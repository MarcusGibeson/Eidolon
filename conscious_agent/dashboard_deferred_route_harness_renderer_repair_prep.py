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
from dashboard_route_behavioral_coverage_continuation import build_dashboard_route_behavioral_coverage_continuation_review

DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_VERSION = RUNTIME_VERSION
DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_ID = "dashboard-deferred-route-harness-renderer-repair-prep-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/dashboard-deferred-route-harness-renderer-repair-prep"
SELF_RENDERER = "render_dashboard_deferred_route_harness_renderer_repair_prep"
REPAIRED_ROUTE = "/execution-approval-scope"
REPAIRED_RENDERER = "render_execution_approval_scope"
SLOW_ROUTE = "/autonomy"
SLOW_RENDERER = "render_autonomy_boundary"
PRIOR_BEHAVIORAL_ROUTE_COUNT = 96
REPAIRED_BEHAVIORAL_ROUTE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 97
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 99
MAPPING_RECONCILED_ROUTE_COUNT = 101
ISOLATED_HARNESS_ROUTE_COUNT = 2
ISOLATED_HARNESS_TIMEOUT_SECONDS = 10

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "deferred_route_harness_prepared": True,
    "renderer_missing_helper_fallback_repaired": True,
    "execution_approval_scope_repaired": True,
    "autonomy_route_isolated_timebox_available": True,
    "autonomy_route_standard_direct_coverage_deferred": True,
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
class DeferredHarnessRoute:
    route: str
    renderer: str
    classification: str
    timeout_seconds: int
    standard_behavioral_coverage: bool


