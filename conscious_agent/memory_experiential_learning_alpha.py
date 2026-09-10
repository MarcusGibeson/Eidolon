from __future__ import annotations

"""Integrated, content-free memory and experiential-learning alpha projection.

This module reconciles the existing v1165-v1168 runtime projections. It does
not select memory independently, create a second learning path, write memory,
commit lessons, train models, or grant any operational authority.
"""

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from unified_memory_context import verify_unified_memory_runtime_diagnostics
from memory_retrieval_relevance import verify_memory_retrieval_diagnostics
from immediate_memory_learning import (
    verify_immediate_memory_learning_diagnostics,
    verify_learning_commit_boundary_handoff,
)
from bounded_experiential_lessons import (
    verify_bounded_experiential_lesson_diagnostics,
    verify_lesson_review_boundary_handoff,
)

CONTRACT_VERSION = "1169.8"
MAX_COMPONENT_BYTES = 262_144
MAX_SELECTED_RECORDS = 12
MAX_PROMPT_CHARS = 3600
MAX_DOMAIN_COUNT = 5

MAX_PRIOR_ALPHA_RECEIPTS = 64
MAX_RECEIPT_BYTES = 16_384
MAX_RELIABILITY_FAULTS = 128

_HANDOFF_FIELDS = {
    "contract_version", "alpha_posture", "continuity_disposition", "selected_count",
    "learning_candidate_type", "lesson_candidate_type", "provider_completed",
    "assistant_memory_committed", "eligible_for_future_structural_continuity",
    "memory_mutation_performed", "lesson_commit_performed",
    "model_training_performed", "model_weights_changed", "authority",
    "content_free", "policy_digest", "receipt_digest",
}
_AUDIT_FIELDS = {
    "contract_version", "compliant", "violation_count", "authority_violation_count",
    "private_field_violation_count", "prompt_injection_count", "content_free",
    "memory_mutation_observed", "lesson_commit_observed", "model_training_observed",
    "model_weights_changed", "authority", "policy_digest", "audit_digest",
}
MEMORY_DOMAINS = ("conversational", "episodic", "semantic", "relationship", "project")
FRESHNESS_BANDS = ("current", "recent", "historical", "archival", "unknown")
LEARNING_TYPES = ("none", "correction", "retraction", "preference_change")
LEARNING_SCOPES = ("none", "temporary", "durable_candidate")
LESSON_TYPES = (
    "none", "corrective_lesson", "retraction_lesson", "preference_lesson",
    "repair_lesson", "failure_avoidance_lesson", "repeatable_success_lesson",
)

_AUTHORITY_FIELDS = {
    "approval_granted", "approved", "authorized", "authorization_granted",
    "execute", "execution_permitted", "action_execution_permitted",
    "tool_use_permitted", "training_permitted", "model_training_permitted",
    "self_training_permitted", "memory_mutation_permitted", "automatic_learning_permitted",
    "automatic_generalization_permitted", "durable_commit_permitted",
    "installation_permitted", "promotion_permitted", "certification_permitted",
    "autonomous_action_performed", "may_initiate_new_turn",
}
_PRIVATE_FIELDS = {
    "private_chain_of_thought", "chain_of_thought", "hidden_reasoning",
    "provider_payload", "raw_prompt", "raw_provider_response", "prompt",
    "conversation_text", "experience_text", "lesson_content", "memory_content",
}
_PROMPT_INJECTION = re.compile(r"<\s*/?\s*(?:system|assistant|developer|tool|memory_experiential_learning_alpha)\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return list(value)


def _bounded_json_bytes(value: object) -> tuple[int, bool]:
    try:
        size = len(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))
    except Exception:
        return MAX_COMPONENT_BYTES + 1, True
    return size, size > MAX_COMPONENT_BYTES


def _valid_digest(value: object, field: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get(field) or "")
    unsigned = {key: item for key, item in value.items() if key != field}
    return len(supplied) == 64 and _digest(unsigned) == supplied


def _exact_fields(value: object, expected: set[str]) -> bool:
    return isinstance(value, Mapping) and set(value.keys()) == expected


def _bounded_count(value: object, maximum: int = MAX_RELIABILITY_FAULTS) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum


def _receipt_size_valid(value: object) -> bool:
    size, oversized = _bounded_json_bytes(value)
    return not oversized and size <= MAX_RECEIPT_BYTES


def _scan_structural(value: object) -> tuple[int, int, int]:
    """Return authority, private-field, and prompt-injection violations."""
    authority = private = injection = 0
    stack = [value]
    visited = 0
    while stack and visited < 4096:
        current = stack.pop()
        visited += 1
        if isinstance(current, Mapping):
            for key, item in current.items():
                token = str(key).strip().lower()
                if token in _AUTHORITY_FIELDS and not (item is False or item is None or item == "" or item == 0):
                    authority += 1
                if token in _PRIVATE_FIELDS:
                    private += 1
                stack.append(item)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(list(current)[:256])
        elif isinstance(current, str) and _PROMPT_INJECTION.search(current):
            injection += 1
    return authority, private, injection


