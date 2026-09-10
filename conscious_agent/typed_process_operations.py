from __future__ import annotations
"""v1336 typed process operations for disposable candidate workspaces.

This layer binds process start/monitor/stop to an existing v1333 disposable
workspace, a sealed satisfied v1332 shell precondition, and an active v1302
standing grant. Commands are argument vectors, never shell text. Process
ownership, PID start-identity checks, exact process-tree cancellation, and
crash/orphan reconciliation reuse the retained v1094 process subsystem.

Raw command arguments, environment values, PIDs, process start identities, and
log text are runtime-private and are never persisted in public v1336 evidence.
"""
import hashlib
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from standing_session_grants import standing_session_allows
from tool_preconditions import load_tool_preconditions
from workspace_isolation import _is_link_like, _record_path as _workspace_record_path, _within
from process_worker_entrypoints import start_bounded_command_worker
from process_ownership import inspect_process_operation, load_private_process_operation, output_dir
from process_recovery import cancel_process_operation_with_escalation, reconcile_process_operation

CONTRACT_VERSION = "v1336.8"
PROCESS_OPERATION_KINDS = ("start", "monitor", "stop")
MAX_ARGUMENTS = 128
MAX_ARGUMENT_BYTES = 32 * 1024
MAX_ENVIRONMENT_ENTRIES = 32
MAX_TIMEOUT_SECONDS = 3600.0
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOG_TAIL_BYTES = 64 * 1024
SPAWN_BIND_GRACE_SECONDS = 3.0
PROCESS_OPERATION_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
    "network_authorized": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_process_operations"


def _record_path(operation_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"proc_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_process_operation_id")
    return _root(runtime_root) / "records" / f"{operation_id}.json"


def _load_sealed(path: Path) -> dict[str, Any]:
    row = _read_json(path)
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest", None)
    row["record_digest"] = digest(row)
    _atomic_json(_record_path(str(row["process_operation_id"]), runtime_root), row)
    return row


def _workspace(workspace_id: str, runtime_root=None) -> dict[str, Any]:
    row = _load_sealed(_workspace_record_path(workspace_id, runtime_root))
    if not row or row.get("cleaned") or not row.get("workspace_created"):
        return {}
    root = Path(str(row.get("candidate_private_path") or ""))
    if not root.is_dir() or _is_link_like(root):
        return {}
    return row


def _precondition(record_id: str, runtime_root=None) -> dict[str, Any]:
    row = load_tool_preconditions(str(record_id or ""), runtime_root=runtime_root, include_private=True)
    if not row or row.get("preconditions_satisfied") is not True or row.get("tool_code") != "shell" or row.get("tool_invoked") is not False:
        return {}
    return row


def _grant_ok(workspace: Mapping[str, Any], grant: Mapping[str, Any], now_unix: int | None) -> tuple[bool, str]:
    if str(grant.get("workspace_digest") or "") != str(workspace.get("source_workspace_digest") or ""):
        return False, "standing_grant_workspace_mismatch"
    if not standing_session_allows(grant, "command", now_unix=now_unix):
        return False, "active_command_grant_required"
    classes = set((grant.get("profile_snapshot") or {}).get("command_classes") or [])
    if not ({"shell", "process"} & classes):
        return False, "typed_process_command_class_required"
    return True, ""


def _safe_cwd(workspace: Mapping[str, Any], cwd_relative: str) -> Path:
    root = Path(str(workspace.get("candidate_private_path") or "")).resolve(strict=True)
    text = str(cwd_relative or ".").replace("\\", "/").strip() or "."
    pure = PurePosixPath(text)
    if pure.is_absolute() or any(part == ".." for part in pure.parts):
        raise ValueError("unsafe_process_cwd")
    candidate = root.joinpath(*[p for p in pure.parts if p not in {"", "."}])
    current = root
    for part in [p for p in pure.parts if p not in {"", "."}]:
        current = current / part
        if current.exists() and _is_link_like(current):
            raise ValueError("process_cwd_link_or_junction_rejected")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir() or not _within(root, resolved):
        raise ValueError("process_cwd_outside_candidate")
    return resolved


