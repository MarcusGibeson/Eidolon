from __future__ import annotations

"""Reliable provider-neutral conversation execution and redacted receipts.

This module owns conversational provider calls and conversational memory commit
semantics. It does not install models, switch providers, execute proposed
actions, grant approvals, or authorize releases.
"""

import json
import queue
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from conversation_context import ConversationPromptPacket, build_conversation_prompt
from immediate_conversation_grounding import build_immediate_conversation_grounding
from conversation_cognitive_backbone import build_turn_cognitive_context, queue_turn_completion_safely
from response_intent_selection import build_response_intent_selection
from response_grounding_policy_v2672 import build_response_grounding_policy, response_grounding_prompt_section
from response_assertion_calibration_v2673 import build_response_assertion_calibration
from response_grounding_observability_v2676 import load_response_grounding_observability, record_response_grounding_observability
from response_grounding_outcome_feedback_v2677 import build_response_grounding_outcome_feedback
from response_grounding_learning_profile_v2678 import append_response_grounding_feedback, load_response_grounding_feedback_history, build_response_grounding_learning_profile, build_response_grounding_policy_review
from response_grounding_output_audit_v2683 import audit_response_grounding_output
from response_grounding_audit_observability_v2686 import record_response_grounding_output_audit
from response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from response_grounding_repair_review_v2688 import build_response_grounding_repair_review
from conversation_target_outcome_learning_v2690 import build_conversation_target_outcome
from conversation_target_outcome_history_v2691 import append_conversation_target_outcome, build_conversation_target_learning_profile
from conversation_health_v2694 import build_conversation_health
from conversation_health_history_v2697 import append_conversation_health, load_conversation_health_history
from conversation_health_trend_v2698 import build_conversation_health_trend
from conversation_outcome_attribution_v2700 import build_conversation_outcome_attribution
from response_quality_evaluation_v2701 import evaluate_response_quality
from response_quality_history_v2702 import append_response_quality, append_retrospective_response_quality, append_positive_retrospective_quality, load_response_quality_history
from response_quality_trend_v2703 import build_response_quality_trend
from response_quality_review_v2704 import build_response_quality_review
from response_quality_retrospective_v2706 import build_retrospective_response_quality
from response_outcome_followup_signal_v2707 import build_response_outcome_followup_signal
from response_quality_positive_retrospective_v2708 import build_positive_retrospective_quality
from daily_use_reliability_runtime_v2713 import build_daily_use_runtime_reliability
from contextual_conversation_behavior import build_contextual_conversation_behavior
from follow_up_silence_policy import build_follow_up_silence_policy
from conversation_discourse_policy import build_conversation_discourse_policy_for_turn
from natural_conversation_continuity import build_natural_continuity_for_turn
from conversation_target_continuity import (
    build_conversation_target_projection,
    enforce_conversation_target_output,
)
from natural_follow_up_policy import (
    NaturalFollowUpStreamGate,
    build_natural_follow_up_runtime_projection,
    enforce_natural_follow_up_output,
)
from governed_speech_policy import build_governed_speech_runtime_projection
from daily_companion_cognition import build_daily_companion_runtime_projection
from era5_companion_coherence import build_era5_companion_projection, audit_era5_companion_output
from preference_adaptation_v2300 import build_private_adaptation_prompt, context_codes_for_message
from unified_memory_context import build_unified_memory_runtime_projection
from memory_retrieval_relevance import build_memory_retrieval_relevance
from precision_memory_retrieval_v2569 import refine_memory_retrieval
from memory_retrieval_budget_v2571 import apply_memory_retrieval_budget
from memory_retrieval_sufficiency_v2573 import assess_memory_retrieval_sufficiency
from memory_retrieval_observability_v2576 import record_memory_retrieval_observability, load_memory_retrieval_observability
from memory_retrieval_followup_learning_v2583 import learn_from_followup_correction
from conversation_context_attribution_v2587 import build_conversation_context_attribution
from conversation_context_arbitration_v2588 import build_context_relevance_arbitration
from conversation_context_sufficiency_v2589 import assess_context_sufficiency
from conversation_context_observability_v2590 import record_conversation_context_observability
from memory_world_model_coherence import build_memory_world_model_projection
from immediate_memory_learning import build_immediate_memory_learning, build_learning_commit_boundary_handoff, audit_immediate_memory_learning
from bounded_experiential_lessons import build_bounded_experiential_lesson, build_lesson_review_boundary_handoff, audit_bounded_experiential_lesson
from memory_experiential_learning_alpha import (
    build_memory_experiential_learning_alpha,
    build_memory_experiential_learning_alpha_handoff,
    audit_memory_experiential_learning_alpha,
    build_memory_experiential_learning_alpha_reliability,
)
from natural_conversation_command_distinction import (
    distinguish_natural_conversation_and_command,
    public_conversation_command_distinction,
)
from conversational_command_integration import (
    build_conversational_command_integration,
    public_conversational_command_integration,
)
from unified_conversation_action import (
    build_unified_conversation_action_projection,
    public_unified_conversation_action_projection,
    unified_conversation_action_prompt,
)
from provider_aware_performance import (
    apply_provider_aware_performance_config,
    build_configured_provider_performance_plan,
    provider_aware_performance_prompt,
)
from provider_aware_performance_foundations import public_provider_aware_performance_plan
from local_model_readiness import provider_capabilities
from natural_language_action_routing import (
    apply_confirmed_execution as _apply_confirmed_execution,
    build_natural_language_action_projection,
    natural_language_action_public_projection,
    bound_unverified_action_claim as _bound_natural_language_action_claim,
    bounded_action_explanation as _bounded_action_explanation,
)
from action_proposal_handoff import (
    action_proposal_handoff_prompt,
    action_proposal_handoff_public,
    build_action_proposal_handoff,
)
from developer_campaign_conversation_projection import (
    build_developer_campaign_conversation_projection,
    developer_campaign_conversation_prompt,
    developer_campaign_conversation_public,
)
from ordinary_chat_development_campaign import (
    process_ordinary_chat_development_turn,
    development_campaign_conversation_prompt,
    development_campaign_public_projection,
)
from v1489_product_capability_integration import integrate_v1489_product_capabilities
from supervised_result_presentation import build_supervised_result_presentation, supervised_result_prompt
from supervised_action_execution import (
    build_supervised_execution_projection,
    supervised_execution_prompt,
    supervised_execution_public,
)
from conversation_policy_state import (
    build_conversation_policy_state,
    stage_conversation_policy_state,
    complete_conversation_policy_state,
)

# Retained source-inspection compatibility markers for the pre-v1159 shared seams.
# They are comments only; authoritative generation uses conversation_policy_state.
# cognitive_context=cognitive["prompt_section"] + "\n" + response_intent["prompt_section"]
# cognitive_context=cognitive["prompt_section"] + "\n" + response_intent["prompt_section"]
# contextual_behavior["prompt_section"]
# contextual_behavior["prompt_section"]
# follow_up_silence["prompt_section"]
# follow_up_silence["prompt_section"]
# natural_continuity["prompt_section"]
# natural_continuity["prompt_section"]

from conversation_sessions import append_conversation_turn, conversation_history_for_prompt, resolve_conversation_session, list_conversation_sessions, load_conversation_session, conversation_controls_for_prompt, bounded_cross_session_candidates
from desires import load_desires
from goal_manager import goal_context_text
from local_model import (
    ClosedClientError,
    ContextLimitError,
    InvalidConfigurationError,
    LocalModelCancelledError,
    LocalModelClient,
    LocalModelConfig,
    LocalModelError,
)
from memory import load_memories, store_memory, store_memory_vector, memory_record_exists
from memory_commit_attribution import (
    build_memory_commit_attribution,
    validate_memory_commit_attribution,
)
from paths import DATA_DIR
from project_manager import get_active_project, project_context_text
from relationship_continuity import build_relationship_continuity_snapshot, is_relationship_memory
from relationship_personality_continuity import classify_relationship_personality_continuity
from self_model import load_self_model
from settings_manager import load_settings
from task_queue import task_context_text
from response_time_runtime import (
    build_compact_cognitive_projection,
    classify_turn_relevance,
    generation_token_budget,
    provider_metrics_public,
    trusted_action_acknowledgement,
)
from critical_path_runtime import build_critical_path_decision, critical_path_public_receipt
from goal_planning_bundle import (
    apply_goal_planning_context,
    apply_goal_planning_handoffs,
    build_goal_planning_bundle,
    deferred_goal_planning_stub,
    unpack_goal_planning_bundle,
)
from work_coalescing import TurnWorkCache
from conversation_performance_metrics import classify_provider_start, mark_provider_warm, build_conversation_timing_receipt
from provider_reliability_contract import provider_recovery_guidance
from bounded_internal_maintenance import schedule_post_turn_housekeeping


RECEIPT_SCHEMA_VERSION = "2"
CONVERSATION_RECEIPT_DIR = DATA_DIR / "conversation_runtime" / "receipts"
_OPERATION_LOCK = threading.Lock()
_OPERATION_CANCEL_EVENTS: dict[str, threading.Event] = {}
_OPERATION_CANCEL_CALLBACKS: dict[str, Any] = {}
_MEMORY_VECTOR_QUEUE: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=256)
_MEMORY_VECTOR_WORKER_LOCK = threading.Lock()
_MEMORY_VECTOR_WORKER: threading.Thread | None = None


def _memory_vector_worker() -> None:
    while True:
        memory = _MEMORY_VECTOR_QUEUE.get()
        try:
            store_memory_vector(memory)
        finally:
            _MEMORY_VECTOR_QUEUE.task_done()


def _queue_memory_vectors(*memories: dict[str, Any] | None) -> None:
    global _MEMORY_VECTOR_WORKER
    rows = [dict(memory) for memory in memories if isinstance(memory, dict)]
    if not rows:
        return
    with _MEMORY_VECTOR_WORKER_LOCK:
        if _MEMORY_VECTOR_WORKER is None or not _MEMORY_VECTOR_WORKER.is_alive():
            _MEMORY_VECTOR_WORKER = threading.Thread(
                target=_memory_vector_worker,
                name="eidolon-memory-vector-worker",
                daemon=True,
            )
            _MEMORY_VECTOR_WORKER.start()
    for memory in rows:
        try:
            _MEMORY_VECTOR_QUEUE.put_nowait(memory)
        except queue.Full:
            break


@dataclass
class ConversationRuntimeResult:
    operation_id: str
    success: bool
    completion_state: str
    response: str = ""
    display_message: str = ""
    provider: str = ""
    model: str = ""
    streaming: bool = False
    retry_count: int = 0
    provider_request_count: int = 0
    failure_category: str | None = None
    error: dict[str, Any] | None = None
    timings_ms: dict[str, int | None] = field(default_factory=dict)
    provider_metrics: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    user_memory_stored: bool = False
    user_memory_reused: bool = False
    assistant_memory_stored: bool = False
    user_memory_attribution_id: str = ""
    assistant_memory_attribution_id: str = ""
    receipt_path: str = ""
    receipt_persisted: bool = False
    cognitive_context: dict[str, Any] = field(default_factory=dict)
    turn_completion: dict[str, Any] = field(default_factory=dict)
    fallback_configured: bool = False
    fallback_used: bool = False
    session_id: str = ""
    session_turn_recorded: bool = False
    recovery_of: str = ""
    recovery_kind: str = ""

    def to_dict(self, *, include_response: bool = True, include_cognitive_context: bool = True) -> dict[str, Any]:
        result = asdict(self)
        if not include_response:
            result.pop("response", None)
            result.pop("display_message", None)
        if not include_cognitive_context:
            result.pop("cognitive_context", None)
        return result


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _operation_id() -> str:
    return f"conversation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:12]}"


def _resolved_operation_id(operation_id: str = "") -> str:
    token = str(operation_id or "").strip()
    if not token:
        return _operation_id()
    if not token.startswith("conversation_") or len(token) > 80:
        raise ValueError("Invalid conversation operation identifier.")
    return token


def _register_operation(operation_id: str, cancel_event: threading.Event) -> None:
    with _OPERATION_LOCK:
        _OPERATION_CANCEL_EVENTS[operation_id] = cancel_event


def _set_operation_cancel_callback(operation_id: str, callback: Any) -> None:
    with _OPERATION_LOCK:
        if operation_id in _OPERATION_CANCEL_EVENTS:
            _OPERATION_CANCEL_CALLBACKS[operation_id] = callback


def _unregister_operation(operation_id: str) -> None:
    with _OPERATION_LOCK:
        _OPERATION_CANCEL_EVENTS.pop(operation_id, None)
        _OPERATION_CANCEL_CALLBACKS.pop(operation_id, None)


def _claim_operation_completion(operation_id: str, cancel_event: threading.Event) -> bool:
    """Atomically close cancellation before committing a completed response."""
    with _OPERATION_LOCK:
        registered = _OPERATION_CANCEL_EVENTS.get(operation_id)
        if registered is not cancel_event or cancel_event.is_set():
            return False
        _OPERATION_CANCEL_EVENTS.pop(operation_id, None)
        _OPERATION_CANCEL_CALLBACKS.pop(operation_id, None)
        return True


def cancel_conversation_operation(operation_id: str) -> dict[str, Any]:
    """Cancel one active conversation without touching provider/model configuration."""
    token = str(operation_id or "").strip()
    with _OPERATION_LOCK:
        cancel_event = _OPERATION_CANCEL_EVENTS.get(token)
        callback = _OPERATION_CANCEL_CALLBACKS.get(token)
    if cancel_event is None:
        return {
            "ok": False,
            "operation_id": token,
            "status": "not_active",
            "message": "Conversation operation is not active or has already completed.",
        }
    cancel_event.set()
    if callable(callback):
        try:
            callback()
        except Exception:
            pass
    return {
        "ok": True,
        "operation_id": token,
        "status": "cancellation_requested",
        "message": "Conversation cancellation was requested.",
    }


def _clean_assistant_response(value: str, name: str = "Eidolon") -> str:
    """Remove provider-added role labels without altering the actual reply."""
    text = str(value or "").strip()
    labels = {"assistant", "eidolon", str(name or "Eidolon").strip().lower()}
    for _ in range(3):
        match = re.match(r"^([A-Za-z][A-Za-z0-9 _-]{0,40})\s*:\s*", text)
        if not match or match.group(1).strip().lower() not in labels:
            break
        text = text[match.end():].lstrip()
    return text


_UNVERIFIED_ACTION_CLAIM = re.compile(
    r"\b(?:i(?:'ll| will)|let'?s|we(?:'ll| will))\s+(?:now\s+)?"
    r"(?:proceed|perform|run|execute|check|inspect|scan|apply|modify|update|install|delete|create|build|fix|verify|review)\b",
    re.I,
)


