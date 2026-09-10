from __future__ import annotations

"""Bounded authority-free correction, retraction, and preference-change learning foundations for v1167."""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "1167.8"
MAX_PRIOR_RECEIPTS = 16
MAX_PRIOR_RECEIPT_BYTES = 24000
MAX_MESSAGE_CHARS = 4000
MAX_CANDIDATES = 24
MAX_PROMPT_CHARS = 2800
_AUTHORITY = {"approval_granted", "authorized", "execute", "execution_permitted", "tool_use_permitted", "installation_permitted", "promotion_permitted", "certification_permitted"}
_PRIVATE = {"private_chain_of_thought", "chain_of_thought", "hidden_reasoning", "provider_payload", "raw_prompt", "raw_provider_response"}

_CORRECTION_PATTERNS = (
    r"\b(?:actually|correction|to correct that|i meant|that's wrong|that is wrong|not .{0,40},? (?:but|it's|it is)|stop calling me|don't call me|do not call me|never call me|stop using)\b",
)
_RETRACTION_PATTERNS = (
    r"\b(?:forget that|disregard that|ignore what i said|scratch that|i take that back|retract that|that no longer applies)\b",
)
_PREFERENCE_PATTERNS = (
    r"\b(?:from now on|going forward|i prefer|my preference is|please use|please don't|do not use|i no longer prefer|i changed my mind|stop calling me|don't call me|do not call me|never call me|stop using)\b",
)
_TEMPORARY_PATTERNS = (r"\b(?:for now|this time|today only|just this once|temporarily)\b",)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _match_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _safe_key(value: object) -> str:
    token = re.sub(r"[^a-z0-9_.:-]+", "_", str(value or "").strip().lower()).strip("_")
    return token[:120]


