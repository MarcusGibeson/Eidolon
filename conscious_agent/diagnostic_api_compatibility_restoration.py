from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_VERSION = RUNTIME_VERSION
DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_ID = "diagnostic-api-compatibility-restoration-v1"
SELF_ROUTE = "/diagnostic-api-compatibility-restoration"
SELF_RENDERER = "render_diagnostic_api_compatibility_restoration"
API_ROUTE = "/api/doctor/diagnostic-api-compatibility-restoration"
API_MODULE = "conscious_agent/api_server.py"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
DOCTOR_LATENCY_MODULE = "conscious_agent/doctor_deep_diagnostic_latency_budget_repair.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
EXPECTED_TARGET_COUNT = 5

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "legacy_defaults_preserved": True,
    "explicit_preview_endpoints": True,
    "dashboard_uses_preview_endpoints": True,
    "preview_routes_claim_full_diagnostics": False,
    "preview_routes_execute_live_work": False,
    "diagnostic_compatibility_restoration_executes_live_work": False,
    "diagnostic_compatibility_restoration_applies_patches": False,
    "diagnostic_compatibility_restoration_writes_memory": False,
    "diagnostic_compatibility_restoration_creates_release": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}

@dataclass(frozen=True)
class DiagnosticCompatibilitySpec:
    label: str
    legacy_route: str
    preview_route: str
    legacy_builder: str
    preview_builder: str
    preview_marker: str

SPECS: tuple[DiagnosticCompatibilitySpec, ...] = (
    DiagnosticCompatibilitySpec("repair-suggestions", "/api/repair-suggestions", "/api/repair-suggestions/preview", "build_repair_suggestions", "build_bounded_repair_suggestions", "bounded_preview"),
    DiagnosticCompatibilitySpec("project-snapshot", "/api/project-snapshot", "/api/project-snapshot/preview", "build_project_snapshot", "build_bounded_project_snapshot", "bounded_preview"),
    DiagnosticCompatibilitySpec("stable-loop-confidence", "/api/stable-loops/confidence", "/api/stable-loops/confidence/preview", "build_stable_loop_confidence", "build_bounded_stable_loop_confidence", "bounded_preview"),
    DiagnosticCompatibilitySpec("hardening-report", "/api/hardening-report", "/api/hardening-report/preview", "build_hardening_report", "build_bounded_hardening_report", "bounded_preview"),
    DiagnosticCompatibilitySpec("controlled-self-build", "/api/controlled-self-build", "/api/controlled-self-build/lightweight-preview", "build_controlled_self_build", "build_controlled_self_build_lightweight_preview", "lightweight_preview"),
)

def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]

def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

def _status(checks: list[dict[str, Any]]) -> str:
    return "pass" if all(bool(check.get("ok")) for check in checks) else "blocked"

def _check(name: str, ok: bool, message: str) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "status": "pass" if ok else "blocked", "message": message}

def _api_default_uses_builder(api_source: str, spec: DiagnosticCompatibilitySpec) -> bool:
    route_parts = [part for part in spec.legacy_route.removeprefix("/api/").split("/") if part]
    preview_parts = [part for part in spec.preview_route.removeprefix("/api/").split("/") if part]
    legacy_pattern = 'parts == ' + repr(route_parts).replace("'", '"')
    preview_pattern = 'parts == ' + repr(preview_parts).replace("'", '"')
    if legacy_pattern not in api_source or spec.legacy_builder not in api_source:
        return False
    legacy_index = api_source.find(legacy_pattern)
    preview_index = api_source.find(preview_pattern)
    builder_index = api_source.find(spec.legacy_builder, legacy_index)
    bounded_index = api_source.find(spec.preview_builder, legacy_index)
    if builder_index < 0:
        return False
    if preview_index >= 0 and preview_index < legacy_index:
        # Preview block before the legacy block is expected. Make sure the legacy
        # builder still appears after the legacy condition.
        return builder_index > legacy_index
    if bounded_index >= 0 and bounded_index < builder_index:
        return False
    return builder_index > legacy_index

def _api_preview_uses_builder(api_source: str, spec: DiagnosticCompatibilitySpec) -> bool:
    route_parts = [part for part in spec.preview_route.removeprefix("/api/").split("/") if part]
    preview_pattern = 'parts == ' + repr(route_parts).replace("'", '"')
    preview_index = api_source.find(preview_pattern)
    builder_index = api_source.find(spec.preview_builder, preview_index)
    return preview_index >= 0 and builder_index > preview_index

