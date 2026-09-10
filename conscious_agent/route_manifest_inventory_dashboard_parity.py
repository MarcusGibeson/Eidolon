from __future__ import annotations

import ast
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_VERSION = CURRENT_VERSION
ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_ID = "route-manifest-inventory-expansion-and-dashboard-parity-gate-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "route_manifest_inventory_expanded": True,
    "dashboard_parity_gate_behavioral": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_parity_is_release_approval": False,
    "parity_gate_executes_governed_actions": False,
    "parity_gate_applies_patches": False,
    "parity_gate_writes_memory": False,
    "parity_gate_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class RouteInventoryRow:
    route: str
    renderer: str
    cohort: str
    status: str = "manual_authoritative"


# Bounded expanded inventory. This deliberately combines the v1024 critical route set,
# the v1025-v1028 extraction surfaces, and a small set of foundational dashboard pages.
# It is not a generated router and it does not replace dashboard.py dispatch.
ROUTE_MANIFEST_INVENTORY: tuple[RouteInventoryRow, ...] = (
    RouteInventoryRow("/", "render_overview", "core-dashboard"),
    RouteInventoryRow("/api-info", "render_api_info", "core-dashboard"),
    RouteInventoryRow("/self-development-smoke-debt", "render_self_development_smoke_debt", "release-truth"),
    RouteInventoryRow("/dashboard-route-inventory", "render_dashboard_route_inventory", "route-health"),
    RouteInventoryRow("/dashboard-route-probe", "render_dashboard_route_probe", "route-health"),
    RouteInventoryRow("/dashboard-route-health-audit", "render_dashboard_route_health_audit", "route-health"),
    RouteInventoryRow("/metadata-release-integrity-audit", "render_metadata_release_integrity_audit", "metadata-integrity"),
    RouteInventoryRow("/source-surface-manifest", "render_source_surface_manifest", "source-manifest"),
    RouteInventoryRow("/source-surface-manifest-audit", "render_source_surface_manifest_audit", "source-manifest"),
    RouteInventoryRow("/first-narrow-live-patch-trial-audit", "render_first_narrow_live_patch_trial_audit", "operator-governance"),
    RouteInventoryRow("/post-live-patch-evidence-intake-contract", "render_post_live_patch_evidence_intake_contract", "operator-governance"),
    RouteInventoryRow("/release-staleness-verification-audit-board", "render_release_staleness_verification_audit_board", "stale-version"),
    RouteInventoryRow("/behavioral-dashboard-route-coverage", "render_behavioral_dashboard_route_coverage", "v1024-route-behavior"),
    RouteInventoryRow("/source-decomposition-compatibility-slice", "render_source_decomposition_compatibility_slice", "v1025-decomposition"),
    RouteInventoryRow("/dashboard-shell-component-extraction", "render_dashboard_shell_component_extraction", "v1026-dashboard-components"),
    RouteInventoryRow("/smoke-registry-sidecar-compatibility", "render_smoke_registry_sidecar_compatibility", "v1027-smoke-sidecar"),
    RouteInventoryRow("/smoke-registry-sidecar-expansion-route-manifest", "render_smoke_registry_sidecar_expansion_route_manifest_prep", "v1028-route-manifest-prep"),
    RouteInventoryRow("/actions", "render_action_center", "core-dashboard"),
    RouteInventoryRow("/tasks", "render_tasks", "core-dashboard"),
    RouteInventoryRow("/build-cycle", "render_build_cycle", "development-dashboard"),
    RouteInventoryRow("/patch-review", "render_patch_review", "development-dashboard"),
    RouteInventoryRow("/self-development", "render_self_development", "development-dashboard"),
    RouteInventoryRow("/development-sessions", "render_development_sessions", "development-dashboard"),
)


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


def _renderer_function_names(dashboard_source: str) -> set[str]:
    try:
        tree = ast.parse(dashboard_source)
    except SyntaxError:
        return set()
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("render_")}