@dataclass(frozen=True)
class LearningCandidate:
    candidate_type: str
    target_key: str
    scope: str
    current_turn_precedence: bool
    historical_truth_preserved: bool
    mutation_requested: bool
    requires_commit_boundary: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_immediate_memory_learning(
    message: object,
    selected_memory_records: object,
    protected_operator_constraints: object = None,
    prior_learning_receipts: object = (),
) -> dict[str, Any]:
    text = str(message or "")
    oversized_message = len(text) > MAX_MESSAGE_CHARS
    bounded = text[:MAX_MESSAGE_CHARS]
    correction = _match_any(bounded, _CORRECTION_PATTERNS)
    retraction = _match_any(bounded, _RETRACTION_PATTERNS)
    preference = _match_any(bounded, _PREFERENCE_PATTERNS)
    temporary = _match_any(bounded, _TEMPORARY_PATTERNS)

    malformed_collection = not isinstance(selected_memory_records, Sequence) or isinstance(selected_memory_records, (str, bytes, bytearray))
    rows = [] if malformed_collection else list(selected_memory_records)[:MAX_CANDIDATES]
    oversized_collection = not malformed_collection and len(selected_memory_records) > MAX_CANDIDATES
    malformed = authority = private = 0
    target_keys: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            malformed += 1
            continue
        if any(key in row and row.get(key) not in {False, None, "", 0} for key in _AUTHORITY):
            authority += 1
            continue
        if any(key in row for key in _PRIVATE):
            private += 1
            continue
        key = _safe_key(row.get("preference_key") or row.get("fact_key") or row.get("subject_key") or row.get("memory_id"))
        if key and key not in target_keys:
            target_keys.append(key)

    constraints = set(protected_operator_constraints or ()) if isinstance(protected_operator_constraints, Sequence) and not isinstance(protected_operator_constraints, (str, bytes, bytearray)) else set()
    required_constraints = {"preserve_historical_truth", "no_unconfirmed_memory_mutation", "current_message_precedence"}
    malformed_constraints = bool(protected_operator_constraints is not None and not isinstance(protected_operator_constraints, Sequence))
    protected = required_constraints <= constraints
    detected_types = [name for name, enabled in (("correction", correction), ("retraction", retraction), ("preference_change", preference)) if enabled]
    ambiguous = len(detected_types) > 1 and not (correction and preference and not retraction)
    degraded = bool(oversized_message or malformed_collection or oversized_collection or malformed or authority or private or malformed_constraints or not protected or ambiguous)

    candidate_type = "none"
    if not degraded:
        if retraction:
            candidate_type = "retraction"
        elif preference:
            candidate_type = "preference_change"
        elif correction:
            candidate_type = "correction"
    target_key = target_keys[0] if len(target_keys) == 1 else "unresolved"
    scope = "temporary" if temporary else "durable_candidate"
    candidate = None
    if candidate_type != "none":
        candidate = LearningCandidate(
            candidate_type=candidate_type,
            target_key=target_key,
            scope=scope,
            current_turn_precedence=True,
            historical_truth_preserved=True,
            mutation_requested=False,
            requires_commit_boundary=True,
        ).to_dict()

    prior = validate_prior_learning_receipts(prior_learning_receipts)
    if prior["continuity_disposition"] == "literal_request_only_recovery":
        degraded = True
        candidate = None
        candidate_type = "none"

    evidence = {
        "contract_version": CONTRACT_VERSION,
        "correction_cue": correction,
        "retraction_cue": retraction,
        "preference_change_cue": preference,
        "temporary_scope_cue": temporary,
        "candidate_count": int(candidate is not None),
        "target_key_count": len(target_keys),
        "malformed_count": malformed,
        "malformed_collection": malformed_collection,
        "oversized_collection": oversized_collection,
        "oversized_message": oversized_message,
        "authority_violation_count": authority,
        "private_field_violation_count": private,
        "ambiguous_change": ambiguous,
        "protected_constraints_present": protected,
        "memory_mutated": False,
        "history_rewritten": False,
        "provider_contacted": False,
        "contains_memory_text": False,
        "contains_private_reasoning": False,
        "authority": "none",
        "prior_verified_receipt_count": prior["verified_receipt_count"],
        "prior_replayed_receipt_count": prior["replayed_receipt_count"],
        "continuity_disposition": prior["continuity_disposition"],
        "integrity": "degraded" if degraded else "valid",
    }
    evidence["evidence_digest"] = _digest(evidence)
    posture = "literal_request_only_recovery" if degraded else ("apply_current_turn_precedence" if candidate else "no_learning_change")
    policy = {
        "contract_version": CONTRACT_VERSION,
        "learning_posture": posture,
        "candidate_type": candidate_type,
        "candidate_scope": scope if candidate else "none",
        "target_key_state": "resolved" if target_key != "unresolved" else "unresolved",
        "current_turn_precedence": bool(candidate),
        "historical_truth_preserved": True,
        "memory_commit_permitted": False,
        "memory_mutation_permitted": False,
        "automatic_learning_permitted": False,
        "requires_existing_commit_boundary": bool(candidate),
        "policy_recovered": degraded,
        "recovery_reason": "invalid_or_ambiguous_learning_input" if degraded else "none",
        "continuity_disposition": prior["continuity_disposition"],
        "verified_prior_learning_receipts": prior["verified_receipt_count"],
        "replayed_prior_learning_receipts": prior["replayed_receipt_count"],
        "tampered_prior_learning_receipts": prior["tampered_receipt_count"],
        "conflicting_prior_learning_receipts": prior["conflicting_receipts"],
        "oversized_prior_learning_receipt_bytes": prior["oversized_receipt_bytes"],
        "authority": "none",
        "content_free": True,
        "evidence_digest": evidence["evidence_digest"],
    }
    policy["policy_digest"] = _digest(policy)
    prompt = '<immediate_memory_learning data_only="true" authority="none">' + json.dumps(policy, sort_keys=True, separators=(",", ":")) + '</immediate_memory_learning>'
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError("immediate memory learning prompt exceeded bound")
    diagnostics = {
        key: policy[key] for key in (
            "contract_version", "learning_posture", "candidate_type", "candidate_scope", "target_key_state",
            "current_turn_precedence", "historical_truth_preserved", "memory_commit_permitted",
            "memory_mutation_permitted", "automatic_learning_permitted", "requires_existing_commit_boundary",
            "policy_recovered", "recovery_reason", "continuity_disposition", "verified_prior_learning_receipts",
            "replayed_prior_learning_receipts", "tampered_prior_learning_receipts", "conflicting_prior_learning_receipts",
            "oversized_prior_learning_receipt_bytes", "authority", "content_free", "policy_digest",
        )
    }
    diagnostics.update({
        "candidate_count": int(candidate is not None),
        "malformed_collection": malformed_collection,
        "oversized_collection": oversized_collection,
        "oversized_message": oversized_message,
        "provider_contacted": False,
        "history_rewritten": False,
    })
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    return {"policy": policy, "evidence": evidence, "candidate": candidate, "diagnostics": diagnostics, "prompt_section": prompt}


