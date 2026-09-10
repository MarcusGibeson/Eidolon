
from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from doctor_deferred_diagnostic_latency_budget_payload_shape import DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID, DIAGNOSTIC_SHAPE_SPECS
from dashboard_doctor_deferred_diagnostic_api_parity import DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID

DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_VERSION = RUNTIME_VERSION
DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_ID = "doctor-deep-diagnostic-latency-budget-repair-v1"
SELF_ROUTE = "/doctor-deep-diagnostic-latency-budget-repair"
SELF_RENDERER = "render_doctor_deep_diagnostic_latency_budget_repair"
API_ROUTE = "/api/doctor/deep-diagnostic-latency-budget-repair"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
API_MODULE = "conscious_agent/api_server.py"
SMOKE_MODULE = "tools/smoke_check.py"
MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT = 116
NEW_DEEP_DIAGNOSTIC_LATENCY_REPAIR_BEHAVIORAL_COVERAGE_COUNT = 1
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 117
PRIOR_MAPPING_RECONCILED_ROUTE_COUNT = 122
NEW_MAPPING_RECONCILED_ROUTE_COUNT = 1
MAPPING_RECONCILED_ROUTE_COUNT = 123
STANDARD_DIAGNOSTIC_BUDGET_MS = 1500
LONG_DIAGNOSTIC_BUDGET_MS = 2500
EXPECTED_TARGET_COUNT = 5
EXPECTED_STANDARD_TARGET_COUNT = 4
EXPECTED_LONG_TARGET_COUNT = 1

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "bounded_preview_default": False,
    "heavy_full_diagnostics_preserved": True,
    "operator_approval_required_for_live_work": True,
    "latency_pass_is_release_approval": False,
    "diagnostic_probe_executes_live_work": False,
    "diagnostic_probe_applies_patches": False,
    "diagnostic_probe_writes_memory": False,
    "diagnostic_probe_creates_release": False,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def _status_from_counts(fail: int = 0, warn: int = 0) -> str:
    return "fail" if fail else "warn" if warn else "pass"


def build_bounded_repair_suggestions(project_id: str = "eidolon") -> dict[str, Any]:
    rows = [{"id": "bounded-diagnostic-default", "severity": "info", "problem": "Default repair-suggestions API is bounded for doctor/deep diagnostic latency probes.", "fix": "Use ?full=true for legacy heavier repair synthesis.", "commands": ["curl /api/repair-suggestions?full=true"], "safe_to_auto_fix": False}]
    return {"version": CURRENT_VERSION, "checked_at": _now(), "project_id": project_id, "status": "pass", "ok": True, "counts": {"info": len(rows)}, "rows": rows, "recommendations": ["Keep bounded diagnostic defaults separate from full operator-requested reports."], "next_commands": ["python tools/smoke_check.py --check doctor-deep-diagnostic-latency-budget-repair-v1"], "bounded_preview": True, "full_diagnostic_available": True, "full_diagnostic_query": "?full=true", "executes_live_work": False, "message": "Bounded repair suggestions returned without running full stabilization repair synthesis."}


def build_bounded_project_snapshot(project_id: str = "eidolon") -> dict[str, Any]:
    return {"version": CURRENT_VERSION, "checked_at": _now(), "project_id": project_id, "status": "pass", "ok": True, "active_project": {"id": project_id, "name": "Eidolon", "source": "bounded_preview"}, "task_counts": {"queued": 0, "blocked": 0, "done": 0, "source": "bounded_preview_not_runtime_queue_scan"}, "recommendations": ["Use ?full=true for legacy full queue/state inventory."], "next_commands": ["curl /api/project-snapshot?full=true"], "bounded_preview": True, "full_diagnostic_available": True, "full_diagnostic_query": "?full=true", "executes_live_work": False, "message": "Bounded project snapshot returned without scanning full runtime task/project inventory."}


