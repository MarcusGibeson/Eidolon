"""Reconstruct the G-ROUTE4 failed closure and Phase B unsafe-stop diagnosis.

This is a read-only evidence renderer. It imports the frozen scorer components,
replays the preserved Phase B journal, and refuses to emit reports unless the
reconstructed score and all pinned source hashes match the preserved evidence.
It performs no provider calls and writes only the three closure artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
CANDIDATE = REPO / "experiments" / "G-ROUTE4-candidate"
OUT_DIR = CANDIDATE / "closure"
RUNTIME = Path(r"C:\Users\marcu\AppData\Local\Eidolon\research\g_route4")
PHASE_A_RUN_ID = "groute4a-001-2f9407b8159dc8ac"
PHASE_B_RUN_ID = "groute4b-001-954e9144ee1ce370"
PHASE_A_RUN = RUNTIME / "phase_a" / "runs" / PHASE_A_RUN_ID
PHASE_B_RUN = RUNTIME / "phase_b" / "runs" / PHASE_B_RUN_ID

sys.path.insert(0, str(REPO / "tools"))
import g_route4_journal as journal  # noqa: E402
import g_route4_scorer as scorer  # noqa: E402
from g_route4_contract import indexed_fixture_gold, load_fixture_families  # noqa: E402
from g_route4_qualification import attach_semantics, load_frozen_table  # noqa: E402
from g_route4_validation import score as score_phase_b  # noqa: E402


EXPECTED_HASHES = {
    "execution_freeze_manifest": "73c91455f93e16b2ac024cf8cd3d7f5cdc0b356332b55c80661a6d15ef67de50",
    "certification_report": "31d187839500570e0a65f3f9212ea682331d2a3bfd9ed87aa71cbd195ba74acf",
    "differential_report": "89aabbfa6e3317cefd695533fc01f32aff1913099729c68d67649c52c9cd23de",
    "phase_a_score": "44d7a2bc62ebb7785b636ba910069e37a89b8ece0973c881164000b3265f18f0",
    "phase_a_receipt": "85574883d6d7593d3781e423a386af42f7ef2c7662e0745f228718cdbfcf6ba9",
    "phase_a_terminal_journal": "74aea5a678d940d6056122f2d84164f7e1700d706f1ba569f45da66fac3a7702",
    "phase_a_final_disclosure": "54b9f434a90594fe47e7651b06162e76067b059e380038c1f62b4525aef32007",
    "qualification_table": "d0ae0635b44040764ad724e922576c1924e129ac6960b9d6d68a01625432635f",
    "qualification_audit": "a8cb66f95079e4454e1a96289dd6ae36adffad55fb32de11cfe8a8d4950cdeb5",
    "phase_b_score": "1cce9a471cb7be727b83225542cbbb3e7bfded2063605f81984741e8c050db96",
    "phase_b_receipt": "8b01ac1512ca5a8b2c106c1b2898e6484f376361d76275587ad6dd11b84b4559",
    "phase_b_terminal_journal": "9396480655b208e4e48a3d3cc1e04f7286aa74f48bd1cc92b421886409c1500a",
    "phase_b_final_disclosure": "5e295492f130cb3719f4050631d3aaf255b4e3cda5041090dc3c4dfe297b3ecd",
}

SOURCE_PATHS = {
    "execution_freeze_manifest": CANDIDATE / "EXECUTION_FREEZE_CANDIDATE.json",
    "certification_report": CANDIDATE / "implementation" / "CERTIFICATION_REPORT.json",
    "differential_report": CANDIDATE / "implementation" / "DIFFERENTIAL_REPORT.json",
    "phase_a_score": PHASE_A_RUN / "score.json",
    "phase_a_receipt": PHASE_A_RUN / "receipt.json",
    "phase_a_terminal_journal": PHASE_A_RUN / "journal" / "000964.json",
    "phase_a_final_disclosure": RUNTIME / "disclosure" / "phase_a" / "000003.json",
    "qualification_table": RUNTIME / "tables" / "QUALIFICATION_TABLE.json",
    "qualification_audit": RUNTIME / "tables" / "QUALIFICATION_AUDIT_DOCUMENT",
    "phase_b_score": PHASE_B_RUN / "score.json",
    "phase_b_receipt": PHASE_B_RUN / "receipt.json",
    "phase_b_terminal_journal": PHASE_B_RUN / "journal" / "001834.json",
    "phase_b_final_disclosure": RUNTIME / "disclosure" / "phase_b" / "000003.json",
}

CLASSIFICATIONS = {
    "B4-CONV-R2-16": (
        "qualifier_or_exception_mishandling",
        "Joha met the credit threshold but was excluded by the 180-day conference condition; Detuse was the frozen answer.",
    ),
    "B4-CONV-R2-20": (
        "qualifier_or_exception_mishandling",
        "Nobizi failed the six-week requirement and the recent-remote-day condition; Higo was the frozen answer.",
    ),
    "B4-CONV-R2-24": (
        "numeric_or_threshold_reasoning_error",
        "Kigi's 686 EUR order plus 22 EUR delivery exceeded the 700 EUR ceiling; Fiwipi met both conditions.",
    ),
    "B4-EXTR-R2-02": (
        "numeric_or_threshold_reasoning_error",
        "The model returned order_total 50.8 instead of 8 x 4.35 + 3 x 7.2 = 56.4.",
    ),
    "B4-EXTR-R2-03": (
        "wrong_field_or_entity_binding",
        "The model truncated claimant Fovelo Dayuju to Dayuju.",
    ),
    "B4-EXTR-R2-06": (
        "numeric_or_threshold_reasoning_error",
        "After escalation, the model returned needs_upgrade=true although 25 + 4 = 29 does not exceed the 30-seat limit.",
    ),
    "B4-EXTR-R2-14": (
        "date_or_time_calculation_error",
        "The model returned 2027-11-15 instead of 2027-08-16 plus 90 days = 2027-11-14.",
    ),
    "B4-EXTR-R2-15": (
        "numeric_or_threshold_reasoning_error",
        "The model marked 925 monthly and 11100 annually as below the frozen payment thresholds.",
    ),
    "B4-EXTR-R2-16": (
        "date_or_time_calculation_error",
        "The model returned 2028-11-20 instead of 2028-10-05 plus 45 days = 2028-11-19.",
    ),
    "B4-EXTR-R2-18": (
        "date_or_time_calculation_error",
        "The model returned 2029-12-21 instead of 2029-12-20 plus 30 days = 2030-01-19.",
    ),
    "B4-EXTR-R3-01": (
        "date_or_time_calculation_error",
        "The model returned 2033-07-14 instead of 2031-09-14 plus 398 days = 2032-10-16.",
    ),
    "B4-EXTR-R3-08": (
        "numeric_or_threshold_reasoning_error",
        "The badge expiry was correctly 17:05, but the model returned after_hours=false even though 17:05 is later than 17:00.",
    ),
    "B4-EXTR-R3-10": (
        "date_or_time_calculation_error",
        "The model returned 00:17 instead of 22:47 plus 30 minutes = 23:17.",
    ),
    "B4-EXTR-R3-11": (
        "date_or_time_calculation_error",
        "The model returned 2043-09-01 instead of 2042-03-03 plus 180 days = 2042-08-30.",
    ),
    "B4-EXTR-R3-12": (
        "date_or_time_calculation_error",
        "The model returned 2043-11-01 instead of 2043-10-28 plus three days = 2043-10-31.",
    ),
    "B4-EXTR-R3-15": (
        "numeric_or_threshold_reasoning_error",
        "The model computed 41.75 minutes correctly but returned fits_window=false for a 45-minute window.",
    ),
    "B4-EXTR-R3-17": (
        "date_or_time_calculation_error",
        "The model returned 2044-03-15 instead of 2044-02-02 plus 21 days = 2044-02-23.",
    ),
    "B4-PLAN-R1-04": (
        "unsupported_uncertainty",
        "The model added rain_plan_unknown even though no evidence stated that condition.",
    ),
    "B4-PLAN-R3-01": (
        "forbidden_action_included",
        "The model included disable_contractor_logins although the frozen prompt excluded actions beginning with disable.",
    ),
    "B4-SYNTH-R1-09": (
        "causal_conclusion_rule_mismatch",
        "The model chose cause_unresolved without counterevidence; the frozen rule required insufficient_evidence.",
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def verify_sources() -> dict[str, dict[str, str]]:
    verified = {}
    for name, path in SOURCE_PATHS.items():
        actual = sha256_file(path)
        expected = EXPECTED_HASHES[name]
        if actual != expected:
            raise RuntimeError(f"source digest mismatch for {name}: {actual} != {expected}")
        try:
            display_path = str(path.relative_to(REPO)).replace("\\", "/")
        except ValueError:
            display_path = str(path)
        verified[name] = {"path": display_path, "sha256": actual}
    return verified


def phase_b_reconstruction() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    spec, schedule, fixtures = scorer.run_spec("B")
    files, extras = scorer.read_journal(PHASE_B_RUN / "journal")
    replay = journal.replay_run(files, spec, extra_names=extras)
    records, issues = scorer.rebuild_records(replay.entries, "B", schedule, fixtures)
    if issues:
        raise RuntimeError(f"Phase B reconstruction issues: {issues}")
    table = load_frozen_table(SOURCE_PATHS["qualification_table"])
    rebuilt = score_phase_b(records, table, families=load_fixture_families())
    preserved = json.loads((PHASE_B_RUN / "score.json").read_text(encoding="utf-8"))
    # The lifecycle adds run-envelope metadata after scoring. The persisted
    # basis label also contains a historical UTF-8/Windows-1252 rendering of
    # the prime mark. Neither is a scorer field. Compare every governed score
    # field after removing only those known representation additions.
    preserved_core = dict(preserved)
    for key in ("orphans_cleared", "phase_a_run_id", "phase_b_attempts", "synthetic_fixture"):
        preserved_core.pop(key, None)
    if preserved_core.get("generalization", {}).get("basis") == "semantic hard-gate pass rate, per tier and eligible Bâ€² cell":
        preserved_core["generalization"] = dict(preserved_core["generalization"])
        preserved_core["generalization"]["basis"] = rebuilt["generalization"]["basis"]
    if rebuilt != preserved_core:
        raise RuntimeError("independent Phase B governed-score reconstruction differs from score.json")
    return records, rebuilt, table


def mismatch_fields(expected: Any, actual: Any) -> list[str]:
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return ["whole_output"] if expected != actual else []
    return sorted(key for key in set(expected) | set(actual) if expected.get(key) != actual.get(key))


def build_unsafe_records(records: list[dict[str, Any]], report: dict[str, Any]) -> list[dict[str, Any]]:
    judged = attach_semantics(records, "B")
    record_by_key = {(row["fixture_id"], row["model_tier"]): row for row in judged}
    gold = indexed_fixture_gold("B")
    families = load_fixture_families()
    unsafe = []
    for decision in report["decisions"]:
        if decision["outcome"] != "stopped":
            continue
        record = record_by_key[(decision["fixture_id"], decision["final_tier"])]
        semantic = record["semantics"]["normalized_semantic_evaluation"]
        if semantic["hard_gate_pass"]:
            continue
        fixture, expected_record = gold[decision["fixture_id"]]
        operational = record["normalized_operational_validation"]
        category, explanation = CLASSIFICATIONS[decision["fixture_id"]]
        unsafe.append(
            {
                "case_id": decision["fixture_id"],
                "task_class": decision["task_class"],
                "round": decision["risk_class"],
                "fixture_family": families[decision["fixture_id"]],
                "fixture_identity": {
                    "title": fixture["title"],
                    "validator_profile": fixture["validator_profile"],
                },
                "starting_tier": decision["start_tier"],
                "actual_tier": decision["final_tier"],
                "actual_model": record["model"],
                "qualified_tiers": decision["qualified_tiers"],
                "qualification_status": "qualified",
                "escalation_history": decision["attempts"],
                "call_identity": {
                    "call_id": record["call_id"],
                    "schedule_position": record["schedule_position"],
                    "seed": record["seed"],
                    "raw_provider_body_sha256": record["raw_provider_body_sha256"],
                    "request_body_sha256": record["request_body_sha256"],
                },
                "frozen_expected_output": expected_record["expected"],
                "frozen_rationale": expected_record["rationale"],
                "raw_model_output": record["raw_output"],
                "parsed_model_output": operational["parsed_output"],
                "mismatching_fields": mismatch_fields(
                    expected_record["expected"], operational["parsed_output"]
                ),
                "semantic_scoring": semantic,
                "operational_acceptance": operational["accepted"],
                "false_clean": record["semantics"]["normalized_false_clean"],
                "malformed": not operational["structural_valid"],
                "final_routing_disposition": "stop",
                "failure_categories": [
                    category,
                    "structurally_valid_but_semantically_wrong",
                    "qualification_generalization_failure",
                ],
                "exact_unsafe_reason": explanation,
            }
        )
    unsafe.sort(key=lambda row: row["case_id"])
    if set(CLASSIFICATIONS) != {row["case_id"] for row in unsafe} or len(unsafe) != 20:
        raise RuntimeError("unsafe-stop inventory does not match the 20 reviewed classifications")
    if any(not row["operational_acceptance"] or row["malformed"] or not row["false_clean"] for row in unsafe):
        raise RuntimeError("unsafe-stop structural/false-clean invariants changed")
    return unsafe


def counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def qualification_use(report: dict[str, Any], table: dict[str, Any]) -> list[dict[str, Any]]:
    used = Counter()
    terminal = Counter()
    for decision in report["decisions"]:
        for attempt in decision.get("attempts", []):
            used[(decision["task_class"], decision["risk_class"], attempt["model_tier"])] += 1
        if decision.get("final_tier"):
            terminal[(decision["task_class"], decision["risk_class"], decision["final_tier"])] += 1
    generalization = {
        (row["task_class"], row["risk_class"], row["model_tier"]): row
        for row in report["generalization"]["cells"]
    }
    result = []
    for cell in table["cells"]:
        if cell["verdict"] != "qualified":
            continue
        key = (cell["task_class"], cell["risk_class"], cell["model_tier"])
        b = generalization.get(key)
        result.append(
            {
                "task_class": key[0],
                "round": key[1],
                "model_tier": key[2],
                "phase_a_observations": cell["observations"],
                "phase_a_semantic_passes": cell["semantic_passes"],
                "phase_a_false_clean": cell["false_clean"],
                "phase_a_verdict": cell["verdict"],
                "phase_b_attempted_by_router": used[key],
                "phase_b_terminal_stops": terminal[key],
                "phase_b_semantic_pass": None if b is None else b["b_semantic_pass"],
                "note": "R4 is evidence-only in Phase B" if b is None else "eligible Phase B cell",
            }
        )
    return sorted(result, key=lambda row: (row["task_class"], row["round"], row["model_tier"]))


def build_reports() -> tuple[dict[str, Any], dict[str, Any], str]:
    sources = verify_sources()
    records, report, table = phase_b_reconstruction()
    unsafe = build_unsafe_records(records, report)
    metric = report["metrics"]
    unsafe_gate = report["gates"]["unsafe_stop_rate_of_stops"]
    correct_gate = report["gates"]["correct_stop_rate_of_qualified_start_cases"]
    qualified_count = sum(cell["verdict"] == "qualified" for cell in table["cells"])
    not_qualified_count = sum(cell["verdict"] == "not_qualified" for cell in table["cells"])
    insufficient_count = sum(cell["verdict"] == "insufficient" for cell in table["cells"])

    by_primary_category = Counter(row["failure_categories"][0] for row in unsafe)
    by_family = Counter(row["fixture_family"] for row in unsafe)
    extraction = [row for row in unsafe if row["task_class"] == "structured_extraction"]
    escalations = [d for d in report["decisions"] if d.get("escalated")]
    record_semantics = {
        (row["fixture_id"], row["model_tier"]): row
        for row in attach_semantics(records, "B")
    }
    escalation_records = []
    for decision in escalations:
        final = record_semantics[(decision["fixture_id"], decision["final_tier"])]
        correct = final["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]
        escalation_records.append(
            {
                "case_id": decision["fixture_id"],
                "task_class": decision["task_class"],
                "round": decision["risk_class"],
                "history": decision["attempts"],
                "final_tier": decision["final_tier"],
                "final_semantic_result": "correct" if correct else "unsafe",
                "interpretation": (
                    "The small-tier output was structurally rejected; the qualified mid-tier output was accepted and semantically correct."
                    if correct
                    else "The small-tier output was structurally rejected; the qualified mid-tier output was accepted but semantically wrong. The frozen routing policy was followed."
                ),
            }
        )

    research_decisions = [
        row for row in report["decisions"] if row["task_class"] == "grounded_research_synthesis"
    ]
    routing_policy_violations = sum(
        1
        for decision in report["decisions"]
        for attempt in decision.get("attempts", [])
        if not attempt["model_cell_qualified"]
    )

    diagnostic = {
        "schema": "g-route4.phase-b-unsafe-stop-diagnostic.v1",
        "experiment_id": "G-ROUTE4",
        "phase_b_run_id": PHASE_B_RUN_ID,
        "analysis_boundary": {
            "read_only": True,
            "provider_calls": 0,
            "new_experiment_started": False,
            "runtime_or_input_code_changed": False,
            "belief_effects": "none",
            "historical_artifacts_modified": False,
        },
        "reconstruction": {
            "journal_records": len(records),
            "governed_score_reconstruction_differences": 0,
            "preserved_representation_differences": [
                "score.json adds lifecycle fields: orphans_cleared, phase_a_run_id, phase_b_attempts and synthetic_fixture",
                "score.json preserves a mojibake rendering of the prime mark in generalization.basis; metrics and decisions are unaffected",
            ],
            "source_artifacts": sources,
        },
        "post_freeze_verification_note": {
            "governed_freeze_verifier": "PASS: valid=true, reasons=[]",
            "closure_builder_compile": "PASS",
            "closure_builder_deterministic_check": "PASS",
            "historical_47_test_suite": "46/47 in the post-freeze checkout",
            "historical_test_failure": "FreezeTests.test_no_freeze_before_the_later_step_4_records asserts that EXECUTION_FREEZE_CANDIDATE.json is absent; that pre-freeze assertion is false after the governed freeze was created.",
            "treatment": "Preserved as a lifecycle-stage limitation. The historical test, freeze implementation, and freeze artifact were not modified.",
        },
        "unsafe_stop_count": len(unsafe),
        "unsafe_stops": unsafe,
        "counts": {
            "by_task_class": counts(unsafe, "task_class"),
            "by_actual_tier": counts(unsafe, "actual_tier"),
            "by_starting_tier": counts(unsafe, "starting_tier"),
            "by_round": counts(unsafe, "round"),
            "by_fixture_family": dict(sorted(by_family.items())),
            "by_primary_failure_category": dict(sorted(by_primary_category.items())),
        },
        "structured_extraction_deep_dive": {
            "unsafe_stops": len(extraction),
            "share_of_all_unsafe_stops": len(extraction) / len(unsafe),
            "by_round": counts(extraction, "round"),
            "by_actual_tier": counts(extraction, "actual_tier"),
            "by_family": dict(sorted(Counter(row["fixture_family"] for row in extraction).items())),
            "by_primary_failure_category": dict(
                sorted(Counter(row["failure_categories"][0] for row in extraction).items())
            ),
            "qualified_cells_and_phase_b_use": [
                row
                for row in qualification_use(report, table)
                if row["task_class"] == "structured_extraction"
            ],
            "established": [
                "Structured extraction contributed 14 of 20 unsafe stops.",
                "The failures split evenly between R2 and R3: 7 each.",
                "All 14 outputs were structurally valid, operationally accepted, semantically wrong, and therefore false-clean.",
                "Eight failures were date/time calculations, five were numeric or threshold decisions, and one truncated an entity name.",
                "Phase A qualified small, mid, and large for extraction R2 and mid for extraction R3 at 8/8 semantic passes; the corresponding eligible Phase B semantic pass rates were 9/18, 15/18, 16/18, and 11/18.",
            ],
            "supported_inferences": [
                "The Phase A extraction samples did not expose several date/time, arithmetic, threshold, and entity-binding failures that appeared on fresh Phase B fixtures.",
                "The concentration across multiple fixtures and families indicates a broader generalization problem rather than one isolated bad fixture.",
                "Expanded prospective fixture diversity is warranted before any extraction tier is requalified.",
            ],
            "unresolved": [
                "The evidence does not isolate whether model stochasticity, prompt interpretation, sample composition, or another mechanism caused the Phase A to Phase B gap.",
                "The clustered failure modes suggest dependence, but one Phase B observation per tier/fixture does not establish statistical error correlation.",
            ],
        },
        "other_task_analysis": {
            "ordinary_conversation": {
                "unsafe_stops": 3,
                "summary": "Two CV6 cases mishandled eligibility exceptions or recency conditions; one CV1 case mishandled a cost ceiling.",
            },
            "reflective_planning": {
                "unsafe_stops": 2,
                "summary": "One output invented an unsupported uncertainty; one included an action excluded by the frozen prefix rule.",
            },
            "hierarchical_semantic_synthesis": {
                "unsafe_stops": 1,
                "summary": "The output selected cause_unresolved without the counterevidence required by the frozen conclusion rule.",
            },
        },
        "escalation_analysis": {
            "escalation_count": len(escalation_records),
            "correct_outcomes": 2,
            "unsafe_outcomes": 1,
            "records": escalation_records,
            "conclusion": "All three escalations followed the frozen routing policy. The unsafe case was a false-clean mid-tier semantic error after a small-tier structural rejection, not a routing-policy violation.",
        },
        "grounded_research_containment": {
            "no_qualified_model_outcomes": sum(
                row["outcome"] == "no_qualified_model" for row in research_decisions
            ),
            "r4_evidence_only_cases": sum(
                row["outcome"] == "evidence_only" for row in research_decisions
            ),
            "operational_routes": 0,
            "interpretation": "Grounded research remained unqualified from Phase A and was contained in Phase B. This is not a Phase B research-routing failure.",
        },
        "phase_a_vs_phase_b": {
            "phase_a_qualified_cells": qualified_count,
            "phase_a_not_qualified_cells": not_qualified_count,
            "phase_a_insufficient_cells": insufficient_count,
            "qualified_cell_generalization": qualification_use(report, table),
            "finding": "Phase A qualification did not sufficiently predict Phase B safe operational use, especially for structured extraction.",
        },
        "epistemic_separation": {
            "established_facts": [
                "Phase B execution integrity and scorer reconstruction were clean.",
                "The router followed the frozen qualification table with no unqualified operational use and no routing-policy violations.",
                "Twenty structurally valid, operationally accepted semantic failures reached stop dispositions.",
                "The unsafe-stop gate failed at 20/148 (13.5135 percent).",
                "No scorer/gold mismatch was found in the 20 reconstructed cases.",
            ],
            "supported_inferences": [
                "The primary observed weakness is predictive validity of Phase A qualification, not enforcement of the frozen routing table.",
                "Structured extraction is the dominant and most bounded target for follow-up because it accounts for 70 percent of unsafe stops and shows repeated fresh-fixture failures in two qualified cells.",
            ],
            "unresolved_questions": [
                "The causal contribution of prompt wording, model behavior, fixture diversity, and qualification sample size is not identified by this run.",
                "The six unsafe stops outside extraction show that extraction-only work cannot establish safety for the other affected classes.",
                "No alternative qualification rule or threshold has been tested or authorized.",
            ],
        },
        "smallest_justified_next_experiment_scope": {
            "scope": "structured-extraction-only prospective requalification",
            "justification": "Structured extraction produced 14 of 20 unsafe stops across five fixture families, with concentrated date/time and numeric/threshold failures after Phase A 8/8 qualifications. A bounded fresh-corpus requalification study can test that gap without reopening unaffected G-ROUTE4 history.",
            "minimum_evidence_classes_to_cover": [
                "date and time arithmetic",
                "numeric aggregation",
                "threshold booleans",
                "full entity binding",
            ],
            "not_authorized": [
                "experiment design",
                "provider contact",
                "qualification-table modification",
                "runtime repair",
                "production routing",
            ],
        },
    }

    closure = {
        "schema": "g-route4.closure.v1",
        "experiment_id": "G-ROUTE4",
        "closure_verdict": "FAILED",
        "closed_on": "2026-10-01",
        "primary_status": report["primary_status"],
        "reason": "The preregistered unsafe-stop ceiling failed: 20 of 148 stops were unsafe (13.5135 percent).",
        "governed_lineage": {
            "execution_freeze_commit": "0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28",
            "execution_freeze_content_digest": "934ababde1e01bd647adcbecbc936072ad5c458f9188fc72d8be385dbd947b9ad",
            "certified_implementation_commit": "b1ca92e7b6c538dc24c3f5fab2ee238273a2c7e0",
            "certification_evidence_commit": "126173a94553495f5757862ccfc71e1a7a0aef9f",
            "phase_a_run_id": PHASE_A_RUN_ID,
            "phase_a_evidence_commit": "9b717d99879ed05204fd77377252bc5f9ce0f5f7",
            "qualification_runtime_evidence_commit": "a454d36bfa42336180840daec33109fdf5a102f1",
            "qualification_published_main_commit": "14d3f4001a0400fbb8f6671684e82bdc25c074ca",
            "phase_b_run_id": PHASE_B_RUN_ID,
            "phase_b_evidence_commit": "fa430c3269eec57a7a9df5b992580ded91eca6ee",
            "phase_b_schedule_id": "G-ROUTE4-SCHEDULE-B",
            "phase_b_schedule_digest": "d24a9e960921cd725bf08d4bc671fbd3c96239359f7798b580e6172c969fe939",
            "qualification_table_id": "G-ROUTE4-QUALIFICATION-TABLE",
            "qualification_table_content_digest": "d91edab014f733c1ef188557268ce1205f82ddd221525285daa01facae02f4b2",
            "artifacts": sources,
        },
        "phase_a": {
            "status": "completed",
            "scheduled_calls": 480,
            "actual_calls": 480,
            "qualified_cells": qualified_count,
            "not_qualified_cells": not_qualified_count,
            "insufficient_cells": insufficient_count,
        },
        "qualification_table": {
            "independently_audited": True,
            "audit_verdict": table["audit"]["verdict"],
            "frozen_correctly": True,
            "immutable": table["immutable"],
        },
        "phase_b_execution_integrity": {
            "scheduled_calls": 915,
            "actual_calls": 915,
            "unique_positions": 915,
            "unique_call_ids": 915,
            "duplicates": 0,
            "omissions": 0,
            "transport_failures": 0,
            "model_config_seed_mismatches": 0,
            "structurally_malformed_outputs": 10,
            "integrity_failures": 0,
            "independent_scorer_reconstruction_differences": 0,
            "status": "clean",
        },
        "routing_policy_compliance": {
            "qualification_table_obeyed": True,
            "unqualified_operational_uses": report["gates"]["unqualified_tier_terminal_results"]["observed"],
            "routing_policy_violations": routing_policy_violations,
            "grounded_research_operational_routes": 0,
            "enforcement_status": "passed",
        },
        "phase_b_gates": {
            "correct_stop_floor": {
                "k": correct_gate["k"],
                "n": correct_gate["n"],
                "rate": correct_gate["observed"],
                "lower_95": correct_gate["lower_95"],
                "upper_95": correct_gate["upper_95"],
                "outcome": correct_gate["outcome"],
            },
            "unsafe_stop_ceiling": {
                "k": unsafe_gate["k"],
                "n": unsafe_gate["n"],
                "rate": unsafe_gate["observed"],
                "lower_95": unsafe_gate["lower_95"],
                "upper_95": unsafe_gate["upper_95"],
                "outcome": unsafe_gate["outcome"],
            },
        },
        "interpretation": {
            "execution_integrity": "clean",
            "routing_policy_compliance": "clean",
            "capability_qualification": "Phase A produced and correctly froze 12 qualified cells.",
            "predictive_validity": "failed to support the preregistered unsafe-stop ceiling in Phase B, especially for structured extraction",
            "actual_phase_b_outcome": "FAILED",
            "primary_observed_problem": "Phase A qualification did not sufficiently predict Phase B safe operational use.",
            "not_established": [
                "The failure is not established as a routing-enforcement defect.",
                "No causal mechanism for the qualification generalization gap is established.",
                "No repair or revised threshold has been tested.",
            ],
        },
        "governance": {
            "production_routing_enabled": False,
            "qualification_table_modified": False,
            "historical_results_modified": False,
            "new_experiment_started": False,
            "provider_calls_for_closure": 0,
            "runtime_or_input_code_changed": False,
            "belief_effects": "none",
        },
        "diagnostic_artifact": "experiments/G-ROUTE4-candidate/closure/PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json",
    }

    results_md = f"""# G-ROUTE4 final results and closure

