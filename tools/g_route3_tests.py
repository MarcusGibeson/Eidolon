from __future__ import annotations

"""Deterministic adversarial tests for G-ROUTE3. No provider is contacted."""

import copy
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import g_route3_contract as contract
import g_route3_qualification as qualification
import g_route3_routing as routing
import g_route3_runner as runner
import g_route3_validation as validation
from g_route1_coding_runner import run_isolated_fixture
from g_route1_operational import validate_operational
from g_route1_persistence import RouteRunStore
from g_route1_validators import validate_fixture_output

READY_AUDIT = {"verdict": "READY", "auditor": "synthetic-test", "statement": "synthetic"}


def receipts(**changes):
    bindings = contract.load_model_bindings()
    return [{"provider_version": bindings["provider_version"], "requested_model": row["model"],
             "resolved_model": row["model"], "manifest_digest": row["manifest_digest"],
             "model_blob_sha256": row["model_blob_sha256"],
             "generation_configuration": bindings["generation_configuration"], "silent_fallback": False, **changes}
            for row in bindings["bindings"]]


def reference(fixture, gold):
    ref = gold["reference_output"]
    return ref if isinstance(ref, str) else json.dumps(ref, sort_keys=True)


def wrong(fixture, gold):
    """A structurally legal but semantically wrong answer, per profile."""
    profile = fixture["validator_profile"]
    exp = copy.deepcopy(gold["expected"])
    if profile == "conversation.v1":
        return "I am not sure."
    if profile == "extraction.v1":
        key = next(iter(exp))
        exp[key] = (not exp[key]) if isinstance(exp[key], bool) else (
            exp[key] + 1 if isinstance(exp[key], (int, float)) else str(exp[key]) + "x")
        schema = fixture["input"]["schema"][key]
        if isinstance(gold["expected"][key], str) and "|" in schema:
            exp[key] = [v for v in schema.split("|") if v != gold["expected"][key]][0]
        return json.dumps(exp, sort_keys=True)
    if profile == "research.v1":
        exp["recommendation"] = [r for r in fixture["input"]["allowed_recommendations"] if r != exp["recommendation"]][0]
        return json.dumps(exp, sort_keys=True)
    if profile == "synthesis.v1":
        ref = copy.deepcopy(gold["reference_output"])
        ref["conclusion"] = [c for c in fixture["input"]["allowed_conclusions"] if c != ref["conclusion"]][0]
        return json.dumps(ref, sort_keys=True)
    if profile == "coding.v1":
        return json.dumps({"path": "app.py", "old": fixture["input"]["source"], "new": fixture["input"]["source"]})
    exp["uncertainties"] = []
    exp["steps"] = [dict(s) for s in exp["steps"]][:-1] or exp["steps"]
    return json.dumps(exp, sort_keys=True)


class Provider:
    """Synthetic provider. `plan(fixture, tier) -> 'correct'|'wrong'|'fenced'|'malformed'|'nonhashable'`."""

    def __init__(self, corpus, plan):
        self.index = contract.indexed_fixture_gold(corpus)
        self.plan = plan
        self.calls = []

    def __call__(self, call_id, body):
        self.calls.append(call_id)
        fixture_id = call_id[len("GROUTE3-"):].rsplit("-R", 1)[0]
        tier = call_id.rsplit("-", 1)[1]
        fixture, gold = self.index[fixture_id]
        mode = self.plan(fixture, tier)
        raw = reference(fixture, gold) if mode in ("correct", "fenced") else wrong(fixture, gold)
        if mode == "fenced" and fixture["validator_profile"] != "conversation.v1":
            raw = "```json\n" + raw + "\n```"
        if mode == "malformed":
            raw = "{not json" if fixture["validator_profile"] != "conversation.v1" else ""
        if mode == "nonhashable" and fixture["validator_profile"] == "research.v1":
            value = json.loads(reference(fixture, gold))
            value["uncertainties"] = [{"code": "x"}]
            raw = json.dumps(value)
        return {"request_id": call_id, "requested_model": body["model"], "returned_model": body["model"],
                "raw_body_b64": "", "raw_body_sha256": "", "envelope": {"model": body["model"], "response": raw},
                "raw_output": raw, "output_field": "response", "metrics": {"eval_count": 10, "prompt_eval_count": 20},
                "latency_seconds": 0.01, "provider_contacted": True, "submitted_body_sha256": "", "error": ""}


