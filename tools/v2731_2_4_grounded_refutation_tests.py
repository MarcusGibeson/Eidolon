from __future__ import annotations

"""A finding a grounded source refutes is not presented as uncontested.

The current-event run was admitted on four grounded supporters - completion had
correctly added them - while a fifth source was grounded as refuting the same
exact claim. Nothing in the general policy looked: grounded_support asks whether
the cited sources support the claim, and completion only adds supporters. The
report surfaced no disagreement, and the refuting source was simply absent.

grounded_refutation joins the baseline: any grounded assessment refuting this
exact claim blocks an uncontested verdict. It does not declare the claim false -
supported and refuted at once is a disputed finding - and the report now shows
it: an unresolved disagreement with supporters and refuters in separate lists,
and the refuting source in the report's source index marked stance "refutes".
It is never added to the finding's own citations, where it would read as a fifth
supporter.

Completion is unchanged. It was right to add the four supporters.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-4-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import (
    _complete_finding_citations,
    _evaluate_evidence_policy,
    _surface_grounded_refutations,
)
from bounded_research_history import sanitize_report
from research_claim_assessment import (
    assess_source_claims,
    grounded_refuting_citation_ids,
    grounded_supporting_citation_ids,
)
from research_evidence_policy import POLICIES
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


OBJECTIVE = "Research the current state of EU AI Act enforcement"
CLAIM = "EU AI Act enforcement of general-purpose AI rules began on August 2, 2026."
PASSAGE = ("Trackers report that the AI Office began supervising general-purpose AI obligations "
           "in August 2026, while some commentators dispute whether enforcement has actually started.")


def live_row(n: int) -> dict:
    url = f"https://tracker{n}.example.org/eu-ai-act"
    return {"citation_id": f"web-{n}", "public_url": url, "host": url.split("/")[2],
            "source_kind": classify_source_kind(url), "freshness": "fresh", "quality_score": 0.5,
            "relevance_score": 1.0, "stance": "unknown", "publisher_digest": f"{n:064x}"}


POOL = [live_row(n) for n in range(1, 6)]


def ground(stances: dict[str, str], claim_for: dict[str, str] | None = None) -> dict:
    """Assessments grounded by the real grounding step on an observed passage."""
    finding = {"title": "Enforcement start", "summary": CLAIM, "citation_ids": ["web-1"], "uncertainties": ["x"]}
    payload = {"findings": [finding], "source_assessments": [
        {"citation_id": cid, "claim": (claim_for or {}).get(cid, CLAIM), "passage_index": 1, "assessment": stance}
        for cid, stance in stances.items()
    ]}
    summary = assess_source_claims(payload, documents=[{"citation_id": r["citation_id"], "excerpt": PASSAGE}
                                                       for r in POOL], citations=POOL)
    require(summary["grounded_assessment_count"] == len(stances), "every_fixture_assessment_is_really_grounded")
    CHECKS.pop()
    return {"ok": True, "payload": {"findings": [finding], "limitations": ["x"]},
            "source_assessment_summary": summary}


# The regression target from the corpus: 4 grounded supporters + 1 grounded refutation.
REGRESSION = {"web-1": "supports", "web-2": "supports", "web-3": "supports", "web-4": "supports", "web-5": "refutes"}

# --- supporters and refuters share one grounding definition -------------------

run = ground(REGRESSION)
rows = run["source_assessment_summary"]["assessments"]
require(grounded_refuting_citation_ids(rows, CLAIM) == ["web-5"], "the_grounded_refuter_is_identified")
require(grounded_supporting_citation_ids(rows, CLAIM) == ["web-1", "web-2", "web-3", "web-4"],
        "the_grounded_supporters_are_unchanged")
other = ground({"web-1": "supports", "web-5": "refutes"}, claim_for={"web-5": "The AI Act has been repealed."})
require(grounded_refuting_citation_ids(other["source_assessment_summary"]["assessments"], CLAIM) == [],
        "a_refutation_of_a_different_claim_does_not_count")

# --- completion is unchanged: it adds the supporters, never the refuter --------

receipt = _complete_finding_citations(run, offered_ids=[r["citation_id"] for r in POOL])
cited = run["payload"]["findings"][0]["citation_ids"]
require(cited == ["web-1", "web-2", "web-3", "web-4"], "completion_still_adds_the_four_supporters")
require("web-5" not in cited, "completion_never_adds_the_refuting_source")
require(receipt["added_citation_count"] == 3, "completion_counts_are_unchanged")

# --- the policy: ordinary admission is blocked --------------------------------

verdict = _evaluate_evidence_policy(payload=run["payload"], citations=POOL,
                                    assessment_summary=run["source_assessment_summary"],
                                    currency_requirement="current", objective=OBJECTIVE)
require(verdict.get("policy_code") == "current", "the_live_wrapper_returned_a_real_evaluation")
require(verdict["would_admit"] is False, "a_grounded_refutation_blocks_ordinary_admission")
require("grounded_refutation" in verdict["finding_condition_failures"], "the_failure_is_named_grounded_refutation")
require(verdict["grounded_refuting_citation_count"] == 1 and verdict["grounded_supporting_citation_count"] == 4,
        "both_the_supporters_and_the_refuter_are_counted")
require(verdict["independent_publisher_count"] == 4 and "corroboration_satisfied" not in verdict["finding_condition_failures"],
        "the_supporting_citations_are_preserved_and_still_corroborate")
require(verdict["available_admissible_evidence"]["would_admit"] is False
        and verdict["admissible_evidence_not_cited"] is False,
        "a_disputed_finding_is_not_misreported_as_ignored_evidence")

clean = ground({"web-1": "supports", "web-2": "supports"})
_complete_finding_citations(clean, offered_ids=["web-1", "web-2"])
clean_verdict = _evaluate_evidence_policy(payload=clean["payload"], citations=POOL,
                                          assessment_summary=clean["source_assessment_summary"],
                                          currency_requirement="current", objective=OBJECTIVE)
require("grounded_refutation" not in clean_verdict["finding_condition_failures"],
        "an_unrefuted_finding_does_not_fail_grounded_refutation")

unjudged = _evaluate_evidence_policy(payload=run["payload"], citations=POOL, assessment_summary=None,
                                     currency_requirement="current", objective=OBJECTIVE)
require("grounded_refutation" not in unjudged["finding_condition_failures"] and unjudged["grounded_support_judged"] is False,
        "with_no_assessment_step_the_refutation_check_is_reported_unjudged_not_failed")

for policy in POLICIES.values():
    require("grounded_refutation" in policy.finding_conditions, f"{policy.policy_code}_checks_grounded_refutation")

# --- the report: the disagreement is surfaced, the refuter's role preserved ---

conclusion = {
    "reasonable_inferences": [{"claim_code": "rq1", "finding": "Enforcement start: " + CLAIM, "citations": list(cited)}],
    "unresolved_disagreements": [],
    "citations": [dict(row) for row in POOL if row["citation_id"] in cited],
    "citation_count": len(cited),
    "rendered_answer": "Enforcement start: " + CLAIM + " [web-1, web-2, web-3, web-4]",
}
surfaced = _surface_grounded_refutations(conclusion, run, POOL)
require(surfaced == 1, "one_refuting_source_is_surfaced")
disagreement = conclusion["unresolved_disagreements"][-1]
require(disagreement["claim_code"] == "grounded_refutation", "the_disagreement_is_labelled_as_a_grounded_refutation")
require(disagreement["refuting_citations"] == ["web-5"], "the_refuter_is_recorded_as_refuting")
require(disagreement["supporting_citations"] == ["web-1", "web-2", "web-3", "web-4"],
        "the_supporters_it_disputes_are_recorded_beside_it")
require(conclusion["reasonable_inferences"][0]["citations"] == ["web-1", "web-2", "web-3", "web-4"],
        "the_refuter_is_never_added_to_the_findings_own_citations")
index = {row["citation_id"]: row for row in conclusion["citations"]}
require(index["web-5"]["stance"] == "refutes", "the_refuter_is_inspectable_and_marked_as_contradicting")
require(all(index[cid]["stance"] != "refutes" for cid in cited), "no_supporter_is_marked_as_contradicting")
require(conclusion["citation_count"] == 5, "the_source_index_count_includes_the_refuter")
require("Disputed: 1 grounded source(s) contradict this finding [web-5]" in conclusion["rendered_answer"],
        "the_rendered_answer_says_the_finding_is_disputed")

untouched = {"reasonable_inferences": [], "unresolved_disagreements": [], "citations": [], "citation_count": 0,
             "rendered_answer": "x"}
require(_surface_grounded_refutations(untouched, clean, POOL) == 0 and untouched["unresolved_disagreements"] == []
        and untouched["rendered_answer"] == "x", "an_unrefuted_finding_leaves_the_report_untouched")
require(_surface_grounded_refutations({}, {"payload": "garbage"}, POOL) == 0, "a_malformed_input_does_not_raise")

# --- the receipt and the persisted report --------------------------------------

persisted = sanitize_report({
    "unresolved_disagreements": conclusion["unresolved_disagreements"],
    "citations": conclusion["citations"],
    "evidence_policy_evaluation": verdict,
})
row = persisted["unresolved_disagreements"][-1]
require(row["refuting_citations"] == ["web-5"] and row["supporting_citations"] == ["web-1", "web-2", "web-3", "web-4"],
        "the_disagreement_survives_persistence_with_roles_intact")
require(next(c for c in persisted["citations"] if c["citation_id"] == "web-5")["stance"] == "refutes",
        "the_contradicting_stance_survives_persistence")
require(persisted["evidence_policy_evaluation"]["grounded_refuting_citation_count"] == 1,
        "the_refuting_count_is_persisted")

print(json.dumps({"suite": "v2731.2.4-grounded-refutation", "passed": len(CHECKS), "total": len(CHECKS),
                  "ok": True, "checks": CHECKS}))
