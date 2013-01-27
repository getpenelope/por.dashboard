import colander

from colander import SchemaNode
import deform
from deform import ValidationFailure
from deform.widget import CheckboxWidget, TextInputWidget, SelectWidget, SequenceWidget
from deform_bootstrap.widget import ChosenSingleWidget, ChosenMultipleWidget
from pyramid.renderers import get_renderer
from pyramid import httpexceptions as exc
from por.models import Project, Group, DBSession, User #CustomerRequest
from por.models.dashboard import Trac, Role, GoogleDoc

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
        role = SchemaNode(typ=colander.String(),
                        widget=ChosenSingleWidget(),
                        missing=colander.required,
                        title=u'role')

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
                        missing=colander.required,
                        title=u'')
            ticket = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Create related ticket')
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

        form['trac']['milestones'].widget = SequenceWidget(min_len=1)
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
        """
            The main handle method for the wizard.
            {'google_docs': {'documentation_analysis': u'a',
                 'estimations': u'c',
                 'sent_by_customer': u'b'},
             'new_users': [{'email': u'massimo@redturtle.it',
                            'fullname': u'Massimo Azzolini',
                            'role': u'customer',
                            'send_email_howto': False}],
             'project_name': u'one',
             'trac': {'create_cr': False,
                      'create_trac': False,
                      'milestones': [{'due_date': datetime.date(2013, 1, 27),
                                      'title': u'Le Ceste di Natale'}]},
             'users': [{'role': u'customer', 'usernames': set([u'1', u'2'])}]}

        """
        customer = self.context.get_instance()
        #import pdb; pdb.set_trace()
        #create new users
        groups = {}
        for newuser in appstruct['new_users']:
            user = User(fullname=newuser['fullname'], email=newuser['email'])
            if not groups.has_key(newuser['role']):
                groups[newuser['role']] = []
            DBSession.add(user)
            DBSession.flush()
            groups[newuser['role']].append(u'%s' % user.id)

        #create project 
        project = Project(name=appstruct['project_name'])

        #... and set manager

        #set groups
        for g in appstruct['users']:
            if not groups.has_key(g['role']):
                groups[g['role']] = []
            for u in g['usernames']:
                groups[g['role']].append(u)

        for r, u in groups.items():
            role = DBSession.query(Role).filter(Role.name==r)[0]
            users = []
            for user_id in u:
                user = DBSession.query(User).filter(User.id==user_id)[0]
                users.append(user)
            group = Group(roles=[role,], users=users)
            project.add_group(group)

                

        #create CR


        #create quality CR

        #create trac
        trac = Trac(name="Trac for %s" % appstruct['project_name'])
        trac.milestones = appstruct['trac']['milestones']
        project.add_application(trac)

        #create quality ticket

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
