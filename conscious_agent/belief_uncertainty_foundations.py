from __future__ import annotations

"""v1152.0-v1152.2 belief candidates and explicit uncertainty foundations.

Transforms evidence-grounded reflections into provisional belief candidates. The
records are revisable context only: they cannot approve, authorize, or execute.
"""

from datetime import datetime, timezone
import hashlib, json, re
from typing import Any
from belief_uncertainty_foundations_belief import (
    SymbolDependencies as _BeliefUncertaintyFoundationsBeliefSymbolDependencies,
    build_belief_candidate as _build_belief_candidate_implementation,
    inspect_belief_candidates as _inspect_belief_candidates_implementation,
)


CONTRACT_VERSION = "v1152.2"
SCHEMA_VERSION = "1"
MAX_PROPOSITION_CHARS = 420
UNCERTAINTY_STATES = {"low", "material", "high", "insufficient_evidence"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _compact(value: object, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _terms(value: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9][a-z0-9'-]{2,}", str(value).lower()) if x not in {"the","and","that","this","with","from","should","could","would","about","user","ordinary","conversation","completed","turn"}}


def classify_uncertainty(confidence: float, evidence_count: int, evidence_sufficient: bool) -> dict[str, Any]:
    confidence = max(0.0, min(1.0, float(confidence)))
    score = round(1.0 - confidence, 3)
    if not evidence_sufficient or evidence_count <= 0:
        state = "insufficient_evidence"
    elif score >= 0.65:
        state = "high"
    elif score >= 0.3:
        state = "material"
    else:
        state = "low"
    return {"uncertainty_score": score, "uncertainty_state": state, "uncertainty_explicit": True}


def _prior_matches(reflection: dict[str, Any], candidate: dict[str, Any]) -> bool:
    key = str(reflection.get("semantic_subject_key") or "")
    if key and key == str(candidate.get("semantic_subject_key") or ""):
        return True
    return len(set(reflection.get("subject_terms") or []) & set(candidate.get("subject_terms") or [])) >= 2


def _build_belief_uncertainty_foundations_belief_dependencies() -> _BeliefUncertaintyFoundationsBeliefSymbolDependencies:
    return _BeliefUncertaintyFoundationsBeliefSymbolDependencies(
        CONTRACT_VERSION=CONTRACT_VERSION,
        MAX_PROPOSITION_CHARS=MAX_PROPOSITION_CHARS,
        UNCERTAINTY_STATES=UNCERTAINTY_STATES,
        _compact=_compact,
        _digest=_digest,
        _now=_now,
        _prior_matches=_prior_matches,
        _terms=_terms,
        classify_uncertainty=classify_uncertainty,
    )

def build_belief_candidate(*, reflection: dict[str, Any], operation_id: str, prior_candidates: list[dict[str, Any]] | None=None) -> dict[str, Any]:
    return _build_belief_candidate_implementation(reflection=reflection, operation_id=operation_id, prior_candidates=prior_candidates, _deps=_build_belief_uncertainty_foundations_belief_dependencies())



def inspect_belief_candidates(memories: list[dict[str, Any]]) -> dict[str, Any]:
    return _inspect_belief_candidates_implementation(memories, _deps=_build_belief_uncertainty_foundations_belief_dependencies())

