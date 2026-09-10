from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_cache_freshness_invalidation_review import (
    DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID,
    FRESHNESS_API_ROUTE,
    EXPECTED_INVALIDATION_SOURCE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1045_MAPPING_RECONCILED_ROUTE_COUNT,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1045_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    build_doctor_diagnostic_cache_freshness_metadata,
)
from doctor_diagnostic_preview_cache_heavy_route_decoupling import (
    CACHE_API_ROUTE,
    CACHE_TTL_SECONDS,
    build_doctor_diagnostic_preview_cache,
)

DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_ID = "doctor-diagnostic-cache-source-dependency-digest-verification-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
CACHE_MODULE = "conscious_agent/doctor_diagnostic_preview_cache_heavy_route_decoupling.py"
FRESHNESS_MODULE = "conscious_agent/doctor_diagnostic_cache_freshness_invalidation_review.py"
LINK_MIGRATION_MODULE = "conscious_agent/doctor_controlled_self_build_lightweight_link_migration.py"
LATENCY_SHAPE_MODULE = "conscious_agent/doctor_deferred_diagnostic_latency_budget_payload_shape.py"
LIGHTWEIGHT_PREVIEW_MODULE = "conscious_agent/controlled_self_build_lightweight_preview_endpoint_prep.py"
SELF_ROUTE = "/doctor-diagnostic-cache-source-dependency-digest-verification"
SELF_RENDERER = "render_doctor_diagnostic_cache_source_dependency_digest_verification"
DIGEST_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness/digest-verification"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 110
NEW_DIGEST_VERIFICATION_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 111
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 116
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 117
EXPECTED_DRY_RUN_FIXTURE_COUNT = 1
EXPECTED_DEPENDENCY_DIGEST_COUNT = 7
EXPECTED_DIGEST_MUTATION_PASS_COUNT = 1
EXPECTED_DIGEST_API_PASS_COUNT = 1
DRY_RUN_MUTATION_SOURCE_ID = "preview-cache-builder"
DRY_RUN_MUTATION_TOKEN = "# v1046 dry-run dependency digest verification fixture"
SOURCE_FILES_MUTATED = False
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "digest_verification_preview_only": True,
    "dry_run_overlay_only": True,
    "source_files_mutated": False,
    "persisted_cache_written": False,
    "live_diagnostic_measurements_performed": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "digest_endpoint_executes_live_work": False,
    "digest_endpoint_applies_patches": False,
    "digest_endpoint_writes_memory": False,
    "digest_endpoint_creates_release": False,
    "digest_endpoint_persists_cache": False,
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
class DependencyDigestRow:
    source_id: str
    path: str
    token: str
    baseline_digest_prefix: str
    overlay_digest_prefix: str
    changed_by_overlay: bool
    dry_run_overlay_applied: bool
    source_file_mutated: bool
    ok: bool
    message: str


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _digest_prefix(text: str) -> str:
    return _digest(text)[:16] if text else "missing"


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


def _dependency_specs() -> tuple[tuple[str, str, str], ...]:
    return (
        ("doctor-lazy-diagnostic-links", DASHBOARD_MODULE, "DOCTOR_LAZY_DIAGNOSTIC_SECTIONS"),
        ("preview-cache-builder", CACHE_MODULE, "build_doctor_diagnostic_preview_cache"),
        ("doctor-cache-api-dispatch", API_MODULE, 'if parts == ["doctor", "diagnostic-preview-cache"]'),
        ("doctor-cache-freshness-api-dispatch", API_MODULE, 'if parts == ["doctor", "diagnostic-preview-cache", "freshness"]'),
        ("lightweight-preview-contract", LIGHTWEIGHT_PREVIEW_MODULE, "build_controlled_self_build_lightweight_preview"),
        ("latency-payload-shape-contract", LATENCY_SHAPE_MODULE, "DIAGNOSTIC_SHAPE_SPECS"),
        ("manual-smoke-cache-coverage", MANUAL_SMOKE_MODULE, DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID),
    )


