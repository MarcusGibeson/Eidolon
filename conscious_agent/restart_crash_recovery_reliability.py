from __future__ import annotations

"""v1272.6-v1272.8 restart/crash/provider/Windows reliability hardening."""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from self_development_alpha_foundations import _runtime_root, load_self_development_alpha_campaign
from long_running_work_sessions import interrupt_long_running_work_session
from long_running_work_sessions_reliability import reconcile_long_running_work_session
from governed_self_update_reliability import inspect_governed_self_update_health
from restart_crash_recovery_foundations import *
from restart_crash_recovery import reconcile_restart_crash_recovery, restart_crash_recovery_operator_status

CONTRACT_VERSION = "v1272.8"


def recover_after_process_restart(
    recovery_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    interruption_code: str = "process_restart",
    now: float | None = None,
) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root)
    row = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    if not validate_restart_crash_recovery(row).get("ok"):
        return {"ok": False, "status": "restart_crash_recovery_invalid", **AUTHORITY_FLAGS}
    note_recovery_interruption(recovery_id, runtime_root=runtime, interruption_code=interruption_code, now=now)
    # Reconcile an expired v1271 lease before recording the process-level
    # interruption; otherwise clearing the lease first would erase the very
    # crash evidence we need to inspect.
    long_recon = reconcile_long_running_work_session(str(row.get("session_id") or ""), runtime_root=runtime, now=now)
    if str(long_recon.get("state") or "") != "interrupted":
        interrupt_long_running_work_session(str(row.get("session_id") or ""), runtime_root=runtime, reason=interruption_code)
    recovery = reconcile_restart_crash_recovery(recovery_id, source_root, runtime_root=runtime, now=now)
    return {
        **recovery,
        "status": "restart_crash_recovery_restart_reconciled" if recovery.get("ok") else recovery.get("status"),
        "long_session_status": long_recon.get("status"),
        "stale_lease_recovered": bool(long_recon.get("expired_lease_recovered")),
        "provider_replayed": False,
        "tests_replayed": False,
        "update_replayed": False,
        "automatic_resume": False,
    }


def rebuild_recovery_from_authoritative_lineage(
    session_id: str,
    *,
    runtime_root: str | Path | None,
    now: float | None = None,
) -> dict[str, Any]:
    """Quarantine only a malformed v1272 projection and rebuild from v1271/v1270.

    This function does not attempt to reconstruct an in-flight external effect.
    If the v1272 write-ahead journal is unreadable, that uncertainty is made
    explicit and the rebuilt record is blocked for operator reconciliation.
    """
    runtime = _runtime_root(runtime_root)
    # Derive deterministic identity from valid lower lineage.
    from long_running_work_sessions_foundations import load_long_running_work_session, validate_long_running_work_session
    session = load_long_running_work_session(session_id, runtime_root=runtime)
    if not session or not validate_long_running_work_session(session).get("ok"):
        return {"ok": False, "status": "restart_crash_recovery_rebuild_missing_long_session", **AUTHORITY_FLAGS}
    alpha = load_self_development_alpha_campaign(str(session.get("campaign_id") or ""), runtime_root=runtime)
    if not alpha:
        return {"ok": False, "status": "restart_crash_recovery_rebuild_missing_campaign", **AUTHORITY_FLAGS}
    recovery_id = recovery_id_for_session(session_id, str(session.get("campaign_id") or ""), str(alpha.get("source_manifest_digest") or ""))
    path = _path(recovery_id, runtime)
    quarantined = False
    if path.exists():
        try:
            current = _read(path)
            if validate_restart_crash_recovery(current).get("ok"):
                return {**public_restart_crash_recovery(current), "ok": True, "status": "restart_crash_recovery_rebuild_not_required", "quarantined": False}
        except Exception:
            pass
        qroot = _quarantine_root(runtime)
        qroot.mkdir(parents=True, exist_ok=True)
        stamp = f"{int(time.time() if now is None else now)}"
        target = qroot / f"{recovery_id}-{stamp}.json"
        try:
            os.replace(path, target)
            quarantined = True
        except OSError:
            try:
                shutil.copy2(path, target)
                path.unlink(missing_ok=True)
                quarantined = True
            except OSError:
                return {"ok": False, "status": "restart_crash_recovery_quarantine_failed", **AUTHORITY_FLAGS}
    rebuilt = prepare_restart_crash_recovery(session_id, runtime_root=runtime, now=now)
    from restart_crash_recovery_foundations import _save_with_receipt
    blocked = dict(rebuilt)
    blocked["state"] = "blocked"
    blocked["status"] = "restart_crash_recovery_rebuilt_from_lower_lineage"
    blocked = _save_with_receipt(
        blocked, runtime_root=runtime, receipt_code="recovery_projection_rebuilt",
        reason_codes=["v1272_journal_unavailable", "operator_reconciliation_required"], state="blocked", now=now,
    )
    _write(path, blocked)
    return {
        **public_restart_crash_recovery(blocked),
        "ok": True,
        "status": "restart_crash_recovery_rebuilt_blocked_for_review",
        "quarantined": quarantined,
        "external_effect_history_assumed": False,
        "operator_reconciliation_required": True,
    }


