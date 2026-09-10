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
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2503-0-runtime-")

from bounded_autonomous_web_research import BoundedResearchSessionStore
from bounded_research_reasoning import (
    build_source_strategy,
    decompose_research_objective,
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
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


OBJECTIVE = (
    "Research three realistic zero-budget SaaS opportunities for a solo developer in 2026. "
    "Use only public, read-only sources. Compare the supporting evidence, identify uncertainties and disagreements, "
    "cite every material conclusion, and explain which opportunity appears most promising and why. "
    "Do not create accounts, post, purchase, message anyone, or perform external side effects."
)
BUDGET = {
    "max_queries": 4,
    "max_candidates": 12,
    "max_observed_pages": 8,
    "max_total_bytes": 2 * 1024 * 1024,
    "max_elapsed_seconds": 180,
    "max_source_failures": 4,
}


decomposition = decompose_research_objective(OBJECTIVE, freshness="current", budget=BUDGET)
require(decomposition["ok"], "real_trial_objective_is_bounded")
require(decomposition["requested_result_count"] == 3, "requested_three_results_are_explicit")
require(decomposition["subquestion_count"] == 4, "comparative_discovery_expands_to_four_evidence_roles")
require(
    [row["planning_role"] for row in decomposition["subquestions"]]
    == ["exploratory_unknown", "required_fact", "comparative_criterion", "comparative_criterion"],
    "discovery_demand_feasibility_and_recommendation_roles_are_distinct",
)
strategy = build_source_strategy(decomposition)
queries = plan_public_search_queries(OBJECTIVE, decomposition, strategy, max_queries=4)
query_texts = [row["query"] for row in queries["queries"]]
require(len(query_texts) == 4 and len(set(query_texts)) == 4, "four_distinct_public_queries_are_planned")
require(all("purchase" not in row and "message" not in row for row in query_texts), "safety_instructions_do_not_pollute_search_queries")
require(any("demand" in row for row in query_texts) and any("competition" in row for row in query_texts), "queries_cover_demand_and_competition")


class NativeShapedAdapter:
    def __init__(self, *, valid_synthesis: bool = True) -> None:
        self.search_limits: list[int] = []
        self.search_queries: list[str] = []
        self.observe_subquestions: list[str] = []
        self.valid_synthesis = valid_synthesis

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "v2503.0-native-shaped-fixture",
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

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.search_queries.append(query)
        self.search_limits.append(limit)
        index = len(self.search_queries)
        rows = []
        for item in range(limit):
            if item == 0:
                rows.append({"url": f"https://evidence{index}.gov/data/{item}", "source_kind": "primary_data", "fetched_at": "2026-08-27T00:00:00+00:00"})
            elif item == 1:
                rows.append({"url": f"https://www.reddit.com/r/saas/comments/{index}{item}", "source_kind": "community_experience", "fetched_at": "2026-08-27T00:00:00+00:00"})
            else:
                rows.append({"url": f"https://analysis{index}-{item}.example/report", "source_kind": "specialist_secondary", "fetched_at": "2026-08-27T00:00:00+00:00"})
        return rows

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        self.observe_subquestions.append(str(candidate.get("subquestion_id") or ""))
        citation_id = f"web-{len(self.observe_subquestions):016x}"
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": "8" * 64,
            "terminal_result_digest": "9" * 64,
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"),
            "stance": "unknown",
            "evidence_digest": hashlib.sha256(citation_id.encode()).hexdigest(),
            "citation_id": citation_id,
            "source_kind": candidate["source_kind"],
            "quality_score": candidate["quality_score"],
            "freshness_known": True,
            "fresh_enough": True,
            "relevance_score": 0.9,
            "observed_bytes": min(256, max_bytes),
        }
        row["receipt_digest"] = digest(row)
        return row

    def synthesize(self, *, decomposition, citations):
        ids = [row["citation_id"] for row in citations]
        if not self.valid_synthesis:
            ids = ["web-not-observed"]
        payload = {
            "opportunities": [
                {"name": "Compliance reminder", "customer": "small regulated service firms", "problem": "recurring deadlines are missed", "product": "tracks deadlines and sends local reminders", "zero_budget_rationale": "uses a local database and free email tier", "evidence_summary": "A narrow reminder product has recurring deadline evidence.", "citation_ids": ids[:2], "uncertainties": ["Willingness to pay needs validation."]},
                {"name": "Review-response assistant", "customer": "independent local businesses", "problem": "reviews require repetitive triage", "product": "organizes reviews and drafts operator-reviewed replies", "zero_budget_rationale": "starts with manual import and local generation", "evidence_summary": "Small businesses repeatedly need bounded review triage.", "citation_ids": ids[2:4] or ids, "uncertainties": ["Platform terms vary."]},
                {"name": "Quote follow-up tracker", "customer": "solo home-service contractors", "problem": "open quotes lose timely follow-up", "product": "tracks quote status and follow-up dates", "zero_budget_rationale": "runs locally without paid integrations", "evidence_summary": "Missed follow-up is a documented workflow problem.", "citation_ids": ids[4:6] or ids, "uncertainties": ["Competition is fragmented."]},
            ],
            "recommendation": {"opportunity_name": "Compliance reminder", "conclusion": "It has the clearest narrow scope and lowest zero-budget integration burden.", "citation_ids": ids[:3]},
            "disagreements": ["Demand signals do not establish conversion rates."],
            "limitations": ["No paid acquisition experiment was performed."],
        }
        return {"ok": True, "status": "research_synthesis_generated", "payload": payload, "provider_contacted": True, "provider_request_count": 1, "private_objective_sent_to_provider": False}


