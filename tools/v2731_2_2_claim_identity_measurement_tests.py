from __future__ import annotations

"""Measure whether "other wording" was cosmetic or a different proposition.

After grounded_support joined the baseline, two of six corpus runs refused on it
with most of their assessments made for "other wording": science 0 exact / 2 other,
demand 1 exact / 3 other. The model's assessed claim text is not retained anywhere
- grounding keeps only a digest, deliberately - so which kind of difference it was
could not be recovered after the fact.

Grounding now also records a digest of the claim with case, whitespace and
trailing punctuation made irrelevant, and the receipt splits the mismatches:

    normalized_exact_matches   differed only cosmetically -> identity test too literal
    different_claim_matches    stated another proposition  -> identity test is right

Admission does not change. grounded_support and citation completion still key on
the exact digest; this checkpoint only measures.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-2-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import _complete_finding_citations
from bounded_research_history import sanitize_report
from research_claim_assessment import (
    assess_source_claims,
    digest_of_claim,
    digest_of_normalized_claim,
    normalized_claim_text,
)
from research_evidence_policy import REFERENCE_EVIDENCE_POLICY, evaluate_policy
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


SUMMARY = "mRNA vaccines trigger adaptive immune responses like antibody production."

# --- normalization is exactly case, whitespace and trailing punctuation ------

for variant in ("mrna vaccines trigger adaptive immune responses like antibody production.",
                "mRNA vaccines trigger adaptive immune responses like antibody production",
                "  mRNA  vaccines trigger\tadaptive immune responses like antibody production.  ",
                "MRNA VACCINES TRIGGER ADAPTIVE IMMUNE RESPONSES LIKE ANTIBODY PRODUCTION!",
                "mRNA vaccines trigger adaptive immune responses like antibody production.;"):
    require(normalized_claim_text(variant) == normalized_claim_text(SUMMARY), "a_cosmetic_variant_normalizes_equal")
    CHECKS.pop()
    require(digest_of_normalized_claim(variant) == digest_of_normalized_claim(SUMMARY),
            "a_cosmetic_variant_has_the_same_normalized_digest")
    CHECKS.pop()
    require(digest_of_claim(variant) != digest_of_claim(SUMMARY), "a_cosmetic_variant_is_still_a_different_exact_digest")
    CHECKS.pop()
CHECKS.append("every_cosmetic_variant_normalizes_equal_and_stays_exact_different")

for different in ("Excerpts state mRNA vaccines trigger adaptive immune responses like antibody production.",
                  "mRNA vaccines trigger innate immune responses like antibody production.",
                  "Stripe charges 2.9% plus 30 cents per transaction.",
                  ".mRNA vaccines trigger adaptive immune responses like antibody production"):
    require(normalized_claim_text(different) != normalized_claim_text(SUMMARY), "a_changed_proposition_stays_different")
    CHECKS.pop()
CHECKS.append("a_changed_word_prefix_or_leading_punctuation_is_not_normalized_away")
require(normalized_claim_text("Stripe charges $0.30.") != normalized_claim_text("Stripe charges 30 cents."),
        "a_different_unit_is_a_different_claim")
require(normalized_claim_text("Fee is 2.9% plus $0.30.") == "fee is 2.9% plus $0.30",
        "internal_punctuation_survives_normalization")
require(normalized_claim_text(None) == "" and normalized_claim_text("   ") == "", "empty_claims_normalize_to_empty")

# --- grounding emits both digests on a live-shaped call ----------------------

PASSAGE = "Studies show mRNA vaccines trigger adaptive immune responses including antibody production in adults."
citations = [{"citation_id": f"web-{n}", "public_url": f"https://pub{n}.example.org/mrna",
              "source_kind": classify_source_kind(f"https://pub{n}.example.org/mrna")} for n in (1, 2, 3)]
documents = [{"citation_id": f"web-{n}", "excerpt": PASSAGE} for n in (1, 2, 3)]
payload = {
    "findings": [{"title": "mRNA", "summary": SUMMARY, "citation_ids": ["web-1"], "uncertainties": ["x"]}],
    "source_assessments": [
        {"citation_id": "web-1", "claim": SUMMARY, "passage_index": 1, "assessment": "supports"},
        {"citation_id": "web-2", "claim": SUMMARY.lower().rstrip("."), "passage_index": 1, "assessment": "supports"},
        {"citation_id": "web-3", "claim": "mRNA vaccines cause lasting innate immune changes.",
         "passage_index": 1, "assessment": "supports"},
    ],
}
grounded = assess_source_claims(payload, documents=documents, citations=citations)
rows = grounded["assessments"]
require(len(rows) == 3, "all_three_assessments_are_grounded_on_the_observed_passage")
require(all(set(r) >= {"claim_digest", "normalized_claim_digest"} for r in rows),
        "grounding_itself_emits_both_digests")
require(rows[0]["normalized_claim_digest"] == digest_of_normalized_claim(SUMMARY),
        "the_emitted_normalized_digest_is_the_shared_definition")
require("claim" not in json.dumps(rows).replace("claim_digest", "").replace("normalized_claim_digest", ""),
        "no_claim_text_is_retained_by_grounding")

# --- the receipt splits other wording into cosmetic and substantive ----------

verdict = evaluate_policy(
    REFERENCE_EVIDENCE_POLICY,
    finding=payload["findings"][0],
    citations=[{**c, "freshness": "fresh", "relevance_score": 1.0, "publisher_digest": f"pub-{c['citation_id']}"}
               for c in citations],
    objective="Research how mRNA vaccines produce an immune response",
    assessments=rows,
)
require(verdict["exact_digest_matches"] == 1, "the_exact_claim_is_counted_as_exact")
require(verdict["normalized_exact_matches"] == 1, "the_cosmetic_variant_is_counted_as_normalized")
require(verdict["different_claim_matches"] == 1, "the_changed_proposition_is_counted_as_different")
require(verdict["exact_digest_matches"] + verdict["normalized_exact_matches"] + verdict["different_claim_matches"]
        == len(rows), "on_grounding_emitted_rows_the_three_counters_account_for_every_assessment")
require(verdict["claim_matched_assessment_count"] == 1 and verdict["claim_mismatched_assessment_count"] == 2,
        "the_existing_counters_are_unchanged")

# --- admission is not changed by the measurement -----------------------------

require(verdict["grounded_supporting_citation_count"] == 1,
        "only_the_exact_claim_supporter_counts_as_grounded_support")
require(verdict["citation_condition_failures"].get("grounded_support") is None,
        "the_cited_exact_claim_supporter_passes")
cosmetic_only = evaluate_policy(
    REFERENCE_EVIDENCE_POLICY,
    finding={**payload["findings"][0], "citation_ids": ["web-2"]},
    citations=[{**citations[1], "freshness": "fresh", "relevance_score": 1.0, "publisher_digest": "pub-2"}],
    objective="Research how mRNA vaccines produce an immune response",
    assessments=rows,
)
require(cosmetic_only["citation_condition_failures"].get("grounded_support") == 1,
        "a_supporter_matching_only_after_normalization_is_still_not_grounded_support")
run = {"ok": True, "payload": {"findings": [dict(payload["findings"][0])]},
       "source_assessment_summary": grounded}
receipt = _complete_finding_citations(run, offered_ids=["web-1", "web-2", "web-3"])
require(run["payload"]["findings"][0]["citation_ids"] == ["web-1"] and receipt["added_citation_count"] == 0,
        "completion_still_adds_nothing_that_matches_only_after_normalization")

# --- legacy rows without a normalized digest are not guessed at ---------------

legacy = [{k: v for k, v in row.items() if k != "normalized_claim_digest"} for row in rows]
legacy_verdict = evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding=payload["findings"][0],
                                 citations=[{**citations[0], "freshness": "fresh", "relevance_score": 1.0,
                                             "publisher_digest": "pub-1"}],
                                 objective="Research how mRNA vaccines produce an immune response",
                                 assessments=legacy)
require(legacy_verdict["exact_digest_matches"] == 1
        and legacy_verdict["normalized_exact_matches"] == 0 and legacy_verdict["different_claim_matches"] == 0,
        "a_row_without_a_normalized_digest_is_not_classified_as_cosmetic_or_different")

# --- the receipt ---------------------------------------------------------------

projected = sanitize_report({"evidence_policy_evaluation": {**verdict, "secret": SUMMARY}})["evidence_policy_evaluation"]
require((projected["exact_digest_matches"], projected["normalized_exact_matches"], projected["different_claim_matches"])
        == (1, 1, 1), "the_three_counters_are_persisted")
require("secret" not in projected and "mRNA" not in json.dumps(projected), "no_claim_text_reaches_the_receipt")

print(json.dumps({"suite": "v2731.2.2-claim-identity-measurement", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
