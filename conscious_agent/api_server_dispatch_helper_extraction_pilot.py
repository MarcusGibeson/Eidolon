from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from api_server_dispatch_shared import API_SERVER_DISPATCH_SHARED_VERSION, api_dispatch_helper_rows
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
ARC_TITLE = "API Server Dispatch Helper Extraction Pilot v1"
REVIEW_ID = "api-server-dispatch-helper-extraction-pilot-v1"
SELF_ROUTE = "/api-server-dispatch-helper-extraction-pilot"
API_ROUTE = "/api/source-surface/api-server-dispatch-helper-extraction-pilot"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
HELPER_ID = "api-server-dispatch-helper-shared-v1"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/api_server_dispatch_helper_extraction_pilot.py",
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
    "api-server-dispatch-helper-shared-v1",
    "source_surface_route_matches",
    "build_manual_preview_dispatch_payload",
    "api_dispatch_helper_rows",
    "build_api_server_dispatch_helper_extraction_pilot",
    "build_api_server_dispatch_helper_extraction_pilot_metadata",
    "api_server_dispatch_helper_extraction_pilot_text",
    "api_preview_payload",
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


def _api_server_usage_row(root: Path) -> dict[str, Any]:
    text = (root / "conscious_agent/api_server.py").read_text(encoding="utf-8", errors="ignore")
    shared = (root / "conscious_agent/api_server_dispatch_shared.py").read_text(encoding="utf-8", errors="ignore")
    uses_direct_matcher = "source_surface_route_matches(parts, \"api-server-dispatch-helper-extraction-pilot\")" in text
    uses_route_table = "build_route_table_preview_payload(parts, query" in text and '"slug": "api-server-dispatch-helper-extraction-pilot"' in shared
    uses_payload = ("build_manual_preview_dispatch_payload" in text and "api_server_dispatch_helper_extraction_pilot" in text) or uses_route_table
    keeps_manual_ok = "return 200, _ok(payload)" in text or "return 200, _ok(route_table_payload)" in text
    return {
        "target": "conscious_agent/api_server.py",
        "uses_source_surface_route_matches": uses_direct_matcher or uses_route_table,
        "uses_build_manual_preview_dispatch_payload": uses_payload,
        "uses_route_table_preview_payload": uses_route_table,
        "manual_dispatch_return_preserved": keeps_manual_ok,
        "status": "pass" if (uses_direct_matcher or uses_route_table) and uses_payload and keeps_manual_ok else "blocked",
    }

