from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass, asdict
from typing import Any

RUNTIME_REGISTRY_VERSION = RUNTIME_VERSION
MODULE_EXTRACTION_BOUNDARIES: dict[str, bool] = {
    "module_extraction_writes_files_automatically": False,
    "module_extraction_removes_routes": False,
    "module_extraction_changes_dashboard_behavior": False,
    "module_extraction_rewrites_architecture_aggressively": False,
    "module_extraction_inferrs_approval_from_success": False,
    "module_extraction_invokes_models_by_default": False,
    "module_extraction_runs_verification_automatically": False,
    "module_extraction_self_approves": False,
    "module_extraction_mutates_memory": False,
    "module_extraction_alters_identity": False,
    "module_extraction_publishes_releases": False,
    "module_extraction_continues_automatically": False,
    "legacy_wrappers_required": True,
    "existing_routes_preserved": True,
    "dashboard_data_tip_required": True,
    "native_nav_title_tooltips_forbidden": True,
    "package_privacy_required": True,
    "operator_approval_required_for_deeper_refactor": True,
}

@dataclass(frozen=True)
class RuntimeRegistryEntry:
    version: str
    slug: str
    label: str
    api: str
    dashboard: str
    runtime_key: str
    theme: str
    route: str
    focus: str
    is_final: bool = False

    @property
    def cli_flag(self) -> str:
        return "--" + self.slug.replace("_", "-")

    @property
    def api_route(self) -> str:
        return f"/api/{self.api}/{self.route}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["cli_flag"] = self.cli_flag
        data["api_route"] = self.api_route
        return data

