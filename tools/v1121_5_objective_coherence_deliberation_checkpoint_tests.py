from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.objective_coherence_deliberation_checkpoint import build_objective_coherence_deliberation_checkpoint
from conscious_agent.api_server import dispatch_api
p=0
def req(x):
 global p; assert x; p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); before=list(r.rglob('*')); x=build_objective_coherence_deliberation_checkpoint(r,source_root=ROOT); req(x['contract_version']=='v1121.5'); req(x['ok']); req(x['runtime_mutated'] is False and before==list(r.rglob('*'))); req(len(x['checks'])==18 and all(y['status']=='pass' for y in x['checks'])); req(not x['hidden_reasoning_exposed'] and not x['objective_text_exposed']); req(not any(x[k] for k in ('objectives_reprioritized','objective_abandoned','dependency_modified','milestone_modified','attention_selected','decision_committed','proposal_created','approval_granted','authorization_granted','external_action_executed'))); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(r/'cli'); z=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'objective-coherence-deliberation-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True); req(z.returncode==0 and json.loads(z.stdout)['contract_version']=='v1121.5'); os.environ['EIDOLON_DATA_DIR']=str(r/'api'); status,payload=dispatch_api('GET','/api/cognition/objective-coherence-deliberation-checkpoint'); req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1121.5'); post,_=dispatch_api('POST','/api/cognition/objective-coherence-deliberation-checkpoint',body={}); req(post in (404,405)); dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); req('objective-coherence-deliberation-checkpoint-panel' in dash)
print(json.dumps({'passed':p,'total':10,'suite':'v1121.5'}))
