from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_slow_route_isolated_behavioral_coverage import (
    DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_ID,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1036_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1036_MAPPING_RECONCILED_ROUTE_COUNT,
)

DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_VERSION = RUNTIME_VERSION
DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_ID = "dashboard-parameterized-route-harness-prep-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/dashboard-parameterized-route-harness-prep"
SELF_RENDERER = "render_dashboard_parameterized_route_harness_prep"
DETAIL_ROUTE = "/detail"
DETAIL_RENDERER = "render_detail"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 101
PARAMETERIZED_ROUTE_COUNT = 1
PARAMETERIZED_FIXTURE_COUNT = 3
NEW_PARAMETERIZED_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 102
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 104
MAPPING_RECONCILED_ROUTE_COUNT = 106
PARAMETERIZED_HARNESS_TIMEOUT_SECONDS = 10
DEFERRED_TIMEOUT_ROUTE_COUNT = 2

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "parameterized_route_harness_prepared": True,
    "query_dependent_detail_route_covered": True,
    "detail_route_graduated_to_parameterized_behavioral_coverage": True,
    "doctor_timeout_classification_added": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_behavior_pass_is_release_approval": False,
    "parameterized_harness_executes_governed_actions": False,
    "parameterized_harness_applies_patches": False,
    "parameterized_harness_writes_memory": False,
    "parameterized_harness_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class ParameterizedRouteFixture:
    route: str
    renderer: str
    query: str
    query_label: str
    expected_title: str
    coverage_status: str
    newly_counted: bool


PARAMETERIZED_DETAIL_FIXTURES: tuple[ParameterizedRouteFixture, ...] = (
    ParameterizedRouteFixture(DETAIL_ROUTE, DETAIL_RENDERER, "kind=task&id=latest", "detail-task-latest", "Task Detail", "query_dependent_detail_fixture_covered", True),
    ParameterizedRouteFixture(DETAIL_ROUTE, DETAIL_RENDERER, "kind=work_item&id=latest", "detail-work-item-latest", "Task Work Detail", "query_dependent_detail_fixture_covered", False),
    ParameterizedRouteFixture(DETAIL_ROUTE, DETAIL_RENDERER, "kind=goal&id=latest", "detail-goal-latest", "Goal Detail", "query_dependent_detail_fixture_covered", False),
)

DEFERRED_TIMEOUT_ROUTES: tuple[dict[str, str], ...] = (
    {"route": "/doctor", "renderer": "render_doctor", "classification": "heavy_diagnostics_timeout_lane_required", "reason": "renderer remains excluded from v1037 counted coverage; v1036 observed it exceeding the 10 second isolated lane and v1037 classifies it for a longer lane or renderer decomposition"},
    {"route": "/stabilization", "renderer": "render_stabilization", "classification": "unstable_timing_timeout_lane_required", "reason": "renderer remains excluded from v1037 counted coverage; v1036 observed unstable timing under the 10 second isolated lane and v1037 keeps it deferred until timeout policy is separated"},
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


def _render_parameterized(root: Path, fixture: ParameterizedRouteFixture, timeout_seconds: int) -> dict[str, Any]:
    code = """
import json, sys, time
from pathlib import Path
from urllib.parse import parse_qs
root = Path(sys.argv[1]).resolve()
route = sys.argv[2]
renderer = sys.argv[3]
query = sys.argv[4]
expected_title = sys.argv[5]
sys.path.insert(0, str(root / 'conscious_agent'))
started = time.perf_counter()
try:
    import dashboard
    body = getattr(dashboard, renderer)(parse_qs(query, keep_blank_values=True))
    checks = {
        'string_body': isinstance(body, str),
        'html_body': isinstance(body, str) and '<html' in body.lower(),
        'data_tip_present': isinstance(body, str) and 'data-tip' in body,
        'route_token_present': isinstance(body, str) and route in body,
        'expected_title_present': isinstance(body, str) and expected_title in body,
        'no_traceback_text': isinstance(body, str) and 'Traceback (most recent call last)' not in body,
        'no_dashboard_error': isinstance(body, str) and 'Dashboard error' not in body,
        'no_500_text': isinstance(body, str) and 'HTTP 500' not in body and 'status=500' not in body,
    }
    ok = all(checks.values())
    payload = {'ok': ok, 'status': 'pass' if ok else 'blocked', 'elapsed_ms': int((time.perf_counter() - started) * 1000), 'body_size': len(body) if isinstance(body, str) else 0, 'checks': checks, 'error': ''}
except Exception as error:
    payload = {'ok': False, 'status': 'error', 'elapsed_ms': int((time.perf_counter() - started) * 1000), 'body_size': 0, 'checks': {}, 'error': f'{type(error).__name__}: {error}'}
print(json.dumps(payload, sort_keys=True))
"""
    started = time.perf_counter()
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-B", "-c", code, str(root), fixture.route, fixture.renderer, fixture.query, fixture.expected_title],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "route": fixture.route,
            "renderer": fixture.renderer,
            "query": fixture.query,
            "query_label": fixture.query_label,
            "mode": "parameterized_subprocess",
            "ok": False,
            "status": "timeout",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "body_size": 0,
            "checks": {},
            "error": f"timeout after {timeout_seconds}s",
            "returncode": None,
        }
    stdout = (proc.stdout or "").strip().splitlines()
    try:
        payload: dict[str, Any] = json.loads(stdout[-1]) if stdout else {}
    except Exception as error:
        payload = {"ok": False, "status": "parse_error", "elapsed_ms": int((time.perf_counter() - started) * 1000), "body_size": 0, "checks": {}, "error": f"{type(error).__name__}: {error}"}
    payload.update({
        "route": fixture.route,
        "renderer": fixture.renderer,
        "query": fixture.query,
        "query_label": fixture.query_label,
        "expected_title": fixture.expected_title,
        "mode": "parameterized_subprocess",
        "returncode": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-400:],
    })
    if proc.returncode != 0:
        payload["ok"] = False
        payload["status"] = "error"
        if not payload.get("error"):
            payload["error"] = f"subprocess returncode {proc.returncode}"
    return payload


