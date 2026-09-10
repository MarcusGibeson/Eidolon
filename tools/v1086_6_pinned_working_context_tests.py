from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_context import build_conversation_prompt
from conversation_pinned_context import build_pinned_context_record, resolve_pinned_context_record, pinned_context_contains_private_fields
from conversation_sessions import (
    add_conversation_pinned_context, append_conversation_turn, clear_conversation_pinned_context,
    create_conversation_session, load_conversation_controls, remove_conversation_pinned_context,
)
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)

def prompt(msg, pins, history=()):
    return build_conversation_prompt(user_message=msg,self_model={'name':'Eidolon'},desires={},memories=[],project_context='',goal_context='',task_context='',conversation_history=history,pinned_context=pins,context_size=8192,max_tokens=256)

def test_pins_persist_per_conversation_without_leaking():
    a=create_conversation_session('Pins A',select_session=False); b=create_conversation_session('Pins B',select_session=False)
    saved=add_conversation_pinned_context(a['id'],content='Keep this API provider-neutral.',kind='project_constraint',scope='current_session',expected_revision=0)
    require(saved['pinned_context_count']==1 and saved['pinned_context'][0]['content']=='Keep this API provider-neutral.','pin not persisted')
    require(load_conversation_controls(b['id'])['pinned_context_count']==0,'pin leaked to another conversation')

def test_active_pin_enters_prompt_as_bounded_working_context():
    record=build_pinned_context_record('Use the current API route names.',kind='reference_fact',scope='current_session',revision=1,updated_at='')
    packet=prompt('Explain the route.',[record])
    require('PINNED WORKING CONTEXT' in packet.prompt and 'Use the current API route names.' in packet.prompt,'pin missing from prompt')
    require(packet.metrics.conversation_control_pinned_context_included==1,'pin metric missing')
    require('cannot' not in record.get('content_digest',''),'digest unexpectedly contains content')

def test_topic_pin_deactivates_on_explicit_topic_shift():
    record=build_pinned_context_record('Use routing examples.',kind='note',scope='current_topic',revision=1,updated_at='',topic_anchor_text='API routing design')
    active=resolve_pinned_context_record(record,current_message='Continue the API routing design.',transition_kind='continuation')
    shifted=resolve_pinned_context_record(record,current_message='Switch to cat grooming.',transition_kind='topic_shift')
    require(active.active and active.topic_overlap_count>=1,'topic pin did not activate')
    require(not shifted.active and shifted.reason=='topic_changed','topic pin survived shift')

def test_expiry_is_explicit_and_does_not_delete_record():
    expiry=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat().replace('+00:00','Z')
    record=build_pinned_context_record('Temporary goal.',kind='goal',scope='current_session',revision=1,updated_at='',expires_at=expiry)
    resolved=resolve_pinned_context_record(record,current_message='Continue.',now=datetime.now(timezone.utc))
    require(not resolved.active and resolved.expired and resolved.reason=='expired','expired pin remained active')
    require(record['content']=='Temporary goal.','expiry rewrote record')

def test_revision_conflict_remove_and_clear_are_explicit_and_idempotent():
    s=create_conversation_session('Pin revisions',select_session=False)
    first=add_conversation_pinned_context(s['id'],content='One pin.',kind='note',scope='current_session',expected_revision=0)
    try:add_conversation_pinned_context(s['id'],content='Stale tab.',kind='note',scope='current_session',expected_revision=0)
    except ValueError as e: require('another tab' in str(e),'revision conflict not explicit')
    else: raise AssertionError('stale pin update accepted')
    removed=remove_conversation_pinned_context(s['id'],item_id=first['pinned_context'][0]['item_id'],expected_revision=first['revision'])
    require(removed['pinned_context_count']==0,'pin not removed')
    cleared=clear_conversation_pinned_context(s['id'],expected_revision=removed['revision'])
    require(cleared['revision']==removed['revision'],'idempotent clear advanced revision')

def test_public_evidence_and_dashboard_surface_remain_private_and_bounded():
    record=build_pinned_context_record('Private working note.',kind='note',scope='until_cleared',revision=1,updated_at='')
    summary=resolve_pinned_context_record(record,current_message='Continue.').public_summary()
    require(not pinned_context_contains_private_fields(summary),'public pin evidence exposes content')
    render=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8'); server=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    require('Pinned working context' in render and 'chat-pin-add' in render,'operator pin UI missing')
    require('add_pinned_context' in server and 'remove_pinned_context' in server,'pin mutations missing')
    require('@media (max-width:620px)' in render and 'chat-working-context-editor' in render,'narrow layout contract missing')

def test_registration_exact():
    names=[s.name for s in verify.select_suites('core')]
    require(names.count('v1086.6-pinned-working-context')==1,'suite registration not exact')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1086.6-pinned-working-context','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
