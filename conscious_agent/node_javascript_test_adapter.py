from __future__ import annotations

"""Bounded Node and JavaScript test adapter.

v1207.0-v1207.8 provides one exact-workspace adapter for JavaScript and Node
projects.  It discovers only bounded project-owned tests, accepts only a strict
``node --test`` package-script grammar, runs syntax checks and tests under a
minimal capability guard, and persists content-free evidence in external
runtime storage.  It never installs dependencies, invokes a shell, reaches the
network, mutates the selected project, repairs failures, or grants release or
independent authority.
"""

import fnmatch
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from grounded_development_planning import load_grounded_plan
from isolated_implementation_workspace import _record_path, _verify_record, _workspace_root
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)
from structured_development_generation import _safe_relative

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1207.8"
MAX_NODE_LAUNCH_ATTEMPTS = 4
MAX_JAVASCRIPT_FILES = 96
MAX_JAVASCRIPT_FILE_BYTES = 512 * 1024
MAX_JAVASCRIPT_TOTAL_BYTES = 4 * 1024 * 1024
MAX_TEST_FILES = 24
MAX_TEST_TOTAL_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 512 * 1024
SYNTAX_TIMEOUT_SECONDS = 8
TEST_TIMEOUT_SECONDS = 24
NODE_PROBE_TIMEOUT_SECONDS = 4
OPERATION_STALE_SECONDS = 30
JAVASCRIPT_SUFFIXES = (".js", ".mjs", ".cjs")
TEST_SUFFIXES = (
    ".test.js", ".test.mjs", ".test.cjs",
    ".spec.js", ".spec.mjs", ".spec.cjs",
)
TEST_DIRS = {"test", "tests", "__tests__"}
SUPPORTED_PROJECT_KINDS = {
    "new_javascript_tool_project",
    "javascript_tool_project",
    "javascript_or_web_project",
    "new_small_web_project",
    "static_web_project",
}
FORBIDDEN_MODULES = {
    "http", "https", "http2", "net", "tls", "dgram", "dns", "dns/promises",
    "child_process", "worker_threads", "cluster", "inspector", "repl",
}
FORBIDDEN_GLOBAL_PATTERNS = (
    re.compile(r"\bprocess\s*\.\s*binding\s*\("),
    re.compile(r"\bprocess\s*\.\s*dlopen\s*\("),
    re.compile(r"\bimport\s*\(\s*(?!['\"])"),
)
ALLOWED_TEST_FLAGS = {"--test", "--test-concurrency=1"}


def _result_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "node_javascript_test_results" / proposal_id / f"revision-{int(revision)}.json"


def _operation_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "node_javascript_test_operations" / proposal_id / f"revision-{int(revision)}.json"


def _private_guard_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "node_javascript_private" / proposal_id / f"revision-{int(revision)}" / "capability-guard.cjs"


