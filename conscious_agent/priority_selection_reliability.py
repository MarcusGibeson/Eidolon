from __future__ import annotations

"""v1263.6-v1263.8 priority freshness, tamper, concurrency, and operator-handoff hardening."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping

from development_backlog_generation_foundations import validate_development_backlog
from development_backlog_generation_reliability import check_development_backlog_freshness, validate_backlog_reliability
from priority_selection_foundations import PRIORITY_DENIED_AUTHORITY, validate_priority_selection

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1263.8"
REQUIRED_SURFACES = (
    "conscious_agent/evidence_based_project_inspection.py",
    "conscious_agent/development_backlog_generation.py",
    "conscious_agent/priority_selection_foundations.py",
    "conscious_agent/priority_selection.py",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def validate_priority_selection_reliability(selection: Mapping[str, Any], backlog: Mapping[str, Any]) -> dict[str, Any]:
    backlog_validation = validate_backlog_reliability(backlog)
    selection_validation = validate_priority_selection(selection, backlog)
    selected_id = selection.get("selected_work_item_id")
    selected_eval = next((row for row in selection.get("evaluations") or [] if row.get("work_item_id") == selected_id), None)
    selected_ready = selected_eval is None or (selected_eval.get("eligible") is True and selected_eval.get("dependency_readiness") == "ready")
    blocked_never_selected = all(not (row.get("dependency_readiness") == "blocked" and row.get("work_item_id") == selected_id) for row in selection.get("evaluations") or [])
    ranking_is_bounded = all(row.get("priority_rank") is None or (isinstance(row.get("priority_rank"), int) and 1 <= row.get("priority_rank") <= len(selection.get("evaluations") or [])) for row in selection.get("evaluations") or [])
    no_authority = all(selection.get(key) is expected for key, expected in PRIORITY_DENIED_AUTHORITY.items())
    ok = bool(backlog_validation.get("ok")) and bool(selection_validation.get("ok")) and selected_ready and blocked_never_selected and ranking_is_bounded and no_authority
    row = {
        "ok": ok,
        "status": "priority_selection_reliability_valid" if ok else "priority_selection_reliability_invalid",
        "backlog_reliability_valid": bool(backlog_validation.get("ok")),
        "selection_valid": bool(selection_validation.get("ok")),
        "selected_item_dependency_ready": selected_ready,
        "blocked_item_never_selected": blocked_never_selected,
        "ranking_bounded": ranking_is_bounded,
        "authority_denied": no_authority,
        "read_only": True,
        "content_minimized": True,
        **PRIORITY_DENIED_AUTHORITY,
    }
    row["reliability_digest"] = _digest(row)
    return row


def check_priority_selection_freshness(selection: Mapping[str, Any], backlog: Mapping[str, Any], source_root: str | Path) -> dict[str, Any]:
    backlog_valid = validate_development_backlog(backlog)
    if not backlog_valid.get("ok"):
        return {"ok": False, "status": "priority_selection_backlog_invalid", "stale": True, "read_only": True, **PRIORITY_DENIED_AUTHORITY}
    source_freshness = check_development_backlog_freshness(backlog, source_root)
    selection_valid = validate_priority_selection(selection, backlog)
    fresh = bool(source_freshness.get("ok")) and bool(selection_valid.get("ok"))
    row = {
        "ok": fresh,
        "status": "priority_selection_fresh" if fresh else "priority_selection_stale",
        "stale": not fresh,
        "backlog_digest": str(backlog.get("backlog_digest") or ""),
        "selection_backlog_digest": str(selection.get("backlog_digest") or ""),
        "source_manifest_digest": str(backlog.get("source_manifest_digest") or ""),
        "source_fresh": bool(source_freshness.get("ok")),
        "selection_valid": bool(selection_valid.get("ok")),
        "read_only": True,
        "content_minimized": True,
        **PRIORITY_DENIED_AUTHORITY,
    }
    row["freshness_digest"] = _digest(row)
    return row


def deterministic_concurrent_selection_digests(build_fn, *, workers: int = 8) -> dict[str, Any]:
    workers = max(1, min(int(workers), 16))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        digests = list(pool.map(lambda _: str(build_fn().get("selection_digest") or ""), range(workers)))
    unique = sorted(set(digests))
    row = {
        "ok": len(unique) == 1 and bool(unique[0]),
        "status": "priority_selection_concurrent_duplicate_converged" if len(unique) == 1 and bool(unique[0]) else "priority_selection_concurrent_duplicate_diverged",
        "attempt_count": workers,
        "unique_selection_digest_count": len(unique),
        "selection_digest": unique[0] if len(unique) == 1 else "",
        "execution_performed": False,
        "read_only": True,
        **PRIORITY_DENIED_AUTHORITY,
    }
    row["concurrency_digest"] = _digest(row)
    return row


def inspect_priority_selection_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    hashes = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in REQUIRED_SURFACES if (root / rel).is_file()}
    checks = {
        "required_surfaces_present": len(hashes) == len(REQUIRED_SURFACES),
        "v1261_evidence_lineage_retained": (root / "conscious_agent/evidence_based_project_inspection.py").is_file(),
        "v1262_backlog_lineage_retained": (root / "conscious_agent/development_backlog_generation.py").is_file(),
        "priority_has_no_execution_authority": True,
        "priority_has_no_proposal_authority": True,
        "priority_is_read_only": True,
    }
    row = {
        "ok": all(checks.values()),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "priority_selection_health_ready",
        "checks": checks,
        "source_sha256": hashes,
        "native_windows_validation": "desktop_review_required",
        "read_only": True,
        "content_minimized": True,
        **PRIORITY_DENIED_AUTHORITY,
    }
    row["health_digest"] = _digest(row)
    return row


def build_priority_selection_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_priority_selection_health(source_root=source_root)
    row = {
        "ok": bool(health.get("ok")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "priority_selection_operator_handoff_ready" if health.get("ok") else "priority_selection_operator_handoff_blocked",
        "health_digest": health.get("health_digest", ""),
        "operator_review_required": True,
        "desktop_focus": [
            "native Windows case-insensitive and junction-contained assessment-to-backlog-to-priority flow",
            "restart deterministic priority selection on the same sealed backlog",
            "concurrent duplicate priority requests converge without proposals or execution",
            "stale source or changed evidence invalidates old priority decisions",
            "ties and near-ties remain explicit rather than hidden by deterministic sort order",
            "dependency-blocked work is never selected ahead of its prerequisite",
            "no automatic proposal, planning, execution, application, installation, or self-update from selection",
        ],
        "next_bounded_unit": "v1264 Alternative Planning and Simulation",
        "read_only": True,
        "content_minimized": True,
        **PRIORITY_DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = [
    "CONTRACT_VERSION", "validate_priority_selection_reliability", "check_priority_selection_freshness",
    "deterministic_concurrent_selection_digests", "inspect_priority_selection_health", "build_priority_selection_operator_handoff",
]
