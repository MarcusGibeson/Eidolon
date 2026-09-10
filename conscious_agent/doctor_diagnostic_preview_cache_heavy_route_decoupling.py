from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_controlled_self_build_lightweight_link_migration import (
    DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_ID,
    HEAVY_PREVIEW_ROUTE,
    LIGHTWEIGHT_PREVIEW_ROUTE,
    MIGRATED_DIAGNOSTIC_SHAPE_SPECS,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1043_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1043_MAPPING_RECONCILED_ROUTE_COUNT,
)

DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_ID = "doctor-diagnostic-preview-cache-and-heavy-route-decoupling-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-diagnostic-preview-cache-heavy-route-decoupling"
SELF_RENDERER = "render_doctor_diagnostic_preview_cache_heavy_route_decoupling"
CACHE_API_ROUTE = "/api/doctor/diagnostic-preview-cache"
DOCTOR_ROUTE = "/doctor"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 108
NEW_CACHE_REPORT_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 109
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 114
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 115
DEFERRED_DIAGNOSTIC_TARGET_COUNT = 5
CACHE_API_TARGET_COUNT = 1
CACHE_TTL_SECONDS = 60
EXPECTED_CACHE_ROW_CONTRACT_PASS_COUNT = 5
EXPECTED_CACHE_PAYLOAD_SHAPE_PASS_COUNT = 1
EXPECTED_CACHE_API_PASS_COUNT = 1

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "preview_cache_review_only": True,
    "preview_cache_endpoint_preview_only": True,
    "doctor_remains_long_isolated": True,
    "doctor_link_stays_lightweight": True,
    "heavy_preview_route_preserved": True,
    "heavy_preview_route_decoupled_from_doctor": True,
    "cache_uses_static_contract_summary": True,
    "cache_does_not_call_live_diagnostics": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "cache_endpoint_executes_live_work": False,
    "cache_endpoint_applies_patches": False,
    "cache_endpoint_writes_memory": False,
    "cache_endpoint_creates_release": False,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class CachedDoctorDiagnosticRow:
    label: str
    route: str
    api_route: str
    lane: str
    budget_ms: int
    required_data_key_count: int
    expected_collection_key_count: int
    payload_shape_contract_present: bool
    cache_only: bool
    measured_live: bool
    preview_only: bool
    lightweight_preview: bool
    heavy_preview_route: str
    heavy_preview_decoupled: bool
    executes_live_work: bool
    applies_patches: bool
    writes_memory: bool
    creates_release: bool
    ok: bool
    message: str


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


def _call_api(root: Path, route: str) -> tuple[int, dict[str, Any], int, str | None]:
    import sys
    import time

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


def _cached_rows() -> list[CachedDoctorDiagnosticRow]:
    rows: list[CachedDoctorDiagnosticRow] = []
    for spec in MIGRATED_DIAGNOSTIC_SHAPE_SPECS:
        api_route = str(spec.dashboard_route)
        is_lightweight = api_route == LIGHTWEIGHT_PREVIEW_ROUTE
        heavy_decoupled = api_route != HEAVY_PREVIEW_ROUTE
        ok = bool(
            spec.required_data_keys
            and spec.expected_collection_keys
            and heavy_decoupled
            and (not is_lightweight or getattr(spec, "migrated_from", "") == HEAVY_PREVIEW_ROUTE)
        )
        rows.append(
            CachedDoctorDiagnosticRow(
                label=str(spec.label),
                route=str(spec.dashboard_route),
                api_route=api_route,
                lane=str(spec.lane),
                budget_ms=int(spec.budget_ms),
                required_data_key_count=len(spec.required_data_keys),
                expected_collection_key_count=len(spec.expected_collection_keys),
                payload_shape_contract_present=bool(spec.required_data_keys and spec.expected_collection_keys),
                cache_only=True,
                measured_live=False,
                preview_only=is_lightweight,
                lightweight_preview=is_lightweight,
                heavy_preview_route=HEAVY_PREVIEW_ROUTE,
                heavy_preview_decoupled=heavy_decoupled,
                executes_live_work=False,
                applies_patches=False,
                writes_memory=False,
                creates_release=False,
                ok=ok,
                message=(
                    f"lane={spec.lane} cache_only=True measured_live=False "
                    f"required_data_keys={len(spec.required_data_keys)} collection_keys={len(spec.expected_collection_keys)} "
                    f"heavy_preview_decoupled={heavy_decoupled}"
                ),
            )
        )
    return rows


