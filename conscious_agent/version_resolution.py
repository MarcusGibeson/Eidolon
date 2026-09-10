from __future__ import annotations

"""Content-free cross-surface resolution for explicit Eidolon version roles."""

import json
import re
from pathlib import Path
from typing import Any

try:
    from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION, WORKING_SOURCE_VERSION
    from version_marker_resolution import marker_matches_runtime_version
    from version_roles import build_version_role_contract, normalize_version
except ImportError:
    from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION, WORKING_SOURCE_VERSION
    from version_marker_resolution import marker_matches_runtime_version
    from version_roles import build_version_role_contract, normalize_version

_CURRENT_HEADING = re.compile(r"^#{1,6}\s+(?:Eidolon |Desktop Alpha )?v(\d+(?:\.\d+)+)\b", re.MULTILINE)
_HISTORY_HEADING = re.compile(r"^#{1,6}\s+v(\d+(?:\.\d+)+)\b", re.MULTILINE)


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _row(surface: str, role: str, observed: str, expected: str, *, source: str, current: bool = True) -> dict[str, Any]:
    observed_norm = normalize_version(observed)
    expected_norm = normalize_version(expected)
    ok = bool(observed_norm and (not current or observed_norm == expected_norm))
    return {
        "surface": surface,
        "role": role,
        "observed_version": observed_norm,
        "expected_version": expected_norm if current else "",
        "status": "pass" if ok else "drift",
        "ok": ok,
        "source": source,
        "current_surface": bool(current),
    }


def _optional_metadata_row(
    path: Path,
    surface: str,
    observed: str,
    expected: str,
    *,
    source: str,
    current: bool = True,
) -> dict[str, Any]:
    if path.is_file():
        return _row(surface, "working_source", observed, expected, source=source, current=current)
    return {
        "surface": surface,
        "role": "optional_source_metadata",
        "observed_version": "",
        "expected_version": normalize_version(expected) if current else "",
        "status": "not_packaged",
        "ok": True,
        "source": source,
        "current_surface": bool(current),
        "required": False,
    }


def _heading_version(path: Path, *, history: bool = False) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""
    match = (_HISTORY_HEADING if history else _CURRENT_HEADING).search(text)
    return match.group(1) if match else ""


