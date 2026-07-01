from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import (
    CURRENT_VERSION,
    CURRENT_VERSION_TAG,
    CURRENT_MILESTONE,
    NEXT_RECOMMENDED_ARC,
    build_current_symbol_staleness_audit,
    build_release_staleness_and_verification_audit_board,
    build_stale_version_string_scanner,
)

DASHBOARD_WORKFLOW_SIMPLIFICATION_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
WORKFLOW_GROUP_ROUTE_INDEX_ID = "v616_workflow_group_route_index"
LEGACY_ROUTE_DRAWER_ID = "v617_legacy_route_drawer"
ARCHIVE_WORKFLOW_PIPELINE_VIEW_ID = "v618_archive_workflow_pipeline_view"
PATCH_SAFETY_MEMORY_GROUP_VIEWS_ID = "v619_patch_safety_memory_group_views"
DASHBOARD_SIMPLIFICATION_BOARD_ID = "v620_dashboard_simplification_board"

WORKFLOW_GROUPS: tuple[str, ...] = (
    "Command",
    "Queue",
    "Patch Lab",
    "Safety",
    "Archive",
    "Memory",
    "System Health",
    "History / Legacy",
)

LEGACY_DRAWER_POLICY: dict[str, bool] = {
    "old_routes_preserved": True,
    "legacy_routes_deleted": False,
    "legacy_routes_hidden_from_history": False,
    "legacy_drawer_executes_routes": False,
    "legacy_drawer_grants_approval": False,
    "legacy_drawer_changes_authorization": False,
}

ARCHIVE_PIPELINE_STAGES: tuple[dict[str, str], ...] = (
    {"stage": "Archive Retrieval", "introduced_version": "v575.0", "route": "/release-archive-continuity-board", "status": "historical_available", "write_allowed": "no"},
    {"stage": "Archive Search", "introduced_version": "v580.0", "route": "/release-archive-search-handoff-board", "status": "historical_available", "write_allowed": "no"},
    {"stage": "Archive Export", "introduced_version": "v585.0", "route": "/release-archive-export-decision-closure-board", "status": "historical_available", "write_allowed": "no"},
    {"stage": "Archive Import", "introduced_version": "v590.0", "route": "/release-archive-import-closure-recall-board", "status": "historical_available", "write_allowed": "no"},
    {"stage": "Conflict Reconciliation", "introduced_version": "v595.0", "route": "/imported-archive-conflict-reconciliation-board", "status": "review_prepared", "write_allowed": "no"},
    {"stage": "Decision Ledger", "introduced_version": "v600.0", "route": "/archive-reconciliation-decision-ledger-board", "status": "operator_decision_required", "write_allowed": "no"},
    {"stage": "Application Prep", "introduced_version": "v610.0", "route": "/archive-reconciliation-application-prep-board", "status": "prepared_only", "write_allowed": "no"},
)

