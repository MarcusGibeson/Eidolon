from __future__ import annotations

"""v1517-v1525 value-prioritized selection over the existing initiative queue.

This module wraps, rather than replaces, the v1501 queue contract.  Dynamic
candidate identity and proposal authority continue to come from the established
discovery/eligibility/comparison path.  Value evidence can reorder those
candidates or block low-value structural work when materially higher-value
observed evidence is not yet bound to a safe implementable candidate.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from initiative_evidence_review import build_initiative_evidence_review
from initiative_value_model import build_initiative_value_model
from supervised_initiative_queue import build_supervised_initiative_shortlist


CONTRACT_VERSION = "v1525.9"
UNBOUND_PRIORITY_MARGIN = 0.08
STRUCTURAL_BLOCK_FLOOR = 0.55
MAX_CONSECUTIVE_STRUCTURAL_INSTALLS = 5


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def value_prioritization_contract() -> dict[str, Any]:
    result = {
        "contract_version": CONTRACT_VERSION,
        "selection_owner": "existing_supervised_initiative_queue",
        "value_owner": "initiative_value_model",
        "unbound_priority_margin": UNBOUND_PRIORITY_MARGIN,
        "structural_block_floor": STRUCTURAL_BLOCK_FLOOR,
        "max_consecutive_structural_installs": MAX_CONSECUTIVE_STRUCTURAL_INSTALLS,
        "rules": [
            "preserve_dynamic_candidate_identity",
            "preserve_discovery_evidence_digest_for_proposal_binding",
            "bind_value_decision_to_separate_content_free_evidence_digest",
            "visible_product_defect_may_outrank_structural_refactor",
            "higher_value_unbound_evidence_blocks_low_value_structural_selection",
            "structural_maintenance_budget_requires_product_rebalance",
            "deferred_or_cancelled_evidence_cannot_drive_selection",
            "selection_creates_no_proposal_or_authority",
        ],
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["contract_digest"] = _digest(result)
    return result


def _quality_map(comparison: Mapping[str, Any]) -> dict[str, float]:
    return {
        str(row.get("candidate_id") or ""): max(0.0, min(1.0, float(row.get("quality_score") or 0.0)))
        for row in comparison.get("ordered_comparison") or ()
        if row.get("candidate_id")
    }


def _risk_fit(base: Mapping[str, Any]) -> float:
    return max(0.0, min(1.0, 1.0 - float(base.get("risk_score") or 0.0)))


def _consecutive_structural_installs(records: Sequence[Mapping[str, Any]]) -> int:
    """Count the current installed structural-only run, ignoring non-install lifecycle noise."""

    count = 0
    installed = [row for row in records if str(row.get("lifecycle_state") or "") == "operator_installed"]
    for row in reversed(installed):
        if not bool((row.get("selected") or {}).get("structural_only", True)):
            break
        count += 1
    return count


def _explainable_candidate(
    base: Mapping[str, Any],
    value: Mapping[str, Any],
    quality_score: float,
) -> dict[str, Any]:
    row = dict(base)
    value_score = float(value.get("value_score") or 0.0)
    priority_score = round(0.72 * value_score + 0.18 * quality_score + 0.10 * _risk_fit(base), 4)
    row.update({
        "value_score": value_score,
        "value_model_score": value_score,
        "value_digest": str(value.get("value_digest") or ""),
        "value_evidence_id": str(value.get("evidence_id") or ""),
        "value_evidence_digest": str(value.get("evidence_digest") or ""),
        "value_factors": dict(value.get("factors") or {}),
        "value_penalties": [dict(item) for item in value.get("penalties") or ()],
        "selection_eligible": bool(value.get("selection_eligible")),
        "priority_score": priority_score,
        "selection_score": priority_score,
        "selection_basis": "capability_value_with_quality_and_risk_guardrails",
    })
    if not value.get("structural_only"):
        module = Path(str(row.get("source_module") or value.get("source_module") or "affected surface")).name
        domain = str(value.get("issue_domain") or "product").replace("_", " ")
        row["title"] = f"Repair {domain} behavior"
        row["description"] = (
            f"Address attributable {str(value.get('evidence_class') or 'product')} evidence in {module} "
            "against its explicit acceptance criteria while preserving the existing authority boundary."
        )
        row["reason"] = (
            f"This evidence has value score {value_score:.2f} and quality score {quality_score:.2f}; "
            "its expected benefit is observable product behavior rather than structural cleanup alone."
        )
        row["structural_only"] = False
        row["practical_benefit"] = str(value.get("practical_benefit") or "observable_product_or_capability_improvement")
        row["acceptance_criteria"] = list(value.get("acceptance_criteria") or ())
    row["candidate_digest"] = _digest({key: val for key, val in row.items() if key != "candidate_digest"})
    return row


def build_value_prioritized_initiative_shortlist(
    hardening: Mapping[str, Any],
    comparison: Mapping[str, Any],
    *,
    evidence_intake: Mapping[str, Any],
    prior_candidate_ids: Sequence[str] = (),
    recent_initiatives: Sequence[Mapping[str, Any]] = (),
    limit: int = 3,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return an authority-inert shortlist ordered by demonstrated practical value."""

    base = build_supervised_initiative_shortlist(
        hardening,
        comparison,
        prior_candidate_ids=prior_candidate_ids,
        limit=max(1, min(3, int(limit))),
        evidence_intake=evidence_intake,
    )
    review = build_initiative_evidence_review(evidence_intake, runtime_root=runtime_root)
    eligible_candidates = [dict(row) for row in hardening.get("eligible_candidates") or ()]
    value_model = build_initiative_value_model(
        review,
        candidates=eligible_candidates,
        prior_candidate_ids=prior_candidate_ids,
    )
    value_by_candidate: dict[str, dict[str, Any]] = {}
    for value_row in value_model.get("records") or ():
        candidate_id = str(value_row.get("candidate_id") or "")
        if not candidate_id:
            continue
        current = value_by_candidate.get(candidate_id)
        if current is None or float(value_row.get("value_score") or 0.0) > float(current.get("value_score") or 0.0):
            value_by_candidate[candidate_id] = dict(value_row)
    quality = _quality_map(comparison)
    enriched = []
    for row in base.get("shortlist") or ():
        candidate_id = str(row.get("candidate_id") or "")
        value = value_by_candidate.get(candidate_id)
        if not value:
            continue
        enriched.append(_explainable_candidate(row, value, quality.get(candidate_id, float(row.get("quality_score") or 0.0))))
    enriched = [row for row in enriched if row.get("selection_eligible")]
    enriched.sort(key=lambda row: (-float(row.get("priority_score") or 0.0), float(row.get("risk_score") or 0.0), row.get("candidate_id") or ""))
    enriched = enriched[:max(1, min(3, int(limit)))]

    best = enriched[0] if enriched else {}
    top_value = dict((value_model.get("records") or [{}])[0]) if value_model.get("records") else {}
    best_value = float(best.get("value_score") or 0.0)
    top_value_score = float(top_value.get("value_score") or 0.0)
    unbound_blocks = bool(
        top_value
        and not top_value.get("implementation_ready")
        and top_value_score >= STRUCTURAL_BLOCK_FLOOR
        and top_value_score >= best_value + UNBOUND_PRIORITY_MARGIN
        and (not best or bool(best.get("structural_only")))
    )
    structural_streak = _consecutive_structural_installs(recent_initiatives)
    maintenance_budget_exhausted = bool(
        best
        and bool(best.get("structural_only"))
        and structural_streak >= MAX_CONSECUTIVE_STRUCTURAL_INSTALLS
    )

    selection = {} if unbound_blocks or maintenance_budget_exhausted else best
    status = (
        "higher_value_evidence_requires_candidate_binding"
        if unbound_blocks
        else "structural_maintenance_budget_exhausted"
        if maintenance_budget_exhausted
        else "value_prioritized_initiative_shortlist_ready"
        if selection
        else "no_value_eligible_initiative"
    )
    result = {
        "ok": bool(selection),
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "shortlist": enriched,
        "shortlist_count": len(enriched),
        "selected_candidate_id": str(selection.get("candidate_id") or ""),
        "selection_made": bool(selection),
        "selection_basis": "capability_value_model_v1516_9_with_quality_and_risk_guardrails" if selection else "",
        "selection_blocked_by_unbound_value": unbound_blocks,
        "selection_blocked_by_maintenance_budget": maintenance_budget_exhausted,
        "consecutive_structural_installs": structural_streak,
        "max_consecutive_structural_installs": MAX_CONSECUTIVE_STRUCTURAL_INSTALLS,
        "portfolio_rebalance_required": maintenance_budget_exhausted,
        "blocking_evidence_id": str(top_value.get("evidence_id") or "") if unbound_blocks else "",
        "blocking_evidence_value_score": top_value_score if unbound_blocks else 0.0,
        "evidence_intake_digest": str(evidence_intake.get("intake_digest") or ""),
        "evidence_review_digest": str(review.get("review_snapshot_digest") or ""),
        "value_model_digest": str(value_model.get("value_model_digest") or ""),
        "unbound_priority_evidence_count": int(evidence_intake.get("unbound_priority_evidence_count") or 0),
        "unbound_high_value_count": int(value_model.get("unbound_high_value_count") or 0),
        "observed_product_impact_present": any(not bool(row.get("structural_only")) for row in enriched),
        "proposal_created": False,
        "workspace_prepared": False,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["shortlist_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "selected_candidate_id": result["selected_candidate_id"],
        "selection_blocked_by_unbound_value": unbound_blocks,
        "selection_blocked_by_maintenance_budget": maintenance_budget_exhausted,
        "consecutive_structural_installs": structural_streak,
        "blocking_evidence_id": result["blocking_evidence_id"],
        "value_model_digest": result["value_model_digest"],
        "candidates": [row.get("candidate_digest") for row in enriched],
    })
    return result