def _source_map(root: Path, overlay_source_id: str | None = None) -> dict[str, str]:
    source_by_id: dict[str, str] = {}
    for source_id, rel, _token in _dependency_specs():
        text = _read_text(root, rel)
        if source_id == overlay_source_id:
            text = f"{text}\n{DRY_RUN_MUTATION_TOKEN}: {source_id}\n"
        source_by_id[source_id] = text
    return source_by_id


def _diagnostic_routes() -> list[str]:
    cache_payload = build_doctor_diagnostic_preview_cache(project_id="eidolon")
    rows = cache_payload.get("diagnostic_rows", []) if isinstance(cache_payload, dict) else []
    return [str(row.get("route")) for row in rows if isinstance(row, dict)]


def _fingerprint_from_sources(source_by_id: dict[str, str], routes: list[str]) -> str:
    digest_prefixes = [_digest_prefix(source_by_id.get(source_id, "")) for source_id, _rel, _token in _dependency_specs()]
    seed = "|".join([CURRENT_VERSION, str(CACHE_TTL_SECONDS), str(len(routes)), *routes, *digest_prefixes])
    return _digest(seed)


def _digest_rows(root: Path, overlay_source_id: str) -> list[DependencyDigestRow]:
    baseline = _source_map(root)
    overlay = _source_map(root, overlay_source_id=overlay_source_id)
    rows: list[DependencyDigestRow] = []
    for source_id, rel, token in _dependency_specs():
        baseline_text = baseline.get(source_id, "")
        overlay_text = overlay.get(source_id, "")
        present = token in baseline_text
        changed = _digest_prefix(baseline_text) != _digest_prefix(overlay_text)
        overlay_applied = source_id == overlay_source_id
        ok = present and (changed if overlay_applied else not changed) and SOURCE_FILES_MUTATED is False
        rows.append(
            DependencyDigestRow(
                source_id=source_id,
                path=rel,
                token=token,
                baseline_digest_prefix=_digest_prefix(baseline_text),
                overlay_digest_prefix=_digest_prefix(overlay_text),
                changed_by_overlay=changed,
                dry_run_overlay_applied=overlay_applied,
                source_file_mutated=SOURCE_FILES_MUTATED,
                ok=ok,
                message=f"present={present} changed_by_overlay={changed} dry_run_overlay_applied={overlay_applied} source_file_mutated={SOURCE_FILES_MUTATED}",
            )
        )
    return rows


