from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.sandbox_test_evidence_diagnosis import build_sandbox_test_evidence, diagnose_sandbox_test_evidence, sandbox_test_diagnosis_public_summary
checks=[]
def req(v): checks.append(bool(v))
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def signed_receipt(status='passed', rows=None, block_reason=''):
    r={
      'schema_version':'1','contract_version':'v1182.2','content_free':True,'sandbox_only':True,
      'source_modified':False,'execution_status':status,'tests_executed':status!='blocked',
      'target_path':'conscious_agent/example.py','attempt_digest':'a'*64,'review_digest':'b'*64,
      'materialization_receipt_digest':'c'*64,'sandbox_target_digest':'d'*64,
      'test_count':len(rows or []),'test_results':rows or [],'block_reason':block_reason,
      'production_source_read':False,'production_source_modified':False,'shell_invoked':False,
      'tool_invoked':False,'provider_contacted':False,'model_contacted':False}
    r['test_receipt_digest']=digest(r); return r
passed=signed_receipt(rows=[{'test':'python_compile','status':'passed','error_class':''},{'test':'content_digest_match','status':'passed','error_class':'','result_digest':'d'*64}])
ev=build_sandbox_test_evidence(passed)
req(ev['evidence_status']=='verified' and ev['test_count']==2 and not ev['root_cause_proven'])
diag=diagnose_sandbox_test_evidence(ev)
req(diag['diagnosis_posture']=='no_diagnosed_failure' and diag['diagnosis_count']==0)
failed=signed_receipt('failed',[{'test':'python_compile','status':'failed','error_class':'python_compile_failed'}])
fdiag=diagnose_sandbox_test_evidence(build_sandbox_test_evidence(failed))
req(fdiag['diagnosis_candidates'][0]['diagnosis_code']=='python_compile_failure_observed')
req(fdiag['diagnosis_candidates'][0]['confidence']=='high_observation_low_root_cause')
timed=signed_receipt('timed_out',[{'test':'python_compile','status':'timed_out','error_class':'test_timeout'}])
tdiag=diagnose_sandbox_test_evidence(build_sandbox_test_evidence(timed))
req(tdiag['diagnosis_candidates'][0]['diagnosis_code']=='sandbox_test_timeout_observed')
blocked=signed_receipt('blocked',[],block_reason='sandbox_target_drift')
bdiag=diagnose_sandbox_test_evidence(build_sandbox_test_evidence(blocked))
req(bdiag['diagnosis_candidates'][0]['diagnosis_code']=='sandbox_test_execution_blocked')
req('sandbox_target_drift' in bdiag['diagnosis_candidates'][0]['supported_conclusion'])
tampered={**passed,'test_count':3}
req(build_sandbox_test_evidence(tampered)['block_reason']=='invalid_test_receipt')
bad={**passed}; bad.pop('test_receipt_digest'); req(build_sandbox_test_evidence(bad)['block_reason']=='invalid_test_receipt')
bad2=signed_receipt('failed',[{'test':'python_compile','status':'failed','error_class':''}])
req(build_sandbox_test_evidence(bad2)['block_reason']=='incomplete_executed_test_evidence')
bad3=signed_receipt('passed',[{'test':'shell_command','status':'passed','error_class':''}])
req(build_sandbox_test_evidence(bad3)['block_reason']=='incomplete_executed_test_evidence')
req(diagnose_sandbox_test_evidence({'contract_version':'v1182.5'})['block_reason']=='invalid_evidence_contract')
summary=sandbox_test_diagnosis_public_summary(fdiag)
req(summary['content_free'] and not summary['authority_granted'] and not summary['source_modified'])
req(not summary['root_cause_proven'] and not summary['repair_authorized'] and not summary['retest_authorized'])
blob=json.dumps(summary).lower()
req('stdout' not in blob and 'stderr' not in blob and 'def broken' not in blob)
req('repair_created' in summary and not summary['repair_created'] and not summary['tests_rerun'])
source=(ROOT/'conscious_agent/sandbox_test_evidence_diagnosis.py').read_text()
req('subprocess' not in source and 'open(' not in source and 'write_' not in source)
req('root_cause_proven": False' in source and 'repair_authorized": False' in source)
req('provider_contacted": False' in source and 'release_authorized": False' in source)
print(json.dumps({'ok':all(checks),'suite':'v1182.3-v1182.5-sandbox-test-evidence-diagnosis-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
if not all(checks): print([i+1 for i,v in enumerate(checks) if not v]); raise SystemExit(1)
