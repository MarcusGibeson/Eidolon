from __future__ import annotations

"""Private, bounded recovery for interrupted metadata encoding migrations.

Recovery records exist only while an operation may need reconciliation. They
contain no JSON payloads, are stored beneath private runtime data, and are
removed after the target is proven original, proven canonical, or restored from
a verified backup. This is recovery state, not a migration history ledger.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
import uuid

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from paths import DATA_DIR
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
    from paths import DATA_DIR


_RECOVERY_SCHEMA_VERSION = "1"
_MAX_BACKUPS_PER_TARGET = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _root(data_dir: Path | None = None) -> Path:
    return Path(data_dir or DATA_DIR).expanduser().resolve()


def recovery_state_dir(*, data_dir: Path | None = None) -> Path:
    return _root(data_dir) / "metadata_migration_state"


def _atomic_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _record_path(operation_id: str, *, data_dir: Path | None = None) -> Path:
    token = str(operation_id or "").strip().lower()
    if len(token) != 32 or any(ch not in "0123456789abcdef" for ch in token):
        raise ValueError("Invalid metadata migration recovery operation identifier.")
    return recovery_state_dir(data_dir=data_dir) / f"{token}.json"


def begin_migration_recovery(
    target: Path,
    *,
    original_sha256: str,
    canonical_sha256: str,
    expected_root_type: str,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    operation_id = uuid.uuid4().hex
    record = {
        "type": "metadata_migration_recovery",
        "schema_version": _RECOVERY_SCHEMA_VERSION,
        "operation_id": operation_id,
        "target_path": str(target.expanduser().resolve()),
        "target_digest": hashlib.sha256(str(target.expanduser().resolve()).encode("utf-8")).hexdigest(),
        "backup_path": "",
        "original_sha256": str(original_sha256),
        "canonical_sha256": str(canonical_sha256),
        "expected_root_type": str(expected_root_type),
        "stage": "prepared",
        "created_at": _now(),
        "updated_at": _now(),
        "content_free": True,
        "local_private": True,
    }
    _atomic_private_json(_record_path(operation_id, data_dir=data_dir), record)
    return record


def update_migration_recovery(
    record: dict[str, Any],
    stage: str,
    *,
    backup_path: Path | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    value = dict(record)
    value["stage"] = str(stage)
    value["updated_at"] = _now()
    if backup_path is not None:
        value["backup_path"] = str(backup_path.expanduser().resolve())
    _atomic_private_json(_record_path(str(value["operation_id"]), data_dir=data_dir), value)
    record.clear(); record.update(value)
    return record


def finish_migration_recovery(record: dict[str, Any], *, data_dir: Path | None = None) -> None:
    try:
        _record_path(str(record.get("operation_id") or ""), data_dir=data_dir).unlink(missing_ok=True)
    except OSError:
        pass


def _valid_root(value: Any, expected: str) -> bool:
    if expected == "dict":
        return isinstance(value, dict)
    if expected == "list":
        return isinstance(value, list)
    return True


def _canonical_target_valid(path: Path, record: dict[str, Any]) -> bool:
    try:
        raw = path.read_bytes()
        if _digest_bytes(raw) != str(record.get("canonical_sha256") or ""):
            return False
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return not raw.startswith(b"\xef\xbb\xbf") and _valid_root(value, str(record.get("expected_root_type") or "any"))


def _backup_verified(record: dict[str, Any]) -> bool:
    backup = Path(str(record.get("backup_path") or ""))
    try:
        return backup.is_file() and _digest_bytes(backup.read_bytes()) == str(record.get("original_sha256") or "")
    except OSError:
        return False


def restore_verified_backup(record: dict[str, Any]) -> bool:
    if not _backup_verified(record):
        return False
    target = Path(str(record.get("target_path") or ""))
    backup = Path(str(record.get("backup_path") or ""))
    temporary = target.with_name(f".{target.name}.recovery-{os.getpid()}-{uuid.uuid4().hex}.tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temporary.open("xb") as handle:
            handle.write(backup.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return _digest_bytes(target.read_bytes()) == str(record.get("original_sha256") or "")
    except OSError:
        return False
    finally:
        temporary.unlink(missing_ok=True)


def prune_target_backups(backup_dir: Path, target_name: str, *, keep: int = _MAX_BACKUPS_PER_TARGET) -> None:
    try:
        rows = sorted(
            backup_dir.glob(f"{target_name}.pre-utf8-migration-*.bak"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return
    for path in rows[max(1, int(keep)):]:
        try:
            path.unlink()
        except OSError:
            pass


def _load_record(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("type") != "metadata_migration_recovery":
        return None
    return value


def metadata_migration_recovery_status(*, data_dir: Path | None = None) -> dict[str, Any]:
    directory = recovery_state_dir(data_dir=data_dir)
    stages: dict[str, int] = {}
    pending = 0
    invalid = 0
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        record = _load_record(path)
        if record is None:
            invalid += 1
            continue
        stage = str(record.get("stage") or "unknown")
        stages[stage] = stages.get(stage, 0) + 1
        pending += 1
    return {
        "ok": True,
        "status": "recovery_pending" if pending or invalid else "idle",
        "pending_operation_count": pending,
        "invalid_private_record_count": invalid,
        "stages": stages,
        "operator_confirmation_required_for_recovery": bool(pending or invalid),
        "payload_returned": False,
        "absolute_path_returned": False,
        "backup_path_returned": False,
        "content_free": True,
        "source_mutated": False,
    }


def recover_pending_metadata_migrations(
    *,
    operator_confirmed: bool,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    status = metadata_migration_recovery_status(data_dir=data_dir)
    operator_confirmed = operator_confirmed is True
    if not operator_confirmed:
        return {**status, "ok": False, "status": "confirmation_required", "recovered": 0, "uncertain": 0}
    directory = recovery_state_dir(data_dir=data_dir)
    results: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        record = _load_record(path)
        if record is None:
            results.append({"status": "invalid_private_record", "recovered": False, "uncertain_result": True})
            continue
        root = _root(data_dir)
        target = Path(str(record.get("target_path") or "")).expanduser().resolve()
        backup = Path(str(record.get("backup_path") or "")).expanduser().resolve() if str(record.get("backup_path") or "") else None
        public = {"status": "unknown", "recovered": False, "uncertain_result": False, "target_digest": str(record.get("target_digest") or "")}
        try:
            target.relative_to(root)
            if backup is not None:
                backup.relative_to(root / "metadata_migration_backups")
        except ValueError:
            public.update(status="unsafe_private_record", uncertain_result=True)
            results.append(public)
            continue
        try:
            with metadata_mutation_lock(target, timeout_seconds=0.5):
                try:
                    current_digest = _digest_bytes(target.read_bytes()) if target.is_file() else ""
                except OSError:
                    current_digest = ""
                original = str(record.get("original_sha256") or "")
                canonical = str(record.get("canonical_sha256") or "")
                if current_digest == original:
                    public.update(status="original_preserved", recovered=True)
                    finish_migration_recovery(record, data_dir=data_dir)
                elif current_digest == canonical and _canonical_target_valid(target, record):
                    public.update(status="canonical_verified", recovered=True)
                    finish_migration_recovery(record, data_dir=data_dir)
                elif restore_verified_backup(record):
                    public.update(status="original_restored", recovered=True)
                    finish_migration_recovery(record, data_dir=data_dir)
                else:
                    public.update(status="uncertain_requires_operator", uncertain_result=True)
        except MetadataMutationBusy:
            public.update(status="mutation_busy", safe_retry=True)
        results.append(public)
    return {
        "ok": not any(row.get("uncertain_result") for row in results),
        "status": "recovered" if results and not any(row.get("uncertain_result") for row in results) else ("idle" if not results else "recovery_incomplete"),
        "recovered": sum(1 for row in results if row.get("recovered")),
        "uncertain": sum(1 for row in results if row.get("uncertain_result")),
        "busy": sum(1 for row in results if row.get("status") == "mutation_busy"),
        "results": results,
        "payload_returned": False,
        "absolute_path_returned": False,
        "backup_path_returned": False,
        "content_free": True,
    }
