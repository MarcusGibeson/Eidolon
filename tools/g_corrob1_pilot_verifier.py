from __future__ import annotations

"""Pilot-only mechanical completeness and lineage verification.

This verifier has no gold, safety, utility, or semantic-accuracy concepts. It
cannot certify a G-CORROB1 production execution.
"""

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from g_corrob1_contract import canonical_digest, load_json
from g_corrob1_policy import compare_pair
from g_corrob1_provider_envelope import verify_envelope_record


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-CORROB1-pilot-capable-r3"
FIXTURE_PATH = DATA / "PILOT_FIXTURE.json"
CONTRACT_VERSION = "g-corrob1.mechanical-pilot.verifier.2"
NAMESPACE = "g_corrob1_mechanical_pilot"
EXPECTED_CALLS = 2
EXPECTED_PAIRS = 1


def load_fixture(path: str | Path | None = None) -> dict[str, Any]:
    fixture = dict(load_json(path or FIXTURE_PATH))
    reasons = []
    if fixture.get("namespace") != NAMESPACE:
        reasons.append("pilot_namespace_mismatch")
    if fixture.get("pilot_only") is not True or fixture.get("production_corpus_member") is not False:
        reasons.append("pilot_fixture_authority_mismatch")
    if fixture.get("semantic_evaluation_permitted") is not False:
        reasons.append("pilot_semantic_evaluation_must_be_false")
    if fixture.get("expected_generation_calls") != EXPECTED_CALLS:
        reasons.append("pilot_call_count_mismatch")
    if fixture.get("expected_pairs") != EXPECTED_PAIRS:
        reasons.append("pilot_pair_count_mismatch")
    schedule = list(fixture.get("schedule") or [])
    if len(schedule) != EXPECTED_CALLS:
        reasons.append("pilot_schedule_count_mismatch")
    identities = [(row.get("call_id"), row.get("role")) for row in schedule]
    if identities != [("PX01-r1-A", "A"), ("PX01-r1-B", "B")]:
        reasons.append("pilot_schedule_identity_or_order_mismatch")
    if len({row.get("seed") for row in schedule}) != EXPECTED_CALLS:
        reasons.append("pilot_seed_collision")
    item = fixture.get("item") or {}
    if item.get("item_id") != "PX01" or not str(item.get("proposition_id") or "").startswith("PPX"):
        reasons.append("pilot_item_identity_mismatch")
    if reasons:
        raise ValueError("invalid_pilot_fixture:" + ",".join(sorted(set(reasons))))
    return fixture


def _verify_record_digest(row: Mapping[str, Any]) -> bool:
    recorded = str(row.get("record_sha256") or "")
    unsigned = {key: value for key, value in row.items() if key != "record_sha256"}
    return recorded == canonical_digest(json.dumps(unsigned, sort_keys=True, separators=(",", ":")))


