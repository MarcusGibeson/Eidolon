from __future__ import annotations

"""Deterministic, provider-neutral conversation context budgeting.

The builder protects the system contract and latest user message, admits complete
optional sections only when they fit, and never sends partial memory records.
It performs no provider calls and writes no runtime state.
"""

from functools import lru_cache
from dataclasses import asdict, dataclass, field
import hashlib
from typing import Any, Iterable

from local_model import ContextLimitError
from conversation_quality import (
    assistant_response_has_unsolicited_operational_content,
    classify_conversation_quality,
    filter_general_conversation_memories,
    general_memory_is_operational,
    memory_duplicates_recent_history,
)
from release_metadata import RUNTIME_VERSION_TAG
from conversation_quality_diagnostics import build_conversation_quality_diagnostics
from context_assembly_architecture import build_context_assembly_plan
from context_relevance_ranking import rank_context_records, ranking_public_summary
from context_salience_balance import balance_ranked_context
from context_topic_segmentation import segment_conversation_topics
from context_budget_management import ContextBudgetLedger, build_context_budget_plan
from context_correction_aware_retrieval import filter_correction_aware_records
from context_cross_session_linking import link_cross_session_threads
from context_stale_summary_detection import filter_stale_continuity_summaries
from conversation_response_preferences import normalize_response_preferences
from temporary_instruction_scope import build_temporary_instruction_record, resolve_temporary_instruction
from conversation_pinned_context import MAX_PINNED_CONTEXT_PROMPT_CHARS, resolve_pinned_context_records
from relationship_personality_continuity import RelationshipPersonalityContinuityProfile
from natural_conversation_foundation import (
    build_greeting_repetition_profile,
    build_identity_relationship_prompt_profile,
    build_intent_topic_continuity_profile,
)
from immediate_conversation_grounding import build_immediate_conversation_grounding
from natural_conversation_quality_runtime import build_natural_conversation_quality_runtime_profile
from relationship_preference_continuity_guard import build_relationship_preference_guard
from natural_conversation_adaptation import (
    build_affection_nickname_boundary_profile,
    build_correction_preference_propagation_profile,
    build_response_length_depth_resolution_profile,
)


CONTEXT_BUDGET_SCHEMA_VERSION = "1"
CHARS_PER_TOKEN_ESTIMATE = 4
MINIMUM_SAFETY_MARGIN_TOKENS = 96
MAXIMUM_SAFETY_MARGIN_TOKENS = 384
MAX_ORDINARY_HISTORY_TURNS = 6
MAX_OPERATOR_HISTORY_TURNS = 12
CASUAL_FAST_FRESH_TOKEN_LIMIT = 600
CASUAL_FAST_CONTINUITY_TOKEN_LIMIT = 900
CASUAL_FAST_HISTORY_TURNS = 2


@dataclass(frozen=True)
class ConversationContextMetrics:
    context_size: int
    reserved_output_tokens: int
    safety_margin_tokens: int
    input_budget_tokens: int
    estimated_prompt_tokens: int
    essential_tokens: int
    memory_candidates: int
    memories_included: int
    history_turn_candidates: int
    history_turns_included: int
    history_turns_omitted: int
    important_memories_included: int
    memories_omitted: int
    relationship_cue_candidates: int
    relationship_cues_included: int
    relationship_cues_omitted: int
    relationship_mood_included: bool
    relationship_categories_included: tuple[str, ...]
    optional_sections_included: tuple[str, ...]
    optional_sections_omitted: tuple[str, ...]
    temporal_mood_candidates: int = 0
    temporal_user_mood_included: bool = False
    temporal_important_moment_candidates: int = 0
    temporal_important_moments_included: int = 0
    continuity_lane: str = "ordinary"
    personality_guard_included: bool = False
    relationship_cues_suppressed: int = 0
    relationship_singleton_conflicts_omitted: int = 0
    relationship_memory_policy: str = "explicit_curation_only"
    personality_history_rows_considered: int = 0
    personality_repeated_opening_runs: int = 0
    personality_identity_reset_signals: int = 0
    personality_long_history_rows_considered: int = 0
    personality_opening_diversity_percent: int = 100
    personality_repeated_opening_percent: int = 0
    personality_operator_bleed_signals: int = 0
    personality_affection_inflation_signals: int = 0
    personality_tone_monoculture_risk: bool = False
    personality_lane_adaptation_stable: bool = True
    personality_drift_risk: str = "bounded"
    emotional_current_mood_count: int = 0
    emotional_affection_escalation_allowed: bool = False
    emotional_progress_claim_allowed: bool = False
    conversation_turn_intent: str = "casual_remark"
    conversation_intent_flags: tuple[str, ...] = ()
    conversation_response_length: str = "balanced"
    conversation_response_depth: str = "reasoned"
    conversation_response_target_min_words: int = 50
    conversation_response_target_max_words: int = 240
    conversation_quality_relevance: str = "current_turn_primary"
    conversation_clarity_risk: str = "bounded"
    conversation_repetition_risk: bool = False
    conversation_current_question_count: int = 0
    conversation_open_question_signals: int = 0
    conversation_unresolved_thread_count: int = 0
    conversation_matching_unresolved_threads: int = 0
    conversation_unresolved_questions: int = 0
    conversation_commitment_signals: int = 0
    conversation_blocker_signals: int = 0
    conversation_unfinished_subjects: int = 0
    conversation_callback_candidates: int = 0
    conversation_callbacks_selected: int = 0
    conversation_topic_transition: str = "no_history"
    conversation_topic_transition_confidence: str = "high"
    conversation_topic_match_offset: int | None = None
    conversation_correction_kind: str = "none"
    conversation_correction_target_scope: str = "none"
    conversation_correction_acknowledge_once: bool = False
    conversation_stale_claim_suppression: bool = False
    conversation_personality_expression_mode: str = "conversational_grounded"
    conversation_personality_expression_lane: str = "ordinary"
    conversation_personality_lane_transition: str = "same_lane"
    conversation_personality_operator_bleed_risk: bool = False
    conversation_personality_therapy_script_risk: bool = False
    conversation_personality_affection_inflation_signals: int = 0
    natural_identity_interaction_lane: str = "ordinary"
    natural_identity_history_available: bool = False
    natural_identity_relationship_cue_count: int = 0
    natural_identity_self_introduction_allowed: bool = False
    natural_greeting_kind: str = "none"
    natural_greeting_suppress_new: bool = True
    natural_greeting_suppress_self_introduction: bool = True
    natural_greeting_repeated_opening_runs: int = 0
    natural_greeting_variation_required: bool = False
    natural_thread_mode: str = "fresh"
    natural_thread_deictic_follow_up: bool = False
    natural_thread_prior_preserved: bool = False
    natural_correction_recent_count: int = 0
    natural_correction_propagates: bool = False
    natural_preference_stored_applies: bool = False
    natural_preference_current_override: bool = False
    natural_preference_scope: str = "current_turn"
    natural_affection_response_mode: str = "ordinary_unprompted_blocked"
    natural_nickname_use_mode: str = "none"
    natural_nickname_stored_available: bool = False
    natural_nickname_current_request: bool = False
    natural_nickname_current_rejection: bool = False
    natural_response_effective_length: str = "balanced"
    natural_response_effective_depth: str = "reasoned"
    natural_response_effective_format: str = "prose"
    natural_response_resolution_source: str = "dynamic_turn_shape"
    natural_response_target_min_words: int = 50
    natural_response_target_max_words: int = 240
    conversation_quality_diagnostics: dict[str, Any] = field(default_factory=dict)
    context_lane_order: tuple[str, ...] = ()
    context_lane_candidates: dict[str, int] = field(default_factory=dict)
    context_lanes_included: tuple[str, ...] = ()
    context_lanes_omitted: tuple[str, ...] = ()
    context_active_thread_offset: int | None = None
    context_assembly_schema_version: str = "1"
    context_ranked_candidate_count: int = 0
    context_top_rank_score: int = 0
    context_ranked_lexical_matches: int = 0
    context_ranked_operator_curated: int = 0
    context_ranked_relationship_relevant: int = 0
    context_salient_candidate_count: int = 0
    context_salience_reservations: int = 0
    context_recent_trivial_demotions: int = 0
    context_ranking_provider_invoked: bool = False
    context_assembly_writes_state: bool = False
    context_topic_segment_count: int = 0
    context_topic_active_turn_count: int = 0
    context_topic_unrelated_turns_excluded: int = 0
    context_topic_selection_reason: str = "no_history"
    context_topic_query_overlap_percent: int = 0
    context_topic_provider_invoked: bool = False
    context_budget_allocated_tokens: dict[str, int] = field(default_factory=dict)
    context_budget_used_tokens: dict[str, int] = field(default_factory=dict)
    context_budget_shared_reserve_tokens: int = 0
    context_budget_shared_reserve_used: int = 0
    context_budget_omissions_by_lane: dict[str, int] = field(default_factory=dict)
    context_budget_omission_reasons: dict[str, int] = field(default_factory=dict)
    context_budget_silent_truncation_allowed: bool = False
    context_correction_records: int = 0
    context_correction_exact_suppressed: int = 0
    context_correction_explicit_link_suppressed: int = 0
    context_correction_ambiguous_similarity_suppressed: int = 0
    context_correction_provider_invoked: bool = False
    context_cross_session_candidate_sessions: int = 0
    context_cross_session_candidate_turns: int = 0
    context_cross_session_linked_sessions: int = 0
    context_cross_session_linked_turns: int = 0
    context_cross_session_turns_included: int = 0
    context_cross_session_turns_omitted: int = 0
    context_cross_session_provider_invoked: bool = False
    context_stale_summary_candidates: int = 0
    context_stale_summaries_detected: int = 0
    context_stale_summaries_suppressed: int = 0
    context_stale_summary_corrected_conflicts: int = 0
    context_stale_summary_retracted_conflicts: int = 0
    context_stale_summary_deleted_conflicts: int = 0
    context_stale_summary_current_session_conflicts: int = 0
    context_stale_summary_provider_invoked: bool = False
    context_provenance_states: dict[str, int] = field(default_factory=dict)
    conversation_control_response_mode: str = "default"
    conversation_control_response_format: str = "default"
    conversation_control_preference_included: bool = False
    conversation_control_temporary_instruction_count: int = 0
    conversation_control_pinned_context_candidates: int = 0
    conversation_control_pinned_context_active: int = 0
    conversation_control_pinned_context_included: int = 0
    conversation_control_pinned_context_omitted: int = 0
    conversation_control_pinned_context_expired: int = 0
    conversation_control_pinned_context_kinds: tuple[str, ...] = ()
    conversation_control_pinned_context_scopes: tuple[str, ...] = ()
    conversation_control_temporary_scopes: tuple[str, ...] = ()
    conversation_control_current_topic_active: bool = False
    conversation_control_provider_invoked: bool = False
    conversation_control_writes_state: bool = False
    prompt_lane: str = "governed"
    provider_prompt_budget_tokens: int = 0
    fast_path_bound_passed: bool = True
    prompt_section_categories_included: tuple[str, ...] = ()
    prompt_section_categories_omitted: tuple[str, ...] = ()
    prompt_metrics_content_free: bool = True
    natural_quality_repeated_greeting_suppressed: bool = False
    natural_quality_project_redirect_suppressed: bool = False
    natural_quality_direct_answer_required: bool = False
    natural_quality_active_topic_required: bool = False
    natural_quality_emotional_ack_required: bool = False
    natural_quality_optional_question_suppressed: bool = False
    natural_quality_ack_target_min_words: int = 0
    natural_quality_ack_target_max_words: int = 0
    natural_quality_canned_phrase_suppressed: bool = False
    natural_quality_present_stakes_grounding_required: bool = False
    natural_quality_profile_digest: str = ""
    immediate_grounding_present: bool = False
    immediate_recall_requested: bool = False
    immediate_exact_repeat_requested: bool = False
    immediate_correction_protected: bool = False
    immediate_grounding_state: str = "none"
    current_message_correction_protected: bool = False
    compound_grounding_explanation_requested: bool = False
    historical_memory_query: bool = False
    attributable_historical_memory_available: bool = False
    historical_memory_evidence_state: str = "not_historical"
    historical_memory_evidence_requested: bool = False
    historical_uncertainty_required: bool = False
    historical_evidence_class_counts: dict[str, int] = field(default_factory=dict)
    historical_provenance_state_digest: str = ""
    historical_user_authored_evidence_count: int = 0
    historical_assistant_authored_non_evidence_count: int = 0
    historical_user_nonassertive_count: int = 0
    historical_malformed_evidence_count: int = 0
    historical_conflict_count: int = 0
    historical_weak_match_rejected_count: int = 0
    historical_match_strength: str = "none"
    estimator: str = "bounded_chars_div_4"
    schema_version: str = CONTEXT_BUDGET_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversationPromptPacket:
    prompt: str
    metrics: ConversationContextMetrics


