from pathlib import Path
import tempfile, subprocess, sys, os, json
ROOT=Path(__file__).resolve().parents[1]
def run():
 root=Path(tempfile.mkdtemp())/'cognition';from conscious_agent.persistent_initiative_checkpoint import build_persistent_initiative_checkpoint;c=build_persistent_initiative_checkpoint(root,source_root=ROOT);from conscious_agent.api_server import dispatch_api;os.environ['EIDOLON_DATA_DIR']=str(root.parent);status,p=dispatch_api('GET','/api/cognition/persistent-initiative-checkpoint');env=dict(os.environ);q=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'persistent-initiative-checkpoint','--json'],capture_output=True,text=True,env=env,timeout=60);tests=[c['contract_version']=='v1108.2',c['runtime_mutated'] is False,status==200,(p.get('data') or {}).get('contract_version')=='v1108.2',q.returncode==0,json.loads(q.stdout)['contract_version']=='v1108.2']
 print({'suite':'v1108.2','passed':sum(tests),'total':len(tests)});return all(tests)
if __name__=='__main__':raise SystemExit(0 if run() else 1)
