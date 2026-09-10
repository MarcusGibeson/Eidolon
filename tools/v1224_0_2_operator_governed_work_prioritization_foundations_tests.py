from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1224-a-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import operator_governed_work_prioritization_scheduling as priority
from v1224_prioritization_fixture import build_prioritization_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_prioritization_fixture("v1224-foundations"); rt=f["runtime"]
try:
 row=priority.build_operator_governed_work_prioritization(runtime_root=rt)
 require(row["ok"] is True,row); require(row["status"]=="operator_governed_work_prioritization_ready")
 require(row["item_count"]==3,row); require(row["eligible_item_count"]==2,row)
 require(row["generation"]==1); require(len(row["prioritization_digest"])==64)
 require(len(row["source_queue_digest"])==64); require(row["recommended_queue_item_id"].startswith("work_"))
 require([x["rank"] for x in row["items"]]==[1,2,3])
 require(all(x["old_authority_reusable"] is False for x in row["items"]))
 require(all("objective_evidence" in x and "heuristic_reasons" in x for x in row["items"]))
 require(any(x["state"]=="blocked" and x["schedule_eligible"] is False for x in row["items"]))
 require(sum(1 for x in row["items"] if x["schedule_eligible"])==2)
 require(row["schedule_is_planning_evidence_only"] is True)
 require(row["ranking_execution_authorized"] is False); require(row["work_dispatch_authorized"] is False)
 public=priority.public_operator_governed_work_prioritization(row)
 blob=json.dumps(public,sort_keys=True)
 require(f["other_private_path"] not in blob); require(f["third_private_path"] not in blob)
 require("Private Project Two" not in blob and "Private Project Three" not in blob)
 require(public["private_path_exposed"] is False); require(public["project_name_exposed"] is False)
 replay=priority.build_operator_governed_work_prioritization(runtime_root=rt)
 require(replay["operation_status"]=="resumed",replay); require(replay["generation"]==1)
 require(replay["prioritization_digest"]==row["prioritization_digest"])
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1224.2","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"operator_governed":True,"execution_authorized":False},sort_keys=True))
