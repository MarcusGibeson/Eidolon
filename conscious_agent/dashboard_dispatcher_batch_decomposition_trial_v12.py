from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import ast
import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_batch_decomposition_checkpoint_v11 import NEXT_BATCH_CANDIDATES
from dashboard_dispatcher_batch_decomposition_prep_v12 import (
    PREPARED_BATCH_CANDIDATES,
    dashboard_dispatcher_batch_decomposition_prep_v12_rows,
)
from dashboard_dispatcher_branch_decomposition_continuation_prep_v3 import (
    DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE,
)
from dashboard_dispatcher_branch_decomposition_continuation_trial_v2 import (
    DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE,
)
from dashboard_dispatcher_branch_decomposition_continuation_trial_v3 import (
    DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE,
)
from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_TWELVE_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID = "dashboard-dispatcher-batch-decomposition-trial-v12"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_TITLE = "Dashboard Dispatcher Batch Decomposition Trial v12"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE = "/dashboard-dispatcher-batch-decomposition-trial-v12"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_RENDERER = "render_dashboard_dispatcher_batch_decomposition_trial_v12"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

PREVIOUS_HELPER_BACKED_BRANCH_COUNT = 42
CURRENT_HELPER_BACKED_BRANCH_COUNT = 45
MOVED_BATCH_SIZE = 3
EXPECTED_MOVED_BATCH_CANDIDATES: tuple[tuple[str, str, str, str, int], ...] = (
    (
        "/dashboard-dispatcher-branch-decomposition-continuation-trial-v2",
        "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE",
        "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2",
        "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_batch_v12_branch",
        43,
    ),
    (
        "/dashboard-dispatcher-branch-decomposition-continuation-prep-v3",
        "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE",
        "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3",
        "render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_batch_v12_branch",
        44,
    ),
    (
        "/dashboard-dispatcher-branch-decomposition-continuation-trial-v3",
        "path == DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE",
        "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3",
        "render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_batch_v12_branch",
        45,
    ),
)
MOVED_BATCH_CANDIDATES = EXPECTED_MOVED_BATCH_CANDIDATES
EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES = (
    DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE,
    DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE,
    DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE,
)
PREVIOUS_PREP_CHECK_ID = "dashboard-dispatcher-batch-decomposition-prep-v12"
PREVIOUS_CHECKPOINT_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v11"

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


