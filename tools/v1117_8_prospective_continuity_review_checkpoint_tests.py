from pathlib import Path
import tempfile, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.prospective_continuity_review_checkpoint import build_prospective_continuity_review_checkpoint
from conscious_agent.api_server import dispatch_api
p=0
def req(x):
 global p; assert x; p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); before=list(r.rglob('*')); x=build_prospective_continuity_review_checkpoint(r,source_root=ROOT); req(x['ok']); req(x['contract_version']=='v1117.8'); req(len(x['checks'])==10 and all(y['status']=='pass' for y in x['checks'])); req(before==list(r.rglob('*')) and x['runtime_mutated'] is False); req(not x['hidden_reasoning_exposed']); req(not any(x[k] for k in ('notification_created','schedule_changed','attention_selected','intention_formed','proposal_applied','approval_granted','authorization_granted','external_action_executed'))); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(r/'cli'); z=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'prospective-continuity-review-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True); req(z.returncode==0 and json.loads(z.stdout)['contract_version']=='v1117.8'); os.environ['EIDOLON_DATA_DIR']=str(r/'api'); status,payload=dispatch_api('GET','/api/cognition/prospective-continuity-review-checkpoint'); req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1117.8'); post,_=dispatch_api('POST','/api/cognition/prospective-continuity-review-checkpoint',body={}); req(post in (404,405)); req('prospective-continuity-review-checkpoint-panel' in (ROOT/'conscious_agent'/'dashboard_first_use.py').read_text())
print(json.dumps({'passed':p,'total':10,'suite':'v1117.8'}))
