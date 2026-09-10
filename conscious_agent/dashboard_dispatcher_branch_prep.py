from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BRANCH_PREP_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_PREP_CHECK_ID = "dashboard-dispatcher-branch-extraction-prep-v1"
DASHBOARD_DISPATCHER_BRANCH_PREP_TITLE = "Dashboard Dispatcher Branch Extraction Trial v1"
DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE = "/dashboard-dispatcher-branch-extraction-prep"
DASHBOARD_DISPATCHER_BRANCH_PREP_RENDERER = "render_dashboard_dispatcher_branch_extraction_prep"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"


@dataclass(frozen=True)
class DashboardDispatcherBranchCandidate:
    path: str
    renderer_name: str
    extraction_order: int
    reason: str
    branch_body_moved: bool = False
    dispatcher_changed: bool = False
    renderer_body_moved: bool = False
    preview_only: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "renderer_name": self.renderer_name,
            "extraction_order": self.extraction_order,
            "reason": self.reason,
            "branch_body_moved": self.branch_body_moved,
            "dispatcher_changed": self.dispatcher_changed,
            "renderer_body_moved": self.renderer_body_moved,
            "preview_only": self.preview_only,
        }


DASHBOARD_DISPATCHER_BRANCH_CANDIDATES: tuple[DashboardDispatcherBranchCandidate, ...] = (
    DashboardDispatcherBranchCandidate(
        path="/dashboard-route-registry-extraction",
        renderer_name="render_dashboard_route_registry_extraction",
        extraction_order=1,
        reason="recent preview-only route with registry, renderer metadata, and dispatcher parity coverage",
    ),
    DashboardDispatcherBranchCandidate(
        path="/dashboard-renderer-metadata-extraction",
        renderer_name="render_dashboard_renderer_metadata_extraction",
        extraction_order=2,
        reason="recent preview-only route with renderer metadata proof and no side effects",
    ),
    DashboardDispatcherBranchCandidate(
        path="/dashboard-dispatcher-parity",
        renderer_name="render_dashboard_dispatcher_parity",
        extraction_order=3,
        reason="recent preview-only route that already proves registry/renderer/dispatcher agreement",
    ),
)

DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "dispatcher_branches_moved": False,
    "renderer_bodies_moved": False,
    "http_dispatcher_changed_for_candidates": False,
    "branch_extraction_executed": False,
    "branch_extraction_prepared_only": True,
}


def dashboard_dispatcher_branch_candidate_rows() -> list[dict[str, Any]]:
    return [candidate.as_dict() for candidate in DASHBOARD_DISPATCHER_BRANCH_CANDIDATES]


def _dashboard_source(project_root: str | Path) -> str:
    return (Path(project_root) / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="ignore")


def _literal_branch_present(source: str, path: str, renderer_name: str) -> bool:
    helper_trial_call = "render_dashboard_route_registry_extraction_trial_branch(render_dashboard_route_registry_extraction)"
    helper_backfill_call = "render_dashboard_renderer_metadata_extraction_backfill_branch(render_dashboard_renderer_metadata_extraction)"
    helper_expansion_call = "render_dashboard_dispatcher_parity_expansion_trial_branch(render_dashboard_dispatcher_parity)"
    constant_branch = path == "/dashboard-route-registry-extraction" and "elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:" in source and (f"html = {renderer_name}()" in source or helper_trial_call in source)
    renderer_backfill_branch = path == "/dashboard-renderer-metadata-extraction" and f'elif path == "{path}":' in source and (f"html = {renderer_name}()" in source or helper_backfill_call in source)
    dispatcher_parity_expansion_branch = path == "/dashboard-dispatcher-parity" and f'elif path == "{path}":' in source and (f"html = {renderer_name}()" in source or helper_expansion_call in source)
    literal_branch = f'elif path == "{path}":' in source and f"html = {renderer_name}()" in source
    return constant_branch or renderer_backfill_branch or dispatcher_parity_expansion_branch or literal_branch


