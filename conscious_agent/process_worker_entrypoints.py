from __future__ import annotations

"""Import-safe spawn entry points for bounded command workers."""

import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence
import uuid

try:
    from process_ownership import accept_process_operation, activate_process_operation, finalize_process_operation, inspect_process_operation, output_dir, process_operation_cancellation_requested, register_process_child, request_process_operation_cancellation, write_process_result
except ImportError:
    from process_ownership import (
        accept_process_operation,
        activate_process_operation,
        finalize_process_operation,
        inspect_process_operation,
        output_dir,
        process_operation_cancellation_requested,
        register_process_child,
        request_process_operation_cancellation,
        write_process_result,
    )

SCHEMA_VERSION = "1"
_SAFE_ENVIRONMENT_KEYS = {
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "HOME", "USERPROFILE",
    "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "PYTHONPATH", "PYTHONHOME",
    "PYTHONPYCACHEPREFIX", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED",
    "EIDOLON_DATA_DIR", "EIDOLON_PROCESS_RUNTIME_ROOT", "EIDOLON_METADATA_LOCK_DIR",
    "EIDOLON_VERIFICATION_RUNTIME_ROOT",
}


def process_worker_inventory() -> dict[str, Any]:
    rows = [
        {
            "id": "bounded_command_spawn",
            "entrypoint": "conscious_agent.process_worker_entrypoints.run_bounded_command_worker",
            "process_model": "multiprocessing_spawn",
            "explicit_serializable_configuration": True,
            "file_backed_output": True,
            "ownership_contract": True,
        },
        {
            "id": "isolated_verification_worker",
            "entrypoint": "tools.isolated_suite_worker.main",
            "process_model": "new_process_group",
            "explicit_serializable_configuration": True,
            "file_backed_output": True,
            "ownership_contract": True,
        },
        {
            "id": "dashboard_startup_probe",
            "entrypoint": "conscious_agent.dashboard_startup",
            "process_model": "subprocess",
            "explicit_serializable_configuration": True,
            "file_backed_output": False,
            "ownership_contract": False,
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "worker_count": len(rows),
        "rows": rows,
        "content_free": True,
        "command_returned": False,
        "environment_returned": False,
        "payload_returned": False,
    }


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, (list, tuple)) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be a nonempty string list")
    return [str(item) for item in value]


def validate_process_worker_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise ValueError("Worker configuration must be a mapping.")
    command = _string_list(config.get("command"), "command")
    cwd = str(config.get("cwd") or "").strip()
    if not cwd:
        raise ValueError("cwd is required")
    timeout = max(0.1, min(float(config.get("timeout_seconds") or 300.0), 86400.0))
    environment = config.get("environment") or {}
    if not isinstance(environment, Mapping) or not all(isinstance(k, str) and isinstance(v, str) for k, v in environment.items()):
        raise ValueError("environment must contain string keys and values")
    max_stdout_bytes = max(1024, min(int(config.get("max_stdout_bytes") or (2 * 1024 * 1024)), 64 * 1024 * 1024))
    max_stderr_bytes = max(1024, min(int(config.get("max_stderr_bytes") or (2 * 1024 * 1024)), 64 * 1024 * 1024))
    normalized = {
        "command": command,
        "cwd": str(Path(cwd).expanduser().resolve()),
        "timeout_seconds": timeout,
        "environment": dict(environment),
        "max_stdout_bytes": max_stdout_bytes,
        "max_stderr_bytes": max_stderr_bytes,
    }
    # This rejects callbacks, Path instances, and other inherited parent state.
    json.dumps(normalized)
    return normalized


def _filtered_environment(explicit: Mapping[str, str]) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key in _SAFE_ENVIRONMENT_KEYS}
    environment.update({str(key): str(value) for key, value in explicit.items()})
    return environment


