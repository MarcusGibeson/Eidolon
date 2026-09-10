from __future__ import annotations

"""v1271.6-v1271.8 restart, lease, Windows and bounded-recovery hardening."""
import os,time
from pathlib import Path
from typing import Any
from self_development_alpha_foundations import _runtime_root, load_self_development_alpha_campaign
from long_running_work_sessions_foundations import *

CONTRACT_VERSION="v1271.8"


def claim_or_renew_work_session_lease(session_id: str, owner_id: str, *, runtime_root, now: float|None=None) -> dict[str,Any]:
    from long_running_work_sessions_foundations import _path,_seal,_write
    runtime=_runtime_root(runtime_root);row=load_long_running_work_session(session_id,runtime_root=runtime);clock=float(time.time() if now is None else now)
    if not validate_long_running_work_session(row).get("ok"): raise ValueError("valid_long_running_work_session_required")
    import re
    if not re.fullmatch(r"^[a-zA-Z0-9_.:-]{1,96}$",str(owner_id or "")): raise ValueError("invalid_lease_owner")
    current=str(row.get("lease_owner") or "");expires=float(row.get("lease_expires_at") or 0)
    if current and current!=owner_id and expires>clock:
        return {**public_long_running_work_session(row),"ok":False,"status":"long_running_work_session_lease_held","lease_acquired":False,"authority_granted":False}
    generation=int(row.get("lease_generation") or 0)+(1 if current!=owner_id else 0)
    updated=dict(row);updated.update({"lease_owner":owner_id,"lease_generation":generation,"heartbeat_at":clock,"lease_expires_at":clock+int(row.get("lease_seconds") or 120),"updated_at":clock})
    updated=_seal(updated);_write(_path(session_id,runtime),updated)
    return {**public_long_running_work_session(updated),"ok":True,"status":"long_running_work_session_lease_acquired" if current!=owner_id else "long_running_work_session_lease_renewed","lease_acquired":True,"authority_granted":False}


def release_work_session_lease(session_id: str, owner_id: str, *, runtime_root) -> dict[str,Any]:
    from long_running_work_sessions_foundations import _path,_seal,_write
    runtime=_runtime_root(runtime_root);row=load_long_running_work_session(session_id,runtime_root=runtime)
    if str(row.get("lease_owner") or "")!=str(owner_id): return {**public_long_running_work_session(row),"ok":False,"status":"lease_owner_mismatch"}
    updated=dict(row);updated.update({"lease_owner":"","heartbeat_at":0.0,"lease_expires_at":0.0,"updated_at":time.time()});updated=_seal(updated);_write(_path(session_id,runtime),updated);return {**public_long_running_work_session(updated),"ok":True,"status":"lease_released"}


def reconcile_long_running_work_session(session_id: str, *, runtime_root, now: float|None=None) -> dict[str,Any]:
    from long_running_work_sessions_foundations import _path,_seal,_write
    runtime=_runtime_root(runtime_root);row=load_long_running_work_session(session_id,runtime_root=runtime)
    if not validate_long_running_work_session(row).get("ok"): return {"ok":False,"status":"long_running_work_session_reconciliation_blocked_invalid_record",**AUTHORITY_FLAGS}
    alpha=load_self_development_alpha_campaign(str(row.get("campaign_id") or ""),runtime_root=runtime)
    if not alpha:return {"ok":False,"status":"long_running_work_session_reconciliation_blocked_missing_campaign",**AUTHORITY_FLAGS}
    phase,next_auth=map_alpha_phase(str(alpha.get("phase") or "blocked"));clock=float(time.time() if now is None else now)
    action=dict(row.get("action_receipts") or {});completed=list(row.get("completed_work_codes") or [])
    inferred=[]
    if alpha.get("phase") in {"repair_authorization_required","operator_review_required","review_decided"} and "candidate_stage" not in action:
        inferred.append("candidate_stage")
    if alpha.get("phase") in {"operator_review_required","review_decided"} and "verification_stage" not in action:
        inferred.append("verification_stage")
    for code in inferred:
        action[code]=str(alpha.get("record_digest") or "");
        if code not in completed:completed.append(code)
    expired=bool(row.get("lease_owner")) and float(row.get("lease_expires_at") or 0)<=clock
    state=str(row.get("state") or "active")
    if expired and state=="active":state="interrupted"
    updated=dict(row);updated.update({"state":state,"current_phase":phase,"next_required_authorization":next_auth,"campaign_record_digest":alpha.get("record_digest",""),"action_receipts":action,"completed_work_codes":completed[-64:],"updated_at":clock})
    if expired:updated.update({"lease_owner":"","heartbeat_at":0.0,"lease_expires_at":0.0,"interruption_reason":"expired_lease_reconciliation"})
    updated=_seal(updated);_write(_path(session_id,runtime),updated)
    return {**public_long_running_work_session(updated),"ok":True,"status":"long_running_work_session_reconciled","inferred_completed_actions":inferred,"expired_lease_recovered":expired,"duplicate_provider_tool_test_activity_created":False}


def inspect_long_running_work_sessions_health(*, source_root: str|Path|None=None) -> dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();required=["long_running_work_sessions_foundations.py","long_running_work_sessions.py","long_running_work_sessions_reliability.py","self_development_alpha.py","self_development_alpha_reliability.py","long_running_multi_day_session_continuity.py"]
    checks={name.replace('.py','_present'):(root/'conscious_agent'/name).is_file() for name in required}
    return {"ok":all(checks.values()),"status":"long_running_work_sessions_health_ready" if all(checks.values()) else "long_running_work_sessions_health_blocked","checks":checks,"native_windows_validation":"desktop_review_required","active_source_modified":False,**AUTHORITY_FLAGS}


def build_long_running_work_sessions_operator_handoff(*, source_root: str|Path|None=None) -> dict[str,Any]:
    health=inspect_long_running_work_sessions_health(source_root=source_root)
    return {"ok":health['ok'],"contract_version":CONTRACT_VERSION,"status":"long_running_work_sessions_operator_handoff_ready" if health['ok'] else "long_running_work_sessions_operator_handoff_blocked","capabilities":["durable_multi_hour_checkpoints","bounded_content_free_summaries","phase_timing_receipts","pause_interrupt_cancel_resume","attempted_vs_completed","resume_deduplication_via_v1270_lineage","bounded_heartbeat_lease","operator_phase_and_next_authorization","verification_harness_budget_split"],"known_limitations":["lease_is_advisory_not_v1273_exactly_once_concurrency","crash_between_external_side_effect_and_v1270_durable_commit_relies_on_existing_stage_idempotency","native_windows_process_lifetime_locking_shutdown_long_path_restart_requires_desktop_review"],"v1270_harness_finding":"monolithic_full_source_probe_exceeded_wall_clock_budget; split candidate/test-selection and verification completed promptly; v1271 budgets split rather than globally raising timeouts","native_windows_review":["process_lifetime_and_shutdown","filesystem_lock_expiry_and_recovery","long_paths","restart_between_campaign_phases","ntfs_atomic_replace_behavior"],"next_bounded_unit":"v1272 Restart and Crash Recovery","active_source_modified":False,**AUTHORITY_FLAGS}


__all__=["CONTRACT_VERSION","claim_or_renew_work_session_lease","release_work_session_lease","reconcile_long_running_work_session","inspect_long_running_work_sessions_health","build_long_running_work_sessions_operator_handoff"]
