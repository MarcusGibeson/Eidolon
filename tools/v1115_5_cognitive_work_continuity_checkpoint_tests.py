import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
from conscious_agent.cognitive_work_scheduling import CognitiveWorkScheduler
from conscious_agent.cognitive_work_continuity_checkpoint import build_cognitive_work_continuity_checkpoint
from conscious_agent.api_server import dispatch_api
p=t=0
def c(n,x):
 global p,t;t+=1
 if not x:raise AssertionError(n)
 p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';d=CognitiveDemandStore(r);did=d.register('d',origin_type='intention',origin_id='i')['result']['demand_id'];aid=CognitiveLoadArbitrator(r).allocate('a',demand_ids=[did])['result']['allocation_id'];CognitiveWorkScheduler(r).schedule('s',demand_id=did,allocation_id=aid);before={x.name:x.read_bytes() for x in r.glob('*.json')};q=build_cognitive_work_continuity_checkpoint(r,source_root=ROOT);after={x.name:x.read_bytes() for x in r.glob('*.json')};c('contract',q['contract_version']=='v1115.5');c('ready',q['ok']);c('readonly',before==after and not q['runtime_mutated']);c('checks',len(q['checks'])==12 and all(x['status']=='pass' for x in q['checks']));c('separation',not any(q[k] for k in ('attention_selected','intention_formed','decision_committed','proposal_created','approval_granted','authorization_granted','external_action_executed')));c('privacy',not q['hidden_reasoning_exposed']);env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');z=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'cognitive-work-continuity-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);c('cli',z.returncode==0 and json.loads(z.stdout)['contract_version']=='v1115.5');os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api');status,payload=dispatch_api('GET','/api/cognition/cognitive-work-continuity-checkpoint');c('api',status==200 and (payload.get('data') or {}).get('contract_version')=='v1115.5');c('runtime_external',q['runtime_external']);c('summary',q['summary']['work_item_count']==1)
print(json.dumps({'passed':p,'total':t,'suite':'v1115.5'}))