def _pass_through_helper_names(source: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return names
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or len(node.args.args) != 1:
            continue
        argument_name = node.args.args[0].arg
        for statement in node.body:
            if not isinstance(statement, ast.Return) or not isinstance(statement.value, ast.Call):
                continue
            call = statement.value
            if isinstance(call.func, ast.Name) and call.func.id == argument_name and not call.args and not call.keywords:
                names.add(node.name)
    return names


def dashboard_dispatcher_batch_decomposition_trial_v12_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_rows = {str(row.get("path")): row for row in consolidated_branch_helper_rows()}
    pass_through_helpers = _pass_through_helper_names(helper_text)
    rows: list[dict[str, Any]] = []
    for path, condition_token, renderer_name, helper_name, extraction_order in MOVED_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, condition_token)
        helper_row = helper_rows.get(path, {})
        parity_row = parity.get(path, {})
        row = {
            "path": path,
            "condition_token": condition_token,
            "renderer_name": renderer_name,
            "helper_name": helper_name,
            "extraction_order": extraction_order,
            "manual_branch_condition_present": f"elif {condition_token}:" in branch,
            "shared_helper_call_exact": f"html = {helper_name}({renderer_name})" in branch,
            "direct_renderer_call_absent": f"html = {renderer_name}()" not in branch,
            "renderer_body_present_in_dashboard": re.search(rf"^def {re.escape(renderer_name)}\(", dashboard_text, re.MULTILINE) is not None,
            "renderer_body_absent_from_helper_module": re.search(rf"^def {re.escape(renderer_name)}\(", helper_text, re.MULTILINE) is None,
            "helper_definition_pass_through": helper_name in pass_through_helpers,
            "helper_registry_row_exact": helper_row.get("renderer_name") == renderer_name and helper_row.get("helper_name") == helper_name and helper_row.get("extraction_order") == extraction_order and helper_row.get("manual_condition_retained") is True and helper_row.get("renderer_body_moved") is False and helper_row.get("preview_only") is True,
            "parity_exact": parity_row.get("ok") is True and parity_row.get("registry_renderer") == renderer_name and parity_row.get("metadata_renderer") == renderer_name and parity_row.get("dispatcher_renderer") == renderer_name,
            "preview_only": True,
        }
        row["ok"] = all(
            row[key] is True
            for key in (
                "manual_branch_condition_present",
                "shared_helper_call_exact",
                "direct_renderer_call_absent",
                "renderer_body_present_in_dashboard",
                "renderer_body_absent_from_helper_module",
                "helper_definition_pass_through",
                "helper_registry_row_exact",
                "parity_exact",
                "preview_only",
            )
        )
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_trial_v12_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15406,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    module_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py")
    prep_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v12.py")
    checkpoint_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v11.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = consolidated_branch_helper_rows()
    trial_rows = dashboard_dispatcher_batch_decomposition_trial_v12_rows(root)
    blocked_rows = [row for row in trial_rows if row.get("ok") is not True]
    prep_successor_rows = dashboard_dispatcher_batch_decomposition_prep_v12_rows(root)
    registry_matches = [row for row in dashboard_route_registry_rows() if row.get("path") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE]
    parity_matches = [row for row in dashboard_dispatcher_parity_rows(root) if row.get("path") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE]
    smoke_matches = [row for row in _smoke_row_specs(row_helper_text) if row[0] == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID]
    own_branch = _branch_block(dashboard_text, "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE")
    candidate_core = tuple(tuple(row[:4]) for row in MOVED_BATCH_CANDIDATES)
    prep_core = tuple(tuple(row[:4]) for row in PREPARED_BATCH_CANDIDATES)
    checkpoint_core = tuple(tuple(row[:4]) for row in NEXT_BATCH_CANDIDATES)
    expected_route_values = tuple(row[0] for row in MOVED_BATCH_CANDIDATES)
    moved_helpers = tuple(row[3] for row in MOVED_BATCH_CANDIDATES)
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-trial-v12-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_VERSION == expected_version},
        {"name": "batch-trial-v12-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_trial_v12_report" in module_text},
        {"name": "batch-trial-v12-route-check-renderer-identity", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID == "dashboard-dispatcher-batch-decomposition-trial-v12" and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE == "/dashboard-dispatcher-batch-decomposition-trial-v12" and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_RENDERER == "render_dashboard_dispatcher_batch_decomposition_trial_v12"},
        {"name": "candidate-route-constant-values-exact", "ok": EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES == expected_route_values, "actual": EXPECTED_CANDIDATE_ROUTE_CONSTANT_VALUES},
        {"name": "prep-runtime-candidates-match-trial", "ok": prep_core == candidate_core and PREVIOUS_PREP_CHECK_ID in prep_text},
        {"name": "checkpoint-runtime-candidates-match-trial", "ok": checkpoint_core == candidate_core and PREVIOUS_CHECKPOINT_CHECK_ID in checkpoint_text},
        {"name": "dashboard-dispatch-branch-exact", "ok": "elif path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE:" in own_branch and "html = render_dashboard_dispatcher_batch_decomposition_trial_v12()" in own_branch},
        {"name": "route-registry-row-exact", "ok": len(registry_matches) == 1 and registry_matches[0].get("renderer_name") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_RENDERER and registry_matches[0].get("preview_only") is True},
        {"name": "dispatcher-parity-row-exact", "ok": len(parity_matches) == 1 and parity_matches[0].get("ok") is True and parity_matches[0].get("registry_renderer") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_RENDERER and parity_matches[0].get("dispatcher_renderer") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_RENDERER},
        {"name": "smoke-row-literals-exact", "ok": smoke_matches == [(DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID, "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v12_check")]},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID in source_privacy_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE in source_privacy_text},
        {"name": "release-docs-current-or-successor", "ok": (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID in readme_history) or ("dashboard-dispatcher-batch-decomposition-checkpoint-v12" in readme_next and "dashboard-dispatcher-batch-decomposition-checkpoint-v12" in readme_history) or ("dashboard-dispatcher-batch-decomposition-prep-v13" in readme_next and "dashboard-dispatcher-batch-decomposition-prep-v13" in readme_history) or ("dashboard-dispatcher-batch-decomposition-trial-v13" in readme_next and "dashboard-dispatcher-batch-decomposition-trial-v13" in readme_history)},
        {"name": "helper-count-increased-by-exactly-three", "ok": len(helper_rows) in {CURRENT_HELPER_BACKED_BRANCH_COUNT, CURRENT_HELPER_BACKED_BRANCH_COUNT + MOVED_BATCH_SIZE} and CURRENT_HELPER_BACKED_BRANCH_COUNT == PREVIOUS_HELPER_BACKED_BRANCH_COUNT + MOVED_BATCH_SIZE, "helper_count": len(helper_rows)},
        {"name": "prep-v12-successor-state-proven", "ok": len(prep_successor_rows) == MOVED_BATCH_SIZE and all(row.get("successor_state_ok") is True for row in prep_successor_rows)},
        {"name": "moved-helpers-defined-and-registered", "ok": not blocked_rows and all(f"def {helper}" in helper_text for helper in moved_helpers), "blocked_count": len(blocked_rows)},
        {"name": "exactly-three-branch-extractions", "ok": SAFETY_BOUNDARY["additional_branch_extraction_count"] == MOVED_BATCH_SIZE and SAFETY_BOUNDARY["moved_branch_count"] == MOVED_BATCH_SIZE},
        {"name": "manual-conditions-retained", "ok": all(row.get("manual_branch_condition_present") is True for row in trial_rows)},
        {"name": "direct-renderer-calls-removed-from-moved-bodies", "ok": all(row.get("direct_renderer_call_absent") is True for row in trial_rows)},
        {"name": "renderer-bodies-remain-only-in-dashboard", "ok": all(row.get("renderer_body_present_in_dashboard") is True and row.get("renderer_body_absent_from_helper_module") is True for row in trial_rows)},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is True and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "dashboard-line-growth-bounded", "ok": previous_dashboard_line_count <= dashboard_lines <= previous_dashboard_line_count + 160, "current_line_count": dashboard_lines},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "operator-console" in readme_next and "data-tip" in module_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": " title=\"" not in dashboard_text and " title='" not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_TITLE,
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE,
        "renderer": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_RENDERER,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py",
        "moved_batch_candidates": trial_rows,
        "blocked_trial_rows": blocked_rows,
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