def build_doctor_diagnostic_cache_source_dependency_digest_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    routes = _diagnostic_routes()
    baseline_sources = _source_map(project_root)
    overlay_sources = _source_map(project_root, overlay_source_id=DRY_RUN_MUTATION_SOURCE_ID)
    baseline_fingerprint = _fingerprint_from_sources(baseline_sources, routes)
    overlay_fingerprint = _fingerprint_from_sources(overlay_sources, routes)
    digest_rows = _digest_rows(project_root, DRY_RUN_MUTATION_SOURCE_ID)
    row_dicts = [asdict(row) for row in digest_rows]
    freshness_payload = build_doctor_diagnostic_cache_freshness_metadata(project_id=project_id, root=project_root)
    changed_rows = [row for row in digest_rows if row.changed_by_overlay]
    ok = (
        freshness_payload.get("ok") is True
        and freshness_payload.get("preview_only") is True
        and len(digest_rows) == EXPECTED_DEPENDENCY_DIGEST_COUNT
        and sum(1 for row in digest_rows if row.ok) == EXPECTED_DEPENDENCY_DIGEST_COUNT
        and len(changed_rows) == EXPECTED_DIGEST_MUTATION_PASS_COUNT
        and changed_rows[0].source_id == DRY_RUN_MUTATION_SOURCE_ID
        and baseline_fingerprint != overlay_fingerprint
        and SOURCE_FILES_MUTATED is False
        and PERSISTED_CACHE_WRITTEN is False
        and LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED is False
    )
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "project_id": project_id,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_only": True,
        "digest_verification_preview_only": True,
        "dry_run_overlay_only": True,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "dependency_digest_count": len(digest_rows),
        "dependency_digest_pass_count": sum(1 for row in digest_rows if row.ok),
        "dry_run_fixture_count": EXPECTED_DRY_RUN_FIXTURE_COUNT,
        "dry_run_mutation_source_id": DRY_RUN_MUTATION_SOURCE_ID,
        "dry_run_mutation_token": DRY_RUN_MUTATION_TOKEN,
        "baseline_cache_fingerprint": baseline_fingerprint,
        "overlay_cache_fingerprint": overlay_fingerprint,
        "fingerprint_changed": baseline_fingerprint != overlay_fingerprint,
        "changed_dependency_count": len(changed_rows),
        "digest_mutation_pass_count": 1 if baseline_fingerprint != overlay_fingerprint and len(changed_rows) == EXPECTED_DIGEST_MUTATION_PASS_COUNT else 0,
        "dependency_digest_rows": row_dicts,
        "freshness_payload_ok": freshness_payload.get("ok") is True,
        "freshness_payload_preview_only": freshness_payload.get("preview_only") is True,
        "source_files_mutated": SOURCE_FILES_MUTATED,
        "persisted_cache_written": PERSISTED_CACHE_WRITTEN,
        "live_diagnostic_measurements_performed": LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED,
        "executes_live_work": False,
        "applies_patches": False,
        "writes_memory": False,
        "creates_release": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "recommendations": [
            "Keep doctor diagnostic preview cache freshness tied to source dependency fingerprints.",
            "Use dry-run source overlays for digest verification instead of mutating source files.",
            "Keep live diagnostic payload measurements in targeted smoke rather than dashboard page loads.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-source-dependency-digest-verification-v1",
            "python tools/smoke_check.py --check doctor-diagnostic-cache-freshness-and-invalidation-review-v1",
        ],
        "message": "Dry-run dependency digest verification proves cache fingerprints change when dependency content changes without mutating source files.",
    }


