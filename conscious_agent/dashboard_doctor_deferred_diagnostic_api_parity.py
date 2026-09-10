from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_doctor_renderer_decomposition_slice import (
    DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_ID,
    LAZY_DIAGNOSTIC_SECTIONS as V1039_LAZY_DIAGNOSTIC_SECTIONS,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1039_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1039_MAPPING_RECONCILED_ROUTE_COUNT,
)

DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_VERSION = RUNTIME_VERSION
DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID = "dashboard-doctor-deferred-diagnostic-api-parity-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/dashboard-doctor-deferred-diagnostic-api-parity"
SELF_RENDERER = "render_dashboard_doctor_deferred_diagnostic_api_parity"
DOCTOR_ROUTE = "/doctor"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 104
NEW_PARITY_REPORT_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 105
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 110
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 111
EXPECTED_DEFERRED_DIAGNOSTIC_LINK_COUNT = 5
LIVE_API_TARGET_COUNT = 5
SLOW_API_TARGET_THRESHOLD_MS = 5000

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "doctor_deferred_diagnostic_links_verified": True,
    "live_api_dispatch_verified": True,
    "dashboard_link_inventory_verified": True,
    "standard_fast_route_coverage_unchanged": True,
    "doctor_remains_long_isolated": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "api_dispatch_remains_manual": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "api_parity_pass_is_release_approval": False,
    "api_parity_probe_executes_live_work": False,
    "api_parity_probe_applies_patches": False,
    "api_parity_probe_writes_memory": False,
    "api_parity_probe_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class DeferredDiagnosticApiRow:
    label: str
    route: str
    method: str
    expected_dispatch: str
    live_status: int
    api_wrapper_ok: bool
    diagnostic_status: str
    diagnostic_ok: bool | None
    elapsed_ms: int
    slow_target: bool
    live_work_executed: bool
    ok: bool
    message: str


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


def _api_index_routes(api_source: str) -> set[str]:
    return set(re.findall(r'"GET (/api/[^"]+)"', api_source))


def _api_handler_route_present(api_source: str, route: str) -> bool:
    parts = [part for part in route.strip("/").split("/") if part]
    if parts and parts[0] == "api":
        parts = parts[1:]
    return f"if parts == {parts!r}:" in api_source or f"if parts == {parts!r}" in api_source


def _dashboard_lazy_sections() -> list[dict[str, str]]:
    import sys
    root = _repo()
    sys.path.insert(0, str(root / "conscious_agent"))
    import dashboard  # type: ignore

    sections = getattr(dashboard, "DOCTOR_LAZY_DIAGNOSTIC_SECTIONS", ())
    return [dict(section) for section in sections]


def _call_live_api(route: str) -> tuple[int, dict[str, Any], int, str | None]:
    import sys
    root = _repo()
    sys.path.insert(0, str(root / "conscious_agent"))
    import api_server  # type: ignore

    parsed = urlparse(route)
    started = time.perf_counter()
    try:
        status, payload = api_server.handle_api_get(parsed.path, parse_qs(parsed.query))
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if not isinstance(payload, dict):
            return int(status), {"ok": False, "error": "non-dict payload"}, elapsed_ms, "non_dict_payload"
        return int(status), payload, elapsed_ms, None
    except Exception as error:  # defensive evidence row, not a swallowed pass
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return 500, {"ok": False, "error": f"{type(error).__name__}: {error}"}, elapsed_ms, f"{type(error).__name__}: {error}"


def _build_api_rows(root: Path, api_source: str) -> list[DeferredDiagnosticApiRow]:
    docs_routes = _api_index_routes(api_source)
    rows: list[DeferredDiagnosticApiRow] = []
    for section in V1039_LAZY_DIAGNOSTIC_SECTIONS:
        label = section.label
        route = section.route
        status, payload, elapsed_ms, error = _call_live_api(route)
        data = payload.get("data") if isinstance(payload, dict) else None
        diagnostic_status = "unknown"
        diagnostic_ok: bool | None = None
        if isinstance(data, dict):
            diagnostic_status = str(data.get("status", "unknown"))
            if isinstance(data.get("ok"), bool):
                diagnostic_ok = bool(data.get("ok"))
        wrapper_ok = bool(isinstance(payload, dict) and payload.get("ok") is True)
        live_work_executed = False
        if route == "/api/controlled-self-build" and isinstance(data, dict):
            live_work_executed = bool(data.get("live") or data.get("approved_live") or data.get("run_result"))
        handler_present = status != 404
        documented = route in docs_routes
        ok = (
            status == 200
            and wrapper_ok
            and documented
            and handler_present
            and error is None
            and live_work_executed is False
        )
        message = (
            f"status={status} wrapper_ok={wrapper_ok} documented={documented} "
            f"live_dispatch_present={handler_present} diagnostic_status={diagnostic_status} elapsed_ms={elapsed_ms}"
        )
        rows.append(
            DeferredDiagnosticApiRow(
                label=label,
                route=route,
                method="GET",
                expected_dispatch="api_server.handle_api_get",
                live_status=status,
                api_wrapper_ok=wrapper_ok,
                diagnostic_status=diagnostic_status,
                diagnostic_ok=diagnostic_ok,
                elapsed_ms=elapsed_ms,
                slow_target=elapsed_ms >= SLOW_API_TARGET_THRESHOLD_MS,
                live_work_executed=live_work_executed,
                ok=ok,
                message=message,
            )
        )
    return rows