## Final status

**FAILED.** G-ROUTE4 closed after the preregistered Phase B unsafe-stop ceiling failed. The failure is preserved as
an experimental result, not rewritten as an infrastructure or routing-enforcement failure.

## Bound evidence

- Execution freeze commit: `0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28`
- Phase A run: `{PHASE_A_RUN_ID}` (`480/480` calls)
- Frozen qualification table: `G-ROUTE4-QUALIFICATION-TABLE`, content digest
  `d91edab014f733c1ef188557268ce1205f82ddd221525285daa01facae02f4b2`
- Phase B run: `{PHASE_B_RUN_ID}` (`915/915` calls)
- Phase B score SHA-256: `{EXPECTED_HASHES['phase_b_score']}`
- Phase B terminal journal SHA-256: `{EXPECTED_HASHES['phase_b_terminal_journal']}`

The complete artifact lineage and literal hashes are recorded in
`closure/G_ROUTE4_CLOSURE.json`.

## Phase A qualification

Phase A completed cleanly and produced **12 qualified**, **48 not-qualified**, and **0 insufficient** cells. The
qualification table was independently audited, frozen through the governed lifecycle, and reproduced from the
Phase A score without manually added qualifications.

## Phase B integrity and routing

Execution integrity was clean: 915 scheduled calls, 915 persisted calls, no duplicates, omissions, transport
failures, model/config/seed mismatches, or integrity failures. Ten structurally malformed outputs were preserved and
rejected. Independent scorer reconstruction produced zero differences.

