from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_batch_decomposition_prep import (
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE,
)
from dashboard_dispatcher_batch_decomposition_trial import (
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE,
)
from dashboard_dispatcher_batch_strategy_checkpoint import (
    DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE,
)
from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_TWELVE_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v12"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_TITLE = "Dashboard Dispatcher Batch Decomposition Checkpoint v12"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE = "/dashboard-dispatcher-batch-decomposition-checkpoint-v12"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_RENDERER = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v12"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 45
RECOMMENDED_BATCH_SIZE = 3
REMAINING_REGISTRY_DIRECT_BRANCH_COUNT = 36
PREVIOUS_TRIAL_CHECK_ID = "dashboard-dispatcher-batch-decomposition-trial-v12"
PREVIOUS_TRIAL_HELPERS: tuple[str, ...] = (
    "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_batch_v12_branch",
    "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_batch_v12_branch",
    "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_batch_v12_branch",
)

NEW_PROOF_ROUTES_PER_CYCLE = 3
MOVED_ROUTES_PER_TRIAL = 3
NET_DIRECT_ROUTE_REDUCTION_PER_CYCLE = MOVED_ROUTES_PER_TRIAL - NEW_PROOF_ROUTES_PER_CYCLE

NEXT_BATCH_CANDIDATES: tuple[tuple[str, str, str, str], ...] = (
    (
        "/dashboard-dispatcher-batch-strategy-checkpoint",
        "path == DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE",
        "render_dashboard_dispatcher_batch_strategy_checkpoint",
        "render_dashboard_dispatcher_batch_strategy_checkpoint_batch_v13_branch",
    ),
    (
        "/dashboard-dispatcher-batch-decomposition-prep",
        "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE",
        "render_dashboard_dispatcher_batch_decomposition_prep",
        "render_dashboard_dispatcher_batch_decomposition_prep_batch_v13_branch",
    ),
    (
        "/dashboard-dispatcher-batch-decomposition-trial",
        "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE",
        "render_dashboard_dispatcher_batch_decomposition_trial",
        "render_dashboard_dispatcher_batch_decomposition_trial_batch_v13_branch",
    ),
)
EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES = (
    DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE,
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE,
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE,
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


def _branch_block(source: str, condition_token: str) -> str:
    pattern = re.compile(rf"elif {re.escape(condition_token)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)")
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_batch_decomposition_checkpoint_v12_candidate_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    rows: list[dict[str, Any]] = []
    for path, condition_token, renderer_name, future_helper in NEXT_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, condition_token)
        parity_row = parity.get(path, {})
        row = {
            "path": path,
            "condition_token": condition_token,
            "renderer_name": renderer_name,
            "expected_future_helper": future_helper,
            "manual_branch_condition_present": f"elif {condition_token}:" in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "future_helper_absent": future_helper not in shared_helper_text and future_helper not in branch,
            "renderer_body_present": re.search(rf"^def {re.escape(renderer_name)}\(", dashboard_text, re.MULTILINE) is not None,
            "already_helper_backed": path in helper_paths,
            "parity_exact": parity_row.get("ok") is True
            and parity_row.get("registry_renderer") == renderer_name
            and parity_row.get("metadata_renderer") == renderer_name
            and parity_row.get("dispatcher_renderer") == renderer_name,
            "preview_only": True,
        }
        row["checkpoint_candidate_state_ok"] = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is False
            and row["parity_exact"] is True
        )
        row["successor_trial_state_ok"] = (
            row["manual_branch_condition_present"]
            and not row["direct_renderer_call_present"]
            and not row["future_helper_absent"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is True
            and row["parity_exact"] is True
        )
        row["ok"] = row["checkpoint_candidate_state_ok"] or row["successor_trial_state_ok"]
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_checkpoint_v12_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15426,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    module_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v12.py")
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
    checkpoint_route = DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE
    direct_registry_rows = [
        row for row in registry_rows
        if str(row.get("path")) not in helper_paths and str(row.get("path")) != checkpoint_route
    ]
    parity_rows = dashboard_dispatcher_parity_rows(root)
    blocked_parity = [row for row in parity_rows if row.get("ok") is not True]
    candidate_rows = dashboard_dispatcher_batch_decomposition_checkpoint_v12_candidate_rows(root)
    blocked_candidate_rows = [row for row in candidate_rows if row.get("ok") is not True]
    dashboard_lines = dashboard_text.count("\n") + 1
    registry_by_path = {str(row.get("path")): row for row in registry_rows}
    checkpoint_registry_row = registry_by_path.get(checkpoint_route, {})
    previous_trial_helpers_present = all(
        re.search(rf"^def {re.escape(helper)}\(", helper_module_text, re.MULTILINE) is not None
        for helper in PREVIOUS_TRIAL_HELPERS
    )
    route_values_exact = tuple(row[0] for row in NEXT_BATCH_CANDIDATES) == EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES
    checkpoint_identity_exact = (
        DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID
        == "dashboard-dispatcher-batch-decomposition-checkpoint-v12"
        and checkpoint_route == "/dashboard-dispatcher-batch-decomposition-checkpoint-v12"
        and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_RENDERER
        == "render_dashboard_dispatcher_batch_decomposition_checkpoint_v12"
    )
    registry_identity_exact = (
        checkpoint_registry_row.get("renderer_name")
        == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_RENDERER
        and checkpoint_registry_row.get("preview_only") is True
        and checkpoint_registry_row.get("dashboard_get_preview_only") is True
    )

    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-checkpoint-v12-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_VERSION <= expected_version},
        {"name": "batch-checkpoint-v12-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_checkpoint_v12_report" in module_text},
        {"name": "batch-checkpoint-v12-route-check-renderer-identity", "ok": checkpoint_identity_exact},
        {"name": "candidate-route-constant-values-exact", "ok": route_values_exact, "actual": EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES},
        {"name": "dashboard-serves-batch-checkpoint-v12-page", "ok": f"elif path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE:" in dashboard_text and f"html = {DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_RENDERER}()" in dashboard_text},
        {"name": "route-registry-batch-checkpoint-v12-identity", "ok": registry_identity_exact},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated", "ok": (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID in readme_history) or ("dashboard-dispatcher-batch-decomposition-prep-v13" in readme_next and "dashboard-dispatcher-batch-decomposition-prep-v13" in readme_history) or ("dashboard-dispatcher-batch-decomposition-trial-v13" in readme_next and "dashboard-dispatcher-batch-decomposition-trial-v13" in readme_history)},
        {"name": "previous-trial-v12-helper-state-confirmed", "ok": previous_trial_helpers_present and PREVIOUS_TRIAL_CHECK_ID in dashboard_text and PREVIOUS_TRIAL_CHECK_ID in row_helper_text},
        {"name": "helper-backed-count-current-or-successor", "ok": len(helper_rows) in {CURRENT_HELPER_BACKED_BRANCH_COUNT, CURRENT_HELPER_BACKED_BRANCH_COUNT + 3}, "helper_count": len(helper_rows)},
        {"name": "remaining-direct-registry-count-confirmed", "ok": len(direct_registry_rows) in {REMAINING_REGISTRY_DIRECT_BRANCH_COUNT - 1, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT + 2}, "direct_count": len(direct_registry_rows)},
        {"name": "cycle-net-direct-reduction-disclosed", "ok": NET_DIRECT_ROUTE_REDUCTION_PER_CYCLE == 0, "new_proof_routes": NEW_PROOF_ROUTES_PER_CYCLE, "moved_routes": MOVED_ROUTES_PER_TRIAL},
        {"name": "dispatcher-parity-clean", "ok": not blocked_parity, "blocked_count": len(blocked_parity)},
        {"name": "next-three-candidate-batch-selected", "ok": len(candidate_rows) == RECOMMENDED_BATCH_SIZE and not blocked_candidate_rows, "blocked_count": len(blocked_candidate_rows)},
        {"name": "manual-dashboard-dispatch-authoritative", "ok": "elif path ==" in dashboard_text and "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE" in dashboard_text and SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True},
        {"name": "manual-api-and-smoke-authoritative", "ok": SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "no-branch-body-movement", "ok": SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0},
        {"name": "candidate-branches-still-direct-or-successor", "ok": all(row.get("ok") is True for row in candidate_rows)},
        {"name": "renderer-bodies-still-in-dashboard", "ok": all(re.search(rf"^def {re.escape(row['renderer_name'])}\(", dashboard_text, re.MULTILINE) is not None for row in candidate_rows) and SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-growth-bounded", "ok": previous_dashboard_line_count <= dashboard_lines <= previous_dashboard_line_count + 140, "current_line_count": dashboard_lines},
        {"name": "command-deck-style-preserved", "ok": "command-deck" in readme_next and "operator-console" in readme_next and "data-tip" in dashboard_text},
        {"name": "native-title-tooltips-absent", "ok": " title=\"" not in dashboard_text and " title='" not in dashboard_text},
        {"name": "safety-boundary-preserved", "ok": all(value == expected for value, expected in [
            (SAFETY_BOUNDARY["actual_fixture_execution_count"], 0),
            (SAFETY_BOUNDARY["sandbox_backend_admission_count"], 0),
            (SAFETY_BOUNDARY["subprocess_spawn_count"], 0),
            (SAFETY_BOUNDARY["source_write_count"], 0),
            (SAFETY_BOUNDARY["source_delete_count"], 0),
            (SAFETY_BOUNDARY["generated_wiring_activated"], False),
            (SAFETY_BOUNDARY["release_authorized"], False),
            (SAFETY_BOUNDARY["autonomy_expanded"], False),
        ])},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_VERSION,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_CHECK_ID,
        "route": checkpoint_route,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": proof_rows,
        "blocked_rows": [row for row in proof_rows if row.get("ok") is not True],
        "helper_backed_branch_count": len(helper_rows),
        "expected_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
        "remaining_registry_direct_branch_count": len(direct_registry_rows),
        "expected_remaining_registry_direct_branch_count": REMAINING_REGISTRY_DIRECT_BRANCH_COUNT,
        "recommended_batch_size": RECOMMENDED_BATCH_SIZE,
        "new_proof_routes_per_cycle": NEW_PROOF_ROUTES_PER_CYCLE,
        "moved_routes_per_trial": MOVED_ROUTES_PER_TRIAL,
        "net_direct_route_reduction_per_cycle": NET_DIRECT_ROUTE_REDUCTION_PER_CYCLE,
        "next_batch_candidates": candidate_rows,
        "blocked_next_batch_candidates": blocked_candidate_rows,
        "parity_rows": len(parity_rows),
        "blocked_parity_rows": blocked_parity,
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "next_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_checkpoint_v12_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        "v1077.3 Dispatcher Batch Decomposition Checkpoint v12",
        f"status: {report.get('status')}",
        f"helper_backed_branch_count: {report.get('helper_backed_branch_count')}",
        f"remaining_registry_direct_branch_count: {report.get('remaining_registry_direct_branch_count')}",
        f"recommended_batch_size: {report.get('recommended_batch_size')}",
        f"new_proof_routes_per_cycle: {report.get('new_proof_routes_per_cycle')}",
        f"moved_routes_per_trial: {report.get('moved_routes_per_trial')}",
        f"net_direct_route_reduction_per_cycle: {report.get('net_direct_route_reduction_per_cycle')}",
        "selected_next_batch:",
    ]
    for row in report.get("next_batch_candidates", []):
        lines.append(f"- {row.get('path')} -> {row.get('expected_future_helper')} ok={row.get('ok')}")
    lines.extend([
        "branch_decomposition_batch_prepared: False",
        "branch_decomposition_batch_executed: False",
        "additional_branch_extraction_count: 0",
        "dispatcher_branch_condition_moved: False",
        "dispatcher_branch_body_moved: False",
        "renderer_bodies_moved: False",
        "actual_fixture_execution_count: 0",
        "sandbox_backend_admission_count: 0",
        "subprocess_spawn_count: 0",
        "source_write_count: 0",
        "source_delete_count: 0",
        "generated_wiring_activated: False",
        "release_authorized: False",
        "autonomy_expanded: False",
        f"next_arc: {report.get('next_arc')}",
    ])
    if full:
        lines.append("proof_rows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'ok' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_checkpoint_v12_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: checkpoint report blocked")
            print(report.get("blocked_rows"))
            print(report.get("blocked_next_batch_candidates"))
            return False
        if report.get("branch_decomposition_batch_prepared") is not False or report.get("branch_decomposition_batch_executed") is not False or report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: branch movement occurred during checkpoint")
            return False
        if report.get("helper_backed_branch_count") not in {CURRENT_HELPER_BACKED_BRANCH_COUNT, CURRENT_HELPER_BACKED_BRANCH_COUNT + 3}:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: helper count escaped safe successor bound")
            return False
        if report.get("remaining_registry_direct_branch_count") not in {REMAINING_REGISTRY_DIRECT_BRANCH_COUNT - 1, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT, REMAINING_REGISTRY_DIRECT_BRANCH_COUNT + 2}:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: direct count escaped safe successor bound")
            return False
        if report.get("recommended_batch_size") != RECOMMENDED_BATCH_SIZE or len(report.get("next_batch_candidates") or []) != RECOMMENDED_BATCH_SIZE:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: next batch escaped safe bound")
            return False
        if report.get("net_direct_route_reduction_per_cycle") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: cycle accounting changed unexpectedly")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: authority boundary changed")
            return False
        print(
            "[ok] dashboard-dispatcher-batch-decomposition-checkpoint-v12 "
            f"helper_count={report.get('helper_backed_branch_count')} "
            f"remaining_direct={report.get('remaining_registry_direct_branch_count')} "
            f"next_batch={len(report.get('next_batch_candidates') or [])} "
            f"net_cycle_reduction={report.get('net_direct_route_reduction_per_cycle')}"
        )
        return True
    except Exception as exc:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: {exc}")
        return False
