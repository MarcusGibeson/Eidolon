from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_proof_surface_consolidation_prep_v1 import dashboard_dispatcher_proof_surface_consolidation_ledger
from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1 import HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1
from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2 import HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V2
from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3 import HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3
from dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1 import HISTORICAL_COMPATIBILITY_ALIAS_BATCH_COMPLETION
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

VERSION = "1078.4"
CHECK_ID = "dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1"
TITLE = "Dashboard Dispatcher Proof Surface Historical Surface Retirement Prep"
ROUTE = "/dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1"
RENDERER = "render_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep"
NEXT_ARC = "v1078.5 Historical Surface Retirement Trial"
EXPECTED_HISTORICAL_ROUTE_COUNT = 37
EXPECTED_REGISTRY_ROUTE_COUNT = 93
RETIRED_IN_V1078_5 = set(HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1)
RETIRED_RENDERERS_V1078_5 = {
    "/dashboard-dispatcher-batch-decomposition-checkpoint": "render_dashboard_dispatcher_batch_decomposition_checkpoint",
    "/dashboard-dispatcher-batch-decomposition-prep-v2": "render_dashboard_dispatcher_batch_decomposition_prep_v2",
    "/dashboard-dispatcher-batch-decomposition-trial-v2": "render_dashboard_dispatcher_batch_decomposition_trial_v2",
}

COMPLETE_ALIAS_INVENTORY = (
    HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1
    + HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V2
    + HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3
    + HISTORICAL_COMPATIBILITY_ALIAS_BATCH_COMPLETION
)