def inspect_governed_update_restart_state(
    update_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    """Read-only v1269 update recovery projection; never retries an update."""
    health = inspect_governed_self_update_health(update_id, source_root, runtime_root=runtime_root)
    return {
        "ok": health.get("ok") is True,
        "status": "governed_update_restart_state_ready" if health.get("ok") else "governed_update_restart_state_attention_required",
        "update_id": update_id,
        "update_phase": health.get("phase"),
        "target_state": health.get("target_state"),
        "backup_present": health.get("backup_present"),
        "lease_active": health.get("lease_active"),
        "recovery_disposition": health.get("recovery_disposition"),
        "update_executed_by_v1272": False,
        "authorization_reused_by_v1272": False,
        "fresh_v1269_authority_contract_preserved": True,
        "successful_rollback_remains_separately_authorized": True,
        **AUTHORITY_FLAGS,
    }


def inspect_restart_crash_recovery_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required = [
        "restart_crash_recovery_foundations.py", "restart_crash_recovery.py", "restart_crash_recovery_reliability.py",
        "long_running_work_sessions_foundations.py", "long_running_work_sessions.py", "long_running_work_sessions_reliability.py",
        "self_development_alpha.py", "isolated_self_modification_reliability.py", "iterative_self_repair_reliability.py",
        "governed_self_update_reliability.py",
    ]
    checks = {name.replace(".py", "_present"): (root / "conscious_agent" / name).is_file() for name in required}
    return {
        "ok": all(checks.values()),
        "status": "restart_crash_recovery_health_ready" if all(checks.values()) else "restart_crash_recovery_health_blocked",
        "checks": checks,
        "native_windows_validation": "desktop_review_required",
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


def build_restart_crash_recovery_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_restart_crash_recovery_health(source_root=source_root)
    return {
        "ok": health.get("ok") is True,
        "contract_version": CONTRACT_VERSION,
        "status": "restart_crash_recovery_operator_handoff_ready" if health.get("ok") else "restart_crash_recovery_operator_handoff_blocked",
        "capabilities": [
            "write_ahead_external_stage_journal", "durable_lineage_reconciliation", "crash_after_stage_commit_deduplication",
            "ambiguous_external_effect_fail_closed", "process_restart_recovery", "dashboard_closure_recovery",
            "machine_interruption_recovery", "provider_outage_pause_and_return_evidence", "stale_v1271_lease_reconciliation",
            "corrupt_v1272_projection_quarantine", "read_only_v1269_update_restart_inspection",
        ],
        "known_limitations": [
            "cross_process_exactly_once_ownership_deferred_to_v1273",
            "provider_contact_interrupted_before_durable_lower_stage_commit_requires_operator_reconciliation_not_automatic_retry",
            "v1272_does_not_issue_replacement_v1265_or_v1267_authorization_tokens",
            "v1272_never_replays_or_authorizes_v1269_update_or_rollback",
            "native_windows_kill_power_loss_ntfs_lock_and_long_path_behavior_requires_desktop_review",
        ],
        "native_windows_review": [
            "process_kill_between_write_ahead_and_stage_commit",
            "process_kill_between_lower_stage_commit_and_v1272_receipt",
            "dashboard_api_shutdown_and_restart",
            "machine_restart_with_expired_v1271_lease",
            "filesystem_lock_release_after_process_death",
            "ntfs_atomic_replace_and_partial_write_behavior",
            "long_runtime_paths",
            "governed_update_running_state_read_only_recovery_projection",
        ],
        "next_bounded_unit": "v1273 Ownership and Concurrency",
        "active_source_modified": False,
        **AUTHORITY_FLAGS,
    }


__all__ = [
    "CONTRACT_VERSION", "recover_after_process_restart", "rebuild_recovery_from_authoritative_lineage",
    "inspect_governed_update_restart_state", "inspect_restart_crash_recovery_health",
    "build_restart_crash_recovery_operator_handoff",
]
