# -*- coding: utf-8 -*-
import logging
import bleach
import colander
import deform
from sunburnt import SolrInterface
from pyramid.view import view_config
from pyramid.url import current_route_url
from por.models.dashboard import Trac
from por.models import DBSession
from por.dashboard.lib.widgets import SearchButton, PorInlineForm
from deform_bootstrap.widget import ChosenMultipleWidget

log = logging.getLogger('penelope')


def searchable_tracs(request):
    all_tracs = DBSession().query(Trac)
    # a list of tracs user can view:
    if not request.has_permission('manage', None):
        user_projects = [g.project for g in request.authenticated_user.groups]
        viewable_tracs = []
        for project in user_projects:
            for trac in project.tracs:
                viewable_tracs.append(trac)
    else:
        viewable_tracs = all_tracs

    query = """SELECT DISTINCT '%(trac)s' AS trac_name, '%(project)s' AS project_name FROM "trac_%(trac)s".permission
 WHERE username IN ('internal_developer', '%(user)s')"""

    queries = []
    for trac in viewable_tracs:
        queries.append(query % {'trac': trac.trac_name,
                                'project': trac.project.name,
                                'user': request.authenticated_user.email})
    sql = '\nUNION '.join(queries)
    sql += ';'
    return DBSession().execute(sql).fetchall()


class SearchSchema(colander.MappingSchema):
    tracs = colander.SchemaNode(deform.Set(allow_empty=True),
                                widget=ChosenMultipleWidget(placeholder=u'Select tracs'),
                                missing=colander.null,
                                title=u'')
    realms = colander.SchemaNode(deform.Set(allow_empty=True),
                                widget=ChosenMultipleWidget(placeholder=u'Select realms',
                                            values=[('', ''),
                                                    ('ticket', 'Ticket'),
                                                    ('wiki', 'Wiki'),
                                                    ('changeset','Changeset')]),
                                missing=colander.null,
                                title=u'')
    searchable = colander.SchemaNode(typ=colander.String(),
                            title=u'',
                            widget = deform.widget.TextInputWidget(
                                            css_class=u'input-xxlarge',
                                            placeholder=u'Searchable text'),)


@view_config(route_name='search', permission='search', renderer='skin')
def search(request):

    schema = SearchSchema().bind(request=request)
    form = PorInlineForm(
                schema,
                formid='search',
                method='GET',
                buttons=[SearchButton(title=u'Search'),]
            )

    tracs = searchable_tracs(request)
    form['tracs'].widget.values = [('', '')] + [(t.trac_name, t.project_name) for t in tracs]

    controls = request.GET.items()
    if not controls:
        return {'form': form.render(),
                'results':[]}
    try:
        appstruct = form.validate(controls)
    except deform.ValidationFailure as e:
        return {'form': e.render(),
                'results':[]}

    params = appstruct.copy()
    if not params['tracs']:
        params['tracs'] = [t.trac_name for t in tracs]

    fs = FullTextSearch(request=request, **params)
    results = fs.get_search_results()
    next_url = None
    previous_url = None
    docs = []

    if results:
        docs = [FullTextSearchObject(**doc) for doc in results]
        base_query = dict(request.params)
        records_len = results.result.numFound
        if not fs.page_start + fs.page_size >= records_len: # end of set
            next_query = base_query.copy()
            next_query['page_start'] = fs.page_start + fs.page_size
            next_url = current_route_url(request, _query=next_query)

        if not fs.page_start == 0:
            previous_page = fs.page_start - fs.page_size
            if previous_page < 0:
                previous_page = 0
            previous_query = base_query.copy()
            previous_query['page_start'] = previous_page
            previous_url = current_route_url(request, _query=previous_query)

    return {'docs': docs,
            'next': next_url,
            'form': form.render(appstruct=appstruct),
            'previous': previous_url,
            'results': results}


