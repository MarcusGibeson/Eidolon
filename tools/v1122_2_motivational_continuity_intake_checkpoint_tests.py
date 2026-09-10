from pathlib import Path
import tempfile, os, sys, json, subprocess
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.motivational_continuity_intake_checkpoint import build_motivational_continuity_intake_checkpoint
from conscious_agent.api_server import dispatch_api
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); before=list(root.rglob('*')); r=build_motivational_continuity_intake_checkpoint(root,source_root=ROOT); req(r['contract_version']=='v1122.2'); req(r['ok']); req(r['runtime_mutated'] is False and before==list(root.rglob('*'))); req(len(r['checks'])==16 and all(x['status']=='pass' for x in r['checks'])); req(not r['hidden_reasoning_exposed'] and not r['motivation_text_exposed']); req(not any(r[k] for k in ('attention_selected','initiative_created','message_sent','notification_created','proposal_created','approval_granted','authorization_granted','external_action_executed','provider_contacted','browsing_performed'))); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(root/'cli'); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'motivational-continuity-intake-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True); req(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1122.2'); os.environ['EIDOLON_DATA_DIR']=str(root/'api'); status,payload=dispatch_api('GET','/api/cognition/motivational-continuity-intake-checkpoint'); req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1122.2'); post,_=dispatch_api('POST','/api/cognition/motivational-continuity-intake-checkpoint',body={}); req(post in (404,405)); dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); req('motivational-continuity-intake-checkpoint-panel' in dash)
print(f"v1122.2 motivational continuity intake checkpoint: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
