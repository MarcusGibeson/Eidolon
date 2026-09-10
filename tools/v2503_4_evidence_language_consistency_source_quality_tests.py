from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2503-4-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_reasoning import RESEARCH_EVIDENCE_DIMENSIONS, validate_research_synthesis
from research_source_independence import canonicalize_public_url, source_evidence_role, source_identity

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate(name: str) -> dict[str, str]:
    return {
        "name": name,
        "customer": f"{name} customers",
        "problem": f"{name} problem",
        "product": f"{name} product",
        "zero_budget_rationale": "The model claims a free implementation is easy.",
        "evidence_summary": "Strong demand and a feasible free tier make this the obvious winner.",
    }


def candidate_digest(row: dict[str, str]) -> str:
    return digest({"title": row["name"], "customer": row["customer"], "problem": row["problem"], "product": row["product"]})


def citation(cid: str, cand: dict[str, str], dimension: str, url: str, *, source_kind: str, quality: float = 0.95) -> dict[str, object]:
    return {
        "citation_id": cid,
        "public_url": url,
        "source_kind": source_kind,
        "freshness": "fresh",
        "quality_score": quality,
        "relevance_score": 0.95,
        "source_digest": digest({"citation": cid, "url": url}),
        "candidate_digest": candidate_digest(cand),
        "evidence_dimension": dimension,
        "stance": "supports",
    }


def payload(rows: list[dict[str, str]], ids: dict[str, dict[str, list[str]]], recommendation: str) -> dict[str, object]:
    opportunities = []
    for row in rows:
        dimensions = {
            dimension: {
                "summary": f"Model generated {dimension} claim for {row['name']}",
                "citation_ids": ids[row["name"]].get(dimension, []),
            }
            for dimension in RESEARCH_EVIDENCE_DIMENSIONS
        }
        all_ids = [cid for dimension in RESEARCH_EVIDENCE_DIMENSIONS for cid in ids[row["name"]].get(dimension, [])]
        opportunities.append(dict(row, citation_ids=all_ids, evidence_dimensions=dimensions))
    recommendation_ids = [
        cid
        for dimension in RESEARCH_EVIDENCE_DIMENSIONS
        for cid in ids[recommendation].get(dimension, [])
    ]
    return {
        "opportunities": opportunities,
        "recommendation": {
            "opportunity_name": recommendation,
            "conclusion": "This is unquestionably most promising because demand and the free tier are strong.",
            "citation_ids": recommendation_ids,
        },
    }


# Malformed public URLs are rejected before identity or synthesis admission.
malformed = (
    "https://statuspage.example/docs/incidents & maintenance/postmortem",
    "https://example.test/path[broken]",
    "https://example.test/path\\broken",
    "https://example.test/%0d%0aheader",
)
require(all(not canonicalize_public_url(value) for value in malformed), "malformed_public_urls_are_rejected")
require(source_evidence_role({"public_url": malformed[0]})["valid_public_url"] is False, "malformed_url_has_inadmissible_evidence_role")

# Source roles constrain which conclusion dimensions a citation can support.
repo_role = source_evidence_role({"public_url": "https://github.com/example/project", "source_kind": "primary_data"})
require(repo_role["evidence_role"] == "implementation_precedent", "github_repository_is_implementation_precedent")
require(repo_role["supportable_dimensions"] == ["implementation_dependencies"], "github_repository_cannot_prove_demand_or_free_tier")
pricing_role = source_evidence_role({"public_url": "https://vendor.example/pricing/", "source_kind": "primary_official"})
require("free_tier_feasibility" in pricing_role["supportable_dimensions"], "pricing_page_can_support_free_tier_feasibility")
promo_role = source_evidence_role({"public_url": "https://market.example/blog/best-saas-ideas-2026", "source_kind": "specialist_secondary"})
require(promo_role["evidence_role"] == "promotional_summary" and promo_role["quality_cap"] < 0.5, "promotional_listicle_is_capped_below_evidence_floor")
require(source_identity({"public_url": "https://github.com/example/project", "source_kind": "primary_data"})["evidence_role"] == "implementation_precedent", "source_identity_exposes_content_free_role")

