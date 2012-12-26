import colander
from colander import SchemaNode
import deform
from deform import ValidationFailure
from deform.widget import CheckboxWidget, TextInputWidget, SelectWidget, SequenceWidget

from pyramid.view import view_config

from por.dashboard.lib.widgets import SubmitButton, ResetButton, WizardForm

class GoogleDocsSchema(colander.Schema):
    documentation_analysis = SchemaNode( typ=colander.String(),
                                widget=TextInputWidget(
                                            css_class='input-xxlarge',
                                            placeholder=u'paste your google docs folder'),
                                missing=None,
                                title=u'Documentation and analysis')

    sent_by_customer = SchemaNode( typ=colander.String(),
                                widget=TextInputWidget(
                                            css_class='input-xxlarge',
                                            placeholder=u'paste your google docs folder'),
                                missing=None,
                                title=u'Documentation sent by the customer')

    estimations = SchemaNode( typ=colander.String(),
                                widget=TextInputWidget(
                                            css_class='input-xxlarge',
                                            placeholder=u'paste your google docs folder'),
                                missing=None,
                                title=u'Estimations')

# it should be something like:
# from por.dashboard.security.acl import ProjectRelatedRoles
# choices = ProjectRelatedRoles.get_roles()
# but for now let's start with these settings
choices = (
    ('','-- select --'),
    ('customer','customer'),
    ('internal_developer','internal developer'),
    ('external_developer','external developer'),
    )


class UsersSchema(colander.SequenceSchema):
    class UserSchema(colander.Schema):
        user = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'select an username (email)'),
                        missing=None,
                        validator=colander.Email(),
                        title=u'User')
        role = SchemaNode(typ=colander.String(),
                        widget=SelectWidget(values=choices),
                        missing=None,)
    user = UserSchema()


class NewUsersSchema(colander.SequenceSchema):
    class NewUserSchema(colander.Schema):
        fullname = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'John Smith'),
                        missing=None,
                        title=u'Fullname')
        email = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'jsmith@domain.com'),
                        missing=None,
                        validator=colander.Email(),
                        title=u'E-mail')
        send_email_howto = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
                        title=u'Send e-mail'
                    )
        role = SchemaNode(typ=colander.String(),
                        widget=SelectWidget(values=choices),
                        missing=None,)

    user = NewUserSchema()

class TracStdCR(colander.Schema):
    class Milestones(colander.SequenceSchema):
        class Milestone(colander.Schema):
            title = SchemaNode(typ=colander.String(),
                        widget=TextInputWidget(placeholder=u'iteration X or name of the milestone'),
                        missing=None,
                        title=u'Title')
            due_date = SchemaNode(typ=colander.Date(),
                        missing=None,
                        title=u'Due date')

        milestone = Milestone()

    create_trac = SchemaNode(typ=colander.Boolean(),
                        widget=CheckboxWidget(),
                        missing=None,
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
                        widget=TextInputWidget(placeholder=u'the customer wants...'),
                        missing=None,
                        title=u'Title')
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
                                            placeholder=u'Insert project name'),
                    missing=colander.required,
                    title=u'Project')
    google_docs = GoogleDocsSchema()
    new_users = NewUsersSchema()
    users = UsersSchema()
    trac = TracStdCR()
    project_cr = ProjectCR()

class Wizard(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(name='report_wizard', route_name='reports', renderer='skin', permission='reports_my_entries')
    def __call__(self):
        schema = WizardSchema().clone()
        form = WizardForm(schema,
                             formid='wizard',
                             method='GET',
                             buttons=[
                                 SubmitButton(title=u'Submit'),
                                 ResetButton(title=u'Reset'),
                             ])
        form['new_users'].widget = SequenceWidget(min_len=1)
        form['users'].widget = SequenceWidget(min_len=1)
        form['trac']['milestones'].widget = SequenceWidget(min_len=1)
        form['project_cr']['customer_requests'].widget = SequenceWidget(min_len=1)
        
        # validate input
        controls = self.request.GET.items()
        if controls != []:
            try:
                appstruct = form.validate(controls)
            except ValidationFailure as e:
                return {
                        'form': e.render(),
                        }

        return {
                'form': form.render(colander.null)
                }

