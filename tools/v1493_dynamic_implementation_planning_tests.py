from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1493-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.dynamic_implementation_planning import build_evidence_bound_plan,revise_plan_from_evidence
from conscious_agent.development_authority import issue_operator_authorization
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 c={'candidate_id':'a','evidence_digest':'e'*64,'eligibility_digest':'a'*64,'source_module':'conscious_agent/sample.py','proposed_destination_module':'conscious_agent/sample_helpers.py','source_symbols':['alpha','beta'],'reversibility_classification':'high_reversible','eligible_for_quality_comparison':True}
 phrase='Select dynamic candidate a.'
 receipt=issue_operator_authorization(stage='candidate_selection',subject_id='a',subject_digest='a'*64,explicit_operator_text=phrase,expected_operator_text=phrase)
 b=build_evidence_bound_plan(c,operator_selection_receipt=None)
 ck('planning requires exact operator-selected candidate id',b['status']=='planning_blocked' and not b['plan_created'],b)
 plan=build_evidence_bound_plan(c,operator_selection_receipt=receipt,available_test_files=['tools/sample_tests.py'])
 ck('selected candidate yields evidence-bound plan',plan['status']=='plan_ready_for_operator_review' and plan['source_symbols']==['alpha','beta'],plan)
 ck('plan binds exact candidate evidence',plan['candidate_evidence_digest']=='e'*64 and plan['candidate_eligibility_digest']=='a'*64 and plan['operator_selection_receipt_digest']==receipt['receipt_digest'],plan)
 ck('plan names prerequisites assumptions uncertainties and rollback',all(plan.get(k) for k in ('requirements','assumptions','uncertainties','prerequisites','rollback_strategy')),plan)
 ck('planning is read-only and provider-free',not any(plan[k] for k in ('workspace_prepared','provider_contacted','source_modified','approval_granted','installation_authorized','promotion_authorized')),plan)
 revised=revise_plan_from_evidence(plan,failed_reason='missing_import',new_prerequisite='resolve import dependency')
 ck('plan revision records invalidated assumption evidence',revised['plan_digest']!=plan['plan_digest'] and 'resolve import dependency' in revised['prerequisites'],revised)
 ck('planning evidence contains no source body',all('source_text' not in str(v) for v in plan.values()),plan)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1493-dynamic-implementation-planning','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