def verify_immediate_memory_learning_diagnostics(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("diagnostics_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "diagnostics_digest"}
    return (
        len(supplied) == 64
        and _digest(unsigned) == supplied
        and value.get("authority") == "none"
        and value.get("content_free") is True
        and value.get("memory_mutation_permitted") is False
        and value.get("automatic_learning_permitted") is False
        and value.get("provider_contacted") is False
        and value.get("history_rewritten") is False
    )


def build_learning_commit_boundary_handoff(
    candidate: object,
    *,
    provider_completed: bool,
    assistant_memory_committed: bool,
) -> dict[str, Any]:
    """Build a content-free handoff to the existing commit boundary; never mutate memory."""
    valid = isinstance(candidate, Mapping) and str(candidate.get("candidate_type") or "") in {"correction", "retraction", "preference_change"}
    durable = valid and candidate.get("scope") == "durable_candidate"
    eligible = bool(durable and provider_completed and assistant_memory_committed)
    handoff = {
        "contract_version": CONTRACT_VERSION,
        "candidate_present": bool(valid),
        "candidate_type": str(candidate.get("candidate_type") or "none") if valid else "none",
        "candidate_scope": str(candidate.get("scope") or "none") if valid else "none",
        "target_key_state": "resolved" if valid and str(candidate.get("target_key") or "") not in {"", "unresolved"} else "unresolved",
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_existing_commit_review": eligible,
        "automatic_commit_permitted": False,
        "memory_mutation_performed": False,
        "historical_truth_preserved": True,
        "authority": "none",
        "content_free": True,
    }
    handoff["handoff_digest"] = _digest(handoff)
    return handoff


def verify_learning_commit_boundary_handoff(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("handoff_digest") or "")
    unsigned = {k:v for k,v in value.items() if k != "handoff_digest"}
    return len(supplied)==64 and _digest(unsigned)==supplied and value.get("authority")=="none" and value.get("content_free") is True and value.get("automatic_commit_permitted") is False and value.get("memory_mutation_performed") is False


def validate_prior_learning_receipts(receipts: object) -> dict[str, Any]:
    malformed_collection = not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes, bytearray))
    rows = [] if malformed_collection else list(receipts)
    oversized_collection = len(rows) > MAX_PRIOR_RECEIPTS
    oversized_bytes = False
    if not malformed_collection:
        try:
            oversized_bytes = len(json.dumps(rows, sort_keys=True, default=str).encode()) > MAX_PRIOR_RECEIPT_BYTES
        except Exception:
            oversized_bytes = True
    rows = rows[:MAX_PRIOR_RECEIPTS]
    verified=stale=tampered=replayed=0
    seen=set()
    durable_types=[]
    target_states=[]
    for row in rows:
        if not isinstance(row, Mapping):
            tampered += 1
            continue
        if "immediate_memory_learning_commit_handoff" in row:
            nested = row.get("immediate_memory_learning_commit_handoff")
            if not isinstance(nested, Mapping):
                tampered += 1
                continue
            candidate = nested
        elif "handoff_digest" in row and "eligible_for_existing_commit_review" in row:
            candidate = row
        else:
            # Session history contains many structural records that are not learning
            # receipts. Their absence from this protocol is neutral, not tampering.
            continue
        if not verify_learning_commit_boundary_handoff(candidate):
            tampered += 1
            continue
        digest=str(candidate.get("handoff_digest"))
        if digest in seen:
            replayed += 1
            continue
        seen.add(digest)
        if not candidate.get("eligible_for_existing_commit_review"):
            stale += 1
            continue
        verified += 1
        durable_types.append(str(candidate.get("candidate_type") or "none"))
        target_states.append(str(candidate.get("target_key_state") or "unresolved"))
    conflicting_receipts = len(set(durable_types)) > 1 or ("resolved" in target_states and "unresolved" in target_states)
    recovered = bool(malformed_collection or oversized_collection or oversized_bytes or tampered or conflicting_receipts)
    result={
        "verified_receipt_count":verified, "stale_receipt_count":stale, "tampered_receipt_count":tampered,
        "replayed_receipt_count":replayed, "malformed_collection":malformed_collection, "oversized_collection":oversized_collection,
        "oversized_receipt_bytes":oversized_bytes, "conflicting_receipts":conflicting_receipts,
        "continuity_disposition":"literal_request_only_recovery" if recovered else ("resume_verified_learning_context" if verified else "use_current_turn_only"),
        "durable_candidate_type_count":len(set(durable_types)), "authority":"none", "content_free":True,
    }
    result["receipt_digest"]=_digest(result)
    return result


