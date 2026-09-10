from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_route_behavioral_coverage_expansion import expanded_route_rows

DASHBOARD_ROUTE_COVERAGE_COMPLETION_DISPATCH_CLASSIFICATION_VERSION = CURRENT_VERSION
DASHBOARD_ROUTE_COVERAGE_COMPLETION_DISPATCH_CLASSIFICATION_ID = "dashboard-route-coverage-completion-and-dispatch-classification-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
BASELINE_MODULE = "conscious_agent/dashboard_route_behavioral_coverage_expansion.py"
PRIOR_RECONCILIATION_ROUTE = "/dashboard-route-manifest-renderer-reconciliation"
PRIOR_RECONCILIATION_RENDERER = "render_dashboard_route_manifest_renderer_reconciliation"
SELF_ROUTE = "/dashboard-route-coverage-completion-dispatch-classification"
SELF_RENDERER = "render_dashboard_route_coverage_completion_dispatch_classification"
INHERITED_BASELINE_ROUTE_COUNT = 48
ADDITIONAL_BEHAVIORAL_ROUTE_COUNT = 24
TOTAL_BEHAVIORAL_COVERAGE_COUNT = 72
MAPPING_RECONCILED_ROUTE_COUNT = 74

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_route_coverage_completion": True,
    "dispatch_classification_prepared": True,
    "behavioral_route_probe_executes_renderers": True,
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


ADDITIONAL_BEHAVIORAL_ROUTES: tuple[RouteRow, ...] = (
    RouteRow("/chat-console", "render_chat_console", "operator-interaction", "v1032-additional-behavior"),
    RouteRow("/chat-actions", "render_chat_actions", "operator-interaction", "v1032-additional-behavior"),
    RouteRow("/create", "render_create", "operator-interaction", "v1032-additional-behavior"),
    RouteRow("/work-cycle", "render_work_cycle", "operator-interaction", "v1032-additional-behavior"),
    RouteRow("/patch-trials", "render_patch_trials", "patch-review", "v1032-additional-behavior"),
    RouteRow("/patch-evidence", "render_patch_evidence", "patch-review", "v1032-additional-behavior"),
    RouteRow("/patch-apply", "render_patch_apply", "patch-review", "v1032-additional-behavior"),
    RouteRow("/patch-recovery", "render_patch_recovery", "patch-review", "v1032-additional-behavior"),
    RouteRow("/patch-queue", "render_patch_queue", "patch-review", "v1032-additional-behavior"),
    RouteRow("/improvement-loop", "render_improvement_loop", "improvement-loop", "v1032-additional-behavior"),
    RouteRow("/local-model-proposals", "render_local_model_proposals", "improvement-loop", "v1032-additional-behavior"),
    RouteRow("/proposal-critique", "render_proposal_critique", "improvement-loop", "v1032-additional-behavior"),
    RouteRow("/candidate-ranking", "render_candidate_ranking", "improvement-loop", "v1032-additional-behavior"),
    RouteRow("/candidate-refinement", "render_candidate_refinement", "improvement-loop", "v1032-additional-behavior"),
    RouteRow("/suggestion-loop", "render_suggestion_loop", "suggestion-workflow", "v1032-additional-behavior"),
    RouteRow("/suggestion-inbox", "render_suggestion_inbox", "suggestion-workflow", "v1032-additional-behavior"),
    RouteRow("/work-order-handoff", "render_work_order_handoff", "work-order", "v1032-additional-behavior"),
    RouteRow("/work-order-evidence", "render_work_order_evidence", "work-order", "v1032-additional-behavior"),
    RouteRow("/self-development-cycle", "render_self_development_cycle_dashboard", "self-development", "v1032-additional-behavior"),
    RouteRow("/self-development-readiness", "render_self_development_readiness", "self-development", "v1032-additional-behavior"),
    RouteRow("/v100-stabilization", "render_v100_stabilization", "legacy-stabilization", "v1032-additional-behavior"),
    RouteRow("/source-change-cartographer", "render_source_change_cartographer", "source-change", "v1032-additional-behavior"),
    RouteRow("/patch-simulation", "render_patch_simulation", "source-change", "v1032-additional-behavior"),
    RouteRow("/verification-matrix", "render_verification_matrix", "source-change", "v1032-additional-behavior"),
)

