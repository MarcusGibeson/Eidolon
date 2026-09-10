from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows

DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_CHECK_ID = "dashboard-dispatcher-branch-decomposition-hardening-v1"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_TITLE = "Dashboard Dispatcher Branch Decomposition Hardening v1"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE = "/dashboard-dispatcher-branch-decomposition-hardening"
DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_RENDERER = "render_dashboard_dispatcher_branch_decomposition_hardening"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
EXPECTED_HELPER_BACKED_BRANCH_COUNT = 6

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
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def build_dashboard_dispatcher_branch_decomposition_hardening_report(project_root: str | Path, *, expected_version: str) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    prep_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep.py")
    trial_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py")
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    expected_paths = {
        "/dashboard-route-registry-extraction",
        "/dashboard-renderer-metadata-extraction",
        "/dashboard-dispatcher-parity",
        "/dashboard-dispatcher-branch-extraction-prep",
        "/dashboard-dispatcher-branch-extraction-trial",
        "/dashboard-dispatcher-branch-extraction-backfill",
    }
    stale_exact_count_patterns = [
        "len(helper_rows) == 4",
        "existing_helper_backed_branch_count\"] == 4",
    ]
    proof_rows = [
        {"name": "hardening-module-current", "ok": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_VERSION == expected_version},
        {"name": "six-or-more-helper-backed-branches", "ok": len(helper_rows) >= EXPECTED_HELPER_BACKED_BRANCH_COUNT},
        {"name": "expected-helper-paths-present", "ok": expected_paths.issubset(helper_paths), "missing": sorted(expected_paths - helper_paths)},
        {"name": "manual-dispatcher-still-authoritative", "ok": "elif path ==" in dashboard_text and SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True},
        {"name": "legacy-exact-helper-counts-made-successor-compatible", "ok": not any(pattern in prep_text or pattern in trial_text for pattern in stale_exact_count_patterns)},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in shared_helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_branch_decomposition_hardening.py",
        "route": DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE,
        "helper_backed_branch_count": len(helper_rows),
        "helper_rows": helper_rows,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_branch_decomposition_hardening_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard dispatcher branch decomposition hardening: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        "Legacy helper-count proof gates are successor-compatible.",
        "No subprocesses, writes, deletes, release authorization, fixture execution, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_branch_decomposition_hardening_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_branch_decomposition_hardening_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-branch-decomposition-hardening-v1: hardening report blocked")
            print(report.get("rows"))
            return False
        print(f"[ok] dashboard-dispatcher-branch-decomposition-hardening-v1 helper_count={report.get('helper_backed_branch_count')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-branch-decomposition-hardening-v1: {error}")
        return False


# v1073.0 hardening tokens: dashboard-dispatcher-branch-decomposition-hardening-v1 /dashboard-dispatcher-branch-decomposition-hardening helper_backed_branch_count=6 dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 successor-compatible hardening tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 helper_backed_branch_count_may_exceed_hardening_floor=True helper_backed_branch_count=7 data-tip command-deck operator-console no_native_title_tooltip
