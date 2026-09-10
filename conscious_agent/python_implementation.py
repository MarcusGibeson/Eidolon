from __future__ import annotations
"""v1341 repository-aware Python implementation over the Phase 4 execution stack.

The module adds Python-specific compatibility and verification judgments to the
existing candidate-workspace, structured file, typed Git, and typed process
contracts.  It never writes the selected source.  Raw source text is used only
inside the candidate operation and is not persisted in the public receipt.
"""

import ast
import hashlib
import re
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from workspace_isolation import create_disposable_workspace, cleanup_disposable_workspace
from structured_file_operations import read_candidate_file, patch_candidate_file
from typed_git_operations import stage_owned_changes, commit_owned_changes
from typed_process_operations import start_candidate_process, monitor_candidate_process, stop_candidate_process
from tool_result_reconciliation import reconcile_tool_result

CONTRACT_VERSION = "v1341.8"
MAX_PYTHON_FILES = 4096
MAX_TEST_FILES = 1024
MAX_ANALYSIS_BYTES = 2 * 1024 * 1024
MAX_PROCESS_WAIT_SECONDS = 45.0
REQUIRED_PRECONDITIONS = ("git", "file_read", "file_patch", "shell")
TERMINAL_PROCESS_STATES = {"completed", "failed", "cancelled", "interrupted", "uncertain"}
PYTHON_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "dependency_installation_authorized": False,
    "package_publication_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase5_python_implementation"


def _path(operation_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"pyimpl_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_python_implementation_id")
    return _root(runtime_root) / "records" / f"{operation_id}.json"


def _load(operation_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path(operation_id, runtime_root))
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest", None)
    row["record_digest"] = digest(row)
    _atomic_json(_path(str(row["python_implementation_id"]), runtime_root), row)
    return row


def _safe_python_relative(relative_path: str) -> str:
    text = str(relative_path or "").replace("\\", "/").strip()
    pure = PurePosixPath(text)
    if not text or pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("unsafe_python_relative_path")
    if pure.suffix != ".py":
        raise ValueError("python_source_file_required")
    if any(part.casefold() in {".git", "data", "runtime", "private", "secrets", "credentials", ".venv", "venv", "__pycache__"} for part in pure.parts):
        raise ValueError("protected_python_path")
    return pure.as_posix()


def _annotation_present(node: ast.arg | ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if isinstance(node, ast.arg):
        return node.annotation is not None
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg:
        args.append(node.args.vararg)
    if node.args.kwarg:
        args.append(node.args.kwarg)
    return bool(node.returns is not None and all(arg.annotation is not None for arg in args))


def _function_signature_digest(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    shape = {
        "args": ast.dump(node.args, annotate_fields=True, include_attributes=False),
        "returns": ast.dump(node.returns, annotate_fields=True, include_attributes=False) if node.returns is not None else "",
        "type_comment": str(node.type_comment or ""),
        "async": isinstance(node, ast.AsyncFunctionDef),
    }
    return digest(shape)


def _module_facts(text: str) -> dict[str, Any]:
    raw = text.encode("utf-8")
    if len(raw) > MAX_ANALYSIS_BYTES:
        raise ValueError("python_analysis_budget_exceeded")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "syntax_valid": False,
            "syntax_error_line": int(exc.lineno or 0),
            "public_symbols": [],
            "public_symbol_kinds": {},
            "public_async_symbols": [],
            "public_signature_digests": {},
            "fully_annotated_public_functions": [],
            "import_count": 0,
            "relative_import_count": 0,
            "persistence_markers": [],
            "module_digest": hashlib.sha256(raw).hexdigest(),
        }
    public: list[str] = []
    kinds: dict[str, str] = {}
    async_public: list[str] = []
    annotated: list[str] = []
    signatures: dict[str, str] = {}
    imports = 0
    relative = 0
    persistence: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            public.append(node.name)
            kinds[node.name] = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function" if isinstance(node, ast.FunctionDef) else "class"
            if isinstance(node, ast.AsyncFunctionDef):
                async_public.append(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signatures[node.name] = _function_signature_digest(node)
                if _annotation_present(node):
                    annotated.append(node.name)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1
            if isinstance(node, ast.ImportFrom) and node.level:
                relative += 1
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"sqlite3", "shelve"}:
                    persistence.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module in {"sqlite3", "shelve"}:
            persistence.add(str(node.module))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"write_text", "write_bytes", "dump", "dumps"}:
                persistence.add(f"call:{func.attr}")
            elif isinstance(func, ast.Name) and func.id == "open" and len(node.args) >= 2:
                mode = node.args[1]
                if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and any(flag in mode.value for flag in "wax+"):
                    persistence.add("call:open_write")
    return {
        "syntax_valid": True,
        "syntax_error_line": 0,
        "public_symbols": sorted(public),
        "public_symbol_kinds": {k: kinds[k] for k in sorted(kinds)},
        "public_async_symbols": sorted(async_public),
        "public_signature_digests": {k: signatures[k] for k in sorted(signatures)},
        "fully_annotated_public_functions": sorted(annotated),
        "import_count": imports,
        "relative_import_count": relative,
        "persistence_markers": sorted(persistence),
        "module_digest": hashlib.sha256(raw).hexdigest(),
    }


