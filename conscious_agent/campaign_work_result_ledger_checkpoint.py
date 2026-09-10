from __future__ import annotations
"""Read-only v1187.5 governed campaign work result and ledger checkpoint."""
import hashlib,json
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from campaign_work_result_ledger import *
CONTRACT_VERSION="v1187.5"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _signed(row:dict,field:str)->dict:
 out=dict(row);out.pop(field,None);out[field]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return out
def build_campaign_work_result_ledger_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda v:checks.append(bool(v))
 ledger=_signed({"campaign_id":"c1","work_item_ids":["w1"],"status":"approved_bounded_ledger","content_free":True},"ledger_digest")
 budget=_signed({"campaign_id":"c1","observed":{"work_items":0,"elapsed_seconds":1,"disk_bytes":0,"token_budget":0},"limits":{"max_work_items":3,"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":100},"status":"within_budget","content_free":True},"budget_receipt_digest")
 for result,state in (("passed","completed"),("failed","failed")):
  execution=_signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","status":"executed","result_code":result,"work_executed":True,"content_free":True},"work_execution_receipt_digest")
  review=create_work_result_review(execution_receipt=execution,decision="accept",operator_decision_digest=_h(result));req(review["status"]=="accepted_for_ledger")
  receipt=create_ledger_update_receipt(ledger=ledger,budget_receipt=budget,execution_receipt=execution,result_review=review,observed_cost={"work_items":1,"elapsed_seconds":2,"disk_bytes":0,"token_budget":1});req(receipt["status"]=="ledger_update_recorded");req(receipt["new_work_item_state"]==state);req(receipt["ledger_updated"] and receipt["budget_consumed"]);req(not receipt["authority_granted"])
  req(work_result_ledger_public_summary(review,receipt)["content_free"])
 execution=_signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","status":"executed","result_code":"passed","work_executed":True,"content_free":True},"work_execution_receipt_digest")
 req(create_work_result_review(execution_receipt=execution,decision="reject",operator_decision_digest=_h("r"))["status"]=="rejected_result")
 req(create_work_result_review(execution_receipt=execution,decision="defer",operator_decision_digest=_h("d"))["status"]=="deferred_result")
 bad=create_work_result_review(execution_receipt=execution,decision="accept",operator_decision_digest=_h("a"));tam=dict(execution);tam["result_code"]="failed";req(create_work_result_review(execution_receipt=tam,decision="accept",operator_decision_digest=_h("x"))["status"]=="blocked")
 req(create_ledger_update_receipt(ledger=ledger,budget_receipt=budget,execution_receipt=execution,result_review=bad,observed_cost={"work_items":2})["status"]=="blocked")
 reg=inspect_checkpoint_registry(source_root=source_root);row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="campaign-work-result-ledger-checkpoint"),{});req(row.get("builder")=="build_campaign_work_result_ledger_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"campaign-work-result-ledger:v1187.5","passed":sum(checks),"total":len(checks),"read_only_source":True,"content_free":True,"isolated_fixture_ledger_updates":True,"production_source_modified":False,"sandbox_modified":False,"work_retried":False,"automatic_reselection":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