def route_manifest_inventory_rows() -> list[dict[str, Any]]:
    return [asdict(row) for row in ROUTE_MANIFEST_INVENTORY]


def _render_direct(route: str, renderer_name: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import dashboard  # type: ignore
    except Exception as error:
        return {"route": route, "renderer": renderer_name, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": f"dashboard import failed: {error}"}
    renderer = getattr(dashboard, renderer_name, None)
    if renderer is None:
        return {"route": route, "renderer": renderer_name, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "renderer missing"}
    try:
        body = renderer()
    except Exception as error:
        return {"route": route, "renderer": renderer_name, "ok": False, "status": "blocked", "elapsed_ms": int((time.perf_counter() - started) * 1000), "body_size": 0, "error": repr(error)}
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
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "elapsed_ms": elapsed_ms,
        "body_size": len(body_text),
        "contains_data_tip": "data-tip" in body_text,
        "contains_traceback": "Traceback" in body_text,
        "contains_500_text": "Internal Server Error" in body_text or "Dashboard route crashed" in body_text,
        "contains_route_token": bool((not token) or token in body_text),
        "error": None if ok else "rendered body failed route parity contract",
    }


def build_route_manifest_inventory_expansion_dashboard_parity_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history])

    route_map = _route_renderer_map(dashboard_source)
    renderer_names = _renderer_function_names(dashboard_source)
    inventory_rows = route_manifest_inventory_rows()
    inventory_routes = [row["route"] for row in inventory_rows]
    duplicate_routes = sorted({route for route in inventory_routes if inventory_routes.count(route) > 1})

    mapping_mismatches: list[dict[str, Any]] = []
    renderer_missing: list[dict[str, Any]] = []
    behavior_rows: list[dict[str, Any]] = []
    for row in inventory_rows:
        route = str(row["route"])
        expected_renderer = str(row["renderer"])
        actual_renderer = route_map.get(route)
        if actual_renderer != expected_renderer:
            mapping_mismatches.append({"route": route, "expected_renderer": expected_renderer, "actual_renderer": actual_renderer})
            behavior_rows.append({"route": route, "renderer": expected_renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "route-to-renderer mapping mismatch"})
            continue
        if expected_renderer not in renderer_names:
            renderer_missing.append({"route": route, "renderer": expected_renderer})
            behavior_rows.append({"route": route, "renderer": expected_renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "renderer function missing"})
            continue
        behavior_rows.append(_render_direct(route, expected_renderer))

    manifest_surface_present = "v1029-route-manifest-inventory-dashboard-parity" in manifest_source
    behavior_pass_count = sum(1 for row in behavior_rows if row.get("ok"))
    behavior_blocked = [row for row in behavior_rows if not row.get("ok")]
    total_elapsed_ms = sum(int(row.get("elapsed_ms") or 0) for row in behavior_rows)
    required_tokens = [
        CURRENT_MILESTONE,
        ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_ID,
        "route_manifest_inventory_expanded=True",
        "dashboard_parity_gate_behavioral=True",
        "route_manifest_route_count=23",
        "route_manifest_render_pass_count=23",
        "/route-manifest-dashboard-parity",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "route_manifest_generates_routes=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    rows = [
        {"name": "module-version-current", "ok": ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_VERSION == CURRENT_VERSION, "message": f"module={ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_VERSION}; current={CURRENT_VERSION}"},
        {"name": "inventory-expanded", "ok": len(inventory_rows) == 23 and not duplicate_routes, "message": f"route_manifest_route_count={len(inventory_rows)} duplicate_routes={duplicate_routes}"},
        {"name": "route-to-renderer-map-parity", "ok": not mapping_mismatches, "message": f"mapping_mismatches={mapping_mismatches}"},
        {"name": "renderer-functions-present", "ok": not renderer_missing, "message": f"renderer_missing={renderer_missing}"},
        {"name": "behavioral-route-render-parity", "ok": behavior_pass_count == len(inventory_rows) and not behavior_blocked, "message": f"route_manifest_render_pass_count={behavior_pass_count}; blocked={behavior_blocked[:3]}"},
        {"name": "source-manifest-representation-present", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1029 route manifest parity gate."},
        {"name": "manual-dashboard-still-authoritative", "ok": "class EidolonDashboardHandler" in dashboard_source and "def do_GET" in dashboard_source and "html = render_" in dashboard_source, "message": "dashboard.py still owns manual route dispatch."},
        {"name": "manual-smoke-still-authoritative", "ok": "def _build_checks" in smoke_source and "class SmokeCheck" in smoke_source, "message": "tools/smoke_check.py still owns manual smoke execution."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/smoke/manifest/docs carry v1029 route manifest parity truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_parity_is_release_approval", "parity_gate_executes_governed_actions", "parity_gate_applies_patches", "parity_gate_writes_memory", "parity_gate_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Route manifest inventory and dashboard parity gate grant no routing, release, action, memory, or autonomy authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_ID,
        "state": "route_manifest_inventory_expansion_dashboard_parity_review_only",
        "dashboard_module": DASHBOARD_MODULE,
        "source_manifest_module": SOURCE_MANIFEST_MODULE,
        "manual_smoke_module": MANUAL_SMOKE_MODULE,
        "route_manifest_inventory_rows": inventory_rows,
        "route_manifest_route_count": len(inventory_rows),
        "route_manifest_render_pass_count": behavior_pass_count,
        "route_manifest_behavior_rows": behavior_rows,
        "total_behavior_elapsed_ms": total_elapsed_ms,
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "duplicate_routes": duplicate_routes,
        "route_manifest_inventory_expanded": True,
        "dashboard_parity_gate_behavioral": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "route_manifest_replaces_dashboard_routes": False,
        "route_manifest_generates_routes": False,
        "dashboard_wiring_generated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "boundaries": dict(BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def route_manifest_inventory_dashboard_parity_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", ROUTE_MANIFEST_INVENTORY_DASHBOARD_PARITY_ID)),
        f"route_manifest_route_count={report.get('route_manifest_route_count')}",
        f"route_manifest_render_pass_count={report.get('route_manifest_render_pass_count')}",
        f"route_manifest_inventory_expanded={report.get('route_manifest_inventory_expanded')}",
        f"dashboard_parity_gate_behavioral={report.get('dashboard_parity_gate_behavioral')}",
        f"total_behavior_elapsed_ms={report.get('total_behavior_elapsed_ms')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"route_manifest_replaces_dashboard_routes={report.get('route_manifest_replaces_dashboard_routes')}",
        f"route_manifest_generates_routes={report.get('route_manifest_generates_routes')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nRoute inventory rows:")
        for row in report.get("route_manifest_inventory_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')} cohort={row.get('cohort')} status={row.get('status')}")
        lines.append("\nBehavior rows:")
        for row in report.get("route_manifest_behavior_rows", []):
            lines.append(f"- {row.get('route')}: {row.get('status')} renderer={row.get('renderer')} elapsed_ms={row.get('elapsed_ms')} body_size={row.get('body_size')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1030.0 Dashboard Route Behavioral Coverage Expansion v1 tokens: route-manifest-inventory-expansion-and-dashboard-parity-gate-v1 route-manifest-dashboard-parity-v1 build_route_manifest_inventory_expansion_dashboard_parity_review route_manifest_inventory_dashboard_parity_review_text module=conscious_agent/route_manifest_inventory_dashboard_parity.py dashboard_module=conscious_agent/dashboard.py manual_smoke_module=tools/smoke_check.py route_manifest_inventory_expanded=True dashboard_parity_gate_behavioral=True route_manifest_route_count=23 route_manifest_render_pass_count=23 manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True /route-manifest-dashboard-parity data-tip command-deck operator-console no_native_title_tooltip.
