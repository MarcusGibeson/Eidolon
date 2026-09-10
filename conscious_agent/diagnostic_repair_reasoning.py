from __future__ import annotations

"""v1257.3-v1257.5 focused diagnostics and repair reasoning integration.

This module runs only inside an already-authorized v1254 isolated coding
execution.  It consumes a failed sealed attempt, executes bounded diagnostics
inside the disposable workspace, ranks the previously-declared competing
hypotheses, and produces content-minimized repair guidance for the next v1254
provider attempt.  It never creates execution/application authority itself.
"""

import os
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from diagnostic_repair_reasoning_foundations import (
    CONTRACT_VERSION as FOUNDATION_CONTRACT_VERSION,
    DENIED_AUTHORITY,
    MAX_DIAGNOSTIC_PROBES,
    _result_path,
    _seal,
    _valid,
    create_or_restore_diagnostic_plan,
    load_diagnostic_result,
)
from isolated_coding_execution_foundations import _safe_relative, _walk_project
from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1257.5"
MAX_ISOLATED_TEST_FILES = 8


def _operation_path(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "diagnostic_repair_operations" / request_id / f"attempt-{int(attempt_number)}.json"


def _operation_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("operation_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "operation_digest"}))


def _seal_operation(record: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(record)
    row["operation_digest"] = _digest({k: v for k, v in row.items() if k != "operation_digest"})
    return row


def _failure(status: str, *, request_id: str = "", attempt_number: int = 0, reason: str = "") -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "request_id": request_id,
        "attempt_number": int(attempt_number),
        "reason": reason,
        "diagnostic_commands_executed": False,
        "provider_contacted": False,
        "repair_created": False,
        "selected_project_modified": False,
        "source_modified": False,
        "content_minimized": True,
        "raw_test_output_stored": False,
        **DENIED_AUTHORITY,
    }
    row["failure_digest"] = _digest(row)
    return row


def _execution_authorized(request_id: str, expected_execution_digest: str, *, runtime_root=None) -> bool:
    from isolated_coding_execution import load_isolated_coding_execution
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    return bool(
        execution
        and execution.get("phase") == "running"
        and execution.get("execution_authority_consumed") is True
        and str(execution.get("execution_digest") or "") == str(expected_execution_digest or "")
    )


def _workspace(request_id: str, *, runtime_root=None) -> tuple[Path | None, list[dict[str, Any]], str]:
    from isolated_coding_execution import _strict_workspace_integrity, _workspace_root_from_record
    record = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    if not record:
        return None, [], "workspace_record_missing"
    try:
        root = _workspace_root_from_record(record)
        ok, status = _strict_workspace_integrity(root)
        if not ok:
            return None, [], status
        files, _ = _walk_project(root)
        return root, files, "workspace_integrity_passed"
    except (OSError, ValueError):
        return None, [], "workspace_integrity_failed"


def _attempt(request_id: str, attempt_number: int, runtime_root=None) -> dict[str, Any]:
    path = _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id / f"attempt-{int(attempt_number)}.json"
    row = _read_json(path)
    if not row:
        return {}
    supplied = str(row.get("attempt_record_digest") or "")
    return row if supplied and supplied == _digest({k: v for k, v in row.items() if k != "attempt_record_digest"}) else {}


def _public_command(probe_code: str, row: Mapping[str, Any], *, path_digest: str = "", selection_digest: str = "") -> dict[str, Any]:
    return {
        "probe_code": probe_code,
        "path_digest": path_digest,
        "selection_digest": selection_digest,
        "passed": bool(row.get("passed")),
        "exit_class": str(row.get("exit_class") or ""),
        "output_digest": str(row.get("output_digest") or ""),
        "output_bytes": int(row.get("output_bytes") or 0),
        "cleanup_confirmed": bool(row.get("cleanup_confirmed", True)),
        "duration_ms": int(row.get("duration_ms") or 0),
    }


def _python_diagnostics(root: Path, files: Sequence[Mapping[str, Any]], attempt: Mapping[str, Any], *, request_id: str, attempt_number: int, runtime_root=None, python_executable: str | None = None) -> list[dict[str, Any]]:
    from isolated_coding_execution import _verification_private_root
    from node_javascript_test_adapter import _run_bounded_command
    from python_test_adapter import (
        PYTHON_PROBE_TIMEOUT_SECONDS, SYNTAX_TIMEOUT_SECONDS, TEST_TIMEOUT_SECONDS,
        _capability_contract_ok, _minimal_environment, _preferred_runner,
        _python_candidates, _read_workspace_sources, _runner_source, _select_python,
    )
    rows, failure = _read_workspace_sources(root, {"files": list(files)})
    if rows is None:
        return [{"probe_code": "python_source_contract", "passed": False, "outcome": str(failure.get("status") or "python_source_contract_rejected")}]
    py_rows = [row for row in rows if str(row.get("relative_path") or "").endswith(".py")]
    ok, rejected = _capability_contract_ok(py_rows)
    if not ok:
        return [{"probe_code": "python_capability_contract", "passed": False, "outcome": "python_test_capability_contract_rejected", "path_digest": rejected}]
    private = _verification_private_root(request_id, attempt_number, runtime_root) / "diagnostics"
    python, source_class, failures, _, cleanup = _select_python(_python_candidates(python_executable), cwd=root, private=private)
    if not python:
        return [{"probe_code": "python_runtime_probe", "passed": False, "outcome": "python_runtime_unavailable", "failure_digests": failures[:4], "cleanup_confirmed": cleanup}]
    env = _minimal_environment(python, private)
    output: list[dict[str, Any]] = [{"probe_code": "python_runtime_probe", "passed": True, "outcome": "python_runtime_available", "runtime_source_class": source_class, "cleanup_confirmed": cleanup}]

    changed = {str(row.get("relative_path") or "") for row in attempt.get("changes") or [] if str(row.get("operation") or "") != "delete"}
    syntax_source = "import ast,pathlib,sys;ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))"
    for row in py_rows:
        relative = str(row.get("relative_path") or "")
        if relative not in changed or row.get("is_test"):
            continue
        command = _run_bounded_command([python, "-I", "-B", "-c", syntax_source, str(row["path"])], cwd=root, env=env, timeout_seconds=SYNTAX_TIMEOUT_SECONDS)
        output.append(_public_command("changed_source_syntax_guard", command, path_digest=str(row.get("relative_path_digest") or "")))
        if len(output) >= MAX_DIAGNOSTIC_PROBES:
            return output

    tests = [row for row in py_rows if row.get("is_test")][:MAX_ISOLATED_TEST_FILES]
    if tests:
        runner = _preferred_runner(rows)
        if runner == "pytest":
            probe = _run_bounded_command([python, "-I", "-B", "-c", "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pytest') else 1)"], cwd=root, env=env, timeout_seconds=PYTHON_PROBE_TIMEOUT_SECONDS)
            output.append(_public_command("python_test_runner_probe", probe))
            if not probe.get("passed"):
                return output[:MAX_DIAGNOSTIC_PROBES]
        for row in tests:
            path_digest = str(row.get("relative_path_digest") or "")
            command = _run_bounded_command(
                [python, "-I", "-B", "-c", _runner_source(runner), str(root), str(private / "temp"), str(row["path"])],
                cwd=root, env=env, timeout_seconds=TEST_TIMEOUT_SECONDS,
            )
            output.append(_public_command("individual_test_file_isolation", command, path_digest=path_digest, selection_digest=_digest([path_digest])))
            if len(output) >= MAX_DIAGNOSTIC_PROBES:
                break
    return output[:MAX_DIAGNOSTIC_PROBES]


def _node_diagnostics(root: Path, files: Sequence[Mapping[str, Any]], attempt: Mapping[str, Any], *, request_id: str, attempt_number: int, runtime_root=None, node_executable: str | None = None) -> list[dict[str, Any]]:
    from isolated_coding_execution import _verification_private_root
    from node_javascript_test_adapter import (
        NODE_PROBE_TIMEOUT_SECONDS, TEST_TIMEOUT_SECONDS, _capability_contract_ok,
        _minimal_environment, _node_candidates, _read_workspace_sources,
        _run_bounded_command, _select_node,
    )
    rows, failure = _read_workspace_sources(root, {"files": list(files)})
    if rows is None:
        return [{"probe_code": "node_source_contract", "passed": False, "outcome": str(failure.get("status") or "node_source_contract_rejected")}]
    js_rows = [row for row in rows if PurePosixPath(str(row.get("relative_path") or "")).suffix.casefold() in {".js", ".mjs", ".cjs"}]
    ok, rejected = _capability_contract_ok(js_rows)
    if not ok:
        return [{"probe_code": "node_capability_contract", "passed": False, "outcome": "node_test_capability_contract_rejected", "path_digest": rejected}]
    private = _verification_private_root(request_id, attempt_number, runtime_root) / "diagnostics"
    node, source_class, failures, _, cleanup = _select_node(_node_candidates(node_executable), cwd=root, home=private)
    if not node:
        return [{"probe_code": "node_runtime_probe", "passed": False, "outcome": "node_runtime_unavailable", "failure_digests": failures[:4], "cleanup_confirmed": cleanup}]
    env = _minimal_environment(node, private)
    output: list[dict[str, Any]] = [{"probe_code": "node_runtime_probe", "passed": True, "outcome": "node_runtime_available", "runtime_source_class": source_class, "cleanup_confirmed": cleanup}]
    changed = {str(row.get("relative_path") or "") for row in attempt.get("changes") or [] if str(row.get("operation") or "") != "delete"}
    for row in js_rows:
        relative = str(row.get("relative_path") or "")
        if relative not in changed or row.get("is_test"):
            continue
        command = _run_bounded_command([node, "--check", str(row["path"])], cwd=root, env=env, timeout_seconds=NODE_PROBE_TIMEOUT_SECONDS)
        output.append(_public_command("changed_source_syntax_guard", command, path_digest=str(row.get("relative_path_digest") or "")))
        if len(output) >= MAX_DIAGNOSTIC_PROBES:
            return output
    tests = [row for row in js_rows if row.get("is_test")][:MAX_ISOLATED_TEST_FILES]
    for row in tests:
        path_digest = str(row.get("relative_path_digest") or "")
        command = _run_bounded_command([node, "--test", str(row["path"])], cwd=root, env=env, timeout_seconds=TEST_TIMEOUT_SECONDS)
        output.append(_public_command("individual_test_file_isolation", command, path_digest=path_digest, selection_digest=_digest([path_digest])))
        if len(output) >= MAX_DIAGNOSTIC_PROBES:
            break
    return output[:MAX_DIAGNOSTIC_PROBES]


def _static_diagnostics(root: Path, attempt: Mapping[str, Any]) -> list[dict[str, Any]]:
    from structured_development_generation import _syntax
    output: list[dict[str, Any]] = []
    for change in list(attempt.get("changes") or [])[:MAX_DIAGNOSTIC_PROBES]:
        relative = str(change.get("relative_path") or "")
        if str(change.get("operation") or "") == "delete":
            continue
        path = root / _safe_relative(relative)
        try:
            content = path.read_text(encoding="utf-8")
            _syntax(relative, content)
            passed, outcome = True, "static_changed_file_valid"
        except (OSError, UnicodeError, ValueError) as exc:
            passed, outcome = False, f"static_changed_file_invalid:{type(exc).__name__}"
        output.append({"probe_code": "changed_source_static_guard", "path_digest": _digest(relative), "passed": passed, "outcome": outcome, "cleanup_confirmed": True})
    return output


def _rank_hypotheses(plan: Mapping[str, Any], probes: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], str, str]:
    failed_tests = [row for row in probes if row.get("probe_code") == "individual_test_file_isolation" and row.get("passed") is False]
    failed_syntax = [row for row in probes if "syntax" in str(row.get("probe_code") or "") and row.get("passed") is False]
    failed_quality = [row for row in probes if row.get("probe_code") == "construction_quality_recheck" and row.get("passed") is False]
    environment_failed = [row for row in probes if str(row.get("outcome") or "").endswith("unavailable") or "capability_contract_rejected" in str(row.get("outcome") or "") or row.get("cleanup_confirmed") is False]
    ranked: list[dict[str, Any]] = []
    for hypothesis in list(plan.get("hypotheses") or []):
        row = dict(hypothesis)
        code = str(row.get("hypothesis_code") or "")
        support = 0
        contradicted = False
        if environment_failed:
            support += 4 if row.get("cause_class") == "environment" else 0
        if failed_syntax:
            support += 5 if code in {"changed_source_syntax_defect", "generated_change_incomplete_or_truncated", "implementation_defect"} else 0
            if row.get("cause_class") == "environment" and not environment_failed:
                contradicted = True
        if failed_tests:
            support += 4 if code in {"implementation_behavior_defect", "incomplete_requirement_coverage", "implementation_hang_or_unbounded_work", "implementation_defect"} else 0
            if code == "test_environment_or_runner_issue" and not environment_failed:
                contradicted = True
        if failed_quality:
            support += 6 if code in {"application_coherence_defect", "incomplete_cross_file_artifact_set", "implementation_defect"} else 0
            if code == "quality_contract_or_workspace_anomaly" and not environment_failed:
                contradicted = True
        if probes and not failed_tests and not failed_syntax and not failed_quality and not environment_failed and row.get("cause_class") == "environment":
            contradicted = True
        row.update({"support_score": support, "contradicted_by_diagnostics": contradicted, "root_cause_proven": False})
        ranked.append(row)
    ranked.sort(key=lambda row: (-int(row.get("support_score") or 0), bool(row.get("contradicted_by_diagnostics")), str(row.get("hypothesis_code") or "")))
    preferred = str(ranked[0].get("hypothesis_code") or "") if ranked else ""
    if environment_failed:
        posture = "blocked_environment"
    elif failed_syntax or failed_tests or failed_quality:
        posture = "repair_supported"
    elif probes and all(row.get("passed") is True for row in probes if "passed" in row):
        posture = "blocked_failure_not_reproduced"
    else:
        posture = "blocked_insufficient_evidence"
    return ranked, preferred, posture


def _verification_fingerprint(attempt: Mapping[str, Any]) -> str:
    verification = dict(attempt.get("verification") or {})
    # Output digests may legitimately vary because test runners include timing
    # metadata.  Repetition is therefore defined by the same repair strategy
    # reaching the same verification status, phase/exit classes, and bounded
    # test/path selections, not byte-identical human-facing output.
    return _digest({
        "status": verification.get("status", ""),
        "commands": [
            {key: row.get(key) for key in ("phase", "passed", "exit_class", "path_digest", "selection_digest")}
            for row in verification.get("command_results") or []
        ],
    })


def _repair_strategy_fingerprint(attempt: Mapping[str, Any]) -> str:
    return _digest([
        {
            "relative_path_digest": str(row.get("relative_path_digest") or ""),
            "operation": str(row.get("operation") or ""),
            "content_digest": str(row.get("content_digest") or ""),
        }
        for row in list(attempt.get("changes") or [])
    ])


def repeated_failed_repair_detected(request_id: str, attempt_number: int, *, runtime_root=None) -> bool:
    if int(attempt_number) <= 1:
        return False
    current = _attempt(request_id, attempt_number, runtime_root)
    prior = _attempt(request_id, int(attempt_number) - 1, runtime_root)
    if not current or not prior:
        return False
    if (current.get("verification") or {}).get("passed") is True or (prior.get("verification") or {}).get("passed") is True:
        return False
    return bool(
        _repair_strategy_fingerprint(current) == _repair_strategy_fingerprint(prior)
        and _verification_fingerprint(current) == _verification_fingerprint(prior)
    )


def run_focused_diagnostics(
    request_id: str,
    attempt_number: int,
    *,
    expected_execution_digest: str,
    runtime_root=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    attempt_number = int(attempt_number)
    result_path = _result_path(request_id, attempt_number, runtime_root)
    operation_path = _operation_path(request_id, attempt_number, runtime_root)

    # A sealed result is read-only evidence and may be restored without any
    # current execution authority.  New diagnostic work, however, requires the
    # exact already-running v1254 execution.
    with _proposal_lock(request_id, runtime_root):
        raw_result = _read_json(result_path)
        if raw_result:
            if not _valid(raw_result, "diagnostic_result_digest"):
                return _failure("diagnostic_result_record_invalid", request_id=request_id, attempt_number=attempt_number)
            return {**raw_result, "operation_status": "restored"}
    if not _execution_authorized(request_id, expected_execution_digest, runtime_root=runtime_root):
        return _failure("diagnostic_existing_execution_authority_required", request_id=request_id, attempt_number=attempt_number)

    from isolated_coding_execution_foundations import check_coding_source_freshness, load_coding_work_plan, load_coding_work_request
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    if not request or request.get("cancelled"):
        return _failure("diagnostic_request_cancelled_or_missing", request_id=request_id, attempt_number=attempt_number)
    freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
    if freshness.get("ok") is not True:
        return _failure("diagnostic_stale_source_detected", request_id=request_id, attempt_number=attempt_number)
    plan = create_or_restore_diagnostic_plan(request_id, attempt_number, runtime_root=runtime_root)
    if plan.get("ok") is not True:
        return plan
    attempt = _attempt(request_id, attempt_number, runtime_root)
    if not attempt:
        return _failure("diagnostic_attempt_missing_or_tampered", request_id=request_id, attempt_number=attempt_number)

    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(request_id, runtime_root):
        raw_result = _read_json(result_path)
        if raw_result:
            if not _valid(raw_result, "diagnostic_result_digest"):
                return _failure("diagnostic_result_record_invalid", request_id=request_id, attempt_number=attempt_number)
            return {**raw_result, "operation_status": "restored"}
        operation = _read_json(operation_path)
        if operation and not _operation_valid(operation):
            return _failure("diagnostic_operation_record_invalid", request_id=request_id, attempt_number=attempt_number)
        if operation and operation.get("phase") == "running" and float(operation.get("lease_expires_unix") or 0.0) > time.time():
            return _failure("diagnostic_operation_in_progress", request_id=request_id, attempt_number=attempt_number)
        recovery_count = int(operation.get("recovery_count") or 0) + int(bool(operation) and operation.get("phase") == "running")
        running = {
            "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "status": "diagnostic_operation_running", "phase": "running",
            "request_id": request_id, "attempt_number": attempt_number,
            "expected_execution_digest": str(expected_execution_digest or ""),
            "lease_token": lease_token, "lease_expires_unix": time.time() + 120.0,
            "recovery_count": recovery_count,
            "provider_contacted": False, "selected_project_modified": False, "source_modified": False,
        }
        _atomic_json(operation_path, _seal_operation(running))

    root, files, workspace_status = _workspace(request_id, runtime_root=runtime_root)
    if root is None:
        probes = [{"probe_code": "workspace_integrity_recheck", "passed": False, "outcome": workspace_status, "cleanup_confirmed": True}]
    else:
        probes = [{"probe_code": "workspace_integrity_recheck", "passed": True, "outcome": workspace_status, "cleanup_confirmed": True}]
        from isolated_coding_execution import _bounded_verification_files
        coding_plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
        files = _bounded_verification_files(files, coding_plan, attempt)
        project_type = str((plan.get("failure_observation") or {}).get("project_type") or "")
        if project_type == "python_project" or any(str(row.get("relative_path") or "").endswith(".py") for row in files):
            probes.extend(_python_diagnostics(root, files, attempt, request_id=request_id, attempt_number=attempt_number, runtime_root=runtime_root, python_executable=python_executable))
        elif project_type in {"javascript_project", "javascript_web_project"} or any(PurePosixPath(str(row.get("relative_path") or "")).suffix.casefold() in {".js", ".mjs", ".cjs"} for row in files):
            probes.extend(_node_diagnostics(root, files, attempt, request_id=request_id, attempt_number=attempt_number, runtime_root=runtime_root, node_executable=node_executable))
        else:
            probes.extend(_static_diagnostics(root, attempt))
        failure_phases = set((plan.get("failure_observation") or {}).get("failed_phase_classes") or [])
        failure_status = str((plan.get("failure_observation") or {}).get("verification_status") or "")
        if "construction_quality" in failure_phases or failure_status == "complete_application_quality_failed":
            try:
                from complete_application_construction import evaluate_complete_application_quality
                quality = evaluate_complete_application_quality(request_id, attempt_number, runtime_root=runtime_root)
                probes.append({
                    "probe_code": "construction_quality_recheck",
                    "passed": bool(quality.get("passed")),
                    "outcome": str(quality.get("status") or "complete_application_quality_unknown"),
                    "output_digest": str(quality.get("quality_result_digest") or quality.get("failure_digest") or ""),
                    "quality_failure_codes": list(quality.get("failed_finding_codes") or [])[:24],
                    "cleanup_confirmed": True,
                })
            except Exception as exc:
                probes.append({
                    "probe_code": "construction_quality_recheck",
                    "passed": False,
                    "outcome": f"complete_application_quality_recheck_error:{type(exc).__name__}",
                    "quality_failure_codes": ["quality_recheck_error"],
                    "cleanup_confirmed": True,
                })
    probes = probes[:MAX_DIAGNOSTIC_PROBES]
    ranked, preferred, posture = _rank_hypotheses(plan, probes)
    freshness_after = check_coding_source_freshness(request_id, runtime_root=runtime_root)
    if freshness_after.get("ok") is not True:
        posture = "blocked_stale_source"
    repeated = repeated_failed_repair_detected(request_id, attempt_number, runtime_root=runtime_root)
    if repeated:
        posture = "blocked_repeated_failed_repair"
    failed_test_digests = sorted({str(row.get("path_digest") or "") for row in probes if row.get("probe_code") == "individual_test_file_isolation" and row.get("passed") is False and row.get("path_digest")})
    record = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "foundation_contract_version": FOUNDATION_CONTRACT_VERSION,
        "status": "diagnostic_repair_reasoning_complete",
        "request_id": request_id,
        "attempt_number": attempt_number,
        "attempt_digest": str(attempt.get("attempt_record_digest") or ""),
        "verification_digest": str((attempt.get("verification") or {}).get("verification_digest") or ""),
        "diagnostic_plan_digest": str(plan.get("diagnostic_plan_digest") or ""),
        "probe_results": probes,
        "probe_count": len(probes),
        "ranked_hypotheses": ranked,
        "preferred_hypothesis_code": preferred,
        "repair_posture": posture,
        "repair_supported": posture == "repair_supported",
        "blocked": posture.startswith("blocked_"),
        "repeated_failed_repair": repeated,
        "failing_test_path_digests": failed_test_digests,
        "root_cause_proven": False,
        "diagnostic_commands_executed": any(row.get("probe_code") != "workspace_integrity_recheck" for row in probes),
        "provider_contacted": False,
        "repair_created": False,
        "content_minimized": True,
        "raw_test_output_stored": False,
        "raw_provider_output_stored": False,
        "private_content_stored": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    record["diagnostic_execution_authorized"] = False
    record["operation_recovery_count"] = recovery_count
    record = _seal(record, "diagnostic_result_digest")
    with _proposal_lock(request_id, runtime_root):
        prior = _read_json(result_path)
        if prior:
            if _valid(prior, "diagnostic_result_digest"):
                return {**prior, "operation_status": "restored"}
            return _failure("diagnostic_result_record_invalid", request_id=request_id, attempt_number=attempt_number)
        operation = _read_json(operation_path)
        if not operation or not _operation_valid(operation) or str(operation.get("lease_token") or "") != lease_token:
            return _failure("diagnostic_operation_lease_lost", request_id=request_id, attempt_number=attempt_number)
        _atomic_json(result_path, record)
        sealed_operation = dict(operation)
        sealed_operation.update({
            "status": "diagnostic_operation_sealed", "phase": "sealed",
            "lease_token": "", "lease_expires_unix": 0.0,
            "diagnostic_result_digest": str(record.get("diagnostic_result_digest") or ""),
        })
        _atomic_json(operation_path, _seal_operation(sealed_operation))
    return {**record, "operation_status": "recovered" if recovery_count else "created"}

def provider_repair_context(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_result_digest": str(record.get("diagnostic_result_digest") or ""),
        "repair_posture": str(record.get("repair_posture") or ""),
        "preferred_hypothesis_code": str(record.get("preferred_hypothesis_code") or ""),
        "failing_test_path_digests": list(record.get("failing_test_path_digests") or [])[:MAX_ISOLATED_TEST_FILES],
        "probe_outcomes": [
            {
                "probe_code": str(row.get("probe_code") or ""),
                "passed": bool(row.get("passed")),
                "exit_class": str(row.get("exit_class") or ""),
                "output_digest": str(row.get("output_digest") or ""),
                "path_digest": str(row.get("path_digest") or ""),
                "quality_failure_codes": list(row.get("quality_failure_codes") or [])[:24],
            }
            for row in list(record.get("probe_results") or [])[:MAX_DIAGNOSTIC_PROBES]
        ],
        "quality_failure_codes": sorted({
            str(code)
            for row in list(record.get("probe_results") or [])
            if row.get("probe_code") == "construction_quality_recheck"
            for code in list(row.get("quality_failure_codes") or [])
            if code
        })[:24],
        "root_cause_proven": False,
        "raw_test_output_included": False,
    }


def public_diagnostic_result(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "request_id": str(record.get("request_id") or ""),
        "attempt_number": int(record.get("attempt_number") or 0),
        "diagnostic_plan_digest": str(record.get("diagnostic_plan_digest") or ""),
        "diagnostic_result_digest": str(record.get("diagnostic_result_digest") or ""),
        "preferred_hypothesis_code": str(record.get("preferred_hypothesis_code") or ""),
        "repair_posture": str(record.get("repair_posture") or ""),
        "repair_supported": bool(record.get("repair_supported")),
        "blocked": bool(record.get("blocked")),
        "repeated_failed_repair": bool(record.get("repeated_failed_repair")),
        "probe_count": int(record.get("probe_count") or 0),
        "failing_test_count": len(record.get("failing_test_path_digests") or []),
        "root_cause_proven": False,
        "content_minimized": True,
        "raw_test_output_exposed": False,
        "raw_provider_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }


__all__ = [
    "CONTRACT_VERSION", "MAX_ISOLATED_TEST_FILES", "provider_repair_context",
    "public_diagnostic_result", "repeated_failed_repair_detected", "run_focused_diagnostics",
]
