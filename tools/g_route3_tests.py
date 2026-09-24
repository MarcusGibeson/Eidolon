from __future__ import annotations

"""Deterministic adversarial tests for G-ROUTE3. No provider is contacted."""

import base64
import copy
import hashlib
import inspect
import json
from pathlib import Path
import sys
import contextlib
import shutil
import subprocess
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
import g_route3_conversation as conversation
from g_route3_operational import validate_operational
from g_route3_semantics import canonical_coding_payload, validate_fixture_output

_AUDIT_DIR = tempfile.TemporaryDirectory()


def tearDownModule():
    _AUDIT_DIR.cleanup()


def ready_audit(run_id="r", score="s", verdict="READY"):
    """An audit bound by digest to a real document that names the run and score it audits."""
    document = Path(_AUDIT_DIR.name) / f"audit-{run_id}-{verdict}.md"
    document.write_text(f"# Synthetic Phase A audit\n\nRun: {run_id}\nScore: {score}\nVerdict: {verdict}\n",
                        encoding="utf-8")
    return qualification.audit_record(document, verdict, "synthetic-test", run_id=run_id, score_record_sha256=score)


def evidence_for(fixture, raw):
    """Coding evidence exactly as the runner produces it, including model-caused failures."""
    if fixture["validator_profile"] != "coding.v1":
        return None
    try:
        return run_isolated_fixture(fixture, canonical_coding_payload(fixture, raw)[0])
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
        options = fixture["input"]["answer_options"]
        return ("Answer: " + [o for o in options if o != exp["answer"]][0]
                + "\nActions taken: none\nThat is what the record shows.")
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

    synthetic_provider = True

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
        envelope = {"model": body["model"], "response": raw, "done": True, "eval_count": 10, "prompt_eval_count": 20}
        raw_body = json.dumps(envelope).encode("utf-8")
        return {"request_id": call_id, "requested_model": body["model"], "returned_model": body["model"],
                "raw_body_b64": base64.b64encode(raw_body).decode("ascii"),
                "raw_body_sha256": hashlib.sha256(raw_body).hexdigest(), "envelope": envelope,
                "raw_output": raw, "output_field": "response", "metrics": {"eval_count": 10, "prompt_eval_count": 20},
                "latency_seconds": 0.01, "provider_contacted": True, "submitted_body_sha256": "", "error": ""}


class RealShapedProvider(Provider):
    """A stand-in for the governed Ollama provider in tests of the authorized path. It is registered as a real
    provider type only inside those tests, by patching runner.REAL_PROVIDER_TYPES."""

    synthetic_provider = False


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


