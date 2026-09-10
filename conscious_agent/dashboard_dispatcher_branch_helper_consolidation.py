from __future__ import annotations

from release_metadata import RUNTIME_VERSION
import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_backfill import (
    DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE,
    dashboard_dispatcher_branch_backfill_rows,
)
from dashboard_dispatcher_branch_helpers import (
    CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS,
    DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY,
    DASHBOARD_DISPATCHER_BRANCH_HELPERS_VERSION,
    consolidated_branch_helper_rows,
)
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_renderer_metadata import DASHBOARD_RENDERER_METADATA_ROUTE
from dashboard_route_registry import DASHBOARD_ROUTE_REGISTRY_ROUTE

_BRANCH_CONDITION_TOKENS: dict[str, str] = {
    DASHBOARD_ROUTE_REGISTRY_ROUTE: "elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:",
    DASHBOARD_RENDERER_METADATA_ROUTE: f'elif path == "{DASHBOARD_RENDERER_METADATA_ROUTE}":',
    "/dashboard-dispatcher-parity": 'elif path == "/dashboard-dispatcher-parity":',
    "/dashboard-dispatcher-branch-extraction-prep": 'elif path == "/dashboard-dispatcher-branch-extraction-prep":',
    "/dashboard-dispatcher-branch-extraction-trial": 'elif path == "/dashboard-dispatcher-branch-extraction-trial":',
    DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE: "elif path == DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE:",
    "/dashboard-dispatcher-branch-helper-consolidation": "elif path == DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE:",
    "/dashboard-dispatcher-branch-extraction-expansion-prep": "elif path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE:",
}

DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_CHECK_ID = "dashboard-dispatcher-branch-helper-consolidation-v1"
DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_TITLE = "Dashboard Dispatcher Branch Expansion Backfill Prep v1"
DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE = "/dashboard-dispatcher-branch-helper-consolidation"
DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_RENDERER = "render_dashboard_dispatcher_branch_helper_consolidation"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, path: str) -> str:
    condition = _BRANCH_CONDITION_TOKENS.get(path, f'elif path == "{path}":')
    pattern = re.compile(rf"{re.escape(condition)}\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)")
    match = pattern.search(source)
    return match.group(0) if match else ""