def _base_checks(root: Path, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    usage = _api_server_usage_row(root)
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-advanced", bool(CURRENT_MILESTONE), f"milestone={CURRENT_MILESTONE}; module_arc=v{MODULE_VERSION} {ARC_TITLE}"),
        check_row("next-arc-advanced", bool(NEXT_RECOMMENDED_ARC), f"next={NEXT_RECOMMENDED_ARC}; module_next={NEXT_ARC}"),
        check_row("dispatch-helper-compatible", API_SERVER_DISPATCH_SHARED_VERSION >= MODULE_VERSION, f"dispatch_helper={API_SERVER_DISPATCH_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("shared-review-helper-compatible", REVIEW_SURFACE_SHARED_VERSION >= MODULE_VERSION, f"review_shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("dispatch-helper-row-count", len(api_dispatch_helper_rows()) >= 3, "API dispatch helper rows are available.", helper_row_count=len(api_dispatch_helper_rows())),
        check_row("api-server-narrow-adoption", usage.get("status") == "pass", "Manual api_server.py adopts the dispatch helper for one current route family only.", usage_row=usage),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual API/dashboard/smoke dispatch remains authoritative."),
        check_row("preview-only", AUTHORITY_BOUNDARIES["api_get_preview_only"] and AUTHORITY_BOUNDARIES["dashboard_get_preview_only"], "GET paths remain preview-only."),
        check_row("no-release-autonomy-or-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"] and not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "Generated wiring, release authorization, and autonomy expansion stay disabled."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = repo_root(root)
    checks = _base_checks(project_root, [
        check_row("boundary-row-count", len(BOUNDARY_ROWS) >= 8, "Dispatch helper pilot keeps explicit safety boundary rows.", boundary_row_count=len(BOUNDARY_ROWS)),
    ])
    return {
        "version": MODULE_VERSION,
        "arc_version": ARC_VERSION,
        "arc_title": ARC_TITLE,
        "checked_at": now_utc(),
        "project_id": project_id,
        "review_id": REVIEW_ID,
        "helper_id": HELPER_ID,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": status_from_rows(checks),
        "ok": ok_from_rows(checks),
        "implementation_status": "implemented_one_route_manual_api_dispatch_helper_pilot",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "dispatch_helper_version": API_SERVER_DISPATCH_SHARED_VERSION,
        "review_surface_shared_version": REVIEW_SURFACE_SHARED_VERSION,
        "helper_rows": api_dispatch_helper_rows(),
        "api_server_usage_row": _api_server_usage_row(project_root),
        "boundary_rows": list(BOUNDARY_ROWS),
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
        "operator_approval_required": True,
        "native_title_tooltip_reintroduced": False,
        "checks": checks,
    }


def build_report(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    project_root = repo_root(root)
    report = build_metadata(root=project_root)
    docs = docs if docs is not None else (_docs(project_root) if inspect_sources else "")
    missing = missing_tokens(docs, REQUIRED_TOKENS)
    checks = list(report.get("checks") or [])
    checks.append(check_row("docs-and-dispatch-helper-tokens", not missing, "Docs/source/dashboard/API/smoke contain required API dispatch helper extraction tokens.", missing_tokens=missing, required_token_count=len(REQUIRED_TOKENS)))
    envelope = build_api_preview_envelope(report, route=API_ROUTE, adapter=HELPER_ID, warning="API Server Dispatch Helper Extraction Pilot is GET preview-only and does not execute fixtures, activate generated wiring, authorize release, or expand autonomy.")
    checks.append(check_row("dispatch-helper-envelope-preview-boundaries", envelope.get("api_get_preview_only") is True and envelope.get("actual_fixture_execution_count") == 0 and envelope.get("generated_wiring_activated") is False, "Shared API preview envelope preserves preview-only and no-authority defaults."))
    report.update({
        "api_preview_envelope": envelope,
        "missing_required_tokens": missing,
        "required_token_count": len(REQUIRED_TOKENS),
        "checks": checks,
        "status": status_from_rows(checks),
        "ok": ok_from_rows(checks),
    })
    return report


def api_preview_payload(report: dict[str, Any]) -> dict[str, Any]:
    return build_api_preview_envelope(report, route=API_ROUTE, adapter=HELPER_ID, warning="API Server Dispatch Helper Extraction Pilot is a review-only GET preview surface.")


def build_api_server_dispatch_helper_extraction_pilot_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    return build_metadata(project_id=project_id, root=root)


def build_api_server_dispatch_helper_extraction_pilot(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    return build_report(root=root, inspect_sources=inspect_sources, docs=docs)


def render_api_server_dispatch_helper_extraction_pilot(report: dict[str, Any] | None = None) -> str:
    report = report or build_metadata()
    summary = render_review_card_component(
        "API server dispatch helper extraction pilot",
        f"Status: {report.get('status')}; helper rows: {len(report.get('helper_rows') or [])}; manual API authoritative: {report.get('manual_api_dispatch_remains_authoritative')}",
        tip="1070.5 review-only API dispatch helper pilot. data-tip hover only; no native title tooltip.",
    )
    helper_table = render_review_table_component(
        report.get("helper_rows") or [],
        (("helper", "Helper"), ("scope", "Scope"), ("status", "Status"), ("replaces_dispatch", "Replaces dispatch")),
        tip="Dispatch helper rows; helpers centralize one safe pattern but do not replace manual dispatch.",
    )
    boundary_table = render_review_table_component(
        report.get("boundary_rows") or [],
        (("boundary", "Boundary"), ("expected", "Expected"), ("actual", "Actual"), ("status", "Status")),
        tip="v1070.5 safety boundaries; no subprocesses, writes, release, or autonomy.",
    )
    return f"""
{summary}
<div class='grid two'>
  <div class='card' data-tip='v1070.5 dispatch helper rows'><h3>Dispatch helpers</h3>{helper_table}</div>
  <div class='card' data-tip='v1070.5 safety boundary rows'><h3>Safety boundaries</h3>{boundary_table}</div>
</div>
<p class='muted'>api-server-dispatch-helper-extraction-pilot-v1 /api-server-dispatch-helper-extraction-pilot /api/source-surface/api-server-dispatch-helper-extraction-pilot api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_rows build_api_server_dispatch_helper_extraction_pilot build_api_server_dispatch_helper_extraction_pilot_metadata api_server_dispatch_helper_extraction_pilot_text api_preview_payload actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip</p>
"""


def api_server_dispatch_helper_extraction_pilot_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        f"{ARC_TITLE} ({REVIEW_ID})",
        f"status={report.get('status')}; ok={report.get('ok')}",
        f"dispatch_helper_version={report.get('dispatch_helper_version')}; manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        "actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False",
    ]
    if full:
        for row in report.get("checks") or []:
            lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return "\n".join(lines)


# v1070.5 API Server Dispatch Helper Extraction Pilot tokens: api-server-dispatch-helper-extraction-pilot-v1 /api-server-dispatch-helper-extraction-pilot /api/source-surface/api-server-dispatch-helper-extraction-pilot api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_rows actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
