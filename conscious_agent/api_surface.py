from __future__ import annotations

from typing import Any

API_SURFACE_VERSION = "1032.0"
DEFAULT_API_SURFACE_HELPERS = [
    {"name": "api_route_metadata_binder", "purpose": "summarize API route metadata", "changes_behavior": False},
    {"name": "runtime_json_response_helper", "purpose": "normalize runtime JSON response shapes", "changes_behavior": False},
    {"name": "api_error_response_helper", "purpose": "document error response patterns", "changes_behavior": False},
    {"name": "dynamic_runtime_route_summary", "purpose": "summarize dynamic runtime route coverage", "changes_behavior": False},
    {"name": "api_route_parity_checker", "purpose": "flag missing API surfaces for review only", "auto_fixes": False},
]


def api_route_tokens() -> list[str]:
    return [
        "/api/dashboard-extraction-map/layer",
        "/api/dashboard-component-audit/layer",
        "/api/api-surface-audit/layer",
        "/api/cli-surface-audit/layer",
        "/api/interface-modularization-audit/layer",
    ]


def build_api_surface_summary(api_text: str = "", route_tokens: list[str] | None = None) -> dict[str, Any]:
    routes = route_tokens or api_route_tokens()
    present = [route for route in routes if route in api_text] if api_text else []
    return {
        "version": API_SURFACE_VERSION,
        "helper_count": len(DEFAULT_API_SURFACE_HELPERS),
        "helpers": DEFAULT_API_SURFACE_HELPERS,
        "route_count": len(routes),
        "routes_present": present,
        "routes_missing": [route for route in routes if route not in present] if api_text else [],
        "uses_dynamic_runtime_route_map": "SUPERVISED_RUNTIME_ROUTE_MAP" in api_text if api_text else True,
        "changes_behavior": False,
        "auto_fixes": False,
        "executes_commands": False,
    }


def api_surface_summary_lines(summary: dict[str, Any]) -> list[str]:
    return [
        f"- API helper count: {summary.get('helper_count', 0)}.",
        f"- API routes present: {len(summary.get('routes_present', []))}/{summary.get('route_count', 0)}.",
        f"- Dynamic runtime route map preserved: {summary.get('uses_dynamic_runtime_route_map', False)}.",
        f"- API behavior changed: {summary.get('changes_behavior', False)}.",
        f"- API auto-fixes enabled: {summary.get('auto_fixes', False)}.",
    ]
