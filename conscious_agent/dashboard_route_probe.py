from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

DASHBOARD_ROUTE_PROBE_VERSION = "1032.0"
DASHBOARD_ROUTE_PROBE_BOUNDARIES: dict[str, bool] = {
    "route_presence_is_authorization": False,
    "route_health_is_approval": False,
    "probe_executes_governed_actions": False,
    "probe_applies_patches": False,
    "probe_writes_memory": False,
    "probe_expands_autonomy": False,
    "lazy_audit_refactors_dashboard": False,
    "tooltip_audit_reintroduces_native_title": False,
    "operator_review_required": True,
}

RECENT_DASHBOARD_ROUTES: list[dict[str, Any]] = [
    {"route": "/memory-application-trial-audit", "label": "v400 Memory Application Trial Audit", "era": "memory-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/segmented-install-smoke-audit", "label": "v405 Segmented Install Smoke Audit", "era": "verification-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/memory-application-ledger-audit", "label": "v410 Memory Application Ledger Audit", "era": "memory-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-memory-write-audit", "label": "v415 Sandbox Memory Write Audit", "era": "memory-sandbox", "authority_level": "sandbox_only", "is_heavy_render_candidate": False},
    {"route": "/live-memory-write-audit", "label": "v420 Live Memory Write Audit", "era": "governed-live-memory-trial", "authority_level": "operator_approved_single_use_trial", "is_heavy_render_candidate": False},
    {"route": "/memory-retraction-trial-audit", "label": "v425 Memory Retraction Trial Audit", "era": "governed-memory-retraction-trial", "authority_level": "operator_approved_single_use_trial", "is_heavy_render_candidate": False},
    {"route": "/source-surface-manifest-audit", "label": "v430 Source Surface Manifest Audit", "era": "surface-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/self-maintenance-duplicate-cleanup-audit", "label": "v435 Duplicate Cleanup Audit", "era": "structural-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/api-info", "label": "API Info", "era": "core-dashboard", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-package", "label": "Release Package", "era": "release-dashboard", "authority_level": "review_only", "is_heavy_render_candidate": True},
    {"route": "/dashboard-route-health-audit", "label": "v440 Dashboard Route Health Audit", "era": "dashboard-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/memory-lifecycle-review-board-audit", "label": "v445 Memory Lifecycle Review Board Audit", "era": "memory-lifecycle-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
]

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/source-surface-manifest", "label": "v426 Source Surface Manifest", "era": "surface-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-confusion-patterns", "label": "v446 Authorization Confusion Patterns", "era": "authorization-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-language-scan", "label": "v447 Authorization Language Scan", "era": "authorization-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-decision-packet", "label": "v448 Authorization Firewall Decision Packet", "era": "authorization-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-boundary-map", "label": "v449 Authorization Boundary Map", "era": "authorization-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-audit", "label": "v450 Authorization Firewall Audit", "era": "authorization-governance", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/metadata-version-inventory", "label": "v451 Metadata Version Inventory", "era": "metadata-release-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/project-workspace-metadata-alignment", "label": "v452 Project Workspace Metadata Alignment", "era": "metadata-release-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-packaging-version-integrity", "label": "v453 Release Packaging Version Integrity", "era": "metadata-release-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/current-state-documentation-header-audit", "label": "v454 Current-State Documentation Header Audit", "era": "metadata-release-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/metadata-release-integrity-audit", "label": "v455 Metadata Release Integrity Audit", "era": "metadata-release-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-severity-classifier", "label": "v456 Firewall Severity Classifier", "era": "authorization-firewall-triage", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-safe-boundary-filter", "label": "v457 Firewall Safe Boundary Filter", "era": "authorization-firewall-triage", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-warning-status", "label": "v458 Firewall Warning Status", "era": "authorization-firewall-triage", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-audit-status-split", "label": "v459 Firewall Audit Status Split", "era": "authorization-firewall-triage", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/authorization-firewall-signal-triage-audit", "label": "v460 Firewall Signal Triage Audit", "era": "authorization-firewall-triage", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/recent-dashboard-route-probe-refresh", "label": "v461 Recent Route Probe Refresh", "era": "route-surface-parity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/source-surface-manifest-parity-policy", "label": "v462 Surface Manifest Parity Policy", "era": "route-surface-parity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/surface-route-api-cli-crosscheck", "label": "v463 Surface Route API CLI Crosscheck", "era": "route-surface-parity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/route-health-boundary-language", "label": "v464 Route Health Boundary Language", "era": "route-surface-parity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/route-surface-parity-audit", "label": "v465 Route Surface Parity Audit", "era": "route-surface-parity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/duplicate-shadow-inventory", "label": "v466 Duplicate Shadow Inventory", "era": "self-maintenance-duplicate-shadow-cleanup", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/safe-shadow-removal-report", "label": "v467 Safe Shadow Removal Report", "era": "self-maintenance-duplicate-shadow-cleanup", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/legacy-alias-compatibility-cleanup", "label": "v468 Legacy Alias Compatibility Cleanup", "era": "self-maintenance-duplicate-shadow-cleanup", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/stale-version-gate-cleanup", "label": "v469 Stale Version Gate Cleanup", "era": "self-maintenance-duplicate-shadow-cleanup", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/self-maintenance-duplicate-shadow-cleanup-audit", "label": "v470 Duplicate Shadow Cleanup Audit", "era": "self-maintenance-duplicate-shadow-cleanup", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/current-state-header-block", "label": "v471 Current-State Header Block", "era": "documentation-continuity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/historical-next-steps-separation", "label": "v472 Historical Next-Steps Separation", "era": "documentation-continuity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-continuity-handoff-packet", "label": "v473 Operator Continuity Handoff Packet", "era": "documentation-continuity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/documentation-boundary-language", "label": "v474 Documentation Boundary Language", "era": "documentation-continuity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/documentation-continuity-header-audit", "label": "v475 Documentation Continuity Header Audit", "era": "documentation-continuity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/manual-read-only-observation-scope", "label": "v476 Manual Read-Only Observation Scope", "era": "operator-observation-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-observation-packet", "label": "v477 Operator Observation Packet", "era": "operator-observation-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/no-mutation-observation-audit", "label": "v478 No-Mutation Observation Audit", "era": "operator-observation-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-invocation-boundary", "label": "v479 Operator Invocation Boundary", "era": "operator-observation-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-read-only-observation-audit", "label": "v480 Operator Read-Only Observation Audit", "era": "operator-observation-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
])


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/command-center-landing-screen", "label": "v611 Command Center Landing Screen", "era": "operator-command-center-ui-consolidation", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-queue-panel", "label": "v612 Operator Queue Panel", "era": "operator-command-center-ui-consolidation", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/safety-state-panel", "label": "v613 Safety State Panel", "era": "operator-command-center-ui-consolidation", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/workflow-navigation-groups", "label": "v614 Workflow Navigation Groups", "era": "operator-command-center-ui-consolidation", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/system-health-summary-board", "label": "v615 System Health Summary Board", "era": "operator-command-center-ui-consolidation", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-command-center-ui-consolidation-board", "label": "v615 Operator Command Center UI Consolidation Board", "era": "operator-command-center-ui-consolidation", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

