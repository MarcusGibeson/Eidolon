from pathlib import Path
import json, os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.deficiency_signals import DeficiencySignalStore
from conscious_agent.deficiency_candidates import DeficiencyCandidateStore
from conscious_agent.supervised_deficiency_intake_checkpoint import build_supervised_deficiency_intake_checkpoint
from conscious_agent.api_server import dispatch_api
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=DeficiencySignalStore(root); a=s.register("e1",origin_ids=["checkpoint:1"],source_categories=["failed_checkpoint"],deficiency_category="reliability_deficiency",component_ids=["component:alpha"],project_digest="a"*64,scope_digest="b"*64,evidence_ids=["evidence:1"],recurrence_count=3,reproducibility=.9,severity=.8,urgency=.2,confidence=.9,uncertainty=.1); DeficiencyCandidateStore(root).register("c1",signal_ids=[a["result"]["signal_id"]])
 report=build_supervised_deficiency_intake_checkpoint(root,source_root=ROOT); assert report["ok"] and len(report["checks"])==20 and not report["runtime_mutated"] and not report["source_modified"]
 env=dict(os.environ); env["EIDOLON_DATA_DIR"]=td; cli=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"supervised-deficiency-intake-checkpoint"],cwd=ROOT,env=env,text=True,capture_output=True); assert cli.returncode==0 and json.loads(cli.stdout)["contract_version"]=="v1135.2"
 old=os.environ.get("EIDOLON_DATA_DIR"); os.environ["EIDOLON_DATA_DIR"]=td
 try: status,payload=dispatch_api("GET","/api/cognition/supervised-deficiency-intake-checkpoint"); assert status==200 and payload["data"]["contract_version"]=="v1135.2"
 finally:
  if old is None: os.environ.pop("EIDOLON_DATA_DIR",None)
  else: os.environ["EIDOLON_DATA_DIR"]=old
 assert dispatch_api("POST","/api/cognition/supervised-deficiency-intake-checkpoint")[0] != 200
 assert report["desktop_verification"]=="pending" and not report["hidden_reasoning_exposed"]
print("v1135.2 supervised deficiency intake checkpoint: 8/8 passed")