HARNESS_ROUTES: tuple[DeferredHarnessRoute, ...] = (
    DeferredHarnessRoute(REPAIRED_ROUTE, REPAIRED_RENDERER, "repaired_missing_helper_renderer", ISOLATED_HARNESS_TIMEOUT_SECONDS, True),
    DeferredHarnessRoute(SLOW_ROUTE, SLOW_RENDERER, "slow_route_isolated_timebox_probe", ISOLATED_HARNESS_TIMEOUT_SECONDS, False),
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


def _body_checks(route: str, body: Any) -> dict[str, bool]:
    return {
        "string_body": isinstance(body, str),
        "html_body": isinstance(body, str) and "<html" in body.lower(),
        "data_tip_present": isinstance(body, str) and "data-tip" in body,
        "route_token_present": isinstance(body, str) and route in body,
        "no_traceback_text": isinstance(body, str) and "Traceback (most recent call last)" not in body,
        "no_dashboard_error": isinstance(body, str) and "Dashboard error" not in body,
        "no_500_text": isinstance(body, str) and "HTTP 500" not in body and "status=500" not in body,
    }


def _render_direct(route: str, renderer: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import dashboard  # type: ignore

        fn = getattr(dashboard, renderer)
        body = fn()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        checks = _body_checks(route, body)
        ok = all(checks.values())
        return {
            "route": route,
            "renderer": renderer,
            "mode": "direct",
            "ok": ok,
            "status": "pass" if ok else "blocked",
            "elapsed_ms": elapsed_ms,
            "body_size": len(body) if isinstance(body, str) else 0,
            "checks": checks,
            "error": "",
        }
    except Exception as error:
        return {
            "route": route,
            "renderer": renderer,
            "mode": "direct",
            "ok": False,
            "status": "error",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "body_size": 0,
            "checks": {},
            "error": f"{type(error).__name__}: {error}",
        }


def _render_isolated(root: Path, route: str, renderer: str, timeout_seconds: int) -> dict[str, Any]:
    code = """
import json, sys, time
from pathlib import Path
root = Path(sys.argv[1]).resolve()
route = sys.argv[2]
renderer = sys.argv[3]
sys.path.insert(0, str(root / 'conscious_agent'))
started = time.perf_counter()
try:
    import dashboard
    body = getattr(dashboard, renderer)()
    checks = {
        'string_body': isinstance(body, str),
        'html_body': isinstance(body, str) and '<html' in body.lower(),
        'data_tip_present': isinstance(body, str) and 'data-tip' in body,
        'route_token_present': isinstance(body, str) and route in body,
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
            [sys.executable, "-I", "-B", "-c", code, str(root), route, renderer],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "route": route,
            "renderer": renderer,
            "mode": "isolated_subprocess",
            "ok": False,
            "status": "timeout",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "body_size": 0,
            "checks": {},
            "error": f"timeout after {timeout_seconds}s",
            "returncode": None,
        }
    stdout = (proc.stdout or "").strip().splitlines()
    payload: dict[str, Any]
    try:
        payload = json.loads(stdout[-1]) if stdout else {}
    except Exception as error:
        payload = {"ok": False, "status": "parse_error", "elapsed_ms": int((time.perf_counter() - started) * 1000), "body_size": 0, "checks": {}, "error": f"{type(error).__name__}: {error}"}
    payload.update({"route": route, "renderer": renderer, "mode": "isolated_subprocess", "returncode": proc.returncode, "stderr_tail": (proc.stderr or "")[-400:]})
    if proc.returncode != 0:
        payload["ok"] = False
        payload["status"] = "error"
        if not payload.get("error"):
            payload["error"] = f"subprocess returncode {proc.returncode}"
    return payload


def build_dashboard_deferred_route_harness_renderer_repair_prep_review(root: str | Path | None = None) -> dict[str, Any]:
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
    prior = build_dashboard_route_behavioral_coverage_continuation_review(project_root)
    prior_count = int(prior.get("total_behavioral_coverage_count") or 0)
    prior_mapping_count = int(prior.get("mapping_reconciled_route_count") or 0)
    repaired_direct = _render_direct(REPAIRED_ROUTE, REPAIRED_RENDERER)
    isolated_rows = [_render_isolated(project_root, row.route, row.renderer, row.timeout_seconds) for row in HARNESS_ROUTES]
    isolated_pass_count = sum(1 for row in isolated_rows if row.get("ok"))
    repaired_isolated = next((row for row in isolated_rows if row.get("route") == REPAIRED_ROUTE), {})
    autonomy_isolated = next((row for row in isolated_rows if row.get("route") == SLOW_ROUTE), {})
    route_rows = [asdict(row) for row in HARNESS_ROUTES]
    mapping_mismatches = [
        {"route": row.route, "expected_renderer": row.renderer, "actual_renderer": route_map.get(row.route)}
        for row in HARNESS_ROUTES
        if route_map.get(row.route) != row.renderer
    ]
    renderer_missing = [asdict(row) for row in HARNESS_ROUTES if row.renderer not in renderers]
    fallback_repair_present = "missing_runtime_text_helper" in dashboard_source and "getattr(sm_v95, f\"{final_slug}_text\", None)" in dashboard_source
    manifest_surface_present = "v1035-dashboard-deferred-route-harness-renderer-repair-prep" in manifest_source
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_ID,
        "prior_behavioral_route_count=96",
        "repaired_behavioral_route_count=1",
        "total_behavioral_coverage_count=97",
        "prior_mapping_reconciled_route_count=99",
        "mapping_reconciled_route_count=101",
        "isolated_harness_route_count=2",
        "isolated_harness_pass_count=2",
        "execution_approval_scope_repaired=True",
        "renderer_missing_helper_fallback_repaired=True",
        "autonomy_route_standard_direct_coverage_deferred=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-behavioral-count", "ok": prior_count == PRIOR_BEHAVIORAL_ROUTE_COUNT, "message": f"prior={prior_count} expected={PRIOR_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "prior-mapping-reconciled-count", "ok": prior_mapping_count == PRIOR_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"prior_mapping={prior_mapping_count} expected={PRIOR_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "harness-route-count", "ok": len(route_rows) == ISOLATED_HARNESS_ROUTE_COUNT, "message": f"harness_routes={len(route_rows)} expected={ISOLATED_HARNESS_ROUTE_COUNT}"},
        {"name": "harness-route-mapping-clean", "ok": not mapping_mismatches, "message": f"mapping mismatches={len(mapping_mismatches)}"},
        {"name": "harness-renderers-present", "ok": not renderer_missing, "message": f"missing renderers={len(renderer_missing)}"},
        {"name": "renderer-fallback-repair-present", "ok": fallback_repair_present, "message": "dashboard runtime arc renderer has fallback text for missing historical self_maintenance helpers."},
        {"name": "execution-approval-scope-direct-render-repaired", "ok": bool(repaired_direct.get("ok")), "message": f"{REPAIRED_ROUTE} direct status={repaired_direct.get('status')} error={repaired_direct.get('error')}"},
        {"name": "execution-approval-scope-isolated-render-repaired", "ok": bool(repaired_isolated.get("ok")), "message": f"{REPAIRED_ROUTE} isolated status={repaired_isolated.get('status')} elapsed_ms={repaired_isolated.get('elapsed_ms')}"},
        {"name": "autonomy-route-isolated-timebox-ready", "ok": bool(autonomy_isolated.get("ok")), "message": f"{SLOW_ROUTE} isolated status={autonomy_isolated.get('status')} elapsed_ms={autonomy_isolated.get('elapsed_ms')} timeout={ISOLATED_HARNESS_TIMEOUT_SECONDS}s"},
        {"name": "isolated-harness-pass-count", "ok": isolated_pass_count == ISOLATED_HARNESS_ROUTE_COUNT, "message": f"isolated_passes={isolated_pass_count}/{ISOLATED_HARNESS_ROUTE_COUNT}"},
        {"name": "behavioral-counts-current", "ok": prior_count + REPAIRED_BEHAVIORAL_ROUTE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_count + REPAIRED_BEHAVIORAL_ROUTE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-reconciled-count-current", "ok": prior_mapping_count + REPAIRED_BEHAVIORAL_ROUTE_COUNT + 1 == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping_count + REPAIRED_BEHAVIORAL_ROUTE_COUNT + 1} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1035 deferred route harness and renderer repair prep surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1035 deferred route harness truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "isolated_route_harness_executes_governed_actions", "isolated_route_harness_applies_patches", "isolated_route_harness_writes_memory", "isolated_route_harness_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Deferred route harness remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_ID,
        "state": "dashboard_deferred_route_harness_renderer_repair_prep_review_only",
        "prior_behavioral_route_count": prior_count,
        "repaired_behavioral_route_count": REPAIRED_BEHAVIORAL_ROUTE_COUNT,
        "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping_count,
        "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT,
        "isolated_harness_route_count": len(route_rows),
        "isolated_harness_pass_count": isolated_pass_count,
        "isolated_harness_timeout_seconds": ISOLATED_HARNESS_TIMEOUT_SECONDS,
        "route_rows": route_rows,
        "isolated_rows": isolated_rows,
        "repaired_direct_row": repaired_direct,
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "execution_approval_scope_repaired": bool(repaired_direct.get("ok") and repaired_isolated.get("ok")),
        "renderer_missing_helper_fallback_repaired": fallback_repair_present,
        "autonomy_route_isolated_timebox_available": bool(autonomy_isolated.get("ok")),
        "autonomy_route_standard_direct_coverage_deferred": True,
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


def dashboard_deferred_route_harness_renderer_repair_prep_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_behavioral_route_count={report.get('prior_behavioral_route_count')}",
        f"repaired_behavioral_route_count={report.get('repaired_behavioral_route_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"isolated_harness_route_count={report.get('isolated_harness_route_count')}",
        f"isolated_harness_pass_count={report.get('isolated_harness_pass_count')}",
        f"isolated_harness_timeout_seconds={report.get('isolated_harness_timeout_seconds')}",
        f"execution_approval_scope_repaired={report.get('execution_approval_scope_repaired')}",
        f"renderer_missing_helper_fallback_repaired={report.get('renderer_missing_helper_fallback_repaired')}",
        f"autonomy_route_isolated_timebox_available={report.get('autonomy_route_isolated_timebox_available')}",
        f"autonomy_route_standard_direct_coverage_deferred={report.get('autonomy_route_standard_direct_coverage_deferred')}",
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
        lines.append("\nIsolated harness rows:")
        for row in report.get("isolated_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} error={row.get('error')}")
        lines.append("\nDirect repaired row:")
        row = report.get("repaired_direct_row") or {}
        lines.append(f"- {row.get('route')} -> {row.get('renderer')}: ok={row.get('ok')} status={row.get('status')} elapsed_ms={row.get('elapsed_ms')} error={row.get('error')}")
    return "\n".join(lines)
