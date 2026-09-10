from __future__ import annotations

"""Corroboration by authority, relevance to the objective, currency by subject.

A seven-domain corpus showed one gate too permissive and one gate missing.

Six of seven objectives admitted a finding, every one of them resting on a single
host, because the only condition asking for a second opinion was demand-only.
A blanket two-source rule is the wrong correction: it would make the official
asyncio documentation insufficient to describe asyncio. So corroboration is
decided by the strongest source actually supporting the finding, and by whether
the claim is one where being wrong is expensive - pricing, causation, enforcement,
market behaviour, the absence of something, or anything under a current objective.

The historical run admitted a finding whose own text read "do not specify causes"
for a question about causes. Claim/source fit passes that, because the citations
genuinely support the sentence; what fails is that the sentence is not an answer.
Relevance to the objective needed to be its own condition.

And a pricing question routed to the reference standard with no recency
requirement at all, because currency was inferred from phrasing alone. Nobody
writing "Stripe fee structure" means the 2019 fee structure.

Nothing here is enforced. These checks pin the shape of the three new conditions.
"""

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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-6-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_history import sanitize_report
from bounded_research_reasoning import decompose_research_objective
from research_evidence_policy import (
    BASELINE_EVIDENCE_POLICY,
    CURRENT_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    REFERENCE_EVIDENCE_POLICY,
    SELF_SUFFICIENT_TIERS,
    TIER_COMMUNITY,
    TIER_NON_AUTHORITATIVE,
    TIER_PRIMARY,
    TIER_SPECIALIST,
    TIER_UNCLASSIFIED,
    claim_risk_flags,
    evaluate_policy,
    objective_terms,
    policy_for_objective,
    required_publisher_count,
    source_authority_tier,
    strongest_tier,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def source(cid: str, *, host: str, url=None, kind="reputable_secondary", role="independent_analysis",
           freshness="fresh", relevance=1.0) -> dict:
    return {"citation_id": cid, "host": host, "public_url": url or f"https://{host}/a",
            "source_kind": kind, "evidence_role": role, "freshness": freshness,
            "freshness_known": freshness != "unknown", "fresh_enough": freshness == "fresh",
            "relevance_score": relevance, "publisher_digest": f"pub-{host}"}


def finding(text: str, *, ids=("web-1",), uncertainties=("Bounded evidence.",)) -> dict:
    return {"title": "T", "summary": "S", "finding": text,
            "citation_ids": list(ids), "uncertainties": list(uncertainties)}


# --- authority tiers ---------------------------------------------------------

for kind, tier in (("primary_official", TIER_PRIMARY), ("primary_data", TIER_PRIMARY),
                   ("specialist_secondary", TIER_SPECIALIST), ("reputable_secondary", TIER_SPECIALIST),
                   ("community_experience", TIER_COMMUNITY), ("unknown", TIER_UNCLASSIFIED)):
    require(source_authority_tier(source("a", host="x.org", kind=kind)) == tier,
            f"{kind}_is_tier_{tier}")

require(source_authority_tier(source("a", host="x.org", kind="primary_official",
                                     role="promotional_summary")) == TIER_NON_AUTHORITATIVE,
        "a_promotional_role_outranks_a_classified_kind")
require(strongest_tier([source("a", host="x.org", kind="unknown"),
                        source("b", host="y.org", kind="primary_official")]) == TIER_PRIMARY,
        "the_strongest_source_decides_the_tier_not_the_average")
require(strongest_tier([]) == "none", "no_citations_is_no_tier")
require(TIER_PRIMARY in SELF_SUFFICIENT_TIERS and TIER_SPECIALIST in SELF_SUFFICIENT_TIERS,
        "primary_and_specialist_can_stand_alone")
require(TIER_UNCLASSIFIED not in SELF_SUFFICIENT_TIERS and TIER_COMMUNITY not in SELF_SUFFICIENT_TIERS,
        "unclassified_and_community_cannot_stand_alone")

# --- corroboration follows authority, not bureaucracy ------------------------

docs = [source("web-1", host="docs.python.org",
               url="https://docs.python.org/3.14/library/asyncio-task.html",
               kind="primary_official", freshness="unknown")]
lone_primary = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                               finding=finding("Cancelling a task raises CancelledError inside it."),
                               citations=docs, objective="Research Python asyncio task cancellation behavior")
require(lone_primary["would_admit"], "one_authoritative_primary_source_settles_a_reference_question")
require(lone_primary["required_publisher_count"] == 1, "a_primary_source_needs_no_second_publisher")
require(lone_primary["supporting_authority_tier"] == TIER_PRIMARY, "the_supporting_tier_is_reported")

lone_specialist = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                                  finding=finding("The tides are generated by gravitational gradients."),
                                  citations=[source("web-1", host="oceanref.example.org")],
                                  objective="Research how ocean tides are generated")
require(lone_specialist["would_admit"], "one_specialist_source_settles_a_low_risk_descriptive_claim")

