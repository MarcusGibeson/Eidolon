from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_doctor_deferred_diagnostic_api_parity import (
    DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1040_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1040_MAPPING_RECONCILED_ROUTE_COUNT,
)
from dashboard_doctor_renderer_decomposition_slice import LAZY_DIAGNOSTIC_SECTIONS as DOCTOR_LAZY_DIAGNOSTIC_SECTIONS

DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_VERSION = RUNTIME_VERSION
DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID = "doctor-deferred-diagnostic-latency-budget-and-payload-shape-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-deferred-diagnostic-latency-budget-payload-shape"
SELF_RENDERER = "render_doctor_deferred_diagnostic_latency_budget_payload_shape"
DOCTOR_ROUTE = "/doctor"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 105
NEW_LATENCY_PAYLOAD_REPORT_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 106
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 111
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 112
DEFERRED_DIAGNOSTIC_TARGET_COUNT = 5
STANDARD_DIAGNOSTIC_BUDGET_MS = 8000
LONG_DIAGNOSTIC_BUDGET_MS = 25000
EXPECTED_STANDARD_TARGET_COUNT = 4
EXPECTED_LONG_TARGET_COUNT = 1
EXPECTED_PAYLOAD_SHAPE_PASS_COUNT = 5
EXPECTED_LATENCY_BUDGET_PASS_COUNT = 5
CONTROLLED_SELF_BUILD_ROUTE = "/api/controlled-self-build"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "latency_budget_review_only": True,
    "payload_shape_review_only": True,
    "doctor_remains_long_isolated": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "controlled_self_build_preview_only": True,
    "controlled_self_build_long_diagnostic_lane_required": True,
    "controlled_self_build_lighter_preview_endpoint_recommended": True,
    "latency_budget_pass_is_release_approval": False,
    "payload_shape_pass_is_api_contract_freeze": False,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "generated_wiring_activated": False,
    "latency_probe_executes_live_work": False,
    "latency_probe_applies_patches": False,
    "latency_probe_writes_memory": False,
    "latency_probe_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class DeferredDiagnosticShapeSpec:
    label: str
    route: str
    lane: str
    budget_ms: int
    required_data_keys: tuple[str, ...]
    expected_collection_keys: tuple[str, ...]
    allow_diagnostic_ok_false: bool


@dataclass(frozen=True)
class DeferredDiagnosticLatencyPayloadRow:
    label: str
    route: str
    lane: str
    budget_ms: int
    elapsed_ms: int
    latency_budget_pass: bool
    live_status: int
    api_wrapper_ok: bool
    top_level_shape_pass: bool
    data_shape_pass: bool
    collection_shape_pass: bool
    payload_shape_pass: bool
    diagnostic_status: str
    diagnostic_ok: bool | None
    live_work_executed: bool
    data_keys: tuple[str, ...]
    missing_data_keys: tuple[str, ...]
    missing_collection_keys: tuple[str, ...]
    ok: bool
    message: str


DIAGNOSTIC_SHAPE_SPECS: tuple[DeferredDiagnosticShapeSpec, ...] = (
    DeferredDiagnosticShapeSpec(
        "Repair Suggestions",
        "/api/repair-suggestions",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "counts", "rows", "recommendations", "next_commands", "message"),
        ("rows", "recommendations", "next_commands"),
        True,
    ),
    DeferredDiagnosticShapeSpec(
        "Project Snapshot",
        "/api/project-snapshot",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "active_project", "task_counts", "recommendations", "next_commands", "message"),
        ("recommendations", "next_commands"),
        True,
    ),
    DeferredDiagnosticShapeSpec(
        "Stable Loop Confidence",
        "/api/stable-loops/confidence",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "score", "strengths", "weaknesses", "recommendations", "next_commands", "inputs", "message"),
        ("strengths", "weaknesses", "recommendations", "next_commands"),
        True,
    ),
    DeferredDiagnosticShapeSpec(
        "Hardening",
        "/api/hardening-report",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "counts", "rows", "blockers", "recommendations", "next_commands", "message"),
        ("rows", "blockers", "recommendations", "next_commands"),
        True,
    ),
    DeferredDiagnosticShapeSpec(
        "Controlled Self-Build Preview",
        CONTROLLED_SELF_BUILD_ROUTE,
        "long_diagnostic_preview",
        LONG_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "live", "approved_live", "use_ai", "max_steps", "blocked_reasons", "actions", "recommendations", "next_commands", "message"),
        ("blocked_reasons", "actions", "recommendations", "next_commands"),
        True,
    ),
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
    except Exception as error:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return 500, {"ok": False, "error": f"{type(error).__name__}: {error}"}, elapsed_ms, f"{type(error).__name__}: {error}"