def estimate_tokens(text: str) -> int:
    """Return a deterministic conservative-enough local estimate."""
    value = str(text or "")
    return max(1, (len(value) + CHARS_PER_TOKEN_ESTIMATE - 1) // CHARS_PER_TOKEN_ESTIMATE)


def _memory_text(memory: dict[str, Any]) -> str:
    value = memory.get("content")
    if value in {None, ""}:
        value = memory.get("thought")
    if value in {None, ""}:
        value = memory.get("summary")
    return " ".join(str(value or "").split())


def _memory_content_digest(memory: dict[str, Any]) -> str:
    return hashlib.sha256(_memory_text(memory).encode("utf-8")).hexdigest()


def _superseded_memory_digests(memories: Iterable[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for memory in memories:
        if not isinstance(memory, dict):
            continue
        values = memory.get("superseded_content_digests")
        if isinstance(values, list):
            result.update(str(value) for value in values if value)
    return result


def _importance_rank(memory: dict[str, Any]) -> int:
    value = memory.get("importance")
    if isinstance(value, (int, float)):
        if value >= 0.8:
            return 3
        if value >= 0.5:
            return 2
    lowered = str(value or "").strip().lower()
    if lowered in {"critical", "core", "high", "important"}:
        return 3
    if lowered in {"medium", "normal"}:
        return 2
    memory_type = str(memory.get("type") or "").strip().lower()
    if memory_type in {
        "core_memory",
        "identity",
        "identity_memory",
        "preference",
        "commitment",
        "relationship",
        "goal",
        "long_term_goal",
    }:
        return 3
    return 1


def _keyword_score(text: str, user_message: str) -> int:
    words = {part for part in _simple_words(user_message) if len(part) >= 3}
    if not words:
        return 0
    haystack = set(_simple_words(text))
    return len(words & haystack)


def _simple_words(text: str) -> list[str]:
    current: list[str] = []
    words: list[str] = []
    for char in str(text or "").lower():
        if char.isalnum() or char in {"_", "-"}:
            current.append(char)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def _deduplicated_memories(memories: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    for memory in memories:
        if not isinstance(memory, dict):
            continue
        text = _memory_text(memory)
        if not text:
            continue
        key = (str(memory.get("type") or "memory"), text)
        if key in seen:
            continue
        seen.add(key)
        rows.append(memory)
    return rows


def _memory_candidate_bundle(
    memories: Iterable[dict[str, Any]],
    user_message: str,
) -> tuple[list[tuple[dict[str, Any], bool]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    memory_list = [memory for memory in memories if isinstance(memory, dict)]
    correction_filtered, correction_evidence = filter_correction_aware_records(memory_list)
    rows = _deduplicated_memories(correction_filtered)
    ranked = rank_context_records(rows, user_message, source_kind="curated_memory")
    balanced, balance_evidence = balance_ranked_context(ranked)
    candidates = [
        (dict(memory), bool(evidence.salient or _importance_rank(dict(memory)) >= 3))
        for memory, evidence in balanced
    ]
    return (
        candidates,
        ranking_public_summary(balanced),
        balance_evidence.public_summary(),
        correction_evidence.public_summary(),
    )


def _memory_candidates(memories: Iterable[dict[str, Any]], user_message: str) -> list[tuple[dict[str, Any], bool]]:
    candidates, _ranking, _balance, _correction = _memory_candidate_bundle(memories, user_message)
    return candidates


def _history_turn_text(turn: dict[str, Any]) -> str:
    user_message = " ".join(str(turn.get("user_message") or "").split())
    assistant_response = " ".join(str(turn.get("assistant_response") or "").split())
    if not user_message or not assistant_response:
        return ""
    action_status = " ".join(str(turn.get("action_status_summary") or "").split())[:520]
    suffix = f"\nSupervised action status: {action_status}" if action_status else ""
    return f"User: {user_message}\n{name_from_response(assistant_response)}{suffix}"


def name_from_response(response: str) -> str:
    return f"Eidolon: {response}" if not response.lower().startswith("eidolon:") else response


def _history_candidates(history: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for turn in history:
        if not isinstance(turn, dict):
            continue
        text = _history_turn_text(turn)
        if text:
            rows.append(turn)
    return rows


def _history_for_prompt(
    history: Iterable[dict[str, Any]],
    *,
    include_operational_context: bool,
) -> list[dict[str, Any]]:
    rows = _history_candidates(history)
    if not include_operational_context:
        rows = [
            turn for turn in rows
            if not assistant_response_has_unsolicited_operational_content(
                turn.get("assistant_response"),
                user_message=turn.get("user_message"),
            )
        ]
    limit = MAX_OPERATOR_HISTORY_TURNS if include_operational_context else MAX_ORDINARY_HISTORY_TURNS
    return rows[-limit:]


def _system_contract(name: str, *, operator_request: bool = False) -> str:
    role = "supervised local AI handling explicit operator work" if operator_request else "local conversational companion"
    lane = (
        "Keep discussion separate from governed execution and approval."
        if operator_request else
        "Stay natural and companion-first; do not sound like a dashboard or support script."
    )
    return f"""SYSTEM CONTRACT
You are {name}, a {role}, under human supervision. Runtime: {RUNTIME_VERSION_TAG}.
Do not claim proven consciousness, unrestricted computer control, provider/model changes, approval, installation, release, or autonomous action.
You may converse, use eligible completed-turn continuity, and propose bounded safe actions. {lane}
Follow current-turn response guidance, not one fixed length, while preserving privacy, memory, exactly-once, and operator-authority boundaries.
""".strip()


@lru_cache(maxsize=32)
def _casual_system_contract(name: str) -> str:
    return (
        f"IDENTITY AND SAFETY\nYou are {name}, a supervised local AI companion. Stay grounded and conversational. "
        "Do not claim human consciousness, unrestricted authority, provider/model changes, protected actions not performed, "
        "fabricated memories, exclusivity, or relationship progress not supported by explicit context."
    )


def clear_casual_contract_cache() -> None:
    _casual_system_contract.cache_clear()

def casual_contract_cache_metrics() -> dict[str, int | bool]:
    info=_casual_system_contract.cache_info()
    return {"hits":info.hits,"misses":info.misses,"size":info.currsize,"maxsize":info.maxsize,"content_free":True}


def _casual_relationship_cues_block(relationship_context: Any) -> tuple[str, int, tuple[str, ...]]:
    """Return a small whole-cue block; optional cues are omitted rather than truncated."""
    if relationship_context is None:
        return "", 0, ()
    cues = tuple(getattr(relationship_context, "cues", ()) or ())
    lines: list[str] = []
    categories: list[str] = []
    count = 0
    for cue in cues[:2]:
        text = " ".join(str(getattr(cue, "text", "") or "").split())
        label = " ".join(str(getattr(cue, "label", "") or "").split()) or "Explicit cue"
        if not text:
            continue
        lines.append(f"- {label}: {text}")
        category = str(getattr(cue, "category", "") or "").strip()
        if category:
            categories.append(category)
        count += 1
    if not lines:
        return "", 0, ()
    return (
        "EXPLICIT RELATIONSHIP OR PREFERENCE CUES\nUse only when relevant; do not recite them just to prove memory.\n" + "\n".join(lines),
        count,
        tuple(dict.fromkeys(categories)),
    )


def _casual_follow_up_lines(policy: dict[str, Any] | None) -> list[str]:
    """Project only behavioral consequences of the authoritative follow-up policy."""
    if not isinstance(policy, dict):
        return []
    suppressions: list[str] = []
    if policy.get("avoid_repeated_opening") is True:
        suppressions.append("opening")
    if policy.get("avoid_repeated_acknowledgment") is True:
        suppressions.append("acknowledgment")
    if policy.get("avoid_repeated_explanation") is True:
        suppressions.append("explanation")
    if policy.get("avoid_reasking_consumed_question") is True:
        suppressions.append("question")
    if policy.get("avoid_generic_closing_offer") is True:
        suppressions.append("generic closing/help offer")
    lines: list[str] = []
    maximum = max(0, min(1, int(policy.get("maximum_follow_up_questions") or 0)))
    permission = str(policy.get("question_permission") or "none")
    if maximum <= 0:
        lines.append("QUESTION BOUNDARY: Ask no question in this reply. End with a statement, reaction, reflection, warmth, humor, or a related thought instead.")
    elif permission == "required_clarification":
        lines.append("QUESTION BOUNDARY: One clarification question is permitted because the request genuinely requires it; ask no second question.")
    elif permission == "user_invited":
        lines.append("QUESTION BOUNDARY: The user explicitly invited a question; you may ask one specific relevant question, never a generic intake question.")
    else:
        lines.append("QUESTION BOUNDARY: At most one specific relevant question may advance the open topic; it is optional and must not be generic.")
    if policy.get("sharing_or_closure_cue_present") is True:
        lines.append("The user is sharing or closing rather than requesting more. Acknowledge or react naturally without reopening the exchange.")
    if policy.get("repeated_question_ending_behavior") is True:
        lines.append("Recent assistant replies have repeatedly ended in questions. Break that pattern and finish this turn without question pressure unless a question is explicitly permitted above.")
    if suppressions:
        lines.append("REPETITION SUPPRESSION: Do not repeat the recent " + ", ".join(suppressions) + ".")
    if policy.get("preserve_intentional_silence") is True:
        lines.append("Do not reopen a conversation the user has naturally closed.")
    return lines


def _optional_block(label: str, value: Any) -> str:
    if isinstance(value, (list, tuple, dict)):
        rendered = str(value)
    else:
        rendered = str(value or "").strip()
    if not rendered:
        return ""
    return f"{label}\n{rendered}".strip()


def build_conversation_prompt(
    *,
    user_message: str,
    self_model: dict[str, Any],
    desires: dict[str, Any],
    memories: Iterable[dict[str, Any]],
    project_context: str,
    goal_context: str,
    task_context: str,
    conversation_history: Iterable[dict[str, Any]] = (),
    relationship_context: Any = None,
    continuity_profile: RelationshipPersonalityContinuityProfile | None = None,
    current_session_id: str = "",
    cross_session_sessions: Iterable[dict[str, Any]] = (),
    explicit_cross_session_id: str = "",
    continuity_summaries: Iterable[dict[str, Any]] = (),
    response_preferences: dict[str, Any] | None = None,
    temporary_instruction: dict[str, Any] | None = None,
    pinned_context: Iterable[dict[str, Any]] = (),
    cognitive_context: str = "",
    transient_instruction: str = "",
    transient_instruction_scope: str = "current_turn",
    context_size: int,
    max_tokens: int,
    natural_follow_up_policy: dict[str, Any] | None = None,
) -> ConversationPromptPacket:
    """Build a prompt while preserving whole protected records and fixed instructions."""
    message = str(user_message or "").strip()
    if not message:
        raise ContextLimitError("Conversation user message cannot be empty.", details={"failure_kind": "empty_message"})
    context_size = int(context_size)
    max_tokens = int(max_tokens)
    safety_margin = max(
        MINIMUM_SAFETY_MARGIN_TOKENS,
        min(MAXIMUM_SAFETY_MARGIN_TOKENS, max(1, context_size // 20)),
    )
    input_budget = context_size - max_tokens - safety_margin
    if input_budget <= 0:
        raise ContextLimitError(
            "The configured context window leaves no room for a conversation prompt after output reservation.",
            details={"failure_kind": "invalid_context_budget"},
        )

    name = str(self_model.get("name") or "Eidolon")
    quality_history = _history_candidates(conversation_history)
    memory_records_all = [memory for memory in memories if isinstance(memory, dict)]
    immediate_grounding = build_immediate_conversation_grounding(
        message,
        quality_history,
        memory_records_all,
    )
    quality = classify_conversation_quality(message, quality_history)
    casual_fast_path = not quality.should_include_operational_context
    segmented_history, topic_segmentation = segment_conversation_topics(
        message,
        quality_history,
        transition=quality.topic_transition,
    )
    cross_session_turns, cross_session_plan = link_cross_session_threads(
        message,
        current_session_id,
        cross_session_sessions,
        explicit_session_id=explicit_cross_session_id,
    )
    history_rows = _history_for_prompt(
        segmented_history,
        include_operational_context=quality.should_include_operational_context,
    )
    if immediate_grounding.protected_recent_user_turn and immediate_grounding.source_turn_offset == 0 and history_rows:
        # The newest user evidence is already protected verbatim above the optional
        # history lane; do not spend the casual budget duplicating the same turn.
        history_rows = history_rows[:-1]
    if casual_fast_path:
        history_rows = history_rows[-CASUAL_FAST_HISTORY_TURNS:]
    transition_kind = str(getattr(quality.topic_transition, "transition_kind", "") or "")
    matched_offset = getattr(quality.topic_transition, "matched_turn_offset", None)
    recent_limit = MAX_OPERATOR_HISTORY_TURNS if quality.should_include_operational_context else MAX_ORDINARY_HISTORY_TURNS
    if transition_kind in {"resumption", "return"} and isinstance(matched_offset, int) and matched_offset >= recent_limit:
        active_index = len(quality_history) - 1 - matched_offset
        if 0 <= active_index < len(quality_history):
            active_candidate = quality_history[active_index]
            history_rows = [turn for turn in history_rows if turn is not active_candidate]
    identity_foundation = build_identity_relationship_prompt_profile(
        self_model,
        continuity_profile,
        relationship_context,
        quality_history,
    )
    greeting_control = build_greeting_repetition_profile(message, quality_history)
    intent_topic_continuity = build_intent_topic_continuity_profile(message, quality)
    preference_profile = normalize_response_preferences(response_preferences)
    correction_preference = build_correction_preference_propagation_profile(
        message,
        quality_history,
        quality=quality,
        response_preferences=preference_profile,
    )
    affection_nickname = build_affection_nickname_boundary_profile(
        message,
        quality=quality,
        relationship_context=relationship_context,
        continuity_profile=continuity_profile,
    )
    response_resolution = build_response_length_depth_resolution_profile(
        message,
        quality=quality,
        response_preferences=preference_profile,
    )
    existing_continuity_block = (
        continuity_profile.to_prompt_block()
        if continuity_profile is not None
        else (
            "PERSONALITY CONTINUITY\nMaintain a stable conversational voice. Relationship cues, when present, are supplied separately and must not be invented."
            if relationship_context is not None
            else "PERSONALITY AND RELATIONSHIP CONTINUITY\nMaintain a stable conversational voice. Do not invent relationship progress or treat operator work as affection."
        )
    )
    continuity_block = "\n\n".join((identity_foundation.prompt_block(), existing_continuity_block))
    preference_profile = normalize_response_preferences(response_preferences)
    control_blocks: list[str] = []
    if immediate_grounding.block:
        control_blocks.append(immediate_grounding.block)
    preference_included = preference_profile.mode != "default" or preference_profile.format != "default"
    if preference_included:
        control_blocks.append(preference_profile.prompt_block(explicit_length_cue=quality.response_shape.explicit_length_cue))
    instruction_resolutions = []
    persisted_resolution = resolve_temporary_instruction(
        temporary_instruction,
        current_message=message,
        short_follow_up=quality.short_follow_up,
        transition_kind=quality.topic_transition.transition_kind,
        persisted=True,
    )
    if persisted_resolution.active:
        instruction_resolutions.append(persisted_resolution)
        control_blocks.append(persisted_resolution.prompt_block())
    pinned_resolutions = resolve_pinned_context_records(
        [row for row in pinned_context if isinstance(row, dict)],
        current_message=message,
        transition_kind=quality.topic_transition.transition_kind,
        short_follow_up=quality.short_follow_up,
    )
    transient_text = " ".join(str(transient_instruction or "").split())
    if transient_text:
        transient_record = build_temporary_instruction_record(
            transient_text,
            scope=transient_instruction_scope or "current_turn",
            revision=1,
            updated_at="",
            source="exact_send_request",
            topic_anchor_text=message,
        )
        transient_resolution = resolve_temporary_instruction(
            transient_record,
            current_message=message,
            short_follow_up=quality.short_follow_up,
            transition_kind=quality.topic_transition.transition_kind,
            persisted=False,
        )
        if transient_resolution.active:
            instruction_resolutions.append(transient_resolution)
            control_blocks.append(transient_resolution.prompt_block())
    natural_quality_profile = build_natural_conversation_quality_runtime_profile(
        message, quality_history,
        emotional=quality.emotional, meaningful_moment=quality.meaningful_moment,
        short_follow_up=quality.short_follow_up,
        maximum_follow_up_questions=(int(natural_follow_up_policy.get("maximum_follow_up_questions") or 0) if isinstance(natural_follow_up_policy, dict) else None),
    )
    natural_quality_public = natural_quality_profile.public_summary()
    relationship_preference_guard = build_relationship_preference_guard(message)
    if casual_fast_path:
        casual_bound_tokens = (
            CASUAL_FAST_CONTINUITY_TOKEN_LIMIT
            if history_rows or quality.meaningful_moment or quality.emotional or quality.flirting
            else CASUAL_FAST_FRESH_TOKEN_LIMIT
        )
        continuity_block = (
            f"IDENTITY CONTINUITY\nRemain {name} across this exchange. Do not reintroduce yourself unless it naturally answers the user."
        )
        # Quality guidance is behaviorally important but optional under pathological
        # tiny context windows. Preserve the baseline identity/current-message
        # contract first; ordinary configured contexts receive the full compact
        # quality profile. Metrics still expose the deterministic profile decision.
        natural_quality_prompt_lines = (
            natural_quality_profile.prompt_lines() if input_budget >= 192 else ()
        )
        casual_guidance_lines = [
            quality.response_instruction(name),
            *natural_quality_prompt_lines,
            *relationship_preference_guard.prompt_lines(),
            *_casual_follow_up_lines(natural_follow_up_policy),
        ]
        essential_parts = [
            _casual_system_contract(name),
            continuity_block,
            *control_blocks,
            f"LATEST USER MESSAGE\n{message}",
            "\n".join(casual_guidance_lines),
        ]
    else:
        casual_bound_tokens = input_budget
        essential_parts = [
            _system_contract(name, operator_request=quality.explicit_operator_request),
            continuity_block,
            *control_blocks,
            f"LATEST USER MESSAGE\n{message}",
            "\n".join((
                quality.response_instruction(name),
                *greeting_control.prompt_lines(),
                *intent_topic_continuity.prompt_lines(),
                *correction_preference.prompt_lines(),
                *affection_nickname.prompt_lines(),
                *response_resolution.prompt_lines(),
            )),
        ]
    essential = "\n\n".join(essential_parts)
    essential_tokens = estimate_tokens(essential)
    admission_budget = min(input_budget, casual_bound_tokens) if casual_fast_path else input_budget
    if not casual_fast_path and essential_tokens > input_budget:
        # Natural-conversation guidance is protected behavior, but its explanatory
        # wording may be compacted before rejecting an otherwise valid turn. The
        # compact form preserves identity, relationship, greeting, and thread rules
        # while leaving correction and other current-turn contracts untouched.
        compact_continuity = "\n\n".join((identity_foundation.compact_prompt_block(), existing_continuity_block))
        essential_parts[1] = compact_continuity
        essential_parts[-1] = "\n".join((
            quality.response_instruction(name),
            *greeting_control.compact_prompt_lines(),
            *intent_topic_continuity.compact_prompt_lines(),
            *correction_preference.compact_prompt_lines(),
            *affection_nickname.compact_prompt_lines(),
            *response_resolution.compact_prompt_lines(),
        ))
        essential = "\n\n".join(essential_parts)
        essential_tokens = estimate_tokens(essential)
    if not casual_fast_path and essential_tokens > input_budget:
        # Under unusually tight contexts, collapse the explanatory adaptation
        # blocks into one protected contract. This keeps the latest correction,
        # identity, relationship boundary, active thread, and explicit response
        # controls intact without spending the user's message budget on headings.
        essential_parts[-1] = "\n".join((
            quality.response_instruction(name),
            f"Remain {name}; avoid repeated self-description and use only explicit user-led relationship cues.",
            "Treat the latest explicit correction and current-turn response controls as authoritative; keep stored preferences session-local and invent no nickname or intimacy.",
            "Answer the active thread directly, preserve explicit topic shifts, and match length/depth naturally without padding.",
        ))
        essential = "\n\n".join(essential_parts)
        essential_tokens = estimate_tokens(essential)
    if not casual_fast_path and essential_tokens > input_budget:
        # Preserve the same authority and identity boundaries in a final compact
        # form before rejecting a small but otherwise usable local-model context.
        essential_parts[0] = (
            f"SYSTEM CONTRACT\nYou are {name}, a supervised local AI companion. "
            "Do not claim unrestricted control, approval, installation, release, or autonomous action."
        )
        essential_parts[1] = (
            f"IDENTITY CONTINUITY\nRemain {name}; do not reintroduce yourself, invent relationship facts, "
            "or infer durable cues from transcript tone."
        )
        essential_parts[-1] = (
            "Answer the latest message directly. Honor explicit corrections and topic shifts; "
            "keep operator work supervised and separate from personal conversation."
        )
        essential = "\n\n".join(essential_parts)
        essential_tokens = estimate_tokens(essential)
    if essential_tokens > input_budget:
        raise ContextLimitError(
            "The latest user message and protected system instructions exceed the configured context budget.",
            details={"failure_kind": "essential_context_too_large"},
        )

    system_part = essential_parts[0]
    continuity_part = essential_parts[1]
    latest_part = essential_parts[-2]
    guidance_part = essential_parts[-1]
    protected_control_parts = essential_parts[2:-2]
    selected_middle: list[str] = []
    used_tokens = essential_tokens
    included_sections: list[str] = []
    omitted_sections: list[str] = []
    history_text = "\n".join(_history_turn_text(turn) for turn in history_rows)
    memory_records = memory_records_all
    summary_types = {"continuity_summary", "conversation_summary", "relationship_summary"}
    stored_summary_rows = [
        memory for memory in memory_records
        if str(memory.get("type") or "").strip().lower() in summary_types
    ]
    explicit_summary_rows = [row for row in continuity_summaries if isinstance(row, dict)]
    summary_rows_by_key: dict[str, dict[str, Any]] = {}
    for row in [*stored_summary_rows, *explicit_summary_rows]:
        key = str(row.get("id") or row.get("content_digest") or _memory_content_digest(row))
        summary_rows_by_key.setdefault(key, dict(row))
    eligible_summaries, stale_summary_evidence = filter_stale_continuity_summaries(
        summary_rows_by_key.values(),
        memory_records,
        current_session_records=quality_history,
    )
    eligible_memories = filter_general_conversation_memories(
        memory for memory in memory_records
        if str(memory.get("type") or "").strip().lower() not in summary_types
    )
    if not quality.should_include_operational_context:
        eligible_memories = [memory for memory in eligible_memories if not general_memory_is_operational(memory)]
    summary_memories = [dict(row, type=str(row.get("type") or "continuity_summary")) for row in eligible_summaries]
    ranked_memory_rows, ranking_summary, salience_summary, correction_retrieval_summary = _memory_candidate_bundle(
        [*eligible_memories, *summary_memories],
        quality.memory_query,
    )
    memory_rows = [
        row for row in ranked_memory_rows
        if not memory_duplicates_recent_history(_memory_text(row[0]), history_text)
    ]
    memories_included = 0
    history_included = 0
    important_included = 0
    relationship_candidates = int(getattr(relationship_context, "cue_candidates", 0) or 0)
    relationship_selected = int(getattr(relationship_context, "cue_count", 0) or 0)
    relationship_included = 0
    relationship_mood_included = False
    relationship_categories: tuple[str, ...] = ()
    continuity_lane = str(getattr(continuity_profile, "lane", "ordinary") or "ordinary")
    relationship_memory_policy = str(
        getattr(continuity_profile, "relationship_memory_policy", "explicit_curation_only")
        or "explicit_curation_only"
    )
    relationship_cues_suppressed = int(getattr(relationship_context, "relationship_cues_suppressed", 0) or 0)
    relationship_singleton_conflicts_omitted = int(getattr(relationship_context, "singleton_conflicts_omitted", 0) or 0)
    temporal = getattr(relationship_context, "mood_moment", None) if relationship_context is not None else None
    temporal_mood_candidates = int(getattr(temporal, "mood_candidates", 0) or 0)
    temporal_moment_candidates = int(getattr(temporal, "moment_candidates", 0) or 0)
    temporal_user_mood_included = False
    temporal_moments_included = 0
    personality_stability = getattr(continuity_profile, "personality_stability", None)
    personality_history_rows_considered = int(getattr(personality_stability, "history_rows_considered", 0) or 0)
    personality_repeated_opening_runs = int(getattr(personality_stability, "repeated_opening_runs", 0) or 0)
    personality_identity_reset_signals = int(getattr(personality_stability, "identity_reset_signals", 0) or 0)
    personality_long_history_rows_considered = int(getattr(personality_stability, "long_history_rows_considered", 0) or 0)
    personality_opening_diversity_percent = int(getattr(personality_stability, "opening_diversity_percent", 100) or 0)
    personality_repeated_opening_percent = int(getattr(personality_stability, "repeated_opening_percent", 0) or 0)
    personality_operator_bleed_signals = int(getattr(personality_stability, "operator_bleed_signals", 0) or 0)
    personality_affection_inflation_signals = int(getattr(personality_stability, "affection_inflation_signals", 0) or 0)
    personality_tone_monoculture_risk = bool(getattr(personality_stability, "tone_monoculture_risk", False))
    personality_lane_adaptation_stable = bool(getattr(personality_stability, "lane_adaptation_stable", True))
    personality_drift_risk = str(getattr(personality_stability, "drift_risk", "bounded") or "bounded")
    emotional_guard = getattr(relationship_context, "emotional_guard", None) if relationship_context is not None else None
    emotional_current_mood_count = int(getattr(emotional_guard, "explicit_current_mood_count", 0) or 0)
    emotional_affection_escalation_allowed = bool(getattr(emotional_guard, "affection_escalation_allowed", False))
    emotional_progress_claim_allowed = bool(getattr(emotional_guard, "new_relationship_progress_claim_allowed", False))
    assembly_plan = build_context_assembly_plan(
        quality=quality,
        history_count=len(quality_history),
        recent_history_count=len(history_rows),
        curated_memory_count=len(memory_rows),
        relationship_context=relationship_context,
    )
    lane_candidates = {lane.lane: lane.candidate_count for lane in assembly_plan.lanes}
    lane_candidates["active_thread"] = lane_candidates.get("active_thread", 0) + len(cross_session_turns)
    budget_candidates = {
        **lane_candidates,
        "optional_context": (5 if quality.should_include_operational_context else 2) + sum(1 for item in pinned_resolutions if item.active),
    }
    budget_plan = build_context_budget_plan(
        input_budget_tokens=admission_budget,
        essential_tokens=min(essential_tokens, admission_budget),
        lane_candidates=budget_candidates,
        include_operational_context=quality.should_include_operational_context,
    )
    budget_ledger = ContextBudgetLedger(budget_plan)
    lane_included: set[str] = {"current_turn"}
    lane_omitted: set[str] = set()
    if quality.correction_handling.explicit_correction:
        lane_included.add("correction_evidence")

    pinned_included = 0
    pinned_omitted = 0
    pinned_prompt_chars = 0
    for resolved in pinned_resolutions:
        if not resolved.active:
            continue
        if casual_fast_path:
            pinned_omitted += 1
            omitted_sections.append("pinned_working_context")
            continue
        block = resolved.prompt_block()
        block_tokens = estimate_tokens(block) if block else 0
        fits_pin_bound = bool(block and pinned_prompt_chars + len(block) <= MAX_PINNED_CONTEXT_PROMPT_CHARS)
        if fits_pin_bound and budget_ledger.admit("optional_context", block_tokens, global_remaining=admission_budget - used_tokens):
            selected_middle.append(block)
            used_tokens += block_tokens
            pinned_prompt_chars += len(block)
            pinned_included += 1
            included_sections.append("pinned_working_context")
        else:
            pinned_omitted += 1
            omitted_sections.append("pinned_working_context")

    # Important memories are admitted before operational context and never truncated.
    for index, (memory, important) in enumerate(memory_rows):
        if casual_fast_path or not important:
            continue
        block = _optional_block(f"IMPORTANT MEMORY {index + 1}", _memory_text(memory))
        block_tokens = estimate_tokens(block)
        if block and budget_ledger.admit("curated_memory", block_tokens, global_remaining=admission_budget - used_tokens):
            selected_middle.append(block)
            used_tokens += block_tokens
            memories_included += 1
            important_included += 1
            lane_included.add("curated_memory")
        else:
            omitted_sections.append("important_memory")
            lane_omitted.add("curated_memory")

    # Relationship continuity is one bounded, whole block. It is built only from
    # explicitly stored durable cues plus Eidolon's current self-state.
    relationship_block = ""
    casual_relationship_count = 0
    casual_relationship_categories: tuple[str, ...] = ()
    if casual_fast_path:
        relationship_block, casual_relationship_count, casual_relationship_categories = _casual_relationship_cues_block(relationship_context)
        if not relationship_block:
            preference_lines: list[str] = []
            for memory, _important in memory_rows:
                if str(memory.get("type") or "").strip().lower() != "preference":
                    continue
                text = _memory_text(memory)
                if text:
                    preference_lines.append(f"- {text}")
                if len(preference_lines) >= 2:
                    break
            if preference_lines:
                relationship_block = (
                    "EXPLICIT RELATIONSHIP OR PREFERENCE CUES\n"
                    "Use only when relevant; do not recite them just to prove memory.\n" + "\n".join(preference_lines)
                )
                casual_relationship_count = len(preference_lines)
                casual_relationship_categories = ("preference",)
    elif relationship_context is not None:
        builder = getattr(relationship_context, "to_prompt_block", None)
        relationship_block = str(builder() if callable(builder) else relationship_context).strip()
        if relationship_selected == 0:
            relationship_block = (
                "RELATIONSHIP CONTINUITY\n"
                "No explicit relationship cue is available for this turn.\n"
                "Do not invent relationship progress or infer a durable relationship fact from transcript tone."
            )
    relationship_tokens = estimate_tokens(relationship_block) if relationship_block else 0
    relationship_budget_lanes: tuple[str, ...] = tuple(
        lane for lane, count in (("mood", temporal_mood_candidates), ("important_moments", temporal_moment_candidates))
        if count > 0
    ) or ("optional_context",)
    if relationship_block and budget_ledger.admit(
        relationship_budget_lanes,
        relationship_tokens,
        global_remaining=admission_budget - used_tokens,
    ):
        selected_middle.append(relationship_block)
        used_tokens += relationship_tokens
        relationship_included = casual_relationship_count if casual_fast_path else relationship_selected
        relationship_mood_included = (not casual_fast_path)
        relationship_categories = casual_relationship_categories if casual_fast_path else tuple(getattr(relationship_context, "categories", ()) or ())
        temporal_user_mood_included = (not casual_fast_path) and bool(getattr(temporal, "user_mood", None) is not None)
        temporal_moments_included = 0 if casual_fast_path else len(tuple(getattr(temporal, "important_moments", ()) or ()))
        included_sections.append("relationship_continuity")
        if temporal_user_mood_included:
            lane_included.add("mood")
        if temporal_moments_included:
            lane_included.add("important_moments")
    elif relationship_block:
        omitted_sections.append("relationship_continuity")
        if temporal_mood_candidates:
            lane_omitted.add("mood")
        if temporal_moment_candidates:
            lane_omitted.add("important_moments")

    # Admit one explicitly matched older active-thread turn when it falls outside
    # the recent suffix. It remains a complete historical turn and is never inferred
    # from another session.
    active_thread_text = ""
    cross_session_included = 0
    cross_session_omitted = 0
    active_offset = assembly_plan.active_thread_offset
    if isinstance(active_offset, int) and 0 <= active_offset < len(quality_history):
        active_turn = quality_history[len(quality_history) - 1 - active_offset]
        recent_texts = {_history_turn_text(turn) for turn in history_rows}
        candidate_text = _history_turn_text(active_turn)
        if candidate_text and candidate_text not in recent_texts:
            active_block = _optional_block("ACTIVE THREAD TURN", candidate_text)
            active_tokens = estimate_tokens(active_block)
            if budget_ledger.admit("active_thread", active_tokens, global_remaining=admission_budget - used_tokens):
                selected_middle.append(active_block)
                used_tokens += active_tokens
                active_thread_text = candidate_text
                lane_included.add("active_thread")
                included_sections.append("active_thread")
            else:
                lane_omitted.add("active_thread")
                omitted_sections.append("active_thread")
        elif candidate_text:
            lane_included.add("active_thread")

    # Cross-session context is admitted only from the explicit or strongly matched
    # links returned by the provider-free linker. Sessions remain separate and each
    # linked turn is a whole completed record.
    current_prompt_turns = {_history_turn_text(turn) for turn in history_rows}
    if active_thread_text:
        current_prompt_turns.add(active_thread_text)
    for linked in (() if casual_fast_path else cross_session_turns):
        candidate_text = _history_turn_text(dict(linked.turn))
        if not candidate_text or candidate_text in current_prompt_turns:
            continue
        block = _optional_block("RELATED SESSION TURN", candidate_text)
        block_tokens = estimate_tokens(block) if block else 0
        if block and budget_ledger.admit("active_thread", block_tokens, global_remaining=admission_budget - used_tokens):
            selected_middle.append(block)
            used_tokens += block_tokens
            cross_session_included += 1
            current_prompt_turns.add(candidate_text)
            lane_included.add("active_thread")
            included_sections.append("cross_session_thread")
        else:
            cross_session_omitted += 1
            lane_omitted.add("active_thread")
            omitted_sections.append("cross_session_thread")

    # Admit the newest complete session turns first, then render the selected suffix
    # chronologically. Failed, cancelled, and partial turns never enter this section.
    selected_history: list[str] = []
    for turn in reversed(history_rows):
        block = _optional_block("RECENT SESSION TURN", _history_turn_text(turn))
        block_tokens = estimate_tokens(block) if block else 0
        if block and budget_ledger.admit("recent_conversation", block_tokens, global_remaining=admission_budget - used_tokens):
            selected_history.append(block)
            used_tokens += block_tokens
            history_included += 1
        else:
            omitted_sections.append("session_history")
    if selected_history:
        selected_middle.extend(reversed(selected_history))
        included_sections.append("session_history")
        lane_included.add("recent_conversation")
    elif history_rows:
        lane_omitted.add("recent_conversation")

    cognitive_block = str(cognitive_context or "").strip()
    if cognitive_block and not casual_fast_path:
        cognitive_tokens = estimate_tokens(cognitive_block)
        if budget_ledger.admit("optional_context", cognitive_tokens, global_remaining=admission_budget - used_tokens):
            selected_middle.append(cognitive_block)
            used_tokens += cognitive_tokens
            included_sections.append("cognitive_context")
        else:
            omitted_sections.append("cognitive_context")

    active_goals = self_model.get("active_goals") or []
    optional_blocks: list[tuple[str, str]] = []
    if not casual_fast_path:
        optional_blocks.append(("desires_and_values", _optional_block("DESIRES AND VALUES", desires)))
        if quality.should_include_operational_context:
            optional_blocks.extend([
                ("identity_and_active_goals", _optional_block("IDENTITY AND ACTIVE GOALS", {"name": name, "active_goals": active_goals})),
                ("active_project_context", _optional_block("ACTIVE PROJECT CONTEXT", project_context)),
                ("structured_goal_context", _optional_block("STRUCTURED GOAL CONTEXT", goal_context)),
                ("task_queue_context", _optional_block("TASK QUEUE CONTEXT", task_context)),
            ])
        else:
            optional_blocks.append(("identity", _optional_block("IDENTITY", {"name": name})))
    for section_name, block in optional_blocks:
        block_tokens = estimate_tokens(block) if block else 0
        if block and budget_ledger.admit("optional_context", block_tokens, global_remaining=admission_budget - used_tokens):
            selected_middle.append(block)
            used_tokens += block_tokens
            included_sections.append(section_name)
        elif block:
            omitted_sections.append(section_name)

    for index, (memory, important) in enumerate(memory_rows):
        if casual_fast_path or important:
            continue
        block = _optional_block(f"RELATED OR RECENT MEMORY {index + 1}", _memory_text(memory))
        block_tokens = estimate_tokens(block)
        if block and budget_ledger.admit("curated_memory", block_tokens, global_remaining=admission_budget - used_tokens):
            selected_middle.append(block)
            used_tokens += block_tokens
            memories_included += 1
            lane_included.add("curated_memory")
        else:
            omitted_sections.append("regular_memory")
            lane_omitted.add("curated_memory")

    for lane in assembly_plan.lanes:
        if lane.enabled and lane.lane not in lane_included:
            lane_omitted.add(lane.lane)

    prompt = "\n\n".join([system_part, continuity_part, *protected_control_parts, *selected_middle, guidance_part, latest_part])
    estimated_prompt_tokens = estimate_tokens(prompt)
    prompt_lane = "casual_fast" if casual_fast_path else "governed_operator"
    fast_path_bound_passed = (not casual_fast_path) or estimated_prompt_tokens <= casual_bound_tokens
    if casual_fast_path:
        # These categories are deliberately excluded from the provider prompt even
        # though their internal runtime projections remain available in receipts.
        omitted_sections.extend([
            "cognitive_architecture", "operational_projection", "planning_projection",
            "campaign_projection", "project_context", "task_context", "release_context",
            "action_projection", "self_maintenance_projection",
        ])
    prompt_categories_included = tuple(dict.fromkeys([
        "identity_safety",
        *(("immediate_user_grounding",) if immediate_grounding.block else ()),
        *(("explicit_controls",) if protected_control_parts else ()),
        *(("relationship_preference_cues",) if relationship_included else ()),
        *(("recent_turns",) if history_included else ()),
        *included_sections,
        "casual_contract" if casual_fast_path else "governed_response_contract",
        "latest_message",
    ]))
    prompt_categories_omitted = tuple(dict.fromkeys(omitted_sections))
    quality_diagnostics = build_conversation_quality_diagnostics(
        quality,
        input_budget_tokens=input_budget,
        estimated_prompt_tokens=estimated_prompt_tokens,
        essential_tokens=essential_tokens,
        included_sections=included_sections,
        omitted_sections=omitted_sections,
        history_candidates=len(history_rows),
        history_included=history_included,
        memory_candidates=len(memory_rows),
        memories_included=memories_included,
        relationship_candidates=relationship_candidates,
        relationship_included=relationship_included,
    )
    budget_usage = budget_ledger.public_summary()
    provenance_states: dict[str, int] = {}
    for memory, _important in memory_rows:
        provenance = memory.get("provenance") if isinstance(memory.get("provenance"), dict) else {}
        state = str(provenance.get("origin") or memory.get("provenance_state") or "legacy_unknown")
        provenance_states[state] = provenance_states.get(state, 0) + 1
    metrics = ConversationContextMetrics(
        context_size=context_size,
        reserved_output_tokens=max_tokens,
        safety_margin_tokens=safety_margin,
        input_budget_tokens=input_budget,
        estimated_prompt_tokens=estimated_prompt_tokens,
        essential_tokens=essential_tokens,
        memory_candidates=len(memory_rows),
        memories_included=memories_included,
        history_turn_candidates=len(history_rows),
        history_turns_included=history_included,
        history_turns_omitted=max(0, len(history_rows) - history_included),
        important_memories_included=important_included,
        memories_omitted=max(0, len(memory_rows) - memories_included),
        relationship_cue_candidates=relationship_candidates,
        relationship_cues_included=relationship_included,
        relationship_cues_omitted=max(0, relationship_candidates - relationship_included),
        relationship_mood_included=relationship_mood_included,
        relationship_categories_included=relationship_categories,
        optional_sections_included=tuple(included_sections),
        optional_sections_omitted=tuple(omitted_sections),
        temporal_mood_candidates=temporal_mood_candidates,
        temporal_user_mood_included=temporal_user_mood_included,
        temporal_important_moment_candidates=temporal_moment_candidates,
        temporal_important_moments_included=temporal_moments_included,
        continuity_lane=continuity_lane,
        personality_guard_included=True,
        relationship_cues_suppressed=relationship_cues_suppressed,
        relationship_singleton_conflicts_omitted=relationship_singleton_conflicts_omitted,
        relationship_memory_policy=relationship_memory_policy,
        personality_history_rows_considered=personality_history_rows_considered,
        personality_repeated_opening_runs=personality_repeated_opening_runs,
        personality_identity_reset_signals=personality_identity_reset_signals,
        personality_long_history_rows_considered=personality_long_history_rows_considered,
        personality_opening_diversity_percent=personality_opening_diversity_percent,
        personality_repeated_opening_percent=personality_repeated_opening_percent,
        personality_operator_bleed_signals=personality_operator_bleed_signals,
        personality_affection_inflation_signals=personality_affection_inflation_signals,
        personality_tone_monoculture_risk=personality_tone_monoculture_risk,
        personality_lane_adaptation_stable=personality_lane_adaptation_stable,
        personality_drift_risk=personality_drift_risk,
        emotional_current_mood_count=emotional_current_mood_count,
        emotional_affection_escalation_allowed=emotional_affection_escalation_allowed,
        emotional_progress_claim_allowed=emotional_progress_claim_allowed,
        conversation_turn_intent=quality.turn_intent.primary_intent,
        conversation_intent_flags=quality.turn_intent.flags,
        conversation_response_length=quality.response_shape.length_mode,
        conversation_response_depth=quality.response_shape.depth_mode,
        conversation_response_target_min_words=quality.response_shape.target_min_words,
        conversation_response_target_max_words=quality.response_shape.target_max_words,
        conversation_quality_relevance=quality.quality_signals.relevance_mode,
        conversation_clarity_risk=quality.quality_signals.clarity_risk,
        conversation_repetition_risk=quality.quality_signals.repetition_risk,
        conversation_current_question_count=quality.quality_signals.current_question_count,
        conversation_open_question_signals=quality.quality_signals.open_assistant_question_signals,
        conversation_unresolved_thread_count=len(quality.unresolved_threads.items),
        conversation_matching_unresolved_threads=quality.unresolved_threads.matching_item_count,
        conversation_unresolved_questions=quality.unresolved_threads.unresolved_question_count,
        conversation_commitment_signals=quality.unresolved_threads.assistant_commitment_signal_count,
        conversation_blocker_signals=quality.unresolved_threads.blocker_count,
        conversation_unfinished_subjects=quality.unresolved_threads.unfinished_subject_count,
        conversation_callback_candidates=quality.callbacks.candidate_count,
        conversation_callbacks_selected=quality.callbacks.selected_count,
        conversation_topic_transition=quality.topic_transition.transition_kind,
        conversation_topic_transition_confidence=quality.topic_transition.confidence,
        conversation_topic_match_offset=quality.topic_transition.matched_turn_offset,
        conversation_correction_kind=quality.correction_handling.correction_kind,
        conversation_correction_target_scope=quality.correction_handling.target_scope,
        conversation_correction_acknowledge_once=quality.correction_handling.acknowledge_once,
        conversation_stale_claim_suppression=quality.correction_handling.stale_claim_suppression_required,
        conversation_personality_expression_mode=quality.personality_expression.expression_mode,
        conversation_personality_expression_lane=quality.personality_expression.current_lane,
        conversation_personality_lane_transition=quality.personality_expression.lane_transition,
        conversation_personality_operator_bleed_risk=quality.personality_expression.operator_language_bleed_risk,
        conversation_personality_therapy_script_risk=quality.personality_expression.therapy_script_repetition_risk,
        conversation_personality_affection_inflation_signals=quality.personality_expression.affection_inflation_signals,
        natural_identity_interaction_lane=identity_foundation.interaction_lane,
        natural_identity_history_available=identity_foundation.history_available,
        natural_identity_relationship_cue_count=identity_foundation.relationship_cue_count,
        natural_identity_self_introduction_allowed=identity_foundation.self_introduction_allowed,
        natural_greeting_kind=greeting_control.greeting_kind,
        natural_greeting_suppress_new=greeting_control.suppress_new_greeting,
        natural_greeting_suppress_self_introduction=greeting_control.suppress_self_introduction,
        natural_greeting_repeated_opening_runs=greeting_control.repeated_opening_runs,
        natural_greeting_variation_required=greeting_control.variation_required,
        natural_thread_mode=intent_topic_continuity.thread_mode,
        natural_thread_deictic_follow_up=intent_topic_continuity.deictic_follow_up,
        natural_thread_prior_preserved=intent_topic_continuity.prior_thread_preserved,
        natural_correction_recent_count=correction_preference.recent_correction_count,
        natural_correction_propagates=correction_preference.corrected_premise_propagates,
        natural_preference_stored_applies=correction_preference.stored_preference_applies,
        natural_preference_current_override=correction_preference.current_turn_override,
        natural_preference_scope=correction_preference.propagation_scope,
        natural_affection_response_mode=affection_nickname.affection_response_mode,
        natural_nickname_use_mode=affection_nickname.nickname_use_mode,
        natural_nickname_stored_available=affection_nickname.stored_nickname_available,
        natural_nickname_current_request=affection_nickname.explicit_nickname_request,
        natural_nickname_current_rejection=affection_nickname.explicit_nickname_rejection,
        natural_response_effective_length=response_resolution.effective_length_mode,
        natural_response_effective_depth=response_resolution.effective_depth_mode,
        natural_response_effective_format=response_resolution.effective_format,
        natural_response_resolution_source=response_resolution.resolution_source,
        natural_response_target_min_words=response_resolution.target_min_words,
        natural_response_target_max_words=response_resolution.target_max_words,
        conversation_quality_diagnostics=quality_diagnostics,
        context_lane_order=assembly_plan.lane_order,
        context_lane_candidates=lane_candidates,
        context_lanes_included=tuple(name for name in assembly_plan.lane_order if name in lane_included),
        context_lanes_omitted=tuple(name for name in assembly_plan.lane_order if name in lane_omitted),
        context_active_thread_offset=assembly_plan.active_thread_offset,
        context_assembly_schema_version=assembly_plan.schema_version,
        context_ranked_candidate_count=int(ranking_summary.get("candidate_count", 0)),
        context_top_rank_score=int(ranking_summary.get("top_total_score", 0)),
        context_ranked_lexical_matches=int(ranking_summary.get("lexical_match_count", 0)),
        context_ranked_operator_curated=int(ranking_summary.get("operator_curated_count", 0)),
        context_ranked_relationship_relevant=int(ranking_summary.get("relationship_relevant_count", 0)),
        context_salient_candidate_count=int(salience_summary.get("salient_candidate_count", 0)),
        context_salience_reservations=int(salience_summary.get("reservations_applied", 0)),
        context_recent_trivial_demotions=int(salience_summary.get("recent_trivial_demotions", 0)),
        context_ranking_provider_invoked=False,
        context_assembly_writes_state=False,
        context_topic_segment_count=topic_segmentation.segment_count,
        context_topic_active_turn_count=topic_segmentation.active_turn_count,
        context_topic_unrelated_turns_excluded=topic_segmentation.unrelated_turns_excluded,
        context_topic_selection_reason=topic_segmentation.selection_reason,
        context_topic_query_overlap_percent=topic_segmentation.query_overlap_percent,
        context_topic_provider_invoked=topic_segmentation.provider_invoked,
        context_budget_allocated_tokens=dict(budget_usage.get("allocated_tokens") or {}),
        context_budget_used_tokens=dict(budget_usage.get("used_tokens") or {}),
        context_budget_shared_reserve_tokens=int(budget_usage.get("shared_reserve_tokens", 0)),
        context_budget_shared_reserve_used=int(budget_usage.get("shared_reserve_used", 0)),
        context_budget_omissions_by_lane=dict(budget_usage.get("omissions_by_lane") or {}),
        context_budget_omission_reasons=dict(budget_usage.get("omission_reasons") or {}),
        context_budget_silent_truncation_allowed=bool(budget_usage.get("silent_truncation_allowed", False)),
        context_correction_records=int(correction_retrieval_summary.get("correction_record_count", 0)),
        context_correction_exact_suppressed=int(correction_retrieval_summary.get("exact_digest_suppressed", 0)),
        context_correction_explicit_link_suppressed=int(correction_retrieval_summary.get("explicit_link_suppressed", 0)),
        context_correction_ambiguous_similarity_suppressed=int(correction_retrieval_summary.get("ambiguous_similarity_suppressed", 0)),
        context_correction_provider_invoked=bool(correction_retrieval_summary.get("provider_invoked", False)),
        context_cross_session_candidate_sessions=cross_session_plan.candidate_session_count,
        context_cross_session_candidate_turns=cross_session_plan.candidate_turn_count,
        context_cross_session_linked_sessions=cross_session_plan.linked_session_count,
        context_cross_session_linked_turns=cross_session_plan.linked_turn_count,
        context_cross_session_turns_included=cross_session_included,
        context_cross_session_turns_omitted=cross_session_omitted,
        context_cross_session_provider_invoked=cross_session_plan.provider_invoked,
        context_stale_summary_candidates=stale_summary_evidence.summary_count,
        context_stale_summaries_detected=stale_summary_evidence.stale_count,
        context_stale_summaries_suppressed=stale_summary_evidence.stale_count,
        context_stale_summary_corrected_conflicts=stale_summary_evidence.corrected_conflicts,
        context_stale_summary_retracted_conflicts=stale_summary_evidence.retracted_conflicts,
        context_stale_summary_deleted_conflicts=stale_summary_evidence.deleted_conflicts,
        context_stale_summary_current_session_conflicts=stale_summary_evidence.current_session_conflicts,
        context_stale_summary_provider_invoked=stale_summary_evidence.provider_invoked,
        context_provenance_states=dict(sorted(provenance_states.items())),
        conversation_control_response_mode=preference_profile.mode,
        conversation_control_response_format=preference_profile.format,
        conversation_control_preference_included=preference_included,
        conversation_control_temporary_instruction_count=len(instruction_resolutions),
        conversation_control_pinned_context_candidates=len(pinned_resolutions),
        conversation_control_pinned_context_active=sum(1 for item in pinned_resolutions if item.active),
        conversation_control_pinned_context_included=pinned_included,
        conversation_control_pinned_context_omitted=pinned_omitted,
        conversation_control_pinned_context_expired=sum(1 for item in pinned_resolutions if item.expired),
        conversation_control_pinned_context_kinds=tuple(item.kind for item in pinned_resolutions if item.active),
        conversation_control_pinned_context_scopes=tuple(item.scope for item in pinned_resolutions if item.active),
        conversation_control_temporary_scopes=tuple(item.scope for item in instruction_resolutions),
        conversation_control_current_topic_active=any(item.scope == "current_topic" and item.active for item in instruction_resolutions),
        conversation_control_provider_invoked=False,
        conversation_control_writes_state=False,
        prompt_lane=prompt_lane,
        provider_prompt_budget_tokens=(casual_bound_tokens if casual_fast_path else input_budget),
        fast_path_bound_passed=fast_path_bound_passed,
        prompt_section_categories_included=prompt_categories_included,
        prompt_section_categories_omitted=prompt_categories_omitted,
        prompt_metrics_content_free=True,
        natural_quality_repeated_greeting_suppressed=natural_quality_profile.repeated_greeting_suppressed,
        natural_quality_project_redirect_suppressed=natural_quality_profile.unsolicited_project_redirect_suppressed,
        natural_quality_direct_answer_required=natural_quality_profile.direct_answer_required,
        natural_quality_active_topic_required=natural_quality_profile.active_topic_continuation_required,
        natural_quality_emotional_ack_required=natural_quality_profile.emotional_subtext_acknowledgment_required,
        natural_quality_optional_question_suppressed=natural_quality_profile.optional_closing_question_suppressed,
        natural_quality_ack_target_min_words=natural_quality_profile.acknowledgement_target_min_words,
        natural_quality_ack_target_max_words=natural_quality_profile.acknowledgement_target_max_words,
        natural_quality_canned_phrase_suppressed=natural_quality_profile.canned_phrase_suppressed,
        natural_quality_present_stakes_grounding_required=natural_quality_profile.present_stakes_grounding_required,
        natural_quality_profile_digest=str(natural_quality_public.get("profile_digest") or ""),
        immediate_grounding_present=bool(immediate_grounding.block),
        immediate_recall_requested=immediate_grounding.immediate_recall_requested,
        immediate_exact_repeat_requested=immediate_grounding.exact_repeat_requested,
        immediate_correction_protected=bool(immediate_grounding.current_message_correction or immediate_grounding.protected_recent_correction),
        immediate_grounding_state=immediate_grounding.grounding_state,
        current_message_correction_protected=immediate_grounding.current_message_correction,
        compound_grounding_explanation_requested=immediate_grounding.compound_explanation_requested,
        historical_memory_query=immediate_grounding.historical_memory_query,
        attributable_historical_memory_available=immediate_grounding.attributable_memory_available,
        historical_memory_evidence_state=immediate_grounding.historical_evidence_state,
        historical_memory_evidence_requested=immediate_grounding.historical_evidence_requested,
        historical_uncertainty_required=immediate_grounding.historical_uncertainty_required,
        historical_evidence_class_counts=immediate_grounding.historical_evidence_class_counts(),
        historical_provenance_state_digest=immediate_grounding.provenance_state_digest(),
        historical_user_authored_evidence_count=immediate_grounding.historical_user_authored_count,
        historical_assistant_authored_non_evidence_count=immediate_grounding.historical_assistant_authored_non_evidence_count,
        historical_user_nonassertive_count=immediate_grounding.historical_user_nonassertive_count,
        historical_malformed_evidence_count=immediate_grounding.historical_malformed_count,
        historical_conflict_count=immediate_grounding.historical_conflict_count,
        historical_weak_match_rejected_count=immediate_grounding.historical_weak_match_rejected_count,
        historical_match_strength=immediate_grounding.historical_match_strength,
    )
    return ConversationPromptPacket(prompt=prompt, metrics=metrics)
