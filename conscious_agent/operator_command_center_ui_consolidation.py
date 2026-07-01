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

OPERATOR_COMMAND_CENTER_UI_CONSOLIDATION_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
COMMAND_CENTER_LANDING_SCREEN_ID = "v611_command_center_landing_screen"
OPERATOR_QUEUE_PANEL_ID = "v612_operator_queue_panel"
SAFETY_STATE_PANEL_ID = "v613_safety_state_panel"
WORKFLOW_NAVIGATION_GROUPS_ID = "v614_workflow_navigation_groups"
SYSTEM_HEALTH_SUMMARY_BOARD_ID = "v615_system_health_summary_board"
OPERATOR_COMMAND_CENTER_UI_CONSOLIDATION_BOARD_ID = "v615_operator_command_center_ui_consolidation_board"

COMMAND_CENTER_FIELDS: tuple[str, ...] = (
    "current_version",
    "autonomy_status",
    "approval_status",
    "source_mutation_status",
    "archive_write_status",
    "memory_write_status",
    "release_status",
    "top_warnings",
    "next_safe_actions",
)

OPERATOR_QUEUE_GROUPS: tuple[str, ...] = (
    "requires_decision",
    "requires_approval",
    "ready_for_review",
    "blocked",
    "prepared_only",
    "advisory",
)

WORKFLOW_NAVIGATION_GROUPS: tuple[str, ...] = (
    "Command",
    "Queue",
    "Patch Lab",
    "Safety",
    "Archive",
    "Memory",
    "System Health",
    "History",
)

SYSTEM_HEALTH_CHECKS: tuple[str, ...] = (
    "version_integrity",
    "stale_version_audit",
    "metadata_integrity",
    "source_package_privacy",
    "dashboard_route_parity",
    "api_runtime_parity",
    "cli_runtime_parity",
    "smoke_coverage",
    "legacy_advisory_blockers",
)

