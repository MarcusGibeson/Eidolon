from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTRACT_VERSION: Any
    PLAN_DENIED_AUTHORITY: Any
    REQUIRED_SURFACES: Any
    SCHEMA_VERSION: Any
    __file__: Any
    _digest: Any
    hashlib: Any



def inspect_alternative_planning_health(*, source_root: str | Path | None=None, _deps: SymbolDependencies) -> dict[str, Any]:
    root = Path(source_root or Path(_deps.__file__).resolve().parents[1]).resolve()
    hashes = {rel: _deps.hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in _deps.REQUIRED_SURFACES if (root / rel).is_file()}
    checks = {'required_surfaces_present': len(hashes) == len(_deps.REQUIRED_SURFACES), 'v1261_evidence_lineage_retained': (root / 'conscious_agent/evidence_based_project_inspection.py').is_file(), 'v1262_backlog_lineage_retained': (root / 'conscious_agent/development_backlog_generation.py').is_file(), 'v1263_priority_lineage_retained': (root / 'conscious_agent/priority_selection.py').is_file(), 'planning_has_no_execution_authority': True, 'planning_has_no_application_authority': True, 'planning_has_no_self_modification_authority': True, 'planning_is_read_only': True}
    row = {'ok': all(checks.values()), 'schema_version': _deps.SCHEMA_VERSION, 'contract_version': _deps.CONTRACT_VERSION, 'status': 'alternative_planning_health_ready', 'checks': checks, 'source_sha256': hashes, 'native_windows_validation': 'desktop_review_required', 'read_only': True, 'content_minimized': True, **_deps.PLAN_DENIED_AUTHORITY}
    row['health_digest'] = _deps._digest(row)
    return row


def build_alternative_planning_operator_handoff(*, source_root: str | Path | None=None, _deps: SymbolDependencies) -> dict[str, Any]:
    health = inspect_alternative_planning_health(source_root=source_root, _deps=_deps)
    row = {'ok': bool(health.get('ok')), 'schema_version': _deps.SCHEMA_VERSION, 'contract_version': _deps.CONTRACT_VERSION, 'status': 'alternative_planning_operator_handoff_ready' if health.get('ok') else 'alternative_planning_operator_handoff_blocked', 'health_digest': health.get('health_digest', ''), 'operator_review_required': True, 'desktop_focus': ['native Windows assessment-to-backlog-to-priority-to-plan flow remains path-contained', 'restart deterministic alternative generation on the same sealed priority decision', 'concurrent duplicate planning requests converge without provider calls or execution', 'stale source, backlog, or priority lineage invalidates the old plan', 'predicted failure modes remain predictions and are not presented as observed defects', 'exact strategy ties return no defensible plan instead of lexical winner selection', 'tampered and resealed approach scores or failure-mode semantics are rejected', 'selected plan grants no proposal, execution, application, installation, release, or self-update authority'], 'next_bounded_unit': 'v1265 Isolated Self-Modification', 'read_only': True, 'content_minimized': True, **_deps.PLAN_DENIED_AUTHORITY}
    row['handoff_digest'] = _deps._digest(row)
    return row