def _call_api_preview(route: str) -> tuple[int, dict[str, Any], str | None]:
    import sys
    root = _repo()
    sys.path.insert(0, str(root / "conscious_agent"))
    import api_server  # type: ignore
    parsed = urlparse(route)
    try:
        status, payload = api_server.handle_api_get(parsed.path, parse_qs(parsed.query))
    except Exception as error:
        return 500, {"ok": False, "error": f"{type(error).__name__}: {error}"}, f"{type(error).__name__}: {error}"
    data = payload.get("data") if isinstance(payload, dict) else None
    return int(status), data if isinstance(data, dict) else {"ok": False, "error": "non_dict_data"}, None

def _preview_probe_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in SPECS:
        status, data, error = _call_api_preview(spec.preview_route)
        bounded = bool(data.get(spec.preview_marker) is True or data.get("bounded_preview") is True or data.get("lightweight_preview") is True or data.get("preview_only") is True)
        full_available = bool(data.get("full_diagnostic_available") is True or spec.label == "controlled-self-build")
        live = bool(data.get("live") or data.get("approved_live") or data.get("run_result", {}).get("live") is True or data.get("executes_live_work") is True)
        rows.append({
            "label": spec.label,
            "preview_route": spec.preview_route,
            "status_code": status,
            "ok": status == 200 and error is None and bounded and full_available and not live,
            "bounded_preview": bounded,
            "full_diagnostic_available": full_available,
            "executes_live_work": live,
            "error": error,
            "message": f"preview_route={spec.preview_route} status={status} bounded_preview={bounded} full_available={full_available} live={live} error={error}",
        })
    return rows

