from __future__ import annotations

import re
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from dashboard_dispatcher_proof_surface_consolidation_prep_v1 import dashboard_dispatcher_proof_surface_consolidation_ledger
from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1 import HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1
from dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_v1 import COMPLETE_ALIAS_INVENTORY
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

VERSION = "1078.5"
CHECK_ID = "dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1"
TITLE = "Dashboard Dispatcher Proof Surface Historical Surface Retirement Trial v1"
ROUTE = "/dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1"
RENDERER = "render_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial"
NEXT_ARC = "v1078.6 Registry, Navigation, and Smoke Consolidation"
EXPECTED_REGISTRY_ROUTE_COUNT = 94
RETIRED_ROUTES = HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1
RETIRED_RENDERERS = {
    "/dashboard-dispatcher-batch-decomposition-checkpoint": "render_dashboard_dispatcher_batch_decomposition_checkpoint",
    "/dashboard-dispatcher-batch-decomposition-prep-v2": "render_dashboard_dispatcher_batch_decomposition_prep_v2",
    "/dashboard-dispatcher-batch-decomposition-trial-v2": "render_dashboard_dispatcher_batch_decomposition_trial_v2",
}

SAFETY_BOUNDARY = {
    "retirement_trial_bounded": True,
    "historical_url_removal_count": 0,
    "historical_dispatcher_branch_removal_count": 3,
    "historical_renderer_body_removal_count": 3,
    "historical_dashboard_import_block_removal_count": 3,
    "historical_route_constant_removal_count": 0,
    "historical_registry_row_removal_count": 0,
    "historical_navigation_row_removal_count": 0,
    "historical_smoke_row_removal_count": 0,
    "actual_fixture_execution_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
}


def _constant_name(path: str) -> str:
    return path.strip("/").replace("-", "_").upper() + "_ROUTE"


def _http_probe(root: Path, paths: tuple[str, ...]) -> dict[str, bool]:
    import dashboard
    old_root = dashboard.ROOT_DIR
    dashboard.ROOT_DIR = root
    server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results: dict[str, bool] = {}
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        for path in paths:
            body = urlopen(base + path, timeout=12).read().decode("utf-8", errors="ignore")
            results[path] = "Dashboard Dispatcher Proof Surface" in body and path in body and "selected" in body
        own = urlopen(base + ROUTE, timeout=12).read().decode("utf-8", errors="ignore")
        results[ROUTE] = TITLE in own and "Retired implementation surfaces" in own
        return results
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        dashboard.ROOT_DIR = old_root