def table_from(lookup):
    cells = []
    for task in contract.TASK_CLASSES:
        for risk in contract.RISK_CLASSES:
            for tier in contract.TIER_ORDER:
                cells.append({"task_class": task, "risk_class": risk, "model_tier": tier,
                              "verdict": "qualified" if tier in lookup.get(f"{task}|{risk}", []) else "not_qualified"})
    return {"routing_lookup": qualification.routing_lookup(cells), "cells": cells, "table_sha256": "synthetic"}


def view(fixture, tier, raw, evidence=None):
    record = {"fixture_id": fixture["fixture_id"], "task_class": fixture["task_class"],
              "risk_class": fixture["consequence_risk"], "model_tier": tier, "infrastructure_failure": "",
              "coding_execution_evidence": evidence, **qualification.collect_evaluation(fixture, raw, evidence)}
    return record


class CorpusConstructionTests(unittest.TestCase):
    def test_a_and_b_namespaces_and_call_ids_never_collide(self):
        a, b = contract.runtime_fixtures("A"), contract.runtime_fixtures("B")
        self.assertFalse(set(a) & set(b))
        self.assertTrue(all(k.startswith("A-") for k in a) and all(k.startswith("B-") for k in b))
        ca = {row.call_id for row in contract.build_schedule("A")}
        cb = {row.call_id for row in contract.build_schedule("B")}
        self.assertFalse(ca & cb)
        self.assertEqual((len(ca), len(cb)), (288, 144))

    def test_every_reference_answer_passes_and_every_gold_code_is_model_visible(self):
        profiles = contract.load_json(contract.PROMPT_PROFILES_PATH)["profiles"]
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                with self.subTest(fixture=fid):
                    raw = reference(fixture, gold)
                    evidence = run_isolated_fixture(fixture, raw) if fixture["validator_profile"] == "coding.v1" else None
                    self.assertTrue(validate_operational(fixture, raw, execution_evidence=evidence)["accepted"])
                    self.assertTrue(validate_fixture_output(fixture, gold, raw, execution_evidence=evidence)["hard_gate_pass"])
                    visible = profiles[fixture["validator_profile"]] + fixture["prompt"] + json.dumps(fixture["input"])
                    exp = gold["expected"]
                    codes = {"research.v1": lambda: [exp["recommendation"], *exp["uncertainties"]],
                             "synthesis.v1": lambda: [exp["conclusion"], *exp["roles"].values()],
                             "planning.v1": lambda: [s["action"] for s in exp["steps"]] + exp["uncertainties"]}
                    for code in codes.get(fixture["validator_profile"], lambda: [])():
                        self.assertIn(code, visible)

    def test_buggy_coding_sources_fail_their_own_tests(self):
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                if fixture["validator_profile"] != "coding.v1":
                    continue
                with self.subTest(fixture=fid):
                    try:
                        evidence = run_isolated_fixture(fixture, wrong(fixture, gold))
                        self.assertFalse(evidence["tests_pass"])
                    except ValueError:
                        pass

    def test_natural_correct_phrasings_are_accepted(self):
        """A correct answer must not fail on wording the model was never told to use."""
        cases = {
            ("B", "B-CONV-R3-2"): "Two databases verified, but the audit database failed with a checksum mismatch.",
            ("B", "B-CONV-R2-1"): "No, it expired in February, since the 12-month warranty started on 2031-02-10.",
            ("A", "A-CONV-R3-2"): "I can't send the list: there is no signed data processing agreement on file.",
        }
        for (corpus, fid), text in cases.items():
            fixture, gold = contract.indexed_fixture_gold(corpus)[fid]
            with self.subTest(fixture=fid):
                self.assertTrue(validate_fixture_output(fixture, gold, text)["hard_gate_pass"],
                                validate_fixture_output(fixture, gold, text)["reasons"])

    def test_single_defensible_conclusion_for_repaired_synthesis_fixtures(self):
        a_fixture, _ = contract.indexed_fixture_gold("A")["A-SYNTH-R1-1"]
        self.assertIn("because its battery reached 0%", json.dumps(a_fixture["input"]))
        b_fixture, _ = contract.indexed_fixture_gold("B")["B-SYNTH-R2-2"]
        self.assertIn("1.4 mm", json.dumps(b_fixture["input"]))

    def test_coding_prompts_disclose_the_operation_whitelist(self):
        for corpus in ("A", "B"):
            for fixture in contract.runtime_fixtures(corpus).values():
                if fixture["validator_profile"] == "coding.v1":
                    self.assertIn("startswith", fixture["prompt"])
                    self.assertIn("PurePosixPath", fixture["prompt"])

    def test_independence_audit_is_clean(self):
        from g_route3_independence import audit
        report = audit()
        self.assertTrue(report["valid"], report["findings"])
        self.assertEqual(report["cell_patterns_shared"], {})


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = contract.indexed_fixture_gold("B")
        cls.fx, cls.gold = cls.b["B-EXTRACT-R1-1"]

    def observer(self, outputs, seen):
        def observe(tier):
            seen.append(tier)
            return view(self.fx, tier, outputs[tier]) if tier in outputs else None
        return observe

    def test_b_gold_cannot_enter_routing_context(self):
        record = {**view(self.fx, "small", reference(self.fx, self.gold)),
                  "semantics": {"normalized_semantic_evaluation": {"hard_gate_pass": True}},
                  "gold_linkage": {"gold_id": "G-ROUTE3-GOLD-B"}}
        projected = routing.runtime_view(record)
        self.assertFalse(routing.FORBIDDEN_VIEW_KEYS & set(projected))
        with self.assertRaisesRegex(ValueError, "gold_leakage_into_routing"):
            routing.verdicts(self.fx, record, table_from({}))
        source = inspect.getsource(routing)
        for forbidden in ("load_gold", "gold_path", "indexed_fixture_gold", "attach_semantics", "hard_gate_pass"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("load_gold", inspect.getsource(runner._collect))

    def test_cheapest_qualified_tier_is_the_start(self):
        seen = []
        good = reference(self.fx, self.gold)
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["small", "mid", "large"]}),
                            self.observer({"small": good, "mid": good, "large": good}, seen))
        self.assertEqual((out["start_tier"], out["final_tier"], seen), ("small", "small", ["small"]))

    def test_unqualified_start_tier_is_never_contacted(self):
        seen = []
        good = reference(self.fx, self.gold)
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["mid", "large"]}),
                            self.observer({"small": good, "mid": good, "large": good}, seen))
        self.assertEqual(out["start_tier"], "mid")
        self.assertNotIn("small", seen)

    def test_unqualified_intermediate_tier_is_skipped(self):
        seen = []
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["small", "large"]}),
                            self.observer({"small": "{bad", "mid": reference(self.fx, self.gold),
                                           "large": reference(self.fx, self.gold)}, seen))
        self.assertEqual(seen, ["small", "large"])
        self.assertEqual((out["outcome"], out["final_tier"]), ("stopped", "large"))

    def test_qualified_intermediate_tier_is_not_skipped(self):
        seen = []
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["small", "mid", "large"]}),
                            self.observer({"small": "{bad", "mid": reference(self.fx, self.gold),
                                           "large": reference(self.fx, self.gold)}, seen))
        self.assertEqual(seen, ["small", "mid"])
        self.assertEqual(out["final_tier"], "mid")

    def test_no_qualified_model_makes_no_routing_contact(self):
        seen = []
        out = routing.route(self.fx, table_from({}), self.observer({"small": reference(self.fx, self.gold)}, seen))
        self.assertEqual((out["outcome"], seen, out["tiers_contacted"]), ("no_qualified_model", [], []))

    def test_accepted_output_from_unqualified_tier_cannot_stop(self):
        v = routing.runtime_view(view(self.fx, "small", reference(self.fx, self.gold)))
        verdict = routing.verdicts(self.fx, v, table_from({"structured_extraction|R1": ["mid"]}))
        self.assertTrue(verdict["output_accepted"])
        self.assertFalse(verdict["model_cell_qualified"])
        self.assertFalse(verdict["safe_to_stop_escalation"])

    def test_accepted_qualified_clean_output_can_stop_and_verdicts_stay_separate(self):
        v = routing.runtime_view(view(self.fx, "small", reference(self.fx, self.gold)))
        verdict = routing.verdicts(self.fx, v, table_from({"structured_extraction|R1": ["small"]}))
        self.assertEqual({k: verdict[k] for k in ("output_accepted", "model_cell_qualified", "safe_to_stop_escalation")},
                         {"output_accepted": True, "model_cell_qualified": True, "safe_to_stop_escalation": True})
        self.assertEqual(set(verdict) & {"output_accepted", "model_cell_qualified", "safe_to_stop_escalation"},
                         {"output_accepted", "model_cell_qualified", "safe_to_stop_escalation"})

    def test_failed_output_escalates_to_next_qualified_tier(self):
        seen = []
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["small", "mid"]}),
                            self.observer({"small": "{bad", "mid": reference(self.fx, self.gold)}, seen))
        self.assertTrue(out["escalated"])
        self.assertEqual(out["attempts"][0]["next_tier"], "mid")

    def test_no_higher_qualified_tier_fails_closed(self):
        seen = []
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["mid"]}),
                            self.observer({"small": reference(self.fx, self.gold), "mid": "{bad",
                                           "large": reference(self.fx, self.gold)}, seen))
        self.assertEqual((out["outcome"], out["final_tier"], seen), ("escalation_exhausted", None, ["mid"]))

    def test_r4_is_evidence_only_and_contacts_nothing(self):
        fx, gold = self.b["B-EXTRACT-R4-1"]
        seen = []
        out = routing.route(fx, table_from({"structured_extraction|R4": ["small"]}),
                            lambda tier: seen.append(tier))
        self.assertEqual((out["outcome"], seen), ("evidence_only", []))

    def test_every_retained_trigger_fires_and_retired_triggers_are_absent(self):
        fired = set()
        research, rgold = self.b["B-RESEARCH-R2-2"]
        empty = copy.deepcopy(rgold["expected"])
        empty["claims"][0]["citations"], empty["claims"][0]["lineages"] = [], []
        fired |= set(routing.triggers_for(research, routing.runtime_view(view(research, "small", json.dumps(empty)))))
        a_research, _ = contract.runtime_fixtures("A")["A-RESEARCH-R2-1"], None
        a_rgold = contract.indexed_fixture_gold("A")["A-RESEARCH-R2-1"][1]
        repeated = copy.deepcopy(a_rgold["expected"])
        repeated["claims"][1]["citations"] = ["S1", "S2"]
        repeated["claims"][1]["lineages"] = ["tallybook-marketing"]
        fired |= set(routing.triggers_for(a_research, routing.runtime_view(view(a_research, "small", json.dumps(repeated)))))
        blank = dict(self.gold["expected"])
        blank["plant"] = ""
        fired |= set(routing.triggers_for(self.fx, routing.runtime_view(view(self.fx, "small", json.dumps(blank)))))
        self.assertEqual(fired, set(routing.TRIGGERS))
        retired = contract.load_thresholds()["routing"]["retired_triggers"]
        self.assertIn("repeat_disagreement", retired)
        self.assertFalse(set(retired) & set(routing.TRIGGERS))


