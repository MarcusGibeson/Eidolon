from __future__ import annotations

"""Bounded Python project test adapter for v1208.0-v1208.8.

The adapter validates exact approved/workspace lineage, discovers bounded
project-owned Python tests, selects stdlib unittest or an already-installed
pytest runner, executes under a minimal environment and capability guard, and
persists only content-free evidence in external runtime storage. It never
installs dependencies, uses a shell, reaches the network, mutates the selected
project, repairs failures, or grants release/independent authority.
"""

import ast
import hashlib
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from grounded_development_planning import load_grounded_plan
from isolated_implementation_workspace import _record_path, _verify_record, _workspace_root
from node_javascript_test_adapter import _run_bounded_command
from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from structured_development_generation import _safe_relative

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1208.8"
MAX_PYTHON_LAUNCH_ATTEMPTS = 4
MAX_PYTHON_FILES = 128
MAX_PYTHON_FILE_BYTES = 512 * 1024
MAX_PYTHON_TOTAL_BYTES = 4 * 1024 * 1024
MAX_TEST_FILES = 24
MAX_TEST_TOTAL_BYTES = 2 * 1024 * 1024
SYNTAX_TIMEOUT_SECONDS = 8
TEST_TIMEOUT_SECONDS = 30
PYTHON_PROBE_TIMEOUT_SECONDS = 5
OPERATION_STALE_SECONDS = 30
SUPPORTED_PROJECT_KINDS = {"new_python_cli_project", "python_cli_project", "python_project"}
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg"}
FORBIDDEN_IMPORT_ROOTS = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib",
    "subprocess", "multiprocessing", "ctypes", "cffi", "pdb", "bdb",
    "asyncio.subprocess", "resource",
}
FORBIDDEN_CALLS = {
    "os.system", "os.popen", "os.spawnl", "os.spawnle", "os.spawnlp", "os.spawnlpe",
    "os.spawnv", "os.spawnve", "os.spawnvp", "os.spawnvpe", "os.execv", "os.execve",
    "os.execvp", "os.execvpe", "asyncio.create_subprocess_exec", "asyncio.create_subprocess_shell",
    "importlib.import_module", "builtins.__import__",
}


def _result_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_test_adapter_results" / proposal_id / f"revision-{int(revision)}.json"


def _operation_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_test_adapter_operations" / proposal_id / f"revision-{int(revision)}.json"


