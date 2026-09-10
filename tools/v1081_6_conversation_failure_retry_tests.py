from __future__ import annotations
import argparse, json, subprocess, tempfile
from pathlib import Path
from typing import Callable

ROOT=Path(__file__).resolve().parents[1]
AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'
import sys
sys.path.insert(0,str(AGENT))
import conversation_operations as ops
import conversation_retry_evidence as retry
import conversation_recovery
import release_metadata
import dashboard_chat_console
import post_review_development_verify as isolated_verify

def require(v,m):
    if not v: raise AssertionError(m)

def isolated_runtime():
    temp=tempfile.TemporaryDirectory(prefix='eidolon-v1081-6-')
    base=Path(temp.name)
    ops.CONVERSATION_OPERATION_DIR=base/'operations'
    ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR=base/'acks'
    retry.CONVERSATION_RETRY_EVIDENCE_DIR=base/'retry_evidence'
    return temp

def test_release_metadata():
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split('.'))) >= (1081, 6), 'runtime metadata predates v1081.6')
    require(tuple(map(int, release_metadata.PREVIOUS_RUNTIME_VERSION.split('.'))) >= (1081, 5), 'v1081.6 lineage missing')

def test_non_acceptance_evidence_is_content_free():
    t=isolated_runtime()
    try:
        session='conversation_session_20260719T120000_1234567890'; key='chat_accept_1234567890abcdef'
        row=retry.persist_non_acceptance_evidence(session,key,reason='acceptance_rejected')
        require(row['non_acceptance_proven'] and row['resend_allowed'],'resend evidence not proven')
        raw=json.loads(next((Path(t.name)/'retry_evidence').rglob('*.json')).read_text())
        forbidden={'message','prompt','response','provider_payload','credentials','receipt','raw_output'}
        require(not(forbidden & set(raw)),f'private fields leaked: {forbidden & set(raw)}')
    finally:t.cleanup()

def test_accepted_key_blocks_non_acceptance_record():
    t=isolated_runtime()
    try:
        session='conversation_session_20260719T120000_1234567890'; key='chat_accept_1234567890abcdef'; op='conversation_20260719T120000_123456789abc'
        ops.create_operation_marker(op,session,acceptance_key=key)
        try: retry.persist_non_acceptance_evidence(session,key)
        except ValueError: pass
        else: raise AssertionError('accepted key permitted non-acceptance evidence')
    finally:t.cleanup()

def test_accepted_failed_turn_has_linked_recovery_not_resend():
    t=isolated_runtime()
    try:
        session='conversation_session_20260719T120000_1234567890'; key='chat_accept_1234567890abcdef'; op='conversation_20260719T120000_123456789abc'
        ops.create_operation_marker(op,session,acceptance_key=key)
        ops.finalize_operation_marker(op,completion_state='unavailable_service',success=False,failure_category='unavailable_service',final_session_turn_recorded=True)
        row=retry.retry_evidence_for_turn(session,op)
        require(row['acceptance_proven'] and row['linked_recovery_allowed'],'accepted failure not recoverable')
        require(row['resend_allowed'] is False,'accepted failure exposed resend')
    finally:t.cleanup()

def test_completed_turn_blocks_recovery():
    t=isolated_runtime()
    try:
        session='conversation_session_20260719T120000_1234567890'; op='conversation_20260719T120000_123456789abc'
        ops.create_operation_marker(op,session,acceptance_key='chat_accept_1234567890abcdef')
        ops.finalize_operation_marker(op,completion_state='completed',success=True,final_session_turn_recorded=True)
        require(retry.retry_evidence_for_turn(session,op)['linked_recovery_allowed'] is False,'completed turn recoverable')
    finally:t.cleanup()

def test_unknown_acceptance_does_not_allow_resend():
    t=isolated_runtime()
    try:
        row=retry.resend_evidence('conversation_session_20260719T120000_1234567890','chat_accept_1234567890abcdef')
        require(not row['resend_allowed'] and not row['non_acceptance_proven'],'unknown acceptance allowed resend')
    finally:t.cleanup()

