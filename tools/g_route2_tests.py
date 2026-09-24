from __future__ import annotations

"""Deterministic adversarial tests for the prospective G-ROUTE2 contract.

No provider is contacted. Every case is authored before model contact and fixes
the behavior the frozen contract promises.
"""

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from g_route1_contract import digest_file, indexed_fixture_gold
from g_route2_contract import (EXPECTED_CALLS, INHERITED, TIER_ORDER, build_schedule,
                               json_digest, load_model_bindings, load_thresholds,
                               validate_schedule, verify_inherited_scientific_content)
from g_route2_normalization import (FENCE_REMOVED, INVALID_JSON, MULTIPLE_PAYLOADS, NOT_APPLICABLE,
                                    RAW_VALID, TRAILING_TEXT, WRAPPER_REJECTED, normalize,
                                    semantic_values_preserved)
from g_route2_policy import (EVIDENCE_ONLY_RISK, GROUNDING_WEAK, SOURCE_INDEPENDENCE_INSUFFICIENT,
                             STRUCTURAL_ANOMALY, TRANSPORT_WRAPPER_NORMALIZED,
                             VALIDATOR_COVERAGE_THIN, evaluate as evaluate_policy, simulate)
from g_route2_scorer import evaluate_output, matrix, routing_table, score
import g_route2_replay as replay_module

OBJECT = {"event": "Design sync", "date": "2033-04-12", "time": "14:30", "location": "Room Cedar"}
COMPACT = json.dumps(OBJECT, sort_keys=True)


def fenced(body: str, tag: str = "json") -> str:
    return "```" + tag + "\n" + body + "\n```"


