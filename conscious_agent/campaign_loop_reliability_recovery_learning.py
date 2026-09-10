from __future__ import annotations
"""v1188.6-v1188.8 campaign-loop reliability, recovery, and learning application."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1188.8";SCHEMA_VERSION="1";MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
INTERRUPTIONS=frozenset({"none","operator_pause","process_restart","provider_outage","stage_failure"})
RECOVERY_ACTIONS=frozenset({"hold","resume_from_stage","restart_stage","rollback_then_hold","abandon"})
LEARNING_CODES=frozenset({"retain_verified_pattern","strengthen_precondition","avoid_failed_pattern","require_more_evidence","no_generalization"})
TERMINAL=frozenset({"completed","failed","blocked"})
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_loop_reliability_assessment(*,loop:Mapping[str,Any],result_receipt:Mapping[str,Any],current_source_digest:str,current_stage_digest:str,expected_source_digest:str,expected_stage_digest:str,interruption_reason:str,rollback_expected_digest:str="",rollback_observed_digest:str="",privacy_findings:Sequence[str]=())->dict[str,Any]:
 l=dict(loop);r=dict(result_receipt);ld,lok=_verify(l,"loop_digest");rd,rok=_verify(r,"loop_result_receipt_digest");errors=[]
 if not lok:errors.append("tampered_loop")
 if not rok:errors.append("tampered_result_receipt")
 if r.get("loop_digest")!=ld:errors.append("result_loop_mismatch")
 if r.get("status")!="loop_result_integrated" or r.get("new_work_item_state") not in TERMINAL:errors.append("result_not_integrated")
 vals={"current_source_digest":current_source_digest,"current_stage_digest":current_stage_digest,"expected_source_digest":expected_source_digest,"expected_stage_digest":expected_stage_digest}
 for k,v in vals.items():
  vals[k]=str(v or "").lower()
  if not DIGEST_RE.fullmatch(vals[k]):errors.append(f"invalid_{k}")
 if interruption_reason not in INTERRUPTIONS:errors.append("unsupported_interruption_reason")
 rexp=str(rollback_expected_digest or "").lower();robs=str(rollback_observed_digest or "").lower()
 if bool(rexp)!=bool(robs):errors.append("incomplete_rollback_evidence")
 if rexp and (not DIGEST_RE.fullmatch(rexp) or not DIGEST_RE.fullmatch(robs)):errors.append("invalid_rollback_digest")
 findings=[str(x) for x in privacy_findings]
 if findings:errors.append("privacy_findings_present")
 source_drift=vals["current_source_digest"]!=vals["expected_source_digest"]
 stage_drift=vals["current_stage_digest"]!=vals["expected_stage_digest"]
 rollback_verified=bool(rexp and rexp==robs)
 if rexp and not rollback_verified:errors.append("rollback_mismatch")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":l.get("campaign_id",""),"work_item_id":l.get("work_item_id",""),"loop_digest":ld,"loop_result_receipt_digest":rd,**vals,"source_drift":source_drift,"stage_drift":stage_drift,"interruption_reason":interruption_reason,"rollback_expected_digest":rexp,"rollback_observed_digest":robs,"rollback_verified":rollback_verified,"privacy_finding_count":len(findings),"status":"recovery_review_required" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"automatic_resume":False,"rollback_executed":False,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1)
 row["loop_reliability_digest"]=_digest(row);return row

def create_loop_recovery_review(*,assessment:Mapping[str,Any],decision:str,recovery_action:str,operator_decision_digest:str,drift_acknowledged:bool=False)->dict[str,Any]:
 a=dict(assessment);ad,aok=_verify(a,"loop_reliability_digest");errors=[]
 if not aok:errors.append("tampered_assessment")
 if a.get("status")!="recovery_review_required":errors.append("assessment_not_reviewable")
 if decision not in {"approve","reject","defer"}:errors.append("unsupported_decision")
 if recovery_action not in RECOVERY_ACTIONS:errors.append("unsupported_recovery_action")
 od=str(operator_decision_digest or "").lower()
 if not DIGEST_RE.fullmatch(od):errors.append("invalid_operator_decision_digest")
 if decision=="approve" and (a.get("source_drift") or a.get("stage_drift")) and not drift_acknowledged:errors.append("drift_not_acknowledged")
 status={"approve":"recovery_approved","reject":"recovery_rejected","defer":"recovery_deferred"}.get(decision,"blocked") if not errors else "blocked"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":a.get("campaign_id",""),"work_item_id":a.get("work_item_id",""),"loop_reliability_digest":ad,"decision":decision,"recovery_action":recovery_action,"operator_decision_digest":od,"drift_acknowledged":bool(drift_acknowledged),"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"recovery_executed":False,"automatic_resume":False,"authority_granted":False}
 row["loop_recovery_review_digest"]=_digest(row);return row

def apply_bounded_loop_learning(*,loop:Mapping[str,Any],result_receipt:Mapping[str,Any],recovery_review:Mapping[str,Any],learning_codes:Sequence[str],operator_learning_digest:str)->dict[str,Any]:
 l=dict(loop);r=dict(result_receipt);v=dict(recovery_review);ld,lok=_verify(l,"loop_digest");rd,rok=_verify(r,"loop_result_receipt_digest");vd,vok=_verify(v,"loop_recovery_review_digest");errors=[]
 if not lok:errors.append("tampered_loop")
 if not rok:errors.append("tampered_result_receipt")
 if not vok:errors.append("tampered_recovery_review")
 if r.get("loop_digest")!=ld:errors.append("result_loop_mismatch")
 if v.get("status") not in {"recovery_approved","recovery_rejected","recovery_deferred"}:errors.append("invalid_recovery_review")
 codes=[str(x) for x in learning_codes]
 if not codes:errors.append("missing_learning_codes")
 if len(codes)!=len(set(codes)):errors.append("duplicate_learning_codes")
 if any(x not in LEARNING_CODES for x in codes):errors.append("unsupported_learning_code")
 if len(codes)>3:errors.append("too_many_learning_codes")
 od=str(operator_learning_digest or "").lower()
 if not DIGEST_RE.fullmatch(od):errors.append("invalid_operator_learning_digest")
 outcome=str(r.get("result_code") or "")
 if outcome=="passed" and "avoid_failed_pattern" in codes:errors.append("learning_outcome_mismatch")
 if outcome in {"failed","blocked"} and "retain_verified_pattern" in codes:errors.append("learning_outcome_mismatch")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":l.get("campaign_id",""),"work_item_id":l.get("work_item_id",""),"loop_digest":ld,"loop_result_receipt_digest":rd,"loop_recovery_review_digest":vd,"result_code":outcome,"learning_codes":codes,"operator_learning_digest":od,"status":"learning_recorded_not_applied" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"learning_recorded":not errors,"learning_applied_to_policy":False,"future_work_selection_modified":False,"automatic_continuation":False,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1,learning_recorded=False)
 row["loop_learning_receipt_digest"]=_digest(row);return row

def campaign_loop_reliability_public_summary(receipt:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":receipt.get("campaign_id",""),"work_item_id":receipt.get("work_item_id",""),"status":receipt.get("status",""),"source_drift":bool(receipt.get("source_drift",False)),"stage_drift":bool(receipt.get("stage_drift",False)),"error_count":int(receipt.get("error_count",0) or 0),"content_free":True,"automatic_resume":False,"learning_applied_to_policy":False,"authority_granted":False}
