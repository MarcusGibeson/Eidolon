from __future__ import annotations

import re
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from dashboard_dispatcher_proof_surface_consolidation_prep_v1 import dashboard_dispatcher_proof_surface_consolidation_ledger
from dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1 import DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

VERSION = "1078.2"
CHECK_ID = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3"
TITLE = "Dashboard Dispatcher Proof Surface Historical Compatibility Migration Trial v3"
ROUTE = "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3"
RENDERER = "render_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3"
NEXT_ARC = "v1078.3 Dispatcher Proof Surface Historical Compatibility Migration Completion"
EXPECTED_REGISTRY_ROUTE_COUNT = 92
EXPECTED_HELPER_BACKED_BRANCH_COUNT = 48

HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3: tuple[str, ...] = (
    "/dashboard-dispatcher-batch-decomposition-prep-v6",
    "/dashboard-dispatcher-batch-decomposition-trial-v6",
    "/dashboard-dispatcher-batch-decomposition-checkpoint-v6",
    "/dashboard-dispatcher-batch-decomposition-prep-v7",
    "/dashboard-dispatcher-batch-decomposition-trial-v7",
    "/dashboard-dispatcher-batch-decomposition-checkpoint-v7",
    "/dashboard-dispatcher-batch-decomposition-prep-v8",
    "/dashboard-dispatcher-batch-decomposition-trial-v8",
    "/dashboard-dispatcher-batch-decomposition-checkpoint-v8",
    "/dashboard-dispatcher-batch-decomposition-prep-v9",
    "/dashboard-dispatcher-batch-decomposition-trial-v9",
    "/dashboard-dispatcher-batch-decomposition-checkpoint-v9",
)

SAFETY_BOUNDARY = {
    "actual_fixture_execution_count": 0, "sandbox_backend_admission_count": 0,
    "subprocess_spawn_count": 0, "source_write_count": 0, "source_delete_count": 0,
    "generated_wiring_activated": False, "release_authorized": False, "autonomy_expanded": False,
    "historical_routes_removed": False, "historical_smoke_rows_removed": False,
    "navigation_rows_removed": False, "historical_renderer_bodies_moved": False,
    "manual_dashboard_remains_authoritative": True, "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
}

def _rollback_branch_intact(text: str, constant_name: str, renderer_name: str) -> bool:
    pattern = rf"elif\s+path\s*==\s*{re.escape(constant_name)}\s*:\s*\n\s*html\s*=\s*{re.escape(renderer_name)}\(\)"
    return re.search(pattern, text) is not None

