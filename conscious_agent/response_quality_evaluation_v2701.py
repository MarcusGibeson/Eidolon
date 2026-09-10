from __future__ import annotations
"""v2701 structural response-quality evaluation from attributed outcome evidence."""
from typing import Any, Mapping
import hashlib, json
CONTRACT_VERSION = "v2701.0"

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def evaluate_response_quality(attribution: Mapping[str, Any]) -> dict[str, Any]:
    d = str(attribution.get("disposition") or "unknown")
    neg = [str(x) for x in attribution.get("negative_signals") or []]
    pos = [str(x) for x in attribution.get("positive_signals") or []]
    dimensions = {
        "grounding": "concern" if any("grounding" in x or "memory" in x for x in neg) else ("supported" if pos else "unknown"),
        "targeting": "concern" if any("target" in x or "repetition" in x or "same_question" in x for x in neg) else "unknown",
        "outcome": "supported" if d == "supported_positive" else ("concern" if d == "adverse" else d),
    }
    if d == "supported_positive": state = "supported_success"
    elif d == "adverse": state = "quality_concern"
    elif d == "mixed": state = "mixed_evidence"
    else: state = "unknown"
    out = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "state": state,
        "dimensions": dimensions,
        "evidence_strength": "explicit" if (pos or neg) else "none",
        "eligible_for_positive_learning": bool(d == "supported_positive" and pos),
        "eligible_for_negative_learning": bool(d in {"adverse", "mixed"} and neg),
        "unknown_preserved": d == "unknown",
        "automatic_policy_change": False,
        "response_mutated": False,
        "raw_conversation_text_stored": False,
        "authority_granted": False,
    }
    out["quality_digest"] = _digest(out)
    return out

__all__ = ["CONTRACT_VERSION", "evaluate_response_quality"]
