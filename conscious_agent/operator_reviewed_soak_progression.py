from __future__ import annotations

"""Content-free v1195.5 operator-reviewed soak progression.

Reviews can approve, reject, or defer presentation-only continuation, pause,
resume, interruption, restart, and terminal interval dispositions. They never
start, pause, resume, cancel, recover, or otherwise execute a soak.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1195.5"
DECISIONS = ("approve", "reject", "defer")
ACTIONS = (
    "continue_observation",
    "pause_observation",
    "resume_observation",
    "review_interruption",
    "review_restart",
    "present_completion",
    "present_failure",
    "present_blocked",
    "present_inconclusive",
)
PURPOSE_CODES = (
    "operator_soak_progression",
    "operator_pause_review",
    "operator_resume_review",
    "operator_interruption_review",
    "operator_restart_review",
    "operator_interval_disposition",
)
LIFECYCLE_STATES = (
    "review_required",
    "observation_only",
    "paused_evidence_only",
    "completed_evidence_only",
    "failed_evidence_only",
    "blocked",
    "inconclusive",
)
ACTION_TARGETS = {
    "continue_observation": "observation_only",
    "pause_observation": "paused_evidence_only",
    "resume_observation": "observation_only",
    "review_interruption": "review_required",
    "review_restart": "review_required",
    "present_completion": "completed_evidence_only",
    "present_failure": "failed_evidence_only",
    "present_blocked": "blocked",
    "present_inconclusive": "inconclusive",
}
ALLOWED_CURRENT = {
    "continue_observation": {"review_required", "observation_only", "paused_evidence_only"},
    "pause_observation": {"review_required", "observation_only"},
    "resume_observation": {"paused_evidence_only"},
    "review_interruption": set(LIFECYCLE_STATES),
    "review_restart": set(LIFECYCLE_STATES),
    "present_completion": {"review_required", "observation_only", "paused_evidence_only"},
    "present_failure": set(LIFECYCLE_STATES),
    "present_blocked": set(LIFECYCLE_STATES),
    "present_inconclusive": set(LIFECYCLE_STATES),
}
PRIVATE_TOKENS = (
    "prompt",
    "conversation_text",
    "message",
    "memory_content",
    "memory_text",
    "memory_record",
    "secret",
    "raw_source",
    "source_text",
    "patch",
    "stdout",
    "stderr",
    "provider_payload",
    "private_reasoning",
)
MAX_TRANSITION_SEQUENCE = 1024
MAX_SESSION_INDEX = 63
MAX_DAY_INDEX = 13


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(character in "0123456789abcdef" for character in token)


def _private_fields(value: object, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            if any(token in str(key).lower() for token in PRIVATE_TOKENS):
                findings.append(label)
            findings.extend(_private_fields(item, label))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(_private_fields(item, f"{prefix}[{index}]"))
    return sorted(set(findings))


def create_soak_progression_request(
    *,
    progression_id: str,
    soak_id: str,
    soak_digest: str,
    plan_digest: str,
    terminal_interval_digest: str,
    snapshot_digest: str,
    context_digest: str,
    action: str,
    current_lifecycle_state: str,
    target_lifecycle_state: str,
    purpose_code: str,
    session_index: int,
    day_index: int,
    transition_sequence: int,
    previous_transition_digest: str,
    artifact_digest: str,
    receipt_digest: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "progression_id": str(progression_id),
        "soak_id": str(soak_id),
        "soak_digest": str(soak_digest),
        "plan_digest": str(plan_digest),
        "terminal_interval_digest": str(terminal_interval_digest),
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "action": str(action),
        "current_lifecycle_state": str(current_lifecycle_state),
        "target_lifecycle_state": str(target_lifecycle_state),
        "purpose_code": str(purpose_code),
        "session_index": session_index,
        "day_index": day_index,
        "transition_sequence": transition_sequence,
        "previous_transition_digest": str(previous_transition_digest),
        "artifact_digest": str(artifact_digest),
        "receipt_digest": str(receipt_digest),
        "content_free": True,
        "actual_waiting_requested": False,
        "automatic_continuation_requested": False,
        "execution_requested": False,
        "pause_execution_requested": False,
        "resume_execution_requested": False,
        "cancellation_requested": False,
        "recovery_requested": False,
        "runtime_mutation_requested": False,
        "provider_contact_requested": False,
        "model_contact_requested": False,
        "thread_start_requested": False,
        "process_start_requested": False,
        "approval_creation_requested": False,
        "approval_consumption_requested": False,
        "authority_requested": False,
    }
    row["request_digest"] = _digest(row)
    return row


def create_soak_progression_review(
    *,
    request_digest: str,
    review_id: str,
    decision: str,
    operator_review_digest: str,
    reason_code: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "request_digest": str(request_digest),
        "review_id": str(review_id),
        "decision": str(decision),
        "operator_review_digest": str(operator_review_digest),
        "reason_code": str(reason_code),
        "content_free": True,
        "approval_created": False,
        "approval_consumed": False,
        "execution_authorized": False,
        "continuation_started": False,
        "pause_executed": False,
        "resume_executed": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "authority_granted": False,
    }
    row["review_digest"] = _digest(row)
    return row


def review_soak_progression(
    *,
    soak_summary: Mapping[str, Any],
    request: Mapping[str, Any],
    review: Mapping[str, Any],
    current_snapshot_digest: str,
    current_context_digest: str,
    previous_transition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    summary = dict(soak_summary)
    req = dict(request)
    rev = dict(review)
    previous = dict(previous_transition or {})

    for field in _private_fields({"summary": summary, "request": req, "review": rev, "previous": previous}):
        errors.append(f"private_field:{field}")

    for row, digest_field, label in (
        (req, "request_digest", "request"),
        (rev, "review_digest", "review"),
    ):
        supplied = row.get(digest_field)
        unsigned = dict(row)
        unsigned.pop(digest_field, None)
        if supplied != _digest(unsigned):
            errors.append(f"{label}_tamper")

    if req.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_request_contract")
    if rev.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_review_contract")
    if not str(req.get("progression_id") or ""):
        errors.append("missing_progression_id")
    if not str(req.get("soak_id") or ""):
        errors.append("missing_soak_id")
    if not str(rev.get("review_id") or ""):
        errors.append("missing_review_id")

    for field in (
        "soak_digest",
        "plan_digest",
        "terminal_interval_digest",
        "snapshot_digest",
        "context_digest",
        "artifact_digest",
        "receipt_digest",
    ):
        if not _is_digest(req.get(field)):
            errors.append(f"malformed_{field}")
    if not _is_digest(rev.get("operator_review_digest")):
        errors.append("malformed_operator_review_digest")
    if req.get("snapshot_digest") != current_snapshot_digest:
        errors.append("stale_snapshot")
    if req.get("context_digest") != current_context_digest:
        errors.append("stale_context")
    if req.get("soak_digest") != summary.get("soak_digest"):
        errors.append("stale_soak")
    if summary.get("plan_digest") and req.get("plan_digest") != summary.get("plan_digest"):
        errors.append("stale_plan")
    if summary.get("terminal_interval_digest") and req.get("terminal_interval_digest") != summary.get("terminal_interval_digest"):
        errors.append("stale_terminal_interval")

    action = str(req.get("action") or "")
    current_state = str(req.get("current_lifecycle_state") or "")
    target_state = str(req.get("target_lifecycle_state") or "")
    if action not in ACTIONS:
        errors.append("unsupported_action")
    if current_state not in LIFECYCLE_STATES:
        errors.append("unsupported_current_lifecycle_state")
    if target_state not in LIFECYCLE_STATES:
        errors.append("unsupported_target_lifecycle_state")
    if action in ACTION_TARGETS and target_state != ACTION_TARGETS[action]:
        errors.append("action_target_mismatch")
    if action in ALLOWED_CURRENT and current_state not in ALLOWED_CURRENT[action]:
        errors.append("invalid_lifecycle_transition")
    if req.get("purpose_code") not in PURPOSE_CODES:
        errors.append("unsupported_purpose_code")
    if rev.get("decision") not in DECISIONS:
        errors.append("unsupported_decision")
    if rev.get("request_digest") != req.get("request_digest"):
        errors.append("review_request_mismatch")
    if not str(rev.get("reason_code") or ""):
        errors.append("missing_reason_code")

    for field, maximum in (
        ("transition_sequence", MAX_TRANSITION_SEQUENCE),
        ("session_index", MAX_SESSION_INDEX),
        ("day_index", MAX_DAY_INDEX),
    ):
        value = req.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > maximum:
            errors.append(f"invalid_{field}")

    sequence = req.get("transition_sequence")
    supplied_previous = str(req.get("previous_transition_digest") or "")
    if sequence == 0:
        if supplied_previous or previous:
            errors.append("unexpected_previous_transition")
    elif isinstance(sequence, int) and sequence > 0:
        if not previous:
            errors.append("missing_previous_transition")
        else:
            previous_digest = previous.get("transition_digest")
            if not _is_digest(previous_digest):
                errors.append("malformed_previous_transition_digest")
            if supplied_previous != previous_digest:
                errors.append("broken_transition_lineage")
            if previous.get("transition_sequence") != sequence - 1:
                errors.append("noncontiguous_transition_sequence")
            if previous.get("soak_id") != req.get("soak_id"):
                errors.append("previous_transition_soak_mismatch")
            if previous.get("content_free") is not True:
                errors.append("previous_transition_content_exposure")

    if action == "review_interruption" and int(summary.get("interruption_evidence_count") or 0) < 1:
        errors.append("missing_interruption_evidence")
    if action == "review_restart" and int(summary.get("restart_evidence_count") or 0) < 1:
        errors.append("missing_restart_evidence")

    expected_summary_truth = {
        "foreground_path_available": True,
        "exact_lineage_verified": True,
        "original_evidence_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
        "content_free": True,
    }
    for field, expected in expected_summary_truth.items():
        if summary.get(field) is not expected:
            errors.append(f"soak_summary_{field}_mismatch")

    for field in (
        "actual_waiting_requested",
        "automatic_continuation_requested",
        "execution_requested",
        "pause_execution_requested",
        "resume_execution_requested",
        "cancellation_requested",
        "recovery_requested",
        "runtime_mutation_requested",
        "provider_contact_requested",
        "model_contact_requested",
        "thread_start_requested",
        "process_start_requested",
        "approval_creation_requested",
        "approval_consumption_requested",
        "authority_requested",
    ):
        if req.get(field) is not False:
            errors.append(f"forbidden_request_claim:{field}")
    for field in (
        "approval_created",
        "approval_consumed",
        "execution_authorized",
        "continuation_started",
        "pause_executed",
        "resume_executed",
        "cancellation_executed",
        "recovery_executed",
        "authority_granted",
    ):
        if rev.get(field) is not False:
            errors.append(f"forbidden_review_claim:{field}")
    if req.get("content_free") is not True or rev.get("content_free") is not True:
        errors.append("content_exposure")

    errors = sorted(set(errors))
    decision = str(rev.get("decision") or "")
    if errors:
        status = "blocked"
    elif decision == "approve":
        status = "progression_presented"
    elif decision == "reject":
        status = "progression_rejected"
    else:
        status = "progression_deferred"

    approved = status == "progression_presented"
    result: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "decision": decision,
        "errors": errors,
        "error_count": len(errors),
        "progression_id": str(req.get("progression_id") or ""),
        "soak_id": str(req.get("soak_id") or ""),
        "soak_digest": str(req.get("soak_digest") or ""),
        "action": action,
        "current_lifecycle_state": current_state,
        "presented_lifecycle_state": target_state if approved else current_state,
        "transition_sequence": req.get("transition_sequence"),
        "session_index": req.get("session_index"),
        "day_index": req.get("day_index"),
        "previous_transition_digest": supplied_previous,
        "accountable_transition_presented": approved,
        "continuation_eligible": approved and action == "continue_observation",
        "pause_presented": approved and action == "pause_observation",
        "resume_eligible": approved and action == "resume_observation",
        "interruption_review_presented": approved and action == "review_interruption",
        "restart_review_presented": approved and action == "review_restart",
        "terminal_disposition_presented": approved and action.startswith("present_"),
        "content_free": True,
        "foreground_path_available": True,
        "exact_lineage_verified": not errors,
        "original_evidence_preserved": True,
        "current_regressions_separate": True,
        "inherited_debt_visible": True,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "progression_started": False,
        "pause_executed": False,
        "resume_executed": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "runtime_mutated": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
    }
    result["transition_digest"] = _digest(result)
    return result


def public_soak_progression_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "contract_version",
        "status",
        "decision",
        "action",
        "current_lifecycle_state",
        "presented_lifecycle_state",
        "transition_sequence",
        "session_index",
        "day_index",
        "accountable_transition_presented",
        "continuation_eligible",
        "pause_presented",
        "resume_eligible",
        "interruption_review_presented",
        "restart_review_presented",
        "terminal_disposition_presented",
        "error_count",
        "transition_digest",
        "content_free",
        "foreground_path_available",
        "exact_lineage_verified",
        "original_evidence_preserved",
        "current_regressions_separate",
        "inherited_debt_visible",
        "actual_waiting_started",
        "automatic_continuation",
        "progression_started",
        "pause_executed",
        "resume_executed",
        "approval_created",
        "approval_consumed",
        "execution_invoked",
        "cancellation_executed",
        "recovery_executed",
        "runtime_mutated",
        "provider_contacted",
        "model_contacted",
        "thread_started",
        "process_started",
        "global_profile_pass_claimed",
        "authority_granted",
    )
    return {key: result.get(key) for key in keys}
