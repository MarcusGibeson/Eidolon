from __future__ import annotations

"""v1262.0-v1262.2 evidence-bound development backlog foundations.

A backlog is a bounded planning artifact derived only from a validated v1261
assessment.  It is not a proposal, priority decision, approval, execution plan,
or mutation authority.  Items retain only content-minimized evidence lineage.
"""

import hashlib
import json
from typing import Any, Iterable, Mapping

from evidence_based_project_inspection import validate_project_assessment
from evidence_based_project_inspection_foundations import DENIED_AUTHORITY

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1262.2"
MAX_BACKLOG_ITEMS = 32
BACKLOG_CATEGORIES = {
    "evidence_acquisition", "evidence_resolution", "reliability_candidate",
    "test_coverage_candidate", "documentation_candidate", "configuration_candidate",
    "maintenance_investigation", "known_limitation_candidate",
}
EFFORT_BANDS = {"small", "medium", "large", "unknown"}
RISK_BANDS = {"low", "medium", "high", "unknown"}
UNCERTAINTY_LEVELS = {"low", "medium", "high"}

BACKLOG_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "development_proposal_creation_authorized": False,
    "backlog_item_execution_authorized": False,
    "backlog_item_application_authorized": False,
    "backlog_priority_selection_authorized": False,
    "backlog_scheduling_authorized": False,
    "self_update_authorized": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _item(*, category: str, objective_code: str, evidence_ids: Iterable[str], claim_ids: Iterable[str], acceptance_criteria: Iterable[str], dependency_ids: Iterable[str] = (), risks: Iterable[str] = (), uncertainty: str = "medium", uncertainty_reasons: Iterable[str] = (), effort: str = "unknown", effort_reason: str = "insufficient_scope_evidence") -> dict[str, Any]:
    if category not in BACKLOG_CATEGORIES or effort not in EFFORT_BANDS or uncertainty not in UNCERTAINTY_LEVELS:
        raise ValueError("invalid_backlog_item_contract")
    risk_codes = sorted(set(str(x) for x in risks if x))[:12]
    risk_band = "high" if any("high" in x for x in risk_codes) else "medium" if risk_codes else "low"
    row = {
        "category": category,
        "objective_code": str(objective_code)[:160],
        "source_evidence_ids": sorted(set(str(x) for x in evidence_ids if x))[:24],
        "source_claim_ids": sorted(set(str(x) for x in claim_ids if x))[:24],
        "acceptance_criteria": sorted(set(str(x) for x in acceptance_criteria if x))[:16],
        "dependency_item_ids": sorted(set(str(x) for x in dependency_ids if x))[:16],
        "risk_codes": risk_codes,
        "risk_band": risk_band if risk_band in RISK_BANDS else "unknown",
        "uncertainty": {"level": uncertainty, "reason_codes": sorted(set(str(x) for x in uncertainty_reasons if x))[:12]},
        "estimated_effort": {"band": effort, "reason_code": str(effort_reason)[:128]},
        "state": "candidate_backlog_item",
        "operator_review_required": True,
        "priority": None,
        "rank": None,
        "scheduled": False,
        "development_proposal_created": False,
        "execution_authorized": False,
        "application_authorized": False,
        "content_minimized": True,
    }
    semantic = {k: v for k, v in row.items() if k not in {"dependency_item_ids"}}
    row["semantic_key"] = _digest(semantic)
    row["work_item_id"] = f"work_{row['semantic_key'][:24]}"
    row["work_item_digest"] = _digest(row)
    return row