def _private_home(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_test_adapter_private" / proposal_id / f"revision-{int(revision)}"


def _record_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("python_test_adapter_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "python_test_adapter_digest"}))


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


def _python_candidates(explicit: str | None = None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def add(source: str, value: str | None) -> None:
        if not value:
            return
        text = str(value)
        if text and all(existing != text for _, existing in rows):
            rows.append((source, text))

    add("explicit", explicit)
    add("environment", os.environ.get("EIDOLON_PYTHON_EXECUTABLE"))
    add("current_interpreter", sys.executable)
    for name in ("python", "python3", "py"):
        add("path", shutil.which(name))
    family = _platform_family()
    if family == "windows":
        roots = (os.environ.get("LOCALAPPDATA"), os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"))
        for root in roots:
            if root:
                add("platform_default", str(Path(root) / "Programs" / "Python" / "Python311" / "python.exe"))
                add("platform_default", str(Path(root) / "Python311" / "python.exe"))
    elif family == "macos":
        for value in ("/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"):
            add("platform_default", value)
    else:
        for value in ("/usr/bin/python3", "/usr/local/bin/python3", "/opt/pyvenv/bin/python"):
            add("platform_default", value)
    return rows[:MAX_PYTHON_LAUNCH_ATTEMPTS]


def _path_digest(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()


def _diagnostic_digest(*parts: object) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8", errors="replace")); h.update(b"\0")
    return h.hexdigest()


def _is_test_path(relative_path: str) -> bool:
    path = Path(relative_path)
    if path.suffix.casefold() != ".py":
        return False
    name = path.name.casefold()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith("_tests.py")
        or any(part.casefold() in {"test", "tests"} for part in path.parts[:-1])
    )


def _read_workspace_sources(root: Path, workspace: Mapping[str, Any]) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = 0
    for item in workspace.get("files") or []:
        relative = str(item.get("relative_path") or "")
        if not (relative.endswith(".py") or Path(relative).name in CONFIG_NAMES):
            continue
        try:
            safe = _safe_relative(relative)
        except ValueError:
            return None, {"ok": False, "status": "python_test_path_rejected"}
        path = root / safe
        if not path.is_file() or path.is_symlink():
            return None, {"ok": False, "status": "python_test_file_rejected"}
        size = path.stat().st_size
        if size > MAX_PYTHON_FILE_BYTES:
            return None, {"ok": False, "status": "python_test_budget_exceeded"}
        total += size
        if total > MAX_PYTHON_TOTAL_BYTES:
            return None, {"ok": False, "status": "python_test_budget_exceeded"}
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None, {"ok": False, "status": "python_test_source_unreadable"}
        rows.append({"relative_path": safe, "relative_path_digest": _path_digest(safe), "path": path, "size_bytes": size, "text": text, "is_test": _is_test_path(safe)})
    py_rows = [row for row in rows if str(row["relative_path"]).endswith(".py")]
    tests = [row for row in py_rows if row["is_test"]]
    if len(py_rows) > MAX_PYTHON_FILES:
        return None, {"ok": False, "status": "python_test_budget_exceeded"}
    if len(tests) > MAX_TEST_FILES or sum(int(row["size_bytes"]) for row in tests) > MAX_TEST_TOTAL_BYTES:
        return None, {"ok": False, "status": "python_test_budget_exceeded"}
    return rows, {}


def _qualified_name(node: ast.AST) -> str:
    parts: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr); current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _capability_contract_ok(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    for row in rows:
        if not str(row.get("relative_path") or "").endswith(".py"):
            continue
        try:
            tree = ast.parse(str(row.get("text") or ""))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                root = name.split(".", 1)[0]
                if name in FORBIDDEN_IMPORT_ROOTS or root in FORBIDDEN_IMPORT_ROOTS:
                    return False, str(row.get("relative_path_digest") or "")
            if isinstance(node, ast.Call):
                qname = _qualified_name(node.func)
                if qname in FORBIDDEN_CALLS or qname.startswith("subprocess.") or qname.startswith("multiprocessing."):
                    return False, str(row.get("relative_path_digest") or "")
    return True, ""


def _preferred_runner(rows: Sequence[Mapping[str, Any]]) -> str:
    for row in rows:
        relative = str(row.get("relative_path") or "")
        text = str(row.get("text") or "")
        if relative in {"pytest.ini", "conftest.py"} or "[tool.pytest.ini_options]" in text:
            return "pytest"
        if relative.endswith(".py"):
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) and any(alias.name.split(".", 1)[0] == "pytest" for alias in node.names):
                    return "pytest"
                if isinstance(node, ast.ImportFrom) and (node.module or "").split(".", 1)[0] == "pytest":
                    return "pytest"
    return "unittest"


def _minimal_environment(python_executable: str, private: Path) -> dict[str, str]:
    home = private / "home"; temp = private / "temp"
    home.mkdir(parents=True, exist_ok=True); temp.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": str(Path(python_executable).parent), "HOME": str(home), "USERPROFILE": str(home),
        "TMPDIR": str(temp), "TMP": str(temp), "TEMP": str(temp), "LANG": "C", "LC_ALL": "C",
        "TZ": "UTC", "CI": "1", "NO_COLOR": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1", "PYTHONHASHSEED": "0", "PYTEST_ADDOPTS": "-p no:cacheprovider", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    if os.name == "nt":
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
            if os.environ.get(key): env[key] = os.environ[key]
    return env


def _select_python(candidates: Sequence[tuple[str, str]], *, cwd: Path, private: Path) -> tuple[str | None, str, list[str], int, bool]:
    failures: list[str] = []; cleanup = True; attempts = 0
    for source_class, executable in candidates:
        attempts += 1
        result = _run_bounded_command([executable, "-I", "-B", "--version"], cwd=cwd, env=_minimal_environment(executable, private), timeout_seconds=PYTHON_PROBE_TIMEOUT_SECONDS)
        cleanup = cleanup and bool(result.get("cleanup_confirmed"))
        if result.get("passed"):
            return executable, source_class, failures, attempts, cleanup
        failures.append(str(result.get("output_digest") or ""))
    return None, "none", failures, attempts, cleanup


def _runner_source(runner: str) -> str:
    common = r'''
import builtins, os, pathlib, runpy, sys, types, unittest
root=pathlib.Path(sys.argv[1]).resolve(); scratch=pathlib.Path(sys.argv[2]).resolve(); root_s=os.path.abspath(str(root)); scratch_s=os.path.abspath(str(scratch)); selected=sys.argv[3:]
blocked={'socket','ssl','http','urllib','ftplib','smtplib','telnetlib','subprocess','multiprocessing','ctypes','cffi','pdb','bdb','resource'}
# Pytest imports colorama only for a Windows console workaround. A no-op stub
# avoids loading ctypes before project tests while output coloring is disabled.
sys.modules.setdefault('colorama',types.ModuleType('colorama'))
def inside(path,base):
    try: return os.path.commonpath([os.path.abspath(os.fsdecode(path)),base])==base
    except (TypeError,ValueError,OSError): return False
def audit_guard(event,args):
    if event=='open':
        path=args[0] if args else None; mode=args[1] if len(args)>1 else None; flags=args[2] if len(args)>2 else 0
        writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_TRUNC)))
        if writing and path != os.devnull and not isinstance(path,int) and not inside(path,scratch_s): raise RuntimeError('eidolon_python_write_blocked')
    elif event in {'os.remove','os.rmdir','os.mkdir','os.chmod','os.chown','os.truncate','os.unlink'}:
        if args and not inside(args[0],scratch_s): raise RuntimeError('eidolon_python_write_blocked')
    elif event in {'os.rename','os.replace','os.link','os.symlink'}:
        if len(args)<2 or not inside(args[0],scratch_s) or not inside(args[1],scratch_s): raise RuntimeError('eidolon_python_write_blocked')
    elif event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.posix_spawnp','ctypes.dlopen'}:
        raise RuntimeError('eidolon_python_capability_blocked')
sys.addaudithook(audit_guard)
_original_import=builtins.__import__
def guarded_import(name,globals=None,locals=None,fromlist=(),level=0):
    origin=(globals or {}).get('__file__') if isinstance(globals,dict) else None
    project_origin=False
    if origin:
        try: project_origin=os.path.commonpath([os.path.abspath(str(origin)),root_s])==root_s
        except (ValueError,OSError): pass
    if project_origin and str(name).split('.',1)[0] in blocked: raise RuntimeError('eidolon_python_capability_blocked')
    return _original_import(name,globals,locals,fromlist,level)
builtins.__import__=guarded_import
_original_open=builtins.open
def guarded_open(file,mode='r',*args,**kwargs):
    if any(flag in str(mode) for flag in 'wax+'):
        path=os.path.abspath(os.fspath(file))
        try: allowed=os.path.commonpath([path,scratch_s])==scratch_s
        except (ValueError,OSError): allowed=False
        if path==os.path.abspath(os.devnull): allowed=True
        if not allowed: raise RuntimeError('eidolon_python_write_blocked')
    return _original_open(file,mode,*args,**kwargs)
builtins.open=guarded_open
os.system=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('eidolon_python_process_blocked'))
os.popen=os.system
sys.path.insert(0,str(root))
'''
    if runner == "pytest":
        guarded = common.replace("_original_import=builtins.__import__", "import pytest\n_original_import=builtins.__import__", 1)
        return guarded + r'''
raise SystemExit(pytest.main(['-q','--disable-warnings','--maxfail=1','-p','no:cacheprovider','-p','no:logging',*selected]))
'''
    return common + r'''
suite=unittest.TestSuite(); loader=unittest.defaultTestLoader
for index,item in enumerate(selected):
    namespace=runpy.run_path(item,run_name=f'__eidolon_test_{index}__')
    module=types.ModuleType(f'__eidolon_test_{index}__'); module.__dict__.update(namespace)
    suite.addTests(loader.loadTestsFromModule(module))
result=unittest.TextTestRunner(stream=sys.stderr,verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def _failure_result(*, proposal_id: str, revision: int, revision_digest: str, planning_digest: str, generation_digest: str,
                    workspace_digest: str, approval_receipt_digest: str, status: str, outcome_class: str,
                    operation_recovery_count: int, platform_family: str, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "ok": True, "status": status,
        "passed": False, "outcome_class": outcome_class, "proposal_id": proposal_id, "proposal_revision": int(revision),
        "proposal_revision_digest": revision_digest, "planning_digest": planning_digest, "generation_digest": generation_digest,
        "workspace_digest": workspace_digest, "approval_receipt_digest": approval_receipt_digest,
        "platform_family": platform_family, "python_source_class": "none", "launch_attempt_count": 0,
        "launch_failure_digests": [], "operation_recovery_count": operation_recovery_count, "python_executed": False,
        "runner": "none", "syntax_file_count": 0, "test_file_count": 0, "command_count": 0,
        "passed_command_count": 0, "failed_command_count": 0, "command_results": [], "cleanup_confirmed": True,
        "network_allowed": False, "process_spawning_allowed": False, "native_extensions_allowed": False,
        "dependencies_installed": False, "shell_executed": False, "selected_project_modified": False,
        "source_modified": False, "implementation_applied": False, "repair_authorized": False,
        "apply_authorized": False, "rollback_authorized": False, "release_authorized": False,
        "authority_granted": False, "private_path_included": False, "private_content_included": False,
        "raw_output_included": False, "content_free": True,
        "sandbox_backend": "python-audit-hook", "filesystem_write_scope": "private_scratch_only",
        "os_isolation_provided": False, "security_boundary": "language_runtime_policy_not_os_container",
    }
    if extra: record.update(dict(extra))
    record["python_test_adapter_digest"] = _digest(record)
    return record


def run_or_resume_python_tests(proposal_id: str, *, expected_revision: int, expected_revision_digest: str,
                               expected_workspace_digest: str, runtime_root=None, python_executable: str | None = None) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
        if not plan or plan.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_or_missing_grounded_plan"}
        project_kind = str(plan.get("project_kind") or "")
        if project_kind not in SUPPORTED_PROJECT_KINDS:
            return {"ok": False, "status": "python_test_adapter_project_kind_unsupported"}
        workspace = _read_json(_record_path(proposal_id, expected_revision, runtime_root))
        if not workspace: return {"ok": False, "status": "workspace_missing"}
        if workspace.get("proposal_revision_digest") != expected_revision_digest: return {"ok": False, "status": "stale_proposal_revision"}
        if workspace.get("workspace_digest") != expected_workspace_digest: return {"ok": False, "status": "stale_workspace_revision"}
        planning_digest = str(workspace.get("planning_digest") or ""); generation_digest = str(workspace.get("generation_digest") or "")
        if planning_digest != plan.get("planning_digest"): return {"ok": False, "status": "stale_workspace_planning_binding"}
        root = _workspace_root(proposal_id, expected_revision, generation_digest, runtime_root)
        if not _verify_record(workspace, root): return {"ok": False, "status": "workspace_record_invalid"}

        result_path = _result_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(result_path)
        if existing:
            bindings = existing.get("proposal_revision_digest") == expected_revision_digest and existing.get("workspace_digest") == expected_workspace_digest and existing.get("planning_digest") == planning_digest and existing.get("generation_digest") == generation_digest
            return ({**existing, "operation_status": "resumed"} if bindings and _record_valid(existing) else {"ok": False, "status": "python_test_adapter_record_invalid"})

        operation_path = _operation_path(proposal_id, expected_revision, runtime_root); operation = _read_json(operation_path)
        recovery_count = 0; attempt_count = 1
        if operation:
            if not _operation_valid(operation): return {"ok": False, "status": "python_test_operation_invalid"}
            if operation.get("proposal_revision_digest") != expected_revision_digest or operation.get("workspace_digest") != expected_workspace_digest or operation.get("planning_digest") != planning_digest or operation.get("generation_digest") != generation_digest:
                return {"ok": False, "status": "stale_python_test_operation"}
            if operation.get("phase") == "sealed": return {"ok": False, "status": "python_test_result_missing"}
            if max(0.0, time.time() - float(operation.get("updated_at_epoch") or 0)) < OPERATION_STALE_SECONDS:
                return {"ok": False, "status": "python_test_operation_in_progress"}
            recovery_count = int(operation.get("recovery_count") or 0) + 1; attempt_count = int(operation.get("attempt_count") or 0) + 1
        operation = _write_operation(operation_path, {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "phase": "prepared",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision), "proposal_revision_digest": expected_revision_digest,
            "planning_digest": planning_digest, "generation_digest": generation_digest, "workspace_digest": expected_workspace_digest,
            "attempt_count": attempt_count, "recovery_count": recovery_count, "updated_at_epoch": time.time(),
            "network_allowed": False, "dependencies_installed": False, "shell_executed": False,
            "selected_project_modified": False, "source_modified": False, "repair_authorized": False,
            "apply_authorized": False, "release_authorized": False, "authority_granted": False,
        })

        platform_family = _platform_family(); rows, error = _read_workspace_sources(root, workspace)
        if rows is None:
            record = _failure_result(proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                planning_digest=planning_digest, generation_digest=generation_digest, workspace_digest=expected_workspace_digest,
                approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""), status=str(error.get("status") or "python_test_source_rejected"),
                outcome_class="contract_rejected", operation_recovery_count=recovery_count, platform_family=platform_family)
        else:
            py_rows = [row for row in rows if str(row["relative_path"]).endswith(".py")]; test_rows = [row for row in py_rows if row["is_test"]]
            test_paths = [str(row["relative_path"]) for row in test_rows]
            contract_ok, rejected_digest = _capability_contract_ok(py_rows)
            if not contract_ok:
                record = _failure_result(proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                    planning_digest=planning_digest, generation_digest=generation_digest, workspace_digest=expected_workspace_digest,
                    approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""), status="python_test_capability_contract_rejected",
                    outcome_class="contract_rejected", operation_recovery_count=recovery_count, platform_family=platform_family,
                    extra={"rejected_path_digest": rejected_digest, "syntax_file_count": len(py_rows), "test_file_count": len(test_paths)})
            elif not test_paths:
                record = _failure_result(proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                    planning_digest=planning_digest, generation_digest=generation_digest, workspace_digest=expected_workspace_digest,
                    approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""), status="python_tests_not_found",
                    outcome_class="tests_not_found", operation_recovery_count=recovery_count, platform_family=platform_family,
                    extra={"syntax_file_count": len(py_rows)})
            else:
                private = _private_home(proposal_id, expected_revision, runtime_root)
                python, source_class, failures, launch_attempts, probe_cleanup = _select_python(_python_candidates(python_executable), cwd=root, private=private)
                runner = _preferred_runner(rows)
                if not python:
                    record = _failure_result(proposal_id=proposal_id, revision=expected_revision, revision_digest=expected_revision_digest,
                        planning_digest=planning_digest, generation_digest=generation_digest, workspace_digest=expected_workspace_digest,
                        approval_receipt_digest=str(workspace.get("approval_receipt_digest") or ""), status="python_runtime_unavailable",
                        outcome_class="python_unavailable", operation_recovery_count=recovery_count, platform_family=platform_family,
                        extra={"runner": runner, "python_source_class": "none", "launch_attempt_count": launch_attempts,
                               "launch_failure_digests": failures, "cleanup_confirmed": probe_cleanup, "syntax_file_count": len(py_rows), "test_file_count": len(test_paths)})
                else:
                    env = _minimal_environment(python, private); command_results: list[dict[str, Any]] = []; cleanup = probe_cleanup; syntax_passed = True
                    syntax_source = "import ast,pathlib,sys;ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))"
                    for row in py_rows:
                        cmd = _run_bounded_command([python, "-I", "-B", "-c", syntax_source, str(row["path"])], cwd=root, env=env, timeout_seconds=SYNTAX_TIMEOUT_SECONDS)
                        cleanup = cleanup and bool(cmd.get("cleanup_confirmed")); command_results.append({"phase": "syntax", "path_digest": str(row["relative_path_digest"]), **cmd})
                        if not cmd.get("passed"): syntax_passed = False; break
                    pytest_available = False
                    if syntax_passed and runner == "pytest":
                        probe = _run_bounded_command([python, "-I", "-B", "-c", "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pytest') else 1)"], cwd=root, env=env, timeout_seconds=PYTHON_PROBE_TIMEOUT_SECONDS)
                        cleanup = cleanup and bool(probe.get("cleanup_confirmed")); pytest_available = bool(probe.get("passed"))
                    tests_passed = False
                    if syntax_passed and (runner != "pytest" or pytest_available):
                        selected = [str(root / _safe_relative(path)) for path in test_paths]
                        cmd = _run_bounded_command([python, "-I", "-B", "-c", _runner_source(runner), str(root), str(private / "temp"), *selected], cwd=root, env=env, timeout_seconds=TEST_TIMEOUT_SECONDS)
                        cleanup = cleanup and bool(cmd.get("cleanup_confirmed")); command_results.append({"phase": "tests", "runner": runner, "selection_digest": _digest([_path_digest(path) for path in test_paths]), **cmd}); tests_passed = bool(cmd.get("passed"))
                    if syntax_passed and runner == "pytest" and not pytest_available:
                        outcome = "pytest_unavailable"; status = "python_pytest_unavailable"
                    elif not syntax_passed:
                        outcome = "syntax_failed"; status = "python_test_adapter_failed"
                    elif not tests_passed:
                        exit_class = str(command_results[-1].get("exit_class") or "nonzero") if command_results else "nonzero"
                        outcome = {"timeout":"test_timeout", "output_limit":"test_output_limit", "spawn_failed":"test_spawn_failed"}.get(exit_class, "tests_failed"); status = "python_test_adapter_failed"
                    elif not cleanup:
                        outcome = "cleanup_failed"; status = "python_test_adapter_failed"
                    else:
                        outcome = "passed"; status = "python_test_adapter_passed"
                    passed = outcome == "passed"
                    record = {
                        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "ok": True, "status": status,
                        "passed": passed, "outcome_class": outcome, "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
                        "proposal_revision_digest": expected_revision_digest, "planning_digest": planning_digest, "generation_digest": generation_digest,
                        "workspace_digest": expected_workspace_digest, "approval_receipt_digest": workspace.get("approval_receipt_digest"),
                        "project_kind": project_kind, "platform_family": platform_family, "python_source_class": source_class,
                        "launch_attempt_count": launch_attempts, "launch_failure_digests": failures, "operation_recovery_count": recovery_count,
                        "python_executed": True, "runner": runner, "pytest_available": pytest_available, "syntax_file_count": len(py_rows),
                        "test_file_count": len(test_paths), "test_selection_digest": _digest([_path_digest(path) for path in test_paths]),
                        "command_count": len(command_results), "passed_command_count": sum(1 for x in command_results if x.get("passed")),
                        "failed_command_count": sum(1 for x in command_results if not x.get("passed")), "command_results": command_results,
                        "cleanup_confirmed": cleanup, "network_allowed": False, "process_spawning_allowed": False,
                        "native_extensions_allowed": False, "dependencies_installed": False, "shell_executed": False,
                        "selected_project_modified": False, "source_modified": False, "implementation_applied": False,
                        "repair_authorized": False, "apply_authorized": False, "rollback_authorized": False,
                        "release_authorized": False, "authority_granted": False, "private_path_included": False,
                        "private_content_included": False, "raw_output_included": False, "content_free": True,
                        "sandbox_backend": "python-audit-hook", "filesystem_write_scope": "private_scratch_only",
                        "os_isolation_provided": False, "security_boundary": "language_runtime_policy_not_os_container",
                    }
                    record["python_test_adapter_digest"] = _digest(record)
        _atomic_json(result_path, record)
        sealed = _write_operation(operation_path, {**{k:v for k,v in operation.items() if k != "operation_digest"}, "phase":"sealed", "result_digest":record["python_test_adapter_digest"], "result_status":record["status"], "result_passed":bool(record.get("passed")), "cleanup_confirmed":bool(record.get("cleanup_confirmed")), "updated_at_epoch":time.time()})
        return {**record, "operation_status":"created", "operation_digest":sealed["operation_digest"]}


def public_python_test_result(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "ok","status","contract_version","passed","outcome_class","proposal_id","proposal_revision","proposal_revision_digest",
        "planning_digest","generation_digest","workspace_digest","approval_receipt_digest","project_kind","platform_family",
        "python_source_class","launch_attempt_count","launch_failure_digests","operation_recovery_count","python_executed","runner",
        "pytest_available","syntax_file_count","test_file_count","test_selection_digest","command_count","passed_command_count",
        "failed_command_count","command_results","cleanup_confirmed","rejected_path_digest","python_test_adapter_digest",
        "network_allowed","process_spawning_allowed","native_extensions_allowed","dependencies_installed","shell_executed",
        "selected_project_modified","source_modified","implementation_applied","repair_authorized","apply_authorized",
        "rollback_authorized","release_authorized","authority_granted","content_free",
        "sandbox_backend","filesystem_write_scope","os_isolation_provided","security_boundary",
    )
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({"private_path_exposed":False,"private_content_exposed":False,"raw_output_exposed":False,"operator_review_required":True})
    return public
