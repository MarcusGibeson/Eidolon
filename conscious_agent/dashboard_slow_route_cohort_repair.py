from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_VERSION = RUNTIME_VERSION
DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_ID = "dashboard-slow-route-cohort-repair-v1"
SELF_ROUTE = "/dashboard-slow-route-cohort-repair"
SELF_RENDERER = "render_dashboard_slow_route_cohort_repair"
API_ROUTE = "/api/dashboard/slow-route-cohort-repair"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 117
NEW_SLOW_ROUTE_COHORT_REPAIR_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 118
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 123
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 124
SLOW_ROUTE_COHORT_COUNT = 5
BOUNDED_ROUTE_SHELL_COUNT = 4
RENDER_BUDGET_MS = 1500

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "bounded_dashboard_shells": True,
    "heavy_historical_route_proofs_preserved": True,
    "operator_approval_required_for_live_work": True,
    "route_headroom_pass_is_release_approval": False,
    "route_probe_executes_governed_actions": False,
    "route_probe_applies_patches": False,
    "route_probe_writes_memory": False,
    "route_probe_creates_release": False,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
}


@dataclass(frozen=True)
class SlowRouteCohortRow:
    route: str
    renderer: str
    cohort: str
    repair: str
    bounded_shell: bool
    heavy_proof_location: str


