from __future__ import annotations

"""Evaluator-side (gold-using) judgment for G-ROUTE3, plus the one coding canonicalization.

- conversation.v1 is judged on the disclosed answer frame (g_route3_conversation).
- coding.v1: `old` is compared with the supplied source ignoring trailing newlines. In G-ROUTE1 and
  G-ROUTE2 the mid model returned `old` without the file's final newline in 10-11 of 12 coding calls,
  and a correct, test-passing fix then failed on that byte alone. By operator decision G-ROUTE3
  measures code repair, not newline fidelity. `canonical_coding_payload` restores the exact source
  as `old` when the only difference is trailing newlines; the runner builds execution evidence from
  the same canonical payload, so the candidate digest agrees. Any other difference in `old` is
  left untouched and still fails.
- every other profile is judged by the frozen G-ROUTE1 validators, unchanged.

g_route1_validators.py itself is not modified.
"""

import json
from typing import Any, Mapping

from g_route1_validators import validate_fixture_output as _g_route1_validate
import g_route3_conversation as conversation

CONTRACT_VERSION = "g-route3.semantics.v1"


def canonical_coding_payload(fixture: Mapping[str, Any], payload: Any) -> tuple[Any, bool]:
    """Return (payload, changed). Changed only when `old` differs from the source by trailing newlines alone."""
    if str(fixture.get("validator_profile") or "") != "coding.v1":
        return payload, False
    try:
        value = dict(payload) if isinstance(payload, Mapping) else json.loads(str(payload))
    except (TypeError, ValueError, RecursionError):
        return payload, False
    if not isinstance(value, dict):
        return payload, False
    source = str(fixture["input"]["source"])
    old = value.get("old")
    if not isinstance(old, str) or old == source or old.rstrip("\r\n") != source.rstrip("\r\n"):
        return payload, False
    value["old"] = source
    return (value if isinstance(payload, Mapping) else json.dumps(value, ensure_ascii=False)), True


def validate_fixture_output(fixture: Mapping[str, Any], gold: Mapping[str, Any], raw_output: Any, *,
                            execution_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Never raises on model output: an evaluator exception is a failed answer, recorded with its type."""
    try:
        return _judge(fixture, gold, raw_output, execution_evidence)
    except Exception as exc:
        return {"contract_version": CONTRACT_VERSION, "valid": False, "hard_gate_pass": False,
                "reasons": [f"evaluator_exception_on_model_output:{type(exc).__name__}"], "metrics": {},
                "belief_effects": "none", "routing_authority": False}


def _judge(fixture: Mapping[str, Any], gold: Mapping[str, Any], raw_output: Any,
           execution_evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    profile = str(fixture.get("validator_profile") or "")
    if profile == "conversation.v1":
        return conversation.semantic(fixture, gold, raw_output)
    payload, _ = canonical_coding_payload(fixture, raw_output)
    if profile == "synthesis.v1":
        payload = _typographic_statement_text(payload)
    return _g_route1_validate(fixture, gold, payload, execution_evidence=execution_evidence)


def _typographic_statement_text(payload: Any) -> Any:
    """Synthesis statements copy observation text verbatim; a typographic hyphen, dash, quote or no-break space
    in that copy is the same text. Normalize statement text only (as the conversation frame does)."""
    try:
        value = dict(payload) if isinstance(payload, Mapping) else json.loads(str(payload))
    except (TypeError, ValueError, RecursionError):
        return payload
    statements = value.get("statements") if isinstance(value, dict) else None
    if not isinstance(statements, list):
        return payload
    value["statements"] = [{**row, "text": conversation.normalize_text(row["text"])}
                           if isinstance(row, dict) and isinstance(row.get("text"), str) else row
                           for row in statements]
    return value if isinstance(payload, Mapping) else json.dumps(value, ensure_ascii=False)


__all__ = ["CONTRACT_VERSION", "canonical_coding_payload", "validate_fixture_output"]
