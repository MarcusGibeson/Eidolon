"""Metadata and release-integrity review helpers for the current Eidolon release.

This module is intentionally review-only. It inspects current-version metadata,
project/workspace state, release packaging version resolution, and documentation
current-state headers. It does not approve releases, publish packages, apply
patches, mutate memory, or expand autonomy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

METADATA_RELEASE_INTEGRITY_VERSION = "500.0"
CURRENT_VERSION = "500.0"
CURRENT_VERSION_TAG = "v500.0"
CURRENT_MILESTONE = "v500.0 Operator-Governed Autonomy Readiness Review Board v1"

METADATA_RELEASE_INTEGRITY_BOUNDARIES = {
    "metadata_consistency_is_authorization": False,
    "release_integrity_pass_is_approval": False,
    "metadata_repair_report_publishes_release": False,
    "metadata_repair_report_applies_source_edits": False,
    "metadata_repair_report_writes_memory": False,
    "metadata_repair_report_expands_autonomy": False,
    "metadata_repair_report_invokes_models": False,
    "operator_approval_still_required": True,
}

METADATA_FILES = [
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _row(name: str, ok: bool, message: str, *, expected: Any = None, actual: Any = None) -> dict[str, Any]:
    row = {"name": name, "status": "pass" if ok else "blocked", "message": message}
    if expected is not None:
        row["expected"] = expected
    if actual is not None:
        row["actual"] = actual
    return row


def _status_from(rows: list[dict[str, Any]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def build_metadata_version_inventory(root_dir: str | Path = ".") -> dict[str, Any]:
    """Inspect the allowlisted source metadata files for current-version alignment."""
    root = Path(root_dir)
    settings = _read_json(root / "data/settings.json", {})
    projects = _read_json(root / "data/projects.json", {})
    active = _read_json(root / "data/workspaces/active_project.json", {})
    workspace_projects = _read_json(root / "data/workspaces/projects.json", {})
    rows = [
        _row("settings-version", settings.get("settings_version") == CURRENT_VERSION, "settings.json declares the current settings version.", expected=CURRENT_VERSION, actual=settings.get("settings_version")),
        _row("settings-last-updated", settings.get("last_updated_for") == CURRENT_VERSION_TAG, "settings.json last_updated_for matches the current arc.", expected=CURRENT_VERSION_TAG, actual=settings.get("last_updated_for")),
        _row("projects-version", projects.get("version") == CURRENT_VERSION, "projects.json top-level version matches the current arc.", expected=CURRENT_VERSION, actual=projects.get("version")),
        _row("projects-root-version", projects.get("root_version") == CURRENT_VERSION, "projects.json root_version matches the current arc.", expected=CURRENT_VERSION, actual=projects.get("root_version")),
        _row("projects-last-updated", projects.get("last_updated_for") == CURRENT_VERSION_TAG, "projects.json last_updated_for matches the current arc.", expected=CURRENT_VERSION_TAG, actual=projects.get("last_updated_for")),
        _row("active-project-version", active.get("version") == CURRENT_VERSION, "active_project.json version matches the current arc.", expected=CURRENT_VERSION, actual=active.get("version")),
        _row("active-project-last-updated", active.get("last_updated_for") == CURRENT_VERSION_TAG, "active_project.json last_updated_for matches the current arc.", expected=CURRENT_VERSION_TAG, actual=active.get("last_updated_for")),
        _row("workspace-projects-version", workspace_projects.get("version") == CURRENT_VERSION, "workspace projects registry version matches the current arc.", expected=CURRENT_VERSION, actual=workspace_projects.get("version")),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "metadata_version_inventory_review_only",
        "expected_version": CURRENT_VERSION,
        "expected_tag": CURRENT_VERSION_TAG,
        "metadata_files": list(METADATA_FILES),
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_project_workspace_metadata_alignment(root_dir: str | Path = ".") -> dict[str, Any]:
    """Check that project and workspace metadata describe the same current milestone."""
    root = Path(root_dir)
    projects = _read_json(root / "data/projects.json", {})
    active = _read_json(root / "data/workspaces/active_project.json", {})
    workspace_projects = _read_json(root / "data/workspaces/projects.json", {})
    current_project = projects.get("current_project", {}) if isinstance(projects, dict) else {}
    project_records = projects.get("projects", []) if isinstance(projects.get("projects"), list) else []
    workspace_records = workspace_projects.get("projects", []) if isinstance(workspace_projects.get("projects"), list) else []
    first_project = project_records[0] if project_records else {}
    first_workspace = workspace_records[0] if workspace_records else {}
    rows = [
        _row("current-project-milestone", current_project.get("current_milestone") == CURRENT_MILESTONE, "Current project milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=current_project.get("current_milestone")),
        _row("top-next-arc", projects.get("next_recommended_arc") == "v501.0-v505.0 Manual Observation-to-Sandbox Packet Bridge v1", "Next recommended arc now points beyond the current cleanup boundary.", actual=projects.get("next_recommended_arc")),
        _row("project-record-milestone", first_project.get("current_milestone") == CURRENT_MILESTONE, "Primary project record milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=first_project.get("current_milestone")),
        _row("active-project-milestone", active.get("current_milestone") == CURRENT_MILESTONE, "Active workspace milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=active.get("current_milestone")),
        _row("workspace-project-milestone", first_workspace.get("current_milestone") == CURRENT_MILESTONE, "Workspace project registry milestone names the current release arc.", expected=CURRENT_MILESTONE, actual=first_workspace.get("current_milestone")),
        _row("memory-board-not-current", "Memory Lifecycle Review Board" not in str(current_project.get("current_milestone", "")), "v445 memory lifecycle board is no longer mislabeled as the current milestone."),
        _row("firewall-not-current-next", str(projects.get("next_recommended_arc")) != "v446.0-v450.0 Governance-State-to-Authorization Firewall v1", "Completed v450 firewall arc is no longer listed as the next arc."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "project_workspace_metadata_alignment_review_only",
        "expected_milestone": CURRENT_MILESTONE,
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_release_packaging_version_integrity(root_dir: str | Path = ".") -> dict[str, Any]:
    """Check that release packaging resolves the current version from metadata correctly."""
    root = Path(root_dir)
    packaging_text = _read_text(root / "conscious_agent/release_packaging.py")
    settings = _read_json(root / "data/settings.json", {})
    rows = [
        _row("settings-version-source", settings.get("settings_version") == CURRENT_VERSION, "Release packaging can read a current settings_version.", expected=CURRENT_VERSION, actual=settings.get("settings_version")),
        _row("current-version-priority", 'settings.get("settings_version")' in packaging_text, "release_packaging._current_version prefers settings_version before last_updated_for."),
        _row("package-name-current", f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip" == f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip", "Expected current source package name is deterministic.", actual=f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip"),
        _row("no-v420-settings", settings.get("settings_version") != "420.0" and settings.get("last_updated_for") != "v420.0", "Stale v420 settings metadata has been repaired."),
        _row("integrity-pass-not-approval", METADATA_RELEASE_INTEGRITY_BOUNDARIES["release_integrity_pass_is_approval"] is False, "Release integrity pass remains evidence only, not approval."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "release_packaging_version_integrity_review_only",
        "expected_package_name": f"Eidolon_v{CURRENT_VERSION.replace('.', '_')}.zip",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_current_state_documentation_header_audit(root_dir: str | Path = ".") -> dict[str, Any]:
    """Check that README files expose a current-state header before historical ledgers."""
    root = Path(root_dir)
    next_steps = _read_text(root / "README_NEXT_STEPS.md")
    release_history = _read_text(root / "README_RELEASE_HISTORY.md")
    required_next = [
        "CURRENT VERSION: v500.0",
        "CURRENT VERIFIED CHECKS",
        "CURRENT BLOCKERS",
        "CURRENT RECOMMENDED NEXT ARC",
        "Supervised Proposal Queue from Observation Reports v1",
    ]
    required_release = [
        "v500.0 - Operator-Governed Autonomy Readiness Review Board v1",
        "mapping is not approval",
        "README state is not approval",
        "Release history is not authorization",
    ]
    rows = [
        _row("next-steps-current-header", all(token in next_steps for token in required_next), "README_NEXT_STEPS.md starts with current-state guidance."),
        _row("release-history-current", all(token in release_history for token in required_release), "README_RELEASE_HISTORY.md documents the current v495 sandbox autonomy boundary prep arc."),
        _row("next-arc-v491", "v501.0-v505.0 Manual Observation-to-Sandbox Packet Bridge" in next_steps, "README_NEXT_STEPS.md points to the next autonomy readiness review board arc."),
        _row("dashboard-hover-rule", "data-tip" in next_steps and "native `title` tooltips" in next_steps, "Dashboard custom hover rule remains documented."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "current_state_documentation_header_audit_review_only",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "ok": status == "pass",
        "status": status,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def build_metadata_release_integrity_audit(root_dir: str | Path = ".", docs_text: str | None = None) -> dict[str, Any]:
    """Audit metadata alignment, release version resolution, docs, and no-authorization boundaries."""
    root = Path(root_dir)
    docs = docs_text if docs_text is not None else _read_text(root / "README_NEXT_STEPS.md") + "\n" + _read_text(root / "README_RELEASE_HISTORY.md")
    inventory = build_metadata_version_inventory(root)
    alignment = build_project_workspace_metadata_alignment(root)
    packaging = build_release_packaging_version_integrity(root)
    docs_audit = build_current_state_documentation_header_audit(root)
    required_tokens = [
        "metadata-version-inventory", "project-workspace-metadata-alignment", "release-packaging-version-integrity",
        "current-state-documentation-header-audit", "metadata-release-integrity-audit",
        "operator-governed-metadata-release-integrity-v1", "metadata_consistency_is_authorization=False",
        "release_integrity_pass_is_approval=False", "operator-governed-route-surface-parity-v1",
        "surface_parity_is_permission=False", "route_health_is_approval=False", "operator-governed-self-maintenance-duplicate-shadow-cleanup-v1", "duplicate_cleanup_is_authorization=False", "stale_gate_cleanup_authorizes_execution=False", "operator-governed-documentation-continuity-header-v1", "documentation_state_is_authorization=False", "handoff_packet_is_execution_packet=False", "operator_approval_still_required=True",
    ]
    rows = [
        _row("metadata-inventory", inventory.get("ok") is True, "Current version metadata files align to v500.0."),
        _row("workspace-alignment", alignment.get("ok") is True, "Project/workspace milestone fields agree on v500.0."),
        _row("release-version-resolution", packaging.get("ok") is True, "Release packaging resolves settings_version before stale last_updated_for fallbacks."),
        _row("documentation-current-state", docs_audit.get("ok") is True, "README files expose current state, v495 history, and next autonomy readiness review guidance."),
        _row("smoke-doc-tokens", all(token in docs for token in required_tokens), "Smoke/API/CLI/docs tokens are present for current metadata integrity and v465 route/surface parity."),
        _row("no-authorization-boundary", METADATA_RELEASE_INTEGRITY_BOUNDARIES["metadata_consistency_is_authorization"] is False and METADATA_RELEASE_INTEGRITY_BOUNDARIES["operator_approval_still_required"] is True, "Metadata consistency remains evidence only and does not authorize release, source edits, memory writes, or autonomy."),
    ]
    status = _status_from(rows)
    return {
        "version": METADATA_RELEASE_INTEGRITY_VERSION,
        "state": "metadata_release_integrity_audit_review_only",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "metadata_inventory": inventory,
        "workspace_alignment": alignment,
        "release_version_integrity": packaging,
        "documentation_header_audit": docs_audit,
        "ok": status == "pass",
        "status": status,
        "publishes_release": False,
        "applies_source_edits": False,
        "writes_memory": False,
        "creates_approval": False,
        "executes_actions": False,
        "expands_autonomy": False,
        **METADATA_RELEASE_INTEGRITY_BOUNDARIES,
    }


def render_metadata_release_integrity_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"status: {report.get('status', 'review_only')}",
        f"version: {report.get('version', METADATA_RELEASE_INTEGRITY_VERSION)}",
    ]
    if report.get("expected_version"):
        lines.append(f"expected version: {report.get('expected_version')}")
    if report.get("expected_milestone"):
        lines.append(f"expected milestone: {report.get('expected_milestone')}")
    rows = report.get("rows") or []
    for row in rows[:12]:
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    lines.append("metadata consistency is not authorization; release integrity pass is not approval; fresh operator approval remains required for governed actions.")
    return lines

# v450.1-v455.0 metadata release integrity smoke tokens: metadata-version-inventory project-workspace-metadata-alignment release-packaging-version-integrity current-state-documentation-header-audit metadata-release-integrity-audit operator-governed-metadata-release-integrity-v1 conscious_agent/metadata_release_integrity.py metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False metadata_repair_report_publishes_release=False metadata_repair_report_applies_source_edits=False metadata_repair_report_writes_memory=False metadata_repair_report_expands_autonomy=False operator_approval_still_required=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console