MODULE_EXTRACTION_ARCS: list[dict[str, Any]] = [
    {
        "version": "v266.0",
        "final_label": "Operator-Governed Runtime Metadata Registry Extraction",
        "api": "runtime-registry",
        "dashboard": "/runtime-registry",
        "runtime_key": "runtime_registry",
        "theme": "runtime metadata registry extraction",
        "items": [
            ("v265.1", "runtime_registry_module_scaffold", "Runtime Registry Module Scaffold", "Create conscious_agent/runtime_registry.py as a source-only metadata helper without replacing dispatch.", "scaffold"),
            ("v265.2", "capability_metadata_extraction", "Capability Metadata Extraction", "Move reusable capability metadata descriptions into the registry helper while preserving live definitions.", "capability"),
            ("v265.3", "dashboard_route_metadata_extraction", "Dashboard Route Metadata Extraction", "Expose dashboard route metadata through the registry helper without removing dashboard handlers.", "dashboard"),
            ("v265.4", "cli_surface_metadata_extraction", "CLI Surface Metadata Extraction", "Expose CLI flag metadata through the registry helper without changing CLI dispatch.", "cli"),
            ("v265.5", "api_surface_metadata_extraction", "API Surface Metadata Extraction", "Expose API route metadata through the registry helper without changing API routing.", "api"),
            ("v265.6", "safety_boundary_metadata_extraction", "Safety Boundary Metadata Extraction", "Move reusable no-autonomy boundary metadata into the registry helper.", "safety"),
            ("v265.7", "registry_compatibility_adapter", "Registry Compatibility Adapter", "Provide adapter helpers so existing runtime maps can consume registry rows without behavior changes.", "adapter"),
            ("v265.8", "registry_smoke_coverage_hook", "Registry Smoke Coverage Hook", "Expose registry tokens and parity checks for smoke coverage without running commands.", "smoke"),
            ("v265.9", "pre_v266_no_behavior_change_audit", "No-Behavior-Change Audit", "Confirm registry extraction preserves routes, commands, API, docs, packaging, and authority boundaries.", "gate"),
            ("v266.0", "operator_governed_runtime_metadata_registry_extraction", "Operator-Governed Runtime Metadata Registry Extraction", "Finalize runtime metadata registry extraction.", "layer", True),
        ],
    },
    {
        "version": "v267.0",
        "final_label": "Operator-Governed Governance Report Builder Extraction",
        "api": "governance-report-builder-audit",
        "dashboard": "/governance-report-builder-audit",
        "runtime_key": "governance_report_builder_audit",
        "theme": "governance report builder extraction",
        "items": [
            ("v266.1", "governance_report_module_scaffold", "Governance Report Module Scaffold", "Create conscious_agent/governance_reports.py for reusable report rendering helpers.", "scaffold"),
            ("v266.2", "packet_summary_renderer_extraction", "Packet Summary Renderer Extraction", "Move reusable packet summary rendering into governance_reports.py.", "packet"),
            ("v266.3", "safety_finding_renderer_extraction", "Safety Finding Renderer Extraction", "Move reusable safety finding rendering into governance_reports.py.", "safety"),
            ("v266.4", "approval_boundary_renderer_extraction", "Approval Boundary Renderer Extraction", "Move reusable approval boundary rendering into governance_reports.py.", "approval"),
            ("v266.5", "verification_rollback_renderer_extraction", "Verification/Rollback Renderer Extraction", "Move reusable verification and rollback rendering helpers into governance_reports.py.", "verify"),
            ("v266.6", "audit_finding_renderer_extraction", "Audit Finding Renderer Extraction", "Move reusable audit finding rendering into governance_reports.py.", "audit"),
            ("v266.7", "backward_compatible_function_wrappers", "Backward-Compatible Function Wrappers", "Keep existing self_maintenance report function wrappers stable.", "wrappers"),
            ("v266.8", "report_output_parity_check", "Report Output Parity Check", "Compare extracted helper output to expected legacy text shape without changing authority.", "parity"),
            ("v266.9", "pre_v267_no_authority_change_audit", "No-Authority-Change Audit", "Confirm report extraction cannot approve, execute, mutate, or publish.", "gate"),
            ("v267.0", "operator_governed_governance_report_builder_extraction", "Operator-Governed Governance Report Builder Extraction", "Finalize governance report builder extraction.", "layer", True),
        ],
    },
    {
        "version": "v268.0",
        "final_label": "Operator-Governed Dashboard Surface Registry Integration",
        "api": "dashboard-registry-integration",
        "dashboard": "/dashboard-registry-integration",
        "runtime_key": "dashboard_registry_integration",
        "theme": "dashboard surface registry integration",
        "items": [
            ("v267.1", "dashboard_registry_adapter", "Dashboard Registry Adapter", "Read review-only dashboard metadata from runtime_registry.py while preserving handlers.", "adapter"),
            ("v267.2", "navigation_metadata_binder", "Navigation Metadata Binder", "Bind nav labels, descriptions, and categories from registry metadata for parity review.", "nav"),
            ("v267.3", "route_label_normalizer", "Route Label Normalizer", "Normalize route labels and audit consistency without changing routes.", "label"),
            ("v267.4", "data_tip_tooltip_binder", "data-tip Tooltip Binder", "Bind tooltip metadata while preserving custom data-tip hover behavior.", "tooltip"),
            ("v267.5", "native_title_regression_guard", "Native title Regression Guard", "Keep native nav title tooltip regressions blocked.", "regression"),
            ("v267.6", "command_deck_style_preservation_check", "Command Deck Style Preservation Check", "Preserve the v135 command-deck/operator-console layout contract.", "layout"),
            ("v267.7", "dashboard_route_parity_audit", "Dashboard Route Parity Audit", "Audit dashboard registry metadata against route handlers.", "parity"),
            ("v267.8", "dashboard_smoke_coverage_update", "Dashboard Smoke Coverage Update", "Update route and tooltip smoke coverage suggestions.", "smoke"),
            ("v267.9", "pre_v268_no_visual_regression_audit", "No-Visual-Regression Audit", "Confirm registry integration does not alter visual behavior or tooltip semantics.", "gate"),
            ("v268.0", "operator_governed_dashboard_surface_registry_integration", "Operator-Governed Dashboard Surface Registry Integration", "Finalize dashboard surface registry integration.", "layer", True),
        ],
    },
    {
        "version": "v269.0",
        "final_label": "Operator-Governed CLI/API Runtime Registry Integration",
        "api": "runtime-dispatch-registry-audit",
        "dashboard": "/runtime-dispatch-registry-audit",
        "runtime_key": "runtime_dispatch_registry_audit",
        "theme": "CLI/API runtime registry integration",
        "items": [
            ("v268.1", "cli_registry_adapter", "CLI Registry Adapter", "Expose CLI metadata from runtime_registry.py while preserving current dispatch.", "cli"),
            ("v268.2", "api_registry_adapter", "API Registry Adapter", "Expose API metadata from runtime_registry.py while preserving current routing.", "api"),
            ("v268.3", "shared_command_metadata_binder", "Shared Command Metadata Binder", "Bind shared command names, labels, routes, and safety notes.", "metadata"),
            ("v268.4", "dynamic_dispatch_parity_checker", "Dynamic Dispatch Parity Checker", "Compare registry metadata against dynamic CLI/API dispatch maps.", "parity"),
            ("v268.5", "missing_cli_surface_guard", "Missing CLI Surface Guard", "Flag missing CLI coverage without adding or executing commands automatically.", "cli-guard"),
            ("v268.6", "missing_api_surface_guard", "Missing API Surface Guard", "Flag missing API coverage without altering route handlers automatically.", "api-guard"),
            ("v268.7", "route_command_name_consistency_checker", "Route/Command Name Consistency Checker", "Compare route and command naming consistency for operator review.", "names"),
            ("v268.8", "dispatch_smoke_coverage_update", "Dispatch Smoke Coverage Update", "Update dispatch smoke coverage suggestions without running checks automatically.", "smoke"),
            ("v268.9", "pre_v269_no_execution_authority_audit", "No-Execution-Authority Audit", "Confirm dispatch registry integration cannot execute, approve, publish, mutate, or continue.", "gate"),
            ("v269.0", "operator_governed_cli_api_runtime_registry_integration", "Operator-Governed CLI/API Runtime Registry Integration", "Finalize CLI/API runtime registry integration.", "layer", True),
        ],
    },
    {
        "version": "v270.0",
        "final_label": "Operator-Governed Runtime Module Extraction v1",
        "api": "module-extraction-audit",
        "dashboard": "/module-extraction-audit",
        "runtime_key": "module_extraction_audit",
        "theme": "module extraction integration audit",
        "items": [
            ("v269.1", "extracted_module_import_audit", "Extracted Module Import Audit", "Audit runtime_registry.py and governance_reports.py imports and wrapper compatibility.", "imports"),
            ("v269.2", "runtime_registry_parity_audit", "Runtime Registry Parity Audit", "Audit registry rows against supervised runtime maps.", "registry"),
            ("v269.3", "governance_report_output_parity_audit", "Governance Report Output Parity Audit", "Audit governance report helper output shape against existing text contracts.", "reports"),
            ("v269.4", "dashboard_route_parity_audit_v270", "Dashboard Route Parity Audit", "Audit dashboard nav/render/route parity after registry integration.", "dashboard"),
            ("v269.5", "cli_api_surface_parity_audit", "CLI/API Surface Parity Audit", "Audit CLI/API surface parity after registry integration.", "parity"),
            ("v269.6", "package_privacy_audit_v270", "Package Privacy Audit", "Audit source-only packaging for extracted modules and runtime directory exclusions.", "privacy"),
            ("v269.7", "readme_release_history_completeness_audit_v270", "README/Release History Completeness Audit", "Audit v270 docs coverage and release history completeness.", "docs"),
            ("v269.8", "refactor_risk_register_update", "Refactor Risk Register Update", "Update risk notes for deeper future self_maintenance decomposition.", "risk"),
            ("v269.9", "pre_v270_smoke_gate", "v270 Smoke Gate", "Confirm compile, smoke, package privacy, dashboard tooltip, route/API/CLI, and extracted ZIP verification.", "gate"),
            ("v270.0", "operator_governed_runtime_module_extraction_v1", "Operator-Governed Runtime Module Extraction v1", "Finalize runtime module extraction integration audit.", "layer", True),
        ],
    },
]

