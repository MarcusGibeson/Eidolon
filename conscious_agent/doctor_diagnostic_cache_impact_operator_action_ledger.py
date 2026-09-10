from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_diagnostic_cache_severity_route_impact_matrix import (
    EXPECTED_ADVISORY_IMPACT_COUNT,
    EXPECTED_BLOCKER_IMPACT_COUNT,
    EXPECTED_IMPACT_FIXTURE_COUNT,
    EXPECTED_IMPACT_MATRIX_ROW_COUNT,
    EXPECTED_IMPACT_SURFACE_KIND_COUNT,
    EXPECTED_INFORMATIONAL_IMPACT_COUNT,
    EXPECTED_WARNING_IMPACT_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1050_MAPPING_RECONCILED_ROUTE_COUNT,
    SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1050_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata,
)
from doctor_diagnostic_cache_source_dependency_digest_verification import CACHE_API_ROUTE, FRESHNESS_API_ROUTE, _read_text, _repo, _route_renderer_map
from doctor_diagnostic_cache_digest_drift_classification import _call_api

DOCTOR_DIAGNOSTIC_CACHE_IMPACT_OPERATOR_ACTION_LEDGER_VERSION = RUNTIME_VERSION
DOCTOR_DIAGNOSTIC_CACHE_IMPACT_OPERATOR_ACTION_LEDGER_ID = "doctor-diagnostic-cache-impact-operator-action-ledger-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/doctor-diagnostic-cache-impact-operator-action-ledger"
SELF_RENDERER = "render_doctor_diagnostic_cache_impact_operator_action_ledger"
IMPACT_OPERATOR_ACTION_LEDGER_API_ROUTE = "/api/doctor/diagnostic-preview-cache/freshness/impact-operator-action-ledger"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = int(V1050_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
NEW_IMPACT_OPERATOR_ACTION_LEDGER_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT + NEW_IMPACT_OPERATOR_ACTION_LEDGER_BEHAVIORAL_COVERAGE_COUNT
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = int(V1050_MAPPING_RECONCILED_ROUTE_COUNT)
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = PRIOR_MAPPING_RECONCILED_ROUTE_COUNT + NEW_MAPPING_RECONCILED_ROUTE_COUNT
EXPECTED_ACTION_LEDGER_ROW_COUNT = EXPECTED_IMPACT_MATRIX_ROW_COUNT
EXPECTED_ACTION_CATEGORY_COUNT = 4
EXPECTED_OPERATOR_APPROVAL_REQUIRED_COUNT = EXPECTED_ACTION_LEDGER_ROW_COUNT
EXPECTED_RELEASE_AUTHORIZATION_COUNT = 0
EXPECTED_AUTOMATIC_REPAIR_COUNT = 0
SOURCE_FILES_MUTATED = False
PERSISTED_CACHE_WRITTEN = False
LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED = False
AUTOMATIC_REPAIR_PERFORMED = False
RELEASE_AUTHORIZED = False
AUTONOMY_EXPANDED = False

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "operator_action_ledger_preview_only": True,
    "dry_run_guidance_only": True,
    "source_files_mutated": False,
    "persisted_cache_written": False,
    "live_diagnostic_measurements_performed": False,
    "automatic_repair_performed": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "operator_action_ledger_endpoint_executes_live_work": False,
    "operator_action_ledger_endpoint_applies_patches": False,
    "operator_action_ledger_endpoint_writes_memory": False,
    "operator_action_ledger_endpoint_creates_release": False,
    "operator_action_ledger_endpoint_persists_cache": False,
    "operator_action_ledger_endpoint_auto_repairs_drift": False,
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
class OperatorActionLedgerRow:
    fixture_id: str
    source_id: str
    drift_category: str
    severity_label: str
    severity_rank: int
    surface_kind: str
    affected_target: str
    affected_route_family: str
    action_category: str
    operator_action: str
    release_impact: str
    evidence_required: tuple[str, ...]
    requires_operator_review: bool
    requires_targeted_verification: bool
    blocks_release_until_verified: bool
    may_auto_repair: bool
    may_authorize_release: bool
    may_expand_autonomy: bool
    ok: bool
    message: str


_ACTION_BY_SEVERITY: dict[str, tuple[str, str, str, bool, bool]] = {
    "informational": (
        "record_and_monitor",
        "record the informational drift note in the operator ledger",
        "does_not_block_release",
        False,
        False,
    ),
    "advisory": (
        "operator_review_before_related_release",
        "review related route/cache wording before release notes or the next related patch",
        "advisory_review_before_release",
        True,
        False,
    ),
    "warning": (
        "targeted_verification_before_release",
        "run targeted verification for the affected target before release consideration",
        "release_warning_until_target_verified",
        True,
        False,
    ),
    "blocker": (
        "operator_blocker_resolution_required",
        "block release until operator-reviewed evidence proves the affected target is repaired or superseded",
        "release_blocked_until_operator_evidence_passes",
        True,
        True,
    ),
}


def _evidence_for(surface_kind: str, affected_target: str, severity_label: str) -> tuple[str, ...]:
    evidence: list[str] = [
        "severity-route-impact-matrix-row-present",
        "operator-action-ledger-row-present",
    ]
    if surface_kind == "dashboard":
        evidence.extend([
            f"dashboard route render check for {affected_target}",
            "manual dashboard renderer mapping remains authoritative",
        ])
    elif surface_kind == "api":
        evidence.extend([
            f"api payload shape check for {affected_target}",
            "manual api dispatch remains authoritative",
        ])
    elif surface_kind == "smoke":
        evidence.extend([
            f"manual smoke check result for {affected_target}",
            "central current-version audit result",
        ])
    else:
        evidence.append("operator manual surface classification required")
    if severity_label in {"warning", "blocker"}:
        evidence.append("targeted verification must pass before release consideration")
    if severity_label == "blocker":
        evidence.append("operator-reviewed blocker closure evidence required")
        evidence.append("final source-zip privacy verification required before release")
    return tuple(evidence)


def _action_rows(root: Path) -> list[OperatorActionLedgerRow]:
    matrix = build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata(project_id="eidolon", root=root)
    impact_rows = matrix.get("impact_matrix_rows", []) if isinstance(matrix, dict) else []
    rows: list[OperatorActionLedgerRow] = []
    for impact in impact_rows:
        if not isinstance(impact, dict):
            continue
        severity_label = str(impact.get("severity_label"))
        action_category, operator_action, release_impact, requires_targeted_verification, blocks_release = _ACTION_BY_SEVERITY.get(
            severity_label,
            (
                "operator_manual_classification_required",
                "classify this unrecognized severity before release consideration",
                "release_blocked_until_classified",
                True,
                True,
            ),
        )
        surface_kind = str(impact.get("surface_kind"))
        affected_target = str(impact.get("affected_target"))
        evidence = _evidence_for(surface_kind, affected_target, severity_label)
        ok = (
            impact.get("ok") is True
            and bool(action_category)
            and bool(operator_action)
            and bool(release_impact)
            and len(evidence) >= 4
            and bool(affected_target.strip())
            and SOURCE_FILES_MUTATED is False
            and PERSISTED_CACHE_WRITTEN is False
            and LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED is False
            and AUTOMATIC_REPAIR_PERFORMED is False
            and RELEASE_AUTHORIZED is False
            and AUTONOMY_EXPANDED is False
            and BOUNDARIES["generated_wiring_activated"] is False
        )
        rows.append(
            OperatorActionLedgerRow(
                fixture_id=str(impact.get("fixture_id")),
                source_id=str(impact.get("source_id")),
                drift_category=str(impact.get("drift_category")),
                severity_label=severity_label,
                severity_rank=int(impact.get("severity_rank", 0)),
                surface_kind=surface_kind,
                affected_target=affected_target,
                affected_route_family=str(impact.get("affected_route_family")),
                action_category=action_category,
                operator_action=operator_action,
                release_impact=release_impact,
                evidence_required=evidence,
                requires_operator_review=True,
                requires_targeted_verification=requires_targeted_verification,
                blocks_release_until_verified=blocks_release,
                may_auto_repair=False,
                may_authorize_release=False,
                may_expand_autonomy=False,
                ok=ok,
                message=(
                    f"fixture={impact.get('fixture_id')} severity={severity_label} surface={surface_kind} "
                    f"target={affected_target} action={action_category} release_impact={release_impact}"
                ),
            )
        )
    return rows


def build_doctor_diagnostic_cache_impact_operator_action_ledger_metadata(project_id: str = "eidolon", root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    matrix = build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata(project_id=project_id, root=project_root)
    rows = _action_rows(project_root)
    row_dicts = [asdict(row) for row in rows]
    severity_labels = sorted({row.severity_label for row in rows})
    action_categories = sorted({row.action_category for row in rows})
    surface_kinds = sorted({row.surface_kind for row in rows})
    informational = sum(1 for row in rows if row.severity_label == "informational")
    advisory = sum(1 for row in rows if row.severity_label == "advisory")
    warning = sum(1 for row in rows if row.severity_label == "warning")
    blocker = sum(1 for row in rows if row.severity_label == "blocker")
    targeted_verification = sum(1 for row in rows if row.requires_targeted_verification)
    release_blocking = sum(1 for row in rows if row.blocks_release_until_verified)
    auto_repair = sum(1 for row in rows if row.may_auto_repair)
    release_authorization = sum(1 for row in rows if row.may_authorize_release)
    autonomy_expansion = sum(1 for row in rows if row.may_expand_autonomy)
    operator_review_required = sum(1 for row in rows if row.requires_operator_review)
    evidence_requirement_count = sum(len(row.evidence_required) for row in rows)
    ok = (
        matrix.get("ok") is True
        and matrix.get("preview_only") is True
        and len(rows) == EXPECTED_ACTION_LEDGER_ROW_COUNT
        and surface_kinds == ["api", "dashboard", "smoke"]
        and len(action_categories) == EXPECTED_ACTION_CATEGORY_COUNT
        and informational == EXPECTED_INFORMATIONAL_IMPACT_COUNT
        and advisory == EXPECTED_ADVISORY_IMPACT_COUNT
        and warning == EXPECTED_WARNING_IMPACT_COUNT
        and blocker == EXPECTED_BLOCKER_IMPACT_COUNT
        and operator_review_required == EXPECTED_OPERATOR_APPROVAL_REQUIRED_COUNT
        and auto_repair == EXPECTED_AUTOMATIC_REPAIR_COUNT
        and release_authorization == EXPECTED_RELEASE_AUTHORIZATION_COUNT
        and autonomy_expansion == 0
        and all(row.ok for row in rows)
        and SOURCE_FILES_MUTATED is False
        and PERSISTED_CACHE_WRITTEN is False
        and LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED is False
        and AUTOMATIC_REPAIR_PERFORMED is False
        and RELEASE_AUTHORIZED is False
        and AUTONOMY_EXPANDED is False
        and all(BOUNDARIES[key] is False for key in [
            "source_files_mutated",
            "persisted_cache_written",
            "live_diagnostic_measurements_performed",
            "automatic_repair_performed",
            "operator_action_ledger_endpoint_executes_live_work",
            "operator_action_ledger_endpoint_applies_patches",
            "operator_action_ledger_endpoint_writes_memory",
            "operator_action_ledger_endpoint_creates_release",
            "operator_action_ledger_endpoint_persists_cache",
            "operator_action_ledger_endpoint_auto_repairs_drift",
            "route_manifest_replaces_dashboard_routes",
            "route_manifest_generates_routes",
            "dashboard_wiring_generated",
            "api_wiring_generated",
            "generated_wiring_activated",
            "release_authorized",
            "autonomy_expanded",
            "expands_autonomy",
        ])
    )
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DOCTOR_DIAGNOSTIC_CACHE_IMPACT_OPERATOR_ACTION_LEDGER_ID,
        "state": "doctor_diagnostic_cache_impact_operator_action_ledger_only",
        "prior_total_behavioral_coverage_count": PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "new_impact_operator_action_ledger_behavioral_coverage_count": NEW_IMPACT_OPERATOR_ACTION_LEDGER_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": PRIOR_MAPPING_RECONCILED_ROUTE_COUNT,
        "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT,
        "impact_matrix_api_route": SEVERITY_ROUTE_IMPACT_MATRIX_API_ROUTE,
        "impact_operator_action_ledger_api_route": IMPACT_OPERATOR_ACTION_LEDGER_API_ROUTE,
        "source_cache_route": CACHE_API_ROUTE,
        "freshness_api_route": FRESHNESS_API_ROUTE,
        "impact_fixture_count": EXPECTED_IMPACT_FIXTURE_COUNT,
        "impact_surface_kind_count": EXPECTED_IMPACT_SURFACE_KIND_COUNT,
        "operator_action_ledger_row_count": len(rows),
        "operator_action_ledger_pass_count": sum(1 for row in rows if row.ok),
        "action_category_count": len(action_categories),
        "severity_labels": severity_labels,
        "action_categories": action_categories,
        "surface_kinds": surface_kinds,
        "informational_action_count": informational,
        "advisory_action_count": advisory,
        "warning_action_count": warning,
        "blocker_action_count": blocker,
        "targeted_verification_action_count": targeted_verification,
        "release_blocking_action_count": release_blocking,
        "operator_review_required_count": operator_review_required,
        "evidence_requirement_count": evidence_requirement_count,
        "auto_repair_action_count": auto_repair,
        "release_authorization_action_count": release_authorization,
        "autonomy_expansion_action_count": autonomy_expansion,
        "operator_action_ledger_rows": row_dicts,
        "source_files_mutated": SOURCE_FILES_MUTATED,
        "persisted_cache_written": PERSISTED_CACHE_WRITTEN,
        "live_diagnostic_measurements_performed": LIVE_DIAGNOSTIC_MEASUREMENTS_PERFORMED,
        "automatic_repair_performed": AUTOMATIC_REPAIR_PERFORMED,
        "release_authorized": RELEASE_AUTHORIZED,
        "autonomy_expanded": AUTONOMY_EXPANDED,
        "preview_only": True,
        "executes_live_work": False,
        "applies_patches": False,
        "writes_memory": False,
        "creates_release": False,
        "persists_cache": False,
        "auto_repairs_drift": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "route_manifest_replaces_dashboard_routes": False,
        "route_manifest_generates_routes": False,
        "dashboard_wiring_generated": False,
        "api_wiring_generated": False,
        "generated_wiring_activated": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "blocked": [asdict(row) for row in rows if not row.ok],
        "recommendations": [
            "Keep the operator action ledger review-only; do not auto-repair drift or authorize release from ledger rows.",
            "Treat blocker rows as release-blocking until operator-reviewed evidence passes.",
            "Run targeted dashboard/API/smoke verification for warning rows before release consideration.",
            "Use informational and advisory rows for operator visibility without changing manual dispatch authority.",
        ],
        "next_commands": [
            "python tools/smoke_check.py --check doctor-diagnostic-cache-impact-operator-action-ledger-v1 --json",
            "python tools/smoke_check.py --check doctor-diagnostic-cache-severity-route-impact-matrix-v1 --json",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1 --json",
        ],
        "message": "Doctor diagnostic cache impact matrix operator action ledger maps impact rows to review-only operator actions and evidence requirements without repair or release authority.",
    }


def build_doctor_diagnostic_cache_impact_operator_action_ledger(root: str | Path | None = None, project_id: str = "eidolon") -> dict[str, Any]:
    project_root = _repo(root)
    metadata = build_doctor_diagnostic_cache_impact_operator_action_ledger_metadata(project_id=project_id, root=project_root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_source = _read_text(project_root, "README_NEXT_STEPS.md") + "\n" + _read_text(project_root, "README_RELEASE_HISTORY.md")
    route_map = _route_renderer_map(dashboard_source)
    status, api_payload, elapsed_ms, api_error = _call_api(project_root, IMPACT_OPERATOR_ACTION_LEDGER_API_ROUTE + "?live=true&approve=true")
    api_data = api_payload.get("data") if isinstance(api_payload, dict) else None
    required_api_data_keys = {
        "ok",
        "operator_action_ledger_row_count",
        "operator_action_ledger_rows",
        "action_categories",
        "evidence_requirement_count",
        "auto_repair_action_count",
        "release_authorization_action_count",
        "autonomy_expansion_action_count",
        "preview_only",
    }
    missing_api_data_keys = sorted(required_api_data_keys - set(api_data.keys())) if isinstance(api_data, dict) else sorted(required_api_data_keys)
    api_payload_shape_pass = (
        status == 200
        and api_error is None
        and isinstance(api_payload, dict)
        and api_payload.get("ok") is True
        and isinstance(api_data, dict)
        and not missing_api_data_keys
        and isinstance(api_data.get("operator_action_ledger_rows"), list)
        and isinstance(api_data.get("action_categories"), list)
        and isinstance(api_data.get("recommendations"), list)
        and isinstance(api_data.get("next_commands"), list)
    )
    self_mapping = {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}
    api_index_present = '"GET /api/doctor/diagnostic-preview-cache/freshness/impact-operator-action-ledger"' in api_source
    api_handler_present = 'if parts == ["doctor", "diagnostic-preview-cache", "freshness", "impact-operator-action-ledger"]' in api_source
    required_tokens = [
        DOCTOR_DIAGNOSTIC_CACHE_IMPACT_OPERATOR_ACTION_LEDGER_ID,
        SELF_ROUTE,
        IMPACT_OPERATOR_ACTION_LEDGER_API_ROUTE,
        "build_doctor_diagnostic_cache_impact_operator_action_ledger_metadata",
        "build_doctor_diagnostic_cache_impact_operator_action_ledger",
        "doctor_diagnostic_cache_impact_operator_action_ledger_text",
        "prior_total_behavioral_coverage_count=115",
        "new_impact_operator_action_ledger_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=116",
        "prior_mapping_reconciled_route_count=121",
        "mapping_reconciled_route_count=122",
        "operator_action_ledger_row_count=18",
        "operator_action_ledger_pass_count=18",
        "action_category_count=4",
        "informational_action_count=3",
        "advisory_action_count=3",
        "warning_action_count=3",
        "blocker_action_count=9",
        "operator_review_required_count=18",
        "auto_repair_action_count=0",
        "release_authorization_action_count=0",
        "autonomy_expansion_action_count=0",
        "source_files_mutated=False",
        "persisted_cache_written=False",
        "live_diagnostic_measurements_performed=False",
        "automatic_repair_performed=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_still_required=True",
    ]
    rows = metadata.get("operator_action_ledger_rows", [])
    rows_status = [
        {"name": "impact-matrix-valid", "ok": metadata.get("ok") is True, "message": f"status={metadata.get('status')}"},
        {"name": "action-ledger-row-count", "ok": metadata.get("operator_action_ledger_row_count") == EXPECTED_ACTION_LEDGER_ROW_COUNT, "message": f"rows={metadata.get('operator_action_ledger_row_count')}"},
        {"name": "action-ledger-rows-pass", "ok": metadata.get("operator_action_ledger_pass_count") == EXPECTED_ACTION_LEDGER_ROW_COUNT and all(isinstance(row, dict) and row.get("ok") is True for row in rows), "message": f"passes={metadata.get('operator_action_ledger_pass_count')}"},
        {"name": "action-category-count", "ok": metadata.get("action_category_count") == EXPECTED_ACTION_CATEGORY_COUNT, "message": f"categories={metadata.get('action_categories')}"},
        {"name": "severity-action-counts", "ok": metadata.get("informational_action_count") == 3 and metadata.get("advisory_action_count") == 3 and metadata.get("warning_action_count") == 3 and metadata.get("blocker_action_count") == 9, "message": "informational=3 advisory=3 warning=3 blocker=9"},
        {"name": "operator-review-required", "ok": metadata.get("operator_review_required_count") == EXPECTED_OPERATOR_APPROVAL_REQUIRED_COUNT, "message": f"operator_review={metadata.get('operator_review_required_count')}"},
        {"name": "blocker-release-hold", "ok": metadata.get("release_blocking_action_count") == EXPECTED_BLOCKER_IMPACT_COUNT and all(not row.get("may_authorize_release") for row in rows if isinstance(row, dict)), "message": f"release_blocking={metadata.get('release_blocking_action_count')}"},
        {"name": "warning-targeted-verification", "ok": metadata.get("targeted_verification_action_count", 0) >= EXPECTED_WARNING_IMPACT_COUNT + EXPECTED_BLOCKER_IMPACT_COUNT, "message": f"targeted={metadata.get('targeted_verification_action_count')}"},
        {"name": "no-auto-repair", "ok": metadata.get("auto_repair_action_count") == 0 and metadata.get("automatic_repair_performed") is False and all(not row.get("may_auto_repair") for row in rows if isinstance(row, dict)), "message": "ledger rows never auto-repair drift."},
        {"name": "no-release-authorization", "ok": metadata.get("release_authorization_action_count") == 0 and metadata.get("release_authorized") is False, "message": "ledger rows never authorize release."},
        {"name": "no-autonomy-expansion", "ok": metadata.get("autonomy_expansion_action_count") == 0 and metadata.get("autonomy_expanded") is False, "message": "ledger rows never expand autonomy."},
        {"name": "api-index-present", "ok": api_index_present, "message": "API index documents the v1054 operator action ledger endpoint."},
        {"name": "api-handler-present", "ok": api_handler_present, "message": "Manual API dispatch handles the v1054 operator action ledger endpoint."},
        {"name": "api-payload-shape", "ok": api_payload_shape_pass, "message": f"status={status} elapsed_ms={elapsed_ms} missing={missing_api_data_keys}"},
        {"name": "behavioral-count", "ok": TOTAL_BEHAVIORAL_COVERAGE_COUNT == 116, "message": f"coverage={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-count", "ok": MAPPING_RECONCILED_ROUTE_COUNT == 122, "message": f"mapping={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "self-route-mapped", "ok": self_mapping["actual_renderer"] == self_mapping["expected_renderer"], "message": f"self_mapping={self_mapping}"},
        {"name": "manifest-surface-current", "ok": "v1054-doctor-diagnostic-cache-impact-operator-action-ledger" in manifest_source, "message": "Source surface manifest represents the v1054 operator action ledger surface."},
        {"name": "docs-current-tokens", "ok": all(token in readme_source + dashboard_source + smoke_source + manifest_source for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1054 operator action ledger truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["source_files_mutated", "persisted_cache_written", "live_diagnostic_measurements_performed", "automatic_repair_performed", "operator_action_ledger_endpoint_executes_live_work", "operator_action_ledger_endpoint_applies_patches", "operator_action_ledger_endpoint_writes_memory", "operator_action_ledger_endpoint_creates_release", "operator_action_ledger_endpoint_persists_cache", "operator_action_ledger_endpoint_auto_repairs_drift", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Operator action ledger remains preview-only and grants no authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows_status)
    report = dict(metadata)
    report.update({
        "api_operator_action_ledger_status": status,
        "api_operator_action_ledger_elapsed_ms": elapsed_ms,
        "api_operator_action_ledger_error": api_error,
        "api_operator_action_ledger_payload_shape_pass_count": 1 if api_payload_shape_pass else 0,
        "api_operator_action_ledger_pass_count": 1 if api_payload_shape_pass and isinstance(api_data, dict) and api_data.get("ok") is True else 0,
        "api_operator_action_ledger_rows": api_data.get("operator_action_ledger_rows", []) if isinstance(api_data, dict) else [],
        "api_index_present": api_index_present,
        "api_handler_present": api_handler_present,
        "self_mapping": self_mapping,
        "required_tokens_present": all(token in readme_source + dashboard_source + smoke_source + manifest_source for token in required_tokens),
        "required_tokens": required_tokens,
        "rows": rows_status,
        "blocked": [row for row in rows_status if not row["ok"]],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    })
    return report


def doctor_diagnostic_cache_impact_operator_action_ledger_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    data = report or build_doctor_diagnostic_cache_impact_operator_action_ledger()
    lines = [
        "# Doctor Diagnostic Cache Impact Matrix Operator Action Ledger v1",
        f"Version: {data.get('version')}",
        f"Status: {data.get('status')}",
        f"Milestone: {data.get('current_milestone')}",
        f"Dashboard route: {SELF_ROUTE}",
        f"API route: {IMPACT_OPERATOR_ACTION_LEDGER_API_ROUTE}",
        f"Review id: {DOCTOR_DIAGNOSTIC_CACHE_IMPACT_OPERATOR_ACTION_LEDGER_ID}",
        f"Action ledger rows: {data.get('operator_action_ledger_row_count')} pass={data.get('operator_action_ledger_pass_count')}",
        f"Actions: informational={data.get('informational_action_count')} advisory={data.get('advisory_action_count')} warning={data.get('warning_action_count')} blocker={data.get('blocker_action_count')}",
        f"Evidence requirements: {data.get('evidence_requirement_count')}",
        f"Authority: source_files_mutated={data.get('source_files_mutated')} persisted_cache_written={data.get('persisted_cache_written')} live_diagnostic_measurements_performed={data.get('live_diagnostic_measurements_performed')} automatic_repair_performed={data.get('automatic_repair_performed')} release_authorized={data.get('release_authorized')} autonomy_expanded={data.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("\n## Operator action rows")
        for row in data.get("operator_action_ledger_rows", []):
            lines.append(
                f"- {row.get('fixture_id')} [{row.get('surface_kind')}] severity={row.get('severity_label')} "
                f"target={row.get('affected_target')} action={row.get('action_category')} release={row.get('release_impact')} ok={row.get('ok')}"
            )
            for evidence in row.get("evidence_required", []):
                lines.append(f"  - evidence: {evidence}")
        blocked = data.get("blocked", [])
        if blocked:
            lines.append("\n## Blocked checks")
            for row in blocked:
                lines.append(f"- {row.get('name')}: {row.get('message')}")
        lines.append("\n## Recommendations")
        for item in data.get("recommendations", []):
            lines.append(f"- {item}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(doctor_diagnostic_cache_impact_operator_action_ledger_text(full=True))
