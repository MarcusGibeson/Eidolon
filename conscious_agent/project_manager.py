from __future__ import annotations

from datetime import datetime
import secrets
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from memory import load_json, save_json, store_memory
from source_project_metadata import load_source_project_metadata
try:
    from json_storage import migrate_json_file_encoding
    from project_identity import normalize_project_identity, project_source_binding as _project_source_binding, resolve_project_selection
except ImportError:
    from json_storage import migrate_json_file_encoding
    from project_identity import normalize_project_identity, project_source_binding as _project_source_binding, resolve_project_selection


PROJECTS_FILE = DATA_DIR / "projects.json"


DEFAULT_PROJECTS = {
    "active_project": "Eidolon",
    "active_project_id": "eidolon",
    "projects": [
        {
            "id": "eidolon",
            "name": "Eidolon",
            "root": ".",
            "description": "A private local conversational agent with supervised development and operator-controlled authority.",
            "language": "Python",
            "status": "active",
            "goals": [
                "Build reliable daily-companion behavior",
                "Preserve private local memory and project continuity",
                "Expand supervised development without autonomous authority",
            ],
            "known_issues": [
                "Native provider behavior depends on the configured local service",
                "Native Windows certification is environment-dependent",
            ],
            "next_steps": [],
            "capabilities": [],
            "notes": ["Powerful actions remain permission-gated and logged."],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_worked_on": datetime.now().isoformat(timespec="seconds"),
        }
    ],
}


def _project_identity(project: dict[str, Any]) -> tuple[str, str]:
    return (
        str(project.get("id") or "").strip().lower(),
        str(project.get("name") or "").strip().lower(),
    )


def _normalize_projects_data(data: dict[str, Any]) -> dict[str, Any]:
    raw_projects = [dict(item) for item in data.get("projects", []) if isinstance(item, dict)]
    if not raw_projects:
        raw_projects = [dict(item) for item in DEFAULT_PROJECTS["projects"]]
    inherited = {
        key: data.get(key)
        for key in (
            "installed_version", "working_version", "candidate_version", "version", "root_version",
            "last_updated_for", "current_milestone", "next_recommended_arc", "capabilities", "next_steps",
        )
        if data.get(key) not in (None, "", [])
    }
    projects = [normalize_project_identity(item, base_root=ROOT_DIR) for item in raw_projects]
    normalized = dict(data)

    active_id = str(data.get("active_project_id") or "").strip()
    active_name = str(data.get("active_project") or "").strip()
    selection = resolve_project_selection(projects, active_id or active_name)
    active = selection.project
    if active is None and len(projects) == 1:
        active = projects[0]
    if active is None:
        active = next((row for row in projects if row.get("id") == "eidolon"), projects[0])
    active_id_resolved = str(active.get("id") or "project")
    projects = [
        normalize_project_identity(row, base_root=ROOT_DIR, inherited=inherited)
        if str(row.get("id") or "") == active_id_resolved else row
        for row in projects
    ]
    active = next(row for row in projects if str(row.get("id") or "") == active_id_resolved)
    normalized["projects"] = projects
    normalized["active_project"] = str(active.get("name") or "Unknown Project")
    normalized["active_project_id"] = active_id_resolved
    normalized["identity_contract"] = "project-identity-v1092"
    normalized["runtime_projects_packaged"] = False
    return normalized


def _resolve_active_project(data: dict[str, Any]) -> dict[str, Any] | None:
    normalized = _normalize_projects_data(data) if data.get("identity_contract") != "project-identity-v1092" else data
    projects = [item for item in normalized.get("projects", []) if isinstance(item, dict)]
    active_id = str(normalized.get("active_project_id") or "").strip()
    selection = resolve_project_selection(projects, active_id)
    if selection.ok:
        return selection.project
    active_name = str(normalized.get("active_project") or "").strip()
    selection = resolve_project_selection(projects, active_name)
    if selection.ok:
        return selection.project
    return projects[0] if len(projects) == 1 else None


def load_projects_data() -> dict[str, Any]:
    if PROJECTS_FILE.is_file():
        data = load_json(PROJECTS_FILE, DEFAULT_PROJECTS)
    else:
        data = load_source_project_metadata(ROOT_DIR)
        if not data.get("projects"):
            data = DEFAULT_PROJECTS.copy()
    if not isinstance(data, dict):
        data = DEFAULT_PROJECTS.copy()
    return _normalize_projects_data(data)


def migrate_projects_metadata_encoding(*, operator_confirmed: bool = False) -> dict[str, Any]:
    """Explicitly normalize mutable projects.json from UTF-8 BOM to UTF-8."""
    return migrate_json_file_encoding(
        PROJECTS_FILE,
        operator_confirmed=operator_confirmed,
        expected_type=dict,
        create_backup=True,
    )