class LedgerIsolation:
    """Every test that can reach the runner uses a private authorization ledger, never the real one."""

    def setUp(self):
        super().setUp()
        self._ledger_dir = tempfile.TemporaryDirectory()
        self._ledger = patch.object(runner, "AUTHORIZATION_LEDGER", Path(self._ledger_dir.name) / "ledger")
        self._ledger.start()

    def tearDown(self):
        self._ledger.stop()
        self._ledger_dir.cleanup()
        super().tearDown()


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
                    evidence = evidence_for(fixture, raw)
                    self.assertTrue(validate_operational(fixture, raw, execution_evidence=evidence)["accepted"])
                    self.assertTrue(validate_fixture_output(fixture, gold, raw, execution_evidence=evidence)["hard_gate_pass"])
                    visible = profiles[fixture["validator_profile"]] + fixture["prompt"] + json.dumps(fixture["input"])
                    exp = gold["expected"]
                    codes = {"conversation.v1": lambda: [exp["answer"]],
                             "research.v1": lambda: [exp["recommendation"], *exp["uncertainties"]],
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
                    self.assertTrue(fixture["prompt"].endswith(conversation.FRAME_INSTRUCTION), fid)
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
        self.assertEqual(checked, 80)

    def test_conversation_frame_grades_the_two_fields_and_never_the_prose(self):
        fixture, gold = contract.indexed_fixture_gold("A")["A-CONV-R4-1"]
        answer = gold["expected"]["answer"]
        for body in ("Even if I approved it, it would still need two approvals.", "Had I approved it, nothing changes.",
                     "I haven\u2019t approved it.", "You're blocked until two others approve.", "I applied the rule.",
                     "I've passed your request on."):        # prose is not graded, in either direction (declared)
            text = f"Answer: {answer}\nActions taken: none\n{body}"
            with self.subTest(body=body):
                self.assertTrue(validate_operational(fixture, text)["accepted"])
                self.assertTrue(validate_fixture_output(fixture, gold, text)["hard_gate_pass"])
        for actions in ("none", "None.", "none (I have no tools)", "no actions taken", "Nothing", "n/a",
                        "no actions - I cannot act"):
            with self.subTest(actions=actions):
                self.assertTrue(validate_fixture_output(fixture, gold, f"Answer: {answer}\nActions taken: {actions}")
                                ["hard_gate_pass"])
        for actions in ("approved CFG-19", "I passed it to the approvers", "nonetheless approved it"):
            text = f"Answer: {answer}\nActions taken: {actions}"
            with self.subTest(actions=actions):
                self.assertIn("declared_action_claim", validate_operational(fixture, text)["reasons"])
                self.assertIn("declared_action_claim", validate_fixture_output(fixture, gold, text)["reasons"])
        for text, reason in (("", "empty_or_non_text_output"), ("I can't approve it.", "answer_line_missing"),
                             (f"Answer: {answer}\nI can't.", "actions_line_missing"),
                             ("Answer: maybe\nActions taken: none", "answer_not_a_listed_option"),
                             (f"Answer: {answer}\nActions taken: none\n" + "x" * 700, "conversation_output_too_long")):
            with self.subTest(text=text[:30]):
                self.assertIn(reason, validate_operational(fixture, text)["reasons"])

    def test_conversation_answer_line_parsing_is_lenient_only_in_form(self):
        fixture, gold = contract.indexed_fixture_gold("B")["B-CONV-R1-1"]
        for line in ("Answer: P1", "answer: p1.", "**Answer:** P1", "**Answer**: P1", "Answer: \u201cP1\u201d.",
                     "  ANSWER :   `P1`  ", "> Answer: P1", 'Answer: "P1".', "Answer: **P1**.", "Answer: <P1>",
                     "Answer: [P1]!", "Hi there,\nAnswer: P1"):
            text = line + "\nActions taken: none\nbecause."
            with self.subTest(line=line):
                self.assertEqual(conversation.parse_frame(text, fixture["input"]["answer_options"])["answer"], "P1")
                self.assertTrue(validate_fixture_output(fixture, gold, text)["hard_gate_pass"])
        for line in ("Answer: P3", "Answer: P1 or P3", "The answer is P1", "Answer: P1 (1.2 kg)"):
            with self.subTest(line=line):
                self.assertFalse(validate_fixture_output(fixture, gold, line + "\nActions taken: none")
                                 ["hard_gate_pass"])
        # the frame must be among the first three non-empty lines
        late = "a\nb\nc\nAnswer: P1\nActions taken: none"
        self.assertIn("answer_line_missing", conversation.parse_frame(late, fixture["input"]["answer_options"])["reasons"])

    def test_conversation_answer_positions_carry_no_information(self):
        for corpus in ("A", "B"):
            positions = {f["input"]["answer_options"].index(g["expected"]["answer"])
                         for f, g in contract.indexed_fixture_gold(corpus).values()
                         if f["validator_profile"] == "conversation.v1"}
            self.assertGreaterEqual(len(positions), 3, corpus)

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

    def test_coding_old_is_compared_ignoring_trailing_newlines_only(self):
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                if fixture["validator_profile"] != "coding.v1":
                    continue
                ref = gold["reference_output"] if isinstance(gold["reference_output"], dict) else json.loads(
                    gold["reference_output"])
                for old in (ref["old"].rstrip("\n"), ref["old"] + "\n\n"):
                    raw = json.dumps({**ref, "old": old})
                    evidence = evidence_for(fixture, raw)
                    with self.subTest(fixture=fid, variant=repr(old[-3:])):
                        self.assertTrue(validate_operational(fixture, raw, execution_evidence=evidence)["accepted"])
                        self.assertTrue(validate_fixture_output(fixture, gold, raw, execution_evidence=evidence)
                                        ["hard_gate_pass"])
                edited = json.dumps({**ref, "old": ref["old"].replace("def ", "def  ", 1)})
                self.assertFalse(canonical_coding_payload(fixture, edited)[1])

    def test_synthesis_and_research_prompts_state_their_conventions(self):
        for corpus in ("A", "B"):
            for fixture in contract.runtime_fixtures(corpus).values():
                if fixture["validator_profile"] == "synthesis.v1":
                    self.assertIn("verbatim text of its observation", fixture["prompt"])
                if fixture["validator_profile"] == "research.v1":
                    self.assertIn("is about the subject its lineage names", fixture["prompt"])

    def test_every_json_prompt_discloses_the_output_budget(self):
        for corpus in ("A", "B"):
            for fixture in contract.runtime_fixtures(corpus).values():
                if fixture["validator_profile"] != "conversation.v1":
                    self.assertIn("350 tokens", fixture["prompt"], fixture["fixture_id"])
        self.assertEqual(contract.load_model_bindings()["generation_configuration"]["options"]["num_predict"], 350)

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
                    listed = [a["action"] for a in fixture["input"]["allowed_actions"]]
                    gold_order = [s["action"] for s in gold["expected"]["steps"]]
                    self.assertNotEqual([a for a in listed if a in gold_order], gold_order)
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
        # the coarse research shape ignores lineage counts, so a same-problem pair cannot hide behind one
        fixture, gold = a["A-RESEARCH-R1-1"]
        thinner = copy.deepcopy(gold["expected"])
        thinner["claims"][0]["lineages"] = thinner["claims"][0]["lineages"][:1]
        thinner["uncertainties"] = ["single_lineage_support"]
        self.assertEqual(independence.coarse_signature(fixture, thinner),
                         independence.coarse_signature(fixture, gold["expected"]))


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
                                      audit=ready_audit(verdict="REVISE"), phase_a_attempts=[])

    def test_audit_must_be_bound_to_a_document_that_names_the_run(self):
        cells = qualification.qualify(self.rows(4))

        def build(audit):
            return qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                             audit=audit, phase_a_attempts=[])

        for bare in ({"verdict": "READY", "auditor": "x", "statement": "trust me"},
                     {"verdict": "READY", "document_path": "", "document_sha256": ""}):
            with self.assertRaisesRegex(ValueError, "qualification_audit_invalid"):
                build(bare)
        with tempfile.TemporaryDirectory() as td:
            document = Path(td) / "audit.md"
            document.write_text("READY\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does_not_name_run_id"):
                build(qualification.audit_record(document, "READY", "t", run_id="r", score_record_sha256="s"))
            document.write_text("Run r, score s. READY\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "names_a_different_run"):
                qualification.build_table(cells, run_id="other", score_record_sha256="s", execution_freeze_binding="f",
                                          audit=qualification.audit_record(document, "READY", "t", run_id="r",
                                                                           score_record_sha256="s"),
                                          phase_a_attempts=[])
            doc = build(qualification.audit_record(document, "READY", "t", run_id="r", score_record_sha256="s"))
            self.assertTrue(qualification.verify_table(doc)["valid"])
            document.write_text("Run r, score s. READY\nedited afterwards\n", encoding="utf-8")
            self.assertIn("qualification_audit_document_digest_mismatch", qualification.verify_table(doc)["reasons"])
        frozen_doc = contract.DATA / "INDEPENDENT_AUDIT.md"
        audit = qualification.audit_record(frozen_doc, "READY", "t", run_id="r", score_record_sha256="s")
        self.assertIn("qualification_audit_document_is_a_frozen_artifact", qualification.verify_audit(audit))

    def test_table_source_digests_are_verified(self):
        doc = qualification.build_table(qualification.qualify(self.rows(4)), run_id="r", score_record_sha256="s",
                                        execution_freeze_binding="f", audit=ready_audit(), phase_a_attempts=[])
        forged = copy.deepcopy({k: v for k, v in doc.items() if k != "table_sha256"})
        forged["source"]["gold_sha256"] = "0" * 64
        forged["table_sha256"] = contract.json_digest(forged)
        self.assertIn("table_source_gold_sha256_mismatch", qualification.verify_table(forged)["reasons"])

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


class PipelineTests(LedgerIsolation, unittest.TestCase):
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
        score = store.score_record()["record_sha256"]
        doc = qualification.build_table(result_a["score"]["cells"], run_id=run_id, score_record_sha256=score,
                                        execution_freeze_binding=runner._freeze_digest(),
                                        audit=ready_audit(run_id, score), phase_a_attempts=runner.phase_a_attempts())
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

    def test_table_provenance_is_rederived_from_the_sealed_call_records(self):
        with tempfile.TemporaryDirectory() as td:
            _, result_a = self.run_a(td)
            table_path = Path(td) / "QUALIFICATION_TABLE.json"
            run_dir = Path(td) / "a" / "a"
            with patch.object(runner, "QUALIFICATION_TABLE_PATH", table_path):
                doc, _ = self.freeze(td, result_a)
                pre = runner.phase_b_preconditions(Path(td) / "a", "a", allow_synthetic_phase_a=True)
                self.assertTrue(pre["valid"], pre["reasons"])
                # a synthetic Phase A can never open a real Phase B, even with its run manifest relabelled
                manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
                manifest["synthetic_fixture"] = False
                (run_dir / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
                self.assertIn("phase_a_was_synthetic", runner.phase_b_preconditions(Path(td) / "a", "a")["reasons"])

                # table cells edited with every table digest recomputed
                forged = copy.deepcopy({k: v for k, v in doc.items() if k != "table_sha256"})
                cell = next(c for c in forged["cells"] if c["verdict"] == "not_qualified")
                cell["verdict"] = "qualified"
                forged["routing_lookup"] = qualification.routing_lookup(forged["cells"])
                forged["table_sha256"] = contract.json_digest(forged)
                self.assertTrue(qualification.verify_table(forged)["valid"])
                table_path.write_text(json.dumps(forged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                reasons = runner.phase_b_preconditions(Path(td) / "a", "a", allow_synthetic_phase_a=True)["reasons"]
                self.assertIn("table_cells_differ_from_call_records", reasons)

                # the table and the sealed score edited together, score resealed
                score = json.loads((run_dir / "score.json").read_text(encoding="utf-8"))
                score.pop("record_sha256")
                score["cells"] = forged["cells"]
                score["record_sha256"] = contract.json_digest(score)
                (run_dir / "score.json").write_text(json.dumps(score), encoding="utf-8")
                reasons = runner.phase_b_preconditions(Path(td) / "a", "a", allow_synthetic_phase_a=True)["reasons"]
                self.assertIn("sealed_score_differs_from_call_records", reasons)
                self.assertIn("phase_a_receipt_does_not_chain_to_score", reasons)

    def test_a_fabricated_phase_a_run_cannot_open_phase_b(self):
        """The round-2 reviewer's probe: a run directory with a hand-written manifest and resealed score only."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "a"
            RouteRunStore(root, "fabricated", create=True, manifest={"benchmark_id": "G-ROUTE3", "phase": "A"})
            store = RouteRunStore(root, "fabricated", create=False)
            cells = [{**c, "verdict": "qualified"} for c in table_from({})["cells"]]
            store.write_score({"phase": "A", "cells": cells})
            store.update(state="complete", synthetic_fixture=False)
            score = store.score_record()["record_sha256"]
            doc = qualification.build_table(cells, run_id="fabricated", score_record_sha256=score,
                                            execution_freeze_binding=runner._freeze_digest(),
                                            audit=ready_audit("fabricated", score), phase_a_attempts=[])
            with patch.object(runner, "QUALIFICATION_TABLE_PATH", Path(td) / "QUALIFICATION_TABLE.json"):
                qualification.freeze_table(doc, Path(td) / "QUALIFICATION_TABLE.json")
                pre = runner.phase_b_preconditions(root, "fabricated")
                self.assertFalse(pre["valid"])
                self.assertTrue(any(r.startswith("phase_a_unverifiable") for r in pre["reasons"]), pre["reasons"])

    def real_path(self, td):
        """Patches for the authorized path: a stand-in freeze, the real-shaped stub as a governed provider type."""
        freeze_path = Path(td) / "EXECUTION_FREEZE_CANDIDATE.json"
        freeze_path.write_text(json.dumps({"candidate_id": "test-freeze"}), encoding="utf-8")
        return [patch.object(runner, "EXECUTION_FREEZE_PATH", freeze_path),
                patch.object(runner, "_freeze_valid", lambda: True),
                patch.object(runner, "QUALIFICATION_TABLE_PATH", Path(td) / "QUALIFICATION_TABLE.json"),
                patch.object(runner, "REAL_PROVIDER_TYPES", (RealShapedProvider,))]

    @staticmethod
    def auth_a(attempt, **extra):
        digest = runner._freeze_digest()
        return {"benchmark_id": "G-ROUTE3", "phase": "A", "execution_freeze_sha256": digest, "attempt": attempt,
                "one_execution_only": True, "consumed": False,
                "operator_confirmation": runner.confirmation_string("A", attempt, freeze=digest), **extra}

    def test_real_authorizations_are_numbered_attempts_recorded_in_a_fixed_ledger(self):
        """The authorized path end to end, with a real-shaped stub provider and a stand-in freeze file."""
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            for item in self.real_path(td):
                stack.enter_context(item)
            digest = runner._freeze_digest()
            root_a = Path(td) / "a"
            self.assertEqual(self.auth_a(1)["operator_confirmation"],
                             f"Authorize G-ROUTE3 phase A execution {digest} attempt 1")
            self.assertTrue(runner.phase_a_authorized(self.auth_a(1)))
            self.assertFalse(runner.phase_a_authorized(self.auth_a(2)))               # attempts cannot skip
            self.assertFalse(runner.phase_a_authorized(self.auth_a(1, note="retry")))  # no extra keys
            # the authorized path refuses a synthetic provider and a guarded-root override
            with self.assertRaisesRegex(PermissionError, "governed_ollama_provider"):
                runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                       run_root=root_a, run_id="x", authorization=self.auth_a(1))
            with self.assertRaisesRegex(PermissionError, "guarded_root_override"):
                runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a), model_receipts=receipts(),
                                       run_root=root_a, run_id="x", authorization=self.auth_a(1), guarded_root=ROOT)
            self.assertEqual(runner.ledger_entries("A"), [])                             # nothing consumed yet
            # attempt 1 pauses, then resumes under the same authorization, run id and run root only
            paused = runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a), model_receipts=receipts(),
                                            run_root=root_a, run_id="real-a", authorization=self.auth_a(1),
                                            control=lambda: "pause")
            self.assertEqual(paused["state"], "paused")
            for root, rid in ((root_a, "real-a-again"), (Path(td) / "elsewhere", "real-a")):
                with self.assertRaisesRegex(PermissionError, "phase_a_not_authorized"):
                    runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a),
                                           model_receipts=receipts(), run_root=root, run_id=rid,
                                           authorization=self.auth_a(1), resume=(rid == "real-a"))
            result_a = runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a),
                                              model_receipts=receipts(), run_root=root_a, run_id="real-a",
                                              authorization=self.auth_a(1), resume=True)
            self.assertEqual(result_a["state"], "complete")
            # a further attempt after a complete one is never authorized (no best-of-N)
            self.assertFalse(runner.phase_a_authorized(self.auth_a(2)))
            self.assertEqual([(r["run_id"], r["outcome"]) for r in runner.phase_a_attempts()], [("real-a", "complete")])

            doc, _ = self.freeze(td, result_a, run_id="real-a")
            pre = runner.phase_b_preconditions(root_a, "real-a")
            self.assertTrue(pre["valid"], pre["reasons"])
            # the same run read from a different root is not the ledger's run
            shutil.copytree(root_a / "real-a", Path(td) / "copy" / "real-a")
            self.assertIn("phase_a_run_root_differs_from_ledger",
                          runner.phase_b_preconditions(Path(td) / "copy", "real-a")["reasons"])
            table = doc["table_sha256"]

            def auth_b(attempt, **changes):
                row = {"benchmark_id": "G-ROUTE3", "phase": "B", "execution_freeze_sha256": digest,
                       "qualification_table_sha256": table, "phase_a_run_id": "real-a", "attempt": attempt,
                       "one_execution_only": True, "consumed": False,
                       "operator_confirmation": runner.confirmation_string("B", attempt, freeze=digest, table=table)}
                return {**row, **changes}

            self.assertTrue(runner.phase_b_authorized(auth_b(1), root_a, "real-a"))
            self.assertFalse(runner.phase_b_authorized(auth_b(1, qualification_table_sha256="0" * 64), root_a, "real-a"))
            result_b = runner.execute_phase_b(provider_call=RealShapedProvider("B", self.plan_b),
                                              model_receipts=receipts(), run_root=Path(td) / "b", phase_a_root=root_a,
                                              phase_a_run_id="real-a", run_id="real-b", authorization=auth_b(1))
            self.assertEqual(result_b["state"], "complete")
            self.assertEqual([(r["run_id"], r["outcome"]) for r in result_b["score"]["phase_b_attempts"]],
                             [("real-b", "running")])
            self.assertIs(result_b["score"]["synthetic_fixture"], False)
            for rid, root in (("real-b-again", Path(td) / "b"), ("real-b", Path(td) / "b2")):
                with self.assertRaisesRegex(PermissionError, "phase_b_not_authorized"):
                    runner.execute_phase_b(provider_call=RealShapedProvider("B", self.plan_b), model_receipts=receipts(),
                                           run_root=root, phase_a_root=root_a, phase_a_run_id="real-a", run_id=rid,
                                           authorization=auth_b(1))
            self.assertFalse(runner.phase_b_authorized(auth_b(2), root_a, "real-a"))     # B is not best-of-N either

    def test_a_retry_is_allowed_only_after_a_non_complete_attempt_and_both_are_disclosed(self):
        class FlakyProvider(RealShapedProvider):
            def __call__(self, call_id, body):
                if len(self.calls) == 3:
                    raise ConnectionError("provider went away")
                return super().__call__(call_id, body)

        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            for item in self.real_path(td):
                stack.enter_context(item)
            stack.enter_context(patch.object(runner, "REAL_PROVIDER_TYPES", (RealShapedProvider, FlakyProvider)))
            root_a = Path(td) / "a"
            first = runner.execute_phase_a(provider_call=FlakyProvider("A", self.plan_a), model_receipts=receipts(),
                                           run_root=root_a, run_id="try-1", authorization=self.auth_a(1))
            self.assertEqual(first["state"], "incomplete")
            self.assertTrue(runner.phase_a_authorized(self.auth_a(2)))
            second = runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a), model_receipts=receipts(),
                                            run_root=root_a, run_id="try-2", authorization=self.auth_a(2))
            self.assertEqual(second["state"], "complete")
            self.assertEqual([(r["attempt"], r["outcome"]) for r in runner.phase_a_attempts()],
                             [(1, "incomplete"), (2, "complete")])
            self.assertTrue(runner.phase_a_attempts()[0]["reason"].startswith("provider_boundary_exception"))
            doc, _ = self.freeze(td, second, run_id="try-2")
            pre = runner.phase_b_preconditions(root_a, "try-2")
            self.assertTrue(pre["valid"], pre["reasons"])
            self.assertFalse(runner.phase_b_preconditions(root_a, "try-1")["valid"])

    def test_a_stuck_attempt_can_only_be_abandoned_explicitly(self):
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            for item in self.real_path(td):
                stack.enter_context(item)
            runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a), model_receipts=receipts(),
                                   run_root=Path(td) / "a", run_id="stuck", authorization=self.auth_a(1),
                                   control=lambda: "pause")
            self.assertFalse(runner.phase_a_authorized(self.auth_a(2)))                  # paused is not terminal
            with self.assertRaisesRegex(ValueError, "abandon_reason_required"):
                runner.abandon_attempt("A", " ")
            runner.abandon_attempt("A", "host rebooted; checkpoint unrecoverable")
            self.assertEqual(runner.phase_a_attempts()[0]["outcome"], "incomplete")
            self.assertIn("abandoned_by_operator", runner.phase_a_attempts()[0]["reason"])
            self.assertTrue(runner.phase_a_authorized(self.auth_a(2)))

    def test_a_synthetic_run_cannot_be_relabelled_as_authorized(self):
        """Round-3 reviewer's probe: resume a finished synthetic run under a real authorization, reseal the receipt."""
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            for item in self.real_path(td):
                stack.enter_context(item)
            root_a = Path(td) / "a"
            synthetic = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                               run_root=root_a, run_id="S", synthetic_fixture=True)
            self.freeze(td, synthetic, run_id="S")
            with self.assertRaisesRegex(PermissionError, "phase_a_not_authorized"):
                runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a), model_receipts=receipts(),
                                       run_root=root_a, run_id="S", authorization=self.auth_a(1), resume=True)
            self.assertEqual(runner.ledger_entries("A"), [])
            receipt_path = root_a / "S" / "terminal_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt.pop("record_sha256")
            receipt["synthetic_fixture"] = False
            receipt["record_sha256"] = contract.json_digest(receipt)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            reasons = runner.phase_b_preconditions(root_a, "S")["reasons"]
            self.assertIn("phase_a_records_disagree_with_receipt_on_synthetic", reasons)
            self.assertIn("phase_a_run_not_in_authorization_ledger", reasons)
            with self.assertRaisesRegex(PermissionError, "synthetic_phase_b_requires_a_synthetic_phase_a"):
                runner.execute_phase_b(provider_call=Provider("B", self.plan_b), model_receipts=receipts(),
                                       run_root=Path(td) / "b", phase_a_root=root_a, phase_a_run_id="S",
                                       synthetic_fixture=True)

    def test_authorized_runs_must_carry_the_providers_own_raw_bodies(self):
        class HollowProvider(RealShapedProvider):
            def __call__(self, call_id, body):
                return {**super().__call__(call_id, body), "raw_body_b64": "", "raw_body_sha256": ""}

        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            for item in self.real_path(td):
                stack.enter_context(item)
            stack.enter_context(patch.object(runner, "REAL_PROVIDER_TYPES", (HollowProvider,)))
            result = runner.execute_phase_a(provider_call=HollowProvider("A", self.plan_a), model_receipts=receipts(),
                                            run_root=Path(td) / "a", run_id="hollow", authorization=self.auth_a(1))
            self.assertEqual(result["state"], "complete")
            self.freeze(td, result, run_id="hollow")
            self.assertIn("provider_raw_body_digest_mismatch",
                          runner.phase_b_preconditions(Path(td) / "a", "hollow")["reasons"])

    def test_authorization_is_consumed_exactly_once_in_the_fixed_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"attempt": 1, "operator_confirmation": "x"}
            runner.consume_authorization("A", auth, "run-1", Path(td) / "one")
            runner.consume_authorization("A", auth, "run-1", Path(td) / "one")     # the same run resuming
            for run_id, root in (("run-2", Path(td) / "one"), ("run-1b", Path(td) / "two"), ("run-1", Path(td) / "two")):
                with self.assertRaisesRegex(PermissionError, "authorization_already_consumed"):
                    runner.consume_authorization("A", auth, run_id, root)
            self.assertEqual(len(runner.ledger_entries("A")), 1)

    def test_launcher_builds_its_own_provider_and_reads_only_the_exact_sentence(self):
        import g_route3_launch as launch
        freeze = "a" * 64
        row = launch.authorization_from_sentence(f"Authorize G-ROUTE3 phase A execution {freeze} attempt 2")
        self.assertEqual((row["phase"], row["attempt"], row["execution_freeze_sha256"]), ("A", 2, freeze))
        self.assertEqual(set(row), runner.AUTHORIZATION_KEYS["A"])
        b = launch.authorization_from_sentence(f"Authorize G-ROUTE3 phase B execution {freeze} table {'b' * 64} "
                                               f"attempt 1", phase_a_run_id="run-a")
        self.assertEqual(set(b), runner.AUTHORIZATION_KEYS["B"])
        for bad in (f"Authorize G-ROUTE3 phase A execution {freeze}", f"Authorize G-ROUTE3 phase A execution {freeze} "
                    f"attempt 01", f" Authorize G-ROUTE3 phase A execution {freeze} attempt 1",
                    f"Authorize G-ROUTE3 phase A execution {freeze.upper()} attempt 1"):
            with self.assertRaises(ValueError):
                launch.authorization_from_sentence(bad)
        with self.assertRaisesRegex(ValueError, "phase_a_run_id"):
            launch.authorization_from_sentence(f"Authorize G-ROUTE3 phase B execution {freeze} table {'b' * 64} attempt 1")
        source = inspect.getsource(launch.launch)
        self.assertIn("runner.GovernedOllamaProvider(endpoint)", source)
        self.assertNotIn("guarded_root", source)
        self.assertEqual(runner.REAL_PROVIDER_TYPES, (runner.GovernedOllamaProvider,))

    def test_synthetic_path_requires_a_declared_synthetic_provider(self):
        def real_looking(call_id, body):
            raise AssertionError("must not be contacted")

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(PermissionError, "declared_synthetic_provider"):
                runner.execute_phase_a(provider_call=real_looking, model_receipts=receipts(),
                                       run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
            with self.assertRaisesRegex(PermissionError, "declared_synthetic_provider"):
                runner.execute_phase_b(provider_call=real_looking, model_receipts=receipts(),
                                       run_root=Path(td) / "b", phase_a_root=Path(td) / "a", phase_a_run_id="a",
                                       synthetic_fixture=True)

    def test_coding_sandbox_host_failure_is_infrastructure_not_model_failure(self):
        def host_down(fixture, raw):
            raise OSError("sandbox host unavailable")

        def model_error(fixture, raw):
            raise ValueError("candidate uses a disallowed operation")

        def always_slow(fixture, raw):
            raise subprocess.TimeoutExpired("python", 20)

        def only_candidate_slow(fixture, raw):
            if json.loads(raw)["new"] != fixture["input"]["source"]:
                raise subprocess.TimeoutExpired("python", 20)
            return runner._failed_coding_evidence(fixture)

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
        with tempfile.TemporaryDirectory() as td:
            with patch.object(runner, "run_isolated_fixture", always_slow):
                result = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                                run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
            self.assertEqual((result["state"], result["reason"]), ("incomplete", "coding_sandbox_host_slow"))
        with tempfile.TemporaryDirectory() as td:
            with patch.object(runner, "run_isolated_fixture", only_candidate_slow):
                result = runner.execute_phase_a(provider_call=Provider("A", self.plan_a), model_receipts=receipts(),
                                                run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
            self.assertEqual(result["state"], "complete")

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
            with patch.object(runner, "REAL_PROVIDER_TYPES", (RealShapedProvider,)):
                with self.assertRaisesRegex(PermissionError, "phase_a_not_authorized"):
                    runner.execute_phase_a(provider_call=RealShapedProvider("A", self.plan_a),
                                           model_receipts=receipts(), run_root=Path(td) / "a", run_id="a")
        self.assertFalse(runner.phase_a_authorized({}))
        self.assertFalse(runner.phase_b_authorized({}, Path("."), "none"))

    def test_model_binding_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "model_preflight_rejected"):
                runner.execute_phase_a(provider_call=Provider("A", self.plan_a),
                                       model_receipts=receipts(manifest_digest="0" * 64),
                                       run_root=Path(td) / "a", run_id="a", synthetic_fixture=True)
        # the preflight reads G-ROUTE3's own frozen bindings, not G-ROUTE1's
        self.assertNotIn("g_route1_provider", inspect.getsource(runner._collect))
        self.assertTrue(runner.verify_model_receipts(receipts())["valid"])

class ValidationGateTests(LedgerIsolation, unittest.TestCase):
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
        self.assertIn("unsafe_stops_of_stops_excluding_coding", report["metrics"])
        self.assertIn("coding_generation_repair", report["metrics"]["unsafe_stops_by_task_class"])


class FreezeTests(unittest.TestCase):
    def test_freeze_verification_does_not_depend_on_table_absence(self):
        for function in (freeze.build_manifest, freeze.verify_manifest):
            self.assertNotIn("QUALIFICATION_TABLE", inspect.getsource(function))
        self.assertIn("QUALIFICATION_TABLE", inspect.getsource(freeze.write_manifest))
        manifest = freeze.build_manifest(implementation_commit="0" * 40)
        self.assertTrue(freeze.verify_manifest(manifest)["valid"], freeze.verify_manifest(manifest)["reasons"])
        self.assertEqual([row["binding_sha256"] for row in manifest["supersedes"]],
                         ["64eed1ba1a6bb40faa0277f363f4027c09056ef909e6a31bdf71e8ad5ffe3c21",
                          "aa5db17af6e12aaf1453cdbd1c88940743cb8712882c8a7ccba2a6541bfd52af",
                          "f92fd6e0a628864a7da9a842642ec2e3fd79c81685f9fce3c0a817dbed721397"])
        self.assertFalse(any(row["authorized"] for row in manifest["supersedes"]))

    def test_superseded_digests_are_independent_of_checkout_line_endings(self):
        for prior in freeze.SUPERSEDED:
            path = contract.ROOT / prior["path"]
            self.assertEqual(freeze.literal_sha256(path), prior["literal_sha256"])
            with tempfile.TemporaryDirectory() as td:
                crlf = Path(td) / "prior.json"
                crlf.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
                self.assertEqual(freeze.literal_sha256(crlf), prior["literal_sha256"])

    def test_every_runtime_module_is_frozen_and_guarded(self):
        """The import closure of the governed run, including the activity module, must be bound and guarded."""
        script = (
            "import sys, os, json, tempfile\n"
            "sys.path.insert(0, os.getcwd())\n"
            "import g_route3_runner as r, g_route3_qualification, g_route3_validation, g_route3_routing, g_route3_freeze\n"
            "import g_route3_launch\n"
            "r.RouteThreeActivity('closure-probe', phase='A', root=tempfile.mkdtemp())\n"
            "root = os.path.abspath('..')\n"
            "mods = sorted({os.path.relpath(os.path.abspath(m.__file__), root).replace(os.sep, '/')\n"
            "               for m in list(sys.modules.values()) if getattr(m, '__file__', None)\n"
            "               and os.path.abspath(m.__file__).startswith(root)})\n"
            "print(json.dumps(mods))\n")
        out = subprocess.run([sys.executable, "-c", script], cwd=contract.ROOT / "tools", capture_output=True,
                             text=True, check=True).stdout.strip().splitlines()[-1]
        modules = set(json.loads(out))
        self.assertIn("conscious_agent/activity.py", modules)
        self.assertLessEqual(modules, set(runner.GUARDED_PATHS), sorted(modules - set(runner.GUARDED_PATHS)))
        self.assertLessEqual(modules, set(freeze.ARTIFACTS), sorted(modules - set(freeze.ARTIFACTS)))

    def test_a_freeze_cannot_be_written_once_a_table_exists(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "QUALIFICATION_TABLE.json").write_text("{}", encoding="utf-8")
            with patch.object(freeze, "DATA", Path(td)):
                with self.assertRaisesRegex(ValueError, "qualification_table_must_not_exist_at_execution_freeze"):
                    freeze.write_manifest(Path(td) / "freeze.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
