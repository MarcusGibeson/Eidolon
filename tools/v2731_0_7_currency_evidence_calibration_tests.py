from __future__ import annotations

"""Currency calibrated by reason, and living documentation recognised as current.

The seven-domain corpus routed a pricing question to "current" correctly and then
rejected seventeen sources out of seventeen on freshness, because "current" meant
thirty days. Nothing about published pricing is reissued monthly. Separating what
a question means from how far back to look was the point of the currency reason;
this checkpoint finishes the job by giving each reason its own window.

The same corpus rejected official Python documentation on the currency layer and
let a mirror of that documentation carry the finding instead. docs.python.org/3/
carries no publication date and no minor version, and neither does MDN or
Microsoft Learn. The repair is not a wider version pattern - that would admit any
URL containing a number and still miss the undated living documentation that
caused the problem. What makes a living document current is that its publisher
maintains it, so the signal requires primary authority. A mirror is
documentation-shaped and maintains nothing.

Nothing is enforced. These checks pin the calibration.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-7-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_history import sanitize_report
from bounded_research_reasoning import (
    CURRENCY_REASON_CURRENT_EVENTS,
    CURRENCY_REASON_DEMAND,
    CURRENCY_REASON_PRICING_OR_LIMITS,
    CURRENCY_REASON_REFERENCE,
    CURRENCY_REASON_REGULATORY_STATUS,
    CURRENCY_REASON_SUPPORT_STATUS,
    WINDOW_FOR_CURRENCY_REASON,
    decompose_research_objective,
)
from research_evidence_policy import (
    CURRENT_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    REFERENCE_EVIDENCE_POLICY,
    authoritative_living_documentation,
    evaluate_policy,
    version_signal_present,
)
from research_source_classification import classify_source_kind
from research_web_intelligence_v2100 import FRESHNESS_DAYS


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def cite(cid: str, url: str, *, role="independent_analysis", freshness="unknown", relevance=1.0,
         publisher=None) -> dict:
    return {"citation_id": cid, "canonical_url": url, "public_url": url,
            "source_kind": classify_source_kind(url), "evidence_role": role,
            "freshness": freshness, "freshness_known": freshness != "unknown",
            "fresh_enough": freshness == "fresh", "relevance_score": relevance,
            "publisher_digest": publisher or f"pub-{url.split('/')[2]}"}


def decomposed(objective: str) -> dict:
    row = decompose_research_objective(objective, freshness="", budget={"max_queries": 20})
    require(row.get("ok"), "the_objective_decomposes")
    CHECKS.pop()
    return row


# --- a reason, not a yes or no -----------------------------------------------

for objective, reason in (
    ("Research Python asyncio task cancellation behavior", CURRENCY_REASON_REFERENCE),
    ("Research how ocean tides are generated", CURRENCY_REASON_REFERENCE),
    ("Research Stripe payment processing fee structure", CURRENCY_REASON_PRICING_OR_LIMITS),
    ("Research the API rate limits for the Widget service", CURRENCY_REASON_PRICING_OR_LIMITS),
    ("Research the current state of EU AI Act enforcement", CURRENCY_REASON_REGULATORY_STATUS),
    ("Research which Ubuntu releases are still supported", CURRENCY_REASON_SUPPORT_STATUS),
    ("Research the current state of Python packaging tooling", CURRENCY_REASON_CURRENT_EVENTS),
    ("Research creator sponsorship payment delays demand.", CURRENCY_REASON_DEMAND),
):
    require(decomposed(objective)["evidence_currency_reason"] == reason,
            "the_objective_names_its_currency_reason")
    CHECKS.pop()
CHECKS.append("every_objective_names_its_currency_reason")

# The window follows the reason. A price and a breaking development both require
# current evidence and move at completely different speeds.
require(WINDOW_FOR_CURRENCY_REASON[CURRENCY_REASON_CURRENT_EVENTS] == "current",
        "current_events_keep_the_news_window")
require(FRESHNESS_DAYS[WINDOW_FOR_CURRENCY_REASON[CURRENCY_REASON_PRICING_OR_LIMITS]] == 365,
        "pricing_looks_back_a_year_not_a_month")
require(FRESHNESS_DAYS[WINDOW_FOR_CURRENCY_REASON[CURRENCY_REASON_REGULATORY_STATUS]] == 365,
        "regulatory_status_looks_back_a_year")
require(FRESHNESS_DAYS[WINDOW_FOR_CURRENCY_REASON[CURRENCY_REASON_SUPPORT_STATUS]] == 180,
        "support_status_follows_a_release_cadence")
require(FRESHNESS_DAYS["annual"] == 365, "the_annual_band_sits_between_news_and_slow_changing")

pricing = decomposed("Research Stripe payment processing fee structure")
require(pricing["evidence_currency_requirement"] == "current", "pricing_still_requires_current_evidence")
require(pricing["recommended_freshness_policy"] == "annual", "pricing_retrieval_looks_back_a_year")
events = decomposed("Research the current state of Python packaging tooling")
require(events["recommended_freshness_policy"] == "current", "current_events_retrieval_stays_tight")
require(decomposed("Research Python asyncio task cancellation behavior")["recommended_freshness_policy"]
        == "slow_changing", "a_reference_question_still_looks_back_furthest")

# Historical framing still overrides a time-sensitive subject.
require(decomposed("Research the causes of the 1929 stock market crash")["evidence_currency_reason"]
        == CURRENCY_REASON_REFERENCE, "a_dated_question_carries_no_currency_reason")

# A caller-stated window still wins, and still cannot invent a requirement.
stated = decompose_research_objective("Research Python asyncio task cancellation behavior",
                                      freshness="breaking", budget={"max_queries": 20})
require(stated["recommended_freshness_policy"] == "breaking", "a_stated_window_is_kept")
require(stated["evidence_currency_requirement"] == "reference",
        "a_stated_window_still_creates_no_currency_requirement")

# --- living documentation is its own currency signal -------------------------

LIVING = ("https://docs.python.org/3/library/asyncio-task.html",
          "https://developer.mozilla.org/en-US/docs/Web/API/AbortController",
          "https://learn.microsoft.com/en-us/dotnet/api/system.threading.cancellationtoken",
          "https://docs.readthedocs.io/en/stable/index.html")
for url in LIVING:
    require(authoritative_living_documentation(cite("web-1", url)), "maintained_first_party_docs_are_current")
    CHECKS.pop()
CHECKS.append("every_maintained_first_party_doc_is_current")

require(not version_signal_present(cite("web-1", LIVING[0])),
        "the_canonical_python_docs_url_carries_no_version_signal")
require(not version_signal_present(cite("web-1", LIVING[1])),
        "a_living_document_carries_no_version_signal")

# A URL pinned to a minor version documents that version, not the current one.
pinned = cite("web-1", "https://docs.python.org/3.14/library/asyncio-task.html")
require(version_signal_present(pinned), "a_pinned_version_is_still_a_version_signal")
require(not authoritative_living_documentation(pinned), "a_pinned_version_is_not_a_living_document")
superseded = cite("web-1", "https://docs.python.org/2.7/library/asyncio-task.html")
require(not authoritative_living_documentation(superseded),
        "an_archived_version_is_not_silently_treated_as_current")

# Mirror safety survives. What makes a living document current is that its
# publisher maintains it, and a mirror maintains nothing.
mirror = cite("web-1", "https://runebook.dev/en/docs/python/library/asyncio-task/task-cancellation")
require(mirror["source_kind"] == "specialist_secondary", "a_docs_mirror_is_still_secondary")
require(not authoritative_living_documentation(mirror), "a_docs_mirror_is_not_a_living_document")
for url in ("https://merchantinsiders.com/blogs/stripe-fees/",
            "https://blog.example.org/2019/asyncio-explained",
            "https://news.example.net/story"):
    require(not authoritative_living_documentation(cite("web-1", url)),
            "an_ordinary_page_is_not_a_living_document")
    CHECKS.pop()
CHECKS.append("no_ordinary_page_is_a_living_document")

# --- the corpus failure this fixes -------------------------------------------

FINDING = {"title": "Task.cancel() does not immediately stop execution",
           "summary": "Calling Task.cancel() does not immediately stop the running coroutine.",
           "citation_ids": ["web-1"], "uncertainties": ["Bounded evidence."]}

undated_official = [cite("web-1", LIVING[0])]
official = evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding=FINDING, citations=undated_official,
                           objective="Research Python asyncio task cancellation behavior",
                           currency_reason=CURRENCY_REASON_REFERENCE, freshness_window="slow_changing")
require(official["admissible_citation_count"] == 1,
        "undated_official_documentation_is_admissible_under_reference")
require("currency_signal_present" not in official["citation_condition_failures"],
        "official_documentation_no_longer_fails_the_currency_layer")
require(official["would_admit"], "one_maintained_official_doc_settles_a_reference_question")
require(official["living_documentation_count"] == 1, "living_documentation_is_counted")

# It holds under the current policy too, where a bare date check would refuse it.
support = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=FINDING, citations=undated_official,
                          objective="Research which Ubuntu releases are still supported",
                          currency_reason=CURRENCY_REASON_SUPPORT_STATUS, freshness_window="versioned")
require("freshness_current" not in support["citation_condition_failures"],
        "maintained_documentation_satisfies_freshness_without_a_date")

mirror_only = evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding=FINDING, citations=[mirror],
                              objective="Research Python asyncio task cancellation behavior",
                              currency_reason=CURRENCY_REASON_REFERENCE, freshness_window="slow_changing")
require("currency_signal_present" in mirror_only["citation_condition_failures"],
        "an_undated_mirror_still_fails_the_currency_layer")
require(mirror_only["living_documentation_count"] == 0, "a_mirror_is_not_counted_as_living")

# Widening the version pattern was the wrong repair and is not what happened.
require(not version_signal_present(cite("web-1", "https://merchantinsiders.com/blogs/stripe-fees/")),
        "a_number_free_ordinary_url_is_still_not_a_version_signal")
require(not version_signal_present(cite("web-1", "https://news.example.net/2024/03/story-12")),
        "a_dated_path_is_not_mistaken_for_a_version_signal")

# --- the measurement stays a measurement -------------------------------------

require(official["enforced"] is False, "the_calibration_refuses_nothing")
require(official["currency_reason"] == CURRENCY_REASON_REFERENCE, "the_currency_reason_is_reported")
require(support["freshness_window"] == "versioned", "the_retrieval_window_is_reported")

projected = sanitize_report({"evidence_policy_evaluation": {
    "policy_code": "current",
    "currency_reason": CURRENCY_REASON_PRICING_OR_LIMITS,
    "freshness_window": "annual",
    "living_documentation_count": 3,
    "version_signal_count": 1,
    "would_admit": False, "enforced": False,
    "secret_objective": "private objective text that must not be persisted",
}})["evidence_policy_evaluation"]
require(projected["currency_reason"] == CURRENCY_REASON_PRICING_OR_LIMITS,
        "the_currency_reason_is_persisted")
require(projected["freshness_window"] == "annual", "the_retrieval_window_is_persisted")
require(projected["living_documentation_count"] == 3, "the_living_documentation_count_is_persisted")
require("secret_objective" not in projected, "unlisted_fields_are_not_persisted")
require("private objective" not in json.dumps(projected), "no_objective_text_reaches_the_receipt")

print(json.dumps({"suite": "v2731.0.7-currency-evidence-calibration", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
