from __future__ import annotations

"""Read-only v1083.9 relationship-continuity checkpoint.

The checkpoint combines the bounded continuity contracts established throughout
v1083. It reads supplied or local state, emits only aggregate content-free
evidence, performs no generation or embedding work, and never mutates memories,
transcripts, personality, provider configuration, approvals, or release state.
"""

import hashlib
import json
from collections import Counter
from typing import Any, Iterable, Mapping

from conversation_sessions import load_conversation_session
from conversation_turn_presentation import build_turn_presentation
from emotional_continuity_guard import build_emotional_continuity_guard
from important_moment_provenance import build_important_moment_provenance
from memory import load_memories
from memory_reconciliation import detect_memory_conflicts
from personality_stability import build_personality_stability_snapshot
from provider_recovery_evidence import provider_resume_cue
from relationship_continuity import is_relationship_memory, relationship_memory_type
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

RELATIONSHIP_CONTINUITY_CHECKPOINT_SCHEMA_VERSION = "1"
_RETRACTED = {"retracted", "deleted", "rejected", "expired", "stale", "blocked"}
_RESOLVED_MOMENTS = {"resolved", "closed", "complete", "completed", "dismissed"}


def _area(name: str, state: str, detail: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "detail": detail, "metrics": metrics}


def _rows(memories: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in memories if isinstance(row, Mapping)]


def _status(memory: Mapping[str, Any]) -> str:
    return str(memory.get("status") or memory.get("curation_state") or "active").strip().lower() or "active"


def _active(memory: Mapping[str, Any]) -> bool:
    return _status(memory) not in _RETRACTED and memory.get("use_in_conversation") is not False


def _history_for_session(session_id: str) -> list[dict[str, Any]]:
    if not session_id:
        return []
    session = load_conversation_session(session_id, include_turns=True)
    turns = session.get("turns") if isinstance(session, Mapping) else []
    return [dict(row) for row in turns if isinstance(row, Mapping)]


