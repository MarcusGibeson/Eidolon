from __future__ import annotations

from typing import Any

DASHBOARD_COMPONENTS_VERSION = "350.0"

DEFAULT_DASHBOARD_COMPONENTS = [
    {"name": "console_card", "purpose": "render command-deck cards with existing classes", "changes_visual_contract": False},
    {"name": "status_row", "purpose": "render compact status rows for dashboard audits", "changes_visual_contract": False},
    {"name": "audit_section", "purpose": "render reusable audit sections without changing route behavior", "changes_visual_contract": False},
    {"name": "packet_summary", "purpose": "render packet summary blocks for operator review", "changes_visual_contract": False},
    {"name": "tooltip_safe_nav", "purpose": "preserve custom data-tip hover metadata without native title attributes", "uses_native_title": False},
]


def dashboard_route_tokens() -> list[str]:
    return [
        "/dashboard-extraction-map",
        "/dashboard-component-audit",
        "/api-surface-audit",
        "/cli-surface-audit",
        "/interface-modularization-audit",
    ]


def native_nav_title_regression_present(dashboard_text: str) -> bool:
    for line in dashboard_text.splitlines():
        if "data-tip" in line and "title=" in line:
            return True
        if "nav" in line.lower() and "title=" in line and "data-route-title" not in line:
            return True
    return False


def build_dashboard_component_summary(dashboard_text: str = "", nav_routes: list[str] | None = None) -> dict[str, Any]:
    routes = nav_routes or dashboard_route_tokens()
    present = [route for route in routes if route in dashboard_text] if dashboard_text else []
    return {
        "version": DASHBOARD_COMPONENTS_VERSION,
        "component_count": len(DEFAULT_DASHBOARD_COMPONENTS),
        "components": DEFAULT_DASHBOARD_COMPONENTS,
        "route_count": len(routes),
        "routes_present": present,
        "routes_missing": [route for route in routes if route not in present] if dashboard_text else [],
        "data_tip_count": dashboard_text.count("data-tip") if dashboard_text else 0,
        "native_nav_title_regression": native_nav_title_regression_present(dashboard_text) if dashboard_text else False,
        "command_deck_preserved": "command" in dashboard_text.lower() or "mini-card" in dashboard_text if dashboard_text else True,
        "changes_visual_contract": False,
        "removes_routes": False,
        "redesigns_dashboard": False,
    }


def tooltip_safe_nav_metadata(routes: list[tuple[str, str, str]] | None = None) -> list[dict[str, Any]]:
    rows = []
    for route, label, tip in routes or []:
        rows.append({"route": route, "label": label, "data_tip": tip, "native_title": None, "tooltip_contract": "data-tip"})
    return rows


def render_dashboard_component_lines(summary: dict[str, Any]) -> list[str]:
    return [
        f"- Dashboard component helpers: {summary.get('component_count', 0)} reusable renderer helper(s).",
        f"- Routes present: {len(summary.get('routes_present', []))}/{summary.get('route_count', 0)}.",
        f"- data-tip count: {summary.get('data_tip_count', 0)}.",
        f"- Native nav title regression: {summary.get('native_nav_title_regression', False)}.",
        f"- Dashboard redesigns applied: {summary.get('redesigns_dashboard', False)}.",
    ]
