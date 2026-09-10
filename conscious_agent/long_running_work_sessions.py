from __future__ import annotations

"""v1271.3-v1271.5 integration with the real v1270 self-development campaign."""
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from self_development_alpha import execute_self_development_alpha_candidate, execute_self_development_alpha_verification_and_review
from self_development_alpha_foundations import _runtime_root, load_self_development_alpha_campaign
from self_development_alpha_reliability import cancel_self_development_alpha_campaign
from long_running_work_sessions_foundations import *

CONTRACT_VERSION="v1271.5"


def _save_control(session_id: str, runtime_root, *, state: str, field: str, reason: str, now: float|None=None) -> dict[str,Any]:
    from long_running_work_sessions_foundations import _path,_seal,_write
    runtime=_runtime_root(runtime_root);row=load_long_running_work_session(session_id,runtime_root=runtime)
    if not validate_long_running_work_session(row).get("ok"):raise ValueError("valid_long_running_work_session_required")
    clock=float(time.time() if now is None else now);updated=dict(row);updated.update({"state":state,field:str(reason or "operator_control")[:96],"updated_at":clock,"lease_owner":"","heartbeat_at":0.0,"lease_expires_at":0.0})
    updated=_seal(updated);_write(_path(session_id,runtime),updated);return {**updated,"operation_status":"control_recorded"}


def pause_long_running_work_session(session_id: str, *, runtime_root, reason: str="operator_pause") -> dict[str,Any]:
    return _save_control(session_id,runtime_root,state="paused",field="pause_reason",reason=reason)


def interrupt_long_running_work_session(session_id: str, *, runtime_root, reason: str="process_interruption") -> dict[str,Any]:
    return _save_control(session_id,runtime_root,state="interrupted",field="interruption_reason",reason=reason)


def resume_long_running_work_session(session_id: str, *, runtime_root) -> dict[str,Any]:
    from long_running_work_sessions_foundations import _path,_seal,_write
    runtime=_runtime_root(runtime_root);row=load_long_running_work_session(session_id,runtime_root=runtime)
    if row.get("state") not in {"paused","interrupted"}: return {**row,"operation_status":"unchanged"}
    alpha=load_self_development_alpha_campaign(str(row.get("campaign_id") or ""),runtime_root=runtime);phase,next_auth=map_alpha_phase(str(alpha.get("phase") or "blocked"))
    updated=dict(row);updated.update({"state":"active","current_phase":phase,"next_required_authorization":next_auth,"updated_at":time.time(),"lease_owner":"","heartbeat_at":0.0,"lease_expires_at":0.0})
    updated=_seal(updated);_write(_path(session_id,runtime),updated);return {**updated,"operation_status":"resumed","underlying_authorization_reused":False}


def cancel_long_running_work_session(session_id: str, *, runtime_root, reason: str="operator_cancel") -> dict[str,Any]:
    runtime=_runtime_root(runtime_root);row=load_long_running_work_session(session_id,runtime_root=runtime)
    if not row:return {"ok":False,"status":"long_running_work_session_missing",**AUTHORITY_FLAGS}
    result=cancel_self_development_alpha_campaign(str(row.get("campaign_id") or ""),runtime_root=runtime)
    if not result.get("ok", True) and result.get("status")=="verified_candidate_requires_review_or_cleanup":
        return {**row,"ok":False,"status":"long_running_work_session_cancel_blocked_verified_candidate_requires_review","state":row.get("state"),**AUTHORITY_FLAGS}
    return _save_control(session_id,runtime,state="cancelled",field="cancel_reason",reason=reason)


def _guard(row: Mapping[str,Any]) -> None:
    if row.get("state") in {"paused","interrupted","cancelled","blocked"}: raise RuntimeError(f"long_running_work_session_not_executable:{row.get('state')}")


