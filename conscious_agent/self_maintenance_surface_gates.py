from __future__ import annotations

from typing import Any

SELF_MAINTENANCE_SURFACE_GATES_VERSION = "1032.0"
SURFACE_GATE_BOUNDARIES: dict[str, bool] = {
    "surface_gates_write_routes": False,
    "surface_gates_change_dashboard": False,
    "surface_gates_mutate_api": False,
    "surface_gates_mutate_cli": False,
    "surface_gates_execute_http_probe": False,
    "surface_gates_continue_automatically": False,
    "surface_gates_review_only": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

def summarize_surface_gates(surfaces: list[dict[str, str]] | None = None) -> dict[str, Any]:
    surfaces = surfaces or []
    missing = [item for item in surfaces if not item.get("dashboard") or not item.get("api") or not item.get("cli")]
    return {
        "version": SELF_MAINTENANCE_SURFACE_GATES_VERSION,
        "state": "route_api_cli_gate_extraction",
        "surface_count": len(surfaces),
        "missing_surface_fields": missing,
        "dashboard_data_tip_required": True,
        "native_title_tooltips_forbidden": True,
        "writes_routes": False,
        "changes_dashboard": False,
        "mutates_api": False,
        "mutates_cli": False,
        "executes_http_probe": False,
        "ok": not missing,
    }

def surface_gate_tokens() -> list[str]:
    return [
        "dashboard route presence checks",
        "API route parity checks",
        "CLI flag parity checks",
        "route health expectations",
        "registry-driven surface checks",
    ]