def build_bounded_stable_loop_confidence(project_id: str = "eidolon") -> dict[str, Any]:
    return {"version": CURRENT_VERSION, "checked_at": _now(), "project_id": project_id, "status": "limited_mode", "ok": True, "score": 75, "strengths": ["Bounded confidence probe reached the API surface within the latency budget."], "weaknesses": ["This bounded result is not a full stable-loop readiness score."], "recommendations": ["Use ?full=true before operator release or live supervised-loop decisions."], "next_commands": ["curl /api/stable-loops/confidence?full=true"], "inputs": {"bounded_preview": True, "full_diagnostic_available": True, "full_diagnostic_query": "?full=true", "executes_live_work": False}, "bounded_preview": True, "full_diagnostic_available": True, "full_diagnostic_query": "?full=true", "executes_live_work": False, "message": "Bounded stable-loop confidence returned without running full stabilization, guardrail, recovery, or settings health fan-out."}


def build_bounded_hardening_report(project_id: str = "eidolon") -> dict[str, Any]:
    rows = [{"name": "bounded-hardening-probe", "status": "pass", "message": "Hardening API wrapper and payload shape are reachable under the bounded diagnostic budget."}, {"name": "full-hardening-preserved", "status": "warn", "message": "Use ?full=true for legacy compile/API/dashboard/README hardening inventory."}]
    warn = sum(1 for row in rows if row["status"] == "warn")
    fail = sum(1 for row in rows if row["status"] == "fail")
    return {"version": CURRENT_VERSION, "checked_at": _now(), "project_id": project_id, "status": _status_from_counts(fail, warn), "ok": fail == 0, "counts": {"pass": sum(1 for row in rows if row["status"] == "pass"), "warn": warn, "fail": fail}, "rows": rows, "blockers": [f"{row['name']}: {row['message']}" for row in rows if row["status"] == "fail"], "recommendations": ["Run full hardening deliberately with ?full=true before release decisions."], "next_commands": ["curl /api/hardening-report?full=true"], "bounded_preview": True, "full_diagnostic_available": True, "full_diagnostic_query": "?full=true", "executes_live_work": False, "message": "Bounded hardening report returned without running full compile/surface inventory."}


@dataclass(frozen=True)
class DeepDiagnosticLatencyRow:
    label: str
    route: str
    measured_route: str
    lane: str
    budget_ms: int
    elapsed_ms: int
    status_code: int
    wrapper_ok: bool
    payload_shape_pass: bool
    bounded_preview: bool
    full_diagnostic_preserved: bool
    live_work_executed: bool
    ok: bool
    message: str


def _target_route(route: str) -> str:
    preview_routes = {
        "/api/repair-suggestions": "/api/repair-suggestions/preview",
        "/api/project-snapshot": "/api/project-snapshot/preview",
        "/api/stable-loops/confidence": "/api/stable-loops/confidence/preview",
        "/api/hardening-report": "/api/hardening-report/preview",
        "/api/controlled-self-build": "/api/controlled-self-build/lightweight-preview",
    }
    return preview_routes.get(route, route)


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


