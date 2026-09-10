from __future__ import annotations
"""v1326 evidence-bound planning safeguards scaled to actual blast radius."""
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION = "v1326.8"
RISK_TIERS = ("low", "moderate", "high", "critical")


def _path(assessment_id: str, runtime_root=None) -> Path:
    return evidence_root("risk_sensitive_planning", runtime_root) / "records" / f"{assessment_id}.json"


def _score(plan: Mapping[str, Any], critique: Mapping[str, Any] | None, impact: Mapping[str, Any] | None) -> tuple[int, list[str]]:
    value = 0
    reasons: list[str] = []
    steps = list(plan.get("steps") or [])
    mutation_count = sum(bool(x.get("mutation_expected")) for x in steps)
    if mutation_count:
        value += 18
        reasons.append("candidate_mutation_planned")
    if mutation_count >= 4:
        value += 12
        reasons.append("multi_mutation_plan")
    affected = int((impact or {}).get("affected_path_count") or 0)
    if affected >= 8:
        value += 18
        reasons.append("broad_predicted_impact")
    elif affected >= 3:
        value += 8
        reasons.append("multi_path_predicted_impact")
    if (impact or {}).get("ui_impact_predicted"):
        value += 7
        reasons.append("ui_impact_predicted")
    if (impact or {}).get("migration_impact_predicted"):
        value += 18
        reasons.append("migration_impact_predicted")
    if (impact or {}).get("unknown_path_count"):
        value += 12
        reasons.append("unknown_impacted_paths")
    if (impact or {}).get("protected_authority_surface_predicted"):
        value += 55
        reasons.append("protected_authority_surface")
    blocking = int((critique or {}).get("blocking_count") or 0)
    if blocking:
        value += min(35, 15 + blocking * 5)
        reasons.append("blocking_plan_critique")
    severity = str((critique or {}).get("highest_severity") or "info")
    if severity == "critical":
        value += 30
        reasons.append("critical_plan_critique")
    elif severity == "high":
        value += 12
        reasons.append("high_plan_critique")
    return min(100, value), reasons


def _tier(score: int, *, protected: bool, critical_finding: bool) -> str:
    if protected or critical_finding or score >= 75:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 20:
        return "moderate"
    return "low"


def assess_plan_risk(
    plan: Mapping[str, Any],
    *,
    plan_critique: Mapping[str, Any] | None = None,
    impact_analysis: Mapping[str, Any] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    if not plan.get("plan_id") or not plan.get("steps"):
        raise ValueError("constructed_plan_required")
    forbidden = ("execution_authorized", "project_mutation_authorized", "source_application_authorized", "approval_consumed")
    if any(bool(plan.get(key)) for key in forbidden):
        raise ValueError("authority_bearing_plan_rejected")
    impact = impact_analysis or {}
    critique = plan_critique or {}
    score, reasons = _score(plan, critique, impact)
    protected = bool(impact.get("protected_authority_surface_predicted"))
    critical_finding = str(critique.get("highest_severity") or "") == "critical"
    tier = _tier(score, protected=protected, critical_finding=critical_finding)
    policy = {
        "low": ("candidate_workspace", "standard_review", "focused_verification", "active_grant_must_cover_execution"),
        "moderate": ("disposable_candidate_workspace", "expanded_review", "focused_plus_integration", "active_grant_must_cover_execution"),
        "high": ("disposable_worktree_or_equivalent", "independent_expanded_review", "broad_affected_verification", "exact_operator_review_required"),
        "critical": ("protected_isolated_candidate", "protected_core_review", "broad_segmented_or_stronger", "separate_protected_action_approval_required"),
    }[tier]
    blockers = int(critique.get("blocking_count") or 0)
    planning_progress_allowed = blockers == 0 and not protected
    assessment_id = "risk_" + digest({
        "plan": plan.get("plan_id"), "manifest": plan.get("source_manifest_digest"), "critique": critique.get("critique_id"),
        "impact": impact.get("analysis_id"), "score": score, "tier": tier, "reasons": sorted(reasons),
    })[:24]
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "assessment_id": assessment_id,
        "plan_id": plan.get("plan_id"),
        "goal_digest": plan.get("goal_digest"),
        "source_manifest_digest": plan.get("source_manifest_digest"),
        "critique_id": critique.get("critique_id"),
        "impact_analysis_id": impact.get("analysis_id"),
        "risk_score": score,
        "risk_tier": tier,
        "reason_codes": sorted(set(reasons)),
        "required_isolation": policy[0],
        "required_review_depth": policy[1],
        "required_verification_breadth": policy[2],
        "approval_requirement": policy[3],
        "planning_progress_allowed": planning_progress_allowed,
        "protected_surface": protected,
        "requirements_are_not_grants": True,
        "approval_granted": False,
        "action_executed": False,
        **PLANNING_DENIED_AUTHORITY,
    })
    atomic_json(_path(assessment_id, runtime_root), row)
    return {
        "ok": True,
        "status": "risk_planning_blocked" if not planning_progress_allowed else "risk_plan_ready",
        "risk_sensitive_planning": public_risk_sensitive_planning(row),
        "action_executed": False,
        **PLANNING_DENIED_AUTHORITY,
    }


def public_risk_sensitive_planning(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "assessment_id": row.get("assessment_id"),
        "plan_id": row.get("plan_id"),
        "goal_digest": row.get("goal_digest"),
        "source_manifest_digest": row.get("source_manifest_digest"),
        "critique_id": row.get("critique_id"),
        "impact_analysis_id": row.get("impact_analysis_id"),
        "risk_score": int(row.get("risk_score") or 0),
        "risk_tier": row.get("risk_tier"),
        "reason_codes": list(row.get("reason_codes") or []),
        "required_isolation": row.get("required_isolation"),
        "required_review_depth": row.get("required_review_depth"),
        "required_verification_breadth": row.get("required_verification_breadth"),
        "approval_requirement": row.get("approval_requirement"),
        "planning_progress_allowed": bool(row.get("planning_progress_allowed")),
        "protected_surface": bool(row.get("protected_surface")),
        "requirements_are_not_grants": True,
        "approval_granted": False,
        "read_only": True,
        "action_executed": False,
        **PLANNING_DENIED_AUTHORITY,
    }


def load_risk_sensitive_planning(assessment_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_path(str(assessment_id), runtime_root))
    if not row or not valid(row):
        return {}
    return row if include_private else public_risk_sensitive_planning(row)


def process_risk_sensitive_planning_control(text: str, *, plan=None, plan_critique=None, impact_analysis=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show risk-sensitive planning", "inspect risk-sensitive planning", "show planning risk"}:
        return {"active": False}
    if not plan:
        return {"active": True, "ok": False, "status": "constructed_plan_required", "action_executed": False, **PLANNING_DENIED_AUTHORITY}
    return {"active": True, **assess_plan_risk(plan, plan_critique=plan_critique, impact_analysis=impact_analysis, runtime_root=runtime_root)}


__all__ = ["CONTRACT_VERSION", "RISK_TIERS", "assess_plan_risk", "public_risk_sensitive_planning", "load_risk_sensitive_planning", "process_risk_sensitive_planning_control"]
