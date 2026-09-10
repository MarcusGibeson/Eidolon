from __future__ import annotations

from pathlib import Path
from typing import Any

from release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, RUNTIME_VERSION
try:
    from json_storage import load_json_file
    from project_identity import normalize_project_identity, stable_project_name
except ImportError:
    from json_storage import load_json_file
    from project_identity import normalize_project_identity, stable_project_name

SOURCE_PROJECT_METADATA_VERSION = RUNTIME_VERSION
DEFAULT_EIDOLON_CAPABILITIES: tuple[str, ...] = (
    "conversation_sessions_and_streaming",
    "provider_neutral_local_generation_and_embeddings",
    "persistent_memory_with_correction_and_retraction",
    "project_inspection_and_source_indexing",
    "supervised_test_patch_and_release_workflows",
    "operator_controlled_approval_rollback_and_promotion",
    "source_only_privacy_verification",
)


def _read_json(path: Path) -> dict[str, Any]:
    return load_json_file(path, {}, expected_type=dict)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_source_project_record(
    project: dict[str, Any],
    *,
    version: str,
    root_version: str,
    last_updated_for: str,
    current_milestone: str,
    next_arc: str,
) -> dict[str, Any]:
    current = normalize_project_identity(
        project,
        base_root=Path(__file__).resolve().parents[1],
        inherited={
            "working_version": version,
            "version": version,
            "root_version": root_version,
            "last_updated_for": last_updated_for,
            "current_milestone": current_milestone,
            "next_recommended_arc": next_arc,
        },
    )
    capabilities = _string_list(current.get("capabilities"))
    if not capabilities and str(current.get("id") or "").lower() == "eidolon":
        capabilities = list(DEFAULT_EIDOLON_CAPABILITIES)
    current["capabilities"] = capabilities
    current["next_steps"] = _string_list(current.get("next_steps"))
    current["recommended_next_actions"] = _string_list(current.get("recommended_next_actions"))
    current["active_project"] = current["name"]
    return current


def load_source_project_metadata(root: str | Path) -> dict[str, Any]:
    """Build an accurate source-safe project view from packaged metadata.

    ``data/projects.json`` remains mutable operator runtime state and is never
    consulted. Project identity is stable across releases; milestone and next
    steps are represented as separate fields instead of replacing the name.
    """
    project_root = Path(root)
    active = _read_json(project_root / "data" / "workspaces" / "active_project.json")
    registry = _read_json(project_root / "data" / "workspaces" / "projects.json")
    records = [item for item in registry.get("projects", []) if isinstance(item, dict)]
    active_id = str(active.get("active_project_id") or registry.get("active_project_id") or "").strip()
    if not records:
        active_id = active_id or "eidolon"
        registry = {
            "active_project_id": active_id,
            "version": RUNTIME_VERSION,
            "root_version": RUNTIME_VERSION,
            "last_updated_for": f"v{RUNTIME_VERSION}",
            "current_milestone": RUNTIME_MILESTONE,
            "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        }
        records = [{
            "id": active_id,
            "name": "Eidolon",
            "description": "Local artificial-mind and daily-companion source project.",
            "language": "Python",
            "framework_type": "local_cli_dashboard_api",
            "root": ".",
            "source_root": ".",
            "safe_to_modify": True,
        }]
    current = next((item for item in records if str(item.get("id") or "") == active_id), None)
    if current is None and records:
        current = records[0]
        active_id = str(current.get("id") or active_id)

    version = str(registry.get("version") or (current or {}).get("version") or "")
    root_version = str(registry.get("root_version") or (current or {}).get("root_version") or version)
    last_updated_for = str(registry.get("last_updated_for") or active.get("last_updated_for") or "")
    current_milestone = str(
        registry.get("current_milestone")
        or active.get("current_milestone")
        or (current or {}).get("current_milestone")
        or ""
    )
    next_arc = str(
        registry.get("next_recommended_arc")
        or active.get("next_recommended_arc")
        or (current or {}).get("next_recommended_arc")
        or ""
    )
    normalized_records = [
        normalize_source_project_record(
            record,
            version=version if str(record.get("id") or "") == active_id else str(record.get("version") or ""),
            root_version=root_version if str(record.get("id") or "") == active_id else str(record.get("root_version") or record.get("version") or ""),
            last_updated_for=last_updated_for if str(record.get("id") or "") == active_id else str(record.get("last_updated_for") or ""),
            current_milestone=current_milestone if str(record.get("id") or "") == active_id else str(record.get("current_milestone") or ""),
            next_arc=next_arc if str(record.get("id") or "") == active_id else str(record.get("next_recommended_arc") or ""),
        )
        for record in records
    ]
    current_project = next(
        (record for record in normalized_records if str(record.get("id") or "") == active_id),
        normalized_records[0] if normalized_records else {},
    )
    name = str(current_project.get("name") or "")

    return {
        "active_project": name,
        "active_project_id": active_id,
        "capabilities": list(current_project.get("capabilities") or []),
        "current_milestone": current_milestone,
        "current_project": current_project,
        "last_updated_for": last_updated_for,
        "next_recommended_arc": next_arc,
        "next_steps": list(current_project.get("next_steps") or []),
        "projects": normalized_records,
        "root_version": root_version,
        "version": version,
        "source": "data/workspaces/projects.json",
        "runtime_projects_packaged": False,
    }