# An adversarially enthusiastic synthesis cannot outrun the evidence matrix.
lead = candidate("Newsletter Growth Dashboard")
lead_ids = {
    "demand": ["lead-demand"],
    "competition": ["lead-competition"],
    "implementation_dependencies": ["lead-implementation"],
    "free_tier_feasibility": ["lead-free"],
}
lead_citations = [
    citation("lead-demand", lead, "demand", "https://market.example/blog/best-newsletter-tools", source_kind="specialist_secondary"),
    citation("lead-competition", lead, "competition", "https://newsletter.example/product", source_kind="primary_official"),
    citation("lead-implementation", lead, "implementation_dependencies", "https://github.com/example/newsletter-dashboard", source_kind="primary_data"),
    citation("lead-free", lead, "free_tier_feasibility", "https://newsletter.example/pricing/", source_kind="primary_official"),
    citation("bad-url", lead, "demand", malformed[0], source_kind="primary_data"),
]
lead_result = validate_research_synthesis(
    payload([lead], {lead["name"]: lead_ids}, lead["name"]),
    citations=lead_citations,
    requested_result_count=1,
    require_candidate_specific_coverage=True,
    candidate_research_matrix_complete=True,
)
require(lead_result["ok"], "bounded_report_remains_available_with_explicit_gaps")
lead_finding = lead_result["reasonable_inferences"][0]
lead_matrix = lead_finding["evidence_dimensions"]
require(lead_matrix["demand"]["matrix_state"] == "researched_with_no_credible_evidence", "promotional_demand_claim_does_not_become_supported")
require(lead_matrix["demand"]["role_mismatch_citation_count"] == 1, "role_mismatch_is_counted_for_review")
require(lead_matrix["implementation_dependencies"]["matrix_state"] == "supported", "github_repository_supports_only_implementation_cell")
require(lead_matrix["free_tier_feasibility"]["matrix_state"] == "supported", "pricing_page_supports_free_tier_cell")
require(lead_finding["evidence_strength"] == "weak", "candidate_strength_is_derived_from_matrix_coverage")
require(lead_result["recommendation"]["confidence_threshold_met"] is False, "matrix_gap_blocks_unqualified_winner")
require("Best current lead for further research:" in lead_result["rendered_answer"], "below_threshold_report_uses_lead_language")
require("Most promising:" not in lead_result["rendered_answer"], "below_threshold_report_never_uses_winner_label")
require("unquestionably most promising" not in lead_result["rendered_answer"].casefold(), "model_recommendation_hype_is_not_rendered")
require("strong demand" not in lead_result["rendered_answer"].casefold(), "model_evidence_hype_is_not_rendered")
require("Zero-budget hypothesis (not independently verified)" not in lead_result["rendered_answer"], "supported_free_tier_uses_verified_zero_budget_label")
require(lead_result["invalid_public_url_citation_count"] == 1, "invalid_public_url_count_is_reported")
require(all(row["public_url"] and " " not in row["public_url"] for row in lead_result["citations"]), "malformed_urls_never_reach_public_citations")
require(lead_result["model_generated_evidence_language_rendered"] is False, "model_prose_is_not_treated_as_evidence_language")

# Deterministic comparison corrects a model-selected weaker candidate.
weak = candidate("Weak Operations Dashboard")
weak_ids: dict[str, list[str]] = {}
weak_citations: list[dict[str, object]] = []
for index, dimension in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    cid = f"weak-{index}"
    weak_ids[dimension] = [cid]
    weak_citations.append(citation(cid, weak, dimension, f"https://weak-{index}.gov/{dimension}", source_kind="primary_data", quality=0.2))
qualified = candidate("Qualified Operations Dashboard")
qualified_ids: dict[str, list[str]] = {}
qualified_citations: list[dict[str, object]] = []
for index, dimension in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    cid = f"qualified-{index}"
    qualified_ids[dimension] = [cid]
    qualified_citations.append(citation(cid, qualified, dimension, f"https://agency-{index}.gov/{dimension}", source_kind="primary_data"))
comparison = validate_research_synthesis(
    payload(
        [weak, qualified],
        {weak["name"]: weak_ids, qualified["name"]: qualified_ids},
        weak["name"],
    ),
    citations=weak_citations + qualified_citations,
    requested_result_count=2,
    require_candidate_specific_coverage=True,
    candidate_research_matrix_complete=True,
)
require(comparison["recommendation_selection_deterministically_corrected"] is True, "weaker_model_selection_is_deterministically_corrected")
require(comparison["recommendation"]["title"] == qualified["name"], "deterministic_comparison_selects_stronger_matrix")
require(comparison["recommendation"]["confidence_label"] == "moderate-confidence", "qualified_candidate_clears_moderate_threshold")
require(comparison["strongest_opportunity_admitted"] is True, "qualified_matrix_admits_strongest_opportunity_claim")
require("Most promising: Qualified Operations Dashboard" in comparison["rendered_answer"], "winner_label_is_reserved_for_threshold_passing_candidate")
require(comparison["recommendation"]["model_generated_conclusion_rendered"] is False, "winner_explanation_is_deterministically_calibrated")

# The focused verifier is source-only and never grants operational authority.
for observed in (lead_result, comparison):
    require(observed.get("network_contacted") is False and observed.get("provider_contacted") is False, "focused_reasoning_performs_no_network_or_provider_work_" + str(len(CHECKS)))
    require(observed.get("authority_expanded") is False and observed.get("installation_authorized") is False, "focused_reasoning_grants_no_authority_" + str(len(CHECKS)))
require(RUNTIME.is_dir() and not str(RUNTIME).startswith(str(ROOT)), "test_runtime_remains_external_to_source")
require(not (ROOT / "data" / "projects.json").exists(), "source_tree_contains_no_packaged_runtime_projects")

print(json.dumps({
    "suite": "v2503.4-evidence-language-consistency-source-quality",
    "ok": True,
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "network_request_count": 0,
    "provider_request_count": 0,
    "external_action_count": 0,
    "authority_expanded": False,
}, sort_keys=True))