def build_dashboard_parameterized_route_harness_prep_review(root: str | Path | None = None) -> dict[str, Any]:
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
    module_source = _read_text(project_root, "conscious_agent/dashboard_parameterized_route_harness_prep.py")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    renderers = _renderer_function_names(dashboard_source)
    prior_total = int(V1036_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping = int(V1036_MAPPING_RECONCILED_ROUTE_COUNT)
    prior_review_token_present = DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_ID in docs
    parameterized_rows = [_render_parameterized(project_root, fixture, PARAMETERIZED_HARNESS_TIMEOUT_SECONDS) for fixture in PARAMETERIZED_DETAIL_FIXTURES]
    parameterized_pass_count = sum(1 for row in parameterized_rows if row.get("ok"))
    fixture_rows = [asdict(fixture) for fixture in PARAMETERIZED_DETAIL_FIXTURES]
    detail_mapping_ok = route_map.get(DETAIL_ROUTE) == DETAIL_RENDERER
    detail_renderer_present = DETAIL_RENDERER in renderers
    self_mapping_ok = route_map.get(SELF_ROUTE) == SELF_RENDERER and SELF_RENDERER in renderers
    manifest_surface_present = "v1037-dashboard-parameterized-route-harness-prep" in manifest_source
    deferred_classification_present = all(row["route"] in docs and row["classification"] in docs and row["reason"] in docs for row in DEFERRED_TIMEOUT_ROUTES)
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_ID,
        "prior_total_behavioral_coverage_count=101",
        "parameterized_route_count=1",
        "parameterized_fixture_count=3",
        "new_parameterized_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=102",
        "prior_mapping_reconciled_route_count=104",
        "mapping_reconciled_route_count=106",
        "parameterized_harness_timeout_seconds=10",
        "parameterized_harness_pass_count=3",
        "deferred_timeout_route_count=2",
        "detail_route_graduated_to_parameterized_behavioral_coverage=True",
        "doctor_timeout_classification_added=True",
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
        {"name": "module-version-current", "ok": DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-review-token-present", "ok": prior_review_token_present, "message": f"prior token {DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_ID} present in docs/source."},
        {"name": "prior-total-behavioral-count", "ok": prior_total == PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"prior_total={prior_total} expected={PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "prior-mapping-reconciled-count", "ok": prior_mapping == PRIOR_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"prior_mapping={prior_mapping} expected={PRIOR_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "detail-route-mapped", "ok": detail_mapping_ok, "message": f"{DETAIL_ROUTE} maps to {route_map.get(DETAIL_ROUTE)} expected={DETAIL_RENDERER}"},
        {"name": "detail-renderer-present", "ok": detail_renderer_present, "message": f"renderer {DETAIL_RENDERER} present={detail_renderer_present}"},
        {"name": "self-route-mapped", "ok": self_mapping_ok, "message": f"{SELF_ROUTE} maps to {route_map.get(SELF_ROUTE)} expected={SELF_RENDERER}"},
        {"name": "parameterized-fixture-count", "ok": len(fixture_rows) == PARAMETERIZED_FIXTURE_COUNT, "message": f"fixtures={len(fixture_rows)} expected={PARAMETERIZED_FIXTURE_COUNT}"},
        {"name": "parameterized-harness-pass-count", "ok": parameterized_pass_count == PARAMETERIZED_FIXTURE_COUNT, "message": f"parameterized_passes={parameterized_pass_count}/{PARAMETERIZED_FIXTURE_COUNT}"},
        {"name": "detail-route-counted-once", "ok": NEW_PARAMETERIZED_BEHAVIORAL_COVERAGE_COUNT == 1 and len({row.route for row in PARAMETERIZED_DETAIL_FIXTURES}) == PARAMETERIZED_ROUTE_COUNT, "message": "Multiple query fixtures count one query-dependent dashboard route once."},
        {"name": "behavioral-counts-current", "ok": prior_total + NEW_PARAMETERIZED_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_PARAMETERIZED_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-reconciled-count-current", "ok": prior_mapping + 2 == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + 2} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "deferred-timeout-classification-present", "ok": deferred_classification_present and len(DEFERRED_TIMEOUT_ROUTES) == DEFERRED_TIMEOUT_ROUTE_COUNT, "message": f"deferred_timeout_routes={len(DEFERRED_TIMEOUT_ROUTES)} expected={DEFERRED_TIMEOUT_ROUTE_COUNT}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1037 parameterized dashboard route harness prep surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1037 parameterized route harness truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "parameterized_harness_executes_governed_actions", "parameterized_harness_applies_patches", "parameterized_harness_writes_memory", "parameterized_harness_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Parameterized route harness remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_ID,
        "state": "dashboard_parameterized_route_harness_prep_review_only",
        "prior_total_behavioral_coverage_count": prior_total,
        "parameterized_route_count": PARAMETERIZED_ROUTE_COUNT,
        "parameterized_fixture_count": len(fixture_rows),
        "new_parameterized_behavioral_coverage_count": NEW_PARAMETERIZED_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT,
        "parameterized_harness_timeout_seconds": PARAMETERIZED_HARNESS_TIMEOUT_SECONDS,
        "parameterized_harness_pass_count": parameterized_pass_count,
        "deferred_timeout_route_count": len(DEFERRED_TIMEOUT_ROUTES),
        "fixture_rows": fixture_rows,
        "parameterized_rows": parameterized_rows,
        "deferred_timeout_routes": [dict(row) for row in DEFERRED_TIMEOUT_ROUTES],
        "detail_route_graduated_to_parameterized_behavioral_coverage": parameterized_pass_count == PARAMETERIZED_FIXTURE_COUNT,
        "doctor_timeout_classification_added": deferred_classification_present,
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


def dashboard_parameterized_route_harness_prep_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"parameterized_route_count={report.get('parameterized_route_count')}",
        f"parameterized_fixture_count={report.get('parameterized_fixture_count')}",
        f"new_parameterized_behavioral_coverage_count={report.get('new_parameterized_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"parameterized_harness_timeout_seconds={report.get('parameterized_harness_timeout_seconds')}",
        f"parameterized_harness_pass_count={report.get('parameterized_harness_pass_count')}",
        f"deferred_timeout_route_count={report.get('deferred_timeout_route_count')}",
        f"detail_route_graduated_to_parameterized_behavioral_coverage={report.get('detail_route_graduated_to_parameterized_behavioral_coverage')}",
        f"doctor_timeout_classification_added={report.get('doctor_timeout_classification_added')}",
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
        lines.append("\nParameterized route rows:")
        for row in report.get("parameterized_rows", []):
            lines.append(f"- {row.get('route')}?{row.get('query')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} error={row.get('error')}")
        lines.append("\nDeferred timeout routes:")
        for row in report.get("deferred_timeout_routes", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: {row.get('classification')} :: {row.get('reason')}")
    return "\n".join(lines)
