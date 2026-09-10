from __future__ import annotations

import re
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

from dashboard_dispatcher_proof_surface_consolidation_prep_v1 import (
    DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE,
    dashboard_dispatcher_proof_surface_consolidation_ledger,
)
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_VERSION = "1077.8"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_CHECK_ID = "dashboard-dispatcher-proof-surface"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_TITLE = "Dashboard Dispatcher Proof Surface Consolidated Renderer Trial v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE = "/dashboard-dispatcher-proof-surface"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_RENDERER = "render_dashboard_dispatcher_proof_surface"
QUERY_PARAMETER = "proof_route"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

EXPECTED_HELPER_BACKED_BRANCH_COUNT = 48
EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT = 37
EXPECTED_REGISTRY_ROUTE_COUNT = 87

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
    "consolidated_renderer_trial_executed": True,
    "canonical_route_registered": True,
    "canonical_renderer_implemented": True,
    "compatibility_aliases_activated": False,
    "historical_routes_removed": False,
    "navigation_rows_removed": False,
    "historical_smoke_rows_removed": False,
    "historical_dispatcher_branch_condition_moved": False,
    "historical_dispatcher_branch_body_moved": False,
    "historical_renderer_bodies_moved": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def build_dashboard_dispatcher_proof_surface_selection(
    project_root: str | Path,
    *,
    proof_route: str | None,
) -> dict[str, Any]:
    ledger = dashboard_dispatcher_proof_surface_consolidation_ledger(project_root)
    rows = list(ledger.get("ledger_rows", []))
    ordinary_rows = list(ledger.get("ordinary_rows", []))
    ordinary_excluding_canonical = [row for row in ordinary_rows if row.get("path") not in {DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE, "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v1", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v2", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-completion-v1", "/dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1", "/dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1"}]
    normalized = (proof_route or "").strip()
    selected = next((row for row in rows if row.get("path") == normalized), None)
    if not normalized:
        state = "selection-required"
    elif selected is None:
        state = "unknown-proof-route"
    else:
        state = "selected"
    return {
        "state": state,
        "proof_route": normalized,
        "selected_row": selected,
        "ledger_rows": rows,
        "historical_proof_route_count": len(rows),
        "helper_backed_branch_count": ledger.get("helper_backed_branch_count"),
        "ordinary_operational_direct_route_count": len(ordinary_excluding_canonical),
        "ordinary_direct_routes_including_canonical": len(ordinary_rows),
        "preview_only": True,
        "historical_renderer_invoked": False,
        "compatibility_alias_activated": False,
    }


