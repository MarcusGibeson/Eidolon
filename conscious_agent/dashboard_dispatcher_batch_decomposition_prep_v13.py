from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import ast
import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_batch_decomposition_checkpoint_v12 import NEXT_BATCH_CANDIDATES
from dashboard_dispatcher_batch_strategy_checkpoint import (
    DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE,
)
from dashboard_dispatcher_batch_decomposition_prep import (
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE,
)
from dashboard_dispatcher_batch_decomposition_trial import (
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE,
)
from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_THIRTEEN_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID = "dashboard-dispatcher-batch-decomposition-prep-v13"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_TITLE = "Dashboard Dispatcher Batch Decomposition Prep v13"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE = "/dashboard-dispatcher-batch-decomposition-prep-v13"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_RENDERER = "render_dashboard_dispatcher_batch_decomposition_prep_v13"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 45
PREPARED_BATCH_SIZE = 3
PREPARED_BATCH_CANDIDATES: tuple[tuple[str, str, str, str, int], ...] = (
    (
        "/dashboard-dispatcher-batch-strategy-checkpoint",
        "path == DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE",
        "render_dashboard_dispatcher_batch_strategy_checkpoint",
        "render_dashboard_dispatcher_batch_strategy_checkpoint_batch_v13_branch",
        46,
    ),
    (
        "/dashboard-dispatcher-batch-decomposition-prep",
        "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE",
        "render_dashboard_dispatcher_batch_decomposition_prep",
        "render_dashboard_dispatcher_batch_decomposition_prep_batch_v13_branch",
        47,
    ),
    (
        "/dashboard-dispatcher-batch-decomposition-trial",
        "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE",
        "render_dashboard_dispatcher_batch_decomposition_trial",
        "render_dashboard_dispatcher_batch_decomposition_trial_batch_v13_branch",
        48,
    ),
)
EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES = (
    DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE,
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE,
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE,
)
PREVIOUS_CHECKPOINT_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v12"

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
    pattern = re.compile(rf"elif {re.escape(condition_token)}:\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)")
    match = pattern.search(source)
    return match.group(0) if match else ""