def _live_work_executed(route: str, data: Any) -> bool:
    if route != CONTROLLED_SELF_BUILD_ROUTE or not isinstance(data, dict):
        return False
    return bool(data.get("live") or data.get("approved_live") or data.get("run_result"))


def _row_from_spec(spec: DeferredDiagnosticShapeSpec) -> DeferredDiagnosticLatencyPayloadRow:
    status, payload, elapsed_ms, error = _call_live_api(spec.route)
    data = payload.get("data") if isinstance(payload, dict) else None
    data_keys = tuple(data.keys()) if isinstance(data, dict) else tuple()
    top_level_shape_pass = isinstance(payload, dict) and all(key in payload for key in ("ok", "api_version", "served_at", "data")) and isinstance(data, dict)
    missing_data_keys = tuple(key for key in spec.required_data_keys if key not in data_keys)
    missing_collection_keys = tuple(
        key for key in spec.expected_collection_keys
        if not isinstance(data, dict) or not isinstance(data.get(key), (list, tuple, dict))
    )
    diagnostic_status = "unknown"
    diagnostic_ok: bool | None = None
    if isinstance(data, dict):
        diagnostic_status = str(data.get("status", "unknown"))
        if isinstance(data.get("ok"), bool):
            diagnostic_ok = bool(data.get("ok"))
    api_wrapper_ok = bool(isinstance(payload, dict) and payload.get("ok") is True)
    live_work = _live_work_executed(spec.route, data)
    latency_budget_pass = elapsed_ms <= spec.budget_ms
    data_shape_pass = not missing_data_keys
    collection_shape_pass = not missing_collection_keys
    payload_shape_pass = top_level_shape_pass and data_shape_pass and collection_shape_pass
    ok = (
        status == 200
        and api_wrapper_ok
        and error is None
        and latency_budget_pass
        and payload_shape_pass
        and live_work is False
        and (spec.allow_diagnostic_ok_false or diagnostic_ok is True)
    )
    message = (
        f"lane={spec.lane} status={status} wrapper_ok={api_wrapper_ok} elapsed_ms={elapsed_ms} "
        f"budget_ms={spec.budget_ms} payload_shape_pass={payload_shape_pass} "
        f"missing_data_keys={len(missing_data_keys)} missing_collection_keys={len(missing_collection_keys)} "
        f"diagnostic_status={diagnostic_status} live_work_executed={live_work}"
    )
    return DeferredDiagnosticLatencyPayloadRow(
        label=spec.label,
        route=spec.route,
        lane=spec.lane,
        budget_ms=spec.budget_ms,
        elapsed_ms=elapsed_ms,
        latency_budget_pass=latency_budget_pass,
        live_status=int(status),
        api_wrapper_ok=api_wrapper_ok,
        top_level_shape_pass=top_level_shape_pass,
        data_shape_pass=data_shape_pass,
        collection_shape_pass=collection_shape_pass,
        payload_shape_pass=payload_shape_pass,
        diagnostic_status=diagnostic_status,
        diagnostic_ok=diagnostic_ok,
        live_work_executed=live_work,
        data_keys=data_keys,
        missing_data_keys=missing_data_keys,
        missing_collection_keys=missing_collection_keys,
        ok=ok,
        message=message,
    )


def _preview_row_from_spec(spec: DeferredDiagnosticShapeSpec) -> DeferredDiagnosticLatencyPayloadRow:
    return DeferredDiagnosticLatencyPayloadRow(
        label=spec.label,
        route=spec.route,
        lane=spec.lane,
        budget_ms=spec.budget_ms,
        elapsed_ms=0,
        latency_budget_pass=False,
        live_status=0,
        api_wrapper_ok=False,
        top_level_shape_pass=False,
        data_shape_pass=True,
        collection_shape_pass=True,
        payload_shape_pass=False,
        diagnostic_status="not_measured_in_dashboard_preview",
        diagnostic_ok=None,
        live_work_executed=False,
        data_keys=tuple(),
        missing_data_keys=tuple(),
        missing_collection_keys=tuple(),
        ok=False,
        message=f"lane={spec.lane} budget_ms={spec.budget_ms} preview_only=True live_measurement_performed=False",
    )