def _component_status(
    projection: object,
    diagnostics_verifier: Any,
) -> dict[str, Any]:
    malformed = not isinstance(projection, Mapping)
    value = _mapping(projection)
    policy = value.get("policy")
    evidence = value.get("evidence")
    diagnostics = value.get("diagnostics")
    candidate = value.get("candidate")
    size, oversized = _bounded_json_bytes(value)
    policy_valid = _valid_digest(policy, "policy_digest")
    evidence_valid = _valid_digest(evidence, "evidence_digest")
    diagnostics_valid = bool(diagnostics_verifier(diagnostics))
    authority, private, injection = _scan_structural((policy, evidence, diagnostics, candidate))
    internal_authority, internal_private, internal_injection = _scan_structural((
        value.get("selected_memory_records"), value.get("selected_references"), value.get("decisions"),
    ))
    authority += internal_authority
    private += internal_private
    injection += internal_injection
    recovered = bool(isinstance(policy, Mapping) and policy.get("policy_recovered") is True)
    valid = not any((
        malformed, oversized, not policy_valid, not evidence_valid, not diagnostics_valid,
        authority, private, injection,
    ))
    return {
        "valid": valid,
        "malformed": malformed,
        "oversized": oversized,
        "component_bytes": min(size, MAX_COMPONENT_BYTES + 1),
        "policy_valid": policy_valid,
        "evidence_valid": evidence_valid,
        "diagnostics_valid": diagnostics_valid,
        "authority_violation_count": authority,
        "private_field_violation_count": private,
        "prompt_injection_count": injection,
        "policy_recovered": recovered,
    }


def _record_key(record: Mapping[str, Any]) -> str:
    for key in ("preference_key", "fact_key", "subject_key", "memory_key", "semantic_key"):
        token = re.sub(r"[^a-z0-9_.:-]+", "_", str(record.get(key) or "").strip().lower()).strip("_")
        if token:
            return token[:120]
    return ""


def _record_content_digest(record: Mapping[str, Any]) -> str:
    parts = []
    for key in ("content", "thought", "summary", "title", "name", "description", "value"):
        value = record.get(key)
        if value not in {None, ""}:
            parts.append(str(value))
    text = " ".join(" ".join(parts).split())[:1200]
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""


def _reference_for_record(record: Mapping[str, Any], references: Sequence[Any], fallback_index: int) -> dict[str, Any]:
    content_digest = _record_content_digest(record)
    if content_digest:
        for reference in references:
            if isinstance(reference, Mapping) and str(reference.get("content_digest") or "") == content_digest:
                return dict(reference)
    if 0 <= fallback_index < len(references) and isinstance(references[fallback_index], Mapping):
        return dict(references[fallback_index])
    domain = str(record.get("memory_domain") or "")
    return {
        "domain": domain if domain in MEMORY_DOMAINS else "",
        "age_band": "unknown",
        "confidence_band": "unknown",
        "authority": "none",
    }


