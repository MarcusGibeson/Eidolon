from __future__ import annotations

"""Operator review and repair-proposal preparation for v1213 diagnoses.

One exact sealed bounded diagnosis may produce one durable, content-free
operator review packet.  An exact conversational decision may accept, defer,
reject, or propose a repair.  Proposing a repair creates a separately
authorization-gated proposal only: this module never contacts a provider,
generates a patch, runs or reruns tests, modifies a project, or grants repair
execution authority.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from bounded_automatic_diagnosis import load_bounded_automatic_diagnosis
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1214.8"

REVIEW_DECISIONS = (
    "accept-diagnosis",
    "defer",
    "reject-diagnosis",
    "propose-repair",
)

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
    r"^record\s+(?P<decision>accept-diagnosis|defer|reject-diagnosis|propose-repair)\s+"
    r"for\s+diagnosis\s+review\s+(?P<review_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)\s+"
    r"attempt\s+(?P<attempt>[2-9][0-9]*)[.!?]*$",
    re.I,
)


def _review_path(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_diagnosis_reviews"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"attempt-{int(attempt_number)}.json"
    )


def _decision_path(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_diagnosis_decisions"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"attempt-{int(attempt_number)}.json"
    )


def _repair_proposal_path(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "bounded_repair_proposals"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"attempt-{int(attempt_number)}.json"
    )


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(character in "0123456789abcdef" for character in token) else ""


def _sealed(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    row = dict(record)
    row[digest_field] = _digest({key: value for key, value in row.items() if key != digest_field})
    return row


def _valid(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != digest_field}))


def _base(*, proposal_id: str = "", revision: int = 0, attempt_number: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "attempt_number": int(attempt_number or 0),
        "operator_review_required": True,
        "repair_proposal_created": False,
        "repair_authorization_required": False,
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
    attempt_number: int = 0,
) -> dict[str, Any]:
    row = {
        "ok": False,
        "status": str(status),
        "reason": str(reason or ""),
        **_base(proposal_id=proposal_id, revision=revision, attempt_number=attempt_number),
    }
    row["operator_diagnosis_result_digest"] = _digest(row)
    return row


def _review_phrase(decision: str, review_digest: str, proposal_id: str, revision: int, attempt_number: int) -> str:
    return (
        f"Record {decision} for diagnosis review {review_digest} proposal "
        f"{proposal_id} revision {int(revision)} attempt {int(attempt_number)}."
    )


def _repair_authorization_phrase(
    repair_proposal_digest: str, proposal_id: str, revision: int, attempt_number: int
) -> str:
    return (
        f"Authorize repair proposal {repair_proposal_digest} proposal {proposal_id} "
        f"revision {int(revision)} attempt {int(attempt_number)}."
    )


def _validated_diagnosis(
    proposal_id: str,
    revision: int,
    attempt_number: int,
    expected_diagnosis_digest: str,
    expected_diagnosis_result_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    record = load_bounded_automatic_diagnosis(
        proposal_id, revision, attempt_number, runtime_root=runtime_root
    )
    if not record or record.get("phase") != "sealed":
        return None, _failure(
            "operator_diagnosis_review_diagnosis_invalid",
            reason="sealed_diagnosis_required",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    result = record.get("result")
    if not isinstance(result, Mapping) or str(record.get("result_digest") or "") != _digest(result):
        return None, _failure(
            "operator_diagnosis_review_diagnosis_invalid",
            reason="sealed_diagnosis_result_invalid",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    calculated_result_digest = _digest(
        {key: value for key, value in result.items() if key != "diagnosis_result_digest"}
    )
    if _sha256(result.get("diagnosis_result_digest")) != calculated_result_digest:
        return None, _failure(
            "operator_diagnosis_review_diagnosis_invalid",
            reason="diagnosis_result_digest_invalid",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    if str(result.get("status") or "") != "bounded_automatic_diagnosis_completed":
        return None, _failure(
            "operator_diagnosis_review_not_available",
            reason="completed_diagnosis_required",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    if _sha256(result.get("diagnosis_digest")) != _sha256(expected_diagnosis_digest):
        return None, _failure(
            "operator_diagnosis_review_stale_diagnosis",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    if calculated_result_digest != _sha256(expected_diagnosis_result_digest):
        return None, _failure(
            "operator_diagnosis_review_stale_result",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    candidates = result.get("diagnosis_candidates")
    if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], Mapping):
        return None, _failure(
            "operator_diagnosis_review_diagnosis_invalid",
            reason="one_diagnosis_candidate_required",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    required_digests = (
        "proposal_revision_digest",
        "attempt_digest",
        "continuation_result_digest",
        "evidence_digest",
        "diagnosis_digest",
        "diagnosis_result_digest",
    )
    if not all(_sha256(result.get(key)) for key in required_digests):
        return None, _failure(
            "operator_diagnosis_review_diagnosis_invalid",
            reason="exact_diagnosis_binding_missing",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    return dict(result), None


def prepare_operator_diagnosis_review(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_number: int,
    expected_diagnosis_digest: str,
    expected_diagnosis_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one exact operator review packet for a sealed diagnosis."""

    proposal_id = str(proposal_id or "").strip().lower()
    diagnosis, failure = _validated_diagnosis(
        proposal_id,
        expected_revision,
        expected_attempt_number,
        expected_diagnosis_digest,
        expected_diagnosis_result_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert diagnosis is not None
    candidate = dict(diagnosis["diagnosis_candidates"][0])
    review_binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": _sha256(diagnosis.get("proposal_revision_digest")),
        "attempt_number": int(expected_attempt_number),
        "attempt_digest": _sha256(diagnosis.get("attempt_digest")),
        "continuation_result_digest": _sha256(diagnosis.get("continuation_result_digest")),
        "evidence_digest": _sha256(diagnosis.get("evidence_digest")),
        "diagnosis_digest": _sha256(diagnosis.get("diagnosis_digest")),
        "diagnosis_result_digest": _sha256(diagnosis.get("diagnosis_result_digest")),
        "diagnosis_candidate_digest": _digest(candidate),
    }
    review_digest = _digest(review_binding)
    row = {
        "ok": True,
        "status": "operator_diagnosis_review_required",
        **review_binding,
        "review_digest": review_digest,
        "outcome_status": str(diagnosis.get("outcome_status") or ""),
        "diagnosis_code": str(candidate.get("diagnosis_code") or ""),
        "diagnosis_confidence": str(candidate.get("confidence") or ""),
        "root_cause_proven": bool(diagnosis.get("root_cause_proven")),
        "unknown_count": len(list(candidate.get("unknowns") or [])),
        "available_decisions": list(REVIEW_DECISIONS),
        "decision_phrases": [
            _review_phrase(decision, review_digest, proposal_id, expected_revision, expected_attempt_number)
            for decision in REVIEW_DECISIONS
        ],
        **_base(
            proposal_id=proposal_id,
            revision=expected_revision,
            attempt_number=expected_attempt_number,
        ),
    }
    row = _sealed(row, "operator_diagnosis_review_record_digest")
    path = _review_path(proposal_id, expected_revision, expected_attempt_number, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_diagnosis_review_record_digest"):
                return _failure(
                    "operator_diagnosis_review_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            if str(existing.get("review_digest") or "") != review_digest:
                return _failure(
                    "operator_diagnosis_review_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def record_operator_diagnosis_decision(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_number: int,
    expected_review_digest: str,
    decision: str,
    decision_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Record exactly one review decision without executing a repair."""

    proposal_id = str(proposal_id or "").strip().lower()
    decision = str(decision or "").strip().lower()
    review_path = _review_path(proposal_id, expected_revision, expected_attempt_number, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(review_path)
        if not review or not _valid(review, "operator_diagnosis_review_record_digest"):
            return _failure(
                "operator_diagnosis_review_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "operator_diagnosis_decision_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if decision not in REVIEW_DECISIONS:
            return _failure(
                "operator_diagnosis_decision_not_allowed",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        expected_phrase = _review_phrase(
            decision, expected_review_digest, proposal_id, expected_revision, expected_attempt_number
        )
        if str(decision_phrase or "").strip().casefold() != expected_phrase.casefold():
            return _failure(
                "operator_diagnosis_exact_decision_required",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        path = _decision_path(proposal_id, expected_revision, expected_attempt_number, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_diagnosis_decision_record_digest"):
                return _failure(
                    "operator_diagnosis_decision_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            if str(existing.get("review_digest") or "") != expected_review_digest:
                return _failure(
                    "operator_diagnosis_decision_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            if str(existing.get("decision") or "") != decision:
                return _failure(
                    "operator_diagnosis_conflicting_decision",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        decision_state = {
            "accept-diagnosis": "diagnosis_accepted",
            "defer": "diagnosis_deferred",
            "reject-diagnosis": "diagnosis_rejected",
            "propose-repair": "repair_proposal_requested",
        }[decision]
        row = {
            "ok": True,
            "status": "operator_diagnosis_decision_recorded",
            "review_digest": expected_review_digest,
            "diagnosis_digest": str(review.get("diagnosis_digest") or ""),
            "diagnosis_result_digest": str(review.get("diagnosis_result_digest") or ""),
            "diagnosis_candidate_digest": str(review.get("diagnosis_candidate_digest") or ""),
            "decision": decision,
            "decision_state": decision_state,
            "repair_proposal_requested": decision == "propose-repair",
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            ),
        }
        row["operator_diagnosis_decision_digest"] = _digest(row)
        row = _sealed(row, "operator_diagnosis_decision_record_digest")
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def prepare_bounded_repair_proposal(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_number: int,
    expected_review_digest: str,
    expected_decision_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Create a reviewable repair proposal; do not authorize or run it."""

    proposal_id = str(proposal_id or "").strip().lower()
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(_review_path(proposal_id, expected_revision, expected_attempt_number, runtime_root))
        decision = _read_json(_decision_path(proposal_id, expected_revision, expected_attempt_number, runtime_root))
        if not review or not _valid(review, "operator_diagnosis_review_record_digest"):
            return _failure(
                "bounded_repair_proposal_review_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if not decision or not _valid(decision, "operator_diagnosis_decision_record_digest"):
            return _failure(
                "bounded_repair_proposal_decision_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "bounded_repair_proposal_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if str(decision.get("operator_diagnosis_decision_digest") or "") != _sha256(expected_decision_digest):
            return _failure(
                "bounded_repair_proposal_stale_decision",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if str(decision.get("review_digest") or "") != expected_review_digest:
            return _failure(
                "bounded_repair_proposal_binding_changed",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if decision.get("decision") != "propose-repair" or decision.get("repair_proposal_requested") is not True:
            return _failure(
                "bounded_repair_proposal_not_requested",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        binding = {
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": str(review.get("proposal_revision_digest") or ""),
            "attempt_number": int(expected_attempt_number),
            "attempt_digest": str(review.get("attempt_digest") or ""),
            "continuation_result_digest": str(review.get("continuation_result_digest") or ""),
            "evidence_digest": str(review.get("evidence_digest") or ""),
            "diagnosis_digest": str(review.get("diagnosis_digest") or ""),
            "diagnosis_result_digest": str(review.get("diagnosis_result_digest") or ""),
            "diagnosis_candidate_digest": str(review.get("diagnosis_candidate_digest") or ""),
            "review_digest": expected_review_digest,
            "operator_diagnosis_decision_digest": expected_decision_digest,
        }
        repair_proposal_digest = _digest(binding)
        row = {
            "ok": True,
            "status": "bounded_repair_proposal_authorization_required",
            **binding,
            "repair_proposal_digest": repair_proposal_digest,
            "repair_scope": "one_bounded_isolated_attempt",
            "repair_target": "exact_failed_continuation_artifact",
            "maximum_repair_attempts": 1,
            "requires_exact_authorization": True,
            "authorization_phrase": _repair_authorization_phrase(
                repair_proposal_digest, proposal_id, expected_revision, expected_attempt_number
            ),
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            ),
            "repair_proposal_created": True,
            "repair_authorization_required": True,
        }
        row = _sealed(row, "bounded_repair_proposal_record_digest")
        path = _repair_proposal_path(proposal_id, expected_revision, expected_attempt_number, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "bounded_repair_proposal_record_digest"):
                return _failure(
                    "bounded_repair_proposal_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            if str(existing.get("repair_proposal_digest") or "") != repair_proposal_digest:
                return _failure(
                    "bounded_repair_proposal_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def public_operator_diagnosis_review(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "attempt_number", "attempt_digest",
        "continuation_result_digest", "evidence_digest", "diagnosis_digest",
        "diagnosis_result_digest", "diagnosis_candidate_digest", "review_digest",
        "operator_diagnosis_review_record_digest", "outcome_status", "diagnosis_code",
        "diagnosis_confidence", "root_cause_proven", "unknown_count", "available_decisions",
        "decision_phrases", "decision", "decision_state", "repair_proposal_requested",
        "operator_diagnosis_decision_digest", "operator_diagnosis_decision_record_digest",
        "repair_proposal_digest", "bounded_repair_proposal_record_digest", "repair_scope",
        "repair_target", "maximum_repair_attempts", "requires_exact_authorization",
        "authorization_phrase", "repair_proposal_created", "repair_authorization_required",
        "operator_review_required", "operation_status", "provider_contacted", "tests_executed",
        "retest_executed", "patch_generated", "repair_executed", "project_modified",
        "selected_project_modified", "source_modified", "runtime_records_external",
        "repair_execution_authorized", "provider_contact_authorized", "test_execution_authorized",
        "retest_authorized", "apply_authorized", "rollback_authorized", "install_authorized",
        "promotion_authorized", "release_authorized", "model_management_authorized",
        "authority_granted", "operator_diagnosis_result_digest",
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
    public["public_operator_diagnosis_digest"] = _digest(public)
    return public


def operator_diagnosis_review_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "operator_diagnosis_review_required":
        code = str(record.get("diagnosis_code") or "observed failure").replace("_", " ")
        choices = " ".join(f"Say: {phrase}" for phrase in list(record.get("decision_phrases") or []))
        return (
            f"The bounded diagnosis ({code}) is ready for your review; its root cause is not proven. "
            f"{choices}"
        ).strip()
    if status == "operator_diagnosis_decision_recorded":
        return f"The {record.get('decision', 'operator')} diagnosis decision was recorded. No repair work was started."
    if status == "bounded_repair_proposal_authorization_required":
        return (
            "A one-attempt repair proposal is ready for separate review. No patch was generated and no tests ran. "
            f"To authorize this exact proposal for the later supervised repair stage, reply: {record.get('authorization_phrase', '')}"
        ).strip()
    return (
        "The diagnosis review or repair proposal was rejected because its exact evidence binding was invalid. "
        "No repair, retest, or project change was authorized."
    )


def attach_operator_diagnosis_review(diagnosis_turn: Mapping[str, Any], *, runtime_root=None) -> dict[str, Any]:
    """Attach one operator review packet to an ordinary-chat diagnosis turn."""

    turn = dict(diagnosis_turn)
    public_diagnosis = turn.get("bounded_automatic_diagnosis")
    if not isinstance(public_diagnosis, Mapping):
        return turn
    if str(public_diagnosis.get("status") or "") != "bounded_automatic_diagnosis_completed":
        return turn
    review = prepare_operator_diagnosis_review(
        str(public_diagnosis.get("proposal_id") or ""),
        expected_revision=int(public_diagnosis.get("proposal_revision") or 0),
        expected_attempt_number=int(public_diagnosis.get("attempt_number") or 0),
        expected_diagnosis_digest=str(public_diagnosis.get("diagnosis_digest") or ""),
        expected_diagnosis_result_digest=str(public_diagnosis.get("diagnosis_result_digest") or ""),
        runtime_root=runtime_root,
    )
    turn["operator_diagnosis_review"] = public_operator_diagnosis_review(review)
    turn["conversation_response"] = " ".join(
        part for part in (
            str(turn.get("conversation_response") or "").strip(),
            operator_diagnosis_review_response(review),
        ) if part
    )
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items() if key not in {"conversation_response", "public_digest"}
    })
    return turn


def process_operator_diagnosis_review_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    match = _REVIEW_DECISION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    attempt_number = int(match.group("attempt"))
    decision = match.group("decision").lower()
    recorded = record_operator_diagnosis_decision(
        proposal_id,
        expected_revision=revision,
        expected_attempt_number=attempt_number,
        expected_review_digest=match.group("review_digest").lower(),
        decision=decision,
        decision_phrase=str(user_text or "").strip(),
        runtime_root=runtime_root,
    )
    public = public_operator_diagnosis_review(recorded)
    turn = {
        "active": True,
        "event": str(recorded.get("status") or "operator_diagnosis_review_control_blocked"),
        "operator_diagnosis_review": public,
        "conversation_response": operator_diagnosis_review_response(recorded),
        "public_digest": _digest(public),
    }
    if recorded.get("ok") is True and recorded.get("decision") == "propose-repair":
        try:
            repair = prepare_bounded_repair_proposal(
                proposal_id,
                expected_revision=revision,
                expected_attempt_number=attempt_number,
                expected_review_digest=str(recorded.get("review_digest") or ""),
                expected_decision_digest=str(recorded.get("operator_diagnosis_decision_digest") or ""),
                runtime_root=runtime_root,
            )
            turn["bounded_repair_proposal"] = public_operator_diagnosis_review(repair)
            turn["conversation_response"] = operator_diagnosis_review_response(repair)
        except Exception as error:
            turn["bounded_repair_proposal"] = {
                "ok": False,
                "status": "bounded_repair_proposal_preparation_blocked",
                "reason_digest": _digest({"type": type(error).__name__}),
                "content_free": True,
                "repair_execution_authorized": False,
                "authority_granted": False,
            }
            turn["conversation_response"] = (
                "The repair proposal could not be prepared. No repair, retest, or project change was authorized."
            )
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items() if key not in {"conversation_response", "public_digest"}
    })
    return turn


def load_operator_diagnosis_review(
    proposal_id: str, revision: int, attempt_number: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_review_path(proposal_id, revision, attempt_number, runtime_root)) or {}
    return record if record and _valid(record, "operator_diagnosis_review_record_digest") else {}


def load_operator_diagnosis_decision(
    proposal_id: str, revision: int, attempt_number: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_decision_path(proposal_id, revision, attempt_number, runtime_root)) or {}
    return record if record and _valid(record, "operator_diagnosis_decision_record_digest") else {}


def load_bounded_repair_proposal(
    proposal_id: str, revision: int, attempt_number: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_repair_proposal_path(proposal_id, revision, attempt_number, runtime_root)) or {}
    return record if record and _valid(record, "bounded_repair_proposal_record_digest") else {}
