from __future__ import annotations
import json, sys, tempfile, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
import conversation_operations as ops
from messaging_reliability import build_exactly_once_evidence

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)
def _ids(): return ('conversation_session_20260726T120000_abcdef1234','chat_accept_abcdef1234567890','conversation_20260726T120000_abcdef123456')
def test_cross_process_style_acceptance_claim_converges_on_one_operation():
    base=Path(tempfile.mkdtemp(prefix='eidolon-v1103-2-')); old=ops.CONVERSATION_ACCEPTANCE_CLAIM_DIR; ops.CONVERSATION_ACCEPTANCE_CLAIM_DIR=base/'claims'
    try:
        session,key,op1=_ids(); op2='conversation_20260726T120001_fedcba654321'; rows=[]
        def run(op): rows.append(ops.claim_operation_acceptance(session,key,op))
        a=threading.Thread(target=run,args=(op1,)); b=threading.Thread(target=run,args=(op2,)); a.start();b.start();a.join();b.join()
        require(sum(1 for r in rows if r['claimed'])==1,rows); require(len({r['operation_id'] for r in rows})==1,rows); require(ops.operation_id_for_acceptance_key(session,key)==rows[0]['operation_id'],rows)
    finally: ops.CONVERSATION_ACCEPTANCE_CLAIM_DIR=old
def test_exactly_once_evidence_accepts_duplicates_only_when_they_converge():
    r=build_exactly_once_evidence(acceptance_claim_count=1,operation_count=1,execution_start_count=1,provider_request_count=1,duplicate_submission_count=4)
    require(r['status']=='pass' and r['exactly_once'] and r['duplicate_submissions_converged'],r)
def test_second_operation_or_provider_request_blocks_evidence():
    for kwargs in ({'operation_count':2,'provider_request_count':1},{'operation_count':1,'provider_request_count':2},{'operation_count':1,'provider_request_count':1,'automatic_retry_count':1}):
        row={'acceptance_claim_count':1,'execution_start_count':1,**kwargs}; require(build_exactly_once_evidence(**row)['status']=='blocked',row)
def test_dashboard_claim_occurs_before_marker_and_thread_start():
    src=(AGENT/'dashboard_chat_console.py').read_text(); claim=src.index('acceptance_claim = claim_operation_acceptance'); marker=src.index('marker = create_operation_marker',claim); thread=src.index('thread = threading.Thread',marker); require(claim<marker<thread,(claim,marker,thread)); require('No duplicate provider request was started.' in src,'bounded race copy')
def test_first_use_and_full_console_have_client_side_duplicate_latches():
    first=(AGENT/'dashboard_first_use.py').read_text(); full=(AGENT/'dashboard_chat_console.py').read_text()
    require('sending) return' in first and 'keyboardSubmitLatch' in first,'first use latch'); require('composerSubmissionPending' in full and 'pendingSubmissions' in full and 'resolveAcceptanceOutcome' in full,'full console reconciliation')
def test_version_suite_registration_is_exactly_once():
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require(verifier.count('"tools/v1103_2_exactly_once_send_provider_request_tests.py"')==1,'registration')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.2-exactly-once-send-provider-request','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
