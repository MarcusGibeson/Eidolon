from __future__ import annotations

"""Hermetic, bounded verification runtime for v1250.2.

The helpers in this module run verifier commands in a clean external snapshot.
They deliberately disable bytecode, redirect runtime data and temporary files
outside the inspected source, terminate timed-out process groups, and emit only
content-free command evidence.  They do not authorize release or mutate the
selected project.
"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "v1250.2"
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "data",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
IGNORED_FILE_SUFFIXES = {".pyc", ".pyo"}
FORBIDDEN_RUNTIME_DIRECTORY_NAMES = {"data", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_RUNTIME_FILE_SUFFIXES = {".pyc", ".pyo"}

AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "independent_authority_granted": False,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.suffix.lower() in IGNORED_FILE_SUFFIXES:
            continue
        yield path


def source_signature(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).resolve()
    rows: list[str] = []
    byte_count = 0
    for path in _iter_source_files(root):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        byte_count += len(data)
        rows.append(f"{relative}:{len(data)}:{_sha256_bytes(data)}")
    return {
        "source_root_digest": _sha256_bytes(str(root).encode("utf-8")),
        "file_count": len(rows),
        "byte_count": byte_count,
        "tree_digest": _sha256_bytes("\n".join(rows).encode("utf-8")),
    }


def validate_external_path(path: str | Path, *, source_root: str | Path) -> dict[str, Any]:
    candidate = Path(path).resolve()
    source = Path(source_root).resolve()
    external = not _is_relative_to(candidate, source)
    return {
        "ok": external,
        "status": "external_path_valid" if external else "path_inside_source_blocked",
        "path_digest": _sha256_bytes(str(candidate).encode("utf-8")),
        "source_root_digest": _sha256_bytes(str(source).encode("utf-8")),
        "external_to_source": external,
        **AUTHORITY_FLAGS,
    }


def build_hermetic_environment(*, runtime_root: str | Path, source_root: str | Path, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    runtime = Path(runtime_root).resolve()
    source = Path(source_root).resolve()
    if _is_relative_to(runtime, source):
        raise ValueError("runtime_root_must_be_outside_source")
    data = runtime / "data"
    temp = runtime / "tmp"
    cache = runtime / "pycache"
    home = runtime / "home"
    for path in (data, temp, cache, home):
        path.mkdir(parents=True, exist_ok=True)
    env = dict(base_env or os.environ)
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(cache),
            "EIDOLON_DATA_DIR": str(data),
            "TMPDIR": str(temp),
            "TMP": str(temp),
            "TEMP": str(temp),
            "HOME": str(home),
            "USERPROFILE": str(home),
            "EIDOLON_VERIFICATION_HERMETIC": "1",
            "EIDOLON_VERIFICATION_SOURCE_ROOT": str(source),
        }
    )
    return env


def copy_clean_source_snapshot(*, source_root: str | Path, snapshot_root: str | Path) -> dict[str, Any]:
    source = Path(source_root).resolve()
    snapshot = Path(snapshot_root).resolve()
    if _is_relative_to(snapshot, source):
        raise ValueError("snapshot_root_must_be_outside_source")
    if snapshot.exists():
        shutil.rmtree(snapshot)
    snapshot.mkdir(parents=True, exist_ok=False)
    copied = 0
    byte_count = 0
    skipped = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts):
            skipped += 1
            continue
        target = snapshot / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file() or path.suffix.lower() in IGNORED_FILE_SUFFIXES:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
        byte_count += path.stat().st_size
    result = {
        "ok": True,
        "status": "clean_source_snapshot_ready",
        "contract_version": CONTRACT_VERSION,
        "copied_file_count": copied,
        "copied_byte_count": byte_count,
        "skipped_entry_count": skipped,
        "snapshot_external_to_source": not _is_relative_to(snapshot, source),
        "snapshot_signature": source_signature(snapshot),
        "source_signature": source_signature(source),
        "read_only_authoritative_source": True,
        **AUTHORITY_FLAGS,
    }
    result["snapshot_receipt_digest"] = _sha256_json(result)
    return result


def scan_forbidden_runtime_entries(root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    entries: list[dict[str, Any]] = []
    if base.exists():
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(base)
            reason = ""
            if path.is_dir() and path.name in FORBIDDEN_RUNTIME_DIRECTORY_NAMES:
                reason = "forbidden_runtime_directory"
            elif path.is_file() and path.suffix.lower() in FORBIDDEN_RUNTIME_FILE_SUFFIXES:
                reason = "forbidden_bytecode_file"
            if reason:
                entries.append(
                    {
                        "relative_path_digest": _sha256_bytes(relative.as_posix().encode("utf-8")),
                        "reason": reason,
                    }
                )
    return {
        "ok": not entries,
        "status": "runtime_debris_absent" if not entries else "runtime_debris_detected",
        "forbidden_entry_count": len(entries),
        "forbidden_entries": entries,
        **AUTHORITY_FLAGS,
    }


@dataclass(frozen=True)
class CommandResult:
    status: str
    returncode: int | None
    timed_out: bool
    elapsed_seconds: float
    stdout_sha256: str
    stderr_sha256: str
    stdout_byte_count: int
    stderr_byte_count: int
    parsed_json: Mapping[str, Any] | None
    command_digest: str
    process_group_terminated: bool
    residual_process_group_terminated: bool

    @property
    def ok(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ok": self.ok,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "elapsed_seconds": self.elapsed_seconds,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_byte_count": self.stdout_byte_count,
            "stderr_byte_count": self.stderr_byte_count,
            "parsed_json": dict(self.parsed_json) if isinstance(self.parsed_json, Mapping) else None,
            "command_digest": self.command_digest,
            "process_group_terminated": self.process_group_terminated,
            "residual_process_group_terminated": self.residual_process_group_terminated,
            **AUTHORITY_FLAGS,
        }


def _parse_last_json(stdout: bytes) -> Mapping[str, Any] | None:
    text = stdout.decode("utf-8", errors="replace")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            return dict(value)
    return None


def _windows_kill_on_close_job(process: subprocess.Popen[bytes]) -> tuple[Any, int] | None:
    """Put a child in a job whose descendants die when the handle closes."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = 0x00002000
        configured = kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        )
        assigned = configured and kernel32.AssignProcessToJobObject(
            job, wintypes.HANDLE(process._handle)
        )
        if not assigned:
            kernel32.CloseHandle(job)
            return None
        return kernel32, int(job)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _close_windows_job(job: tuple[Any, int] | None) -> bool:
    if job is None:
        return False
    kernel32, handle = job
    try:
        return bool(kernel32.CloseHandle(handle))
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def _terminate_process_group(process: subprocess.Popen[bytes]) -> bool:
    terminated = False
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=2,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
        terminated = True
    except (ProcessLookupError, PermissionError, subprocess.SubprocessError, OSError):
        try:
            process.kill()
            terminated = True
        except OSError:
            pass
    return terminated



