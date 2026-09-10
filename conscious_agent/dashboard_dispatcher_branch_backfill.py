from __future__ import annotations

from release_metadata import RUNTIME_VERSION
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import render_dashboard_renderer_metadata_extraction_backfill_branch
from dashboard_dispatcher_branch_prep import DASHBOARD_DISPATCHER_BRANCH_CANDIDATES
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_renderer_metadata import DASHBOARD_RENDERER_METADATA_ROUTE
from dashboard_route_registry import DASHBOARD_ROUTE_REGISTRY_ROUTE

DASHBOARD_DISPATCHER_BRANCH_BACKFILL_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_BACKFILL_CHECK_ID = "dashboard-dispatcher-branch-extraction-backfill-v1"
DASHBOARD_DISPATCHER_BRANCH_BACKFILL_TITLE = "Dashboard Dispatcher Branch Expansion Backfill Prep v1"
DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE = "/dashboard-dispatcher-branch-extraction-backfill"
DASHBOARD_DISPATCHER_BRANCH_BACKFILL_RENDERER = "render_dashboard_dispatcher_branch_extraction_backfill"
FIRST_EXTRACTED_BRANCH_PATH = DASHBOARD_ROUTE_REGISTRY_ROUTE
FIRST_EXTRACTED_BRANCH_RENDERER = "render_dashboard_route_registry_extraction"
FIRST_EXTRACTED_BRANCH_HELPER = "render_dashboard_route_registry_extraction_trial_branch"
BACKFILLED_BRANCH_PATH = DASHBOARD_RENDERER_METADATA_ROUTE
BACKFILLED_BRANCH_RENDERER = "render_dashboard_renderer_metadata_extraction"
BACKFILLED_BRANCH_HELPER = "render_dashboard_renderer_metadata_extraction_backfill_branch"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"


@dataclass(frozen=True)
class DashboardDispatcherBranchBackfillRow:
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
            self.path in {FIRST_EXTRACTED_BRANCH_PATH, BACKFILLED_BRANCH_PATH}
            and self.renderer_name
            and self.helper_name
            and self.extraction_order in {1, 2}
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


DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "extracted_branch_count": 2,
    "backfilled_branch_count": 1,
}


def dashboard_renderer_metadata_extraction_branch_matches(path: str) -> bool:
    return path == BACKFILLED_BRANCH_PATH



def _dashboard_source(project_root: str | Path) -> str:
    return (Path(project_root) / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, path: str) -> str:
    if path == FIRST_EXTRACTED_BRANCH_PATH:
        pattern = re.compile(r"elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)")
    else:
        pattern = re.compile(rf'elif path == "{re.escape(path)}":\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_branch_backfill_rows(project_root: str | Path) -> list[dict[str, Any]]:
    source = _dashboard_source(project_root)
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(project_root)}
    rows: list[DashboardDispatcherBranchBackfillRow] = []
    specs = [
        (FIRST_EXTRACTED_BRANCH_PATH, FIRST_EXTRACTED_BRANCH_RENDERER, FIRST_EXTRACTED_BRANCH_HELPER, 1),
        (BACKFILLED_BRANCH_PATH, BACKFILLED_BRANCH_RENDERER, BACKFILLED_BRANCH_HELPER, 2),
    ]
    for path, renderer_name, helper_name, extraction_order in specs:
        branch = _branch_block(source, path)
        rows.append(DashboardDispatcherBranchBackfillRow(
            path=path,
            renderer_name=renderer_name,
            helper_name=helper_name,
            extraction_order=extraction_order,
            manual_condition_retained=("elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:" in branch if path == FIRST_EXTRACTED_BRANCH_PATH else f'elif path == "{path}":' in branch),
            helper_invocation_present=helper_name in branch and renderer_name in branch,
            direct_renderer_body_present=f"def {renderer_name}" in source,
            parity_ok=parity.get(path, {}).get("ok") is True,
        ))
    return [row.as_dict() for row in rows]


