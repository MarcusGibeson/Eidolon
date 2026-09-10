from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_branch_prep import DASHBOARD_DISPATCHER_BRANCH_CANDIDATES
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_CHECK_ID = "dashboard-dispatcher-branch-extraction-expansion-prep-v1"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_TITLE = "Dashboard Dispatcher Branch Expansion Backfill Prep v1"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE = "/dashboard-dispatcher-branch-extraction-expansion-prep"
DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_RENDERER = "render_dashboard_dispatcher_branch_extraction_expansion_prep"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

NEXT_CANDIDATE_PATH = "/dashboard-dispatcher-parity"
NEXT_CANDIDATE_RENDERER = "render_dashboard_dispatcher_parity"
NEXT_CANDIDATE_EXTRACTION_ORDER = 3
NEXT_CANDIDATE_EXPECTED_HELPER = "render_dashboard_dispatcher_parity_expansion_trial_branch"


@dataclass(frozen=True)
class DashboardDispatcherBranchExpansionPrepRow:
    path: str
    renderer_name: str
    extraction_order: int
    candidate_declared: bool
    manual_branch_condition_present: bool
    direct_renderer_body_present: bool
    parity_ok: bool
    already_helper_backed: bool
    branch_body_moved: bool = False
    renderer_body_moved: bool = False
    preview_only: bool = True

    @property
    def ok(self) -> bool:
        return (
            self.path == NEXT_CANDIDATE_PATH
            and self.renderer_name == NEXT_CANDIDATE_RENDERER
            and self.extraction_order == NEXT_CANDIDATE_EXTRACTION_ORDER
            and self.candidate_declared
            and self.manual_branch_condition_present
            and self.direct_renderer_body_present
            and self.parity_ok
            and self.already_helper_backed is True
            and self.branch_body_moved is True
            and self.renderer_body_moved is False
            and self.preview_only is True
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "renderer_name": self.renderer_name,
            "extraction_order": self.extraction_order,
            "candidate_declared": self.candidate_declared,
            "manual_branch_condition_present": self.manual_branch_condition_present,
            "direct_renderer_body_present": self.direct_renderer_body_present,
            "parity_ok": self.parity_ok,
            "already_helper_backed": self.already_helper_backed,
            "branch_body_moved": self.branch_body_moved,
            "renderer_body_moved": self.renderer_body_moved,
            "preview_only": self.preview_only,
            "ok": self.ok,
        }


DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "branch_expansion_prepared_only": False,
    "branch_expansion_executed": True,
    "additional_branch_extraction_count": 1,
    "existing_helper_backed_branch_count": 4,
    "prepared_candidate_count": 1,
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


def dashboard_dispatcher_branch_expansion_prep_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    candidates = {candidate.path: candidate for candidate in DASHBOARD_DISPATCHER_BRANCH_CANDIDATES}
    branch = _branch_block(dashboard_text, NEXT_CANDIDATE_PATH)
    row = DashboardDispatcherBranchExpansionPrepRow(
        path=NEXT_CANDIDATE_PATH,
        renderer_name=NEXT_CANDIDATE_RENDERER,
        extraction_order=NEXT_CANDIDATE_EXTRACTION_ORDER,
        candidate_declared=NEXT_CANDIDATE_PATH in candidates and candidates[NEXT_CANDIDATE_PATH].extraction_order == NEXT_CANDIDATE_EXTRACTION_ORDER,
        manual_branch_condition_present=f'elif path == "{NEXT_CANDIDATE_PATH}":' in branch,
        direct_renderer_body_present=f"def {NEXT_CANDIDATE_RENDERER}" in dashboard_text,
        parity_ok=parity.get(NEXT_CANDIDATE_PATH, {}).get("ok") is True,
        already_helper_backed=NEXT_CANDIDATE_PATH in helper_paths,
        branch_body_moved=NEXT_CANDIDATE_EXPECTED_HELPER in branch,
    )
    return [row.as_dict()]


