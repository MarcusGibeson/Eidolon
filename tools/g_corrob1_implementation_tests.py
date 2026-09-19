from __future__ import annotations

"""Deterministic and adversarial implementation tests. No provider contact."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_corrob1_activity as activity
import g_corrob1_contract as contract
import g_corrob1_freeze as freeze
import g_corrob1_persistence as persistence
import g_corrob1_policy as policy
import g_corrob1_provider as provider
import g_corrob1_runner as runner
import g_corrob1_scorer as scorer


def preflight(**changes):
    proposal = contract.load_sampling()
    row = {
        "provider": "ollama", "provider_version": "fixture-ollama",
        "requested_model": proposal["model_name"],
        "resolved_model": proposal["model_name"], "model_content_digest": "a" * 64,
        "submitted_parameters": dict(proposal["parameters"]),
        "parameter_submission_support": {name: True for name in proposal["parameters"]},
        "seed_submission_supported": True, "fresh_session_per_call": True,
        "retry_limit": 0, "silent_fallback": False,
        "honoring_attestation": "not_provided_by_ollama", "provider_contacted": False,
    }
    row.update(changes)
    return row


class FixtureProvider:
    def __init__(self, *, mutation=None, fail_call=None):
        self.items = {row["item_id"]: row for row in contract.load_corpus()}
        self.gold = {row["item_id"]: row for row in scorer.load_gold()}
        self.schedule = {row.call_id: row for row in contract.build_schedule()}
        self.requests = []
        self.mutation = mutation
        self.fail_call = fail_call

    def __call__(self, request_id, body):
        contract.assert_minimal_semantic_body(body)
        call = self.schedule[request_id]
        item, gold = self.items[call.item_id], self.gold[call.item_id]
        assessment = {
            "proposition_id": item["proposition_id"], "evidence_id": item["evidence_id"],
            "relation": gold["gold_relation"], "scope": gold["gold_scope"],
            "temporal": gold["gold_temporal"], "quotes": [item["evidence"][:40]], "confidence": "high",
        }
        result = {
            "request_id": request_id, "raw_response": json.dumps(assessment),
            "returned_model": "qwen3.8:27b", "metrics": {"prompt_eval_count": 100, "eval_count": 70},
            "seconds": 0.01, "provider_contacted": False,
            "submitted_body_sha256": contract.canonical_digest(json.dumps(body, sort_keys=True, separators=(",", ":"))),
            "error": "",
        }
        if request_id == self.fail_call:
            result.update(raw_response="", error="fixture_transport_failure")
        if self.mutation:
            self.mutation(request_id, body, result, assessment)
        self.requests.append({"request_id": request_id, "body": deepcopy(body), "result": deepcopy(result)})
        return result


class ContractTests(unittest.TestCase):
    def test_schedule_is_complete_balanced_and_seeded(self):
        rows = contract.build_schedule()
        self.assertEqual(len(rows), 192)
        self.assertEqual(len({row.seed for row in rows}), 192)
        self.assertEqual([rows[i].role for i in range(0, 192, 2)].count("A"), 48)
        self.assertEqual([rows[i].role for i in range(0, 192, 2)].count("B"), 48)
        self.assertEqual({row.ordinal for row in rows}, set(range(1, 193)))

    def test_semantic_request_is_minimal_and_blind(self):
        item = contract.load_corpus()[0]
        call = contract.build_schedule()[0]
        body = contract.semantic_http_body(item, call)
        contract.assert_minimal_semantic_body(body)
        serialized = json.dumps(body)
        for token in ("gold_relation", "expected_disposition", "use_permitted", "unsafe_use", "pair_id", "family"):
            self.assertNotIn(token, serialized)
        self.assertNotIn("Assessor A", body["prompt"])
        self.assertNotIn("Assessor B", body["prompt"])
        self.assertNotIn("repeat_index", body["prompt"])
        self.assertEqual(body["options"]["seed"], call.seed)
        self.assertNotIn("stream", body["options"])
        self.assertIs(body["stream"], False)

    def test_authorization_boundary_rejects_real_execution(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError):
                runner.execute(provider_call=FixtureProvider(), preflight_receipt=preflight(), run_root=td)

    def test_rendered_prompt_matches_frozen_g_evid1_template(self):
        sys.path.insert(0, str(TOOLS))
        import g_evid1_harness
        for item in contract.load_corpus():
            self.assertEqual(contract.build_prompt(item), g_evid1_harness.build_prompt(item))

    def test_no_cross_assessor_or_runtime_metadata_in_http_body(self):
        items = {row["item_id"]: row for row in contract.load_corpus()}
        schedule = contract.build_schedule()
        prior_secret = "SECRET_FROM_OTHER_ASSESSOR"
        for call in schedule:
            body = contract.semantic_http_body(items[call.item_id], call)
            text = json.dumps(body)
            self.assertNotIn(prior_secret, text)
            self.assertNotIn("environment", text.casefold())
            self.assertNotIn("runtime_state", text.casefold())
            self.assertNotIn("activity", text.casefold())


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.item = contract.load_corpus()[0]
        self.valid = {
            "proposition_id": self.item["proposition_id"], "evidence_id": self.item["evidence_id"],
            "relation": "supports", "scope": "match", "temporal": "compatible",
            "quotes": [self.item["evidence"][:40]], "confidence": "high",
        }

    def test_structural_validator_accepts_valid_record(self):
        result = policy.process_assessment(json.dumps(self.valid), proposition_id=self.item["proposition_id"],
                                           evidence_id=self.item["evidence_id"], evidence_text=self.item["evidence"])
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["disposition"], "use")

    def test_structural_failure_matrix(self):
        cases = {}
        cases["missing"] = {key: value for key, value in self.valid.items() if key != "relation"}
        cases["enum"] = {**self.valid, "relation": "unsafe"}
        cases["forbidden"] = {**self.valid, "disposition": "use"}
        cases["quote"] = {**self.valid, "quotes": ["not present in the evidence at all"]}
        cases["item"] = {**self.valid, "proposition_id": "WRONG"}
        for name, row in cases.items():
            with self.subTest(name=name):
                result = policy.process_assessment(json.dumps(row), proposition_id=self.item["proposition_id"],
                                                   evidence_id=self.item["evidence_id"], evidence_text=self.item["evidence"])
                self.assertFalse(result["validation"]["valid"])
                self.assertEqual(result["disposition"], "abstain")
        malformed = policy.process_assessment("{bad", proposition_id=self.item["proposition_id"],
                                              evidence_id=self.item["evidence_id"], evidence_text=self.item["evidence"])
        truncated = policy.process_assessment(json.dumps(self.valid), proposition_id=self.item["proposition_id"],
                                              evidence_id=self.item["evidence_id"], evidence_text=self.item["evidence"],
                                              truncated=True)
        bound = policy.process_assessment(json.dumps(self.valid), proposition_id=self.item["proposition_id"],
                                          evidence_id=self.item["evidence_id"], evidence_text=self.item["evidence"],
                                          binding_error="wrong_assessor_binding")
        for result in (malformed, truncated, bound):
            self.assertFalse(result["validation"]["valid"])
            self.assertEqual(result["disposition"], "abstain")

    def test_cross_assessor_payload_is_forbidden_extra_field(self):
        row = {**self.valid, "other_assessment": {"relation": "supports"}}
        result = policy.process_assessment(json.dumps(row), proposition_id=self.item["proposition_id"],
                                           evidence_id=self.item["evidence_id"], evidence_text=self.item["evidence"])
        self.assertFalse(result["validation"]["valid"])
        self.assertIn("extra_field:other_assessment", result["validation"]["reasons"])

    def test_policy_and_pair_state_counts(self):
        self.assertEqual(policy.enumerate_policy_state_space(), {
            "individual_states": 300,
            "individual": {"use": 2, "investigate": 106, "abstain": 192},
            "paired_states": 90000,
            "paired": {"use": 4, "investigate": 11660, "abstain": 78336},
        })

    def test_correlated_false_clean_remains_use(self):
        row = {"disposition": "use", "validation": {"valid": True}}
        self.assertEqual(policy.compare_pair(row, row)["disposition"], "use")


class ProviderTests(unittest.TestCase):
    def test_preflight_mismatch_matrix(self):
        self.assertTrue(provider.verify_preflight_receipt(preflight())["valid"])
        cases = [
            preflight(provider="other"), preflight(provider_version=""),
            preflight(resolved_model="fallback"),
            preflight(model_content_digest=""), preflight(retry_limit=1),
            preflight(seed_submission_supported=False), preflight(silent_fallback=True),
            preflight(submitted_parameters={}),
            preflight(parameter_submission_support={name: name != "min_p" for name in contract.load_sampling()["parameters"]}),
        ]
        for row in cases:
            self.assertFalse(provider.verify_preflight_receipt(row)["valid"])

    def test_offline_adapter_never_contacts_provider(self):
        adapter = provider.OllamaExperimentAdapter()
        with self.assertRaises(PermissionError):
            adapter.inspect_model("qwen3.8:27b")
        with self.assertRaises(PermissionError):
            adapter.generate("fixture", {"model": "qwen3.8:27b"})

    def test_prepared_configuration_discloses_unattested_options(self):
        row = provider.prepared_configuration()
        self.assertFalse(row["provider_contacted"])
        self.assertTrue(any("does not attest" in text for text in row["verification_limitations"]))


class PersistenceTests(unittest.TestCase):
    def test_append_only_and_terminal_guards(self):
        with tempfile.TemporaryDirectory() as td:
            store = persistence.RunStore(td, "one", create=True)
            record = {"call_id": "c1", "provider_contacted": False, "provider_error": ""}
            store.write_call(record)
            with self.assertRaises(FileExistsError):
                store.write_call(record)
            store.finish(state="incomplete", reason="fixture", valid_verdict=False)
            with self.assertRaises(ValueError):
                store.update(state="running")
            with self.assertRaises(FileExistsError):
                persistence.RunStore(td, "one", create=True)


class FreezePreparationTests(unittest.TestCase):
    def test_candidate_manifest_rebuild_is_deterministic_and_non_authoritative(self):
        first, second = freeze.build_manifest(), freeze.build_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "implementation_candidate_not_execution_frozen")
        self.assertFalse(first["execution_frozen"])
        self.assertFalse(first["execution_authorized"])
        self.assertTrue(freeze.verify_manifest(first)["valid"])

    def test_artifact_drift_and_unfrozen_execution_manifest_fail_closed(self):
        changed = freeze.build_manifest()
        key = next(iter(changed["artifacts"]))
        changed["artifacts"][key] = "0" * 64
        self.assertFalse(freeze.verify_manifest(changed)["valid"])
        self.assertFalse(freeze.verify_execution_manifest(freeze.build_manifest())["valid"])


class EndToEndTests(unittest.TestCase):
    def run_fixture(self, td, name="run", fixture=None, observer=None):
        fixture = fixture or FixtureProvider()
        result = runner.execute(provider_call=fixture, preflight_receipt=preflight(), run_root=td,
                                run_id=name, activity=observer, synthetic_fixture=True)
        return result, fixture

    def test_complete_fixture_end_to_end_and_scorer(self):
        with tempfile.TemporaryDirectory() as td:
            result, fixture = self.run_fixture(td)
            self.assertEqual(result["state"], "complete")
            self.assertEqual(len(fixture.requests), 192)
            report = result["report"]
            self.assertTrue(report["all_gates_passed"])
            self.assertEqual(report["conditions"]["paired"]["primary_unsafe_use"], {"count": 0, "of": 42, "offending": []})
            self.assertEqual(report["conditions"]["paired"]["useful_evidence_admitted"]["count"], 42)
            self.assertEqual(report["semantic_accuracy"]["A"]["exact_tuple"], {"correct": 84, "of": 84})
            self.assertEqual(report["semantic_accuracy"]["B"]["exact_tuple"], {"correct": 84, "of": 84})
            self.assertEqual(report["correlated_error"]["correlated_false_clean_agreement"]["count"], 0)

    def test_malformed_output_preserved_without_retry(self):
        target = contract.build_schedule()[0].call_id
        def mutation(request_id, body, result, assessment):
            if request_id == target:
                result["raw_response"] = "{truncated"
        with tempfile.TemporaryDirectory() as td:
            result, fixture = self.run_fixture(td, fixture=FixtureProvider(mutation=mutation))
            self.assertEqual(result["state"], "complete")
            self.assertEqual(len(fixture.requests), 192)
            call = json.loads((Path(td) / "run" / "calls" / f"{target}.json").read_text(encoding="utf-8"))
            self.assertEqual(call["raw_response"], "{truncated")
            self.assertFalse(call["validation"]["valid"])
            self.assertEqual(call["disposition"], "abstain")

    def test_truncation_is_preserved_and_structurally_rejected(self):
        target = contract.build_schedule()[0].call_id
        def mutation(request_id, body, result, assessment):
            if request_id == target:
                result["metrics"]["eval_count"] = 350
        with tempfile.TemporaryDirectory() as td:
            result, fixture = self.run_fixture(td, fixture=FixtureProvider(mutation=mutation))
            self.assertEqual(result["state"], "complete")
            self.assertEqual(len(fixture.requests), 192)
            call = json.loads((Path(td) / "run" / "calls" / f"{target}.json").read_text(encoding="utf-8"))
            self.assertTrue(call["truncated"])
            self.assertIn("truncated_output", call["validation"]["reasons"])

    def test_provider_failure_stops_without_retry_or_valid_verdict(self):
        target = contract.build_schedule()[3].call_id
        with tempfile.TemporaryDirectory() as td:
            result, fixture = self.run_fixture(td, fixture=FixtureProvider(fail_call=target))
            self.assertEqual(result["state"], "incomplete")
            self.assertFalse(result["valid_verdict"])
            self.assertEqual(len(fixture.requests), 4)

    def test_swapped_binding_fails_closed(self):
        target = contract.build_schedule()[0].call_id
        def mutation(request_id, body, result, assessment):
            if request_id == target:
                result["request_id"] = request_id[:-1] + ("B" if request_id.endswith("A") else "A")
        with tempfile.TemporaryDirectory() as td:
            result, fixture = self.run_fixture(td, fixture=FixtureProvider(mutation=mutation))
            self.assertEqual(result["state"], "incomplete")
            self.assertEqual(len(fixture.requests), 1)

    def test_returned_model_fallback_fails_closed(self):
        target = contract.build_schedule()[0].call_id
        def mutation(request_id, body, result, assessment):
            if request_id == target:
                result["returned_model"] = "fallback:latest"
        with tempfile.TemporaryDirectory() as td:
            result, fixture = self.run_fixture(td, fixture=FixtureProvider(mutation=mutation))
            self.assertEqual(result["state"], "incomplete")
            self.assertEqual(result["reason"], "provenance_or_binding_failure")
            self.assertEqual(len(fixture.requests), 1)

    def test_scorer_exposes_correlated_unsafe_pair(self):
        def mutation(request_id, body, result, assessment):
            if request_id in {"R02-r1-A", "R02-r1-B"}:
                assessment.update(relation="supports", scope="match", temporal="compatible", confidence="high")
                result["raw_response"] = json.dumps(assessment)
        with tempfile.TemporaryDirectory() as td:
            result, _ = self.run_fixture(td, fixture=FixtureProvider(mutation=mutation))
            report = result["report"]
            self.assertEqual(report["conditions"]["paired"]["primary_unsafe_use"]["count"], 1)
            self.assertEqual(report["correlated_error"]["correlated_false_clean_agreement"]["count"], 1)
            self.assertFalse(report["gates"]["paired_primary_unsafe_use"]["passed"])

    def test_scorer_rejects_missing_repeat_duplicate_and_denominator_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            self.run_fixture(td)
            store = persistence.RunStore(td, "run", create=False)
            calls, pairs = store.call_records(), store.pair_records()
            with self.assertRaises(ValueError):
                scorer.score(calls[:-1], pairs)
            duplicate = deepcopy(calls)
            duplicate[-1] = deepcopy(duplicate[0])
            with self.assertRaises(ValueError):
                scorer.score(duplicate, pairs)
            changed = deepcopy(calls)
            changed[0]["repeat"] = 99
            with self.assertRaises(ValueError):
                scorer.score(changed, pairs)
            duplicate_pair = deepcopy(pairs)
            duplicate_pair[-1] = deepcopy(duplicate_pair[0])
            with self.assertRaises(ValueError):
                scorer.score(calls, duplicate_pair)

    def test_ambiguity_never_enters_crisp_accuracy_denominator(self):
        with tempfile.TemporaryDirectory() as td:
            result, _ = self.run_fixture(td)
            for role in ("A", "B"):
                self.assertEqual(result["report"]["semantic_accuracy"][role]["exact_tuple"]["of"], 84)
                self.assertTrue(result["report"]["semantic_accuracy"][role]["diagnostic_excluded_from_crisp_denominators"])

    def test_pair_mutation_is_rejected_before_it_can_change_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            self.run_fixture(td)
            store = persistence.RunStore(td, "run", create=False)
            calls, pairs = store.call_records(), store.pair_records()
            pairs[0]["disposition"] = "abstain" if pairs[0]["disposition"] != "abstain" else "use"
            with self.assertRaises(ValueError):
                scorer.score(calls, pairs)

    def test_activity_is_content_minimized_and_does_not_change_result(self):
        with tempfile.TemporaryDirectory() as td:
            plain, plain_fixture = self.run_fixture(td, name="plain")
            observed_fixture = FixtureProvider()
            observed = activity.CorrobActivity("observed", root=Path(td) / "activity")
            seen, _ = self.run_fixture(td, name="seen", fixture=observed_fixture, observer=observed)
            self.assertEqual([row["body"] for row in plain_fixture.requests],
                             [row["body"] for row in observed_fixture.requests])
            self.assertEqual(plain["report"], seen["report"])
            snapshot = (Path(td) / "activity" / "activities" / "observed.json").read_text(encoding="utf-8")
            for token in ("proposition", "evidence", "relation", "scope", "temporal", "confidence",
                          "disposition", "unsafe", "gold"):
                self.assertNotIn(token, snapshot.casefold())

    def test_activity_adapter_failure_cannot_change_execution(self):
        class BrokenActivity:
            def emit(self, *args, **kwargs):
                raise OSError("fixture activity persistence failure")
        with tempfile.TemporaryDirectory() as td:
            plain, plain_fixture = self.run_fixture(td, name="plain")
            broken_fixture = FixtureProvider()
            broken, _ = self.run_fixture(td, name="broken", fixture=broken_fixture, observer=BrokenActivity())
            self.assertEqual([row["body"] for row in plain_fixture.requests],
                             [row["body"] for row in broken_fixture.requests])
            self.assertEqual(plain["report"], broken["report"])


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"tests_run": result.testsRun, "failures": len(result.failures),
                      "errors": len(result.errors), "provider_calls": 0,
                      "pilot_launched": False, "experiment_launched": False}, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
