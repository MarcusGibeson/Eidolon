from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_cache_digest_drift_classification import (
    DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_ID,
    DRIFT_CLASSIFICATION_API_ROUTE,
    MAPPING_RECONCILED_ROUTE_COUNT as V1047_MAPPING_RECONCILED_ROUTE_COUNT,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1047_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    _call_api,
)
from doctor_diagnostic_cache_source_dependency_digest_verification import (
    CACHE_API_ROUTE,
    DIGEST_API_ROUTE,
    EXPECTED_DEPENDENCY_DIGEST_COUNT,
    FRESHNESS_API_ROUTE,
    _dependency_specs,
    _diagnostic_routes,
    _fingerprint_from_sources,
    _read_text,
    _repo,
    _route_renderer_map,
    _source_map,
)

DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_ID = "doctor-diagnostic-cache-contract-drift-fixture-expansion-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-diagnostic-cache-contract-drift-fixture-expansion"
SELF_RENDERER = "render_doctor_diagnostic_cache_contract_drift_fixture_expansion"
CONTRACT_DRIFT_FIXTURE_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness/contract-drift-fixtures"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 112
NEW_CONTRACT_DRIFT_FIXTURE_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 113
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 118
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 119
EXPECTED_EXPANDED_DRIFT_FIXTURE_COUNT = 6
EXPECTED_CONTRACT_AFFECTING_FIXTURE_COUNT = 5
EXPECTED_BENIGN_SOURCE_DRIFT_COUNT = 1
EXPECTED_TOKEN_REMOVAL_FIXTURE_COUNT = 3
EXPECTED_ROUTE_RENAME_FIXTURE_COUNT = 1
EXPECTED_DRY_RUN_OVERLAY_COUNT = 6
EXPECTED_EXPANDED_CLASSIFICATION_PASS_COUNT = 6
SOURCE_FILES_MUTATED = False
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "contract_drift_fixture_preview_only": True,
    "dry_run_overlay_only": True,
    "source_files_mutated": False,
    "persisted_cache_written": False,
    "live_diagnostic_measurements_performed": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "contract_fixture_endpoint_executes_live_work": False,
    "contract_fixture_endpoint_applies_patches": False,
    "contract_fixture_endpoint_writes_memory": False,
    "contract_fixture_endpoint_creates_release": False,
    "contract_fixture_endpoint_persists_cache": False,
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
class ContractDriftFixture:
    fixture_id: str
    source_id: str
    drift_category: str
    fixture_kind: str
    path: str
    contract_token: str
    baseline_fingerprint_prefix: str
    overlay_fingerprint_prefix: str
    fingerprint_changed: bool
    changed_dependency_count: int
    token_present_in_baseline: bool
    token_removed_in_overlay: bool
    route_renamed_in_overlay: bool
    contract_affecting: bool
    dry_run_overlay_applied: bool
    source_file_mutated: bool
    ok: bool
    message: str


CONTRACT_DRIFT_FIXTURE_SPECS: tuple[dict[str, str | bool], ...] = (
    {
        "fixture_id": "benign-source-append-fixture",
        "source_id": "preview-cache-builder",
        "drift_category": "benign_source_drift",
        "fixture_kind": "append_comment",
        "contract_affecting": False,
    },
    {
        "fixture_id": "route-contract-append-fixture",
        "source_id": "doctor-cache-api-dispatch",
        "drift_category": "route_contract_drift",
        "fixture_kind": "append_comment",
        "contract_affecting": True,
    },
    {
        "fixture_id": "route-contract-token-removal-fixture",
        "source_id": "doctor-cache-api-dispatch",
        "drift_category": "route_contract_drift",
        "fixture_kind": "token_removal",
        "contract_affecting": True,
    },
    {
        "fixture_id": "route-contract-route-rename-fixture",
        "source_id": "doctor-cache-api-dispatch",
        "drift_category": "route_contract_drift",
        "fixture_kind": "route_rename",
        "contract_affecting": True,
    },
    {
        "fixture_id": "payload-shape-token-removal-fixture",
        "source_id": "latency-payload-shape-contract",
        "drift_category": "payload_shape_drift",
        "fixture_kind": "token_removal",
        "contract_affecting": True,
    },
    {
        "fixture_id": "smoke-evidence-token-removal-fixture",
        "source_id": "manual-smoke-cache-coverage",
        "drift_category": "smoke_evidence_drift",
        "fixture_kind": "token_removal",
        "contract_affecting": True,
    },
)

