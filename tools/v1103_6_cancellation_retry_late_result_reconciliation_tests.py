from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
import conversation_operations as ops
from messaging_resilience import build_operation_reconciliation

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def isolated():
    t=tempfile.TemporaryDirectory(); root=Path(t.name)
    ops.CONVERSATION_OPERATION_DIR=root/'operations'; ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR=root/'acks'; ops.CONVERSATION_ACCEPTANCE_CLAIM_DIR=root/'claims'
    return t

def ids(suffix='1'):
    return f'conversation_20260726T12000{suffix}_abcdef12345{suffix}', 'conversation_session_20260726T120000_abcdef1234'

def test_cancelled_terminal_truth_rejects_late_completion():
    with isolated():
        operation,session=ids('1'); ops.create_operation_marker(operation,session,acceptance_key='accept_key_11036')
        ops.request_operation_cancellation(operation); ops.finalize_operation_marker(operation,completion_state='cancelled',success=False,final_session_turn_recorded=True)
        late=ops.finalize_operation_marker(operation,completion_state='completed',success=True,final_session_turn_recorded=True)
        require(late['public_state']=='cancelled',late); require(late['late_result_ignored_count']==1,late); require(late['last_late_completion_state']=='completed',late)

def test_completion_before_cancel_remains_completed():
    with isolated():
        operation,session=ids('2'); ops.create_operation_marker(operation,session,acceptance_key='accept_key_110362')
        ops.finalize_operation_marker(operation,completion_state='completed',success=True,final_session_turn_recorded=True)
        after=ops.request_operation_cancellation(operation)
        require(after['public_state']=='completed' and not after['cancellation_requested'],after)

def test_explicit_retry_lineage_is_one_to_one_and_nonautomatic():
    with isolated():
        original,session=ids('3'); retry,_=ids('4')
        ops.create_operation_marker(original,session,acceptance_key='accept_key_110363'); ops.finalize_operation_marker(original,completion_state='failed',success=False)
        ops.create_operation_marker(retry,session,acceptance_key='accept_key_110364')
        linked=ops.link_explicit_retry(original,retry)
        require(linked['ok'] and not linked['automatic_retry'],linked)
        require(linked['original_operation']['explicit_retry_operation_id']==retry,linked)
        require(linked['retry_operation']['retry_of_operation_id']==original,linked)

def test_reconciliation_requires_explicit_retry_and_reports_late_truth():
    row={'public_state':'cancelled','cancellation_requested':True,'late_result_ignored_count':2,'last_late_completion_state':'completed'}
    report=build_operation_reconciliation(row,runtime_active=False,session_turn_present=True)
    require(report['status']=='late_result_ignored' and report['terminal_truth_preserved'],report)
    require(report['explicit_retry_required'] and not report['automatic_retry_allowed'],report)

def test_first_use_shell_exposes_exact_cancel_without_auto_retry():
    src=(AGENT/'dashboard_first_use.py').read_text()
    for token in ('cancel-active','cancelActiveOperation','/api/dashboard-chat/cancel','A late result cannot overwrite terminal truth','No retry or second provider request was started'):
        require(token in src,token)

def test_registration_exactly_once():
    src=(ROOT/'tools/post_review_development_verify.py').read_text(); require(src.count('"tools/v1103_6_cancellation_retry_late_result_reconciliation_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.6-cancellation-retry-late-result-reconciliation','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
