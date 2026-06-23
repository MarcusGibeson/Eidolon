from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

PACKAGE_INTEGRITY_VERSION = "350.0"

FORBIDDEN_RUNTIME_PARTS = (
    "/data/autonomy/",
    "/data/self_maintenance/",
    "/data/workspaces/",
    "/runtime/",
    "/.venv/",
    "/__pycache__/",
)

SOURCE_DATA_ALLOWLIST = (
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/projects.json",
    "data/workspaces/active_project.json",
    "data/workspaces/command_profiles/default_java.json",
    "data/workspaces/command_profiles/default_node.json",
    "data/workspaces/command_profiles/default_python.json",
    "data/workspaces/command_profiles/eidolon.json",
)

SOURCE_ONLY_POLICY = {
    "includes_source_modules": True,
    "excludes_runtime_data": True,
    "excludes_private_state": True,
    "excludes_generated_reports": True,
    "operator_review_required_for_release": True,
}

def normalize_entry(path: str | Path) -> str:
    return str(path).replace("\\", "/")

def _source_allowlisted(normalized: str) -> bool:
    stripped = normalized.strip("/")
    if stripped.startswith("Eidolon/"):
        stripped = stripped[len("Eidolon/"):]
    return stripped in SOURCE_DATA_ALLOWLIST


def forbidden_runtime_path_matches(entries: Iterable[str | Path]) -> list[str]:
    matches: list[str] = []
    for entry in entries:
        normalized = "/" + normalize_entry(entry).strip("/")
        if _source_allowlisted(normalized):
            continue
        if any(part in normalized for part in FORBIDDEN_RUNTIME_PARTS):
            matches.append(normalize_entry(entry))
    return matches

def source_only_entry_policy() -> dict[str, Any]:
    return {
        "version": PACKAGE_INTEGRITY_VERSION,
        "policy": dict(SOURCE_ONLY_POLICY),
        "forbidden_runtime_parts": list(FORBIDDEN_RUNTIME_PARTS),
        "source_data_allowlist": list(SOURCE_DATA_ALLOWLIST),
        "authorizes_package_creation": False,
        "publishes_release": False,
    }

def package_privacy_summary(entries: Iterable[str | Path] | None = None) -> dict[str, Any]:
    entry_list = [normalize_entry(item) for item in (entries or [])]
    forbidden = forbidden_runtime_path_matches(entry_list)
    return {
        "version": PACKAGE_INTEGRITY_VERSION,
        "entry_count": len(entry_list),
        "forbidden_count": len(forbidden),
        "forbidden_entries": forbidden,
        "ok": not forbidden,
        "source_only": not forbidden,
        "authorizes_packaging": False,
    }

# v305 source-only package integrity allows stable source metadata under data/workspaces while still rejecting private runtime workspace data outside SOURCE_DATA_ALLOWLIST.