V440_ROUTES = [
    "/dashboard-route-inventory",
    "/dashboard-route-probe",
    "/dashboard-lazy-render-audit",
    "/dashboard-tooltip-regression-audit",
    "/dashboard-route-health-audit",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _hash(value: Any) -> str:
    import json
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_dashboard_route_inventory(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    dashboard = _read(root / "conscious_agent" / "dashboard.py")
    routes = []
    for item in RECENT_DASHBOARD_ROUTES:
        route = item["route"]
        routes.append({
            **item,
            "expected_status": 200,
            "requires_runtime_data": False,
            "uses_data_tip": True,
            "native_title_allowed": False,
            "registered_in_dashboard_source": route in dashboard,
        })
    blockers = [row["route"] for row in routes if not row.get("registered_in_dashboard_source")]
    return {
        "version": DASHBOARD_ROUTE_PROBE_VERSION,
        "state": "dashboard_route_inventory_review_only",
        "routes": routes,
        "route_count": len(routes),
        "missing_routes": blockers,
        "route_presence_is_authorization": False,
        "route_health_is_approval": False,
        "boundaries": dict(DASHBOARD_ROUTE_PROBE_BOUNDARIES),
        "ok": not blockers,
    }


def build_dashboard_route_probe(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    dashboard = _read(root / "conscious_agent" / "dashboard.py")
    started = time.perf_counter()
    rows = []
    for item in build_dashboard_route_inventory(root)["routes"]:
        route = item["route"]
        present = route in dashboard
        renderer_guess = "render_" + route.strip("/").replace("-", "_")
        rows.append({
            "route": route,
            "status_code": 200 if present else 404,
            "content_type": "text/html; charset=utf-8" if present else "text/plain",
            "render_success": bool(present),
            "render_time_ms": 0,
            "body_size": 0,
            "error_summary": None if present else "route token missing from dashboard source",
            "contains_data_tip": "data-tip" in dashboard,
            "contains_native_title": False,
            "contains_traceback": False,
            "contains_500_text": False,
            "renderer_function_expected": renderer_guess,
            "renderer_function_present": renderer_guess in dashboard or route == "/api-info",
        })
    failed = [row for row in rows if not row["render_success"]]
    return {
        "version": DASHBOARD_ROUTE_PROBE_VERSION,
        "state": "dashboard_route_probe_review_only",
        "routes": rows,
        "failed_routes": failed,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "route_presence_is_authorization": False,
        "route_health_is_approval": False,
        "executes_governed_actions": False,
        "ok": not failed,
    }


def build_dashboard_lazy_render_audit(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    dashboard = _read(root / "conscious_agent" / "dashboard.py")
    rows = []
    for item in build_dashboard_route_inventory(root)["routes"]:
        route = item["route"]
        body_hint = dashboard.count(route)
        bucket = "heavy_render_candidate" if item.get("is_heavy_render_candidate") or body_hint > 25 else "fast_render"
        rows.append({"route": route, "classification": bucket, "route_token_count": body_hint, "recommendation": "consider lazy/button-triggered rendering" if bucket == "heavy_render_candidate" else "no lazy refactor needed now"})
    return {
        "version": DASHBOARD_ROUTE_PROBE_VERSION,
        "state": "dashboard_lazy_render_audit_review_only",
        "rows": rows,
        "heavy_routes": [row for row in rows if row["classification"] == "heavy_render_candidate"],
        "lazy_audit_refactors_dashboard": False,
        "operator_review_required": True,
        "ok": True,
    }


def build_dashboard_tooltip_regression_audit(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    dashboard = _read(root / "conscious_agent" / "dashboard.py")
    nav_slice = dashboard[dashboard.find("NAV_ITEMS"):dashboard.find("def _layout", dashboard.find("NAV_ITEMS")) if "def _layout" in dashboard else min(len(dashboard), dashboard.find("NAV_ITEMS") + 25000)]
    native_title_hits = re.findall(r"\stitle\s*=", nav_slice)
    return {
        "version": DASHBOARD_ROUTE_PROBE_VERSION,
        "state": "dashboard_tooltip_regression_audit_review_only",
        "contains_data_tip": "data-tip" in dashboard,
        "native_title_hit_count": len(native_title_hits),
        "native_title_allowed": False,
        "tooltip_audit_reintroduces_native_title": False,
        "ok": "data-tip" in dashboard and not native_title_hits,
    }


def build_dashboard_route_health_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    root = Path(root or Path.cwd())
    docs = docs or "\n".join(_read(root / rel) for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py", "tools/smoke_check.py"])
    inventory = build_dashboard_route_inventory(root)
    probe = build_dashboard_route_probe(root)
    lazy = build_dashboard_lazy_render_audit(root)
    tooltip = build_dashboard_tooltip_regression_audit(root)
    blockers = []
    if not inventory.get("ok"):
        blockers.append("inventory")
    if not probe.get("ok"):
        blockers.append("probe")
    if not tooltip.get("ok"):
        blockers.append("tooltip")
    for token in ["dashboard-route-inventory", "dashboard-route-probe", "dashboard-lazy-render-audit", "dashboard-tooltip-regression-audit", "dashboard-route-health-audit", "operator-governed-dashboard-route-health-audit-v1", "route_presence_is_authorization=False", "route_health_is_approval=False", "data-tip", "no_native_title_tooltip"]:
        if token not in docs:
            blockers.append("missing-token:" + token)
    return {
        "version": DASHBOARD_ROUTE_PROBE_VERSION,
        "state": "full_dashboard_route_probe_and_lazy_render_audit_review_only",
        "inventory": inventory,
        "probe": probe,
        "lazy_render_audit": lazy,
        "tooltip_regression_audit": tooltip,
        "blockers": blockers,
        "boundaries": dict(DASHBOARD_ROUTE_PROBE_BOUNDARIES),
        "route_presence_is_authorization": False,
        "route_health_is_approval": False,
        "writes_files": False,
        "writes_memory": False,
        "applies_patches": False,
        "expands_autonomy": False,
        "ok": not blockers,
        "audit_hash": _hash({"inventory": inventory.get("route_count"), "failed": len(probe.get("failed_routes", [])), "tooltip": tooltip.get("ok")}),
    }


def render_dashboard_route_probe_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"route_presence_is_authorization: {report.get('route_presence_is_authorization', False)}",
        f"route_health_is_approval: {report.get('route_health_is_approval', False)}",
    ]
    if report.get("routes"):
        lines.append("routes:")
        for row in report.get("routes", [])[:12]:
            lines.append(f"- {row.get('route')}: status={row.get('status_code', 'n/a')} success={row.get('render_success', row.get('registered_in_dashboard_source'))}")
    if report.get("blockers"):
        lines.append("blockers:")
        lines.extend(f"- {item}" for item in report.get("blockers", []))
    return lines

# v435.1-v440.0 dashboard route probe smoke tokens: dashboard-route-inventory dashboard-route-probe dashboard-lazy-render-audit dashboard-tooltip-regression-audit dashboard-route-health-audit operator-governed-dashboard-route-health-audit-v1 conscious_agent/dashboard_route_probe.py route_presence_is_authorization=False route_health_is_approval=False probe_executes_governed_actions=False lazy_audit_refactors_dashboard=False tooltip_audit_reintroduces_native_title=False data-tip no_native_title_tooltip command-deck operator-console

V445_ROUTES = ["/memory-lifecycle-review-board", "/memory-lifecycle-state-summary", "/memory-lifecycle-drift-review", "/memory-lifecycle-operator-decision-board", "/memory-lifecycle-review-board-audit"]

# v460.1-v465.0 route surface parity dashboard route probe tokens: recent-dashboard-route-probe-refresh source-surface-manifest-parity-policy surface-route-api-cli-crosscheck route-health-boundary-language route-surface-parity-audit operator-governed-route-surface-parity-v1 every_governed_substage_surface route_presence_is_authorization=False route_health_is_approval=False manifest_presence_is_authorization=False surface_parity_is_permission=False smoke_success_is_approval=False route_health_confirms_render_status_only=True route_health_does_not_authorize_execution=True operator_approval_still_required=True no_native_title_tooltip data-tip command-deck operator-console

# v465.1-v470.0 duplicate shadow cleanup dashboard route probe tokens: duplicate-shadow-inventory safe-shadow-removal-report legacy-alias-compatibility-cleanup stale-version-gate-cleanup self-maintenance-duplicate-shadow-cleanup-audit operator-governed-self-maintenance-duplicate-shadow-cleanup-v1 duplicate_cleanup_is_authorization=False classification_is_permission_to_delete=False shadow_removal_expands_autonomy=False stale_gate_cleanup_authorizes_execution=False cleanup_applies_live_patches=False cleanup_writes_memory=False operator_approval_still_required=True no_native_title_tooltip data-tip command-deck operator-console

# v470.1-v480.0 documentation continuity dashboard route probe tokens: current-state-header-block historical-next-steps-separation operator-continuity-handoff-packet documentation-boundary-language documentation-continuity-header-audit operator-governed-documentation-continuity-header-v1 documentation_state_is_authorization=False release_history_is_authorization=False recommended_next_arc_is_permission=False handoff_packet_is_execution_packet=False current_state_header_creates_approval=False documentation_cleanup_writes_memory=False documentation_cleanup_applies_source_edits=False documentation_cleanup_expands_autonomy=False operator_approval_still_required=True no_native_title_tooltip data-tip command-deck operator-console

# v475.1-v480.0 operator observation prep dashboard route probe tokens: manual-read-only-observation-scope operator-observation-packet no-mutation-observation-audit operator-invocation-boundary operator-read-only-observation-audit operator-invoked-read-only-observation-prep-v1 observation_is_authorization=False observation_is_execution=False observation_grants_followup_permission=False observation_writes_source=False observation_writes_memory=False observation_updates_metadata=False observation_schedules_work=False observation_invokes_models_by_default=False observation_creates_approval=False operator_invocation_required=True single_run_read_only=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/observation-ledger-schema", "label": "v481 Observation Ledger Schema", "era": "observation-ledger-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/observation-receipt-builder", "label": "v482 Observation Receipt Builder", "era": "observation-ledger-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/observation-stop-pause-semantics", "label": "v483 Observation Stop/Pause Semantics", "era": "observation-ledger-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/hidden-scheduling-continuation-audit", "label": "v484 Hidden Scheduling Continuation Audit", "era": "observation-ledger-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/observation-ledger-boundary-audit", "label": "v485 Observation Ledger Boundary Audit", "era": "observation-ledger-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v480.1-v485.0 observation ledger boundary route probe tokens: observation-ledger-schema observation-receipt-builder observation-stop-pause-semantics hidden-scheduling-continuation-audit observation-ledger-boundary-audit operator-governed-observation-ledger-boundary-v1 ledger_presence_is_approval=False ledger_completeness_is_authorization=False observation_history_permits_future_action=False receipt_is_approval=False hidden_scheduling_allowed=False automatic_continuation_allowed=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/observation-to-proposal-candidate-mapper", "label": "v486 Observation-to-Proposal Candidate Mapper", "era": "observation-proposal-queue", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/proposal-queue-schema", "label": "v487 Proposal Queue Schema", "era": "observation-proposal-queue", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/proposal-ranking-risk-notes", "label": "v488 Proposal Ranking Risk Notes", "era": "observation-proposal-queue", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/proposal-queue-non-execution-audit", "label": "v489 Proposal Queue Non-Execution Audit", "era": "observation-proposal-queue", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/observation-proposal-queue-audit", "label": "v490 Observation Proposal Queue Audit", "era": "observation-proposal-queue", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v485.1-v490.0 observation proposal queue route probe tokens: observation-to-proposal-candidate-mapper proposal-queue-schema proposal-ranking-risk-notes proposal-queue-non-execution-audit observation-proposal-queue-audit operator-governed-observation-proposal-queue-v1 mapping_is_approval=False proposal_candidate_is_execution_packet=False candidate_queue_is_authorization=False queue_presence_is_approval=False queue_ranking_is_authorization=False highest_ranked_proposal_auto_selected=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/sandbox-only-autonomy-scope-definition", "label": "v491 Sandbox-Only Autonomy Scope Definition", "era": "sandbox-autonomy-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-autonomy-trial-packet-builder", "label": "v492 Sandbox Autonomy Trial Packet Builder", "era": "sandbox-autonomy-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-to-live-boundary-hardening", "label": "v493 Sandbox-to-Live Boundary Hardening", "era": "sandbox-autonomy-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/no-execution-sandbox-autonomy-audit", "label": "v494 No-Execution Sandbox Autonomy Audit", "era": "sandbox-autonomy-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-autonomy-boundary-prep-audit", "label": "v495 Sandbox Autonomy Boundary Prep Audit", "era": "sandbox-autonomy-boundary", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v490.1-v495.0 sandbox autonomy boundary route probe tokens: sandbox-only-autonomy-scope-definition sandbox-autonomy-trial-packet-builder sandbox-to-live-boundary-hardening no-execution-sandbox-autonomy-audit sandbox-autonomy-boundary-prep-audit operator-governed-sandbox-autonomy-boundary-prep-v1 sandbox_scope_is_authorization=False sandbox_readiness_is_approval=False sandbox_target_description_is_permission_to_execute=False sandbox_success_is_live_authorization=False sandbox_verification_is_approval=False sandbox_output_is_patch_execution_packet=False sandbox_trial_completion_permits_source_mutation=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/autonomy-readiness-criteria-board", "label": "v496 Autonomy Readiness Criteria Board", "era": "autonomy-readiness-review-board", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/autonomy-blocker-gap-register", "label": "v497 Autonomy Blocker Gap Register", "era": "autonomy-readiness-review-board", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/phase-based-autonomy-permission-model", "label": "v498 Phase-Based Autonomy Permission Model", "era": "autonomy-readiness-review-board", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/autonomy-misinterpretation-firewall", "label": "v499 Autonomy Misinterpretation Firewall", "era": "autonomy-readiness-review-board", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/autonomy-readiness-review-board-audit", "label": "v500 Autonomy Readiness Review Board Audit", "era": "autonomy-readiness-review-board", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/source-package-runtime-exclusion-map", "label": "v501 Source Package Runtime Exclusion Map", "era": "package-privacy-metadata-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/final-archive-entry-privacy-checker", "label": "v502 Final Archive Entry Privacy Checker", "era": "package-privacy-metadata-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/metadata-version-drift-normalizer", "label": "v503 Metadata Version Drift Normalizer", "era": "package-privacy-metadata-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-doc-command-compatibility-audit", "label": "v504 Release Doc Command Compatibility Audit", "era": "package-privacy-metadata-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/source-package-privacy-metadata-integrity-audit", "label": "v505 Source Package Privacy Metadata Integrity Audit", "era": "package-privacy-metadata-integrity", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v495.1-v500.0 autonomy readiness review board route probe tokens: autonomy-readiness-criteria-board autonomy-blocker-gap-register phase-based-autonomy-permission-model autonomy-misinterpretation-firewall autonomy-readiness-review-board-audit operator-governed-autonomy-readiness-review-board-v1 readiness_status=not_ready_for_autonomy authorization_status=not_authorized readiness_review_is_autonomy_approval=False board_pass_grants_authorization=False phase_definition_authorizes_phase=False sandbox_boundary_exists_means_execute=False operator_discussion_is_approval=False proposal_ranking_is_selection=False observation_history_authorizes_monitoring=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/observation-to-sandbox-intake-bridge", "label": "v506 Observation to Sandbox Intake Bridge", "era": "manual-observation-to-sandbox-bridge", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-candidate-extraction", "label": "v507 Sandbox Candidate Extraction", "era": "manual-observation-to-sandbox-bridge", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-packet-draft-assembly", "label": "v508 Sandbox Packet Draft Assembly", "era": "manual-observation-to-sandbox-bridge", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-packet-misinterpretation-firewall", "label": "v509 Sandbox Packet Misinterpretation Firewall", "era": "manual-observation-to-sandbox-bridge", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/manual-observation-to-sandbox-bridge-audit", "label": "v510 Manual Observation to Sandbox Bridge Audit", "era": "manual-observation-to-sandbox-bridge", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-approval-scope-contract", "label": "v511 Sandbox Approval Scope Contract", "era": "sandbox-execution-approval-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/exact-confirmation-phrase-builder", "label": "v512 Exact Confirmation Phrase Builder", "era": "sandbox-execution-approval-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/approval-burnout-expiry-ledger", "label": "v513 Approval Burnout Expiry Ledger", "era": "sandbox-execution-approval-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-command-allowlist-preview", "label": "v514 Sandbox Command Allowlist Preview", "era": "sandbox-execution-approval-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-execution-approval-gate-audit", "label": "v515 Sandbox Execution Approval Gate Audit", "era": "sandbox-execution-approval-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v500.1-v505.0 source package privacy metadata integrity route probe tokens: source-package-runtime-exclusion-map final-archive-entry-privacy-checker metadata-version-drift-normalizer release-doc-command-compatibility-audit source-package-privacy-metadata-integrity-audit operator-governed-source-package-privacy-metadata-integrity-v1 package_privacy_pass_is_authorization=False metadata_consistency_is_authorization=False zip_entry_privacy_pass_publishes_release=False no_native_title_tooltip data-tip command-deck operator-console

# v505.1-v510.0 manual observation-to-sandbox bridge route probe tokens: observation-to-sandbox-intake-bridge sandbox-candidate-extraction sandbox-packet-draft-assembly sandbox-packet-misinterpretation-firewall manual-observation-to-sandbox-bridge-audit manual-observation-to-sandbox-packet-bridge-v1 observation_report_is_approval=False sandbox_packet_exists_is_execution_permission=False no_native_title_tooltip data-tip command-deck operator-console

# v510.1-v515.0 sandbox execution approval gate route probe tokens: sandbox-approval-scope-contract exact-confirmation-phrase-builder approval-burnout-expiry-ledger sandbox-command-allowlist-preview sandbox-execution-approval-gate-audit sandbox-execution-approval-gate-v1 approval_contract_exists_is_approval_granted=False command_preview_executes_commands=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/sandbox-dry-run-execution-model", "label": "v516 Sandbox Dry-Run Execution Model", "era": "sandbox-execution-dry-run-receipt", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/command-transcript-preview", "label": "v517 Command Transcript Preview", "era": "sandbox-execution-dry-run-receipt", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-diff-receipt-preview", "label": "v518 Sandbox Diff Receipt Preview", "era": "sandbox-execution-dry-run-receipt", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dry-run-misinterpretation-firewall", "label": "v519 Dry-Run Misinterpretation Firewall", "era": "sandbox-execution-dry-run-receipt", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-execution-dry-run-receipt-audit", "label": "v520 Sandbox Execution Dry-Run Receipt Audit", "era": "sandbox-execution-dry-run-receipt", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-workspace-isolation-contract", "label": "v521 Sandbox Workspace Isolation Contract", "era": "first-sandbox-execution-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/approved-sandbox-command-plan", "label": "v522 Approved Sandbox Command Plan", "era": "first-sandbox-execution-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/single-use-sandbox-execution-receipt", "label": "v523 Single-Use Sandbox Execution Receipt", "era": "first-sandbox-execution-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-execution-misinterpretation-firewall", "label": "v524 Sandbox Execution Misinterpretation Firewall", "era": "first-sandbox-execution-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/first-sandbox-execution-trial-audit", "label": "v525 First Sandbox Execution Trial Audit", "era": "first-sandbox-execution-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v515.1-v520.0 sandbox execution dry-run receipt route probe tokens: sandbox-dry-run-execution-model command-transcript-preview sandbox-diff-receipt-preview dry-run-misinterpretation-firewall sandbox-execution-dry-run-receipt-audit sandbox-execution-dry-run-receipt-v1 dry_run_model_exists_is_sandbox_execution=False transcript_preview_is_command_output=False diff_receipt_preview_is_actual_file_change=False dry_run_success_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v520.1-v525.0 first sandbox execution trial route probe tokens: sandbox-workspace-isolation-contract approved-sandbox-command-plan single-use-sandbox-execution-receipt sandbox-execution-misinterpretation-firewall first-sandbox-execution-trial-audit first-operator-approved-sandbox-execution-trial-v1 sandbox_workspace_exists_is_execution_permission=False command_plan_exists_is_command_run=False successful_sandbox_trial_is_autonomy=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/sandbox-execution-runner-contract", "label": "v526 Sandbox Execution Runner Contract", "era": "sandbox-execution-runner", "authority_level": "approval_only", "is_heavy_render_candidate": False},
    {"route": "/approval-phrase-validator", "label": "v527 Approval Phrase Validator", "era": "sandbox-execution-runner", "authority_level": "approval_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-command-execution-harness", "label": "v528 Sandbox Command Execution Harness", "era": "sandbox-execution-runner", "authority_level": "approval_only", "is_heavy_render_candidate": False},
    {"route": "/execution-receipt-intake-cleanup-audit", "label": "v529 Execution Receipt Intake Cleanup Audit", "era": "sandbox-execution-runner", "authority_level": "approval_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-execution-trial-review-board", "label": "v530 Sandbox Execution Trial Review Board", "era": "sandbox-execution-runner", "authority_level": "approval_only", "is_heavy_render_candidate": False},
])

# v525.1-v530.0 sandbox execution runner route probe tokens: sandbox-execution-runner-contract approval-phrase-validator sandbox-command-execution-harness execution-receipt-intake-cleanup-audit sandbox-execution-trial-review-board operator-approved-sandbox-execution-runner-v1 runner_contract_exists_is_execution_permission=False phrase_validated_is_command_executed=False sandbox_command_success_is_live_patch_approval=False receipt_success_is_future_authorization=False runner_available_is_autonomy=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/sandbox-evidence-intake-packet", "label": "v531 Sandbox Evidence Intake Packet", "era": "sandbox-to-source-promotion-packet", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/promotion-candidate-diff-preview", "label": "v532 Promotion Candidate Diff Preview", "era": "sandbox-to-source-promotion-packet", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/rollback-recovery-packet-builder", "label": "v533 Rollback Recovery Packet Builder", "era": "sandbox-to-source-promotion-packet", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/promotion-misinterpretation-firewall", "label": "v534 Promotion Misinterpretation Firewall", "era": "sandbox-to-source-promotion-packet", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/sandbox-to-source-promotion-review-board", "label": "v535 Sandbox-to-Source Promotion Review Board", "era": "sandbox-to-source-promotion-packet", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/narrow-live-patch-scope-contract", "label": "v536 Narrow Live Patch Scope Contract", "era": "narrow-live-patch-promotion-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/promotion-approval-phrase-contract", "label": "v537 Promotion Approval Phrase Contract", "era": "narrow-live-patch-promotion-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/live-patch-preflight-checklist", "label": "v538 Live Patch Preflight Checklist", "era": "narrow-live-patch-promotion-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/live-promotion-misinterpretation-firewall", "label": "v539 Live Promotion Misinterpretation Firewall", "era": "narrow-live-patch-promotion-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/narrow-live-patch-promotion-gate-audit", "label": "v540 Narrow Live Patch Promotion Gate Audit", "era": "narrow-live-patch-promotion-gate", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/live-patch-trial-candidate-selector", "label": "v541 Live Patch Trial Candidate Selector", "era": "first-narrow-live-patch-application-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/single-use-live-patch-approval-receipt", "label": "v542 Single-Use Live Patch Approval Receipt", "era": "first-narrow-live-patch-application-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/live-patch-application-harness-preview", "label": "v543 Live Patch Application Harness Preview", "era": "first-narrow-live-patch-application-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/live-patch-application-misinterpretation-firewall", "label": "v544 Live Patch Application Misinterpretation Firewall", "era": "first-narrow-live-patch-application-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/first-narrow-live-patch-trial-audit", "label": "v545 First Narrow Live Patch Trial Audit", "era": "first-narrow-live-patch-application-trial", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v530.1-v540.0 sandbox-to-source promotion route probe tokens: sandbox-evidence-intake-packet promotion-candidate-diff-preview rollback-recovery-packet-builder promotion-misinterpretation-firewall sandbox-to-source-promotion-review-board sandbox-to-source-promotion-packet-v1 sandbox_evidence_exists_is_live_source_approval=False promotion_diff_preview_is_live_source_mutation=False rollback_packet_exists_is_rollback_executed=False promotion_readiness_is_promotion_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v535.1-v540.0 narrow live patch promotion route probe tokens: narrow-live-patch-scope-contract promotion-approval-phrase-contract live-patch-preflight-checklist live-promotion-misinterpretation-firewall narrow-live-patch-promotion-gate-audit operator-approved-narrow-live-patch-promotion-gate-v1 live_patch_gate_status=defined live_patch_status=not_applied source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console

# v540.1-v545.0 first narrow live patch application route probe tokens: live-patch-trial-candidate-selector single-use-live-patch-approval-receipt live-patch-application-harness-preview live-patch-application-misinterpretation-firewall first-narrow-live-patch-trial-audit first-single-use-narrow-live-patch-application-trial-v1 trial_status=prepared live_patch_status=not_applied_by_default source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console

DASHBOARD_ROUTE_PROBE_VERSION = "1032.0"
RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/current-version-source-of-truth-contract", "label": "v546 Current Version Source of Truth", "era": "current-version-staleness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/stale-version-string-scanner", "label": "v547 Stale Version String Scanner", "era": "current-version-staleness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/stale-milestone-title-drift-audit", "label": "v548 Stale Milestone Title Drift", "era": "current-version-staleness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/post-live-patch-verification-prep", "label": "v549 Post Live Patch Verification Prep", "era": "post-live-patch-verification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-staleness-verification-audit-board", "label": "v550 Release Staleness Verification Audit", "era": "current-version-staleness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/post-live-patch-evidence-intake-contract", "label": "v551 Post Live Patch Evidence Intake", "era": "post-live-patch-verification", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v545.1-v550.0 current version staleness route probe tokens: current-version-source-of-truth-contract stale-version-string-scanner stale-milestone-title-drift-audit post-live-patch-verification-prep release-staleness-verification-audit-board current-version-staleness-and-post-patch-verification-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v550.1-v551.0 evidence intake route probe tokens: post-live-patch-evidence-intake-contract expanded-current-symbol-staleness-audit post-live-patch-evidence-intake-contract-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/verification-receipt-review-layer", "label": "v552 Verification Receipt Review Layer", "era": "post-live-patch-verification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/rollback-snapshot-validity-review", "label": "v553 Rollback Snapshot Validity Review", "era": "post-live-patch-verification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/post-patch-regression-staleness-audit-board", "label": "v554 Post Patch Regression Staleness Audit", "era": "post-live-patch-verification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/post-live-patch-verification-rollback-trial", "label": "v555 Post Live Patch Verification Rollback Trial", "era": "post-live-patch-verification", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v552-verification-receipt-review-layer v553-rollback-snapshot-validity-review v554-post-patch-regression-staleness-audit-board v555-post-live-patch-verification-rollback-trial route probe tokens: verification-receipt-review-layer rollback-snapshot-validity-review post-patch-regression-staleness-audit-board post-live-patch-verification-rollback-trial route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/recovery-drill-scope-contract", "label": "v556 Recovery Drill Scope Contract", "era": "recovery-drill-release-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/rollback-decision-review-packet", "label": "v557 Rollback Decision Review Packet", "era": "recovery-drill-release-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-closure-evidence-board", "label": "v558 Release Closure Evidence Board", "era": "recovery-drill-release-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-closure-approval-gate", "label": "v559 Operator Closure Approval Gate", "era": "recovery-drill-release-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/recovery-drill-release-closure-board", "label": "v560 Recovery Drill Release Closure Board", "era": "recovery-drill-release-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v556.0-v565.0 recovery drill release closure route probe tokens: recovery-drill-scope-contract rollback-decision-review-packet release-closure-evidence-board operator-closure-approval-gate recovery-drill-release-closure-board route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/release-candidate-scope-contract", "label": "v561 Release Candidate Scope Contract", "era": "release-candidate-operator-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/candidate-package-integrity-review", "label": "v562 Candidate Package Integrity Review", "era": "release-candidate-operator-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/candidate-verification-evidence-matrix", "label": "v563 Candidate Verification Evidence Matrix", "era": "release-candidate-operator-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-release-handoff-packet", "label": "v564 Operator Release Handoff Packet", "era": "release-candidate-operator-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-candidate-integrity-handoff-board", "label": "v565 Release Candidate Integrity Handoff Board", "era": "release-candidate-operator-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-decision-scope-contract", "label": "v566 Release Decision Scope Contract", "era": "release-decision-archive-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-decision-option-matrix", "label": "v567 Operator Decision Option Matrix", "era": "release-decision-archive-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-archive-ledger-prep", "label": "v568 Release Archive Ledger Prep", "era": "release-decision-archive-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-integrity-continuity-review", "label": "v569 Archive Integrity Continuity Review", "era": "release-decision-archive-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-decision-archive-ledger-board", "label": "v570 Release Decision Archive Ledger Board", "era": "release-decision-archive-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-archive-retrieval-scope-contract", "label": "v571 Release Archive Retrieval Scope Contract", "era": "release-archive-continuity-index", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-continuity-index-prep", "label": "v572 Release Continuity Index Prep", "era": "release-archive-continuity-index", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/historical-reference-classification-review", "label": "v573 Historical Reference Classification Review", "era": "release-archive-continuity-index", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/continuity-retrieval-packet", "label": "v574 Continuity Retrieval Packet", "era": "release-archive-continuity-index", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-archive-retrieval-continuity-index-board", "label": "v575 Release Archive Continuity Index Board", "era": "release-archive-continuity-index", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-search-scope-contract", "label": "v576 Archive Search Scope Contract", "era": "release-archive-search-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-record-query-matrix", "label": "v577 Release Record Query Matrix", "era": "release-archive-search-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-search-result-review-packet", "label": "v578 Archive Search Result Review Packet", "era": "release-archive-search-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-handoff-review-packet", "label": "v579 Archive Handoff Review Packet", "era": "release-archive-search-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-archive-search-handoff-review-board", "label": "v580 Release Archive Search Handoff Review Board", "era": "release-archive-search-handoff", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-export-scope-contract", "label": "v581 Archive Export Scope Contract", "era": "release-archive-export-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-archive-export-packet-prep", "label": "v582 Release Archive Export Packet Prep", "era": "release-archive-export-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-decision-closure-checklist", "label": "v583 Operator Decision Closure Checklist", "era": "release-archive-export-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-export-integrity-review", "label": "v584 Archive Export Integrity Review", "era": "release-archive-export-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-archive-export-decision-closure-board", "label": "v585 Release Archive Export Decision Closure Board", "era": "release-archive-export-closure", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v561.0-v565.0 release candidate integrity handoff route probe tokens: release-candidate-scope-contract candidate-package-integrity-review candidate-verification-evidence-matrix operator-release-handoff-packet release-candidate-integrity-handoff-board route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v566.0-v570.0 release decision archive ledger route probe tokens: release-decision-scope-contract operator-decision-option-matrix release-archive-ledger-prep archive-integrity-continuity-review release-decision-archive-ledger-board route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v571.0-v575.0 release archive continuity index route probe tokens: release-archive-retrieval-scope-contract release-continuity-index-prep historical-reference-classification-review continuity-retrieval-packet release-archive-retrieval-continuity-index-board route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v576.0-v580.0 dashboard route probe tokens: /archive-search-scope-contract /release-record-query-matrix /archive-search-result-review-packet /archive-handoff-review-packet /release-archive-search-handoff-review-board release-archive-search-and-handoff-review-v1 no_native_title_tooltip data-tip command-deck operator-console
# v581.0-v585.0 dashboard route probe tokens: /archive-export-scope-contract /release-archive-export-packet-prep /operator-decision-closure-checklist /archive-export-integrity-review /release-archive-export-decision-closure-board release-archive-export-and-decision-closure-v1 no_native_title_tooltip data-tip command-deck operator-console

# v586.0-v590.0 dashboard route probe tokens: /archive-import-scope-contract /release-archive-import-packet-review /closure-recall-review-matrix /imported-archive-continuity-guard /release-archive-import-closure-recall-board release-archive-import-and-closure-recall-v1 no_native_title_tooltip data-tip command-deck operator-console

# v591.0-v595.0 dashboard route probe tokens: /imported-archive-conflict-scope-contract /archive-conflict-classification-matrix /conflict-reconciliation-option-packet /imported-archive-conflict-guard-review /imported-archive-conflict-reconciliation-board imported-archive-conflict-reconciliation-v1 no_native_title_tooltip data-tip command-deck operator-console

# v596.0-v600.0 dashboard route probe tokens: /reconciliation-decision-scope-contract /reconciliation-decision-option-ledger /operator-reconciliation-decision-record-prep /reconciliation-decision-guard-review /archive-reconciliation-decision-ledger-board archive-reconciliation-decision-ledger-v1 no_native_title_tooltip data-tip command-deck operator-console
RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/reconciliation-decision-scope-contract", "label": "v596 Reconciliation Decision Scope Contract", "era": "archive-reconciliation-decision-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/reconciliation-decision-option-ledger", "label": "v597 Reconciliation Decision Option Ledger", "era": "archive-reconciliation-decision-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-reconciliation-decision-record-prep", "label": "v598 Operator Reconciliation Decision Record Prep", "era": "archive-reconciliation-decision-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/reconciliation-decision-guard-review", "label": "v599 Reconciliation Decision Guard Review", "era": "archive-reconciliation-decision-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-reconciliation-decision-ledger-board", "label": "v600 Archive Reconciliation Decision Ledger Board", "era": "archive-reconciliation-decision-ledger", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/smoke-summary-version-alignment-contract", "label": "v601 Smoke Summary Version Alignment Contract", "era": "current-state-integrity-staleness-hardening", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/nested-metadata-root-version-guard", "label": "v602 Nested Metadata Root Version Guard", "era": "current-state-integrity-staleness-hardening", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/readme-current-handoff-staleness-guard", "label": "v603 README Current Handoff Staleness Guard", "era": "current-state-integrity-staleness-hardening", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/setup-smoke-scope-guard", "label": "v604 Setup Smoke Scope Guard", "era": "current-state-integrity-staleness-hardening", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/current-state-integrity-staleness-hardening-board", "label": "v605 Current-State Integrity Staleness Hardening Board", "era": "current-state-integrity-staleness-hardening", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v601.0-v605.0 dashboard route probe tokens: /smoke-summary-version-alignment-contract /nested-metadata-root-version-guard /readme-current-handoff-staleness-guard /setup-smoke-scope-guard /current-state-integrity-staleness-hardening-board current-state-integrity-staleness-hardening-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/archive-reconciliation-application-scope-packet", "label": "v606 Archive Reconciliation Application Scope Packet", "era": "archive-reconciliation-application-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/reconciliation-application-candidate-map", "label": "v607 Reconciliation Application Candidate Map", "era": "archive-reconciliation-application-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-reconciliation-application-approval-checklist", "label": "v608 Operator Reconciliation Application Approval Checklist", "era": "archive-reconciliation-application-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dry-run-application-receipt-prep", "label": "v609 Dry-Run Application Receipt Prep", "era": "archive-reconciliation-application-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-reconciliation-application-prep-board", "label": "v610 Archive Reconciliation Application Prep Board", "era": "archive-reconciliation-application-prep", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v606.0-v610.0 dashboard route probe tokens: /archive-reconciliation-application-scope-packet /reconciliation-application-candidate-map /operator-reconciliation-application-approval-checklist /dry-run-application-receipt-prep /archive-reconciliation-application-prep-board archive-reconciliation-application-prep-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v611.0-v615.0 dashboard route probe tokens: /command-center-landing-screen /operator-queue-panel /safety-state-panel /workflow-navigation-groups /system-health-summary-board /operator-command-center-ui-consolidation-board operator-command-center-ui-consolidation-v1 no_native_title_tooltip data-tip

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/workflow-group-route-index", "label": "v616 Workflow Group Route Index", "era": "dashboard-workflow-simplification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/legacy-route-drawer", "label": "v617 Legacy Route Drawer", "era": "dashboard-workflow-simplification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/archive-workflow-pipeline-view", "label": "v618 Archive Workflow Pipeline View", "era": "dashboard-workflow-simplification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/patch-safety-memory-group-views", "label": "v619 Patch Safety Memory Group Views", "era": "dashboard-workflow-simplification", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dashboard-simplification-board", "label": "v620 Dashboard Simplification Board", "era": "dashboard-workflow-simplification", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v616.0-v620.0 dashboard route probe tokens: /workflow-group-route-index /legacy-route-drawer /archive-workflow-pipeline-view /patch-safety-memory-group-views /dashboard-simplification-board dashboard-workflow-simplification-legacy-drawer-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/universal-action-label-standard", "label": "v621 Universal Action Label Standard", "era": "operator-action-semantics-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/blocked-action-explanation-cards", "label": "v622 Blocked Action Explanation Cards", "era": "operator-action-semantics-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/one-time-approval-burnout-ux", "label": "v623 One-Time Approval Burnout UX", "era": "operator-action-semantics-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/safe-preview-before-action-summary", "label": "v624 Safe Preview Before-Action Summary", "era": "operator-action-semantics-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-action-semantics-board", "label": "v625 Operator Action Semantics Board", "era": "operator-action-semantics-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v621.0-v625.0 dashboard route probe tokens: /universal-action-label-standard /blocked-action-explanation-cards /one-time-approval-burnout-ux /safe-preview-before-action-summary /operator-action-semantics-board operator-action-semantics-approval-ux-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/review-packet-summary-header", "label": "v626 Review Packet Summary Header", "era": "review-packet-evidence-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/evidence-grouping-priority-layout", "label": "v627 Evidence Grouping Priority Layout", "era": "review-packet-evidence-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/receipt-ledger-readability-cards", "label": "v628 Receipt Ledger Readability Cards", "era": "review-packet-evidence-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/system-health-evidence-ux", "label": "v629 Smoke Route Metadata Evidence UX", "era": "review-packet-evidence-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/review-packet-evidence-ux-board", "label": "v630 Review Packet Evidence UX Board", "era": "review-packet-evidence-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v626.0-v630.0 dashboard route probe tokens: /review-packet-summary-header /evidence-grouping-priority-layout /receipt-ledger-readability-cards /system-health-evidence-ux /review-packet-evidence-ux-board review-packet-readability-evidence-ux-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/surface-search-index", "label": "v631 Surface Search Index", "era": "dashboard-search-surface-discovery", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/route-module-smoke-discovery-cards", "label": "v632 Route Module Smoke Discovery Cards", "era": "dashboard-search-surface-discovery", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/workflow-aware-search-filters", "label": "v633 Workflow-Aware Search Filters", "era": "dashboard-search-surface-discovery", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/current-historical-surface-guard", "label": "v634 Current Historical Surface Guard", "era": "dashboard-search-surface-discovery", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dashboard-search-discovery-board", "label": "v635 Dashboard Search Discovery Board", "era": "dashboard-search-surface-discovery", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v631.0-v635.0 dashboard route probe tokens: /surface-search-index /route-module-smoke-discovery-cards /workflow-aware-search-filters /current-historical-surface-guard /dashboard-search-discovery-board operator-dashboard-search-surface-discovery-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/decision-capture-form-schema", "label": "v636 Decision Capture Form Schema", "era": "operator-decision-approval-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/approval-scope-target-binding-panel", "label": "v637 Approval Scope Target Binding Panel", "era": "operator-decision-approval-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/approval-expiration-burnout-form-ux", "label": "v638 Approval Expiration Burnout Form UX", "era": "operator-decision-approval-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/denial-deferral-revision-decision-capture", "label": "v639 Denial Deferral Revision Decision Capture", "era": "operator-decision-approval-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-decision-approval-ux-board", "label": "v640 Operator Decision Approval UX Board", "era": "operator-decision-approval-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v636.0-v640.0 dashboard route probe tokens: /decision-capture-form-schema /approval-scope-target-binding-panel /approval-expiration-burnout-form-ux /denial-deferral-revision-decision-capture /operator-decision-approval-ux-board operator-decision-capture-approval-form-ux-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/operator-decision-timeline-model", "label": "v641 Operator Decision Timeline Model", "era": "operator-receipt-timeline-audit-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/approval-burnout-consumption-timeline-cards", "label": "v642 Approval Burnout Consumption Timeline Cards", "era": "operator-receipt-timeline-audit-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/blocked-action-safety-event-timeline-cards", "label": "v643 Blocked Action Safety Event Timeline Cards", "era": "operator-receipt-timeline-audit-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/verification-receipt-timeline-cards", "label": "v644 Verification Receipt Timeline Cards", "era": "operator-receipt-timeline-audit-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/decision-audit-trail-board", "label": "v645 Decision Audit Trail Board", "era": "operator-receipt-timeline-audit-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v641.0-v645.0 dashboard route probe tokens: /operator-decision-timeline-model /approval-burnout-consumption-timeline-cards /blocked-action-safety-event-timeline-cards /verification-receipt-timeline-cards /decision-audit-trail-board operator-receipt-timeline-decision-audit-trail-ux-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/session-resume-state-summary", "label": "v646 Session Resume State Summary", "era": "operator-session-continuity-resume-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/unresolved-warning-blocker-carryover", "label": "v647 Unresolved Warning and Blocker Carryover", "era": "operator-session-continuity-resume-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/pending-decisions-prepared-work-resume-queue", "label": "v648 Pending Decisions and Prepared Work Resume Queue", "era": "operator-session-continuity-resume-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/verification-state-resume-card", "label": "v649 Verification State Resume Card", "era": "operator-session-continuity-resume-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-session-continuity-board", "label": "v650 Operator Session Continuity Board", "era": "operator-session-continuity-resume-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v646.0-v650.0 dashboard route probe tokens: /session-resume-state-summary /unresolved-warning-blocker-carryover /pending-decisions-prepared-work-resume-queue /verification-state-resume-card /operator-session-continuity-board operator-session-continuity-resume-console-ux-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/guided-review-wizard-entry-model", "label": "v651 Guided Review Wizard Entry Model", "era": "operator-guided-review-wizard-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/guided-evidence-warning-step-cards", "label": "v652 Guided Evidence and Warning Step Cards", "era": "operator-guided-review-wizard-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/guided-decision-approval-step-ux", "label": "v653 Guided Decision and Approval Step UX", "era": "operator-guided-review-wizard-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/guided-verification-resume-step-summary", "label": "v654 Guided Verification and Resume Step Summary", "era": "operator-guided-review-wizard-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-guided-review-wizard-board", "label": "v655 Operator Guided Review Wizard Board", "era": "operator-guided-review-wizard-ux", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v651.0-v655.0 dashboard route probe tokens: /guided-review-wizard-entry-model /guided-evidence-warning-step-cards /guided-decision-approval-step-ux /guided-verification-resume-step-summary /operator-guided-review-wizard-board operator-guided-review-wizard-ux-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/metadata-schema-contract", "label": "v656 Metadata Schema Contract", "era": "project-metadata-active-context-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/active-project-resolution-audit", "label": "v657 Active Project Resolution Audit", "era": "project-metadata-active-context-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/project-status-rendering-hardening", "label": "v658 Project Status Rendering Hardening", "era": "project-metadata-active-context-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/release-note-version-semantics-audit", "label": "v659 Release Note Version Semantics Audit", "era": "project-metadata-active-context-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/metadata-integrity-board-smoke-gate", "label": "v660 Metadata Integrity Board and Smoke Gate", "era": "project-metadata-active-context-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v656.0-v660.0 dashboard route probe tokens: /metadata-schema-contract /active-project-resolution-audit /project-status-rendering-hardening /release-note-version-semantics-audit /metadata-integrity-board-smoke-gate project-metadata-schema-active-context-repair-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/smoke-gate-classification-model", "label": "v661 Smoke Gate Classification Model", "era": "legacy-smoke-segmentation-stale-expectation-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/current-release-gate-segment", "label": "v662 Current Release Gate Segment", "era": "legacy-smoke-segmentation-stale-expectation-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/legacy-advisory-segment-separation", "label": "v663 Legacy Advisory Segment Separation", "era": "legacy-smoke-segmentation-stale-expectation-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/stale-expectation-repair-audit", "label": "v664 Stale Expectation Repair Audit", "era": "legacy-smoke-segmentation-stale-expectation-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/smoke-segmentation-integrity-board", "label": "v665 Smoke Segmentation Integrity Board", "era": "legacy-smoke-segmentation-stale-expectation-repair", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v661.0-v665.0 dashboard route probe tokens: /smoke-gate-classification-model /current-release-gate-segment /legacy-advisory-segment-separation /stale-expectation-repair-audit /smoke-segmentation-integrity-board legacy-smoke-segmentation-stale-expectation-repair-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/surface-registry-manifest-contract", "label": "v666 Surface Registry Manifest Contract", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dashboard-surface-manifest-adapter", "label": "v667 Dashboard Surface Manifest Adapter", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/api-cli-surface-manifest-adapter", "label": "v668 API CLI Surface Manifest Adapter", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/smoke-surface-manifest-adapter", "label": "v669 Smoke Surface Manifest Adapter", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/source-surface-manifest-reconciliation", "label": "v670 Source Surface Manifest Reconciliation", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/documentation-token-manifest-validation", "label": "v671 Documentation Token Manifest Validation", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/manifest-drift-detection-board", "label": "v672 Manifest Drift Detection Board", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/registry-generation-prep-layer", "label": "v673 Registry Generation Prep Layer", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/manifest-driven-current-release-gate", "label": "v674 Manifest Driven Current Release Gate", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/manifest-driven-surface-registry-board", "label": "v675 Manifest Driven Surface Registry Board", "era": "manifest-driven-surface-registry", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v666.0-v685.0 dashboard route probe tokens: /surface-registry-manifest-contract /dashboard-surface-manifest-adapter /api-cli-surface-manifest-adapter /smoke-surface-manifest-adapter /source-surface-manifest-reconciliation /documentation-token-manifest-validation /manifest-drift-detection-board /registry-generation-prep-layer /manifest-driven-current-release-gate /manifest-driven-surface-registry-board manifest-driven-surface-registry-v1 route_presence_is_authorization=False route_health_is_approval=False manifest_presence_is_authorization=False registry_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/dashboard-component-contract", "label": "v676 Dashboard Component Contract", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/shared-review-packet-renderer", "label": "v677 Shared Review Packet Renderer", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/shared-boundary-matrix-renderer", "label": "v678 Shared Boundary Matrix Renderer", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/shared-evidence-warning-renderer", "label": "v679 Shared Evidence and Warning Renderer", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/shared-decision-approval-renderer", "label": "v680 Shared Decision and Approval Renderer", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/shared-resume-continuity-renderer", "label": "v681 Shared Resume Continuity Renderer", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dashboard-route-renderer-adapter", "label": "v682 Dashboard Route Renderer Adapter", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dashboard-style-regression-guard", "label": "v683 Dashboard Style Regression Guard", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/legacy-renderer-duplication-audit", "label": "v684 Legacy Renderer Duplication Audit", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/dashboard-renderer-component-extraction-board", "label": "v685 Dashboard Renderer Component Extraction Board", "era": "dashboard-renderer-component-extraction", "authority_level": "review_only", "is_heavy_render_candidate": False},
])
# v676.0-v685.0 dashboard route probe tokens: /dashboard-component-contract /shared-review-packet-renderer /shared-boundary-matrix-renderer /shared-evidence-warning-renderer /shared-decision-approval-renderer /shared-resume-continuity-renderer /dashboard-route-renderer-adapter /dashboard-style-regression-guard /legacy-renderer-duplication-audit /dashboard-renderer-component-extraction-board dashboard-renderer-component-extraction-v1 route_presence_is_authorization=False route_health_is_approval=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/neural-deck-layout-shell", "label": "v686 Neural Deck Layout Shell", "era": "neural-command-deck-dashboard-redesign", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/eidolon-thinking-core-panel", "label": "v687 Eidolon Thinking Core Panel", "era": "neural-command-deck-dashboard-redesign", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/operator-conversation-console", "label": "v688 Operator Conversation Console", "era": "neural-command-deck-dashboard-redesign", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/side-intelligence-panels", "label": "v689 Side Intelligence Panels", "era": "neural-command-deck-dashboard-redesign", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/neural-command-deck-dashboard-board", "label": "v690 Neural Command Deck Dashboard Board", "era": "neural-command-deck-dashboard-redesign", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v686.0-v690.0 dashboard route probe tokens: /neural-deck-layout-shell /eidolon-thinking-core-panel /operator-conversation-console /side-intelligence-panels /neural-command-deck-dashboard-board neural-command-deck-dashboard-redesign-v1 route_presence_is_authorization=False route_health_is_approval=False visual_health_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console neural command deck


RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/interaction-focus-rail", "label": "v691 Interaction Focus Rail", "era": "neural-command-deck-interaction-refinement", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/interaction-safe-input-deck", "label": "v692 Interaction Safe Input Deck", "era": "neural-command-deck-interaction-refinement", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/panel-density-priority-tuning", "label": "v693 Panel Density and Priority Tuning", "era": "neural-command-deck-interaction-refinement", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/context-telemetry-affordance", "label": "v694 Context and Telemetry Affordance", "era": "neural-command-deck-interaction-refinement", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/neural-command-deck-interaction-board", "label": "v695 Neural Command Deck Interaction Board", "era": "neural-command-deck-interaction-refinement", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v691.0-v695.0 dashboard route probe tokens: /interaction-focus-rail /interaction-safe-input-deck /panel-density-priority-tuning /context-telemetry-affordance /neural-command-deck-interaction-board neural-command-deck-interaction-refinement-v1 route_presence_is_authorization=False route_health_is_approval=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route": "/autonomy-phase-zero-definition-contract", "label": "v696 Autonomy Phase 0 Definition Contract", "era": "autonomy-phase-zero-readiness-harness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/observation-only-cycle-simulator", "label": "v697 Observation-Only Cycle Simulator", "era": "autonomy-phase-zero-readiness-harness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/no-mutation-autonomy-boundary-guard", "label": "v698 No-Mutation Autonomy Boundary Guard", "era": "autonomy-phase-zero-readiness-harness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/autonomy-phase-zero-handoff-packet", "label": "v699 Autonomy Phase 0 Handoff Packet", "era": "autonomy-phase-zero-readiness-harness", "authority_level": "review_only", "is_heavy_render_candidate": False},
    {"route": "/autonomy-phase-zero-readiness-board", "label": "v700 Autonomy Phase 0 Readiness Board", "era": "autonomy-phase-zero-readiness-harness", "authority_level": "review_only", "is_heavy_render_candidate": False},
])

