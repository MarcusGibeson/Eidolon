from pathlib import Path
import tempfile, os, sys, json, subprocess
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.reflective_attention_salience_intake_checkpoint import build_reflective_attention_salience_intake_checkpoint
from conscious_agent.api_server import dispatch_api
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); before=list(root.rglob('*')); report=build_reflective_attention_salience_intake_checkpoint(root,source_root=ROOT)
 req(report['contract_version']=='v1123.2'); req(report['ok'] and report['status']=='ready_for_desktop_verification'); req(report['runtime_mutated'] is False and before==list(root.rglob('*'))); req(report['check_count']==20 and all(x['status']=='pass' for x in report['checks']))
 req(not any(report[k] for k in ('raw_messages_exposed','raw_content_exposed','prompts_exposed','provider_payloads_exposed','evidence_text_exposed','motivational_text_exposed','identity_text_exposed','objective_text_exposed','hidden_reasoning_exposed','private_content_exposed')))
 req(not any(report[k] for k in ('attention_selected','reflection_created','intention_created','initiative_created','message_sent','notification_created','proposal_created','approval_granted','authorization_granted','external_action_executed','provider_contacted','browsing_performed','schedule_mutated','release_promoted','release_certified')))
 env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(root/'cli'); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'reflective-attention-salience-intake-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=60); req(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1123.2')
 os.environ['EIDOLON_DATA_DIR']=str(root/'api'); status,payload=dispatch_api('GET','/api/cognition/reflective-attention-salience-intake-checkpoint'); req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1123.2')
 post,_=dispatch_api('POST','/api/cognition/reflective-attention-salience-intake-checkpoint',body={}); req(post in (404,405))
 dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); req('reflective-attention-salience-intake-checkpoint-panel' in dash and '/api/cognition/reflective-attention-salience-intake-checkpoint' in dash)
print(f"v1123.2 reflective attention salience intake checkpoint: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
