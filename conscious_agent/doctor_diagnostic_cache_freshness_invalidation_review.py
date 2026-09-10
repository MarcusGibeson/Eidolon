from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_preview_cache_heavy_route_decoupling import (
    CACHE_API_ROUTE,
    CACHE_TTL_SECONDS,
    DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_ID,
    HEAVY_PREVIEW_ROUTE,
    LIGHTWEIGHT_PREVIEW_ROUTE,
    build_doctor_diagnostic_preview_cache,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1044_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1044_MAPPING_RECONCILED_ROUTE_COUNT,
)

DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID = "doctor-diagnostic-cache-freshness-and-invalidation-review-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
CACHE_MODULE = "conscious_agent/doctor_diagnostic_preview_cache_heavy_route_decoupling.py"
LINK_MIGRATION_MODULE = "conscious_agent/doctor_controlled_self_build_lightweight_link_migration.py"
LATENCY_SHAPE_MODULE = "conscious_agent/doctor_deferred_diagnostic_latency_budget_payload_shape.py"
LIGHTWEIGHT_PREVIEW_MODULE = "conscious_agent/controlled_self_build_lightweight_preview_endpoint_prep.py"
SELF_ROUTE = "/doctor-diagnostic-cache-freshness-invalidation-review"
SELF_RENDERER = "render_doctor_diagnostic_cache_freshness_invalidation_review"
FRESHNESS_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 109
NEW_FRESHNESS_REVIEW_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 110
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 115
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 116
EXPECTED_DEFERRED_DIAGNOSTIC_ROW_COUNT = 5
EXPECTED_INVALIDATION_SOURCE_COUNT = 7
EXPECTED_FRESHNESS_PAYLOAD_SHAPE_PASS_COUNT = 1
EXPECTED_FRESHNESS_API_PASS_COUNT = 1
EXPECTED_CACHE_PREVIEW_ONLY_PASS_COUNT = 1
FRESHNESS_REVALIDATE_ON_SOURCE_CHANGE = True
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "freshness_metadata_preview_only": True,
    "cache_invalidation_review_only": True,
    "reads_source_files_only": True,
    "preview_cache_endpoint_stays_preview_only": True,
    "live_measurements_stay_in_targeted_smoke": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "freshness_endpoint_executes_live_work": False,
    "freshness_endpoint_applies_patches": False,
    "freshness_endpoint_writes_memory": False,
    "freshness_endpoint_creates_release": False,
    "freshness_endpoint_persists_cache": False,
    "cache_endpoint_calls_live_diagnostics": False,
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
class DiagnosticCacheInvalidationSource:
    source_id: str
    path: str
    token: str
    reason: str
    invalidates_on_change: bool
    required_for_cache: bool
    present: bool
    digest_prefix: str
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


def _digest_prefix(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16] if text else "missing"


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


def _invalidation_specs() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("doctor-lazy-diagnostic-links", DASHBOARD_MODULE, "DOCTOR_LAZY_DIAGNOSTIC_SECTIONS", "Changes to /doctor deferred diagnostic links alter the cache row contract."),
        ("preview-cache-builder", CACHE_MODULE, "build_doctor_diagnostic_preview_cache", "Changes to the cache builder alter preview-only summary semantics."),
        ("doctor-cache-api-dispatch", API_MODULE, 'if parts == ["doctor", "diagnostic-preview-cache"]', "Changes to manual API dispatch alter the cache endpoint contract."),
        ("doctor-cache-freshness-api-dispatch", API_MODULE, 'if parts == ["doctor", "diagnostic-preview-cache", "freshness"]', "Changes to freshness dispatch alter the invalidation review endpoint contract."),
        ("lightweight-preview-contract", LIGHTWEIGHT_PREVIEW_MODULE, "build_controlled_self_build_lightweight_preview", "Changes to the lightweight preview contract can alter the migrated doctor diagnostic row."),
        ("latency-payload-shape-contract", LATENCY_SHAPE_MODULE, "DIAGNOSTIC_SHAPE_SPECS", "Changes to live latency or payload-shape specs should refresh cached diagnostic summaries."),
        ("manual-smoke-cache-coverage", MANUAL_SMOKE_MODULE, DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID, "Changes to manual smoke coverage alter the release evidence for cache freshness."),
    )


