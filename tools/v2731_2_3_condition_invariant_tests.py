from __future__ import annotations

"""Every policy condition must be seen to pass and to fail on live-shaped inputs.

Three times in one day a check came out green because it never actually ran:

    1. claim-risk and relevance read the finding under the wrong keys ("finding"
       instead of the payload's "title"/"summary") and judged an empty string;
    2. the promotional-page exclusion read an evidence_role that live citation rows
       never carry, so it passed every unit test - which supplied the role - and
       never fired on a real run;
    3. evaluate_policy's own local "assessments" overwrote the new parameter, so
       grounded_support would have reported "unjudged" on every live run.

None of the three was a bug in a condition's logic. All three were in the wiring
between live data and the condition. So this suite does not call condition
functions directly. It goes through the real call-site wrapper the research run
uses, with rows shaped exactly like live citation_rows, findings in the synthesis
payload shape, and assessments emitted by the real grounding step - and it
requires every condition any policy uses to be witnessed both passing and failing.
A condition that cannot be made to fail on live-shaped input is not a check.

A registry test fails as soon as a condition is added to a policy without a
witness pair, so the rule outlives this session.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-3-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import _evaluate_evidence_policy
from research_claim_assessment import assess_source_claims
from research_evidence_policy import CITATION_CONDITIONS, FINDING_CONDITIONS, POLICIES
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


# Keys a live citation row carries when it reaches the policy (see the
# citation_rows construction in bounded_autonomous_web_research). Deliberately no
# evidence_role: live rows have none, which is what hid bug 2.
LIVE_ROW_KEYS = {"citation_id", "public_url", "host", "source_kind", "freshness", "quality_score",
                 "relevance_score", "source_digest", "candidate_digest", "evidence_dimension", "stance",
                 "source_identity_digest", "canonical_page_digest", "publisher_digest", "explicit_origin_digest",
                 "attribution_digest", "content_similarity_digest", "content_similarity_confidence"}

PASSAGE = ("A 2026 survey of 1,200 creators found that most respondents reported sponsorship payments "
           "arriving late, often by more than sixty days after delivery.")


def live_row(cid: str, url: str, *, freshness: str = "fresh", relevance: float = 1.0, publisher: str = "") -> dict:
    row = {key: "" for key in LIVE_ROW_KEYS}
    row.update({"citation_id": cid, "public_url": url, "host": url.split("/")[2],
                "source_kind": classify_source_kind(url), "freshness": freshness,
                "quality_score": 0.5, "relevance_score": relevance, "stance": "unknown",
                "publisher_digest": publisher or ("p" * 63 + cid[-1])})
    return row


def run(citations: list[dict], *, summary: str, cited: list[str], requirement: str, objective: str,
        assessments: list[tuple[str, str, str]] | None = (), uncertainties=("Bounded evidence.",),
        claim: str | None = None) -> dict:
    """Evaluate exactly as the research run does, through its own wrapper.

    assessments are (citation_id, stance, evidence_kind) and are grounded by the
    real assess_source_claims against an observed passage. None means no
    assessment step ran at all.
    """
    finding = {"title": "Finding", "summary": summary, "citation_ids": list(cited),
               "uncertainties": list(uncertainties)}
    summary_block = None
    if assessments is not None:
        payload = {"findings": [finding], "source_assessments": [
            {"citation_id": cid, "claim": claim if claim is not None else summary, "passage_index": 1,
             "assessment": stance, "evidence_kind": kind, "dimension": "demand"}
            for cid, stance, kind in assessments
        ]}
        summary_block = assess_source_claims(
            payload,
            documents=[{"citation_id": row["citation_id"], "excerpt": PASSAGE} for row in citations],
            citations=citations,
            required_dimension="demand",
        )
        require(summary_block.get("grounded_assessment_count") == len(assessments),
                "every_witness_assessment_was_really_grounded")
        CHECKS.pop()
    result = _evaluate_evidence_policy(
        payload={"findings": [finding]},
        citations=citations,
        assessment_summary=summary_block,
        currency_requirement=requirement,
        objective=objective,
    )
    # The wrapper swallows exceptions and returns {}. An empty result would make
    # every condition look as though it passed - the exact failure this suite
    # exists to prevent.
    require(result.get("policy_code"), "the_wrapper_returned_a_real_evaluation")
    CHECKS.pop()
    return result


def failed(result: dict, name: str) -> bool:
    return name in (result.get("citation_condition_failures") or {}) or name in (result.get("finding_condition_failures") or [])


GENERAL = "Research how ocean tides are generated"
TIDES = "The Moon's gravity is the main driver of ocean tides on Earth."
HISTORY = "Research the causes of the 1929 stock market crash"
DEMAND = "Research creator sponsorship payment delays demand."
SURVEY_CLAIM = "Most surveyed creators report sponsorship payments arriving more than sixty days late."
docs = live_row("web-1", "https://docs.python.org/3/library/asyncio-task.html", freshness="unknown")
listicle = live_row("web-1", "https://blog.example.com/best-payment-processors-2026")
blog = live_row("web-1", "https://blog.example.com/tides-explained")
blog2 = live_row("web-2", "https://notes.example.net/tides")
survey1 = live_row("web-1", "https://researchfirm.example.org/creator-payments-2026")
survey2 = live_row("web-2", "https://institute.example.net/creator-payments-2026")


def reference(citations, **kw):
    kw.setdefault("summary", TIDES)
    kw.setdefault("cited", [row["citation_id"] for row in citations])
    kw.setdefault("assessments", [(row["citation_id"], "supports", "unknown") for row in citations])
    return run(citations, requirement="reference", objective=GENERAL, **kw)


def current(citations, **kw):
    kw.setdefault("summary", TIDES)
    kw.setdefault("cited", [row["citation_id"] for row in citations])
    kw.setdefault("assessments", [(row["citation_id"], "supports", "unknown") for row in citations])
    return run(citations, requirement="current", objective="Research the current state of tide prediction", **kw)


def demand(citations, *, stance="supports", kind="survey_result", **kw):
    kw.setdefault("summary", SURVEY_CLAIM)
    kw.setdefault("cited", [row["citation_id"] for row in citations])
    kw.setdefault("assessments", [(row["citation_id"], stance, kind) for row in citations])
    return run(citations, requirement="demand_current", objective=DEMAND, **kw)


# Each condition: a live-shaped input on which it passes, and one on which it fails.
WITNESSES = {
    "source_authority_assessed": (lambda: reference([docs]), lambda: reference([listicle])),
    "source_not_promotional": (lambda: reference([blog]), lambda: reference([listicle])),
    "claim_source_fit": (lambda: reference([blog]),
                         lambda: reference([live_row("web-1", "https://blog.example.com/t", relevance=0.1)])),
    "currency_signal_present": (lambda: reference([blog]),
                                lambda: reference([live_row("web-1", "https://blog.example.com/t", freshness="unknown")])),
    "grounded_support": (lambda: reference([blog]),
                         lambda: reference([blog], assessments=[("web-1", "unclear", "unknown")])),
    "freshness_current": (lambda: current([blog]),
                          lambda: current([live_row("web-1", "https://blog.example.com/t", freshness="stale")])),
    "stance_supports": (lambda: demand([survey1, survey2]), lambda: demand([survey1, survey2], stance="unclear")),
    "evidence_type_admissible": (lambda: demand([survey1, survey2]),
                                 lambda: demand([survey1, survey2], kind="vendor_offering")),
    "citation_present": (lambda: reference([blog, blog2]), lambda: reference([blog, blog2], cited=[])),
    "uncertainty_declared_where_warranted": (lambda: reference([docs]),
                                             lambda: reference([docs], uncertainties=())),
    "answers_objective": (
        lambda: run([blog, blog2], summary="Margin buying and a speculative bubble caused the 1929 crash.",
                    cited=["web-1", "web-2"], requirement="reference", objective=HISTORY,
                    assessments=[("web-1", "supports", "unknown"), ("web-2", "supports", "unknown")]),
        lambda: run([blog, blog2], summary="Excerpts describe a rapid collapse but do not specify causes.",
                    cited=["web-1", "web-2"], requirement="reference", objective=HISTORY,
                    assessments=[("web-1", "supports", "unknown"), ("web-2", "supports", "unknown")]),
    ),
    "corroboration_satisfied": (lambda: reference([blog, blog2]), lambda: reference([blog])),
    "independent_publishers": (lambda: demand([survey1, survey2]),
                               lambda: demand([survey1, live_row("web-2", "https://researchfirm.example.org/other",
                                                                 publisher=survey1["publisher_digest"])])),
}

# --- the registry: every condition a policy uses has a witness pair ---------

used = sorted({name for policy in POLICIES.values()
               for name in (*policy.citation_conditions, *policy.finding_conditions)})
missing = [name for name in used if name not in WITNESSES]
require(not missing, f"every_policy_condition_has_a_pass_and_fail_witness{'' if not missing else ':' + ','.join(missing)}")
require(set(WITNESSES) <= set(CITATION_CONDITIONS) | set(FINDING_CONDITIONS),
        "no_witness_names_a_condition_that_does_not_exist")
unused = sorted((set(CITATION_CONDITIONS) | set(FINDING_CONDITIONS)) - set(used))

# --- each condition is seen to pass and to fail through the live path ---------

for name in used:
    passing, failing = WITNESSES[name]
    passed_result, failed_result = passing(), failing()
    require(not failed(passed_result, name), f"{name}_passes_on_its_live_shaped_pass_witness")
    require(failed(failed_result, name), f"{name}_fails_on_its_live_shaped_fail_witness")

# --- the not-judged paths are never what made a condition pass ---------------

grounded_pass = WITNESSES["grounded_support"][0]()
require(grounded_pass["grounded_support_judged"] is True, "grounded_support_passed_because_it_was_judged")
require(grounded_pass["grounded_supporting_citation_count"] == 1, "and_it_found_the_grounded_supporter")
relevance_pass = WITNESSES["answers_objective"][0]()
require(relevance_pass["objective_terms_supplied"] is True, "answers_objective_passed_because_it_was_judged")

# And an input where nothing could be judged is visibly marked, not quietly green.
unjudged = run([blog], summary=TIDES, cited=["web-1"], requirement="reference", objective="", assessments=None)
require(unjudged["grounded_support_judged"] is False and unjudged["objective_terms_supplied"] is False,
        "an_unjudgeable_input_is_reported_as_unjudged")

# --- the three bugs, pinned where they lived -----------------------------------

# 1. The finding is read in the payload shape: a risky claim in "summary" is seen.
risky = reference([blog], summary="The regulator has issued fines under the new rules.")
require("enforcement_claim" in risky["claim_risk_flags"], "a_claim_in_the_payload_summary_is_read_for_risk")
# 2. A live row has no evidence_role, and the promotional exclusion still fires.
require("evidence_role" not in listicle, "the_live_row_fixture_carries_no_evidence_role")
require(failed(WITNESSES["source_not_promotional"][1](), "source_not_promotional"),
        "the_promotional_exclusion_fires_on_a_live_row_without_a_role")
# 3. Assessments reach grounded_support through the real wrapper.
require(WITNESSES["grounded_support"][1]()["grounded_support_judged"] is True,
        "assessments_reach_grounded_support_through_the_live_wrapper")

print(json.dumps({"suite": "v2731.2.3-condition-invariant", "passed": len(CHECKS), "total": len(CHECKS),
                  "ok": True, "unused_conditions": unused, "checks": CHECKS}))