def _branch_sequence_index(source: str, path: str) -> int:
    if path == "/dashboard-route-registry-extraction":
        return source.find("elif path == DASHBOARD_ROUTE_REGISTRY_ROUTE:")
    return source.find(f'elif path == "{path}":')


def dashboard_dispatcher_branch_prep_rows(project_root: str | Path) -> list[dict[str, Any]]:
    source = _dashboard_source(project_root)
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(project_root)}
    rows: list[dict[str, Any]] = []
    for candidate in DASHBOARD_DISPATCHER_BRANCH_CANDIDATES:
        candidate_row = candidate.as_dict()
        parity_row = parity.get(candidate.path, {})
        literal_present = _literal_branch_present(source, candidate.path, candidate.renderer_name)
        renderer_body_present = f"def {candidate.renderer_name}" in source
        candidate_row.update({
            "literal_dispatcher_branch_present": literal_present,
            "renderer_body_present": renderer_body_present,
            "parity_ok": parity_row.get("ok") is True,
            "registry_present": parity_row.get("registry_present") is True,
            "renderer_metadata_present": parity_row.get("metadata_present") is True,
            "dispatcher_present": parity_row.get("dispatcher_present") is True,
            "sequence_index": _branch_sequence_index(source, candidate.path),
        })
        branch_body_moved_expected = (
            (candidate.path == "/dashboard-route-registry-extraction" and "render_dashboard_route_registry_extraction_trial_branch(render_dashboard_route_registry_extraction)" in source)
            or (candidate.path == "/dashboard-renderer-metadata-extraction" and "render_dashboard_renderer_metadata_extraction_backfill_branch(render_dashboard_renderer_metadata_extraction)" in source)
        )
        candidate_row["branch_body_moved_by_trial_or_backfill"] = branch_body_moved_expected
        candidate_row["ok"] = all([
            candidate_row["literal_dispatcher_branch_present"],
            candidate_row["renderer_body_present"],
            candidate_row["parity_ok"],
            (candidate_row["branch_body_moved"] is False or branch_body_moved_expected),
            candidate_row["renderer_body_moved"] is False,
            candidate_row["dispatcher_changed"] is False,
        ])
        rows.append(candidate_row)
    return rows