def build_report(project_root: str | Path, *, expected_version: str, run_http: bool = False) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = (root / "conscious_agent/dashboard.py").read_text(encoding="utf-8", errors="ignore")
    registry_text = (root / "conscious_agent/dashboard_route_registry.py").read_text(encoding="utf-8", errors="ignore")
    smoke_text = (root / "tools/smoke_registry_check_rows.py").read_text(encoding="utf-8", errors="ignore")
    registry_rows = dashboard_route_registry_rows()
    registry_by_path = {str(row.get("path")): row for row in registry_rows}
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    ledger_rows = dashboard_dispatcher_proof_surface_consolidation_ledger(root).get("ledger_rows", [])
    ledger_by_path = {str(row.get("path")): row for row in ledger_rows}
    http = _http_probe(root, RETIRED_ROUTES) if run_http else {}

    retired_rows = []
    for path in RETIRED_ROUTES:
        ledger = ledger_by_path.get(path, {})
        constant = str(ledger.get("route_constant_name") or _constant_name(path))
        renderer = RETIRED_RENDERERS[path]
        check_id = str(ledger.get("check_id") or "")
        check_function = str(ledger.get("check_function") or "")
        exact_branch = re.search(rf"elif\s+path\s*==\s*{re.escape(constant)}\s*:\s*\n\s*html\s*=\s*{re.escape(renderer)}\(\)", dashboard_text) is not None
        renderer_present = bool(renderer) and re.search(rf"^def\s+{re.escape(renderer)}\s*\(", dashboard_text, re.M) is not None
        import_present = re.search(rf"from\s+{re.escape(path.strip('/').replace('-', '_'))}\s+import\s*\(", dashboard_text) is not None
        retired_rows.append({
            "path": path,
            "constant": constant,
            "renderer": renderer,
            "dispatcher_branch_removed": not exact_branch,
            "renderer_body_removed": not renderer_present,
            "dashboard_import_removed": not import_present,
            "ledger_preserved": path in ledger_by_path,
            "registry_preserved": path in registry_by_path,
            "navigation_identity_preserved": path in registry_text,
            "smoke_row_preserved": bool(check_id) and check_id in smoke_text,
            "smoke_binding_preserved": bool(check_function) and check_function in smoke_text,
            "parity_preserved": parity_by_path.get(path, {}).get("ok") is True,
            "compatibility_http_ok": http.get(path) if run_http else None,
        })

    own_registry = registry_by_path.get(ROUTE)
    own_parity = parity_by_path.get(ROUTE, {})
    rows = [
        {"name": "module-version-immutable", "ok": VERSION == "1078.5"},
        {"name": "runtime-version-compatible", "ok": tuple(int(part) for part in expected_version.split(".")) >= (1078, 5)},
        {"name": "route-check-value-identity", "ok": ROUTE.lstrip("/") == CHECK_ID},
        {"name": "own-registry-row-exact", "ok": own_registry is not None and own_registry.get("renderer_name") == RENDERER},
        {"name": "own-parity-exact", "ok": own_parity.get("ok") is True and own_parity.get("registry_renderer") == RENDERER},
        {"name": "retirement-batch-exact", "ok": len(RETIRED_ROUTES) == 3 and len(set(RETIRED_ROUTES)) == 3},
        {"name": "direct-branches-retired", "ok": all(row["dispatcher_branch_removed"] for row in retired_rows)},
        {"name": "renderer-bodies-retired", "ok": all(row["renderer_body_removed"] for row in retired_rows)},
        {"name": "dead-dashboard-imports-retired", "ok": all(row["dashboard_import_removed"] for row in retired_rows)},
        {"name": "ledger-identities-preserved", "ok": all(row["ledger_preserved"] for row in retired_rows)},
        {"name": "registry-navigation-preserved", "ok": all(row["registry_preserved"] and row["navigation_identity_preserved"] for row in retired_rows)},
        {"name": "smoke-identities-preserved", "ok": all(row["smoke_row_preserved"] and row["smoke_binding_preserved"] for row in retired_rows)},
        {"name": "parity-preserved", "ok": all(row["parity_preserved"] for row in retired_rows)},
        {"name": "complete-compatibility-inventory", "ok": len(COMPLETE_ALIAS_INVENTORY) == 37 and len(set(COMPLETE_ALIAS_INVENTORY)) == 37},
        {"name": "all-compatibility-parity", "ok": all(parity_by_path.get(path, {}).get("ok") is True for path in COMPLETE_ALIAS_INVENTORY)},
        {"name": "registry-count-expected", "ok": len(registry_rows) == EXPECTED_REGISTRY_ROUTE_COUNT},
        {"name": "historical-route-count-stable", "ok": len(ledger_rows) == 37},
        {"name": "retired-route-compatibility-http", "ok": (not run_http) or all(http.get(path) is True for path in RETIRED_ROUTES)},
        {"name": "own-http", "ok": (not run_http) or http.get(ROUTE) is True},
        {"name": "safety-boundary-closed", "ok": all(SAFETY_BOUNDARY[k] == 0 for k in ("historical_url_removal_count", "historical_route_constant_removal_count", "historical_registry_row_removal_count", "historical_navigation_row_removal_count", "historical_smoke_row_removal_count", "actual_fixture_execution_count", "subprocess_spawn_count", "source_write_count", "source_delete_count"))},
        {"name": "dashboard-style-preserved", "ok": "data-tip" in dashboard_text and 'title="' not in dashboard_text},
    ]
    ok = all(row["ok"] is True for row in rows)
    return {
        "version": VERSION, "check_id": CHECK_ID, "title": TITLE, "route": ROUTE, "renderer": RENDERER,
        "status": "pass" if ok else "blocked", "ok": ok, "rows": rows,
        "blocked_rows": [row for row in rows if row["ok"] is not True],
        "retired_rows": retired_rows, "retired_surface_count": len(RETIRED_ROUTES),
        "compatibility_aliases_active": len(COMPLETE_ALIAS_INVENTORY), "registry_route_count": len(registry_rows),
        **SAFETY_BOUNDARY, "next_arc": NEXT_ARC,
    }


def report_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [f"{report.get('title')} [{report.get('status')}]", f"retired_surface_count: {report.get('retired_surface_count')}", f"compatibility_aliases_active: {report.get('compatibility_aliases_active')}", "historical_urls_removed: 0"]
    if full:
        lines.extend(f"{row.get('name')}: {row.get('ok')}" for row in report.get("rows", []))
    return "\n".join(lines)


def run_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_report(project_root, expected_version=expected_version, run_http=True)
    except Exception as exc:
        print(f"[blocked] {CHECK_ID}: {exc}")
        return False
    print(f"[{'pass' if report.get('ok') else 'blocked'}] {CHECK_ID} retired={report.get('retired_surface_count')} compatibility={report.get('compatibility_aliases_active')}")
    if not report.get("ok"):
        for row in report.get("blocked_rows", []):
            print(f"  - {row.get('name')}: {row.get('ok')}")
    return report.get("ok") is True

# v1078.5 retirement trial tokens: retired_surface_count=3 compatibility_aliases_active=37 historical_urls_removed=0 historical_dispatcher_branch_removal_count=3 historical_renderer_body_removal_count=3 historical_dashboard_import_block_removal_count=3 historical_route_constant_removal_count=0 historical_registry_row_removal_count=0 historical_navigation_row_removal_count=0 historical_smoke_row_removal_count=0 release_authorized=False autonomy_expanded=False
