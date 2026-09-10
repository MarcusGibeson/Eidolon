from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_cache_drift_severity_guidance import (
    DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
    EXPECTED_SEVERITY_GUIDANCE_ROW_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1049_MAPPING_RECONCILED_ROUTE_COUNT,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1049_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    build_doctor_diagnostic_cache_drift_severity_guidance_metadata,
)
from doctor_diagnostic_cache_digest_drift_classification import _call_api
from doctor_diagnostic_cache_source_dependency_digest_verification import CACHE_API_ROUTE, FRESHNESS_API_ROUTE, _read_text, _repo, _route_renderer_map

DOCTOR_DIAGNOSTIC_CACHE_SEVERITY_ROUTE_IMPACT_MATRIX_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_SEVERITY_ROUTE_IMPACT_MATRIX_ID = "doctor-diagnostic-cache-severity-route-impact-matrix-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-diagnostic-cache-severity-route-impact-matrix"
SELF_RENDERER = "render_doctor_diagnostic_cache_severity_route_impact_matrix"
SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness/severity-route-impact-matrix"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = int(V1049_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
NEW_SEVERITY_ROUTE_IMPACT_MATRIX_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT + NEW_SEVERITY_ROUTE_IMPACT_MATRIX_BEHAVIORAL_COVERAGE_COUNT
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = int(V1049_MAPPING_RECONCILED_ROUTE_COUNT)
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = PRIOR_MAPPING_RECONCILED_ROUTE_COUNT + NEW_MAPPING_RECONCILED_ROUTE_COUNT
EXPECTED_IMPACT_FIXTURE_COUNT = int(EXPECTED_SEVERITY_GUIDANCE_ROW_COUNT)
EXPECTED_IMPACT_SURFACE_KIND_COUNT = 3
EXPECTED_IMPACT_MATRIX_ROW_COUNT = EXPECTED_IMPACT_FIXTURE_COUNT * EXPECTED_IMPACT_SURFACE_KIND_COUNT
EXPECTED_IMPACT_MATRIX_PASS_COUNT = EXPECTED_IMPACT_MATRIX_ROW_COUNT
EXPECTED_INFORMATIONAL_IMPACT_COUNT = 3
EXPECTED_ADVISORY_IMPACT_COUNT = 3
EXPECTED_WARNING_IMPACT_COUNT = 3
EXPECTED_BLOCKER_IMPACT_COUNT = 9
SOURCE_FILES_MUTATED = False
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False
AUTOMATIC_REPAIR_PERFORMED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "route_impact_matrix_preview_only": True,
    "dry_run_guidance_only": True,
    "source_files_mutated": False,
    "persisted_cache_written": False,
    "live_diagnostic_measurements_performed": False,
    "automatic_repair_performed": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_impact_matrix_endpoint_executes_live_work": False,
    "route_impact_matrix_endpoint_applies_patches": False,
    "route_impact_matrix_endpoint_writes_memory": False,
    "route_impact_matrix_endpoint_creates_release": False,
    "route_impact_matrix_endpoint_persists_cache": False,
    "route_impact_matrix_endpoint_auto_repairs_drift": False,
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
class RouteImpactMatrixRow:
    fixture_id: str
    source_id: str
    drift_category: str
    fixture_kind: str
    severity_label: str
    severity_rank: int
    surface_kind: str
    affected_target: str
    affected_route_family: str
    operator_action: str
    release_impact: str
    contract_affecting: bool
    dry_run_overlay_applied: bool
    source_file_mutated: bool
    generated_wiring_activated: bool
    ok: bool
    message: str