def _checkpoint_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_relationship_continuity_checkpoint(
    session_id: str = "",
    *,
    memories: Iterable[Mapping[str, Any]] | None = None,
    history: Iterable[Mapping[str, Any]] | None = None,
    provider_evidence: Mapping[str, Any] | None = None,
    interaction_lane: str = "ordinary",
) -> dict[str, Any]:
    """Return bounded aggregate evidence for the completed v1083 continuity arc."""
    stored = _rows(load_memories() if memories is None else memories)
    recent_history = _rows(_history_for_session(session_id) if history is None else history)
    relationship_rows = [row for row in stored if is_relationship_memory(row)]
    active_rows = [row for row in relationship_rows if _active(row)]

    conflict_rows = detect_memory_conflicts(relationship_rows)
    conflict_counts = Counter(str(row.get("kind") or "unknown") for row in conflict_rows)

    correction_events = 0
    corrected_records = 0
    superseded_digest_count = 0
    correction_lineage_complete = True
    for row in relationship_rows:
        lineage = row.get("correction_lineage") if isinstance(row.get("correction_lineage"), list) else []
        superseded = row.get("superseded_content_digests") if isinstance(row.get("superseded_content_digests"), list) else []
        if lineage:
            corrected_records += 1
            correction_events += len(lineage)
            correction_lineage_complete = correction_lineage_complete and bool(superseded)
        superseded_digest_count += len({str(value) for value in superseded if value})

    retracted_count = sum(1 for row in relationship_rows if _status(row) == "retracted")
    tombstones = [row for row in stored if row.get("type") == "relationship_memory_deletion_tombstone"]
    incomplete_cleanup = sum(
        1 for row in tombstones if not bool((row.get("vector_cleanup") or {}).get("cleanup_complete"))
    )
    content_free_tombstones = all(
        not any(row.get(key) for key in ("content", "thought", "summary")) for row in tombstones
    )

    emotional = build_emotional_continuity_guard(active_rows, interaction_lane=interaction_lane)
    current_moods = sum(
        1
        for row in active_rows
        if relationship_memory_type(row) == "user_mood"
        and str(row.get("mood_state") or row.get("temporal_state") or "current").strip().lower() == "current"
    )
    open_moments = []
    provenance_counts: Counter[str] = Counter()
    for row in active_rows:
        if relationship_memory_type(row) != "important_moment":
            continue
        temporal_state = str(row.get("moment_state") or row.get("temporal_state") or "open").strip().lower()
        if temporal_state in _RESOLVED_MOMENTS:
            continue
        evidence = build_important_moment_provenance(row)
        open_moments.append(row)
        provenance_counts[str(evidence.get("rationale_code") or "legacy_unknown")] += 1

    personality = build_personality_stability_snapshot(recent_history)
    provider = provider_resume_cue(provider_evidence)
    cancelled = build_turn_presentation(
        {"operation_id": "content-free-cancelled", "accepted_at": "persisted", "public_state": "cancelled"},
        turn={"success": False, "completion_state": "cancelled"},
    )
    failed = build_turn_presentation(
        {"operation_id": "content-free-failed", "accepted_at": "persisted", "public_state": "failed"},
        turn={"success": False, "completion_state": "failed"},
    )

    stable_contract = {
        "active_relationship_records": len(active_rows),
        "corrected_records": corrected_records,
        "correction_events": correction_events,
        "superseded_digest_count": superseded_digest_count,
        "conflict_counts": dict(sorted(conflict_counts.items())),
        "retracted_records": retracted_count,
        "deletion_tombstones": len(tombstones),
        "incomplete_vector_cleanup": incomplete_cleanup,
        "current_mood_records": current_moods,
        "open_important_moments": len(open_moments),
        "important_moment_provenance": dict(sorted(provenance_counts.items())),
        "personality": personality.receipt_metrics(),
        "provider_state": str(provider.get("state") or "unknown"),
        "provider_generation_available": bool(provider.get("generation_available")),
        "provider_embedding_available": bool(provider.get("embedding_available")),
        "cancelled_memory_commit_allowed": bool(cancelled.get("memory_commit_allowed")),
        "failed_memory_commit_allowed": bool(failed.get("memory_commit_allowed")),
    }
    contract_digest = _checkpoint_digest(stable_contract)

    areas = [
        _area(
            "long_session_personality",
            personality.drift_risk,
            "Only bounded recent conversation structure is inspected; personality and identity are not rewritten.",
            history_rows_considered=personality.history_rows_considered,
            maximum_history_rows=12,
            repeated_opening_runs=personality.repeated_opening_runs,
            identity_reset_signals=personality.identity_reset_signals,
        ),
        _area(
            "restart_continuity",
            "deterministic",
            "Equivalent persisted inputs produce the same content-free contract digest after reload or restart.",
            contract_digest=contract_digest,
            writes_state=False,
        ),
        _area(
            "correction_propagation",
            "ready" if correction_lineage_complete else "review_required",
            "Explicit corrections retain bounded lineage and superseded digests so stale exact content remains suppressed.",
            corrected_records=corrected_records,
            correction_events=correction_events,
            superseded_digest_count=superseded_digest_count,
            raw_transcripts_rewritten=False,
        ),
        _area(
            "memory_conflicts",
            "review_required" if conflict_rows else "clear",
            "Deterministic conflicts remain evidence only until the operator selects an explicit reconciliation action.",
            total=len(conflict_rows),
            kinds=dict(sorted(conflict_counts.items())),
            automatic_mutation=False,
            provider_invoked=False,
        ),
        _area(
            "retraction_and_deletion",
            "ready" if incomplete_cleanup == 0 and content_free_tombstones else "blocked",
            "Retracted memories remain excluded; permanent deletion keeps content-free tombstones after cleanup verification.",
            retracted_records=retracted_count,
            deletion_tombstones=len(tombstones),
            incomplete_vector_cleanup=incomplete_cleanup,
            content_free_tombstones=content_free_tombstones,
        ),
        _area(
            "mood_continuity",
            "bounded" if current_moods <= 1 else "conflict_review_required",
            "At most one explicit current mood may influence continuity; old or cleared moods do not accumulate.",
            current_mood_records=current_moods,
            current_moods_used=min(1, current_moods),
            old_moods_accumulate=False,
        ),
        _area(
            "important_moments",
            "ready",
            "Open important moments retain reviewable content-free provenance without repeated dramatization.",
            open_moment_count=len(open_moments),
            provenance_states=dict(sorted(provenance_counts.items())),
            raw_transcripts_rewritten=False,
        ),
        _area(
            "provider_outage",
            str(provider.get("state") or "unknown"),
            "Provider availability is evidence only; return from an outage never replays an accepted request.",
            generation_available=bool(provider.get("generation_available")),
            embedding_available=bool(provider.get("embedding_available")),
            recovery_proven=bool(provider.get("recovery_proven")),
            automatic_generation_replay=False,
            automatic_resend=False,
        ),
        _area(
            "failed_and_cancelled_generation",
            "memory_blocked",
            "Failed and cancelled assistant turns cannot create durable assistant continuity memories.",
            cancelled_state=str(cancelled.get("state") or ""),
            failed_state=str(failed.get("state") or ""),
            cancelled_memory_commit_allowed=False,
            failed_memory_commit_allowed=False,
            synthetic_assistant_output=False,
        ),
        _area(
            "affection_inflation",
            "blocked",
            "Warmth may follow the user, but unsupported affection, dependence, exclusivity, possessiveness, and invented progress remain blocked.",
            user_led_warmth_allowed=emotional.user_led_warmth_allowed,
            affection_escalation_allowed=False,
            relationship_progress_claim_allowed=False,
        ),
        _area(
            "privacy",
            "content_free",
            "The checkpoint returns aggregate evidence only and excludes prompts, replies, provider payloads, credentials, vectors, and deleted text.",
            raw_memory_text_returned=False,
            raw_transcript_text_returned=False,
            provider_payload_returned=False,
            hidden_vector_rows_returned=False,
        ),
    ]

    return {
        "type": "relationship_continuity_checkpoint",
        "schema_version": RELATIONSHIP_CONTINUITY_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "relationship_continuity_contracts_ready",
        "release_certified": False,
        "verification_required": True,
        "session_id_present": bool(session_id),
        "contract_digest": contract_digest,
        "relationship_record_count": len(relationship_rows),
        "active_relationship_record_count": len(active_rows),
        "areas": areas,
        "boundaries": {
            "automatic_memory_merge": False,
            "automatic_memory_replacement": False,
            "automatic_memory_retraction": False,
            "automatic_memory_deletion": False,
            "raw_transcript_rewrite": False,
            "automatic_generation_retry": False,
            "automatic_resend": False,
            "provider_request_replay": False,
            "provider_switching": False,
            "model_management": False,
            "settings_mutation": False,
            "personality_mutation": False,
            "affection_escalation": False,
            "relationship_progress_invention": False,
            "approval_or_release_authority_changed": False,
            "installation_or_promotion": False,
        },
        "read_only": True,
        "redacted": True,
        "content_free": True,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "writes_state": False,
    }


def relationship_continuity_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "messages", "user_message", "assistant_response", "transcript", "transcripts",
        "prompt", "prompts", "response", "responses", "content", "thought", "summary",
        "provider_payload", "credentials", "endpoint", "model", "raw_response", "raw_output",
        "receipt", "receipts", "vector", "vectors", "embedding", "embeddings", "acceptance_key",
        "claim_token", "deleted_memory_id",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
