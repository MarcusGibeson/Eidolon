from __future__ import annotations

"""Read-only v1085.8 operator context inspection console.

The console reports lane, budget, ranking, correction, linking, stale-summary,
and provenance evidence. It never returns prompt text or hidden reasoning and
never contacts a generation or embedding provider.
"""

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "1"


def _plain(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def build_context_inspection_console(metrics: Any, *, session_id: str = "") -> dict[str, Any]:
    raw = _plain(metrics)
    values = raw if isinstance(raw, Mapping) else {}
    lane_order = list(values.get("context_lane_order") or ())
    included = list(values.get("context_lanes_included") or ())
    omitted = list(values.get("context_lanes_omitted") or ())
    inclusion_reasons = {
        lane: (
            "protected_current_turn" if lane == "current_turn"
            else "explicit_correction" if lane == "correction_evidence"
            else "eligible_whole_records_within_lane_budget"
        )
        for lane in included
    }
    return {
        "type": "context_inspection_console",
        "schema_version": SCHEMA_VERSION,
        "session_id_present": bool(session_id),
        "lane_order": lane_order,
        "lanes_included": included,
        "lanes_omitted": omitted,
        "lane_candidates": dict(values.get("context_lane_candidates") or {}),
        "inclusion_reasons": inclusion_reasons,
        "allocated_tokens": dict(values.get("context_budget_allocated_tokens") or {}),
        "used_tokens": dict(values.get("context_budget_used_tokens") or {}),
        "omissions_by_lane": dict(values.get("context_budget_omissions_by_lane") or {}),
        "omission_reasons": dict(values.get("context_budget_omission_reasons") or {}),
        "topic": {
            "segment_count": int(values.get("context_topic_segment_count", 0)),
            "active_turn_count": int(values.get("context_topic_active_turn_count", 0)),
            "unrelated_turns_excluded": int(values.get("context_topic_unrelated_turns_excluded", 0)),
            "selection_reason": str(values.get("context_topic_selection_reason") or "no_history"),
        },
        "ranking": {
            "candidate_count": int(values.get("context_ranked_candidate_count", 0)),
            "top_score": int(values.get("context_top_rank_score", 0)),
            "salience_reservations": int(values.get("context_salience_reservations", 0)),
        },
        "provenance_states": dict(values.get("context_provenance_states") or {}),
        "corrections": {
            "records": int(values.get("context_correction_records", 0)),
            "exact_suppressed": int(values.get("context_correction_exact_suppressed", 0)),
            "linked_suppressed": int(values.get("context_correction_explicit_link_suppressed", 0)),
            "ambiguous_similarity_suppressed": int(
                values.get("context_correction_ambiguous_similarity_suppressed", 0)
            ),
        },
        "cross_session": {
            "candidate_sessions": int(values.get("context_cross_session_candidate_sessions", 0)),
            "candidate_turns": int(values.get("context_cross_session_candidate_turns", 0)),
            "linked_sessions": int(values.get("context_cross_session_linked_sessions", 0)),
            "linked_turns": int(values.get("context_cross_session_linked_turns", 0)),
            "turns_included": int(values.get("context_cross_session_turns_included", 0)),
            "turns_omitted": int(values.get("context_cross_session_turns_omitted", 0)),
        },
        "stale_summaries": {
            "candidates": int(values.get("context_stale_summary_candidates", 0)),
            "detected": int(values.get("context_stale_summaries_detected", 0)),
            "suppressed": int(values.get("context_stale_summaries_suppressed", 0)),
            "corrected_conflicts": int(values.get("context_stale_summary_corrected_conflicts", 0)),
            "retracted_conflicts": int(values.get("context_stale_summary_retracted_conflicts", 0)),
            "deleted_conflicts": int(values.get("context_stale_summary_deleted_conflicts", 0)),
            "current_session_conflicts": int(
                values.get("context_stale_summary_current_session_conflicts", 0)
            ),
        },
        "offline_available": True,
        "read_only": True,
        "provider_invoked": False,
        "writes_state": False,
        "contains_context_content": False,
        "contains_hidden_reasoning": False,
    }


def context_inspection_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "prompt", "content", "summary", "transcript", "message", "user_message",
        "assistant_response", "memory", "provider_payload", "credentials", "vector",
        "embedding", "chain_of_thought", "reasoning_trace",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(current)
    return False


def build_context_inspection_for_session(session_id: str = "") -> dict[str, Any]:
    """Build a read-only inspection from stored local state without provider access."""

    from conversation_context import build_conversation_prompt
    from conversation_sessions import (
        list_conversation_sessions,
        load_conversation_session,
    )
    from memory import load_memories

    session = load_conversation_session(session_id, include_turns=True) if session_id else None
    turns = [turn for turn in ((session or {}).get("turns") or []) if isinstance(turn, Mapping)]
    history = [
        {
            "user_message": str(turn.get("user_message") or ""),
            "assistant_response": str(turn.get("assistant_response") or ""),
            "completion_state": str(turn.get("completion_state") or ""),
            "success": bool(turn.get("success", True)),
            "corrects_summary_id": str(turn.get("corrects_summary_id") or ""),
            "superseded_content_digests": list(turn.get("superseded_content_digests") or ()),
        }
        for turn in turns[-12:]
    ]
    message = str(history[-1].get("user_message") if history else "Inspect current context")
    prompt_history = history[:-1] if history else ()
    other_sessions = []
    for row in list_conversation_sessions(include_archived=False)[:24]:
        candidate_id = str(row.get("id") or "")
        if not candidate_id or candidate_id == session_id:
            continue
        loaded = load_conversation_session(candidate_id, include_turns=True)
        if loaded:
            other_sessions.append(loaded)

    packet = build_conversation_prompt(
        user_message=message,
        self_model={"name": "Eidolon"},
        desires={},
        memories=load_memories(limit=80),
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=prompt_history,
        current_session_id=session_id,
        cross_session_sessions=other_sessions,
        context_size=8192,
        max_tokens=512,
    )
    result = build_context_inspection_console(packet.metrics, session_id=session_id)
    result["session_found"] = bool(session)
    result["history_turn_count"] = len(history)
    return result
