from pathlib import Path
import json, os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.supervised_isolated_sandbox_execution_integration_checkpoint import build_supervised_isolated_sandbox_execution_integration_checkpoint
from conscious_agent.api_server import dispatch_api
def main():
 with tempfile.TemporaryDirectory() as td:
  out=build_supervised_isolated_sandbox_execution_integration_checkpoint(Path(td),source_root=ROOT); assert out["ok"] and len(out["checks"])==20 and not out["runtime_mutated"] and not out["source_modified"]
 with tempfile.TemporaryDirectory() as td:
  env=dict(os.environ); env["EIDOLON_DATA_DIR"]=td; cli=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"supervised-isolated-sandbox-execution-integration-checkpoint"],cwd=ROOT,env=env,text=True,capture_output=True); assert cli.returncode==0 and json.loads(cli.stdout)["contract_version"]=="v1140.8"
 status,payload=dispatch_api("GET","/api/cognition/supervised-isolated-sandbox-execution-integration-checkpoint"); assert status==200 and payload["data"]["contract_version"]=="v1140.8"
 post,_=dispatch_api("POST","/api/cognition/supervised-isolated-sandbox-execution-integration-checkpoint",body={}); assert post!=200
 dashboard=(ROOT/"conscious_agent"/"dashboard_first_use.py").read_text(); assert "supervised-isolated-sandbox-execution-integration-checkpoint-panel" in dashboard and "/api/cognition/supervised-isolated-sandbox-execution-integration-checkpoint" in dashboard
 print("v1140.8 supervised isolated sandbox execution integration checkpoint: 5/5 passed")
if __name__=="__main__": main()
