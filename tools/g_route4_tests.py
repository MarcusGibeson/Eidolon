# forked from g_route3_tests
from __future__ import annotations

"""Deterministic tests for G-ROUTE4 (design step 4). No provider is contacted; no network is used.

The forked suite's tests of the superseded R6 runner and of coding are not carried (the R6 path and coding are not in
this fork). The rest is rewritten against the G-ROUTE4 corpus, and the design's own deterministic tests are added:
identity (the grep test and its frozen allowlist), the module rule, the closure rule, bindings equality, seed ranges
and disjointness, O8 (thresholds keys by static reading), N9 (the independence core byte-identical), the prior data
root's refusal (static read), prompt identity and the D8 freeze-time checks, and the coding exclusion.

    python -B tools/g_route4_tests.py
"""

import ast
import copy
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route4_contract as contract
import g_route4_freeze as freeze
import g_route4_independence as independence
import g_route4_journal as journal
import g_route4_qualification as qualification
import g_route4_runner as runner
import g_route4_validation as validation
import g_route3_conversation as conversation
import g_route3_routing as routing
import g_route3_triggers as triggers
from g_route3_operational import validate_operational
from g_route3_semantics import validate_fixture_output

CAND = ROOT / "experiments" / "G-ROUTE4-candidate"
PRIOR = "G-ROUTE3"                                   # read-only references; see G3_REFERENCE_ALLOWLIST
IMPORTED_UNCHANGED_PRIOR = ("g_route3_conversation", "g_route3_semantics", "g_route3_operational",
                            "g_route3_triggers", "g_route3_routing")
IMPORTED_UNCHANGED = IMPORTED_UNCHANGED_PRIOR + ("g_route1_validators", "g_route1_operational", "g_route1_contract",
                                                 "g_route1_provider", "g_route1_execution_contract", "g_route1_freeze",
                                                 "g_route2_normalization")
FORBIDDEN_MODULES = ("g_route1_coding_runner", "g_route1_persistence", "g_route3_worker")
# The frozen allowlist of prior-experiment references in g_route4_* modules (design "Identity constants"). Every other
# line matching the grep pattern is a failure. Each entry is (module file, allowed kind): the kinds are the
# imported-unchanged module paths, the carried contract ids referenced by attribute, the provenance lines, and the
# named read-only references (by test or module name).
G3_REFERENCE_ALLOWLIST = {
    "provenance_line": r"^# forked from g_route3_[a-z0-9_]+$",
    "imported_unchanged_module": r"g_route3_(conversation|semantics|operational|triggers|routing)\b",
    # named read-only references: file -> the module ("*") or the named functions and constants that may hold them
    "read_only_references": {
        "g_route4_independence.py": ("*", "the contamination and independence checks"),
        "g_route4_differential.py": ("*", "both differentials (lifecycle and grading)"),
        "g_route4_campaign.py": (("review_seeds",), "the module-rule certification probe naming the forbidden modules"),
        "g_route4_tests.py": (("PRIOR", "IMPORTED_UNCHANGED_PRIOR", "FORBIDDEN_MODULES", "G3_REFERENCE_ALLOWLIST", "GREP",
                               "test_prompt_identity_rendering_is_the_prior_experiments",
                               "test_n9_the_carried_core_is_byte_identical_to_the_prior_module",
                               "test_grep_identity_and_the_frozen_allowlist", "test_module_rule",
                               "test_three_way_bindings_equality", "test_seed_ranges_and_disjointness",
                               "test_the_prior_data_root_refuses_by_its_own_literal", "test_coding_is_excluded"),
                              "the named tests: prompt identity, N9, grep, module rule, bindings equality, seed "
                              "disjointness, data-root refusal, coding exclusion"),
    },
}
GREP = re.compile(r"(?i)g[-_ ]?route[-_ ]?3")
_AUDIT_DIR = tempfile.TemporaryDirectory()


def tearDownModule():
    _AUDIT_DIR.cleanup()


def ready_audit(run_id="r", score="s", verdict="READY"):
    """An audit bound by digest to a real document that names the run and score it audits."""
    document = Path(_AUDIT_DIR.name) / f"audit-{run_id}-{verdict}.md"
    document.write_text(f"# Synthetic Phase A audit\n\nRun: {run_id}\nScore: {score}\nVerdict: {verdict}\n",
                        encoding="utf-8")
    return qualification.audit_record(document, verdict, "synthetic-test", run_id=run_id, score_record_sha256=score)


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
                + "\nActions taken: none\nThat is what the message shows.")
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
    exp["uncertainties"] = [] if exp["uncertainties"] else ["x"]
    return json.dumps(exp, sort_keys=True)


def table_from(lookup):
    cells = []
    for task in contract.TASK_CLASSES:
        for risk in contract.RISK_CLASSES:
            for tier in contract.TIER_ORDER:
                cells.append({"task_class": task, "risk_class": risk, "model_tier": tier,
                              "verdict": "qualified" if tier in lookup.get(f"{task}|{risk}", []) else "not_qualified"})
    return {"routing_lookup": qualification.routing_lookup(cells), "cells": cells, "table_sha256": "synthetic"}


def view(fixture, tier, raw):
    return {"fixture_id": fixture["fixture_id"], "task_class": fixture["task_class"],
            "risk_class": fixture["consequence_risk"], "model_tier": tier, "infrastructure_failure": "",
            **qualification.collect_evaluation(fixture, raw)}


