from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'cognition';env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td))
  from conscious_agent.privacy_security_continuity import PrivacySecurityContinuityStore
  PrivacySecurityContinuityStore(root).record_cycle('cycle-a')
  from conscious_agent.privacy_security_hardening_reliability_checkpoint import build_privacy_security_hardening_reliability_checkpoint
  r=build_privacy_security_hardening_reliability_checkpoint(root,source_root=ROOT)
  checks += [r['contract_version']=='v1148.8',r['ok'],r['passed']==r['total'],r['read_only'],not r['post_available'],not r['source_modified'],not r['runtime_mutated'],not r['raw_content_exposed'],not r['provider_payload_exposed'],not r['hidden_reasoning_exposed'],r['desktop_verification_pending'],not r['consciousness_proven']]
  cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'privacy-security-hardening-reliability-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90);checks.append(cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1148.8')
  from conscious_agent.api_server import dispatch_api
  old=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(Path(td))
  try:
   status,payload=dispatch_api('GET','/api/cognition/privacy-security-hardening-reliability-checkpoint');post,_=dispatch_api('POST','/api/cognition/privacy-security-hardening-reliability-checkpoint',body={'confirm':True})
  finally:
   if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
   else: os.environ['EIDOLON_DATA_DIR']=old
  checks += [status==200 and payload['data']['contract_version']=='v1148.8',post in (404,405)]
  dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();checks += ['privacy-security-hardening-reliability-checkpoint-panel' in dash,'loadPrivacySecurityHardeningReliabilityCheckpoint' in dash]
 print(f'v1148.8 privacy/security reliability checkpoint tests: {sum(checks)}/{len(checks)} passed')
 return 0 if all(checks) else 1
if __name__=='__main__': raise SystemExit(main())