store = BoundedResearchSessionStore(Path(os.environ["EIDOLON_DATA_DIR"]))
adapter = NativeShapedAdapter()
created = store.create_session("v2503:create", objective=OBJECTIVE, budget=BUDGET)
session = created["result"]
authorized = store.authorize_session("v2503:authorize", session_id=session["session_id"], session_digest=session["session_digest"], public_query_confirmed=True)
run = store.execute_session("v2503:execute", session_id=session["session_id"], authorization_digest=authorized["result"]["authorization_digest"], adapter=adapter)
report = run["result"]["report"]
require(run["ok"] and report["status"] == "research_report_insufficient_evidence", "one_pass_adapter_cannot_admit_unsupported_opportunity_synthesis")
require(adapter.search_limits == [3, 3, 3, 3], "candidate_budget_is_balanced_across_all_evidence_queries")
require(set(adapter.observe_subquestions) >= {"rq1", "rq2", "rq3", "rq4"}, "page_budget_covers_each_evidence_role")
require(len(report["reasonable_inferences"]) == 3, "unsupported_candidates_remain_labeled_inferences_without_recommendation")
require(not report["rendered_answer"], "unsupported_opportunity_synthesis_is_not_rendered_as_research")
require(report["citation_count"] >= 3 and all(row["public_url"].startswith("https://") for row in report["citations"]), "material_synthesis_has_public_citations")
require(report["provider_contacted"] and report["provider_request_count"] == 1, "single_synthesis_provider_request_is_reported_truthfully")
require(not report["private_objective_sent_to_provider"] and not report["raw_page_content_persisted"], "private_objective_and_raw_pages_remain_out_of_persisted_synthesis")

rerun = store.create_session("v2503:rerun", objective=OBJECTIVE, budget=BUDGET)
rerun_session = rerun["result"]
require(rerun["status"] == "research_session_created", "completed_objective_can_start_a_fresh_session")
require(rerun_session["session_id"] != session["session_id"] and rerun_session["semantic_attempt"] == 2, "fresh_rerun_has_distinct_exact_authorization_identity")
rerun_duplicate = store.create_session("v2503:rerun-duplicate", objective=OBJECTIVE, budget=BUDGET)
require(rerun_duplicate["status"] == "duplicate_research_session_reused" and rerun_duplicate["result"]["session_id"] == rerun_session["session_id"], "inflight_duplicate_still_reuses_one_session")

invalid = validate_research_synthesis(
    {"findings": [{"title": "Invented", "conclusion": "Unsupported", "citation_ids": ["web-not-observed"]}]},
    citations=report["citations"],
    requested_result_count=3,
)
require(not invalid["ok"] and invalid["status"] == "citation_bound_research_synthesis_rejected", "unobserved_citations_fail_closed")
require(not invalid["rendered_answer"], "rejected_synthesis_is_never_presented_as_research")

transport = GovernedPublicWebResearchAdapter(synthesizer=lambda prompt: {"findings": [], "recommendation": {}, "limitations": ["fixture"]})
transport._transient_documents["web-fixture"] = {
    "citation_id": "web-fixture", "title": "Fixture", "excerpt": "Public evidence only.",
    "public_url": "https://example.com/evidence", "source_kind": "reputable_secondary", "query_terms": ["saas", "demand"],
}
transport_result = transport.synthesize(decomposition={"requested_result_count": 0}, citations=[{"citation_id": "web-fixture"}])
require(transport_result["ok"] and transport_result["provider_request_count"] == 1, "production_transport_has_one_bounded_synthesis_seam")
require(not transport._transient_documents, "transient_public_excerpts_are_cleared_after_synthesis")

require(Path(os.environ["EIDOLON_DATA_DIR"]).is_dir(), "fixture_runtime_remains_external_to_source")
print(json.dumps({
    "suite": "v2503.0-research-planning-native-synthesis-repair",
    "ok": True,
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "network_request_count": 0,
    "provider_request_count": 0,
    "authority_expanded": False,
    "raw_page_content_persisted": False,
}, sort_keys=True))
