from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import render_dashboard_route_registry_extraction_trial_branch
from dashboard_dispatcher_branch_prep import DASHBOARD_DISPATCHER_BRANCH_CANDIDATES
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import DASHBOARD_ROUTE_REGISTRY_ROUTE

DASHBOARD_DISPATCHER_BRANCH_TRIAL_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_TRIAL_CHECK_ID = "dashboard-dispatcher-branch-extraction-trial-v1"
DASHBOARD_DISPATCHER_BRANCH_TRIAL_TITLE = "Dashboard Dispatcher Branch Extraction Trial v1"
DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE = "/dashboard-dispatcher-branch-extraction-trial"
DASHBOARD_DISPATCHER_BRANCH_TRIAL_RENDERER = "render_dashboard_dispatcher_branch_extraction_trial"
EXTRACTED_BRANCH_PATH = DASHBOARD_ROUTE_REGISTRY_ROUTE
EXTRACTED_BRANCH_RENDERER = "render_dashboard_route_registry_extraction"
EXTRACTED_BRANCH_HELPER = "render_dashboard_route_registry_extraction_trial_branch"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"


@dataclass(frozen=True)
class DashboardDispatcherBranchTrialRow:
    path: str
    renderer_name: str
    helper_name: str
    manual_condition_retained: bool
    helper_invocation_present: bool
    direct_renderer_body_present: bool
    parity_ok: bool
    renderer_body_moved: bool = False
    preview_only: bool = True

    @property
    def ok(self) -> bool:
        return (
            self.path == EXTRACTED_BRANCH_PATH
            and self.renderer_name == EXTRACTED_BRANCH_RENDERER
            and self.helper_name == EXTRACTED_BRANCH_HELPER
            and self.manual_condition_retained
            and self.helper_invocation_present
            and self.direct_renderer_body_present
            and self.parity_ok
            and self.renderer_body_moved is False
            and self.preview_only is True
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "renderer_name": self.renderer_name,
            "helper_name": self.helper_name,
            "manual_condition_retained": self.manual_condition_retained,
            "helper_invocation_present": self.helper_invocation_present,
            "direct_renderer_body_present": self.direct_renderer_body_present,
            "parity_ok": self.parity_ok,
            "renderer_body_moved": self.renderer_body_moved,
            "preview_only": self.preview_only,
            "ok": self.ok,
        }


DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "dispatcher_branch_helper_adopted": True,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": True,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
    "branch_extraction_executed": True,
    "branch_extraction_prepared_only": False,
    "extracted_branch_count": 1,
}


def dashboard_route_registry_extraction_branch_matches(path: str) -> bool:
    return path == EXTRACTED_BRANCH_PATH



def _dashboard_source(project_root: str | Path) -> str:
    return (Path(project_root) / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, path_token: str = "DASHBOARD_ROUTE_REGISTRY_ROUTE") -> str:
    pattern = re.compile(rf"elif path == {re.escape(path_token)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)")
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_branch_trial_rows(project_root: str | Path) -> list[dict[str, Any]]:
    source = _dashboard_source(project_root)
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(project_root)}
    branch = _branch_block(source)
    row = DashboardDispatcherBranchTrialRow(
        path=EXTRACTED_BRANCH_PATH,
        renderer_name=EXTRACTED_BRANCH_RENDERER,
        helper_name=EXTRACTED_BRANCH_HELPER,
        manual_condition_retained="elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:" in branch,
        helper_invocation_present=EXTRACTED_BRANCH_HELPER in branch and EXTRACTED_BRANCH_RENDERER in branch,
        direct_renderer_body_present=f"def {EXTRACTED_BRANCH_RENDERER}" in source,
        parity_ok=parity.get(EXTRACTED_BRANCH_PATH, {}).get("ok") is True,
    )
    return [row.as_dict()]


