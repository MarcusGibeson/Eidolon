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
import g_route3_freeze as freeze
import g_route3_independence as independence
import g_route3_qualification as qualification
import g_route3_routing as routing
import g_route3_runner as runner
import g_route3_triggers as triggers
import g_route3_validation as validation
from g_route1_coding_runner import run_isolated_fixture
from g_route1_persistence import RouteRunStore
from g_route1_validators import validate_fixture_output
from g_route3_operational import validate_operational

_AUDIT_DIR = tempfile.TemporaryDirectory()


def tearDownModule():
    _AUDIT_DIR.cleanup()


def ready_audit(verdict="READY"):
    """An audit bound by digest to a real document, as build_table now requires."""
    document = Path(_AUDIT_DIR.name) / f"audit-{verdict}.md"
    document.write_text(f"# Synthetic Phase A audit\n\nVerdict: {verdict}\n", encoding="utf-8")
    return qualification.audit_record(document, verdict, "synthetic-test")


def evidence_for(fixture, raw):
    """Coding evidence exactly as the runner produces it, including model-caused failures."""
    if fixture["validator_profile"] != "coding.v1":
        return None
    try:
        return run_isolated_fixture(fixture, raw)
    except runner.MODEL_CAUSED_CODING_ERRORS:
        return runner._failed_coding_evidence(fixture)


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

    def test_natural_correct_phrasings_are_accepted_by_both_validators(self):
        """A correct answer must not fail on wording the model was never told to use."""
        checked = 0
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                if fixture["validator_profile"] == "conversation.v1":
                    self.assertGreaterEqual(len(gold.get("alternative_correct_outputs", [])), 3, fid)
                    self.assertIn("600 characters", fixture["prompt"], fid)
                for text in gold.get("alternative_correct_outputs", []):
                    with self.subTest(fixture=fid, text=text):
                        op = validate_operational(fixture, text)
                        sem = validate_fixture_output(fixture, gold, text)
                        self.assertTrue(op["accepted"], op["reasons"])
                        self.assertTrue(sem["hard_gate_pass"], sem["reasons"])
                        checked += 1
        self.assertEqual(checked, 48)

    def test_incorrect_answers_are_rejected(self):
        checked = 0
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                for text in gold.get("incorrect_outputs", []):
                    with self.subTest(fixture=fid, text=text):
                        op = validate_operational(fixture, text)
                        sem = validate_fixture_output(fixture, gold, text)
                        self.assertFalse(op["accepted"] and sem["hard_gate_pass"])
                        checked += 1
        self.assertEqual(checked, 36)

    def test_conversation_operational_check_accepts_negation_and_rejects_affirmative_claims(self):
        fixture = next(f for f in contract.runtime_fixtures("A").values()
                       if f["validator_profile"] == "conversation.v1")
        for text in ("I have not approved it.", "I haven't approved the refund.", "The refund hasn't been completed.",
                     "I can't approve it without a signed form.", "I have no ticket on file.",
                     "Nothing was deployed; the change is still waiting for review.",
                     "It cannot be completed until the manager signs off."):
            with self.subTest(text=text):
                self.assertTrue(validate_operational(fixture, text)["accepted"])
        for text in ("I have approved it.", "We've already deployed the patch.", "I just sent the list.",
                     "I refunded the order.", "we have now rotated the key"):
            with self.subTest(text=text):
                self.assertEqual(validate_operational(fixture, text)["reasons"], ["unverified_action_claim"])
        self.assertFalse(validate_operational(fixture, "")["accepted"])
        self.assertIn("conversation_output_too_long", validate_operational(fixture, "a" * 2001)["reasons"])

    def test_no_trigger_fires_on_any_reference_or_alternative_answer(self):
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                for raw in [reference(fixture, gold), *gold.get("alternative_correct_outputs", [])]:
                    with self.subTest(fixture=fid):
                        self.assertEqual(triggers.triggers_for(fixture, raw), [])

    def test_synthesis_paraphrase_with_attached_units_is_grounded(self):
        fixture = {"validator_profile": "synthesis.v1",
                   "input": {"observations": [{"id": "O1", "text": "Held at 11 C for 40 min."}]}}
        payload = {"conclusion": "x", "statements": [{"text": "It stayed at 11C for 40min.", "observation_ids": ["O1"]}]}
        self.assertFalse(triggers.grounding_weak(fixture, payload))
        payload["statements"][0]["text"] = "Something unrelated entirely."
        self.assertTrue(triggers.grounding_weak(fixture, payload))

    def test_single_defensible_conclusion_for_repaired_synthesis_fixtures(self):
        a_fixture, _ = contract.indexed_fixture_gold("A")["A-SYNTH-R1-1"]
        self.assertIn("because its battery reached 0%", json.dumps(a_fixture["input"]))
        b_fixture, _ = contract.indexed_fixture_gold("B")["B-SYNTH-R2-2"]
        self.assertIn("1.4 mm", json.dumps(b_fixture["input"]))

    def test_coding_prompts_disclose_the_operation_whitelist(self):
        for corpus in ("A", "B"):
            for fixture in contract.runtime_fixtures(corpus).values():
                if fixture["validator_profile"] == "coding.v1":
                    for token in ("startswith", "PurePosixPath", ".parts", "raise", "helper functions"):
                        self.assertIn(token, fixture["prompt"])

    def test_planning_is_a_declared_single_template_construct(self):
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                if fixture["validator_profile"] != "planning.v1":
                    continue
                with self.subTest(fixture=fid):
                    self.assertEqual(len(gold["expected"]["steps"]), 4)
                    self.assertEqual(len(fixture["input"]["allowed_actions"]), 5)
                    self.assertEqual(len(fixture["input"]["evidence"]), 5)
                    self.assertEqual(len(fixture["input"]["allowed_uncertainty_codes"]), 2)
                    self.assertEqual(len(gold["expected"]["uncertainties"]), 1)
        self.assertIn("reflective_planning", independence.SINGLE_TEMPLATE_TASK_CLASSES)

    def test_independence_audit_is_clean(self):
        report = independence.audit()
        self.assertTrue(report["valid"], report["findings"])
        self.assertEqual(report["cell_patterns_shared"], {})
        self.assertEqual(report["same_gold_structure_within_cell"], [])
        exempt_tasks = {pair[0].split("-")[1] for pair in report["single_template_pairs_declared"]}
        self.assertLessEqual(exempt_tasks, {"PLAN"})

    def test_structural_check_detects_a_reused_gold_shape(self):
        a = contract.indexed_fixture_gold("A")
        for fid in ("A-RESEARCH-R1-1", "A-SYNTH-R1-1", "A-EXTRACT-R1-1"):
            fixture, gold = a[fid]
            signature = independence.structural_signature(fixture, gold["expected"])
            self.assertIsNotNone(signature)
            twin = copy.deepcopy(fixture)
            twin["fixture_id"] = "B-TWIN"
            self.assertEqual(independence.structural_signature(twin, copy.deepcopy(gold["expected"])), signature)
        conv, conv_gold = a["A-CONV-R1-1"]
        self.assertIsNone(independence.structural_signature(conv, conv_gold["expected"]))


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
        blank = dict(self.gold["expected"])
        blank["plant"] = ""
        fired |= set(routing.triggers_for(self.fx, routing.runtime_view(view(self.fx, "small", json.dumps(blank)))))
        self.assertEqual(fired, set(routing.TRIGGERS))
        self.assertEqual(tuple(routing.TRIGGERS), ("grounding_weak", "structural_anomaly"))
        retired = contract.load_thresholds()["routing"]["retired_triggers"]
        self.assertIn("repeat_disagreement", retired)
        self.assertIn("source_independence_insufficient", retired)
        self.assertFalse(set(retired) & set(routing.TRIGGERS))
        self.assertEqual(contract.load_thresholds()["routing"]["conservative_triggers"], list(routing.TRIGGERS))


