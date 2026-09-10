from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from self_maintenance_governance_gates import (
    GOVERNANCE_GATE_BOUNDARIES,
    SELF_MAINTENANCE_GOVERNANCE_GATES_VERSION,
    governance_gate_tokens,
    summarize_governance_gates,
)
from self_maintenance_surface_gates import (
    SELF_MAINTENANCE_SURFACE_GATES_VERSION,
    SURFACE_GATE_BOUNDARIES,
    summarize_surface_gates,
    surface_gate_tokens,
)
from self_maintenance_version_package_gates import (
    SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION,
    VERSION_PACKAGE_GATE_BOUNDARIES,
    summarize_version_package_gates,
    version_package_gate_tokens,
)

SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION = RUNTIME_VERSION
SELF_MAINTENANCE_MODULAR_EXTRACTION_BOUNDARIES: dict[str, bool] = {
    "modular_extraction_applies_live_patches": False,
    "modular_extraction_changes_expression_behavior": False,
    "modular_extraction_mutates_memory": False,
    "modular_extraction_alters_identity": False,
    "modular_extraction_alters_personality": False,
    "modular_extraction_invokes_models": False,
    "modular_extraction_self_approves": False,
    "modular_extraction_publishes_release": False,
    "modular_extraction_creates_release_candidate": False,
    "modular_extraction_continues_automatically": False,
    "modular_extraction_review_only": True,
    "version_package_gate_extraction_present": True,
    "surface_gate_extraction_present": True,
    "governance_gate_extraction_present": True,
    "dashboard_data_tip_required": True,
    "native_title_tooltips_forbidden": True,
}

EXTRACTION_FAMILIES = [
    "version expectations",
    "route/API/CLI readiness checks",
    "package privacy checks",
    "dashboard hover checks",
    "governance boundary checks",
    "legacy gate compatibility checks",
    "expression-layer audit checks",
    "minimal live-change replay checks",
]

MODULE_SURFACES = [
    {"dashboard": "/self-maintenance-module-extraction-plan", "api": "/api/self-maintenance-module-extraction-plan/layer", "cli": "--operator-governed-self-maintenance-module-extraction-plan-v1"},
    {"dashboard": "/self-maintenance-version-package-gates", "api": "/api/self-maintenance-version-package-gates/layer", "cli": "--operator-governed-self-maintenance-version-package-gate-extraction-v1"},
    {"dashboard": "/self-maintenance-surface-gates", "api": "/api/self-maintenance-surface-gates/layer", "cli": "--operator-governed-self-maintenance-surface-gate-extraction-v1"},
    {"dashboard": "/self-maintenance-governance-gates", "api": "/api/self-maintenance-governance-gates/layer", "cli": "--operator-governed-self-maintenance-governance-gate-extraction-v1"},
    {"dashboard": "/self-maintenance-modular-extraction-audit", "api": "/api/self-maintenance-modular-extraction-audit/layer", "cli": "--operator-governed-self-maintenance-modular-extraction-v1"},
]

def _boundaries_ok() -> bool:
    false_ok = all(value is False for key, value in SELF_MAINTENANCE_MODULAR_EXTRACTION_BOUNDARIES.items() if key.startswith("modular_extraction_") and key != "modular_extraction_review_only")
    true_keys = [
        "modular_extraction_review_only",
        "version_package_gate_extraction_present",
        "surface_gate_extraction_present",
        "governance_gate_extraction_present",
        "dashboard_data_tip_required",
        "native_title_tooltips_forbidden",
    ]
    return false_ok and all(SELF_MAINTENANCE_MODULAR_EXTRACTION_BOUNDARIES.get(key) is True for key in true_keys)

def build_module_extraction_plan_summary() -> dict[str, Any]:
    return {
        "version": SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION,
        "state": "self_maintenance_module_extraction_plan",
        "extractable_families": list(EXTRACTION_FAMILIES),
        "safe_first_modules": [
            "self_maintenance_version_package_gates.py",
            "self_maintenance_surface_gates.py",
            "self_maintenance_governance_gates.py",
        ],
        "writes_files": False,
        "moves_logic_automatically": False,
        "changes_behavior": False,
        "ok": True,
    }

