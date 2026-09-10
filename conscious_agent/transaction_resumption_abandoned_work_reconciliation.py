from __future__ import annotations

"""Bounded transaction resumption and abandoned-work reconciliation.

v1222 derives one content-free resumption assessment from the exact current
v1221 transaction-history generation.  The assessment can be reviewed through
an exact ordinary-chat decision.  A resume-oriented decision may prepare one
new approval-gated continuation proposal, but this module never reuses an old
approval, consumes the new approval, executes work, contacts a provider, runs
commands, mutates a project, or grants authority.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)
from unified_supervised_development_transaction_history import (
    build_unified_supervised_development_transaction_history,
    load_unified_supervised_development_transaction_history,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1222.8"
ASSESSMENT_CLASSES = (
    "safely_resumable",
    "restart_required",
    "review_required",
    "permanently_closed",
)
RESUMPTION_DECISIONS = (
    "resume-planning",
    "begin-fresh-attempt",
    "defer",
    "close-as-abandoned",
    "investigate-inconsistency",
)
AUTHORITY_FLAGS = {
    "prior_approval_reusable": False,
    "prior_authorization_reusable": False,
    "continuation_execution_authorized": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "repair_execution_authorized": False,
    "apply_execution_authorized": False,
    "rollback_execution_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}

_ASSESS_CONTROL = re.compile(
    r"^assess\s+(?:unified\s+)?supervised\s+development\s+transaction\s+"
    r"resumption\s+proposal\s+(?P<proposal_id>devc_[a-f0-9]{24})\s+"
    r"revision\s+(?P<revision>[1-9][0-9]*)[.!?]*$",
    re.I,
)
_DECISION_CONTROL = re.compile(
    r"^record\s+(?P<decision>resume-planning|begin-fresh-attempt|defer|"
    r"close-as-abandoned|investigate-inconsistency)\s+for\s+transaction\s+"
    r"resumption\s+assessment\s+(?P<assessment_digest>[a-f0-9]{64})\s+"
    r"history\s+(?P<history_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+"
    r"(?P<revision>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _assessment_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "transaction_resumption_assessments"
        / proposal_id
        / f"revision-{int(revision)}.json"
    )


def _assessment_snapshot_path(
    proposal_id: str, revision: int, generation: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "transaction_resumption_assessment_snapshots"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"generation-{int(generation):06d}.json"
    )


def _decision_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "transaction_resumption_decisions"
        / proposal_id
        / f"revision-{int(revision)}.json"
    )


def _continuation_proposal_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "transaction_resumption_continuation_proposals"
        / proposal_id
        / f"revision-{int(revision)}.json"
    )


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(
        supplied
        and supplied
        == _digest({key: value for key, value in record.items() if key != field})
    )


def _base(proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "content_free": True,
        "operator_review_required": True,
        "runtime_records_external": True,
        "history_is_derivative": True,
        "authoritative_receipts_preserved": True,
        "old_authority_reuse_forbidden": True,
        "new_approval_required_before_continuation": True,
        "provider_contacted": False,
        "tests_executed": False,
        "continuation_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(
    status: str, *, reason: str = "", proposal_id: str = "", revision: int = 0
) -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base(proposal_id, revision)}
    row["transaction_resumption_result_digest"] = _digest(row)
    return row


def _decision_phrase(
    decision: str,
    assessment_digest: str,
    history_digest: str,
    proposal_id: str,
    revision: int,
) -> str:
    return (
        f"Record {decision} for transaction resumption assessment {assessment_digest} "
        f"history {history_digest} proposal {proposal_id} revision {int(revision)}."
    )


def classify_transaction_history(history: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one already-validated content-free history without side effects."""

    events = [dict(row) for row in (history.get("events") or []) if isinstance(row, Mapping)]
    if not events:
        return {
            "classification": "review_required",
            "last_trustworthy_stage": "",
            "safe_resumption_boundary": "none",
            "reason_codes": ["no_history_events"],
            "eligible_decisions": ["investigate-inconsistency", "defer"],
            "consumed_authority_event_count": 0,
            "inconsistency_detected": True,
            "unfinished_work_detected": False,
        }
    last = events[-1]
    stage = str(last.get("stage") or "")
    status = str(last.get("status") or "").lower()
    decision = str(last.get("operator_decision") or "").lower()
    decision_state = str(last.get("decision_state") or "").lower()
    gaps = int(history.get("gap_count") or 0)
    consumed = sum(1 for row in events if row.get("authority_consumed") is True)
    last_consumed = last.get("authority_consumed") is True
    terminal = history.get("terminal") is True
    closed_token = any(token in f"{status} {decision} {decision_state}" for token in (
        "accepted", "rejected", "cancelled", "closed", "discarded",
    ))
    deferred = "defer" in f"{status} {decision} {decision_state}"
    interrupted = any(token in status for token in ("interrupted", "incomplete", "timed_out"))
    blocked_or_failed = any(token in status for token in ("blocked", "failed", "error"))

    if terminal or (closed_token and not deferred):
        classification = "permanently_closed"
        reasons = ["terminal_or_closed_disposition"]
        decisions: list[str] = []
        boundary = "closed"
        unfinished = False
    elif gaps:
        classification = "review_required"
        reasons = ["history_has_missing_intermediate_stages"]
        decisions = ["investigate-inconsistency", "defer", "close-as-abandoned"]
        boundary = "last_gap_free_authoritative_receipt"
        unfinished = True
    elif interrupted and last_consumed:
        classification = "restart_required"
        reasons = ["interrupted_after_authority_consumption", "old_authority_cannot_be_reused"]
        decisions = ["begin-fresh-attempt", "defer", "close-as-abandoned", "investigate-inconsistency"]
        boundary = stage
        unfinished = True
    elif stage.endswith("review") or stage.endswith("decision") or deferred:
        classification = "review_required"
        reasons = ["operator_disposition_or_fresh_authority_required"]
        decisions = ["resume-planning", "begin-fresh-attempt", "defer", "close-as-abandoned"]
        boundary = stage
        unfinished = True
    elif last_consumed or blocked_or_failed:
        classification = "restart_required"
        reasons = ["consumed_or_failed_attempt_requires_fresh_authority"]
        decisions = ["begin-fresh-attempt", "defer", "close-as-abandoned", "investigate-inconsistency"]
        boundary = stage
        unfinished = True
    else:
        classification = "safely_resumable"
        reasons = ["authoritative_history_has_safe_review_boundary"]
        decisions = ["resume-planning", "begin-fresh-attempt", "defer", "close-as-abandoned"]
        boundary = stage
        unfinished = True

    return {
        "classification": classification,
        "last_trustworthy_stage": stage,
        "safe_resumption_boundary": boundary,
        "reason_codes": reasons,
        "eligible_decisions": decisions,
        "consumed_authority_event_count": consumed,
        "inconsistency_detected": bool(gaps),
        "unfinished_work_detected": unfinished,
    }


