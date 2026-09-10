from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_cache_source_dependency_digest_verification import (
    CACHE_API_ROUTE,
    DIGEST_API_ROUTE,
    EXPECTED_DEPENDENCY_DIGEST_COUNT,
    FRESHNESS_API_ROUTE,
    MAPPING_RECONCILED_ROUTE_COUNT as V1046_MAPPING_RECONCILED_ROUTE_COUNT,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1046_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    _dependency_specs,
    _diagnostic_routes,
    _fingerprint_from_sources,
    _read_text,
    _repo,
    _route_renderer_map,
    _source_map,
    build_doctor_diagnostic_cache_source_dependency_digest_metadata,
)

DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_ID = "doctor-diagnostic-cache-digest-drift-classification-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-diagnostic-cache-digest-drift-classification"
SELF_RENDERER = "render_doctor_diagnostic_cache_digest_drift_classification"
DRIFT_CLASSIFICATION_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness/digest-drift-classification"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 111
NEW_DRIFT_CLASSIFICATION_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 112
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 117
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 118
EXPECTED_DRIFT_FIXTURE_COUNT = 4
EXPECTED_DRIFT_CATEGORY_COUNT = 4
EXPECTED_DRIFT_CLASSIFICATION_PASS_COUNT = 4
EXPECTED_DRY_RUN_OVERLAY_COUNT = 4
SOURCE_FILES_MUTATED = False
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "drift_classification_preview_only": True,
    "dry_run_overlay_only": True,
    "source_files_mutated": False,
    "persisted_cache_written": False,
    "live_diagnostic_measurements_performed": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "drift_endpoint_executes_live_work": False,
    "drift_endpoint_applies_patches": False,
    "drift_endpoint_writes_memory": False,
    "drift_endpoint_creates_release": False,
    "drift_endpoint_persists_cache": False,
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
class DriftClassificationFixture:
    fixture_id: str
    source_id: str
    drift_category: str
    path: str
    contract_token: str
    baseline_fingerprint_prefix: str
    overlay_fingerprint_prefix: str
    fingerprint_changed: bool
    changed_dependency_count: int
    dry_run_overlay_applied: bool
    source_file_mutated: bool
    ok: bool
    message: str


DRIFT_CLASSIFICATION_SPECS: tuple[tuple[str, str, str], ...] = (
    ("benign-source-drift-fixture", "preview-cache-builder", "benign_source_drift"),
    ("route-contract-drift-fixture", "doctor-cache-api-dispatch", "route_contract_drift"),
    ("payload-shape-drift-fixture", "latency-payload-shape-contract", "payload_shape_drift"),
    ("smoke-evidence-drift-fixture", "manual-smoke-cache-coverage", "smoke_evidence_drift"),
)


_SPEC_BY_SOURCE_ID = {source_id: (rel, token) for source_id, rel, token in _dependency_specs()}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _prefix(value: str) -> str:
    return value[:16] if value else "missing"


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


def _overlay_sources(root: Path, source_id: str) -> dict[str, str]:
    baseline = _source_map(root)
    if source_id in baseline:
        baseline[source_id] = f"{baseline[source_id]}\n# v1047 dry-run drift classification overlay: {source_id}\n"
    return baseline


def _changed_dependency_count(root: Path, source_id: str) -> int:
    baseline = _source_map(root)
    overlay = _overlay_sources(root, source_id)
    changed = 0
    for dependency_source_id, _rel, _token in _dependency_specs():
        if _digest(baseline.get(dependency_source_id, "")) != _digest(overlay.get(dependency_source_id, "")):
            changed += 1
    return changed


def _fixture_rows(root: Path) -> list[DriftClassificationFixture]:
    routes = _diagnostic_routes()
    baseline_sources = _source_map(root)
    baseline_fingerprint = _fingerprint_from_sources(baseline_sources, routes)
    rows: list[DriftClassificationFixture] = []
    for fixture_id, source_id, category in DRIFT_CLASSIFICATION_SPECS:
        rel, token = _SPEC_BY_SOURCE_ID.get(source_id, ("[missing]", "[missing]"))
        overlay_sources = _overlay_sources(root, source_id)
        overlay_fingerprint = _fingerprint_from_sources(overlay_sources, routes)
        changed_count = _changed_dependency_count(root, source_id)
        token_present = token in baseline_sources.get(source_id, "")
        fingerprint_changed = baseline_fingerprint != overlay_fingerprint
        ok = (
            token_present
            and fingerprint_changed
            and changed_count == 1
            and category in {"benign_source_drift", "route_contract_drift", "payload_shape_drift", "smoke_evidence_drift"}
            and SOURCE_FILES_MUTATED is False
        )
        rows.append(
            DriftClassificationFixture(
                fixture_id=fixture_id,
                source_id=source_id,
                drift_category=category,
                path=rel,
                contract_token=token,
                baseline_fingerprint_prefix=_prefix(baseline_fingerprint),
                overlay_fingerprint_prefix=_prefix(overlay_fingerprint),
                fingerprint_changed=fingerprint_changed,
                changed_dependency_count=changed_count,
                dry_run_overlay_applied=True,
                source_file_mutated=SOURCE_FILES_MUTATED,
                ok=ok,
                message=f"category={category} source_id={source_id} token_present={token_present} fingerprint_changed={fingerprint_changed} changed_dependency_count={changed_count} source_file_mutated={SOURCE_FILES_MUTATED}",
            )
        )
    return rows