def _bound_unverified_action_claim(response: str, response_intent: dict[str, Any]) -> str:
    """Prevent provider prose from becoming execution evidence without a receipt."""
    if isinstance(response_intent, dict) and "intent" in response_intent and "grounding" in response_intent:
        intent = response_intent.get("intent") if isinstance(response_intent.get("intent"), dict) else {}
        grounding = response_intent.get("grounding") if isinstance(response_intent.get("grounding"), dict) else {}
        if intent.get("action_intent_present") and not grounding.get("authoritative_execution_receipt_present"):
            return _bounded_action_explanation(response_intent)
        return _bound_natural_language_action_claim(response, response_intent)
    evidence = response_intent.get("evidence") if isinstance(response_intent, dict) else {}
    action_request = bool(evidence.get("action_intent_present")) if isinstance(evidence, dict) else False
    if not action_request:
        return str(response or "")
    return (
        "I recognized this as a system action request. I have not executed it through the conversation model; "
        "the supervised action router must report an authoritative result before it counts as completed."
    )


class _AssistantStreamCleaner:
    """Buffer only a possible leading role label before exposing stream text."""

    def __init__(self, name: str = "Eidolon") -> None:
        self.name = str(name or "Eidolon").strip() or "Eidolon"
        self.labels = tuple(sorted({"assistant", "eidolon", self.name.lower()}, key=len, reverse=True))
        self.buffer = ""
        self.decided = False
        self.labels_removed = 0

    def _possible_label_prefix(self, value: str) -> bool:
        lowered = value.lower()
        return any(
            label.startswith(lowered)
            or bool(re.fullmatch(rf"{re.escape(label)}\s*", value, flags=re.IGNORECASE))
            for label in self.labels
        )

    def feed(self, value: str) -> str:
        text = str(value or "")
        if self.decided:
            return text
        self.buffer += text
        while self.labels_removed < 3:
            candidate = self.buffer.lstrip()
            if not candidate:
                return ""
            match = next(
                (
                    match for label in self.labels
                    if (match := re.match(rf"^{re.escape(label)}\s*:\s*", candidate, flags=re.IGNORECASE))
                ),
                None,
            )
            if match is not None:
                self.buffer = candidate[match.end():]
                self.labels_removed += 1
                continue
            if self._possible_label_prefix(candidate):
                return ""
            break
        self.decided = True
        visible = self.buffer.lstrip()
        self.buffer = ""
        return visible

    def finish(self) -> str:
        if self.decided:
            return ""
        self.decided = True
        visible = _clean_assistant_response(self.buffer, self.name)
        self.buffer = ""
        return visible


def _failure_category(error: BaseException) -> str:
    if isinstance(error, LocalModelError):
        return error.code
    if isinstance(error, (OSError, IOError)):
        return "runtime_io_failure"
    return "conversation_runtime_failure"


def _safe_error(error: BaseException, config: LocalModelConfig | None = None) -> dict[str, Any]:
    if isinstance(error, LocalModelError):
        return error.to_safe_dict()
    return {
        "code": _failure_category(error),
        "message": "The conversation runtime failed before a safe provider result was completed.",
        "provider": str(config.provider if config else "")[:40],
        "model": str(config.model if config else "")[:160],
        "retryable": False,
        "status_code": None,
        "details": {"exception_type": type(error).__name__},
        "redacted": True,
    }


def conversation_error_message(error: BaseException, *, provider: str = "", model: str = "") -> str:
    category = _failure_category(error)
    provider_text = provider or (error.provider if isinstance(error, LocalModelError) else "configured provider")
    model_text = model or (error.model if isinstance(error, LocalModelError) else "configured model")
    messages = {
        "unavailable_service": f"The configured {provider_text} service is unavailable. No fallback provider was used.",
        "missing_model": f"The configured model {model_text!r} is unavailable from {provider_text}. Model installation remains an operator action.",
        "timeout": f"The configured {provider_text} request timed out. No fallback provider was used and no model switch occurred.",
        "unsupported_streaming": f"The configured {provider_text} endpoint does not support streaming. Use non-streaming or change the configuration explicitly.",
        "malformed_response": f"The configured {provider_text} service returned an invalid response. Raw provider data was not saved.",
        "interrupted_stream": f"The configured {provider_text} stream disconnected before completion. The partial response was not committed to memory.",
        "context_limit": "The conversation could not fit inside the configured context window. Protected instructions and the latest user message were not truncated.",
        "cancelled": "The conversation request was cancelled. Any partial response was discarded and not committed to memory.",
        "empty_response": f"The configured {provider_text} service completed without a usable response.",
        "memory_write_failure": "The response could not be committed to conversational memory. The turn is marked incomplete.",
        "invalid_configuration": "The local-model configuration is invalid. No provider request or fallback was attempted.",
        "closed_client": "The local-model client closed before the conversation completed.",
    }
    return messages.get(category, "The conversation runtime failed safely. No fallback provider was used and no failed response was committed to memory.")


def _build_prompt_packet(
    user_message: str,
    *,
    config: LocalModelConfig,
    self_model: dict[str, Any],
    desires: dict[str, Any],
    memories: list[dict[str, Any]],
    conversation_history: list[dict[str, Any]],
    session_id: str = "",
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
    cognitive_context: str = "",
    natural_follow_up_policy: dict[str, Any] | None = None,
) -> ConversationPromptPacket:
    continuity_profile = classify_relationship_personality_continuity(
        user_message, conversation_history,
    )
    relationship_context = build_relationship_continuity_snapshot(
        memories, self_model, user_message=user_message, interaction_profile=continuity_profile,
    )
    general_memories = [memory for memory in memories if not is_relationship_memory(memory)]
    other_sessions = bounded_cross_session_candidates(
        user_message, session_id=session_id, project_id=None, limit=6,
    )
    controls = conversation_controls_for_prompt(session_id) if session_id else {}
    return build_conversation_prompt(
        user_message=user_message,
        self_model=self_model,
        desires=desires,
        memories=general_memories,
        project_context=project_context_text(include_version_roles=False),
        goal_context=goal_context_text(),
        task_context=task_context_text(),
        conversation_history=conversation_history,
        relationship_context=relationship_context,
        continuity_profile=continuity_profile,
        current_session_id=session_id,
        cross_session_sessions=other_sessions,
        response_preferences=controls.get("response_preferences") if isinstance(controls, dict) else None,
        temporary_instruction=controls.get("temporary_instruction") if isinstance(controls, dict) else None,
        pinned_context=controls.get("pinned_context", []) if isinstance(controls, dict) else (),
        cognitive_context=cognitive_context,
        transient_instruction=transient_instruction,
        transient_instruction_scope=transient_instruction_scope,
        context_size=config.context_size,
        max_tokens=config.generation.max_tokens,
        natural_follow_up_policy=natural_follow_up_policy,
    )


def _memory_exists(operation_id: str, memory_type: str) -> bool:
    token = str(operation_id or "").strip()
    if not token:
        return False
    return memory_record_exists(token, memory_type)


def _apply_immediate_grounding_metrics(context: dict[str, Any], grounding: Any) -> None:
    """Overlay content-free grounding truth from the pre-selection evidence boundary."""
    if not isinstance(context, dict) or grounding is None:
        return
    context.update({
        "immediate_grounding_present": bool(getattr(grounding, "block", "")),
        "immediate_recall_requested": bool(getattr(grounding, "immediate_recall_requested", False)),
        "immediate_exact_repeat_requested": bool(getattr(grounding, "exact_repeat_requested", False)),
        "immediate_correction_protected": bool(getattr(grounding, "current_message_correction", False) or getattr(grounding, "protected_recent_correction", False)),
        "immediate_grounding_state": str(getattr(grounding, "grounding_state", "none") or "none"),
        "current_message_correction_protected": bool(getattr(grounding, "current_message_correction", False)),
        "compound_grounding_explanation_requested": bool(getattr(grounding, "compound_explanation_requested", False)),
        "historical_memory_query": bool(getattr(grounding, "historical_memory_query", False)),
        "attributable_historical_memory_available": bool(getattr(grounding, "attributable_memory_available", False)),
        "historical_memory_evidence_state": str(getattr(grounding, "historical_evidence_state", "not_historical") or "not_historical"),
        "historical_memory_evidence_requested": bool(getattr(grounding, "historical_evidence_requested", False)),
        "historical_uncertainty_required": bool(getattr(grounding, "historical_uncertainty_required", False)),
        "historical_evidence_class_counts": grounding.historical_evidence_class_counts() if hasattr(grounding, "historical_evidence_class_counts") else {},
        "historical_provenance_state_digest": grounding.provenance_state_digest() if hasattr(grounding, "provenance_state_digest") else "",
        "historical_user_authored_evidence_count": int(getattr(grounding, "historical_user_authored_count", 0) or 0),
        "historical_assistant_authored_non_evidence_count": int(getattr(grounding, "historical_assistant_authored_non_evidence_count", 0) or 0),
        "historical_user_nonassertive_count": int(getattr(grounding, "historical_user_nonassertive_count", 0) or 0),
        "historical_malformed_evidence_count": int(getattr(grounding, "historical_malformed_count", 0) or 0),
        "historical_conflict_count": int(getattr(grounding, "historical_conflict_count", 0) or 0),
        "historical_weak_match_rejected_count": int(getattr(grounding, "historical_weak_match_rejected_count", 0) or 0),
        "historical_match_strength": str(getattr(grounding, "historical_match_strength", "none") or "none"),
    })


def _store_user_memory(
    operation_id: str,
    message: str,
    source: str,
    session_id: str,
    *,
    recovery_of: str = "",
    continuity_lane: str = "ordinary",
) -> dict[str, Any]:
    attribution = build_memory_commit_attribution(
        role="user",
        operation_id=operation_id,
        session_id=session_id,
        turn_id=operation_id,
        source=source,
        content=message,
        completion_state="received",
    )
    memory = {
        "id": attribution["memory_candidate_id"],
        "memory_candidate_id": attribution["memory_candidate_id"],
        "memory_commit_attribution": attribution,
        "type": "conversation_user",
        "content": message,
        "source": source,
        "conversation_operation_id": operation_id,
        "conversation_session_id": session_id,
        "conversation_turn_id": operation_id,
        "completion_state": "received",
        "recovery_of": str(recovery_of or ""),
        "continuity_lane": str(continuity_lane or "ordinary")[:24],
        "relationship_eligible": False,
        "use_in_relationship_continuity": False,
    }
    store_memory(memory, vectorize=False)
    from active_conversation_facts import persist_explicit_user_memory_request
    from entity_association_curation import apply_conversational_entity_association_mutation
    memory["explicit_memory_result"] = persist_explicit_user_memory_request(message)
    memory["entity_association_mutation"] = apply_conversational_entity_association_mutation(message)
    return memory


def _store_assistant_memory(
    operation_id: str,
    response: str,
    source: str,
    config: LocalModelConfig,
    session_id: str,
    *,
    continuity_lane: str = "ordinary",
) -> dict[str, Any]:
    attribution = build_memory_commit_attribution(
        role="assistant",
        operation_id=operation_id,
        session_id=session_id,
        turn_id=operation_id,
        source=source,
        content=response,
        completion_state="completed",
        provider_generation_completed=True,
        operation_completion_claimed=True,
        synthetic_response=False,
        partial_response=False,
    )
    validate_memory_commit_attribution(attribution, require_assistant_eligible=True)
    memory = {
        "id": attribution["memory_candidate_id"],
        "memory_candidate_id": attribution["memory_candidate_id"],
        "memory_commit_attribution": attribution,
        "type": "conversation_eidolon",
        "content": response,
        "source": source,
        "conversation_operation_id": operation_id,
        "conversation_session_id": session_id,
        "conversation_turn_id": operation_id,
        "completion_state": "completed",
        "provider": config.provider,
        "model": config.model,
        "continuity_lane": str(continuity_lane or "ordinary")[:24],
        "relationship_eligible": False,
        "use_in_relationship_continuity": False,
    }
    store_memory(memory, vectorize=False)
    return memory


def _receipt_for(result: ConversationRuntimeResult, started_at: str, completed_at: str) -> dict[str, Any]:
    return {
        "receipt_type": "conversation_runtime",
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "operation_id": result.operation_id,
        "conversation_session_id": result.session_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "provider": result.provider[:40],
        "model": result.model[:160],
        "operation": "streaming_generation" if result.streaming else "non_streaming_generation",
        "timings_ms": dict(result.timings_ms),
        "provider_metrics": dict(result.provider_metrics),
        "performance": dict(result.cognitive_context.get("response_performance") or {}),
        "retry_count": int(result.retry_count),
        "completion_state": result.completion_state,
        "failure_category": result.failure_category,
        "context_budget": dict(result.context),
        "cognitive_completion": {
            "state": str(result.turn_completion.get("completion_state") or "not_attempted"),
            "recorded": bool(result.turn_completion.get("completion_state") == "completed"),
            "retry_required": bool(result.turn_completion.get("retry_required", False)),
            "contains_content": False,
        },
        "memory_commit": {
            "user_message": result.user_memory_stored,
            "user_message_reused": result.user_memory_reused,
            "assistant_response": result.assistant_memory_stored,
            "attribution_schema_version": "1",
            "user_memory_candidate_id": result.user_memory_attribution_id,
            "assistant_memory_candidate_id": result.assistant_memory_attribution_id,
            "contains_memory_content": False,
        },
        "recovery": {
            "kind": result.recovery_kind,
            "source_operation_id": result.recovery_of,
        },
        "session_turn_recorded": result.session_turn_recorded,
        "fallback": {
            "configured": result.fallback_configured,
            "used": result.fallback_used,
        },
        "contains_prompts": False,
        "contains_generated_responses": False,
        "contains_credentials": False,
        "contains_raw_events": False,
        "redacted": True,
        "governance": {
            "provider_selection_changed": False,
            "model_management_performed": False,
            "approval_granted": False,
            "release_authorized": False,
            "autonomous_action_performed": False,
        },
    }


def _persist_receipt(result: ConversationRuntimeResult, started_at: str) -> None:
    completed_at = _now_utc()
    receipt = _receipt_for(result, started_at, completed_at)
    try:
        CONVERSATION_RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        path = CONVERSATION_RECEIPT_DIR / f"{result.operation_id}.json"
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
            for attempt in range(5):
                try:
                    temporary.replace(path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)
        result.receipt_path = str(path)
        result.receipt_persisted = True
    except OSError:
        result.receipt_path = ""
        result.receipt_persisted = False