_CACHE: dict[tuple[str, float, float, float], dict[str, Any]] = {}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except FileNotFoundError:
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
        SELF_ROUTE,
    }
    for route, renderer in sorted(route_map.items()):
        if route in covered_routes:
            classification = "behaviorally_rendered"
        elif route in {PRIOR_RECONCILIATION_ROUTE, SELF_ROUTE}:
            classification = "mapping_verified_recursion_guard"
        elif route in known_slow_or_stateful:
            classification = "deferred_slow_stateful_or_self_referential"
        elif renderer.startswith("render_"):
            classification = "remaining_manual_dispatch_candidate"
        else:
            classification = "unclassified"
        rows.append({"route": route, "renderer": renderer, "classification": classification})
    return rows


def coverage_route_rows() -> list[dict[str, Any]]:
    inherited = [dict(row) for row in expanded_route_rows()]
    additional = [asdict(row) for row in ADDITIONAL_BEHAVIORAL_ROUTES]
    return inherited + additional


def build_dashboard_route_coverage_completion_dispatch_classification_review(root: str | Path | None = None) -> dict[str, Any]:
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
    if cache_key in _CACHE:
        return dict(_CACHE[cache_key])

    dashboard_source = _read_text(project_root, DASHBOARD_MODULE)
    smoke_source = _read_text(project_root, MANUAL_SMOKE_MODULE)
    manifest_source = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([dashboard_source, smoke_source, manifest_source, readme_next, readme_history])

    route_map = _route_renderer_map(dashboard_source)
    renderer_names = _renderer_function_names(dashboard_source)
    baseline_rows = [dict(row) for row in expanded_route_rows()]
    additional_rows = [asdict(row) for row in ADDITIONAL_BEHAVIORAL_ROUTES]
    inherited_routes = {str(row.get("route")) for row in baseline_rows}
    additional_routes = {str(row.get("route")) for row in additional_rows}
    behavior_route_rows = baseline_rows + additional_rows
    covered_routes = inherited_routes | additional_routes
    duplicate_routes = sorted({route for route in covered_routes if [row.get("route") for row in behavior_route_rows].count(route) > 1})

    mapping_mismatches: list[dict[str, Any]] = []
    renderer_missing: list[dict[str, Any]] = []
    for row in additional_rows:
        route = str(row["route"])
        expected_renderer = str(row["renderer"])
        actual_renderer = route_map.get(route)
        if actual_renderer != expected_renderer:
            mapping_mismatches.append({"route": route, "expected_renderer": expected_renderer, "actual_renderer": actual_renderer})
        if expected_renderer not in renderer_names:
            renderer_missing.append({"route": route, "renderer": expected_renderer})

    behavior_rows: list[dict[str, Any]] = []
    for row in additional_rows:
        route = str(row["route"])
        renderer = str(row["renderer"])
        if any(mismatch.get("route") == route for mismatch in mapping_mismatches):
            behavior_rows.append({"route": route, "renderer": renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "route-to-renderer mapping mismatch"})
            continue
        if any(missing.get("route") == route for missing in renderer_missing):
            behavior_rows.append({"route": route, "renderer": renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "renderer function missing"})
            continue
        behavior_rows.append(_render_direct(route, renderer))

    additional_render_pass_count = sum(1 for row in behavior_rows if row.get("ok"))
    blocked_behavior_rows = [row for row in behavior_rows if not row.get("ok")]
    classification_rows = _classify_manual_dispatch(route_map, covered_routes | {PRIOR_RECONCILIATION_ROUTE, SELF_ROUTE})
    classification_counts: dict[str, int] = {}
    for row in classification_rows:
        key = str(row.get("classification"))
        classification_counts[key] = classification_counts.get(key, 0) + 1
    deferred_count = classification_counts.get("deferred_slow_stateful_or_self_referential", 0)
    candidate_count = classification_counts.get("remaining_manual_dispatch_candidate", 0)
    cohort_rows = _cohort_summary(additional_rows, behavior_rows)
    mapping_reconciled_routes = covered_routes | {PRIOR_RECONCILIATION_ROUTE, SELF_ROUTE}
    manifest_surface_present = "v1032-dashboard-route-coverage-completion-dispatch-classification" in manifest_source
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_ROUTE_COVERAGE_COMPLETION_DISPATCH_CLASSIFICATION_ID,
        "inherited_baseline_route_count=48",
        "additional_behavioral_route_count=24",
        "total_behavioral_coverage_count=72",
        "mapping_reconciled_route_count=74",
        "additional_render_pass_count=24",
        "manual_dispatch_routes_classified=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_ROUTE_COVERAGE_COMPLETION_DISPATCH_CLASSIFICATION_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_ROUTE_COVERAGE_COMPLETION_DISPATCH_CLASSIFICATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "inherited-baseline-count", "ok": len(baseline_rows) == INHERITED_BASELINE_ROUTE_COUNT, "message": f"baseline={len(baseline_rows)} expected={INHERITED_BASELINE_ROUTE_COUNT}"},
        {"name": "additional-route-count", "ok": len(additional_rows) == ADDITIONAL_BEHAVIORAL_ROUTE_COUNT, "message": f"additional={len(additional_rows)} expected={ADDITIONAL_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "total-behavioral-coverage-count", "ok": len(behavior_route_rows) == TOTAL_BEHAVIORAL_COVERAGE_COUNT, "message": f"total={len(behavior_route_rows)} expected={TOTAL_BEHAVIORAL_COVERAGE_COUNT}"},
        {"name": "route-list-unique", "ok": not duplicate_routes, "message": f"duplicate routes={duplicate_routes}"},
        {"name": "additional-route-renderer-mapping-clean", "ok": not mapping_mismatches, "message": f"mapping mismatches={len(mapping_mismatches)}"},
        {"name": "additional-route-renderers-present", "ok": not renderer_missing, "message": f"missing renderers={len(renderer_missing)}"},
        {"name": "additional-routes-render-behaviorally", "ok": additional_render_pass_count == ADDITIONAL_BEHAVIORAL_ROUTE_COUNT and not blocked_behavior_rows, "message": f"render passes={additional_render_pass_count}/{ADDITIONAL_BEHAVIORAL_ROUTE_COUNT}"},
        {"name": "mapping-reconciled-count", "ok": len(mapping_reconciled_routes) == MAPPING_RECONCILED_ROUTE_COUNT, "message": f"mapping reconciled={len(mapping_reconciled_routes)} expected={MAPPING_RECONCILED_ROUTE_COUNT}"},
        {"name": "manual-dispatch-routes-classified", "ok": bool(classification_rows) and len(classification_rows) >= MAPPING_RECONCILED_ROUTE_COUNT and candidate_count > 0 and deferred_count > 0, "message": f"classified={len(classification_rows)} candidates={candidate_count} deferred={deferred_count}"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1032 dashboard route coverage completion surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1032 route coverage truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "route_probe_executes_governed_actions", "route_probe_applies_patches", "route_probe_writes_memory", "route_probe_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Coverage completion remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_ROUTE_COVERAGE_COMPLETION_DISPATCH_CLASSIFICATION_ID,
        "state": "dashboard_route_coverage_completion_dispatch_classification_review_only",
        "inherited_baseline_route_count": len(baseline_rows),
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


def dashboard_route_coverage_completion_dispatch_classification_review_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"{report.get('current_milestone')}",
        f"review_id={report.get('review_id')}",
        f"status={report.get('status')}",
        f"inherited_baseline_route_count={report.get('inherited_baseline_route_count')}",
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
        lines.append("\nClassification counts:")
        for key, value in sorted((report.get("classification_counts") or {}).items()):
            lines.append(f"- {key}: {value}")
        if report.get("blocked_behavior_rows"):
            lines.append("\nBlocked behavior rows:")
            for row in report.get("blocked_behavior_rows", []):
                lines.append(f"- {row.get('route')} -> {row.get('renderer')}: {row.get('error')}")
    return "\n".join(lines)
