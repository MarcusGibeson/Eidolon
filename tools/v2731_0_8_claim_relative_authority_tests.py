from __future__ import annotations

"""Authority is claim-relative, and the asker's wording narrows a topical window.

Refusing Stripe as a source for Stripe's own posted fees is absurd, and that is
what the policy did: evidence roles named from a URL path - /pricing, /docs,
/plans - sat in the non-authoritative set, so a vendor's own price list was
disqualified while an aggregator writing about it was merely unclassified. That is
the document-form versus publisher-authority confusion the documentation rules
already fixed, repeated in the role classifier.

The fix is not to make vendors globally authoritative. A vendor is the record for
facts it sets - what it charges, what a plan contains, what it still supports -
and no source at all for whether its product is best or what the market wants.
Both statements can appear on the same page, so the standing belongs to the pair
of claim and source, not to the source.

A first party making a claim that is neither - the Python documentation describing
what cancelling a task does - is evaluated normally. Downgrading that case made
python.org promotional for a claim about Python, which is how this suite caught it.

Separately: a topic sets the default horizon and the asker's words may narrow it.
Otherwise "the current state of enforcement" quietly means "anything from the last
year", which is too lawyerly even for software.

Nothing is enforced. These checks pin the relationship model.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-8-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_history import sanitize_report
from bounded_research_reasoning import decompose_research_objective
from research_evidence_policy import (
    ALWAYS_NON_AUTHORITATIVE_ROLES,
    AUTHORITY_KNOWN_AUTHORITATIVE,
    AUTHORITY_KNOWN_NON_AUTHORITATIVE,
    AUTHORITY_UNCLASSIFIED,
    CLAIM_RELATIVE_EVIDENCE_ROLES,
    CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL,
    CLAIM_SOURCE_FIRST_PARTY_OTHER,
    CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL,
    CLAIM_SOURCE_THIRD_PARTY,
    CURRENT_EVIDENCE_POLICY,
    FIRST_PARTY_SETTLED_RISK_FLAGS,
    REFERENCE_EVIDENCE_POLICY,
    TIER_PRIMARY,
    claim_source_relationship,
    evaluate_policy,
    first_party_source,
    objective_terms,
    required_publisher_count,
    source_authority_state,
    source_authority_tier,
)
from research_source_classification import classify_source_kind
from research_web_intelligence_v2100 import FRESHNESS_DAYS


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def cite(url: str, *, role="independent_analysis", cid="web-1", freshness="fresh", publisher=None) -> dict:
    return {"citation_id": cid, "canonical_url": url, "public_url": url,
            "source_kind": classify_source_kind(url), "evidence_role": role,
            "freshness": freshness, "freshness_known": freshness != "unknown",
            "fresh_enough": freshness == "fresh", "relevance_score": 1.0,
            "publisher_digest": publisher or f"pub-{url.split('/')[2]}"}


def finding(summary: str, *, ids=("web-1",)) -> dict:
    return {"title": "T", "summary": summary, "citation_ids": list(ids),
            "uncertainties": ["Bounded evidence."]}


STRIPE = "Research Stripe payment processing fee structure"
STRIPE_TERMS = objective_terms(STRIPE)
POSTED_FEE = "Stripe charges 2.9% plus 30 cents per successful US card transaction."

# --- first party is established structurally, not enumerated -----------------

require(first_party_source(cite("https://stripe.com/pricing"), STRIPE_TERMS),
        "the_objectives_own_subject_identifies_its_first_party")
require(not first_party_source(cite("https://merchantinsiders.com/blogs/stripe-fees/"), STRIPE_TERMS),
        "an_aggregator_writing_about_a_vendor_is_not_the_vendor")
require(first_party_source(cite("https://docs.stripe.com/payments"), STRIPE_TERMS),
        "a_documentation_subdomain_of_the_first_party_is_still_the_first_party")
require(not first_party_source(cite("https://stripe.com/pricing"), ()),
        "without_an_objective_nothing_is_first_party")
for url in ("https://www.example.com/a", "https://blog.example.net/a", "https://news.example.org/a"):
    require(not first_party_source(cite(url), STRIPE_TERMS), "a_surface_label_is_not_an_identity")
    CHECKS.pop()
CHECKS.append("no_surface_label_is_mistaken_for_an_identity")

# --- the same page, two claims, two standings --------------------------------

vendor_price = cite("https://stripe.com/pricing", role="pricing_or_free_tier")
operational = claim_source_relationship(vendor_price, finding(POSTED_FEE), STRIPE_TERMS)
require(operational == CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL, "a_vendor_states_its_own_posted_price")
require(source_authority_state(vendor_price, operational) == AUTHORITY_KNOWN_AUTHORITATIVE,
        "a_first_party_operational_fact_is_authoritative")
require(source_authority_tier(vendor_price, operational) == TIER_PRIMARY,
        "a_first_party_operational_fact_is_primary")

promotional = claim_source_relationship(
    vendor_price, finding("Stripe is the best payment processor for startups."), STRIPE_TERMS)
require(promotional == CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL, "a_vendor_praising_itself_is_promotional")
require(source_authority_state(vendor_price, promotional) == AUTHORITY_KNOWN_NON_AUTHORITATIVE,
        "a_first_party_promotional_claim_carries_no_authority")
for claim in ("Customers prefer Stripe over its competitors.",
              "The market demands this feature.",
              "Stripe is the industry-leading choice."):
    relationship = claim_source_relationship(vendor_price, finding(claim), STRIPE_TERMS)
    require(relationship == CLAIM_SOURCE_FIRST_PARTY_PROMOTIONAL, "an_evaluative_claim_is_promotional")
    CHECKS.pop()
CHECKS.append("every_evaluative_claim_from_a_first_party_is_promotional")

# The anti-promotional boundary is preserved on the very same URL.
require(operational != promotional, "one_page_carries_two_standings")

# --- an ambiguous first-party claim changes nothing --------------------------

PY_OBJECTIVE = "Research Python asyncio task cancellation behavior"
py_docs = cite("https://docs.python.org/3/library/asyncio-task.html", freshness="unknown")
py_terms = objective_terms(PY_OBJECTIVE)
require(first_party_source(py_docs, py_terms), "python_org_is_the_first_party_for_python")
behaviour = claim_source_relationship(
    py_docs, finding("Calling Task.cancel() does not immediately stop the running coroutine."), py_terms)
require(behaviour == CLAIM_SOURCE_FIRST_PARTY_OTHER, "describing_ones_own_behaviour_is_neither")
require(source_authority_tier(py_docs, behaviour) == TIER_PRIMARY,
        "official_documentation_is_not_demoted_by_being_first_party")
require(source_authority_state(py_docs, behaviour) == AUTHORITY_KNOWN_AUTHORITATIVE,
        "an_ambiguous_first_party_claim_is_evaluated_normally")

# --- third parties are unaffected --------------------------------------------

aggregator = cite("https://merchantinsiders.com/blogs/stripe-fees/", role="unclassified_public_source")
third = claim_source_relationship(aggregator, finding(POSTED_FEE), STRIPE_TERMS)
require(third == CLAIM_SOURCE_THIRD_PARTY, "an_aggregator_is_evaluated_as_a_third_party")
require(source_authority_state(aggregator, third) == AUTHORITY_UNCLASSIFIED,
        "an_aggregator_reporting_a_price_is_still_unclassified")

# Roles that are about the page's own nature stay disqualifying for everyone.
for role in sorted(ALWAYS_NON_AUTHORITATIVE_ROLES):
    row = cite("https://stripe.com/pricing", role=role)
    relationship = claim_source_relationship(row, finding(POSTED_FEE), STRIPE_TERMS)
    require(source_authority_state(row, relationship) == AUTHORITY_KNOWN_NON_AUTHORITATIVE,
            "an_always_non_authoritative_role_is_not_rescued_by_first_partyness")
    CHECKS.pop()
CHECKS.append("no_always_non_authoritative_role_is_rescued_by_first_partyness")

require("pricing_or_free_tier" in CLAIM_RELATIVE_EVIDENCE_ROLES,
        "a_path_named_pricing_role_is_claim_relative_not_disqualifying")
require("promotional_summary" in ALWAYS_NON_AUTHORITATIVE_ROLES,
        "a_page_whose_path_says_marketing_stays_disqualified")

# --- corroboration: settled by the first party, or not -----------------------

require(required_publisher_count(TIER_PRIMARY, ("pricing_claim",), "current", True) == 1,
        "a_first_party_settles_its_own_posted_price_alone")
require(required_publisher_count(TIER_PRIMARY, ("availability_claim",), "current", True) == 1,
        "a_first_party_settles_its_own_support_status_alone")
require(required_publisher_count(TIER_PRIMARY, ("pricing_claim",), "current", False) == 2,
        "a_third_party_price_still_needs_corroboration")
for flag in ("negative_claim", "causal_claim", "enforcement_claim", "market_claim"):
    require(required_publisher_count(TIER_PRIMARY, (flag,), "current", True) == 2,
            "a_first_party_does_not_settle_this")
    CHECKS.pop()
CHECKS.append("a_first_party_settles_no_negative_causal_enforcement_or_market_claim")
require(required_publisher_count(TIER_PRIMARY, ("pricing_claim", "negative_claim"), "current", True) == 2,
        "one_unsettled_risk_flag_is_enough_to_require_corroboration")
require(FIRST_PARTY_SETTLED_RISK_FLAGS == frozenset({"pricing_claim", "availability_claim"}),
        "only_facts_a_first_party_sets_are_settled_by_it")

# --- end to end: the case that started this ----------------------------------

vendor_only = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(POSTED_FEE),
                              citations=[vendor_price], objective=STRIPE,
                              currency_reason="pricing_or_limits", freshness_window="annual")
require(vendor_only["admissible_citation_count"] == 1, "the_vendors_own_price_list_is_admissible")
require(vendor_only["supporting_authority_tier"] == TIER_PRIMARY, "it_is_admitted_as_a_primary_source")
require(vendor_only["required_publisher_count"] == 1, "and_it_does_not_need_a_blog_to_agree_with_it")
require(vendor_only["would_admit"], "stripe_is_a_source_for_stripes_posted_fees")
require(vendor_only["claim_source_relationships"].get(CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL) == 1,
        "the_relationship_is_reported")

aggregator_only = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(POSTED_FEE),
                                  citations=[aggregator], objective=STRIPE,
                                  currency_reason="pricing_or_limits", freshness_window="annual")
require(not aggregator_only["would_admit"], "an_aggregator_alone_still_cannot_carry_a_price")
require("corroboration_satisfied" in aggregator_only["finding_condition_failures"],
        "and_it_fails_for_wanting_corroboration")

praise = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                         finding=finding("Stripe is the best payment processor for startups."),
                         citations=[vendor_price], objective=STRIPE)
require(not praise["would_admit"], "a_vendor_cannot_carry_praise_of_itself")
require("source_authority_assessed" in praise["citation_condition_failures"],
        "and_it_fails_on_authority_for_that_claim")

# --- wording narrows a topical window, never widens it -----------------------

def window(objective: str) -> str:
    row = decompose_research_objective(objective, freshness="", budget={"max_queries": 20})
    require(row.get("ok"), "the_objective_decomposes")
    CHECKS.pop()
    return str(row["recommended_freshness_policy"])


require(window("Research the EU AI Act enforcement actions") == "annual",
        "a_topic_sets_the_default_horizon")
require(window("Research the current state of EU AI Act enforcement") == "quarterly",
        "current_state_narrows_a_topical_window")
require(window("Research the latest EU AI Act enforcement actions") == "current",
        "latest_narrows_it_further")
require(window("Research Stripe payment processing fee structure") == "annual",
        "an_unqualified_pricing_question_keeps_the_annual_horizon")
require(window("Research the current Stripe payment processing fee structure") == "quarterly",
        "the_same_question_asked_about_now_narrows")
require(FRESHNESS_DAYS["quarterly"] == 90, "the_quarterly_band_is_ninety_days")
require(FRESHNESS_DAYS["quarterly"] < FRESHNESS_DAYS["annual"] < FRESHNESS_DAYS["slow_changing"],
        "the_bands_are_ordered")

# Wording cannot widen: a reference question stays at the widest horizon.
require(window("Research Python asyncio task cancellation behavior") == "slow_changing",
        "wording_never_widens_a_reference_horizon")
require(window("Research the causes of the 1929 stock market crash") == "slow_changing",
        "a_historical_question_is_untouched_by_topic_or_wording")

# --- the measurement stays a measurement -------------------------------------

require(vendor_only["enforced"] is False, "the_relationship_model_refuses_nothing")
projected = sanitize_report({"evidence_policy_evaluation": {
    "policy_code": "current",
    "claim_source_relationships": {CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL: 1, CLAIM_SOURCE_THIRD_PARTY: 4},
    "would_admit": True, "enforced": False,
    "secret_objective": "private objective text that must not be persisted",
}})["evidence_policy_evaluation"]
require(projected["claim_source_relationships"] == {CLAIM_SOURCE_FIRST_PARTY_OPERATIONAL: 1,
                                                    CLAIM_SOURCE_THIRD_PARTY: 4},
        "the_relationship_counts_are_persisted")
require("secret_objective" not in projected, "unlisted_fields_are_not_persisted")
require("private objective" not in json.dumps(projected), "no_objective_text_reaches_the_receipt")

print(json.dumps({"suite": "v2731.0.8-claim-relative-authority", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
