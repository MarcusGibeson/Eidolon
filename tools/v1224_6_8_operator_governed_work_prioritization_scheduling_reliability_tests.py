from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1224-c-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import operator_governed_work_prioritization_scheduling as priority
from ordinary_chat_development_campaign import create_or_resume_development_proposal
from v1224_prioritization_fixture import build_prioritization_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_prioritization_fixture("v1224-reliability"); rt=f["runtime"]
try:
 row=priority.build_operator_governed_work_prioritization(runtime_root=rt)
 eligible=[x for x in row["items"] if x["schedule_eligible"]]; a,b=eligible[:2]
 bad=priority.record_work_priority_override(a["queue_item_id"],expected_prioritization_digest="0"*64,priority_level="high",runtime_root=rt)
 require(bad["ok"] is False and bad["reason"]=="stale_prioritization_digest",bad)
 selfdep=priority.record_work_priority_override(a["queue_item_id"],expected_prioritization_digest=row["prioritization_digest"],dependency_item_id=a["queue_item_id"],dependency_action="add",runtime_root=rt)
 require(selfdep["ok"] is False and "dependency_binding" in selfdep["reason"],selfdep)
 one=priority.record_work_priority_override(a["queue_item_id"],expected_prioritization_digest=row["prioritization_digest"],dependency_item_id=b["queue_item_id"],dependency_action="add",runtime_root=rt)
 require(one["ok"] is True,one); current=one["refreshed_prioritization"]
 two=priority.record_work_priority_override(b["queue_item_id"],expected_prioritization_digest=current["prioritization_digest"],dependency_item_id=a["queue_item_id"],dependency_action="add",runtime_root=rt)
 require(two["ok"] is True,two); cycle=two["refreshed_prioritization"]
 require(sum(1 for x in cycle["items"] if x["dependency_cycle"])==2,cycle["items"])
 require(sum(1 for x in cycle["items"] if x["schedule_eligible"])==0,cycle["items"])
 rejected=priority.record_work_prioritization_review("reject",expected_prioritization_digest=cycle["prioritization_digest"],runtime_root=rt)
 require(rejected["ok"] is True,rejected)
 blocked_schedule=priority.prepare_operator_governed_work_schedule(expected_prioritization_digest=cycle["prioritization_digest"],runtime_root=rt)
 require(blocked_schedule["ok"] is False and blocked_schedule["reason"]=="prioritization_not_accepted",blocked_schedule)
 conflict=priority.record_work_prioritization_review("accept",expected_prioritization_digest=cycle["prioritization_digest"],runtime_root=rt)
 require(conflict["ok"] is False and conflict["reason"]=="conflicting_prioritization_review",conflict)
 # New queue evidence invalidates an existing prioritization.
 create_or_resume_development_proposal("Build another tool",project_state={"id":"project-four","name":"Private Four","path":str(Path(rt)/"private-four")},runtime_root=rt)
 from unified_development_work_queue import build_unified_development_work_queue
 q=build_unified_development_work_queue(runtime_root=rt)
 require(q["generation"]>=2,q)
 stale=priority.record_work_prioritization_review("accept",expected_prioritization_digest=cycle["prioritization_digest"],runtime_root=rt)
 require(stale["ok"] is False and stale["reason"]=="stale_source_queue",stale)
 # Tamper detection closes construction.
 p=priority._override_path(a["queue_item_id"],rt); data=json.loads(p.read_text()); data["priority_level"]="critical"; p.write_text(json.dumps(data))
 tampered=priority.build_operator_governed_work_prioritization(runtime_root=rt)
 require(tampered["ok"] is False and "tampered" in tampered["reason"],tampered)
 blob=json.dumps(tampered,sort_keys=True)
 require(f["other_private_path"] not in blob and f["third_private_path"] not in blob)
 require(tampered["authority_granted"] is False); require(tampered["background_execution_authorized"] is False)
 require(tampered["project_modified"] is False and tampered["source_modified"] is False)
 require(tampered["provider_contacted"] is False and tampered["tests_executed"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1224.8","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"stale_and_tamper_closed":True,"execution_authorized":False},sort_keys=True))
