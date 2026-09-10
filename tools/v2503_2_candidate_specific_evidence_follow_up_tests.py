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
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2503-2-runtime-")

from bounded_autonomous_web_research import BoundedResearchSessionStore
from bounded_research_history import sanitize_report
from bounded_research_reasoning import plan_candidate_evidence_follow_up, validate_research_synthesis
from conversational_research_actions import _research_report_message, execute_conversational_research_action
from governed_public_web_research_adapter import CANDIDATE_DISCOVERY_MAX_TOKENS, FINAL_SYNTHESIS_MAX_TOKENS, GovernedPublicWebResearchAdapter
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


OBJECTIVE = (
    "Research three realistic zero-budget SaaS opportunities for a solo developer in 2026. "
    "Use only public, read-only sources. Compare the supporting evidence, identify uncertainties and disagreements, "
    "cite every material conclusion, and explain which opportunity appears most promising and why. "
    "Do not create accounts, post, purchase, message anyone, or perform external side effects."
)

OPPORTUNITIES = [
    {
        "name": "Compliance reminder",
        "customer": "small regulated service firms",
        "problem": "recurring deadlines are missed",
        "product": "tracks deadlines and sends local reminders",
        "zero_budget_rationale": "uses a local database and free email tier",
        "evidence_summary": "Public sources describe recurring compliance deadline work.",
        "uncertainties": ["Willingness to pay remains uncertain."],
    },
    {
        "name": "Review response assistant",
        "customer": "independent local businesses",
        "problem": "reviews require repetitive triage",
        "product": "organizes reviews and drafts operator-reviewed replies",
        "zero_budget_rationale": "starts with manual import and local generation",
        "evidence_summary": "Public sources describe repetitive review triage.",
        "uncertainties": ["Platform terms vary."],
    },
    {
        "name": "Quote follow-up tracker",
        "customer": "solo home-service contractors",
        "problem": "open quotes lose timely follow-up",
        "product": "tracks quote status and follow-up dates",
        "zero_budget_rationale": "runs locally without paid integrations",
        "evidence_summary": "Public sources describe missed quote follow-up.",
        "uncertainties": ["Competition remains uncertain."],
    },
]


def candidate_digest(row: dict[str, object]) -> str:
    return digest({
        "title": row["name"],
        "customer": row["customer"],
        "problem": row["problem"],
        "product": row["product"],
    })


class TwoPassAdapter:
    def __init__(self) -> None:
        self.search_queries: list[str] = []
        self.search_limits: list[int] = []
        self.follow_up_dimensions: list[str] = []
        self.discovery_calls = 0
        self.final_synthesis_calls = 0
        self.observation_count = 0

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "v2503.2-two-pass-fixture",
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
        return [
            {
                "url": f"https://evidence{index}-{item}.gov/data",
                "source_kind": "primary_data",
                "fetched_at": "2026-08-28T00:00:00+00:00",
            }
            for item in range(limit)
        ]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        self.observation_count += 1
        dimension = str(candidate.get("evidence_dimension") or "")
        if dimension:
            self.follow_up_dimensions.append(dimension)
        citation_id = f"web-{self.observation_count:016x}"
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": digest({"observation": self.observation_count}),
            "terminal_result_digest": digest({"result": self.observation_count}),
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"),
            "stance": "unknown",
            "evidence_digest": digest({"citation": citation_id}),
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

    def _payload(self, citations, *, include_dimensions: bool) -> dict[str, object]:
        rows = [dict(row) for row in citations]
        all_ids = [str(row["citation_id"]) for row in rows]
        opportunities = []
        for index, source in enumerate(OPPORTUNITIES):
            item = dict(source)
            item["citation_ids"] = all_ids[index:index + 2] or all_ids[:2]
            dimensions: dict[str, object] = {}
            if include_dimensions:
                expected = candidate_digest(source)
                for dimension in ("demand", "competition", "implementation_dependencies", "free_tier_feasibility"):
                    ids = [
                        str(row["citation_id"])
                        for row in rows
                        if row.get("candidate_digest") == expected and row.get("evidence_dimension") == dimension
                    ]
                    if ids:
                        dimensions[dimension] = {
                            "summary": f"Candidate-specific {dimension.replace('_', ' ')} evidence was observed.",
                            "citation_ids": ids,
                        }
            item["evidence_dimensions"] = dimensions
            opportunities.append(item)
        return {
            "opportunities": opportunities,
            "recommendation": {
                "opportunity_name": "Compliance reminder",
                "conclusion": "It has the narrowest implementation boundary.",
                "citation_ids": all_ids[:2],
            },
            "disagreements": ["Observed demand does not establish conversion."],
            "limitations": ["No purchase or outreach experiment occurred."],
        }

    def discover_candidates(self, *, decomposition, citations):
        self.discovery_calls += 1
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": self._payload(citations, include_dimensions=False),
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }

    def synthesize(self, *, decomposition, citations):
        self.final_synthesis_calls += 1
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": self._payload(citations, include_dimensions=True),
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }


class IntermittentSearchAdapter(TwoPassAdapter):
    def __init__(self, fail_on_search: int) -> None:
        super().__init__()
        self.fail_on_search = fail_on_search

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        if len(self.search_queries) + 1 == self.fail_on_search:
            self.search_queries.append(query)
            error = RuntimeError("fixture search status rejected")
            error.code = "public_web_http_status_rejected"
            raise error
        return super().search(query, limit=limit, timeout_seconds=timeout_seconds)