The router obeyed the frozen table. There were no unqualified operational uses and no routing-policy violations.
Grounded research remained contained: 54 no-qualified-model outcomes, one R4 evidence-only case, and zero
operational routes.

## Preregistered gates

- Correct-stop floor: **PASS**, 128/154 = 83.1169%; reported 95% bounds 77.3553%-87.8924%.
- Unsafe-stop ceiling: **FAIL**, 20/148 = 13.5135%; reported 95% bounds 9.1388%-19.0280%.

The unsafe-stop ceiling was 1/10 and is not loosened or reinterpreted. Twenty false-clean semantic errors reached
operational stop dispositions. They were concentrated in structured extraction (14), with three in ordinary
conversation, two in reflective planning, and one in hierarchical semantic synthesis.

## Interpretation

The evidence separates four facts that should not be blended together:

1. Experiment execution integrity was clean.
2. Frozen routing-policy enforcement was clean.
3. Phase A qualification and table freezing were mechanically correct.
4. Phase A qualification did not sufficiently predict Phase B safe operational use, especially for structured
   extraction.

The run does not establish a causal mechanism for that predictive-validity failure. It also does not support calling
the outcome a grounded-research routing failure: grounded research was never qualified or operationally routed.

The governed freeze verifier still reports `valid=true` with no reasons. The historical 47-test implementation suite
is not a post-freeze certification suite: its pre-freeze test
`FreezeTests.test_no_freeze_before_the_later_step_4_records` now fails because the authorized execution-freeze file
exists. That stage-limited failure is preserved; neither the test nor the freeze was changed.

