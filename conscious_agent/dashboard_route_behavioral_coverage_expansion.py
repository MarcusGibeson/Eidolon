from __future__ import annotations

import ast
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from route_manifest_inventory_dashboard_parity import ROUTE_MANIFEST_INVENTORY

DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_VERSION = CURRENT_VERSION
DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_ID = "dashboard-route-behavioral-coverage-expansion-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
EXPANDED_ROUTE_TARGET_COUNT = 48
BASELINE_ROUTE_COUNT = 23
ADDED_ROUTE_COUNT = 25
_CACHE: dict[tuple[str, float, float, float], dict[str, Any]] = {}

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "behavioral_route_coverage_expanded": True,
    "route_cohorts_declared": True,
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
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class ExpandedRouteRow:
    route: str
    renderer: str
    cohort: str
    source: str = "manual_dashboard_authoritative"


ADDITIONAL_BEHAVIORAL_ROUTES: tuple[ExpandedRouteRow, ...] = (
    ExpandedRouteRow("/approval-console", "render_approval_console", "operator-governance"),
    ExpandedRouteRow("/experiment-planner", "render_experiment_planner", "operator-governance"),
    ExpandedRouteRow("/outcome-reflections", "render_outcome_reflections", "operator-governance"),
    ExpandedRouteRow("/improvement-cycles", "render_improvement_cycles", "operator-governance"),
    ExpandedRouteRow("/cycle-replay", "render_cycle_replay", "operator-governance"),
    ExpandedRouteRow("/capability-ledger", "render_capability_ledger", "operator-governance"),
    ExpandedRouteRow("/shadow-autonomy", "render_shadow_autonomy", "operator-governance"),
    ExpandedRouteRow("/failure-war-games", "render_failure_war_games", "operator-governance"),
    ExpandedRouteRow("/mind-milestone-audit", "render_mind_milestone_audit", "operator-governance"),
    ExpandedRouteRow("/operator-home", "render_operator_home", "operator-console-core"),
    ExpandedRouteRow("/system-map", "render_system_map", "operator-console-core"),
    ExpandedRouteRow("/coherence-binder", "render_coherence_binder", "operator-console-core"),
    ExpandedRouteRow("/daily-loop", "render_daily_loop", "operator-console-core"),
    ExpandedRouteRow("/local-mind-runtime", "render_local_mind_runtime", "operator-console-core"),
    ExpandedRouteRow("/memory-quality", "render_memory_quality", "operator-console-core"),
    ExpandedRouteRow("/goal-continuity", "render_goal_continuity", "operator-console-core"),
    ExpandedRouteRow("/reasoning-workbench", "render_reasoning_workbench", "operator-console-core"),
    ExpandedRouteRow("/workflow-console", "render_workflow_console", "operator-console-core"),
    ExpandedRouteRow("/practical-mind-audit", "render_practical_mind_audit", "supervised-development"),
    ExpandedRouteRow("/improvement-intent", "render_improvement_intent", "supervised-development"),
    ExpandedRouteRow("/work-package-builder", "render_work_package_builder", "supervised-development"),
    ExpandedRouteRow("/patch-readiness", "render_patch_readiness", "supervised-development"),
    ExpandedRouteRow("/release-candidate-judgment", "render_release_candidate_judgment", "supervised-development"),
    ExpandedRouteRow("/supervised-development-readiness", "render_supervised_development_readiness", "supervised-development"),
    ExpandedRouteRow("/development-session-planner", "render_development_session_planner", "supervised-development"),
)


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _route_renderer_map(dashboard_source: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    pattern = re.compile(r'(?:if|elif) path == "([^"]+)"\s*:\n\s*html = (render_[A-Za-z0-9_]+)\(\)')
    for match in pattern.finditer(dashboard_source):
        mapping[match.group(1)] = match.group(2)
    return mapping


def _renderer_function_names(dashboard_source: str) -> set[str]:
    try:
        tree = ast.parse(dashboard_source)
    except SyntaxError:
        return set()
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("render_")}


