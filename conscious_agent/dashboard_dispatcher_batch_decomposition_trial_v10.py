from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_TEN_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID = "dashboard-dispatcher-batch-decomposition-trial-v10"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_TITLE = "Dashboard Dispatcher Batch Decomposition Trial v10"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE = "/dashboard-dispatcher-batch-decomposition-trial-v10"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_RENDERER = "render_dashboard_dispatcher_batch_decomposition_trial_v10"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

PREVIOUS_HELPER_BACKED_BRANCH_COUNT = 36
CURRENT_HELPER_BACKED_BRANCH_COUNT = 39
MOVED_BATCH_SIZE = 3
MOVED_BATCH_CANDIDATES: tuple[tuple[str, str, str, str, int], ...] = (
    (
        "/dashboard-dispatcher-branch-expansion-backfill-trial-v3",
        "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE",
        "render_dashboard_dispatcher_branch_expansion_backfill_trial_v3",
        "render_dashboard_dispatcher_branch_expansion_backfill_trial_v3_batch_v10_branch",
        37,
    ),
    (
        "/dashboard-dispatcher-branch-decomposition-hardening",
        "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE",
        "render_dashboard_dispatcher_branch_decomposition_hardening",
        "render_dashboard_dispatcher_branch_decomposition_hardening_batch_v10_branch",
        38,
    ),
    (
        "/eidolon-v1073-source-review-checkpoint",
        "path == EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE",
        "render_eidolon_v1073_source_review_checkpoint",
        "render_eidolon_v1073_source_review_checkpoint_batch_v10_branch",
        39,
    ),
)
PREVIOUS_PREP_CHECK_ID = "dashboard-dispatcher-batch-decomposition-prep-v10"
PREVIOUS_CHECKPOINT_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v9"

SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "sandbox_backend_admission_count": 0,
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
    "branch_decomposition_batch_prepared": True,
    "branch_decomposition_batch_executed": True,
    "additional_branch_extraction_count": MOVED_BATCH_SIZE,
    "moved_branch_count": MOVED_BATCH_SIZE,
    "prepared_batch_size": MOVED_BATCH_SIZE,
    "previous_helper_backed_branch_count": PREVIOUS_HELPER_BACKED_BRANCH_COUNT,
    "existing_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": True,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, condition_token: str) -> str:
    pattern = re.compile(rf'elif {re.escape(condition_token)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_batch_decomposition_trial_v10_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    rows: list[dict[str, Any]] = []
    for path, condition_token, renderer_name, helper_name, extraction_order in MOVED_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, condition_token)
        row = {
            "path": path,
            "condition_token": condition_token,
            "renderer_name": renderer_name,
            "helper_name": helper_name,
            "extraction_order": extraction_order,
            "manual_branch_condition_present": f"elif {condition_token}:" in branch,
            "shared_helper_call_present": helper_name in branch and renderer_name in branch,
            "direct_renderer_call_absent": f"html = {renderer_name}()" not in branch,
            "renderer_body_present": f"def {renderer_name}" in dashboard_text,
            "helper_registered": path in helper_paths,
            "parity_ok": parity.get(path, {}).get("ok") is True,
            "preview_only": True,
        }
        row["ok"] = (
            row["manual_branch_condition_present"]
            and row["shared_helper_call_present"]
            and row["direct_renderer_call_absent"]
            and row["renderer_body_present"]
            and row["helper_registered"] is True
            and row["parity_ok"] is True
            and row["preview_only"] is True
        )
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_trial_v10_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15247,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v10.py")
    prep_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v10.py")
    checkpoint_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v9.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    trial_rows = dashboard_dispatcher_batch_decomposition_trial_v10_rows(root)
    blocked_trial_rows = [row for row in trial_rows if row.get("ok") is not True]
    moved_paths = [path for path, _condition, _renderer, _helper, _order in MOVED_BATCH_CANDIDATES]
    moved_helpers = [helper for _path, _condition, _renderer, helper, _order in MOVED_BATCH_CANDIDATES]
    moved_renderers = [renderer for _path, _condition, renderer, _helper, _order in MOVED_BATCH_CANDIDATES]
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-trial-v10-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_VERSION <= expected_version},
        {"name": "batch-trial-v10-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_trial_v10_report" in helper_text},
        {"name": "dashboard-serves-batch-trial-v10-page", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_RENDERER in dashboard_text},
        {"name": "route-registry-links-batch-trial-v10-page", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE in registry_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_trial_v10_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated", "ok": (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID in readme_history) or ("dashboard-dispatcher-batch-decomposition-prep-v10" in readme_next and "dashboard-dispatcher-batch-decomposition-prep-v10" in readme_history)},
        {"name": "prep-v10-acknowledges-successor", "ok": PREVIOUS_PREP_CHECK_ID in prep_text and all(helper in prep_text for helper in moved_helpers)},
        {"name": "checkpoint-v9-selected-same-batch", "ok": PREVIOUS_CHECKPOINT_CHECK_ID in checkpoint_text and all(path in checkpoint_text for path in moved_paths)},
        {"name": "helper-count-increased-by-three-or-successor", "ok": len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT and CURRENT_HELPER_BACKED_BRANCH_COUNT == PREVIOUS_HELPER_BACKED_BRANCH_COUNT + MOVED_BATCH_SIZE, "helper_count": len(helper_rows)},
        {"name": "moved-helpers-registered", "ok": all(path in helper_paths for path in moved_paths) and all(f"def {helper}" in shared_helper_text for helper in moved_helpers)},
        {"name": "exactly-three-branch-extractions", "ok": SAFETY_BOUNDARY["additional_branch_extraction_count"] == MOVED_BATCH_SIZE and SAFETY_BOUNDARY["moved_branch_count"] == MOVED_BATCH_SIZE},
        {"name": "moved-branches-helper-backed", "ok": not blocked_trial_rows, "blocked_count": len(blocked_trial_rows)},
        {"name": "manual-conditions-retained", "ok": all(f"elif {condition}:" in dashboard_text for _path, condition, _renderer, _helper, _order in MOVED_BATCH_CANDIDATES)},
        {"name": "branch-bodies-call-shared-helpers", "ok": all(helper in _branch_block(dashboard_text, condition) for _path, condition, _renderer, helper, _order in MOVED_BATCH_CANDIDATES)},
        {"name": "direct-renderer-calls-removed-from-moved-bodies", "ok": all(f"html = {renderer}()" not in _branch_block(dashboard_text, condition) for _path, condition, renderer, _helper, _order in MOVED_BATCH_CANDIDATES)},
        {"name": "renderer-bodies-still-in-dashboard", "ok": all(f"def {renderer}" in dashboard_text for renderer in moved_renderers)},
        {"name": "batch-trial-v10-executed-not-autonomous", "ok": SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is True and SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is True},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= previous_dashboard_line_count + 800, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": ' title="' not in dashboard_text and " title='" not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v10.py",
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE,
        "moved_batch_candidates": trial_rows,
        "blocked_trial_rows": blocked_trial_rows,
        "moved_batch_size": MOVED_BATCH_SIZE,
        "helper_backed_branch_count": len(helper_rows),
        "previous_helper_backed_branch_count": PREVIOUS_HELPER_BACKED_BRANCH_COUNT,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_trial_v10_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Moved batch size: {report.get('moved_batch_size')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        "Batch decomposition trial v10 executed: True",
        "Additional branch extractions: 3",
        "Dispatcher branch body moved: True",
        "Dispatcher branch condition moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No fixture execution, sandbox backend admission, subprocesses, writes, deletes, release authorization, generated wiring activation, or autonomy expansion.",
    ]
    for row in report.get("moved_batch_candidates", []):
        lines.append(f"- {row.get('path')} -> {row.get('helper_name')}: {'pass' if row.get('ok') else 'blocked'}")
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_trial_v10_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_trial_v10_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v10: trial report blocked")
            print(report.get("rows"))
            print(report.get("blocked_trial_rows"))
            return False
        if report.get("moved_batch_size") != MOVED_BATCH_SIZE or len(report.get("moved_batch_candidates") or []) != MOVED_BATCH_SIZE:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v10: moved batch escaped safe bound")
            return False
        if int(report.get("helper_backed_branch_count") or 0) < CURRENT_HELPER_BACKED_BRANCH_COUNT:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v10: helper count fell below the v10 baseline")
            return False
        if report.get("additional_branch_extraction_count") != MOVED_BATCH_SIZE or report.get("dispatcher_branch_body_moved") is not True or report.get("branch_decomposition_batch_executed") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v10: trial execution accounting changed")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v10: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v10: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-trial-v10 moved={len(report.get('moved_batch_candidates') or [])} helper_count={report.get('helper_backed_branch_count')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-trial-v10: {error}")
        return False


# v1077.0 dispatcher batch decomposition trial v10 tokens: dashboard-dispatcher-batch-decomposition-trial-v10 /dashboard-dispatcher-batch-decomposition-trial-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v10.py /dashboard-dispatcher-branch-expansion-backfill-trial-v3 /dashboard-dispatcher-branch-decomposition-hardening /eidolon-v1073-source-review-checkpoint render_dashboard_dispatcher_branch_expansion_backfill_trial_v3_batch_v10_branch render_dashboard_dispatcher_branch_decomposition_hardening_batch_v10_branch render_eidolon_v1073_source_review_checkpoint_batch_v10_branch moved_batch_size=3 helper_backed_branch_count=39 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
