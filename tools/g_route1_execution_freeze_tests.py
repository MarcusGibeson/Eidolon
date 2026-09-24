from __future__ import annotations

import copy
import json
import unittest

import g_route1_execution_freeze as freeze
from g_route1_contract import ROOT, digest_file


class GRoute1ExecutionFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(freeze.FREEZE_PATH.read_text(encoding="utf-8"))

    def test_candidate_rebuilds_and_is_ready_but_unauthorized(self):
        result = freeze.verify_manifest(self.manifest)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["status"], "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["planned_generation_calls"], 216)
        self.assertEqual(result["provider_generation_calls"], 0)
        self.assertEqual(result["benchmark_launches"], 0)

    def test_every_bound_artifact_matches(self):
        for path, expected in self.manifest["artifacts"].items():
            self.assertEqual(digest_file(ROOT / path), expected, path)

    def test_behavioral_drift_categories_fail_closed(self):
        keywords = (
            "corpus.json", "gold.json", "prompt_profiles.json", "g_route1_validators.py",
            "g_route1_scorer.py", "schedule.json", "thresholds.json", "model_bindings.json",
            "g_route1_activity.py", "g_route1_persistence.py", "g_route1_runner.py",
        )
        for keyword in keywords:
            path = next(path for path in self.manifest["artifacts"] if keyword in path)
            changed = copy.deepcopy(self.manifest)
            changed["artifacts"][path] = "0" * 64
            with self.subTest(path=path):
                self.assertFalse(freeze.verify_manifest(changed)["valid"])

    def test_schedule_model_threshold_and_content_digests_are_bound(self):
        for key in (
            "schedule_content_sha256", "model_bindings_sha256", "thresholds_sha256",
            "fixture_freeze_content_sha256", "execution_freeze_content_sha256",
        ):
            changed = copy.deepcopy(self.manifest)
            changed[key] = "0" * 64
            self.assertFalse(freeze.verify_manifest(changed)["valid"], key)

    def test_authority_cannot_be_smuggled_into_candidate(self):
        for key in (
            "benchmark_execution_authorized", "provider_generation_authorized", "mechanical_pilot_authorized",
            "production_routing_authorized", "automatic_escalation_authorized",
            "source_mutation_authorized", "authorization_artifact_created",
        ):
            changed = copy.deepcopy(self.manifest)
            changed[key] = True
            result = freeze.verify_manifest(changed)
            self.assertFalse(result["valid"], key)
            self.assertIn(f"authority_must_remain_false:{key}", result["reasons"])

    def test_exact_three_models_and_counts_are_frozen(self):
        self.assertEqual([row["tier"] for row in self.manifest["model_identities"]], ["small", "mid", "large"])
        self.assertEqual([row["model"] for row in self.manifest["model_identities"]], ["qwen2.5:7b", "qwen3:14b", "qwen3.8:27b"])
        self.assertEqual(self.manifest["qualification_cells"], 72)
        self.assertEqual(self.manifest["planned_generation_calls"], 216)

    def test_historical_experiments_remain_present_and_unbound(self):
        self.assertTrue((ROOT / "experiments/G-EVID1/corpus.json").is_file())
        self.assertTrue((ROOT / "experiments/G-CORROB1-candidate-r2/corpus.json").is_file())
        serialized = json.dumps(self.manifest["artifacts"])
        self.assertNotIn("experiments/G-EVID1", serialized)
        self.assertNotIn("experiments/G-CORROB1", serialized)

    def test_superseded_freeze_is_preserved_exactly(self):
        self.assertEqual(freeze.literal_digest(freeze.HISTORICAL_FREEZE_PATH), freeze.HISTORICAL_LITERAL_SHA256)
        historical = json.loads(freeze.HISTORICAL_FREEZE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(historical["execution_freeze_content_sha256"], freeze.HISTORICAL_CONTENT_SHA256)
        self.assertEqual(self.manifest["supersedes_candidate_id"], historical["candidate_id"])
        self.assertEqual(self.manifest["superseded_literal_sha256"], freeze.HISTORICAL_LITERAL_SHA256)
        self.assertEqual(self.manifest["superseded_content_sha256"], freeze.HISTORICAL_CONTENT_SHA256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