class DuplicateLeadingResultAdapter(TwoPassAdapter):
    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.search_queries.append(query)
        self.search_limits.append(limit)
        index = len(self.search_queries)
        if index <= 4:
            return [
                {
                    "url": f"https://initial{index}-{item}.gov/data",
                    "source_kind": "primary_data",
                    "fetched_at": "2026-08-28T00:00:00+00:00",
                }
                for item in range(limit)
            ]
        rows = [{
            "url": "https://repeated-leading-result.gov/data",
            "source_kind": "primary_data",
            "fetched_at": "2026-08-28T00:00:00+00:00",
        }]
        rows.extend({
            "url": f"https://fallback{index}-{item}.gov/data",
            "source_kind": "primary_data",
            "fetched_at": "2026-08-28T00:00:00+00:00",
        } for item in range(1, limit))
        return rows[:limit]


class FirstFollowObservationFailureAdapter(TwoPassAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.failed_follow_observation = False

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        if candidate.get("evidence_dimension") and not self.failed_follow_observation:
            self.failed_follow_observation = True
            error = RuntimeError("fixture observation failed")
            error.code = "public_web_observation_failed"
            raise error
        return super().observe(candidate, plan=plan, max_bytes=max_bytes, timeout_seconds=timeout_seconds)


class StubbornFirstFollowCellAdapter(TwoPassAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.first_follow_cell = ""
        self.first_cell_failure_count = 0
        self.attempted_follow_cells: list[str] = []

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        if candidate.get("evidence_dimension"):
            cell = str(candidate.get("subquestion_id") or "")
            self.attempted_follow_cells.append(cell)
            if not self.first_follow_cell:
                self.first_follow_cell = cell
            if cell == self.first_follow_cell:
                self.first_cell_failure_count += 1
                error = RuntimeError("fixture cell remains unavailable")
                error.code = "public_web_http_status_rejected"
                raise error
        return super().observe(candidate, plan=plan, max_bytes=max_bytes, timeout_seconds=timeout_seconds)


class RejectedDiscoveryAdapter(TwoPassAdapter):
    def discover_candidates(self, *, decomposition, citations):
        self.discovery_calls += 1
        payload = self._payload(citations, include_dimensions=False)
        for row, title in zip(
            payload["opportunities"],
            ("AI-Powered Legal Workflow Automation", "Niche Analytics Tools", "Developer Utilities"),
        ):
            row["name"] = title
        payload["recommendation"]["opportunity_name"] = "AI-Powered Legal Workflow Automation"
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": payload,
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }

    def synthesize(self, *, decomposition, citations):
        self.final_synthesis_calls += 1
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": self._payload(citations, include_dimensions=False),
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }


class SemanticRepairAdapter(RejectedDiscoveryAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.semantic_repair_calls = 0

    def discover_candidates(self, *, decomposition, citations):
        self.discovery_calls += 1
        payload = self._payload(citations, include_dimensions=False)
        payload["opportunities"][0]["customer"] = ""
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": payload,
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }

    def repair_candidate_discovery(self, *, decomposition, citations):
        self.semantic_repair_calls += 1
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": self._payload(citations, include_dimensions=False),
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }

    def synthesize(self, *, decomposition, citations):
        return TwoPassAdapter.synthesize(self, decomposition=decomposition, citations=citations)