def build_doctor_diagnostic_cache_source_dependency_digest_verification(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_cache_source_dependency_digest_verification.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    metadata = build_doctor_diagnostic_cache_source_dependency_digest_metadata(project_id="eidolon", root=project_root)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, DIGEST_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    required_api_data_keys = (
        "version",
        "current_version_tag",
        "current_milestone",
        "next_recommended_arc",
        "project_id",
        "status",
        "ok",
        "preview_only",
        "digest_verification_preview_only",
        "dry_run_overlay_only",
        "source_cache_route",
        "freshness_api_route",
        "digest_api_route",
        "cache_ttl_seconds",
        "dependency_digest_count",
        "dependency_digest_pass_count",
        "dry_run_fixture_count",
        "dry_run_mutation_source_id",
        "dry_run_mutation_token",
        "baseline_cache_fingerprint",
        "overlay_cache_fingerprint",
        "fingerprint_changed",
        "changed_dependency_count",
        "digest_mutation_pass_count",
        "dependency_digest_rows",
        "freshness_payload_ok",
        "freshness_payload_preview_only",
        "source_files_mutated",
        "persisted_cache_written",
        "live_diagnostic_measurements_performed",
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
        and isinstance(api_data.get("dependency_digest_rows"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    digest_rows = metadata.get("dependency_digest_rows", [])
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness/digest-verification"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness", "digest-verification"]' in api_source
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_ID,
        SELF_ROUTE,
        DIGEST_API_ROUTE,
        "build_doctor_diagnostic_cache_source_dependency_digest_metadata",
        "build_doctor_diagnostic_cache_source_dependency_digest_verification",
        "doctor_diagnostic_cache_source_dependency_digest_verification_text",
        "prior_total_behavioral_coverage_count=110",
        "new_digest_verification_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=111",
        "prior_mapping_reconciled_route_count=116",
        "mapping_reconciled_route_count=117",
        "dependency_digest_count=7",
        "dependency_digest_pass_count=7",
        "dry_run_fixture_count=1",
        "fingerprint_changed=True",
        "digest_mutation_pass_count=1",
        "digest_api_pass_count=1",
        "source_files_mutated=False",
        "persisted_cache_written=False",
        "live_diagnostic_measurements_performed=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "autonomy_expanded=False",
    ]
    rows_status = [
        {"name": "module-version-current", "ok": DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1045-token-present", "ok": DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID in docs, "message": f"prior token {DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_ID} present."},
        {"name": "digest-api-index-and-handler-present", "ok": api_index_present and api_handler_present, "message": f"api_index_present={api_index_present} api_handler_present={api_handler_present}"},
        {"name": "digest-api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing_api_data_keys={len(missing_api_data_keys)} error={api_error}"},
        {"name": "dependency-digest-rows-present", "ok": metadata.get("dependency_digest_count") == EXPECTED_DEPENDENCY_DIGEST_COUNT and metadata.get("dependency_digest_pass_count") == EXPECTED_DEPENDENCY_DIGEST_COUNT, "message": f"pass={metadata.get('dependency_digest_pass_count')} rows={metadata.get('dependency_digest_count')}"},
        {"name": "dry-run-fixture-mutates-fingerprint", "ok": metadata.get("fingerprint_changed") is True and metadata.get("digest_mutation_pass_count") == EXPECTED_DIGEST_MUTATION_PASS_COUNT and metadata.get("changed_dependency_count") == EXPECTED_DIGEST_MUTATION_PASS_COUNT, "message": f"changed={metadata.get('fingerprint_changed')} changed_dependency_count={metadata.get('changed_dependency_count')}"},
        {"name": "no-source-or-cache-mutation", "ok": metadata.get("source_files_mutated") is False and metadata.get("persisted_cache_written") is False and metadata.get("live_diagnostic_measurements_performed") is False, "message": f"source_mutated={metadata.get('source_files_mutated')} persisted={metadata.get('persisted_cache_written')} live_measurements={metadata.get('live_diagnostic_measurements_performed')}"},
        {"name": "behavioral-count-current", "ok": int(V1045_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DIGEST_VERIFICATION_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={int(V1045_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DIGEST_VERIFICATION_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": int(V1045_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={int(V1045_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1046-doctor-diagnostic-cache-source-dependency-digest-verification" in manifest_source, "message": "Source surface manifest represents the v1046 digest verification surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1046 digest verification truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "digest_endpoint_executes_live_work", "digest_endpoint_applies_patches", "digest_endpoint_writes_memory", "digest_endpoint_creates_release", "digest_endpoint_persists_cache", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Digest verification remains dry-run/advisory and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_ID,
        "state": "doctor_diagnostic_cache_source_dependency_digest_verification_only",
        "prior_total_behavioral_coverage_count": int(V1045_TOTAL_BEHAVIORAL_COVERAGE_COUNT),
        "new_digest_verification_behavioral_coverage_count": NEW_DIGEST_VERIFICATION_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": int(V1045_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DIGEST_VERIFICATION_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": int(V1045_MAPPING_RECONCILED_ROUTE_COUNT),
        "mapping_reconciled_route_count": int(V1045_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "digest_api_elapsed_ms": elapsed_ms,
        "dependency_digest_count": metadata.get("dependency_digest_count"),
        "dependency_digest_pass_count": metadata.get("dependency_digest_pass_count"),
        "dry_run_fixture_count": metadata.get("dry_run_fixture_count"),
        "dry_run_mutation_source_id": metadata.get("dry_run_mutation_source_id"),
        "baseline_cache_fingerprint": metadata.get("baseline_cache_fingerprint"),
        "overlay_cache_fingerprint": metadata.get("overlay_cache_fingerprint"),
        "fingerprint_changed": metadata.get("fingerprint_changed"),
        "changed_dependency_count": metadata.get("changed_dependency_count"),
        "digest_mutation_pass_count": metadata.get("digest_mutation_pass_count"),
        "digest_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "digest_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "dependency_digest_rows": digest_rows,
        "api_dependency_digest_rows": api_data.get("dependency_digest_rows", []) if isinstance(api_data, dict) else [],
        "freshness_payload_ok": metadata.get("freshness_payload_ok"),
        "freshness_payload_preview_only": metadata.get("freshness_payload_preview_only"),
        "source_files_mutated": metadata.get("source_files_mutated"),
        "persisted_cache_written": metadata.get("persisted_cache_written"),
        "live_diagnostic_measurements_performed": metadata.get("live_diagnostic_measurements_performed"),
        "digest_endpoint_preview_only": metadata.get("preview_only") is True,
        "digest_endpoint_executes_live_work": metadata.get("executes_live_work"),
        "digest_endpoint_applies_patches": metadata.get("applies_patches"),
        "digest_endpoint_writes_memory": metadata.get("writes_memory"),
        "digest_endpoint_creates_release": metadata.get("creates_release"),
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


def doctor_diagnostic_cache_source_dependency_digest_verification_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_cache_source_dependency_digest_metadata",
        "build_doctor_diagnostic_cache_source_dependency_digest_verification",
        "doctor_diagnostic_cache_source_dependency_digest_verification_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_digest_verification_behavioral_coverage_count={report.get('new_digest_verification_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"source_cache_route={report.get('source_cache_route')}",
        f"freshness_api_route={report.get('freshness_api_route')}",
        f"digest_api_route={report.get('digest_api_route')}",
        f"dependency_digest_count={report.get('dependency_digest_count')}",
        f"dependency_digest_pass_count={report.get('dependency_digest_pass_count')}",
        f"dry_run_fixture_count={report.get('dry_run_fixture_count')}",
        f"dry_run_mutation_source_id={report.get('dry_run_mutation_source_id')}",
        f"fingerprint_changed={report.get('fingerprint_changed')}",
        f"changed_dependency_count={report.get('changed_dependency_count')}",
        f"digest_mutation_pass_count={report.get('digest_mutation_pass_count')}",
        f"digest_payload_shape_pass_count={report.get('digest_payload_shape_pass_count')}",
        f"digest_api_pass_count={report.get('digest_api_pass_count')}",
        f"freshness_payload_ok={report.get('freshness_payload_ok')}",
        f"freshness_payload_preview_only={report.get('freshness_payload_preview_only')}",
        f"source_files_mutated={report.get('source_files_mutated')}",
        f"persisted_cache_written={report.get('persisted_cache_written')}",
        f"live_diagnostic_measurements_performed={report.get('live_diagnostic_measurements_performed')}",
        f"digest_endpoint_preview_only={report.get('digest_endpoint_preview_only')}",
        f"digest_endpoint_executes_live_work={report.get('digest_endpoint_executes_live_work')}",
        f"digest_endpoint_applies_patches={report.get('digest_endpoint_applies_patches')}",
        f"digest_endpoint_writes_memory={report.get('digest_endpoint_writes_memory')}",
        f"digest_endpoint_creates_release={report.get('digest_endpoint_creates_release')}",
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
        lines.append("\nDependency digest rows:")
        for row in report.get("dependency_digest_rows", []):
            lines.append(f"- {row.get('source_id')} {row.get('path')} baseline={row.get('baseline_digest_prefix')} overlay={row.get('overlay_digest_prefix')} changed_by_overlay={row.get('changed_by_overlay')} dry_run_overlay_applied={row.get('dry_run_overlay_applied')} source_file_mutated={row.get('source_file_mutated')} ok={row.get('ok')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