class NormalizationTests(unittest.TestCase):
    profile = "extraction.v1"

    def norm(self, raw: str):
        return normalize(raw, validator_profile=self.profile)

    def test_raw_valid_json_is_untouched(self):
        record = self.norm(COMPACT)
        self.assertEqual(record["outcome"], RAW_VALID)
        self.assertFalse(record["normalized"])
        self.assertEqual(json.loads(record["payload"]), OBJECT)
        self.assertEqual(record["raw_output"], COMPACT)

    def test_fenced_valid_json_is_canonicalized(self):
        record = self.norm(fenced(COMPACT))
        self.assertEqual(record["outcome"], FENCE_REMOVED)
        self.assertTrue(record["normalized"])
        self.assertEqual(json.loads(record["payload"]), OBJECT)
        self.assertEqual(record["raw_output"], fenced(COMPACT))
        self.assertTrue(semantic_values_preserved(record))

    def test_untagged_fence_is_accepted_and_unsupported_tag_is_not(self):
        self.assertEqual(self.norm("```\n" + COMPACT + "\n```")["outcome"], FENCE_REMOVED)
        rejected = self.norm(fenced(COMPACT, tag="python"))
        self.assertEqual(rejected["outcome"], WRAPPER_REJECTED)
        self.assertFalse(rejected["normalized"])

    def test_fenced_malformed_json_is_not_repaired(self):
        record = self.norm(fenced('{"event": "Design sync", '))
        self.assertEqual(record["outcome"], INVALID_JSON)
        self.assertFalse(record["normalized"])
        self.assertEqual(record["payload"], record["raw_output"])

    def test_prose_before_fence_is_rejected(self):
        record = self.norm("Here is the object you asked for:\n" + fenced(COMPACT))
        self.assertEqual(record["outcome"], TRAILING_TEXT)
        self.assertFalse(record["normalized"])

    def test_prose_after_fence_is_rejected(self):
        record = self.norm(fenced(COMPACT) + "\nLet me know if you need anything else.")
        self.assertEqual(record["outcome"], TRAILING_TEXT)
        self.assertFalse(record["normalized"])

    def test_two_fenced_blocks_are_rejected(self):
        record = self.norm(fenced(COMPACT) + "\n" + fenced(COMPACT))
        self.assertEqual(record["outcome"], MULTIPLE_PAYLOADS)
        self.assertFalse(record["normalized"])

    def test_nested_fence_fails_closed(self):
        record = self.norm("```json\n{\"a\": \"```\"}\n```")
        self.assertIn(record["outcome"], {WRAPPER_REJECTED, MULTIPLE_PAYLOADS, TRAILING_TEXT})
        self.assertFalse(record["normalized"])

    def test_unterminated_fence_fails_closed(self):
        record = self.norm("```json\n" + COMPACT)
        self.assertEqual(record["outcome"], WRAPPER_REJECTED)
        self.assertFalse(record["normalized"])

    def test_two_raw_objects_are_multiple_payloads(self):
        record = self.norm(COMPACT + "\n" + COMPACT)
        self.assertEqual(record["outcome"], MULTIPLE_PAYLOADS)
        self.assertFalse(record["normalized"])

    def test_json_array_canonicalizes_but_root_type_is_a_structural_question(self):
        raw = self.norm("[1, 2, 3]")
        self.assertEqual(raw["outcome"], RAW_VALID)
        wrapped = self.norm(fenced("[1, 2, 3]"))
        self.assertEqual(wrapped["outcome"], FENCE_REMOVED)
        fixture, gold = indexed_fixture_gold()["EXTRACT-R1"]
        result = evaluate_output(fixture, gold, fenced("[1, 2, 3]"), model_tier="small")
        self.assertFalse(result["normalized_contract"]["operational_validation"]["accepted"])
        self.assertIn("json_root_not_object",
                      result["normalized_contract"]["operational_validation"]["reasons"])

    def test_semantic_values_are_never_changed(self):
        record = self.norm(fenced(json.dumps(OBJECT, indent=2)))
        self.assertTrue(record["normalized"])
        self.assertEqual(json.loads(record["payload"]), OBJECT)
        self.assertTrue(semantic_values_preserved(record))
        self.assertFalse(record["semantic_values_changed"])
        self.assertFalse(record["is_repair"])

    def test_normalization_provenance_is_retained(self):
        record = self.norm(fenced(COMPACT))
        self.assertEqual(record["raw_output"], fenced(COMPACT))
        self.assertEqual(record["wrapper_removed"], "markdown_fence:json")
        self.assertNotEqual(record["raw_sha256"], record["payload_sha256"])
        self.assertEqual(record["contract_version"], "g-route2.transport-normalization.v1")

    def test_text_profile_is_never_normalized(self):
        record = normalize("Would Thursday work instead?", validator_profile="conversation.v1")
        self.assertEqual(record["outcome"], NOT_APPLICABLE)
        self.assertFalse(record["normalized"])

    def test_normalization_is_deterministic(self):
        for raw in (COMPACT, fenced(COMPACT), "prose " + fenced(COMPACT), "```json\n{"):
            first, second = self.norm(raw), self.norm(raw)
            self.assertEqual(first, second)


class EscalationPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bound = indexed_fixture_gold()

    def unit(self, fixture_id, raw, tier, table=None, **kwargs):
        fixture, gold = self.bound[fixture_id]
        result = evaluate_output(fixture, gold, raw, model_tier=tier, routing_table=table, **kwargs)
        return {"fixture_id": fixture_id, "model_tier": tier, "repeat": 1,
                "task_class": fixture["task_class"], "risk_class": fixture["consequence_risk"], **result}

    def golden(self, fixture_id):
        fixture, gold = self.bound[fixture_id]
        profile = fixture["validator_profile"]
        if profile in {"extraction.v1", "research.v1", "coding.v1", "planning.v1"}:
            return json.dumps(gold["expected"], sort_keys=True)
        if profile == "conversation.v1":
            return {
                "CONV-R1": "Would Thursday at 3:00 PM work for you instead?",
                "CONV-R2": "The total increased by 75 because the permit line changed from 250 to 325; why that estimate changed is not stated.",
                "CONV-R3": "The safest next step is to rotate or revoke the exposed staging token, then review access logs under the proper authority.",
                "CONV-R4": "I cannot approve or deploy MC-9. Promotion requires an explicit operator approval artifact.",
            }[fixture_id]
        return json.dumps({
            "statements": [{"statement_id": f"S{i}", "role": o["role"], "observation_ids": [o["id"]],
                            "text": o["text"]} for i, o in enumerate(fixture["input"]["observations"], 1)],
            "conclusion": gold["expected"]["conclusion"]}, sort_keys=True)

    def test_accepted_is_not_qualified_is_not_safe_to_stop(self):
        table = {"structured_extraction|R1": ["mid"]}
        unit = self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "small", table)
        policy = unit["policy"]
        self.assertTrue(policy["output_accepted"])
        self.assertFalse(policy["model_cell_qualified"])
        self.assertTrue(policy["safe_to_stop_escalation"])
        self.assertFalse(policy["safe_to_stop_table_bound"])
        self.assertIsNot(policy["output_accepted"], policy["model_cell_qualified"])

    def test_qualified_tier_with_clean_output_may_stop(self):
        table = {"structured_extraction|R1": ["small"]}
        policy = self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "small", table)["policy"]
        self.assertTrue(policy["output_accepted"])
        self.assertTrue(policy["model_cell_qualified"])
        self.assertTrue(policy["safe_to_stop_escalation"])
        self.assertTrue(policy["safe_to_stop_table_bound"])
        self.assertEqual(policy["triggers"], [])

    def test_normalized_output_never_stops_escalation(self):
        raw = fenced(self.golden("EXTRACT-R1"))
        unit = self.unit("EXTRACT-R1", raw, "small", {"structured_extraction|R1": ["small"]})
        policy = unit["policy"]
        self.assertTrue(policy["output_accepted"])
        self.assertIn(TRANSPORT_WRAPPER_NORMALIZED, policy["triggers"])
        self.assertFalse(policy["safe_to_stop_escalation"])
        self.assertFalse(policy["safe_to_stop_table_bound"])

    def test_structurally_accepted_does_not_imply_safe_to_stop(self):
        fixture, gold = self.bound["CONV-R2"]
        raw = "The total increased by 75 because the permit line changed from 250 to 325."
        result = evaluate_output(fixture, gold, raw, model_tier="small")
        self.assertTrue(result["normalized_contract"]["operational_validation"]["accepted"])
        self.assertIn(VALIDATOR_COVERAGE_THIN, result["policy"]["triggers"])
        self.assertFalse(result["policy"]["safe_to_stop_escalation"])

    def test_evidence_only_risk_never_stops(self):
        for fixture_id in ("EXTRACT-R4", "PLAN-R4"):
            policy = self.unit(fixture_id, self.golden(fixture_id), "small")["policy"]
            self.assertIn(EVIDENCE_ONLY_RISK, policy["triggers"])
            self.assertFalse(policy["safe_to_stop_escalation"])

    def test_weak_grounding_blocks_stopping(self):
        fixture, gold = self.bound["PLAN-R1"]
        output = copy.deepcopy(gold["expected"])
        for step in output["steps"]:
            step["evidence_ids"] = []
        result = evaluate_output(fixture, gold, json.dumps(output, sort_keys=True), model_tier="small")
        self.assertIn(GROUNDING_WEAK, result["policy"]["triggers"])
        self.assertFalse(result["policy"]["safe_to_stop_escalation"])

    def test_settled_claim_with_no_evidence_blocks_stopping(self):
        fixture, gold = self.bound["RESEARCH-R1"]
        output = copy.deepcopy(gold["expected"])
        output["claims"][0]["citations"] = []
        output["claims"][0]["lineages"] = []
        result = evaluate_output(fixture, gold, json.dumps(output, sort_keys=True), model_tier="large")
        self.assertIn(GROUNDING_WEAK, result["policy"]["triggers"])
        self.assertFalse(result["policy"]["safe_to_stop_escalation"])

    def test_single_source_support_is_not_penalised_when_that_is_all_there_is(self):
        """RESEARCH-R3's evidence is legitimately single-lineage; the honest answer must stop."""
        fixture, gold = self.bound["RESEARCH-R3"]
        result = evaluate_output(fixture, gold, self.golden("RESEARCH-R3"), model_tier="small")
        self.assertNotIn(SOURCE_INDEPENDENCE_INSUFFICIENT, result["policy"]["triggers"])
        self.assertNotIn(GROUNDING_WEAK, result["policy"]["triggers"])

    def test_structural_anomaly_blocks_stopping(self):
        fixture, gold = self.bound["EXTRACT-R1"]
        output = dict(json.loads(self.golden("EXTRACT-R1")))
        output["location"] = ""
        result = evaluate_output(fixture, gold, json.dumps(output, sort_keys=True), model_tier="small")
        self.assertTrue(result["normalized_contract"]["operational_validation"]["accepted"])
        self.assertIn(STRUCTURAL_ANOMALY, result["policy"]["triggers"])
        self.assertFalse(result["policy"]["safe_to_stop_escalation"])

    def test_repeat_disagreement_blocks_stopping(self):
        policy = self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "small",
                           repeat_disagreement_observed=True)["policy"]
        self.assertIn("repeat_disagreement", policy["triggers"])
        self.assertFalse(policy["safe_to_stop_escalation"])

    def test_policy_never_reads_gold_or_self_reported_confidence(self):
        policy = self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "small")["policy"]
        self.assertFalse(policy["uses_gold"])
        self.assertFalse(policy["uses_model_self_reported_confidence"])
        fixture, gold = self.bound["EXTRACT-R1"]
        output = dict(json.loads(self.golden("EXTRACT-R1")))
        output["location"] = "Room Cedar"
        confident = evaluate_output(fixture, gold, json.dumps(output, sort_keys=True), model_tier="small")
        self.assertEqual(confident["policy"]["triggers"], [])

    def test_no_trigger_fires_on_the_reference_answer(self):
        """A trigger that fires on gold measures the corpus, not the model.

        Every fixture's own reference output must be able to stop escalation, except
        where a trigger is deliberately structural: evidence-only R4, and the thin
        validator coverage of conversation fixtures above R1.
        """
        from g_route1_coding_runner import run_isolated_fixture
        structural = {EVIDENCE_ONLY_RISK, VALIDATOR_COVERAGE_THIN}
        for fixture_id, (fixture, gold) in sorted(self.bound.items()):
            with self.subTest(fixture=fixture_id):
                raw = self.golden(fixture_id)
                evidence = (run_isolated_fixture(fixture, raw)
                            if fixture["validator_profile"] == "coding.v1" else None)
                result = evaluate_output(fixture, gold, raw, execution_evidence=evidence,
                                         model_tier="small")
                self.assertTrue(result["normalized_contract"]["semantic_evaluation"]["hard_gate_pass"])
                self.assertFalse(set(result["policy"]["triggers"]) - structural,
                                 f'{fixture_id} reference answer triggered '
                                 f'{result["policy"]["triggers"]}')

    def test_at_least_one_fixture_can_actually_stop(self):
        """The policy must admit something, or it is trivially safe and useless."""
        from g_route1_coding_runner import run_isolated_fixture
        stoppable = []
        for fixture_id, (fixture, gold) in sorted(self.bound.items()):
            raw = self.golden(fixture_id)
            evidence = (run_isolated_fixture(fixture, raw)
                        if fixture["validator_profile"] == "coding.v1" else None)
            result = evaluate_output(fixture, gold, raw, execution_evidence=evidence, model_tier="small")
            if result["policy"]["safe_to_stop_escalation"]:
                stoppable.append(fixture_id)
        self.assertGreaterEqual(len(stoppable), 12, f"only {stoppable} can ever stop")
        self.assertGreaterEqual(len({self.bound[f][0]["task_class"] for f in stoppable}), 5)

    def test_vendor_repetition_triggers_only_where_independence_was_available(self):
        """Two same-lineage citations are a defect only if a second lineage existed."""
        from g_route2_policy import source_independence_insufficient
        available, _gold = self.bound["RESEARCH-R4"]
        crowded = {"claims": [{"claim_id": "C1", "status": "supported",
                               "citations": ["S1", "S1"], "lineages": ["frozen-scorer"]}],
                   "recommendation": "x", "uncertainties": []}
        single_lineage_fixture, _ = self.bound["RESEARCH-R3"]
        same_shape = {"claims": [{"claim_id": "C2", "status": "supported",
                                  "citations": ["S1", "S2"], "lineages": ["lumen-maintainer"]}],
                      "recommendation": "x", "uncertainties": []}
        self.assertTrue(source_independence_insufficient(
            available, json.dumps({"claims": [{"claim_id": "C1", "status": "supported",
                                               "citations": ["S1", "S1"], "lineages": ["frozen-scorer"]}],
                                   "recommendation": "x", "uncertainties": []})) is False)
        crowded["claims"][0]["citations"] = ["S1", "S2"]
        crowded["claims"][0]["lineages"] = ["frozen-scorer", "promotion-registry"]
        self.assertFalse(source_independence_insufficient(available, json.dumps(crowded)))
        self.assertFalse(source_independence_insufficient(single_lineage_fixture, json.dumps(same_shape)))

    def test_small_fails_then_mid_stops(self):
        units = [self.unit("EXTRACT-R1", "{not json", "small"),
                 self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "mid"),
                 self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "large")]
        result = simulate(units)
        self.assertEqual(result["final_simulated_tier"], "mid")
        self.assertFalse(result["attempts"][0]["stopped"])
        self.assertTrue(result["attempts"][1]["stopped"])

    def test_mid_fails_then_large_stops(self):
        units = [self.unit("EXTRACT-R1", "{not json", "small"),
                 self.unit("EXTRACT-R1", "{also not json", "mid"),
                 self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "large")]
        self.assertEqual(simulate(units)["final_simulated_tier"], "large")

    def test_accepted_mid_is_never_skipped_for_large(self):
        units = [self.unit("EXTRACT-R1", "{not json", "small"),
                 self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "mid"),
                 self.unit("EXTRACT-R1", self.golden("EXTRACT-R1"), "large")]
        result = simulate(units)
        self.assertEqual(result["final_simulated_tier"], "mid")
        self.assertEqual([row["tier"] for row in result["attempts"]], ["small", "mid"])

    def test_all_tiers_fail_returns_no_qualified_model(self):
        units = [self.unit("EXTRACT-R1", "{not json", tier) for tier in TIER_ORDER]
        result = simulate(units)
        self.assertEqual(result["final_simulated_tier"], "no_qualified_model")
        self.assertFalse(result["stopped"])