def _registered(root: Path, suite_name: str) -> bool:
    try:
        text = (root / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8-sig")
    except OSError:
        return False
    return suite_name in text


def build_cross_surface_version_resolution(
    root_dir: str | Path | None = None,
    *,
    installed_version: str = "",
    candidate_version: str = "",
    packaged_archive_name: str = "",
) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1]).resolve()
    expected = WORKING_SOURCE_VERSION
    settings_path = root / "data" / "settings.json"
    active_path = root / "data" / "workspaces" / "active_project.json"
    projects_path = root / "data" / "workspaces" / "projects.json"
    settings = _json(settings_path)
    active = _json(active_path)
    projects = _json(projects_path)
    project_rows = [row for row in projects.get("projects", []) if isinstance(row, dict)]
    eidolon = next((row for row in project_rows if str(row.get("id") or "") == "eidolon"), {})

    dashboard_path = root / "conscious_agent" / "dashboard.py"
    api_path = root / "conscious_agent" / "api_server.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8-sig", errors="ignore") if dashboard_path.is_file() else ""
    api_text = api_path.read_text(encoding="utf-8-sig", errors="ignore") if api_path.is_file() else ""

    rows = [
        _row("release_metadata", "working_source", expected, expected, source="release_metadata.py:WORKING_SOURCE_VERSION"),
        _optional_metadata_row(settings_path, "settings.version", str(settings.get("version") or ""), expected, source="data/settings.json"),
        _optional_metadata_row(settings_path, "settings.root_version", str(settings.get("root_version") or ""), expected, source="data/settings.json"),
        _optional_metadata_row(active_path, "active_project.version", str(active.get("version") or ""), expected, source="data/workspaces/active_project.json"),
        _optional_metadata_row(active_path, "active_project.root_version", str(active.get("root_version") or ""), expected, source="data/workspaces/active_project.json"),
        _optional_metadata_row(projects_path, "projects.version", str(projects.get("version") or ""), expected, source="data/workspaces/projects.json"),
        _optional_metadata_row(projects_path, "projects.root_version", str(projects.get("root_version") or ""), expected, source="data/workspaces/projects.json"),
        _optional_metadata_row(projects_path, "eidolon_project.working_version", str(eidolon.get("working_version") or ""), expected, source="data/workspaces/projects.json#eidolon"),
        _optional_metadata_row(projects_path, "eidolon_project.root_version", str(eidolon.get("root_version") or ""), expected, source="data/workspaces/projects.json#eidolon"),
        _row("README", "working_source", _heading_version(root / "README.md"), expected, source="README.md"),
        _row("README_DESKTOP_ALPHA", "working_source", _heading_version(root / "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md"), expected, source="archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md"),
        _row("README_NEXT_STEPS", "working_source", normalize_version(str((root / "README_NEXT_STEPS.md").read_text(encoding="utf-8-sig", errors="ignore") if (root / "README_NEXT_STEPS.md").is_file() else "")), expected, source="README_NEXT_STEPS.md"),
        _row("release_history.latest", "historical", _heading_version(root / "README_RELEASE_HISTORY.md", history=True), expected, source="README_RELEASE_HISTORY.md"),
        {
            "surface": "dashboard.marker",
            "role": "working_source",
            "observed_version": expected if marker_matches_runtime_version(dashboard_text, "DASHBOARD_VERSION", expected) else "",
            "expected_version": expected,
            "status": "pass" if marker_matches_runtime_version(dashboard_text, "DASHBOARD_VERSION", expected) else "drift",
            "ok": marker_matches_runtime_version(dashboard_text, "DASHBOARD_VERSION", expected),
            "source": "conscious_agent/dashboard.py:DASHBOARD_VERSION",
            "current_surface": True,
        },
        {
            "surface": "api.marker",
            "role": "working_source",
            "observed_version": expected if marker_matches_runtime_version(api_text, "API_VERSION", expected) else "",
            "expected_version": expected,
            "status": "pass" if marker_matches_runtime_version(api_text, "API_VERSION", expected) else "drift",
            "ok": marker_matches_runtime_version(api_text, "API_VERSION", expected),
            "source": "conscious_agent/api_server.py:API_VERSION",
            "current_surface": True,
        },
        {
            "surface": "verification.v1095.2",
            "role": "verification_registration",
            "observed_version": expected if _registered(root, "v1095.2-version-drift-safe-reconciliation") else "",
            "expected_version": expected,
            "status": "pass" if _registered(root, "v1095.2-version-drift-safe-reconciliation") else "drift",
            "ok": _registered(root, "v1095.2-version-drift-safe-reconciliation"),
            "source": "tools/post_review_development_verify.py",
            "current_surface": True,
        },
        {
            "surface": "settings.settings_version",
            "role": "metadata_schema" if settings_path.is_file() else "optional_source_metadata",
            "observed_version": str(settings.get("settings_version") or ""),
            "expected_version": "",
            "status": "pass" if settings.get("settings_version") else "not_packaged",
            "ok": bool(settings.get("settings_version")) or not settings_path.is_file(),
            "source": "data/settings.json",
            "current_surface": False,
            "required": False,
        },
    ]
    drift = [row for row in rows if not row.get("ok")]
    roles = build_version_role_contract(
        root,
        installed_version=installed_version,
        candidate_version=candidate_version,
        packaged_archive_name=packaged_archive_name,
    )
    return {
        "ok": not drift and bool(roles.get("ok")),
        "status": "pass" if not drift and roles.get("ok") else "drift_detected",
        "version": RUNTIME_VERSION,
        "working_source_version": expected,
        "milestone": RUNTIME_MILESTONE,
        "version_roles": roles,
        "rows": rows,
        "drift": drift,
        "surface_count": len(rows),
        "drift_count": len(drift),
        "installed": False,
        "promoted": False,
        "certified": False,
        "deterministic_verification_is_certification": False,
        "provider_contacted": False,
        "runtime_mutation_performed": False,
        "content_free": True,
    }
