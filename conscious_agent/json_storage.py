from __future__ import annotations

"""BOM-aware, atomic JSON storage helpers for mutable Eidolon metadata.

Reads accept ordinary UTF-8 and UTF-8 files with a byte-order mark. Writes are
always canonical UTF-8 without a BOM and use a unique same-directory temporary
file followed by ``os.replace``. Migration is previewed, digest-bound, explicit,
and backup-protected. The compatibility migration helper remains available for
older callers, but new code should use ``preview_json_migration`` followed by
``apply_json_migration``.
"""

from copy import deepcopy
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Type
import uuid

try:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
except ImportError:
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock

UTF8_BOM = b"\xef\xbb\xbf"


class JsonStorageError(ValueError):
    """Raised when a requested JSON write violates the declared store shape."""


def write_text_atomic(path: str | Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Atomically replace a durable text file using a same-directory temp file.

    This is the text analogue of ``write_json_atomic`` for authoritative marker,
    manifest, patch-input, and other non-JSON state. It never writes through the
    target path directly, so interruption cannot leave a partially truncated file.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    data = str(text).encode(encoding)
    try:
        with temp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        try:
            if temp.exists():
                temp.unlink()
        except OSError:
            pass
    return target


def append_text_atomic(path: str | Path, suffix: str, *, encoding: str = "utf-8", errors: str = "strict") -> Path:
    """Serialize read-modify-write append under the existing metadata lock."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(target, timeout_seconds=5):
        prior = target.read_text(encoding=encoding, errors=errors) if target.exists() else ""
        return write_text_atomic(target, prior + str(suffix), encoding=encoding)


class AtomicJsonWriteError(OSError):
    """Classified atomic-write failure without exposing a private target path."""

    def __init__(
        self,
        status: str,
        *,
        safe_retry: bool,
        uncertain_result: bool,
        original_restored: bool = False,
    ) -> None:
        super().__init__(status.replace("_", " "))
        self.status = status
        self.safe_retry = bool(safe_retry)
        self.uncertain_result = bool(uncertain_result)
        self.original_restored = bool(original_restored)
        self.content_free = True


def _default(value: Any) -> Any:
    return deepcopy(value)


def _expected_type_name(expected_type: Type[Any] | tuple[Type[Any], ...] | None) -> str:
    if expected_type is None:
        return "any"
    if isinstance(expected_type, tuple):
        return "|".join(sorted(item.__name__ for item in expected_type))
    return expected_type.__name__


def _root_type_name(value: Any) -> str:
    if value is None:
        return "null"
    return type(value).__name__




def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _file_digest_after_replace(path: Path, *, attempts: int = 8, delay_seconds: float = 0.02) -> str:
    """Bound transient Windows sharing delays before classifying replacement state."""
    for attempt in range(max(1, int(attempts))):
        value = _file_digest(path)
        if value:
            return value
        if attempt + 1 < attempts:
            time.sleep(max(0.0, float(delay_seconds)) * (attempt + 1))
    return ""


def _replace_error_safe_to_retry(error: OSError) -> bool:
    winerror = getattr(error, "winerror", None)
    return bool(
        isinstance(error, PermissionError)
        or winerror in {5, 32, 33}
        or getattr(error, "errno", None) in {errno.EACCES, errno.EBUSY}
    )


def _restore_prior_target(target: Path, original: bytes | None) -> bool:
    """Best-effort restore while the caller still owns the mutation lock."""
    if original is None:
        try:
            target.unlink(missing_ok=True)
            return not target.exists()
        except OSError:
            return False
    restoration = target.with_name(
        f".{target.name}.restore-{os.getpid()}-{uuid.uuid4().hex}.tmp"
    )
    try:
        with restoration.open("xb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(restoration, target)
        return _file_digest(target) == hashlib.sha256(original).hexdigest()
    except OSError:
        return False
    finally:
        try:
            restoration.unlink(missing_ok=True)
        except OSError:
            pass


def canonical_json_bytes(
    value: Any,
    *,
    indent: int = 2,
    sort_keys: bool = False,
    default: Any = None,
) -> bytes:
    text = json.dumps(
        value,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=False,
        allow_nan=False,
        default=default,
    )
    return (text + "\n").encode("utf-8")


def read_json_bytes(path: str | Path) -> tuple[bytes, bool]:
    raw = Path(path).read_bytes()
    return raw, raw.startswith(UTF8_BOM)


def load_json_file(
    path: str | Path,
    default: Any,
    *,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
) -> Any:
    """Return parsed JSON, accepting UTF-8 BOM files and preserving defaults.

    Failed reads never rewrite or remove the source file. The returned default is
    deep-copied so callers cannot accidentally mutate a shared template.
    """
    target = Path(path)
    try:
        if not target.is_file() or target.stat().st_size == 0:
            return _default(default)
        raw = target.read_bytes()
        value = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _default(default)
    if expected_type is not None and not isinstance(value, expected_type):
        return _default(default)
    return value


def write_json_atomic(
    path: str | Path,
    value: Any,
    *,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
    indent: int = 2,
    sort_keys: bool = False,
    default: Any = None,
    replace_retries: int = 5,
    retry_delay_seconds: float = 0.02,
    coordination_timeout_seconds: float = 5.0,
    coordinate: bool = True,
) -> None:
    """Write canonical UTF-8 JSON atomically without sharing a temp filename.

    Serialization and root-shape validation happen before a temporary file is
    created. A bounded ``PermissionError`` retry accommodates Windows scanners
    and short-lived file sharing without converting an unavailable target into a
    silent data loss event.
    """
    if expected_type is not None and not isinstance(value, expected_type):
        raise JsonStorageError(
            f"JSON root must be {_expected_type_name(expected_type)}, got {_root_type_name(value)}."
        )
    payload = canonical_json_bytes(value, indent=indent, sort_keys=sort_keys, default=default)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    def _commit() -> None:
        temporary = target.with_name(
            f".{target.name}.transaction-{os.getpid()}-{uuid.uuid4().hex}.tmp"
        )
        payload_digest = hashlib.sha256(payload).hexdigest()
        try:
            original = target.read_bytes() if target.is_file() else None
        except OSError as error:
            raise AtomicJsonWriteError(
                "original_read_failed", safe_retry=False, uncertain_result=False
            ) from error
        original_digest = hashlib.sha256(original).hexdigest() if original is not None else ""
        try:
            with temporary.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            attempts = max(1, int(replace_retries))
            replaced = False
            for attempt in range(attempts):
                try:
                    os.replace(temporary, target)
                except OSError as error:
                    current_digest = _file_digest_after_replace(target)
                    if current_digest == payload_digest:
                        # Some Windows filters can report an error after replacement became visible.
                        replaced = True
                        break
                    original_intact = (
                        current_digest == original_digest
                        if original is not None
                        else not target.exists()
                    )
                    retryable = _replace_error_safe_to_retry(error)
                    if retryable and original_intact and temporary.exists() and attempt + 1 < attempts:
                        time.sleep(max(0.0, float(retry_delay_seconds)) * (attempt + 1))
                        continue
                    if original_intact:
                        raise AtomicJsonWriteError(
                            "replace_blocked",
                            safe_retry=retryable,
                            uncertain_result=False,
                        ) from error
                    restored = _restore_prior_target(target, original)
                    raise AtomicJsonWriteError(
                        "replacement_result_restored" if restored else "replacement_result_uncertain",
                        safe_retry=restored,
                        uncertain_result=not restored,
                        original_restored=restored,
                    ) from error
                current_digest = _file_digest_after_replace(target)
                if current_digest == payload_digest:
                    replaced = True
                    break
                restored = _restore_prior_target(target, original)
                raise AtomicJsonWriteError(
                    "replacement_verification_failed_restored" if restored else "replacement_verification_uncertain",
                    safe_retry=restored,
                    uncertain_result=not restored,
                    original_restored=restored,
                )
            if not replaced:
                raise AtomicJsonWriteError(
                    "replace_not_completed", safe_retry=True, uncertain_result=False
                )
            try:
                directory_descriptor = os.open(target.parent, os.O_RDONLY)
            except (AttributeError, OSError):
                directory_descriptor = None
            if directory_descriptor is not None:
                try:
                    os.fsync(directory_descriptor)
                except OSError:
                    pass
                finally:
                    os.close(directory_descriptor)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    if coordinate:
        with metadata_mutation_lock(target, timeout_seconds=coordination_timeout_seconds):
            _commit()
    else:
        _commit()


def inspect_json_encoding(
    path: str | Path,
    *,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
) -> dict[str, Any]:
    target = Path(path)
    try:
        raw, had_bom = read_json_bytes(target)
    except OSError:
        return {
            "exists": False,
            "valid_json": False,
            "root_shape_valid": False,
            "utf8_bom_present": False,
            "detected_encoding": "missing",
            "root_type": "missing",
            "expected_root_type": _expected_type_name(expected_type),
            "size_bytes": 0,
            "content_sha256": "",
            "canonical_sha256": "",
        }
    valid = False
    value: Any = None
    try:
        value = json.loads(raw.decode("utf-8-sig"))
        valid = True
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    shape_valid = bool(valid and (expected_type is None or isinstance(value, expected_type)))
    canonical_sha = ""
    if shape_valid:
        try:
            canonical_sha = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
        except (TypeError, ValueError):
            shape_valid = False
    return {
        "exists": True,
        "valid_json": valid,
        "root_shape_valid": shape_valid,
        "utf8_bom_present": had_bom,
        "detected_encoding": "utf-8-bom" if had_bom else "utf-8",
        "root_type": _root_type_name(value) if valid else "invalid",
        "expected_root_type": _expected_type_name(expected_type),
        "size_bytes": len(raw),
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_sha256": canonical_sha,
    }


def _migration_token(
    *,
    target: Path,
    content_sha256: str,
    detected_encoding: str,
    root_type: str,
    expected_root_type: str,
    canonical_sha256: str,
) -> str:
    material = "\n".join(
        (
            str(target.resolve()),
            content_sha256,
            detected_encoding,
            root_type,
            expected_root_type,
            canonical_sha256,
        )
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def preview_json_migration(
    path: str | Path,
    *,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
) -> dict[str, Any]:
    """Build a content-free, non-mutating migration preview."""
    target = Path(path)
    state = inspect_json_encoding(target, expected_type=expected_type)
    result: dict[str, Any] = {
        "ok": False,
        "status": "missing",
        "operator_confirmation_required": True,
        "path_exists": state["exists"],
        "valid_json": state["valid_json"],
        "root_shape_valid": state["root_shape_valid"],
        "detected_encoding": state["detected_encoding"],
        "utf8_bom_present": state["utf8_bom_present"],
        "root_type": state["root_type"],
        "expected_root_type": state["expected_root_type"],
        "size_bytes": state["size_bytes"],
        "content_sha256": state["content_sha256"],
        "canonical_sha256": state["canonical_sha256"],
        "preview_token": "",
        "payload_returned": False,
        "source_mutated": False,
    }
    if not state["exists"]:
        return result
    if not state["valid_json"]:
        result["status"] = "invalid_json"
        return result
    if not state["root_shape_valid"]:
        result["status"] = "invalid_root_shape"
        return result
    result["preview_token"] = _migration_token(
        target=target,
        content_sha256=state["content_sha256"],
        detected_encoding=state["detected_encoding"],
        root_type=state["root_type"],
        expected_root_type=state["expected_root_type"],
        canonical_sha256=state["canonical_sha256"],
    )
    result["ok"] = True
    result["status"] = "migration_available" if state["utf8_bom_present"] else "already_canonical"
    return result


def _apply_json_migration_locked(
    path: str | Path,
    *,
    preview_token: str,
    operator_confirmed: bool,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
    backup_dir: str | Path,
    recovery_dir: str | Path | None = None,
    fault_hook: Any = None,
) -> dict[str, Any]:
    """Apply one exact preview with private interruption-recovery state."""
    try:
        from metadata_migration_recovery import begin_migration_recovery, finish_migration_recovery, prune_target_backups, restore_verified_backup, update_migration_recovery
    except ImportError:
        from metadata_migration_recovery import (
            begin_migration_recovery, finish_migration_recovery, prune_target_backups,
            restore_verified_backup, update_migration_recovery,
        )
    target = Path(path)
    preview = preview_json_migration(target, expected_type=expected_type)
    result: dict[str, Any] = {
        **preview, "ok": False, "operator_confirmed": bool(operator_confirmed),
        "backup_created": False, "backup_verified": False, "backup_reference": "",
        "source_mutated": False, "utf8_bom_present_before": preview.get("utf8_bom_present", False),
        "utf8_bom_present_after": preview.get("utf8_bom_present", False),
        "content_sha256_before": preview.get("content_sha256", ""),
        "content_sha256_after": preview.get("content_sha256", ""),
        "recovery_required": False, "safe_retry": False, "uncertain_result": False,
    }
    if not operator_confirmed:
        result["status"] = "confirmation_required"; return result
    if not preview.get("ok"):
        return result
    supplied = str(preview_token or "").strip()
    if not supplied or supplied != preview.get("preview_token"):
        result["status"] = "stale_or_mismatched_preview"; return result
    if preview.get("status") == "already_canonical":
        result.update(ok=True, status="already_canonical"); return result

    value = load_json_file(target, None, expected_type=expected_type)
    if value is None:
        result["status"] = "invalid_json_or_shape"; return result
    backups = Path(backup_dir); backups.mkdir(parents=True, exist_ok=True)
    data_root = Path(recovery_dir).parent if recovery_dir is not None else backups.parent.parent
    original = target.read_bytes()
    record = begin_migration_recovery(
        target, original_sha256=preview["content_sha256"], canonical_sha256=preview["canonical_sha256"],
        expected_root_type=preview["expected_root_type"], data_dir=data_root,
    )
    if fault_hook is not None:
        fault_hook("before_backup")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backups / f"{target.name}.pre-utf8-migration-{stamp}-{uuid.uuid4().hex[:12]}.bak"
    try:
        with backup.open("xb") as handle:
            handle.write(original); handle.flush(); os.fsync(handle.fileno())
    except OSError:
        finish_migration_recovery(record, data_dir=data_root)
        result["status"] = "backup_failed"; return result
    result["backup_created"] = True; result["backup_reference"] = backup.name
    result["backup_verified"] = hashlib.sha256(backup.read_bytes()).hexdigest() == preview["content_sha256"]
    update_migration_recovery(record, "backup_created", backup_path=backup, data_dir=data_root)
    if not result["backup_verified"]:
        result["status"] = "backup_verification_failed"; result["recovery_required"] = True; return result
    if fault_hook is not None:
        fault_hook("after_backup")

    current = preview_json_migration(target, expected_type=expected_type)
    if current.get("preview_token") != supplied:
        finish_migration_recovery(record, data_dir=data_root)
        result["status"] = "stale_after_backup"; return result
    update_migration_recovery(record, "replacement_started", data_dir=data_root)
    if fault_hook is not None:
        fault_hook("before_replace")
    try:
        write_json_atomic(target, value, expected_type=expected_type, coordinate=False)
    except Exception:
        restored = restore_verified_backup(record)
        if restored:
            finish_migration_recovery(record, data_dir=data_root)
        result["status"] = "write_failed"
        result["recovery_required"] = not restored
        result["uncertain_result"] = not restored
        return result
    update_migration_recovery(record, "replacement_written", data_dir=data_root)
    if fault_hook is not None:
        fault_hook("after_replace_before_verify")

    after = inspect_json_encoding(target, expected_type=expected_type)
    migrated = bool(after["valid_json"] and after["root_shape_valid"] and not after["utf8_bom_present"] and after["content_sha256"] == preview["canonical_sha256"])
    if not migrated:
        restored = restore_verified_backup(record)
        if restored:
            finish_migration_recovery(record, data_dir=data_root)
        result["status"] = "verification_failed"
        result["recovery_required"] = not restored
        result["uncertain_result"] = not restored
        return result
    update_migration_recovery(record, "verified", data_dir=data_root)
    finish_migration_recovery(record, data_dir=data_root)
    prune_target_backups(backups, target.name)
    result.update(ok=True, status="migrated", source_mutated=True, utf8_bom_present_after=False, content_sha256_after=after["content_sha256"])
    return result


def apply_json_migration(
    path: str | Path,
    *,
    preview_token: str,
    operator_confirmed: bool,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
    backup_dir: str | Path,
    coordination_timeout_seconds: float = 5.0,
    recovery_dir: str | Path | None = None,
    fault_hook: Any = None,
) -> dict[str, Any]:
    target = Path(path)
    operator_confirmed = operator_confirmed is True
    try:
        with metadata_mutation_lock(target, timeout_seconds=coordination_timeout_seconds):
            return _apply_json_migration_locked(
                target,
                preview_token=preview_token,
                operator_confirmed=operator_confirmed,
                expected_type=expected_type,
                backup_dir=backup_dir,
                recovery_dir=recovery_dir,
                fault_hook=fault_hook,
            )
    except MetadataMutationBusy:
        preview = preview_json_migration(target, expected_type=expected_type)
        return {
            **preview,
            "ok": False,
            "status": "mutation_busy",
            "operator_confirmed": bool(operator_confirmed),
            "backup_created": False,
            "backup_verified": False,
            "backup_reference": "",
            "source_mutated": False,
            "safe_retry": True,
            "uncertain_result": False,
        }


def migrate_json_file_encoding(
    path: str | Path,
    *,
    operator_confirmed: bool,
    expected_type: Type[Any] | tuple[Type[Any], ...] | None = None,
    create_backup: bool = True,
) -> dict[str, Any]:
    """Compatibility migration wrapper retained for v1091 callers.

    New migration surfaces should use ``preview_json_migration`` and
    ``apply_json_migration`` so confirmation is bound to the exact file digest.
    """
    target = Path(path)
    operator_confirmed = operator_confirmed is True
    before = inspect_json_encoding(target, expected_type=expected_type)
    result: dict[str, Any] = {
        "ok": False,
        "status": "confirmation_required",
        "operator_confirmation_required": True,
        "operator_confirmed": bool(operator_confirmed),
        "path_exists": before["exists"],
        "valid_json": before["valid_json"],
        "utf8_bom_present_before": before["utf8_bom_present"],
        "utf8_bom_present_after": before["utf8_bom_present"],
        "backup_created": False,
        "payload_returned": False,
        "content_sha256_before": before["content_sha256"],
        "content_sha256_after": before["content_sha256"],
    }
    if not operator_confirmed:
        return result
    if not before["exists"]:
        result["status"] = "missing"
        return result
    value = load_json_file(target, None, expected_type=expected_type)
    if value is None:
        result["status"] = "invalid_json_or_shape"
        return result
    if not before["utf8_bom_present"]:
        result.update(ok=True, status="already_canonical")
        return result

    backup: Path | None = None
    if create_backup:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(
            f".{target.name}.pre-utf8-migration-{stamp}-{uuid.uuid4().hex[:8]}.bak"
        )
        with backup.open("xb") as handle:
            handle.write(target.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        result["backup_created"] = True
    try:
        write_json_atomic(target, value, expected_type=expected_type)
    except Exception:
        if backup is not None and backup.exists():
            os.replace(backup, target)
            result["backup_created"] = False
        result["status"] = "write_failed"
        return result

    after = inspect_json_encoding(target, expected_type=expected_type)
    result.update(
        ok=bool(after["valid_json"] and after["root_shape_valid"] and not after["utf8_bom_present"]),
        status=(
            "migrated"
            if after["valid_json"] and after["root_shape_valid"] and not after["utf8_bom_present"]
            else "verification_failed"
        ),
        utf8_bom_present_after=after["utf8_bom_present"],
        content_sha256_after=after["content_sha256"],
    )
    return result
