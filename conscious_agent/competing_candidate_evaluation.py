from __future__ import annotations
"""v1294.3-v1294.5 compare independently verified isolated candidates."""
from typing import Any, Iterable, Mapping
from competing_candidate_evaluation_foundations import ARCHITECTURE_LINEAGE,DENIED_AUTHORITY,digest,normalize_candidate_evidence

CONTRACT_VERSION = "v1294.5"
BLOCKING_QUALITY = {"needs_revision", "insufficient_evidence"}


def _score(row: Mapping[str, Any]) -> float:
    return round(.42*int(row["quality_score"]) + .18*int(row["reversibility"]) - .16*int(row["risk"]) - .10*int(row["cost"]) - .14*int(row["residual_uncertainty"]), 2)


def evaluate_competing_candidates(candidates: Iterable[Mapping[str, Any]], *, comparison_context: Mapping[str, Any], ambiguity_margin: float = 3.0) -> dict[str, Any]:
    rows = [normalize_candidate_evidence(r) for r in candidates][:6]
    required = bool(comparison_context.get("comparison_required"))
    violations=[]
    if not required:
        return _result("comparison_not_warranted", "single_candidate_path_should_remain_available", rows, [], None, violations)
    if len(rows) < 2:
        return _result("defer_insufficient_candidates", "comparison_requires_at_least_two_candidates", rows, [], None, ["fewer_than_two_candidates"])
    campaigns={r["campaign_id"] for r in rows};baselines={r["baseline_digest"] for r in rows};workspaces=[r["workspace_digest"] for r in rows];approaches=[r["approach_digest"] for r in rows];runs=[r["verification_run_digest"] for r in rows]
    if len(campaigns)!=1: violations.append("campaign_identity_mismatch")
    if len(baselines)!=1: violations.append("baseline_identity_mismatch")
    if len(workspaces)!=len(set(workspaces)): violations.append("candidate_workspace_not_isolated")
    if len(approaches)!=len(set(approaches)): violations.append("duplicate_approach")
    if len(runs)!=len(set(runs)): violations.append("verification_not_independent")
    assessed=[]
    for row in rows:
        blocks=[]
        if not row["focused_verification_passed"]: blocks.append("focused_verification_failed")
        if not row["regression_verification_passed"]: blocks.append("regression_verification_failed")
        if not row["scope_conforming"]: blocks.append("scope_nonconforming")
        if not row["evidence_fresh"]: blocks.append("stale_evidence")
        if row["private_evidence"]: blocks.append("private_evidence_not_comparable")
        if row["quality_disposition"] in BLOCKING_QUALITY: blocks.append("product_quality_not_ready")
        assessed.append(row | {"score":_score(row),"blocked":bool(blocks),"block_reasons":blocks})
    if violations:
        return _result("reject_comparison_integrity_failure", "candidate_independence_or_lineage_invalid", assessed, [], None, violations)
    viable=sorted((r for r in assessed if not r["blocked"]),key=lambda r:(-r["score"],r["candidate_id"]))
    if not viable:
        return _result("reject_all_candidates", "no_candidate_has_complete_defensible_evidence", assessed, [], None, [])
    selected=viable[0]
    if len(viable)>1 and abs(viable[0]["score"]-viable[1]["score"])<float(ambiguity_margin) and max(viable[0]["residual_uncertainty"],viable[1]["residual_uncertainty"])>=45:
        return _result("defer_ambiguous_candidates", "top_candidates_remain_too_close_under_uncertainty", assessed, viable, None, [])
    comparisons=[]
    for other in assessed:
        if other["candidate_id"]==selected["candidate_id"]: continue
        reasons=[]
        if other["blocked"]: reasons.append("alternative_failed_required_evidence")
        if selected["score"]>other["score"]: reasons.append("higher_evidence_weighted_score")
        if selected["risk"]<other["risk"]: reasons.append("lower_risk")
        if selected["residual_uncertainty"]<other["residual_uncertainty"]: reasons.append("lower_residual_uncertainty")
        if selected["quality_score"]>other["quality_score"]: reasons.append("higher_product_quality")
        comparisons.append({"alternative_candidate_id":other["candidate_id"],"reason_codes":reasons or ["deterministic_tie_break"],"content_free":True})
    return _result("recommend_candidate_for_operator_review", "best_defensible_verified_candidate", assessed, viable, selected, [], comparisons)


def _result(disposition: str, reason: str, assessed: list[Mapping[str,Any]], viable: list[Mapping[str,Any]], selected: Mapping[str,Any] | None, violations: list[str], comparisons: list[Mapping[str,Any]] | None=None) -> dict[str,Any]:
    out={
        "contract_version":CONTRACT_VERSION,
        "disposition":disposition,
        "reason":reason,
        "candidate_count":len(assessed),
        "viable_candidate_count":len(viable),
        "recommended_candidate_id":str(selected.get("candidate_id") or "") if selected else "",
        "recommended_candidate_identity_digest":str(selected.get("candidate_identity_digest") or "") if selected else "",
        "assessments":[{"candidate_id":r.get("candidate_id",""),"score":r.get("score",_score(r) if "quality_score" in r else 0),"blocked":bool(r.get("blocked",False)),"block_reasons":list(r.get("block_reasons") or []),"focused_verification_passed":bool(r.get("focused_verification_passed")),"regression_verification_passed":bool(r.get("regression_verification_passed")),"quality_disposition":r.get("quality_disposition",""),"risk":r.get("risk",0),"cost":r.get("cost",0),"reversibility":r.get("reversibility",0),"residual_uncertainty":r.get("residual_uncertainty",0),"content_free":True} for r in assessed],
        "comparisons":list(comparisons or []),
        "integrity_violations":list(violations),
        "selection_is_application":False,
        "selection_is_update":False,
        "operator_review_required":bool(selected),
        "architecture_lineage":dict(ARCHITECTURE_LINEAGE),
        "content_free":True,
        "read_only":True,
        **DENIED_AUTHORITY,
    }
    out["evaluation_digest"]=digest(out)
    return out
