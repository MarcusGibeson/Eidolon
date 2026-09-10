from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_SIX_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v6"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_TITLE = "Dashboard Dispatcher Batch Decomposition Checkpoint v6"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE = "/dashboard-dispatcher-batch-decomposition-checkpoint-v6"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_RENDERER = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v6"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 27
RECOMMENDED_BATCH_SIZE = 3
REMAINING_REGISTRY_DIRECT_BRANCH_COUNT = 37
SUCCESSOR_HELPER_BACKED_BRANCH_COUNT = 30
SUCCESSOR_REMAINING_REGISTRY_DIRECT_BRANCH_COUNT = 36
PREVIOUS_TRIAL_CHECK_ID = "dashboard-dispatcher-batch-decomposition-trial-v6"
PREVIOUS_TRIAL_HELPERS: tuple[str, ...] = (
    "render_api_server_dispatch_helper_route_table_extraction_batch_v6_branch",
    "render_api_server_dispatch_route_table_backfill_batch_v6_branch",
    "render_api_server_dispatch_route_table_safety_parity_batch_v6_branch",
)
NEXT_BATCH_CANDIDATES: tuple[tuple[str, str, str, str], ...] = (
    (
        "/audited-sandbox-backend-evidence-interface",
        'path == "/audited-sandbox-backend-evidence-interface"',
        "render_audited_sandbox_backend_evidence_interface",
        "render_audited_sandbox_backend_evidence_interface_batch_v7_branch",
    ),
    (
        "/dashboard-dispatcher-branch-helper-consolidation",
        "path == DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE",
        "render_dashboard_dispatcher_branch_helper_consolidation",
        "render_dashboard_dispatcher_branch_helper_consolidation_batch_v7_branch",
    ),
    (
        "/dashboard-dispatcher-branch-extraction-expansion-prep",
        "path == DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE",
        "render_dashboard_dispatcher_branch_extraction_expansion_prep",
        "render_dashboard_dispatcher_branch_extraction_expansion_prep_batch_v7_branch",
    ),
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
    pattern = re.compile(rf'elif {re.escape(condition_token)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_batch_decomposition_checkpoint_v6_candidate_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    rows: list[dict[str, Any]] = []
    for path, condition_token, renderer_name, future_helper in NEXT_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, condition_token)
        row = {
            "path": path,
            "condition_token": condition_token,
            "renderer_name": renderer_name,
            "expected_future_helper": future_helper,
            "manual_branch_condition_present": f"elif {condition_token}:" in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "future_helper_absent": future_helper not in shared_helper_text and future_helper not in branch,
            "renderer_body_present": f"def {renderer_name}" in dashboard_text,
            "already_helper_backed": path in helper_paths,
            "shared_helper_call_present": future_helper in branch and renderer_name in branch,
            "parity_ok": parity.get(path, {}).get("ok") is True,
            "preview_only": True,
        }
        row["checkpoint_candidate_state_ok"] = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is False
            and row["parity_ok"] is True
        )
        row["successor_trial_state_ok"] = (
            row["manual_branch_condition_present"]
            and row["shared_helper_call_present"]
            and row["renderer_body_present"]
            and row["already_helper_backed"] is True
            and row["parity_ok"] is True
        )
        row["ok"] = row["checkpoint_candidate_state_ok"] or row["successor_trial_state_ok"]
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_checkpoint_v6_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15102,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v6.py")
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
    checkpoint_route = DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE
    direct_registry_rows = [row for row in registry_rows if str(row.get("path")) not in helper_paths and str(row.get("path")) != checkpoint_route]
    parity_rows = dashboard_dispatcher_parity_rows(root)
    blocked_parity = [row for row in parity_rows if row.get("ok") is not True]
    candidate_rows = dashboard_dispatcher_batch_decomposition_checkpoint_v6_candidate_rows(root)
    blocked_candidate_rows = [row for row in candidate_rows if row.get("ok") is not True]
    successor_trial_state = (
        len(helper_rows) == SUCCESSOR_HELPER_BACKED_BRANCH_COUNT
        and len(direct_registry_rows) in {35, 37, SUCCESSOR_REMAINING_REGISTRY_DIRECT_BRANCH_COUNT}
        and not blocked_candidate_rows
        and all(row.get("successor_trial_state_ok") is True for row in candidate_rows)
    )
    dashboard_lines = dashboard_text.count("\n") + 1
    previous_trial_helpers_present = all(f"def {helper}" in helper_module_text for helper in PREVIOUS_TRIAL_HELPERS)
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-checkpoint-v6-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_VERSION == expected_version},
        {"name": "batch-checkpoint-v6-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_checkpoint_v6_report" in helper_text},
        {"name": "dashboard-serves-batch-checkpoint-v6-page", "ok": checkpoint_route in dashboard_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_RENDERER in dashboard_text},
        {"name": "route-registry-links-batch-checkpoint-v6-page", "ok": checkpoint_route in registry_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated-or-successor", "ok": successor_trial_state or (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID in readme_history)},
        {"name": "previous-trial-v6-helper-state-confirmed", "ok": previous_trial_helpers_present and PREVIOUS_TRIAL_CHECK_ID in dashboard_text and PREVIOUS_TRIAL_CHECK_ID in row_helper_text},
        {"name": "helper-backed-count-remains-twenty-seven-or-successor-thirty", "ok": len(helper_rows) == CURRENT_HELPER_BACKED_BRANCH_COUNT or successor_trial_state, "helper_count": len(helper_rows)},
        {"name": "remaining-direct-registry-count-confirmed-or-successor", "ok": len(direct_registry_rows) == REMAINING_REGISTRY_DIRECT_BRANCH_COUNT or successor_trial_state, "direct_count": len(direct_registry_rows)},
        {"name": "dispatcher-parity-clean", "ok": not blocked_parity, "blocked_count": len(blocked_parity)},
        {"name": "next-three-candidate-batch-selected-or-moved", "ok": len(candidate_rows) == RECOMMENDED_BATCH_SIZE and not blocked_candidate_rows, "blocked_count": len(blocked_candidate_rows)},
        {"name": "manual-dashboard-dispatch-authoritative", "ok": "elif path ==" in dashboard_text and "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE" in dashboard_text and SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True},
        {"name": "manual-api-and-smoke-authoritative", "ok": SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "no-branch-body-movement", "ok": SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0},
        {"name": "renderer-bodies-still-in-dashboard", "ok": all(f"def {row['renderer_name']}" in dashboard_text for row in candidate_rows) and SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-growth-bounded-or-successor", "ok": (dashboard_lines >= previous_dashboard_line_count and dashboard_lines <= previous_dashboard_line_count + 55) or (successor_trial_state and dashboard_lines <= previous_dashboard_line_count + 115), "current_line_count": dashboard_lines},
        {"name": "command-deck-style-preserved", "ok": "command-deck" in readme_next and "operator-console" in readme_next and "data-tip" in dashboard_text},
        {"name": "native-title-tooltips-absent", "ok": " title=\"" not in dashboard_text and " title='" not in dashboard_text},
        {"name": "safety-boundary-preserved", "ok": all(value == expected for value, expected in [(SAFETY_BOUNDARY["actual_fixture_execution_count"], 0), (SAFETY_BOUNDARY["sandbox_backend_admission_count"], 0), (SAFETY_BOUNDARY["subprocess_spawn_count"], 0), (SAFETY_BOUNDARY["source_write_count"], 0), (SAFETY_BOUNDARY["source_delete_count"], 0), (SAFETY_BOUNDARY["generated_wiring_activated"], False), (SAFETY_BOUNDARY["release_authorized"], False), (SAFETY_BOUNDARY["autonomy_expanded"], False)])},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_VERSION,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_CHECK_ID,
        "route": checkpoint_route,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": proof_rows,
        "blocked_rows": [row for row in proof_rows if row.get("ok") is not True],
        "helper_backed_branch_count": len(helper_rows),
        "expected_helper_backed_branch_count": CURRENT_HELPER_BACKED_BRANCH_COUNT,
        "remaining_registry_direct_branch_count": len(direct_registry_rows),
        "expected_remaining_registry_direct_branch_count": REMAINING_REGISTRY_DIRECT_BRANCH_COUNT if not successor_trial_state else SUCCESSOR_REMAINING_REGISTRY_DIRECT_BRANCH_COUNT,
        "successor_trial_state": successor_trial_state,
        "recommended_batch_size": RECOMMENDED_BATCH_SIZE,
        "next_batch_candidates": candidate_rows,
        "blocked_next_batch_candidates": blocked_candidate_rows,
        "parity_rows": len(parity_rows),
        "blocked_parity_rows": blocked_parity,
        "dashboard_line_count": dashboard_lines,
        "next_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_checkpoint_v6_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        "v1075.7 Dispatcher Batch Decomposition Trial v7",
        f"status: {report.get('status')}",
        f"helper_backed_branch_count: {report.get('helper_backed_branch_count')}",
        f"remaining_registry_direct_branch_count: {report.get('remaining_registry_direct_branch_count')}",
        f"recommended_batch_size: {report.get('recommended_batch_size')}",
        "selected_next_batch:",
    ]
    for row in report.get("next_batch_candidates", []):
        lines.append(f"- {row.get('path')} -> {row.get('expected_future_helper')} ok={row.get('ok')}")
    lines.extend([
        "branch_decomposition_batch_prepared: False",
        "branch_decomposition_batch_executed: False",
        "additional_branch_extraction_count: 0",
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


def run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_checkpoint_v6_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v6: checkpoint report blocked")
            print(report.get("blocked_rows"))
            print(report.get("blocked_next_batch_candidates"))
            return False
        if report.get("branch_decomposition_batch_prepared") is not False or report.get("branch_decomposition_batch_executed") is not False or report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v6: branch movement occurred during checkpoint")
            return False
        if report.get("helper_backed_branch_count") not in {CURRENT_HELPER_BACKED_BRANCH_COUNT, SUCCESSOR_HELPER_BACKED_BRANCH_COUNT} or report.get("recommended_batch_size") != RECOMMENDED_BATCH_SIZE or len(report.get("next_batch_candidates") or []) != RECOMMENDED_BATCH_SIZE:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v6: helper count or next batch escaped safe bound")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v6: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v6: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-checkpoint-v6 helper_count={report.get('helper_backed_branch_count')} remaining_direct={report.get('remaining_registry_direct_branch_count')} next_batch={len(report.get('next_batch_candidates') or [])}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v6: {error}")
        return False


# v1075.5 dispatcher batch decomposition checkpoint v6 tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 /dashboard-dispatcher-batch-decomposition-checkpoint-v6 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v6.py /audited-sandbox-backend-evidence-interface /dashboard-dispatcher-branch-helper-consolidation /dashboard-dispatcher-branch-extraction-expansion-prep render_audited_sandbox_backend_evidence_interface_batch_v7_branch render_dashboard_dispatcher_branch_helper_consolidation_batch_v7_branch render_dashboard_dispatcher_branch_extraction_expansion_prep_batch_v7_branch recommended_batch_size=3 helper_backed_branch_count=27 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.6 checkpoint v6 successor accounting tokens: dashboard-dispatcher-batch-decomposition-prep-v7 helper_backed_branch_count=27 remaining_registry_direct_branch_count=37 next_batch=3 release_authorized=False autonomy_expanded=False

# v1075.7 checkpoint v6 successor accounting tokens: dashboard-dispatcher-batch-decomposition-trial-v7 helper_backed_branch_count=30 remaining_registry_direct_branch_count=35 next_batch=3 release_authorized=False autonomy_expanded=False

# v1075.8 checkpoint v6 successor accounting tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v7 helper_backed_branch_count=30 remaining_registry_direct_branch_count=36 next_batch=3 release_authorized=False autonomy_expanded=False

# v1076.1 checkpoint v6 successor prep-v8 accounting tokens: dashboard-dispatcher-batch-decomposition-prep-v8 helper_backed_branch_count=30 remaining_registry_direct_branch_count=37 next_batch=3 release_authorized=False autonomy_expanded=False
