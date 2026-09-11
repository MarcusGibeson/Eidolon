from __future__ import annotations

"""The refutation path, driven end to end through the real research run.

The live corpus produced a grounded refutation on the current-event objective in
two of three runs, then in none of the next four. Retrieval will not hand over
the regression target on demand, so it cannot be validated live on schedule.
The offline suite already exercises the real grounding, the real policy wrapper,
the real surfacing function and real persistence. What no live run could show,
because it had nothing to surface, is that execute_session actually calls the
surfacing step: "called and found nothing" looks the same as "never called".

This drives BoundedResearchSessionStore.execute_session itself with a fixture
adapter whose synthesis returns the regression target - four grounded
supporters and one grounded refutation of the same exact claim, grounded by the
real assess_source_claims - and checks the report the run actually stores. A
control run, identical except that the fifth assessment is unclear, shows the
call site responds to the refutation and not merely to being reached.

Fixture trap, hit twice today: publishers are identified by registrable domain,
so tracker1.example.org and tracker2.example.org are one publisher. The sources
here use distinct registrable domains, and both runs assert four independent
publishers so a fixture can never quietly collapse the evidence again.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-2-5-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from bounded_autonomous_web_research import BoundedResearchSessionStore
from bounded_research_history import sanitize_report
from research_claim_assessment import assess_source_claims
from research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


OBJECTIVE = "Research the current state of EU AI Act enforcement"
BUDGET = {"max_queries": 3, "max_candidates": 8, "max_observed_pages": 5, "max_total_bytes": 65_536,
          "max_elapsed_seconds": 120, "max_source_failures": 3}
CLAIM = "EU AI Act enforcement of general-purpose AI rules began on August 2, 2026."
PASSAGE = ("Trackers report that the AI Office began supervising general-purpose AI obligations in "
           "August 2026, while some commentators dispute whether enforcement has actually started.")
# Distinct registrable domains: five publishers, not one.
URLS = [f"https://tracker{n}-watch.org/eu-ai-act-enforcement" for n in range(1, 6)]


class RegressionTargetAdapter:
    """Five fresh, relevant, distinct-publisher sources; synthesis returns the target."""

    def __init__(self, fifth_stance: str) -> None:
        self.fifth_stance = fifth_stance
        self.search_calls = 0
        self.synthesize_calls = 0
        self.offered_ids: list[str] = []

    def describe(self) -> dict[str, object]:
        return {"adapter_code": "v2731.2.5-grounded-refutation-fixture", "read_only": True,
                "allowed_methods": ["GET", "HEAD"], "search_supported": True,
                "private_network_allowed": False, "redirect_revalidation_required": True,
                "credentials_allowed": False, "cookies_allowed": False, "uploads_allowed": False,
                "side_effects_allowed": False, "max_bytes_enforced": True, "timeout_enforced": True}

    def search(self, query: str, *, limit: int, timeout_seconds: float) -> list[dict[str, object]]:
        self.search_calls += 1
        if self.search_calls > 1:
            return []
        return [{"url": url, "source_kind": "unknown", "fetched_at": "2026-09-10T00:00:00+00:00"}
                for url in URLS][:limit]

    def observe(self, candidate: dict[str, object], *, plan: dict[str, object], max_bytes: int,
                timeout_seconds: float) -> dict[str, object]:
        url = str(candidate.get("public_url") or candidate.get("url") or "")
        cid = "web-" + hashlib.sha256(url.encode()).hexdigest()[:16]
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION, "receipt_kind": "source_observation",
            "authoritative": True, "terminal": True,
            "operation_digest": digest({"operation": cid}), "terminal_result_digest": digest({"terminal": cid}),
            "source_observed": True, "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"), "stance": "unknown",
            "evidence_digest": digest({"evidence": cid}), "citation_id": cid,
            "source_kind": candidate.get("source_kind", "unknown"), "quality_score": 0.5,
            "freshness_known": True, "fresh_enough": True, "relevance_score": 0.85,
            "observed_bytes": min(512, max_bytes), "public_url": url,
        }
        row["receipt_digest"] = digest(row)
        return row

    def synthesize(self, *, decomposition, citations, **kwargs) -> dict[str, object]:
        self.synthesize_calls += 1
        rows = [dict(row) for row in citations]
        self.offered_ids = [str(row["citation_id"]) for row in rows]
        ordered = sorted(self.offered_ids)
        stances = {cid: "supports" for cid in ordered[:4]}
        stances[ordered[4]] = self.fifth_stance
        finding = {"title": "Enforcement start", "summary": CLAIM, "citation_ids": [ordered[0]],
                   "uncertainties": ["Trackers disagree on whether enforcement has begun."]}
        assessed = {"findings": [finding], "source_assessments": [
            {"citation_id": cid, "claim": CLAIM, "passage_index": 1, "assessment": stance}
            for cid, stance in stances.items()
        ]}
        summary = assess_source_claims(assessed, documents=[{"citation_id": cid, "excerpt": PASSAGE}
                                                            for cid in ordered], citations=rows)
        return {"ok": True, "status": "research_synthesis_ready",
                "payload": {"findings": [finding], "limitations": ["Fixture evidence only."]},
                "source_assessment_summary": summary,
                "provider_contacted": False, "provider_request_count": 0}


def run(fifth_stance: str, label: str) -> tuple[dict, RegressionTargetAdapter]:
    store = BoundedResearchSessionStore(RUNTIME / label)
    adapter = RegressionTargetAdapter(fifth_stance)
    created = store.create_session(f"create-{label}", objective=OBJECTIVE, budget=BUDGET)
    require(created["ok"], f"{label}_session_created")
    session = created["result"]
    authorized = store.authorize_session(f"authorize-{label}", session_id=session["session_id"],
                                         session_digest=session["session_digest"], public_query_confirmed=True)
    require(authorized["ok"], f"{label}_session_authorized")
    executed = store.execute_session(f"execute-{label}", session_id=session["session_id"],
                                     authorization_digest=authorized["result"]["authorization_digest"],
                                     adapter=adapter)
    require(executed["ok"], f"{label}_session_completes")
    return executed["result"]["report"], adapter


# --- the regression target, through the real run -------------------------------

report, adapter = run("refutes", "refuted")
require(adapter.synthesize_calls == 1 and len(adapter.offered_ids) == 5,
        "all_five_admissible_sources_were_offered_to_synthesis")
refuter = sorted(adapter.offered_ids)[4]
supporters = sorted(adapter.offered_ids)[:4]

policy = report.get("evidence_policy_evaluation") or {}
require(policy.get("policy_code") == "current", "the_run_evaluated_the_current_policy")
require(policy.get("independent_publisher_count") == 4, "the_four_supporters_are_four_independent_publishers")
require(policy.get("would_admit") is False, "ordinary_admission_is_false")
require(policy.get("finding_condition_failures") == ["grounded_refutation"],
        "grounded_refutation_is_the_only_reason_admission_fails")
require(not policy.get("citation_condition_failures"), "every_cited_supporter_is_itself_admissible")
require(policy.get("grounded_refuting_citation_count") == 1 and policy.get("grounded_supporting_citation_count") == 4,
        "the_run_counts_four_supporters_and_one_refuter")
require((policy.get("citation_completion") or {}).get("added_citation_count") == 3,
        "completion_still_adds_the_three_uncited_supporters")

inference = (report.get("reasonable_inferences") or [{}])[0]
require(sorted(inference.get("citations") or []) == supporters, "the_supporting_citations_are_preserved")
require(refuter not in (inference.get("citations") or []), "the_refuter_is_not_one_of_the_findings_citations")

disputes = [row for row in report.get("unresolved_disagreements") or [] if row.get("claim_code") == "grounded_refutation"]
require(len(disputes) == 1, "execute_session_surfaced_exactly_one_disagreement")
require(disputes[0].get("refuting_citations") == [refuter], "the_disagreement_names_the_refuter_as_refuting")
require(sorted(disputes[0].get("supporting_citations") or []) == supporters,
        "the_disagreement_names_the_supporters_it_disputes")
index = {row.get("citation_id"): row for row in report.get("citations") or []}
require(index.get(refuter, {}).get("stance") == "refutes", "the_refuter_is_indexed_as_contradicting_evidence")
require(all(index.get(cid, {}).get("stance") != "refutes" for cid in supporters),
        "no_supporter_is_indexed_as_contradicting")
require("Disputed: 1 grounded source(s) contradict this finding" in str(report.get("rendered_answer") or ""),
        "the_rendered_answer_says_the_finding_is_disputed")

persisted = sanitize_report(report)
persisted_disputes = [row for row in persisted.get("unresolved_disagreements") or []
                      if row.get("claim_code") == "grounded_refutation"]
require(persisted_disputes and persisted_disputes[0]["refuting_citations"] == [refuter],
        "the_disagreement_survives_persistence")
require(persisted["evidence_policy_evaluation"]["grounded_refuting_citation_count"] == 1,
        "the_refuting_count_survives_persistence")

# --- the control: the same run with no refutation -------------------------------

control, control_adapter = run("unclear", "control")
control_policy = control.get("evidence_policy_evaluation") or {}
require(control_policy.get("independent_publisher_count") == 4,
        "the_control_also_has_four_independent_publishers")
require("grounded_refutation" not in (control_policy.get("finding_condition_failures") or []),
        "without_a_refutation_the_failure_does_not_appear")
require(control_policy.get("would_admit") is True, "without_a_refutation_four_grounded_supporters_are_admitted")
require(not [row for row in control.get("unresolved_disagreements") or [] if row.get("claim_code") == "grounded_refutation"],
        "without_a_refutation_no_disagreement_is_surfaced")
require(not any(row.get("stance") == "refutes" for row in control.get("citations") or []),
        "without_a_refutation_nothing_is_indexed_as_contradicting")
require("Disputed" not in str(control.get("rendered_answer") or ""),
        "without_a_refutation_the_answer_is_not_marked_disputed")

print(json.dumps({"suite": "v2731.2.5-grounded-refutation-end-to-end", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
