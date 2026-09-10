from pathlib import Path
import tempfile, json, os, subprocess, sys
from conscious_agent.reflective_execution_continuity_checkpoint import build_reflective_execution_continuity_checkpoint
from conscious_agent.api_server import dispatch_api
root=Path(tempfile.mkdtemp());report=build_reflective_execution_continuity_checkpoint(root,source_root=Path(__file__).resolve().parents[1]);checks=[report["contract_version"]=="v1125.5",report["passed"]==18,report["total"]==18,report["ok"],not report["runtime_mutated"],not report["source_modified"],not report["message_sent"],not report["notification_created"],not report["belief_updated"],not report["initiative_created"],not report["external_action_executed"],report["desktop_verification_pending"]]
env=dict(os.environ);env["EIDOLON_DATA_DIR"]=str(root.parent);cli=subprocess.run([sys.executable,"eidolon.py","reflective-execution-continuity-checkpoint","--json"],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True);checks += [cli.returncode==0,json.loads(cli.stdout)["contract_version"]=="v1125.5"]
status,payload=dispatch_api("GET","/api/cognition/reflective-execution-continuity-checkpoint");checks += [status==200,payload["data"]["contract_version"]=="v1125.5"]
dash=(Path(__file__).resolve().parents[1]/"conscious_agent/dashboard_first_use.py").read_text();checks += ["reflective-execution-continuity-checkpoint-panel" in dash,"reflective-execution-continuity-checkpoint" in dash]
print(json.dumps({"passed":sum(checks),"total":18,"suite":"v1125.5"}));raise SystemExit(0 if all(checks) else 1)
