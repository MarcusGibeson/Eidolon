import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.api_server import dispatch_api
from conscious_agent.cognitive_sustainability_review_checkpoint import build_cognitive_sustainability_review_checkpoint
p=t=0
def c(n,x):
 global p,t;t+=1
 if x:p+=1
 else:raise AssertionError(n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);before=list(r.rglob('*'));x=build_cognitive_sustainability_review_checkpoint(r,source_root=ROOT);c('contract',x['contract_version']=='v1116.8');c('ok',x['ok']);c('readonly',not x['runtime_mutated'] and before==list(r.rglob('*')));c('checks',len(x['checks'])==13 and all(i['status']=='pass' for i in x['checks']));c('privacy',not x['raw_messages_exposed'] and not x['hidden_reasoning_exposed']);c('authority',not any(x[k] for k in ('schedule_changed','work_paused','work_resumed','adaptation_applied','attention_selected','authorization_granted','external_action_executed')));env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');z=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'cognitive-sustainability-review-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);c('cli',z.returncode==0 and json.loads(z.stdout)['contract_version']=='v1116.8');os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api');status,payload=dispatch_api('GET','/api/cognition/cognitive-sustainability-review-checkpoint');c('api',status==200 and (payload.get('data') or {}).get('contract_version')=='v1116.8');post,_=dispatch_api('POST','/api/cognition/cognitive-sustainability-review-checkpoint',body={});c('post',post in (404,405));source=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();c('dashboard','cognitive-sustainability-review-checkpoint' in source)
print(json.dumps({'passed':p,'total':t,'suite':'v1116.8'}))
