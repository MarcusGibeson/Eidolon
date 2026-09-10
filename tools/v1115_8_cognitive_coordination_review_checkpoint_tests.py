from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.cognitive_coordination_review_checkpoint import build_cognitive_coordination_review_checkpoint
from conscious_agent.api_server import dispatch_api
p=t=0
def c(n,x):
 global p,t;t+=1;p+=bool(x)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';q=build_cognitive_coordination_review_checkpoint(r,source_root=ROOT);c('contract',q['contract_version']=='v1115.8');c('ok',q['ok']);c('readonly',not q['runtime_mutated']);c('checks',len(q['checks'])==12 and all(x['status']=='pass' for x in q['checks']));c('separation',not any(q[k] for k in ('attention_selected','intention_formed','decision_committed','schedule_changed','adaptation_applied','proposal_created','approval_granted','authorization_granted','external_action_executed')));c('privacy',not q['raw_content_exposed'] and not q['hidden_reasoning_exposed']);env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');z=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'cognitive-coordination-review-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);c('cli',z.returncode==0 and json.loads(z.stdout)['contract_version']=='v1115.8');os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api');status,payload=dispatch_api('GET','/api/cognition/cognitive-coordination-review-checkpoint');c('api',status==200 and (payload.get('data') or {}).get('contract_version')=='v1115.8');c('summary',q['summary']['outcome_count']==0);c('desktop',q['status']=='ready_for_desktop_verification')
print(json.dumps({'passed':p,'total':t,'suite':'v1115.8'}));raise SystemExit(0 if p==t else 1)
