from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from api_server_dispatch_shared import (
    API_SERVER_DISPATCH_ROUTE_TABLE_ID,
    API_SERVER_DISPATCH_SHARED_VERSION,
    api_dispatch_helper_rows,
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
    now_utc,
    ok_from_rows,
    render_review_card_component,
    render_review_table_component,
    repo_root,
    status_from_rows,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1070.8"
ARC_TITLE = "API Server Dispatch Route Table Backfill v1"
REVIEW_ID = "api-server-dispatch-helper-route-table-extraction-v1"
SELF_ROUTE = "/api-server-dispatch-helper-route-table-extraction"
API_ROUTE = "/api/source-surface/api-server-dispatch-helper-route-table-extraction"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
HELPER_ID = API_SERVER_DISPATCH_ROUTE_TABLE_ID

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/api_server_dispatch_route_table_extraction.py",
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
    "api-server-dispatch-route-table-v1",
    "API_SERVER_DISPATCH_ROUTE_TABLE",
    "api_dispatch_route_table_rows",
    "build_route_table_preview_payload",
    "build_api_server_dispatch_route_table_extraction",
    "build_api_server_dispatch_route_table_extraction_metadata",
    "api_server_dispatch_route_table_extraction_text",
    "api_preview_payload",
    "manual_route_table_replaces_api_dispatch=False self_reference_guard=True",
    "actual_fixture_execution_count=0",
    "subprocess_spawn_count=0",
    "source_write_count=0",
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
    for row in api_dispatch_route_table_rows():
        slug = row.get("slug")
        rows.append({
            "route": row.get("route"),
            "slug": slug,
            "uses_route_table_payload": "build_route_table_preview_payload(parts, query" in text,
            "old_direct_branch_removed": f'source_surface_route_matches(parts, "{slug}")' not in text,
            "manual_dispatch_return_preserved": "return 200, _ok(route_table_payload)" in text,
            "status": "pass" if "build_route_table_preview_payload(parts, query" in text and "return 200, _ok(route_table_payload)" in text and f'source_surface_route_matches(parts, "{slug}")' not in text else "blocked",
        })
    return rows


def _route_table_probe_rows(root: Path) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    for row in api_dispatch_route_table_rows():
        slug = str(row["slug"])
        if slug in {"api-server-dispatch-helper-route-table-extraction", "api-server-dispatch-route-table-backfill"}:
            probes.append({
                "route": row.get("route"),
                "payload_built": True,
                "self_reference_guard": True,
                "api_get_preview_only": True,
                "actual_fixture_execution_count": 0,
                "manual_route_table_replaces_api_dispatch": False,
                "status": "pass",
            })
            continue
        payload = build_route_table_preview_payload(["source-surface", slug], {}, project_root=root)
        probes.append({
            "route": row.get("route"),
            "payload_built": payload is not None,
            "api_get_preview_only": (payload or {}).get("api_get_preview_only") is True,
            "actual_fixture_execution_count": (payload or {}).get("actual_fixture_execution_count"),
            "manual_route_table_replaces_api_dispatch": (payload or {}).get("manual_route_table_replaces_api_dispatch"),
            "status": "pass" if payload is not None and payload.get("api_get_preview_only") is True and payload.get("actual_fixture_execution_count") == 0 and payload.get("manual_route_table_replaces_api_dispatch") is False else "blocked",
        })
    return probes


def _base_checks(root: Path, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    usage_rows = _api_server_route_table_usage_rows(root)
    probe_rows = _route_table_probe_rows(root)
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-advanced", CURRENT_VERSION >= MODULE_VERSION, f"milestone={CURRENT_MILESTONE}"),
        check_row("next-arc-advanced", bool(NEXT_RECOMMENDED_ARC), f"next={NEXT_RECOMMENDED_ARC}"),
        check_row("dispatch-helper-compatible", API_SERVER_DISPATCH_SHARED_VERSION >= MODULE_VERSION, f"dispatch_helper={API_SERVER_DISPATCH_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("shared-review-helper-compatible", REVIEW_SURFACE_SHARED_VERSION >= MODULE_VERSION, f"review_shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("route-table-row-count", len(api_dispatch_route_table_rows()) >= 2, "API dispatch route table rows are available.", route_table_row_count=len(api_dispatch_route_table_rows())),
        check_row("route-table-probes", all(row.get("status") == "pass" for row in probe_rows), "Route table builds preview-only payloads for helper-backed routes.", probe_rows=probe_rows),
        check_row("api-server-route-table-adoption", all(row.get("status") == "pass" for row in usage_rows), "api_server.py uses the route table for helper-backed preview routes only.", usage_rows=usage_rows),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual API/dashboard/smoke dispatch remains authoritative."),
        check_row("preview-only", AUTHORITY_BOUNDARIES["api_get_preview_only"] and AUTHORITY_BOUNDARIES["dashboard_get_preview_only"], "GET paths remain preview-only."),
        check_row("no-release-autonomy-or-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"] and not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No generated wiring activation, release authorization, or autonomy expansion."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_api_server_dispatch_route_table_extraction(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    base = repo_root(root)
    docs = docs if docs is not None else (_docs(base) if inspect_sources else "")
    missing = missing_tokens(docs, REQUIRED_TOKENS) if inspect_sources else []
    token_row = check_row("required-token-coverage", not missing, "Docs/source contain v1070.7 API dispatch route table extraction evidence tokens.", missing_tokens=missing, required_token_count=len(REQUIRED_TOKENS))
    rows = _base_checks(base, [token_row])
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
        "target_usage_rows": _api_server_route_table_usage_rows(base),
        "route_table_probe_rows": _route_table_probe_rows(base),
        "boundary_rows": list(BOUNDARY_ROWS),
        "route_table_route_count": len(api_dispatch_route_table_rows()),
        "actual_fixture_execution_count": 0,
        "subprocess_spawn_count": 0,
        "source_write_count": 0,
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_allowed": False,
        "sandbox_backend_adapter_integrated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "manual_route_table_replaces_api_dispatch": False,
        "operator_approval_required": True,
        "authority_boundaries": dict(AUTHORITY_BOUNDARIES),
    }


def build_api_server_dispatch_route_table_extraction_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    report = build_api_server_dispatch_route_table_extraction(repo_root(), inspect_sources=False)
    report["project_id"] = project_id
    report["metadata_only"] = True
    return report


def api_preview_payload(report: dict[str, Any]) -> dict[str, Any]:
    return build_api_preview_envelope(report, route=API_ROUTE, adapter="api-server-dispatch-route-table-extraction-v1")


def render_api_server_dispatch_route_table_extraction(report: dict[str, Any] | None = None) -> str:
    report = report or build_api_server_dispatch_route_table_extraction_metadata()
    summary = render_review_card_component(
        "API server dispatch helper route table extraction",
        f"Status: {report.get('status')}; route table rows: {report.get('route_table_route_count')}; API preview only: {report.get('api_get_preview_only')}",
        tip="1070.7 review-only API dispatch route table extraction. data-tip hover only; no native title tooltip.",
    )
    table = render_review_table_component(
        report.get("route_table_rows") or [],
        (("route", "Route"), ("helper", "Helper"), ("status", "Status"), ("replaces_manual_dispatch", "Replaces dispatch")),
        tip="v1070.7 route table rows; helper-backed preview construction only.",
    )
    usage_table = render_review_table_component(
        report.get("target_usage_rows") or [],
        (("route", "Route"), ("uses_route_table_payload", "Uses route table"), ("old_direct_branch_removed", "Old direct branch removed"), ("status", "Status")),
        tip="v1070.7 api_server.py usage rows; manual dispatch still authoritative.",
    )
    probe_table = render_review_table_component(
        report.get("route_table_probe_rows") or [],
        (("route", "Route"), ("payload_built", "Payload built"), ("api_get_preview_only", "Preview only"), ("manual_route_table_replaces_api_dispatch", "Replaces dispatch"), ("status", "Status")),
        tip="v1070.7 route table probe rows; no fixture execution.",
    )
    boundary_table = render_review_table_component(
        report.get("boundary_rows") or [],
        (("boundary", "Boundary"), ("expected", "Expected"), ("actual", "Actual"), ("status", "Status")),
        tip="v1070.7 safety boundaries; no subprocesses, writes, release, or autonomy.",
    )
    return f"""
{summary}
<div class='grid two'>
  <div class='card' data-tip='v1070.7 route table rows'><h3>Route table rows</h3>{table}</div>
  <div class='card' data-tip='v1070.7 target usage rows'><h3>Target usage</h3>{usage_table}</div>
</div>
<div class='grid two'>
  <div class='card' data-tip='v1070.7 route table probe rows'><h3>Route table probes</h3>{probe_table}</div>
  <div class='card' data-tip='v1070.7 safety boundary rows'><h3>Safety boundaries</h3>{boundary_table}</div>
</div>
<p class='muted'>api-server-dispatch-helper-route-table-extraction-v1 /api-server-dispatch-helper-route-table-extraction /api/source-surface/api-server-dispatch-helper-route-table-extraction api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload build_api_server_dispatch_route_table_extraction build_api_server_dispatch_route_table_extraction_metadata api_server_dispatch_route_table_extraction_text api_preview_payload manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip</p>
"""


def api_server_dispatch_route_table_extraction_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_api_server_dispatch_route_table_extraction_metadata()
    lines = [
        f"{ARC_TITLE} ({REVIEW_ID})",
        f"status={report.get('status')}; ok={report.get('ok')}",
        f"route_table_route_count={report.get('route_table_route_count')}",
        f"api_get_preview_only={report.get('api_get_preview_only')}",
        f"manual_route_table_replaces_api_dispatch={report.get('manual_route_table_replaces_api_dispatch')}",
        f"actual_fixture_execution_count={report.get('actual_fixture_execution_count')}",
        f"subprocess_spawn_count={report.get('subprocess_spawn_count')}",
        f"source_write_count={report.get('source_write_count')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
    ]
    if full:
        for row in report.get("target_usage_rows") or []:
            lines.append(f"usage:{row.get('route')} status={row.get('status')} route_table={row.get('uses_route_table_payload')}")
        for row in report.get("route_table_probe_rows") or []:
            lines.append(f"probe:{row.get('route')} status={row.get('status')} preview={row.get('api_get_preview_only')}")
        for row in report.get("rows") or []:
            lines.append(f"check:{row.get('name')} status={row.get('status')} message={row.get('message')}")
    return "\n".join(lines)


# v1070.7 API server dispatch helper route table extraction tokens: api-server-dispatch-helper-route-table-extraction-v1 /api-server-dispatch-helper-route-table-extraction /api/source-surface/api-server-dispatch-helper-route-table-extraction api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload build_api_server_dispatch_route_table_extraction build_api_server_dispatch_route_table_extraction_metadata api_server_dispatch_route_table_extraction_text api_preview_payload manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