def build_version_package_gate_extraction_summary(root: Path | None = None, expected_version: str = SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION) -> dict[str, Any]:
    summary = summarize_version_package_gates(root, expected_version)
    summary.update({
        "extracted_module": "self_maintenance_version_package_gates.py",
        "extracted_tokens": version_package_gate_tokens(),
        "module_version": SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION,
        "boundaries": dict(VERSION_PACKAGE_GATE_BOUNDARIES),
    })
    return summary

def build_surface_gate_extraction_summary(surfaces: list[dict[str, str]] | None = None) -> dict[str, Any]:
    summary = summarize_surface_gates(surfaces or MODULE_SURFACES)
    summary.update({
        "extracted_module": "self_maintenance_surface_gates.py",
        "extracted_tokens": surface_gate_tokens(),
        "module_version": SELF_MAINTENANCE_SURFACE_GATES_VERSION,
        "boundaries": dict(SURFACE_GATE_BOUNDARIES),
    })
    return summary

def build_governance_gate_extraction_summary() -> dict[str, Any]:
    summary = summarize_governance_gates()
    summary.update({
        "extracted_module": "self_maintenance_governance_gates.py",
        "extracted_tokens": governance_gate_tokens(),
        "module_version": SELF_MAINTENANCE_GOVERNANCE_GATES_VERSION,
        "boundaries": dict(GOVERNANCE_GATE_BOUNDARIES),
    })
    return summary

def build_modular_extraction_audit_summary(root: Path | None = None, docs_text: str = "", expected_version: str = SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION) -> dict[str, Any]:
    plan = build_module_extraction_plan_summary()
    version_package = build_version_package_gate_extraction_summary(root, expected_version)
    surface = build_surface_gate_extraction_summary(MODULE_SURFACES)
    governance = build_governance_gate_extraction_summary()
    required_tokens = [
        "self_maintenance_version_package_gates.py",
        "self_maintenance_surface_gates.py",
        "self_maintenance_governance_gates.py",
        "operator-governed-self-maintenance-modular-extraction-v1",
        "data-tip",
        "no_native_title_tooltip",
    ]
    docs_ok = all(token in docs_text for token in required_tokens) if docs_text else True
    ok = _boundaries_ok() and bool(plan.get("ok")) and bool(version_package.get("ok")) and bool(surface.get("ok")) and bool(governance.get("ok")) and docs_ok
    return {
        "version": SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION,
        "state": "self_maintenance_modular_extraction_audit",
        "module_extraction_plan": plan,
        "version_package_gates": version_package,
        "surface_gates": surface,
        "governance_gates": governance,
        "module_versions": {
            "version_package": SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION,
            "surface": SELF_MAINTENANCE_SURFACE_GATES_VERSION,
            "governance": SELF_MAINTENANCE_GOVERNANCE_GATES_VERSION,
        },
        "boundaries": dict(SELF_MAINTENANCE_MODULAR_EXTRACTION_BOUNDARIES),
        "boundaries_ok": _boundaries_ok(),
        "docs_ok": docs_ok,
        "ok": ok,
        "safe_next_action": "Operator may review modular extraction results. No live expression behavior change, autonomy expansion, source application, memory mutation, identity/personality mutation, local model invocation, release creation, or automatic continuation is authorized.",
    }

def render_self_maintenance_modular_extraction_lines(summary: dict[str, Any]) -> list[str]:
    return [
        f"- version: {summary.get('version')}",
        f"- state: {summary.get('state')}",
        f"- ok: {summary.get('ok', summary.get('boundaries_ok', 'review-only'))}",
        f"- writes_files: {summary.get('writes_files', False)}",
        f"- changes_behavior: {summary.get('changes_behavior', False)}",
        f"- extracted_module: {summary.get('extracted_module', 'n/a')}",
        f"- safe_next_action: {summary.get('safe_next_action', 'operator review only')}",
    ]
