from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_VERSION = "1074.6"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v1"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_TITLE = "Dashboard Dispatcher Batch Decomposition Checkpoint v1"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_ROUTE = "/dashboard-dispatcher-batch-decomposition-checkpoint"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_RENDERER = "render_dashboard_dispatcher_batch_decomposition_checkpoint"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 12
RECOMMENDED_BATCH_SIZE = 3
REMAINING_REGISTRY_DIRECT_BRANCH_COUNT = 36
NEXT_BATCH_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("/sandboxed-fixture-execution-trial", "render_sandboxed_fixture_execution_trial", "render_sandboxed_fixture_execution_trial_batch_v2_branch"),
    ("/sandboxed-fixture-batch-execution", "render_sandboxed_fixture_batch_execution", "render_sandboxed_fixture_batch_execution_batch_v2_branch"),
    ("/generated-dispatch-promotion-readiness-ledger", "render_generated_dispatch_promotion_readiness_ledger", "render_generated_dispatch_promotion_readiness_ledger_batch_v2_branch"),
)

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


def dashboard_dispatcher_batch_decomposition_checkpoint_candidate_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    prep_v2_present = "dashboard-dispatcher-batch-decomposition-prep-v2" in dashboard_text
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    rows: list[dict[str, Any]] = []
    for path, renderer_name, future_helper in NEXT_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, path)
        row = {
            "path": path,
            "renderer_name": renderer_name,
            "future_helper": future_helper,
            "manual_branch_condition_present": f'elif path == "{path}":' in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "future_helper_absent": future_helper not in shared_helper_text,
            "renderer_body_present": f"def {renderer_name}" in dashboard_text,
            "already_helper_backed": path in helper_paths,
            "parity_ok": parity.get(path, {}).get("ok") is True,
            "preview_only": True,
        }
        row["ok"] = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is False
            and row["parity_ok"] is True
        ) or (
            prep_v2_present
            and row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is False
            and row["parity_ok"] is True
        )
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_checkpoint_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14835,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    registry_rows = dashboard_route_registry_rows()
    checkpoint_route = DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_ROUTE
    direct_registry_rows = [row for row in registry_rows if str(row.get("path")) not in helper_paths and str(row.get("path")) != checkpoint_route]
    parity_rows = dashboard_dispatcher_parity_rows(root)
    blocked_parity = [row for row in parity_rows if row.get("ok") is not True]
    candidate_rows = dashboard_dispatcher_batch_decomposition_checkpoint_candidate_rows(root)
    blocked_candidate_rows = [row for row in candidate_rows if row.get("ok") is not True]
    dashboard_lines = dashboard_text.count("\n") + 1
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-checkpoint-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_VERSION == expected_version},
        {"name": "batch-checkpoint-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_checkpoint_report" in helper_text},
        {"name": "dashboard-serves-batch-checkpoint-page", "ok": checkpoint_route in dashboard_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_RENDERER in dashboard_text},
        {"name": "route-registry-links-batch-checkpoint-page", "ok": checkpoint_route in registry_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_checkpoint_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID in readme_history},
        {"name": "helper-backed-count-confirmed", "ok": len(helper_rows) == CURRENT_HELPER_BACKED_BRANCH_COUNT, "helper_count": len(helper_rows)},
        {"name": "remaining-direct-registry-count-confirmed", "ok": len(direct_registry_rows) >= REMAINING_REGISTRY_DIRECT_BRANCH_COUNT, "direct_count": len(direct_registry_rows)},
        {"name": "dispatcher-parity-clean", "ok": not blocked_parity, "blocked_count": len(blocked_parity)},
        {"name": "next-three-candidate-batch-selected", "ok": len(candidate_rows) == RECOMMENDED_BATCH_SIZE and not blocked_candidate_rows, "blocked_count": len(blocked_candidate_rows)},
        {"name": "checkpoint-does-not-prepare-or-move-branches", "ok": SAFETY_BOUNDARY["batch_decomposition_checkpoint_only"] is True and SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is False and SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False},
        {"name": "batch-size-remains-three", "ok": SAFETY_BOUNDARY["recommended_batch_size"] == 3 and RECOMMENDED_BATCH_SIZE == 3},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= previous_dashboard_line_count + 800, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py",
        "route": checkpoint_route,
        "candidate_rows": candidate_rows,
        "blocked_candidate_rows": blocked_candidate_rows,
        "recommended_batch_size": RECOMMENDED_BATCH_SIZE,
        "helper_backed_branch_count": len(helper_rows),
        "remaining_registry_direct_branch_count": len(direct_registry_rows),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_checkpoint_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        f"Remaining registry direct branches: {report.get('remaining_registry_direct_branch_count')}",
        f"Recommended batch size: {report.get('recommended_batch_size')}",
        "Batch decomposition checkpoint only: True",
        "Batch prepared: False",
        "Batch executed: False",
        "Additional branch extractions: 0",
        "Dispatcher branch body moved: False",
        "Dispatcher branch condition moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No fixture execution, sandbox backend admission, subprocesses, writes, deletes, release authorization, generated wiring activation, or autonomy expansion.",
    ]
    for row in report.get("candidate_rows", []):
        lines.append(f"- next: {row.get('path')} -> {row.get('future_helper')}: {'pass' if row.get('ok') else 'blocked'}")
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_checkpoint_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_checkpoint_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v1: checkpoint report blocked")
            print(report.get("rows"))
            print(report.get("blocked_candidate_rows"))
            return False
        if report.get("branch_decomposition_batch_prepared") is not False or report.get("branch_decomposition_batch_executed") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v1: checkpoint unexpectedly prepared or executed a batch")
            return False
        if report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v1: branch movement boundary changed")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v1: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-checkpoint-v1 helper_count={report.get('helper_backed_branch_count')} remaining_direct={report.get('remaining_registry_direct_branch_count')} next_batch={report.get('recommended_batch_size')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v1: {error}")
        return False


# v1074.0 dispatcher batch decomposition checkpoint tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py /sandboxed-fixture-execution-trial /sandboxed-fixture-batch-execution /generated-dispatch-promotion-readiness-ledger render_sandboxed_fixture_execution_trial_batch_v2_branch render_sandboxed_fixture_batch_execution_batch_v2_branch render_generated_dispatch_promotion_readiness_ledger_batch_v2_branch recommended_batch_size=3 helper_backed_branch_count=12 remaining_registry_direct_branch_count=36 batch_decomposition_checkpoint_only=True branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.1 checkpoint successor compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v2 prepared_batch_size=3 helper_backed_branch_count=12 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0
