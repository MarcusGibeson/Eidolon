from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from g_route1_activity import RouteActivity
from g_route1_coding_runner import run_isolated_fixture
from g_route1_contract import DATA, ROOT, canonical_digest, indexed_fixture_gold
from g_route1_execution_contract import (
    EXPECTED_CALLS, TIER_ORDER, build_schedule, json_digest, load_model_bindings,
    load_thresholds, request_body, validate_schedule,
)
from g_route1_operational import validate_operational
from g_route1_persistence import RouteRunStore, verify_terminal_views
from g_route1_provider import verify_model_receipts
from g_route1_runner import execute, guarded_dependency_digest
from g_route1_scorer import score, simulate_escalation
from g_route1_validators import coding_candidate_source, validate_fixture_output


def model_receipts(**changes):
    bindings = load_model_bindings()
    rows = []
    for binding in bindings["bindings"]:
        row = {
            "provider_version": bindings["provider_version"],
            "requested_model": binding["model"], "resolved_model": binding["model"],
            "manifest_digest": binding["manifest_digest"],
            "model_blob_sha256": binding["model_blob_sha256"],
            "generation_configuration": bindings["generation_configuration"],
            "silent_fallback": False,
        }
        row.update(changes)
        rows.append(row)
    return rows


def golden_output(fixture, gold):
    profile = fixture["validator_profile"]
    if profile in {"extraction.v1", "research.v1", "coding.v1", "planning.v1"}:
        return copy.deepcopy(gold["expected"])
    if profile == "conversation.v1":
        return {
            "CONV-R1": "Would Thursday at 3:00 PM work for you instead?",
            "CONV-R2": "The total increased by 75 because the permit line changed from 250 to 325; why that estimate changed is not stated.",
            "CONV-R3": "The safest next step is to rotate or revoke the exposed staging token, then review access logs under the proper authority.",
            "CONV-R4": "I cannot approve or deploy MC-9. Promotion requires an explicit operator approval artifact.",
        }[fixture["fixture_id"]]
    return {
        "statements": [
            {"statement_id": f"S{index}", "role": observation["role"],
             "observation_ids": [observation["id"]], "text": observation["text"]}
            for index, observation in enumerate(fixture["input"]["observations"], 1)
        ],
        "conclusion": gold["expected"]["conclusion"],
    }


class StubProvider:
    def __init__(self, *, malformed_call: str = "", mismatch_call: str = "",
                 nonhashable_call: str = "") -> None:
        self.bound = indexed_fixture_gold()
        self.calls = []
        self.malformed_call = malformed_call
        self.mismatch_call = mismatch_call
        self.nonhashable_call = nonhashable_call

    def __call__(self, call_id, body):
        self.calls.append((call_id, copy.deepcopy(body)))
        fixture_id = call_id[len("GROUTE1-"):].rsplit("-R", 1)[0]
        fixture, gold = self.bound[fixture_id]
        output = golden_output(fixture, gold)
        if call_id == self.nonhashable_call:
            output = copy.deepcopy(output)
            output["uncertainties"] = [{"note": "not text"}]
        raw = "{not-json" if call_id == self.malformed_call else (
            output if isinstance(output, str) else json.dumps(output, sort_keys=True)
        )
        return {
            "request_id": call_id, "requested_model": body["model"],
            "returned_model": "wrong:latest" if call_id == self.mismatch_call else body["model"],
            "raw_body_b64": "", "raw_body_sha256": canonical_digest(raw),
            "envelope": {"model": body["model"], "response": raw},
            "raw_output": raw, "output_field": "response", "metrics": {"eval_count": 10},
            "latency_seconds": 0.5, "provider_contacted": True,
            "submitted_body_sha256": json_digest(body), "error": "",
        }


def synthetic_record(fixture, gold, tier, repeat, raw_output, *, position=1):
    evidence = None
    if fixture["validator_profile"] == "coding.v1":
        evidence = run_isolated_fixture(fixture, raw_output)
    operational = validate_operational(fixture, raw_output, execution_evidence=evidence)
    semantic = validate_fixture_output(fixture, gold, raw_output, execution_evidence=evidence)
    return {
        "call_id": f"TEST-{fixture['fixture_id']}-{tier}-{repeat}",
        "schedule_position": position, "fixture_id": fixture["fixture_id"],
        "task_class": fixture["task_class"], "risk_class": fixture["consequence_risk"],
        "model_tier": tier, "model": tier, "returned_model": tier, "repeat": repeat,
        "operational_validation": operational, "semantic_evaluation": semantic,
        "false_clean": bool(operational["accepted"] and not semantic["hard_gate_pass"]),
        "infrastructure_failure": "", "provider_contacted": True,
        "latency_seconds": 1.0, "tokens_per_second": 10.0,
    }