def blueprint():
    return contract.load_json(CAND / "blueprint" / "BLUEPRINT.json")


# ============================================================================ corpus and prompts
class CorpusTests(unittest.TestCase):
    def test_namespaces_counts_and_call_ids(self):
        a, b = contract.runtime_fixtures("A"), contract.runtime_fixtures("B")
        self.assertFalse(set(a) & set(b))
        self.assertTrue(all(k.startswith("A4-") for k in a) and all(k.startswith("B4-") for k in b))
        self.assertEqual((len(a), len(b)), (80, 305))
        ca = {row.call_id for row in contract.build_schedule("A")}
        cb = {row.call_id for row in contract.build_schedule("B")}
        self.assertFalse(ca & cb)
        self.assertEqual((len(ca), len(cb)), (480, 915))

    def test_d9_composition_and_a_prime_cells(self):
        from collections import Counter
        comp = {c: Counter((f["task_class"], f["consequence_risk"]) for f in contract.runtime_fixtures(c).values())
                for c in "AB"}
        self.assertEqual(dict(comp["A"]), contract.CELL_SIZES["A"])
        self.assertEqual(dict(comp["B"]), contract.CELL_SIZES["B"])
        self.assertEqual(sum(v for (t, r), v in comp["B"].items() if r != "R4"), 300)
        self.assertEqual(sum(v for (t, r), v in comp["B"].items() if r == "R4"), 5)

    def test_execution_inputs_are_the_reviewed_final_corpus(self):
        addenda = {c: contract.load_json(CAND / "adjudication" / f"{c}_MAIN_CLOSURE_ADDENDUM_CR1.json")["final_corpus"]
                   for c in ("A", "B")}
        for corpus, key in (("A", "a_main"), ("B", "b_main")):
            fixtures = sorted(contract.load_corpus(corpus)["fixtures"], key=lambda x: x["fixture_id"])
            gold = sorted(contract.load_gold(corpus)["items"], key=lambda x: x["fixture_id"])
            self.assertEqual(independence.sha256(independence.canonical_json(fixtures)),
                             addenda[corpus][key]["model_facing_sha256"])
            self.assertEqual(independence.sha256(independence.canonical_json(gold)), addenda[corpus][key]["gold_sha256"])

    def test_every_reference_answer_passes_and_every_gold_code_is_model_visible(self):
        profiles = contract.load_json(contract.PROMPT_PROFILES_PATH)["profiles"]
        checked = 0
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                with self.subTest(fixture=fid):
                    raw = reference(fixture, gold)
                    self.assertTrue(validate_operational(fixture, raw)["accepted"])
                    self.assertTrue(validate_fixture_output(fixture, gold, raw)["hard_gate_pass"])
                    visible = profiles[fixture["validator_profile"]] + fixture["prompt"] + json.dumps(fixture["input"])
                    exp = gold["expected"]
                    codes = {"conversation.v1": lambda: [exp["answer"]],
                             "research.v1": lambda: [exp["recommendation"], *exp["uncertainties"]],
                             "synthesis.v1": lambda: [exp["conclusion"]],
                             "planning.v1": lambda: [s["action"] for s in exp["steps"]] + exp["uncertainties"]}
                    for code in codes.get(fixture["validator_profile"], lambda: [])():
                        self.assertIn(code, visible)
                    checked += 1
        self.assertEqual(checked, 385)

    def test_every_wrong_answer_is_rejected(self):
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                raw = wrong(fixture, gold)
                with self.subTest(fixture=fid):
                    self.assertFalse(validate_operational(fixture, raw)["accepted"]
                                     and validate_fixture_output(fixture, gold, raw)["hard_gate_pass"])

    def test_no_trigger_fires_on_any_reference_answer(self):
        for corpus in ("A", "B"):
            for fid, (fixture, gold) in contract.indexed_fixture_gold(corpus).items():
                with self.subTest(fixture=fid):
                    self.assertEqual(triggers.triggers_for(fixture, reference(fixture, gold)), [])

    def test_conversation_frame_grades_the_two_fields_and_never_the_prose(self):
        fixture, gold = next((f, g) for f, g in contract.indexed_fixture_gold("A").values()
                             if f["validator_profile"] == "conversation.v1")
        answer = gold["expected"]["answer"]
        self.assertTrue(fixture["prompt"].endswith(conversation.FRAME_INSTRUCTION) or
                        conversation.FRAME_INSTRUCTION in fixture["prompt"])
        for body in ("Even if I booked it, it would still be over budget.", "I haven\u2019t booked anything.",
                     "I've passed your request on."):          # prose is not graded, in either direction (declared)
            text = f"Answer: {answer}\nActions taken: none\n{body}"
            with self.subTest(body=body):
                self.assertTrue(validate_operational(fixture, text)["accepted"])
                self.assertTrue(validate_fixture_output(fixture, gold, text)["hard_gate_pass"])
        for actions in ("booked it for you", "none, but I have forwarded your request", "None - I've reserved it"):
            text = f"Answer: {answer}\nActions taken: {actions}"
            with self.subTest(actions=actions):
                self.assertIn("declared_action_claim", validate_operational(fixture, text)["reasons"])
        for text, reason in (("", "empty_or_non_text_output"), ("I can't say.", "answer_line_missing"),
                             ("Answer: maybe\nActions taken: none", "answer_not_a_listed_option"),
                             (f"Answer: {answer}\nActions taken: none\n" + "x" * 700, "conversation_output_too_long")):
            with self.subTest(text=text[:30]):
                self.assertIn(reason, validate_operational(fixture, text)["reasons"])

    def test_conversation_gold_positions_are_balanced_per_cell(self):
        from collections import Counter, defaultdict
        slots = {s["fixture_id"]: s for s in blueprint()["slots"]}
        positions = defaultdict(Counter)
        for corpus in ("A", "B"):
            for fixture, gold in contract.indexed_fixture_gold(corpus).values():
                if fixture["validator_profile"] == "conversation.v1":
                    options = fixture["input"]["answer_options"]
                    self.assertEqual(len(options), 4)
                    positions[(corpus, slots[fixture["fixture_id"]]["risk"])][options.index(gold["expected"]["answer"])] += 1
        for cell, counts in positions.items():
            values = [counts.get(p, 0) for p in range(4)]
            self.assertLessEqual(max(values) - min(values), 1, cell)

    def test_every_prompt_is_its_opening_and_the_frozen_class_template(self):
        """D8 and N6 at the freeze: every prompt ends with its class's frozen assembled template (the part after the
        subject), each disclosure sentence appears exactly once, and the research sentence matches its frozen digest."""
        templates = blueprint()["templates"]
        for corpus in ("A", "B"):
            for fixture in contract.runtime_fixtures(corpus).values():
                t = templates[fixture["task_class"]]
                prefix, suffix = t["assembled_template"].split("{SUBJECT}", 1)
                with self.subTest(fixture=fixture["fixture_id"]):
                    self.assertTrue(fixture["prompt"].startswith(prefix) and fixture["prompt"].endswith(suffix))
                    if t["disclosure_sentence"]:
                        self.assertEqual(fixture["prompt"].count(t["disclosure_sentence"]), 1)
        research = templates["grounded_research_synthesis"]
        self.assertEqual(independence.sha256(research["disclosure_sentence"]),
                         "f3c383d92b5ca1cb99008b49864f7330b6515c93f8e795a6c135f1326844ab47")
        self.assertEqual(len(research["disclosure_sentence"]), 454)
        for t in templates.values():
            self.assertEqual(independence.sha256(t["assembled_template"]), t["assembled_template_sha256"])

    def test_every_json_prompt_discloses_the_output_budget(self):
        for corpus in ("A", "B"):
            for fixture in contract.runtime_fixtures(corpus).values():
                if fixture["validator_profile"] != "conversation.v1":
                    self.assertIn("350 tokens", fixture["prompt"], fixture["fixture_id"])
        self.assertEqual(contract.load_model_bindings()["generation_configuration"]["options"]["num_predict"], 350)

    def test_prompt_identity_rendering_is_the_prior_experiments(self):
        """The prompt identity test (a named read-only reference): the rendering function and request body are
        unchanged from the prior experiment's contract, and the G-ROUTE1 system prompts are the ones the prior
        experiment used, byte for byte."""
        prior = ast.parse((TOOLS / "g_route3_contract.py").read_text(encoding="utf-8"))
        ours = ast.parse((TOOLS / "g_route4_contract.py").read_text(encoding="utf-8"))
        for name in ("render_prompt", "request_body"):
            a = next(n for n in prior.body if isinstance(n, ast.FunctionDef) and n.name == name)
            b = next(n for n in ours.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertEqual(ast.dump(a), ast.dump(b), name)
        profiles = subprocess.run(["git", "-C", str(ROOT), "show", "06af676:experiments/G-ROUTE1-candidate/prompt_profiles.json"],
                                  capture_output=True, check=True).stdout.replace(b"\r\n", b"\n")
        self.assertEqual(contract.PROMPT_PROFILES_PATH.read_bytes().replace(b"\r\n", b"\n"), profiles)


# ============================================================================ independence
class IndependenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = independence.load_final_pool()
        cls.report = independence.audit(cls.pool)

    def test_the_final_pool_is_clean_and_carries_the_26_fixes(self):
        self.assertTrue(self.report["valid"], self.report["findings"])
        self.assertEqual(sum(len(v) for v in self.report["fixes_applied"].values()), 26)
        self.assertEqual(self.report["pool"]["g4_fixtures"], 584)

    def test_n9_the_carried_core_is_byte_identical_to_the_prior_module(self):
        """N9: the forked module's tokenizer, exemption lists and carried functions are byte-identical to the prior
        module's (read statically, never imported)."""
        names = ("MAX_CROSS_CORPUS_TRIGRAM_JACCARD", "BOILERPLATE_SHARE", "_WORD", "_ENTITY", "_COMMON",
                 "SHARED_RULE_KEYS", "SHARED_RULE_TOKENS", "_WEEKDAYS_MONTHS", "_content", "_named_entities",
                 "_trigrams", "_field_type", "structural_signature")

        def segments(path):
            text = path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
            tree, out = ast.parse(text), {}
            for node in tree.body:
                name = node.name if isinstance(node, ast.FunctionDef) else (
                    node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None)
                if name in names:
                    out[name] = ast.get_source_segment(text, node)
            return out
        prior, ours = segments(TOOLS / "g_route3_independence.py"), segments(TOOLS / "g_route4_independence.py")
        self.assertEqual(set(prior), set(names))
        for name in names:
            self.assertEqual(ours[name], prior[name], name)
        self.assertIn("\x08", ours["_named_entities"])        # the frozen detector's literal backspace bytes, kept

    def _audit_with(self, mutate):
        pool = copy.deepcopy(self.pool)
        mutate(pool)
        return independence.audit(pool)

    def test_a_planted_shared_entity_is_found(self):
        def mutate(pool):
            f = pool["fixtures"]["B4-EXTR-R2-01"]
            f["input"]["text"] += " It was delivered by the Zorbanek courier."
            g = pool["fixtures"]["A4-EXTR-R2-01"]
            g["input"]["text"] += " Ask the Zorbanek courier."
        report = self._audit_with(mutate)
        self.assertGreater(report["o3_entities"]["shared"], 0)
        self.assertFalse(report["valid"])

    def test_a_cloned_fixture_breaks_the_overlap_bound(self):
        def mutate(pool):
            pool["fixtures"]["B4-SYNTH-R1-05"]["input"] = copy.deepcopy(pool["fixtures"]["A4-SYNTH-R1-02"]["input"])
        report = self._audit_with(mutate)
        self.assertGreater(report["trigram"]["hierarchical_semantic_synthesis"]["pairs_over_bound"], 0)

    def test_identical_gold_and_repeated_lineages_and_actions_are_found(self):
        def mutate(pool):
            pool["gold"]["B4-PLAN-R1-02"] = dict(pool["gold"]["B4-PLAN-R1-02"],
                                                 expected=copy.deepcopy(pool["gold"]["A4-PLAN-R1-01"]["expected"]))
            src = pool["fixtures"]["A4-RSRCH-R1-01"]["input"]["sources"][0]["lineage"]
            pool["fixtures"]["B4-RSRCH-R1-02"]["input"]["sources"][0]["lineage"] = src
            act = pool["fixtures"]["A4-PLAN-R1-01"]["input"]["allowed_actions"][0]["action"]
            pool["fixtures"]["B4-PLAN-R1-03"]["input"]["allowed_actions"][0]["action"] = act
        report = self._audit_with(mutate)
        self.assertGreater(report["n1_duplicates"], 0)
        self.assertGreater(report["research_lineage_repeats"], 0)
        self.assertGreater(report["planning"]["repeated_action_names"], 0)

    def test_a_repeated_fine_signature_in_a_cell_is_found(self):
        def mutate(pool):
            a = pool["fixtures"]["A4-EXTR-R1-01"]
            b = copy.deepcopy(a)
            b["fixture_id"] = "B4-EXTR-R1-01"
            pool["fixtures"]["B4-EXTR-R1-01"] = dict(pool["fixtures"]["B4-EXTR-R1-01"], input=b["input"], prompt=b["prompt"])
            pool["gold"]["B4-EXTR-R1-01"] = dict(pool["gold"]["B4-EXTR-R1-01"],
                                                 expected=copy.deepcopy(pool["gold"]["A4-EXTR-R1-01"]["expected"]))
        self.assertGreater(self._audit_with(mutate)["fine_signature_clashes"], 0)

    def test_b7_passed_for_the_bound_module(self):
        record = contract.load_json(CAND / "implementation" / "B7_INDEPENDENCE_RECHECK.json")
        self.assertEqual((record["result"], record["differing"]), ("PASS", []))
        self.assertEqual(record["forked_module"]["lf_sha256"],
                         independence.lf_sha256(TOOLS / "g_route4_independence.py"))


# ============================================================================ routing (imported unchanged)
class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = contract.indexed_fixture_gold("B")
        cls.fx, cls.gold = cls.b["B4-EXTR-R1-01"]

    def observer(self, outputs, seen):
        def observe(tier):
            seen.append(tier)
            return view(self.fx, tier, outputs[tier]) if tier in outputs else None
        return observe

    def test_b_gold_cannot_enter_routing_context(self):
        record = {**view(self.fx, "small", reference(self.fx, self.gold)),
                  "semantics": {"normalized_semantic_evaluation": {"hard_gate_pass": True}},
                  "gold_linkage": {"gold_id": "G-ROUTE4-GOLD-B"}}
        self.assertFalse(routing.FORBIDDEN_VIEW_KEYS & set(routing.runtime_view(record)))
        with self.assertRaisesRegex(ValueError, "gold_leakage_into_routing"):
            routing.verdicts(self.fx, record, table_from({}))
        source = inspect.getsource(routing)
        for forbidden in ("load_gold", "gold_path", "indexed_fixture_gold", "attach_semantics", "hard_gate_pass"):
            self.assertNotIn(forbidden, source)

    def test_cheapest_qualified_tier_is_the_start(self):
        seen, good = [], reference(self.fx, self.gold)
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["small", "mid", "large"]}),
                            self.observer({"small": good, "mid": good, "large": good}, seen))
        self.assertEqual((out["start_tier"], out["final_tier"], seen), ("small", "small", ["small"]))

    def test_unqualified_tiers_are_never_contacted_or_stopped_on(self):
        seen, good = [], reference(self.fx, self.gold)
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["small", "large"]}),
                            self.observer({"small": "{bad", "mid": good, "large": good}, seen))
        self.assertEqual(seen, ["small", "large"])
        self.assertEqual((out["outcome"], out["final_tier"]), ("stopped", "large"))
        v = routing.runtime_view(view(self.fx, "small", good))
        verdict = routing.verdicts(self.fx, v, table_from({"structured_extraction|R1": ["mid"]}))
        self.assertTrue(verdict["output_accepted"] and not verdict["safe_to_stop_escalation"])

    def test_no_qualified_model_contacts_nothing_and_exhaustion_fails_closed(self):
        seen = []
        out = routing.route(self.fx, table_from({}), self.observer({"small": reference(self.fx, self.gold)}, seen))
        self.assertEqual((out["outcome"], seen), ("no_qualified_model", []))
        seen = []
        out = routing.route(self.fx, table_from({"structured_extraction|R1": ["mid"]}),
                            self.observer({"mid": "{bad"}, seen))
        self.assertEqual((out["outcome"], out["final_tier"], seen), ("escalation_exhausted", None, ["mid"]))

    def test_r4_is_evidence_only_and_contacts_nothing(self):
        fx, _ = self.b["B4-EXTR-R4-01"]
        seen = []
        out = routing.route(fx, table_from({"structured_extraction|R4": ["small"]}), lambda tier: seen.append(tier))
        self.assertEqual((out["outcome"], seen), ("evidence_only", []))

    def test_the_retained_triggers_fire(self):
        fired = set()
        research, rgold = self.b["B4-RSRCH-R2-02"]
        empty = copy.deepcopy(rgold["expected"])
        empty["claims"][0]["citations"], empty["claims"][0]["lineages"] = [], []
        fired |= set(routing.triggers_for(research, routing.runtime_view(view(research, "small", json.dumps(empty)))))
        blank = dict(self.gold["expected"])
        blank[next(k for k, t in self.fx["input"]["schema"].items() if t == "string")] = ""
        fired |= set(routing.triggers_for(self.fx, routing.runtime_view(view(self.fx, "small", json.dumps(blank)))))
        self.assertEqual(tuple(routing.TRIGGERS), ("grounding_weak", "structural_anomaly"))
        self.assertEqual(fired, set(routing.TRIGGERS))


