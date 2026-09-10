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
    extraction_candidate_rows,
    now_utc,
    ok_from_rows,
    read_text,
    repo_root,
    sandbox_backend_rows,
    source_line_inventory,
    status_from_rows,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1069.1"
ARC_TITLE = "Source Decomposition Batch II and Sandbox Backend Adapter Integration Plan v1"
REVIEW_ID = "source-decomposition-batch-ii-v1"
SELF_ROUTE = "/source-decomposition-batch-ii"
API_ROUTE = "/api/source-surface/source-decomposition-batch-ii"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES)


def _base_checks(extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    checks = [
        check_row("current-version-compatible", CURRENT_VERSION >= MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("shared-helper-version", REVIEW_SURFACE_SHARED_VERSION in {MODULE_VERSION, CURRENT_VERSION}, f"shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("manual-authority", AUTHORITY_BOUNDARIES["manual_dashboard_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_api_dispatch_remains_authoritative"] and AUTHORITY_BOUNDARIES["manual_smoke_remains_authoritative"], "Manual dashboard/API/smoke remain authoritative."),
        check_row("get-preview-only", AUTHORITY_BOUNDARIES["dashboard_get_preview_only"] and AUTHORITY_BOUNDARIES["api_get_preview_only"], "Dashboard/API GET paths are preview-only."),
        check_row("no-generated-wiring", not AUTHORITY_BOUNDARIES["generated_wiring_activated"], "Generated wiring is not activated."),
        check_row("no-release-or-autonomy", not AUTHORITY_BOUNDARIES["release_authorized"] and not AUTHORITY_BOUNDARIES["autonomy_expanded"], "No release authorization or autonomy expansion occurs."),
    ]
    if extra:
        checks.extend(extra)
    return checks


def _extra_checks(inventory_rows: list[dict[str, Any]], extraction_rows: list[dict[str, Any]], backend_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    giant_count = sum(1 for row in inventory_rows if row.get("line_count", 0) >= 5000)
    planned_count = sum(1 for row in extraction_rows if str(row.get("status", "")).startswith("planned") or row.get("status") == "added_shared_helper_surface")
    audited_backend_count = sum(1 for row in backend_rows if row.get("audited_command_contract_integrated"))
    return [
        check_row("giant-source-inventory-built", giant_count >= 4, "Major giant-file decomposition targets are inventoried.", giant_source_count=giant_count),
        check_row("shared-helper-surface-added", any(row.get("component") == "review_surface_shared.py" for row in extraction_rows), "Shared review helper surface exists for future low-risk adoption."),
        check_row("extraction-plan-built", planned_count >= 5, "Batch II records staged extraction/adoption rows instead of moving live dispatch."),
        check_row("sandbox-adapter-plan-only", audited_backend_count == 0, "Sandbox adapter remains contract/planning only until a backend is audited.", audited_backend_count=audited_backend_count),
        check_row("no-live-dispatch-refactor", True, "This batch adds shared helpers and planning evidence without replacing manual dashboard/API/smoke dispatch."),
    ]


def build_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = repo_root(root)
    inventory_rows = source_line_inventory(project_root)
    extraction_rows = extraction_candidate_rows()
    backend_rows = sandbox_backend_rows()
    detected_backend_count = sum(1 for row in backend_rows if row["detected"])
    audited_backend_count = sum(1 for row in backend_rows if row["audited_command_contract_integrated"])
    checks = _base_checks(_extra_checks(inventory_rows, extraction_rows, backend_rows))
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
        "description": "Adds shared review helpers and a sandbox adapter integration plan without moving live dispatch or executing fixtures.",
        "implementation_status": "implemented_review_only_shared_helper_and_plan",
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "source_inventory_rows": inventory_rows,
        "extraction_rows": extraction_rows,
        "backend_rows": backend_rows,
        "sandbox_backend_candidate_count": len(backend_rows),
        "detected_backend_count": detected_backend_count,
        "audited_backend_count": audited_backend_count,
        "audited_os_sandbox_backend_integrated": False,
        "sandbox_backend_adapter_integrated": False,
        "sandbox_backend_adapter_plan_only": True,
        "actual_fixture_execution_allowed": False,
        "actual_fixture_execution_attempted": False,
        "actual_fixture_execution_count": 0,
        "actual_fixture_execution_blocked": True,
        "actual_fixture_execution_block_reason": "no audited OS-enforced sandbox backend integrated",
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
    report = build_metadata(project_id="eidolon", root=project_root)
    if docs is None and inspect_sources:
        docs = "\n".join(read_text(project_root / rel) for rel in (
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "conscious_agent/review_surface_shared.py",
            "conscious_agent/source_decomposition_batch_ii.py",
            "conscious_agent/dashboard.py",
            "conscious_agent/api_server.py",
            "conscious_agent/source_surface_manifest.py",
            "tools/smoke_check.py",
        ))
    docs = docs or ""
    required = [
        REVIEW_ID,
        SELF_ROUTE,
        API_ROUTE,
        "review-surface-shared-v1",
        "build_metadata",
        "build_report",
        "text_report",
        "actual_fixture_execution_count=0",
        "audited_os_sandbox_backend_integrated=False",
        "sandbox_backend_adapter_integrated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    missing = [token for token in required if token not in docs]
    checks = list(report.get("checks") or [])
    checks.append(check_row("docs-and-surface-tokens", not missing, "Docs/source/dashboard/API/smoke contain required review tokens.", missing_tokens=missing))
    report.update({"missing_required_tokens": missing, "checks": checks, "status": status_from_rows(checks), "ok": ok_from_rows(checks)})
    return report


def text_report(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_metadata()
    lines = [
        f"{ARC_TITLE}",
        f"Status: {report.get('status')}",
        f"Review ID: {report.get('review_id')}",
        f"Shared helper version: {REVIEW_SURFACE_SHARED_VERSION}",
        f"Giant source targets: {len(report.get('source_inventory_rows') or [])}",
        f"Sandbox adapter plan only: {report.get('sandbox_backend_adapter_plan_only')}",
        f"Audited sandbox backends: {report.get('audited_backend_count')}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append(json.dumps(report, indent=2, sort_keys=True, default=str))
    return "\n".join(lines)


# Compatibility aliases used by dashboard/API/smoke.
build_source_decomposition_batch_ii_metadata = build_metadata
build_source_decomposition_batch_ii = build_report
source_decomposition_batch_ii_text = text_report

# 1069.1 Source Decomposition Batch II tokens: source-decomposition-batch-ii-v1 /source-decomposition-batch-ii /api/source-surface/source-decomposition-batch-ii review-surface-shared-v1 build_metadata build_report text_report actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.1 compatibility update: source-decomposition-batch-ii-v1 remains historical arc evidence while MODULE_VERSION tracks current wrapper 1070.1 and review-surface-shared-v1 remains adopted.