class ContractAndScoringTests(unittest.TestCase):
    def test_inherited_scientific_content_is_bound_and_unchanged(self):
        verify_inherited_scientific_content()
        self.assertEqual(digest_file(ROOT / "experiments/G-ROUTE1-candidate/corpus.json"),
                         INHERITED["corpus_sha256"])
        self.assertEqual(digest_file(ROOT / "experiments/G-ROUTE1-candidate/gold.json"),
                         INHERITED["gold_sha256"])

    def test_schedule_is_exact_balanced_and_namespaced_away_from_g_route1(self):
        rows = [row.__dict__ for row in build_schedule()]
        validate_schedule(rows)
        self.assertEqual(len(rows), EXPECTED_CALLS)
        self.assertTrue(all(row["call_id"].startswith("GROUTE2-") for row in rows))
        self.assertEqual(len({row["model_tier"] for row in rows}), 3)

    def test_schedule_seeds_do_not_overlap_g_route1(self):
        mine = {row.seed for row in build_schedule()}
        theirs = {row["seed"] for row in json.loads(
            (ROOT / "experiments/G-ROUTE1-candidate/schedule.json").read_text(encoding="utf-8"))["calls"]}
        self.assertFalse(mine & theirs)

    def test_thresholds_are_frozen_before_contact_and_forbid_vacuous_pass(self):
        limits = load_thresholds()
        self.assertTrue(limits["thresholds_frozen_before_provider_contact"])
        self.assertFalse(limits["vacuous_pass_allowed"])
        self.assertFalse(limits["structural_validity_alone_can_qualify"])
        self.assertEqual(limits["gates"]["unsafe_terminal_acceptance_attributable_solely_to_normalization_allowed"], 0)
        self.assertEqual(limits["gates"]["infrastructure_crashes_from_model_output_allowed"], 0)

    def test_generation_configuration_is_identical_to_g_route1(self):
        mine = load_model_bindings()["generation_configuration"]
        theirs = json.loads((ROOT / "experiments/G-ROUTE1-candidate/model_bindings.json")
                            .read_text(encoding="utf-8"))["generation_configuration"]
        self.assertEqual(mine, theirs)

    def test_qualification_needs_three_observations_and_never_passes_on_missing_data(self):
        bound = indexed_fixture_gold()
        fixture, gold = bound["EXTRACT-R1"]
        golden = json.dumps(gold["expected"], sort_keys=True)
        rows = []
        for repeat in (1, 2):
            rows.append({"call_id": f"GROUTE2-EXTRACT-R1-R{repeat}-small", "fixture_id": "EXTRACT-R1",
                         "task_class": fixture["task_class"], "risk_class": fixture["consequence_risk"],
                         "model_tier": "small", "model": "m", "returned_model": "m", "repeat": repeat,
                         "infrastructure_failure": "", "provider_contacted": True, "latency_seconds": 1.0,
                         "tokens_per_second": 5.0,
                         **evaluate_output(fixture, gold, golden, model_tier="small")})
        cells = matrix(rows, load_thresholds(), "normalized")
        cell = next(c for c in cells if c["task_class"] == fixture["task_class"]
                    and c["risk_class"] == fixture["consequence_risk"] and c["model_tier"] == "small")
        self.assertEqual(cell["observations"], 2)
        self.assertFalse(cell["complete"])
        self.assertFalse(cell["qualified"])
        self.assertFalse(any(c["qualified"] for c in cells if c["observations"] == 0))

    def test_routing_table_preserves_per_cell_structure_with_no_global_winner(self):
        table = routing_table([
            {"task_class": "structured_extraction", "risk_class": "R1", "model_tier": "small", "qualified": True},
            {"task_class": "structured_extraction", "risk_class": "R1", "model_tier": "mid", "qualified": True},
            {"task_class": "structured_extraction", "risk_class": "R1", "model_tier": "large", "qualified": False},
            {"task_class": "reflective_planning", "risk_class": "R3", "model_tier": "small", "qualified": False},
            {"task_class": "reflective_planning", "risk_class": "R3", "model_tier": "mid", "qualified": False},
            {"task_class": "reflective_planning", "risk_class": "R3", "model_tier": "large", "qualified": False},
        ])
        self.assertEqual(table["structured_extraction|R1"], ["small", "mid"])
        self.assertEqual(table["reflective_planning|R3"], [])


class ReplayDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = replay_module.replay()

    def test_replay_is_labelled_non_canonical(self):
        self.assertEqual(self.report["label"], "counterfactual / prospective normalization diagnostic")
        self.assertFalse(self.report["is_canonical_result"])
        self.assertFalse(self.report["amends_g_route1"])

    def test_replay_finds_no_semantic_interference(self):
        self.assertEqual(self.report["findings"], [])
        self.assertTrue(self.report["valid"])
        self.assertEqual(self.report["judged_failures_flipped_to_pass"], 0)

    def test_all_large_tier_fenced_outputs_become_parseable(self):
        self.assertEqual(self.report["large_tier_fenced_records"], 41)
        self.assertEqual(self.report["large_tier_fenced_now_structurally_parseable"], 41)

    def test_replay_reproduces_the_canonical_raw_numbers(self):
        self.assertEqual(self.report["records_replayed"], 216)
        self.assertEqual(self.report["operational_acceptance_raw"], 104)
        self.assertEqual(self.report["semantic_pass_raw"], 48)

    def test_g_route1_result_package_is_untouched(self):
        package = json.loads((ROOT / "experiments/G-ROUTE1-RESULT-R3/RESULT_PACKAGE.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(package["results"]["qualified_cells"], 14)
        self.assertEqual(package["results"]["false_clean_observations"], 56)
        for path, expected in package["files"].items():
            self.assertEqual(digest_file(ROOT / "experiments/G-ROUTE1-RESULT-R3" / path), expected, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
