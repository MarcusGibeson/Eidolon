from __future__ import annotations

from typing import Any, Iterable

SURFACE_PARITY_VERSION = "500.0"

def missing_tokens(text: str, tokens: Iterable[str]) -> list[str]:
    return [token for token in tokens if token not in text]

def surface_presence_summary(name: str, text: str, tokens: Iterable[str]) -> dict[str, Any]:
    token_list = list(tokens)
    missing = missing_tokens(text, token_list)
    return {
        "name": name,
        "version": SURFACE_PARITY_VERSION,
        "expected_count": len(token_list),
        "missing": missing,
        "ok": not missing,
        "changes_surface": False,
    }

def build_surface_parity_summary(dashboard_text: str, api_text: str, main_text: str, *, dashboard_routes: list[str], api_routes: list[str], cli_flags: list[str]) -> dict[str, Any]:
    rows = [
        surface_presence_summary("dashboard-routes", dashboard_text, dashboard_routes),
        surface_presence_summary("api-routes", api_text, api_routes),
        surface_presence_summary("cli-flags", main_text, cli_flags),
    ]
    return {
        "version": SURFACE_PARITY_VERSION,
        "rows": rows,
        "ok": all(row["ok"] for row in rows),
        "missing": {row["name"]: row["missing"] for row in rows if row["missing"]},
        "adds_routes": False,
        "executes_commands": False,
    }

def parity_summary_renderer(summary: dict[str, Any]) -> list[str]:
    lines = []
    for row in summary.get("rows", []):
        state = "pass" if row.get("ok") else "blocked"
        missing = ", ".join(row.get("missing", [])) or "none"
        lines.append(f"- {state.upper()} {row.get('name')}: missing {missing}")
    return lines
