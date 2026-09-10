import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ['PYTHONDONTWRITEBYTECODE']='1'
from conscious_agent.privacy_security_test_catalog import build_privacy_security_test_catalog
from conscious_agent.privacy_security_bounded_execution import PrivacySecurityBoundedExecutionStore,build_privacy_security_bounded_execution_inspection
checks=[]
with tempfile.TemporaryDirectory() as td:
 store=PrivacySecurityBoundedExecutionStore(Path(td));scenario=build_privacy_security_test_catalog()['scenarios'][0]
 r=store.execute('event-1',scenario_id=scenario['scenario_id']);checks += [r['state']=='awaiting_confirmation']
 r2=store.execute('event-2',scenario_id=scenario['scenario_id'],operator_confirmation_id='operator-confirm-1',observed_outcome=scenario['expected_outcome'],steps_used=1,attempts_used=1,runtime_ms=20);checks += [r2['state']=='passed']
 checks += [store.execute('event-2',scenario_id=scenario['scenario_id'],operator_confirmation_id='x')['idempotent']]
 r3=store.execute('event-3',scenario_id=build_privacy_security_test_catalog()['scenarios'][1]['scenario_id'],operator_confirmation_id='operator-confirm-2',observed_outcome='deny',steps_used=9,attempts_used=1,runtime_ms=20);checks += [r3['state']=='review_required']
 r4=store.execute('event-4',scenario_id=build_privacy_security_test_catalog()['scenarios'][2]['scenario_id'],operator_confirmation_id='operator-confirm-3',timed_out=True,runtime_ms=251);checks += [r4['state']=='timed_out']
 i=build_privacy_security_bounded_execution_inspection(Path(td));checks += [i['record_count']==4,not i['raw_content_exposed'],not i['provider_payload_exposed'],not any(i['authority_boundary'].values()),all(x['provider_tokens_used']==0 for x in i['recent_records'])]
 try:store.execute('bad',scenario_id='missing')
 except ValueError:checks.append(True)
 else:checks.append(False)
assert all(checks),[i+1 for i,v in enumerate(checks) if not v]
print(json.dumps({'suite':'v1148.3','passed':len(checks),'total':len(checks)}))
