from __future__ import annotations

"""v1155.0-v1155.2 bounded reasoning-alpha consolidation.

Combines reflection, belief, deliberation and decision-boundary projections into
one authority-free ordinary-turn reasoning state. This module exposes outcomes,
evidence sufficiency and uncertainty, never private chain-of-thought.
"""

from copy import deepcopy
import hashlib
import json
from typing import Any

CONTRACT_VERSION = "v1155.8"
SCHEMA_VERSION = "1"
MAX_CASES = 2
MAX_OPTIONS = 3
MAX_SUMMARY_CHARS = 1100


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _clamp(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def build_reasoning_state(
    *,
    reflection_items: list[dict[str, Any]] | None,
    belief_deliberation: dict[str, Any] | None,
    multi_step_deliberation: dict[str, Any] | None,
    decision_boundary: dict[str, Any] | None,
    continuity: dict[str, Any] | None,
    prior_reasoning_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one bounded, explainable, non-authorizing reasoning projection."""
    reflections = [row for row in (reflection_items or []) if isinstance(row, dict)]
    deliberation = belief_deliberation if isinstance(belief_deliberation, dict) else {}
    multi = multi_step_deliberation if isinstance(multi_step_deliberation, dict) else {}
    boundary = decision_boundary if isinstance(decision_boundary, dict) else {}
    continuity_row = continuity if isinstance(continuity, dict) else {}
    prior_row = prior_reasoning_state if isinstance(prior_reasoning_state, dict) else {}
    prior_projection = prior_row.get("projection") if isinstance(prior_row.get("projection"), dict) else {}

    cases: list[dict[str, Any]] = []
    for row in (multi.get("cases") or [])[:MAX_CASES]:
        if not isinstance(row, dict):
            continue
        options = []
        for option in (row.get("options") or [])[:MAX_OPTIONS]:
            if not isinstance(option, dict):
                continue
            options.append({
                "option_id": str(option.get("option_id") or "")[:120],
                "proposition": " ".join(str(option.get("proposition") or "").split())[:260],
                "confidence": round(_clamp(option.get("confidence")), 3),
                "uncertainty": round(_clamp(option.get("uncertainty")), 3),
                "evidence_quality": round(_clamp(option.get("evidence_quality")), 3),
            })
        comparison = row.get("comparison") if isinstance(row.get("comparison"), dict) else {}
        cases.append({
            "case_digest": str(row.get("case_digest") or "")[:128],
            "options": options,
            "completed_step_count": sum(1 for step in (row.get("steps") or []) if isinstance(step, dict) and step.get("complete")),
            "step_count": min(4, len(row.get("steps") or [])),
            "outcome": str(comparison.get("outcome") or "requires_more_evidence")[:80],
            "provisional_leader_option_id": str(comparison.get("provisional_leader_option_id") or "")[:120],
            "resolution_permitted": False,
        })

    boundary_cases = []
    for row in (boundary.get("cases") or [])[:MAX_CASES]:
        if not isinstance(row, dict):
            continue
        boundary_cases.append({
            "boundary_id": str(row.get("boundary_id") or "")[:120],
            "state": str(row.get("state") or "no_decision")[:80],
            "candidate_option_id": str(row.get("candidate_option_id") or "")[:120],
            "evidence_sufficient": bool(row.get("evidence_sufficient")),
            "prerequisites_complete": bool(row.get("prerequisites_complete")),
            "risk_level": str(row.get("risk_level") or "unknown")[:40],
            "reversibility": str(row.get("reversibility") or "unknown")[:40],
            "operator_approval_required": bool(row.get("operator_approval_required", True)),
            "decision_created": False,
            "execution_permitted": False,
        })

    uncertainty_values = [_clamp(row.get("uncertainty_score")) for row in reflections]
    reflection_confidences = [_clamp(row.get("confidence")) for row in reflections]
    boundary_states = [row["state"] for row in boundary_cases]
    more_evidence = any(state == "more_evidence_required" for state in boundary_states) or any(case["outcome"] == "requires_more_evidence" for case in cases)
    candidate_present = any(state == "candidate_recommendation" for state in boundary_states)
    quality = "insufficient_evidence" if more_evidence else ("bounded_candidate" if candidate_present else "no_decision")

    result = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "reasoning_quality": quality,
        "reflection_count": len(reflections),
        "mean_reflection_confidence": round(sum(reflection_confidences) / len(reflection_confidences), 3) if reflection_confidences else 0.0,
        "mean_reflection_uncertainty": round(sum(uncertainty_values) / len(uncertainty_values), 3) if uncertainty_values else 1.0,
        "belief_conflict_count": int(deliberation.get("conflict_count") or 0),
        "quarantined_conflict_count": int(deliberation.get("quarantined_conflict_count") or 0),
        "cases": cases,
        "decision_boundaries": boundary_cases,
        "prior_session_present": bool(continuity_row.get("prior_session_present")),
        "prior_session_stale": bool(continuity_row.get("prior_session_stale")),
        "goal_context_count": int(continuity_row.get("goal_context_count") or 0),
        "missing_evidence_explicit": more_evidence,
        "candidate_recommendation_present": candidate_present,
        "private_chain_of_thought_exposed": False,
        "raw_belief_ledger_exposed": False,
        "raw_reflection_evidence_exposed": False,
        "decision_created": False,
        "intention_created": False,
        "action_executed": False,
        "operator_approval_required": candidate_present,
        "prior_reasoning_state_present": bool(prior_row.get("prior_state_present")),
        "prior_reasoning_state_stale": bool(prior_row.get("prior_state_stale")),
        "prior_reasoning_store_malformed": bool(prior_row.get("malformed_store")),
        "prior_reasoning_quality": str(prior_projection.get("reasoning_quality") or "")[:80],
        "reasoning_transition": (
            "first_observation" if not prior_row.get("prior_state_present") else
            "evidence_improved" if prior_projection.get("missing_evidence_explicit") and not more_evidence else
            "evidence_degraded" if not prior_projection.get("missing_evidence_explicit") and more_evidence else
            "candidate_emerged" if not prior_projection.get("candidate_recommendation_present") and candidate_present else
            "candidate_withdrawn" if prior_projection.get("candidate_recommendation_present") and not candidate_present else
            "stable"
        ),
        "authority": "none",
    }
    result["reasoning_state_digest"] = _digest(result)
    return result


def prompt_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Return the minimal projection admitted to the ordinary prompt."""
    if not isinstance(state, dict):
        return {}
    projection = {
        "reasoning_quality": state.get("reasoning_quality"),
        "belief_conflict_count": state.get("belief_conflict_count"),
        "cases": deepcopy(state.get("cases") or [])[:MAX_CASES],
        "decision_boundaries": deepcopy(state.get("decision_boundaries") or [])[:MAX_CASES],
        "prior_session_present": bool(state.get("prior_session_present")),
        "prior_session_stale": bool(state.get("prior_session_stale")),
        "goal_context_count": int(state.get("goal_context_count") or 0),
        "missing_evidence_explicit": bool(state.get("missing_evidence_explicit")),
        "candidate_recommendation_present": bool(state.get("candidate_recommendation_present")),
        "prior_reasoning_state_present": bool(state.get("prior_reasoning_state_present")),
        "prior_reasoning_state_stale": bool(state.get("prior_reasoning_state_stale")),
        "reasoning_transition": str(state.get("reasoning_transition") or "first_observation")[:80],
        "decision_created": False,
        "execution_permitted": False,
        "authority": "none",
    }
    encoded = json.dumps(projection, sort_keys=True, ensure_ascii=True)
    if len(encoded) > MAX_SUMMARY_CHARS:
        projection["cases"] = []
        projection["decision_boundaries"] = []
        projection["truncated"] = True
    return projection