lone_unclassified = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                                    finding=finding("The tides are generated by gravitational gradients."),
                                    citations=[source("web-1", host="blog.example.org", kind="unknown")],
                                    objective="Research how ocean tides are generated")
require(not lone_unclassified["would_admit"], "one_unclassified_source_cannot_settle_anything")
require(lone_unclassified["required_publisher_count"] == 2, "an_unclassified_source_needs_corroboration")
require("corroboration_satisfied" in lone_unclassified["finding_condition_failures"],
        "the_corroboration_failure_is_named")

two_unclassified = evaluate_policy(
    REFERENCE_EVIDENCE_POLICY,
    finding=finding("The tides are generated by gravitational gradients.", ids=("web-1", "web-2")),
    citations=[source("web-1", host="blog.example.org", kind="unknown"),
               source("web-2", host="notes.example.net", kind="unknown")],
    objective="Research how ocean tides are generated")
require(two_unclassified["would_admit"], "two_independent_unclassified_publishers_corroborate")
require(two_unclassified["independent_publisher_count"] == 2, "the_publisher_count_is_reported")

same_publisher = evaluate_policy(
    REFERENCE_EVIDENCE_POLICY,
    finding=finding("The tides are generated by gravitational gradients.", ids=("web-1", "web-2")),
    citations=[source("web-1", host="blog.example.org", kind="unknown"),
               source("web-2", host="blog.example.org", kind="unknown")],
    objective="Research how ocean tides are generated")
require(not same_publisher["would_admit"], "two_pages_from_one_publisher_are_not_corroboration")

# --- higher-risk claims need corroboration whatever backs them ---------------

RISKY = {
    "pricing_claim": "Stripe charges 2.9% plus 30 cents per transaction.",
    "enforcement_claim": "The regulator has issued fines under the new rules.",
    "market_claim": "Its market share among small merchants is growing.",
    "causal_claim": "The collapse was caused by margin lending.",
    "negative_claim": "There are no confirmed penalties to date.",
    "availability_claim": "The v1 endpoint is deprecated.",
}
for code, text in RISKY.items():
    require(code in claim_risk_flags({"finding": text}), f"{code}_is_recognised")
    risky = evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding=finding(text), citations=docs,
                            objective="Research the subject")
    require(risky["required_publisher_count"] == 2, f"{code}_needs_corroboration_despite_a_primary_source")
    require("corroboration_satisfied" in risky["finding_condition_failures"],
            f"{code}_fails_corroboration_on_one_publisher")

require(claim_risk_flags({"finding": "Cancelling a task raises CancelledError inside it."}) == (),
        "an_ordinary_descriptive_claim_carries_no_risk_flag")
require(claim_risk_flags({"finding": "It works this way because the loop yields."}) == (),
        "a_connective_because_is_not_a_causal_assertion")
require(claim_risk_flags({}) == (), "a_finding_with_no_text_carries_no_risk_flag")

# A current objective makes every claim under it time-sensitive.
require(required_publisher_count(TIER_PRIMARY, (), "current") == 2,
        "a_current_objective_requires_corroboration_regardless_of_tier")
require(required_publisher_count(TIER_PRIMARY, (), "demand") == 2,
        "a_demand_objective_requires_corroboration_regardless_of_tier")
require(required_publisher_count(TIER_PRIMARY, (), "reference") == 1,
        "a_reference_objective_trusts_a_primary_source_alone")
current_one = evaluate_policy(CURRENT_EVIDENCE_POLICY,
                              finding=finding("No penalties have been announced."),
                              citations=[source("web-1", host="news.example.org")],
                              objective="Research the current state of enforcement")
require("corroboration_satisfied" in current_one["finding_condition_failures"],
        "a_lone_source_under_a_current_objective_fails_corroboration")

# --- the finding has to answer the question ----------------------------------

HISTORY = "Research the causes of the 1929 stock market crash"
require("cause" in objective_terms(HISTORY), "objective_terms_are_stemmed")
require("research" not in objective_terms(HISTORY), "objective_terms_drop_the_instruction_verb")

non_answer = evaluate_policy(
    REFERENCE_EVIDENCE_POLICY,
    finding=finding("Excerpts describe the event as a rapid collapse but do not specify causes.",
                    ids=("web-1", "web-2")),
    citations=[source("web-1", host="alphapress.org", kind="unknown"),
               source("web-2", host="betajournal.net", kind="unknown")],
    objective=HISTORY)
require(not non_answer["would_admit"], "a_finding_that_concedes_it_has_no_answer_is_refused")
require("answers_objective" in non_answer["finding_condition_failures"],
        "the_relevance_failure_is_named_separately_from_support")
require("claim_source_fit" not in non_answer["citation_condition_failures"],
        "the_citations_still_support_the_sentence_they_annotate")
require(non_answer["objective_terms_supplied"] is True, "the_relevance_check_reports_that_it_ran")

# A concession about something the objective did not ask for is not fatal.
peripheral = evaluate_policy(
    REFERENCE_EVIDENCE_POLICY,
    finding=finding("Cancelling a task raises CancelledError; the docs do not specify the "
                    "exact thread scheduling order."),
    citations=docs,
    objective="Research Python asyncio task cancellation behavior")
