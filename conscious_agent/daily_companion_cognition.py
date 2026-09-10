from __future__ import annotations

"""Bounded v1164.0-v1164.8 Daily Companion Cognition integration and reliability.

Combines already-authoritative conversation policies into one content-free,
authority-free companion posture for the current user-requested response. It
adds no memory unification, learning mutation, autonomous turns, tools, or
private-reflection delivery.
"""

import hashlib
import json
from typing import Any, Iterable

CONTRACT_VERSION = "v1164.8"
MAX_PRIOR_COMPANION_RECEIPTS = 8
MAX_MESSAGE_CHARS = 4096
MAX_CONTEXT_ROWS = 24
MAX_PROMPT_CHARS = 2400

_AUTHORITY_KEYS = {
    "approval_granted", "authorization_granted", "execution_permitted",
    "action_execution_permitted", "may_initiate_new_turn",
    "autonomous_new_turn_permitted", "tool_intent_selected",
    "learning_mutation_permitted", "memory_rewrite_permitted",
    "private_reflection_delivery_permitted", "installation_permitted",
    "promotion_permitted", "certification_permitted",
}
_SUSPICIOUS_KEYS = {
    "private_chain_of_thought", "hidden_reasoning", "provider_payload",
    "raw_memory_text", "memory_text", "conversation_text", "prompt_section",
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bounded_rows(rows: object) -> tuple[int, bool, bool, int, int]:
    if rows is None:
        return 0, False, False, 0, 0
    if isinstance(rows, (str, bytes, dict)):
        return 0, False, True, 0, 0
    try:
        material = list(rows)[: MAX_CONTEXT_ROWS + 1]  # type: ignore[arg-type]
    except Exception:
        return 0, False, True, 0, 0
    truncated = len(material) > MAX_CONTEXT_ROWS
    material = material[:MAX_CONTEXT_ROWS]
    stale = suspicious = valid = 0
    for row in material:
        if not isinstance(row, dict):
            suspicious += 1
            continue
        if str(row.get("status") or "active") in {"stale", "superseded", "rejected"}:
            stale += 1
            continue
        if any(key in row for key in _SUSPICIOUS_KEYS):
            suspicious += 1
            continue
        valid += 1
    return valid, truncated, False, stale, suspicious



def _prior_companion_receipts(rows: object) -> tuple[int, int, int, int, str]:
    """Validate bounded prior content-free companion diagnostics.

    Returns verified, stale, rejected, replayed, and the latest verified posture.
    Raw conversation rows are ignored rather than interpreted as companion state.
    """
    if rows is None:
        return 0, 0, 0, 0, "none"
    if isinstance(rows, (str, bytes, dict)):
        return 0, 0, 1, 0, "none"
    try:
        material = list(rows)[: MAX_PRIOR_COMPANION_RECEIPTS + 1]  # type: ignore[arg-type]
    except Exception:
        return 0, 0, 1, 0, "none"
    rejected = 1 if len(material) > MAX_PRIOR_COMPANION_RECEIPTS else 0
    stale = verified = replayed = 0
    latest = "none"
    seen_digests: set[str] = set()
    for row in material[:MAX_PRIOR_COMPANION_RECEIPTS]:
        if not isinstance(row, dict):
            rejected += 1
            continue
        candidate = row.get("daily_companion_runtime_diagnostics", row)
        if not isinstance(candidate, dict) or "diagnostics_digest" not in candidate:
            continue
        if str(row.get("status") or "active") in {"stale", "superseded", "rejected"}:
            stale += 1
            continue
        if not verify_daily_companion_runtime_diagnostics(candidate):
            rejected += 1
            continue
        receipt_digest = str(candidate.get("diagnostics_digest") or "")
        if receipt_digest in seen_digests:
            replayed += 1
            continue
        seen_digests.add(receipt_digest)
        verified += 1
        latest = str(candidate.get("companion_posture") or "none")[:64]
    return verified, stale, rejected, replayed, latest

def build_daily_companion_evidence(
    message: object,
    response_intent: object,
    conversation_policy: object,
    discourse_policy: object,
    natural_continuity: object,
    natural_follow_up: object,
    governed_speech: object,
    *,
    context_rows: object = None,
    protected_operator_constraints: Iterable[str] = (),
    prior_companion_receipts: object = None,
) -> dict[str, Any]:
    raw = str(message or "")
    bounded = raw[:MAX_MESSAGE_CHARS]
    intent = _mapping(response_intent)
    canonical = _mapping(conversation_policy)
    discourse = _mapping(discourse_policy)
    continuity = _mapping(natural_continuity)
    follow = _mapping(natural_follow_up)
    speech = _mapping(governed_speech)
    valid, context_truncated, context_malformed, stale, suspicious = _bounded_rows(context_rows)
    prior_verified, prior_stale, prior_rejected, prior_replayed, prior_posture = _prior_companion_receipts(prior_companion_receipts)
    components = (intent, canonical, discourse, continuity, follow, speech)
    authority_conflict = any(bool(component.get(key)) for component in components for key in _AUTHORITY_KEYS)
    malformed_components = sum(1 for original in (response_intent, conversation_policy, discourse_policy, natural_continuity, natural_follow_up, governed_speech) if not isinstance(original, dict))
    deliberate_silence = bool(canonical.get("intentional_silence_verified") or speech.get("deliberate_silence_preserved"))
    relation = str(discourse.get("discourse_relation") or "respond")
    continuation = str(follow.get("continuation_posture") or "answer_only")
    topic = str(follow.get("topic_continuity_posture") or "active")
    speech_mode = str(speech.get("speech_mode") or "reactive_answer_only")
    correction = relation == "repair" or bool(discourse.get("address_explicit_correction"))
    closure = relation == "close" or continuation == "briefly_acknowledge_and_close" or topic == "complete"
    clarification = relation == "clarify" or continuation == "ask_one_required_clarification"
    active_continuity = relation == "continue" or continuation == "continue_current_topic"
    policy_conflicts = sum((
        deliberate_silence and (clarification or correction or active_continuity or closure or speech_mode == "bounded_user_requested_observation"),
        closure and active_continuity,
        clarification and closure,
        correction and clarification,
    ))
    degraded = authority_conflict or malformed_components > 0 or context_malformed or suspicious > 0 or policy_conflicts > 0 or prior_rejected > 0 or prior_replayed > 0
    constraints = tuple(str(v)[:80] for v in protected_operator_constraints if isinstance(v, str))[:16]
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "message_present": bool(bounded.strip()),
        "message_truncated": len(raw) > MAX_MESSAGE_CHARS,
        "selected_intent": str(intent.get("selected_intent") or canonical.get("selected_intent") or "direct_answer")[:64],
        "discourse_relation": relation[:48],
        "continuation_posture": continuation[:64],
        "topic_posture": topic[:32],
        "speech_mode": speech_mode[:64],
        "active_continuity": active_continuity,
        "clarification_required": clarification,
        "correction_active": correction,
        "topic_complete": closure,
        "deliberate_silence_verified": deliberate_silence,
        "optional_expansion_allowed": speech_mode == "bounded_user_requested_observation" and not degraded,
        "recent_context_count": valid,
        "context_truncated": context_truncated,
        "context_malformed": context_malformed,
        "stale_records_ignored": stale,
        "suspicious_records_ignored": suspicious,
        "malformed_component_count": malformed_components,
        "authority_conflict_suppressed": authority_conflict,
        "policy_conflict_count": int(policy_conflicts),
        "prior_companion_receipts_verified": prior_verified,
        "prior_companion_receipts_stale": prior_stale,
        "prior_companion_receipts_rejected": prior_rejected,
        "prior_companion_receipts_replayed": prior_replayed,
        "prior_companion_posture": prior_posture,
        "continuity_health": "degraded" if degraded else ("resumable" if prior_verified and active_continuity else "current_turn_verified"),
        "protected_constraint_count": len(constraints),
        "evidence_integrity": "degraded" if degraded else "verified",
        "contains_message_content": False,
        "contains_conversation_text": False,
        "contains_memory_text": False,
        "contains_reflection_text": False,
        "contains_provider_payload": False,
        "contains_private_chain_of_thought": False,
    }
    evidence["evidence_digest"] = _digest(evidence)
    return evidence


