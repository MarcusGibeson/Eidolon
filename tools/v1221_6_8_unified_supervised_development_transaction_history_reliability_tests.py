from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1221-c-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn, _atomic_json, _digest, _store_root
import unified_supervised_development_transaction_history as history
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1221-reliability"); rt=f["runtime"]; p=f["proposal"]; review=f["rollback_result_review"]
try:
 phrase=next(x for x in review["decision_phrases"] if "reject-rollback-result" in x)
 process_ordinary_chat_development_turn(phrase,runtime_root=rt)
 first=history.load_unified_supervised_development_transaction_history(p["proposal_id"],1,runtime_root=rt)
 require(first and first["generation"]==1,first)
 # Add a later authoritative campaign event and verify append-only history refresh lineage.
 event={"contract_version":"v1221.8","proposal_id":p["proposal_id"],"revision":1,"revision_digest":"a"*64,
        "event_type":"operator_follow_up_recorded","created_at":"2099-01-01T00:00:00Z","details":{},
        "content_free":True,"request_text_included":False,"private_path_included":False,
        "provider_contacted":False,"implementation_started":False,"authority_granted":False}
 event["event_digest"]=_digest(event)
 event_path=_store_root(rt)/"events"/p["proposal_id"]/"999999.json"
 _atomic_json(event_path,event)
 refreshed=history.build_unified_supervised_development_transaction_history(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(refreshed["operation_status"]=="refreshed",refreshed)
 require(refreshed["generation"]==2); require(refreshed["previous_history_digest"]==first["history_digest"])
 require(refreshed["event_count"]==first["event_count"]+1)
 require(history._snapshot_path(p["proposal_id"],1,1,rt).is_file())
 require(history._snapshot_path(p["proposal_id"],1,2,rt).is_file())
 replay=history.build_unified_supervised_development_transaction_history(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(replay["operation_status"]=="resumed"); require(replay["generation"]==2)
 public=history.public_unified_supervised_development_transaction_history(refreshed,page=999,page_size=10)
 require(public["page_event_count"]==0); require(public["has_previous_page"] is True)
 require(str(rt) not in json.dumps(public)); require(public["private_path_exposed"] is False)
 # Tamper the derived index. Loading and rebuilding fail closed; receipts remain untouched.
 current_path=history._history_path(p["proposal_id"],1,rt)
 raw=json.loads(current_path.read_text()); raw["current_state"]="forged"; current_path.write_text(json.dumps(raw))
 require(history.load_unified_supervised_development_transaction_history(p["proposal_id"],1,runtime_root=rt)=={})
 blocked=history.build_unified_supervised_development_transaction_history(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(blocked["status"]=="unified_supervised_development_transaction_history_record_invalid")
 require(blocked["project_modified"] is False); require(blocked["authority_granted"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1221.8","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"refresh_lineage_preserved":True,"tamper_closed":True,"release_authorized":False},sort_keys=True))
