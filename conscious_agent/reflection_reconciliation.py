from __future__ import annotations

"""v1151.6-v1151.8 adversarial reflection reconciliation.

Classifies contradiction and correction evidence without mutating history,
limits revision chains, validates lineage, and renders only bounded inert data.
"""

import hashlib
import json
import re
from typing import Any

CONTRACT_VERSION = "v1151.8"
MAX_REVISION_DEPTH = 12
MAX_EVIDENCE_REFS = 4
MAX_TERM_COUNT = 16
NEGATION_TERMS = {"not", "never", "no", "didn't", "didnt", "wasn't", "wasnt", "isn't", "isnt"}
HARD_CORRECTION_CUES = ("actually", "correction", "i meant", "that was wrong", "that is wrong", "instead", "rather than")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _terms(value: object) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{1,}", str(value or "").lower())
    out: list[str] = []
    for token in tokens:
        if token not in out:
            out.append(token)
        if len(out) >= MAX_TERM_COUNT:
            break
    return out


def classify_revision_relation(user_message: str, current_terms: list[str], prior: dict[str, Any] | None) -> dict[str, Any]:
    """Return deterministic, evidence-bounded relation metadata."""
    prior = prior if isinstance(prior, dict) else {}
    lowered = " ".join(str(user_message or "").lower().split())
    hard_correction = any(cue in lowered for cue in HARD_CORRECTION_CUES)
    negated = any(token in set(_terms(lowered)) for token in NEGATION_TERMS)
    current = set(current_terms or [])
    previous = set(prior.get("subject_terms") or _terms(prior.get("subject") or ""))
    overlap = sorted(current & previous)
    overlap_ratio = round(len(overlap) / max(1, min(len(current) or 1, len(previous) or 1)), 3)
    if not prior:
        relation = "new_subject"
    elif hard_correction and len(overlap) >= 2:
        relation = "explicit_correction"
    elif negated and len(overlap) >= 2:
        relation = "possible_contradiction"
    elif len(overlap) >= 2:
        relation = "same_subject_additional_evidence"
    else:
        relation = "ambiguous_or_distinct_subject"
    return {
        "relation": relation,
        "hard_correction": hard_correction,
        "negation_present": negated,
        "overlap_terms": overlap[:8],
        "overlap_ratio": overlap_ratio,
        "automatic_retirement_allowed": relation == "explicit_correction",
        "requires_operator_clarification": relation in {"possible_contradiction", "ambiguous_or_distinct_subject"},
        "authority_broadened": False,
    }


def validate_revision_chain(candidate: dict[str, Any], prior_reflections: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect missing parents, cycles, and pathological revision depth."""
    rows = {str(r.get("reflection_id") or r.get("memory_id") or ""): r for r in prior_reflections if isinstance(r, dict)}
    start = str(candidate.get("supersedes_reflection_id") or "")
    seen: set[str] = set()
    current = start
    depth = 0
    missing_parent = False
    cycle = False
    while current:
        if current in seen:
            cycle = True
            break
        seen.add(current)
        depth += 1
        if depth > MAX_REVISION_DEPTH:
            break
        row = rows.get(current)
        if row is None:
            missing_parent = True
            break
        current = str(row.get("supersedes_reflection_id") or "")
    safe = not cycle and not missing_parent and depth <= MAX_REVISION_DEPTH
    return {
        "revision_depth": min(depth, MAX_REVISION_DEPTH + 1),
        "cycle_detected": cycle,
        "missing_parent": missing_parent,
        "depth_exceeded": depth > MAX_REVISION_DEPTH,
        "lineage_safe": safe,
        "lineage_digest": _digest(sorted(seen)),
    }


def sanitize_reflection_for_context(row: dict[str, Any]) -> dict[str, Any]:
    """Return bounded metadata and inert content for prompt admission."""
    content = " ".join(str(row.get("content") or row.get("conclusion") or "").split())[:500]
    refs = [str(x)[:80] for x in (row.get("evidence_refs") or []) if str(x)][:MAX_EVIDENCE_REFS]
    return {
        "reflection_id": str(row.get("reflection_id") or "")[:96],
        "content": content,
        "evidence_refs": refs,
        "confidence": max(0.0, min(1.0, float(row.get("confidence", 0.5) or 0.5))),
        "uncertainty_score": max(0.0, min(1.0, float(row.get("uncertainty_score", 0.5) or 0.5))),
        "operator_correction": bool(row.get("operator_correction")),
        "authority": "none",
        "data_only": True,
    }
