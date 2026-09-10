from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_deferred_route_harness_renderer_repair_prep import (
    DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_ID,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1035_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1035_MAPPING_RECONCILED_ROUTE_COUNT,
    _render_isolated,
)

DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_VERSION = RUNTIME_VERSION
DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_ID = "dashboard-slow-route-isolated-behavioral-coverage-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/dashboard-slow-route-isolated-behavioral-coverage"
SELF_RENDERER = "render_dashboard_slow_route_isolated_behavioral_coverage"
PRIOR_STANDARD_BEHAVIORAL_ROUTE_COUNT = 97
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 101
ISOLATED_BEHAVIORAL_ROUTE_COUNT = 5
NEW_ISOLATED_BEHAVIORAL_COVERAGE_COUNT = 4
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 101
MAPPING_RECONCILED_ROUTE_COUNT = 104
ISOLATED_HARNESS_TIMEOUT_SECONDS = 10
DEFERRED_UNREADY_ROUTE_COUNT = 3

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "isolated_slow_route_behavioral_coverage": True,
    "isolated_harness_executes_renderers_only": True,
    "autonomy_route_graduated_to_isolated_behavioral_coverage": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_behavior_pass_is_release_approval": False,
    "isolated_route_harness_executes_governed_actions": False,
    "isolated_route_harness_applies_patches": False,
    "isolated_route_harness_writes_memory": False,
    "isolated_route_harness_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class IsolatedRouteRow:
    route: str
    renderer: str
    cohort: str
    coverage_status: str
    newly_counted: bool


ISOLATED_BEHAVIORAL_ROUTES: tuple[IsolatedRouteRow, ...] = (
    IsolatedRouteRow("/autonomy", "render_autonomy_boundary", "autonomy-safety", "graduated_from_v1035_probe_only", True),
    IsolatedRouteRow("/dashboard-route-behavioral-coverage-expansion", "render_dashboard_route_behavioral_coverage_expansion", "route-coverage-history", "slow_historical_route_covered_isolated", True),
    IsolatedRouteRow("/execution-approval-scope", "render_execution_approval_scope", "approval-scope", "v1035_direct_repair_reconfirmed_isolated", False),
    IsolatedRouteRow("/route-manifest-dashboard-parity", "render_route_manifest_dashboard_parity", "route-manifest-parity", "slow_manifest_route_covered_isolated", True),
    IsolatedRouteRow("/smoke-registry-sidecar-parity-expansion", "render_smoke_registry_sidecar_parity_expansion", "smoke-sidecar-history", "sidecar_parity_route_covered_isolated", True),
)

DEFERRED_UNREADY_ROUTES: tuple[dict[str, str], ...] = (
    {"route": "/detail", "renderer": "render_detail", "reason": "renderer requires a query argument; needs a parameterized harness before it can be counted"},
    {"route": "/doctor", "renderer": "render_doctor", "reason": "renderer still exceeds the 10 second isolated harness timeout in this environment"},
    {"route": "/stabilization", "renderer": "render_stabilization", "reason": "renderer is deferred from the v1036 counted cohort because its current render timing is unstable under the 10 second isolated harness"},
)

_CACHE: dict[tuple[str, float, float, float], dict[str, Any]] = {}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _route_renderer_map(source: str) -> dict[str, str]:
    pairs = re.findall(r'elif path == "([^"]+)":\n\s+html = (render_[A-Za-z0-9_]+)\(', source)
    route_map = {route: renderer for route, renderer in pairs}
    if 'if path in ("/", "/index")' in source:
        route_map["/"] = "render_overview"
    return route_map


def _renderer_function_names(source: str) -> set[str]:
    return set(re.findall(r'^def (render_[A-Za-z0-9_]+)\(', source, re.MULTILINE))


