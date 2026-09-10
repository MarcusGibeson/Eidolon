from __future__ import annotations

"""A refused model-assessed inference must say which rule refused it.

`model_assessed_conclusion` returned a bare `model_assessment_not_admitted` from
nineteen different places, so a run blocked by a single stale citation looked
identical in the receipt to one with no supporting evidence at all. Two of those
rules are all-or-nothing over the model's citation list - one stale or one
ineligible citation denies the whole finding - and deciding whether either is too
strict is impossible while every denial reads the same.

Reasons are fixed codes carrying no claim text, quote or URL.
"""

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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-2-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from research_claim_assessment import model_assessed_conclusion


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


CLAIM = "Creators report sponsorship payment delays."
CLAIM_DIGEST = hashlib.sha256(CLAIM.encode()).hexdigest()


def citation(cid: str, *, host: str, freshness: str = "fresh", stance: str = "unknown") -> dict:
    return {"citation_id": cid, "public_url": f"https://{host}/study", "host": host,
            "source_kind": "reputable_secondary", "freshness": freshness, "stance": stance,
            "relevance_score": 1.0, "quality_score": 0.82,
            "publisher_digest": hashlib.sha256(host.encode()).hexdigest()}


def assessment(cid: str, *, stance: str = "supports", kind: str = "survey_result") -> dict:
    return {"citation_id": cid, "claim_digest": CLAIM_DIGEST, "assessed_dimension": "demand",
            "model_assessment": stance, "model_evidence_kind": kind,
            "passage_digest": hashlib.sha256(cid.encode()).hexdigest(),
            "textual_provenance_verified": True}


def payload(ids: list[str]) -> dict:
    return {"findings": [{"title": "Payment delays", "summary": CLAIM, "citation_ids": ids,
                          "uncertainties": ["Bounded evidence."]}]}


def deny_reason(*, ids, citations, assessments, summary_extra=None, dimension="demand") -> str:
    summary = {"assessments": assessments, "rejected_assessment_counts": {}}
    summary.update(summary_extra or {})
    result = model_assessed_conclusion(payload(ids), assessment_summary=summary,
                                       citations=citations, dimension=dimension)
    require(not result.get("ok"), "the_scenario_under_test_is_actually_refused")
    CHECKS.pop()
    return str(result.get("denial_reason") or "")


TWO_GOOD = [citation("web-1", host="alphapress.org"), citation("web-2", host="betajournal.net")]
TWO_ASSESSED = [assessment("web-1"), assessment("web-2")]

# Each rule must be distinguishable from the others.
require(deny_reason(ids=["web-1", "web-2"], citations=TWO_GOOD, assessments=TWO_ASSESSED,
                    dimension="competition") == "not_a_demand_dimension",
        "a_non_demand_dimension_is_named")

require(deny_reason(ids=["web-1", "web-2"], citations=TWO_GOOD, assessments=TWO_ASSESSED,
                    summary_extra={"rejected_assessment_counts": {"passage_not_observed": 1}})
        == "grounding_rejected_some_assessments",
        "grounding_rejections_are_named")

# --- which rejections are serious enough to refuse the whole inference --------

from research_claim_assessment import BENIGN_ASSESSMENT_REJECTIONS, disqualifying_rejections

require(not disqualifying_rejections({"duplicate_assessment": 3}),
        "a_repeated_assessment_alone_does_not_disqualify")
require(disqualifying_rejections({"passage_not_observed": 1}),
        "a_quote_absent_from_the_excerpt_disqualifies")
require(disqualifying_rejections({"unobserved_citation": 1}),
        "citing_a_source_never_shown_disqualifies")
require(disqualifying_rejections({"passage_quote_mismatch": 1}),
        "a_quote_that_does_not_match_its_passage_disqualifies")
require(disqualifying_rejections({"duplicate_assessment": 2, "passage_not_observed": 1}),
        "a_benign_reason_does_not_mask_a_serious_one")
require(not disqualifying_rejections({}), "no_rejections_disqualify_nothing")
require(not disqualifying_rejections({"duplicate_assessment": 0}),
        "a_zero_count_does_not_disqualify")
require(disqualifying_rejections({"some_future_rejection_code": 1}),
        "an_unrecognised_reason_fails_closed")
require(BENIGN_ASSESSMENT_REJECTIONS == frozenset({"duplicate_assessment"}),
        "only_duplication_is_treated_as_benign")

