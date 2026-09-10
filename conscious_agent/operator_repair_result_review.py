from __future__ import annotations

"""Operator review and apply-proposal preparation for v1215 repair results.

One exact sealed supervised-repair result may produce one durable, content-free
operator review packet.  An exact conversational decision may accept the
result, defer, reject the repair, or (only for a passing repaired candidate)
propose a later apply action.  The apply proposal is separately authorization
gated.  This module never reads candidate contents, runs tests, mutates the
selected project, applies files, installs, promotes, releases, manages models,
or grants independent authority.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from conversational_supervised_repair_execution import (
    load_conversational_supervised_repair_execution,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1216.8"

REPAIR_RESULT_STATUSES = frozenset({
    "supervised_repair_completed",
    "supervised_repair_tests_failed",
    "supervised_repair_test_blocked",
    "supervised_repair_build_blocked",
    "supervised_repair_internal_error",
})
PASSING_REPAIR_STATUS = "supervised_repair_completed"
BASE_REVIEW_DECISIONS = (
    "accept-repair-result",
    "defer",
    "reject-repair",
)
PASSING_REVIEW_DECISIONS = (*BASE_REVIEW_DECISIONS, "propose-apply")

AUTHORITY_FLAGS = {
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

_REVIEW_DECISION = re.compile(
    r"^record\s+(?P<decision>accept-repair-result|defer|reject-repair|propose-apply)\s+"
    r"for\s+repair\s+result\s+review\s+(?P<review_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)\s+"
    r"failed\s+attempt\s+(?P<failed_attempt>[2-9][0-9]*)\s+repair\s+attempt\s+"
    r"(?P<repair_attempt>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _review_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_repair_result_reviews"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _decision_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_repair_result_decisions"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _apply_proposal_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "bounded_repaired_candidate_apply_proposals"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(char in "0123456789abcdef" for char in token) else ""


def _sealed(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    row = dict(record)
    row[digest_field] = _digest({key: value for key, value in row.items() if key != digest_field})
    return row


def _valid(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(
        supplied
        and supplied == _digest({key: value for key, value in record.items() if key != digest_field})
    )


def _base(
    *, proposal_id: str = "", revision: int = 0, failed_attempt: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "failed_attempt_number": int(failed_attempt or 0),
        "repair_attempt_number": 1,
        "repair_attempt_limit": 1,
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
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(
    status: str,
    *,
    reason: str = "",
    proposal_id: str = "",
    revision: int = 0,
    failed_attempt: int = 0,
) -> dict[str, Any]:
    row = {
        "ok": False,
        "status": str(status or "operator_repair_result_review_blocked"),
        "reason": str(reason or ""),
        **_base(
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        ),
    }
    row["operator_repair_result_review_result_digest"] = _digest(row)
    return row


def _review_phrase(
    decision: str,
    review_digest: str,
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    repair_attempt: int = 1,
) -> str:
    return (
        f"Record {decision} for repair result review {review_digest} proposal {proposal_id} "
        f"revision {int(revision)} failed attempt {int(failed_attempt)} repair attempt "
        f"{int(repair_attempt)}."
    )


def _apply_authorization_phrase(
    apply_proposal_digest: str,
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    repair_attempt: int = 1,
) -> str:
    return (
        f"Authorize repaired candidate apply proposal {apply_proposal_digest} proposal "
        f"{proposal_id} revision {int(revision)} failed attempt {int(failed_attempt)} "
        f"repair attempt {int(repair_attempt)}."
    )


def _validated_repair_result(
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    expected_execution_digest: str,
    expected_result_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    record = load_conversational_supervised_repair_execution(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    if not record or record.get("phase") != "sealed":
        return None, _failure(
            "operator_repair_result_review_repair_invalid",
            reason="sealed_repair_result_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    result = record.get("result")
    if not isinstance(result, Mapping) or str(record.get("result_digest") or "") != _digest(result):
        return None, _failure(
            "operator_repair_result_review_repair_invalid",
            reason="sealed_repair_result_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    calculated = _digest({
        key: value for key, value in result.items() if key != "supervised_repair_result_digest"
    })
    if _sha256(result.get("supervised_repair_result_digest")) != calculated:
        return None, _failure(
            "operator_repair_result_review_repair_invalid",
            reason="repair_result_digest_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if str(result.get("status") or "") not in REPAIR_RESULT_STATUSES:
        return None, _failure(
            "operator_repair_result_review_not_available",
            reason="terminal_repair_result_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if (
        int(result.get("proposal_revision") or 0) != int(revision)
        or int(result.get("failed_attempt_number") or 0) != int(failed_attempt)
        or int(result.get("repair_attempt_number") or 0) != 1
        or int(result.get("repair_attempt_limit") or 0) != 1
        or result.get("repair_result_review_required") is not True
        or result.get("project_modified") is not False
        or result.get("selected_project_modified") is not False
        or result.get("source_modified") is not False
        or result.get("apply_authorized") is not False
        or result.get("authority_granted") is not False
    ):
        return None, _failure(
            "operator_repair_result_review_repair_invalid",
            reason="repair_authority_or_attempt_boundary_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    required = (
        "supervised_repair_execution_digest",
        "supervised_repair_result_digest",
        "repair_proposal_digest",
        "source_workspace_digest",
    )
    if not all(_sha256(result.get(key)) for key in required):
        return None, _failure(
            "operator_repair_result_review_repair_invalid",
            reason="exact_repair_binding_missing",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if _sha256(result.get("supervised_repair_execution_digest")) != _sha256(expected_execution_digest):
        return None, _failure(
            "operator_repair_result_review_stale_execution",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if calculated != _sha256(expected_result_digest):
        return None, _failure(
            "operator_repair_result_review_stale_result",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    passing = str(result.get("status") or "") == PASSING_REPAIR_STATUS
    if passing and (
        result.get("ok") is not True
        or result.get("test_passed") is not True
        or result.get("cleanup_confirmed") is not True
        or result.get("patch_generated") is not True
        or not _sha256(result.get("repair_workspace_digest"))
        or not _sha256(result.get("repair_loop_result_digest"))
    ):
        return None, _failure(
            "operator_repair_result_review_repair_invalid",
            reason="passing_repair_evidence_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    return dict(result), None


def prepare_operator_repair_result_review(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_execution_digest: str,
    expected_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one exact, non-executing review packet for a repair result."""

    proposal_id = str(proposal_id or "").strip().lower()
    result, failure = _validated_repair_result(
        proposal_id,
        expected_revision,
        expected_failed_attempt_number,
        expected_execution_digest,
        expected_result_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert result is not None
    passing = str(result.get("status") or "") == PASSING_REPAIR_STATUS
    decisions = PASSING_REVIEW_DECISIONS if passing else BASE_REVIEW_DECISIONS
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "failed_attempt_number": int(expected_failed_attempt_number),
        "repair_attempt_number": 1,
        "supervised_repair_execution_digest": _sha256(result.get("supervised_repair_execution_digest")),
        "supervised_repair_result_digest": _sha256(result.get("supervised_repair_result_digest")),
        "repair_proposal_digest": _sha256(result.get("repair_proposal_digest")),
        "source_workspace_digest": _sha256(result.get("source_workspace_digest")),
        "repair_workspace_digest": _sha256(result.get("repair_workspace_digest")),
        "repair_loop_result_digest": _sha256(result.get("repair_loop_result_digest")),
        "repair_result_status": str(result.get("status") or ""),
    }
    review_digest = _digest(binding)
    row = {
        "ok": True,
        "status": "operator_repair_result_review_required",
        **binding,
        "review_digest": review_digest,
        "repair_passed": passing,
        "candidate_apply_eligible": passing,
        "test_passed": result.get("test_passed") if isinstance(result.get("test_passed"), bool) else None,
        "cleanup_confirmed": result.get("cleanup_confirmed") if isinstance(result.get("cleanup_confirmed"), bool) else None,
        "available_decisions": list(decisions),
        "decision_phrases": [
            _review_phrase(
                decision,
                review_digest,
                proposal_id,
                expected_revision,
                expected_failed_attempt_number,
            )
            for decision in decisions
        ],
        **_base(
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        ),
    }
    row = _sealed(row, "operator_repair_result_review_record_digest")
    path = _review_path(
        proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
    )
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_repair_result_review_record_digest"):
                return _failure(
                    "operator_repair_result_review_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("review_digest") or "") != review_digest:
                return _failure(
                    "operator_repair_result_review_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def record_operator_repair_result_decision(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_review_digest: str,
    decision: str,
    decision_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Record one exact repair-result disposition without applying anything."""

    proposal_id = str(proposal_id or "").strip().lower()
    decision = str(decision or "").strip().lower()
    path = _review_path(
        proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
    )
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(path)
        if not review or not _valid(review, "operator_repair_result_review_record_digest"):
            return _failure(
                "operator_repair_result_review_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "operator_repair_result_decision_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        available = tuple(str(value) for value in review.get("available_decisions") or [])
        if decision not in available:
            return _failure(
                "operator_repair_result_decision_not_allowed",
                reason="passing_candidate_required" if decision == "propose-apply" else "decision_unavailable",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        expected_phrase = _review_phrase(
            decision,
            expected_review_digest,
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
        )
        if str(decision_phrase or "").strip().casefold() != expected_phrase.casefold():
            return _failure(
                "operator_repair_result_exact_decision_required",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        decision_path = _decision_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        )
        existing = _read_json(decision_path)
        if existing:
            if not _valid(existing, "operator_repair_result_decision_record_digest"):
                return _failure(
                    "operator_repair_result_decision_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("review_digest") or "") != expected_review_digest:
                return _failure(
                    "operator_repair_result_decision_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("decision") or "") != decision:
                return _failure(
                    "operator_repair_result_conflicting_decision",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        state = {
            "accept-repair-result": "repair_result_accepted",
            "defer": "repair_result_deferred",
            "reject-repair": "repair_rejected",
            "propose-apply": "apply_proposal_requested",
        }[decision]
        row = {
            "ok": True,
            "status": "operator_repair_result_decision_recorded",
            "review_digest": expected_review_digest,
            "supervised_repair_execution_digest": str(review.get("supervised_repair_execution_digest") or ""),
            "supervised_repair_result_digest": str(review.get("supervised_repair_result_digest") or ""),
            "repair_workspace_digest": str(review.get("repair_workspace_digest") or ""),
            "repair_result_status": str(review.get("repair_result_status") or ""),
            "candidate_apply_eligible": bool(review.get("candidate_apply_eligible")),
            "decision": decision,
            "decision_state": state,
            "apply_proposal_requested": decision == "propose-apply",
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            ),
        }
        row["operator_repair_result_decision_digest"] = _digest(row)
        row = _sealed(row, "operator_repair_result_decision_record_digest")
        _atomic_json(decision_path, row)
    return {**row, "operation_status": "created"}


def prepare_bounded_repaired_candidate_apply_proposal(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_review_digest: str,
    expected_decision_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one separately gated apply proposal; never execute the apply."""

    proposal_id = str(proposal_id or "").strip().lower()
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(_review_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        ))
        decision = _read_json(_decision_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        ))
        if not review or not _valid(review, "operator_repair_result_review_record_digest"):
            return _failure(
                "bounded_apply_proposal_review_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if not decision or not _valid(decision, "operator_repair_result_decision_record_digest"):
            return _failure(
                "bounded_apply_proposal_decision_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "bounded_apply_proposal_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(decision.get("operator_repair_result_decision_digest") or "") != _sha256(expected_decision_digest):
            return _failure(
                "bounded_apply_proposal_stale_decision",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if (
            str(decision.get("review_digest") or "") != str(review.get("review_digest") or "")
            or decision.get("decision") != "propose-apply"
            or decision.get("apply_proposal_requested") is not True
            or review.get("candidate_apply_eligible") is not True
            or review.get("repair_passed") is not True
            or review.get("repair_result_status") != PASSING_REPAIR_STATUS
            or not _sha256(review.get("repair_workspace_digest"))
        ):
            return _failure(
                "bounded_apply_proposal_not_eligible",
                reason="passing_reviewed_candidate_required",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        binding = {
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "failed_attempt_number": int(expected_failed_attempt_number),
            "repair_attempt_number": 1,
            "supervised_repair_execution_digest": str(review.get("supervised_repair_execution_digest") or ""),
            "supervised_repair_result_digest": str(review.get("supervised_repair_result_digest") or ""),
            "repair_proposal_digest": str(review.get("repair_proposal_digest") or ""),
            "source_workspace_digest": str(review.get("source_workspace_digest") or ""),
            "repair_workspace_digest": str(review.get("repair_workspace_digest") or ""),
            "repair_loop_result_digest": str(review.get("repair_loop_result_digest") or ""),
            "review_digest": str(review.get("review_digest") or ""),
            "operator_repair_result_decision_digest": str(decision.get("operator_repair_result_decision_digest") or ""),
        }
        apply_digest = _digest(binding)
        row = {
            "ok": True,
            "status": "bounded_repaired_candidate_apply_proposal_authorization_required",
            **binding,
            "apply_proposal_digest": apply_digest,
            "apply_scope": "one_selected_project_apply_attempt",
            "apply_target": "exact_isolated_repaired_candidate",
            "maximum_apply_attempts": 1,
            "requires_exact_authorization": True,
            "authorization_phrase": _apply_authorization_phrase(
                apply_digest,
                proposal_id,
                expected_revision,
                expected_failed_attempt_number,
            ),
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            ),
            "apply_proposal_created": True,
            "apply_authorization_required": True,
        }
        row = _sealed(row, "bounded_repaired_candidate_apply_proposal_record_digest")
        path = _apply_proposal_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        )
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "bounded_repaired_candidate_apply_proposal_record_digest"):
                return _failure(
                    "bounded_apply_proposal_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("apply_proposal_digest") or "") != apply_digest:
                return _failure(
                    "bounded_apply_proposal_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def public_operator_repair_result_review(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "failed_attempt_number", "repair_attempt_number",
        "repair_attempt_limit", "supervised_repair_execution_digest",
        "supervised_repair_result_digest", "repair_proposal_digest",
        "source_workspace_digest", "repair_workspace_digest", "repair_loop_result_digest",
        "repair_result_status", "review_digest", "repair_passed", "candidate_apply_eligible",
        "test_passed", "cleanup_confirmed", "available_decisions", "decision_phrases",
        "operator_repair_result_review_record_digest", "decision", "decision_state",
        "apply_proposal_requested", "operator_repair_result_decision_digest",
        "operator_repair_result_decision_record_digest", "apply_proposal_digest",
        "apply_scope", "apply_target", "maximum_apply_attempts",
        "requires_exact_authorization", "authorization_phrase",
        "bounded_repaired_candidate_apply_proposal_record_digest", "operation_status",
        "operator_review_required", "repair_result_review_required",
        "apply_proposal_created", "apply_authorization_required", "runtime_records_external",
        "provider_contacted", "tests_executed", "retest_executed", "patch_generated",
        "repair_executed", "project_modified", "selected_project_modified", "source_modified",
        "repair_execution_authorized", "provider_contact_authorized",
        "test_execution_authorized", "retest_authorized", "apply_authorized",
        "rollback_authorized", "install_authorized", "promotion_authorized",
        "release_authorized", "model_management_authorized", "authority_granted",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "content_free": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    public["public_operator_repair_result_review_digest"] = _digest(public)
    return public


def operator_repair_result_review_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "operator_repair_result_review_required":
        phrases = list(record.get("decision_phrases") or [])
        choices = " ".join(f"[{phrase}]" for phrase in phrases)
        eligibility = (
            "The passing repaired candidate is eligible for a separately gated apply proposal."
            if record.get("candidate_apply_eligible") is True
            else "This result is not eligible for an apply proposal."
        )
        return (
            f"The exact supervised repair result is ready for operator review. {eligibility} "
            f"Nothing has been applied. Choose one exact disposition: {choices}"
        )
    if status == "operator_repair_result_decision_recorded":
        return (
            f"The repair-result decision {record.get('decision', '')} was recorded exactly once. "
            "No candidate was applied and no installation, promotion, or release was authorized."
        )
    if status == "bounded_repaired_candidate_apply_proposal_authorization_required":
        return (
            "One exact repaired-candidate apply proposal is prepared, but no apply has run. "
            f"A later supervised apply stage requires this separate phrase: {record.get('authorization_phrase', '')}"
        )
    if status == "operator_repair_result_conflicting_decision":
        return "A different repair-result disposition is already sealed, so this conflicting decision was rejected."
    return (
        "The repair-result review control was rejected because its exact evidence binding was invalid. "
        "No apply, rollback, installation, promotion, or release action was authorized."
    )


def attach_operator_repair_result_review(
    repair_turn: Mapping[str, Any], *, runtime_root=None
) -> dict[str, Any]:
    turn = dict(repair_turn)
    public_repair = turn.get("supervised_repair_execution")
    if not isinstance(public_repair, Mapping):
        return turn
    if str(public_repair.get("status") or "") not in REPAIR_RESULT_STATUSES:
        return turn
    try:
        review = prepare_operator_repair_result_review(
            str(public_repair.get("proposal_id") or ""),
            expected_revision=int(public_repair.get("proposal_revision") or 0),
            expected_failed_attempt_number=int(public_repair.get("failed_attempt_number") or 0),
            expected_execution_digest=str(public_repair.get("supervised_repair_execution_digest") or ""),
            expected_result_digest=str(public_repair.get("supervised_repair_result_digest") or ""),
            runtime_root=runtime_root,
        )
        turn["operator_repair_result_review"] = public_operator_repair_result_review(review)
        if review.get("ok") is True:
            turn["conversation_response"] = " ".join(
                part for part in (
                    str(turn.get("conversation_response") or "").strip(),
                    operator_repair_result_review_response(review),
                ) if part
            )
    except Exception as error:
        turn["operator_repair_result_review"] = {
            "ok": False,
            "status": "operator_repair_result_review_preparation_blocked",
            "reason_digest": _digest({"type": type(error).__name__}),
            "content_free": True,
            "apply_authorized": False,
            "authority_granted": False,
        }
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items()
        if key not in {"conversation_response", "public_digest"}
    })
    return turn


def process_operator_repair_result_review_control(
    user_text: str, *, runtime_root=None
) -> dict[str, Any]:
    match = _REVIEW_DECISION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    failed_attempt = int(match.group("failed_attempt"))
    repair_attempt = int(match.group("repair_attempt"))
    if repair_attempt != 1:
        result = _failure(
            "operator_repair_result_decision_not_allowed",
            reason="repair_attempt_limit_exceeded",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    else:
        result = record_operator_repair_result_decision(
            proposal_id,
            expected_revision=revision,
            expected_failed_attempt_number=failed_attempt,
            expected_review_digest=match.group("review_digest").lower(),
            decision=match.group("decision").lower(),
            decision_phrase=str(user_text or "").strip(),
            runtime_root=runtime_root,
        )
    public = public_operator_repair_result_review(result)
    turn = {
        "active": True,
        "event": str(result.get("status") or "operator_repair_result_review_control_blocked"),
        "operator_repair_result_review": public,
        "conversation_response": operator_repair_result_review_response(result),
        "public_digest": _digest(public),
    }
    if result.get("ok") is True and result.get("decision") == "propose-apply":
        try:
            apply_proposal = prepare_bounded_repaired_candidate_apply_proposal(
                proposal_id,
                expected_revision=revision,
                expected_failed_attempt_number=failed_attempt,
                expected_review_digest=str(result.get("review_digest") or ""),
                expected_decision_digest=str(result.get("operator_repair_result_decision_digest") or ""),
                runtime_root=runtime_root,
            )
            turn["bounded_repaired_candidate_apply_proposal"] = public_operator_repair_result_review(
                apply_proposal
            )
            turn["conversation_response"] = operator_repair_result_review_response(apply_proposal)
        except Exception as error:
            turn["bounded_repaired_candidate_apply_proposal"] = {
                "ok": False,
                "status": "bounded_apply_proposal_preparation_blocked",
                "reason_digest": _digest({"type": type(error).__name__}),
                "content_free": True,
                "apply_authorized": False,
                "authority_granted": False,
            }
            turn["conversation_response"] = (
                "The apply proposal could not be prepared. No project change was authorized."
            )
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items()
        if key not in {"conversation_response", "public_digest"}
    })
    return turn


def load_operator_repair_result_review(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_review_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(record, "operator_repair_result_review_record_digest") else {}


def load_operator_repair_result_decision(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_decision_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(record, "operator_repair_result_decision_record_digest") else {}


def load_bounded_repaired_candidate_apply_proposal(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_apply_proposal_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return (
        record
        if record and _valid(record, "bounded_repaired_candidate_apply_proposal_record_digest")
        else {}
    )
