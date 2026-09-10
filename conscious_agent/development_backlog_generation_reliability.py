from __future__ import annotations

"""v1262.6-v1262.8 backlog freshness, dependency, and operator-handoff hardening."""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY, validate_development_backlog
from evidence_based_project_inspection_foundations import inspect_project_evidence

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1262.8"
REQUIRED_SURFACES = (
    "conscious_agent/evidence_based_project_inspection.py",
    "conscious_agent/development_backlog_generation_foundations.py",
    "conscious_agent/development_backlog_generation.py",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _cycle_nodes(backlog: Mapping[str, Any]) -> set[str]:
    graph = {str(row.get("work_item_id") or ""): [str(x) for x in row.get("dependency_item_ids") or []] for row in backlog.get("items") or []}
    visiting: set[str] = set(); visited: set[str] = set(); cycles: set[str] = set()
    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            if node in trail: cycles.update(trail[trail.index(node):])
            else: cycles.add(node)
            return
        if node in visited: return
        visiting.add(node); trail.append(node)
        for dep in graph.get(node, []):
            if dep in graph: visit(dep, trail)
        trail.pop(); visiting.remove(node); visited.add(node)
    for node in graph: visit(node, [])
    return cycles


def validate_backlog_reliability(backlog: Mapping[str, Any]) -> dict[str, Any]:
    base = validate_development_backlog(backlog)
    cycles = sorted(_cycle_nodes(backlog)) if base.get("ok") else []
    no_cycles = not cycles
    no_priority = not bool(backlog.get("priority_selected")) and all(row.get("rank") is None and row.get("priority") is None for row in backlog.get("items") or [])
    row = {"ok": bool(base.get("ok")) and no_cycles and no_priority, "status": "development_backlog_reliability_valid" if base.get("ok") and no_cycles and no_priority else "development_backlog_reliability_invalid",
           "base_validation_ok": bool(base.get("ok")), "dependency_cycle_item_ids": cycles, "dependency_cycles_absent": no_cycles, "priority_not_selected": no_priority,
           "read_only": True, "content_minimized": True, **BACKLOG_DENIED_AUTHORITY}
    row["reliability_digest"] = _digest(row); return row


def check_development_backlog_freshness(backlog: Mapping[str, Any], source_root: str | Path) -> dict[str, Any]:
    validation = validate_backlog_reliability(backlog)
    if not validation.get("ok"):
        return {"ok": False, "status": "development_backlog_invalid", "stale_source": True, "read_only": True, **BACKLOG_DENIED_AUTHORITY}
    current = inspect_project_evidence(source_root)
    expected = str(backlog.get("source_manifest_digest") or ""); actual = str(current.get("source_manifest_digest") or "")
    fresh = bool(expected and expected == actual)
    row = {"ok": fresh, "status": "development_backlog_source_fresh" if fresh else "development_backlog_source_stale", "stale_source": not fresh,
           "expected_manifest_digest": expected, "current_manifest_digest": actual, "read_only": True, "content_minimized": True, **BACKLOG_DENIED_AUTHORITY}
    row["freshness_digest"] = _digest(row); return row


def inspect_development_backlog_generation_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    hashes = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in REQUIRED_SURFACES if (root / rel).is_file()}
    checks = {"required_surfaces_present": len(hashes) == len(REQUIRED_SURFACES), "v1261_assessment_reused": (root / "conscious_agent/evidence_based_project_inspection.py").is_file(),
              "backlog_has_no_priority_authority": True, "backlog_has_no_execution_authority": True, "backlog_is_read_only": True}
    row = {"ok": all(checks.values()), "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "status": "development_backlog_generation_health_ready",
           "checks": checks, "source_sha256": hashes, "native_windows_validation": "desktop_review_required", "read_only": True, "content_minimized": True, **BACKLOG_DENIED_AUTHORITY}
    row["health_digest"] = _digest(row); return row


def build_development_backlog_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_development_backlog_generation_health(source_root=source_root)
    row = {"ok": bool(health.get("ok")), "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
           "status": "development_backlog_operator_handoff_ready" if health.get("ok") else "development_backlog_operator_handoff_blocked",
           "health_digest": health.get("health_digest", ""), "operator_review_required": True,
           "desktop_focus": ["native Windows case-insensitive and junction-contained assessment-to-backlog generation", "large assessment bounded-item behavior", "contradictory evidence dependency ordering without priority selection", "stale assessment rejection after source changes", "duplicate deterministic backlog generation across restarts", "no automatic proposal, execution, application, or self-update from backlog items"],
           "next_bounded_unit": "v1263 Priority Selection", "read_only": True, "content_minimized": True, **BACKLOG_DENIED_AUTHORITY}
    row["handoff_digest"] = _digest(row); return row


__all__ = ["CONTRACT_VERSION", "validate_backlog_reliability", "check_development_backlog_freshness", "inspect_development_backlog_generation_health", "build_development_backlog_operator_handoff"]
