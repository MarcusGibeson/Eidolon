#!/usr/bin/env python3
import hashlib,json,tempfile
from pathlib import Path
from conscious_agent.governed_campaign_work_continuation import *
from conscious_agent.governed_campaign_work_continuation_checkpoint import build_governed_campaign_work_continuation_checkpoint
ROOT=Path(__file__).resolve().parents[1];checks=[]
def req(v,m=""):checks.append(bool(v));assert v,m
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def signed(row,field):
 out=dict(row);out.pop(field,None);out[field]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return out
ledger=signed({"campaign_id":"c1","work_item_ids":["w1","w2","w3"],"content_free":True},"ledger_digest")
prior=signed({"campaign_id":"c1","storage_generation":2,"campaign_state":"active","content_free":True},"storage_record_digest")
for state,actions in (("completed",["select_followup","pause_campaign","complete_campaign"]),("failed",["hold_failure","select_followup","pause_campaign","abandon_campaign"])):
 update=signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","new_work_item_state":state,"status":"ledger_update_recorded","ledger_updated":True,"content_free":True},"ledger_update_receipt_digest")
 for action in actions:
  review=create_campaign_continuation_review(ledger_update_receipt=update,requested_action=action,decision="approve",operator_decision_digest=h(state+action));req(review["status"]=="continuation_approved")
  selection=None
  if action=="select_followup":selection=create_followup_work_selection(ledger=ledger,ledger_update_receipt=update,continuation_review=review,candidate_work_item_ids=["w2","w3"],max_items=1);req(selection["selected_work_item_ids"]==["w2"]);req(not selection["work_executed"])
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"campaigns/c1";p.mkdir(parents=True);(p/"campaign_state.json").write_text(json.dumps(prior),encoding="utf-8")
   stored=persist_continuation_generation(runtime_root=td,prior_storage_record=prior,ledger_update_receipt=update,continuation_review=review,followup_selection=selection,operator_storage_digest=h(action));req(stored["status"]=="continuation_stored");req(stored["storage_generation"]==3);req(not stored["automatic_retry"]);req(not stored["authority_granted"])
for decision,status in (("reject","continuation_rejected"),("defer","continuation_deferred")):
 update=signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","new_work_item_state":"failed","status":"ledger_update_recorded","ledger_updated":True,"content_free":True},"ledger_update_receipt_digest");req(create_campaign_continuation_review(ledger_update_receipt=update,requested_action="hold_failure",decision=decision,operator_decision_digest=h(decision))["status"]==status)
update=signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","new_work_item_state":"completed","status":"ledger_update_recorded","ledger_updated":True,"content_free":True},"ledger_update_receipt_digest");review=create_campaign_continuation_review(ledger_update_receipt=update,requested_action="select_followup",decision="approve",operator_decision_digest=h("ok"))
req(create_followup_work_selection(ledger=ledger,ledger_update_receipt=update,continuation_review=review,candidate_work_item_ids=["w1"],max_items=1)["status"]=="blocked")
tam=dict(update);tam["new_work_item_state"]="failed";req(create_campaign_continuation_review(ledger_update_receipt=tam,requested_action="hold_failure",decision="approve",operator_decision_digest=h("tam"))["status"]=="blocked")
cp=build_governed_campaign_work_continuation_checkpoint(source_root=ROOT);req(cp["ok"]);req(cp["passed"]==cp["total"]);req(not cp["authority_granted"])
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":"v1187.8"},sort_keys=True))
