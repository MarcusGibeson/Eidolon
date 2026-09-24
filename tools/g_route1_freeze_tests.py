from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import g_route1_freeze as freeze
from g_route1_contract import DATA, ROOT, digest_file


class GRoute1FreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(freeze.FREEZE_PATH.read_text(encoding="utf-8"))

    def test_checked_in_manifest_matches_all_frozen_artifacts(self) -> None:
        result = freeze.verify_manifest(self.manifest)
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["executable"])
        self.assertEqual(result["fixture_count"], 24)
        self.assertEqual(result["planned_generation_calls"], 216)

    def test_freeze_binds_every_behaviorally_relevant_fixture_artifact(self) -> None:
        required = {
            "docs/ADAPTIVE_COGNITIVE_ROUTING_BENCHMARK_DESIGN.md",
            "experiments/G-ROUTE1-candidate/FIXTURE_VALIDATOR_FREEZE_R1.json",
            "qualifications/adaptive_cognitive_routing_benchmark_design.json",
            "experiments/G-ROUTE1-candidate/corpus.json",
            "experiments/G-ROUTE1-candidate/gold.json",
            "experiments/G-ROUTE1-candidate/prompt_profiles.json",
            "experiments/G-ROUTE1-candidate/VALIDATOR_CONTRACT.md",
            "experiments/G-ROUTE1-candidate/INDEPENDENT_CORPUS_GOLD_AUDIT.md",
            "experiments/G-ROUTE1-candidate/CONTAMINATION_LEDGER.md",
            "experiments/G-ROUTE1-candidate/VALIDATOR_AUDIT.md",
            "tools/g_route1_contract.py",
            "tools/g_route1_validators.py",
            "tools/g_route1_fixture_tests.py",
            "tools/adaptive_cognitive_routing_design_tests.py",
            "tools/g_route1_freeze.py",
            "tools/g_route1_freeze_tests.py",
        }
        self.assertEqual(set(self.manifest["artifacts"]), required)
        for path, expected_digest in self.manifest["artifacts"].items():
            self.assertEqual(digest_file(ROOT / path), expected_digest, path)

    def test_artifact_digest_drift_fails_closed(self) -> None:
        for path in self.manifest["artifacts"]:
            changed = copy.deepcopy(self.manifest)
            changed["artifacts"][path] = "0" * 64
            with self.subTest(path=path):
                result = freeze.verify_manifest(changed)
                self.assertFalse(result["valid"])
                self.assertIn("manifest_mismatch:artifacts", result["reasons"])

    def test_manifest_omission_and_freeze_digest_tampering_fail_closed(self) -> None:
        omitted = copy.deepcopy(self.manifest)
        omitted.pop("independent_gold_audit_complete")
        self.assertFalse(freeze.verify_manifest(omitted)["valid"])
        changed = copy.deepcopy(self.manifest)
        changed["freeze_content_sha256"] = "0" * 64
        self.assertFalse(freeze.verify_manifest(changed)["valid"])

    def test_no_authority_can_be_enabled_in_fixture_freeze(self) -> None:
        for key in (
            "execution_freeze",
            "mechanical_pilot_authorized",
            "benchmark_execution_authorized",
            "provider_generation_authorized",
            "production_routing_authorized",
            "automatic_escalation_authorized",
            "source_apply_authorized",
        ):
            self.assertFalse(self.manifest[key], key)
            changed = copy.deepcopy(self.manifest)
            changed[key] = True
            result = freeze.verify_manifest(changed)
            self.assertFalse(result["valid"])
            self.assertIn(f"authority_must_remain_false:{key}", result["reasons"])

    def test_runner_and_execution_infrastructure_remain_absent(self) -> None:
        self.assertFalse(self.manifest["runner_implemented"])
        self.assertFalse(self.manifest["scorer_implemented"])
        self.assertFalse(self.manifest["schedule_frozen"])
        self.assertFalse(self.manifest["provider_configuration_frozen"])
        self.assertFalse(self.manifest["activity_adapter_implemented"])
        self.assertFalse(self.manifest["persistence_implemented"])
        self.assertEqual(self.manifest["provider_generation_calls"], 0)
        self.assertEqual(self.manifest["benchmark_launches"], 0)

    def test_superseded_r1_freeze_is_preserved_byte_for_byte(self) -> None:
        historical = freeze.HISTORICAL_FREEZE_PATH
        self.assertTrue(historical.is_file())
        self.assertEqual(freeze.literal_digest(historical), freeze.HISTORICAL_LITERAL_SHA256)
        preserved = json.loads(historical.read_text(encoding="utf-8"))
        self.assertEqual(preserved["freeze_id"], "G-ROUTE1-FIXTURE-VALIDATOR-R1")
        self.assertEqual(preserved["freeze_content_sha256"], freeze.HISTORICAL_CONTENT_SHA256)
        self.assertEqual(self.manifest["supersedes_freeze_id"], "G-ROUTE1-FIXTURE-VALIDATOR-R1")
        self.assertEqual(self.manifest["superseded_literal_sha256"], freeze.HISTORICAL_LITERAL_SHA256)

    def test_corpus_gold_and_prompt_profiles_did_not_change_across_the_repair(self) -> None:
        preserved = json.loads(freeze.HISTORICAL_FREEZE_PATH.read_text(encoding="utf-8"))
        for path in (
            "experiments/G-ROUTE1-candidate/corpus.json",
            "experiments/G-ROUTE1-candidate/gold.json",
            "experiments/G-ROUTE1-candidate/prompt_profiles.json",
        ):
            self.assertEqual(self.manifest["artifacts"][path], preserved["artifacts"][path], path)
        self.assertNotEqual(
            self.manifest["artifacts"]["tools/g_route1_validators.py"],
            preserved["artifacts"]["tools/g_route1_validators.py"],
        )
        self.assertTrue(self.manifest["corpus_gold_prompts_unchanged_since_r1"])

    def test_freeze_is_idempotent_and_separate_from_historical_experiments(self) -> None:
        self.assertEqual(freeze.build_manifest(), self.manifest)
        self.assertTrue((ROOT / "experiments/G-EVID1/corpus.json").is_file())
        self.assertTrue((ROOT / "experiments/G-CORROB1-candidate-r2/corpus.json").is_file())
        self.assertNotIn("G-EVID1", json.dumps(self.manifest["artifacts"]))
        self.assertNotIn("G-CORROB1", json.dumps(self.manifest["artifacts"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
