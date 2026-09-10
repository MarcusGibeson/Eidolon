from __future__ import annotations

"""Cross-process coordination for mutable JSON writes and migrations.

Locks are private, content-free, target-digest keyed, and acquired with O_EXCL so
the same implementation works with Windows spawn and POSIX processes. A valid
owner is never reclaimed merely because it is old; reclamation requires a dead
PID or an abandoned malformed record that remained incomplete beyond a short
grace period.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import threading
import time
from typing import Any, Iterator
import uuid

def _default_data_dir() -> Path:
    override = os.environ.get("EIDOLON_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    from runtime_data_bootstrap import default_runtime_data_dir
    return default_runtime_data_dir()


class MetadataMutationBusy(RuntimeError):
    def __init__(self, message: str = "This metadata file is being updated by another process. Retry after it finishes.") -> None:
        super().__init__(message)
        self.status = "metadata_mutation_busy"
        self.safe_retry = True
        self.uncertain_result = False


_PROCESS_NONCE = uuid.uuid4().hex
_HELD = threading.local()
_DEFAULT_TIMEOUT_SECONDS = 5.0
_INCOMPLETE_GRACE_SECONDS = 2.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _target_digest(path: Path) -> str:
    return hashlib.sha256(str(path.expanduser().resolve()).encode("utf-8")).hexdigest()


def _lock_root() -> Path:
    override = os.environ.get("EIDOLON_METADATA_LOCK_DIR")
    return Path(override).expanduser().resolve() if override else _default_data_dir() / "metadata_mutation_locks"


def metadata_lock_path(path: str | Path) -> Path:
    return _lock_root() / f"{_target_digest(Path(path))}.lock"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: no such process.
                return False
            # Access denied or an unknown status must retain the lock owner.
            return True
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as error:
        if os.name == "nt" and getattr(error, "winerror", None) == 87:
            # Windows reports a PID with no process as ERROR_INVALID_PARAMETER.
            return False
        # On platforms where liveness cannot be proven, fail closed and retain the owner.
        return True
    return True


def _read_owner(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _lock_age(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return 0.0


def _owner_abandoned(path: Path, owner: dict[str, Any] | None) -> bool:
    if not owner:
        return _lock_age(path) >= _INCOMPLETE_GRACE_SECONDS
    try:
        pid = int(owner.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    token = str(owner.get("owner_token") or "")
    target_digest = str(owner.get("target_digest") or "")
    if not pid or len(token) < 16 or len(target_digest) != 64:
        return _lock_age(path) >= _INCOMPLETE_GRACE_SECONDS
    return not _pid_alive(pid)


def _held_targets() -> set[str]:
    value = getattr(_HELD, "targets", None)
    if value is None:
        value = set()
        _HELD.targets = value
    return value


def _write_owner(descriptor: int, *, target_digest: str, owner_token: str) -> None:
    record = {
        "type": "metadata_mutation_owner",
        "schema_version": "1",
        "pid": os.getpid(),
        "process_nonce": _PROCESS_NONCE,
        "owner_token": owner_token,
        "target_digest": target_digest,
        "host_digest": hashlib.sha256(socket.gethostname().encode("utf-8", errors="ignore")).hexdigest(),
        "acquired_at": _utc_now(),
        "content_free": True,
        "local_private": True,
    }
    payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    os.write(descriptor, payload)
    os.fsync(descriptor)


@contextmanager
def metadata_mutation_lock(
    path: str | Path,
    *,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    poll_seconds: float = 0.02,
) -> Iterator[dict[str, Any]]:
    target = Path(path).expanduser().resolve()
    digest = _target_digest(target)
    held = _held_targets()
    if digest in held:
        yield {
            "ok": True,
            "status": "reentrant_owner",
            "target_digest": digest,
            "content_free": True,
            "local_private": True,
        }
        return

    lock_path = metadata_lock_path(target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.01, float(timeout_seconds))
    descriptor: int | None = None
    acquired = False
    owner_token = uuid.uuid4().hex
    reclaimed_dead_owner = False
    while not acquired:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            _write_owner(descriptor, target_digest=digest, owner_token=owner_token)
            # Windows contenders must be able to read the durable owner record.
            # The exclusive lock is represented by the file entry and token, so
            # retaining the write descriptor only creates a sharing violation.
            os.close(descriptor)
            descriptor = None
            acquired = True
        except (FileExistsError, PermissionError):
            if not lock_path.exists():
                if time.monotonic() >= deadline:
                    raise MetadataMutationBusy()
                time.sleep(max(0.001, float(poll_seconds)))
                continue
            owner = _read_owner(lock_path)
            if _owner_abandoned(lock_path, owner):
                try:
                    lock_path.unlink()
                    reclaimed_dead_owner = True
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise MetadataMutationBusy()
            time.sleep(max(0.001, float(poll_seconds)))
        except Exception:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                descriptor = None
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    held.add(digest)
    public = {
        "ok": True,
        "status": "owner_acquired",
        "target_digest": digest,
        "reclaimed_dead_owner": reclaimed_dead_owner,
        "content_free": True,
        "local_private": True,
    }
    try:
        yield public
    finally:
        held.discard(digest)
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for _attempt in range(150):
            if not lock_path.exists():
                break
            current = _read_owner(lock_path)
            owned = bool(current and str(current.get("owner_token") or "") == owner_token)
            if current is not None and not owned:
                break
            if current is None:
                time.sleep(0.02)
                continue
            try:
                lock_path.unlink()
                break
            except OSError:
                time.sleep(0.02)


def metadata_mutation_status(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    lock_path = metadata_lock_path(target)
    owner = _read_owner(lock_path) if lock_path.exists() else None
    active = bool(owner and not _owner_abandoned(lock_path, owner))
    return {
        "ok": True,
        "status": "mutation_active" if active else "idle",
        "target_digest": _target_digest(target),
        "owner_active": active,
        "owner_pid_alive": bool(active),
        "safe_retry": not active,
        "uncertain_result": False,
        "content_free": True,
        "absolute_path_returned": False,
    }


def inspect_metadata_lock(path: str | Path) -> dict[str, Any]:
    """Return a content-free lock classification for one exact metadata target."""
    target = Path(path).expanduser().resolve()
    digest = _target_digest(target)
    lock_path = metadata_lock_path(target)
    exists = lock_path.is_file()
    owner = _read_owner(lock_path) if exists else None
    abandoned = bool(exists and _owner_abandoned(lock_path, owner))
    valid_record = bool(
        owner
        and str(owner.get("target_digest") or "") == digest
        and len(str(owner.get("owner_token") or "")) >= 16
    )
    active = bool(exists and valid_record and not abandoned)
    return {
        "ok": True,
        "status": "active" if active else ("abandoned" if abandoned else ("invalid" if exists else "idle")),
        "target_digest": digest,
        "lock_exists": exists,
        "valid_record": valid_record,
        "owner_active": active,
        "owner_abandoned": abandoned,
        "safe_cleanup": bool(exists and abandoned and valid_record),
        "operator_review_required": bool(exists and (not valid_record or (not active and not abandoned))),
        "content_free": True,
        "absolute_path_returned": False,
    }


def cleanup_abandoned_metadata_lock(path: str | Path, *, operator_confirmed: bool) -> dict[str, Any]:
    """Remove only an exact-target lock whose recorded owner is demonstrably abandoned."""
    state = inspect_metadata_lock(path)
    operator_confirmed = operator_confirmed is True
    if not operator_confirmed:
        return {**state, "ok": False, "status": "confirmation_required", "removed": False}
    if not state.get("safe_cleanup"):
        return {**state, "ok": False, "status": "not_safe_to_cleanup", "removed": False}
    target = Path(path).expanduser().resolve()
    lock_path = metadata_lock_path(target)
    owner = _read_owner(lock_path)
    if not owner or str(owner.get("target_digest") or "") != _target_digest(target) or not _owner_abandoned(lock_path, owner):
        return {**inspect_metadata_lock(target), "ok": False, "status": "state_changed", "removed": False}
    try:
        lock_path.unlink()
    except OSError:
        return {**inspect_metadata_lock(target), "ok": False, "status": "cleanup_failed", "removed": False}
    return {**inspect_metadata_lock(target), "ok": True, "status": "abandoned_lock_removed", "removed": True}
