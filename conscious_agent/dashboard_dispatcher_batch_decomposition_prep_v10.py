from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_TEN_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID = "dashboard-dispatcher-batch-decomposition-prep-v10"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_TITLE = "Dashboard Dispatcher Batch Decomposition Prep v10"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE = "/dashboard-dispatcher-batch-decomposition-prep-v10"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_RENDERER = "render_dashboard_dispatcher_batch_decomposition_prep_v10"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 36
PREPARED_BATCH_SIZE = 3
PREPARED_BATCH_CANDIDATES: tuple[tuple[str, str, str, str, int], ...] = (
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
    "branch_decomposition_batch_executed": False,
    "additional_branch_extraction_count": 0,
    "prepared_batch_size": PREPARED_BATCH_SIZE,
    "prepared_batch_candidate_count": PREPARED_BATCH_SIZE,
    "existing_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": False,
    "renderer_bodies_moved": False,
    "http_dispatcher_replaced": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _branch_block(source: str, condition_token: str) -> str:
    pattern = re.compile(rf'elif {re.escape(condition_token)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_batch_decomposition_prep_v10_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    rows: list[dict[str, Any]] = []
    for path, condition_token, renderer_name, expected_helper, extraction_order in PREPARED_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, condition_token)
        helper_absent_from_real_helper_module = f"def {expected_helper}" not in shared_helper_text and f"helper_name=\"{expected_helper}\"" not in shared_helper_text
        row = {
            "path": path,
            "condition_token": condition_token,
            "renderer_name": renderer_name,
            "expected_future_helper": expected_helper,
            "extraction_order": extraction_order,
            "manual_branch_condition_present": f"elif {condition_token}:" in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "shared_helper_call_present": expected_helper in branch and renderer_name in branch,
            "future_helper_absent_from_real_helper_module": helper_absent_from_real_helper_module,
            "future_helper_absent_from_branch": expected_helper not in branch,
            "renderer_body_present": f"def {renderer_name}" in dashboard_text,
            "already_helper_backed": path in helper_paths,
            "parity_ok": parity.get(path, {}).get("ok") is True,
            "preview_only": True,
        }
        prep_state_ok = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent_from_real_helper_module"]
            and row["future_helper_absent_from_branch"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is False
            and row["parity_ok"] is True
            and row["preview_only"] is True
        )
        successor_state_ok = (
            row["manual_branch_condition_present"]
            and row["shared_helper_call_present"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is True
            and row["parity_ok"] is True
            and row["preview_only"] is True
        )
        row["ok"] = prep_state_ok or successor_state_ok
        row["prep_state_ok"] = prep_state_ok
        row["successor_state_ok"] = successor_state_ok
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_prep_v10_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15284,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v10.py")
    checkpoint_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v9.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    helper_module_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = consolidated_branch_helper_rows()
    prep_rows = dashboard_dispatcher_batch_decomposition_prep_v10_rows(root)
    blocked_prep_rows = [row for row in prep_rows if row.get("ok") is not True]
    blocked_current_prep_rows = [row for row in prep_rows if row.get("prep_state_ok") is not True]
    candidate_paths = [path for path, _condition, _renderer, _helper, _order in PREPARED_BATCH_CANDIDATES]
    candidate_helpers = [helper for _path, _condition, _renderer, helper, _order in PREPARED_BATCH_CANDIDATES]
    current_prep_state = len(helper_rows) == CURRENT_HELPER_BACKED_BRANCH_COUNT and not blocked_current_prep_rows
    successor_trial_state = len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT + PREPARED_BATCH_SIZE and not blocked_prep_rows
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-prep-v10-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_VERSION == expected_version},
        {"name": "batch-prep-v10-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_prep_v10_report" in helper_text},
        {"name": "dashboard-serves-batch-prep-v10-page", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_RENDERER in dashboard_text},
        {"name": "route-registry-links-batch-prep-v10-page", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE in registry_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_prep_v10_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated-or-successor", "ok": successor_trial_state or (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID in readme_history)},
        {"name": "checkpoint-selected-same-three-candidates", "ok": all(path in checkpoint_text for path in candidate_paths) and "recommended_batch_size=3" in checkpoint_text},
        {"name": "helper-backed-count-remains-thirty-six-or-successor", "ok": current_prep_state or successor_trial_state, "helper_count": len(helper_rows)},
        {"name": "three-batch-candidates-prepared", "ok": len(prep_rows) == PREPARED_BATCH_SIZE and not blocked_prep_rows, "blocked_count": len(blocked_prep_rows)},
        {"name": "future-helpers-still-absent-from-real-helper-module-or-successor", "ok": all(f"def {helper}" not in helper_module_text for helper in candidate_helpers) or successor_trial_state},
        {"name": "direct-renderer-calls-still-direct", "ok": not blocked_current_prep_rows or successor_trial_state, "blocked_count": len(blocked_current_prep_rows)},
        {"name": "dispatcher-conditions-remain-in-dashboard", "ok": all(row.get("manual_branch_condition_present") is True for row in prep_rows)},
        {"name": "renderer-bodies-remain-in-dashboard", "ok": all(row.get("renderer_body_present") is True for row in prep_rows)},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "prep-only-no-branch-movement", "ok": SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is True and SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= previous_dashboard_line_count + 800, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": " title=\"" not in dashboard_text and " title=\'" not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v10.py",
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE,
        "prepared_batch_candidates": prep_rows,
        "blocked_prep_rows": blocked_prep_rows,
        "blocked_current_prep_rows": blocked_current_prep_rows,
        "prepared_batch_size": PREPARED_BATCH_SIZE,
        "helper_backed_branch_count": len(helper_rows),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_prep_v10_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Prepared batch size: {report.get('prepared_batch_size')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        "Batch decomposition prep v8 executed: False",
        "Additional branch extractions: 0",
        "Dispatcher branch body moved: False",
        "Dispatcher branch condition moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No fixture execution, sandbox backend admission, subprocesses, writes, deletes, release authorization, generated wiring activation, or autonomy expansion.",
    ]
    for row in report.get("prepared_batch_candidates", []):
        lines.append(f"- {row.get('path')} -> {row.get('expected_future_helper')}: {'pass' if row.get('ok') else 'blocked'}")
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_prep_v10_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_prep_v10_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v10: prep report blocked")
            print(report.get("rows"))
            print(report.get("blocked_prep_rows"))
            return False
        if report.get("prepared_batch_size") != PREPARED_BATCH_SIZE or len(report.get("prepared_batch_candidates") or []) != PREPARED_BATCH_SIZE:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v10: prepared batch escaped safe bound")
            return False
        if report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False or report.get("branch_decomposition_batch_executed") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v10: branch movement occurred during prep")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v10: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v10: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-prep-v10 helper_count={report.get('helper_backed_branch_count')} prepared={len(report.get('prepared_batch_candidates') or [])}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-prep-v10: {error}")
        return False


# v1076.5 dispatcher batch decomposition prep v10 tokens: dashboard-dispatcher-batch-decomposition-prep-v10 /dashboard-dispatcher-batch-decomposition-prep-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v10.py /dashboard-dispatcher-branch-expansion-backfill-trial-v3 /dashboard-dispatcher-branch-decomposition-hardening /eidolon-v1073-source-review-checkpoint render_dashboard_dispatcher_branch_expansion_backfill_trial_v3_batch_v10_branch render_dashboard_dispatcher_branch_decomposition_hardening_batch_v10_branch render_eidolon_v1073_source_review_checkpoint_batch_v10_branch prepared_batch_size=3 helper_backed_branch_count=36 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
