# -*- coding: utf-8 -*-

from json import loads
from copy import deepcopy
from pyramid_formalchemy import actions
from fa.bootstrap import actions as factions
from por.dashboard.forms import ModelView
from por.dashboard.fanstatic_resources import kanban
from por.models.dashboard import Trac, Project
from por.models import DBSession


def configurate(config):
    config.formalchemy_model_view('admin',
            request_method='GET',
            permission='view',
            name='',
            attr='show',
            renderer='por.dashboard.forms:templates/kanbanboard.pt',
            model='por.models.dashboard.KanbanBoard',
            view=KanbanBoardModelView)

    config.formalchemy_model_view('admin',
        request_method='POST',
        permission='delete',
        name='delete',
        attr='delete',
        renderer='fa.bootstrap:templates/admin/edit.pt',
        model='por.models.dashboard.KanbanBoard',
        view=KanbanBoardModelView)

    config.formalchemy_model_view('admin',
            request_method='GET',
            permission='view',
            name='get_board_data.json',
            attr='get_board_data',
            renderer='json',
            model='por.models.dashboard.KanbanBoard',
            view=KanbanBoardModelView)

    config.formalchemy_model_view('admin',
            request_method='POST',
            permission='edit',
            name='set_board_data.json',
            attr='set_board_data',
            renderer='json',
            model='por.models.dashboard.KanbanBoard',
            view=KanbanBoardModelView)

add_column = factions.UIButton(id='add_col',
            content='Add column',
            permission='view',
            _class='btn btn-primary',
            attrs=dict(href="'#'"))

remove_column = factions.UIButton(id='remove_col',
            content='Remove column',
            permission='view',
            _class='btn btn-danger',
            attrs=dict(href="'#'"))


def find_tickets(request):
    all_tracs = DBSession.query(Trac).join(Project).filter(Project.active)
    query = """SELECT DISTINCT '%(trac)s' AS trac_name, '%(project)s' as project, id AS ticket, summary  FROM "trac_%(trac)s".ticket WHERE owner='%(email)s' AND status!='closed'"""
    queries = []
    for trac in all_tracs:
        queries.append(query % {'trac': trac.trac_name,
                                'project': trac.project,
                                'email': request.authenticated_user.email})
    sql = '\nUNION '.join(queries)
    sql += ';'
    tracs =  DBSession().execute(sql).fetchall()
    return tracs


class KanbanBoardModelView(ModelView):
    actions_categories = ('buttons',)
    defaults_actions = deepcopy(factions.defaults_actions)
    defaults_actions['show_buttons'] = factions.Actions(factions.edit, add_column, remove_column)

    @actions.action()
    def show(self):
        kanban.need()
        return super(KanbanBoardModelView, self).show()

    def get_board_data(self):
        try:
            boards = loads(self.context.get_instance().json)
        except (ValueError, TypeError):
            boards = []

        existing_tickets = [[b['id'] for b in a['tasks']] for a in boards]
        existing_tickets = [item for sublist in existing_tickets for item in sublist]

        backlog = {'title': 'Backlog',
                   'wip': 0,
                   'tasks': []}

        ticket_text = ("<strong><a target='_blank' href='%(url)s'>%(project)s #%(ticket)s</a>"
                       "</strong><br/>%(summary)s")

        for ticket in find_tickets(self.request):
            ticket_id = '%s_%s' % (ticket.trac_name, ticket.ticket)
            opts = {'project': ticket.project,
                    'url': '%s/trac/%s/ticket/%s' % (self.request.application_url,
                                                     ticket.trac_name,
                                                     ticket.ticket),
                    'ticket': ticket.ticket,
                    'summary': ticket.summary}
            if ticket_id not in existing_tickets:
                backlog['tasks'].append({'id': ticket_id,
                                         'text': ticket_text % opts})
        boards.insert(0, backlog)
        return boards

    def set_board_data(self):
        self.context.get_instance().json = self.request.params.get('board')
        return 'OK'

    def delete(self):
        """
        For Application we are always forcing to delete.
        No additional validation
        """
        return self.force_delete()