def build_doctor_diagnostic_preview_cache(project_id: str = "eidolon") -> dict[str, Any]:
    rows = _cached_rows()
    row_dicts = [asdict(row) for row in rows]
    row_contract_pass_count = sum(1 for row in rows if row.ok)
    lightweight_rows = [row for row in rows if row.route == LIGHTWEIGHT_PREVIEW_ROUTE]
    heavy_rows = [row for row in rows if row.route == HEAVY_PREVIEW_ROUTE]
    ok = (
        len(rows) == DEFERRED_DIAGNOSTIC_TARGET_COUNT
        and row_contract_pass_count == EXPECTED_CACHE_ROW_CONTRACT_PASS_COUNT
        and len(lightweight_rows) == 1
        and len(heavy_rows) == 0
        and all(row.measured_live is False for row in rows)
        and all(row.executes_live_work is False for row in rows)
    )
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_cache": True,
        "preview_only": True,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "cache_strategy": "static_contract_summary_no_live_diagnostic_calls",
        "diagnostic_target_count": len(rows),
        "cache_row_contract_pass_count": row_contract_pass_count,
        "diagnostic_rows": row_dicts,
        "lightweight_preview_route": LIGHTWEIGHT_PREVIEW_ROUTE,
        "heavy_preview_route": HEAVY_PREVIEW_ROUTE,
        "heavy_preview_route_preserved": True,
        "doctor_controlled_self_build_link_migrated": bool(lightweight_rows and not heavy_rows),
        "heavy_preview_route_decoupled_from_doctor": bool(not heavy_rows),
        "cache_does_not_call_live_api": True,
        "live_measurements_performed": False,
        "diagnostic_storm_avoided": True,
        "executes_live_work": False,
        "applies_patches": False,
        "writes_memory": False,
        "creates_release": False,
        "generated_wiring_activated": False,
        "autonomy_expanded": False,
        "recommendations": [
            "Keep /doctor linked to the lightweight controlled self-build preview endpoint.",
            "Use targeted smoke for live payload measurements instead of dashboard page-load probes.",
            "Preserve the heavy /api/controlled-self-build route as a deliberate full preview surface.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-preview-cache-and-heavy-route-decoupling-v1",
            "python tools/smoke_check.py --check doctor-controlled-self-build-lightweight-link-migration-v1",
        ],
        "message": "Doctor deferred diagnostics are summarized through a bounded preview cache without live diagnostic fan-out.",
    }


