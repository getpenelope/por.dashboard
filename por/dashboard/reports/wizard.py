import colander

from colander import SchemaNode
import deform
from deform import ValidationFailure
from deform.widget import CheckboxWidget, TextInputWidget, SelectWidget, SequenceWidget
from deform_bootstrap.widget import ChosenSingleWidget, ChosenMultipleWidget
from pyramid.renderers import get_renderer
from pyramid import httpexceptions as exc
from por.models import Project, Group, DBSession, User, CustomerRequest
from por.models.dashboard import Trac, Role, GoogleDoc, Estimation

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
        usernames = SchemaNode(deform.Set(allow_empty=False),
                   widget=ChosenMultipleWidget(placeholder=u'Select people'),
                   missing=colander.required,
                   title=u'')
        role = SchemaNode(typ=colander.String(),
                        widget=ChosenSingleWidget(),
                        missing=colander.required,
                        title=u'role')
    user = UserSchema()




class NewUsersSchema(colander.SequenceSchema):
    class NewUserSchema(colander.Schema):
        def unusedEmail(value):
            try:
                user = DBSession.query(User).filter(User.email==value).one()
                return "email '%s' is already associated to another user" % value
            except:
                return True


        fullname = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'Fullname'),
                        missing=colander.required,
                        title=u'')
        email = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'E-mail'),
                        missing=colander.required,
                        validator=colander.Function(unusedEmail, ''),
                        title=u'')
        send_email_howto = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Send e-mail'
                    )
        role = SchemaNode(typ=colander.String(),
                        widget=ChosenSingleWidget(),
                        missing=colander.required,
                        title=u'role')

    new_user = NewUserSchema()


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

class ProjectCR(colander.Schema):
    class CustomerRequests(colander.SequenceSchema):
        class CustomerRequest(colander.Schema):
            title = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'Title, the customer wants...'),
                        missing=colander.required,
                        title=u'')
            junior = SchemaNode(typ=colander.Decimal(),
                        widget=TextInputWidget(css_class='input-mini', placeholder=u'Junior'),
                        missing=None,
                        title=u'')
            senior = SchemaNode(typ=colander.Decimal(),
                        widget=TextInputWidget(css_class='input-mini', placeholder=u'Senior'),
                        missing=None,
                        title=u'')
            graphic = SchemaNode(typ=colander.Decimal(),
                        widget=TextInputWidget(css_class='input-mini', placeholder=u'Graphic'),
                        missing=None,
                        title=u'')
            pm = SchemaNode(typ=colander.Decimal(),
                        widget=TextInputWidget(css_class='input-mini', placeholder=u'PM'),
                        missing=None,
                        title=u'')
            architect = SchemaNode(typ=colander.Decimal(),
                        widget=TextInputWidget(css_class='input-mini', placeholder=u'Arch.'),
                        missing=None,
                        title=u'')
            tester = SchemaNode(typ=colander.Decimal(),
                        widget=TextInputWidget(css_class='input-mini', placeholder=u'Tester'),
                        missing=None,
                        title=u'')
            ticket = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Create related ticket')
            
        customer_request = CustomerRequest()

    customer_requests = CustomerRequests()
    create_cr = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Create CR "VERIFICHE E VALIDAZIONI PROGETTO" and 2 additional tickets'
                    )

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

    milestones = Milestones()
    project_cr = ProjectCR()


class Wizard(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def render(self):
        result = {}
        result['main_template'] = get_renderer('por.dashboard:skins/main_template.pt').implementation()
        result['main'] = get_renderer('por.dashboard.forms:templates/master.pt').implementation()

        schema = WizardSchema().clone()
        wizard_fanstatic.need()
        form = WizardForm(schema,
                          formid='wizard',
                          method='POST',
                          buttons=[
                                 SubmitButton(title=u'Submit'),
                                 ResetButton(title=u'Reset'),
                          ])
        form['new_users'].widget = SequenceWidget()
        form['users'].widget = SequenceWidget(min_len=1)

        users = DBSession.query(User).order_by(User.fullname)
        form['users']['user']['usernames'].widget.values = [('', '')] + [(str(u.id), u.fullname) for u in users]

        roles = DBSession.query(Role).order_by(Role.name)
        form['users']['user']['role'].widget.values = [('', '')] + [(str(role.id), role.name) for role in roles]
        form['new_users']['new_user']['role'].widget.values = [('', '')] + [(str(role.id), role.name) for role in roles]

        form['milestones'].widget = SequenceWidget(min_len=1)
        form['project_cr']['customer_requests'].widget = SequenceWidget()

        # validate input
        controls = self.request.POST.items()
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
        """ The main handle method for the wizard. """
        customer = self.context.get_instance()

        #create new users
        groups = {}
        for newuser in appstruct['new_users']:
            user = User(fullname=newuser['fullname'], email=newuser['email'])
            if not groups.has_key(newuser['role']):
                groups[newuser['role']] = []
            groups[newuser['role']].append(user)

        #create project and set manager
        manager = self.request.authenticated_user
        project = Project(name=appstruct['project_name'], 
                        manager=manager)

        #set groups
        for g in appstruct['users']:
            if not groups.has_key(g['role']):
                groups[g['role']] = []
            for u in g['usernames']:
                user = DBSession.query(User).get(u)
                groups[g['role']].append(user)

        for rolename, users in groups.items():
            role = DBSession.query(Role).filter(Role.name==rolename).one()
            group = Group(roles=[role,], users=users)
            project.add_group(group)

        #create CR
        for cr in appstruct['customer_requests']:
            customer_request = CustomerRequest(name=cr['title'])
            person_types = {
                'junior':'Junior',
                'senior':'Senior',
                'graphic':'Graphic',
                'pm':'Project manager',
                'architect':'Architect',
                'tester':'Tester'
            }
            for key, value in person_types.items():
                if cr[key]:
                    junior_estimation = Estimations(person_type=key, 
                                                    days=value,
                                                    customer_request=customer_request)
            project.add_customer_request(customer_request)
            #BBB define the ticket

        #create quality CR
        project.add_customer_request(CustomerRequest(name="Verifiche e validazioni progetto"))
        #BBB define the two ticket

        #create trac
        trac = Trac(name="Trac for %s" % appstruct['project_name'])
        trac.milestones = appstruct['milestones']
        project.add_application(trac)

        #create all the tickets

        #create svn
        #svn = Subversion(name="SVN")
        #project.add_application(svn)

        #create google docs/folders
        if appstruct['google_docs']['documentation_analysis']:
            app = GoogleDoc(name=u'documentation_analysis', 
                            api_uri=appstruct['google_docs']['documentation_analysis'])
            project.add_application(app)

        if appstruct['google_docs']['estimations']:
            app = GoogleDoc(name=u'estimations', 
                            api_uri=appstruct['google_docs']['estimations'])
            project.add_application(app)


        if appstruct['google_docs']['sent_by_customer']:
            app = GoogleDoc(name=u'sent_by_customer', 
                            api_uri=appstruct['google_docs']['sent_by_customer'])
            project.add_application(app)


        customer.add_project(project)
        raise exc.HTTPFound(location=self.request.fa_url('Customer', customer.id))
