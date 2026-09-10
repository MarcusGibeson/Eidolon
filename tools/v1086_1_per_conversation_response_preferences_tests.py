from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_context import build_conversation_prompt
from conversation_sessions import create_conversation_session, load_conversation_controls, update_conversation_response_preferences
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def prompt(pref,msg='Explain the API route.'):
    return build_conversation_prompt(user_message=msg,self_model={'name':'Eidolon'},desires={},memories=[],project_context='',goal_context='',task_context='',conversation_history=[],response_preferences=pref,context_size=8192,max_tokens=256)

def test_preferences_persist_per_session():
    a=create_conversation_session('A',select_session=False); b=create_conversation_session('B',select_session=False)
    saved=update_conversation_response_preferences(a['id'],mode='technical',format='steps')
    require(saved['response_preferences']['mode']=='technical','mode not saved')
    require(load_conversation_controls(a['id'])['response_preferences']['format']=='steps','format not reloaded')
    require(load_conversation_controls(b['id'])['response_preferences']['mode']=='default','preference leaked across sessions')

def test_prompt_applies_session_preference_without_mutating_personality():
    pref={'mode':'casual','format':'prose','revision':1}
    packet=prompt(pref)
    require('PER-CONVERSATION RESPONSE PREFERENCE' in packet.prompt,'preference block missing')
    require(packet.metrics.conversation_control_response_mode=='casual','metric missing')
    require('does not modify the configured personality' in packet.prompt,'personality boundary missing')

def test_current_turn_length_request_overrides_stored_length():
    packet=prompt({'mode':'concise','format':'default'},'Give me a detailed step-by-step explanation of the API route.')
    require('explicit length request overrides' in packet.prompt,'current-turn override missing')
    require(packet.metrics.conversation_response_length in {'deep','detailed'},'current-turn detail cue lost')

def test_invalid_preferences_are_rejected():
    s=create_conversation_session('Invalid',select_session=False)
    try:update_conversation_response_preferences(s['id'],mode='unlimited',format='default')
    except ValueError:pass
    else:raise AssertionError('invalid mode accepted')

def test_revision_conflict_is_explicit():
    s=create_conversation_session('Revision',select_session=False)
    first=update_conversation_response_preferences(s['id'],mode='concise',expected_revision=0)
    require(first['revision']==1,'revision not advanced')
    try:update_conversation_response_preferences(s['id'],mode='detailed',expected_revision=0)
    except ValueError as e:require('another tab' in str(e),'conflict message not explicit')
    else:raise AssertionError('stale revision accepted')

def test_preferences_do_not_contact_provider_or_change_global_defaults():
    s=create_conversation_session('Safety',select_session=False)
    r=update_conversation_response_preferences(s['id'],mode='brainstorming')
    require(not r['response_preferences']['provider_invoked'],'preference contacted provider')
    require(r['response_preferences']['session_local'] and not r['response_preferences']['mutates_global_personality'],'scope boundary wrong')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.1-per-conversation-response-preferences')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.1-per-conversation-response-preferences','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
