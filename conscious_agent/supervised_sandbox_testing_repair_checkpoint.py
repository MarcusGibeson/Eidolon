from __future__ import annotations

"""Strictly bounded v1182.9 supervised sandbox testing and repair checkpoint.

Consolidates exact sandbox-test review and execution, content-free evidence and
conservative diagnosis, and operator-reviewed repair/retest planning. The
checkpoint uses temporary synthetic sandboxes and caller-owned synthetic
contracts only. It never changes production source, applies a repair, reruns a
repair, invokes a provider/model, promotes a sandbox result, or grants release
authority.
"""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from sandbox_test_evidence_diagnosis import CONTRACT_VERSION as EVIDENCE_CONTRACT_VERSION, MAX_DIAGNOSES as EVIDENCE_MAX_DIAGNOSES, MAX_TEST_RESULTS, build_sandbox_test_evidence, diagnose_sandbox_test_evidence, sandbox_test_diagnosis_public_summary
from supervised_implementation_checkpoint import build_supervised_implementation_checkpoint
from supervised_repair_planning import CONTRACT_VERSION as REPAIR_CONTRACT_VERSION, MAX_DIAGNOSES as REPAIR_MAX_DIAGNOSES, build_supervised_repair_plan, repair_plan_public_summary, review_repair_diagnosis
from supervised_sandbox_test_execution import CONTRACT_VERSION as TEST_CONTRACT_VERSION, MAX_TESTS, MAX_TIMEOUT_SECONDS, execute_reviewed_sandbox_tests, review_sandbox_test_execution

