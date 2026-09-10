from __future__ import annotations

"""Synthesis cites from the evidence the policy already admits.

Across the seven-domain corpus the same pattern repeated three times: Eidolon
found admissible evidence, correctly scored it as admissible, and cited something
worse. Coding cited a documentation mirror beside the official docs; product
cited a fee aggregator beside the vendor's own price list; current cited one
blog beside five admissible publishers. Synthesis was handed every observed
source in hash order with nothing to say which the policy would admit.

Selection does not define a second notion of a good source. It runs the shared
policy's own source conditions before synthesis and offers the sources that pass.
Conditions that read the model's assessment of a source cannot run yet, so they
stay with the post-synthesis verdict. When nothing is admissible every source is
offered as before and the verdict refuses afterwards: selection never makes a
source admissible.

Separately, the policy's role checks read only a supplied field, and live
citation rows never carry one - so the promotional-page exclusion passed every
unit test and never fired on a real run. The policy now derives the page-nature
roles itself. These checks use rows shaped exactly like the live ones.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import _select_citable_evidence
from bounded_research_history import sanitize_report
from research_evidence_policy import (
    AUTHORITY_KNOWN_AUTHORITATIVE,
    AUTHORITY_KNOWN_NON_AUTHORITATIVE,
    CURRENT_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    DERIVED_DISQUALIFYING_ROLES,
    REFERENCE_EVIDENCE_POLICY,
    SELECTION_ADMISSIBLE_ONLY,
    SELECTION_NO_ADMISSIBLE_EVIDENCE,
    select_citable_evidence,
    source_authority_state,
)
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def live_row(cid: str, url: str, *, freshness="fresh", relevance=1.0) -> dict:
    """A citation shaped like the live rows the policy receives: no evidence_role."""
    return {"citation_id": cid, "public_url": url, "host": url.split("/")[2],
            "source_kind": classify_source_kind(url), "freshness": freshness,
            "quality_score": 0.5, "relevance_score": relevance,
            "publisher_digest": f"pub-{url.split('/')[2]}", "stance": "unknown"}


# --- the policy sees page-nature roles on live-shaped rows --------------------

require("evidence_role" not in live_row("web-1", "https://example.com/a"),
        "the_fixture_matches_the_live_row_shape")

python_docs = live_row("web-1", "https://docs.python.org/3/library/asyncio-task.html", freshness="unknown")
mdn = live_row("web-2", "https://developer.mozilla.org/en-US/docs/Web/API/AbortController", freshness="unknown")
require(source_authority_state(python_docs) == AUTHORITY_KNOWN_AUTHORITATIVE,
        "official_python_docs_are_not_demoted_by_derived_roles")
require(source_authority_state(mdn) == AUTHORITY_KNOWN_AUTHORITATIVE, "mdn_is_not_demoted_by_derived_roles")

listicle = live_row("web-3", "https://blog.example.com/best-payment-processors-2026")
require(source_authority_state(listicle) == AUTHORITY_KNOWN_NON_AUTHORITATIVE,
        "a_promotional_listicle_is_recognised_on_a_live_row")
definition = live_row("web-4", "https://www.example.com/dictionary/demand")
require(source_authority_state(definition) == AUTHORITY_KNOWN_NON_AUTHORITATIVE,
        "a_dictionary_page_is_recognised_on_a_live_row")
no_url = {"citation_id": "web-5", "public_url": "", "source_kind": "unknown", "relevance_score": 1.0}
require(source_authority_state(no_url) == AUTHORITY_KNOWN_NON_AUTHORITATIVE,
        "a_citation_without_a_public_url_carries_no_authority")

# Deliberately not derived: whether a project's own repository is authoritative
# is a separate decision from recognising what a page is.
repo = live_row("web-6", "https://github.com/python/cpython/blob/main/Lib/asyncio/tasks.py")
require(source_authority_state(repo) == AUTHORITY_KNOWN_AUTHORITATIVE,
        "a_code_repository_is_not_silently_demoted")
require(DERIVED_DISQUALIFYING_ROLES == frozenset({"invalid_public_url", "generic_definition", "promotional_summary"}),
        "only_page_nature_roles_are_derived")

# A role a caller supplies is still honoured as before.
require(source_authority_state({**live_row("web-7", "https://example.org/a"), "evidence_role": "promotional_summary"})
        == AUTHORITY_KNOWN_NON_AUTHORITATIVE, "a_supplied_role_is_still_honoured")

# --- the coding pattern: an inadmissible mirror beside the official docs -----

CODING = "Research Python asyncio task cancellation behavior"
mirror = live_row("web-1", "https://runebook.dev/en/docs/python/library/asyncio-task/task-cancellation",
                  freshness="unknown")
official = live_row("web-2", "https://docs.python.org/3/library/asyncio-task.html", freshness="unknown")
undated_blog = live_row("web-3", "https://someblog.example.net/asyncio-notes", freshness="unknown")
coding = select_citable_evidence(REFERENCE_EVIDENCE_POLICY, citations=[mirror, official, undated_blog],
                                 objective=CODING)
require(coding["selection_mode"] == SELECTION_ADMISSIBLE_ONLY, "admissible_evidence_is_offered_alone")
require(coding["citable_ids"] == ["web-2"], "the_official_docs_are_offered_and_the_mirror_is_not")
require(coding["withheld_citation_count"] == 2, "the_inadmissible_sources_are_withheld")
require(coding["withheld_condition_counts"].get("currency_signal_present") == 2,
        "they_are_withheld_for_the_policys_own_reason")

# --- the product pattern: the vendor's price list beside an aggregator -------

STRIPE = "Research Stripe payment processing fee structure"
aggregator = live_row("web-1", "https://merchantinsiders.com/blogs/stripe-fees/", relevance=1.0)
vendor = live_row("web-2", "https://stripe.com/pricing", relevance=0.8)
product = select_citable_evidence(CURRENT_EVIDENCE_POLICY, citations=[aggregator, vendor], objective=STRIPE)
require(product["citable_ids"][0] == "web-2",
        "the_first_party_price_list_is_offered_first_despite_lower_relevance")
require(set(product["citable_ids"]) == {"web-1", "web-2"},
        "a_source_admissible_aggregator_is_still_offered")
require(product["offered_authority_tiers"].get("primary") == 1,
        "the_objective_stands_in_as_the_provisional_claim_for_first_partyness")

# --- nothing admissible: every source is offered, and nothing is laundered ---

stale = [live_row("web-1", "https://a.example.org/x", freshness="stale"),
         live_row("web-2", "https://b.example.org/y", freshness="stale")]
none = select_citable_evidence(CURRENT_EVIDENCE_POLICY, citations=stale,
                               objective="Research the current state of EU AI Act enforcement")
require(none["selection_mode"] == SELECTION_NO_ADMISSIBLE_EVIDENCE, "no_admissible_evidence_is_reported")
require(none["citable_ids"] == ["web-1", "web-2"], "the_whole_pool_is_offered_when_nothing_is_admissible")
require(none["withheld_citation_count"] == 0, "nothing_is_withheld_when_nothing_is_admissible")

empty = select_citable_evidence(REFERENCE_EVIDENCE_POLICY, citations=[], objective=CODING)
require(empty["citable_ids"] == [] and empty["observed_citation_count"] == 0, "an_empty_pool_is_safe")

# --- assessment-dependent conditions wait for the verdict --------------------

survey = live_row("web-1", "https://researchfirm.example.org/creator-payments-2026", freshness="fresh")
demand = select_citable_evidence(DEMAND_EVIDENCE_POLICY, citations=[survey],
                                 objective="Research creator sponsorship payment delays demand.")
require(demand["citable_ids"] == ["web-1"],
        "a_source_is_not_withheld_for_an_assessment_that_has_not_happened_yet")
require(demand["assessment_conditions_deferred"] == ["evidence_type_admissible", "stance_supports"],
        "the_deferred_conditions_are_named")
require(select_citable_evidence(REFERENCE_EVIDENCE_POLICY, citations=[survey], objective=CODING)
        ["assessment_conditions_deferred"] == [], "a_policy_without_assessment_conditions_defers_none")

# --- the run-side helper never stops a run ------------------------------------

helper = _select_citable_evidence(citations=[mirror, official], currency_requirement="reference", objective=CODING)
require(helper.get("citable_ids") == ["web-2"], "the_run_helper_consumes_the_shared_policy")
require(_select_citable_evidence(citations=[mirror, official], currency_requirement="not-a-requirement",
                                 objective=CODING).get("policy_code") == "baseline",
        "an_unknown_requirement_falls_back_to_the_baseline_policy")
require(isinstance(_select_citable_evidence(citations=None, currency_requirement="", objective=""), dict),
        "a_missing_pool_does_not_raise")

# --- the receipt ---------------------------------------------------------------

projected = sanitize_report({"evidence_policy_evaluation": {
    "policy_code": "reference",
    "source_selection": {**{k: v for k, v in coding.items() if k != "citable_ids"},
                         "secret": "https://runebook.dev/private-url"},
    "would_admit": True, "enforced": False,
}})["evidence_policy_evaluation"]["source_selection"]
require(projected["selection_mode"] == SELECTION_ADMISSIBLE_ONLY, "the_selection_mode_is_persisted")
require(projected["offered_citation_count"] == 1 and projected["withheld_citation_count"] == 2,
        "the_selection_counts_are_persisted")
require(projected["withheld_condition_counts"] == {"currency_signal_present": 2},
        "the_withholding_reasons_are_persisted")
require("citable_ids" not in projected and "secret" not in projected, "no_ids_or_urls_reach_the_receipt")
require("runebook" not in json.dumps(projected), "no_source_identity_reaches_the_receipt")
require(sanitize_report({"evidence_policy_evaluation": {"source_selection": {"selection_mode": "anything"}}})
        ["evidence_policy_evaluation"]["source_selection"]["selection_mode"] == "",
        "an_unknown_selection_mode_is_not_persisted")

print(json.dumps({"suite": "v2731.2.0-source-selection", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
