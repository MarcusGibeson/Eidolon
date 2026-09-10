from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1221-a-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import unified_supervised_development_transaction_history as history
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1221-foundations"); rt=f["runtime"]; p=f["proposal"]; review=f["rollback_result_review"]
try:
 phrase=next(x for x in review["decision_phrases"] if "accept-rollback-result" in x)
 turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
 attached=turn.get("unified_supervised_development_transaction_history") or {}
 require(attached.get("ok") is True,turn)
 require(attached.get("history_is_derivative") is True)
 require(attached.get("authoritative_receipts_preserved") is True)
 row=history.build_unified_supervised_development_transaction_history(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(row["ok"] is True,row); require(row["status"]=="unified_supervised_development_transaction_history_ready")
 require(row["event_count"]>=20,row); require(row["stage_count"]>=20,row)
 require(row["gap_count"]==0,row.get("coverage")); require(row["terminal"] is True)
 require(row["current_state"]=="rollback_result_accepted")
 require(row["generation"]==1); require(row["operation_status"]=="resumed")
 require(row["events"][0]["sequence"]==1)
 require(row["events"][-1]["stage"]=="rollback-result-decision")
 require(all(event["sequence"]==i for i,event in enumerate(row["events"],start=1)))
 require(all(len(event["transaction_event_digest"])==64 for event in row["events"]))
 public=history.public_unified_supervised_development_transaction_history(row,page=1,page_size=7)
 require(public["page_event_count"]==7); require(public["has_next_page"] is True)
 require(public["content_free"] is True); require(public["private_path_exposed"] is False)
 require(public["authority_granted"] is False); require(public["release_authorized"] is False)
 require(str(f["source_workspace_root"]) not in json.dumps(public))
 require(str(f["repaired_workspace_root"]) not in json.dumps(public))
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1221.2","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"unified_history_ready":True,"authoritative_receipts_preserved":True,"release_authorized":False},sort_keys=True))
