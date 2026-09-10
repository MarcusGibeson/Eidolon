from __future__ import annotations

"""Content-free browser lifecycle recovery policy.

The policy coordinates status reconciliation after sleep, wake, focus, pageshow,
and network return. It never authorizes generation, retries, provider replay, model
management, or settings changes.
"""

from typing import Any

LIFECYCLE_RECOVERY_SCHEMA_VERSION = "1"
_ALLOWED_REASONS = {
    "initial-load", "history-return", "bfcache-return", "sleep-resume",
    "focus-recovery", "offline-recovery", "ownership-transfer", "tab-update",
}


def lifecycle_recovery_plan(
    reason: str,
    *,
    hidden: bool,
    online: bool,
    owns_control: bool,
    active_operation_id: str = "",
) -> dict[str, Any]:
    normalized = str(reason or "history-return").strip().lower()
    if normalized not in _ALLOWED_REASONS:
        normalized = "history-return"
    active = str(active_operation_id or "")[:120]
    return {
        "type": "conversation_lifecycle_recovery_plan",
        "schema_version": LIFECYCLE_RECOVERY_SCHEMA_VERSION,
        "reason": normalized,
        "coordination_action": "heartbeat" if owns_control else "register",
        "reconcile_session": bool(not hidden and online),
        "resume_operation_poll": bool(not hidden and online and active),
        "active_operation_id": active if not hidden and online else "",
        "visible": not hidden,
        "online": bool(online),
        "single_flight_required": True,
        "automatic_generation_retry": False,
        "automatic_resend": False,
        "provider_request_replayed": False,
        "provider_switch_allowed": False,
        "settings_mutation_allowed": False,
        "redacted": True,
        "content_free": True,
    }


def lifecycle_plan_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "message", "user_message", "assistant_response", "prompt", "response",
        "provider_payload", "credentials", "endpoint", "model", "draft_content",
        "raw_response", "command_output", "receipt_payload",
    }
    return bool(forbidden & {str(key) for key in value})
