from __future__ import annotations

"""v1203.3-v1203.5 bounded project-owned Python test execution.

Discovers only allowlisted Python test files in the exact isolated workspace and
runs them with the configured Python interpreter under an isolated, minimal
process contract. No dependencies are installed, network/process-capable imports
are permitted, or repair/apply/release authority is granted.
"""

import ast
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_implementation_workspace import _record_path, _workspace_root, _verify_record
from structured_development_generation import _safe_relative

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1203.5"
MAX_TEST_FILES = 12
MAX_TEST_FILE_BYTES = 256 * 1024
MAX_TEST_TOTAL_BYTES = 1024 * 1024
TEST_TIMEOUT_SECONDS = 12
TEST_PREFIXES = ("test_",)
TEST_SUFFIXES = ("_test.py",)
FORBIDDEN_IMPORT_ROOTS = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib",
    "subprocess", "multiprocessing", "asyncio.subprocess", "ctypes",
}


def _path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "project_owned_python_tests" / proposal_id / f"revision-{int(revision)}.json"


def _valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("test_execution_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "test_execution_digest"}))


def _diag(*parts: str) -> str:
    text = "\n".join(str(part or "")[:4096] for part in parts)
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _is_test_path(relative_path: str) -> bool:
    path = Path(relative_path)
    if not relative_path.startswith("tests/") or path.suffix.lower() != ".py":
        return False
    return path.name.startswith(TEST_PREFIXES) or path.name.endswith(TEST_SUFFIXES)


def _discover(root: Path, workspace: Mapping[str, Any]):
    rows = []
    for row in workspace.get("files") or []:
        relative_path = str(row.get("relative_path") or "")
        if not _is_test_path(relative_path):
            continue
        try:
            safe = _safe_relative(relative_path)
        except ValueError:
            return None, {"ok": False, "status": "project_test_path_rejected"}
        path = root / safe
        if not path.is_file() or path.is_symlink():
            return None, {"ok": False, "status": "project_test_file_rejected"}
        size = path.stat().st_size
        if size > MAX_TEST_FILE_BYTES:
            return None, {"ok": False, "status": "project_test_budget_exceeded"}
        rows.append((safe, path, size))
    rows.sort(key=lambda item: item[0])
    if not rows:
        return None, {"ok": False, "status": "project_tests_not_found"}
    if len(rows) > MAX_TEST_FILES or sum(item[2] for item in rows) > MAX_TEST_TOTAL_BYTES:
        return None, {"ok": False, "status": "project_test_budget_exceeded"}
    return rows, {}


def _capability_contract_ok(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        for name in names:
            if name in FORBIDDEN_IMPORT_ROOTS or name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                return False
    return True


def execute_or_resume_project_python_tests(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    runtime_root=None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        workspace = _read_json(_record_path(proposal_id, expected_revision, runtime_root))
        if not workspace:
            return {"ok": False, "status": "workspace_missing"}
        if workspace.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if workspace.get("workspace_digest") != expected_workspace_digest:
            return {"ok": False, "status": "stale_workspace_revision"}
        root = _workspace_root(proposal_id, expected_revision, str(workspace.get("generation_digest") or ""), runtime_root)
        if not _verify_record(workspace, root):
            return {"ok": False, "status": "workspace_record_invalid"}
        existing = _read_json(_path(proposal_id, expected_revision, runtime_root))
        if existing:
            bindings_ok = existing.get("workspace_digest") == expected_workspace_digest and existing.get("proposal_revision_digest") == expected_revision_digest
            return ({**existing, "operation_status": "resumed"} if bindings_ok and _valid(existing) else {"ok": False, "status": "project_test_record_invalid"})

        discovered, error = _discover(root, workspace)
        if discovered is None:
            return error
        python = python_executable or shutil.which("python3") or shutil.which("python")
        if not python:
            return {"ok": False, "status": "python_unavailable"}

        for relative_path, path, _ in discovered:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return {"ok": False, "status": "project_test_source_unreadable"}
            if not _capability_contract_ok(text):
                return {
                    "ok": False,
                    "status": "project_test_capability_rejected",
                    "test_path_digest": hashlib.sha256(relative_path.encode()).hexdigest(),
                }

        private_home = _store_root(runtime_root) / "private_python_test_home"
        private_home.mkdir(parents=True, exist_ok=True)
        env = {
            "PATH": os.path.dirname(python),
            "LANG": "C",
            "LC_ALL": "C",
            "NO_COLOR": "1",
            "CI": "1",
            "HOME": str(private_home),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        runner = (
            "import runpy,sys; root,test=sys.argv[1],sys.argv[2]; "
            "sys.path.insert(0,root); sys.argv=[test]; runpy.run_path(test,run_name='__main__')"
        )
        results = []
        for relative_path, path, _ in discovered:
            try:
                completed = subprocess.run(
                    [python, "-I", "-B", "-c", runner, str(root), str(path)],
                    cwd=str(root),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=TEST_TIMEOUT_SECONDS,
                    check=False,
                )
                results.append({
                    "test_path_digest": hashlib.sha256(relative_path.encode()).hexdigest(),
                    "exit_class": "zero" if completed.returncode == 0 else "nonzero",
                    "passed": completed.returncode == 0,
                    "output_digest": _diag(completed.stdout.decode(errors="replace"), completed.stderr.decode(errors="replace")),
                })
            except subprocess.TimeoutExpired as error:
                results.append({
                    "test_path_digest": hashlib.sha256(relative_path.encode()).hexdigest(),
                    "exit_class": "timeout",
                    "passed": False,
                    "output_digest": _diag(str(error)),
                })
            except OSError as error:
                results.append({
                    "test_path_digest": hashlib.sha256(relative_path.encode()).hexdigest(),
                    "exit_class": "spawn_failed",
                    "passed": False,
                    "output_digest": _diag(type(error).__name__),
                })

        passed = all(result["passed"] for result in results)
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "project_python_tests_passed" if passed else "project_python_tests_failed",
            "passed": passed,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "planning_digest": workspace.get("planning_digest"),
            "generation_digest": workspace.get("generation_digest"),
            "workspace_digest": expected_workspace_digest,
            "approval_receipt_digest": workspace.get("approval_receipt_digest"),
            "test_file_count": len(discovered),
            "command_count": len(results),
            "results": results,
            "network_allowed": False,
            "process_spawning_allowed": False,
            "dependencies_installed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        }
        record["test_execution_digest"] = _digest(record)
        _atomic_json(_path(proposal_id, expected_revision, runtime_root), record)
        return {**record, "operation_status": "created"}


def public_project_python_tests(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "passed": bool(record.get("passed")),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "workspace_digest": str(record.get("workspace_digest") or ""),
        "test_execution_digest": str(record.get("test_execution_digest") or ""),
        "test_file_count": int(record.get("test_file_count") or 0),
        "command_count": int(record.get("command_count") or 0),
        "passed_result_count": sum(1 for row in record.get("results") or [] if row.get("passed")),
        "network_allowed": False,
        "process_spawning_allowed": False,
        "dependencies_installed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
