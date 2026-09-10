from __future__ import annotations
"""v1328 deterministic stop/escalation decisions for bounded planning."""
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION="v1328.8"
STOP_REASONS=("repeated_failure","material_uncertainty","boundary_conflict","resource_exhaustion","unsafe_side_effect","protected_surface_block")


def _path(decision_id:str,runtime_root=None)->Path:
    return evidence_root("planning_stop_escalation",runtime_root)/"records"/f"{decision_id}.json"


def evaluate_stop_escalation(*,failure_count:int=0,uncertainty:Mapping[str,Any]|None=None,boundary_conflict:bool=False,resource_exhausted:bool=False,unsafe_side_effect:bool=False,risk_sensitive_planning:Mapping[str,Any]|None=None,runtime_root=None)->dict[str,Any]:
    reasons=[];evidence=[];unc=dict(uncertainty or {});risk=dict(risk_sensitive_planning or {})
    if int(failure_count)>=3: reasons.append("repeated_failure")
    confidence=unc.get("confidence")
    epistemic=str(unc.get("epistemic_state") or unc.get("state") or "")
    contradictory=bool(unc.get("contradictory") or epistemic in {"contradictory","suspended","unverified"})
    if contradictory or (confidence is not None and float(confidence)<40): reasons.append("material_uncertainty")
    if boundary_conflict: reasons.append("boundary_conflict")
    if resource_exhausted: reasons.append("resource_exhaustion")
    if unsafe_side_effect: reasons.append("unsafe_side_effect")
    if risk.get("protected_surface") or (risk and not risk.get("planning_progress_allowed",True)): reasons.append("protected_surface_block")
    for item in (unc.get("evidence_digests") or []):
        if str(item): evidence.append(str(item))
    for item in (risk.get("assessment_id"),risk.get("source_manifest_digest")):
        if item:evidence.append(str(item))
    reasons=list(dict.fromkeys(reasons));stop=bool(reasons)
    choices=[]
    mapping={
      "repeated_failure":["diagnose_root_cause","change_candidate_approach","defer_work"],
      "material_uncertainty":["validate_uncertain_evidence","request_consequential_clarification","defer_work"],
      "boundary_conflict":["narrow_scope_to_active_boundary","request_separate_authority","abandon_out_of_scope_work"],
      "resource_exhaustion":["reduce_scope_or_cost","request_budget_revision","defer_work"],
      "unsafe_side_effect":["inspect_owned_side_effect","rollback_owned_candidate_if_authorized","abandon_unsafe_route"],
      "protected_surface_block":["route_to_protected_core_review","request_separate_protected_action_approval","narrow_scope_away_from_protected_surface"],
    }
    for reason in reasons:
        for choice in mapping[reason]:
            if choice not in choices:choices.append(choice)
    decision_id="stop_"+digest({"failure_count":int(failure_count),"reasons":reasons,"evidence":sorted(set(evidence)),"risk":risk.get("assessment_id")})[:24]
    row=seal({"contract_version":CONTRACT_VERSION,"decision_id":decision_id,"stop_required":stop,"continue_planning_allowed":not stop,"reason_codes":reasons,"failure_count":int(failure_count),
              "uncertainty_confidence":confidence,"uncertainty_state":epistemic,"boundary_conflict":bool(boundary_conflict),"resource_exhausted":bool(resource_exhausted),"unsafe_side_effect":bool(unsafe_side_effect),
              "risk_assessment_id":risk.get("assessment_id"),"evidence_digests":sorted(set(evidence))[:32],"actionable_choice_codes":choices,"automatic_retry_allowed":False,"automatic_resume_allowed":False,
              "choice_execution_authorized":False,"action_executed":False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(decision_id,runtime_root),row)
    return {"ok":True,"status":"planning_stopped_for_escalation" if stop else "planning_may_continue","stop_escalation":public_stop_escalation(row),"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def public_stop_escalation(row:Mapping[str,Any])->dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"decision_id":row.get("decision_id"),"stop_required":bool(row.get("stop_required")),"continue_planning_allowed":bool(row.get("continue_planning_allowed")),"reason_codes":list(row.get("reason_codes") or []),
            "failure_count":int(row.get("failure_count") or 0),"uncertainty_confidence":row.get("uncertainty_confidence"),"uncertainty_state":row.get("uncertainty_state"),"boundary_conflict":bool(row.get("boundary_conflict")),
            "resource_exhausted":bool(row.get("resource_exhausted")),"unsafe_side_effect":bool(row.get("unsafe_side_effect")),"risk_assessment_id":row.get("risk_assessment_id"),"actionable_choice_codes":list(row.get("actionable_choice_codes") or []),
            "automatic_retry_allowed":False,"automatic_resume_allowed":False,"choice_execution_authorized":False,"read_only":True,"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def load_stop_escalation(decision_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(decision_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_stop_escalation(row)


def process_stop_escalation_control(text:str,*,failure_count=0,uncertainty=None,boundary_conflict=False,resource_exhausted=False,unsafe_side_effect=False,risk_sensitive_planning=None,runtime_root=None,**_)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show stop escalation','inspect stop escalation','should planning stop'}:return {'active':False}
    return {'active':True,**evaluate_stop_escalation(failure_count=failure_count,uncertainty=uncertainty,boundary_conflict=boundary_conflict,resource_exhausted=resource_exhausted,unsafe_side_effect=unsafe_side_effect,risk_sensitive_planning=risk_sensitive_planning,runtime_root=runtime_root)}


__all__=['CONTRACT_VERSION','STOP_REASONS','evaluate_stop_escalation','public_stop_escalation','load_stop_escalation','process_stop_escalation_control']