def save_projects_data(data: dict[str, Any]) -> None:
    save_json(PROJECTS_FILE, _normalize_projects_data(data))


def list_projects() -> list[dict[str, Any]]:
    return [dict(row) for row in load_projects_data().get("projects", []) if isinstance(row, dict)]


def resolve_project_selector(selector: str) -> dict[str, Any]:
    return resolve_project_selection(list_projects(), selector).as_dict()


def get_project(name_or_id: str) -> dict[str, Any] | None:
    return resolve_project_selection(list_projects(), name_or_id).project


def get_active_project() -> dict[str, Any] | None:
    return _resolve_active_project(load_projects_data())


def active_project_identity() -> dict[str, Any]:
    project = get_active_project()
    if not project:
        return {"ok": False, "status": "no_active_project", "project": None}
    binding = _project_source_binding(project)
    return {
        "ok": True,
        "status": "active",
        "project": dict(project),
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "source_root": binding.get("source_root"),
        "source_root_status": binding.get("status"),
        "source_identity_matches": binding.get("source_identity_matches"),
        "capability_state": binding.get("capability_state"),
        "identity_contract": "project-identity-v1092",
    }


def project_source_binding(selector: str = "") -> dict[str, Any]:
    project = get_project(selector) if str(selector or "").strip() else get_active_project()
    return _project_source_binding(project)


def preview_active_project_selection(selector: str) -> dict[str, Any]:
    resolved = resolve_project_selection(list_projects(), selector)
    report = resolved.as_dict()
    report.update({
        "changed": False,
        "operator_confirmation_required": resolved.ok,
        "runtime_registry_rewritten": False,
        "conversation_binding": "project-scoped",
    })
    if resolved.status == "ambiguous":
        report["message"] = "Project name is ambiguous. Select one stable project ID."
    elif resolved.status == "not_found":
        report["message"] = "Project was not found. No active-project state changed."
    elif resolved.ok:
        report["message"] = "Project selection is valid and awaits explicit confirmation."
    else:
        report["message"] = "A project ID or unambiguous project name is required."
    return report


