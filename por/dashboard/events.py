
from sqlalchemy.util import OrderedDict

from zope.interface import Interface

from formalchemy import Field, fatypes
from formalchemy.exceptions import ValidationError
from formalchemy.fields import HiddenFieldRenderer, SelectFieldRenderer
from formalchemy.fields import _query_options

from pyramid_formalchemy import events
from pyramid.security import has_permission
from pyramid.i18n import TranslationStringFactory

from fa.jquery.renderers import RichTextFieldRenderer
from fa.jquery.fanstatic_resources import fa_pyramid_js
from plone.i18n.normalizer import idnormalizer

from por.models import DBSession
from por.models.dashboard import TRAC, SVN, Application, Customer, \
        CustomerRequest, Group, Project, User, Contract
from por.models.tp import TimeEntry
from por.dashboard.lib.fa_fields import BigTextAreaFieldRenderer
from por.dashboard.forms.renderers import grooming_label_renderer, UrlRenderer
from por.models.dublincore import DublinCore
from por.models.workflow import Workflow
from por.models.interfaces import IRoleable, ITimeEntry
from por.dashboard.forms.renderers import TicketRenderer
from por.dashboard import PROJECT_ID_BLACKLIST

_ = TranslationStringFactory('por')


@events.subscriber([Interface, events.IBeforeEditRenderEvent])
def before_generic_edit_render(context, event):
    fa_pyramid_js.need()


@events.subscriber([DublinCore, events.IAfterSyncEvent])
def after_dublincore_sync(context, event):
    context.request = event.request #we need request for user calculation


#Dublincore rendering events
@events.subscriber([DublinCore, events.IBeforeListingRenderEvent])
def before_dublincore_listing_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['creation_date']
    del fs._render_fields['modification_date']
    del fs._render_fields['author']


@events.subscriber([DublinCore, events.IBeforeEditRenderEvent])
def before_dublincore_edit_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure()
    del fs._render_fields['creation_date']
    del fs._render_fields['modification_date']
    if has_permission('manage', context, event.request) and ITimeEntry.providedBy(context):
        pass
    else:
        del fs._render_fields['author']


#Role mapping events
@events.subscriber([IRoleable, events.IBeforeEditRenderEvent])
def before_role_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    if not has_permission('manage', context, event.request):
        del fs._render_fields['roles']


#Workflow events
@events.subscriber([Workflow, events.IBeforeRenderEvent])
def before_workflow_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    fs._render_fields.pop('invoice_number', None)
    wf = fs._render_fields.pop('workflow_state')
    fs.append(wf)


@events.subscriber([Workflow, events.IBeforeEditRenderEvent])
def before_workflow_edit_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure()
    del fs._render_fields['workflow_state']



#Project rendering events
@events.subscriber([Project, events.IBeforeRenderEvent])
def before_project_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['applications']
    del fs._render_fields['time_entries']
    del fs._render_fields['favorite_users']

@events.subscriber([Project, events.IBeforeEditRenderEvent])
def before_project_edit_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure()
    fs.test_date.set(instructions=_(u'the date (if any) in which the Customer has officially accepted the project as "completed"'))
    fs.assistance_date.set(instructions=_(u'the date (if any) when the post-release assistance is ending'))
    fs.completion_date.set(instructions=_(u'the date in which the full invoicing of the developement phase is completed, excluding post-release assistance. Usually, it is the date of the final invoice.'))
    fs.append(fs.name.required())
    del fs._render_fields['customer_requests']
    del fs._render_fields['groups']
    pk_to_add = [a for a in fs._raw_fields() if a.name == 'id']
    fs.append(pk_to_add[0].set(renderer=HiddenFieldRenderer))

@events.subscriber([Project, events.IBeforeNewRenderEvent])
def before_project_new_render(context, event):
    """called after edit renderer"""
    bind_customer(context, event)
    fs = event.kwargs['fs']
    del fs._render_fields['customer']
    pk_to_add = [a for a in fs._raw_fields() if a.name == 'id']
    items = list(tuple(fs._render_fields.iteritems()))
    items.insert(0, (pk_to_add[0].name, pk_to_add[0]))
    fs._render_fields = OrderedDict(items)
    fs._render_fields['id'].validators = []
    fs._render_fields['id']._renderer = None


