from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from api_server import ApiError, handle_api_get, handle_api_post
from conversation_control_foundation import build_conversation_control_foundation, default_conversation_control_state, normalize_conversation_control_state
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)

def test_foundation_exposes_bounded_controls():
    r=build_conversation_control_foundation()
    require({'default','concise','detailed','technical','casual','brainstorming'} <= set(r['response_modes']), 'response modes missing')
    require(set(r['temporary_instruction_scopes'])=={'current_turn','current_topic','current_session','until_cleared'}, 'scope set wrong')
    require(r['default_retry_policy']=='safe_transient_only' and r['default_branch_policy']=='preserve_original','safe defaults wrong')

def test_foundation_preserves_authority_boundaries():
    r=build_conversation_control_foundation()
    for key in ('accepted_request_replay_allowed','automatic_resend_allowed','automatic_branch_creation_allowed','mutates_global_personality','changes_provider_or_model','grants_release_or_approval_authority','unrestricted_shell_allowed','provider_invoked','writes_state'):
        require(r[key] is False, f'{key} boundary weakened')
    require(r['explicit_post_required_for_persisted_changes'], 'persisted changes are not explicit')

def test_default_state_is_session_local_and_content_free():
    r=default_conversation_control_state('session-x')
    require(r['session_id']=='session-x' and r['revision']==0, 'default state wrong')
    require(r['response_preferences']['mode']=='default' and r['temporary_instruction'] is None, 'defaults not neutral')

def test_normalization_rejects_unknown_policy_by_fallback():
    r=normalize_conversation_control_state({'retry_policy':'magic','branch_policy':'overwrite_original'},session_id='s')
    require(r['retry_policy']=='safe_transient_only','unsafe retry policy survived')
    require(r['branch_policy']=='preserve_original','unsafe branch policy survived')

def test_read_only_api_route_exists_without_post_mutation():
    status,payload=handle_api_get('/api/conversation/control-foundation',{})
    require(status==200 and payload.get('ok'),'foundation GET failed')
    try: handle_api_post('/api/conversation/control-foundation',{})
    except ApiError as e: require(e.status in {404,405},'unexpected POST status')
    else: raise AssertionError('foundation exposes POST mutation')

def test_dashboard_contract_retains_narrow_layout_and_post_control_route():
    text=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    styles=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    require('/api/dashboard-chat/conversation-controls' in text,'operator control route missing')
    require('@media (max-width:620px)' in styles and 'max-width:100%' in styles,'narrow layout contract missing')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.0-conversation-control-foundation')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.0-conversation-control-foundation','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
