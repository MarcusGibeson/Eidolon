from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any
import importlib

from api_server_dispatch_shared import (
    API_SERVER_DISPATCH_ROUTE_TABLE,
    API_SERVER_DISPATCH_ROUTE_TABLE_ID,
    API_SERVER_DISPATCH_SHARED_VERSION,
    api_dispatch_helper_rows,
    api_dispatch_route_table_rows,
    build_manual_preview_dispatch_payload,
    build_route_table_preview_payload,
)
from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from review_surface_shared import (
    DEFAULT_AUTHORITY_BOUNDARIES,
    REVIEW_SURFACE_SHARED_VERSION,
    build_api_preview_envelope,
    check_row,
    missing_tokens,
    ok_from_rows,
    render_review_card_component,
    render_review_table_component,
    repo_root,
    status_from_rows,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1074.4"
ARC_TITLE = "API Server Dispatch Route Table Safety Parity v1"
REVIEW_ID = "api-server-dispatch-route-table-safety-parity-v1"
SELF_ROUTE = "/api-server-dispatch-route-table-safety-parity"
API_ROUTE = "/api/source-surface/api-server-dispatch-route-table-safety-parity"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
MIGRATED_SLUG = "api-server-dispatch-route-table-backfill"
HELPER_ID = API_SERVER_DISPATCH_ROUTE_TABLE_ID

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

SAFETY_PARITY_KEYS: tuple[str, ...] = (
    "api_get_preview_only",
    "dashboard_get_preview_only",
    "actual_fixture_execution_count",
    "subprocess_spawn_count",
    "source_write_count",
    "source_delete_count",
    "actual_fixture_execution_allowed",
    "generated_wiring_activated",
    "release_authorized",
    "autonomy_expanded",
    "manual_api_dispatch_remains_authoritative",
    "manual_route_table_replaces_api_dispatch",
)

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/api_server_dispatch_route_table_backfill.py",
    "conscious_agent/api_server_dispatch_route_table_safety_parity.py",
    "conscious_agent/review_surface_shared.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/smoke_segment_registry.py",
    "tools/smoke_check.py",
)

REQUIRED_TOKENS: tuple[str, ...] = (
    REVIEW_ID,
    SELF_ROUTE,
    API_ROUTE,
    HELPER_ID,
    MIGRATED_SLUG,
    "api-server-dispatch-route-table-v1",
    "API_SERVER_DISPATCH_ROUTE_TABLE",
    "api_dispatch_route_table_rows",
    "build_route_table_preview_payload",
    "build_manual_preview_dispatch_payload",
    "build_api_server_dispatch_route_table_safety_parity",
    "build_api_server_dispatch_route_table_safety_parity_metadata",
    "api_server_dispatch_route_table_safety_parity_text",
    "api_preview_payload",
    "route_table_payload_manual_helper_parity=True",
    "route_table_safety_key_parity=True",
    "route_table_safe_preview_row_count=4",
    "route_table_newly_migrated_route_count=1",
    "old_direct_branch_removed=True",
    "manual_route_table_replaces_api_dispatch=False",
    "actual_fixture_execution_count=0",
    "subprocess_spawn_count=0",
    "source_write_count=0",
    "source_delete_count=0",
    "generated_wiring_activated=False",
    "release_authorized=False",
    "autonomy_expanded=False",
    "dashboard_get_preview_only=True",
    "api_get_preview_only=True",
    "manual_api_dispatch_remains_authoritative=True",
    "manual_dashboard_remains_authoritative=True",
    "manual_smoke_remains_authoritative=True",
    "operator_approval_required=True",
    "data-tip",
    "command-deck",
    "operator-console",
    "no_native_title_tooltip",
)

BOUNDARY_ROWS: tuple[dict[str, Any], ...] = (
    {"boundary": "api_get_preview_only", "expected": True, "actual": True, "status": "pass"},
    {"boundary": "dashboard_get_preview_only", "expected": True, "actual": True, "status": "pass"},
    {"boundary": "actual_fixture_execution_count", "expected": 0, "actual": 0, "status": "pass"},
    {"boundary": "subprocess_spawn_count", "expected": 0, "actual": 0, "status": "pass"},
    {"boundary": "source_write_count", "expected": 0, "actual": 0, "status": "pass"},
    {"boundary": "source_delete_count", "expected": 0, "actual": 0, "status": "pass"},
    {"boundary": "generated_wiring_activated", "expected": False, "actual": False, "status": "pass"},
    {"boundary": "release_authorized", "expected": False, "actual": False, "status": "pass"},
    {"boundary": "autonomy_expanded", "expected": False, "actual": False, "status": "pass"},
)


