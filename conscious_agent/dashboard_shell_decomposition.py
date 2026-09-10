from __future__ import annotations

"""Structural and deterministic parity validation for the v1250.7 dashboard shell extraction."""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "v1250.7"
BASELINE_PARENT_LINE_COUNT = 18432
BASELINE_NORMALIZED_LAYOUT_SHA256 = "1872a65fa848863b814c84e2e60bb660bcf1c69d5ef7f397b92db355d1c68ee5"
AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _function_span(text: str, name: str) -> int:
    tree = ast.parse(text)
    node = next((row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name == name), None)
    return 0 if node is None else int(node.end_lineno - node.lineno + 1)


def _deterministic_layout_probe(root: Path) -> tuple[str, int]:
    import sys

    for value in (root / "conscious_agent", root):
        if str(value) not in sys.path:
            sys.path.insert(0, str(value))
    import dashboard  # type: ignore

    original_settings = dashboard.load_settings
    original_now = dashboard._now
    original_nav = dashboard.dashboard_route_registry_nav_items
    original_message = dashboard.DashboardState.message
    original_error = dashboard.DashboardState.error
    try:
        dashboard.load_settings = lambda: {
            "dashboard_live_refresh_enabled": False,
            "dashboard_host": "127.0.0.1",
            "dashboard_port": 8765,
            "dashboard_companion_chat_enabled": False,
        }
        dashboard._now = lambda: "2000-01-01T00:00:00"
        dashboard.dashboard_route_registry_nav_items = lambda: []
        dashboard.DashboardState.message = ""
        dashboard.DashboardState.error = ""
        html = dashboard._layout("/", '<section id="bundle-c-parity">stable</section>')
        normalized = html.replace(str(dashboard.DASHBOARD_VERSION), "__VERSION__")
        return hashlib.sha256(normalized.encode()).hexdigest(), len(normalized)
    finally:
        dashboard.load_settings = original_settings
        dashboard._now = original_now
        dashboard.dashboard_route_registry_nav_items = original_nav
        dashboard.DashboardState.message = original_message
        dashboard.DashboardState.error = original_error


def validate_dashboard_shell_decomposition(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    parent_path = root / "conscious_agent/dashboard.py"
    child_path = root / "conscious_agent/dashboard_layout.py"
    parent = parent_path.read_text(encoding="utf-8") if parent_path.is_file() else ""
    child = child_path.read_text(encoding="utf-8") if child_path.is_file() else ""
    parent_lines = len(parent.splitlines())
    child_lines = len(child.splitlines())
    wrapper_span = _function_span(parent, "_layout") if parent else 0
    renderer_span = _function_span(child, "render_dashboard_layout") if child else 0
    layout_sha, layout_length = _deterministic_layout_probe(root)
    checks = {
        "layout_module_present": child_path.is_file(),
        "layout_contract_current": 'CONTRACT_VERSION = "v1250.7"' in child,
        "parent_wrapper_bounded": 5 <= wrapper_span <= 40,
        "renderer_extracted": renderer_span >= 850,
        "parent_reduced": parent_lines < BASELINE_PARENT_LINE_COUNT - 800,
        "child_bounded": 900 <= child_lines <= 1000,
        "dependencies_explicit": all(token in child for token in ("load_settings,", "DashboardState,", "_render_nav,", "_live_refresh_script,")),
        "manual_dashboard_surface_preserved": "def _layout(path: str, content: str)" in parent,
        "deterministic_layout_parity": layout_sha == BASELINE_NORMALIZED_LAYOUT_SHA256,
        "layout_contains_full_shell": layout_length > 200000,
        "no_action_authority": '"release_authorized": False' in child and '"tool_execution_authorized": False' in child,
    }
    passed = sum(bool(value) for value in checks.values())
    result: dict[str, Any] = {
        "ok": passed == len(checks),
        "status": "dashboard_shell_decomposed" if passed == len(checks) else "dashboard_shell_decomposition_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "parent_line_count": parent_lines,
        "baseline_parent_line_count": BASELINE_PARENT_LINE_COUNT,
        "extracted_line_count": child_lines,
        "wrapper_span": wrapper_span,
        "renderer_span": renderer_span,
        "normalized_layout_sha256": layout_sha,
        "normalized_layout_length": layout_length,
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "validate_dashboard_shell_decomposition"]
