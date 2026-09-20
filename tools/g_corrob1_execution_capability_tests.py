from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import inspect
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
AGENT = ROOT / "conscious_agent"
for path in (str(TOOLS), str(AGENT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import authorized_frozen_experiment_execution as capability
import chat_action_router
import g_corrob1_execution_capability_freeze as freeze
import g_corrob1_runner as runner


def authorized_manifest() -> dict:
    candidate = freeze.build_candidate()
    row = dict(candidate)
    row.update({
        "authorization_manifest_contract": "g-corrob1.r2.authorized-execution-manifest.1",
        "execution_base_candidate_sha256": freeze.digest_file(freeze.CANDIDATE),
        "status": "execution_frozen_authorized_for_one_run",
        "execution_authorized": True,
        "full_experiment_authorized": True,
        "provider_contact_authorized": True,
    })
    content = dict(row)
    row["authorized_manifest_content_sha256"] = freeze.canonical_digest(
        json.dumps(content, sort_keys=True, separators=(",", ":"))
    )
    return row


def authorization(identifier: str = "gcorrob1exec_auth_test", **changes) -> dict:
    manifest = authorized_manifest()
    digest = freeze.execution_manifest_sha256(manifest)
    issued = datetime.now(timezone.utc) - timedelta(minutes=1)
    row = {
        "contract_version": "g-corrob1.r2.operator-execution-authorization.1",
        "authorization_id": identifier,
        "manifest_id": capability.MANIFEST_ID,
        "execution_manifest": manifest,
        "execution_manifest_sha256": digest,
        "authorization_scope": capability.AUTHORIZATION_SCOPE,
        "one_run_only": True,
        "execution_frozen": True,
        "execution_authorized": True,
        "full_experiment_authorized": True,
        "provider_contact_authorized": True,
        "expected_generation_calls": 192,
        "expected_pairs": 96,
        "operator_confirmation": f"Authorize G-CORROB1-R2 frozen execution {digest}",
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": (issued + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        "belief_effects": "none",
    }
    row.update(changes)
    return row


def save_authorization(root: Path, row: dict) -> Path:
    directory = root / "experiment_execution_authorizations" / capability.MANIFEST_ID
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (row["authorization_id"] + ".json")
    path.write_text(json.dumps(row), encoding="utf-8")
    return path


def preflight() -> dict:
    candidate = freeze.build_candidate()
    parameters = dict(candidate["submitted_parameters"])
    return {
        "provider": candidate["model_provider"],
        "provider_version": candidate["provider_version"],
        "requested_model": candidate["requested_model"],
        "resolved_model": candidate["resolved_model"],
        "model_content_digest": candidate["model_content_digest"],
        "submitted_parameters": parameters,
        "parameter_submission_support": {name: True for name in parameters},
        "seed_submission_supported": True,
        "fresh_session_per_call": True,
        "retry_limit": 0,
        "silent_fallback": False,
        "honoring_attestation": "not_provided_by_ollama",
        "provider_contacted": False,
    }


class Adapter:
    def __init__(self) -> None:
        self.inspections = 0

    def inspect_model(self, model, *, allow_provider_contact=False):
        self.inspections += 1
        return {"provider_contacted": True}


class ExecutionCapabilityTests(unittest.TestCase):
    def test_exact_command_and_router_are_narrow(self):
        exact = "Execute authorized frozen experiment G-CORROB1-R2."
        self.assertEqual(capability.parse_authorized_experiment_command(exact), capability.MANIFEST_ID)
        for text in (
            "execute an authorized experiment", "execute authorized frozen experiment ../secret",
            "execute authorized frozen experiment G-CORROB1-R2 with another model",
            "authorize frozen experiment G-CORROB1-R2",
        ):
            self.assertEqual(capability.parse_authorized_experiment_command(text), "")
        action = chat_action_router.propose_chat_action(exact, save=False)
        self.assertEqual(action["intent"], "authorized_frozen_experiment_execution")
        self.assertEqual(action["function_args"], {"manifest_id": capability.MANIFEST_ID})
        self.assertNotIn("path", json.dumps(action["function_args"]))
        signature = inspect.signature(capability.execute_authorized_frozen_experiment)
        self.assertEqual(list(signature.parameters), ["manifest_id"])
        process_signature = inspect.signature(capability.process_authorized_frozen_experiment_command)
        self.assertEqual(list(process_signature.parameters), ["text", "cancel_event"])
        self.assertNotIn("create_authorization", dir(capability))

    def test_candidate_is_non_authorizing_and_authorized_manifest_is_exact(self):
        candidate = freeze.build_candidate()
        self.assertTrue(freeze.verify_candidate(candidate)["valid"])
        self.assertFalse(candidate["execution_authorized"])
        self.assertFalse(candidate["full_experiment_authorized"])
        self.assertFalse(candidate["provider_contact_authorized"])
        manifest = authorized_manifest()
        self.assertTrue(freeze.verify_authorized_execution_manifest(manifest)["valid"])
        for field in ("artifacts", "submitted_parameters", "expected_generation_calls", "requested_model"):
            changed = deepcopy(manifest)
            changed[field] = {} if isinstance(changed[field], dict) else "changed"
            self.assertFalse(freeze.verify_authorized_execution_manifest(changed)["valid"], field)

    def test_authorization_tampering_staleness_scope_and_overrides_fail(self):
        self.assertTrue(capability.verify_execution_authorization(authorization())["valid"])
        mutations = {
            "missing_full_authority": {"full_experiment_authorized": False},
            "wrong_scope": {"authorization_scope": "anything"},
            "wrong_counts": {"expected_generation_calls": 2},
            "wrong_manifest": {"manifest_id": "OTHER"},
            "belief_effect": {"belief_effects": "allowed"},
            "stale": {"expires_at": "2020-01-01T00:00:00Z"},
        }
        for name, change in mutations.items():
            with self.subTest(name=name):
                self.assertFalse(capability.verify_execution_authorization(authorization(**change))["valid"])
        extra = authorization()
        extra["provider_override"] = "other"
        self.assertFalse(capability.verify_execution_authorization(extra)["valid"])

    def test_missing_and_multiple_authorizations_fail_before_provider(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = Adapter()
            with self.assertRaises(PermissionError):
                capability._execute_authorized_frozen_experiment(
                    capability.MANIFEST_ID, runtime_root=td, provider_adapter=adapter
                )
            self.assertEqual(adapter.inspections, 0)
            root = Path(td)
            save_authorization(root, authorization("gcorrob1exec_auth_one"))
            save_authorization(root, authorization("gcorrob1exec_auth_two"))
            with self.assertRaises(PermissionError):
                capability._execute_authorized_frozen_experiment(
                    capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter
                )
            self.assertEqual(adapter.inspections, 0)

    def test_malformed_authorization_and_pre_cancel_fail_without_generation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            directory = root / "experiment_execution_authorizations" / capability.MANIFEST_ID
            directory.mkdir(parents=True)
            (directory / "broken.json").write_text("{not json", encoding="utf-8")
            adapter = Adapter()
            with self.assertRaises(PermissionError):
                capability._execute_authorized_frozen_experiment(
                    capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter
                )
            self.assertEqual(adapter.inspections, 0)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth = authorization("gcorrob1exec_auth_precancel")
            save_authorization(root, auth)
            cancelled = threading.Event()
            cancelled.set()
            adapter = Adapter()
            result = capability._execute_authorized_frozen_experiment(
                capability.MANIFEST_ID,
                runtime_root=root,
                provider_adapter=adapter,
                activity=object(),
                cancel_event=cancelled,
            )
            self.assertEqual(result["state"], "cancelled")
            self.assertEqual(adapter.inspections, 0)
            marker = root / "experiment_execution_consumptions" / (auth["authorization_id"] + ".json")
            self.assertTrue(marker.is_file())

    def test_valid_authorization_consumed_before_runner_and_replay_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth = authorization("gcorrob1exec_auth_once")
            save_authorization(root, auth)
            adapter = Adapter()
            observed = {}

            def fake_execute(**kwargs):
                marker = root / "experiment_execution_consumptions" / (auth["authorization_id"] + ".json")
                observed["consumed_before_runner"] = marker.is_file()
                observed["synthetic_fixture"] = kwargs["synthetic_fixture"]
                run = Path(kwargs["run_root"]) / kwargs["run_id"]
                run.mkdir(parents=True)
                (run / "run.json").write_text(json.dumps({"provider_contacts": 192}), encoding="utf-8")
                (run / "score.json").write_text("{}", encoding="utf-8")
                return {"run_id": kwargs["run_id"], "state": "complete", "store": str(run), "valid_verdict": True}

            with patch("g_corrob1_runner.execute", side_effect=fake_execute):
                first = capability._execute_authorized_frozen_experiment(
                    capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter, activity=object()
                )
                self.assertEqual(first["state"], "complete")
                self.assertEqual(first["provider_call_count"], 192)
                self.assertTrue(observed["consumed_before_runner"])
                self.assertFalse(observed["synthetic_fixture"])
                with self.assertRaises(PermissionError):
                    capability._execute_authorized_frozen_experiment(
                        capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter, activity=object()
                    )
                second_auth = authorization("gcorrob1exec_auth_second")
                save_authorization(root, second_auth)
                second = capability._execute_authorized_frozen_experiment(
                    capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter, activity=object()
                )
                self.assertEqual(second["state"], "complete")
            self.assertEqual(adapter.inspections, 2)

    def test_failed_and_cancelled_runs_consume_authorization(self):
        for name, raised in (("failed", RuntimeError("fixture")), ("cancelled", KeyboardInterrupt())):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                auth = authorization("gcorrob1exec_auth_" + name)
                save_authorization(root, auth)
                adapter = Adapter()
                with patch("g_corrob1_runner.execute", side_effect=raised):
                    if isinstance(raised, KeyboardInterrupt):
                        with self.assertRaises(KeyboardInterrupt):
                            capability._execute_authorized_frozen_experiment(
                                capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter, activity=object()
                            )
                    else:
                        result = capability._execute_authorized_frozen_experiment(
                            capability.MANIFEST_ID, runtime_root=root, provider_adapter=adapter, activity=object()
                        )
                        self.assertEqual(result["state"], "failed")
                marker = root / "experiment_execution_consumptions" / (auth["authorization_id"] + ".json")
                self.assertTrue(marker.is_file())

    def test_concurrent_duplicate_invocation_allows_only_one_runner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth = authorization("gcorrob1exec_auth_concurrent")
            save_authorization(root, auth)
            barrier = threading.Barrier(2)
            results = []

            def attempt():
                barrier.wait()
                try:
                    capability._execute_authorized_frozen_experiment(
                        capability.MANIFEST_ID, runtime_root=root, provider_adapter=Adapter(), activity=object()
                    )
                    results.append("ran")
                except PermissionError:
                    results.append("refused")

            def fake_execute(**kwargs):
                run = Path(kwargs["run_root"]) / kwargs["run_id"]
                run.mkdir(parents=True)
                (run / "run.json").write_text(json.dumps({"provider_contacts": 0}), encoding="utf-8")
                return {"run_id": kwargs["run_id"], "state": "complete", "store": str(run)}

            with patch("g_corrob1_runner.execute", side_effect=fake_execute):
                threads = [threading.Thread(target=attempt) for _ in range(2)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
            self.assertEqual(sorted(results), ["ran", "refused"])

    def test_terminal_projection_and_activity_contract_expose_no_semantics(self):
        public = capability._public_result({
            "run_id": "run", "terminal_state": "complete", "reason_code": "terminal",
            "terminal_reference": "experiment-terminal:auth", "receipt_sha256": "a" * 64,
            "provider_call_count": 192,
        })
        serialized = json.dumps(public).lower()
        for forbidden in ("corpus", "proposition", "assessment", "disposition", "gold", "unsafe_use", "score.json"):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(public["semantic_results_exposed"])

        with patch.object(capability, "_execute_authorized_frozen_experiment", return_value=public):
            projected = capability._process_authorized_frozen_experiment_command(
                "Execute authorized frozen experiment G-CORROB1-R2."
            )
        response = projected["response"].lower()
        for forbidden in ("corpus", "proposition", "assessment", "disposition", "gold", "unsafe", "score"):
            self.assertNotIn(forbidden, response)

    def test_live_preflight_is_bound_to_new_manifest_and_mismatch_fails(self):
        auth = authorization()
        receipt = preflight()
        self.assertTrue(runner._preflight_matches_execution_manifest(receipt, auth))
        for field, value in (
            ("provider", "other"),
            ("resolved_model", "fallback"),
            ("model_content_digest", "0" * 64),
            ("provider_version", "different"),
        ):
            changed = deepcopy(receipt)
            changed[field] = value
            self.assertFalse(runner._preflight_matches_execution_manifest(changed, auth), field)
        changed = deepcopy(receipt)
        changed["submitted_parameters"]["temperature"] = 0.1
        self.assertFalse(runner._preflight_matches_execution_manifest(changed, auth))

    def test_incomplete_run_is_terminal_and_authorization_is_consumed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            auth = authorization("gcorrob1exec_auth_incomplete")
            save_authorization(root, auth)

            def incomplete(**kwargs):
                run = Path(kwargs["run_root"]) / kwargs["run_id"]
                run.mkdir(parents=True)
                (run / "run.json").write_text(
                    json.dumps({"provider_contacts": 7, "state": "incomplete"}), encoding="utf-8"
                )
                return {"run_id": kwargs["run_id"], "state": "incomplete", "store": str(run)}

            with patch("g_corrob1_runner.execute", side_effect=incomplete):
                result = capability._execute_authorized_frozen_experiment(
                    capability.MANIFEST_ID, runtime_root=root, provider_adapter=Adapter(), activity=object()
                )
            self.assertEqual(result["state"], "incomplete")
            self.assertEqual(result["provider_call_count"], 7)
            marker = root / "experiment_execution_consumptions" / (auth["authorization_id"] + ".json")
            self.assertTrue(marker.is_file())

    def test_runner_accepts_only_new_exact_manifest_or_historical_contract(self):
        auth = authorization()
        runner_auth = {
            "execution_manifest": auth["execution_manifest"],
            "execution_manifest_sha256": auth["execution_manifest_sha256"],
            "execution_authorized": True,
            "execution_frozen": True,
            "operator_confirmation": auth["operator_confirmation"],
        }
        self.assertTrue(runner._authorization_valid(runner_auth))
        changed = deepcopy(runner_auth)
        changed["execution_manifest"]["submitted_parameters"]["temperature"] = 0.1
        self.assertFalse(runner._authorization_valid(changed))


if __name__ == "__main__":
    unittest.main()
