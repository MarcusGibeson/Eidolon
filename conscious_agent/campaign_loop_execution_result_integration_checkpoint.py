from __future__ import annotations
"""Read-only v1188.5 governed campaign loop execution/result checkpoint."""
import hashlib,json
from pathlib import Path
from typing import Any,Mapping
from checkpoint_registry import inspect_checkpoint_registry
from complete_campaign_development_loop_checkpoint import _fixtures
from complete_campaign_development_loop import integrate_complete_campaign_development_loop
from campaign_loop_execution_result_integration import *
CONTRACT_VERSION="v1188.5"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _sign(row:Mapping[str,Any],field:str)->dict[str,Any]:
 x=dict(row);x[field]=hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return x
def build_campaign_loop_execution_result_integration_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda v:checks.append(bool(v));c,r,s,w,stages=_fixtures();loop=integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=stages)
 review=create_loop_execution_review(loop=loop,decision="approve",operator_decision_digest=_h("approve"));req(review["status"]=="execution_approved")
 ledger=_sign({"campaign_id":"campaign-v1188","work_item_ids":["work-1"],"content_free":True},"ledger_digest")
 budget=_sign({"campaign_id":"campaign-v1188","observed":{"elapsed_seconds":1,"disk_bytes":0,"token_budget":0},"limits":{"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":100},"content_free":True},"budget_receipt_digest")
 for result,state in (("passed","completed"),("failed","failed"),("blocked","blocked")):
  sr=create_loop_stage_result(loop=loop,execution_review=review,stage="testing",result_code=result,evidence_digest=_h(result),observed_cost={"elapsed_seconds":2,"disk_bytes":0,"token_budget":1});req(sr["status"]=="stage_result_recorded")
  receipt=integrate_campaign_loop_results(loop=loop,execution_review=review,stage_results=[sr],ledger=ledger,budget_receipt=budget);req(receipt["status"]=="loop_result_integrated");req(receipt["new_work_item_state"]==state);req(receipt["ledger_updated"] and receipt["budget_consumed"]);req(not receipt["automatic_continuation"]);req(not receipt["authority_granted"]);req(campaign_loop_result_public_summary(receipt)["content_free"])
 req(create_loop_execution_review(loop=loop,decision="reject",operator_decision_digest=_h("r"))["status"]=="execution_rejected")
 req(create_loop_execution_review(loop=loop,decision="defer",operator_decision_digest=_h("d"))["status"]=="execution_deferred")
 bad=dict(loop);bad["stage_count"]=9;req(create_loop_execution_review(loop=bad,decision="approve",operator_decision_digest=_h("x"))["status"]=="blocked")
 req(create_loop_stage_result(loop=loop,execution_review=review,stage="shell",result_code="passed",evidence_digest=_h("x"),observed_cost={})["status"]=="blocked")
 sr=create_loop_stage_result(loop=loop,execution_review=review,stage="testing",result_code="passed",evidence_digest=_h("p"),observed_cost={"elapsed_seconds":200});req(integrate_campaign_loop_results(loop=loop,execution_review=review,stage_results=[sr],ledger=ledger,budget_receipt=budget)["status"]=="blocked")
 reg=inspect_checkpoint_registry(source_root=source_root);row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="campaign-loop-execution-result-integration-checkpoint"),{});req(row.get("builder")=="build_campaign_loop_execution_result_integration_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"campaign-loop-execution-result-integration:v1188.5","passed":sum(checks),"total":len(checks),"read_only_source":True,"content_free":True,"production_source_modified":False,"sandbox_modified":False,"automatic_continuation":False,"learning_applied":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"desktop_verification_deferred_until_v1200":True}
