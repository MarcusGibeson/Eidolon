from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_message_branching import build_message_branch_plan, create_message_edit_branch, message_branch_evidence_contains_private_fields, ConversationBranchError
from conversation_sessions import append_conversation_turn, create_conversation_session, load_conversation_draft, load_conversation_session
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def source_session():
    s=create_conversation_session('Original',select_session=False)
    append_conversation_turn(s['id'],turn_id='turn_one',user_message='Design the API.',assistant_response='Use bounded routes.',completion_state='completed',success=True,source='test')
    append_conversation_turn(s['id'],turn_id='turn_two',user_message='Add a POST route.',assistant_response='Keep mutation explicit.',completion_state='completed',success=True,source='test')
    return s

def test_plan_is_read_only_content_free_and_requires_explicit_action():
    r=build_message_branch_plan('session','turn','Use a GET route instead.','branch_request_plan_01')
    require(r['branch_allowed'] and r['original_session_preserved'] and r['original_turn_preserved'],'preservation missing')
    require(not r['raw_transcript_rewritten'] and not r['message_submitted'] and not r['provider_invoked'],'branch planner gained side effects')
    require(r['fresh_acceptance_required_to_send'],'fresh send boundary missing')
    require(not message_branch_evidence_contains_private_fields(r),'edited content exposed')

def test_edit_creates_branch_with_copied_prefix_and_unsent_draft():
    s=source_session(); result=create_message_edit_branch(s['id'],'turn_two','Add a GET route.',branch_request_id='branch_request_edit_01',select_session=False)
    branch=result['branch']; loaded=load_conversation_session(branch['id'],include_turns=True); draft=load_conversation_draft(branch['id'])
    require(loaded['turn_count']==1 and loaded['turns'][0]['branch_copy_of']=='turn_one','prefix not preserved')
    require(draft['content']=='Add a GET route.' and result['message_submitted'] is False,'edit was not an unsent draft')
    require(loaded['branch']['source_turn_id']=='turn_two' and loaded['branch']['original_session_preserved'],'branch provenance missing')
    repeated=create_message_edit_branch(s['id'],'turn_two','Add a GET route.',branch_request_id='branch_request_edit_01',select_session=False)
    require(repeated['branch']['id']==branch['id'],'duplicate branch request was not idempotent')

def test_original_session_and_turns_remain_unchanged():
    s=source_session(); before=load_conversation_session(s['id'],include_turns=True)
    create_message_edit_branch(s['id'],'turn_one','Redesign the API.',branch_request_id='branch_request_original_01',select_session=False)
    after=load_conversation_session(s['id'],include_turns=True)
    require(before==after,'source transcript was rewritten')

def test_branch_from_first_turn_has_empty_prefix_not_synthetic_reply():
    s=source_session(); result=create_message_edit_branch(s['id'],'turn_one','Start with a CLI.',branch_request_id='branch_request_first_01',select_session=False)
    loaded=load_conversation_session(result['branch']['id'],include_turns=True)
    require(loaded['turn_count']==0 and loaded['completed_turn_count']==0,'synthetic branch reply created')
    require(load_conversation_draft(loaded['id'])['content']=='Start with a CLI.','first-turn edit draft missing')

def test_empty_edit_is_rejected():
    s=source_session()
    try:create_message_edit_branch(s['id'],'turn_one','   ',branch_request_id='branch_request_empty_01',select_session=False)
    except ConversationBranchError:pass
    else:raise AssertionError('empty branch edit accepted')

def test_operator_ui_and_api_preserve_original_and_do_not_auto_send():
    render=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8')
    server=(AGENT/'api_server.py').read_text(encoding='utf-8')
    require('Edit into a new branch' in render and 'Create branch draft' in render,'branch UI missing')
    require('/api/conversation/message-branch' in server,'branch API missing')
    require('branch_request_id' in server and 'turn.message_branch' in (AGENT/'dashboard.py').read_text(encoding='utf-8'),'branch idempotency or coordination missing')
    require('does not send automatically' in render.lower() or 'unsent draft' in render.lower(),'auto-send boundary missing')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.5-message-editing-branching')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.5-message-editing-branching','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
