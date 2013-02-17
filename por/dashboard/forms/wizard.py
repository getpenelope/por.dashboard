# This Python file uses the following encoding: utf-8
import colander
import deform

from colander import SchemaNode
from deform import ValidationFailure
from deform.widget import CheckboxWidget, TextInputWidget, SequenceWidget
from deform_bootstrap.widget import ChosenSingleWidget, ChosenMultipleWidget
from pyramid.renderers import get_renderer
from pyramid import httpexceptions as exc
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message

from por.models import Project, Group, DBSession, User, CustomerRequest
from por.models.dashboard import Trac, Role, GoogleDoc, Estimation
from por.dashboard.lib.widgets import SubmitButton, ResetButton, WizardForm
from por.dashboard.fanstatic_resources import wizard as wizard_fanstatic

WELCOME_SUBJECT = u"Benvenuto su Penelope, il sistema di Issue tracking di RedTurtle"
WELCOME_BODY = u"""
Sei stato abilitato all'utilizzo di Penelope, la nostra piattaforma online di gestione dei progetti e dei "trouble ticket". 
Con Penelope potrai aprire nuovi ticket e seguire l'evoluzione delle tue segnalazioni. 
Ci raccomandiamo di verificare che i ticket che hai aperto abbiano la marcatura "Ticket Aperto dal Cliente = SI".

Utilizzando questo link: %s/password_reset_form potrai definire la tua nuova password di accesso a Penelope.

RedTurtle ti ringrazia della collaborazione.

====
You were enabled as a user of Penelope, our online projects and trouble ticket management platform. 
With penelope you will be able to open new tickets and follow the evolution of the issues you opened. 
We recommend to double check that the tickets you open have the "Ticked opened by customer" field set at "SI" (Yes).

By this link: %s/password_reset_form you can set your new Penelope password.

RedTurtle thanks you for your collaboration.
"""


class Definition(colander.Schema):
    project_name = SchemaNode(typ=colander.String(),
                              widget=TextInputWidget(css_class='input-xlarge',
                                                     validator=colander.
                                                               Length(max=20),
                                                     placeholder=u'Project name'),
                              missing=colander.required,
                              title=u'')
    trac_name = SchemaNode(typ=colander.String(),
                           widget=TextInputWidget(css_class='input-xxlarge',
                                                  placeholder=u"Short name. It will appear in email's subject"),
                           missing=None,
                           title=u'')


class GoogleDocsSchema(colander.SequenceSchema):
    class GoogleDocSchema(colander.Schema):
        name = SchemaNode(typ=colander.String(),
                          widget=TextInputWidget(css_class='input-xlarge',
                                                 validator=colander.
                                                               Length(max=20),
                                                 placeholder=u'Enter google '
                                                             'doc name'),
                          missing=colander.required,
                          title=u'')
        uri = SchemaNode(typ=colander.String(),
                         widget=TextInputWidget(css_class='input-xxlarge',
                                                placeholder=u'Paste your '
                                                'google docs folder'),
                         missing=colander.required,
                         title=u'')
        share_with_customer = SchemaNode(typ=colander.Boolean(),
                                         widget=CheckboxWidget(),
                                         missing=None,
                                         title=u'Share with the customer')

    google_doc = GoogleDocSchema(title='')


class UsersSchema(colander.SequenceSchema):
    class UserSchema(colander.Schema):
        usernames = SchemaNode(deform.Set(allow_empty=False),
                               widget=ChosenMultipleWidget(placeholder=
                                                           u'Select people'),
                               missing=colander.required,
                               title=u'')
        role = SchemaNode(typ=colander.String(),
                          widget=ChosenSingleWidget(),
                          missing=colander.required,
                          title=u'role')

    user = UserSchema(title='')


class NewUsersSchema(colander.SequenceSchema):
    class NewUserSchema(colander.Schema):
        def unusedEmail(value):
            user = DBSession.query(User.id).filter(User.email == value).first()
            if user:
                return "email '%s' is already associated to another user" % \
                                                                         value
            else:
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
        role = SchemaNode(typ=colander.String(),
                          widget=ChosenSingleWidget(),
                          missing=colander.required,
                          title=u'Role')
        send_email_howto = SchemaNode(typ=colander.Boolean(),
                                      widget=CheckboxWidget(),
                                      missing=None,
                                      title=u'Send e-mail')

    new_user = NewUserSchema(title='')


