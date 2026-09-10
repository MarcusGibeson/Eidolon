from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    Iterable: Any
    Mapping: Any
    build_alternative_plan: Any
    generate_backlog_and_priority_selection: Any
    public_alternative_plan: Any
    validate_alternative_plan: Any



def generate_alternative_plan(source_root: str | Path, *, external_evidence: _deps.Iterable[_deps.Mapping[str, Any]]=(), priority_context: _deps.Iterable[_deps.Mapping[str, Any]]=(), plan_context: _deps.Iterable[_deps.Mapping[str, Any]]=(), _deps: SymbolDependencies) -> dict[str, Any]:
    backlog, selection = _deps.generate_backlog_and_priority_selection(source_root, external_evidence=external_evidence, priority_context=priority_context)
    return _deps.build_alternative_plan(selection, backlog, plan_context=plan_context)


def generate_priority_and_alternative_plan(source_root: str | Path, *, external_evidence: _deps.Iterable[_deps.Mapping[str, Any]]=(), priority_context: _deps.Iterable[_deps.Mapping[str, Any]]=(), plan_context: _deps.Iterable[_deps.Mapping[str, Any]]=(), _deps: SymbolDependencies) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    backlog, selection = _deps.generate_backlog_and_priority_selection(source_root, external_evidence=external_evidence, priority_context=priority_context)
    plan = _deps.build_alternative_plan(selection, backlog, plan_context=plan_context)
    return (backlog, selection, plan)


def inspect_alternative_planning(source_root: str | Path, *, external_evidence: _deps.Iterable[_deps.Mapping[str, Any]]=(), priority_context: _deps.Iterable[_deps.Mapping[str, Any]]=(), plan_context: _deps.Iterable[_deps.Mapping[str, Any]]=(), _deps: SymbolDependencies) -> dict[str, Any]:
    backlog, selection, plan = generate_priority_and_alternative_plan(source_root, external_evidence=external_evidence, priority_context=priority_context, plan_context=plan_context, _deps=_deps)
    validation = _deps.validate_alternative_plan(plan, selection, backlog)
    return {'ok': bool(validation.get('ok')), 'status': 'alternative_planning_inspection_ready' if validation.get('ok') else 'alternative_planning_inspection_invalid', 'public_plan': _deps.public_alternative_plan(plan), 'backlog_digest': backlog.get('backlog_digest', ''), 'selection_digest': selection.get('selection_digest', ''), 'plan_digest': plan.get('plan_digest', ''), 'read_only': True, 'content_minimized': True}
