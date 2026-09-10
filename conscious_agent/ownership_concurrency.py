from __future__ import annotations

"""v1273.3-v1273.5 ownership integration with the real v1272 pipeline."""

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from self_development_alpha_foundations import _runtime_root, load_self_development_alpha_campaign
from restart_crash_recovery_foundations import load_restart_crash_recovery
from restart_crash_recovery import (
    execute_recoverable_candidate,
    execute_recoverable_verification_and_review,
    reconcile_restart_crash_recovery,
)
from ownership_concurrency_foundations import *

CONTRACT_VERSION = "v1273.5"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _target_for_operation(ownership: Mapping[str, Any], operation_code: str, runtime: Path) -> str:
    alpha = load_self_development_alpha_campaign(str(ownership.get("campaign_id") or ""), runtime_root=runtime)
    return str(alpha.get("candidate_operation_id") or "") if operation_code == "candidate_stage" else str(alpha.get("repair_id") or "")


def _latest_recovery_entry(recovery: Mapping[str, Any], operation_code: str, target_id: str) -> dict[str, Any]:
    return next((dict(x) for x in reversed(list(recovery.get("operation_journal") or [])) if x.get("operation_code") == operation_code and str(x.get("target_id") or "") == str(target_id or "")), {})


def reconcile_transferred_ownership(
    ownership_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    operation_code: str,
    target_id: str,
    owner_id: str,
    epoch: int,
    fence_token: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Reconcile v1272 before activating an expired-owner successor claim."""
    runtime = _runtime_root(runtime_root)
    ownership = load_ownership_concurrency(ownership_id, runtime_root=runtime)
    if not validate_ownership_concurrency(ownership).get("ok"):
        return {"ok": False, "status": "ownership_concurrency_invalid", "execution_allowed": False, **AUTHORITY_FLAGS}
    recovery_id = str(ownership.get("recovery_id") or "")
    reconciled = reconcile_restart_crash_recovery(recovery_id, source_root, runtime_root=runtime, now=now)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    entry = _latest_recovery_entry(recovery, operation_code, target_id)
    if entry.get("state") == "completed":
        completed = complete_operation_ownership(
            ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
            owner_id=owner_id, epoch=epoch, fence_token=fence_token,
            completion_code="durable_lineage_reconciled", durable_lineage_digest=str(entry.get("durable_lineage_digest") or ""),
            result_digest=str(entry.get("entry_digest") or ""), now=now, allow_expired_reconciled=True,
        )
        return {
            **completed, "ok": True, "status": "ownership_completed_from_v1272_lineage", "execution_allowed": False,
            "duplicate_provider_activity_created": False, "duplicate_test_activity_created": False,
            "late_previous_owner_result_may_commit": False,
        }
    if entry.get("state") in {"started", "ambiguous", "blocked"} or reconciled.get("status") == "restart_crash_recovery_operator_reconciliation_required":
        blocked = block_operation_ownership(
            ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
            owner_id=owner_id, epoch=epoch, fence_token=fence_token, reason_code="v1272_reconciliation_required", now=now,
        )
        return {
            **blocked, "ok": False, "status": "ownership_transfer_blocked_by_v1272", "execution_allowed": False,
            "operator_reconciliation_required": True, "duplicate_external_activity_suppressed": True,
        }
    # No durable/in-flight external effect exists for this target. Ownership can
    # become active, but the underlying exact stage authorization is untouched.
    activated = activate_operation_after_reconciliation(
        ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
        owner_id=owner_id, epoch=epoch, fence_token=fence_token, reconciliation_code="v1272_no_inflight_effect", now=now,
    )
    return {
        **activated, "ok": True, "status": "ownership_transfer_reconciled_for_stage_entry",
        "execution_allowed": True, "underlying_exact_authorization_still_required": True,
        "duplicate_external_activity_suppressed": True, "fence_token": fence_token,
    }


def _acquire_and_reconcile(
    ownership_id: str, source_root: str | Path, *, runtime: Path, operation_code: str, target_id: str,
    owner_id: str, claimant_kind: str, lease_seconds: int, now: float | None,
) -> dict[str, Any]:
    claim = acquire_operation_ownership(
        ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
        owner_id=owner_id, claimant_kind=claimant_kind, lease_seconds=lease_seconds, now=now,
    )
    if claim.get("operation_status") in {"already_completed", "cancelled", "owned_elsewhere"}:
        return claim
    if claim.get("reconciliation_required"):
        return reconcile_transferred_ownership(
            ownership_id, source_root, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
            owner_id=owner_id, epoch=int(claim.get("epoch") or 0), fence_token=str(claim.get("fence_token") or ""), now=now,
        )
    return claim


def _finish_owned_result(
    ownership_id: str, *, runtime: Path, operation_code: str, target_id: str, owner_id: str,
    claim: Mapping[str, Any], result: Mapping[str, Any], now: float | None,
) -> dict[str, Any]:
    status = str(result.get("status") or "")
    restart_state = str(result.get("restart_operation_state") or "")
    if restart_state == "authorization_required" or "exact_authorization_required" in status:
        released = release_operation_ownership(
            ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
            owner_id=owner_id, epoch=int(claim.get("epoch") or 0), fence_token=str(claim.get("fence_token") or ""),
            release_code="authorization_required", now=now,
        )
        return {**result, "ownership_status": released.get("operation_status"), "ownership_execution_completed": False, "ownership_authority_created": False}
    recovery = load_restart_crash_recovery(str(load_ownership_concurrency(ownership_id, runtime_root=runtime).get("recovery_id") or ""), runtime_root=runtime)
    entry = _latest_recovery_entry(recovery, operation_code, target_id)
    if entry.get("state") == "completed" and str(entry.get("durable_lineage_digest") or ""):
        fence = fence_operation_result(
            ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
            owner_id=owner_id, epoch=int(claim.get("epoch") or 0), fence_token=str(claim.get("fence_token") or ""), now=now,
        )
        if not fence.get("result_may_commit"):
            return {
                **result, "ownership_status": fence.get("status"), "ownership_execution_completed": False,
                "late_result_fenced": True, "durable_v1272_result_retained_for_successor_reconciliation": True,
            }
        completed = complete_operation_ownership(
            ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
            owner_id=owner_id, epoch=int(claim.get("epoch") or 0), fence_token=str(claim.get("fence_token") or ""),
            completion_code=f"{operation_code}_completed", durable_lineage_digest=str(entry.get("durable_lineage_digest") or ""),
            result_digest=_digest(result), now=now,
        )
        return {**result, "ownership_status": completed.get("operation_status"), "ownership_execution_completed": bool(completed.get("completed")), "late_result_fenced": False}
    blocked = block_operation_ownership(
        ownership_id, runtime_root=runtime, operation_code=operation_code, target_id=target_id,
        owner_id=owner_id, epoch=int(claim.get("epoch") or 0), fence_token=str(claim.get("fence_token") or ""),
        reason_code="stage_not_durably_completed", now=now,
    )
    return {**result, "ownership_status": blocked.get("operation_status"), "ownership_execution_completed": False}


def execute_owned_candidate(
    ownership_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    owner_id: str,
    authorization_phrase: str,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    claimant_kind: str = "process",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: float | None = None,
    completion_now: float | None = None,
    post_stage_hook: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    ownership = load_ownership_concurrency(ownership_id, runtime_root=runtime)
    if not validate_ownership_concurrency(ownership).get("ok"):
        raise ValueError("valid_ownership_concurrency_required")
    target = _target_for_operation(ownership, "candidate_stage", runtime)
    claim = _acquire_and_reconcile(ownership_id, source_root, runtime=runtime, operation_code="candidate_stage", target_id=target, owner_id=owner_id, claimant_kind=claimant_kind, lease_seconds=lease_seconds, now=now)
    if not claim.get("execution_allowed"):
        return {
            "ok": claim.get("operation_status") == "already_completed", "status": str(claim.get("status") or claim.get("operation_status") or "ownership_not_executable"),
            "ownership_id": ownership_id, "ownership_epoch": claim.get("epoch"), "provider_contacted": False,
            "duplicate_external_activity_suppressed": True, "execution_allowed": False, **AUTHORITY_FLAGS,
        }
    result = execute_recoverable_candidate(
        str(ownership.get("recovery_id") or ""), source_root, runtime_root=runtime,
        authorization_phrase=authorization_phrase, provider=provider, post_stage_hook=post_stage_hook,
    )
    return _finish_owned_result(ownership_id, runtime=runtime, operation_code="candidate_stage", target_id=target, owner_id=owner_id, claim=claim, result=result, now=completion_now if completion_now is not None else now)


def execute_owned_verification_and_review(
    ownership_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    owner_id: str,
    repair_authorization_phrase: str,
    repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    budget: Mapping[str, Any] | None = None,
    claimant_kind: str = "process",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: float | None = None,
    completion_now: float | None = None,
    post_stage_hook: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    ownership = load_ownership_concurrency(ownership_id, runtime_root=runtime)
    if not validate_ownership_concurrency(ownership).get("ok"):
        raise ValueError("valid_ownership_concurrency_required")
    target = _target_for_operation(ownership, "verification_stage", runtime)
    claim = _acquire_and_reconcile(ownership_id, source_root, runtime=runtime, operation_code="verification_stage", target_id=target, owner_id=owner_id, claimant_kind=claimant_kind, lease_seconds=lease_seconds, now=now)
    if not claim.get("execution_allowed"):
        return {
            "ok": claim.get("operation_status") == "already_completed", "status": str(claim.get("status") or claim.get("operation_status") or "ownership_not_executable"),
            "ownership_id": ownership_id, "ownership_epoch": claim.get("epoch"), "provider_contacted": False, "tests_executed": False,
            "duplicate_external_activity_suppressed": True, "execution_allowed": False, **AUTHORITY_FLAGS,
        }
    result = execute_recoverable_verification_and_review(
        str(ownership.get("recovery_id") or ""), source_root, runtime_root=runtime,
        repair_authorization_phrase=repair_authorization_phrase, repair_provider=repair_provider, budget=budget,
        post_stage_hook=post_stage_hook,
    )
    return _finish_owned_result(ownership_id, runtime=runtime, operation_code="verification_stage", target_id=target, owner_id=owner_id, claim=claim, result=result, now=completion_now if completion_now is not None else now)


def ownership_concurrency_operator_status(ownership_id: str, *, runtime_root: str | Path | None, now: float | None = None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    row = load_ownership_concurrency(ownership_id, runtime_root=runtime)
    public = public_ownership_concurrency(row, now=now)
    recovery = load_restart_crash_recovery(str(row.get("recovery_id") or ""), runtime_root=runtime)
    public.update({
        "recovery_state": recovery.get("state"),
        "recovery_restart_generation": recovery.get("restart_generation"),
        "ownership_transfer_requires_recovery_reconciliation": True,
        "underlying_exact_authorization_still_required": True,
        "next_required_authority_derived_from_v1271_v1270": True,
        "automatic_execution_after_transfer": False,
    })
    return public


__all__ = [
    "CONTRACT_VERSION", "execute_owned_candidate", "execute_owned_verification_and_review",
    "reconcile_transferred_ownership", "ownership_concurrency_operator_status",
]
