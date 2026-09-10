from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import bounded_automatic_diagnosis as diagnosis
import conversational_build_test_continuation as continuation
from ordinary_chat_development_campaign import _atomic_json, _digest

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def sealed_continuation(runtime: Path, status: str, *, attempt_digest: str = "a" * 64):
    proposal_id = "devc_" + "1" * 24
    result = {
        "ok": status == "conversational_build_test_continuation_completed",
        "schema_version": "1",
        "contract_version": "v1212.8",
        "status": status,
        "completed_stage": "complete" if status.endswith("_completed") else ("build" if "build_blocked" in status else ("internal" if "internal_error" in status else "test")),
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "proposal_revision_digest": "b" * 64,
        "attempt_number": 2,
        "attempt_digest": attempt_digest,
        "parent_loop_result_digest": "c" * 64,
        "continuation_loop_result_digest": "d" * 64,
        "lineage_digest": "e" * 64,
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "provider_contacted": True,
        "tests_executed": "tests_failed" in status,
        "test_passed": True if status.endswith("_completed") else (False if "tests_failed" in status else None),
        "cleanup_confirmed": True,
        "operator_review_required": True,
        "automatic_continuation": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
    result["continuation_result_digest"] = _digest(result)
    record = {
        "phase": "sealed",
        "status": status,
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "attempt_number": 2,
        "attempt_digest": attempt_digest,
        "result": result,
        "result_digest": _digest(result),
    }
    path = continuation._attempt_path(proposal_id, 1, runtime)
    _atomic_json(path, continuation._seal(record))
    return proposal_id, result


for status, expected_code in (
    ("conversational_build_test_continuation_tests_failed", "test_failure_observed"),
    ("conversational_build_test_continuation_test_blocked", "test_execution_blocked"),
    ("conversational_build_test_continuation_build_blocked", "build_stage_blocked"),
    ("conversational_build_test_continuation_internal_error", "continuation_pipeline_error_observed"),
):
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1213-a-"))
    try:
        proposal_id, result = sealed_continuation(runtime, status)
        prepared = diagnosis.prepare_bounded_automatic_diagnosis(
            proposal_id,
            expected_revision=1,
            expected_attempt_digest=result["attempt_digest"],
            expected_continuation_result_digest=result["continuation_result_digest"],
            runtime_root=runtime,
        )
        require(prepared["ok"] is True, prepared)
        require(prepared["status"] == "bounded_automatic_diagnosis_ready")
        require(prepared["phase"] == "prepared")
        require(prepared["evidence"]["outcome_status"] == status)
        require(prepared["evidence"]["content_free"] is True)
        require(prepared["evidence"]["raw_output_included"] is False)
        require(prepared["evidence"]["private_path_included"] is False)
        require(prepared["evidence"]["lineage_digest_source"] == "continuation_result")
        require(len(prepared["evidence_digest"]) == 64)
        require(len(prepared["diagnosis_digest"]) == 64)
        require(prepared["diagnosis_performed"] is False)
        require(prepared["automatic_diagnosis"] is False)
        require(prepared["diagnosis_authorized"] is False)
        require(prepared["provider_contacted"] is False)
        require(prepared["tests_executed"] is False)
        require(prepared["repair_authorized"] is False)
        require(prepared["retest_authorized"] is False)
        require(prepared["authority_granted"] is False)
        require(diagnosis.DIAGNOSABLE_OUTCOMES[status]["diagnosis_code"] == expected_code)
        replay = diagnosis.prepare_bounded_automatic_diagnosis(
            proposal_id,
            expected_revision=1,
            expected_attempt_digest=result["attempt_digest"],
            expected_continuation_result_digest=result["continuation_result_digest"],
            runtime_root=runtime,
        )
        require(replay["operation_status"] == "resumed")
        require(replay["diagnosis_digest"] == prepared["diagnosis_digest"])
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


# A successful continuation is explicitly ineligible and creates no diagnosis record.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1213-a-pass-"))
try:
    proposal_id, result = sealed_continuation(runtime, "conversational_build_test_continuation_completed")
    outcome = diagnosis.prepare_bounded_automatic_diagnosis(
        proposal_id,
        expected_revision=1,
        expected_attempt_digest=result["attempt_digest"],
        expected_continuation_result_digest=result["continuation_result_digest"],
        runtime_root=runtime,
    )
    require(outcome["status"] == "bounded_automatic_diagnosis_not_required", outcome)
    require(outcome["diagnosis_performed"] is False)
    require(not diagnosis._diagnosis_path(proposal_id, 1, 2, runtime).exists())
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# An actual early v1212 internal error can lack child-loop lineage. Diagnosis
# derives a content-free attempt binding without changing the signed result.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1213-a-early-error-"))
try:
    proposal_id = "devc_" + "3" * 24
    result = {
        "ok": False, "schema_version": "1", "contract_version": "v1212.8",
        "status": "conversational_build_test_continuation_internal_error",
        "proposal_id": proposal_id, "proposal_revision": 1, "attempt_number": 2,
        "attempt_digest": "4" * 64, "parent_loop_result_digest": "5" * 64,
        "provider_contacted": False, "tests_executed": False,
        "repair_authorized": False, "authority_granted": False,
    }
    result["continuation_result_digest"] = _digest(result)
    record = {
        "phase": "sealed", "status": result["status"], "proposal_id": proposal_id,
        "proposal_revision": 1, "proposal_revision_digest": "6" * 64,
        "attempt_number": 2, "attempt_digest": result["attempt_digest"],
        "parent_loop_result_digest": result["parent_loop_result_digest"],
        "project_kind": "new_python_cli_project", "selected_adapter_id": "python",
        "result": result, "result_digest": _digest(result),
    }
    _atomic_json(continuation._attempt_path(proposal_id, 1, runtime), continuation._seal(record))
    prepared = diagnosis.prepare_bounded_automatic_diagnosis(
        proposal_id, expected_revision=1, expected_attempt_digest=result["attempt_digest"],
        expected_continuation_result_digest=result["continuation_result_digest"], runtime_root=runtime,
    )
    require(prepared["status"] == "bounded_automatic_diagnosis_ready", prepared)
    require(prepared["evidence"]["lineage_digest_source"] == "derived_sealed_attempt_binding")
    require(len(prepared["evidence"]["lineage_digest"]) == 64)
    require(prepared["evidence"]["proposal_revision_digest"] == "6" * 64)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Stale attempt/result bindings are rejected before a diagnosis record is written.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1213-a-stale-"))
try:
    proposal_id, result = sealed_continuation(runtime, "conversational_build_test_continuation_tests_failed")
    stale_attempt = diagnosis.prepare_bounded_automatic_diagnosis(
        proposal_id,
        expected_revision=1,
        expected_attempt_digest="0" * 64,
        expected_continuation_result_digest=result["continuation_result_digest"],
        runtime_root=runtime,
    )
    require(stale_attempt["status"] == "bounded_automatic_diagnosis_stale_attempt")
    stale_result = diagnosis.prepare_bounded_automatic_diagnosis(
        proposal_id,
        expected_revision=1,
        expected_attempt_digest=result["attempt_digest"],
        expected_continuation_result_digest="0" * 64,
        runtime_root=runtime,
    )
    require(stale_result["status"] == "bounded_automatic_diagnosis_stale_result")
    require(not diagnosis._diagnosis_path(proposal_id, 1, 2, runtime).exists())
finally:
    shutil.rmtree(runtime, ignore_errors=True)


release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1213.2-bounded-automatic-diagnosis-foundations"') == 2)
require(release.count("tools/v1213_0_2_bounded_automatic_diagnosis_foundations_tests.py") == 1)
print(json.dumps({
    "ok": True,
    "version": "1213.2",
    "checks": len(checks),
    "passed": sum(checks),
    "diagnosable_outcomes": len(diagnosis.DIAGNOSABLE_OUTCOMES),
    "provider_contacted": False,
    "tests_executed": False,
    "root_cause_proven": False,
    "repair_authorized": False,
}, sort_keys=True))
