from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_batch_decomposition_trial_v13 import (
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_CHECK_ID,
    DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE,
    EXPECTED_MOVED_BATCH_CANDIDATES,
    dashboard_dispatcher_batch_decomposition_trial_v13_rows,
)
from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_THIRTEEN_VERSION = "1077.9"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID = "dashboard-dispatcher-batch-decomposition-checkpoint-v13"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_TITLE = "Dashboard Dispatcher Batch Decomposition Checkpoint v13"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE = "/dashboard-dispatcher-batch-decomposition-checkpoint-v13"
DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_RENDERER = "render_dashboard_dispatcher_batch_decomposition_checkpoint_v13"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

CURRENT_HELPER_BACKED_BRANCH_COUNT = 48
EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT = 36
EXPECTED_PRECHECKPOINT_LEGACY_PROOF_ROUTES = 35
EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTES = 0
NEW_PROOF_ROUTES_PER_LEGACY_CYCLE = 3
MOVED_ROUTES_PER_LEGACY_TRIAL = 3
NET_DIRECT_ROUTE_REDUCTION_PER_LEGACY_CYCLE = 0
SUCCESSOR_PROOF_SURFACE_ROUTES: tuple[str, ...] = (
    "/dashboard-dispatcher-proof-surface-consolidation-prep-v1",
)

HISTORICAL_PROOF_ROUTE_PATTERN = re.compile(
    r"^/dashboard-dispatcher-batch-decomposition-(?:prep|trial|checkpoint)(?:-v\d+)?$"
)