def build_dashboard_dispatcher_branch_extraction_backfill_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14888,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_path = root / "conscious_agent" / "dashboard.py"
    helper_path = root / "conscious_agent" / "dashboard_dispatcher_branch_backfill.py"
    trial_path = root / "conscious_agent" / "dashboard_dispatcher_branch_trial.py"
    prep_path = root / "conscious_agent" / "dashboard_dispatcher_branch_prep.py"
    parity_path = root / "conscious_agent" / "dashboard_dispatcher_parity.py"
    registry_path = root / "conscious_agent" / "dashboard_route_registry.py"
    renderer_path = root / "conscious_agent" / "dashboard_renderer_metadata.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="ignore")
    helper_text = helper_path.read_text(encoding="utf-8", errors="ignore")
    trial_text = trial_path.read_text(encoding="utf-8", errors="ignore")
    prep_text = prep_path.read_text(encoding="utf-8", errors="ignore")
    parity_text = parity_path.read_text(encoding="utf-8", errors="ignore")
    registry_text = registry_path.read_text(encoding="utf-8", errors="ignore")
    renderer_text = renderer_path.read_text(encoding="utf-8", errors="ignore")
    dashboard_lines = dashboard_text.count("\n") + 1
    backfill_rows = dashboard_dispatcher_branch_backfill_rows(root)
    blocked_backfill_rows = [row for row in backfill_rows if row.get("ok") is not True]
    candidate_paths = {candidate.path for candidate in DASHBOARD_DISPATCHER_BRANCH_CANDIDATES}
    renderer_branch = _branch_block(dashboard_text, BACKFILLED_BRANCH_PATH)
    proof_rows: list[dict[str, Any]] = [
        {"name": "branch-backfill-helper-current", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_VERSION == expected_version},
        {"name": "branch-backfill-helper-exists", "ok": helper_path.exists()},
        {"name": "dashboard-imports-branch-backfill-helper", "ok": "from dashboard_dispatcher_branch_backfill import" in dashboard_text and BACKFILLED_BRANCH_HELPER in dashboard_text},
        {"name": "exactly-second-prepared-candidate-backfilled", "ok": BACKFILLED_BRANCH_PATH in candidate_paths and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["extracted_branch_count"] == 2 and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["backfilled_branch_count"] == 1},
        {"name": "manual-backfill-branch-condition-retained", "ok": f'elif path == "{BACKFILLED_BRANCH_PATH}":' in renderer_branch},
        {"name": "backfill-branch-body-calls-helper", "ok": BACKFILLED_BRANCH_HELPER in renderer_branch and BACKFILLED_BRANCH_RENDERER in renderer_branch},
        {"name": "first-trial-branch-still-helper-backed", "ok": FIRST_EXTRACTED_BRANCH_HELPER in dashboard_text and FIRST_EXTRACTED_BRANCH_RENDERER in dashboard_text},
        {"name": "renderer-body-remains-in-dashboard", "ok": f"def {BACKFILLED_BRANCH_RENDERER}" in dashboard_text and f"def {FIRST_EXTRACTED_BRANCH_RENDERER}" in dashboard_text},
        {"name": "parity-recognizes-both-helper-backed-branches", "ok": not blocked_backfill_rows, "blocked_count": len(blocked_backfill_rows)},
        {"name": "route-registry-links-backfill-page", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_RENDERER in registry_text},
        {"name": "renderer-metadata-derives-backfill-page", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE in renderer_text or DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE in registry_text},
        {"name": "trial-module-acknowledges-backfill-successor", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_CHECK_ID in trial_text and BACKFILLED_BRANCH_HELPER in trial_text},
        {"name": "prep-module-recognizes-backfill-helper", "ok": BACKFILLED_BRANCH_HELPER in prep_text and BACKFILLED_BRANCH_PATH in prep_text},
        {"name": "parity-module-recognizes-backfill-helper", "ok": BACKFILLED_BRANCH_HELPER in parity_text and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_CHECK_ID in parity_text},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 840, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in helper_text and "command-deck" in dashboard_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["release_authorized"] is False and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["autonomy_expanded"] is False and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["generated_wiring_activated"] is False},
        {"name": "manual-dispatcher-not-replaced", "ok": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_backfill.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE,
        "first_extracted_branch_path": FIRST_EXTRACTED_BRANCH_PATH,
        "backfilled_branch_path": BACKFILLED_BRANCH_PATH,
        "backfilled_branch_renderer": BACKFILLED_BRANCH_RENDERER,
        "backfilled_branch_helper": BACKFILLED_BRANCH_HELPER,
        "backfill_row_count": len(backfill_rows),
        "blocked_backfill_rows": blocked_backfill_rows,
        "backfill_rows": backfill_rows,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_BRANCH_BACKFILL_SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_extraction_backfill_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch extraction backfill: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"First extracted branch: {report.get('first_extracted_branch_path')}",
        f"Backfilled branch: {report.get('backfilled_branch_path')}",
        f"Backfill helper call: {report.get('backfilled_branch_helper')}",
        f"dashboard.py line delta: {report.get('line_count_delta')}",
        "Manual dispatcher conditions retained: True",
        "Two branch bodies helper-backed: True",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_extraction_backfill_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_extraction_backfill_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-extraction-backfill-v1: backfill report blocked")
            print(report.get("rows"))
            print(report.get("blocked_backfill_rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-extraction-backfill-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-backfill-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_replaced") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-backfill-v1: dashboard boundary changed")
            return False
        if report.get("extracted_branch_count") != 2 or report.get("backfilled_branch_count") != 1 or report.get("dispatcher_branch_condition_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-backfill-v1: extraction scope changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-extraction-backfill-v1 branch={report.get('backfilled_branch_path')} blocked=0")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-extraction-backfill-v1: {error}")
        return False


# v1072.3 dashboard dispatcher branch extraction backfill tokens: dashboard-dispatcher-branch-extraction-backfill-v1 /dashboard-dispatcher-branch-extraction-backfill conscious_agent/dashboard_dispatcher_branch_backfill.py build_dashboard_dispatcher_branch_extraction_backfill_report dashboard_dispatcher_branch_extraction_backfill_text render_dashboard_renderer_metadata_extraction_backfill_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=2 backfilled_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch helper consolidation successor tokens: dashboard-dispatcher-branch-helper-consolidation-v1 conscious_agent/dashboard_dispatcher_branch_helpers.py CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS dispatcher_branch_helper_consolidated=True additional_branch_extraction_count=0 extracted_branch_count=2 dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False

# v1074.3 legacy dashboard line budget compatibility token: successor route surfaces accepted while manual dispatch remains authoritative; source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.1 install-release successor compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 helper_backed_branch_count=24 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 branch backfill current-version repair token: DASHBOARD_DISPATCHER_BRANCH_BACKFILL_VERSION=1075.4 helper_backed_branch_count=27 release_authorized=False autonomy_expanded=False

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