def _compatibility(before: Mapping[str, Any], after: Mapping[str, Any], *, allow_public_api_change: bool, persistence_change_declared: bool, package_boundary_change_declared: bool, relative_path: str) -> dict[str, Any]:
    before_symbols = set(before.get("public_symbols") or [])
    after_symbols = set(after.get("public_symbols") or [])
    removed = sorted(before_symbols - after_symbols)
    changed_kinds = sorted(name for name in before_symbols & after_symbols if (before.get("public_symbol_kinds") or {}).get(name) != (after.get("public_symbol_kinds") or {}).get(name))
    before_signatures = dict(before.get("public_signature_digests") or {})
    after_signatures = dict(after.get("public_signature_digests") or {})
    changed_signatures = sorted(name for name in before_signatures.keys() & after_signatures.keys() if before_signatures.get(name) != after_signatures.get(name))
    annotation_regressions = sorted(set(before.get("fully_annotated_public_functions") or []) - set(after.get("fully_annotated_public_functions") or []))
    added_persistence = sorted(set(after.get("persistence_markers") or []) - set(before.get("persistence_markers") or []))
    package_boundary = PurePosixPath(relative_path).name == "__init__.py"
    reasons: list[str] = []
    if not after.get("syntax_valid"):
        reasons.append("python_syntax_invalid")
    if (removed or changed_kinds or changed_signatures or annotation_regressions) and not allow_public_api_change:
        reasons.append("undeclared_public_api_change")
    if added_persistence and not persistence_change_declared:
        reasons.append("undeclared_persistence_side_effect")
    if package_boundary and before.get("module_digest") != after.get("module_digest") and not package_boundary_change_declared:
        reasons.append("undeclared_package_boundary_change")
    return {
        "compatible": not reasons,
        "reasons": reasons,
        "removed_public_symbol_count": len(removed),
        "public_kind_change_count": len(changed_kinds),
        "public_signature_change_count": len(changed_signatures),
        "annotation_regression_count": len(annotation_regressions),
        "added_persistence_marker_count": len(added_persistence),
        "package_boundary_touched": package_boundary,
        "before_public_symbol_count": len(before_symbols),
        "after_public_symbol_count": len(after_symbols),
        "before_annotated_public_function_count": len(before.get("fully_annotated_public_functions") or []),
        "after_annotated_public_function_count": len(after.get("fully_annotated_public_functions") or []),
        "before_async_public_count": len(before.get("public_async_symbols") or []),
        "after_async_public_count": len(after.get("public_async_symbols") or []),
    }


