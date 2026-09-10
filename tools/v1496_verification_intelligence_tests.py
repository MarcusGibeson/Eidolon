from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1496-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.verification_intelligence import verification_plan,classify_receipt,evaluate_verification
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 plan=verification_plan(changed_files=['conscious_agent/sample.py'],candidate_test_files=['tools/sample_tests.py'])
 ck('verification plan includes compile immutability privacy',all(x in plan['suites'] for x in ('python_compile','source_immutability','source_only_privacy')),plan)
 ck('source changes add focused retained regression classes',all(x in plan['suites'] for x in ('focused_behavioral','retained_architecture')),plan)
 sec=verification_plan(changed_files=['conscious_agent/release_authority.py']);ck('authority changes demand security regression', 'security_authority_regression' in sec['suites'],sec)
 ck('wrapper timeout classified separately',classify_receipt({'passed':False,'timed_out':True,'assertions_failed':0})=='wrapper_timeout')
 ck('provider unavailable classified separately',classify_receipt({'passed':False,'provider_available':False})=='provider_unavailable')
 ck('baseline-identical failure classified as inherited',classify_receipt({'passed':False,'baseline_same':True})=='stale_fixture_or_inherited_failure')
 receipts=[{'suite':'python_compile','passed':True},{'suite':'source_immutability','passed':True},{'suite':'source_only_privacy','passed':True},{'suite':'tools/sample_tests.py','passed':True},{'suite':'focused_behavioral','passed':True},{'suite':'retained_architecture','passed':True}]
 ev=evaluate_verification(plan,receipts);ck('complete required evidence passes verification',ev['verification_passed'],ev)
 incomplete=evaluate_verification(plan,receipts[:-1]);ck('missing retained regression evidence blocks verification',not incomplete['verification_passed'] and 'retained_architecture' in incomplete['missing_required_suites'],incomplete)
 failed=evaluate_verification(plan,receipts+[{'suite':'focused','passed':False}]);ck('real product failure blocks verification',not failed['verification_passed'] and failed['product_failure_count']==1,failed)
 ck('verification evidence cannot authorize install or promotion',not ev['source_install_authorized'] and not ev['promotion_authorized'],ev)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1496-verification-intelligence','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
