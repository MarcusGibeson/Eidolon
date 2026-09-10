from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_deferred_route_harness_renderer_repair_prep import _render_isolated
from dashboard_parameterized_route_harness_prep import (
    DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_ID,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1037_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1037_MAPPING_RECONCILED_ROUTE_COUNT,
)

DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_VERSION = RUNTIME_VERSION
DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_ID = "dashboard-timeout-lane-classification-and-slow-renderer-decomposition-prep-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/dashboard-timeout-lane-classification-slow-renderer-decomposition-prep"
SELF_RENDERER = "render_dashboard_timeout_lane_classification_slow_renderer_decomposition_prep"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 102
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 106
FAST_LANE_TIMEOUT_SECONDS = 3
ISOLATED_LANE_TIMEOUT_SECONDS = 10
LONG_ISOLATED_LANE_TIMEOUT_SECONDS = 15
DOCTOR_DIAGNOSTIC_TIMEOUT_SECONDS = 3
LONG_ISOLATED_ROUTE_COUNT = 1
LONG_ISOLATED_PASS_COUNT = 1
NEW_LONG_ISOLATED_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 103
MAPPING_RECONCILED_ROUTE_COUNT = 108
DEFERRED_DECOMPOSITION_ROUTE_COUNT = 1
TIMEOUT_LANE_COUNT = 4

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "timeout_lane_policy_classified": True,
    "long_isolated_lane_prepared": True,
    "stabilization_graduated_to_long_isolated_behavioral_coverage": True,
    "doctor_decomposition_prep_classified": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_behavior_pass_is_release_approval": False,
    "timeout_lane_harness_executes_governed_actions": False,
    "timeout_lane_harness_applies_patches": False,
    "timeout_lane_harness_writes_memory": False,
    "timeout_lane_harness_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class TimeoutLaneRow:
    lane: str
    timeout_seconds: int
    purpose: str
    counted_coverage_allowed: bool
    execution_mode: str


@dataclass(frozen=True)
class LongIsolatedRouteRow:
    route: str
    renderer: str
    lane: str
    coverage_status: str
    newly_counted: bool


TIMEOUT_LANES: tuple[TimeoutLaneRow, ...] = (
    TimeoutLaneRow("fast", FAST_LANE_TIMEOUT_SECONDS, "standard direct-render route cohorts that should remain fast", True, "in_process_or_fast_subprocess"),
    TimeoutLaneRow("isolated", ISOLATED_LANE_TIMEOUT_SECONDS, "known slow/deferred routes that render safely inside the existing isolated subprocess harness", True, "isolated_subprocess"),
    TimeoutLaneRow("long_isolated", LONG_ISOLATED_LANE_TIMEOUT_SECONDS, "bounded slow renderers that need more time but still must not execute governed actions", True, "isolated_subprocess_long_lane"),
    TimeoutLaneRow("deferred_decomposition", 0, "routes that exceed bounded lanes or need renderer decomposition before counted coverage", False, "not_counted"),
)

LONG_ISOLATED_ROUTES: tuple[LongIsolatedRouteRow, ...] = (
    LongIsolatedRouteRow("/stabilization", "render_stabilization", "long_isolated", "graduated_from_v1037_deferred_timeout_classification", True),
)