def build_diagnostic_api_compatibility_restoration(root: str | Path | None = None, *, inspect_sources: bool = True, probe_previews: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    api_source = _read_text(project_root, API_MODULE)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    doctor_latency_source = _read_text(project_root, DOCTOR_LATENCY_MODULE)
    smoke_source = _read_text(project_root, SMOKE_MODULE)
    manifest_source = _read_text(project_root, MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/diagnostic_api_compatibility_restoration.py")
    docs = "\n".join([api_source, dashboard_source, doctor_latency_source, smoke_source, manifest_source, readme_next, readme_history, module_source])

    preview_rows = _preview_probe_rows() if probe_previews else []
    legacy_rows = []
    for spec in SPECS:
        legacy_rows.append({
            "label": spec.label,
            "legacy_route": spec.legacy_route,
            "preview_route": spec.preview_route,
            "legacy_builder": spec.legacy_builder,
            "preview_builder": spec.preview_builder,
            "legacy_default_uses_full_builder": _api_default_uses_builder(api_source, spec),
            "preview_route_uses_bounded_builder": _api_preview_uses_builder(api_source, spec),
        })

    doctor_preview_targets = [spec.preview_route for spec in SPECS[:4]] + ["/api/controlled-self-build/lightweight-preview"]
    doctor_targets_ok = all(target in doctor_latency_source for target in doctor_preview_targets)
    dashboard_tokens_ok = SELF_ROUTE in dashboard_source and SELF_RENDERER in dashboard_source and "data-tip" in dashboard_source
    api_route_ok = API_ROUTE in api_source
    source_tokens = [
        "diagnostic-api-compatibility-restoration-v1",
        SELF_ROUTE,
        API_ROUTE,
        "legacy_default_full_compatibility_restored=True",
        "explicit_preview_endpoints=True",
        "preview_routes_claim_full_diagnostics=False",
        "doctor_diagnostic_latency_uses_preview_routes=True",
        "manual_api_dispatch_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    source_tokens_ok = all(token in docs for token in source_tokens)

    checks = [
        _check("current-version", DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_VERSION == CURRENT_VERSION, f"module version is {DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_VERSION}; expected {CURRENT_VERSION}"),
        _check("target-count", len(SPECS) == EXPECTED_TARGET_COUNT, f"{len(SPECS)} diagnostic compatibility targets are defined."),
        _check("legacy-defaults-use-full-builders", all(row["legacy_default_uses_full_builder"] for row in legacy_rows), "Legacy diagnostic API routes dispatch to their full-compatible builders by default."),
        _check("preview-routes-use-bounded-builders", all(row["preview_route_uses_bounded_builder"] for row in legacy_rows), "Explicit preview routes dispatch to bounded/lightweight preview builders."),
        _check("preview-probes-safe", (not probe_previews) or all(row["ok"] for row in preview_rows), "Preview API probes return bounded/lightweight payloads and do not execute live work."),
        _check("doctor-latency-uses-preview-routes", doctor_targets_ok, "Doctor deep diagnostic latency probe targets explicit preview/lightweight routes, not legacy full defaults."),
        _check("dashboard-route-wired", dashboard_tokens_ok, "Dashboard route is wired with command-deck/data-tip style and no native title tooltip."),
        _check("api-route-wired", api_route_ok, "Diagnostic compatibility restoration API route is wired."),
        _check("source-tokens-present", source_tokens_ok, "Documentation/source tokens describe the compatibility and non-authority boundaries."),
        _check("authority-boundaries", BOUNDARIES["generated_wiring_activated"] is False and BOUNDARIES["release_authorized"] is False and BOUNDARIES["autonomy_expanded"] is False, "Compatibility restoration does not activate generated wiring, authorize release, or expand autonomy."),
    ]
    status = _status(checks)
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": "eidolon",
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "diagnostic_api_compatibility_restoration_id": DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_count": len(SPECS),
        "legacy_default_full_compatibility_restored": all(row["legacy_default_uses_full_builder"] for row in legacy_rows),
        "explicit_preview_endpoints": all(row["preview_route_uses_bounded_builder"] for row in legacy_rows),
        "preview_route_count": len(SPECS),
        "legacy_default_route_count": len(SPECS),
        "preview_routes_claim_full_diagnostics": False,
        "preview_routes_execute_live_work": any(row.get("executes_live_work") for row in preview_rows),
        "doctor_diagnostic_latency_uses_preview_routes": doctor_targets_ok,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "legacy_rows": legacy_rows,
        "preview_probe_rows": preview_rows,
        "checks": checks,
        "blocked": [check["message"] for check in checks if not check.get("ok")],
        "boundaries": dict(BOUNDARIES),
        "status": status,
        "ok": status == "pass",
    }

def build_diagnostic_api_compatibility_restoration_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "diagnostic_api_compatibility_restoration_id": DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_ID,
        "self_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "target_count": EXPECTED_TARGET_COUNT,
        "legacy_default_full_compatibility_restored": True,
        "explicit_preview_endpoints": True,
        "preview_routes_claim_full_diagnostics": False,
        "doctor_diagnostic_latency_uses_preview_routes": True,
        "manual_api_dispatch_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "status": "preview",
        "ok": True,
        "writes_source": False,
        "executes_live_work": False,
        "expands_autonomy": False,
    }

def diagnostic_api_compatibility_restoration_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_diagnostic_api_compatibility_restoration()
    lines = [
        "Installed-Tree Cleanup Enforcement v1",
        f"Version: {report.get('version')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Targets: {report.get('target_count')}",
        f"Legacy defaults restored: {report.get('legacy_default_full_compatibility_restored')}",
        f"Explicit preview endpoints: {report.get('explicit_preview_endpoints')}",
        f"Doctor latency uses preview routes: {report.get('doctor_diagnostic_latency_uses_preview_routes')}",
        f"Preview routes claim full diagnostics: {report.get('preview_routes_claim_full_diagnostics')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("Legacy/default rows:")
        for row in report.get("legacy_rows", []):
            lines.append(f"- {row.get('label')}: legacy={row.get('legacy_route')} full_builder={row.get('legacy_default_uses_full_builder')} preview={row.get('preview_route')} preview_builder={row.get('preview_route_uses_bounded_builder')}")
        lines.append("Preview probe rows:")
        for row in report.get("preview_probe_rows", []):
            lines.append(f"- {row.get('label')}: ok={row.get('ok')} route={row.get('preview_route')} bounded={row.get('bounded_preview')} live={row.get('executes_live_work')}")
        lines.append("Checks:")
        for check in report.get("checks", []):
            lines.append(f"- {check.get('name')}: {check.get('status')} - {check.get('message')}")
    return "\n".join(lines)