def _cohort_summary(route_rows: list[dict[str, Any]], behavior_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    behavior_by_route = {str(row.get("route")): row for row in behavior_rows}
    cohorts = sorted({str(row.get("cohort")) for row in route_rows})
    summary: list[dict[str, Any]] = []
    for cohort in cohorts:
        routes = [row for row in route_rows if row.get("cohort") == cohort]
        rendered = [behavior_by_route.get(str(row.get("route"))) for row in routes]
        passed = sum(1 for row in rendered if row and row.get("ok"))
        summary.append({"cohort": cohort, "routes": len(routes), "passed": passed, "blocked": len(routes) - passed})
    return summary


def build_dashboard_slow_route_isolated_behavioral_coverage_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    mtimes: list[float] = []
    for rel in [DASHBOARD_MODULE, MANUAL_SMOKE_MODULE, SOURCE_MANIFEST_MODULE, "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"]:
        path = project_root / rel
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            mtimes.append(0.0)
    cache_key = (str(project_root), *mtimes[:3])
    cached = _CACHE.get(cache_key)
    if cached:
        return dict(cached)

    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history])
    route_map = _route_renderer_map(dashboard_source)
    renderers = _renderer_function_names(dashboard_source)
    # Avoid recursively rebuilding the full v1030-v1035 dashboard coverage stack here.
    # v1036 is a bounded slow-route slice and only needs the prior audited constants.
    prior_standard_count = int(V1035_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping_count = int(V1035_MAPPING_RECONCILED_ROUTE_COUNT)
    prior_review_token_present = DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_ID in docs
    route_rows = [asdict(row) for row in ISOLATED_BEHAVIORAL_ROUTES]
    isolated_rows = [
        _render_isolated(project_root, row.route, row.renderer, ISOLATED_HARNESS_TIMEOUT_SECONDS)
        for row in ISOLATED_BEHAVIORAL_ROUTES
    ]
    isolated_pass_count = sum(1 for row in isolated_rows if row.get("ok"))
    newly_counted_rows = [row for row in route_rows if row.get("newly_counted")]
    newly_counted_routes = {str(row.get("route")) for row in newly_counted_rows}
    existing_mapped_routes = {"/execution-approval-scope", "/autonomy", SELF_ROUTE}
    mapping_new_routes = {row.route for row in ISOLATED_BEHAVIORAL_ROUTES if row.route not in {"/execution-approval-scope", "/autonomy"}}
    mapping_mismatches = [
        {"route": row.route, "expected_renderer": row.renderer, "actual_renderer": route_map.get(row.route)}
        for row in ISOLATED_BEHAVIORAL_ROUTES
        if route_map.get(row.route) != row.renderer
    ]
    renderer_missing = [asdict(row) for row in ISOLATED_BEHAVIORAL_ROUTES if row.renderer not in renderers]
    self_mapping_ok = route_map.get(SELF_ROUTE) == SELF_RENDERER and SELF_RENDERER in renderers
    deferred_reasons_present = all(row["route"] in docs and row["reason"] in docs for row in DEFERRED_UNREADY_ROUTES)
    manifest_surface_present = "v1036-dashboard-slow-route-isolated-behavioral-coverage" in manifest_source
    cohort_rows = _cohort_summary(route_rows, isolated_rows)
    autonomy_row = next((row for row in isolated_rows if row.get("route") == "/autonomy"), {})
    blocked_isolated_rows = [row for row in isolated_rows if not row.get("ok")]
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_ID,
        "prior_standard_behavioral_route_count=97",
        "isolated_behavioral_route_count=5",
        "new_isolated_behavioral_coverage_count=4",
        "total_behavioral_coverage_count=101",
        "prior_mapping_reconciled_route_count=101",
        "mapping_reconciled_route_count=104",
        "isolated_harness_pass_count=5",
        "deferred_unready_route_count=3",
        "autonomy_route_graduated_to_isolated_behavioral_coverage=True",
        "standard_fast_route_coverage_unchanged=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-review-token-present", "ok": prior_review_token_present, "message": f"prior_review_token_present={prior_review_token_present}"},
        {"name": "prior-standard-behavioral-count", "ok": prior_standard_count == PRIOR_STANDARD_BEHAVIORAL_ROUTE_COUNT, "message": f"prior_standard={prior_standard_count} expected={PRIOR_STANDARD_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "prior-mapping-reconciled-count", "ok": prior_mapping_count == PRIOR_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"prior_mapping={prior_mapping_count} expected={PRIOR_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "isolated-route-count", "ok": len(route_rows) == ISOLATED_BEHAVIORAL_ROUTE_COUNT, "message": f"isolated_routes={len(route_rows)} expected={ISOLATED_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "new-isolated-behavioral-count", "ok": len(newly_counted_routes) == NEW_ISOLATED_BEHAVIORAL_COVERAGE_COUNT, "message": f"newly_counted={len(newly_counted_routes)} expected={NEW_ISOLATED_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "slow-route-mapping-clean", "ok": not mapping_mismatches and self_mapping_ok, "message": f"mapping_mismatches={len(mapping_mismatches)} self_mapping_ok={self_mapping_ok}"},
        {"name": "slow-route-renderers-present", "ok": not renderer_missing, "message": f"missing_renderers={len(renderer_missing)}"},
        {"name": "isolated-routes-render-behaviorally", "ok": isolated_pass_count == ISOLATED_BEHAVIORAL_ROUTE_COUNT and not blocked_isolated_rows, "message": f"isolated_passes={isolated_pass_count}/{ISOLATED_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "autonomy-route-graduated", "ok": bool(autonomy_row.get("ok")), "message": f"/autonomy isolated status={autonomy_row.get('status')} elapsed_ms={autonomy_row.get('elapsed_ms')}"},
        {"name": "total-behavioral-coverage-count", "ok": prior_standard_count + NEW_ISOLATED_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_standard_count + NEW_ISOLATED_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-reconciled-count-current", "ok": prior_mapping_count + len(mapping_new_routes) == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping_count + len(mapping_new_routes)} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "deferred-unready-routes-documented", "ok": len(DEFERRED_UNREADY_ROUTES) == DEFERRED_UNREADY_ROUTE_COUNT and deferred_reasons_present, "message": f"deferred_unready={len(DEFERRED_UNREADY_ROUTES)} expected={DEFERRED_UNREADY_ROUTE_COUNT}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1036 slow route isolated behavioral coverage surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1036 slow-route isolated coverage truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "isolated_route_harness_executes_governed_actions", "isolated_route_harness_applies_patches", "isolated_route_harness_writes_memory", "isolated_route_harness_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Isolated slow-route coverage remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_ID,
        "state": "dashboard_slow_route_isolated_behavioral_coverage_review_only",
        "prior_standard_behavioral_route_count": prior_standard_count,
        "prior_mapping_reconciled_route_count": prior_mapping_count,
        "isolated_behavioral_route_count": len(route_rows),
        "new_isolated_behavioral_coverage_count": len(newly_counted_routes),
        "total_behavioral_coverage_count": prior_standard_count + len(newly_counted_routes),
        "mapping_reconciled_route_count": prior_mapping_count + len(mapping_new_routes),
        "isolated_harness_timeout_seconds": ISOLATED_HARNESS_TIMEOUT_SECONDS,
        "isolated_harness_pass_count": isolated_pass_count,
        "deferred_unready_route_count": len(DEFERRED_UNREADY_ROUTES),
        "route_rows": route_rows,
        "isolated_rows": isolated_rows,
        "blocked_isolated_rows": blocked_isolated_rows,
        "cohort_rows": cohort_rows,
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "deferred_unready_routes": list(DEFERRED_UNREADY_ROUTES),
        "autonomy_route_graduated_to_isolated_behavioral_coverage": bool(autonomy_row.get("ok")),
        "standard_fast_route_coverage_unchanged": True,
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
    _CACHE.clear()
    _CACHE[cache_key] = dict(report)
    return report


def dashboard_slow_route_isolated_behavioral_coverage_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_standard_behavioral_route_count={report.get('prior_standard_behavioral_route_count')}",
        f"isolated_behavioral_route_count={report.get('isolated_behavioral_route_count')}",
        f"new_isolated_behavioral_coverage_count={report.get('new_isolated_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"isolated_harness_timeout_seconds={report.get('isolated_harness_timeout_seconds')}",
        f"isolated_harness_pass_count={report.get('isolated_harness_pass_count')}",
        f"deferred_unready_route_count={report.get('deferred_unready_route_count')}",
        f"autonomy_route_graduated_to_isolated_behavioral_coverage={report.get('autonomy_route_graduated_to_isolated_behavioral_coverage')}",
        f"standard_fast_route_coverage_unchanged={report.get('standard_fast_route_coverage_unchanged')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"route_manifest_replaces_dashboard_routes={report.get('route_manifest_replaces_dashboard_routes')}",
        f"route_manifest_generates_routes={report.get('route_manifest_generates_routes')}",
        f"dashboard_wiring_generated={report.get('dashboard_wiring_generated')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"expands_autonomy={report.get('expands_autonomy')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
        lines.append("\nIsolated route rows:")
        for row in report.get("isolated_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} error={row.get('error')}")
        lines.append("\nDeferred unready routes:")
        for row in report.get("deferred_unready_routes", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: {row.get('reason')}")
        lines.append("\nCohorts:")
        for row in report.get("cohort_rows", []):
            lines.append(f"- {row.get('cohort')}: passed={row.get('passed')}/{row.get('routes')} blocked={row.get('blocked')}")
    return "\n".join(lines)