class Milestones(colander.SequenceSchema):
    class Milestone(colander.Schema):
        title = SchemaNode(typ=colander.String(),
                           widget=TextInputWidget(placeholder=u'Title'),
                           missing=colander.required,
                           title=u'')
        due_date = SchemaNode(typ=colander.Date(),
                              missing=colander.required,
                              title=u'Due date')

    milestone = Milestone(title='')
          


class CustomerRequests(colander.SequenceSchema):
    class CustomerRequest(colander.Schema):
          """
              #BBB specify that junior & co wants days
          """
          title = SchemaNode(typ=colander.String(),
                             widget=TextInputWidget(placeholder=u'Title, '
                                                    'the customer wants...'),
                             missing=colander.required,
                             title=u'')
          junior = SchemaNode(typ=colander.Decimal(),
                              widget=TextInputWidget(css_class='input-mini',
                                                     placeholder=u'Junior'),
                              missing=None,
                              title=u'')
          senior = SchemaNode(typ=colander.Decimal(),
                              widget=TextInputWidget(css_class='input-mini',
                                                     placeholder=u'Senior'),
                              missing=None,
                              title=u'')
          graphic = SchemaNode(typ=colander.Decimal(),
                               widget=TextInputWidget(css_class='input-mini',
                                                      placeholder=u'Graphic'
                                                      ),
                               missing=None,
                               title=u'')
          pm = SchemaNode(typ=colander.Decimal(),
                          widget=TextInputWidget(css_class='input-mini',
                                                 placeholder=u'PM'),
                          missing=None,
                          title=u'')
          architect = SchemaNode(typ=colander.Decimal(),
                                 widget=TextInputWidget(css_class='input-mini',
                                                        placeholder=u'Arch.'),
                                 missing=None,
                                 title=u'')
          tester = SchemaNode(typ=colander.Decimal(),
                              widget=TextInputWidget(css_class='input-mini',
                                                     placeholder=u'Tester'),
                              missing=None,
                              title=u'')
          ticket = SchemaNode(typ=colander.Boolean(),
                              widget=CheckboxWidget(),
                              missing=None,
                              title=u'Create related ticket')

    customer_request = CustomerRequest(title='')


class WizardSchema(colander.Schema):
    project = Definition()
    google_docs = GoogleDocsSchema()
    users = UsersSchema()
    new_users = NewUsersSchema()
    milestones = Milestones()
    customer_requests = CustomerRequests()