def audit_immediate_memory_learning(
    projection: object,
    handoff: object = None,
) -> dict[str, Any]:
    """Audit structural learning state without retaining correction or preference content."""
    malformed_projection = not isinstance(projection, Mapping)
    policy = projection.get("policy") if isinstance(projection, Mapping) else None
    candidate = projection.get("candidate") if isinstance(projection, Mapping) else None
    diagnostics = projection.get("diagnostics") if isinstance(projection, Mapping) else None
    malformed_policy = not isinstance(policy, Mapping)
    malformed_candidate = candidate is not None and not isinstance(candidate, Mapping)
    invalid_diagnostics = not verify_immediate_memory_learning_diagnostics(diagnostics)
    authority_violations = 0
    private_field_violations = 0
    for item in (policy, candidate, diagnostics, handoff):
        if not isinstance(item, Mapping):
            continue
        authority_violations += sum(1 for key in _AUTHORITY if key in item and item.get(key) not in {False, None, "", 0})
        private_field_violations += sum(1 for key in _PRIVATE if key in item)
    handoff_present = handoff is not None
    invalid_handoff = handoff_present and not verify_learning_commit_boundary_handoff(handoff)
    candidate_present = isinstance(candidate, Mapping)
    durable_candidate = candidate_present and candidate.get("scope") == "durable_candidate"
    eligible_handoff = isinstance(handoff, Mapping) and handoff.get("eligible_for_existing_commit_review") is True
    premature_handoff = bool(eligible_handoff and not durable_candidate)
    mutation_violation = bool(
        (isinstance(policy, Mapping) and (policy.get("memory_commit_permitted") is not False or policy.get("memory_mutation_permitted") is not False))
        or (isinstance(handoff, Mapping) and (handoff.get("automatic_commit_permitted") is not False or handoff.get("memory_mutation_performed") is not False))
    )
    recovered_candidate_violation = bool(isinstance(policy, Mapping) and policy.get("policy_recovered") is True and candidate_present)
    compliant = not any((malformed_projection, malformed_policy, malformed_candidate, invalid_diagnostics, invalid_handoff,
                         authority_violations, private_field_violations, premature_handoff, mutation_violation,
                         recovered_candidate_violation))
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
        "mutation_violation": mutation_violation,
        "recovered_candidate_violation": recovered_candidate_violation,
        "compliant": compliant,
        "memory_mutation_performed": False,
        "contains_learning_content": False,
        "contains_private_reasoning": False,
        "authority": "none",
        "content_free": True,
    }
    result["audit_digest"] = _digest(result)
    return result


def verify_immediate_memory_learning_audit(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    supplied = str(value.get("audit_digest") or "")
    unsigned = {key: item for key, item in value.items() if key != "audit_digest"}
    return (
        len(supplied) == 64 and _digest(unsigned) == supplied
        and value.get("authority") == "none" and value.get("content_free") is True
        and value.get("memory_mutation_performed") is False
        and value.get("contains_learning_content") is False
        and value.get("contains_private_reasoning") is False
    )
