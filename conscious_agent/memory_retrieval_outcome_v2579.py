from __future__ import annotations
"""v2579 content-minimized outcome evidence for memory retrieval.

This module does not mutate memories, retrieval policy, prompts, or responses. It
turns already-minimized retrieval feedback plus structural post-turn signals into
an evidence candidate suitable for longitudinal learning.
"""
from typing import Any, Mapping
import hashlib, json

CONTRACT_VERSION = "v2579.0"
AUTHORITY = {
    "memory_mutation_authorized": False,
    "retrieval_policy_mutation_authorized": False,
    "provider_contact_authorized": False,
    "response_claim_authorized": False,
    "independent_authority_granted": False,
}

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def build_memory_retrieval_outcome(
    feedback: Mapping[str, Any], *,
    turn_completed: bool,
    correction_detected: bool = False,
    contradiction_detected: bool = False,
    uncertainty_preserved: bool = False,
    memory_supported_resolution: bool = False,
    retrieval_referenced_by_planning: bool = False,
) -> dict[str, Any]:
    state = str(feedback.get("state") or "unknown")[:48]
    selected = max(0, int(feedback.get("selected_count") or 0))
    adverse = int(bool(correction_detected)) + int(bool(contradiction_detected))
    supportive = int(bool(memory_supported_resolution)) + int(bool(retrieval_referenced_by_planning))
    if not turn_completed:
        disposition = "incomplete_turn"
    elif adverse:
        disposition = "negative_evidence"
    elif supportive and state.startswith("grounded"):
        disposition = "positive_evidence"
    elif state in {"weak_context_only", "no_useful_memory"} and uncertainty_preserved:
        disposition = "appropriate_restraint"
    else:
        disposition = "neutral_evidence"
    out = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "retrieval_state": state,
        "selected_count": selected,
        "turn_completed": bool(turn_completed),
        "correction_detected": bool(correction_detected),
        "contradiction_detected": bool(contradiction_detected),
        "uncertainty_preserved": bool(uncertainty_preserved),
        "memory_supported_resolution": bool(memory_supported_resolution),
        "retrieval_referenced_by_planning": bool(retrieval_referenced_by_planning),
        "outcome_disposition": disposition,
        "raw_memory_text_stored": False,
        "raw_prompt_stored": False,
        "raw_response_stored": False,
        **AUTHORITY,
    }
    out["outcome_digest"] = _digest(out)
    return out

__all__ = ["CONTRACT_VERSION", "build_memory_retrieval_outcome"]