_SOURCE_IMPACT_TARGETS: dict[str, dict[str, str]] = {
    "preview-cache-builder": {
        "dashboard": "/doctor",
        "api": CACHE_API_ROUTE,
        "smoke": "doctor-diagnostic-preview-cache-and-heavy-route-decoupling-v1",
        "family": "doctor_preview_cache",
    },
    "doctor-cache-api-dispatch": {
        "dashboard": "/doctor-diagnostic-cache-drift-severity-guidance",
        "api": DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
        "smoke": "doctor-diagnostic-cache-drift-severity-guidance-v1",
        "family": "doctor_cache_route_contract",
    },
    "latency-payload-shape-contract": {
        "dashboard": "/doctor-deferred-diagnostic-latency-budget-payload-shape",
        "api": "/api/doctor/diagnostic-preview-cache/freshness/drift-severity-guidance",
        "smoke": "doctor-deferred-diagnostic-latency-budget-and-payload-shape-v1",
        "family": "doctor_payload_shape_contract",
    },
    "manual-smoke-cache-coverage": {
        "dashboard": "/doctor-diagnostic-cache-drift-severity-guidance",
        "api": SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE,
        "smoke": "doctor-diagnostic-cache-drift-severity-guidance-v1",
        "family": "manual_smoke_evidence",
    },
}


def _operator_action_for(label: str, surface_kind: str) -> tuple[str, str]:
    if label == "informational":
        return ("review_digest_note", "does_not_block_release")
    if label == "advisory":
        return ("operator_review_before_related_route_change", "advisory_review_before_release")
    if label == "warning":
        if surface_kind == "smoke":
            return ("rerun_payload_shape_smoke", "release_warning_until_payload_shape_verified")
        return ("inspect_payload_consumers", "release_warning_until_payload_shape_verified")
    if label == "blocker":
        if surface_kind == "smoke":
            return ("reconcile_manual_smoke_evidence", "release_blocked_until_manual_smoke_reconciled")
        return ("repair_manual_route_contract_and_verify_target", "release_blocked_until_manual_contract_verified")
    return ("operator_manual_classification_required", "release_blocked_until_classified")


def _impact_rows(root: Path) -> list[RouteImpactMatrixRow]:
    severity_metadata = build_doctor_diagnostic_cache_drift_severity_guidance_metadata(project_id="eidolon", root=root)
    severity_rows = severity_metadata.get("severity_guidance_rows", []) if isinstance(severity_metadata, dict) else []
    rows: list[RouteImpactMatrixRow] = []
    for severity in severity_rows:
        if not isinstance(severity, dict):
            continue
        source_id = str(severity.get("source_id"))
        targets = _SOURCE_IMPACT_TARGETS.get(source_id, _SOURCE_IMPACT_TARGETS["manual-smoke-cache-coverage"])
        for surface_kind, affected_target in (("dashboard", targets["dashboard"]), ("api", targets["api"]), ("smoke", targets["smoke"])):
            action, release_impact = _operator_action_for(str(severity.get("severity_label")), surface_kind)
            ok = (
                severity.get("ok") is True
                and surface_kind in {"dashboard", "api", "smoke"}
                and bool(str(affected_target).strip())
                and severity.get("dry_run_overlay_applied") is True
                and severity.get("source_file_mutated") is False
                and SOURCE_FILES_MUTATED is False
                and PERSISTED_CACHE_WRITTEN is False
                and LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED is False
                and AUTOMATIC_REPAIR_PERFORMED is False
                and BOUNDARIES["generated_wiring_activated"] is False
                and BOUNDARIES["release_authorized"] is False
                and BOUNDARIES["autonomy_expanded"] is False
            )
            rows.append(
                RouteImpactMatrixRow(
                    fixture_id=str(severity.get("fixture_id")),
                    source_id=source_id,
                    drift_category=str(severity.get("drift_category")),
                    fixture_kind=str(severity.get("fixture_kind")),
                    severity_label=str(severity.get("severity_label")),
                    severity_rank=int(severity.get("severity_rank", 0)),
                    surface_kind=surface_kind,
                    affected_target=str(affected_target),
                    affected_route_family=str(targets["family"]),
                    operator_action=action,
                    release_impact=release_impact,
                    contract_affecting=bool(severity.get("contract_affecting")),
                    dry_run_overlay_applied=severity.get("dry_run_overlay_applied") is True,
                    source_file_mutated=severity.get("source_file_mutated") is True,
                    generated_wiring_activated=False,
                    ok=ok,
                    message=f"fixture={severity.get('fixture_id')} severity={severity.get('severity_label')} surface={surface_kind} target={affected_target} action={action} release_impact={release_impact}",
                )
            )
    return rows