def build_module_extraction_stage_defs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arc in MODULE_EXTRACTION_ARCS:
        for item in arc["items"]:
            rows.append({
                "version": item[0],
                "slug": item[1],
                "label": item[2],
                "focus": item[3],
                "route": item[4],
                "is_final": bool(item[5]) if len(item) > 5 else False,
                "final_label": arc["final_label"],
                "api": arc["api"],
                "dashboard": arc["dashboard"],
                "runtime_key": arc["runtime_key"],
                "theme": arc["theme"],
                "stage": f"{arc['version']} {arc['final_label']}",
            })
    return rows

def build_runtime_registry_entries() -> list[dict[str, Any]]:
    """Build runtime registry rows while adapting richer stage-definition metadata."""
    allowed = set(RuntimeRegistryEntry.__dataclass_fields__)
    return [RuntimeRegistryEntry(**{key: value for key, value in row.items() if key in allowed}).to_dict() for row in build_module_extraction_stage_defs()]

def cli_map() -> dict[str, str]:
    return {row["slug"].replace("_", "-"): row["slug"] for row in build_module_extraction_stage_defs()}

def route_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in build_module_extraction_stage_defs():
        mapping[f"{row['api']}/{row['route']}"] = row["slug"]
        mapping[row["slug"].replace("_", "-")] = row["slug"]
    return mapping

def registry_summary() -> dict[str, Any]:
    rows = build_module_extraction_stage_defs()
    return {
        "version": RUNTIME_REGISTRY_VERSION,
        "stage_count": len(rows),
        "final_routes": [row["dashboard"] for row in rows if row.get("is_final")],
        "final_cli_flags": ["--" + row["slug"].replace("_", "-") for row in rows if row.get("is_final")],
        "final_api_routes": [f"/api/{row['api']}/{row['route']}" for row in rows if row.get("is_final")],
        "boundaries": MODULE_EXTRACTION_BOUNDARIES,
    }
