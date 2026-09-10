from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from api_server import handle_api_get
from conversation_long_session_hardening import build_long_session_hardening_state, long_session_hardening_contains_private_fields
from conversation_sessions import (
    add_conversation_pinned_context, append_conversation_turn, create_conversation_session,
    queue_conversation_operator_intent, save_conversation_draft,
)
from dashboard_chat_console import dashboard_chat_session_snapshot
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)

def long_session(turns=125):
    s=create_conversation_session('Long session',select_session=False)
    for i in range(turns):
        append_conversation_turn(s['id'],turn_id=f'long_turn_{i:04d}',user_message=f'User topic {i} bounded history.',assistant_response=f'Eidolon response {i} remains complete.',completion_state='completed',success=True,source='long-test')
    return s

def test_large_session_uses_bounded_initial_and_earlier_windows():
    s=long_session(); state=build_long_session_hardening_state(s['id'])
    require(state['long_session'] and state['turn_count']==125,'long session not recognized')
    require(state['initial_turns_rendered']<=80 and state['earlier_history_available'],'history window not bounded')
    require(not state['full_transcript_embedded'] and state['whole_turn_windows'],'full transcript leaked into initial view')

def test_dashboard_snapshot_remains_bounded_and_content_free_in_hardening_evidence():
    s=long_session(90); snap=dashboard_chat_session_snapshot(s['id']); hard=snap['long_session_hardening']
    require(snap['history_window']['shown']<=80 and snap['history_window']['has_older'],'snapshot history not bounded')
    require(not long_session_hardening_contains_private_fields(hard),'hardening evidence exposes transcript content')

def test_drafts_pins_and_offline_intent_survive_long_session_state():
    s=long_session(5); save_conversation_draft(s['id'],'Pending long-session draft.',editor_id='long-test',base_revision=0)
    controls=add_conversation_pinned_context(s['id'],content='Keep this session provider-neutral.',kind='project_constraint',scope='current_session',expected_revision=0)
    queue_conversation_operator_intent(s['id'],kind='send_current_draft',expected_revision=controls['revision'])
    state=build_long_session_hardening_state(s['id'])
    require(state['draft_preserved'] and state['pinned_context_count']==1 and state['queued_operator_intent_present'],'local controls not preserved')
    require(state['offline_degradation']['queued_operator_intent']['state']=='ready','offline intent not visible')

def test_branch_retry_multitab_and_scroll_contracts_remain_explicit():
    s=long_session(2); state=build_long_session_hardening_state(s['id'])
    for key in ('scroll_anchor_preserved_on_prepend','jump_to_latest_preserved','message_edits_create_branches','original_transcript_preserved','retry_regeneration_resend_separated','multi_tab_revision_guard'):
        require(state[key] is True,f'{key} contract missing')
    require(not state['provider_invoked'] and not state['writes_state'],'hardening evidence has side effects')

def test_read_only_api_route_is_content_free():
    s=long_session(3); status,payload=handle_api_get('/api/conversation/long-session-hardening',{'session_id':[s['id']]})
    require(status==200 and payload.get('ok'),'long-session GET failed')
    require(not long_session_hardening_contains_private_fields(payload['data']),'API evidence exposes private content')

def test_dashboard_layout_contains_new_controls_on_narrow_screens():
    render=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    require('chat-working-context-editor' in render and 'chat-offline-intent-editor' in render,'new control panels missing')
    require('@media (max-width:620px)' in render and 'grid-template-columns:1fr' in render,'narrow layout hardening missing')
    require('Load earlier messages' in render and 'chat-jump-latest' in render,'long-session navigation controls missing')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.8-long-session-performance-ux-hardening')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.8-long-session-performance-ux-hardening','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
