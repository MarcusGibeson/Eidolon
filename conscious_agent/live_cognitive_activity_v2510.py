from __future__ import annotations

"""v2510 safe live cognitive/action activity projection.

This is a user-facing status surface, not a chain-of-thought recorder. It turns
real runtime event classes into short bounded summaries. Raw prompts, hidden
reasoning, model scratch text, tool arguments, and provider output are never
copied into activity events.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v2510.0"
ACTIVITY_KINDS = frozenset({"activity", "observation", "milestone"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _event(kind: str, stage: str, summary: str, source: Mapping[str, Any], *, operation_id: str = "") -> dict[str, Any]:
    row = {
        "event": "activity",
        "contract_version": CONTRACT_VERSION,
        "activity_kind": kind,
        "stage": str(stage or "working")[:80],
        "summary": " ".join(str(summary or "").split())[:180],
        "operation_id": str(operation_id or source.get("operation_id") or "")[:160],
        "source_event": str(source.get("event") or "message")[:40],
        "source_event_digest": _digest({
            "event": source.get("event"),
            "stage": source.get("stage"),
            "operation_id": operation_id or source.get("operation_id"),
        }),
        "hidden_reasoning_exposed": False,
        "raw_prompt_stored": False,
        "raw_provider_output_stored": False,
        "tool_arguments_stored": False,
        "content_minimized": True,
    }
    row["activity_digest"] = _digest(row)
    return row


def project_live_activity(source: Mapping[str, Any], *, operation_id: str = "") -> dict[str, Any] | None:
    event = str(source.get("event") or "").strip().lower()
    if event == "accepted":
        return _event("milestone", "accepted", "Request accepted. Preparing the conversation runtime.", source, operation_id=operation_id)
    if event == "meta":
        return _event("activity", "context", "Reviewing current conversation context and runtime state.", source, operation_id=operation_id)
    if event == "status":
        stage = str(source.get("stage") or "working").strip().lower()
        summaries = {
            "governed_action": "Routing the request through supervised action governance.",
            "action_execution": "Running the explicitly authorized bounded action.",
            "action_retry": "Retrying the exact linked bounded action.",
            "action_control": "Applying the requested pending-action control.",
            "action_ready": "Action preparation is complete and awaiting review.",
            "conversation_only": "Conversation work is complete; no external action was needed.",
            "saving": "Finalizing durable conversation state.",
        }
        return _event("activity", stage, summaries.get(stage, "Working through the current response stage."), source, operation_id=operation_id)
    if event == "action":
        return _event("milestone", "action_proposed", "A supervised action candidate was recognized for review.", source, operation_id=operation_id)
    if event == "action_result":
        return _event("milestone", "action_result", "The supervised action returned a governed result receipt.", source, operation_id=operation_id)
    if event == "conversation_complete":
        result = source.get("result") if isinstance(source.get("result"), Mapping) else {}
        success = bool(result.get("success"))
        return _event("milestone", "response_complete", "Response processing completed successfully." if success else "Response processing stopped with a bounded failure state.", source, operation_id=operation_id)
    if event == "saved":
        return _event("milestone", "saved", "The completed turn was saved to conversation continuity.", source, operation_id=operation_id)
    if event == "error":
        return _event("milestone", "error", "The current operation stopped safely after an error.", source, operation_id=operation_id)
    return None


__all__ = ["CONTRACT_VERSION", "ACTIVITY_KINDS", "project_live_activity"]
