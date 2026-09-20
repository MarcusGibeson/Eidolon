from __future__ import annotations

"""Lossless Ollama envelope preservation and deterministic output extraction.

Ollama's GenerateResponse contract exposes ``response`` as the final response
and may expose ``thinking`` separately.  G-CORROB1 preserves the complete JSON
body before selecting either field.  ``thinking`` is accepted as an alternate
semantic payload only when ``response`` is empty and the alternate is itself a
complete JSON object; arbitrary reasoning text is never promoted to an
assessment.
"""

import base64
import hashlib
import json
from typing import Any, Mapping

from g_corrob1_contract import canonical_digest


CONTRACT_VERSION = "g-corrob1.provider-envelope.1"
OUTPUT_FIELDS = ("response", "thinking")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    # Provider evidence is byte-exact and must not use source-file newline normalization.
    return hashlib.sha256(value).hexdigest()


def parse_envelope_bytes(raw_body: bytes) -> dict[str, Any]:
    """Decode one non-streaming Ollama JSON response without losing its bytes."""
    try:
        value = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"malformed_provider_envelope:{type(error).__name__}") from error
    if not isinstance(value, dict):
        raise ValueError("malformed_provider_envelope:not_an_object")
    return value


def _complete_json_object(text: str) -> bool:
    try:
        return isinstance(json.loads(text), dict)
    except json.JSONDecodeError:
        return False


def extract_semantic_output(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Select semantic output under the frozen, fail-closed extraction policy."""
    present = {field: envelope[field] for field in OUTPUT_FIELDS if field in envelope}
    wrong_type = sorted(field for field, value in present.items() if not isinstance(value, str))
    field_digests = {
        field: canonical_digest(value) if isinstance(value, str) else canonical_digest(_canonical_json(value))
        for field, value in present.items()
    }
    base = {
        "contract_version": CONTRACT_VERSION,
        "accepted_fields": list(OUTPUT_FIELDS),
        "present_fields": sorted(present),
        "field_digests": field_digests,
        "selected_field": None,
        "method": None,
        "status": "failed",
        "reasons": [],
        "text": "",
    }
    if wrong_type:
        base["reasons"] = [f"non_text_output_field:{field}" for field in wrong_type]
        return _seal_extraction(base)

    populated = {
        field: value.strip() for field, value in present.items()
        if isinstance(value, str) and value.strip()
    }
    if not populated:
        base["reasons"] = ["no_usable_output_field"]
        return _seal_extraction(base)

    response = populated.get("response")
    thinking = populated.get("thinking")
    if response is not None and thinking is not None:
        if response != thinking:
            base["reasons"] = ["conflicting_output_fields:response,thinking"]
            return _seal_extraction(base)
        base.update(
            status="success", selected_field="response",
            method="consistent_contract_fields_response_precedence", text=response,
        )
        return _seal_extraction(base)

    if response is not None:
        base.update(status="success", selected_field="response", method="primary_response", text=response)
        return _seal_extraction(base)

    assert thinking is not None
    if not _complete_json_object(thinking):
        base["reasons"] = ["alternate_thinking_not_complete_json_object"]
        return _seal_extraction(base)
    base.update(
        status="success", selected_field="thinking",
        method="contract_alternate_structured_output", text=thinking,
    )
    return _seal_extraction(base)


def _seal_extraction(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    unsigned = {key: item for key, item in result.items() if key != "extraction_sha256"}
    result["extraction_sha256"] = canonical_digest(_canonical_json(unsigned))
    return result


def envelope_record(raw_body: bytes) -> dict[str, Any]:
    """Return a lossless, digest-bound provider envelope and extraction record."""
    envelope = parse_envelope_bytes(raw_body)
    extraction = extract_semantic_output(envelope)
    return {
        "raw_provider_envelope_b64": base64.b64encode(raw_body).decode("ascii"),
        "raw_provider_envelope_sha256": _sha256_bytes(raw_body),
        "provider_envelope": envelope,
        "provider_envelope_sha256": canonical_digest(_canonical_json(envelope)),
        "extracted_model_output": extraction["text"],
        "output_extraction": extraction,
    }


def raw_envelope_evidence(raw_body: bytes) -> dict[str, Any]:
    """Preserve exact body bytes even when the provider envelope is malformed."""
    extraction = _seal_extraction({
        "contract_version": CONTRACT_VERSION,
        "accepted_fields": list(OUTPUT_FIELDS),
        "present_fields": [],
        "field_digests": {},
        "selected_field": None,
        "method": None,
        "status": "failed",
        "reasons": ["provider_envelope_not_parsed"],
        "text": "",
    })
    return {
        "raw_provider_envelope_b64": base64.b64encode(raw_body).decode("ascii"),
        "raw_provider_envelope_sha256": _sha256_bytes(raw_body),
        "provider_envelope": None,
        "provider_envelope_sha256": "",
        "extracted_model_output": "",
        "output_extraction": extraction,
    }


def envelope_bytes_from_mapping(envelope: Mapping[str, Any]) -> bytes:
    """Canonical fixture representation; live code always uses HTTP body bytes."""
    return _canonical_json(dict(envelope)).encode("utf-8")


def verify_envelope_record(record: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        raw_body = base64.b64decode(str(record.get("raw_provider_envelope_b64") or ""), validate=True)
    except Exception:
        raw_body = b""
        reasons.append("raw_provider_envelope_base64_invalid")
    if _sha256_bytes(raw_body) != str(record.get("raw_provider_envelope_sha256") or ""):
        reasons.append("raw_provider_envelope_digest_mismatch")
    try:
        parsed = parse_envelope_bytes(raw_body)
    except ValueError as error:
        parsed = None
        reasons.append(str(error))
    stored_envelope = record.get("provider_envelope")
    if parsed is not None and parsed != stored_envelope:
        reasons.append("provider_envelope_structure_mismatch")
    if isinstance(stored_envelope, Mapping):
        if canonical_digest(_canonical_json(stored_envelope)) != str(record.get("provider_envelope_sha256") or ""):
            reasons.append("provider_envelope_digest_mismatch")
        expected_extraction = extract_semantic_output(stored_envelope)
        if expected_extraction != record.get("output_extraction"):
            reasons.append("output_extraction_mismatch")
        if expected_extraction["text"] != str(record.get("extracted_model_output") or ""):
            reasons.append("extracted_model_output_mismatch")
        if "raw_response" in record and str(record.get("raw_response") or "") != expected_extraction["text"]:
            reasons.append("legacy_raw_response_alias_mismatch")
    else:
        reasons.append("provider_envelope_missing_or_invalid")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "contract_version": CONTRACT_VERSION}


def fixture_envelope_fields(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Build production-shaped envelope fields for deterministic offline fixtures."""
    return envelope_record(envelope_bytes_from_mapping(envelope))


__all__ = [
    "CONTRACT_VERSION", "OUTPUT_FIELDS", "parse_envelope_bytes", "extract_semantic_output",
    "envelope_record", "raw_envelope_evidence", "envelope_bytes_from_mapping", "verify_envelope_record",
    "fixture_envelope_fields",
]
