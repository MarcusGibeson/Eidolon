from __future__ import annotations

"""v1263.0-v1263.2 evidence-bound priority selection foundations.

Priority selection is a read-only judgment artifact derived from a validated
v1262 backlog.  It may rank candidate work and identify a preferred item, but
it cannot create a development proposal, schedule work, execute anything,
apply changes, or grant self-modification authority.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY
from development_backlog_generation_reliability import validate_backlog_reliability

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1263.2"
MAX_PRIORITY_CONTEXT_ROWS = 64

VALUE_LEVELS = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
REVERSIBILITY_LEVELS = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
EFFORT_COST = {"small": 1, "medium": 2, "large": 3, "unknown": 3}
UNCERTAINTY_COST = {"low": 1, "medium": 2, "high": 3}
RISK_COST = {"low": 1, "medium": 2, "high": 3, "unknown": 3}
DEPENDENCY_STATES = {"ready", "blocked"}
SELECTION_STATUSES = {
    "priority_selected",
    "no_defensible_selection_empty_backlog",
    "no_defensible_selection_tie",
    "no_defensible_selection_all_blocked",
}
FACTOR_WEIGHTS = {
    "user_value": 3,
    "reliability_impact": 4,
    "urgency": 3,
    "reversibility": 1,
    "effort_cost": 2,
    "uncertainty_cost": 2,
    "risk_cost": 1,
}

PRIORITY_DENIED_AUTHORITY = {
    **BACKLOG_DENIED_AUTHORITY,
    "priority_selection_execution_authorized": False,
    "priority_selection_scheduling_authorized": False,
    "priority_selection_proposal_authorized": False,
    "priority_selection_application_authorized": False,
    "priority_selection_self_modification_authorized": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _default_factor_bands(item: Mapping[str, Any], *, depended_on: bool) -> dict[str, str]:
    category = str(item.get("category") or "")
    objective = str(item.get("objective_code") or "")
    user = {
        "reliability_candidate": "critical",
        "test_coverage_candidate": "high",
        "evidence_resolution": "high",
        "evidence_acquisition": "medium",
        "known_limitation_candidate": "medium",
        "maintenance_investigation": "low",
        "documentation_candidate": "low",
        "configuration_candidate": "low",
    }.get(category, "unknown")
    reliability = {
        "reliability_candidate": "critical",
        "test_coverage_candidate": "high",
        "evidence_resolution": "high",
        "evidence_acquisition": "medium",
        "known_limitation_candidate": "medium",
        "maintenance_investigation": "low",
        "documentation_candidate": "low",
        "configuration_candidate": "low",
    }.get(category, "unknown")
    urgency = {
        "reliability_candidate": "high",
        "test_coverage_candidate": "medium",
        "evidence_resolution": "high" if depended_on else "medium",
        "evidence_acquisition": "medium",
        "known_limitation_candidate": "medium",
        "maintenance_investigation": "low",
        "documentation_candidate": "low",
        "configuration_candidate": "low",
    }.get(category, "unknown")
    if objective == "repair_observed_python_parse_failures" or objective.startswith("investigate_runtime_health_signal:"):
        urgency = "critical"
    reversibility = {
        "evidence_acquisition": "high",
        "evidence_resolution": "high",
        "maintenance_investigation": "high",
        "known_limitation_candidate": "high",
        "documentation_candidate": "high",
        "test_coverage_candidate": "medium",
        "configuration_candidate": "medium",
        "reliability_candidate": "medium",
    }.get(category, "unknown")
    return {
        "user_value": user,
        "reliability_impact": reliability,
        "urgency": urgency,
        "reversibility": reversibility,
    }


def _validate_priority_context(priority_context: Iterable[Mapping[str, Any]], objective_codes: set[str]) -> dict[str, Mapping[str, Any]]:
    rows = list(priority_context)
    if len(rows) > MAX_PRIORITY_CONTEXT_ROWS:
        raise ValueError("priority_context_too_large")
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        code = str(row.get("objective_code") or "")
        if not code or code not in objective_codes or code in out:
            raise ValueError("priority_context_objective_invalid_or_duplicate")
        for key in ("user_value", "urgency"):
            if key in row and str(row.get(key)) not in VALUE_LEVELS:
                raise ValueError("priority_context_value_invalid")
        if "reversibility" in row and str(row.get("reversibility")) not in REVERSIBILITY_LEVELS:
            raise ValueError("priority_context_reversibility_invalid")
        digest = str(row.get("evidence_digest") or "")
        if digest and not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("priority_context_evidence_digest_invalid")
        out[code] = row
    return out


def _rank_with_ties(rows: list[dict[str, Any]]) -> None:
    last_score: int | None = None
    rank = 0
    ordinal = 0
    for row in rows:
        ordinal += 1
        score = int(row.get("net_score") or 0)
        if last_score is None or score != last_score:
            rank = ordinal
            last_score = score
        row["priority_rank"] = rank


def select_priority_from_backlog(
    backlog: Mapping[str, Any], *, priority_context: Iterable[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    validation = validate_backlog_reliability(backlog)
    if not validation.get("ok"):
        raise ValueError("invalid_development_backlog")

    items = list(backlog.get("items") or [])
    item_ids = {str(row.get("work_item_id") or "") for row in items}
    objective_codes = {str(row.get("objective_code") or "") for row in items}
    context = _validate_priority_context(priority_context, objective_codes)
    depended_on = {
        str(dep)
        for row in items
        for dep in (row.get("dependency_item_ids") or [])
        if str(dep) in item_ids
    }
    evaluations: list[dict[str, Any]] = []

    for item in items:
        item_id = str(item.get("work_item_id") or "")
        objective = str(item.get("objective_code") or "")
        defaults = _default_factor_bands(item, depended_on=item_id in depended_on)
        explicit = context.get(objective, {})
        factors: dict[str, Any] = {}
        for key in ("user_value", "urgency", "reversibility"):
            band = str(explicit.get(key) or defaults[key])
            levels = REVERSIBILITY_LEVELS if key == "reversibility" else VALUE_LEVELS
            factors[key] = {
                "band": band,
                "points": levels[band],
                "basis": "explicit_bounded_context" if key in explicit else "conservative_rule_inference",
                "epistemic_status": "observed_input" if key in explicit else "inferred",
            }
        reliability_band = defaults["reliability_impact"]
        factors["reliability_impact"] = {
            "band": reliability_band,
            "points": VALUE_LEVELS[reliability_band],
            "basis": "backlog_category_and_objective",
            "epistemic_status": "inferred",
        }
        effort_band = str((item.get("estimated_effort") or {}).get("band") or "unknown")
        uncertainty_band = str((item.get("uncertainty") or {}).get("level") or "high")
        risk_band = str(item.get("risk_band") or "unknown")
        factors["effort_cost"] = {"band": effort_band, "points": EFFORT_COST[effort_band], "basis": "v1262_estimated_effort", "epistemic_status": "observed_input"}
        factors["uncertainty_cost"] = {"band": uncertainty_band, "points": UNCERTAINTY_COST[uncertainty_band], "basis": "v1262_uncertainty", "epistemic_status": "observed_input"}
        factors["risk_cost"] = {"band": risk_band, "points": RISK_COST[risk_band], "basis": "v1262_risk_band", "epistemic_status": "observed_input"}
        dependencies = [str(x) for x in item.get("dependency_item_ids") or []]
        dependency_state = "ready" if not dependencies else "blocked"
        benefit = (
            factors["user_value"]["points"] * FACTOR_WEIGHTS["user_value"]
            + factors["reliability_impact"]["points"] * FACTOR_WEIGHTS["reliability_impact"]
            + factors["urgency"]["points"] * FACTOR_WEIGHTS["urgency"]
            + factors["reversibility"]["points"] * FACTOR_WEIGHTS["reversibility"]
        )
        cost = (
            factors["effort_cost"]["points"] * FACTOR_WEIGHTS["effort_cost"]
            + factors["uncertainty_cost"]["points"] * FACTOR_WEIGHTS["uncertainty_cost"]
            + factors["risk_cost"]["points"] * FACTOR_WEIGHTS["risk_cost"]
        )
        row = {
            "work_item_id": item_id,
            "work_item_digest": str(item.get("work_item_digest") or ""),
            "objective_code": objective,
            "category": str(item.get("category") or ""),
            "factors": factors,
            "benefit_score": benefit,
            "cost_score": cost,
            "net_score": benefit - cost,
            "dependency_readiness": dependency_state,
            "dependency_item_ids": dependencies,
            "eligible": dependency_state == "ready",
            "priority_rank": None,
            "priority_context_evidence_digest": str(explicit.get("evidence_digest") or ""),
            "content_minimized": True,
        }
        row["evaluation_digest"] = _digest(row)
        evaluations.append(row)

    eligible = sorted(
        (row for row in evaluations if row["eligible"]),
        key=lambda row: (-int(row["net_score"]), str(row["objective_code"]), str(row["work_item_id"])),
    )
    _rank_with_ties(eligible)
    ranks = {row["work_item_id"]: row["priority_rank"] for row in eligible}
    for row in evaluations:
        row["priority_rank"] = ranks.get(row["work_item_id"])
        row["evaluation_digest"] = _digest({k: v for k, v in row.items() if k != "evaluation_digest"})
    evaluations = sorted(evaluations, key=lambda row: (row["priority_rank"] is None, row["priority_rank"] or 10**9, str(row["objective_code"]), str(row["work_item_id"])))

    selected_id: str | None = None
    tied_ids: list[str] = []
    status: str
    margin: int | None = None
    confidence = "none"
    near_tie = False
    if not items:
        status = "no_defensible_selection_empty_backlog"
    elif not eligible:
        status = "no_defensible_selection_all_blocked"
    else:
        top_score = int(eligible[0]["net_score"])
        tied_ids = sorted(row["work_item_id"] for row in eligible if int(row["net_score"]) == top_score)
        if len(tied_ids) > 1:
            status = "no_defensible_selection_tie"
        else:
            status = "priority_selected"
            selected_id = eligible[0]["work_item_id"]
            if len(eligible) == 1:
                confidence = "high"
            else:
                margin = top_score - int(eligible[1]["net_score"])
                near_tie = margin <= 3
                confidence = "low" if margin <= 3 else "medium" if margin <= 9 else "high"

    comparative_rationale: list[dict[str, Any]] = []
    selection_reason_codes: list[str] = []
    if status == "priority_selected" and selected_id is not None:
        selected_eval = next(row for row in evaluations if row["work_item_id"] == selected_id)
        selection_reason_codes.append("unique_highest_eligible_net_score")
        if near_tie:
            selection_reason_codes.append("near_tie_operator_review_required")
        for other in evaluations:
            if other["work_item_id"] == selected_id:
                continue
            advantage_codes: list[str] = []
            if other["dependency_readiness"] == "blocked":
                advantage_codes.append("alternative_dependency_blocked")
            for factor in ("user_value", "reliability_impact", "urgency", "reversibility"):
                if selected_eval["factors"][factor]["points"] > other["factors"][factor]["points"]:
                    advantage_codes.append(f"higher_{factor}")
            for factor in ("effort_cost", "uncertainty_cost", "risk_cost"):
                if selected_eval["factors"][factor]["points"] < other["factors"][factor]["points"]:
                    advantage_codes.append(f"lower_{factor}")
            comparative_rationale.append({
                "alternative_work_item_id": other["work_item_id"],
                "selected_net_score_advantage": int(selected_eval["net_score"]) - int(other["net_score"]),
                "alternative_dependency_readiness": other["dependency_readiness"],
                "advantage_codes": sorted(set(advantage_codes)),
                "content_minimized": True,
            })
    elif status == "no_defensible_selection_tie":
        selection_reason_codes.append("exact_top_score_tie")
    elif status == "no_defensible_selection_empty_backlog":
        selection_reason_codes.append("no_candidate_work_items")
    elif status == "no_defensible_selection_all_blocked":
        selection_reason_codes.append("all_candidates_dependency_blocked")

    selection = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "backlog_digest": str(backlog.get("backlog_digest") or ""),
        "assessment_digest": str(backlog.get("assessment_digest") or ""),
        "source_manifest_digest": str(backlog.get("source_manifest_digest") or ""),
        "project_type": str(backlog.get("project_type") or ""),
        "evaluations": evaluations,
        "evaluated_item_count": len(evaluations),
        "eligible_item_count": len(eligible),
        "selected_work_item_id": selected_id,
        "tied_work_item_ids": tied_ids if status == "no_defensible_selection_tie" else [],
        "selection_confidence": confidence,
        "selection_margin": margin,
        "near_tie": near_tie,
        "selection_reason_codes": selection_reason_codes,
        "comparative_rationale": comparative_rationale,
        "factor_weights": dict(FACTOR_WEIGHTS),
        "ranking_semantics": "deterministic_evidence_bound_priority_judgment",
        "backlog_mutated": False,
        "schedule_created": False,
        "development_proposal_created": False,
        "execution_started": False,
        "project_modified": False,
        "operator_review_required": True,
        "raw_source_content_stored": False,
        "raw_evidence_content_stored": False,
        "content_minimized": True,
        "read_only": True,
        **PRIORITY_DENIED_AUTHORITY,
    }
    selection["selection_digest"] = _digest(selection)
    return selection


def validate_priority_selection(selection: Mapping[str, Any], backlog: Mapping[str, Any]) -> dict[str, Any]:
    backlog_valid = bool(validate_backlog_reliability(backlog).get("ok"))
    supplied = str(selection.get("selection_digest") or "")
    digest_ok = bool(supplied and supplied == _digest({k: v for k, v in selection.items() if k != "selection_digest"}))
    lineage_ok = (
        str(selection.get("backlog_digest") or "") == str(backlog.get("backlog_digest") or "")
        and str(selection.get("assessment_digest") or "") == str(backlog.get("assessment_digest") or "")
        and str(selection.get("source_manifest_digest") or "") == str(backlog.get("source_manifest_digest") or "")
    )
    evaluations = list(selection.get("evaluations") or [])
    backlog_items = {str(row.get("work_item_id") or ""): row for row in backlog.get("items") or []}
    item_ids = set(backlog_items)
    evaluation_ids = [str(row.get("work_item_id") or "") for row in evaluations]
    evaluation_set_ok = len(evaluation_ids) == len(set(evaluation_ids)) and set(evaluation_ids) == item_ids
    weights_ok = selection.get("factor_weights") == FACTOR_WEIGHTS
    evaluation_digests_ok = all(
        str(row.get("evaluation_digest") or "") == _digest({k: v for k, v in row.items() if k != "evaluation_digest"})
        for row in evaluations
    )
    factors_ok = True
    arithmetic_ok = True
    dependency_ok = True
    work_item_binding_ok = True
    for row in evaluations:
        item = backlog_items.get(str(row.get("work_item_id") or ""))
        if item is None:
            work_item_binding_ok = False
            continue
        if str(row.get("work_item_digest") or "") != str(item.get("work_item_digest") or ""):
            work_item_binding_ok = False
        factors = row.get("factors") or {}
        if set(factors.keys()) != set(FACTOR_WEIGHTS) or row.get("dependency_readiness") not in DEPENDENCY_STATES or row.get("content_minimized") is not True:
            factors_ok = False
            continue
        expected_points = {
            "user_value": VALUE_LEVELS.get(str((factors.get("user_value") or {}).get("band"))),
            "reliability_impact": VALUE_LEVELS.get(str((factors.get("reliability_impact") or {}).get("band"))),
            "urgency": VALUE_LEVELS.get(str((factors.get("urgency") or {}).get("band"))),
            "reversibility": REVERSIBILITY_LEVELS.get(str((factors.get("reversibility") or {}).get("band"))),
            "effort_cost": EFFORT_COST.get(str((factors.get("effort_cost") or {}).get("band"))),
            "uncertainty_cost": UNCERTAINTY_COST.get(str((factors.get("uncertainty_cost") or {}).get("band"))),
            "risk_cost": RISK_COST.get(str((factors.get("risk_cost") or {}).get("band"))),
        }
        if any(value is None for value in expected_points.values()) or any((factors.get(key) or {}).get("points") != value for key, value in expected_points.items()):
            factors_ok = False
            continue
        benefit = (
            expected_points["user_value"] * FACTOR_WEIGHTS["user_value"]
            + expected_points["reliability_impact"] * FACTOR_WEIGHTS["reliability_impact"]
            + expected_points["urgency"] * FACTOR_WEIGHTS["urgency"]
            + expected_points["reversibility"] * FACTOR_WEIGHTS["reversibility"]
        )
        cost = (
            expected_points["effort_cost"] * FACTOR_WEIGHTS["effort_cost"]
            + expected_points["uncertainty_cost"] * FACTOR_WEIGHTS["uncertainty_cost"]
            + expected_points["risk_cost"] * FACTOR_WEIGHTS["risk_cost"]
        )
        if row.get("benefit_score") != benefit or row.get("cost_score") != cost or row.get("net_score") != benefit - cost:
            arithmetic_ok = False
        dependencies = [str(x) for x in item.get("dependency_item_ids") or []]
        expected_state = "ready" if not dependencies else "blocked"
        if row.get("dependency_item_ids") != dependencies or row.get("dependency_readiness") != expected_state or row.get("eligible") is not (expected_state == "ready"):
            dependency_ok = False
    eligible = sorted(
        (row for row in evaluations if row.get("eligible") is True),
        key=lambda row: (-int(row.get("net_score") or 0), str(row.get("objective_code") or ""), str(row.get("work_item_id") or "")),
    )
    expected_ranks: dict[str, int] = {}
    last_score: int | None = None
    rank = 0
    for ordinal, row in enumerate(eligible, 1):
        score = int(row.get("net_score") or 0)
        if last_score is None or score != last_score:
            rank = ordinal
            last_score = score
        expected_ranks[str(row.get("work_item_id") or "")] = rank
    ranks_ok = all(row.get("priority_rank") == expected_ranks.get(str(row.get("work_item_id") or "")) for row in evaluations)
    status = str(selection.get("status") or "")
    status_ok = status in SELECTION_STATUSES
    selected = selection.get("selected_work_item_id")
    if not item_ids:
        semantic_expected = status == "no_defensible_selection_empty_backlog" and selected is None
    elif not eligible:
        semantic_expected = status == "no_defensible_selection_all_blocked" and selected is None
    else:
        top_score = int(eligible[0].get("net_score") or 0)
        top_ids = [str(row.get("work_item_id") or "") for row in eligible if int(row.get("net_score") or 0) == top_score]
        if len(top_ids) > 1:
            semantic_expected = status == "no_defensible_selection_tie" and selected is None and sorted(selection.get("tied_work_item_ids") or []) == sorted(top_ids)
        else:
            semantic_expected = status == "priority_selected" and selected == top_ids[0]
    selection_semantics_ok = semantic_expected
    authority_ok = all(selection.get(key) is expected for key, expected in PRIORITY_DENIED_AUTHORITY.items())
    no_action = not any(bool(selection.get(key)) for key in ("schedule_created", "development_proposal_created", "execution_started", "project_modified", "backlog_mutated"))
    ok = backlog_valid and digest_ok and lineage_ok and evaluation_set_ok and weights_ok and evaluation_digests_ok and factors_ok and arithmetic_ok and dependency_ok and work_item_binding_ok and ranks_ok and status_ok and selection_semantics_ok and authority_ok and no_action
    return {
        "ok": ok,
        "status": "priority_selection_valid" if ok else "priority_selection_invalid",
        "backlog_valid": backlog_valid,
        "digest_valid": digest_ok,
        "lineage_valid": lineage_ok,
        "evaluation_set_valid": evaluation_set_ok,
        "factor_weights_valid": weights_ok,
        "evaluation_digests_valid": evaluation_digests_ok,
        "factor_contracts_valid": factors_ok,
        "score_arithmetic_valid": arithmetic_ok,
        "dependency_semantics_valid": dependency_ok,
        "work_item_binding_valid": work_item_binding_ok,
        "ranking_valid": ranks_ok,
        "selection_semantics_valid": selection_semantics_ok,
        "authority_denied": authority_ok,
        "no_action_created": no_action,
        "selection_digest": supplied,
        "read_only": True,
        **PRIORITY_DENIED_AUTHORITY,
    }


def public_priority_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(selection.get("ok")),
        "status": str(selection.get("status") or ""),
        "project_type": str(selection.get("project_type") or ""),
        "evaluated_item_count": int(selection.get("evaluated_item_count") or 0),
        "eligible_item_count": int(selection.get("eligible_item_count") or 0),
        "selected_work_item_id": selection.get("selected_work_item_id"),
        "selection_confidence": str(selection.get("selection_confidence") or "none"),
        "selection_margin": selection.get("selection_margin"),
        "near_tie": bool(selection.get("near_tie")),
        "tied_item_count": len(selection.get("tied_work_item_ids") or []),
        "backlog_digest": str(selection.get("backlog_digest") or ""),
        "selection_digest": str(selection.get("selection_digest") or ""),
        "operator_review_required": True,
        "raw_evidence_content_exposed": False,
        "raw_paths_exposed": False,
        "content_minimized": True,
        "read_only": True,
        **PRIORITY_DENIED_AUTHORITY,
    }


__all__ = [
    "SCHEMA_VERSION", "CONTRACT_VERSION", "MAX_PRIORITY_CONTEXT_ROWS", "VALUE_LEVELS", "REVERSIBILITY_LEVELS",
    "FACTOR_WEIGHTS", "PRIORITY_DENIED_AUTHORITY", "select_priority_from_backlog", "validate_priority_selection",
    "public_priority_selection",
]