# ============================================================================ qualification (8/8)
class QualificationTests(unittest.TestCase):
    IDS = ["A4-EXTR-R1-01", "A4-EXTR-R1-02", "A4-EXTR-R1-03", "A4-EXTR-R1-04"]

    def rows(self, ids=None, correct=True):
        ids = ids if ids is not None else [i for i in self.IDS for _ in range(2)]
        return [{"fixture_id": fid, "task_class": "structured_extraction", "risk_class": "R1", "model_tier": "small",
                 "model": "m", "returned_model": "m", "infrastructure_failure": "",
                 "normalized_operational_validation": {"accepted": True},
                 "semantics": {"normalized_semantic_evaluation": {"hard_gate_pass": correct},
                               "normalized_false_clean": not correct}} for fid in ids]

    def verdict(self, rows):
        return next(c for c in qualification.qualify(rows) if c["task_class"] == "structured_extraction"
                    and c["risk_class"] == "R1" and c["model_tier"] == "small")

    def test_only_the_exact_four_by_two_design_can_qualify(self):
        self.assertEqual(self.verdict(self.rows())["verdict"], "qualified")
        self.assertEqual(self.verdict(self.rows(self.IDS * 2 + self.IDS[:1]))["verdict"], "insufficient_evidence")
        self.assertEqual(self.verdict(self.rows(self.IDS[:3] * 2 + self.IDS[:2]))["verdict"], "insufficient_evidence")
        self.assertEqual(self.verdict(self.rows(self.IDS * 1))["verdict"], "insufficient_evidence")
        self.assertEqual(len(qualification.qualify([])), 60)
        self.assertTrue(all(c["verdict"] == "insufficient_evidence" for c in qualification.qualify([])))

    def test_one_failure_disqualifies_and_infrastructure_is_insufficient(self):
        rows = self.rows()
        rows[5]["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"] = False
        self.assertEqual(self.verdict(rows)["verdict"], "not_qualified")
        rows = self.rows()
        rows[0]["infrastructure_failure"] = "timeout"
        self.assertEqual(self.verdict(rows)["verdict"], "insufficient_evidence")

    def test_both_bounds_are_reported(self):
        cell = self.verdict(self.rows())
        self.assertEqual(cell["failure_rate_upper_95"], qualification.failure_rate_upper_bound(0, 8))
        self.assertAlmostEqual(cell["failure_rate_upper_95"], 0.312, places=3)
        self.assertAlmostEqual(cell["fixture_failure_rate_upper_95"], 0.527, places=3)
        rows = self.rows()
        rows[1]["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"] = False
        self.assertEqual(self.verdict(rows)["failing_fixtures"], 1)

    def test_table_digest_audit_binding_and_write_once(self):
        cells = qualification.qualify(self.rows())
        doc = qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                        audit=ready_audit(), phase_a_attempts=[])
        self.assertTrue(qualification.verify_table(doc)["valid"], qualification.verify_table(doc)["reasons"])
        tampered = copy.deepcopy(doc)
        tampered["routing_lookup"]["structured_extraction|R2"] = ["small"]
        self.assertIn("table_digest_mismatch", qualification.verify_table(tampered)["reasons"])
        with self.assertRaises(ValueError):
            qualification.build_table(cells, run_id="r", score_record_sha256="s", execution_freeze_binding="f",
                                      audit=ready_audit(verdict="REVISE"), phase_a_attempts=[])
        frozen_doc = CAND / "DESIGN_CANDIDATE.md"
        audit = qualification.audit_record(frozen_doc, "READY", "t", run_id="r", score_record_sha256="s")
        self.assertIn("qualification_audit_document_is_a_frozen_artifact", qualification.verify_audit(audit))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "table.json"
            qualification.freeze_table(doc, path)
            other = qualification.build_table(qualification.qualify(self.rows(self.IDS)), run_id="r",
                                              score_record_sha256="s", execution_freeze_binding="f",
                                              audit=ready_audit(), phase_a_attempts=[])
            with self.assertRaisesRegex(FileExistsError, "already_frozen"):
                qualification.freeze_table(other, path)


