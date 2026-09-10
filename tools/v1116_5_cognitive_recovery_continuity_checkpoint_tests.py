from pathlib import Path
import json,tempfile,sys,os,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.cognitive_recovery_continuity_checkpoint import build_cognitive_recovery_continuity_checkpoint
from conscious_agent.api_server import dispatch_api
passed=0
def check(n,v):
 global passed
 if not v:raise AssertionError(n)
 passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td);before=list(root.rglob("*"));r=build_cognitive_recovery_continuity_checkpoint(root,source_root=ROOT);check("contract",r["contract_version"]=="v1116.5");check("ok",r["ok"]);check("readonly",not r["runtime_mutated"] and before==list(root.rglob("*")));check("checks",len(r["checks"])==13 and all(x["status"]=="pass" for x in r["checks"]));check("privacy",not r["raw_messages_exposed"] and not r["hidden_reasoning_exposed"]);check("authority",not any(r[k] for k in ("schedule_changed","work_paused","work_resumed","adaptation_applied","attention_selected","authorization_granted","external_action_executed")));env=dict(os.environ);env["EIDOLON_DATA_DIR"]=str(Path(td)/"cli");p=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"cognitive-recovery-continuity-checkpoint","--json"],cwd=ROOT,env=env,text=True,capture_output=True);check("cli",p.returncode==0 and json.loads(p.stdout)["contract_version"]=="v1116.5");os.environ["EIDOLON_DATA_DIR"]=str(Path(td)/"api");status,payload=dispatch_api("GET","/api/cognition/cognitive-recovery-continuity-checkpoint");check("api",status==200 and (payload.get("data") or {}).get("contract_version")=="v1116.5");post,_=dispatch_api("POST","/api/cognition/cognitive-recovery-continuity-checkpoint",body={});check("post",post in (404,405));source=(ROOT/"conscious_agent"/"dashboard_first_use.py").read_text();check("dashboard","cognitive-recovery-continuity-checkpoint" in source)
print(json.dumps({"passed":passed,"total":10,"suite":"v1116.5"}))