class Wizard(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def render(self):
        result = {}
        result['main_template'] = get_renderer(
                'por.dashboard:skins/main_template.pt').implementation()
        result['main'] = get_renderer(
                'por.dashboard.forms:templates/master.pt').implementation()

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
        form['users']['user']['usernames'].widget.values = [('', '')] + \
                                      [(str(u.id), u.fullname) for u in users]

        roles = DBSession.query(Role).order_by(Role.name)
        form['users']['user']['role'].widget.values = [('', '')] + \
                                 [(str(role.id), role.name) for role in roles]
        form['new_users']['new_user']['role'].widget.values = [('', '')] + \
                [(str(role.id), role.name) for role in roles]

        form['milestones'].widget = SequenceWidget(min_len=1)
        form['customer_requests'].widget = SequenceWidget(min_len=2)
        
        controls = self.request.POST.items()
        if controls != []:
            try:
                appstruct = form.validate(controls)
                self.handle_save(appstruct)
            except ValidationFailure as e:
                result['form'] = e.render()
                return result

        appstruct = {'customer_requests': [{'ticket': True,
                                            'title': u'Analisi'},
                                           {'ticket': True,
                                            'title': u'Supporto'}]
                                       }


        result['form'] = form.render(appstruct=appstruct)
        return result

    def handle_save(self, appstruct):
        """ The main handle method for the wizard. """
        customer = self.context.get_instance()

        #create new users
        groups = {}
        settings = self.request.registry.settings
        mailer = get_mailer(self.request)
        for newuser in appstruct['new_users']:
            user = User(fullname=newuser['fullname'], email=newuser['email'])
            if not newuser['role'] in groups:
                groups[newuser['role']] = []
            groups[newuser['role']].append(user)
            if newuser['send_email_howto']:
                body = WELCOME_BODY % (self.request.application_url, self.request.application_url)
                message = Message(subject=WELCOME_SUBJECT,
                                  sender=settings['mail.from_address'],
                                  recipients=[newuser['email']],
                                  body=body)
                mailer.send(message)

        #create project and set manager
        manager = self.request.authenticated_user
        project = Project(name=appstruct['project']['project_name'],
                          manager=manager)

        #set groups
        for g in appstruct['users']:
            if not g['role'] in groups:
                groups[g['role']] = []
            for u in g['usernames']:
                user = DBSession.query(User).get(u)
                groups[g['role']].append(user)

        for rolename, users in groups.items():
            role = DBSession.query(Role).filter(Role.name == rolename).one()
            group = Group(roles=[role, ], users=users)
            project.add_group(group)

        #create CR
        tickets = []
        for cr in appstruct['customer_requests']:
            customer_request = CustomerRequest(name=cr['title'])
            person_types = {
                'junior': 'Junior',
                'senior': 'Senior',
                'graphic': 'Graphic',
                'pm': 'Project manager',
                'architect': 'Architect',
                'tester': 'Tester'
            }
            for key, value in person_types.items():
                if cr[key]:
                    Estimation(person_type=value,
                               days=cr[key],
                               customer_request=customer_request)
            project.add_customer_request(customer_request)
            #BBB define the ticket
            tickets += [{'summary': cr['title'],
                         'customerrequest': customer_request,
                         'reporter': manager.email,
                         'type': 'task',
                         'priority': 'major',
                         'milestone': 'Backlog',
                         'owner': manager.email}]

        #create project management CR and tickets
        project_management_cr = CustomerRequest(name="Project management")
        project.add_customer_request(project_management_cr)
        project_management_tickets = {u'Riesami e Verifiche degli Elementi in Ingresso al progetto':u"""Questo ticket serve sia per 
                i RIESAMI sia per le VERIFICHE del progetto. Il RIESAME risponde alle domande HO TUTTI GLI ELEMENTI PER LAVORARE? 
                STO LAVORANDO SECONDO I REQUISITI DEL CLIENTE? In questo ticket viene registrato l'avvenuto esame degli elementi 
                iniziali (ad esempio: il capitolato tecnico) e di tutti gli elementi emersi in corso d'opera 
                (ad esempio: documenti integrativi). La VERIFICA risponde alle domande HO FATTO TUTTO QUELLO CHE C’ERA DA FARE? 
                SONO PRONTO AL COLLAUDO? Cioè, per capire se la produzione è conclusa, verifico che ciò che ho prodotto sia 
                compatibile con gli input della progettazione. POSSIBILMENTE, CI DOVREBBE ESSERE UN COMMENT CON L'ELENCO DEI 
                DOCUMENTI CONSULTATI, E UN COMMENT PER OGNI FASE DI VERIFICA. TECNICAMENTE, QUESTO TICKET ANDREBBE CHIUSO PRIMA 
                DI PROCEDERE ALLA VALIDAZIONE DEL PROGETTO. """,
                                u'Validazione del progetto': u"""Questo ticket serve per la VALIDAZIONE, step finale del ciclo 
                produttivo, prima della consegna, ovvero la registrazione del fatto che HO COLLAUDATO IL PRODOTTO IN UN CASO D’USO 
                REALE E CI METTO LA FIRMA! La validazione delle singole funzionalità avviene a livello di ticket. Questo ticket 
                viene completato (chiuso) per registrare l'avvenuta validazione del progetto nel suo assieme. """,
                u'project management': u'',
                u'incontri con il cliente': u'',
                u'Punto interno con/tra sviluppatori': u'',
                u'Riesame documentazione di progetto (verification)': u'',
                u'Gestione progetto su Penelope': u''}
        for summary, description in project_management_tickets.items():
          tickets += [{ 'summary': summary,
                        'description': description,
                        'customerrequest': project_management_cr,
                        'reporter': manager.email,
                        'type': 'task',
                        'priority': 'major',
                        'milestone': 'Backlog',
                        'owner': manager.email}]

        #create google docs/folders
        for app_definition in appstruct['google_docs']:
            app = GoogleDoc(name=app_definition['name'],
                            api_uri=app_definition['uri'])
            app.share_with_customer = app_definition['share_with_customer']
            project.add_application(app)

        #create trac
        trac = Trac(name="Trac for %s" % appstruct['project']['project_name'])
        trac.milestones = appstruct['milestones']
        trac.tickets = tickets
        if appstruct['project']['trac_name']:
            trac.project_name = appstruct['project']['trac_name']
        else:
            trac.project_name = appstruct['project']['project_name']
        project.add_application(trac)

        customer.add_project(project)
        raise exc.HTTPFound(location=self.request.fa_url('Customer',
                                                         customer.id))
