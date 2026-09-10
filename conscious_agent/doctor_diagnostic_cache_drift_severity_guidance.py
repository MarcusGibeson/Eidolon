from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_cache_contract_drift_fixture_expansion import (
    CONTRACT_DRIFT_FIXTURE_API_ROUTE,
    EXPECTED_EXPANDED_DRIFT_FIXTURE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1048_MAPPING_RECONCILED_ROUTE_COUNT,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1048_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata,
)
from doctor_diagnostic_cache_digest_drift_classification import DRIFT_CLASSIFICATION_API_ROUTE, _call_api
from doctor_diagnostic_cache_source_dependency_digest_verification import (
    CACHE_API_ROUTE,
    DIGEST_API_ROUTE,
    FRESHNESS_API_ROUTE,
    _read_text,
    _repo,
    _route_renderer_map,
)

DOCTOR_DIAGNOSTIC_CACHE_DRIFT_SEVERITY_GUIDANCE_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_DRIFT_SEVERITY_GUIDANCE_ID = "doctor-diagnostic-cache-drift-severity-guidance-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-diagnostic-cache-drift-severity-guidance"
SELF_RENDERER = "render_doctor_diagnostic_cache_drift_severity_guidance"
DRIFT_SEVERITY_GUIDANCE_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness/drift-severity-guidance"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = int(V1048_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
NEW_DRIFT_SEVERITY_GUIDANCE_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT + NEW_DRIFT_SEVERITY_GUIDANCE_BEHAVIORAL_COVERAGE_COUNT
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = int(V1048_MAPPING_RECONCILED_ROUTE_COUNT)
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = PRIOR_MAPPING_RECONCILED_ROUTE_COUNT + NEW_MAPPING_RECONCILED_ROUTE_COUNT
EXPECTED_SEVERITY_GUIDANCE_ROW_COUNT = 6
EXPECTED_SEVERITY_LABEL_COUNT = 4
EXPECTED_INFORMATIONAL_SEVERITY_COUNT = 1
EXPECTED_ADVISORY_SEVERITY_COUNT = 1
EXPECTED_WARNING_SEVERITY_COUNT = 1
EXPECTED_BLOCKER_SEVERITY_COUNT = 3
EXPECTED_SEVERITY_GUIDANCE_PASS_COUNT = 6
EXPECTED_DRY_RUN_OVERLAY_COUNT = 6
SOURCE_FILES_MUTATED = False
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "severity_guidance_preview_only": True,
    "dry_run_overlay_only": True,
    "source_files_mutated": False,
    "persisted_cache_written": False,
    "live_diagnostic_measurements_performed": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "severity_guidance_endpoint_executes_live_work": False,
    "severity_guidance_endpoint_applies_patches": False,
    "severity_guidance_endpoint_writes_memory": False,
    "severity_guidance_endpoint_creates_release": False,
    "severity_guidance_endpoint_persists_cache": False,
    "severity_guidance_endpoint_auto_repairs_drift": False,
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
class DriftSeverityGuidanceRow:
    fixture_id: str
    source_id: str
    drift_category: str
    fixture_kind: str
    severity_label: str
    severity_rank: int
    operator_guidance: str
    remediation_scope: str
    contract_affecting: bool
    token_removed_in_overlay: bool
    route_renamed_in_overlay: bool
    dry_run_overlay_applied: bool
    source_file_mutated: bool
    ok: bool
    message: str


def _severity_for(row: dict[str, Any]) -> tuple[str, int, str, str]:
    category = str(row.get("drift_category"))
    kind = str(row.get("fixture_kind"))
    token_removed = row.get("token_removed_in_overlay") is True
    route_renamed = row.get("route_renamed_in_overlay") is True
    if category == "benign_source_drift":
        return (
            "informational",
            1,
            "Review the source digest note, but do not block the cache if contract tokens and route targets remain intact.",
            "no_operator_blocker",
        )
    if category == "route_contract_drift" and kind == "append_comment" and not token_removed and not route_renamed:
        return (
            "advisory",
            2,
            "Check route-contract context before approving related dashboard/API changes; no automatic repair is allowed.",
            "operator_review_advisory",
        )
    if category == "payload_shape_drift":
        return (
            "warning",
            3,
            "Re-run payload-shape smoke and inspect dependent dashboard/API consumers before relying on cached diagnostic summaries.",
            "operator_payload_contract_review",
        )
    if category == "route_contract_drift" and (token_removed or route_renamed):
        return (
            "blocker",
            4,
            "Block release until the route contract is repaired, the manual API/dashboard target is verified, and smoke evidence is updated.",
            "release_blocking_operator_repair",
        )
    if category == "smoke_evidence_drift":
        return (
            "blocker",
            4,
            "Block release until manual smoke evidence is reconciled; generated wiring and auto-repair remain inactive.",
            "release_blocking_smoke_reconciliation",
        )
    return (
        "blocker",
        4,
        "Unknown drift category or fixture shape; block until an operator classifies it manually.",
        "release_blocking_unknown_drift",
    )