class QualificationTests(unittest.TestCase):
    def rows(self, n, correct=True):
        fx = contract.runtime_fixtures("A")
        ids = ["A-EXTRACT-R1-1", "A-EXTRACT-R1-2"]
        out = []
        for i in range(n):
            out.append({"fixture_id": ids[i % 2], "task_class": "structured_extraction", "risk_class": "R1",
                        "model_tier": "small", "model": "m", "returned_model": "m", "infrastructure_failure": "",
                        "normalized_operational_validation": {"accepted": True},
                        "semantics": {"normalized_semantic_evaluation": {"hard_gate_pass": correct},
                                      "normalized_false_clean": not correct}})
        return out

    def verdict(self, rows):
        return next(c for c in qualification.qualify(rows) if c["task_class"] == "structured_extraction"
                    and c["risk_class"] == "R1" and c["model_tier"] == "small")

    def test_missing_observations_cannot_qualify(self):
        self.assertEqual(self.verdict(self.rows(3))["verdict"], "insufficient_evidence")
        self.assertEqual(self.verdict(self.rows(4))["verdict"], "qualified")

    def test_vacuous_pass_is_impossible(self):
        cells = qualification.qualify([])
        self.assertTrue(all(c["verdict"] == "insufficient_evidence" for c in cells))
        self.assertEqual(qualification.routing_lookup(cells), {k: [] for k in qualification.routing_lookup(cells)})

    def test_one_failure_disqualifies(self):
        rows = self.rows(4)
        rows[3]["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"] = False
        self.assertEqual(self.verdict(rows)["verdict"], "not_qualified")

    def test_infrastructure_failure_makes_evidence_insufficient(self):
        rows = self.rows(4)
        rows[0]["infrastructure_failure"] = "timeout"
        self.assertEqual(self.verdict(rows)["verdict"], "insufficient_evidence")

    def test_pilot_scale_bound_is_reported_honestly(self):
        self.assertAlmostEqual(qualification.failure_rate_upper_bound(0, 4), 0.527129, places=4)
        self.assertEqual(self.verdict(self.rows(4))["failure_rate_upper_95"],
                         qualification.failure_rate_upper_bound(0, 4))

    def test_table_digest_mismatch_fails_closed(self):
        cells = qualification.qualify(self.rows(4))
        doc = qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                        audit=READY_AUDIT)
        self.assertTrue(qualification.verify_table(doc)["valid"])
        tampered = copy.deepcopy(doc)
        tampered["routing_lookup"]["structured_extraction|R2"] = ["small"]
        self.assertIn("table_digest_mismatch", qualification.verify_table(tampered)["reasons"])
        with self.assertRaises(ValueError):
            qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                      audit={"verdict": "REVISE"})

    def test_table_is_write_once(self):
        cells = qualification.qualify(self.rows(4))
        doc = qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                        audit=READY_AUDIT)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "table.json"
            qualification.freeze_table(doc, path)
            other = qualification.build_table(qualification.qualify(self.rows(3)), run_id="r",
                                              score_record_sha256="s", execution_freeze_binding="f", audit=READY_AUDIT)
            with self.assertRaisesRegex(FileExistsError, "already_frozen"):
                qualification.freeze_table(other, path)


