from copy import deepcopy
import json

from sqlalchemy import not_
from pyramid import httpexceptions as exc
from pyramid_skins import SkinObject

from fa.bootstrap import actions

from por.models import dashboard
from por.dashboard.forms import ModelView
from por.dashboard.forms.renderers import ProjectRelationRenderer
from por.dashboard.reports.all_entries import AllEntriesReport
from por.dashboard.reports.views import ReportContext



def configurate(config):
    #custom view for customer

    config.formalchemy_model_view('admin',
        request_method='GET',
        permission='metadata',
        name='metadata',
        attr='show',
        renderer='por.dashboard.forms:templates/customer.pt',
        model='por.models.dashboard.Customer',
        view=CustomerModelView)

    config.formalchemy_model_view('admin',
        request_method='POST',
        permission='delete',
        name='delete',
        attr='delete',
        renderer='fa.bootstrap:templates/admin/edit.pt',
        model='por.models.dashboard.Customer',
        view=CustomerModelView)

    config.formalchemy_model_view('admin',
        renderer='por.dashboard.forms:templates/customer_listing.pt',
        attr='datatable',
        context='pyramid_formalchemy.resources.ModelListing',
        request_method='GET',
        permission='customer_listing',
        model='por.models.dashboard.Customer',
        view=CustomerModelView)

    #custom view for adding a project to a customer
    config.formalchemy_model_view('admin',
        request_method='GET',
        permission='new',
        name='add_project',
        attr='add_project',
        renderer='fa.bootstrap:templates/admin/new.pt',
        model='por.models.dashboard.Customer',
        view=CustomerModelView)

    #custom view for customer projects
    config.formalchemy_model_view('admin',
        request_method='GET',
        permission='view',
        name='',
        attr='customer_projects',
        renderer='por.dashboard.forms:templates/customer_projects.pt',
        model='por.models.dashboard.Customer',
        view=CustomerModelView)

    #custom view for customer projects
    config.formalchemy_model_view('admin',
        request_method='GET',
        permission='time_entries',
        name='customer_time_entries',
        attr='customer_time_entries',
        model='por.models.dashboard.Customer',
        view=CustomerModelView)


add_project = actions.UIButton(id='add_project',
    content='Add project',
    permission='new',
    _class='btn btn-success',
    attrs=dict(href="request.fa_url('Customer', request.model_id, 'add_project')"))

customer_tabs = actions.Actions(actions.TabAction("show",
    content="Customer",
    attrs=dict(href="request.fa_url('Customer', request.model_id, '')")),
    actions.TabAction("metadata",
        permission='metadata',
        content="Metadata",
        attrs=dict(href="request.fa_url('Customer', request.model_id, 'metadata')")),
    actions.TabAction("customer_time_entries",
        content="Time entires",
        permission='time_entries',
        attrs=dict(
            href="request.fa_url('Customer', request.model_id, 'customer_time_entries', customer_id=request.model_id)"))
    , )


class CustomerModelView(ModelView):
    actions_categories = ('buttons', 'tabs')

    defaults_actions = deepcopy(actions.defaults_actions)
    defaults_actions.update(show_buttons=actions.Actions(actions.edit))
    defaults_actions['customer_projects_buttons'] = actions.Actions(add_project)
    defaults_actions.update(show_tabs=customer_tabs)
    defaults_actions.update(customer_projects_tabs=customer_tabs)
    defaults_actions.update(customer_time_entries_tabs=customer_tabs)

    def add_project_url(self, *args, **kwargs):
        return self.project_url

    def add_project(self, *args, **kwargs):
        self.request.model_class = dashboard.Project
        self.request.model_name = dashboard.Project.__name__
        return self.new()

    @actions.action('customer_projects')
    def customer_projects(self, *args, **kwargs):
        context = self.context.get_instance()

        query = self.session.query(dashboard.Project).filter(dashboard.Project.customer_id == context.id)
        other_projects = self.request.query_factory(self.request, query).filter(not_(dashboard.Project.active))

        active_project_query = query.filter(dashboard.Project.active)
        active_projects = self.request.query_factory(self.request, active_project_query)

        self.context.get_model = lambda: dashboard.Project
        self.request.model_name = 'Project'

        page = self.get_page(collection=list(self.request.filter_viewables(other_projects)))
        fs = self.get_grid()
        fs = fs.bind(instances=page, request=self.request)
        fs.configure(readonly=True)
        del fs._render_fields['applications']
        del fs._render_fields['time_entries']
        del fs._render_fields['favorite_users']
        del fs._render_fields['creation_date']
        del fs._render_fields['modification_date']
        del fs._render_fields['author']
        del fs._render_fields['activated']
        del fs._render_fields['customer']
        del fs._render_fields['groups']
        del fs._render_fields['customer_requests']
        del fs._render_fields['karma_id']
        del fs._render_fields['completion_date']
        del fs._render_fields['test_date']
        del fs._render_fields['inception_date']
        del fs._render_fields['assistance_date']

        page = self.get_page(collection=list(self.request.filter_viewables(active_projects)))
        fs_active = self.get_grid()
        fs_active = fs_active.bind(instances=page, request=self.request)
        fs_active.configure(readonly=True)
        del fs_active._render_fields['karma_id']
        del fs_active._render_fields['applications']
        del fs_active._render_fields['time_entries']
        del fs_active._render_fields['favorite_users']
        del fs_active._render_fields['creation_date']
        del fs_active._render_fields['modification_date']
        del fs_active._render_fields['activated']
        del fs_active._render_fields['customer']
        del fs_active._render_fields['author']
        del fs_active._render_fields['groups']
        del fs_active._render_fields['customer_requests']
        del fs_active._render_fields['completion_date']
        del fs_active._render_fields['test_date']
        del fs_active._render_fields['assistance_date']
        del fs_active._render_fields['inception_date']

        return self.render(fs=fs, fs_active=fs_active)

    @actions.action('customer_time_entries')
    def customer_time_entries(self, *args, **kwargs):
        params = AllEntriesReport(self.context, self.request)()
        params.update(**self.render())
        params.update(request=self.request)
        report_context= ReportContext(self.request)
        params.update(context=report_context)
        return SkinObject('customer_time_entries')(**params)

    @actions.action('listing')
    def datatable(self, **kwargs):
        result = super(CustomerModelView, self).datatable(**kwargs)

        fs = result['fs']
        fs.configure(pk=True, readonly=True)
        viewed_customers = set(fs.rows.items)

        columns = ['name', 'projects', 'id']
        self.pick_columns(fs, columns)

        fs._render_fields['projects']._get_renderer = lambda: ProjectRelationRenderer(fs._render_fields['projects'])

        favorite_projects = set(self.request.authenticated_user.favorite_projects)
        favorite_customers = set(c.id
                                 for c in viewed_customers
                                 if favorite_projects.intersection(c.projects))
        active_customers = set(c.id
                               for c in viewed_customers
                               if any(p.activated for p in c.projects))

        return dict(result,
                    columns=columns,
                    js_active_customers=json.dumps(list(active_customers)),
                    js_favorite_customers=json.dumps(list(favorite_customers)))


    def delete(self):
        customer = self.context.get_instance()
        if customer.projects:
            request = self.request
            request.add_message(u'Customer has projects. Please remove them first.', type='danger')
            raise exc.HTTPFound(location=request.fa_url('Customer', customer.id))
        else:
            return self.force_delete()