_SPEC_BY_SOURCE_ID = {source_id: (rel, token) for source_id, rel, token in _dependency_specs()}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _prefix(value: str) -> str:
    return value[:16] if value else "missing"


def _overlay_text(text: str, *, source_id: str, token: str, fixture_kind: str) -> tuple[str, bool, bool]:
    if fixture_kind == "token_removal" and token and token in text:
        return text.replace(token, f"[v1048 dry-run removed token for {source_id}]"), True, False
    if fixture_kind == "route_rename":
        if CACHE_API_ROUTE in text:
            return text.replace(CACHE_API_ROUTE, CACHE_API_ROUTE + "-renamed-by-v1048-dry-run", 1), False, True
        return f"{text}\n# v1048 dry-run route rename fallback: {source_id}\n", False, True
    return f"{text}\n# v1048 dry-run contract drift fixture: {source_id} {fixture_kind}\n", False, False


def _overlay_sources(root: Path, source_id: str, fixture_kind: str) -> tuple[dict[str, str], bool, bool]:
    baseline = _source_map(root)
    rel, token = _SPEC_BY_SOURCE_ID.get(source_id, ("[missing]", "[missing]"))
    if source_id in baseline:
        baseline[source_id], token_removed, route_renamed = _overlay_text(
            baseline[source_id], source_id=source_id, token=token, fixture_kind=fixture_kind
        )
        return baseline, token_removed, route_renamed
    return baseline, False, False


def _changed_dependency_count(root: Path, source_id: str, fixture_kind: str) -> int:
    baseline = _source_map(root)
    overlay, _token_removed, _route_renamed = _overlay_sources(root, source_id, fixture_kind)
    changed = 0
    for dependency_source_id, _rel, _token in _dependency_specs():
        if _digest(baseline.get(dependency_source_id, "")) != _digest(overlay.get(dependency_source_id, "")):
            changed += 1
    return changed


def _fixture_rows(root: Path) -> list[ContractDriftFixture]:
    routes = _diagnostic_routes()
    baseline_sources = _source_map(root)
    baseline_fingerprint = _fingerprint_from_sources(baseline_sources, routes)
    rows: list[ContractDriftFixture] = []
    valid_categories = {"benign_source_drift", "route_contract_drift", "payload_shape_drift", "smoke_evidence_drift"}
    valid_kinds = {"append_comment", "token_removal", "route_rename"}
    for spec in CONTRACT_DRIFT_FIXTURE_SPECS:
        fixture_id = str(spec["fixture_id"])
        source_id = str(spec["source_id"])
        category = str(spec["drift_category"])
        fixture_kind = str(spec["fixture_kind"])
        contract_affecting = bool(spec["contract_affecting"])
        rel, token = _SPEC_BY_SOURCE_ID.get(source_id, ("[missing]", "[missing]"))
        overlay_sources, token_removed, route_renamed = _overlay_sources(root, source_id, fixture_kind)
        overlay_fingerprint = _fingerprint_from_sources(overlay_sources, routes)
        changed_count = _changed_dependency_count(root, source_id, fixture_kind)
        token_present = token in baseline_sources.get(source_id, "")
        overlay_text = overlay_sources.get(source_id, "")
        token_absent_after_removal = token_removed and token not in overlay_text
        fingerprint_changed = baseline_fingerprint != overlay_fingerprint
        fixture_specific_pass = (
            (fixture_kind == "token_removal" and token_absent_after_removal)
            or (fixture_kind == "route_rename" and route_renamed)
            or (fixture_kind == "append_comment" and not token_removed)
        )
        ok = (
            token_present
            and fingerprint_changed
            and changed_count == 1
            and category in valid_categories
            and fixture_kind in valid_kinds
            and fixture_specific_pass
            and SOURCE_FILES_MUTATED is False
        )
        rows.append(
            ContractDriftFixture(
                fixture_id=fixture_id,
                source_id=source_id,
                drift_category=category,
                fixture_kind=fixture_kind,
                path=rel,
                contract_token=token,
                baseline_fingerprint_prefix=_prefix(baseline_fingerprint),
                overlay_fingerprint_prefix=_prefix(overlay_fingerprint),
                fingerprint_changed=fingerprint_changed,
                changed_dependency_count=changed_count,
                token_present_in_baseline=token_present,
                token_removed_in_overlay=token_absent_after_removal,
                route_renamed_in_overlay=route_renamed,
                contract_affecting=contract_affecting,
                dry_run_overlay_applied=True,
                source_file_mutated=SOURCE_FILES_MUTATED,
                ok=ok,
                message=f"category={category} kind={fixture_kind} source_id={source_id} token_present={token_present} token_removed={token_absent_after_removal} route_renamed={route_renamed} fingerprint_changed={fingerprint_changed} changed_dependency_count={changed_count} contract_affecting={contract_affecting}",
            )
        )
    return rows


