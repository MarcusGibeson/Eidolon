from __future__ import annotations

"""A finding is judged on the citations it names, not on everything observed.

The seven-domain corpus reported four findings as admissible. Re-scored against
the sources each finding actually cited, all four were refused. The policy had
been applying its conditions to the run's whole observed pool, so a finding
citing one unclassified blog borrowed admission from seven publishers it never
used, and a finding citing a fee aggregator borrowed the vendor's own price list.
The conditions were right; the unit they were applied to was wrong.

The pool is not discarded. It is measured separately as the admissible evidence
that was available, because the gap between the two - admissible evidence in
hand, not cited - is the signal that synthesis ignored good evidence. That is
the measurement a source-selection repair has to start from.

Nothing is enforced. These checks pin the unit of evaluation.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-1-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_history import sanitize_report
from research_evidence_policy import (
    CURRENT_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    REFERENCE_EVIDENCE_POLICY,
    evaluate_policy,
)
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def cite(cid: str, url: str, *, role="independent_analysis", freshness="fresh", relevance=1.0) -> dict:
    return {"citation_id": cid, "canonical_url": url, "public_url": url,
            "source_kind": classify_source_kind(url), "evidence_role": role,
            "freshness": freshness, "freshness_known": freshness != "unknown",
            "fresh_enough": freshness == "fresh", "relevance_score": relevance,
            "publisher_digest": f"pub-{url.split('/')[2]}"}


def finding(summary: str, ids) -> dict:
    return {"title": "T", "summary": summary, "citation_ids": list(ids),
            "uncertainties": ["Bounded evidence."]}


# --- the current-event case: one cited blog, seven publishers in hand --------

EU = "Research the current state of EU AI Act enforcement"
NEGATIVE = "No fine or enforcement decision under the EU AI Act has been publicly confirmed."
blog = cite("web-1", "https://axis-intelligence.com/eu-ai-act-status")
others = [cite(f"web-{n}", f"https://publisher{n}.example.org/eu-ai-act") for n in range(2, 9)]
pool = [blog, *others]

lone_blog = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(NEGATIVE, ["web-1"]),
                            citations=pool, objective=EU,
                            currency_reason="regulatory_status", freshness_window="quarterly")
require(lone_blog["evaluated_citation_count"] == 1, "the_verdict_counts_only_the_cited_source")
require(lone_blog["independent_publisher_count"] == 1, "the_verdict_counts_only_the_cited_publisher")
require(not lone_blog["would_admit"], "one_cited_blog_cannot_borrow_seven_uncited_publishers")
require("corroboration_satisfied" in lone_blog["finding_condition_failures"],
        "the_cited_blog_fails_on_corroboration")

available = lone_blog["available_admissible_evidence"]
require(available["observed_citation_count"] == 8, "the_pool_is_still_measured")
require(available["independent_publisher_count"] == 8, "the_pool_publishers_are_still_counted")
require(available["would_admit"], "the_evidence_to_support_it_was_in_hand")
require(lone_blog["uncited_admissible_citation_count"] == 7, "seven_admissible_sources_went_uncited")
require(lone_blog["admissible_evidence_not_cited"] is True,
        "good_evidence_existed_and_synthesis_did_not_use_it")

# Citing the corroboration it had makes the same finding admissible.
corroborated = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(NEGATIVE, ["web-1", "web-2"]),
                               citations=pool, objective=EU,
                               currency_reason="regulatory_status", freshness_window="quarterly")
require(corroborated["would_admit"], "a_finding_citing_its_corroboration_is_admitted")
require(corroborated["admissible_evidence_not_cited"] is False,
        "an_admitted_finding_is_not_flagged_as_ignoring_evidence")

# --- the product case: an aggregator cited, the vendor in hand ---------------

STRIPE = "Research Stripe payment processing fee structure"
FEE = "Stripe charges 2.9% plus 30 cents per successful US card transaction."
aggregator = cite("web-1", "https://merchantinsiders.com/blogs/stripe-fees/", role="unclassified_public_source")
vendor = cite("web-2", "https://stripe.com/pricing", role="pricing_or_free_tier")

cites_aggregator = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(FEE, ["web-1"]),
                                   citations=[aggregator, vendor], objective=STRIPE,
                                   currency_reason="pricing_or_limits", freshness_window="annual")
require(not cites_aggregator["would_admit"], "an_aggregator_cannot_borrow_the_vendors_price_list")
require(cites_aggregator["admissible_evidence_not_cited"] is True,
        "the_uncited_vendor_page_is_reported_as_available")
require(cites_aggregator["available_admissible_evidence"]["supporting_authority_tier"] == "primary",
        "the_available_evidence_was_primary")

cites_vendor = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(FEE, ["web-2"]),
                               citations=[aggregator, vendor], objective=STRIPE,
                               currency_reason="pricing_or_limits", freshness_window="annual")
require(cites_vendor["would_admit"], "citing_the_vendor_for_its_own_price_is_admitted")
require(cites_vendor["supporting_authority_tier"] == "primary", "and_it_is_admitted_as_primary")

# --- a finding that fails on its own terms is not "ignored evidence" ----------

HISTORY = "Research the causes of the 1929 stock market crash"
concession = finding("Excerpts describe the event as a rapid collapse but do not specify causes.", ["web-1"])
history_pool = [cite("web-1", "https://www.investopedia.com/1929-crash"),
                cite("web-2", "https://history.example.org/1929"),
                cite("web-3", "https://econ.example.net/crash")]
non_answer = evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding=concession, citations=history_pool,
                             objective=HISTORY)
require("answers_objective" in non_answer["finding_condition_failures"], "a_non_answer_is_still_refused")
require(non_answer["available_admissible_evidence"]["would_admit"] is False,
        "no_amount_of_available_evidence_makes_a_non_answer_an_answer")
require(non_answer["admissible_evidence_not_cited"] is False,
        "a_non_answer_is_not_misreported_as_a_source_selection_gap")

# --- what the finding names ---------------------------------------------------

uncited = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                          finding={"title": "T", "summary": "Tides follow the Moon."},
                          citations=history_pool, objective="Research how ocean tides are generated")
require(uncited["cited_citation_ids_supplied"] is False, "a_finding_that_names_nothing_is_reported")
require(uncited["evaluated_citation_count"] == 0, "and_nothing_is_judged_on_its_behalf")
require(not uncited["would_admit"], "a_finding_that_names_no_citation_is_not_admitted")
require(uncited["available_admissible_evidence"]["observed_citation_count"] == 3,
        "the_pool_is_measured_even_when_the_finding_names_nothing")

report_row = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                             finding={"finding": "Tides follow the Moon and Sun.", "citations": ["web-2", "web-3"],
                                      "uncertainties": ["Bounded evidence."]},
                             citations=history_pool, objective="Research how ocean tides are generated")
require(report_row["cited_citation_ids_supplied"] is True, "a_report_row_names_its_citations_too")
require(report_row["evaluated_citation_count"] == 2, "a_report_rows_citations_are_the_unit")

phantom = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                          finding=finding("Tides follow the Moon.", ["web-2", "web-99", "web-2"]),
                          citations=history_pool, objective="Research how ocean tides are generated")
require(phantom["unobserved_cited_citation_count"] == 1, "a_cited_id_that_was_never_observed_is_counted")
require(phantom["evaluated_citation_count"] == 1, "an_unobserved_or_repeated_id_is_never_judged_twice")

# --- coverage diagnostics still describe everything observed -----------------

require(sum(lone_blog["authority_tiers"].values()) == 8, "authority_tiers_still_cover_the_whole_pool")
require(sum(lone_blog["url_classification_reasons"].values()) == 8,
        "classification_coverage_still_covers_the_whole_pool")
require(sum(lone_blog["claim_source_relationships"].values()) == 8,
        "relationships_still_cover_the_whole_pool")

# --- demand keeps its bar under the new unit ---------------------------------

surveys = [cite("web-1", "https://alphapress.org/survey"), cite("web-2", "https://betajournal.net/survey")]
supporting = {"web-1": {"citation_id": "web-1", "model_assessment": "supports", "model_evidence_kind": "survey_result"},
              "web-2": {"citation_id": "web-2", "model_assessment": "supports", "model_evidence_kind": "survey_result"}}
demand_two = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=finding("Creators report late payments.", ["web-1", "web-2"]),
                             citations=surveys, assessments_by_citation=supporting)
require(demand_two["would_admit"], "two_cited_independent_surveys_still_pass_demand")
demand_one = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=finding("Creators report late payments.", ["web-1"]),
                             citations=surveys, assessments_by_citation=supporting)
require(not demand_one["would_admit"], "citing_one_of_two_surveys_does_not_pass_demand")
require(demand_one["admissible_evidence_not_cited"] is True,
        "the_second_survey_is_reported_as_available_and_uncited")

# --- the measurement stays a measurement -------------------------------------

require(lone_blog["enforced"] is False, "the_unit_change_refuses_nothing")
projected = sanitize_report({"evidence_policy_evaluation": {
    **lone_blog,
    "secret_objective": "private objective text that must not be persisted",
}})["evidence_policy_evaluation"]
require(projected["available_admissible_evidence"]["observed_citation_count"] == 8,
        "the_available_evidence_is_persisted")
require(projected["available_admissible_evidence"]["would_admit"] is True,
        "the_available_verdict_is_persisted")
require(projected["uncited_admissible_citation_count"] == 7, "the_uncited_count_is_persisted")
require(projected["admissible_evidence_not_cited"] is True, "the_ignored_evidence_flag_is_persisted")
require(projected["cited_citation_ids_supplied"] is True, "the_citation_declaration_is_persisted")
require(projected["would_admit"] is False, "the_finding_verdict_is_persisted")
require("secret_objective" not in projected, "unlisted_fields_are_not_persisted")
dumped = json.dumps(projected)
require("private objective" not in dumped and "axis-intelligence" not in dumped,
        "no_objective_text_or_source_identity_reaches_the_receipt")

print(json.dumps({"suite": "v2731.1.0-finding-citation-unit", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
