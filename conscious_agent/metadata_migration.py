from __future__ import annotations

"""Preview-bound migration for inventoried mutable JSON runtime stores.

This module deliberately stores no migration queue or durable approval ledger.
A preview token is recomputed from the exact current file bytes, encoding, root
shape, and canonical output. Applying a migration requires explicit operator
confirmation and writes a verified private backup beneath the runtime data root.
"""

from pathlib import Path, PurePosixPath
from typing import Any

from paths import DATA_DIR
try:
    from json_storage import apply_json_migration, preview_json_migration
    from metadata_store_inventory import get_mutable_json_store
except ImportError:
    from json_storage import apply_json_migration, preview_json_migration
    from metadata_store_inventory import get_mutable_json_store


class MetadataMigrationError(ValueError):
    pass


def _safe_relative_path(value: str) -> str:
    token = str(value or "").replace("\\", "/").strip().lstrip("/")
    candidate = PurePosixPath(token)
    if not token or candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise MetadataMigrationError("Metadata path must be a safe runtime-data-relative path.")
    return candidate.as_posix()


def _resolve_store_path(store_id: str, relative_path: str, *, data_dir: Path | None = None):
    store = get_mutable_json_store(store_id)
    if store is None:
        raise MetadataMigrationError("Unknown mutable JSON store.")
    if not store.migration_allowed:
        raise MetadataMigrationError("This metadata store does not support encoding migration.")
    relative = _safe_relative_path(relative_path)
    if not PurePosixPath(relative).match(store.relative_pattern):
        raise MetadataMigrationError("Metadata path does not match the selected store family.")
    root = Path(data_dir or DATA_DIR).expanduser().resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise MetadataMigrationError("Metadata path escapes the runtime data root.") from error
    return store, root, target, relative


def preview_metadata_migration(
    store_id: str,
    relative_path: str,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    store, _root, target, relative = _resolve_store_path(store_id, relative_path, data_dir=data_dir)
    preview = preview_json_migration(target, expected_type=store.expected_type)
    return {
        **preview,
        "store_id": store.store_id,
        "category": store.category,
        "relative_path": relative,
        "operator_registry": store.operator_registry,
        "operator_registry_confirmation_required": store.operator_registry,
        "absolute_path_returned": False,
        "payload_returned": False,
    }


def apply_metadata_migration(
    store_id: str,
    relative_path: str,
    *,
    preview_token: str,
    operator_confirmed: bool,
    operator_registry_confirmed: bool = False,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    store, root, target, relative = _resolve_store_path(store_id, relative_path, data_dir=data_dir)
    operator_confirmed = operator_confirmed is True
    operator_registry_confirmed = operator_registry_confirmed is True
    if store.operator_registry and not operator_registry_confirmed:
        preview = preview_metadata_migration(store_id, relative_path, data_dir=root)
        return {
            **preview,
            "ok": False,
            "status": "operator_registry_confirmation_required",
            "operator_confirmed": bool(operator_confirmed),
            "operator_registry_confirmed": False,
            "source_mutated": False,
            "backup_created": False,
        }
    backup_dir = root / "metadata_migration_backups" / store.store_id
    result = apply_json_migration(
        target,
        preview_token=preview_token,
        operator_confirmed=operator_confirmed,
        expected_type=store.expected_type,
        backup_dir=backup_dir,
    )
    return {
        **result,
        "store_id": store.store_id,
        "category": store.category,
        "relative_path": relative,
        "operator_registry": store.operator_registry,
        "operator_registry_confirmed": bool(operator_registry_confirmed),
        "absolute_path_returned": False,
        "payload_returned": False,
    }
