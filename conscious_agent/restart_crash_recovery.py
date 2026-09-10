from __future__ import annotations

"""v1272.3-v1272.5 integration with v1270/v1271 supervised development.

The write-ahead journal is persisted before entering provider/test stages.  A
crash after a lower stage durably completed but before the v1272 completion
receipt can therefore be reconciled without replaying that provider/test work.
Ambiguous external effects fail closed and require operator reconciliation.
"""

import time
from pathlib import Path
from typing import Any, Callable, Mapping

from self_development_alpha_foundations import _runtime_root, _stage_root, load_self_development_alpha_campaign
from self_development_alpha import (
    execute_self_development_alpha_candidate,
    execute_self_development_alpha_verification_and_review,
)
from isolated_self_modification_foundations import load_self_modification
from isolated_self_modification_reliability import recover_interrupted_self_modification
from iterative_self_repair_foundations import load_iterative_self_repair
from iterative_self_repair_reliability import recover_interrupted_iterative_self_repair
from long_running_work_sessions import (
    execute_long_running_candidate,
    execute_long_running_verification_and_review,
    interrupt_long_running_work_session,
    resume_long_running_work_session,
    long_running_operator_status,
)
from long_running_work_sessions_reliability import reconcile_long_running_work_session
from restart_crash_recovery_foundations import *

CONTRACT_VERSION = "v1272.5"


def _never_provider(_: Mapping[str, Any]) -> Mapping[str, Any]:
    raise RuntimeError("restart_reconciliation_must_not_contact_provider")


def _latest_entry(row: Mapping[str, Any], operation_code: str) -> dict[str, Any]:
    return next((dict(x) for x in reversed(list(row.get("operation_journal") or [])) if x.get("operation_code") == operation_code), {})


def _operation_outcome(result: Mapping[str, Any], operation_code: str) -> tuple[str, str]:
    status = str(result.get("status") or "")
    phase = str(result.get("phase") or result.get("campaign_phase") or "")
    if operation_code == "candidate_stage":
        if phase in {"repair_authorization_required", "operator_review_required", "review_decided"}:
            return "completed", "candidate_stage_durable"
        if status == "isolated_self_modification_exact_authorization_required":
            return "authorization_required", "candidate_authorization_required"
    if operation_code == "verification_stage":
        if phase in {"operator_review_required", "review_decided"}:
            return "completed", "verification_stage_durable"
        if status == "iterative_self_repair_exact_authorization_required":
            return "authorization_required", "verification_authorization_required"
    if "blocked" in status or phase == "blocked":
        return "blocked", "stage_blocked"
    return "blocked", "stage_not_durably_completed"


