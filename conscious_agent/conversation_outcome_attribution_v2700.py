from __future__ import annotations
"""v2700 structural conversation outcome attribution.

Consumes already-minimized evidence only.  Absence of an explicit positive or negative
signal remains unknown; silence is never interpreted as success.
"""
from typing import Any, Mapping
import hashlib, json
CONTRACT_VERSION = "v2700.0"

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def build_conversation_outcome_attribution(
    *,
    grounding_feedback: Mapping[str, Any] | None = None,
    target_outcome: Mapping[str, Any] | None = None,
    output_audit: Mapping[str, Any] | None = None,
    memory_feedback: Mapping[str, Any] | None = None,
    context_observability: Mapping[str, Any] | None = None,
    explicit_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    g = dict(grounding_feedback or {})
    t = dict(target_outcome or {})
    a = dict(output_audit or {})
    m = dict(memory_feedback or {})
    c = dict(context_observability or {})
    r = dict(explicit_resolution or {})
    negative: list[str] = []
    positive: list[str] = []
    neutral: list[str] = []

    if bool(g.get("adverse_calibration_evidence")):
        negative.append("grounding_correction_or_retraction")
    if int(t.get("repair_signal_count") or 0) > 0:
        negative.append("target_or_repetition_repair_required")
    if int(a.get("concern_count") or a.get("audit_concern_count") or 0) > 0 or bool(a.get("has_concerns")):
        negative.append("post_generation_grounding_concern")

    memory_state = str(m.get("state") or m.get("feedback", {}).get("state") if isinstance(m.get("feedback"), Mapping) else m.get("state") or "unknown")
    preserve_uncertainty = bool(m.get("should_preserve_uncertainty") or (m.get("feedback", {}).get("should_preserve_uncertainty") if isinstance(m.get("feedback"), Mapping) else False))
    if memory_state in {"weak_context_only", "no_useful_memory"}:
        if preserve_uncertainty:
            neutral.append("weak_memory_uncertainty_preserved")
        else:
            negative.append("weak_memory_without_uncertainty_restraint")

    context_state = str(c.get("state") or "unknown")
    if context_state == "budget_constrained":
        neutral.append("context_budget_constrained")
    elif context_state in {"context_supported", "current_turn_only"}:
        neutral.append("context_available")

    resolution_kind = str(r.get("kind") or r.get("resolution_kind") or "none")
    resolution_explicit = bool(r.get("explicit") or r.get("evidence_recorded"))
    if resolution_explicit and resolution_kind in {"confirmed_resolution", "explicitly_helpful", "accepted_answer", "issue_resolved"}:
        positive.append("explicit_supported_resolution")
    elif resolution_explicit and resolution_kind in {"correction", "retraction", "same_question_reasked", "target_missed"}:
        negative.append("explicit_negative_followup")

    if positive and negative:
        disposition = "mixed"
    elif negative:
        disposition = "adverse"
    elif positive:
        disposition = "supported_positive"
    else:
        disposition = "unknown"

    out = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "disposition": disposition,
        "positive_signal_count": len(positive),
        "negative_signal_count": len(negative),
        "neutral_signal_count": len(neutral),
        "positive_signals": positive[:8],
        "negative_signals": negative[:8],
        "neutral_signals": neutral[:8],
        "silence_treated_as_success": False,
        "raw_prompt_stored": False,
        "raw_response_stored": False,
        "raw_memory_text_stored": False,
        "conversation_policy_mutated": False,
        "authority_granted": False,
    }
    out["outcome_digest"] = _digest(out)
    return out

__all__ = ["CONTRACT_VERSION", "build_conversation_outcome_attribution"]
