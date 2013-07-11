import redis
import transaction
from json import loads, dumps
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from pyramid.view import view_config
from pyramid.response import Response
from por.models.dashboard import KanbanBoard
from por.models.dashboard import Trac, Project
from por.models import DBSession


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


class KanbanNamespace(BaseNamespace):

    def initialize(self):
        self.session['board_id'] = None
        self.spawn(self.job_send_board)
#        self.spawn(self.listener)

    def listener(self):
        r = redis.StrictRedis()
        r = r.pubsub()
        r.subscribe('board_changed')
        for m in r.listen():
            if m['type'] == 'message':
                self.job_send_board(m['data'])

    def on_board_id(self, board_id):
        self.session['board_id'] = board_id

    def on_board_changed(self, data):
        board_id = self.session['board_id']
        if not board_id:
            return
        # cleanup data - make sure we will not save empty tasks
        for col in data:
            to_remove = []
            for n, task in enumerate(col['tasks']):
                if not 'id' in task:
                    to_remove.append(n)
            to_remove.reverse()
            for n in to_remove:
                col['tasks'].pop(n)

        with transaction.manager:
            board = DBSession().query(KanbanBoard).get(board_id)
            board.json = dumps(data)
            r = redis.Redis()
            r.publish('board_changed', board_id)
        print "BOARD SAVED", board_id

    def job_send_board(self, board_id=None):
        if not board_id:
            board_id = self.session['board_id']
        if not board_id:
            return ''

        board = DBSession().query(KanbanBoard).get(board_id)
        try:
            boards = loads(board.json)
        except (ValueError, TypeError):
            boards = []

        existing_tickets = [[b['id'] for b in a['tasks'] if b.get('id')] for a in boards]
        existing_tickets = [item for sublist in existing_tickets for item in sublist]

        backlog = {'title': 'Backlog',
                   'wip': 0,
                   'tasks': []}

        limit = 10
        for n, ticket in enumerate(find_tickets(self.request)):
            if n > limit:
                break
            ticket_id = '%s_%s' % (ticket.trac_name, ticket.ticket)
            if ticket_id not in existing_tickets:
                backlog['tasks'].append({'id': ticket_id,
                                         'project': ticket.project,
                                         'url': '%s/trac/%s/ticket/%s' % (self.request.application_url,
                                                                          ticket.trac_name,
                                                                          ticket.ticket),
                                         'ticket': ticket.ticket,
                                         'summary': ticket.summary})

        boards.insert(0, backlog)
        self.emit("columns", {"value": boards})


@view_config(route_name="socketio")
def socketio(request):
    socketio_manage(request.environ, {"/kanban": KanbanNamespace}, request=request)
    return Response('')
