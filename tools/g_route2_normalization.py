from __future__ import annotations

"""Deterministic transport canonicalization for G-ROUTE2 JSON-profile outputs.

This layer removes one kind of transport wrapper and nothing else. It is not
repair. It never edits, adds, removes, reorders or retypes a field; it never
completes truncated JSON; it never selects among candidate payloads. Given an
ambiguous wrapper it fails closed and lets structural validation reject the
output.

Root type is a structural question, not a transport one: an array or scalar
payload canonicalizes successfully and is then rejected downstream. This keeps
normalization outcomes free of any structural or semantic judgment.
"""

import hashlib
import json
import re
from typing import Any, Mapping


CONTRACT_VERSION = "g-route2.transport-normalization.v1"

RAW_VALID = "raw_valid"
FENCE_REMOVED = "fence_removed"
WRAPPER_REJECTED = "wrapper_rejected"
INVALID_JSON = "invalid_json"
MULTIPLE_PAYLOADS = "multiple_payloads"
TRAILING_TEXT = "trailing_text"
NOT_APPLICABLE = "not_applicable"

OUTCOMES = (RAW_VALID, FENCE_REMOVED, WRAPPER_REJECTED, INVALID_JSON,
            MULTIPLE_PAYLOADS, TRAILING_TEXT, NOT_APPLICABLE)
ACCEPTED_OUTCOMES = (RAW_VALID, FENCE_REMOVED)
JSON_PROFILES = ("extraction.v1", "research.v1", "synthesis.v1", "coding.v1", "planning.v1")
TEXT_PROFILES = ("conversation.v1",)

ALLOWED_FENCE_TAGS = frozenset({"", "json"})
_FENCE = re.compile(r"^```([A-Za-z0-9_+.-]*)[ \t]*\r?\n(.*?)\r?\n?```$", re.DOTALL)
_BLOCK = re.compile(r"```([A-Za-z0-9_+.-]*)[ \t]*\r?\n(.*?)\r?\n?```", re.DOTALL)
_DECODER = json.JSONDecoder()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _one_json_value(text: str) -> tuple[Any, str]:
    """Parse exactly one JSON value spanning the whole string.

    Returns (value, outcome_token) where the token is "" on success,
    MULTIPLE_PAYLOADS when a second value follows, TRAILING_TEXT when
    non-JSON text follows, and INVALID_JSON when nothing parses.
    """
    stripped = text.strip()
    if not stripped:
        return None, INVALID_JSON
    try:
        value, end = _DECODER.raw_decode(stripped)
    except ValueError:
        return None, INVALID_JSON
    remainder = stripped[end:].strip()
    if not remainder:
        return value, ""
    try:
        _DECODER.raw_decode(remainder)
    except ValueError:
        return None, TRAILING_TEXT
    return None, MULTIPLE_PAYLOADS


def normalize(raw_output: Any, *, validator_profile: str) -> dict[str, Any]:
    """Canonicalize the transport wrapper of one model output.

    The original bytes are always preserved verbatim in `raw_output`. When the
    outcome is not accepted, `payload` is the original text unchanged, so a
    rejected wrapper reaches structural validation exactly as the model wrote it.
    """
    raw_text = raw_output if isinstance(raw_output, str) else json.dumps(raw_output, sort_keys=True)
    record = {
        "contract_version": CONTRACT_VERSION,
        "validator_profile": str(validator_profile),
        "raw_output": raw_text,
        "raw_sha256": digest(raw_text),
        "normalized": False,
        "outcome": NOT_APPLICABLE,
        "payload": raw_text,
        "payload_sha256": digest(raw_text),
        "wrapper_removed": "",
        "is_repair": False,
        "semantic_values_changed": False,
    }
    if validator_profile not in JSON_PROFILES:
        return record

    stripped = raw_text.strip()
    if not stripped:
        record["outcome"] = INVALID_JSON
        return record

    if "```" not in stripped:
        value, token = _one_json_value(stripped)
        if token:
            record["outcome"] = token
            return record
        record["outcome"] = RAW_VALID
        record["payload"] = stripped
        record["payload_sha256"] = digest(stripped)
        return record

    blocks = list(_BLOCK.finditer(stripped))
    if not blocks:
        record["outcome"] = WRAPPER_REJECTED
        record["wrapper_removed"] = "unterminated_fence"
        return record
    outside = stripped[:blocks[0].start()] + "".join(
        stripped[left.end():right.start()] for left, right in zip(blocks, blocks[1:])
    ) + stripped[blocks[-1].end():]
    if "```" in outside:
        record["outcome"] = WRAPPER_REJECTED
        record["wrapper_removed"] = "ambiguous_fence_structure"
        return record
    if len(blocks) > 1:
        record["outcome"] = MULTIPLE_PAYLOADS if not outside.strip() else TRAILING_TEXT
        return record
    if outside.strip():
        record["outcome"] = TRAILING_TEXT
        return record

    match = _FENCE.match(stripped)
    if match is None:
        record["outcome"] = WRAPPER_REJECTED
        record["wrapper_removed"] = "ambiguous_fence_structure"
        return record
    tag, body = match.group(1).strip().lower(), match.group(2)
    if tag not in ALLOWED_FENCE_TAGS:
        record["outcome"] = WRAPPER_REJECTED
        record["wrapper_removed"] = "unsupported_fence_tag:" + tag
        return record
    if "```" in body:
        record["outcome"] = WRAPPER_REJECTED
        record["wrapper_removed"] = "nested_fence"
        return record
    value, token = _one_json_value(body)
    if token:
        record["outcome"] = token
        return record
    payload = body.strip()
    if json.loads(payload) != value:
        record["outcome"] = WRAPPER_REJECTED
        record["wrapper_removed"] = "non_idempotent_payload"
        return record
    record["normalized"] = True
    record["outcome"] = FENCE_REMOVED
    record["payload"] = payload
    record["payload_sha256"] = digest(payload)
    record["wrapper_removed"] = "markdown_fence:" + (tag or "untagged")
    return record


def semantic_values_preserved(record: Mapping[str, Any]) -> bool:
    """True when the canonicalized payload parses to the same value as the wrapper body.

    For a non-normalized record this is vacuously true because the payload is the
    original text. For a normalized record it asserts that stripping the fence
    changed no field, value, ordering-independent key set, or type.
    """
    if not record.get("normalized"):
        return record.get("payload") == record.get("raw_output")
    inner = _FENCE.match(str(record["raw_output"]).strip())
    if inner is None:
        return False
    try:
        return json.loads(str(record["payload"])) == json.loads(inner.group(2))
    except ValueError:
        return False


def outcome_counts(records) -> dict[str, int]:
    counts = {outcome: 0 for outcome in OUTCOMES}
    for record in records:
        counts[str(record["outcome"])] = counts.get(str(record["outcome"]), 0) + 1
    return counts


__all__ = [
    "CONTRACT_VERSION", "OUTCOMES", "ACCEPTED_OUTCOMES", "JSON_PROFILES", "TEXT_PROFILES",
    "RAW_VALID", "FENCE_REMOVED", "WRAPPER_REJECTED", "INVALID_JSON", "MULTIPLE_PAYLOADS",
    "TRAILING_TEXT", "NOT_APPLICABLE", "digest", "normalize", "semantic_values_preserved",
    "outcome_counts",
]
