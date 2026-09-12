from __future__ import annotations

"""A report can represent several findings, each judged on its own claim, without touching today's reports.

The migration moves mechanism research from one generic finding to several
atomic ones. Before anything produces them, the report has to be able to say,
per finding: what the evidence policy measured, which citations completion
added, whether the finding is supported, disputed or unsupported, and which
disagreement disputes it - and to say that the answer judge judged the composed
explanation, not a finding.

Nothing in the run produces this shape yet. The history projection reads it in
its own shape: the run's policy fields once, each finding's verdict in its own
bounded entry, and no top-level verdict filled with defaults that would read as
one failed finding. A single-finding report keeps its exact keys and digest.
The Markdown export has no faithful rendering for an atomic explanation yet and
refuses one rather than flatten it into an inference list.
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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-4-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import bounded_autonomous_web_research as bawr
from bounded_research_history import (
    build_history_record,
    compare_reports,
    render_markdown_export,
    sanitize_report,
    validate_history_record,
)
from research_claim_assessment import digest_of_claim
from research_evidence_policy import RUN_LEVEL_EVALUATION_KEYS
from research_source_classification import classify_source_kind


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


OBJECTIVE = "Research how TCP congestion control works"
LOSS = "Loss detection halves the congestion window."
SLOW = "Slow start doubles the window every round trip."
HISTORY = "Congestion control was added to TCP in 1988."


def assessed(cid: str, stance: str, claim: str) -> dict:
    return {"citation_id": cid, "claim_digest": digest_of_claim(claim),
            "passage_digest": hashlib.sha256(f"passage-{cid}-{claim}".encode()).hexdigest(),
            "model_assessment": stance, "model_evidence_kind": "unknown",
            "textual_provenance_verified": True, "semantic_support_verified": False}


def source(n: int) -> dict:
    url = f"https://publisher{n}-net.org/tcp/congestion"
    return {"citation_id": f"web-{n}", "public_url": url, "host": url.split("/")[2],
            "source_kind": classify_source_kind(url), "freshness": "fresh", "quality_score": 0.5,
            "relevance_score": 1.0, "stance": "unknown", "publisher_digest": f"{n:064x}"}


POOL = [source(n) for n in range(1, 6)]
OFFERED = [row["citation_id"] for row in POOL]
FINDINGS = [
    {"title": "Loss", "summary": LOSS, "citation_ids": ["web-1"], "uncertainties": ["u"]},
    {"title": "Slow start", "summary": SLOW, "citation_ids": ["web-3"], "uncertainties": ["u"]},
    {"title": "History", "summary": HISTORY, "citation_ids": ["web-5"], "uncertainties": ["u"]},
]
ROWS = [assessed("web-1", "supports", LOSS), assessed("web-2", "supports", LOSS),
        assessed("web-3", "supports", SLOW), assessed("web-4", "refutes", SLOW),
        assessed("web-5", "unclear", HISTORY)]
SNAPSHOT = json.dumps(FINDINGS, sort_keys=True)


def build(findings=FINDINGS, **extra):
    return bawr._multi_finding_report_fields(
        findings, assessment_summary={"assessments": ROWS}, offered_ids=OFFERED, citations=POOL,
        currency_requirement="", objective=OBJECTIVE, answer_quality_level="partial",
        answer_quality_status="answer_quality_judged", answer_quality_input_truncated=True,
        source_selection={"selection_mode": "admissible_only", "citable_ids": OFFERED, "offered_citation_count": 5},
        **extra)


fields = build(truncated_finding_count=2)
evaluation = fields["evidence_policy_evaluation"]
entries = evaluation["finding_evaluations"]

# --- per-finding semantics are represented ----------------------------------------------

require(fields["finding_schema_version"] == bawr.FINDING_SCHEMA_VERSION and fields["synthesis_path"] == "atomic_mechanism",
        "a_multi_finding_report_names_its_schema_and_path")
require([e["admission_state"] for e in entries] == ["supported", "disputed", "unsupported"],
        "each_finding_has_its_own_admission_state")
require(evaluation["finding_evaluation_counts"] == {"total": 3, "supported": 1, "disputed": 1, "unsupported": 1, "truncated": 2},
        "the_counts_state_how_many_findings_are_in_each_state_and_how_many_were_cut")
require(fields["findings"][0]["citation_ids"] == ["web-1", "web-2"]
        and entries[0]["citation_completion"]["added_citation_count"] == 1
        and entries[1]["citation_completion"]["added_citation_count"] == 0,
        "citation_completion_is_per_finding")
require([e["grounded_supporting_citation_count"] for e in entries] == [2, 1, 0]
        and [e["grounded_refuting_citation_count"] for e in entries] == [0, 1, 0],
        "grounded_support_and_refutation_are_counted_per_finding")
require(all(e["policy_measurement"] in {"admitted", "not_admitted"} for e in entries)
        and entries[1]["policy_measurement"] == "not_admitted"
        and "grounded_refutation" in entries[1]["finding_condition_failures"],
        "each_finding_carries_its_measured_policy_verdict_as_a_fixed_code")
require(all(e["claim_digest"] == digest_of_claim(f["summary"]) for e, f in zip(entries, FINDINGS)),
        "each_entry_is_bound_to_its_claim_by_digest")
require([row["finding_claim_code"] for row in fields["unresolved_disagreements"]] == ["synthesis_2"]
        and fields["unresolved_disagreements"][0]["refuting_citations"] == ["web-4"]
        and "web-4" not in fields["findings"][1]["citation_ids"],
        "a_disagreement_names_the_finding_it_disputes_and_the_refuter_stays_out_of_its_citations")
require(evaluation["answer_quality_unit"] == "composed_explanation" and evaluation["answer_quality_input_truncated"] is True,
        "the_answer_judge_is_recorded_as_judging_the_composed_explanation")

# --- the run's fields are stated once, and no top-level verdict pretends to exist -----

verdict_keys = {"would_admit", "finding_condition_failures", "independent_publisher_count", "citation_completion",
                "grounded_supporting_citation_count", "authority_states", "available_admissible_evidence"}
require(not verdict_keys & set(evaluation), "no_finding_verdict_sits_at_the_top_of_a_multi_finding_measurement")
require(all(key in evaluation for key in ("policy_code", "requested_relation", "enforced"))
        and all(not RUN_LEVEL_EVALUATION_KEYS & set(e) for e in entries),
        "run_level_fields_are_stated_once_and_never_repeated_per_finding")
require(json.dumps(FINDINGS, sort_keys=True) == SNAPSHOT, "the_builder_never_mutates_its_inputs")

original = bawr._finding_policy_evaluation
calls = {"n": 0}


def drifting(finding, **kwargs):
    calls["n"] += 1
    return {**original(finding, **kwargs), "policy_code": f"policy-{calls['n']}"}


bawr._finding_policy_evaluation = drifting
try:
    build()
    raised = False
except ValueError as error:
    raised = str(error) == "run_level_policy_fields_differ_between_findings"
finally:
    bawr._finding_policy_evaluation = original
require(raised, "run_level_fields_that_differ_between_findings_are_an_error_not_an_average")

# --- the persisted projection ---------------------------------------------------------

REPORT = {
    "contract_version": "v2503.2", "session_id": "session-multi", "status": "research_report_ready",
    "finding_schema_version": fields["finding_schema_version"], "synthesis_path": fields["synthesis_path"],
    "reasonable_inferences": [{"claim_code": f"synthesis_{i}", "finding": f["summary"], "citations": f["citation_ids"],
                               "traceable": True} for i, f in enumerate(fields["findings"], 1)],
    "unresolved_disagreements": fields["unresolved_disagreements"], "citations": POOL, "citation_count": len(POOL),
    "evidence_policy_evaluation": evaluation, "rendered_answer": "Composed explanation.",
}
persisted = sanitize_report(REPORT)
projected = persisted["evidence_policy_evaluation"]
require(persisted["finding_schema_version"] == "v2731.4" and persisted["synthesis_path"] == "atomic_mechanism",
        "the_schema_and_path_survive_persistence")
require([e["admission_state"] for e in projected["finding_evaluations"]] == ["supported", "disputed", "unsupported"]
        and projected["finding_evaluation_counts"]["disputed"] == 1
        and projected["finding_evaluations"][0]["citation_completion"]["added_citation_count"] == 1,
        "per_finding_entries_survive_persistence_with_their_completion")
require(not verdict_keys & set(projected) and projected["answer_quality_unit"] == "composed_explanation"
        and projected["answer_quality_input_truncated"] is True and projected["policy_code"] == evaluation["policy_code"],
        "the_persisted_measurement_keeps_the_multi_finding_shape")
require(persisted["unresolved_disagreements"][0]["finding_claim_code"] == "synthesis_2",
        "the_disagreement_link_survives_persistence")
dumped = json.dumps(projected)
require(not any(text in dumped for text in (LOSS, SLOW, HISTORY, "publisher1-net")),
        "no_claim_text_or_source_identity_reaches_the_measurement_receipt")
many = {**evaluation, "finding_evaluations": entries * 14}
bounded = sanitize_report({**REPORT, "evidence_policy_evaluation": many})["evidence_policy_evaluation"]
require(len(bounded["finding_evaluations"]) == 32 and bounded["finding_evaluations_not_projected"] == 10,
        "the_projection_is_bounded_and_says_how_many_entries_it_left_out")

# --- single-finding reports carry none of it ------------------------------------------

LEGACY = {"session_id": "session-legacy", "status": "research_report_ready", "citations": POOL, "citation_count": len(POOL),
          "reasonable_inferences": [{"claim_code": "synthesis_1", "finding": "Loss: " + LOSS, "citations": ["web-1"]}],
          "unresolved_disagreements": [{"claim_code": "grounded_refutation", "finding": "x", "supporting_citations": ["web-1"],
                                        "refuting_citations": ["web-4"], "traceable": True}],
          "evidence_policy_evaluation": {"policy_code": "reference", "would_admit": True}, "rendered_answer": "Answer."}
legacy = sanitize_report(LEGACY)
require("finding_schema_version" not in legacy and "synthesis_path" not in legacy
        and "finding_claim_code" not in legacy["unresolved_disagreements"][0],
        "a_single_finding_report_gains_no_new_keys")
require(legacy["evidence_policy_evaluation"]["would_admit"] is True
        and "finding_evaluations" not in legacy["evidence_policy_evaluation"],
        "a_single_finding_measurement_keeps_its_own_shape")

# --- consumers: export refuses, history and comparison still work ----------------------

refused = render_markdown_export("session-multi", REPORT)
require(refused["ok"] is False and refused["status"] == "multi_finding_report_export_not_migrated",
        "the_markdown_export_refuses_a_multi_finding_report_rather_than_flatten_it")
require(render_markdown_export("session-legacy", LEGACY)["ok"] is True, "a_single_finding_report_still_exports")
session = {"state": "completed", "session_id": "session-multi", "session_digest": "a" * 64, "plan_digest": "b" * 64}
record = build_history_record(session, REPORT)
require(validate_history_record(record, session=session, report=REPORT)["ok"],
        "a_multi_finding_report_still_gets_a_valid_history_record")
require("status" in compare_reports(record, REPORT, record, LEGACY), "comparison_reads_claims_and_citations_and_still_runs")

print(json.dumps({"suite": "v2731.3.4-multi-finding-schema", "passed": len(CHECKS), "total": len(CHECKS),
                  "ok": True, "checks": CHECKS}))