def inspect_python_project(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).resolve(strict=True)
    python_files: list[Path] = []
    test_files: list[Path] = []
    package_dirs: set[str] = set()
    annotated_functions = 0
    public_functions = 0
    async_functions = 0
    syntax_invalid = 0
    for path in sorted(root.rglob("*.py")):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in {".git", ".venv", "venv", "__pycache__", "data", "runtime", "private"} for part in rel.parts):
            continue
        if len(python_files) >= MAX_PYTHON_FILES:
            break
        if not path.is_file() or path.stat().st_size > MAX_ANALYSIS_BYTES:
            continue
        python_files.append(path)
        if path.name == "__init__.py":
            package_dirs.add(rel.parent.as_posix())
        if (path.name.startswith("test_") or path.name.endswith("_test.py") or "tests" in rel.parts) and len(test_files) < MAX_TEST_FILES:
            test_files.append(path)
        try:
            facts = _module_facts(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError, ValueError):
            continue
        if not facts.get("syntax_valid"):
            syntax_invalid += 1
        public_functions += sum(1 for kind in (facts.get("public_symbol_kinds") or {}).values() if kind in {"function", "async_function"})
        annotated_functions += len(facts.get("fully_annotated_public_functions") or [])
        async_functions += len(facts.get("public_async_symbols") or [])
    metadata = [name for name in ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "Pipfile") if (root / name).is_file()]
    framework = "unittest_or_unknown"
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")[:200_000]
        if "pytest" in text:
            framework = "pytest"
    if framework == "unittest_or_unknown" and any("pytest" in p.read_text(encoding="utf-8", errors="ignore")[:20_000] for p in test_files[:50]):
        framework = "pytest"
    summary = {
        "contract_version": CONTRACT_VERSION,
        "python_file_count": len(python_files),
        "test_file_count": len(test_files),
        "package_directory_count": len(package_dirs),
        "packaging_metadata_files": sorted(metadata),
        "test_framework_inferred": framework,
        "public_function_count": public_functions,
        "fully_annotated_public_function_count": annotated_functions,
        "async_public_function_count": async_functions,
        "syntax_invalid_file_count": syntax_invalid,
        "inspection_truncated": len(python_files) >= MAX_PYTHON_FILES,
        "source_manifest_digest": digest([(p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()) for p in python_files]),
        "inspection_only": True,
        "network_contacted": False,
        "dependency_installed": False,
        **PYTHON_DENIED_AUTHORITY,
    }
    summary["inspection_digest"] = digest(summary)
    return summary


def _wait_process(process_id: str, *, workspace_digest: str, runtime_root=None) -> tuple[bool, dict[str, Any], str]:
    deadline = time.monotonic() + MAX_PROCESS_WAIT_SECONDS
    observed: dict[str, Any] = {}
    while time.monotonic() < deadline:
        observed = monitor_candidate_process(process_id, runtime_root=runtime_root)
        state = (observed.get("process_operation") or {}).get("process_state")
        if state in TERMINAL_PROCESS_STATES:
            break
        time.sleep(0.05)
    proc = observed.get("process_operation") or {}
    passed = proc.get("process_state") == "completed" and proc.get("return_code") == 0 and not proc.get("timed_out") and not proc.get("log_limit_exceeded")
    recon = reconcile_tool_result(tool_code="shell", operation_id=process_id, wrapper_observation={"wrapper_status": "returned", "reported_status": proc.get("process_state")}, current_workspace_digest=workspace_digest, runtime_root=runtime_root)
    return passed, proc, str((recon.get("reconciliation") or {}).get("reconciliation_id") or "")