def _terminate_process_tree(process: subprocess.Popen[Any], group_id: int = 0) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        except Exception:
            try:
                process.terminate()
            except OSError:
                pass
    else:
        try:
            os.killpg(int(group_id or process.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.terminate()
            except OSError:
                pass
        deadline = time.monotonic() + 2.0
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if process.poll() is None:
            try:
                os.killpg(int(group_id or process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    process.kill()
                except OSError:
                    pass
    try:
        process.wait(timeout=5)
    except Exception:
        pass


def run_bounded_command_worker(operation_id: str, generation: int, config: dict[str, Any]) -> None:
    """Module-level spawn target. Arguments are deliberately JSON-serializable."""
    activated = activate_process_operation(operation_id, generation)
    if not activated.get("ok"):
        return
    owner_nonce = str(activated.get("owner_nonce") or "")
    normalized = validate_process_worker_config(config)
    root = output_dir(operation_id)
    root.mkdir(parents=True, exist_ok=True)
    stdout_path = root / "stdout.txt"
    stderr_path = root / "stderr.txt"
    environment = _filtered_environment(normalized["environment"])
    popen_kwargs: dict[str, Any] = {}
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True
    state = "failed"
    return_code: int | None = None
    timed_out = False
    log_limit_exceeded = False
    child: subprocess.Popen[Any] | None = None
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            child = subprocess.Popen(
                normalized["command"],
                cwd=normalized["cwd"],
                env=environment,
                stdout=stdout_file,
                stderr=stderr_file,
                creationflags=creationflags,
                **popen_kwargs,
            )
            group_id = child.pid
            registered = register_process_child(
                operation_id,
                generation,
                owner_nonce,
                child.pid,
                child_process_group_id=group_id,
            )
            if not registered.get("ok"):
                _terminate_process_tree(child, group_id)
                state = "uncertain"
            else:
                deadline = time.monotonic() + float(normalized["timeout_seconds"])
                while child.poll() is None:
                    if process_operation_cancellation_requested(operation_id, generation):
                        _terminate_process_tree(child, group_id)
                        state = "cancelled"
                        break
                    if time.monotonic() >= deadline:
                        timed_out = True
                        _terminate_process_tree(child, group_id)
                        state = "failed"
                        break
                    try:
                        stdout_size = stdout_path.stat().st_size if stdout_path.exists() else 0
                        stderr_size = stderr_path.stat().st_size if stderr_path.exists() else 0
                    except OSError:
                        stdout_size = stderr_size = 0
                    if stdout_size > int(normalized["max_stdout_bytes"]) or stderr_size > int(normalized["max_stderr_bytes"]):
                        log_limit_exceeded = True
                        _terminate_process_tree(child, group_id)
                        state = "failed"
                        break
                    time.sleep(0.05)
                return_code = child.returncode
                if state not in {"cancelled", "uncertain"}:
                    state = "completed" if return_code == 0 and not timed_out else "failed"
        write_process_result(
            operation_id,
            generation=generation,
            owner_nonce=owner_nonce,
            state=state,
            return_code=return_code,
            applied=False,
            timed_out=timed_out,
            log_limit_exceeded=log_limit_exceeded,
        )
        finalize_process_operation(operation_id, generation, owner_nonce, state=state)
    except BaseException:
        if child is not None and child.poll() is None:
            _terminate_process_tree(child, child.pid)
        try:
            write_process_result(
                operation_id,
                generation=generation,
                owner_nonce=owner_nonce,
                state="failed",
                return_code=return_code,
                applied=False,
                timed_out=timed_out,
                log_limit_exceeded=log_limit_exceeded,
            )
            finalize_process_operation(operation_id, generation, owner_nonce, state="failed")
        except Exception:
            pass


def start_bounded_command_worker(
    *,
    operation_id: str,
    acceptance_key: str,
    operation_kind: str,
    may_mutate: bool,
    config: Mapping[str, Any],
    project_id: str = "",
    session_id: str = "",
    tab_id: str = "",
    tab_revision: int = 0,
) -> dict[str, Any]:
    normalized = validate_process_worker_config(config)
    accepted = accept_process_operation(
        operation_id,
        operation_kind=operation_kind,
        may_mutate=may_mutate,
        acceptance_key=acceptance_key,
        project_id=project_id,
        session_id=session_id,
        tab_id=tab_id,
        tab_revision=tab_revision,
    )
    if not accepted.get("ok") or accepted.get("duplicate"):
        return {**accepted, "worker_started": False}
    generation = int(accepted.get("generation") or 0)
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=run_bounded_command_worker,
        args=(operation_id, generation, normalized),
        daemon=False,
    )
    try:
        process.start()
    except BaseException:
        # A launch failure is a known non-accepted execution result.  Mark it
        # failed rather than leaving an accepted operation permanently stuck.
        activated = activate_process_operation(operation_id, generation)
        if activated.get("ok"):
            nonce = str(activated.get("owner_nonce") or "")
            write_process_result(operation_id, generation=generation, owner_nonce=nonce, state="failed")
            finalize_process_operation(operation_id, generation, nonce, state="failed")
        return {**inspect_process_operation(operation_id), "ok": False, "status": "worker_start_failed", "worker_started": False}
    return {
        **inspect_process_operation(operation_id),
        "ok": True,
        "status": "worker_started",
        "worker_started": True,
        "worker_pid": process.pid,
        "worker_handle": process,
    }


def cancel_bounded_command_worker(operation_id: str, *, operator_confirmed: bool) -> dict[str, Any]:
    return request_process_operation_cancellation(operation_id, operator_confirmed=operator_confirmed)