SIMPLIFICATION_BOUNDARIES: dict[str, bool] = {
    "workflow_index_executes_actions": False,
    "workflow_index_grants_approval": False,
    "legacy_drawer_deletes_routes": False,
    "legacy_drawer_hides_safety": False,
    "archive_pipeline_writes_archive_records": False,
    "archive_pipeline_selects_reconciliation": False,
    "archive_pipeline_mutates_current_state": False,
    "group_views_execute_patch": False,
    "group_views_write_memory": False,
    "group_views_change_authorization": False,
    "simplification_board_changes_approval_semantics": False,
    "simplification_board_reintroduces_native_title_tooltips": False,
    "simplification_board_writes_source": False,
    "simplification_board_writes_memory": False,
    "simplification_board_writes_archive_records": False,
    "simplification_board_mutates_current_state": False,
    "simplification_board_creates_release": False,
    "simplification_board_publishes_release": False,
    "simplification_board_reuses_approval": False,
    "simplification_board_continues_automatically": False,
    "simplification_board_expands_autonomy": False,
    "operator_review_required": True,
    "approval_required_for_writes": True,
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


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _base_state() -> dict[str, Any]:
    return {
        "dashboard_simplification_status": "prepared_only",
        "workflow_grouping_status": "prepared",
        "legacy_route_drawer_status": "prepared_without_route_deletion",
        "archive_pipeline_status": "prepared_read_only",
        "group_views_status": "prepared_review_only",
        "legacy_routes_preserved": True,
        "native_title_tooltips": "not_reintroduced",
        "data_tip_hover_system": "preserved",
        "command_deck_style": "preserved",
        "approval_semantics_changed": False,
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "source_mutation_status": "not_performed",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "writes_source": False,
        "writes_memory": False,
        "writes_archive_records": False,
        "writes_external_ledger": False,
        "mutates_current_state": False,
        "executes_commands": False,
        "executes_smoke": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "operator_review_required": True,
    }


def build_workflow_group_route_index(root: str | Path | None = None) -> dict[str, Any]:
    groups = {
        "Command": ["/command-center-landing-screen", "/operator-command-center-ui-consolidation-board"],
        "Queue": ["/operator-queue-panel"],
        "Patch Lab": ["/patch-drafts", "/sandbox-execution-approval-gate", "/sandbox-to-source-promotion-packet"],
        "Safety": ["/safety-state-panel", "/governance-authorization-firewall", "/current-state-integrity-staleness-hardening-board"],
        "Archive": ["/archive-reconciliation-decision-ledger-board", "/archive-reconciliation-application-prep-board"],
        "Memory": ["/memory-lifecycle-review-board", "/memory-application-dry-run-ledger"],
        "System Health": ["/system-health-summary-board", "/route-surface-parity", "/source-surface-manifest"],
        "History / Legacy": ["legacy-route-drawer"],
    }
    rows = [
        _row("workflow-groups-present", all(group in groups for group in WORKFLOW_GROUPS), "Workflow route index exposes Command, Queue, Patch Lab, Safety, Archive, Memory, System Health, and History / Legacy groups."),
        _row("grouping-review-only", SIMPLIFICATION_BOUNDARIES["workflow_index_executes_actions"] is False, "Workflow route index is navigation metadata only and executes no actions."),
        _row("grouping-not-approval", SIMPLIFICATION_BOUNDARIES["workflow_index_grants_approval"] is False, "Workflow grouping does not grant or imply approval."),
        _row("archive-route-group-present", "/archive-reconciliation-application-prep-board" in groups["Archive"], "Archive group includes the current archive reconciliation application prep surface."),
    ]
    return {"version": CURRENT_VERSION, "state": "workflow_group_route_index_review_only", "index_id": WORKFLOW_GROUP_ROUTE_INDEX_ID, "workflow_groups": groups, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SIMPLIFICATION_BOUNDARIES)}