def run_python_implementation(
    *, source_root: str | Path, source_workspace_digest: str, active_grant: Mapping[str, Any], precondition_record_ids: Mapping[str, str],
    relative_path: str, expected_content_digest: str, patches: Sequence[Mapping[str, Any]], test_argv: Sequence[str], commit_message: str,
    allow_public_api_change: bool = False, persistence_change_declared: bool = False, package_boundary_change_declared: bool = False,
    runtime_root=None, now_unix: int | None = None, git_executable: str | None = None, python_executable: str | None = None,
    cleanup_on_complete: bool = True,
) -> dict[str, Any]:
    try:
        rel = _safe_python_relative(relative_path)
    except ValueError as exc:
        return {"ok": False, "status": str(exc), "action_executed": False, **PYTHON_DENIED_AUTHORITY}
    pres = {str(k): str(v) for k, v in precondition_record_ids.items()}
    if any(not pres.get(k) for k in REQUIRED_PRECONDITIONS):
        return {"ok": False, "status": "complete_python_preconditions_required", "action_executed": False, **PYTHON_DENIED_AUTHORITY}
    spec = {
        "contract": CONTRACT_VERSION, "source_workspace_digest": source_workspace_digest, "grant": active_grant.get("grant_digest"),
        "preconditions": pres, "relative_path_digest": hashlib.sha256(rel.encode()).hexdigest(), "expected_content_digest": expected_content_digest,
        "patch_digest": digest(patches), "test_argv_digest": digest(list(test_argv)), "commit_message_digest": hashlib.sha256(str(commit_message).encode()).hexdigest(),
        "allow_public_api_change": bool(allow_public_api_change), "persistence_change_declared": bool(persistence_change_declared),
        "package_boundary_change_declared": bool(package_boundary_change_declared), "cleanup_on_complete": bool(cleanup_on_complete),
    }
    operation_id = "pyimpl_" + digest(spec)[:24]
    existing = _load(operation_id, runtime_root)
    if existing:
        return {"ok": existing.get("implementation_state") == "completed", "status": "python_implementation_already_exists", "python_implementation": public_python_implementation(existing), "action_executed": False, **PYTHON_DENIED_AUTHORITY}
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION, "python_implementation_id": operation_id, "source_workspace_digest": source_workspace_digest,
        "grant_digest": active_grant.get("grant_digest"), "relative_path_digest": hashlib.sha256(rel.encode()).hexdigest(), "precondition_digest": digest(pres),
        "implementation_state": "starting", "failure_stage": "", "workspace_id": "", "file_operation_id": "", "git_stage_operation_id": "", "git_commit_operation_id": "",
        "compile_process_id": "", "compile_reconciliation_id": "", "test_process_id": "", "test_reconciliation_id": "",
        "syntax_valid": False, "compatibility_passed": False, "compile_passed": False, "tests_passed": False, "workspace_cleaned": False, "host_recoverable": False,
        "compatibility_summary": {}, "before_facts_digest": "", "after_facts_digest": "", "action_executed": False, **PYTHON_DENIED_AUTHORITY,
    }
    _save(row, runtime_root)
    workspace_id = ""
    process_ids: list[str] = []
    try:
        isolated = create_disposable_workspace(source_root=source_root, source_workspace_digest=source_workspace_digest, active_grant=active_grant, precondition_record_id=pres["git"], mode="git_branch_worktree", retention_rule="retain_for_review", runtime_root=runtime_root, now_unix=now_unix, git_executable=git_executable)
        if not isolated.get("ok") or not isolated.get("workspace_created"):
            raise RuntimeError("workspace_isolation")
        workspace_id = str(isolated["workspace_id"]); row["workspace_id"] = workspace_id; row["action_executed"] = True; _save(row, runtime_root)
        before_read = read_candidate_file(workspace_id, rel, active_grant=active_grant, precondition_record_id=pres["file_read"], runtime_root=runtime_root, now_unix=now_unix, include_content=True)
        if not before_read.get("ok"):
            raise RuntimeError("python_read_before")
        before_text = str(before_read.get("content") or "")
        before = _module_facts(before_text)
        if not before.get("syntax_valid"):
            raise RuntimeError("existing_python_syntax_invalid")
        if before.get("module_digest") != expected_content_digest:
            raise RuntimeError("stale_python_content_digest")
        row["before_facts_digest"] = digest(before); _save(row, runtime_root)
        patched = patch_candidate_file(workspace_id, rel, expected_content_digest=expected_content_digest, patches=patches, active_grant=active_grant, precondition_record_id=pres["file_patch"], runtime_root=runtime_root, now_unix=now_unix)
        if not patched.get("ok"):
            raise RuntimeError(str(patched.get("status") or "python_patch"))
        row["file_operation_id"] = str((patched.get("file_operation") or {}).get("operation_id") or ""); _save(row, runtime_root)
        after_read = read_candidate_file(workspace_id, rel, active_grant=active_grant, precondition_record_id=pres["file_read"], runtime_root=runtime_root, now_unix=now_unix, include_content=True)
        if not after_read.get("ok"):
            raise RuntimeError("python_read_after")
        after = _module_facts(str(after_read.get("content") or ""))
        row["syntax_valid"] = bool(after.get("syntax_valid")); row["after_facts_digest"] = digest(after)
        compat = _compatibility(before, after, allow_public_api_change=allow_public_api_change, persistence_change_declared=persistence_change_declared, package_boundary_change_declared=package_boundary_change_declared, relative_path=rel)
        row["compatibility_summary"] = compat; row["compatibility_passed"] = bool(compat.get("compatible")); _save(row, runtime_root)
        if not row["compatibility_passed"]:
            raise RuntimeError(str((compat.get("reasons") or ["python_compatibility"])[0]))
        py = str(python_executable or sys.executable)
        compile_result = start_candidate_process(workspace_id, [py, "-m", "py_compile", rel], active_grant=active_grant, precondition_record_id=pres["shell"], runtime_root=runtime_root, now_unix=now_unix, timeout_seconds=30, invocation_discriminator=f"v1341:{operation_id}:compile")
        if not compile_result.get("ok"):
            raise RuntimeError("python_compile_start")
        compile_id = str((compile_result.get("process_operation") or {}).get("process_operation_id") or ""); process_ids.append(compile_id); row["compile_process_id"] = compile_id; _save(row, runtime_root)
        passed, _, recon_id = _wait_process(compile_id, workspace_digest=source_workspace_digest, runtime_root=runtime_root); row["compile_passed"] = passed; row["compile_reconciliation_id"] = recon_id; _save(row, runtime_root)
        if not passed:
            raise RuntimeError("python_compile_failed")
        if not test_argv:
            raise RuntimeError("focused_python_tests_required")
        test_result = start_candidate_process(workspace_id, list(test_argv), active_grant=active_grant, precondition_record_id=pres["shell"], runtime_root=runtime_root, now_unix=now_unix, timeout_seconds=40, invocation_discriminator=f"v1341:{operation_id}:tests")
        if not test_result.get("ok"):
            raise RuntimeError("python_test_start")
        test_id = str((test_result.get("process_operation") or {}).get("process_operation_id") or ""); process_ids.append(test_id); row["test_process_id"] = test_id; _save(row, runtime_root)
        passed, _, recon_id = _wait_process(test_id, workspace_digest=source_workspace_digest, runtime_root=runtime_root); row["tests_passed"] = passed; row["test_reconciliation_id"] = recon_id; _save(row, runtime_root)
        if not passed:
            raise RuntimeError("python_tests_failed")
        staged = stage_owned_changes(workspace_id, owned_file_operation_ids=[row["file_operation_id"]], active_grant=active_grant, precondition_record_id=pres["git"], runtime_root=runtime_root, now_unix=now_unix, git_executable=git_executable)
        if not staged.get("ok"):
            raise RuntimeError("python_git_stage")
        row["git_stage_operation_id"] = str((staged.get("git_operation") or {}).get("operation_id") or ""); _save(row, runtime_root)
        committed = commit_owned_changes(workspace_id, stage_operation_id=row["git_stage_operation_id"], commit_message=commit_message, active_grant=active_grant, precondition_record_id=pres["git"], runtime_root=runtime_root, now_unix=now_unix, git_executable=git_executable)
        if not committed.get("ok"):
            raise RuntimeError("python_git_commit")
        row["git_commit_operation_id"] = str((committed.get("git_operation") or {}).get("operation_id") or "")
        row["implementation_state"] = "verified_candidate"; _save(row, runtime_root)
    except Exception as exc:
        row["implementation_state"] = "failed"; row["failure_stage"] = str(exc); _save(row, runtime_root)
    finally:
        for process_id in process_ids:
            try:
                observed = monitor_candidate_process(process_id, runtime_root=runtime_root)
                if (observed.get("process_operation") or {}).get("process_state") not in TERMINAL_PROCESS_STATES:
                    stop_candidate_process(process_id, active_grant=active_grant, runtime_root=runtime_root, now_unix=now_unix)
            except Exception:
                pass
        if workspace_id and cleanup_on_complete:
            try:
                cleaned = cleanup_disposable_workspace(workspace_id, active_grant=active_grant, discard_owned_changes=True, runtime_root=runtime_root, now_unix=now_unix, git_executable=git_executable)
                row["workspace_cleaned"] = cleaned.get("cleaned") is True
            except Exception:
                row["workspace_cleaned"] = False
        row["host_recoverable"] = bool(not cleanup_on_complete or row.get("workspace_cleaned"))
        if row.get("implementation_state") == "verified_candidate" and row.get("host_recoverable"):
            row["implementation_state"] = "completed"
        _save(row, runtime_root)
    ok = row.get("implementation_state") == "completed"
    return {"ok": ok, "status": "python_implementation_completed" if ok else "python_implementation_failed", "python_implementation": public_python_implementation(row), "action_executed": row.get("action_executed") is True, **PYTHON_DENIED_AUTHORITY}