def build_daily_companion_policy(evidence: object) -> dict[str, Any]:
    value = _mapping(evidence)
    supplied = str(value.get("evidence_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "evidence_digest"}
    digest_valid = len(supplied) == 64 and _digest(unsigned) == supplied
    degraded = not digest_valid or value.get("evidence_integrity") != "verified"
    if bool(value.get("deliberate_silence_verified")):
        posture, cadence, focus = "preserve_deliberate_silence", "silent", "none"
    elif degraded:
        posture, cadence, focus = "literal_request_only", "brief", "current_request"
    elif bool(value.get("clarification_required")):
        posture, cadence, focus = "clarify_once", "brief", "missing_information"
    elif bool(value.get("correction_active")):
        posture, cadence, focus = "repair_and_stabilize", "brief", "corrected_point"
    elif bool(value.get("topic_complete")):
        posture, cadence, focus = "acknowledge_and_close", "brief", "closure"
    elif bool(value.get("active_continuity")):
        posture, cadence, focus = "continue_companionably", "natural", "current_topic"
    elif bool(value.get("optional_expansion_allowed")):
        posture, cadence, focus = "answer_with_bounded_insight", "natural", "current_request"
    else:
        posture, cadence, focus = "answer_companionably", "natural", "current_request"
    if posture == "preserve_deliberate_silence":
        continuity_disposition = "preserve_silence"
    elif posture == "acknowledge_and_close":
        continuity_disposition = "settle_closed_topic"
    elif degraded:
        continuity_disposition = "recover_literal_request"
    elif posture == "continue_companionably" and int(value.get("prior_companion_receipts_verified") or 0) > 0:
        continuity_disposition = "resume_verified_companion_context"
    else:
        continuity_disposition = "use_current_turn_only"
    policy = {
        "contract_version": CONTRACT_VERSION,
        "companion_posture": posture,
        "response_cadence": cadence,
        "attention_focus": focus,
        "continuity_disposition": continuity_disposition,
        "prior_companion_continuity_used": continuity_disposition == "resume_verified_companion_context",
        "policy_conflict_suppressed": int(value.get("policy_conflict_count") or 0) > 0,
        "use_current_topic_continuity": posture == "continue_companionably",
        "acknowledge_correction_once": posture == "repair_and_stabilize",
        "maximum_clarifying_questions": 1 if posture == "clarify_once" else 0,
        "maximum_optional_observations": 1 if posture == "answer_with_bounded_insight" else 0,
        "close_without_reopening": posture == "acknowledge_and_close",
        "emit_no_substantive_content": posture == "preserve_deliberate_silence",
        "policy_recovered": degraded,
        "recovery_reason": "invalid_or_degraded_evidence" if degraded else "none",
        "response_turn_only": True,
        "may_initiate_new_turn": False,
        "autonomous_new_turn_permitted": False,
        "tool_intent_selected": False,
        "action_execution_permitted": False,
        "learning_mutation_permitted": False,
        "memory_rewrite_permitted": False,
        "private_reflection_delivery_permitted": False,
        "approval_granted": False,
        "authorization_granted": False,
        "installation_permitted": False,
        "promotion_permitted": False,
        "certification_permitted": False,
        "contains_message_content": False,
        "contains_conversation_text": False,
        "contains_memory_text": False,
        "contains_reflection_text": False,
        "contains_provider_payload": False,
        "contains_private_chain_of_thought": False,
        "evidence_digest": supplied if digest_valid else "",
    }
    policy["policy_digest"] = _digest(policy)
    return policy


def build_daily_companion_runtime_projection(
    message: object,
    response_intent: object,
    conversation_policy: object,
    discourse_policy: object,
    natural_continuity: object,
    natural_follow_up: object,
    governed_speech: object,
    *,
    context_rows: object = None,
    protected_operator_constraints: Iterable[str] = (),
    prior_companion_receipts: object = None,
) -> dict[str, Any]:
    evidence = build_daily_companion_evidence(
        message, response_intent, conversation_policy, discourse_policy,
        natural_continuity, natural_follow_up, governed_speech,
        context_rows=context_rows,
        protected_operator_constraints=protected_operator_constraints,
        prior_companion_receipts=prior_companion_receipts,
    )
    policy = build_daily_companion_policy(evidence)
    public = {k: v for k, v in policy.items() if k not in {"prompt_section"}}
    prompt = '<daily_companion_cognition data_only="true" authority="none">' + json.dumps(public, sort_keys=True, separators=(",", ":")) + '</daily_companion_cognition>'
    if len(prompt) > MAX_PROMPT_CHARS:
        policy = build_daily_companion_policy({})
        public = dict(policy)
        prompt = '<daily_companion_cognition data_only="true" authority="none">' + json.dumps(public, sort_keys=True, separators=(",", ":")) + '</daily_companion_cognition>'
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "companion_posture": policy["companion_posture"],
        "response_cadence": policy["response_cadence"],
        "attention_focus": policy["attention_focus"],
        "continuity_disposition": policy["continuity_disposition"],
        "prior_companion_continuity_used": policy["prior_companion_continuity_used"],
        "policy_conflict_suppressed": policy["policy_conflict_suppressed"],
        "prior_companion_receipts_replayed": evidence["prior_companion_receipts_replayed"],
        "policy_recovered": policy["policy_recovered"],
        "recovery_reason": policy["recovery_reason"],
        "authority": "none",
        "content_free": True,
        "policy_digest": policy["policy_digest"],
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    policy["evidence"] = evidence
    policy["prompt_section"] = prompt
    return {"policy": policy, "prompt_section": prompt, "diagnostics": diagnostics}


def verify_daily_companion_runtime_diagnostics(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    supplied = str(value.get("diagnostics_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "diagnostics_digest"}
    return len(supplied) == 64 and _digest(unsigned) == supplied and value.get("authority") == "none" and value.get("content_free") is True


def audit_daily_companion_response_shape(response_text: object, policy: object) -> dict[str, Any]:
    """Return a transient, content-free compliance receipt for one response.

    The response is inspected only long enough to count structural features. No
    generated text, excerpt, token, provider payload, or semantic summary is
    retained in the returned receipt.
    """
    text = str(response_text or "")
    value = _mapping(policy)
    oversized = len(text) > 12000
    bounded = text[:12000]
    paragraphs = [part for part in bounded.split("\n\n") if part.strip()]
    sentence_count = sum(1 for ch in bounded if ch in ".!?")
    question_count = bounded.count("?")
    non_whitespace = len(bounded.strip())
    posture = str(value.get("companion_posture") or "literal_request_only")
    silence_violation = posture == "preserve_deliberate_silence" and non_whitespace > 0
    clarification_budget = int(value.get("maximum_clarifying_questions") or 0)
    clarification_violation = question_count > clarification_budget
    closure_violation = bool(value.get("close_without_reopening")) and question_count > 0
    observation_budget = int(value.get("maximum_optional_observations") or 0)
    bounded_insight_violation = posture == "answer_with_bounded_insight" and (len(paragraphs) > 2 or sentence_count > 6)
    compliant = not any((oversized, silence_violation, clarification_violation, closure_violation, bounded_insight_violation))
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "companion_posture": posture[:64],
        "response_present": non_whitespace > 0,
        "response_oversized": oversized,
        "paragraph_count": len(paragraphs),
        "sentence_marker_count": sentence_count,
        "question_count": question_count,
        "clarification_budget": clarification_budget,
        "optional_observation_budget": observation_budget,
        "silence_violation": silence_violation,
        "clarification_budget_violation": clarification_violation,
        "closure_reopened": closure_violation,
        "bounded_insight_shape_violation": bounded_insight_violation,
        "compliant": compliant,
        "content_free": True,
        "authority": "none",
        "contains_generated_text": False,
        "contains_provider_payload": False,
        "contains_memory_text": False,
        "contains_reflection_text": False,
        "contains_private_chain_of_thought": False,
    }
    receipt["audit_digest"] = _digest(receipt)
    return receipt


def verify_daily_companion_response_audit(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    supplied = str(value.get("audit_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "audit_digest"}
    return (
        len(supplied) == 64
        and _digest(unsigned) == supplied
        and value.get("content_free") is True
        and value.get("authority") == "none"
        and value.get("contains_generated_text") is False
    )