CONTRACT_VERSION = "v1182.9"
_CHECKPOINT_ID = "supervised-sandbox-testing-repair:v1182.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_REPORT_TEXT = (
    "SANDBOX_CHECKPOINT_PRIVATE_SOURCE",
    "SANDBOX_CHECKPOINT_PRIVATE_OUTPUT",
    "SANDBOX_CHECKPOINT_PRIVATE_SECRET",
    "raw_source_text",
    "raw_patch_text",
    "stdout",
    "stderr",
    "chain_of_thought",
    "private reasoning payload",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _tree_signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        h.update(relative.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


def _materialization_receipt(target: str, content: bytes) -> dict[str, Any]:
    target_digest = _bytes_digest(content)
    structural = {
        "schema_version": "1",
        "contract_version": "v1181.8",
        "content_free": True,
        "sandbox_only": True,
        "materialization_status": "materialized",
        "sandbox_materialized": True,
        "sandbox_file_written": True,
        "source_modified": False,
        "production_source_modified": False,
        "patch_applied_to_source": False,
        "tests_executed": False,
        "target_path": target,
        "sandbox_target_digest": target_digest,
        "sandbox_marker_digest": _digest({"target": target, "target_digest": target_digest}),
    }
    structural["materialization_receipt_digest"] = _digest(structural)
    return structural


def _synthetic_test_receipt(
    *, status: str, target: str, error_class: str = "", block_reason: str = "",
) -> dict[str, Any]:
    target_digest = _digest({"target": target})
    rows: list[dict[str, Any]] = []
    tests_executed = status != "blocked"
    if tests_executed:
        rows = [{
            "test": "python_compile",
            "status": status,
            "error_class": error_class,
        }]
    result: dict[str, Any] = {
        "schema_version": "1",
        "contract_version": "v1182.2",
        "sandbox_only": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "patch_applied_to_source": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "operator_review_required": True,
        "execution_status": status,
        "tests_executed": tests_executed,
        "test_execution_authorized": tests_executed,
        "target_path": target if tests_executed else "",
        "attempt_digest": _digest({"attempt": target, "status": status}) if tests_executed else "",
        "review_digest": _digest({"review": target}) if tests_executed else "",
        "materialization_receipt_digest": _digest({"materialization": target}) if tests_executed else "",
        "sandbox_target_digest": target_digest if tests_executed else "",
        "test_count": len(rows),
        "test_results": rows,
        "elapsed_ms": 1,
        "block_reason": block_reason,
        "content_free": True,
        "single_use_consumed": tests_executed,
    }
    result["test_receipt_digest"] = _digest(result)
    return result


def _source_contract(source: Path) -> dict[str, Any]:
    paths = {
        "testing": source / "conscious_agent" / "supervised_sandbox_test_execution.py",
        "diagnosis": source / "conscious_agent" / "sandbox_test_evidence_diagnosis.py",
        "repair": source / "conscious_agent" / "supervised_repair_planning.py",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    return {
        "test_contract": TEST_CONTRACT_VERSION,
        "evidence_contract": EVIDENCE_CONTRACT_VERSION,
        "repair_contract": REPAIR_CONTRACT_VERSION,
        "maximum_tests": MAX_TESTS,
        "maximum_timeout_seconds": MAX_TIMEOUT_SECONDS,
        "maximum_test_results": MAX_TEST_RESULTS,
        "maximum_evidence_diagnoses": EVIDENCE_MAX_DIAGNOSES,
        "maximum_repair_diagnoses": REPAIR_MAX_DIAGNOSES,
        "testing_production_write_present": "patch_applied_to_source\": True" in texts["testing"],
        "diagnosis_source_read_present": any(token in texts["diagnosis"] for token in ("read_text(", "read_bytes(", "open(")),
        "diagnosis_write_present": any(token in texts["diagnosis"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "repair_source_read_present": any(token in texts["repair"] for token in ("read_text(", "read_bytes(", "open(")),
        "repair_write_present": any(token in texts["repair"] for token in ("write_text(", "write_bytes(", "subprocess")),
        "repair_authority_enabled": "'repair_authorized':True" in texts["repair"].replace(" ", ""),
        "retest_authority_enabled": "'retest_authorized':True" in texts["repair"].replace(" ", ""),
    }


def build_supervised_sandbox_testing_repair_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    prior = build_supervised_implementation_checkpoint(source_root=source, runtime_root=runtime)
    for key in (
        "ok", "read_only", "content_free", "authority_preserved",
        "supervised_implementation_checkpoint_completed",
        "implementation_preparation_exercised", "private_patch_drafting_exercised",
        "operator_patch_review_exercised", "isolated_sandbox_materialization_exercised",
    ):
        require(prior.get(key))
    for key in (
        "production_source_modified", "patch_applied_to_source", "tests_executed",
        "shell_invoked", "execution_invoked", "registered_tool_invoked",
        "provider_contacted", "model_operation_performed", "source_edit_performed",
        "production_runtime_mutated", "installation_performed", "promotion_performed",
        "certification_performed", "release_authorized", "source_modified", "runtime_mutated",
    ):
        require(prior.get(key) is False)

    with TemporaryDirectory(prefix="eidolon-v1182-checkpoint-") as directory:
        root = Path(directory)
        source_stub = root / "synthetic-source"
        source_stub.mkdir()

        good_sandbox = root / "good-sandbox"
        good_target = "pkg/good.py"
        good_bytes = b"def healthy():\n    return 1\n"
        (good_sandbox / "pkg").mkdir(parents=True)
        (good_sandbox / good_target).write_bytes(good_bytes)
        good_materialization = _materialization_receipt(good_target, good_bytes)
        approved = review_sandbox_test_execution(
            good_materialization,
            decision="approve", operator_actor="checkpoint-operator",
            requested_tests=["python_compile", "content_digest_match"],
        )
        rejected = review_sandbox_test_execution(
            good_materialization,
            decision="reject", operator_actor="checkpoint-operator",
            requested_tests=["python_compile"],
        )
        deferred = review_sandbox_test_execution(
            good_materialization,
            decision="defer", operator_actor="checkpoint-operator",
            requested_tests=["content_digest_match"],
        )
        require(approved.get("review_status") == "approved_for_sandbox_tests")
        require(approved.get("test_execution_authorized") is True)
        require(approved.get("content_free") is True)
        require(rejected.get("review_status") == "rejected")
        require(rejected.get("test_execution_authorized") is False)
        require(deferred.get("review_status") == "deferred")
        require(deferred.get("test_execution_authorized") is False)
        require(len(str(approved.get("review_digest") or "")) == 64)
        require(len(str(approved.get("review_receipt_digest") or "")) == 64)

        passed_receipt = execute_reviewed_sandbox_tests(
            good_materialization, approved,
            sandbox_root=good_sandbox, source_root=source_stub, timeout_seconds=5,
        )
        require(passed_receipt.get("execution_status") == "passed")
        require(passed_receipt.get("tests_executed") is True)
        require(passed_receipt.get("test_count") == 2)
        require(all(row.get("status") == "passed" for row in passed_receipt.get("test_results", [])))
        require(passed_receipt.get("source_modified") is False)
        require(passed_receipt.get("patch_applied_to_source") is False)
        require(passed_receipt.get("provider_contacted") is False)
        require(passed_receipt.get("model_contacted") is False)
        require(passed_receipt.get("release_authorized") is False)
        require(len(str(passed_receipt.get("attempt_digest") or "")) == 64)
        require(len(str(passed_receipt.get("test_receipt_digest") or "")) == 64)

        passed_evidence = build_sandbox_test_evidence(passed_receipt)
        passed_diagnosis = diagnose_sandbox_test_evidence(passed_evidence)
        require(passed_evidence.get("evidence_status") == "verified")
        require(passed_diagnosis.get("diagnosis_status") == "complete")
        require(passed_diagnosis.get("diagnosis_posture") == "no_diagnosed_failure")
        require(passed_diagnosis.get("diagnosis_count") == 0)
        require(passed_diagnosis.get("root_cause_proven") is False)
        require(passed_diagnosis.get("repair_authorized") is False)
        require(passed_diagnosis.get("retest_authorized") is False)
        require(review_repair_diagnosis(passed_diagnosis, "confirm", "checkpoint-operator").get("block_reason") == "no_failure_diagnosis_to_confirm")

        bad_sandbox = root / "bad-sandbox"
        bad_target = "pkg/bad.py"
        bad_bytes = b"def broken(:\n    pass\n"
        (bad_sandbox / "pkg").mkdir(parents=True)
        (bad_sandbox / bad_target).write_bytes(bad_bytes)
        bad_materialization = _materialization_receipt(bad_target, bad_bytes)
        bad_review = review_sandbox_test_execution(
            bad_materialization,
            decision="approve", operator_actor="checkpoint-operator",
            requested_tests=["python_compile", "content_digest_match"],
        )
        failed_receipt = execute_reviewed_sandbox_tests(
            bad_materialization, bad_review,
            sandbox_root=bad_sandbox, source_root=source_stub, timeout_seconds=5,
        )
        require(failed_receipt.get("execution_status") == "failed")
        require(failed_receipt.get("tests_executed") is True)
        require(any(row.get("error_class") == "python_compile_failed" for row in failed_receipt.get("test_results", [])))
        failed_evidence = build_sandbox_test_evidence(failed_receipt)
        failed_diagnosis = diagnose_sandbox_test_evidence(failed_evidence)
        require(failed_evidence.get("evidence_status") == "verified")
        require(failed_diagnosis.get("diagnosis_posture") == "diagnosis_candidates_require_review")
        require(failed_diagnosis.get("diagnosis_count") == 1)
        require((failed_diagnosis.get("diagnosis_candidates") or [{}])[0].get("diagnosis_code") == "python_compile_failure_observed")
        require(failed_diagnosis.get("root_cause_proven") is False)

        confirmed = review_repair_diagnosis(failed_diagnosis, "confirm", "checkpoint-operator")
        rejected_repair = review_repair_diagnosis(failed_diagnosis, "reject", "checkpoint-operator")
        deferred_repair = review_repair_diagnosis(failed_diagnosis, "defer", "checkpoint-operator")
        require(confirmed.get("review_status") == "confirmed_for_repair_planning")
        require(rejected_repair.get("review_status") == "rejected")
        require(deferred_repair.get("review_status") == "deferred")
        repair_plan = build_supervised_repair_plan(failed_diagnosis, confirmed)
        require(repair_plan.get("planning_status") == "candidate")
        require(repair_plan.get("repair_step_count") == 1)
        require(repair_plan.get("root_cause_proven") is False)
        require(repair_plan.get("repair_authorized") is False)
        require(repair_plan.get("retest_authorized") is False)
        require((repair_plan.get("repair_steps") or [{}])[0].get("minimal_change_required") is True)
        require((repair_plan.get("repair_steps") or [{}])[0].get("sandbox_only_required") is True)
        require((repair_plan.get("repair_steps") or [{}])[0].get("rollback_required") is True)
        require("no_production_source_change" in (repair_plan.get("acceptance_criteria") or []))
        public_plan = repair_plan_public_summary(repair_plan)
        require(public_plan.get("content_free") is True)
        require(public_plan.get("source_modified") is False)
        require(public_plan.get("patch_created") is False)
        require(public_plan.get("tests_rerun") is False)
        require(public_plan.get("tool_invoked") is False)
        require(public_plan.get("provider_contacted") is False)
        require(public_plan.get("model_contacted") is False)
        require(public_plan.get("release_authorized") is False)

        timeout_receipt = _synthetic_test_receipt(
            status="timed_out", target="pkg/timeout.py", error_class="test_timeout",
        )
        timeout_evidence = build_sandbox_test_evidence(timeout_receipt)
        timeout_diagnosis = diagnose_sandbox_test_evidence(timeout_evidence)
        require(timeout_evidence.get("evidence_status") == "verified")
        require((timeout_diagnosis.get("diagnosis_candidates") or [{}])[0].get("diagnosis_code") == "sandbox_test_timeout_observed")
        timeout_review = review_repair_diagnosis(timeout_diagnosis, "confirm", "checkpoint-operator")
        timeout_plan = build_supervised_repair_plan(timeout_diagnosis, timeout_review)
        require(timeout_plan.get("planning_status") == "candidate")
        require((timeout_plan.get("repair_steps") or [{}])[0].get("retest_step") == "rerun_original_bounded_test_set")

        blocked_receipt = _synthetic_test_receipt(
            status="blocked", target="", block_reason="sandbox_target_drift",
        )
        blocked_evidence = build_sandbox_test_evidence(blocked_receipt)
        blocked_diagnosis = diagnose_sandbox_test_evidence(blocked_evidence)
        require(blocked_evidence.get("evidence_status") == "verified")
        require((blocked_diagnosis.get("diagnosis_candidates") or [{}])[0].get("diagnosis_code") == "sandbox_test_execution_blocked")
        blocked_review = review_repair_diagnosis(blocked_diagnosis, "confirm", "checkpoint-operator")
        blocked_plan = build_supervised_repair_plan(blocked_diagnosis, blocked_review)
        require(blocked_plan.get("planning_status") == "candidate")
        require((blocked_plan.get("repair_steps") or [{}])[0].get("repair_step") == "restore_exact_test_preconditions")

        require(review_sandbox_test_execution(good_materialization, decision="approve", operator_actor="", requested_tests=["python_compile"]).get("block_reason") == "missing_operator_actor")
        require(review_sandbox_test_execution(good_materialization, decision="ship", operator_actor="operator", requested_tests=["python_compile"]).get("block_reason") == "invalid_review_decision")
        require(review_sandbox_test_execution(good_materialization, decision="approve", operator_actor="operator", requested_tests=["invented_test"]).get("block_reason") == "unsupported_test_request")
        unsafe_materialization = dict(good_materialization)
        unsafe_materialization["target_path"] = "../secret.py"
        require(review_sandbox_test_execution(unsafe_materialization, decision="approve", operator_actor="operator", requested_tests=["python_compile"]).get("block_reason") == "invalid_materialization_contract")
        require(execute_reviewed_sandbox_tests(good_materialization, rejected, sandbox_root=good_sandbox, source_root=source_stub).get("block_reason") == "invalid_test_review_binding")
        require(execute_reviewed_sandbox_tests(good_materialization, approved, sandbox_root=source_stub, source_root=source_stub).get("block_reason") == "sandbox_not_isolated")
        drifted = dict(good_materialization)
        drifted["sandbox_target_digest"] = "f" * 64
        drift_review = review_sandbox_test_execution(drifted, decision="approve", operator_actor="operator", requested_tests=["content_digest_match"])
        require(execute_reviewed_sandbox_tests(drifted, drift_review, sandbox_root=good_sandbox, source_root=source_stub).get("block_reason") == "sandbox_target_drift")
        tampered_receipt = dict(passed_receipt)
        tampered_receipt["execution_status"] = "failed"
        require(build_sandbox_test_evidence(tampered_receipt).get("block_reason") == "invalid_test_receipt")
        require(diagnose_sandbox_test_evidence({**passed_evidence, "evidence_status": "blocked"}).get("block_reason") == "invalid_evidence_contract")
        require(review_repair_diagnosis({**failed_diagnosis, "diagnosis_digest": "0" * 64}, "confirm", "operator").get("block_reason") == "invalid_diagnosis_review_binding")
        require(build_supervised_repair_plan(failed_diagnosis, rejected_repair).get("block_reason") == "invalid_confirmed_diagnosis_binding")

        summary = sandbox_test_diagnosis_public_summary(failed_diagnosis)
        encoded = json.dumps({"evidence": failed_evidence, "diagnosis": summary, "plan": public_plan}, sort_keys=True)
        require("SANDBOX_CHECKPOINT_PRIVATE_SOURCE" not in encoded)
        require("SANDBOX_CHECKPOINT_PRIVATE_OUTPUT" not in encoded)
        require("stdout" not in encoded.lower())
        require("stderr" not in encoded.lower())
        require("source_text" not in encoded.lower())
        require("raw_patch" not in encoded.lower())
        require(not any(source_stub.rglob("*")))

    source_contract = _source_contract(source)
    require(source_contract["test_contract"] == "v1182.2")
    require(source_contract["evidence_contract"] == "v1182.5")
    require(source_contract["repair_contract"] == "v1182.8")
    require(source_contract["maximum_tests"] == 8)
    require(source_contract["maximum_timeout_seconds"] == 30)
    require(source_contract["maximum_test_results"] == 8)
    require(source_contract["maximum_evidence_diagnoses"] == 8)
    require(source_contract["maximum_repair_diagnoses"] == 8)
    require(source_contract["testing_production_write_present"] is False)
    require(source_contract["diagnosis_source_read_present"] is False)
    require(source_contract["diagnosis_write_present"] is False)
    require(source_contract["repair_source_read_present"] is False)
    require(source_contract["repair_write_present"] is False)
    require(source_contract["repair_authority_enabled"] is False)
    require(source_contract["retest_authority_enabled"] is False)

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_row = next((
        row for row in registry.get("checkpoints", [])
        if row.get("checkpoint_id") == "supervised-sandbox-testing-repair-checkpoint"
    ), None)
    require(checkpoint_row is not None)
    require((checkpoint_row or {}).get("builder") == "build_supervised_sandbox_testing_repair_checkpoint")
    require((checkpoint_row or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok"))
    require(privacy.get("source_only"))
    require(int(privacy.get("forbidden_count", privacy.get("forbidden_entry_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    evidence = {
        "retained_implementation_checkpoint": {
            "contract_version": prior.get("contract_version"),
            "passed": prior.get("passed"),
            "total": prior.get("total"),
            "structural_digest": prior.get("structural_digest"),
        },
        "sandbox_testing": {
            "passed_status": passed_receipt.get("execution_status"),
            "failed_status": failed_receipt.get("execution_status"),
            "passed_receipt_digest": passed_receipt.get("test_receipt_digest"),
            "failed_receipt_digest": failed_receipt.get("test_receipt_digest"),
        },
        "evidence_and_diagnosis": {
            "passed_posture": passed_diagnosis.get("diagnosis_posture"),
            "failure_diagnosis_digest": failed_diagnosis.get("diagnosis_digest"),
            "timeout_diagnosis_digest": timeout_diagnosis.get("diagnosis_digest"),
            "blocked_diagnosis_digest": blocked_diagnosis.get("diagnosis_digest"),
        },
        "repair_planning": {
            "repair_plan_digest": repair_plan.get("plan_digest"),
            "timeout_plan_digest": timeout_plan.get("plan_digest"),
            "blocked_plan_digest": blocked_plan.get("plan_digest"),
        },
        "source_contract": source_contract,
        "privacy": {
            "entry_count": privacy.get("entry_count"),
            "forbidden_entry_count": privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)),
            "private_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
    }
    evidence_text = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    forbidden_count = sum(1 for value in _FORBIDDEN_REPORT_TEXT if value in evidence_text)
    require(forbidden_count == 0)

    source_modified = source_before != _tree_signature(source)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    require(source_modified is False)
    require(runtime_mutated is False)

    report: dict[str, Any] = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "status": "ready" if all(checks) else "review_required",
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "supervised_sandbox_testing_repair_checkpoint_completed": True,
        "retained_supervised_implementation_checkpoint_completed": True,
        "sandbox_test_review_exercised": True,
        "sandbox_test_execution_exercised": True,
        "pass_failure_timeout_blocked_evidence_exercised": True,
        "conservative_diagnosis_exercised": True,
        "operator_diagnosis_review_exercised": True,
        "repair_retest_planning_exercised": True,
        "tamper_and_boundary_rejection_exercised": True,
        "production_source_read": False,
        "production_source_modified": False,
        "raw_source_exposed": False,
        "raw_test_output_exposed": False,
        "raw_patch_exposed": False,
        "patch_created": False,
        "patch_applied_to_source": False,
        "repair_performed": False,
        "tests_rerun": False,
        "shell_invoked": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "repair_authorized": False,
        "retest_authorized": False,
        "source_application_authorized": False,
        "execution_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "source_edit_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "retained_checkpoint_count": 1,
            "sandbox_test_review_case_count": 3,
            "sandbox_execution_case_count": 2,
            "evidence_outcome_case_count": 4,
            "diagnosis_case_count": 4,
            "repair_review_decision_case_count": 3,
            "repair_plan_case_count": 3,
            "negative_boundary_case_count": 13,
            "maximum_tests": MAX_TESTS,
            "maximum_timeout_seconds": MAX_TIMEOUT_SECONDS,
            "maximum_test_results": MAX_TEST_RESULTS,
            "maximum_diagnoses": min(EVIDENCE_MAX_DIAGNOSES, REPAIR_MAX_DIAGNOSES),
            "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
            "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
            "open_limitation_count": 5,
        },
        "evidence": evidence,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