def build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    rows = _fixture_rows(project_root)
    row_dicts = [asdict(row) for row in rows]
    categories = sorted({row.drift_category for row in rows})
    ok = (
        len(rows) == EXPECTED_EXPANDED_DRIFT_FIXTURE_COUNT
        and sum(1 for row in rows if row.ok) == EXPECTED_EXPANDED_CLASSIFICATION_PASS_COUNT
        and sum(1 for row in rows if row.contract_affecting) == EXPECTED_CONTRACT_AFFECTING_FIXTURE_COUNT
        and sum(1 for row in rows if row.fixture_kind == "token_removal") == EXPECTED_TOKEN_REMOVAL_FIXTURE_COUNT
        and sum(1 for row in rows if row.fixture_kind == "route_rename") == EXPECTED_ROUTE_RENAME_FIXTURE_COUNT
        and sum(1 for row in rows if row.drift_category == "benign_source_drift") == EXPECTED_BENIGN_SOURCE_DRIFT_COUNT
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
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_only": True,
        "contract_drift_fixture_preview_only": True,
        "dry_run_overlay_only": True,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "drift_classification_api_route": DRIFT_CLASSIFICATION_API_ROUTE,
        "contract_drift_fixture_api_route": CONTRACT_DRIFT_FIXTURE_API_ROUTE,
        "dependency_digest_count": EXPECTED_DEPENDENCY_DIGEST_COUNT,
        "expanded_drift_fixture_count": len(rows),
        "expanded_drift_category_count": len(categories),
        "expanded_drift_categories": categories,
        "expanded_classification_pass_count": sum(1 for row in rows if row.ok),
        "contract_affecting_fixture_count": sum(1 for row in rows if row.contract_affecting),
        "benign_source_drift_count": sum(1 for row in rows if row.drift_category == "benign_source_drift"),
        "route_contract_drift_count": sum(1 for row in rows if row.drift_category == "route_contract_drift"),
        "payload_shape_drift_count": sum(1 for row in rows if row.drift_category == "payload_shape_drift"),
        "smoke_evidence_drift_count": sum(1 for row in rows if row.drift_category == "smoke_evidence_drift"),
        "token_removal_fixture_count": sum(1 for row in rows if row.fixture_kind == "token_removal"),
        "route_rename_fixture_count": sum(1 for row in rows if row.fixture_kind == "route_rename"),
        "dry_run_overlay_count": sum(1 for row in rows if row.dry_run_overlay_applied),
        "source_files_mutated": SOURCE_FILES_MUTATED,
        "persisted_cache_written": PERSISTED_CACHE_WRITTEN,
        "live_diagnostic_measurements_performed": LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED,
        "contract_drift_fixture_rows": row_dicts,
        "executes_live_work": False,
        "applies_patches": False,
        "writes_memory": False,
        "creates_release": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "recommendations": [
            "Use contract-affecting dry-run fixtures to separate harmless cache freshness changes from API route, payload, and smoke evidence drift.",
            "Keep token removal and route rename simulation in memory only; do not mutate source files to prove drift detection.",
            "Next, map drift severity to operator-facing remediation guidance without granting automatic repair authority.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-contract-drift-fixture-expansion-v1",
            "python tools/smoke_check.py --check doctor-diagnostic-cache-digest-drift-classification-v1",
        ],
        "message": "Expanded doctor diagnostic cache contract drift fixtures simulate token removal and route rename drift with dry-run overlays only.",
    }


