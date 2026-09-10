from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1221-b-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import unified_supervised_development_transaction_history as history
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1221-conversation"); rt=f["runtime"]; p=f["proposal"]; review=f["rollback_result_review"]
try:
 decision_phrase=next(x for x in review["decision_phrases"] if "defer" in x)
 final_turn=process_ordinary_chat_development_turn(decision_phrase,runtime_root=rt)
 require(final_turn["event"]=="operator_repaired_candidate_rollback_result_decision_recorded")
 require((final_turn.get("unified_supervised_development_transaction_history") or {}).get("ok") is True)
 command=f"Show supervised development transaction history proposal {p['proposal_id']} revision 1 page 2 size 5."
 turn=process_ordinary_chat_development_turn(command,runtime_root=rt)
 require(turn["active"] is True,turn); require(turn["event"]=="unified_supervised_development_transaction_history_ready")
 row=turn["unified_supervised_development_transaction_history"]
 require(row["page"]==2); require(row["page_size"]==5); require(row["page_event_count"]==5)
 require(row["events_included"] is True); require(len(row["events"])==5)
 require("underlying receipts remain authoritative" in turn["conversation_response"])
 status_command=f"Show unified supervised development transaction status proposal {p['proposal_id']} revision 1."
 status_turn=process_ordinary_chat_development_turn(status_command,runtime_root=rt)
 status=status_turn["unified_supervised_development_transaction_history"]
 require(status["events_included"] is False); require(status["events"]==[])
 require(status["current_state"]=="rollback_result_deferred")
 oversize=history.process_unified_supervised_development_transaction_history_control(
  f"Show supervised development transaction history proposal {p['proposal_id']} revision 1 page 1 size 51.",runtime_root=rt)
 require(oversize["active"] is True)
 require(oversize["unified_supervised_development_transaction_history"]["status"]=="unified_supervised_development_transaction_history_page_invalid")
finally: shutil.rmtree(rt,ignore_errors=True)
for casual in ("Show me what happened.","I wish I had a transaction history.",'She said "show supervised development transaction history".'):
 require(history.process_unified_supervised_development_transaction_history_control(casual)=={"active":False,"event":"inactive"})
print(json.dumps({"ok":True,"version":"1221.5","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"ordinary_chat_history_inspection":True,"bounded_pagination":True,"release_authorized":False},sort_keys=True))
