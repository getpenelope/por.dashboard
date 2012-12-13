# -*- coding: utf-8 -*-
from zope.interface import implements

from pyramid_formalchemy import resources
from por.dashboard.interfaces import IManageView


def configurate(config):
    #custom view for role
    config.formalchemy_model_view('admin',
        view='por.dashboard.forms.ModelView',
        context=ModelListing,
        model='por.models.dashboard.Role',
        renderer='pyramid_formalchemy:templates/admin/listing.pt',
        attr='listing',
        request_method='GET',
        permission='listing')

class ModelListing(resources.ModelListing):
    implements(IManageView)


