# -*- coding: utf-8 -*-

from copy import deepcopy

from pyramid import httpexceptions as exc

from js.jqgrid import jqgrid, jqgrid_i18n_en
from fa.bootstrap import actions

from por.dashboard.forms import ModelView
from por.dashboard.forms import workflow
from por.models import dashboard


def configurate(config):
    config.formalchemy_model_view('admin',
                                  request_method='GET',
                                  permission='view',
                                  name='',
                                  attr='show',
                                  renderer='fa.bootstrap:templates/admin/show.pt',
                                  model='por.models.dashboard.CustomerRequest',
                                  view=CustomerRequestModelView)

    config.formalchemy_model_view('admin',
                                  request_method='POST',
                                  permission='delete',
                                  name='delete',
                                  attr='delete',
                                  renderer='fa.bootstrap:templates/admin/edit.pt',
                                  model='por.models.dashboard.CustomerRequest',
                                  view=CustomerRequestModelView)

    config.formalchemy_model_view('admin',
                                  renderer='fa.bootstrap:templates/admin/listing.pt',
                                  context='pyramid_formalchemy.resources.ModelListing',
                                  attr='listing',
                                  request_method='GET',
                                  permission='view',
                                  model='por.models.dashboard.CustomerRequest',
                                  view=CustomerRequestListingView)

    config.formalchemy_model_view('admin',
                                  request_method='GET',
                                  permission='workflow',
                                  name='goto_state',
                                  model='por.models.dashboard.CustomerRequest',
                                  view=workflow.goto_state)

    config.formalchemy_model_view('admin',
                                  request_method='GET',
                                  permission='estimations',
                                  name='estimations.json',
                                  renderer='json',
                                  attr='get_estimations',
                                  model='por.models.dashboard.CustomerRequest',
                                  view=CustomerRequestModelView)

    config.formalchemy_model_view('admin',
                                  request_method='POST',
                                  permission='estimations',
                                  name='estimations.json',
                                  renderer='json',
                                  attr='put_estimations',
                                  model='por.models.dashboard.CustomerRequest',
                                  view=CustomerRequestModelView)

    config.formalchemy_model_view('admin',
                                  request_method='GET',
                                  permission='estimations',
                                  name='estimations',
                                  attr='estimations',
                                  model='por.models.dashboard.CustomerRequest',
                                  renderer='por.dashboard.forms:templates/estimations.pt',
                                  view=CustomerRequestModelView)

    config.formalchemy_model_view('admin',
                                  request_method='GET',
                                  permission='view',
                                  name='tickets',
                                  attr='tickets',
                                  model='por.models.dashboard.CustomerRequest',
                                  renderer='por.dashboard.forms:templates/customer_request_tickets.pt',
                                  view=CustomerRequestModelView)


customer_request_tabs = actions.TabsActions(actions.TabAction("show",
                                                              content="View",
                                                              permission='view',
                                                              attrs=dict(href="request.fa_url(request.model_name, request.model_id, '')")),
                                            actions.TabAction("tickets",
                                                              content="Tickets",
                                                              permission='view',
                                                              attrs=dict(href="request.fa_url(request.model_name, request.model_id, 'tickets')")),
                                            actions.TabAction("estimations",
                                                              content="Estimations",
                                                              permission='estimations',
                                                              attrs=dict(href="request.fa_url(request.model_name, request.model_id, 'estimations')")),)


add_ticket = actions.UIButton(id='add_ticket',
                              content='Add ticket',
                              permission='view',
                              _class='btn btn-success',
                              attrs=dict(href="request.model_instance.add_ticket_url(request)"))


class CustomerRequestListingView(ModelView):
    defaults_actions = deepcopy(actions.defaults_actions)
    defaults_actions.update(listing_buttons = actions.Actions())


class CustomerRequestModelView(ModelView):
    actions_categories = ('buttons', 'tabs')
    defaults_actions = deepcopy(actions.defaults_actions)

    def __init__(self, *args, **kwargs):
        super(CustomerRequestModelView, self).__init__(*args, **kwargs)
        self.defaults_actions.update(show_buttons=actions.Actions(actions.edit))
        cr_actions = deepcopy(customer_request_tabs)
        wf = workflow.change_workflow(self.context)
        if wf:
            cr_actions.append(wf)
        self.defaults_actions.update(show_tabs = cr_actions)
        self.defaults_actions.update(estimations_tabs = cr_actions)
        self.defaults_actions['show_buttons'].append(add_ticket)

    def delete(self):
        cr = self.context.get_instance()
        if len(cr.get_tickets(self.request)):
            request = self.request
            request.add_message(u'Customer request has tickets. Please remove them first.', type='danger')
            raise exc.HTTPFound(location=request.fa_url('CustomerRequest', cr.id))
        else:
            return self.force_delete()

    @actions.action('estimations')
    def estimations(self):
        """Use http://trirand.com/blog grid widget """
        jqgrid_i18n_en.need()
        jqgrid.need()
        return self.render()

    @actions.action('estimations')
    def tickets(self):
        """Use iframe to render tickets """
        tracs = list(self.request.model_instance.project.tracs)
        if not tracs:
            return None
        trac_url = tracs[0].application_uri(self.request)
        customer_request_id = self.request.model_instance.id
        report_url = '%s/query?customerrequest=%s&iframe=true' % (trac_url, customer_request_id)
        return self.render(report_url=report_url)

    def put_estimations(self):
        self.request.model_class = dashboard.Estimation
        self.request.model_name = 'Estimation'
        customer_request_id = self.request.model_instance.id
        response = {'success': True}

        self.data = self.request.POST
        obj_id = self.data.pop('id')
        if obj_id == u'_empty':
            obj_id = ''
        else:
            self.request.model_instance = self.session.query(dashboard.Estimation).get(obj_id)

        action = self.data.pop('oper')

        def process(session=None):
            self.data = dict([('Estimation-%s-%s' % (obj_id, k),v) for k,v in self.data.items()])
            self.data['Estimation-%s-customer_request_id' % obj_id] = customer_request_id
            if session:
                self.fs = self.fs.bind(data=self.data, session=self.session, request=self.request)
            else:
                self.fs = self.fs.bind(data=self.data, request=self.request)
            if self.validate(self.fs):
                self.fs.sync()
                return {'success': True}
            else:
                return {'success': False, 'message': 'Validation error'}

        def add():
            self.fs = self.get_fieldset()
            return process(session=self.session)

        def edit():
            self.fs = self.get_fieldset(id=obj_id)
            msg = process()
            self.sync(self.fs, obj_id)
            return msg

        def delete():
            record = self.request.model_instance
            if record:
                self.session.delete(record)

        if action == 'add': response = add()
        elif action == 'edit': response = edit()
        elif action == 'del': delete()

        self.session.flush()

        return response

    def get_estimations(self):
        """
        Return json for the grid:

          {"records":"13",
           "rows":[
             {"id":"1","cell":["1","2007-10-01","Client 1","100.00","20.00","120.00","note 1"]}],
          }
        """
        items = self.request.model_instance.estimations
        total_days = sum([a.days for a in items])
        len_items = len(items)

        resp = {'records': len_items,
                'userdata':{"days":total_days,
                            "person_type":"Totals:"},
                'rows':[]}

        for item in items:
            resp['rows'].append({'id': str(item.id), 'cell':[item.person_type,
                                                             item.days]})
        return resp

