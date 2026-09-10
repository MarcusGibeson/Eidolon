from __future__ import annotations
"""Read-only v1188.8 campaign-loop reliability/recovery/learning checkpoint."""
import hashlib,json
from pathlib import Path
from typing import Any,Mapping
from checkpoint_registry import inspect_checkpoint_registry
from complete_campaign_development_loop_checkpoint import _fixtures
from complete_campaign_development_loop import integrate_complete_campaign_development_loop
from campaign_loop_execution_result_integration import *
from campaign_loop_reliability_recovery_learning import *
CONTRACT_VERSION="v1188.8"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _sign(row:Mapping[str,Any],field:str)->dict[str,Any]:
 x=dict(row);x[field]=hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return x
def _base():
 c,r,s,w,stages=_fixtures();loop=integrate_complete_campaign_development_loop(campaign_charter=c,campaign_review=r,session_snapshot=s,work_selection=w,stages=stages)
 review=create_loop_execution_review(loop=loop,decision="approve",operator_decision_digest=_h("approve"))
 ledger=_sign({"campaign_id":"campaign-v1188","work_item_ids":["work-1"],"content_free":True},"ledger_digest")
 budget=_sign({"campaign_id":"campaign-v1188","observed":{"elapsed_seconds":1,"disk_bytes":0,"token_budget":0},"limits":{"max_elapsed_seconds":100,"max_disk_bytes":1000,"max_token_budget":100},"content_free":True},"budget_receipt_digest")
 sr=create_loop_stage_result(loop=loop,execution_review=review,stage="testing",result_code="passed",evidence_digest=_h("passed"),observed_cost={"elapsed_seconds":2,"disk_bytes":0,"token_budget":1})
 receipt=integrate_campaign_loop_results(loop=loop,execution_review=review,stage_results=[sr],ledger=ledger,budget_receipt=budget)
 return loop,receipt
def build_campaign_loop_reliability_recovery_learning_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 del runtime_root
 checks=[];req=lambda v:checks.append(bool(v));loop,result=_base();same=_h("source");stage=_h("stage")
 a=create_loop_reliability_assessment(loop=loop,result_receipt=result,current_source_digest=same,current_stage_digest=stage,expected_source_digest=same,expected_stage_digest=stage,interruption_reason="none",rollback_expected_digest=_h("rollback"),rollback_observed_digest=_h("rollback"));req(a["status"]=="recovery_review_required");req(a["rollback_verified"]);req(not a["source_drift"]);req(not a["authority_granted"])
 for decision,status in (("approve","recovery_approved"),("reject","recovery_rejected"),("defer","recovery_deferred")):
  rv=create_loop_recovery_review(assessment=a,decision=decision,recovery_action="hold",operator_decision_digest=_h(decision));req(rv["status"]==status);req(not rv["recovery_executed"])
 approved=create_loop_recovery_review(assessment=a,decision="approve",recovery_action="resume_from_stage",operator_decision_digest=_h("go"))
 learn=apply_bounded_loop_learning(loop=loop,result_receipt=result,recovery_review=approved,learning_codes=["retain_verified_pattern"],operator_learning_digest=_h("learn"));req(learn["status"]=="learning_recorded_not_applied");req(learn["learning_recorded"]);req(not learn["learning_applied_to_policy"]);req(not learn["future_work_selection_modified"]);req(campaign_loop_reliability_public_summary(a)["content_free"])
 drift=create_loop_reliability_assessment(loop=loop,result_receipt=result,current_source_digest=_h("new"),current_stage_digest=stage,expected_source_digest=same,expected_stage_digest=stage,interruption_reason="process_restart");req(drift["source_drift"]);req(create_loop_recovery_review(assessment=drift,decision="approve",recovery_action="resume_from_stage",operator_decision_digest=_h("x"))["status"]=="blocked");req(create_loop_recovery_review(assessment=drift,decision="approve",recovery_action="resume_from_stage",operator_decision_digest=_h("x"),drift_acknowledged=True)["status"]=="recovery_approved")
 bad=dict(result);bad["result_code"]="failed";req(create_loop_reliability_assessment(loop=loop,result_receipt=bad,current_source_digest=same,current_stage_digest=stage,expected_source_digest=same,expected_stage_digest=stage,interruption_reason="none")["status"]=="blocked")
 req(create_loop_reliability_assessment(loop=loop,result_receipt=result,current_source_digest=same,current_stage_digest=stage,expected_source_digest=same,expected_stage_digest=stage,interruption_reason="none",privacy_findings=["secret"])["status"]=="blocked")
 req(create_loop_reliability_assessment(loop=loop,result_receipt=result,current_source_digest=same,current_stage_digest=stage,expected_source_digest=same,expected_stage_digest=stage,interruption_reason="none",rollback_expected_digest=_h("a"),rollback_observed_digest=_h("b"))["status"]=="blocked")
 req(apply_bounded_loop_learning(loop=loop,result_receipt=result,recovery_review=approved,learning_codes=["avoid_failed_pattern"],operator_learning_digest=_h("bad"))["status"]=="blocked")
 reg=inspect_checkpoint_registry(source_root=source_root);row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="campaign-loop-reliability-recovery-learning-checkpoint"),{});req(row.get("builder")=="build_campaign_loop_reliability_recovery_learning_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"campaign-loop-reliability-recovery-learning:v1188.8","passed":sum(checks),"total":len(checks),"read_only_source":True,"content_free":True,"production_source_modified":False,"sandbox_modified":False,"automatic_resume":False,"rollback_executed":False,"learning_applied_to_policy":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"desktop_verification_deferred_until_v1200":True}