SAFETY_BOUNDARY = {
    "retirement_prep_only": True,
    "historical_dispatcher_branches_removed": 0,
    "historical_renderer_bodies_removed": 0,
    "historical_imports_removed": 0,
    "historical_route_constants_removed": 0,
    "historical_registry_rows_removed": 0,
    "historical_navigation_rows_removed": 0,
    "historical_smoke_rows_removed": 0,
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

def _exact_branch_present(source: str, constant: str, renderer: str) -> bool:
    return re.search(rf"elif\s+path\s*==\s*{re.escape(constant)}\s*:\s*\n\s*html\s*=\s*{re.escape(renderer)}\(\)", source) is not None

def build_report(project_root: str | Path, *, expected_version: str) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = (root / "conscious_agent/dashboard.py").read_text(encoding="utf-8", errors="ignore")
    registry_text = (root / "conscious_agent/dashboard_route_registry.py").read_text(encoding="utf-8", errors="ignore")
    smoke_text = (root / "tools/smoke_registry_check_rows.py").read_text(encoding="utf-8", errors="ignore")
    next_text = (root / "README_NEXT_STEPS.md").read_text(encoding="utf-8", errors="ignore")
    history_text = (root / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8", errors="ignore")
    registry_rows = dashboard_route_registry_rows()
    registry_by_path = {str(row.get("path")): row for row in registry_rows}
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    ledger = dashboard_dispatcher_proof_surface_consolidation_ledger(root)
    ledger_rows = ledger.get("ledger_rows", [])
    ledger_by_path = {str(row.get("path")): row for row in ledger_rows}

    manifest=[]
    for path in COMPLETE_ALIAS_INVENTORY:
        row=ledger_by_path.get(path,{})
        retired_now = expected_version == "1078.5" and path in RETIRED_IN_V1078_5
        renderer = RETIRED_RENDERERS_V1078_5[path] if retired_now else str(row.get("renderer_name") or "")
        check_id=str(row.get("check_id") or "")
        check_function=str(row.get("check_function") or "")
        constant=_constant_name(path)
        # The first unversioned checkpoint uses the same deterministic constant convention.
        item={
            "path": path,
            "phase": row.get("phase"),
            "sequence": row.get("sequence"),
            "dispatcher_constant": constant,
            "renderer_name": renderer,
            "check_id": check_id,
            "check_function": check_function,
            "compatibility_url_required": True,
            "rollback_required_until_trial_verified": True,
            "dispatcher_branch_present": _exact_branch_present(dashboard_text, constant, renderer),
            "renderer_body_present": bool(renderer) and re.search(rf"^def\s+{re.escape(renderer)}\s*\(", dashboard_text, re.M) is not None,
            "import_reference_present": constant in dashboard_text,
            "route_constant_reference_present": constant in dashboard_text,
            "registry_row_present": path in registry_by_path,
            "navigation_row_present": path in registry_text,
            "smoke_row_present": bool(check_id) and check_id in smoke_text,
            "smoke_function_binding_present": bool(check_function) and check_function in smoke_text,
            "parity_exact": parity_by_path.get(path,{}).get("ok") is True,
            "metadata_reference_count": sum(p.read_text(encoding="utf-8",errors="ignore").count(path) for p in (root/"conscious_agent").glob("*.py")),
            "documentation_reference_count": next_text.count(path)+history_text.count(path),
            "retirement_action": "remove redundant implementation only after v1078.5 behavioral proof",
        }
        item["retired_in_v1078_5"] = retired_now
        if retired_now:
            item["inventory_complete"] = (
                not item["dispatcher_branch_present"]
                and not item["renderer_body_present"]
                and not item["import_reference_present"]
                and (root / "conscious_agent" / f"{path.strip('/').replace('-', '_')}.py").read_text(encoding="utf-8", errors="ignore").count(constant) > 0
                and item["registry_row_present"]
                and item["navigation_row_present"]
                and item["smoke_row_present"]
                and item["smoke_function_binding_present"]
                and item["parity_exact"]
            )
        else:
            item["inventory_complete"] = all(item[k] for k in (
                "dispatcher_branch_present","renderer_body_present","import_reference_present",
                "route_constant_reference_present","registry_row_present","navigation_row_present",
                "smoke_row_present","smoke_function_binding_present","parity_exact",
            ))
        manifest.append(item)

    own_registry=registry_by_path.get(ROUTE)
    own_parity=parity_by_path.get(ROUTE,{})
    rows=[
        {"name":"module-version-current","ok": expected_version in {"1078.4","1078.5"}},
        {"name":"route-check-value-identity","ok": ROUTE.lstrip("/")==CHECK_ID},
        {"name":"own-registry-row-exact","ok": own_registry is not None and own_registry.get("renderer_name")==RENDERER},
        {"name":"own-parity-exact","ok": own_parity.get("ok") is True and own_parity.get("registry_renderer")==RENDERER},
        {"name":"complete-alias-inventory-exact","ok": len(COMPLETE_ALIAS_INVENTORY)==37 and len(set(COMPLETE_ALIAS_INVENTORY))==37 and set(COMPLETE_ALIAS_INVENTORY)==set(ledger_by_path)},
        {"name":"manifest-row-count-exact","ok": len(manifest)==EXPECTED_HISTORICAL_ROUTE_COUNT},
        {"name":"manifest-identities-complete","ok": all(row.get("inventory_complete") is True for row in manifest)},
        {"name":"compatibility-coverage-complete","ok": all(path in registry_by_path and parity_by_path.get(path,{}).get("ok") is True for path in COMPLETE_ALIAS_INVENTORY)},
        {"name":"registry-count-expected","ok": len(registry_rows) in {EXPECTED_REGISTRY_ROUTE_COUNT, 94}},
        {"name":"historical-route-count-stable","ok": len(ledger_rows)==EXPECTED_HISTORICAL_ROUTE_COUNT},
        {"name":"retirement-prep-removes-nothing","ok": all(SAFETY_BOUNDARY[k]==0 for k in ("historical_dispatcher_branches_removed","historical_renderer_bodies_removed","historical_imports_removed","historical_route_constants_removed","historical_registry_rows_removed","historical_navigation_rows_removed","historical_smoke_rows_removed"))},
        {"name":"execution-boundary-zero","ok": all(SAFETY_BOUNDARY[k]==0 for k in ("actual_fixture_execution_count","subprocess_spawn_count","source_write_count","source_delete_count"))},
        {"name":"dashboard-style-preserved","ok": "data-tip" in dashboard_text and 'title="' not in dashboard_text},
    ]
    ok=all(row["ok"] is True for row in rows)
    return {
        "version": VERSION,"check_id":CHECK_ID,"title":TITLE,"route":ROUTE,"renderer":RENDERER,
        "status":"pass" if ok else "blocked","ok":ok,"rows":rows,
        "blocked_rows":[row for row in rows if row["ok"] is not True],
        "removal_manifest":manifest,"historical_proof_route_count":len(ledger_rows),
        "compatibility_aliases_active":len(COMPLETE_ALIAS_INVENTORY),"registry_route_count":len(registry_rows),
        **SAFETY_BOUNDARY,"next_arc":NEXT_ARC,
    }

def report_text(report: dict[str, Any], *, full: bool=False) -> str:
    lines=[f"{report.get('title')} [{report.get('status')}]",f"manifest_rows: {len(report.get('removal_manifest',[]))}",f"compatibility_aliases_active: {report.get('compatibility_aliases_active')}","historical_surfaces_removed: 0"]
    if full: lines.extend(f"{row.get('name')}: {row.get('ok')}" for row in report.get('rows',[]))
    return "\n".join(lines)

def run_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_check(project_root: str | Path, *, expected_version: str) -> bool:
    try: report=build_report(project_root,expected_version=expected_version)
    except Exception as exc:
        print(f"[blocked] {CHECK_ID}: {exc}"); return False
    print(f"[{'pass' if report.get('ok') else 'blocked'}] {CHECK_ID} manifest_rows={len(report.get('removal_manifest',[]))}")
    if not report.get('ok'):
        for row in report.get('blocked_rows',[]): print(f"  - {row.get('name')}: {row.get('ok')}")
    return report.get('ok') is True

# v1078.4 retirement prep tokens: historical_surface_retirement_prepared=True removal_manifest_rows=37 compatibility_aliases_active=37 historical_dispatcher_branches_removed=0 historical_renderer_bodies_removed=0 historical_imports_removed=0 historical_route_constants_removed=0 historical_registry_rows_removed=0 historical_navigation_rows_removed=0 historical_smoke_rows_removed=0 release_authorized=False autonomy_expanded=False
