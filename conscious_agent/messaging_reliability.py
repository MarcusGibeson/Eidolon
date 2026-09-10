from __future__ import annotations

"""Content-free messaging timing, keyboard intent, and exactly-once evidence.

This module does not store message text, contact a provider, mutate conversations,
or grant release authority. It supplies bounded decisions and redacted evidence for
v1103 reliable instant messaging surfaces.
"""

from typing import Any

SCHEMA_VERSION = "1"


def _ms(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return None


def build_first_visible_timing(
    *,
    intent_to_acceptance_ms: Any = None,
    acceptance_to_first_transport_ms: Any = None,
    acceptance_to_first_visible_ms: Any = None,
    intent_to_first_visible_ms: Any = None,
    render_delay_ms: Any = None,
    total_ms: Any = None,
) -> dict[str, Any]:
    """Return a content-free phase report without inventing missing timings."""
    phases = {
        "intent_to_acceptance_ms": _ms(intent_to_acceptance_ms),
        "acceptance_to_first_transport_ms": _ms(acceptance_to_first_transport_ms),
        "acceptance_to_first_visible_ms": _ms(acceptance_to_first_visible_ms),
        "intent_to_first_visible_ms": _ms(intent_to_first_visible_ms),
        "render_delay_ms": _ms(render_delay_ms),
        "total_ms": _ms(total_ms),
    }
    visible = phases["intent_to_first_visible_ms"]
    return {
        "type": "message_delivery_timing",
        "schema_version": SCHEMA_VERSION,
        "status": "measured" if visible is not None else "pending",
        "first_visible_token_measured": visible is not None,
        "phases": phases,
        "content_free": True,
        "contains_message_text": False,
        "contains_response_text": False,
        "contains_prompt_text": False,
        "private_paths_included": False,
        "provider_payload_included": False,
    }


def keyboard_intent(
    *,
    key: str = "",
    shift: bool = False,
    composing: bool = False,
    key_code: int = 0,
    input_type: str = "",
    submission_pending: bool = False,
    repeated: bool = False,
) -> dict[str, Any]:
    """Resolve one keyboard/beforeinput signal without submitting during IME composition."""
    normalized_key = str(key or "")
    normalized_input = str(input_type or "")
    is_line_signal = normalized_key == "Enter" or normalized_input in {"insertLineBreak", "insertParagraph"}
    composition_active = bool(composing or int(key_code or 0) == 229)
    if not is_line_signal:
        action = "ignore"
    elif composition_active:
        action = "composition"
    elif shift:
        action = "newline"
    elif submission_pending or repeated:
        action = "blocked_duplicate"
    else:
        action = "send"
    return {
        "action": action,
        "prevent_default": action in {"send", "blocked_duplicate"},
        "submit_once": action == "send",
        "composition_active": composition_active,
        "content_free": True,
    }


def build_exactly_once_evidence(
    *,
    acceptance_claim_count: int,
    operation_count: int,
    execution_start_count: int,
    provider_request_count: int,
    duplicate_submission_count: int = 0,
    automatic_retry_count: int = 0,
) -> dict[str, Any]:
    claims = max(0, int(acceptance_claim_count))
    operations = max(0, int(operation_count))
    executions = max(0, int(execution_start_count))
    provider_requests = max(0, int(provider_request_count))
    duplicates = max(0, int(duplicate_submission_count))
    retries = max(0, int(automatic_retry_count))
    exactly_once = claims == 1 and operations == 1 and executions == 1 and provider_requests <= 1 and retries == 0
    return {
        "type": "message_exactly_once_evidence",
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if exactly_once else "blocked",
        "exactly_once": exactly_once,
        "acceptance_claim_count": claims,
        "operation_count": operations,
        "execution_start_count": executions,
        "provider_request_count": provider_requests,
        "duplicate_submission_count": duplicates,
        "automatic_retry_count": retries,
        "duplicate_submissions_converged": duplicates == 0 or operations == 1,
        "content_free": True,
        "contains_message_text": False,
        "contains_response_text": False,
        "provider_payload_included": False,
    }
