from __future__ import annotations

"""Bounded daily-use status for mutable metadata recovery.

The status is assembled from current private coordination and recovery state. It
contains no metadata payloads or private paths and does not contact providers,
change models, or mutate a store during inspection.
"""

from pathlib import Path
from typing import Any

try:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    from metadata_migration_recovery import metadata_migration_recovery_status
except ImportError:
    from metadata_artifact_reconciliation import inspect_orphaned_metadata_artifacts, reconcile_orphaned_metadata_artifacts
    from metadata_migration_recovery import metadata_migration_recovery_status


def _message(status: str) -> str:
    return {
        "healthy": "Metadata stores are available. Ordinary conversation and supervised project work can continue.",
        "busy": "A metadata store is being updated by another live process. Conversation remains available; retry metadata work after it finishes.",
        "recovery_required": "A metadata update needs explicit recovery. Conversation remains available while metadata changes stay blocked.",
        "safely_recovered": "Redundant private metadata artifacts were safely reconciled. No conversation or provider state changed.",
        "uncertain": "A metadata artifact cannot be reconciled automatically. Conversation remains available; metadata changes require operator review.",
    }.get(status, "Metadata recovery state is unavailable. No metadata change was attempted.")


def build_metadata_recovery_state(*, data_dir: Path | None = None) -> dict[str, Any]:
    artifacts = inspect_orphaned_metadata_artifacts(data_dir=data_dir)
    recovery = metadata_migration_recovery_status(data_dir=data_dir)
    counts = dict(artifacts.get("counts") or {})
    if counts.get("operator_review") or recovery.get("invalid_private_record_count"):
        status = "uncertain"
    elif recovery.get("pending_operation_count") or counts.get("recovery_required"):
        status = "recovery_required"
    elif counts.get("busy"):
        status = "busy"
    else:
        status = "healthy"
    return {
        "ok": status in {"healthy", "busy"},
        "status": status,
        "message": _message(status),
        "summary": {
            "busy_store_count": int(counts.get("busy") or 0),
            "recovery_required_count": max(int(recovery.get("pending_operation_count") or 0), int(counts.get("recovery_required") or 0)),
            "safe_cleanup_count": int(counts.get("safe_cleanup") or 0),
            "operator_review_count": int(counts.get("operator_review") or 0) + int(recovery.get("invalid_private_record_count") or 0),
            "verified_backup_count": int(counts.get("verified_backup") or 0),
        },
        "controls": {
            "ordinary_conversation_available": True,
            "metadata_mutations_enabled": status == "healthy",
            "safe_cleanup_available": bool(counts.get("safe_cleanup")),
            "confirmed_recovery_available": bool(recovery.get("pending_operation_count")),
            "operator_review_required": status == "uncertain",
        },
        "technical_details_available": True,
        "provider_contacted": False,
        "payload_returned": False,
        "absolute_path_returned": False,
        "lock_token_returned": False,
        "backup_path_returned": False,
        "recovery_secret_returned": False,
        "source_mutated": False,
        "content_free": True,
    }


def reconcile_metadata_recovery_state(*, operator_confirmed: bool, data_dir: Path | None = None) -> dict[str, Any]:
    result = reconcile_orphaned_metadata_artifacts(operator_confirmed=operator_confirmed is True, data_dir=data_dir)
    state = build_metadata_recovery_state(data_dir=data_dir)
    if result.get("status") == "confirmation_required":
        return {**state, "ok": False, "status": "confirmation_required", "message": "Explicit operator confirmation is required before safe private-artifact cleanup.", "removed": 0}
    removed = int(result.get("removed") or 0)
    if removed and state.get("status") == "healthy":
        return {**state, "ok": True, "status": "safely_recovered", "message": _message("safely_recovered"), "removed": removed}
    return {**state, "removed": removed}
