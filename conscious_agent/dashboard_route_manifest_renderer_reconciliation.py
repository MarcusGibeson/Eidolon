from __future__ import annotations

import ast
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_route_behavioral_coverage_expansion import expanded_route_rows

DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_VERSION = CURRENT_VERSION
DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_ID = "dashboard-route-manifest-to-renderer-reconciliation-v1"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
BASELINE_MODULE = "conscious_agent/dashboard_route_behavioral_coverage_expansion.py"
SELF_ROUTE = "/dashboard-route-manifest-renderer-reconciliation"
SELF_RENDERER = "render_dashboard_route_manifest_renderer_reconciliation"
BASELINE_ROUTE_COUNT = 48
MAPPING_RECONCILED_ROUTE_COUNT = 49
_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "dashboard_route_manifest_renderer_reconciliation": True,
    "route_manifest_to_renderer_reconciled": True,
    "manual_dispatch_routes_classified": True,
    "self_route_mapping_verified": True,
    "route_manifest_replaces_dashboard_routes": False,
    "route_manifest_generates_routes": False,
    "dashboard_wiring_generated": False,
    "generated_wiring_activated": False,
    "route_presence_is_authorization": False,
    "route_reconciliation_is_release_approval": False,
    "reconciliation_executes_governed_actions": False,
    "reconciliation_applies_patches": False,
    "reconciliation_writes_memory": False,
    "reconciliation_creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class ReconciledRouteRow:
    route: str
    renderer: str
    cohort: str
    source: str
    render_mode: str
    status: str = "manual_authoritative"


@dataclass(frozen=True)
class DispatchClassificationRow:
    route: str
    renderer: str
    classification: str
    reason: str


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


def _baseline_rows() -> list[dict[str, Any]]:
    rows = [dict(row) for row in expanded_route_rows()]
    # v1030 is the authoritative bounded behavioral baseline. Keep this check
    # explicit so v1031 cannot silently drift into a different route count.
    return rows


def reconciled_route_rows() -> list[dict[str, Any]]:
    rows = [
        asdict(ReconciledRouteRow(
            route=str(row.get("route")),
            renderer=str(row.get("renderer")),
            cohort=str(row.get("cohort")),
            source="v1030_behavioral_baseline",
            render_mode="behavioral_render",
        ))
        for row in _baseline_rows()
    ]
    rows.append(asdict(ReconciledRouteRow(
        route=SELF_ROUTE,
        renderer=SELF_RENDERER,
        cohort="v1031-reconciliation",
        source="v1031_self_route",
        render_mode="mapping_only_self_route",
    )))
    return rows


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
        "error": None if ok else "rendered body failed route manifest-to-renderer reconciliation contract",
    }


def _classify_uncovered_route(route: str, renderer: str) -> DispatchClassificationRow:
    text = f"{route} {renderer}".lower()
    if any(token in text for token in ["chat", "actions", "approvals", "notifications", "memory", "tasks"]):
        return DispatchClassificationRow(route, renderer, "dynamic_stateful", "Route may depend on runtime state or local operator data.")
    if any(token in text for token in ["self-development", "release", "archive", "smoke", "manifest", "probe", "integrity", "coverage", "parity", "decomposition"]):
        return DispatchClassificationRow(route, renderer, "safe_review_candidate", "Review/report route likely suitable for future bounded behavioral rendering.")
    if any(token in text for token in ["search", "history", "timeline", "sessions", "workspaces"]):
        return DispatchClassificationRow(route, renderer, "slow_or_large", "Route may scan larger local state and should be rendered in a separate cohort.")
    return DispatchClassificationRow(route, renderer, "route_probe_only_initially", "Route requires manual review before behavioral rendering is added.")


def _classification_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("classification"))
        counts[key] = counts.get(key, 0) + 1
    return [{"classification": key, "count": counts[key]} for key in sorted(counts)]