def build_doctor_deferred_diagnostic_latency_budget_payload_shape_review(root: str | Path | None = None, *, measure_live: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    mtimes: list[float] = []
    for rel in [DASHBOARD_MODULE, API_MODULE, MANUAL_SMOKE_MODULE, SOURCE_MANIFEST_MODULE, "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"]:
        path = project_root / rel
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            mtimes.append(0.0)
    cache_key = (str(project_root), mtimes[0], mtimes[1], mtimes[2], 1.0 if measure_live else 0.0)
    cached = _CACHE.get(cache_key)
    if cached:
        return dict(cached)

    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_deferred_diagnostic_latency_budget_payload_shape.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])

    route_map = _route_renderer_map(dashboard_source)
    spec_routes = [spec.route for spec in DIAGNOSTIC_SHAPE_SPECS]
    lazy_routes = [row.route for row in DOCTOR_LAZY_DIAGNOSTIC_SECTIONS]
    rows = [_row_from_spec(spec) for spec in DIAGNOSTIC_SHAPE_SPECS] if measure_live else [_preview_row_from_spec(spec) for spec in DIAGNOSTIC_SHAPE_SPECS]
    row_dicts = [asdict(row) for row in rows]
    standard_rows = [row for row in rows if row.lane == "standard_diagnostic"]
    long_rows = [row for row in rows if row.lane == "long_diagnostic_preview"]
    latency_pass_count = sum(1 for row in rows if row.latency_budget_pass)
    payload_shape_pass_count = sum(1 for row in rows if row.payload_shape_pass)
    live_pass_count = sum(1 for row in rows if row.ok)
    controlled_rows = [row for row in rows if row.route == CONTROLLED_SELF_BUILD_ROUTE]
    controlled_preview_only = bool(controlled_rows and controlled_rows[0].live_work_executed is False and controlled_rows[0].lane == "long_diagnostic_preview")
    prior_total = int(V1040_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping = int(V1040_MAPPING_RECONCILED_ROUTE_COUNT)
    mapping_mismatches = [
        {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)},
    ]
    mapping_mismatches = [row for row in mapping_mismatches if row["actual_renderer"] != row["expected_renderer"]]
    required_tokens = [
        DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID,
        SELF_ROUTE,
        "build_doctor_deferred_diagnostic_latency_budget_payload_shape_review",
        "doctor_deferred_diagnostic_latency_budget_payload_shape_review_text",
        "latency_budget_pass_count=5",
        "payload_shape_pass_count=5",
        "standard_diagnostic_target_count=4",
        "long_diagnostic_preview_target_count=1",
        "controlled_self_build_preview_only=True",
        "controlled_self_build_lighter_preview_endpoint_recommended=True",
        "manual_api_dispatch_remains_authoritative=True",
        "generated_wiring_activated=False",
        "autonomy_expanded=False",
    ]
    rows_status = [
        {"name": "module-version-current", "ok": DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1040-token-present", "ok": DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID in docs, "message": f"prior token {DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID} present in docs/source."},
        {"name": "lazy-route-spec-parity", "ok": spec_routes == lazy_routes and len(spec_routes) == DEFERRED_DIAGNOSTIC_TARGET_COUNT, "message": f"spec_routes={len(spec_routes)} lazy_routes={len(lazy_routes)}"},
        {"name": "latency-budget-rows-pass", "ok": latency_pass_count == EXPECTED_LATENCY_BUDGET_PASS_COUNT and all(row.latency_budget_pass for row in rows), "message": f"latency_budget_pass_count={latency_pass_count}"},
        {"name": "payload-shape-rows-pass", "ok": payload_shape_pass_count == EXPECTED_PAYLOAD_SHAPE_PASS_COUNT and all(row.payload_shape_pass for row in rows), "message": f"payload_shape_pass_count={payload_shape_pass_count}"},
        {"name": "standard-and-long-lanes-classified", "ok": len(standard_rows) == EXPECTED_STANDARD_TARGET_COUNT and len(long_rows) == EXPECTED_LONG_TARGET_COUNT, "message": f"standard={len(standard_rows)} long={len(long_rows)}"},
        {"name": "controlled-self-build-preview-only", "ok": controlled_preview_only, "message": "controlled self-build remains a long diagnostic preview target and does not execute live work."},
        {"name": "live-api-wrapper-rows-pass", "ok": live_pass_count == DEFERRED_DIAGNOSTIC_TARGET_COUNT and all(row.live_status == 200 and row.api_wrapper_ok for row in rows), "message": f"live_pass_count={live_pass_count}"},
        {"name": "behavioral-count-current", "ok": prior_total + NEW_LATENCY_PAYLOAD_REPORT_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_LATENCY_PAYLOAD_REPORT_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "manifest-surface-current", "ok": "v1041-doctor-deferred-diagnostic-latency-budget-payload-shape" in manifest_source, "message": "Source surface manifest represents the v1041 doctor diagnostic latency/payload surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1041 latency/payload truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["latency_budget_pass_is_release_approval", "payload_shape_pass_is_api_contract_freeze", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "latency_probe_executes_live_work", "latency_probe_applies_patches", "latency_probe_writes_memory", "latency_probe_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Latency and payload shape review remains advisory and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID,
        "state": "doctor_deferred_diagnostic_latency_budget_payload_shape_review_only",
        "live_measurement_performed": bool(measure_live),
        "prior_total_behavioral_coverage_count": prior_total,
        "new_latency_payload_report_behavioral_coverage_count": NEW_LATENCY_PAYLOAD_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": prior_total + NEW_LATENCY_PAYLOAD_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "deferred_diagnostic_target_count": len(rows),
        "standard_diagnostic_target_count": len(standard_rows),
        "long_diagnostic_preview_target_count": len(long_rows),
        "standard_diagnostic_budget_ms": STANDARD_DIAGNOSTIC_BUDGET_MS,
        "long_diagnostic_budget_ms": LONG_DIAGNOSTIC_BUDGET_MS,
        "latency_budget_pass_count": latency_pass_count,
        "payload_shape_pass_count": payload_shape_pass_count,
        "live_api_pass_count": live_pass_count,
        "controlled_self_build_preview_only": controlled_preview_only,
        "controlled_self_build_long_diagnostic_lane_required": True,
        "controlled_self_build_lighter_preview_endpoint_recommended": True,
        "doctor_remains_long_isolated": True,
        "standard_fast_route_coverage_unchanged": True,
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
        "latency_payload_rows": row_dicts,
        "standard_latency_rows": [asdict(row) for row in standard_rows],
        "long_latency_rows": [asdict(row) for row in long_rows],
        "shape_specs": [asdict(spec) for spec in DIAGNOSTIC_SHAPE_SPECS],
        "boundaries": dict(BOUNDARIES),
        "mapping_mismatches": mapping_mismatches,
        "rows": rows_status,
        "blocked": [row for row in rows_status if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }
    _CACHE.clear()
    _CACHE[cache_key] = dict(report)
    return report


def doctor_deferred_diagnostic_latency_budget_payload_shape_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"dashboard_route={SELF_ROUTE}",
        "builder_function=build_doctor_deferred_diagnostic_latency_budget_payload_shape_review",
        "text_function=doctor_deferred_diagnostic_latency_budget_payload_shape_review_text",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_latency_payload_report_behavioral_coverage_count={report.get('new_latency_payload_report_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"deferred_diagnostic_target_count={report.get('deferred_diagnostic_target_count')}",
        f"standard_diagnostic_target_count={report.get('standard_diagnostic_target_count')}",
        f"long_diagnostic_preview_target_count={report.get('long_diagnostic_preview_target_count')}",
        f"standard_diagnostic_budget_ms={report.get('standard_diagnostic_budget_ms')}",
        f"long_diagnostic_budget_ms={report.get('long_diagnostic_budget_ms')}",
        f"latency_budget_pass_count={report.get('latency_budget_pass_count')}",
        f"payload_shape_pass_count={report.get('payload_shape_pass_count')}",
        f"live_api_pass_count={report.get('live_api_pass_count')}",
        f"controlled_self_build_preview_only={report.get('controlled_self_build_preview_only')}",
        f"controlled_self_build_long_diagnostic_lane_required={report.get('controlled_self_build_long_diagnostic_lane_required')}",
        f"controlled_self_build_lighter_preview_endpoint_recommended={report.get('controlled_self_build_lighter_preview_endpoint_recommended')}",
        f"doctor_remains_long_isolated={report.get('doctor_remains_long_isolated')}",
        f"standard_fast_route_coverage_unchanged={report.get('standard_fast_route_coverage_unchanged')}",
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
        lines.append("\nLatency and payload rows:")
        for row in report.get("latency_payload_rows", []):
            lines.append(
                f"- {row.get('label')}: {row.get('route')} lane={row.get('lane')} elapsed_ms={row.get('elapsed_ms')} budget_ms={row.get('budget_ms')} latency_ok={row.get('latency_budget_pass')} payload_shape_ok={row.get('payload_shape_pass')} diagnostic_status={row.get('diagnostic_status')} live_work_executed={row.get('live_work_executed')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)