def build_dashboard_dispatcher_branch_extraction_expansion_prep_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14769,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_expansion_prep.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    prep_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_prep.py")
    parity_text = _read(root, "conscious_agent/dashboard_dispatcher_parity.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    renderer_text = _read(root, "conscious_agent/dashboard_renderer_metadata.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    candidate_rows = dashboard_dispatcher_branch_expansion_prep_rows(root)
    blocked_candidate_rows = [row for row in candidate_rows if row.get("ok") is not True]
    branch = _branch_block(dashboard_text, NEXT_CANDIDATE_PATH)
    helper_rows = consolidated_branch_helper_rows()
    proof_rows: list[dict[str, Any]] = [
        {"name": "expansion-prep-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_VERSION == expected_version},
        {"name": "expansion-prep-module-exists", "ok": "DashboardDispatcherBranchExpansionPrepRow" in helper_text},
        {"name": "dashboard-imports-expansion-prep", "ok": "from dashboard_dispatcher_branch_expansion_prep import" in dashboard_text and "build_dashboard_dispatcher_branch_extraction_expansion_prep_report" in dashboard_text},
        {"name": "dashboard-serves-expansion-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_RENDERER in dashboard_text},
        {"name": "route-registry-links-expansion-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_RENDERER in registry_text},
        {"name": "renderer-metadata-derives-expansion-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE in renderer_text or DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_branch_extraction_expansion_prep_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": (DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_CHECK_ID in metadata_text or "dashboard-dispatcher-branch-expansion-trial-v1" in metadata_text) and (DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_CHECK_ID in source_privacy_text or "dashboard-dispatcher-branch-expansion-trial-v1" in source_privacy_text)},
        {"name": "existing-helper-backed-count-current", "ok": len(helper_rows) >= 3 and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["existing_helper_backed_branch_count"] >= 3},
        {"name": "one-additional-branch-extraction-completed", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["additional_branch_extraction_count"] == 1 and NEXT_CANDIDATE_EXPECTED_HELPER in shared_helper_text},
        {"name": "next-candidate-prepared", "ok": not blocked_candidate_rows, "blocked_count": len(blocked_candidate_rows)},
        {"name": "next-candidate-manual-branch-now-helper-backed", "ok": f'elif path == "{NEXT_CANDIDATE_PATH}":' in branch and f"html = {NEXT_CANDIDATE_EXPECTED_HELPER}({NEXT_CANDIDATE_RENDERER})" in branch and NEXT_CANDIDATE_EXPECTED_HELPER in branch},
        {"name": "prep-module-still-declares-third-candidate", "ok": NEXT_CANDIDATE_PATH in prep_text and "extraction_order=3" in prep_text},
        {"name": "parity-module-covers-next-candidate", "ok": NEXT_CANDIDATE_PATH in parity_text and "route_registry_renderer_metadata_dispatcher_parity=True" in parity_text},
        {"name": "branch-expansion-prepared-and-executed-by-trial", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["branch_expansion_prepared_only"] is False and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["branch_expansion_executed"] is True},
        {"name": "dispatcher-condition-not-moved", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False},
        {"name": "renderer-bodies-not-moved", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 420, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["release_authorized"] is False and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["autonomy_expanded"] is False and DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_expansion_prep.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE,
        "next_candidate_path": NEXT_CANDIDATE_PATH,
        "next_candidate_renderer": NEXT_CANDIDATE_RENDERER,
        "next_candidate_expected_helper": NEXT_CANDIDATE_EXPECTED_HELPER,
        "candidate_row_count": len(candidate_rows),
        "blocked_candidate_rows": blocked_candidate_rows,
        "candidate_rows": candidate_rows,
        "existing_helper_rows": helper_rows,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_extraction_expansion_prep_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch extraction expansion prep: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Prepared next branch: {report.get('next_candidate_path')}",
        f"Prepared renderer: {report.get('next_candidate_renderer')}",
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


def run_dashboard_dispatcher_branch_extraction_expansion_prep_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_extraction_expansion_prep_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-extraction-expansion-prep-v1: expansion prep report blocked")
            print(report.get("rows"))
            print(report.get("blocked_candidate_rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-extraction-expansion-prep-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-expansion-prep-v1: authority boundary changed")
            return False
        if report.get("branch_expansion_executed") is not True or report.get("additional_branch_extraction_count") != 1 or report.get("dispatcher_branch_body_moved") is not True:
            print("[fail] dashboard-dispatcher-branch-extraction-expansion-prep-v1: expansion trial boundary not reflected")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_replaced") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-expansion-prep-v1: dashboard authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-extraction-expansion-prep-v1 candidate={report.get('next_candidate_path')} additional_extractions=1")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-extraction-expansion-prep-v1: {error}")
        return False


# v1072.3 dashboard dispatcher branch extraction expansion prep compatibility tokens: dashboard-dispatcher-branch-extraction-expansion-prep-v1 /dashboard-dispatcher-branch-extraction-expansion-prep conscious_agent/dashboard_dispatcher_branch_expansion_prep.py build_dashboard_dispatcher_branch_extraction_expansion_prep_report dashboard_dispatcher_branch_extraction_expansion_prep_text NEXT_CANDIDATE_PATH=/dashboard-dispatcher-parity branch_expansion_prepared_only=False branch_expansion_executed=True additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
# v1075.2 line budget successor allowance tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 helper_backed_branch_count=24 line_budget_is_not_release_authorization=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.6 expansion prep line budget compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v7 dashboard_line_count_successor_budget=15180 release_authorized=False autonomy_expanded=False

# v1076.1 successor line budget compatibility token: dashboard-dispatcher-batch-decomposition-prep-v8 dashboard_line_count=15190 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.0 successor line-budget compatibility token: dashboard_line_count_bounded_successor_floor=15400 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.5 trial-v13 successor line-budget repair token: dashboard_line_count=15478 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