def activate_project(
    selector: str,
    *,
    operator_confirmed: bool = False,
    expected_switch_revision: int | None = None,
    switch_key: str = "",
    switch_source_tab_id: str = "",
    switch_lease_token: str = "",
    coordination_revision: int | None = None,
) -> dict[str, Any]:
    data = load_projects_data()
    selection = resolve_project_selection(data.get("projects", []), selector)
    report = selection.as_dict()
    previous_project_id = str(data.get("active_project_id") or "eidolon")
    report.update({
        "changed": False,
        "operator_confirmed": bool(operator_confirmed),
        "runtime_registry_rewritten": False,
        "previous_project_id": previous_project_id,
    })
    if not selection.ok:
        report["message"] = (
            "Project name is ambiguous; use the stable project ID."
            if selection.status == "ambiguous"
            else "Project was not found; active-project state was not changed."
        )
        return report
    project = selection.project or {}
    project_id = str(project.get("id") or "")
    report["project_id"] = project_id
    report["project_name"] = project.get("name")
    report["source_binding"] = _project_source_binding(project)
    if not operator_confirmed:
        report["ok"] = False
        report["status"] = "confirmation_required"
        report["operator_confirmation_required"] = True
        report["message"] = "Explicit operator confirmation is required before changing the runtime project registry."
        return report

    from project_switching_continuity import (
        capture_project_continuity,
        claim_project_switch,
        complete_project_switch,
    )

    effective_switch_key = str(switch_key or "").strip() or f"project-switch-{secrets.token_hex(16)}"
    coordination_claim = None
    if str(switch_source_tab_id or "").strip():
        from conversation_tab_coordination import claim_dashboard_tab_mutation
        coordination_claim = claim_dashboard_tab_mutation(
            tab_id=str(switch_source_tab_id).strip(),
            lease_token=str(switch_lease_token or "").strip(),
            mutation_key=effective_switch_key,
            mutation_kind="project.switch",
            project_id=previous_project_id,
            expected_revision=coordination_revision,
            advance_revision=True,
        )
        report["coordination"] = coordination_claim.get("coordination") or {}
        if not coordination_claim.get("ok"):
            report.update({
                "ok": False,
                "status": str(coordination_claim.get("status") or "coordination_rejected"),
                "message": str(coordination_claim.get("error") or "Project switch coordination was rejected."),
                "operator_confirmation_required": False,
            })
            return report
        if coordination_claim.get("duplicate_mutation"):
            actual = str(load_projects_data().get("active_project_id") or "")
            completed = actual == project_id
            report.update({
                "ok": completed,
                "status": "already_active" if completed else "switch_in_progress",
                "changed": False,
                "runtime_registry_rewritten": False,
                "operator_confirmation_required": False,
                "message": "This exact coordinated project switch was already handled." if completed else "This exact coordinated project switch is still pending.",
            })
            return report

    capture_project_continuity(previous_project_id)
    claim = claim_project_switch(
        previous_project_id,
        project_id,
        expected_revision=expected_switch_revision,
        switch_key=effective_switch_key,
        source_tab_id=switch_source_tab_id,
    )
    report["switch_receipt"] = claim
    if not claim.get("ok"):
        if coordination_claim is not None:
            from conversation_tab_coordination import complete_dashboard_tab_mutation
            complete_dashboard_tab_mutation(effective_switch_key, success=False)
        report.update({
            "ok": False,
            "status": str(claim.get("status") or "switch_rejected"),
            "message": str(claim.get("error") or "Project switch was rejected."),
            "operator_confirmation_required": False,
        })
        return report
    if claim.get("duplicate_switch"):
        actual = str(load_projects_data().get("active_project_id") or "")
        completed = actual == project_id and str(claim.get("status") or "") == "completed"
        report.update({
            "ok": completed,
            "status": "already_active" if completed else "switch_in_progress",
            "changed": False,
            "runtime_registry_rewritten": False,
            "operator_confirmation_required": False,
            "message": "This exact confirmed project switch was already applied." if completed else "This exact project switch is already pending.",
        })
        return report

    try:
        data["active_project"] = project["name"]
        data["active_project_id"] = project_id
        for row in data.get("projects", []):
            if str(row.get("id") or "") == project_id:
                row["last_worked_on"] = datetime.now().isoformat(timespec="seconds")
                break
        save_projects_data(data)
        store_memory({
            "type": "project_event",
            "content": f"Active project changed to {project['name']}.",
            "source": "project_manager",
            "project": project["name"],
            "project_id": project_id,
        })
    except Exception:
        complete_project_switch(str(claim.get("switch_key") or ""), success=False, actual_project_id=previous_project_id)
        if coordination_claim is not None:
            from conversation_tab_coordination import complete_dashboard_tab_mutation
            complete_dashboard_tab_mutation(effective_switch_key, success=False)
        raise

    capture_project_continuity(project_id)
    completed = complete_project_switch(str(claim.get("switch_key") or ""), success=True, actual_project_id=project_id)
    coordination_state = None
    if coordination_claim is not None:
        from conversation_tab_coordination import complete_dashboard_tab_mutation, coordination_snapshot
        complete_dashboard_tab_mutation(
            effective_switch_key,
            success=True,
            selected_project_id=project_id,
            result={"project_id": project_id, "previous_project_id": previous_project_id, "target_project_id": project_id, "status": "changed"},
        )
        coordination_state = coordination_snapshot(tab_id=str(switch_source_tab_id).strip())
    report.update({
        "ok": True,
        "status": "changed" if previous_project_id != project_id else "already_active",
        "changed": previous_project_id != project_id,
        "runtime_registry_rewritten": True,
        "operator_confirmation_required": False,
        "message": f"Active project set to {project['name']} ({project_id}).",
        "switch_receipt": completed,
        "conversation_binding": "project-scoped",
        "provider_contacted": False,
        "coordination": coordination_state or report.get("coordination") or {},
    })
    return report


def set_active_project(name: str, *, operator_confirmed: bool = False) -> bool:
    """Compatibility wrapper. Persistence now requires explicit confirmation."""
    return bool(activate_project(name, operator_confirmed=operator_confirmed).get("ok"))


def add_project(
    name: str,
    path: str = "",
    description: str = "",
    language: str = "Unknown",
) -> dict[str, Any]:
    data = load_projects_data()
    existing = get_project(name)
    if existing:
        return existing
    project = normalize_project_identity({
        "name": name,
        "root": path or ".",
        "description": description,
        "language": language,
        "status": "active",
        "goals": [],
        "known_issues": [],
        "next_steps": [],
        "capabilities": [],
        "notes": [],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "last_worked_on": datetime.now().isoformat(timespec="seconds"),
    }, base_root=ROOT_DIR)
    data["projects"].append(project)
    data["active_project"] = project["name"]
    data["active_project_id"] = project["id"]
    save_projects_data(data)
    store_memory({
        "type": "project_event",
        "content": f"Project added and set active: {name}.",
        "source": "project_manager",
        "project": name,
        "project_id": project["id"],
    })
    return project


