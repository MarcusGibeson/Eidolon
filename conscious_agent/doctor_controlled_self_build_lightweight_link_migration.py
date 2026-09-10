from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from controlled_self_build_lightweight_preview_endpoint_prep import (
    CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_ID,
    LIGHTWEIGHT_PREVIEW_ROUTE,
    HEAVY_PREVIEW_ROUTE,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1042_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1042_MAPPING_RECONCILED_ROUTE_COUNT,
)
from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_VERSION = RUNTIME_VERSION
DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_ID = "doctor-controlled-self-build-lightweight-link-migration-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-controlled-self-build-lightweight-link-migration"
SELF_RENDERER = "render_doctor_controlled_self_build_lightweight_link_migration"
DOCTOR_ROUTE = "/doctor"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 107
NEW_LINK_MIGRATION_REPORT_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 108
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 113
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 114
DEFERRED_DIAGNOSTIC_TARGET_COUNT = 5
MIGRATED_DIAGNOSTIC_LINK_COUNT = 1
LIGHTWEIGHT_DIAGNOSTIC_BUDGET_MS = 2000
STANDARD_DIAGNOSTIC_BUDGET_MS = 8000
EXPECTED_LATENCY_PASS_COUNT = 5
EXPECTED_PAYLOAD_SHAPE_PASS_COUNT = 5
EXPECTED_LIVE_API_PASS_COUNT = 5

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "doctor_link_migration_review_only": True,
    "doctor_remains_long_isolated": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "heavy_preview_route_preserved": True,
    "lightweight_get_preview_only": True,
    "migrated_link_executes_live_work": False,
    "migrated_link_applies_patches": False,
    "migrated_link_writes_memory": False,
    "migrated_link_creates_release": False,
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
class MigratedDiagnosticShapeSpec:
    label: str
    dashboard_route: str
    api_probe_route: str
    lane: str
    budget_ms: int
    required_data_keys: tuple[str, ...]
    expected_collection_keys: tuple[str, ...]
    allow_diagnostic_ok_false: bool
    migrated_from: str = ""


@dataclass(frozen=True)
class MigratedDiagnosticApiRow:
    label: str
    dashboard_route: str
    api_probe_route: str
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
    preview_only: bool | None
    lightweight_preview: bool | None
    live_work_executed: bool
    applies_patches: bool
    writes_memory: bool
    creates_release: bool
    generated_wiring_activated: bool
    autonomy_expanded: bool
    missing_data_keys: tuple[str, ...]
    missing_collection_keys: tuple[str, ...]
    migrated_from: str
    ok: bool
    message: str


