from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True; ROOT=Path(__file__).resolve().parents[1]; os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="v1225b-")); sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import supervised_work_dispatch_execution_session_preparation as d
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1225_dispatch_fixture import build_dispatch_fixture
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
f=build_dispatch_fixture("v1225-review"); rt=f["runtime"]
try:
 slot=f["schedule"]["slots"][0]; cmd=f"Prepare development execution session for item {slot['queue_item_id']} schedule {f['schedule']['schedule_digest']}."; turn=process_ordinary_chat_development_turn(cmd,runtime_root=rt); r(turn["active"] is True,turn); r(turn["event"]=="prepared_development_execution_session_ready",turn); s=turn["supervised_work_dispatch"]; r("fresh launch authorization" in turn["conversation_response"].lower())
 acc=process_ordinary_chat_development_turn(s["accept_phrase"],runtime_root=rt); r(acc["event"]=="prepared_development_execution_session_accepted",acc); rv=acc["supervised_work_dispatch"]
 for v in [rv["launch_readiness_established"] is True,rv["fresh_launch_authorization_required"] is True,rv["execution_session_launch_authorized"] is False,rv["provider_contacted"] is False and rv["commands_executed"] is False]: r(v,rv)
 r(process_ordinary_chat_development_turn(s["accept_phrase"],runtime_root=rt)["event"]=="prepared_development_execution_session_accepted")
 conflict=process_ordinary_chat_development_turn(s["reject_phrase"],runtime_root=rt); r(conflict["event"]=="prepared_execution_session_review_blocked",conflict); r(conflict["supervised_work_dispatch"]["reason"]=="conflicting_prepared_session_review")
 listed=process_ordinary_chat_development_turn("Show prepared development execution sessions.",runtime_root=rt); r(listed["event"]=="prepared_development_execution_session_list_ready",listed); r(listed["supervised_work_dispatch"]["session_count"]==1); r(listed["supervised_work_dispatch"]["reviews"][0]["decision"]=="accept"); r(listed["supervised_work_dispatch"]["reviews"][0]["execution_session_launch_authorized"] is False); r(d.process_supervised_work_dispatch_control("It would be nice to prepare a session someday.",runtime_root=rt)["active"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1225.5","checks":len(C),"passed":sum(C),"elapsed_seconds":round(time.monotonic()-S,4),"operator_reviewed":True,"execution_launched":False},sort_keys=True))
