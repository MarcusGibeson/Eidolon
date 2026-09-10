from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_route_coverage_completion_dispatch_classification import coverage_route_rows as prior_coverage_route_rows

DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_VERSION = RUNTIME_VERSION
DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_ID = "dashboard-route-behavioral-coverage-continuation-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
PRIOR_COMPLETION_MODULE = "conscious_agent/dashboard_route_coverage_completion_dispatch_classification.py"
PRIOR_RECONCILIATION_ROUTE = "/dashboard-route-manifest-renderer-reconciliation"
PRIOR_COMPLETION_ROUTE = "/dashboard-route-coverage-completion-dispatch-classification"
SELF_ROUTE = "/dashboard-route-behavioral-coverage-continuation"
SELF_RENDERER = "render_dashboard_route_behavioral_coverage_continuation"
PRIOR_BEHAVIORAL_ROUTE_COUNT = 72
ADDITIONAL_BEHAVIORAL_ROUTE_COUNT = 24
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 96
MAPPING_RECONCILED_ROUTE_COUNT = 99

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_route_coverage_continued": True,
    "behavioral_route_probe_executes_renderers": True,
    "slow_stateful_routes_deferred": True,
    "broken_renderer_routes_deferred": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_behavior_pass_is_release_approval": False,
    "route_probe_executes_governed_actions": False,
    "route_probe_applies_patches": False,
    "route_probe_writes_memory": False,
    "route_probe_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class RouteRow:
    route: str
    renderer: str
    cohort: str
    source: str