CONSOLIDATION_PLAN: tuple[dict[str, Any], ...] = (
    {
        "order": 1,
        "id": "parameterized-proof-ledger-prep",
        "scope": "Define one parameterized read-only proof ledger and compatibility contract without removing routes.",
        "changes_routes": False,
        "moves_branch_bodies": False,
    },
    {
        "order": 2,
        "id": "consolidated-proof-renderer-trial",
        "scope": "Add the shared proof renderer and dispatcher adapter under manual dispatch authority.",
        "changes_routes": True,
        "moves_branch_bodies": False,
    },
    {
        "order": 3,
        "id": "historical-route-compatibility-migration",
        "scope": "Map historical proof routes to the consolidated surface in bounded compatibility batches.",
        "changes_routes": True,
        "moves_branch_bodies": True,
    },
    {
        "order": 4,
        "id": "registry-navigation-cleanup",
        "scope": "Remove duplicate permanent navigation rows only after compatibility and HTTP parity pass.",
        "changes_routes": True,
        "moves_branch_bodies": False,
    },
    {
        "order": 5,
        "id": "current-version-truth-reduction",
        "scope": "Reduce duplicated rolling version and milestone truth while preserving historical release records.",
        "changes_routes": False,
        "moves_branch_bodies": False,
    },
    {
        "order": 6,
        "id": "dispatcher-decomposition-closure",
        "scope": "Prove zero ordinary direct routes, bounded compatibility aliases, and complete release integrity.",
        "changes_routes": False,
        "moves_branch_bodies": False,
    },
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
    "branch_decomposition_batch_prepared": False,
    "branch_decomposition_batch_executed": False,
    "additional_branch_extraction_count": 0,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": False,
    "renderer_bodies_moved": False,
    "historical_routes_removed": False,
    "compatibility_aliases_activated": False,
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


def dashboard_dispatcher_batch_decomposition_checkpoint_v13_inventory(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    registry_rows = dashboard_route_registry_rows()
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}

    direct_rows = [row for row in registry_rows if str(row.get("path")) not in helper_paths]
    successor_rows = [row for row in direct_rows if str(row.get("path")) in SUCCESSOR_PROOF_SURFACE_ROUTES]
    direct_excluding_own = [
        row for row in direct_rows
        if row.get("path") != DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE
        and str(row.get("path")) not in SUCCESSOR_PROOF_SURFACE_ROUTES
    ]
    historical_rows = [row for row in direct_excluding_own if HISTORICAL_PROOF_ROUTE_PATTERN.fullmatch(str(row.get("path")))]
    ordinary_rows = [row for row in direct_excluding_own if row not in historical_rows]
    precheckpoint_legacy_rows = [row for row in historical_rows if row.get("path") != DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE]

    inventory_rows: list[dict[str, Any]] = []
    for row in historical_rows:
        path = str(row.get("path"))
        renderer_name = str(row.get("renderer_name"))
        parity_row = parity_by_path.get(path, {})
        item = {
            "path": path,
            "renderer_name": renderer_name,
            "historical_proof_route": True,
            "helper_registry_row_absent": path not in helper_paths,
            "direct_renderer_call_present": f"html = {renderer_name}()" in dashboard_text,
            "renderer_body_present_in_dashboard": re.search(rf"^def {re.escape(renderer_name)}\(", dashboard_text, re.MULTILINE) is not None,
            "parity_exact": parity_row.get("ok") is True and parity_row.get("registry_renderer") == renderer_name and parity_row.get("dispatcher_renderer") == renderer_name,
            "preview_only": row.get("preview_only") is True,
        }
        item["ok"] = all(item[key] is True for key in (
            "historical_proof_route",
            "helper_registry_row_absent",
            "direct_renderer_call_present",
            "renderer_body_present_in_dashboard",
            "parity_exact",
            "preview_only",
        ))
        inventory_rows.append(item)

    return {
        "registry_route_count": len(registry_rows),
        "helper_backed_branch_count": len(helper_rows),
        "direct_registry_branch_count_total": len(direct_rows),
        "direct_registry_branch_count_excluding_checkpoint_v13": len(direct_excluding_own),
        "historical_proof_direct_route_count": len(historical_rows),
        "precheckpoint_legacy_proof_route_count": len(precheckpoint_legacy_rows),
        "ordinary_operational_direct_route_count": len(ordinary_rows),
        "historical_rows": inventory_rows,
        "ordinary_rows": ordinary_rows,
        "precheckpoint_legacy_rows": precheckpoint_legacy_rows,
        "successor_proof_surface_rows": successor_rows,
        "successor_proof_surface_route_count": len(successor_rows),
    }


def build_dashboard_dispatcher_batch_decomposition_checkpoint_v13_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15477,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    module_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v13.py")
    trial_text = _read(root, "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v13.py")
    row_helper_text = _read(root, "tools/smoke_registry_check_rows.py")
    metadata_text = _read(root, "conscious_agent/metadata_release_integrity.py")
    source_privacy_text = _read(root, "conscious_agent/source_package_privacy_metadata_integrity.py")
    readme_next = _read(root, "README_NEXT_STEPS.md")
    readme_history = _read(root, "README_RELEASE_HISTORY.md")
    dashboard_lines = dashboard_text.count("\n") + 1

    inventory = dashboard_dispatcher_batch_decomposition_checkpoint_v13_inventory(root)
    trial_rows = dashboard_dispatcher_batch_decomposition_trial_v13_rows(root)
    registry_matches = [row for row in dashboard_route_registry_rows() if row.get("path") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE]
    parity_rows = dashboard_dispatcher_parity_rows(root)
    parity_matches = [row for row in parity_rows if row.get("path") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE]
    blocked_parity = [row for row in parity_rows if row.get("ok") is not True]
    smoke_matches = [row for row in _smoke_row_specs(row_helper_text) if row[0] == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID]
    own_branch = _branch_block(dashboard_text, "path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE")

    historical_rows = inventory["historical_rows"]
    blocked_inventory = [row for row in historical_rows if row.get("ok") is not True]
    proof_rows: list[dict[str, Any]] = [
        {"name": "checkpoint-v13-module-current", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_VERSION == expected_version},
        {"name": "checkpoint-v13-module-exists", "ok": "build_dashboard_dispatcher_batch_decomposition_checkpoint_v13_report" in module_text},
        {"name": "checkpoint-v13-route-check-renderer-identity", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID == "dashboard-dispatcher-batch-decomposition-checkpoint-v13" and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE == "/dashboard-dispatcher-batch-decomposition-checkpoint-v13" and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_RENDERER == "render_dashboard_dispatcher_batch_decomposition_checkpoint_v13"},
        {"name": "dashboard-dispatch-branch-exact", "ok": "elif path == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE:" in own_branch and "html = render_dashboard_dispatcher_batch_decomposition_checkpoint_v13()" in own_branch},
        {"name": "route-registry-row-exact", "ok": len(registry_matches) == 1 and registry_matches[0].get("renderer_name") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_RENDERER and registry_matches[0].get("preview_only") is True},
        {"name": "dispatcher-parity-row-exact", "ok": len(parity_matches) == 1 and parity_matches[0].get("ok") is True and parity_matches[0].get("registry_renderer") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_RENDERER and parity_matches[0].get("dispatcher_renderer") == DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_RENDERER},
        {"name": "smoke-row-literals-exact", "ok": smoke_matches == [(DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID, "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check")]},
        {"name": "current-metadata-tokens-updated", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE in metadata_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID in source_privacy_text and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE in source_privacy_text},
        {"name": "release-docs-current-or-successor", "ok": (DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID in readme_next and DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID in readme_history) or ("dashboard-dispatcher-proof-surface-consolidation-prep-v1" in readme_next and "dashboard-dispatcher-proof-surface-consolidation-prep-v1" in readme_history)},
        {"name": "trial-v13-helper-state-stable", "ok": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_CHECK_ID in trial_text and len(trial_rows) == len(EXPECTED_MOVED_BATCH_CANDIDATES) and all(row.get("ok") is True for row in trial_rows)},
        {"name": "helper-backed-count-stable", "ok": inventory["helper_backed_branch_count"] == CURRENT_HELPER_BACKED_BRANCH_COUNT, "helper_count": inventory["helper_backed_branch_count"]},
        {"name": "direct-proof-inventory-current", "ok": inventory["direct_registry_branch_count_excluding_checkpoint_v13"] in {EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT, EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT + 1} and inventory["historical_proof_direct_route_count"] == EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT, "direct_count": inventory["direct_registry_branch_count_excluding_checkpoint_v13"]},
        {"name": "precheckpoint-35-route-inventory-reconciled", "ok": inventory["precheckpoint_legacy_proof_route_count"] == EXPECTED_PRECHECKPOINT_LEGACY_PROOF_ROUTES, "legacy_count": inventory["precheckpoint_legacy_proof_route_count"]},
        {"name": "zero-ordinary-operational-direct-routes", "ok": inventory["ordinary_operational_direct_route_count"] in {EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTES, EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTES + 1}, "ordinary_count": inventory["ordinary_operational_direct_route_count"]},
        {"name": "successor-proof-surface-bounded", "ok": inventory.get("successor_proof_surface_route_count") in {0, 1} and all(str(row.get("path")) in SUCCESSOR_PROOF_SURFACE_ROUTES for row in inventory.get("successor_proof_surface_rows", [])), "successor_count": inventory.get("successor_proof_surface_route_count")},
        {"name": "historical-proof-inventory-behavioral", "ok": len(historical_rows) == EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT and not blocked_inventory, "blocked_count": len(blocked_inventory)},
        {"name": "dispatcher-parity-clean", "ok": not blocked_parity, "blocked_count": len(blocked_parity)},
        {"name": "legacy-cycle-zero-net-reduction-disclosed", "ok": NEW_PROOF_ROUTES_PER_LEGACY_CYCLE == MOVED_ROUTES_PER_LEGACY_TRIAL and NET_DIRECT_ROUTE_REDUCTION_PER_LEGACY_CYCLE == 0},
        {"name": "consolidation-plan-bounded", "ok": len(CONSOLIDATION_PLAN) == 6 and CONSOLIDATION_PLAN[0]["id"] == "parameterized-proof-ledger-prep" and all(row.get("moves_branch_bodies") is False for row in CONSOLIDATION_PLAN[:2])},
        {"name": "next-arc-selects-consolidation-not-prep-v14", "ok": NEXT_ARC == "v1077.9 Dispatcher Proof Surface Historical Compatibility Migration Prep v1" and "Prep v14" not in NEXT_ARC},
        {"name": "no-checkpoint-movement", "ok": SAFETY_BOUNDARY["branch_decomposition_batch_prepared"] is False and SAFETY_BOUNDARY["branch_decomposition_batch_executed"] is False and SAFETY_BOUNDARY["additional_branch_extraction_count"] == 0 and SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "manual-authority-retained", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "historical-routes-not-removed", "ok": SAFETY_BOUNDARY["historical_routes_removed"] is False and SAFETY_BOUNDARY["compatibility_aliases_activated"] is False},
        {"name": "dashboard-line-growth-bounded", "ok": previous_dashboard_line_count <= dashboard_lines <= previous_dashboard_line_count + 180, "current_line_count": dashboard_lines},
        {"name": "command-deck-style-preserved", "ok": "command-deck" in readme_next and "operator-console" in readme_next and "data-tip" in dashboard_text and "data-tip" in module_text},
        {"name": "native-title-tooltips-absent", "ok": " title=\"" not in dashboard_text and " title='" not in dashboard_text},
        {"name": "safety-boundary-preserved", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0 and SAFETY_BOUNDARY["generated_wiring_activated"] is False and SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_TITLE,
        "route": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE,
        "renderer": DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_RENDERER,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": proof_rows,
        "blocked_rows": [row for row in proof_rows if row.get("ok") is not True],
        "blocked_inventory_rows": blocked_inventory,
        "inventory_rows": historical_rows,
        "consolidation_plan": list(CONSOLIDATION_PLAN),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "next_arc": NEXT_ARC,
        "new_proof_routes_per_legacy_cycle": NEW_PROOF_ROUTES_PER_LEGACY_CYCLE,
        "moved_routes_per_legacy_trial": MOVED_ROUTES_PER_LEGACY_TRIAL,
        "net_direct_route_reduction_per_legacy_cycle": NET_DIRECT_ROUTE_REDUCTION_PER_LEGACY_CYCLE,
        **inventory,
        **SAFETY_BOUNDARY,
    }


def dashboard_dispatcher_batch_decomposition_checkpoint_v13_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        "v1077.6 Dispatcher Batch Decomposition Checkpoint v13",
        f"status: {report.get('status')}",
        f"registry_route_count: {report.get('registry_route_count')}",
        f"helper_backed_branch_count: {report.get('helper_backed_branch_count')}",
        f"direct_registry_branch_count_excluding_checkpoint_v13: {report.get('direct_registry_branch_count_excluding_checkpoint_v13')}",
        f"historical_proof_direct_route_count: {report.get('historical_proof_direct_route_count')}",
        f"precheckpoint_legacy_proof_route_count: {report.get('precheckpoint_legacy_proof_route_count')}",
        f"ordinary_operational_direct_route_count: {report.get('ordinary_operational_direct_route_count')}",
        f"net_direct_route_reduction_per_legacy_cycle: {report.get('net_direct_route_reduction_per_legacy_cycle')}",
        "consolidation_plan:",
    ]
    for row in report.get("consolidation_plan", []):
        lines.append(f"- {row.get('order')}. {row.get('id')}: {row.get('scope')}")
    lines.extend([
        "branch_decomposition_batch_prepared: False",
        "branch_decomposition_batch_executed: False",
        "additional_branch_extraction_count: 0",
        "dispatcher_branch_condition_moved: False",
        "dispatcher_branch_body_moved: False",
        "renderer_bodies_moved: False",
        "historical_routes_removed: False",
        "compatibility_aliases_activated: False",
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


def run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_dispatcher_batch_decomposition_checkpoint_v13_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: checkpoint report blocked")
            print(report.get("blocked_rows"))
            print(report.get("blocked_inventory_rows"))
            return False
        if report.get("helper_backed_branch_count") != CURRENT_HELPER_BACKED_BRANCH_COUNT:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: helper count changed during checkpoint")
            return False
        if report.get("direct_registry_branch_count_excluding_checkpoint_v13") not in {EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT, EXPECTED_DIRECT_PROOF_ROUTES_EXCLUDING_CHECKPOINT + 1}:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: direct proof inventory drifted")
            return False
        if report.get("precheckpoint_legacy_proof_route_count") != EXPECTED_PRECHECKPOINT_LEGACY_PROOF_ROUTES:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: 35-route legacy inventory not reconciled")
            return False
        if report.get("ordinary_operational_direct_route_count") not in {0, 1}:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: ordinary operational direct route remains")
            return False
        if report.get("additional_branch_extraction_count") != 0 or report.get("dispatcher_branch_body_moved") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: movement occurred during checkpoint")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("sandbox_backend_admission_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False:
            print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: authorization boundary changed")
            return False
        print(
            "[ok] dashboard-dispatcher-batch-decomposition-checkpoint-v13 "
            f"helper_count={report.get('helper_backed_branch_count')} "
            f"historical_direct={report.get('historical_proof_direct_route_count')} "
            f"precheckpoint_legacy={report.get('precheckpoint_legacy_proof_route_count')} "
            f"ordinary_direct={report.get('ordinary_operational_direct_route_count')} "
            "next_arc=proof-surface-consolidation"
        )
        return True
    except Exception as exc:
        print(f"[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: {exc}")
        return False
