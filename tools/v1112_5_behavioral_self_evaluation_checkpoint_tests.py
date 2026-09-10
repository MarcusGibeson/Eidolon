from pathlib import Path
import tempfile,os,sys,json,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def req(x):
 if not x:raise AssertionError
base=Path(tempfile.mkdtemp());root=base/'runtime'/'cognition'
def snap():
 return sorted((p.relative_to(root).as_posix(),p.stat().st_size,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()) if root.exists() else []
before=snap();from conscious_agent.behavioral_self_evaluation_checkpoint import build_behavioral_self_evaluation_checkpoint
c=build_behavioral_self_evaluation_checkpoint(root,source_root=ROOT);req(before==snap());req(c['contract_version']=='v1112.5' and c['runtime_mutated'] is False);req(all(x['status']=='pass' for x in c['checks']));req(not c['behavior_changed'] and not c['adaptation_proposal_created'] and not c['authorization_granted'])
from conscious_agent.api_server import dispatch_api;os.environ['EIDOLON_DATA_DIR']=str(base/'runtime');status,p=dispatch_api('GET','/api/cognition/behavioral-self-evaluation-checkpoint');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1112.5');status2,_=dispatch_api('POST','/api/cognition/behavioral-self-evaluation-checkpoint',body={});req(status2!=200)
run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'behavioral-self-evaluation-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(run.returncode==0 and json.loads(run.stdout)['contract_version']=='v1112.5');dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('behavioral-self-evaluation-checkpoint-panel' in dash and '/api/cognition/behavioral-self-evaluation-checkpoint' in dash);req(not c['hidden_reasoning_exposed']);print('{"passed":10,"total":10,"suite":"v1112.5"}')
