from __future__ import annotations

"""v1264.0-v1264.2 evidence-bound alternative planning and simulation foundations.

The planner consumes a validated v1263 priority decision and its v1262 backlog,
constructs multiple bounded approaches for the uniquely selected work item,
predicts failure modes, compares tradeoffs, and may select one defensible plan.
It is advisory only and grants no execution, application, installation, release,
or self-modification authority.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from development_backlog_generation_reliability import validate_backlog_reliability
from priority_selection_foundations import PRIORITY_DENIED_AUTHORITY, validate_priority_selection
from alternative_planning_foundations_alternative_plan import (
    SymbolDependencies as _AlternativePlanningFoundationsAlternativePlanSymbolDependencies,
    public_alternative_plan as _public_alternative_plan_implementation,
    validate_alternative_plan as _validate_alternative_plan_implementation,
)


SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1264.2"
MAX_APPROACHES = 4
MAX_PLAN_CONTEXT_ROWS = 8
BANDS = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
COST_BANDS = {"small": 1, "medium": 2, "large": 3, "unknown": 3}
RISK_COST = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 3}
UNCERTAINTY_COST = {"low": 1, "medium": 2, "high": 3, "unknown": 3}
REVERSIBILITY_POINTS = {"low": 1, "medium": 2, "high": 3, "unknown": 0}
PLAN_STATUSES = {
    "alternative_plan_selected",
    "no_defensible_plan_no_priority_selection",
    "no_defensible_plan_approach_tie",
}

PLAN_DENIED_AUTHORITY = {
    **PRIORITY_DENIED_AUTHORITY,
    "alternative_planning_execution_authorized": False,
    "alternative_planning_application_authorized": False,
    "alternative_planning_provider_authorized": False,
    "alternative_planning_self_modification_authorized": False,
    "alternative_planning_release_authorized": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _strategy_specs(category: str, objective: str) -> list[dict[str, Any]]:
    if category == "evidence_acquisition":
        return [
            {
                "strategy_code": "focused_existing_verification",
                "implementation_steps": ["resolve_existing_verification_surface", "run_smallest_relevant_existing_checks", "record_bounded_outcome_evidence"],
                "verification_steps": ["evidence_digest_present", "outcome_is_current_or_blocked", "no_source_mutation"],
                "effort": "small", "risk": "low", "uncertainty": "low", "reversibility": "high", "success_confidence": "high",
                "failure_modes": [
                    ("verification_surface_incomplete", "medium", "low", "expand_only_to_adjacent_existing_checks", "focused_checks_do_not_cover_relevant_surface"),
                    ("environment_blocks_verification", "low", "medium", "record_genuine_blocker_without_repair", "tooling_or_environment_unavailable"),
                ],
            },
            {
                "strategy_code": "layered_focused_then_regression",
                "implementation_steps": ["resolve_existing_verification_surface", "run_focused_checks", "expand_to_retained_regression_if_focused_passes", "record_layered_evidence"],
                "verification_steps": ["focused_outcome_recorded", "regression_scope_reason_recorded", "no_source_mutation"],
                "effort": "medium", "risk": "low", "uncertainty": "low", "reversibility": "high", "success_confidence": "high",
                "failure_modes": [
                    ("regression_cost_exceeds_bound", "medium", "low", "stop_at_declared_bound_and_record_partial_evidence", "planned_regression_bound_exceeded"),
                    ("environment_blocks_verification", "low", "medium", "record_genuine_blocker_without_repair", "tooling_or_environment_unavailable"),
                ],
            },
            {
                "strategy_code": "fresh_extract_validation_campaign",
                "implementation_steps": ["materialize_clean_source_copy", "run_relevant_checks_in_clean_copy", "compare_result_with_current_source_context", "record_clean_environment_evidence"],
                "verification_steps": ["clean_copy_manifest_bound", "result_evidence_recorded", "active_source_untouched"],
                "effort": "large", "risk": "low", "uncertainty": "medium", "reversibility": "high", "success_confidence": "medium",
                "failure_modes": [
                    ("clean_environment_differs_from_operator_runtime", "medium", "medium", "label_environment_scope_explicitly", "result_cannot_be_generalized_to_active_runtime"),
                    ("validation_campaign_exceeds_bound", "medium", "low", "stop_and_record_partial_evidence", "campaign_budget_exhausted"),
                ],
            },
        ]
    if category == "evidence_resolution":
        return [
            {
                "strategy_code": "reproduce_conflicting_signal_under_same_conditions",
                "implementation_steps": ["bind_conflicting_evidence", "normalize_test_conditions", "repeat_bounded_observation", "record_resolution_or_remaining_conflict"],
                "verification_steps": ["both_evidence_sides_preserved", "conditions_digest_recorded", "conflict_disposition_explicit"],
                "effort": "small", "risk": "low", "uncertainty": "medium", "reversibility": "high", "success_confidence": "high",
                "failure_modes": [("conflict_not_reproducible", "medium", "low", "retain_unknown_and_request_new_evidence", "neither_prior_signal_reproduces")],
            },
            {
                "strategy_code": "independent_secondary_check",
                "implementation_steps": ["bind_conflicting_evidence", "select_independent_bounded_check", "run_secondary_check", "triangulate_result"],
                "verification_steps": ["secondary_check_independent", "triangulation_rationale_recorded", "conflict_not_silently_overwritten"],
                "effort": "medium", "risk": "low", "uncertainty": "medium", "reversibility": "high", "success_confidence": "medium",
                "failure_modes": [("secondary_check_also_conflicts", "medium", "medium", "retain_conflict_and_block_downstream_work", "third_signal_does_not_resolve_conflict")],
            },
            {
                "strategy_code": "defer_until_stronger_evidence",
                "implementation_steps": ["record_conflict_as_blocker", "define_missing_evidence_requirement", "defer_dependent_work"],
                "verification_steps": ["blocker_explicit", "no_dependent_execution", "evidence_requirement_bounded"],
                "effort": "small", "risk": "low", "uncertainty": "high", "reversibility": "high", "success_confidence": "low",
                "failure_modes": [("evidence_never_arrives", "high", "low", "periodic_operator_review_only", "dependency_remains_blocked")],
            },
        ]
    if category in {"reliability_candidate", "test_coverage_candidate"}:
        return [
            {
                "strategy_code": "diagnose_then_minimal_repair",
                "implementation_steps": ["reproduce_bounded_signal", "form_competing_causes", "run_discriminating_diagnostic", "repair_smallest_supported_surface", "run_focused_verification"],
                "verification_steps": ["cause_supported_by_evidence", "focused_checks_pass", "affected_regression_scope_defined"],
                "effort": "medium", "risk": "medium", "uncertainty": "medium", "reversibility": "high", "success_confidence": "high",
                "failure_modes": [("symptom_repaired_not_cause", "medium", "medium", "require_discriminating_diagnostic_before_change", "failure_recurs_under_focused_check"), ("repair_affects_adjacent_behavior", "low", "high", "expand_regression_by_affected_surface", "adjacent_regression_fails")],
            },
            {
                "strategy_code": "guarded_structural_repair",
                "implementation_steps": ["map_affected_boundary", "design_structural_fix", "implement_in_isolation", "run_focused_and_adjacent_regressions", "review_diff_and_rollback"],
                "verification_steps": ["boundary_behavior_preserved", "focused_and_adjacent_checks_pass", "rollback_defined"],
                "effort": "large", "risk": "high", "uncertainty": "medium", "reversibility": "medium", "success_confidence": "medium",
                "failure_modes": [("scope_expands_beyond_evidence", "medium", "high", "abort_if_changed_surface_exceeds_plan", "unexpected_components_require_change"), ("structural_fix_regresses_compatibility", "medium", "high", "retain_compatibility_checks_and_rollback", "retained_regression_fails")],
            },
            {
                "strategy_code": "additional_evidence_before_repair",
                "implementation_steps": ["collect_more_failure_evidence", "reassess_candidate_causes", "defer_mutation_until_confidence_improves"],
                "verification_steps": ["new_evidence_changes_or_confirms_diagnosis", "mutation_remains_deferred_until_threshold"],
                "effort": "small", "risk": "low", "uncertainty": "high", "reversibility": "high", "success_confidence": "medium",
                "failure_modes": [("additional_evidence_not_discriminating", "medium", "low", "stop_at_bound_and_record_blocker", "confidence_does_not_improve")],
            },
        ]
    return [
        {
            "strategy_code": "bounded_targeted_investigation",
            "implementation_steps": ["inspect_supported_signal", "classify_actionability", "define_smallest_next_change_or_deferral", "verify_disposition"],
            "verification_steps": ["evidence_linkage_preserved", "disposition_explicit", "scope_bounded"],
            "effort": "small", "risk": "low", "uncertainty": "medium", "reversibility": "high", "success_confidence": "high",
            "failure_modes": [("signal_not_actionable", "medium", "low", "record_non_defect_or_defer", "followup_evidence_does_not_support_change")],
        },
        {
            "strategy_code": "component_cluster_review",
            "implementation_steps": ["map_related_component_cluster", "inspect_related_signals", "compare_cross_component implications", "define_bounded_disposition"],
            "verification_steps": ["cluster_scope_recorded", "cross_component_assumptions_explicit", "no_unsupported_defect_claim"],
            "effort": "medium", "risk": "low", "uncertainty": "medium", "reversibility": "high", "success_confidence": "medium",
            "failure_modes": [("cluster_scope_too_broad", "medium", "medium", "stop_at_component_boundary", "inspection_budget_exceeded")],
        },
        {
            "strategy_code": "historical_evidence_crosscheck",
            "implementation_steps": ["bind_current_signal", "compare_retained_evidence", "identify_changed_assumptions", "record_current_disposition"],
            "verification_steps": ["current_evidence_remains_primary", "historical_evidence_age_explicit", "no_stale_conclusion_promoted"],
            "effort": "medium", "risk": "low", "uncertainty": "high", "reversibility": "high", "success_confidence": "medium",
            "failure_modes": [("historical_context_is_stale", "high", "low", "discard_stale_inference", "historical_assumption_no_longer_matches_current_source")],
        },
    ]


def _validate_plan_context(plan_context: Iterable[Mapping[str, Any]], strategy_codes: set[str]) -> dict[str, Mapping[str, Any]]:
    rows = list(plan_context)
    if len(rows) > MAX_PLAN_CONTEXT_ROWS:
        raise ValueError("plan_context_too_large")
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        code = str(row.get("strategy_code") or "")
        if code not in strategy_codes or code in out:
            raise ValueError("plan_context_strategy_invalid_or_duplicate")
        for key in ("success_confidence", "risk", "uncertainty", "reversibility"):
            if key in row:
                valid = BANDS if key == "success_confidence" else (RISK_COST if key == "risk" else UNCERTAINTY_COST if key == "uncertainty" else REVERSIBILITY_POINTS)
                if str(row.get(key)) not in valid:
                    raise ValueError("plan_context_band_invalid")
        if "effort" in row and str(row.get("effort")) not in COST_BANDS:
            raise ValueError("plan_context_effort_invalid")
        digest = str(row.get("evidence_digest") or "")
        if digest and not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("plan_context_evidence_digest_invalid")
        out[code] = row
    return out


def _failure_mode_row(code: str, likelihood: str, impact: str, mitigation: str, falsifier: str) -> dict[str, Any]:
    row = {
        "failure_code": code,
        "likelihood": likelihood,
        "impact": impact,
        "mitigation_code": mitigation,
        "falsification_condition": falsifier,
        "epistemic_status": "predicted",
        "content_minimized": True,
    }
    row["failure_mode_digest"] = _digest(row)
    return row


def build_alternative_plan(
    selection: Mapping[str, Any],
    backlog: Mapping[str, Any],
    *,
    plan_context: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not validate_backlog_reliability(backlog).get("ok") or not validate_priority_selection(selection, backlog).get("ok"):
        raise ValueError("invalid_priority_lineage")
    if str(selection.get("status") or "") != "priority_selected" or not selection.get("selected_work_item_id"):
        plan = {
            "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "status": "no_defensible_plan_no_priority_selection",
            "selection_digest": str(selection.get("selection_digest") or ""), "backlog_digest": str(backlog.get("backlog_digest") or ""),
            "assessment_digest": str(backlog.get("assessment_digest") or ""), "source_manifest_digest": str(backlog.get("source_manifest_digest") or ""),
            "selected_work_item_id": None, "approaches": [], "selected_approach_id": None, "selection_margin": None,
            "selection_confidence": "none", "assumptions": ["unique_priority_selection_required"], "completion_conditions": [],
            "blocker_conditions": ["priority_selection_not_unique_or_absent"], "operator_review_required": True,
            "execution_started": False, "project_modified": False, "content_minimized": True, "read_only": True, **PLAN_DENIED_AUTHORITY,
        }
        plan["plan_digest"] = _digest(plan)
        return plan

    item_id = str(selection.get("selected_work_item_id") or "")
    item = next((row for row in backlog.get("items") or [] if str(row.get("work_item_id") or "") == item_id), None)
    if item is None:
        raise ValueError("selected_work_item_missing")
    category = str(item.get("category") or "")
    objective = str(item.get("objective_code") or "")
    specs = _strategy_specs(category, objective)[:MAX_APPROACHES]
    context = _validate_plan_context(plan_context, {str(row["strategy_code"]) for row in specs})
    approaches: list[dict[str, Any]] = []
    for ordinal, spec in enumerate(specs, 1):
        code = str(spec["strategy_code"])
        explicit = context.get(code, {})
        success = str(explicit.get("success_confidence") or spec["success_confidence"])
        effort = str(explicit.get("effort") or spec["effort"])
        risk = str(explicit.get("risk") or spec["risk"])
        uncertainty = str(explicit.get("uncertainty") or spec["uncertainty"])
        reversibility = str(explicit.get("reversibility") or spec["reversibility"])
        success_points = BANDS[success]
        reversibility_points = REVERSIBILITY_POINTS[reversibility]
        effort_cost = COST_BANDS[effort]
        risk_cost = RISK_COST[risk]
        uncertainty_cost = UNCERTAINTY_COST[uncertainty]
        score = success_points * 4 + reversibility_points * 2 - effort_cost * 2 - risk_cost * 2 - uncertainty_cost
        failures = [_failure_mode_row(*fm) for fm in spec["failure_modes"]]
        row = {
            "approach_id": hashlib.sha256(f"{item_id}:{code}".encode()).hexdigest()[:20],
            "strategy_code": code,
            "strategy_ordinal": ordinal,
            "work_item_id": item_id,
            "work_item_digest": str(item.get("work_item_digest") or ""),
            "objective_code": objective,
            "category": category,
            "implementation_steps": list(spec["implementation_steps"]),
            "verification_steps": list(spec["verification_steps"]),
            "predicted_failure_modes": failures,
            "failure_mode_count": len(failures),
            "success_confidence": success,
            "estimated_effort": effort,
            "risk_band": risk,
            "uncertainty_band": uncertainty,
            "reversibility": reversibility,
            "simulation_score": score,
            "factor_basis": "explicit_bounded_context" if explicit else "deterministic_strategy_simulation",
            "plan_context_evidence_digest": str(explicit.get("evidence_digest") or ""),
            "epistemic_status": "observed_input_adjusted" if explicit else "inferred_simulation",
            "content_minimized": True,
        }
        row["approach_digest"] = _digest(row)
        approaches.append(row)

    ordered = sorted(approaches, key=lambda row: (-int(row["simulation_score"]), str(row["strategy_code"]), str(row["approach_id"])))
    top_score = int(ordered[0]["simulation_score"])
    tied = [row for row in ordered if int(row["simulation_score"]) == top_score]
    selected_id: str | None = None
    status = "alternative_plan_selected"
    margin: int | None = None
    confidence = "none"
    reason_codes: list[str] = []
    if len(tied) > 1:
        status = "no_defensible_plan_approach_tie"
        reason_codes.append("exact_top_approach_score_tie")
    else:
        selected_id = ordered[0]["approach_id"]
        reason_codes.append("unique_highest_simulation_score")
        if len(ordered) == 1:
            confidence = "high"
        else:
            margin = top_score - int(ordered[1]["simulation_score"])
            confidence = "low" if margin <= 2 else "medium" if margin <= 6 else "high"
            if margin <= 2:
                reason_codes.append("near_tie_operator_review_required")

    rationale: list[dict[str, Any]] = []
    if selected_id:
        chosen = next(row for row in approaches if row["approach_id"] == selected_id)
        for other in approaches:
            if other["approach_id"] == selected_id:
                continue
            advantages: list[str] = []
            if BANDS[chosen["success_confidence"]] > BANDS[other["success_confidence"]]: advantages.append("higher_success_confidence")
            if REVERSIBILITY_POINTS[chosen["reversibility"]] > REVERSIBILITY_POINTS[other["reversibility"]]: advantages.append("higher_reversibility")
            if COST_BANDS[chosen["estimated_effort"]] < COST_BANDS[other["estimated_effort"]]: advantages.append("lower_effort")
            if RISK_COST[chosen["risk_band"]] < RISK_COST[other["risk_band"]]: advantages.append("lower_risk")
            if UNCERTAINTY_COST[chosen["uncertainty_band"]] < UNCERTAINTY_COST[other["uncertainty_band"]]: advantages.append("lower_uncertainty")
            rationale.append({
                "alternative_approach_id": other["approach_id"],
                "selected_score_advantage": int(chosen["simulation_score"]) - int(other["simulation_score"]),
                "advantage_codes": advantages,
                "content_minimized": True,
            })

    plan = {
        "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "status": status,
        "selection_digest": str(selection.get("selection_digest") or ""), "backlog_digest": str(backlog.get("backlog_digest") or ""),
        "assessment_digest": str(backlog.get("assessment_digest") or ""), "source_manifest_digest": str(backlog.get("source_manifest_digest") or ""),
        "selected_work_item_id": item_id, "selected_work_item_digest": str(item.get("work_item_digest") or ""),
        "objective_code": objective, "category": category, "approaches": approaches, "approach_count": len(approaches),
        "selected_approach_id": selected_id, "selection_margin": margin, "selection_confidence": confidence,
        "selection_reason_codes": reason_codes, "comparative_rationale": rationale,
        "assumptions": ["v1263_priority_remains_current", "simulation_predictions_are_not_observed_outcomes", "implementation_authority_is_separate"],
        "completion_conditions": ["selected_approach_verification_steps_satisfied", "predicted_failure_modes_reassessed_against_real_evidence"],
        "blocker_conditions": ["priority_or_backlog_lineage_changes", "source_manifest_becomes_stale", "no_unique_defensible_approach"],
        "planning_semantics": "deterministic_competing_approach_simulation",
        "operator_review_required": True, "execution_started": False, "project_modified": False,
        "development_proposal_created": False, "schedule_created": False, "raw_source_content_stored": False,
        "raw_evidence_content_stored": False, "content_minimized": True, "read_only": True, **PLAN_DENIED_AUTHORITY,
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def _expected_approach_score(row: Mapping[str, Any]) -> int | None:
    try:
        return BANDS[str(row.get("success_confidence"))] * 4 + REVERSIBILITY_POINTS[str(row.get("reversibility"))] * 2 - COST_BANDS[str(row.get("estimated_effort"))] * 2 - RISK_COST[str(row.get("risk_band"))] * 2 - UNCERTAINTY_COST[str(row.get("uncertainty_band"))]
    except KeyError:
        return None


def _build_alternative_planning_foundations_alternative_plan_dependencies() -> _AlternativePlanningFoundationsAlternativePlanSymbolDependencies:
    return _AlternativePlanningFoundationsAlternativePlanSymbolDependencies(
        BANDS=BANDS,
        MAX_APPROACHES=MAX_APPROACHES,
        Mapping=Mapping,
        PLAN_DENIED_AUTHORITY=PLAN_DENIED_AUTHORITY,
        PLAN_STATUSES=PLAN_STATUSES,
        _digest=_digest,
        _expected_approach_score=_expected_approach_score,
        validate_backlog_reliability=validate_backlog_reliability,
        validate_priority_selection=validate_priority_selection,
    )

def validate_alternative_plan(plan: Mapping[str, Any], selection: Mapping[str, Any], backlog: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_alternative_plan_implementation(plan, selection, backlog, _deps=_build_alternative_planning_foundations_alternative_plan_dependencies())



def public_alternative_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    return _public_alternative_plan_implementation(plan, _deps=_build_alternative_planning_foundations_alternative_plan_dependencies())



__all__ = [
    "SCHEMA_VERSION", "CONTRACT_VERSION", "MAX_APPROACHES", "PLAN_DENIED_AUTHORITY", "PLAN_STATUSES",
    "build_alternative_plan", "validate_alternative_plan", "public_alternative_plan",
]
