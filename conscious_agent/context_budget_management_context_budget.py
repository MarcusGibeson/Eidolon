from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    ContextBudgetPlan: Any
    LaneBudgetEvidence: Any
    Mapping: Any
    Sequence: Any
    _BUDGET_LANES: Any



def build_context_budget_plan(*, input_budget_tokens: int, essential_tokens: int, lane_candidates: _deps.Mapping[str, int], include_operational_context: bool=False, _deps: SymbolDependencies) -> _deps.ContextBudgetPlan:
    input_budget = max(0, int(input_budget_tokens))
    essential = max(0, min(input_budget, int(essential_tokens)))
    discretionary = max(0, input_budget - essential)
    reserve = min(discretionary // 10, 192)
    allocatable = max(0, discretionary - reserve)
    weights = {'active_thread': 10, 'recent_conversation': 34 if include_operational_context else 42, 'mood': 6, 'important_moments': 8, 'curated_memory': 22 if include_operational_context else 26, 'optional_context': 20 if include_operational_context else 8}
    enabled = {lane: bool(lane == 'optional_context' or int(lane_candidates.get(lane, 0) or 0) > 0) for lane in _deps._BUDGET_LANES}
    active_weight = sum((weight for lane, weight in weights.items() if enabled[lane])) or 1
    raw = {lane: allocatable * weights[lane] // active_weight if enabled[lane] else 0 for lane in _deps._BUDGET_LANES}
    remainder = allocatable - sum(raw.values())
    for lane in _deps._BUDGET_LANES:
        if remainder <= 0:
            break
        if enabled[lane]:
            raw[lane] += 1
            remainder -= 1
    minimums = {'active_thread': 48, 'recent_conversation': 96, 'mood': 32, 'important_moments': 48, 'curated_memory': 96, 'optional_context': 48}
    lanes = tuple((_deps.LaneBudgetEvidence(lane=lane, allocated_tokens=raw[lane], minimum_reserved_tokens=min(raw[lane], minimums[lane]) if enabled[lane] else 0, candidate_count=max(0, int(lane_candidates.get(lane, 0) or 0)), enabled=enabled[lane]) for lane in _deps._BUDGET_LANES))
    return _deps.ContextBudgetPlan(input_budget, essential, discretionary, reserve, lanes)


def context_budget_contains_private_fields(value: _deps.Mapping[str, Any] | None, *, _deps: SymbolDependencies) -> bool:
    forbidden = {'message', 'user_message', 'assistant_response', 'content', 'thought', 'summary', 'prompt', 'transcript', 'memory', 'provider_payload', 'credentials', 'vector', 'embedding', 'receipt', 'chain_of_thought', 'reasoning_trace'}
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