# v1034 deliberately covers approval, authorization, and autonomy-safety pages that
# render quickly and do not execute governed actions. Slow/stateful or known-broken
# candidates remain explicitly deferred for later isolated harnesses.
ADDITIONAL_BEHAVIORAL_ROUTES: tuple[RouteRow, ...] = (
    RouteRow("/approval-checklist", "render_approval_checklist", "approval-boundary", "v1034-additional-behavior"),
    RouteRow("/approval-transaction-model", "render_approval_transaction_model", "approval-boundary", "v1034-additional-behavior"),
    RouteRow("/authorization-boundary-map", "render_authorization_boundary_map", "authorization-boundary", "v1034-additional-behavior"),
    RouteRow("/authorization-confusion-patterns", "render_authorization_confusion_patterns", "authorization-boundary", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-audit", "render_authorization_firewall_audit", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-audit-status-split", "render_authorization_firewall_audit_status_split", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-decision-packet", "render_authorization_firewall_decision_packet", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-safe-boundary-filter", "render_authorization_firewall_safe_boundary_filter", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-severity-classifier", "render_authorization_firewall_severity_classifier", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-signal-triage-audit", "render_authorization_firewall_signal_triage_audit", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-firewall-warning-status", "render_authorization_firewall_warning_status", "authorization-firewall", "v1034-additional-behavior"),
    RouteRow("/authorization-language-scan", "render_authorization_language_scan", "authorization-boundary", "v1034-additional-behavior"),
    RouteRow("/autonomy-blocker-gap-register", "render_autonomy_blocker_gap_register", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/autonomy-misinterpretation-firewall", "render_autonomy_misinterpretation_firewall", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/autonomy-phase-zero-definition-contract", "render_autonomy_phase_zero_definition_contract", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/autonomy-phase-zero-handoff-packet", "render_autonomy_phase_zero_handoff_packet", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/autonomy-phase-zero-readiness-board", "render_autonomy_phase_zero_readiness_board", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/autonomy-readiness-criteria-board", "render_autonomy_readiness_criteria_board", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/autonomy-readiness-review-board-audit", "render_autonomy_readiness_review_board_audit", "autonomy-safety", "v1034-additional-behavior"),
    RouteRow("/blocked-action-explanation-cards", "render_blocked_action_explanation_cards", "supervised-blockers", "v1034-additional-behavior"),
    RouteRow("/blocked-action-safety-event-timeline-cards", "render_blocked_action_safety_event_timeline_cards", "supervised-blockers", "v1034-additional-behavior"),
    RouteRow("/capability-gap-overreach-analysis", "render_capability_gap_overreach_analysis", "capability-safety", "v1034-additional-behavior"),
    RouteRow("/capability-maturity-governance-audit", "render_capability_maturity_governance_audit", "capability-safety", "v1034-additional-behavior"),
    RouteRow("/expression-live-application-eligibility-gate", "render_expression_live_application_eligibility_gate", "approval-boundary", "v1034-additional-behavior"),
)

DEFERRED_ROUTE_REASONS: dict[str, str] = {
    "/autonomy": "slow renderer in current direct-render probe; defer until isolated slow-route harness exists",
    "/execution-approval-scope": "renderer currently raises a missing self_maintenance helper in direct render; defer until repaired separately",
}

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


def _render_direct(route: str, renderer: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import dashboard  # type: ignore

        fn = getattr(dashboard, renderer)
        body = fn()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        checks = {
            "string_body": isinstance(body, str),
            "html_body": isinstance(body, str) and "<html" in body.lower(),
            "data_tip_present": isinstance(body, str) and "data-tip" in body,
            "route_token_present": isinstance(body, str) and route in body,
            "no_traceback_text": isinstance(body, str) and "Traceback (most recent call last)" not in body,
            "no_dashboard_error": isinstance(body, str) and "Dashboard error" not in body,
            "no_500_text": isinstance(body, str) and "HTTP 500" not in body and "status=500" not in body,
        }
        return {
            "route": route,
            "renderer": renderer,
            "ok": all(checks.values()),
            "status": "pass" if all(checks.values()) else "blocked",
            "elapsed_ms": elapsed_ms,
            "body_size": len(body) if isinstance(body, str) else 0,
            "checks": checks,
            "error": "",
        }
    except Exception as error:
        return {
            "route": route,
            "renderer": renderer,
            "ok": False,
            "status": "error",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "body_size": 0,
            "checks": {},
            "error": f"{type(error).__name__}: {error}",
        }


def _cohort_summary(route_rows: list[dict[str, Any]], behavior_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_route = {str(row.get("route")): row for row in behavior_rows}
    cohorts = sorted({str(row.get("cohort")) for row in route_rows})
    summary: list[dict[str, Any]] = []
    for cohort in cohorts:
        routes = [row for row in route_rows if row.get("cohort") == cohort]
        rendered = [by_route.get(str(row.get("route"))) for row in routes]
        passed = sum(1 for row in rendered if row and row.get("ok"))
        blocked = len(routes) - passed
        summary.append({"cohort": cohort, "routes": len(routes), "passed": passed, "blocked": blocked})
    return summary


def _classify_manual_dispatch(route_map: dict[str, str], covered_routes: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    known_slow_or_stateful = {
        "/stabilization",
        "/doctor",
        "/detail",
        "/route-manifest-dashboard-parity",
        "/dashboard-route-behavioral-coverage-expansion",
        "/dashboard-route-manifest-renderer-reconciliation",
        PRIOR_COMPLETION_ROUTE,
        SELF_ROUTE,
        *DEFERRED_ROUTE_REASONS.keys(),
    }
    for route, renderer in sorted(route_map.items()):
        if route in covered_routes:
            classification = "behaviorally_rendered"
        elif route in {PRIOR_RECONCILIATION_ROUTE, PRIOR_COMPLETION_ROUTE, SELF_ROUTE}:
            classification = "mapping_verified_recursion_guard"
        elif route in known_slow_or_stateful:
            classification = "deferred_slow_stateful_or_self_referential"
        elif route in DEFERRED_ROUTE_REASONS:
            classification = "deferred_known_renderer_issue"
        elif renderer.startswith("render_"):
            classification = "remaining_manual_dispatch_candidate"
        else:
            classification = "unclassified"
        rows.append({"route": route, "renderer": renderer, "classification": classification})
    return rows


def continuation_route_rows() -> list[dict[str, Any]]:
    inherited = [dict(row) for row in prior_coverage_route_rows()]
    additional = [asdict(row) for row in ADDITIONAL_BEHAVIORAL_ROUTES]
    return inherited + additional


def build_dashboard_route_behavioral_coverage_continuation_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    try:
        cache_key = (
            str(project_root),
            (project_root / DASHBOARD_MODULE).stat().st_mtime,
            (project_root / MANUAL_SMOKE_MODULE).stat().st_mtime,
            (project_root / SOURCE_MANIFEST_MODULE).stat().st_mtime,
        )
    except OSError:
        cache_key = (str(project_root), 0.0, 0.0, 0.0)
    cached = _CACHE.get(cache_key)
    if cached:
        return dict(cached)

    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history])
    route_map = _route_renderer_map(dashboard_source)
    renderers = _renderer_function_names(dashboard_source)
    inherited_rows = [dict(row) for row in prior_coverage_route_rows()]
    additional_rows = [asdict(row) for row in ADDITIONAL_BEHAVIORAL_ROUTES]
    behavior_route_rows = inherited_rows + additional_rows
    route_names = [str(row["route"]) for row in behavior_route_rows]
    duplicate_routes = sorted({route for route in route_names if route_names.count(route) > 1})
    mapping_mismatches = [
        {"route": row["route"], "expected_renderer": row["renderer"], "actual_renderer": route_map.get(str(row["route"]))}
        for row in additional_rows
        if route_map.get(str(row["route"])) != row["renderer"]
    ]
    renderer_missing = [row for row in additional_rows if row["renderer"] not in renderers]
    behavior_rows = [_render_direct(str(row["route"]), str(row["renderer"])) for row in additional_rows]
    additional_render_pass_count = sum(1 for row in behavior_rows if row.get("ok"))
    blocked_behavior_rows = [row for row in behavior_rows if not row.get("ok")]
    covered_routes = set(route_names)
    recursion_guard_routes = {PRIOR_RECONCILIATION_ROUTE, PRIOR_COMPLETION_ROUTE, SELF_ROUTE}
    classification_rows = _classify_manual_dispatch(route_map, covered_routes | recursion_guard_routes)
    classification_counts: dict[str, int] = {}
    for row in classification_rows:
        key = str(row.get("classification"))
        classification_counts[key] = classification_counts.get(key, 0) + 1
    deferred_count = classification_counts.get("deferred_slow_stateful_or_self_referential", 0)
    candidate_count = classification_counts.get("remaining_manual_dispatch_candidate", 0)
    cohort_rows = _cohort_summary(additional_rows, behavior_rows)
    mapping_reconciled_routes = covered_routes | recursion_guard_routes
    manifest_surface_present = "v1034-dashboard-route-behavioral-coverage-continuation" in manifest_source
    deferred_reasons_present = all(route in docs and reason in docs for route, reason in DEFERRED_ROUTE_REASONS.items())
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_ID,
        "prior_behavioral_route_count=72",
        "additional_behavioral_route_count=24",
        "total_behavioral_coverage_count=96",
        "mapping_reconciled_route_count=99",
        "additional_render_pass_count=24",
        "manual_dispatch_routes_classified=True",
        "slow_stateful_routes_deferred=True",
        "broken_renderer_routes_deferred=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "prior-behavioral-count", "ok": len(inherited_rows) == PRIOR_BEHAVIORAL_ROUTE_COUNT, "message": f"prior={len(inherited_rows)} expected={PRIOR_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "additional-route-count", "ok": len(additional_rows) == ADDITIONAL_BEHAVIORAL_ROUTE_COUNT, "message": f"additional={len(additional_rows)} expected={ADDITIONAL_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "total-behavioral-coverage-count", "ok": len(behavior_route_rows) == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={len(behavior_route_rows)} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "route-list-unique", "ok": not duplicate_routes, "message": f"duplicate routes={duplicate_routes}"},
        {"name": "additional-route-renderer-mapping-clean", "ok": not mapping_mismatches, "message": f"mapping mismatches={len(mapping_mismatches)}"},
        {"name": "additional-route-renderers-present", "ok": not renderer_missing, "message": f"missing renderers={len(renderer_missing)}"},
        {"name": "additional-routes-render-behaviorally", "ok": additional_render_pass_count == ADDITIONAL_BEHAVIORAL_ROUTE_COUNT and not blocked_behavior_rows, "message": f"render passes={additional_render_pass_count}/{ADDITIONAL_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "mapping-reconciled-count", "ok": len(mapping_reconciled_routes) == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping reconciled={len(mapping_reconciled_routes)} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "manual-dispatch-routes-classified", "ok": bool(classification_rows) and len(classification_rows) >= MAPPING_RECONCILED_ROUTE_COUNT and candidate_count > 0 and deferred_count > 0, "message": f"classified={len(classification_rows)} candidates={candidate_count} deferred={deferred_count}"},
        {"name": "deferred-route-reasons-documented", "ok": deferred_reasons_present, "message": f"deferred_routes={sorted(DEFERRED_ROUTE_REASONS)}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1034 dashboard route behavioral continuation surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1034 route continuation truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "route_probe_executes_governed_actions", "route_probe_applies_patches", "route_probe_writes_memory", "route_probe_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Route behavioral continuation remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_ID,
        "state": "dashboard_route_behavioral_coverage_continuation_review_only",
        "prior_behavioral_route_count": len(inherited_rows),
        "additional_behavioral_route_count": len(additional_rows),
        "total_behavioral_coverage_count": len(behavior_route_rows),
        "mapping_reconciled_route_count": len(mapping_reconciled_routes),
        "behavior_rendered_this_release_count": len(behavior_rows),
        "additional_render_pass_count": additional_render_pass_count,
        "additional_render_blocked_count": len(blocked_behavior_rows),
        "manual_dispatch_route_count": len(classification_rows),
        "manual_dispatch_routes_classified": True,
        "classification_counts": classification_counts,
        "deferred_manual_dispatch_count": deferred_count,
        "remaining_manual_dispatch_candidate_count": candidate_count,
        "route_rows": behavior_route_rows,
        "additional_route_rows": additional_rows,
        "behavior_rows": behavior_rows,
        "blocked_behavior_rows": blocked_behavior_rows,
        "cohort_rows": cohort_rows,
        "classification_rows": classification_rows,
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "duplicate_routes": duplicate_routes,
        "deferred_route_reasons": dict(DEFERRED_ROUTE_REASONS),
        "slow_stateful_routes_deferred": True,
        "broken_renderer_routes_deferred": True,
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
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }
    _CACHE.clear()
    _CACHE[cache_key] = dict(report)
    return report


def dashboard_route_behavioral_coverage_continuation_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"prior_behavioral_route_count={report.get('prior_behavioral_route_count')}",
        f"additional_behavioral_route_count={report.get('additional_behavioral_route_count')}",
        f"total_behavioral_coverage_count={report.get('total_behavioral_coverage_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"behavior_rendered_this_release_count={report.get('behavior_rendered_this_release_count')}",
        f"additional_render_pass_count={report.get('additional_render_pass_count')}",
        f"additional_render_blocked_count={report.get('additional_render_blocked_count')}",
        f"manual_dispatch_route_count={report.get('manual_dispatch_route_count')}",
        f"manual_dispatch_routes_classified={report.get('manual_dispatch_routes_classified')}",
        f"deferred_manual_dispatch_count={report.get('deferred_manual_dispatch_count')}",
        f"remaining_manual_dispatch_candidate_count={report.get('remaining_manual_dispatch_candidate_count')}",
        f"slow_stateful_routes_deferred={report.get('slow_stateful_routes_deferred')}",
        f"broken_renderer_routes_deferred={report.get('broken_renderer_routes_deferred')}",
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
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: ok={row.get('ok')} :: {row.get('message')}")
        lines.append("\nCohorts:")
        for row in report.get("cohort_rows", []):
            lines.append(f"- {row.get('cohort')}: passed={row.get('passed')}/{row.get('routes')} blocked={row.get('blocked')}")
        lines.append("\nDeferred routes:")
        for route, reason in sorted((report.get("deferred_route_reasons") or {}).items()):
            lines.append(f"- {route}: {reason}")
        lines.append("\nClassification counts:")
        for key, value in sorted((report.get("classification_counts") or {}).items()):
            lines.append(f"- {key}: {value}")
        if report.get("blocked_behavior_rows"):
            lines.append("\nBlocked behavior rows:")
            for row in report.get("blocked_behavior_rows", []):
                lines.append(f"- {row.get('route')} -> {row.get('renderer')}: {row.get('error')}")
    return "\n".join(lines)
