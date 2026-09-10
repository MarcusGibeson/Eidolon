from __future__ import annotations

"""Explicit, read-only v1085.0 conversation context-lane architecture.

The plan names and bounds the sources already eligible for prompt assembly. It
contains only counts, states, lane codes, and offsets. It never returns message
or memory content, writes runtime state, or contacts a provider.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence
from context_assembly_architecture_context_assembly import (
    SymbolDependencies as _ContextAssemblyArchitectureContextAssemblySymbolDependencies,
    build_context_assembly_plan as _build_context_assembly_plan_implementation,
    context_assembly_contains_private_fields as _context_assembly_contains_private_fields_implementation,
)


CONTEXT_ASSEMBLY_SCHEMA_VERSION = "1"
CONTEXT_LANE_ORDER = (
    "current_turn",
    "correction_evidence",
    "active_thread",
    "recent_conversation",
    "mood",
    "important_moments",
    "curated_memory",
)


@dataclass(frozen=True)
class ContextLaneEvidence:
    lane: str
    admission_order: int
    candidate_count: int
    item_limit: int
    protected: bool
    enabled: bool
    admission_policy: str

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextAssemblyPlan:
    lanes: tuple[ContextLaneEvidence, ...]
    active_thread_offset: int | None
    current_turn_protected: bool = True
    read_only: bool = True
    provider_invoked: bool = False
    writes_state: bool = False
    rewrites_transcript: bool = False
    mutates_memory: bool = False
    schema_version: str = CONTEXT_ASSEMBLY_SCHEMA_VERSION

    @property
    def lane_order(self) -> tuple[str, ...]:
        return tuple(lane.lane for lane in self.lanes)

    def lane(self, name: str) -> ContextLaneEvidence:
        for lane in self.lanes:
            if lane.lane == name:
                return lane
        raise KeyError(name)

    def public_summary(self) -> dict[str, Any]:
        return {
            "type": "conversation_context_assembly_plan",
            "schema_version": self.schema_version,
            "lane_order": list(self.lane_order),
            "lanes": [lane.public_summary() for lane in self.lanes],
            "active_thread_offset": self.active_thread_offset,
            "current_turn_protected": self.current_turn_protected,
            "read_only": self.read_only,
            "provider_invoked": self.provider_invoked,
            "writes_state": self.writes_state,
            "rewrites_transcript": self.rewrites_transcript,
            "mutates_memory": self.mutates_memory,
            "contains_context_content": False,
        }


def _active_thread_offset(quality: Any, history_count: int) -> int | None:
    transition = getattr(quality, "topic_transition", None)
    transition_kind = str(getattr(transition, "transition_kind", "") or "")
    offset = getattr(transition, "matched_turn_offset", None)
    if transition_kind in {"resumption", "return"} and isinstance(offset, int) and 0 <= offset < history_count:
        return offset
    unresolved = getattr(quality, "unresolved_threads", None)
    for item in tuple(getattr(unresolved, "items", ()) or ()):
        candidate = getattr(item, "turn_offset", None)
        if bool(getattr(item, "current_turn_match", False)) and isinstance(candidate, int) and 0 <= candidate < history_count:
            return candidate
    return None


def _build_context_assembly_architecture_context_assembly_dependencies() -> _ContextAssemblyArchitectureContextAssemblySymbolDependencies:
    return _ContextAssemblyArchitectureContextAssemblySymbolDependencies(
        CONTEXT_LANE_ORDER=CONTEXT_LANE_ORDER,
        ContextAssemblyPlan=ContextAssemblyPlan,
        ContextLaneEvidence=ContextLaneEvidence,
        Mapping=Mapping,
        Sequence=Sequence,
        _active_thread_offset=_active_thread_offset,
    )

def build_context_assembly_plan(*, quality: Any, history_count: int, recent_history_count: int, curated_memory_count: int, relationship_context: Any=None) -> ContextAssemblyPlan:
    return _build_context_assembly_plan_implementation(quality=quality, history_count=history_count, recent_history_count=recent_history_count, curated_memory_count=curated_memory_count, relationship_context=relationship_context, _deps=_build_context_assembly_architecture_context_assembly_dependencies())



def context_assembly_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    return _context_assembly_contains_private_fields_implementation(value, _deps=_build_context_assembly_architecture_context_assembly_dependencies())

