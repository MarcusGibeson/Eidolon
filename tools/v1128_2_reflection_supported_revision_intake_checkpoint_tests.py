from pathlib import Path
import tempfile, subprocess, sys, json
from conscious_agent.reflection_supported_revision_intake_checkpoint import build_reflection_supported_revision_intake_checkpoint
from conscious_agent.api_server import dispatch_api
root=Path(tempfile.mkdtemp());source=Path(__file__).resolve().parents[1];r=build_reflection_supported_revision_intake_checkpoint(root,source_root=source);checks=[r['ok'],r['contract_version']=='v1128.2',len(r['checks'])==18,all(x['status']=='pass' for x in r['checks']),not r['runtime_mutated'],not r['source_modified'],not r['raw_content_exposed'],not r['hidden_reasoning_exposed'],not r['belief_revised'],not r['motivation_revised'],not r['goal_revised'],not r['self_model_revised'],not r['provider_contacted'],not r['message_sent'],not r['external_action_executed']]
cli=subprocess.run([sys.executable,str(source/'eidolon.py'),'reflection-supported-revision-intake-checkpoint'],cwd=source,text=True,capture_output=True);checks.append(cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1128.2')
status,payload=dispatch_api('GET','/api/cognition/reflection-supported-revision-intake-checkpoint');checks.append(status==200 and payload['data']['contract_version']=='v1128.2');status2,_=dispatch_api('POST','/api/cognition/reflection-supported-revision-intake-checkpoint',body={});checks.append(status2!=200)
print(f"v1128.2 reflection-supported revision intake checkpoint tests: {sum(checks)}/{len(checks)} passed");raise SystemExit(0 if all(checks) else 1)
