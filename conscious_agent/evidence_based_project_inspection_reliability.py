from __future__ import annotations

"""v1261.6-v1261.8 reliability, freshness, and operator-handoff evidence."""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from evidence_based_project_inspection import build_evidence_based_project_assessment, validate_project_assessment
from evidence_based_project_inspection_foundations import DENIED_AUTHORITY, inspect_project_evidence

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1261.8"
REQUIRED_SURFACES = (
    "conscious_agent/isolated_coding_execution_foundations.py",
    "conscious_agent/evidence_based_project_inspection_foundations.py",
    "conscious_agent/evidence_based_project_inspection.py",
    "conscious_agent/persistent_development_sessions.py",
    "conscious_agent/diagnostic_repair_reasoning.py",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def check_project_inspection_freshness(assessment: Mapping[str, Any], source_root: str | Path) -> dict[str, Any]:
    validation = validate_project_assessment(assessment)
    if not validation.get("ok"):
        return {"ok": False, "status": "inspection_assessment_invalid", "stale_source": True, **DENIED_AUTHORITY}
    current = inspect_project_evidence(source_root)
    expected = str(assessment.get("source_manifest_digest") or "")
    actual = str(current.get("source_manifest_digest") or "")
    fresh = bool(expected and expected == actual)
    row = {
        "ok": fresh, "status": "inspection_source_fresh" if fresh else "inspection_source_stale",
        "expected_manifest_digest": expected, "current_manifest_digest": actual, "stale_source": not fresh,
        "read_only": True, "content_minimized": True, **DENIED_AUTHORITY,
    }
    row["freshness_digest"] = _digest(row)
    return row


def inspect_evidence_based_project_inspection_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    hashes = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in REQUIRED_SURFACES if (root / rel).is_file()}
    checks = {
        "all_required_surfaces_present": len(hashes) == len(REQUIRED_SURFACES),
        "v1254_containment_reused": (root / "conscious_agent/isolated_coding_execution_foundations.py").is_file(),
        "persistent_session_surface_present": (root / "conscious_agent/persistent_development_sessions.py").is_file(),
        "diagnostic_evidence_surface_present": (root / "conscious_agent/diagnostic_repair_reasoning.py").is_file(),
        "inspection_is_read_only": True,
    }
    row = {
        "ok": all(checks.values()), "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "status": "evidence_based_project_inspection_health_ready", "checks": checks,
        "source_sha256": hashes, "required_source_count": len(REQUIRED_SURFACES), "present_source_count": len(hashes),
        "read_only": True, "content_minimized": True, "native_windows_validation": "desktop_review_required",
        **DENIED_AUTHORITY,
    }
    row["health_digest"] = _digest(row)
    return row


def build_evidence_based_project_inspection_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_evidence_based_project_inspection_health(source_root=source_root)
    row = {
        "ok": bool(health.get("ok")), "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "status": "evidence_based_project_inspection_operator_handoff_ready" if health.get("ok") else "evidence_based_project_inspection_operator_handoff_blocked",
        "health_digest": health.get("health_digest", ""), "operator_review_required": True,
        "desktop_focus": [
            "native NTFS junction and reparse-point containment during full-project inspection",
            "case-insensitive path collisions and long source paths",
            "source changes while inspection is in progress and freshness recheck",
            "large-project budget and deterministic evidence ordering",
            "explicit runtime-health and development-session evidence without private payload leakage",
            "contradictory external evidence retained as uncertainty rather than silently reconciled",
            "no automatic backlog proposal or self-modification from inspection findings",
        ],
        "content_minimized": True, "read_only": True, **DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "check_project_inspection_freshness", "inspect_evidence_based_project_inspection_health", "build_evidence_based_project_inspection_operator_handoff"]
