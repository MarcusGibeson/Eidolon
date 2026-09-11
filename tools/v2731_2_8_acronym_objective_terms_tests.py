from __future__ import annotations

"""Acronym subjects are objective terms, and short ordinary words still are not.

objective_terms kept only words of four or more characters, so every acronym
fell out along with "the" and "how": "Research how GPS works" had no term for
GPS, "the difference between TCP and UDP" none for either protocol, and "EU AI
Act enforcement" none for EU or AI. answers_objective only fires when a
concession lands on a term the objective asked about, so it could not see those
subjects at all - a finding admitting it could not explain GPS passed as an
answer about GPS.

A lower length limit would have let "the", "and" and "how" in with them. Casing
tells them apart: a short word is a term when it is written in capitals or mixes
letters with digits. This suite pins both halves, and the knock-on decision for
first_party_source: an acronym term never makes a host label the first party,
because .ai, .eu and ai.google would otherwise be granted first-party authority
for every AI or EU objective.

Relevance and standing are checked through the research run's own wrappers with
rows shaped like live citation_rows, as in v2731_2_3.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-8-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import _evaluate_evidence_policy, _select_citable_evidence
from research_claim_assessment import assess_source_claims
from research_evidence_policy import CLAIM_SOURCE_THIRD_PARTY, first_party_source, objective_terms
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


# Keys a live citation row carries when it reaches the policy; see v2731_2_3.
LIVE_ROW_KEYS = {"citation_id", "public_url", "host", "source_kind", "freshness", "quality_score",
                 "relevance_score", "source_digest", "candidate_digest", "evidence_dimension", "stance",
                 "source_identity_digest", "canonical_page_digest", "publisher_digest", "explicit_origin_digest",
                 "attribution_digest", "content_similarity_digest", "content_similarity_confidence",
                 "evidence_producer_signal"}

PASSAGE = "The protocol specification describes how the system behaves and when it was introduced."


def live_row(cid: str, url: str) -> dict:
    row = {key: "" for key in LIVE_ROW_KEYS}
    row.update({"citation_id": cid, "public_url": url, "host": url.split("/")[2],
                "source_kind": classify_source_kind(url), "freshness": "fresh",
                "quality_score": 0.5, "relevance_score": 1.0, "stance": "unknown",
                "publisher_digest": "p" * 63 + cid[-1], "evidence_producer_signal": "none"})
    return row


def run(citations: list[dict], *, summary: str, objective: str, requirement: str = "reference") -> dict:
    """Evaluate exactly as the research run does: grounded assessments, its own wrapper."""
    finding = {"title": "Finding", "summary": summary, "citation_ids": [row["citation_id"] for row in citations],
               "uncertainties": ["Bounded evidence."]}
    payload = {"findings": [finding], "source_assessments": [
        {"citation_id": row["citation_id"], "claim": summary, "passage_index": 1,
         "assessment": "supports", "evidence_kind": "unknown", "dimension": "demand"}
        for row in citations
    ]}
    summary_block = assess_source_claims(
        payload,
        documents=[{"citation_id": row["citation_id"], "excerpt": PASSAGE} for row in citations],
        citations=citations,
        required_dimension="demand",
    )
    require(summary_block.get("grounded_assessment_count") == len(citations),
            "every_witness_assessment_was_really_grounded")
    CHECKS.pop()
    result = _evaluate_evidence_policy(
        payload={"findings": [finding]},
        citations=citations,
        assessment_summary=summary_block,
        currency_requirement=requirement,
        objective=objective,
    )
    # The wrapper swallows exceptions and returns {}, which would read as a pass.
    require(result.get("policy_code"), "the_wrapper_returned_a_real_evaluation")
    CHECKS.pop()
    return result


def answers(objective: str, summary: str) -> bool:
    result = run([blog, blog2], summary=summary, objective=objective)
    require(result["objective_terms_supplied"] is True, "the_relevance_check_ran")
    CHECKS.pop()
    return "answers_objective" not in (result.get("finding_condition_failures") or [])


GPS = "Research how GPS works"
TCP_UDP = "Research the difference between TCP and UDP"
EU_AI_ACT = "Research the current state of EU AI Act enforcement"
HISTORY = "Research the causes of the 1929 stock market crash"
ORDINARY = {"the", "and", "how", "of", "is"}
blog = live_row("web-1", "https://blog.example.com/explained")
blog2 = live_row("web-2", "https://notes.example.net/explained")

# --- acronyms and short identifiers are terms ----------------------------------

require("gps" in objective_terms(GPS), "gps_is_a_term_of_how_gps_works")
require({"tcp", "udp"} <= set(objective_terms(TCP_UDP)), "tcp_and_udp_are_terms_of_their_difference")
require({"eu", "ai"} <= set(objective_terms(EU_AI_ACT)), "eu_and_ai_are_terms_of_eu_ai_act_enforcement")
for objective, term in (("Research how the Stripe API handles retries", "api"),
                        ("Research Amazon S3 storage classes", "s3"),
                        ("Research 5G network slicing", "5g"),
                        ("Research how EC2 instances are billed", "ec2")):
    require(term in objective_terms(objective), "a_short_identifier_is_a_term")
    CHECKS.pop()
CHECKS.append("every_short_identifier_is_a_term")
# "APIs" and "API" are one term, as "causes" and "cause" already were.
require("api" in objective_terms("Research how REST APIs paginate results"), "a_pluralised_acronym_is_the_acronym")

# --- ordinary short words stay out: casing is the signal, not length -----------

for objective in (GPS, TCP_UDP, EU_AI_ACT, "How does GPS work?", "Is the EU AI Act in force?",
                  "What are the causes of the 1929 crash?"):
    require(not ORDINARY & set(objective_terms(objective)), "ordinary_short_words_stay_out")
    CHECKS.pop()
CHECKS.append("ordinary_short_words_stay_out_even_capitalised_at_the_start")
emphatic = objective_terms("Research why TCP does NOT preserve message boundaries")
require("tcp" in emphatic and "not" not in emphatic, "capitals_for_emphasis_are_not_an_acronym")
require("gps" not in objective_terms("research how gps works"), "a_lowercase_short_word_is_not_promoted")
require("3" not in objective_terms("Research Python 3 typing changes"), "a_bare_number_is_not_a_term")
# Shouted text has no lower case, so its capitals say nothing; only a digit does.
shouted = objective_terms("RESEARCH AMAZON S3 PRICING AND HOW IT WORKS")
require("s3" in shouted and not (ORDINARY | {"it"}) & set(shouted), "shouted_text_promotes_only_digit_identifiers")
require(objective_terms("RESEARCH HOW GPS WORKS") == ("work",), "shouted_text_carries_no_casing_signal")

# Words of four or more characters behave exactly as before.
require(objective_terms(HISTORY) == ("cause", "1929", "stock", "market", "crash"), "long_word_terms_are_unchanged")
require(objective_terms("Research Stripe payment processing fee structure")
        == ("stripe", "payment", "processing", "structure"), "a_lowercase_short_word_still_drops_out")

# --- answers_objective can now see an acronym subject --------------------------

# The measurement probe's case: a correct answer that shared no term with its question.
PROBE = ("TCP guarantees ordered delivery through acknowledgements, whereas UDP sends datagrams "
         "without delivery guarantees.")
require({"tcp", "udp"} <= (set(objective_terms(PROBE)) & set(objective_terms(TCP_UDP))),
        "the_probe_finding_shares_its_questions_terms")
require(answers(TCP_UDP, PROBE), "the_probe_finding_answers_its_question")
EU_ANSWER = "The EU AI Act's prohibitions on unacceptable-risk AI systems have applied since 2 February 2025."
require({"eu", "ai"} <= (set(objective_terms(EU_ANSWER)) & set(objective_terms(EU_AI_ACT))),
        "a_correct_eu_ai_act_finding_is_on_topic")
require(answers(EU_AI_ACT, EU_ANSWER), "a_correct_eu_ai_act_finding_answers")

# Each of these passed before: the concession named only the acronym, which was
# no term at all.
for objective, concession in (
    (GPS, "The sources describe satellites in orbit but do not explain how GPS fixes a position."),
    (TCP_UDP, "The excerpts discuss transport protocols but do not specify how UDP differs."),
    (EU_AI_ACT, "The excerpts do not specify which EU AI Act obligations are being enforced."),
    ("Research how REST APIs paginate results", "The excerpts do not describe any API's paging scheme."),
):
    require(not answers(objective, concession), "a_concession_about_the_acronym_subject_is_caught")
    CHECKS.pop()
CHECKS.append("every_concession_about_an_acronym_subject_is_caught")

# A concession about something the question did not ask stays harmless.
require(answers(GPS, "GPS receivers compute position from satellite signal timing; "
                     "the excerpts do not specify receiver prices."),
        "a_concession_about_something_else_is_still_not_a_non_answer")
# The finding is read by the same rule: lower-case "us" is a pronoun, not the US.
require("us" in objective_terms("Research US steel tariff exemptions"), "us_is_a_term_when_written_as_an_acronym")
require(answers("Research US steel tariff exemptions",
                "Section 232 duties on imported steel now stand at 50 percent. "
                "Whether they leave us better off is not established."),
        "a_lowercase_pronoun_is_not_the_acronym_it_spells")

# An objective that names only an acronym used to leave nothing to judge.
require(objective_terms("Research GPS") == ("gps",), "an_acronym_only_objective_has_a_term")
require(answers("Research GPS", "GPS receivers compute position from the timing of satellite signals."),
        "an_acronym_only_objective_is_judged_and_answered")

# --- knock-on: an acronym never makes a host the first party -------------------

eu_terms = objective_terms(EU_AI_ACT)
for url in ("https://spark.ai/blog/eu-ai-act-guide", "https://ai.google/responsibility/eu-ai-act/",
            "https://www.compliance.eu/ai-act-enforcement", "https://ai.example.org/eu"):
    require(not first_party_source({"public_url": url}, eu_terms), "an_ai_or_eu_host_is_not_first_party")
    CHECKS.pop()
CHECKS.append("no_ai_or_eu_host_is_made_first_party_by_an_acronym")
# Deliberate: a real first party named only by an acronym stays unrecognised, as
# before, rather than open short labels to every suffix and subdomain.
require(not first_party_source({"public_url": "https://aws.amazon.com/lambda/pricing/"},
                               objective_terms("Research AWS Lambda pricing")),
        "a_short_host_label_is_not_matched_even_when_it_is_the_publisher")
# A full-length subject still identifies its first party beside an acronym.
require(first_party_source({"public_url": "https://docs.stripe.com/rate-limits"},
                           objective_terms("Research Stripe API rate limits")),
        "a_full_length_subject_still_identifies_its_first_party")

# Through the live wrapper: an operational claim cited to .ai hosts stays third-party.
eu_rows = [live_row("web-1", "https://spark.ai/blog/eu-ai-act-guide"),
           live_row("web-2", "https://ai.google/responsibility/eu-ai-act/")]
fined = run(eu_rows, requirement="current", objective=EU_AI_ACT,
            summary="The EU AI Act sets fines of up to 35 million euros or 7 percent of global turnover.")
require(fined["claim_source_relationships"] == {CLAIM_SOURCE_THIRD_PARTY: 2},
        "an_operational_claim_on_ai_hosts_stays_third_party")
# And selection offers exactly what it offered when the acronyms were invisible.
selection_rows = [*eu_rows, live_row("web-3", "https://digital-strategy.ec.europa.eu/en/policies/ai-act")]
with_acronyms = _select_citable_evidence(citations=selection_rows, currency_requirement="current", objective=EU_AI_ACT)
without = _select_citable_evidence(citations=selection_rows, currency_requirement="current",
                                   objective="Research the current state of enforcement")
require(with_acronyms.get("policy_code") and with_acronyms == without,
        "source_selection_is_unchanged_by_acronym_terms")

print(json.dumps({"suite": "v2731.2.8-acronym-objective-terms", "passed": len(CHECKS), "total": len(CHECKS),
                  "ok": True, "checks": CHECKS}))