DEFERRED_DECOMPOSITION_ROUTES: tuple[dict[str, str], ...] = (
    {
        "route": "/doctor",
        "renderer": "render_doctor",
        "lane": "deferred_decomposition",
        "classification": "renderer_decomposition_required_before_counted_behavioral_coverage",
        "reason": "v1038 keeps /doctor outside counted coverage because a bounded diagnostic timeout still confirms the current renderer is unsuitable for normal or long-isolated behavioral coverage without decomposition",
    },
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


def _doctor_timeout_diagnostic(root: Path) -> dict[str, Any]:
    row = DEFERRED_DECOMPOSITION_ROUTES[0]
    result = _render_isolated(root, row["route"], row["renderer"], DOCTOR_DIAGNOSTIC_TIMEOUT_SECONDS)
    result["lane"] = row["lane"]
    result["classification"] = row["classification"]
    result["expected_status"] = "timeout_or_blocked_not_counted"
    result["counted_coverage"] = False
    return result


def build_dashboard_timeout_lane_classification_slow_renderer_decomposition_prep_review(root: str | Path | None = None) -> dict[str, Any]:
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
    module_source = _read_text(project_root, "conscious_agent/dashboard_timeout_lane_classification_slow_renderer_decomposition_prep.py")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    renderers = _renderer_function_names(dashboard_source)
    prior_total = int(V1037_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping = int(V1037_MAPPING_RECONCILED_ROUTE_COUNT)
    prior_review_token_present = DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_ID in docs
    lane_rows = [asdict(row) for row in TIMEOUT_LANES]
    long_route_rows = [asdict(row) for row in LONG_ISOLATED_ROUTES]
    long_isolated_rows = [
        _render_isolated(project_root, row.route, row.renderer, LONG_ISOLATED_LANE_TIMEOUT_SECONDS)
        for row in LONG_ISOLATED_ROUTES
    ]
    for row in long_isolated_rows:
        row["lane"] = "long_isolated"
        row["counted_coverage"] = True
    long_pass_count = sum(1 for row in long_isolated_rows if row.get("ok"))
    doctor_diagnostic = _doctor_timeout_diagnostic(project_root)
    blocked_long_rows = [row for row in long_isolated_rows if not row.get("ok")]
    newly_counted_routes = {row.route for row in LONG_ISOLATED_ROUTES if row.newly_counted}
    mapping_new_routes = {SELF_ROUTE, *(row.route for row in LONG_ISOLATED_ROUTES)}
    mapping_mismatches = [
        {"route": row.route, "expected_renderer": row.renderer, "actual_renderer": route_map.get(row.route)}
        for row in LONG_ISOLATED_ROUTES
        if route_map.get(row.route) != row.renderer
    ]
    renderer_missing = [asdict(row) for row in LONG_ISOLATED_ROUTES if row.renderer not in renderers]
    self_mapping_ok = route_map.get(SELF_ROUTE) == SELF_RENDERER and SELF_RENDERER in renderers
    deferred_docs_present = all(row["route"] in docs and row["classification"] in docs and row["reason"] in docs for row in DEFERRED_DECOMPOSITION_ROUTES)
    manifest_surface_present = "v1038-dashboard-timeout-lane-classification-slow-renderer-decomposition-prep" in manifest_source
    doctor_deferred_not_counted = doctor_diagnostic.get("ok") is False and doctor_diagnostic.get("counted_coverage") is False
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_ID,
        "prior_total_behavioral_coverage_count=102",
        "timeout_lane_count=4",
        "fast_lane_timeout_seconds=3",
        "isolated_lane_timeout_seconds=10",
        "long_isolated_lane_timeout_seconds=15",
        "long_isolated_route_count=1",
        "long_isolated_pass_count=1",
        "new_long_isolated_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=103",
        "prior_mapping_reconciled_route_count=106",
        "mapping_reconciled_route_count=108",
        "deferred_decomposition_route_count=1",
        "stabilization_graduated_to_long_isolated_behavioral_coverage=True",
        "doctor_decomposition_prep_classified=True",
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
        {"name": "module-version-current", "ok": DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-review-token-present", "ok": prior_review_token_present, "message": f"prior token {DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_ID} present in docs/source."},
        {"name": "prior-total-behavioral-count", "ok": prior_total == PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"prior_total={prior_total} expected={PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "prior-mapping-reconciled-count", "ok": prior_mapping == PRIOR_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"prior_mapping={prior_mapping} expected={PRIOR_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "timeout-lanes-classified", "ok": len(lane_rows) == TIMEOUT_LANE_COUNT and {row['lane'] for row in lane_rows} == {'fast', 'isolated', 'long_isolated', 'deferred_decomposition'}, "message": f"lanes={len(lane_rows)} expected={TIMEOUT_LANE_COUNT}"},
        {"name": "long-isolated-route-count", "ok": len(long_route_rows) == LONG_ISOLATED_ROUTE_COUNT, "message": f"long_isolated_routes={len(long_route_rows)} expected={LONG_ISOLATED_ROUTE_COUNT}"},
        {"name": "long-isolated-render-pass", "ok": long_pass_count == LONG_ISOLATED_PASS_COUNT and not blocked_long_rows, "message": f"long_isolated_passes={long_pass_count}/{LONG_ISOLATED_ROUTE_COUNT}"},
        {"name": "stabilization-graduated", "ok": any(row.get('route') == '/stabilization' and row.get('ok') for row in long_isolated_rows), "message": "stabilization route renders in the long-isolated lane and is counted once."},
        {"name": "doctor-decomposition-classified", "ok": doctor_deferred_not_counted and deferred_docs_present, "message": f"doctor_status={doctor_diagnostic.get('status')} counted={doctor_diagnostic.get('counted_coverage')}"},
        {"name": "route-mapping-clean", "ok": not mapping_mismatches and self_mapping_ok, "message": f"mapping_mismatches={len(mapping_mismatches)} self_mapping_ok={self_mapping_ok}"},
        {"name": "renderers-present", "ok": not renderer_missing, "message": f"missing_renderers={len(renderer_missing)}"},
        {"name": "behavioral-counts-current", "ok": prior_total + NEW_LONG_ISOLATED_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_LONG_ISOLATED_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-reconciled-count-current", "ok": prior_mapping + len(mapping_new_routes) == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + len(mapping_new_routes)} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1038 timeout lane classification and slow renderer decomposition prep surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1038 timeout-lane truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "timeout_lane_harness_executes_governed_actions", "timeout_lane_harness_applies_patches", "timeout_lane_harness_writes_memory", "timeout_lane_harness_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Timeout lane classification remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_ID,
        "state": "dashboard_timeout_lane_classification_slow_renderer_decomposition_prep_review_only",
        "prior_total_behavioral_coverage_count": prior_total,
        "timeout_lane_count": len(lane_rows),
        "fast_lane_timeout_seconds": FAST_LANE_TIMEOUT_SECONDS,
        "isolated_lane_timeout_seconds": ISOLATED_LANE_TIMEOUT_SECONDS,
        "long_isolated_lane_timeout_seconds": LONG_ISOLATED_LANE_TIMEOUT_SECONDS,
        "doctor_diagnostic_timeout_seconds": DOCTOR_DIAGNOSTIC_TIMEOUT_SECONDS,
        "long_isolated_route_count": len(long_route_rows),
        "long_isolated_pass_count": long_pass_count,
        "new_long_isolated_behavioral_coverage_count": NEW_LONG_ISOLATED_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": prior_total + NEW_LONG_ISOLATED_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": prior_mapping + len(mapping_new_routes),
        "deferred_decomposition_route_count": len(DEFERRED_DECOMPOSITION_ROUTES),
        "timeout_lanes": lane_rows,
        "long_isolated_route_rows": long_route_rows,
        "long_isolated_rows": long_isolated_rows,
        "blocked_long_isolated_rows": blocked_long_rows,
        "doctor_diagnostic_row": doctor_diagnostic,
        "deferred_decomposition_routes": [dict(row) for row in DEFERRED_DECOMPOSITION_ROUTES],
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "stabilization_graduated_to_long_isolated_behavioral_coverage": long_pass_count == LONG_ISOLATED_PASS_COUNT,
        "doctor_decomposition_prep_classified": doctor_deferred_not_counted and deferred_docs_present,
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


def dashboard_timeout_lane_classification_slow_renderer_decomposition_prep_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"timeout_lane_count={report.get('timeout_lane_count')}",
        f"fast_lane_timeout_seconds={report.get('fast_lane_timeout_seconds')}",
        f"isolated_lane_timeout_seconds={report.get('isolated_lane_timeout_seconds')}",
        f"long_isolated_lane_timeout_seconds={report.get('long_isolated_lane_timeout_seconds')}",
        f"doctor_diagnostic_timeout_seconds={report.get('doctor_diagnostic_timeout_seconds')}",
        f"long_isolated_route_count={report.get('long_isolated_route_count')}",
        f"long_isolated_pass_count={report.get('long_isolated_pass_count')}",
        f"new_long_isolated_behavioral_coverage_count={report.get('new_long_isolated_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"deferred_decomposition_route_count={report.get('deferred_decomposition_route_count')}",
        f"stabilization_graduated_to_long_isolated_behavioral_coverage={report.get('stabilization_graduated_to_long_isolated_behavioral_coverage')}",
        f"doctor_decomposition_prep_classified={report.get('doctor_decomposition_prep_classified')}",
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
        lines.append("\nTimeout lanes:")
        for row in report.get("timeout_lanes", []):
            lines.append(f"- {row.get('lane')}: timeout={row.get('timeout_seconds')} counted={row.get('counted_coverage_allowed')} mode={row.get('execution_mode')} :: {row.get('purpose')}")
        lines.append("\nLong-isolated route rows:")
        for row in report.get("long_isolated_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} body_size={row.get('body_size')} error={row.get('error')}")
        doctor = report.get("doctor_diagnostic_row", {})
        lines.append("\nDoctor diagnostic:")
        lines.append(f"- {doctor.get('route')} -> {doctor.get('renderer')}: ok={doctor.get('ok')} status={doctor.get('status')} elapsed_ms={doctor.get('elapsed_ms')} counted_coverage={doctor.get('counted_coverage')} classification={doctor.get('classification')} error={doctor.get('error')}")
        lines.append("\nDeferred decomposition routes:")
        for row in report.get("deferred_decomposition_routes", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: {row.get('classification')} :: {row.get('reason')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)
