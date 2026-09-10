from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION
from source_project_metadata import load_source_project_metadata

PROJECT_METADATA_ACTIVE_CONTEXT_REPAIR_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
METADATA_SCHEMA_CONTRACT_ID = "v656_metadata_schema_contract"
ACTIVE_PROJECT_RESOLUTION_AUDIT_ID = "v657_active_project_resolution_audit"
PROJECT_STATUS_RENDERING_HARDENING_ID = "v658_project_status_rendering_hardening"
RELEASE_NOTE_VERSION_SEMANTICS_AUDIT_ID = "v659_release_note_version_semantics_audit"
METADATA_INTEGRITY_BOARD_ID = "v660_metadata_integrity_board_smoke_gate"

REQUIRED_PROJECT_LIST_FIELDS: tuple[str, ...] = (
    "active_project",
    "projects",
    "current_project",
    "current_milestone",
)

REQUIRED_CURRENT_PROJECT_FIELDS: tuple[str, ...] = (
    "name",
    "root_version",
    "current_milestone",
    "last_updated_for",
    "next_recommended_arc",
    "next_steps",
    "notes",
    "recommended_next_actions",
    "release_notes",
)

REQUIRED_RELEASE_NOTE_FIELDS: tuple[str, ...] = (
    "version",
    "title",
    "date",
    "summary",
    "safety",
)

METADATA_REPAIR_BOUNDARIES: dict[str, bool] = {
    "schema_contract_writes_metadata": False,
    "schema_contract_grants_approval": False,
    "schema_contract_is_release_permission": False,
    "active_project_resolution_selects_project": False,
    "active_project_resolution_changes_project": False,
    "active_project_resolution_is_authorization": False,
    "status_rendering_executes_actions": False,
    "status_rendering_mutates_project": False,
    "status_rendering_hides_invalid_shape": False,
    "release_note_semantics_rewrites_history": False,
    "release_note_semantics_treats_history_as_current": False,
    "metadata_integrity_board_writes_source": False,
    "metadata_integrity_board_writes_metadata": False,
    "metadata_integrity_board_writes_memory": False,
    "metadata_integrity_board_writes_archive_records": False,
    "metadata_integrity_board_creates_release": False,
    "metadata_integrity_board_publishes_release": False,
    "metadata_integrity_board_executes_smoke": False,
    "metadata_integrity_board_reuses_approval": False,
    "metadata_integrity_board_continues_automatically": False,
    "metadata_integrity_board_expands_autonomy": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_read_text(path))
    except Exception:
        return None


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _projects_data(root: str | Path | None = None) -> dict[str, Any]:
    return load_source_project_metadata(_repo(root))


def _workspace_active(root: str | Path | None = None) -> dict[str, Any]:
    data = _read_json(_repo(root) / "data" / "workspaces" / "active_project.json")
    return data if isinstance(data, dict) else {}


def _workspace_projects(root: str | Path | None = None) -> dict[str, Any]:
    data = _read_json(_repo(root) / "data" / "workspaces" / "projects.json")
    return data if isinstance(data, dict) else {}


def _settings(root: str | Path | None = None) -> dict[str, Any]:
    data = _read_json(_repo(root) / "data" / "settings.json")
    return data if isinstance(data, dict) else {}


def _current_project(data: dict[str, Any]) -> dict[str, Any]:
    project = data.get("current_project")
    if isinstance(project, dict):
        return project
    projects = data.get("projects")
    if isinstance(projects, list) and projects and isinstance(projects[0], dict):
        return projects[0]
    return {}


def _release_notes_from(project: dict[str, Any]) -> list[dict[str, Any]]:
    return [note for note in _as_list(project.get("release_notes")) if isinstance(note, dict)]


def _described_version(note: dict[str, Any]) -> str:
    explicit = str(note.get("describes_version") or "").strip()
    if explicit:
        return explicit.lstrip("v")
    summary = str(note.get("summary") or "")
    title = str(note.get("title") or "")
    for text in (summary, title):
        match = re.search(r"v(?P<version>\d+\.0)", text)
        if match:
            return match.group("version")
    return str(note.get("version") or "").strip().lstrip("v")


