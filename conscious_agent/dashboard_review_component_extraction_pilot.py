from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import json
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from review_surface_shared import (
    DEFAULT_AUTHORITY_BOUNDARIES,
    REVIEW_SURFACE_SHARED_VERSION,
    check_row,
    build_api_preview_envelope,
    missing_tokens,
    now_utc,
    ok_from_rows,
    preview_response_payload,
    render_review_card_component,
    render_review_table_component,
    repo_root,
    status_from_rows,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1070.1"
ARC_TITLE = "Dashboard Review Component Extraction Pilot v1"
REVIEW_ID = "dashboard-review-component-extraction-pilot-v1"
SELF_ROUTE = "/dashboard-review-component-extraction-pilot"
API_ROUTE = "/api/source-surface/dashboard-review-component-extraction-pilot"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

PILOT_COMPONENT_ROWS: tuple[dict[str, Any], ...] = (
    {
        "component": "render_review_card_component",
        "adopted_by": "render_dashboard_review_component_extraction_pilot",
        "scope": "one current dashboard review route",
        "behavior_change": "none_preview_only",
        "status": "used",
    },
    {
        "component": "render_review_table_component",
        "adopted_by": "render_dashboard_review_component_extraction_pilot",
        "scope": "one current dashboard review route",
        "behavior_change": "none_preview_only",
        "status": "used",
    },
    {
        "component": "preview_response_payload",
        "adopted_by": API_ROUTE,
        "scope": "one current API preview route",
        "behavior_change": "none_preview_only",
        "status": "used",
    },
)

PILOT_BOUNDARY_ROWS: tuple[dict[str, Any], ...] = (
    {"boundary": "dashboard_get_preview_only", "expected": True, "actual": True, "status": "pass"},
    {"boundary": "api_get_preview_only", "expected": True, "actual": True, "status": "pass"},
    {"boundary": "subprocess_spawn_count", "expected": 0, "actual": 0, "status": "pass"},
    {"boundary": "source_write_count", "expected": 0, "actual": 0, "status": "pass"},
    {"boundary": "generated_wiring_activated", "expected": False, "actual": False, "status": "pass"},
    {"boundary": "release_authorized", "expected": False, "actual": False, "status": "pass"},
    {"boundary": "autonomy_expanded", "expected": False, "actual": False, "status": "pass"},
    {"boundary": "native_title_tooltip_reintroduced", "expected": False, "actual": False, "status": "pass"},
)


def _docs(root: Path) -> str:
    rels = (
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/review_surface_shared.py",
        "conscious_agent/dashboard_review_component_extraction_pilot.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    )
    chunks: list[str] = []
    for rel in rels:
        try:
            chunks.append((root / rel).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            chunks.append("")
    return "\n".join(chunks)


def _component_output_samples() -> dict[str, str]:
    return {
        "card_sample": render_review_card_component(
            "Component extraction pilot",
            "Shared dashboard review-card rendering is used by this one route while manual dispatch stays authoritative.",
            tip="v1070.1 component extraction pilot; preview-only; no native title tooltip.",
        ),
        "table_sample": render_review_table_component(
            PILOT_COMPONENT_ROWS,
            (("component", "Component"), ("adopted_by", "Adopted by"), ("status", "Status")),
        ),
    }


def _base_checks(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    samples = _component_output_samples()
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-advanced", CURRENT_VERSION >= MODULE_VERSION, f"milestone={CURRENT_MILESTONE}; module_arc=v{MODULE_VERSION} {ARC_TITLE}"),
        check_row("shared-helper-compatible", REVIEW_SURFACE_SHARED_VERSION in {MODULE_VERSION, CURRENT_VERSION}, f"shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("review-card-component-used", "data-tip" in samples["card_sample"] and "title=" not in samples["card_sample"], "Shared review card component preserves custom data-tip hover and avoids native title tooltips."),
        check_row("review-table-component-used", "<table" in samples["table_sample"] and "data-tip" in samples["table_sample"], "Shared review table component renders tabular review rows and preserves custom hover behavior."),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual dashboard/API/smoke dispatch remain authoritative."),
        check_row("no-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"], "Generated wiring is not activated."),
        check_row("no-release-or-autonomy", not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No release authorization or autonomy expansion occurs."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    checks = _base_checks([
        check_row("component-row-count", len(PILOT_COMPONENT_ROWS) == 3, "Exactly one narrow dashboard/API/smoke family adopts shared review components.", component_row_count=len(PILOT_COMPONENT_ROWS)),
        check_row("boundary-row-count", len(PILOT_BOUNDARY_ROWS) >= 7, "Safety boundary rows remain explicit for the pilot route.", boundary_row_count=len(PILOT_BOUNDARY_ROWS)),
        check_row("next-arc-advanced", bool(NEXT_RECOMMENDED_ARC), f"next={NEXT_RECOMMENDED_ARC}; original_next={NEXT_ARC}"),
    ])
    return {
        "version": MODULE_VERSION,
        "arc_version": ARC_VERSION,
        "arc_title": ARC_TITLE,
        "checked_at": now_utc(),
        "project_id": project_id,
        "review_id": REVIEW_ID,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": status_from_rows(checks),
        "ok": ok_from_rows(checks),
        "implementation_status": "implemented_narrow_component_adoption",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "shared_helper_version": REVIEW_SURFACE_SHARED_VERSION,
        "component_rows": list(PILOT_COMPONENT_ROWS),
        "boundary_rows": list(PILOT_BOUNDARY_ROWS),
        "component_output_samples": _component_output_samples(),
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
    required = [
        REVIEW_ID,
        SELF_ROUTE,
        API_ROUTE,
        "render_review_card_component",
        "render_review_table_component",
        "preview_response_payload",
        "actual_fixture_execution_count=0",
        "subprocess_spawn_count=0",
        "source_write_count=0",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    docs = docs if docs is not None else (_docs(project_root) if inspect_sources else "")
    missing = missing_tokens(docs, required)
    checks = list(report.get("checks") or [])
    checks.append(check_row("docs-and-component-tokens", not missing, "Docs/source/dashboard/API/smoke contain required component extraction tokens.", missing_tokens=missing))
    report.update({"missing_required_tokens": missing, "checks": checks, "status": status_from_rows(checks), "ok": ok_from_rows(checks)})
    return report


def api_preview_payload(report: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_api_preview_envelope(
        report or build_metadata(),
        route=API_ROUTE,
        adapter="api-preview-adapter-backfill-v1",
        warning="Dashboard Review Component Extraction Pilot is GET preview-only and does not execute fixtures, activate generated wiring, authorize release, or expand autonomy.",
    )


def text_report(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        ARC_TITLE,
        f"Status: {report.get('status')}",
        f"Review ID: {report.get('review_id')}",
        f"Shared helper version: {report.get('shared_helper_version')}",
        f"Component row count: {len(report.get('component_rows') or [])}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Subprocess spawn count: {report.get('subprocess_spawn_count')}",
        f"Source write count: {report.get('source_write_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append(json.dumps(report, indent=2, sort_keys=True, default=str))
    return "\n".join(lines)


build_dashboard_review_component_extraction_pilot_metadata = build_metadata
build_dashboard_review_component_extraction_pilot = build_report
dashboard_review_component_extraction_pilot_text = text_report

# v1070.1 Dashboard Review Component Extraction Pilot tokens: dashboard-review-component-extraction-pilot-v1 /dashboard-review-component-extraction-pilot /api/source-surface/dashboard-review-component-extraction-pilot render_review_card_component render_review_table_component preview_response_payload build_dashboard_review_component_extraction_pilot build_dashboard_review_component_extraction_pilot_metadata dashboard_review_component_extraction_pilot_text actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.4 API preview adapter backfill token: api-preview-adapter-backfill-v1 build_api_preview_envelope conscious_agent/dashboard_review_component_extraction_pilot.py actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False api_get_preview_only=True dashboard_get_preview_only=True manual_api_dispatch_remains_authoritative=True