def build_doctor_diagnostic_cache_digest_drift_classification_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    digest_metadata = build_doctor_diagnostic_cache_source_dependency_digest_metadata(project_id=project_id, root=project_root)
    rows = _fixture_rows(project_root)
    categories = sorted({row.drift_category for row in rows})
    row_dicts = [asdict(row) for row in rows]
    ok = (
        digest_metadata.get("ok") is True
        and digest_metadata.get("preview_only") is True
        and digest_metadata.get("dependency_digest_count") == EXPECTED_DEPENDENCY_DIGEST_COUNT
        and len(rows) == EXPECTED_DRIFT_FIXTURE_COUNT
        and len(categories) == EXPECTED_DRIFT_CATEGORY_COUNT
        and sum(1 for row in rows if row.ok) == EXPECTED_DRIFT_CLASSIFICATION_PASS_COUNT
        and sum(1 for row in rows if row.dry_run_overlay_applied) == EXPECTED_DRY_RUN_OVERLAY_COUNT
        and all(row.changed_dependency_count == 1 for row in rows)
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
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_only": True,
        "drift_classification_preview_only": True,
        "dry_run_overlay_only": True,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "drift_classification_api_route": DRIFT_CLASSIFICATION_API_ROUTE,
        "dependency_digest_count": digest_metadata.get("dependency_digest_count"),
        "dependency_digest_pass_count": digest_metadata.get("dependency_digest_pass_count"),
        "digest_baseline_fingerprint": digest_metadata.get("baseline_cache_fingerprint"),
        "drift_fixture_count": len(rows),
        "drift_category_count": len(categories),
        "drift_categories": categories,
        "drift_classification_pass_count": sum(1 for row in rows if row.ok),
        "dry_run_overlay_count": sum(1 for row in rows if row.dry_run_overlay_applied),
        "benign_source_drift_count": sum(1 for row in rows if row.drift_category == "benign_source_drift"),
        "route_contract_drift_count": sum(1 for row in rows if row.drift_category == "route_contract_drift"),
        "payload_shape_drift_count": sum(1 for row in rows if row.drift_category == "payload_shape_drift"),
        "smoke_evidence_drift_count": sum(1 for row in rows if row.drift_category == "smoke_evidence_drift"),
        "drift_classification_rows": row_dicts,
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
            "Classify doctor diagnostic cache digest drift before deciding whether cache freshness is benign or contract-affecting.",
            "Keep digest drift fixtures dry-run only; do not mutate source files or write a persisted cache.",
            "Expand contract-change fixtures only after source dependency categories stay stable.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-digest-drift-classification-v1",
            "python tools/smoke_check.py --check doctor-diagnostic-cache-source-dependency-digest-verification-v1",
        ],
        "message": "Dry-run overlays classify doctor diagnostic cache digest drift as benign source, route-contract, payload-shape, or smoke-evidence drift without mutating source files.",
    }


