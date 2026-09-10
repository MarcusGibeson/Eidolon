from __future__ import annotations

"""Strictly read-only v1215.9 supervised repair execution checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from conversational_supervised_repair_execution import CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, DIAGNOSABLE_FAILURES, _AUTHORIZATION, _authority, public_conversational_supervised_repair
from operator_diagnosis_review import _repair_authorization_phrase

CONTRACT_VERSION = "v1215.9"
_EXCLUDED = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "reports"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in _EXCLUDED)
        for name in sorted(files):
            path = Path(base) / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(root).as_posix()
            content = path.read_bytes()
            digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(content).digest())
            count += 1
    return digest.hexdigest(), count


def _synthetic_prepared() -> dict[str, Any]:
    proposal_id = "devc_" + "1" * 24
    repair_digest = "c" * 64
    row = {
        "ok": True,
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "status": "supervised_repair_execution_prepared",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "proposal_revision_digest": "2" * 64,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "repair_attempt_limit": 1,
        "failed_attempt_digest": "3" * 64,
        "failed_continuation_result_digest": "4" * 64,
        "failed_loop_result_digest": "5" * 64,
        "diagnosis_digest": "6" * 64,
        "diagnosis_result_digest": "7" * 64,
        "review_digest": "8" * 64,
        "operator_diagnosis_decision_digest": "9" * 64,
        "repair_proposal_digest": repair_digest,
        "bounded_repair_proposal_record_digest": "a" * 64,
        "source_workspace_digest": "b" * 64,
        "source_generation_digest": "d" * 64,
        "project_kind": "new_python_cli_project",
        "selected_adapter_id": "python",
        "supervised_repair_execution_digest": "e" * 64,
        "authorization_phrase": _repair_authorization_phrase(repair_digest, proposal_id, 1, 2),
        "phase": "prepared",
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "patch_generated": False,
        "repair_executed": False,
        "operator_review_required": True,
        "repair_result_review_required": True,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "runtime_records_external": True,
        **_authority(authorized=False),
    }
    return public_conversational_supervised_repair(row)


def _synthetic_result(prepared: dict[str, Any], *, passed: bool) -> dict[str, Any]:
    lineage = [
        {"stage": "failed_continuation_artifact", "artifact_digest": prepared["failed_continuation_result_digest"]},
        {"stage": "authorized_repair_proposal", "artifact_digest": prepared["repair_proposal_digest"]},
        {"stage": "isolated_repair_build_and_test", "artifact_digest": "f" * 64},
    ]
    row = {
        **prepared,
        "ok": passed,
        "status": "supervised_repair_completed" if passed else "supervised_repair_tests_failed",
        "completed_stage": "complete" if passed else "test",
        "phase": "sealed",
        "repair_workspace_digest": "1" * 64,
        "repair_loop_digest": "2" * 64,
        "repair_loop_result_digest": "3" * 64,
        "provider_contacted": True,
        "tests_executed": True,
        "retest_executed": True,
        "test_passed": passed,
        "cleanup_confirmed": True,
        "patch_generated": True,
        "repair_executed": True,
        "repair_lineage": lineage,
        "repair_lineage_digest": _digest(lineage),
        "operator_review_required": True,
        "repair_result_review_required": True,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        **_authority(authorized=True),
    }
    return public_conversational_supervised_repair(row)


def build_conversational_supervised_repair_execution_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    prepared = _synthetic_prepared()
    passed = _synthetic_result(prepared, passed=True)
    failed = _synthetic_result(prepared, passed=False)
    check(prepared.get("ok") is True)
    check(prepared.get("status") == "supervised_repair_execution_prepared")
    check(prepared.get("repair_attempt_number") == 1)
    check(prepared.get("repair_attempt_limit") == 1)
    check(prepared.get("failed_attempt_number") == 2)
    check(prepared.get("source_workspace_digest") == "b" * 64)
    check(prepared.get("project_kind") == "new_python_cli_project")
    check(prepared.get("selected_adapter_id") == "python")
    check(_AUTHORIZATION.fullmatch(str(prepared.get("authorization_phrase") or "")) is not None)
    check(str(prepared.get("repair_proposal_digest")) in str(prepared.get("authorization_phrase")))
    check(passed.get("status") == "supervised_repair_completed")
    check(passed.get("test_passed") is True)
    check(failed.get("status") == "supervised_repair_tests_failed")
    check(failed.get("test_passed") is False)
    for row in (prepared, passed, failed):
        check(row.get("content_free") is True)
        check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False)
        check(row.get("raw_provider_output_exposed") is False)
        check(row.get("raw_test_output_exposed") is False)
        check(row.get("selected_project_modified") is False)
        check(row.get("source_modified") is False)
        check(row.get("apply_authorized") is False)
        check(row.get("install_authorized") is False)
        check(row.get("promotion_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("model_management_authorized") is False)
        check(row.get("authority_granted") is False)
    check(prepared.get("provider_contacted") is False)
    check(prepared.get("tests_executed") is False)
    check(prepared.get("repair_executed") is False)
    for row in (passed, failed):
        check(row.get("provider_contacted") is True)
        check(row.get("tests_executed") is True)
        check(row.get("retest_executed") is True)
        check(row.get("patch_generated") is True)
        check(row.get("repair_executed") is True)
        check(row.get("repair_execution_authorized") is True)
        check(row.get("operator_review_required") is True)
        check(row.get("repair_result_review_required") is True)
        check(len(row.get("repair_lineage") or []) == 3)
        check(bool(row.get("repair_lineage_digest")))
    check(len(DIAGNOSABLE_FAILURES) == 4)
    check(RETAINED_CONTRACT_VERSION == "v1215.8")

    module_source = (source / "conscious_agent" / "conversational_supervised_repair_execution.py").read_text(encoding="utf-8")
    ordinary_source = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    check("authorize_and_run_conversational_build_test_loop" in module_source)
    check("run_or_resume_general_small_project_implementation" not in module_source)
    check("run_or_resume_selected_test_adapter" not in module_source)
    check("process_conversational_supervised_repair_control" in ordinary_source)
    check('"apply_authorized": True' not in module_source)
    check('"release_authorized": True' not in module_source)
    check('"authority_granted": True' not in module_source)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == "conversational-supervised-repair-execution-checkpoint"),
        None,
    )
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)

    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "diagnosable_failure_count": len(DIAGNOSABLE_FAILURES),
        "exact_repair_authorization_required": True,
        "repair_attempt_limit": 1,
        "isolated_repair_execution_present": True,
        "retained_build_coordinator_present": True,
        "retained_test_adapter_present": True,
        "result_outcome_count": 5,
        "operator_review_required": True,
        "project_modified": False,
        "apply_authorized": False,
        "authority_preserved": True,
    }
    report = {
        "ok": all(checks),
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "read_only": True,
        "post_available": False,
        "synthetic_contract_evaluation": True,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "project_tests_executed": False,
        "retest_executed": False,
        "patch_generated": False,
        "repair_executed": False,
        "project_modified": False,
        "dependencies_installed": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates synthetic content-free records and reads no private runtime data.",
            "Operational repair requires one exact v1214 authorization and remains limited to one isolated attempt.",
            "The retained build coordinator and selected test adapter perform operational work; the checkpoint invokes neither.",
            "Successful repaired candidates still require operator review and cannot be applied, installed, promoted, or released here.",
        ],
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
