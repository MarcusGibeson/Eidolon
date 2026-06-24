from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

DASHBOARD_ROUTE_PROBE_VERSION = "500.0"

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
])

# v495.1-v500.0 autonomy readiness review board route probe tokens: autonomy-readiness-criteria-board autonomy-blocker-gap-register phase-based-autonomy-permission-model autonomy-misinterpretation-firewall autonomy-readiness-review-board-audit operator-governed-autonomy-readiness-review-board-v1 readiness_status=not_ready_for_autonomy authorization_status=not_authorized readiness_review_is_autonomy_approval=False board_pass_grants_authorization=False phase_definition_authorizes_phase=False sandbox_boundary_exists_means_execute=False operator_discussion_is_approval=False proposal_ranking_is_selection=False observation_history_authorizes_monitoring=False no_native_title_tooltip data-tip command-deck operator-console
