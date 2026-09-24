from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from g_route1_mechanical_pilot import (
    EXPECTED_GENERATION_CALLS, FROZEN_CONTENT_DIGEST, PILOT_IDENTITY,
    PilotStore, pilot_definition, verify_pilot_definition, verify_scientific_freeze,
)
from g_route1_provider import verify_model_receipts
from g_route1_execution_contract import load_model_bindings


def receipts(**changes):
    frozen = load_model_bindings()
    rows = []
    for binding in frozen["bindings"]:
        row = {
            "provider_version": frozen["provider_version"],
            "requested_model": binding["model"], "resolved_model": binding["model"],
            "manifest_digest": binding["manifest_digest"],
            "model_blob_sha256": binding["model_blob_sha256"],
            "generation_configuration": frozen["generation_configuration"],
            "silent_fallback": False,
        }
        row.update(changes)
        rows.append(row)
    return rows


class GRoute1MechanicalPilotTests(unittest.TestCase):
    def test_definition_is_nine_synthetic_calls_across_three_models(self):
        value = pilot_definition()
        self.assertTrue(verify_pilot_definition(value)["valid"])
        self.assertEqual(len(value["calls"]), EXPECTED_GENERATION_CALLS)
        self.assertEqual({row["fixture_id"] for row in value["calls"]}, {PILOT_IDENTITY})
        self.assertEqual({row["model_tier"] for row in value["calls"]}, {"small", "mid", "large"})
        serialized = json.dumps(value).casefold()
        for forbidden in ("conv-r", "extract-r", "research-r", "synth-r", "code-r", "plan-r", "gold_id"):
            self.assertNotIn(forbidden, serialized)

    def test_definition_drift_fails_closed(self):
        value = pilot_definition()
        for mutation in (
            lambda row: row["calls"].pop(),
            lambda row: row["calls"][0].update(model="wrong:latest"),
            lambda row: row["generation_configuration"]["options"].update(temperature=0.9),
            lambda row: row.update(pilot_definition_sha256="0" * 64),
        ):
            changed = copy.deepcopy(value)
            mutation(changed)
            self.assertFalse(verify_pilot_definition(changed)["valid"])

    def test_scientific_freeze_is_current_without_authorizing_execution(self):
        result = verify_scientific_freeze()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["execution_freeze_content_sha256"], FROZEN_CONTENT_DIGEST)

    def test_model_and_config_drift_rejected(self):
        self.assertTrue(verify_model_receipts(receipts())["valid"])
        for change in (
            {"resolved_model": "wrong:latest"}, {"manifest_digest": "0" * 64},
            {"generation_configuration": {}}, {"silent_fallback": True},
        ):
            self.assertFalse(verify_model_receipts(receipts(**change))["valid"])

    def test_append_only_store_checkpoint_and_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            store = PilotStore(td, "pilot_test", create=True, definition=pilot_definition())
            record = {"call_id": "P1", "position": 1}
            store.write_call(record)
            with self.assertRaises(FileExistsError):
                store.write_call(record)
            store.write_checkpoint(next_position=2, state="paused")
            self.assertEqual(store.checkpoint()["next_position"], 2)
            self.assertIn("pilot_test", str(store.root))
            value = json.loads(store.checkpoint_path.read_text(encoding="utf-8"))
            value["next_position"] = 3
            store.checkpoint_path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                store.checkpoint()

    def test_pilot_source_has_no_scientific_runner_or_scorer_import(self):
        source = Path(__file__).with_name("g_route1_mechanical_pilot.py").read_text(encoding="utf-8")
        self.assertNotIn("g_route1_runner", source)
        self.assertNotIn("g_route1_scorer", source)
        self.assertNotIn("load_corpus", source)
        self.assertNotIn("load_gold", source)
        self.assertNotIn("validate_fixture_output", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