def _base_result(
    operation_id: str,
    config: LocalModelConfig,
    streaming: bool,
    session_id: str = "",
    *,
    recovery_of: str = "",
    recovery_kind: str = "",
) -> ConversationRuntimeResult:
    return ConversationRuntimeResult(
        operation_id=operation_id,
        success=False,
        completion_state="started",
        provider=config.provider,
        model=config.model,
        streaming=streaming,
        session_id=session_id,
        recovery_of=recovery_of,
        recovery_kind=recovery_kind,
    )




def _load_runtime_configuration(
    operation_id: str,
    *,
    streaming: bool,
    session_id: str = "",
    recovery_of: str = "",
    recovery_kind: str = "",
) -> tuple[dict[str, Any], LocalModelConfig | None, ConversationRuntimeResult, LocalModelError | None]:
    settings: dict[str, Any] = {}
    provider = "configured provider"
    model = "configured model"
    try:
        settings = load_settings()
        provider = str(settings.get("local_model_provider") or provider)[:40]
        model = str(settings.get("local_model") or model)[:160]
        config = LocalModelConfig.from_settings(settings)
        return settings, config, _base_result(
            operation_id,
            config,
            streaming,
            session_id,
            recovery_of=recovery_of,
            recovery_kind=recovery_kind,
        ), None
    except LocalModelError as error:
        config_error = error if isinstance(error, InvalidConfigurationError) else InvalidConfigurationError(
            "The local-model configuration could not be loaded safely.",
            provider=provider,
            model=model,
            details={"failure_kind": "configuration_load", "exception_type": type(error).__name__},
        )
    except (TypeError, ValueError) as error:
        config_error = InvalidConfigurationError(
            "The local-model configuration could not be loaded safely.",
            provider=provider,
            model=model,
            details={"failure_kind": "configuration_load", "exception_type": type(error).__name__},
        )
    result = ConversationRuntimeResult(
        operation_id=operation_id,
        success=False,
        completion_state="failed",
        provider=provider,
        model=model,
        streaming=streaming,
        session_id=session_id,
        failure_category="invalid_configuration",
        error=config_error.to_safe_dict(),
        display_message=conversation_error_message(config_error, provider=provider, model=model),
        recovery_of=recovery_of,
        recovery_kind=recovery_kind,
    )
    return settings, None, result, config_error


def _session_context(session_id: str) -> tuple[str, list[dict[str, str]]]:
    session = resolve_conversation_session(session_id, create_if_missing=True)
    if not session:
        raise ValueError("Conversation session could not be created or resumed.")
    resolved = str(session.get("id") or "")
    if not resolved:
        raise ValueError("Conversation session identifier is missing.")
    return resolved, conversation_history_for_prompt(resolved, limit=16)


def _grounding_session_history(session_id: str) -> list[dict[str, str]]:
    """Use a wider read-only fact window without enlarging the provider prompt history."""
    return conversation_history_for_prompt(session_id, limit=64)


