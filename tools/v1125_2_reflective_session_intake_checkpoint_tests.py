import json,tempfile,subprocess,sys,os
from pathlib import Path
from conscious_agent.reflective_session_intake_checkpoint import build_reflective_session_intake_checkpoint
root=Path(tempfile.mkdtemp());report=build_reflective_session_intake_checkpoint(root,source_root=Path(__file__).resolve().parents[1])
checks=[report['contract_version']=='v1125.2',report['passed']==18,report['total']==18,report['ok'],report['runtime_mutated'] is False,report['source_modified'] is False,report['message_sent'] is False,report['belief_updated'] is False,report['goal_updated'] is False,report['self_model_updated'] is False,report['provider_payloads_exposed'] is False,report['hidden_reasoning_exposed'] is False,report['desktop_verification_pending'] is True]
env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(root.parent);env['PYTHONPATH']=str(Path(__file__).resolve().parents[1])
cli=subprocess.run([sys.executable,'eidolon.py','reflective-session-intake-checkpoint','--json'],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True)
checks += [cli.returncode==0, json.loads(cli.stdout)['contract_version']=='v1125.2']
from conscious_agent.api_server import dispatch_api
status,payload=dispatch_api('GET','/api/cognition/reflective-session-intake-checkpoint')
checks += [status==200,payload['data']['contract_version']=='v1125.2']
dash=(Path(__file__).resolve().parents[1]/'conscious_agent/dashboard_first_use.py').read_text()
checks += ['reflective-session-intake-checkpoint-panel' in dash]
print(json.dumps({'passed':sum(checks),'total':18,'suite':'v1125.2'}));raise SystemExit(0 if all(checks) else 1)