def _argv(value: Sequence[str]) -> list[str]:
    if isinstance(value, (str, bytes)):
        raise ValueError("argument_vector_required")
    rows = [str(x) for x in value]
    if not rows or len(rows) > MAX_ARGUMENTS or any(not x or "\x00" in x for x in rows):
        raise ValueError("argument_vector_invalid")
    if sum(len(x.encode("utf-8")) for x in rows) > MAX_ARGUMENT_BYTES:
        raise ValueError("argument_vector_budget_exceeded")
    return rows


def _environment(value: Mapping[str, str] | None) -> dict[str, str]:
    raw = dict(value or {})
    if len(raw) > MAX_ENVIRONMENT_ENTRIES:
        raise ValueError("environment_entry_budget_exceeded")
    result: dict[str, str] = {}
    for key, val in raw.items():
        if not isinstance(key, str) or not isinstance(val, str) or not key or "\x00" in key or "\x00" in val:
            raise ValueError("environment_entry_invalid")
        result[key] = val
    return result


def _runtime_process_root(runtime_root=None) -> Path:
    root = _root(runtime_root) / "process_runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextmanager
def _process_runtime(runtime_root=None):
    key = "EIDOLON_PROCESS_RUNTIME_ROOT"
    old = os.environ.get(key)
    os.environ[key] = str(_runtime_process_root(runtime_root))
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "process_operation_id": row.get("process_operation_id"),
        "workspace_id": row.get("workspace_id"),
        "source_workspace_digest": row.get("source_workspace_digest"),
        "precondition_record_id": row.get("precondition_record_id"),
        "grant_digest": row.get("grant_digest"),
        "argument_count": int(row.get("argument_count") or 0),
        "argument_vector_digest": row.get("argument_vector_digest"),
        "cwd_digest": row.get("cwd_digest"),
        "environment_key_count": int(row.get("environment_key_count") or 0),
        "environment_keys_digest": row.get("environment_keys_digest"),
        "timeout_seconds": float(row.get("timeout_seconds") or 0.0),
        "max_log_bytes": int(row.get("max_log_bytes") or 0),
        "process_state": row.get("process_state"),
        "generation": int(row.get("generation") or 0),
        "return_code": row.get("return_code"),
        "timed_out": row.get("timed_out") is True,
        "log_limit_exceeded": row.get("log_limit_exceeded") is True,
        "stdout_bytes": int(row.get("stdout_bytes") or 0),
        "stderr_bytes": int(row.get("stderr_bytes") or 0),
        "stdout_digest": row.get("stdout_digest") or "",
        "stderr_digest": row.get("stderr_digest") or "",
        "orphan_running": row.get("process_state") == "orphan_running",
        "recovery_required": row.get("recovery_required") is True,
        "safe_retry": row.get("safe_retry") is True,
        "worker_or_child_identity_exposed": False,
        "raw_command_exposed": False,
        "environment_values_exposed": False,
        "raw_log_persisted_in_evidence": False,
        "selected_source_modified": False,
        "candidate_workspace_only": True,
        "content_free": True,
        **PROCESS_OPERATION_DENIED_AUTHORITY,
    }


def _log_summary(process_runtime_root: Path, owner_operation_id: str) -> dict[str, Any]:
    hashed = hashlib.sha256(owner_operation_id.encode("utf-8")).hexdigest()
    folder = process_runtime_root / "outputs" / hashed
    out: dict[str, Any] = {}
    for code, filename in (("stdout", "stdout.txt"), ("stderr", "stderr.txt")):
        path = folder / filename
        if path.is_file():
            data = path.read_bytes()
            out[f"{code}_bytes"] = len(data)
            out[f"{code}_digest"] = hashlib.sha256(data).hexdigest()
        else:
            out[f"{code}_bytes"] = 0
            out[f"{code}_digest"] = ""
    return out


def _result_summary(process_runtime_root: Path, owner_operation_id: str) -> dict[str, Any]:
    hashed = hashlib.sha256(owner_operation_id.encode("utf-8")).hexdigest()
    row = _read_json(process_runtime_root / "results" / f"{hashed}.json")
    return {
        "return_code": row.get("return_code") if row else None,
        "timed_out": bool(row and row.get("timed_out") is True),
        "log_limit_exceeded": bool(row and row.get("log_limit_exceeded") is True),
    }


