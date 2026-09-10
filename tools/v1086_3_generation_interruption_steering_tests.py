from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
import dashboard_chat_console
from conversation_generation_steering import build_generation_steering_plan, request_generation_steering, steering_evidence_contains_private_fields
from conversation_operations import create_operation_marker, finalize_operation_marker, new_client_acceptance_key, new_conversation_operation_id
from conversation_sessions import create_conversation_session
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)

def running_marker():
    s=create_conversation_session('Steer',select_session=False); op=new_conversation_operation_id()
    create_operation_marker(op,s['id'],acceptance_key=new_client_acceptance_key())
    return s,op

def test_plan_is_cancellation_first_and_content_free():
    s,op=running_marker(); r=build_generation_steering_plan(s['id'],op,'Focus on the error path.')
    require(r['steering_allowed'] and r['fresh_acceptance_identity_required'],'steering plan not explicit')
    require(not r['automatic_resend'] and not r['accepted_request_replay'],'replay boundary weakened')
    require(r['redirect_digest'] and r['redirect_length']>0,'bounded redirect evidence missing')
    require(not steering_evidence_contains_private_fields(r),'private steering content exposed')

def test_terminal_and_session_mismatch_are_blocked():
    s,op=running_marker(); finalize_operation_marker(op,completion_state='completed',success=True)
    r=build_generation_steering_plan(s['id'],op,'Try another direction.')
    require(not r['steering_allowed'] and r['reason']=='operation_terminal','terminal operation steerable')
    other=create_conversation_session('Other',select_session=False)
    m=build_generation_steering_plan(other['id'],op,'Try another direction.')
    require(not m['steering_allowed'] and m['reason']=='session_mismatch','session mismatch not blocked')

def test_request_cancels_exact_operation_without_submitting_redirect():
    s,op=running_marker(); original=dashboard_chat_console.cancel_dashboard_chat_operation
    dashboard_chat_console.cancel_dashboard_chat_operation=lambda operation_id:{'ok':True,'operation_id':operation_id,'status':'cancellation_requested'}
    try:r=request_generation_steering(s['id'],op,'Use the smaller example.')
    finally:dashboard_chat_console.cancel_dashboard_chat_operation=original
    require(r['ok'] and r['cancellation_requested'],'cancellation not requested')
    require(not r['redirect_submitted'] and r['next_action'].startswith('wait_for_cancelled'),'redirect was auto-submitted')

def test_api_post_is_explicit_and_does_not_replay():
    original=api_server.request_generation_steering
    api_server.request_generation_steering=lambda s,o,m:{'ok':True,'automatic_resend':False,'redirect_submitted':False,'fresh_acceptance_identity_required':True}
    try:status,payload=api_server.handle_api_post('/api/conversation/steer',{'session_id':'s','operation_id':'o','redirect_message':'new direction'})
    finally:api_server.request_generation_steering=original
    require(status==200 and payload.get('ok'),'steering POST missing')
    data=payload.get('data') or {}
    require(data.get('automatic_resend') is False and data.get('redirect_submitted') is False,'API auto-replayed redirect')

def test_runtime_precommit_cancellation_boundary_is_preserved():
    text=(AGENT/'conversation_runtime.py').read_text(encoding='utf-8')
    require('_claim_operation_completion' in text and 'pre_commit_cancellation' in text,'precommit cancellation boundary missing')
    require('partial_discarded' in text and 'assistant_memory' in text,'partial memory boundary missing')

def test_dashboard_has_review_before_send_steering_ui_and_narrow_layout():
    text=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    styles=(AGENT/'dashboard_chat_styles.py').read_text(encoding='utf-8')
    require('Cancel and prepare redirect' in text and '/api/conversation/steer' in text,'steering UI missing')
    require('unsent draft' in text and 'fresh acceptance identity' in text,'review-before-send boundary missing')
    require('cancelButton, steeringButton].filter(Boolean)' in text and 'steeringRequest].filter(Boolean)' not in text,'steering control reference mismatch')
    require('@media (max-width:620px)' in styles and 'max-width:100%' in styles,'narrow layout contract missing')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.3-generation-interruption-steering')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.3-generation-interruption-steering','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
