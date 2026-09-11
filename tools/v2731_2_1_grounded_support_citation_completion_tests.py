from __future__ import annotations

"""A citation must be grounded as supporting its claim, and every grounded supporter is cited.

After source selection, no finding in the seven-domain corpus cited an
inadmissible source - and every finding cited exactly one. The model's own
grounded assessments showed why that mattered in two different ways:

    product   5 grounded "supports", 1 cited
    demand    3 grounded "supports", 1 cited   (its pool met the demand bar)
    history   0 grounded "supports" of 8, 1 cited - and the policy admitted it

grounded_support joins the baseline: a citation counts as supporting evidence only
when an observed passage from it was judged to support this exact claim. Being
authoritative, current and relevant-looking is not enough. Grounding verifies the
passage was offered and appears literally in the observed excerpt; the support
judgement itself stays the model's, and the receipt does not pretend otherwise.

Citation completion then adds every offered source the model grounded as
supporting the finding's exact claim - not every admissible source. That is
completion rather than laundering: the model already examined the source, found
an observed passage and judged it supportive, then left the id off the finding.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-1-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import _complete_finding_citations
from bounded_research_history import sanitize_report
from bounded_research_reasoning import MAX_FINDING_CITATION_IDS
from research_claim_assessment import digest_of_claim, grounded_supporting_citation_ids
from research_evidence_policy import (
    BASELINE_EVIDENCE_POLICY,
    CURRENT_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    REFERENCE_EVIDENCE_POLICY,
    evaluate_policy,
    select_citable_evidence,
)
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


CLAIM = "Stripe charges 2.9% plus 30 cents per successful US card transaction."


def assessed(cid: str, stance: str, claim: str = CLAIM, *, verified: bool = True, kind: str = "unknown") -> dict:
    """An accepted, grounded assessment row as research_claim_assessment emits it."""
    return {"citation_id": cid, "claim_digest": digest_of_claim(claim),
            "passage_digest": hashlib.sha256(f"passage-{cid}".encode()).hexdigest(),
            "model_assessment": stance, "model_evidence_kind": kind,
            "textual_provenance_verified": verified, "semantic_support_verified": False}


def live_row(cid: str, url: str, *, freshness: str = "fresh") -> dict:
    return {"citation_id": cid, "public_url": url, "host": url.split("/")[2],
            "source_kind": classify_source_kind(url), "freshness": freshness,
            "quality_score": 0.5, "relevance_score": 1.0,
            "publisher_digest": f"pub-{url.split('/')[2]}", "stance": "unknown"}


def finding(ids, summary: str = CLAIM) -> dict:
    return {"title": "Stripe fee", "summary": summary, "citation_ids": list(ids),
            "uncertainties": ["Bounded evidence."]}


# --- one definition of "this exact claim" ------------------------------------

require(digest_of_claim(CLAIM) == hashlib.sha256(CLAIM.encode()).hexdigest(),
        "the_claim_digest_is_the_one_grounding_already_used")
require(digest_of_claim(None) == digest_of_claim(""), "a_missing_claim_digests_as_empty")

# --- which citations were grounded as supporting this claim ------------------

rows = [assessed("web-1", "supports"), assessed("web-2", "unclear"), assessed("web-3", "refutes"),
        assessed("web-4", "supports", claim="Stripe is the best processor."),
        assessed("web-5", "supports", verified=False), assessed("web-6", "supports"),
        assessed("web-1", "supports")]
require(grounded_supporting_citation_ids(rows, CLAIM) == ["web-1", "web-6"],
        "only_verified_supports_for_this_exact_claim_count_in_order_without_duplicates")
require(grounded_supporting_citation_ids(rows, CLAIM, offered_ids=["web-6"]) == ["web-6"],
        "a_source_that_was_not_offered_is_never_counted")
require(grounded_supporting_citation_ids(None, CLAIM) == [] and grounded_supporting_citation_ids("x", CLAIM) == [],
        "malformed_assessments_ground_nothing")

# --- grounded_support is part of every policy, and waits for the verdict -----

for policy in (BASELINE_EVIDENCE_POLICY, REFERENCE_EVIDENCE_POLICY, CURRENT_EVIDENCE_POLICY, DEMAND_EVIDENCE_POLICY):
    require("grounded_support" in policy.citation_conditions, f"{policy.policy_code}_requires_grounded_support")
selection = select_citable_evidence(REFERENCE_EVIDENCE_POLICY,
                                    citations=[live_row("web-1", "https://docs.python.org/3/library/asyncio-task.html",
                                                        freshness="unknown")],
                                    objective="Research Python asyncio task cancellation behavior")
require("grounded_support" in selection["assessment_conditions_deferred"],
        "selection_never_withholds_a_source_for_an_assessment_that_has_not_happened")
require(selection["citable_ids"] == ["web-1"], "so_the_source_is_still_offered_to_synthesis")

# --- not judged, judged empty, judged unsupported, judged supported ----------

STRIPE = "Research Stripe payment processing fee structure"
vendor = live_row("web-1", "https://stripe.com/pricing")


def verdict(assessments, ids=("web-1",), citations=(vendor,), summary=CLAIM):
    return evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=finding(ids, summary), citations=list(citations),
                           objective=STRIPE, currency_reason="pricing_or_limits", freshness_window="annual",
                           assessments=assessments)


unjudged = verdict(None)
require(unjudged["grounded_support_judged"] is False, "no_assessment_step_is_reported_as_unjudged")
require("grounded_support" not in unjudged["citation_condition_failures"],
        "an_unjudged_citation_is_not_refused_for_want_of_a_judgement")

empty = verdict([])
require(empty["grounded_support_judged"] is True, "an_empty_grounded_list_is_a_judgement")
require(empty["citation_condition_failures"].get("grounded_support") == 1,
        "a_citation_nothing_grounded_is_not_supporting_evidence")
require(not empty["would_admit"], "so_the_finding_is_not_admitted")

# The history case: eight sources assessed, none supporting, one cited.
HISTORY_CLAIM = "Record 12.9 million shares traded on October 24, 1929."
history_rows = [assessed(f"web-{n}", "unclear", HISTORY_CLAIM) for n in range(1, 9)]
history = evaluate_policy(REFERENCE_EVIDENCE_POLICY,
                          finding=finding(["web-1"], HISTORY_CLAIM),
                          citations=[live_row(f"web-{n}", f"https://history{n}.example.org/1929") for n in range(1, 9)],
                          objective="Research the causes of the 1929 stock market crash",
                          assessments=history_rows)
require(history["citation_condition_failures"].get("grounded_support") == 1,
        "a_citation_the_model_itself_called_unclear_fails_grounded_support")
require(history["claim_matched_assessment_count"] == 8 and history["claim_mismatched_assessment_count"] == 0,
        "the_receipt_shows_it_was_judged_unclear_not_paraphrased")

# A paraphrased claim is told apart from an unsupported one.
paraphrased = verdict([assessed("web-1", "supports", claim="Stripe's US card fee is 2.9% + 30c.")])
require(paraphrased["citation_condition_failures"].get("grounded_support") == 1,
        "support_for_a_different_wording_of_the_claim_does_not_count")
require(paraphrased["claim_mismatched_assessment_count"] == 1 and paraphrased["claim_matched_assessment_count"] == 0,
        "the_receipt_shows_the_mismatch_so_a_sterile_result_can_be_diagnosed")

supported = verdict([assessed("web-1", "supports")])
require("grounded_support" not in supported["citation_condition_failures"],
        "a_citation_grounded_as_supporting_its_claim_passes")
require(supported["grounded_supporting_citation_count"] == 1, "the_grounded_supporter_is_counted")
require(supported["would_admit"], "a_first_party_price_grounded_in_the_vendors_page_is_admitted")

# --- citation completion ------------------------------------------------------

def synthesis(ids, assessments, summary=CLAIM) -> dict:
    return {"ok": True, "payload": {"findings": [finding(ids, summary)], "limitations": ["x"]},
            "source_assessment_summary": {"assessments": assessments}}


product_rows = [assessed(f"web-{n}", "supports") for n in range(1, 6)] + [assessed("web-6", "unclear"),
                                                                            assessed("web-7", "supports", "Other claim.")]
result = synthesis(["web-3"], product_rows)
original_payload = result["payload"]
receipt = _complete_finding_citations(result, offered_ids=[f"web-{n}" for n in range(1, 9)])
completed = result["payload"]["findings"][0]["citation_ids"]
require(completed == ["web-3", "web-1", "web-2", "web-4", "web-5"],
        "every_grounded_supporter_is_cited_after_the_models_own_choice")
require(receipt == {"applied": True, "original_cited_count": 1, "completed_cited_count": 5, "added_citation_count": 4},
        "the_completion_is_counted")
require("web-6" not in completed and "web-7" not in completed,
        "an_unclear_source_and_a_source_supporting_another_claim_are_not_added")
require(result["model_payload"] is original_payload
        and original_payload["findings"][0]["citation_ids"] == ["web-3"],
        "the_models_own_payload_is_kept_unchanged_for_training")

not_offered = synthesis(["web-1"], [assessed("web-1", "supports"), assessed("web-9", "supports")])
_complete_finding_citations(not_offered, offered_ids=["web-1", "web-2"])
require(not_offered["payload"]["findings"][0]["citation_ids"] == ["web-1"],
        "a_source_synthesis_was_not_offered_is_never_added")

nothing = synthesis(["web-1"], [assessed("web-1", "supports"), assessed("web-2", "unclear")])
nothing_payload = nothing["payload"]
nothing_receipt = _complete_finding_citations(nothing, offered_ids=["web-1", "web-2"])
require(nothing_receipt["added_citation_count"] == 0 and nothing["payload"] is nothing_payload
        and "model_payload" not in nothing,
        "an_honest_single_support_finding_is_left_exactly_as_the_model_wrote_it")

many = synthesis(["web-9"], [assessed(f"web-{n}", "supports") for n in range(1, 9)])
_complete_finding_citations(many, offered_ids=[f"web-{n}" for n in range(1, 10)])
many_ids = many["payload"]["findings"][0]["citation_ids"]
require(len(many_ids) == MAX_FINDING_CITATION_IDS and many_ids[0] == "web-9",
        "completion_respects_the_validators_own_limit_and_never_drops_the_models_choice")

two = {"ok": True, "payload": {"findings": [finding(["web-1"]), finding(["web-2"])]},
       "source_assessment_summary": {"assessments": [assessed("web-3", "supports")]}}
require(_complete_finding_citations(two, offered_ids=["web-3"]) == {}, "completion_only_touches_a_single_finding")
require(_complete_finding_citations({"payload": "garbage"}, offered_ids=[]) == {}, "a_malformed_payload_is_left_alone")
require(_complete_finding_citations({}, offered_ids=None) == {}, "a_missing_payload_does_not_raise")

# --- together: the product pattern clears on grounded evidence ----------------

aggregator = live_row("web-1", "https://merchantinsiders.com/blogs/stripe-fees/")
second = live_row("web-2", "https://feesguide.example.org/stripe")
pool = [aggregator, second, live_row("web-3", "https://unrelated.example.net/x")]
grounded = [assessed("web-1", "supports"), assessed("web-2", "supports"), assessed("web-3", "unclear")]
run = synthesis(["web-1"], grounded)
_complete_finding_citations(run, offered_ids=["web-1", "web-2", "web-3"])
after = evaluate_policy(CURRENT_EVIDENCE_POLICY, finding=run["payload"]["findings"][0], citations=pool,
                        objective=STRIPE, currency_reason="pricing_or_limits", freshness_window="annual",
                        assessments=grounded)
require(after["independent_publisher_count"] == 2, "the_completed_finding_cites_both_grounded_publishers")
require(after["would_admit"], "two_grounded_independent_publishers_corroborate_a_price")
require(after["admissible_evidence_not_cited"] is False,
        "admissible_grounded_evidence_is_no_longer_left_uncited")

# --- the receipt ---------------------------------------------------------------

projected = sanitize_report({"evidence_policy_evaluation": {
    **after, "citation_completion": receipt,
    "secret": "Stripe charges 2.9% plus 30 cents",
}})["evidence_policy_evaluation"]
require(projected["citation_completion"] == receipt, "the_completion_counts_are_persisted")
require(projected["grounded_support_judged"] is True and projected["grounded_supporting_citation_count"] == 2,
        "the_grounded_support_counts_are_persisted")
require(projected["claim_matched_assessment_count"] == 3, "the_claim_match_counts_are_persisted")
dumped = json.dumps(projected)
require("secret" not in projected and "2.9%" not in dumped and "merchantinsiders" not in dumped,
        "no_claim_text_or_source_identity_reaches_the_receipt")

print(json.dumps({"suite": "v2731.2.1-grounded-support-citation-completion", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