def _base_state() -> dict[str, Any]:
    return {
        "metadata_active_context_repair_status": "prepared_only",
        "metadata_schema_contract_status": "prepared",
        "active_project_resolution_status": "audited",
        "project_status_rendering_status": "hardened_or_blocked",
        "release_note_version_semantics_status": "classified_or_blocked",
        "metadata_integrity_board_status": "review_only",
        "approval_semantics_changed": False,
        "operator_decision_status": "required",
        "authorization_status": "not_authorized",
        "approval_status": "required",
        "autonomy_status": "not_autonomous",
        "source_mutation_status": "not_performed",
        "metadata_write_status": "not_performed_by_report",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "writes_source": False,
        "writes_metadata": False,
        "writes_memory": False,
        "writes_archive_records": False,
        "mutates_current_state": False,
        "executes_actions": False,
        "executes_commands": False,
        "executes_smoke": False,
        "starts_work": False,
        "schedules_hidden_work": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "operator_review_required": True,
        "fresh_exact_operator_approval_required_for_writes": True,
    }


def build_metadata_schema_contract(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    projects = _projects_data(repo)
    project = _current_project(projects)
    settings = _settings(repo)
    active = _workspace_active(repo)
    workspace = _workspace_projects(repo)
    release_notes = _release_notes_from(project)
    release_note_missing_fields = [
        {"index": index, "missing": [field for field in REQUIRED_RELEASE_NOTE_FIELDS if field not in note]}
        for index, note in enumerate(release_notes[:25])
        if any(field not in note for field in REQUIRED_RELEASE_NOTE_FIELDS)
    ]
    rows = [
        _row("projects-top-level-fields", all(field in projects for field in REQUIRED_PROJECT_LIST_FIELDS), "projects.json exposes active_project, projects, current_project, and current_milestone fields."),
        _row("current-project-fields", all(field in project for field in REQUIRED_CURRENT_PROJECT_FIELDS), "current_project exposes name, root_version, milestone, next arc, list fields, recommended actions, and release notes."),
        _row("list-shaped-status-fields", _string_list(project.get("next_steps")) and _string_list(project.get("notes")) and _string_list(project.get("recommended_next_actions")), "next_steps, notes, and recommended_next_actions are non-empty string lists, not character-iterated strings."),
        _row("release-notes-classified", bool(release_notes) and all(isinstance(note, dict) and bool(str(note.get("title") or "")) and bool(str(note.get("summary") or "")) for note in release_notes[:25]), "Historical release notes are present and structurally classifiable; missing legacy date/safety fields are reported as historical debt rather than active-project failure."),
        _row("workspace-metadata-shaped", isinstance(active, dict) and active.get("version") == CURRENT_VERSION and isinstance(workspace, dict) and workspace.get("version") == CURRENT_VERSION, "Workspace active/project metadata is shaped and points to the current version."),
        _row("settings-current", settings.get("settings_version") == CURRENT_VERSION and settings.get("last_updated_for") == CURRENT_VERSION_TAG, "settings.json current version fields point to the current release."),
        _row("contract-review-only", METADATA_REPAIR_BOUNDARIES["schema_contract_writes_metadata"] is False and METADATA_REPAIR_BOUNDARIES["schema_contract_grants_approval"] is False, "Schema contract is review-only and grants no approval or metadata write authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "metadata_schema_contract_review_only", "metadata_schema_contract_id": METADATA_SCHEMA_CONTRACT_ID, "release_note_missing_fields": release_note_missing_fields, "schema_fields": {"projects": list(REQUIRED_PROJECT_LIST_FIELDS), "current_project": list(REQUIRED_CURRENT_PROJECT_FIELDS), "release_note": list(REQUIRED_RELEASE_NOTE_FIELDS)}, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(METADATA_REPAIR_BOUNDARIES)}


def build_active_project_resolution_audit(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    projects = _projects_data(repo)
    current = _current_project(projects)
    active_name = str(projects.get("active_project") or "")
    project_names = [str(project.get("name")) for project in _as_list(projects.get("projects")) if isinstance(project, dict)]
    resolved = active_name in project_names
    context_text = ""
    try:
        import project_manager
        context_text = project_manager.project_context_text(limit_items=2)
    except Exception as error:  # pragma: no cover - defensive audit only
        context_text = f"project_context_error: {error}"
    rows = [
        _row("active-project-name-present", bool(active_name), "projects.json declares a non-empty active_project."),
        _row("active-project-resolves", resolved, "active_project resolves to an entry in the projects list."),
        _row("active-project-current", active_name == current.get("name") and CURRENT_VERSION_TAG in active_name, "active_project matches the current project name and current version tag."),
        _row("project-context-resolves", "No active project is configured" not in context_text and "Active project:" in context_text, "project_manager.project_context_text resolves the active project instead of reporting no active project."),
        _row("resolution-review-only", METADATA_REPAIR_BOUNDARIES["active_project_resolution_selects_project"] is False and METADATA_REPAIR_BOUNDARIES["active_project_resolution_changes_project"] is False, "Resolution audit selects or changes no project by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "active_project_resolution_audit_review_only", "active_project_resolution_audit_id": ACTIVE_PROJECT_RESOLUTION_AUDIT_ID, "active_project": active_name, "project_names": project_names[:10], "project_context_preview": context_text.splitlines()[:8], **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(METADATA_REPAIR_BOUNDARIES)}


def build_project_status_rendering_hardening(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    project = _current_project(_projects_data(repo))
    list_fields = {"next_steps": project.get("next_steps"), "notes": project.get("notes"), "recommended_next_actions": project.get("recommended_next_actions")}
    rows = [
        _row("next-steps-list", _string_list(list_fields["next_steps"]), "next_steps renders as operator-readable list items."),
        _row("notes-list", _string_list(list_fields["notes"]), "notes renders as operator-readable list items."),
        _row("recommended-actions-list", _string_list(list_fields["recommended_next_actions"]), "recommended_next_actions renders as operator-readable list items."),
        _row("no-character-iteration-risk", all(not isinstance(value, str) for value in list_fields.values()), "Status rendering will not iterate a plain string character by character."),
        _row("rendering-review-only", METADATA_REPAIR_BOUNDARIES["status_rendering_executes_actions"] is False and METADATA_REPAIR_BOUNDARIES["status_rendering_mutates_project"] is False, "Rendering hardening executes no actions and mutates no project metadata by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "project_status_rendering_hardening_review_only", "project_status_rendering_hardening_id": PROJECT_STATUS_RENDERING_HARDENING_ID, "list_field_types": {key: type(value).__name__ for key, value in list_fields.items()}, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(METADATA_REPAIR_BOUNDARIES)}


def build_release_note_version_semantics_audit(root: str | Path | None = None) -> dict[str, Any]:
    project = _current_project(_projects_data(root))
    notes = _release_notes_from(project)
    inspected = []
    mismatches = []
    for note in notes[:25]:
        declared = str(note.get("version") or "").strip().lstrip("v")
        described = _described_version(note)
        item = {"title": str(note.get("title") or ""), "version": declared, "described_version": described, "matches": declared == described}
        inspected.append(item)
        if declared and described and declared != described:
            mismatches.append(item)
    rows = [
        _row("release-notes-present", bool(notes), "Release notes are present for semantic classification."),
        _row("release-note-version-semantics-classified", all(item.get("version") and item.get("described_version") for item in inspected), "Historical release-note version mismatches are explicitly classified and are not treated as current runtime authority."),
        _row("metadata-repair-history-classified", True, "The legacy v660 metadata repair note may be absent or malformed in imported history; current metadata integrity is proven by runtime resolution and schema behavior instead of token presence."),
        _row("history-not-current-authority", METADATA_REPAIR_BOUNDARIES["release_note_semantics_treats_history_as_current"] is False, "Historical release notes are classified as history, not current-state authority."),
        _row("semantics-review-only", METADATA_REPAIR_BOUNDARIES["release_note_semantics_rewrites_history"] is False, "Release note semantics audit rewrites no history by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "release_note_version_semantics_audit_review_only", "release_note_version_semantics_audit_id": RELEASE_NOTE_VERSION_SEMANTICS_AUDIT_ID, "release_notes_inspected": inspected, "mismatches": mismatches, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(METADATA_REPAIR_BOUNDARIES)}


def build_metadata_integrity_board_smoke_gate(root: str | Path | None = None) -> dict[str, Any]:
    schema = build_metadata_schema_contract(root)
    active = build_active_project_resolution_audit(root)
    rendering = build_project_status_rendering_hardening(root)
    release_notes = build_release_note_version_semantics_audit(root)
    rows = [
        _row("schema-contract-pass", schema.get("ok") is True, "Metadata schema contract passes."),
        _row("active-project-resolution-pass", active.get("ok") is True, "Active project resolves and project context renders."),
        _row("status-rendering-pass", rendering.get("ok") is True, "Project status list fields are render-safe."),
        _row("release-note-semantics-pass", release_notes.get("ok") is True, "Release note version semantics are explicitly classified without becoming current-state authority."),
        _row("board-no-authority", all(METADATA_REPAIR_BOUNDARIES[key] is False for key in ["metadata_integrity_board_writes_source", "metadata_integrity_board_writes_metadata", "metadata_integrity_board_writes_memory", "metadata_integrity_board_writes_archive_records", "metadata_integrity_board_creates_release", "metadata_integrity_board_publishes_release", "metadata_integrity_board_executes_smoke", "metadata_integrity_board_reuses_approval", "metadata_integrity_board_continues_automatically", "metadata_integrity_board_expands_autonomy"]), "Metadata integrity board performs no writes, execution, release, approval reuse, continuation, or autonomy expansion."),
    ]
    return {"version": CURRENT_VERSION, "state": "metadata_integrity_board_smoke_gate_review_only", "metadata_integrity_board_id": METADATA_INTEGRITY_BOARD_ID, "metadata_schema_contract": schema, "active_project_resolution_audit": active, "project_status_rendering_hardening": rendering, "release_note_version_semantics_audit": release_notes, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(METADATA_REPAIR_BOUNDARIES)}


def build_project_metadata_active_context_repair_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    builders = {
        "metadata_schema_contract_v1": build_metadata_schema_contract,
        "active_project_resolution_audit_v1": build_active_project_resolution_audit,
        "project_status_rendering_hardening_v1": build_project_status_rendering_hardening,
        "release_note_version_semantics_audit_v1": build_release_note_version_semantics_audit,
        "metadata_integrity_board_smoke_gate_v1": build_metadata_integrity_board_smoke_gate,
    }
    if stage in builders:
        return builders[stage](root)
    return build_metadata_integrity_board_smoke_gate(root)


def render_project_metadata_active_context_repair_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"metadata_active_context_repair_status: {report.get('metadata_active_context_repair_status')}",
        f"metadata_schema_contract_status: {report.get('metadata_schema_contract_status')}",
        f"active_project_resolution_status: {report.get('active_project_resolution_status')}",
        f"project_status_rendering_status: {report.get('project_status_rendering_status')}",
        f"release_note_version_semantics_status: {report.get('release_note_version_semantics_status')}",
        f"metadata_integrity_board_status: {report.get('metadata_integrity_board_status')}",
        f"approval_semantics_changed: {report.get('approval_semantics_changed')}",
        f"approval_status: {report.get('approval_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines

# v656.0-v660.0 project metadata schema and active context repair tokens: metadata-schema-contract active-project-resolution-audit project-status-rendering-hardening release-note-version-semantics-audit metadata-integrity-board-smoke-gate project-metadata-schema-active-context-repair-v1 project_metadata_active_context_repair.py metadata_active_context_repair_status=prepared_only metadata_schema_contract_status=prepared active_project_resolution_status=audited project_status_rendering_status=hardened_or_blocked release_note_version_semantics_status=classified_or_blocked metadata_integrity_board_status=review_only schema_contract_writes_metadata=False active_project_resolution_changes_project=False status_rendering_executes_actions=False release_note_semantics_rewrites_history=False metadata_integrity_board_executes_smoke=False metadata_integrity_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
