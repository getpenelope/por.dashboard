# -*- coding: utf-8 -*-
from fa.bootstrap import actions
from webob.exc import HTTPFound
from repoze.workflow import WorkflowError
from repoze.workflow import get_workflow


def goto_state(context, request):
    state = request.params.get('state')
    if not state:
        request.add_message(u'Missing state parameter.', 'error')
        return HTTPFound(location=request.fa_url(request.model_name, request.model_id))
    try:
        workflow = get_workflow(request.model_instance, request.model_name)
        workflow.transition_to_state(context.get_instance(), request, state, skip_same=False)
        request.add_message(u'Workflow status has been changed. New workflow state is: <strong>%s</strong>.' % state)
        return HTTPFound(location=request.fa_url(request.model_name, request.model_id))
    except WorkflowError, msg:
        print unicode(msg)
        return HTTPFound(location=request.fa_url(request.model_name, request.model_id))


def change_workflow(context):
    try:
        wf = get_workflow(context.get_instance(), context.get_model().__name__)
    except TypeError:
        wf = None
    if not wf: return
    wf_actions = actions.DropdownActions(id='change_workflow',
            permission='workflow',
            content='%s state' % context.get_instance().workflow_state)

    states = wf.get_transitions(context.get_instance(), None)
    if not states:
        return None
    for state in states:
        attrs = {'href': "request.fa_url(request.model_name, request.model_id, 'goto_state', state='%s')" % state['to_state']}
        wf_actions.append(actions.TabAction(id=state['to_state'],
            permission='workflow',
            content=state['name'],
            attrs=attrs))
    return wf_actions
