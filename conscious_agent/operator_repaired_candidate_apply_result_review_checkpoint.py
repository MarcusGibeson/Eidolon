from __future__ import annotations

"""Strictly read-only v1218.9 apply-result review checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from operator_repaired_candidate_apply_result_review import APPLY_RESULT_STATUSES, BASE_REVIEW_DECISIONS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, ROLLBACK_REVIEW_DECISIONS, _REVIEW_DECISION, _rollback_authorization_phrase, public_operator_repaired_candidate_apply_result_review

CONTRACT_VERSION = "v1218.9"
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


def _synthetic_review(*, applied: bool) -> dict[str, Any]:
    proposal_id = "devc_" + "1" * 24
    status = (
        "supervised_repaired_candidate_apply_completed"
        if applied else "supervised_repaired_candidate_apply_failed_rolled_back"
    )
    binding = {
        "contract_version": RETAINED_CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "supervised_repaired_candidate_apply_digest": "a" * 64,
        "supervised_repaired_candidate_apply_result_digest": "b" * 64,
        "apply_proposal_digest": "c" * 64,
        "source_workspace_digest": "d" * 64,
        "repair_workspace_digest": "e" * 64,
        "apply_plan_digest": "f" * 64,
        "authorization_receipt_digest": "1" * 64,
        "rollback_manifest_digest": "2" * 64,
        "apply_result_status": status,
    }
    review_digest = _digest(binding)
    decisions = ROLLBACK_REVIEW_DECISIONS if applied else BASE_REVIEW_DECISIONS
    row = {
        "ok": True,
        "schema_version": "1",
        "status": "operator_repaired_candidate_apply_result_review_required",
        **binding,
        "review_digest": review_digest,
        "apply_completed": applied,
        "rollback_available": applied,
        "rollback_eligible": applied,
        "available_decisions": list(decisions),
        "decision_phrases": [
            f"Record {decision} for repaired candidate apply result review {review_digest} "
            f"proposal {proposal_id} revision 1 failed attempt 2 repair attempt 1 apply attempt 1."
            for decision in decisions
        ],
        "repair_attempt_limit": 1,
        "apply_attempt_limit": 1,
        "operator_review_required": True,
        "apply_result_review_required": True,
        "rollback_proposal_created": False,
        "rollback_authorization_required": False,
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
        "apply_authorized": False,
        "rollback_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }
    return public_operator_repaired_candidate_apply_result_review(row)


def _synthetic_rollback_proposal(review: dict[str, Any]) -> dict[str, Any]:
    binding = {
        "contract_version": RETAINED_CONTRACT_VERSION,
        "proposal_id": review["proposal_id"],
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "supervised_repaired_candidate_apply_digest": review["supervised_repaired_candidate_apply_digest"],
        "supervised_repaired_candidate_apply_result_digest": review["supervised_repaired_candidate_apply_result_digest"],
        "apply_proposal_digest": review["apply_proposal_digest"],
        "source_workspace_digest": review["source_workspace_digest"],
        "repair_workspace_digest": review["repair_workspace_digest"],
        "apply_plan_digest": review["apply_plan_digest"],
        "authorization_receipt_digest": review["authorization_receipt_digest"],
        "rollback_manifest_digest": review["rollback_manifest_digest"],
        "review_digest": review["review_digest"],
        "operator_repaired_candidate_apply_result_decision_digest": "3" * 64,
    }
    proposal_digest = _digest(binding)
    row = {
        "ok": True,
        "schema_version": "1",
        "status": "bounded_repaired_candidate_rollback_proposal_authorization_required",
        **binding,
        "rollback_proposal_digest": proposal_digest,
        "rollback_scope": "one_selected_project_rollback_attempt",
        "rollback_target": "exact_pre_apply_project_state",
        "maximum_rollback_attempts": 1,
        "requires_exact_authorization": True,
        "authorization_phrase": _rollback_authorization_phrase(
            proposal_digest, review["proposal_id"], 1, 2
        ),
        "repair_attempt_limit": 1,
        "apply_attempt_limit": 1,
        "operator_review_required": True,
        "apply_result_review_required": True,
        "rollback_proposal_created": True,
        "rollback_authorization_required": True,
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
        "apply_authorized": False,
        "rollback_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }
    return public_operator_repaired_candidate_apply_result_review(row)


def build_operator_repaired_candidate_apply_result_review_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    applied = _synthetic_review(applied=True)
    restored = _synthetic_review(applied=False)
    rollback = _synthetic_rollback_proposal(applied)

    check(applied.get("ok") is True)
    check(applied.get("rollback_eligible") is True)
    check(applied.get("rollback_available") is True)
    check(len(applied.get("available_decisions") or []) == 4)
    check("propose-rollback" in (applied.get("available_decisions") or []))
    check(all(_REVIEW_DECISION.fullmatch(value) for value in applied.get("decision_phrases") or []))
    check(restored.get("rollback_eligible") is False)
    check(restored.get("rollback_available") is False)
    check(len(restored.get("available_decisions") or []) == 3)
    check("propose-rollback" not in (restored.get("available_decisions") or []))

    check(rollback.get("ok") is True)
    check(rollback.get("status") == "bounded_repaired_candidate_rollback_proposal_authorization_required")
    check(rollback.get("rollback_scope") == "one_selected_project_rollback_attempt")
    check(rollback.get("rollback_target") == "exact_pre_apply_project_state")
    check(rollback.get("maximum_rollback_attempts") == 1)
    check(rollback.get("rollback_proposal_created") is True)
    check(rollback.get("rollback_authorization_required") is True)
    check(rollback.get("rollback_authorized") is False)
    check(rollback.get("rollback_executed") is False)
    check(str(rollback.get("rollback_proposal_digest")) in str(rollback.get("authorization_phrase")))

    for row in (applied, restored, rollback):
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
        check(row.get("apply_authorized") is False)
        check(row.get("rollback_authorized") is False)
        check(row.get("install_authorized") is False)
        check(row.get("promotion_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("authority_granted") is False)

    check(len(APPLY_RESULT_STATUSES) == 4)
    check(RETAINED_CONTRACT_VERSION == "v1218.8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    module = (source / "conscious_agent" / "operator_repaired_candidate_apply_result_review.py").read_text(encoding="utf-8")
    check("process_operator_repaired_candidate_apply_result_review_control" in ordinary)
    check("attach_operator_repaired_candidate_apply_result_review" in ordinary)
    check("LocalModelClient" not in module)
    check('"rollback_authorized": True' not in module)
    check('"install_authorized": True' not in module)
    check('"promotion_authorized": True' not in module)
    check('"release_authorized": True' not in module)
    check('"authority_granted": True' not in module)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((
        row for row in registry["checkpoints"]
        if row["checkpoint_id"] == "operator-repaired-candidate-apply-result-review-checkpoint"
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
        "base_decision_count": len(BASE_REVIEW_DECISIONS),
        "rollback_eligible_decision_count": len(ROLLBACK_REVIEW_DECISIONS),
        "separate_rollback_authorization_required": True,
        "rollback_proposal_preparation_present": True,
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
        "rollback_proposal_prepared_operationally": False,
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
            "Only an applied result with intact rollback evidence may propose rollback.",
            "Operational rollback requires a later exact authorization and is outside v1218.",
            "The checkpoint cannot apply, roll back, install, promote, release, or grant authority.",
        ],
    }
    report["structural_digest"] = _digest({
        key: value for key, value in report.items() if key != "structural_digest"
    })
    return report