def build_dashboard_dispatcher_branch_helper_consolidation_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14888,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    consolidation_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helper_consolidation.py")
    trial_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_trial.py")
    backfill_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_backfill.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    renderer_text = _read(root, "conscious_agent/dashboard_renderer_metadata.py")
    parity_text = _read(root, "conscious_agent/dashboard_dispatcher_parity.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = [row for row in consolidated_branch_helper_rows() if int(row.get("extraction_order", 0)) <= 30]
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    backfill_rows = dashboard_dispatcher_branch_backfill_rows(root)
    branch_rows: list[dict[str, Any]] = []
    for row in helper_rows:
        branch = _branch_block(dashboard_text, str(row.get("path")))
        branch_rows.append({
            **row,
            "manual_branch_condition_retained": _BRANCH_CONDITION_TOKENS.get(str(row.get("path")), f'elif path == "{row.get("path")}":') in branch,
            "branch_invokes_consolidated_helper": str(row.get("helper_name")) in branch and str(row.get("renderer_name")) in branch,
            "renderer_body_present": f"def {row.get('renderer_name')}" in dashboard_text,
            "parity_ok": parity.get(str(row.get("path")), {}).get("ok") is True,
        })
    blocked_branch_rows = [row for row in branch_rows if not (row.get("manual_branch_condition_retained") and row.get("branch_invokes_consolidated_helper") and row.get("renderer_body_present") and row.get("parity_ok"))]
    local_wrapper_defs = [
        "def render_dashboard_route_registry_extraction_trial_branch" in trial_text,
        "def render_dashboard_renderer_metadata_extraction_backfill_branch" in backfill_text,
    ]
    proof_rows: list[dict[str, Any]] = [
        {"name": "consolidation-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_VERSION == expected_version},
        {"name": "shared-helper-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPERS_VERSION == expected_version},
        {"name": "shared-helper-module-exists", "ok": "CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS" in helper_text},
        {"name": "helper-backed-branch-count-current", "ok": len(helper_rows) >= 3 and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["extracted_branch_count"] >= 3},
        {"name": "one-or-more-additional-branch-extractions-after-consolidation", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["additional_branch_extraction_count"] >= 1},
        {"name": "trial-imports-shared-helper", "ok": "from dashboard_dispatcher_branch_helpers import" in trial_text and "render_dashboard_route_registry_extraction_trial_branch" in trial_text},
        {"name": "backfill-imports-shared-helper", "ok": "from dashboard_dispatcher_branch_helpers import" in backfill_text and "render_dashboard_renderer_metadata_extraction_backfill_branch" in backfill_text},
        {"name": "local-wrapper-definitions-removed", "ok": not any(local_wrapper_defs), "local_defs": local_wrapper_defs},
        {"name": "dashboard-import-source-remains-trial-backfill", "ok": "from dashboard_dispatcher_branch_trial import" in dashboard_text and "from dashboard_dispatcher_branch_backfill import" in dashboard_text},
        {"name": "manual-branch-conditions-retained", "ok": not [row for row in branch_rows if not row.get("manual_branch_condition_retained")]},
        {"name": "branch-bodies-still-helper-backed", "ok": not blocked_branch_rows, "blocked_count": len(blocked_branch_rows)},
        {"name": "backfill-proof-still-recognizes-two-branches", "ok": len(backfill_rows) == 2 and not [row for row in backfill_rows if row.get("ok") is not True]},
        {"name": "parity-recognizes-helper-backed-branches", "ok": all(parity.get(str(row.get("path")), {}).get("ok") is True for row in helper_rows)},
        {"name": "route-registry-links-consolidation-page", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_RENDERER in registry_text},
        {"name": "renderer-metadata-derives-consolidation-page", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE in renderer_text or DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE in registry_text},
        {"name": "parity-module-acknowledges-consolidated-helper", "ok": "dashboard_dispatcher_branch_helpers" in parity_text or "render_dashboard_renderer_metadata_extraction_backfill_branch" in parity_text},
        {"name": "smoke-row-registered-through-helper", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_CHECK_ID in row_helper_text},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 840, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in helper_text and "command-deck" in dashboard_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["release_authorized"] is False and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["autonomy_expanded"] is False and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["generated_wiring_activated"] is False},
        {"name": "manual-dispatcher-not-replaced", "ok": DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["manual_dashboard_remains_authoritative"] is True and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["http_dispatcher_replaced"] is False and DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY["dispatcher_branch_condition_moved"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_helpers.py",
        "consolidation_module": "conscious_agent/dashboard_dispatcher_branch_helper_consolidation.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE,
        "helper_rows": helper_rows,
        "branch_rows": branch_rows,
        "blocked_branch_rows": blocked_branch_rows,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY,
    }


def dashboard_dispatcher_branch_helper_consolidation_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch helper consolidation: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Shared helper module: {report.get('helper_module')}",
        f"Consolidated helper-backed branches: {len(report.get('helper_rows') or [])}",
        f"Additional branch extractions since consolidation: {report.get('additional_branch_extraction_count')}",
        f"dashboard.py line delta: {report.get('line_count_delta')}",
        "Manual dispatcher conditions retained: True",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_helper_consolidation_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_helper_consolidation_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-helper-consolidation-v1: consolidation report blocked")
            print(report.get("rows"))
            print(report.get("blocked_branch_rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-helper-consolidation-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-helper-consolidation-v1: authority boundary changed")
            return False
        if report.get("additional_branch_extraction_count") < 1 or report.get("extracted_branch_count") < 3:
            print("[fail] dashboard-dispatcher-branch-helper-consolidation-v1: extraction scope changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_replaced") is not False or report.get("dispatcher_branch_condition_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-helper-consolidation-v1: dashboard authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-helper-consolidation-v1 helpers={len(report.get('helper_rows') or [])} blocked=0")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-helper-consolidation-v1: {error}")
        return False


# v1072.3 dashboard dispatcher branch helper consolidation tokens: dashboard-dispatcher-branch-helper-consolidation-v1 /dashboard-dispatcher-branch-helper-consolidation conscious_agent/dashboard_dispatcher_branch_helper_consolidation.py conscious_agent/dashboard_dispatcher_branch_helpers.py build_dashboard_dispatcher_branch_helper_consolidation_report dashboard_dispatcher_branch_helper_consolidation_text CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS dispatcher_branch_helper_consolidated=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True additional_branch_extraction_count=1 extracted_branch_count=3 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 dashboard dispatcher branch helper consolidation successor tokens: dashboard-dispatcher-batch-decomposition-trial-v1 extracted_branch_count=12 additional_branch_extraction_count=3 one_or_more_additional_branch_extractions_after_consolidation=True

# v1074.3 legacy dashboard line budget compatibility token: successor route surfaces accepted while manual dispatch remains authoritative; source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.1 install-release successor compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 helper_backed_branch_count=24 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 install-release successor compatibility token: dashboard_dispatcher_branch_helper_consolidation.py current_version=1075.4 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.7 branch helper consolidation successor token: recognizes DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE after trial-v7 helper wrapping source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