def test_persisted_non_acceptance_requires_fresh_identity():
    t=isolated_runtime()
    try:
        s='conversation_session_20260719T120000_1234567890'; k='chat_accept_1234567890abcdef'
        retry.persist_non_acceptance_evidence(s,k)
        row=retry.resend_evidence(s,k)
        require(row['resend_allowed'] and row['fresh_acceptance_identity_required'],'fresh identity not required')
        require(row['automatic_resend'] is False,'automatic resend enabled')
    finally:t.cleanup()

def test_recovery_module_requires_marker_evidence():
    src=(AGENT/'conversation_recovery.py').read_text()
    require('retry_evidence_for_turn' in src and 'acceptance_proven' in src,'recovery lacks acceptance proof')
    require('linked_recovery_allowed' in src,'linked recovery boundary missing')

def test_failure_cards_use_explicit_linked_recovery_copy():
    src=(AGENT/'dashboard_chat_console.py').read_text()
    require('Run explicit linked recovery' in src,'explicit recovery label missing')
    require('Acceptance proven' in src,'acceptance evidence absent from diagnostics')
    require('Retry failed turn once' not in src,'ambiguous retry copy retained')

def test_no_automatic_replay_or_settings_mutation():
    src=(AGENT/'conversation_retry_evidence.py').read_text()
    for token in ('automatic_resend": False','provider_request_replayed": False'):
        require(token in src,f'missing boundary {token}')
    require('local_model_settings' not in src and 'subprocess' not in src,'retry evidence mutates settings or runs commands')

def test_rendered_javascript_syntax():
    html=dashboard_chat_console.render_realtime_chat_panel(None,compact=True)
    scripts=[]; cursor=0
    while True:
        a=html.find('<script>',cursor)
        if a<0: break
        b=html.find('</script>',a); require(b>=0,'unterminated script'); scripts.append(html[a+8:b]); cursor=b+9
    with tempfile.TemporaryDirectory() as d:
        for i,script in enumerate(scripts):
            p=Path(d)/f'{i}.js'; p.write_text(script)
            r=subprocess.run(['node','--check',str(p)],capture_output=True,text=True,timeout=30)
            require(r.returncode==0,r.stderr or 'node syntax failed')

def test_narrow_layout_controls_wrap():
    require('.chat-recovery-actions { display:flex; flex-wrap:wrap;' in dashboard_chat_console.COMPANION_CHAT_STYLES,'recovery actions do not wrap')

def test_core_profile_registration():
    selected={s.name for s in isolated_verify.select_suites('core')}
    require('v1081.6-conversation-failure-retry' in selected,'v1081.6 absent from core')
    require('v1081.5-recovery-evidence-resume' in selected,'v1081.5 retained suite missing')

def test_release_registration():
    src=(TOOLS/'release_verify.py').read_text()
    require(src.count('conversation-failure-explicit-retry-fixtures')==1,'release stage count wrong')
    require(src.count('tools/v1081_6_conversation_failure_retry_tests.py')==1,'suite registration count wrong')

def test_docs_and_workspace_versions():
    require('v1081.6' in (ROOT/'README_RELEASE_HISTORY.md').read_text(), 'historical v1081.6 release evidence missing')
    current = release_metadata.RUNTIME_VERSION_TAG
    for rel in ('README.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','data/workspaces/active_project.json','data/workspaces/projects.json'):
        require(current in (ROOT/rel).read_text(), f'{rel} missing current runtime tag')
    require(release_metadata.RUNTIME_VERSION in (ROOT/'data/settings.json').read_text(), 'data/settings.json missing current runtime version')

def test_source_only_privacy():
    require(not (ROOT/'data/projects.json').exists(),'data/projects.json present')
    forbidden=('data/conversation_runtime','data/conversation_sessions','data/dashboard_chat','data/approvals','data/tasks.json','data/memories.json','.venv')
    paths=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}]
    for token in forbidden: require(not any(token in x for x in paths),f'forbidden runtime path {token}')

TESTS=tuple((n[5:],v) for n,v in sorted(globals().items()) if n.startswith('test_') and callable(v))
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args()
    checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1081.6-conversation-failure-evidence-explicit-retry','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks,'automatic_retry':False,'automatic_resend':False,'release_authorized':False}
    print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
