from __future__ import annotations

"""Bounded v1088.0 Desktop Alpha operator evaluation campaign protocol.

The protocol consumes the verified v1087.9 daily-evaluation checkpoint and
specifies an operator-started campaign contract. It does not create campaigns,
start evaluations, inspect private notes or transcripts, call a provider,
change models or settings, score releases, or authorize installation/promotion.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation_checkpoint import build_daily_evaluation_checkpoint
from conversation_daily_evaluation_protocol import EVALUATION_SIGNALS
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

EVALUATION_CAMPAIGN_PROTOCOL_SCHEMA_VERSION = "1"
CAMPAIGN_STATES = ("planned", "active", "completed", "aborted")
CAMPAIGN_FOCUS_AREAS = (
    "everyday_consecutive_use",
    "restart_and_resumption",
    "provider_outage_and_return",
    "interruption_and_recovery",
    "long_session_usability",
    "multi_tab_coordination",
    "memory_and_relationship_continuity",
    "conversation_quality",
)
MIN_CAMPAIGN_EVALUATIONS = 1
MAX_CAMPAIGN_EVALUATIONS = 32
MIN_CAMPAIGN_DURATION_DAYS = 1
MAX_CAMPAIGN_DURATION_DAYS = 30
MAX_CAMPAIGN_LABEL_CHARS = 120
MAX_CAMPAIGN_OBJECTIVE_CHARS = 2_000
MAX_CAMPAIGN_FOCUS_AREAS = len(CAMPAIGN_FOCUS_AREAS)
MAX_CAMPAIGN_REQUIRED_SIGNALS = 12


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_evaluation_campaign_protocol() -> dict[str, Any]:
    checkpoint = build_daily_evaluation_checkpoint()
    checkpoint_ready = checkpoint.get("checkpoint_status") == "ready_for_operator_daily_evaluation"
    contract = {
        "campaign_states": list(CAMPAIGN_STATES),
        "focus_areas": list(CAMPAIGN_FOCUS_AREAS),
        "evaluation_signals": list(EVALUATION_SIGNALS),
        "limits": {
            "minimum_campaign_evaluations": MIN_CAMPAIGN_EVALUATIONS,
            "maximum_campaign_evaluations": MAX_CAMPAIGN_EVALUATIONS,
            "minimum_campaign_duration_days": MIN_CAMPAIGN_DURATION_DAYS,
            "maximum_campaign_duration_days": MAX_CAMPAIGN_DURATION_DAYS,
            "maximum_campaign_label_chars": MAX_CAMPAIGN_LABEL_CHARS,
            "maximum_campaign_objective_chars": MAX_CAMPAIGN_OBJECTIVE_CHARS,
            "maximum_focus_areas": MAX_CAMPAIGN_FOCUS_AREAS,
            "maximum_required_signals": MAX_CAMPAIGN_REQUIRED_SIGNALS,
        },
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "campaign_launch_is_explicit": True,
        "evaluation_creation_is_explicit": True,
        "evaluation_enrollment_is_explicit": True,
        "automatic_campaign_launch": False,
        "automatic_evaluation_creation": False,
        "automatic_provider_request": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "autonomous_scoring": False,
        "automatic_release_certification": False,
        "release_decision": "operator_only",
    }
    return {
        "type": "desktop_alpha_operator_evaluation_campaign_protocol",
        "schema_version": EVALUATION_CAMPAIGN_PROTOCOL_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "protocol_status": "ready" if checkpoint_ready else "review_required",
        "daily_evaluation_checkpoint_status": str(checkpoint.get("checkpoint_status") or "unknown"),
        "daily_evaluation_contract_digest": str(checkpoint.get("contract_digest") or ""),
        "daily_evaluation_areas_digest": str(checkpoint.get("areas_digest") or ""),
        "daily_evaluation_area_count": max(0, int(checkpoint.get("area_count") or 0)),
        **contract,
        "campaign_contract_digest": _digest(contract),
        "private_plan_runtime_only": True,
        "transcript_content_required": False,
        "private_notes_required": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "model_management": False,
        "provider_switching": False,
        "generation_settings_changed": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def evaluation_campaign_protocol_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "messages", "user_message", "assistant_response",
        "transcript", "prompt", "note", "notes", "objective", "campaign_label",
        "temporary_instruction", "pinned_context", "queued_operator_intent",
        "provider_payload", "credentials", "vectors", "embedding", "receipt",
        "receipts", "hidden_reasoning", "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
