from __future__ import annotations

from pathlib import Path
from typing import Any

from version_state import VERSION_STATE_VERSION, version_marker_summary

SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION = "500.0"

SELF_MAINTENANCE_REFACTOR_BOUNDARIES: dict[str, bool] = {
    "refactor_registry_writes_files": False,
    "refactor_registry_removes_routes": False,
    "refactor_registry_changes_runtime_behavior": False,
    "refactor_registry_executes_smoke": False,
    "refactor_registry_applies_patches": False,
    "refactor_registry_mutates_memory": False,
    "refactor_registry_alters_identity": False,
    "refactor_registry_alters_personality": False,
    "refactor_registry_invokes_models": False,
    "refactor_registry_self_approves": False,
    "refactor_registry_publishes_release": False,
    "refactor_registry_continues_automatically": False,
    "registry_metadata_is_review_only": True,
    "centralized_version_expectations_required": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

GATE_FAMILIES = [
    "governance",
    "memory",
    "model",
    "expression",
    "packaging",
    "route_health",
    "smoke",
    "version_expectation",
]

GATE_REGISTRY_SEED = [
    {"family": "governance", "name": "operator approval boundary", "source": "self_maintenance.py", "status": "registered"},
    {"family": "expression", "name": "expression application no-autonomy boundary", "source": "minimal_live_expression_application.py", "status": "registered"},
    {"family": "packaging", "name": "source-only package privacy", "source": "release_packaging.py", "status": "registered"},
    {"family": "route_health", "name": "dashboard route/API/CLI parity", "source": "route_health.py", "status": "registered"},
    {"family": "smoke", "name": "targeted install smoke registry", "source": "tools/smoke_check.py", "status": "registered"},
    {"family": "version_expectation", "name": "current version marker expectations", "source": "version_state.py", "status": "registered"},
]

SURFACE_METADATA_SEED = [
    {"dashboard": "/self-maintenance-gate-registry", "api": "/api/self-maintenance-gate-registry/layer", "cli": "--operator-governed-self-maintenance-gate-inventory-registry-seed-v1"},
    {"dashboard": "/self-maintenance-version-expectations", "api": "/api/self-maintenance-version-expectations/layer", "cli": "--operator-governed-self-maintenance-version-expectation-layer-v1"},
    {"dashboard": "/governed-surface-metadata-registry", "api": "/api/governed-surface-metadata-registry/layer", "cli": "--operator-governed-surface-metadata-registry-v1"},
    {"dashboard": "/smoke-check-legacy-gate-registry", "api": "/api/smoke-check-legacy-gate-registry/layer", "cli": "--operator-governed-smoke-check-registry-and-legacy-gate-cleanup-v1"},
    {"dashboard": "/self-maintenance-refactor-audit", "api": "/api/self-maintenance-refactor-audit/layer", "cli": "--operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1"},
]

SMOKE_REGISTRY_SEED = [
    "operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1",
    "operator-approved-minimal-live-expression-application-audit-v1",
    "operator-governed-expression-live-application-execution-prep-v1",
    "operator-governed-self-maintenance-decomposition-v1",
]

def build_gate_inventory_registry_summary(root: Path | None = None) -> dict[str, Any]:
    return {
        "version": SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION,
        "state": "gate_inventory_registry_seed",
        "gate_families": list(GATE_FAMILIES),
        "registered_gates": list(GATE_REGISTRY_SEED),
        "gate_count": len(GATE_REGISTRY_SEED),
        "review_only": True,
        "writes_files": False,
        "changes_behavior": False,
    }

def build_version_expectation_registry_summary(root: Path | None = None, expected_version: str = SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    marker_summary = version_marker_summary(root, expected_version)
    return {
        "version": SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION,
        "state": "centralized_version_expectations",
        "expected_version": expected_version,
        "version_state_helper_version": VERSION_STATE_VERSION,
        "marker_summary": marker_summary,
        "stale_literal_detector_enabled": True,
        "writes_files": False,
        "ok": bool(marker_summary.get("ok")),
    }

def build_surface_metadata_registry_summary() -> dict[str, Any]:
    return {
        "version": SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION,
        "state": "governed_surface_metadata_registry",
        "surfaces": list(SURFACE_METADATA_SEED),
        "surface_count": len(SURFACE_METADATA_SEED),
        "dashboard_data_tip_required": True,
        "native_title_tooltips_forbidden": True,
        "writes_routes": False,
    }

def build_smoke_registry_summary() -> dict[str, Any]:
    return {
        "version": SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION,
        "state": "smoke_check_registry_and_legacy_gate_cleanup",
        "registered_smoke_checks": list(SMOKE_REGISTRY_SEED),
        "legacy_gate_cleanup_enabled": True,
        "executes_smoke": False,
        "writes_files": False,
    }

def build_self_maintenance_refactor_audit_summary(root: Path | None = None, expected_version: str = SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION) -> dict[str, Any]:
    gate = build_gate_inventory_registry_summary(root)
    version = build_version_expectation_registry_summary(root, expected_version)
    surface = build_surface_metadata_registry_summary()
    smoke = build_smoke_registry_summary()
    boundaries_ok = all(value is False for key, value in SELF_MAINTENANCE_REFACTOR_BOUNDARIES.items() if key.startswith("refactor_registry_"))
    required_true_ok = all(SELF_MAINTENANCE_REFACTOR_BOUNDARIES[key] is True for key in ["registry_metadata_is_review_only", "centralized_version_expectations_required", "dashboard_data_tip_required", "native_title_tooltips_forbidden"])
    return {
        "version": SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION,
        "state": "self_maintenance_surface_reduction_and_gate_registry_refactor_audit",
        "gate_inventory": gate,
        "version_expectations": version,
        "surface_metadata": surface,
        "smoke_registry": smoke,
        "boundaries": dict(SELF_MAINTENANCE_REFACTOR_BOUNDARIES),
        "boundaries_ok": boundaries_ok and required_true_ok,
        "ok": boundaries_ok and required_true_ok and version.get("ok", False),
        "safe_next_action": "Operator may review registry-driven maintenance cleanup. No behavior expansion, autonomy expansion, source apply, memory mutation, identity mutation, personality mutation, command execution, or release publishing is authorized.",
    }

def render_self_maintenance_refactor_lines(summary: dict[str, Any]) -> list[str]:
    return [
        f"- version: {summary.get('version')}",
        f"- state: {summary.get('state')}",
        f"- ok: {summary.get('ok', summary.get('boundaries_ok', 'review-only'))}",
        f"- writes_files: {summary.get('writes_files', False)}",
        f"- executes_smoke: {summary.get('executes_smoke', False)}",
        f"- changes_behavior: {summary.get('changes_behavior', False)}",
        f"- safe_next_action: {summary.get('safe_next_action', 'operator review only')}",
    ]
