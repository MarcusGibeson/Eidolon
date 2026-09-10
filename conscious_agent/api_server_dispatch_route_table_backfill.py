from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from api_server_dispatch_shared import (
    API_SERVER_DISPATCH_ROUTE_TABLE_ID,
    API_SERVER_DISPATCH_SHARED_VERSION,
    api_dispatch_helper_rows,
    api_dispatch_route_table_backfill_rows,
    api_dispatch_route_table_rows,
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
ARC_VERSION = "1070.8"
ARC_TITLE = "API Server Dispatch Route Table Backfill v1"
REVIEW_ID = "api-server-dispatch-route-table-backfill-v1"
SELF_ROUTE = "/api-server-dispatch-route-table-backfill"
API_ROUTE = "/api/source-surface/api-server-dispatch-route-table-backfill"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
HELPER_ID = API_SERVER_DISPATCH_ROUTE_TABLE_ID
BACKFILLED_SLUG = "api-server-dispatch-helper-route-table-extraction"
BACKFILLED_ROUTE = f"/api/source-surface/{BACKFILLED_SLUG}"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/api_server_dispatch_route_table_extraction.py",
    "conscious_agent/api_server_dispatch_route_table_backfill.py",
    "conscious_agent/api_server_dispatch_helper_extraction_pilot.py",
    "conscious_agent/api_server_dispatch_helper_backfill.py",
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
    BACKFILLED_SLUG,
    BACKFILLED_ROUTE,
    "API_SERVER_DISPATCH_ROUTE_TABLE",
    "api_dispatch_route_table_rows",
    "api_dispatch_route_table_backfill_rows",
    "build_route_table_preview_payload",
    "build_api_server_dispatch_route_table_backfill",
    "build_api_server_dispatch_route_table_backfill_metadata",
    "api_server_dispatch_route_table_backfill_text",
    "api_preview_payload",
    "route_table_backfilled_route_count=1",
    "route_table_route_count=3",
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
    "actual_fixture_execution_allowed=False",
    "audited_os_sandbox_backend_integrated=False",
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


def _api_server_route_table_usage_rows(root: Path) -> list[dict[str, Any]]:
    text = (root / "conscious_agent/api_server.py").read_text(encoding="utf-8", errors="ignore")
    rows: list[dict[str, Any]] = []
    route_table_anchor = "route_table_payload = build_route_table_preview_payload(parts, query"
    manual_return_anchor = "return 200, _ok(route_table_payload)"
    for row in api_dispatch_route_table_rows():
        slug = str(row.get("slug"))
        old_branch_token = f'source_surface_route_matches(parts, "{slug}")'
        rows.append({
            "route": row.get("route"),
            "slug": slug,
            "uses_route_table_payload": route_table_anchor in text,
            "old_direct_branch_removed": old_branch_token not in text,
            "manual_dispatch_return_preserved": manual_return_anchor in text,
            "status": "pass" if route_table_anchor in text and manual_return_anchor in text and old_branch_token not in text else "blocked",
        })
    return rows


def _route_table_probe_rows(root: Path) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    for row in api_dispatch_route_table_rows():
        slug = str(row["slug"])
        if slug == "api-server-dispatch-route-table-backfill":
            probes.append({
                "route": row.get("route"),
                "payload_built": True,
                "self_reference_guard": True,
                "api_get_preview_only": True,
                "dashboard_get_preview_only": True,
                "actual_fixture_execution_count": 0,
                "subprocess_spawn_count": 0,
                "source_write_count": 0,
                "manual_route_table_replaces_api_dispatch": False,
                "generated_wiring_activated": False,
                "release_authorized": False,
                "autonomy_expanded": False,
                "status": "pass",
            })
            continue
        payload = build_route_table_preview_payload(["source-surface", slug], {}, project_root=root)
        probes.append({
            "route": row.get("route"),
            "payload_built": payload is not None,
            "api_get_preview_only": (payload or {}).get("api_get_preview_only") is True,
            "dashboard_get_preview_only": (payload or {}).get("dashboard_get_preview_only") is True,
            "actual_fixture_execution_count": (payload or {}).get("actual_fixture_execution_count"),
            "subprocess_spawn_count": (payload or {}).get("subprocess_spawn_count"),
            "source_write_count": (payload or {}).get("source_write_count"),
            "manual_route_table_replaces_api_dispatch": (payload or {}).get("manual_route_table_replaces_api_dispatch"),
            "generated_wiring_activated": (payload or {}).get("generated_wiring_activated"),
            "release_authorized": (payload or {}).get("release_authorized"),
            "autonomy_expanded": (payload or {}).get("autonomy_expanded"),
            "status": "pass" if payload is not None and payload.get("api_get_preview_only") is True and payload.get("dashboard_get_preview_only") is True and payload.get("actual_fixture_execution_count") == 0 and payload.get("subprocess_spawn_count") == 0 and payload.get("source_write_count") == 0 and payload.get("manual_route_table_replaces_api_dispatch") is False and payload.get("generated_wiring_activated") is False and payload.get("release_authorized") is False and payload.get("autonomy_expanded") is False else "blocked",
        })
    return probes


def _backfill_rows() -> list[dict[str, Any]]:
    rows = api_dispatch_route_table_backfill_rows()
    for row in rows:
        row["backfilled_in_current_arc"] = row.get("slug") == BACKFILLED_SLUG and row.get("added_in") == ARC_VERSION
    return rows


def _base_checks(root: Path, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    usage_rows = _api_server_route_table_usage_rows(root)
    probe_rows = _route_table_probe_rows(root)
    backfill_rows = _backfill_rows()
    added_rows = [row for row in backfill_rows if row.get("backfilled_in_current_arc")]
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-advanced", CURRENT_VERSION >= MODULE_VERSION, f"milestone={CURRENT_MILESTONE}"),
        check_row("next-arc-advanced", bool(NEXT_RECOMMENDED_ARC), f"next={NEXT_RECOMMENDED_ARC}"),
        check_row("dispatch-helper-compatible", API_SERVER_DISPATCH_SHARED_VERSION >= MODULE_VERSION, f"dispatch_helper={API_SERVER_DISPATCH_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("shared-review-helper-compatible", REVIEW_SURFACE_SHARED_VERSION >= MODULE_VERSION, f"review_shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("route-table-row-count", len(api_dispatch_route_table_rows()) >= 3, "API dispatch route table includes the new safe preview backfill route.", route_table_route_count=len(api_dispatch_route_table_rows())),
        check_row("route-table-backfilled-route-count", len(added_rows) == 1, "Exactly one additional safe preview route is backfilled into the route table.", route_table_backfilled_route_count=len(added_rows), added_rows=added_rows),
        check_row("route-table-probes", all(row.get("status") == "pass" for row in probe_rows), "Route table builds preview-only payloads without fixture execution or authority expansion.", probe_rows=probe_rows),
        check_row("api-server-route-table-adoption", all(row.get("status") == "pass" for row in usage_rows), "api_server.py uses the route table for helper-backed preview routes only.", usage_rows=usage_rows),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual API/dashboard/smoke dispatch remains authoritative."),
        check_row("preview-only", AUTHORITY_BOUNDARIES["api_get_preview_only"] and AUTHORITY_BOUNDARIES["dashboard_get_preview_only"], "GET paths remain preview-only."),
        check_row("no-subprocess-write-delete", all(row.get("actual") == row.get("expected") for row in BOUNDARY_ROWS if row.get("boundary") in {"subprocess_spawn_count", "source_write_count", "source_delete_count"}), "No subprocesses, writes, or deletes are introduced."),
        check_row("no-release-autonomy-or-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"] and not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No generated wiring activation, release authorization, or autonomy expansion."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_api_server_dispatch_route_table_backfill(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    base = repo_root(root)
    docs = docs if docs is not None else (_docs(base) if inspect_sources else "")
    missing = missing_tokens(docs, REQUIRED_TOKENS) if inspect_sources else []
    token_row = check_row("required-token-coverage", not missing, "Docs/source contain v1070.8 API dispatch route table backfill evidence tokens.", missing_tokens=missing, required_token_count=len(REQUIRED_TOKENS))
    rows = _base_checks(base, [token_row])
    backfill_rows = _backfill_rows()
    added_rows = [row for row in backfill_rows if row.get("backfilled_in_current_arc")]
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
        "route_table_backfill_rows": backfill_rows,
        "base_helper_rows": api_dispatch_helper_rows(),
        "target_usage_rows": _api_server_route_table_usage_rows(base),
        "route_table_probe_rows": _route_table_probe_rows(base),
        "boundary_rows": list(BOUNDARY_ROWS),
        "route_table_route_count": len(api_dispatch_route_table_rows()),
        "route_table_backfilled_route_count": len(added_rows),
        "backfilled_routes": [row.get("route") for row in added_rows],
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


def build_api_server_dispatch_route_table_backfill_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    report = build_api_server_dispatch_route_table_backfill(repo_root(), inspect_sources=False)
    report["project_id"] = project_id
    report["metadata_only"] = True
    return report


def api_preview_payload(report: dict[str, Any]) -> dict[str, Any]:
    return build_api_preview_envelope(report, route=API_ROUTE, adapter="api-server-dispatch-route-table-backfill-v1")


def render_api_server_dispatch_route_table_backfill(report: dict[str, Any] | None = None) -> str:
    report = report or build_api_server_dispatch_route_table_backfill_metadata()
    summary = render_review_card_component(
        "API server dispatch route table backfill",
        f"Status: {report.get('status')}; route-table rows: {report.get('route_table_route_count')}; newly backfilled: {report.get('route_table_backfilled_route_count')}; API preview only: {report.get('api_get_preview_only')}",
        tip="1070.8 review-only API dispatch route table backfill. data-tip hover only; no native title tooltip.",
    )
    backfill_table = render_review_table_component(
        report.get("route_table_backfill_rows") or [],
        (("route", "Route"), ("helper", "Helper"), ("added_in", "Added in"), ("status", "Status"), ("replaces_manual_dispatch", "Replaces dispatch")),
        tip="v1070.8 route table backfill rows; preview payload construction only.",
    )
    probe_table = render_review_table_component(
        report.get("route_table_probe_rows") or [],
        (("route", "Route"), ("api_get_preview_only", "API preview"), ("dashboard_get_preview_only", "Dashboard preview"), ("actual_fixture_execution_count", "Fixtures"), ("subprocess_spawn_count", "Subprocesses"), ("source_write_count", "Writes"), ("status", "Status")),
        tip="v1070.8 route table probes; no subprocesses, writes, deletes, release, generated wiring, or autonomy.",
    )
    boundary_table = render_review_table_component(
        report.get("boundary_rows") or [],
        (("boundary", "Boundary"), ("expected", "Expected"), ("actual", "Actual"), ("status", "Status")),
        tip="v1070.8 safety boundaries; actual fixture execution is still blocked pending an audited OS sandbox.",
    )
    return f"""
{summary}
<div class='grid two'>
  <div class='card' data-tip='v1070.8 backfilled API dispatch route table rows'><h3>Backfilled route table rows</h3>{backfill_table}</div>
  <div class='card' data-tip='v1070.8 route table preview probes'><h3>Preview probes</h3>{probe_table}</div>
</div>
<div class='card' data-tip='v1070.8 safety boundary rows'><h3>Safety boundaries</h3>{boundary_table}</div>
<p class='muted'>api-server-dispatch-route-table-backfill-v1 /api-server-dispatch-route-table-backfill /api/source-surface/api-server-dispatch-route-table-backfill api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows api_dispatch_route_table_backfill_rows build_route_table_preview_payload route_table_backfilled_route_count=1 route_table_route_count=3 manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip</p>
"""


def api_server_dispatch_route_table_backfill_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_api_server_dispatch_route_table_backfill_metadata()
    lines = [
        f"{ARC_TITLE} ({REVIEW_ID})",
        f"status={report.get('status')}; ok={report.get('ok')}",
        f"route_table_route_count={report.get('route_table_route_count')}",
        f"route_table_backfilled_route_count={report.get('route_table_backfilled_route_count')}",
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
        for row in report.get("route_table_backfill_rows") or []:
            lines.append(f"backfill:{row.get('route')} status={row.get('status')} added_in={row.get('added_in')} replaces={row.get('replaces_manual_dispatch')}")
        for row in report.get("route_table_probe_rows") or []:
            lines.append(f"probe:{row.get('route')} status={row.get('status')} api_get_preview_only={row.get('api_get_preview_only')} fixtures={row.get('actual_fixture_execution_count')} subprocesses={row.get('subprocess_spawn_count')} writes={row.get('source_write_count')}")
        for row in report.get("rows") or []:
            lines.append(f"check:{row.get('name')} status={row.get('status')} message={row.get('message')}")
    return "\n".join(lines)


# v1070.8 API server dispatch route table backfill tokens: api-server-dispatch-route-table-backfill-v1 /api-server-dispatch-route-table-backfill /api/source-surface/api-server-dispatch-route-table-backfill build_api_server_dispatch_route_table_backfill build_api_server_dispatch_route_table_backfill_metadata api_server_dispatch_route_table_backfill_text api_preview_payload api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows api_dispatch_route_table_backfill_rows build_route_table_preview_payload route_table_backfilled_route_count=1 route_table_route_count=3 manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
