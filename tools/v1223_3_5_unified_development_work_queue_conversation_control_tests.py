from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1223-b-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import unified_development_work_queue as queue
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1223-conversation"); rt=f["runtime"]
try:
 show=process_ordinary_chat_development_turn("Show unified development work queue.",runtime_root=rt)
 require(show["active"] is True,show); require(show["event"]=="unified_development_work_queue_ready",show)
 row=show["unified_development_work_queue"]; require(row["item_count"]==1,row)
 item=row["items"][0]
 project=process_ordinary_chat_development_turn(f"Show development project state {item['project_reference']}.",runtime_root=rt)
 require(project["unified_development_work_queue"]["project_count"]==1,project)
 blocked=process_ordinary_chat_development_turn("Show blocked development work.",runtime_root=rt)
 require(blocked["active"] is True); require(blocked["unified_development_work_queue"]["filter"]=="blocked")
 focus=process_ordinary_chat_development_turn(item["focus_phrase"],runtime_root=rt)
 require(focus["event"]=="unified_development_work_queue_focus_recorded",focus)
 require(focus["unified_development_work_queue"]["authority_granted"] is False)
 focus_replay=process_ordinary_chat_development_turn(item["focus_phrase"],runtime_root=rt)
 require(focus_replay["unified_development_work_queue"]["operation_status"]=="resumed",focus_replay)
 current=queue.build_unified_development_work_queue(runtime_root=rt); item=current["items"][0]
 defer=process_ordinary_chat_development_turn(item["defer_phrase"],runtime_root=rt)
 require(defer["event"]=="unified_development_work_queue_item_action_recorded",defer)
 require(defer["unified_development_work_queue"]["action"]=="defer")
 replay=process_ordinary_chat_development_turn(item["defer_phrase"],runtime_root=rt)
 require(replay["unified_development_work_queue"]["operation_status"]=="resumed",replay)
 deferred=process_ordinary_chat_development_turn("Show deferred development work.",runtime_root=rt)
 require(deferred["unified_development_work_queue"]["item_count"]==1,deferred)
 deferred_item=deferred["unified_development_work_queue"]["items"][0]
 reopen=process_ordinary_chat_development_turn(deferred_item["reopen_phrase"],runtime_root=rt)
 require(reopen["event"]=="unified_development_work_queue_item_action_recorded",reopen)
 proposal=reopen["unified_development_work_queue"]["reopen_proposal"]
 require(proposal["status"]=="unified_development_work_queue_reopen_proposal_ready",proposal)
 require(proposal["fresh_authority_required"] is True)
 require(proposal["prior_authority_reusable"] is False)
 require(proposal["approval_consumed"] is False)
 require(proposal["continuation_executed"] is False)
 require(proposal["approval_phrase"].startswith("Approve development work queue reopen proposal "))
 require(reopen["unified_development_work_queue"]["project_modified"] is False)
 require(reopen["unified_development_work_queue"]["authority_granted"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
for casual in ("Show me what you are working on sometime.","It would be nice to focus this project.",'She said "show unified development work queue".'):
 require(queue.process_unified_development_work_queue_control(casual)=={"active":False,"event":"inactive"})
print(json.dumps({"ok":True,"version":"1223.5","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"ordinary_chat_controls":True,"fresh_reopen_approval_required":True,"release_authorized":False},sort_keys=True))
