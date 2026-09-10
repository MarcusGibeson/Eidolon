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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2730-9-4-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import BoundedResearchSessionStore
from bounded_research_reasoning import (
    RESEARCH_EVIDENCE_DIMENSIONS,
    build_source_strategy,
    decompose_research_objective,
    plan_adaptive_follow_up,
    plan_public_search_queries,
    validate_research_synthesis,
)
from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


objective = "Research Brand Deal Tracking for Content Creators demand."
budget = {
    "max_queries": 3,
    "max_candidates": 5,
    "max_observed_pages": 3,
    "max_total_bytes": 16_384,
    "max_elapsed_seconds": 60,
    "max_source_failures": 3,
}
decomp = decompose_research_objective(objective, budget=budget)
require(decomp["ok"] and decomp["objective_shape"] == "single_candidate_dimension", "single_dimension_objective_is_classified")
strategy = build_source_strategy(decomp)
query_plan = plan_public_search_queries(objective, decomp, strategy, max_queries=3)
query = query_plan["queries"][0]["query"]
lower_query = query.casefold()
for token in ("brand", "deal", "content", "creators", "problem", "evidence"):
    require(token in lower_query, f"narrow_demand_query_keeps_domain_anchor_{token}")
require("dictionary" not in lower_query and "definition" not in lower_query, "narrow_demand_query_does_not_seek_definition_pages")

comparison = {"claims": [{"claim_code": "rq1", "state": "incomplete", "incomplete_citations": ["web-a"], "all_independent_citations": ["web-a"]}]}
follow = plan_adaptive_follow_up(
    decomp,
    strategy,
    comparison,
    remaining_query_budget=1,
    remaining_page_budget=1,
    remaining_failure_budget=1,
    existing_query_digests=[query_plan["queries"][0]["query_digest"]],
    max_followups=1,
)
require(follow["ok"] and follow["query_count"] == 1, "incomplete_evidence_triggers_one_bounded_follow_up")
require(follow["queries"][0]["follow_up_reason"] == "insufficient_or_stale_evidence", "incomplete_follow_up_records_material_reason")
require(all(token in follow["queries"][0]["query"].split() for token in ("brand", "deal", "content", "creators", "survey")), "incomplete_follow_up_keeps_original_subject_and_measurement_intent")
require(follow["network_contacted"] is False and follow["authority_expanded"] is False, "adaptive_follow_up_remains_planning_only")


class NarrowDemandAdapter:
    def __init__(self) -> None:
        self.search_queries: list[str] = []
        self.synthesize_calls = 0
        self.observe_calls = 0

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "v2730.9.4-narrow-demand-fixture",
            "read_only": True,
            "allowed_methods": ["GET", "HEAD"],
            "search_supported": True,
            "private_network_allowed": False,
            "redirect_revalidation_required": True,
            "credentials_allowed": False,
            "cookies_allowed": False,
            "uploads_allowed": False,
            "side_effects_allowed": False,
            "max_bytes_enforced": True,
            "timeout_enforced": True,
        }

    def search(self, query: str, *, limit: int, timeout_seconds: float) -> list[dict[str, object]]:
        self.search_queries.append(query)
        if len(self.search_queries) == 1:
            return [
                {"url": "https://creator.example/problem/brand-deal-tracking", "source_kind": "community_experience", "fetched_at": "2026-09-06T00:00:00+00:00"}
            ][:limit]
        return [
            {"url": "https://research.example/creator-sponsorship-workflow", "source_kind": "reputable_secondary", "fetched_at": "2026-09-06T00:00:00+00:00"}
        ][:limit]

    def observe(self, candidate: dict[str, object], *, plan: dict[str, object], max_bytes: int, timeout_seconds: float) -> dict[str, object]:
        self.observe_calls += 1
        supports = self.observe_calls > 1
        cid = f"web-fixture-{self.observe_calls}"
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": digest({"operation": cid}),
            "terminal_result_digest": digest({"terminal": cid}),
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"),
            "stance": "supports" if supports else "unknown",
            "evidence_digest": digest({"evidence": cid}),
            "citation_id": cid,
            "source_kind": candidate.get("source_kind", "unknown"),
            "quality_score": 0.75 if supports else 0.45,
            "freshness_known": True,
            "fresh_enough": True,
            "relevance_score": 0.85,
            "observed_bytes": min(512, max_bytes),
        }
        row["receipt_digest"] = digest(row)
        return row

    def synthesize(self, **kwargs: object) -> dict[str, object]:
        self.synthesize_calls += 1
        return {"ok": False, "status": "unexpected_synthesis_call"}


