import json,tempfile,subprocess,sys
from pathlib import Path
from conscious_agent.continuous_thought_intake_checkpoint import build_continuous_thought_intake_checkpoint
from conscious_agent.api_server import dispatch_api
root=Path(tempfile.mkdtemp());source=Path(__file__).resolve().parents[1];r=build_continuous_thought_intake_checkpoint(root,source_root=source);checks=[r['ok'],r['contract_version']=='v1127.2',len(r['checks'])==18,all(x['status']=='pass' for x in r['checks']),not r['runtime_mutated'],not r['source_modified'],not r['raw_content_exposed'],not r['hidden_reasoning_exposed'],not r['provider_contacted'],not r['belief_updated'],not r['goal_updated'],not r['self_model_updated'],not r['message_sent'],not r['initiative_created'],not r['external_action_executed']]
cli=subprocess.run([sys.executable,str(source/'eidolon.py'),'continuous-thought-intake-checkpoint'],cwd=source,text=True,capture_output=True);checks.append(cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1127.2')
status,payload=dispatch_api('GET','/api/cognition/continuous-thought-intake-checkpoint');checks.append(status==200 and payload['data']['contract_version']=='v1127.2')
status2,_=dispatch_api('POST','/api/cognition/continuous-thought-intake-checkpoint',body={});checks.append(status2!=200)
print(json.dumps({'passed':sum(checks),'total':18,'suite':'v1127.2'}));raise SystemExit(0 if all(checks) else 1)
