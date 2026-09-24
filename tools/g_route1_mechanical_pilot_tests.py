from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from g_route1_mechanical_pilot import (
    EXPECTED_GENERATION_CALLS, FROZEN_CONTENT_DIGEST, PILOT_IDENTITY,
    PilotStore, pilot_definition, run_resume, verify_pilot_definition,
    verify_scientific_freeze, verify_terminal_views,
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
    def _completed_store(self, root: str) -> tuple[PilotStore, dict]:
        definition = pilot_definition()
        store = PilotStore(root, "pilot_complete", create=True, definition=definition)
        for call in definition["calls"]:
            store.write_call({"call_id": call["call_id"], "position": call["position"]})
            store.write_checkpoint(next_position=call["position"] + 1, state="running")
        receipt = {
            "contract_version": "g-route1.mechanical-pilot-terminal.v1",
            "pilot_id": "pilot_complete", "state": "complete",
            "generation_calls": EXPECTED_GENERATION_CALLS,
        }
        store.write_terminal_receipt(receipt)
        store.finish("complete", "mechanical_pilot_complete")
        return store, {"state": "complete"}

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

    def test_successful_terminalization_seals_all_views_at_exact_position(self):
        with tempfile.TemporaryDirectory() as td:
            store, activity = self._completed_store(td)
            call_bytes = {
                path.name: path.read_bytes() for path in (store.root / "calls").glob("*.json")
            }
            checkpoint = store.seal_terminal_checkpoint(
                state="complete", expected_calls=EXPECTED_GENERATION_CALLS,
            )
            result = verify_terminal_views(
                store, activity, expected_calls=EXPECTED_GENERATION_CALLS,
            )
            self.assertTrue(result["valid"], result)
            self.assertEqual(checkpoint["state"], "complete")
            self.assertEqual(checkpoint["completed_position"], EXPECTED_GENERATION_CALLS)
            self.assertEqual(checkpoint["next_position"], EXPECTED_GENERATION_CALLS + 1)
            self.assertEqual(
                call_bytes,
                {path.name: path.read_bytes() for path in (store.root / "calls").glob("*.json")},
            )

    def test_terminal_checkpoint_is_idempotent_and_resume_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            store, _ = self._completed_store(td)
            first = store.seal_terminal_checkpoint(
                state="complete", expected_calls=EXPECTED_GENERATION_CALLS,
            )
            before = store.checkpoint_path.read_bytes()
            second = store.seal_terminal_checkpoint(
                state="complete", expected_calls=EXPECTED_GENERATION_CALLS,
            )
            self.assertEqual(first, second)
            self.assertEqual(before, store.checkpoint_path.read_bytes())
            with self.assertRaisesRegex(ValueError, "pilot_not_paused"):
                run_resume(
                    pilot_id="pilot_complete", root=Path(td), activity_root=Path(td),
                    endpoint="http://127.0.0.1:1", authorization_digest=FROZEN_CONTENT_DIGEST,
                )

    def test_incomplete_pilot_cannot_be_falsely_sealed_complete(self):
        with tempfile.TemporaryDirectory() as td:
            store = PilotStore(td, "pilot_incomplete", create=True, definition=pilot_definition())
            store.write_call({"call_id": "P1", "position": 1})
            store.write_checkpoint(next_position=2, state="running")
            store.finish("incomplete", "provider_failure")
            with self.assertRaises(FileNotFoundError):
                store.seal_terminal_checkpoint(
                    state="complete", expected_calls=EXPECTED_GENERATION_CALLS,
                )
            self.assertEqual(store.checkpoint()["state"], "running")

    def test_paused_checkpoint_remains_valid_and_resumable(self):
        with tempfile.TemporaryDirectory() as td:
            store = PilotStore(td, "pilot_paused", create=True, definition=pilot_definition())
            store.write_call({"call_id": "P1", "position": 1})
            checkpoint = store.write_checkpoint(next_position=2, state="paused")
            store.update(state="paused")
            self.assertEqual(checkpoint["state"], "paused")
            self.assertEqual(store.checkpoint()["next_position"], 2)
            self.assertEqual(store.manifest()["state"], "paused")

    def test_pilot_source_has_no_scientific_runner_or_scorer_import(self):
        source = Path(__file__).with_name("g_route1_mechanical_pilot.py").read_text(encoding="utf-8")
        self.assertNotIn("g_route1_runner", source)
        self.assertNotIn("g_route1_scorer", source)
        self.assertNotIn("load_corpus", source)
        self.assertNotIn("load_gold", source)
        self.assertNotIn("validate_fixture_output", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
