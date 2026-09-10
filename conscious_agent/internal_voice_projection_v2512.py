from __future__ import annotations

"""v2512 state-grounded internal voice projections.

These are short first-person verbalizations of *known structural runtime state*.
They are not transcripts of hidden reasoning and never accept arbitrary model
scratch text as input. The initial implementation is provider-free and fully
deterministic so its semantics can be audited before richer generation exists.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v2512.0"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


_ACTIVITY_VOICE = {
    "accepted": "I'm orienting to the request before I respond.",
    "context": "I'm checking the current conversation context and runtime state.",
    "governed_action": "I need to keep this request inside the supervised action boundary.",
    "action_proposed": "I've recognized an action candidate, but it still needs the required review.",
    "action_result": "I have a governed result receipt to work from now.",
    "response_complete": "I have enough processed state to finish the response.",
    "saved": "I've preserved the completed turn in conversation continuity.",
    "error": "Something failed, so I'm stopping this operation safely instead of guessing forward.",
}

_COGNITIVE_VOICE = {
    "REFLECT": "I'm reflecting on the current concern before deciding whether anything should change.",
    "CONTINUE_THOUGHT": "I'm returning to an unfinished thought instead of starting over.",
    "RECONSIDER_BELIEF": "Something deserves another look before I keep treating the earlier belief as settled.",
    "REVIEW_GOAL": "I'm checking whether the current goal still deserves its place in my priorities.",
    "PLAN": "I'm organizing the next steps before treating the goal as actionable.",
    "REPLAN": "The old route may no longer fit the evidence, so I'm reconsidering the plan.",
    "INTEGRATE_EXPERIENCE": "I'm connecting this experience to what I already retain instead of leaving it isolated.",
    "REVIEW_SELF_MODEL": "I'm comparing this behavior with the evidence I retain about my own tendencies.",
    "RESOLVE_CONFLICT": "I have conflicting state to reconcile before I can treat either side as settled.",
    "REST": "Nothing useful needs more cognition from me right now.",
}


def project_activity_internal_voice(activity: Mapping[str, Any]) -> dict[str, Any] | None:
    if str(activity.get("event") or "") != "activity":
        return None
    stage = str(activity.get("stage") or "").strip().lower()
    text = _ACTIVITY_VOICE.get(stage)
    if not text:
        return None
    row = {
        "event": "internal_voice",
        "contract_version": CONTRACT_VERSION,
        "voice_text": text,
        "grounded_stage": stage,
        "source_activity_digest": str(activity.get("activity_digest") or "")[:64],
        "representation_kind": "state_grounded_internal_voice_projection",
        "provider_contacted": False,
        "hidden_reasoning_exposed": False,
        "claims_literal_thought_transcript": False,
        "raw_prompt_stored": False,
        "raw_provider_output_stored": False,
        "content_minimized": True,
    }
    row["voice_digest"] = _digest(row)
    return row


def project_cognitive_internal_voice(cycle: Mapping[str, Any]) -> dict[str, Any] | None:
    operation = str(cycle.get("selected_operation") or cycle.get("operation") or "").strip().upper()
    text = _COGNITIVE_VOICE.get(operation)
    if not text:
        return None
    source_digest = str(cycle.get("frame_digest") or cycle.get("source_digest") or "")[:64]
    row = {
        "event": "internal_voice",
        "contract_version": CONTRACT_VERSION,
        "voice_text": text,
        "grounded_operation": operation,
        "source_state_digest": source_digest,
        "representation_kind": "state_grounded_internal_voice_projection",
        "provider_contacted": False,
        "hidden_reasoning_exposed": False,
        "claims_literal_thought_transcript": False,
        "raw_cognitive_content_stored": False,
        "content_minimized": True,
    }
    row["voice_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "project_activity_internal_voice", "project_cognitive_internal_voice"]