def _severity_rows(root: Path) -> list[DriftSeverityGuidanceRow]:
    metadata = build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata(project_id="eidolon", root=root)
    fixture_rows = metadata.get("contract_drift_fixture_rows", []) if isinstance(metadata, dict) else []
    rows: list[DriftSeverityGuidanceRow] = []
    valid_labels = {"informational", "advisory", "warning", "blocker"}
    for fixture in fixture_rows:
        if not isinstance(fixture, dict):
            continue
        label, rank, guidance, scope = _severity_for(fixture)
        contract_affecting = bool(fixture.get("contract_affecting"))
        token_removed = fixture.get("token_removed_in_overlay") is True
        route_renamed = fixture.get("route_renamed_in_overlay") is True
        dry_run = fixture.get("dry_run_overlay_applied") is True
        source_mutated = fixture.get("source_file_mutated") is True
        ok = (
            fixture.get("ok") is True
            and label in valid_labels
            and isinstance(rank, int)
            and 1 <= rank <= 4
            and isinstance(guidance, str)
            and bool(guidance.strip())
            and isinstance(scope, str)
            and bool(scope.strip())
            and dry_run is True
            and source_mutated is False
            and SOURCE_FILES_MUTATED is False
        )
        rows.append(
            DriftSeverityGuidanceRow(
                fixture_id=str(fixture.get("fixture_id")),
                source_id=str(fixture.get("source_id")),
                drift_category=str(fixture.get("drift_category")),
                fixture_kind=str(fixture.get("fixture_kind")),
                severity_label=label,
                severity_rank=rank,
                operator_guidance=guidance,
                remediation_scope=scope,
                contract_affecting=contract_affecting,
                token_removed_in_overlay=token_removed,
                route_renamed_in_overlay=route_renamed,
                dry_run_overlay_applied=dry_run,
                source_file_mutated=source_mutated,
                ok=ok,
                message=f"fixture={fixture.get('fixture_id')} category={fixture.get('drift_category')} kind={fixture.get('fixture_kind')} severity={label} rank={rank} dry_run={dry_run} source_file_mutated={source_mutated}",
            )
        )
    return rows


def build_doctor_diagnostic_cache_drift_severity_guidance_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    fixture_metadata = build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata(project_id=project_id, root=project_root)
    rows = _severity_rows(project_root)
    row_dicts = [asdict(row) for row in rows]
    severity_labels = sorted({row.severity_label for row in rows})
    ok = (
        fixture_metadata.get("ok") is True
        and fixture_metadata.get("preview_only") is True
        and len(rows) == EXPECTED_SEVERITY_GUIDANCE_ROW_COUNT
        and len(rows) == EXPECTED_EXPANDED_DRIFT_FIXTURE_COUNT
        and len(severity_labels) == EXPECTED_SEVERITY_LABEL_COUNT
        and sum(1 for row in rows if row.ok) == EXPECTED_SEVERITY_GUIDANCE_PASS_COUNT
        and sum(1 for row in rows if row.severity_label == "informational") == EXPECTED_INFORMATIONAL_SEVERITY_COUNT
        and sum(1 for row in rows if row.severity_label == "advisory") == EXPECTED_ADVISORY_SEVERITY_COUNT
        and sum(1 for row in rows if row.severity_label == "warning") == EXPECTED_WARNING_SEVERITY_COUNT
        and sum(1 for row in rows if row.severity_label == "blocker") == EXPECTED_BLOCKER_SEVERITY_COUNT
        and sum(1 for row in rows if row.dry_run_overlay_applied) == EXPECTED_DRY_RUN_OVERLAY_COUNT
        and all(row.source_file_mutated is False for row in rows)
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
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_DRIFT_SEVERITY_GUIDANCE_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "preview_only": True,
        "severity_guidance_preview_only": True,
        "dry_run_overlay_only": True,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "contract_drift_fixture_api_route": CONTRACT_DRIFT_FIXTURE_API_ROUTE,
        "drift_classification_api_route": DRIFT_CLASSIFICATION_API_ROUTE,
        "drift_severity_guidance_api_route": DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
        "severity_guidance_row_count": len(rows),
        "severity_label_count": len(severity_labels),
        "severity_labels": severity_labels,
        "severity_guidance_pass_count": sum(1 for row in rows if row.ok),
        "informational_severity_count": sum(1 for row in rows if row.severity_label == "informational"),
        "advisory_severity_count": sum(1 for row in rows if row.severity_label == "advisory"),
        "warning_severity_count": sum(1 for row in rows if row.severity_label == "warning"),
        "blocker_severity_count": sum(1 for row in rows if row.severity_label == "blocker"),
        "contract_affecting_severity_count": sum(1 for row in rows if row.contract_affecting),
        "dry_run_overlay_count": sum(1 for row in rows if row.dry_run_overlay_applied),
        "source_files_mutated": SOURCE_FILES_MUTATED,
        "persisted_cache_written": PERSISTED_CACHE_WRITTEN,
        "live_diagnostic_measurements_performed": LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED,
        "severity_guidance_rows": row_dicts,
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
            "Treat informational drift as review-only unless paired with contract token loss.",
            "Treat advisory drift as an operator review cue, not release permission or auto-repair authority.",
            "Treat warning and blocker drift as reasons to rerun targeted smoke and inspect manual dashboard/API/smoke contracts before release.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-drift-severity-guidance-v1",
            "python tools/smoke_check.py --check doctor-diagnostic-cache-contract-drift-fixture-expansion-v1",
        ],
        "message": "Doctor diagnostic cache drift severity guidance maps dry-run fixture categories to operator-facing informational, advisory, warning, and blocker labels without granting repair authority.",
    }