def add_project_item(project_name: str, item_type: str, content: str) -> bool:
    if item_type not in {"goals", "known_issues", "next_steps", "notes"}:
        return False
    data = load_projects_data()
    selection = resolve_project_selection(data.get("projects", []), project_name)
    if not selection.ok:
        return False
    project_id = str((selection.project or {}).get("id") or "")
    for project in data.get("projects", []):
        if str(project.get("id") or "") == project_id:
            project.setdefault(item_type, [])
            project[item_type].append(content)
            project["last_worked_on"] = datetime.now().isoformat(timespec="seconds")
            save_projects_data(data)
            store_memory({
                "type": "project_event",
                "content": f"Added {item_type[:-1].replace('_', ' ')} to {project['name']}: {content}",
                "source": "project_manager",
                "project": project["name"],
                "project_id": project["id"],
            })
            return True
    return False


def project_context_text(limit_items: int = 5, *, include_version_roles: bool = True) -> str:
    project = get_active_project()
    if not project:
        return "No active project is configured."

    def lines(label: str, values: list[str]) -> str:
        if not values:
            return f"{label}: none"
        clipped = values[:limit_items]
        joined = "\n".join(f"- {value}" for value in clipped)
        return f"{label}:\n{joined}"

    binding = _project_source_binding(project)
    try:
        from version_roles import project_version_roles
    except ImportError:
        from version_roles import project_version_roles
    roles = project_version_roles(project)
    versions = [
        f"Installed version: {roles.get('installed_version') or 'unknown'}",
        f"Working source version: {roles.get('working_source_version') or 'unknown'}",
        f"Candidate version: {roles.get('candidate_version') or 'none'}",
    ]
    version_lines = versions if include_version_roles else []
    return "\n".join([
        f"Active project: {project.get('name', 'Unknown')}",
        f"Project ID: {project.get('id', '')}",
        f"Source root: {binding.get('source_root', project.get('source_root', project.get('path', '')))}",
        f"Source root status: {binding.get('status', 'unknown')}",
        f"Source identity matches: {str(bool(binding.get('source_identity_matches'))).lower()}",
        *version_lines,
        f"Current milestone: {project.get('current_milestone', '')}",
        f"Next recommended arc: {project.get('next_recommended_arc', '')}",
        f"Language: {project.get('language', 'Unknown')}",
        f"Description: {project.get('description', '')}",
        lines("Capabilities", project.get("capabilities", [])),
        lines("Goals", project.get("goals", [])),
        lines("Known issues", project.get("known_issues", [])),
        lines("Next steps", project.get("next_steps", [])),
        lines("Notes", project.get("notes", [])),
    ])


def print_project_status() -> None:
    data = load_projects_data()
    active_id = str(data.get("active_project_id") or "")
    active_name = str(data.get("active_project") or "None")
    print(f"Active project: {active_name} ({active_id})")
    print("Projects:")
    for project in data.get("projects", []):
        marker = "*" if str(project.get("id") or "") == active_id else "-"
        print(f"{marker} {project.get('name', 'Unknown')} [{project.get('language', 'Unknown')}] {project.get('status', '')}")
        print(f"  ID: {project.get('id', '')}")
        print(f"  Source root: {project.get('source_root', project.get('path', ''))}")
        print(f"  Source status: {_project_source_binding(project).get('status', 'unknown')}")
        if project.get("description"):
            print(f"  Description: {project.get('description')}")
        if project.get("next_steps"):
            print("  Next steps:")
            for step in project.get("next_steps", [])[:5]:
                print(f"    - {step}")


def preview_project_source_root_update(selector: str, candidate_root: str) -> dict[str, Any]:
    """Preview an exact source-root correction without mutating runtime registries."""
    from project_root_recovery import preview_project_root_correction
    return preview_project_root_correction(selector, candidate_root)


def confirm_project_source_root_update(
    selector: str,
    candidate_root: str,
    *,
    preview_token: str,
    operator_confirmed: bool = False,
) -> dict[str, Any]:
    """Apply one preview-bound source-root correction after explicit confirmation."""
    from project_root_recovery import confirm_project_root_correction
    return confirm_project_root_correction(
        selector,
        candidate_root,
        preview_token=preview_token,
        operator_confirmed=operator_confirmed,
    )


def restore_active_project_continuity() -> dict[str, Any]:
    """Revalidate and restore content-free project state after restart."""
    from project_recovery_state import restore_project_recovery_state
    return restore_project_recovery_state()


def active_project_recovery_state(*, tab_id: str = "", expected_switch_revision: int | None = None) -> dict[str, Any]:
    """Return one content-free read-only project recovery state."""
    from project_recovery_state import build_project_recovery_state
    return build_project_recovery_state(tab_id=tab_id, expected_switch_revision=expected_switch_revision)
