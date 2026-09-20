from __future__ import annotations

"""Adversarial provider-envelope tests. No provider or model contact."""

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_corrob1_contract as contract
import g_corrob1_live_pilot as pilot
import g_corrob1_provider as provider
import g_corrob1_provider_envelope as envelope


ASSESSMENT = {
    "proposition_id": "P1", "evidence_id": "E1", "relation": "supports",
    "scope": "match", "temporal": "compatible", "quotes": ["fixture quote"],
    "confidence": "high",
}


class ExtractionPolicyTests(unittest.TestCase):
    def test_primary_response_is_selected(self):
        text = json.dumps(ASSESSMENT)
        result = envelope.extract_semantic_output({"response": text, "thinking": ""})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["selected_field"], "response")
        self.assertEqual(result["text"], text)

    def test_empty_response_allows_only_structured_thinking_alternate(self):
        text = json.dumps(ASSESSMENT)
        accepted = envelope.extract_semantic_output({"response": "  ", "thinking": text})
        rejected = envelope.extract_semantic_output({"response": "", "thinking": "private prose"})
        self.assertEqual(accepted["selected_field"], "thinking")
        self.assertEqual(accepted["method"], "contract_alternate_structured_output")
        self.assertEqual(rejected["status"], "failed")
        self.assertIn("alternate_thinking_not_complete_json_object", rejected["reasons"])

    def test_consistent_dual_fields_use_response_precedence(self):
        text = json.dumps(ASSESSMENT)
        result = envelope.extract_semantic_output({"response": "  " + text, "thinking": text + "  "})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["selected_field"], "response")
        self.assertEqual(result["method"], "consistent_contract_fields_response_precedence")

    def test_conflicting_dual_fields_fail_closed(self):
        result = envelope.extract_semantic_output({
            "response": json.dumps(ASSESSMENT),
            "thinking": json.dumps({**ASSESSMENT, "confidence": "low"}),
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["text"], "")
        self.assertIn("conflicting_output_fields:response,thinking", result["reasons"])

    def test_missing_and_whitespace_outputs_fail_closed(self):
        for value in ({}, {"response": ""}, {"response": " \r\n", "thinking": "\t"}):
            with self.subTest(value=value):
                self.assertEqual(envelope.extract_semantic_output(value)["status"], "failed")

    def test_non_text_alternate_fails_even_with_primary_text(self):
        result = envelope.extract_semantic_output({"response": json.dumps(ASSESSMENT), "thinking": ["bad"]})
        self.assertEqual(result["status"], "failed")
        self.assertIn("non_text_output_field:thinking", result["reasons"])


class PreservationTests(unittest.TestCase):
    def test_raw_bytes_and_structure_are_preserved(self):
        raw = b'{ "model":"qwen3.8:27b", "thinking":"", "response":"ok", "done":true }\n'
        record = envelope.envelope_record(raw)
        self.assertEqual(base64.b64decode(record["raw_provider_envelope_b64"]), raw)
        self.assertEqual(record["raw_provider_envelope_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(record["provider_envelope"]["response"], "ok")
        self.assertTrue(envelope.verify_envelope_record({**record, "raw_response": "ok"})["valid"])

    def test_malformed_envelope_is_preserved_but_not_accepted(self):
        raw = b'{"response":"unterminated"'
        evidence = envelope.raw_envelope_evidence(raw)
        self.assertEqual(base64.b64decode(evidence["raw_provider_envelope_b64"]), raw)
        check = envelope.verify_envelope_record(evidence)
        self.assertFalse(check["valid"])
        self.assertTrue(any(reason.startswith("malformed_provider_envelope") for reason in check["reasons"]))

    def test_digest_and_extraction_tampering_are_detected(self):
        record = envelope.fixture_envelope_fields({"response": json.dumps(ASSESSMENT)})
        changed = deepcopy(record)
        changed["raw_provider_envelope_sha256"] = "0" * 64
        self.assertFalse(envelope.verify_envelope_record(changed)["valid"])
        changed = deepcopy(record)
        changed["output_extraction"]["selected_field"] = "thinking"
        self.assertFalse(envelope.verify_envelope_record(changed)["valid"])


class _FakeResponse:
    def __init__(self, raw: bytes) -> None:
        self.content = raw

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, deepcopy(json), timeout))
        return _FakeResponse(self.raw)


class AdapterContractTests(unittest.TestCase):
    def _generate(self, payload):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        session = _FakeSession(raw)
        fake_requests = types.SimpleNamespace(Session=lambda: session)
        item = contract.load_corpus()[0]
        scheduled = contract.build_schedule()[0]
        body = contract.semantic_http_body(item, scheduled)
        with mock.patch.dict(sys.modules, {"requests": fake_requests}):
            result = provider.OllamaExperimentAdapter().generate(
                scheduled.call_id, body, allow_provider_contact=True
            )
        return raw, session, result

    def test_adapter_preserves_envelope_before_selecting_alternate(self):
        text = json.dumps(ASSESSMENT)
        raw, session, result = self._generate({
            "model": "qwen3.8:27b", "response": "", "thinking": text,
            "eval_count": 112, "prompt_eval_count": 334, "done": True,
        })
        self.assertEqual(base64.b64decode(result.raw_provider_envelope_b64), raw)
        self.assertEqual(result.extracted_model_output, text)
        self.assertEqual(result.output_extraction["selected_field"], "thinking")
        self.assertEqual(len(session.posts), 1)
        self.assertEqual(result.metrics["eval_count"], 112)

    def test_generated_tokens_without_usable_output_remain_failure(self):
        _raw, _session, result = self._generate({
            "model": "qwen3.8:27b", "response": "", "thinking": "",
            "eval_count": 112, "done": True,
        })
        self.assertEqual(result.output_extraction["status"], "failed")
        self.assertEqual(result.extracted_model_output, "")
        self.assertEqual(result.metrics["eval_count"], 112)

    def test_malformed_http_body_is_preserved_and_reported(self):
        raw = b'{"model":"qwen3.8:27b","response":'
        session = _FakeSession(raw)
        fake_requests = types.SimpleNamespace(Session=lambda: session)
        item, scheduled = contract.load_corpus()[0], contract.build_schedule()[0]
        body = contract.semantic_http_body(item, scheduled)
        with mock.patch.dict(sys.modules, {"requests": fake_requests}):
            result = provider.OllamaExperimentAdapter().generate(
                scheduled.call_id, body, allow_provider_contact=True
            )
        self.assertEqual(base64.b64decode(result.raw_provider_envelope_b64), raw)
        self.assertIn("malformed_provider_envelope", result.error)
        self.assertIsNone(result.as_dict()["provider_envelope"])


class PersistenceInterruptionTests(unittest.TestCase):
    def test_raw_envelope_persistence_interruption_stops_before_assessment_record(self):
        # This attacks the durable boundary without authorizing provider contact.
        class Adapter:
            generations = 0

            def inspect_model(self, model, *, allow_provider_contact=False):
                sampling = contract.load_sampling()
                return {
                    "provider": "ollama", "provider_version": "fixture",
                    "requested_model": model, "resolved_model": model,
                    "model_content_digest": "a" * 64,
                    "submitted_parameters": dict(sampling["parameters"]),
                    "parameter_submission_support": {key: True for key in sampling["parameters"]},
                    "seed_submission_supported": True, "fresh_session_per_call": True,
                    "retry_limit": 0, "silent_fallback": False,
                    "honoring_attestation": "unavailable", "provider_contacted": False,
                }

            def generate(self, request_id, body, *, allow_provider_contact=False):
                self.generations += 1
                fixture = json.loads((ROOT / "experiments/G-CORROB1-pilot-capable-r3/PILOT_FIXTURE.json").read_text())
                item = fixture["item"]
                assessment = {
                    "proposition_id": item["proposition_id"], "evidence_id": item["evidence_id"],
                    "relation": "supports", "scope": "match", "temporal": "compatible",
                    "quotes": ["during fictional rehearsal window W-4"], "confidence": "high",
                }
                fields = envelope.fixture_envelope_fields({"response": json.dumps(assessment)})
                return {
                    "request_id": request_id, "raw_response": fields["extracted_model_output"],
                    "returned_model": "qwen3.8:27b", "metrics": {"eval_count": 20},
                    "seconds": 0.01, "provider_contacted": False,
                    "submitted_body_sha256": contract.canonical_digest(
                        json.dumps(body, sort_keys=True, separators=(",", ":"))
                    ), "error": "", **fields,
                }

        adapter = Adapter()
        with tempfile.TemporaryDirectory() as td:
            with mock.patch("g_corrob1_live_pilot.RunStore.write_provider_envelope",
                            side_effect=OSError("fixture envelope persistence failure")):
                with self.assertRaisesRegex(OSError, "envelope persistence failure"):
                    pilot.execute(provider_adapter=adapter, run_root=td,
                                  run_id="gcorrob1pilot_envelopeinterrupt", synthetic_fixture=True)
            self.assertEqual(adapter.generations, 1)
            run = Path(td) / "g_corrob1_mechanical_pilot" / "gcorrob1pilot_envelopeinterrupt"
            self.assertFalse((run / "calls").exists())
            self.assertEqual(json.loads((run / "run.json").read_text())["state"], "failed")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "provider_generation_calls": 0, "pilot_launches": 0, "experiment_launches": 0,
    }, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
