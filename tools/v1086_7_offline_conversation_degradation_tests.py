from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from api_server import ApiError, handle_api_get, handle_api_post
from conversation_offline_degradation import offline_conversation_degradation_state, offline_degradation_contains_private_fields
from conversation_sessions import (
    add_conversation_pinned_context, append_conversation_turn, clear_conversation_operator_intent,
    create_conversation_session, load_conversation_controls, queue_conversation_operator_intent,
    save_conversation_draft,
)
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)

def session_with_draft():
    s=create_conversation_session('Offline',select_session=False)
    save_conversation_draft(s['id'],'Review this draft later.',editor_id='offline-test',base_revision=0)
    return s

def test_offline_state_preserves_local_surfaces_and_pins():
    s=session_with_draft(); pin=add_conversation_pinned_context(s['id'],content='Keep the task local.',kind='project_constraint',scope='current_session',expected_revision=0)
    state=offline_conversation_degradation_state(s['id'],provider_available=False)
    caps=state['capabilities']
    require(state['degradation_mode']=='local_surfaces_only' and state['draft_preserved'],'offline degradation wrong')
    for key in ('conversation_history','conversation_search','archive_browsing','memory_browse','context_inspection','pinned_working_context','queued_operator_intent'):
        require(caps.get(key) is True,f'{key} not preserved offline')
    require(state['pinned_context_count']==1,'pin missing offline')

def test_queued_draft_intent_is_content_free_and_never_executes_automatically():
    s=session_with_draft(); queued=queue_conversation_operator_intent(s['id'],kind='send_current_draft',expected_revision=0)
    intent=queued['queued_operator_intent']
    require(intent['state']=='ready' and intent['explicit_confirmation_required'],'queue not reviewable')
    require(not intent['automatic_execution'] and not intent['automatic_resend'] and not intent['provider_invoked'],'queue gained execution authority')
    require(not offline_degradation_contains_private_fields(intent),'queued intent exposes draft content')

def test_draft_change_marks_queued_send_stale_without_resending():
    s=session_with_draft(); queued=queue_conversation_operator_intent(s['id'],kind='send_current_draft',expected_revision=0)
    save_conversation_draft(s['id'],'Changed after queueing.',editor_id='offline-test',base_revision=1)
    state=offline_conversation_degradation_state(s['id'])
    require(state['queued_operator_intent']['state']=='stale' and state['queued_operator_intent']['reason']=='draft_changed','changed draft did not stale queue')
    require(not state['automatic_execution_after_recovery'],'stale queue auto-executes')

def test_turn_intent_requires_existing_target_and_stays_explicit():
    s=create_conversation_session('Target',select_session=False)
    append_conversation_turn(s['id'],turn_id='failed_turn',user_message='Try this.',assistant_response='',completion_state='failed',success=False,source='test')
    queued=queue_conversation_operator_intent(s['id'],kind='retry_failed_turn',target_turn_id='failed_turn',expected_revision=0)
    require(queued['queued_operator_intent']['state']=='ready','valid target not queued')
    try:queue_conversation_operator_intent(s['id'],kind='retry_failed_turn',target_turn_id='missing_turn',expected_revision=queued['revision'])
    except ValueError:pass
    else:raise AssertionError('missing target accepted')

def test_clear_is_idempotent_and_does_not_execute_intent():
    s=session_with_draft(); queued=queue_conversation_operator_intent(s['id'],kind='send_current_draft',expected_revision=0)
    cleared=clear_conversation_operator_intent(s['id'],expected_revision=queued['revision'])
    require(cleared['queued_operator_intent']['state']=='none','intent not cleared')
    again=clear_conversation_operator_intent(s['id'],expected_revision=cleared['revision'])
    require(again['revision']==cleared['revision'],'idempotent clear advanced revision')

def test_read_only_api_and_dashboard_queue_preserve_no_replay_boundary():
    s=session_with_draft(); status,payload=handle_api_get('/api/conversation/offline-degradation',{'session_id':[s['id']]})
    require(status==200 and payload.get('ok'),'offline GET failed')
    try:handle_api_post('/api/conversation/offline-degradation',{})
    except ApiError as e: require(e.status in {404,405},'unexpected mutation route')
    else:raise AssertionError('offline degradation exposes POST')
    dashboard=(AGENT/'dashboard.py').read_text(encoding='utf-8'); render=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    require('queue_offline_intent' in dashboard and 'clear_offline_intent' in dashboard,'queue dashboard actions missing')
    require('will not execute automatically' in render.lower(),'no-auto-execution copy missing')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.7-offline-conversation-degradation')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.7-offline-conversation-degradation','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