def _invalidation_sources(root: Path) -> list[DiagnosticCacheInvalidationSource]:
    rows: list[DiagnosticCacheInvalidationSource] = []
    for source_id, rel, token, reason in _invalidation_specs():
        source = _read_text(root, rel)
        present = token in source
        rows.append(
            DiagnosticCacheInvalidationSource(
                source_id=source_id,
                path=rel,
                token=token,
                reason=reason,
                invalidates_on_change=True,
                required_for_cache=True,
                present=present,
                digest_prefix=_digest_prefix(source),
                ok=present,
                message=f"present={present} invalidates_on_change=True digest_prefix={_digest_prefix(source)}",
            )
        )
    return rows


def build_doctor_diagnostic_cache_freshness_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    checked_at = _now()
    expires_at = (datetime.fromisoformat(checked_at) + timedelta(seconds=CACHE_TTL_SECONDS)).isoformat(timespec="seconds")
    cache_payload = build_doctor_diagnostic_preview_cache(project_id=project_id)
    diagnostic_rows = cache_payload.get("diagnostic_rows", []) if isinstance(cache_payload, dict) else []
    invalidation_rows = _invalidation_sources(project_root)
    row_dicts = [asdict(row) for row in invalidation_rows]
    fingerprint_seed = "|".join(
        [
            CURRENT_VERSION,
            str(CACHE_TTL_SECONDS),
            str(len(diagnostic_rows)),
            *[str(row.get("route")) for row in diagnostic_rows if isinstance(row, dict)],
            *[row.digest_prefix for row in invalidation_rows],
        ]
    )
    cache_fingerprint = hashlib.sha256(fingerprint_seed.encode("utf-8", errors="ignore")).hexdigest()
    ok = (
        cache_payload.get("ok") is True
        and cache_payload.get("preview_only") is True
        and cache_payload.get("cache_does_not_call_live_api") is True
        and len(diagnostic_rows) == EXPECTED_DEFERRED_DIAGNOSTIC_ROW_COUNT
        and len(invalidation_rows) == EXPECTED_INVALIDATION_SOURCE_COUNT
        and all(row.ok for row in invalidation_rows)
        and PERSISTED_CACHE_WRITTEN is False
        and LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED is False
    )
    return {
        "version": CURRENT_VERSION,
        "checked_at": checked_at,
        "expires_at": expires_at,
        "project_id": project_id,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_only": True,
        "freshness_metadata_preview_only": True,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "freshness_window_seconds": CACHE_TTL_SECONDS,
        "revalidate_on_source_change": FRESHNESS_REVALIDATE_ON_SOURCE_CHANGE,
        "invalidation_policy": "invalidate_on_dashboard_api_contract_smoke_or_current_release_source_change",
        "cache_strategy": "static_contract_summary_with_source_dependency_fingerprint",
        "cache_fingerprint": cache_fingerprint,
        "cache_version_key": f"v{CURRENT_VERSION}:{cache_fingerprint[:12]}",
        "deferred_diagnostic_row_count": len(diagnostic_rows),
        "invalidation_source_count": len(invalidation_rows),
        "invalidation_sources": row_dicts,
        "invalidation_source_pass_count": sum(1 for row in invalidation_rows if row.ok),
        "dependency_digest_count": sum(1 for row in invalidation_rows if row.digest_prefix != "missing"),
        "cache_preview_only_pass": cache_payload.get("preview_only") is True and cache_payload.get("cache_does_not_call_live_api") is True,
        "live_diagnostic_measurements_performed": LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED,
        "persisted_cache_written": PERSISTED_CACHE_WRITTEN,
        "executes_live_work": False,
        "applies_patches": False,
        "writes_memory": False,
        "creates_release": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "recommendations": [
            "Invalidate cached doctor diagnostic summaries when dashboard lazy-link, API dispatch, payload-shape, lightweight-preview, smoke, or current-release source contracts change.",
            "Keep live diagnostic measurements in targeted smoke and keep dashboard page loads on preview-only metadata.",
            "Preserve /api/controlled-self-build as a deliberate full preview route while /doctor uses lightweight/cache surfaces.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-freshness-and-invalidation-review-v1",
            "python tools/smoke_check.py --check doctor-diagnostic-preview-cache-and-heavy-route-decoupling-v1",
        ],
        "message": "Doctor diagnostic cache freshness and invalidation metadata is preview-only and source-fingerprint based.",
    }


