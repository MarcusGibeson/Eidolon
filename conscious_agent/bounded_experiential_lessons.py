from __future__ import annotations

"""Bounded, authority-free experiential lesson candidates for v1168.0-v1168.2."""

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "1168.8"
MAX_MESSAGE_CHARS = 4000
MAX_EXPERIENCE_ROWS = 24
MAX_PROMPT_CHARS = 3200
MAX_PRIOR_LESSON_RECEIPTS = 12
MAX_PRIOR_LESSON_RECEIPT_BYTES = 24000
_AUTHORITY_FIELDS = {"approval_granted", "authorized", "execute", "execution_permitted", "tool_use_permitted", "training_permitted", "installation_permitted", "promotion_permitted", "certification_permitted"}
_PRIVATE_FIELDS = {"private_chain_of_thought", "chain_of_thought", "hidden_reasoning", "provider_payload", "raw_prompt", "raw_provider_response", "memory_text"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class LessonCandidate:
    lesson_type: str
    source_kind: str
    target_state: str
    confidence_band: str
    review_required: bool
    historical_truth_preserved: bool
    memory_mutation_performed: bool
    model_training_performed: bool
    self_training_permitted: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_bounded_experiential_lesson(
    message: object,
    immediate_learning_projection: object,
    experience_rows: object = (),
    protected_operator_constraints: object = None,
    prior_lesson_receipts: object = (),
) -> dict[str, Any]:
    text = str(message or "")
    oversized_message = len(text) > MAX_MESSAGE_CHARS
    malformed_projection = not isinstance(immediate_learning_projection, Mapping)
    projection = {} if malformed_projection else dict(immediate_learning_projection)
    policy = projection.get("policy") if isinstance(projection.get("policy"), Mapping) else {}
    candidate = projection.get("candidate") if isinstance(projection.get("candidate"), Mapping) else None

    malformed_rows = not isinstance(experience_rows, Sequence) or isinstance(experience_rows, (str, bytes, bytearray))
    rows = [] if malformed_rows else list(experience_rows)[:MAX_EXPERIENCE_ROWS]
    oversized_rows = not malformed_rows and len(experience_rows) > MAX_EXPERIENCE_ROWS
    authority_violations = private_violations = malformed_count = 0
    failure_signal = repair_signal = success_signal = 0
    for row in rows:
        if not isinstance(row, Mapping):
            malformed_count += 1
            continue
        if any(key in row and row.get(key) not in {False, None, "", 0} for key in _AUTHORITY_FIELDS):
            authority_violations += 1
            continue
        if any(key in row for key in _PRIVATE_FIELDS):
            private_violations += 1
            continue
        state = str(row.get("completion_state") or row.get("failure_category") or row.get("state") or "").lower()
        failure_signal += int(any(token in state for token in ("failed", "failure", "error", "cancelled", "timeout")))
        repair_signal += int(any(token in state for token in ("repaired", "recovered", "corrected")))
        success_signal += int(any(token in state for token in ("completed", "success", "verified")))

    prior = validate_prior_lesson_receipts(prior_lesson_receipts)
    constraints = set(protected_operator_constraints or ()) if isinstance(protected_operator_constraints, Sequence) and not isinstance(protected_operator_constraints, (str, bytes, bytearray)) else set()
    required = {"no_uncontrolled_self_training", "review_before_durable_lesson", "preserve_historical_truth"}
    constraints_valid = required <= constraints

    candidate_type = str((candidate or {}).get("candidate_type") or "none")
    candidate_scope = str((candidate or {}).get("scope") or "none")
    lesson_type = "none"
    source_kind = "none"
    target_state = "unresolved"
    if candidate and candidate_scope == "durable_candidate" and candidate_type in {"correction", "retraction", "preference_change"}:
        lesson_type = {"correction": "corrective_lesson", "retraction": "retraction_lesson", "preference_change": "preference_lesson"}[candidate_type]
        source_kind = "explicit_user_change"
        target_state = "resolved" if str(candidate.get("target_key") or "unresolved") != "unresolved" else "unresolved"
    elif failure_signal and repair_signal:
        lesson_type, source_kind = "repair_lesson", "bounded_failure_recovery"
    elif failure_signal:
        lesson_type, source_kind = "failure_avoidance_lesson", "bounded_failure"
    elif success_signal >= 2:
        lesson_type, source_kind = "repeatable_success_lesson", "bounded_repeated_success"

    degraded = bool(
        oversized_message or malformed_projection or malformed_rows or oversized_rows or malformed_count
        or authority_violations or private_violations or not constraints_valid
        or bool(policy.get("policy_recovered")) or bool(prior["policy_recovered"])
    )
    lesson = None
    if lesson_type != "none" and not degraded:
        lesson = LessonCandidate(
            lesson_type=lesson_type,
            source_kind=source_kind,
            target_state=target_state,
            confidence_band="high" if source_kind == "explicit_user_change" else "medium",
            review_required=True,
            historical_truth_preserved=True,
            memory_mutation_performed=False,
            model_training_performed=False,
            self_training_permitted=False,
        ).to_dict()

    evidence = {
        "contract_version": CONTRACT_VERSION,
        "lesson_candidate_count": int(lesson is not None),
        "failure_signal_count": failure_signal,
        "repair_signal_count": repair_signal,
        "success_signal_count": success_signal,
        "malformed_experience_count": malformed_count,
        "malformed_experience_collection": malformed_rows,
        "oversized_experience_collection": oversized_rows,
        "oversized_message": oversized_message,
        "authority_violation_count": authority_violations,
        "private_field_violation_count": private_violations,
        "constraints_valid": constraints_valid,
        "historical_truth_preserved": True,
        "memory_mutated": False,
        "model_weights_changed": False,
        "provider_contacted": False,
        "contains_experience_text": False,
        "contains_private_reasoning": False,
        "verified_prior_lesson_receipts": prior["verified_receipt_count"],
        "replayed_prior_lesson_receipts": prior["replayed_receipt_count"],
        "tampered_prior_lesson_receipts": prior["tampered_receipt_count"],
        "conflicting_prior_lesson_receipts": prior["conflicting_receipts"],
        "authority": "none",
        "integrity": "degraded" if degraded else "valid",
    }
    evidence["evidence_digest"] = _digest(evidence)
    lesson_policy = {
        "contract_version": CONTRACT_VERSION,
        "lesson_posture": "literal_request_only_recovery" if degraded else ("stage_bounded_lesson_candidate" if lesson else "no_lesson_candidate"),
        "lesson_type": lesson_type if lesson else "none",
        "source_kind": source_kind if lesson else "none",
        "target_state": target_state if lesson else "unresolved",
        "review_required": bool(lesson),
        "durable_commit_permitted": False,
        "memory_mutation_permitted": False,
        "model_training_permitted": False,
        "self_training_permitted": False,
        "automatic_generalization_permitted": False,
        "historical_truth_preserved": True,
        "policy_recovered": degraded,
        "recovery_reason": prior["recovery_reason"] if prior["policy_recovered"] else ("invalid_or_unbounded_experience" if degraded else "none"),
        "continuity_disposition": prior["continuity_disposition"],
        "verified_prior_lesson_receipts": prior["verified_receipt_count"],
        "replayed_prior_lesson_receipts": prior["replayed_receipt_count"],
        "tampered_prior_lesson_receipts": prior["tampered_receipt_count"],
        "conflicting_prior_lesson_receipts": prior["conflicting_receipts"],
        "authority": "none",
        "content_free": True,
        "evidence_digest": evidence["evidence_digest"],
    }
    lesson_policy["policy_digest"] = _digest(lesson_policy)
    diagnostics = dict(lesson_policy)
    diagnostics.update({
        "lesson_candidate_count": int(lesson is not None),
        "failure_signal_count": failure_signal,
        "repair_signal_count": repair_signal,
        "success_signal_count": success_signal,
        "provider_contacted": False,
        "model_weights_changed": False,
    })
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    prompt = '<bounded_experiential_lesson data_only="true" authority="none">' + json.dumps(lesson_policy, sort_keys=True, separators=(",", ":")) + '</bounded_experiential_lesson>'
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError("bounded experiential lesson prompt exceeded bound")
    return {"policy": lesson_policy, "evidence": evidence, "candidate": lesson, "diagnostics": diagnostics, "prompt_section": prompt}


def verify_bounded_experiential_lesson_diagnostics(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("diagnostics_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "diagnostics_digest"}
    return len(supplied) == 64 and _digest(unsigned) == supplied and value.get("authority") == "none" and value.get("content_free") is True and value.get("self_training_permitted") is False and value.get("model_training_permitted") is False


def build_lesson_review_boundary_handoff(
    candidate: object,
    *,
    provider_completed: bool,
    assistant_memory_committed: bool,
) -> dict[str, Any]:
    """Create a content-free operator-review handoff; never commit or train."""
    valid = isinstance(candidate, Mapping) and str(candidate.get("lesson_type") or "") in {
        "corrective_lesson", "retraction_lesson", "preference_lesson",
        "repair_lesson", "failure_avoidance_lesson", "repeatable_success_lesson",
    }
    eligible = bool(valid and provider_completed and assistant_memory_committed)
    handoff = {
        "contract_version": CONTRACT_VERSION,
        "lesson_candidate_present": valid,
        "lesson_type": str(candidate.get("lesson_type") or "none") if valid else "none",
        "source_kind": str(candidate.get("source_kind") or "none") if valid else "none",
        "target_state": str(candidate.get("target_state") or "unresolved") if valid else "unresolved",
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_operator_review": eligible,
        "durable_commit_permitted": False,
        "memory_mutation_performed": False,
        "model_training_performed": False,
        "self_training_permitted": False,
        "historical_truth_preserved": True,
        "authority": "none",
        "content_free": True,
    }
    handoff["handoff_digest"] = _digest(handoff)
    return handoff


def verify_lesson_review_boundary_handoff(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("handoff_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "handoff_digest"}
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("authority") == "none" and value.get("content_free") is True
        and value.get("durable_commit_permitted") is False
        and value.get("memory_mutation_performed") is False
        and value.get("model_training_performed") is False
        and value.get("self_training_permitted") is False
    )


def validate_prior_lesson_receipts(receipts: object) -> dict[str, Any]:
    malformed_collection = not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes, bytearray))
    rows = [] if malformed_collection else list(receipts)
    oversized_collection = len(rows) > MAX_PRIOR_LESSON_RECEIPTS
    try:
        oversized_bytes = (not malformed_collection and len(json.dumps(rows, sort_keys=True, default=str).encode()) > MAX_PRIOR_LESSON_RECEIPT_BYTES)
    except Exception:
        oversized_bytes = True
    verified = stale = tampered = replayed = 0
    seen: set[str] = set()
    lesson_types: list[str] = []
    source_kinds: list[str] = []
    target_states: list[str] = []
    for row in rows[:MAX_PRIOR_LESSON_RECEIPTS]:
        if not isinstance(row, Mapping):
            tampered += 1
            continue
        if "bounded_experiential_lesson_review_handoff" in row:
            nested = row.get("bounded_experiential_lesson_review_handoff")
            if not isinstance(nested, Mapping):
                tampered += 1
                continue
            receipt = nested
        elif "handoff_digest" in row and "eligible_for_operator_review" in row:
            receipt = row
        else:
            # Ordinary transcript rows are not lesson receipts and must not force
            # the entire learning stack into a false recovery posture.
            continue
        if not verify_lesson_review_boundary_handoff(receipt):
            tampered += 1
            continue
        digest = str(receipt.get("handoff_digest") or "")
        if digest in seen:
            replayed += 1
            continue
        seen.add(digest)
        if receipt.get("eligible_for_operator_review") is not True:
            stale += 1
            continue
        verified += 1
        lesson_types.append(str(receipt.get("lesson_type") or "none"))
        source_kinds.append(str(receipt.get("source_kind") or "none"))
        target_states.append(str(receipt.get("target_state") or "unresolved"))
    conflicting = (
        len(set(lesson_types)) > 1
        or ("resolved" in target_states and "unresolved" in target_states)
        or (len(set(source_kinds)) > 1 and len(set(lesson_types)) == 1)
    )
    recovered = bool(malformed_collection or oversized_collection or oversized_bytes or tampered or conflicting)
    result = {
        "verified_receipt_count": verified,
        "stale_receipt_count": stale,
        "tampered_receipt_count": tampered,
        "replayed_receipt_count": replayed,
        "malformed_collection": malformed_collection,
        "oversized_collection": oversized_collection,
        "oversized_receipt_bytes": oversized_bytes,
        "conflicting_receipts": conflicting,
        "policy_recovered": recovered,
        "recovery_reason": "invalid_or_conflicting_prior_lesson_receipts" if recovered else "none",
        "continuity_disposition": "literal_request_only_recovery" if recovered else ("resume_verified_lesson_context" if verified else "use_current_turn_only"),
        "authority": "none",
        "content_free": True,
    }
    result["receipt_digest"] = _digest(result)
    return result


def audit_bounded_experiential_lesson(
    projection: object,
    handoff: object = None,
) -> dict[str, Any]:
    """Audit bounded lesson state without retaining lesson or experience content."""
    malformed_projection = not isinstance(projection, Mapping)
    policy = projection.get("policy") if isinstance(projection, Mapping) else None
    candidate = projection.get("candidate") if isinstance(projection, Mapping) else None
    diagnostics = projection.get("diagnostics") if isinstance(projection, Mapping) else None
    malformed_policy = not isinstance(policy, Mapping)
    malformed_candidate = candidate is not None and not isinstance(candidate, Mapping)
    invalid_diagnostics = not verify_bounded_experiential_lesson_diagnostics(diagnostics)
    authority_violations = 0
    private_field_violations = 0
    for item in (policy, candidate, diagnostics, handoff):
        if not isinstance(item, Mapping):
            continue
        authority_violations += sum(1 for key in _AUTHORITY_FIELDS if key in item and item.get(key) not in {False, None, "", 0})
        private_field_violations += sum(1 for key in _PRIVATE_FIELDS if key in item)
    handoff_present = handoff is not None
    invalid_handoff = handoff_present and not verify_lesson_review_boundary_handoff(handoff)
    candidate_present = isinstance(candidate, Mapping)
    eligible_handoff = isinstance(handoff, Mapping) and handoff.get("eligible_for_operator_review") is True
    premature_handoff = bool(eligible_handoff and not candidate_present)
    recovered_candidate_violation = bool(isinstance(policy, Mapping) and policy.get("policy_recovered") is True and candidate_present)
    mutation_or_training_violation = bool(
        (isinstance(policy, Mapping) and (
            policy.get("durable_commit_permitted") is not False
            or policy.get("memory_mutation_permitted") is not False
            or policy.get("model_training_permitted") is not False
            or policy.get("self_training_permitted") is not False
            or policy.get("automatic_generalization_permitted") is not False
        ))
        or (isinstance(handoff, Mapping) and (
            handoff.get("durable_commit_permitted") is not False
            or handoff.get("memory_mutation_performed") is not False
            or handoff.get("model_training_performed") is not False
            or handoff.get("self_training_permitted") is not False
        ))
    )
    candidate_contract_violation = bool(candidate_present and (
        candidate.get("review_required") is not True
        or candidate.get("historical_truth_preserved") is not True
        or candidate.get("memory_mutation_performed") is not False
        or candidate.get("model_training_performed") is not False
        or candidate.get("self_training_permitted") is not False
    ))
    compliant = not any((
        malformed_projection, malformed_policy, malformed_candidate, invalid_diagnostics, invalid_handoff,
        authority_violations, private_field_violations, premature_handoff, recovered_candidate_violation,
        mutation_or_training_violation, candidate_contract_violation,
    ))
    result = {
        "contract_version": CONTRACT_VERSION,
        "malformed_projection": malformed_projection,
        "malformed_policy": malformed_policy,
        "malformed_candidate": malformed_candidate,
        "invalid_diagnostics": invalid_diagnostics,
        "handoff_present": handoff_present,
        "invalid_handoff": invalid_handoff,
        "authority_violation_count": authority_violations,
        "private_field_violation_count": private_field_violations,
        "premature_handoff": premature_handoff,
        "recovered_candidate_violation": recovered_candidate_violation,
        "mutation_or_training_violation": mutation_or_training_violation,
        "candidate_contract_violation": candidate_contract_violation,
        "compliant": compliant,
        "durable_lesson_committed": False,
        "memory_mutation_performed": False,
        "model_training_performed": False,
        "contains_lesson_content": False,
        "contains_experience_text": False,
        "contains_private_reasoning": False,
        "authority": "none",
        "content_free": True,
    }
    result["audit_digest"] = _digest(result)
    return result


def verify_bounded_experiential_lesson_audit(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("audit_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "audit_digest"}
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("authority") == "none" and value.get("content_free") is True
        and value.get("durable_lesson_committed") is False
        and value.get("memory_mutation_performed") is False
        and value.get("model_training_performed") is False
        and value.get("contains_lesson_content") is False
        and value.get("contains_experience_text") is False
        and value.get("contains_private_reasoning") is False
    )