def _validate_assessment(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "transaction_resumption_assessment_record_digest"):
        return False
    phrases = record.get("decision_phrases")
    if not isinstance(phrases, list):
        return False
    expected = [
        _decision_phrase(
            decision,
            str(record.get("assessment_digest") or ""),
            str(record.get("history_digest") or ""),
            str(record.get("proposal_id") or ""),
            int(record.get("proposal_revision") or 0),
        )
        for decision in record.get("eligible_decisions") or []
    ]
    return phrases == expected


def build_transaction_resumption_assessment(
    proposal_id: str, *, expected_revision: int, runtime_root=None
) -> dict[str, Any]:
    proposal_id = str(proposal_id or "").strip().lower()
    revision = int(expected_revision or 0)
    if not re.fullmatch(r"devc_[a-f0-9]{24}", proposal_id) or revision < 1:
        return _failure(
            "transaction_resumption_assessment_invalid_request",
            reason="valid_proposal_and_revision_required",
            proposal_id=proposal_id,
            revision=revision,
        )
    history = build_unified_supervised_development_transaction_history(
        proposal_id, expected_revision=revision, runtime_root=runtime_root
    )
    if history.get("ok") is not True:
        return _failure(
            "transaction_resumption_assessment_history_blocked",
            reason=str(history.get("status") or "history_unavailable"),
            proposal_id=proposal_id,
            revision=revision,
        )
    classification = classify_transaction_history(history)
    path = _assessment_path(proposal_id, revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _validate_assessment(existing):
                return _failure(
                    "transaction_resumption_assessment_record_invalid",
                    reason="persisted_assessment_tampered_or_malformed",
                    proposal_id=proposal_id,
                    revision=revision,
                )
            if str(existing.get("history_digest") or "") == str(history.get("history_digest") or ""):
                return {**existing, "operation_status": "resumed"}
            generation = int(existing.get("assessment_generation") or 0) + 1
            previous_assessment_digest = str(existing.get("assessment_digest") or "")
        else:
            generation = 1
            previous_assessment_digest = ""
        binding = {
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_revision": revision,
            "assessment_generation": generation,
            "previous_assessment_digest": previous_assessment_digest,
            "history_generation": int(history.get("generation") or 0),
            "history_digest": str(history.get("history_digest") or ""),
            "history_source_set_digest": str(history.get("source_set_digest") or ""),
            "classification": classification["classification"],
            "last_trustworthy_stage": classification["last_trustworthy_stage"],
            "safe_resumption_boundary": classification["safe_resumption_boundary"],
            "reason_codes": classification["reason_codes"],
            "eligible_decisions": classification["eligible_decisions"],
        }
        assessment_digest = _digest(binding)
        row = {
            "ok": True,
            "status": "transaction_resumption_assessment_ready",
            **binding,
            "assessment_digest": assessment_digest,
            "decision_phrases": [
                _decision_phrase(decision, assessment_digest, binding["history_digest"], proposal_id, revision)
                for decision in classification["eligible_decisions"]
            ],
            "history_event_count": int(history.get("event_count") or 0),
            "history_stage_count": int(history.get("stage_count") or 0),
            "history_gap_count": int(history.get("gap_count") or 0),
            "history_current_state": str(history.get("current_state") or ""),
            "history_terminal": bool(history.get("terminal")),
            **classification,
            **_base(proposal_id, revision),
        }
        row = _sealed(row, "transaction_resumption_assessment_record_digest")
        _atomic_json(_assessment_snapshot_path(proposal_id, revision, generation, runtime_root), row)
        _atomic_json(path, row)
    return {**row, "operation_status": "created" if generation == 1 else "refreshed"}


def _prepare_continuation_proposal(
    assessment: Mapping[str, Any], decision: str, runtime_root=None
) -> dict[str, Any]:
    proposal_id = str(assessment.get("proposal_id") or "")
    revision = int(assessment.get("proposal_revision") or 0)
    path = _continuation_proposal_path(proposal_id, revision, runtime_root)
    existing = _read_json(path)
    if existing:
        if not _valid(existing, "transaction_resumption_continuation_proposal_record_digest"):
            return _failure(
                "transaction_resumption_continuation_proposal_invalid",
                reason="persisted_continuation_proposal_tampered",
                proposal_id=proposal_id,
                revision=revision,
            )
        if (
            str(existing.get("assessment_digest") or "") == str(assessment.get("assessment_digest") or "")
            and str(existing.get("requested_mode") or "") == decision
        ):
            return {**existing, "operation_status": "resumed"}
        return _failure(
            "transaction_resumption_continuation_proposal_conflict",
            reason="different_continuation_proposal_already_sealed",
            proposal_id=proposal_id,
            revision=revision,
        )
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": revision,
        "requested_mode": decision,
        "assessment_digest": str(assessment.get("assessment_digest") or ""),
        "history_digest": str(assessment.get("history_digest") or ""),
        "history_generation": int(assessment.get("history_generation") or 0),
        "safe_resumption_boundary": str(assessment.get("safe_resumption_boundary") or ""),
        "fresh_authority_required": True,
        "prior_authority_reusable": False,
    }
    proposal_digest = _digest(binding)
    row = {
        "ok": True,
        "status": "transaction_resumption_continuation_proposal_ready",
        **binding,
        "continuation_proposal_digest": proposal_digest,
        "approval_phrase": (
            f"Approve transaction resumption proposal {proposal_digest} proposal "
            f"{proposal_id} revision {revision}."
        ),
        "approval_consumed": False,
        "continuation_executed": False,
        **_base(proposal_id, revision),
    }
    row = _sealed(row, "transaction_resumption_continuation_proposal_record_digest")
    _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def record_transaction_resumption_decision(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_assessment_digest: str,
    expected_history_digest: str,
    decision: str,
    decision_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    proposal_id = str(proposal_id or "").strip().lower()
    revision = int(expected_revision or 0)
    decision = str(decision or "").strip().lower()
    assessment = _read_json(_assessment_path(proposal_id, revision, runtime_root)) or {}
    if not assessment or not _validate_assessment(assessment):
        return _failure(
            "transaction_resumption_decision_assessment_invalid",
            reason="valid_current_assessment_required",
            proposal_id=proposal_id,
            revision=revision,
        )
    current_history = load_unified_supervised_development_transaction_history(
        proposal_id, revision, runtime_root=runtime_root
    )
    if (
        str(assessment.get("assessment_digest") or "") != str(expected_assessment_digest or "").lower()
        or str(assessment.get("history_digest") or "") != str(expected_history_digest or "").lower()
        or str((current_history or {}).get("history_digest") or "") != str(expected_history_digest or "").lower()
    ):
        return _failure(
            "transaction_resumption_decision_stale_or_mismatched",
            reason="assessment_or_history_binding_mismatch",
            proposal_id=proposal_id,
            revision=revision,
        )
    eligible = list(assessment.get("eligible_decisions") or [])
    if decision not in eligible:
        return _failure(
            "transaction_resumption_decision_not_allowed",
            reason="decision_not_eligible_for_assessment",
            proposal_id=proposal_id,
            revision=revision,
        )
    expected_phrase = _decision_phrase(
        decision,
        str(assessment.get("assessment_digest") or ""),
        str(assessment.get("history_digest") or ""),
        proposal_id,
        revision,
    )
    if str(decision_phrase or "").strip() != expected_phrase:
        return _failure(
            "transaction_resumption_decision_phrase_invalid",
            reason="exact_decision_phrase_required",
            proposal_id=proposal_id,
            revision=revision,
        )
    path = _decision_path(proposal_id, revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "transaction_resumption_decision_record_digest"):
                return _failure(
                    "transaction_resumption_decision_record_invalid",
                    reason="persisted_decision_tampered",
                    proposal_id=proposal_id,
                    revision=revision,
                )
            if (
                str(existing.get("assessment_digest") or "") == str(assessment.get("assessment_digest") or "")
                and str(existing.get("decision") or "") == decision
            ):
                output = {**existing, "operation_status": "resumed"}
                continuation = _read_json(_continuation_proposal_path(proposal_id, revision, runtime_root)) or {}
                if continuation:
                    output["continuation_proposal"] = continuation
                return output
            return _failure(
                "transaction_resumption_conflicting_decision",
                reason="different_decision_already_sealed",
                proposal_id=proposal_id,
                revision=revision,
            )
        state = {
            "resume-planning": "resumption_planning_proposed",
            "begin-fresh-attempt": "fresh_attempt_proposed",
            "defer": "resumption_deferred",
            "close-as-abandoned": "abandoned_closed",
            "investigate-inconsistency": "inconsistency_investigation_required",
        }[decision]
        row = {
            "ok": True,
            "status": "transaction_resumption_decision_recorded",
            "decision": decision,
            "decision_state": state,
            "assessment_digest": str(assessment.get("assessment_digest") or ""),
            "assessment_generation": int(assessment.get("assessment_generation") or 0),
            "history_digest": str(assessment.get("history_digest") or ""),
            "history_generation": int(assessment.get("history_generation") or 0),
            "classification": str(assessment.get("classification") or ""),
            "safe_resumption_boundary": str(assessment.get("safe_resumption_boundary") or ""),
            **_base(proposal_id, revision),
        }
        row["transaction_resumption_decision_digest"] = _digest(row)
        row = _sealed(row, "transaction_resumption_decision_record_digest")
        _atomic_json(path, row)
        continuation = {}
        if decision in {"resume-planning", "begin-fresh-attempt"}:
            continuation = _prepare_continuation_proposal(assessment, decision, runtime_root)
        output = {**row, "operation_status": "created"}
        if continuation:
            output["continuation_proposal"] = continuation
        return output


def public_transaction_resumption(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "status", "reason", "schema_version", "contract_version", "proposal_id",
        "proposal_revision", "assessment_generation", "previous_assessment_digest",
        "history_generation", "history_digest", "history_source_set_digest",
        "classification", "last_trustworthy_stage", "safe_resumption_boundary",
        "reason_codes", "eligible_decisions", "assessment_digest", "decision_phrases",
        "history_event_count", "history_stage_count", "history_gap_count",
        "history_current_state", "history_terminal", "consumed_authority_event_count",
        "inconsistency_detected", "unfinished_work_detected", "decision", "decision_state",
        "transaction_resumption_decision_digest", "operation_status", "content_free",
        "operator_review_required", "runtime_records_external", "history_is_derivative",
        "authoritative_receipts_preserved", "old_authority_reuse_forbidden",
        "new_approval_required_before_continuation", "provider_contacted", "tests_executed",
        "continuation_executed", "repair_executed", "apply_executed", "rollback_executed",
        "project_modified", "selected_project_modified", "source_modified", *AUTHORITY_FLAGS.keys(),
    }
    public = {key: record.get(key) for key in allowed if key in record}
    continuation = record.get("continuation_proposal")
    if isinstance(continuation, Mapping):
        continuation_allowed = {
            "ok", "status", "contract_version", "proposal_id", "proposal_revision",
            "requested_mode", "assessment_digest", "history_digest", "history_generation",
            "safe_resumption_boundary", "fresh_authority_required", "prior_authority_reusable",
            "continuation_proposal_digest", "approval_phrase", "approval_consumed",
            "continuation_executed", "operation_status",
        }
        public["continuation_proposal"] = {
            key: continuation.get(key) for key in continuation_allowed if key in continuation
        }
    public.update({
        "content_free": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    public["public_transaction_resumption_digest"] = _digest(public)
    return public


def transaction_resumption_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "transaction_resumption_assessment_ready":
        phrases = " ".join(f"[{phrase}]" for phrase in record.get("decision_phrases") or [])
        return (
            f"Transaction resumption assessment: {record.get('classification')}. Last trustworthy "
            f"stage: {record.get('last_trustworthy_stage') or 'none'}. Old approvals and authorizations "
            f"cannot be reused. Choose one exact operator disposition: {phrases}"
        )
    if status == "transaction_resumption_decision_recorded":
        continuation = record.get("continuation_proposal") or {}
        suffix = (
            f" A new approval-gated continuation proposal was prepared: {continuation.get('approval_phrase')}"
            if continuation else ""
        )
        return (
            f"The transaction-resumption decision {record.get('decision')} was recorded exactly once."
            f"{suffix} No continuation executed and no old authority was reused."
        )
    if status == "transaction_resumption_conflicting_decision":
        return "A different resumption disposition is already sealed, so the conflicting decision was rejected."
    return (
        "The transaction-resumption request was blocked because its exact history or assessment binding "
        "was invalid. No continuation, project change, provider work, or authority grant occurred."
    )


def process_transaction_resumption_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    assessment_match = _ASSESS_CONTROL.fullmatch(text)
    if assessment_match:
        result = build_transaction_resumption_assessment(
            assessment_match.group("proposal_id").lower(),
            expected_revision=int(assessment_match.group("revision")),
            runtime_root=runtime_root,
        )
    else:
        decision_match = _DECISION_CONTROL.fullmatch(text)
        if not decision_match:
            return {"active": False, "event": "inactive"}
        result = record_transaction_resumption_decision(
            decision_match.group("proposal_id").lower(),
            expected_revision=int(decision_match.group("revision")),
            expected_assessment_digest=decision_match.group("assessment_digest").lower(),
            expected_history_digest=decision_match.group("history_digest").lower(),
            decision=decision_match.group("decision").lower(),
            decision_phrase=text,
            runtime_root=runtime_root,
        )
    public = public_transaction_resumption(result)
    return {
        "active": True,
        "event": str(result.get("status") or "transaction_resumption_blocked"),
        "transaction_resumption_abandoned_work_reconciliation": public,
        "conversation_response": transaction_resumption_response(public),
        "public_digest": _digest(public),
    }


def load_transaction_resumption_assessment(
    proposal_id: str, revision: int, *, runtime_root=None
) -> dict[str, Any]:
    row = _read_json(_assessment_path(proposal_id, revision, runtime_root)) or {}
    return row if row and _validate_assessment(row) else {}


def load_transaction_resumption_decision(
    proposal_id: str, revision: int, *, runtime_root=None
) -> dict[str, Any]:
    row = _read_json(_decision_path(proposal_id, revision, runtime_root)) or {}
    return row if row and _valid(row, "transaction_resumption_decision_record_digest") else {}