@events.subscriber([Project, events.IBeforeValidateEvent])
def before_project_validated(context, event):
    """called before validation"""
    def my_validator(fs):
        if not fs.id.value:
            project_id = idnormalizer.normalize(fs.name.value)
        else:
            project_id = fs.id.value

        if project_id.lower() in PROJECT_ID_BLACKLIST:
            msg = _('${fs_name_value} is a restricted name! Please choose '
                    'another project name or provide unique ID!',
                    mapping={'fs_name_value': project_id})
            raise ValidationError(msg)

        project = DBSession().query(Project).get(project_id)
        if project and project != fs.model:
            msg = _('${fs_name_value} already exists! Please choose another '
                    'project name or provide unique ID!',
                    mapping={'fs_name_value': project_id})
            raise ValidationError(msg)

        if fs.activated.value == False:
            active_contracts = [a for a in project.contracts if a.active]
            if active_contracts:
                msg = _('You cannot deactivate project! It has uncompleted '
                        'contracts!')
                raise ValidationError(msg)

    event.fs.validator = my_validator


#Customer rendering events
@events.subscriber([Customer, events.IBeforeEditRenderEvent])
def before_customer_render(context, event):
    fs = event.kwargs['fs']
    #fs.projects.set(renderer=autocomplete_relation(filter_by='name'))
    fs.append(fs.name.required())
    del fs._render_fields['projects']


#User listing
@events.subscriber([User, events.IBeforeListingRenderEvent])
def before_user_listing_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['mobile']
    del fs._render_fields['phone']
    del fs._render_fields['groups']
    del fs._render_fields['favorite_projects']


#User rendering events
@events.subscriber([User, events.IBeforeRenderEvent])
def before_user_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['gdata_auth_token']
    del fs._render_fields['openids']
    del fs._render_fields['salt']
    del fs._render_fields['password']
    del fs._render_fields['active']


@events.subscriber([User, events.IBeforeEditRenderEvent])
def before_user_edit_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)

    del fs._render_fields['favorite_projects']
    del fs._render_fields['groups']

    if not has_permission('manage', context, event.request):
        del fs._render_fields['project_manager']

    fs.append(fs.fullname.required())
    fs.append(fs.email.required())


#Group rendering events
@events.subscriber([Group, events.IBeforeEditRenderEvent])
def before_group_render(context, event):
    bind_project(context, event)
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['project']


@events.subscriber([Application, events.IBeforeRenderEvent])
def before_application_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['svn_name']
    del fs._render_fields['trac_name']
    del fs._render_fields['acl']
    fs.api_uri.set(renderer=UrlRenderer) 


@events.subscriber([Application, events.IBeforeValidateEvent])
def before_application_validated(context, event):
    """called before validation"""
    def my_validator(fs):
        app_type = fs.application_type.value
        if app_type != TRAC and app_type != SVN:
            if not fs.api_uri.value:
                msg = _('You have choosen ${app_type} as your application type. Please provide api uri.',
                        mapping={'app_type': app_type})
                raise ValidationError(msg)
    event.fs.validator = my_validator


@events.subscriber([Application, events.IBeforeEditRenderEvent])
def before_application_edit_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    fs.description.set(renderer=RichTextFieldRenderer(use='tinymce', theme='simple'))
    fs.append(fs.name.required())
    del fs._render_fields['project']
    fs.append(Field('application_type', type=fatypes.String))
    fs.application_type.set(renderer=SelectFieldRenderer, options=['trac', 'svn', 'trac report', 'google docs', 'generic'])
    bind_project(context, event)
    [fs.append(fs._render_fields.pop(a)) for a in fs._render_fields if a != 'name']


@events.subscriber([Application, events.IBeforeNewRenderEvent])
def before_application_new_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['position']
    fs.api_uri.metadata['instructions'] = _(u'Please provide application uri. If you choose trac or svn - leave this field empty.')


@events.subscriber([Contract, events.IBeforeRenderEvent])
def before_contract_render(context, event):
    bind_project(context, event)
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['project']
    del fs._render_fields['time_entries']
    del fs._render_fields['customer_requests']


#Contract listing
@events.subscriber([Contract, events.IBeforeListingRenderEvent])
def before_contract_listing_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['description']
    del fs._render_fields['project_id']


@events.subscriber([Contract, events.IBeforeEditRenderEvent])
def before_contract_editrender(context, event):
    bind_project(context, event)
    fs = event.kwargs['fs']
    fs.contract_number.set(instructions=_(u'Something like number/year'))
    fs.ammount.set(instructions=_(u'Contract ammount in EUR'))
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    fs.description.set(renderer=RichTextFieldRenderer(use='tinymce', theme='simple'))
    fs.append(fs.name.required())
    for field in ['name', 'contract_number', 'ammount', 'days', 'start_date', 'end_date', 'description']:
        fs.append(fs._render_fields.pop(field))