def public_python_implementation(row: Mapping[str, Any]) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "contract_version": CONTRACT_VERSION,
        "python_implementation_id": row.get("python_implementation_id"),
        "source_workspace_digest": row.get("source_workspace_digest"),
        "relative_path_digest": row.get("relative_path_digest"),
        "implementation_state": row.get("implementation_state"),
        "failure_stage": row.get("failure_stage") or "",
        "workspace_id": row.get("workspace_id") or "",
        "file_operation_id": row.get("file_operation_id") or "",
        "git_stage_operation_id": row.get("git_stage_operation_id") or "",
        "git_commit_operation_id": row.get("git_commit_operation_id") or "",
        "compile_process_id": row.get("compile_process_id") or "",
        "compile_reconciliation_id": row.get("compile_reconciliation_id") or "",
        "test_process_id": row.get("test_process_id") or "",
        "test_reconciliation_id": row.get("test_reconciliation_id") or "",
        "syntax_valid": row.get("syntax_valid") is True,
        "compatibility_passed": row.get("compatibility_passed") is True,
        "compatibility_summary": dict(row.get("compatibility_summary") or {}),
        "compile_passed": row.get("compile_passed") is True,
        "tests_passed": row.get("tests_passed") is True,
        "workspace_cleaned": row.get("workspace_cleaned") is True,
        "host_recoverable": row.get("host_recoverable") is True,
        "before_facts_digest": row.get("before_facts_digest") or "",
        "after_facts_digest": row.get("after_facts_digest") or "",
        "raw_source_exposed": False,
        "raw_test_command_exposed": False,
        "selected_source_content_modified": False,
        "candidate_only": True,
        "action_executed": row.get("action_executed") is True,
        **PYTHON_DENIED_AUTHORITY,
    }


def load_python_implementation(operation_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _load(str(operation_id), runtime_root)
    return public_python_implementation(row) if row else {}


def process_python_implementation_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show python implementation checkpoint", "inspect python implementation", "show python implementation"}:
        return {"active": False}
    operation_id = str((project_state or {}).get("python_implementation_id") or "")
    row = load_python_implementation(operation_id, runtime_root=runtime_root) if operation_id else {}
    return {"active": True, "ok": bool(row), "status": "python_implementation_found" if row else "python_implementation_missing", "python_implementation": row, "action_executed": False, **PYTHON_DENIED_AUTHORITY}


__all__ = [
    "CONTRACT_VERSION", "REQUIRED_PRECONDITIONS", "PYTHON_DENIED_AUTHORITY",
    "inspect_python_project", "run_python_implementation", "public_python_implementation",
    "load_python_implementation", "process_python_implementation_control",
]
