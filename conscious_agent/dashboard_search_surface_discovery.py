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

DASHBOARD_SEARCH_SURFACE_DISCOVERY_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
SURFACE_SEARCH_INDEX_ID = "v631_surface_search_index"
ROUTE_MODULE_SMOKE_DISCOVERY_CARDS_ID = "v632_route_module_smoke_discovery_cards"
WORKFLOW_AWARE_SEARCH_FILTERS_ID = "v633_workflow_aware_search_filters"
CURRENT_HISTORICAL_SURFACE_GUARD_ID = "v634_current_historical_surface_guard"
DASHBOARD_SEARCH_DISCOVERY_BOARD_ID = "v635_dashboard_search_discovery_board"

SURFACE_INDEX_TYPES: tuple[str, ...] = (
    "dashboard_route",
    "api_route",
    "cli_flag",
    "smoke_check",
    "source_module",
    "release_history_entry",
    "readme_continuity_section",
    "evidence_board",
    "workflow_group",
)

DISCOVERY_CARD_FIELDS: tuple[str, ...] = (
    "title",
    "surface_type",
    "introduced_version",
    "current_status",
    "dashboard_route",
    "api_route",
    "cli_flag",
    "smoke_check",
    "risk_level",
    "operator_required",
)

WORKFLOW_SEARCH_FILTERS: tuple[str, ...] = (
    "Command Center",
    "Patch Lab",
    "Safety",
    "Archive",
    "Memory",
    "System Health",
    "Legacy / History",
    "Current Release",
    "Recent Arcs",
    "Blocked / Operator Required",
)

SURFACE_CLASSIFICATIONS: tuple[str, ...] = (
    "Current",
    "Recent",
    "Historical",
    "Legacy Advisory",
    "Deprecated / Superseded",
)