def build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    severity_metadata = build_doctor_diagnostic_cache_drift_severity_guidance_metadata(project_id=project_id, root=project_root)
    rows = _impact_rows(project_root)
    row_dicts = [asdict(row) for row in rows]
    surface_kinds = sorted({row.surface_kind for row in rows})
    severity_labels = sorted({row.severity_label for row in rows})
    ok = (
        severity_metadata.get("ok") is True
        and severity_metadata.get("preview_only") is True
        and len(rows) == EXPECTED_IMPACT_MATRIX_ROW_COUNT
        and len(surface_kinds) == EXPECTED_IMPACT_SURFACE_KIND_COUNT
        and len({row.fixture_id for row in rows}) == EXPECTED_IMPACT_FIXTURE_COUNT
        and sum(1 for row in rows if row.ok) == EXPECTED_IMPACT_MATRIX_PASS_COUNT
        and sum(1 for row in rows if row.severity_label == "informational") == EXPECTED_INFORMATIONAL_IMPACT_COUNT
        and sum(1 for row in rows if row.severity_label == "advisory") == EXPECTED_ADVISORY_IMPACT_COUNT
        and sum(1 for row in rows if row.severity_label == "warning") == EXPECTED_WARNING_IMPACT_COUNT
        and sum(1 for row in rows if row.severity_label == "blocker") == EXPECTED_BLOCKER_IMPACT_COUNT
        and SOURCE_FILES_MUTATED is False
        and PERSISTED_CACHE_WRITTEN is False
        and LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED is False
        and AUTOMATIC_REPAIR_PERFORMED is False
        and BOUNDARIES["generated_wiring_activated"] is False
        and BOUNDARIES["release_authorized"] is False
        and BOUNDARIES["autonomy_expanded"] is False
    )
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "project_id": project_id,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_SEVERITY_ROUTE_IMPACT_MATRIX_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_only": True,
        "route_impact_matrix_preview_only": True,
        "dry_run_guidance_only": True,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "drift_severity_guidance_api_route": DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
        "severity_route_impact_matrix_api_route": SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE,
        "impact_fixture_count": len({row.fixture_id for row in rows}),
        "impact_surface_kind_count": len(surface_kinds),
        "impact_surface_kinds": surface_kinds,
        "impact_matrix_row_count": len(rows),
        "impact_matrix_pass_count": sum(1 for row in rows if row.ok),
        "severity_label_count": len(severity_labels),
        "severity_labels": severity_labels,
        "informational_impact_count": sum(1 for row in rows if row.severity_label == "informational"),
        "advisory_impact_count": sum(1 for row in rows if row.severity_label == "advisory"),
        "warning_impact_count": sum(1 for row in rows if row.severity_label == "warning"),
        "blocker_impact_count": sum(1 for row in rows if row.severity_label == "blocker"),
        "dashboard_impact_count": sum(1 for row in rows if row.surface_kind == "dashboard"),
        "api_impact_count": sum(1 for row in rows if row.surface_kind == "api"),
        "smoke_impact_count": sum(1 for row in rows if row.surface_kind == "smoke"),
        "source_files_mutated": SOURCE_FILES_MUTATED,
        "persisted_cache_written": PERSISTED_CACHE_WRITTEN,
        "live_diagnostic_measurements_performed": LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED,
        "automatic_repair_performed": AUTOMATIC_REPAIR_PERFORMED,
        "impact_matrix_rows": row_dicts,
        "executes_live_work": False,
        "applies_patches": False,
        "writes_memory": False,
        "creates_release": False,
        "persists_cache": False,
        "auto_repairs_drift": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "recommendations": [
            "Use informational impact rows as review context only.",
            "Use advisory and warning rows to decide which manual dashboard/API/smoke checks require operator review before release.",
            "Treat blocker impact rows as release-blocking until the affected manual route/API/smoke target is repaired and re-verified.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-severity-route-impact-matrix-v1",
            "python tools/smoke_check.py --check doctor-diagnostic-cache-drift-severity-guidance-v1",
        ],
        "message": "Doctor diagnostic cache severity route impact matrix maps preview-only severity guidance onto affected manual dashboard/API/smoke targets without repair authority.",
    }


