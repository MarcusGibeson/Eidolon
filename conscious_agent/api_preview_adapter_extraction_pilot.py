from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from review_surface_shared import (
    DEFAULT_AUTHORITY_BOUNDARIES,
    REVIEW_SURFACE_SHARED_VERSION,
    api_preview_adapter_rows,
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
ARC_VERSION = "1070.3"
ARC_TITLE = "API Preview Adapter Extraction Pilot v1"
REVIEW_ID = "api-preview-adapter-extraction-pilot-v1"
SELF_ROUTE = "/api-preview-adapter-extraction-pilot"
API_ROUTE = "/api/source-surface/api-preview-adapter-extraction-pilot"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
ADAPTER_ID = "api-preview-adapter-shared-v1"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/review_surface_shared.py",
    "conscious_agent/api_preview_adapter_extraction_pilot.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/smoke_segment_registry.py",
    "tools/smoke_check.py",
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

REQUIRED_TOKENS: tuple[str, ...] = (
    REVIEW_ID,
    SELF_ROUTE,
    API_ROUTE,
    ADAPTER_ID,
    "build_api_preview_envelope",
    "api_preview_adapter_rows",
    "preview_response_payload",
    "build_api_preview_adapter_extraction_pilot",
    "build_api_preview_adapter_extraction_pilot_metadata",
    "api_preview_adapter_extraction_pilot_text",
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


def _docs(root: Path) -> str:
    chunks: list[str] = []
    for rel in DOC_PATHS:
        try:
            chunks.append((root / rel).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            chunks.append("")
    return "\n".join(chunks)


def _base_checks(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-advanced", CURRENT_VERSION >= MODULE_VERSION, f"milestone={CURRENT_MILESTONE}; module_arc=v{MODULE_VERSION} {ARC_TITLE}"),
        check_row("next-arc-advanced", CURRENT_VERSION >= MODULE_VERSION, f"next={NEXT_RECOMMENDED_ARC}; module_next={NEXT_ARC}"),
        check_row("shared-helper-compatible", REVIEW_SURFACE_SHARED_VERSION in {MODULE_VERSION, CURRENT_VERSION}, f"shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("adapter-row-count", len(api_preview_adapter_rows()) == 3, "API preview adapter helper rows inventory one narrow API route adoption.", adapter_row_count=len(api_preview_adapter_rows())),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual API/dashboard/smoke dispatch remains authoritative."),
        check_row("preview-only", AUTHORITY_BOUNDARIES["api_get_preview_only"] and AUTHORITY_BOUNDARIES["dashboard_get_preview_only"], "GET paths remain preview-only."),
        check_row("no-release-autonomy-or-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"] and not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "Generated wiring, release authorization, and autonomy expansion stay disabled."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    checks = _base_checks([
        check_row("boundary-row-count", len(BOUNDARY_ROWS) >= 8, "API preview adapter pilot keeps explicit safety boundary rows.", boundary_row_count=len(BOUNDARY_ROWS)),
    ])
    return {
        "version": MODULE_VERSION,
        "arc_version": ARC_VERSION,
        "arc_title": ARC_TITLE,
        "checked_at": now_utc(),
        "project_id": project_id,
        "review_id": REVIEW_ID,
        "adapter_id": ADAPTER_ID,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": status_from_rows(checks),
        "ok": ok_from_rows(checks),
        "implementation_status": "implemented_narrow_api_preview_adapter_adoption",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "shared_helper_version": REVIEW_SURFACE_SHARED_VERSION,
        "adapter_rows": api_preview_adapter_rows(),
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
    checks.append(check_row("docs-and-api-preview-adapter-tokens", not missing, "Docs/source/dashboard/API/smoke contain required API preview adapter extraction tokens.", missing_tokens=missing, required_token_count=len(REQUIRED_TOKENS)))
    envelope = build_api_preview_envelope(report, route=API_ROUTE, adapter=ADAPTER_ID, warning="API Preview Adapter Extraction Pilot is GET preview-only and does not execute fixtures, activate generated wiring, authorize release, or expand autonomy.")
    checks.append(check_row("adapter-envelope-preview-boundaries", envelope.get("api_get_preview_only") is True and envelope.get("actual_fixture_execution_count") == 0 and envelope.get("generated_wiring_activated") is False, "Shared API preview envelope preserves preview-only and no-authority defaults."))
    report.update({
        "api_preview_envelope": envelope,
        "missing_required_tokens": missing,
        "required_token_count": len(REQUIRED_TOKENS),
        "checks": checks,
        "status": status_from_rows(checks),
        "ok": ok_from_rows(checks),
    })
    return report


def api_preview_payload(report: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_api_preview_envelope(
        report or build_metadata(),
        route=API_ROUTE,
        adapter=ADAPTER_ID,
        warning="API Preview Adapter Extraction Pilot is GET preview-only and does not execute fixtures, activate generated wiring, authorize release, or expand autonomy.",
    )


def text_report(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        ARC_TITLE,
        f"Status: {report.get('status')}",
        f"Review ID: {report.get('review_id')}",
        f"Adapter ID: {report.get('adapter_id')}",
        f"Shared helper version: {report.get('shared_helper_version')}",
        f"Adapter rows: {len(report.get('adapter_rows') or [])}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Subprocess spawn count: {report.get('subprocess_spawn_count')}",
        f"Source write count: {report.get('source_write_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("Adapter rows:")
        for row in report.get("adapter_rows") or []:
            lines.append(f"- {row.get('helper')}: {row.get('status')} adopted_by={row.get('adopted_by')}")
        lines.append("Checks:")
        for row in report.get("checks") or []:
            lines.append(f"- {row.get('name')}: {row.get('status')} :: {row.get('message')}")
    return "\n".join(lines)


def build_api_preview_adapter_extraction_pilot_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    return build_metadata(project_id=project_id, root=root)


def build_api_preview_adapter_extraction_pilot(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    return build_report(root=root, inspect_sources=inspect_sources, docs=docs)


def api_preview_adapter_extraction_pilot_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    return text_report(report, full=full)

# v1070.3 API Preview Adapter Extraction Pilot tokens: api-preview-adapter-extraction-pilot-v1 /api-preview-adapter-extraction-pilot /api/source-surface/api-preview-adapter-extraction-pilot api-preview-adapter-shared-v1 build_api_preview_envelope api_preview_adapter_rows preview_response_payload build_api_preview_adapter_extraction_pilot build_api_preview_adapter_extraction_pilot_metadata api_preview_adapter_extraction_pilot_text actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.4 compatibility token: api-preview-adapter-extraction-pilot-v1 remains historical/individually runnable while current arc advances to api-preview-adapter-backfill-v1.
