import colander
import deform
from deform import ValidationFailure
from pyramid.renderers import get_renderer
from pyramid import httpexceptions as exc
from por.dashboard.lib.widgets import SubmitButton, ResetButton, WizardForm

class Tickets(colander.SequenceSchema):
    class Ticket(colander.Schema):
          """
              summary: entered by user
              description: entered by user in wiki syntax
              customerrequest: the context,
              reporter: user's email,
              type: 'task',
              priority: 'major',
              milestone: 'Backlog' (choosen for the available ones in trac?)
              owner: user's email
          """
          summary = colander.SchemaNode(typ=colander.String(),
                             widget=deform.widget.TextInputWidget(placeholder=u'Summary'),
                             missing=colander.required,
                             title=u'')
          description = colander.SchemaNode(
                             colander.String(),
                             widget=deform.widget.TextAreaWidget(
                                  placeholder=u'Describe the ticket (wiki syntax)',
                                  cols=60,
                                  rows=5),
                             title=u'')

    tickets = Ticket(title='')


class FastTicketingSchema(colander.Schema):
    tickets = Tickets()


class FastTicketing(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def render(self):
        result = {}
        result['main_template'] = get_renderer(
                'por.dashboard:skins/main_template.pt').implementation()
        result['main'] = get_renderer(
                'por.dashboard.forms:templates/master.pt').implementation()

        schema = FastTicketingSchema().clone()
        form = WizardForm(schema,
                          formid='fastticketing',
                          method='POST',
                          buttons=[
                                 SubmitButton(title=u'Submit'),
                                 ResetButton(title=u'Reset'),
                          ])
        form['tickets'].widget = deform.widget.SequenceWidget(min_len=1)
        
        controls = self.request.POST.items()
        if controls != []:
            try:
                appstruct = form.validate(controls)
                self.handle_save(appstruct)
            except ValidationFailure as e:
                result['form'] = e.render()
                return result


        result['form'] = form.render()
        return result
    
    def handle_save(self, appstruct):
      customerrequest = self.context.get_instance()

      import pdb; pdb.set_trace()
      raise exc.HTTPFound(location=self.request.fa_url('CustomerRequest',
                                                         customerrequest.id))