def _selected_pairs(unified: Mapping[str, Any], retrieval: Mapping[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    source_records = _sequence(unified.get("selected_memory_records"))
    source_refs = _sequence(unified.get("selected_references"))
    decisions = _sequence(retrieval.get("decisions"))
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for decision in decisions:
        if not isinstance(decision, Mapping) or decision.get("selected") is not True:
            continue
        try:
            index = int(decision.get("candidate_index"))
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(source_records):
            continue
        record = source_records[index]
        if isinstance(record, Mapping):
            pairs.append((dict(record), _reference_for_record(record, source_refs, index)))
    # Retain compatibility if a fixture supplies selected rows without decisions.
    if not pairs and not decisions:
        for index, record in enumerate(_sequence(retrieval.get("selected_memory_records"))[:MAX_SELECTED_RECORDS]):
            if isinstance(record, Mapping):
                pairs.append((dict(record), _reference_for_record(record, source_refs, index)))
    return pairs[:MAX_SELECTED_RECORDS]


def _expected_lesson_type(learning_type: str) -> str:
    return {
        "correction": "corrective_lesson",
        "retraction": "retraction_lesson",
        "preference_change": "preference_lesson",
    }.get(learning_type, "none")


def build_memory_experiential_learning_alpha(
    unified_memory_projection: object,
    memory_retrieval_projection: object,
    immediate_learning_projection: object,
    bounded_lesson_projection: object,
    *,
    learning_commit_handoff: object = None,
    lesson_review_handoff: object = None,
    prior_alpha_receipts: object = None,
) -> dict[str, Any]:
    """Reconcile v1165-v1168 into one bounded ordinary-conversation projection."""
    unified = _mapping(unified_memory_projection)
    retrieval = _mapping(memory_retrieval_projection)
    learning = _mapping(immediate_learning_projection)
    lesson = _mapping(bounded_lesson_projection)

    statuses = {
        "unified_memory": _component_status(unified_memory_projection, verify_unified_memory_runtime_diagnostics),
        "retrieval": _component_status(memory_retrieval_projection, verify_memory_retrieval_diagnostics),
        "immediate_learning": _component_status(immediate_learning_projection, verify_immediate_memory_learning_diagnostics),
        "bounded_lesson": _component_status(bounded_lesson_projection, verify_bounded_experiential_lesson_diagnostics),
    }
    invalid_components = sum(not item["valid"] for item in statuses.values())
    recovered_components = sum(item["policy_recovered"] for item in statuses.values())

    unified_policy = _mapping(unified.get("policy"))
    retrieval_policy = _mapping(retrieval.get("policy"))
    learning_policy = _mapping(learning.get("policy"))
    lesson_policy = _mapping(lesson.get("policy"))
    learning_candidate = _mapping(learning.get("candidate"))
    lesson_candidate = _mapping(lesson.get("candidate"))

    learning_type = str(learning_policy.get("candidate_type") or "none")
    learning_scope = str(learning_policy.get("candidate_scope") or "none")
    lesson_type = str(lesson_policy.get("lesson_type") or "none")
    enum_invalid = False
    if learning_type not in LEARNING_TYPES:
        learning_type = "none"
        enum_invalid = True
    if learning_scope not in LEARNING_SCOPES:
        learning_scope = "none"
        enum_invalid = True
    if lesson_type not in LESSON_TYPES:
        lesson_type = "none"
        enum_invalid = True
    invalid_components = min(4, invalid_components + int(enum_invalid))

    unified_records = _sequence(unified.get("selected_memory_records"))
    unified_references = _sequence(unified.get("selected_references"))
    retrieval_records = _sequence(retrieval.get("selected_memory_records"))
    retrieval_decisions = _sequence(retrieval.get("decisions"))
    selected_decisions = [row for row in retrieval_decisions if isinstance(row, Mapping) and row.get("selected") is True]
    retrieval_projection_coherent = (
        len(unified_records) <= 80
        and len(unified_references) >= len(unified_records)
        and len(retrieval_records) == int(retrieval_policy.get("selected_count") or 0)
        and len(selected_decisions) == len(retrieval_records)
    )
    if retrieval_projection_coherent:
        for output_index, decision in enumerate(selected_decisions):
            try:
                source_index = int(decision.get("candidate_index"))
            except (TypeError, ValueError):
                retrieval_projection_coherent = False
                break
            if source_index < 0 or source_index >= len(unified_records):
                retrieval_projection_coherent = False
                break
            if not isinstance(retrieval_records[output_index], Mapping) or dict(retrieval_records[output_index]) != dict(unified_records[source_index]):
                retrieval_projection_coherent = False
                break
    learning_projection_coherent = (
        (not learning_candidate and learning_type == "none" and learning_scope == "none")
        or (
            bool(learning_candidate)
            and str(learning_candidate.get("candidate_type") or "none") == learning_type
            and str(learning_candidate.get("scope") or "none") == learning_scope
            and learning_candidate.get("current_turn_precedence") is True
            and learning_candidate.get("historical_truth_preserved") is True
            and learning_candidate.get("mutation_requested") is False
            and learning_candidate.get("requires_commit_boundary") is True
        )
    )
    lesson_projection_coherent = (
        (not lesson_candidate and lesson_type == "none")
        or (
            bool(lesson_candidate)
            and str(lesson_candidate.get("lesson_type") or "none") == lesson_type
            and lesson_candidate.get("review_required") is True
            and lesson_candidate.get("historical_truth_preserved") is True
            and lesson_candidate.get("memory_mutation_performed") is False
            and lesson_candidate.get("model_training_performed") is False
            and lesson_candidate.get("self_training_permitted") is False
        )
    )
    component_coherence_failures = sum(not value for value in (
        retrieval_projection_coherent, learning_projection_coherent, lesson_projection_coherent,
    ))

    continuity_values = {
        str(unified_policy.get("continuity_disposition") or ""),
        str(retrieval_policy.get("continuity_disposition") or ""),
        str(learning_policy.get("continuity_disposition") or ""),
        str(lesson_policy.get("continuity_disposition") or ""),
    }
    recovery_continuity = any("recover" in value for value in continuity_values)
    resumed_continuity = any(value.startswith("resume_verified") for value in continuity_values)

    explicit_receipt_conflicts = sum(bool(value) for value in (
        learning_policy.get("conflicting_prior_learning_receipts"),
        lesson_policy.get("conflicting_prior_lesson_receipts"),
    ))
    memory_learning_receipt_conflict = bool(recovery_continuity and resumed_continuity)
    retrieval_lesson_receipt_conflict = bool(
        retrieval_policy.get("prior_receipts_rejected")
        and lesson_policy.get("verified_prior_lesson_receipts")
    )
    cross_system_conflicts = explicit_receipt_conflicts + int(memory_learning_receipt_conflict) + int(retrieval_lesson_receipt_conflict)

    replayed_receipts = sum(int(value or 0) for value in (
        unified_policy.get("prior_receipts_replayed"),
        retrieval_policy.get("prior_receipts_replayed"),
        learning_policy.get("replayed_prior_learning_receipts"),
        lesson_policy.get("replayed_prior_lesson_receipts"),
    ))
    tampered_receipts = sum(int(value or 0) for value in (
        unified_policy.get("prior_receipts_rejected"),
        retrieval_policy.get("prior_receipts_rejected"),
        learning_policy.get("tampered_prior_learning_receipts"),
        lesson_policy.get("tampered_prior_lesson_receipts"),
    ))

    lesson_mismatch = False
    expected_lesson = _expected_lesson_type(learning_type)
    if learning_scope == "temporary" and lesson_candidate:
        lesson_mismatch = True
    elif lesson_candidate and learning_type in {"correction", "retraction", "preference_change"}:
        if lesson_type in {"corrective_lesson", "retraction_lesson", "preference_lesson"}:
            lesson_mismatch = lesson_type != expected_lesson
    elif lesson_candidate and lesson_type in {"corrective_lesson", "retraction_lesson", "preference_lesson"} and not learning_candidate:
        lesson_mismatch = True

    residual_state = bool(
        (statuses["unified_memory"]["policy_recovered"] and unified.get("selected_memory_records"))
        or (statuses["retrieval"]["policy_recovered"] and retrieval.get("selected_memory_records"))
        or (statuses["immediate_learning"]["policy_recovered"] and learning_candidate)
        or (statuses["bounded_lesson"]["policy_recovered"] and lesson_candidate)
    )

    full_recovery = bool(
        invalid_components or recovered_components or component_coherence_failures
        or cross_system_conflicts or tampered_receipts or lesson_mismatch or residual_state
    )

    pairs = [] if full_recovery else _selected_pairs(unified, retrieval)
    target_key = str(learning_candidate.get("target_key") or "unresolved") if learning_candidate else "unresolved"
    precedence_suppressed = 0
    effective_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record, reference in pairs:
        record_key = _record_key(record)
        freshness = str(reference.get("age_band") or "unknown")
        suppress = False
        if learning_candidate:
            if target_key == "unresolved" and learning_type in {"correction", "retraction"}:
                suppress = True
            elif target_key != "unresolved" and record_key == target_key:
                suppress = True
            elif learning_type in {"correction", "retraction"} and freshness in {"historical", "archival", "unknown"}:
                suppress = True
        if suppress:
            precedence_suppressed += 1
        else:
            effective_pairs.append((record, reference))

    effective_lesson_candidate = dict(lesson_candidate) if lesson_candidate and not full_recovery else None
    lesson_subordinate = False
    if effective_lesson_candidate and learning_candidate:
        if lesson_type in {"repair_lesson", "failure_avoidance_lesson", "repeatable_success_lesson"}:
            effective_lesson_candidate = None
            lesson_subordinate = True
        elif learning_scope == "temporary":
            effective_lesson_candidate = None
            lesson_subordinate = True

    selected_records = [record for record, _ in effective_pairs][:MAX_SELECTED_RECORDS]
    selected_refs = [reference for _, reference in effective_pairs][:MAX_SELECTED_RECORDS]
    domains = sorted({str(ref.get("domain")) for ref in selected_refs if str(ref.get("domain")) in MEMORY_DOMAINS})
    freshness_counts = {band: 0 for band in FRESHNESS_BANDS}
    for ref in selected_refs:
        band = str(ref.get("age_band") or "unknown")
        freshness_counts[band if band in freshness_counts else "unknown"] += 1

    learning_handoff_valid = learning_commit_handoff is None or verify_learning_commit_boundary_handoff(learning_commit_handoff)
    lesson_handoff_valid = lesson_review_handoff is None or verify_lesson_review_boundary_handoff(lesson_review_handoff)
    handoff_recovery = not learning_handoff_valid or not lesson_handoff_valid
    prior_alpha = validate_prior_memory_experiential_learning_alpha_receipts(prior_alpha_receipts)
    if prior_alpha["recovery_required"]:
        handoff_recovery = True
    if handoff_recovery:
        full_recovery = True
        selected_records = []
        domains = []
        freshness_counts = {band: 0 for band in FRESHNESS_BANDS}
        effective_lesson_candidate = None

    learning_review_eligible = bool(
        learning_candidate
        and learning_scope == "durable_candidate"
        and isinstance(learning_commit_handoff, Mapping)
        and learning_commit_handoff.get("eligible_for_existing_commit_review") is True
        and learning_handoff_valid
        and not full_recovery
    )
    lesson_review_eligible = bool(
        effective_lesson_candidate
        and isinstance(lesson_review_handoff, Mapping)
        and lesson_review_handoff.get("eligible_for_operator_review") is True
        and lesson_handoff_valid
        and not full_recovery
    )

    if full_recovery:
        posture = "literal_current_request_only_recovery"
        continuity = "literal_current_request_only"
        learning_type_public = "none"
        learning_scope_public = "none"
        lesson_type_public = "none"
    else:
        learning_type_public = learning_type
        learning_scope_public = learning_scope
        lesson_type_public = str(effective_lesson_candidate.get("lesson_type") or "none") if effective_lesson_candidate else "none"
        if learning_candidate:
            posture = "current_change_precedence"
        elif selected_records and effective_lesson_candidate:
            posture = "memory_grounded_with_bounded_lesson"
        elif selected_records:
            posture = "memory_grounded"
        elif effective_lesson_candidate:
            posture = "bounded_lesson_review_candidate"
        else:
            posture = "literal_current_request"
        verified_receipts = sum(int(value or 0) for value in (
            unified_policy.get("prior_receipts_verified"),
            retrieval_policy.get("prior_receipts_verified"),
            learning_policy.get("verified_prior_learning_receipts"),
            lesson_policy.get("verified_prior_lesson_receipts"),
        ))
        verified_receipts += int(prior_alpha["verified_receipt_count"])
        replayed_receipts += int(prior_alpha["replayed_receipt_count"])
        continuity = "resume_verified_alpha_context" if verified_receipts and not replayed_receipts else "use_current_turn_alpha"

    evidence = {
        "contract_version": CONTRACT_VERSION,
        "component_count": 4,
        "valid_component_count": 4 - invalid_components,
        "invalid_component_count": invalid_components,
        "recovered_component_count": recovered_components,
        "component_coherence_failure_count": component_coherence_failures,
        "selected_count": len(selected_records),
        "selected_domain_count": min(len(domains), MAX_DOMAIN_COUNT),
        "selected_domains": domains[:MAX_DOMAIN_COUNT],
        "freshness_band_counts": freshness_counts,
        "precedence_suppressed_count": precedence_suppressed,
        "retrieval_stale_suppressed_count": int(retrieval_policy.get("stale_suppressed_count") or 0),
        "learning_candidate_count": int(bool(learning_candidate and not full_recovery)),
        "lesson_candidate_count": int(bool(effective_lesson_candidate)),
        "learning_review_eligible": learning_review_eligible,
        "lesson_review_eligible": lesson_review_eligible,
        "lesson_subordinate_to_current_change": lesson_subordinate,
        "replayed_receipt_count": replayed_receipts,
        "tampered_receipt_count": tampered_receipts,
        "cross_system_conflict_count": cross_system_conflicts + int(lesson_mismatch),
        "residual_state_detected": residual_state,
        "handoff_recovery": handoff_recovery,
        "prior_alpha_receipt_count": int(prior_alpha["verified_receipt_count"]),
        "prior_alpha_replay_count": int(prior_alpha["replayed_receipt_count"]),
        "provenance_complete": bool(unified_policy.get("provenance_complete")) and not full_recovery,
        "provenance_source_count": int(unified_policy.get("provenance_source_count") or 0) if not full_recovery else 0,
        "historical_truth_preserved": True,
        "literal_current_request_precedence": True,
        "memory_mutation_performed": False,
        "lesson_commit_performed": False,
        "model_training_performed": False,
        "model_weights_changed": False,
        "provider_contacted": False,
        "contains_memory_content": False,
        "contains_correction_value": False,
        "contains_preference_value": False,
        "contains_lesson_content": False,
        "contains_experience_text": False,
        "contains_conversation_text": False,
        "contains_private_reasoning": False,
        "authority": "none",
        "integrity": "degraded" if full_recovery else "valid",
    }
    evidence["evidence_digest"] = _digest(evidence)

    policy = {
        "contract_version": CONTRACT_VERSION,
        "alpha_posture": posture,
        "continuity_disposition": continuity,
        "selected_domains": domains[:MAX_DOMAIN_COUNT] if not full_recovery else [],
        "selected_count": len(selected_records),
        "freshness_bands_present": [band for band in FRESHNESS_BANDS if freshness_counts[band]],
        "learning_candidate_type": learning_type_public,
        "learning_candidate_scope": learning_scope_public,
        "lesson_candidate_type": lesson_type_public,
        "learning_review_eligible": learning_review_eligible,
        "lesson_review_eligible": lesson_review_eligible,
        "literal_current_request_precedence": True,
        "explicit_correction_precedence": True,
        "explicit_retraction_precedence": True,
        "temporary_scope_bounded": True,
        "stale_memory_may_dominate": False,
        "lesson_may_override_current_change": False,
        "historical_truth_preserved": True,
        "memory_selection_separate_from_learning": True,
        "lesson_nomination_separate_from_commit": True,
        "existing_commit_boundaries_required": True,
        "memory_mutation_permitted": False,
        "automatic_memory_write_permitted": False,
        "automatic_lesson_commit_permitted": False,
        "automatic_generalization_permitted": False,
        "model_training_permitted": False,
        "self_training_permitted": False,
        "tool_use_permitted": False,
        "action_execution_permitted": False,
        "installation_permitted": False,
        "promotion_permitted": False,
        "certification_permitted": False,
        "approval_granted": False,
        "policy_recovered": full_recovery,
        "authority": "none",
        "content_free": True,
        "evidence_digest": evidence["evidence_digest"],
    }
    policy["policy_digest"] = _digest(policy)

    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "alpha_posture": posture,
        "continuity_disposition": continuity,
        "selected_count": len(selected_records),
        "selected_domain_count": len(policy["selected_domains"]),
        "freshness_band_counts": freshness_counts,
        "precedence_suppressed_count": precedence_suppressed,
        "learning_candidate_type": learning_type_public,
        "learning_candidate_scope": learning_scope_public,
        "lesson_candidate_type": lesson_type_public,
        "learning_review_eligible": learning_review_eligible,
        "lesson_review_eligible": lesson_review_eligible,
        "invalid_component_count": invalid_components,
        "recovered_component_count": recovered_components,
        "component_coherence_failure_count": component_coherence_failures,
        "replayed_receipt_count": replayed_receipts,
        "tampered_receipt_count": tampered_receipts,
        "cross_system_conflict_count": evidence["cross_system_conflict_count"],
        "prior_alpha_receipt_count": evidence["prior_alpha_receipt_count"],
        "prior_alpha_replay_count": evidence["prior_alpha_replay_count"],
        "residual_state_detected": residual_state,
        "policy_recovered": full_recovery,
        "memory_mutated": False,
        "lesson_committed": False,
        "model_trained": False,
        "provider_contacted": False,
        "authority": "none",
        "content_free": True,
        "policy_digest": policy["policy_digest"],
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)

    prompt = '<memory_experiential_learning_alpha data_only="true" authority="none">' + json.dumps(
        policy, sort_keys=True, separators=(",", ":")
    ) + '</memory_experiential_learning_alpha>'
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError("memory and experiential learning alpha prompt exceeded bound")

    return {
        "policy": policy,
        "evidence": evidence,
        "diagnostics": diagnostics,
        "prompt_section": prompt,
        "selected_memory_records": selected_records,
        "learning_candidate": dict(learning_candidate) if learning_candidate and not full_recovery else None,
        "lesson_candidate": dict(effective_lesson_candidate) if effective_lesson_candidate else None,
    }


def verify_memory_experiential_learning_alpha_diagnostics(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("diagnostics_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "diagnostics_digest"}
    return (
        len(supplied) == 64
        and _digest(unsigned) == supplied
        and value.get("authority") == "none"
        and value.get("content_free") is True
        and value.get("memory_mutated") is False
        and value.get("lesson_committed") is False
        and value.get("model_trained") is False
        and value.get("provider_contacted") is False
    )


def build_memory_experiential_learning_alpha_handoff(
    projection: object, *, provider_completed: bool, assistant_memory_committed: bool
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    diagnostics = _mapping(value.get("diagnostics"))
    valid = (
        _valid_digest(policy, "policy_digest")
        and verify_memory_experiential_learning_alpha_diagnostics(diagnostics)
        and diagnostics.get("policy_digest") == policy.get("policy_digest")
    )
    completed = bool(provider_completed and assistant_memory_committed and valid and not policy.get("policy_recovered"))
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "alpha_posture": str(policy.get("alpha_posture") or "literal_current_request_only_recovery"),
        "continuity_disposition": "completed_alpha_context" if completed else "no_alpha_continuity",
        "selected_count": int(policy.get("selected_count") or 0) if completed else 0,
        "learning_candidate_type": str(policy.get("learning_candidate_type") or "none") if completed else "none",
        "lesson_candidate_type": str(policy.get("lesson_candidate_type") or "none") if completed else "none",
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_future_structural_continuity": completed,
        "memory_mutation_performed": False,
        "lesson_commit_performed": False,
        "model_training_performed": False,
        "model_weights_changed": False,
        "authority": "none",
        "content_free": True,
        "policy_digest": str(policy.get("policy_digest") or "") if valid else "",
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def verify_memory_experiential_learning_alpha_handoff(value: object) -> bool:
    if not _exact_fields(value, _HANDOFF_FIELDS) or not _receipt_size_valid(value):
        return False
    supplied = str(value.get("receipt_digest") or "")
    unsigned = {k: v for k, v in value.items() if k != "receipt_digest"}
    posture = str(value.get("alpha_posture") or "")
    continuity = str(value.get("continuity_disposition") or "")
    selected_count = value.get("selected_count")
    eligible = value.get("eligible_for_future_structural_continuity")
    coherent_completion = (
        eligible is False
        or (
            eligible is True
            and value.get("provider_completed") is True
            and value.get("assistant_memory_committed") is True
            and continuity == "completed_alpha_context"
            and posture != "literal_current_request_only_recovery"
        )
    )
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == CONTRACT_VERSION
        and posture in {"literal_current_request_only_recovery", "current_change_precedence", "memory_grounded_with_bounded_lesson", "memory_grounded", "bounded_lesson_review_candidate", "literal_current_request"}
        and continuity in {"completed_alpha_context", "no_alpha_continuity"}
        and _bounded_count(selected_count, MAX_SELECTED_RECORDS)
        and isinstance(value.get("provider_completed"), bool)
        and isinstance(value.get("assistant_memory_committed"), bool)
        and isinstance(eligible, bool) and coherent_completion
        and value.get("authority") == "none" and value.get("content_free") is True
        and value.get("memory_mutation_performed") is False
        and value.get("lesson_commit_performed") is False
        and value.get("model_training_performed") is False
        and value.get("model_weights_changed") is False
        and len(str(value.get("policy_digest") or "")) in {0, 64}
    )


def validate_prior_memory_experiential_learning_alpha_receipts(rows: object) -> dict[str, Any]:
    raw_rows = _sequence(rows)
    receipts = []
    ignored = max(0, len(raw_rows) - MAX_PRIOR_ALPHA_RECEIPTS)
    oversized = 0
    malformed = 0
    for row in raw_rows[:MAX_PRIOR_ALPHA_RECEIPTS]:
        if not isinstance(row, Mapping):
            malformed += 1
            continue
        if "memory_experiential_learning_alpha_handoff" in row:
            candidate = row.get("memory_experiential_learning_alpha_handoff")
        elif "receipt_digest" in row and "eligible_for_future_structural_continuity" in row:
            candidate = row
        else:
            # Transcript and operation rows are not alpha receipts. Only a row
            # that declares this protocol can be malformed or tampered.
            continue
        if not isinstance(candidate, Mapping):
            malformed += 1
            continue
        if not _receipt_size_valid(candidate):
            oversized += 1
            continue
        receipts.append(dict(candidate))
    valid = [r for r in receipts if verify_memory_experiential_learning_alpha_handoff(r) and r.get("eligible_for_future_structural_continuity") is True]
    digests = [str(r.get("receipt_digest")) for r in valid]
    unique = list(dict.fromkeys(digests))
    replayed = max(0, len(digests) - len(unique))
    policy_digests = {str(r.get("policy_digest") or "") for r in valid if r.get("policy_digest")}
    conflicting = len(policy_digests) > 1
    tampered = sum(1 for r in receipts if not verify_memory_experiential_learning_alpha_handoff(r))
    recovery_required = bool(tampered or conflicting or oversized or malformed or ignored)
    return {
        "verified_receipt_count": len(unique) if not conflicting else 0,
        "replayed_receipt_count": replayed,
        "tampered_receipt_count": tampered,
        "oversized_receipt_count": oversized,
        "malformed_receipt_count": malformed,
        "ignored_receipt_count": ignored,
        "conflicting_receipts": conflicting,
        "receipt_budget_exceeded": bool(ignored),
        "recovery_required": recovery_required,
    }


def audit_memory_experiential_learning_alpha(projection: object, handoff: object = None) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    diagnostics = _mapping(value.get("diagnostics"))
    violations = 0
    violations += int(not _valid_digest(policy, "policy_digest"))
    violations += int(not _valid_digest(evidence, "evidence_digest"))
    violations += int(not verify_memory_experiential_learning_alpha_diagnostics(diagnostics))
    if handoff is not None:
        violations += int(not verify_memory_experiential_learning_alpha_handoff(handoff))
    authority, private, injection = _scan_structural((policy, evidence, diagnostics, handoff))
    violations += authority + private + injection
    audit = {
        "contract_version": CONTRACT_VERSION,
        "compliant": violations == 0,
        "violation_count": violations,
        "authority_violation_count": authority,
        "private_field_violation_count": private,
        "prompt_injection_count": injection,
        "content_free": True,
        "memory_mutation_observed": False,
        "lesson_commit_observed": False,
        "model_training_observed": False,
        "model_weights_changed": False,
        "authority": "none",
        "policy_digest": str(policy.get("policy_digest") or ""),
    }
    audit["audit_digest"] = _digest(audit)
    return audit


def verify_memory_experiential_learning_alpha_audit(value: object) -> bool:
    if not _exact_fields(value, _AUDIT_FIELDS) or not _receipt_size_valid(value):
        return False
    supplied = str(value.get("audit_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "audit_digest"}
    counts_valid = all(_bounded_count(value.get(field)) for field in (
        "violation_count", "authority_violation_count", "private_field_violation_count",
        "prompt_injection_count",
    ))
    component_sum = sum(int(value.get(field) or 0) for field in (
        "authority_violation_count", "private_field_violation_count", "prompt_injection_count",
    ))
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == CONTRACT_VERSION
        and counts_valid and int(value.get("violation_count") or 0) >= component_sum
        and value.get("compliant") is (value.get("violation_count") == 0)
        and value.get("content_free") is True and value.get("authority") == "none"
        and value.get("memory_mutation_observed") is False
        and value.get("lesson_commit_observed") is False
        and value.get("model_training_observed") is False
        and value.get("model_weights_changed") is False
        and len(str(value.get("policy_digest") or "")) in {0, 64}
    )


def build_memory_experiential_learning_alpha_reliability(
    projection: object, handoff: object, audit: object, *, prior_alpha_receipts: object = None
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    diagnostics = _mapping(value.get("diagnostics"))
    prior = validate_prior_memory_experiential_learning_alpha_receipts(prior_alpha_receipts)
    projection_valid = (
        _valid_digest(policy, "policy_digest")
        and verify_memory_experiential_learning_alpha_diagnostics(diagnostics)
        and diagnostics.get("policy_digest") == policy.get("policy_digest")
    )
    handoff_valid = verify_memory_experiential_learning_alpha_handoff(handoff)
    audit_valid = verify_memory_experiential_learning_alpha_audit(audit)
    recovered = bool(policy.get("policy_recovered"))
    residual = bool(
        recovered and (value.get("selected_memory_records") or value.get("learning_candidate") or value.get("lesson_candidate"))
    )
    fault_count = sum((
        int(not projection_valid), int(not handoff_valid), int(not audit_valid), int(recovered), int(residual),
        int(prior["recovery_required"]),
    ))
    ready = fault_count == 0
    report = {
        "contract_version": CONTRACT_VERSION,
        "reliability_posture": "alpha_context_reliable" if ready else "literal_current_request_only_recovery",
        "ordinary_conversation_ready": ready,
        "projection_valid": projection_valid,
        "handoff_valid": handoff_valid,
        "audit_valid": audit_valid,
        "prior_continuity_valid": not prior["recovery_required"],
        "recovered_projection": recovered,
        "residual_state_detected": residual,
        "fault_count": min(fault_count, MAX_RELIABILITY_FAULTS),
        "verified_prior_receipt_count": int(prior["verified_receipt_count"]),
        "replayed_prior_receipt_count": int(prior["replayed_receipt_count"]),
        "tampered_prior_receipt_count": int(prior["tampered_receipt_count"]),
        "oversized_prior_receipt_count": int(prior["oversized_receipt_count"]),
        "malformed_prior_receipt_count": int(prior["malformed_receipt_count"]),
        "ignored_prior_receipt_count": int(prior["ignored_receipt_count"]),
        "selected_count": int(policy.get("selected_count") or 0) if ready else 0,
        "learning_candidate_available": bool(value.get("learning_candidate")) if ready else False,
        "lesson_candidate_available": bool(value.get("lesson_candidate")) if ready else False,
        "literal_current_request_precedence": True,
        "historical_truth_preserved": True,
        "memory_mutation_performed": False,
        "lesson_commit_performed": False,
        "model_training_performed": False,
        "model_weights_changed": False,
        "authority": "none",
        "content_free": True,
        "policy_digest": str(policy.get("policy_digest") or "") if projection_valid else "",
    }
    report["reliability_digest"] = _digest(report)
    return report


def verify_memory_experiential_learning_alpha_reliability(value: object) -> bool:
    if not isinstance(value, Mapping) or not _receipt_size_valid(value):
        return False
    supplied = str(value.get("reliability_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "reliability_digest"}
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("contract_version") == CONTRACT_VERSION
        and value.get("authority") == "none" and value.get("content_free") is True
        and value.get("literal_current_request_precedence") is True
        and value.get("historical_truth_preserved") is True
        and value.get("memory_mutation_performed") is False
        and value.get("lesson_commit_performed") is False
        and value.get("model_training_performed") is False
        and value.get("model_weights_changed") is False
        and _bounded_count(value.get("fault_count"))
    )
