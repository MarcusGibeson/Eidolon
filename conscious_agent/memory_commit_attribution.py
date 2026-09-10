from __future__ import annotations

"""Content-free provenance and eligibility evidence for durable conversation memories.

The attribution contract binds a stored memory candidate to the exact conversation
operation and session that produced it. It never stores prompts, generated text,
provider payloads, credentials, raw receipts, or unrestricted command output.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


MEMORY_COMMIT_ATTRIBUTION_SCHEMA_VERSION = "1"
_ALLOWED_ROLES = {"user", "assistant"}


class MemoryCommitAttributionError(ValueError):
    pass


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _bounded(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def acceptance_identity_for_operation(operation_id: str) -> tuple[str, str]:
    """Resolve the exact accepted identity without retaining its raw client key."""
    operation = _bounded(operation_id, 100)
    if not operation:
        raise MemoryCommitAttributionError("Conversation operation identity is required.")
    acceptance_key = ""
    try:
        from conversation_operations import load_operation_marker

        marker = load_operation_marker(operation) or {}
        acceptance_key = _bounded(marker.get("acceptance_key"), 96)
    except Exception:
        acceptance_key = ""
    if acceptance_key:
        return "client_acceptance_key", _digest(acceptance_key)
    return "conversation_operation_id", _digest(operation)


def assistant_commit_eligibility(
    *,
    response: str,
    completion_state: str,
    provider_generation_completed: bool,
    operation_completion_claimed: bool,
    synthetic_response: bool = False,
    partial_response: bool = False,
) -> dict[str, Any]:
    """Return the canonical assistant-memory eligibility decision."""
    text_present = bool(str(response or "").strip())
    state = _bounded(completion_state, 80).lower()
    reasons: list[str] = []
    if state != "completed":
        reasons.append("completion_state_not_completed")
    if not provider_generation_completed:
        reasons.append("provider_generation_not_completed")
    if not operation_completion_claimed:
        reasons.append("operation_completion_not_claimed")
    if not text_present:
        reasons.append("generated_response_missing")
    if synthetic_response:
        reasons.append("synthetic_response")
    if partial_response:
        reasons.append("partial_response")
    eligible = not reasons
    return {
        "decision": "eligible" if eligible else "ineligible",
        "eligible": eligible,
        "reason": "completed_generated_turn" if eligible else reasons[0],
        "all_reasons": reasons,
        "evaluated_at": _now_utc(),
    }


def build_memory_commit_attribution(
    *,
    role: str,
    operation_id: str,
    session_id: str,
    turn_id: str,
    source: str,
    content: str,
    completion_state: str,
    provider_generation_completed: bool = False,
    operation_completion_claimed: bool = False,
    synthetic_response: bool = False,
    partial_response: bool = False,
) -> dict[str, Any]:
    """Build bounded provenance for one exact durable conversation-memory candidate."""
    normalized_role = _bounded(role, 20).lower()
    if normalized_role not in _ALLOWED_ROLES:
        raise MemoryCommitAttributionError("Unsupported conversation-memory role.")
    operation = _bounded(operation_id, 100)
    session = _bounded(session_id, 120)
    turn = _bounded(turn_id, 120)
    if not operation or not session or not turn:
        raise MemoryCommitAttributionError("Operation, session, and turn identities are required.")
    identity_kind, identity_digest = acceptance_identity_for_operation(operation)
    content_digest = _digest(str(content or ""))
    candidate_seed = json.dumps(
        {
            "role": normalized_role,
            "operation_id": operation,
            "session_id": session,
            "turn_id": turn,
            "acceptance_identity_digest": identity_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate_id = f"memory_candidate_{hashlib.sha256(candidate_seed.encode('utf-8')).hexdigest()[:24]}"

    if normalized_role == "assistant":
        eligibility = assistant_commit_eligibility(
            response=content,
            completion_state=completion_state,
            provider_generation_completed=provider_generation_completed,
            operation_completion_claimed=operation_completion_claimed,
            synthetic_response=synthetic_response,
            partial_response=partial_response,
        )
    else:
        eligibility = {
            "decision": "not_applicable",
            "eligible": False,
            "reason": "user_input_memory",
            "all_reasons": [],
            "evaluated_at": _now_utc(),
        }

    return {
        "schema_version": MEMORY_COMMIT_ATTRIBUTION_SCHEMA_VERSION,
        "memory_candidate_id": candidate_id,
        "role": normalized_role,
        "conversation_operation_id": operation,
        "conversation_session_id": session,
        "conversation_turn_id": turn,
        "acceptance_identity_kind": identity_kind,
        "acceptance_identity_digest": identity_digest,
        "content_digest": content_digest,
        "source": _bounded(source, 80),
        "completion_evidence": {
            "completion_state": _bounded(completion_state, 80).lower(),
            "provider_generation_completed": bool(provider_generation_completed),
            "operation_completion_claimed": bool(operation_completion_claimed),
            "generated_response_present": bool(str(content or "").strip()) if normalized_role == "assistant" else False,
            "synthetic_response": bool(synthetic_response),
            "partial_response": bool(partial_response),
        },
        "eligibility_decision": eligibility,
        "recorded_at": _now_utc(),
        "contains_prompt": False,
        "contains_response": False,
        "contains_provider_payload": False,
        "contains_credentials": False,
        "content_free_evidence": True,
    }


def validate_memory_commit_attribution(
    value: Mapping[str, Any] | None,
    *,
    require_assistant_eligible: bool = False,
) -> dict[str, Any]:
    """Validate an attribution record before a durable assistant-memory write."""
    record = dict(value or {})
    if str(record.get("schema_version") or "") != MEMORY_COMMIT_ATTRIBUTION_SCHEMA_VERSION:
        raise MemoryCommitAttributionError("Unsupported memory-commit attribution schema.")
    role = str(record.get("role") or "")
    if role not in _ALLOWED_ROLES:
        raise MemoryCommitAttributionError("Memory-commit role is invalid.")
    for field in (
        "memory_candidate_id",
        "conversation_operation_id",
        "conversation_session_id",
        "conversation_turn_id",
        "acceptance_identity_digest",
        "content_digest",
    ):
        if not str(record.get(field) or "").strip():
            raise MemoryCommitAttributionError(f"Memory-commit attribution is missing {field}.")
    if not bool(record.get("content_free_evidence")):
        raise MemoryCommitAttributionError("Memory-commit attribution must remain content-free.")
    if require_assistant_eligible:
        decision = record.get("eligibility_decision") if isinstance(record.get("eligibility_decision"), Mapping) else {}
        evidence = record.get("completion_evidence") if isinstance(record.get("completion_evidence"), Mapping) else {}
        if role != "assistant" or not bool(decision.get("eligible")):
            raise MemoryCommitAttributionError("Assistant memory is not eligible for durable commit.")
        if str(evidence.get("completion_state") or "") != "completed":
            raise MemoryCommitAttributionError("Assistant memory lacks completed-turn evidence.")
        if not bool(evidence.get("provider_generation_completed")) or not bool(evidence.get("operation_completion_claimed")):
            raise MemoryCommitAttributionError("Assistant memory lacks successful generation completion evidence.")
        if bool(evidence.get("synthetic_response")) or bool(evidence.get("partial_response")):
            raise MemoryCommitAttributionError("Synthetic or partial assistant responses cannot be committed.")
    return record


def public_memory_commit_attribution(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return provenance suitable for operator curation surfaces."""
    try:
        record = validate_memory_commit_attribution(value)
    except MemoryCommitAttributionError:
        return {
            "schema_version": MEMORY_COMMIT_ATTRIBUTION_SCHEMA_VERSION,
            "available": False,
            "origin": "legacy_or_operator",
            "content_free_evidence": True,
        }
    decision = record.get("eligibility_decision") if isinstance(record.get("eligibility_decision"), Mapping) else {}
    evidence = record.get("completion_evidence") if isinstance(record.get("completion_evidence"), Mapping) else {}
    return {
        "schema_version": MEMORY_COMMIT_ATTRIBUTION_SCHEMA_VERSION,
        "available": True,
        "origin": "generated_turn" if record.get("role") == "assistant" else "user_turn",
        "memory_candidate_id": str(record.get("memory_candidate_id") or ""),
        "conversation_operation_id": str(record.get("conversation_operation_id") or ""),
        "conversation_session_id": str(record.get("conversation_session_id") or ""),
        "conversation_turn_id": str(record.get("conversation_turn_id") or ""),
        "acceptance_identity_kind": str(record.get("acceptance_identity_kind") or ""),
        "acceptance_identity_digest": str(record.get("acceptance_identity_digest") or ""),
        "eligibility_decision": str(decision.get("decision") or "unknown"),
        "eligibility_reason": str(decision.get("reason") or ""),
        "completion_state": str(evidence.get("completion_state") or ""),
        "provider_generation_completed": bool(evidence.get("provider_generation_completed")),
        "operation_completion_claimed": bool(evidence.get("operation_completion_claimed")),
        "synthetic_response": bool(evidence.get("synthetic_response")),
        "partial_response": bool(evidence.get("partial_response")),
        "recorded_at": str(record.get("recorded_at") or ""),
        "contains_prompt": False,
        "contains_response": False,
        "contains_provider_payload": False,
        "content_free_evidence": True,
    }
