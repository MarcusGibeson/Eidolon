from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_operations import create_operation_marker, finalize_operation_marker, new_client_acceptance_key, new_conversation_operation_id
from conversation_retry_regeneration import build_turn_action_plan, regenerate_completed_conversation_turn, explicitly_resend_conversation_turn, ConversationTurnActionError, turn_action_evidence_contains_private_fields
from conversation_sessions import append_conversation_turn, conversation_session_turns, create_conversation_session
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def completed():
    s=create_conversation_session('Completed',select_session=False); op=new_conversation_operation_id()
    append_conversation_turn(s['id'],turn_id=op,user_message='Explain the route.',assistant_response='The route is GET only.',completion_state='completed',success=True,source='test')
    return s,op

def test_plan_distinguishes_retry_regeneration_and_resend():
    s,op=completed(); r=build_turn_action_plan(s['id'],op)
    require(not r['failed_retry_allowed'] and r['regeneration_allowed'] and r['explicit_resend_allowed'],'completed actions confused')
    require(r['regeneration_reuses_user_memory'] and r['resend_creates_new_user_turn'],'lineage semantics missing')
    require(not r['automatic_retry'] and not r['automatic_regeneration'] and not r['automatic_resend'],'automatic action enabled')
    require(not turn_action_evidence_contains_private_fields(r),'private content exposed')

def test_failed_turn_retry_is_separate_and_acceptance_bound():
    s=create_conversation_session('Failed',select_session=False); op=new_conversation_operation_id()
    create_operation_marker(op,s['id'],acceptance_key=new_client_acceptance_key())
    finalize_operation_marker(op,completion_state='failed',success=False,failure_category='unavailable_service',final_session_turn_recorded=True)
    append_conversation_turn(s['id'],turn_id=op,user_message='Try provider.',assistant_response='Unavailable.',completion_state='failed',success=False,failure_category='unavailable_service',source='test')
    r=build_turn_action_plan(s['id'],op)
    require(r['failed_retry_allowed'] and not r['regeneration_allowed'],'failed retry not separated')

def test_regeneration_preserves_original_and_uses_linked_lineage():
    s,op=completed(); fresh=new_conversation_operation_id()
    result=regenerate_completed_conversation_turn(s['id'],op,use_ai=False,operation_id=fresh)
    require(result.operation_id==fresh and result.recovery_of==op,'regeneration lineage missing')
    require(result.recovery_kind=='completed_turn_regeneration','wrong regeneration kind')
    original=next(t for t in conversation_session_turns(s['id']) if t['id']==op)
    require(original['assistant_response']=='The route is GET only.' and original['success'],'original response changed')

def test_explicit_resend_is_new_user_turn_not_recovery():
    s,op=completed(); fresh=new_conversation_operation_id()
    result=explicitly_resend_conversation_turn(s['id'],op,use_ai=False,operation_id=fresh)
    require(result.operation_id==fresh and result.recovery_of=='','resend reused recovery identity')
    require(result.recovery_kind=='explicit_user_resend','resend kind missing')

def test_duplicate_fresh_operation_identity_is_rejected_before_execution():
    s,op=completed(); fresh=new_conversation_operation_id()
    create_operation_marker(fresh,s['id'],acceptance_key=new_client_acceptance_key())
    try:regenerate_completed_conversation_turn(s['id'],op,use_ai=False,operation_id=fresh)
    except ConversationTurnActionError as e:require('already been accepted' in str(e),'wrong duplicate rejection')
    else:raise AssertionError('duplicate operation identity accepted')

def test_dashboard_controls_keep_three_actions_visibly_distinct():
    render=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    handler=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    require('Regenerate response' in render and 'Resend as new turn' in render,'completed turn controls missing')
    require('dashboard_chat_turn_regenerate' in handler and 'dashboard_chat_turn_resend' in handler,'turn action handlers missing')
    require('operation_id=form.get("operation_id"' in handler and 'newConversationOperationId' in render,'fresh operation identity not wired')
    require('preserving the original completed turn' in handler or 'preserve' in render.lower(),'original preservation not stated')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.4-safe-retry-regeneration')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.4-safe-retry-regeneration','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
