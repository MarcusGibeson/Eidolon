from __future__ import annotations

"""v1273.6-v1273.8 ownership/concurrency reliability hardening."""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from self_development_alpha_foundations import _runtime_root
from restart_crash_recovery_foundations import load_restart_crash_recovery
from ownership_concurrency_foundations import *
from ownership_concurrency_foundations import _path, _read, _root
from ownership_concurrency import reconcile_transferred_ownership, ownership_concurrency_operator_status

CONTRACT_VERSION = "v1273.8"


def transfer_expired_operation_ownership(
    ownership_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    operation_code: str,
    target_id: str,
    successor_owner_id: str,
    claimant_kind: str = "recovery_worker",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: float | None = None,
) -> dict[str, Any]:
    claim = acquire_operation_ownership(
        ownership_id, runtime_root=runtime_root, operation_code=operation_code, target_id=target_id,
        owner_id=successor_owner_id, claimant_kind=claimant_kind, lease_seconds=lease_seconds, now=now,
    )
    if claim.get("operation_status") == "owned_elsewhere":
        return {**claim, "ok": False, "status": "ownership_transfer_denied_live_owner", "execution_allowed": False}
    if claim.get("operation_status") == "already_completed":
        return {**claim, "ok": True, "status": "ownership_transfer_not_required_completed", "execution_allowed": False}
    if not claim.get("reconciliation_required"):
        return {**claim, "ok": True, "status": "ownership_transfer_not_required", "execution_allowed": bool(claim.get("execution_allowed"))}
    return reconcile_transferred_ownership(
        ownership_id, source_root, runtime_root=runtime_root, operation_code=operation_code, target_id=target_id,
        owner_id=successor_owner_id, epoch=int(claim.get("epoch") or 0), fence_token=str(claim.get("fence_token") or ""), now=now,
    )


def recover_expired_ownership_claims(
    ownership_id: str,
    *,
    runtime_root: str | Path | None,
    now: float | None = None,
) -> dict[str, Any]:
    """Read-only projection of claims that need explicit transfer/reconciliation."""
    clock = float(time.time() if now is None else now)
    row = load_ownership_concurrency(ownership_id, runtime_root=runtime_root)
    if not validate_ownership_concurrency(row).get("ok"):
        return {"ok": False, "status": "ownership_concurrency_invalid", **AUTHORITY_FLAGS}
    latest: dict[str, dict[str, Any]] = {}
    for claim in row.get("claims") or []:
        latest[str(claim.get("claim_key") or "")] = dict(claim)
    expired = [x for x in latest.values() if x.get("state") in {"active", "reconciliation_required"} and clock >= float(x.get("lease_expires_at") or 0.0)]
    return {
        "ok": True,
        "status": "expired_ownership_claims_detected" if expired else "ownership_claims_current",
        "expired_claim_count": len(expired),
        "expired_claim_keys": [str(x.get("claim_key") or "") for x in expired],
        "automatic_transfer_performed": False,
        "automatic_execution_performed": False,
        "explicit_successor_claim_required": bool(expired),
        "v1272_reconciliation_required_before_successor_execution": bool(expired),
        **AUTHORITY_FLAGS,
    }


def quarantine_invalid_ownership_projection(
    ownership_id: str,
    *,
    runtime_root: str | Path | None,
    now: float | None = None,
) -> dict[str, Any]:
    """Quarantine a malformed v1273 projection; never infer lost ownership history."""
    runtime = _runtime_root(runtime_root)
    path = _path(ownership_id, runtime)
    if not path.exists():
        return {"ok": False, "status": "ownership_projection_missing", **AUTHORITY_FLAGS}
    try:
        row = _read(path)
        if validate_ownership_concurrency(row).get("ok"):
            return {"ok": True, "status": "ownership_projection_valid_no_quarantine", "quarantined": False, **AUTHORITY_FLAGS}
    except Exception:
        pass
    qroot = _root(runtime) / "quarantine"; qroot.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time() if now is None else now)
    target = qroot / f"{ownership_id}-{stamp}.json"
    try:
        os.replace(path, target)
    except OSError:
        try:
            shutil.copy2(path, target); path.unlink(missing_ok=True)
        except OSError:
            return {"ok": False, "status": "ownership_projection_quarantine_failed", **AUTHORITY_FLAGS}
    return {
        "ok": True, "status": "ownership_projection_quarantined_operator_reconciliation_required",
        "quarantined": True, "ownership_history_reconstructed": False, "automatic_transfer_performed": False,
        "operator_reconciliation_required": True, **AUTHORITY_FLAGS,
    }


def inspect_ownership_concurrency_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required = [
        "ownership_concurrency_foundations.py", "ownership_concurrency.py", "ownership_concurrency_reliability.py",
        "restart_crash_recovery_foundations.py", "restart_crash_recovery.py", "restart_crash_recovery_reliability.py",
        "long_running_work_sessions_reliability.py", "self_development_alpha.py",
    ]
    checks = {name.replace(".py", "_present"): (root / "conscious_agent" / name).is_file() for name in required}
    return {
        "ok": all(checks.values()),
        "status": "ownership_concurrency_health_ready" if all(checks.values()) else "ownership_concurrency_health_blocked",
        "checks": checks,
        "native_windows_validation": "desktop_review_required",
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


def build_ownership_concurrency_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_ownership_concurrency_health(source_root=source_root)
    return {
        "ok": health.get("ok") is True,
        "contract_version": CONTRACT_VERSION,
        "status": "ownership_concurrency_operator_handoff_ready" if health.get("ok") else "ownership_concurrency_operator_handoff_blocked",
        "capabilities": [
            "durable_stage_ownership_claims", "cross_process_lock_serialized_claim_acquisition", "browser_tab_queue_retry_owner_identity_hashing",
            "bounded_lease_heartbeat", "expired_owner_fencing", "explicit_successor_epoch_transfer", "v1272_reconciliation_before_transferred_execution",
            "late_provider_tool_result_rejection", "terminal_completion_duplicate_suppression", "content_minimized_owner_projection",
        ],
        "known_limitations": [
            "ownership_claims_coordinate_v1270_v1272_stage_entry_not_arbitrary_external_services",
            "os_filesystem_lock_semantics_require_native_windows_desktop_validation",
            "network_partition_distributed_consensus_is_out_of_scope_for_local_v1273",
            "corrupt_v1273_projection_is_quarantined_not_invented_from_missing_history",
            "v1273_does_not_create_replace_or_reuse_v1265_v1267_v1269_authorization",
        ],
        "native_windows_review": [
            "two_process_same_stage_claim_race", "browser_tab_and_api_worker_duplicate_submission", "queue_retry_after_owner_process_death",
            "expired_lease_successor_transfer_with_v1272_reconciliation", "late_result_from_fenced_process", "filesystem_lock_cleanup_after_forced_termination",
            "ntfs_directory_lock_atomic_replace_and_antivirus_contention", "long_runtime_paths_and_restart",
        ],
        "next_bounded_unit": "v1274 Environment Awareness",
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


__all__ = [
    "CONTRACT_VERSION", "transfer_expired_operation_ownership", "recover_expired_ownership_claims",
    "quarantine_invalid_ownership_projection", "inspect_ownership_concurrency_health", "build_ownership_concurrency_operator_handoff",
]