class PipelineTests(unittest.TestCase):
    """End-to-end through the governed runner with synthetic providers."""

    @staticmethod
    def plan_a(fixture, tier):
        if tier == "small" and fixture["task_class"] in ("grounded_research_synthesis", "reflective_planning"):
            return "wrong"
        if tier == "large":
            return "fenced"
        return "correct"

    @staticmethod
    def plan_b(fixture, tier):
        if tier == "small" and fixture["task_class"] == "structured_extraction" and fixture["fixture_id"].endswith("-1"):
            return "malformed"
        if tier == "small" and fixture["task_class"] in ("ordinary_conversation", "grounded_research_synthesis"):
            return "wrong"
        if tier == "large" and fixture["task_class"] == "grounded_research_synthesis":
            return "nonhashable"
        return "fenced" if tier == "large" else "correct"

    def run_a(self, td):
        provider = Provider("A", self.plan_a)
        result = runner.execute_phase_a(provider_call=provider, model_receipts=receipts(), run_root=Path(td) / "a",
                                        run_id="a", synthetic_fixture=True)
        return provider, result

    def freeze(self, td, result_a):
        store = RouteRunStore(Path(td) / "a", "a", create=False)
        doc = qualification.build_table(result_a["score"]["cells"], run_id="a",
                                        score_record_sha256=store.score_record()["record_sha256"],
                                        execution_freeze_binding=runner._freeze_digest(), audit=READY_AUDIT)
        path = Path(td) / "QUALIFICATION_TABLE.json"
        qualification.freeze_table(doc, path)
        return doc, path

    def test_full_pipeline_boundary_arithmetic_and_denominators(self):
        with tempfile.TemporaryDirectory() as td:
            real_load_gold = contract.load_gold

            def guarded_gold(corpus):
                if corpus == "B":
                    raise AssertionError("corpus B gold loaded during phase A")
                return real_load_gold(corpus)

            with patch.object(contract, "load_gold", guarded_gold):
                provider_a, result_a = self.run_a(td)
            self.assertEqual(result_a["state"], "complete")
            self.assertEqual(len(provider_a.calls), 288)
            records_a = RouteRunStore(Path(td) / "a", "a", create=False).call_records()
            self.assertTrue(all(r["normalization"]["raw_output"] == r["raw_output"] for r in records_a))
            self.assertTrue(any(r["normalization"]["normalized"] for r in records_a))
            self.assertFalse(any("semantics" in r for r in records_a))

            with patch.object(runner, "QUALIFICATION_TABLE_PATH", Path(td) / "QUALIFICATION_TABLE.json"):
                with self.assertRaisesRegex(PermissionError, "qualification_table_not_frozen"):
                    runner.execute_phase_b(provider_call=Provider("B", self.plan_b), model_receipts=receipts(),
                                           run_root=Path(td) / "b", phase_a_root=Path(td) / "a",
                                           phase_a_run_id="a", synthetic_fixture=True)
                doc, path = self.freeze(td, result_a)
                lookup = doc["routing_lookup"]
                self.assertEqual(lookup["grounded_research_synthesis|R1"], ["mid", "large"])
                self.assertEqual(lookup["structured_extraction|R1"], ["small", "mid", "large"])

                provider_b = Provider("B", self.plan_b)
                result_b = runner.execute_phase_b(provider_call=provider_b, model_receipts=receipts(),
                                                  run_root=Path(td) / "b", phase_a_root=Path(td) / "a",
                                                  phase_a_run_id="a", synthetic_fixture=True)
            self.assertEqual(result_b["state"], "complete")
            self.assertTrue(result_b["terminal_views"]["valid"])
            report = result_b["score"]
            m = report["metrics"]
            self.assertEqual(m["validation_cases"], 48)
            self.assertEqual(m["r4_evidence_only_cases"], 12)
            self.assertEqual(m["eligible_cases"], 36)
            self.assertEqual(m["stops"] + m["no_qualified_model_cases"] + m["escalation_exhausted_cases"]
                             + m["r4_evidence_only_cases"], 48)
            self.assertEqual(m["routing_provider_calls"] + m["diagnostic_only_provider_calls"], 144)
            self.assertEqual(report["gates"]["unqualified_tier_terminal_results"]["observed"], 0)
            self.assertTrue(report["gates"]["denominator_integrity"]["observed"])
            self.assertGreater(m["successful_escalations"], 0)
            self.assertGreater(m["false_clean_outputs_caught_because_tier_unqualified"], 0)
            research = [d for d in report["decisions"] if d["task_class"] == "grounded_research_synthesis"
                        and d["risk_class"] != "R4"]
            self.assertTrue(research and all(d["start_tier"] == "mid" and "small" not in d["tiers_contacted"]
                                             for d in research))
            conversation_unsafe = [d for d in report["decisions"] if d["task_class"] == "ordinary_conversation"
                                   and d["outcome"] == "stopped" and d["final_tier"] == "small"]
            self.assertEqual(m["unsafe_stops"], len(conversation_unsafe))
            labels = report["generalization"]["label_counts"]
            self.assertGreater(labels.get("false_positive_qualification", 0), 0)
            self.assertEqual(report["table_sha256"], doc["table_sha256"])
            self.assertIn(report["primary_status"], ("PASS", "FAIL", "NOT_TESTABLE"))

    def test_table_mutation_after_phase_b_launch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            _, result_a = self.run_a(td)
            with patch.object(runner, "QUALIFICATION_TABLE_PATH", Path(td) / "QUALIFICATION_TABLE.json"):
                doc, path = self.freeze(td, result_a)
                ticks = {"n": 0}

                def control():
                    ticks["n"] += 1
                    if ticks["n"] == 3:
                        path.write_text(path.read_text(encoding="utf-8").replace('"small"', '"large"', 1),
                                        encoding="utf-8")
                    return "continue"

                with self.assertRaisesRegex(RuntimeError, "guarded_dependency_drift"):
                    runner.execute_phase_b(provider_call=Provider("B", self.plan_b), model_receipts=receipts(),
                                           run_root=Path(td) / "b", phase_a_root=Path(td) / "a", phase_a_run_id="a",
                                           synthetic_fixture=True, control=control)
            run_dir = next(p for p in (Path(td) / "b").iterdir() if p.is_dir())
            self.assertEqual(RouteRunStore(Path(td) / "b", run_dir.name, create=False).manifest()["state"],
                             "incomplete")

    def test_incomplete_phase_a_blocks_phase_b(self):
        with tempfile.TemporaryDirectory() as td:
            ticks = {"n": 0}

            def control():
                ticks["n"] += 1
                return "pause" if ticks["n"] == 5 else "continue"

            paused = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                            run_root=Path(td) / "a", run_id="a", synthetic_fixture=True,
                                            control=control)
            self.assertEqual(paused["state"], "paused")
            with patch.object(runner, "QUALIFICATION_TABLE_PATH", Path(td) / "QUALIFICATION_TABLE.json"):
                pre = runner.phase_b_preconditions(Path(td) / "a", "a")
                self.assertFalse(pre["valid"])

    def test_malformed_and_non_hashable_output_never_crash(self):
        def chaos(fixture, tier):
            return {"small": "malformed", "mid": "nonhashable", "large": "wrong"}[tier]
        with tempfile.TemporaryDirectory() as td:
            result = runner.execute_phase_a(provider_call=Provider("A", chaos), model_receipts=receipts(),
                                            run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
            self.assertEqual(result["state"], "complete")
            self.assertEqual(result["score"]["qualified_cells"], 0)

    def test_authorization_is_required_for_both_phases(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(PermissionError, "phase_a_not_authorized"):
                runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                       run_root=Path(td) / "a", run_id="a")
        self.assertFalse(runner.phase_a_authorized({}))
        self.assertFalse(runner.phase_b_authorized({}, Path("."), "none"))

    def test_model_binding_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "model_preflight_rejected"):
                runner.execute_phase_a(provider_call=Provider("A", self.plan_a),
                                       model_receipts=receipts(manifest_digest="0" * 64),
                                       run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)


class ValidationGateTests(unittest.TestCase):
    def test_an_empty_table_is_not_testable_rather_than_passing(self):
        records = []
        b = contract.indexed_fixture_gold("B")
        for fid, (fixture, gold) in b.items():
            for tier in contract.TIER_ORDER:
                raw = reference(fixture, gold)
                evidence = run_isolated_fixture(fixture, raw) if fixture["validator_profile"] == "coding.v1" else None
                records.append({"fixture_id": fid, "task_class": fixture["task_class"],
                                "risk_class": fixture["consequence_risk"], "model_tier": tier, "model": "m",
                                "returned_model": "m", "infrastructure_failure": "", "raw_output": raw,
                                "coding_execution_evidence": evidence,
                                **qualification.collect_evaluation(fixture, raw, evidence)})
        report = validation.score(records, table_from({}))
        self.assertEqual(report["primary_status"], "NOT_TESTABLE")
        self.assertEqual(report["metrics"]["stops"], 0)
        self.assertEqual(report["metrics"]["no_qualified_model_cases"], 36)


if __name__ == "__main__":
    unittest.main(verbosity=2)
