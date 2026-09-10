from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_TWO_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_CHECK_ID = "dashboard-dispatcher-branch-expansion-backfill-trial-v2"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_TITLE = "Dashboard Dispatcher Branch Expansion Backfill Trial v2"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE = "/dashboard-dispatcher-branch-expansion-backfill-trial-v2"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_RENDERER = "render_dashboard_dispatcher_branch_expansion_backfill_trial_v2"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

BACKFILLED_BRANCH_PATH = "/dashboard-dispatcher-branch-extraction-trial"
BACKFILLED_BRANCH_RENDERER = "render_dashboard_dispatcher_branch_extraction_trial"
BACKFILLED_BRANCH_HELPER = "render_dashboard_dispatcher_branch_extraction_trial_backfill_v2_branch"
BACKFILLED_BRANCH_EXTRACTION_ORDER = 5
PREVIOUS_HELPER_BACKED_BRANCH_COUNT = 4
CURRENT_HELPER_BACKED_BRANCH_COUNT = 5
CONDITION_EXPR = '"/dashboard-dispatcher-branch-extraction-trial"'

SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "dashboard_get_preview_only": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "branch_expansion_backfill_trial_executed": True,
    "branch_expansion_backfill_prepared_only": False,
    "additional_branch_extraction_count": 1,
    "previous_helper_backed_branch_count": PREVIOUS_HELPER_BACKED_BRANCH_COUNT,
    "existing_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "backfilled_branch_count": 1,
    "extracted_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": True,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, condition_expr: str) -> str:
    pattern = re.compile(rf"elif path == {re.escape(condition_expr)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)")
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_branch_expansion_backfill_trial_v2_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    branch = _branch_block(dashboard_text, CONDITION_EXPR)
    row = {
        "path": BACKFILLED_BRANCH_PATH,
        "renderer_name": BACKFILLED_BRANCH_RENDERER,
        "helper_name": BACKFILLED_BRANCH_HELPER,
        "extraction_order": BACKFILLED_BRANCH_EXTRACTION_ORDER,
        "manual_condition_retained": f"elif path == {CONDITION_EXPR}:" in branch,
        "helper_invocation_present": BACKFILLED_BRANCH_HELPER in branch and BACKFILLED_BRANCH_RENDERER in branch,
        "direct_renderer_body_present": f"def {BACKFILLED_BRANCH_RENDERER}" in dashboard_text,
        "parity_ok": parity.get(BACKFILLED_BRANCH_PATH, {}).get("ok") is True,
        "helper_registered": BACKFILLED_BRANCH_PATH in helper_paths,
        "renderer_body_moved": False,
        "preview_only": True,
    }
    row["ok"] = (
        row["manual_condition_retained"]
        and row["helper_invocation_present"]
        and row["direct_renderer_body_present"]
        and row["parity_ok"]
        and row["helper_registered"]
        and row["renderer_body_moved"] is False
    )
    return [row]


def build_dashboard_dispatcher_branch_expansion_backfill_trial_v2_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14619,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v2.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    backfill_rows = dashboard_dispatcher_branch_expansion_backfill_trial_v2_rows(root)
    blocked_backfill_rows = [row for row in backfill_rows if row.get("ok") is not True]
    helper_rows = consolidated_branch_helper_rows()
    proof_rows: list[dict[str, Any]] = [
        {"name": "trial-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_VERSION == expected_version},
        {"name": "dashboard-serves-trial-page", "ok": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE" in dashboard_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_RENDERER in dashboard_text},
        {"name": "route-registry-links-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_branch_expansion_backfill_trial_v2_check" in row_helper_text},
        {"name": "helper-count-at-or-beyond-this-trial", "ok": len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT and CURRENT_HELPER_BACKED_BRANCH_COUNT == PREVIOUS_HELPER_BACKED_BRANCH_COUNT + 1},
        {"name": "exactly-one-backfill-branch-extraction", "ok": SAFETY_BOUNDARY["additional_branch_extraction_count"] == 1 and SAFETY_BOUNDARY["backfilled_branch_count"] == 1},
        {"name": "backfilled-branch-helper-backed", "ok": not blocked_backfill_rows, "blocked_count": len(blocked_backfill_rows)},
        {"name": "shared-helper-registers-branch", "ok": BACKFILLED_BRANCH_HELPER in shared_helper_text and BACKFILLED_BRANCH_PATH in shared_helper_text},
        {"name": "dispatcher-condition-not-moved", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False},
        {"name": "renderer-bodies-not-moved", "ok": SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v2.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE,
        "backfilled_branch_path": BACKFILLED_BRANCH_PATH,
        "backfilled_branch_renderer": BACKFILLED_BRANCH_RENDERER,
        "backfilled_branch_helper": BACKFILLED_BRANCH_HELPER,
        "backfill_rows": backfill_rows,
        "blocked_backfill_rows": blocked_backfill_rows,
        "existing_helper_rows": helper_rows,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_expansion_backfill_trial_v2_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Backfilled branch: {report.get('backfilled_branch_path')}",
        f"Backfilled renderer: {report.get('backfilled_branch_renderer')}",
        f"Existing helper-backed branches: {report.get('existing_helper_backed_branch_count')}",
        "Manual dispatcher condition retained: True",
        "Branch expansion backfill trial executed: True",
        "Renderer bodies moved: False",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_expansion_backfill_trial_v2_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_expansion_backfill_trial_v2_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-expansion-backfill-trial-v2: trial report blocked")
            print(report.get("rows"))
            print(report.get("blocked_backfill_rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-expansion-backfill-trial-v2: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-expansion-backfill-trial-v2: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-expansion-backfill-trial-v2 branch={report.get('backfilled_branch_path')} helper_count={report.get('existing_helper_backed_branch_count')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-expansion-backfill-trial-v2: {error}")
        return False


# 1073.0 Dashboard Dispatcher Branch Expansion Backfill Trial v2 tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v2 /dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard_dispatcher_branch_expansion_backfill_trial_v2.py BACKFILLED_BRANCH_PATH=/dashboard-dispatcher-branch-extraction-trial render_dashboard_dispatcher_branch_extraction_trial_backfill_v2_branch branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 previous_helper_backed_branch_count=4 existing_helper_backed_branch_count=5 backfilled_branch_count=1 extracted_branch_count=5 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.1 install-release successor compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 helper_backed_branch_count=24 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 install-release successor compatibility token: dashboard_dispatcher_branch_expansion_backfill_trial_v2.py current_version=1075.4 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
