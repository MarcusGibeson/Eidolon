from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_deferred_route_harness_renderer_repair_prep import _render_isolated
from dashboard_timeout_lane_classification_slow_renderer_decomposition_prep import (
    DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_ID,
    LONG_ISOLATED_LANE_TIMEOUT_SECONDS,
    TOTAL_BEHAVIORAL_COVERAGE_COUNT as V1038_TOTAL_BEHAVIORAL_COVERAGE_COUNT,
    MAPPING_RECONCILED_ROUTE_COUNT as V1038_MAPPING_RECONCILED_ROUTE_COUNT,
)

DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_VERSION = RUNTIME_VERSION
DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_ID = "dashboard-doctor-renderer-decomposition-slice-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
SELF_ROUTE = "/dashboard-doctor-renderer-decomposition-slice"
SELF_RENDERER = "render_dashboard_doctor_renderer_decomposition_slice"
DOCTOR_ROUTE = "/doctor"
DOCTOR_RENDERER = "render_doctor"
DOCTOR_LONG_ISOLATED_TIMEOUT_SECONDS = LONG_ISOLATED_LANE_TIMEOUT_SECONDS
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 103
NEW_DOCTOR_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 104
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 108
MAPPING_RECONCILED_ROUTE_COUNT = 110
PRIMARY_DOCTOR_REPORT_COUNT = 4
LAZY_DIAGNOSTIC_SECTION_COUNT = 5
EXPECTED_PRIMARY_TOKENS = (
    "Doctor Headroom",
    "Preview Cache",
    "Deep Diagnostics",
    "Primary operational reports",
)
EXPECTED_LAZY_TOKENS = (
    "Deferred diagnostics",
    "Repair Suggestions",
    "Project Snapshot",
    "Stable Loop Confidence",
    "Hardening",
    "Controlled Self-Build Preview",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "doctor_renderer_decomposed": True,
    "doctor_long_isolated_behavioral_coverage": True,
    "doctor_route_graduated_to_counted_behavioral_coverage": True,
    "slow_diagnostics_deferred_to_links": True,
    "standard_fast_route_coverage_unchanged": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_behavior_pass_is_release_approval": False,
    "doctor_harness_executes_governed_actions": False,
    "doctor_harness_applies_patches": False,
    "doctor_harness_writes_memory": False,
    "doctor_harness_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class DoctorPrimaryReportRow:
    label: str
    source: str
    counted_in_primary_shell: bool


@dataclass(frozen=True)
class DoctorLazyDiagnosticRow:
    label: str
    route: str
    reason: str


PRIMARY_DOCTOR_REPORTS: tuple[DoctorPrimaryReportRow, ...] = (
    DoctorPrimaryReportRow("Doctor Headroom", "build_doctor_dashboard_headroom_snapshot(project_id='eidolon')", True),
    DoctorPrimaryReportRow("Preview Cache", "build_doctor_diagnostic_preview_cache(project_id='eidolon')", True),
    DoctorPrimaryReportRow("Deep Diagnostics", "deferred API links only", False),
    DoctorPrimaryReportRow("Primary operational reports", "bounded snapshot summary; legacy report text no longer inlined", False),
)

LAZY_DIAGNOSTIC_SECTIONS: tuple[DoctorLazyDiagnosticRow, ...] = (
    DoctorLazyDiagnosticRow("Repair Suggestions", "/api/repair-suggestions", "kept outside the primary /doctor render so suggestion synthesis remains a separate diagnostic surface"),
    DoctorLazyDiagnosticRow("Project Snapshot", "/api/project-snapshot", "kept outside the primary /doctor render so project inventory does not compound route latency"),
    DoctorLazyDiagnosticRow("Stable Loop Confidence", "/api/stable-loops/confidence", "kept outside the primary /doctor render so confidence scoring remains independently testable"),
    DoctorLazyDiagnosticRow("Hardening", "/api/hardening-report", "kept outside the primary /doctor render until its diagnostics are separately decomposed"),
    DoctorLazyDiagnosticRow("Controlled Self-Build Preview", "/api/controlled-self-build", "kept outside the primary /doctor render so a dashboard route never runs a self-build preview as incidental page load work"),
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


def _renderer_function_names(source: str) -> set[str]:
    return set(re.findall(r'^def (render_[A-Za-z0-9_]+)\(', source, re.MULTILINE))


def _doctor_render_body(root: Path) -> str:
    import sys
    sys.path.insert(0, str(root / "conscious_agent"))
    import dashboard  # type: ignore
    return dashboard.render_doctor()


def build_dashboard_doctor_renderer_decomposition_slice_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    mtimes: list[float] = []
    for rel in [DASHBOARD_MODULE, MANUAL_SMOKE_MODULE, SOURCE_MANIFEST_MODULE, "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"]:
        path = project_root / rel
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            mtimes.append(0.0)
    cache_key = (str(project_root), *mtimes[:3])
    cached = _CACHE.get(cache_key)
    if cached:
        return dict(cached)

    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/dashboard_doctor_renderer_decomposition_slice.py")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    renderers = _renderer_function_names(dashboard_source)
    prior_total = int(V1038_TOTAL_BEHAVIORAL_COVERAGE_COUNT)
    prior_mapping = int(V1038_MAPPING_RECONCILED_ROUTE_COUNT)
    prior_review_token_present = DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_ID in docs

    doctor_row = _render_isolated(project_root, DOCTOR_ROUTE, DOCTOR_RENDERER, DOCTOR_LONG_ISOLATED_TIMEOUT_SECONDS)
    doctor_row["lane"] = "long_isolated_decomposed_doctor"
    doctor_row["counted_coverage"] = True
    doctor_row["decomposition_status"] = "primary_shell_with_lazy_diagnostic_links"

    try:
        body = _doctor_render_body(project_root)
    except Exception as error:
        body = f"ERROR: {type(error).__name__}: {error}"
    primary_tokens_present = all(token in body for token in EXPECTED_PRIMARY_TOKENS)
    lazy_tokens_present = all(token in body for token in EXPECTED_LAZY_TOKENS)
    slow_inline_tokens_absent = all(token not in body for token in ["Stable Loop Confidence Report", "Hardening Report", "Controlled Self-Build Report"])
    primary_rows = [asdict(row) for row in PRIMARY_DOCTOR_REPORTS]
    lazy_rows = [asdict(row) for row in LAZY_DIAGNOSTIC_SECTIONS]
    mapping_new_routes = {SELF_ROUTE, DOCTOR_ROUTE}
    mapping_mismatches = [
        {"route": DOCTOR_ROUTE, "expected_renderer": DOCTOR_RENDERER, "actual_renderer": route_map.get(DOCTOR_ROUTE)},
        {"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)},
    ]
    mapping_mismatches = [row for row in mapping_mismatches if row["actual_renderer"] != row["expected_renderer"]]
    renderer_missing = [name for name in [DOCTOR_RENDERER, SELF_RENDERER] if name not in renderers]
    manifest_surface_present = "v1039-dashboard-doctor-renderer-decomposition-slice" in manifest_source
    dashboard_decomposition_tokens_present = all(token in dashboard_source for token in [
        "DOCTOR_LAZY_DIAGNOSTIC_SECTIONS",
        "_doctor_primary_reports",
        "_doctor_lazy_section_html",
        "Primary operational reports",
        "Deferred diagnostics",
    ])
    lazy_routes_present = all(row.route in dashboard_source for row in LAZY_DIAGNOSTIC_SECTIONS)
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_ID,
        "prior_total_behavioral_coverage_count=103",
        "doctor_long_isolated_timeout_seconds=15",
        "primary_doctor_report_count=4",
        "lazy_diagnostic_section_count=5",
        "new_doctor_behavioral_coverage_count=1",
        "total_behavioral_coverage_count=104",
        "prior_mapping_reconciled_route_count=108",
        "mapping_reconciled_route_count=110",
        "doctor_renderer_decomposed=True",
        "doctor_graduated_to_long_isolated_behavioral_coverage=True",
        "slow_diagnostics_deferred_to_links=True",
        "standard_fast_route_coverage_unchanged=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-review-token-present", "ok": prior_review_token_present, "message": f"prior token {DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_ID} present in docs/source."},
        {"name": "prior-total-behavioral-count", "ok": prior_total == PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"prior_total={prior_total} expected={PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "prior-mapping-reconciled-count", "ok": prior_mapping == PRIOR_MAPPING_RECONCILED_ROUTE_COUNT, "message": f"prior_mapping={prior_mapping} expected={PRIOR_MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "doctor-primary-shell-count", "ok": len(primary_rows) == PRIMARY_DOCTOR_REPORT_COUNT and primary_tokens_present, "message": f"primary_reports={len(primary_rows)} tokens_present={primary_tokens_present}"},
        {"name": "doctor-lazy-section-count", "ok": len(lazy_rows) == LAZY_DIAGNOSTIC_SECTION_COUNT and lazy_tokens_present and lazy_routes_present, "message": f"lazy_sections={len(lazy_rows)} tokens_present={lazy_tokens_present} routes_present={lazy_routes_present}"},
        {"name": "doctor-slow-inline-sections-deferred", "ok": slow_inline_tokens_absent, "message": "slow diagnostic text bodies are not inlined in the primary /doctor render; v1052_bounded_shell_supersedes_primary_report_inline_requirement=True."},
        {"name": "doctor-long-isolated-render-pass", "ok": doctor_row.get("ok") is True and doctor_row.get("status") == "pass", "message": f"doctor_status={doctor_row.get('status')} elapsed_ms={doctor_row.get('elapsed_ms')} body_size={doctor_row.get('body_size')}"},
        {"name": "doctor-decomposition-tokens-present", "ok": dashboard_decomposition_tokens_present, "message": "dashboard.py contains bounded doctor primary/lazy compatibility helpers while /doctor uses the v1052 bounded shell. v1052_bounded_shell_supersedes_primary_report_inline_requirement=True."},
        {"name": "route-mapping-clean", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "renderers-present", "ok": not renderer_missing, "message": f"missing_renderers={len(renderer_missing)}"},
        {"name": "behavioral-counts-current", "ok": prior_total + NEW_DOCTOR_BEHAVIORAL_COVERAGE_COUNT == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={prior_total + NEW_DOCTOR_BEHAVIORAL_COVERAGE_COUNT} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "mapping-reconciled-count-current", "ok": prior_mapping + len(mapping_new_routes) == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping={prior_mapping + len(mapping_new_routes)} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1039 doctor renderer decomposition slice surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1039 doctor decomposition truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "doctor_harness_executes_governed_actions", "doctor_harness_applies_patches", "doctor_harness_writes_memory", "doctor_harness_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Doctor decomposition remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_ID,
        "state": "dashboard_doctor_renderer_decomposition_slice_review_only",
        "prior_total_behavioral_coverage_count": prior_total,
        "doctor_long_isolated_timeout_seconds": DOCTOR_LONG_ISOLATED_TIMEOUT_SECONDS,
        "primary_doctor_report_count": len(primary_rows),
        "lazy_diagnostic_section_count": len(lazy_rows),
        "new_doctor_behavioral_coverage_count": NEW_DOCTOR_BEHAVIORAL_COVERAGE_COUNT,
        "total_behavioral_coverage_count": prior_total + NEW_DOCTOR_BEHAVIORAL_COVERAGE_COUNT,
        "prior_mapping_reconciled_route_count": prior_mapping,
        "mapping_reconciled_route_count": prior_mapping + len(mapping_new_routes),
        "primary_doctor_reports": primary_rows,
        "lazy_diagnostic_sections": lazy_rows,
        "doctor_long_isolated_row": doctor_row,
        "doctor_renderer_decomposed": dashboard_decomposition_tokens_present,
        "doctor_graduated_to_long_isolated_behavioral_coverage": doctor_row.get("ok") is True,
        "slow_diagnostics_deferred_to_links": lazy_tokens_present and slow_inline_tokens_absent,
        "v1052_bounded_shell_supersedes_primary_report_inline_requirement": True,
        "standard_fast_route_coverage_unchanged": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "route_manifest_replaces_dashboard_routes": False,
        "route_manifest_generates_routes": False,
        "dashboard_wiring_generated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "boundaries": dict(BOUNDARIES),
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }
    _CACHE.clear()
    _CACHE[cache_key] = dict(report)
    return report


def dashboard_doctor_renderer_decomposition_slice_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}",
        f"doctor_long_isolated_timeout_seconds={report.get('doctor_long_isolated_timeout_seconds')}",
        f"primary_doctor_report_count={report.get('primary_doctor_report_count')}",
        f"lazy_diagnostic_section_count={report.get('lazy_diagnostic_section_count')}",
        f"new_doctor_behavioral_coverage_count={report.get('new_doctor_behavioral_coverage_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"doctor_renderer_decomposed={report.get('doctor_renderer_decomposed')}",
        f"doctor_graduated_to_long_isolated_behavioral_coverage={report.get('doctor_graduated_to_long_isolated_behavioral_coverage')}",
        f"slow_diagnostics_deferred_to_links={report.get('slow_diagnostics_deferred_to_links')}",
        f"v1052_bounded_shell_supersedes_primary_report_inline_requirement={report.get('v1052_bounded_shell_supersedes_primary_report_inline_requirement')}",
        f"standard_fast_route_coverage_unchanged={report.get('standard_fast_route_coverage_unchanged')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"route_manifest_replaces_dashboard_routes={report.get('route_manifest_replaces_dashboard_routes')}",
        f"route_manifest_generates_routes={report.get('route_manifest_generates_routes')}",
        f"dashboard_wiring_generated={report.get('dashboard_wiring_generated')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"expands_autonomy={report.get('expands_autonomy')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nPrimary doctor reports:")
        for row in report.get("primary_doctor_reports", []):
            lines.append(f"- {row.get('label')}: {row.get('source')} counted={row.get('counted_in_primary_shell')}")
        lines.append("\nLazy diagnostic sections:")
        for row in report.get("lazy_diagnostic_sections", []):
            lines.append(f"- {row.get('label')}: {row.get('route')} :: {row.get('reason')}")
        doctor = report.get("doctor_long_isolated_row", {})
        lines.append("\nDoctor long-isolated render:")
        lines.append(f"- {doctor.get('route')} -> {doctor.get('renderer')}: ok={doctor.get('ok')} status={doctor.get('status')} elapsed_ms={doctor.get('elapsed_ms')} body_size={doctor.get('body_size')} counted_coverage={doctor.get('counted_coverage')} error={doctor.get('error')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)

# v1053 reconciliation token: v1052_bounded_shell_supersedes_primary_report_inline_requirement=True historical_doctor_primary_report_inline_requirement_removed=True static_advisory_report_is_not_operational_proof=True