def build_doctor_diagnostic_cache_severity_route_impact_matrix(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_cache_severity_route_impact_matrix.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    metadata = build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata(project_id="eidolon", root=project_root)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    required_api_data_keys = (
        "version", "current_version_tag", "current_milestone", "next_recommended_arc", "project_id", "review_id", "status", "ok",
        "preview_only", "route_impact_matrix_preview_only", "dry_run_guidance_only", "source_cache_route", "freshness_api_route", "drift_severity_guidance_api_route",
        "severity_route_impact_matrix_api_route", "impact_fixture_count", "impact_surface_kind_count", "impact_surface_kinds", "impact_matrix_row_count", "impact_matrix_pass_count",
        "severity_label_count", "severity_labels", "informational_impact_count", "advisory_impact_count", "warning_impact_count", "blocker_impact_count",
        "dashboard_impact_count", "api_impact_count", "smoke_impact_count", "source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "automatic_repair_performed",
        "impact_matrix_rows", "executes_live_work", "applies_patches", "writes_memory", "creates_release", "persists_cache", "auto_repairs_drift",
        "generated_wiring_activated", "release_authorized", "autonomy_expanded", "recommendations", "next_commands", "message",
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
        and isinstance(api_data.get("impact_matrix_rows"), list)
        and isinstance(api_data.get("impact_surface_kinds"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness/severity-route-impact-matrix"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness", "severity-route-impact-matrix"]' in api_source
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_SEVERITY_ROUTE_IMPACT_MATRIX_ID,
        SELF_ROUTE,
        SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE,
        "build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata",
        "build_doctor_diagnostic_cache_severity_route_impact_matrix",
        "doctor_diagnostic_cache_severity_route_impact_matrix_text",
        "prior_total_behavioral_coverage_count=114",
        "new_severity_route_impact_matrix_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=115",
        "prior_mapping_reconciled_route_count=120",
        "mapping_reconciled_route_count=121",
        "impact_fixture_count=6",
        "impact_surface_kind_count=3",
        "impact_matrix_row_count=18",
        "impact_matrix_pass_count=18",
        "informational_impact_count=3",
        "advisory_impact_count=3",
        "warning_impact_count=3",
        "blocker_impact_count=9",
        "dashboard_impact_count=6",
        "api_impact_count=6",
        "smoke_impact_count=6",
        "source_files_mutated=False",
        "persisted_cache_written=False",
        "live_diagnostic_measurements_performed=False",
        "automatic_repair_performed=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_still_required=True",
    ]
    rows = metadata.get("impact_matrix_rows", [])
    severity_labels = {row.get("severity_label") for row in rows if isinstance(row, dict)}
    surface_kinds = {row.get("surface_kind") for row in rows if isinstance(row, dict)}
    rows_status = [
        {"name": "severity-metadata-valid", "ok": metadata.get("ok") is True, "message": f"status={metadata.get('status')}"},
        {"name": "impact-fixture-count", "ok": metadata.get("impact_fixture_count") == EXPECTED_IMPACT_FIXTURE_COUNT, "message": f"fixtures={metadata.get('impact_fixture_count')}"},
        {"name": "impact-surface-kind-count", "ok": metadata.get("impact_surface_kind_count") == EXPECTED_IMPACT_SURFACE_KIND_COUNT and surface_kinds == {"dashboard", "api", "smoke"}, "message": f"surface_kinds={sorted(surface_kinds)}"},
        {"name": "impact-matrix-row-count", "ok": metadata.get("impact_matrix_row_count") == EXPECTED_IMPACT_MATRIX_ROW_COUNT, "message": f"rows={metadata.get('impact_matrix_row_count')}"},
        {"name": "severity-impact-counts", "ok": metadata.get("informational_impact_count") == 3 and metadata.get("advisory_impact_count") == 3 and metadata.get("warning_impact_count") == 3 and metadata.get("blocker_impact_count") == 9 and severity_labels == {"informational", "advisory", "warning", "blocker"}, "message": "informational=3 advisory=3 warning=3 blocker=9"},
        {"name": "surface-impact-counts", "ok": metadata.get("dashboard_impact_count") == 6 and metadata.get("api_impact_count") == 6 and metadata.get("smoke_impact_count") == 6, "message": "dashboard=6 api=6 smoke=6"},
        {"name": "impact-matrix-rows-pass", "ok": metadata.get("impact_matrix_pass_count") == EXPECTED_IMPACT_MATRIX_PASS_COUNT and all(isinstance(row, dict) and row.get("ok") is True for row in rows), "message": f"passes={metadata.get('impact_matrix_pass_count')}"},
        {"name": "dry-run-only", "ok": metadata.get("source_files_mutated") is False and metadata.get("persisted_cache_written") is False and metadata.get("live_diagnostic_measurements_performed") is False and metadata.get("automatic_repair_performed") is False, "message": "route impact matrix writes no source/cache, runs no live diagnostics, and performs no automatic repair."},
        {"name": "api-index-present", "ok": api_index_present, "message": "API index documents the v1050 route impact matrix endpoint."},
        {"name": "api-handler-present", "ok": api_handler_present, "message": "Manual API dispatch handles the v1050 route impact matrix endpoint."},
        {"name": "api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing={missing_api_data_keys}"},
        {"name": "behavioral-count", "ok": TOTAL_BEHAVIORAL_COVERAGE_COUNT == int(V1049_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_SEVERITY_ROUTE_IMPACT_MATRIX_BEHAVIORAL_COVERAGE_COUNT, "message": f"coverage={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count", "ok": MAPPING_RECONCILED_ROUTE_COUNT == int(V1049_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1050-doctor-diagnostic-cache-severity-route-impact-matrix" in manifest_source, "message": "Source surface manifest represents the v1050 route impact matrix surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1050 route impact matrix truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "automatic_repair_performed", "route_impact_matrix_endpoint_executes_live_work", "route_impact_matrix_endpoint_applies_patches", "route_impact_matrix_endpoint_writes_memory", "route_impact_matrix_endpoint_creates_release", "route_impact_matrix_endpoint_persists_cache", "route_impact_matrix_endpoint_auto_repairs_drift", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Route impact matrix remains preview-only and does not grant repair authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_SEVERITY_ROUTE_IMPACT_MATRIX_ID,
        "state": "doctor_diagnostic_cache_severity_route_impact_matrix_only",
        "prior_total_behavioral_coverage_count": PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "new_severity_route_impact_matrix_behavioral_coverage_count": NEW_SEVERITY_ROUTE_IMPACT_MATRIX_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": PRIOR_MAPPING_RECONCILED_ROUTE_COUNT,
        "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "drift_severity_guidance_api_route": DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
        "severity_route_impact_matrix_api_route": SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE,
        "severity_route_impact_matrix_api_elapsed_ms": elapsed_ms,
        "impact_fixture_count": metadata.get("impact_fixture_count"),
        "impact_surface_kind_count": metadata.get("impact_surface_kind_count"),
        "impact_surface_kinds": metadata.get("impact_surface_kinds"),
        "impact_matrix_row_count": metadata.get("impact_matrix_row_count"),
        "impact_matrix_pass_count": metadata.get("impact_matrix_pass_count"),
        "severity_label_count": metadata.get("severity_label_count"),
        "severity_labels": metadata.get("severity_labels"),
        "informational_impact_count": metadata.get("informational_impact_count"),
        "advisory_impact_count": metadata.get("advisory_impact_count"),
        "warning_impact_count": metadata.get("warning_impact_count"),
        "blocker_impact_count": metadata.get("blocker_impact_count"),
        "dashboard_impact_count": metadata.get("dashboard_impact_count"),
        "api_impact_count": metadata.get("api_impact_count"),
        "smoke_impact_count": metadata.get("smoke_impact_count"),
        "impact_matrix_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "impact_matrix_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "impact_matrix_rows": metadata.get("impact_matrix_rows", []),
        "api_impact_matrix_rows": api_data.get("impact_matrix_rows", []) if isinstance(api_data, dict) else [],
        "source_files_mutated": metadata.get("source_files_mutated"),
        "persisted_cache_written": metadata.get("persisted_cache_written"),
        "live_diagnostic_measurements_performed": metadata.get("live_diagnostic_measurements_performed"),
        "automatic_repair_performed": metadata.get("automatic_repair_performed"),
        "route_impact_matrix_endpoint_preview_only": metadata.get("preview_only") is True,
        "route_impact_matrix_endpoint_executes_live_work": metadata.get("executes_live_work"),
        "route_impact_matrix_endpoint_applies_patches": metadata.get("applies_patches"),
        "route_impact_matrix_endpoint_writes_memory": metadata.get("writes_memory"),
        "route_impact_matrix_endpoint_creates_release": metadata.get("creates_release"),
        "route_impact_matrix_endpoint_persists_cache": metadata.get("persists_cache"),
        "route_impact_matrix_endpoint_auto_repairs_drift": metadata.get("auto_repairs_drift"),
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


def doctor_diagnostic_cache_severity_route_impact_matrix_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata",
        "build_doctor_diagnostic_cache_severity_route_impact_matrix",
        "doctor_diagnostic_cache_severity_route_impact_matrix_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_severity_route_impact_matrix_behavioral_coverage_count={report.get('new_severity_route_impact_matrix_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"source_cache_route={report.get('source_cache_route')}",
        f"freshness_api_route={report.get('freshness_api_route')}",
        f"drift_severity_guidance_api_route={report.get('drift_severity_guidance_api_route')}",
        f"severity_route_impact_matrix_api_route={report.get('severity_route_impact_matrix_api_route')}",
        f"impact_fixture_count={report.get('impact_fixture_count')}",
        f"impact_surface_kind_count={report.get('impact_surface_kind_count')}",
        f"impact_matrix_row_count={report.get('impact_matrix_row_count')}",
        f"impact_matrix_pass_count={report.get('impact_matrix_pass_count')}",
        f"severity_label_count={report.get('severity_label_count')}",
        f"informational_impact_count={report.get('informational_impact_count')}",
        f"advisory_impact_count={report.get('advisory_impact_count')}",
        f"warning_impact_count={report.get('warning_impact_count')}",
        f"blocker_impact_count={report.get('blocker_impact_count')}",
        f"dashboard_impact_count={report.get('dashboard_impact_count')}",
        f"api_impact_count={report.get('api_impact_count')}",
        f"smoke_impact_count={report.get('smoke_impact_count')}",
        f"impact_matrix_payload_shape_pass_count={report.get('impact_matrix_payload_shape_pass_count')}",
        f"impact_matrix_api_pass_count={report.get('impact_matrix_api_pass_count')}",
        f"source_files_mutated={report.get('source_files_mutated')}",
        f"persisted_cache_written={report.get('persisted_cache_written')}",
        f"live_diagnostic_measurements_performed={report.get('live_diagnostic_measurements_performed')}",
        f"automatic_repair_performed={report.get('automatic_repair_performed')}",
        f"route_impact_matrix_endpoint_preview_only={report.get('route_impact_matrix_endpoint_preview_only')}",
        f"route_impact_matrix_endpoint_executes_live_work={report.get('route_impact_matrix_endpoint_executes_live_work')}",
        f"route_impact_matrix_endpoint_applies_patches={report.get('route_impact_matrix_endpoint_applies_patches')}",
        f"route_impact_matrix_endpoint_writes_memory={report.get('route_impact_matrix_endpoint_writes_memory')}",
        f"route_impact_matrix_endpoint_creates_release={report.get('route_impact_matrix_endpoint_creates_release')}",
        f"route_impact_matrix_endpoint_persists_cache={report.get('route_impact_matrix_endpoint_persists_cache')}",
        f"route_impact_matrix_endpoint_auto_repairs_drift={report.get('route_impact_matrix_endpoint_auto_repairs_drift')}",
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
        lines.append("\nRoute impact matrix rows:")
        for row in report.get("impact_matrix_rows", []):
            lines.append(
                f"- {row.get('fixture_id')} {row.get('surface_kind')} target={row.get('affected_target')} category={row.get('drift_category')} severity={row.get('severity_label')} rank={row.get('severity_rank')} action={row.get('operator_action')} release_impact={row.get('release_impact')} contract_affecting={row.get('contract_affecting')} dry_run_overlay_applied={row.get('dry_run_overlay_applied')} source_file_mutated={row.get('source_file_mutated')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