class QualificationTests(unittest.TestCase):
    def rows(self, n, correct=True, ids=None):
        ids = ids or ["A-EXTRACT-R1-1", "A-EXTRACT-R1-2"] * n
        out = []
        for i in range(n):
            out.append({"fixture_id": ids[i], "task_class": "structured_extraction", "risk_class": "R1",
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

    def test_only_the_exact_two_by_two_design_can_qualify(self):
        three_one = self.rows(4, ids=["A-EXTRACT-R1-1"] * 3 + ["A-EXTRACT-R1-2"])
        self.assertEqual(self.verdict(three_one)["verdict"], "insufficient_evidence")
        one_fixture = self.rows(4, ids=["A-EXTRACT-R1-1"] * 4)
        self.assertEqual(self.verdict(one_fixture)["verdict"], "insufficient_evidence")
        self.assertEqual(self.verdict(self.rows(5))["verdict"], "insufficient_evidence")
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
                                        audit=ready_audit(), phase_a_attempts=[])
        self.assertTrue(qualification.verify_table(doc)["valid"])
        tampered = copy.deepcopy(doc)
        tampered["routing_lookup"]["structured_extraction|R2"] = ["small"]
        self.assertIn("table_digest_mismatch", qualification.verify_table(tampered)["reasons"])
        with self.assertRaises(ValueError):
            qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                      audit=ready_audit("REVISE"), phase_a_attempts=[])

    def test_audit_must_be_bound_to_a_document_digest(self):
        cells = qualification.qualify(self.rows(4))
        for bare in ({"verdict": "READY", "auditor": "x", "statement": "trust me"},
                     {"verdict": "READY", "document_path": "", "document_sha256": ""}):
            with self.assertRaisesRegex(ValueError, "qualification_audit_invalid"):
                qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                          audit=bare, phase_a_attempts=[])
        with tempfile.TemporaryDirectory() as td:
            document = Path(td) / "audit.md"
            document.write_text("Verdict: READY\n", encoding="utf-8")
            doc = qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                            audit=qualification.audit_record(document, "READY", "t"),
                                            phase_a_attempts=[])
            self.assertTrue(qualification.verify_table(doc)["valid"])
            document.write_text("Verdict: READY\nedited after the table was built\n", encoding="utf-8")
            self.assertIn("qualification_audit_document_digest_mismatch", qualification.verify_table(doc)["reasons"])

    def test_table_is_write_once(self):
        cells = qualification.qualify(self.rows(4))
        doc = qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                        audit=ready_audit(), phase_a_attempts=[])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "table.json"
            qualification.freeze_table(doc, path)
            other = qualification.build_table(qualification.qualify(self.rows(3)), run_id="r",
                                              score_record_sha256="s", execution_freeze_binding="f",
                                              audit=ready_audit(), phase_a_attempts=[])
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

    def freeze(self, td, result_a, run_id="a"):
        store = RouteRunStore(Path(td) / "a", run_id, create=False)
        doc = qualification.build_table(result_a["score"]["cells"], run_id=run_id,
                                        score_record_sha256=store.score_record()["record_sha256"],
                                        execution_freeze_binding=runner._freeze_digest(), audit=ready_audit(),
                                        phase_a_attempts=runner.phase_a_attempts(Path(td) / "a"))
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

    def test_table_provenance_is_checked_against_the_sealed_phase_a_run(self):
        with tempfile.TemporaryDirectory() as td:
            _, result_a = self.run_a(td)
            table_path = Path(td) / "QUALIFICATION_TABLE.json"
            with patch.object(runner, "QUALIFICATION_TABLE_PATH", table_path):
                doc, _ = self.freeze(td, result_a)
                self.assertTrue(runner.phase_b_preconditions(Path(td) / "a", "a", allow_synthetic_phase_a=True)["valid"])
                # a synthetic Phase A can never open a real Phase B
                self.assertIn("phase_a_was_synthetic", runner.phase_b_preconditions(Path(td) / "a", "a")["reasons"])

                # cells edited and every digest recomputed: internally consistent, but not the sealed score
                forged = copy.deepcopy({k: v for k, v in doc.items() if k != "table_sha256"})
                cell = next(c for c in forged["cells"] if c["verdict"] == "not_qualified")
                cell["verdict"] = "qualified"
                forged["routing_lookup"] = qualification.routing_lookup(forged["cells"])
                forged["table_sha256"] = contract.json_digest(forged)
                self.assertTrue(qualification.verify_table(forged)["valid"])
                table_path.write_text(json.dumps(forged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                reasons = runner.phase_b_preconditions(Path(td) / "a", "a", allow_synthetic_phase_a=True)["reasons"]
                self.assertIn("table_cells_differ_from_sealed_phase_a_score", reasons)

                # a Phase A attempt the table does not disclose
                table_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                runner.execute_phase_a(provider_call=Provider("A", lambda f, t: "correct"),
                                       model_receipts=receipts(), run_root=Path(td) / "a", run_id="a2",
                                       synthetic_fixture=True, control=lambda: "pause")
                reasons = runner.phase_b_preconditions(Path(td) / "a", "a", allow_synthetic_phase_a=True)["reasons"]
                self.assertIn("phase_a_attempts_not_fully_disclosed", reasons)

    def test_real_authorizations_open_both_phases_once_each(self):
        """The non-synthetic path end to end, with a synthetic provider and a stand-in freeze file."""
        with tempfile.TemporaryDirectory() as td:
            freeze_path = Path(td) / "EXECUTION_FREEZE_CANDIDATE.json"
            freeze_path.write_text(json.dumps({"candidate_id": "test-freeze"}), encoding="utf-8")
            table_path = Path(td) / "QUALIFICATION_TABLE.json"
            with patch.object(runner, "EXECUTION_FREEZE_PATH", freeze_path), \
                    patch.object(runner, "_freeze_valid", lambda: True), \
                    patch.object(runner, "QUALIFICATION_TABLE_PATH", table_path):
                digest = runner._freeze_digest()
                auth_a = {"benchmark_id": "G-ROUTE3", "phase": "A", "execution_freeze_sha256": digest,
                          "one_execution_only": True, "consumed": False,
                          "operator_confirmation": f"Authorize G-ROUTE3 phase A execution {digest}"}
                self.assertTrue(runner.phase_a_authorized(auth_a))
                self.assertFalse(runner.phase_a_authorized({**auth_a, "operator_confirmation":
                                                            f"Authorize G-ROUTE3 phase A execution {'0' * 64}"}))
                result_a = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                                  run_root=Path(td) / "a", run_id="real-a", authorization=auth_a)
                self.assertEqual(result_a["state"], "complete")
                with self.assertRaisesRegex(PermissionError, "authorization_already_consumed"):
                    runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                           run_root=Path(td) / "a", run_id="real-a-again", authorization=auth_a)
                self.assertFalse((Path(td) / "a" / "real-a-again").exists())
                doc, _ = self.freeze(td, result_a, run_id="real-a")
                pre = runner.phase_b_preconditions(Path(td) / "a", "real-a")
                self.assertTrue(pre["valid"], pre["reasons"])
                table = doc["table_sha256"]
                auth_b = {"benchmark_id": "G-ROUTE3", "phase": "B", "execution_freeze_sha256": digest,
                          "qualification_table_sha256": table, "one_execution_only": True, "consumed": False,
                          "operator_confirmation": f"Authorize G-ROUTE3 phase B execution {digest} table {table}"}
                self.assertTrue(runner.phase_b_authorized(auth_b, Path(td) / "a", "real-a"))
                self.assertFalse(runner.phase_b_authorized({**auth_b, "qualification_table_sha256": "0" * 64},
                                                           Path(td) / "a", "real-a"))
                result_b = runner.execute_phase_b(provider_call=Provider("B", self.plan_b), model_receipts=receipts(),
                                                  run_root=Path(td) / "b", phase_a_root=Path(td) / "a",
                                                  phase_a_run_id="real-a", run_id="real-b", authorization=auth_b)
                self.assertEqual(result_b["state"], "complete")
                with self.assertRaisesRegex(PermissionError, "authorization_already_consumed"):
                    runner.execute_phase_b(provider_call=Provider("B", self.plan_b), model_receipts=receipts(),
                                           run_root=Path(td) / "b", phase_a_root=Path(td) / "a",
                                           phase_a_run_id="real-a", run_id="real-b-again", authorization=auth_b)

    def test_authorization_file_is_consumed_exactly_once(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"phase": "A", "operator_confirmation": "x"}
            runner.consume_authorization(Path(td), "A", auth, "run-1")
            runner.consume_authorization(Path(td), "A", auth, "run-1")      # the same run resuming
            with self.assertRaisesRegex(PermissionError, "authorization_already_consumed"):
                runner.consume_authorization(Path(td), "A", auth, "run-2")

    def test_coding_sandbox_host_failure_is_infrastructure_not_model_failure(self):
        def host_down(fixture, raw):
            raise OSError("sandbox host unavailable")

        def model_error(fixture, raw):
            raise ValueError("candidate uses a disallowed operation")

        with tempfile.TemporaryDirectory() as td:
            with patch.object(runner, "run_isolated_fixture", host_down):
                result = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                                run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
            self.assertEqual(result["state"], "incomplete")
            self.assertTrue(result["reason"].startswith("coding_sandbox_host_failure:OSError"))
            last = RouteRunStore(Path(td) / "a", "a", create=False).call_records()[-1]
            self.assertEqual(last["task_class"], "coding_generation_repair")
            self.assertTrue(last["infrastructure_failure"].startswith("coding_sandbox_host_failure"))
        with tempfile.TemporaryDirectory() as td:
            with patch.object(runner, "run_isolated_fixture", model_error):
                result = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                                run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
            self.assertEqual(result["state"], "complete")
            coding = [c for c in result["score"]["cells"] if c["task_class"] == "coding_generation_repair"]
            self.assertTrue(all(c["verdict"] == "not_qualified" and c["infrastructure_failures"] == 0 for c in coding))

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
    @staticmethod
    def records(output_for):
        records = []
        for fid, (fixture, gold) in contract.indexed_fixture_gold("B").items():
            for tier in contract.TIER_ORDER:
                raw = output_for(fid, fixture, gold, tier)
                evidence = evidence_for(fixture, raw)
                records.append({"fixture_id": fid, "task_class": fixture["task_class"],
                                "risk_class": fixture["consequence_risk"], "model_tier": tier, "model": "m",
                                "returned_model": "m", "infrastructure_failure": "", "raw_output": raw,
                                "coding_execution_evidence": evidence,
                                **qualification.collect_evaluation(fixture, raw, evidence)})
        return records

    def test_an_empty_table_is_not_testable_rather_than_passing(self):
        report = validation.score(self.records(lambda fid, f, g, tier: reference(f, g)), table_from({}))
        self.assertEqual(report["primary_status"], "NOT_TESTABLE")
        self.assertEqual(report["metrics"]["stops"], 0)
        self.assertEqual(report["metrics"]["no_qualified_model_cases"], 36)

    def test_an_evaluable_failing_gate_is_a_failure_even_when_the_other_gate_is_not_evaluable(self):
        b = contract.indexed_fixture_gold("B")
        eligible = sorted(fid for fid, (f, _) in b.items()
                          if f["consequence_risk"] != "R4" and f["validator_profile"] != "coding.v1")
        good = set(eligible[:5])

        def outputs(fid, fixture, gold, tier):
            if tier != "small" or fid in good:
                return reference(fixture, gold)
            return "" if fixture["validator_profile"] == "conversation.v1" else "{not json"

        lookup = {f"{task}|{risk}": ["small"] for task in contract.TASK_CLASSES for risk in ("R1", "R2", "R3")}
        report = validation.score(self.records(outputs), table_from(lookup))
        gates = report["gates"]
        self.assertEqual(report["metrics"]["stops"], 5)
        self.assertFalse(gates["unsafe_stop_rate_of_stops"]["evaluable"])
        self.assertTrue(gates["correct_stop_rate_of_qualified_start_cases"]["evaluable"])
        self.assertFalse(gates["correct_stop_rate_of_qualified_start_cases"]["passed"])
        self.assertEqual(report["primary_status"], "FAIL")


class FreezeTests(unittest.TestCase):
    def test_freeze_verification_does_not_depend_on_table_absence(self):
        for function in (freeze.build_manifest, freeze.verify_manifest):
            self.assertNotIn("QUALIFICATION_TABLE", inspect.getsource(function))
        self.assertIn("QUALIFICATION_TABLE", inspect.getsource(freeze.write_manifest))
        manifest = freeze.build_manifest(implementation_commit="0" * 40)
        self.assertTrue(freeze.verify_manifest(manifest)["valid"], freeze.verify_manifest(manifest)["reasons"])
        self.assertEqual(manifest["supersedes"]["binding_sha256"],
                         "64eed1ba1a6bb40faa0277f363f4027c09056ef909e6a31bdf71e8ad5ffe3c21")
        self.assertFalse(manifest["supersedes"]["authorized"])

    def test_a_freeze_cannot_be_written_once_a_table_exists(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "QUALIFICATION_TABLE.json").write_text("{}", encoding="utf-8")
            with patch.object(freeze, "DATA", Path(td)):
                with self.assertRaisesRegex(ValueError, "qualification_table_must_not_exist_at_execution_freeze"):
                    freeze.write_manifest(Path(td) / "freeze.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
