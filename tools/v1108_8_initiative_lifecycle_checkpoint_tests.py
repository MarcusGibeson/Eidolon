from pathlib import Path
import tempfile, os, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
def run():
 root=Path(tempfile.mkdtemp())/'cognition'
 from conscious_agent.initiative_lifecycle_checkpoint import build_initiative_lifecycle_checkpoint
 c=build_initiative_lifecycle_checkpoint(root,source_root=ROOT)
 from conscious_agent.api_server import dispatch_api
 os.environ['EIDOLON_DATA_DIR']=str(root.parent); status,p=dispatch_api('GET','/api/cognition/initiative-lifecycle-checkpoint')
 env=dict(os.environ); q=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'initiative-lifecycle-checkpoint','--json'],capture_output=True,text=True,env=env,timeout=60)
 html=(ROOT/'conscious_agent/dashboard_first_use.py').read_text()
 checks=[c['contract_version']=='v1108.8',c['runtime_mutated'] is False,c['message_sent'] is False,c['automatic_retry'] is False,status==200,(p.get('data') or {}).get('contract_version')=='v1108.8',q.returncode==0,json.loads(q.stdout)['contract_version']=='v1108.8','initiative-lifecycle-checkpoint-panel' in html]
 print('v1108.8',sum(checks),'/',len(checks)); return all(checks)
if __name__=='__main__': raise SystemExit(0 if run() else 1)
