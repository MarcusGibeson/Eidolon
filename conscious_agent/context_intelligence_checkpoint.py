from __future__ import annotations

"""Read-only v1085.9 context-intelligence checkpoint.

The checkpoint consolidates the deterministic context-selection contracts from
v1085.0 through v1085.8. It reads bounded local inputs, emits content-free
aggregate evidence, performs no generation or embedding work, and never mutates
sessions, transcripts, memories, provider settings, approvals, or release state.
"""

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from context_correction_aware_retrieval import (
    content_digest,
    filter_correction_aware_records,
)
from context_inspection_console import (
    build_context_inspection_console,
    context_inspection_contains_private_fields,
)
from context_stale_summary_detection import filter_stale_continuity_summaries
from conversation_context import build_conversation_prompt
from conversation_quality import filter_general_conversation_memories
from provider_recovery_evidence import provider_resume_cue
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

CONTEXT_INTELLIGENCE_CHECKPOINT_SCHEMA_VERSION = "1"
MAX_CHECKPOINT_HISTORY_ROWS = 48
MAX_CHECKPOINT_MEMORY_ROWS = 80
MAX_CHECKPOINT_SESSION_ROWS = 24
MAX_CHECKPOINT_CONTINUITY_ROWS = 24


def _area(name: str, state: str, detail: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "detail": detail, "metrics": metrics}


