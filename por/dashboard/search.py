# -*- coding: utf-8 -*-
import logging
from sunburnt import SolrInterface
from pyramid.view import view_config
#from por.models.dashboard import Trac
#from por.models import DBSession

log = logging.getLogger('penelope')


@view_config(route_name='search', permission='manage', renderer='skin')
def search(request):
#    tracs = [a.trac_name for a in DBSession().query(Trac.trac_name)\
#                                             .filter_by(searchable=True)]
    tracs = []
    fs = FullTextSearch()
    results = fs.get_search_results(request.params.get('searchable'),
                                   trac_ids=tracs)
    return {'results':results}


class FullTextSearch(object):

    solr_endpoint = 'http://localhost:8983/solr/'

    def get_search_results(self, terms, trac_ids=None):
        try:
            query, response = self._do_search(terms, trac_ids)
        except Exception, e:
            log.error("Couldn't perform Full text search, falling back "
                           "to built-in search sources: %s", e)
            return
        return (FullTextSearchObject(**doc) for doc in self._docs(query))

    def _build_filter_query(self, si, trac_ids):
        Q = si.query().Q
        def rec(list1):
            if len(list1) > 2:
                return Q(project=list1.pop()) | rec(list1)
            elif len(list1) == 2:
                return Q(project=list1.pop()) | Q(project=list1.pop())
            elif len(list1) == 1:
                return Q(project=list1.pop())
            else:
                # NB A TypeError will be raised if this string is combined
                #    with a LuceneQuery
                return ""
        return rec(trac_ids[:])

    def _do_search(self, terms, trac_ids, facet='realm', sort_by=None,
                                         field_limit=None):

        si = SolrInterface(self.solr_endpoint)
        if trac_ids:
            filter_q = self._build_filter_query(si, trac_ids)
            query = si.query(terms).filter(filter_q)
        else:
            query = si.query(terms)

        # The index can store multiple projects, restrict results to this one
        #filter_q &= si.query().Q(project=self.project)

        # Construct a query that searches for terms in docs that match chosen
        # realms and current project

        if facet:
            query = query.facet_by(facet)
        for field in sort_by or []:
            query = query.sort_by(field)
        if field_limit:
            query = query.field_limit(field_limit)

        # Submit the query to Solr, response contains the first 10 results
        response = query.execute()
        if facet:
            log.debug("Facets: %s", response.facet_counts.facet_fields)

        return query, response

    def _docs(self, query, page_size=10):
        """Return a generator of all the docs in query.
        """
        i = 0
        while True:
            response = query.paginate(start=i, rows=page_size).execute()
            for doc in response:
                yield doc
            if len(response) < page_size:
                break
            i += page_size


class FullTextSearchObject(object):
    '''Minimal behaviour class to store documents going to/comping from Solr.
    '''
    def __init__(self, project, realm, id=None,
                 parent_realm=None, parent_id=None,
                 title=None, author=None, changed=None, created=None,
                 oneline=None, tags=None, involved=None,
                 popularity=None, body=None, comments=None, action=None,
                 **kwarg):
        self.project = project
        self.title = ''.join(title)
        self.author = author
        self.oneline = oneline
        self.tags = tags
        self.involved = involved
        self.popularity = popularity
        self.body = body
        self.comments = comments
        self.action = action
        self.realm = realm
        self.id = id

    def href(self):
        return "%s/%s/%s" % (self.project, self.realm, self.id)
