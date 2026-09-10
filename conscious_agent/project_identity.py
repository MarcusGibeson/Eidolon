from __future__ import annotations

"""Normalized, source-root-bound project identity.

This module is deliberately read-only.  It normalizes source-safe or runtime
project records, resolves selectors without guessing, and reports whether an
exact source root is usable.  Persistence remains an explicit operator action
owned by ``project_manager`` or the supervised workspace layer.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any, Iterable

try:
    from paths import ROOT_DIR
except ImportError:
    from paths import ROOT_DIR

PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_MILESTONE_NAME = re.compile(r"^v\d+(?:\.\d+)+\b", re.IGNORECASE)
_RUNTIME_VERSION_LINE = re.compile(r'^RUNTIME_VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _text(item)
        if token and token not in seen:
            seen.add(token)
            rows.append(token)
    return rows


def stable_project_id(value: Any, *, name: str = "") -> str:
    token = _text(value).lower().replace(" ", "-")
    token = re.sub(r"[^a-z0-9._-]+", "-", token).strip("-._")
    if not token:
        token = re.sub(r"[^a-z0-9._-]+", "-", _text(name).lower()).strip("-._")
    return token if PROJECT_ID_PATTERN.fullmatch(token) else "project"


def stable_project_name(project: dict[str, Any], milestone: str = "") -> str:
    name = _text(project.get("name") or project.get("display_name"))
    project_id = stable_project_id(project.get("id"), name=name)
    if project_id == "eidolon" and (not name or name == milestone or _MILESTONE_NAME.match(name)):
        return "Eidolon"
    if name and not (name == milestone and _MILESTONE_NAME.match(name)):
        return name
    if project_id == "eidolon":
        return "Eidolon"
    return project_id.replace("_", " ").replace("-", " ").title() or "Unknown Project"


def _root_reference(project: dict[str, Any]) -> str:
    return _text(project.get("source_root") or project.get("root") or project.get("path") or ".") or "."


def resolve_source_root(reference: str, *, base_root: str | Path = ROOT_DIR) -> Path:
    token = _text(reference) or "."
    if token in {".", "$ROOT_DIR", "{ROOT_DIR}", "ROOT_DIR"}:
        return Path(base_root).resolve()
    candidate = Path(os.path.expandvars(token)).expanduser()
    if not candidate.is_absolute():
        candidate = Path(base_root) / candidate
    return candidate.resolve(strict=False)


def source_root_state(reference: str, *, base_root: str | Path = ROOT_DIR) -> dict[str, Any]:
    path = resolve_source_root(reference, base_root=base_root)
    exists = path.exists()
    is_dir = path.is_dir() if exists else False
    accessible = bool(is_dir and os.access(path, os.R_OK | os.X_OK))
    status = "available" if accessible else "missing" if not exists else "not_directory" if not is_dir else "inaccessible"
    return {
        "source_root": str(path),
        "source_root_reference": _text(reference) or ".",
        "source_root_status": status,
        "source_root_exists": exists,
        "source_root_is_directory": is_dir,
        "source_root_accessible": accessible,
    }


def normalize_project_identity(
    project: dict[str, Any],
    *,
    base_root: str | Path = ROOT_DIR,
    inherited: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inherited = inherited or {}
    current = dict(project)
    milestone = _text(current.get("current_milestone") or inherited.get("current_milestone"))
    name = stable_project_name(current, milestone)
    project_id = stable_project_id(current.get("id"), name=name)
    root = source_root_state(_root_reference(current), base_root=base_root)
    installed = _text(current.get("installed_version") or inherited.get("installed_version"))
    working = _text(current.get("working_version") or current.get("version") or inherited.get("working_version") or inherited.get("version"))
    candidate = _text(current.get("candidate_version") or inherited.get("candidate_version"))
    root_version = _text(current.get("root_version") or inherited.get("root_version") or working)
    normalized = {
        **current,
        "id": project_id,
        "name": name,
        "display_name": name,
        **root,
        "path": root["source_root"],
        "root": root["source_root_reference"],
        "installed_version": installed,
        "working_version": working,
        "candidate_version": candidate,
        "version": working,
        "root_version": root_version,
        "current_milestone": milestone,
        "next_recommended_arc": _text(current.get("next_recommended_arc") or inherited.get("next_recommended_arc")),
        "last_updated_for": _text(current.get("last_updated_for") or inherited.get("last_updated_for")),
        "capabilities": _strings(current.get("capabilities") or inherited.get("capabilities")),
        "next_steps": _strings(current.get("next_steps") or inherited.get("next_steps")),
        "recommended_next_actions": _strings(current.get("recommended_next_actions") or inherited.get("recommended_next_actions")),
        "identity_contract": "project-identity-v1092",
    }
    return normalized


@dataclass(frozen=True)
class ProjectSelection:
    status: str
    selector: str
    matches: tuple[dict[str, Any], ...]

    @property
    def ok(self) -> bool:
        return self.status == "matched" and len(self.matches) == 1

    @property
    def project(self) -> dict[str, Any] | None:
        return dict(self.matches[0]) if self.ok else None

    def as_dict(self) -> dict[str, Any]:
        project = self.project
        return {
            "ok": self.ok,
            "status": self.status,
            "selector": self.selector,
            "project": project,
            "match_count": len(self.matches),
            "matches": [
                {"id": row.get("id"), "name": row.get("name"), "source_root": row.get("source_root")}
                for row in self.matches
            ],
            "ambiguous": self.status == "ambiguous",
            "not_found": self.status == "not_found",
        }


def resolve_project_selection(projects: Iterable[dict[str, Any]], selector: str) -> ProjectSelection:
    rows = [dict(row) for row in projects if isinstance(row, dict)]
    token = _text(selector).lower()
    if not token:
        return ProjectSelection("missing_selector", token, tuple())
    id_matches = tuple(row for row in rows if _text(row.get("id")).lower() == token)
    if len(id_matches) == 1:
        return ProjectSelection("matched", token, id_matches)
    if len(id_matches) > 1:
        return ProjectSelection("ambiguous", token, id_matches)
    name_matches = tuple(row for row in rows if _text(row.get("name")).lower() == token)
    if len(name_matches) == 1:
        return ProjectSelection("matched", token, name_matches)
    if len(name_matches) > 1:
        return ProjectSelection("ambiguous", token, name_matches)
    return ProjectSelection("not_found", token, tuple())


def project_source_binding(project: dict[str, Any] | None) -> dict[str, Any]:
    if not project:
        return {
            "ok": False, "status": "no_active_project", "project_id": "", "project_name": "",
            "source_root": "", "source_root_accessible": False,
            "message": "No active project is configured.",
        }
    normalized = normalize_project_identity(project, base_root=ROOT_DIR)
    root = Path(str(normalized.get("source_root") or ""))
    status = str(normalized.get("source_root_status") or "unknown")
    accessible = bool(normalized.get("source_root_accessible"))
    project_id = _text(normalized.get("id"))
    marker_paths = _strings(normalized.get("source_identity_markers"))
    if not marker_paths and project_id == "eidolon":
        marker_paths = ["conscious_agent/release_metadata.py", "README_NEXT_STEPS.md"]
    missing_markers = [marker for marker in marker_paths if accessible and not (root / marker).is_file()]
    observed_version = ""
    version_file_reference = _text(normalized.get("source_version_file"))
    if not version_file_reference and project_id == "eidolon":
        version_file_reference = "conscious_agent/release_metadata.py"
    version_pattern_text = _text(normalized.get("source_version_pattern"))
    try:
        version_pattern = re.compile(version_pattern_text, re.MULTILINE) if version_pattern_text else _RUNTIME_VERSION_LINE
    except re.error:
        version_pattern = _RUNTIME_VERSION_LINE
    if accessible and version_file_reference:
        metadata = root / version_file_reference
        try:
            match = version_pattern.search(metadata.read_text(encoding="utf-8-sig"))
            observed_version = match.group(1).strip() if match and match.groups() else ""
        except OSError:
            observed_version = ""
    expected_version = _text(normalized.get("working_version") or normalized.get("version"))
    version_mismatch = bool(observed_version and expected_version and observed_version != expected_version)
    identity_evidence_sufficient = bool(marker_paths or version_file_reference or project_id == "eidolon")
    identity_matches = accessible and not missing_markers and not version_mismatch
    if accessible and not identity_matches:
        status = "identity_mismatch"
    configured_safe_to_modify = bool(normalized.get("safe_to_modify", project_id == "eidolon"))
    safe_to_modify = bool(identity_matches and configured_safe_to_modify)
    capabilities = list(normalized.get("capabilities") or [])
    capability_state = {
        "ordinary_conversation": True,
        "project_context": True,
        "source_inspection": bool(identity_matches),
        "development": safe_to_modify,
        "verification": bool(identity_matches),
        "provider_generation": None,
    }
    messages = {
        "available": "The selected project source root is available and identity-bound.",
        "missing": "The selected project source root is missing. Update that project explicitly before development or verification.",
        "not_directory": "The selected project source root is not a directory.",
        "inaccessible": "The selected project source root is not accessible to this process.",
        "identity_mismatch": "The selected source root does not match the registered project identity or working version.",
    }
    return {
        "ok": bool(identity_matches),
        "status": status,
        "project_id": project_id,
        "project_name": _text(normalized.get("name")),
        "source_root": str(root),
        "source_root_reference": _text(normalized.get("source_root_reference") or normalized.get("root")),
        "source_root_accessible": accessible,
        "source_identity_matches": bool(identity_matches),
        "source_identity_markers": marker_paths,
        "missing_identity_markers": missing_markers,
        "expected_working_version": expected_version,
        "observed_working_version": observed_version,
        "source_version_file": version_file_reference,
        "version_mismatch": version_mismatch,
        "identity_evidence_sufficient": identity_evidence_sufficient,
        "capabilities": capabilities,
        "capability_state": capability_state,
        "safe_to_modify": safe_to_modify,
        "configured_safe_to_modify": configured_safe_to_modify,
        "message": messages.get(status, "The selected project source root status is unknown."),
        "provider_contacted": False,
        "runtime_registry_rewritten": False,
    }
