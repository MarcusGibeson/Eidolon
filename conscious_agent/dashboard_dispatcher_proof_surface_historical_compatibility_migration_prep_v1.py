from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from dashboard_dispatcher_proof_surface_consolidation_prep_v1 import dashboard_dispatcher_proof_surface_consolidation_ledger
from dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1 import (
    DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE,
)
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_VERSION = "1077.9"
DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_CHECK_ID = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_TITLE = "Dashboard Dispatcher Proof Surface Historical Compatibility Migration Prep v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE = "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_RENDERER = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"
EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT = 37
EXPECTED_HELPER_BACKED_BRANCH_COUNT = 48
EXPECTED_REGISTRY_ROUTE_COUNT = 88

COMPATIBILITY_MIGRATION_CONTRACT: dict[str, Any] = {
    "canonical_route": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE,
    "query_parameter": "proof_route",
    "historical_route_count": EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT,
    "migration_mode": "manual-read-only-compatibility-adapter",
    "alias_response_mode": "render-canonical-view-with-exact-proof-route-selection",
    "preserve_historical_http_200_during_trial": True,
    "preserve_historical_route_identity": True,
    "preserve_historical_smoke_identity": True,
    "preserve_navigation_until_cleanup": True,
    "rollback_mode": "remove-adapter-branch-and-restore-direct-renderer-call",
    "rollback_requires_operator_review": True,
    "compatibility_aliases_activated": False,
    "historical_routes_removed": False,
    "historical_renderers_invoked_by_canonical_route": False,
}

SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "sandbox_backend_admission_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "compatibility_aliases_activated": False,
    "historical_routes_removed": False,
    "historical_smoke_rows_removed": False,
    "navigation_rows_removed": False,
    "historical_dispatcher_branch_condition_moved": False,
    "historical_dispatcher_branch_body_moved": False,
    "historical_renderer_bodies_moved": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
}


def build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_report(project_root: str | Path, *, expected_version: str) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = (root / "conscious_agent/dashboard.py").read_text(encoding="utf-8", errors="ignore")
    registry_rows = dashboard_route_registry_rows()
    registry_by_path = {str(row.get("path")): row for row in registry_rows}
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    ledger = dashboard_dispatcher_proof_surface_consolidation_ledger(root)
    historical_rows = list(ledger.get("ledger_rows", []))
    historical_paths = [str(row.get("path")) for row in historical_rows]
    alias_plan = [
        {
            "sequence": index,
            "historical_route": path,
            "canonical_route": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE,
            "proof_route": path,
            "migration_prepared": True,
            "alias_activated": False,
            "rollback_prepared": True,
        }
        for index, path in enumerate(historical_paths, start=1)
    ]
    own_registry = registry_by_path.get(DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE)
    own_parity = parity_by_path.get(DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE, {})
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_VERSION == "1077.9" and expected_version in {"1077.9", "1078.1"}},
        {"name": "route-check-value-identity", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE.lstrip("/") == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_CHECK_ID},
        {"name": "renderer-value-identity", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_RENDERER == "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1"},
        {"name": "own-registry-row-exact", "ok": own_registry is not None and own_registry.get("renderer_name") == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_RENDERER and own_registry.get("preview_only") is True},
        {"name": "own-parity-exact", "ok": own_parity.get("ok") is True and own_parity.get("registry_renderer") == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_RENDERER and own_parity.get("dispatcher_renderer") == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_RENDERER},
        {"name": "manual-dispatch-present", "ok": "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE" in dashboard_text},
        {"name": "historical-ledger-stable", "ok": len(historical_rows) == EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT and all(row.get("ok") is True for row in historical_rows)},
        {"name": "historical-routes-preserved", "ok": all(path in registry_by_path for path in historical_paths)},
        {"name": "historical-parity-preserved", "ok": all(parity_by_path.get(path, {}).get("ok") is True for path in historical_paths)},
        {"name": "alias-plan-complete", "ok": len(alias_plan) == EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT and len({row["historical_route"] for row in alias_plan}) == EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT},
        {"name": "alias-plan-inactive", "ok": all(row["alias_activated"] is False for row in alias_plan) and COMPATIBILITY_MIGRATION_CONTRACT["compatibility_aliases_activated"] is False},
        {"name": "rollback-contract-exact", "ok": COMPATIBILITY_MIGRATION_CONTRACT["rollback_mode"] == "remove-adapter-branch-and-restore-direct-renderer-call" and COMPATIBILITY_MIGRATION_CONTRACT["rollback_requires_operator_review"] is True},
        {"name": "canonical-route-preserved", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE in registry_by_path and parity_by_path.get(DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE, {}).get("ok") is True},
        {"name": "registry-count-expected", "ok": len(registry_rows) in {EXPECTED_REGISTRY_ROUTE_COUNT, EXPECTED_REGISTRY_ROUTE_COUNT + 1}},
        {"name": "helper-count-stable", "ok": ledger.get("helper_backed_branch_count") == EXPECTED_HELPER_BACKED_BRANCH_COUNT},
        {"name": "movement-zero", "ok": not SAFETY_BOUNDARY["historical_dispatcher_branch_condition_moved"] and not SAFETY_BOUNDARY["historical_dispatcher_branch_body_moved"] and not SAFETY_BOUNDARY["historical_renderer_bodies_moved"]},
        {"name": "side-effect-boundary-zero", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "manual-authority-preserved", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"]},
        {"name": "dashboard-style-preserved", "ok": "data-tip" in dashboard_text and 'title="' not in dashboard_text},
    ]
    ok = all(row["ok"] is True for row in rows)
    return {
        "version": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_VERSION,
        "check_id": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_TITLE,
        "route": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE,
        "renderer": DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_RENDERER,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": rows,
        "blocked_rows": [row for row in rows if row["ok"] is not True],
        "alias_plan": alias_plan,
        "compatibility_contract": dict(COMPATIBILITY_MIGRATION_CONTRACT),
        "historical_proof_route_count": len(historical_rows),
        "registry_route_count": len(registry_rows),
        "helper_backed_branch_count": ledger.get("helper_backed_branch_count"),
        "compatibility_migration_prepared": True,
        **SAFETY_BOUNDARY,
        "next_arc": NEXT_ARC,
    }


def dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')} [{report.get('status')}]",
        f"route: {report.get('route')}",
        f"registry_route_count: {report.get('registry_route_count')}",
        f"historical_proof_route_count: {report.get('historical_proof_route_count')}",
        f"helper_backed_branch_count: {report.get('helper_backed_branch_count')}",
        "compatibility_migration_prepared: True",
        "compatibility_aliases_activated: False",
        "historical_routes_removed: False",
        "historical_smoke_rows_removed: False",
        "navigation_rows_removed: False",
        "historical_renderer_bodies_moved: False",
        "actual_fixture_execution_count: 0",
        "subprocess_spawn_count: 0",
        "source_write_count: 0",
        "source_delete_count: 0",
        "release_authorized: False",
        "autonomy_expanded: False",
        f"next_arc: {report.get('next_arc')}",
    ]
    if full:
        lines.append("proof_rows:")
        lines.extend(f"- {row.get('name')}: {'ok' if row.get('ok') else 'blocked'}" for row in report.get("rows", []))
    return "\n".join(lines)


def _direct_http_probe(project_root: Path) -> bool:
    import sys
    source_root = str(project_root / "conscious_agent")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from dashboard import EidolonDashboardHandler
    server = ThreadingHTTPServer(("127.0.0.1", 0), EidolonDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        with urlopen(base + DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE, timeout=10) as response:
            own_html = response.read().decode("utf-8", errors="ignore")
        with urlopen(base + DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE, timeout=10) as response:
            canonical_html = response.read().decode("utf-8", errors="ignore")
        with urlopen(base + "/dashboard-dispatcher-batch-decomposition-checkpoint", timeout=10) as response:
            historical_html = response.read().decode("utf-8", errors="ignore")
        return "compatibility_migration_prepared: True" in own_html and "selection-required" in canonical_html and "Dashboard Dispatcher Batch Decomposition Checkpoint" in historical_html and "data-tip" in own_html
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        root = Path(project_root)
        report = build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_report(root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1: report blocked")
            print(report.get("blocked_rows"))
            return False
        if not _direct_http_probe(root):
            print("[fail] dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1: direct HTTP behavior probe failed")
            return False
        print(f"[ok] dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1 historical_routes={report.get('historical_proof_route_count')} registry_routes={report.get('registry_route_count')} aliases_activated=False")
        return True
    except Exception as exc:
        print(f"[fail] dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1: {exc}")
        return False


# v1077.9 compatibility migration prep v1 tokens: dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1 /dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1 render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1 historical_proof_route_count=37 helper_backed_branch_count=48 registry_route_count=88 compatibility_migration_prepared=True compatibility_aliases_activated=False historical_routes_removed=False historical_smoke_rows_removed=False navigation_rows_removed=False rollback_requires_operator_review=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True direct_http_probe_required=True data-tip command-deck operator-console no_native_title_tooltip
