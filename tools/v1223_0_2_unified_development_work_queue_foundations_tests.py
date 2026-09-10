from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1223-a-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import unified_development_work_queue as queue
from ordinary_chat_development_campaign import create_or_resume_development_proposal
from v1223_work_queue_fixture import build_work_queue_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_work_queue_fixture("v1223-foundations"); rt=f["runtime"]
try:
 row=queue.build_unified_development_work_queue(runtime_root=rt)
 require(row["ok"] is True,row); require(row["status"]=="unified_development_work_queue_ready")
 require(row["item_count"]==2,row); require(row["project_count"]==2,row)
 require(row["generation"]==1); require(len(row["queue_digest"])==64)
 require(set(row["state_counts"])==set(queue.QUEUE_STATES))
 require(any(x["state"]=="awaiting_approval" for x in row["items"]),row["items"])
 require(all(x["project_reference"].startswith("project_") for x in row["items"]))
 require(all(len(x["project_identity_digest"])==64 for x in row["items"]))
 public=queue.public_unified_development_work_queue(row)
 blob=json.dumps(public,sort_keys=True)
 require(f["other_private_path"] not in blob)
 require("Private Project Two" not in blob)
 require(public["private_path_exposed"] is False)
 require(public["project_name_exposed"] is False)
 require(public["authority_granted"] is False)
 require(public["project_modified"] is False)
 replay=queue.build_unified_development_work_queue(runtime_root=rt)
 require(replay["operation_status"]=="resumed",replay)
 require(replay["generation"]==1)
 # A second open proposal for the same exact project is detected and blocked.
 duplicate=create_or_resume_development_proposal(
   "Build a second JavaScript helper",
   project_state={"id":"project-two","name":"Private Project Two","path":f["other_private_path"]},
   runtime_root=rt,
 )
 require(duplicate["proposal_id"]!=f["other_proposal"]["proposal_id"])
 refreshed=queue.build_unified_development_work_queue(runtime_root=rt)
 require(refreshed["generation"]==2,refreshed)
 conflicts=[x for x in refreshed["items"] if x["project_reference"]==next(y["project_reference"] for y in row["items"] if y["proposal_id"]==f["other_proposal"]["proposal_id"])]
 require(len(conflicts)==2,conflicts)
 require(all(x["duplicate_active_conflict"] is True and x["state"]=="blocked" for x in conflicts),conflicts)
 require(any(p["duplicate_active_conflict"] is True for p in refreshed["projects"]))
 require(all(x["old_authority_reusable"] is False for x in refreshed["items"]))
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1223.2","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"project_identity_digest_only":True,"duplicate_active_conflict_blocked":True,"release_authorized":False},sort_keys=True))
