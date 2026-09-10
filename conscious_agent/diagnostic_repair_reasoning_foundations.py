from __future__ import annotations

"""v1257.0-v1257.2 diagnostic and repair reasoning foundations.

The foundation converts one sealed failed isolated-coding attempt into a
content-minimized observation, several explicit competing explanations, and a
bounded diagnostic plan.  It is provider-free and executes no commands.  The
records are external-runtime evidence only and cannot authorize repair,
retesting, application, installation, release, or independent action.
"""

from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1257.2"
MAX_HYPOTHESES = 5
MAX_DIAGNOSTIC_PROBES = 10

DENIED_AUTHORITY = {
    "diagnostic_execution_authorized": False,
    "provider_contact_authorized": False,
    "repair_authorized": False,
    "test_execution_authorized": False,
    "application_authorized": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}

_ENVIRONMENT_STATUSES = {
    "python_runtime_unavailable",
    "python_pytest_unavailable",
    "node_runtime_unavailable",
    "python_test_capability_contract_rejected",
    "node_test_capability_contract_rejected",
    "isolated_coding_verification_workspace_invalid",
    "workspace_scan_failed",
    "workspace_private_or_generated_material_detected",
    "workspace_link_or_boundary_rejected",
    "workspace_casefold_path_collision",
}