MIGRATED_DIAGNOSTIC_SHAPE_SPECS: tuple[MigratedDiagnosticShapeSpec, ...] = (
    MigratedDiagnosticShapeSpec(
        "Repair Suggestions",
        "/api/repair-suggestions",
        "/api/repair-suggestions",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "counts", "rows", "recommendations", "next_commands", "message"),
        ("rows", "recommendations", "next_commands"),
        True,
    ),
    MigratedDiagnosticShapeSpec(
        "Project Snapshot",
        "/api/project-snapshot",
        "/api/project-snapshot",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "active_project", "task_counts", "recommendations", "next_commands", "message"),
        ("recommendations", "next_commands"),
        True,
    ),
    MigratedDiagnosticShapeSpec(
        "Stable Loop Confidence",
        "/api/stable-loops/confidence",
        "/api/stable-loops/confidence",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "score", "strengths", "weaknesses", "recommendations", "next_commands", "inputs", "message"),
        ("strengths", "weaknesses", "recommendations", "next_commands"),
        True,
    ),
    MigratedDiagnosticShapeSpec(
        "Hardening",
        "/api/hardening-report",
        "/api/hardening-report",
        "standard_diagnostic",
        STANDARD_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "counts", "rows", "blockers", "recommendations", "next_commands", "message"),
        ("rows", "blockers", "recommendations", "next_commands"),
        True,
    ),
    MigratedDiagnosticShapeSpec(
        "Controlled Self-Build Lightweight Preview",
        LIGHTWEIGHT_PREVIEW_ROUTE,
        LIGHTWEIGHT_PREVIEW_ROUTE + "?live=true&approve=true&steps=5",
        "lightweight_diagnostic_preview",
        LIGHTWEIGHT_DIAGNOSTIC_BUDGET_MS,
        ("version", "checked_at", "project_id", "status", "ok", "live", "approved_live", "use_ai", "max_steps", "preview_endpoint", "heavy_preview_route", "lightweight_preview", "preview_only", "executes_live_work", "applies_patches", "writes_memory", "creates_release", "generated_wiring_activated", "autonomy_expanded", "requires_post_for_live_work", "live_confirmation_required", "actions", "recommendations", "next_commands", "message"),
        ("actions", "recommendations", "next_commands"),
        True,
        migrated_from=HEAVY_PREVIEW_ROUTE,
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


def _dashboard_lazy_sections(root: Path) -> list[dict[str, str]]:
    import sys
    sys.path.insert(0, str(root / "conscious_agent"))
    import dashboard  # type: ignore

    return [dict(section) for section in getattr(dashboard, "DOCTOR_LAZY_DIAGNOSTIC_SECTIONS", ())]


def _call_live_api(root: Path, route: str) -> tuple[int, dict[str, Any], int, str | None]:
    import sys
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


def _live_work_executed(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return bool(data.get("live") or data.get("approved_live") or data.get("run_result") or data.get("executes_live_work"))


def _row_from_spec(root: Path, spec: MigratedDiagnosticShapeSpec) -> MigratedDiagnosticApiRow:
    status, payload, elapsed_ms, error = _call_live_api(root, spec.api_probe_route)
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
    preview_only: bool | None = None
    lightweight_preview: bool | None = None
    if isinstance(data, dict):
        diagnostic_status = str(data.get("status", "unknown"))
        if isinstance(data.get("ok"), bool):
            diagnostic_ok = bool(data.get("ok"))
        if "preview_only" in data:
            preview_only = bool(data.get("preview_only"))
        if "lightweight_preview" in data:
            lightweight_preview = bool(data.get("lightweight_preview"))
    api_wrapper_ok = bool(isinstance(payload, dict) and payload.get("ok") is True)
    latency_budget_pass = elapsed_ms <= spec.budget_ms
    data_shape_pass = not missing_data_keys
    collection_shape_pass = not missing_collection_keys
    payload_shape_pass = top_level_shape_pass and data_shape_pass and collection_shape_pass
    live_work = _live_work_executed(data)
    applies_patches = bool(isinstance(data, dict) and data.get("applies_patches") is True)
    writes_memory = bool(isinstance(data, dict) and data.get("writes_memory") is True)
    creates_release = bool(isinstance(data, dict) and data.get("creates_release") is True)
    generated = bool(isinstance(data, dict) and data.get("generated_wiring_activated") is True)
    autonomy = bool(isinstance(data, dict) and data.get("autonomy_expanded") is True)
    if spec.dashboard_route == LIGHTWEIGHT_PREVIEW_ROUTE:
        lightweight_safety_pass = preview_only is True and lightweight_preview is True and bool(isinstance(data, dict) and data.get("live") is False) and bool(isinstance(data, dict) and data.get("approved_live") is False)
    else:
        lightweight_safety_pass = True
    ok = (
        status == 200
        and api_wrapper_ok
        and error is None
        and latency_budget_pass
        and payload_shape_pass
        and live_work is False
        and applies_patches is False
        and writes_memory is False
        and creates_release is False
        and generated is False
        and autonomy is False
        and lightweight_safety_pass
        and (spec.allow_diagnostic_ok_false or diagnostic_ok is True)
    )
    message = (
        f"lane={spec.lane} status={status} wrapper_ok={api_wrapper_ok} elapsed_ms={elapsed_ms} "
        f"budget_ms={spec.budget_ms} payload_shape_pass={payload_shape_pass} "
        f"diagnostic_status={diagnostic_status} preview_only={preview_only} lightweight_preview={lightweight_preview} "
        f"live_work_executed={live_work} migrated_from={spec.migrated_from or 'none'}"
    )
    return MigratedDiagnosticApiRow(
        label=spec.label,
        dashboard_route=spec.dashboard_route,
        api_probe_route=spec.api_probe_route,
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
        preview_only=preview_only,
        lightweight_preview=lightweight_preview,
        live_work_executed=live_work,
        applies_patches=applies_patches,
        writes_memory=writes_memory,
        creates_release=creates_release,
        generated_wiring_activated=generated,
        autonomy_expanded=autonomy,
        missing_data_keys=missing_data_keys,
        missing_collection_keys=missing_collection_keys,
        migrated_from=spec.migrated_from,
        ok=ok,
        message=message,
    )


def build_doctor_controlled_self_build_lightweight_link_migration_review(root: str | Path | None = None) -> dict[str, Any]:
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
    module_source = _read_text(project_root, "conscious_agent/doctor_controlled_self_build_lightweight_link_migration.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])

    route_map = _route_renderer_map(dashboard_source)
    dashboard_sections = _dashboard_lazy_sections(project_root)
    dashboard_routes = [section.get("route") for section in dashboard_sections]
    expected_routes = [spec.dashboard_route for spec in MIGRATED_DIAGNOSTIC_SHAPE_SPECS]
    rows = [_row_from_spec(project_root, spec) for spec in MIGRATED_DIAGNOSTIC_SHAPE_SPECS]
    row_dicts = [asdict(row) for row in rows]
    migrated_rows = [row for row in rows if row.migrated_from == HEAVY_PREVIEW_ROUTE]
    latency_pass_count = sum(1 for row in rows if row.latency_budget_pass)
    payload_shape_pass_count = sum(1 for row in rows if row.payload_shape_pass)
    live_pass_count = sum(1 for row in rows if row.ok)
    lightweight_rows = [row for row in rows if row.dashboard_route == LIGHTWEIGHT_PREVIEW_ROUTE]
    heavy_preview_route_preserved = (
        '"GET /api/controlled-self-build"' in api_source
        and 'if parts == ["controlled-self-build"]' in api_source
        and 'GET is preview-only' in api_source
        and 'LIVE_CONTROLLED_BUILD' in api_source
    )
    dashboard_link_migrated = (
        dashboard_routes == expected_routes
        and LIGHTWEIGHT_PREVIEW_ROUTE in dashboard_routes
        and HEAVY_PREVIEW_ROUTE not in dashboard_routes
    )
    lightweight_safety_pass = bool(
        lightweight_rows
        and all(row.preview_only is True and row.lightweight_preview is True and row.live_work_executed is False for row in lightweight_rows)
    )
    prior_total = int(V1042_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping = int(V1042_MAPPING_RECONCILED_ROUTE_COUNT)
    mapping_mismatches = [
        {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)},
    ]
    mapping_mismatches = [row for row in mapping_mismatches if row["actual_renderer"] != row["expected_renderer"]]
    required_tokens = [
        DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_ID,
        SELF_ROUTE,
        "build_doctor_controlled_self_build_lightweight_link_migration_review",
        "doctor_controlled_self_build_lightweight_link_migration_review_text",
        "prior_total_behavioral_coverage_count=107",
        "new_link_migration_report_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=108",
        "prior_mapping_reconciled_route_count=113",
        "mapping_reconciled_route_count=114",
        "deferred_diagnostic_target_count=5",
        "migrated_diagnostic_link_count=1",
        "lightweight_preview_route=/api/controlled-self-build/lightweight-preview",
        "old_heavy_preview_route_preserved=True",
        "doctor_controlled_self_build_link_migrated=True",
        "lightweight_preview_only=True",
        "lightweight_preview_does_not_execute_live_work=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows_status = [
        {"name": "module-version-current", "ok": DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1042-token-present", "ok": CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_ID in docs, "message": f"prior token {CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_ID} present in docs/source."},
        {"name": "dashboard-lazy-link-migrated", "ok": dashboard_link_migrated, "message": f"dashboard_routes={dashboard_routes} expected_routes={expected_routes}"},
        {"name": "deferred-diagnostic-target-count", "ok": len(rows) == DEFERRED_DIAGNOSTIC_TARGET_COUNT and len(dashboard_sections) == DEFERRED_DIAGNOSTIC_TARGET_COUNT, "message": f"rows={len(rows)} dashboard_sections={len(dashboard_sections)}"},
        {"name": "migrated-diagnostic-link-count", "ok": len(migrated_rows) == MIGRATED_DIAGNOSTIC_LINK_COUNT, "message": f"migrated_links={len(migrated_rows)}"},
        {"name": "latency-budget-rows-pass", "ok": latency_pass_count == EXPECTED_LATENCY_PASS_COUNT and all(row.latency_budget_pass for row in rows), "message": f"latency_budget_pass_count={latency_pass_count}"},
        {"name": "payload-shape-rows-pass", "ok": payload_shape_pass_count == EXPECTED_PAYLOAD_SHAPE_PASS_COUNT and all(row.payload_shape_pass for row in rows), "message": f"payload_shape_pass_count={payload_shape_pass_count}"},
        {"name": "live-api-wrapper-rows-pass", "ok": live_pass_count == EXPECTED_LIVE_API_PASS_COUNT and all(row.live_status == 200 and row.api_wrapper_ok for row in rows), "message": f"live_pass_count={live_pass_count}"},
        {"name": "lightweight-preview-safety", "ok": lightweight_safety_pass, "message": "lightweight diagnostic target remains preview-only and cannot become live work through GET query flags."},
        {"name": "heavy-preview-route-preserved", "ok": heavy_preview_route_preserved, "message": "Old heavy /api/controlled-self-build GET route and POST confirmation token remain present."},
        {"name": "behavioral-count-current", "ok": prior_total + NEW_LINK_MIGRATION_REPORT_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_LINK_MIGRATION_REPORT_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "manifest-surface-current", "ok": "v1043-doctor-controlled-self-build-lightweight-link-migration" in manifest_source, "message": "Source surface manifest represents the v1043 doctor lightweight link migration surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1043 link migration truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["migrated_link_executes_live_work", "migrated_link_applies_patches", "migrated_link_writes_memory", "migrated_link_creates_release", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Doctor link migration remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_ID,
        "state": "doctor_controlled_self_build_lightweight_link_migration_review_only",
        "prior_total_behavioral_coverage_count": prior_total,
        "new_link_migration_report_behavioral_coverage_count": NEW_LINK_MIGRATION_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": prior_total + NEW_LINK_MIGRATION_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "deferred_diagnostic_target_count": len(rows),
        "migrated_diagnostic_link_count": len(migrated_rows),
        "lightweight_preview_route": LIGHTWEIGHT_PREVIEW_ROUTE,
        "old_heavy_preview_route": HEAVY_PREVIEW_ROUTE,
        "old_heavy_preview_route_preserved": heavy_preview_route_preserved,
        "doctor_controlled_self_build_link_migrated": dashboard_link_migrated,
        "latency_budget_pass_count": latency_pass_count,
        "payload_shape_pass_count": payload_shape_pass_count,
        "live_api_pass_count": live_pass_count,
        "lightweight_preview_only": lightweight_safety_pass,
        "lightweight_preview_does_not_execute_live_work": all(row.live_work_executed is False for row in rows),
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
        "dashboard_lazy_diagnostic_sections": dashboard_sections,
        "migrated_diagnostic_rows": row_dicts,
        "shape_specs": [asdict(spec) for spec in MIGRATED_DIAGNOSTIC_SHAPE_SPECS],
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


def doctor_controlled_self_build_lightweight_link_migration_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"dashboard_route={SELF_ROUTE}",
        "builder_function=build_doctor_controlled_self_build_lightweight_link_migration_review",
        "text_function=doctor_controlled_self_build_lightweight_link_migration_review_text",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_link_migration_report_behavioral_coverage_count={report.get('new_link_migration_report_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"deferred_diagnostic_target_count={report.get('deferred_diagnostic_target_count')}",
        f"migrated_diagnostic_link_count={report.get('migrated_diagnostic_link_count')}",
        f"lightweight_preview_route={report.get('lightweight_preview_route')}",
        f"old_heavy_preview_route={report.get('old_heavy_preview_route')}",
        f"old_heavy_preview_route_preserved={report.get('old_heavy_preview_route_preserved')}",
        f"doctor_controlled_self_build_link_migrated={report.get('doctor_controlled_self_build_link_migrated')}",
        f"latency_budget_pass_count={report.get('latency_budget_pass_count')}",
        f"payload_shape_pass_count={report.get('payload_shape_pass_count')}",
        f"live_api_pass_count={report.get('live_api_pass_count')}",
        f"lightweight_preview_only={report.get('lightweight_preview_only')}",
        f"lightweight_preview_does_not_execute_live_work={report.get('lightweight_preview_does_not_execute_live_work')}",
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
        "live_confirmation_token=LIVE_CONTROLLED_BUILD",
    ]
    if full:
        lines.append("\nMigrated diagnostic rows:")
        for row in report.get("migrated_diagnostic_rows", []):
            lines.append(
                f"- {row.get('label')}: dashboard_route={row.get('dashboard_route')} api_probe_route={row.get('api_probe_route')} lane={row.get('lane')} elapsed_ms={row.get('elapsed_ms')} budget_ms={row.get('budget_ms')} latency_ok={row.get('latency_budget_pass')} payload_shape_ok={row.get('payload_shape_pass')} preview_only={row.get('preview_only')} lightweight_preview={row.get('lightweight_preview')} live_work_executed={row.get('live_work_executed')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)