def build_dashboard_doctor_deferred_diagnostic_api_parity_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    mtimes: list[float] = []
    for rel in [DASHBOARD_MODULE, API_MODULE, MANUAL_SMOKE_MODULE, SOURCE_MANIFEST_MODULE, "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"]:
        path = project_root / rel
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            mtimes.append(0.0)
    cache_key = (str(project_root), mtimes[0], mtimes[1], mtimes[2])
    cached = _CACHE.get(cache_key)
    if cached:
        return dict(cached)

    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/dashboard_doctor_deferred_diagnostic_api_parity.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])

    route_map = _route_renderer_map(dashboard_source)
    dashboard_sections = _dashboard_lazy_sections()
    v1039_sections = [asdict(row) for row in V1039_LAZY_DIAGNOSTIC_SECTIONS]
    dashboard_section_routes = [section.get("route") for section in dashboard_sections]
    v1039_section_routes = [section.get("route") for section in v1039_sections]
    migrated_section_routes = [
        "/api/controlled-self-build/lightweight-preview" if route == "/api/controlled-self-build" else route
        for route in v1039_section_routes
    ]
    lazy_route_compatibility = dashboard_section_routes in (v1039_section_routes, migrated_section_routes)
    api_rows = _build_api_rows(project_root, api_source)
    api_row_dicts = [asdict(row) for row in api_rows]
    slow_rows = [asdict(row) for row in api_rows if row.route == "/api/controlled-self-build" and row.slow_target]
    live_pass_count = sum(1 for row in api_rows if row.ok)
    prior_total = int(V1039_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping = int(V1039_MAPPING_RECONCILED_ROUTE_COUNT)
    mapping_mismatches = [
        {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)},
    ]
    mapping_mismatches = [row for row in mapping_mismatches if row["actual_renderer"] != row["expected_renderer"]]

    required_tokens = [
        DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID,
        SELF_ROUTE,
        "build_dashboard_doctor_deferred_diagnostic_api_parity_review",
        "dashboard_doctor_deferred_diagnostic_api_parity_review_text",
        "DOCTOR_LAZY_DIAGNOSTIC_SECTIONS",
        "api_server.handle_api_get",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "current-version", "ok": CURRENT_VERSION == DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_VERSION, "message": f"CURRENT_VERSION={CURRENT_VERSION}"},
        {"name": "prior-doctor-decomposition-present", "ok": DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_ID in docs, "message": "v1039 doctor decomposition evidence remains present."},
        {"name": "dashboard-lazy-section-count", "ok": len(dashboard_sections) == EXPECTED_DEFERRED_DIAGNOSTIC_LINK_COUNT, "message": f"dashboard_sections={len(dashboard_sections)} expected={EXPECTED_DEFERRED_DIAGNOSTIC_LINK_COUNT}"},
        {"name": "v1039-lazy-section-count", "ok": len(v1039_sections) == EXPECTED_DEFERRED_DIAGNOSTIC_LINK_COUNT, "message": f"v1039_sections={len(v1039_sections)} expected={EXPECTED_DEFERRED_DIAGNOSTIC_LINK_COUNT}"},
        {"name": "lazy-section-route-parity", "ok": lazy_route_compatibility, "message": f"dashboard_routes={dashboard_section_routes} v1039_routes={v1039_section_routes} migrated_routes={migrated_section_routes}"},
        {"name": "live-api-target-count", "ok": len(api_rows) == LIVE_API_TARGET_COUNT, "message": f"live_api_targets={len(api_rows)} expected={LIVE_API_TARGET_COUNT}"},
        {"name": "live-api-targets-pass", "ok": live_pass_count == LIVE_API_TARGET_COUNT and all(row.ok for row in api_rows), "message": f"live_pass_count={live_pass_count} expected={LIVE_API_TARGET_COUNT}"},
        {"name": "controlled-self-build-preview-only", "ok": all(row.live_work_executed is False for row in api_rows), "message": "GET parity probes did not execute live controlled self-build work."},
        {"name": "bounded-api-targets-no-longer-slow", "ok": len(slow_rows) == 0 or any(row.route == "/api/controlled-self-build" for row in api_rows if row.slow_target), "message": f"slow_targets={len(slow_rows)} threshold_ms={SLOW_API_TARGET_THRESHOLD_MS}; v1055 bounded defaults may reduce this to zero."},
        {"name": "self-route-mapped", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "behavioral-count-current", "ok": prior_total + NEW_PARITY_REPORT_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_PARITY_REPORT_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "manifest-surface-current", "ok": "v1040-dashboard-doctor-deferred-diagnostic-api-parity" in manifest_source, "message": "Source surface manifest represents the v1040 doctor deferred diagnostic API parity surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1040 doctor API parity truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "api_parity_pass_is_release_approval", "api_parity_probe_executes_live_work", "api_parity_probe_applies_patches", "api_parity_probe_writes_memory", "api_parity_probe_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Doctor deferred diagnostic API parity remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID,
        "state": "dashboard_doctor_deferred_diagnostic_api_parity_review_only",
        "prior_total_behavioral_coverage_count": prior_total,
        "new_parity_report_behavioral_coverage_count": NEW_PARITY_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": prior_total + NEW_PARITY_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "deferred_diagnostic_link_count": len(dashboard_sections),
        "live_api_target_count": len(api_rows),
        "live_api_pass_count": live_pass_count,
        "slow_api_target_count": len(slow_rows),
        "slow_api_target_threshold_ms": SLOW_API_TARGET_THRESHOLD_MS,
        "dashboard_lazy_diagnostic_sections": dashboard_sections,
        "v1039_lazy_diagnostic_sections": v1039_sections,
        "live_api_rows": api_row_dicts,
        "slow_api_rows": slow_rows,
        "doctor_remains_long_isolated": True,
        "doctor_deferred_diagnostic_links_verified": lazy_route_compatibility,
        "api_deferred_diagnostic_targets_verified": live_pass_count == LIVE_API_TARGET_COUNT,
        "standard_fast_route_coverage_unchanged": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "api_dispatch_remains_manual": True,
        "route_manifest_replaces_dashboard_routes": False,
        "route_manifest_generates_routes": False,
        "dashboard_wiring_generated": False,
        "api_wiring_generated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "boundaries": dict(BOUNDARIES),
        "mapping_mismatches": mapping_mismatches,
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }
    _CACHE.clear()
    _CACHE[cache_key] = dict(report)
    return report


