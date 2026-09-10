from __future__ import annotations

"""v1255.3-v1255.5 controlled application, verification, and rollback.

A sealed v1254 candidate may be applied only after a separate exact v1255
application authorization.  The application touches only reviewed candidate
paths, captures a private rollback manifest immediately before the first write,
performs bounded post-apply verification, and restores the pre-apply state if
application or verification fails.  A successful application can later be
rolled back only with another exact, digest-bound authorization.

Provider contact, dependency installation, release, promotion, permanent
approval, and independent authority are never granted by this module.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from controlled_application_rollback_foundations import (
    CONTRACT_VERSION as FOUNDATION_CONTRACT_VERSION,
    DENIED_AUTHORITY,
    _application_authorization_phrase,
    _application_path,
    _candidate_workspace_root,
    _current_path_state,
    _request_id,
    _sealed,
    _valid,
    _workspace_record_path,
    build_private_backup_manifest,
    inspect_controlled_application_conflicts,
    load_controlled_application,
    prepare_controlled_application,
    public_controlled_application,
    validate_private_backup_manifest,
)
from isolated_coding_execution_foundations import (
    _file_digest,
    _is_link_like,
    _resolve_project_root,
    _safe_relative,
    _within,
    load_coding_project_inspection,
    load_coding_work_request,
)
from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from security_privacy_hardening_foundations import inspect_contained_path

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1255.5"
LEASE_SECONDS = 180.0
VERIFY_TIMEOUT_SECONDS = 45


def _execution_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_application_executions" / f"{request_id}.json"


def _authorization_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_application_authorizations" / f"{request_id}.json"


def _backup_manifest_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_application_backups" / f"{request_id}.json"


def _journal_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_application_journals" / f"{request_id}.json"


def _rollback_request_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_rollback_requests" / f"{request_id}.json"


def _rollback_result_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_rollback_results" / f"{request_id}.json"


def _rollback_authorization_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_rollback_authorizations" / f"{request_id}.json"


def _rollback_journal_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_rollback_journals" / f"{request_id}.json"


def _write_journal(path: Path, **fields: Any) -> dict[str, Any]:
    row = {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, **fields}
    return_row = _sealed(row, "journal_digest")
    _atomic_json(path, return_row)
    return return_row


def _valid_journal(row: Mapping[str, Any]) -> bool:
    return bool(row and _valid(row, "journal_digest"))


def _execution_authority() -> dict[str, bool]:
    row = dict(DENIED_AUTHORITY)
    row.update({
        "application_execution_authorized": True,
        "selected_project_mutation_authorized": True,
        "command_execution_authorized": True,
        "test_execution_authorized": True,
    })
    return row


def _rollback_authority() -> dict[str, bool]:
    row = dict(DENIED_AUTHORITY)
    row.update({
        "rollback_execution_authorized": True,
        "selected_project_mutation_authorized": True,
    })
    return row


def _failure(status: str, *, request_id: str = "", reason: str = "") -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "request_id": request_id,
        "reason": reason,
        "selected_project_modified": False,
        "operator_review_required": True,
        **DENIED_AUTHORITY,
    }
    row["result_digest"] = _digest(row)
    return row


def _safe_target(project_root: Path, relative: str, *, create_parent: bool = False) -> Path:
    safe = _safe_relative(relative)
    target = project_root / Path(*PurePosixPath(safe).parts)
    if not _within(project_root, target):
        raise ValueError("selected_project_path_escape")
    inspect_contained_path(project_root, safe, require_exists=False)
    current = project_root
    parts = PurePosixPath(safe).parts[:-1]
    for part in parts:
        current = current / part
        if current.exists() and (_is_link_like(current) or not current.is_dir()):
            raise ValueError("selected_project_parent_link_or_non_directory")
    if target.exists() and _is_link_like(target):
        raise ValueError("selected_project_target_link_or_junction")
    if create_parent:
        target.parent.mkdir(parents=True, exist_ok=True)
        inspect_contained_path(project_root, safe, require_exists=False)
        if not _within(project_root, target.parent) or _is_link_like(target.parent):
            raise ValueError("selected_project_parent_boundary_changed")
    return target


def _workspace_candidate_bytes(request_id: str, change: Mapping[str, Any], *, runtime_root=None) -> bytes:
    if str(change.get("operation") or "") == "delete":
        return b""
    workspace = _read_json(_workspace_record_path(request_id, runtime_root))
    if not workspace:
        raise ValueError("candidate_workspace_record_missing")
    root = _candidate_workspace_root(workspace)
    relative = _safe_relative(str(change.get("relative_path") or ""))
    path = root / Path(*PurePosixPath(relative).parts)
    inspect_contained_path(root, relative, require_exists=True, require_file=True)
    if not _within(root, path) or _is_link_like(path) or not path.is_file():
        raise ValueError("candidate_file_unavailable")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != str(change.get("candidate_content_digest") or ""):
        raise ValueError("candidate_file_digest_mismatch")
    if len(content) != int(change.get("candidate_size_bytes") or -1):
        raise ValueError("candidate_file_size_mismatch")
    return content


def _prepared_candidate_integrity(request_id: str, application: Mapping[str, Any], *, runtime_root=None) -> tuple[bool, str]:
    workspace = _read_json(_workspace_record_path(request_id, runtime_root))
    if not workspace:
        return False, "candidate_workspace_record_missing"
    try:
        root = _candidate_workspace_root(workspace)
        for change in application.get("changes") or []:
            relative = _safe_relative(str(change.get("relative_path") or ""))
            path = root / Path(*PurePosixPath(relative).parts)
            if not _within(root, path):
                return False, "candidate_workspace_path_escape"
            if str(change.get("operation") or "") == "delete":
                if path.exists():
                    return False, "candidate_delete_path_reappeared"
            else:
                _workspace_candidate_bytes(request_id, change, runtime_root=runtime_root)
        return True, "candidate_workspace_integrity_ok"
    except (OSError, ValueError):
        return False, "candidate_workspace_integrity_changed"


def _application_scope_states(project_root: Path, application: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [_current_path_state(project_root, row) for row in application.get("changes") or []]


def _all_state(states: Sequence[Mapping[str, Any]], state: str) -> bool:
    return bool(states) and all(str(row.get("state") or "") == state for row in states)


def _capture_backup(request_id: str, application: Mapping[str, Any], project_root: Path, *, runtime_root=None) -> dict[str, Any]:
    path = _backup_manifest_path(request_id, runtime_root)
    existing = _read_json(path)
    if existing:
        if not validate_private_backup_manifest(existing, expected_application_digest=str(application.get("application_digest") or "")):
            raise ValueError("private_backup_manifest_invalid")
        return existing
    manifest = build_private_backup_manifest(request_id, application, project_root)
    # The manifest must reflect the baseline state that the immutable packet
    # authorized.  If it does not, somebody changed an affected path after
    # preparation and before authorization.
    by_path = {str(row.get("relative_path") or ""): row for row in manifest.get("entries") or []}
    for change in application.get("changes") or []:
        relative = str(change.get("relative_path") or "")
        entry = by_path.get(relative) or {}
        if bool(entry.get("existed")) != bool(change.get("baseline_existed")):
            raise ValueError("affected_path_changed_before_backup")
        if str(entry.get("content_digest") or "") != str(change.get("baseline_content_digest") or ""):
            raise ValueError("affected_path_changed_before_backup")
    _atomic_json(path, manifest)
    return manifest


def _write_candidate_file(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.eidolon-", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        try:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        except OSError:
            pass


def _apply_candidate(request_id: str, application: Mapping[str, Any], project_root: Path, *, runtime_root=None) -> list[str]:
    # Preflight every path and every candidate byte payload before the first
    # selected-project mutation.  This prevents half an operation because the
    # last file turned out to be invalid.
    payloads: dict[str, bytes] = {}
    for change in application.get("changes") or []:
        relative = _safe_relative(str(change.get("relative_path") or ""))
        target = _safe_target(project_root, relative)
        state = _current_path_state(project_root, change)
        if state.get("state") != "baseline":
            raise ValueError(f"affected_path_not_at_baseline:{relative}")
        if str(change.get("operation") or "") != "delete":
            payloads[relative] = _workspace_candidate_bytes(request_id, change, runtime_root=runtime_root)
        elif target.exists() and not target.is_file():
            raise ValueError("delete_target_not_regular_file")

    applied: list[str] = []
    for change in application.get("changes") or []:
        relative = _safe_relative(str(change.get("relative_path") or ""))
        target = _safe_target(project_root, relative, create_parent=str(change.get("operation") or "") != "delete")
        operation = str(change.get("operation") or "")
        if operation == "delete":
            if target.exists():
                target.unlink()
        else:
            _write_candidate_file(target, payloads[relative])
        applied.append(relative)
    return applied


def _decode_backup(entry: Mapping[str, Any]) -> bytes:
    if not entry.get("existed"):
        return b""
    content = base64.b64decode(str(entry.get("content_b64") or ""), validate=True)
    if hashlib.sha256(content).hexdigest() != str(entry.get("content_digest") or ""):
        raise ValueError("backup_entry_digest_mismatch")
    return content


def _remove_empty_parents(project_root: Path, target: Path) -> None:
    current = target.parent
    while current != project_root:
        if not _within(project_root, current) or _is_link_like(current):
            return
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _restore_backup(project_root: Path, backup: Mapping[str, Any]) -> list[str]:
    if not validate_private_backup_manifest(backup, expected_application_digest=str(backup.get("application_digest") or "")):
        raise ValueError("backup_manifest_invalid")
    restored: list[str] = []
    for entry in backup.get("entries") or []:
        relative = _safe_relative(str(entry.get("relative_path") or ""))
        target = _safe_target(project_root, relative, create_parent=bool(entry.get("existed")))
        if entry.get("existed"):
            _write_candidate_file(target, _decode_backup(entry))
        else:
            if target.exists():
                if _is_link_like(target) or not target.is_file():
                    raise ValueError("rollback_new_path_not_regular_file")
                target.unlink()
            _remove_empty_parents(project_root, target)
        restored.append(relative)
    return restored


def _backup_matches(project_root: Path, backup: Mapping[str, Any]) -> bool:
    if not validate_private_backup_manifest(backup, expected_application_digest=str(backup.get("application_digest") or "")):
        return False
    try:
        for entry in backup.get("entries") or []:
            relative = _safe_relative(str(entry.get("relative_path") or ""))
            target = _safe_target(project_root, relative)
            exists = target.is_file()
            if exists != bool(entry.get("existed")):
                return False
            if exists and _file_digest(target) != str(entry.get("content_digest") or ""):
                return False
        return True
    except (OSError, ValueError):
        return False


def _candidate_matches(project_root: Path, application: Mapping[str, Any]) -> bool:
    try:
        return _all_state(_application_scope_states(project_root, application), "candidate")
    except (OSError, ValueError):
        return False


def _restore_candidate_known_state(request_id: str, application: Mapping[str, Any], project_root: Path, *, runtime_root=None) -> None:
    states = _application_scope_states(project_root, application)
    if any(str(row.get("state") or "") not in {"baseline", "candidate"} for row in states):
        raise ValueError("candidate_recovery_conflict")
    payloads: dict[str, bytes] = {}
    for change in application.get("changes") or []:
        relative = _safe_relative(str(change.get("relative_path") or ""))
        if str(change.get("operation") or "") != "delete":
            payloads[relative] = _workspace_candidate_bytes(request_id, change, runtime_root=runtime_root)
    for change in application.get("changes") or []:
        relative = _safe_relative(str(change.get("relative_path") or ""))
        target = _safe_target(project_root, relative, create_parent=str(change.get("operation") or "") != "delete")
        if str(change.get("operation") or "") == "delete":
            if target.exists():
                if _is_link_like(target) or not target.is_file():
                    raise ValueError("candidate_delete_recovery_nonfile")
                target.unlink()
        else:
            _write_candidate_file(target, payloads[relative])


def _bounded_process(command: list[str], cwd: Path, *, timeout: int) -> dict[str, Any]:
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "NO_PROXY": "*", "no_proxy": "*"})
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = bytes(completed.stdout or b"")
        return {
            "passed": completed.returncode == 0,
            "exit_class": "zero" if completed.returncode == 0 else "nonzero",
            "output_digest": hashlib.sha256(output).hexdigest(),
            "output_bytes": len(output),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        output = bytes(exc.stdout or b"")
        return {
            "passed": False,
            "exit_class": "timeout",
            "output_digest": hashlib.sha256(output).hexdigest(),
            "output_bytes": len(output),
            "duration_ms": int((time.monotonic() - started) * 1000),
        }


def _verify_applied_project(
    request_id: str,
    project_root: Path,
    application: Mapping[str, Any],
    *,
    runtime_root=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    import ast

    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    project_type = str(inspection.get("project_type") or "")
    manifest_ok = _candidate_matches(project_root, application)
    command_results: list[dict[str, Any]] = []
    tests_executed = False
    passed = manifest_ok
    verification_kind = "manifest_only"

    if manifest_ok and (project_type == "python_project" or any(str(row.get("relative_path") or "").endswith(".py") for row in application.get("changes") or [])):
        syntax_rows = []
        for path in sorted(project_root.rglob("*.py")):
            if not path.is_file() or _is_link_like(path) or not _within(project_root, path):
                passed = False
                syntax_rows.append({"path": path, "passed": False})
                break
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
                syntax_rows.append({"path": path, "passed": True})
            except (OSError, UnicodeError, SyntaxError):
                syntax_rows.append({"path": path, "passed": False})
                passed = False
                break
        command_results.append({
            "phase": "python_syntax",
            "passed": passed,
            "exit_class": "zero" if passed else "nonzero",
            "output_digest": _digest([{"path_digest": hashlib.sha256(str(row["path"].relative_to(project_root)).encode()).hexdigest(), "passed": row["passed"]} for row in syntax_rows]),
            "output_bytes": 0,
            "duration_ms": 0,
        })
        verification_kind = "python_syntax"
        tests_dir = project_root / "tests"
        if passed and tests_dir.is_dir() and not _is_link_like(tests_dir):
            interpreter = str(python_executable or os.sys.executable)
            runner = (
                "import os,sys,unittest;root=sys.argv[1];sys.path.insert(0,root);"
                "suite=unittest.defaultTestLoader.discover(os.path.join(root,'tests'),pattern='test*.py');"
                "stream=open(os.devnull,'w');result=unittest.TextTestRunner(stream=stream,verbosity=0).run(suite);"
                "stream.close();sys.exit(0 if result.wasSuccessful() else 1)"
            )
            row = _bounded_process([interpreter, "-I", "-B", "-c", runner, str(project_root)], project_root, timeout=20)
            row["phase"] = "python_unittest_discover"
            command_results.append(row)
            tests_executed = True
            passed = passed and bool(row.get("passed"))
            verification_kind = "python_syntax_and_tests"
    elif manifest_ok and project_type in {"javascript_project", "javascript_web_project"}:
        node = str(node_executable or "node")
        js_files = sorted(path for path in project_root.rglob("*.js") if path.is_file() and not _is_link_like(path))
        for path in js_files[:256]:
            row = _bounded_process([node, "--check", str(path.relative_to(project_root))], project_root, timeout=10)
            row["phase"] = "node_syntax"
            command_results.append(row)
            if not row.get("passed"):
                passed = False
                break
        verification_kind = "node_syntax"
        tests = sorted([p for p in project_root.rglob("*.test.js") if p.is_file()] + [p for p in project_root.rglob("*.spec.js") if p.is_file()])
        if passed and tests:
            row = _bounded_process([node, "--test", *[str(path.relative_to(project_root)) for path in tests[:128]]], project_root, timeout=20)
            row["phase"] = "node_test"
            command_results.append(row)
            tests_executed = True
            passed = passed and bool(row.get("passed"))
            verification_kind = "node_syntax_and_tests"

    public_commands = [{
        "phase": str(row.get("phase") or ""),
        "passed": bool(row.get("passed")),
        "exit_class": str(row.get("exit_class") or ""),
        "output_digest": str(row.get("output_digest") or ""),
        "output_bytes": int(row.get("output_bytes") or 0),
        "duration_ms": int(row.get("duration_ms") or 0),
    } for row in command_results]
    result = {
        "ok": True,
        "status": "controlled_application_verification_passed" if passed else "controlled_application_verification_failed",
        "request_id": request_id,
        "project_type": project_type,
        "verification_kind": verification_kind,
        "passed": bool(passed),
        "tests_executed": tests_executed,
        "cleanup_confirmed": True,
        "command_results": public_commands,
        "candidate_manifest_verified": manifest_ok,
        "network_allowed": False,
        "dependencies_installed": False,
        "provider_contacted": False,
        "raw_output_exposed": False,
    }
    result["verification_digest"] = _digest(result)
    return result


def _prepare_execution_record(application: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    request_id = str(application.get("request_id") or "")
    path = _execution_path(request_id, runtime_root)
    existing = _read_json(path)
    if existing:
        if not _valid(existing, "execution_record_digest"):
            return _failure("controlled_application_execution_record_invalid", request_id=request_id)
        return existing
    record = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "controlled_application_execution_prepared",
        "phase": "prepared",
        "request_id": request_id,
        "application_digest": application.get("application_digest", ""),
        "application_request_record_digest": application.get("application_request_record_digest", ""),
        "lease_token": "",
        "lease_expires_unix": 0.0,
        "recovery_count": 0,
        "authorization_consumed": False,
        "backup_prepared": False,
        "selected_project_modified": False,
        **DENIED_AUTHORITY,
    }
    record = _sealed(record, "execution_record_digest")
    _atomic_json(path, record)
    return record


def _seal_application_result(
    application: Mapping[str, Any],
    execution: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    runtime_root=None,
) -> dict[str, Any]:
    request_id = str(application.get("request_id") or "")
    current = dict(execution)
    current.update({
        "status": str(result.get("status") or "controlled_application_failed"),
        "phase": "sealed",
        "lease_token": "",
        "lease_expires_unix": 0.0,
        "result": dict(result),
        "result_digest": _digest(result),
        "backup_prepared": bool(result.get("backup_prepared")),
        "selected_project_modified": bool(result.get("selected_project_modified")),
        "authorization_consumed": True,
        **DENIED_AUTHORITY,
    })
    current = _sealed(current, "execution_record_digest")
    _atomic_json(_execution_path(request_id, runtime_root), current)
    return current


def authorize_and_apply_controlled_candidate(
    request_id: str,
    *,
    expected_application_digest: str,
    authorization_phrase: str,
    runtime_root=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    request_id = _request_id(request_id)
    application = prepare_controlled_application(request_id, runtime_root=runtime_root)
    if application.get("ok") is not True:
        return application
    if str(application.get("application_digest") or "") != str(expected_application_digest or ""):
        return _failure("controlled_application_stale_authorization", request_id=request_id)
    if str(authorization_phrase or "").strip().casefold() != _application_authorization_phrase(request_id, expected_application_digest).casefold():
        return _failure("controlled_application_exact_authorization_required", request_id=request_id)

    # Exact replay of an already sealed application is idempotent and does not
    # reinterpret the now-applied candidate as a fresh preflight conflict.
    prior_execution = _read_json(_execution_path(request_id, runtime_root))
    recovery_reentry = False
    if prior_execution and _valid(prior_execution, "execution_record_digest"):
        if prior_execution.get("phase") == "sealed":
            prior_result = dict(prior_execution.get("result") or {})
            if prior_result and str(prior_execution.get("result_digest") or "") == _digest(prior_result):
                return {**prior_result, "operation_status": "restored"}
        if prior_execution.get("phase") == "running":
            if float(prior_execution.get("lease_expires_unix") or 0.0) > time.time():
                return _failure("controlled_application_in_progress", request_id=request_id)
            recovery_reentry = True

    request_state = load_coding_work_request(request_id, runtime_root=runtime_root)
    if not request_state or request_state.get("cancelled"):
        return _failure("coding_work_request_cancelled", request_id=request_id)
    candidate_ok, candidate_status = _prepared_candidate_integrity(request_id, application, runtime_root=runtime_root)
    if not candidate_ok:
        return _failure(candidate_status, request_id=request_id)

    # Recheck affected paths immediately before consuming a new exact
    # authorization. An expired running record already consumed its authority;
    # its recovery path below accepts only baseline/candidate states.
    if not recovery_reentry:
        preflight = inspect_controlled_application_conflicts(request_id, runtime_root=runtime_root)
        if preflight.get("ok") is not True or preflight.get("candidate_already_present") or preflight.get("mixed_known_state"):
            return _failure(str(preflight.get("status") or "controlled_application_conflict_detected"), request_id=request_id)

    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(request_id, runtime_root):
        existing_result = _read_json(_execution_path(request_id, runtime_root))
        if existing_result and _valid(existing_result, "execution_record_digest") and existing_result.get("phase") == "sealed":
            result = dict(existing_result.get("result") or {})
            if result and str(existing_result.get("result_digest") or "") == _digest(result):
                return {**result, "operation_status": "restored"}
        execution = _prepare_execution_record(application, runtime_root=runtime_root)
        if execution.get("ok") is not True:
            return execution
        if execution.get("phase") == "running" and float(execution.get("lease_expires_unix") or 0.0) > time.time():
            return _failure("controlled_application_in_progress", request_id=request_id)
        recovery_count = int(execution.get("recovery_count") or 0) + int(execution.get("phase") == "running")
        auth = _read_json(_authorization_path(request_id, runtime_root))
        if auth:
            if not _valid(auth, "authorization_record_digest") or str(auth.get("application_digest") or "") != expected_application_digest:
                return _failure("controlled_application_authorization_record_invalid", request_id=request_id)
        else:
            auth = _sealed({
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "request_id": request_id,
                "application_digest": expected_application_digest,
                "authorization_consumed": True,
                "consumption_count": 1,
                "authorization_phrase_digest": hashlib.sha256(str(authorization_phrase).encode("utf-8")).hexdigest(),
            }, "authorization_record_digest")
            _atomic_json(_authorization_path(request_id, runtime_root), auth)
        running = dict(execution)
        running.update({
            "status": "controlled_application_running",
            "phase": "running",
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + LEASE_SECONDS,
            "recovery_count": recovery_count,
            "authorization_consumed": True,
            **_execution_authority(),
        })
        running = _sealed(running, "execution_record_digest")
        _atomic_json(_execution_path(request_id, runtime_root), running)
        execution = running

    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    try:
        if not request or request.get("cancelled"):
            raise ValueError("coding_work_request_cancelled")
        project_root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
        states = _application_scope_states(project_root, application)
        # Recovery is safe only when every affected path is either exactly the
        # original baseline or exactly this candidate.  An unknown third state
        # is an operator conflict and must not be overwritten automatically.
        if any(str(row.get("state") or "") not in {"baseline", "candidate"} for row in states):
            result = _failure("controlled_application_recovery_conflict", request_id=request_id)
            result.update({"backup_prepared": bool(_read_json(_backup_manifest_path(request_id, runtime_root))), "recovery_count": recovery_count})
        else:
            backup = _read_json(_backup_manifest_path(request_id, runtime_root))
            if backup:
                if not validate_private_backup_manifest(backup, expected_application_digest=expected_application_digest):
                    raise ValueError("private_backup_manifest_invalid")
            elif _all_state(states, "baseline"):
                backup = _capture_backup(request_id, application, project_root, runtime_root=runtime_root)
            else:
                # A process died after at least one write but before persisting a
                # backup would violate the write ordering contract, so fail closed.
                raise ValueError("recovery_backup_missing")

            _write_journal(
                _journal_path(request_id, runtime_root),
                request_id=request_id,
                application_digest=expected_application_digest,
                phase="authorized_apply",
                backup_manifest_digest=backup.get("backup_manifest_digest", ""),
                recovery_count=recovery_count,
            )

            if not _all_state(states, "candidate"):
                if not _all_state(states, "baseline"):
                    # Known partial state from our own interrupted apply. Restore
                    # the exact backup first, then retry the single authorized
                    # transaction from a clean baseline.
                    _restore_backup(project_root, backup)
                    if not _backup_matches(project_root, backup):
                        raise ValueError("interrupted_apply_backup_restore_failed")
                _write_journal(
                    _journal_path(request_id, runtime_root),
                    request_id=request_id,
                    application_digest=expected_application_digest,
                    phase="writing_candidate",
                    backup_manifest_digest=backup.get("backup_manifest_digest", ""),
                    recovery_count=recovery_count,
                )
                _apply_candidate(request_id, application, project_root, runtime_root=runtime_root)

            if not _candidate_matches(project_root, application):
                raise ValueError("post_apply_candidate_manifest_mismatch")
            verification = _verify_applied_project(
                request_id,
                project_root,
                application,
                runtime_root=runtime_root,
                python_executable=python_executable,
                node_executable=node_executable,
            )
            if verification.get("passed") is not True:
                _restore_backup(project_root, backup)
                restored = _backup_matches(project_root, backup)
                result = {
                    "ok": False,
                    "schema_version": SCHEMA_VERSION,
                    "contract_version": CONTRACT_VERSION,
                    "status": "controlled_application_verification_failed_rolled_back" if restored else "controlled_application_verification_failed_rollback_incomplete",
                    "request_id": request_id,
                    "application_digest": expected_application_digest,
                    "backup_manifest_digest": backup.get("backup_manifest_digest", ""),
                    "backup_prepared": True,
                    "verification": verification,
                    "verification_digest": verification.get("verification_digest", ""),
                    "rollback_executed": True,
                    "rollback_verified": restored,
                    "selected_project_modified": not restored,
                    "recovery_count": recovery_count,
                    "authorization_consumption_count": 1,
                    "operator_review_required": True,
                    **DENIED_AUTHORITY,
                }
            else:
                result = {
                    "ok": True,
                    "schema_version": SCHEMA_VERSION,
                    "contract_version": CONTRACT_VERSION,
                    "status": "controlled_application_completed_recovered" if recovery_count else "controlled_application_completed",
                    "request_id": request_id,
                    "application_digest": expected_application_digest,
                    "backup_manifest_digest": backup.get("backup_manifest_digest", ""),
                    "backup_prepared": True,
                    "applied_count": int(application.get("change_count") or 0),
                    "candidate_manifest_verified": True,
                    "verification": verification,
                    "verification_digest": verification.get("verification_digest", ""),
                    "tests_executed": bool(verification.get("tests_executed")),
                    "verification_passed": True,
                    "rollback_available": True,
                    "rollback_executed": False,
                    "selected_project_modified": True,
                    "recovery_count": recovery_count,
                    "authorization_consumption_count": 1,
                    "operator_review_required": True,
                    "provider_contacted": False,
                    "dependency_installation_performed": False,
                    "release_performed": False,
                    **DENIED_AUTHORITY,
                }
            result["application_result_digest"] = _digest(result)
    except Exception as exc:
        reason = str(exc)
        try:
            project_root = _resolve_project_root((request.get("target") or {}).get("private_path") or "") if request else None
            backup = _read_json(_backup_manifest_path(request_id, runtime_root))
            restored = False
            if project_root and backup and validate_private_backup_manifest(backup, expected_application_digest=expected_application_digest):
                states = _application_scope_states(project_root, application)
                # Never overwrite a third-party unknown state during failure
                # recovery. Only states equal to baseline or this candidate are
                # safe to normalize back to the sealed backup.
                if all(str(row.get("state") or "") in {"baseline", "candidate"} for row in states):
                    _restore_backup(project_root, backup)
                    restored = _backup_matches(project_root, backup)
            result = _failure("controlled_application_failed_rolled_back" if restored else "controlled_application_failed", request_id=request_id, reason=hashlib.sha256(reason.encode()).hexdigest())
            result.update({
                "backup_prepared": bool(backup),
                "rollback_executed": bool(restored),
                "rollback_verified": bool(restored),
                "selected_project_modified": False if restored else bool(backup),
                "recovery_count": recovery_count,
                "authorization_consumption_count": 1,
            })
            result["application_result_digest"] = _digest(result)
        except Exception:
            result = _failure("controlled_application_internal_recovery_failed", request_id=request_id, reason=hashlib.sha256(reason.encode()).hexdigest())
            result.update({"backup_prepared": True, "selected_project_modified": True, "recovery_count": recovery_count, "authorization_consumption_count": 1})
            result["application_result_digest"] = _digest(result)

    with _proposal_lock(request_id, runtime_root):
        current = _read_json(_execution_path(request_id, runtime_root))
        if not current or not _valid(current, "execution_record_digest") or str(current.get("lease_token") or "") != lease_token:
            return _failure("controlled_application_lease_lost", request_id=request_id)
        _seal_application_result(application, current, result, runtime_root=runtime_root)
        _write_journal(
            _journal_path(request_id, runtime_root),
            request_id=request_id,
            application_digest=expected_application_digest,
            phase="sealed",
            result_digest=result.get("application_result_digest", result.get("result_digest", "")),
            recovery_count=recovery_count,
        )
    return {**result, "operation_status": "recovered" if recovery_count else "created"}


def load_controlled_application_execution(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    row = _read_json(_execution_path(request_id, runtime_root))
    return row if row and _valid(row, "execution_record_digest") else {}


def _rollback_authorization_phrase(request_id: str, rollback_digest: str) -> str:
    return f"Authorize controlled rollback for request {request_id} packet {rollback_digest}."


def prepare_controlled_rollback(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    path = _rollback_request_path(request_id, runtime_root)
    with _proposal_lock(request_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "rollback_request_record_digest"):
                return _failure("controlled_rollback_request_invalid", request_id=request_id)
            return {**existing, "operation_status": "restored"}
        application = load_controlled_application(request_id, runtime_root=runtime_root)
        execution = load_controlled_application_execution(request_id, runtime_root=runtime_root)
        result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
        backup = _read_json(_backup_manifest_path(request_id, runtime_root))
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        if not application or not execution or not result.get("ok") or not backup or not request:
            return _failure("successful_controlled_application_required", request_id=request_id)
        if not validate_private_backup_manifest(backup, expected_application_digest=str(application.get("application_digest") or "")):
            return _failure("controlled_rollback_backup_invalid", request_id=request_id)
        try:
            project_root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
            states = _application_scope_states(project_root, application)
        except (OSError, ValueError) as exc:
            return _failure("controlled_rollback_target_unavailable", request_id=request_id, reason=str(exc))
        if not _all_state(states, "candidate"):
            return _failure("controlled_rollback_conflict_detected", request_id=request_id)
        bindings = {
            "application_digest": application.get("application_digest", ""),
            "application_result_digest": result.get("application_result_digest", ""),
            "backup_manifest_digest": backup.get("backup_manifest_digest", ""),
        }
        rollback_digest = _digest({"request_id": request_id, "bindings": bindings})
        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "controlled_rollback_authorization_required",
            "phase": "prepared",
            "request_id": request_id,
            "rollback_digest": rollback_digest,
            "authorization_phrase": _rollback_authorization_phrase(request_id, rollback_digest),
            "bindings": bindings,
            "restore_count": int(backup.get("entry_count") or 0),
            "backup_manifest_valid": True,
            "selected_project_modified": True,
            "operator_review_required": True,
            **DENIED_AUTHORITY,
        }
        record = _sealed(record, "rollback_request_record_digest")
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def authorize_and_rollback_controlled_candidate(
    request_id: str,
    *,
    expected_rollback_digest: str,
    authorization_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    request_id = _request_id(request_id)
    rollback = prepare_controlled_rollback(request_id, runtime_root=runtime_root)
    if rollback.get("ok") is not True:
        return rollback
    if str(rollback.get("rollback_digest") or "") != str(expected_rollback_digest or ""):
        return _failure("controlled_rollback_stale_authorization", request_id=request_id)
    if str(authorization_phrase or "").strip().casefold() != _rollback_authorization_phrase(request_id, expected_rollback_digest).casefold():
        return _failure("controlled_rollback_exact_authorization_required", request_id=request_id)

    with _proposal_lock(request_id, runtime_root):
        existing = _read_json(_rollback_result_path(request_id, runtime_root))
        if existing and _valid(existing, "rollback_result_record_digest"):
            return {**existing, "operation_status": "restored"}
        auth = _read_json(_rollback_authorization_path(request_id, runtime_root))
        if auth:
            if not _valid(auth, "authorization_record_digest") or str(auth.get("rollback_digest") or "") != expected_rollback_digest:
                return _failure("controlled_rollback_authorization_record_invalid", request_id=request_id)
        else:
            auth = _sealed({
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "request_id": request_id,
                "rollback_digest": expected_rollback_digest,
                "authorization_consumed": True,
                "consumption_count": 1,
                "authorization_phrase_digest": hashlib.sha256(str(authorization_phrase).encode("utf-8")).hexdigest(),
            }, "authorization_record_digest")
            _atomic_json(_rollback_authorization_path(request_id, runtime_root), auth)

        application = load_controlled_application(request_id, runtime_root=runtime_root)
        backup = _read_json(_backup_manifest_path(request_id, runtime_root))
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        if not application or not backup or not request or not validate_private_backup_manifest(backup, expected_application_digest=str(application.get("application_digest") or "")):
            return _failure("controlled_rollback_lineage_invalid", request_id=request_id)
        try:
            project_root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
            states = _application_scope_states(project_root, application)
            if any(str(row.get("state") or "") not in {"baseline", "candidate"} for row in states):
                return _failure("controlled_rollback_conflict_detected", request_id=request_id)
            _write_journal(
                _rollback_journal_path(request_id, runtime_root),
                request_id=request_id,
                rollback_digest=expected_rollback_digest,
                phase="restoring_backup",
                backup_manifest_digest=backup.get("backup_manifest_digest", ""),
            )
            _restore_backup(project_root, backup)
            restored = _backup_matches(project_root, backup)
            if not restored:
                raise ValueError("controlled_rollback_restore_verification_failed")
            result = {
                "ok": True,
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "status": "controlled_rollback_completed",
                "phase": "sealed",
                "request_id": request_id,
                "rollback_digest": expected_rollback_digest,
                "application_digest": application.get("application_digest", ""),
                "backup_manifest_digest": backup.get("backup_manifest_digest", ""),
                "restored_count": int(backup.get("entry_count") or 0),
                "rollback_verified": True,
                "selected_project_modified": True,
                "authorization_consumption_count": 1,
                "operator_review_required": True,
                **DENIED_AUTHORITY,
            }
        except Exception as exc:
            # If rollback itself fails, restore the already-authorized applied
            # candidate so the project returns to a known state rather than a
            # half-rollback.  This does not expand authority; it narrows failure.
            candidate_restored = False
            try:
                _restore_candidate_known_state(request_id, application, project_root, runtime_root=runtime_root)
                candidate_restored = _candidate_matches(project_root, application)
            except Exception:
                candidate_restored = False
            result = {
                "ok": False,
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "status": "controlled_rollback_failed_applied_state_restored" if candidate_restored else "controlled_rollback_failed_manual_recovery_required",
                "phase": "sealed",
                "request_id": request_id,
                "rollback_digest": expected_rollback_digest,
                "application_digest": application.get("application_digest", ""),
                "backup_manifest_digest": backup.get("backup_manifest_digest", ""),
                "rollback_verified": False,
                "applied_state_restored": candidate_restored,
                "reason_digest": hashlib.sha256(str(exc).encode()).hexdigest(),
                "selected_project_modified": True,
                "authorization_consumption_count": 1,
                "operator_review_required": True,
                **DENIED_AUTHORITY,
            }
        result["rollback_result_digest"] = _digest(result)
        sealed = _sealed(result, "rollback_result_record_digest")
        _atomic_json(_rollback_result_path(request_id, runtime_root), sealed)
        _write_journal(
            _rollback_journal_path(request_id, runtime_root),
            request_id=request_id,
            rollback_digest=expected_rollback_digest,
            phase="sealed",
            result_digest=result.get("rollback_result_digest", ""),
        )
        return {**sealed, "operation_status": "created"}


def load_controlled_rollback(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    row = _read_json(_rollback_request_path(request_id, runtime_root))
    return row if row and _valid(row, "rollback_request_record_digest") else {}


def load_controlled_rollback_result(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    row = _read_json(_rollback_result_path(request_id, runtime_root))
    return row if row and _valid(row, "rollback_result_record_digest") else {}


def public_controlled_application_result(record: Mapping[str, Any]) -> dict[str, Any]:
    result = record.get("result") if isinstance(record.get("result"), Mapping) else record
    verification = result.get("verification") if isinstance(result.get("verification"), Mapping) else {}
    return {
        "ok": bool(result.get("ok")),
        "status": str(result.get("status") or record.get("status") or ""),
        "request_id": str(result.get("request_id") or record.get("request_id") or ""),
        "application_digest": str(result.get("application_digest") or record.get("application_digest") or ""),
        "applied_count": int(result.get("applied_count") or 0),
        "backup_prepared": bool(result.get("backup_prepared")),
        "verification_passed": bool(result.get("verification_passed")),
        "tests_executed": bool(result.get("tests_executed")),
        "verification_digest": str(result.get("verification_digest") or verification.get("verification_digest") or ""),
        "rollback_available": bool(result.get("rollback_available")),
        "rollback_executed": bool(result.get("rollback_executed")),
        "selected_project_modified": bool(result.get("selected_project_modified")),
        "recovery_count": int(result.get("recovery_count") or 0),
        "operator_review_required": True,
        "private_project_path_exposed": False,
        "backup_content_exposed": False,
        "raw_test_output_exposed": False,
        "provider_payload_exposed": False,
        **DENIED_AUTHORITY,
    }


def public_controlled_rollback(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "request_id": str(record.get("request_id") or ""),
        "rollback_digest": str(record.get("rollback_digest") or ""),
        "restored_count": int(record.get("restored_count") or 0),
        "rollback_verified": bool(record.get("rollback_verified")),
        "selected_project_modified": bool(record.get("selected_project_modified")),
        "operator_review_required": True,
        "private_project_path_exposed": False,
        "backup_content_exposed": False,
        **DENIED_AUTHORITY,
    }


_PREPARE = re.compile(r"^prepare\s+controlled\s+application\s+for\s+request\s+(?P<request_id>devc_[a-f0-9]{24})[.!?]*$", re.I)
_APPLY = re.compile(r"^authorize\s+controlled\s+application\s+for\s+request\s+(?P<request_id>devc_[a-f0-9]{24})\s+packet\s+(?P<digest>[a-f0-9]{64})[.!?]*$", re.I)
_PREPARE_ROLLBACK = re.compile(r"^prepare\s+controlled\s+rollback\s+for\s+request\s+(?P<request_id>devc_[a-f0-9]{24})[.!?]*$", re.I)
_ROLLBACK = re.compile(r"^authorize\s+controlled\s+rollback\s+for\s+request\s+(?P<request_id>devc_[a-f0-9]{24})\s+packet\s+(?P<digest>[a-f0-9]{64})[.!?]*$", re.I)


def process_controlled_application_rollback_control(
    user_text: str,
    *,
    runtime_root=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _PREPARE.fullmatch(text)
    if match:
        row = prepare_controlled_application(match.group("request_id"), runtime_root=runtime_root)
        public = public_controlled_application(row)
        return {
            "active": True,
            "event": str(row.get("status") or "controlled_application_prepare_blocked"),
            "controlled_application": public,
            "conversation_response": (
                f"Controlled application for {public.get('request_id')} is prepared for {public.get('change_count', 0)} reviewed path(s). "
                "The selected project has not been modified. Use the exact application authorization shown in the packet to proceed."
                if row.get("ok") else
                f"Controlled application preparation stopped with status {row.get('status', 'blocked')}. No selected-project changes were made."
            ),
            "public_digest": _digest(public),
        }
    match = _APPLY.fullmatch(text)
    if match:
        row = authorize_and_apply_controlled_candidate(
            match.group("request_id"),
            expected_application_digest=match.group("digest").lower(),
            authorization_phrase=text,
            runtime_root=runtime_root,
            python_executable=python_executable,
            node_executable=node_executable,
        )
        public = public_controlled_application_result(row)
        return {
            "active": True,
            "event": str(row.get("status") or "controlled_application_blocked"),
            "controlled_application_result": public,
            "conversation_response": (
                f"Controlled application for {public.get('request_id')} completed and post-apply verification passed. A separate rollback authorization remains available."
                if row.get("ok") else
                f"Controlled application stopped with status {row.get('status', 'blocked')}. Review the sealed recovery evidence before any further mutation."
            ),
            "public_digest": _digest(public),
        }
    match = _PREPARE_ROLLBACK.fullmatch(text)
    if match:
        row = prepare_controlled_rollback(match.group("request_id"), runtime_root=runtime_root)
        public = public_controlled_rollback(row)
        public["authorization_phrase"] = str(row.get("authorization_phrase") or "") if row.get("phase") == "prepared" else ""
        return {
            "active": True,
            "event": str(row.get("status") or "controlled_rollback_prepare_blocked"),
            "controlled_rollback": public,
            "conversation_response": (
                f"Controlled rollback for {public.get('request_id')} is prepared. The applied candidate remains installed until the exact rollback authorization is given."
                if row.get("ok") else
                f"Controlled rollback preparation stopped with status {row.get('status', 'blocked')}."
            ),
            "public_digest": _digest(public),
        }
    match = _ROLLBACK.fullmatch(text)
    if match:
        row = authorize_and_rollback_controlled_candidate(
            match.group("request_id"),
            expected_rollback_digest=match.group("digest").lower(),
            authorization_phrase=text,
            runtime_root=runtime_root,
        )
        public = public_controlled_rollback(row)
        return {
            "active": True,
            "event": str(row.get("status") or "controlled_rollback_blocked"),
            "controlled_rollback_result": public,
            "conversation_response": (
                f"Controlled rollback for {public.get('request_id')} completed and the sealed pre-apply state was restored."
                if row.get("ok") else
                f"Controlled rollback stopped with status {row.get('status', 'blocked')}. Review recovery evidence before further mutation."
            ),
            "public_digest": _digest(public),
        }
    return {"active": False, "event": "inactive"}


__all__ = [
    "CONTRACT_VERSION",
    "authorize_and_apply_controlled_candidate",
    "prepare_controlled_rollback",
    "authorize_and_rollback_controlled_candidate",
    "load_controlled_application_execution",
    "load_controlled_rollback",
    "load_controlled_rollback_result",
    "public_controlled_application_result",
    "public_controlled_rollback",
    "process_controlled_application_rollback_control",
]