# ============================================================================ gates
class GateTests(unittest.TestCase):
    GATES = contract.load_thresholds()["gates"]

    def test_the_frozen_three_way_tables(self):
        u = lambda k, n: validation.unsafe_stop_gate(k, n, self.GATES)["outcome"]            # noqa: E731
        c = lambda x, n: validation.correct_stop_gate(x, n, self.GATES)["outcome"]           # noqa: E731
        self.assertEqual(u(3, 76), "PASS")
        self.assertEqual(u(4, 76), "FAIL (not shown)")
        self.assertEqual(u(3, 75), "NOT_TESTABLE")
        self.assertEqual(u(10, 30), "FAIL (shown worse)")
        self.assertEqual(u(2, 12), "FAIL (not shown)")               # n >= 10 and observed > 0.10
        self.assertEqual(u(1, 10), "NOT_TESTABLE")
        self.assertEqual(u(0, 0), "NOT_TESTABLE")
        self.assertEqual(c(23, 30), "PASS")
        self.assertEqual(c(22, 30), "FAIL (not shown)")
        self.assertEqual(c(2, 20), "FAIL (shown worse)")
        self.assertEqual(c(5, 9), "NOT_TESTABLE")
        self.assertEqual(c(5, 10), "FAIL (not shown)")               # n >= 10 and observed < 0.60

    def test_the_floors_reproduce_their_derivation(self):
        from fractions import Fraction
        self.assertEqual(next(n for n in range(4, 400) if validation.upper_bound_at_most(3, n, Fraction(1, 10),
                                                                                        Fraction(1, 20))), 76)
        self.assertEqual(next(x for x in range(31) if validation.lower_bound_at_least(x, 30, Fraction(3, 5),
                                                                                     Fraction(1, 20))), 23)

    @classmethod
    def records(cls, output_for, drop=0):
        out = []
        for fid, (fixture, gold) in contract.indexed_fixture_gold("B").items():
            for tier in contract.TIER_ORDER:
                raw = output_for(fid, fixture, gold, tier)
                out.append({"fixture_id": fid, "task_class": fixture["task_class"], "risk_class": fixture["consequence_risk"],
                            "model_tier": tier, "model": "m", "returned_model": "m", "infrastructure_failure": "",
                            "raw_output": raw, **qualification.collect_evaluation(fixture, raw)})
        return out[drop:]

    def test_an_empty_table_is_not_testable_with_intact_denominators(self):
        report = validation.score(self.records(lambda fid, f, g, tier: reference(f, g)), table_from({}))
        self.assertEqual(report["primary_status"], "NOT_TESTABLE")
        self.assertEqual((report["metrics"]["stops"], report["metrics"]["no_qualified_model_cases"],
                          report["metrics"]["r4_evidence_only_cases"]), (0, 300, 5))
        self.assertTrue(report["gates"]["denominator_integrity"]["observed"])
        self.assertNotIn("secondary_status", report)
        self.assertNotIn("unsafe_stops_of_stops_excluding_coding", report["metrics"])

    def test_a_missing_record_is_an_integrity_failure(self):
        report = validation.score(self.records(lambda fid, f, g, tier: reference(f, g), drop=1),
                                  table_from({f"{t}|{r}": ["small"] for t in contract.TASK_CLASSES
                                              for r in ("R1", "R2", "R3")}))
        self.assertEqual(report["primary_status"], "FAILED_INTEGRITY")

    def test_every_stop_correct_passes_both_gates(self):
        lookup = {f"{t}|{r}": ["small"] for t in contract.TASK_CLASSES for r in ("R1", "R2", "R3")}
        report = validation.score(self.records(lambda fid, f, g, tier: reference(f, g)), table_from(lookup))
        self.assertEqual(report["metrics"]["stops"], 300)
        self.assertEqual(report["gates"]["unsafe_stop_rate_of_stops"]["outcome"], "PASS")
        self.assertEqual(report["gates"]["correct_stop_rate_of_qualified_start_cases"]["outcome"], "PASS")
        self.assertEqual(report["primary_status"], "PASS")
        self.assertEqual(report["descriptive_never_gating"]["research_metrics_b"]["claim_level_agreement"]["rate"], 1.0)

    def test_an_evaluable_failing_gate_is_a_failure(self):
        lookup = {f"{t}|{r}": ["small"] for t in contract.TASK_CLASSES for r in ("R1", "R2", "R3")}
        report = validation.score(self.records(lambda fid, f, g, tier: wrong(f, g) if tier == "small" else reference(f, g)),
                                  table_from(lookup))
        self.assertEqual(report["gates"]["unsafe_stop_rate_of_stops"]["outcome"], "FAIL (shown worse)")
        self.assertEqual(report["primary_status"], "FAIL")


