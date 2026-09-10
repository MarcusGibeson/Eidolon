from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from bounded_research_reasoning import validate_research_synthesis
from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def candidate_digest(row: dict[str, object]) -> str:
    return digest({
        "title": row["name"],
        "customer": row["customer"],
        "problem": row["problem"],
        "product": row["product"],
    })


CANDIDATES = [
    {
        "name": "Invoice follow-up ledger",
        "customer": "solo service contractors",
        "problem": "overdue invoices require repetitive manual follow-up",
        "product": "tracks invoices and schedules operator-reviewed reminders",
        "zero_budget_rationale": "starts with local storage and manual CSV import",
        "evidence_summary": "Public evidence describes late-payment administration.",
        "uncertainties": ["Willingness to pay remains untested."],
    },
    {
        "name": "Creator sponsorship tracker",
        "customer": "independent content creators",
        "problem": "sponsorship stages and payment dates are scattered",
        "product": "tracks sponsor outreach, deliverables, invoices, and payment dates",
        "zero_budget_rationale": "starts without paid platform integrations",
        "evidence_summary": "Public evidence describes sponsorship workflow tools.",
        "uncertainties": ["Demand evidence remains limited."],
    },
    {
        "name": "Permit deadline reminder",
        "customer": "small licensed trade businesses",
        "problem": "permit and renewal dates are tracked manually",
        "product": "records deadlines and prepares operator-reviewed reminders",
        "zero_budget_rationale": "uses local scheduling before external integrations",
        "evidence_summary": "Public evidence describes recurring permit administration.",
        "uncertainties": ["Jurisdiction coverage remains uncertain."],
    },
]

DIMENSIONS = ("demand", "competition", "implementation_dependencies", "free_tier_feasibility")
initial_citations = []
all_citations = []
for index, candidate in enumerate(CANDIDATES):
    citation_id = f"web-initial-{index}"
    candidate["citation_ids"] = [citation_id]
    row = {
        "citation_id": citation_id,
        "public_url": f"https://initial{index}.example/evidence",
        "quality_score": 0.6,
        "relevance_score": 0.8,
    }
    initial_citations.append(row)
    all_citations.append(row)
    for dimension in DIMENSIONS:
        all_citations.append({
            "citation_id": f"web-{index}-{dimension}",
            "public_url": f"https://candidate{index}.example/{dimension}",
            "source_kind": "primary_data",
            "quality_score": 0.6,
            "relevance_score": 0.8,
            "candidate_digest": candidate_digest(candidate),
            "evidence_dimension": dimension,
        })

discovery_payload = {
    "opportunities": CANDIDATES,
    "recommendation": {},
    "disagreements": [],
    "limitations": [],
}
identities = validate_research_synthesis(
    discovery_payload,
    citations=initial_citations,
    requested_result_count=3,
    require_recommendation=False,
    allow_generic_opportunity_names=True,
)
assert identities["ok"]

checks = 0
for scenario in range(30):
    omitted = scenario % 3
    supported_count = 1 + (scenario % len(DIMENSIONS))
    compact_rows = []
    for index, candidate in enumerate(CANDIDATES[: len(CANDIDATES) - omitted]):
        dimensions = {}
        for dimension in DIMENSIONS[:supported_count]:
            dimensions[dimension] = {
                "summary": f"Bounded {dimension.replace('_', ' ')} evidence was observed.",
                "citation_ids": [f"web-{index}-{dimension}"],
            }
        compact_rows.append({
            "candidate_digest": candidate_digest(candidate),
            "evidence_summary": candidate["evidence_summary"],
            "citation_ids": candidate["citation_ids"],
            "evidence_dimensions": dimensions,
            "uncertainties": candidate["uncertainties"],
        })

    adapter = GovernedPublicWebResearchAdapter(synthesizer=lambda prompt: {})
    adapter._transient_candidate_discovery = discovery_payload
    expanded = adapter._expand_digest_bound_final_payload({
        "opportunities": compact_rows,
        "recommendation": {
            "candidate_digest": candidate_digest(CANDIDATES[0]),
            "conclusion": "It has the clearest bounded starting workflow.",
            "citation_ids": CANDIDATES[0]["citation_ids"],
        },
        "disagreements": ["Observed interest does not establish conversion."],
        "limitations": ["No purchase experiment occurred."],
    })
    assert len(expanded["opportunities"]) == 3
    checks += 1

    complete_matrix = validate_research_synthesis(
        expanded,
        citations=all_citations,
        requested_result_count=3,
        candidate_identities=identities,
        require_candidate_specific_coverage=True,
        candidate_research_matrix_complete=True,
    )
    assert complete_matrix["ok"]
    assert complete_matrix["candidate_identity_binding_count"] == 3
    assert complete_matrix["candidate_research_matrix_complete"]
    assert bool(complete_matrix["missing_evidence"]) == (supported_count < len(DIMENSIONS) or omitted > 0)
    if not complete_matrix["candidate_specific_coverage_complete"]:
        assert "Best current lead for further research" in complete_matrix["rendered_answer"]
    checks += 5

    incomplete_matrix = validate_research_synthesis(
        expanded,
        citations=all_citations,
        requested_result_count=3,
        candidate_identities=identities,
        require_candidate_specific_coverage=True,
        candidate_research_matrix_complete=False,
    )
    assert not incomplete_matrix["ok"]
    assert not incomplete_matrix["rendered_answer"]
    checks += 2

print(json.dumps({
    "suite": "v2503.3-live-failure-replay-stress",
    "ok": True,
    "scenarios": 30,
    "checks": checks,
    "network_request_count": 0,
    "provider_request_count": 0,
    "raw_page_content_persisted": False,
    "authority_expanded": False,
}, sort_keys=True))
