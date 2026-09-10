from __future__ import annotations

"""Bounded, read-only multi-step deliberation for ordinary conversation.

The contract turns unresolved belief conflicts into explicit alternatives, checks
prerequisites, and compares evidence without resolving conflicts or authorizing
any action. It is deliberately provider-neutral and deterministic.
"""

from pathlib import Path
from typing import Any, Mapping
import hashlib
import json

try:
    from belief_deliberation import build_belief_deliberation
except ImportError:
    from belief_deliberation import build_belief_deliberation

CONTRACT_VERSION = "v1153.2"
MAX_CASES = 2
MAX_OPTIONS = 3
MAX_STEPS = 4
MAX_TEXT_CHARS = 260


def _clean(value: Any, limit: int = MAX_TEXT_CHARS) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _bounded(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 4)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _option(option: Mapping[str, Any], index: int) -> dict[str, Any]:
    confidence = _bounded(option.get("confidence"), 0.5)
    uncertainty = _bounded(option.get("uncertainty"), 1.0)
    evidence_count = max(0, min(999, int(option.get("evidence_count") or 0)))
    evidence_quality = round(min(1.0, evidence_count / 3.0) * (1.0 - uncertainty), 4)
    score = round(confidence * 0.55 + evidence_quality * 0.30 + (1.0 - uncertainty) * 0.15, 4)
    proposition = _clean(option.get("proposition"))
    return {
        "option_id": _clean(option.get("belief_id") or f"option-{index+1}", 120),
        "proposition": proposition,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "evidence_count": evidence_count,
        "evidence_quality": evidence_quality,
        "comparison_score": score,
        "action_authority": False,
    }


def _steps(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    needs_evidence = any(row["evidence_count"] < 2 or row["uncertainty"] >= 0.5 for row in options)
    steps = [
        {
            "step": 1,
            "kind": "frame_alternatives",
            "prerequisites": [],
            "completion_criteria": "at_least_two_bounded_options",
            "complete": len(options) >= 2,
        },
        {
            "step": 2,
            "kind": "check_evidence_and_uncertainty",
            "prerequisites": [1],
            "completion_criteria": "each_option_has_bounded_evidence_state",
            "complete": all("evidence_quality" in row for row in options),
        },
        {
            "step": 3,
            "kind": "compare_without_resolving",
            "prerequisites": [1, 2],
            "completion_criteria": "scores_and_material_difference_recorded",
            "complete": len(options) >= 2,
        },
    ]
    if needs_evidence:
        steps.append({
            "step": 4,
            "kind": "identify_missing_evidence",
            "prerequisites": [2],
            "completion_criteria": "evidence_gap_explicit",
            "complete": True,
        })
    return steps[:MAX_STEPS]


def build_multi_step_deliberation(
    user_message: str,
    *,
    runtime_root: str | Path | None = None,
    belief_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = build_belief_deliberation(user_message, runtime_root=runtime_root, state=belief_state)
    cases: list[dict[str, Any]] = []
    for conflict in (base.get("conflicts") or [])[:MAX_CASES]:
        raw_options = [row for row in (conflict.get("options") or []) if isinstance(row, Mapping)][:MAX_OPTIONS]
        options = [_option(row, index) for index, row in enumerate(raw_options)]
        if len(options) < 2:
            continue
        options.sort(key=lambda row: (-row["comparison_score"], row["option_id"]))
        margin = round(options[0]["comparison_score"] - options[1]["comparison_score"], 4)
        sufficient = all(row["evidence_count"] >= 2 and row["uncertainty"] < 0.5 for row in options)
        outcome = "provisional_leader_only" if sufficient and margin >= 0.25 else "requires_more_evidence"
        case = {
            "case_digest": _digest({"conflict": conflict.get("conflict_id"), "options": [r["option_id"] for r in options]})[:24],
            "options": options,
            "steps": _steps(options),
            "comparison": {
                "score_margin": margin,
                "evidence_sufficient": sufficient,
                "outcome": outcome,
                "resolution_permitted": False,
            },
            "prerequisites_satisfied": True,
            "decision_created": False,
            "action_authority": False,
        }
        cases.append(case)
    return {
        "contract_version": CONTRACT_VERSION,
        "type": "multi_step_deliberation",
        "case_count": len(cases),
        "cases": cases,
        "quarantined_conflict_count": int(base.get("quarantined_conflict_count") or 0),
        "bounded": True,
        "read_only": True,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "resolution_permitted": False,
        "decision_created": False,
        "action_executed": False,
        "recommended_action": "store_only",
        "operator_authority_required_for_action": True,
        "authority_broadened": False,
    }
