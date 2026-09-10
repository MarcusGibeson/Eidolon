from __future__ import annotations

"""v1264.6-v1264.8 alternative-plan freshness, tamper, concurrency, and handoff hardening."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping

from alternative_planning_foundations import PLAN_DENIED_AUTHORITY, validate_alternative_plan
from priority_selection_reliability import check_priority_selection_freshness, validate_priority_selection_reliability
from alternative_planning_reliability_alternative_planning import (
    SymbolDependencies as _AlternativePlanningReliabilityAlternativePlanningSymbolDependencies,
    build_alternative_planning_operator_handoff as _build_alternative_planning_operator_handoff_implementation,
    inspect_alternative_planning_health as _inspect_alternative_planning_health_implementation,
)


SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1264.8"
REQUIRED_SURFACES = (
    "conscious_agent/evidence_based_project_inspection.py",
    "conscious_agent/development_backlog_generation.py",
    "conscious_agent/priority_selection.py",
    "conscious_agent/alternative_planning_foundations.py",
    "conscious_agent/alternative_planning.py",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def validate_alternative_plan_reliability(plan: Mapping[str, Any], selection: Mapping[str, Any], backlog: Mapping[str, Any]) -> dict[str, Any]:
    priority_ok = bool(validate_priority_selection_reliability(selection, backlog).get("ok"))
    plan_ok = bool(validate_alternative_plan(plan, selection, backlog).get("ok"))
    selected = plan.get("selected_approach_id")
    selected_unique = selected is None or sum(1 for row in plan.get("approaches") or [] if row.get("approach_id") == selected) == 1
    predicted_not_observed = all(fm.get("epistemic_status") == "predicted" for row in plan.get("approaches") or [] for fm in row.get("predicted_failure_modes") or [])
    no_authority = all(plan.get(key) is expected for key, expected in PLAN_DENIED_AUTHORITY.items())
    ok = priority_ok and plan_ok and selected_unique and predicted_not_observed and no_authority
    row = {
        "ok": ok, "status": "alternative_plan_reliability_valid" if ok else "alternative_plan_reliability_invalid",
        "priority_reliability_valid": priority_ok, "plan_valid": plan_ok, "selected_approach_unique": selected_unique,
        "failure_modes_remain_predictions": predicted_not_observed, "authority_denied": no_authority,
        "read_only": True, "content_minimized": True, **PLAN_DENIED_AUTHORITY,
    }
    row["reliability_digest"] = _digest(row)
    return row


def check_alternative_plan_freshness(plan: Mapping[str, Any], selection: Mapping[str, Any], backlog: Mapping[str, Any], source_root: str | Path) -> dict[str, Any]:
    priority_fresh = check_priority_selection_freshness(selection, backlog, source_root)
    plan_valid = validate_alternative_plan(plan, selection, backlog)
    fresh = bool(priority_fresh.get("ok")) and bool(plan_valid.get("ok"))
    row = {
        "ok": fresh, "status": "alternative_plan_fresh" if fresh else "alternative_plan_stale", "stale": not fresh,
        "source_fresh": bool(priority_fresh.get("source_fresh")), "priority_fresh": bool(priority_fresh.get("ok")),
        "plan_valid": bool(plan_valid.get("ok")), "selection_digest": str(selection.get("selection_digest") or ""),
        "plan_selection_digest": str(plan.get("selection_digest") or ""), "source_manifest_digest": str(backlog.get("source_manifest_digest") or ""),
        "read_only": True, "content_minimized": True, **PLAN_DENIED_AUTHORITY,
    }
    row["freshness_digest"] = _digest(row)
    return row


def deterministic_concurrent_plan_digests(build_fn, *, workers: int = 8) -> dict[str, Any]:
    workers = max(1, min(int(workers), 16))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        digests = list(pool.map(lambda _: str(build_fn().get("plan_digest") or ""), range(workers)))
    unique = sorted(set(digests))
    row = {
        "ok": len(unique) == 1 and bool(unique[0]),
        "status": "alternative_plan_concurrent_duplicate_converged" if len(unique) == 1 and bool(unique[0]) else "alternative_plan_concurrent_duplicate_diverged",
        "attempt_count": workers, "unique_plan_digest_count": len(unique), "plan_digest": unique[0] if len(unique) == 1 else "",
        "execution_performed": False, "read_only": True, **PLAN_DENIED_AUTHORITY,
    }
    row["concurrency_digest"] = _digest(row)
    return row


def _build_alternative_planning_reliability_alternative_planning_dependencies() -> _AlternativePlanningReliabilityAlternativePlanningSymbolDependencies:
    return _AlternativePlanningReliabilityAlternativePlanningSymbolDependencies(
        CONTRACT_VERSION=CONTRACT_VERSION,
        PLAN_DENIED_AUTHORITY=PLAN_DENIED_AUTHORITY,
        REQUIRED_SURFACES=REQUIRED_SURFACES,
        SCHEMA_VERSION=SCHEMA_VERSION,
        __file__=__file__,
        _digest=_digest,
        hashlib=hashlib,
    )

def inspect_alternative_planning_health(*, source_root: str | Path | None=None) -> dict[str, Any]:
    return _inspect_alternative_planning_health_implementation(source_root=source_root, _deps=_build_alternative_planning_reliability_alternative_planning_dependencies())



def build_alternative_planning_operator_handoff(*, source_root: str | Path | None=None) -> dict[str, Any]:
    return _build_alternative_planning_operator_handoff_implementation(source_root=source_root, _deps=_build_alternative_planning_reliability_alternative_planning_dependencies())



__all__ = [
    "CONTRACT_VERSION", "validate_alternative_plan_reliability", "check_alternative_plan_freshness",
    "deterministic_concurrent_plan_digests", "inspect_alternative_planning_health", "build_alternative_planning_operator_handoff",
]
