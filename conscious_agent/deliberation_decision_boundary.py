from __future__ import annotations

"""Governed boundary between deliberation outcomes and candidate decisions.

This module is deterministic, read-only, and authority preserving. It can describe
whether a bounded deliberation is eligible to become a candidate recommendation,
but it cannot create an intention, approve, schedule, execute, or contact a provider.
"""

from pathlib import Path
from typing import Any, Mapping
import hashlib
import json

try:
    from multi_step_deliberation import build_multi_step_deliberation
except ImportError:
    from multi_step_deliberation import build_multi_step_deliberation

CONTRACT_VERSION = "v1154.2"
MAX_CASES = 2
MAX_REASONS = 6
MAX_TEXT = 260
HIGH_RISK_TERMS = {
    "delete", "erase", "install", "uninstall", "replace", "publish", "promote",
    "purchase", "pay", "send", "email", "message", "execute", "run", "deploy",
    "credential", "secret", "private", "medical", "legal", "financial",
}
REVERSIBLE_TERMS = {"preview", "draft", "inspect", "compare", "review", "simulate", "test", "sandbox", "read-only"}


def _clean(value: Any, limit: int = MAX_TEXT) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _terms(value: Any) -> set[str]:
    return {part for part in "".join(c.lower() if c.isalnum() else " " for c in str(value)).split() if len(part) >= 3}


def _risk_and_reversibility(proposition: str) -> tuple[str, str, list[str]]:
    terms = _terms(proposition)
    reasons: list[str] = []
    if terms & HIGH_RISK_TERMS:
        reasons.append("sensitive_or_mutating_language")
        return "high", "unknown", reasons
    if terms & REVERSIBLE_TERMS:
        reasons.append("explicitly_reversible_or_read_only")
        return "low", "high", reasons
    reasons.append("reversibility_not_demonstrated")
    return "material", "unknown", reasons


def build_decision_boundary(
    user_message: str,
    *,
    runtime_root: str | Path | None = None,
    deliberation: Mapping[str, Any] | None = None,
    belief_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project deliberation outcomes into governed candidate-decision states."""
    base = dict(deliberation or build_multi_step_deliberation(
        user_message, runtime_root=runtime_root, belief_state=belief_state
    ))
    cases: list[dict[str, Any]] = []
    for raw_case in (base.get("cases") or [])[:MAX_CASES]:
        if not isinstance(raw_case, Mapping):
            continue
        options = [row for row in (raw_case.get("options") or []) if isinstance(row, Mapping)]
        comparison = raw_case.get("comparison") if isinstance(raw_case.get("comparison"), Mapping) else {}
        outcome = str(comparison.get("outcome") or "requires_more_evidence")
        leader = options[0] if options else {}
        proposition = _clean(leader.get("proposition"))
        evidence_sufficient = bool(comparison.get("evidence_sufficient"))
        prerequisites_complete = bool(raw_case.get("prerequisites_satisfied")) and all(
            bool(step.get("complete")) for step in (raw_case.get("steps") or []) if isinstance(step, Mapping)
        )
        risk, reversibility, reasons = _risk_and_reversibility(proposition)
        if not options:
            reasons.append("no_bounded_alternative")
        if not evidence_sufficient:
            reasons.append("evidence_insufficient")
        if not prerequisites_complete:
            reasons.append("prerequisites_incomplete")
        if outcome != "provisional_leader_only":
            reasons.append("no_provisional_leader")
        candidate_eligible = bool(
            options
            and outcome == "provisional_leader_only"
            and evidence_sufficient
            and prerequisites_complete
        )
        state = "candidate_recommendation" if candidate_eligible else (
            "more_evidence_required" if options else "no_decision"
        )
        approval_required = candidate_eligible
        executable = False
        cases.append({
            "boundary_id": "boundary-" + _digest({
                "case": raw_case.get("case_digest"),
                "leader": leader.get("option_id"),
                "state": state,
            })[:24],
            "case_digest": _clean(raw_case.get("case_digest"), 64),
            "state": state,
            "candidate_option_id": _clean(leader.get("option_id"), 120) if candidate_eligible else "",
            "candidate_proposition": proposition if candidate_eligible else "",
            "evidence_sufficient": evidence_sufficient,
            "prerequisites_complete": prerequisites_complete,
            "risk_level": risk,
            "reversibility": reversibility,
            "boundary_reasons": reasons[:MAX_REASONS],
            "operator_approval_required": approval_required,
            "decision_created": False,
            "intention_created": False,
            "execution_permitted": False,
            "action_authority": False,
        })
    no_decision_count = sum(1 for row in cases if row["state"] == "no_decision")
    evidence_required_count = sum(1 for row in cases if row["state"] == "more_evidence_required")
    candidate_count = sum(1 for row in cases if row["state"] == "candidate_recommendation")
    return {
        "contract_version": CONTRACT_VERSION,
        "type": "deliberation_decision_boundary",
        "case_count": len(cases),
        "cases": cases,
        "candidate_recommendation_count": candidate_count,
        "more_evidence_required_count": evidence_required_count,
        "no_decision_count": no_decision_count,
        "explicit_no_decision_preserved": True,
        "risk_and_reversibility_checked": True,
        "operator_approval_required_for_candidates": candidate_count > 0,
        "read_only": True,
        "runtime_mutated": False,
        "provider_contacted": False,
        "decision_created": False,
        "intention_created": False,
        "action_executed": False,
        "execution_permitted": False,
        "recommended_action": "store_only",
        "authority_broadened": False,
    }