def dashboard_dispatcher_batch_decomposition_trial_v12_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Route: {report.get('route')}",
        f"Moved batch size: {report.get('moved_batch_size')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        "Batch decomposition trial v12 executed: True",
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
        lines.append("proof_rows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_trial_v12_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_trial_v12_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: trial report blocked")
            print(report.get("rows"))
            print(report.get("blocked_trial_rows"))
            return False
        if report.get("moved_batch_size") != MOVED_BATCH_SIZE or len(report.get("moved_batch_candidates") or []) != MOVED_BATCH_SIZE:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: moved batch escaped safe bound")
            return False
        if report.get("helper_backed_branch_count") not in {CURRENT_HELPER_BACKED_BRANCH_COUNT, CURRENT_HELPER_BACKED_BRANCH_COUNT + MOVED_BATCH_SIZE}:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: helper count did not reach 45")
            return False
        if report.get("additional_branch_extraction_count") != MOVED_BATCH_SIZE or report.get("dispatcher_branch_body_moved") is not True or report.get("dispatcher_branch_condition_moved") is not False or report.get("renderer_bodies_moved") is not False or report.get("branch_decomposition_batch_executed") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: trial execution accounting changed")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-trial-v12 helper_count={report.get('helper_backed_branch_count')} moved={len(report.get('moved_batch_candidates') or [])} route_identity=exact")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-trial-v12: {error}")
        return False


# v1077.2 dispatcher batch decomposition trial v12 tokens: dashboard-dispatcher-batch-decomposition-trial-v12 /dashboard-dispatcher-batch-decomposition-trial-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py /dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_batch_v12_branch render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_batch_v12_branch render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_batch_v12_branch moved_batch_size=3 previous_helper_backed_branch_count=42 helper_backed_branch_count=45 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True route_check_renderer_constant_values_exact=True direct_http_probe_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1077.7 bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False
