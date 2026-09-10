from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.temporal_review_checkpoint import build_temporal_review_checkpoint
from conscious_agent.api_server import dispatch_api
p=0
def req(x):
 global p;assert x;p+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td);before=list(root.rglob('*'));r=build_temporal_review_checkpoint(root,source_root=ROOT);req(r['contract_version']=='v1117.5');req(r['ok']);req(r['runtime_mutated'] is False and before==list(root.rglob('*')));req(len(r['checks'])==10 and all(x['status']=='pass' for x in r['checks']));req(not r['hidden_reasoning_exposed']);req(not any(r[k] for k in ('notification_created','schedule_changed','attention_selected','intention_formed','proposal_created','approval_granted','authorization_granted','external_action_executed')));env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(root/'cli');z=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'temporal-review-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);req(z.returncode==0 and json.loads(z.stdout)['contract_version']=='v1117.5');os.environ['EIDOLON_DATA_DIR']=str(root/'api');status,payload=dispatch_api('GET','/api/cognition/temporal-review-checkpoint');req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1117.5');post,_=dispatch_api('POST','/api/cognition/temporal-review-checkpoint',body={});req(post in (404,405));dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();req('temporal-review-checkpoint-panel' in dash)
print(json.dumps({'passed':p,'total':10,'suite':'v1117.5'}))