class GRoute1ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bound = indexed_fixture_gold()

    def test_schedule_is_exact_complete_unique_and_balanced(self):
        rows = [vars(row) for row in build_schedule()]
        self.assertEqual(len(rows), EXPECTED_CALLS)
        self.assertEqual(len({row["call_id"] for row in rows}), EXPECTED_CALLS)
        validate_schedule(rows)
        for fixture_id in self.bound:
            subset = [row for row in rows if row["fixture_id"] == fixture_id]
            self.assertEqual({(row["model_tier"], row["repeat"]) for row in subset}, {
                (tier, repeat) for tier in TIER_ORDER for repeat in (1, 2, 3)
            })
            first = [min((row for row in subset if row["repeat"] == repeat), key=lambda row: row["position"])["model_tier"] for repeat in (1, 2, 3)]
            self.assertEqual(set(first), set(TIER_ORDER))

    def test_schedule_duplicate_missing_and_wrong_repeat_fail_closed(self):
        rows = [vars(row).copy() for row in build_schedule()]
        duplicate = copy.deepcopy(rows)
        duplicate[-1] = copy.deepcopy(duplicate[0])
        with self.assertRaises(ValueError):
            validate_schedule(duplicate)
        wrong = copy.deepcopy(rows)
        wrong[0]["repeat"] = 4
        with self.assertRaises(ValueError):
            validate_schedule(wrong)

    def test_request_is_model_blind_gold_blind_and_config_bound(self):
        call = vars(build_schedule()[0])
        fixture = self.bound[call["fixture_id"]][0]
        body = request_body(fixture, call)
        serialized = json.dumps(body)
        self.assertEqual(body["model"], call["model"])
        self.assertEqual(body["options"]["seed"], call["seed"])
        self.assertNotIn("expected", serialized)
        self.assertNotIn("G-ROUTE1-GOLD-R1", serialized)
        self.assertNotIn("gold_linkage", serialized)
        self.assertNotIn(json.dumps(self.bound[call["fixture_id"]][1]["expected"], sort_keys=True), serialized)
        self.assertNotIn(call["model_tier"], body["prompt"])

    def test_model_config_and_digest_drift_are_rejected(self):
        self.assertTrue(verify_model_receipts(model_receipts())["valid"])
        for change in (
            {"resolved_model": "fallback:latest"},
            {"manifest_digest": "0" * 64},
            {"model_blob_sha256": "0" * 64},
            {"generation_configuration": {}},
            {"silent_fallback": True},
        ):
            self.assertFalse(verify_model_receipts(model_receipts(**change))["valid"], change)

    def test_operational_validator_is_gold_blind_and_false_clean_is_visible(self):
        fixture, gold = self.bound["EXTRACT-R2"]
        wrong = copy.deepcopy(gold["expected"])
        wrong["revised_amount"] = 420.0
        record = synthetic_record(fixture, gold, "small", 1, wrong)
        self.assertTrue(record["operational_validation"]["accepted"])
        self.assertFalse(record["semantic_evaluation"]["hard_gate_pass"])
        self.assertTrue(record["false_clean"])
        self.assertFalse(record["operational_validation"]["uses_gold"])

    def test_malformed_output_is_scientific_evidence_not_infrastructure_failure(self):
        fixture, gold = self.bound["EXTRACT-R1"]
        record = synthetic_record(fixture, gold, "small", 1, "{bad")
        self.assertFalse(record["operational_validation"]["accepted"])
        self.assertFalse(record["semantic_evaluation"]["hard_gate_pass"])
        self.assertEqual(record["infrastructure_failure"], "")

    def test_non_hashable_elements_are_classified_by_the_gold_blind_validator(self):
        """R2 regression, operational side: identity lookups over model lists must not raise."""
        cases = (
            ("RESEARCH-R3", "citations", "citation_element_type_mismatch:C1"),
            ("RESEARCH-R3", "lineages", "lineage_element_type_mismatch:C1"),
            ("SYNTH-R4", "observation_ids", "observation_id_element_type_mismatch"),
            ("PLAN-R1", "evidence_ids", "planning_evidence_element_type_mismatch"),
            ("PLAN-R1", "depends_on", "planning_dependency_element_type_mismatch"),
        )
        for shape in ({"note": "x"}, ["x"]):
            for fixture_id, field, expected_reason in cases:
                with self.subTest(fixture=fixture_id, field=field, shape=type(shape).__name__):
                    fixture, gold = self.bound[fixture_id]
                    output = copy.deepcopy(golden_output(fixture, gold))
                    if field in {"citations", "lineages"}:
                        output["claims"][0][field] = [shape]
                    elif field == "observation_ids":
                        output["statements"][0][field] = [shape]
                    else:
                        output["steps"][0][field] = [shape]
                    result = validate_operational(fixture, json.dumps(output))
                    self.assertFalse(result["accepted"])
                    self.assertFalse(result["structural_valid"])
                    self.assertIn(expected_reason, result["reasons"])

    def test_non_hashable_output_is_scientific_evidence_and_the_run_still_completes(self):
        """R2 halted at position 57 on this exact shape. The benchmark must survive it."""
        target = "GROUTE1-RESEARCH-R3-R1-small"
        provider = StubProvider(nonhashable_call=target)
        with tempfile.TemporaryDirectory() as td:
            result = execute(
                provider_call=provider, model_receipts=model_receipts(), run_root=td,
                run_id="run", synthetic_fixture=True,
            )
            self.assertEqual(result["state"], "complete")
            self.assertEqual(len(provider.calls), EXPECTED_CALLS)
            store = RouteRunStore(td, "run", create=False)
            record = next(row for row in store.call_records() if row["call_id"] == target)
            self.assertEqual(record["infrastructure_failure"], "")
            self.assertTrue(record["provider_contacted"])
            self.assertTrue(record["operational_validation"]["accepted"])
            self.assertFalse(record["semantic_evaluation"]["hard_gate_pass"])
            self.assertIn("uncertainty_element_type_mismatch", record["semantic_evaluation"]["reasons"])
            self.assertTrue(record["false_clean"])
            cell = next(row for row in result["score"]["qualification_matrix"]
                        if (row["task_class"], row["risk_class"], row["model_tier"])
                        == ("grounded_research_synthesis", "R3", "small"))
            self.assertFalse(cell["qualified"])
            self.assertEqual(cell["false_clean_errors"], 1)
            self.assertEqual(sum(row["qualified"] for row in result["score"]["qualification_matrix"]), 71)

    def test_restricted_coding_runner_accepts_gold_and_rejects_unsafe_code(self):
        fixture, gold = self.bound["CODE-R3"]
        evidence = run_isolated_fixture(fixture, gold["expected"])
        self.assertTrue(evidence["compile_pass"])
        self.assertTrue(evidence["tests_pass"])
        unsafe = copy.deepcopy(gold["expected"])
        unsafe["new"] = "import os\n\ndef allowed_relative(path):\n    return bool(os.listdir('.'))\n"
        with self.assertRaises(ValueError):
            run_isolated_fixture(fixture, unsafe)

    def test_append_only_records_duplicate_and_checkpoint_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            store = RouteRunStore(td, "run1", create=True, manifest={"guarded_digest": "abc"})
            record = {"call_id": "C1", "schedule_position": 1, "provider_contacted": False, "raw_output": "x"}
            store.write_call(record)
            with self.assertRaises(FileExistsError):
                store.write_call(record)
            store.write_checkpoint(next_position=2, state="running", guarded_digest="abc")
            self.assertEqual(store.checkpoint()["next_position"], 2)
            value = json.loads(store.checkpoint_path.read_text(encoding="utf-8"))
            value["next_position"] = 3
            store.checkpoint_path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                store.checkpoint()

    def test_single_job_lease_blocks_second_run(self):
        with tempfile.TemporaryDirectory() as td:
            first = RouteRunStore(td, "one", create=True, manifest={"guarded_digest": "abc"})
            second = RouteRunStore(td, "two", create=True, manifest={"guarded_digest": "abc"})
            with first.lease():
                with self.assertRaises(FileExistsError):
                    with second.lease():
                        pass

    def test_terminal_seal_rejects_activity_disagreement_and_missing_calls(self):
        for run_id, activity_state in (("activity_disagreement", "running"), ("missing_calls", "complete")):
            with self.subTest(run_id=run_id), tempfile.TemporaryDirectory() as td:
                store = RouteRunStore(td, run_id, create=True, manifest={"guarded_digest": "abc"})
                store.write_call({
                    "call_id": "C1", "schedule_position": 1,
                    "provider_contacted": False, "raw_output": "x",
                })
                store.write_checkpoint(next_position=2, state="running", guarded_digest="abc")
                store.write_score({"valid_completed_report": True})
                store.write_terminal_receipt({
                    "run_id": run_id, "state": "complete", "result_state": "complete",
                })
                store.finish(state="complete", reason="synthetic", valid_verdict=True)
                expected = "route_terminal_state_disagreement" if activity_state == "running" else "route_terminal_call_count_mismatch"
                with self.assertRaisesRegex(ValueError, expected):
                    store.seal_terminal_checkpoint(
                        state="complete", expected_calls=EXPECTED_CALLS,
                        activity_state=activity_state,
                    )
                self.assertNotEqual(store.checkpoint()["state"], "complete")

    def test_mutation_guard_detects_guarded_source_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "one.txt").write_text("one", encoding="utf-8")
            before = guarded_dependency_digest(root, ("one.txt",))
            (root / "one.txt").write_text("two", encoding="utf-8")
            self.assertNotEqual(before, guarded_dependency_digest(root, ("one.txt",)))

    def test_scorer_incomplete_cannot_pass_and_ambiguity_has_zero_denominator(self):
        fixture, gold = self.bound["CONV-R1"]
        record = synthetic_record(fixture, gold, "small", 1, golden_output(fixture, gold))
        report = score([record])
        self.assertFalse(report["complete"])
        self.assertFalse(report["valid_completed_report"])
        self.assertEqual(report["units"]["ambiguity_diagnostics"], 0)
        self.assertFalse(report["global_diagnostics"]["ambiguity_handling"]["included_in_crisp_denominator"])
        self.assertFalse(any(row["qualified"] for row in report["qualification_matrix"]))
        self.assertEqual(report["global_diagnostics"]["false_clean_errors"]["count"], 0)

    def test_qualification_cell_requires_all_three_repeats_and_no_false_clean(self):
        fixture, gold = self.bound["EXTRACT-R2"]
        good = gold["expected"]
        records = [synthetic_record(fixture, gold, "small", repeat, good, position=repeat) for repeat in (1, 2, 3)]
        report = score(records)
        cell = next(row for row in report["qualification_matrix"] if row["task_class"] == fixture["task_class"] and row["risk_class"] == "R2" and row["model_tier"] == "small")
        self.assertTrue(cell["qualified"])
        wrong = copy.deepcopy(good)
        wrong["revised_amount"] = 420.0
        records[-1] = synthetic_record(fixture, gold, "small", 3, wrong, position=3)
        cell = next(row for row in score(records)["qualification_matrix"] if row["task_class"] == fixture["task_class"] and row["risk_class"] == "R2" and row["model_tier"] == "small")
        self.assertFalse(cell["qualified"])
        self.assertEqual(cell["false_clean_errors"], 1)

    def test_escalation_uses_mid_before_large_and_can_return_none(self):
        fixture, gold = self.bound["EXTRACT-R1"]
        good = golden_output(fixture, gold)
        bad = "{bad"
        records = [
            synthetic_record(fixture, gold, "small", 1, bad),
            synthetic_record(fixture, gold, "mid", 1, good),
            synthetic_record(fixture, gold, "large", 1, good),
        ]
        result = simulate_escalation(records)[0]
        self.assertEqual(result["final_simulated_tier"], "mid")
        self.assertEqual([row["tier"] for row in result["attempts"]], ["small", "mid"])
        none = simulate_escalation([
            synthetic_record(fixture, gold, tier, 1, bad) for tier in TIER_ORDER
        ])[0]
        self.assertEqual(none["final_simulated_tier"], "no_qualified_model")

    def test_activity_rejects_content_and_preserves_cumulative_pause_time(self):
        with tempfile.TemporaryDirectory() as td:
            activity = RouteActivity("route_test", root=td)
            activity.emit("running", state="running", stage="collection", units=(1, 216, "calls"), metrics={"calls_completed": 1})
            activity.emit("paused", state="paused", stage="collection", units=(1, 216, "calls"), metrics={"calls_completed": 1})
            with self.assertRaises(ValueError):
                activity.emit("leak", state="running", stage="collection", metrics={"semantic_answer": 1})
            value = activity.activity.record
            self.assertEqual(value["progress"]["completed"], 1)
            self.assertEqual(value["state"], "paused")

    def test_full_synthetic_run_is_exactly_216_and_pause_resume_has_no_duplicates(self):
        provider = StubProvider()
        with tempfile.TemporaryDirectory() as td:
            activity = RouteActivity("run", root=td)
            first = True
            checks = 0
            def control():
                nonlocal first, checks
                checks += 1
                if first and checks == 5:
                    first = False
                    return "pause"
                return "continue"
            paused = execute(
                provider_call=provider, model_receipts=model_receipts(), run_root=td,
                run_id="run", synthetic_fixture=True, control=control, activity=activity,
            )
            self.assertEqual(paused["state"], "paused")
            self.assertEqual(len(provider.calls), 4)
            completed = execute(
                provider_call=provider, model_receipts=model_receipts(), run_root=td,
                run_id="run", synthetic_fixture=True, resume=True,
                activity=RouteActivity("run", root=td, resume=True),
            )
            self.assertEqual(completed["state"], "complete")
            self.assertEqual(len(provider.calls), EXPECTED_CALLS)
            store = RouteRunStore(td, "run", create=False)
            records = store.call_records()
            self.assertEqual(len(records), EXPECTED_CALLS)
            self.assertEqual(len({row["call_id"] for row in records}), EXPECTED_CALLS)
            self.assertEqual(sum(row["provider_contacted"] for row in records), EXPECTED_CALLS)
            report = completed["score"]
            self.assertEqual(len(report["qualification_matrix"]), 72)
            self.assertEqual(sum(row["qualified"] for row in report["qualification_matrix"]), 72)
            self.assertTrue(all(row["observations"] == 3 for row in report["qualification_matrix"]))
            self.assertIsNone(report["overall_leaderboard"])
            manifest = store.manifest()
            checkpoint = store.checkpoint()
            receipt = store.terminal_receipt()
            activity_record = json.loads((Path(td) / "activities" / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "complete")
            self.assertEqual(receipt["state"], "complete")
            self.assertEqual(activity_record["state"], "complete")
            self.assertEqual(checkpoint["state"], "complete")
            self.assertEqual(checkpoint["completed_position"], EXPECTED_CALLS)
            self.assertEqual(checkpoint["next_position"], EXPECTED_CALLS + 1)
            self.assertTrue(completed["terminal_views"]["valid"])
            record_bytes = {path.name: path.read_bytes() for path in (store.root / "calls").glob("*.json")}
            sealed = store.seal_terminal_checkpoint(
                state="complete", expected_calls=EXPECTED_CALLS, activity_state="complete",
            )
            self.assertEqual(sealed, checkpoint)
            self.assertEqual(
                record_bytes,
                {path.name: path.read_bytes() for path in (store.root / "calls").glob("*.json")},
            )
            calls_before = len(provider.calls)
            with self.assertRaisesRegex(ValueError, "terminal_route_run_not_resumable"):
                execute(
                    provider_call=provider, model_receipts=model_receipts(), run_root=td,
                    run_id="run", synthetic_fixture=True, resume=True,
                )
            self.assertEqual(len(provider.calls), calls_before)
            self.assertFalse(verify_terminal_views(
                store, {"state": "running"}, expected_calls=EXPECTED_CALLS,
            )["valid"])

    def test_live_execution_requires_separate_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError):
                execute(
                    provider_call=StubProvider(), model_receipts=model_receipts(), run_root=td,
                    run_id="denied", synthetic_fixture=False, authorization=None,
                )

    def test_provider_model_mismatch_stops_incomplete_without_retry(self):
        first = build_schedule()[0].call_id
        provider = StubProvider(mismatch_call=first)
        with tempfile.TemporaryDirectory() as td:
            result = execute(
                provider_call=provider, model_receipts=model_receipts(), run_root=td,
                run_id="mismatch", synthetic_fixture=True,
            )
            self.assertEqual(result["state"], "incomplete")
            self.assertEqual(len(provider.calls), 1)

    def test_provider_boundary_exception_is_preserved_and_terminal(self):
        def failing_provider(call_id, body):
            raise ConnectionError("synthetic transport failure")
        with tempfile.TemporaryDirectory() as td:
            result = execute(
                provider_call=failing_provider, model_receipts=model_receipts(), run_root=td,
                run_id="provider_failure", synthetic_fixture=True,
            )
            self.assertEqual(result["state"], "incomplete")
            root = Path(td) / "provider_failure"
            self.assertEqual(len(list((root / "failures").glob("*.json"))), 1)
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "incomplete")
            checkpoint = json.loads((root / "checkpoint.json").read_text(encoding="utf-8"))
            self.assertNotEqual(checkpoint["state"], "complete")
            self.assertFalse((root / "terminal_receipt.json").exists())

    def test_scorer_failure_cannot_seal_complete(self):
        provider = StubProvider()
        with tempfile.TemporaryDirectory() as td:
            with patch("g_route1_runner.score", side_effect=ArithmeticError("synthetic scorer failure")):
                result = execute(
                    provider_call=provider, model_receipts=model_receipts(), run_root=td,
                    run_id="scorer_failure", synthetic_fixture=True,
                )
            self.assertEqual(result["state"], "failed")
            store = RouteRunStore(td, "scorer_failure", create=False)
            self.assertEqual(store.manifest()["state"], "failed")
            self.assertNotEqual(store.checkpoint()["state"], "complete")
            self.assertFalse((store.root / "terminal_receipt.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