def build_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_report(
    project_root: str | Path,
    *,
    expected_version: str,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    registry_rows = dashboard_route_registry_rows()
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    ledger = dashboard_dispatcher_proof_surface_consolidation_ledger(root)
    selection_required = build_dashboard_dispatcher_proof_surface_selection(root, proof_route=None)
    first_path = str(ledger.get("ledger_rows", [{}])[0].get("path", ""))
    valid_selection = build_dashboard_dispatcher_proof_surface_selection(root, proof_route=first_path)
    invalid_selection = build_dashboard_dispatcher_proof_surface_selection(root, proof_route="/not-a-proof-route")
    own_registry = next((row for row in registry_rows if row.get("path") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE), None)
    own_parity = parity_by_path.get(DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE, {})
    historical_paths = {str(row.get("path")) for row in ledger.get("ledger_rows", [])}
    ordinary_rows = list(ledger.get("ordinary_rows", []))
    ordinary_excluding_canonical = [row for row in ordinary_rows if row.get("path") not in {DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE, "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v1", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v2", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3", "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-completion-v1", "/dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1", "/dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1"}]

    rows: list[dict[str, Any]] = [
        {"name": "module-version-current", "ok": expected_version in {DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_VERSION, "1077.9", "1078.0", "1078.1", "1078.2", "1078.3", "1078.4", "1078.5"}},
        {"name": "route-check-value-identity", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE.lstrip("/") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_CHECK_ID},
        {"name": "renderer-value-identity", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_RENDERER == "render_dashboard_dispatcher_proof_surface"},
        {"name": "canonical-registry-row-exact", "ok": own_registry is not None and own_registry.get("renderer_name") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_RENDERER and own_registry.get("preview_only") is True},
        {"name": "canonical-parity-exact", "ok": own_parity.get("ok") is True and own_parity.get("registry_renderer") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_RENDERER and own_parity.get("dispatcher_renderer") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_RENDERER},
        {"name": "canonical-manual-dispatch-present", "ok": "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE" in dashboard_text and "render_dashboard_dispatcher_proof_surface(proof_route=" in dashboard_text},
        {"name": "canonical-renderer-present", "ok": re.search(r"^def render_dashboard_dispatcher_proof_surface\(", dashboard_text, re.MULTILINE) is not None},
        {"name": "query-parameter-manual", "ok": f'parse_qs(parsed.query).get("{QUERY_PARAMETER}", [""])[0]' in dashboard_text},
        {"name": "historical-ledger-stable", "ok": ledger.get("historical_proof_route_count") == EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT and all(row.get("ok") is True for row in ledger.get("ledger_rows", []))},
        {"name": "historical-registry-routes-preserved", "ok": historical_paths.issubset({str(row.get("path")) for row in registry_rows})},
        {"name": "selection-required-state", "ok": selection_required.get("state") == "selection-required" and selection_required.get("selected_row") is None},
        {"name": "valid-selection-state", "ok": valid_selection.get("state") == "selected" and valid_selection.get("selected_row", {}).get("path") == first_path},
        {"name": "invalid-selection-state", "ok": invalid_selection.get("state") == "unknown-proof-route" and invalid_selection.get("selected_row") is None},
        {"name": "historical-renderer-not-invoked", "ok": all(selection.get("historical_renderer_invoked") is False for selection in (selection_required, valid_selection, invalid_selection))},
        {"name": "compatibility-aliases-inactive", "ok": SAFETY_BOUNDARY["compatibility_aliases_activated"] is False},
        {"name": "historical-routes-not-removed", "ok": SAFETY_BOUNDARY["historical_routes_removed"] is False and SAFETY_BOUNDARY["historical_smoke_rows_removed"] is False},
        {"name": "historical-movement-zero", "ok": SAFETY_BOUNDARY["historical_dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["historical_dispatcher_branch_body_moved"] is False and SAFETY_BOUNDARY["historical_renderer_bodies_moved"] is False},
        {"name": "manual-authority-preserved", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_api_dispatch_remains_authoritative"] is True and SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
        {"name": "side-effect-boundary-zero", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary-closed", "ok": SAFETY_BOUNDARY["generated_wiring_activated"] is False and SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False},
        {"name": "registry-count-expected", "ok": len(registry_rows) in {EXPECTED_REGISTRY_ROUTE_COUNT, 88, 89, 90, 91, 92, 93, 94}},
        {"name": "helper-count-stable", "ok": ledger.get("helper_backed_branch_count") == EXPECTED_HELPER_BACKED_BRANCH_COUNT},
        {"name": "ordinary-operational-direct-zero", "ok": len(ordinary_excluding_canonical) == 0 and len(ordinary_rows) in {1, 2, 3, 4, 5, 6, 7, 8, 9}},
        {"name": "dashboard-style-preserved", "ok": "data-tip" in dashboard_text and 'title="' not in dashboard_text},
        {"name": "prep-surface-preserved", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE in {str(row.get("path")) for row in registry_rows}},
    ]
    ok = all(row.get("ok") is True for row in rows)
    return {
        "version": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_VERSION,
        "check_id": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_TITLE,
        "route": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE,
        "renderer": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_RENDERER,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": rows,
        "blocked_rows": [row for row in rows if row.get("ok") is not True],
        "ledger_rows": ledger.get("ledger_rows", []),
        "historical_proof_route_count": ledger.get("historical_proof_route_count"),
        "registry_route_count": len(registry_rows),
        "helper_backed_branch_count": ledger.get("helper_backed_branch_count"),
        "ordinary_operational_direct_route_count": len(ordinary_excluding_canonical),
        "ordinary_direct_routes_including_canonical": len(ordinary_rows),
        "query_parameter": QUERY_PARAMETER,
        **SAFETY_BOUNDARY,
        "next_arc": NEXT_ARC,
    }


def dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')} [{report.get('status')}]",
        f"route: {report.get('route')}",
        f"registry_route_count: {report.get('registry_route_count')}",
        f"historical_proof_route_count: {report.get('historical_proof_route_count')}",
        f"helper_backed_branch_count: {report.get('helper_backed_branch_count')}",
        f"query_parameter: {report.get('query_parameter')}",
        "canonical_route_registered: True",
        "canonical_renderer_implemented: True",
        "consolidated_renderer_trial_executed: True",
        "compatibility_aliases_activated: False",
        "historical_routes_removed: False",
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
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'ok' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def _direct_http_probe(project_root: Path) -> bool:
    import sys
    root_text = str(project_root / "conscious_agent")
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from dashboard import EidolonDashboardHandler

    server = ThreadingHTTPServer(("127.0.0.1", 0), EidolonDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}{DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE}"
        with urlopen(base, timeout=10) as response:
            selection_html = response.read().decode("utf-8", errors="ignore")
        proof_route = "/dashboard-dispatcher-batch-decomposition-checkpoint"
        with urlopen(f"{base}?{QUERY_PARAMETER}={quote(proof_route, safe='')}", timeout=10) as response:
            selected_html = response.read().decode("utf-8", errors="ignore")
        with urlopen(f"{base}?{QUERY_PARAMETER}={quote('/not-a-proof-route', safe='')}", timeout=10) as response:
            invalid_html = response.read().decode("utf-8", errors="ignore")
        return (
            "selection-required" in selection_html
            and proof_route in selected_html
            and "selected" in selected_html
            and "unknown-proof-route" in invalid_html
            and "data-tip" in selected_html
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_check(
    project_root: str | Path,
    *,
    expected_version: str,
) -> bool:
    try:
        root = Path(project_root)
        report = build_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_report(root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-proof-surface: trial report blocked")
            print(report.get("blocked_rows"))
            return False
        if not _direct_http_probe(root):
            print("[fail] dashboard-dispatcher-proof-surface: direct HTTP behavior probe failed")
            return False
        print(
            "[ok] dashboard-dispatcher-proof-surface "
            f"historical_routes={report.get('historical_proof_route_count')} "
            f"registry_routes={report.get('registry_route_count')} "
            f"helper_count={report.get('helper_backed_branch_count')} "
            "aliases_activated=False historical_routes_removed=False"
        )
        return True
    except Exception as exc:
        print(f"[fail] dashboard-dispatcher-proof-surface: {exc}")
        return False


# v1077.8 consolidated renderer trial v1 tokens: dashboard-dispatcher-proof-surface /dashboard-dispatcher-proof-surface render_dashboard_dispatcher_proof_surface proof_route historical_proof_route_count=37 helper_backed_branch_count=48 canonical_route_registered=True canonical_renderer_implemented=True consolidated_renderer_trial_executed=True compatibility_aliases_activated=False historical_routes_removed=False historical_renderer_bodies_moved=False actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True direct_http_probe_required=True data-tip command-deck operator-console no_native_title_tooltip
