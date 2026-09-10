from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1224-b-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import operator_governed_work_prioritization_scheduling as priority
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1224_prioritization_fixture import build_prioritization_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_prioritization_fixture("v1224-review"); rt=f["runtime"]
try:
 row=priority.build_operator_governed_work_prioritization(runtime_root=rt)
 eligible=[x for x in row["items"] if x["schedule_eligible"]]
 first,second=eligible[0],eligible[1]
 cmd=f"Set development work priority critical for item {second['queue_item_id']} prioritization {row['prioritization_digest']}."
 turn=process_ordinary_chat_development_turn(cmd,runtime_root=rt)
 require(turn["active"] is True,turn); require(turn["event"]=="operator_governed_work_priority_override_recorded")
 refreshed=turn["operator_governed_work_prioritization"]["refreshed_prioritization"]
 require(refreshed["generation"]==2,refreshed)
 second_row=next(x for x in refreshed["items"] if x["queue_item_id"]==second["queue_item_id"])
 require(second_row["priority_level"]=="critical"); require(second_row["rank"]==1)
 pin_cmd=f"Pin development work item {first['queue_item_id']} prioritization {refreshed['prioritization_digest']}."
 pinned=process_ordinary_chat_development_turn(pin_cmd,runtime_root=rt)
 require(pinned["event"]=="operator_governed_work_priority_override_recorded",pinned)
 current=pinned["operator_governed_work_prioritization"]["refreshed_prioritization"]
 require(next(x for x in current["items"] if x["queue_item_id"]==first["queue_item_id"])["rank"]==1)
 dep_cmd=f"Add development work dependency {second['queue_item_id']} on {first['queue_item_id']} prioritization {current['prioritization_digest']}."
 dep=process_ordinary_chat_development_turn(dep_cmd,runtime_root=rt)
 require(dep["event"]=="operator_governed_work_priority_override_recorded",dep)
 current=dep["operator_governed_work_prioritization"]["refreshed_prioritization"]
 dep_row=next(x for x in current["items"] if x["queue_item_id"]==second["queue_item_id"])
 require(dep_row["dependency_item_ids"]==[first["queue_item_id"]])
 accept=process_ordinary_chat_development_turn(current["accept_phrase"],runtime_root=rt)
 require(accept["event"]=="operator_governed_work_prioritization_accepted",accept)
 require(accept["operator_governed_work_prioritization"]["schedule_preparation_allowed"] is True)
 schedule_turn=process_ordinary_chat_development_turn(current["prepare_schedule_phrase"],runtime_root=rt)
 schedule=schedule_turn["operator_governed_work_prioritization"]
 require(schedule_turn["event"]=="operator_governed_work_schedule_ready",schedule_turn)
 require(schedule["slot_count"]==2,schedule)
 require(schedule["slots"][0]["queue_item_id"]==first["queue_item_id"],schedule["slots"])
 require(schedule["slots"][1]["queue_item_id"]==second["queue_item_id"],schedule["slots"])
 require(all(x["execution_authorized"] is False for x in schedule["slots"]))
 sched_accept=process_ordinary_chat_development_turn(schedule["accept_phrase"],runtime_root=rt)
 require(sched_accept["event"]=="operator_governed_work_schedule_accepted",sched_accept)
 sr=sched_accept["operator_governed_work_prioritization"]
 require(sr["bounded_work_order_approved"] is True); require(sr["execution_authorized"] is False)
 replay=process_ordinary_chat_development_turn(schedule["accept_phrase"],runtime_root=rt)
 require(replay["event"]=="operator_governed_work_schedule_accepted")
 casual=priority.process_operator_governed_work_prioritization_control("It would be nice to prioritize things someday.",runtime_root=rt)
 require(casual.get("active") is False)
 require(sr["provider_contacted"] is False and sr["project_modified"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1224.5","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"schedule_planning_only":True,"execution_authorized":False},sort_keys=True))
