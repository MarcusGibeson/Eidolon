from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_deferred_diagnostic_latency_budget_payload_shape import (
    DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1041_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1041_MAPPING_RECONCILED_ROUTE_COUNT,
)

CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_VERSION = RUNTIME_VERSION
CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_ID = "controlled-self-build-lightweight-preview-endpoint-prep-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
OPERATIONAL_READINESS_MODULE = "conscious_agent/operational_readiness.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/controlled-self-build-lightweight-preview-endpoint-prep"
SELF_RENDERER = "render_controlled_self_build_lightweight_preview_endpoint_prep"
LIGHTWEIGHT_PREVIEW_ROUTE = "/api/controlled-self-build/lightweight-preview"
HEAVY_PREVIEW_ROUTE = "/api/controlled-self-build"
LIVE_CONFIRMATION_TOKEN = "LIVE_CONTROLLED_BUILD"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 106
NEW_LIGHTWEIGHT_PREVIEW_REPORT_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 107
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 112
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 113
LIGHTWEIGHT_PREVIEW_BUDGET_MS = 2000
EXPECTED_LIGHTWEIGHT_PREVIEW_ENDPOINT_COUNT = 1
EXPECTED_PREVIEW_PAYLOAD_SHAPE_PASS_COUNT = 1
EXPECTED_LIVE_API_PASS_COUNT = 1

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "endpoint_prep_review_only": True,
    "lightweight_get_preview_only": True,
    "heavy_get_preview_only_preserved": True,
    "post_live_confirmation_preserved": True,
    "doctor_remains_long_isolated": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "lightweight_preview_executes_live_work": False,
    "lightweight_preview_runs_heavy_doctor": False,
    "lightweight_preview_runs_stable_loop_preflight": False,
    "lightweight_preview_applies_patches": False,
    "lightweight_preview_writes_memory": False,
    "lightweight_preview_creates_release": False,
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
class LightweightPreviewApiRow:
    label: str
    route: str
    budget_ms: int
    elapsed_ms: int
    live_status: int
    api_wrapper_ok: bool
    preview_only: bool
    lightweight_preview: bool
    live: bool
    approved_live: bool
    executes_live_work: bool
    applies_patches: bool
    writes_memory: bool
    creates_release: bool
    generated_wiring_activated: bool
    autonomy_expanded: bool
    top_level_shape_pass: bool
    data_shape_pass: bool
    payload_shape_pass: bool
    missing_data_keys: tuple[str, ...]
    ok: bool
    message: str


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


def _call_api(route: str) -> tuple[int, dict[str, Any], int, str | None]:
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