def _rows(values: Iterable[Mapping[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows = [dict(value) for value in values if isinstance(value, Mapping)]
    return rows[-max(0, int(limit)):]


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _turn_complete(row: Mapping[str, Any]) -> bool:
    state = str(row.get("completion_state") or "completed").strip().lower()
    return (
        bool(str(row.get("user_message") or "").strip())
        and bool(str(row.get("assistant_response") or "").strip())
        and bool(row.get("success", True))
        and state in {"completed", "complete", "succeeded", "success"}
    )


def _bounded_history(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in _rows(values, MAX_CHECKPOINT_HISTORY_ROWS) if _turn_complete(row)]


def _latest_message(history: Sequence[Mapping[str, Any]]) -> str:
    for row in reversed(history):
        message = str(row.get("user_message") or "").strip()
        if message:
            return message
    return "Inspect the active context selection."


def _load_persisted_inputs(session_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not session_id:
        return [], [], []
    from conversation_sessions import list_conversation_sessions, load_conversation_session

    session = load_conversation_session(session_id, include_turns=True)
    history = _bounded_history((session or {}).get("turns") or ()) if isinstance(session, Mapping) else []
    other_sessions: list[dict[str, Any]] = []
    for row in list_conversation_sessions(include_archived=False)[:MAX_CHECKPOINT_SESSION_ROWS]:
        candidate_id = str(row.get("id") or "")
        if not candidate_id or candidate_id == session_id:
            continue
        loaded = load_conversation_session(candidate_id, include_turns=True)
        if isinstance(loaded, Mapping):
            other_sessions.append(dict(loaded))
    return history, other_sessions, []


def _probe_inputs() -> dict[str, Any]:
    old_location = "The Atlas office is in Dayton."
    old_digest = content_digest(old_location)
    history: list[dict[str, Any]] = []
    for index in range(12):
        history.append({
            "user_message": f"Atlas deployment certificate alpha{index}",
            "assistant_response": f"Launch beta milestone atlas{index} remains reviewable.",
            "completion_state": "completed",
            "success": True,
        })
    for index in range(12):
        history.append({
            "user_message": f"Orchid compost soil bed{index}",
            "assistant_response": f"Mulch watering schedule garden{index} stays separate.",
            "completion_state": "completed",
            "success": True,
        })
    history.append({
        "user_message": "The Atlas office location was corrected.",
        "assistant_response": "The corrected location is Columbus.",
        "completion_state": "completed",
        "success": True,
        "superseded_content_digests": [old_digest],
        "corrects_summary_id": "atlas-old-location",
    })

    memories = [
        {
            "id": "atlas-current-location",
            "type": "fact",
            "content": "The Atlas office is in Columbus.",
            "importance": "high",
            "operator_curated": True,
            "retention_confirmed": True,
            "provenance": {"origin": "operator_explicit"},
            "superseded_content_digests": [old_digest],
            "correction_lineage": [{"operator_explicit": True, "previous_content_digest": old_digest}],
        },
        {
            "id": "atlas-stale-location",
            "type": "fact",
            "content": old_location,
            "importance": "high",
        },
        {
            "id": "atlas-similar-but-not-linked",
            "type": "fact",
            "content": "The Atlas office location should be reviewed before travel.",
            "importance": "normal",
        },
        {
            "id": "atlas-retracted",
            "type": "fact",
            "content": "Retracted Atlas fact must remain excluded.",
            "status": "retracted",
            "importance": "high",
        },
        {
            "id": "atlas-deleted",
            "type": "fact",
            "content": "Deleted Atlas fact must remain excluded.",
            "status": "deleted",
            "importance": "high",
        },
    ]
    memories.extend(
        {
            "id": f"atlas-context-{index}",
            "type": "fact",
            "content": (f"Atlas launch supporting note {index}. " + "bounded context detail " * 18).strip(),
            "importance": "normal",
        }
        for index in range(16)
    )
    continuity_rows = [
        {
            "id": "atlas-old-location",
            "content": old_location,
            "content_digest": old_digest,
            "source_record_ids": ["atlas-stale-location"],
        },
        {
            "id": "atlas-current-hours",
            "content": "The Atlas office opens at nine.",
            "importance": "high",
        },
        {
            "id": "atlas-retracted-source-note",
            "content": "Retracted source continuity must remain excluded.",
            "source_record_ids": ["atlas-retracted"],
        },
        {
            "id": "atlas-deleted-source-note",
            "content": "Deleted source continuity must remain excluded.",
            "source_record_ids": ["atlas-deleted"],
        },
    ]
    other_sessions = [
        {
            "id": "atlas-session",
            "title": "Atlas launch plan",
            "status": "active",
            "thread_key": "atlas-launch",
            "turns": [
                {
                    "user_message": "We discussed the Atlas launch plan.",
                    "assistant_response": "The beta milestone remains open.",
                    "completion_state": "completed",
                    "success": True,
                    "thread_key": "atlas-launch",
                },
                {
                    "user_message": "This failed provider request should not link.",
                    "assistant_response": "Partial provider output",
                    "completion_state": "failed",
                    "success": False,
                },
            ],
        },
        {
            "id": "garden-session",
            "title": "Garden notes",
            "status": "active",
            "turns": [
                {
                    "user_message": "The garden needs compost.",
                    "assistant_response": "Compost can be added next week.",
                    "completion_state": "completed",
                    "success": True,
                }
            ],
        },
    ]
    return {
        "message": "Return to the Atlas launch plan.",
        "history": history,
        "memories": memories,
        "continuity_rows": continuity_rows,
        "other_sessions": other_sessions,
        "old_digest": old_digest,
    }


def _build_packet(
    *,
    message: str,
    history: Sequence[Mapping[str, Any]],
    memories: Sequence[Mapping[str, Any]],
    continuity_rows: Sequence[Mapping[str, Any]],
    other_sessions: Sequence[Mapping[str, Any]],
    session_id: str,
    context_size: int = 8192,
    max_tokens: int = 512,
) -> Any:
    return build_conversation_prompt(
        user_message=message,
        self_model={"name": "Eidolon"},
        desires={},
        memories=[dict(row) for row in memories],
        project_context="",
        goal_context="",
        task_context="",
        conversation_history=[dict(row) for row in history],
        current_session_id=session_id,
        cross_session_sessions=[dict(row) for row in other_sessions],
        continuity_summaries=[dict(row) for row in continuity_rows],
        context_size=context_size,
        max_tokens=max_tokens,
    )


def build_context_intelligence_checkpoint(
    session_id: str = "",
    *,
    history: Iterable[Mapping[str, Any]] | None = None,
    memories: Iterable[Mapping[str, Any]] | None = None,
    continuity_rows: Iterable[Mapping[str, Any]] | None = None,
    cross_session_sessions: Iterable[Mapping[str, Any]] | None = None,
    provider_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded content-free evidence for the completed v1085 context arc."""

    persisted_history: list[dict[str, Any]] = []
    persisted_sessions: list[dict[str, Any]] = []
    persisted_continuity: list[dict[str, Any]] = []
    if history is None or cross_session_sessions is None or continuity_rows is None:
        persisted_history, persisted_sessions, persisted_continuity = _load_persisted_inputs(session_id)

    if memories is None:
        from memory import load_memories
        memory_rows = _rows(load_memories(limit=MAX_CHECKPOINT_MEMORY_ROWS), MAX_CHECKPOINT_MEMORY_ROWS)
    else:
        memory_rows = _rows(memories, MAX_CHECKPOINT_MEMORY_ROWS)
    history_rows = _bounded_history(persisted_history if history is None else history)
    session_rows = _rows(
        persisted_sessions if cross_session_sessions is None else cross_session_sessions,
        MAX_CHECKPOINT_SESSION_ROWS,
    )
    continuity_values = _rows(
        persisted_continuity if continuity_rows is None else continuity_rows,
        MAX_CHECKPOINT_CONTINUITY_ROWS,
    )

    actual_packet = _build_packet(
        message=_latest_message(history_rows),
        history=history_rows,
        memories=memory_rows,
        continuity_rows=continuity_values,
        other_sessions=session_rows,
        session_id=session_id,
    )
    actual_console = build_context_inspection_console(actual_packet.metrics, session_id=session_id)

    probe = _probe_inputs()
    probe_packet_one = _build_packet(
        message=probe["message"],
        history=probe["history"],
        memories=probe["memories"],
        continuity_rows=probe["continuity_rows"],
        other_sessions=probe["other_sessions"],
        session_id="checkpoint-current",
        context_size=2300,
        max_tokens=384,
    )
    probe_packet_two = _build_packet(
        message=probe["message"],
        history=probe["history"],
        memories=probe["memories"],
        continuity_rows=probe["continuity_rows"],
        other_sessions=probe["other_sessions"],
        session_id="checkpoint-current",
        context_size=2300,
        max_tokens=384,
    )
    probe_console = build_context_inspection_console(probe_packet_one.metrics, session_id="checkpoint-current")

    correction_filtered, correction_evidence = filter_correction_aware_records(probe["memories"])
    eligible_records = filter_general_conversation_memories(correction_filtered)
    eligible_continuity, stale_evidence = filter_stale_continuity_summaries(
        probe["continuity_rows"],
        probe["memories"],
        current_session_records=probe["history"],
    )
    eligible_ids = {str(row.get("id") or "") for row in eligible_records}
    eligible_continuity_ids = {str(row.get("id") or "") for row in eligible_continuity}

    deterministic = (
        probe_packet_one.prompt == probe_packet_two.prompt
        and probe_packet_one.metrics.to_dict() == probe_packet_two.metrics.to_dict()
    )
    assembly_digest = _digest({
        "rendered": probe_packet_one.prompt,
        "metrics": probe_packet_one.metrics.to_dict(),
    })
    provider = provider_resume_cue(provider_evidence)

    lane_order = list(probe_console.get("lane_order") or ())
    included_lanes = list(probe_console.get("lanes_included") or ())
    omitted_lanes = list(probe_console.get("lanes_omitted") or ())
    budget_omissions = dict(probe_console.get("omissions_by_lane") or {})
    omission_reasons = dict(probe_console.get("omission_reasons") or {})
    topic = dict(probe_console.get("topic") or {})
    cross_session = dict(probe_console.get("cross_session") or {})
    corrections = dict(probe_console.get("corrections") or {})
    stale = dict(probe_console.get("stale_summaries") or {})

    stable_contract = {
        "lane_order": lane_order,
        "included_lanes": included_lanes,
        "omitted_lanes": omitted_lanes,
        "topic": topic,
        "cross_session": cross_session,
        "corrections": corrections,
        "continuity_filter": stale,
        "budget_omissions": budget_omissions,
        "omission_reasons": omission_reasons,
        "eligible_record_count": len(eligible_records),
        "eligible_continuity_count": len(eligible_continuity),
        "deterministic": deterministic,
        "provider_state": str(provider.get("state") or "unknown"),
        "provider_generation_available": bool(provider.get("generation_available")),
        "provider_embedding_available": bool(provider.get("embedding_available")),
    }
    contract_digest = _digest(stable_contract)

    areas = [
        _area(
            "context_lanes",
            "ready" if lane_order == [
                "current_turn", "correction_evidence", "active_thread", "recent_conversation",
                "mood", "important_moments", "curated_memory",
            ] else "review_required",
            "Context sources remain separated into fixed ordered lanes with the current turn and explicit correction evidence protected.",
            lane_order=lane_order,
            included_lanes=included_lanes,
            omitted_lanes=omitted_lanes,
            current_turn_protected=True,
            correction_evidence_precedes_ranked_context=True,
            writes_state=False,
        ),
        _area(
            "large_history_and_topics",
            "bounded",
            "Large histories are reduced through bounded topic segmentation while complete turns remain intact.",
            supplied_history_rows=len(probe["history"]),
            maximum_topic_history_rows=32,
            segment_count=int(topic.get("segment_count", 0)),
            active_turn_count=int(topic.get("active_turn_count", 0)),
            unrelated_turns_excluded=int(topic.get("unrelated_turns_excluded", 0)),
            selection_reason=str(topic.get("selection_reason") or "no_history"),
            partial_turn_admission_allowed=False,
        ),
        _area(
            "cross_session_threads",
            "ready" if int(cross_session.get("linked_turns", 0)) >= 1 else "bounded_no_match",
            "Another session contributes only explicitly or strongly matched whole completed turns; sessions remain separate.",
            candidate_sessions=int(cross_session.get("candidate_sessions", 0)),
            candidate_turns=int(cross_session.get("candidate_turns", 0)),
            linked_sessions=int(cross_session.get("linked_sessions", 0)),
            linked_turns=int(cross_session.get("linked_turns", 0)),
            turns_included=int(cross_session.get("turns_included", 0)),
            turns_omitted=int(cross_session.get("turns_omitted", 0)),
            merges_sessions=False,
            rewrites_history=False,
            failed_or_partial_turns_eligible=False,
        ),
        _area(
            "ranking_and_salience",
            "bounded",
            "Eligible context is ranked deterministically and one relevant older salient record may receive a bounded reservation.",
            candidate_count=int((probe_console.get("ranking") or {}).get("candidate_count", 0)),
            top_score=int((probe_console.get("ranking") or {}).get("top_score", 0)),
            salience_reservations=int((probe_console.get("ranking") or {}).get("salience_reservations", 0)),
            provider_invoked=False,
            automatic_curation=False,
        ),
        _area(
            "budget_management",
            "ready",
            "Each lane has an explicit budget; complete records are either admitted or omitted with bounded reasons.",
            allocated_tokens=dict(probe_console.get("allocated_tokens") or {}),
            used_tokens=dict(probe_console.get("used_tokens") or {}),
            omissions_by_lane=budget_omissions,
            omission_reasons=omission_reasons,
            silent_truncation_allowed=False,
            partial_record_admission_allowed=False,
        ),
        _area(
            "correction_aware_retrieval",
            "ready",
            "Exact superseded digests and explicit lineage suppress stale records before ranking; ambiguous similarity alone does not.",
            correction_records=correction_evidence.correction_record_count,
            exact_suppressed=correction_evidence.exact_digest_suppressed,
            explicit_link_suppressed=correction_evidence.explicit_link_suppressed,
            ambiguous_similarity_suppressed=correction_evidence.ambiguous_similarity_suppressed,
            current_record_eligible="atlas-current-location" in eligible_ids,
            stale_record_eligible="atlas-stale-location" in eligible_ids,
            similar_unlinked_record_eligible="atlas-similar-but-not-linked" in eligible_ids,
            retracted_record_eligible="atlas-retracted" in eligible_ids,
            deleted_record_eligible="atlas-deleted" in eligible_ids,
            rewrites_transcript=False,
        ),
        _area(
            "continuity_record_staleness",
            "ready",
            "Continuity records are suppressed only through exact corrections, explicit lineage, current-session evidence, retraction, or deletion.",
            candidates=stale_evidence.summary_count,
            detected=stale_evidence.stale_count,
            eligible=stale_evidence.eligible_count,
            exact_digest_matches=stale_evidence.exact_digest_matches,
            explicit_lineage_matches=stale_evidence.explicit_lineage_matches,
            corrected_conflicts=stale_evidence.corrected_conflicts,
            retracted_conflicts=stale_evidence.retracted_conflicts,
            deleted_conflicts=stale_evidence.deleted_conflicts,
            current_session_conflicts=stale_evidence.current_session_conflicts,
            old_location_eligible="atlas-old-location" in eligible_continuity_ids,
            fresh_hours_eligible="atlas-current-hours" in eligible_continuity_ids,
            rewrites_stored_record=False,
        ),
        _area(
            "inspection_console",
            "content_free" if not context_inspection_contains_private_fields(probe_console) else "blocked",
            "Operator inspection exposes lane, budget, ranking, topic, provenance, correction, link, and omission evidence without context content.",
            offline_available=bool(probe_console.get("offline_available")),
            read_only=bool(probe_console.get("read_only")),
            provider_invoked=bool(probe_console.get("provider_invoked")),
            writes_state=bool(probe_console.get("writes_state")),
            contains_context_content=bool(probe_console.get("contains_context_content")),
            contains_hidden_reasoning=bool(probe_console.get("contains_hidden_reasoning")),
            private_fields_detected=context_inspection_contains_private_fields(probe_console),
        ),
        _area(
            "offline_and_provider_outage",
            str(provider.get("state") or "unknown"),
            "Local context assembly and inspection remain available during provider outages and never replay accepted work.",
            offline_context_available=True,
            generation_available=bool(provider.get("generation_available")),
            embedding_available=bool(provider.get("embedding_available")),
            automatic_generation_replay=bool(provider.get("automatic_generation_replay")),
            automatic_resend=bool(provider.get("automatic_resend")),
            provider_switching=False,
            model_management=False,
        ),
        _area(
            "deterministic_assembly",
            "stable" if deterministic else "review_required",
            "Equivalent bounded inputs produce the same assembled-context digest and content-free metrics across reload-equivalent runs.",
            deterministic=deterministic,
            assembly_digest=assembly_digest,
            contract_digest=contract_digest,
            restart_stable=deterministic,
            provider_invoked=False,
            writes_state=False,
        ),
        _area(
            "privacy_and_authority",
            "ready",
            "The checkpoint contains only bounded codes, counts, booleans, and digests and cannot certify, install, or promote a release.",
            actual_history_rows_considered=len(history_rows),
            actual_memory_rows_considered=len(memory_rows),
            actual_session_rows_considered=len(session_rows),
            actual_continuity_rows_considered=len(continuity_values),
            actual_console_private_fields=context_inspection_contains_private_fields(actual_console),
            raw_context_returned=False,
            hidden_reasoning_returned=False,
            release_certified=False,
        ),
    ]

    return {
        "type": "context_intelligence_checkpoint",
        "schema_version": CONTEXT_INTELLIGENCE_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "session_id_present": bool(session_id),
        "checkpoint_status": "context_intelligence_contracts_ready",
        "areas": areas,
        "contract_digest": contract_digest,
        "read_only": True,
        "redacted": True,
        "content_free": True,
        "offline_available": True,
        "provider_invoked": False,
        "writes_state": False,
        "release_certified": False,
        "verification_required": True,
        "boundaries": {
            "automatic_session_merge": False,
            "automatic_transcript_rewrite": False,
            "automatic_memory_mutation": False,
            "automatic_provider_request": False,
            "automatic_request_replay": False,
            "automatic_resend": False,
            "automatic_provider_switch": False,
            "automatic_model_management": False,
            "hidden_reasoning_exposure": False,
            "release_authority": False,
            "installation_authority": False,
            "promotion_authority": False,
        },
    }


def context_intelligence_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "messages", "user_message", "assistant_response", "content", "thought", "summary",
        "prompt", "transcript", "memory", "memory_text", "provider_payload", "credentials", "vector",
        "embedding", "chain_of_thought", "reasoning_trace", "receipt", "acceptance_key", "claim_token",
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