def verify_pilot_records(
    calls: Iterable[Mapping[str, Any]],
    pairs: Iterable[Mapping[str, Any]],
    *,
    provider_envelopes: Iterable[Mapping[str, Any]] = (),
    fixture: Mapping[str, Any] | None = None,
    pilot_manifest_sha256: str,
) -> dict[str, Any]:
    selected = dict(fixture or load_fixture())
    call_rows = [dict(row) for row in calls]
    pair_rows = [dict(row) for row in pairs]
    envelope_rows = [dict(row) for row in provider_envelopes]
    reasons: list[str] = []

    if len(call_rows) != EXPECTED_CALLS:
        reasons.append("pilot_fixed_call_denominator_mismatch")
    if len(pair_rows) != EXPECTED_PAIRS:
        reasons.append("pilot_fixed_pair_denominator_mismatch")
    if len(envelope_rows) != EXPECTED_CALLS:
        reasons.append("pilot_fixed_provider_envelope_denominator_mismatch")
    if len({row.get("call_id") for row in call_rows}) != len(call_rows):
        reasons.append("duplicate_pilot_call_identity")
    if len({row.get("pair_id") for row in pair_rows}) != len(pair_rows):
        reasons.append("duplicate_pilot_pair_identity")

    expected_calls = {row["call_id"]: row for row in selected["schedule"]}
    observed_calls = {str(row.get("call_id")): row for row in call_rows}
    observed_envelopes = {str(row.get("call_id")): row for row in envelope_rows}
    if set(observed_calls) != set(expected_calls):
        reasons.append("pilot_call_coverage_mismatch")
    if set(observed_envelopes) != set(expected_calls):
        reasons.append("pilot_provider_envelope_coverage_mismatch")
    if not pilot_manifest_sha256 or len(pilot_manifest_sha256) != 64:
        reasons.append("pilot_manifest_digest_missing")

    for call_id, row in observed_calls.items():
        expected = expected_calls.get(call_id)
        if expected is None:
            continue
        for key in ("pair_id", "item_id", "repeat", "role", "ordinal", "pair_ordinal", "seed"):
            if row.get(key) != expected.get(key):
                reasons.append(f"pilot_call_binding_mismatch:{call_id}:{key}")
        if row.get("record_namespace") != NAMESPACE or row.get("pilot_only") is not True:
            reasons.append(f"pilot_namespace_or_authority_mismatch:{call_id}")
        if row.get("production_result") is not False or row.get("semantic_evaluation_performed") is not False:
            reasons.append(f"pilot_result_boundary_mismatch:{call_id}")
        if row.get("belief_effects") != "none":
            reasons.append(f"pilot_belief_effects_mismatch:{call_id}")
        if not _verify_record_digest(row):
            reasons.append(f"pilot_call_digest_mismatch:{call_id}")
        if not bool((row.get("validation") or {}).get("valid")):
            reasons.append(f"pilot_structural_validation_failed:{call_id}")
        if row.get("provider_error"):
            reasons.append(f"pilot_provider_error:{call_id}")
        envelope_check = verify_envelope_record(row)
        reasons.extend(f"pilot_envelope:{call_id}:{reason}" for reason in envelope_check["reasons"])
        if (row.get("output_extraction") or {}).get("status") != "success":
            reasons.append(f"pilot_output_extraction_failed:{call_id}")
        request = row.get("request") or {}
        for key in ("call_id", "pair_id", "item_id", "repeat", "role", "seed"):
            if request.get(key) != expected.get(key):
                reasons.append(f"pilot_request_binding_mismatch:{call_id}:{key}")
        if row.get("submitted_body_sha256") != request.get("submitted_body_sha256"):
            reasons.append(f"pilot_request_digest_mismatch:{call_id}")
        envelope = observed_envelopes.get(call_id)
        if envelope is not None:
            if envelope.get("record_namespace") != NAMESPACE or envelope.get("pilot_only") is not True:
                reasons.append(f"pilot_provider_envelope_namespace_mismatch:{call_id}")
            if envelope.get("production_result") is not False:
                reasons.append(f"pilot_provider_envelope_result_boundary_mismatch:{call_id}")
            if not _verify_record_digest(envelope):
                reasons.append(f"pilot_provider_envelope_record_digest_mismatch:{call_id}")
            if row.get("provider_envelope_record_sha256") != envelope.get("record_sha256"):
                reasons.append(f"pilot_provider_envelope_lineage_mismatch:{call_id}")
            for key in ("raw_provider_envelope_b64", "raw_provider_envelope_sha256",
                        "provider_envelope", "provider_envelope_sha256"):
                if row.get(key) != envelope.get(key):
                    reasons.append(f"pilot_provider_envelope_copy_mismatch:{call_id}:{key}")

    if len(pair_rows) == 1 and set(observed_calls) == set(expected_calls):
        pair = pair_rows[0]
        a, b = observed_calls["PX01-r1-A"], observed_calls["PX01-r1-B"]
        expected_comparison = compare_pair(a, b)
        if pair.get("record_namespace") != NAMESPACE or pair.get("pilot_only") is not True:
            reasons.append("pilot_pair_namespace_mismatch")
        if pair.get("production_result") is not False or pair.get("semantic_evaluation_performed") is not False:
            reasons.append("pilot_pair_result_boundary_mismatch")
        if pair.get("A_call_id") != a.get("call_id") or pair.get("B_call_id") != b.get("call_id"):
            reasons.append("pilot_pair_call_binding_mismatch")
        for key in ("disposition", "rule", "scientific_status", "individual_dispositions", "belief_effects"):
            if pair.get(key) != expected_comparison.get(key):
                reasons.append(f"pilot_pair_recomputation_mismatch:{key}")
        if not _verify_record_digest(pair):
            reasons.append("pilot_pair_digest_mismatch")

    lineage = {
        "pilot_manifest_sha256": pilot_manifest_sha256,
        "fixture_sha256": canonical_digest(json.dumps(selected, sort_keys=True, separators=(",", ":"))),
        "call_record_sha256": [str(row.get("record_sha256") or "") for row in call_rows],
        "provider_envelope_record_sha256": [str(row.get("record_sha256") or "") for row in envelope_rows],
        "pair_record_sha256": [str(row.get("record_sha256") or "") for row in pair_rows],
    }
    lineage_sha256 = canonical_digest(json.dumps(lineage, sort_keys=True, separators=(",", ":")))
    seeds = {
        str(row.get("role")): int(((row.get("request") or {}).get("options") or {}).get("seed") or 0)
        for row in call_rows
    }
    raw_by_role = {
        str(row.get("role")): canonical_digest(str(row.get("raw_response") or ""))
        for row in call_rows
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "record_namespace": NAMESPACE,
        "pilot_only": True,
        "production_result": False,
        "semantic_evaluation_performed": False,
        "gold_loaded": False,
        "mechanical_pass": not reasons,
        "reasons": sorted(set(reasons)),
        "calls_verified": len(call_rows),
        "provider_envelopes_verified": len(envelope_rows),
        "pairs_verified": len(pair_rows),
        "pilot_item_ids": sorted({str(row.get("item_id") or "") for row in call_rows}),
        "pilot_repeats": sorted({int(row.get("repeat") or 0) for row in call_rows}),
        "call_order": [str(row.get("role") or "") for row in sorted(call_rows, key=lambda row: int(row.get("ordinal") or 0))],
        "submitted_seeds": seeds,
        "distinct_seed_submission": len(set(seeds.values())) == EXPECTED_CALLS,
        "raw_response_digests": raw_by_role,
        "raw_responses_identical": len(set(raw_by_role.values())) == 1 if len(raw_by_role) == EXPECTED_CALLS else None,
        "seed_honoring_attestation": "unavailable_from_provider",
        "fresh_session_contract": "new_provider_session_per_generation_call",
        "lineage_sha256": lineage_sha256,
        "pilot_manifest_sha256": pilot_manifest_sha256,
        "belief_effects": "none",
    }


__all__ = [
    "ROOT", "DATA", "FIXTURE_PATH", "CONTRACT_VERSION", "NAMESPACE", "EXPECTED_CALLS",
    "EXPECTED_PAIRS", "load_fixture", "verify_pilot_records",
]
