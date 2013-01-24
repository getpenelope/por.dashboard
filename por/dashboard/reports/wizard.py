import colander

from colander import SchemaNode
from deform import ValidationFailure
from deform.widget import CheckboxWidget, TextInputWidget, SelectWidget, SequenceWidget
from deform_bootstrap.widget import ChosenSingleWidget
from pyramid.renderers import get_renderer
from pyramid import httpexceptions as exc
from por.models import Project, DBSession, User #CustomerRequest
from por.models.dashboard import Trac, Role

#from pyramid.view import view_config

from por.dashboard.lib.widgets import SubmitButton, ResetButton, WizardForm
from por.dashboard.fanstatic_resources import wizard as wizard_fanstatic


class GoogleDocsSchema(colander.Schema):
    documentation_analysis = SchemaNode( typ=colander.String(),
                                widget=TextInputWidget(
                                            css_class='input-xxlarge',
                                            placeholder=u'Documentation and analysis, paste your google docs folder'),
                                missing=None,
                                title=u'')

    sent_by_customer = SchemaNode( typ=colander.String(),
                                widget=TextInputWidget(
                                            css_class='input-xxlarge',
                                            placeholder=u'Documentation sent by the customer, paste your google docs folder'),
                                missing=None,
                                title=u'')

    estimations = SchemaNode( typ=colander.String(),
                                widget=TextInputWidget(
                                            css_class='input-xxlarge',
                                            placeholder=u'Estimations, paste your google docs folder'),
                                missing=None,
                                title=u'')

class UsersSchema(colander.SequenceSchema):
    class UserSchema(colander.Schema):
        username = SchemaNode(typ=colander.String(),
                        widget=ChosenSingleWidget(),
                        missing=colander.required,
                        title=u'')
        role = SchemaNode(typ=colander.String(),
                        widget=ChosenSingleWidget(),
                        missing=colander.required,
                        title=u'role')
    user = UserSchema()


class NewUsersSchema(colander.SequenceSchema):
    class NewUserSchema(colander.Schema):
        fullname = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'Fullname'),
                        missing=None,
                        title=u'')
        email = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'E-mail'),
                        missing=None,
                        validator=colander.Email(),
                        title=u'')
        send_email_howto = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Send e-mail'
                    )
        #BBB to be fixed with proper role values
        role = SchemaNode(typ=colander.String(),
                        widget=SelectWidget(),
                        missing=None,)

    new_user = NewUserSchema()

class TracStdCR(colander.Schema):
    class Milestones(colander.SequenceSchema):
        class Milestone(colander.Schema):
            title = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'Title'),
                        missing=colander.required,
                        title=u'')
            due_date = SchemaNode(typ=colander.Date(),
                        missing=colander.required,
                        title=u'Due date')

        milestone = Milestone()

    create_trac = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=False,
                        title=u'Create trac'
                    )
    milestones = Milestones()
    create_cr = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Create CR "VERIFICHE E VALIDAZIONI PROGETTO" and 2 additional tickets'
                    )

class ProjectCR(colander.Schema):
    class CustomerRequests(colander.SequenceSchema):
        class CustomerRequest(colander.Schema):
            title = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'Title, the customer wants...'),
                        missing=None,
                        title=u'')
            ticket = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Create related ticket'
                    )
            junior = SchemaNode(typ=colander.Decimal(),
                        missing=None,
                        title=u'Junior')
            senior = SchemaNode(typ=colander.Decimal(),
                        missing=None,
                        title=u'Senior')
            graphic = SchemaNode(typ=colander.Decimal(),
                        missing=None,
                        title=u'Graphic')
            pm = SchemaNode(typ=colander.Decimal(),
                        missing=None,
                        title=u'PM')
            architect = SchemaNode(typ=colander.Decimal(),
                        missing=None,
                        title=u'Architect')
            tester = SchemaNode(typ=colander.Decimal(),
                        missing=None,
                        title=u'Tester')
        customer_request = CustomerRequest()

    create_cr = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Create the following CRs'
                    )
    customer_requests = CustomerRequests()


class WizardSchema(colander.Schema):
    project_name = SchemaNode(typ=colander.String(),
                    widget=TextInputWidget( size=20,
                                            validator=colander.Length(max=20),
                                            css_class='projectname-select',
                                            placeholder=u'Project name'),
                    missing=colander.required,
                    title=u'')
    google_docs = GoogleDocsSchema()
    users = UsersSchema()
    new_users = NewUsersSchema()

    trac = TracStdCR()
    #project_cr = ProjectCR()


class Wizard(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    #@view_config(name='wizard', route_name='reports', renderer='skin', permission='reports_my_entries')
    def render(self):
        result = {}
        result['main_template'] = get_renderer('por.dashboard:skins/main_template.pt').implementation()
        result['main'] = get_renderer('por.dashboard.forms:templates/master.pt').implementation()

        schema = WizardSchema().clone()
        wizard_fanstatic.need()
        form = WizardForm(schema,
                             formid='wizard',
                             method='GET',
                             buttons=[
                                 SubmitButton(title=u'Submit'),
                                 ResetButton(title=u'Reset'),
                             ])
                             
        form['new_users'].widget = SequenceWidget()
        form['users'].widget = SequenceWidget(min_len=1)
        
        #import pdb; pdb.set_trace()
        users = DBSession.query(User).order_by(User.fullname)
        form['users']['user']['username'].widget.values = [('', '')] + [(str(u.id), u.fullname) for u in users]
        
        roles = DBSession.query(Role).order_by(Role.name)
        form['users']['user']['role'].widget.values = [('', '')] + [(str(role.id), role.name) for role in roles]
        
        form['trac']['milestones'].widget = SequenceWidget(min_len=1)
        #form['project_cr']['customer_requests'].widget = SequenceWidget(min_len=1)

        # validate input
        controls = self.request.GET.items()
        if controls != []:
            try:
                appstruct = form.validate(controls)
                self.handle_save(appstruct)
            except ValidationFailure as e:
                result['form'] = e.render()
                return result

        result['form'] = form.render(colander.null)
        return result
          
    def handle_save(self, appstruct):
        """The main handle method for the wizard."""
        customer = self.context.get_instance()
        
        project = Project(name=appstruct['project_name'])
        trac = Trac(name="Trac for %s" % appstruct['project_name'])
        trac.milestones = appstruct['trac']['milestones']
        project.add_application(trac)
        #svn = Subversion(name="SVN")
        #project.add_application(svn)
        
        customer.add_project(project)
        #import pdb; pdb.set_trace()
        
        raise exc.HTTPFound(location=self.request.fa_url('Customer', customer.id))