# ============================================================================ freeze
class FreezeTests(unittest.TestCase):
    def test_identity_and_pinned_data_root(self):
        self.assertEqual((freeze.CANDIDATE_ID, freeze.SUPERSEDED), ("G-ROUTE4-EXECUTION-R1", ()))
        self.assertEqual(freeze.DATA_ROOT, r"C:\Users\marcu\AppData\Local\Eidolon\research\g_route4")

    def test_no_freeze_before_the_later_step_4_records(self):
        review_path = CAND / "implementation" / "IMPLEMENTATION_REVIEW.json"
        review = contract.load_json(review_path)
        self.assertEqual(review["verdict"], "READY_FOR_CERTIFICATION")
        self.assertFalse(freeze.FREEZE_PATH.exists())

        with self.assertRaises(FileNotFoundError) as caught:
            freeze.build_manifest(implementation_commit="0" * 40)

        message = str(caught.exception)
        self.assertIn("CERTIFICATION_REPORT.json", message)
        self.assertNotIn("IMPLEMENTATION_REVIEW.json", message)
        self.assertFalse(freeze.FREEZE_PATH.exists())

    def test_freeze_conditions_b7_and_b8_are_bound(self):
        self.assertEqual(freeze.b7_condition()["result"], "PASS")
        counts = freeze.b8_condition()["per_cell_fix_round_counts"]
        self.assertEqual(counts["g4adj-bmain-fix1-20260929T171651Z"]["B4-RSRCH-R3"], {"slots": 12, "disagreeing_slots": 7})

    def test_a_freeze_cannot_be_written_once_a_table_exists(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "QUALIFICATION_TABLE.json").write_text("{}", encoding="utf-8")
            with patch.object(freeze, "DATA", Path(td)):
                with self.assertRaisesRegex(ValueError, "qualification_table_must_not_exist_at_execution_freeze"):
                    freeze.write_manifest(Path(td) / "freeze.json")

    def test_every_runtime_module_is_guarded_and_frozen(self):
        script = ("import sys, os, json\nsys.path.insert(0, os.getcwd())\n"
                  "import g_route4_launch, g_route4_lifecycle, g_route4_scorer, g_route4_runner, g_route4_journal\n"
                  "import g_route4_qualification, g_route4_validation, g_route4_freeze, g_route4_evidence, g_route4_fs\n"
                  "root = os.path.abspath('..')\n"
                  "print(json.dumps(sorted({os.path.relpath(os.path.abspath(m.__file__), root).replace(os.sep, '/')\n"
                  "      for m in list(sys.modules.values()) if getattr(m, '__file__', None)\n"
                  "      and os.path.abspath(m.__file__).startswith(root)})))\n")
        out = subprocess.run([sys.executable, "-B", "-c", script], cwd=TOOLS, capture_output=True, text=True,
                             check=True).stdout.strip().splitlines()[-1]
        modules = set(json.loads(out))
        import g_route4_lifecycle
        guarded = set(runner.GUARDED_PATHS) | set(g_route4_lifecycle.R7_MODULES)
        self.assertLessEqual(modules, guarded, sorted(modules - guarded))
        self.assertLessEqual(modules, set(freeze.ARTIFACTS), sorted(modules - set(freeze.ARTIFACTS)))