def _terminate_residual_process_group(process: subprocess.Popen[bytes]) -> bool:
    """Terminate descendants that survived a successful direct-child exit."""
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP gives the direct child a group ID equal to
        # its PID. The group remains addressable while descendants survive,
        # even after the leader exits; taskkill's parent-tree lookup does not.
        try:
            os.kill(process.pid, signal.CTRL_BREAK_EVENT)
            time.sleep(0.1)
            return True
        except (ProcessLookupError, PermissionError, OSError, ValueError):
            pass
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=2,
            )
            return completed.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False
    try:
        os.killpg(process.pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    try:
        os.killpg(process.pid, signal.SIGKILL)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False

def run_bounded_command(
    command: Sequence[str],
    *,
    cwd: str | Path,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> CommandResult:
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise ValueError("command_must_be_nonempty_string_sequence")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds_must_be_positive")
    command_list = list(command)
    started = time.monotonic()
    creationflags = 0
    kwargs: dict[str, Any] = {"start_new_session": True}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs = {"creationflags": creationflags}
    timed_out = False
    terminated = False
    residual_terminated = False
    with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
        process = subprocess.Popen(
            command_list,
            cwd=str(Path(cwd).resolve()),
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            shell=False,
            **kwargs,
        )
        windows_job = _windows_kill_on_close_job(process)
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            terminated = _close_windows_job(windows_job)
            if not terminated:
                terminated = _terminate_process_group(process)
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except OSError:
                    pass
                process.wait()
                terminated = True
        else:
            residual_terminated = _close_windows_job(windows_job)
            if not residual_terminated:
                residual_terminated = _terminate_residual_process_group(process)
        stdout_file.flush()
        stderr_file.flush()
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read()
        stderr = stderr_file.read()
    elapsed = round(time.monotonic() - started, 6)
    parsed = _parse_last_json(stdout)
    if timed_out:
        status = "timeout"
    elif process.returncode == 0 and (parsed is None or parsed.get("ok", True) is True):
        status = "passed"
    else:
        status = "failed"
    return CommandResult(
        status=status,
        returncode=process.returncode,
        timed_out=timed_out,
        elapsed_seconds=elapsed,
        stdout_sha256=_sha256_bytes(stdout),
        stderr_sha256=_sha256_bytes(stderr),
        stdout_byte_count=len(stdout),
        stderr_byte_count=len(stderr),
        parsed_json=parsed,
        command_digest=_sha256_json(command_list),
        process_group_terminated=terminated,
        residual_process_group_terminated=residual_terminated,
    )


def atomic_write_json(path: str | Path, payload: Mapping[str, Any], *, source_root: str | Path) -> dict[str, Any]:
    target = Path(path).resolve()
    external = validate_external_path(target, source_root=source_root)
    if not external["ok"]:
        return {"ok": False, "status": "receipt_path_inside_source_blocked", **AUTHORITY_FLAGS}
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    encoded = (json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")
    with temp_path.open("wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, target)
    return {
        "ok": True,
        "status": "receipt_written",
        "receipt_path_digest": _sha256_bytes(str(target).encode("utf-8")),
        "receipt_sha256": _sha256_bytes(encoded),
        "receipt_byte_count": len(encoded),
        **AUTHORITY_FLAGS,
    }


def hermetic_runtime_contract() -> dict[str, Any]:
    result = {
        "ok": True,
        "status": "hermetic_verification_runtime_ready",
        "contract_version": CONTRACT_VERSION,
        "bytecode_disabled": True,
        "clean_external_snapshot_required": True,
        "runtime_paths_external_to_source_required": True,
        "shell_execution_forbidden": True,
        "bounded_process_group_timeout": True,
        "temporary_file_output_capture": True,
        "residual_process_group_cleanup": True,
        "partial_receipts_external_to_source_required": True,
        "source_immutability_required": True,
        "repository_size_thresholds_used": False,
        "ignored_directory_names": sorted(IGNORED_DIRECTORY_NAMES),
        "ignored_file_suffixes": sorted(IGNORED_FILE_SUFFIXES),
        "read_only_authoritative_source": True,
        **AUTHORITY_FLAGS,
    }
    result["contract_digest"] = _sha256_json(result)
    return result


__all__ = [
    "CONTRACT_VERSION",
    "IGNORED_DIRECTORY_NAMES",
    "IGNORED_FILE_SUFFIXES",
    "AUTHORITY_FLAGS",
    "CommandResult",
    "source_signature",
    "validate_external_path",
    "build_hermetic_environment",
    "copy_clean_source_snapshot",
    "scan_forbidden_runtime_entries",
    "run_bounded_command",
    "atomic_write_json",
    "hermetic_runtime_contract",
]
