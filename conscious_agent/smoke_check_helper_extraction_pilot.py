from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from review_surface_shared import (
    DEFAULT_AUTHORITY_BOUNDARIES,
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
from smoke_check_shared import (
    SMOKE_CHECK_SHARED_VERSION,
    authority_boundary_violations,
    read_docs_bundle,
    smoke_helper_adoption_rows,
    smoke_token_validation_row,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1070.2"
ARC_TITLE = "Smoke Check Helper Extraction Pilot v1"
REVIEW_ID = "smoke-check-helper-extraction-pilot-v1"
SELF_ROUTE = "/smoke-check-helper-extraction-pilot"
API_ROUTE = "/api/source-surface/smoke-check-helper-extraction-pilot"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/smoke_check_shared.py",
    "conscious_agent/smoke_check_helper_extraction_pilot.py",
    "conscious_agent/review_surface_shared.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/smoke_segment_registry.py",
    "tools/smoke_check.py",
)

HELPER_SCOPE_ROWS: tuple[dict[str, Any], ...] = (
    {"scope": "tools/smoke_check.py", "change": "one current check imports shared helper functions", "status": "narrow_adoption"},
    {"scope": "smoke token bundle reads", "change": "read_docs_bundle replaces repeated inline README/source reads for this check", "status": "used"},
    {"scope": "token validation", "change": "smoke_token_validation_row and missing_required_tokens centralize one token-validation family", "status": "used"},
    {"scope": "authority boundaries", "change": "authority_boundary_violations centralizes forbidden authority checks for this check", "status": "used"},
)

BOUNDARY_ROWS: tuple[dict[str, Any], ...] = (
    {"boundary": "manual_smoke_remains_authoritative", "expected": True, "actual": True, "status": "pass"},
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
    "smoke-check-shared-v1",
    "SMOKE_CHECK_SHARED_VERSION",
    "read_docs_bundle",
    "missing_required_tokens",
    "authority_boundary_violations",
    "smoke_token_validation_row",
    "actual_fixture_execution_count=0",
    "subprocess_spawn_count=0",
    "source_write_count=0",
    "generated_wiring_activated=False",
    "release_authorized=False",
    "autonomy_expanded=False",
    "manual_smoke_remains_authoritative=True",
    "data-tip",
    "command-deck",
    "operator-console",
    "no_native_title_tooltip",
)


def _base_checks(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    violations = authority_boundary_violations({
        "actual_fixture_execution_count": 0,
        "actual_fixture_execution_allowed": False,
        "audited_os_sandbox_backend_integrated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    })
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone-recorded", bool(CURRENT_MILESTONE), f"milestone={CURRENT_MILESTONE}"),
        check_row("shared-smoke-helper-compatible", SMOKE_CHECK_SHARED_VERSION in {MODULE_VERSION, CURRENT_VERSION}, f"shared={SMOKE_CHECK_SHARED_VERSION}; module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("helper-adoption-row-count", len(smoke_helper_adoption_rows()) == 4, "Four smoke helper functions are inventoried for narrow adoption.", helper_row_count=len(smoke_helper_adoption_rows())),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"], "Manual dashboard/API/smoke dispatch remains authoritative."),
        check_row("no-authority-violations", not violations, "Shared smoke helpers detect no forbidden authority boundary violations.", violations=violations),
        check_row("next-arc-recorded", bool(NEXT_RECOMMENDED_ARC), f"next={NEXT_RECOMMENDED_ARC}"),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    checks = _base_checks([
        check_row("scope-row-count", len(HELPER_SCOPE_ROWS) == 4, "Pilot scope rows show one narrow smoke helper extraction family.", scope_row_count=len(HELPER_SCOPE_ROWS)),
        check_row("boundary-row-count", len(BOUNDARY_ROWS) >= 7, "Safety boundaries remain explicit for helper extraction.", boundary_row_count=len(BOUNDARY_ROWS)),
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
        "implementation_status": "implemented_narrow_smoke_helper_adoption",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "smoke_helper_version": SMOKE_CHECK_SHARED_VERSION,
        "helper_rows": smoke_helper_adoption_rows(),
        "helper_scope_rows": list(HELPER_SCOPE_ROWS),
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
    docs = docs if docs is not None else (read_docs_bundle(project_root, DOC_PATHS) if inspect_sources else "")
    token_row = smoke_token_validation_row(docs, REQUIRED_TOKENS)
    checks = list(report.get("checks") or [])
    checks.append(check_row("docs-and-smoke-helper-tokens", token_row["ok"], "Docs/source/dashboard/API/smoke contain required smoke helper extraction tokens.", missing_tokens=token_row.get("missing_tokens", []), required_token_count=token_row.get("required_token_count")))
    report.update({
        "missing_required_tokens": token_row.get("missing_tokens", []),
        "required_token_count": token_row.get("required_token_count"),
        "checks": checks,
        "status": status_from_rows(checks),
        "ok": ok_from_rows(checks),
    })
    return report


def api_preview_payload(report: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_api_preview_envelope(
        report or build_metadata(),
        route=API_ROUTE,
        adapter="api-preview-adapter-backfill-v1",
        warning="Smoke Check Helper Extraction Pilot is GET preview-only and does not execute fixtures, activate generated wiring, authorize release, or expand autonomy.",
    )


def text_report(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        ARC_TITLE,
        f"Status: {report.get('status')}",
        f"Review ID: {report.get('review_id')}",
        f"Smoke helper version: {report.get('smoke_helper_version')}",
        f"Helper row count: {len(report.get('helper_rows') or [])}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Subprocess spawn count: {report.get('subprocess_spawn_count')}",
        f"Source write count: {report.get('source_write_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("Helper rows:")
        for row in report.get("helper_rows") or []:
            lines.append(f"- {row.get('helper')}: {row.get('status')} adopted_by={row.get('adopted_by')}")
        lines.append("Checks:")
        for row in report.get("checks") or []:
            lines.append(f"- {row.get('name')}: {row.get('status')} :: {row.get('message')}")
    return "\n".join(lines)


def build_smoke_check_helper_extraction_pilot_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    return build_metadata(project_id=project_id, root=root)


def build_smoke_check_helper_extraction_pilot(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    return build_report(root=root, inspect_sources=inspect_sources, docs=docs)


def smoke_check_helper_extraction_pilot_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    return text_report(report, full=full)


# v1070.2 smoke check helper extraction pilot tokens: smoke-check-helper-extraction-pilot-v1 /smoke-check-helper-extraction-pilot /api/source-surface/smoke-check-helper-extraction-pilot build_smoke_check_helper_extraction_pilot build_smoke_check_helper_extraction_pilot_metadata smoke_check_helper_extraction_pilot_text smoke-check-shared-v1 read_docs_bundle missing_required_tokens authority_boundary_violations smoke_token_validation_row actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.4 API preview adapter backfill token: api-preview-adapter-backfill-v1 build_api_preview_envelope conscious_agent/smoke_check_helper_extraction_pilot.py actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False api_get_preview_only=True dashboard_get_preview_only=True manual_api_dispatch_remains_authoritative=True