def _sync_record(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    owner_id = str(row.get("owner_operation_id") or "")
    with _process_runtime(runtime_root):
        observed = inspect_process_operation(owner_id)
        observed_state = str(observed.get("state") or "missing")
        age = max(0.0, time.time() - float(row.get("created_unix") or 0.0))
        # A spawn worker may not yet have executed activate_process_operation.
        # During that bounded window, accepted/starting with no bound child is
        # normal startup, not evidence of a stale owner.
        if observed_state in {"accepted", "starting"} and not observed.get("child_active") and age < SPAWN_BIND_GRACE_SECONDS:
            state = {**observed, "ok": True, "status": "starting", "safe_retry": False}
        else:
            state = reconcile_process_operation(owner_id, terminate_orphan=False)
    row["process_state"] = str(state.get("status") or state.get("state") or "unknown")
    row["generation"] = int(state.get("generation") or row.get("generation") or 0)
    row["recovery_required"] = state.get("recovery_required") is True
    row["safe_retry"] = state.get("safe_retry") is True
    row.update(_log_summary(_runtime_process_root(runtime_root), owner_id))
    row.update(_result_summary(_runtime_process_root(runtime_root), owner_id))
    _save(row, runtime_root)
    return row


def _load(operation_id: str, runtime_root=None) -> dict[str, Any]:
    return _load_sealed(_record_path(operation_id, runtime_root))


def start_candidate_process(
    workspace_id: str,
    argv: Sequence[str],
    *,
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    cwd_relative: str = ".",
    environment: Mapping[str, str] | None = None,
    timeout_seconds: float = 300.0,
    max_log_bytes: int = MAX_LOG_BYTES,
    runtime_root=None,
    now_unix: int | None = None,
    include_private_worker_handle: bool = False,
    invocation_discriminator: str = "",
) -> dict[str, Any]:
    workspace = _workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_missing_or_invalid", **PROCESS_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _grant_ok(workspace, active_grant, now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **PROCESS_OPERATION_DENIED_AUTHORITY}
    pre = _precondition(precondition_record_id, runtime_root)
    if not pre:
        return {"ok": False, "status": "sealed_satisfied_shell_preconditions_required", **PROCESS_OPERATION_DENIED_AUTHORITY}
    try:
        args = _argv(argv)
        env = _environment(environment)
        cwd = _safe_cwd(workspace, cwd_relative)
        timeout = float(timeout_seconds)
        log_budget = int(max_log_bytes)
        if timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
            raise ValueError("process_timeout_budget_invalid")
        if log_budget < 1024 or log_budget > MAX_LOG_BYTES:
            raise ValueError("process_log_budget_invalid")
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "status": str(exc), **PROCESS_OPERATION_DENIED_AUTHORITY}

    material = {
        "contract": CONTRACT_VERSION,
        "workspace": workspace_id,
        "args": [hashlib.sha256(x.encode()).hexdigest() for x in args],
        "cwd": hashlib.sha256(str(cwd.relative_to(Path(str(workspace["candidate_private_path"])).resolve())).encode()).hexdigest(),
        "env_keys": sorted(env),
        "timeout": timeout,
        "log": log_budget,
        "pre": pre.get("record_digest"),
        "grant": active_grant.get("grant_digest"),
        "invocation_discriminator": str(invocation_discriminator or "")[:80],
    }
    process_operation_id = "proc_" + digest(material)[:24]
    existing = _load(process_operation_id, runtime_root)
    if existing:
        synced = _sync_record(existing, runtime_root)
        result = {"ok": True, "status": "process_operation_already_exists", "duplicate": True, "process_operation": _public(synced), "operation_executed_this_request": False, **PROCESS_OPERATION_DENIED_AUTHORITY}
        return result

    owner_operation_id = "v1336:" + process_operation_id
    acceptance_key = digest(material)
    project_id = str(workspace_id)
    session_id = str(active_grant.get("grant_id") or active_grant.get("grant_digest") or "")[:160]
    config = {
        "command": args,
        "cwd": str(cwd),
        "timeout_seconds": timeout,
        "environment": env,
        "max_stdout_bytes": log_budget,
        "max_stderr_bytes": log_budget,
    }
    with _process_runtime(runtime_root):
        launched = start_bounded_command_worker(
            operation_id=owner_operation_id,
            acceptance_key=acceptance_key,
            operation_kind="v1336_candidate_process",
            may_mutate=True,
            config=config,
            project_id=project_id,
            session_id=session_id,
            tab_id=process_operation_id,
            tab_revision=1,
        )
    if not launched.get("ok"):
        return {"ok": False, "status": str(launched.get("status") or "process_start_failed"), **PROCESS_OPERATION_DENIED_AUTHORITY}
    row = {
        "contract_version": CONTRACT_VERSION,
        "process_operation_id": process_operation_id,
        "owner_operation_id": owner_operation_id,
        "workspace_id": workspace_id,
        "source_workspace_digest": workspace.get("source_workspace_digest"),
        "precondition_record_id": precondition_record_id,
        "precondition_digest": pre.get("record_digest"),
        "grant_digest": active_grant.get("grant_digest"),
        "session_id_digest": hashlib.sha256(session_id.encode()).hexdigest(),
        "argument_count": len(args),
        "argument_vector_digest": digest([hashlib.sha256(x.encode()).hexdigest() for x in args]),
        "cwd_digest": hashlib.sha256(str(cwd).encode()).hexdigest(),
        "environment_key_count": len(env),
        "environment_keys_digest": digest(sorted(env)),
        "timeout_seconds": timeout,
        "max_log_bytes": log_budget,
        "process_state": "starting",
        "created_unix": time.time(),
        "generation": int(launched.get("generation") or 1),
        "return_code": None,
        "timed_out": False,
        "log_limit_exceeded": False,
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "stdout_digest": "",
        "stderr_digest": "",
        "recovery_required": False,
        "safe_retry": False,
        "selected_source_modified": False,
        "candidate_workspace_only": True,
        "raw_command_persisted": False,
        "environment_values_persisted": False,
        "content_free": True,
    }
    _save(row, runtime_root)
    # Allow the spawn worker a short bounded window to bind owner/child identity.
    deadline = time.monotonic() + SPAWN_BIND_GRACE_SECONDS
    while time.monotonic() < deadline:
        synced = _sync_record(row, runtime_root)
        if synced.get("process_state") not in {"accepted", "starting"}:
            row = synced
            break
        time.sleep(0.02)
    result = {"ok": True, "status": "candidate_process_started", "duplicate": False, "process_operation": _public(row), "operation_executed_this_request": True, **PROCESS_OPERATION_DENIED_AUTHORITY}
    if include_private_worker_handle:
        result["_worker_handle"] = launched.get("worker_handle")
        result["_worker_pid"] = launched.get("worker_pid")
    return result


