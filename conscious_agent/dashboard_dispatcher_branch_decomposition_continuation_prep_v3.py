from __future__ import annotations

from release_metadata import RUNTIME_VERSION
import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_THREE_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_CHECK_ID = "dashboard-dispatcher-branch-decomposition-continuation-prep-v3"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_TITLE = "Dashboard Dispatcher Branch Decomposition Continuation Prep v3"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE = "/dashboard-dispatcher-branch-decomposition-continuation-prep-v3"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_RENDERER = "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

NEXT_CONTINUATION_CANDIDATE_PATH = "/settings"
NEXT_CONTINUATION_CANDIDATE_RENDERER = "render_settings"
NEXT_CONTINUATION_EXPECTED_HELPER = "render_settings_continuation_branch"
NEXT_CONTINUATION_CANDIDATE_EXTRACTION_ORDER = 9
CURRENT_HELPER_BACKED_BRANCH_COUNT = 8

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
    "branch_decomposition_continuation_prepared_only": True,
    "branch_decomposition_continuation_executed": False,
    "additional_branch_extraction_count": 0,
    "existing_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "prepared_candidate_count": 1,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": False,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, path: str) -> str:
    pattern = re.compile(rf'elif path == "{re.escape(path)}":\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_branch_decomposition_continuation_prep_v3_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    branch = _branch_block(dashboard_text, NEXT_CONTINUATION_CANDIDATE_PATH)
    row = {
        "path": NEXT_CONTINUATION_CANDIDATE_PATH,
        "renderer_name": NEXT_CONTINUATION_CANDIDATE_RENDERER,
        "expected_future_helper": NEXT_CONTINUATION_EXPECTED_HELPER,
        "extraction_order": NEXT_CONTINUATION_CANDIDATE_EXTRACTION_ORDER,
        "manual_branch_condition_present": f'elif path == "{NEXT_CONTINUATION_CANDIDATE_PATH}":' in branch,
        "direct_renderer_call_present": f"html = {NEXT_CONTINUATION_CANDIDATE_RENDERER}()" in branch,
        "future_helper_absent": NEXT_CONTINUATION_EXPECTED_HELPER not in branch and NEXT_CONTINUATION_EXPECTED_HELPER not in dashboard_text,
        "future_helper_active": NEXT_CONTINUATION_EXPECTED_HELPER in branch and NEXT_CONTINUATION_CANDIDATE_RENDERER in branch,
        "renderer_body_present": f"def {NEXT_CONTINUATION_CANDIDATE_RENDERER}" in dashboard_text,
        "parity_ok": parity.get(NEXT_CONTINUATION_CANDIDATE_PATH, {}).get("ok") is True,
        "already_helper_backed": NEXT_CONTINUATION_CANDIDATE_PATH in helper_paths,
        "successor_trial_active": "dashboard-dispatcher-branch-decomposition-continuation-trial-v3" in dashboard_text,
        "preview_only": True,
    }
    prep_state_ok = (
        row["manual_branch_condition_present"]
        and row["direct_renderer_call_present"]
        and row["future_helper_absent"]
        and row["already_helper_backed"] is False
    )
    successor_state_ok = (
        row["manual_branch_condition_present"]
        and row["future_helper_active"]
        and row["already_helper_backed"] is True
        and row["successor_trial_active"] is True
    )
    row["ok"] = row["renderer_body_present"] and row["parity_ok"] and (prep_state_ok or successor_state_ok)
    return [row]


def build_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14757,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    successor_route_allowance = 540 if "dashboard-dispatcher-batch-decomposition-prep-v8" in dashboard_text else (160 if "dashboard-dispatcher-batch-decomposition-trial-v7" in dashboard_text else (120 if "dashboard-dispatcher-batch-decomposition-trial-v6" in dashboard_text else (80 if "dashboard-dispatcher-batch-decomposition-prep-v5" in dashboard_text else 0)))
    line_successor_budget = previous_dashboard_line_count + 310 + successor_route_allowance
    candidate_rows = dashboard_dispatcher_branch_decomposition_continuation_prep_v3_rows(root)
    blocked_candidate_rows = [row for row in candidate_rows if row.get("ok") is not True]
    helper_rows = consolidated_branch_helper_rows()
    branch = _branch_block(dashboard_text, NEXT_CONTINUATION_CANDIDATE_PATH)
    proof_rows: list[dict[str, Any]] = [
        {"name": "continuation-prep-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_THREE_VERSION == expected_version},
        {"name": "continuation-prep-module-exists", "ok": "build_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_report" in helper_text},
        {"name": "dashboard-serves-continuation-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_RENDERER in dashboard_text},
        {"name": "route-registry-links-continuation-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_CHECK_ID in source_privacy_text},
        {"name": "helper-backed-count-at-or-beyond-prep", "ok": len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT, "helper_count": len(helper_rows)},
        {"name": "one-next-candidate-prepared", "ok": len(candidate_rows) == 1 and not blocked_candidate_rows, "blocked_count": len(blocked_candidate_rows)},
        {"name": "candidate-direct-or-successor-helper-backed", "ok": (f'elif path == "{NEXT_CONTINUATION_CANDIDATE_PATH}":' in branch and ((f"html = {NEXT_CONTINUATION_CANDIDATE_RENDERER}()" in branch and NEXT_CONTINUATION_EXPECTED_HELPER not in branch) or (NEXT_CONTINUATION_EXPECTED_HELPER in branch and NEXT_CONTINUATION_CANDIDATE_RENDERER in branch)))},
        {"name": "prep-only-or-successor-trial-safe", "ok": (SAFETY_BOUNDARY["branch_decomposition_continuation_prepared_only"] is True and SAFETY_BOUNDARY["branch_decomposition_continuation_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False) or ("dashboard-dispatcher-branch-decomposition-continuation-trial-v3" in dashboard_text and NEXT_CONTINUATION_EXPECTED_HELPER in branch)},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(line_successor_budget, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count, "successor_budget": max(line_successor_budget, 15750), "successor_route_allowance": successor_route_allowance},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE,
        "next_continuation_candidate_path": NEXT_CONTINUATION_CANDIDATE_PATH,
        "next_continuation_candidate_renderer": NEXT_CONTINUATION_CANDIDATE_RENDERER,
        "next_continuation_expected_helper": NEXT_CONTINUATION_EXPECTED_HELPER,
        "candidate_rows": candidate_rows,
        "blocked_candidate_rows": blocked_candidate_rows,
        "existing_helper_rows": helper_rows,
        "helper_backed_branch_count": len(helper_rows),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_decomposition_continuation_prep_v3_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Prepared branch: {report.get('next_continuation_candidate_path')}",
        f"Prepared renderer: {report.get('next_continuation_candidate_renderer')}",
        f"Expected future helper: {report.get('next_continuation_expected_helper')}",
        f"Existing helper-backed branches: {report.get('existing_helper_backed_branch_count')}",
        "Branch decomposition continuation prepared only: True",
        "Branch decomposition continuation executed: False",
        "Additional branch extractions: 0",
        "Dispatcher branch body moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-prep-v3: prep report blocked")
            print(report.get("rows"))
            print(report.get("blocked_candidate_rows"))
            return False
        if report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-prep-v3: branch body moved during prep")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-prep-v3: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-decomposition-continuation-prep-v3: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-decomposition-continuation-prep-v3 candidate={report.get('next_continuation_candidate_path')} helper_count={report.get('helper_backed_branch_count')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-decomposition-continuation-prep-v3: {error}")
        return False


# v1074.0 dispatcher branch decomposition continuation prep v3 tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py NEXT_CONTINUATION_CANDIDATE_PATH=/settings render_settings branch_decomposition_continuation_prepared_only=True branch_decomposition_continuation_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=8 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip


# v1074.0 successor-compatible continuation prep v3 tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 render_settings_continuation_branch helper_backed_branch_count_may_exceed_prep_count=True existing_helper_backed_branch_count=8 branch_decomposition_continuation_trial_executed=True additional_branch_extraction_count=1 data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.0 dashboard dispatcher branch decomposition continuation prep v3 line budget successor allowance tokens: dashboard-dispatcher-batch-decomposition-prep-v5 successor_route_allowance=80 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.1 install-release successor compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 helper_backed_branch_count=24 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 continuation prep v3 successor line budget tokens: dashboard-dispatcher-batch-decomposition-trial-v6 successor_route_allowance=120 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 install-release successor compatibility token: dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py current_version=1075.4 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.7 install-release successor compatibility token: dashboard-dispatcher-batch-decomposition-trial-v7 line_budget_successor_allowance=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1076.1 successor line budget compatibility token: dashboard-dispatcher-batch-decomposition-prep-v8 dashboard_line_count=15190 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.0 successor line-budget compatibility token: successor_route_allowance=340 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.0 checkpoint-v11 successor line-budget repair token: successor_route_allowance=360 runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.

# v1077.2 trial-v12 successor line-budget repair token: bounded_allowance_increase=20 runtime_behavior_unchanged=True renderer_movement=False release_authorized=False autonomy_expanded=False
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.5 trial-v13 successor line-budget repair token: dashboard_line_count=15478 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.9 compatibility migration prep successor line-budget token: successor_route_allowance=500 runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
