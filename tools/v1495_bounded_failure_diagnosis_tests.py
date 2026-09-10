from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1495-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.bounded_failure_diagnosis import diagnose_candidate_failure,admit_bounded_repair
from conscious_agent.development_authority import issue_operator_authorization
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 syntax=diagnose_candidate_failure([{'status':'failed','failure_code':'python_syntax_error','passed':False}],attempt=1)
 ck('syntax failure is classified deterministically',syntax['primary_failure_class']=='syntax_or_compile_failure',syntax)
 ck('first repairable failure exposes one bounded preparation chance',syntax['repair_attempt_may_be_prepared'] and syntax['max_additional_attempts']==1,syntax)
 ck('diagnosis never retries automatically',not syntax['automatic_retry_allowed'] and not syntax['source_modified'],syntax)
 blocked=admit_bounded_repair(syntax,candidate_id='a',operator_authorization_receipt=None);ck('repair preparation remains operator gated',not blocked['repair_workspace_authorized'],blocked)
 phrase='Authorize bounded repair a.';receipt=issue_operator_authorization(stage='bounded_repair',subject_id='a',subject_digest=syntax['diagnosis_digest'],explicit_operator_text=phrase,expected_operator_text=phrase)
 admitted=admit_bounded_repair(syntax,candidate_id='a',operator_authorization_receipt=receipt);ck('operator can authorize one isolated repair preparation',admitted['repair_workspace_authorized'] and not admitted['automatic_execution'],admitted)
 second=diagnose_candidate_failure([{'status':'failed','reason':'assertion failed','passed':False}],attempt=2);ck('second failure stops rather than looping',not second['repair_attempt_may_be_prepared'] and second['max_additional_attempts']==0,second)
 provider=diagnose_candidate_failure([{'status':'failed','reason':'provider unavailable','passed':False}],attempt=1);ck('provider failure is not treated as code repair',provider['primary_failure_class']=='provider_failure' and not provider['repair_attempt_may_be_prepared'],provider)
 authority=diagnose_candidate_failure([{'status':'blocked','reason':'approval required','passed':False}]);ck('authority failures stop for operator',authority['primary_failure_class']=='authority_boundary_failure' and authority['repair_kind']=='stop_for_operator_authority',authority)
 stale=diagnose_candidate_failure([{'status':'failed','reason':'source digest changed concurrently','passed':False}]);ck('concurrent source change requires discard/rebase',stale['primary_failure_class']=='stale_or_concurrent_source_failure',stale)
 clean=diagnose_candidate_failure([{'status':'passed','passed':True}]);ck('passing receipts produce no invented repair',clean['primary_failure_class']=='no_failure' and not clean['bounded_repair_proposed'],clean)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1495-bounded-failure-diagnosis','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