def monitor_candidate_process(operation_id: str, *, runtime_root=None, include_log_tail: bool = False) -> dict[str, Any]:
    row = _load(operation_id, runtime_root)
    if not row:
        return {"ok": False, "status": "process_operation_missing_or_invalid", **PROCESS_OPERATION_DENIED_AUTHORITY}
    row = _sync_record(row, runtime_root)
    result: dict[str, Any] = {"ok": True, "status": "candidate_process_observed", "process_operation": _public(row), "action_executed": False, **PROCESS_OPERATION_DENIED_AUTHORITY}
    if include_log_tail:
        folder = _runtime_process_root(runtime_root) / "outputs" / hashlib.sha256(str(row["owner_operation_id"]).encode()).hexdigest()
        tails = {}
        for code, filename in (("stdout", "stdout.txt"), ("stderr", "stderr.txt")):
            path = folder / filename
            data = path.read_bytes()[-MAX_LOG_TAIL_BYTES:] if path.is_file() else b""
            tails[code] = data.decode("utf-8", errors="replace")
        result["log_tail"] = tails
        result["log_tail_internal_only"] = True
    return result


def stop_candidate_process(
    operation_id: str,
    *,
    active_grant: Mapping[str, Any],
    runtime_root=None,
    now_unix: int | None = None,
    force_termination_permitted: bool = True,
) -> dict[str, Any]:
    row = _load(operation_id, runtime_root)
    if not row:
        return {"ok": False, "status": "process_operation_missing_or_invalid", **PROCESS_OPERATION_DENIED_AUTHORITY}
    workspace = _workspace(str(row.get("workspace_id") or ""), runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_missing_or_invalid", **PROCESS_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _grant_ok(workspace, active_grant, now_unix)
    if not grant_ok or str(active_grant.get("grant_digest") or "") != str(row.get("grant_digest") or ""):
        return {"ok": False, "status": reason if not grant_ok else "standing_grant_lineage_mismatch", **PROCESS_OPERATION_DENIED_AUTHORITY}
    # Stop is unavailable while spawn ownership is not yet identity-bound. Wait a
    # bounded interval rather than treating the normal spawn window as stale.
    owner_id = str(row.get("owner_operation_id") or "")
    deadline = time.monotonic() + SPAWN_BIND_GRACE_SECONDS
    private: dict[str, Any] = {}
    while time.monotonic() < deadline:
        with _process_runtime(runtime_root):
            private = load_private_process_operation(owner_id) or {}
        if private.get("owner_start_identity") and private.get("owner_nonce"):
            break
        state = str(private.get("state") or "")
        if state in {"completed", "failed", "cancelled", "interrupted", "uncertain"}:
            break
        time.sleep(0.02)
    if not private:
        return {"ok": False, "status": "process_ownership_missing", **PROCESS_OPERATION_DENIED_AUTHORITY}
    if not private.get("owner_start_identity") and str(private.get("state") or "") not in {"completed", "failed", "cancelled", "interrupted", "uncertain"}:
        return {"ok": False, "status": "process_spawn_binding_incomplete", **PROCESS_OPERATION_DENIED_AUTHORITY}
    with _process_runtime(runtime_root):
        stopped = cancel_process_operation_with_escalation(
            owner_id,
            generation=int(private.get("generation") or row.get("generation") or 1),
            project_id=str(row.get("workspace_id") or ""),
            session_id=str(private.get("session_id") or ""),
            tab_id=str(operation_id),
            tab_revision=1,
            operator_confirmed=True,
            force_termination_permitted=bool(force_termination_permitted),
            cooperative_wait_seconds=0.5,
        )
    synced = _sync_record(row, runtime_root)
    return {"ok": str(synced.get("process_state")) in {"cancelled", "failed", "completed", "interrupted", "uncertain"}, "status": "candidate_process_stop_reconciled", "stop_result_status": stopped.get("status"), "process_operation": _public(synced), "operation_executed_this_request": True, **PROCESS_OPERATION_DENIED_AUTHORITY}


def recover_candidate_process(operation_id: str, *, runtime_root=None, terminate_orphan: bool = False) -> dict[str, Any]:
    row = _load(operation_id, runtime_root)
    if not row:
        return {"ok": False, "status": "process_operation_missing_or_invalid", **PROCESS_OPERATION_DENIED_AUTHORITY}
    with _process_runtime(runtime_root):
        recovered = reconcile_process_operation(str(row.get("owner_operation_id") or ""), terminate_orphan=terminate_orphan)
    synced = _sync_record(row, runtime_root)
    return {"ok": bool(recovered.get("ok")), "status": str(recovered.get("status") or "process_recovery_observed"), "process_operation": _public(synced), "orphan_terminated": recovered.get("orphan_terminated") is True, "replay_allowed": False, "action_executed": bool(terminate_orphan and recovered.get("orphan_terminated")), **PROCESS_OPERATION_DENIED_AUTHORITY}


def load_process_operation(operation_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _load(operation_id, runtime_root)
    return _public(row) if row else {}


def process_process_operations_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    lowered = str(text or "").strip().lower()
    if lowered not in {"show process operation", "inspect process operation", "show process operations"}:
        return {"active": False}
    state = project_state or {}
    operation_id = str(state.get("process_operation_id") or "")
    row = load_process_operation(operation_id, runtime_root=runtime_root) if operation_id else {}
    return {"active": True, "ok": bool(row), "status": "process_operation_inspection_ready" if row else "process_operation_not_selected", "process_operation": row, "action_executed": False, **PROCESS_OPERATION_DENIED_AUTHORITY}


__all__ = [
    "CONTRACT_VERSION", "PROCESS_OPERATION_KINDS", "MAX_LOG_BYTES", "MAX_LOG_TAIL_BYTES", "PROCESS_OPERATION_DENIED_AUTHORITY",
    "start_candidate_process", "monitor_candidate_process", "stop_candidate_process", "recover_candidate_process", "load_process_operation", "process_process_operations_control",
]
