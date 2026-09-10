from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTEXT_LANE_ORDER: Any
    ContextAssemblyPlan: Any
    ContextLaneEvidence: Any
    Mapping: Any
    Sequence: Any
    _active_thread_offset: Any



def build_context_assembly_plan(*, quality: Any, history_count: int, recent_history_count: int, curated_memory_count: int, relationship_context: Any=None, _deps: SymbolDependencies) -> _deps.ContextAssemblyPlan:
    """Return the fixed seven-lane architecture with bounded content-free evidence."""
    history_count = max(0, int(history_count))
    recent_history_count = max(0, min(history_count, int(recent_history_count)))
    temporal = getattr(relationship_context, 'mood_moment', None) if relationship_context is not None else None
    mood_count = 1 if getattr(temporal, 'user_mood', None) is not None else 0
    moment_count = len(tuple(getattr(temporal, 'important_moments', ()) or ()))
    correction = getattr(quality, 'correction_handling', None)
    correction_count = 1 if bool(getattr(correction, 'explicit_correction', False)) else 0
    active_offset = _deps._active_thread_offset(quality, history_count)
    counts = {'current_turn': 1, 'correction_evidence': correction_count, 'active_thread': 1 if active_offset is not None else 0, 'recent_conversation': recent_history_count, 'mood': mood_count, 'important_moments': moment_count, 'curated_memory': max(0, int(curated_memory_count))}
    limits = {'current_turn': 1, 'correction_evidence': 1, 'active_thread': 1, 'recent_conversation': 12, 'mood': 1, 'important_moments': 3, 'curated_memory': 12}
    policies = {'current_turn': 'always_protected', 'correction_evidence': 'explicit_correction_only', 'active_thread': 'explicit_or_bounded_match_only', 'recent_conversation': 'newest_complete_turns_only', 'mood': 'one_explicit_current_mood_only', 'important_moments': 'open_explicit_curated_only', 'curated_memory': 'eligible_corrected_ranked_whole_records'}
    lanes = tuple((_deps.ContextLaneEvidence(lane=name, admission_order=index, candidate_count=counts[name], item_limit=limits[name], protected=name == 'current_turn' or (name == 'correction_evidence' and correction_count > 0), enabled=counts[name] > 0, admission_policy=policies[name]) for index, name in enumerate(_deps.CONTEXT_LANE_ORDER, start=1)))
    return _deps.ContextAssemblyPlan(lanes=lanes, active_thread_offset=active_offset)


def context_assembly_contains_private_fields(value: _deps.Mapping[str, Any] | None, *, _deps: SymbolDependencies) -> bool:
    forbidden = {'message', 'messages', 'user_message', 'assistant_response', 'content', 'thought', 'summary', 'prompt', 'transcript', 'memory_text', 'provider_payload', 'credentials', 'vector', 'embedding', 'chain_of_thought', 'reasoning_trace', 'receipt', 'acceptance_key', 'claim_token'}
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, _deps.Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, _deps.Sequence) and (not isinstance(current, (str, bytes, bytearray))):
            stack.extend(current)
    return False
