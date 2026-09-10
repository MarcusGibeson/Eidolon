from __future__ import annotations

"""v1264.3-v1264.5 v1261->v1262->v1263->v1264 alternative-planning integration."""

from pathlib import Path
from typing import Any, Iterable, Mapping

from priority_selection import generate_backlog_and_priority_selection
from alternative_planning_foundations import build_alternative_plan, public_alternative_plan, validate_alternative_plan
from alternative_planning_alternative import (
    SymbolDependencies as _AlternativePlanningAlternativeSymbolDependencies,
    generate_alternative_plan as _generate_alternative_plan_implementation,
    generate_priority_and_alternative_plan as _generate_priority_and_alternative_plan_implementation,
    inspect_alternative_planning as _inspect_alternative_planning_implementation,
)


CONTRACT_VERSION = "v1264.5"


def _build_alternative_planning_alternative_dependencies() -> _AlternativePlanningAlternativeSymbolDependencies:
    return _AlternativePlanningAlternativeSymbolDependencies(
        Iterable=Iterable,
        Mapping=Mapping,
        build_alternative_plan=build_alternative_plan,
        generate_backlog_and_priority_selection=generate_backlog_and_priority_selection,
        public_alternative_plan=public_alternative_plan,
        validate_alternative_plan=validate_alternative_plan,
    )

def generate_alternative_plan(source_root: str | Path, *, external_evidence: Iterable[Mapping[str, Any]]=(), priority_context: Iterable[Mapping[str, Any]]=(), plan_context: Iterable[Mapping[str, Any]]=()) -> dict[str, Any]:
    return _generate_alternative_plan_implementation(source_root, external_evidence=external_evidence, priority_context=priority_context, plan_context=plan_context, _deps=_build_alternative_planning_alternative_dependencies())



def generate_priority_and_alternative_plan(source_root: str | Path, *, external_evidence: Iterable[Mapping[str, Any]]=(), priority_context: Iterable[Mapping[str, Any]]=(), plan_context: Iterable[Mapping[str, Any]]=()) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return _generate_priority_and_alternative_plan_implementation(source_root, external_evidence=external_evidence, priority_context=priority_context, plan_context=plan_context, _deps=_build_alternative_planning_alternative_dependencies())



def inspect_alternative_planning(source_root: str | Path, *, external_evidence: Iterable[Mapping[str, Any]]=(), priority_context: Iterable[Mapping[str, Any]]=(), plan_context: Iterable[Mapping[str, Any]]=()) -> dict[str, Any]:
    return _inspect_alternative_planning_implementation(source_root, external_evidence=external_evidence, priority_context=priority_context, plan_context=plan_context, _deps=_build_alternative_planning_alternative_dependencies())



__all__ = ["CONTRACT_VERSION", "generate_alternative_plan", "generate_priority_and_alternative_plan", "inspect_alternative_planning"]
