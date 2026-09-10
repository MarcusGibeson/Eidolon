from __future__ import annotations

"""v1086.7 offline conversation degradation and queued operator intent.

The queue stores only bounded references and digests. It never submits a provider
request automatically, and returning provider availability never executes it.
"""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Mapping

from conversation_control_foundation import OFFLINE_INTENT_KINDS

OFFLINE_DEGRADATION_SCHEMA_VERSION = "1"
MAX_TARGET_ID_CHARS = 160


def _digest(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OfflineOperatorIntentResolution:
    intent_id: str
    kind: str
    target_turn_id: str
    draft_revision: int
    draft_content_digest: str
    state: str
    reason: str
    explicit_confirmation_required: bool = True
    automatic_execution: bool = False
    automatic_resend: bool = False
    provider_invoked: bool = False
    writes_state: bool = False
    contains_message_content: bool = False
    schema_version: str = OFFLINE_DEGRADATION_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_offline_operator_intent_record(
    *,
    kind: str,
    revision: int,
    updated_at: str,
    target_turn_id: str = "",
    draft_revision: int = 0,
    draft_content_digest: str = "",
    source: str = "operator",
) -> dict[str, Any]:
    kind_token = str(kind or "").strip().lower()
    if kind_token not in OFFLINE_INTENT_KINDS:
        raise ValueError("Unsupported offline operator intent.")
    target = str(target_turn_id or "").strip()
    if len(target) > MAX_TARGET_ID_CHARS or any(ord(char) < 32 for char in target):
        raise ValueError("Invalid offline intent target.")
    draft_rev = max(0, int(draft_revision or 0))
    draft_digest = str(draft_content_digest or "").strip().lower()
    material = f"{kind_token}\n{target}\n{draft_rev}\n{draft_digest}\n{revision}"
    return {
        "type": "queued_conversation_operator_intent",
        "schema_version": OFFLINE_DEGRADATION_SCHEMA_VERSION,
        "intent_id": _digest(material)[:32],
        "kind": kind_token,
        "target_turn_id": target,
        "draft_revision": draft_rev,
        "draft_content_digest": draft_digest,
        "revision": max(1, int(revision)),
        "updated_at": str(updated_at or "")[:40],
        "source": str(source or "operator")[:80],
        "explicit_confirmation_required": True,
        "automatic_execution": False,
        "automatic_resend": False,
    }


def resolve_offline_operator_intent(
    record: Mapping[str, Any] | None,
    *,
    current_draft_revision: int = 0,
    current_draft_digest: str = "",
    target_turn_exists: bool = True,
) -> OfflineOperatorIntentResolution:
    raw = record if isinstance(record, Mapping) else {}
    intent_id = str(raw.get("intent_id") or "")
    kind = str(raw.get("kind") or "").strip().lower()
    target = str(raw.get("target_turn_id") or "")
    draft_revision = max(0, int(raw.get("draft_revision") or 0))
    draft_digest = str(raw.get("draft_content_digest") or "").strip().lower()
    if not intent_id or kind not in OFFLINE_INTENT_KINDS:
        return OfflineOperatorIntentResolution("", "none", "", 0, "", "none", "no_queued_intent")
    if kind == "send_current_draft":
        stale = draft_revision != max(0, int(current_draft_revision or 0)) or draft_digest != str(current_draft_digest or "").strip().lower()
        return OfflineOperatorIntentResolution(
            intent_id, kind, target, draft_revision, draft_digest,
            "stale" if stale else "ready",
            "draft_changed" if stale else "draft_match",
        )
    if kind in {"retry_failed_turn", "regenerate_completed_turn", "resend_user_turn"} and (not target or not target_turn_exists):
        return OfflineOperatorIntentResolution(intent_id, kind, target, draft_revision, draft_digest, "stale", "target_turn_missing")
    return OfflineOperatorIntentResolution(intent_id, kind, target, draft_revision, draft_digest, "ready", "explicit_review_required")


def build_offline_degradation_state(
    *,
    session_state: Mapping[str, Any],
    pinned_context_count: int,
    queued_intent: OfflineOperatorIntentResolution,
    provider_available: bool = False,
) -> dict[str, Any]:
    capabilities = dict(session_state.get("capabilities") or {})
    capabilities.update({
        "pinned_working_context": True,
        "context_inspection": True,
        "message_branching": bool(session_state.get("session_active")),
        "queued_operator_intent": bool(session_state.get("session_active")),
        "queued_intent_auto_execution": False,
        "provider_generation": bool(provider_available),
        "automatic_request_replay": False,
    })
    return {
        "type": "conversation_offline_degradation",
        "schema_version": OFFLINE_DEGRADATION_SCHEMA_VERSION,
        "session_id": str(session_state.get("session_id") or ""),
        "session_available": bool(session_state.get("session_available")),
        "provider_available": bool(provider_available),
        "degradation_mode": "online" if provider_available else "local_surfaces_only",
        "draft_preserved": bool(session_state.get("has_draft")),
        "navigation_preserved": bool(capabilities.get("conversation_history")),
        "search_preserved": bool(capabilities.get("conversation_search")),
        "memory_browse_preserved": bool(capabilities.get("memory_curation")),
        "pinned_context_count": max(0, int(pinned_context_count)),
        "queued_operator_intent": queued_intent.public_summary(),
        "explicit_confirmation_required_after_recovery": queued_intent.state in {"ready", "stale"},
        "automatic_execution_after_recovery": False,
        "automatic_resend": False,
        "provider_response_fabricated": False,
        "assistant_memory_commit_allowed": False,
        "capabilities": capabilities,
        "content_free": True,
        "local_private": True,
        "provider_invoked": False,
        "writes_state": False,
    }


def offline_degradation_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "user_message", "assistant_response", "transcript", "prompt",
        "provider_payload", "credentials", "raw_response", "receipt", "memory", "memories", "chain_of_thought",
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


def offline_conversation_degradation_state(session_id: str = "", *, provider_available: bool = False) -> dict[str, Any]:
    """Load bounded private runtime metadata and return a content-free offline state."""
    from conversation_offline_durability import offline_session_durability_state
    from conversation_sessions import (
        conversation_controls_for_prompt,
        conversation_session_turns,
        load_conversation_draft,
    )
    state = offline_session_durability_state(session_id)
    resolved_id = str(state.get("session_id") or "")
    controls = conversation_controls_for_prompt(resolved_id) if resolved_id else {}
    pins = [row for row in controls.get("pinned_context", []) if isinstance(row, Mapping)] if isinstance(controls, Mapping) else []
    queued = controls.get("queued_operator_intent") if isinstance(controls, Mapping) and isinstance(controls.get("queued_operator_intent"), Mapping) else None
    draft = load_conversation_draft(resolved_id) if resolved_id else {}
    target_id = str((queued or {}).get("target_turn_id") or "")
    target_exists = True
    if target_id and resolved_id:
        target_exists = any(str(turn.get("id") or "") == target_id for turn in conversation_session_turns(resolved_id))
    resolution = resolve_offline_operator_intent(
        queued,
        current_draft_revision=int(draft.get("revision") or 0),
        current_draft_digest=str(draft.get("content_digest") or ""),
        target_turn_exists=target_exists,
    )
    return build_offline_degradation_state(
        session_state=state,
        pinned_context_count=len(pins),
        queued_intent=resolution,
        provider_available=provider_available,
    )
