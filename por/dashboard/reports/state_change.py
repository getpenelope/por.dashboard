# -*- coding: utf-8 -*-

import collections
import logging

import colander
import sqlalchemy as sa
from sqlalchemy.orm import lazyload
from repoze.workflow import get_workflow, WorkflowError
from webhelpers.html.builder import HTML

from deform import ValidationFailure
from pyramid.renderers import render
from pyramid.view import view_config

from por.dashboard import fanstatic_resources
from por.dashboard.lib.helpers import ticket_url, unicodelower
from por.dashboard.lib.widgets import SearchButton, PorInlineForm
from por.dashboard.reports import fields
from por.dashboard.reports.queries import qry_active_projects, te_filter_by_customer_requests, NullCustomerRequest, filter_users_with_timeentries
from por.dashboard.reports.validators import validate_period
from por.dashboard.reports.favourites import render_saved_query_form

from por.models import DBSession, Project, TimeEntry, User, CustomerRequest, Contract
from por.models.tickets import ticket_store

log = logging.getLogger(__name__)



class StateChangeReport(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


    class StateChangeSchema(colander.MappingSchema):
        customer_id = fields.customer_id.clone()

        project_id = fields.project_id.clone()
        date_from = fields.date_from.clone()
        date_to = fields.date_to.clone()
        users = fields.users.clone()
        customer_requests = fields.customer_requests.clone()
        workflow_states = fields.workflow_states.clone()
        invoice_number = fields.invoice_number.clone()


    def search(self, customer_id, project_id, date_from, date_to,
               users, customer_requests, invoice_number, workflow_states):

        # also search archived projects, if none are specified
        qry = DBSession.query(TimeEntry).join(TimeEntry.project).join(Project.customer).outerjoin(TimeEntry.author)
        qry = qry.options(lazyload(TimeEntry.project, TimeEntry.author, Project.customer))

        if customer_id is not colander.null:
            qry = qry.filter(Project.customer_id == customer_id)

        if project_id is not colander.null:
            qry = qry.filter(TimeEntry.project_id == project_id)

        if date_from is not colander.null:
            qry = qry.filter(TimeEntry.date>=date_from)

        if date_to is not colander.null:
            qry = qry.filter(TimeEntry.date<=date_to)

        if users:
            qry = qry.filter(TimeEntry.author_id.in_(users))

        if invoice_number:
            qry = qry.filter(TimeEntry.invoice_number==invoice_number)

        if workflow_states:
            qry = qry.filter(TimeEntry.workflow_state.in_(workflow_states))

        qry = qry.filter(te_filter_by_customer_requests(customer_requests, request=self.request))

        qry = qry.order_by(sa.desc(TimeEntry.date), sa.desc(TimeEntry.start), sa.desc(TimeEntry.creation_date))

        time_entries = self.request.filter_viewables(qry)

        proj_tickets = collections.defaultdict(set)
        for te in time_entries:
            if te.ticket is None:
                continue
            proj_tickets[te.project_id].add(te.ticket)

        # projectsmap = {
        #    'project_id': {
        #         'ticket_id': 'customer_request_id',
        #         ...
        #    },
        #    ...
        # }

        projectsmap = {}
        for project_id, ticket_ids in proj_tickets.items():
            project = DBSession.query(Project).get(project_id)
            projectsmap[project_id] = dict(ticket_store.get_requests_from_tickets(
                                            project, tuple(ticket_ids), request=self.request))

        tkts = {}
        for project_id, ticket_ids in proj_tickets.items():
            project = DBSession.query(Project).get(project_id)
            for tkt in ticket_store.get_tickets_for_project(project, request=self.request):
                tkts[(project_id, tkt['id'])] = tkt

        entries_tree = collections.defaultdict(lambda: collections.defaultdict(list))

        cr_get = DBSession.query(CustomerRequest).get

        # one nullcr for each project, to better group them
        nullcrs = dict(
                (project, NullCustomerRequest(project=project))
                for project in DBSession.query(Project)
                )


        for te in time_entries:
            if te.ticket is None:
                customer_request = nullcrs[project]
            else:
                cr_id = projectsmap[te.project_id].get(te.ticket)
                if not cr_id:
                    continue
                customer_request = cr_get(cr_id) or nullcrs[project]

            entry = {
                        'customer': te.project.customer.name.strip(),
                        'project': te.project.name.strip(),
                        'user': te.author.fullname.strip(),
                        'date': te.date.strftime('%Y-%m-%d'),
                        'contract': te.contract,
                        'description': te.description,
                        'hours_str': te.hours_str,
                        'workflow_state': te.workflow_state,
                        'tickettype': te.tickettype,
                        'invoice_number': te.invoice_number,
                        'location': te.location,
                        'id': te.id,
                    }

            if te.ticket is None:
                ticket_description = '(no ticket)'
            else:
                tkt = tkts[(te.project_id, te.ticket)]
                href = ticket_url(request=self.request,
                                  project=te.project,
                                  ticket_id=te.ticket)
                ticket_description = HTML.SPAN(
                                            HTML.A('#%(id)s - %(summary)s' % tkt, href=href),
                                            ' ',
                                            HTML.SUP(tkt['type']),
                                            )

            entries_tree[customer_request][ticket_description].append(entry)

        return {
                'entries_tree': entries_tree,
                }



    def state_contract_change(self):
        new_state = self.request.POST['new_state']
        new_contract = self.request.POST['new_contract']
        invoice_number = self.request.POST['invoice_number']

        te_ids = set(int(s[3:])
                     for s, checkbox_state in self.request.POST.iteritems()
                     if s.startswith('te_') and checkbox_state=='on')

        qry = DBSession.query(TimeEntry).filter(TimeEntry.id.in_(te_ids))

        done_state = set()
        done_contract = set()
        errors = {}

        for te in qry:
            if new_state:
                try:
                    workflow = get_workflow(te, te.__class__.__name__)
                    workflow.transition_to_state(te, self.request, new_state, skip_same=True)
                    done_state.add(te.id)
                    if new_state == 'invoiced' and invoice_number:
                        te.invoice_number = invoice_number
                except WorkflowError as msg:
                    errors[te.id] = msg
            if new_contract:
                done_contract.add(te.id)
                te.contract_id = new_contract

        return done_state, done_contract, errors


    @view_config(name='report_state_change', route_name='reports', renderer='skin', permission='reports_state_change')
    def __call__(self):

        done_state = set()
        done_contract = set()
        errors = {}
        if self.request.POST:
            done_state, done_contract, errors = self.state_contract_change()
            if done_state:
                self.request.add_message('State changed for %d time entries.' % len(done_state))
            if done_contract:
                self.request.add_message('Contract changed for %d time entries.' % len(done_contract))

        # GET parameters for the search form

        fanstatic_resources.report_te_state_change.need()
        schema = self.StateChangeSchema(validator=validate_period).clone()
        projects = self.request.filter_viewables(qry_active_projects())

        # select customers that have some active project
        customers = self.request.filter_viewables(sorted(set(p.customer for p in projects), key=unicodelower))

        users = DBSession.query(User).order_by(User.fullname)
        users = filter_users_with_timeentries(users)
        customer_requests = self.request.filter_viewables(DBSession.query(CustomerRequest).order_by(CustomerRequest.name))

        form = PorInlineForm(schema,
                             formid='te_state_change',
                             method='GET',
                             buttons=[
                                 SearchButton(title=u'Search'),
                             ])

        workflow = get_workflow(TimeEntry(), 'TimeEntry')

        all_wf_states = [
                            (state, workflow._state_data[state]['title'] or state)
                            for state in workflow._state_order
                        ]

        form['workflow_states'].widget.values = all_wf_states
        # XXX the following validator is broken
        form['workflow_states'].validator = colander.OneOf([str(ws[0]) for ws in all_wf_states])

        form['customer_id'].widget.values = [('', '')] + [(str(c.id), c.name) for c in customers]
        # don't validate as it might be an archived customer
        form['project_id'].widget.values = [('', '')] + [(str(p.id), p.name) for p in projects]
        # don't validate as it might be an archived project

        form['users'].widget.values = [(str(u.id), u.fullname) for u in users]
        # XXX the following validator is broken
        form['users'].validator = colander.OneOf([str(u.id) for u in users])

        form['customer_requests'].widget.values = [(str(c.id), c.name) for c in customer_requests]
        # XXX the following validator is broken
        form['customer_requests'].validator = colander.OneOf([str(c.id) for c in customer_requests])

        controls = self.request.GET.items()

        if not controls:
            # the form is empty
            return {
                    'form': form.render(),
                    'saved_query_form': render_saved_query_form(self.request),
		    'qs':'',
                    'result_table': '',
                    }

        try:
            appstruct = form.validate(controls)
        except ValidationFailure as e:
            return {
                    'form': e.render(),
                    'saved_query_form': render_saved_query_form(self.request),
		    'qs':'',
                    'result_table': '',
                    }

        entries_detail = self.search(**appstruct)

        all_contracts = DBSession().query(Contract.id, Contract.name).all()

        result_table = render('por.dashboard:reports/templates/state_change.pt',
                              {
                                  'entries_tree': entries_detail['entries_tree'],
                                  'all_wf_states': all_wf_states,
                                  'all_contracts': all_contracts,
                                  'wf_state_names': dict((ws[0], ws[1]) for ws in all_wf_states),
                                  'done_state': done_state,
                                  'done_contract': done_contract,
                                  'errors': errors,
                              },
                              request=self.request)

        return {
                'form': form.render(appstruct=appstruct),
                'saved_query_form': render_saved_query_form(self.request),
		'qs': self.request.query_string,
                'result_table': result_table,
                }