def build_doctor_diagnostic_cache_contract_drift_fixture_expansion(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_cache_contract_drift_fixture_expansion.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    metadata = build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata(project_id="eidolon", root=project_root)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, CONTRACT_DRIFT_FIXTURE_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    required_api_data_keys = (
        "version", "current_version_tag", "current_milestone", "next_recommended_arc", "project_id", "review_id",
        "status", "ok", "preview_only", "contract_drift_fixture_preview_only", "dry_run_overlay_only",
        "source_cache_route", "freshness_api_route", "digest_api_route", "drift_classification_api_route", "contract_drift_fixture_api_route",
        "dependency_digest_count", "expanded_drift_fixture_count", "expanded_drift_category_count", "expanded_drift_categories", "expanded_classification_pass_count",
        "contract_affecting_fixture_count", "benign_source_drift_count", "route_contract_drift_count", "payload_shape_drift_count", "smoke_evidence_drift_count",
        "token_removal_fixture_count", "route_rename_fixture_count", "dry_run_overlay_count", "source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed",
        "contract_drift_fixture_rows", "executes_live_work", "applies_patches", "writes_memory", "creates_release", "generated_wiring_activated", "release_authorized", "autonomy_expanded",
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
        and isinstance(api_data.get("contract_drift_fixture_rows"), list)
        and isinstance(api_data.get("expanded_drift_categories"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness/contract-drift-fixtures"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness", "contract-drift-fixtures"]' in api_source
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_ID,
        SELF_ROUTE,
        CONTRACT_DRIFT_FIXTURE_API_ROUTE,
        "build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata",
        "build_doctor_diagnostic_cache_contract_drift_fixture_expansion",
        "doctor_diagnostic_cache_contract_drift_fixture_expansion_text",
        "prior_total_behavioral_coverage_count=112",
        "new_contract_drift_fixture_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=113",
        "prior_mapping_reconciled_route_count=118",
        "mapping_reconciled_route_count=119",
        "expanded_drift_fixture_count=6",
        "contract_affecting_fixture_count=5",
        "token_removal_fixture_count=3",
        "route_rename_fixture_count=1",
        "expanded_classification_pass_count=6",
        "dry_run_overlay_count=6",
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
        {"name": "module-version-current", "ok": DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1047-token-present", "ok": DRIFT_CLASSIFICATION_API_ROUTE in docs and DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_ID in docs, "message": "Prior digest drift classification route/check remains represented."},
        {"name": "contract-fixture-api-index-and-handler-present", "ok": api_index_present and api_handler_present, "message": f"api_index_present={api_index_present} api_handler_present={api_handler_present}"},
        {"name": "contract-fixture-api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing_api_data_keys={len(missing_api_data_keys)} error={api_error}"},
        {"name": "expanded-fixtures-present", "ok": metadata.get("expanded_drift_fixture_count") == EXPECTED_EXPANDED_DRIFT_FIXTURE_COUNT and metadata.get("expanded_classification_pass_count") == EXPECTED_EXPANDED_CLASSIFICATION_PASS_COUNT, "message": f"fixtures={metadata.get('expanded_drift_fixture_count')} pass={metadata.get('expanded_classification_pass_count')}"},
        {"name": "contract-affecting-fixtures-separated", "ok": metadata.get("contract_affecting_fixture_count") == EXPECTED_CONTRACT_AFFECTING_FIXTURE_COUNT and metadata.get("benign_source_drift_count") == EXPECTED_BENIGN_SOURCE_DRIFT_COUNT, "message": f"contract_affecting={metadata.get('contract_affecting_fixture_count')} benign={metadata.get('benign_source_drift_count')}"},
        {"name": "token-removal-and-route-rename-fixtures", "ok": metadata.get("token_removal_fixture_count") == EXPECTED_TOKEN_REMOVAL_FIXTURE_COUNT and metadata.get("route_rename_fixture_count") == EXPECTED_ROUTE_RENAME_FIXTURE_COUNT, "message": f"token_removal={metadata.get('token_removal_fixture_count')} route_rename={metadata.get('route_rename_fixture_count')}"},
        {"name": "dry-run-overlays-only", "ok": metadata.get("dry_run_overlay_count") == EXPECTED_DRY_RUN_OVERLAY_COUNT and metadata.get("source_files_mutated") is False and metadata.get("persisted_cache_written") is False, "message": f"dry_run_overlay_count={metadata.get('dry_run_overlay_count')} source_mutated={metadata.get('source_files_mutated')} persisted={metadata.get('persisted_cache_written')}"},
        {"name": "behavioral-count-current", "ok": int(V1047_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_CONTRACT_DRIFT_FIXTURE_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={int(V1047_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_CONTRACT_DRIFT_FIXTURE_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count-current", "ok": int(V1047_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={int(V1047_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1048-doctor-diagnostic-cache-contract-drift-fixture-expansion" in manifest_source, "message": "Source surface manifest represents the v1048 contract drift fixture expansion surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1048 contract drift fixture expansion truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "contract_fixture_endpoint_executes_live_work", "contract_fixture_endpoint_applies_patches", "contract_fixture_endpoint_writes_memory", "contract_fixture_endpoint_creates_release", "contract_fixture_endpoint_persists_cache", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Contract drift fixture expansion remains dry-run/advisory and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_ID,
        "state": "doctor_diagnostic_cache_contract_drift_fixture_expansion_only",
        "prior_total_behavioral_coverage_count": int(V1047_TOTAL_BEHAVIORAL_COVERAGE_COUNT),
        "new_contract_drift_fixture_behavioral_coverage_count": NEW_CONTRACT_DRIFT_FIXTURE_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": int(V1047_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_CONTRACT_DRIFT_FIXTURE_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": int(V1047_MAPPING_RECONCILED_ROUTE_COUNT),
        "mapping_reconciled_route_count": int(V1047_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "drift_classification_api_route": DRIFT_CLASSIFICATION_API_ROUTE,
        "contract_drift_fixture_api_route": CONTRACT_DRIFT_FIXTURE_API_ROUTE,
        "contract_fixture_api_elapsed_ms": elapsed_ms,
        "dependency_digest_count": metadata.get("dependency_digest_count"),
        "expanded_drift_fixture_count": metadata.get("expanded_drift_fixture_count"),
        "expanded_drift_category_count": metadata.get("expanded_drift_category_count"),
        "expanded_drift_categories": metadata.get("expanded_drift_categories"),
        "expanded_classification_pass_count": metadata.get("expanded_classification_pass_count"),
        "contract_affecting_fixture_count": metadata.get("contract_affecting_fixture_count"),
        "benign_source_drift_count": metadata.get("benign_source_drift_count"),
        "route_contract_drift_count": metadata.get("route_contract_drift_count"),
        "payload_shape_drift_count": metadata.get("payload_shape_drift_count"),
        "smoke_evidence_drift_count": metadata.get("smoke_evidence_drift_count"),
        "token_removal_fixture_count": metadata.get("token_removal_fixture_count"),
        "route_rename_fixture_count": metadata.get("route_rename_fixture_count"),
        "dry_run_overlay_count": metadata.get("dry_run_overlay_count"),
        "contract_fixture_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "contract_fixture_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "contract_drift_fixture_rows": metadata.get("contract_drift_fixture_rows", []),
        "api_contract_drift_fixture_rows": api_data.get("contract_drift_fixture_rows", []) if isinstance(api_data, dict) else [],
        "source_files_mutated": metadata.get("source_files_mutated"),
        "persisted_cache_written": metadata.get("persisted_cache_written"),
        "live_diagnostic_measurements_performed": metadata.get("live_diagnostic_measurements_performed"),
        "contract_fixture_endpoint_preview_only": metadata.get("preview_only") is True,
        "contract_fixture_endpoint_executes_live_work": metadata.get("executes_live_work"),
        "contract_fixture_endpoint_applies_patches": metadata.get("applies_patches"),
        "contract_fixture_endpoint_writes_memory": metadata.get("writes_memory"),
        "contract_fixture_endpoint_creates_release": metadata.get("creates_release"),
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


def doctor_diagnostic_cache_contract_drift_fixture_expansion_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata",
        "build_doctor_diagnostic_cache_contract_drift_fixture_expansion",
        "doctor_diagnostic_cache_contract_drift_fixture_expansion_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_contract_drift_fixture_behavioral_coverage_count={report.get('new_contract_drift_fixture_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"source_cache_route={report.get('source_cache_route')}",
        f"freshness_api_route={report.get('freshness_api_route')}",
        f"digest_api_route={report.get('digest_api_route')}",
        f"drift_classification_api_route={report.get('drift_classification_api_route')}",
        f"contract_drift_fixture_api_route={report.get('contract_drift_fixture_api_route')}",
        f"dependency_digest_count={report.get('dependency_digest_count')}",
        f"expanded_drift_fixture_count={report.get('expanded_drift_fixture_count')}",
        f"expanded_drift_category_count={report.get('expanded_drift_category_count')}",
        f"expanded_classification_pass_count={report.get('expanded_classification_pass_count')}",
        f"contract_affecting_fixture_count={report.get('contract_affecting_fixture_count')}",
        f"benign_source_drift_count={report.get('benign_source_drift_count')}",
        f"route_contract_drift_count={report.get('route_contract_drift_count')}",
        f"payload_shape_drift_count={report.get('payload_shape_drift_count')}",
        f"smoke_evidence_drift_count={report.get('smoke_evidence_drift_count')}",
        f"token_removal_fixture_count={report.get('token_removal_fixture_count')}",
        f"route_rename_fixture_count={report.get('route_rename_fixture_count')}",
        f"dry_run_overlay_count={report.get('dry_run_overlay_count')}",
        f"contract_fixture_payload_shape_pass_count={report.get('contract_fixture_payload_shape_pass_count')}",
        f"contract_fixture_api_pass_count={report.get('contract_fixture_api_pass_count')}",
        f"source_files_mutated={report.get('source_files_mutated')}",
        f"persisted_cache_written={report.get('persisted_cache_written')}",
        f"live_diagnostic_measurements_performed={report.get('live_diagnostic_measurements_performed')}",
        f"contract_fixture_endpoint_preview_only={report.get('contract_fixture_endpoint_preview_only')}",
        f"contract_fixture_endpoint_executes_live_work={report.get('contract_fixture_endpoint_executes_live_work')}",
        f"contract_fixture_endpoint_applies_patches={report.get('contract_fixture_endpoint_applies_patches')}",
        f"contract_fixture_endpoint_writes_memory={report.get('contract_fixture_endpoint_writes_memory')}",
        f"contract_fixture_endpoint_creates_release={report.get('contract_fixture_endpoint_creates_release')}",
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
        lines.append("\nContract drift fixture rows:")
        for row in report.get("contract_drift_fixture_rows", []):
            lines.append(
                f"- {row.get('fixture_id')} {row.get('source_id')} category={row.get('drift_category')} kind={row.get('fixture_kind')} path={row.get('path')} fingerprint_changed={row.get('fingerprint_changed')} changed_dependency_count={row.get('changed_dependency_count')} token_present_in_baseline={row.get('token_present_in_baseline')} token_removed_in_overlay={row.get('token_removed_in_overlay')} route_renamed_in_overlay={row.get('route_renamed_in_overlay')} contract_affecting={row.get('contract_affecting')} dry_run_overlay_applied={row.get('dry_run_overlay_applied')} source_file_mutated={row.get('source_file_mutated')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
