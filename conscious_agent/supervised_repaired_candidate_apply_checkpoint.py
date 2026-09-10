from __future__ import annotations

"""Strictly read-only v1217.9 repaired-candidate apply checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from conversational_supervised_repaired_candidate_apply import APPLY_RESULT_STATUSES, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, _AUTHORIZATION, public_supervised_repaired_candidate_apply
from operator_repair_result_review import _apply_authorization_phrase

CONTRACT_VERSION = "v1217.9"
_EXCLUDED = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "dist", "build", "reports",
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


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
    apply_proposal_digest = "a" * 64
    row = {
        "ok": True,
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "status": "supervised_repaired_candidate_apply_prepared",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "apply_attempt_limit": 1,
        "apply_proposal_digest": apply_proposal_digest,
        "review_digest": "b" * 64,
        "operator_repair_result_decision_digest": "c" * 64,
        "supervised_repair_execution_digest": "d" * 64,
        "supervised_repair_result_digest": "e" * 64,
        "source_workspace_digest": "f" * 64,
        "repair_workspace_digest": "1" * 64,
        "repair_loop_result_digest": "2" * 64,
        "apply_plan_digest": "3" * 64,
        "supervised_repaired_candidate_apply_digest": "4" * 64,
        "authorization_phrase": _apply_authorization_phrase(
            apply_proposal_digest, proposal_id, 1, 2
        ),
        "operation_count": 1,
        "operation_path_digests": ["5" * 64],
        "total_apply_bytes": 57,
        "phase": "prepared",
        "recovery_count": 0,
        "operator_review_required": True,
        "apply_result_review_required": True,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "repair_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "rollback_prepared": False,
        "rollback_executed": False,
        "apply_execution_authorized": False,
        "apply_authorized": False,
        "rollback_authorized": False,
        "repair_execution_authorized": False,
        "provider_contact_authorized": False,
        "test_execution_authorized": False,
        "retest_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }
    return public_supervised_repaired_candidate_apply(row)


def _synthetic_result(prepared: dict[str, Any], *, completed: bool) -> dict[str, Any]:
    row = {
        **prepared,
        "ok": completed,
        "status": (
            "supervised_repaired_candidate_apply_completed"
            if completed
            else "supervised_repaired_candidate_apply_failed_rolled_back"
        ),
        "phase": "sealed",
        "authorization_receipt_digest": "6" * 64,
        "authorization_consumption_count": 1,
        "rollback_manifest_digest": "7" * 64,
        "rollback_prepared": True,
        "rollback_available": completed,
        "rollback_executed": not completed,
        "applied_count": 1 if completed else 0,
        "applied_path_digests": ["5" * 64] if completed else [],
        "project_modified": completed,
        "selected_project_modified": completed,
        "apply_execution_authorized": True,
        "apply_authorized": True,
        "rollback_authorized": False,
        "supervised_repaired_candidate_apply_result_digest": "8" * 64,
    }
    return public_supervised_repaired_candidate_apply(row)


def build_supervised_repaired_candidate_apply_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    prepared = _synthetic_prepared()
    completed = _synthetic_result(prepared, completed=True)
    rolled_back = _synthetic_result(prepared, completed=False)

    check(prepared.get("ok") is True)
    check(prepared.get("status") == "supervised_repaired_candidate_apply_prepared")
    check(prepared.get("phase") == "prepared")
    check(prepared.get("apply_attempt_number") == 1)
    check(prepared.get("apply_attempt_limit") == 1)
    check(prepared.get("operation_count") == 1)
    check(prepared.get("rollback_prepared") is False)
    check(prepared.get("apply_authorized") is False)
    check(prepared.get("project_modified") is False)
    check(_AUTHORIZATION.fullmatch(str(prepared.get("authorization_phrase") or "")) is not None)
    check(str(prepared.get("apply_proposal_digest")) in str(prepared.get("authorization_phrase")))

    check(completed.get("ok") is True)
    check(completed.get("status") == "supervised_repaired_candidate_apply_completed")
    check(completed.get("authorization_consumption_count") == 1)
    check(completed.get("rollback_prepared") is True)
    check(completed.get("rollback_available") is True)
    check(completed.get("rollback_executed") is False)
    check(completed.get("applied_count") == 1)
    check(completed.get("project_modified") is True)
    check(completed.get("selected_project_modified") is True)
    check(completed.get("apply_authorized") is True)
    check(completed.get("rollback_authorized") is False)

    check(rolled_back.get("ok") is False)
    check(rolled_back.get("status") == "supervised_repaired_candidate_apply_failed_rolled_back")
    check(rolled_back.get("authorization_consumption_count") == 1)
    check(rolled_back.get("rollback_prepared") is True)
    check(rolled_back.get("rollback_available") is False)
    check(rolled_back.get("rollback_executed") is True)
    check(rolled_back.get("applied_count") == 0)
    check(rolled_back.get("project_modified") is False)
    check(rolled_back.get("selected_project_modified") is False)
    check(rolled_back.get("rollback_authorized") is False)

    for row in (prepared, completed, rolled_back):
        check(row.get("content_free") is True)
        check(row.get("private_request_exposed") is False)
        check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False)
        check(row.get("rollback_content_exposed") is False)
        check(row.get("raw_provider_output_exposed") is False)
        check(row.get("raw_test_output_exposed") is False)
        check(row.get("provider_contacted") is False)
        check(row.get("tests_executed") is False)
        check(row.get("retest_executed") is False)
        check(row.get("repair_executed") is False)
        check(row.get("source_modified") is False)
        check(row.get("install_authorized") is False)
        check(row.get("promotion_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("model_management_authorized") is False)
        check(row.get("authority_granted") is False)
    check(len(APPLY_RESULT_STATUSES) == 4)
    check(RETAINED_CONTRACT_VERSION == "v1217.8")

    module_source = (
        source / "conscious_agent" / "conversational_supervised_repaired_candidate_apply.py"
    ).read_text(encoding="utf-8")
    ordinary_source = (
        source / "conscious_agent" / "ordinary_chat_development_campaign.py"
    ).read_text(encoding="utf-8")
    check("process_supervised_repaired_candidate_apply_control" in ordinary_source)
    check("_prepare_rollback_manifest" in module_source)
    check("authorization_receipt_digest" in module_source)
    check("APPLY_LEASE_SECONDS" in module_source)
    check("authorize_and_run_conversational_build_test_loop" not in module_source)
    check("LocalModelClient" not in module_source)
    check('"rollback_authorized": True' not in module_source)
    check('"install_authorized": True' not in module_source)
    check('"promotion_authorized": True' not in module_source)
    check('"release_authorized": True' not in module_source)
    check('"authority_granted": True' not in module_source)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((
        row for row in registry["checkpoints"]
        if row["checkpoint_id"] == "supervised-repaired-candidate-apply-checkpoint"
    ), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)

    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "apply_result_outcome_count": len(APPLY_RESULT_STATUSES),
        "apply_attempt_limit": 1,
        "exact_v1216_authorization_required": True,
        "rollback_evidence_required_before_write": True,
        "selected_project_scope_bound": True,
        "operator_review_required": True,
        "rollback_separately_authorized": True,
        "checkpoint_apply_executed": False,
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
        "repair_executed": False,
        "apply_prepared_operationally": False,
        "apply_executed": False,
        "rollback_prepared_operationally": False,
        "rollback_executed": False,
        "project_modified": False,
        "dependencies_installed": False,
        "apply_authorized": False,
        "rollback_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates synthetic content-free records and reads no private runtime data.",
            "Operational apply requires one exact sealed v1216 apply proposal and authorization phrase.",
            "Rollback evidence is prepared privately before an operational write, but rollback authorization remains separate.",
            "The checkpoint cannot apply, roll back, install, promote, release, or grant authority.",
        ],
    }
    report["structural_digest"] = _digest({
        key: value for key, value in report.items() if key != "structural_digest"
    })
    return report