require(peripheral["would_admit"], "a_concession_about_an_unasked_detail_is_not_a_non_answer")

for text in ("The sources do not state the causes.",
             "No information about causes was found.",
             "The causes are unspecified in the retrieved excerpts.",
             "The excerpts could not identify any causes."):
    row = evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding=finding(text, ids=("web-1", "web-2")),
                          citations=[source("web-1", host="alphapress.org", kind="unknown"),
                                     source("web-2", host="betajournal.net", kind="unknown")],
                          objective=HISTORY)
    require("answers_objective" in row["finding_condition_failures"], "a_non_answer_phrasing_is_caught")
    CHECKS.pop()
CHECKS.append("every_non_answer_phrasing_is_caught")

blind = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                        finding=finding("The sources do not specify causes.", ids=("web-1", "web-2")),
                        citations=[source("web-1", host="alphapress.org", kind="unknown"),
                                   source("web-2", host="betajournal.net", kind="unknown")])
require(blind["objective_terms_supplied"] is False, "a_missing_objective_is_reported_not_hidden")
require("answers_objective" not in blind["finding_condition_failures"],
        "relevance_is_not_judged_without_an_objective_to_judge_against")

# --- currency is inferred from the subject, not only the phrasing ------------

def currency(objective: str) -> str:
    row = decompose_research_objective(objective, freshness="", budget={"max_queries": 20})
    require(row.get("ok"), "the_objective_decomposes")
    CHECKS.pop()
    return str(row["evidence_currency_requirement"])


for objective in ("Research Stripe payment processing fee structure",
                  "Research the EU AI Act penalties for prohibited systems",
                  "Research which Ubuntu releases are still supported",
                  "Research who is the chief executive of Contoso",
                  "Research the API rate limits for the Widget service"):
    require(currency(objective) == "current", "a_time_sensitive_subject_requires_current_evidence")
    CHECKS.pop()
CHECKS.append("every_time_sensitive_subject_requires_current_evidence")

for objective in ("Research Python asyncio task cancellation behavior",
                  "Research how mRNA vaccines produce an immune response",
                  "Research how ocean tides are generated"):
    require(currency(objective) == "reference", "a_durable_subject_stays_a_reference_question")
    CHECKS.pop()
CHECKS.append("every_durable_subject_stays_a_reference_question")

# Historical framing overrides a time-sensitive-looking subject.
require(currency("Research the causes of the 1929 stock market crash") == "reference",
        "a_dated_question_about_a_market_needs_no_fresh_evidence")
require(currency("Research the history of software licensing costs") == "reference",
        "historical_framing_overrides_a_pricing_subject")
require(currency("Research current software licensing costs") == "current",
        "the_same_pricing_subject_undated_requires_currency")
require(policy_for_objective(currency("Research Stripe payment processing fee structure")).policy_code == "current",
        "a_pricing_objective_selects_the_current_policy")

# --- the measurement stays a measurement -------------------------------------

require(lone_unclassified["enforced"] is False, "the_new_conditions_refuse_nothing")
for policy in (REFERENCE_EVIDENCE_POLICY, CURRENT_EVIDENCE_POLICY, DEMAND_EVIDENCE_POLICY):
    require("corroboration_satisfied" in policy.finding_conditions,
            f"{policy.policy_code}_inherits_corroboration")
    require("answers_objective" in policy.finding_conditions,
            f"{policy.policy_code}_inherits_relevance")
require("independent_publishers" in DEMAND_EVIDENCE_POLICY.finding_conditions,
        "demand_keeps_its_unconditional_publisher_diversity_rule")

projected = sanitize_report({"evidence_policy_evaluation": {
    "policy_code": "current",
    "authority_tiers": {"unclassified": 5, "primary": 1},
    "claim_risk_flags": ["pricing_claim", "negative_claim"],
    "supporting_authority_tier": "unclassified",
    "independent_publisher_count": 1,
    "required_publisher_count": 2,
    "objective_terms_supplied": True,
    "finding_condition_failures": ["corroboration_satisfied"],
    "would_admit": False, "enforced": False,
    "secret_objective": "private objective text that must not be persisted",
}})["evidence_policy_evaluation"]
require(projected["authority_tiers"] == {"unclassified": 5, "primary": 1}, "authority_tiers_are_persisted")
require(projected["claim_risk_flags"] == ["pricing_claim", "negative_claim"], "risk_codes_are_persisted")
require(projected["required_publisher_count"] == 2, "the_corroboration_requirement_is_persisted")
require(projected["independent_publisher_count"] == 1, "the_publisher_count_is_persisted")
require(projected["objective_terms_supplied"] is True, "the_relevance_check_state_is_persisted")
require("secret_objective" not in projected, "unlisted_fields_are_not_persisted")
require("private objective" not in json.dumps(projected), "no_objective_text_reaches_the_receipt")

print(json.dumps({"suite": "v2731.0.6-corroboration-relevance-currency", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