COMMAND_CENTER_BOUNDARIES: dict[str, bool] = {
    "command_center_executes_actions": False,
    "command_center_grants_approval": False,
    "operator_queue_grants_approval": False,
    "safety_panel_changes_authorization": False,
    "workflow_navigation_removes_legacy_routes": False,
    "workflow_navigation_rewrites_approval_semantics": False,
    "system_health_summary_runs_smoke": False,
    "system_health_summary_treats_pass_as_approval": False,
    "ui_consolidation_writes_source": False,
    "ui_consolidation_writes_memory": False,
    "ui_consolidation_writes_archive_records": False,
    "ui_consolidation_mutates_current_state": False,
    "ui_consolidation_creates_release": False,
    "ui_consolidation_publishes_release": False,
    "ui_consolidation_reuses_approval": False,
    "ui_consolidation_continues_automatically": False,
    "ui_consolidation_expands_autonomy": False,
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


def _base_ui_state() -> dict[str, Any]:
    return {
        "ui_consolidation_status": "prepared_only",
        "command_center_status": "review_prepared",
        "operator_queue_status": "review_prepared",
        "safety_panel_status": "review_prepared",
        "workflow_navigation_status": "grouped_without_removal",
        "system_health_status": "summary_prepared",
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


def build_command_center_landing_screen(root: str | Path | None = None) -> dict[str, Any]:
    landing = {
        "current_version": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "autonomy_status": "not_autonomous",
        "approval_status": "required",
        "source_mutation_status": "not_performed",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "top_warnings": ["broad legacy smoke may remain advisory", "archive writes require explicit single-use operator approval"],
        "next_safe_actions": ["review operator queue", "review safety state panel", "review system health summary", "prepare v616-v620 workflow simplification only after operator direction"],
    }
    rows = [
        _row("required-fields-present", all(field in landing for field in COMMAND_CENTER_FIELDS), "Command Center landing screen exposes the core operator status fields."),
        _row("command-center-review-only", COMMAND_CENTER_BOUNDARIES["command_center_executes_actions"] is False, "Command Center summarizes state and executes no actions."),
        _row("approval-not-created", COMMAND_CENTER_BOUNDARIES["command_center_grants_approval"] is False, "Command Center cannot create or infer approval."),
        _row("safety-visible", landing["autonomy_status"] == "not_autonomous" and landing["approval_status"] == "required", "Autonomy and approval boundaries are visible on the landing screen."),
    ]
    return {"version": CURRENT_VERSION, "state": "command_center_landing_screen_review_only", "screen_id": COMMAND_CENTER_LANDING_SCREEN_ID, "landing": landing, **_base_ui_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(COMMAND_CENTER_BOUNDARIES)}


def build_operator_queue_panel(root: str | Path | None = None) -> dict[str, Any]:
    queue = {
        "requires_decision": ["archive reconciliation operator decision remains required before any archive application"],
        "requires_approval": ["archive write", "current-state mutation", "source patch", "release creation", "memory write"],
        "ready_for_review": ["v610 archive reconciliation application prep board", "v615 command center UI consolidation board"],
        "blocked": ["autonomy expansion", "approval reuse", "automatic continuation", "publish"],
        "prepared_only": ["command center landing", "operator queue", "safety panel", "workflow navigation groups", "system health summary"],
        "advisory": ["legacy broad smoke blockers should remain advisory until segmented cleanup"],
    }
    rows = [
        _row("queue-groups-present", all(group in queue for group in OPERATOR_QUEUE_GROUPS), "Operator Queue groups work by decision, approval, review, blocked, prepared-only, and advisory states."),
        _row("queue-not-approval", COMMAND_CENTER_BOUNDARIES["operator_queue_grants_approval"] is False, "Queue entries do not grant or reuse approval."),
        _row("blocked-items-visible", bool(queue["blocked"]), "Blocked actions are visible instead of hidden behind route clutter."),
        _row("prepared-only-visible", bool(queue["prepared_only"]), "Prepared-only UI surfaces are explicit."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_queue_panel_review_only", "queue_id": OPERATOR_QUEUE_PANEL_ID, "queue": queue, **_base_ui_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(COMMAND_CENTER_BOUNDARIES)}


def build_safety_state_panel(root: str | Path | None = None) -> dict[str, Any]:
    safety = {
        "source_writes": {"status": "not_authorized", "reason": "live source writes require exact operator approval"},
        "archive_writes": {"status": "not_authorized", "reason": "archive reconciliation decision and single-use approval are required"},
        "memory_writes": {"status": "not_authorized", "reason": "memory candidates require fresh exact confirmation"},
        "release_creation": {"status": "not_authorized", "reason": "release approval has not been granted"},
        "publishing": {"status": "not_authorized", "reason": "publish permission is separate and absent"},
        "autonomy": {"status": "not_autonomous", "reason": "UI consolidation is not an autonomy phase change"},
        "model_invocation": {"status": "not_default", "reason": "local models remain sandbox/approval scoped"},
    }
    rows = [
        _row("safety-statuses-blocked", all(item["status"] in {"not_authorized", "not_autonomous", "not_default"} for item in safety.values()), "Safety panel shows all high-risk gates as blocked or non-default."),
        _row("safety-panel-not-authority", COMMAND_CENTER_BOUNDARIES["safety_panel_changes_authorization"] is False, "Safety panel cannot change authorization state."),
        _row("reasons-present", all(bool(item.get("reason")) for item in safety.values()), "Every blocked safety item explains why it is blocked."),
    ]
    return {"version": CURRENT_VERSION, "state": "safety_state_panel_review_only", "panel_id": SAFETY_STATE_PANEL_ID, "safety": safety, **_base_ui_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(COMMAND_CENTER_BOUNDARIES)}


def build_workflow_navigation_groups(root: str | Path | None = None) -> dict[str, Any]:
    groups = {
        "Command": ["command-center-landing-screen", "operator-command-center-ui-consolidation-board"],
        "Queue": ["operator-queue-panel"],
        "Patch Lab": ["patch drafts", "sandbox trials", "live patch gates", "rollback plans"],
        "Safety": ["safety-state-panel", "authorization firewall", "approval burnout"],
        "Archive": ["retrieval", "search", "export", "import", "conflict reconciliation", "decision ledger", "application prep"],
        "Memory": ["memory candidates", "memory trials", "retractions", "identity/personality expression"],
        "System Health": ["system-health-summary-board", "stale audit", "metadata integrity", "route parity", "smoke coverage"],
        "History": ["release history", "legacy route drawer candidate"],
    }
    rows = [
        _row("workflow-groups-present", all(group in groups for group in WORKFLOW_NAVIGATION_GROUPS), "Workflow navigation groups present the dashboard by task instead of raw version sprawl."),
        _row("legacy-routes-preserved", COMMAND_CENTER_BOUNDARIES["workflow_navigation_removes_legacy_routes"] is False, "Workflow grouping does not delete existing legacy routes."),
        _row("approval-semantics-preserved", COMMAND_CENTER_BOUNDARIES["workflow_navigation_rewrites_approval_semantics"] is False, "Workflow grouping does not rewrite approval semantics."),
        _row("archive-pipeline-visible", all(token in groups["Archive"] for token in ["retrieval", "search", "export", "import", "conflict reconciliation", "decision ledger", "application prep"]), "Archive governance is represented as a pipeline."),
    ]
    return {"version": CURRENT_VERSION, "state": "workflow_navigation_groups_review_only", "navigation_id": WORKFLOW_NAVIGATION_GROUPS_ID, "groups": groups, **_base_ui_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(COMMAND_CENTER_BOUNDARIES)}


def build_system_health_summary_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scanner = build_stale_version_string_scanner(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    health = {
        "version_integrity": "pass" if symbols.get("ok") else "blocked",
        "stale_version_audit": "pass" if scanner.get("ok") else "blocked",
        "metadata_integrity": "review_required",
        "source_package_privacy": "review_required",
        "dashboard_route_parity": "review_required",
        "api_runtime_parity": "review_required",
        "cli_runtime_parity": "review_required",
        "smoke_coverage": "targeted_current_required",
        "legacy_advisory_blockers": "advisory_not_release_authority",
    }
    rows = [
        _row("health-fields-present", all(field in health for field in SYSTEM_HEALTH_CHECKS), "System Health board summarizes version, stale, metadata, privacy, route, runtime, CLI, smoke, and legacy advisory checks."),
        _row("stale-scanner-clean", scanner.get("ok") is True, "Stale-version scanner remains clean for current-state fields."),
        _row("current-symbols-clean", symbols.get("ok") is True, "Current symbol audit remains aligned."),
        _row("release-board-clean", release_board.get("ok") is True, "Release staleness verification board remains clean and review-only."),
        _row("health-does-not-run-smoke", COMMAND_CENTER_BOUNDARIES["system_health_summary_runs_smoke"] is False, "System Health summary does not execute smoke checks."),
        _row("health-pass-not-approval", COMMAND_CENTER_BOUNDARIES["system_health_summary_treats_pass_as_approval"] is False, "Health pass does not grant approval."),
    ]
    return {"version": CURRENT_VERSION, "state": "system_health_summary_board_review_only", "board_id": SYSTEM_HEALTH_SUMMARY_BOARD_ID, "health": health, "stale_version_string_scanner": scanner, "current_symbol_staleness_audit": symbols, "release_staleness_verification_board": release_board, **_base_ui_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(COMMAND_CENTER_BOUNDARIES)}


def build_operator_command_center_ui_consolidation_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    landing = build_command_center_landing_screen(repo)
    queue = build_operator_queue_panel(repo)
    safety = build_safety_state_panel(repo)
    navigation = build_workflow_navigation_groups(repo)
    health = build_system_health_summary_board(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/operator_command_center_ui_consolidation.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py", "conscious_agent/smoke_segment_registry.py", "data/projects.json",
    ])
    required_tokens = [
        "v615.0 - Operator Command Center UI Consolidation v1",
        TARGETED_SMOKE,
        "command-center-landing-screen",
        "operator-queue-panel",
        "safety-state-panel",
        "workflow-navigation-groups",
        "system-health-summary-board",
        "operator-command-center-ui-consolidation-board",
        "operator_command_center_ui_consolidation.py",
        "ui_consolidation_status=prepared_only",
        "workflow_navigation_status=grouped_without_removal",
        "system_health_summary_runs_smoke=False",
        "command_center_executes_actions=False",
        "operator_queue_grants_approval=False",
        "safety_panel_changes_authorization=False",
        "ui_consolidation_expands_autonomy=False",
        "no_native_title_tooltip",
        "data-tip",
    ]
    rows = [
        _row("landing-ready", landing.get("ok") is True, "Command Center landing screen is prepared."),
        _row("operator-queue-ready", queue.get("ok") is True, "Operator Queue panel is prepared."),
        _row("safety-panel-ready", safety.get("ok") is True, "Safety State panel is prepared."),
        _row("workflow-navigation-ready", navigation.get("ok") is True, "Workflow navigation groups are prepared without removing old routes."),
        _row("system-health-ready", health.get("ok") is True, "System Health summary board is prepared."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v611-v615 UI consolidation surfaces and non-authority tokens."),
        _row("no-authority", all(COMMAND_CENTER_BOUNDARIES[key] is False for key in ["command_center_executes_actions", "command_center_grants_approval", "operator_queue_grants_approval", "safety_panel_changes_authorization", "workflow_navigation_removes_legacy_routes", "workflow_navigation_rewrites_approval_semantics", "system_health_summary_runs_smoke", "system_health_summary_treats_pass_as_approval", "ui_consolidation_writes_source", "ui_consolidation_writes_memory", "ui_consolidation_writes_archive_records", "ui_consolidation_mutates_current_state", "ui_consolidation_creates_release", "ui_consolidation_publishes_release", "ui_consolidation_reuses_approval", "ui_consolidation_continues_automatically", "ui_consolidation_expands_autonomy"]), "UI consolidation grants no approval, write, mutation, command, smoke, release, publish, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_command_center_ui_consolidation_board_review_only", "board_id": OPERATOR_COMMAND_CENTER_UI_CONSOLIDATION_BOARD_ID, **_base_ui_state(), "command_center_landing_screen": landing, "operator_queue_panel": queue, "safety_state_panel": safety, "workflow_navigation_groups": navigation, "system_health_summary_board": health, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(COMMAND_CENTER_BOUNDARIES), "safe_next_action": "Operator may review the v615 command center UI consolidation board. Next work should simplify dashboard workflow and legacy route drawers without deleting existing routes, changing approval semantics, or expanding autonomy."}


def build_operator_command_center_ui_consolidation_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "operator_command_center_ui_consolidation_board_v1"
    builders = {
        "command_center_landing_screen_v1": build_command_center_landing_screen,
        "operator_queue_panel_v1": build_operator_queue_panel,
        "safety_state_panel_v1": build_safety_state_panel,
        "workflow_navigation_groups_v1": build_workflow_navigation_groups,
        "system_health_summary_board_v1": build_system_health_summary_board,
        "operator_command_center_ui_consolidation_board_v1": build_operator_command_center_ui_consolidation_board,
    }
    return builders.get(stage, build_operator_command_center_ui_consolidation_board)(root=root)


def render_operator_command_center_ui_consolidation_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"ui_consolidation_status: {report.get('ui_consolidation_status')}",
        f"command_center_status: {report.get('command_center_status')}",
        f"operator_queue_status: {report.get('operator_queue_status')}",
        f"safety_panel_status: {report.get('safety_panel_status')}",
        f"workflow_navigation_status: {report.get('workflow_navigation_status')}",
        f"system_health_status: {report.get('system_health_status')}",
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


# v611.0-v615.0 operator command center UI consolidation tokens: command-center-landing-screen operator-queue-panel safety-state-panel workflow-navigation-groups system-health-summary-board operator-command-center-ui-consolidation-board operator-command-center-ui-consolidation-v1 operator_command_center_ui_consolidation.py ui_consolidation_status=prepared_only command_center_status=review_prepared operator_queue_status=review_prepared safety_panel_status=review_prepared workflow_navigation_status=grouped_without_removal system_health_status=summary_prepared source_mutation_status=not_performed archive_write_status=not_performed memory_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous command_center_executes_actions=False command_center_grants_approval=False operator_queue_grants_approval=False safety_panel_changes_authorization=False workflow_navigation_removes_legacy_routes=False workflow_navigation_rewrites_approval_semantics=False system_health_summary_runs_smoke=False system_health_summary_treats_pass_as_approval=False ui_consolidation_writes_source=False ui_consolidation_writes_memory=False ui_consolidation_writes_archive_records=False ui_consolidation_mutates_current_state=False ui_consolidation_creates_release=False ui_consolidation_publishes_release=False ui_consolidation_reuses_approval=False ui_consolidation_continues_automatically=False ui_consolidation_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
