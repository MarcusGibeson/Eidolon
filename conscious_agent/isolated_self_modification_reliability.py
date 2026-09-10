from __future__ import annotations

"""v1265.6-v1265.8 isolation, freshness, tamper, recovery, and operator handoff."""

import hashlib
import shutil
from pathlib import Path
from typing import Any, Mapping

from isolated_self_modification_foundations import (
    SELF_MODIFICATION_DENIED_AUTHORITY, _digest, _record_digest, _record_path, _runtime_root, _write_json,
    check_self_source_freshness, load_self_modification, source_only_manifest,
)

CONTRACT_VERSION = "v1265.8"


def validate_self_modification_candidate(operation_id: str, source_root: str | Path, *, runtime_root: str | Path | None) -> dict[str, Any]:
    record = load_self_modification(operation_id, runtime_root=runtime_root)
    if not record:
        return {"ok": False, "status": "self_modification_candidate_missing"}
    digest_ok = str(record.get("record_digest") or "") == _record_digest(record)
    freshness = check_self_source_freshness(operation_id, source_root, runtime_root=runtime_root)
    workspace_ok = False; candidate_digest = ""
    try:
        workspace = Path(str(record.get("workspace_path") or "")).resolve(strict=True)
        candidate = source_only_manifest(workspace)
        candidate_digest = candidate["source_manifest_digest"]
        if record.get("phase") == "sealed":
            workspace_ok = candidate_digest == (record.get("result") or {}).get("candidate_manifest_digest")
        else:
            workspace_ok = candidate_digest == record.get("workspace_baseline_manifest_digest")
    except Exception:
        workspace_ok = False
    active_untouched = record.get("active_source_modified") is False
    authority_ok = all(record.get(k, v) is v for k, v in SELF_MODIFICATION_DENIED_AUTHORITY.items() if k not in {"provider_contact_authorized"})
    ok = digest_ok and freshness.get("ok") is True and workspace_ok and active_untouched and authority_ok
    return {"ok": ok, "status": "self_modification_candidate_valid" if ok else "self_modification_candidate_invalid", "record_digest_valid": digest_ok, "source_fresh": freshness.get("ok") is True, "workspace_manifest_valid": workspace_ok, "candidate_manifest_digest": candidate_digest, "active_source_untouched": active_untouched, "authority_contained": authority_ok}


def cancel_isolated_self_modification(operation_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root); path = _record_path(operation_id, runtime); record = load_self_modification(operation_id, runtime_root=runtime)
    if not record: return {"ok": False, "status": "self_modification_record_missing"}
    if record.get("phase") == "sealed": return {"ok": False, "status": "sealed_candidate_requires_review_or_cleanup"}
    row = dict(record); row.update({"phase": "cancelled", "status": "isolated_self_modification_cancelled", "active_source_modified": False, "isolated_workspace_modified": False})
    row["record_digest"] = _record_digest(row); _write_json(path, row); return {**row, "ok": True}


def cleanup_isolated_self_modification(operation_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root); record = load_self_modification(operation_id, runtime_root=runtime)
    if not record: return {"ok": True, "status": "self_modification_cleanup_already_complete", "operation_id": operation_id}
    workspace = Path(str(record.get("workspace_path") or ""))
    parent = workspace.parent if workspace.name == "Eidolon" else workspace
    shutil.rmtree(parent, ignore_errors=True)
    return {"ok": not parent.exists(), "status": "self_modification_workspace_cleaned" if not parent.exists() else "self_modification_cleanup_blocked", "operation_id": operation_id, "active_source_modified": False}


def recover_interrupted_self_modification(operation_id: str, source_root: str | Path, *, runtime_root: str | Path | None) -> dict[str, Any]:
    runtime = _runtime_root(runtime_root); path = _record_path(operation_id, runtime); record = load_self_modification(operation_id, runtime_root=runtime)
    if not record: return {"ok": False, "status": "self_modification_record_missing"}
    if record.get("phase") != "running": return {"ok": True, "status": "self_modification_recovery_not_needed", "phase": record.get("phase")}
    fresh = check_self_source_freshness(operation_id, source_root, runtime_root=runtime)
    if not fresh.get("ok"):
        return {"ok": False, "status": "stale_self_source_detected", "automatic_provider_retry": False}
    # Fail closed.  A provider may have been contacted before interruption; v1265
    # never repeats it automatically.  Operator can discard and prepare anew.
    row = dict(record); row.update({"phase": "blocked", "status": "interrupted_self_modification_requires_operator_reprepare", "automatic_provider_retry": False, "active_source_modified": False})
    row["record_digest"] = _record_digest(row); _write_json(path, row)
    return {**row, "ok": True}


def inspect_isolated_self_modification_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    checks = {
        "foundations_present": (root / "conscious_agent/isolated_self_modification_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/isolated_self_modification.py").is_file(),
        "v1264_planning_retained": (root / "conscious_agent/alternative_planning.py").is_file(),
        "privacy_policy_retained": (root / "conscious_agent/package_integrity.py").is_file(),
    }
    return {"ok": all(checks.values()), "contract_version": CONTRACT_VERSION, "checks": checks, "read_only": True, "active_source_modified": False, "provider_contacted": False, **SELF_MODIFICATION_DENIED_AUTHORITY}


def build_isolated_self_modification_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_isolated_self_modification_health(source_root=source_root)
    row = {
        "ok": health["ok"], "contract_version": CONTRACT_VERSION, "status": "isolated_self_modification_operator_handoff_ready" if health["ok"] else "isolated_self_modification_operator_handoff_blocked",
        "native_windows_review": ["real_ntfs_junction_and_reparse_containment", "long_path_workspace_materialization", "case_insensitive_collision_behavior", "cross_process_duplicate_authorization"],
        "review_boundaries": ["active_source_never_modified", "runtime_private_data_not_copied", "provider_retry_after_interruption_is_not_automatic", "candidate_application_deferred", "test_selection_deferred_to_v1266"],
        "next_bounded_unit": "v1266 Intelligent Test Selection", "read_only": True, "content_minimized": True, "active_source_modified": False,
        **SELF_MODIFICATION_DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row); return row


__all__ = ["CONTRACT_VERSION", "validate_self_modification_candidate", "cancel_isolated_self_modification", "cleanup_isolated_self_modification", "recover_interrupted_self_modification", "inspect_isolated_self_modification_health", "build_isolated_self_modification_operator_handoff"]
