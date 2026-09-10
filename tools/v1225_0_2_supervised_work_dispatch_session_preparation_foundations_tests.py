from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True; ROOT=Path(__file__).resolve().parents[1]; os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="v1225a-")); sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import supervised_work_dispatch_execution_session_preparation as d
from v1225_dispatch_fixture import build_dispatch_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_dispatch_fixture("v1225-foundations"); rt=f["runtime"]
try:
 slot=f["schedule"]["slots"][0]; row=d.prepare_development_execution_session(slot["queue_item_id"],expected_schedule_digest=f["schedule"]["schedule_digest"],runtime_root=rt)
 for v in [row["ok"] is True,row["status"]=="prepared_development_execution_session_ready",row["session_id"].startswith("session_"),len(row["session_digest"])==64,row["queue_item_id"]==slot["queue_item_id"],row["project_reference"]==slot["project_reference"],row["source_schedule_digest"]==f["schedule"]["schedule_digest"],row["source_schedule_slot_digest"]==slot["schedule_slot_digest"],row["requirements"]["fresh_isolated_workspace_required"] is True,row["requirements"]["goal_alignment_review_required"] is True,row["requirements"]["uncertainty_review_required"] is True,row["requirements"]["outcome_reflection_required"] is True,row["fresh_launch_authorization_required"] is True,row["execution_session_launch_authorized"] is False,row["provider_execution_authorized"] is False,row["command_execution_authorized"] is False,row["test_execution_authorized"] is False,row["workspace_created"] is False and row["project_modified"] is False,row["cognition_written"] is False]: r(v,row)
 blob=json.dumps(d._public_session(row),sort_keys=True); r(f["other_private_path"] not in blob and f["third_private_path"] not in blob); r("Private Project" not in blob); r(d._public_session(row)["private_path_exposed"] is False)
 replay=d.prepare_development_execution_session(slot["queue_item_id"],expected_schedule_digest=f["schedule"]["schedule_digest"],runtime_root=rt); r(replay["operation_status"]=="resumed",replay); r(replay["session_digest"]==row["session_digest"])
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1225.2","checks":len(C),"passed":sum(C),"elapsed_seconds":round(time.monotonic()-S,4),"session_preparation_only":True,"launch_authorized":False},sort_keys=True))
