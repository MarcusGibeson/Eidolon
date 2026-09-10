import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ['PYTHONDONTWRITEBYTECODE']='1'
from conscious_agent.privacy_security_test_catalog import build_privacy_security_test_catalog
from conscious_agent.privacy_security_bounded_execution import PrivacySecurityBoundedExecutionStore
from conscious_agent.privacy_security_findings_receipts import PrivacySecurityFindingReceiptStore,build_privacy_security_findings_receipts_inspection
checks=[]
with tempfile.TemporaryDirectory() as td:
 root=Path(td);scenario=build_privacy_security_test_catalog()['scenarios'][0];e=PrivacySecurityBoundedExecutionStore(root).execute('e1',scenario_id=scenario['scenario_id'],operator_confirmation_id='c1',observed_outcome='deny',steps_used=1,attempts_used=1,runtime_ms=10)
 store=PrivacySecurityFindingReceiptStore(root);r=store.record('f1',execution_id=e['execution_id']);checks += [r['state']=='no_finding']
 r2=store.record('f2',execution_id=e['execution_id'],finding_code='boundary_variance',severity=3,contained=True);checks += [r2['state']=='contained']
 r3=store.record('f3',execution_id=e['execution_id'],finding_code='recovery_check',severity=4,recovery_attempted=True,recovery_succeeded=True);checks += [r3['state']=='recovered']
 r4=store.record('f4',execution_id=e['execution_id'],finding_code='recovery_check',severity=4,recovery_attempted=True,recovery_succeeded=False);checks += [r4['state']=='recovery_failed']
 checks += [store.record('f4',execution_id=e['execution_id'])['idempotent']]
 i=build_privacy_security_findings_receipts_inspection(root);checks += [i['record_count']==4,not i['raw_content_exposed'],not i['provider_payload_exposed'],not any(i['authority_boundary'].values()),all(not x['raw_evidence_recorded'] for x in i['recent_records'])]
 try:store.record('bad',execution_id='missing')
 except ValueError:checks.append(True)
 else:checks.append(False)
assert all(checks),[i+1 for i,v in enumerate(checks) if not v]
print(json.dumps({'suite':'v1148.4','passed':len(checks),'total':len(checks)}))
