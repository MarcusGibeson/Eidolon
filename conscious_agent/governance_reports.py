from __future__ import annotations

from typing import Any
import json

GOVERNANCE_REPORTS_VERSION = "500.0"

def render_status_rows(rows: list[dict[str, Any]]) -> list[str]:
    return [f"- {row.get('status', 'unknown').upper()} {row.get('name', 'check')}: {row.get('message', '')}" for row in rows]

def render_boundary_rows(boundaries: dict[str, Any]) -> list[str]:
    return [f"- {key}: {value}" for key, value in sorted(boundaries.items())]

def render_seed_rows(items: list[dict[str, Any]], key_order: tuple[str, ...] = ("field", "surface", "gate", "audit", "requirement"), limit: int = 6) -> list[str]:
    lines: list[str] = []
    for item in items[:limit]:
        label = next((str(item[k]) for k in key_order if k in item), "item")
        requirement = str(item.get("requirement", item.get("focus", "review-only")))
        lines.append(f"- {label}: {requirement}")
    return lines

def render_governance_packet(title: str, report: dict[str, Any], sections: list[tuple[str, list[str]]], full: bool = False) -> str:
    payload = report.get("payload", {})
    lines: list[str] = [f"# {title}", "", report.get("message", "Governance packet report."), ""]
    for heading, body in sections:
        lines.append(f"## {heading}")
        lines.extend(body or ["- No rows supplied."])
        lines.append("")
    rows = report.get("rows", [])
    if rows:
        lines.append("## Checks")
        lines.extend(render_status_rows(rows))
        lines.append("")
    boundaries = payload.get("boundaries") or {}
    if boundaries:
        lines.append("## Boundaries")
        lines.extend(render_boundary_rows(boundaries))
        lines.append("")
    if full:
        lines.extend(["## Payload", json.dumps(payload, indent=2, default=str)])
    return "\n".join(lines).strip() + "\n"

def parity_snapshot(name: str, expected: list[str], observed_text: str) -> dict[str, Any]:
    missing = [token for token in expected if token not in observed_text]
    return {"name": name, "expected": expected, "missing": missing, "ok": not missing}