def execute_long_running_candidate(session_id: str, source_root: str|Path, *, runtime_root, authorization_phrase: str, provider: Callable[[Mapping[str,Any]],Mapping[str,Any]]) -> dict[str,Any]:
    runtime=_runtime_root(runtime_root);session=load_long_running_work_session(session_id,runtime_root=runtime);_guard(session)
    alpha=load_self_development_alpha_campaign(str(session.get("campaign_id") or ""),runtime_root=runtime)
    if alpha.get("phase") in {"repair_authorization_required","operator_review_required","review_decided"}:
        phase,next_auth=map_alpha_phase(str(alpha.get("phase")));record_progress_receipt(session_id,runtime_root=runtime,phase=phase,work_code="candidate_stage",outcome="completed",action_key="candidate_stage");return {**alpha,"operation_status":"restored","long_session_duplicate_suppressed":True}
    start=time.monotonic();result=execute_self_development_alpha_candidate(str(session.get("campaign_id") or ""),source_root,runtime_root=runtime,authorization_phrase=authorization_phrase,provider=provider);elapsed=time.monotonic()-start
    completed=result.get("phase") in {"repair_authorization_required","operator_review_required","review_decided"};phase,next_auth=map_alpha_phase(str(result.get("phase") or result.get("campaign_phase") or "prepared"))
    record_progress_receipt(session_id,runtime_root=runtime,phase=phase,work_code="candidate_stage",outcome="completed" if completed else "attempted",elapsed_seconds=elapsed,action_key="candidate_stage" if completed else "",detail_codes=[str(result.get("status") or "candidate_result")[:95]])
    return {**result,"long_session_id":session_id,"long_session_next_required_authorization":next_auth}


def execute_long_running_verification_and_review(session_id: str, source_root: str|Path, *, runtime_root, repair_authorization_phrase: str, repair_provider: Callable[[Mapping[str,Any]],Mapping[str,Any]], budget: Mapping[str,Any]|None=None) -> dict[str,Any]:
    runtime=_runtime_root(runtime_root);session=load_long_running_work_session(session_id,runtime_root=runtime);_guard(session)
    alpha=load_self_development_alpha_campaign(str(session.get("campaign_id") or ""),runtime_root=runtime)
    if alpha.get("phase") in {"operator_review_required","review_decided"}:
        phase,next_auth=map_alpha_phase(str(alpha.get("phase")));record_progress_receipt(session_id,runtime_root=runtime,phase=phase,work_code="verification_stage",outcome="completed",action_key="verification_stage");return {**alpha,"operation_status":"restored","long_session_duplicate_suppressed":True}
    if budget is not None and budget.get("ok") is not True: raise ValueError("valid_verification_budget_required")
    # A predicted over-budget monolithic harness is not silently granted a longer timeout.
    if budget and budget.get("monolithic_run_within_budget") is False:
        record_progress_receipt(session_id,runtime_root=runtime,phase="verification_and_repair",work_code="verification_stage",outcome="blocked",detail_codes=["harness_budget_split_required"])
        return {"ok":False,"status":"verification_harness_budget_split_required","session_id":session_id,"budget":dict(budget),"tests_executed":False,"provider_contacted":False,**AUTHORITY_FLAGS}
    start=time.monotonic();result=execute_self_development_alpha_verification_and_review(str(session.get("campaign_id") or ""),source_root,runtime_root=runtime,repair_authorization_phrase=repair_authorization_phrase,repair_provider=repair_provider);elapsed=time.monotonic()-start
    completed=result.get("phase") in {"operator_review_required","review_decided"};phase,next_auth=map_alpha_phase(str(result.get("phase") or result.get("campaign_phase") or "blocked"))
    record_progress_receipt(session_id,runtime_root=runtime,phase=phase,work_code="verification_stage",outcome="completed" if completed else "attempted",elapsed_seconds=elapsed,action_key="verification_stage" if completed else "",detail_codes=[str(result.get("status") or "verification_result")[:95]])
    return {**result,"long_session_id":session_id,"long_session_next_required_authorization":next_auth}


def long_running_operator_status(session_id: str, *, runtime_root) -> dict[str,Any]:
    row=load_long_running_work_session(session_id,runtime_root=runtime_root);alpha=load_self_development_alpha_campaign(str(row.get("campaign_id") or ""),runtime_root=runtime_root);phase,next_auth=map_alpha_phase(str(alpha.get("phase") or row.get("current_phase") or "blocked"))
    public=public_long_running_work_session(row);public.update({"current_phase":phase,"next_required_authorization":next_auth,"campaign_phase":alpha.get("phase"),"campaign_status":alpha.get("status"),"work_completed":list(row.get("completed_work_codes") or []),"work_attempted_not_completed":[x for x in row.get("attempted_work_codes") or [] if x not in set(row.get("completed_work_codes") or [])]})
    return public


__all__=["CONTRACT_VERSION","pause_long_running_work_session","interrupt_long_running_work_session","resume_long_running_work_session","cancel_long_running_work_session","execute_long_running_candidate","execute_long_running_verification_and_review","long_running_operator_status"]