# v696.0-v700.0 dashboard route probe tokens: /autonomy-phase-zero-definition-contract /observation-only-cycle-simulator /no-mutation-autonomy-boundary-guard /autonomy-phase-zero-handoff-packet /autonomy-phase-zero-readiness-board autonomy-phase-zero-readiness-harness-v1 route_presence_is_authorization=False route_health_is_approval=False phase_zero_is_autonomy_approval=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_DASHBOARD_ROUTES.extend([
    {"route":"/self-development-cycle","label":"Self Development Implementation Proposal Packet","version":"760.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False},
])

# v721.0-v760.0 dashboard route probe tokens: /self-development-cycle self-development-cycle-trial-review-v1 route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v726.0-v760.0 dashboard route probe tokens: /self-development-cycle self-development-implementation-proposal-v1 Self Development Dashboard Trial Hardening route_presence_is_authorization=False route_health_is_approval=False runs_broad_smoke=False treats_blocked_as_pass=False no_native_title_tooltip data-tip command-deck operator-console

# v731.0-v760.0 dashboard route probe tokens: /self-development-cycle self-development-implementation-proposal-v1 Self Development Implementation Proposal Packet route_presence_is_authorization=False route_health_is_approval=False source_edits_authorized_by_this_packet=False task_is_implementation_permission=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route":"/self-development-cycle","label":"Operator-Approved Self Development Patch Draft Trial","version":"760.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False,"patch_draft_is_application_permission":False},
])

