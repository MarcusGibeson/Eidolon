from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True; ROOT=Path(__file__).resolve().parents[1]; os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="v1225c-")); sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import supervised_work_dispatch_execution_session_preparation as d
from ordinary_chat_development_campaign import create_or_resume_development_proposal
from unified_development_work_queue import build_unified_development_work_queue
from v1225_dispatch_fixture import build_dispatch_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_dispatch_fixture("v1225-reliability"); rt=f["runtime"]
try:
 slot=f["schedule"]["slots"][0]; stale=d.prepare_development_execution_session(slot["queue_item_id"],expected_schedule_digest="0"*64,runtime_root=rt); r(stale["ok"] is False and stale["reason"]=="stale_schedule_digest",stale)
 miss=d.prepare_development_execution_session("work_"+"f"*24,expected_schedule_digest=f["schedule"]["schedule_digest"],runtime_root=rt); r(miss["ok"] is False and miss["reason"]=="schedule_item_missing",miss)
 row=d.prepare_development_execution_session(slot["queue_item_id"],expected_schedule_digest=f["schedule"]["schedule_digest"],runtime_root=rt); r(row["ok"] is True,row)
 bad=d.record_prepared_execution_session_review("accept",session_id=row["session_id"],expected_session_digest="0"*64,runtime_root=rt); r(bad["ok"] is False and bad["reason"]=="stale_session_digest",bad)
 create_or_resume_development_proposal("Build another bounded utility",project_state={"id":"project-four","name":"Private Four","path":str(Path(rt)/"private-four")},runtime_root=rt); q=build_unified_development_work_queue(runtime_root=rt); r(q["generation"]>=2,q)
 expired=d.inspect_prepared_development_execution_session(row["session_id"],runtime_root=rt); r(expired["ok"] is False and expired["status"]=="prepared_development_execution_session_expired",expired); r("stale" in expired["reason"] or "current" in expired["reason"]); r(expired["execution_session_launch_authorized"] is False)
 p=d._session_path(row["session_id"],rt); data=json.loads(p.read_text()); data["priority_level"]="critical"; p.write_text(json.dumps(data)); r(d.load_prepared_development_execution_session(row["session_id"],runtime_root=rt)=={})
 blocked=d.record_prepared_execution_session_review("accept",session_id=row["session_id"],expected_session_digest=row["session_digest"],runtime_root=rt); r(blocked["ok"] is False,blocked); blob=json.dumps(blocked,sort_keys=True); r(f["other_private_path"] not in blob and f["third_private_path"] not in blob and "private-four" not in blob); r(blocked["provider_contacted"] is False and blocked["commands_executed"] is False); r(blocked["tests_executed"] is False and blocked["project_modified"] is False); r(blocked["background_execution_authorized"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1225.8","checks":len(C),"passed":sum(C),"elapsed_seconds":round(time.monotonic()-S,4),"stale_and_tamper_closed":True,"launch_authorized":False},sort_keys=True))
