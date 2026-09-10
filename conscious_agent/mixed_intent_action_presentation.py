from __future__ import annotations

"""Preserve a bounded conversational acknowledgement beside governed action truth."""

import hashlib
import json
import re
from typing import Any

from natural_conversation_command_distinction import distinguish_natural_conversation_and_command


CONTRACT_VERSION = "v1500.9"
_AFFECTS = (
    ("fatigue", re.compile(r"\b(?:tired|worn out|exhausted|drained)\b", re.I), "I hear that you're tired."),
    ("frustration", re.compile(r"\b(?:frustrated|frustrating|upset)\b", re.I), "I hear that you're frustrated."),
    ("worry", re.compile(r"\b(?:worried|anxious|nervous|concerned)\b", re.I), "I hear that you're worried."),
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def present_mixed_intent_action_response(user_message: str, receipt_response: str) -> tuple[str, dict[str, Any]]:
    """Add one grounded affect acknowledgement without changing action claims."""
    response = str(receipt_response or "").strip()
    distinction = distinguish_natural_conversation_and_command(user_message)
    conversation_text = str(distinction.get("conversation_text") or "")
    acknowledgement = ""
    acknowledgement_kind = "none"
    if distinction.get("mixed_turn"):
        for kind, pattern, phrase in _AFFECTS:
            if pattern.search(conversation_text):
                acknowledgement_kind = kind
                acknowledgement = phrase
                break
    if acknowledgement and response:
        response = f"{acknowledgement} {response}"
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "mixed_turn": bool(distinction.get("mixed_turn")),
        "acknowledgement_added": bool(acknowledgement),
        "acknowledgement_kind": acknowledgement_kind,
        "receipt_response_preserved": bool(receipt_response),
        "provider_contacted": False,
        "provider_request_added": False,
        "authority_granted": False,
        "contains_conversation_text": False,
    }
    diagnostics["diagnostic_digest"] = _digest(diagnostics)
    return response, diagnostics


__all__ = ["CONTRACT_VERSION", "present_mixed_intent_action_response"]