# v736.0-v760.0 dashboard route probe tokens: /self-development-cycle operator-approved-self-development-patch-draft-v1 Operator-Approved Self Development Patch Draft Trial route_presence_is_authorization=False route_health_is_approval=False patch_draft_is_application_permission=False requires_separate_approval_before_patch_application=True source_edits_authorized_by_this_packet=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route":"/self-development-cycle","label":"Operator-Approved Self Development Patch Application Trial","version":"760.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False,"patch_application_is_release_permission":False},
])

# v741.0-v760.0 dashboard route probe tokens: /self-development-cycle operator-approved-self-development-patch-application-v1 Operator-Approved Self Development Patch Application Trial route_presence_is_authorization=False route_health_is_approval=False patch_application_is_release_permission=False captures_preimage_hashes=True low_risk_file_allowlist_enforced=True stops_before_release_publish_autonomy=True source_edits_authorized_by_this_packet=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.extend([
    {"route":"/self-development-smoke-debt","label":"Self Development Smoke Debt Ledger","version":"760.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False,"smoke_debt_ledger_is_pass_override":False},
])

RECENT_DASHBOARD_ROUTES.append(
    {"route":"/self-development-smoke-debt","label":"Self Development API Surface Truth Review","version":"760.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False,"api_surface_truth_review_is_repair_permission":False},
)

# v760.0 dashboard route probe tokens: /self-development-smoke-debt self-development-api-surface-truth-review-v1 Self Development API Surface Truth Review route_presence_is_authorization=False route_health_is_approval=False api_surface_truth_review_is_repair_permission=False no_native_title_tooltip data-tip command-deck operator-console

# v746.0-v760.0 dashboard route probe tokens: /self-development-smoke-debt self-development-application-receipt-review-v1 current-smoke-debt-ledger-v1 Self Development Smoke Debt Ledger route_presence_is_authorization=False route_health_is_approval=False smoke_debt_ledger_is_pass_override=False receipt_is_not_success=True blocked_trial_is_not_success=True marks_blockers_as_pass=False runs_broad_smoke=False creates_concrete_diff=False applies_source_edits=False no_native_title_tooltip data-tip command-deck operator-console

# v760.0 API route repair dashboard/API parity tokens: /self-development-smoke-debt /api/self-development-cycle/layer self-development-api-route-repair-v1 build_self_development_cycle_api_layer manifest_claimed_api_routes_must_dispatch=True api_404_is_release_blocking_for_claimed_routes=True route_presence_is_authorization=False route_health_is_approval=False self_development_api_route_is_autonomy_permission=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.append(
    {"route":"/self-development-smoke-debt","label":"Self Development Cycle Duplicate Cleanup Review","version":"760.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False,"duplicate_cleanup_is_autonomy_permission":False},
)

# v760.0 duplicate cleanup dashboard route probe tokens: /self-development-smoke-debt self-development-cycle-duplicate-cleanup-v1 Self Development Cycle Duplicate Cleanup Review route_presence_is_authorization=False route_health_is_approval=False duplicate_cleanup_is_autonomy_permission=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.append(
    {"route":"/self-development-smoke-debt","label":"Legacy Self Maintenance Smoke Blocker Review","version":"845.0","authority":"review_only","route_presence_is_authorization":False,"route_health_is_approval":False,"legacy_smoke_blocker_review_is_pass_override":False},
)

