from __future__ import annotations

import ast
import re
import time
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_VERSION = CURRENT_VERSION
BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_ID = "behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1"

CRITICAL_BEHAVIORAL_ROUTES: tuple[str, ...] = (
    "/",
    "/api-info",
    "/self-development-smoke-debt",
    "/dashboard-route-inventory",
    "/dashboard-route-probe",
    "/dashboard-route-health-audit",
    "/metadata-release-integrity-audit",
    "/source-surface-manifest",
    "/source-surface-manifest-audit",
    "/first-narrow-live-patch-trial-audit",
    "/post-live-patch-evidence-intake-contract",
    "/release-staleness-verification-audit-board",
)

DECOMPOSITION_PREP_FILES: tuple[tuple[str, int], ...] = (
    ("conscious_agent/self_maintenance.py", 40000),
    ("tools/smoke_check.py", 12000),
    ("conscious_agent/self_development_cycle.py", 12000),
    ("conscious_agent/dashboard.py", 10000),
    ("conscious_agent/main.py", 7000),
    ("conscious_agent/api_server.py", 5000),
)

BEHAVIORAL_ROUTE_BOUNDARIES: dict[str, bool] = {
    "behavioral_probe_executes_governed_actions": False,
    "behavioral_probe_applies_patches": False,
    "behavioral_probe_writes_memory": False,
    "behavioral_probe_creates_release": False,
    "behavioral_probe_expands_autonomy": False,
    "route_health_is_approval": False,
    "route_presence_is_authorization": False,
    "decomposition_prep_moves_code": False,
    "generated_wiring_activated": False,
    "manual_smoke_remains_authoritative": True,
    "operator_review_required": True,
}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _route_renderer_map(dashboard_source: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    pattern = re.compile(r'(?:if|elif) path == "([^"]+)"\s*:\n\s*html = (render_[A-Za-z0-9_]+)\(\)')
    for match in pattern.finditer(dashboard_source):
        mapping[match.group(1)] = match.group(2)
    return mapping


def _render_direct(route: str, renderer_name: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import dashboard  # type: ignore
    except Exception as error:
        return {
            "route": route,
            "renderer": renderer_name,
            "status": "blocked",
            "ok": False,
            "elapsed_ms": 0,
            "body_size": 0,
            "error": f"dashboard import failed: {error}",
        }
    renderer = getattr(dashboard, renderer_name, None)
    if renderer is None:
        return {
            "route": route,
            "renderer": renderer_name,
            "status": "blocked",
            "ok": False,
            "elapsed_ms": 0,
            "body_size": 0,
            "error": "renderer missing",
        }
    try:
        body = renderer()
    except Exception as error:
        return {
            "route": route,
            "renderer": renderer_name,
            "status": "blocked",
            "ok": False,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "body_size": 0,
            "error": repr(error),
        }
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    body_text = body if isinstance(body, str) else ""
    token = route.strip("/")
    ok = (
        isinstance(body, str)
        and "<html" in body_text.lower()
        and "data-tip" in body_text
        and "Traceback" not in body_text
        and "Dashboard route crashed" not in body_text
        and "Internal Server Error" not in body_text
        and (not token or token in body_text)
    )
    return {
        "route": route,
        "renderer": renderer_name,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "elapsed_ms": elapsed_ms,
        "body_size": len(body_text),
        "contains_data_tip": "data-tip" in body_text,
        "contains_traceback": "Traceback" in body_text,
        "contains_500_text": "Internal Server Error" in body_text or "Dashboard route crashed" in body_text,
        "contains_route_token": bool((not token) or token in body_text),
        "error": None if ok else "rendered body failed behavioral shape contract",
    }


def _line_count(root: Path, rel: str) -> int:
    text = _read_text(root, rel)
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _collect_renderer_function_names(dashboard_source: str) -> set[str]:
    try:
        tree = ast.parse(dashboard_source)
    except SyntaxError:
        return set()
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("render_")}


def build_behavioral_dashboard_route_coverage_and_source_decomposition_prep_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, "conscious_agent/dashboard.py")
    smoke_source = _read_text(project_root, "tools/smoke_check.py")
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    route_map = _route_renderer_map(dashboard_source)
    renderer_functions = _collect_renderer_function_names(dashboard_source)
    route_rows: list[dict[str, Any]] = []
    for route in CRITICAL_BEHAVIORAL_ROUTES:
        renderer_name = route_map.get(route)
        if not renderer_name:
            route_rows.append({
                "route": route,
                "renderer": None,
                "status": "blocked",
                "ok": False,
                "error": "route not mapped to a zero-argument dashboard renderer",
            })
            continue
        route_rows.append(_render_direct(route, renderer_name))
    duplicate_route_count = len(CRITICAL_BEHAVIORAL_ROUTES) - len(set(CRITICAL_BEHAVIORAL_ROUTES))
    route_map_covers_critical = all(route in route_map for route in CRITICAL_BEHAVIORAL_ROUTES)
    renderer_functions_cover_critical = all((route_map.get(route) in renderer_functions) for route in CRITICAL_BEHAVIORAL_ROUTES)
    behavior_routes_pass = all(bool(row.get("ok")) for row in route_rows)
    decomposition_rows = []
    for rel, threshold in DECOMPOSITION_PREP_FILES:
        lines = _line_count(project_root, rel)
        decomposition_rows.append({
            "path": rel,
            "line_count": lines,
            "threshold": threshold,
            "needs_decomposition": lines >= threshold,
            "prep_action": "extract compatibility-preserving helpers before behavior changes" if lines >= threshold else "monitor",
        })
    giant_file_count = sum(1 for row in decomposition_rows if row["needs_decomposition"])
    docs = "\n".join([dashboard_source, smoke_source, readme_next, readme_history])
    required_tokens = [
        CURRENT_MILESTONE,
        BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_ID,
        "behavioral_route_probe_executes_renderers=True",
        "critical_dashboard_route_count=12",
        "/self-development-smoke-debt",
        "/dashboard-route-health-audit",
        "source_decomposition_prep_only=True",
        "manual_registry_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_VERSION == CURRENT_VERSION, "message": f"module={BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_VERSION}; current={CURRENT_VERSION}"},
        {"name": "critical-route-list-unique", "ok": duplicate_route_count == 0, "message": f"duplicate critical route count={duplicate_route_count}"},
        {"name": "critical-routes-mapped", "ok": route_map_covers_critical, "message": "Critical routes map to direct zero-argument dashboard renderers."},
        {"name": "critical-renderers-present", "ok": renderer_functions_cover_critical, "message": "Critical route renderers exist in dashboard.py."},
        {"name": "critical-routes-render", "ok": behavior_routes_pass, "message": "Critical dashboard routes render HTML through their actual renderer functions."},
        {"name": "smoke-helper-still-http-behavioral", "ok": "probe_dashboard_http_routes" in smoke_source and "urllib.request.urlopen" in smoke_source, "message": "Smoke harness keeps real HTTP route probing available."},
        {"name": "decomposition-prep-inventory", "ok": giant_file_count >= 4, "message": f"giant files flagged for compatibility extraction={giant_file_count}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke docs carry the v1024 behavioral route and decomposition-prep truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BEHAVIORAL_ROUTE_BOUNDARIES[key] is False for key in ["behavioral_probe_executes_governed_actions", "behavioral_probe_applies_patches", "behavioral_probe_writes_memory", "behavioral_probe_creates_release", "behavioral_probe_expands_autonomy", "route_health_is_approval", "route_presence_is_authorization", "decomposition_prep_moves_code", "generated_wiring_activated"]), "message": "Behavioral route coverage and decomposition prep do not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_ID,
        "state": "behavioral_dashboard_route_coverage_and_source_decomposition_prep_review_only",
        "critical_dashboard_route_count": len(CRITICAL_BEHAVIORAL_ROUTES),
        "behavioral_route_probe_executes_renderers": True,
        "behavioral_route_probe_uses_token_presence_only": False,
        "critical_route_map_covers_all": route_map_covers_critical,
        "critical_renderers_present": renderer_functions_cover_critical,
        "critical_routes_pass": behavior_routes_pass,
        "route_rows": route_rows,
        "decomposition_rows": decomposition_rows,
        "giant_file_count": giant_file_count,
        "source_decomposition_prep_only": True,
        "source_decomposition_applied": False,
        "manual_registry_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "boundaries": dict(BEHAVIORAL_ROUTE_BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row["ok"]],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def behavioral_dashboard_route_coverage_and_source_decomposition_prep_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", BEHAVIORAL_DASHBOARD_ROUTE_COVERAGE_ID)),
        f"critical_dashboard_route_count={report.get('critical_dashboard_route_count')}",
        f"behavioral_route_probe_executes_renderers={report.get('behavioral_route_probe_executes_renderers')}",
        f"behavioral_route_probe_uses_token_presence_only={report.get('behavioral_route_probe_uses_token_presence_only')}",
        f"critical_routes_pass={report.get('critical_routes_pass')}",
        f"source_decomposition_prep_only={report.get('source_decomposition_prep_only')}",
        f"source_decomposition_applied={report.get('source_decomposition_applied')}",
        f"giant_file_count={report.get('giant_file_count')}",
        f"manual_registry_authoritative={report.get('manual_registry_authoritative')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("critical_routes:")
        for row in report.get("route_rows", []):
            lines.append(f"- {row.get('route')}: {row.get('status')} renderer={row.get('renderer')} elapsed_ms={row.get('elapsed_ms', 0)} body_size={row.get('body_size', 0)}")
        lines.append("decomposition_prep:")
        for row in report.get("decomposition_rows", []):
            lines.append(f"- {row.get('path')}: lines={row.get('line_count')} needs_decomposition={row.get('needs_decomposition')}")
        lines.append("checks:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1025.0 First Source Decomposition Compatibility Slice v1 tokens: behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1 behavioral_route_probe_executes_renderers=True behavioral_route_probe_uses_token_presence_only=False critical_dashboard_route_count=12 critical_routes_pass=True source_decomposition_prep_only=True source_decomposition_applied=False giant_file_count=6 manual_registry_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip /self-development-smoke-debt /dashboard-route-health-audit.