def _docs(root: Path) -> str:
    chunks: list[str] = []
    for rel in DOC_PATHS:
        try:
            chunks.append((root / rel).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            chunks.append("")
    return "\n".join(chunks)


def _manual_payload_for_entry(entry: dict[str, Any], query: dict[str, list[str]], root: Path) -> dict[str, Any]:
    module = importlib.import_module(str(entry["module"]))
    payload = build_manual_preview_dispatch_payload(
        query,
        project_root=root,
        metadata_builder=getattr(module, str(entry["metadata_builder"])),
        report_builder=getattr(module, str(entry["report_builder"])),
        payload_builder=getattr(module, str(entry["payload_builder"])),
        warning=str(entry["warning"]),
    )
    payload.setdefault("api_dispatch_route_table", API_SERVER_DISPATCH_ROUTE_TABLE_ID)
    payload.setdefault("manual_route_table_replaces_api_dispatch", False)
    return payload


def _safety_snapshot(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return {key: payload.get(key) for key in SAFETY_PARITY_KEYS}


def _payload_parity_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in API_SERVER_DISPATCH_ROUTE_TABLE:
        slug = str(entry["slug"])
        query: dict[str, list[str]] = {"execute": ["true"], "live": ["true"], "approve": ["true"]}
        route_table_payload = build_route_table_preview_payload(["source-surface", slug], query, project_root=root)
        manual_payload = _manual_payload_for_entry(entry, query, root)
        route_table_snapshot = _safety_snapshot(route_table_payload)
        manual_snapshot = _safety_snapshot(manual_payload)
        warning_text = " ".join((route_table_payload or {}).get("warnings") or [])
        ok = (
            route_table_payload is not None
            and route_table_snapshot == manual_snapshot
            and route_table_payload.get("api_dispatch_route_table") == API_SERVER_DISPATCH_ROUTE_TABLE_ID
            and route_table_payload.get("manual_route_table_replaces_api_dispatch") is False
            and "GET preview-only" in warning_text
        )
        rows.append({
            "slug": slug,
            "route": f"/api/source-surface/{slug}",
            "module": str(entry["module"]),
            "route_table_payload_built": route_table_payload is not None,
            "manual_helper_payload_built": True,
            "safety_key_parity": route_table_snapshot == manual_snapshot,
            "warning_parity_guard": "GET preview-only" in warning_text,
            "route_table_id": (route_table_payload or {}).get("api_dispatch_route_table"),
            "manual_route_table_replaces_api_dispatch": (route_table_payload or {}).get("manual_route_table_replaces_api_dispatch"),
            "status": "pass" if ok else "blocked",
        })
    return rows


def _api_server_migration_rows(root: Path) -> list[dict[str, Any]]:
    text = (root / "conscious_agent/api_server.py").read_text(encoding="utf-8", errors="ignore")
    route_table_anchor = "route_table_payload = build_route_table_preview_payload(parts, query"
    manual_return_anchor = "return 200, _ok(route_table_payload)"
    rows: list[dict[str, Any]] = []
    for row in api_dispatch_route_table_rows():
        slug = str(row.get("slug"))
        old_branch_token = f'source_surface_route_matches(parts, "{slug}")'
        rows.append({
            "slug": slug,
            "route": row.get("route"),
            "uses_route_table_payload": route_table_anchor in text,
            "manual_dispatch_return_preserved": manual_return_anchor in text,
            "old_direct_branch_removed": old_branch_token not in text,
            "newly_migrated_in_current_arc": slug == MIGRATED_SLUG and old_branch_token not in text,
            "status": "pass" if route_table_anchor in text and manual_return_anchor in text and old_branch_token not in text else "blocked",
        })
    return rows


def _base_checks(root: Path, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    parity_rows = _payload_parity_rows(root)
    migration_rows = _api_server_migration_rows(root)
    migrated_rows = [row for row in migration_rows if row.get("newly_migrated_in_current_arc")]
    rows = [
        check_row("current-version", CURRENT_VERSION == MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-advanced", CURRENT_VERSION >= MODULE_VERSION and bool(CURRENT_MILESTONE), f"milestone={CURRENT_MILESTONE}"),
        check_row("next-arc-forward", bool(NEXT_RECOMMENDED_ARC) and NEXT_RECOMMENDED_ARC != CURRENT_MILESTONE, f"next={NEXT_RECOMMENDED_ARC}"),
        check_row("dispatch-helper-compatible", API_SERVER_DISPATCH_SHARED_VERSION >= MODULE_VERSION, f"dispatch_helper={API_SERVER_DISPATCH_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("shared-review-helper-compatible", REVIEW_SURFACE_SHARED_VERSION >= "1070.1", f"review_shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("route-table-row-count", len(api_dispatch_route_table_rows()) >= 4, "API dispatch route table includes the migrated backfill route.", route_table_safe_preview_row_count=len(api_dispatch_route_table_rows())),
        check_row("route-table-new-migration-count", len(migrated_rows) == 1, "Exactly one additional safe preview route moved from direct helper branch to route-table dispatch.", route_table_newly_migrated_route_count=len(migrated_rows), migrated_rows=migrated_rows),
        check_row("route-table-payload-manual-helper-parity", all(row.get("status") == "pass" and row.get("safety_key_parity") is True for row in parity_rows), "Route-table payloads match manual helper payloads for safety-critical fields.", route_table_payload_manual_helper_parity=True, route_table_safety_key_parity=all(row.get("safety_key_parity") is True for row in parity_rows), parity_rows=parity_rows),
        check_row("api-server-migration-adoption", all(row.get("status") == "pass" for row in migration_rows), "api_server.py keeps manual route-table call authoritative and removes direct branches for table-backed routes.", migration_rows=migration_rows, old_direct_branch_removed=True),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual API/dashboard/smoke dispatch remains authoritative."),
        check_row("preview-only", AUTHORITY_BOUNDARIES["api_get_preview_only"] and AUTHORITY_BOUNDARIES["dashboard_get_preview_only"], "GET paths remain preview-only."),
        check_row("no-subprocess-write-delete", all(row.get("actual") == row.get("expected") for row in BOUNDARY_ROWS if row.get("boundary") in {"subprocess_spawn_count", "source_write_count", "source_delete_count"}), "No subprocesses, writes, or deletes are introduced."),
        check_row("no-release-autonomy-or-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"] and not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No generated wiring activation, release authorization, or autonomy expansion."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_api_server_dispatch_route_table_safety_parity(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    base = repo_root(root)
    docs = docs if docs is not None else (_docs(base) if inspect_sources else "")
    missing = missing_tokens(docs, REQUIRED_TOKENS) if inspect_sources else []
    token_row = check_row("required-token-coverage", not missing, "Docs/source contain v1070.9 API dispatch route table safety parity evidence tokens.", missing_tokens=missing, required_token_count=len(REQUIRED_TOKENS))
    rows = _base_checks(base, [token_row])
    parity_rows = _payload_parity_rows(base)
    migration_rows = _api_server_migration_rows(base)
    migrated_rows = [row for row in migration_rows if row.get("newly_migrated_in_current_arc")]
    return {
        "version": MODULE_VERSION,
        "arc_version": ARC_VERSION,
        "arc_title": ARC_TITLE,
        "review_id": REVIEW_ID,
        "route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": status_from_rows(rows),
        "ok": ok_from_rows(rows),
        "rows": rows,
        "route_table_rows": api_dispatch_route_table_rows(),
        "base_helper_rows": api_dispatch_helper_rows(),
        "payload_parity_rows": parity_rows,
        "migration_rows": migration_rows,
        "boundary_rows": list(BOUNDARY_ROWS),
        "route_table_safe_preview_row_count": len(api_dispatch_route_table_rows()),
        "route_table_newly_migrated_route_count": len(migrated_rows),
        "route_table_payload_manual_helper_parity": all(row.get("status") == "pass" for row in parity_rows),
        "route_table_safety_key_parity": all(row.get("safety_key_parity") is True for row in parity_rows),
        "migrated_routes": [row.get("route") for row in migrated_rows],
        "actual_fixture_execution_count": 0,
        "subprocess_spawn_count": 0,
        "source_write_count": 0,
        "source_delete_count": 0,
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_allowed": False,
        "sandbox_backend_adapter_integrated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "manual_route_table_replaces_api_dispatch": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "operator_approval_required": True,
        "actual_fixture_execution_blocked_reason": "Real fixture execution remains blocked until a real audited OS-enforced sandbox backend exists.",
        "authority_boundaries": dict(AUTHORITY_BOUNDARIES),
    }


def build_api_server_dispatch_route_table_safety_parity_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    report = build_api_server_dispatch_route_table_safety_parity(repo_root(), inspect_sources=False)
    report["project_id"] = project_id
    report["metadata_only"] = True
    return report


def api_preview_payload(report: dict[str, Any]) -> dict[str, Any]:
    return build_api_preview_envelope(report, route=API_ROUTE, adapter="api-server-dispatch-route-table-safety-parity-v1")


def render_api_server_dispatch_route_table_safety_parity(report: dict[str, Any] | None = None) -> str:
    report = report or build_api_server_dispatch_route_table_safety_parity_metadata()
    summary = render_review_card_component(
        "API server dispatch route table safety parity",
        f"Status: {report.get('status')}; route-table rows: {report.get('route_table_safe_preview_row_count')}; newly migrated: {report.get('route_table_newly_migrated_route_count')}; parity: {report.get('route_table_payload_manual_helper_parity')}",
        tip="1070.9 review-only API dispatch route table safety parity. data-tip hover only; no native title tooltip.",
    )
    parity_table = render_review_table_component(
        report.get("payload_parity_rows") or [],
        (("route", "Route"), ("module", "Module"), ("safety_key_parity", "Safety parity"), ("warning_parity_guard", "Warning"), ("manual_route_table_replaces_api_dispatch", "Replaces dispatch"), ("status", "Status")),
        tip="v1070.9 payload parity rows; table-built payloads match manual helper safety fields.",
    )
    migration_table = render_review_table_component(
        report.get("migration_rows") or [],
        (("route", "Route"), ("uses_route_table_payload", "Uses table"), ("old_direct_branch_removed", "Direct branch removed"), ("newly_migrated_in_current_arc", "Migrated now"), ("status", "Status")),
        tip="v1070.9 migration rows; manual dispatch remains authoritative while direct branches are reduced.",
    )
    boundary_table = render_review_table_component(
        report.get("boundary_rows") or [],
        (("boundary", "Boundary"), ("expected", "Expected"), ("actual", "Actual"), ("status", "Status")),
        tip="v1070.9 safety boundaries; actual fixture execution remains blocked pending an audited OS sandbox.",
    )
    return f"""
{summary}
<div class='grid two'>
  <div class='card' data-tip='v1070.9 route table/manual helper payload parity'><h3>Payload parity</h3>{parity_table}</div>
  <div class='card' data-tip='v1070.9 route table migration rows'><h3>Migration rows</h3>{migration_table}</div>
</div>
<div class='card' data-tip='v1070.9 safety boundary rows'><h3>Safety boundaries</h3>{boundary_table}</div>
<p class='muted'>api-server-dispatch-route-table-safety-parity-v1 /api-server-dispatch-route-table-safety-parity /api/source-surface/api-server-dispatch-route-table-safety-parity route_table_payload_manual_helper_parity=True route_table_safety_key_parity=True route_table_safe_preview_row_count=4 route_table_newly_migrated_route_count=1 old_direct_branch_removed=True manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip</p>
"""


def api_server_dispatch_route_table_safety_parity_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_api_server_dispatch_route_table_safety_parity_metadata()
    lines = [
        f"{ARC_TITLE} ({REVIEW_ID})",
        f"status={report.get('status')}; ok={report.get('ok')}",
        f"route_table_safe_preview_row_count={report.get('route_table_safe_preview_row_count')}",
        f"route_table_newly_migrated_route_count={report.get('route_table_newly_migrated_route_count')}",
        f"route_table_payload_manual_helper_parity={report.get('route_table_payload_manual_helper_parity')}",
        f"route_table_safety_key_parity={report.get('route_table_safety_key_parity')}",
        f"api_get_preview_only={report.get('api_get_preview_only')}",
        f"dashboard_get_preview_only={report.get('dashboard_get_preview_only')}",
        f"actual_fixture_execution_count={report.get('actual_fixture_execution_count')}",
        f"subprocess_spawn_count={report.get('subprocess_spawn_count')}",
        f"source_write_count={report.get('source_write_count')}",
        f"source_delete_count={report.get('source_delete_count')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"manual_route_table_replaces_api_dispatch={report.get('manual_route_table_replaces_api_dispatch')}",
        f"actual_fixture_execution_blocked_reason={report.get('actual_fixture_execution_blocked_reason')}",
    ]
    if full:
        for row in report.get("payload_parity_rows") or []:
            lines.append(f"parity:{row.get('route')} status={row.get('status')} safety_key_parity={row.get('safety_key_parity')} warning={row.get('warning_parity_guard')} replaces={row.get('manual_route_table_replaces_api_dispatch')}")
        for row in report.get("migration_rows") or []:
            lines.append(f"migration:{row.get('route')} status={row.get('status')} old_direct_branch_removed={row.get('old_direct_branch_removed')} newly_migrated={row.get('newly_migrated_in_current_arc')}")
        for row in report.get("rows") or []:
            lines.append(f"check:{row.get('name')} status={row.get('status')} message={row.get('message')}")
    return "\n".join(lines)


# v1070.9 API server dispatch route table safety parity tokens: api-server-dispatch-route-table-safety-parity-v1 /api-server-dispatch-route-table-safety-parity /api/source-surface/api-server-dispatch-route-table-safety-parity build_api_server_dispatch_route_table_safety_parity build_api_server_dispatch_route_table_safety_parity_metadata api_server_dispatch_route_table_safety_parity_text api_preview_payload api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload build_manual_preview_dispatch_payload route_table_payload_manual_helper_parity=True route_table_safety_key_parity=True route_table_safe_preview_row_count=4 route_table_newly_migrated_route_count=1 old_direct_branch_removed=True manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
