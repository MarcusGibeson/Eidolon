from __future__ import annotations
"""v1286.3-v1286.5 integrates replanning with goal progress, uncertainty, and learned evidence."""
from typing import Any,Mapping,Sequence
from dynamic_replanning_foundations import *
from dynamic_replanning_foundations import _digest
CONTRACT_VERSION="v1286.5"
def replan_from_goal_progress(*,hierarchy:Mapping[str,Any],progress:Mapping[str,Any],event:Mapping[str,Any],failed_strategy_codes:Sequence[str]=())->dict[str,Any]:
 completed=[x.get("milestone_code") for x in progress.get("milestones") or [] if x.get("complete") is True];return build_replan_candidate(hierarchy=hierarchy,completed_milestone_codes=completed,event=event,failed_strategy_codes=failed_strategy_codes)
def replan_with_uncertainty(*,hierarchy:Mapping[str,Any],progress:Mapping[str,Any],uncertainty_claim:Mapping[str,Any],event_code:str="uncertainty_change")->dict[str,Any]:
 state=str(uncertainty_claim.get("epistemic_state") or "unverified");kind="failed_assumption" if state in {"suspended","unverified"} and int(uncertainty_claim.get("confidence") or 0)<=30 else "new_evidence";ev=build_replanning_event(event_kind=kind,event_code=event_code,evidence_codes=uncertainty_claim.get("evidence_codes") or []);r=replan_from_goal_progress(hierarchy=hierarchy,progress=progress,event=ev);r["uncertainty_state_seen"]=state;r["uncertainty_does_not_grant_execution_authority"]=True;r["replan_digest"]=_digest({k:v for k,v in r.items() if k!="replan_digest"});return r
def public_replan_summary(candidate:Mapping[str,Any])->dict[str,Any]:
 v=validate_replan_candidate(candidate);return {"ok":v.get("ok"),"event_kind":candidate.get("event_kind"),"completed_preserved":candidate.get("preserved_completed_milestone_count"),"pending_count":candidate.get("pending_milestone_count"),"action_codes":list(candidate.get("replan_action_codes") or []),"failed_strategy_count":len(candidate.get("failed_strategy_codes") or []),"original_intent_digest":candidate.get("original_intent_digest"),"raw_event_content_exposed":False,"execution_started":False,**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","replan_from_goal_progress","replan_with_uncertainty","public_replan_summary","build_replanning_event","validate_replan_candidate","AUTHORITY_FLAGS"]