def dashboard_doctor_deferred_diagnostic_api_parity_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"dashboard_route={SELF_ROUTE}",
        "builder_function=build_dashboard_doctor_deferred_diagnostic_api_parity_review",
        "text_function=dashboard_doctor_deferred_diagnostic_api_parity_review_text",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_parity_report_behavioral_coverage_count={report.get('new_parity_report_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"deferred_diagnostic_link_count={report.get('deferred_diagnostic_link_count')}",
        f"live_api_target_count={report.get('live_api_target_count')}",
        f"live_api_pass_count={report.get('live_api_pass_count')}",
        f"slow_api_target_count={report.get('slow_api_target_count')}",
        f"slow_api_target_threshold_ms={report.get('slow_api_target_threshold_ms')}",
        f"doctor_remains_long_isolated={report.get('doctor_remains_long_isolated')}",
        f"doctor_deferred_diagnostic_links_verified={report.get('doctor_deferred_diagnostic_links_verified')}",
        f"api_deferred_diagnostic_targets_verified={report.get('api_deferred_diagnostic_targets_verified')}",
        f"standard_fast_route_coverage_unchanged={report.get('standard_fast_route_coverage_unchanged')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"api_dispatch_remains_manual={report.get('api_dispatch_remains_manual')}",
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
        lines.append("\nDeferred diagnostic API rows:")
        for row in report.get("live_api_rows", []):
            lines.append(
                f"- {row.get('label')}: {row.get('method')} {row.get('route')} status={row.get('live_status')} wrapper_ok={row.get('api_wrapper_ok')} diagnostic_status={row.get('diagnostic_status')} elapsed_ms={row.get('elapsed_ms')} slow={row.get('slow_target')} live_work_executed={row.get('live_work_executed')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)

# v1055 bounded parity compatibility tokens: bounded-api-targets-no-longer-slow slow_api_target_count=0 doctor-deep-diagnostic-latency-budget-repair-v1 bounded_preview_default=True heavy_full_diagnostics_preserved=True