@events.subscriber([Contract, events.IBeforeValidateEvent])
def before_contract_validated(context, event):
    """called before validation"""
    def my_validator(fs):
        contract_id = idnormalizer.normalize('%s_%s' % (fs.project_id.value, fs.name.value))

        if contract_id.lower() in PROJECT_ID_BLACKLIST:
            msg = _('${fs_name_value} is a restricted name! Please choose '
                    'another contract name!',
                    mapping={'fs_name_value': fs.name.value})
            raise ValidationError(msg)

        contract = DBSession().query(Contract).get(contract_id)
        if contract and contract != fs.model:
            msg = _('${fs_name_value} already exists! Please choose another '
                    'contract name!',
                    mapping={'fs_name_value': fs.name.value})
            raise ValidationError(msg)
    event.fs.validator = my_validator


#Customer request rendering events
@events.subscriber([CustomerRequest, events.IBeforeEditRenderEvent])
def before_customerrequest_editrender(context, event):
    bind_project(context, event)
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    fs.description.set(renderer=RichTextFieldRenderer(use='tinymce', theme='simple'))
    fs.append(fs.name.required())
    del fs._render_fields['project']
    q = DBSession().query(fs.contract.relation_type()).filter_by(project_id=context.project_id).order_by('name')
    fs.contract.render_opts['options'] = _query_options(q)
    [fs.append(fs._render_fields.pop(a)) for a in fs._render_fields if a != 'name']


@events.subscriber([CustomerRequest, events.IBeforeRenderEvent])
def before_customerrequest_render(context, event):
    bind_project(context, event)
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    fs.placement.set(renderer=grooming_label_renderer())
    del fs._render_fields['estimations']
    del fs._render_fields['uid']
    del fs._render_fields['project_id']
    if not event.request.has_permission('contract', context):
        del fs._render_fields['contract']
    if fs.readonly:
        fs.append(Field('estimation_days', type=fatypes.Float))
        fs.estimation_days._value = context.estimation_days


#TimeEntry events
@events.subscriber([TimeEntry, events.IBeforeShowRenderEvent])
def before_timeentry_show_render(context, event):
    fs = event.kwargs['fs']
    fs.ticket.set(renderer=TicketRenderer(fs.ticket))


@events.subscriber([TimeEntry, events.IBeforeEditRenderEvent])
def before_timeentry_edit_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    fs.description.set(renderer=BigTextAreaFieldRenderer)
    del fs._render_fields['start']
    del fs._render_fields['end']
    del fs._render_fields['tickettype']

    q = DBSession().query(fs.contract.relation_type()).filter_by(project_id=context.project_id).order_by('name')
    fs.contract.render_opts['options'] = _query_options(q)
    #remove location required validator
    if not fs.location.value:
        fs.location.model.location = u'RedTurtle'

    fs.append(fs.date.required())
    fs.append(fs.ticket.required())


@events.subscriber([TimeEntry, events.IBeforeListingRenderEvent])
def before_timeentry_listing_render(context, event):
    fs = event.kwargs['fs']
    if not fs._render_fields.keys():
        fs.configure(readonly=fs.readonly)
    del fs._render_fields['start']
    del fs._render_fields['end']
    #stupid sorter
    [fs.append(fs._render_fields.pop(a)) for a in fs._render_fields if a != 'description']


def bind_project(context, event):
    fs = event.kwargs['fs']
    if event.request.model_instance.__class__ is Project:
        fs.model.project_id = event.request.model_id
    fs.project_id.is_raw_foreign_key = False
    fs.project_id.set(renderer=HiddenFieldRenderer)
    fs.append(fs.project_id)


def bind_customer(context, event):
    fs = event.kwargs['fs']
    if event.request.model_instance.__class__ is Customer:
        fs.model.customer_id = event.request.model_id
    fs.customer_id.is_raw_foreign_key = False
    fs.customer_id.set(renderer=HiddenFieldRenderer)
    fs.append(fs.customer_id)


class AfterEntryCreatedEvent(object):
    """A search entry was created"""

    def __init__(self, entry, timeentry):
        self.entry = entry
        self.timeentry = timeentry