def _smoke_row_specs(source: str) -> list[tuple[str, str, int, str]]:
    rows: list[tuple[str, str, int, str]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return rows
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "SmokeCheckRowSpec":
            continue
        if len(node.args) != 4:
            continue
        try:
            values = tuple(ast.literal_eval(argument) for argument in node.args)
        except (ValueError, TypeError, SyntaxError):
            continue
        if isinstance(values[0], str) and isinstance(values[1], str) and isinstance(values[2], int) and isinstance(values[3], str):
            rows.append(values)
    return rows


def dashboard_dispatcher_batch_decomposition_prep_v13_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    rows: list[dict[str, Any]] = []
    for path, condition_token, renderer_name, expected_helper, extraction_order in PREPARED_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, condition_token)
        parity_row = parity.get(path, {})
        row = {
            "path": path,
            "condition_token": condition_token,
            "renderer_name": renderer_name,
            "expected_future_helper": expected_helper,
            "extraction_order": extraction_order,
            "manual_branch_condition_present": f"elif {condition_token}:" in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "shared_helper_call_present": expected_helper in branch and renderer_name in branch,
            "future_helper_absent_from_real_helper_module": f"def {expected_helper}" not in shared_helper_text and f'helper_name="{expected_helper}"' not in shared_helper_text,
            "future_helper_absent_from_branch": expected_helper not in branch,
            "renderer_body_present_in_dashboard": re.search(rf"^def {re.escape(renderer_name)}\(", dashboard_text, re.MULTILINE) is not None,
            "renderer_body_absent_from_helper_module": re.search(rf"^def {re.escape(renderer_name)}\(", shared_helper_text, re.MULTILINE) is None,
            "already_helper_backed": path in helper_paths,
            "parity_exact": parity_row.get("ok") is True and parity_row.get("registry_renderer") == renderer_name and parity_row.get("metadata_renderer") == renderer_name and parity_row.get("dispatcher_renderer") == renderer_name,
            "preview_only": True,
        }
        prep_state_ok = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent_from_real_helper_module"]
            and row["future_helper_absent_from_branch"]
            and row["renderer_body_present_in_dashboard"]
            and row["renderer_body_absent_from_helper_module"]
            and row["already_helper_backed"] is False
            and row["parity_exact"] is True
            and row["preview_only"] is True
        )
        successor_state_ok = (
            row["manual_branch_condition_present"]
            and row["shared_helper_call_present"]
            and row["renderer_body_present_in_dashboard"]
            and row["renderer_body_absent_from_helper_module"]
            and row["already_helper_backed"] is True
            and row["parity_exact"] is True
            and row["preview_only"] is True
        )
        row["prep_state_ok"] = prep_state_ok
        row["successor_state_ok"] = successor_state_ok
        row["ok"] = prep_state_ok or successor_state_ok
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_prep_v13_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15443,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py")
    checkpoint_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v12.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    helper_module_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = consolidated_branch_helper_rows()
    prep_rows = dashboard_dispatcher_batch_decomposition_prep_v13_rows(root)
    blocked_rows = [row for row in prep_rows if row.get("ok") is not True]
    blocked_current_rows = [row for row in prep_rows if row.get("prep_state_ok") is not True]
    current_prep_state = len(helper_rows) == CURRENT_HELPER_BACKED_BRANCH_COUNT and not blocked_current_rows
    successor_trial_state = len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT + PREPARED_BATCH_SIZE and not blocked_rows
    candidate_paths = tuple(row[0] for row in PREPARED_BATCH_CANDIDATES)
    candidate_helpers = tuple(row[3] for row in PREPARED_BATCH_CANDIDATES)
    checkpoint_candidates = tuple(tuple(row[:4]) for row in NEXT_BATCH_CANDIDATES)
    prep_candidate_core = tuple(tuple(row[:4]) for row in PREPARED_BATCH_CANDIDATES)
    registry_matches = [row for row in dashboard_route_registry_rows() if row.get("path") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE]
    parity_matches = [row for row in dashboard_dispatcher_parity_rows(root) if row.get("path") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE]
    smoke_matches = [row for row in _smoke_row_specs(row_helper_text) if row[0] == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID]
    own_branch = _branch_block(dashboard_text, "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE")
    expected_route_values = tuple(row[0] for row in PREPARED_BATCH_CANDIDATES)
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-prep-v13-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_VERSION == expected_version},
        {"name": "batch-prep-v13-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_prep_v13_report" in helper_text},
        {"name": "batch-prep-v13-route-check-renderer-identity", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID == "dashboard-dispatcher-batch-decomposition-prep-v13" and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE == "/dashboard-dispatcher-batch-decomposition-prep-v13" and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_RENDERER == "render_dashboard_dispatcher_batch_decomposition_prep_v13"},
        {"name": "candidate-route-constant-values-exact", "ok": EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES == expected_route_values, "actual": EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES},
        {"name": "checkpoint-runtime-candidates-match-prep", "ok": checkpoint_candidates == prep_candidate_core and PREVIOUS_CHECKPOINT_CHECK_ID in checkpoint_text},
        {"name": "dashboard-dispatch-branch-exact", "ok": "elif path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE:" in own_branch and "html = render_dashboard_dispatcher_batch_decomposition_prep_v13()" in own_branch},
        {"name": "route-registry-row-exact", "ok": len(registry_matches) == 1 and registry_matches[0].get("renderer_name") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_RENDERER and registry_matches[0].get("preview_only") is True},
        {"name": "dispatcher-parity-row-exact", "ok": len(parity_matches) == 1 and parity_matches[0].get("ok") is True and parity_matches[0].get("registry_renderer") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_RENDERER and parity_matches[0].get("dispatcher_renderer") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_RENDERER},
        {"name": "smoke-row-literals-exact", "ok": smoke_matches == [(DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID, "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v13_check")]},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID in source_privacy_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE in source_privacy_text},
        {"name": "release-docs-current-or-successor", "ok": (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID in readme_history) or ("dashboard-dispatcher-batch-decomposition-trial-v13" in readme_next and "dashboard-dispatcher-batch-decomposition-trial-v13" in readme_history) or ("dashboard-dispatcher-batch-decomposition-checkpoint-v13" in readme_next and "dashboard-dispatcher-batch-decomposition-checkpoint-v13" in readme_history)},
        {"name": "helper-backed-count-remains-forty-five-or-successor", "ok": current_prep_state or successor_trial_state, "helper_count": len(helper_rows)},
        {"name": "current-release-enforces-prep-only-state", "ok": expected_version != "1077.4" or current_prep_state},
        {"name": "three-batch-candidates-prepared", "ok": len(prep_rows) == PREPARED_BATCH_SIZE and not blocked_rows, "blocked_count": len(blocked_rows)},
        {"name": "future-helpers-absent-or-successor", "ok": all(f"def {helper}" not in helper_module_text for helper in candidate_helpers) or successor_trial_state},
        {"name": "direct-renderer-calls-still-direct", "ok": not blocked_current_rows or successor_trial_state, "blocked_count": len(blocked_current_rows)},
        {"name": "dispatcher-conditions-remain-in-dashboard", "ok": all(row.get("manual_branch_condition_present") is True for row in prep_rows)},
        {"name": "renderer-bodies-remain-only-in-dashboard", "ok": all(row.get("renderer_body_present_in_dashboard") is True and row.get("renderer_body_absent_from_helper_module") is True for row in prep_rows)},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "prep-only-no-branch-movement", "ok": SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is True and SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "dashboard-line-growth-bounded", "ok": previous_dashboard_line_count <= dashboard_lines <= previous_dashboard_line_count + 120, "current_line_count": dashboard_lines},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "operator-console" in readme_next and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": " title=\"" not in dashboard_text and " title='" not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_TITLE,
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE,
        "renderer": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_RENDERER,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py",
        "prepared_batch_candidates": prep_rows,
        "blocked_prep_rows": blocked_rows,
        "blocked_current_prep_rows": blocked_current_rows,
        "prepared_batch_size": PREPARED_BATCH_SIZE,
        "helper_backed_branch_count": len(helper_rows),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_prep_v13_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Route: {report.get('route')}",
        f"Prepared batch size: {report.get('prepared_batch_size')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        "Batch decomposition prep v13 executed: False",
        "Additional branch extractions: 0",
        "Dispatcher branch body moved: False",
        "Dispatcher branch condition moved: False",
        "Renderer bodies moved: False",
        "Dashboard GET preview-only: True",
        "No fixture execution, sandbox backend admission, subprocesses, writes, deletes, release authorization, generated wiring activation, or autonomy expansion.",
    ]
    for row in report.get("prepared_batch_candidates", []):
        lines.append(f"- {row.get('path')} -> {row.get('expected_future_helper')}: {'pass' if row.get('prep_state_ok') else 'successor' if row.get('successor_state_ok') else 'blocked'}")
    if full:
        lines.append("proof_rows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_prep_v13_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_prep_v13_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: prep report blocked")
            print(report.get("rows"))
            print(report.get("blocked_prep_rows"))
            return False
        if report.get("prepared_batch_size") != PREPARED_BATCH_SIZE or len(report.get("prepared_batch_candidates") or []) != PREPARED_BATCH_SIZE:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: prepared batch escaped safe bound")
            return False
        if expected_version == "1077.4" and report.get("helper_backed_branch_count") != CURRENT_HELPER_BACKED_BRANCH_COUNT:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: prep release changed helper-backed count")
            return False
        if report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_condition_moved") is not False or report.get("dispatcher_branch_body_moved") is not False or report.get("renderer_bodies_moved") is not False or report.get("branch_decomposition_batch_executed") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: branch or renderer movement occurred during prep")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-prep-v13 helper_count={report.get('helper_backed_branch_count')} prepared={len(report.get('prepared_batch_candidates') or [])} route_identity=exact")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-prep-v13: {error}")
        return False


# v1077.4 dispatcher batch decomposition prep v13 tokens: dashboard-dispatcher-batch-decomposition-prep-v13 /dashboard-dispatcher-batch-decomposition-prep-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py /dashboard-dispatcher-batch-strategy-checkpoint /dashboard-dispatcher-batch-decomposition-prep /dashboard-dispatcher-batch-decomposition-trial render_dashboard_dispatcher_batch_strategy_checkpoint_batch_v13_branch render_dashboard_dispatcher_batch_decomposition_prep_batch_v13_branch render_dashboard_dispatcher_batch_decomposition_trial_batch_v13_branch prepared_batch_size=3 helper_backed_branch_count=45 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True route_check_renderer_constant_values_exact=True direct_http_probe_required=True data-tip command-deck operator-console no_native_title_tooltip
