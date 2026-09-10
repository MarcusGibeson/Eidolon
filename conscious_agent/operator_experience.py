from __future__ import annotations
"""v1279.3-v1279.5 integration with the real supervised development lineage."""
from pathlib import Path
from typing import Any

from paths import DATA_DIR
from self_development_alpha_foundations import _runtime_root, _stage_root, load_self_development_alpha_campaign
from long_running_work_sessions_foundations import load_long_running_work_session
from long_running_work_sessions import pause_long_running_work_session, resume_long_running_work_session, cancel_long_running_work_session
from restart_crash_recovery_foundations import recovery_id_for_session, load_restart_crash_recovery
from restart_crash_recovery import reconcile_restart_crash_recovery
from ownership_concurrency_foundations import ownership_id_for_recovery, load_ownership_concurrency
from development_observability_foundations import load_development_observability, validate_development_observability
from development_observability import development_observability_operator_status
from operator_review_handoff_foundations import load_operator_review_packet
from governed_self_update_foundations import _read_json as _read_update_json
from operator_experience_foundations import AUTHORITY_FLAGS, build_operator_experience_projection, validate_operator_experience_projection

CONTRACT_VERSION = "v1279.5"


def _find_update(review_id: str, runtime: Path) -> dict[str, Any]:
    if not review_id:
        return {}
    roots = [
        _stage_root(runtime, "v1269") / "governed_self_update" / "updates",
        runtime / "governed_self_update" / "updates",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("selfupdate_*.json"), key=lambda p: p.name.casefold()):
            try:
                row = _read_update_json(path)
            except Exception:
                continue
            if row.get("review_id") == review_id:
                return row
    return {}


def _find_rollback(update: dict[str, Any], runtime: Path) -> dict[str, Any]:
    update_id = str(update.get("update_id") or "")
    if not update_id:
        return {}
    roots = [
        _stage_root(runtime, "v1269") / "governed_self_update" / "rollbacks" / f"{update_id}.json",
        runtime / "governed_self_update" / "rollbacks" / f"{update_id}.json",
    ]
    for path in roots:
        if path.is_file():
            try:
                return _read_update_json(path)
            except Exception:
                return {}
    return {}


def build_operator_experience_snapshot(observability_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root if runtime_root is not None else DATA_DIR)
    observability = load_development_observability(observability_id, runtime_root=runtime)
    if not observability or not validate_development_observability(observability).get("ok"):
        raise ValueError("valid_v1277_observability_required")
    # Synchronization is read-only with respect to source/provider/test/update activity;
    # it may append bounded external-runtime observability receipts.
    public_observability = development_observability_operator_status(observability_id, runtime_root=runtime)
    session_id = str(observability.get("session_id") or "")
    campaign_id = str(observability.get("campaign_id") or "")
    session = load_long_running_work_session(session_id, runtime_root=runtime)
    campaign = load_self_development_alpha_campaign(campaign_id, runtime_root=runtime)
    source_digest = str(observability.get("source_manifest_digest") or "")
    recovery_id = recovery_id_for_session(session_id, campaign_id, source_digest)
    recovery = load_restart_crash_recovery(recovery_id, runtime_root=runtime)
    ownership_id = ownership_id_for_recovery(recovery_id, source_digest)
    ownership = load_ownership_concurrency(ownership_id, runtime_root=runtime)
    review_id = str(campaign.get("review_id") or "")
    review = load_operator_review_packet(review_id, runtime_root=_stage_root(runtime, "v1268")) if review_id else {}
    update = _find_update(review_id, runtime)
    rollback = _find_rollback(update, runtime)
    row = build_operator_experience_projection(campaign=campaign, session=session, observability=public_observability, recovery=recovery, ownership=ownership, review_packet=review, update=update, rollback=rollback)
    if not validate_operator_experience_projection(row).get("ok"):
        raise ValueError("operator_experience_projection_invalid")
    return row


def list_operator_experience_snapshots(*, runtime_root: str | Path | None = None, limit: int = 24) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root if runtime_root is not None else DATA_DIR)
    root = runtime / "development_observability" / "records"
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if root.is_dir():
        for path in sorted(root.glob("observability_*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:max(1, min(int(limit), 100))]:
            try:
                rows.append(build_operator_experience_snapshot(path.stem, runtime_root=runtime))
            except Exception as exc:
                errors.append(type(exc).__name__)
    return {"ok": not errors, "status": "operator_experience_snapshots_ready" if not errors else "operator_experience_snapshots_partial", "snapshots": rows, "snapshot_count": len(rows), "error_count": len(errors), "error_codes": sorted(set(errors)), "content_minimized": True, "private_payloads_exposed": False, **AUTHORITY_FLAGS}


def operator_experience_session_control(observability_id: str, *, action: str, runtime_root: str | Path | None = None, reason: str = "operator_dashboard_control") -> dict[str, Any]:
    runtime = _runtime_root(runtime_root if runtime_root is not None else DATA_DIR)
    obs = load_development_observability(observability_id, runtime_root=runtime)
    if not obs or not validate_development_observability(obs).get("ok"):
        raise ValueError("valid_v1277_observability_required")
    session_id = str(obs.get("session_id") or "")
    action = str(action or "").strip().lower()
    if action == "pause":
        result = pause_long_running_work_session(session_id, runtime_root=runtime, reason=reason)
    elif action == "resume":
        result = resume_long_running_work_session(session_id, runtime_root=runtime)
    elif action == "cancel":
        result = cancel_long_running_work_session(session_id, runtime_root=runtime, reason=reason)
    else:
        return {"ok": False, "status": "operator_experience_invalid_session_control", "allowed_actions": ["pause", "resume", "cancel"], **AUTHORITY_FLAGS}
    return {"ok": bool(result.get("ok", True)), "status": "operator_experience_session_control_recorded", "action": action, "session_id": session_id, "session_state": result.get("state"), "provider_contacted": False, "tests_executed": False, "active_source_modified": False, "snapshot": build_operator_experience_snapshot(observability_id, runtime_root=runtime), **AUTHORITY_FLAGS}


def operator_experience_reconcile_recovery(observability_id: str, source_root: str | Path, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root if runtime_root is not None else DATA_DIR)
    obs = load_development_observability(observability_id, runtime_root=runtime)
    if not obs or not validate_development_observability(obs).get("ok"):
        raise ValueError("valid_v1277_observability_required")
    session_id = str(obs.get("session_id") or "")
    campaign_id = str(obs.get("campaign_id") or "")
    recovery_id = recovery_id_for_session(session_id, campaign_id, str(obs.get("source_manifest_digest") or ""))
    result = reconcile_restart_crash_recovery(recovery_id, source_root, runtime_root=runtime)
    return {"ok": bool(result.get("ok")), "status": "operator_experience_recovery_reconciled" if result.get("ok") else str(result.get("status") or "operator_experience_recovery_blocked"), "provider_replayed": False, "tests_replayed": False, "active_source_modified": False, "recovery_result_code": str(result.get("status") or "unknown"), "snapshot": build_operator_experience_snapshot(observability_id, runtime_root=runtime), **AUTHORITY_FLAGS}


__all__ = ["CONTRACT_VERSION", "build_operator_experience_snapshot", "list_operator_experience_snapshots", "operator_experience_session_control", "operator_experience_reconcile_recovery"]
