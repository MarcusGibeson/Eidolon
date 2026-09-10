from __future__ import annotations

"""Strictly read-only v1220.9 repaired-candidate rollback-result review checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from operator_repaired_candidate_rollback_result_review import COMPLETED_ROLLBACK_STATUSES, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, ROLLBACK_RESULT_REVIEW_DECISIONS, _REVIEW_DECISION, public_operator_repaired_candidate_rollback_result_review
from conversational_supervised_repaired_candidate_rollback import ROLLBACK_RESULT_STATUSES

CONTRACT_VERSION = "v1220.9"
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
            digest.update(relative.encode() + b"\0" + hashlib.sha256(content).digest())
            count += 1
    return digest.hexdigest(), count


def _synthetic_review(*, completed: bool) -> dict[str, Any]:
    proposal_id = "devc_" + "1" * 24
    result_status = (
        "supervised_repaired_candidate_rollback_completed"
        if completed
        else "supervised_repaired_candidate_rollback_failed_applied_state_restored"
    )
    binding = {
        "contract_version": RETAINED_CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "rollback_attempt_number": 1,
        "supervised_repaired_candidate_rollback_digest": "a" * 64,
        "supervised_repaired_candidate_rollback_result_digest": "b" * 64,
        "rollback_proposal_digest": "c" * 64,
        "supervised_repaired_candidate_apply_digest": "d" * 64,
        "supervised_repaired_candidate_apply_result_digest": "e" * 64,
        "source_workspace_digest": "f" * 64,
        "repair_workspace_digest": "1" * 64,
        "apply_plan_digest": "2" * 64,
        "apply_authorization_receipt_digest": "3" * 64,
        "rollback_manifest_digest": "4" * 64,
        "rollback_authorization_receipt_digest": "5" * 64,
        "operator_apply_result_review_digest": "6" * 64,
        "operator_apply_result_decision_digest": "7" * 64,
        "rollback_result_status": result_status,
    }
    review_digest = _digest(binding)
    row = {
        "ok": True,
        "schema_version": "1",
        "status": "operator_repaired_candidate_rollback_result_review_required",
        **binding,
        "review_digest": review_digest,
        "rollback_completed": completed,
        "pre_apply_state_restored": completed,
        "applied_repaired_candidate_state_restored": not completed,
        "outcome_class": (
            "pre_apply_state_restored"
            if completed
            else "rollback_failed_applied_repaired_candidate_state_restored"
        ),
        "reviewed_rollback_authorization_consumed": True,
        "reviewed_rollback_execution_completed": completed,
        "available_decisions": list(ROLLBACK_RESULT_REVIEW_DECISIONS),
        "decision_phrases": [
            f"Record {decision} for repaired candidate rollback result review {review_digest} "
            f"proposal {proposal_id} revision 1 failed attempt 2 repair attempt 1 "
            f"apply attempt 1 rollback attempt 1."
            for decision in ROLLBACK_RESULT_REVIEW_DECISIONS
        ],
        "repair_attempt_limit": 1,
        "apply_attempt_limit": 1,
        "rollback_attempt_limit": 1,
        "operator_review_required": True,
        "rollback_result_review_required": True,
        "terminal_disposition_only": True,
        "rollback_retry_available": False,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "rollback_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }
    return public_operator_repaired_candidate_rollback_result_review(row)


def _synthetic_decision(review: dict[str, Any], decision: str) -> dict[str, Any]:
    state = {
        "accept-rollback-result": "rollback_result_accepted",
        "defer": "rollback_result_deferred",
        "reject-rollback-result": "rollback_result_rejected",
    }[decision]
    row = {
        "ok": True,
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "status": "operator_repaired_candidate_rollback_result_decision_recorded",
        "proposal_id": review["proposal_id"],
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "repair_attempt_limit": 1,
        "apply_attempt_number": 1,
        "apply_attempt_limit": 1,
        "rollback_attempt_number": 1,
        "rollback_attempt_limit": 1,
        "review_digest": review["review_digest"],
        "supervised_repaired_candidate_rollback_digest": review["supervised_repaired_candidate_rollback_digest"],
        "supervised_repaired_candidate_rollback_result_digest": review["supervised_repaired_candidate_rollback_result_digest"],
        "rollback_result_status": review["rollback_result_status"],
        "outcome_class": review["outcome_class"],
        "decision": decision,
        "decision_state": state,
        "operator_review_required": True,
        "rollback_result_review_required": True,
        "terminal_disposition_only": True,
        "rollback_retry_available": False,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "rollback_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }
    return public_operator_repaired_candidate_rollback_result_review(row)


def build_operator_repaired_candidate_rollback_result_review_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    completed = _synthetic_review(completed=True)
    failed = _synthetic_review(completed=False)
    decisions = [_synthetic_decision(completed, value) for value in ROLLBACK_RESULT_REVIEW_DECISIONS]

    check(completed.get("ok") is True)
    check(completed.get("rollback_completed") is True)
    check(completed.get("pre_apply_state_restored") is True)
    check(completed.get("applied_repaired_candidate_state_restored") is False)
    check(failed.get("ok") is True)
    check(failed.get("rollback_completed") is False)
    check(failed.get("pre_apply_state_restored") is False)
    check(failed.get("applied_repaired_candidate_state_restored") is True)
    for row in (completed, failed):
        check(len(row.get("available_decisions") or []) == 3)
        check(set(row.get("available_decisions") or []) == set(ROLLBACK_RESULT_REVIEW_DECISIONS))
        check(all(_REVIEW_DECISION.fullmatch(value) for value in row.get("decision_phrases") or []))
        check(row.get("terminal_disposition_only") is True)
        check(row.get("rollback_retry_available") is False)
    check({row.get("decision") for row in decisions} == set(ROLLBACK_RESULT_REVIEW_DECISIONS))
    check({row.get("decision_state") for row in decisions} == {
        "rollback_result_accepted", "rollback_result_deferred", "rollback_result_rejected"
    })

    for row in (completed, failed, *decisions):
        check(row.get("content_free") is True)
        check(row.get("private_request_exposed") is False)
        check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False)
        check(row.get("rollback_content_exposed") is False)
        check(row.get("provider_contacted") is False)
        check(row.get("tests_executed") is False)
        check(row.get("retest_executed") is False)
        check(row.get("repair_executed") is False)
        check(row.get("apply_executed") is False)
        check(row.get("rollback_executed") is False)
        check(row.get("project_modified") is False)
        check(row.get("source_modified") is False)
        check(row.get("rollback_authorized") is False)
        check(row.get("install_authorized") is False)
        check(row.get("promotion_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("authority_granted") is False)

    check(len(ROLLBACK_RESULT_STATUSES) == 4)
    check(len(COMPLETED_ROLLBACK_STATUSES) == 2)
    check(RETAINED_CONTRACT_VERSION == "v1220.8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    module = (source / "conscious_agent" / "operator_repaired_candidate_rollback_result_review.py").read_text(encoding="utf-8")
    check("process_operator_repaired_candidate_rollback_result_review_control" in ordinary)
    check("attach_operator_repaired_candidate_rollback_result_review" in ordinary)
    check("LocalModelClient" not in module)
    check('"rollback_authorized": True' not in module)
    check('"install_authorized": True' not in module)
    check('"promotion_authorized": True' not in module)
    check('"release_authorized": True' not in module)
    check('"authority_granted": True' not in module)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((
        row for row in registry["checkpoints"]
        if row["checkpoint_id"] == "operator-repaired-candidate-rollback-result-review-checkpoint"
    ), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)

    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "rollback_result_outcome_count": len(ROLLBACK_RESULT_STATUSES),
        "rollback_result_decision_count": len(ROLLBACK_RESULT_REVIEW_DECISIONS),
        "terminal_disposition_only": True,
        "rollback_retry_available": False,
        "checkpoint_rollback_executed": False,
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
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "dependencies_installed": False,
        "rollback_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates synthetic content-free records and reads no private runtime data.",
            "Review decisions are terminal dispositions and cannot retry rollback or mutate a project.",
            "The checkpoint cannot contact providers, run tests, repair, apply, roll back, install, promote, release, or grant authority.",
        ],
    }
    report["structural_digest"] = _digest({
        key: value for key, value in report.items() if key != "structural_digest"
    })
    return report