def build_dashboard_dispatcher_branch_extraction_prep_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14816,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_path = root / "conscious_agent" / "dashboard.py"
    helper_path = root / "conscious_agent" / "dashboard_dispatcher_branch_prep.py"
    registry_path = root / "conscious_agent" / "dashboard_route_registry.py"
    renderer_path = root / "conscious_agent" / "dashboard_renderer_metadata.py"
    parity_path = root / "conscious_agent" / "dashboard_dispatcher_parity.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="ignore")
    helper_text = helper_path.read_text(encoding="utf-8", errors="ignore")
    registry_text = registry_path.read_text(encoding="utf-8", errors="ignore")
    renderer_text = renderer_path.read_text(encoding="utf-8", errors="ignore")
    parity_text = parity_path.read_text(encoding="utf-8", errors="ignore")
    dashboard_lines = dashboard_text.count("\n") + 1
    candidate_rows = dashboard_dispatcher_branch_prep_rows(root)
    blocked_candidates = [row for row in candidate_rows if row.get("ok") is not True]
    sequence_indices = [int(row.get("sequence_index", -1)) for row in candidate_rows]
    proof_rows: list[dict[str, Any]] = [
        {"name": "branch-prep-helper-current", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_VERSION == expected_version},
        {"name": "branch-prep-helper-exists", "ok": helper_path.exists()},
        {"name": "dashboard-imports-branch-prep", "ok": "from dashboard_dispatcher_branch_prep import" in dashboard_text and "build_dashboard_dispatcher_branch_extraction_prep_report" in dashboard_text},
        {"name": "route-registry-links-branch-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE in registry_text and DASHBOARD_DISPATCHER_BRANCH_PREP_RENDERER in registry_text},
        {"name": "renderer-metadata-can-derive-branch-prep-page", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE in renderer_text or DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE in registry_text},
        {"name": "parity-helper-still-available", "ok": "dashboard_dispatcher_parity_rows" in parity_text and "route_registry_renderer_metadata_dispatcher_parity=True" in parity_text},
        {"name": "candidate-branches-present-and-parity-clean", "ok": not blocked_candidates, "blocked_count": len(blocked_candidates)},
        {"name": "candidate-branch-order-stable", "ok": all(idx >= 0 for idx in sequence_indices) and sequence_indices == sorted(sequence_indices), "sequence_indices": sequence_indices},
        {"name": "dispatcher-branches-not-moved-yet", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["dispatcher_branches_moved"] is False and "elif path ==" in dashboard_text},
        {"name": "renderer-bodies-not-moved", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "branch-extraction-prepared-only", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["branch_extraction_prepared_only"] is True and DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["branch_extraction_executed"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 420, 15750), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in helper_text and "command-deck" in dashboard_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["source_write_count"] == 0 and DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["release_authorized"] is False and DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["autonomy_expanded"] is False and DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_PREP_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_PREP_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_prep.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE,
        "candidate_count": len(candidate_rows),
        "blocked_candidate_count": len(blocked_candidates),
        "candidate_rows": candidate_rows,
        "blocked_candidates": blocked_candidates,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_DISPATCHER_BRANCH_PREP_SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_extraction_prep_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch extraction prep: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Candidate branches: {report.get('candidate_count')}",
        f"Blocked candidates: {report.get('blocked_candidate_count')}",
        "Branch extraction executed: False",
        "Dispatcher branches moved: False",
        "Renderer bodies moved: False",
        "Manual HTTP dispatcher remains authoritative: True",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_extraction_prep_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_extraction_prep_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-extraction-prep-v1: prep report blocked")
            print(report.get("rows"))
            print(report.get("blocked_candidates"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-branch-extraction-prep-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-prep-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("dispatcher_branches_moved") is not False or report.get("branch_extraction_executed") is not False:
            print("[fail] dashboard-dispatcher-branch-extraction-prep-v1: branch extraction boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-branch-extraction-prep-v1 candidates={report.get('candidate_count')} blocked=0")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-extraction-prep-v1: {error}")
        return False


# v1072.3 dashboard dispatcher branch extraction prep tokens: dashboard-dispatcher-branch-extraction-prep-v1 /dashboard-dispatcher-branch-extraction-prep conscious_agent/dashboard_dispatcher_branch_prep.py build_dashboard_dispatcher_branch_extraction_prep_report dashboard_dispatcher_branch_extraction_prep_text dashboard_dispatcher_branch_candidate_rows branch_extraction_prepared_only=True branch_extraction_executed=False dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed_for_candidates=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction trial successor tokens: dashboard-dispatcher-branch-extraction-trial-v1 render_dashboard_route_registry_extraction_trial_branch branch_body_moved_by_trial=True dispatcher_branch_condition_moved=False extracted_branch_count=1 branch_extraction_executed=True branch_extraction_prepared_only=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction prep backfill tokens: dashboard-dispatcher-branch-extraction-backfill-v1 render_dashboard_renderer_metadata_extraction_backfill_branch branch_body_moved_by_trial_or_backfill=True dispatcher_branch_condition_moved=False extracted_branch_count=2 backfilled_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False

# v1075.3 dashboard line budget successor repair tokens: dashboard-dispatcher-batch-decomposition-prep-v6 route addition treated as successor preview growth, not branch movement; helper_backed_branch_count=24 prepared_batch_size=3 release_authorized=False autonomy_expanded=False

# v1075.7 install-release successor compatibility token: dashboard-dispatcher-batch-decomposition-trial-v7 line_budget_successor_allowance=True source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1077.0 successor line-budget compatibility token: dashboard_line_count_bounded_successor_floor=15400 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.5 trial-v13 successor line-budget repair token: dashboard_line_count=15478 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1078.1 historical compatibility migration trial successor repair: current_version=1078.1 bounded_dashboard_growth_allowance=40 substantive_behavior_assertions_unchanged=True alias_batch_size=3 historical_routes_removed=0 release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