# End to end: a duplicate no longer refuses an otherwise admissible inference.
admitted = model_assessed_conclusion(
    payload(["web-1", "web-2"]),
    assessment_summary={"assessments": TWO_ASSESSED,
                        "rejected_assessment_counts": {"duplicate_assessment": 1}},
    citations=TWO_GOOD, dimension="demand")
require(admitted.get("ok"), "a_duplicate_no_longer_refuses_an_admissible_inference")
require(admitted.get("reasonable_inferences"), "the_inference_is_returned_as_a_labelled_inference")
require(admitted["reasonable_inferences"][0].get("semantic_support_verified") is False,
        "the_admitted_inference_is_still_not_verified_support")

# ...but a genuine provenance failure still refuses it.
refused = model_assessed_conclusion(
    payload(["web-1", "web-2"]),
    assessment_summary={"assessments": TWO_ASSESSED,
                        "rejected_assessment_counts": {"passage_not_observed": 1}},
    citations=TWO_GOOD, dimension="demand")
require(not refused.get("ok"), "a_fabricated_quote_still_refuses_the_inference")

require(deny_reason(ids=["web-1", "web-9"], citations=TWO_GOOD, assessments=TWO_ASSESSED)
        == "cited_citation_not_observed",
        "an_unobserved_citation_is_named")

require(deny_reason(ids=["web-1", "web-2"], citations=TWO_GOOD,
                    assessments=[assessment("web-1"), assessment("web-2", stance="unclear")])
        == "cited_source_not_assessed_as_supporting",
        "a_non_supporting_cited_source_is_named")

# The two all-or-nothing rules, which is what this whole exercise is about.
stale_pair = [citation("web-1", host="alphapress.org"),
              citation("web-2", host="betajournal.net", freshness="stale")]
require(deny_reason(ids=["web-1", "web-2"], citations=stale_pair, assessments=TWO_ASSESSED)
        == "cited_source_stale_or_conflicting",
        "one_stale_citation_denying_the_finding_is_named")

vendor_pair = [citation("web-1", host="alphapress.org"), citation("web-2", host="betajournal.net")]
require(deny_reason(ids=["web-1", "web-2"], citations=vendor_pair,
                    assessments=[assessment("web-1"), assessment("web-2", kind="vendor_offering")])
        == "cited_source_ineligible",
        "an_ineligible_cited_source_is_named")

same_host = [citation("web-1", host="alphapress.org"), citation("web-2", host="alphapress.org")]
require(deny_reason(ids=["web-1", "web-2"], citations=same_host, assessments=TWO_ASSESSED)
        == "insufficient_distinct_publishers",
        "a_single_publisher_is_named")

# Two subdomains of one site are one publisher, not two independent ones.
subdomains = [citation("web-1", host="news.alphapress.org"), citation("web-2", host="blog.alphapress.org")]
require(deny_reason(ids=["web-1", "web-2"], citations=subdomains, assessments=TWO_ASSESSED)
        == "insufficient_distinct_publishers",
        "subdomains_of_one_site_are_not_two_publishers")

# Reasons must be distinct, not one code reused for everything.
seen = {
    deny_reason(ids=["web-1", "web-2"], citations=TWO_GOOD, assessments=TWO_ASSESSED, dimension="competition"),
    deny_reason(ids=["web-1", "web-9"], citations=TWO_GOOD, assessments=TWO_ASSESSED),
    deny_reason(ids=["web-1", "web-2"], citations=stale_pair, assessments=TWO_ASSESSED),
    deny_reason(ids=["web-1", "web-2"], citations=same_host, assessments=TWO_ASSESSED),
}
require(len(seen) == 4, "distinct_rules_report_distinct_reasons")
require(all(reason and " " not in reason and reason.islower() for reason in seen),
        "reasons_are_fixed_lowercase_codes")

# A refusal still refuses; the reason is diagnostic, not permissive.
result = model_assessed_conclusion(
    payload(["web-1", "web-2"]),
    assessment_summary={"assessments": TWO_ASSESSED, "rejected_assessment_counts": {}},
    citations=stale_pair, dimension="demand")
require(result.get("ok") is False, "a_named_denial_is_still_a_denial")
require(result.get("status") == "model_assessment_not_admitted", "the_refusal_status_is_unchanged")
require("reasonable_inferences" not in result, "a_refusal_admits_no_inference")

print(json.dumps({"suite": "v2731.0.2-model-assessment-denial-reason", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