def _private_home(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "node_javascript_private" / proposal_id / f"revision-{int(revision)}" / "home"


def _record_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("node_javascript_test_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "node_javascript_test_digest"}))


def _operation_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("operation_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "operation_digest"}))


def _write_operation(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(payload)
    record["operation_digest"] = _digest(record)
    _atomic_json(path, record)
    return record


def _platform_family() -> str:
    name = platform.system().casefold()
    if name.startswith("win"):
        return "windows"
    if name == "darwin":
        return "macos"
    return "linux"


def _node_candidates(explicit: str | None = None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def add(source: str, value: str | None) -> None:
        if not value:
            return
        text = str(value)
        if text and all(existing != text for _, existing in rows):
            rows.append((source, text))

    add("explicit", explicit)
    add("environment", os.environ.get("EIDOLON_NODE_EXECUTABLE"))
    for name in ("node", "nodejs"):
        add("path", shutil.which(name))
    family = _platform_family()
    if family == "windows":
        roots = (
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        )
        suffixes = (
            r"nodejs\node.exe",
            r"Programs\nodejs\node.exe",
        )
        for root in roots:
            for suffix in suffixes:
                add("platform_default", str(Path(root) / suffix) if root else None)
    elif family == "macos":
        for value in ("/opt/homebrew/bin/node", "/usr/local/bin/node", "/usr/bin/node"):
            add("platform_default", value)
    else:
        for value in ("/usr/bin/node", "/usr/local/bin/node", "/opt/node/bin/node"):
            add("platform_default", value)
    return rows[:MAX_NODE_LAUNCH_ATTEMPTS]


def _path_digest(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()


def _diagnostic_digest(*parts: object) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()


def _is_test_path(relative_path: str) -> bool:
    path = Path(relative_path)
    return bool(path.suffix in JAVASCRIPT_SUFFIXES and (
        relative_path.endswith(TEST_SUFFIXES)
        or any(part.casefold() in TEST_DIRS for part in path.parts[:-1])
    ))


def _read_workspace_sources(root: Path, workspace: Mapping[str, Any]) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = 0
    for item in workspace.get("files") or []:
        relative = str(item.get("relative_path") or "")
        if relative == "package.json" or relative.endswith(JAVASCRIPT_SUFFIXES):
            try:
                safe = _safe_relative(relative)
            except ValueError:
                return None, {"ok": False, "status": "node_javascript_path_rejected"}
            path = root / safe
            if not path.is_file() or path.is_symlink():
                return None, {"ok": False, "status": "node_javascript_file_rejected"}
            size = path.stat().st_size
            if size > MAX_JAVASCRIPT_FILE_BYTES:
                return None, {"ok": False, "status": "node_javascript_budget_exceeded"}
            total += size
            if total > MAX_JAVASCRIPT_TOTAL_BYTES:
                return None, {"ok": False, "status": "node_javascript_budget_exceeded"}
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return None, {"ok": False, "status": "node_javascript_source_unreadable"}
            rows.append({
                "relative_path": safe,
                "relative_path_digest": _path_digest(safe),
                "path": path,
                "size_bytes": size,
                "text": text,
                "is_test": _is_test_path(safe),
            })
            if len(rows) > MAX_JAVASCRIPT_FILES + 1:
                return None, {"ok": False, "status": "node_javascript_budget_exceeded"}
    javascript_rows = [row for row in rows if str(row["relative_path"]).endswith(JAVASCRIPT_SUFFIXES)]
    if len(javascript_rows) > MAX_JAVASCRIPT_FILES:
        return None, {"ok": False, "status": "node_javascript_budget_exceeded"}
    test_rows = [row for row in javascript_rows if row["is_test"]]
    if len(test_rows) > MAX_TEST_FILES or sum(int(row["size_bytes"]) for row in test_rows) > MAX_TEST_TOTAL_BYTES:
        return None, {"ok": False, "status": "node_javascript_test_budget_exceeded"}
    return rows, {}


def _module_tokens(text: str) -> Iterable[str]:
    patterns = (
        r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        r"\bfrom\s*['\"]([^'\"]+)['\"]",
        r"\bimport\s*['\"]([^'\"]+)['\"]",
        r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            yield match.group(1)


def _capability_contract_ok(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    for row in rows:
        text = str(row.get("text") or "")
        for module in _module_tokens(text):
            normalized = module[5:] if module.startswith("node:") else module
            if normalized in FORBIDDEN_MODULES:
                return False, str(row.get("relative_path_digest") or "")
        if any(pattern.search(text) for pattern in FORBIDDEN_GLOBAL_PATTERNS):
            return False, str(row.get("relative_path_digest") or "")
    return True, ""


def _parse_package_test_script(package_text: str, discovered: Sequence[str]) -> tuple[list[str] | None, dict[str, Any]]:
    try:
        package = json.loads(package_text)
    except json.JSONDecodeError:
        return None, {"ok": False, "status": "node_package_json_invalid"}
    script = (package.get("scripts") or {}).get("test") if isinstance(package, dict) else None
    if script is None:
        return list(discovered), {"package_test_script_present": False, "package_test_script_used": False}
    if not isinstance(script, str) or not script.strip() or len(script) > 256:
        return None, {"ok": False, "status": "node_test_script_unsupported"}
    try:
        tokens = shlex.split(script, posix=True)
    except ValueError:
        return None, {"ok": False, "status": "node_test_script_unsupported"}
    if not tokens or tokens[0] not in {"node", "nodejs"}:
        return None, {"ok": False, "status": "node_test_script_unsupported"}
    flags: list[str] = []
    selectors: list[str] = []
    for token in tokens[1:]:
        if token.startswith("-"):
            if token not in ALLOWED_TEST_FLAGS:
                return None, {"ok": False, "status": "node_test_script_unsupported"}
            flags.append(token)
        else:
            if token.startswith(("/", "\\")) or ":" in token or ".." in Path(token).parts:
                return None, {"ok": False, "status": "node_test_script_unsupported"}
            selectors.append(token.replace("\\", "/"))
    if "--test" not in flags:
        return None, {"ok": False, "status": "node_test_script_unsupported"}
    selected: list[str] = []
    if selectors:
        for selector in selectors:
            matches = [path for path in discovered if path == selector or fnmatch.fnmatchcase(path, selector)]
            for path in matches:
                if path not in selected:
                    selected.append(path)
        if not selected:
            return None, {"ok": False, "status": "node_test_script_selected_no_bounded_tests"}
    else:
        selected = list(discovered)
    return selected, {
        "package_test_script_present": True,
        "package_test_script_used": True,
        "package_test_script_digest": hashlib.sha256(script.encode("utf-8")).hexdigest(),
    }


def _write_capability_guard(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    modules = sorted(FORBIDDEN_MODULES)
    source = """'use strict';
const Module = require('module');
const blocked = new Set(%s);
const originalLoad = Module._load;
Module._load = function(request, parent, isMain) {
  const normalized = String(request || '').replace(/^node:/, '');
  if (blocked.has(normalized)) throw new Error('eidolon_node_capability_blocked');
  return originalLoad.apply(this, arguments);
};
const deny = function(){ throw new Error('eidolon_network_capability_blocked'); };
for (const name of ['fetch','WebSocket','EventSource']) {
  try { Object.defineProperty(globalThis, name, {value: deny, writable: false, configurable: false}); } catch (_) {}
}
const fs = require('fs');
const pathModule = require('path');
const scratch = pathModule.resolve(process.env.EIDOLON_TEST_SCRATCH || '');
const allowedPath = value => {
  if (typeof value === 'number') return true;
  const resolved = pathModule.resolve(String(value));
  return resolved === scratch || resolved.startsWith(scratch + pathModule.sep);
};
const rejectPath = value => { if (!allowedPath(value)) throw new Error('eidolon_node_write_blocked'); };
const wrapOnePath = (object, name) => {
  if (typeof object[name] !== 'function') return;
  const original = object[name];
  object[name] = function(target, ...args) { rejectPath(target); return original.call(this, target, ...args); };
};
const wrapTwoPaths = (object, name) => {
  if (typeof object[name] !== 'function') return;
  const original = object[name];
  object[name] = function(source, target, ...args) { rejectPath(source); rejectPath(target); return original.call(this, source, target, ...args); };
};
for (const name of ['writeFile','writeFileSync','appendFile','appendFileSync','truncate','truncateSync','unlink','unlinkSync','rm','rmSync','rmdir','rmdirSync','mkdir','mkdirSync','chmod','chmodSync','chown','chownSync','createWriteStream']) wrapOnePath(fs, name);
for (const name of ['copyFile','copyFileSync','rename','renameSync','link','linkSync','symlink','symlinkSync']) wrapTwoPaths(fs, name);
const writeFlag = flag => typeof flag === 'string' ? /[wa+]/.test(flag) : Boolean(Number(flag) & (fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_APPEND | fs.constants.O_CREAT | fs.constants.O_TRUNC));
for (const name of ['open','openSync']) {
  const original = fs[name];
  fs[name] = function(target, flags, ...args) { if (writeFlag(flags)) rejectPath(target); return original.call(this, target, flags, ...args); };
}
if (fs.promises) {
  for (const name of ['writeFile','appendFile','truncate','unlink','rm','rmdir','mkdir','chmod','chown']) wrapOnePath(fs.promises, name);
  for (const name of ['copyFile','rename','link','symlink']) wrapTwoPaths(fs.promises, name);
  if (typeof fs.promises.open === 'function') {
    const originalOpen = fs.promises.open;
    fs.promises.open = function(target, flags, ...args) { if (writeFlag(flags)) rejectPath(target); return originalOpen.call(this, target, flags, ...args); };
  }
}
""" % json.dumps(modules, separators=(",", ":"))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(source, encoding="utf-8", newline="")
    os.replace(tmp, path)


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _run_bounded_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=str(cwd),
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=(os.name != "nt"),
            creationflags=creationflags,
        )
    except OSError as error:
        return {
            "passed": False,
            "exit_class": "spawn_failed",
            "output_digest": _diagnostic_digest(type(error).__name__),
            "output_bytes": 0,
            "output_limit_exceeded": False,
            "cleanup_confirmed": True,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }

    lock = threading.Lock()
    total = {"bytes": 0}
    limit_exceeded = threading.Event()
    digests = {"stdout": hashlib.sha256(), "stderr": hashlib.sha256()}

    def pump(name: str, stream) -> None:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            digests[name].update(chunk)
            with lock:
                total["bytes"] += len(chunk)
                if total["bytes"] > MAX_OUTPUT_BYTES:
                    limit_exceeded.set()
            if limit_exceeded.is_set():
                _terminate_process(process)
                break

    threads = [
        threading.Thread(target=pump, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=pump, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
    for thread in threads:
        thread.join(timeout=3)
    cleanup_confirmed = process.poll() is not None
    if limit_exceeded.is_set():
        exit_class = "output_limit"
    elif timed_out:
        exit_class = "timeout"
    elif process.returncode == 0:
        exit_class = "zero"
    else:
        exit_class = "nonzero"
    return {
        "passed": exit_class == "zero",
        "exit_class": exit_class,
        "output_digest": _diagnostic_digest(
            digests["stdout"].hexdigest(),
            digests["stderr"].hexdigest(),
            total["bytes"],
            process.returncode,
        ),
        "output_bytes": min(total["bytes"], MAX_OUTPUT_BYTES + 1),
        "output_limit_exceeded": bool(limit_exceeded.is_set()),
        "cleanup_confirmed": cleanup_confirmed,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def _minimal_environment(node_executable: str, home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    scratch = home / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": str(Path(node_executable).parent),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "TMPDIR": str(home),
        "TMP": str(home),
        "TEMP": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "CI": "1",
        "NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "NODE_NO_WARNINGS": "1",
        "NODE_PATH": "",
        "EIDOLON_TEST_SCRATCH": str(scratch),
    }
    if os.name == "nt":
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
            if os.environ.get(key):
                env[key] = os.environ[key]
    return env


def _select_node(
    candidates: Sequence[tuple[str, str]],
    *,
    cwd: Path,
    home: Path,
) -> tuple[str | None, str, list[str], int, bool]:
    failures: list[str] = []
    cleanup = True
    attempts = 0
    for source_class, executable in candidates:
        attempts += 1
        result = _run_bounded_command(
            [executable, "--version"],
            cwd=cwd,
            env=_minimal_environment(executable, home),
            timeout_seconds=NODE_PROBE_TIMEOUT_SECONDS,
        )
        cleanup = cleanup and bool(result.get("cleanup_confirmed"))
        if result.get("passed"):
            return executable, source_class, failures, attempts, cleanup
        failures.append(str(result.get("output_digest") or ""))
    return None, "none", failures, attempts, cleanup


def _supports_test_concurrency(node: str, *, cwd: Path, env: Mapping[str, str]) -> bool:
    try:
        completed = subprocess.run(
            [node, "--help"],
            cwd=str(cwd),
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=NODE_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0 and b"--test-concurrency" in completed.stdout


def _failure_result(
    *,
    proposal_id: str,
    revision: int,
    revision_digest: str,
    planning_digest: str,
    generation_digest: str,
    workspace_digest: str,
    approval_receipt_digest: str,
    status: str,
    outcome_class: str,
    operation_recovery_count: int,
    platform_family: str,
    node_source_class: str = "none",
    launch_attempt_count: int = 0,
    launch_failure_digests: Sequence[str] = (),
    cleanup_confirmed: bool = True,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "status": status,
        "passed": False,
        "outcome_class": outcome_class,
        "proposal_id": proposal_id,
        "proposal_revision": int(revision),
        "proposal_revision_digest": revision_digest,
        "planning_digest": planning_digest,
        "generation_digest": generation_digest,
        "workspace_digest": workspace_digest,
        "approval_receipt_digest": approval_receipt_digest,
        "platform_family": platform_family,
        "node_source_class": node_source_class,
        "launch_attempt_count": int(launch_attempt_count),
        "launch_failure_digests": list(launch_failure_digests),
        "operation_recovery_count": int(operation_recovery_count),
        "node_executed": False,
        "syntax_file_count": 0,
        "test_file_count": 0,
        "command_count": 0,
        "passed_command_count": 0,
        "failed_command_count": 0,
        "cleanup_confirmed": bool(cleanup_confirmed),
        "network_allowed": False,
        "dependencies_installed": False,
        "shell_executed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "implementation_applied": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "rollback_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "private_path_included": False,
        "private_content_included": False,
        "raw_output_included": False,
        "content_free": True,
        "sandbox_backend": "node-preload-capability-guard",
        "filesystem_write_scope": "private_scratch_only",
        "os_isolation_provided": False,
        "security_boundary": "language_runtime_policy_not_os_container",
    }
    if extra:
        record.update(dict(extra))
    record["node_javascript_test_digest"] = _digest(record)
    return record


def run_or_resume_node_javascript_tests(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    runtime_root=None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    """Execute or resume one bounded Node/JavaScript test operation."""

    with _proposal_lock(proposal_id, runtime_root):
        plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
        if not plan or plan.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_or_missing_grounded_plan"}
        project_kind = str(plan.get("project_kind") or "")
        if project_kind not in SUPPORTED_PROJECT_KINDS:
            return {"ok": False, "status": "node_javascript_adapter_project_kind_unsupported"}

        workspace = _read_json(_record_path(proposal_id, expected_revision, runtime_root))
        if not workspace:
            return {"ok": False, "status": "workspace_missing"}
        if workspace.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if workspace.get("workspace_digest") != expected_workspace_digest:
            return {"ok": False, "status": "stale_workspace_revision"}
        generation_digest = str(workspace.get("generation_digest") or "")
        planning_digest = str(workspace.get("planning_digest") or "")
        if planning_digest != plan.get("planning_digest"):
            return {"ok": False, "status": "stale_workspace_planning_binding"}
        root = _workspace_root(proposal_id, expected_revision, generation_digest, runtime_root)
        if not _verify_record(workspace, root):
            return {"ok": False, "status": "workspace_record_invalid"}

        result_path = _result_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(result_path)
        if existing:
            bindings = (
                existing.get("proposal_revision_digest") == expected_revision_digest
                and existing.get("workspace_digest") == expected_workspace_digest
                and existing.get("planning_digest") == planning_digest
                and existing.get("generation_digest") == generation_digest
            )
            if bindings and _record_valid(existing):
                return {**existing, "operation_status": "resumed"}
            return {"ok": False, "status": "node_javascript_test_record_invalid"}

        operation_path = _operation_path(proposal_id, expected_revision, runtime_root)
        operation = _read_json(operation_path)
        recovery_count = 0
        attempt_count = 1
        if operation:
            if not _operation_valid(operation):
                return {"ok": False, "status": "node_javascript_operation_invalid"}
            if (
                operation.get("proposal_revision_digest") != expected_revision_digest
                or operation.get("workspace_digest") != expected_workspace_digest
                or operation.get("planning_digest") != planning_digest
                or operation.get("generation_digest") != generation_digest
            ):
                return {"ok": False, "status": "stale_node_javascript_operation"}
            if operation.get("phase") == "sealed":
                return {"ok": False, "status": "node_javascript_result_missing"}
            age = max(0.0, time.time() - float(operation.get("updated_at_epoch") or 0.0))
            if age < OPERATION_STALE_SECONDS:
                return {"ok": False, "status": "node_javascript_operation_in_progress"}
            recovery_count = int(operation.get("recovery_count") or 0) + 1
            attempt_count = int(operation.get("attempt_count") or 0) + 1

        operation = _write_operation(operation_path, {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "phase": "prepared",
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "planning_digest": planning_digest,
            "generation_digest": generation_digest,
            "workspace_digest": expected_workspace_digest,
            "attempt_count": attempt_count,
            "recovery_count": recovery_count,
            "updated_at_epoch": time.time(),
            "network_allowed": False,
            "dependencies_installed": False,
            "shell_executed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        })

        platform_family = _platform_family()
        rows, error = _read_workspace_sources(root, workspace)
        if rows is None:
            record = _failure_result(
                proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                planning_digest=planning_digest, generation_digest=generation_digest,
                workspace_digest=expected_workspace_digest, approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""),
                status=str(error.get("status") or "node_javascript_source_rejected"), outcome_class="contract_rejected",
                operation_recovery_count=recovery_count, platform_family=platform_family,
            )
        else:
            js_rows = [row for row in rows if str(row["relative_path"]).endswith(JAVASCRIPT_SUFFIXES)]
            test_rows = [row for row in js_rows if row["is_test"]]
            test_paths = [str(row["relative_path"]) for row in test_rows]
            package_rows = [row for row in rows if row["relative_path"] == "package.json"]
            package_info: dict[str, Any] = {"package_test_script_present": False, "package_test_script_used": False}
            if package_rows:
                selected_tests, package_info = _parse_package_test_script(str(package_rows[0]["text"]), test_paths)
                if selected_tests is None:
                    record = _failure_result(
                        proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                        planning_digest=planning_digest, generation_digest=generation_digest,
                        workspace_digest=expected_workspace_digest, approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""),
                        status=str(package_info.get("status") or "node_test_script_unsupported"), outcome_class="contract_rejected",
                        operation_recovery_count=recovery_count, platform_family=platform_family,
                        extra={"test_file_count": len(test_rows), **{k: v for k, v in package_info.items() if k != "ok"}},
                    )
                else:
                    test_paths = selected_tests
                    record = {}
            else:
                record = {}

            if not record:
                contract_ok, rejected_digest = _capability_contract_ok(js_rows)
                if not contract_ok:
                    record = _failure_result(
                        proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                        planning_digest=planning_digest, generation_digest=generation_digest,
                        workspace_digest=expected_workspace_digest, approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""),
                        status="node_javascript_capability_contract_rejected", outcome_class="contract_rejected",
                        operation_recovery_count=recovery_count, platform_family=platform_family,
                        extra={"rejected_path_digest": rejected_digest, "test_file_count": len(test_paths), **package_info},
                    )

            if not record and not test_paths:
                record = _failure_result(
                    proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                    planning_digest=planning_digest, generation_digest=generation_digest,
                    workspace_digest=expected_workspace_digest, approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""),
                    status="node_javascript_tests_not_found", outcome_class="tests_not_found",
                    operation_recovery_count=recovery_count, platform_family=platform_family,
                    extra={"syntax_file_count": len(js_rows), **package_info},
                )

            if not record:
                private_home = _private_home(proposal_id, expected_revision, runtime_root)
                node, source_class, launch_failures, launch_attempts, probe_cleanup = _select_node(
                    _node_candidates(node_executable), cwd=root, home=private_home,
                )
                if not node:
                    record = _failure_result(
                        proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                        planning_digest=planning_digest, generation_digest=generation_digest,
                        workspace_digest=expected_workspace_digest, approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""),
                        status="node_runtime_unavailable", outcome_class="node_unavailable",
                        operation_recovery_count=recovery_count, platform_family=platform_family,
                        node_source_class="none", launch_attempt_count=launch_attempts,
                        launch_failure_digests=launch_failures, cleanup_confirmed=probe_cleanup,
                        extra={"syntax_file_count": len(js_rows), "test_file_count": len(test_paths), **package_info},
                    )
                else:
                    guard = _private_guard_path(proposal_id, expected_revision, runtime_root)
                    _write_capability_guard(guard)
                    env = _minimal_environment(node, private_home)
                    command_results: list[dict[str, Any]] = []
                    cleanup_confirmed = probe_cleanup
                    syntax_passed = True
                    concurrency_supported = False
                    for row in js_rows:
                        command = _run_bounded_command(
                            [node, "--check", str(row["path"])],
                            cwd=root,
                            env=env,
                            timeout_seconds=SYNTAX_TIMEOUT_SECONDS,
                        )
                        cleanup_confirmed = cleanup_confirmed and bool(command.get("cleanup_confirmed"))
                        command_results.append({
                            "phase": "syntax",
                            "path_digest": str(row["relative_path_digest"]),
                            **command,
                        })
                        if not command.get("passed"):
                            syntax_passed = False
                            break
                    tests_passed = False
                    if syntax_passed:
                        selected_paths = [str(root / _safe_relative(path)) for path in test_paths]
                        concurrency_supported = _supports_test_concurrency(node, cwd=root, env=env)
                        test_argv = [node, "--require", str(guard), "--test"]
                        if concurrency_supported:
                            test_argv.append("--test-concurrency=1")
                        test_command = _run_bounded_command(
                            [*test_argv, *selected_paths],
                            cwd=root,
                            env=env,
                            timeout_seconds=TEST_TIMEOUT_SECONDS,
                        )
                        cleanup_confirmed = cleanup_confirmed and bool(test_command.get("cleanup_confirmed"))
                        command_results.append({
                            "phase": "tests",
                            "selection_digest": _digest([_path_digest(path) for path in test_paths]),
                            **test_command,
                        })
                        tests_passed = bool(test_command.get("passed"))
                    passed = syntax_passed and tests_passed and cleanup_confirmed
                    if not syntax_passed:
                        outcome_class = "syntax_failed"
                    elif not tests_passed:
                        test_exit = str(command_results[-1].get("exit_class") or "nonzero")
                        outcome_class = {
                            "timeout": "test_timeout",
                            "output_limit": "test_output_limit",
                            "spawn_failed": "test_spawn_failed",
                        }.get(test_exit, "tests_failed")
                    elif not cleanup_confirmed:
                        outcome_class = "cleanup_failed"
                    else:
                        outcome_class = "passed"
                    record = {
                        "schema_version": SCHEMA_VERSION,
                        "contract_version": CONTRACT_VERSION,
                        "ok": True,
                        "status": "node_javascript_test_adapter_passed" if passed else "node_javascript_test_adapter_failed",
                        "passed": passed,
                        "outcome_class": outcome_class,
                        "proposal_id": proposal_id,
                        "proposal_revision": int(expected_revision),
                        "proposal_revision_digest": expected_revision_digest,
                        "planning_digest": planning_digest,
                        "generation_digest": generation_digest,
                        "workspace_digest": expected_workspace_digest,
                        "approval_receipt_digest": workspace.get("approval_receipt_digest"),
                        "project_kind": project_kind,
                        "platform_family": platform_family,
                        "node_source_class": source_class,
                        "launch_attempt_count": launch_attempts,
                        "launch_failure_digests": launch_failures,
                        "operation_recovery_count": recovery_count,
                        "node_executed": True,
                        "syntax_file_count": len(js_rows),
                        "test_file_count": len(test_paths),
                        "test_selection_digest": _digest([_path_digest(path) for path in test_paths]),
                        "test_concurrency_supported": concurrency_supported,
                        "command_count": len(command_results),
                        "passed_command_count": sum(1 for item in command_results if item.get("passed")),
                        "failed_command_count": sum(1 for item in command_results if not item.get("passed")),
                        "command_results": command_results,
                        "cleanup_confirmed": cleanup_confirmed,
                        **package_info,
                        "network_allowed": False,
                        "dependencies_installed": False,
                        "shell_executed": False,
                        "selected_project_modified": False,
                        "source_modified": False,
                        "implementation_applied": False,
                        "repair_authorized": False,
                        "apply_authorized": False,
                        "rollback_authorized": False,
                        "release_authorized": False,
                        "authority_granted": False,
                        "private_path_included": False,
                        "private_content_included": False,
                        "raw_output_included": False,
                        "content_free": True,
                        "sandbox_backend": "node-preload-capability-guard",
                        "filesystem_write_scope": "private_scratch_only",
                        "os_isolation_provided": False,
                        "security_boundary": "language_runtime_policy_not_os_container",
                    }
                    record["node_javascript_test_digest"] = _digest(record)

        _atomic_json(result_path, record)
        sealed_operation = _write_operation(operation_path, {
            **{k: v for k, v in operation.items() if k != "operation_digest"},
            "phase": "sealed",
            "result_digest": record["node_javascript_test_digest"],
            "result_status": record["status"],
            "result_passed": bool(record.get("passed")),
            "cleanup_confirmed": bool(record.get("cleanup_confirmed")),
            "updated_at_epoch": time.time(),
        })
        return {
            **record,
            "operation_status": "created",
            "operation_digest": sealed_operation["operation_digest"],
        }


def public_node_javascript_test_result(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "ok", "status", "contract_version", "passed", "outcome_class", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "planning_digest", "generation_digest",
        "workspace_digest", "approval_receipt_digest", "project_kind", "platform_family",
        "node_source_class", "launch_attempt_count", "launch_failure_digests",
        "operation_recovery_count", "node_executed", "syntax_file_count", "test_file_count",
        "test_selection_digest", "test_concurrency_supported", "command_count", "passed_command_count", "failed_command_count",
        "command_results", "cleanup_confirmed", "package_test_script_present",
        "package_test_script_used", "package_test_script_digest", "rejected_path_digest",
        "sandbox_backend", "filesystem_write_scope", "os_isolation_provided", "security_boundary",
        "node_javascript_test_digest", "network_allowed", "dependencies_installed",
        "shell_executed", "selected_project_modified", "source_modified", "implementation_applied",
        "repair_authorized", "apply_authorized", "rollback_authorized", "release_authorized",
        "authority_granted", "content_free",
    )
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "node_executable_path_exposed": False,
        "package_script_text_exposed": False,
    })
    return public
