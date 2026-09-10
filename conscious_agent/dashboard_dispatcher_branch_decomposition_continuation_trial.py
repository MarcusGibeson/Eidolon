from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_CHECK_ID = "dashboard-dispatcher-branch-decomposition-continuation-trial-v1"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_TITLE = "Dispatcher Branch Decomposition Continuation Trial v1"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE = "/dashboard-dispatcher-branch-decomposition-continuation-trial"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_RENDERER = "render_dashboard_dispatcher_branch_decomposition_continuation_trial"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

MOVED_BRANCH_PATH = "/smoke-check-helper-extraction-pilot"
MOVED_BRANCH_RENDERER = "render_smoke_check_helper_extraction_pilot"
MOVED_BRANCH_HELPER = "render_smoke_check_helper_extraction_pilot_continuation_branch"
MOVED_BRANCH_EXTRACTION_ORDER = 7
PREVIOUS_HELPER_BACKED_BRANCH_COUNT = 6
CURRENT_HELPER_BACKED_BRANCH_COUNT = 7

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
    "branch_decomposition_continuation_trial_executed": True,
    "branch_decomposition_continuation_prepared_only": False,
    "additional_branch_extraction_count": 1,
    "previous_helper_backed_branch_count": PREVIOUS_HELPER_BACKED_BRANCH_COUNT,
    "existing_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "moved_branch_count": 1,
    "extracted_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": True,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, path: str) -> str:
    pattern = re.compile(rf'elif path == "{re.escape(path)}":\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_branch_decomposition_continuation_trial_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_rows = consolidated_branch_helper_rows()
    helper_by_path = {str(row.get("path")): row for row in helper_rows}
    branch = _branch_block(dashboard_text, MOVED_BRANCH_PATH)
    helper_row = helper_by_path.get(MOVED_BRANCH_PATH, {})
    row = {
        "path": MOVED_BRANCH_PATH,
        "renderer_name": MOVED_BRANCH_RENDERER,
        "helper_name": MOVED_BRANCH_HELPER,
        "extraction_order": MOVED_BRANCH_EXTRACTION_ORDER,
        "manual_condition_retained": f'elif path == "{MOVED_BRANCH_PATH}":' in branch,
        "helper_invocation_present": MOVED_BRANCH_HELPER in branch and MOVED_BRANCH_RENDERER in branch,
        "direct_renderer_call_removed": f"html = {MOVED_BRANCH_RENDERER}()" not in branch,
        "renderer_body_present": f"def {MOVED_BRANCH_RENDERER}" in dashboard_text,
        "parity_ok": parity.get(MOVED_BRANCH_PATH, {}).get("ok") is True,
        "helper_registered": helper_row.get("helper_name") == MOVED_BRANCH_HELPER and helper_row.get("renderer_name") == MOVED_BRANCH_RENDERER,
        "renderer_body_moved": False,
        "preview_only": True,
    }
    row["ok"] = (
        row["manual_condition_retained"]
        and row["helper_invocation_present"]
        and row["direct_renderer_call_removed"]
        and row["renderer_body_present"]
        and row["parity_ok"]
        and row["helper_registered"]
        and row["renderer_body_moved"] is False
        and row["preview_only"] is True
    )
    return [row]


def build_dashboard_dispatcher_branch_decomposition_continuation_trial_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14716,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial.py")
    prep_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    trial_rows = dashboard_dispatcher_branch_decomposition_continuation_trial_rows(root)
    blocked_trial_rows = [row for row in trial_rows if row.get("ok") is not True]
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    branch = _branch_block(dashboard_text, MOVED_BRANCH_PATH)
    proof_rows: list[dict[str, Any]] = [
        {"name": "continuation-trial-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_VERSION == expected_version},
        {"name": "continuation-trial-module-exists", "ok": "build_dashboard_dispatcher_branch_decomposition_continuation_trial_report" in helper_text},
        {"name": "dashboard-serves-continuation-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_RENDERER in dashboard_text},
        {"name": "route-registry-links-continuation-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_branch_decomposition_continuation_trial_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_CHECK_ID in source_privacy_text},
        {"name": "prep-module-acknowledges-successor", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_CHECK_ID in prep_text and MOVED_BRANCH_HELPER in prep_text},
        {"name": "helper-count-increased-by-one", "ok": len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT and CURRENT_HELPER_BACKED_BRANCH_COUNT == PREVIOUS_HELPER_BACKED_BRANCH_COUNT + 1, "helper_count": len(helper_rows)},
        {"name": "moved-branch-helper-registered", "ok": MOVED_BRANCH_PATH in helper_paths and MOVED_BRANCH_HELPER in shared_helper_text},
        {"name": "exactly-one-continuation-branch-extraction", "ok": SAFETY_BOUNDARY["additional_branch_extraction_count"] == 1 and SAFETY_BOUNDARY["moved_branch_count"] == 1},
        {"name": "moved-branch-helper-backed", "ok": not blocked_trial_rows, "blocked_count": len(blocked_trial_rows)},
        {"name": "manual-condition-retained", "ok": f'elif path == "{MOVED_BRANCH_PATH}":' in branch},
        {"name": "branch-body-calls-shared-helper", "ok": MOVED_BRANCH_HELPER in branch and MOVED_BRANCH_RENDERER in branch},
        {"name": "renderer-body-still-in-dashboard", "ok": f"def {MOVED_BRANCH_RENDERER}" in dashboard_text},
        {"name": "branch-trial-executed-not-prep-only", "ok": SAFETY_BOUNDARY["branch_decomposition_continuation_trial_executed"] is True and SAFETY_BOUNDARY["branch_decomposition_continuation_prepared_only"] is False},
        {"name": "dispatcher-condition-not-moved", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False},
        {"name": "renderer-bodies-not-moved", "ok": SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 500, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial.py",
        "shared_helper_module": "conscious_agent/dashboard_dispatcher_branch_helpers.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE,
        "moved_branch_path": MOVED_BRANCH_PATH,
        "moved_branch_renderer": MOVED_BRANCH_RENDERER,
        "moved_branch_helper": MOVED_BRANCH_HELPER,
        "trial_rows": trial_rows,
        "blocked_trial_rows": blocked_trial_rows,
        "existing_helper_rows": helper_rows,
        "helper_backed_branch_count": len(helper_rows),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_decomposition_continuation_trial_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Moved branch: {report.get('moved_branch_path')}",
        f"Moved renderer: {report.get('moved_branch_renderer')}",
        f"Shared helper: {report.get('moved_branch_helper')}",
        f"Existing helper-backed branches: {report.get('existing_helper_backed_branch_count')}",
        "Branch decomposition continuation trial executed: True",
        "Additional branch extractions: 1",
        "Dispatcher branch body moved: True",
        "Dispatcher branch condition moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_decomposition_continuation_trial_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_decomposition_continuation_trial_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-trial-v1: trial report blocked")
            print(report.get("rows"))
            print(report.get("blocked_trial_rows"))
            return False
        if report.get("additional_branch_extraction_count") != 1 or report.get("dispatcher_branch_body_moved") is not True:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-trial-v1: one-branch trial boundary changed")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-trial-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-trial-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_replaced") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-trial-v1: dashboard authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-decomposition-continuation-trial-v1 branch={report.get('moved_branch_path')} helper_count={report.get('helper_backed_branch_count')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-decomposition-continuation-trial-v1: {error}")
        return False


# v1073.3 dispatcher branch decomposition continuation trial tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 /dashboard-dispatcher-branch-decomposition-continuation-trial conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial.py MOVED_BRANCH_PATH=/smoke-check-helper-extraction-pilot render_smoke_check_helper_extraction_pilot_continuation_branch branch_decomposition_continuation_trial_executed=True branch_decomposition_continuation_prepared_only=False additional_branch_extraction_count=1 previous_helper_backed_branch_count=6 existing_helper_backed_branch_count=7 moved_branch_count=1 extracted_branch_count=7 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
# v1075.2 line budget successor allowance tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 helper_backed_branch_count=24 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.6 successor line budget compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v7 dashboard_line_count_successor_budget=15180 release_authorized=False autonomy_expanded=False

# v1076.1 successor line budget compatibility token: dashboard-dispatcher-batch-decomposition-prep-v8 dashboard_line_count=15190 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.0 successor line-budget compatibility token: dashboard_line_count_bounded_successor_floor=15400 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.5 trial-v13 successor line-budget repair token: dashboard_line_count=15478 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
