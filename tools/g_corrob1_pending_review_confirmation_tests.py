from __future__ import annotations

"""Deterministic guards for pending conversational-action confirmation."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
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
import natural_language_action_routing as routing


PACKAGE_ID = "G-CORROB1-R2-REVIEW"
MANIFEST = "a" * 64
PACKAGE = {
    "package_id": PACKAGE_ID,
    "title": "completed experiment review",
    "manifest_sha256": MANIFEST,
    "eligible": True,
}
REQUEST = "Review G-CORROB1-R2 independently."


class PendingReviewConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-pending-confirmation-")
        self.old_dir = router.CHAT_ACTIONS_DIR
        self.old_readme = router.CHAT_ACTIONS_README
        self.memory_patch = patch.object(router, "store_memory", return_value=None)
        self.memory_patch.start()
        router.CHAT_ACTIONS_DIR = Path(self.temp.name) / "chat_actions"
        router.CHAT_ACTIONS_README = router.CHAT_ACTIONS_DIR / "README.md"

    def tearDown(self) -> None:
        router.CHAT_ACTIONS_DIR = self.old_dir
        router.CHAT_ACTIONS_README = self.old_readme
        self.memory_patch.stop()
        self.temp.cleanup()

    def package_context(self, *, digest: str = MANIFEST, execute=None):
        package = {**PACKAGE, "manifest_sha256": digest}
        stack = ExitStack()
        stack.enter_context(patch.object(review_adapter, "propose_message", return_value=(package, "eligible")))
        stack.enter_context(patch.object(review_adapter, "find_package", return_value=package))
        stack.enter_context(patch.object(review_adapter, "eligible_target_ids", return_value=(PACKAGE_ID,)))
        if execute is not None:
            stack.enter_context(patch.object(review_adapter, "execute_conversational_review_action", side_effect=execute))
        return stack

    def proposal(self, *, package_id: str = PACKAGE_ID, manifest: str = MANIFEST) -> dict:
        action = router._make_action(
            REQUEST,
            "experiment_review_start",
            f"Review {package_id}",
            f"Eligible package; manifest {manifest[:16]}. Confirm to start it.",
            router.DIRECT_FUNCTION,
            risk_level="medium",
            function_name="experiment_review_start",
            function_args={"package_id": package_id, "manifest_sha256": manifest},
        )
        router._ensure_confirmation_contract(action)
        router.save_chat_action(action)
        return action

    @staticmethod
    def fake_success(calls: list[tuple[str, dict]]):
        def execute(function_name: str, args: dict, **_kwargs):
            calls.append((function_name, dict(args)))
            return {"ok": True, "message": "mock review started", "receipt": {"job_id": "job_test", "review_id": ""}}
        return execute

    def test_start_the_review_starts_the_exact_single_pending_action(self):
        calls: list[tuple[str, dict]] = []
        with self.package_context(execute=self.fake_success(calls)):
            action = self.proposal()
            projection = routing.build_natural_language_action_projection("start the review")
            self.assertEqual(projection["grounding"]["pending_review_action"]["action_id"], action["id"])
            result = routing.apply_confirmed_execution(projection)
        self.assertEqual(result["grounding"]["execution_state"], "started")
        self.assertEqual(calls, [("experiment_review_start", {"package_id": PACKAGE_ID, "manifest_sha256": MANIFEST})])
        saved = router.load_chat_action(action["id"])
        self.assertEqual(saved["status"], "executed")
        self.assertEqual(saved["lifecycle_stage"], "terminal")
        self.assertEqual(saved["confirmation"]["state"], "consumed")
        event_types = [row["type"] for row in saved["action_events"]]
        self.assertIn("operator_approval_consumed", event_types)
        self.assertIn("action_starting", event_types)
        self.assertIn("execution_claimed", event_types)
        self.assertIn("execution_completed", event_types)

    def test_go_ahead_starts_one_unambiguous_pending_review(self):
        calls: list[tuple[str, dict]] = []
        with self.package_context(execute=self.fake_success(calls)):
            action = self.proposal()
            projection = routing.build_natural_language_action_projection("go ahead")
            self.assertEqual(projection["intent"]["category"], "action_request")
            self.assertEqual(projection["grounding"]["pending_review_action"]["action_id"], action["id"])
            routing.apply_confirmed_execution(projection)
        self.assertEqual(len(calls), 1)

    def test_other_clear_phrases_resolve_only_with_one_pending_action(self):
        with self.package_context():
            action = self.proposal()
            for phrase in ("start it", "proceed", "run the review"):
                state, target, _ = router.resolve_confirmation(phrase)
                self.assertEqual((state, target["id"]), ("one", action["id"]))

    def test_no_pending_action_never_executes(self):
        calls: list[tuple[str, dict]] = []
        with self.package_context(execute=self.fake_success(calls)):
            self.assertEqual(router.resolve_confirmation("start the review")[0], "unavailable")
            projection = routing.build_natural_language_action_projection("start the review")
            routing.apply_confirmed_execution(projection)
        self.assertEqual(calls, [])

    def test_two_pending_actions_are_ambiguous_even_for_the_same_target(self):
        with self.package_context():
            first = self.proposal()
            second = self.proposal()
            self.assertNotEqual(first["id"], second["id"])
            for phrase in ("start it", "start the review", f"confirm {PACKAGE_ID}"):
                state, target, waiting = router.resolve_confirmation(phrase)
                self.assertEqual(state, "ambiguous")
                self.assertIsNone(target)
                self.assertEqual(len(waiting), 2)

    def test_expired_action_fails_closed(self):
        with self.package_context():
            expired = self.proposal()
            expired["confirmation"]["expires_at"] = "2000-01-01T00:00:00"
            router.save_chat_action(expired)
            self.assertEqual(router.run_confirmed_action(expired["id"])["refused"], "pending_action_expired")

    def test_cancelled_action_fails_closed(self):
        with self.package_context():
            cancelled = self.proposal()
            self.assertTrue(router.cancel_pending_chat_action(cancelled["id"]).ok)
            self.assertEqual(router.run_confirmed_action(cancelled["id"])["refused"], "already_resolved")

    def test_consumed_action_fails_closed(self):
        calls: list[tuple[str, dict]] = []
        with self.package_context(execute=self.fake_success(calls)):
            consumed = self.proposal()
            self.assertTrue(router.run_confirmed_action(consumed["id"])["ok"])
            self.assertEqual(router.run_confirmed_action(consumed["id"])["refused"], "already_resolved")
        self.assertEqual(len(calls), 1)

    def test_package_drift_blocks_before_the_review_adapter(self):
        calls: list[tuple[str, dict]] = []
        action = self.proposal()
        with self.package_context(digest="b" * 64, execute=self.fake_success(calls)):
            receipt = router.run_confirmed_action(action["id"])
        self.assertEqual(receipt["refused"], "pending_target_drift")
        self.assertEqual(calls, [])

    def test_follow_up_cannot_override_target_or_capability(self):
        with self.package_context():
            action = self.proposal()
            self.assertEqual(router.resolve_confirmation("run the review G-OTHER")[0], "none")
            self.assertEqual((router.load_chat_action(action["id"]) or {})["function_args"]["package_id"], PACKAGE_ID)
            for request in (
                "Execute the G-CORROB1-R2 experiment now.",
                "Change the model provider configuration.",
                "Modify the source code.",
                "Change your beliefs.",
            ):
                routed = router.propose_chat_action(request, save=False)
                self.assertNotEqual(routed.get("intent"), "experiment_review_confirm")
                self.assertNotEqual(routed.get("function_name"), "experiment_review_start")
            self.assertEqual((router.load_chat_action(action["id"]) or {})["status"], "proposed")

    def test_duplicate_approval_cannot_create_duplicate_review_runs(self):
        calls: list[tuple[str, dict]] = []
        with self.package_context(execute=self.fake_success(calls)):
            action = self.proposal()
            first = router.run_confirmed_action(action["id"])
            second = router.run_confirmed_action(action["id"])
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["refused"], "already_resolved")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
