from __future__ import annotations

"""Strictly read-only v1216.9 operator repair-result review checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from operator_repair_result_review import BASE_REVIEW_DECISIONS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, PASSING_REVIEW_DECISIONS, REPAIR_RESULT_STATUSES, _REVIEW_DECISION, _apply_authorization_phrase, _review_phrase, public_operator_repair_result_review

CONTRACT_VERSION = "v1216.9"
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


def _synthetic_review(*, passing: bool) -> dict[str, Any]:
    proposal_id = "devc_" + "1" * 24
    review_digest = "a" * 64
    decisions = PASSING_REVIEW_DECISIONS if passing else BASE_REVIEW_DECISIONS
    row = {
        "ok": True,
        "schema_version": "1",
        "contract_version": RETAINED_CONTRACT_VERSION,
        "status": "operator_repair_result_review_required",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "repair_attempt_limit": 1,
        "supervised_repair_execution_digest": "2" * 64,
        "supervised_repair_result_digest": "3" * 64,
        "repair_proposal_digest": "4" * 64,
        "source_workspace_digest": "5" * 64,
        "repair_workspace_digest": "6" * 64 if passing else "",
        "repair_loop_result_digest": "7" * 64 if passing else "8" * 64,
        "repair_result_status": (
            "supervised_repair_completed" if passing else "supervised_repair_tests_failed"
        ),
        "review_digest": review_digest,
        "repair_passed": passing,
        "candidate_apply_eligible": passing,
        "test_passed": passing,
        "cleanup_confirmed": True,
        "available_decisions": list(decisions),
        "decision_phrases": [
            _review_phrase(decision, review_digest, proposal_id, 1, 2)
            for decision in decisions
        ],
        "operator_review_required": True,
        "repair_result_review_required": True,
        "apply_proposal_created": False,
        "apply_authorization_required": False,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "patch_generated": False,
        "repair_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "runtime_records_external": True,
        "repair_execution_authorized": False,
        "provider_contact_authorized": False,
        "test_execution_authorized": False,
        "retest_authorized": False,
        "apply_authorized": False,
        "rollback_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }
    return public_operator_repair_result_review(row)


def _synthetic_apply_proposal(review: dict[str, Any]) -> dict[str, Any]:
    apply_digest = "b" * 64
    row = {
        **review,
        "ok": True,
        "status": "bounded_repaired_candidate_apply_proposal_authorization_required",
        "operator_repair_result_decision_digest": "c" * 64,
        "apply_proposal_digest": apply_digest,
        "apply_scope": "one_selected_project_apply_attempt",
        "apply_target": "exact_isolated_repaired_candidate",
        "maximum_apply_attempts": 1,
        "requires_exact_authorization": True,
        "authorization_phrase": _apply_authorization_phrase(
            apply_digest,
            str(review["proposal_id"]),
            int(review["proposal_revision"]),
            int(review["failed_attempt_number"]),
        ),
        "apply_proposal_created": True,
        "apply_authorization_required": True,
        "apply_authorized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "authority_granted": False,
    }
    return public_operator_repair_result_review(row)


def build_operator_repair_result_review_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    passing = _synthetic_review(passing=True)
    failed = _synthetic_review(passing=False)
    apply_proposal = _synthetic_apply_proposal(passing)

    check(passing.get("ok") is True)
    check(passing.get("status") == "operator_repair_result_review_required")
    check(passing.get("repair_passed") is True)
    check(passing.get("candidate_apply_eligible") is True)
    check(passing.get("test_passed") is True)
    check(passing.get("cleanup_confirmed") is True)
    check(passing.get("repair_attempt_number") == 1)
    check(passing.get("repair_attempt_limit") == 1)
    check(passing.get("available_decisions") == list(PASSING_REVIEW_DECISIONS))
    check(len(passing.get("decision_phrases") or []) == 4)
    check(failed.get("repair_passed") is False)
    check(failed.get("candidate_apply_eligible") is False)
    check(failed.get("available_decisions") == list(BASE_REVIEW_DECISIONS))
    check(len(failed.get("decision_phrases") or []) == 3)
    check("propose-apply" not in (failed.get("available_decisions") or []))
    for phrase in passing.get("decision_phrases") or []:
        check(_REVIEW_DECISION.fullmatch(str(phrase)) is not None)
    for phrase in failed.get("decision_phrases") or []:
        check(_REVIEW_DECISION.fullmatch(str(phrase)) is not None)

    check(apply_proposal.get("ok") is True)
    check(apply_proposal.get("status") == "bounded_repaired_candidate_apply_proposal_authorization_required")
    check(apply_proposal.get("apply_scope") == "one_selected_project_apply_attempt")
    check(apply_proposal.get("apply_target") == "exact_isolated_repaired_candidate")
    check(apply_proposal.get("maximum_apply_attempts") == 1)
    check(apply_proposal.get("requires_exact_authorization") is True)
    check(apply_proposal.get("apply_proposal_created") is True)
    check(apply_proposal.get("apply_authorization_required") is True)
    check(str(apply_proposal.get("apply_proposal_digest")) in str(apply_proposal.get("authorization_phrase")))

    for row in (passing, failed, apply_proposal):
        check(row.get("content_free") is True)
        check(row.get("private_request_exposed") is False)
        check(row.get("private_path_exposed") is False)
        check(row.get("private_content_exposed") is False)
        check(row.get("raw_provider_output_exposed") is False)
        check(row.get("raw_test_output_exposed") is False)
        check(row.get("provider_contacted") is False)
        check(row.get("tests_executed") is False)
        check(row.get("project_modified") is False)
        check(row.get("selected_project_modified") is False)
        check(row.get("source_modified") is False)
        check(row.get("apply_authorized") is False)
        check(row.get("rollback_authorized") is False)
        check(row.get("install_authorized") is False)
        check(row.get("promotion_authorized") is False)
        check(row.get("release_authorized") is False)
        check(row.get("model_management_authorized") is False)
        check(row.get("authority_granted") is False)
    check(len(REPAIR_RESULT_STATUSES) == 5)
    check(RETAINED_CONTRACT_VERSION == "v1216.8")

    module_source = (
        source / "conscious_agent" / "operator_repair_result_review.py"
    ).read_text(encoding="utf-8")
    ordinary_source = (
        source / "conscious_agent" / "ordinary_chat_development_campaign.py"
    ).read_text(encoding="utf-8")
    check("process_operator_repair_result_review_control" in ordinary_source)
    check("attach_operator_repair_result_review" in ordinary_source)
    check("authorize_and_run_conversational_build_test_loop" not in module_source)
    check("_workspace_root(" not in module_source)
    check('"apply_authorized": True' not in module_source)
    check('"release_authorized": True' not in module_source)
    check('"authority_granted": True' not in module_source)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (
            row for row in registry["checkpoints"]
            if row["checkpoint_id"] == "operator-repair-result-review-checkpoint"
        ),
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
        "repair_result_outcome_count": len(REPAIR_RESULT_STATUSES),
        "passing_decision_count": len(PASSING_REVIEW_DECISIONS),
        "nonpassing_decision_count": len(BASE_REVIEW_DECISIONS),
        "passing_candidate_required_for_apply_proposal": True,
        "exact_review_decision_required": True,
        "separate_apply_authorization_required": True,
        "apply_attempt_limit": 1,
        "apply_executed": False,
        "project_modified": False,
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
        "apply_proposal_prepared_operationally": False,
        "apply_executed": False,
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
            "Operational review requires one exact sealed v1215 repair result.",
            "Only a passing, cleanup-confirmed repaired candidate may produce an apply proposal.",
            "The apply proposal remains separately authorized; this checkpoint cannot apply, roll back, install, promote, or release it.",
        ],
    }
    report["structural_digest"] = _digest({
        key: value for key, value in report.items() if key != "structural_digest"
    })
    return report
