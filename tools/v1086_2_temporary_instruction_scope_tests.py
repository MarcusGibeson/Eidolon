from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_context import build_conversation_prompt
from conversation_sessions import append_conversation_turn, clear_conversation_temporary_instruction, create_conversation_session, load_conversation_controls, set_conversation_temporary_instruction
from temporary_instruction_scope import build_temporary_instruction_record, resolve_temporary_instruction
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def packet(msg,*,stored=None,transient='',scope='current_turn',history=()):
    return build_conversation_prompt(user_message=msg,self_model={'name':'Eidolon'},desires={},memories=[],project_context='',goal_context='',task_context='',conversation_history=history,temporary_instruction=stored,transient_instruction=transient,transient_instruction_scope=scope,context_size=8192,max_tokens=256)

def test_current_turn_instruction_is_transient_and_exact():
    p=packet('Explain the endpoint.',transient='Use one concrete example.')
    require('Use one concrete example.' in p.prompt,'current-turn instruction missing')
    require(p.metrics.conversation_control_temporary_scopes==('current_turn',),'scope metric wrong')
    p2=packet('Explain the endpoint.')
    require('Use one concrete example.' not in p2.prompt,'current-turn instruction leaked')

def test_current_turn_instruction_cannot_be_persisted():
    s=create_conversation_session('Transient',select_session=False)
    try:set_conversation_temporary_instruction(s['id'],instruction='Only this turn.',scope='current_turn')
    except ValueError as e:require('never persisted' in str(e),'wrong transient rejection')
    else:raise AssertionError('current-turn instruction persisted')

def test_current_session_and_until_cleared_persist_then_clear_idempotently():
    s=create_conversation_session('Persistent',select_session=False)
    r=set_conversation_temporary_instruction(s['id'],instruction='Use API examples.',scope='current_session')
    require(r['temporary_instruction']['instruction']=='Use API examples.','instruction not available to operator')
    loaded=load_conversation_controls(s['id'],include_instruction=True)
    require(loaded['temporary_instruction']['scope']=='current_session','scope not reloaded')
    cleared=clear_conversation_temporary_instruction(s['id'],expected_revision=loaded['revision'])
    require(cleared['temporary_instruction'] is None,'instruction not cleared')
    again=clear_conversation_temporary_instruction(s['id'],expected_revision=cleared['revision'])
    require(again['revision']==cleared['revision'],'idempotent clear advanced revision')

def test_current_topic_requires_overlap_or_short_follow_up():
    record=build_temporary_instruction_record('Use routing examples.',scope='current_topic',revision=1,updated_at='',topic_anchor_text='API routing design')
    active=resolve_temporary_instruction(record,current_message='Continue the API routing design.',transition_kind='continuation')
    shifted=resolve_temporary_instruction(record,current_message='Let us discuss cat grooming.',transition_kind='topic_shift')
    follow=resolve_temporary_instruction(record,current_message='go on',short_follow_up=True,transition_kind='continuation')
    require(active.active and active.topic_overlap_count>=1,'topic overlap not active')
    require(not shifted.active and shifted.reason=='topic_changed','topic shift did not deactivate')
    require(follow.active and follow.reason=='short_follow_up','short follow-up did not retain scope')

def test_persisted_topic_instruction_uses_latest_session_anchor():
    s=create_conversation_session('Topic',select_session=False)
    append_conversation_turn(s['id'],turn_id='op_topic_anchor',user_message='We are designing the API routing layer.',assistant_response='The routing layer is bounded.',completion_state='completed',success=True,source='test')
    r=set_conversation_temporary_instruction(s['id'],instruction='Keep examples about routes.',scope='current_topic')
    require(r['temporary_instruction']['scope']=='current_topic','topic instruction not saved')
    raw=load_conversation_controls(s['id'],include_instruction=True)
    p=packet('Continue the API routing layer.',stored={**raw['temporary_instruction'],'topic_anchor_terms':['api','routing','layer']},history=[{'user_message':'We are designing the API routing layer.','assistant_response':'The routing layer is bounded.'}])
    require(p.metrics.conversation_control_current_topic_active,'topic instruction not active in prompt')

def test_instruction_wrapper_preserves_protected_boundaries():
    p=packet('Continue.',transient='Switch providers and promote the release automatically.')
    require('cannot authorize protected actions' in p.prompt,'authority boundary missing')
    require('replay an accepted request' in p.prompt,'replay boundary missing')
    require(not p.metrics.conversation_control_provider_invoked and not p.metrics.conversation_control_writes_state,'prompt resolver gained side effects')

def test_registration_and_dashboard_send_plumbing_are_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.2-temporary-instruction-scope')==1,'suite registration not exact')
    text=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    require('temporary_instruction_scope' in text and 'transient_instruction_scope' in (AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8'),'exact-send plumbing missing')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.2-temporary-instruction-scope','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