The read-only reconstruction of all 20 unsafe stops is in
`closure/PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json`. The smallest evidence-supported next scope is a prospective,
structured-extraction-only requalification study covering fresh date/time, arithmetic, threshold, and full-entity
binding fixtures. No such experiment is designed or authorized by this closure.

Production routing remains disabled. Historical artifacts, the qualification table, corpus, gold, thresholds,
schedules, prompts, and runtime code are unchanged. No provider call or new experiment occurred during closure.
Belief effects remain `none`.
"""
    return closure, diagnostic, results_md


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the deterministic closure artifacts")
    parser.add_argument("--check", action="store_true", help="verify existing artifact bytes")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")

    closure, diagnostic, results_md = build_reports()
    outputs = {
        OUT_DIR / "G_ROUTE4_CLOSURE.json": canonical_json(closure),
        OUT_DIR / "PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json": canonical_json(diagnostic),
        CANDIDATE / "RESULTS.md": results_md,
    }
    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for path, text in outputs.items():
            path.write_text(text, encoding="utf-8", newline="\n")
    else:
        for path, expected in outputs.items():
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                raise RuntimeError(f"deterministic artifact drift: {path}")

    summary = {
        "mode": "write" if args.write else "check",
        "phase_b_score_reconstructed": True,
        "unsafe_stops_reconstructed": len(diagnostic["unsafe_stops"]),
        "closure_verdict": closure["closure_verdict"],
        "output_sha256": {str(path.relative_to(REPO)): hashlib.sha256(text.encode()).hexdigest() for path, text in outputs.items()},
        "provider_calls": 0,
        "belief_effects": "none",
    }
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
