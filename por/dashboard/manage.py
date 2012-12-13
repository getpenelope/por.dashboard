# -*- coding: utf-8 -*-

import zope.component
from zope.interface import implements
from pyramid.view import view_config
from pyramid.renderers import get_renderer
from por.dashboard.sidebar import SidebarRenderer, HeaderSidebarAction, SidebarAction
from por.dashboard.interfaces import ISidebar
from por.dashboard.interfaces import IManageView
from por.dashboard.views import DefaultContext


class ManageContext(DefaultContext):
    "Default context factory for Manage views."
    implements(IManageView)


class ManageSidebarRenderer(SidebarRenderer):

    def render(self, request):
        self.actions.append(HeaderSidebarAction('manage',content=u'Manage penelope', permission='manage', no_link=True))
        self.actions.append(SidebarAction('manage_users',
                                          content=u'Manage users',
                                          permission='manage',
                                          attrs=dict(href="'%s/admin/User' % request.application_url")))
        self.actions.append(SidebarAction('manage_roles',
                                          content=u'Manage roles',
                                          permission='manage',
                                          attrs=dict(href="'%s/admin/Role' % request.application_url")))
        self.actions.append(SidebarAction('manage_groups',
                                          content=u'Manage groups',
                                          permission='manage',
                                          attrs=dict(href="'%s/admin/Group' % request.application_url")))
        actions = self.actions.render(request)
        template =  get_renderer('por.dashboard.forms:templates/project_sidebar.pt').implementation()
        return template(actions=actions,
                        request=request)

gsm = zope.component.getGlobalSiteManager()
gsm.registerAdapter(ManageSidebarRenderer, (IManageView,), ISidebar)


@view_config(route_name='administrator', permission='manage', renderer='skin')
def manage_home(request):
    return {}

