from pathlib import Path
import tempfile, os, sys, json, subprocess
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.reflective_attention_deliberation_checkpoint import build_reflective_attention_deliberation_checkpoint
from conscious_agent.api_server import dispatch_api
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); before=list(root.rglob('*')); x=build_reflective_attention_deliberation_checkpoint(root,source_root=ROOT); req(x['ok'] and x['contract_version']=='v1123.5'); req(x['status']=='ready_for_desktop_verification'); req(x['check_count']==19 and all(r['status']=='pass' for r in x['checks'])); req(before==list(root.rglob('*')) and not x['runtime_mutated']); req(not any(x[k] for k in ('attention_selected','reflection_created','intention_created','initiative_created','message_sent','notification_created','proposal_created','approval_granted','authorization_granted','external_action_executed','provider_contacted','browsing_performed','schedule_mutated','release_promoted','release_certified'))); req(not x['hidden_reasoning_exposed'])
 env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(root/'cli'); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'reflective-attention-deliberation-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=60); req(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1123.5')
 os.environ['EIDOLON_DATA_DIR']=str(root/'api'); status,payload=dispatch_api('GET','/api/cognition/reflective-attention-deliberation-checkpoint'); req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1123.5')
 post,_=dispatch_api('POST','/api/cognition/reflective-attention-deliberation-checkpoint',body={}); req(post in (404,405))
 dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); req('reflective-attention-deliberation-checkpoint-panel' in dash and '/api/cognition/reflective-attention-deliberation-checkpoint' in dash)
print(f"v1123.5 reflective attention deliberation checkpoint: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