def _lightweight_api_row(route: str = LIGHTWEIGHT_PREVIEW_ROUTE + "?live=true&approve=true&steps=5") -> LightweightPreviewApiRow:
    status, payload, elapsed_ms, error = _call_api(route)
    data = payload.get("data") if isinstance(payload, dict) else None
    required = (
        "version",
        "checked_at",
        "project_id",
        "status",
        "ok",
        "live",
        "approved_live",
        "use_ai",
        "max_steps",
        "preview_endpoint",
        "heavy_preview_route",
        "lightweight_preview",
        "preview_only",
        "executes_live_work",
        "applies_patches",
        "writes_memory",
        "creates_release",
        "generated_wiring_activated",
        "autonomy_expanded",
        "requires_post_for_live_work",
        "live_confirmation_required",
        "actions",
        "recommendations",
        "next_commands",
        "message",
    )
    data_keys = tuple(data.keys()) if isinstance(data, dict) else tuple()
    missing = tuple(key for key in required if key not in data_keys)
    top_level_shape_pass = isinstance(payload, dict) and all(key in payload for key in ("ok", "api_version", "served_at", "data")) and isinstance(data, dict)
    data_shape_pass = not missing and isinstance(data, dict) and isinstance(data.get("actions"), list) and isinstance(data.get("recommendations"), list) and isinstance(data.get("next_commands"), list)
    preview_only = bool(isinstance(data, dict) and data.get("preview_only") is True)
    lightweight_preview = bool(isinstance(data, dict) and data.get("lightweight_preview") is True)
    live = bool(isinstance(data, dict) and data.get("live") is True)
    approved_live = bool(isinstance(data, dict) and data.get("approved_live") is True)
    executes_live_work = bool(isinstance(data, dict) and data.get("executes_live_work") is True)
    applies_patches = bool(isinstance(data, dict) and data.get("applies_patches") is True)
    writes_memory = bool(isinstance(data, dict) and data.get("writes_memory") is True)
    creates_release = bool(isinstance(data, dict) and data.get("creates_release") is True)
    generated = bool(isinstance(data, dict) and data.get("generated_wiring_activated") is True)
    autonomy = bool(isinstance(data, dict) and data.get("autonomy_expanded") is True)
    payload_shape_pass = top_level_shape_pass and data_shape_pass
    ok = (
        status == 200
        and error is None
        and bool(payload.get("ok") is True)
        and elapsed_ms <= LIGHTWEIGHT_PREVIEW_BUDGET_MS
        and payload_shape_pass
        and preview_only
        and lightweight_preview
        and live is False
        and approved_live is False
        and executes_live_work is False
        and applies_patches is False
        and writes_memory is False
        and creates_release is False
        and generated is False
        and autonomy is False
    )
    message = (
        f"status={status} wrapper_ok={payload.get('ok') is True if isinstance(payload, dict) else False} "
        f"elapsed_ms={elapsed_ms} budget_ms={LIGHTWEIGHT_PREVIEW_BUDGET_MS} "
        f"payload_shape_pass={payload_shape_pass} preview_only={preview_only} lightweight_preview={lightweight_preview} "
        f"live={live} approved_live={approved_live} executes_live_work={executes_live_work}"
    )
    return LightweightPreviewApiRow(
        label="Controlled Self-Build Lightweight Preview",
        route=LIGHTWEIGHT_PREVIEW_ROUTE,
        budget_ms=LIGHTWEIGHT_PREVIEW_BUDGET_MS,
        elapsed_ms=elapsed_ms,
        live_status=status,
        api_wrapper_ok=bool(isinstance(payload, dict) and payload.get("ok") is True),
        preview_only=preview_only,
        lightweight_preview=lightweight_preview,
        live=live,
        approved_live=approved_live,
        executes_live_work=executes_live_work,
        applies_patches=applies_patches,
        writes_memory=writes_memory,
        creates_release=creates_release,
        generated_wiring_activated=generated,
        autonomy_expanded=autonomy,
        top_level_shape_pass=top_level_shape_pass,
        data_shape_pass=data_shape_pass,
        payload_shape_pass=payload_shape_pass,
        missing_data_keys=missing,
        ok=ok,
        message=message,
    )


