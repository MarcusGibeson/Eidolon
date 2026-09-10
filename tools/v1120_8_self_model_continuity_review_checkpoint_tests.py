from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.self_model_continuity_review_checkpoint import build_self_model_continuity_review_checkpoint
from conscious_agent.api_server import dispatch_api
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); before=list(root.rglob("*")); r=build_self_model_continuity_review_checkpoint(root,source_root=ROOT); req(r["contract_version"]=="v1120.8"); req(r["ok"]); req(r["runtime_mutated"] is False and before==list(root.rglob("*"))); req(len(r["checks"])==18 and all(x["status"]=="pass" for x in r["checks"])); req(not r["hidden_reasoning_exposed"] and not r["claim_text_exposed"]); req(not any(r[k] for k in ("identity_revised","self_model_revised","temporary_state_promoted","attention_selected","decision_committed","proposal_applied","approval_granted","authorization_granted","external_action_executed"))); env=dict(os.environ); env["EIDOLON_DATA_DIR"]=str(root/"cli"); p=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"self-model-continuity-review-checkpoint","--json"],cwd=ROOT,env=env,text=True,capture_output=True); req(p.returncode==0 and json.loads(p.stdout)["contract_version"]=="v1120.8"); os.environ["EIDOLON_DATA_DIR"]=str(root/"api"); status,payload=dispatch_api("GET","/api/cognition/self-model-continuity-review-checkpoint"); req(status==200 and (payload.get("data") or {}).get("contract_version")=="v1120.8"); post,_=dispatch_api("POST","/api/cognition/self-model-continuity-review-checkpoint",body={}); req(post in (404,405)); dash=(ROOT/"conscious_agent"/"dashboard_first_use.py").read_text(); req("self-model-continuity-review-checkpoint-panel" in dash)
print(json.dumps({"passed":passed,"total":10,"suite":"v1120.8"}))