store = BoundedResearchSessionStore(RUNTIME)
adapter = NarrowDemandAdapter()
created = store.create_session("create-narrow-demand", objective=objective, budget=budget)
require(created["ok"], "narrow_demand_session_created")
session = created["result"]
authorized = store.authorize_session(
    "authorize-narrow-demand",
    session_id=session["session_id"],
    session_digest=session["session_digest"],
    public_query_confirmed=True,
)
require(authorized["ok"], "narrow_demand_session_authorized")
run = store.execute_session(
    "execute-narrow-demand",
    session_id=session["session_id"],
    authorization_digest=authorized["result"]["authorization_digest"],
    adapter=adapter,
)
require(run["ok"], "narrow_demand_session_completes_with_deterministic_conclusion")
report = run["result"]["report"]
require(adapter.synthesize_calls == 1, "single_dimension_research_attempts_cited_synthesis")
require(len(adapter.search_queries) == 2, "single_dimension_incomplete_result_gets_follow_up_search")
require(all("brand" in q.casefold() and "demand" in q.casefold() for q in adapter.search_queries), "all_live_queries_keep_subject_and_dimension")
require(report["candidate_specific_coverage_required"] is False, "single_dimension_report_does_not_require_candidate_matrix")
require(not any(row.get("claim_code") == "candidate_matrix_candidate_evidence" for row in report["missing_evidence"]), "single_dimension_report_has_no_spurious_candidate_matrix_gap")
require(report["provider_contacted"] is False and report["provider_request_count"] == 0, "skipped_synthesis_does_not_claim_provider_contact")
require(report["raw_query_text_exposed"] is False and report["raw_page_content_persisted"] is False, "single_dimension_report_stays_content_minimized")


class NativeAdapterProbe(GovernedPublicWebResearchAdapter):
    def __init__(self) -> None:
        super().__init__(synthesizer=lambda prompt: "{}", resolver=lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))], search_min_interval_seconds=0)

    def _fetch(self, url: str, *, max_bytes: int, timeout_seconds: float) -> dict[str, object]:
        if "duckduckgo" in url:
            body = b'<html><body><a class="result__a" href="https://www.creatorsjet.com/brand-deal-demand">result</a></body></html>'
            return {
                "body": body,
                "content_type": "text/html",
                "final_url": url,
                "public_url": url,
                "redirect_count": 0,
                "observed_bytes": len(body),
                "content_digest": digest({"body": body.decode()}),
            }
        body = (
            "Creators report brand deal tracking demand, sponsorship workflow complaints, "
            "brand deal pipeline problems, invoice deadlines, and creator evidence."
        ).encode("utf-8")
        return {
            "body": body,
            "content_type": "text/html",
            "final_url": url,
            "public_url": url,
            "redirect_count": 0,
            "observed_bytes": len(body),
            "content_digest": digest({"body": body.decode()}),
        }


native_probe = NativeAdapterProbe()
native_results = native_probe.search(query, limit=1, timeout_seconds=1.0)
require(native_results and not native_results[0]["fetched_at"], "search_discovery_does_not_assert_page_freshness")
source_candidate = {
    "source_candidate_digest": "a" * 64,
    "public_url": native_results[0]["url"],
    "source_kind": "reputable_secondary",
    "quality_score": 0.82,
    "freshness_known": True,
    "fresh_enough": True,
    "_evidence_terms": query.split(),
}
native_observation = native_probe.observe(source_candidate, plan={"plan_digest": "b" * 64, "subquestions": [{"subquestion_id": "rq1"}]}, max_bytes=4096, timeout_seconds=1.0)
require(native_observation["stance"] == "unknown", "keyword_overlap_does_not_prove_claim_support")
require(native_probe._transient_documents[native_observation["citation_id"]]["excerpt"], "native_observation_keeps_only_transient_excerpt")