# ============================================================================ design: identity and separation
class DesignTests(unittest.TestCase):
    def test_grep_identity_and_the_frozen_allowlist(self):
        """No prior-experiment reference in any g_route4_* module outside the frozen allowlist."""
        provenance = re.compile(G3_REFERENCE_ALLOWLIST["provenance_line"])
        imported = re.compile(G3_REFERENCE_ALLOWLIST["imported_unchanged_module"])
        failures = []
        for path in sorted(TOOLS.glob("g_route4_*.py")):
            text = path.read_text(encoding="utf-8")
            scope, _ = G3_REFERENCE_ALLOWLIST["read_only_references"].get(path.name, ((), ""))
            if scope == "*":
                continue
            allowed_lines = set()
            for node in ast.walk(ast.parse(text)):
                name = getattr(node, "name", None)
                if name is None and isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                if name in scope:
                    allowed_lines |= set(range(node.lineno, node.end_lineno + 1))
            for number, line in enumerate(text.splitlines(), 1):
                if not GREP.search(line) or provenance.match(line) or number in allowed_lines:
                    continue
                if GREP.search(imported.sub("", line)):
                    failures.append(f"{path.name}:{number}:{line.strip()[:100]}")
        self.assertEqual(failures, [])
        camel = "Route" + "Three"                     # built from parts so this test does not match itself
        for path in TOOLS.glob("g_route4_*.py"):
            self.assertNotIn(camel, path.read_text(encoding="utf-8"), path.name)

    def test_module_rule(self):
        """No prior module other than the five imported unchanged, and neither the coding runner nor the persistence
        module, is loaded by a G-ROUTE4 process (checked through the loaded module set)."""
        code = ("import sys; sys.path.insert(0, r'%s')\n"
                "import g_route4_launch, g_route4_lifecycle, g_route4_scorer, g_route4_runner, g_route4_journal\n"
                "import g_route4_qualification, g_route4_validation, g_route4_freeze, g_route4_independence\n"
                "print('\\n'.join(sorted(sys.modules)))" % TOOLS)
        loaded = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, check=True).stdout.split()
        prior = sorted(m for m in loaded if m.startswith("g_route3_"))
        self.assertEqual(set(prior) - set(IMPORTED_UNCHANGED_PRIOR), set(), prior)
        self.assertFalse(set(FORBIDDEN_MODULES) & set(loaded))

    def test_closure_rule_for_imported_unchanged_modules(self):
        allowed = set(IMPORTED_UNCHANGED) | {"requests"}
        for name in IMPORTED_UNCHANGED:
            tree = ast.parse((TOOLS / f"{name}.py").read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    for module in modules:
                        top = module.split(".")[0]
                        with self.subTest(module=name, imports=top):
                            self.assertTrue(top in allowed or top in sys.stdlib_module_names or top == "__future__",
                                            top)

    def test_three_way_bindings_equality(self):
        rows = [contract.load_json(p) for p in (ROOT / "experiments/G-ROUTE1-candidate/model_bindings.json",
                                                ROOT / "experiments/G-ROUTE3-candidate/model_bindings.json",
                                                CAND / "model_bindings.json")]
        for key in ("bindings", "generation_configuration", "provider_version"):
            self.assertEqual(rows[0][key], rows[1][key], key)
            self.assertEqual(rows[1][key], rows[2][key], key)
        self.assertEqual((rows[2]["schema_version"], rows[2]["binding_id"]),
                         ("g-route4.model-bindings.v1", "G-ROUTE4-MODEL-BINDINGS-R1"))

    def test_seed_ranges_and_disjointness(self):
        seeds = {c: {row.seed for row in contract.build_schedule(c)} for c in "AB"}
        self.assertEqual((min(seeds["A"]), max(seeds["A"])), (470001, 470792))
        self.assertEqual((min(seeds["B"]), max(seeds["B"])), (480001, 483041))
        prior = {row["seed"] for c in "ab"
                 for row in contract.load_json(ROOT / f"experiments/G-ROUTE3-candidate/schedule_{c}.json")["calls"]}
        self.assertFalse((seeds["A"] | seeds["B"]) & prior)
        self.assertLess(max(prior), 470001)

    def test_o8_thresholds_carry_exactly_the_keys_the_code_reads(self):
        """O8: derive by static reading the keys read by the forked qualify, score and gate code and the threshold
        loader, and require the frozen thresholds to contain exactly that set."""
        holders = {"limits", "gates", "qualification", "payload", "thresholds"}

        def rooted(expr) -> bool:
            """True when the expression is the thresholds object or a part of it."""
            while True:
                if isinstance(expr, ast.Name):
                    return expr.id in holders
                if isinstance(expr, ast.Call):
                    if isinstance(expr.func, ast.Name) and expr.func.id == "load_thresholds":
                        return True
                    if isinstance(expr.func, ast.Name) and expr.func.id == "dict" and expr.args:
                        expr = expr.args[0]
                        continue
                    return False
                if isinstance(expr, ast.BoolOp):
                    return any(rooted(v) for v in expr.values)
                if isinstance(expr, ast.Subscript):
                    expr = expr.value
                    continue
                return False

        read = set()
        for module, names in (("g_route4_qualification.py", ("qualify",)),
                              ("g_route4_validation.py", ("score", "unsafe_stop_gate", "correct_stop_gate", "unsafe_stop_outcome",
                                                         "correct_stop_outcome")),
                              ("g_route4_contract.py", ("load_thresholds",))):
            tree = ast.parse((TOOLS / module).read_text(encoding="utf-8"))
            for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names):
                for node in ast.walk(fn):
                    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and rooted(node.value):
                        read.add(node.slice.value)
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" \
                            and node.args and isinstance(node.args[0], ast.Constant) and rooted(node.func.value):
                        read.add(node.args[0].value)
        thresholds = contract.load_thresholds()
        frozen = set(thresholds) | set(thresholds["qualification"]) | set(thresholds["gates"])
        self.assertEqual(read, frozen, sorted(read ^ frozen))
        self.assertEqual(thresholds["qualification"]["false_clean_allowed"], 0)

    def test_the_prior_data_root_refuses_by_its_own_literal(self):
        """The data-root refusal test (static read of the prior freeze module, never imported)."""
        tree = ast.parse((TOOLS / "g_route3_freeze.py").read_text(encoding="utf-8"))
        literal = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                       and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "DATA_ROOT")
        self.assertTrue(literal.endswith("\\g_route3"))
        self.assertNotEqual(literal, freeze.DATA_ROOT)
        self.assertTrue(freeze.DATA_ROOT.endswith("\\g_route4"))

    def test_coding_is_excluded(self):
        with self.assertRaisesRegex(ValueError, "coding_positions_forbidden"):
            journal.RunSpec(call_ids=("x",), coding=frozenset({1}))
        self.assertNotIn("coding_generation_repair", contract.TASK_CLASSES)
        doc = contract.load_corpus("A")
        bad = copy.deepcopy(doc)
        bad["fixtures"][0]["validator_profile"] = "coding.v1"
        with patch.object(contract, "load_json", lambda path: bad):
            with self.assertRaisesRegex(ValueError, "corpus_coding_fixture_refused"):
                contract.load_corpus("A")
        runner_source = (TOOLS / "g_route4_runner.py").read_text(encoding="utf-8")
        for name in FORBIDDEN_MODULES:
            self.assertNotIn(f"import {name}", runner_source)
            self.assertNotIn(f"from {name}", runner_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