def build_dashboard_route_manifest_renderer_reconciliation_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    try:
        cache_key = (
            str(project_root),
            (project_root / DASHBOARD_MODULE).stat().st_mtime,
            (project_root / MANUAL_SMOKE_MODULE).stat().st_mtime,
            (project_root / SOURCE_MANIFEST_MODULE).stat().st_mtime,
            (project_root / "README_NEXT_STEPS.md").stat().st_mtime,
            (project_root / "README_RELEASE_HISTORY.md").stat().st_mtime,
        )
    except OSError:
        cache_key = (str(project_root), 0.0, 0.0, 0.0, 0.0, 0.0)
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
    baseline_rows = _baseline_rows()
    route_rows = reconciled_route_rows()
    routes = [str(row["route"]) for row in route_rows]
    duplicate_routes = sorted({route for route in routes if routes.count(route) > 1})

    mapping_mismatches: list[dict[str, Any]] = []
    renderer_missing: list[dict[str, Any]] = []
    behavior_rows: list[dict[str, Any]] = []
    mapping_only_rows: list[dict[str, Any]] = []
    for row in route_rows:
        route = str(row["route"])
        expected_renderer = str(row["renderer"])
        actual_renderer = route_map.get(route)
        if actual_renderer != expected_renderer:
            mapping_mismatches.append({"route": route, "expected_renderer": expected_renderer, "actual_renderer": actual_renderer})
        if expected_renderer not in renderer_names:
            renderer_missing.append({"route": route, "renderer": expected_renderer})
        if row.get("render_mode") == "mapping_only_self_route":
            mapping_only_rows.append({"route": route, "renderer": expected_renderer, "ok": actual_renderer == expected_renderer and expected_renderer in renderer_names, "status": "mapping-only"})
            continue
        if actual_renderer != expected_renderer or expected_renderer not in renderer_names:
            behavior_rows.append({"route": route, "renderer": expected_renderer, "ok": False, "status": "blocked", "elapsed_ms": 0, "body_size": 0, "error": "route mapping or renderer missing"})
            continue
        behavior_rows.append(_render_direct(route, expected_renderer))

    covered_routes = set(routes)
    untested_dispatch_rows = [
        asdict(_classify_uncovered_route(route, renderer))
        for route, renderer in sorted(route_map.items())
        if route not in covered_routes
    ]
    classification_rows = _classification_summary(untested_dispatch_rows)
    behavior_pass_count = sum(1 for row in behavior_rows if row.get("ok"))
    blocked_behavior_rows = [row for row in behavior_rows if not row.get("ok")]
    self_route_mapping_verified = bool(mapping_only_rows and mapping_only_rows[0].get("ok"))
    manifest_surface_present = "v1031-dashboard-route-manifest-renderer-reconciliation" in manifest_source
    total_elapsed_ms = sum(int(row.get("elapsed_ms") or 0) for row in behavior_rows)
    required_tokens = [
        CURRENT_MILESTONE,
        DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_ID,
        "dashboard_route_manifest_renderer_reconciliation=True",
        "baseline_behavioral_route_count=48",
        "mapping_reconciled_route_count=49",
        "behavior_rendered_route_count=48",
        "self_route_mapping_verified=True",
        "manual_dispatch_routes_classified=True",
        "manual_dashboard_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "route_manifest_replaces_dashboard_routes=False",
        "route_manifest_generates_routes=False",
        "dashboard_wiring_generated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
        SELF_ROUTE,
    ]
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "baseline-reused", "ok": len(baseline_rows) == BASELINE_ROUTE_COUNT, "message": f"baseline_behavioral_route_count={len(baseline_rows)}"},
        {"name": "mapping-reconciled-count", "ok": len(route_rows) == MAPPING_RECONCILED_ROUTE_COUNT and not duplicate_routes, "message": f"mapping_reconciled_route_count={len(route_rows)} duplicate_routes={duplicate_routes}"},
        {"name": "route-to-renderer-map-reconciled", "ok": not mapping_mismatches, "message": f"mapping_mismatches={mapping_mismatches[:5]}"},
        {"name": "renderer-functions-present", "ok": not renderer_missing, "message": f"renderer_missing={renderer_missing[:5]}"},
        {"name": "baseline-routes-render-behaviorally", "ok": behavior_pass_count == BASELINE_ROUTE_COUNT and not blocked_behavior_rows, "message": f"behavior_rendered_route_count={behavior_pass_count}; blocked={blocked_behavior_rows[:3]}"},
        {"name": "self-route-mapping-verified", "ok": self_route_mapping_verified, "message": f"self route mapping rows={mapping_only_rows}"},
        {"name": "manual-dispatch-routes-classified", "ok": len(untested_dispatch_rows) >= 1 and sum(row.get('count', 0) for row in classification_rows) == len(untested_dispatch_rows), "message": f"uncovered={len(untested_dispatch_rows)} classifications={classification_rows}"},
        {"name": "source-manifest-representation-present", "ok": manifest_surface_present, "message": "Source surface manifest represents the v1031 route manifest-to-renderer reconciliation surface."},
        {"name": "manual-dashboard-still-authoritative", "ok": "class EidolonDashboardHandler" in dashboard_source and "def do_GET" in dashboard_source and "html = render_" in dashboard_source, "message": "dashboard.py still owns manual route dispatch."},
        {"name": "manual-smoke-still-authoritative", "ok": "def _build_checks" in smoke_source and "class SmokeCheck" in smoke_source, "message": "tools/smoke_check.py still owns manual smoke execution."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Dashboard/smoke/manifest/docs carry v1031 route manifest-to-renderer reconciliation truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["route_manifest_replaces_dashboard_routes", "route_manifest_generates_routes", "dashboard_wiring_generated", "generated_wiring_activated", "route_presence_is_authorization", "route_reconciliation_is_release_approval", "reconciliation_executes_governed_actions", "reconciliation_applies_patches", "reconciliation_writes_memory", "reconciliation_creates_release", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "Route manifest-to-renderer reconciliation grants no routing, release, action, memory, or autonomy authority."},
    ]
    ok = all(bool(row["ok"]) for row in rows)
    report = {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_ID,
        "state": "dashboard_route_manifest_renderer_reconciliation_review_only",
        "dashboard_module": DASHBOARD_MODULE,
        "baseline_module": BASELINE_MODULE,
        "source_manifest_module": SOURCE_MANIFEST_MODULE,
        "manual_smoke_module": MANUAL_SMOKE_MODULE,
        "baseline_behavioral_route_count": len(baseline_rows),
        "mapping_reconciled_route_count": len(route_rows),
        "behavior_rendered_route_count": behavior_pass_count,
        "behavior_rendered_route_target": BASELINE_ROUTE_COUNT,
        "route_rows": route_rows,
        "behavior_rows": behavior_rows,
        "mapping_only_rows": mapping_only_rows,
        "blocked_behavior_rows": blocked_behavior_rows,
        "mapping_mismatches": mapping_mismatches,
        "renderer_missing": renderer_missing,
        "duplicate_routes": duplicate_routes,
        "self_route_mapping_verified": self_route_mapping_verified,
        "manual_dispatch_route_count": len(route_map),
        "manual_dispatch_uncovered_route_count": len(untested_dispatch_rows),
        "manual_dispatch_uncovered_rows": untested_dispatch_rows,
        "dispatch_classification_rows": classification_rows,
        "manual_dispatch_routes_classified": True,
        "total_behavior_elapsed_ms": total_elapsed_ms,
        "dashboard_route_manifest_renderer_reconciliation": True,
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


def dashboard_route_manifest_renderer_reconciliation_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", DASHBOARD_ROUTE_MANIFEST_RENDERER_RECONCILIATION_ID)),
        f"dashboard_route_manifest_renderer_reconciliation={report.get('dashboard_route_manifest_renderer_reconciliation')}",
        f"baseline_behavioral_route_count={report.get('baseline_behavioral_route_count')}",
        f"mapping_reconciled_route_count={report.get('mapping_reconciled_route_count')}",
        f"behavior_rendered_route_count={report.get('behavior_rendered_route_count')}",
        f"self_route_mapping_verified={report.get('self_route_mapping_verified')}",
        f"manual_dispatch_route_count={report.get('manual_dispatch_route_count')}",
        f"manual_dispatch_uncovered_route_count={report.get('manual_dispatch_uncovered_route_count')}",
        f"manual_dispatch_routes_classified={report.get('manual_dispatch_routes_classified')}",
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
        lines.append("\nDispatch classification rows:")
        for row in report.get("dispatch_classification_rows", []):
            lines.append(f"- {row.get('classification')}: {row.get('count')}")
        lines.append("\nMapping-only rows:")
        for row in report.get("mapping_only_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')} ok={row.get('ok')} status={row.get('status')}")
        lines.append("\nBlocked rows:")
        for row in report.get("blocked", []):
            lines.append(f"- {row.get('name')}: {row.get('message')}")
    return "\n".join(lines)


# v1031.0 Dashboard Route Manifest-to-Renderer Reconciliation v1 tokens: dashboard-route-manifest-to-renderer-reconciliation-v1 /dashboard-route-manifest-renderer-reconciliation build_dashboard_route_manifest_renderer_reconciliation_review dashboard_route_manifest_renderer_reconciliation_review_text module=conscious_agent/dashboard_route_manifest_renderer_reconciliation.py dashboard_module=conscious_agent/dashboard.py baseline_module=conscious_agent/dashboard_route_behavioral_coverage_expansion.py baseline_behavioral_route_count=48 mapping_reconciled_route_count=49 behavior_rendered_route_count=48 self_route_mapping_verified=True manual_dispatch_routes_classified=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip.