def _analysis_path(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "diagnostic_repair_reasoning" / request_id / f"attempt-{int(attempt_number)}.json"


def _result_path(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "diagnostic_repair_results" / request_id / f"attempt-{int(attempt_number)}.json"


def _attempt_path(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id / f"attempt-{int(attempt_number)}.json"


def _seal(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _attempt_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("attempt_record_digest") or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != "attempt_record_digest"}))


def _failure(status: str, *, request_id: str = "", attempt_number: int = 0, reason: str = "") -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "request_id": request_id,
        "attempt_number": int(attempt_number),
        "reason": reason,
        "content_minimized": True,
        "raw_test_output_stored": False,
        "raw_provider_output_stored": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    row["failure_digest"] = _digest(row)
    return row


def _command_observations(verification: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for command in list(verification.get("command_results") or [])[:MAX_DIAGNOSTIC_PROBES]:
        rows.append({
            "phase": str(command.get("phase") or ""),
            "runner": str(command.get("runner") or ""),
            "path_digest": str(command.get("path_digest") or ""),
            "selection_digest": str(command.get("selection_digest") or ""),
            "passed": bool(command.get("passed")),
            "exit_class": str(command.get("exit_class") or ""),
            "output_digest": str(command.get("output_digest") or ""),
            "output_bytes": int(command.get("output_bytes") or 0),
            "cleanup_confirmed": bool(command.get("cleanup_confirmed", True)),
            "duration_ms": int(command.get("duration_ms") or 0),
        })
    return rows


def build_failure_observation(request_id: str, attempt_number: int, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    attempt_number = int(attempt_number)
    attempt = _read_json(_attempt_path(request_id, attempt_number, runtime_root))
    if not attempt or not _attempt_valid(attempt):
        return _failure("diagnostic_attempt_missing_or_tampered", request_id=request_id, attempt_number=attempt_number)
    verification = dict(attempt.get("verification") or {})
    if not verification.get("verification_digest"):
        return _failure("diagnostic_verification_missing", request_id=request_id, attempt_number=attempt_number)
    if verification.get("passed") is True:
        return _failure("diagnostic_failure_not_present", request_id=request_id, attempt_number=attempt_number)
    commands = _command_observations(verification)
    failed = [row for row in commands if not row["passed"]]
    observation = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "diagnostic_failure_observation_ready",
        "request_id": request_id,
        "attempt_number": attempt_number,
        "attempt_digest": str(attempt.get("attempt_record_digest") or ""),
        "change_manifest_digest": str(attempt.get("change_manifest_digest") or ""),
        "change_count": int(attempt.get("change_count") or len(attempt.get("changes") or [])),
        "verification_status": str(verification.get("status") or ""),
        "verification_digest": str(verification.get("verification_digest") or ""),
        "project_type": str(verification.get("project_type") or ""),
        "test_file_count": int(verification.get("test_file_count") or 0),
        "cleanup_confirmed": bool(verification.get("cleanup_confirmed", True)),
        "failed_command_count": len(failed),
        "failed_phase_classes": sorted({str(row.get("phase") or "") for row in failed}),
        "failed_exit_classes": sorted({str(row.get("exit_class") or "") for row in failed}),
        "failed_path_digests": sorted({str(row.get("path_digest") or "") for row in failed if row.get("path_digest")}),
        "failed_selection_digests": sorted({str(row.get("selection_digest") or "") for row in failed if row.get("selection_digest")}),
        "command_observations": commands,
        "environment_blocker_observed": str(verification.get("status") or "") in _ENVIRONMENT_STATUSES or not bool(verification.get("cleanup_confirmed", True)),
        "content_minimized": True,
        "raw_test_output_stored": False,
        "raw_provider_output_stored": False,
        "private_content_stored": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    observation["observation_digest"] = _digest(observation)
    return {"ok": True, **observation}


def _hypothesis(code: str, *, cause_class: str, confidence: str, basis: list[str], disproof: str, repairable: bool) -> dict[str, Any]:
    row = {
        "hypothesis_code": code,
        "cause_class": cause_class,
        "confidence": confidence,
        "evidence_basis": list(basis)[:4],
        "disproof_test": disproof,
        "repairable_in_isolated_workspace": bool(repairable),
        "root_cause_proven": False,
    }
    row["hypothesis_digest"] = _digest(row)
    return row


def form_competing_explanations(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    status = str(observation.get("verification_status") or "")
    phases = set(observation.get("failed_phase_classes") or [])
    exits = set(observation.get("failed_exit_classes") or [])
    rows: list[dict[str, Any]] = []
    if observation.get("environment_blocker_observed"):
        rows.append(_hypothesis(
            "verification_environment_unavailable",
            cause_class="environment",
            confidence="high",
            basis=[status, "cleanup_or_runtime_evidence"],
            disproof="confirm_required_runtime_and_capability_in_the_same_bounded_workspace",
            repairable=False,
        ))
        rows.append(_hypothesis(
            "implementation_defect_not_yet_excluded",
            cause_class="implementation",
            confidence="low",
            basis=[status],
            disproof="restore_verification_environment_then_rerun_original_verification",
            repairable=True,
        ))
    elif "syntax" in phases or "syntax_failed" in status:
        rows.extend([
            _hypothesis("changed_source_syntax_defect", cause_class="implementation", confidence="high", basis=[status, "syntax_phase_failed"], disproof="targeted_syntax_recheck_of_failed_path_passes", repairable=True),
            _hypothesis("generated_change_incomplete_or_truncated", cause_class="generation", confidence="medium", basis=["syntax_phase_failed"], disproof="changed_source_structure_is_complete_and_targeted_syntax_recheck_passes", repairable=True),
            _hypothesis("verification_runtime_anomaly", cause_class="environment", confidence="low", basis=list(exits)[:2], disproof="same_targeted_syntax_probe_reproduces_under_available_runtime", repairable=False),
        ])
    elif "construction_quality" in phases or status == "complete_application_quality_failed":
        rows.extend([
            _hypothesis("application_coherence_defect", cause_class="implementation", confidence="high", basis=[status, "construction_quality_failed"], disproof="deterministic_application_quality_recheck_passes", repairable=True),
            _hypothesis("incomplete_cross_file_artifact_set", cause_class="generation", confidence="medium", basis=["construction_quality_failed"], disproof="all_required_artifact_roles_and_relationships_are_satisfied", repairable=True),
            _hypothesis("quality_contract_or_workspace_anomaly", cause_class="environment", confidence="low", basis=[status], disproof="construction_contract_and_workspace_integrity_recheck_cleanly", repairable=False),
        ])
    elif "tests" in phases or status.endswith("tests_failed"):
        rows.extend([
            _hypothesis("implementation_behavior_defect", cause_class="implementation", confidence="medium", basis=[status, "aggregate_tests_failed"], disproof="all_project_test_files_pass_in_individual_isolation", repairable=True),
            _hypothesis("incomplete_requirement_coverage", cause_class="implementation", confidence="medium", basis=["verification_failed_after_generation"], disproof="focused_test_isolation_shows_only_preexisting_or_environment_failure", repairable=True),
            _hypothesis("preexisting_or_unrelated_test_failure", cause_class="baseline_or_unrelated", confidence="low", basis=["aggregate_tests_failed"], disproof="failing_test_isolation_correlates_with_changed_implementation_and_baseline_was_green", repairable=False),
            _hypothesis("test_environment_or_runner_issue", cause_class="environment", confidence="low", basis=list(exits)[:2], disproof="focused_test_files_reproduce_consistently_with_clean_runtime", repairable=False),
        ])
    elif "timeout" in exits:
        rows.extend([
            _hypothesis("implementation_hang_or_unbounded_work", cause_class="implementation", confidence="medium", basis=["timeout"], disproof="focused_test_isolation_completes_within_bound", repairable=True),
            _hypothesis("verification_environment_stall", cause_class="environment", confidence="medium", basis=["timeout"], disproof="other focused probes complete normally", repairable=False),
        ])
    else:
        rows.extend([
            _hypothesis("implementation_defect", cause_class="implementation", confidence="low", basis=[status or "verification_failed"], disproof="focused_recheck_passes_without_change", repairable=True),
            _hypothesis("verification_or_environment_blocker", cause_class="environment", confidence="low", basis=[status or "verification_failed"], disproof="bounded_environment_and_workspace_probes_pass", repairable=False),
        ])
    return rows[:MAX_HYPOTHESES]


def _diagnostic_probes(observation: Mapping[str, Any], hypotheses: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    status = str(observation.get("verification_status") or "")
    phases = set(observation.get("failed_phase_classes") or [])
    probes: list[dict[str, Any]] = [{
        "probe_code": "workspace_integrity_recheck",
        "purpose": "disprove_workspace_contamination_or_boundary_failure",
        "hypothesis_codes": [str(row.get("hypothesis_code") or "") for row in hypotheses if row.get("cause_class") == "environment"][:3],
        "command_execution_required": False,
    }]
    if "construction_quality" in phases or status == "complete_application_quality_failed":
        probes.append({
            "probe_code": "construction_quality_recheck",
            "purpose": "reproduce_or_disprove_the_cross_file_quality_failure_without_new_changes",
            "hypothesis_codes": ["application_coherence_defect", "incomplete_cross_file_artifact_set", "quality_contract_or_workspace_anomaly"],
            "command_execution_required": False,
        })
    elif "syntax" in phases or "syntax_failed" in status:
        probes.append({
            "probe_code": "failed_path_syntax_recheck",
            "purpose": "reproduce_or_disprove_the_observed_syntax_failure_on_the_smallest_known_path",
            "hypothesis_codes": ["changed_source_syntax_defect", "verification_runtime_anomaly"],
            "command_execution_required": True,
        })
    elif "tests" in phases or status.endswith("tests_failed") or "timeout" in set(observation.get("failed_exit_classes") or []):
        probes.extend([
            {
                "probe_code": "individual_test_file_isolation",
                "purpose": "identify_which_bounded_project_test_files_reproduce_the_failure",
                "hypothesis_codes": ["implementation_behavior_defect", "preexisting_or_unrelated_test_failure", "test_environment_or_runner_issue", "implementation_hang_or_unbounded_work"],
                "command_execution_required": True,
            },
            {
                "probe_code": "changed_source_syntax_guard",
                "purpose": "exclude_a_hidden_syntax_failure_before_reasoning_about_behavior",
                "hypothesis_codes": ["implementation_behavior_defect", "test_environment_or_runner_issue"],
                "command_execution_required": True,
            },
        ])
    else:
        probes.append({
            "probe_code": "bounded_verification_recheck",
            "purpose": "determine_whether_the_observed_failure_reproduces_without_any_new_change",
            "hypothesis_codes": [str(row.get("hypothesis_code") or "") for row in hypotheses][:3],
            "command_execution_required": True,
        })
    return probes[:MAX_DIAGNOSTIC_PROBES]


def create_or_restore_diagnostic_plan(request_id: str, attempt_number: int, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    attempt_number = int(attempt_number)
    path = _analysis_path(request_id, attempt_number, runtime_root)
    with _proposal_lock(request_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "diagnostic_plan_digest"):
                return _failure("diagnostic_plan_record_invalid", request_id=request_id, attempt_number=attempt_number)
            return {**existing, "operation_status": "restored"}
        observation = build_failure_observation(request_id, attempt_number, runtime_root=runtime_root)
        if observation.get("ok") is not True:
            return observation
        hypotheses = form_competing_explanations(observation)
        probes = _diagnostic_probes(observation, hypotheses)
        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "diagnostic_plan_ready",
            "request_id": request_id,
            "attempt_number": attempt_number,
            "attempt_digest": str(observation.get("attempt_digest") or ""),
            "verification_digest": str(observation.get("verification_digest") or ""),
            "observation_digest": str(observation.get("observation_digest") or ""),
            "failure_observation": {key: observation.get(key) for key in (
                "verification_status", "project_type", "test_file_count", "cleanup_confirmed",
                "failed_command_count", "failed_phase_classes", "failed_exit_classes",
                "failed_path_digests", "failed_selection_digests", "environment_blocker_observed",
            )},
            "hypotheses": hypotheses,
            "hypothesis_count": len(hypotheses),
            "diagnostic_probes": probes,
            "diagnostic_probe_count": len(probes),
            "completion_condition": "one_preferred_supported_explanation_or_explicit_blocker_posture",
            "blocker_condition": "environment_unavailable_workspace_invalid_no_discriminating_evidence_or_repeated_failed_repair",
            "root_cause_proven": False,
            "operator_review_required": True,
            "content_minimized": True,
            "raw_test_output_stored": False,
            "raw_provider_output_stored": False,
            "private_content_stored": False,
            "selected_project_modified": False,
            "source_modified": False,
            **DENIED_AUTHORITY,
        }
        record = _seal(record, "diagnostic_plan_digest")
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_diagnostic_plan(request_id: str, attempt_number: int, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_analysis_path(str(request_id or "").lower(), int(attempt_number), runtime_root))
    return row if row and _valid(row, "diagnostic_plan_digest") else {}


def load_diagnostic_result(request_id: str, attempt_number: int, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_result_path(str(request_id or "").lower(), int(attempt_number), runtime_root))
    return row if row and _valid(row, "diagnostic_result_digest") else {}


def public_diagnostic_plan(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "request_id": str(record.get("request_id") or ""),
        "attempt_number": int(record.get("attempt_number") or 0),
        "observation_digest": str(record.get("observation_digest") or ""),
        "diagnostic_plan_digest": str(record.get("diagnostic_plan_digest") or ""),
        "hypotheses": [
            {key: row.get(key) for key in ("hypothesis_code", "cause_class", "confidence", "disproof_test", "repairable_in_isolated_workspace", "root_cause_proven")}
            for row in list(record.get("hypotheses") or [])[:MAX_HYPOTHESES]
        ],
        "diagnostic_probes": [
            {key: row.get(key) for key in ("probe_code", "purpose", "command_execution_required")}
            for row in list(record.get("diagnostic_probes") or [])[:MAX_DIAGNOSTIC_PROBES]
        ],
        "content_minimized": True,
        "raw_test_output_exposed": False,
        "raw_provider_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }


__all__ = [
    "CONTRACT_VERSION", "DENIED_AUTHORITY", "MAX_DIAGNOSTIC_PROBES", "MAX_HYPOTHESES",
    "build_failure_observation", "create_or_restore_diagnostic_plan", "form_competing_explanations",
    "load_diagnostic_plan", "load_diagnostic_result", "public_diagnostic_plan",
]