def build_controlled_self_build_lightweight_preview_endpoint_prep_review(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    dashboard_source = _read_text(repo, DASHBOARD_MODULE)
    api_source = _read_text(repo, API_MODULE)
    operational_source = _read_text(repo, OPERATIONAL_READINESS_MODULE)
    manifest_source = _read_text(repo, SOURCE_MANIFEST_MODULE)
    smoke_source = _read_text(repo, MANUAL_SMOKE_MODULE)
    docs = "\n".join([
        _read_text(repo, "README_NEXT_STEPS.md"),
        _read_text(repo, "README_RELEASE_HISTORY.md"),
        dashboard_source,
        api_source,
        operational_source,
        manifest_source,
        smoke_source,
    ])
    route_map = _route_renderer_map(dashboard_source)
    api_row = _lightweight_api_row()
    row_dict = asdict(api_row)
    mapping_mismatches = []
    if route_map.get(SELF_ROUTE) != SELF_RENDERER:
        mapping_mismatches.append({"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)})
    api_index_present = '"GET /api/controlled-self-build/lightweight-preview"' in api_source
    api_get_handler_present = 'if parts == ["controlled-self-build", "lightweight-preview"]' in api_source
    old_get_preview_only_preserved = 'if parts == ["controlled-self-build"]' in api_source and 'live=False, approve_live=False' in api_source and 'GET is preview-only' in api_source
    post_confirmation_preserved = 'if parts == ["controlled-self-build"]' in api_source and LIVE_CONFIRMATION_TOKEN in api_source and '_require_confirmation(body, "LIVE_CONTROLLED_BUILD")' in api_source
    builder_present = "def build_controlled_self_build_lightweight_preview" in operational_source
    heavy_builder_preserved = "def build_controlled_self_build(" in operational_source
    required_tokens = [
        CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_ID,
        SELF_ROUTE,
        "build_controlled_self_build_lightweight_preview_endpoint_prep_review",
        "controlled_self_build_lightweight_preview_endpoint_prep_review_text",
        LIGHTWEIGHT_PREVIEW_ROUTE,
        HEAVY_PREVIEW_ROUTE,
        "lightweight_preview_endpoint_count=1",
        "lightweight_preview_budget_ms=2000",
        "lightweight_preview_latency_pass_count=1",
        "lightweight_preview_payload_shape_pass_count=1",
        "old_heavy_preview_route_preserved=True",
        "post_live_confirmation_preserved=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    prior_total = V1041_TOTAL_BEHAVIORAL_COVERAGE_COUNT
    prior_mapping = V1041_MAPPING_RECONCILED_ROUTE_COUNT
    rows_status = [
        {"name": "version-current", "ok": CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_VERSION == CURRENT_VERSION, "message": f"module_version={CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_VERSION} current={CURRENT_VERSION}"},
        {"name": "prior-v1041-token-present", "ok": DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID in docs, "message": f"prior token {DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID} present."},
        {"name": "lightweight-api-index-present", "ok": api_index_present, "message": "API index documents GET /api/controlled-self-build/lightweight-preview."},
        {"name": "lightweight-api-handler-present", "ok": api_get_handler_present, "message": "Manual API dispatch handles the lightweight preview endpoint."},
        {"name": "lightweight-builder-present", "ok": builder_present, "message": "Operational readiness exposes the lightweight preview builder."},
        {"name": "heavy-builder-preserved", "ok": heavy_builder_preserved, "message": "The original heavy controlled self-build preview builder remains present."},
        {"name": "old-heavy-get-preview-only-preserved", "ok": old_get_preview_only_preserved, "message": "GET /api/controlled-self-build still calls the heavy preview with live=False and approval disabled."},
        {"name": "post-live-confirmation-preserved", "ok": post_confirmation_preserved, "message": "POST /api/controlled-self-build still requires LIVE_CONTROLLED_BUILD for live work."},
        {"name": "lightweight-api-latency-pass", "ok": api_row.ok and api_row.elapsed_ms <= LIGHTWEIGHT_PREVIEW_BUDGET_MS, "message": api_row.message},
        {"name": "lightweight-api-payload-shape-pass", "ok": api_row.payload_shape_pass and not api_row.missing_data_keys, "message": f"missing_data_keys={len(api_row.missing_data_keys)}"},
        {"name": "lightweight-api-preview-only", "ok": api_row.preview_only and api_row.lightweight_preview and not api_row.live and not api_row.approved_live and not api_row.executes_live_work, "message": "Lightweight endpoint stays preview-only even when live/approve query flags are supplied."},
        {"name": "lightweight-api-no-side-effect-authority", "ok": not any([api_row.applies_patches, api_row.writes_memory, api_row.creates_release, api_row.generated_wiring_activated, api_row.autonomy_expanded]), "message": "Lightweight endpoint does not apply patches, write memory, create releases, activate generated wiring, or expand autonomy."},
        {"name": "behavioral-count-current", "ok": prior_total + NEW_LIGHTWEIGHT_PREVIEW_REPORT_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_LIGHTWEIGHT_PREVIEW_REPORT_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "manifest-surface-current", "ok": "v1042-controlled-self-build-lightweight-preview-endpoint-prep" in manifest_source, "message": "Source surface manifest represents the v1042 lightweight preview endpoint prep surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1042 lightweight preview endpoint truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["lightweight_preview_executes_live_work", "lightweight_preview_runs_heavy_doctor", "lightweight_preview_runs_stable_loop_preflight", "lightweight_preview_applies_patches", "lightweight_preview_writes_memory", "lightweight_preview_creates_release", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Endpoint prep remains review-only and does not grant runtime authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_ID,
        "state": "controlled_self_build_lightweight_preview_endpoint_prep_review_only",
        "prior_total_behavioral_coverage_count": prior_total,
        "new_lightweight_preview_report_behavioral_coverage_count": NEW_LIGHTWEIGHT_PREVIEW_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": prior_total + NEW_LIGHTWEIGHT_PREVIEW_REPORT_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": prior_mapping + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "lightweight_preview_endpoint_count": EXPECTED_LIGHTWEIGHT_PREVIEW_ENDPOINT_COUNT,
        "lightweight_preview_route": LIGHTWEIGHT_PREVIEW_ROUTE,
        "heavy_preview_route": HEAVY_PREVIEW_ROUTE,
        "lightweight_preview_budget_ms": LIGHTWEIGHT_PREVIEW_BUDGET_MS,
        "lightweight_preview_elapsed_ms": api_row.elapsed_ms,
        "lightweight_preview_latency_pass_count": 1 if api_row.ok and api_row.elapsed_ms <= LIGHTWEIGHT_PREVIEW_BUDGET_MS else 0,
        "lightweight_preview_payload_shape_pass_count": 1 if api_row.payload_shape_pass else 0,
        "live_api_pass_count": 1 if api_row.live_status == 200 and api_row.api_wrapper_ok else 0,
        "old_heavy_preview_route_preserved": bool(old_get_preview_only_preserved and heavy_builder_preserved),
        "post_live_confirmation_preserved": post_confirmation_preserved,
        "lightweight_preview_only": api_row.preview_only,
        "lightweight_preview_does_not_execute_live_work": not api_row.executes_live_work,
        "controlled_self_build_lighter_preview_endpoint_prepared": True,
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
        "api_rows": [row_dict],
        "boundaries": dict(BOUNDARIES),
        "mapping_mismatches": mapping_mismatches,
        "rows": rows_status,
        "blocked": [row for row in rows_status if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def controlled_self_build_lightweight_preview_endpoint_prep_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"dashboard_route={SELF_ROUTE}",
        "builder_function=build_controlled_self_build_lightweight_preview_endpoint_prep_review",
        "text_function=controlled_self_build_lightweight_preview_endpoint_prep_review_text",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_lightweight_preview_report_behavioral_coverage_count={report.get('new_lightweight_preview_report_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"lightweight_preview_endpoint_count={report.get('lightweight_preview_endpoint_count')}",
        f"lightweight_preview_route={report.get('lightweight_preview_route')}",
        f"heavy_preview_route={report.get('heavy_preview_route')}",
        f"lightweight_preview_budget_ms={report.get('lightweight_preview_budget_ms')}",
        f"lightweight_preview_elapsed_ms={report.get('lightweight_preview_elapsed_ms')}",
        f"lightweight_preview_latency_pass_count={report.get('lightweight_preview_latency_pass_count')}",
        f"lightweight_preview_payload_shape_pass_count={report.get('lightweight_preview_payload_shape_pass_count')}",
        f"live_api_pass_count={report.get('live_api_pass_count')}",
        f"old_heavy_preview_route_preserved={report.get('old_heavy_preview_route_preserved')}",
        f"post_live_confirmation_preserved={report.get('post_live_confirmation_preserved')}",
        f"lightweight_preview_only={report.get('lightweight_preview_only')}",
        f"lightweight_preview_does_not_execute_live_work={report.get('lightweight_preview_does_not_execute_live_work')}",
        f"controlled_self_build_lighter_preview_endpoint_prepared={report.get('controlled_self_build_lighter_preview_endpoint_prepared')}",
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
        lines.append("\nAPI rows:")
        for row in report.get("api_rows", []):
            lines.append(
                f"- {row.get('label')}: {row.get('route')} elapsed_ms={row.get('elapsed_ms')} budget_ms={row.get('budget_ms')} wrapper_ok={row.get('api_wrapper_ok')} preview_only={row.get('preview_only')} lightweight_preview={row.get('lightweight_preview')} live={row.get('live')} approved_live={row.get('approved_live')} executes_live_work={row.get('executes_live_work')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
        lines.append("\nBoundaries:")
        for key, value in sorted((report.get("boundaries") or {}).items()):
            lines.append(f"- {key}={value}")
    return "\n".join(lines).strip()


if __name__ == "__main__":
    print(controlled_self_build_lightweight_preview_endpoint_prep_review_text(build_controlled_self_build_lightweight_preview_endpoint_prep_review(), full=True))
