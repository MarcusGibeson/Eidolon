from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1222-c-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import _atomic_json, _digest, _store_root
import transaction_resumption_abandoned_work_reconciliation as resume
import unified_supervised_development_transaction_history as history
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1222-reliability"); rt=f["runtime"]; p=f["proposal"]
try:
 first=resume.build_transaction_resumption_assessment(p["proposal_id"],expected_revision=1,runtime_root=rt)
 phrase=next(x for x in first["decision_phrases"] if "defer" in x)
 event={"contract_version":"v1221.8","proposal_id":p["proposal_id"],"revision":1,"revision_digest":"a"*64,
        "event_type":"operator_follow_up_recorded","created_at":"2099-01-01T00:00:00Z","details":{},
        "content_free":True,"request_text_included":False,"private_path_included":False,
        "provider_contacted":False,"implementation_started":False,"authority_granted":False}
 event["event_digest"]=_digest(event)
 _atomic_json(_store_root(rt)/"events"/p["proposal_id"]/"999999.json",event)
 refreshed_history=history.build_unified_supervised_development_transaction_history(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(refreshed_history["generation"]==2,refreshed_history)
 stale=resume.process_transaction_resumption_control(phrase,runtime_root=rt)
 require(stale["event"]=="transaction_resumption_decision_stale_or_mismatched",stale)
 refreshed=resume.build_transaction_resumption_assessment(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(refreshed["operation_status"]=="refreshed",refreshed)
 require(refreshed["assessment_generation"]==2)
 require(refreshed["previous_assessment_digest"]==first["assessment_digest"])
 require(resume._assessment_snapshot_path(p["proposal_id"],1,1,rt).is_file())
 require(resume._assessment_snapshot_path(p["proposal_id"],1,2,rt).is_file())
 public=resume.public_transaction_resumption(refreshed)
 require(str(rt) not in json.dumps(public))
 require(public["private_request_exposed"] is False)
 require(public["private_content_exposed"] is False)
 require(public["authority_granted"] is False)
 path=resume._assessment_path(p["proposal_id"],1,rt)
 raw=json.loads(path.read_text()); raw["classification"]="forged"; path.write_text(json.dumps(raw))
 require(resume.load_transaction_resumption_assessment(p["proposal_id"],1,runtime_root=rt)=={})
 blocked=resume.build_transaction_resumption_assessment(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(blocked["status"]=="transaction_resumption_assessment_record_invalid",blocked)
 require(blocked["project_modified"] is False)
 require(blocked["authority_granted"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
synthetic={"events":[{"stage":"approval","status":"interrupted","authority_consumed":True,"operator_decision":"","decision_state":""}],"gap_count":0,"terminal":False}
classified=resume.classify_transaction_history(synthetic)
require(classified["classification"]=="restart_required",classified)
require("old_authority_cannot_be_reused" in classified["reason_codes"])
print(json.dumps({"ok":True,"version":"1222.8","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"stale_history_rejected":True,"tamper_closed":True,"release_authorized":False},sort_keys=True))
