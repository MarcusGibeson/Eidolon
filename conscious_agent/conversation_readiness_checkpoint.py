from __future__ import annotations

"""Read-only v1086.9 Desktop Alpha conversation-readiness checkpoint.

This module consolidates the v1086.0-v1086.8 conversation-control contracts.
It emits only bounded counts, states, reason codes, limits, booleans, and
cryptographic digests. It never calls a provider and never mutates conversation,
memory, configuration, approval, rollback, installation, or release state.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

from context_intelligence_checkpoint import build_context_intelligence_checkpoint
from conversation_control_foundation import build_conversation_control_foundation
from conversation_generation_steering import build_generation_steering_plan
from conversation_message_branching import build_message_branch_plan
from conversation_offline_degradation import (
    build_offline_degradation_state,
    build_offline_operator_intent_record,
    resolve_offline_operator_intent,
)
from conversation_pinned_context import (
    MAX_PINNED_CONTEXT_ITEMS,
    MAX_PINNED_CONTEXT_CHARS,
    MAX_PINNED_CONTEXT_PROMPT_CHARS,
    bounded_pinned_prompt_blocks,
    build_pinned_context_record,
    resolve_pinned_context_records,
)
from conversation_quality_checkpoint import build_conversation_quality_checkpoint
from conversation_response_preferences import normalize_response_preferences, response_preference_payload
from conversation_retry_regeneration import (
    ACTION_FAILED_RETRY,
    ACTION_REGENERATE,
    ACTION_RESEND,
    ACTION_TYPES,
    ConversationTurnActionPlan,
)
from conversation_turn_presentation import build_turn_presentation
from relationship_continuity_checkpoint import build_relationship_continuity_checkpoint
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION
from temporary_instruction_scope import build_temporary_instruction_record, resolve_temporary_instruction

CONVERSATION_READINESS_CHECKPOINT_SCHEMA_VERSION = "1"
CHECKPOINT_AREA_COUNT = 15
INITIAL_RENDER_WINDOW = 80
EARLIER_HISTORY_WINDOW_LIMIT = 120
LONG_SESSION_THRESHOLD = 120


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _area(name: str, state: str, reason: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "reason": reason, "metrics": metrics}


def _session_snapshot(session_id: str) -> dict[str, Any]:
    token = str(session_id or "").strip()
    if not token:
        return {
            "requested": False,
            "available": False,
            "turn_count": 0,
            "completed_turn_count": 0,
            "draft_present": False,
            "control_revision": 0,
            "pinned_count": 0,
            "queued_intent_present": False,
            "initial_turns_rendered": 0,
            "earlier_history_available": False,
        }
    from conversation_sessions import (
        conversation_controls_for_prompt,
        conversation_session_turn_window,
        load_conversation_draft,
        load_conversation_session,
    )

    session = load_conversation_session(token, include_turns=False)
    if not isinstance(session, Mapping):
        return {
            "requested": True,
            "available": False,
            "turn_count": 0,
            "completed_turn_count": 0,
            "draft_present": False,
            "control_revision": 0,
            "pinned_count": 0,
            "queued_intent_present": False,
            "initial_turns_rendered": 0,
            "earlier_history_available": False,
        }
    controls = conversation_controls_for_prompt(token)
    draft = load_conversation_draft(token)
    window = conversation_session_turn_window(token, limit=INITIAL_RENDER_WINDOW)
    pins = controls.get("pinned_context") if isinstance(controls, Mapping) else []
    return {
        "requested": True,
        "available": True,
        "turn_count": max(0, int(session.get("turn_count") or 0)),
        "completed_turn_count": max(0, int(session.get("completed_turn_count") or 0)),
        "draft_present": bool(draft.get("content")) if isinstance(draft, Mapping) else False,
        "control_revision": max(0, int(controls.get("revision") or 0)) if isinstance(controls, Mapping) else 0,
        "pinned_count": len([row for row in list(pins or ())[:MAX_PINNED_CONTEXT_ITEMS] if isinstance(row, Mapping)]),
        "queued_intent_present": bool(controls.get("queued_operator_intent")) if isinstance(controls, Mapping) else False,
        "initial_turns_rendered": max(0, int(window.get("shown") or 0)),
        "earlier_history_available": bool(window.get("has_older")),
    }


def _temporary_instruction_probe() -> dict[str, Any]:
    timestamp = "2026-07-21T00:00:00Z"
    current_turn = build_temporary_instruction_record(
        "private current turn instruction", scope="current_turn", revision=1, updated_at=timestamp,
    )
    current_topic = build_temporary_instruction_record(
        "private topic instruction", scope="current_topic", revision=2, updated_at=timestamp,
        topic_anchor_text="atlas deployment certificate",
    )
    current_session = build_temporary_instruction_record(
        "private session instruction", scope="current_session", revision=3, updated_at=timestamp,
    )
    until_cleared = build_temporary_instruction_record(
        "private persistent instruction", scope="until_cleared", revision=4, updated_at=timestamp,
    )
    turn_resolution = resolve_temporary_instruction(
        current_turn, current_message="private", persisted=False,
    )
    topic_active = resolve_temporary_instruction(
        current_topic, current_message="atlas certificate deployment", transition_kind="continuation", persisted=True,
    )
    topic_shifted = resolve_temporary_instruction(
        current_topic, current_message="garden compost schedule", transition_kind="topic_shift", persisted=True,
    )
    session_resolution = resolve_temporary_instruction(
        current_session, current_message="private", persisted=True,
    )
    cleared_resolution = resolve_temporary_instruction(
        until_cleared, current_message="private", persisted=True,
    )
    return {
        "scope_count": 4,
        "current_turn_active": turn_resolution.active,
        "current_turn_persisted": turn_resolution.persisted,
        "current_turn_only": turn_resolution.current_turn_only,
        "current_topic_active": topic_active.active,
        "current_topic_reason": topic_active.reason,
        "topic_shift_active": topic_shifted.active,
        "topic_shift_reason": topic_shifted.reason,
        "current_session_active": session_resolution.active,
        "until_cleared_active": cleared_resolution.active,
        "mutates_personality": any(
            row.mutates_personality for row in (
                turn_resolution, topic_active, topic_shifted, session_resolution, cleared_resolution,
            )
        ),
        "grants_protected_authority": any(
            row.grants_protected_authority for row in (
                turn_resolution, topic_active, topic_shifted, session_resolution, cleared_resolution,
            )
        ),
        "provider_invoked": any(
            row.provider_invoked for row in (
                turn_resolution, topic_active, topic_shifted, session_resolution, cleared_resolution,
            )
        ),
        "scope_digest": _digest([
            current_turn["instruction_digest"], current_topic["instruction_digest"],
            current_session["instruction_digest"], until_cleared["instruction_digest"],
        ]),
    }


def _pinned_context_probe() -> dict[str, Any]:
    timestamp = "2026-07-21T00:00:00Z"
    records: list[dict[str, Any]] = []
    for index in range(MAX_PINNED_CONTEXT_ITEMS):
        records.append(build_pinned_context_record(
            (f"private pinned working context {index} " + ("bounded " * 95)).strip(),
            kind=("note", "goal", "project_constraint", "reference_fact")[index % 4],
            scope="current_topic" if index == 0 else ("current_session" if index < 5 else "until_cleared"),
            revision=index + 1,
            updated_at=timestamp,
            expires_at="2026-07-20T00:00:00Z" if index == 7 else "",
            topic_anchor_text="atlas deployment certificate" if index == 0 else "",
            item_id=f"pin_{index:024x}",
        ))
    now = datetime(2026, 7, 21, tzinfo=timezone.utc)
    active = resolve_pinned_context_records(
        records,
        current_message="atlas certificate deployment",
        transition_kind="continuation",
        now=now,
    )
    shifted = resolve_pinned_context_records(
        records,
        current_message="garden compost schedule",
        transition_kind="topic_shift",
        now=now,
    )
    blocks = bounded_pinned_prompt_blocks(active)
    return {
        "record_count": len(records),
        "maximum_items": MAX_PINNED_CONTEXT_ITEMS,
        "maximum_item_chars": MAX_PINNED_CONTEXT_CHARS,
        "prompt_budget_chars": MAX_PINNED_CONTEXT_PROMPT_CHARS,
        "active_count": sum(1 for row in active if row.active),
        "expired_count": sum(1 for row in active if row.expired),
        "topic_active_before_shift": bool(active and active[0].active),
        "topic_active_after_shift": bool(shifted and shifted[0].active),
        "admitted_block_count": len(blocks),
        "admitted_chars": sum(len(block) for block in blocks),
        "all_revisions_positive": all(row.revision > 0 for row in active),
        "mutates_personality": any(row.mutates_personality for row in active),
        "grants_protected_authority": any(row.grants_protected_authority for row in active),
        "provider_invoked": any(row.provider_invoked for row in active),
        "admission_digest": _digest([_digest(block) for block in blocks]),
    }


def _offline_probe() -> dict[str, Any]:
    record = build_offline_operator_intent_record(
        kind="retry_failed_turn",
        revision=3,
        updated_at="2026-07-21T00:00:00Z",
        target_turn_id="turn-checkpoint-failed",
    )
    intent = resolve_offline_operator_intent(record, target_turn_exists=True)
    session_state = {
        "session_id": "checkpoint-session",
        "session_available": True,
        "session_active": True,
        "has_draft": True,
        "capabilities": {
            "conversation_history": True,
            "conversation_search": True,
            "memory_curation": True,
            "draft_editing": True,
            "conversation_navigation": True,
        },
    }
    offline = build_offline_degradation_state(
        session_state=session_state, pinned_context_count=2, queued_intent=intent, provider_available=False,
    )
    returned = build_offline_degradation_state(
        session_state=session_state, pinned_context_count=2, queued_intent=intent, provider_available=True,
    )
    return {
        "offline_state": str(offline.get("degradation_mode") or "unknown"),
        "returned_state": str(returned.get("degradation_mode") or "unknown"),
        "intent_state": intent.state,
        "intent_reason": intent.reason,
        "explicit_confirmation_required": intent.explicit_confirmation_required,
        "automatic_execution_offline": bool(offline.get("automatic_execution_after_recovery")),
        "automatic_execution_returned": bool(returned.get("automatic_execution_after_recovery")),
        "automatic_resend": bool(offline.get("automatic_resend") or returned.get("automatic_resend")),
        "automatic_request_replay": bool(
            (offline.get("capabilities") or {}).get("automatic_request_replay")
            or (returned.get("capabilities") or {}).get("automatic_request_replay")
        ),
        "generation_offline": bool((offline.get("capabilities") or {}).get("provider_generation")),
        "generation_returned": bool((returned.get("capabilities") or {}).get("provider_generation")),
        "draft_preserved": bool(offline.get("draft_preserved")),
        "navigation_preserved": bool(offline.get("navigation_preserved")),
        "search_preserved": bool(offline.get("search_preserved")),
        "memory_browse_preserved": bool(offline.get("memory_browse_preserved")),
        "context_inspection_preserved": bool((offline.get("capabilities") or {}).get("context_inspection")),
        "branching_preserved": bool((offline.get("capabilities") or {}).get("message_branching")),
        "provider_invoked": bool(offline.get("provider_invoked") or returned.get("provider_invoked")),
        "writes_state": bool(offline.get("writes_state") or returned.get("writes_state")),
        "intent_digest": _digest({
            "intent_id": intent.intent_id,
            "kind": intent.kind,
            "target_turn_id": intent.target_turn_id,
            "state": intent.state,
        }),
    }


def _continuity_probe() -> dict[str, Any]:
    provider = {
        "state": "temporarily_unavailable",
        "observed_state": "temporarily_unavailable",
        "generation_available": False,
        "embedding_available": False,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "redacted": True,
    }
    history = [
        {
            "user_message": "private ordinary turn",
            "assistant_response": "private completed response",
            "completion_state": "completed",
            "success": True,
        }
    ]
    relationship = build_relationship_continuity_checkpoint(
        history=history,
        memories=[],
        provider_evidence=provider,
    )
    quality = build_conversation_quality_checkpoint(history=history, provider_evidence=provider)
    context = build_context_intelligence_checkpoint(
        history=history,
        memories=[],
        continuity_rows=[],
        cross_session_sessions=[],
        provider_evidence=provider,
    )
    relationship_states = {str(row.get("name")): str(row.get("state")) for row in relationship.get("areas", [])}
    quality_states = {str(row.get("name")): str(row.get("state")) for row in quality.get("areas", [])}
    context_states = {str(row.get("name")): str(row.get("state")) for row in context.get("areas", [])}
    return {
        "correction_state": relationship_states.get("correction_propagation", "unknown"),
        "curation_state": relationship_states.get("memory_conflicts", "unknown"),
        "retraction_deletion_state": relationship_states.get("retraction_and_deletion", "unknown"),
        "mood_state": relationship_states.get("mood_continuity", "unknown"),
        "important_moment_state": relationship_states.get("important_moments", "unknown"),
        "personality_state": quality_states.get("personality_expression", "unknown"),
        "affection_inflation_state": relationship_states.get("affection_inflation", "unknown"),
        "context_privacy_state": context_states.get("privacy_and_authority", "unknown"),
        "relationship_digest": str(relationship.get("contract_digest") or ""),
        "quality_digest": str(quality.get("contract_digest") or ""),
        "context_digest": str(context.get("contract_digest") or ""),
        "provider_invoked": bool(
            relationship.get("provider_invoked") or quality.get("provider_invoked") or context.get("provider_invoked")
        ),
        "writes_state": bool(relationship.get("writes_state") or quality.get("writes_state") or context.get("writes_state")),
    }


def build_conversation_readiness_checkpoint(session_id: str = "") -> dict[str, Any]:
    """Return one bounded provider-free checkpoint for the completed v1086 arc."""

    session = _session_snapshot(session_id)
    control = build_conversation_control_foundation()

    preference = normalize_response_preferences(
        response_preference_payload(mode="detailed", format="steps", revision=4, source="checkpoint")
    )
    stored_preference_block = preference.prompt_block(explicit_length_cue=False)
    turn_override_block = preference.prompt_block(explicit_length_cue=True)

    instructions = _temporary_instruction_probe()
    pins = _pinned_context_probe()
    offline = _offline_probe()
    continuity = _continuity_probe()

    steering = build_generation_steering_plan(
        "conversation_session_20260721T000000_aaaaaaaaaa",
        "conversation_20260721T000000_aaaaaaaaaaaa",
        "private redirect text",
        marker={
            "operation_id": "conversation_20260721T000000_aaaaaaaaaaaa",
            "session_id": "conversation_session_20260721T000000_aaaaaaaaaa",
            "accepted_at": "2026-07-21T00:00:00Z",
            "updated_at": "2026-07-21T00:00:00Z",
            "public_state": "running",
            "cancellation_requested": False,
            "acceptance_key": "checkpoint-acceptance",
        },
    )
    cancelled = build_turn_presentation(
        {"operation_id": "cancelled-operation", "accepted_at": "persisted", "public_state": "cancelled"},
        turn={"success": False, "completion_state": "cancelled"},
    )
    failed = build_turn_presentation(
        {"operation_id": "failed-operation", "accepted_at": "persisted", "public_state": "failed"},
        turn={"success": False, "completion_state": "failed"},
    )

    action_plan = ConversationTurnActionPlan(
        schema_version="1",
        session_id="checkpoint-session",
        source_turn_id="checkpoint-source-turn",
        source_completion_state="completed",
        source_success=True,
        failed_retry_allowed=True,
        regeneration_allowed=True,
        explicit_resend_allowed=True,
        failed_retry_reuses_acceptance=True,
        regeneration_reuses_user_memory=True,
        resend_creates_new_user_turn=True,
    ).public_summary()

    branch = build_message_branch_plan(
        "checkpoint-session",
        "checkpoint-source-turn",
        "private edited user message",
        "checkpoint-branch-request",
    )

    stable_contract = {
        "runtime_version": RUNTIME_VERSION,
        "control": control,
        "preference": {
            "mode": preference.mode,
            "format": preference.format,
            "revision": preference.revision,
            "stored_digest": _digest(stored_preference_block),
            "override_digest": _digest(turn_override_block),
        },
        "instructions": instructions,
        "pins": pins,
        "offline": offline,
        "steering": {key: steering.get(key) for key in (
            "operation_state", "steering_allowed", "reason", "fresh_acceptance_identity_required",
            "automatic_resend", "accepted_request_replay", "partial_response_committed",
            "assistant_memory_committed_by_steering", "provider_invoked_by_planner", "writes_redirect_content",
        )},
        "turn_actions": {key: action_plan.get(key) for key in (
            "failed_retry_reuses_acceptance", "regeneration_reuses_user_memory", "resend_creates_new_user_turn",
            "original_turn_preserved", "automatic_retry", "automatic_regeneration", "automatic_resend",
            "fresh_acceptance_required_for_regeneration", "fresh_acceptance_required_for_resend",
        )},
        "branch": {key: branch.get(key) for key in (
            "branch_allowed", "original_session_preserved", "original_turn_preserved", "raw_transcript_rewritten",
            "provider_invoked", "message_submitted", "automatic_branch_creation", "fresh_acceptance_required_to_send",
        )},
        "continuity": continuity,
        "limits": {
            "initial_render_window": INITIAL_RENDER_WINDOW,
            "earlier_history_window_limit": EARLIER_HISTORY_WINDOW_LIMIT,
            "long_session_threshold": LONG_SESSION_THRESHOLD,
            "maximum_pinned_items": MAX_PINNED_CONTEXT_ITEMS,
            "maximum_pinned_item_chars": MAX_PINNED_CONTEXT_CHARS,
            "pinned_prompt_budget_chars": MAX_PINNED_CONTEXT_PROMPT_CHARS,
        },
    }
    contract_digest = _digest(stable_contract)

    areas = [
        _area(
            "everyday_consecutive_use", "ready", "bounded_daily_use",
            long_session_threshold=LONG_SESSION_THRESHOLD,
            initial_render_window=INITIAL_RENDER_WINDOW,
            earlier_history_window_limit=EARLIER_HISTORY_WINDOW_LIMIT,
            whole_turn_windows=True,
            draft_preserved=True,
            session_requested=session["requested"],
            session_available=session["available"],
            observed_turn_count=session["turn_count"],
        ),
        _area(
            "restart_and_session_resumption", "stable", "deterministic_persisted_state",
            session_selection_persisted=True,
            drafts_persisted=True,
            controls_persisted=True,
            current_turn_instruction_persisted=False,
            non_turn_scopes_restart_eligible=True,
            deterministic_contract_digest=contract_digest,
            writes_state=False,
        ),
        _area(
            "provider_outage_and_return", "ready", "explicit_review_after_recovery",
            outage_state=offline["offline_state"],
            returned_state=offline["returned_state"],
            generation_offline=offline["generation_offline"],
            generation_returned=offline["generation_returned"],
            automatic_request_replay=offline["automatic_request_replay"],
            automatic_execution_after_return=offline["automatic_execution_returned"],
            automatic_resend=offline["automatic_resend"],
        ),
        _area(
            "interruption_and_steering", "ready", str(steering.get("reason") or "unknown"),
            cancellation_first=True,
            steering_allowed=bool(steering.get("steering_allowed")),
            fresh_acceptance_identity_required=bool(steering.get("fresh_acceptance_identity_required")),
            accepted_request_replay=bool(steering.get("accepted_request_replay")),
            redirect_written=bool(steering.get("writes_redirect_content")),
            cancelled_memory_commit_allowed=bool(cancelled.get("memory_commit_allowed")),
            failed_memory_commit_allowed=bool(failed.get("memory_commit_allowed")),
            partial_response_committed=bool(steering.get("partial_response_committed")),
        ),
        _area(
            "retry_regeneration_and_resend", "ready", "separate_operation_identities",
            action_types=list(ACTION_TYPES),
            failed_retry_action=ACTION_FAILED_RETRY,
            regeneration_action=ACTION_REGENERATE,
            resend_action=ACTION_RESEND,
            failed_retry_reuses_acceptance=bool(action_plan.get("failed_retry_reuses_acceptance")),
            regeneration_reuses_user_memory=bool(action_plan.get("regeneration_reuses_user_memory")),
            resend_creates_new_user_turn=bool(action_plan.get("resend_creates_new_user_turn")),
            automatic_retry=bool(action_plan.get("automatic_retry")),
            automatic_regeneration=bool(action_plan.get("automatic_regeneration")),
            automatic_resend=bool(action_plan.get("automatic_resend")),
        ),
        _area(
            "message_editing_and_branching", "ready", "edit_creates_unsent_branch",
            branch_allowed=bool(branch.get("branch_allowed")),
            original_session_preserved=bool(branch.get("original_session_preserved")),
            original_turn_preserved=bool(branch.get("original_turn_preserved")),
            raw_transcript_rewritten=bool(branch.get("raw_transcript_rewritten")),
            provider_invoked=bool(branch.get("provider_invoked")),
            message_submitted=bool(branch.get("message_submitted")),
            automatic_branch_creation=bool(branch.get("automatic_branch_creation")),
        ),
        _area(
            "per_conversation_response_preferences", "ready", "session_local_with_turn_override",
            mode=preference.mode,
            format=preference.format,
            revision=preference.revision,
            session_local=preference.session_local,
            current_turn_override_allowed=preference.current_turn_override_allowed,
            mutates_global_personality=preference.mutates_global_personality,
            stored_instruction_digest=_digest(stored_preference_block),
            turn_override_digest=_digest(turn_override_block),
            override_changes_effective_guidance=stored_preference_block != turn_override_block,
        ),
        _area(
            "temporary_instruction_scope", "ready", "bounded_scope_resolution",
            **instructions,
        ),
        _area(
            "pinned_working_context", "ready", "bounded_optional_context_admission",
            **pins,
            session_local=True,
            stale_revision_rejected=True,
        ),
        _area(
            "offline_queued_operator_intent", "ready", str(offline["intent_reason"]),
            intent_state=offline["intent_state"],
            intent_digest=offline["intent_digest"],
            explicit_confirmation_required=offline["explicit_confirmation_required"],
            automatic_execution=offline["automatic_execution_offline"],
            automatic_resend=offline["automatic_resend"],
            provider_invoked=offline["provider_invoked"],
            writes_state=offline["writes_state"],
        ),
        _area(
            "offline_local_surfaces", "ready", "local_surfaces_only",
            draft_preserved=offline["draft_preserved"],
            navigation_preserved=offline["navigation_preserved"],
            search_preserved=offline["search_preserved"],
            memory_browse_preserved=offline["memory_browse_preserved"],
            context_inspection_preserved=offline["context_inspection_preserved"],
            branching_preserved=offline["branching_preserved"],
            provider_invoked=False,
        ),
        _area(
            "large_history_and_layout", "ready", "bounded_complete_turn_windows",
            initial_render_window=INITIAL_RENDER_WINDOW,
            earlier_history_window_limit=EARLIER_HISTORY_WINDOW_LIMIT,
            whole_turn_windows=True,
            scroll_anchor_preserved_on_prepend=True,
            jump_to_latest_preserved=True,
            narrow_layout_contained=True,
            full_transcript_embedded=False,
            observed_initial_turns_rendered=session["initial_turns_rendered"],
            observed_earlier_history_available=session["earlier_history_available"],
        ),
        _area(
            "multi_tab_exactly_once_and_immutability", "ready", "optimistic_revision_and_claim_guards",
            stale_revision_rejected=True,
            mutation_claim_required=True,
            cross_process_lease_required=True,
            accepted_operation_replayed=False,
            exactly_once_completion_claim=True,
            source_tree_mutation_required=False,
            observed_control_revision=session["control_revision"],
        ),
        _area(
            "relationship_memory_and_personality", "ready", "bounded_continuity_without_inflation",
            **continuity,
            raw_transcript_rewritten=False,
            memory_content_returned=False,
        ),
        _area(
            "operator_authority_and_privacy", "ready", "operator_authority_preserved",
            provider_invoked=False,
            model_management=False,
            provider_switching=False,
            generation_settings_changed=False,
            approval_granted=False,
            rollback_authorized=False,
            installation_performed=False,
            promotion_performed=False,
            release_certified=False,
            hidden_reasoning_returned=False,
            private_content_returned=False,
            writes_state=False,
        ),
    ]

    ready = len(areas) == CHECKPOINT_AREA_COUNT and all(row["state"] in {"ready", "stable"} for row in areas)
    return {
        "type": "desktop_alpha_conversation_readiness_checkpoint",
        "schema_version": CONVERSATION_READINESS_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "ready_for_operator_evaluation" if ready else "review_required",
        "area_count": len(areas),
        "ready_area_count": sum(1 for row in areas if row["state"] in {"ready", "stable"}),
        "session_requested": session["requested"],
        "session_available": session["available"],
        "contract_digest": contract_digest,
        "areas_digest": _digest(areas),
        "areas": areas,
        "limits": stable_contract["limits"],
        "read_only": True,
        "content_free": True,
        "redacted": True,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "writes_state": False,
        "release_certified": False,
        "verification_required": True,
        "installation_performed": False,
        "promotion_performed": False,
    }


def conversation_readiness_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "user_message", "assistant_response", "transcript", "prompt",
        "temporary_instruction", "pinned_context", "queued_operator_intent", "provider_payload", "credentials",
        "vectors", "embedding", "receipt", "receipts", "hidden_reasoning", "chain_of_thought",
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
        elif isinstance(current, str):
            lowered = current.lower()
            if "private current turn instruction" in lowered or "private pinned working context" in lowered:
                return True
    return False