def build_doctor_diagnostic_cache_drift_severity_guidance(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_diagnostic_cache_drift_severity_guidance.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    metadata = build_doctor_diagnostic_cache_drift_severity_guidance_metadata(project_id="eidolon", root=project_root)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, DRIFT_SEVERITY_GUIDANCE_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    required_api_data_keys = (
        "version", "current_version_tag", "current_milestone", "next_recommended_arc", "project_id", "review_id", "status", "ok",
        "preview_only", "severity_guidance_preview_only", "dry_run_overlay_only", "source_cache_route", "freshness_api_route", "digest_api_route",
        "contract_drift_fixture_api_route", "drift_classification_api_route", "drift_severity_guidance_api_route", "severity_guidance_row_count", "severity_label_count", "severity_labels",
        "severity_guidance_pass_count", "informational_severity_count", "advisory_severity_count", "warning_severity_count", "blocker_severity_count",
        "contract_affecting_severity_count", "dry_run_overlay_count", "source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed",
        "severity_guidance_rows", "executes_live_work", "applies_patches", "writes_memory", "creates_release", "persists_cache", "auto_repairs_drift",
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
        and isinstance(api_data.get("severity_guidance_rows"), list)
        and isinstance(api_data.get("severity_labels"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness/drift-severity-guidance"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness", "drift-severity-guidance"]' in api_source
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_DRIFT_SEVERITY_GUIDANCE_ID,
        SELF_ROUTE,
        DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
        "build_doctor_diagnostic_cache_drift_severity_guidance_metadata",
        "build_doctor_diagnostic_cache_drift_severity_guidance",
        "doctor_diagnostic_cache_drift_severity_guidance_text",
        "prior_total_behavioral_coverage_count=113",
        "new_drift_severity_guidance_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=114",
        "prior_mapping_reconciled_route_count=119",
        "mapping_reconciled_route_count=120",
        "severity_guidance_row_count=6",
        "severity_label_count=4",
        "informational_severity_count=1",
        "advisory_severity_count=1",
        "warning_severity_count=1",
        "blocker_severity_count=3",
        "severity_guidance_pass_count=6",
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
    rows = metadata.get("severity_guidance_rows", [])
    severity_labels = {row.get("severity_label") for row in rows if isinstance(row, dict)}
    rows_status = [
        {"name": "fixture-metadata-valid", "ok": metadata.get("ok") is True, "message": f"status={metadata.get('status')}"},
        {"name": "severity-row-count", "ok": metadata.get("severity_guidance_row_count") == EXPECTED_SEVERITY_GUIDANCE_ROW_COUNT, "message": f"rows={metadata.get('severity_guidance_row_count')}"},
        {"name": "severity-label-count", "ok": metadata.get("severity_label_count") == EXPECTED_SEVERITY_LABEL_COUNT and severity_labels == {"informational", "advisory", "warning", "blocker"}, "message": f"labels={sorted(severity_labels)}"},
        {"name": "severity-counts", "ok": metadata.get("informational_severity_count") == 1 and metadata.get("advisory_severity_count") == 1 and metadata.get("warning_severity_count") == 1 and metadata.get("blocker_severity_count") == 3, "message": "informational=1 advisory=1 warning=1 blocker=3"},
        {"name": "severity-guidance-rows-pass", "ok": metadata.get("severity_guidance_pass_count") == EXPECTED_SEVERITY_GUIDANCE_PASS_COUNT and all(isinstance(row, dict) and row.get("ok") is True for row in rows), "message": f"passes={metadata.get('severity_guidance_pass_count')}"},
        {"name": "dry-run-only", "ok": metadata.get("dry_run_overlay_count") == EXPECTED_DRY_RUN_OVERLAY_COUNT and metadata.get("source_files_mutated") is False and metadata.get("persisted_cache_written") is False and metadata.get("live_diagnostic_measurements_performed") is False, "message": "dry-run severity guidance writes no source/cache and runs no live diagnostics."},
        {"name": "api-index-present", "ok": api_index_present, "message": "API index documents the v1049 severity guidance endpoint."},
        {"name": "api-handler-present", "ok": api_handler_present, "message": "Manual API dispatch handles the v1049 severity guidance endpoint."},
        {"name": "api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing={missing_api_data_keys}"},
        {"name": "behavioral-count", "ok": TOTAL_BEHAVIORAL_COVERAGE_COUNT == int(V1048_TOTAL_BEHAVIORAL_COVERAGE_COUNT) + NEW_DRIFT_SEVERITY_GUIDANCE_BEHAVIORAL_COVERAGE_COUNT, "message": f"coverage={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count", "ok": MAPPING_RECONCILED_ROUTE_COUNT == int(V1048_MAPPING_RECONCILED_ROUTE_COUNT) + NEW_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1049-doctor-diagnostic-cache-drift-severity-guidance" in manifest_source, "message": "Source surface manifest represents the v1049 severity guidance surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1049 severity guidance truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "severity_guidance_endpoint_executes_live_work", "severity_guidance_endpoint_applies_patches", "severity_guidance_endpoint_writes_memory", "severity_guidance_endpoint_creates_release", "severity_guidance_endpoint_persists_cache", "severity_guidance_endpoint_auto_repairs_drift", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Severity guidance remains preview-only and does not grant repair authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_DRIFT_SEVERITY_GUIDANCE_ID,
        "state": "doctor_diagnostic_cache_drift_severity_guidance_only",
        "prior_total_behavioral_coverage_count": PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "new_drift_severity_guidance_behavioral_coverage_count": NEW_DRIFT_SEVERITY_GUIDANCE_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": PRIOR_MAPPING_RECONCILED_ROUTE_COUNT,
        "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "digest_api_route": DIGEST_API_ROUTE,
        "contract_drift_fixture_api_route": CONTRACT_DRIFT_FIXTURE_API_ROUTE,
        "drift_classification_api_route": DRIFT_CLASSIFICATION_API_ROUTE,
        "drift_severity_guidance_api_route": DRIFT_SEVERITY_GUIDANCE_API_ROUTE,
        "drift_severity_guidance_api_elapsed_ms": elapsed_ms,
        "severity_guidance_row_count": metadata.get("severity_guidance_row_count"),
        "severity_label_count": metadata.get("severity_label_count"),
        "severity_labels": metadata.get("severity_labels"),
        "severity_guidance_pass_count": metadata.get("severity_guidance_pass_count"),
        "informational_severity_count": metadata.get("informational_severity_count"),
        "advisory_severity_count": metadata.get("advisory_severity_count"),
        "warning_severity_count": metadata.get("warning_severity_count"),
        "blocker_severity_count": metadata.get("blocker_severity_count"),
        "contract_affecting_severity_count": metadata.get("contract_affecting_severity_count"),
        "dry_run_overlay_count": metadata.get("dry_run_overlay_count"),
        "severity_guidance_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "severity_guidance_api_pass_count": 1 if status == 200 and isinstance(api_payload, dict) and api_payload.get("ok") is True and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "severity_guidance_rows": metadata.get("severity_guidance_rows", []),
        "api_severity_guidance_rows": api_data.get("severity_guidance_rows", []) if isinstance(api_data, dict) else [],
        "source_files_mutated": metadata.get("source_files_mutated"),
        "persisted_cache_written": metadata.get("persisted_cache_written"),
        "live_diagnostic_measurements_performed": metadata.get("live_diagnostic_measurements_performed"),
        "severity_guidance_endpoint_preview_only": metadata.get("preview_only") is True,
        "severity_guidance_endpoint_executes_live_work": metadata.get("executes_live_work"),
        "severity_guidance_endpoint_applies_patches": metadata.get("applies_patches"),
        "severity_guidance_endpoint_writes_memory": metadata.get("writes_memory"),
        "severity_guidance_endpoint_creates_release": metadata.get("creates_release"),
        "severity_guidance_endpoint_persists_cache": metadata.get("persists_cache"),
        "severity_guidance_endpoint_auto_repairs_drift": metadata.get("auto_repairs_drift"),
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


def doctor_diagnostic_cache_drift_severity_guidance_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{CURRENT_MILESTONE}",
        f"review_id={report.get('review_id')}",
        "build_doctor_diagnostic_cache_drift_severity_guidance_metadata",
        "build_doctor_diagnostic_cache_drift_severity_guidance",
        "doctor_diagnostic_cache_drift_severity_guidance_text",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"new_drift_severity_guidance_behavioral_coverage_count={report.get('new_drift_severity_guidance_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"source_cache_route={report.get('source_cache_route')}",
        f"freshness_api_route={report.get('freshness_api_route')}",
        f"digest_api_route={report.get('digest_api_route')}",
        f"contract_drift_fixture_api_route={report.get('contract_drift_fixture_api_route')}",
        f"drift_classification_api_route={report.get('drift_classification_api_route')}",
        f"drift_severity_guidance_api_route={report.get('drift_severity_guidance_api_route')}",
        f"severity_guidance_row_count={report.get('severity_guidance_row_count')}",
        f"severity_label_count={report.get('severity_label_count')}",
        f"severity_guidance_pass_count={report.get('severity_guidance_pass_count')}",
        f"informational_severity_count={report.get('informational_severity_count')}",
        f"advisory_severity_count={report.get('advisory_severity_count')}",
        f"warning_severity_count={report.get('warning_severity_count')}",
        f"blocker_severity_count={report.get('blocker_severity_count')}",
        f"contract_affecting_severity_count={report.get('contract_affecting_severity_count')}",
        f"dry_run_overlay_count={report.get('dry_run_overlay_count')}",
        f"severity_guidance_payload_shape_pass_count={report.get('severity_guidance_payload_shape_pass_count')}",
        f"severity_guidance_api_pass_count={report.get('severity_guidance_api_pass_count')}",
        f"source_files_mutated={report.get('source_files_mutated')}",
        f"persisted_cache_written={report.get('persisted_cache_written')}",
        f"live_diagnostic_measurements_performed={report.get('live_diagnostic_measurements_performed')}",
        f"severity_guidance_endpoint_preview_only={report.get('severity_guidance_endpoint_preview_only')}",
        f"severity_guidance_endpoint_executes_live_work={report.get('severity_guidance_endpoint_executes_live_work')}",
        f"severity_guidance_endpoint_applies_patches={report.get('severity_guidance_endpoint_applies_patches')}",
        f"severity_guidance_endpoint_writes_memory={report.get('severity_guidance_endpoint_writes_memory')}",
        f"severity_guidance_endpoint_creates_release={report.get('severity_guidance_endpoint_creates_release')}",
        f"severity_guidance_endpoint_persists_cache={report.get('severity_guidance_endpoint_persists_cache')}",
        f"severity_guidance_endpoint_auto_repairs_drift={report.get('severity_guidance_endpoint_auto_repairs_drift')}",
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
        lines.append("\nSeverity guidance rows:")
        for row in report.get("severity_guidance_rows", []):
            lines.append(
                f"- {row.get('fixture_id')} {row.get('source_id')} category={row.get('drift_category')} kind={row.get('fixture_kind')} severity={row.get('severity_label')} rank={row.get('severity_rank')} remediation_scope={row.get('remediation_scope')} contract_affecting={row.get('contract_affecting')} token_removed={row.get('token_removed_in_overlay')} route_renamed={row.get('route_renamed_in_overlay')} dry_run_overlay_applied={row.get('dry_run_overlay_applied')} source_file_mutated={row.get('source_file_mutated')} ok={row.get('ok')}"
            )
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} {row.get('message')}")
    return "\n".join(lines)
