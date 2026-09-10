from __future__ import annotations

"""Bounded supervised capability for mutable JSON encoding migration.

The surface is deliberately thin: it exposes the existing inventory, one exact
file preview, one confirmed application, and content-free status. It does not
scan-and-migrate, persist approvals, reveal payloads, or mutate metadata during
ordinary inspection.
"""

from pathlib import Path
from typing import Any

try:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    from metadata_store_inventory import inspect_mutable_json_stores, list_mutable_json_stores
    from metadata_migration_recovery import metadata_migration_recovery_status as _recovery_status, recover_pending_metadata_migrations
except ImportError:
    from metadata_migration import apply_metadata_migration, preview_metadata_migration
    from metadata_store_inventory import inspect_mutable_json_stores, list_mutable_json_stores
    from metadata_migration_recovery import metadata_migration_recovery_status as _recovery_status, recover_pending_metadata_migrations


class MetadataMigrationCapabilityError(ValueError):
    pass


def _public_result(value: dict[str, Any]) -> dict[str, Any]:
    """Return only bounded migration metadata, never file content or secret paths."""
    allowed = {
        "ok", "status", "store_id", "category", "relative_path", "path_exists",
        "valid_json", "root_shape_valid", "detected_encoding", "utf8_bom_present",
        "utf8_bom_present_before", "utf8_bom_present_after", "root_type",
        "expected_root_type", "size_bytes", "content_sha256", "canonical_sha256",
        "content_sha256_before", "content_sha256_after", "preview_token",
        "operator_confirmation_required", "operator_confirmed", "operator_registry",
        "operator_registry_confirmation_required", "operator_registry_confirmed",
        "backup_created", "backup_verified", "source_mutated", "payload_returned",
        "absolute_path_returned", "safe_retry", "uncertain_result", "recovery_required",
    }
    result = {key: value.get(key) for key in allowed if key in value}
    result["payload_returned"] = False
    result["absolute_path_returned"] = False
    result.pop("backup_reference", None)
    result["private_backup_reference_returned"] = False
    result["content_free"] = True
    return result


def metadata_migration_inventory(*, data_dir: Path | None = None) -> dict[str, Any]:
    inspection = inspect_mutable_json_stores(data_dir=data_dir)
    return {
        "ok": True,
        "status": "inventory_ready",
        "stores": list_mutable_json_stores(),
        "summary": inspection.get("summary") or {},
        "rows": inspection.get("rows") or [],
        "payload_returned": False,
        "absolute_path_returned": False,
        "source_mutated": False,
        "content_free": True,
        "bulk_migration_supported": False,
        "operator_confirmation_required_for_apply": True,
    }


def preview_metadata_migration_capability(
    store_id: str,
    relative_path: str,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    result = preview_metadata_migration(store_id, relative_path, data_dir=data_dir)
    public = _public_result(result)
    public.update(
        action="preview",
        source_mutated=False,
        exact_file_required=True,
        bulk_migration_supported=False,
    )
    return public


def apply_metadata_migration_capability(
    store_id: str,
    relative_path: str,
    *,
    preview_token: str,
    operator_confirmed: bool,
    operator_registry_confirmed: bool = False,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    if not str(preview_token or "").strip():
        raise MetadataMigrationCapabilityError("The exact migration preview token is required.")
    operator_confirmed = operator_confirmed is True
    operator_registry_confirmed = operator_registry_confirmed is True
    result = apply_metadata_migration(
        store_id,
        relative_path,
        preview_token=preview_token,
        operator_confirmed=operator_confirmed,
        operator_registry_confirmed=operator_registry_confirmed,
        data_dir=data_dir,
    )
    public = _public_result(result)
    public.update(
        action="apply",
        exact_file_required=True,
        bulk_migration_supported=False,
        technical_details_available=True,
    )
    return public


def metadata_migration_recovery_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    return _recovery_status(data_dir=data_dir)


def recover_metadata_migrations_capability(*, operator_confirmed: bool, data_dir: Path | None = None) -> dict[str, Any]:
    result = recover_pending_metadata_migrations(operator_confirmed=operator_confirmed is True, data_dir=data_dir)
    result["technical_details_available"] = True
    result["content_free"] = True
    return result