def execute_recoverable_candidate(
    recovery_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    authorization_phrase: str,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    post_stage_hook: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    if not validate_restart_crash_recovery(recovery).get("ok"):
        raise ValueError("valid_restart_crash_recovery_required")
    session_id = str(recovery.get("session_id") or "")
    alpha = load_self_development_alpha_campaign(str(recovery.get("campaign_id") or ""), runtime_root=runtime)
    target_id = str(alpha.get("candidate_operation_id") or "")
    entry = begin_recovery_operation(recovery_id, runtime_root=runtime, operation_code="candidate_stage", target_id=target_id)
    if entry.get("operation_status") == "already_completed":
        return {**alpha, "operation_status": "restored", "restart_duplicate_suppressed": True, "provider_contacted_this_invocation": False}
    if entry.get("operation_status") == "existing_incomplete":
        return {
            "ok": False, "status": "restart_crash_recovery_reconciliation_required", "recovery_id": recovery_id,
            "operation_code": "candidate_stage", "provider_contacted": False, "tests_executed": False,
            "duplicate_external_activity_suppressed": True, **AUTHORITY_FLAGS,
        }
    result = execute_long_running_candidate(
        session_id, source_root, runtime_root=runtime, authorization_phrase=authorization_phrase, provider=provider
    )
    # Test fixtures may simulate a process death exactly after the durable v1270
    # stage commit but before this v1272 completion receipt is written.
    if post_stage_hook is not None:
        post_stage_hook(result)
    state, outcome = _operation_outcome(result, "candidate_stage")
    lineage = load_self_development_alpha_campaign(str(recovery.get("campaign_id") or ""), runtime_root=runtime)
    finish_recovery_operation(
        recovery_id, runtime_root=runtime, operation_code="candidate_stage", generation=int(entry.get("generation") or 0),
        state=state, outcome_code=outcome, durable_lineage_digest=str(lineage.get("record_digest") or ""),
    )
    return {**result, "restart_recovery_id": recovery_id, "restart_operation_state": state}


def execute_recoverable_verification_and_review(
    recovery_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    repair_authorization_phrase: str,
    repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    budget: Mapping[str, Any] | None = None,
    post_stage_hook: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    if not validate_restart_crash_recovery(recovery).get("ok"):
        raise ValueError("valid_restart_crash_recovery_required")
    session_id = str(recovery.get("session_id") or "")
    alpha = load_self_development_alpha_campaign(str(recovery.get("campaign_id") or ""), runtime_root=runtime)
    target_id = str(alpha.get("repair_id") or "")
    entry = begin_recovery_operation(recovery_id, runtime_root=runtime, operation_code="verification_stage", target_id=target_id)
    if entry.get("operation_status") == "already_completed":
        return {**alpha, "operation_status": "restored", "restart_duplicate_suppressed": True, "tests_executed_this_invocation": False, "provider_contacted_this_invocation": False}
    if entry.get("operation_status") == "existing_incomplete":
        return {
            "ok": False, "status": "restart_crash_recovery_reconciliation_required", "recovery_id": recovery_id,
            "operation_code": "verification_stage", "provider_contacted": False, "tests_executed": False,
            "duplicate_external_activity_suppressed": True, **AUTHORITY_FLAGS,
        }
    result = execute_long_running_verification_and_review(
        session_id, source_root, runtime_root=runtime, repair_authorization_phrase=repair_authorization_phrase,
        repair_provider=repair_provider, budget=budget,
    )
    if post_stage_hook is not None:
        post_stage_hook(result)
    state, outcome = _operation_outcome(result, "verification_stage")
    lineage = load_self_development_alpha_campaign(str(recovery.get("campaign_id") or ""), runtime_root=runtime)
    finish_recovery_operation(
        recovery_id, runtime_root=runtime, operation_code="verification_stage", generation=int(entry.get("generation") or 0),
        state=state, outcome_code=outcome, durable_lineage_digest=str(lineage.get("record_digest") or ""),
    )
    return {**result, "restart_recovery_id": recovery_id, "restart_operation_state": state}


def _reconcile_candidate_incomplete(recovery: Mapping[str, Any], source_root: str | Path, runtime: Path) -> dict[str, Any]:
    campaign_id = str(recovery.get("campaign_id") or "")
    alpha = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    entry = _latest_entry(recovery, "candidate_stage")
    if not entry or entry.get("state") not in {"started", "ambiguous"}:
        return {"status": "candidate_recovery_not_needed", "completed": False, "ambiguous": False}
    if alpha.get("phase") in {"repair_authorization_required", "operator_review_required", "review_decided"}:
        finish_recovery_operation(
            str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="candidate_stage",
            generation=int(entry.get("generation") or 0), state="completed", outcome_code="candidate_stage_durable_after_restart",
            durable_lineage_digest=str(alpha.get("record_digest") or ""), reason_codes=["alpha_phase_advanced"],
        )
        return {"status": "candidate_recovered_from_alpha_lineage", "completed": True, "ambiguous": False}
    op_id = str(alpha.get("candidate_operation_id") or entry.get("target_id") or "")
    lower = load_self_modification(op_id, runtime_root=_stage_root(runtime, "v1265")) if op_id else {}
    if lower.get("phase") == "sealed":
        # Safe completion of the *derived alpha bookkeeping* only. The lower
        # provider action is already durably sealed and the forbidden provider
        # proves it cannot be replayed here.
        result = execute_self_development_alpha_candidate(
            campaign_id, source_root, runtime_root=runtime, authorization_phrase="", provider=_never_provider
        )
        refreshed = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
        if refreshed.get("phase") not in {"repair_authorization_required", "operator_review_required", "review_decided"}:
            raise RuntimeError("candidate_durable_lineage_finalize_failed")
        finish_recovery_operation(
            str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="candidate_stage",
            generation=int(entry.get("generation") or 0), state="completed", outcome_code="candidate_lower_stage_sealed_reconciled",
            durable_lineage_digest=str(refreshed.get("record_digest") or ""), reason_codes=["v1265_sealed"],
        )
        return {"status": "candidate_recovered_from_v1265_lineage", "completed": True, "ambiguous": False, "provider_replayed": False, "result_status": result.get("status")}
    if lower.get("phase") == "running":
        recovered = recover_interrupted_self_modification(op_id, source_root, runtime_root=_stage_root(runtime, "v1265"))
        finish_recovery_operation(
            str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="candidate_stage",
            generation=int(entry.get("generation") or 0), state="ambiguous", outcome_code="candidate_external_effect_ambiguous",
            durable_lineage_digest=str(recovered.get("record_digest") or ""), reason_codes=["v1265_running_at_restart"],
        )
        return {"status": "candidate_external_effect_ambiguous", "completed": False, "ambiguous": True, "provider_replayed": False}
    finish_recovery_operation(
        str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="candidate_stage",
        generation=int(entry.get("generation") or 0), state="blocked", outcome_code="candidate_stage_not_durable",
        durable_lineage_digest=str(lower.get("record_digest") or ""), reason_codes=[str(lower.get("phase") or "missing_lower_stage")],
    )
    return {"status": "candidate_recovery_blocked", "completed": False, "ambiguous": False, "provider_replayed": False}


def _reconcile_verification_incomplete(recovery: Mapping[str, Any], source_root: str | Path, runtime: Path) -> dict[str, Any]:
    campaign_id = str(recovery.get("campaign_id") or "")
    alpha = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    entry = _latest_entry(recovery, "verification_stage")
    if not entry or entry.get("state") not in {"started", "ambiguous"}:
        return {"status": "verification_recovery_not_needed", "completed": False, "ambiguous": False}
    if alpha.get("phase") in {"operator_review_required", "review_decided"}:
        finish_recovery_operation(
            str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="verification_stage",
            generation=int(entry.get("generation") or 0), state="completed", outcome_code="verification_stage_durable_after_restart",
            durable_lineage_digest=str(alpha.get("record_digest") or ""), reason_codes=["alpha_phase_advanced"],
        )
        return {"status": "verification_recovered_from_alpha_lineage", "completed": True, "ambiguous": False}
    repair_id = str(alpha.get("repair_id") or entry.get("target_id") or "")
    lower = load_iterative_self_repair(repair_id, runtime_root=_stage_root(runtime, "v1267")) if repair_id else {}
    if lower.get("phase") == "passed":
        result = execute_self_development_alpha_verification_and_review(
            campaign_id, source_root, runtime_root=runtime, repair_authorization_phrase="", repair_provider=_never_provider
        )
        refreshed = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
        if refreshed.get("phase") not in {"operator_review_required", "review_decided"}:
            raise RuntimeError("verification_durable_lineage_finalize_failed")
        finish_recovery_operation(
            str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="verification_stage",
            generation=int(entry.get("generation") or 0), state="completed", outcome_code="verification_lower_stage_passed_reconciled",
            durable_lineage_digest=str(refreshed.get("record_digest") or ""), reason_codes=["v1267_passed"],
        )
        return {"status": "verification_recovered_from_v1267_lineage", "completed": True, "ambiguous": False, "tests_replayed": False, "provider_replayed": False, "result_status": result.get("status")}
    if lower.get("phase") == "running":
        recovered = recover_interrupted_iterative_self_repair(repair_id, runtime_root=_stage_root(runtime, "v1267"))
        finish_recovery_operation(
            str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="verification_stage",
            generation=int(entry.get("generation") or 0), state="ambiguous", outcome_code="verification_external_effect_ambiguous",
            durable_lineage_digest=str(recovered.get("record_digest") or ""), reason_codes=["v1267_running_at_restart"],
        )
        return {"status": "verification_external_effect_ambiguous", "completed": False, "ambiguous": True, "tests_replayed": False, "provider_replayed": False}
    finish_recovery_operation(
        str(recovery.get("recovery_id")), runtime_root=runtime, operation_code="verification_stage",
        generation=int(entry.get("generation") or 0), state="blocked", outcome_code="verification_stage_not_durable",
        durable_lineage_digest=str(lower.get("record_digest") or ""), reason_codes=[str(lower.get("phase") or "missing_lower_stage")],
    )
    return {"status": "verification_recovery_blocked", "completed": False, "ambiguous": False, "tests_replayed": False, "provider_replayed": False}


def reconcile_restart_crash_recovery(
    recovery_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    now: float | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    if not validate_restart_crash_recovery(recovery).get("ok"):
        return {"ok": False, "status": "restart_crash_recovery_invalid", **AUTHORITY_FLAGS}
    long_recon = reconcile_long_running_work_session(str(recovery.get("session_id") or ""), runtime_root=runtime, now=now)
    candidate = _reconcile_candidate_incomplete(recovery, source_root, runtime)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    verification = _reconcile_verification_incomplete(recovery, source_root, runtime)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    ambiguous = bool(candidate.get("ambiguous") or verification.get("ambiguous"))
    blocked = any(x.get("state") in {"blocked", "ambiguous"} for x in recovery.get("operation_journal") or [])
    from restart_crash_recovery_foundations import _path, _save_with_receipt, _write
    updated = dict(recovery)
    updated["state"] = "blocked" if (ambiguous or blocked) else "reconciled"
    updated["campaign_record_digest"] = str(load_self_development_alpha_campaign(str(updated.get("campaign_id") or ""), runtime_root=runtime).get("record_digest") or "")
    updated = _save_with_receipt(
        updated, runtime_root=runtime, receipt_code="restart_reconciliation_complete",
        reason_codes=["ambiguous_external_effect" if ambiguous else "durable_lineage_reconciled"], state=str(updated["state"]), now=now,
    )
    _write(_path(recovery_id, runtime), updated)
    return {
        **public_restart_crash_recovery(updated),
        "ok": not ambiguous,
        "status": "restart_crash_recovery_reconciled" if not ambiguous else "restart_crash_recovery_operator_reconciliation_required",
        "candidate_recovery": candidate,
        "verification_recovery": verification,
        "long_session_reconciliation_status": long_recon.get("status"),
        "duplicate_provider_activity_created": False,
        "duplicate_test_activity_created": False,
        "duplicate_update_activity_created": False,
    }


def record_provider_outage(recovery_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    row = load_restart_crash_recovery(recovery_id, runtime_root=runtime_root)
    interrupt_long_running_work_session(str(row.get("session_id") or ""), runtime_root=runtime_root, reason="provider_outage")
    return note_recovery_interruption(recovery_id, runtime_root=runtime_root, interruption_code="provider_outage")


def record_provider_return(recovery_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return note_recovery_interruption(recovery_id, runtime_root=runtime_root, interruption_code="provider_return")


def resume_restart_crash_recovery(
    recovery_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    reconciled = reconcile_restart_crash_recovery(recovery_id, source_root, runtime_root=runtime)
    row = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    if reconciled.get("status") == "restart_crash_recovery_operator_reconciliation_required" or row.get("state") == "blocked":
        return {**reconciled, "resume_applied": False, "fresh_stage_authorization_still_required": True}
    resumed = resume_long_running_work_session(str(row.get("session_id") or ""), runtime_root=runtime)
    from restart_crash_recovery_foundations import _path, _save_with_receipt, _write
    updated = dict(row)
    updated["state"] = "healthy"
    updated = _save_with_receipt(updated, runtime_root=runtime, receipt_code="recovery_resume_recorded", reason_codes=["operator_resume"], state="healthy")
    _write(_path(recovery_id, runtime), updated)
    return {
        **public_restart_crash_recovery(updated),
        "ok": True,
        "status": "restart_crash_recovery_resumed",
        "resume_applied": True,
        "underlying_session_state": resumed.get("state"),
        "underlying_authorization_reused": False,
        "fresh_stage_authorization_still_required": True,
    }


def restart_crash_recovery_operator_status(recovery_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    row = load_restart_crash_recovery(recovery_id, runtime_root=runtime_root)
    public = public_restart_crash_recovery(row)
    session = long_running_operator_status(str(row.get("session_id") or ""), runtime_root=runtime_root)
    incomplete = [x for x in row.get("operation_journal") or [] if x.get("state") in {"started", "ambiguous", "blocked"}]
    public.update({
        "status": "restart_crash_recovery_operator_status",
        "current_phase": session.get("current_phase"),
        "next_required_authorization": session.get("next_required_authorization"),
        "long_session_state": session.get("state"),
        "recovery_required": row.get("state") in {"interrupted", "recovery_required", "blocked"} or bool(incomplete),
        "operator_reconciliation_required": any(x.get("state") == "ambiguous" for x in incomplete),
        "incomplete_operation_count": len(incomplete),
        "work_completed": session.get("work_completed", []),
        "work_attempted_not_completed": session.get("work_attempted_not_completed", []),
        "fresh_stage_authorization_still_required": True,
        "automatic_resume": False,
        "automatic_retry": False,
    })
    return public


__all__ = [
    "CONTRACT_VERSION", "execute_recoverable_candidate", "execute_recoverable_verification_and_review",
    "reconcile_restart_crash_recovery", "record_provider_outage", "record_provider_return",
    "resume_restart_crash_recovery", "restart_crash_recovery_operator_status",
]