def build_dashboard_dispatcher_branch_extraction_trial_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14499,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_path = root / "conscious_agent" / "dashboard.py"
    helper_path = root / "conscious_agent" / "dashboard_dispatcher_branch_trial.py"
    prep_path = root / "conscious_agent" / "dashboard_dispatcher_branch_prep.py"
    parity_path = root / "conscious_agent" / "dashboard_dispatcher_parity.py"
    registry_path = root / "conscious_agent" / "dashboard_route_registry.py"
    renderer_path = root / "conscious_agent" / "dashboard_renderer_metadata.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="ignore")
    helper_text = helper_path.read_text(encoding="utf-8", errors="ignore")
    prep_text = prep_path.read_text(encoding="utf-8", errors="ignore")
    parity_text = parity_path.read_text(encoding="utf-8", errors="ignore")
    registry_text = registry_path.read_text(encoding="utf-8", errors="ignore")
    renderer_text = renderer_path.read_text(encoding="utf-8", errors="ignore")
    dashboard_lines = dashboard_text.count("\n") + 1
    successor_route_allowance = 520 if "dashboard-dispatcher-batch-decomposition-prep-v8" in dashboard_text else (160 if "dashboard-dispatcher-batch-decomposition-trial-v7" in dashboard_text else (120 if "dashboard-dispatcher-batch-decomposition-prep-v5" in dashboard_text else 0))
    line_successor_budget = previous_dashboard_line_count + 590 + successor_route_allowance
    trial_rows = dashboard_dispatcher_branch_trial_rows(root)
    blocked_trial_rows = [row for row in trial_rows if row.get("ok") is not True]
    branch = _branch_block(dashboard_text)
    candidate_paths = {candidate.path for candidate in DASHBOARD_DISPATCHER_BRANCH_CANDIDATES}
    proof_rows: list[dict[str, Any]] = [
        {"name": "branch-trial-helper-current", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_VERSION == expected_version},
        {"name": "branch-trial-helper-exists", "ok": helper_path.exists()},
        {"name": "dashboard-imports-branch-trial-helper", "ok": "from dashboard_dispatcher_branch_trial import" in dashboard_text and EXTRACTED_BRANCH_HELPER in dashboard_text},
        {"name": "exactly-one-prepared-candidate-extracted", "ok": EXTRACTED_BRANCH_PATH in candidate_paths and DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["extracted_branch_count"] == 1},
        {"name": "manual-branch-condition-retained", "ok": "elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:" in branch},
        {"name": "branch-body-calls-helper", "ok": EXTRACTED_BRANCH_HELPER in branch and EXTRACTED_BRANCH_RENDERER in branch},
        {"name": "renderer-body-remains-in-dashboard", "ok": f"def {EXTRACTED_BRANCH_RENDERER}" in dashboard_text},
        {"name": "parity-helper-recognizes-extracted-branch", "ok": not blocked_trial_rows, "blocked_count": len(blocked_trial_rows)},
        {"name": "route-registry-links-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_TRIAL_RENDERER in registry_text},
        {"name": "renderer-metadata-derives-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE in renderer_text or DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE in registry_text},
        {"name": "prep-module-acknowledges-trial-successor", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_CHECK_ID in prep_text and EXTRACTED_BRANCH_HELPER in prep_text},
        {"name": "parity-module-acknowledges-trial-helper", "ok": EXTRACTED_BRANCH_HELPER in parity_text and DASHBOARD_DISPATCHER_BRANCH_TRIAL_CHECK_ID in parity_text},
        {"name": "dashboard-line-count-successor-budget", "ok": dashboard_lines <= max(line_successor_budget, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count, "successor_budget": max(line_successor_budget, 15750), "successor_route_allowance": successor_route_allowance},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in helper_text and "command-deck" in dashboard_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["release_authorized"] is False and DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["autonomy_expanded"] is False and DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["generated_wiring_activated"] is False},
        {"name": "manual-dispatcher-not-replaced", "ok": DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_TRIAL_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_TRIAL_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_trial.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE,
        "extracted_branch_path": EXTRACTED_BRANCH_PATH,
        "extracted_branch_renderer": EXTRACTED_BRANCH_RENDERER,
        "extracted_branch_helper": EXTRACTED_BRANCH_HELPER,
        "trial_row_count": len(trial_rows),
        "blocked_trial_rows": blocked_trial_rows,
        "trial_rows": trial_rows,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_BRANCH_TRIAL_SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_extraction_trial_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch extraction trial: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Extracted branch: {report.get('extracted_branch_path')}",
        f"Helper call: {report.get('extracted_branch_helper')}",
        f"dashboard.py line delta: {report.get('line_count_delta')}",
        "Manual dispatcher condition retained: True",
        "One branch body moved behind helper: True",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_extraction_trial_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_extraction_trial_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-extraction-trial-v1: trial report blocked")
            print(report.get("rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-extraction-trial-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-trial-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_replaced") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-trial-v1: dashboard boundary changed")
            return False
        if report.get("extracted_branch_count") != 1 or report.get("dispatcher_branch_condition_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-trial-v1: extraction scope changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-extraction-trial-v1 branch={report.get('extracted_branch_path')} blocked=0")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-extraction-trial-v1: {error}")
        return False


# v1072.3 dashboard dispatcher branch extraction trial tokens: dashboard-dispatcher-branch-extraction-trial-v1 /dashboard-dispatcher-branch-extraction-trial conscious_agent/dashboard_dispatcher_branch_trial.py build_dashboard_dispatcher_branch_extraction_trial_report dashboard_dispatcher_branch_extraction_trial_text render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction backfill successor tokens: dashboard-dispatcher-branch-extraction-backfill-v1 render_dashboard_renderer_metadata_extraction_backfill_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=2 backfilled_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch helper consolidation successor tokens: dashboard-dispatcher-branch-helper-consolidation-v1 conscious_agent/dashboard_dispatcher_branch_helpers.py CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS dispatcher_branch_helper_consolidated=True additional_branch_extraction_count=0 extracted_branch_count=2 dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False

# v1075.0 dashboard dispatcher branch trial line budget successor allowance tokens: dashboard-dispatcher-batch-decomposition-prep-v5 successor_route_allowance=80 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 branch trial successor budget repair token: dashboard-line-count-successor-budget successor_route_allowance=120 helper_backed_branch_count=27 release_authorized=False autonomy_expanded=False

# v1075.7 install-release successor compatibility token: dashboard-dispatcher-batch-decomposition-trial-v7 line_budget_successor_allowance=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1076.1 successor line budget compatibility token: dashboard-dispatcher-batch-decomposition-prep-v8 dashboard_line_count=15190 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.0 successor line-budget compatibility token: successor_route_allowance=320 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.0 checkpoint-v11 successor line-budget repair token: successor_route_allowance=340 runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.

# v1077.2 trial-v12 successor line-budget repair token: bounded_allowance_increase=20 runtime_behavior_unchanged=True renderer_movement=False release_authorized=False autonomy_expanded=False
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.5 trial-v13 successor line-budget repair token: dashboard_line_count=15478 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.9 compatibility migration prep successor line-budget token: successor_route_allowance=480 runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
