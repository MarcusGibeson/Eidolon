"""Adversarial integrity tests for the non-authorizing G-CORROB1 freeze candidate."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

import g_corrob1_activity as activity
import g_corrob1_freeze as freeze
import g_corrob1_runner as runner
from g_corrob1_contract import canonical_digest, digest_file, load_sampling
from g_corrob1_persistence import RunStore
from g_corrob1_provider import verify_preflight_receipt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-CORROB1-candidate-r2"


def _json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _receipt() -> dict:
    environment = _json("PROVIDER_CONFIGURATION_PREFLIGHT.json")
    parameters = dict(environment["experiment_submission"])
    return {
        "provider": environment["provider"],
        "provider_version": environment["provider_version"],
        "requested_model": environment["requested_model"],
        "resolved_model": environment["resolved_model"],
        "model_content_digest": environment["model_manifest_sha256"],
        "submitted_parameters": parameters,
        "parameter_submission_support": {name: True for name in parameters},
        "seed_submission_supported": True,
        "fresh_session_per_call": True,
        "retry_limit": 0,
        "silent_fallback": False,
        "honoring_attestation": "not_provided_by_ollama",
        "provider_contacted": True,
    }


class ExecutionFreezeAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = _json("EXECUTION_FREEZE_CANDIDATE.json")

    def test_historical_candidate_is_preserved_but_current_code_invalidates_execution(self) -> None:
        candidate_path = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
        self.assertEqual(
            digest_file(candidate_path),
            "366a787cbf901f25e795d72ad4f71bd09a1f5318a51ed6549940bc9c3aff5114",
        )
        current_check = freeze.verify_execution_freeze_candidate(self.manifest)
        self.assertFalse(current_check["valid"])
        self.assertTrue(any("artifact" in reason for reason in current_check["reasons"]))
        self.assertFalse(self.manifest["pilot_authorized"])
        self.assertFalse(self.manifest["experiment_authorized"])
        self.assertFalse(freeze.verify_execution_manifest(self.manifest)["valid"])

        digest = canonical_digest(
            json.dumps(self.manifest, sort_keys=True, separators=(",", ":"))
        )
        attempted_authorization = {
            "execution_manifest": self.manifest,
            "execution_manifest_sha256": digest,
            "execution_authorized": True,
            "execution_frozen": True,
            "operator_confirmation": f"Authorize G-CORROB1-R2 execution {digest}",
        }
        self.assertFalse(runner._authorization_valid(attempted_authorization))

    def test_behavioral_artifact_drift_matrix_fails_closed(self) -> None:
        targets = {
            "corpus": "experiments/G-CORROB1-candidate-r2/corpus.json",
            "gold_and_ambiguity": "experiments/G-CORROB1-candidate-r2/gold_candidate.json",
            "prompt": "experiments/G-CORROB1-candidate-r2/prompt.txt",
            "policy_and_comparator": "tools/g_corrob1_policy.py",
            "scorer": "tools/g_corrob1_scorer.py",
            "denominators": "experiments/G-CORROB1-candidate-r2/METRICS.md",
            "thresholds": "experiments/G-CORROB1-candidate-r2/THRESHOLD_PROVENANCE.md",
            "configuration": "experiments/G-CORROB1-candidate-r2/PROVIDER_CONFIGURATION_PREFLIGHT.json",
            "seed_and_order": "experiments/G-CORROB1-candidate-r2/sampling_proposal.json",
            "activity": "tools/g_corrob1_activity.py",
            "persistence": "tools/g_corrob1_persistence.py",
            "runner": "tools/g_corrob1_runner.py",
            "gold_signoff": "experiments/G-CORROB1-candidate-r2/PREPILOT_RENEWED_GOLD_SIGNOFF.md",
        }
        self.assertTrue(set(targets.values()).issubset(self.manifest["artifacts"]))
        for label, path in targets.items():
            changed = copy.deepcopy(self.manifest)
            changed["artifacts"][path] = "0" * 64
            with self.subTest(label=label):
                self.assertFalse(freeze.verify_execution_freeze_candidate(changed)["valid"])

    def test_manifest_omission_digest_and_authority_tampering_fail_closed(self) -> None:
        mutations = []
        omitted = copy.deepcopy(self.manifest)
        omitted.pop("model_configuration_digest")
        mutations.append(omitted)
        for key, value in (
            ("execution_freeze_content_sha256", "0" * 64),
            ("model_content_digest", "0" * 64),
            ("provider_version", "different"),
            ("pilot_authorized", True),
            ("experiment_authorized", True),
        ):
            changed = copy.deepcopy(self.manifest)
            changed[key] = value
            mutations.append(changed)
        for changed in mutations:
            self.assertFalse(freeze.verify_execution_freeze_candidate(changed)["valid"])

    def test_live_preflight_must_match_frozen_provider_model_and_options(self) -> None:
        receipt = _receipt()
        self.assertTrue(verify_preflight_receipt(receipt)["valid"])
        authorization = {"execution_manifest": self.manifest}
        self.assertTrue(runner._preflight_matches_execution_manifest(receipt, authorization))
        for key, value in (
            ("provider_version", "different"),
            ("resolved_model", "fallback"),
            ("model_content_digest", "0" * 64),
        ):
            changed = copy.deepcopy(receipt)
            changed[key] = value
            self.assertFalse(
                runner._preflight_matches_execution_manifest(changed, authorization)
            )
        changed = copy.deepcopy(receipt)
        changed["submitted_parameters"]["temperature"] = 0.7
        self.assertFalse(runner._preflight_matches_execution_manifest(changed, authorization))

    def test_schedule_and_activity_contracts_are_bound_and_blind(self) -> None:
        sampling = load_sampling()
        self.assertEqual(sampling["planned_calls"], 192)
        self.assertEqual(sampling["planned_pairs"], 96)
        self.assertEqual(sampling["expected_A_first_pairs"], 48)
        self.assertEqual(sampling["expected_B_first_pairs"], 48)
        forbidden = {
            "corpus", "proposition", "semantic_assessment", "relation", "scope",
            "temporal_status", "disposition", "gold", "safe", "unsafe", "score",
        }
        self.assertFalse(forbidden & set(activity.ALLOWED_METRICS))
        self.assertIn("tools/g_corrob1_activity.py", self.manifest["artifacts"])
        self.assertIn("experiments/G-CORROB1-candidate-r2/sampling_proposal.json", self.manifest["artifacts"])

    def test_stale_run_store_cannot_be_reused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            RunStore(td, "frozen-run", create=True)
            with self.assertRaises(FileExistsError):
                RunStore(td, "frozen-run", create=True)

    def test_no_semantic_provider_or_launch_counts_are_recorded(self) -> None:
        self.assertEqual(self.manifest["semantic_generation_calls"], 0)
        self.assertEqual(self.manifest["pilot_launch_count"], 0)
        self.assertEqual(self.manifest["experiment_launch_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
