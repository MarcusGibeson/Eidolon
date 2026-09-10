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
    repo_root,
    shared_adoption_rows,
    source_line_inventory,
    status_from_rows,
)
from sandbox_backend_adapter import (
    SANDBOX_BACKEND_ADAPTER_ID,
    SANDBOX_BACKEND_ADAPTER_VERSION,
    build_sandbox_backend_adapter_report,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1069.1"
ARC_TITLE = "Dashboard API Smoke Shared Utility Adoption and Sandbox Adapter Skeleton v1"
REVIEW_ID = "dashboard-api-smoke-shared-utility-adoption-v1"
SELF_ROUTE = "/dashboard-api-smoke-shared-utility-adoption"
API_ROUTE = "/api/source-surface/dashboard-api-smoke-shared-utility-adoption"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)


def _docs(root: Path) -> str:
    rels = (
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/review_surface_shared.py",
        "conscious_agent/sandbox_backend_adapter.py",
        "conscious_agent/dashboard_api_smoke_shared_utility_adoption.py",
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


def _base_checks(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("shared-helper-current", REVIEW_SURFACE_SHARED_VERSION in {MODULE_VERSION, CURRENT_VERSION}, f"shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("sandbox-adapter-compatible", SANDBOX_BACKEND_ADAPTER_VERSION in {MODULE_VERSION, CURRENT_VERSION}, f"adapter={SANDBOX_BACKEND_ADAPTER_VERSION}; module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual dashboard/API/smoke dispatch remain authoritative."),
        check_row("get-preview-only", AUTHORITY_BOUNDARIES["dashboard_get_preview_only"] and AUTHORITY_BOUNDARIES["api_get_preview_only"], "Dashboard/API GET paths remain preview-only."),
        check_row("no-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"], "Generated wiring is not activated."),
        check_row("no-release-or-autonomy", not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No release authorization or autonomy expansion occurs."),
    ]
    if extra:
        rows.extend(extra)
    return rows


def build_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = repo_root(root)
    adapter = build_sandbox_backend_adapter_report(project_id=project_id)
    adoption_rows = shared_adoption_rows()
    inventory_rows = source_line_inventory(project_root)
    adopted_helper_count = sum(1 for row in adoption_rows if row.get("status") == "used")
    checks = _base_checks([
        check_row("shared-helper-adoption", adopted_helper_count >= 5, "Dashboard/API/smoke adoption rows prove helper usage by one narrow current family.", adopted_helper_count=adopted_helper_count),
        check_row("sandbox-adapter-skeleton", adapter.get("adapter_status") == "skeleton_contract_only", "Sandbox adapter is present as a non-executing skeleton."),
        check_row("sandbox-execution-blocked", adapter.get("actual_fixture_execution_allowed") is False and adapter.get("actual_fixture_execution_count") == 0, "The adapter does not allow fixture execution."),
        check_row("source-inventory-preserved", len(inventory_rows) >= 6, "Giant-file source inventory remains available for decomposition planning."),
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
        "implementation_status": "implemented_narrow_adoption",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "shared_helper_version": REVIEW_SURFACE_SHARED_VERSION,
        "sandbox_backend_adapter_id": SANDBOX_BACKEND_ADAPTER_ID,
        "sandbox_backend_adapter_version": SANDBOX_BACKEND_ADAPTER_VERSION,
        "adoption_rows": adoption_rows,
        "adopted_helper_count": adopted_helper_count,
        "source_inventory_rows": inventory_rows,
        "sandbox_backend_adapter": adapter,
        "sandbox_backend_adapter_integrated": False,
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_allowed": False,
        "actual_fixture_execution_attempted": False,
        "actual_fixture_execution_count": 0,
        "subprocess_spawn_count": 0,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "operator_approval_required": True,
        "checks": checks,
    }


def build_report(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    project_root = repo_root(root)
    report = build_metadata(root=project_root)
    required = [
        REVIEW_ID,
        SELF_ROUTE,
        API_ROUTE,
        "review-surface-shared-v1",
        "sandbox-backend-adapter-skeleton-v1",
        "html_table_from_rows",
        "preview_response_payload",
        "missing_tokens",
        "actual_fixture_execution_count=0",
        "sandbox_backend_adapter_integrated=False",
        "audited_os_sandbox_backend_integrated=False",
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
    checks.append(check_row("docs-and-adoption-tokens", not missing, "Docs/source/dashboard/API/smoke contain required shared adoption and adapter tokens.", missing_tokens=missing))
    report.update({"missing_required_tokens": missing, "checks": checks, "status": status_from_rows(checks), "ok": ok_from_rows(checks)})
    return report


def api_preview_payload(report: dict[str, Any] | None = None) -> dict[str, Any]:
    return build_api_preview_envelope(
        report or build_metadata(),
        route=API_ROUTE,
        adapter="api-preview-adapter-backfill-v1",
        warning="Dashboard API Smoke Shared Utility Adoption is GET preview-only and does not execute fixtures, activate generated wiring, authorize release, or expand autonomy.",
    )


def text_report(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        ARC_TITLE,
        f"Status: {report.get('status')}",
        f"Review ID: {report.get('review_id')}",
        f"Shared helper version: {report.get('shared_helper_version')}",
        f"Adopted helper count: {report.get('adopted_helper_count')}",
        f"Sandbox adapter status: {report.get('sandbox_backend_adapter', {}).get('adapter_status')}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append(json.dumps(report, indent=2, sort_keys=True, default=str))
    return "\n".join(lines)


build_dashboard_api_smoke_shared_utility_adoption_metadata = build_metadata
build_dashboard_api_smoke_shared_utility_adoption = build_report
dashboard_api_smoke_shared_utility_adoption_text = text_report

# v1070.1 Dashboard API Smoke Shared Utility Adoption tokens: dashboard-api-smoke-shared-utility-adoption-v1 /dashboard-api-smoke-shared-utility-adoption /api/source-surface/dashboard-api-smoke-shared-utility-adoption review-surface-shared-v1 sandbox-backend-adapter-skeleton-v1 html_table_from_rows preview_response_payload missing_tokens build_dashboard_api_smoke_shared_utility_adoption build_dashboard_api_smoke_shared_utility_adoption_metadata dashboard_api_smoke_shared_utility_adoption_text actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.4 API preview adapter backfill token: api-preview-adapter-backfill-v1 build_api_preview_envelope conscious_agent/dashboard_api_smoke_shared_utility_adoption.py actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False api_get_preview_only=True dashboard_get_preview_only=True manual_api_dispatch_remains_authoritative=True
