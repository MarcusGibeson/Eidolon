from __future__ import annotations

"""One evidence policy underneath every objective shape, measured before enforced.

Admission rules existed only for demand-shaped objectives. A general research
objective was admitted on a title, a summary and one observed citation, so a
single undated forum post could carry a finding, while a demand claim required two
fresh independent non-promotional survey sources. That is one gate that exists and
one that does not.

The policy is data so a stricter objective composes on top of the baseline rather
than restating it. It is measured in report-only mode first: requiring source
authority at the baseline could take general research from over-permissive to
producing nothing, because most sources are still classified unknown, and that
regression would be invisible until it had already happened.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-4-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_research_history import sanitize_report
from research_evidence_policy import (
    BASELINE_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    EvidencePolicy,
    evaluate_policy,
    policy_for_dimension,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def source(cid: str, *, host: str, kind="reputable_secondary", role="independent_analysis",
           freshness="fresh", relevance=1.0) -> dict:
    return {"citation_id": cid, "host": host, "public_url": f"https://{host}/a",
            "source_kind": kind, "evidence_role": role, "freshness": freshness,
            "freshness_known": freshness != "unknown", "fresh_enough": freshness == "fresh",
            "relevance_score": relevance, "publisher_digest": f"pub-{host}"}


def assessed(cid: str, *, stance="supports", kind="survey_result") -> dict:
    return {"citation_id": cid, "model_assessment": stance, "model_evidence_kind": kind}


FINDING = {"title": "T", "summary": "S", "citation_ids": ["web-1", "web-2"],
           "uncertainties": ["Bounded evidence."]}

# --- the policies compose, they do not restate --------------------------------

require(set(BASELINE_EVIDENCE_POLICY.citation_conditions) <= set(DEMAND_EVIDENCE_POLICY.citation_conditions),
        "demand_inherits_every_baseline_citation_condition")
require(set(BASELINE_EVIDENCE_POLICY.finding_conditions) <= set(DEMAND_EVIDENCE_POLICY.finding_conditions),
        "demand_inherits_every_baseline_finding_condition")
require(len(DEMAND_EVIDENCE_POLICY.citation_conditions) > len(BASELINE_EVIDENCE_POLICY.citation_conditions),
        "demand_is_strictly_tighter_than_the_baseline")
require(len(set(DEMAND_EVIDENCE_POLICY.citation_conditions)) == len(DEMAND_EVIDENCE_POLICY.citation_conditions),
        "composition_does_not_duplicate_a_condition")
require(policy_for_dimension("demand").policy_code == "demand", "a_demand_objective_selects_the_demand_policy")
require(policy_for_dimension("").policy_code == "baseline", "an_unshaped_objective_selects_the_baseline")
require(policy_for_dimension("competition").policy_code == "baseline",
        "an_undecided_dimension_falls_back_to_the_baseline")

# --- the general-research case that prompted this -----------------------------

forum = [source("web-1", host="discuss.example.org", kind="unknown", freshness="stale")]
forum_finding = {"title": "T", "summary": "S", "citation_ids": ["web-1"], "uncertainties": []}
result = evaluate_policy(BASELINE_EVIDENCE_POLICY, finding=forum_finding, citations=forum)
require(not result["would_admit"], "one_undated_unclassified_forum_post_fails_the_baseline")
require("source_authority_known" in result["citation_condition_failures"],
        "an_unclassified_source_fails_on_authority")
require("uncertainty_declared" in result["finding_condition_failures"],
        "a_finding_declaring_no_uncertainty_fails_the_baseline")
require(result["admissible_citation_count"] == 0, "no_citation_survives_that_baseline_evaluation")

# A classified, dated, relevant source with a stated uncertainty passes the baseline.
good = [source("web-1", host="docs.example.org", kind="primary_official")]
solid = evaluate_policy(BASELINE_EVIDENCE_POLICY, finding={**FINDING, "citation_ids": ["web-1"]}, citations=good)
require(solid["would_admit"], "a_classified_dated_relevant_source_passes_the_baseline")
require(not solid["citation_condition_failures"], "a_solid_source_fails_no_baseline_condition")

# --- the baseline alone must not silently satisfy a demand claim --------------

two_fresh = [source("web-1", host="alphapress.org"), source("web-2", host="betajournal.net")]
supporting = {"web-1": assessed("web-1"), "web-2": assessed("web-2")}
demand = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING, citations=two_fresh,
                         assessments_by_citation=supporting)
require(demand["would_admit"], "two_fresh_independent_supporting_surveys_pass_the_demand_policy")

single_publisher = [source("web-1", host="alphapress.org"), source("web-2", host="alphapress.org")]
one_pub = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING, citations=single_publisher,
                          assessments_by_citation=supporting)
require("independent_publishers" in one_pub["finding_condition_failures"],
        "a_single_publisher_still_fails_the_demand_policy")

vendor = {"web-1": assessed("web-1"), "web-2": assessed("web-2", kind="vendor_offering")}
vendor_result = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING, citations=two_fresh,
                                assessments_by_citation=vendor)
require("evidence_type_admissible" in vendor_result["citation_condition_failures"],
        "a_vendor_offering_still_fails_the_demand_evidence_type")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY, finding=FINDING, citations=two_fresh,
                        assessments_by_citation=vendor)["would_admit"],
        "the_baseline_alone_does_not_impose_demand_evidence_types")

stale_pair = [source("web-1", host="alphapress.org"),
              source("web-2", host="betajournal.net", freshness="stale")]
stale_demand = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING, citations=stale_pair,
                               assessments_by_citation=supporting)
require("freshness_current" in stale_demand["citation_condition_failures"],
        "a_stale_source_fails_demand_freshness")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY, finding=FINDING, citations=stale_pair)["would_admit"],
        "a_dated_but_old_source_still_satisfies_the_baseline")

# --- measurement only: this must not refuse anything yet ----------------------

require(result["enforced"] is False and demand["enforced"] is False,
        "every_evaluation_reports_itself_as_unenforced")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY, finding=None, citations=None)["evaluated_citation_count"] == 0,
        "an_empty_evaluation_is_safe")

# The projection keeps the receipt content-free.
projected = sanitize_report({"evidence_policy_evaluation": {
    "policy_code": "demand", "evaluated_citation_count": 7, "admissible_citation_count": 1,
    "citation_condition_failures": {"source_authority_known": 6},
    "finding_condition_failures": ["independent_publishers"],
    "would_admit": False, "enforced": False,
    "secret_claim": "private text that must not be persisted",
}})["evidence_policy_evaluation"]
require(projected["policy_code"] == "demand", "the_policy_code_is_persisted")
require(projected["citation_condition_failures"] == {"source_authority_known": 6},
        "condition_failure_counts_are_persisted")
require(projected["finding_condition_failures"] == ["independent_publishers"],
        "finding_condition_failures_are_persisted")
require("secret_claim" not in projected, "unlisted_fields_are_not_persisted")
require("private text" not in json.dumps(projected), "no_claim_text_reaches_the_receipt")
require(sanitize_report({})["evidence_policy_evaluation"] == {},
        "a_run_without_a_measurement_persists_an_empty_projection")

# A custom tightening composes the same way, so new dimensions need no new plumbing.
custom = BASELINE_EVIDENCE_POLICY.tightened("competition", citation=("freshness_current",))
require(custom.policy_code == "competition", "a_new_policy_keeps_its_own_code")
require("freshness_current" in custom.citation_conditions, "a_new_policy_adds_its_own_condition")
require(set(BASELINE_EVIDENCE_POLICY.citation_conditions) <= set(custom.citation_conditions),
        "a_new_policy_still_inherits_the_baseline")
require("independent_publishers" not in custom.finding_conditions,
        "a_new_policy_does_not_inherit_unrelated_demand_rules")

print(json.dumps({"suite": "v2731.0.4-evidence-policy", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