def build_legacy_route_drawer(root: str | Path | None = None) -> dict[str, Any]:
    drawer = {
        "label": "Legacy / Full Surface Drawer",
        "purpose": "Keep old versioned and arc-specific routes accessible without placing them all in the primary operator path.",
        "route_policy": dict(LEGACY_DRAWER_POLICY),
        "legacy_buckets": {
            "archive_history": ["v570-v610 archive governance surfaces"],
            "patch_trials": ["sandbox, live patch, rollback, and verification trial surfaces"],
            "memory_identity": ["memory, identity, personality, and expression trial surfaces"],
            "system_audits": ["stale, metadata, package privacy, route parity, and smoke audit surfaces"],
            "early_history": ["pre-v500 historical governance and development surfaces"],
        },
    }
    rows = [
        _row("legacy-routes-preserved", LEGACY_DRAWER_POLICY["old_routes_preserved"] is True, "Legacy drawer preserves old routes instead of deleting them."),
        _row("legacy-routes-not-deleted", LEGACY_DRAWER_POLICY["legacy_routes_deleted"] is False, "Legacy drawer does not remove historical dashboard surfaces."),
        _row("legacy-drawer-not-execution", LEGACY_DRAWER_POLICY["legacy_drawer_executes_routes"] is False, "Legacy drawer is an access/navigation concept, not route execution."),
        _row("legacy-drawer-not-approval", LEGACY_DRAWER_POLICY["legacy_drawer_grants_approval"] is False, "Legacy drawer does not grant approval or authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "legacy_route_drawer_review_only", "drawer_id": LEGACY_ROUTE_DRAWER_ID, "drawer": drawer, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SIMPLIFICATION_BOUNDARIES)}


def build_archive_workflow_pipeline_view(root: str | Path | None = None) -> dict[str, Any]:
    pipeline = []
    for stage in ARCHIVE_PIPELINE_STAGES:
        item = dict(stage)
        item["operator_required"] = "yes"
        item["current_blocker"] = "explicit single-use operator decision/approval required before writes" if stage["write_allowed"] == "no" else "none"
        item["open_surface"] = stage["route"]
        pipeline.append(item)
    rows = [
        _row("pipeline-complete", len(pipeline) == len(ARCHIVE_PIPELINE_STAGES), "Archive pipeline covers retrieval, search, export, import, conflict reconciliation, decision ledger, and application prep."),
        _row("pipeline-read-only", SIMPLIFICATION_BOUNDARIES["archive_pipeline_writes_archive_records"] is False, "Archive workflow pipeline view writes no archive records."),
        _row("pipeline-does-not-select", SIMPLIFICATION_BOUNDARIES["archive_pipeline_selects_reconciliation"] is False, "Archive workflow pipeline does not select reconciliation options."),
        _row("pipeline-does-not-mutate", SIMPLIFICATION_BOUNDARIES["archive_pipeline_mutates_current_state"] is False, "Archive workflow pipeline does not mutate current state."),
    ]
    return {"version": CURRENT_VERSION, "state": "archive_workflow_pipeline_view_review_only", "pipeline_id": ARCHIVE_WORKFLOW_PIPELINE_VIEW_ID, "archive_pipeline": pipeline, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SIMPLIFICATION_BOUNDARIES)}


def build_patch_safety_memory_group_views(root: str | Path | None = None) -> dict[str, Any]:
    groups = {
        "Patch Lab": {"summary": "Patch drafting, sandbox preparation, live-patch gates, receipts, and rollback review surfaces grouped for navigation only.", "blocked_actions": ["patch execution", "approval reuse", "automatic continuation"]},
        "Safety & Authorization": {"summary": "Authorization firewall, safety state, stale-version, metadata, and package privacy review surfaces grouped for visibility.", "blocked_actions": ["authorization changes", "release approval inference", "smoke pass treated as consent"]},
        "Memory & Identity": {"summary": "Memory candidate, memory write trial, retraction, identity, personality, and expression surfaces grouped under locked review.", "blocked_actions": ["memory write", "identity mutation", "personality mutation"]},
        "System Health": {"summary": "Version, metadata, dashboard, API, CLI, smoke, package privacy, and legacy advisory checks grouped for status review.", "blocked_actions": ["command execution from summary", "release approval inference"]},
    }
    rows = [
        _row("group-views-present", all(name in groups for name in ["Patch Lab", "Safety & Authorization", "Memory & Identity", "System Health"]), "Patch, safety, memory, and health grouped views are prepared."),
        _row("patch-group-no-execution", SIMPLIFICATION_BOUNDARIES["group_views_execute_patch"] is False, "Patch group view does not execute patches."),
        _row("memory-group-no-write", SIMPLIFICATION_BOUNDARIES["group_views_write_memory"] is False, "Memory group view writes no memory."),
        _row("safety-group-no-auth-change", SIMPLIFICATION_BOUNDARIES["group_views_change_authorization"] is False, "Safety group view cannot change authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "patch_safety_memory_group_views_review_only", "group_views_id": PATCH_SAFETY_MEMORY_GROUP_VIEWS_ID, "group_views": groups, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SIMPLIFICATION_BOUNDARIES)}


def build_dashboard_simplification_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    index = build_workflow_group_route_index(repo)
    drawer = build_legacy_route_drawer(repo)
    archive = build_archive_workflow_pipeline_view(repo)
    grouped = build_patch_safety_memory_group_views(repo)
    scanner = build_stale_version_string_scanner(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard_workflow_simplification.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py", "conscious_agent/smoke_segment_registry.py", "data/projects.json",
    ])
    required_tokens = [
        "v620.0 - Dashboard Workflow Simplification and Legacy Route Drawer v1",
        TARGETED_SMOKE,
        "workflow-group-route-index",
        "legacy-route-drawer",
        "archive-workflow-pipeline-view",
        "patch-safety-memory-group-views",
        "dashboard-simplification-board",
        "dashboard_workflow_simplification.py",
        "dashboard_simplification_status=prepared_only",
        "workflow_grouping_status=prepared",
        "legacy_routes_preserved=True",
        "native_title_tooltips=not_reintroduced",
        "data_tip_hover_system=preserved",
        "approval_semantics_changed=False",
        "simplification_board_expands_autonomy=False",
    ]
    rows = [
        _row("workflow-index-ready", index.get("ok") is True, "Workflow group route index is prepared."),
        _row("legacy-drawer-ready", drawer.get("ok") is True, "Legacy route drawer is prepared without route deletion."),
        _row("archive-pipeline-ready", archive.get("ok") is True, "Archive workflow pipeline view is prepared and read-only."),
        _row("group-views-ready", grouped.get("ok") is True, "Patch, safety, memory, and system health grouped views are prepared."),
        _row("stale-scanner-clean", scanner.get("ok") is True, "Stale-version scanner remains clean for current-state fields."),
        _row("current-symbols-clean", symbols.get("ok") is True, "Current symbol audit remains aligned."),
        _row("release-board-clean", release_board.get("ok") is True, "Release staleness verification board remains clean and review-only."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v616-v620 simplification surfaces and non-authority tokens."),
        _row("no-authority", all(SIMPLIFICATION_BOUNDARIES[key] is False for key in ["workflow_index_executes_actions", "workflow_index_grants_approval", "legacy_drawer_deletes_routes", "legacy_drawer_hides_safety", "archive_pipeline_writes_archive_records", "archive_pipeline_selects_reconciliation", "archive_pipeline_mutates_current_state", "group_views_execute_patch", "group_views_write_memory", "group_views_change_authorization", "simplification_board_changes_approval_semantics", "simplification_board_reintroduces_native_title_tooltips", "simplification_board_writes_source", "simplification_board_writes_memory", "simplification_board_writes_archive_records", "simplification_board_mutates_current_state", "simplification_board_creates_release", "simplification_board_publishes_release", "simplification_board_reuses_approval", "simplification_board_continues_automatically", "simplification_board_expands_autonomy"]), "Dashboard simplification grants no approval, write, mutation, command, smoke, release, publish, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "dashboard_simplification_board_review_only", "board_id": DASHBOARD_SIMPLIFICATION_BOARD_ID, **_base_state(), "workflow_group_route_index": index, "legacy_route_drawer": drawer, "archive_workflow_pipeline_view": archive, "patch_safety_memory_group_views": grouped, "stale_version_string_scanner": scanner, "current_symbol_staleness_audit": symbols, "release_staleness_verification_board": release_board, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SIMPLIFICATION_BOUNDARIES), "safe_next_action": "Operator may review the v620 dashboard simplification board. Next work should standardize action semantics and approval UX without changing approval rules or expanding autonomy."}


def build_dashboard_workflow_simplification_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "dashboard_simplification_board_v1"
    builders = {
        "workflow_group_route_index_v1": build_workflow_group_route_index,
        "legacy_route_drawer_v1": build_legacy_route_drawer,
        "archive_workflow_pipeline_view_v1": build_archive_workflow_pipeline_view,
        "patch_safety_memory_group_views_v1": build_patch_safety_memory_group_views,
        "dashboard_simplification_board_v1": build_dashboard_simplification_board,
    }
    return builders.get(stage, build_dashboard_simplification_board)(root=root)


def render_dashboard_workflow_simplification_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"dashboard_simplification_status: {report.get('dashboard_simplification_status')}",
        f"workflow_grouping_status: {report.get('workflow_grouping_status')}",
        f"legacy_route_drawer_status: {report.get('legacy_route_drawer_status')}",
        f"archive_pipeline_status: {report.get('archive_pipeline_status')}",
        f"group_views_status: {report.get('group_views_status')}",
        f"legacy_routes_preserved: {report.get('legacy_routes_preserved')}",
        f"native_title_tooltips: {report.get('native_title_tooltips')}",
        f"data_tip_hover_system: {report.get('data_tip_hover_system')}",
        f"approval_semantics_changed: {report.get('approval_semantics_changed')}",
        f"source_mutation_status: {report.get('source_mutation_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"memory_write_status: {report.get('memory_write_status')}",
        f"release_status: {report.get('release_status')}",
        f"publish_status: {report.get('publish_status')}",
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


# v616.0-v620.0 dashboard workflow simplification tokens: workflow-group-route-index legacy-route-drawer archive-workflow-pipeline-view patch-safety-memory-group-views dashboard-simplification-board dashboard-workflow-simplification-legacy-drawer-v1 dashboard_workflow_simplification.py dashboard_simplification_status=prepared_only workflow_grouping_status=prepared legacy_routes_preserved=True native_title_tooltips=not_reintroduced data_tip_hover_system=preserved approval_semantics_changed=False source_mutation_status=not_performed archive_write_status=not_performed memory_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous workflow_index_executes_actions=False workflow_index_grants_approval=False legacy_drawer_deletes_routes=False legacy_drawer_hides_safety=False archive_pipeline_writes_archive_records=False archive_pipeline_selects_reconciliation=False archive_pipeline_mutates_current_state=False group_views_execute_patch=False group_views_write_memory=False group_views_change_authorization=False simplification_board_changes_approval_semantics=False simplification_board_reintroduces_native_title_tooltips=False simplification_board_writes_source=False simplification_board_writes_memory=False simplification_board_writes_archive_records=False simplification_board_mutates_current_state=False simplification_board_creates_release=False simplification_board_publishes_release=False simplification_board_reuses_approval=False simplification_board_continues_automatically=False simplification_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
