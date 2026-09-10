from __future__ import annotations

"""One evidence policy underneath every objective shape, measured before enforced.

Admission rules existed only for demand-shaped objectives. General research was
admitted on a title, a summary and one observed citation, so a single undated
forum post could carry a finding, while a demand claim required two fresh
independent non-promotional survey sources.

Two design corrections came out of measuring the first draft on real corpora.
Requiring a declared publication date universally refused genuine official Python
documentation, which does not become suspect for lacking a timestamp - so currency
is a conditional layer, satisfied for reference material by a documented version.
And a single "unknown" authority conflated "we have not classified this host" with
"this source carries no authority"; the baseline now refuses only the latter.

Nothing is enforced. These checks pin the policy shape and the measurement.
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
    AUTHORITY_KNOWN_AUTHORITATIVE,
    AUTHORITY_KNOWN_NON_AUTHORITATIVE,
    AUTHORITY_UNCLASSIFIED,
    BASELINE_EVIDENCE_POLICY,
    CURRENT_EVIDENCE_POLICY,
    DEMAND_EVIDENCE_POLICY,
    REFERENCE_EVIDENCE_POLICY,
    evaluate_policy,
    policy_for_objective,
    source_authority_state,
    version_signal_present,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def source(cid: str, *, host: str, url=None, kind="reputable_secondary", role="independent_analysis",
           freshness="fresh", relevance=1.0) -> dict:
    return {"citation_id": cid, "host": host, "public_url": url or f"https://{host}/a",
            "source_kind": kind, "evidence_role": role, "freshness": freshness,
            "freshness_known": freshness != "unknown", "fresh_enough": freshness == "fresh",
            "relevance_score": relevance, "publisher_digest": f"pub-{host}"}


def assessed(cid: str, *, stance="supports", kind="survey_result") -> dict:
    return {"citation_id": cid, "model_assessment": stance, "model_evidence_kind": kind}


FINDING = {"title": "T", "summary": "S", "citation_ids": ["web-1", "web-2"],
           "uncertainties": ["Bounded evidence."]}

# --- authority is three-valued -----------------------------------------------

require(source_authority_state(source("a", host="x.org", kind="primary_official")) == AUTHORITY_KNOWN_AUTHORITATIVE,
        "a_classified_source_is_known_authoritative")
require(source_authority_state(source("a", host="x.org", kind="unknown")) == AUTHORITY_UNCLASSIFIED,
        "an_unclassified_host_is_unclassified_not_disqualified")
require(source_authority_state(source("a", host="x.org", kind="reputable_secondary",
                                      role="promotional_summary")) == AUTHORITY_KNOWN_NON_AUTHORITATIVE,
        "a_promotional_source_is_known_non_authoritative")

unclassified = [source("web-1", host="forum.example.org", kind="unknown")]
require(evaluate_policy(BASELINE_EVIDENCE_POLICY,
                        finding={**FINDING, "citation_ids": ["web-1"]},
                        citations=unclassified)["would_admit"],
        "an_unclassified_source_is_not_refused_by_the_baseline")
promotional = [source("web-1", host="vendor.example.com", role="promotional_summary")]
promo = evaluate_policy(BASELINE_EVIDENCE_POLICY, finding={**FINDING, "citation_ids": ["web-1"]},
                        citations=promotional)
require(not promo["would_admit"], "a_promotional_source_is_refused_by_the_baseline")
require("source_authority_assessed" in promo["citation_condition_failures"],
        "a_promotional_source_fails_on_assessed_authority")
require(promo["authority_states"].get(AUTHORITY_KNOWN_NON_AUTHORITATIVE) == 1,
        "authority_states_are_reported_for_measurement")

# --- currency is a layer, not a universal requirement ------------------------

require("currency_signal_present" not in BASELINE_EVIDENCE_POLICY.citation_conditions,
        "the_baseline_does_not_demand_a_publication_date")
for policy in (REFERENCE_EVIDENCE_POLICY, CURRENT_EVIDENCE_POLICY, DEMAND_EVIDENCE_POLICY):
    require("currency_signal_present" in policy.citation_conditions,
            f"the_{policy.policy_code}_policy_applies_the_currency_layer")

# Official documentation, no date, pinned to a version.
docs = [source("web-1", host="docs.python.org", url="https://docs.python.org/3.14/library/asyncio-task.html",
               kind="primary_official", freshness="unknown")]
require(version_signal_present(docs[0]), "a_versioned_documentation_url_is_a_currency_signal")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY, finding={**FINDING, "citation_ids": ["web-1"]},
                        citations=docs)["would_admit"],
        "undated_official_documentation_passes_the_baseline")
require(evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding={**FINDING, "citation_ids": ["web-1"]},
                        citations=docs)["would_admit"],
        "undated_official_documentation_passes_the_reference_policy")
undated_blog = [source("web-1", host="blog.example.org", url="https://blog.example.org/post",
                       kind="reputable_secondary", freshness="unknown")]
require(not evaluate_policy(REFERENCE_EVIDENCE_POLICY, finding={**FINDING, "citation_ids": ["web-1"]},
                            citations=undated_blog)["would_admit"],
        "an_undated_unversioned_page_fails_the_currency_layer")
require(not version_signal_present(undated_blog[0]), "an_ordinary_url_is_not_a_version_signal")

# --- the layers compose ------------------------------------------------------

for policy in (REFERENCE_EVIDENCE_POLICY, CURRENT_EVIDENCE_POLICY, DEMAND_EVIDENCE_POLICY):
    require(set(BASELINE_EVIDENCE_POLICY.citation_conditions) <= set(policy.citation_conditions),
            f"{policy.policy_code}_inherits_every_baseline_citation_condition")
    require(set(BASELINE_EVIDENCE_POLICY.finding_conditions) <= set(policy.finding_conditions),
            f"{policy.policy_code}_inherits_every_baseline_finding_condition")
require(set(CURRENT_EVIDENCE_POLICY.citation_conditions) <= set(DEMAND_EVIDENCE_POLICY.citation_conditions),
        "demand_is_at_least_as_strict_as_current")
require(len(set(DEMAND_EVIDENCE_POLICY.citation_conditions)) == len(DEMAND_EVIDENCE_POLICY.citation_conditions),
        "composition_does_not_duplicate_a_condition")

require(policy_for_objective("demand_current").policy_code == "demand", "a_demand_objective_selects_demand")
require(policy_for_objective("current").policy_code == "current", "a_current_claim_selects_the_currency_layer")
require(policy_for_objective("reference").policy_code == "reference", "reference_material_selects_reference")
require(policy_for_objective("").policy_code == "baseline", "an_unstated_requirement_falls_back_to_the_baseline")
require(policy_for_objective("nonsense").policy_code == "baseline",
        "an_unrecognised_requirement_falls_back_rather_than_guessing")

# --- the invariant the accidental CURRENT run discovered ----------------------
# A default freshness window silently created a semantic currency requirement,
# so a documentation lookup was asked for evidence from the last thirty days.
# Currency must come from the objective's meaning; the window only says how far
# back to look once that is settled.

from bounded_research_reasoning import decompose_research_objective  # noqa: E402

BUDGET = {"max_queries": 20}


def decomposed(objective: str, freshness: str = ""):
    row = decompose_research_objective(objective, freshness=freshness, budget=BUDGET)
    require(row.get("ok"), "the_objective_decomposes")
    CHECKS.pop()
    return row


reference_objective = decomposed("Research Python asyncio task cancellation behavior")
require(reference_objective["evidence_currency_requirement"] == "reference",
        "a_documentation_lookup_requires_reference_not_currency")
require(reference_objective["subquestions"][0]["requires_current_evidence"] is False,
        "a_documentation_lookup_does_not_require_current_evidence")
require(policy_for_objective(reference_objective["evidence_currency_requirement"]).policy_code == "reference",
        "a_documentation_lookup_selects_the_reference_policy")

# The window may be anything; it must not change what the objective requires.
for window in ("current", "breaking", "versioned", "slow_changing", "stable"):
    forced = decomposed("Research Python asyncio task cancellation behavior", freshness=window)
    require(forced["evidence_currency_requirement"] == "reference",
            "a_freshness_window_never_creates_a_currency_requirement")
    CHECKS.pop()
    require(forced["subquestions"][0]["requires_current_evidence"] is False,
            "a_freshness_window_never_sets_requires_current_evidence")
    CHECKS.pop()
CHECKS.append("a_freshness_window_never_creates_a_currency_requirement")
CHECKS.append("a_freshness_window_never_sets_requires_current_evidence")

# Wording that genuinely asks for currency still gets it.
for objective in ("Research the current state of Python packaging tooling",
                  "Research recent changes in TLS certificate policy",
                  "Research the latest Kubernetes release notes"):
    row = decomposed(objective)
    require(row["evidence_currency_requirement"] == "current",
            "currency_wording_requires_current_evidence")
    CHECKS.pop()
CHECKS.append("currency_wording_requires_current_evidence")

# A demand objective's currency need is inherent to its class, not to a window.
demand_objective = decomposed("Research Widget Payment Tracker demand.")
require(demand_objective["evidence_currency_requirement"] == "demand_current",
        "a_demand_objective_requires_demand_currency")
require(policy_for_objective(demand_objective["evidence_currency_requirement"]).policy_code == "demand",
        "a_demand_objective_still_selects_the_demand_policy")
require(demand_objective["subquestions"][0]["requires_current_evidence"] is True,
        "a_demand_objective_still_requires_current_evidence")

# Naming a version is a compatibility answer, not a recency demand.
versioned = decomposed("Research Python 3.14 asyncio TaskGroup behavior")
require(versioned["evidence_currency_requirement"] == "reference",
        "naming_a_version_does_not_make_a_question_time_sensitive")

# --- demand keeps its stricter bar -------------------------------------------

two_fresh = [source("web-1", host="alphapress.org"), source("web-2", host="betajournal.net")]
supporting = {"web-1": assessed("web-1"), "web-2": assessed("web-2")}
require(evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING, citations=two_fresh,
                        assessments_by_citation=supporting)["would_admit"],
        "two_fresh_independent_supporting_surveys_pass_demand")
one_pub = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING,
                          citations=[source("web-1", host="alphapress.org"), source("web-2", host="alphapress.org")],
                          assessments_by_citation=supporting)
require("independent_publishers" in one_pub["finding_condition_failures"],
        "a_single_publisher_still_fails_demand")
vendor = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING, citations=two_fresh,
                         assessments_by_citation={"web-1": assessed("web-1"),
                                                  "web-2": assessed("web-2", kind="vendor_offering")})
require("evidence_type_admissible" in vendor["citation_condition_failures"],
        "a_vendor_offering_still_fails_demand_evidence_type")
stale = evaluate_policy(DEMAND_EVIDENCE_POLICY, finding=FINDING,
                        citations=[source("web-1", host="alphapress.org"),
                                   source("web-2", host="betajournal.net", freshness="stale")],
                        assessments_by_citation=supporting)
require("freshness_current" in stale["citation_condition_failures"], "a_stale_source_fails_demand_freshness")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY, finding=FINDING,
                        citations=[source("web-1", host="alphapress.org"),
                                   source("web-2", host="betajournal.net", freshness="stale")])["would_admit"],
        "a_dated_but_old_source_still_satisfies_the_baseline")

# --- uncertainty is required where warranted ---------------------------------

thin = evaluate_policy(BASELINE_EVIDENCE_POLICY,
                       finding={"title": "T", "summary": "S", "citation_ids": ["web-1"], "uncertainties": []},
                       citations=[source("web-1", host="alphapress.org")])
require("uncertainty_declared_where_warranted" in thin["finding_condition_failures"],
        "a_single_source_finding_must_declare_uncertainty")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY,
                        finding={"title": "T", "summary": "S", "citation_ids": ["web-1", "web-2"],
                                 "uncertainties": []},
                        citations=two_fresh)["would_admit"],
        "a_well_supported_finding_need_not_hedge")

# --- measurement only --------------------------------------------------------

require(thin["enforced"] is False, "every_evaluation_reports_itself_as_unenforced")
require(evaluate_policy(BASELINE_EVIDENCE_POLICY, finding=None, citations=None)["evaluated_citation_count"] == 0,
        "an_empty_evaluation_is_safe")

projected = sanitize_report({"evidence_policy_evaluation": {
    "policy_code": "demand", "evaluated_citation_count": 7, "admissible_citation_count": 1,
    "citation_condition_failures": {"source_authority_assessed": 6},
    "authority_states": {"unclassified": 5, "known_authoritative": 2},
    "version_signal_count": 3,
    "finding_condition_failures": ["independent_publishers"],
    "would_admit": False, "enforced": False,
    "secret_claim": "private text that must not be persisted",
}})["evidence_policy_evaluation"]
require(projected["authority_states"] == {"unclassified": 5, "known_authoritative": 2},
        "authority_states_are_persisted")
require(projected["version_signal_count"] == 3, "version_signal_count_is_persisted")
require("secret_claim" not in projected, "unlisted_fields_are_not_persisted")
require("private text" not in json.dumps(projected), "no_claim_text_reaches_the_receipt")
require(sanitize_report({})["evidence_policy_evaluation"] == {},
        "a_run_without_a_measurement_persists_an_empty_projection")

print(json.dumps({"suite": "v2731.0.4-evidence-policy", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
