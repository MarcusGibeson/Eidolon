from __future__ import annotations

"""v1150.1 crash-safe copy-only migration of legacy source-local runtime data.

The migration never deletes or rewrites the legacy source. It refuses to merge
with a populated external runtime, stages a complete copy beside the target,
verifies a deterministic inventory digest, and atomically installs the staged
runtime. A small external journal permits safe retry after interruption.
"""

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "v1150.1"
RUNTIME_LAYOUT_VERSION = 1
_LAYOUT_MARKER = ".eidolon_runtime_layout.json"
_TRANSIENT_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv",
    "cache", "caches", "tmp", "temp",
}
_TRANSIENT_SUFFIXES = {".pyc", ".pyo", ".tmp", ".lock"}


class RuntimeDataMigrationError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _resolved(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _is_transient(relative: Path) -> bool:
    return any(part.lower() in _TRANSIENT_DIRS for part in relative.parts) or relative.suffix.lower() in _TRANSIENT_SUFFIXES


def _inventory(root: Path, *, include_marker: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return {"file_count": 0, "byte_count": 0, "files": rows, "digest": _digest(rows), "symlink_count": 0}
    symlink_count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink():
            symlink_count += 1
            continue
        if not path.is_file() or _is_transient(relative):
            continue
        rel = relative.as_posix()
        if not include_marker and rel == _LAYOUT_MARKER:
            continue
        data = path.read_bytes()
        rows.append({"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {
        "file_count": len(rows),
        "byte_count": sum(row["size"] for row in rows),
        "files": rows,
        "digest": _digest(rows),
        "symlink_count": symlink_count,
    }


def _layout_version(root: Path) -> tuple[int, str]:
    marker = root / _LAYOUT_MARKER
    if not marker.is_file():
        return 1, "implicit_legacy_layout"
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        version = int(payload.get("layout_version") or 0)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 0, "invalid_layout_marker"
    return version, "declared_layout"


def _journal_path(target: Path) -> Path:
    return target.parent / f".{target.name}.eidolon-runtime-migration.json"


def _stage_path(target: Path) -> Path:
    return target.parent / f".{target.name}.eidolon-runtime-migration-stage"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _read_journal(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "unreadable_journal"}
    return payload if isinstance(payload, dict) else {"state": "invalid_journal"}


def _copy_inventory(source: Path, stage: Path, inventory: dict[str, Any]) -> None:
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=False)
    for row in inventory["files"]:
        relative = Path(row["path"])
        src = source / relative
        dst = stage / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _write_layout_marker(root: Path, source_digest: str) -> None:
    _write_json_atomic(root / _LAYOUT_MARKER, {
        "contract_version": CONTRACT_VERSION,
        "layout_version": RUNTIME_LAYOUT_VERSION,
        "migrated_at": _now(),
        "source_inventory_digest": source_digest,
    })


def preview_runtime_data_migration(
    legacy_runtime_root: str | Path,
    external_runtime_root: str | Path,
    *,
    include_paths: bool = False,
) -> dict[str, Any]:
    source = _resolved(legacy_runtime_root)
    target = _resolved(external_runtime_root)
    source_inventory = _inventory(source)
    target_inventory = _inventory(target)
    source_layout_version, layout_origin = _layout_version(source)
    journal = _read_journal(_journal_path(target))
    journal_state = str(journal.get("state") or "")
    journal_source_digest = str(journal.get("source_inventory_digest") or "")
    journal_matches_source = bool(journal_source_digest and journal_source_digest == source_inventory["digest"])
    target_matches_source = bool(
        target_inventory["file_count"]
        and target_inventory["file_count"] == source_inventory["file_count"]
        and target_inventory["digest"] == source_inventory["digest"]
    )
    same_location = source == target
    compatible = source_layout_version == RUNTIME_LAYOUT_VERSION
    status = "ready"
    if same_location:
        status = "same_runtime_location"
    elif source_inventory["symlink_count"]:
        status = "legacy_runtime_contains_symlinks"
    elif not compatible:
        status = "incompatible_runtime_layout"
    elif source_inventory["file_count"] == 0:
        status = "no_legacy_runtime_data"
    elif target_matches_source and journal_matches_source and journal_state == "complete":
        status = "migration_already_complete"
    elif target_matches_source and journal_matches_source and journal_state in {"copying", "verified", "failed"}:
        status = "interrupted_migration_finalization_detected"
    elif target_inventory["file_count"]:
        status = "external_runtime_already_populated"
    elif journal_state and journal_state != "complete":
        status = "interrupted_migration_detected"
    result: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "ok": status in {
            "ready", "no_legacy_runtime_data", "same_runtime_location",
            "interrupted_migration_detected", "interrupted_migration_finalization_detected",
            "migration_already_complete",
        },
        "migration_needed": status in {
            "ready", "interrupted_migration_detected", "interrupted_migration_finalization_detected",
        },
        "legacy_file_count": source_inventory["file_count"],
        "legacy_byte_count": source_inventory["byte_count"],
        "legacy_inventory_digest": source_inventory["digest"],
        "legacy_symlink_count": source_inventory["symlink_count"],
        "external_file_count": target_inventory["file_count"],
        "external_inventory_digest": target_inventory["digest"],
        "source_layout_version": source_layout_version,
        "supported_layout_version": RUNTIME_LAYOUT_VERSION,
        "layout_origin": layout_origin,
        "interrupted_migration_detected": status in {
            "interrupted_migration_detected", "interrupted_migration_finalization_detected",
        },
        "interrupted_migration_finalization_detected": status == "interrupted_migration_finalization_detected",
        "journal_state": journal_state or "none",
        "journal_matches_source": journal_matches_source,
        "external_runtime_matches_legacy": target_matches_source,
        "copy_only": True,
        "legacy_source_deleted": False,
        "legacy_source_modified": False,
        "external_runtime_overwritten": False,
        "provider_contacted": False,
        "models_changed": False,
        "private_payload_returned": False,
        "private_paths_included": bool(include_paths),
        "content_free": not bool(include_paths),
    }
    if include_paths:
        result.update({
            "legacy_runtime_root": str(source),
            "external_runtime_root": str(target),
            "journal_path": str(_journal_path(target)),
            "stage_path": str(_stage_path(target)),
        })
    result["structural_digest"] = _digest({key: value for key, value in result.items() if key not in {"structural_digest", "legacy_runtime_root", "external_runtime_root", "journal_path", "stage_path"}})
    return result


def migrate_runtime_data(
    legacy_runtime_root: str | Path,
    external_runtime_root: str | Path,
    *,
    operator_confirmed: bool,
    automatic: bool = False,
    include_paths: bool = False,
) -> dict[str, Any]:
    source = _resolved(legacy_runtime_root)
    target = _resolved(external_runtime_root)
    preview = preview_runtime_data_migration(source, target, include_paths=include_paths)
    source_before = _inventory(source)
    if operator_confirmed is not True:
        return {
            **preview,
            "ok": False,
            "status": "operator_confirmation_required",
            "operator_confirmed": False,
            "automatic": bool(automatic),
            "migration_performed": False,
            "recovered_interrupted_migration": False,
        }
    if preview["status"] in {"no_legacy_runtime_data", "same_runtime_location", "migration_already_complete"}:
        return {
            **preview,
            "operator_confirmed": True,
            "automatic": bool(automatic),
            "migration_performed": False,
            "recovered_interrupted_migration": False,
        }
    if preview["status"] not in {
        "ready", "interrupted_migration_detected", "interrupted_migration_finalization_detected",
    }:
        return {
            **preview,
            "ok": False,
            "operator_confirmed": True,
            "automatic": bool(automatic),
            "migration_performed": False,
            "recovered_interrupted_migration": False,
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    journal_path = _journal_path(target)
    stage = _stage_path(target)
    prior_journal = _read_journal(journal_path)
    recovered = preview["status"] in {
        "interrupted_migration_detected", "interrupted_migration_finalization_detected",
    } or bool(prior_journal)

    if preview["status"] == "interrupted_migration_finalization_detected":
        source_after = _inventory(source)
        installed = _inventory(target)
        if source_after["digest"] != source_before["digest"]:
            return {
                **preview,
                "ok": False,
                "status": "migration_failed_recoverable",
                "operator_confirmed": True,
                "automatic": bool(automatic),
                "migration_performed": False,
                "migration_finalization_performed": False,
                "recovered_interrupted_migration": True,
                "error_type": "RuntimeDataMigrationError",
                "error_summary": "legacy runtime changed before interrupted migration finalization",
                "journal_state": str(prior_journal.get("state") or "unknown"),
                "legacy_source_modified": True,
                "legacy_source_deleted": False,
                "external_runtime_overwritten": False,
            }
        if installed["digest"] != source_before["digest"] or installed["file_count"] != source_before["file_count"]:
            return {
                **preview,
                "ok": False,
                "status": "migration_failed_recoverable",
                "operator_confirmed": True,
                "automatic": bool(automatic),
                "migration_performed": False,
                "migration_finalization_performed": False,
                "recovered_interrupted_migration": True,
                "error_type": "RuntimeDataMigrationError",
                "error_summary": "installed runtime no longer matches interrupted migration source",
                "journal_state": str(prior_journal.get("state") or "unknown"),
                "legacy_source_modified": False,
                "legacy_source_deleted": False,
                "external_runtime_overwritten": False,
            }
        _write_layout_marker(target, source_before["digest"])
        completed_journal = dict(prior_journal)
        completed_journal.update({
            "contract_version": CONTRACT_VERSION,
            "state": "complete",
            "completed_at": _now(),
            "updated_at": _now(),
            "source_inventory_digest": source_before["digest"],
            "source_file_count": source_before["file_count"],
            "installed_inventory_digest": installed["digest"],
            "target_name": target.name,
            "copy_only": True,
        })
        _write_json_atomic(journal_path, completed_journal)
        result = {
            **preview,
            "ok": True,
            "status": "migration_recovery_complete",
            "operator_confirmed": True,
            "automatic": bool(automatic),
            "migration_performed": False,
            "migration_finalization_performed": True,
            "recovered_interrupted_migration": True,
            "installed_file_count": installed["file_count"],
            "installed_byte_count": installed["byte_count"],
            "installed_inventory_digest": installed["digest"],
            "legacy_source_modified": False,
            "legacy_source_deleted": False,
            "external_runtime_overwritten": False,
            "journal_state": "complete",
        }
        result["structural_digest"] = _digest({key: value for key, value in result.items() if key not in {"structural_digest", "legacy_runtime_root", "external_runtime_root", "journal_path", "stage_path"}})
        return result
    migration_id = _digest({"source": source_before["digest"], "target_name": target.name})[:24]
    journal = {
        "contract_version": CONTRACT_VERSION,
        "migration_id": migration_id,
        "state": "copying",
        "started_at": str(prior_journal.get("started_at") or _now()),
        "updated_at": _now(),
        "source_inventory_digest": source_before["digest"],
        "source_file_count": source_before["file_count"],
        "target_name": target.name,
        "copy_only": True,
    }
    _write_json_atomic(journal_path, journal)
    try:
        _copy_inventory(source, stage, source_before)
        staged = _inventory(stage)
        if staged["digest"] != source_before["digest"] or staged["file_count"] != source_before["file_count"]:
            raise RuntimeDataMigrationError("staged runtime verification failed")
        journal.update({"state": "verified", "updated_at": _now(), "staged_inventory_digest": staged["digest"]})
        _write_json_atomic(journal_path, journal)
        if target.exists():
            if any(target.iterdir()):
                raise RuntimeDataMigrationError("external runtime became populated during migration")
            target.rmdir()
        os.replace(stage, target)
        _write_layout_marker(target, source_before["digest"])
        installed = _inventory(target)
        if installed["digest"] != source_before["digest"]:
            raise RuntimeDataMigrationError("installed runtime verification failed")
        source_after = _inventory(source)
        if source_after["digest"] != source_before["digest"]:
            raise RuntimeDataMigrationError("legacy runtime changed during migration")
        journal.update({
            "state": "complete",
            "completed_at": _now(),
            "updated_at": _now(),
            "installed_inventory_digest": installed["digest"],
        })
        _write_json_atomic(journal_path, journal)
        result = {
            **preview,
            "ok": True,
            "status": "migration_complete",
            "operator_confirmed": True,
            "automatic": bool(automatic),
            "migration_performed": True,
            "recovered_interrupted_migration": recovered,
            "installed_file_count": installed["file_count"],
            "installed_byte_count": installed["byte_count"],
            "installed_inventory_digest": installed["digest"],
            "legacy_source_modified": False,
            "legacy_source_deleted": False,
            "external_runtime_overwritten": False,
            "journal_state": "complete",
        }
        result["structural_digest"] = _digest({key: value for key, value in result.items() if key not in {"structural_digest", "legacy_runtime_root", "external_runtime_root", "journal_path", "stage_path"}})
        return result
    except Exception as error:
        journal.update({"state": "failed", "updated_at": _now(), "error_type": type(error).__name__, "error_summary": str(error)[:240]})
        _write_json_atomic(journal_path, journal)
        return {
            **preview,
            "ok": False,
            "status": "migration_failed_recoverable",
            "operator_confirmed": True,
            "automatic": bool(automatic),
            "migration_performed": False,
            "recovered_interrupted_migration": recovered,
            "error_type": type(error).__name__,
            "error_summary": str(error)[:240],
            "journal_state": "failed",
            "legacy_source_modified": _inventory(source)["digest"] != source_before["digest"],
            "legacy_source_deleted": False,
            "external_runtime_overwritten": False,
        }