def expanded_route_rows() -> list[dict[str, Any]]:
    base_rows = [
        ExpandedRouteRow(str(row.route), str(row.renderer), str(row.cohort), "v1029_parity_baseline")
        for row in ROUTE_MANIFEST_INVENTORY
    ]
    return [asdict(row) for row in [*base_rows, *ADDITIONAL_BEHAVIORAL_ROUTES]]


def _render_direct(route: str, renderer_name: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import dashboard  # type: ignore
    except Exception as error:
        return {"route": route, "renderer": renderer_name, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": f"dashboard import failed: {error}"}
    renderer = getattr(dashboard, renderer_name, None)
    if renderer is None:
        return {"route": route, "renderer": renderer_name, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "renderer missing"}
    try:
        body = renderer()
    except Exception as error:
        return {"route": route, "renderer": renderer_name, "ok": False, "status": "blocked", "elapsed_ms": int((time.perf_counter() - started) * 1000), "body_size": 0, "error": repr(error)}
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    body_text = body if isinstance(body, str) else ""
    token = route.strip("/")
    ok = (
        isinstance(body, str)
        and "<html" in body_text.lower()
        and "data-tip" in body_text
        and "Traceback" not in body_text
        and "Dashboard route crashed" not in body_text
        and "Internal Server Error" not in body_text
        and (not token or token in body_text)
    )
    return {
        "route": route,
        "renderer": renderer_name,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "elapsed_ms": elapsed_ms,
        "body_size": len(body_text),
        "contains_data_tip": "data-tip" in body_text,
        "contains_traceback": "Traceback" in body_text,
        "contains_500_text": "Internal Server Error" in body_text or "Dashboard route crashed" in body_text,
        "contains_route_token": bool((not token) or token in body_text),
        "error": None if ok else "rendered body failed expanded behavioral route contract",
    }


def _cohort_summary(rows: list[dict[str, Any]], behavior_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_route = {row.get("route"): row for row in behavior_rows}
    cohorts: dict[str, dict[str, Any]] = {}
    for row in rows:
        cohort = str(row.get("cohort"))
        summary = cohorts.setdefault(cohort, {"cohort": cohort, "total": 0, "passed": 0, "blocked": 0})
        summary["total"] += 1
        if by_route.get(row.get("route"), {}).get("ok") is True:
            summary["passed"] += 1
        else:
            summary["blocked"] += 1
    return list(cohorts.values())


def build_dashboard_route_behavioral_coverage_expansion_review(root: str | Path | None = None) -> dict[str, Any]:
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
    route_rows = expanded_route_rows()
    routes = [str(row["route"]) for row in route_rows]
    duplicate_routes = sorted({route for route in routes if routes.count(route) > 1})

    mapping_mismatches: list[dict[str, Any]] = []
    renderer_missing: list[dict[str, Any]] = []
    behavior_rows: list[dict[str, Any]] = []
    for row in route_rows:
        route = str(row["route"])
        expected_renderer = str(row["renderer"])
        actual_renderer = route_map.get(route)
        if actual_renderer != expected_renderer:
            mapping_mismatches.append({"route": route, "expected_renderer": expected_renderer, "actual_renderer": actual_renderer})
            behavior_rows.append({"route": route, "renderer": expected_renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "route-to-renderer mapping mismatch"})
            continue
        if expected_renderer not in renderer_names:
            renderer_missing.append({"route": route, "renderer": expected_renderer})
            behavior_rows.append({"route": route, "renderer": expected_renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "renderer function missing"})
            continue
        behavior_rows.append(_render_direct(route, expected_renderer))

    render_pass_count = sum(1 for row in behavior_rows if row.get("ok"))
    blocked_behavior_rows = [row for row in behavior_rows if not row.get("ok")]
    total_elapsed_ms = sum(int(row.get("elapsed_ms") or 0) for row in behavior_rows)
    cohort_rows = _cohort_summary(route_rows, behavior_rows)
    added_route_count = len(ADDITIONAL_BEHAVIORAL_ROUTES)
    manifest_surface_present = "v1030-dashboard-route-behavioral-coverage-expansion" in manifest_source
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_ID,
        "expanded_behavioral_route_count=48",
        "baseline_route_count=23",
        "added_route_count=25",
        "route_cohort_count=15",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "route-count-expanded", "ok": len(route_rows) == EXPANDED_ROUTE_TARGET_COUNT and len(route_rows) > len(ROUTE_MANIFEST_INVENTORY), "message": f"expanded={len(route_rows)} baseline={len(ROUTE_MANIFEST_INVENTORY)} added={added_route_count}"},
        {"name": "route-list-unique", "ok": not duplicate_routes, "message": f"duplicate routes={duplicate_routes}"},
        {"name": "route-renderer-mapping-clean", "ok": not mapping_mismatches, "message": f"mapping mismatches={len(mapping_mismatches)}"},
        {"name": "route-renderers-present", "ok": not renderer_missing, "message": f"missing renderers={len(renderer_missing)}"},
        {"name": "expanded-routes-render-behaviorally", "ok": render_pass_count == EXPANDED_ROUTE_TARGET_COUNT and not blocked_behavior_rows, "message": f"render passes={render_pass_count}/{EXPANDED_ROUTE_TARGET_COUNT}"},
        {"name": "cohort-summary-complete", "ok": len(cohort_rows) == 15 and all(row.get("blocked") == 0 for row in cohort_rows), "message": f"cohorts={len(cohort_rows)} blocked={[row for row in cohort_rows if row.get('blocked')] }"},
        {"name": "manifest-surface-current", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1030 route behavior coverage expansion surface."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "README/dashboard/smoke/manifest docs carry the v1030 route behavioral coverage expansion truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_behavior_pass_is_release_approval", "route_probe_executes_governed_actions", "route_probe_applies_patches", "route_probe_writes_memory", "route_probe_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Expanded route behavior coverage remains review-only and does not grant authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_ID,
        "state": "dashboard_route_behavioral_coverage_expansion_review_only",
        "expanded_behavioral_route_count": len(route_rows),
        "baseline_route_count": len(ROUTE_MANIFEST_INVENTORY),
        "added_route_count": added_route_count,
        "route_cohort_count": len(cohort_rows),
        "route_rows": route_rows,
        "behavior_rows": behavior_rows,
        "cohort_rows": cohort_rows,
        "render_pass_count": render_pass_count,
        "render_blocked_count": len(blocked_behavior_rows),
        "blocked_behavior_rows": blocked_behavior_rows,
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "duplicate_routes": duplicate_routes,
        "total_behavior_elapsed_ms": total_elapsed_ms,
        "behavioral_route_coverage_expanded": True,
        "route_cohorts_declared": True,
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


def dashboard_route_behavioral_coverage_expansion_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_EXPANSION_ID)),
        f"expanded_behavioral_route_count={report.get('expanded_behavioral_route_count')}",
        f"baseline_route_count={report.get('baseline_route_count')}",
        f"added_route_count={report.get('added_route_count')}",
        f"route_cohort_count={report.get('route_cohort_count')}",
        f"render_pass_count={report.get('render_pass_count')}",
        f"render_blocked_count={report.get('render_blocked_count')}",
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
        f"ok={report.get('ok')}",
    ]
    if full:
        for row in report.get("cohort_rows", []):
            lines.append(f"cohort={row.get('cohort')} passed={row.get('passed')}/{row.get('total')} blocked={row.get('blocked')}")
        for row in report.get("blocked_behavior_rows", []):
            lines.append(f"blocked_route={row.get('route')} renderer={row.get('renderer')} error={row.get('error')}")
    return "\n".join(lines)


# v1030.0 Dashboard Route Behavioral Coverage Expansion v1 tokens: dashboard-route-behavioral-coverage-expansion-v1 /dashboard-route-behavioral-coverage-expansion build_dashboard_route_behavioral_coverage_expansion_review dashboard_route_behavioral_coverage_expansion_review_text expanded_behavioral_route_count=48 baseline_route_count=23 added_route_count=25 route_cohort_count=15 render_pass_count=48 render_blocked_count=0 manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip.