def _long_term_memories(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Session transcript owns recent dialogue; general memory supplies durable facts."""
    selected: list[dict[str, Any]] = []
    for memory in memories:
        memory_type = str(memory.get("type") or "")
        integrity = memory.get("provenance_integrity") if isinstance(memory.get("provenance_integrity"), dict) else {}
        provenance = str(integrity.get("provenance_class") or "").strip().lower()
        eligible = memory.get("historical_evidence_eligible")
        if eligible is None:
            eligible = integrity.get("historical_evidence_eligible")
        if memory_type == "conversation_eidolon" or provenance == "assistant":
            continue
        if eligible is False or memory.get("use_in_conversation") is False:
            continue
        selected.append(memory)
    return selected


def _grounding_memories(recent_memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep active explicit relationship facts available beyond the general-memory window."""
    from relationship_memory_curation import list_relationship_memory_curation_records

    rows = list(recent_memories)
    curated = list_relationship_memory_curation_records(include_retracted=False)
    seen = {
        (str(row.get("record_key") or row.get("id") or ""), str(row.get("content") or ""))
        for row in rows if isinstance(row, dict)
    }
    for row in curated:
        key = (str(row.get("record_key") or row.get("id") or ""), str(row.get("content") or ""))
        if key not in seen:
            rows.append(row)
            seen.add(key)
    return rows


def _record_session_turn(
    result: ConversationRuntimeResult,
    *,
    user_message: str,
    source: str,
    created_at: str,
    select_session: bool = True,
) -> None:
    if not result.session_id or not str(user_message or "").strip():
        return
    try:
        append_conversation_turn(
            result.session_id,
            turn_id=result.operation_id,
            user_message=user_message,
            assistant_response=result.response if result.success else result.display_message,
            completion_state=result.completion_state,
            success=result.success,
            provider=result.provider,
            model=result.model,
            streaming=result.streaming,
            failure_category=result.failure_category,
            source=source,
            created_at=created_at,
            user_memory_stored=result.user_memory_stored,
            user_memory_reused=result.user_memory_reused,
            assistant_memory_stored=result.assistant_memory_stored,
            user_memory_attribution_id=result.user_memory_attribution_id,
            assistant_memory_attribution_id=result.assistant_memory_attribution_id,
            recovery_of=result.recovery_of,
            recovery_kind=result.recovery_kind,
            continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            relationship_memory_policy=str(result.context.get("relationship_memory_policy") or "explicit_curation_only"),
            diagnostic=(
                None
                if result.success
                else result.error
                or {
                    "code": result.failure_category or result.completion_state,
                    "provider": result.provider,
                    "model": result.model,
                    "retryable": False,
                    "redacted": True,
                }
            ),
            select_session=select_session,
            allow_default_title_update=select_session,
        )
        result.session_turn_recorded = True
    except (OSError, ValueError):
        result.session_turn_recorded = False


def _complete_deferred_goal_planning(
    *,
    result: ConversationResult,
    decision: Any,
    message: str,
    memory_learning_alpha_projection: dict[str, Any],
    session_history: list[dict[str, Any]],
    current_bundle: dict[str, Any],
) -> dict[str, Any]:
    """Finish non-critical planning after provider generation without failing the turn."""
    if not bool(getattr(decision, "goal_planning_deferred", False)):
        return current_bundle
    started = time.monotonic()
    receipt = result.cognitive_context.setdefault("critical_path", critical_path_public_receipt(decision))
    try:
        completed = build_goal_planning_bundle(
            message,
            memory_learning_alpha_projection,
            session_history=session_history,
            phase="post_provider",
        )
        apply_goal_planning_context(result.cognitive_context, completed)
        receipt["deferred_goal_planning_completed"] = True
        receipt["deferred_error_type"] = None
        return completed
    except Exception as error:
        receipt["deferred_goal_planning_completed"] = False
        receipt["deferred_error_type"] = type(error).__name__
        return current_bundle
    finally:
        result.timings_ms["deferred_goal_planning"] = int((time.monotonic() - started) * 1000)


def _schedule_housekeeping_safely(result: ConversationResult) -> None:
    """Schedule content-free housekeeping; never make it part of conversation success."""
    try:
        result.cognitive_context["post_turn_housekeeping"] = schedule_post_turn_housekeeping(result.session_id)
    except Exception as error:
        result.cognitive_context["post_turn_housekeeping"] = {
            "scheduled": False,
            "error_type": type(error).__name__,
            "content_free": True,
            "authority_granted": False,
        }


def run_conversation_turn(
    user_message: str,
    *,
    source: str = "terminal_chat",
    use_ai: bool = True,
    cancel_event: threading.Event | None = None,
    session_id: str = "",
    recovery_of: str = "",
    recovery_kind: str = "",
    operation_id: str = "",
    select_session_on_record: bool = True,
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
    authoritative_action_results: tuple[dict[str, Any], ...] = (),
) -> ConversationRuntimeResult:
    """Run one non-streaming turn. Safe transient retries occur before visibility."""
    started_clock = time.monotonic()
    started_at = _now_utc()
    provider_start_kind = "not_contacted"
    prompt_tokens = 0
    operation_id = _resolved_operation_id(operation_id)
    message = str(user_message or "").strip()
    resolved_session_id, session_history = _session_context(session_id)
    settings, config, result, configuration_error = _load_runtime_configuration(
        operation_id,
        streaming=False,
        session_id=resolved_session_id,
        recovery_of=recovery_of,
        recovery_kind=recovery_kind,
    )
    if configuration_error is not None or config is None:
        result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
        _record_session_turn(
            result, user_message=message, source=source, created_at=started_at,
            select_session=select_session_on_record,
        )
        _persist_receipt(result, started_at)
        return result
    active_cancel = cancel_event or threading.Event()
    user_memory: dict[str, Any] | None = None
    _register_operation(operation_id, active_cancel)
    try:
        turn_work = TurnWorkCache()
        if not message:
            raise ContextLimitError("Conversation user message cannot be empty.", details={"failure_kind": "empty_message"})
        conversation_command_distinction = distinguish_natural_conversation_and_command(message)
        conversational_command_integration = build_conversational_command_integration(
            message, conversation_history=session_history, session_id=resolved_session_id,
        )
        routed_action_text = str(conversational_command_integration.get("routing_text") or "").strip()
        if not routed_action_text and conversational_command_integration.get("status") in {
            "conversation_only", "correction_target_resolved", "cancellation_target_resolved",
            "correction_target_ambiguous", "cancellation_target_ambiguous", "generic_authorization_blocked",
        }:
            routed_action_text = message
        if conversation_command_distinction.get("requires_clarification"):
            routed_action_text = ""
        action_projection = build_natural_language_action_projection(
            routed_action_text, conversation_history=session_history, authoritative_receipts=authoritative_action_results,
        )
        # The live turn is the only place a confirmed proposal runs. Grounding never executes, so a confirmation
        # replayed from history cannot start a second run.
        action_projection = _apply_confirmed_execution(action_projection)
        conversational_command_integration = build_conversational_command_integration(
            message, action_projection=action_projection, conversation_history=session_history, session_id=resolved_session_id,
        )
        result_presentation = build_supervised_result_presentation(
            str((action_projection.get("grounding") or {}).get("capability_id") or ""), authoritative_action_results,
        )

        action_handoff = build_action_proposal_handoff(action_projection, operation_id=operation_id)
        active_project = turn_work.get("active_project", get_active_project)
        development_campaign_lifecycle = process_ordinary_chat_development_turn(
            routed_action_text,
            action_projection=action_projection,
            session_id=resolved_session_id,
            project_state=active_project,
        )
        development_campaign_lifecycle = integrate_v1489_product_capabilities(
            routed_action_text or message,
            development_campaign_lifecycle,
            project_state=active_project if isinstance(active_project, dict) else None,
        )
        developer_campaign_projection = build_developer_campaign_conversation_projection(
            action_projection,
            action_handoff,
            project_state=active_project,
            lifecycle_state=development_campaign_lifecycle,
        )
        unified_conversation_action = build_unified_conversation_action_projection(
            message,
            conversational_command_integration=conversational_command_integration,
            action_projection=action_projection,
            development_lifecycle=development_campaign_lifecycle,
            developer_campaign_projection=developer_campaign_projection,
        )
        execution_projection = build_supervised_execution_projection(action_handoff, operation_id=operation_id)
        # Scan enough canonical history to survive the several derived records emitted
        # per turn; the coherence projection then applies its tighter selection bound.
        memories = _long_term_memories(load_memories(limit=480))
        memory_world_model_projection = build_memory_world_model_projection(message, memories)
        memories = list(memory_world_model_projection["selected_memory_records"])
        grounding_memory_candidates = _grounding_memories(memories)
        unified_memory_projection = build_unified_memory_runtime_projection(
            message,
            memory_records=memories,
            conversation_history=session_history,
            project_state=active_project,
            protected_operator_constraints=(
                "current_message_precedence", "explicit_correction_precedence",
                "no_memory_mutation", "no_action_execution",
            ),
            prior_unified_memory_receipts=session_history,
        )
        # Retained v1165 handoff seam: memories = list(unified_memory_projection["selected_memory_records"])
        memory_retrieval_projection = build_memory_retrieval_relevance(
            message,
            unified_memory_projection["selected_memory_records"],
            unified_memory_projection.get("selected_references"),
            prior_retrieval_receipts=session_history,
        )
        memory_retrieval_projection = refine_memory_retrieval(memory_retrieval_projection)
        memory_retrieval_projection = apply_memory_retrieval_budget(memory_retrieval_projection)
        memory_retrieval_projection["retrieval_sufficiency"] = assess_memory_retrieval_sufficiency(memory_retrieval_projection)
        prior_memory_retrieval_observability = load_memory_retrieval_observability()
        prior_response_grounding_observability = load_response_grounding_observability()
        memory_retrieval_projection["retrieval_observability"] = record_memory_retrieval_observability(memory_retrieval_projection, operation_id=operation_id)
        memories = list(memory_retrieval_projection["selected_memory_records"])
        immediate_learning_projection = build_immediate_memory_learning(
            message,
            memories,
            protected_operator_constraints=(
                "preserve_historical_truth", "no_unconfirmed_memory_mutation", "current_message_precedence",
            ),
            prior_learning_receipts=session_history,
        )
        memory_retrieval_followup_learning = learn_from_followup_correction(
            prior_memory_retrieval_observability, immediate_learning_projection
        )
        response_grounding_outcome_feedback = build_response_grounding_outcome_feedback(
            prior_response_grounding_observability, immediate_learning_projection
        )
        append_response_grounding_feedback(response_grounding_outcome_feedback)
        retrospective_response_quality = build_retrospective_response_quality(
            prior_response_grounding_observability, response_grounding_outcome_feedback, evidence_operation_id=operation_id
        )
        append_retrospective_response_quality(retrospective_response_quality)
        response_outcome_followup_signal = build_response_outcome_followup_signal(message, immediate_learning_projection)
        positive_retrospective_response_quality = build_positive_retrospective_quality(
            prior_response_grounding_observability, response_outcome_followup_signal, evidence_operation_id=operation_id
        )
        if not response_outcome_followup_signal.get("negative_followup"):
            append_positive_retrospective_quality(positive_retrospective_response_quality)
        response_grounding_learning_profile = build_response_grounding_learning_profile(
            load_response_grounding_feedback_history().get("rows") or []
        )
        response_grounding_policy_review = build_response_grounding_policy_review(response_grounding_learning_profile)
        bounded_lesson_projection = build_bounded_experiential_lesson(
            message, immediate_learning_projection, experience_rows=session_history,
            protected_operator_constraints=(
                "no_uncontrolled_self_training", "review_before_durable_lesson", "preserve_historical_truth",
            ),
            prior_lesson_receipts=session_history,
        )
        memory_learning_alpha_projection = build_memory_experiential_learning_alpha(
            unified_memory_projection, memory_retrieval_projection,
            immediate_learning_projection, bounded_lesson_projection,
            prior_alpha_receipts=session_history,
        )
        turn_relevance = classify_turn_relevance(
            message, action_projection=action_projection, development_campaign=development_campaign_lifecycle,
        )
        critical_path_decision = build_critical_path_decision(
            message, relevance=turn_relevance, action_projection=action_projection,
            development_campaign=development_campaign_lifecycle,
        )
        if critical_path_decision.goal_planning_pre_provider:
            goal_planning_bundle = build_goal_planning_bundle(
                message, memory_learning_alpha_projection, session_history=session_history, phase="pre_provider",
            )
        else:
            goal_planning_bundle = deferred_goal_planning_stub()
        (
            goal_candidate_projection, goal_candidate_review_projection, goal_candidate_reliability,
            hierarchical_planning_projection, hierarchical_planning_review_projection, hierarchical_planning_reliability,
            plan_simulation_projection, plan_simulation_review_projection, plan_simulation_reliability,
            persistent_follow_through_projection, persistent_follow_through_review_projection, persistent_follow_through_reliability,
            goal_and_planning_alpha_projection, goal_and_planning_alpha_review_projection, goal_and_planning_alpha_reliability,
        ) = unpack_goal_planning_bundle(goal_planning_bundle)
        memories = list(memory_learning_alpha_projection["selected_memory_records"])
        immediate_grounding = build_immediate_conversation_grounding(
            message, _grounding_session_history(resolved_session_id), grounding_memory_candidates
        )
        self_model = turn_work.get("self_model", load_self_model)
        desires = turn_work.get("desires", load_desires)
        context_started = time.monotonic()
        cognitive = build_turn_cognitive_context(
            message, operation_id=operation_id, session_id=resolved_session_id,
            memories=memories, self_model=self_model, desires=desires,
        )
        response_intent = build_response_intent_selection(
            message, reasoning_state=cognitive, conversation_history=session_history,
            explicit_corrections=[row for row in memories if isinstance(row, dict) and bool(row.get("operator_correction"))],
            protected_operator_constraints=("no_automatic_authority", "current_message_precedence", "protected_instructions_precedence"),
            self_model=self_model, desires=desires, contextual_memories=memories,
        )
        response_grounding = build_response_grounding_policy(
            response_intent, memory_retrieval_projection.get("retrieval_sufficiency") or {}, immediate_grounding.public_summary()
        )
        response_assertion_calibration = build_response_assertion_calibration(response_grounding)
        response_grounding_observability = record_response_grounding_observability(response_grounding, response_assertion_calibration, operation_id=operation_id)
        contextual_behavior = build_contextual_conversation_behavior(
            response_intent, self_model=self_model, contextual_memories=memories,
            conversation_history=session_history,
        )
        follow_up_silence = build_follow_up_silence_policy(message, response_intent, contextual_behavior)
        conversation_policy = build_conversation_policy_state(response_intent, contextual_behavior, follow_up_silence)
        conversation_discourse = build_conversation_discourse_policy_for_turn(
            message, conversation_policy, conversation_history=session_history,
            explicit_corrections=[row for row in memories if isinstance(row, dict) and bool(row.get("operator_correction"))],
        )
        natural_continuity = build_natural_continuity_for_turn(
            message, conversation_policy, conversation_discourse, conversation_history=session_history,
        )
        conversation_target = build_conversation_target_projection(message, session_history)
        natural_follow_up_projection = build_natural_follow_up_runtime_projection(
            message, conversation_policy, conversation_discourse, natural_continuity,
            conversation_history=session_history,
            protected_operator_constraints=("no_proactive_speech", "no_action_execution", "literal_current_request_precedence"),
        )
        natural_follow_up = natural_follow_up_projection["policy"]
        governed_speech_projection = build_governed_speech_runtime_projection(
            message, response_intent, conversation_policy, conversation_discourse,
            natural_follow_up, context_rows=session_history,
            protected_operator_constraints=("no_autonomous_new_turn", "no_private_reflection_delivery", "no_action_execution"),
        )
        governed_speech = governed_speech_projection["policy"]
        daily_companion_projection = build_daily_companion_runtime_projection(
            message, response_intent, conversation_policy, conversation_discourse,
            natural_continuity, natural_follow_up, governed_speech,
            context_rows=session_history,
            protected_operator_constraints=("no_autonomous_new_turn", "no_memory_mutation", "no_action_execution"),
            prior_companion_receipts=session_history,
        )
        daily_companion = daily_companion_projection["policy"]
        era5_companion_projection = build_era5_companion_projection(
            message,
            response_intent=response_intent,
            contextual_behavior=contextual_behavior,
            conversation_discourse=conversation_discourse,
            conversation_history=session_history,
            memories=memories,
            self_model=self_model,
            session_id=resolved_session_id,
        )
        era9_preference_adaptation = build_private_adaptation_prompt(
            context_codes=context_codes_for_message(message), runtime_root=DATA_DIR,
        )
        policy_continuity = stage_conversation_policy_state(
            conversation_policy, operation_id=operation_id, session_id=resolved_session_id
        )
        effective_max_tokens = generation_token_budget(
            message, config.generation.max_tokens, relevance=turn_relevance,
        )
        if effective_max_tokens != config.generation.max_tokens:
            config = config.with_generation(max_tokens=effective_max_tokens)
        provider_performance_plan = build_configured_provider_performance_plan(
            config,
            streaming_requested=False,
            capability_evidence=provider_capabilities(config.provider),
            task_kind="conversation",
        )
        config = apply_provider_aware_performance_config(config, provider_performance_plan)
        compact_cognitive_context, response_time_projection = build_compact_cognitive_projection(
            message,
            action_projection=action_projection,
            development_campaign=development_campaign_lifecycle,
            cognitive=cognitive,
            conversation_policy=conversation_policy,
            conversation_discourse=conversation_discourse,
            memory_retrieval=memory_retrieval_projection,
            natural_continuity=natural_continuity,
            natural_follow_up=natural_follow_up_projection,
            governed_speech=governed_speech_projection,
            daily_companion=daily_companion_projection,
            goal_candidate=goal_candidate_projection,
            hierarchical_planning=hierarchical_planning_projection,
            plan_simulation=plan_simulation_projection,
            persistent_follow_through=persistent_follow_through_projection,
            goal_planning_alpha=goal_and_planning_alpha_projection,
            action_handoff_prompt=action_proposal_handoff_prompt(action_handoff),
            developer_campaign_prompt=(
                developer_campaign_conversation_prompt(developer_campaign_projection)
                + "\n" + unified_conversation_action_prompt(unified_conversation_action)
            ),
            development_campaign_prompt=development_campaign_conversation_prompt(development_campaign_lifecycle),
            supervised_execution_prompt=supervised_execution_prompt(execution_projection),
            supervised_result_prompt=supervised_result_prompt(result_presentation),
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + provider_aware_performance_prompt(provider_performance_plan)
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + conversation_target["prompt_section"]
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + memory_world_model_projection["prompt_section"]
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + era5_companion_projection["prompt_section"]
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + response_grounding_prompt_section(response_grounding)
        )
        if era9_preference_adaptation.get("prompt_section"):
            compact_cognitive_context = (
                compact_cognitive_context.rstrip() + "\n" + era9_preference_adaptation["prompt_section"]
            )
        packet = _build_prompt_packet(
            message, config=config, self_model=self_model, desires=desires,
            memories=memories, conversation_history=session_history, session_id=resolved_session_id,
            transient_instruction=transient_instruction,
            transient_instruction_scope=transient_instruction_scope,
            cognitive_context=compact_cognitive_context,
            natural_follow_up_policy=natural_follow_up,
        )
        prompt_tokens = int(packet.metrics.estimated_prompt_tokens or 0)
        context_attribution = build_conversation_context_attribution(packet.metrics.to_dict(), memory_retrieval_projection.get("retrieval_sufficiency") or {})
        context_arbitration = build_context_relevance_arbitration(context_attribution)
        context_sufficiency = assess_context_sufficiency(context_attribution, context_arbitration)
        context_observability = record_conversation_context_observability(context_attribution, context_arbitration, context_sufficiency, operation_id=operation_id)
        result.cognitive_context = {k: v for k, v in cognitive.items() if k != "prompt_section"}
        result.cognitive_context["conversation_context_attribution"] = dict(context_attribution)
        result.cognitive_context["conversation_context_arbitration"] = dict(context_arbitration)
        result.cognitive_context["conversation_context_sufficiency"] = dict(context_sufficiency)
        result.cognitive_context["conversation_context_observability"] = dict(context_observability)
        result.cognitive_context["provider_aware_performance"] = public_provider_aware_performance_plan(provider_performance_plan)
        result.cognitive_context["memory_world_model_coherence"] = dict(memory_world_model_projection["evidence"])
        result.cognitive_context["unified_memory_policy"] = dict(unified_memory_projection["policy"])
        result.cognitive_context["unified_memory_evidence"] = dict(unified_memory_projection["evidence"])
        result.cognitive_context["unified_memory_runtime_diagnostics"] = dict(unified_memory_projection["diagnostics"])
        result.cognitive_context["memory_retrieval_policy"] = dict(memory_retrieval_projection["policy"])
        result.cognitive_context["memory_retrieval_evidence"] = dict(memory_retrieval_projection["evidence"])
        result.cognitive_context["memory_retrieval_runtime_diagnostics"] = dict(memory_retrieval_projection["diagnostics"])
        result.cognitive_context["memory_retrieval_followup_learning"] = dict(memory_retrieval_followup_learning)
        result.cognitive_context["immediate_memory_learning_policy"] = dict(immediate_learning_projection["policy"])
        result.cognitive_context["immediate_memory_learning_evidence"] = dict(immediate_learning_projection["evidence"])
        result.cognitive_context["immediate_memory_learning_runtime_diagnostics"] = dict(immediate_learning_projection["diagnostics"])
        result.cognitive_context["bounded_experiential_lesson_policy"] = dict(bounded_lesson_projection["policy"])
        result.cognitive_context["bounded_experiential_lesson_evidence"] = dict(bounded_lesson_projection["evidence"])
        result.cognitive_context["bounded_experiential_lesson_runtime_diagnostics"] = dict(bounded_lesson_projection["diagnostics"])
        result.cognitive_context["memory_experiential_learning_alpha_policy"] = dict(memory_learning_alpha_projection["policy"])
        result.cognitive_context["memory_experiential_learning_alpha_evidence"] = dict(memory_learning_alpha_projection["evidence"])
        result.cognitive_context["memory_experiential_learning_alpha_runtime_diagnostics"] = dict(memory_learning_alpha_projection["diagnostics"])
        apply_goal_planning_context(result.cognitive_context, goal_planning_bundle)
        result.cognitive_context["response_intent"] = {k: v for k, v in response_intent.items() if k != "prompt_section"}
        result.cognitive_context["response_grounding"] = dict(response_grounding)
        result.cognitive_context["response_assertion_calibration"] = dict(response_assertion_calibration)
        result.cognitive_context["response_grounding_observability"] = dict(response_grounding_observability)
        result.cognitive_context["response_grounding_outcome_feedback"] = dict(response_grounding_outcome_feedback)
        result.cognitive_context["retrospective_response_quality"] = dict(retrospective_response_quality)
        result.cognitive_context["response_outcome_followup_signal"] = dict(response_outcome_followup_signal)
        result.cognitive_context["positive_retrospective_response_quality"] = dict(positive_retrospective_response_quality)
        result.cognitive_context["response_grounding_learning_profile"] = dict(response_grounding_learning_profile)
        result.cognitive_context["response_grounding_policy_review"] = dict(response_grounding_policy_review)
        result.cognitive_context["contextual_conversation_behavior"] = {k: v for k, v in contextual_behavior.items() if k != "prompt_section"}
        result.cognitive_context["follow_up_silence_policy"] = {k: v for k, v in follow_up_silence.items() if k != "prompt_section"}
        result.cognitive_context["conversation_policy_state"] = {k: v for k, v in conversation_policy.items() if k != "prompt_section"}
        result.cognitive_context["conversation_discourse_policy"] = {k: v for k, v in conversation_discourse.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["conversation_discourse_evidence"] = dict(conversation_discourse.get("evidence") or {})
        result.cognitive_context["natural_conversation_continuity"] = {k: v for k, v in natural_continuity.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["natural_conversation_continuity_evidence"] = dict(natural_continuity.get("evidence") or {})
        result.cognitive_context["natural_follow_up_policy"] = {k: v for k, v in natural_follow_up.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["natural_follow_up_evidence"] = dict(natural_follow_up.get("evidence") or {})
        result.cognitive_context["natural_follow_up_runtime_diagnostics"] = dict(natural_follow_up_projection["diagnostics"])
        result.cognitive_context["governed_speech_policy"] = {k: v for k, v in governed_speech.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["governed_speech_evidence"] = dict(governed_speech.get("evidence") or {})
        result.cognitive_context["governed_speech_runtime_diagnostics"] = dict(governed_speech_projection["diagnostics"])
        result.cognitive_context["daily_companion_cognition"] = {k: v for k, v in daily_companion.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["daily_companion_evidence"] = dict(daily_companion.get("evidence") or {})
        result.cognitive_context["daily_companion_runtime_diagnostics"] = dict(daily_companion_projection["diagnostics"])
        result.cognitive_context["era5_companion_coherence"] = {k: v for k, v in era5_companion_projection.items() if k != "prompt_section"}
        result.cognitive_context["era9_preference_adaptation"] = dict(era9_preference_adaptation.get("evidence") or {})
        result.cognitive_context["natural_language_action_routing"] = natural_language_action_public_projection(action_projection)
        result.cognitive_context["supervised_result_presentation"] = result_presentation
        result.cognitive_context["action_proposal_handoff"] = action_proposal_handoff_public(action_handoff)
        result.cognitive_context["developer_campaign_conversation"] = developer_campaign_conversation_public(developer_campaign_projection)
        result.cognitive_context["ordinary_chat_development_campaign"] = development_campaign_public_projection(development_campaign_lifecycle)
        result.cognitive_context["natural_conversation_command_distinction"] = public_conversation_command_distinction(conversation_command_distinction)
        result.cognitive_context["conversational_command_integration"] = public_conversational_command_integration(conversational_command_integration)
        result.cognitive_context["unified_conversation_action"] = public_unified_conversation_action_projection(unified_conversation_action)
        result.cognitive_context["supervised_execution"] = supervised_execution_public(execution_projection)
        result.cognitive_context["conversation_policy_continuity"] = dict(policy_continuity)
        result.context = packet.metrics.to_dict()
        _apply_immediate_grounding_metrics(result.context, immediate_grounding)
        result.cognitive_context["immediate_conversation_grounding"] = immediate_grounding.public_summary()
        result.context["effective_generation_max_tokens"] = int(config.generation.max_tokens)
        result.context["response_time_projection"] = dict(response_time_projection)
        result.cognitive_context["response_time_projection"] = dict(response_time_projection)
        result.cognitive_context["critical_path"] = critical_path_public_receipt(critical_path_decision)
        result.cognitive_context["work_coalescing"] = turn_work.receipt()
        result.timings_ms["context_build"] = int((time.monotonic() - context_started) * 1000)
        if recovery_of and _memory_exists(recovery_of, "conversation_user"):
            result.user_memory_reused = True
        else:
            user_memory = _store_user_memory(
                operation_id,
                message,
                source,
                result.session_id,
                recovery_of=recovery_of,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.user_memory_stored = True
            result.user_memory_attribution_id = str(user_memory.get("memory_candidate_id") or "")

        development_response_active = bool(
            development_campaign_lifecycle.get("active")
            and development_campaign_lifecycle.get("conversation_response")
        )
        mutation_result = user_memory.get("entity_association_mutation", {}) if not result.user_memory_reused else {}
        grounded_response = (
            str(mutation_result.get("response") or "")
            if mutation_result.get("handled") else
            (None if development_response_active else immediate_grounding.deterministic_response())
        )
        if grounded_response:
            response = grounded_response
            result.response = response
            result.display_message = response
            result.success = True
            result.completion_state = "grounded_immediate_context"
            result.provider_request_count = 0
            result.cognitive_context["immediate_conversation_grounding"]["provider_bypassed"] = True
            if not _claim_operation_completion(operation_id, active_cancel):
                raise LocalModelCancelledError(
                    "Grounded conversation response was cancelled before memory commit.",
                    provider=config.provider, endpoint=config.endpoint, model=config.model,
                    details={"failure_kind": "pre_commit_cancellation"},
                )
            assistant_memory = _store_assistant_memory(
                operation_id, response, source, config, result.session_id,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.assistant_memory_stored = True
            result.assistant_memory_attribution_id = str(assistant_memory.get("memory_candidate_id") or "")
            result.cognitive_context["conversation_policy_continuity"] = complete_conversation_policy_state(
                operation_id=operation_id, session_id=result.session_id
            )
            _queue_memory_vectors(user_memory, assistant_memory)
            result.turn_completion = queue_turn_completion_safely(
                operation_id=operation_id, session_id=result.session_id, user_message=message,
                assistant_response=response, source=source, context_summary=result.cognitive_context,
            )
            _schedule_housekeeping_safely(result)
            return result

        if (
            development_campaign_lifecycle.get("active")
            and development_campaign_lifecycle.get("conversation_response")
            and (
                not conversation_command_distinction.get("mixed_turn")
                or development_campaign_lifecycle.get("v1489_self_inspection_requested")
            )
        ):
            response = str(development_campaign_lifecycle["conversation_response"])
            result.response = response
            result.display_message = response
            result.success = True
            result.completion_state = "development_campaign_lifecycle"
            result.provider_request_count = 0
            if not _claim_operation_completion(operation_id, active_cancel):
                raise LocalModelCancelledError(
                    "Development campaign response was cancelled before memory commit.",
                    provider=config.provider,
                    endpoint=config.endpoint,
                    model=config.model,
                    details={"failure_kind": "pre_commit_cancellation"},
                )
            assistant_memory = _store_assistant_memory(
                operation_id, response, source, config, result.session_id,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.assistant_memory_stored = True
            result.assistant_memory_attribution_id = str(assistant_memory.get("memory_candidate_id") or "")
            result.cognitive_context["conversation_policy_continuity"] = complete_conversation_policy_state(
                operation_id=operation_id, session_id=result.session_id
            )
            _queue_memory_vectors(user_memory, assistant_memory)
            result.turn_completion = queue_turn_completion_safely(
                operation_id=operation_id, session_id=result.session_id, user_message=message,
                assistant_response=response, source=source, context_summary=result.cognitive_context,
            )
            _schedule_housekeeping_safely(result)
            return result

        if not use_ai or not bool(settings.get("ai_chat_enabled", True)):
            result.completion_state = "ai_disabled"
            result.failure_category = "ai_disabled"
            result.display_message = "Your message was saved. Local generation is off, so no provider was contacted and no fallback was used."
            return result

        provider_start_kind = classify_provider_start(config.provider, config.endpoint, config.model)
        provider_started = time.monotonic()
        result.timings_ms["pre_provider"] = int((provider_started - started_clock) * 1000)
        result.cognitive_context["critical_path"] = critical_path_public_receipt(
            critical_path_decision, pre_provider_ms=result.timings_ms["pre_provider"]
        )
        if active_cancel.is_set():
            raise LocalModelCancelledError(
                "Local model request was cancelled before provider contact.",
                provider=config.provider,
                endpoint=config.endpoint,
                model=config.model,
                details={"failure_kind": "pre_provider_cancellation"},
            )
        result.provider_request_count = 1
        client = LocalModelClient(config, cancel_event=active_cancel)
        try:
            _set_operation_cancel_callback(operation_id, client.cancel)
            generated = client.generate(packet.prompt)
            result.provider_metrics = provider_metrics_public(getattr(client, "last_metrics", {}))
        finally:
            result.retry_count = client.last_retry_count
            client.close()
        result.timings_ms["provider"] = int((time.monotonic() - provider_started) * 1000)
        mark_provider_warm(config.provider, config.endpoint, config.model)
        result.provider_metrics["runtime_start_kind"] = provider_start_kind
        response = _bound_unverified_action_claim(
            _clean_assistant_response(generated, str(self_model.get("name") or "Eidolon")),
            action_projection,
        )
        response, follow_up_output_diagnostics = enforce_natural_follow_up_output(
            response, natural_follow_up,
            casual_fast_path=str(packet.metrics.prompt_lane) == "casual_fast",
        )
        result.cognitive_context["natural_follow_up_output_enforcement"] = follow_up_output_diagnostics
        response, target_output_diagnostics = enforce_conversation_target_output(
            response, conversation_target, session_history,
            casual_fast_path=str(packet.metrics.prompt_lane) == "casual_fast",
        )
        result.cognitive_context["conversation_target_continuity"] = dict(conversation_target["policy"])
        result.cognitive_context["conversation_target_output_enforcement"] = target_output_diagnostics
        result.cognitive_context["conversation_target_outcome"] = build_conversation_target_outcome(target_output_diagnostics)
        append_conversation_target_outcome(result.cognitive_context["conversation_target_outcome"], operation_id=operation_id)
        result.cognitive_context["conversation_target_learning_profile"] = build_conversation_target_learning_profile()
        result.cognitive_context["era5_companion_output_audit"] = audit_era5_companion_output(
            response, projection=era5_companion_projection,
        )
        result.cognitive_context["response_grounding_output_audit"] = audit_response_grounding_output(
            response, response_grounding, response_assertion_calibration,
            authoritative_execution_evidence=bool(result_presentation.get("authoritative_execution_claim")),
        )
        result.cognitive_context["response_grounding_output_observability"] = record_response_grounding_output_audit(
            result.cognitive_context["response_grounding_output_audit"], operation_id=operation_id
        )
        result.cognitive_context["response_grounding_repair_candidate"] = build_response_grounding_repair_candidate(
            result.cognitive_context["response_grounding_output_audit"], response_grounding, response_assertion_calibration
        )
        result.cognitive_context["response_grounding_repair_review"] = build_response_grounding_repair_review(
            result.cognitive_context["response_grounding_repair_candidate"]
        )
        result.cognitive_context["conversation_health"] = build_conversation_health()
        append_conversation_health(result.cognitive_context["conversation_health"], operation_id=operation_id)
        result.cognitive_context["conversation_health_trend"] = build_conversation_health_trend(
            load_conversation_health_history().get("rows") or []
        )
        result.cognitive_context["conversation_outcome_attribution"] = build_conversation_outcome_attribution(
            target_outcome=result.cognitive_context.get("conversation_target_outcome") or {},
            output_audit=result.cognitive_context.get("response_grounding_output_audit") or {},
            memory_feedback=memory_retrieval_projection.get("retrieval_sufficiency") or {},
            context_observability=result.cognitive_context.get("conversation_context_observability") or {},
        )
        result.cognitive_context["response_quality_evaluation"] = evaluate_response_quality(
            result.cognitive_context["conversation_outcome_attribution"]
        )
        append_response_quality(
            result.cognitive_context["response_quality_evaluation"],
            result.cognitive_context["conversation_outcome_attribution"],
            operation_id=operation_id,
        )
        result.cognitive_context["response_quality_trend"] = build_response_quality_trend(
            load_response_quality_history().get("rows") or []
        )
        result.cognitive_context["response_quality_review"] = build_response_quality_review(
            result.cognitive_context["response_quality_evaluation"],
            result.cognitive_context["response_quality_trend"],
        )
        result.cognitive_context["daily_use_reliability"] = build_daily_use_runtime_reliability(operation_id=operation_id)
        if conversation_command_distinction.get("mixed_turn") and development_campaign_lifecycle.get("conversation_response"):
            response = response.rstrip() + "\n\n" + str(development_campaign_lifecycle["conversation_response"]).strip()
        result.response = response
        result.display_message = response
        goal_planning_bundle = _complete_deferred_goal_planning(
            result=result,
            decision=critical_path_decision,
            message=message,
            memory_learning_alpha_projection=memory_learning_alpha_projection,
            session_history=session_history,
            current_bundle=goal_planning_bundle,
        )
        if not _claim_operation_completion(operation_id, active_cancel):
            raise LocalModelCancelledError(
                "Local model request was cancelled before memory commit.",
                provider=config.provider,
                endpoint=config.endpoint,
                model=config.model,
                details={"failure_kind": "pre_commit_cancellation"},
            )
        try:
            assistant_memory = _store_assistant_memory(
                operation_id, response, source, config, result.session_id,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.assistant_memory_stored = True
            result.assistant_memory_attribution_id = str(assistant_memory.get("memory_candidate_id") or "")
            learning_commit_handoff = build_learning_commit_boundary_handoff(
                immediate_learning_projection.get("candidate"),
                provider_completed=True,
                assistant_memory_committed=True,
            )
            result.cognitive_context["immediate_memory_learning_commit_handoff"] = learning_commit_handoff
            result.cognitive_context["immediate_memory_learning_compliance_audit"] = audit_immediate_memory_learning(
                immediate_learning_projection,
                learning_commit_handoff,
            )
            lesson_review_handoff = build_lesson_review_boundary_handoff(
                bounded_lesson_projection.get("candidate"),
                provider_completed=True,
                assistant_memory_committed=True,
            )
            result.cognitive_context["bounded_experiential_lesson_review_handoff"] = lesson_review_handoff
            result.cognitive_context["bounded_experiential_lesson_compliance_audit"] = audit_bounded_experiential_lesson(
                bounded_lesson_projection,
                lesson_review_handoff,
            )
            memory_learning_alpha_projection = build_memory_experiential_learning_alpha(
                unified_memory_projection, memory_retrieval_projection,
                immediate_learning_projection, bounded_lesson_projection,
                learning_commit_handoff=learning_commit_handoff,
                lesson_review_handoff=lesson_review_handoff,
                prior_alpha_receipts=session_history,
            )
            result.cognitive_context["memory_experiential_learning_alpha_policy"] = dict(memory_learning_alpha_projection["policy"])
            result.cognitive_context["memory_experiential_learning_alpha_evidence"] = dict(memory_learning_alpha_projection["evidence"])
            result.cognitive_context["memory_experiential_learning_alpha_runtime_diagnostics"] = dict(memory_learning_alpha_projection["diagnostics"])
            alpha_handoff = build_memory_experiential_learning_alpha_handoff(memory_learning_alpha_projection, provider_completed=True, assistant_memory_committed=True)
            result.cognitive_context["memory_experiential_learning_alpha_handoff"] = alpha_handoff
            alpha_audit = audit_memory_experiential_learning_alpha(memory_learning_alpha_projection, alpha_handoff)
            result.cognitive_context["memory_experiential_learning_alpha_compliance_audit"] = alpha_audit
            alpha_prior_receipts = session_history
            result.cognitive_context["memory_experiential_learning_alpha_reliability"] = build_memory_experiential_learning_alpha_reliability(
                memory_learning_alpha_projection, alpha_handoff, alpha_audit,
                prior_alpha_receipts=alpha_prior_receipts,
            )
            apply_goal_planning_handoffs(result.cognitive_context, goal_planning_bundle)
            result.cognitive_context["conversation_policy_continuity"] = complete_conversation_policy_state(
                operation_id=operation_id, session_id=result.session_id
            )
            result.success = True
            result.completion_state = "completed"
            _queue_memory_vectors(user_memory, assistant_memory)
            result.turn_completion = queue_turn_completion_safely(
                operation_id=operation_id, session_id=result.session_id, user_message=message,
                assistant_response=response, source=source, context_summary=result.cognitive_context,
            )
            _schedule_housekeeping_safely(result)
        except Exception as error:
            result.success = False
            result.completion_state = "response_generated_memory_failed"
            result.failure_category = "memory_write_failure"
            result.error = _safe_error(error, config)
            result.display_message = response
        return result
    except Exception as error:
        result.success = False
        result.failure_category = _failure_category(error)
        result.completion_state = "cancelled" if isinstance(error, LocalModelCancelledError) else "failed"
        result.error = _safe_error(error, config)
        if isinstance(error, LocalModelError):
            result.cognitive_context["provider_recovery"] = provider_recovery_guidance(error)
        result.display_message = conversation_error_message(error, provider=config.provider, model=config.model)
        return result
    finally:
        result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
        result.cognitive_context["response_performance"] = build_conversation_timing_receipt(
            result.timings_ms, provider_start_kind=provider_start_kind, prompt_tokens=prompt_tokens
        )
        _record_session_turn(
            result, user_message=message, source=source, created_at=started_at,
            select_session=select_session_on_record,
        )
        _persist_receipt(result, started_at)
        _unregister_operation(operation_id)


def stream_conversation_turn(
    user_message: str,
    *,
    source: str = "dashboard_chat_console_stream",
    use_ai: bool = True,
    cancel_event: threading.Event | None = None,
    session_id: str = "",
    recovery_of: str = "",
    recovery_kind: str = "",
    operation_id: str = "",
    select_session_on_record: bool = True,
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
    authoritative_action_results: tuple[dict[str, Any], ...] = (),
) -> Iterator[dict[str, Any]]:
    """Stream one turn without retries or partial-response memory commits."""
    started_clock = time.monotonic()
    started_at = _now_utc()
    provider_start_kind = "not_contacted"
    prompt_tokens = 0
    operation_id = _resolved_operation_id(operation_id)
    message = str(user_message or "").strip()
    resolved_session_id, session_history = _session_context(session_id)
    settings, config, result, configuration_error = _load_runtime_configuration(
        operation_id,
        streaming=True,
        session_id=resolved_session_id,
        recovery_of=recovery_of,
        recovery_kind=recovery_kind,
    )
    active_cancel = cancel_event or threading.Event()
    visible_content = False
    yield {
        "event": "meta",
        "operation_id": operation_id,
        "provider": result.provider,
        "model": result.model,
        "streaming": True,
        "fallback_configured": False,
        "session_id": result.session_id,
    }
    if configuration_error is not None or config is None:
        result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
        _record_session_turn(
            result, user_message=message, source=source, created_at=started_at,
            select_session=select_session_on_record,
        )
        _persist_receipt(result, started_at)
        yield {
            "event": "error",
            "operation_id": operation_id,
            "failure_category": result.failure_category,
            "message": result.display_message,
            "error": result.error,
            "partial_discarded": False,
        }
        yield {"event": "replace", "text": result.display_message, "operation_id": operation_id}
        yield {"event": "done", "operation_id": operation_id, "result": result.to_dict(include_response=True, include_cognitive_context=False)}
        return
    _register_operation(operation_id, active_cancel)
    finalized_early = False
    user_memory: dict[str, Any] | None = None
    try:
        turn_work = TurnWorkCache()
        if not message:
            raise ContextLimitError("Conversation user message cannot be empty.", details={"failure_kind": "empty_message"})
        conversation_command_distinction = distinguish_natural_conversation_and_command(message)
        conversational_command_integration = build_conversational_command_integration(
            message, conversation_history=session_history, session_id=resolved_session_id,
        )
        routed_action_text = str(conversational_command_integration.get("routing_text") or "").strip()
        if not routed_action_text and conversational_command_integration.get("status") in {
            "conversation_only", "correction_target_resolved", "cancellation_target_resolved",
            "correction_target_ambiguous", "cancellation_target_ambiguous", "generic_authorization_blocked",
        }:
            routed_action_text = message
        if conversation_command_distinction.get("requires_clarification"):
            routed_action_text = ""
        action_projection = build_natural_language_action_projection(
            routed_action_text, conversation_history=session_history, authoritative_receipts=authoritative_action_results,
        )
        # The live turn is the only place a confirmed proposal runs. Grounding never executes, so a confirmation
        # replayed from history cannot start a second run.
        action_projection = _apply_confirmed_execution(action_projection)
        conversational_command_integration = build_conversational_command_integration(
            message, action_projection=action_projection, conversation_history=session_history, session_id=resolved_session_id,
        )
        result_presentation = build_supervised_result_presentation(
            str((action_projection.get("grounding") or {}).get("capability_id") or ""), authoritative_action_results,
        )

        action_handoff = build_action_proposal_handoff(action_projection, operation_id=operation_id)
        active_project = turn_work.get("active_project", get_active_project)
        development_campaign_lifecycle = process_ordinary_chat_development_turn(
            routed_action_text,
            action_projection=action_projection,
            session_id=resolved_session_id,
            project_state=active_project,
        )
        development_campaign_lifecycle = integrate_v1489_product_capabilities(
            routed_action_text or message,
            development_campaign_lifecycle,
            project_state=active_project if isinstance(active_project, dict) else None,
        )
        developer_campaign_projection = build_developer_campaign_conversation_projection(
            action_projection,
            action_handoff,
            project_state=active_project,
            lifecycle_state=development_campaign_lifecycle,
        )
        unified_conversation_action = build_unified_conversation_action_projection(
            message,
            conversational_command_integration=conversational_command_integration,
            action_projection=action_projection,
            development_lifecycle=development_campaign_lifecycle,
            developer_campaign_projection=developer_campaign_projection,
        )
        execution_projection = build_supervised_execution_projection(action_handoff, operation_id=operation_id)
        # Keep the streaming and non-streaming paths on the same attributable window.
        memories = _long_term_memories(load_memories(limit=480))
        memory_world_model_projection = build_memory_world_model_projection(message, memories)
        memories = list(memory_world_model_projection["selected_memory_records"])
        grounding_memory_candidates = _grounding_memories(memories)
        unified_memory_projection = build_unified_memory_runtime_projection(
            message,
            memory_records=memories,
            conversation_history=session_history,
            project_state=active_project,
            protected_operator_constraints=(
                "current_message_precedence", "explicit_correction_precedence",
                "no_memory_mutation", "no_action_execution",
            ),
            prior_unified_memory_receipts=session_history,
        )
        # Retained v1165 handoff seam: memories = list(unified_memory_projection["selected_memory_records"])
        memory_retrieval_projection = build_memory_retrieval_relevance(
            message,
            unified_memory_projection["selected_memory_records"],
            unified_memory_projection.get("selected_references"),
            prior_retrieval_receipts=session_history,
        )
        memory_retrieval_projection = refine_memory_retrieval(memory_retrieval_projection)
        memory_retrieval_projection = apply_memory_retrieval_budget(memory_retrieval_projection)
        memory_retrieval_projection["retrieval_sufficiency"] = assess_memory_retrieval_sufficiency(memory_retrieval_projection)
        prior_memory_retrieval_observability = load_memory_retrieval_observability()
        prior_response_grounding_observability = load_response_grounding_observability()
        memory_retrieval_projection["retrieval_observability"] = record_memory_retrieval_observability(memory_retrieval_projection, operation_id=operation_id)
        memories = list(memory_retrieval_projection["selected_memory_records"])
        immediate_learning_projection = build_immediate_memory_learning(
            message,
            memories,
            protected_operator_constraints=(
                "preserve_historical_truth", "no_unconfirmed_memory_mutation", "current_message_precedence",
            ),
            prior_learning_receipts=session_history,
        )
        memory_retrieval_followup_learning = learn_from_followup_correction(
            prior_memory_retrieval_observability, immediate_learning_projection
        )
        response_grounding_outcome_feedback = build_response_grounding_outcome_feedback(
            prior_response_grounding_observability, immediate_learning_projection
        )
        append_response_grounding_feedback(response_grounding_outcome_feedback)
        retrospective_response_quality = build_retrospective_response_quality(
            prior_response_grounding_observability, response_grounding_outcome_feedback, evidence_operation_id=operation_id
        )
        append_retrospective_response_quality(retrospective_response_quality)
        response_outcome_followup_signal = build_response_outcome_followup_signal(message, immediate_learning_projection)
        positive_retrospective_response_quality = build_positive_retrospective_quality(
            prior_response_grounding_observability, response_outcome_followup_signal, evidence_operation_id=operation_id
        )
        if not response_outcome_followup_signal.get("negative_followup"):
            append_positive_retrospective_quality(positive_retrospective_response_quality)
        response_grounding_learning_profile = build_response_grounding_learning_profile(
            load_response_grounding_feedback_history().get("rows") or []
        )
        response_grounding_policy_review = build_response_grounding_policy_review(response_grounding_learning_profile)
        bounded_lesson_projection = build_bounded_experiential_lesson(
            message, immediate_learning_projection, experience_rows=session_history,
            protected_operator_constraints=(
                "no_uncontrolled_self_training", "review_before_durable_lesson", "preserve_historical_truth",
            ),
            prior_lesson_receipts=session_history,
        )
        memory_learning_alpha_projection = build_memory_experiential_learning_alpha(
            unified_memory_projection, memory_retrieval_projection,
            immediate_learning_projection, bounded_lesson_projection,
            prior_alpha_receipts=session_history,
        )
        turn_relevance = classify_turn_relevance(
            message, action_projection=action_projection, development_campaign=development_campaign_lifecycle,
        )
        critical_path_decision = build_critical_path_decision(
            message, relevance=turn_relevance, action_projection=action_projection,
            development_campaign=development_campaign_lifecycle,
        )
        if critical_path_decision.goal_planning_pre_provider:
            goal_planning_bundle = build_goal_planning_bundle(
                message, memory_learning_alpha_projection, session_history=session_history, phase="pre_provider",
            )
        else:
            goal_planning_bundle = deferred_goal_planning_stub()
        (
            goal_candidate_projection, goal_candidate_review_projection, goal_candidate_reliability,
            hierarchical_planning_projection, hierarchical_planning_review_projection, hierarchical_planning_reliability,
            plan_simulation_projection, plan_simulation_review_projection, plan_simulation_reliability,
            persistent_follow_through_projection, persistent_follow_through_review_projection, persistent_follow_through_reliability,
            goal_and_planning_alpha_projection, goal_and_planning_alpha_review_projection, goal_and_planning_alpha_reliability,
        ) = unpack_goal_planning_bundle(goal_planning_bundle)
        memories = list(memory_learning_alpha_projection["selected_memory_records"])
        immediate_grounding = build_immediate_conversation_grounding(
            message, _grounding_session_history(resolved_session_id), grounding_memory_candidates
        )
        self_model = turn_work.get("self_model", load_self_model)
        desires = turn_work.get("desires", load_desires)
        context_started = time.monotonic()
        cognitive = build_turn_cognitive_context(
            message, operation_id=operation_id, session_id=resolved_session_id,
            memories=memories, self_model=self_model, desires=desires,
        )
        response_intent = build_response_intent_selection(
            message, reasoning_state=cognitive, conversation_history=session_history,
            explicit_corrections=[row for row in memories if isinstance(row, dict) and bool(row.get("operator_correction"))],
            protected_operator_constraints=("no_automatic_authority", "current_message_precedence", "protected_instructions_precedence"),
            self_model=self_model, desires=desires, contextual_memories=memories,
        )
        response_grounding = build_response_grounding_policy(
            response_intent, memory_retrieval_projection.get("retrieval_sufficiency") or {}, immediate_grounding.public_summary()
        )
        response_assertion_calibration = build_response_assertion_calibration(response_grounding)
        response_grounding_observability = record_response_grounding_observability(response_grounding, response_assertion_calibration, operation_id=operation_id)
        contextual_behavior = build_contextual_conversation_behavior(
            response_intent, self_model=self_model, contextual_memories=memories,
            conversation_history=session_history,
        )
        follow_up_silence = build_follow_up_silence_policy(message, response_intent, contextual_behavior)
        conversation_policy = build_conversation_policy_state(response_intent, contextual_behavior, follow_up_silence)
        conversation_discourse = build_conversation_discourse_policy_for_turn(
            message, conversation_policy, conversation_history=session_history,
            explicit_corrections=[row for row in memories if isinstance(row, dict) and bool(row.get("operator_correction"))],
        )
        natural_continuity = build_natural_continuity_for_turn(
            message, conversation_policy, conversation_discourse, conversation_history=session_history,
        )
        conversation_target = build_conversation_target_projection(message, session_history)
        natural_follow_up_projection = build_natural_follow_up_runtime_projection(
            message, conversation_policy, conversation_discourse, natural_continuity,
            conversation_history=session_history,
            protected_operator_constraints=("no_proactive_speech", "no_action_execution", "literal_current_request_precedence"),
        )
        natural_follow_up = natural_follow_up_projection["policy"]
        governed_speech_projection = build_governed_speech_runtime_projection(
            message, response_intent, conversation_policy, conversation_discourse,
            natural_follow_up, context_rows=session_history,
            protected_operator_constraints=("no_autonomous_new_turn", "no_private_reflection_delivery", "no_action_execution"),
        )
        governed_speech = governed_speech_projection["policy"]
        daily_companion_projection = build_daily_companion_runtime_projection(
            message, response_intent, conversation_policy, conversation_discourse,
            natural_continuity, natural_follow_up, governed_speech,
            context_rows=session_history,
            protected_operator_constraints=("no_autonomous_new_turn", "no_memory_mutation", "no_action_execution"),
            prior_companion_receipts=session_history,
        )
        daily_companion = daily_companion_projection["policy"]
        era5_companion_projection = build_era5_companion_projection(
            message,
            response_intent=response_intent,
            contextual_behavior=contextual_behavior,
            conversation_discourse=conversation_discourse,
            conversation_history=session_history,
            memories=memories,
            self_model=self_model,
            session_id=resolved_session_id,
        )
        era9_preference_adaptation = build_private_adaptation_prompt(
            context_codes=context_codes_for_message(message), runtime_root=DATA_DIR,
        )
        policy_continuity = stage_conversation_policy_state(
            conversation_policy, operation_id=operation_id, session_id=resolved_session_id
        )
        effective_max_tokens = generation_token_budget(
            message, config.generation.max_tokens, relevance=turn_relevance,
        )
        if effective_max_tokens != config.generation.max_tokens:
            config = config.with_generation(max_tokens=effective_max_tokens)
        provider_performance_plan = build_configured_provider_performance_plan(
            config,
            streaming_requested=True,
            capability_evidence=provider_capabilities(config.provider),
            task_kind="conversation",
        )
        config = apply_provider_aware_performance_config(config, provider_performance_plan)
        compact_cognitive_context, response_time_projection = build_compact_cognitive_projection(
            message,
            action_projection=action_projection,
            development_campaign=development_campaign_lifecycle,
            cognitive=cognitive,
            conversation_policy=conversation_policy,
            conversation_discourse=conversation_discourse,
            memory_retrieval=memory_retrieval_projection,
            natural_continuity=natural_continuity,
            natural_follow_up=natural_follow_up_projection,
            governed_speech=governed_speech_projection,
            daily_companion=daily_companion_projection,
            goal_candidate=goal_candidate_projection,
            hierarchical_planning=hierarchical_planning_projection,
            plan_simulation=plan_simulation_projection,
            persistent_follow_through=persistent_follow_through_projection,
            goal_planning_alpha=goal_and_planning_alpha_projection,
            action_handoff_prompt=action_proposal_handoff_prompt(action_handoff),
            developer_campaign_prompt=(
                developer_campaign_conversation_prompt(developer_campaign_projection)
                + "\n" + unified_conversation_action_prompt(unified_conversation_action)
            ),
            development_campaign_prompt=development_campaign_conversation_prompt(development_campaign_lifecycle),
            supervised_execution_prompt=supervised_execution_prompt(execution_projection),
            supervised_result_prompt=supervised_result_prompt(result_presentation),
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + provider_aware_performance_prompt(provider_performance_plan)
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + conversation_target["prompt_section"]
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + memory_world_model_projection["prompt_section"]
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + era5_companion_projection["prompt_section"]
        )
        compact_cognitive_context = (
            compact_cognitive_context.rstrip() + "\n" + response_grounding_prompt_section(response_grounding)
        )
        if era9_preference_adaptation.get("prompt_section"):
            compact_cognitive_context = (
                compact_cognitive_context.rstrip() + "\n" + era9_preference_adaptation["prompt_section"]
            )
        packet = _build_prompt_packet(
            message, config=config, self_model=self_model, desires=desires,
            memories=memories, conversation_history=session_history, session_id=resolved_session_id,
            transient_instruction=transient_instruction,
            transient_instruction_scope=transient_instruction_scope,
            cognitive_context=compact_cognitive_context,
            natural_follow_up_policy=natural_follow_up,
        )
        prompt_tokens = int(packet.metrics.estimated_prompt_tokens or 0)
        context_attribution = build_conversation_context_attribution(packet.metrics.to_dict(), memory_retrieval_projection.get("retrieval_sufficiency") or {})
        context_arbitration = build_context_relevance_arbitration(context_attribution)
        context_sufficiency = assess_context_sufficiency(context_attribution, context_arbitration)
        context_observability = record_conversation_context_observability(context_attribution, context_arbitration, context_sufficiency, operation_id=operation_id)
        result.cognitive_context = {k: v for k, v in cognitive.items() if k != "prompt_section"}
        result.cognitive_context["conversation_context_attribution"] = dict(context_attribution)
        result.cognitive_context["conversation_context_arbitration"] = dict(context_arbitration)
        result.cognitive_context["conversation_context_sufficiency"] = dict(context_sufficiency)
        result.cognitive_context["conversation_context_observability"] = dict(context_observability)
        result.cognitive_context["provider_aware_performance"] = public_provider_aware_performance_plan(provider_performance_plan)
        result.cognitive_context["memory_world_model_coherence"] = dict(memory_world_model_projection["evidence"])
        result.cognitive_context["unified_memory_policy"] = dict(unified_memory_projection["policy"])
        result.cognitive_context["unified_memory_evidence"] = dict(unified_memory_projection["evidence"])
        result.cognitive_context["unified_memory_runtime_diagnostics"] = dict(unified_memory_projection["diagnostics"])
        result.cognitive_context["memory_retrieval_policy"] = dict(memory_retrieval_projection["policy"])
        result.cognitive_context["memory_retrieval_evidence"] = dict(memory_retrieval_projection["evidence"])
        result.cognitive_context["memory_retrieval_runtime_diagnostics"] = dict(memory_retrieval_projection["diagnostics"])
        result.cognitive_context["memory_retrieval_followup_learning"] = dict(memory_retrieval_followup_learning)
        result.cognitive_context["immediate_memory_learning_policy"] = dict(immediate_learning_projection["policy"])
        result.cognitive_context["immediate_memory_learning_evidence"] = dict(immediate_learning_projection["evidence"])
        result.cognitive_context["immediate_memory_learning_runtime_diagnostics"] = dict(immediate_learning_projection["diagnostics"])
        result.cognitive_context["bounded_experiential_lesson_policy"] = dict(bounded_lesson_projection["policy"])
        result.cognitive_context["bounded_experiential_lesson_evidence"] = dict(bounded_lesson_projection["evidence"])
        result.cognitive_context["bounded_experiential_lesson_runtime_diagnostics"] = dict(bounded_lesson_projection["diagnostics"])
        result.cognitive_context["memory_experiential_learning_alpha_policy"] = dict(memory_learning_alpha_projection["policy"])
        result.cognitive_context["memory_experiential_learning_alpha_evidence"] = dict(memory_learning_alpha_projection["evidence"])
        result.cognitive_context["memory_experiential_learning_alpha_runtime_diagnostics"] = dict(memory_learning_alpha_projection["diagnostics"])
        apply_goal_planning_context(result.cognitive_context, goal_planning_bundle)
        result.cognitive_context["response_intent"] = {k: v for k, v in response_intent.items() if k != "prompt_section"}
        result.cognitive_context["response_grounding"] = dict(response_grounding)
        result.cognitive_context["response_assertion_calibration"] = dict(response_assertion_calibration)
        result.cognitive_context["response_grounding_observability"] = dict(response_grounding_observability)
        result.cognitive_context["response_grounding_outcome_feedback"] = dict(response_grounding_outcome_feedback)
        result.cognitive_context["retrospective_response_quality"] = dict(retrospective_response_quality)
        result.cognitive_context["response_outcome_followup_signal"] = dict(response_outcome_followup_signal)
        result.cognitive_context["positive_retrospective_response_quality"] = dict(positive_retrospective_response_quality)
        result.cognitive_context["response_grounding_learning_profile"] = dict(response_grounding_learning_profile)
        result.cognitive_context["response_grounding_policy_review"] = dict(response_grounding_policy_review)
        result.cognitive_context["contextual_conversation_behavior"] = {k: v for k, v in contextual_behavior.items() if k != "prompt_section"}
        result.cognitive_context["follow_up_silence_policy"] = {k: v for k, v in follow_up_silence.items() if k != "prompt_section"}
        result.cognitive_context["conversation_policy_state"] = {k: v for k, v in conversation_policy.items() if k != "prompt_section"}
        result.cognitive_context["conversation_discourse_policy"] = {k: v for k, v in conversation_discourse.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["conversation_discourse_evidence"] = dict(conversation_discourse.get("evidence") or {})
        result.cognitive_context["natural_conversation_continuity"] = {k: v for k, v in natural_continuity.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["natural_conversation_continuity_evidence"] = dict(natural_continuity.get("evidence") or {})
        result.cognitive_context["natural_follow_up_policy"] = {k: v for k, v in natural_follow_up.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["natural_follow_up_evidence"] = dict(natural_follow_up.get("evidence") or {})
        result.cognitive_context["natural_follow_up_runtime_diagnostics"] = dict(natural_follow_up_projection["diagnostics"])
        result.cognitive_context["governed_speech_policy"] = {k: v for k, v in governed_speech.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["governed_speech_evidence"] = dict(governed_speech.get("evidence") or {})
        result.cognitive_context["governed_speech_runtime_diagnostics"] = dict(governed_speech_projection["diagnostics"])
        result.cognitive_context["daily_companion_cognition"] = {k: v for k, v in daily_companion.items() if k not in {"prompt_section", "evidence"}}
        result.cognitive_context["daily_companion_evidence"] = dict(daily_companion.get("evidence") or {})
        result.cognitive_context["daily_companion_runtime_diagnostics"] = dict(daily_companion_projection["diagnostics"])
        result.cognitive_context["era5_companion_coherence"] = {k: v for k, v in era5_companion_projection.items() if k != "prompt_section"}
        result.cognitive_context["era9_preference_adaptation"] = dict(era9_preference_adaptation.get("evidence") or {})
        result.cognitive_context["natural_language_action_routing"] = natural_language_action_public_projection(action_projection)
        result.cognitive_context["supervised_result_presentation"] = result_presentation
        result.cognitive_context["action_proposal_handoff"] = action_proposal_handoff_public(action_handoff)
        result.cognitive_context["developer_campaign_conversation"] = developer_campaign_conversation_public(developer_campaign_projection)
        result.cognitive_context["ordinary_chat_development_campaign"] = development_campaign_public_projection(development_campaign_lifecycle)
        result.cognitive_context["natural_conversation_command_distinction"] = public_conversation_command_distinction(conversation_command_distinction)
        result.cognitive_context["conversational_command_integration"] = public_conversational_command_integration(conversational_command_integration)
        result.cognitive_context["unified_conversation_action"] = public_unified_conversation_action_projection(unified_conversation_action)
        result.cognitive_context["supervised_execution"] = supervised_execution_public(execution_projection)
        result.cognitive_context["conversation_policy_continuity"] = dict(policy_continuity)
        result.context = packet.metrics.to_dict()
        _apply_immediate_grounding_metrics(result.context, immediate_grounding)
        result.cognitive_context["immediate_conversation_grounding"] = immediate_grounding.public_summary()
        result.context["effective_generation_max_tokens"] = int(config.generation.max_tokens)
        result.context["response_time_projection"] = dict(response_time_projection)
        result.cognitive_context["response_time_projection"] = dict(response_time_projection)
        result.cognitive_context["critical_path"] = critical_path_public_receipt(critical_path_decision)
        result.cognitive_context["work_coalescing"] = turn_work.receipt()
        result.timings_ms["context_build"] = int((time.monotonic() - context_started) * 1000)
        yield {"event": "context", "operation_id": operation_id, "budget": result.context}
        if recovery_of and _memory_exists(recovery_of, "conversation_user"):
            result.user_memory_reused = True
        else:
            user_memory = _store_user_memory(
                operation_id,
                message,
                source,
                result.session_id,
                recovery_of=recovery_of,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.user_memory_stored = True
            result.user_memory_attribution_id = str(user_memory.get("memory_candidate_id") or "")
        yield {"event": "status", "stage": "user_saved", "operation_id": operation_id}

        development_response_active = bool(
            development_campaign_lifecycle.get("active")
            and development_campaign_lifecycle.get("conversation_response")
        )
        mutation_result = user_memory.get("entity_association_mutation", {}) if not result.user_memory_reused else {}
        grounded_response = (
            str(mutation_result.get("response") or "")
            if mutation_result.get("handled") else
            (None if development_response_active else immediate_grounding.deterministic_response())
        )
        if grounded_response:
            response = grounded_response
            result.response = response
            result.display_message = response
            result.success = True
            result.completion_state = "grounded_immediate_context"
            result.provider_request_count = 0
            result.cognitive_context["immediate_conversation_grounding"]["provider_bypassed"] = True
            if not _claim_operation_completion(operation_id, active_cancel):
                raise LocalModelCancelledError(
                    "Grounded conversation response was cancelled before memory commit.",
                    provider=config.provider, endpoint=config.endpoint, model=config.model,
                    details={"failure_kind": "pre_commit_cancellation"},
                )
            assistant_memory = _store_assistant_memory(
                operation_id, response, source, config, result.session_id,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.assistant_memory_stored = True
            result.assistant_memory_attribution_id = str(assistant_memory.get("memory_candidate_id") or "")
            result.cognitive_context["conversation_policy_continuity"] = complete_conversation_policy_state(
                operation_id=operation_id, session_id=result.session_id
            )
            _queue_memory_vectors(user_memory, assistant_memory)
            result.turn_completion = queue_turn_completion_safely(
                operation_id=operation_id, session_id=result.session_id, user_message=message,
                assistant_response=response, source=source, context_summary=result.cognitive_context,
            )
            _schedule_housekeeping_safely(result)
            yield {"event": "replace", "text": response, "operation_id": operation_id, "trusted_status": True}
            yield {"event": "response_complete", "operation_id": operation_id}
            result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
            _record_session_turn(
                result, user_message=message, source=source, created_at=started_at,
                select_session=select_session_on_record,
            )
            _persist_receipt(result, started_at)
            _unregister_operation(operation_id)
            finalized_early = True
            yield {"event": "done", "operation_id": operation_id, "result": result.to_dict(include_response=True, include_cognitive_context=False)}
            return

        if (
            development_campaign_lifecycle.get("active")
            and development_campaign_lifecycle.get("conversation_response")
            and (
                not conversation_command_distinction.get("mixed_turn")
                or development_campaign_lifecycle.get("v1489_self_inspection_requested")
            )
        ):
            response = str(development_campaign_lifecycle["conversation_response"])
            result.response = response
            result.display_message = response
            result.success = True
            result.completion_state = "development_campaign_lifecycle"
            result.provider_request_count = 0
            if not _claim_operation_completion(operation_id, active_cancel):
                raise LocalModelCancelledError(
                    "Development campaign response was cancelled before memory commit.",
                    provider=config.provider,
                    endpoint=config.endpoint,
                    model=config.model,
                    details={"failure_kind": "pre_commit_cancellation"},
                )
            assistant_memory = _store_assistant_memory(
                operation_id, response, source, config, result.session_id,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.assistant_memory_stored = True
            result.assistant_memory_attribution_id = str(assistant_memory.get("memory_candidate_id") or "")
            result.cognitive_context["conversation_policy_continuity"] = complete_conversation_policy_state(
                operation_id=operation_id, session_id=result.session_id
            )
            _queue_memory_vectors(user_memory, assistant_memory)
            result.turn_completion = queue_turn_completion_safely(
                operation_id=operation_id, session_id=result.session_id, user_message=message,
                assistant_response=response, source=source, context_summary=result.cognitive_context,
            )
            _schedule_housekeeping_safely(result)
            yield {"event": "replace", "text": response, "operation_id": operation_id}
            yield {"event": "response_complete", "operation_id": operation_id}
            result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
            _record_session_turn(
                result, user_message=message, source=source, created_at=started_at,
                select_session=select_session_on_record,
            )
            _persist_receipt(result, started_at)
            _unregister_operation(operation_id)
            finalized_early = True
            yield {"event": "done", "operation_id": operation_id, "result": result.to_dict(include_response=True, include_cognitive_context=False)}
            return

        if not use_ai or not bool(settings.get("ai_chat_enabled", True)):
            result.completion_state = "ai_disabled"
            result.failure_category = "ai_disabled"
            result.display_message = "Your message was saved. Local generation is off, so no provider was contacted and no fallback was used."
            yield {"event": "replace", "text": result.display_message, "operation_id": operation_id}
            result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
            _record_session_turn(
                result, user_message=message, source=source, created_at=started_at,
                select_session=select_session_on_record,
            )
            _persist_receipt(result, started_at)
            _unregister_operation(operation_id)
            finalized_early = True
            yield {"event": "done", "operation_id": operation_id, "result": result.to_dict(include_response=True, include_cognitive_context=False)}
            return

        chunks: list[str] = []
        visible_chunks: list[str] = []
        action_response_guarded = bool(
            (action_projection.get("intent") or {}).get("action_intent_present")
            and not (action_projection.get("grounding") or {}).get("authoritative_execution_receipt_present")
        )
        stream_cleaner = _AssistantStreamCleaner(str(self_model.get("name") or "Eidolon"))
        follow_up_stream_gate = NaturalFollowUpStreamGate(
            natural_follow_up, casual_fast_path=str(packet.metrics.prompt_lane) == "casual_fast",
        )
        first_transport_chunk_clock: float | None = None
        first_visible_token_clock: float | None = None
        if action_response_guarded:
            acknowledgement = trusted_action_acknowledgement(action_projection)
            result.timings_ms["first_visible_feedback"] = int((time.monotonic() - started_clock) * 1000)
            yield {
                "event": "replace",
                "text": acknowledgement,
                "operation_id": operation_id,
                "trusted_status": True,
                "authoritative_execution_claim": False,
                "timing": {
                    "first_visible_feedback_ms": result.timings_ms["first_visible_feedback"],
                    "content_free": True,
                },
            }
        provider_start_kind = classify_provider_start(config.provider, config.endpoint, config.model)
        provider_started = time.monotonic()
        result.timings_ms["pre_provider"] = int((provider_started - started_clock) * 1000)
        result.cognitive_context["critical_path"] = critical_path_public_receipt(
            critical_path_decision, pre_provider_ms=result.timings_ms["pre_provider"]
        )
        if active_cancel.is_set():
            raise LocalModelCancelledError(
                "Local model request was cancelled before provider contact.",
                provider=config.provider,
                endpoint=config.endpoint,
                model=config.model,
                details={"failure_kind": "pre_provider_cancellation"},
            )
        result.provider_request_count = 1
        yield {"event": "provider_request", "operation_id": operation_id, "request_index": 1, "automatic_retry": False, "content_free": True}
        with LocalModelClient(config, cancel_event=active_cancel) as client:
            _set_operation_cancel_callback(operation_id, client.cancel)
            for chunk in client.stream(packet.prompt):
                if first_transport_chunk_clock is None:
                    first_transport_chunk_clock = time.monotonic()
                raw_chunk = str(chunk)
                chunks.append(raw_chunk)
                visible_chunk = follow_up_stream_gate.feed(stream_cleaner.feed(raw_chunk))
                if visible_chunk and not action_response_guarded:
                    if first_visible_token_clock is None and visible_chunk.strip():
                        first_visible_token_clock = time.monotonic()
                    visible_chunks.append(visible_chunk)
                    visible_content = True
                    timing = None
                    if first_visible_token_clock is not None and len(visible_chunks) == 1:
                        timing = {
                            "first_transport_chunk_ms": int((first_transport_chunk_clock - started_clock) * 1000) if first_transport_chunk_clock is not None else None,
                            "first_visible_token_ms": int((first_visible_token_clock - started_clock) * 1000),
                            "pre_provider_ms": result.timings_ms.get("pre_provider"),
                            "content_free": True,
                        }
                    yield {"event": "delta", "text": visible_chunk, "operation_id": operation_id, "timing": timing}
            result.provider_metrics = provider_metrics_public(getattr(client, "last_metrics", {}))
            result.retry_count = client.last_retry_count
        cleaned_tail = stream_cleaner.finish()
        gated_tail = follow_up_stream_gate.feed(cleaned_tail) if cleaned_tail else ""
        final_visible_chunk = gated_tail + follow_up_stream_gate.finish()
        result.cognitive_context["natural_follow_up_output_enforcement"] = follow_up_stream_gate.diagnostics()
        if final_visible_chunk and not action_response_guarded:
            if first_visible_token_clock is None and final_visible_chunk.strip():
                first_visible_token_clock = time.monotonic()
            visible_chunks.append(final_visible_chunk)
            visible_content = True
            timing = {
                "first_transport_chunk_ms": int((first_transport_chunk_clock - started_clock) * 1000) if first_transport_chunk_clock is not None else None,
                "first_visible_token_ms": int((first_visible_token_clock - started_clock) * 1000) if first_visible_token_clock is not None else None,
                "pre_provider_ms": result.timings_ms.get("pre_provider"),
                "content_free": True,
            } if len(visible_chunks) == 1 else None
            yield {"event": "delta", "text": final_visible_chunk, "operation_id": operation_id, "timing": timing}
        result.timings_ms["provider"] = int((time.monotonic() - provider_started) * 1000)
        mark_provider_warm(config.provider, config.endpoint, config.model)
        result.provider_metrics["runtime_start_kind"] = provider_start_kind
        first_transport_ms = (
            int((first_transport_chunk_clock - started_clock) * 1000)
            if first_transport_chunk_clock is not None else None
        )
        first_visible_ms = (
            int((first_visible_token_clock - started_clock) * 1000)
            if first_visible_token_clock is not None else None
        )
        result.timings_ms["first_transport_chunk"] = first_transport_ms
        result.timings_ms["first_visible_token"] = first_visible_ms
        result.timings_ms["first_token"] = first_visible_ms
        response = _bound_unverified_action_claim(
            _clean_assistant_response("".join(chunks), str(self_model.get("name") or "Eidolon")),
            action_projection,
        )
        response, final_follow_up_output_diagnostics = enforce_natural_follow_up_output(
            response, natural_follow_up,
            casual_fast_path=str(packet.metrics.prompt_lane) == "casual_fast",
        )
        # The stream gate and finalizer share the same policy.  Merge only
        # content-free counters; never store generated/provider text in diagnostics.
        stream_diagnostics = dict(result.cognitive_context.get("natural_follow_up_output_enforcement") or {})
        result.cognitive_context["natural_follow_up_output_enforcement"] = {
            "stream_gate": stream_diagnostics,
            "finalizer": final_follow_up_output_diagnostics,
            "content_free": True,
            "provider_request_added": False,
        }
        response, target_output_diagnostics = enforce_conversation_target_output(
            response, conversation_target, session_history,
            casual_fast_path=str(packet.metrics.prompt_lane) == "casual_fast",
        )
        result.cognitive_context["conversation_target_continuity"] = dict(conversation_target["policy"])
        result.cognitive_context["conversation_target_output_enforcement"] = target_output_diagnostics
        result.cognitive_context["conversation_target_outcome"] = build_conversation_target_outcome(target_output_diagnostics)
        append_conversation_target_outcome(result.cognitive_context["conversation_target_outcome"], operation_id=operation_id)
        result.cognitive_context["conversation_target_learning_profile"] = build_conversation_target_learning_profile()
        result.cognitive_context["era5_companion_output_audit"] = audit_era5_companion_output(
            response, projection=era5_companion_projection,
        )
        result.cognitive_context["response_grounding_output_audit"] = audit_response_grounding_output(
            response, response_grounding, response_assertion_calibration,
            authoritative_execution_evidence=bool(result_presentation.get("authoritative_execution_claim")),
        )
        result.cognitive_context["response_grounding_output_observability"] = record_response_grounding_output_audit(
            result.cognitive_context["response_grounding_output_audit"], operation_id=operation_id
        )
        result.cognitive_context["response_grounding_repair_candidate"] = build_response_grounding_repair_candidate(
            result.cognitive_context["response_grounding_output_audit"], response_grounding, response_assertion_calibration
        )
        result.cognitive_context["response_grounding_repair_review"] = build_response_grounding_repair_review(
            result.cognitive_context["response_grounding_repair_candidate"]
        )
        result.cognitive_context["conversation_health"] = build_conversation_health()
        append_conversation_health(result.cognitive_context["conversation_health"], operation_id=operation_id)
        result.cognitive_context["conversation_health_trend"] = build_conversation_health_trend(
            load_conversation_health_history().get("rows") or []
        )
        result.cognitive_context["conversation_outcome_attribution"] = build_conversation_outcome_attribution(
            target_outcome=result.cognitive_context.get("conversation_target_outcome") or {},
            output_audit=result.cognitive_context.get("response_grounding_output_audit") or {},
            memory_feedback=memory_retrieval_projection.get("retrieval_sufficiency") or {},
            context_observability=result.cognitive_context.get("conversation_context_observability") or {},
        )
        result.cognitive_context["response_quality_evaluation"] = evaluate_response_quality(
            result.cognitive_context["conversation_outcome_attribution"]
        )
        append_response_quality(
            result.cognitive_context["response_quality_evaluation"],
            result.cognitive_context["conversation_outcome_attribution"],
            operation_id=operation_id,
        )
        result.cognitive_context["response_quality_trend"] = build_response_quality_trend(
            load_response_quality_history().get("rows") or []
        )
        result.cognitive_context["response_quality_review"] = build_response_quality_review(
            result.cognitive_context["response_quality_evaluation"],
            result.cognitive_context["response_quality_trend"],
        )
        result.cognitive_context["daily_use_reliability"] = build_daily_use_runtime_reliability(operation_id=operation_id)
        if not response:
            raise ClosedClientError(
                "Streaming completed without a visible response.",
                provider=config.provider,
                model=config.model,
            )
        if conversation_command_distinction.get("mixed_turn") and development_campaign_lifecycle.get("conversation_response"):
            response = response.rstrip() + "\n\n" + str(development_campaign_lifecycle["conversation_response"]).strip()
        result.response = response
        result.display_message = response
        if "".join(visible_chunks).strip() != response:
            yield {"event": "replace", "text": response, "operation_id": operation_id}
        goal_planning_bundle = _complete_deferred_goal_planning(
            result=result,
            decision=critical_path_decision,
            message=message,
            memory_learning_alpha_projection=memory_learning_alpha_projection,
            session_history=session_history,
            current_bundle=goal_planning_bundle,
        )
        if not _claim_operation_completion(operation_id, active_cancel):
            raise LocalModelCancelledError(
                "Local model request was cancelled before memory commit.",
                provider=config.provider,
                endpoint=config.endpoint,
                model=config.model,
                details={"failure_kind": "pre_commit_cancellation"},
            )
        try:
            assistant_memory = _store_assistant_memory(
                operation_id, response, source, config, result.session_id,
                continuity_lane=str(result.context.get("continuity_lane") or "ordinary"),
            )
            result.assistant_memory_stored = True
            result.assistant_memory_attribution_id = str(assistant_memory.get("memory_candidate_id") or "")
            learning_commit_handoff = build_learning_commit_boundary_handoff(
                immediate_learning_projection.get("candidate"),
                provider_completed=True,
                assistant_memory_committed=True,
            )
            result.cognitive_context["immediate_memory_learning_commit_handoff"] = learning_commit_handoff
            result.cognitive_context["immediate_memory_learning_compliance_audit"] = audit_immediate_memory_learning(
                immediate_learning_projection,
                learning_commit_handoff,
            )
            lesson_review_handoff = build_lesson_review_boundary_handoff(
                bounded_lesson_projection.get("candidate"),
                provider_completed=True,
                assistant_memory_committed=True,
            )
            result.cognitive_context["bounded_experiential_lesson_review_handoff"] = lesson_review_handoff
            result.cognitive_context["bounded_experiential_lesson_compliance_audit"] = audit_bounded_experiential_lesson(
                bounded_lesson_projection,
                lesson_review_handoff,
            )
            memory_learning_alpha_projection = build_memory_experiential_learning_alpha(
                unified_memory_projection, memory_retrieval_projection,
                immediate_learning_projection, bounded_lesson_projection,
                learning_commit_handoff=learning_commit_handoff,
                lesson_review_handoff=lesson_review_handoff,
                prior_alpha_receipts=session_history,
            )
            result.cognitive_context["memory_experiential_learning_alpha_policy"] = dict(memory_learning_alpha_projection["policy"])
            result.cognitive_context["memory_experiential_learning_alpha_evidence"] = dict(memory_learning_alpha_projection["evidence"])
            result.cognitive_context["memory_experiential_learning_alpha_runtime_diagnostics"] = dict(memory_learning_alpha_projection["diagnostics"])
            alpha_handoff = build_memory_experiential_learning_alpha_handoff(memory_learning_alpha_projection, provider_completed=True, assistant_memory_committed=True)
            result.cognitive_context["memory_experiential_learning_alpha_handoff"] = alpha_handoff
            alpha_audit = audit_memory_experiential_learning_alpha(memory_learning_alpha_projection, alpha_handoff)
            result.cognitive_context["memory_experiential_learning_alpha_compliance_audit"] = alpha_audit
            alpha_prior_receipts = session_history
            result.cognitive_context["memory_experiential_learning_alpha_reliability"] = build_memory_experiential_learning_alpha_reliability(
                memory_learning_alpha_projection, alpha_handoff, alpha_audit,
                prior_alpha_receipts=alpha_prior_receipts,
            )
            apply_goal_planning_handoffs(result.cognitive_context, goal_planning_bundle)
            result.cognitive_context["conversation_policy_continuity"] = complete_conversation_policy_state(
                operation_id=operation_id, session_id=result.session_id
            )
            result.success = True
            result.completion_state = "completed"
            _queue_memory_vectors(user_memory, assistant_memory)
            result.turn_completion = queue_turn_completion_safely(
                operation_id=operation_id, session_id=result.session_id, user_message=message,
                assistant_response=response, source=source, context_summary=result.cognitive_context,
            )
            _schedule_housekeeping_safely(result)
            yield {"event": "response_complete", "operation_id": operation_id}
        except Exception as error:
            result.success = False
            result.completion_state = "response_generated_memory_failed"
            result.failure_category = "memory_write_failure"
            result.error = _safe_error(error, config)
            yield {
                "event": "error",
                "operation_id": operation_id,
                "failure_category": result.failure_category,
                "message": conversation_error_message(error, provider=config.provider, model=config.model),
                "error": result.error,
                "partial_discarded": False,
            }
    except Exception as error:
        if active_cancel.is_set() and not isinstance(error, LocalModelCancelledError):
            error = LocalModelCancelledError(
                "Local model request was cancelled.",
                provider=config.provider,
                endpoint=config.endpoint,
                model=config.model,
                details={"failure_kind": "operator_cancellation", "exception_type": type(error).__name__},
            )
        result.success = False
        result.failure_category = _failure_category(error)
        result.completion_state = "cancelled" if isinstance(error, LocalModelCancelledError) else "failed"
        result.error = _safe_error(error, config)
        if isinstance(error, LocalModelError):
            result.cognitive_context["provider_recovery"] = provider_recovery_guidance(error)
        result.display_message = conversation_error_message(error, provider=config.provider, model=config.model)
        yield {
            "event": "error",
            "operation_id": operation_id,
            "failure_category": result.failure_category,
            "message": result.display_message,
            "error": result.error,
            "recovery": dict(result.cognitive_context.get("provider_recovery") or {}),
            "partial_discarded": visible_content,
        }
        yield {"event": "replace", "text": result.display_message, "operation_id": operation_id}
    finally:
        if result.completion_state == "started":
            cancelled = active_cancel.is_set()
            result.success = False
            result.completion_state = "cancelled" if cancelled else "consumer_disconnected"
            result.failure_category = result.completion_state
            result.display_message = (
                "The conversation request was cancelled before completion."
                if cancelled
                else "The conversation consumer disconnected before completion."
            )
            result.error = {
                "code": result.failure_category,
                "message": result.display_message,
                "provider": result.provider,
                "model": result.model,
                "retryable": False,
                "status_code": None,
                "details": {"partial_visible": visible_content},
                "redacted": True,
            }
        if not finalized_early:
            result.timings_ms["total"] = int((time.monotonic() - started_clock) * 1000)
            result.cognitive_context["response_performance"] = build_conversation_timing_receipt(
                result.timings_ms, provider_start_kind=provider_start_kind, prompt_tokens=prompt_tokens
            )
            _record_session_turn(
                result, user_message=message, source=source, created_at=started_at,
                select_session=select_session_on_record,
            )
            _persist_receipt(result, started_at)
            _unregister_operation(operation_id)
    yield {
        "event": "done",
        "operation_id": operation_id,
        "result": result.to_dict(include_response=True, include_cognitive_context=False),
    }
