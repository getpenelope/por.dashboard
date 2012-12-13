# -*- coding: utf-8 -*-

from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings, set_cache_regions_from_settings
from zope.component import getGlobalSiteManager
from pyramid.authentication import RepozeWho1AuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_skins.renderer import renderer_factory

try:
    import pyinotify; pyinotify
    DISCOVERY = True
except ImportError:
    DISCOVERY = False


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    globalreg = getGlobalSiteManager()
    set_cache_regions_from_settings(settings)
    config = Configurator(registry=globalreg)

    config.include('pyramid_zcml')
    config.load_zcml('workflow.zcml')
    config.add_translation_dirs('por.dashboard:locale')

    from por.dashboard.views import PORRequest
    config.setup_registry(settings=settings,
                          request_factory=PORRequest,
                          root_factory='por.dashboard.views.DefaultContext')

    # por security
    from por.dashboard import security
    authentication_policy = RepozeWho1AuthenticationPolicy(identifier_name="auth_tkt",callback=security.rolefinder)
    config._set_authentication_policy(authentication_policy)
    authorization_policy = ACLAuthorizationPolicy()
    config._set_authorization_policy(authorization_policy)
    config.scan('por.dashboard.security.views')
    config.include('por.dashboard.security.openid2')
    config.include('velruse.store.memstore')
    config.add_view('por.dashboard.security.views.forbidden', renderer='skin', context="pyramid.httpexceptions.HTTPForbidden")

    #mailier
    config.include('pyramid_mailer')

    # por.models's configuration
    config.include('por.models')
    import por.dashboard.events; por.dashboard.events
    import por.dashboard.breadcrumbs; por.dashboard.breadcrumbs
    import por.dashboard.sidebar; por.dashboard.sidebar

    session_factory = session_factory_from_settings(settings)
    config.set_session_factory(session_factory)

    config.add_static_view('static', 'por.dashboard:static')
    config.scan('por.dashboard.views')

    config.add_route('tp', '/tp/*traverse', factory='por.dashboard.tp.TPContext')
    config.scan('por.dashboard.tp')
    config.scan('por.dashboard.smartadd')
    config.scan('por.dashboard.backlog')

    config.add_route('administrator', '/manage', factory='por.dashboard.manage.ManageContext')
    config.scan('por.dashboard.manage')

    config.add_route('reports', '/reports/*traverse', factory='por.dashboard.reports.ReportContext')
    config.scan('por.dashboard.reports')
    config.add_renderer(name='xls_report', factory='por.dashboard.renderers.XLSReportRenderer')
    config.add_renderer(name='csv_report', factory='por.dashboard.renderers.CSVReportRenderer')

    config.include('pyramid_rpc.jsonrpc')
    config.add_jsonrpc_endpoint('DashboardAPI', '/apis/json/dashboard')
    config.scan('por.dashboard.api')

    config.add_renderer('skin', renderer_factory)
    config.include('pyramid_skins')
    config.register_path("por.dashboard:skins", discovery=DISCOVERY)

    # por.gdata configuration
    config.include('por.gdata')

    # por.trac configuration
    # config.include('por.trac')

    # pyramid_formalchemy's configuration
    config.include('pyramid_formalchemy')
    config.include('fa.bootstrap')
    config.include('deform_bootstrap')

    config.formalchemy_admin('admin',
                             package='por.dashboard',
                             factory='por.dashboard.forms.CrudModels',
                             models='por.models',
                             view='por.dashboard.forms.ModelView',
                             session_factory='por.models.DBSession')

    config.add_view(context='pyramid_formalchemy.resources.ModelListing',
                    renderer='fa.bootstrap:templates/admin/new.pt',
                    request_method='POST',
                    route_name='admin',
                    request_type='por.dashboard.interfaces.IPorRequest',
                    view='por.dashboard.forms.security_create')

    config.add_static_view('deform_static', 'deform:static')
    config.add_route('navbar', '/navbar')
    config.add_route('favicon', '/favicon.ico')

    from por.dashboard.forms import include_forms
    include_forms(config)

    return config.make_wsgi_app()
