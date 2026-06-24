from __future__ import annotations

from pathlib import Path
from typing import Any

VERSION_STATE_VERSION = "500.0"

VERSION_MARKER_PATTERNS = {
    "conscious_agent/self_maintenance.py": "SELF_MAINTENANCE_VERSION",
    "conscious_agent/dashboard.py": "DASHBOARD_VERSION",
    "conscious_agent/api_server.py": "API_VERSION",
    "conscious_agent/release_packaging.py": "RELEASE_PACKAGING_VERSION",
    "conscious_agent/release_installation.py": "RELEASE_INSTALLATION_VERSION",
    "conscious_agent/workspace_orchestration.py": "WORKSPACE_ORCHESTRATION_VERSION",
    "conscious_agent/runtime_registry.py": "RUNTIME_REGISTRY_VERSION",
    "conscious_agent/governance_reports.py": "GOVERNANCE_REPORTS_VERSION",
    "conscious_agent/package_integrity.py": "PACKAGE_INTEGRITY_VERSION",
    "conscious_agent/version_state.py": "VERSION_STATE_VERSION",
    "conscious_agent/surface_parity.py": "SURFACE_PARITY_VERSION",
    "conscious_agent/verification_planning.py": "VERIFICATION_PLANNING_VERSION",
    "conscious_agent/identity_expression.py": "IDENTITY_EXPRESSION_VERSION",
    "conscious_agent/self_maintenance_refactor_registry.py": "SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION",
    "conscious_agent/minimal_live_change_replay.py": "MINIMAL_LIVE_CHANGE_REPLAY_VERSION",
}

def _extract_marker(text: str, marker: str) -> str | None:
    prefix = marker + ' = "'
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].split('"', 1)[0]
    return None

def version_marker_summary(root: Path, expected_version: str = VERSION_STATE_VERSION) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for rel, marker in VERSION_MARKER_PATTERNS.items():
        path = root / rel
        value = _extract_marker(path.read_text(encoding="utf-8", errors="ignore"), marker) if path.exists() else None
        rows.append({
            "path": rel,
            "marker": marker,
            "value": value,
            "expected": expected_version,
            "status": "pass" if value == expected_version else "blocked",
        })
    blocked = [row for row in rows if row["status"] != "pass"]
    return {
        "version": VERSION_STATE_VERSION,
        "expected_version": expected_version,
        "rows": rows,
        "blocked": blocked,
        "ok": not blocked,
        "authorizes_version_change": False,
    }

def release_marker_compatibility_adapter(root: Path, expected_version: str = VERSION_STATE_VERSION) -> dict[str, Any]:
    summary = version_marker_summary(root, expected_version)
    return {
        "version": VERSION_STATE_VERSION,
        "ok": summary["ok"],
        "marker_count": len(summary["rows"]),
        "blocked_count": len(summary["blocked"]),
        "rows": summary["rows"],
        "changes_files": False,
    }