def value_prioritized_initiative_response(shortlist: Mapping[str, Any]) -> str:
    if shortlist.get("selection_blocked_by_unbound_value"):
        return (
            f"I found higher-value attributable evidence ({shortlist.get('blocking_evidence_id')}, value "
            f"{float(shortlist.get('blocking_evidence_value_score') or 0.0):.2f}) that is not yet bound to a safe implementable candidate. "
            "I did not choose lower-value structural cleanup merely because it is easy to verify. No proposal, workspace, provider request, or source change occurred."
        )
    if shortlist.get("selection_blocked_by_maintenance_budget"):
        return (
            f"The structural-maintenance budget is complete after {int(shortlist.get('consecutive_structural_installs') or 0)} "
            "consecutive installed cleanup initiatives. I did not select another helper extraction. The next supervised cycle must bind "
            "an attributable product defect, reliability issue, performance regression, security finding, or missing capability to a "
            "bounded implementable candidate. No proposal, workspace, provider request, or source change occurred."
        )
    rows = [dict(row) for row in shortlist.get("shortlist") or ()]
    if not rows:
        return "No value-eligible supervised initiative is currently safe to select. The queue remains unchanged."
    selected = rows[0]
    return (
        f"I prioritized {selected.get('title')} at value {float(selected.get('value_score') or 0.0):.2f}. "
        f"The decision is bound to value evidence {selected.get('value_evidence_id')} and dynamic candidate {selected.get('candidate_id')}. "
        "Selection alone creates no proposal, workspace, provider request, source change, installation, promotion, or future authority."
    )


__all__ = [
    "CONTRACT_VERSION",
    "UNBOUND_PRIORITY_MARGIN",
    "STRUCTURAL_BLOCK_FLOOR",
    "MAX_CONSECUTIVE_STRUCTURAL_INSTALLS",
    "value_prioritization_contract",
    "build_value_prioritized_initiative_shortlist",
    "value_prioritized_initiative_response",
]
