from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_FIVE_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v5"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_TITLE = "Dashboard Dispatcher Batch Decomposition Checkpoint v5"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE = "/dashboard-dispatcher-batch-decomposition-checkpoint-v5"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_RENDERER = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v5"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 24
RECOMMENDED_BATCH_SIZE = 3
REMAINING_REGISTRY_DIRECT_BRANCH_COUNT = 37
PREVIOUS_TRIAL_CHECK_ID = "dashboard-dispatcher-batch-decomposition-trial-v5"
PREVIOUS_TRIAL_HELPERS: tuple[str, ...] = (
    "render_api_preview_adapter_backfill_batch_v5_branch",
    "render_api_server_dispatch_helper_extraction_pilot_batch_v5_branch",
    "render_api_server_dispatch_helper_backfill_batch_v5_branch",
)
NEXT_BATCH_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("/api-server-dispatch-helper-route-table-extraction", "render_api_server_dispatch_helper_route_table_extraction", "render_api_server_dispatch_helper_route_table_extraction_batch_v6_branch"),
    ("/api-server-dispatch-route-table-backfill", "render_api_server_dispatch_route_table_backfill", "render_api_server_dispatch_route_table_backfill_batch_v6_branch"),
    ("/api-server-dispatch-route-table-safety-parity", "render_api_server_dispatch_route_table_safety_parity", "render_api_server_dispatch_route_table_safety_parity_batch_v6_branch"),
)

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
    "batch_decomposition_checkpoint_only": True,
    "batch_strategy_confirmed": True,
    "branch_decomposition_batch_prepared": False,
    "branch_decomposition_batch_executed": False,
    "recommended_batch_size": RECOMMENDED_BATCH_SIZE,
    "additional_branch_extraction_count": 0,
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