class FullTextSearch(object):

    def __init__(self, request, tracs=None, searchable=None, realms=None):
        self.request = request
        self.viewable_tracs = list(tracs)
        self.searchable = searchable.split(' ') # always a sequence
        self.realms = list(realms)
        self.solr_endpoint = request.registry.settings.get('por.solr')

    @property
    def page_start(self):
        return int(self.request.params.get('page_start', 0))

    @property
    def page_size(self):
        return 30

    def get_search_results(self,):
        try:
            return self._do_search(sort_by=['-score'])
        except Exception, e:
            log.error("Couldn't perform Full text search, falling back "
                           "to built-in search sources: %s", e)
            return

    def _build_trac_filter(self, si):
        all_tracs = set([a.trac_name for a in DBSession().query(Trac.trac_name)])
        Q = si.query().Q

        def query_include(items):
            if len(items) > 2:
                return Q(project=items.pop()) | query_include(items)
            elif len(items) == 2:
                return Q(project=items.pop()) | Q(project=items.pop())
            elif len(items) == 1:
                return Q(project=items.pop())
            else:
                return ""

        def query_exclude(items):
            if len(items) > 2:
                return ~Q(project=items.pop()) & ~query_exclude(items)
            elif len(items) == 2:
                return ~Q(project=items.pop()) & ~Q(project=items.pop())
            elif len(items) == 1:
                return ~Q(project=items.pop())
            else:
                return ""

        # if viewable_tracs are > (all_tracs / 2)
        # let's exclude
        if len(self.viewable_tracs) > (len(all_tracs) / 2):
            return query_exclude(all_tracs.difference(self.viewable_tracs))
        # in other cases
        # let's use include
        else:
            return query_include(self.viewable_tracs)

    def _build_realm_filter(self, si):

        Q = si.query().Q

        def query(items):
            if len(items) > 2:
                return Q(realm=items.pop()) | query(items)
            elif len(items) == 2:
                return Q(realm=items.pop()) | Q(realm=items.pop())
            elif len(items) == 1:
                return Q(realm=items.pop())
            else:
                return ""
        return query(self.realms)

    def _do_search(self, sort_by=None):
        si = SolrInterface(self.solr_endpoint)
        query = si.query().field_limit(score=True)

        for searchterm in self.searchable:
            query = query.query(searchterm)

        realm_query = self._build_realm_filter(si)
        if realm_query:
            query = query.filter(realm_query)

        trac_query = self._build_trac_filter(si)
        if trac_query:
            query = query.filter(trac_query)

        for field in sort_by or []:
            query = query.sort_by(field)

        return query.paginate(start=self.page_start, rows=self.page_size)\
                            .highlight('oneline',
                                    **{'simple.pre':'<span class="highlight">',
                                       'simple.post':'</span>'})\
                            .highlight('title',
                                    **{'simple.pre':'<span class="highlight">',
                                       'simple.post':'</span>'})\
                            .execute()

    def _docs(self, query):
        """Return a generator of all the docs in query.
        """
        i = 0
        while True:
            response = query.paginate(start=i, rows=self.page_size)\
                            .highlight('oneline',
                                    **{'simple.pre':'<span class="highlight">',
                                       'simple.post':'</span>'})\
                            .highlight('title',
                                    **{'simple.pre':'<span class="highlight">',
                                       'simple.post':'</span>'})\
                            .execute()
            for doc in response:
                yield doc
            if len(response) < self.page_size:
                break
            i += self.page_size


class FullTextSearchObject(object):
    '''Minimal behaviour class to store documents going to/comping from Solr.
    '''
    def __init__(self, project, realm, id=None, score=None,
                 title=None, author=None, changed=None, created=None,
                 oneline=None, involved=None, popularity=None, comments=None,
                 parent_id=None, solr_highlights=None , **kwarg):

        if not involved:
            involved = ()
        if not author:
            author = ()
        self.project = project
        self.author = ', '.join(author + involved)
        self.created = created
        self.popularity = popularity
        self.comments = comments
        self.realm = realm
        self.solr_highlights = solr_highlights
        self._title = ''.join(title)
        self._oneline = oneline
        self.id = id
        self.score = score
        self.parent_id = parent_id

    @property
    def title(self):
        result = []
        if self.solr_highlights:
            result = self.solr_highlights.get('title')
        if not result:
            result = self._title
        text = ''.join(result)
        return bleach.clean(text, ['span'], ['class'], strip=True)

    @property
    def oneline(self):
        result = []
        if self.solr_highlights:
            result = self.solr_highlights.get('oneline')
        if not result:
            result = self._oneline
        text = ''.join(result)
        return bleach.clean(text, ['span'], ['class'], strip=True)

    def href(self):
        if self.realm == 'changeset':
            return "trac/%s/%s/%s/%s" % (self.project, self.realm, self.id, self.parent_id)
        else:
            return "trac/%s/%s/%s" % (self.project, self.realm, self.id)
