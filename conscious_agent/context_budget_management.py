from __future__ import annotations

"""Deterministic v1085.4 context-budget allocation and admission evidence."""

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence
from context_budget_management_context_budget import (
    SymbolDependencies as _ContextBudgetManagementContextBudgetSymbolDependencies,
    build_context_budget_plan as _build_context_budget_plan_implementation,
    context_budget_contains_private_fields as _context_budget_contains_private_fields_implementation,
)


CONTEXT_BUDGET_MANAGEMENT_SCHEMA_VERSION = "1"
_BUDGET_LANES = (
    "active_thread", "recent_conversation", "mood", "important_moments", "curated_memory", "optional_context",
)


@dataclass(frozen=True)
class LaneBudgetEvidence:
    lane: str
    allocated_tokens: int
    minimum_reserved_tokens: int
    candidate_count: int
    enabled: bool
    protected: bool = False

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextBudgetPlan:
    input_budget_tokens: int
    essential_tokens: int
    discretionary_tokens: int
    shared_reserve_tokens: int
    lanes: tuple[LaneBudgetEvidence, ...]
    current_turn_protected: bool = True
    correction_evidence_protected: bool = True
    whole_record_admission: bool = True
    silent_truncation_allowed: bool = False
    read_only: bool = True
    provider_invoked: bool = False
    writes_state: bool = False
    schema_version: str = CONTEXT_BUDGET_MANAGEMENT_SCHEMA_VERSION

    def allocation(self, lane: str) -> int:
        return next((item.allocated_tokens for item in self.lanes if item.lane == lane), 0)

    def public_summary(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "type": "conversation_context_budget_plan",
            "lanes": [lane.public_summary() for lane in self.lanes],
            "content_free": True,
        }


class ContextBudgetLedger:
    def __init__(self, plan: ContextBudgetPlan) -> None:
        self.plan = plan
        self.used: dict[str, int] = {lane.lane: 0 for lane in plan.lanes}
        self.shared_used = 0
        self.omissions: dict[str, int] = {}
        self.omission_reasons: dict[str, int] = {}

    def _available(self, lanes: Sequence[str]) -> int:
        allocated = sum(self.plan.allocation(lane) for lane in lanes)
        used = sum(self.used.get(lane, 0) for lane in lanes)
        return max(0, allocated - used)

    def admit(self, lanes: str | Sequence[str], tokens: int, *, global_remaining: int) -> bool:
        names = (lanes,) if isinstance(lanes, str) else tuple(lanes)
        tokens = max(0, int(tokens))
        if tokens <= 0:
            return True
        if tokens > max(0, int(global_remaining)):
            self._omit(names, "global_budget_exhausted")
            return False
        available = self._available(names)
        reserve_available = max(0, self.plan.shared_reserve_tokens - self.shared_used)
        if tokens > available + reserve_available:
            self._omit(names, "lane_budget_exhausted")
            return False
        remaining = tokens
        for lane in names:
            lane_available = max(0, self.plan.allocation(lane) - self.used.get(lane, 0))
            consumed = min(remaining, lane_available)
            self.used[lane] = self.used.get(lane, 0) + consumed
            remaining -= consumed
            if remaining <= 0:
                break
        if remaining:
            self.shared_used += remaining
        return True

    def _omit(self, lanes: Sequence[str], reason: str) -> None:
        for lane in lanes:
            self.omissions[lane] = self.omissions.get(lane, 0) + 1
        self.omission_reasons[reason] = self.omission_reasons.get(reason, 0) + 1

    def public_summary(self) -> dict[str, Any]:
        return {
            "type": "conversation_context_budget_usage",
            "schema_version": self.plan.schema_version,
            "allocated_tokens": {lane.lane: lane.allocated_tokens for lane in self.plan.lanes},
            "used_tokens": dict(self.used),
            "shared_reserve_tokens": self.plan.shared_reserve_tokens,
            "shared_reserve_used": self.shared_used,
            "omissions_by_lane": dict(self.omissions),
            "omission_reasons": dict(self.omission_reasons),
            "whole_record_admission": True,
            "silent_truncation_allowed": False,
            "content_free": True,
            "provider_invoked": False,
            "writes_state": False,
        }


def _build_context_budget_management_context_budget_dependencies() -> _ContextBudgetManagementContextBudgetSymbolDependencies:
    return _ContextBudgetManagementContextBudgetSymbolDependencies(
        ContextBudgetPlan=ContextBudgetPlan,
        LaneBudgetEvidence=LaneBudgetEvidence,
        Mapping=Mapping,
        Sequence=Sequence,
        _BUDGET_LANES=_BUDGET_LANES,
    )

def build_context_budget_plan(*, input_budget_tokens: int, essential_tokens: int, lane_candidates: Mapping[str, int], include_operational_context: bool=False) -> ContextBudgetPlan:
    return _build_context_budget_plan_implementation(input_budget_tokens=input_budget_tokens, essential_tokens=essential_tokens, lane_candidates=lane_candidates, include_operational_context=include_operational_context, _deps=_build_context_budget_management_context_budget_dependencies())



def context_budget_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    return _context_budget_contains_private_fields_implementation(value, _deps=_build_context_budget_management_context_budget_dependencies())