def _claim_map(assessment: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    out: dict[str, list[Mapping[str, Any]]] = {}
    for claim in assessment.get("claims") or []:
        out.setdefault(str(claim.get("claim_code") or ""), []).append(claim)
    return out


def _claim_refs(rows: Iterable[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    claims = list(rows)
    return (
        sorted({str(eid) for row in claims for eid in (row.get("evidence_ids") or []) if eid}),
        sorted({str(row.get("claim_id") or "") for row in claims if row.get("claim_id")}),
    )


def build_backlog_from_assessment(assessment: Mapping[str, Any], *, max_items: int = MAX_BACKLOG_ITEMS) -> dict[str, Any]:
    validation = validate_project_assessment(assessment)
    if not validation.get("ok"):
        raise ValueError("invalid_project_assessment")
    max_items = max(1, min(int(max_items), MAX_BACKLOG_ITEMS))
    claims = _claim_map(assessment)
    evidence = {str(row.get("evidence_id") or ""): row for row in assessment.get("evidence") or []}
    items: list[dict[str, Any]] = []

    def add(**kwargs: Any) -> dict[str, Any]:
        item = _item(**kwargs)
        if not any(old["semantic_key"] == item["semantic_key"] for old in items):
            items.append(item)
        return item

    # Contradictions are always resolved before work that depends on the disputed signal.
    conflict_items: dict[str, str] = {}
    for code in sorted(set(str(x) for x in assessment.get("contradiction_codes") or [])):
        rows = claims.get(f"conflicting_evidence:{code}", [])
        eids, cids = _claim_refs(rows)
        item = add(category="evidence_resolution", objective_code=f"resolve_conflicting_evidence:{code}", evidence_ids=eids, claim_ids=cids,
                   acceptance_criteria=["conflicting_evidence_resolved_or_explicitly_left_unknown", "replacement_assessment_records_disposition"],
                   risks=["decision_on_conflicting_evidence_medium_risk"], uncertainty="high", uncertainty_reasons=["explicit_evidence_disagrees"], effort="small", effort_reason="bounded_evidence_reconciliation")
        conflict_items[code] = item["work_item_id"]

    if claims.get("python_parse_failure_observed"):
        eids, cids = _claim_refs(claims["python_parse_failure_observed"])
        add(category="reliability_candidate", objective_code="repair_observed_python_parse_failures", evidence_ids=eids, claim_ids=cids,
            acceptance_criteria=["python_parse_failure_count_zero", "focused_parse_verification_passes", "fresh_assessment_confirms_repair"],
            risks=["source_change_medium_risk"], uncertainty="low", uncertainty_reasons=["failure_directly_observed"], effort="medium", effort_reason="scope_locations_not_retained_by_minimized_inspection")

    if int(assessment.get("test_file_count") or 0) == 0:
        rows = claims.get("test_surface_observed", []); eids, cids = _claim_refs(rows)
        add(category="test_coverage_candidate", objective_code="review_absent_test_surface", evidence_ids=eids, claim_ids=cids,
            acceptance_criteria=["testing_need_explicitly_decided", "tests_added_or_no_test_rationale_recorded"],
            risks=["test_strategy_scope_medium_risk"], uncertainty="high", uncertainty_reasons=["absence_does_not_prove_deficiency"], effort="medium", effort_reason="test_strategy_requires_project_context")
    elif claims.get("executed_test_outcome_unknown"):
        eids, cids = _claim_refs(claims["executed_test_outcome_unknown"])
        add(category="evidence_acquisition", objective_code="acquire_current_test_outcome_evidence", evidence_ids=eids, claim_ids=cids,
            acceptance_criteria=["bounded_test_outcome_evidence_available_or_blocker_recorded"], risks=[], uncertainty="medium", uncertainty_reasons=["tests_exist_but_outcome_unknown"], effort="small", effort_reason="evidence_acquisition_only")

    if int(assessment.get("documentation_file_count") or 0) == 0:
        rows = claims.get("documentation_surface_observed", []); eids, cids = _claim_refs(rows)
        add(category="documentation_candidate", objective_code="review_absent_documentation_surface", evidence_ids=eids, claim_ids=cids,
            acceptance_criteria=["documentation_need_explicitly_decided", "documentation_added_or_no_documentation_rationale_recorded"], risks=[], uncertainty="high", uncertainty_reasons=["absence_does_not_prove_deficiency"], effort="small", effort_reason="bounded_documentation_review")

    if int(assessment.get("configuration_file_count") or 0) == 0:
        add(category="configuration_candidate", objective_code="review_absent_configuration_surface", evidence_ids=[], claim_ids=[],
            acceptance_criteria=["configuration_need_explicitly_decided", "configuration_added_or_no_configuration_rationale_recorded"], risks=[], uncertainty="high", uncertainty_reasons=["project_may_not_require_configuration"], effort="small", effort_reason="bounded_configuration_review")

    if int(assessment.get("maintenance_marker_count") or 0) or int(assessment.get("limitation_marker_count") or 0):
        rows = claims.get("maintenance_or_limitation_signals_observed", []) + claims.get("known_limitations_observed", [])
        eids, cids = _claim_refs(rows)
        add(category="maintenance_investigation", objective_code="triage_observed_maintenance_and_limitation_signals", evidence_ids=eids, claim_ids=cids,
            acceptance_criteria=["signals_classified_as_actionable_deferred_or_not_defect", "actionable_findings_receive_specific_evidence"],
            risks=[], uncertainty="high", uncertainty_reasons=["marker_presence_is_not_defect_proof", "content_minimized_inspection_omits_raw_text"], effort="medium", effort_reason="requires_bounded_followup_inspection")

    # Explicit external evidence can support actionable candidates without exposing payloads.
    for ev in sorted(evidence.values(), key=lambda row: str(row.get("evidence_id") or "")):
        kind, status, code = str(ev.get("kind") or ""), str(ev.get("status") or ""), str(ev.get("claim_code") or "")
        eid = str(ev.get("evidence_id") or "")
        dep = [conflict_items[code]] if code in conflict_items else []
        if kind == "tests" and status in {"failing", "blocked"}:
            add(category="reliability_candidate", objective_code=f"investigate_test_signal:{code or 'bounded_test_signal'}", evidence_ids=[eid], claim_ids=[], dependency_ids=dep,
                acceptance_criteria=["failing_or_blocked_test_signal_explained", "focused_verification_passes_or_genuine_blocker_recorded"], risks=["repair_may_affect_behavior_medium_risk"],
                uncertainty="high" if dep else "medium", uncertainty_reasons=["external_test_signal_requires_diagnosis"], effort="medium", effort_reason="failure_scope_not_available_in_minimized_evidence")
        if kind == "runtime_health" and status in {"degraded", "failed", "blocked"}:
            add(category="reliability_candidate", objective_code=f"investigate_runtime_health_signal:{code or 'runtime_health'}", evidence_ids=[eid], claim_ids=[], dependency_ids=dep,
                acceptance_criteria=["runtime_health_signal_explained", "health_restored_or_genuine_blocker_recorded"], risks=["runtime_behavior_medium_risk"], uncertainty="high" if dep else "medium",
                uncertainty_reasons=["runtime_signal_requires_diagnosis"], effort="medium", effort_reason="runtime_scope_not_available_in_minimized_evidence")
        if kind == "known_limitation" and status in {"present", "degraded", "failed", "blocked"}:
            add(category="known_limitation_candidate", objective_code=f"review_known_limitation:{code or 'known_limitation'}", evidence_ids=[eid], claim_ids=[], dependency_ids=dep,
                acceptance_criteria=["limitation_disposition_recorded", "if_actionable_acceptance_criteria_refined_before_implementation"], risks=[], uncertainty="medium",
                uncertainty_reasons=["known_limitation_may_be_deliberate_or_environment_bound"], effort="unknown", effort_reason="scope_not_present_in_minimized_evidence")

    items = sorted(items, key=lambda row: (row["category"], row["objective_code"], row["work_item_id"]))
    truncated = len(items) > max_items
    items = items[:max_items]
    valid_ids = {row["work_item_id"] for row in items}
    for row in items:
        row["dependency_item_ids"] = [dep for dep in row["dependency_item_ids"] if dep in valid_ids]
        row["work_item_digest"] = _digest({k: v for k, v in row.items() if k != "work_item_digest"})
    backlog = {
        "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "status": "development_backlog_ready", "assessment_digest": str(assessment.get("assessment_digest") or ""),
        "source_manifest_digest": str(assessment.get("source_manifest_digest") or ""),
        "project_type": str(assessment.get("project_type") or ""), "adapter_id": str(assessment.get("adapter_id") or ""),
        "items": items, "item_count": len(items), "max_items": max_items, "truncated": truncated,
        "ordering_semantics": "deterministic_non_priority", "priority_selected": False, "schedule_created": False,
        "development_proposal_created": False, "execution_started": False, "project_modified": False,
        "raw_source_content_stored": False, "raw_evidence_content_stored": False, "private_runtime_discovery_performed": False,
        "content_minimized": True, "read_only": True, **BACKLOG_DENIED_AUTHORITY,
    }
    backlog["backlog_digest"] = _digest(backlog)
    return backlog


def validate_development_backlog(backlog: Mapping[str, Any]) -> dict[str, Any]:
    supplied = str(backlog.get("backlog_digest") or "")
    digest_ok = bool(supplied and supplied == _digest({k: v for k, v in backlog.items() if k != "backlog_digest"}))
    items = list(backlog.get("items") or [])
    ids = [str(row.get("work_item_id") or "") for row in items]
    unique = len(ids) == len(set(ids)) and all(ids)
    bounded = len(items) <= MAX_BACKLOG_ITEMS
    fields = all(
        row.get("category") in BACKLOG_CATEGORIES
        and (row.get("estimated_effort") or {}).get("band") in EFFORT_BANDS
        and (row.get("uncertainty") or {}).get("level") in UNCERTAINTY_LEVELS
        and row.get("risk_band") in RISK_BANDS
        and isinstance(row.get("acceptance_criteria"), list) and bool(row.get("acceptance_criteria"))
        and row.get("priority") is None and row.get("rank") is None
        for row in items
    )
    deps = all(dep in set(ids) and dep != row.get("work_item_id") for row in items for dep in row.get("dependency_item_ids") or [])
    return {"ok": digest_ok and unique and bounded and fields and deps, "status": "development_backlog_valid" if digest_ok and unique and bounded and fields and deps else "development_backlog_invalid",
            "digest_valid": digest_ok, "unique_items": unique, "bounded": bounded, "item_contracts_valid": fields, "dependencies_bound": deps,
            "backlog_digest": supplied, "read_only": True, **BACKLOG_DENIED_AUTHORITY}


def public_development_backlog(backlog: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(backlog.get("ok")), "status": str(backlog.get("status") or ""), "project_type": str(backlog.get("project_type") or ""),
        "item_count": int(backlog.get("item_count") or 0), "category_counts": {category: sum(1 for row in backlog.get("items") or [] if row.get("category") == category) for category in sorted(BACKLOG_CATEGORIES)},
        "backlog_digest": str(backlog.get("backlog_digest") or ""), "source_manifest_digest": str(backlog.get("source_manifest_digest") or ""),
        "priority_selected": False, "schedule_created": False, "development_proposal_created": False,
        "raw_evidence_content_exposed": False, "raw_paths_exposed": False, "content_minimized": True, "read_only": True, **BACKLOG_DENIED_AUTHORITY,
    }


__all__ = ["SCHEMA_VERSION", "CONTRACT_VERSION", "MAX_BACKLOG_ITEMS", "BACKLOG_CATEGORIES", "BACKLOG_DENIED_AUTHORITY", "build_backlog_from_assessment", "validate_development_backlog", "public_development_backlog"]
