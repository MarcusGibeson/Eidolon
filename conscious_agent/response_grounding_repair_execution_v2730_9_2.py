from __future__ import annotations
"""Operator-confirmed execution of reviewed response-grounding repairs.

This module acts only on a pending response string supplied to the executor. It
cannot mutate source, memory, approvals, provider configuration, or external
state. Candidate/review digests must bind to the exact audit chain and the
repaired output is re-audited before it may be returned as successful.
"""
from typing import Any, Mapping
import hashlib, json, re
from response_grounding_output_audit_v2683 import audit_response_grounding_output
from response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from response_grounding_repair_review_v2688 import build_response_grounding_repair_review

CONTRACT_VERSION = "v2730.9.2"
_DENIED = {
    "source_mutation_allowed": False,
    "memory_mutation_allowed": False,
    "authority_expanded": False,
    "provider_contacted": False,
    "external_action_executed": False,
    "automatic_repair_permitted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _sentence_spans(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    return [p for p in parts if p]


def _repair_sentence(sentence: str, *, memory: bool, execution: bool) -> str:
    # Repair independent clauses separately; never discard the unaffected tail.
    clauses = re.split(r"(,\s*(?:and|but)\s+|;\s*|\s+and\s+|\s+but\s+)", sentence)
    if len(clauses) > 1:
        if any(not re.match(r"\s*(?:the|a|an|I|you|we|it|this|that|there|your)\b", p, re.I)
               for p in clauses[2::2]):
            return sentence
        return "".join(_repair_sentence(p, memory=memory, execution=execution).rstrip(".") if i % 2 == 0 and i < len(clauses) - 1
                       else (_repair_sentence(p, memory=memory, execution=execution) if i % 2 == 0 else p)
                       for i, p in enumerate(clauses))
    # Subordinate/relative clauses cannot be safely separated by this bounded
    # executor. Leave them untouched so re-audit fails instead of losing facts.
    if re.search(r"\b(?:because|although|while|which|whereas)\b|,", sentence, re.I):
        return sentence
    low = sentence.lower()
    if memory and any(re.search(p, low) for p in (
        r"\bi (?:remember|recall)\b", r"\byou(?:'ve| have)? (?:told|said|mentioned)\b",
        r"\bwe(?:'ve| have)? (?:talked|discussed)\b", r"\bfrom what you told me\b", r"\bas you told me\b",
    )):
        return "I don't have grounded memory evidence for that."
    if execution and any(re.search(p, low) for p in (
        r"\bi(?:'ve| have)?\s+(?:successfully\s+|already\s+)?(?:sent|deleted|removed|installed|changed|updated|created|ran|executed|applied|submitted|uploaded|downloaded|saved|wrote|edited|moved|renamed|cancelled|canceled)\b",
        r"\b(?:it|that|the\s+\w+|your\s+\w+)(?:'s| has| was| is)\s+(?:already\s+)?(?:been\s+)?(?:sent|deleted|removed|installed|changed|updated|created|run|executed|applied|submitted|uploaded|downloaded|saved|written|edited|moved|renamed|cancelled|canceled)\b",
    )):
        return "I don't have authoritative execution evidence that this action was completed."
    return sentence


def authorize_and_execute_response_grounding_repair(
    response_text: str,
    *,
    audit: Mapping[str, Any],
    candidate: Mapping[str, Any],
    review: Mapping[str, Any],
    policy: Mapping[str, Any],
    calibration: Mapping[str, Any],
    operator_confirmation: bool,
    authoritative_execution_evidence: bool = False,
) -> dict[str, Any]:
    if operator_confirmation is not True:
        return {"ok": False, "status": "explicit_operator_confirmation_required", **_DENIED}
    if str(candidate.get("state")) != "repair_candidate_ready" or str(review.get("state")) != "operator_review_required":
        return {"ok": False, "status": "reviewed_repair_candidate_required", **_DENIED}
    if str(candidate.get("audit_digest") or "") != str(audit.get("audit_digest") or ""):
        return {"ok": False, "status": "stale_or_mismatched_audit", **_DENIED}
    if str(review.get("candidate_digest") or "") != str(candidate.get("candidate_digest") or ""):
        return {"ok": False, "status": "stale_or_mismatched_review", **_DENIED}

    expected_audit = audit_response_grounding_output(response_text, policy, calibration,
                                                    authoritative_execution_evidence=authoritative_execution_evidence)
    expected_candidate = build_response_grounding_repair_candidate(expected_audit, policy, calibration)
    expected_review = build_response_grounding_repair_review(expected_candidate)
    if dict(audit) != expected_audit or dict(candidate) != expected_candidate or dict(review) != expected_review:
        return {"ok": False, "status": "stale_or_invalid_repair_chain", **_DENIED}

    actions = set(str(x) for x in candidate.get("action_codes") or [])
    memory = "regenerate_without_unsupported_personal_memory_claim_or_state_uncertainty" in actions
    execution = "remove_execution_completion_claim_or_bind_authoritative_receipt" in actions
    repaired_parts = [_repair_sentence(p, memory=memory, execution=execution) for p in _sentence_spans(response_text)]
    repaired = " ".join(repaired_parts).strip()
    post_audit = audit_response_grounding_output(
        repaired, policy, calibration,
        authoritative_execution_evidence=authoritative_execution_evidence,
    )
    changed = repaired != str(response_text or "")
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "before_digest": hashlib.sha256(str(response_text or "").encode()).hexdigest(),
        "after_digest": hashlib.sha256(repaired.encode()).hexdigest(),
        "candidate_digest": str(candidate.get("candidate_digest") or "")[:64],
        "review_digest": str(review.get("review_digest") or "")[:64],
        "action_codes": sorted(actions),
        "operator_confirmed": True,
        "response_changed": changed,
        "post_audit_ok": bool(post_audit.get("ok")),
        "raw_response_persisted": False,
        **_DENIED,
    }
    receipt["receipt_digest"] = _digest(receipt)
    return {
        "ok": bool(changed and post_audit.get("ok")),
        "status": "response_grounding_repair_executed" if changed and post_audit.get("ok") else "response_grounding_repair_not_verified",
        "repaired_response": repaired,
        "post_audit": post_audit,
        "receipt": receipt,
        **_DENIED,
    }


__all__ = ["CONTRACT_VERSION", "authorize_and_execute_response_grounding_repair"]