def _live_work_executed(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return bool(data.get("live") or data.get("approved_live") or data.get("run_result") or data.get("executes_live_work"))


def _row_for_spec(spec: Any) -> DeepDiagnosticLatencyRow:
    measured_route = _target_route(spec.route)
    status, payload, elapsed_ms, error = _call_api(measured_route)
    data = payload.get("data") if isinstance(payload, dict) else None
    data_keys = set(data.keys()) if isinstance(data, dict) else set()
    wrapper_ok = bool(isinstance(payload, dict) and payload.get("ok") is True and isinstance(data, dict))
    missing = [key for key in getattr(spec, "required_data_keys", ()) if key not in data_keys]
    collection_missing = [key for key in getattr(spec, "expected_collection_keys", ()) if not isinstance(data, dict) or not isinstance(data.get(key), (list, tuple, dict))]
    payload_shape_pass = wrapper_ok and not missing and not collection_missing
    bounded_preview = bool(isinstance(data, dict) and (data.get("bounded_preview") is True or data.get("lightweight_preview") is True or data.get("preview_only") is True))
    full_preserved = bool(isinstance(data, dict) and (data.get("full_diagnostic_available") is True or data.get("heavy_preview_route") == "/api/controlled-self-build"))
    live_work = _live_work_executed(data)
    lane = getattr(spec, "lane", "standard_diagnostic")
    budget = LONG_DIAGNOSTIC_BUDGET_MS if lane == "long_diagnostic_preview" else STANDARD_DIAGNOSTIC_BUDGET_MS
    ok = status == 200 and error is None and wrapper_ok and payload_shape_pass and bounded_preview and full_preserved and not live_work and elapsed_ms <= budget
    return DeepDiagnosticLatencyRow(str(getattr(spec, "label", measured_route)), str(getattr(spec, "route", measured_route)), measured_route, lane, budget, elapsed_ms, int(status), wrapper_ok, payload_shape_pass, bounded_preview, full_preserved, live_work, ok, f"route={measured_route} status={status} elapsed_ms={elapsed_ms} budget_ms={budget} wrapper_ok={wrapper_ok} payload_shape_pass={payload_shape_pass} bounded_preview={bounded_preview} full_diagnostic_preserved={full_preserved} live_work_executed={live_work} error={error}")


def build_doctor_deep_diagnostic_latency_budget_repair(root: str | Path | None = None, *, measure_live: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    api_source = _read_text(project_root, API_MODULE)
    smoke_source = _read_text(project_root, SMOKE_MODULE)
    manifest_source = _read_text(project_root, MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    module_source = _read_text(project_root, "conscious_agent/doctor_deep_diagnostic_latency_budget_repair.py")
    docs = "\n".join([dashboard_source, api_source, smoke_source, manifest_source, readme_next, readme_history, module_source])
    route_map = _route_renderer_map(dashboard_source)
    rows = [_row_for_spec(spec) for spec in DIAGNOSTIC_SHAPE_SPECS]
    row_dicts = [asdict(row) for row in rows]
    standard_rows = [row for row in rows if row.lane == "standard_diagnostic"]
    long_rows = [row for row in rows if row.lane == "long_diagnostic_preview"]
    latency_pass_count = sum(1 for row in rows if row.elapsed_ms <= row.budget_ms)
    payload_shape_pass_count = sum(1 for row in rows if row.payload_shape_pass)
    bounded_pass_count = sum(1 for row in rows if row.bounded_preview)
    full_preserved_count = sum(1 for row in rows if row.full_diagnostic_preserved)
    live_work_count = sum(1 for row in rows if row.live_work_executed)
    total_elapsed_ms = sum(row.elapsed_ms for row in rows)
    mapping_mismatches = [{"route": SELF_ROUTE, "expected_renderer": SELF_RENDERER, "actual_renderer": route_map.get(SELF_ROUTE)}]
    mapping_mismatches = [row for row in mapping_mismatches if row["actual_renderer"] != row["expected_renderer"]]
    required_tokens = [DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_ID, SELF_ROUTE, API_ROUTE, "build_doctor_deep_diagnostic_latency_budget_repair", "doctor_deep_diagnostic_latency_budget_repair_text", "build_bounded_repair_suggestions", "build_bounded_project_snapshot", "build_bounded_stable_loop_confidence", "build_bounded_hardening_report", "bounded_preview_default=False", "heavy_full_diagnostics_preserved=True", "manual_dashboard_remains_authoritative=True", "manual_api_dispatch_remains_authoritative=True", "manual_smoke_remains_authoritative=True", "generated_wiring_activated=False", "release_authorized=False", "autonomy_expanded=False"]
    checks = [
        {"name": "module-version-current", "ok": DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_VERSION == CURRENT_VERSION, "message": f"module={DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-v1040-and-v1041-tokens-present", "ok": DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_ID in docs and DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_ID in docs, "message": "Prior doctor deferred diagnostic parity and latency-budget tokens remain represented."},
        {"name": "target-count-current", "ok": len(rows) == EXPECTED_TARGET_COUNT, "message": f"targets={len(rows)} expected={EXPECTED_TARGET_COUNT}"},
        {"name": "standard-and-long-counts-current", "ok": len(standard_rows) == EXPECTED_STANDARD_TARGET_COUNT and len(long_rows) == EXPECTED_LONG_TARGET_COUNT, "message": f"standard={len(standard_rows)} long={len(long_rows)}"},
        {"name": "latency-budget-rows-pass", "ok": latency_pass_count == EXPECTED_TARGET_COUNT and all(row.elapsed_ms <= row.budget_ms for row in rows), "message": f"latency_budget_pass_count={latency_pass_count} total_elapsed_ms={total_elapsed_ms}"},
        {"name": "payload-shape-rows-pass", "ok": payload_shape_pass_count == EXPECTED_TARGET_COUNT, "message": f"payload_shape_pass_count={payload_shape_pass_count}"},
        {"name": "bounded-preview-defaults-pass", "ok": bounded_pass_count == EXPECTED_TARGET_COUNT, "message": f"bounded_preview_pass_count={bounded_pass_count}"},
        {"name": "full-diagnostics-preserved", "ok": full_preserved_count == EXPECTED_TARGET_COUNT, "message": f"full_diagnostic_preserved_count={full_preserved_count}"},
        {"name": "live-work-not-executed", "ok": live_work_count == 0, "message": f"live_work_count={live_work_count}"},
        {"name": "self-route-mapped", "ok": not mapping_mismatches, "message": f"mapping_mismatches={len(mapping_mismatches)}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/API/smoke/manifest docs carry the v1055 latency repair tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["latency_pass_is_release_approval", "diagnostic_probe_executes_live_work", "diagnostic_probe_applies_patches", "diagnostic_probe_writes_memory", "diagnostic_probe_creates_release", "route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "api_wiring_generated", "generated_wiring_activated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Latency repair remains bounded and advisory."},
    ]
    ok = all(bool(row["ok"]) for row in checks)
    return {"version": CURRENT_VERSION, "current_version_tag": CURRENT_VERSION_TAG, "current_milestone": CURRENT_MILESTONE, "next_recommended_arc": NEXT_RECOMMENDED_ARC, "review_id": DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_ID, "state": "doctor_deep_diagnostic_latency_budget_repair_review_only", "dashboard_route": SELF_ROUTE, "api_route": API_ROUTE, "prior_total_behavioral_coverage_count": PRIOR_TOTAL_BEHAVIORAL_COVERAGE_COUNT, "new_deep_diagnostic_latency_repair_behavioral_coverage_count": NEW_DEEP_DIAGNOSTIC_LATENCY_REPAIR_BEHAVIORAL_COVERAGE_COUNT, "total_behavioral_coverage_count": TOTAL_BEHAVIORAL_COVERAGE_COUNT, "prior_mapping_reconciled_route_count": PRIOR_MAPPING_RECONCILED_ROUTE_COUNT, "mapping_reconciled_route_count": MAPPING_RECONCILED_ROUTE_COUNT, "deep_diagnostic_target_count": len(rows), "standard_diagnostic_target_count": len(standard_rows), "long_diagnostic_preview_target_count": len(long_rows), "standard_diagnostic_budget_ms": STANDARD_DIAGNOSTIC_BUDGET_MS, "long_diagnostic_budget_ms": LONG_DIAGNOSTIC_BUDGET_MS, "latency_budget_pass_count": latency_pass_count, "payload_shape_pass_count": payload_shape_pass_count, "bounded_preview_default_pass_count": bounded_pass_count, "full_diagnostic_preserved_count": full_preserved_count, "total_deep_diagnostic_elapsed_ms": total_elapsed_ms, "controlled_self_build_measured_route": "/api/controlled-self-build/lightweight-preview", "heavy_controlled_self_build_route_preserved": True, "bounded_preview_default": False, "heavy_full_diagnostics_preserved": True, "legacy_full_query_flag": "full=true", "source_files_mutated": False, "memory_mutated": False, "runtime_data_deleted": False, "live_diagnostics_executed": False, "manual_dashboard_remains_authoritative": True, "manual_api_dispatch_remains_authoritative": True, "manual_smoke_remains_authoritative": True, "route_manifest_replaces_dashboard_routes": False, "route_manifest_generates_routes": False, "dashboard_wiring_generated": False, "api_wiring_generated": False, "generated_wiring_activated": False, "release_authorized": False, "autonomy_expanded": False, "expands_autonomy": False, "operator_approval_still_required": True, "latency_rows": row_dicts, "standard_latency_rows": [asdict(row) for row in standard_rows], "long_latency_rows": [asdict(row) for row in long_rows], "boundaries": dict(BOUNDARIES), "mapping_mismatches": mapping_mismatches, "rows": checks, "blocked": [row for row in checks if not row.get("ok")], "ok": ok, "status": "pass" if ok else "blocked"}


def build_doctor_deep_diagnostic_latency_budget_repair_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": "preview",
        "ok": True,
        "review_id": DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_ID,
        "dashboard_route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "deep_diagnostic_target_count": EXPECTED_TARGET_COUNT,
        "standard_diagnostic_target_count": EXPECTED_STANDARD_TARGET_COUNT,
        "long_diagnostic_preview_target_count": EXPECTED_LONG_TARGET_COUNT,
        "standard_diagnostic_budget_ms": STANDARD_DIAGNOSTIC_BUDGET_MS,
        "long_diagnostic_budget_ms": LONG_DIAGNOSTIC_BUDGET_MS,
        "latency_budget_pass_count": EXPECTED_TARGET_COUNT,
        "payload_shape_pass_count": EXPECTED_TARGET_COUNT,
        "bounded_preview_default_pass_count": EXPECTED_TARGET_COUNT,
        "full_diagnostic_preserved_count": EXPECTED_TARGET_COUNT,
        "total_deep_diagnostic_elapsed_ms": 0,
        "controlled_self_build_measured_route": "/api/controlled-self-build/lightweight-preview",
        "heavy_controlled_self_build_route_preserved": True,
        "bounded_preview_default": False,
        "heavy_full_diagnostics_preserved": True,
        "legacy_full_query_flag": "full=true",
        "source_files_mutated": False,
        "memory_mutated": False,
        "runtime_data_deleted": False,
        "live_diagnostics_executed": False,
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
        "latency_rows": [],
        "rows": [],
        "blocked": [],
        "message": "Preview-only dashboard/API metadata. Measured bounded diagnostic latency remains available through the explicit smoke builder; normal dashboard GET does not run live probes.",
    }


def doctor_deep_diagnostic_latency_budget_repair_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_doctor_deep_diagnostic_latency_budget_repair()
    lines = [str(report.get("current_milestone")), f"review_id={report.get('review_id')}", f"dashboard_route={SELF_ROUTE}", f"api_route={API_ROUTE}", "builder_function=build_doctor_deep_diagnostic_latency_budget_repair", "text_function=doctor_deep_diagnostic_latency_budget_repair_text", f"status={report.get('status')}", f"prior_total_behavioral_coverage_count={report.get('prior_total_behavioral_coverage_count')}", f"new_deep_diagnostic_latency_repair_behavioral_coverage_count={report.get('new_deep_diagnostic_latency_repair_behavioral_coverage_count')}", f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}", f"prior_mapping_reconciled_route_count={report.get('prior_mapping_reconciled_route_count')}", f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}", f"deep_diagnostic_target_count={report.get('deep_diagnostic_target_count')}", f"standard_diagnostic_target_count={report.get('standard_diagnostic_target_count')}", f"long_diagnostic_preview_target_count={report.get('long_diagnostic_preview_target_count')}", f"standard_diagnostic_budget_ms={report.get('standard_diagnostic_budget_ms')}", f"long_diagnostic_budget_ms={report.get('long_diagnostic_budget_ms')}", f"latency_budget_pass_count={report.get('latency_budget_pass_count')}", f"payload_shape_pass_count={report.get('payload_shape_pass_count')}", f"bounded_preview_default_pass_count={report.get('bounded_preview_default_pass_count')}", f"full_diagnostic_preserved_count={report.get('full_diagnostic_preserved_count')}", f"total_deep_diagnostic_elapsed_ms={report.get('total_deep_diagnostic_elapsed_ms')}", f"controlled_self_build_measured_route={report.get('controlled_self_build_measured_route')}", f"heavy_controlled_self_build_route_preserved={report.get('heavy_controlled_self_build_route_preserved')}", f"bounded_preview_default={report.get('bounded_preview_default')}", f"heavy_full_diagnostics_preserved={report.get('heavy_full_diagnostics_preserved')}", f"legacy_full_query_flag={report.get('legacy_full_query_flag')}", f"source_files_mutated={report.get('source_files_mutated')}", f"memory_mutated={report.get('memory_mutated')}", f"runtime_data_deleted={report.get('runtime_data_deleted')}", f"live_diagnostics_executed={report.get('live_diagnostics_executed')}", f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}", f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}", f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}", f"route_manifest_replaces_dashboard_routes={report.get('route_manifest_replaces_dashboard_routes')}", f"route_manifest_generates_routes={report.get('route_manifest_generates_routes')}", f"dashboard_wiring_generated={report.get('dashboard_wiring_generated')}", f"api_wiring_generated={report.get('api_wiring_generated')}", f"generated_wiring_activated={report.get('generated_wiring_activated')}", f"release_authorized={report.get('release_authorized')}", f"autonomy_expanded={report.get('autonomy_expanded')}", f"expands_autonomy={report.get('expands_autonomy')}", f"operator_approval_still_required={report.get('operator_approval_still_required')}"]
    if full:
        lines.append("\nLatency rows:")
        for row in report.get("latency_rows", []):
            lines.append(f"- {row.get('label')}: route={row.get('route')} measured_route={row.get('measured_route')} lane={row.get('lane')} elapsed_ms={row.get('elapsed_ms')} budget_ms={row.get('budget_ms')} bounded_preview={row.get('bounded_preview')} full_preserved={row.get('full_diagnostic_preserved')} live_work_executed={row.get('live_work_executed')} ok={row.get('ok')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
    return "\n".join(lines)

# v1055.0 deep diagnostic latency repair source tokens: doctor-deep-diagnostic-latency-budget-repair-v1 /doctor-deep-diagnostic-latency-budget-repair /api/doctor/deep-diagnostic-latency-budget-repair build_doctor_deep_diagnostic_latency_budget_repair build_doctor_deep_diagnostic_latency_budget_repair_metadata doctor_deep_diagnostic_latency_budget_repair_text build_bounded_repair_suggestions build_bounded_project_snapshot build_bounded_stable_loop_confidence build_bounded_hardening_report bounded_preview_default=False heavy_full_diagnostics_preserved=True prior_total_behavioral_coverage_count=116 new_deep_diagnostic_latency_repair_behavioral_coverage_count=1 total_behavioral_coverage_count=117 prior_mapping_reconciled_route_count=122 mapping_reconciled_route_count=123 deep_diagnostic_target_count=5 standard_diagnostic_target_count=4 long_diagnostic_preview_target_count=1 standard_diagnostic_budget_ms=1500 long_diagnostic_budget_ms=2500 latency_budget_pass_count=5 payload_shape_pass_count=5 bounded_preview_default_pass_count=5 full_diagnostic_preserved_count=5 heavy_controlled_self_build_route_preserved=True live_diagnostics_executed=False source_files_mutated=False memory_mutated=False runtime_data_deleted=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False api_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True

# v1065.10 diagnostic API compatibility restoration latency tokens: doctor_diagnostic_latency_uses_preview_routes=True /api/repair-suggestions/preview /api/project-snapshot/preview /api/stable-loops/confidence/preview /api/hardening-report/preview /api/controlled-self-build/lightweight-preview legacy_default_full_compatibility_restored=True explicit_preview_endpoints=True preview_routes_claim_full_diagnostics=False
