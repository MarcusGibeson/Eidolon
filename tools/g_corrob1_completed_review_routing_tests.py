from __future__ import annotations

"""Deterministic routing guards for completed G-CORROB1 review requests."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

import chat_action_router as router
import conversational_experiment_review as review_adapter


PACKAGE = {
    "package_id": "G-CORROB1-R2",
    "title": "G-CORROB1-R2 completed experiment review package",
    "manifest_sha256": "a" * 64,
    "eligible": True,
}

BASE_REQUEST = """Review the completed frozen G-CORROB1-R2 experiment independently.
This is a read-only, non-authoritative research review.
Do not modify beliefs, memories, source code, experiment artifacts, gold, thresholds, policy, configuration, provider state, or model state.
Do not change gold based on observed model behavior.
Stop after the review and wait for external audit."""


class CompletedExperimentReviewRoutingTests(unittest.TestCase):
    def route(self, text: str) -> tuple[dict, list[str]]:
        selected: list[str] = []

        def propose(name: str):
            selected.append(name)
            return PACKAGE, "The selected completed package is eligible for independent review."

        with patch.object(review_adapter, "propose_message", side_effect=propose):
            action = router.propose_chat_action(text, save=False)
        return action, selected

    def test_completed_experiment_review_routes_to_existing_governed_selector(self):
        action, selected = self.route(BASE_REQUEST)
        self.assertEqual(selected, ["G-CORROB1-R2"])
        self.assertEqual(action["intent"], "experiment_review_start")
        self.assertEqual(action["function_name"], "experiment_review_start")
        self.assertEqual(action["function_args"], {"package_id": "G-CORROB1-R2"})
        self.assertEqual(action["execution_mode"], router.DIRECT_FUNCTION)

    def test_model_and_provider_metadata_do_not_become_management(self):
        text = BASE_REQUEST.replace(
            "Stop after the review",
            "Assess the recorded qwen3.8 model identity and Ollama provider metadata. Stop after the review",
        )
        action, selected = self.route(text)
        self.assertEqual(selected, ["G-CORROB1-R2"])
        self.assertEqual(action["intent"], "experiment_review_start")

    def test_provider_configuration_change_remains_blocked(self):
        action = router.propose_chat_action("Change the model provider configuration to another provider.", save=False)
        self.assertEqual(action["intent"], "blocked_model_provider_management")
        self.assertEqual(action["execution_mode"], router.BLOCKED)

    def test_unapproved_rerun_does_not_enter_review_or_execution(self):
        action = router.propose_chat_action("Rerun the G-CORROB1-R2 experiment now.", save=False)
        self.assertNotEqual(action.get("intent"), "experiment_review_start")
        self.assertNotEqual(action.get("intent"), "authorized_frozen_experiment_execution")
        self.assertEqual(action["intent"], "blocked_experiment_execution_without_authorization")
        self.assertEqual(action["execution_mode"], router.BLOCKED)

        exact = router.propose_chat_action("Execute authorized frozen experiment G-CORROB1-R2.", save=False)
        self.assertEqual(exact["intent"], "authorized_frozen_experiment_execution")

    def test_source_and_belief_mutation_requests_do_not_enter_review(self):
        for addition in (
            " Also modify the source code after reviewing it.",
            " Also change beliefs after reviewing it.",
        ):
            action, selected = self.route(BASE_REQUEST + addition)
            self.assertEqual(selected, [])
            self.assertNotEqual(action.get("intent"), "experiment_review_start")
            self.assertEqual(action["execution_mode"], router.BLOCKED)

    def test_review_boundary_is_non_authoritative_and_content_minimized(self):
        action, _ = self.route(BASE_REQUEST)
        serialized_args = json.dumps(action["function_args"], sort_keys=True)
        self.assertEqual(serialized_args, '{"package_id": "G-CORROB1-R2"}')
        self.assertIn("non-authoritative", action["explanation"])
        for forbidden in ("source code", "change gold", "model behavior", "external audit"):
            self.assertNotIn(forbidden, serialized_args)

    def test_routing_never_starts_review_or_contacts_provider(self):
        with patch.object(review_adapter, "start_review", side_effect=AssertionError("review_started")) as start:
            action, _ = self.route(BASE_REQUEST)
        self.assertEqual(action["status"], "proposed")
        start.assert_not_called()

    def test_live_selector_still_fails_closed_without_an_installed_package(self):
        with patch.object(review_adapter, "eligible_packages", return_value=[]):
            action = router.propose_chat_action(BASE_REQUEST, save=False)
        self.assertEqual(action["intent"], "experiment_review_unavailable")
        self.assertEqual(action["execution_mode"], router.BLOCKED)


if __name__ == "__main__":
    unittest.main()