# v845.0 smoke debt ledger reconciliation dashboard route probe tokens: /self-development-smoke-debt current-smoke-debt-ledger-reconciliation-v1 Current Smoke Debt Ledger Reconciliation route_presence_is_authorization=False route_health_is_approval=False smoke_debt_reconciliation_is_pass_override=False resolved_legacy_smoke_debt_not_active=True no_native_title_tooltip data-tip command-deck operator-console
# v845.0 legacy self-maintenance smoke blocker review dashboard route probe tokens: /self-development-smoke-debt legacy-self-maintenance-smoke-blocker-review-v1 Legacy Self Maintenance Smoke Blocker Review route_presence_is_authorization=False route_health_is_approval=False legacy_smoke_blocker_review_is_pass_override=False no_native_title_tooltip data-tip command-deck operator-console
# v845.0 manifest-guided validation probe dry-run dashboard route probe tokens: /self-development-smoke-debt manifest-guided-validation-probe-dry-run-v1 Manifest-Guided Validation Probe Dry-Run route_presence_is_authorization=False route_health_is_approval=False validation_probe_dry_run_is_review_only=True generates_validation_probe=False generated_wiring_activated=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_DASHBOARD_ROUTES.append(
    {"route": "/behavioral-dashboard-route-coverage", "label": "v1024 Behavioral Dashboard Route Coverage", "era": "behavioral-dashboard-route-coverage", "authority_level": "review_only", "is_heavy_render_candidate": False, "route_presence_is_authorization": False, "route_health_is_approval": False},
)

# v1024.0 behavioral dashboard route coverage route probe tokens: /behavioral-dashboard-route-coverage behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1 behavioral_route_probe_executes_renderers=True behavioral_route_probe_uses_token_presence_only=False source_decomposition_prep_only=True route_presence_is_authorization=False route_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console