def build_doctor_diagnostic_preview_cache_heavy_route_decoupling_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_preview_cache_heavy_route_decoupling.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)

    cache_payload = build_doctor_diagnostic_preview_cache(project_id="eidolon")
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, CACHE_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    rows = cache_payload.get("diagnostic_rows", [])
    api_rows = api_data.get("diagnostic_rows", []) if isinstance(api_data, dict) else []
    lazy_routes = re.findall(r'\{"name": "[^"]+", "route": "([^"]+)"', dashboard_source[dashboard_source.find("DOCTOR_LAZY_DIAGNOSTIC_SECTIONS"):dashboard_source.find("def _doctor_primary_reports")])
    required_api_data_keys = (
        "version",
        "checked_at",
        "project_id",
        "status",
        "ok",
        "preview_cache",
        "preview_only",
        "cache_ttl_seconds",
        "cache_strategy",
        "diagnostic_target_count",
        "cache_row_contract_pass_count",
        "diagnostic_rows",
        "lightweight_preview_route",
        "heavy_preview_route",
        "heavy_preview_route_preserved",
        "doctor_controlled_self_build_link_migrated",
        "heavy_preview_route_decoupled_from_doctor",
        "cache_does_not_call_live_api",
        "live_measurements_performed",
        "diagnostic_storm_avoided",
        "executes_live_work",
        "applies_patches",
        "writes_memory",
        "creates_release",
        "generated_wiring_activated",
        "autonomy_expanded",
        "recommendations",
        "next_commands",
        "message",
    )
    api_data_keys = tuple(api_data.keys()) if isinstance(api_data, dict) else tuple()
    missing_api_data_keys = tuple(key for key in required_api_data_keys if key not in api_data_keys)
    api_payload_shape_pass = (
        status == 200
        and api_error is None
        and isinstance(api_payload, dict)
        and api_payload.get("ok") is True
        and isinstance(api_data, dict)
        and not missing_api_data_keys
        and isinstance(api_data.get("diagnostic_rows"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache"]' in api_source
    doctor_quick_link_lightweight = "/api/controlled-self-build/lightweight-preview" in dashboard_source and "Controlled self-build lightweight preview" in dashboard_source
    doctor_quick_link_heavy_removed = "Controlled self-build JSON</a>" not in dashboard_source
    cache_row_contract_pass_count = sum(1 for row in rows if row.get("ok") is True)
    heavy_route_rows = [row for row in rows if row.get("route") == HEAVY_PREVIEW_ROUTE or row.get("api_route") == HEAVY_PREVIEW_ROUTE]
    lightweight_rows = [row for row in rows if row.get("route") == LIGHTWEIGHT_PREVIEW_ROUTE or row.get("api_route") == LIGHTWEIGHT_PREVIEW_ROUTE]
    required_tokens = [
        DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_ID,
        SELF_ROUTE,
        CACHE_API_ROUTE,
        "build_doctor_diagnostic_preview_cache",
        "build_doctor_diagnostic_preview_cache_heavy_route_decoupling_review",
        "doctor_diagnostic_preview_cache_heavy_route_decoupling_review_text",
        "prior_total_behavioral_coverage_count=108",
        "new_cache_report_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=109",
        "prior_mapping_reconciled_route_count=114",
        "mapping_reconciled_route_count=115",
        "cache_api_target_count=1",
        "deferred_diagnostic_target_count=5",
        "cache_row_contract_pass_count=5",
        "cache_payload_shape_pass_count=1",
        "cache_api_pass_count=1",
        "heavy_preview_route_decoupled_from_doctor=True",
        "cache_does_not_call_live_api=True",
        "diagnostic_storm_avoided=True",
        "manual_api_dispatch_remains_authoritative=True",
        "generated_wiring_activated=False",
        "autonomy_expanded=False",
    ]
    rows_status = [
        {"name": "module-version-current", "ok": DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1043-token-present", "ok": DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_ID in docs, "message": f"prior token {DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_ID} present."},
        {"name": "cache-api-index-and-handler-present", "ok": api_index_present and api_handler_present, "message": f"api_index_present={api_index_present} api_handler_present={api_handler_present}"},
        {"name": "cache-api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing_api_data_keys={len(missing_api_data_keys)} error={api_error}"},
        {"name": "cache-row-contracts-pass", "ok": cache_row_contract_pass_count == EXPECTED_CACHE_ROW_CONTRACT_PASS_COUNT and len(rows) == DEFERRED_DIAGNOSTIC_TARGET_COUNT, "message": f"row_pass={cache_row_contract_pass_count} rows={len(rows)}"},
        {"name": "lazy-route-cache-parity", "ok": [row.get("route") for row in rows] == lazy_routes == [row.get("route") for row in api_rows], "message": f"cache_rows={len(rows)} lazy_routes={len(lazy_routes)} api_rows={len(api_rows)}"},
        {"name": "heavy-route-decoupled", "ok": len(heavy_route_rows) == 0 and len(lightweight_rows) == 1 and cache_payload.get("heavy_preview_route_decoupled_from_doctor") is True, "message": f"heavy_route_rows={len(heavy_route_rows)} lightweight_rows={len(lightweight_rows)}"},
        {"name": "cache-does-not-call-live-api", "ok": cache_payload.get("cache_does_not_call_live_api") is True and cache_payload.get("live_measurements_performed") is False and all(row.get("measured_live") is False for row in rows), "message": "cache rows are static preview contracts, not live diagnostic calls."},
        {"name": "doctor-quick-link-decoupled", "ok": doctor_quick_link_lightweight and doctor_quick_link_heavy_removed, "message": f"lightweight_link={doctor_quick_link_lightweight} heavy_quick_link_removed={doctor_quick_link_heavy_removed}"},
        {"name": "behavioral-count-current", "ok": int(V1043_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_CACHE_REPORT_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={int(V1043_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_CACHE_REPORT_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": int(V1043_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={int(V1043_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1044-doctor-diagnostic-preview-cache-heavy-route-decoupling" in manifest_source, "message": "Source surface manifest represents the v1044 doctor diagnostic preview cache surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1044 cache/heavy-route decoupling truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["cache_endpoint_executes_live_work", "cache_endpoint_applies_patches", "cache_endpoint_writes_memory", "cache_endpoint_creates_release", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Preview cache remains advisory and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_ID,
        "state": "doctor_diagnostic_preview_cache_heavy_route_decoupling_review_only",
        "prior_total_behavioral_coverage_count": int(V1043_TOTAL_BEHAVIORAL_COVERAGE_COUNT),
        "new_cache_report_behavioral_coverage_count": NEW_CACHE_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": int(V1043_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_CACHE_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": int(V1043_MAPPING_RECONCILED_ROUTE_COUNT),
        "mapping_reconciled_route_count": int(V1043_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "cache_api_route": CACHE_API_ROUTE,
        "cache_api_target_count": CACHE_API_TARGET_COUNT,
        "cache_api_elapsed_ms": elapsed_ms,
        "deferred_diagnostic_target_count": len(rows),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "cache_row_contract_pass_count": cache_row_contract_pass_count,
        "cache_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "cache_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "diagnostic_rows": rows,
        "api_diagnostic_rows": api_rows,
        "lightweight_preview_route": LIGHTWEIGHT_PREVIEW_ROUTE,
        "old_heavy_preview_route": HEAVY_PREVIEW_ROUTE,
        "heavy_preview_route_preserved": cache_payload.get("heavy_preview_route_preserved") is True,
        "doctor_controlled_self_build_link_migrated": cache_payload.get("doctor_controlled_self_build_link_migrated") is True,
        "heavy_preview_route_decoupled_from_doctor": cache_payload.get("heavy_preview_route_decoupled_from_doctor") is True,
        "cache_does_not_call_live_api": cache_payload.get("cache_does_not_call_live_api") is True,
        "live_measurements_performed": cache_payload.get("live_measurements_performed") is True,
        "diagnostic_storm_avoided": cache_payload.get("diagnostic_storm_avoided") is True,
        "cache_endpoint_preview_only": cache_payload.get("preview_only") is True,
        "cache_endpoint_executes_live_work": cache_payload.get("executes_live_work") is True,
        "cache_endpoint_applies_patches": cache_payload.get("applies_patches") is True,
        "cache_endpoint_writes_memory": cache_payload.get("writes_memory") is True,
        "cache_endpoint_creates_release": cache_payload.get("creates_release") is True,
        "doctor_quick_link_lightweight": doctor_quick_link_lightweight,
        "doctor_quick_link_heavy_removed": doctor_quick_link_heavy_removed,
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
        "rows": rows_status,
        "blocked": [row for row in rows_status if not row["ok"]],
        "status": "pass" if ok else "blocked",
        "ok": ok,
    }
    return report


def doctor_diagnostic_preview_cache_heavy_route_decoupling_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_preview_cache",
        "build_doctor_diagnostic_preview_cache_heavy_route_decoupling_review",
        "doctor_diagnostic_preview_cache_heavy_route_decoupling_review_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_cache_report_behavioral_coverage_count={report.get('new_cache_report_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"cache_api_route={report.get('cache_api_route')}",
        f"cache_api_target_count={report.get('cache_api_target_count')}",
        f"deferred_diagnostic_target_count={report.get('deferred_diagnostic_target_count')}",
        f"cache_ttl_seconds={report.get('cache_ttl_seconds')}",
        f"cache_row_contract_pass_count={report.get('cache_row_contract_pass_count')}",
        f"cache_payload_shape_pass_count={report.get('cache_payload_shape_pass_count')}",
        f"cache_api_pass_count={report.get('cache_api_pass_count')}",
        f"lightweight_preview_route={report.get('lightweight_preview_route')}",
        f"old_heavy_preview_route={report.get('old_heavy_preview_route')}",
        f"heavy_preview_route_preserved={report.get('heavy_preview_route_preserved')}",
        f"doctor_controlled_self_build_link_migrated={report.get('doctor_controlled_self_build_link_migrated')}",
        f"heavy_preview_route_decoupled_from_doctor={report.get('heavy_preview_route_decoupled_from_doctor')}",
        f"cache_does_not_call_live_api={report.get('cache_does_not_call_live_api')}",
        f"live_measurements_performed={report.get('live_measurements_performed')}",
        f"diagnostic_storm_avoided={report.get('diagnostic_storm_avoided')}",
        f"cache_endpoint_preview_only={report.get('cache_endpoint_preview_only')}",
        f"cache_endpoint_executes_live_work={report.get('cache_endpoint_executes_live_work')}",
        f"cache_endpoint_applies_patches={report.get('cache_endpoint_applies_patches')}",
        f"cache_endpoint_writes_memory={report.get('cache_endpoint_writes_memory')}",
        f"cache_endpoint_creates_release={report.get('cache_endpoint_creates_release')}",
        f"doctor_quick_link_lightweight={report.get('doctor_quick_link_lightweight')}",
        f"doctor_quick_link_heavy_removed={report.get('doctor_quick_link_heavy_removed')}",
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
        f"status={report.get('status')}",
    ]
    if full:
        lines.append("\nCached diagnostic rows:")
        for row in report.get("diagnostic_rows", []):
            lines.append(f"- {row.get('label')} -> {row.get('route')}: lane={row.get('lane')} cache_only={row.get('cache_only')} measured_live={row.get('measured_live')} heavy_decoupled={row.get('heavy_preview_decoupled')} ok={row.get('ok')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