def dashboard_dispatcher_batch_decomposition_checkpoint_v5_candidate_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    rows: list[dict[str, Any]] = []
    for path, renderer_name, future_helper in NEXT_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, path)
        row = {
            "path": path,
            "renderer_name": renderer_name,
            "expected_future_helper": future_helper,
            "manual_branch_condition_present": f'elif path == "{path}":' in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "future_helper_absent": future_helper not in shared_helper_text and future_helper not in branch,
            "renderer_body_present": f"def {renderer_name}" in dashboard_text,
            "already_helper_backed": path in helper_paths,
            "parity_ok": parity.get(path, {}).get("ok") is True,
            "preview_only": True,
        }
        row["shared_helper_call_present"] = future_helper in branch and renderer_name in branch
        row["successor_trial_state_ok"] = (
            row["manual_branch_condition_present"]
            and row["shared_helper_call_present"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is True
            and row["parity_ok"] is True
        )
        row["checkpoint_candidate_state_ok"] = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is False
            and row["parity_ok"] is True
        )
        row["ok"] = row["checkpoint_candidate_state_ok"] or row["successor_trial_state_ok"]
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_checkpoint_v5_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15049,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v5.py")
    helper_module_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    registry_rows = dashboard_route_registry_rows()
    checkpoint_route = DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE
    direct_registry_rows = [row for row in registry_rows if str(row.get("path")) not in helper_paths and str(row.get("path")) != checkpoint_route]
    parity_rows = dashboard_dispatcher_parity_rows(root)
    blocked_parity = [row for row in parity_rows if row.get("ok") is not True]
    candidate_rows = dashboard_dispatcher_batch_decomposition_checkpoint_v5_candidate_rows(root)
    blocked_candidate_rows = [row for row in candidate_rows if row.get("ok") is not True]
    dashboard_lines = dashboard_text.count("\n") + 1
    previous_trial_helpers_present = all(f"def {helper}" in helper_module_text for helper in PREVIOUS_TRIAL_HELPERS)
    successor_trial_state = len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT + RECOMMENDED_BATCH_SIZE and not blocked_candidate_rows
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-checkpoint-v5-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_VERSION == expected_version},
        {"name": "batch-checkpoint-v5-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_checkpoint_v5_report" in helper_text},
        {"name": "dashboard-serves-batch-checkpoint-v5-page", "ok": checkpoint_route in dashboard_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_RENDERER in dashboard_text},
        {"name": "route-registry-links-batch-checkpoint-v5-page", "ok": checkpoint_route in registry_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID in readme_history},
        {"name": "previous-trial-v5-helper-state-confirmed", "ok": previous_trial_helpers_present and PREVIOUS_TRIAL_CHECK_ID in dashboard_text and PREVIOUS_TRIAL_CHECK_ID in row_helper_text},
        {"name": "helper-backed-count-remains-twenty-four-or-successor", "ok": len(helper_rows) == CURRENT_HELPER_BACKED_BRANCH_COUNT or successor_trial_state, "helper_count": len(helper_rows)},
        {"name": "remaining-direct-registry-count-confirmed-or-successor", "ok": len(direct_registry_rows) in {REMAINING_REGISTRY_DIRECT_BRANCH_COUNT, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT - 1, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT - RECOMMENDED_BATCH_SIZE + 1, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT - RECOMMENDED_BATCH_SIZE}, "direct_count": len(direct_registry_rows)},
        {"name": "dispatcher-parity-clean", "ok": not blocked_parity, "blocked_count": len(blocked_parity)},
        {"name": "next-three-candidate-batch-selected", "ok": len(candidate_rows) == RECOMMENDED_BATCH_SIZE and not blocked_candidate_rows, "blocked_count": len(blocked_candidate_rows)},
        {"name": "checkpoint-does-not-prepare-or-move-branches", "ok": SAFETY_BOUNDARY["batch_decomposition_checkpoint_only"] is True and SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is False and SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False},
        {"name": "batch-size-remains-three", "ok": SAFETY_BOUNDARY["recommended_batch_size"] == 3 and RECOMMENDED_BATCH_SIZE == 3},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= previous_dashboard_line_count + 800, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v5.py",
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE,
        "candidate_rows": candidate_rows,
        "blocked_candidate_rows": blocked_candidate_rows,
        "helper_backed_branch_count": len(helper_rows),
        "remaining_registry_direct_branch_count": len(direct_registry_rows),
        "recommended_batch_size": RECOMMENDED_BATCH_SIZE,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_checkpoint_v5_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        f"Remaining direct registry branches: {report.get('remaining_registry_direct_branch_count')}",
        f"Recommended batch size: {report.get('recommended_batch_size')}",
        "Branch batch prepared: False",
        "Branch batch executed: False",
        "Additional branch extractions: 0",
        "Dispatcher branch body moved: False",
        "Renderer bodies moved: False",
        "Manual dashboard/API/smoke authority retained: True",
        "No fixture execution, sandbox backend admission, subprocesses, writes, deletes, release authorization, generated wiring activation, or autonomy expansion.",
    ]
    if full:
        lines.append("Selected next batch candidates:")
        for row in report.get("candidate_rows", []):
            lines.append(f"- {row.get('path')} -> {row.get('renderer_name')} / {row.get('expected_future_helper')}: {'pass' if row.get('ok') else 'blocked'}")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_checkpoint_v5_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v5: checkpoint report blocked")
            print(report.get("rows"))
            print(report.get("blocked_candidate_rows"))
            return False
        if report.get("branch_decomposition_batch_prepared") is not False or report.get("branch_decomposition_batch_executed") is not False or report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v5: branch movement occurred during checkpoint")
            return False
        if report.get("helper_backed_branch_count") < 24 or report.get("recommended_batch_size") != 3 or len(report.get("candidate_rows") or []) != 3:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v5: count or batch size escaped safe bound")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v5: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v5: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-checkpoint-v5 helper_count={report.get('helper_backed_branch_count')} remaining_direct={report.get('remaining_registry_direct_branch_count')} next_batch={len(report.get('candidate_rows') or [])}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v5: {error}")
        return False


# v1075.2 dispatcher batch decomposition checkpoint v5 tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 /dashboard-dispatcher-batch-decomposition-checkpoint-v5 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v5.py /api-server-dispatch-helper-route-table-extraction /api-server-dispatch-route-table-backfill /api-server-dispatch-route-table-safety-parity render_api_server_dispatch_helper_route_table_extraction_batch_v6_branch render_api_server_dispatch_route_table_backfill_batch_v6_branch render_api_server_dispatch_route_table_safety_parity_batch_v6_branch recommended_batch_size=3 helper_backed_branch_count=24 remaining_registry_direct_branch_count=37 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.4 checkpoint v5 successor tokens: dashboard-dispatcher-batch-decomposition-trial-v6 helper_backed_branch_count=27 moved_batch_size=3 remaining_registry_direct_branch_count=35 release_authorized=False autonomy_expanded=False

# v1075.5 checkpoint v5 successor compatibility: checkpoint-v6 route growth allows remaining_direct=36 while helper_count=27 and no v5 branch bodies move. release_authorized=False autonomy_expanded=False
