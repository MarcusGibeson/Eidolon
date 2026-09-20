from __future__ import annotations

"""Deterministic/adversarial tests for the pilot-capable candidate. No network."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_corrob1_contract as production_contract
import g_corrob1_live_pilot as pilot
import g_corrob1_pilot_activity as pilot_activity
import g_corrob1_pilot_envelope_freeze as pilot_freeze
import g_corrob1_pilot_verifier as pilot_verifier
from g_corrob1_provider_envelope import fixture_envelope_fields
import g_corrob1_scorer as production_scorer


def _preflight(**changes):
    frozen = json.loads((pilot_freeze.PREFLIGHT).read_text(encoding="utf-8"))
    row = {
        "provider": frozen["provider"],
        "provider_version": frozen["provider_version"],
        "requested_model": frozen["requested_model"],
        "resolved_model": frozen["resolved_model"],
        "model_content_digest": frozen["model_manifest_sha256"],
        "submitted_parameters": dict(frozen["experiment_submission"]),
        "parameter_submission_support": {name: True for name in frozen["experiment_submission"]},
        "seed_submission_supported": True,
        "fresh_session_per_call": True,
        "retry_limit": 0,
        "silent_fallback": False,
        "honoring_attestation": "not_provided_by_ollama",
        "provider_contacted": True,
    }
    row.update(changes)
    return row


def _authorization(identifier="gcorrob1pilot_auth_test"):
    manifest = pilot_freeze.build_candidate()
    digest = pilot_freeze.candidate_file_sha256(manifest)
    return {
        "authorization_id": identifier,
        "pilot_manifest": manifest,
        "pilot_manifest_sha256": digest,
        "pilot_authorized": True,
        "provider_contact_authorized": True,
        "experiment_authorized": False,
        "expected_generation_calls": 2,
        "expected_pairs": 1,
        "operator_confirmation": f"Authorize G-CORROB1 live mechanical pilot {digest}",
    }


class FixtureAdapter:
    def __init__(self, mutation=None, preflight=None):
        self.mutation = mutation
        self.preflight = dict(preflight or _preflight())
        self.inspections = 0
        self.generations = []
        self.fixture = pilot_verifier.load_fixture()

    def inspect_model(self, model, *, allow_provider_contact=False):
        self.inspections += 1
        self.asserted_inspection_authority = allow_provider_contact
        return deepcopy(self.preflight)

    def generate(self, request_id, body, *, allow_provider_contact=False):
        item = self.fixture["item"]
        assessment = {
            "proposition_id": item["proposition_id"],
            "evidence_id": item["evidence_id"],
            "relation": "supports",
            "scope": "match",
            "temporal": "compatible",
            "quotes": ["during fictional rehearsal window W-4"],
            "confidence": "high",
        }
        result = {
            "request_id": request_id,
            "returned_model": "qwen3.8:27b",
            "metrics": {"prompt_eval_count": 80, "eval_count": 40},
            "seconds": 0.01,
            "provider_contacted": True,
            "submitted_body_sha256": production_contract.canonical_digest(
                json.dumps(body, sort_keys=True, separators=(",", ":"))
            ),
            "error": "",
        }
        if self.mutation:
            self.mutation(request_id, body, result, assessment)
        result.setdefault("raw_response", json.dumps(assessment))
        result.update(fixture_envelope_fields({"response": str(result.get("raw_response") or "")}))
        result["raw_response"] = result["extracted_model_output"]
        self.generations.append({"request_id": request_id, "body": deepcopy(body),
                                 "allow_provider_contact": allow_provider_contact,
                                 "result": deepcopy(result)})
        return result


class PilotAuthorityTests(unittest.TestCase):
    def test_absent_authority_permits_zero_provider_contact(self):
        adapter = FixtureAdapter()
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError):
                pilot.execute(provider_adapter=adapter, run_root=td, run_id="gcorrob1pilot_noauth")
        self.assertEqual(adapter.inspections, 0)
        self.assertEqual(adapter.generations, [])

    def test_valid_authority_permits_exactly_two_calls_and_is_one_shot(self):
        adapter = FixtureAdapter()
        auth = _authorization("gcorrob1pilot_auth_once")
        with tempfile.TemporaryDirectory() as td:
            result = pilot.execute(provider_adapter=adapter, run_root=td,
                                   run_id="gcorrob1pilot_authorized", authorization=auth)
            self.assertTrue(result["mechanical_pass"])
            self.assertEqual(adapter.inspections, 1)
            self.assertEqual(len(adapter.generations), 2)
            before = len(adapter.generations)
            with self.assertRaises(FileExistsError):
                pilot.execute(provider_adapter=adapter, run_root=td,
                              run_id="gcorrob1pilot_reuse", authorization=auth)
            self.assertEqual(len(adapter.generations), before)

    def test_candidate_and_authorization_never_grant_full_execution(self):
        candidate = pilot_freeze.build_candidate()
        auth = _authorization()
        self.assertFalse(candidate["pilot_authorized"])
        self.assertFalse(candidate["experiment_authorized"])
        self.assertFalse(candidate["execution_authorized"])
        self.assertFalse(auth["experiment_authorized"])
        self.assertTrue(pilot_freeze.verify_pilot_authorization(auth)["valid"])
        changed = deepcopy(auth)
        changed["experiment_authorized"] = True
        self.assertFalse(pilot_freeze.verify_pilot_authorization(changed)["valid"])

    def test_authorization_digest_and_confirmation_tampering_fail(self):
        for field, value in (("pilot_manifest_sha256", "0" * 64),
                             ("operator_confirmation", "authorize anything"),
                             ("expected_generation_calls", 192),
                             ("provider_contact_authorized", False)):
            changed = _authorization("gcorrob1pilot_auth_" + field)
            changed[field] = value
            self.assertFalse(pilot_freeze.verify_pilot_authorization(changed)["valid"])


class PilotBoundaryTests(unittest.TestCase):
    def test_fixture_is_outside_production_corpus_and_uses_distinct_seeds(self):
        fixture = pilot_verifier.load_fixture()
        production_ids = {row["item_id"] for row in production_contract.load_corpus()}
        self.assertNotIn(fixture["item"]["item_id"], production_ids)
        self.assertEqual([row["role"] for row in fixture["schedule"]], ["A", "B"])
        self.assertEqual(len({row["seed"] for row in fixture["schedule"]}), 2)

    def test_production_schedule_and_scorer_remain_fixed(self):
        self.assertEqual(len(production_contract.build_schedule()), 192)
        with self.assertRaisesRegex(ValueError, "fixed_observation_or_pair_denominator_mismatch"):
            production_scorer.score([], [])

    def test_production_scorer_rejects_pilot_and_pilot_verifier_rejects_production_shape(self):
        adapter = FixtureAdapter()
        with tempfile.TemporaryDirectory() as td:
            result = pilot.execute(provider_adapter=adapter, run_root=td,
                                   run_id="gcorrob1pilot_boundary", synthetic_fixture=True)
            run = Path(result["store"])
            calls = [json.loads(path.read_text(encoding="utf-8")) for path in (run / "calls").glob("*.json")]
            pairs = [json.loads(path.read_text(encoding="utf-8")) for path in (run / "pairs").glob("*.json")]
            with self.assertRaisesRegex(ValueError, "fixed_observation_or_pair_denominator_mismatch"):
                production_scorer.score(calls, pairs)
            report = pilot_verifier.verify_pilot_records(
                calls * 96, pairs * 96, pilot_manifest_sha256="f" * 64
            )
            self.assertFalse(report["mechanical_pass"])

    def test_completed_pilot_is_never_a_valid_production_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            result = pilot.execute(provider_adapter=FixtureAdapter(), run_root=td,
                                   run_id="gcorrob1pilot_notproduction", synthetic_fixture=True)
            manifest = json.loads((Path(result["store"]) / "run.json").read_text(encoding="utf-8"))
            score = json.loads((Path(result["store"]) / "score.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "complete")
            self.assertFalse(manifest["valid_verdict"])
            self.assertTrue(manifest["pilot_only"])
            self.assertFalse(manifest["production_result"])
            self.assertIn(pilot_verifier.NAMESPACE, Path(result["store"]).parts)
            self.assertFalse(score["semantic_evaluation_performed"])
            self.assertFalse(score["production_result"])
            self.assertEqual(score["submitted_seeds"], {"A": 319682844, "B": 1888622981})
            self.assertTrue(score["distinct_seed_submission"])

    def test_g_evid1_digest_is_bound_unchanged_from_production_candidate(self):
        old = json.loads((ROOT / "experiments/G-CORROB1-candidate-r2/EXECUTION_FREEZE_CANDIDATE.json").read_text(encoding="utf-8"))
        candidate = pilot_freeze.build_candidate()
        self.assertEqual(candidate["artifacts"]["tools/g_evid1_policy.py"],
                         old["artifacts"]["tools/g_evid1_policy.py"])


class FailClosedTests(unittest.TestCase):
    def _run(self, mutation=None, preflight=None, name="case"):
        adapter = FixtureAdapter(mutation=mutation, preflight=preflight)
        td = tempfile.TemporaryDirectory()
        result = pilot.execute(provider_adapter=adapter, run_root=td.name,
                               run_id="gcorrob1pilot_" + name, authorization=_authorization("gcorrob1pilot_auth_" + name))
        return td, adapter, result

    def test_wrong_model_digest_options_and_fallback_stop_before_generation(self):
        cases = [
            _preflight(resolved_model="fallback:latest"),
            _preflight(model_content_digest="0" * 64),
            _preflight(submitted_parameters={}),
            _preflight(silent_fallback=True),
        ]
        for index, receipt in enumerate(cases):
            with self.subTest(index=index):
                td, adapter, result = self._run(preflight=receipt, name=f"preflight{index}")
                try:
                    self.assertEqual(result["state"], "incomplete")
                    self.assertEqual(len(adapter.generations), 0)
                finally:
                    td.cleanup()

    def test_malformed_truncated_wrong_binding_and_cross_contamination_abort(self):
        def malformed(_request, _body, result, _assessment):
            result["raw_response"] = "{bad"
        def truncated(_request, _body, result, _assessment):
            result["metrics"]["eval_count"] = 350
        def wrong_binding(_request, _body, _result, assessment):
            assessment["proposition_id"] = "WRONG"
        def crossed(_request, _body, _result, assessment):
            assessment["other_assessment"] = {"relation": "supports"}
        for index, mutation in enumerate((malformed, truncated, wrong_binding, crossed)):
            with self.subTest(index=index):
                td, adapter, result = self._run(mutation=mutation, name=f"structural{index}")
                try:
                    self.assertEqual(result["state"], "incomplete")
                    self.assertEqual(len(adapter.generations), 1)
                    self.assertEqual(result["reason"], "structural_assessment_rejection")
                finally:
                    td.cleanup()

    def test_swapped_assessor_and_request_digest_mismatch_abort(self):
        def swapped(request_id, _body, result, _assessment):
            result["request_id"] = request_id[:-1] + ("B" if request_id.endswith("A") else "A")
        def digest(_request, _body, result, _assessment):
            result["submitted_body_sha256"] = "0" * 64
        for index, mutation in enumerate((swapped, digest)):
            td, adapter, result = self._run(mutation=mutation, name=f"binding{index}")
            try:
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["reason"], "provenance_or_binding_failure")
                self.assertEqual(len(adapter.generations), 1)
            finally:
                td.cleanup()

    def test_provider_interruption_is_preserved_without_retry(self):
        def fail_b(request_id, _body, result, _assessment):
            if request_id.endswith("B"):
                result.update(raw_response="", error="fixture_transport_failure")
        td, adapter, result = self._run(mutation=fail_b, name="interrupt")
        try:
            self.assertEqual(result["state"], "incomplete")
            self.assertEqual(result["reason"], "provider_failure")
            self.assertEqual(len(adapter.generations), 2)
            self.assertEqual(list((Path(result["store"]) / "calls").glob("*.json")).__len__(), 2)
            self.assertFalse((Path(result["store"]) / "pairs").exists())
        finally:
            td.cleanup()

    def test_verifier_rejects_missing_duplicate_and_digest_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            result = pilot.execute(provider_adapter=FixtureAdapter(), run_root=td,
                                   run_id="gcorrob1pilot_verify", synthetic_fixture=True)
            root = Path(result["store"])
            calls = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "calls").glob("*.json"))]
            pairs = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "pairs").glob("*.json"))]
            cases = [
                (calls[:-1], pairs),
                ([calls[0], calls[0]], pairs),
                (calls, [pairs[0], pairs[0]]),
            ]
            changed = deepcopy(calls)
            changed[0]["record_sha256"] = "0" * 64
            cases.append((changed, pairs))
            for case_calls, case_pairs in cases:
                report = pilot_verifier.verify_pilot_records(
                    case_calls, case_pairs, pilot_manifest_sha256="f" * 64
                )
                self.assertFalse(report["mechanical_pass"])

    def test_stale_run_records_fail_before_provider_contact(self):
        adapter = FixtureAdapter()
        with tempfile.TemporaryDirectory() as td:
            pilot.execute(provider_adapter=adapter, run_root=td, run_id="gcorrob1pilot_stale",
                          synthetic_fixture=True)
            before = len(adapter.generations)
            with self.assertRaises(FileExistsError):
                pilot.execute(provider_adapter=adapter, run_root=td, run_id="gcorrob1pilot_stale",
                              synthetic_fixture=True)
            self.assertEqual(len(adapter.generations), before)


class ActivityAndLineageTests(unittest.TestCase):
    def test_activity_is_content_minimized_and_execution_invariant(self):
        with tempfile.TemporaryDirectory() as td:
            plain_adapter = FixtureAdapter()
            plain = pilot.execute(provider_adapter=plain_adapter, run_root=td,
                                  run_id="gcorrob1pilot_plain", synthetic_fixture=True)
            seen_adapter = FixtureAdapter()
            observer = pilot_activity.PilotActivity("pilotactivity", root=Path(td) / "activity")
            seen = pilot.execute(provider_adapter=seen_adapter, run_root=td,
                                 run_id="gcorrob1pilot_seen", activity=observer, synthetic_fixture=True)
            self.assertEqual([row["body"] for row in plain_adapter.generations],
                             [row["body"] for row in seen_adapter.generations])
            self.assertEqual(plain["report"], seen["report"])
            snapshot = (Path(td) / "activity" / "activities" / "pilotactivity.json").read_text(encoding="utf-8").casefold()
            for token in ("ppx01", "pex01", "calibration token", "\"relation\"", "\"scope\"",
                          "\"temporal\"", "\"disposition\"", "unsafe", "gold"):
                self.assertNotIn(token, snapshot)

    def test_activity_failure_cannot_mutate_execution(self):
        class BrokenActivity:
            def emit(self, *args, **kwargs):
                raise OSError("fixture activity failure")
        with tempfile.TemporaryDirectory() as td:
            plain_adapter, broken_adapter = FixtureAdapter(), FixtureAdapter()
            plain = pilot.execute(provider_adapter=plain_adapter, run_root=td,
                                  run_id="gcorrob1pilot_control", synthetic_fixture=True)
            broken = pilot.execute(provider_adapter=broken_adapter, run_root=td,
                                   run_id="gcorrob1pilot_broken", activity=BrokenActivity(),
                                   synthetic_fixture=True)
            self.assertEqual([row["body"] for row in plain_adapter.generations],
                             [row["body"] for row in broken_adapter.generations])
            self.assertEqual(plain["report"], broken["report"])

    def test_complete_lineage_is_reconstructable_and_digest_bound(self):
        with tempfile.TemporaryDirectory() as td:
            result = pilot.execute(provider_adapter=FixtureAdapter(), run_root=td,
                                   run_id="gcorrob1pilot_lineage", synthetic_fixture=True)
            root = Path(result["store"])
            manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
            score = json.loads((root / "score.json").read_text(encoding="utf-8"))
            terminal = json.loads((root / "terminal_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["provider_envelopes_persisted"], 2)
            self.assertEqual(manifest["calls_persisted"], 2)
            self.assertEqual(manifest["pairs_persisted"], 1)
            self.assertEqual(manifest["state"], "complete")
            self.assertEqual(score["calls_verified"], 2)
            self.assertEqual(score["provider_envelopes_verified"], 2)
            self.assertEqual(score["pairs_verified"], 1)
            self.assertEqual(len(score["lineage_sha256"]), 64)
            self.assertFalse(manifest["valid_verdict"])
            unsigned = {key: value for key, value in terminal.items() if key != "receipt_sha256"}
            self.assertEqual(
                terminal["receipt_sha256"],
                production_contract.canonical_digest(json.dumps(unsigned, sort_keys=True, separators=(",", ":"))),
            )
            self.assertEqual(terminal["terminal_state"], "complete")
            self.assertEqual(len(terminal["provider_envelope_record_sha256"]), 2)


class FreezeTests(unittest.TestCase):
    def test_candidate_rebuild_is_deterministic_and_non_authoritative(self):
        first, second = pilot_freeze.build_candidate(), pilot_freeze.build_candidate()
        self.assertEqual(first, second)
        self.assertTrue(pilot_freeze.verify_candidate(first)["valid"])
        self.assertTrue(first["pilot_capable"])
        self.assertFalse(first["pilot_authorized"])
        self.assertFalse(first["experiment_authorized"])

    def test_serialized_candidate_hash_matches_authorization_digest_convention(self):
        candidate = pilot_freeze.build_candidate()
        if pilot_freeze.CANDIDATE.is_file():
            candidate = json.loads(pilot_freeze.CANDIDATE.read_text(encoding="utf-8"))
            self.assertEqual(
                production_contract.digest_file(pilot_freeze.CANDIDATE),
                pilot_freeze.candidate_file_sha256(candidate),
            )
        else:
            serialized = json.dumps(candidate, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
            self.assertEqual(production_contract.canonical_digest(serialized),
                             pilot_freeze.candidate_file_sha256(candidate))

    def test_every_bound_artifact_drift_and_authority_change_fails(self):
        candidate = pilot_freeze.build_candidate()
        for path in candidate["artifacts"]:
            changed = deepcopy(candidate)
            changed["artifacts"][path] = "0" * 64
            self.assertFalse(pilot_freeze.verify_candidate(changed)["valid"], path)
        for key, value in (("pilot_authorized", True), ("experiment_authorized", True),
                           ("belief_effects", "allowed"), ("expected_generation_calls", 192)):
            changed = deepcopy(candidate)
            changed[key] = value
            self.assertFalse(pilot_freeze.verify_candidate(changed)["valid"], key)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "provider_calls": 0,
        "pilot_launches": 0,
        "experiment_launches": 0,
    }, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