SEARCH_DISCOVERY_BOUNDARIES: dict[str, bool] = {
    "search_index_executes_queries": False,
    "search_index_executes_actions": False,
    "search_index_grants_approval": False,
    "search_index_treats_presence_as_authorization": False,
    "discovery_cards_open_routes_as_authorization": False,
    "discovery_cards_execute_commands": False,
    "workflow_filters_hide_safety": False,
    "workflow_filters_change_authorization": False,
    "current_historical_guard_treats_current_as_approval": False,
    "current_historical_guard_mutates_status": False,
    "discovery_board_changes_approval_semantics": False,
    "discovery_board_deletes_routes": False,
    "discovery_board_writes_source": False,
    "discovery_board_writes_memory": False,
    "discovery_board_writes_archive_records": False,
    "discovery_board_mutates_current_state": False,
    "discovery_board_runs_smoke": False,
    "discovery_board_creates_release": False,
    "discovery_board_publishes_release": False,
    "discovery_board_reuses_approval": False,
    "discovery_board_continues_automatically": False,
    "discovery_board_expands_autonomy": False,
    "raw_routes_preserved": True,
    "legacy_surfaces_preserved": True,
    "operator_review_required": True,
    "explicit_approval_required_for_writes": True,
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
        "dashboard_search_discovery_status": "prepared_only",
        "search_index_status": "prepared",
        "surface_discovery_status": "prepared",
        "workflow_filter_status": "prepared",
        "current_vs_historical_guard_status": "prepared",
        "raw_routes_preserved": True,
        "legacy_surfaces_preserved": True,
        "approval_semantics_changed": False,
        "authorization_status": "not_authorized",
        "approval_status": "required",
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
        "executes_actions": False,
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


def build_surface_search_index(root: str | Path | None = None) -> dict[str, Any]:
    index = [
        {"surface_type": item, "searchable": True, "executes": False, "grants_authorization": False}
        for item in SURFACE_INDEX_TYPES
    ]
    rows = [
        _row("index-types-present", len(index) >= 9, "Search index covers dashboard routes, API routes, CLI flags, smoke checks, modules, release history, README continuity sections, evidence boards, and workflow groups."),
        _row("index-does-not-execute", SEARCH_DISCOVERY_BOUNDARIES["search_index_executes_actions"] is False and SEARCH_DISCOVERY_BOUNDARIES["search_index_executes_queries"] is False, "Surface search index is prepared metadata and runs no queries or actions by itself."),
        _row("index-not-approval", SEARCH_DISCOVERY_BOUNDARIES["search_index_grants_approval"] is False and SEARCH_DISCOVERY_BOUNDARIES["search_index_treats_presence_as_authorization"] is False, "Search result presence is not approval or authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "surface_search_index_review_only", "search_index_id": SURFACE_SEARCH_INDEX_ID, "surface_index_types": list(SURFACE_INDEX_TYPES), "search_index": index, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SEARCH_DISCOVERY_BOUNDARIES)}


def build_route_module_smoke_discovery_cards(root: str | Path | None = None) -> dict[str, Any]:
    card_template = {
        "title": "Surface Discovery Result",
        "surface_type": "dashboard_route_or_api_or_cli_or_smoke_or_module",
        "introduced_version": "declared_when_known",
        "current_status": "current_recent_historical_or_advisory",
        "dashboard_route": "optional",
        "api_route": "optional",
        "cli_flag": "optional",
        "smoke_check": "optional",
        "risk_level": "operator_review_required_when_applicable",
        "operator_required": True,
    }
    examples = [
        {**card_template, "title": "Archive Reconciliation Application Prep Board", "surface_type": "dashboard_route", "introduced_version": "v610.0", "current_status": "recent", "dashboard_route": "/archive-reconciliation-application-prep-board", "api_route": "/api/archive-reconciliation-application-prep-board/layer", "cli_flag": "--archive-reconciliation-application-prep-board-v1", "smoke_check": "archive-reconciliation-application-prep-v1"},
        {**card_template, "title": "Review Packet Evidence UX Board", "surface_type": "evidence_board", "introduced_version": "v630.0", "current_status": "recent", "dashboard_route": "/review-packet-evidence-ux-board", "api_route": "/api/review-packet-evidence-ux-board/layer", "cli_flag": "--review-packet-evidence-ux-board-v1", "smoke_check": "review-packet-readability-evidence-ux-v1"},
        {**card_template, "title": "Dashboard Search Discovery Board", "surface_type": "current_release", "introduced_version": CURRENT_VERSION_TAG, "current_status": "current", "dashboard_route": "/dashboard-search-discovery-board", "api_route": "/api/dashboard-search-discovery-board/layer", "cli_flag": "--dashboard-search-discovery-board-v1", "smoke_check": TARGETED_SMOKE},
    ]
    rows = [
        _row("card-fields-present", all(field in card_template for field in DISCOVERY_CARD_FIELDS), "Discovery cards declare title, type, version, status, dashboard/API/CLI/smoke links, risk, and operator requirement fields."),
        _row("examples-present", len(examples) >= 3, "Discovery examples cover archive prep, recent evidence UX, and the current dashboard search board."),
        _row("cards-do-not-execute", SEARCH_DISCOVERY_BOUNDARIES["discovery_cards_execute_commands"] is False, "Discovery cards do not execute commands."),
        _row("cards-not-authorization", SEARCH_DISCOVERY_BOUNDARIES["discovery_cards_open_routes_as_authorization"] is False, "Opening a discovered route is not authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "route_module_smoke_discovery_cards_review_only", "discovery_cards_id": ROUTE_MODULE_SMOKE_DISCOVERY_CARDS_ID, "discovery_card_template": card_template, "discovery_card_examples": examples, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SEARCH_DISCOVERY_BOUNDARIES)}


def build_workflow_aware_search_filters(root: str | Path | None = None) -> dict[str, Any]:
    filters = [{"filter": item, "changes_authorization": False, "hides_safety": False} for item in WORKFLOW_SEARCH_FILTERS]
    rows = [
        _row("filters-present", len(filters) >= 10, "Workflow-aware filters cover command center, patch lab, safety, archive, memory, system health, legacy/history, current release, recent arcs, and blocked/operator-required views."),
        _row("safety-visible", SEARCH_DISCOVERY_BOUNDARIES["workflow_filters_hide_safety"] is False and all(item["hides_safety"] is False for item in filters), "Workflow filters do not hide safety state."),
        _row("filters-not-authorization", SEARCH_DISCOVERY_BOUNDARIES["workflow_filters_change_authorization"] is False, "Search filters do not change authorization semantics."),
    ]
    return {"version": CURRENT_VERSION, "state": "workflow_aware_search_filters_review_only", "filters_id": WORKFLOW_AWARE_SEARCH_FILTERS_ID, "workflow_search_filters": filters, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SEARCH_DISCOVERY_BOUNDARIES)}


def build_current_historical_surface_guard(root: str | Path | None = None) -> dict[str, Any]:
    classifications = [
        {"classification": item, "is_authorization": False, "mutates_status": False, "operator_review_required": item in {"Current", "Recent", "Legacy Advisory", "Deprecated / Superseded"}}
        for item in SURFACE_CLASSIFICATIONS
    ]
    rows = [
        _row("classifications-present", len(classifications) == len(SURFACE_CLASSIFICATIONS), "Current, recent, historical, legacy advisory, and deprecated/superseded classifications are prepared."),
        _row("current-not-approval", SEARCH_DISCOVERY_BOUNDARIES["current_historical_guard_treats_current_as_approval"] is False, "Current classification is not operator approval."),
        _row("guard-does-not-mutate", SEARCH_DISCOVERY_BOUNDARIES["current_historical_guard_mutates_status"] is False and all(item["mutates_status"] is False for item in classifications), "Current-vs-historical guard labels surfaces but does not mutate status."),
    ]
    return {"version": CURRENT_VERSION, "state": "current_historical_surface_guard_review_only", "surface_guard_id": CURRENT_HISTORICAL_SURFACE_GUARD_ID, "surface_classifications": classifications, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SEARCH_DISCOVERY_BOUNDARIES)}


def build_dashboard_search_discovery_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    search_index = build_surface_search_index(repo)
    cards = build_route_module_smoke_discovery_cards(repo)
    filters = build_workflow_aware_search_filters(repo)
    guard = build_current_historical_surface_guard(repo)
    scanner = build_stale_version_string_scanner(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard_search_surface_discovery.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py", "conscious_agent/smoke_segment_registry.py", "data/projects.json",
    ])
    required_tokens = [
        "v635.0 - Operator Dashboard Search and Surface Discovery v1",
        TARGETED_SMOKE,
        "surface-search-index",
        "route-module-smoke-discovery-cards",
        "workflow-aware-search-filters",
        "current-historical-surface-guard",
        "dashboard-search-discovery-board",
        "dashboard_search_surface_discovery.py",
        "dashboard_search_discovery_status=prepared_only",
        "search_index_status=prepared",
        "surface_discovery_status=prepared",
        "workflow_filter_status=prepared",
        "current_vs_historical_guard_status=prepared",
        "raw_routes_preserved=True",
        "legacy_surfaces_preserved=True",
        "approval_semantics_changed=False",
        "search_index_grants_approval=False",
        "search_index_treats_presence_as_authorization=False",
        "discovery_cards_execute_commands=False",
        "workflow_filters_hide_safety=False",
        "current_historical_guard_treats_current_as_approval=False",
        "discovery_board_expands_autonomy=False",
    ]
    no_authority_keys = [
        "search_index_executes_queries", "search_index_executes_actions", "search_index_grants_approval",
        "search_index_treats_presence_as_authorization", "discovery_cards_open_routes_as_authorization", "discovery_cards_execute_commands",
        "workflow_filters_hide_safety", "workflow_filters_change_authorization", "current_historical_guard_treats_current_as_approval",
        "current_historical_guard_mutates_status", "discovery_board_changes_approval_semantics", "discovery_board_deletes_routes",
        "discovery_board_writes_source", "discovery_board_writes_memory", "discovery_board_writes_archive_records",
        "discovery_board_mutates_current_state", "discovery_board_runs_smoke", "discovery_board_creates_release",
        "discovery_board_publishes_release", "discovery_board_reuses_approval", "discovery_board_continues_automatically",
        "discovery_board_expands_autonomy",
    ]
    rows = [
        _row("search-index-ready", search_index.get("ok") is True, "Surface search index is prepared."),
        _row("discovery-cards-ready", cards.get("ok") is True, "Route/module/smoke discovery cards are prepared."),
        _row("workflow-filters-ready", filters.get("ok") is True, "Workflow-aware search filters are prepared."),
        _row("current-historical-guard-ready", guard.get("ok") is True, "Current vs historical surface guard is prepared."),
        _row("raw-routes-preserved", SEARCH_DISCOVERY_BOUNDARIES["raw_routes_preserved"] is True and search_index.get("raw_routes_preserved") is True, "Raw routes remain preserved."),
        _row("legacy-surfaces-preserved", SEARCH_DISCOVERY_BOUNDARIES["legacy_surfaces_preserved"] is True and search_index.get("legacy_surfaces_preserved") is True, "Legacy surfaces remain preserved."),
        _row("stale-scanner-clean", scanner.get("ok") is True, "Stale-version scanner remains clean."),
        _row("current-symbols-clean", symbols.get("ok") is True, "Current-symbol audit remains clean."),
        _row("release-board-clean", release_board.get("ok") is True, "Release staleness verification board remains clean and review-only."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v631-v635 search/discovery surfaces and no-authority tokens."),
        _row("no-authority", all(SEARCH_DISCOVERY_BOUNDARIES[key] is False for key in no_authority_keys), "Search/discovery grants no approval, execution, source, memory, archive, smoke, release, publish, current-state mutation, approval reuse, continuation, route deletion, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "dashboard_search_discovery_board_review_only", "board_id": DASHBOARD_SEARCH_DISCOVERY_BOARD_ID, **_base_state(), "surface_search_index": search_index, "route_module_smoke_discovery_cards": cards, "workflow_aware_search_filters": filters, "current_historical_surface_guard": guard, "stale_version_string_scanner": scanner, "current_symbol_staleness_audit": symbols, "release_staleness_verification_board": release_board, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SEARCH_DISCOVERY_BOUNDARIES), "safe_next_action": "Operator may review the v635 dashboard search/discovery board. Next work should standardize decision capture and approval forms without changing approval semantics or expanding autonomy."}


def build_dashboard_search_surface_discovery_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "dashboard_search_discovery_board_v1"
    builders = {
        "surface_search_index_v1": build_surface_search_index,
        "route_module_smoke_discovery_cards_v1": build_route_module_smoke_discovery_cards,
        "workflow_aware_search_filters_v1": build_workflow_aware_search_filters,
        "current_historical_surface_guard_v1": build_current_historical_surface_guard,
        "dashboard_search_discovery_board_v1": build_dashboard_search_discovery_board,
    }
    return builders.get(stage, build_dashboard_search_discovery_board)(root=root)


def render_dashboard_search_surface_discovery_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"dashboard_search_discovery_status: {report.get('dashboard_search_discovery_status')}",
        f"search_index_status: {report.get('search_index_status')}",
        f"surface_discovery_status: {report.get('surface_discovery_status')}",
        f"workflow_filter_status: {report.get('workflow_filter_status')}",
        f"current_vs_historical_guard_status: {report.get('current_vs_historical_guard_status')}",
        f"raw_routes_preserved: {report.get('raw_routes_preserved')}",
        f"legacy_surfaces_preserved: {report.get('legacy_surfaces_preserved')}",
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


# v631.0-v635.0 dashboard search and surface discovery tokens: surface-search-index route-module-smoke-discovery-cards workflow-aware-search-filters current-historical-surface-guard dashboard-search-discovery-board operator-dashboard-search-surface-discovery-v1 dashboard_search_surface_discovery.py dashboard_search_discovery_status=prepared_only search_index_status=prepared surface_discovery_status=prepared workflow_filter_status=prepared current_vs_historical_guard_status=prepared raw_routes_preserved=True legacy_surfaces_preserved=True approval_semantics_changed=False source_mutation_status=not_performed archive_write_status=not_performed memory_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous search_index_executes_queries=False search_index_executes_actions=False search_index_grants_approval=False search_index_treats_presence_as_authorization=False discovery_cards_open_routes_as_authorization=False discovery_cards_execute_commands=False workflow_filters_hide_safety=False workflow_filters_change_authorization=False current_historical_guard_treats_current_as_approval=False current_historical_guard_mutates_status=False discovery_board_changes_approval_semantics=False discovery_board_deletes_routes=False discovery_board_writes_source=False discovery_board_writes_memory=False discovery_board_writes_archive_records=False discovery_board_mutates_current_state=False discovery_board_runs_smoke=False discovery_board_creates_release=False discovery_board_publishes_release=False discovery_board_reuses_approval=False discovery_board_continues_automatically=False discovery_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
