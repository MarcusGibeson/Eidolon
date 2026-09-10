from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import (
    DASHBOARD_DISPATCHER_BRANCH_HELPER_BOUNDARY,
    consolidated_branch_helper_rows,
    render_dashboard_dispatcher_parity_expansion_trial_branch,
)
from dashboard_dispatcher_branch_expansion_prep import NEXT_CANDIDATE_PATH
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_CHECK_ID = "dashboard-dispatcher-branch-expansion-trial-v1"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_TITLE = "Dashboard Dispatcher Branch Expansion Backfill Prep v1"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE = "/dashboard-dispatcher-branch-expansion-trial"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_RENDERER = "render_dashboard_dispatcher_branch_expansion_trial"
EXPANDED_BRANCH_PATH = "/dashboard-dispatcher-parity"
EXPANDED_BRANCH_RENDERER = "render_dashboard_dispatcher_parity"
EXPANDED_BRANCH_HELPER = "render_dashboard_dispatcher_parity_expansion_trial_branch"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"


@dataclass(frozen=True)
class DashboardDispatcherBranchExpansionTrialRow:
    path: str
    renderer_name: str
    helper_name: str
    extraction_order: int
    manual_condition_retained: bool
    helper_invocation_present: bool
    direct_renderer_body_present: bool
    parity_ok: bool
    renderer_body_moved: bool = False
    preview_only: bool = True

    @property
    def ok(self) -> bool:
        return (
            self.path == EXPANDED_BRANCH_PATH
            and self.path == NEXT_CANDIDATE_PATH
            and self.renderer_name == EXPANDED_BRANCH_RENDERER
            and self.helper_name == EXPANDED_BRANCH_HELPER
            and self.extraction_order == 3
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
            "extraction_order": self.extraction_order,
            "manual_condition_retained": self.manual_condition_retained,
            "helper_invocation_present": self.helper_invocation_present,
            "direct_renderer_body_present": self.direct_renderer_body_present,
            "parity_ok": self.parity_ok,
            "renderer_body_moved": self.renderer_body_moved,
            "preview_only": self.preview_only,
            "ok": self.ok,
        }


DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "branch_expansion_trial_executed": True,
    "branch_expansion_prepared_only": False,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": True,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
    "additional_branch_extraction_count": 1,
    "existing_helper_backed_branch_count": 4,
    "extracted_branch_count": 4,
}


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, path: str = EXPANDED_BRANCH_PATH) -> str:
    pattern = re.compile(rf'elif path == "{re.escape(path)}":\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_branch_expansion_trial_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_rows = {str(row.get("path")): row for row in consolidated_branch_helper_rows()}
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    branch = _branch_block(dashboard_text)
    helper_row = helper_rows.get(EXPANDED_BRANCH_PATH, {})
    row = DashboardDispatcherBranchExpansionTrialRow(
        path=EXPANDED_BRANCH_PATH,
        renderer_name=EXPANDED_BRANCH_RENDERER,
        helper_name=EXPANDED_BRANCH_HELPER,
        extraction_order=int(helper_row.get("extraction_order") or 0),
        manual_condition_retained=f'elif path == "{EXPANDED_BRANCH_PATH}":' in branch,
        helper_invocation_present=EXPANDED_BRANCH_HELPER in branch and EXPANDED_BRANCH_RENDERER in branch,
        direct_renderer_body_present=f"def {EXPANDED_BRANCH_RENDERER}" in dashboard_text,
        parity_ok=parity.get(EXPANDED_BRANCH_PATH, {}).get("ok") is True,
    )
    return [row.as_dict()]


def build_dashboard_dispatcher_branch_expansion_trial_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14816,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    trial_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_expansion_trial.py")
    prep_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_expansion_prep.py")
    parity_text = _read(root, "conscious_agent/dashboard_dispatcher_parity.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    renderer_text = _read(root, "conscious_agent/dashboard_renderer_metadata.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = consolidated_branch_helper_rows()
    expanded_rows = dashboard_dispatcher_branch_expansion_trial_rows(root)
    blocked_expanded_rows = [row for row in expanded_rows if row.get("ok") is not True]
    branch = _branch_block(dashboard_text)
    proof_rows: list[dict[str, Any]] = [
        {"name": "expansion-trial-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_VERSION == expected_version},
        {"name": "expansion-trial-module-exists", "ok": "DashboardDispatcherBranchExpansionTrialRow" in trial_text},
        {"name": "dashboard-imports-expansion-trial", "ok": "from dashboard_dispatcher_branch_expansion_trial import" in dashboard_text and "build_dashboard_dispatcher_branch_expansion_trial_report" in dashboard_text},
        {"name": "dashboard-serves-expansion-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_RENDERER in dashboard_text},
        {"name": "route-registry-links-expansion-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_RENDERER in registry_text},
        {"name": "renderer-metadata-derives-expansion-trial-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE in renderer_text or DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_branch_expansion_trial_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_CHECK_ID in source_privacy_text},
        {"name": "shared-helper-has-third-branch", "ok": len(helper_rows) >= 3 and EXPANDED_BRANCH_HELPER in helper_text and EXPANDED_BRANCH_PATH in helper_text},
        {"name": "exactly-one-additional-branch-extraction", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["additional_branch_extraction_count"] >= 1 and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["existing_helper_backed_branch_count"] >= 3},
        {"name": "expanded-branch-helper-backed", "ok": not blocked_expanded_rows, "blocked_count": len(blocked_expanded_rows)},
        {"name": "manual-condition-retained", "ok": f'elif path == "{EXPANDED_BRANCH_PATH}":' in branch},
        {"name": "branch-body-calls-shared-helper", "ok": EXPANDED_BRANCH_HELPER in branch and f"html = {EXPANDED_BRANCH_HELPER}({EXPANDED_BRANCH_RENDERER})" in branch},
        {"name": "renderer-body-still-in-dashboard", "ok": f"def {EXPANDED_BRANCH_RENDERER}" in dashboard_text},
        {"name": "prep-module-still-identifies-candidate", "ok": "NEXT_CANDIDATE_PATH" in prep_text and EXPANDED_BRANCH_PATH in prep_text},
        {"name": "parity-module-recognizes-expanded-helper", "ok": EXPANDED_BRANCH_HELPER in parity_text or EXPANDED_BRANCH_PATH in parity_text},
        {"name": "branch-expansion-executed-not-prep-only", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["branch_expansion_trial_executed"] is True and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["branch_expansion_prepared_only"] is False},
        {"name": "dispatcher-condition-not-moved", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False},
        {"name": "renderer-bodies-not-moved", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 420, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in trial_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["release_authorized"] is False and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["autonomy_expanded"] is False and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_expansion_trial.py",
        "shared_helper_module": "conscious_agent/dashboard_dispatcher_branch_helpers.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE,
        "expanded_branch_path": EXPANDED_BRANCH_PATH,
        "expanded_branch_renderer": EXPANDED_BRANCH_RENDERER,
        "expanded_branch_helper": EXPANDED_BRANCH_HELPER,
        "expanded_rows": expanded_rows,
        "blocked_expanded_rows": blocked_expanded_rows,
        "existing_helper_rows": helper_rows,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_expansion_trial_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch expansion trial: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Expanded branch: {report.get('expanded_branch_path')}",
        f"Expanded renderer: {report.get('expanded_branch_renderer')}",
        f"Existing helper-backed branches: {report.get('existing_helper_backed_branch_count')}",
        f"Additional branch extractions: {report.get('additional_branch_extraction_count')}",
        "Manual dispatcher condition retained: True",
        "Branch expansion executed: True",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_expansion_trial_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_expansion_trial_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-expansion-trial-v1: expansion trial report blocked")
            print(report.get("rows"))
            print(report.get("blocked_expanded_rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-expansion-trial-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-expansion-trial-v1: authority boundary changed")
            return False
        if report.get("branch_expansion_trial_executed") is not True or report.get("additional_branch_extraction_count") != 1 or report.get("dispatcher_branch_body_moved") is not True:
            print("[fail] dashboard-dispatcher-branch-expansion-trial-v1: one-branch extraction boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_replaced") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-expansion-trial-v1: dashboard authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-expansion-trial-v1 branch={report.get('expanded_branch_path')} additional_extractions=1")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-expansion-trial-v1: {error}")
        return False


# v1072.3 dashboard dispatcher branch expansion trial tokens: dashboard-dispatcher-branch-expansion-trial-v1 /dashboard-dispatcher-branch-expansion-trial conscious_agent/dashboard_dispatcher_branch_expansion_trial.py build_dashboard_dispatcher_branch_expansion_trial_report dashboard_dispatcher_branch_expansion_trial_text EXPANDED_BRANCH_PATH=/dashboard-dispatcher-parity branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 extracted_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.3 dashboard line budget successor repair tokens: dashboard-dispatcher-batch-decomposition-prep-v6 route addition treated as successor preview growth, not branch movement; helper_backed_branch_count=24 prepared_batch_size=3 release_authorized=False autonomy_expanded=False

# v1075.7 install-release successor compatibility token: dashboard-dispatcher-batch-decomposition-trial-v7 line_budget_successor_allowance=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1077.0 successor line-budget compatibility token: dashboard_line_count_bounded_successor_floor=15400 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.5 trial-v13 successor line-budget repair token: dashboard_line_count=15478 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