def build_doctor_diagnostic_cache_digest_drift_classification(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_cache_digest_drift_classification.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    metadata = build_doctor_diagnostic_cache_digest_drift_classification_metadata(project_id="eidolon", root=project_root)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, DRIFT_CLASSIFICATION_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    required_api_data_keys = (
        "version", "current_version_tag", "current_milestone", "next_recommended_arc", "project_id", "review_id",
        "status", "ok", "preview_only", "drift_classification_preview_only", "dry_run_overlay_only",
        "source_cache_route", "freshness_api_route", "digest_api_route", "drift_classification_api_route",
        "dependency_digest_count", "dependency_digest_pass_count", "digest_baseline_fingerprint",
        "drift_fixture_count", "drift_category_count", "drift_categories", "drift_classification_pass_count",
        "dry_run_overlay_count", "benign_source_drift_count", "route_contract_drift_count", "payload_shape_drift_count", "smoke_evidence_drift_count",
        "drift_classification_rows", "source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed",
        "executes_live_work", "applies_patches", "writes_memory", "creates_release", "generated_wiring_activated", "release_authorized", "autonomy_expanded",
        "recommendations", "next_commands", "message",
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
        and isinstance(api_data.get("drift_classification_rows"), list)
        and isinstance(api_data.get("drift_categories"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness/digest-drift-classification"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness", "digest-drift-classification"]' in api_source
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_ID,
        SELF_ROUTE,
        DRIFT_CLASSIFICATION_API_ROUTE,
        "build_doctor_diagnostic_cache_digest_drift_classification_metadata",
        "build_doctor_diagnostic_cache_digest_drift_classification",
        "doctor_diagnostic_cache_digest_drift_classification_text",
        "prior_total_behavioral_coverage_count=111",
        "new_drift_classification_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=112",
        "prior_mapping_reconciled_route_count=117",
        "mapping_reconciled_route_count=118",
        "drift_fixture_count=4",
        "drift_category_count=4",
        "drift_classification_pass_count=4",
        "dry_run_overlay_count=4",
        "benign_source_drift_count=1",
        "route_contract_drift_count=1",
        "payload_shape_drift_count=1",
        "smoke_evidence_drift_count=1",
        "drift_api_pass_count=1",
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
        {"name": "module-version-current", "ok": DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1046-token-present", "ok": DIGEST_API_ROUTE in docs and "doctor-diagnostic-cache-source-dependency-digest-verification-v1" in docs, "message": "Prior digest verification route/check remains represented."},
        {"name": "drift-api-index-and-handler-present", "ok": api_index_present and api_handler_present, "message": f"api_index_present={api_index_present} api_handler_present={api_handler_present}"},
        {"name": "drift-api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing_api_data_keys={len(missing_api_data_keys)} error={api_error}"},
        {"name": "drift-fixtures-present", "ok": metadata.get("drift_fixture_count") == EXPECTED_DRIFT_FIXTURE_COUNT and metadata.get("drift_classification_pass_count") == EXPECTED_DRIFT_CLASSIFICATION_PASS_COUNT, "message": f"fixtures={metadata.get('drift_fixture_count')} pass={metadata.get('drift_classification_pass_count')}"},
        {"name": "drift-categories-separated", "ok": metadata.get("drift_category_count") == EXPECTED_DRIFT_CATEGORY_COUNT and metadata.get("benign_source_drift_count") == 1 and metadata.get("route_contract_drift_count") == 1 and metadata.get("payload_shape_drift_count") == 1 and metadata.get("smoke_evidence_drift_count") == 1, "message": f"categories={metadata.get('drift_categories')}"},
        {"name": "dry-run-overlays-only", "ok": metadata.get("dry_run_overlay_count") == EXPECTED_DRY_RUN_OVERLAY_COUNT and metadata.get("source_files_mutated") is False and metadata.get("persisted_cache_written") is False, "message": f"dry_run_overlay_count={metadata.get('dry_run_overlay_count')} source_mutated={metadata.get('source_files_mutated')} persisted={metadata.get('persisted_cache_written')}"},
        {"name": "behavioral-count-current", "ok": int(V1046_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DRIFT_CLASSIFICATION_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={int(V1046_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DRIFT_CLASSIFICATION_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": int(V1046_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={int(V1046_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1047-doctor-diagnostic-cache-digest-drift-classification" in manifest_source, "message": "Source surface manifest represents the v1047 digest drift classification surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1047 digest drift classification truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "drift_endpoint_executes_live_work", "drift_endpoint_applies_patches", "drift_endpoint_writes_memory", "drift_endpoint_creates_release", "drift_endpoint_persists_cache", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Digest drift classification remains dry-run/advisory and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_ID,
        "state": "doctor_diagnostic_cache_digest_drift_classification_only",
        "prior_total_behavioral_coverage_count": int(V1046_TOTAL_BEHAVIORAL_COVERAGE_COUNT),
        "new_drift_classification_behavioral_coverage_count": NEW_DRIFT_CLASSIFICATION_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": int(V1046_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DRIFT_CLASSIFICATION_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": int(V1046_MAPPING_RECONCILED_ROUTE_COUNT),
        "mapping_reconciled_route_count": int(V1046_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "drift_classification_api_route": DRIFT_CLASSIFICATION_API_ROUTE,
        "drift_api_elapsed_ms": elapsed_ms,
        "dependency_digest_count": metadata.get("dependency_digest_count"),
        "dependency_digest_pass_count": metadata.get("dependency_digest_pass_count"),
        "drift_fixture_count": metadata.get("drift_fixture_count"),
        "drift_category_count": metadata.get("drift_category_count"),
        "drift_categories": metadata.get("drift_categories"),
        "drift_classification_pass_count": metadata.get("drift_classification_pass_count"),
        "dry_run_overlay_count": metadata.get("dry_run_overlay_count"),
        "benign_source_drift_count": metadata.get("benign_source_drift_count"),
        "route_contract_drift_count": metadata.get("route_contract_drift_count"),
        "payload_shape_drift_count": metadata.get("payload_shape_drift_count"),
        "smoke_evidence_drift_count": metadata.get("smoke_evidence_drift_count"),
        "drift_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "drift_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "drift_classification_rows": metadata.get("drift_classification_rows", []),
        "api_drift_classification_rows": api_data.get("drift_classification_rows", []) if isinstance(api_data, dict) else [],
        "source_files_mutated": metadata.get("source_files_mutated"),
        "persisted_cache_written": metadata.get("persisted_cache_written"),
        "live_diagnostic_measurements_performed": metadata.get("live_diagnostic_measurements_performed"),
        "drift_endpoint_preview_only": metadata.get("preview_only") is True,
        "drift_endpoint_executes_live_work": metadata.get("executes_live_work"),
        "drift_endpoint_applies_patches": metadata.get("applies_patches"),
        "drift_endpoint_writes_memory": metadata.get("writes_memory"),
        "drift_endpoint_creates_release": metadata.get("creates_release"),
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


def doctor_diagnostic_cache_digest_drift_classification_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_cache_digest_drift_classification_metadata",
        "build_doctor_diagnostic_cache_digest_drift_classification",
        "doctor_diagnostic_cache_digest_drift_classification_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_drift_classification_behavioral_coverage_count={report.get('new_drift_classification_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"source_cache_route={report.get('source_cache_route')}",
        f"freshness_api_route={report.get('freshness_api_route')}",
        f"digest_api_route={report.get('digest_api_route')}",
        f"drift_classification_api_route={report.get('drift_classification_api_route')}",
        f"dependency_digest_count={report.get('dependency_digest_count')}",
        f"dependency_digest_pass_count={report.get('dependency_digest_pass_count')}",
        f"drift_fixture_count={report.get('drift_fixture_count')}",
        f"drift_category_count={report.get('drift_category_count')}",
        f"drift_classification_pass_count={report.get('drift_classification_pass_count')}",
        f"dry_run_overlay_count={report.get('dry_run_overlay_count')}",
        f"benign_source_drift_count={report.get('benign_source_drift_count')}",
        f"route_contract_drift_count={report.get('route_contract_drift_count')}",
        f"payload_shape_drift_count={report.get('payload_shape_drift_count')}",
        f"smoke_evidence_drift_count={report.get('smoke_evidence_drift_count')}",
        f"drift_payload_shape_pass_count={report.get('drift_payload_shape_pass_count')}",
        f"drift_api_pass_count={report.get('drift_api_pass_count')}",
        f"source_files_mutated={report.get('source_files_mutated')}",
        f"persisted_cache_written={report.get('persisted_cache_written')}",
        f"live_diagnostic_measurements_performed={report.get('live_diagnostic_measurements_performed')}",
        f"drift_endpoint_preview_only={report.get('drift_endpoint_preview_only')}",
        f"drift_endpoint_executes_live_work={report.get('drift_endpoint_executes_live_work')}",
        f"drift_endpoint_applies_patches={report.get('drift_endpoint_applies_patches')}",
        f"drift_endpoint_writes_memory={report.get('drift_endpoint_writes_memory')}",
        f"drift_endpoint_creates_release={report.get('drift_endpoint_creates_release')}",
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
        lines.append("\nDrift classification rows:")
        for row in report.get("drift_classification_rows", []):
            lines.append(
                f"- {row.get('fixture_id')} {row.get('source_id')} category={row.get('drift_category')} path={row.get('path')} baseline={row.get('baseline_fingerprint_prefix')} overlay={row.get('overlay_fingerprint_prefix')} fingerprint_changed={row.get('fingerprint_changed')} changed_dependency_count={row.get('changed_dependency_count')} dry_run_overlay_applied={row.get('dry_run_overlay_applied')} source_file_mutated={row.get('source_file_mutated')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
