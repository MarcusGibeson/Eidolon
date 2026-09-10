import json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ['PYTHONDONTWRITEBYTECODE']='1'
from conscious_agent.privacy_security_test_catalog import build_privacy_security_test_catalog
from conscious_agent.privacy_security_bounded_execution import PrivacySecurityBoundedExecutionStore
from conscious_agent.privacy_security_findings_receipts import PrivacySecurityFindingReceiptStore
from conscious_agent.privacy_security_hardening_execution_checkpoint import build_privacy_security_hardening_execution_checkpoint
checks=[]
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/'runtime';scenario=build_privacy_security_test_catalog()['scenarios'][0];e=PrivacySecurityBoundedExecutionStore(root).execute('e1',scenario_id=scenario['scenario_id'],operator_confirmation_id='confirm',observed_outcome='deny',steps_used=1,attempts_used=1,runtime_ms=10);PrivacySecurityFindingReceiptStore(root).record('f1',execution_id=e['execution_id'],finding_code='none')
 report=build_privacy_security_hardening_execution_checkpoint(root,source_root=ROOT)
 checks += [report['contract_version']=='v1148.5',report['checkpoint_id']=='privacy-security-hardening-execution:v1148.5',report['ok'] and report['status']=='ready_for_bundle_c',report['passed']==report['total']==19,report['read_only'] and not report['post_available'],not report['runtime_mutated'] and not report['source_modified'],report['summary']['execution_count']==1,report['summary']['finding_count']==1,not report['raw_content_exposed'],not report['provider_payload_exposed'],report['desktop_verification_pending'] and not report['consciousness_proven']]
 env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(root.parent/'cli');cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'privacy-security-hardening-execution-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90);checks.append(cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1148.5')
 old=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(root.parent/'api')
 try:
  from conscious_agent.api_server import dispatch_api
  status,payload=dispatch_api('GET','/api/cognition/privacy-security-hardening-execution-checkpoint');checks.append(status==200 and payload['data']['contract_version']=='v1148.5')
  post,_=dispatch_api('POST','/api/cognition/privacy-security-hardening-execution-checkpoint',body={'confirm':True});checks.append(post in (404,405))
 finally:
  if old is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=old
 dashboard=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');checks.append('privacy-security-hardening-execution-checkpoint-panel' in dashboard and 'loadPrivacySecurityHardeningExecutionCheckpoint' in dashboard)
 metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8');working=re.search(r'WORKING_SOURCE_VERSION = "([^"]+)"',metadata);previous=re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "([^"]+)"',metadata);current_version=tuple(int(part) for part in working.group(1).split('.')) if working else ();previous_version=tuple(int(part) for part in previous.group(1).split('.')) if previous else ();checks.append(bool(current_version>=(1148,5) and (current_version!=(1148,5) or previous_version==(1148,4))))
 checks.append('v1148.5 Privacy and Security Hardening Execution Checkpoint' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'))
assert all(checks),[i+1 for i,v in enumerate(checks) if not v]
print(json.dumps({'suite':'v1148.5','passed':len(checks),'total':len(checks)}))