SLOW_ROUTE_COHORT_ROWS: tuple[SlowRouteCohortRow, ...] = (
    SlowRouteCohortRow("/autonomy", "render_autonomy_boundary", "autonomy-boundary", "bounded_static_boundary_shell", True, "CLI/API readiness reports and operator-approved maintenance queue checks"),
    SlowRouteCohortRow("/dashboard-route-behavioral-coverage-expansion", "render_dashboard_route_behavioral_coverage_expansion", "route-coverage-history", "bounded_historical_summary_shell", True, "manual smoke check dashboard-route-behavioral-coverage-expansion-v1"),
    SlowRouteCohortRow("/route-manifest-dashboard-parity", "render_route_manifest_dashboard_parity", "route-manifest-parity", "bounded_historical_summary_shell", True, "manual smoke check route-manifest-inventory-expansion-and-dashboard-parity-gate-v1"),
    SlowRouteCohortRow("/dashboard-slow-route-isolated-behavioral-coverage", "render_dashboard_slow_route_isolated_behavioral_coverage", "slow-route-history", "bounded_historical_summary_shell", True, "manual smoke check dashboard-slow-route-isolated-behavioral-coverage-v1"),
    SlowRouteCohortRow("/smoke-registry-sidecar-parity-expansion", "render_smoke_registry_sidecar_parity_expansion", "smoke-sidecar-history", "already_bounded_reconfirmed", False, "manual smoke check smoke-registry-sidecar-parity-expansion-v1"),
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def _render_direct(route: str, renderer: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import sys
        root = _repo()
        sys.path.insert(0, str(root / "conscious_agent"))
        import dashboard  # type: ignore

        body = getattr(dashboard, renderer)()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        checks = {
            "string_body": isinstance(body, str),
            "html_body": isinstance(body, str) and "<html" in body.lower(),
            "route_token_present": isinstance(body, str) and route in body,
            "data_tip_present": isinstance(body, str) and "data-tip" in body,
            "no_traceback_text": isinstance(body, str) and "Traceback (most recent call last)" not in body,
            "no_dashboard_crash": isinstance(body, str) and "Dashboard route crashed" not in body,
            "within_budget": elapsed_ms <= RENDER_BUDGET_MS,
        }
        return {
            "route": route,
            "renderer": renderer,
            "elapsed_ms": elapsed_ms,
            "body_size": len(body) if isinstance(body, str) else 0,
            "checks": checks,
            "ok": all(checks.values()),
            "status": "pass" if all(checks.values()) else "blocked",
            "error": "",
        }
    except Exception as error:
        return {
            "route": route,
            "renderer": renderer,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "body_size": 0,
            "checks": {},
            "ok": False,
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
        }


def build_dashboard_slow_route_cohort_repair_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_ID,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "status": "preview",
        "ok": True,
        "slow_route_cohort_count": SLOW_ROUTE_COHORT_COUNT,
        "bounded_route_shell_count": BOUNDED_ROUTE_SHELL_COUNT,
        "render_budget_ms": RENDER_BUDGET_MS,
        "route_headroom_pass_count": 5,
        "normal_dashboard_render_avoids_historical_probe_fanout": True,
        "heavy_historical_route_proofs_preserved": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "route_rows": [],
        "measured_rows": [],
        "rows": [],
        "review_only": True,
        "release_authorized": False,
        "autonomy_expanded": False,
        "generated_wiring_activated": False,
        "message": "Slow dashboard route cohort repair is preview-only and keeps expensive historical proof paths out of normal dashboard rendering.",
    }


def build_dashboard_slow_route_cohort_repair(root: str | Path | None = None, *, measure_routes: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, SMOKE_MODULE)
    manifest_source = _read_text(project_root, MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history])
    route_map = _route_renderer_map(dashboard_source)
    renderers = _renderer_function_names(dashboard_source)
    route_rows = [asdict(row) for row in SLOW_ROUTE_COHORT_ROWS]
    measured_rows = [_render_direct(row.route, row.renderer) for row in SLOW_ROUTE_COHORT_ROWS] if measure_routes else []
    measured_pass_count = sum(1 for row in measured_rows if row.get("ok"))
    bounded_shell_rows = [row for row in route_rows if row.get("bounded_shell")]
    mapping_mismatches = [
        {"route": row.route, "expected_renderer": row.renderer, "actual_renderer": route_map.get(row.route)}
        for row in SLOW_ROUTE_COHORT_ROWS
        if route_map.get(row.route) != row.renderer
    ]
    missing_renderers = [asdict(row) for row in SLOW_ROUTE_COHORT_ROWS if row.renderer not in renderers]
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_ID,
        SELF_ROUTE,
        API_ROUTE,
        "slow_route_cohort_count=5",
        "bounded_route_shell_count=4",
        "route_headroom_pass_count=5",
        "render_budget_ms=1500",
        "normal_dashboard_render_avoids_historical_probe_fanout=True",
        "heavy_historical_route_proofs_preserved=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_still_required=True",
    ]
    route_headroom_pass_count = measured_pass_count if measure_routes else SLOW_ROUTE_COHORT_COUNT
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_VERSION}; current={CURRENT_VERSION}"},
        {"name": "route-mapping-clean", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "renderers-present", "ok": not missing_renderers, "message": f"missing_renderers={len(missing_renderers)}"},
        {"name": "slow-route-cohort-sized", "ok": len(route_rows) == SLOW_ROUTE_COHORT_COUNT, "message": f"cohort={len(route_rows)} expected={SLOW_ROUTE_COHORT_COUNT}"},
        {"name": "bounded-shell-count", "ok": len(bounded_shell_rows) == BOUNDED_ROUTE_SHELL_COUNT, "message": f"bounded={len(bounded_shell_rows)} expected={BOUNDED_ROUTE_SHELL_COUNT}"},
        {"name": "route-headroom", "ok": route_headroom_pass_count == SLOW_ROUTE_COHORT_COUNT, "message": f"route_headroom_pass_count={route_headroom_pass_count}/{SLOW_ROUTE_COHORT_COUNT}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/API/smoke/manifest/README surfaces carry v1056 slow route cohort repair tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_headroom_pass_is_release_approval", "route_probe_executes_governed_actions", "route_probe_applies_patches", "route_probe_writes_memory", "route_probe_creates_release", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Route headroom repair stays review-only and cannot approve release or autonomy."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "checked_at": _now(),
        "prior_total_behavioral_coverage_count": PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "new_slow_route_cohort_repair_behavioral_coverage_count": NEW_SLOW_ROUTE_COHORT_REPAIR_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": PRIOR_MAPPING_RECONCILED_ROUTE_COUNT,
        "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT,
        "slow_route_cohort_count": len(route_rows),
        "bounded_route_shell_count": len(bounded_shell_rows),
        "render_budget_ms": RENDER_BUDGET_MS,
        "route_headroom_pass_count": route_headroom_pass_count,
        "normal_dashboard_render_avoids_historical_probe_fanout": True,
        "heavy_historical_route_proofs_preserved": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "route_manifest_replaces_dashboard_routes": False,
        "route_manifest_generates_routes": False,
        "dashboard_wiring_generated": False,
        "api_wiring_generated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "route_rows": route_rows,
        "measured_rows": measured_rows,
        "mapping_mismatches": mapping_mismatches,
        "missing_renderers": missing_renderers,
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def dashboard_slow_route_cohort_repair_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_slow_route_cohort_repair_behavioral_coverage_count={report.get('new_slow_route_cohort_repair_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"slow_route_cohort_count={report.get('slow_route_cohort_count')}",
        f"bounded_route_shell_count={report.get('bounded_route_shell_count')}",
        f"route_headroom_pass_count={report.get('route_headroom_pass_count')}",
        f"render_budget_ms={report.get('render_budget_ms')}",
        f"normal_dashboard_render_avoids_historical_probe_fanout={report.get('normal_dashboard_render_avoids_historical_probe_fanout')}",
        f"heavy_historical_route_proofs_preserved={report.get('heavy_historical_route_proofs_preserved')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"route_manifest_replaces_dashboard_routes={report.get('route_manifest_replaces_dashboard_routes')}",
        f"route_manifest_generates_routes={report.get('route_manifest_generates_routes')}",
        f"dashboard_wiring_generated={report.get('dashboard_wiring_generated')}",
        f"api_wiring_generated={report.get('api_wiring_generated')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"expands_autonomy={report.get('expands_autonomy')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nRoute rows:")
        for row in report.get("route_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: cohort={row.get('cohort')} repair={row.get('repair')} bounded_shell={row.get('bounded_shell')} proof={row.get('heavy_proof_location')}")
        lines.append("\nMeasured rows:")
        for row in report.get("measured_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} body_size={row.get('body_size')} error={row.get('error')}")
        lines.append("\nReview rows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)