prompts = []
def findings_provider(prompt):
    prompts.append(prompt)
    return {"findings": [{"title": "Reported workflow", "summary": "The supplied page reports workflow complaints; independent demand remains uncertain.", "citation_ids": [native_observation["citation_id"]]}], "limitations": ["One source only."]}
native_probe.synthesizer = findings_provider
generated = native_probe.synthesize(decomposition=decomp, citations=[{**native_observation, "public_url": source_candidate["public_url"]}], retain_documents=True)
require(generated["ok"] and "findings" in generated["payload"], "native_narrow_synthesis_preserves_findings")
require('"findings"' in prompts[0] and "distinct, buildable product opportunities" not in prompts[0], "narrow_prompt_uses_findings_contract")
admitted = validate_research_synthesis(generated["payload"], citations=[{**native_observation, "public_url": source_candidate["public_url"]}])
require(admitted["ok"], "native_findings_pass_existing_citation_validator")
require("independent demand remains uncertain" in admitted["rendered_answer"], "narrow_render_preserves_cited_finding")
require("not independently verified" in admitted["rendered_answer"], "narrow_render_distinguishes_citation_validation_from_independent_support")
require("Evidence matrix:" not in admitted["rendered_answer"] and "No candidate clears" not in admitted["rendered_answer"], "narrow_render_has_no_comparison_scaffolding")

calls = []
def retry_failure(prompt):
    calls.append(prompt)
    if len(calls) == 1:
        return "invalid"
    raise RuntimeError("fixture provider failure")
native_probe.synthesizer = retry_failure
failed = native_probe.synthesize(decomposition=decomp, citations=[native_observation])
require(failed["provider_request_count"] == 2 and failed["provider_contacted"], "failed_second_provider_call_is_counted")


def candidate(name: str) -> dict[str, str]:
    return {
        "name": name,
        "customer": f"{name} customers",
        "problem": f"{name} problem",
        "product": f"{name} product",
        "zero_budget_rationale": "local-first implementation with public read-only research",
        "evidence_summary": f"Observed evidence supports evaluating {name}.",
    }


def candidate_digest(row: dict[str, str]) -> str:
    return digest({"title": row["name"], "customer": row["customer"], "problem": row["problem"], "product": row["product"]})


def citation(cid: str, cand: dict[str, str], dimension: str, url: str) -> dict[str, object]:
    return {
        "citation_id": cid,
        "public_url": url,
        "host": url.split("/")[2],
        "source_kind": "primary_data",
        "freshness": "fresh",
        "quality_score": 0.9,
        "relevance_score": 0.9,
        "source_digest": digest({"citation": cid, "url": url}),
        "candidate_digest": candidate_digest(cand),
        "evidence_dimension": dimension,
        "stance": "supports",
    }


product = candidate("Tiny creator deal tracker")
ids: list[str] = []
citations: list[dict[str, object]] = []
for index, dimension in enumerate(RESEARCH_EVIDENCE_DIMENSIONS):
    cid = f"t-{dimension[:2]}-{index}"
    ids.append(cid)
    citations.append(citation(cid, product, dimension, f"https://source-{index}.example/{dimension}"))
payload = {
    "opportunities": [
        {
            **product,
            "citation_ids": ids,
            "evidence_dimensions": {
                dimension: {"summary": f"{dimension} evidence", "citation_ids": [ids[index]]}
                for index, dimension in enumerate(RESEARCH_EVIDENCE_DIMENSIONS)
            },
        }
    ],
    "recommendation": {
        "opportunity_name": product["name"],
        "conclusion": "Best observed fit under the bounded evidence matrix.",
        "citation_ids": ids[:2],
    },
    "limitations": ["Public evidence remains bounded."],
}
validated = validate_research_synthesis(
    payload,
    citations=citations,
    requested_result_count=1,
    require_candidate_specific_coverage=True,
    candidate_research_matrix_complete=True,
)
rendered = validated["rendered_answer"]
first_candidate_line = next(line for line in rendered.splitlines() if line.startswith("1. "))
require("Evidence matrix:" not in first_candidate_line, "candidate_summary_line_does_not_duplicate_matrix")
require(rendered.count("Evidence matrix:") == 1, "candidate_matrix_renders_once_per_candidate")

print(json.dumps({"suite": "v2730.9.4-research-trial-repair", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