class StructuralDiscoveryRepairAdapter(TwoPassAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.structural_repair_calls = 0

    def discover_candidates(self, *, decomposition, citations):
        self.discovery_calls += 1
        return {
            "ok": False,
            "status": "research_synthesis_generation_invalid",
            "provider_contacted": True,
            "provider_request_count": 2,
            "generation_retry_used": True,
        }

    def repair_candidate_discovery(self, *, decomposition, citations):
        self.structural_repair_calls += 1
        return {
            "ok": True,
            "status": "research_synthesis_generated",
            "payload": self._payload(citations, include_dimensions=False),
            "provider_contacted": True,
            "provider_request_count": 1,
            "private_objective_sent_to_provider": False,
        }


class UnrecoverableStructuralDiscoveryAdapter(StructuralDiscoveryRepairAdapter):
    def repair_candidate_discovery(self, *, decomposition, citations):
        self.structural_repair_calls += 1
        return {
            "ok": False,
            "status": "research_synthesis_generation_invalid",
            "provider_contacted": True,
            "provider_request_count": 1,
        }


class MutableClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class TimeExhaustingDiscoveryAdapter(TwoPassAdapter):
    def __init__(self, clock: MutableClock) -> None:
        super().__init__()
        self.fixture_clock = clock

    def discover_candidates(self, *, decomposition, citations):
        result = super().discover_candidates(decomposition=decomposition, citations=citations)
        self.fixture_clock.value = 301.0
        return result


fixture_citations = [
    {
        "citation_id": f"web-{index:016x}",
        "public_url": f"https://source{index}.example/evidence",
        "quality_score": 0.8,
        "relevance_score": 0.8,
    }
    for index in range(1, 7)
]
fixture_payload = TwoPassAdapter()._payload(fixture_citations, include_dimensions=False)
validated = validate_research_synthesis(fixture_payload, citations=fixture_citations, requested_result_count=3)
require(validated["ok"], "broad_candidate_discovery_is_valid_before_follow_up")

discovery_without_recommendation = json.loads(json.dumps(fixture_payload))
discovery_without_recommendation["recommendation"] = {}
discovery_only = validate_research_synthesis(
    discovery_without_recommendation,
    citations=fixture_citations,
    requested_result_count=3,
    require_recommendation=False,
)
require(discovery_only["ok"], "candidate_discovery_does_not_require_premature_comparative_winner")
final_without_recommendation = validate_research_synthesis(
    discovery_without_recommendation,
    citations=fixture_citations,
    requested_result_count=3,
)
require(not final_without_recommendation["ok"], "final_synthesis_still_requires_comparative_recommendation")

generic_payload = json.loads(json.dumps(fixture_payload))
for row, title in zip(
    generic_payload["opportunities"],
    ("AI-Powered Legal Workflow Automation", "Niche Analytics Tools", "Developer Utilities"),
):
    row["name"] = title
generic_payload["recommendation"]["opportunity_name"] = "AI-Powered Legal Workflow Automation"
generic_result = validate_research_synthesis(generic_payload, citations=fixture_citations, requested_result_count=3)
require(not generic_result["ok"], "broad_product_categories_do_not_pass_as_concrete_opportunities")
require(generic_result["rejected_opportunity_reason_counts"] == {"generic_name": 3}, "candidate_rejection_reasons_are_content_free_and_specific")
generic_discovery = validate_research_synthesis(
    generic_payload,
    citations=fixture_citations,
    requested_result_count=3,
    require_recommendation=False,
    allow_generic_opportunity_names=True,
)
require(generic_discovery["ok"], "broad_discovery_labels_can_enter_candidate_evidence_stage")

generic_matrix_payload = json.loads(json.dumps(generic_payload))
generic_matrix_citations = json.loads(json.dumps(fixture_citations))
generic_identities = [
    row for row in generic_discovery["reasonable_inferences"]
    if row.get("claim_code") != "synthesis_recommendation"
]
for candidate_index, (row, identity) in enumerate(zip(generic_matrix_payload["opportunities"], generic_identities), 1):
    row["evidence_dimensions"] = {}
    for dimension_index, dimension in enumerate(("demand", "competition", "implementation_dependencies", "free_tier_feasibility"), 1):
        citation_id = f"web-generic-{candidate_index}-{dimension_index}"
        generic_matrix_citations.append({
            "citation_id": citation_id,
            "public_url": f"https://generic{candidate_index}-{dimension_index}.example/evidence",
            "source_kind": "primary_data",
            "quality_score": 0.3,
            "relevance_score": 0.8,
            "candidate_digest": identity["candidate_digest"],
            "evidence_dimension": dimension,
        })
        row["evidence_dimensions"][dimension] = {
            "summary": f"Candidate-specific {dimension} evidence was observed.",
            "citation_ids": [citation_id],
        }
generic_matrix_result = validate_research_synthesis(
    generic_matrix_payload,
    citations=generic_matrix_citations,
    requested_result_count=3,
    candidate_identities=generic_discovery,
    require_candidate_specific_coverage=True,
    candidate_research_matrix_complete=True,
)
require(generic_matrix_result["ok"], "broad_label_requires_complete_candidate_specific_matrix_before_final_admission")
require(
    all(row["generic_name_fully_evidence_bound"] for row in generic_matrix_result["reasonable_inferences"][:3]),
    "broad_final_labels_are_explicitly_bound_to_complete_candidate_evidence",
)

generic_sparse_payload = json.loads(json.dumps(generic_payload))
generic_sparse_payload["recommendation"] = {}
generic_sparse_result = validate_research_synthesis(
    generic_sparse_payload,
    citations=fixture_citations,
    requested_result_count=3,
    candidate_identities=generic_discovery,
    require_candidate_specific_coverage=True,
    candidate_research_matrix_complete=True,
    require_recommendation=False,
)
require(generic_sparse_result["ok"], "researched_generic_candidate_is_retained_with_explicit_evidence_gaps")
require(generic_sparse_result["candidate_specificity_limited_count"] == 3, "generic_candidate_specificity_limit_is_counted")
require(not generic_sparse_result["recommendation_deterministic_fallback_used"], "evidence_gap_review_does_not_invent_a_recommendation")
require("No candidate clears the evidence threshold" in generic_sparse_result["rendered_answer"], "evidence_gap_review_states_that_no_recommendation_clears")

retry_prompts: list[str] = []


def retry_synthesizer(prompt: str):
    retry_prompts.append(prompt)
    return "not-json" if len(retry_prompts) == 1 else fixture_payload


retry_adapter = GovernedPublicWebResearchAdapter(synthesizer=retry_synthesizer)
retry_citations = []
for index in range(15):
    citation_id = f"web-{index + 100:016x}"
    retry_adapter._transient_documents[citation_id] = {
        "citation_id": citation_id,
        "title": f"Public evidence {index}",
        "source_kind": "community_experience",
        "excerpt": "evidence " * 600,
        "public_url": f"https://source{index}.example/evidence",
        "query_terms": ["evidence"],
        "candidate_name": "",
        "candidate_digest": "",
        "evidence_dimension": "",
    }
    retry_citations.append({
        "citation_id": citation_id,
        "public_url": f"https://source{index}.example/evidence",
        "quality_score": 0.6,
        "relevance_score": 0.8,
    })
retry_result = retry_adapter.synthesize(
    decomposition={"requested_result_count": 3},
    citations=retry_citations,
)
require(retry_result["ok"] and retry_result["provider_request_count"] == 2, "invalid_json_gets_one_bounded_synthesis_retry")
require(retry_result["generation_retry_used"], "synthesis_retry_is_reported_truthfully")
require(retry_result["public_source_excerpt_char_count"] <= 7200, "final_synthesis_excerpts_fit_conservative_context_budget")
require(max(len(prompt) for prompt in retry_prompts) < 20_000, "full_matrix_prompt_is_compacted_for_eight_k_context")
require(len(retry_prompts[1]) < len(retry_prompts[0]), "invalid_json_retry_uses_smaller_recovery_context")
require("at most 24 words" in retry_prompts[1], "invalid_json_retry_bounds_structured_field_length")
require(retry_prompts[1].count("UNTRUSTED PUBLIC DOCUMENTS") == 0, "invalid_json_retry_does_not_duplicate_full_prompt")

digest_bound_prompts: list[str] = []
compact_final_payload = {
    "opportunities": [
        {
            "candidate_digest": candidate_digest(source),
            "evidence_summary": "Candidate-specific evidence was observed.",
            "citation_ids": [fixture_citations[index]["citation_id"]],
            "evidence_dimensions": {},
            "uncertainties": ["Conversion remains untested."],
        }
        for index, source in enumerate(OPPORTUNITIES[:2])
    ],
    "recommendation": {
        "candidate_digest": candidate_digest(OPPORTUNITIES[0]),
        "conclusion": "It has the narrowest bounded implementation.",
        "citation_ids": [fixture_citations[0]["citation_id"]],
    },
    "disagreements": [],
    "limitations": ["No purchase experiment occurred."],
}


def digest_bound_synthesizer(prompt: str):
    digest_bound_prompts.append(prompt)
    return fixture_payload if len(digest_bound_prompts) == 1 else compact_final_payload


digest_bound_adapter = GovernedPublicWebResearchAdapter(synthesizer=digest_bound_synthesizer)
for index, citation in enumerate(fixture_citations):
    source = OPPORTUNITIES[index % len(OPPORTUNITIES)]
    digest_bound_adapter._transient_documents[citation["citation_id"]] = {
        "citation_id": citation["citation_id"],
        "title": f"Candidate evidence {index}",
        "source_kind": "community_experience",
        "excerpt": "Candidate-specific public evidence.",
        "public_url": citation["public_url"],
        "query_terms": ["evidence"],
        "candidate_name": source["name"],
        "candidate_digest": candidate_digest(source),
        "evidence_dimension": "demand",
    }
digest_bound_discovery = digest_bound_adapter.discover_candidates(
    decomposition={"requested_result_count": 3},
    citations=fixture_citations,
)
require(digest_bound_discovery["ok"], "digest_bound_final_test_caches_candidate_discovery")
digest_bound_final = digest_bound_adapter.synthesize(
    decomposition={"requested_result_count": 3},
    citations=fixture_citations,
)
expanded_rows = digest_bound_final["payload"]["opportunities"]
require([row["name"] for row in expanded_rows] == [row["name"] for row in OPPORTUNITIES], "digest_bound_final_restores_exact_candidate_names")
require(all(row.get("customer") and row.get("problem") and row.get("product") for row in expanded_rows), "digest_bound_final_restores_required_candidate_identity")
require(len(expanded_rows) == 3, "digest_bound_final_restores_model_omitted_discovery_candidate")
require(digest_bound_final["payload"]["recommendation"]["opportunity_name"] == OPPORTUNITIES[0]["name"], "digest_bound_recommendation_restores_exact_candidate_name")
require("candidate_digest" in digest_bound_prompts[1], "final_prompt_requests_digest_bound_candidate_rows")

paraphrased_payload = json.loads(json.dumps(fixture_payload))
paraphrased_payload["opportunities"][0]["customer"] = "independent regulated-service operators"
paraphrased_payload["opportunities"][0]["problem"] = "deadline administration remains repetitive and error prone"
paraphrased_citations = json.loads(json.dumps(fixture_citations))
paraphrased_citations[0]["candidate_digest"] = validated["reasonable_inferences"][0]["candidate_digest"]
paraphrased_citations[0]["evidence_dimension"] = "demand"
paraphrased_citations[0]["source_kind"] = "primary_data"
paraphrased_payload["opportunities"][0]["evidence_dimensions"] = {
    "demand": {
        "summary": "Candidate-specific demand evidence was observed.",
        "citation_ids": [paraphrased_citations[0]["citation_id"]],
    }
}
paraphrased = validate_research_synthesis(
    paraphrased_payload,
    citations=paraphrased_citations,
    requested_result_count=3,
    candidate_identities=validated,
)
require(paraphrased["ok"], "paraphrased_final_candidate_remains_valid")
require(paraphrased["candidate_identity_binding_count"] == 3, "final_candidates_bind_to_discovery_identity")
require(
    paraphrased["reasonable_inferences"][0]["evidence_dimensions"]["demand"]["candidate_specific_evidence_present"],
    "paraphrasing_does_not_detach_candidate_specific_evidence",
)

weak_payload = json.loads(json.dumps(fixture_payload))
weak_citations = json.loads(json.dumps(fixture_citations))
identity_findings = [
    row for row in validated["reasonable_inferences"]
    if row.get("claim_code") != "synthesis_recommendation"
]
for index, (row, identity) in enumerate(zip(weak_payload["opportunities"], identity_findings)):
    citation = weak_citations[index]
    citation["quality_score"] = 0.3
    citation["source_kind"] = "primary_data"
    citation["candidate_digest"] = identity["candidate_digest"]
    citation["evidence_dimension"] = "demand"
    row["evidence_dimensions"] = {
        "demand": {
            "summary": "Candidate-specific but weak demand evidence was observed.",
            "citation_ids": [citation["citation_id"]],
        }
    }
weak_result = validate_research_synthesis(
    weak_payload,
    citations=weak_citations,
    requested_result_count=3,
    candidate_identities=validated,
    require_candidate_specific_coverage=True,
)
require(not weak_result["ok"], "partial_candidate_matrix_is_not_reported_as_complete")
require(
    all(row["evidence_dimensions"]["demand"]["evidence_strength"] == "weak" for row in weak_result["reasonable_inferences"][:3]),
    "weak_candidate_evidence_is_not_upgraded",
)
require(
    all("demand" not in row["evidence_gap_dimensions"] for row in weak_result["reasonable_inferences"][:3]),
    "weak_candidate_evidence_is_distinguished_from_missing_evidence",
)
matrix_complete_partial = validate_research_synthesis(
    weak_payload,
    citations=weak_citations,
    requested_result_count=3,
    candidate_identities=validated,
    require_candidate_specific_coverage=True,
    candidate_research_matrix_complete=True,
)
require(matrix_complete_partial["ok"], "fully_attempted_matrix_can_return_explicit_evidence_gaps")
require(not matrix_complete_partial["candidate_specific_coverage_complete"], "researched_uncertainty_is_not_mislabeled_as_complete_evidence")
require(matrix_complete_partial["candidate_research_matrix_complete"], "matrix_attempt_completion_is_recorded_separately")
require("Best current lead for further research" in matrix_complete_partial["rendered_answer"], "partial_evidence_cannot_render_an_unqualified_winner")
planned = plan_candidate_evidence_follow_up(
    validated,
    remaining_query_budget=4,
    remaining_page_budget=4,
    remaining_failure_budget=4,
    max_followups=4,
)
require(planned["status"] == "candidate_evidence_follow_up_ready", "candidate_specific_follow_up_is_planned")
require(planned["query_count"] == 4, "follow_up_respects_four_query_cap")
require(planned["candidate_count"] == 3, "follow_up_reaches_all_three_candidates_before_repeating_one")
require(set(planned["evidence_dimensions"]) == {"demand", "competition"}, "round_robin_prioritizes_demand_then_next_material_gap")
require(all(row["candidate_digest"] and row["query_digest"] for row in planned["public_summary"]), "public_plan_is_digest_bound")
require(not planned["candidate_identity_exposed_in_public_receipt"] and not planned["raw_query_text_exposed"], "public_plan_excludes_candidate_names_and_queries")

full_matrix = plan_candidate_evidence_follow_up(
    validated,
    remaining_query_budget=12,
    remaining_page_budget=12,
    remaining_failure_budget=4,
    max_followups=12,
)
require(full_matrix["query_count"] == 12, "three_by_four_candidate_evidence_matrix_is_planned")
require(full_matrix["candidate_count"] == 3, "full_matrix_retains_all_three_candidates")
require(
    set(full_matrix["evidence_dimensions"]) == {"demand", "competition", "implementation_dependencies", "free_tier_feasibility"},
    "full_matrix_covers_all_requested_evidence_dimensions",
)
dimension_markers = {
    "demand": "demand",
    "competition": "competitors",
    "implementation_dependencies": "implementation",
    "free_tier_feasibility": "free",
}
require(
    all(dimension_markers[row["evidence_dimension"]] in row["query"].split() for row in full_matrix["queries"]),
    "sanitized_matrix_queries_retain_their_evidence_dimension_terms",
)

runtime = Path(os.environ["EIDOLON_DATA_DIR"])
store = BoundedResearchSessionStore(runtime)
adapter = TwoPassAdapter()
created = store.create_session("v2503.2:create", objective=OBJECTIVE)
session = created["result"]
require(session["budget"]["max_queries"] == 8, "default_session_reserves_candidate_follow_up_query_capacity")


class ConversationCreateStore:
    def __init__(self) -> None:
        self.budget: dict[str, object] = {}

    def create_session(self, event_id, *, objective, budget):
        self.budget = dict(budget)
        return {
            "ok": True,
            "status": "research_session_created",
            "result": {
                "session_id": "research-" + "a" * 24,
                "session_digest": "b" * 64,
                "state": "prepared",
                "budget": dict(budget),
            },
        }


conversation_store = ConversationCreateStore()
conversation_created = execute_conversational_research_action(
    "research_session_create",
    {"objective": OBJECTIVE},
    event_id="v2503.2:conversation-create",
    store=conversation_store,
)
require(conversation_created["ok"], "conversation_research_session_is_created")
require(conversation_store.budget["max_queries"] == 20, "conversation_path_reserves_full_candidate_follow_up_query_and_retry_capacity")
require(conversation_store.budget["max_candidates"] == 32, "conversation_path_reserves_two_independent_sources_per_candidate_cell")
require(conversation_store.budget["max_observed_pages"] == 28, "conversation_path_reserves_discovery_plus_two_sources_per_candidate_cell")
require(conversation_store.budget["max_source_failures"] == 12, "conversation_path_tolerates_hard_bounded_public_source_failures")
require(conversation_store.budget["max_elapsed_seconds"] == 600, "conversation_path_reserves_time_for_discovery_follow_up_and_final_synthesis")
require(CANDIDATE_DISCOVERY_MAX_TOKENS >= 2000, "candidate_discovery_has_bounded_structured_output_room")
require(FINAL_SYNTHESIS_MAX_TOKENS > CANDIDATE_DISCOVERY_MAX_TOKENS, "final_synthesis_has_additional_structured_output_room")

invalid_message = _research_report_message(
    {"session_id": "research-" + "c" * 24},
    {
        "status": "research_report_insufficient_evidence",
        "synthesis_status": "research_synthesis_generation_invalid",
        "citations": [],
        "missing_evidence": [{"claim_code": "requested_result_count"}],
    },
)
require("did not produce a trustworthy answer" in invalid_message, "invalid_synthesis_is_not_presented_as_success")
require("no recommendation should be inferred" in invalid_message, "invalid_synthesis_blocks_false_recommendation")
authorized = store.authorize_session(
    "v2503.2:authorize",
    session_id=session["session_id"],
    session_digest=session["session_digest"],
    public_query_confirmed=True,
)
run = store.execute_session(
    "v2503.2:execute",
    session_id=session["session_id"],
    authorization_digest=authorized["result"]["authorization_digest"],
    adapter=adapter,
)
report = run["result"]["report"]
require(run["ok"] and report["status"] == "research_report_insufficient_evidence", "partial_candidate_follow_up_remains_explicitly_incomplete")
require(adapter.discovery_calls == 1 and adapter.final_synthesis_calls == 1, "discovery_and_final_synthesis_each_run_once")
require(report["provider_request_count"] == 2, "both_bounded_provider_requests_are_reported")
require(report["candidate_follow_up_query_count"] == 4, "report_records_candidate_follow_up_query_count")
require(report["candidate_follow_up_candidate_count"] == 3, "report_records_candidate_coverage_count")
require(set(report["candidate_follow_up_dimensions"]) == {"demand", "competition"}, "report_records_dimensions_actually_researched")
require(not report["candidate_specific_coverage_complete"], "partial_matrix_does_not_claim_complete_candidate_coverage")
require(len(adapter.follow_up_dimensions) == 8, "two_sources_are_observed_for_each_partial_matrix_cell")
require(not report["rendered_answer"], "incomplete_candidate_matrix_suppresses_rendered_answer")
require(
    any(str(row.get("claim_code") or "").endswith("_candidate_evidence") for row in report["missing_evidence"]),
    "incomplete_candidate_matrix_records_explicit_evidence_gaps",
)
require(not report["candidate_identity_exposed_in_public_receipt"], "public_receipt_does_not_expose_candidate_identity")
require(not report["private_objective_sent_to_provider"], "private_objective_remains_out_of_both_synthesis_calls")

rejected_adapter = RejectedDiscoveryAdapter()
rejected_created = store.create_session("v2503.2:rejected-discovery-create", objective=OBJECTIVE)
rejected_session = rejected_created["result"]
rejected_authorized = store.authorize_session(
    "v2503.2:rejected-discovery-authorize",
    session_id=rejected_session["session_id"],
    session_digest=rejected_session["session_digest"],
    public_query_confirmed=True,
)
rejected_run = store.execute_session(
    "v2503.2:rejected-discovery-execute",
    session_id=rejected_session["session_id"],
    authorization_digest=rejected_authorized["result"]["authorization_digest"],
    adapter=rejected_adapter,
)
rejected_report = rejected_run["result"]["report"]
require(rejected_run["ok"], "rejected_candidate_discovery_can_complete_collection_without_admitting_answer")
require(rejected_report["status"] == "research_report_insufficient_evidence", "rejected_discovery_reports_insufficient_evidence")
require(rejected_report["candidate_specific_coverage_required"], "comparative_opportunity_report_always_requires_candidate_coverage")
require(not rejected_report["candidate_specific_coverage_complete"], "unresearched_candidates_do_not_claim_complete_coverage")

semantic_adapter = SemanticRepairAdapter()
semantic_created = store.create_session("v2503.2:semantic-repair-create", objective=OBJECTIVE)
semantic_session = semantic_created["result"]
semantic_authorized = store.authorize_session(
    "v2503.2:semantic-repair-authorize",
    session_id=semantic_session["session_id"],
    session_digest=semantic_session["session_digest"],
    public_query_confirmed=True,
)
semantic_run = store.execute_session(
    "v2503.2:semantic-repair-execute",
    session_id=semantic_session["session_id"],
    authorization_digest=semantic_authorized["result"]["authorization_digest"],
    adapter=semantic_adapter,
)
semantic_report = semantic_run["result"]["report"]
require(semantic_run["ok"] and semantic_report["status"] == "research_report_insufficient_evidence", "semantic_candidate_repair_recovers_discovery_without_overstating_partial_coverage")
require(semantic_adapter.semantic_repair_calls == 1, "semantic_candidate_repair_is_bounded_to_one_attempt")
require(semantic_report["candidate_discovery_semantic_repair_used"], "semantic_candidate_repair_is_reported_truthfully")
require(semantic_report["provider_request_count"] == 3, "semantic_repair_provider_request_is_counted")
require(semantic_report["candidate_follow_up_query_count"] == 4, "repaired_candidates_receive_bounded_evidence_follow_up")
require(semantic_report["candidate_discovery_validation_diagnostics"]["admitted_opportunity_count"] == 3, "semantic_repair_admission_count_is_reported")

structural_adapter = StructuralDiscoveryRepairAdapter()
structural_created = store.create_session("v2503.2:structural-repair-create", objective=OBJECTIVE)
structural_session = structural_created["result"]
structural_authorized = store.authorize_session(
    "v2503.2:structural-repair-authorize",
    session_id=structural_session["session_id"],
    session_digest=structural_session["session_digest"],
    public_query_confirmed=True,
)
structural_run = store.execute_session(
    "v2503.2:structural-repair-execute",
    session_id=structural_session["session_id"],
    authorization_digest=structural_authorized["result"]["authorization_digest"],
    adapter=structural_adapter,
)
structural_report = structural_run["result"]["report"]
require(structural_run["ok"], "malformed_candidate_discovery_can_reach_semantic_repair")
require(structural_adapter.structural_repair_calls == 1, "malformed_candidate_discovery_gets_one_bounded_semantic_repair")
require(structural_report["candidate_discovery_semantic_repair_used"], "structural_candidate_repair_is_reported")
require(structural_report["candidate_follow_up_query_count"] == 4, "structurally_repaired_candidates_receive_follow_up")
require(structural_report["provider_request_count"] == 4, "structural_repair_and_final_synthesis_requests_are_counted")

unrecoverable_adapter = UnrecoverableStructuralDiscoveryAdapter()
unrecoverable_created = store.create_session("v2503.2:unrecoverable-discovery-create", objective=OBJECTIVE)
unrecoverable_session = unrecoverable_created["result"]
unrecoverable_authorized = store.authorize_session(
    "v2503.2:unrecoverable-discovery-authorize",
    session_id=unrecoverable_session["session_id"],
    session_digest=unrecoverable_session["session_digest"],
    public_query_confirmed=True,
)
unrecoverable_run = store.execute_session(
    "v2503.2:unrecoverable-discovery-execute",
    session_id=unrecoverable_session["session_id"],
    authorization_digest=unrecoverable_authorized["result"]["authorization_digest"],
    adapter=unrecoverable_adapter,
)
unrecoverable_report = unrecoverable_run["result"]["report"]
require(unrecoverable_run["ok"] and unrecoverable_report["status"] == "research_report_insufficient_evidence", "unrecoverable_discovery_fails_closed")
require(unrecoverable_adapter.structural_repair_calls == 1, "unrecoverable_discovery_repair_is_not_repeated")
require(unrecoverable_adapter.final_synthesis_calls == 0, "final_synthesis_is_skipped_without_candidate_identities")
require(unrecoverable_report["provider_request_count"] == 3, "unrecoverable_discovery_does_not_spend_final_synthesis_requests")

expired_clock = MutableClock()
expired_store = BoundedResearchSessionStore(runtime / "expired-clock", clock=expired_clock)
expired_adapter = TimeExhaustingDiscoveryAdapter(expired_clock)
expired_created = expired_store.create_session(
    "v2503.2:expired-after-discovery-create",
    objective=OBJECTIVE,
    budget={
        "max_queries": 16,
        "max_candidates": 24,
        "max_observed_pages": 16,
        "max_total_bytes": 4 * 1024 * 1024,
        "max_elapsed_seconds": 300,
        "max_source_failures": 8,
    },
)
expired_session = expired_created["result"]
expired_authorized = expired_store.authorize_session(
    "v2503.2:expired-after-discovery-authorize",
    session_id=expired_session["session_id"],
    session_digest=expired_session["session_digest"],
    public_query_confirmed=True,
)
expired_run = expired_store.execute_session(
    "v2503.2:expired-after-discovery-execute",
    session_id=expired_session["session_id"],
    authorization_digest=expired_authorized["result"]["authorization_digest"],
    adapter=expired_adapter,
)
expired_report = expired_run["result"]["report"]
require(expired_run["ok"] and expired_report["status"] == "research_report_insufficient_evidence", "expired_session_fails_closed_after_candidate_discovery")
require(expired_adapter.final_synthesis_calls == 0, "expired_session_starts_no_final_provider_request")
require(expired_report["provider_request_count"] == 1, "expired_session_reports_only_completed_discovery_request")
require(expired_run["result"]["session"]["stop_reason"] == "time_budget_reached", "expired_session_reports_time_budget_stop")

full_adapter = TwoPassAdapter()
full_created = store.create_session(
    "v2503.2:full-matrix-create",
    objective=OBJECTIVE,
    budget={
        "max_queries": 16,
        "max_candidates": 32,
        "max_observed_pages": 28,
        "max_total_bytes": 4 * 1024 * 1024,
        "max_elapsed_seconds": 300,
        "max_source_failures": 4,
    },
)
full_session = full_created["result"]
full_authorized = store.authorize_session(
    "v2503.2:full-matrix-authorize",
    session_id=full_session["session_id"],
    session_digest=full_session["session_digest"],
    public_query_confirmed=True,
)
full_run = store.execute_session(
    "v2503.2:full-matrix-execute",
    session_id=full_session["session_id"],
    authorization_digest=full_authorized["result"]["authorization_digest"],
    adapter=full_adapter,
)
full_report = full_run["result"]["report"]
require(full_run["ok"] and full_report["status"] == "research_report_ready", "conversation_sized_research_matrix_completes")
require(full_report["candidate_follow_up_query_count"] == 12, "conversation_sized_run_executes_twelve_candidate_followups")
require(full_report["candidate_follow_up_candidate_count"] == 3, "conversation_sized_run_covers_three_candidates")
require(len(full_report["candidate_follow_up_dimensions"]) == 4, "conversation_sized_run_covers_four_dimensions")
require(len(full_adapter.follow_up_dimensions) == 24, "two_independent_sources_per_candidate_dimension_are_observed")
matrix_search_limits = full_adapter.search_limits[-12:]
require(
    len(matrix_search_limits) == 12
    and matrix_search_limits[0] == 6
    and all(1 <= value <= 6 for value in matrix_search_limits)
    and sum(matrix_search_limits) > 24,
    "candidate_evidence_matrix_considers_bounded_fallback_results_within_candidate_budget",
)
require(full_report["candidate_identity_binding_count"] == 3, "full_matrix_final_synthesis_preserves_candidate_identity")

duplicate_adapter = DuplicateLeadingResultAdapter()
duplicate_created = store.create_session(
    "v2503.2:duplicate-leading-create",
    objective=OBJECTIVE,
    budget={
        "max_queries": 16,
        "max_candidates": 32,
        "max_observed_pages": 28,
        "max_total_bytes": 4 * 1024 * 1024,
        "max_elapsed_seconds": 300,
        "max_source_failures": 4,
    },
)
duplicate_session = duplicate_created["result"]
duplicate_authorized = store.authorize_session(
    "v2503.2:duplicate-leading-authorize",
    session_id=duplicate_session["session_id"],
    session_digest=duplicate_session["session_digest"],
    public_query_confirmed=True,
)
duplicate_run = store.execute_session(
    "v2503.2:duplicate-leading-execute",
    session_id=duplicate_session["session_id"],
    authorization_digest=duplicate_authorized["result"]["authorization_digest"],
    adapter=duplicate_adapter,
)
duplicate_report = duplicate_run["result"]["report"]
require(duplicate_run["ok"] and duplicate_report["status"] == "research_report_ready", "duplicate_leading_results_use_bounded_fallbacks")
require(len(duplicate_adapter.follow_up_dimensions) == 24, "duplicate_leading_result_preserves_two_sources_per_matrix_cell")
require(duplicate_report["candidate_specific_coverage_complete"], "duplicate_fallback_preserves_complete_candidate_matrix")

observation_fallback_adapter = FirstFollowObservationFailureAdapter()
observation_fallback_created = store.create_session(
    "v2503.2:observation-fallback-create",
    objective=OBJECTIVE,
    budget={
        "max_queries": 16,
        "max_candidates": 32,
        "max_observed_pages": 28,
        "max_total_bytes": 4 * 1024 * 1024,
        "max_elapsed_seconds": 300,
        "max_source_failures": 4,
    },
)
observation_fallback_session = observation_fallback_created["result"]
observation_fallback_authorized = store.authorize_session(
    "v2503.2:observation-fallback-authorize",
    session_id=observation_fallback_session["session_id"],
    session_digest=observation_fallback_session["session_digest"],
    public_query_confirmed=True,
)
observation_fallback_run = store.execute_session(
    "v2503.2:observation-fallback-execute",
    session_id=observation_fallback_session["session_id"],
    authorization_digest=observation_fallback_authorized["result"]["authorization_digest"],
    adapter=observation_fallback_adapter,
)
observation_fallback_report = observation_fallback_run["result"]["report"]
require(observation_fallback_run["ok"] and observation_fallback_report["status"] == "research_report_ready", "failed_observation_uses_same_query_fallback")
require(observation_fallback_adapter.failed_follow_observation, "observation_fallback_fixture_exercised_failure")
require(len(observation_fallback_adapter.follow_up_dimensions) == 24, "observation_fallback_preserves_two_sources_per_matrix_cell")
require(observation_fallback_run["result"]["session"]["source_failure_count"] == 1, "failed_primary_page_remains_truthfully_counted")

stubborn_adapter = StubbornFirstFollowCellAdapter()
stubborn_created = store.create_session(
    "v2503.2:stubborn-cell-create",
    objective=OBJECTIVE,
    budget={
        "max_queries": 16,
        "max_candidates": 32,
        "max_observed_pages": 28,
        "max_total_bytes": 4 * 1024 * 1024,
        "max_elapsed_seconds": 300,
        "max_source_failures": 12,
    },
)
stubborn_session = stubborn_created["result"]
stubborn_authorized = store.authorize_session(
    "v2503.2:stubborn-cell-authorize",
    session_id=stubborn_session["session_id"],
    session_digest=stubborn_session["session_digest"],
    public_query_confirmed=True,
)
stubborn_run = store.execute_session(
    "v2503.2:stubborn-cell-execute",
    session_id=stubborn_session["session_id"],
    authorization_digest=stubborn_authorized["result"]["authorization_digest"],
    adapter=stubborn_adapter,
)
require(stubborn_run["ok"], "stubborn_matrix_cell_finishes_with_truthful_insufficient_evidence")
require(stubborn_adapter.first_cell_failure_count == 2, "one_matrix_cell_is_bounded_to_two_failed_page_attempts")
require(len(set(stubborn_adapter.attempted_follow_cells)) > 1, "later_matrix_cells_run_after_stubborn_source_failures")
require(stubborn_run["result"]["session"]["source_failure_count"] == 2, "stubborn_cell_failures_remain_truthfully_counted")

intermittent_adapter = IntermittentSearchAdapter(fail_on_search=8)
intermittent_created = store.create_session(
    "v2503.2:intermittent-create",
    objective=OBJECTIVE,
    budget={
        "max_queries": 20,
        "max_candidates": 32,
        "max_observed_pages": 28,
        "max_total_bytes": 4 * 1024 * 1024,
        "max_elapsed_seconds": 300,
        "max_source_failures": 4,
    },
)
intermittent_session = intermittent_created["result"]
intermittent_authorized = store.authorize_session(
    "v2503.2:intermittent-authorize",
    session_id=intermittent_session["session_id"],
    session_digest=intermittent_session["session_digest"],
    public_query_confirmed=True,
)
intermittent_run = store.execute_session(
    "v2503.2:intermittent-execute",
    session_id=intermittent_session["session_id"],
    authorization_digest=intermittent_authorized["result"]["authorization_digest"],
    adapter=intermittent_adapter,
)
require(intermittent_run["ok"], "one_rejected_search_does_not_abort_research_session")
require(intermittent_run["result"]["session"]["source_failure_count"] == 1, "rejected_search_is_counted_as_bounded_source_failure")
require(intermittent_run["result"]["report"]["status"] == "research_report_ready", "one_rejected_matrix_search_is_retried_without_discarding_completed_research")
require(intermittent_run["result"]["report"]["candidate_research_matrix_complete"], "successful_retry_completes_the_candidate_evidence_matrix")
require(intermittent_run["result"]["report"]["candidate_follow_up_completed_query_count"] == 12, "retry_preserves_all_twelve_distinct_matrix_cells")

sanitized = sanitize_report(report)
require(sanitized["research_intelligence_version"] == "v2503.2", "history_preserves_v2503_2_intelligence_version")
require(sanitized["synthesis_provider_request_count"] == 2, "history_preserves_two_request_receipt")
require(sanitized["candidate_follow_up_query_count"] == 4, "history_preserves_follow_up_query_count")
require(len(sanitized["candidate_follow_up_dimensions"]) == 2, "history_preserves_content_free_dimension_names")
require(sanitized["candidate_identity_binding_count"] == 3, "history_preserves_content_free_identity_binding_count")
require(not sanitized["candidate_identity_exposed_in_public_receipt"], "history_excludes_candidate_identity_from_public_receipt")
semantic_sanitized = sanitize_report(semantic_report)
require(semantic_sanitized["candidate_discovery_semantic_repair_used"], "history_preserves_semantic_repair_receipt")
require(semantic_sanitized["candidate_discovery_validation_diagnostics"]["admitted_opportunity_count"] == 3, "history_preserves_content_free_discovery_diagnostics")
require(runtime.is_dir() and not str(runtime).startswith(str(ROOT)), "test_runtime_remains_external_to_source")

print(json.dumps({
    "suite": "v2503.2-candidate-specific-evidence-follow-up",
    "ok": True,
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "network_request_count": 0,
    "provider_request_count": 0,
    "authority_expanded": False,
    "raw_page_content_persisted": False,
}, sort_keys=True))
