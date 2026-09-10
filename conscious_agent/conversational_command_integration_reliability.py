from __future__ import annotations

"""v1259.6-v1259.8 read-only reliability inspection and operator handoff."""

from pathlib import Path
from typing import Any

from conversational_command_integration_foundations import DENIED_AUTHORITY
from ordinary_chat_development_campaign import _digest

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1259.8"

_REQUIRED = (
    "conscious_agent/conversational_command_integration_foundations.py",
    "conscious_agent/conversational_command_integration.py",
    "conscious_agent/natural_conversation_command_distinction.py",
    "conscious_agent/natural_language_action_routing.py",
    "conscious_agent/ordinary_chat_development_campaign.py",
    "conscious_agent/conversation_runtime.py",
    "tools/v1259_0_2_conversational_command_integration_foundations_tests.py",
    "tools/v1259_3_5_conversational_command_integration_tests.py",
    "tools/v1259_6_8_conversational_command_integration_reliability_tests.py",
)


def inspect_conversational_command_integration_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    texts = {rel: (root / rel).read_text(encoding="utf-8") if (root / rel).is_file() else "" for rel in _REQUIRED}
    foundation = texts[_REQUIRED[0]]
    integration = texts[_REQUIRED[1]]
    runtime = texts[_REQUIRED[5]]
    ordinary = texts[_REQUIRED[4]]
    checks = {
        "all_required_surfaces_present": all(bool(texts[rel]) for rel in _REQUIRED),
        "speech_act_categories_present": all(token in foundation for token in ("discussion", "hypothetical", "information_request", "action_request", "authorization", "correction", "cancellation")),
        "generic_authorization_blocked": "generic_authorization_blocked" in integration and "exact_authorization_must_not_be_inferred" in foundation,
        "correction_uses_existing_revision_path": "revise_development_campaign_proposal" in integration,
        "cancellation_uses_existing_terminal_path": "cancel_development_campaign_proposal" in integration,
        "conversation_runtime_projection_wired": "conversational_command_integration" in runtime,
        "ordinary_chat_control_wired": "process_conversational_development_control" in ordinary,
        "no_new_execution_engine": "provider_generate" not in integration and "subprocess" not in integration,
    }
    row = {
        "ok": all(checks.values()),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "conversational_command_integration_healthy" if all(checks.values()) else "conversational_command_integration_health_blocked",
        "checks": checks,
        "required_surface_count": len(_REQUIRED),
        "read_only": True,
        "content_minimized": True,
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        "native_windows_multi_process_validation": "desktop_review_required",
        **DENIED_AUTHORITY,
    }
    row["health_digest"] = _digest(row)
    return row


def build_conversational_command_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_conversational_command_integration_health(source_root=source_root)
    row = {
        "ok": bool(health.get("ok")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "conversational_command_operator_handoff_ready" if health.get("ok") else "conversational_command_operator_handoff_blocked",
        "health_digest": health.get("health_digest", ""),
        "desktop_focus": [
            "ordinary conversation with wishes, hypotheticals, quotes, and information requests must not create development proposals",
            "mixed conversation plus one coding imperative must create at most one supervised proposal while retaining a conversational response",
            "generic authorization must never substitute for an exact proposal/execution/application authorization",
            "correction must revise exactly one pending proposal and make its prior revision stale",
            "cancellation must resolve exactly one pending proposal or fail closed",
            "multiple tabs/processes and restart restoration must not duplicate corrections, cancellations, approvals, or execution",
        ],
        "limitations": [
            "Deterministic speech-act rules do not claim general natural-language understanding.",
            "Ambiguous references fail closed rather than guessing a target.",
            "Exact authorization semantics remain owned by the pre-existing governed proposal/execution/application contracts.",
        ],
        "read_only": True,
        "operator_review_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        "native_windows_multi_process_validation": "desktop_review_required",
        **DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "build_conversational_command_operator_handoff", "inspect_conversational_command_integration_health"]
