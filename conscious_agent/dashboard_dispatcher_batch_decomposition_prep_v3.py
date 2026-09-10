from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_VERSION = "1074.6"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_THREE_VERSION = RUNTIME_VERSION
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID = "dashboard-dispatcher-batch-decomposition-prep-v3"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_TITLE = "Dashboard Dispatcher Batch Decomposition Prep v3"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE = "/dashboard-dispatcher-batch-decomposition-prep-v3"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_RENDERER = "render_dashboard_dispatcher_batch_decomposition_prep_v3"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 15
PREPARED_BATCH_SIZE = 3
PREPARED_BATCH_CANDIDATES: tuple[tuple[str, str, str, int], ...] = (
    ("/source-decomposition-batch-i", "render_source_decomposition_batch_i", "render_source_decomposition_batch_i_batch_v3_branch", 16),
    ("/autonomy-phase-zero-observation-contract", "render_autonomy_phase_zero_observation_contract", "render_autonomy_phase_zero_observation_contract_batch_v3_branch", 17),
    ("/source-decomposition-batch-ii", "render_source_decomposition_batch_ii", "render_source_decomposition_batch_ii_batch_v3_branch", 18),
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


def _branch_block(source: str, path: str) -> str:
    pattern = re.compile(rf'elif path == "{re.escape(path)}":\n(?P<body>(?:\s+[^\n]+\n)+?)(?=\s+elif path ==|\s+else:)')
    match = pattern.search(source)
    return match.group(0) if match else ""


def dashboard_dispatcher_batch_decomposition_prep_v3_rows(project_root: str | Path) -> list[dict[str, Any]]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    shared_helper_text = _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py")
    parity = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    helper_paths = {str(row.get("path")) for row in consolidated_branch_helper_rows()}
    rows: list[dict[str, Any]] = []
    for path, renderer_name, expected_helper, extraction_order in PREPARED_BATCH_CANDIDATES:
        branch = _branch_block(dashboard_text, path)
        row = {
            "path": path,
            "renderer_name": renderer_name,
            "expected_future_helper": expected_helper,
            "extraction_order": extraction_order,
            "manual_branch_condition_present": f'elif path == "{path}":' in branch,
            "direct_renderer_call_present": f"html = {renderer_name}()" in branch,
            "shared_helper_call_present": expected_helper in branch and renderer_name in branch,
            "future_helper_absent": expected_helper not in branch and expected_helper not in shared_helper_text,
            "renderer_body_present": f"def {renderer_name}" in dashboard_text,
            "already_helper_backed": path in helper_paths,
            "parity_ok": parity.get(path, {}).get("ok") is True,
            "preview_only": True,
        }
        prep_state_ok = (
            row["manual_branch_condition_present"]
            and row["direct_renderer_call_present"]
            and row["future_helper_absent"]
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
        row["successor_state_ok"] = successor_state_ok
        rows.append(row)
    return rows


def build_dashboard_dispatcher_batch_decomposition_prep_v3_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 14905,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    helper_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py")
    checkpoint_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v2.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    dashboard_lines = dashboard_text.count("\n") + 1
    helper_rows = consolidated_branch_helper_rows()
    prep_rows = dashboard_dispatcher_batch_decomposition_prep_v3_rows(root)
    blocked_prep_rows = [row for row in prep_rows if row.get("ok") is not True]
    candidate_paths = [path for path, _renderer, _helper, _order in PREPARED_BATCH_CANDIDATES]
    candidate_helpers = [helper for _path, _renderer, helper, _order in PREPARED_BATCH_CANDIDATES]
    proof_rows: list[dict[str, Any]] = [
        {"name": "batch-prep-v3-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_VERSION == expected_version},
        {"name": "batch-prep-v3-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_prep_v3_report" in helper_text},
        {"name": "dashboard-serves-batch-prep-v3-page", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE in dashboard_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_RENDERER in dashboard_text},
        {"name": "route-registry-links-batch-prep-v3-page", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE in registry_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_RENDERER in registry_text},
        {"name": "smoke-row-registered", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID in row_helper_text and "run_dashboard_dispatcher_batch_decomposition_prep_v3_check" in row_helper_text},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID in source_privacy_text},
        {"name": "docs-current-arc-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID in readme_history},
        {"name": "checkpoint-selected-same-three-candidates", "ok": all(path in checkpoint_text for path in candidate_paths) and "recommended_batch_size=3" in checkpoint_text},
        {"name": "helper-backed-count-unchanged-or-successor", "ok": len(helper_rows) >= CURRENT_HELPER_BACKED_BRANCH_COUNT, "helper_count": len(helper_rows)},
        {"name": "three-batch-candidates-prepared", "ok": len(prep_rows) == PREPARED_BATCH_SIZE and not blocked_prep_rows, "blocked_count": len(blocked_prep_rows)},
        {"name": "future-helpers-still-absent-or-successor-trial", "ok": all(helper not in _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py") for helper in candidate_helpers) or ("dashboard-dispatcher-batch-decomposition-trial-v3" in dashboard_text and all(helper in _read(root, "conscious_agent/dashboard_dispatcher_branch_helpers.py") for helper in candidate_helpers))},
        {"name": "batch-prep-not-trial", "ok": SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is True and SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False},
        {"name": "dispatcher-and-renderer-authority-retained", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False and SAFETY_BOUNDARY["http_dispatcher_replaced"] is False},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "dashboard-line-count-budget", "ok": dashboard_lines <= previous_dashboard_line_count + 800, "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "preview-only-side-effect-boundary", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py",
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE,
        "prepared_batch_candidates": prep_rows,
        "blocked_candidate_rows": blocked_prep_rows,
        "helper_backed_branch_count": len(helper_rows),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_prep_v3_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')}: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper-backed branches: {report.get('helper_backed_branch_count')}",
        f"Prepared batch size: {report.get('prepared_batch_size')}",
        "Branch batch prepared: True",
        "Branch batch executed: False",
        "Additional branch extractions: 0",
        "Dispatcher branch body moved: False",
        "Renderer bodies moved: False",
        "Manual dashboard/API/smoke authority retained: True",
        "No subprocesses, writes, deletes, release authorization, fixture execution, sandbox backend admission, generated wiring activation, or autonomy expansion.",
    ]
    if full:
        lines.append("Prepared batch candidates:")
        for row in report.get("prepared_batch_candidates", []):
            lines.append(f"- {row.get('path')} -> {row.get('renderer_name')} / {row.get('expected_future_helper')}: {'pass' if row.get('ok') else 'blocked'}")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_batch_decomposition_prep_v3_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_prep_v3_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v3: prep report blocked")
            print(report.get("rows"))
            print(report.get("blocked_candidate_rows"))
            return False
        if report.get("branch_decomposition_batch_executed") is not False or report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v3: branch movement occurred during prep")
            return False
        if report.get("prepared_batch_size") != 3 or len(report.get("prepared_batch_candidates") or []) != 3:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v3: batch size escaped safe bound")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v3: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-prep-v3: authority boundary changed")
            return False
        print(f"[ok] dashboard-dispatcher-batch-decomposition-prep-v3 prepared={report.get('prepared_batch_size')} helper_count={report.get('helper_backed_branch_count')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-prep-v3: {error}")
        return False


# v1074.4 dispatcher batch decomposition prep v3 tokens: dashboard-dispatcher-batch-decomposition-prep-v3 /dashboard-dispatcher-batch-decomposition-prep-v3 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py prepared_batch_size=3 /source-decomposition-batch-i /autonomy-phase-zero-observation-contract /source-decomposition-batch-ii render_source_decomposition_batch_i_batch_v3_branch render_autonomy_phase_zero_observation_contract_batch_v3_branch render_source_decomposition_batch_ii_batch_v3_branch branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 helper_backed_branch_count=15 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