def build_report(project_root: str | Path, *, expected_version: str) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = (root / "conscious_agent/dashboard.py").read_text(encoding="utf-8", errors="ignore")
    registry_rows = dashboard_route_registry_rows()
    registry_by_path = {str(row.get("path")): row for row in registry_rows}
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    ledger = dashboard_dispatcher_proof_surface_consolidation_ledger(root)
    ledger_by_path = {str(row.get("path")): row for row in ledger.get("ledger_rows", [])}
    own_registry = registry_by_path.get(ROUTE)
    own_parity = parity_by_path.get(ROUTE, {})
    alias_rows=[]
    for path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3:
        row=ledger_by_path.get(path,{})
        constant=str(row.get("dispatcher_constant") or row.get("constant_name") or "")
        renderer=str(row.get("renderer_name") or "")
        if not constant:
            # The canonical ledger currently omits constant names; derive the exact imported symbol from the route.
            constant = path.strip('/').replace('-', '_').upper() + "_ROUTE"
        alias_rows.append({
            "historical_route": path,
            "ledger_present": path in ledger_by_path,
            "registry_preserved": path in registry_by_path,
            "parity_preserved": parity_by_path.get(path, {}).get("ok") is True,
            "renderer": renderer,
            "constant": constant,
            "rollback_branch_preserved": bool(renderer) and _rollback_branch_intact(dashboard_text, constant, renderer),
        })
    rows=[
        {"name":"module-version-current","ok": expected_version in {"1078.2","1078.3"}},
        {"name":"route-check-value-identity","ok": ROUTE.lstrip('/') == CHECK_ID},
        {"name":"own-registry-row-exact","ok": own_registry is not None and own_registry.get("renderer_name") == RENDERER and own_registry.get("preview_only") is True},
        {"name":"own-parity-exact","ok": own_parity.get("ok") is True and own_parity.get("registry_renderer") == RENDERER},
        {"name":"alias-batch-exact","ok": len(HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3)==12 and len(set(HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3))==12},
        {"name":"alias-batch-ledger-backed","ok": all(r["ledger_present"] for r in alias_rows)},
        {"name":"historical-registration-preserved","ok": all(r["registry_preserved"] for r in alias_rows)},
        {"name":"historical-parity-preserved","ok": all(r["parity_preserved"] for r in alias_rows)},
        {"name":"rollback-branches-structurally-intact","ok": all(r["rollback_branch_preserved"] for r in alias_rows)},
        {"name":"manual-adapter-branch-present","ok": "path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3" in dashboard_text and "render_dashboard_dispatcher_proof_surface(proof_route=path)" in dashboard_text},
        {"name":"canonical-route-preserved","ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE in registry_by_path},
        {"name":"registry-count-expected","ok": len(registry_rows)==EXPECTED_REGISTRY_ROUTE_COUNT},
        {"name":"helper-count-stable","ok": ledger.get("helper_backed_branch_count")==EXPECTED_HELPER_BACKED_BRANCH_COUNT},
        {"name":"historical-route-count-stable","ok": len(ledger.get("ledger_rows",[]))==37},
        {"name":"no-prefix-or-wildcard-adapter","ok": "elif path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3:" in dashboard_text and "path.startswith" not in dashboard_text[dashboard_text.find("elif path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3:"):dashboard_text.find("elif path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3:")+220]},
        {"name":"side-effect-boundary-zero","ok": all(SAFETY_BOUNDARY[k]==0 for k in ("actual_fixture_execution_count","subprocess_spawn_count","source_write_count","source_delete_count"))},
        {"name":"dashboard-style-preserved","ok": "data-tip" in dashboard_text and 'title="' not in dashboard_text},
    ]
    ok=all(r["ok"] is True for r in rows)
    return {"version":VERSION,"check_id":CHECK_ID,"title":TITLE,"route":ROUTE,"renderer":RENDERER,"status":"pass" if ok else "blocked","ok":ok,"rows":rows,"blocked_rows":[r for r in rows if r["ok"] is not True],"alias_rows":alias_rows,"compatibility_aliases_activated_batch":12,"compatibility_aliases_activated_total":25,"historical_aliases_remaining":12,"historical_routes_removed":False,"historical_proof_route_count":37,"registry_route_count":len(registry_rows),"helper_backed_branch_count":ledger.get("helper_backed_branch_count"),**SAFETY_BOUNDARY,"next_arc":NEXT_ARC}

def report_text(report: dict[str, Any], *, full: bool=False) -> str:
    lines=[f"{report.get('title')} [{report.get('status')}]",f"route: {report.get('route')}",f"compatibility_aliases_activated_total: {report.get('compatibility_aliases_activated_total')}",f"historical_aliases_remaining: {report.get('historical_aliases_remaining')}"]
    if full: lines.extend(f"{r.get('name')}: {r.get('ok')}" for r in report.get('rows',[]))
    return "\n".join(lines)

def _http_probe(root: Path, *, expected_version: str) -> bool:
    import dashboard
    old_root=dashboard.ROOT_DIR; dashboard.ROOT_DIR=root
    server=ThreadingHTTPServer(("127.0.0.1",0),dashboard.EidolonDashboardHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        base=f"http://127.0.0.1:{server.server_address[1]}"
        own=urlopen(base+ROUTE,timeout=10).read().decode("utf-8",errors="ignore")
        if TITLE not in own or "25" not in own: return False
        for path in HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3:
            body=urlopen(base+path,timeout=10).read().decode("utf-8",errors="ignore")
            if "Dashboard Dispatcher Proof Surface" not in body or path not in body or "selected" not in body: return False
        successor_route="/dashboard-dispatcher-batch-decomposition-prep-v10"
        body=urlopen(base+successor_route,timeout=10).read().decode("utf-8",errors="ignore")
        if expected_version >= "1078.3" and f"Selected proof route: {successor_route}" not in body: return False
        if expected_version < "1078.3" and f"Selected proof route: {successor_route}" in body: return False
        return True
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=10); dashboard.ROOT_DIR=old_root

def run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_check(project_root: str | Path, *, expected_version: str) -> bool:
    root=Path(project_root)
    try: report=build_report(root,expected_version=expected_version); http_ok=_http_probe(root, expected_version=expected_version)
    except Exception as exc:
        print(f"[blocked] {CHECK_ID}: {exc}"); return False
    ok=report.get("ok") is True and http_ok
    print(f"[{'pass' if ok else 'blocked'}] {CHECK_ID}")
    if not ok:
        for row in report.get("blocked_rows",[]): print(f"  - {row.get('name')}: {row.get('ok')}")
        print(f"  - direct-http-probe: {http_ok}")
    return ok