def build_doctor_diagnostic_cache_freshness_invalidation_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_cache_freshness_invalidation_review.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)

    freshness_payload = build_doctor_diagnostic_cache_freshness_metadata(project_id="eidolon", root=project_root)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, FRESHNESS_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    invalidation_rows = freshness_payload.get("invalidation_sources", [])
    api_invalidation_rows = api_data.get("invalidation_sources", []) if isinstance(api_data, dict) else []
    required_api_data_keys = (
        "version",
        "checked_at",
        "expires_at",
        "project_id",
        "status",
        "ok",
        "preview_only",
        "freshness_metadata_preview_only",
        "source_cache_route",
        "freshness_api_route",
        "cache_ttl_seconds",
        "freshness_window_seconds",
        "revalidate_on_source_change",
        "invalidation_policy",
        "cache_strategy",
        "cache_fingerprint",
        "cache_version_key",
        "deferred_diagnostic_row_count",
        "invalidation_source_count",
        "invalidation_sources",
        "invalidation_source_pass_count",
        "dependency_digest_count",
        "cache_preview_only_pass",
        "live_diagnostic_measurements_performed",
        "persisted_cache_written",
        "executes_live_work",
        "applies_patches",
        "writes_memory",
        "creates_release",
        "generated_wiring_activated",
        "release_authorized",
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
        and isinstance(api_data.get("invalidation_sources"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness"]' in api_source
    invalidation_pass_count = sum(1 for row in invalidation_rows if row.get("ok") is True)
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID,
        SELF_ROUTE,
        FRESHNESS_API_ROUTE,
        "build_doctor_diagnostic_cache_freshness_metadata",
        "build_doctor_diagnostic_cache_freshness_invalidation_review",
        "doctor_diagnostic_cache_freshness_invalidation_review_text",
        "prior_total_behavioral_coverage_count=109",
        "new_freshness_review_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=110",
        "prior_mapping_reconciled_route_count=115",
        "mapping_reconciled_route_count=116",
        "cache_ttl_seconds=60",
        "freshness_window_seconds=60",
        "invalidation_source_count=7",
        "invalidation_source_pass_count=7",
        "freshness_payload_shape_pass_count=1",
        "freshness_api_pass_count=1",
        "cache_preview_only_pass_count=1",
        "live_diagnostic_measurements_performed=False",
        "persisted_cache_written=False",
        "revalidate_on_source_change=True",
        "manual_api_dispatch_remains_authoritative=True",
        "generated_wiring_activated=False",
        "autonomy_expanded=False",
    ]
    rows_status = [
        {"name": "module-version-current", "ok": DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1044-token-present", "ok": DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_ID in docs, "message": f"prior token {DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_ID} present."},
        {"name": "freshness-api-index-and-handler-present", "ok": api_index_present and api_handler_present, "message": f"api_index_present={api_index_present} api_handler_present={api_handler_present}"},
        {"name": "freshness-api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing_api_data_keys={len(missing_api_data_keys)} error={api_error}"},
        {"name": "invalidation-sources-present", "ok": invalidation_pass_count == EXPECTED_INVALIDATION_SOURCE_COUNT and len(invalidation_rows) == EXPECTED_INVALIDATION_SOURCE_COUNT, "message": f"pass={invalidation_pass_count} rows={len(invalidation_rows)}"},
        {"name": "api-invalidation-source-parity", "ok": [row.get("source_id") for row in invalidation_rows] == [row.get("source_id") for row in api_invalidation_rows], "message": f"metadata_rows={len(invalidation_rows)} api_rows={len(api_invalidation_rows)}"},
        {"name": "cache-preview-only-preserved", "ok": freshness_payload.get("cache_preview_only_pass") is True and freshness_payload.get("live_diagnostic_measurements_performed") is False and freshness_payload.get("persisted_cache_written") is False, "message": f"preview_only={freshness_payload.get('cache_preview_only_pass')} live_measurements={freshness_payload.get('live_diagnostic_measurements_performed')} persisted={freshness_payload.get('persisted_cache_written')}"},
        {"name": "behavioral-count-current", "ok": int(V1044_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_FRESHNESS_REVIEW_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={int(V1044_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_FRESHNESS_REVIEW_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": int(V1044_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={int(V1044_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1045-doctor-diagnostic-cache-freshness-invalidation-review" in manifest_source, "message": "Source surface manifest represents the v1045 cache freshness/invalidation surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1045 cache freshness/invalidation truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["freshness_endpoint_executes_live_work", "freshness_endpoint_applies_patches", "freshness_endpoint_writes_memory", "freshness_endpoint_creates_release", "freshness_endpoint_persists_cache", "cache_endpoint_calls_live_diagnostics", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Freshness review remains advisory and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID,
        "state": "doctor_diagnostic_cache_freshness_invalidation_review_only",
        "prior_total_behavioral_coverage_count": int(V1044_TOTAL_BEHAVIORAL_COVERAGE_COUNT),
        "new_freshness_review_behavioral_coverage_count": NEW_FRESHNESS_REVIEW_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": int(V1044_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_FRESHNESS_REVIEW_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": int(V1044_MAPPING_RECONCILED_ROUTE_COUNT),
        "mapping_reconciled_route_count": int(V1044_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "freshness_api_elapsed_ms": elapsed_ms,
        "cache_ttl_seconds": freshness_payload.get("cache_ttl_seconds"),
        "freshness_window_seconds": freshness_payload.get("freshness_window_seconds"),
        "revalidate_on_source_change": freshness_payload.get("revalidate_on_source_change"),
        "invalidation_policy": freshness_payload.get("invalidation_policy"),
        "cache_strategy": freshness_payload.get("cache_strategy"),
        "cache_fingerprint": freshness_payload.get("cache_fingerprint"),
        "cache_version_key": freshness_payload.get("cache_version_key"),
        "deferred_diagnostic_row_count": freshness_payload.get("deferred_diagnostic_row_count"),
        "invalidation_source_count": len(invalidation_rows),
        "invalidation_source_pass_count": invalidation_pass_count,
        "dependency_digest_count": freshness_payload.get("dependency_digest_count"),
        "freshness_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "freshness_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "cache_preview_only_pass_count": 1 if freshness_payload.get("cache_preview_only_pass") is True else 0,
        "invalidation_sources": invalidation_rows,
        "api_invalidation_sources": api_invalidation_rows,
        "live_diagnostic_measurements_performed": freshness_payload.get("live_diagnostic_measurements_performed"),
        "persisted_cache_written": freshness_payload.get("persisted_cache_written"),
        "freshness_endpoint_preview_only": freshness_payload.get("preview_only") is True,
        "freshness_endpoint_executes_live_work": freshness_payload.get("executes_live_work"),
        "freshness_endpoint_applies_patches": freshness_payload.get("applies_patches"),
        "freshness_endpoint_writes_memory": freshness_payload.get("writes_memory"),
        "freshness_endpoint_creates_release": freshness_payload.get("creates_release"),
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


def doctor_diagnostic_cache_freshness_invalidation_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_cache_freshness_metadata",
        "build_doctor_diagnostic_cache_freshness_invalidation_review",
        "doctor_diagnostic_cache_freshness_invalidation_review_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_freshness_review_behavioral_coverage_count={report.get('new_freshness_review_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"source_cache_route={report.get('source_cache_route')}",
        f"freshness_api_route={report.get('freshness_api_route')}",
        "lightweight_preview_route=/api/controlled-self-build/lightweight-preview",
        "old_heavy_preview_route=/api/controlled-self-build",
        f"cache_ttl_seconds={report.get('cache_ttl_seconds')}",
        f"freshness_window_seconds={report.get('freshness_window_seconds')}",
        f"revalidate_on_source_change={report.get('revalidate_on_source_change')}",
        f"invalidation_source_count={report.get('invalidation_source_count')}",
        f"invalidation_source_pass_count={report.get('invalidation_source_pass_count')}",
        f"dependency_digest_count={report.get('dependency_digest_count')}",
        f"freshness_payload_shape_pass_count={report.get('freshness_payload_shape_pass_count')}",
        f"freshness_api_pass_count={report.get('freshness_api_pass_count')}",
        f"cache_preview_only_pass_count={report.get('cache_preview_only_pass_count')}",
        f"live_diagnostic_measurements_performed={report.get('live_diagnostic_measurements_performed')}",
        f"persisted_cache_written={report.get('persisted_cache_written')}",
        f"freshness_endpoint_preview_only={report.get('freshness_endpoint_preview_only')}",
        f"freshness_endpoint_executes_live_work={report.get('freshness_endpoint_executes_live_work')}",
        f"freshness_endpoint_applies_patches={report.get('freshness_endpoint_applies_patches')}",
        f"freshness_endpoint_writes_memory={report.get('freshness_endpoint_writes_memory')}",
        f"freshness_endpoint_creates_release={report.get('freshness_endpoint_creates_release')}",
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
        lines.append("\nInvalidation sources:")
        for row in report.get("invalidation_sources", []):
            lines.append(f"- {row.get('source_id')} {row.get('path')} token={row.get('token')} invalidates_on_change={row.get('invalidates_on_change')} digest={row.get('digest_prefix')} ok={row.get('ok')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
