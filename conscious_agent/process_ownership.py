from __future__ import annotations

"""Private, generation-bound ownership for process-owned operations.

Ownership records live beneath the external runtime root, contain no command or
payload content, and are coordinated through the existing metadata mutation
lock.  Process identity includes the OS PID and a start identity so a recycled
PID cannot inherit an older operation.
"""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import signal
import socket
import time
from typing import Any
import uuid

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from paths import DATA_DIR
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from paths import DATA_DIR

SCHEMA_VERSION = "3"
TERMINAL_STATES = {"completed", "failed", "cancelled", "interrupted", "uncertain"}
ACTIVE_STATES = {"accepted", "starting", "running", "cancellation_requested"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _runtime_root() -> Path:
    override = os.getenv("EIDOLON_PROCESS_RUNTIME_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    legacy = os.getenv("EIDOLON_PROCESS_OWNERSHIP_DIR", "").strip()
    if legacy:
        path = Path(legacy).expanduser().resolve()
        return path.parent if path.name == "ownership" else path
    return DATA_DIR / "process_runtime"


def ownership_root() -> Path:
    return _runtime_root() / "ownership"


def results_root() -> Path:
    return _runtime_root() / "results"


def outputs_root() -> Path:
    return _runtime_root() / "outputs"


def _safe_operation_id(operation_id: str) -> str:
    value = str(operation_id or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
    if not value or len(value) > 160 or any(ch not in allowed for ch in value):
        raise ValueError("Invalid process operation identifier.")
    return value


def operation_digest(operation_id: str) -> str:
    return hashlib.sha256(_safe_operation_id(operation_id).encode("utf-8")).hexdigest()


def ownership_path(operation_id: str) -> Path:
    return ownership_root() / f"{operation_digest(operation_id)}.json"


def result_path(operation_id: str) -> Path:
    return results_root() / f"{operation_digest(operation_id)}.json"


def output_dir(operation_id: str) -> Path:
    return outputs_root() / operation_digest(operation_id)


def process_start_identity(pid: int | None = None) -> str:
    pid = int(pid or os.getpid())
    if pid <= 0:
        return ""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                return ""
            try:
                created = wintypes.FILETIME()
                exited = wintypes.FILETIME()
                kernel = wintypes.FILETIME()
                user = wintypes.FILETIME()
                ok = ctypes.windll.kernel32.GetProcessTimes(
                    handle,
                    ctypes.byref(created),
                    ctypes.byref(exited),
                    ctypes.byref(kernel),
                    ctypes.byref(user),
                )
                if not ok:
                    return ""
                ticks = (int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime)
                return f"win:{pid}:{ticks}"
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return ""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        boot_id = ""
        try:
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
        except OSError:
            pass
        if len(fields) > 21:
            return f"proc:{boot_id}:{pid}:{fields[21]}"
    except OSError:
        pass
    # Unknown identity must remain unknown for other processes.  Returning only
    # our own fallback avoids pretending PID liveness proves identity.
    return f"self:{pid}:{time.time_ns()}" if pid == os.getpid() else ""


_PROCESS_START_IDENTITY = process_start_identity(os.getpid())


def current_process_start_identity() -> str:
    return _PROCESS_START_IDENTITY


def process_is_alive(pid: int, expected_start_identity: str = "") -> bool | None:
    pid = int(pid or 0)
    if pid <= 0:
        return False
    if pid == os.getpid():
        alive: bool | None = True
        actual = _PROCESS_START_IDENTITY
    elif os.name == "nt":
        try:
            import ctypes
            process_query_limited_information = 0x1000
            still_active = 259
            handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                error = int(ctypes.windll.kernel32.GetLastError())
                alive = False if error in {87, 1168} else (True if error == 5 else None)
                actual = ""
            else:
                exit_code = ctypes.c_ulong()
                try:
                    alive = bool(
                        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                        and exit_code.value == still_active
                    )
                    actual = process_start_identity(pid) if alive else ""
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            alive = None
            actual = ""
    else:
        try:
            os.kill(pid, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        except PermissionError:
            alive = True
        except OSError:
            alive = None
        actual = process_start_identity(pid) if alive is True else ""
    if alive is True and expected_start_identity:
        if not actual:
            return None
        if actual != expected_start_identity:
            return False
    return alive


def _load(operation_id: str) -> dict[str, Any] | None:
    return load_json_file(ownership_path(operation_id), None, expected_type=dict)


def _write(operation_id: str, record: dict[str, Any]) -> None:
    path = ownership_path(operation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, record, expected_type=dict, sort_keys=True, coordinate=False)


def _owner_liveness(record: dict[str, Any]) -> bool | None:
    pid = int(record.get("owner_pid") or 0)
    identity = str(record.get("owner_start_identity") or "")
    if not pid or not identity:
        return False
    return process_is_alive(pid, identity)


def _child_liveness(record: dict[str, Any]) -> bool | None:
    pid = int(record.get("child_pid") or 0)
    identity = str(record.get("child_start_identity") or "")
    if not pid or not identity:
        return False
    return process_is_alive(pid, identity)


def _public(record: dict[str, Any] | None) -> dict[str, Any]:
    record = record or {}
    state = str(record.get("state") or "missing")
    owner_alive = _owner_liveness(record) if record else False
    child_alive = _child_liveness(record) if record else False
    operation_kind = str(record.get("operation_kind") or "unknown")
    may_mutate = bool(record.get("may_mutate"))
    return {
        "schema_version": SCHEMA_VERSION,
        "operation_id": str(record.get("operation_id") or ""),
        "operation_kind": operation_kind,
        "generation": int(record.get("generation") or 0),
        "state": state,
        "owner_active": owner_alive is True and state in ACTIVE_STATES,
        "owner_dead": owner_alive is False and state in ACTIVE_STATES,
        "owner_liveness_unknown": owner_alive is None and state in ACTIVE_STATES,
        "child_active": child_alive is True,
        "child_identity_mismatch_or_dead": child_alive is False and bool(record.get("child_pid")),
        "child_liveness_unknown": child_alive is None,
        "cancellation_requested": bool(record.get("cancellation_requested")),
        "cancellation_available": state in ACTIVE_STATES and owner_alive is not False,
        "bound_to_project": bool(record.get("project_id")),
        "bound_to_session": bool(record.get("session_id")),
        "bound_to_tab": bool(record.get("tab_id")),
        "tab_revision": int(record.get("tab_revision") or 0),
        "may_mutate": may_mutate,
        "safe_retry": state in {"failed", "cancelled", "interrupted"} and not may_mutate,
        "uncertain_result": state == "uncertain",
        "accepted_at": str(record.get("accepted_at") or ""),
        "updated_at": str(record.get("updated_at") or ""),
        "content_free": True,
        "private_owner_details_returned": False,
        "command_returned": False,
        "payload_returned": False,
    }


def inspect_process_operation(operation_id: str) -> dict[str, Any]:
    return _public(_load(operation_id))


def accept_process_operation(
    operation_id: str,
    *,
    operation_kind: str,
    may_mutate: bool,
    acceptance_key: str,
    project_id: str = "",
    session_id: str = "",
    tab_id: str = "",
    tab_revision: int = 0,
) -> dict[str, Any]:
    token = _safe_operation_id(operation_id)
    if not str(operation_kind or "").strip():
        raise ValueError("operation_kind is required")
    if not str(acceptance_key or "").strip():
        raise ValueError("acceptance_key is required")
    path = ownership_path(token)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        existing = _load(token)
        if path.exists() and existing is None:
            return {
                "ok": False, "status": "invalid_existing_ownership",
                "operation_id": token, "content_free": True, "safe_retry": False,
            }
        if existing:
            public = _public(existing)
            same_acceptance = str(existing.get("acceptance_key") or "") == str(acceptance_key)
            if same_acceptance:
                return {**public, "ok": True, "status": "already_accepted", "duplicate": True}
            if str(existing.get("state") or "") in ACTIVE_STATES or public["owner_active"] or public["child_active"]:
                return {**public, "ok": False, "status": "already_owned", "duplicate": False}
            # An old terminal generation is retained as evidence; a different
            # acceptance key must use a new operation ID rather than reusing it.
            return {**public, "ok": False, "status": "operation_id_reuse_rejected", "duplicate": False}
        now = _utc_now()
        record = {
            "schema_version": SCHEMA_VERSION,
            "operation_id": token,
            "operation_kind": str(operation_kind)[:80],
            "may_mutate": bool(may_mutate),
            "acceptance_key": str(acceptance_key)[:240],
            "project_id": str(project_id or "")[:160],
            "session_id": str(session_id or "")[:160],
            "tab_id": str(tab_id or "")[:160],
            "tab_revision": max(0, int(tab_revision or 0)),
            "generation": 1,
            "state": "accepted",
            "launcher_pid": os.getpid(),
            "launcher_start_identity": _PROCESS_START_IDENTITY,
            "owner_pid": 0,
            "owner_start_identity": "",
            "owner_nonce": "",
            "child_pid": 0,
            "child_start_identity": "",
            "child_process_group_id": 0,
            "cancellation_requested": False,
            "accepted_at": now,
            "updated_at": now,
            "host_digest": hashlib.sha256(socket.gethostname().encode("utf-8", errors="ignore")).hexdigest(),
            "redacted": True,
        }
        _write(token, record)
    return {**_public(record), "ok": True, "status": "accepted", "duplicate": False}


def activate_process_operation(operation_id: str, generation: int) -> dict[str, Any]:
    token = _safe_operation_id(operation_id)
    path = ownership_path(token)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        record = _load(token)
        if not record:
            return {"ok": False, "status": "not_found", "operation_id": token, "content_free": True}
        if int(record.get("generation") or 0) != int(generation):
            return {**_public(record), "ok": False, "status": "generation_mismatch"}
        alive = _owner_liveness(record)
        state = str(record.get("state") or "")
        child_alive = _child_liveness(record)
        if state in ACTIVE_STATES and alive is True:
            return {**_public(record), "ok": False, "status": "live_owner_preserved", "safe_retry": True}
        if child_alive is True:
            return {**_public(record), "ok": False, "status": "live_child_preserved", "safe_retry": False}
        if state not in {"accepted", "starting", "running"}:
            return {**_public(record), "ok": False, "status": "not_activatable"}
        record["state"] = "starting"
        record["owner_pid"] = os.getpid()
        record["owner_start_identity"] = _PROCESS_START_IDENTITY
        record["owner_nonce"] = uuid.uuid4().hex
        record["updated_at"] = _utc_now()
        _write(token, record)
    return {**_public(record), "ok": True, "status": "starting", "owner_nonce": record["owner_nonce"]}


def register_process_child(
    operation_id: str,
    generation: int,
    owner_nonce: str,
    child_pid: int,
    *,
    child_process_group_id: int | None = None,
) -> dict[str, Any]:
    token = _safe_operation_id(operation_id)
    path = ownership_path(token)
    child_pid = int(child_pid or 0)
    identity = process_start_identity(child_pid)
    if child_pid <= 0 or not identity:
        return {"ok": False, "status": "child_identity_unavailable", "operation_id": token, "content_free": True}
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        record = _load(token)
        if not record:
            return {"ok": False, "status": "not_found", "operation_id": token, "content_free": True}
        if int(record.get("generation") or 0) != int(generation) or str(record.get("owner_nonce") or "") != str(owner_nonce):
            return {**_public(record), "ok": False, "status": "owner_mismatch"}
        record["child_pid"] = child_pid
        record["child_start_identity"] = identity
        record["child_process_group_id"] = int(child_process_group_id or 0)
        record["state"] = "running"
        record["updated_at"] = _utc_now()
        _write(token, record)
    return {**_public(record), "ok": True, "status": "child_registered"}


def process_operation_cancellation_requested(operation_id: str, generation: int) -> bool:
    record = _load(operation_id)
    return bool(
        record
        and int(record.get("generation") or 0) == int(generation)
        and record.get("cancellation_requested") is True
    )


def _binding_matches(
    record: dict[str, Any], *, generation: int, project_id: str, session_id: str,
    tab_id: str, tab_revision: int,
) -> tuple[bool, str]:
    if int(record.get("generation") or 0) != int(generation):
        return False, "generation_mismatch"
    for field, expected in (("project_id", project_id), ("session_id", session_id), ("tab_id", tab_id)):
        stored = str(record.get(field) or "")
        if stored and stored != str(expected or ""):
            return False, f"{field}_mismatch"
    stored_revision = int(record.get("tab_revision") or 0)
    if stored_revision and stored_revision != int(tab_revision or 0):
        return False, "tab_revision_mismatch"
    return True, "match"


def request_process_operation_cancellation_exact(
    operation_id: str, *, generation: int, project_id: str = "", session_id: str = "",
    tab_id: str = "", tab_revision: int = 0, operator_confirmed: bool,
) -> dict[str, Any]:
    if operator_confirmed is not True:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "confirmation_required"}
    token = _safe_operation_id(operation_id)
    path = ownership_path(token)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        record = _load(token)
        if not record:
            return {"ok": False, "status": "not_found", "operation_id": token, "content_free": True}
        matched, reason = _binding_matches(
            record, generation=generation, project_id=project_id, session_id=session_id,
            tab_id=tab_id, tab_revision=tab_revision,
        )
        if not matched:
            return {**_public(record), "ok": False, "status": reason, "stale_request": True}
        if str(record.get("state") or "") in TERMINAL_STATES:
            return {**_public(record), "ok": False, "status": "already_terminal"}
        owner_alive = _owner_liveness(record)
        child_alive = _child_liveness(record)
        if owner_alive is False and child_alive is not True:
            return {**_public(record), "ok": False, "status": "owner_not_live", "safe_retry": not bool(record.get("may_mutate"))}
        record["cancellation_requested"] = True
        record["state"] = "cancellation_requested"
        record["cancellation_generation"] = int(generation)
        record["cancellation_owner_nonce_digest"] = hashlib.sha256(str(record.get("owner_nonce") or "").encode("utf-8")).hexdigest()
        record["cancellation_child_identity_digest"] = hashlib.sha256(str(record.get("child_start_identity") or "").encode("utf-8")).hexdigest()
        record["cancellation_requested_at"] = _utc_now()
        record["updated_at"] = _utc_now()
        _write(token, record)
    return {**_public(record), "ok": True, "status": "cancellation_requested", "cooperative_first": True}


def request_process_operation_cancellation(operation_id: str, *, operator_confirmed: bool) -> dict[str, Any]:
    """Backward-compatible internal wrapper; new callers must use exact bindings."""
    record = _load(operation_id)
    if not record:
        return {"ok": False, "status": "not_found", "operation_id": str(operation_id), "content_free": True}
    return request_process_operation_cancellation_exact(
        operation_id,
        generation=int(record.get("generation") or 0),
        project_id=str(record.get("project_id") or ""),
        session_id=str(record.get("session_id") or ""),
        tab_id=str(record.get("tab_id") or ""),
        tab_revision=int(record.get("tab_revision") or 0),
        operator_confirmed=operator_confirmed,
    )


def write_process_result(
    operation_id: str,
    *,
    generation: int,
    owner_nonce: str,
    state: str,
    return_code: int | None = None,
    applied: bool = False,
    timed_out: bool = False,
    log_limit_exceeded: bool = False,
) -> dict[str, Any]:
    if state not in TERMINAL_STATES:
        raise ValueError("Invalid process result state.")
    token = _safe_operation_id(operation_id)
    owner = _load(token)
    if not owner:
        return {"ok": False, "status": "not_found", "operation_id": token, "content_free": True}
    if int(owner.get("generation") or 0) != int(generation) or str(owner.get("owner_nonce") or "") != str(owner_nonce):
        return {**_public(owner), "ok": False, "status": "owner_mismatch"}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "operation_id": token,
        "generation": int(generation),
        "owner_nonce_digest": hashlib.sha256(str(owner_nonce).encode("utf-8")).hexdigest(),
        "state": state,
        "return_code": None if return_code is None else int(return_code),
        "applied": bool(applied),
        "timed_out": bool(timed_out),
        "log_limit_exceeded": bool(log_limit_exceeded),
        "persisted_at": _utc_now(),
        "redacted": True,
    }
    path = result_path(token)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, payload, expected_type=dict, sort_keys=True)
    return {"ok": True, "status": state, "operation_id": token, "content_free": True}


def finalize_process_operation(
    operation_id: str,
    generation: int,
    owner_nonce: str,
    *,
    state: str,
) -> dict[str, Any]:
    if state not in TERMINAL_STATES:
        raise ValueError("Invalid terminal process state.")
    token = _safe_operation_id(operation_id)
    path = ownership_path(token)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        record = _load(token)
        if not record:
            return {"ok": False, "status": "not_found", "operation_id": token, "content_free": True}
        if int(record.get("generation") or 0) != int(generation) or str(record.get("owner_nonce") or "") != str(owner_nonce):
            return {**_public(record), "ok": False, "status": "owner_mismatch"}
        record["state"] = state
        record["updated_at"] = _utc_now()
        record["finished_at"] = _utc_now()
        _write(token, record)
    return {**_public(record), "ok": True, "status": state}


def load_private_process_operation(operation_id: str) -> dict[str, Any] | None:
    """Internal recovery helper; never expose this record through dashboard routes."""
    return _load(operation_id)


def process_ownership_contains_private_fields() -> tuple[str, ...]:
    return (
        "acceptance_key",
        "launcher_pid",
        "launcher_start_identity",
        "owner_pid",
        "owner_start_identity",
        "owner_nonce",
        "child_pid",
        "child_start_identity",
        "child_process_group_id",
        "project_id",
        "session_id",
        "tab_id",
        "acceptance_key",
        "cancellation_owner_nonce_digest",
        "cancellation_child_identity_digest",
    )
