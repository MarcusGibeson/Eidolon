from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SOURCE_SURFACE_MANIFEST_VERSION = "1032.0"
AUTHORITY_LEVELS = {
    "review_only",
    "simulation_only",
    "sandbox_only",
    "execution_prep_only",
    "operator_approved_single_use_trial",
    "operator_approved_sandbox_write",
    "post_execution_audit_only",
}

SOURCE_SURFACE_MANIFEST_BOUNDARIES: dict[str, bool] = {
    "manifest_presence_is_authorization": False,
    "parity_pass_is_authorization": False,
    "authority_label_is_approval": False,
    "surface_exists_means_may_execute": False,
    "smoke_pass_allows_live_action": False,
    "manifest_writes_files": False,
    "manifest_writes_memory": False,
    "manifest_expands_autonomy": False,
    "operator_review_required": True,
}

MANIFEST_VERSION_SEMANTICS = {
    "legacy_version_field": "compatibility_alias_retained_during_split",
    "surface_origin_version": "version where the represented surface originated",
    "manifest_representation_version": "current manifest schema/update version for this row",
    "last_verified_for_version": "current Eidolon release that verified the row",
}

RECENT_SURFACE_ENTRIES: list[dict[str, Any]] = [
    {
        "surface_id": "v400-memory-candidate-application-trial",
        "version": "400.0",
        "era": "memory-governance",
        "dashboard_route": "/memory-application-trial-audit",
        "api_route": "/api/memory-application-trial-audit/layer",
        "cli_flag": "--operator-governed-memory-application-trial-audit-v1",
        "builder_function": "build_operator_governed_memory_application_trial_audit_v1",
        "text_function": "operator_governed_memory_application_trial_audit_v1_text",
        "runtime_directory": "data/autonomy/memory_application_trial_audit/",
        "smoke_check": "operator-governed-memory-application-trial-audit-v1",
        "smoke_segment": "install-memory",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v405-segmented-install-smoke",
        "version": "405.0",
        "era": "verification-governance",
        "dashboard_route": "/segmented-install-smoke-audit",
        "api_route": "/api/segmented-install-smoke-audit/layer",
        "cli_flag": "--operator-governed-segmented-install-smoke-audit-v1",
        "builder_function": "build_operator_governed_segmented_install_smoke_audit_v1",
        "text_function": "operator_governed_segmented_install_smoke_audit_v1_text",
        "runtime_directory": "data/autonomy/segmented_install_smoke_audit/",
        "smoke_check": "operator-governed-segmented-install-smoke-audit-v1",
        "smoke_segment": "install-governance",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": False,
        "single_use_approval_required": False,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v410-memory-application-dry-run-ledger",
        "version": "410.0",
        "era": "memory-governance",
        "dashboard_route": "/memory-application-ledger-audit",
        "api_route": "/api/memory-application-ledger-audit/layer",
        "cli_flag": "--operator-governed-memory-application-dry-run-ledger-v1",
        "builder_function": "build_operator_governed_memory_application_dry_run_ledger_v1",
        "text_function": "operator_governed_memory_application_dry_run_ledger_v1_text",
        "runtime_directory": "data/autonomy/memory_application_ledger_audit/",
        "smoke_check": "operator-governed-memory-application-dry-run-ledger-v1",
        "smoke_segment": "install-memory",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v415-sandbox-memory-write-target",
        "version": "415.0",
        "era": "memory-sandbox",
        "dashboard_route": "/sandbox-memory-write-audit",
        "api_route": "/api/sandbox-memory-write-audit/layer",
        "cli_flag": "--operator-governed-sandbox-memory-write-target-v1",
        "builder_function": "build_operator_governed_sandbox_memory_write_target_v1",
        "text_function": "operator_governed_sandbox_memory_write_target_v1_text",
        "runtime_directory": "data/sandbox_memory_trials/",
        "smoke_check": "operator-governed-sandbox-memory-write-target-v1",
        "smoke_segment": "install-memory",
        "authority_level": "sandbox_only",
        "writes_files": True,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v420-live-memory-write-burnout",
        "version": "420.0",
        "era": "governed-live-memory-trial",
        "dashboard_route": "/live-memory-write-audit",
        "api_route": "/api/live-memory-write-audit/layer",
        "cli_flag": "--operator-governed-live-memory-write-burnout-v1",
        "builder_function": "build_operator_governed_live_memory_write_burnout_v1",
        "text_function": "operator_governed_live_memory_write_burnout_v1_text",
        "runtime_directory": "data/memory_application_trials/",
        "smoke_check": "operator-governed-live-memory-write-burnout-v1",
        "smoke_segment": "install-memory",
        "authority_level": "operator_approved_single_use_trial",
        "writes_files": True,
        "writes_memory": True,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v425-memory-retraction-trial",
        "version": "425.0",
        "era": "governed-memory-retraction-trial",
        "dashboard_route": "/memory-retraction-trial-audit",
        "api_route": "/api/memory-retraction-trial-audit/layer",
        "cli_flag": "--operator-governed-memory-retraction-trial-v1",
        "builder_function": "build_operator_governed_memory_retraction_trial_v1",
        "text_function": "operator_governed_memory_retraction_trial_v1_text",
        "runtime_directory": "data/memory_application_trials/",
        "smoke_check": "operator-governed-memory-retraction-trial-v1",
        "smoke_segment": "install-memory",
        "authority_level": "operator_approved_single_use_trial",
        "writes_files": True,
        "writes_memory": True,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v435-self-maintenance-duplicate-cleanup",
        "version": "435.0",
        "era": "structural-governance",
        "dashboard_route": "/self-maintenance-duplicate-cleanup-audit",
        "api_route": "/api/self-maintenance-duplicate-cleanup-audit/layer",
        "cli_flag": "--operator-governed-self-maintenance-duplicate-cleanup-v1",
        "builder_function": "build_operator_governed_self_maintenance_duplicate_cleanup_v1",
        "text_function": "operator_governed_self_maintenance_duplicate_cleanup_v1_text",
        "runtime_directory": "data/autonomy/self_maintenance_duplicate_cleanup_audit/",
        "smoke_check": "operator-governed-self-maintenance-duplicate-cleanup-v1",
        "smoke_segment": "install-governance",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": False,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v440-dashboard-route-health-audit",
        "version": "440.0",
        "era": "dashboard-governance",
        "dashboard_route": "/dashboard-route-health-audit",
        "api_route": "/api/dashboard-route-health-audit/layer",
        "cli_flag": "--operator-governed-dashboard-route-health-audit-v1",
        "builder_function": "build_operator_governed_dashboard_route_health_audit_v1",
        "text_function": "operator_governed_dashboard_route_health_audit_v1_text",
        "runtime_directory": "data/autonomy/dashboard_route_health_audit/",
        "smoke_check": "operator-governed-dashboard-route-health-audit-v1",
        "smoke_segment": "install-dashboard",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": False,
        "single_use_approval_required": False,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v445-memory-lifecycle-review-board",
        "version": "445.0",
        "era": "memory-lifecycle-governance",
        "dashboard_route": "/memory-lifecycle-review-board-audit",
        "api_route": "/api/memory-lifecycle-review-board-audit/layer",
        "cli_flag": "--operator-governed-memory-lifecycle-review-board-v1",
        "builder_function": "build_operator_governed_memory_lifecycle_review_board_v1",
        "text_function": "operator_governed_memory_lifecycle_review_board_v1_text",
        "runtime_directory": "data/autonomy/memory_lifecycle_review_board_audit/",
        "smoke_check": "operator-governed-memory-lifecycle-review-board-v1",
        "smoke_segment": "install-memory",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": False,
        "single_use_approval_required": False,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v430-source-surface-manifest",
        "version": "430.0",
        "era": "surface-governance",
        "dashboard_route": "/source-surface-manifest",
        "api_route": "/api/source-surface-manifest/layer",
        "cli_flag": "--source-surface-manifest-v1",
        "builder_function": "build_source_surface_manifest_v1",
        "text_function": "source_surface_manifest_v1_text",
        "runtime_directory": "data/autonomy/source_surface_manifest/",
        "smoke_check": "operator-governed-source-surface-manifest-v1",
        "smoke_segment": "install-governance",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": False,
        "single_use_approval_required": False,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
    {
        "surface_id": "v450-authorization-firewall",
        "version": "450.0",
        "era": "authorization-governance",
        "dashboard_route": "/authorization-firewall-audit",
        "api_route": "/api/authorization-firewall-audit/layer",
        "cli_flag": "--operator-governed-authorization-firewall-v1",
        "builder_function": "build_operator_governed_authorization_firewall_v1",
        "text_function": "operator_governed_authorization_firewall_v1_text",
        "runtime_directory": "data/autonomy/authorization_firewall_audit/",
        "smoke_check": "operator-governed-authorization-firewall-v1",
        "smoke_segment": "install-governance",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": False,
        "single_use_approval_required": False,
        "approval_burnout_required": False,
        "package_privacy_sensitive": True,
        "status": "represented",
    },
]


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v446-authorization-confusion-patterns","version":"v446.0","era":"authorization-governance","dashboard_route":"/authorization-confusion-patterns","api_route":"/api/authorization-confusion-patterns/layer","cli_flag":"--authorization-confusion-patterns-v1","builder_function":"build_authorization_confusion_patterns_v1","text_function":"authorization_confusion_patterns_v1_text","runtime_directory":"data/autonomy/authorization_confusion_patterns/","smoke_check":"operator-governed-authorization-firewall-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v447-authorization-language-scan","version":"v447.0","era":"authorization-governance","dashboard_route":"/authorization-language-scan","api_route":"/api/authorization-language-scan/layer","cli_flag":"--authorization-language-scan-v1","builder_function":"build_authorization_language_scan_v1","text_function":"authorization_language_scan_v1_text","runtime_directory":"data/autonomy/authorization_language_scan/","smoke_check":"operator-governed-authorization-firewall-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v448-authorization-firewall-decision-packet","version":"v448.0","era":"authorization-governance","dashboard_route":"/authorization-firewall-decision-packet","api_route":"/api/authorization-firewall-decision-packet/layer","cli_flag":"--authorization-firewall-decision-packet-v1","builder_function":"build_authorization_firewall_decision_packet_v1","text_function":"authorization_firewall_decision_packet_v1_text","runtime_directory":"data/autonomy/authorization_firewall_decision_packet/","smoke_check":"operator-governed-authorization-firewall-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v449-authorization-boundary-map","version":"v449.0","era":"authorization-governance","dashboard_route":"/authorization-boundary-map","api_route":"/api/authorization-boundary-map/layer","cli_flag":"--authorization-boundary-map-v1","builder_function":"build_authorization_boundary_map_v1","text_function":"authorization_boundary_map_v1_text","runtime_directory":"data/autonomy/authorization_boundary_map/","smoke_check":"operator-governed-authorization-firewall-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v451-metadata-version-inventory","version":"v451.0","era":"metadata-release-integrity","dashboard_route":"/metadata-version-inventory","api_route":"/api/metadata-version-inventory/layer","cli_flag":"--metadata-version-inventory-v1","builder_function":"build_metadata_version_inventory_v1","text_function":"metadata_version_inventory_v1_text","runtime_directory":"data/autonomy/metadata_version_inventory/","smoke_check":"operator-governed-metadata-release-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v452-project-workspace-metadata-alignment","version":"v452.0","era":"metadata-release-integrity","dashboard_route":"/project-workspace-metadata-alignment","api_route":"/api/project-workspace-metadata-alignment/layer","cli_flag":"--project-workspace-metadata-alignment-v1","builder_function":"build_project_workspace_metadata_alignment_v1","text_function":"project_workspace_metadata_alignment_v1_text","runtime_directory":"data/autonomy/project_workspace_metadata_alignment/","smoke_check":"operator-governed-metadata-release-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v453-release-packaging-version-integrity","version":"v453.0","era":"metadata-release-integrity","dashboard_route":"/release-packaging-version-integrity","api_route":"/api/release-packaging-version-integrity/layer","cli_flag":"--release-packaging-version-integrity-v1","builder_function":"build_release_packaging_version_integrity_v1","text_function":"release_packaging_version_integrity_v1_text","runtime_directory":"data/autonomy/release_packaging_version_integrity/","smoke_check":"operator-governed-metadata-release-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v454-current-state-documentation-header-audit","version":"v454.0","era":"metadata-release-integrity","dashboard_route":"/current-state-documentation-header-audit","api_route":"/api/current-state-documentation-header-audit/layer","cli_flag":"--current-state-documentation-header-audit-v1","builder_function":"build_current_state_documentation_header_audit_v1","text_function":"current_state_documentation_header_audit_v1_text","runtime_directory":"data/autonomy/current_state_documentation_header_audit/","smoke_check":"operator-governed-metadata-release-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v455-metadata-release-integrity","version":"v455.0","era":"metadata-release-integrity","dashboard_route":"/metadata-release-integrity-audit","api_route":"/api/metadata-release-integrity-audit/layer","cli_flag":"--operator-governed-metadata-release-integrity-v1","builder_function":"build_operator_governed_metadata_release_integrity_v1","text_function":"operator_governed_metadata_release_integrity_v1_text","runtime_directory":"data/autonomy/metadata_release_integrity_audit/","smoke_check":"operator-governed-metadata-release-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v456-authorization-firewall-severity-classifier","version":"v456.0","era":"authorization-firewall-triage","dashboard_route":"/authorization-firewall-severity-classifier","api_route":"/api/authorization-firewall-severity-classifier/layer","cli_flag":"--authorization-firewall-severity-classifier-v1","builder_function":"build_authorization_firewall_severity_classifier_v1","text_function":"authorization_firewall_severity_classifier_v1_text","runtime_directory":"data/autonomy/authorization_firewall_severity_classifier/","smoke_check":"operator-governed-authorization-firewall-signal-triage-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v457-authorization-firewall-safe-boundary-filter","version":"v457.0","era":"authorization-firewall-triage","dashboard_route":"/authorization-firewall-safe-boundary-filter","api_route":"/api/authorization-firewall-safe-boundary-filter/layer","cli_flag":"--authorization-firewall-safe-boundary-filter-v1","builder_function":"build_authorization_firewall_safe_boundary_filter_v1","text_function":"authorization_firewall_safe_boundary_filter_v1_text","runtime_directory":"data/autonomy/authorization_firewall_safe_boundary_filter/","smoke_check":"operator-governed-authorization-firewall-signal-triage-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v458-authorization-firewall-warning-status","version":"v458.0","era":"authorization-firewall-triage","dashboard_route":"/authorization-firewall-warning-status","api_route":"/api/authorization-firewall-warning-status/layer","cli_flag":"--authorization-firewall-warning-status-v1","builder_function":"build_authorization_firewall_warning_status_v1","text_function":"authorization_firewall_warning_status_v1_text","runtime_directory":"data/autonomy/authorization_firewall_warning_status/","smoke_check":"operator-governed-authorization-firewall-signal-triage-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v459-authorization-firewall-audit-status-split","version":"v459.0","era":"authorization-firewall-triage","dashboard_route":"/authorization-firewall-audit-status-split","api_route":"/api/authorization-firewall-audit-status-split/layer","cli_flag":"--authorization-firewall-audit-status-split-v1","builder_function":"build_authorization_firewall_audit_status_split_v1","text_function":"authorization_firewall_audit_status_split_v1_text","runtime_directory":"data/autonomy/authorization_firewall_audit_status_split/","smoke_check":"operator-governed-authorization-firewall-signal-triage-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v460-authorization-firewall-signal-triage","version":"v460.0","era":"authorization-firewall-triage","dashboard_route":"/authorization-firewall-signal-triage-audit","api_route":"/api/authorization-firewall-signal-triage-audit/layer","cli_flag":"--operator-governed-authorization-firewall-signal-triage-v1","builder_function":"build_operator_governed_authorization_firewall_signal_triage_v1","text_function":"operator_governed_authorization_firewall_signal_triage_v1_text","runtime_directory":"data/autonomy/authorization_firewall_signal_triage_audit/","smoke_check":"operator-governed-authorization-firewall-signal-triage-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v461-recent-dashboard-route-probe-refresh","version":"v461.0","era":"route-surface-parity","dashboard_route":"/recent-dashboard-route-probe-refresh","api_route":"/api/recent-dashboard-route-probe-refresh/layer","cli_flag":"--recent-dashboard-route-probe-refresh-v1","builder_function":"build_recent_dashboard_route_probe_refresh_v1","text_function":"recent_dashboard_route_probe_refresh_v1_text","runtime_directory":"data/autonomy/recent_dashboard_route_probe_refresh/","smoke_check":"operator-governed-route-surface-parity-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v462-source-surface-manifest-parity-policy","version":"v462.0","era":"route-surface-parity","dashboard_route":"/source-surface-manifest-parity-policy","api_route":"/api/source-surface-manifest-parity-policy/layer","cli_flag":"--source-surface-manifest-parity-policy-v1","builder_function":"build_source_surface_manifest_parity_policy_v1","text_function":"source_surface_manifest_parity_policy_v1_text","runtime_directory":"data/autonomy/source_surface_manifest_parity_policy/","smoke_check":"operator-governed-route-surface-parity-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v463-surface-route-api-cli-crosscheck","version":"v463.0","era":"route-surface-parity","dashboard_route":"/surface-route-api-cli-crosscheck","api_route":"/api/surface-route-api-cli-crosscheck/layer","cli_flag":"--surface-route-api-cli-crosscheck-v1","builder_function":"build_surface_route_api_cli_crosscheck_v1","text_function":"surface_route_api_cli_crosscheck_v1_text","runtime_directory":"data/autonomy/surface_route_api_cli_crosscheck/","smoke_check":"operator-governed-route-surface-parity-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v464-route-health-boundary-language","version":"v464.0","era":"route-surface-parity","dashboard_route":"/route-health-boundary-language","api_route":"/api/route-health-boundary-language/layer","cli_flag":"--route-health-boundary-language-v1","builder_function":"build_route_health_boundary_language_v1","text_function":"route_health_boundary_language_v1_text","runtime_directory":"data/autonomy/route_health_boundary_language/","smoke_check":"operator-governed-route-surface-parity-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v465-route-surface-parity-audit","version":"v465.0","era":"route-surface-parity","dashboard_route":"/route-surface-parity-audit","api_route":"/api/route-surface-parity-audit/layer","cli_flag":"--operator-governed-route-surface-parity-v1","builder_function":"build_operator_governed_route_surface_parity_v1","text_function":"operator_governed_route_surface_parity_v1_text","runtime_directory":"data/autonomy/route_surface_parity_audit/","smoke_check":"operator-governed-route-surface-parity-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _docs_contain(docs: str, token: str) -> bool:
    return token in docs


def _normalize_version_label(value: Any) -> str:
    text = str(value or "").strip()
    return text[1:] if text.startswith("v") else text


def _surface_origin_version(surface_id: str, fallback_version: Any = "") -> str:
    match = re.match(r"v(?P<origin>\d+)-", str(surface_id or ""))
    if match:
        return f"{match.group('origin')}.0"
    return _normalize_version_label(fallback_version)


def _normalize_manifest_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(entry)
    legacy_version = normalized.get("version")
    origin_version = normalized.get("surface_origin_version") or _surface_origin_version(
        str(normalized.get("surface_id", "")), legacy_version or ""
    )
    normalized.setdefault("legacy_version", legacy_version)
    normalized["surface_origin_version"] = origin_version
    normalized["manifest_representation_version"] = SOURCE_SURFACE_MANIFEST_VERSION
    normalized["last_verified_for_version"] = SOURCE_SURFACE_MANIFEST_VERSION
    normalized.setdefault("version", SOURCE_SURFACE_MANIFEST_VERSION)
    normalized["legacy_version_validation_mode"] = "compatibility_only_not_current_state"
    return normalized


def build_manifest_validation_normalization_summary(entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Validate the v908 split-field semantics without treating legacy version as truth.

    Historical surface origins are allowed. Current manifest representation and
    verification fields must match the current manifest version. The legacy
    version field is retained for older consumers but is not used as the
    current-state validation source.
    """
    manifest = build_source_surface_manifest_summary(entries)
    rows: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        surface_id = str(entry.get("surface_id") or "")
        expected_origin = _surface_origin_version(surface_id, entry.get("legacy_version") or entry.get("version") or "")
        origin = entry.get("surface_origin_version")
        representation = entry.get("manifest_representation_version")
        verified = entry.get("last_verified_for_version")
        legacy = entry.get("legacy_version", entry.get("version"))
        checks = {
            "origin_present": bool(origin),
            "origin_matches_surface_id_or_fallback": bool(origin) and origin == expected_origin,
            "representation_current": representation == SOURCE_SURFACE_MANIFEST_VERSION,
            "last_verified_current": verified == SOURCE_SURFACE_MANIFEST_VERSION,
            "legacy_version_not_used_as_current_state": True,
        }
        rows.append({
            "surface_id": surface_id,
            "legacy_version": legacy,
            "surface_origin_version": origin,
            "manifest_representation_version": representation,
            "last_verified_for_version": verified,
            "expected_surface_origin_version": expected_origin,
            "historical_origin": origin != SOURCE_SURFACE_MANIFEST_VERSION,
            "legacy_representation_mismatch": legacy != representation,
            "checks": checks,
            "status": "pass" if all(checks.values()) else "blocked",
        })
    blockers = [row for row in rows if row["status"] != "pass"]
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "manifest_validation_normalized_review_only",
        "entry_count": len(rows),
        "row_count": len(rows),
        "normalized_row_count": sum(1 for row in rows if row["status"] == "pass"),
        "historical_origin_count": sum(1 for row in rows if row.get("historical_origin")),
        "legacy_representation_mismatch_count": sum(1 for row in rows if row.get("legacy_representation_mismatch")),
        "surface_origin_versions_required": True,
        "manifest_representation_versions_required_current": True,
        "last_verified_versions_required_current": True,
        "legacy_version_field_validation_mode": "compatibility_only_not_current_state",
        "historical_origin_versions_allowed": True,
        "current_state_version_source": "manifest_representation_version_and_last_verified_for_version",
        "legacy_version_is_current_state_source": False,
        "rows": rows,
        "blocker_count": len(blockers),
        "blockers": blockers[:25],
        "manifest_ok": manifest.get("ok") is True,
        "ok": manifest.get("ok") is True and not blockers,
        "review_only": True,
        "grants_authorization": False,
        "expands_autonomy": False,
    }


def build_source_surface_manifest_summary(entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    raw_entries = [dict(entry) for entry in (entries or RECENT_SURFACE_ENTRIES)]
    entries = [_normalize_manifest_entry(entry) for entry in raw_entries]
    blockers: list[str] = []
    required_fields = {
        "surface_id", "version", "surface_origin_version", "manifest_representation_version",
        "last_verified_for_version", "era", "dashboard_route", "api_route", "cli_flag",
        "builder_function", "text_function", "runtime_directory", "smoke_check",
        "smoke_segment", "authority_level", "writes_files", "writes_memory",
        "requires_operator_approval", "single_use_approval_required", "approval_burnout_required",
        "package_privacy_sensitive", "status",
    }
    for entry in entries:
        missing = sorted(required_fields - set(entry))
        if missing:
            blockers.append(f"{entry.get('surface_id', 'unknown')}:missing:{','.join(missing)}")
        if entry.get("authority_level") not in AUTHORITY_LEVELS:
            blockers.append(f"{entry.get('surface_id', 'unknown')}:bad-authority")
        if not entry.get("surface_origin_version"):
            blockers.append(f"{entry.get('surface_id', 'unknown')}:missing-surface-origin-version")
        if entry.get("manifest_representation_version") != SOURCE_SURFACE_MANIFEST_VERSION:
            blockers.append(f"{entry.get('surface_id', 'unknown')}:stale-manifest-representation-version")
        if entry.get("last_verified_for_version") != SOURCE_SURFACE_MANIFEST_VERSION:
            blockers.append(f"{entry.get('surface_id', 'unknown')}:stale-last-verified-for-version")
    origin_representation_mismatches = [
        entry["surface_id"] for entry in entries
        if entry.get("surface_origin_version") != entry.get("manifest_representation_version")
    ]
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "canonical_source_surface_manifest_review_only",
        "entries": entries,
        "entry_count": len(entries),
        "manifest_hash": _stable_hash(entries),
        "version_semantics": dict(MANIFEST_VERSION_SEMANTICS),
        "legacy_version_field_retained_for_compatibility": True,
        "manifest_version_schema_split_applied": True,
        "surface_origin_version_count": sum(1 for entry in entries if entry.get("surface_origin_version")),
        "manifest_representation_version_count": sum(1 for entry in entries if entry.get("manifest_representation_version") == SOURCE_SURFACE_MANIFEST_VERSION),
        "last_verified_for_version_count": sum(1 for entry in entries if entry.get("last_verified_for_version") == SOURCE_SURFACE_MANIFEST_VERSION),
        "origin_representation_mismatch_count": len(origin_representation_mismatches),
        "origin_representation_mismatches_are_historical_not_stale": True,
        "authority_levels": sorted(AUTHORITY_LEVELS),
        "boundaries": dict(SOURCE_SURFACE_MANIFEST_BOUNDARIES),
        "blockers": blockers,
        "ok": not blockers,
        "writes_files": False,
        "writes_memory": False,
        "grants_authorization": False,
        "manifest_presence_is_authorization": False,
    }


def build_source_surface_parity_audit_summary(docs: str = "", entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manifest = build_source_surface_manifest_summary(entries)
    rows: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        tokens = [
            entry["dashboard_route"],
            entry["api_route"].replace("/api/", "").replace("/layer", ""),
            entry["cli_flag"],
            entry["builder_function"],
            entry["text_function"],
            entry["smoke_check"],
        ]
        missing = [token for token in tokens if not _docs_contain(docs, token)]
        rows.append({
            "surface_id": entry["surface_id"],
            "status": "pass" if not missing else "blocked",
            "missing_tokens": missing,
            "dashboard_route": entry["dashboard_route"],
            "api_route": entry["api_route"],
            "cli_flag": entry["cli_flag"],
            "smoke_check": entry["smoke_check"],
        })
    blockers = [row["surface_id"] for row in rows if row["status"] != "pass"]
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "source_surface_parity_audit_review_only",
        "rows": rows,
        "blockers": blockers,
        "ok": not blockers and manifest.get("ok") is True,
        "parity_pass_is_authorization": False,
        "surface_exists_means_may_execute": False,
    }


def build_source_surface_authority_map_summary(entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manifest = build_source_surface_manifest_summary(entries)
    by_authority: dict[str, list[str]] = {label: [] for label in sorted(AUTHORITY_LEVELS)}
    write_surfaces: list[str] = []
    memory_surfaces: list[str] = []
    for entry in manifest["entries"]:
        by_authority.setdefault(entry["authority_level"], []).append(entry["surface_id"])
        if entry.get("writes_files"):
            write_surfaces.append(entry["surface_id"])
        if entry.get("writes_memory"):
            memory_surfaces.append(entry["surface_id"])
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "source_surface_authority_map_review_only",
        "by_authority": by_authority,
        "write_surfaces": write_surfaces,
        "memory_surfaces": memory_surfaces,
        "operator_approval_required": [entry["surface_id"] for entry in manifest["entries"] if entry.get("requires_operator_approval")],
        "single_use_approval_required": [entry["surface_id"] for entry in manifest["entries"] if entry.get("single_use_approval_required")],
        "approval_burnout_required": [entry["surface_id"] for entry in manifest["entries"] if entry.get("approval_burnout_required")],
        "authority_label_is_approval": False,
        "ok": manifest.get("ok") is True,
    }


def build_source_surface_package_privacy_map_summary(entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manifest = build_source_surface_manifest_summary(entries)
    sensitive = [entry for entry in manifest["entries"] if entry.get("package_privacy_sensitive")]
    runtime_dirs = sorted({entry["runtime_directory"] for entry in sensitive if entry.get("runtime_directory")})
    forbidden_live_paths = ["memory.json", "data/runtime/", "data/memory_application_trials/", "logs/", "__pycache__/", "*.pyc"]
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "source_surface_package_privacy_map_review_only",
        "package_privacy_sensitive_count": len(sensitive),
        "runtime_directories": runtime_dirs,
        "forbidden_live_paths": forbidden_live_paths,
        "source_only_package_must_exclude_runtime": True,
        "manifest_writes_files": False,
        "manifest_writes_memory": False,
        "ok": bool(runtime_dirs) and manifest.get("ok") is True,
    }


def build_source_surface_manifest_audit_summary(docs: str = "", entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manifest = build_source_surface_manifest_summary(entries)
    parity = build_source_surface_parity_audit_summary(docs, manifest["entries"])
    authority = build_source_surface_authority_map_summary(manifest["entries"])
    privacy = build_source_surface_package_privacy_map_summary(manifest["entries"])
    blockers = list(manifest.get("blockers", [])) + list(parity.get("blockers", []))
    required_tokens = [
        "v430.0 - Canonical Source Surface Manifest v1",
        "source-surface-manifest",
        "source-surface-parity-audit",
        "source-surface-authority-map",
        "source-surface-package-privacy-map",
        "operator-governed-source-surface-manifest-v1",
        "manifest_presence_is_authorization=False",
        "parity_pass_is_authorization=False",
        "surface_exists_means_may_execute=False",
        "smoke_pass_allows_live_action=False",
    ]
    for token in required_tokens:
        if token not in docs:
            blockers.append(f"docs-missing:{token}")
    for key, value in SOURCE_SURFACE_MANIFEST_BOUNDARIES.items():
        if key == "operator_review_required":
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "canonical_source_surface_manifest_audit_review_only",
        "manifest": manifest,
        "parity": parity,
        "authority": authority,
        "package_privacy": privacy,
        "boundaries": dict(SOURCE_SURFACE_MANIFEST_BOUNDARIES),
        "blockers": blockers,
        "ok": not blockers,
        "status": "pass" if not blockers else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "grants_authorization": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the manifest and parity map. Manifest presence, parity success, authority labels, and smoke success do not approve execution, memory writes, releases, or autonomous continuation.",
    }


def render_source_surface_manifest_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"grants_authorization: {report.get('grants_authorization', False)}",
    ]
    entries = report.get("entries") or report.get("manifest", {}).get("entries", [])
    if entries:
        lines.append("surfaces:")
        for entry in entries[:12]:
            lines.append(f"- {entry.get('surface_id')} | {entry.get('authority_level')} | {entry.get('dashboard_route')} | {entry.get('cli_flag')}")
    blockers = report.get("blockers", [])
    if blockers:
        lines.append("blockers:")
        lines.extend(f"- {blocker}" for blocker in blockers)
    return lines


# v425.1-v430.0 source surface manifest smoke tokens: source-surface-manifest source-surface-parity-audit source-surface-authority-map source-surface-package-privacy-map operator-governed-source-surface-manifest-v1 source_surface_manifest.py manifest_presence_is_authorization=False parity_pass_is_authorization=False authority_label_is_approval=False surface_exists_means_may_execute=False smoke_pass_allows_live_action=False manifest_writes_files=False manifest_writes_memory=False source_only_package_must_exclude_runtime=True data-tip no_native_title_tooltip command-deck operator-console

# v445.1-v450.0 authorization firewall manifest tokens: v450-authorization-firewall authorization-firewall-audit operator-governed-authorization-firewall-v1 install-governance review_only manifest_presence_is_authorization=False firewall_pass_is_authorization=False

# v460.1-v465.0 route surface parity manifest tokens: v461-recent-dashboard-route-probe-refresh v462-source-surface-manifest-parity-policy v463-surface-route-api-cli-crosscheck v464-route-health-boundary-language v465-route-surface-parity-audit operator-governed-route-surface-parity-v1 every_governed_substage_surface route_presence_is_authorization=False route_health_is_approval=False manifest_presence_is_authorization=False surface_parity_is_permission=False smoke_success_is_approval=False route_health_confirms_render_status_only=True route_health_does_not_authorize_execution=True parity_audit_applies_patches=False parity_audit_writes_memory=False parity_audit_expands_autonomy=False operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v466-duplicate-shadow-inventory","version":"v466.0","era":"self-maintenance-duplicate-shadow-cleanup","dashboard_route":"/duplicate-shadow-inventory","api_route":"/api/duplicate-shadow-inventory/layer","cli_flag":"--duplicate-shadow-inventory-v1","builder_function":"build_duplicate_shadow_inventory_v1","text_function":"duplicate_shadow_inventory_v1_text","runtime_directory":"data/autonomy/duplicate_shadow_inventory/","smoke_check":"operator-governed-self-maintenance-duplicate-shadow-cleanup-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v467-safe-shadow-removal-report","version":"v467.0","era":"self-maintenance-duplicate-shadow-cleanup","dashboard_route":"/safe-shadow-removal-report","api_route":"/api/safe-shadow-removal-report/layer","cli_flag":"--safe-shadow-removal-report-v1","builder_function":"build_safe_shadow_removal_report_v1","text_function":"safe_shadow_removal_report_v1_text","runtime_directory":"data/autonomy/safe_shadow_removal_report/","smoke_check":"operator-governed-self-maintenance-duplicate-shadow-cleanup-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v468-legacy-alias-compatibility-cleanup","version":"v468.0","era":"self-maintenance-duplicate-shadow-cleanup","dashboard_route":"/legacy-alias-compatibility-cleanup","api_route":"/api/legacy-alias-compatibility-cleanup/layer","cli_flag":"--legacy-alias-compatibility-cleanup-v1","builder_function":"build_legacy_alias_compatibility_cleanup_v1","text_function":"legacy_alias_compatibility_cleanup_v1_text","runtime_directory":"data/autonomy/legacy_alias_compatibility_cleanup/","smoke_check":"operator-governed-self-maintenance-duplicate-shadow-cleanup-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v469-stale-version-gate-cleanup","version":"v469.0","era":"self-maintenance-duplicate-shadow-cleanup","dashboard_route":"/stale-version-gate-cleanup","api_route":"/api/stale-version-gate-cleanup/layer","cli_flag":"--stale-version-gate-cleanup-v1","builder_function":"build_stale_version_gate_cleanup_v1","text_function":"stale_version_gate_cleanup_v1_text","runtime_directory":"data/autonomy/stale_version_gate_cleanup/","smoke_check":"operator-governed-self-maintenance-duplicate-shadow-cleanup-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v470-self-maintenance-duplicate-shadow-cleanup-audit","version":"v470.0","era":"self-maintenance-duplicate-shadow-cleanup","dashboard_route":"/self-maintenance-duplicate-shadow-cleanup-audit","api_route":"/api/self-maintenance-duplicate-shadow-cleanup-audit/layer","cli_flag":"--operator-governed-self-maintenance-duplicate-shadow-cleanup-v1","builder_function":"build_operator_governed_self_maintenance_duplicate_shadow_cleanup_v1","text_function":"operator_governed_self_maintenance_duplicate_shadow_cleanup_v1_text","runtime_directory":"data/autonomy/self_maintenance_duplicate_shadow_cleanup_audit/","smoke_check":"operator-governed-self-maintenance-duplicate-shadow-cleanup-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v465.1-v470.0 duplicate shadow cleanup manifest tokens: v466-duplicate-shadow-inventory v467-safe-shadow-removal-report v468-legacy-alias-compatibility-cleanup v469-stale-version-gate-cleanup v470-self-maintenance-duplicate-shadow-cleanup-audit operator-governed-self-maintenance-duplicate-shadow-cleanup-v1 duplicate_cleanup_is_authorization=False classification_is_permission_to_delete=False shadow_removal_expands_autonomy=False stale_gate_cleanup_authorizes_execution=False cleanup_applies_live_patches=False cleanup_writes_memory=False operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v471-current-state-header-block","version":"v471.0","era":"documentation-continuity","dashboard_route":"/current-state-header-block","api_route":"/api/current-state-header-block/layer","cli_flag":"--current-state-header-block-v1","builder_function":"build_current_state_header_block_v1","text_function":"current_state_header_block_v1_text","runtime_directory":"data/autonomy/current_state_header_block/","smoke_check":"operator-governed-documentation-continuity-header-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v472-historical-next-steps-separation","version":"v472.0","era":"documentation-continuity","dashboard_route":"/historical-next-steps-separation","api_route":"/api/historical-next-steps-separation/layer","cli_flag":"--historical-next-steps-separation-v1","builder_function":"build_historical_next_steps_separation_v1","text_function":"historical_next_steps_separation_v1_text","runtime_directory":"data/autonomy/historical_next_steps_separation/","smoke_check":"operator-governed-documentation-continuity-header-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v473-operator-continuity-handoff-packet","version":"v473.0","era":"documentation-continuity","dashboard_route":"/operator-continuity-handoff-packet","api_route":"/api/operator-continuity-handoff-packet/layer","cli_flag":"--operator-continuity-handoff-packet-v1","builder_function":"build_operator_continuity_handoff_packet_v1","text_function":"operator_continuity_handoff_packet_v1_text","runtime_directory":"data/autonomy/operator_continuity_handoff_packet/","smoke_check":"operator-governed-documentation-continuity-header-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v474-documentation-boundary-language","version":"v474.0","era":"documentation-continuity","dashboard_route":"/documentation-boundary-language","api_route":"/api/documentation-boundary-language/layer","cli_flag":"--documentation-boundary-language-v1","builder_function":"build_documentation_boundary_language_v1","text_function":"documentation_boundary_language_v1_text","runtime_directory":"data/autonomy/documentation_boundary_language/","smoke_check":"operator-governed-documentation-continuity-header-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v475-documentation-continuity-header-audit","version":"v475.0","era":"documentation-continuity","dashboard_route":"/documentation-continuity-header-audit","api_route":"/api/documentation-continuity-header-audit/layer","cli_flag":"--operator-governed-documentation-continuity-header-v1","builder_function":"build_operator_governed_documentation_continuity_header_v1","text_function":"operator_governed_documentation_continuity_header_v1_text","runtime_directory":"data/autonomy/documentation_continuity_header_audit/","smoke_check":"operator-governed-documentation-continuity-header-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v470.1-v480.0 documentation continuity manifest tokens: v471-current-state-header-block v472-historical-next-steps-separation v473-operator-continuity-handoff-packet v474-documentation-boundary-language v475-documentation-continuity-header-audit operator-governed-documentation-continuity-header-v1 documentation_state_is_authorization=False release_history_is_authorization=False recommended_next_arc_is_permission=False handoff_packet_is_execution_packet=False current_state_header_creates_approval=False documentation_cleanup_writes_memory=False documentation_cleanup_applies_source_edits=False documentation_cleanup_expands_autonomy=False operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v476-manual-read-only-observation-scope","version":"v476.0","era":"operator-observation-prep","dashboard_route":"/manual-read-only-observation-scope","api_route":"/api/manual-read-only-observation-scope/layer","cli_flag":"--manual-read-only-observation-scope-v1","builder_function":"build_manual_read_only_observation_scope_v1","text_function":"manual_read_only_observation_scope_v1_text","runtime_directory":"data/autonomy/manual_read_only_observation_scope/","smoke_check":"operator-invoked-read-only-observation-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v477-operator-observation-packet","version":"v477.0","era":"operator-observation-prep","dashboard_route":"/operator-observation-packet","api_route":"/api/operator-observation-packet/layer","cli_flag":"--operator-observation-packet-v1","builder_function":"build_operator_observation_packet_v1","text_function":"operator_observation_packet_v1_text","runtime_directory":"data/autonomy/operator_observation_packet/","smoke_check":"operator-invoked-read-only-observation-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v478-no-mutation-observation-audit","version":"v478.0","era":"operator-observation-prep","dashboard_route":"/no-mutation-observation-audit","api_route":"/api/no-mutation-observation-audit/layer","cli_flag":"--no-mutation-observation-audit-v1","builder_function":"build_no_mutation_observation_audit_v1","text_function":"no_mutation_observation_audit_v1_text","runtime_directory":"data/autonomy/no_mutation_observation_audit/","smoke_check":"operator-invoked-read-only-observation-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v479-operator-invocation-boundary","version":"v479.0","era":"operator-observation-prep","dashboard_route":"/operator-invocation-boundary","api_route":"/api/operator-invocation-boundary/layer","cli_flag":"--operator-invocation-boundary-v1","builder_function":"build_operator_invocation_boundary_v1","text_function":"operator_invocation_boundary_v1_text","runtime_directory":"data/autonomy/operator_invocation_boundary/","smoke_check":"operator-invoked-read-only-observation-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v480-operator-read-only-observation-audit","version":"v480.0","era":"operator-observation-prep","dashboard_route":"/operator-read-only-observation-audit","api_route":"/api/operator-read-only-observation-audit/layer","cli_flag":"--operator-invoked-read-only-observation-prep-v1","builder_function":"build_operator_invoked_read_only_observation_prep_v1","text_function":"operator_invoked_read_only_observation_prep_v1_text","runtime_directory":"data/autonomy/operator_read_only_observation_audit/","smoke_check":"operator-invoked-read-only-observation-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v475.1-v480.0 operator observation prep manifest tokens: v476-manual-read-only-observation-scope v477-operator-observation-packet v478-no-mutation-observation-audit v479-operator-invocation-boundary v480-operator-read-only-observation-audit operator-invoked-read-only-observation-prep-v1 observation_is_authorization=False observation_is_execution=False observation_grants_followup_permission=False observation_writes_source=False observation_writes_memory=False observation_updates_metadata=False observation_schedules_work=False observation_invokes_models_by_default=False observation_creates_approval=False operator_invocation_required=True single_run_read_only=True operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v481-observation-ledger-schema","version":"v481.0","era":"observation-ledger-boundary","dashboard_route":"/observation-ledger-schema","api_route":"/api/observation-ledger-schema/layer","cli_flag":"--observation-ledger-schema-v1","builder_function":"build_observation_ledger_schema_v1","text_function":"observation_ledger_schema_v1_text","runtime_directory":"data/autonomy/observation_ledger_schema/","smoke_check":"operator-governed-observation-ledger-boundary-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v482-observation-receipt-builder","version":"v482.0","era":"observation-ledger-boundary","dashboard_route":"/observation-receipt-builder","api_route":"/api/observation-receipt-builder/layer","cli_flag":"--observation-receipt-builder-v1","builder_function":"build_observation_receipt_builder_v1","text_function":"observation_receipt_builder_v1_text","runtime_directory":"data/autonomy/observation_receipt_builder/","smoke_check":"operator-governed-observation-ledger-boundary-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v483-observation-stop-pause-semantics","version":"v483.0","era":"observation-ledger-boundary","dashboard_route":"/observation-stop-pause-semantics","api_route":"/api/observation-stop-pause-semantics/layer","cli_flag":"--observation-stop-pause-semantics-v1","builder_function":"build_observation_stop_pause_semantics_v1","text_function":"observation_stop_pause_semantics_v1_text","runtime_directory":"data/autonomy/observation_stop_pause_semantics/","smoke_check":"operator-governed-observation-ledger-boundary-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v484-hidden-scheduling-continuation-audit","version":"v484.0","era":"observation-ledger-boundary","dashboard_route":"/hidden-scheduling-continuation-audit","api_route":"/api/hidden-scheduling-continuation-audit/layer","cli_flag":"--hidden-scheduling-continuation-audit-v1","builder_function":"build_hidden_scheduling_continuation_audit_v1","text_function":"hidden_scheduling_continuation_audit_v1_text","runtime_directory":"data/autonomy/hidden_scheduling_continuation_audit/","smoke_check":"operator-governed-observation-ledger-boundary-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v485-observation-ledger-boundary-audit","version":"v485.0","era":"observation-ledger-boundary","dashboard_route":"/observation-ledger-boundary-audit","api_route":"/api/observation-ledger-boundary-audit/layer","cli_flag":"--operator-governed-observation-ledger-boundary-v1","builder_function":"build_operator_governed_observation_ledger_boundary_v1","text_function":"operator_governed_observation_ledger_boundary_v1_text","runtime_directory":"data/autonomy/observation_ledger_boundary_audit/","smoke_check":"operator-governed-observation-ledger-boundary-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v480.1-v485.0 observation ledger boundary manifest tokens: v481-observation-ledger-schema v482-observation-receipt-builder v483-observation-stop-pause-semantics v484-hidden-scheduling-continuation-audit v485-observation-ledger-boundary-audit operator-governed-observation-ledger-boundary-v1 ledger_presence_is_approval=False ledger_completeness_is_authorization=False observation_history_permits_future_action=False receipt_is_approval=False hidden_scheduling_allowed=False automatic_continuation_allowed=False daily_loop_allowed=False hourly_loop_allowed=False auto_roadmap_selection_allowed=False auto_patch_packet_generation_allowed=False auto_promotion_from_observation_allowed=False source_mutation_allowed=False memory_mutation_allowed=False approval_creation_allowed=False operator_invocation_required=True operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v486-observation-to-proposal-candidate-mapper","version":"v486.0","era":"observation-proposal-queue","dashboard_route":"/observation-to-proposal-candidate-mapper","api_route":"/api/observation-to-proposal-candidate-mapper/layer","cli_flag":"--observation-to-proposal-candidate-mapper-v1","builder_function":"build_observation_to_proposal_candidate_mapper_v1","text_function":"observation_to_proposal_candidate_mapper_v1_text","runtime_directory":"data/autonomy/observation_to_proposal_candidate_mapper/","smoke_check":"operator-governed-observation-proposal-queue-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v487-proposal-queue-schema","version":"v487.0","era":"observation-proposal-queue","dashboard_route":"/proposal-queue-schema","api_route":"/api/proposal-queue-schema/layer","cli_flag":"--proposal-queue-schema-v1","builder_function":"build_proposal_queue_schema_v1","text_function":"proposal_queue_schema_v1_text","runtime_directory":"data/autonomy/proposal_queue_schema/","smoke_check":"operator-governed-observation-proposal-queue-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v488-proposal-ranking-risk-notes","version":"v488.0","era":"observation-proposal-queue","dashboard_route":"/proposal-ranking-risk-notes","api_route":"/api/proposal-ranking-risk-notes/layer","cli_flag":"--proposal-ranking-risk-notes-v1","builder_function":"build_proposal_ranking_risk_notes_v1","text_function":"proposal_ranking_risk_notes_v1_text","runtime_directory":"data/autonomy/proposal_ranking_risk_notes/","smoke_check":"operator-governed-observation-proposal-queue-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v489-proposal-queue-non-execution-audit","version":"v489.0","era":"observation-proposal-queue","dashboard_route":"/proposal-queue-non-execution-audit","api_route":"/api/proposal-queue-non-execution-audit/layer","cli_flag":"--proposal-queue-non-execution-audit-v1","builder_function":"build_proposal_queue_non_execution_audit_v1","text_function":"proposal_queue_non_execution_audit_v1_text","runtime_directory":"data/autonomy/proposal_queue_non_execution_audit/","smoke_check":"operator-governed-observation-proposal-queue-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v490-observation-proposal-queue-audit","version":"v490.0","era":"observation-proposal-queue","dashboard_route":"/observation-proposal-queue-audit","api_route":"/api/observation-proposal-queue-audit/layer","cli_flag":"--operator-governed-observation-proposal-queue-v1","builder_function":"build_operator_governed_observation_proposal_queue_v1","text_function":"operator_governed_observation_proposal_queue_v1_text","runtime_directory":"data/autonomy/observation_proposal_queue_audit/","smoke_check":"operator-governed-observation-proposal-queue-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v485.1-v490.0 observation proposal queue manifest tokens: v486-observation-to-proposal-candidate-mapper v487-proposal-queue-schema v488-proposal-ranking-risk-notes v489-proposal-queue-non-execution-audit v490-observation-proposal-queue-audit operator-governed-observation-proposal-queue-v1 mapping_is_approval=False proposal_candidate_is_execution_packet=False candidate_queue_is_authorization=False queue_presence_is_approval=False queue_ranking_is_authorization=False highest_ranked_proposal_auto_selected=False approved_for_packet_drafting_only_is_live_execution=False source_mutation_allowed=False memory_mutation_allowed=False schedule_creation_allowed=False model_invocation_by_default_allowed=False execution_packet_creation_allowed=False patch_application_allowed=False proposal_approval_allowed=False automatic_continuation_allowed=False observation_promotes_to_live_change=False operator_review_required=True fresh_operator_approval_required=True operator_approval_still_required=True


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v491-sandbox-only-autonomy-scope-definition","version":"v491.0","era":"sandbox-autonomy-boundary","dashboard_route":"/sandbox-only-autonomy-scope-definition","api_route":"/api/sandbox-only-autonomy-scope-definition/layer","cli_flag":"--sandbox-only-autonomy-scope-definition-v1","builder_function":"build_sandbox_only_autonomy_scope_definition_v1","text_function":"sandbox_only_autonomy_scope_definition_v1_text","runtime_directory":"data/autonomy/sandbox_only_autonomy_scope_definition/","smoke_check":"operator-governed-sandbox-autonomy-boundary-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v492-sandbox-autonomy-trial-packet-builder","version":"v492.0","era":"sandbox-autonomy-boundary","dashboard_route":"/sandbox-autonomy-trial-packet-builder","api_route":"/api/sandbox-autonomy-trial-packet-builder/layer","cli_flag":"--sandbox-autonomy-trial-packet-builder-v1","builder_function":"build_sandbox_autonomy_trial_packet_builder_v1","text_function":"sandbox_autonomy_trial_packet_builder_v1_text","runtime_directory":"data/autonomy/sandbox_autonomy_trial_packet_builder/","smoke_check":"operator-governed-sandbox-autonomy-boundary-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v493-sandbox-to-live-boundary-hardening","version":"v493.0","era":"sandbox-autonomy-boundary","dashboard_route":"/sandbox-to-live-boundary-hardening","api_route":"/api/sandbox-to-live-boundary-hardening/layer","cli_flag":"--sandbox-to-live-boundary-hardening-v1","builder_function":"build_sandbox_to_live_boundary_hardening_v1","text_function":"sandbox_to_live_boundary_hardening_v1_text","runtime_directory":"data/autonomy/sandbox_to_live_boundary_hardening/","smoke_check":"operator-governed-sandbox-autonomy-boundary-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v494-no-execution-sandbox-autonomy-audit","version":"v494.0","era":"sandbox-autonomy-boundary","dashboard_route":"/no-execution-sandbox-autonomy-audit","api_route":"/api/no-execution-sandbox-autonomy-audit/layer","cli_flag":"--no-execution-sandbox-autonomy-audit-v1","builder_function":"build_no_execution_sandbox_autonomy_audit_v1","text_function":"no_execution_sandbox_autonomy_audit_v1_text","runtime_directory":"data/autonomy/no_execution_sandbox_autonomy_audit/","smoke_check":"operator-governed-sandbox-autonomy-boundary-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v495-sandbox-autonomy-boundary-prep-audit","version":"v495.0","era":"sandbox-autonomy-boundary","dashboard_route":"/sandbox-autonomy-boundary-prep-audit","api_route":"/api/sandbox-autonomy-boundary-prep-audit/layer","cli_flag":"--operator-governed-sandbox-autonomy-boundary-prep-v1","builder_function":"build_operator_governed_sandbox_autonomy_boundary_prep_v1","text_function":"operator_governed_sandbox_autonomy_boundary_prep_v1_text","runtime_directory":"data/autonomy/sandbox_autonomy_boundary_prep_audit/","smoke_check":"operator-governed-sandbox-autonomy-boundary-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v490.1-v495.0 sandbox autonomy boundary manifest tokens: v491-sandbox-only-autonomy-scope-definition v492-sandbox-autonomy-trial-packet-builder v493-sandbox-to-live-boundary-hardening v494-no-execution-sandbox-autonomy-audit v495-sandbox-autonomy-boundary-prep-audit operator-governed-sandbox-autonomy-boundary-prep-v1 sandbox_scope_is_authorization=False sandbox_readiness_is_approval=False sandbox_target_description_is_permission_to_execute=False sandbox_success_is_live_authorization=False sandbox_verification_is_approval=False sandbox_output_is_patch_execution_packet=False sandbox_trial_completion_permits_source_mutation=False promotion_requires_fresh_single_use_operator_approval=True live_source_writes_allowed=False memory_writes_allowed=False real_patch_application_allowed=False release_candidate_creation_allowed=False automatic_scheduling_allowed=False local_model_invocation_by_default_allowed=False approval_creation_allowed=False sandbox_execution_allowed=False operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v496-autonomy-readiness-criteria-board","version":"v496.0","era":"autonomy-readiness-review-board","dashboard_route":"/autonomy-readiness-criteria-board","api_route":"/api/autonomy-readiness-criteria-board/layer","cli_flag":"--autonomy-readiness-criteria-board-v1","builder_function":"build_autonomy_readiness_criteria_board_v1","text_function":"autonomy_readiness_criteria_board_v1_text","runtime_directory":"data/autonomy/autonomy_readiness_criteria_board/","smoke_check":"operator-governed-autonomy-readiness-review-board-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v497-autonomy-blocker-gap-register","version":"v497.0","era":"autonomy-readiness-review-board","dashboard_route":"/autonomy-blocker-gap-register","api_route":"/api/autonomy-blocker-gap-register/layer","cli_flag":"--autonomy-blocker-gap-register-v1","builder_function":"build_autonomy_blocker_gap_register_v1","text_function":"autonomy_blocker_gap_register_v1_text","runtime_directory":"data/autonomy/autonomy_blocker_gap_register/","smoke_check":"operator-governed-autonomy-readiness-review-board-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v498-phase-based-autonomy-permission-model","version":"v498.0","era":"autonomy-readiness-review-board","dashboard_route":"/phase-based-autonomy-permission-model","api_route":"/api/phase-based-autonomy-permission-model/layer","cli_flag":"--phase-based-autonomy-permission-model-v1","builder_function":"build_phase_based_autonomy_permission_model_v1","text_function":"phase_based_autonomy_permission_model_v1_text","runtime_directory":"data/autonomy/phase_based_autonomy_permission_model/","smoke_check":"operator-governed-autonomy-readiness-review-board-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v499-autonomy-misinterpretation-firewall","version":"v499.0","era":"autonomy-readiness-review-board","dashboard_route":"/autonomy-misinterpretation-firewall","api_route":"/api/autonomy-misinterpretation-firewall/layer","cli_flag":"--autonomy-misinterpretation-firewall-v1","builder_function":"build_autonomy_misinterpretation_firewall_v1","text_function":"autonomy_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/autonomy_misinterpretation_firewall/","smoke_check":"operator-governed-autonomy-readiness-review-board-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v500-autonomy-readiness-review-board-audit","version":"v500.0","era":"autonomy-readiness-review-board","dashboard_route":"/autonomy-readiness-review-board-audit","api_route":"/api/autonomy-readiness-review-board-audit/layer","cli_flag":"--operator-governed-autonomy-readiness-review-board-v1","builder_function":"build_operator_governed_autonomy_readiness_review_board_v1","text_function":"operator_governed_autonomy_readiness_review_board_v1_text","runtime_directory":"data/autonomy/autonomy_readiness_review_board_audit/","smoke_check":"operator-governed-autonomy-readiness-review-board-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v495.1-v500.0 autonomy readiness review board manifest tokens: v496-autonomy-readiness-criteria-board v497-autonomy-blocker-gap-register v498-phase-based-autonomy-permission-model v499-autonomy-misinterpretation-firewall v500-autonomy-readiness-review-board-audit operator-governed-autonomy-readiness-review-board-v1 readiness_status=not_ready_for_autonomy authorization_status=not_authorized readiness_review_is_autonomy_approval=False board_pass_grants_authorization=False phase_definition_authorizes_phase=False sandbox_boundary_exists_means_execute=False operator_discussion_is_approval=False proposal_ranking_is_selection=False observation_history_authorizes_monitoring=False source_mutation_allowed=False memory_mutation_allowed=False schedule_creation_allowed=False model_invocation_by_default_allowed=False execution_packet_creation_allowed=False sandbox_execution_allowed=False live_source_writes_allowed=False approval_creation_allowed=False release_candidate_creation_allowed=False operator_approval_still_required=True


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v501-source-package-runtime-exclusion-map","version":"v501.0","era":"package-privacy-metadata-integrity","dashboard_route":"/source-package-runtime-exclusion-map","api_route":"/api/source-package-runtime-exclusion-map/layer","cli_flag":"--source-package-runtime-exclusion-map-v1","builder_function":"build_source_package_runtime_exclusion_map_v1","text_function":"source_package_runtime_exclusion_map_v1_text","runtime_directory":"data/autonomy/source_package_runtime_exclusion_map/","smoke_check":"operator-governed-source-package-privacy-metadata-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v502-final-archive-entry-privacy-checker","version":"v502.0","era":"package-privacy-metadata-integrity","dashboard_route":"/final-archive-entry-privacy-checker","api_route":"/api/final-archive-entry-privacy-checker/layer","cli_flag":"--final-archive-entry-privacy-checker-v1","builder_function":"build_final_archive_entry_privacy_checker_v1","text_function":"final_archive_entry_privacy_checker_v1_text","runtime_directory":"data/autonomy/final_archive_entry_privacy_checker/","smoke_check":"operator-governed-source-package-privacy-metadata-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v503-metadata-version-drift-normalizer","version":"v503.0","era":"package-privacy-metadata-integrity","dashboard_route":"/metadata-version-drift-normalizer","api_route":"/api/metadata-version-drift-normalizer/layer","cli_flag":"--metadata-version-drift-normalizer-v1","builder_function":"build_metadata_version_drift_normalizer_v1","text_function":"metadata_version_drift_normalizer_v1_text","runtime_directory":"data/autonomy/metadata_version_drift_normalizer/","smoke_check":"operator-governed-source-package-privacy-metadata-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v504-release-doc-command-compatibility-audit","version":"v504.0","era":"package-privacy-metadata-integrity","dashboard_route":"/release-doc-command-compatibility-audit","api_route":"/api/release-doc-command-compatibility-audit/layer","cli_flag":"--release-doc-command-compatibility-audit-v1","builder_function":"build_release_doc_command_compatibility_audit_v1","text_function":"release_doc_command_compatibility_audit_v1_text","runtime_directory":"data/autonomy/release_doc_command_compatibility_audit/","smoke_check":"operator-governed-source-package-privacy-metadata-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v505-source-package-privacy-metadata-integrity-audit","version":"v505.0","era":"package-privacy-metadata-integrity","dashboard_route":"/source-package-privacy-metadata-integrity-audit","api_route":"/api/source-package-privacy-metadata-integrity-audit/layer","cli_flag":"--operator-governed-source-package-privacy-metadata-integrity-v1","builder_function":"build_operator_governed_source_package_privacy_metadata_integrity_v1","text_function":"operator_governed_source_package_privacy_metadata_integrity_v1_text","runtime_directory":"data/autonomy/source_package_privacy_metadata_integrity_audit/","smoke_check":"operator-governed-source-package-privacy-metadata-integrity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

# v500.1-v505.0 source package privacy metadata integrity manifest tokens: v501-source-package-runtime-exclusion-map v502-final-archive-entry-privacy-checker v503-metadata-version-drift-normalizer v504-release-doc-command-compatibility-audit v505-source-package-privacy-metadata-integrity-audit operator-governed-source-package-privacy-metadata-integrity-v1 data/workspaces/timeline.json package_privacy_pass_is_authorization=False metadata_consistency_is_authorization=False zip_entry_privacy_pass_publishes_release=False documentation_cleanup_grants_approval=False source_package_repair_applies_live_patches=False source_package_repair_writes_memory=False source_package_repair_expands_autonomy=False source_package_repair_executes_sandbox=False authorizes_package_creation=False publishes_release=False operator_review_required=True fresh_operator_approval_still_required=True

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v506-observation-to-sandbox-intake-bridge","version":"v506.0","era":"manual-observation-to-sandbox-bridge","dashboard_route":"/observation-to-sandbox-intake-bridge","api_route":"/api/observation-to-sandbox-intake-bridge/layer","cli_flag":"--observation-to-sandbox-intake-bridge-v1","builder_function":"build_observation_to_sandbox_intake_bridge_v1","text_function":"observation_to_sandbox_intake_bridge_v1_text","runtime_directory":"data/autonomy/observation_to_sandbox_intake_bridge/","smoke_check":"manual-observation-to-sandbox-packet-bridge-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v507-sandbox-candidate-extraction","version":"v507.0","era":"manual-observation-to-sandbox-bridge","dashboard_route":"/sandbox-candidate-extraction","api_route":"/api/sandbox-candidate-extraction/layer","cli_flag":"--sandbox-candidate-extraction-v1","builder_function":"build_sandbox_candidate_extraction_v1","text_function":"sandbox_candidate_extraction_v1_text","runtime_directory":"data/autonomy/sandbox_candidate_extraction/","smoke_check":"manual-observation-to-sandbox-packet-bridge-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v508-sandbox-packet-draft-assembly","version":"v508.0","era":"manual-observation-to-sandbox-bridge","dashboard_route":"/sandbox-packet-draft-assembly","api_route":"/api/sandbox-packet-draft-assembly/layer","cli_flag":"--sandbox-packet-draft-assembly-v1","builder_function":"build_sandbox_packet_draft_assembly_v1","text_function":"sandbox_packet_draft_assembly_v1_text","runtime_directory":"data/autonomy/sandbox_packet_draft_assembly/","smoke_check":"manual-observation-to-sandbox-packet-bridge-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v509-sandbox-packet-misinterpretation-firewall","version":"v509.0","era":"manual-observation-to-sandbox-bridge","dashboard_route":"/sandbox-packet-misinterpretation-firewall","api_route":"/api/sandbox-packet-misinterpretation-firewall/layer","cli_flag":"--sandbox-packet-misinterpretation-firewall-v1","builder_function":"build_sandbox_packet_misinterpretation_firewall_v1","text_function":"sandbox_packet_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/sandbox_packet_misinterpretation_firewall/","smoke_check":"manual-observation-to-sandbox-packet-bridge-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v510-manual-observation-to-sandbox-bridge-audit","version":"v510.0","era":"manual-observation-to-sandbox-bridge","dashboard_route":"/manual-observation-to-sandbox-bridge-audit","api_route":"/api/manual-observation-to-sandbox-bridge-audit/layer","cli_flag":"--manual-observation-to-sandbox-packet-bridge-v1","builder_function":"build_manual_observation_to_sandbox_packet_bridge_v1","text_function":"manual_observation_to_sandbox_packet_bridge_v1_text","runtime_directory":"data/autonomy/manual_observation_to_sandbox_bridge_audit/","smoke_check":"manual-observation-to-sandbox-packet-bridge-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v511-sandbox-approval-scope-contract","version":"v511.0","era":"sandbox-execution-approval-gate","dashboard_route":"/sandbox-approval-scope-contract","api_route":"/api/sandbox-approval-scope-contract/layer","cli_flag":"--sandbox-approval-scope-contract-v1","builder_function":"build_sandbox_approval_scope_contract_v1","text_function":"sandbox_approval_scope_contract_v1_text","runtime_directory":"data/autonomy/sandbox_approval_scope_contract/","smoke_check":"sandbox-execution-approval-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":False,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v512-exact-confirmation-phrase-builder","version":"v512.0","era":"sandbox-execution-approval-gate","dashboard_route":"/exact-confirmation-phrase-builder","api_route":"/api/exact-confirmation-phrase-builder/layer","cli_flag":"--exact-confirmation-phrase-builder-v1","builder_function":"build_exact_confirmation_phrase_builder_v1","text_function":"exact_confirmation_phrase_builder_v1_text","runtime_directory":"data/autonomy/exact_confirmation_phrase_builder/","smoke_check":"sandbox-execution-approval-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v513-approval-burnout-expiry-ledger","version":"v513.0","era":"sandbox-execution-approval-gate","dashboard_route":"/approval-burnout-expiry-ledger","api_route":"/api/approval-burnout-expiry-ledger/layer","cli_flag":"--approval-burnout-expiry-ledger-v1","builder_function":"build_approval_burnout_expiry_ledger_v1","text_function":"approval_burnout_expiry_ledger_v1_text","runtime_directory":"data/autonomy/approval_burnout_expiry_ledger/","smoke_check":"sandbox-execution-approval-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v514-sandbox-command-allowlist-preview","version":"v514.0","era":"sandbox-execution-approval-gate","dashboard_route":"/sandbox-command-allowlist-preview","api_route":"/api/sandbox-command-allowlist-preview/layer","cli_flag":"--sandbox-command-allowlist-preview-v1","builder_function":"build_sandbox_command_allowlist_preview_v1","text_function":"sandbox_command_allowlist_preview_v1_text","runtime_directory":"data/autonomy/sandbox_command_allowlist_preview/","smoke_check":"sandbox-execution-approval-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v515-sandbox-execution-approval-gate-audit","version":"v515.0","era":"sandbox-execution-approval-gate","dashboard_route":"/sandbox-execution-approval-gate-audit","api_route":"/api/sandbox-execution-approval-gate-audit/layer","cli_flag":"--sandbox-execution-approval-gate-v1","builder_function":"build_sandbox_execution_approval_gate_v1","text_function":"sandbox_execution_approval_gate_v1_text","runtime_directory":"data/autonomy/sandbox_execution_approval_gate_audit/","smoke_check":"sandbox-execution-approval-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v516-sandbox-dry-run-execution-model","version":"v516.0","era":"sandbox-execution-dry-run-receipt","dashboard_route":"/sandbox-dry-run-execution-model","api_route":"/api/sandbox-dry-run-execution-model/layer","cli_flag":"--sandbox-dry-run-execution-model-v1","builder_function":"build_sandbox_dry_run_execution_model_v1","text_function":"sandbox_dry_run_execution_model_v1_text","runtime_directory":"data/autonomy/sandbox_dry_run_execution_model/","smoke_check":"sandbox-execution-dry-run-receipt-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v517-command-transcript-preview","version":"v517.0","era":"sandbox-execution-dry-run-receipt","dashboard_route":"/command-transcript-preview","api_route":"/api/command-transcript-preview/layer","cli_flag":"--command-transcript-preview-v1","builder_function":"build_command_transcript_preview_v1","text_function":"command_transcript_preview_v1_text","runtime_directory":"data/autonomy/command_transcript_preview/","smoke_check":"sandbox-execution-dry-run-receipt-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v518-sandbox-diff-receipt-preview","version":"v518.0","era":"sandbox-execution-dry-run-receipt","dashboard_route":"/sandbox-diff-receipt-preview","api_route":"/api/sandbox-diff-receipt-preview/layer","cli_flag":"--sandbox-diff-receipt-preview-v1","builder_function":"build_sandbox_diff_receipt_preview_v1","text_function":"sandbox_diff_receipt_preview_v1_text","runtime_directory":"data/autonomy/sandbox_diff_receipt_preview/","smoke_check":"sandbox-execution-dry-run-receipt-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v519-dry-run-misinterpretation-firewall","version":"v519.0","era":"sandbox-execution-dry-run-receipt","dashboard_route":"/dry-run-misinterpretation-firewall","api_route":"/api/dry-run-misinterpretation-firewall/layer","cli_flag":"--dry-run-misinterpretation-firewall-v1","builder_function":"build_dry_run_misinterpretation_firewall_v1","text_function":"dry_run_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/dry_run_misinterpretation_firewall/","smoke_check":"sandbox-execution-dry-run-receipt-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v520-sandbox-execution-dry-run-receipt-audit","version":"v520.0","era":"sandbox-execution-dry-run-receipt","dashboard_route":"/sandbox-execution-dry-run-receipt-audit","api_route":"/api/sandbox-execution-dry-run-receipt-audit/layer","cli_flag":"--sandbox-execution-dry-run-receipt-v1","builder_function":"build_sandbox_execution_dry_run_receipt_v1","text_function":"sandbox_execution_dry_run_receipt_v1_text","runtime_directory":"data/autonomy/sandbox_execution_dry_run_receipt_audit/","smoke_check":"sandbox-execution-dry-run-receipt-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":False,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v521-sandbox-workspace-isolation-contract","version":"v521.0","era":"first-sandbox-execution-trial","dashboard_route":"/sandbox-workspace-isolation-contract","api_route":"/api/sandbox-workspace-isolation-contract/layer","cli_flag":"--sandbox-workspace-isolation-contract-v1","builder_function":"build_sandbox_workspace_isolation_contract_v1","text_function":"sandbox_workspace_isolation_contract_v1_text","runtime_directory":"data/autonomy/sandbox_workspace_isolation_contract/","smoke_check":"first-operator-approved-sandbox-execution-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v522-approved-sandbox-command-plan","version":"v522.0","era":"first-sandbox-execution-trial","dashboard_route":"/approved-sandbox-command-plan","api_route":"/api/approved-sandbox-command-plan/layer","cli_flag":"--approved-sandbox-command-plan-v1","builder_function":"build_approved_sandbox_command_plan_v1","text_function":"approved_sandbox_command_plan_v1_text","runtime_directory":"data/autonomy/approved_sandbox_command_plan/","smoke_check":"first-operator-approved-sandbox-execution-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v523-single-use-sandbox-execution-receipt","version":"v523.0","era":"first-sandbox-execution-trial","dashboard_route":"/single-use-sandbox-execution-receipt","api_route":"/api/single-use-sandbox-execution-receipt/layer","cli_flag":"--single-use-sandbox-execution-receipt-v1","builder_function":"build_single_use_sandbox_execution_receipt_v1","text_function":"single_use_sandbox_execution_receipt_v1_text","runtime_directory":"data/autonomy/single_use_sandbox_execution_receipt/","smoke_check":"first-operator-approved-sandbox-execution-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v524-sandbox-execution-misinterpretation-firewall","version":"v524.0","era":"first-sandbox-execution-trial","dashboard_route":"/sandbox-execution-misinterpretation-firewall","api_route":"/api/sandbox-execution-misinterpretation-firewall/layer","cli_flag":"--sandbox-execution-misinterpretation-firewall-v1","builder_function":"build_sandbox_execution_misinterpretation_firewall_v1","text_function":"sandbox_execution_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/sandbox_execution_misinterpretation_firewall/","smoke_check":"first-operator-approved-sandbox-execution-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v525-first-sandbox-execution-trial-audit","version":"v525.0","era":"first-sandbox-execution-trial","dashboard_route":"/first-sandbox-execution-trial-audit","api_route":"/api/first-sandbox-execution-trial-audit/layer","cli_flag":"--first-operator-approved-sandbox-execution-trial-v1","builder_function":"build_first_operator_approved_sandbox_execution_trial_v1","text_function":"first_operator_approved_sandbox_execution_trial_v1_text","runtime_directory":"data/autonomy/first_sandbox_execution_trial_audit/","smoke_check":"first-operator-approved-sandbox-execution-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])


# v505.1-v510.0 manual observation-to-sandbox bridge manifest tokens: v506-observation-to-sandbox-intake-bridge v507-sandbox-candidate-extraction v508-sandbox-packet-draft-assembly v509-sandbox-packet-misinterpretation-firewall v510-manual-observation-to-sandbox-bridge-audit manual-observation-to-sandbox-packet-bridge-v1 observation_report_is_approval=False candidate_found_is_candidate_selected=False sandbox_packet_exists_is_execution_permission=False packet_assembly_executes_sandbox=False bridge_status=prepared authorization_status=not_authorized execution_status=not_executed autonomy_status=not_autonomous

# v510.1-v515.0 sandbox execution approval gate manifest tokens: v511-sandbox-approval-scope-contract v512-exact-confirmation-phrase-builder v513-approval-burnout-expiry-ledger v514-sandbox-command-allowlist-preview v515-sandbox-execution-approval-gate-audit sandbox-execution-approval-gate-v1 approval_contract_exists_is_approval_granted=False confirmation_phrase_generated_is_confirmation_entered=False command_preview_executes_commands=False approval_gate_status=defined approval_status=not_granted authorization_status=not_authorized execution_status=not_executed sandbox_status=not_started autonomy_status=not_autonomous

# v515.1-v520.0 sandbox execution dry-run receipt manifest tokens: v516-sandbox-dry-run-execution-model v517-command-transcript-preview v518-sandbox-diff-receipt-preview v519-dry-run-misinterpretation-firewall v520-sandbox-execution-dry-run-receipt-audit sandbox-execution-dry-run-receipt-v1 dry_run_model_exists_is_sandbox_execution=False transcript_preview_is_command_output=False diff_receipt_preview_is_actual_file_change=False dry_run_success_is_authorization=False dry_run_receipt_status=prepared actual_execution_status=not_executed approval_status=not_granted authorization_status=not_authorized sandbox_status=not_started autonomy_status=not_autonomous

# v520.1-v525.0 first sandbox execution trial manifest tokens: v521-sandbox-workspace-isolation-contract v522-approved-sandbox-command-plan v523-single-use-sandbox-execution-receipt v524-sandbox-execution-misinterpretation-firewall v525-first-sandbox-execution-trial-audit first-operator-approved-sandbox-execution-trial-v1 trial_layer_status=prepared sandbox_execution_status=not_run_by_default approval_status=required live_source_status=untouched memory_status=untouched autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v526-sandbox-execution-runner-contract","version":"v526.0","era":"sandbox-execution-runner","dashboard_route":"/sandbox-execution-runner-contract","api_route":"/api/sandbox-execution-runner-contract/layer","cli_flag":"--sandbox-execution-runner-contract-v1","builder_function":"build_sandbox_execution_runner_contract_v1","text_function":"sandbox_execution_runner_contract_v1_text","runtime_directory":"data/autonomy/sandbox_execution_runner_contract/","smoke_check":"operator-approved-sandbox-execution-runner-v1","smoke_segment":"install-governance","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v527-approval-phrase-validator","version":"v527.0","era":"sandbox-execution-runner","dashboard_route":"/approval-phrase-validator","api_route":"/api/approval-phrase-validator/layer","cli_flag":"--approval-phrase-validator-v1","builder_function":"build_approval_phrase_validator_v1","text_function":"approval_phrase_validator_v1_text","runtime_directory":"data/autonomy/approval_phrase_validator/","smoke_check":"operator-approved-sandbox-execution-runner-v1","smoke_segment":"install-governance","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v528-sandbox-command-execution-harness","version":"v528.0","era":"sandbox-execution-runner","dashboard_route":"/sandbox-command-execution-harness","api_route":"/api/sandbox-command-execution-harness/layer","cli_flag":"--sandbox-command-execution-harness-v1","builder_function":"build_sandbox_command_execution_harness_v1","text_function":"sandbox_command_execution_harness_v1_text","runtime_directory":"data/autonomy/sandbox_command_execution_harness/","smoke_check":"operator-approved-sandbox-execution-runner-v1","smoke_segment":"install-governance","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v529-execution-receipt-intake-cleanup-audit","version":"v529.0","era":"sandbox-execution-runner","dashboard_route":"/execution-receipt-intake-cleanup-audit","api_route":"/api/execution-receipt-intake-cleanup-audit/layer","cli_flag":"--execution-receipt-intake-cleanup-audit-v1","builder_function":"build_execution_receipt_intake_cleanup_audit_v1","text_function":"execution_receipt_intake_cleanup_audit_v1_text","runtime_directory":"data/autonomy/execution_receipt_intake_cleanup_audit/","smoke_check":"operator-approved-sandbox-execution-runner-v1","smoke_segment":"install-governance","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v530-sandbox-execution-trial-review-board","version":"v530.0","era":"sandbox-execution-runner","dashboard_route":"/sandbox-execution-trial-review-board","api_route":"/api/sandbox-execution-trial-review-board/layer","cli_flag":"--operator-approved-sandbox-execution-runner-v1","builder_function":"build_operator_approved_sandbox_execution_runner_v1","text_function":"operator_approved_sandbox_execution_runner_v1_text","runtime_directory":"data/autonomy/sandbox_execution_trial_review_board/","smoke_check":"operator-approved-sandbox-execution-runner-v1","smoke_segment":"install-governance","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v525.1-v530.0 sandbox execution runner manifest tokens: v526-sandbox-execution-runner-contract v527-approval-phrase-validator v528-sandbox-command-execution-harness v529-execution-receipt-intake-cleanup-audit v530-sandbox-execution-trial-review-board operator-approved-sandbox-execution-runner-v1 runner_status=available_under_approval_only execution_status=not_executed_by_default approval_status=required live_source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v531-sandbox-evidence-intake-packet","version":"v531.0","era":"sandbox-to-source-promotion-packet","dashboard_route":"/sandbox-evidence-intake-packet","api_route":"/api/sandbox-evidence-intake-packet/layer","cli_flag":"--sandbox-evidence-intake-packet-v1","builder_function":"build_sandbox_evidence_intake_packet_v1","text_function":"sandbox_evidence_intake_packet_v1_text","runtime_directory":"data/autonomy/sandbox_evidence_intake_packet/","smoke_check":"sandbox-to-source-promotion-packet-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v532-promotion-candidate-diff-preview","version":"v532.0","era":"sandbox-to-source-promotion-packet","dashboard_route":"/promotion-candidate-diff-preview","api_route":"/api/promotion-candidate-diff-preview/layer","cli_flag":"--promotion-candidate-diff-preview-v1","builder_function":"build_promotion_candidate_diff_preview_v1","text_function":"promotion_candidate_diff_preview_v1_text","runtime_directory":"data/autonomy/promotion_candidate_diff_preview/","smoke_check":"sandbox-to-source-promotion-packet-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v533-rollback-recovery-packet-builder","version":"v533.0","era":"sandbox-to-source-promotion-packet","dashboard_route":"/rollback-recovery-packet-builder","api_route":"/api/rollback-recovery-packet-builder/layer","cli_flag":"--rollback-recovery-packet-builder-v1","builder_function":"build_rollback_recovery_packet_builder_v1","text_function":"rollback_recovery_packet_builder_v1_text","runtime_directory":"data/autonomy/rollback_recovery_packet_builder/","smoke_check":"sandbox-to-source-promotion-packet-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v534-promotion-misinterpretation-firewall","version":"v534.0","era":"sandbox-to-source-promotion-packet","dashboard_route":"/promotion-misinterpretation-firewall","api_route":"/api/promotion-misinterpretation-firewall/layer","cli_flag":"--promotion-misinterpretation-firewall-v1","builder_function":"build_promotion_misinterpretation_firewall_v1","text_function":"promotion_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/promotion_misinterpretation_firewall/","smoke_check":"sandbox-to-source-promotion-packet-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v535-sandbox-to-source-promotion-review-board","version":"v540.0","era":"sandbox-to-source-promotion-packet","dashboard_route":"/sandbox-to-source-promotion-review-board","api_route":"/api/sandbox-to-source-promotion-review-board/layer","cli_flag":"--sandbox-to-source-promotion-packet-v1","builder_function":"build_sandbox_to_source_promotion_packet_v1","text_function":"sandbox_to_source_promotion_packet_v1_text","runtime_directory":"data/autonomy/sandbox_to_source_promotion_review_board/","smoke_check":"sandbox-to-source-promotion-packet-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v530.1-v540.0 sandbox-to-source promotion packet manifest tokens: v531-sandbox-evidence-intake-packet v532-promotion-candidate-diff-preview v533-rollback-recovery-packet-builder v534-promotion-misinterpretation-firewall v535-sandbox-to-source-promotion-review-board sandbox-to-source-promotion-packet-v1 promotion_packet_status=prepared live_source_status=untouched approval_status=required rollback_status=planned_not_executed release_status=not_created autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v536-narrow-live-patch-scope-contract","version":"v536.0","era":"narrow-live-patch-promotion-gate","dashboard_route":"/narrow-live-patch-scope-contract","api_route":"/api/narrow-live-patch-scope-contract/layer","cli_flag":"--narrow-live-patch-scope-contract-v1","builder_function":"build_narrow_live_patch_scope_contract_v1","text_function":"narrow_live_patch_scope_contract_v1_text","runtime_directory":"data/autonomy/narrow_live_patch_scope_contract/","smoke_check":"operator-approved-narrow-live-patch-promotion-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v537-promotion-approval-phrase-contract","version":"v537.0","era":"narrow-live-patch-promotion-gate","dashboard_route":"/promotion-approval-phrase-contract","api_route":"/api/promotion-approval-phrase-contract/layer","cli_flag":"--promotion-approval-phrase-contract-v1","builder_function":"build_promotion_approval_phrase_contract_v1","text_function":"promotion_approval_phrase_contract_v1_text","runtime_directory":"data/autonomy/promotion_approval_phrase_contract/","smoke_check":"operator-approved-narrow-live-patch-promotion-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v538-live-patch-preflight-checklist","version":"v538.0","era":"narrow-live-patch-promotion-gate","dashboard_route":"/live-patch-preflight-checklist","api_route":"/api/live-patch-preflight-checklist/layer","cli_flag":"--live-patch-preflight-checklist-v1","builder_function":"build_live_patch_preflight_checklist_v1","text_function":"live_patch_preflight_checklist_v1_text","runtime_directory":"data/autonomy/live_patch_preflight_checklist/","smoke_check":"operator-approved-narrow-live-patch-promotion-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v539-live-promotion-misinterpretation-firewall","version":"v539.0","era":"narrow-live-patch-promotion-gate","dashboard_route":"/live-promotion-misinterpretation-firewall","api_route":"/api/live-promotion-misinterpretation-firewall/layer","cli_flag":"--live-promotion-misinterpretation-firewall-v1","builder_function":"build_live_promotion_misinterpretation_firewall_v1","text_function":"live_promotion_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/live_promotion_misinterpretation_firewall/","smoke_check":"operator-approved-narrow-live-patch-promotion-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v540-narrow-live-patch-promotion-gate-audit","version":"v540.0","era":"narrow-live-patch-promotion-gate","dashboard_route":"/narrow-live-patch-promotion-gate-audit","api_route":"/api/narrow-live-patch-promotion-gate-audit/layer","cli_flag":"--operator-approved-narrow-live-patch-promotion-gate-v1","builder_function":"build_operator_approved_narrow_live_patch_promotion_gate_v1","text_function":"operator_approved_narrow_live_patch_promotion_gate_v1_text","runtime_directory":"data/autonomy/narrow_live_patch_promotion_gate_audit/","smoke_check":"operator-approved-narrow-live-patch-promotion-gate-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v535.1-v540.0 narrow live patch promotion gate manifest tokens: v536-narrow-live-patch-scope-contract v537-promotion-approval-phrase-contract v538-live-patch-preflight-checklist v539-live-promotion-misinterpretation-firewall v540-narrow-live-patch-promotion-gate-audit operator-approved-narrow-live-patch-promotion-gate-v1 live_patch_scope_defined_is_live_patch_approved=False approval_phrase_template_is_operator_approval=False preflight_pass_is_live_patch_permission=False live_patch_gate_status=defined live_patch_status=not_applied approval_status=required source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v541-live-patch-trial-candidate-selector","version":"v541.0","era":"first-narrow-live-patch-application-trial","dashboard_route":"/live-patch-trial-candidate-selector","api_route":"/api/live-patch-trial-candidate-selector/layer","cli_flag":"--live-patch-trial-candidate-selector-v1","builder_function":"build_live_patch_trial_candidate_selector_v1","text_function":"live_patch_trial_candidate_selector_v1_text","runtime_directory":"data/autonomy/live_patch_trial_candidate_selector/","smoke_check":"first-single-use-narrow-live-patch-application-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v542-single-use-live-patch-approval-receipt","version":"v542.0","era":"first-narrow-live-patch-application-trial","dashboard_route":"/single-use-live-patch-approval-receipt","api_route":"/api/single-use-live-patch-approval-receipt/layer","cli_flag":"--single-use-live-patch-approval-receipt-v1","builder_function":"build_single_use_live_patch_approval_receipt_v1","text_function":"single_use_live_patch_approval_receipt_v1_text","runtime_directory":"data/autonomy/single_use_live_patch_approval_receipt/","smoke_check":"first-single-use-narrow-live-patch-application-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v543-live-patch-application-harness-preview","version":"v543.0","era":"first-narrow-live-patch-application-trial","dashboard_route":"/live-patch-application-harness-preview","api_route":"/api/live-patch-application-harness-preview/layer","cli_flag":"--live-patch-application-harness-preview-v1","builder_function":"build_live_patch_application_harness_preview_v1","text_function":"live_patch_application_harness_preview_v1_text","runtime_directory":"data/autonomy/live_patch_application_harness_preview/","smoke_check":"first-single-use-narrow-live-patch-application-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v544-live-patch-application-misinterpretation-firewall","version":"v544.0","era":"first-narrow-live-patch-application-trial","dashboard_route":"/live-patch-application-misinterpretation-firewall","api_route":"/api/live-patch-application-misinterpretation-firewall/layer","cli_flag":"--live-patch-application-misinterpretation-firewall-v1","builder_function":"build_live_patch_application_misinterpretation_firewall_v1","text_function":"live_patch_application_misinterpretation_firewall_v1_text","runtime_directory":"data/autonomy/live_patch_application_misinterpretation_firewall/","smoke_check":"first-single-use-narrow-live-patch-application-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v545-first-narrow-live-patch-trial-audit","version":"v545.0","era":"first-narrow-live-patch-application-trial","dashboard_route":"/first-narrow-live-patch-trial-audit","api_route":"/api/first-narrow-live-patch-trial-audit/layer","cli_flag":"--first-single-use-narrow-live-patch-application-trial-v1","builder_function":"build_first_single_use_narrow_live_patch_application_trial_v1","text_function":"first_single_use_narrow_live_patch_application_trial_v1_text","runtime_directory":"data/autonomy/first_narrow_live_patch_trial_audit/","smoke_check":"first-single-use-narrow-live-patch-application-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v540.1-v545.0 first narrow live patch application trial manifest tokens: v541-live-patch-trial-candidate-selector v542-single-use-live-patch-approval-receipt v543-live-patch-application-harness-preview v544-live-patch-application-misinterpretation-firewall v545-first-narrow-live-patch-trial-audit first-single-use-narrow-live-patch-application-trial-v1 candidate_selected_is_live_patch_approved=False approval_receipt_template_is_approval_granted=False application_harness_exists_is_patch_applied=False trial_status=prepared live_patch_status=not_applied_by_default approval_status=required source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v546-current-version-source-of-truth-contract","version":"v546.0","era":"current-version-staleness-post-patch-verification","dashboard_route":"/current-version-source-of-truth-contract","api_route":"/api/current-version-source-of-truth-contract/layer","cli_flag":"--current-version-source-of-truth-contract-v1","builder_function":"build_current_version_source_of_truth_contract_v1","text_function":"current_version_source_of_truth_contract_v1_text","runtime_directory":"data/autonomy/current_version_source_of_truth_contract/","smoke_check":"current-version-staleness-and-post-patch-verification-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v547-stale-version-string-scanner","version":"v547.0","era":"current-version-staleness-post-patch-verification","dashboard_route":"/stale-version-string-scanner","api_route":"/api/stale-version-string-scanner/layer","cli_flag":"--stale-version-string-scanner-v1","builder_function":"build_stale_version_string_scanner_v1","text_function":"stale_version_string_scanner_v1_text","runtime_directory":"data/autonomy/stale_version_string_scanner/","smoke_check":"current-version-staleness-and-post-patch-verification-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v548-stale-milestone-title-drift-audit","version":"v548.0","era":"current-version-staleness-post-patch-verification","dashboard_route":"/stale-milestone-title-drift-audit","api_route":"/api/stale-milestone-title-drift-audit/layer","cli_flag":"--stale-milestone-title-drift-audit-v1","builder_function":"build_stale_milestone_title_drift_audit_v1","text_function":"stale_milestone_title_drift_audit_v1_text","runtime_directory":"data/autonomy/stale_milestone_title_drift_audit/","smoke_check":"current-version-staleness-and-post-patch-verification-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v549-post-live-patch-verification-prep","version":"v549.0","era":"current-version-staleness-post-patch-verification","dashboard_route":"/post-live-patch-verification-prep","api_route":"/api/post-live-patch-verification-prep/layer","cli_flag":"--post-live-patch-verification-prep-v1","builder_function":"build_post_live_patch_verification_prep_v1","text_function":"post_live_patch_verification_prep_v1_text","runtime_directory":"data/autonomy/post_live_patch_verification_prep/","smoke_check":"current-version-staleness-and-post-patch-verification-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v550-release-staleness-verification-audit-board","version":"v550.0","era":"current-version-staleness-post-patch-verification","dashboard_route":"/release-staleness-verification-audit-board","api_route":"/api/release-staleness-verification-audit-board/layer","cli_flag":"--current-version-staleness-and-post-patch-verification-v1","builder_function":"build_current_version_staleness_and_post_patch_verification_v1","text_function":"current_version_staleness_and_post_patch_verification_v1_text","runtime_directory":"data/autonomy/release_staleness_verification_audit_board/","smoke_check":"current-version-staleness-and-post-patch-verification-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v551-post-live-patch-evidence-intake-contract","version":"v551.0","era":"post-live-patch-verification-rollback-trial","dashboard_route":"/post-live-patch-evidence-intake-contract","api_route":"/api/post-live-patch-evidence-intake-contract/layer","cli_flag":"--post-live-patch-evidence-intake-contract-v1","builder_function":"build_post_live_patch_evidence_intake_contract_v1","text_function":"post_live_patch_evidence_intake_contract_v1_text","runtime_directory":"data/autonomy/post_live_patch_evidence_intake_contract/","smoke_check":"post-live-patch-evidence-intake-contract-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v545.1-v550.0 current version staleness manifest tokens: v546-current-version-source-of-truth-contract v547-stale-version-string-scanner v548-stale-milestone-title-drift-audit v549-post-live-patch-verification-prep v550-release-staleness-verification-audit-board current-version-staleness-and-post-patch-verification-v1 historical_version_references_are_blocked=False current_state_stale_references_are_allowed=False matching_version_marker_alone_is_metadata_integrity=False verification_plan_exists_is_patch_applied=False stale_version_audit_status=clean_or_blocked metadata_current_state_status=aligned_or_blocked post_patch_verification_status=prepared live_patch_status=not_applied_by_default approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous

# v550.1-v551.0 evidence intake manifest tokens: v551-post-live-patch-evidence-intake-contract post-live-patch-evidence-intake-contract expanded-current-symbol-staleness-audit post-live-patch-evidence-intake-contract-v1 evidence_presence_is_verification_success=False evidence_intake_executes_commands=False evidence_intake_applies_patches=False evidence_intake_executes_rollback=False stale_version_audit_status=clean_or_blocked evidence_intake_status=awaiting_operator_supplied_evidence verification_receipt_status=not_supplied rollback_status=not_executed approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v552-verification-receipt-review-layer","version":"v552.0","era":"post-live-patch-verification-rollback-trial","dashboard_route":"/verification-receipt-review-layer","api_route":"/api/verification-receipt-review-layer/layer","cli_flag":"--verification-receipt-review-layer-v1","builder_function":"build_verification_receipt_review_layer_v1","text_function":"verification_receipt_review_layer_v1_text","runtime_directory":"data/autonomy/verification_receipt_review_layer/","smoke_check":"post-live-patch-verification-and-rollback-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v553-rollback-snapshot-validity-review","version":"v553.0","era":"post-live-patch-verification-rollback-trial","dashboard_route":"/rollback-snapshot-validity-review","api_route":"/api/rollback-snapshot-validity-review/layer","cli_flag":"--rollback-snapshot-validity-review-v1","builder_function":"build_rollback_snapshot_validity_review_v1","text_function":"rollback_snapshot_validity_review_v1_text","runtime_directory":"data/autonomy/rollback_snapshot_validity_review/","smoke_check":"post-live-patch-verification-and-rollback-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v554-post-patch-regression-staleness-audit-board","version":"v554.0","era":"post-live-patch-verification-rollback-trial","dashboard_route":"/post-patch-regression-staleness-audit-board","api_route":"/api/post-patch-regression-staleness-audit-board/layer","cli_flag":"--post-patch-regression-staleness-audit-board-v1","builder_function":"build_post_patch_regression_staleness_audit_board_v1","text_function":"post_patch_regression_staleness_audit_board_v1_text","runtime_directory":"data/autonomy/post_patch_regression_staleness_audit_board/","smoke_check":"post-live-patch-verification-and-rollback-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v555-post-live-patch-verification-rollback-trial","version":"v555.0","era":"post-live-patch-verification-rollback-trial","dashboard_route":"/post-live-patch-verification-rollback-trial","api_route":"/api/post-live-patch-verification-rollback-trial/layer","cli_flag":"--post-live-patch-verification-rollback-trial-v1","builder_function":"build_post_live_patch_verification_rollback_trial_v1","text_function":"post_live_patch_verification_rollback_trial_v1_text","runtime_directory":"data/autonomy/post_live_patch_verification_rollback_trial/","smoke_check":"post-live-patch-verification-and-rollback-trial-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v552.0-v555.0 post live patch verification rollback manifest tokens: v552-verification-receipt-review-layer v553-rollback-snapshot-validity-review v554-post-patch-regression-staleness-audit-board v555-post-live-patch-verification-rollback-trial post-live-patch-verification-and-rollback-trial-v1 receipt_review_does_not_execute_commands=True rollback_plan_is_rollback_execution=False regression_audit_pass_is_release_approval=False trial_board_is_autonomy_approval=False verification_receipt_status=awaiting_operator_supplied_evidence rollback_status=planned_not_executed approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v556-recovery-drill-scope-contract","version":"v556.0","era":"recovery-drill-release-closure","dashboard_route":"/recovery-drill-scope-contract","api_route":"/api/recovery-drill-scope-contract/layer","cli_flag":"--recovery-drill-scope-contract-v1","builder_function":"build_recovery_drill_scope_contract_v1","text_function":"recovery_drill_scope_contract_v1_text","runtime_directory":"data/autonomy/recovery_drill_scope_contract/","smoke_check":"recovery-drill-and-release-closure-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v557-rollback-decision-review-packet","version":"v557.0","era":"recovery-drill-release-closure","dashboard_route":"/rollback-decision-review-packet","api_route":"/api/rollback-decision-review-packet/layer","cli_flag":"--rollback-decision-review-packet-v1","builder_function":"build_rollback_decision_review_packet_v1","text_function":"rollback_decision_review_packet_v1_text","runtime_directory":"data/autonomy/rollback_decision_review_packet/","smoke_check":"recovery-drill-and-release-closure-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v558-release-closure-evidence-board","version":"v558.0","era":"recovery-drill-release-closure","dashboard_route":"/release-closure-evidence-board","api_route":"/api/release-closure-evidence-board/layer","cli_flag":"--release-closure-evidence-board-v1","builder_function":"build_release_closure_evidence_board_v1","text_function":"release_closure_evidence_board_v1_text","runtime_directory":"data/autonomy/release_closure_evidence_board/","smoke_check":"recovery-drill-and-release-closure-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v559-operator-closure-approval-gate","version":"v559.0","era":"recovery-drill-release-closure","dashboard_route":"/operator-closure-approval-gate","api_route":"/api/operator-closure-approval-gate/layer","cli_flag":"--operator-closure-approval-gate-v1","builder_function":"build_operator_closure_approval_gate_v1","text_function":"operator_closure_approval_gate_v1_text","runtime_directory":"data/autonomy/operator_closure_approval_gate/","smoke_check":"recovery-drill-and-release-closure-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v560-recovery-drill-release-closure-board","version":"v565.0","era":"recovery-drill-release-closure","dashboard_route":"/recovery-drill-release-closure-board","api_route":"/api/recovery-drill-release-closure-board/layer","cli_flag":"--recovery-drill-release-closure-board-v1","builder_function":"build_recovery_drill_release_closure_board_v1","text_function":"recovery_drill_release_closure_board_v1_text","runtime_directory":"data/autonomy/recovery_drill_release_closure_board/","smoke_check":"recovery-drill-and-release-closure-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v556.0-v565.0 recovery drill release closure manifest tokens: v556-recovery-drill-scope-contract v557-rollback-decision-review-packet v558-release-closure-evidence-board v559-operator-closure-approval-gate v560-recovery-drill-release-closure-board recovery-drill-and-release-closure-v1 recovery_drill_status=prepared_not_executed rollback_decision_status=review_prepared release_closure_status=evidence_prepared closure_approval_status=required recovery_board_is_rollback_permission=False recovery_board_is_release_approval=False recovery_board_executes_commands=False recovery_board_executes_rollback=False approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v561-release-candidate-scope-contract","version":"v561.0","era":"release-candidate-operator-handoff","dashboard_route":"/release-candidate-scope-contract","api_route":"/api/release-candidate-scope-contract/layer","cli_flag":"--release-candidate-scope-contract-v1","builder_function":"build_release_candidate_scope_contract_v1","text_function":"release_candidate_scope_contract_v1_text","runtime_directory":"data/autonomy/release_candidate_scope_contract/","smoke_check":"release-candidate-integrity-and-operator-handoff-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v562-candidate-package-integrity-review","version":"v562.0","era":"release-candidate-operator-handoff","dashboard_route":"/candidate-package-integrity-review","api_route":"/api/candidate-package-integrity-review/layer","cli_flag":"--candidate-package-integrity-review-v1","builder_function":"build_candidate_package_integrity_review_v1","text_function":"candidate_package_integrity_review_v1_text","runtime_directory":"data/autonomy/candidate_package_integrity_review/","smoke_check":"release-candidate-integrity-and-operator-handoff-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v563-candidate-verification-evidence-matrix","version":"v563.0","era":"release-candidate-operator-handoff","dashboard_route":"/candidate-verification-evidence-matrix","api_route":"/api/candidate-verification-evidence-matrix/layer","cli_flag":"--candidate-verification-evidence-matrix-v1","builder_function":"build_candidate_verification_evidence_matrix_v1","text_function":"candidate_verification_evidence_matrix_v1_text","runtime_directory":"data/autonomy/candidate_verification_evidence_matrix/","smoke_check":"release-candidate-integrity-and-operator-handoff-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v564-operator-release-handoff-packet","version":"v564.0","era":"release-candidate-operator-handoff","dashboard_route":"/operator-release-handoff-packet","api_route":"/api/operator-release-handoff-packet/layer","cli_flag":"--operator-release-handoff-packet-v1","builder_function":"build_operator_release_handoff_packet_v1","text_function":"operator_release_handoff_packet_v1_text","runtime_directory":"data/autonomy/operator_release_handoff_packet/","smoke_check":"release-candidate-integrity-and-operator-handoff-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v565-release-candidate-integrity-handoff-board","version":"v565.0","era":"release-candidate-operator-handoff","dashboard_route":"/release-candidate-integrity-handoff-board","api_route":"/api/release-candidate-integrity-handoff-board/layer","cli_flag":"--release-candidate-integrity-handoff-board-v1","builder_function":"build_release_candidate_integrity_handoff_board_v1","text_function":"release_candidate_integrity_handoff_board_v1_text","runtime_directory":"data/autonomy/release_candidate_integrity_handoff_board/","smoke_check":"release-candidate-integrity-and-operator-handoff-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v561.0-v565.0 release candidate integrity handoff manifest tokens: v561-release-candidate-scope-contract v562-candidate-package-integrity-review v563-candidate-verification-evidence-matrix v564-operator-release-handoff-packet v565-release-candidate-integrity-handoff-board release-candidate-integrity-and-operator-handoff-v1 release_candidate_status=prepared_not_created package_integrity_status=review_prepared verification_evidence_status=matrix_prepared operator_handoff_status=prepared release_status=not_created publish_status=not_authorized candidate_board_is_release_creation=False candidate_board_is_publish_approval=False candidate_board_executes_commands=False candidate_board_creates_release=False candidate_board_publishes_release=False approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v566-release-decision-scope-contract","version":"v566.0","era":"release-decision-archive-ledger","dashboard_route":"/release-decision-scope-contract","api_route":"/api/release-decision-scope-contract/layer","cli_flag":"--release-decision-scope-contract-v1","builder_function":"build_release_decision_scope_contract_v1","text_function":"release_decision_scope_contract_v1_text","runtime_directory":"data/autonomy/release_decision_scope_contract/","smoke_check":"release-decision-and-archive-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v567-operator-decision-option-matrix","version":"v567.0","era":"release-decision-archive-ledger","dashboard_route":"/operator-decision-option-matrix","api_route":"/api/operator-decision-option-matrix/layer","cli_flag":"--operator-decision-option-matrix-v1","builder_function":"build_operator_decision_option_matrix_v1","text_function":"operator_decision_option_matrix_v1_text","runtime_directory":"data/autonomy/operator_decision_option_matrix/","smoke_check":"release-decision-and-archive-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v568-release-archive-ledger-prep","version":"v568.0","era":"release-decision-archive-ledger","dashboard_route":"/release-archive-ledger-prep","api_route":"/api/release-archive-ledger-prep/layer","cli_flag":"--release-archive-ledger-prep-v1","builder_function":"build_release_archive_ledger_prep_v1","text_function":"release_archive_ledger_prep_v1_text","runtime_directory":"data/autonomy/release_archive_ledger_prep/","smoke_check":"release-decision-and-archive-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v569-archive-integrity-continuity-review","version":"v569.0","era":"release-decision-archive-ledger","dashboard_route":"/archive-integrity-continuity-review","api_route":"/api/archive-integrity-continuity-review/layer","cli_flag":"--archive-integrity-continuity-review-v1","builder_function":"build_archive_integrity_continuity_review_v1","text_function":"archive_integrity_continuity_review_v1_text","runtime_directory":"data/autonomy/archive_integrity_continuity_review/","smoke_check":"release-decision-and-archive-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v570-release-decision-archive-ledger-board","version":"v570.0","era":"release-decision-archive-ledger","dashboard_route":"/release-decision-archive-ledger-board","api_route":"/api/release-decision-archive-ledger-board/layer","cli_flag":"--release-decision-archive-ledger-board-v1","builder_function":"build_release_decision_archive_ledger_board_v1","text_function":"release_decision_archive_ledger_board_v1_text","runtime_directory":"data/autonomy/release_decision_archive_ledger_board/","smoke_check":"release-decision-and-archive-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v566.0-v570.0 release decision archive ledger manifest tokens: v566-release-decision-scope-contract v567-operator-decision-option-matrix v568-release-archive-ledger-prep v569-archive-integrity-continuity-review v570-release-decision-archive-ledger-board release-decision-and-archive-ledger-v1 release_decision_status=prepared_for_operator operator_decision_status=required archive_ledger_status=prepared_not_written_externally archive_integrity_status=review_prepared release_decision_board_is_release_approval=False release_decision_board_is_publish_permission=False release_decision_board_selects_decision=False release_decision_board_writes_external_archive=False release_decision_board_executes_commands=False release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v571-release-archive-retrieval-scope-contract","version":"v571.0","era":"release-archive-continuity-index","dashboard_route":"/release-archive-retrieval-scope-contract","api_route":"/api/release-archive-retrieval-scope-contract/layer","cli_flag":"--release-archive-retrieval-scope-contract-v1","builder_function":"build_release_archive_retrieval_scope_contract_v1","text_function":"release_archive_retrieval_scope_contract_v1_text","runtime_directory":"data/autonomy/release_archive_retrieval_scope_contract/","smoke_check":"release-archive-retrieval-and-continuity-index-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v572-release-continuity-index-prep","version":"v572.0","era":"release-archive-continuity-index","dashboard_route":"/release-continuity-index-prep","api_route":"/api/release-continuity-index-prep/layer","cli_flag":"--release-continuity-index-prep-v1","builder_function":"build_release_continuity_index_prep_v1","text_function":"release_continuity_index_prep_v1_text","runtime_directory":"data/autonomy/release_continuity_index_prep/","smoke_check":"release-archive-retrieval-and-continuity-index-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v573-historical-reference-classification-review","version":"v573.0","era":"release-archive-continuity-index","dashboard_route":"/historical-reference-classification-review","api_route":"/api/historical-reference-classification-review/layer","cli_flag":"--historical-reference-classification-review-v1","builder_function":"build_historical_reference_classification_review_v1","text_function":"historical_reference_classification_review_v1_text","runtime_directory":"data/autonomy/historical_reference_classification_review/","smoke_check":"release-archive-retrieval-and-continuity-index-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v574-continuity-retrieval-packet","version":"v574.0","era":"release-archive-continuity-index","dashboard_route":"/continuity-retrieval-packet","api_route":"/api/continuity-retrieval-packet/layer","cli_flag":"--continuity-retrieval-packet-v1","builder_function":"build_continuity_retrieval_packet_v1","text_function":"continuity_retrieval_packet_v1_text","runtime_directory":"data/autonomy/continuity_retrieval_packet/","smoke_check":"release-archive-retrieval-and-continuity-index-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v575-release-archive-retrieval-continuity-index-board","version":"v575.0","era":"release-archive-continuity-index","dashboard_route":"/release-archive-retrieval-continuity-index-board","api_route":"/api/release-archive-retrieval-continuity-index-board/layer","cli_flag":"--release-archive-retrieval-continuity-index-board-v1","builder_function":"build_release_archive_retrieval_continuity_index_board_v1","text_function":"release_archive_retrieval_continuity_index_board_v1_text","runtime_directory":"data/autonomy/release_archive_retrieval_continuity_index_board/","smoke_check":"release-archive-retrieval-and-continuity-index-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v571.0-v575.0 release archive continuity index manifest tokens: v571-release-archive-retrieval-scope-contract v572-release-continuity-index-prep v573-historical-reference-classification-review v574-continuity-retrieval-packet v575-release-archive-retrieval-continuity-index-board release-archive-retrieval-and-continuity-index-v1 archive_retrieval_status=prepared_read_only continuity_index_status=prepared historical_reference_status=classified stale_current_reference_status=blocked_if_detected retrieval_packet_status=prepared release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False

# v576.0-v580.0 release archive search handoff manifest tokens: v576-archive-search-scope-contract v577-release-record-query-matrix v578-archive-search-result-review-packet v579-archive-handoff-review-packet v580-release-archive-search-handoff-review-board release-archive-search-and-handoff-review-v1 archive_search_status=prepared_read_only release_record_query_status=matrix_prepared search_result_review_status=prepared archive_handoff_status=prepared archive_write_status=not_performed release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False
# v581.0-v585.0 release archive export closure manifest tokens: v581-archive-export-scope-contract v582-release-archive-export-packet-prep v583-operator-decision-closure-checklist v584-archive-export-integrity-review v585-release-archive-export-decision-closure-board release-archive-export-and-decision-closure-v1 archive_export_status=prepared_not_written_externally export_packet_status=prepared operator_decision_closure_status=required archive_export_integrity_status=review_prepared external_archive_write_status=not_performed release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False

# v586.0-v590.0 source surface manifest tokens: release_archive_import_closure_recall.py archive-import-scope-contract release-archive-import-packet-review closure-recall-review-matrix imported-archive-continuity-guard release-archive-import-closure-recall-board release-archive-import-and-closure-recall-v1

# v591.0-v595.0 source surface manifest tokens: imported_archive_conflict_reconciliation.py imported-archive-conflict-scope-contract archive-conflict-classification-matrix conflict-reconciliation-option-packet imported-archive-conflict-guard-review imported-archive-conflict-reconciliation-board imported-archive-conflict-reconciliation-v1

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v596-reconciliation-decision-scope-contract","version":"v596.0","era":"archive-reconciliation-decision-ledger","dashboard_route":"/reconciliation-decision-scope-contract","api_route":"/api/reconciliation-decision-scope-contract/layer","cli_flag":"--reconciliation-decision-scope-contract-v1","builder_function":"build_reconciliation_decision_scope_contract_v1","text_function":"reconciliation_decision_scope_contract_v1_text","runtime_directory":"data/autonomy/reconciliation_decision_scope_contract/","smoke_check":"archive-reconciliation-decision-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v597-reconciliation-decision-option-ledger","version":"v597.0","era":"archive-reconciliation-decision-ledger","dashboard_route":"/reconciliation-decision-option-ledger","api_route":"/api/reconciliation-decision-option-ledger/layer","cli_flag":"--reconciliation-decision-option-ledger-v1","builder_function":"build_reconciliation_decision_option_ledger_v1","text_function":"reconciliation_decision_option_ledger_v1_text","runtime_directory":"data/autonomy/reconciliation_decision_option_ledger/","smoke_check":"archive-reconciliation-decision-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v598-operator-reconciliation-decision-record-prep","version":"v598.0","era":"archive-reconciliation-decision-ledger","dashboard_route":"/operator-reconciliation-decision-record-prep","api_route":"/api/operator-reconciliation-decision-record-prep/layer","cli_flag":"--operator-reconciliation-decision-record-prep-v1","builder_function":"build_operator_reconciliation_decision_record_prep_v1","text_function":"operator_reconciliation_decision_record_prep_v1_text","runtime_directory":"data/autonomy/operator_reconciliation_decision_record_prep/","smoke_check":"archive-reconciliation-decision-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v599-reconciliation-decision-guard-review","version":"v599.0","era":"archive-reconciliation-decision-ledger","dashboard_route":"/reconciliation-decision-guard-review","api_route":"/api/reconciliation-decision-guard-review/layer","cli_flag":"--reconciliation-decision-guard-review-v1","builder_function":"build_reconciliation_decision_guard_review_v1","text_function":"reconciliation_decision_guard_review_v1_text","runtime_directory":"data/autonomy/reconciliation_decision_guard_review/","smoke_check":"archive-reconciliation-decision-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v600-archive-reconciliation-decision-ledger-board","version":"v600.0","era":"archive-reconciliation-decision-ledger","dashboard_route":"/archive-reconciliation-decision-ledger-board","api_route":"/api/archive-reconciliation-decision-ledger-board/layer","cli_flag":"--archive-reconciliation-decision-ledger-board-v1","builder_function":"build_archive_reconciliation_decision_ledger_board_v1","text_function":"archive_reconciliation_decision_ledger_board_v1_text","runtime_directory":"data/autonomy/archive_reconciliation_decision_ledger_board/","smoke_check":"archive-reconciliation-decision-ledger-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v596.0-v600.0 source surface manifest tokens: archive_reconciliation_decision_ledger.py reconciliation-decision-scope-contract reconciliation-decision-option-ledger operator-reconciliation-decision-record-prep reconciliation-decision-guard-review archive-reconciliation-decision-ledger-board archive-reconciliation-decision-ledger-v1

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v601-smoke-summary-version-alignment-contract","version":"v601.0","era":"current-state-integrity-staleness-hardening","dashboard_route":"/smoke-summary-version-alignment-contract","api_route":"/api/smoke-summary-version-alignment-contract/layer","cli_flag":"--smoke-summary-version-alignment-contract-v1","builder_function":"build_smoke_summary_version_alignment_contract_v1","text_function":"smoke_summary_version_alignment_contract_v1_text","runtime_directory":"data/autonomy/smoke_summary_version_alignment_contract/","smoke_check":"current-state-integrity-staleness-hardening-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v602-nested-metadata-root-version-guard","version":"v602.0","era":"current-state-integrity-staleness-hardening","dashboard_route":"/nested-metadata-root-version-guard","api_route":"/api/nested-metadata-root-version-guard/layer","cli_flag":"--nested-metadata-root-version-guard-v1","builder_function":"build_nested_metadata_root_version_guard_v1","text_function":"nested_metadata_root_version_guard_v1_text","runtime_directory":"data/autonomy/nested_metadata_root_version_guard/","smoke_check":"current-state-integrity-staleness-hardening-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v603-readme-current-handoff-staleness-guard","version":"v603.0","era":"current-state-integrity-staleness-hardening","dashboard_route":"/readme-current-handoff-staleness-guard","api_route":"/api/readme-current-handoff-staleness-guard/layer","cli_flag":"--readme-current-handoff-staleness-guard-v1","builder_function":"build_readme_current_handoff_staleness_guard_v1","text_function":"readme_current_handoff_staleness_guard_v1_text","runtime_directory":"data/autonomy/readme_current_handoff_staleness_guard/","smoke_check":"current-state-integrity-staleness-hardening-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v604-setup-smoke-scope-guard","version":"v604.0","era":"current-state-integrity-staleness-hardening","dashboard_route":"/setup-smoke-scope-guard","api_route":"/api/setup-smoke-scope-guard/layer","cli_flag":"--setup-smoke-scope-guard-v1","builder_function":"build_setup_smoke_scope_guard_v1","text_function":"setup_smoke_scope_guard_v1_text","runtime_directory":"data/autonomy/setup_smoke_scope_guard/","smoke_check":"current-state-integrity-staleness-hardening-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v605-current-state-integrity-staleness-hardening-board","version":"v605.0","era":"current-state-integrity-staleness-hardening","dashboard_route":"/current-state-integrity-staleness-hardening-board","api_route":"/api/current-state-integrity-staleness-hardening-board/layer","cli_flag":"--current-state-integrity-staleness-hardening-board-v1","builder_function":"build_current_state_integrity_staleness_hardening_board_v1","text_function":"current_state_integrity_staleness_hardening_board_v1_text","runtime_directory":"data/autonomy/current_state_integrity_staleness_hardening_board/","smoke_check":"current-state-integrity-staleness-hardening-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v601.0-v605.0 source surface manifest tokens: current_state_integrity_staleness_hardening.py smoke-summary-version-alignment-contract nested-metadata-root-version-guard readme-current-handoff-staleness-guard setup-smoke-scope-guard current-state-integrity-staleness-hardening-board current-state-integrity-staleness-hardening-v1 hardening_report_writes_source=False hardening_report_writes_metadata=False hardening_report_executes_smoke=False audit_pass_is_release_approval=False audit_pass_is_live_patch_permission=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v606-archive-reconciliation-application-scope-packet","version":"v606.0","era":"archive-reconciliation-application-prep","dashboard_route":"/archive-reconciliation-application-scope-packet","api_route":"/api/archive-reconciliation-application-scope-packet/layer","cli_flag":"--archive-reconciliation-application-scope-packet-v1","builder_function":"build_archive_reconciliation_application_scope_packet_v1","text_function":"archive_reconciliation_application_scope_packet_v1_text","runtime_directory":"data/autonomy/archive_reconciliation_application_scope_packet/","smoke_check":"archive-reconciliation-application-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v607-reconciliation-application-candidate-map","version":"v607.0","era":"archive-reconciliation-application-prep","dashboard_route":"/reconciliation-application-candidate-map","api_route":"/api/reconciliation-application-candidate-map/layer","cli_flag":"--reconciliation-application-candidate-map-v1","builder_function":"build_reconciliation_application_candidate_map_v1","text_function":"reconciliation_application_candidate_map_v1_text","runtime_directory":"data/autonomy/reconciliation_application_candidate_map/","smoke_check":"archive-reconciliation-application-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v608-operator-reconciliation-application-approval-checklist","version":"v608.0","era":"archive-reconciliation-application-prep","dashboard_route":"/operator-reconciliation-application-approval-checklist","api_route":"/api/operator-reconciliation-application-approval-checklist/layer","cli_flag":"--operator-reconciliation-application-approval-checklist-v1","builder_function":"build_operator_reconciliation_application_approval_checklist_v1","text_function":"operator_reconciliation_application_approval_checklist_v1_text","runtime_directory":"data/autonomy/operator_reconciliation_application_approval_checklist/","smoke_check":"archive-reconciliation-application-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v609-dry-run-application-receipt-prep","version":"v609.0","era":"archive-reconciliation-application-prep","dashboard_route":"/dry-run-application-receipt-prep","api_route":"/api/dry-run-application-receipt-prep/layer","cli_flag":"--dry-run-application-receipt-prep-v1","builder_function":"build_dry_run_application_receipt_prep_v1","text_function":"dry_run_application_receipt_prep_v1_text","runtime_directory":"data/autonomy/dry_run_application_receipt_prep/","smoke_check":"archive-reconciliation-application-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v610-archive-reconciliation-application-prep-board","version":"v610.0","era":"archive-reconciliation-application-prep","dashboard_route":"/archive-reconciliation-application-prep-board","api_route":"/api/archive-reconciliation-application-prep-board/layer","cli_flag":"--archive-reconciliation-application-prep-board-v1","builder_function":"build_archive_reconciliation_application_prep_board_v1","text_function":"archive_reconciliation_application_prep_board_v1_text","runtime_directory":"data/autonomy/archive_reconciliation_application_prep_board/","smoke_check":"archive-reconciliation-application-prep-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v606.0-v610.0 source surface manifest tokens: archive_reconciliation_application_prep.py archive-reconciliation-application-scope-packet reconciliation-application-candidate-map operator-reconciliation-application-approval-checklist dry-run-application-receipt-prep archive-reconciliation-application-prep-board archive-reconciliation-application-prep-v1 application_prep_board_is_operator_approval=False application_prep_board_writes_archive_records=False application_prep_board_mutates_current_state=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v611-command-center-landing-screen","version":"v611.0","era":"operator-command-center-ui-consolidation","dashboard_route":"/command-center-landing-screen","api_route":"/api/command-center-landing-screen/layer","cli_flag":"--command-center-landing-screen-v1","builder_function":"build_command_center_landing_screen_v1","text_function":"command_center_landing_screen_v1_text","runtime_directory":"data/autonomy/command_center_landing_screen/","smoke_check":"operator-command-center-ui-consolidation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v612-operator-queue-panel","version":"v612.0","era":"operator-command-center-ui-consolidation","dashboard_route":"/operator-queue-panel","api_route":"/api/operator-queue-panel/layer","cli_flag":"--operator-queue-panel-v1","builder_function":"build_operator_queue_panel_v1","text_function":"operator_queue_panel_v1_text","runtime_directory":"data/autonomy/operator_queue_panel/","smoke_check":"operator-command-center-ui-consolidation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v613-safety-state-panel","version":"v613.0","era":"operator-command-center-ui-consolidation","dashboard_route":"/safety-state-panel","api_route":"/api/safety-state-panel/layer","cli_flag":"--safety-state-panel-v1","builder_function":"build_safety_state_panel_v1","text_function":"safety_state_panel_v1_text","runtime_directory":"data/autonomy/safety_state_panel/","smoke_check":"operator-command-center-ui-consolidation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v614-workflow-navigation-groups","version":"v614.0","era":"operator-command-center-ui-consolidation","dashboard_route":"/workflow-navigation-groups","api_route":"/api/workflow-navigation-groups/layer","cli_flag":"--workflow-navigation-groups-v1","builder_function":"build_workflow_navigation_groups_v1","text_function":"workflow_navigation_groups_v1_text","runtime_directory":"data/autonomy/workflow_navigation_groups/","smoke_check":"operator-command-center-ui-consolidation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v615-system-health-summary-board","version":"v615.0","era":"operator-command-center-ui-consolidation","dashboard_route":"/system-health-summary-board","api_route":"/api/system-health-summary-board/layer","cli_flag":"--system-health-summary-board-v1","builder_function":"build_system_health_summary_board_v1","text_function":"system_health_summary_board_v1_text","runtime_directory":"data/autonomy/system_health_summary_board/","smoke_check":"operator-command-center-ui-consolidation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v615-operator-command-center-ui-consolidation-board","version":"v615.0","era":"operator-command-center-ui-consolidation","dashboard_route":"/operator-command-center-ui-consolidation-board","api_route":"/api/operator-command-center-ui-consolidation-board/layer","cli_flag":"--operator-command-center-ui-consolidation-board-v1","builder_function":"build_operator_command_center_ui_consolidation_board_v1","text_function":"operator_command_center_ui_consolidation_board_v1_text","runtime_directory":"data/autonomy/operator_command_center_ui_consolidation_board/","smoke_check":"operator-command-center-ui-consolidation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v611.0-v615.0 source surface manifest tokens: operator_command_center_ui_consolidation.py command-center-landing-screen operator-queue-panel safety-state-panel workflow-navigation-groups system-health-summary-board operator-command-center-ui-consolidation-board operator-command-center-ui-consolidation-v1 command_center_executes_actions=False operator_queue_grants_approval=False safety_panel_changes_authorization=False system_health_summary_runs_smoke=False ui_consolidation_expands_autonomy=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v616-workflow-group-route-index","version":"v616.0","era":"dashboard-workflow-simplification","dashboard_route":"/workflow-group-route-index","api_route":"/api/workflow-group-route-index/layer","cli_flag":"--workflow-group-route-index-v1","builder_function":"build_workflow_group_route_index_v1","text_function":"workflow_group_route_index_v1_text","runtime_directory":"data/autonomy/workflow_group_route_index/","smoke_check":"dashboard-workflow-simplification-legacy-drawer-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v617-legacy-route-drawer","version":"v617.0","era":"dashboard-workflow-simplification","dashboard_route":"/legacy-route-drawer","api_route":"/api/legacy-route-drawer/layer","cli_flag":"--legacy-route-drawer-v1","builder_function":"build_legacy_route_drawer_v1","text_function":"legacy_route_drawer_v1_text","runtime_directory":"data/autonomy/legacy_route_drawer/","smoke_check":"dashboard-workflow-simplification-legacy-drawer-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v618-archive-workflow-pipeline-view","version":"v618.0","era":"dashboard-workflow-simplification","dashboard_route":"/archive-workflow-pipeline-view","api_route":"/api/archive-workflow-pipeline-view/layer","cli_flag":"--archive-workflow-pipeline-view-v1","builder_function":"build_archive_workflow_pipeline_view_v1","text_function":"archive_workflow_pipeline_view_v1_text","runtime_directory":"data/autonomy/archive_workflow_pipeline_view/","smoke_check":"dashboard-workflow-simplification-legacy-drawer-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v619-patch-safety-memory-group-views","version":"v619.0","era":"dashboard-workflow-simplification","dashboard_route":"/patch-safety-memory-group-views","api_route":"/api/patch-safety-memory-group-views/layer","cli_flag":"--patch-safety-memory-group-views-v1","builder_function":"build_patch_safety_memory_group_views_v1","text_function":"patch_safety_memory_group_views_v1_text","runtime_directory":"data/autonomy/patch_safety_memory_group_views/","smoke_check":"dashboard-workflow-simplification-legacy-drawer-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v620-dashboard-simplification-board","version":"v620.0","era":"dashboard-workflow-simplification","dashboard_route":"/dashboard-simplification-board","api_route":"/api/dashboard-simplification-board/layer","cli_flag":"--dashboard-simplification-board-v1","builder_function":"build_dashboard_simplification_board_v1","text_function":"dashboard_simplification_board_v1_text","runtime_directory":"data/autonomy/dashboard_simplification_board/","smoke_check":"dashboard-workflow-simplification-legacy-drawer-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v616.0-v620.0 source surface manifest tokens: dashboard_workflow_simplification.py workflow-group-route-index legacy-route-drawer archive-workflow-pipeline-view patch-safety-memory-group-views dashboard-simplification-board dashboard-workflow-simplification-legacy-drawer-v1 workflow_index_executes_actions=False legacy_drawer_deletes_routes=False archive_pipeline_writes_archive_records=False group_views_write_memory=False simplification_board_expands_autonomy=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v621-universal-action-label-standard","version":"v621.0","era":"operator-action-semantics-ux","dashboard_route":"/universal-action-label-standard","api_route":"/api/universal-action-label-standard/layer","cli_flag":"--universal-action-label-standard-v1","builder_function":"build_universal_action_label_standard_v1","text_function":"universal_action_label_standard_v1_text","runtime_directory":"data/autonomy/universal_action_label_standard/","smoke_check":"operator-action-semantics-approval-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v622-blocked-action-explanation-cards","version":"v622.0","era":"operator-action-semantics-ux","dashboard_route":"/blocked-action-explanation-cards","api_route":"/api/blocked-action-explanation-cards/layer","cli_flag":"--blocked-action-explanation-cards-v1","builder_function":"build_blocked_action_explanation_cards_v1","text_function":"blocked_action_explanation_cards_v1_text","runtime_directory":"data/autonomy/blocked_action_explanation_cards/","smoke_check":"operator-action-semantics-approval-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v623-one-time-approval-burnout-ux","version":"v623.0","era":"operator-action-semantics-ux","dashboard_route":"/one-time-approval-burnout-ux","api_route":"/api/one-time-approval-burnout-ux/layer","cli_flag":"--one-time-approval-burnout-ux-v1","builder_function":"build_one_time_approval_burnout_ux_v1","text_function":"one_time_approval_burnout_ux_v1_text","runtime_directory":"data/autonomy/one_time_approval_burnout_ux/","smoke_check":"operator-action-semantics-approval-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v624-safe-preview-before-action-summary","version":"v624.0","era":"operator-action-semantics-ux","dashboard_route":"/safe-preview-before-action-summary","api_route":"/api/safe-preview-before-action-summary/layer","cli_flag":"--safe-preview-before-action-summary-v1","builder_function":"build_safe_preview_before_action_summary_v1","text_function":"safe_preview_before_action_summary_v1_text","runtime_directory":"data/autonomy/safe_preview_before_action_summary/","smoke_check":"operator-action-semantics-approval-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v625-operator-action-semantics-board","version":"v625.0","era":"operator-action-semantics-ux","dashboard_route":"/operator-action-semantics-board","api_route":"/api/operator-action-semantics-board/layer","cli_flag":"--operator-action-semantics-board-v1","builder_function":"build_operator_action_semantics_board_v1","text_function":"operator_action_semantics_board_v1_text","runtime_directory":"data/autonomy/operator_action_semantics_board/","smoke_check":"operator-action-semantics-approval-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v621.0-v625.0 source surface manifest tokens: operator_action_semantics_ux.py universal-action-label-standard blocked-action-explanation-cards one-time-approval-burnout-ux safe-preview-before-action-summary operator-action-semantics-board operator-action-semantics-approval-ux-v1 action_labels_execute_actions=False blocked_cards_unblock_actions=False approval_card_reuses_approval=False safe_preview_executes_action=False semantics_board_expands_autonomy=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v626-review-packet-summary-header","version":"v626.0","era":"review-packet-evidence-ux","dashboard_route":"/review-packet-summary-header","api_route":"/api/review-packet-summary-header/layer","cli_flag":"--review-packet-summary-header-v1","builder_function":"build_review_packet_summary_header_v1","text_function":"review_packet_summary_header_v1_text","runtime_directory":"data/autonomy/review_packet_summary_header/","smoke_check":"review-packet-readability-evidence-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v627-evidence-grouping-priority-layout","version":"v627.0","era":"review-packet-evidence-ux","dashboard_route":"/evidence-grouping-priority-layout","api_route":"/api/evidence-grouping-priority-layout/layer","cli_flag":"--evidence-grouping-priority-layout-v1","builder_function":"build_evidence_grouping_priority_layout_v1","text_function":"evidence_grouping_priority_layout_v1_text","runtime_directory":"data/autonomy/evidence_grouping_priority_layout/","smoke_check":"review-packet-readability-evidence-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v628-receipt-ledger-readability-cards","version":"v628.0","era":"review-packet-evidence-ux","dashboard_route":"/receipt-ledger-readability-cards","api_route":"/api/receipt-ledger-readability-cards/layer","cli_flag":"--receipt-ledger-readability-cards-v1","builder_function":"build_receipt_ledger_readability_cards_v1","text_function":"receipt_ledger_readability_cards_v1_text","runtime_directory":"data/autonomy/receipt_ledger_readability_cards/","smoke_check":"review-packet-readability-evidence-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v629-system-health-evidence-ux","version":"v629.0","era":"review-packet-evidence-ux","dashboard_route":"/system-health-evidence-ux","api_route":"/api/system-health-evidence-ux/layer","cli_flag":"--system-health-evidence-ux-v1","builder_function":"build_system_health_evidence_ux_v1","text_function":"system_health_evidence_ux_v1_text","runtime_directory":"data/autonomy/system_health_evidence_ux/","smoke_check":"review-packet-readability-evidence-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v630-review-packet-evidence-ux-board","version":"v630.0","era":"review-packet-evidence-ux","dashboard_route":"/review-packet-evidence-ux-board","api_route":"/api/review-packet-evidence-ux-board/layer","cli_flag":"--review-packet-evidence-ux-board-v1","builder_function":"build_review_packet_evidence_ux_board_v1","text_function":"review_packet_evidence_ux_board_v1_text","runtime_directory":"data/autonomy/review_packet_evidence_ux_board/","smoke_check":"review-packet-readability-evidence-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v626.0-v630.0 source surface manifest tokens: review_packet_evidence_ux.py review-packet-summary-header evidence-grouping-priority-layout receipt-ledger-readability-cards system-health-evidence-ux review-packet-evidence-ux-board review-packet-readability-evidence-ux-v1 summary_header_grants_approval=False evidence_grouping_hides_raw_evidence=False receipt_cards_treat_receipt_as_approval=False system_health_panels_run_smoke=False evidence_board_expands_autonomy=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v631-surface-search-index","version":"v631.0","era":"dashboard-search-surface-discovery","dashboard_route":"/surface-search-index","api_route":"/api/surface-search-index/layer","cli_flag":"--surface-search-index-v1","builder_function":"build_surface_search_index_v1","text_function":"surface_search_index_v1_text","runtime_directory":"data/autonomy/surface_search_index/","smoke_check":"operator-dashboard-search-surface-discovery-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v632-route-module-smoke-discovery-cards","version":"v632.0","era":"dashboard-search-surface-discovery","dashboard_route":"/route-module-smoke-discovery-cards","api_route":"/api/route-module-smoke-discovery-cards/layer","cli_flag":"--route-module-smoke-discovery-cards-v1","builder_function":"build_route_module_smoke_discovery_cards_v1","text_function":"route_module_smoke_discovery_cards_v1_text","runtime_directory":"data/autonomy/route_module_smoke_discovery_cards/","smoke_check":"operator-dashboard-search-surface-discovery-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v633-workflow-aware-search-filters","version":"v633.0","era":"dashboard-search-surface-discovery","dashboard_route":"/workflow-aware-search-filters","api_route":"/api/workflow-aware-search-filters/layer","cli_flag":"--workflow-aware-search-filters-v1","builder_function":"build_workflow_aware_search_filters_v1","text_function":"workflow_aware_search_filters_v1_text","runtime_directory":"data/autonomy/workflow_aware_search_filters/","smoke_check":"operator-dashboard-search-surface-discovery-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v634-current-historical-surface-guard","version":"v634.0","era":"dashboard-search-surface-discovery","dashboard_route":"/current-historical-surface-guard","api_route":"/api/current-historical-surface-guard/layer","cli_flag":"--current-historical-surface-guard-v1","builder_function":"build_current_historical_surface_guard_v1","text_function":"current_historical_surface_guard_v1_text","runtime_directory":"data/autonomy/current_historical_surface_guard/","smoke_check":"operator-dashboard-search-surface-discovery-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v635-dashboard-search-discovery-board","version":"v635.0","era":"dashboard-search-surface-discovery","dashboard_route":"/dashboard-search-discovery-board","api_route":"/api/dashboard-search-discovery-board/layer","cli_flag":"--dashboard-search-discovery-board-v1","builder_function":"build_dashboard_search_discovery_board_v1","text_function":"dashboard_search_discovery_board_v1_text","runtime_directory":"data/autonomy/dashboard_search_discovery_board/","smoke_check":"operator-dashboard-search-surface-discovery-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":False,"approval_burnout_required":False,"package_privacy_sensitive":True,"status":"represented"},
])
# v631.0-v635.0 source surface manifest tokens: dashboard_search_surface_discovery.py surface-search-index route-module-smoke-discovery-cards workflow-aware-search-filters current-historical-surface-guard dashboard-search-discovery-board operator-dashboard-search-surface-discovery-v1 search_index_grants_approval=False search_index_treats_presence_as_authorization=False discovery_cards_execute_commands=False workflow_filters_hide_safety=False current_historical_guard_treats_current_as_approval=False discovery_board_expands_autonomy=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v636-decision-capture-form-schema","version":"v636.0","era":"operator-decision-approval-ux","dashboard_route":"/decision-capture-form-schema","api_route":"/api/decision-capture-form-schema/layer","cli_flag":"--decision-capture-form-schema-v1","builder_function":"build_decision_capture_form_schema_v1","text_function":"decision_capture_form_schema_v1_text","runtime_directory":"data/autonomy/decision_capture_form_schema/","smoke_check":"operator-decision-capture-approval-form-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v637-approval-scope-target-binding-panel","version":"v637.0","era":"operator-decision-approval-ux","dashboard_route":"/approval-scope-target-binding-panel","api_route":"/api/approval-scope-target-binding-panel/layer","cli_flag":"--approval-scope-target-binding-panel-v1","builder_function":"build_approval_scope_target_binding_panel_v1","text_function":"approval_scope_target_binding_panel_v1_text","runtime_directory":"data/autonomy/approval_scope_target_binding_panel/","smoke_check":"operator-decision-capture-approval-form-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v638-approval-expiration-burnout-form-ux","version":"v638.0","era":"operator-decision-approval-ux","dashboard_route":"/approval-expiration-burnout-form-ux","api_route":"/api/approval-expiration-burnout-form-ux/layer","cli_flag":"--approval-expiration-burnout-form-ux-v1","builder_function":"build_approval_expiration_burnout_form_ux_v1","text_function":"approval_expiration_burnout_form_ux_v1_text","runtime_directory":"data/autonomy/approval_expiration_burnout_form_ux/","smoke_check":"operator-decision-capture-approval-form-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v639-denial-deferral-revision-decision-capture","version":"v639.0","era":"operator-decision-approval-ux","dashboard_route":"/denial-deferral-revision-decision-capture","api_route":"/api/denial-deferral-revision-decision-capture/layer","cli_flag":"--denial-deferral-revision-decision-capture-v1","builder_function":"build_denial_deferral_revision_decision_capture_v1","text_function":"denial_deferral_revision_decision_capture_v1_text","runtime_directory":"data/autonomy/denial_deferral_revision_decision_capture/","smoke_check":"operator-decision-capture-approval-form-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v640-operator-decision-approval-ux-board","version":"v640.0","era":"operator-decision-approval-ux","dashboard_route":"/operator-decision-approval-ux-board","api_route":"/api/operator-decision-approval-ux-board/layer","cli_flag":"--operator-decision-approval-ux-board-v1","builder_function":"build_operator_decision_approval_ux_board_v1","text_function":"operator_decision_approval_ux_board_v1_text","runtime_directory":"data/autonomy/operator_decision_approval_ux_board/","smoke_check":"operator-decision-capture-approval-form-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v636.0-v640.0 source surface manifest tokens: operator_decision_approval_ux.py decision-capture-form-schema approval-scope-target-binding-panel approval-expiration-burnout-form-ux denial-deferral-revision-decision-capture operator-decision-approval-ux-board operator-decision-capture-approval-form-ux-v1 decision_form_creates_approval=False scope_binding_grants_authorization=False approval_burnout_reuse_allowed=False denial_deferral_is_approval=False ux_board_expands_autonomy=False
# v641.0-v645.0 source surface manifest tokens: operator_receipt_timeline_audit_ux.py operator-decision-timeline-model approval-burnout-consumption-timeline-cards blocked-action-safety-event-timeline-cards verification-receipt-timeline-cards decision-audit-trail-board operator-receipt-timeline-decision-audit-trail-ux-v1 timeline_model_grants_approval=False approval_consumption_cards_allow_reuse=False blocked_action_cards_unblock_actions=False verification_cards_treat_pass_as_authorization=False audit_trail_expands_autonomy=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v646-session-resume-state-summary","version":"v646.0","era":"operator-session-continuity-resume-ux","dashboard_route":"/session-resume-state-summary","api_route":"/api/session-resume-state-summary/layer","cli_flag":"--session-resume-state-summary-v1","builder_function":"build_session_resume_state_summary_v1","text_function":"session_resume_state_summary_v1_text","runtime_directory":"data/autonomy/session_resume_state_summary/","smoke_check":"operator-session-continuity-resume-console-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v647-unresolved-warning-blocker-carryover","version":"v647.0","era":"operator-session-continuity-resume-ux","dashboard_route":"/unresolved-warning-blocker-carryover","api_route":"/api/unresolved-warning-blocker-carryover/layer","cli_flag":"--unresolved-warning-blocker-carryover-v1","builder_function":"build_unresolved_warning_blocker_carryover_v1","text_function":"unresolved_warning_blocker_carryover_v1_text","runtime_directory":"data/autonomy/unresolved_warning_blocker_carryover/","smoke_check":"operator-session-continuity-resume-console-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v648-pending-decisions-prepared-work-resume-queue","version":"v648.0","era":"operator-session-continuity-resume-ux","dashboard_route":"/pending-decisions-prepared-work-resume-queue","api_route":"/api/pending-decisions-prepared-work-resume-queue/layer","cli_flag":"--pending-decisions-prepared-work-resume-queue-v1","builder_function":"build_pending_decisions_prepared_work_resume_queue_v1","text_function":"pending_decisions_prepared_work_resume_queue_v1_text","runtime_directory":"data/autonomy/pending_decisions_prepared_work_resume_queue/","smoke_check":"operator-session-continuity-resume-console-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v649-verification-state-resume-card","version":"v649.0","era":"operator-session-continuity-resume-ux","dashboard_route":"/verification-state-resume-card","api_route":"/api/verification-state-resume-card/layer","cli_flag":"--verification-state-resume-card-v1","builder_function":"build_verification_state_resume_card_v1","text_function":"verification_state_resume_card_v1_text","runtime_directory":"data/autonomy/verification_state_resume_card/","smoke_check":"operator-session-continuity-resume-console-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v650-operator-session-continuity-board","version":"v650.0","era":"operator-session-continuity-resume-ux","dashboard_route":"/operator-session-continuity-board","api_route":"/api/operator-session-continuity-board/layer","cli_flag":"--operator-session-continuity-board-v1","builder_function":"build_operator_session_continuity_board_v1","text_function":"operator_session_continuity_board_v1_text","runtime_directory":"data/autonomy/operator_session_continuity_board/","smoke_check":"operator-session-continuity-resume-console-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v646.0-v650.0 source surface manifest tokens: operator_session_continuity_resume_ux.py session-resume-state-summary unresolved-warning-blocker-carryover pending-decisions-prepared-work-resume-queue verification-state-resume-card operator-session-continuity-board operator-session-continuity-resume-console-ux-v1 resume_summary_starts_work=False pending_queue_starts_work=False verification_card_treats_pass_as_authorization=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v651-guided-review-wizard-entry-model","version":"v651.0","era":"operator-guided-review-wizard-ux","dashboard_route":"/guided-review-wizard-entry-model","api_route":"/api/guided-review-wizard-entry-model/layer","cli_flag":"--guided-review-wizard-entry-model-v1","builder_function":"build_guided_review_wizard_entry_model_v1","text_function":"guided_review_wizard_entry_model_v1_text","runtime_directory":"data/autonomy/guided_review_wizard_entry_model/","smoke_check":"operator-guided-review-wizard-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v652-guided-evidence-warning-step-cards","version":"v652.0","era":"operator-guided-review-wizard-ux","dashboard_route":"/guided-evidence-warning-step-cards","api_route":"/api/guided-evidence-warning-step-cards/layer","cli_flag":"--guided-evidence-warning-step-cards-v1","builder_function":"build_guided_evidence_warning_step_cards_v1","text_function":"guided_evidence_warning_step_cards_v1_text","runtime_directory":"data/autonomy/guided_evidence_warning_step_cards/","smoke_check":"operator-guided-review-wizard-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v653-guided-decision-approval-step-ux","version":"v653.0","era":"operator-guided-review-wizard-ux","dashboard_route":"/guided-decision-approval-step-ux","api_route":"/api/guided-decision-approval-step-ux/layer","cli_flag":"--guided-decision-approval-step-ux-v1","builder_function":"build_guided_decision_approval_step_ux_v1","text_function":"guided_decision_approval_step_ux_v1_text","runtime_directory":"data/autonomy/guided_decision_approval_step_ux/","smoke_check":"operator-guided-review-wizard-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v654-guided-verification-resume-step-summary","version":"v654.0","era":"operator-guided-review-wizard-ux","dashboard_route":"/guided-verification-resume-step-summary","api_route":"/api/guided-verification-resume-step-summary/layer","cli_flag":"--guided-verification-resume-step-summary-v1","builder_function":"build_guided_verification_resume_step_summary_v1","text_function":"guided_verification_resume_step_summary_v1_text","runtime_directory":"data/autonomy/guided_verification_resume_step_summary/","smoke_check":"operator-guided-review-wizard-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v655-operator-guided-review-wizard-board","version":"v655.0","era":"operator-guided-review-wizard-ux","dashboard_route":"/operator-guided-review-wizard-board","api_route":"/api/operator-guided-review-wizard-board/layer","cli_flag":"--operator-guided-review-wizard-board-v1","builder_function":"build_operator_guided_review_wizard_board_v1","text_function":"operator_guided_review_wizard_board_v1_text","runtime_directory":"data/autonomy/operator_guided_review_wizard_board/","smoke_check":"operator-guided-review-wizard-ux-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v651.0-v655.0 source surface manifest tokens: operator_guided_review_wizard_ux.py guided-review-wizard-entry-model guided-evidence-warning-step-cards guided-decision-approval-step-ux guided-verification-resume-step-summary operator-guided-review-wizard-board operator-guided-review-wizard-ux-v1 wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_treats_pass_as_authorization=False wizard_board_expands_autonomy=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v656-metadata-schema-contract","version":"v656.0","era":"project-metadata-active-context-repair","dashboard_route":"/metadata-schema-contract","api_route":"/api/metadata-schema-contract/layer","cli_flag":"--metadata-schema-contract-v1","builder_function":"build_metadata_schema_contract_v1","text_function":"metadata_schema_contract_v1_text","runtime_directory":"data/autonomy/metadata_schema_contract/","smoke_check":"project-metadata-schema-active-context-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v657-active-project-resolution-audit","version":"v657.0","era":"project-metadata-active-context-repair","dashboard_route":"/active-project-resolution-audit","api_route":"/api/active-project-resolution-audit/layer","cli_flag":"--active-project-resolution-audit-v1","builder_function":"build_active_project_resolution_audit_v1","text_function":"active_project_resolution_audit_v1_text","runtime_directory":"data/autonomy/active_project_resolution_audit/","smoke_check":"project-metadata-schema-active-context-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v658-project-status-rendering-hardening","version":"v658.0","era":"project-metadata-active-context-repair","dashboard_route":"/project-status-rendering-hardening","api_route":"/api/project-status-rendering-hardening/layer","cli_flag":"--project-status-rendering-hardening-v1","builder_function":"build_project_status_rendering_hardening_v1","text_function":"project_status_rendering_hardening_v1_text","runtime_directory":"data/autonomy/project_status_rendering_hardening/","smoke_check":"project-metadata-schema-active-context-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v659-release-note-version-semantics-audit","version":"v659.0","era":"project-metadata-active-context-repair","dashboard_route":"/release-note-version-semantics-audit","api_route":"/api/release-note-version-semantics-audit/layer","cli_flag":"--release-note-version-semantics-audit-v1","builder_function":"build_release_note_version_semantics_audit_v1","text_function":"release_note_version_semantics_audit_v1_text","runtime_directory":"data/autonomy/release_note_version_semantics_audit/","smoke_check":"project-metadata-schema-active-context-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v660-metadata-integrity-board-smoke-gate","version":"v660.0","era":"project-metadata-active-context-repair","dashboard_route":"/metadata-integrity-board-smoke-gate","api_route":"/api/metadata-integrity-board-smoke-gate/layer","cli_flag":"--metadata-integrity-board-smoke-gate-v1","builder_function":"build_metadata_integrity_board_smoke_gate_v1","text_function":"metadata_integrity_board_smoke_gate_v1_text","runtime_directory":"data/autonomy/metadata_integrity_board_smoke_gate/","smoke_check":"project-metadata-schema-active-context-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v656.0-v660.0 source surface manifest tokens: project_metadata_active_context_repair.py metadata-schema-contract active-project-resolution-audit project-status-rendering-hardening release-note-version-semantics-audit metadata-integrity-board-smoke-gate project-metadata-schema-active-context-repair-v1 schema_contract_writes_metadata=False active_project_resolution_changes_project=False status_rendering_executes_actions=False release_note_semantics_rewrites_history=False metadata_integrity_board_executes_smoke=False metadata_integrity_board_expands_autonomy=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v661-smoke-gate-classification-model","version":"v661.0","era":"legacy-smoke-segmentation-repair","dashboard_route":"/smoke-gate-classification-model","api_route":"/api/smoke-gate-classification-model/layer","cli_flag":"--smoke-gate-classification-model-v1","builder_function":"build_smoke_gate_classification_model_v1","text_function":"smoke_gate_classification_model_v1_text","runtime_directory":"data/autonomy/smoke_gate_classification_model/","smoke_check":"legacy-smoke-segmentation-stale-expectation-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v662-current-release-gate-segment","version":"v662.0","era":"legacy-smoke-segmentation-repair","dashboard_route":"/current-release-gate-segment","api_route":"/api/current-release-gate-segment/layer","cli_flag":"--current-release-gate-segment-v1","builder_function":"build_current_release_gate_segment_v1","text_function":"current_release_gate_segment_v1_text","runtime_directory":"data/autonomy/current_release_gate_segment/","smoke_check":"legacy-smoke-segmentation-stale-expectation-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v663-legacy-advisory-segment-separation","version":"v663.0","era":"legacy-smoke-segmentation-repair","dashboard_route":"/legacy-advisory-segment-separation","api_route":"/api/legacy-advisory-segment-separation/layer","cli_flag":"--legacy-advisory-segment-separation-v1","builder_function":"build_legacy_advisory_segment_separation_v1","text_function":"legacy_advisory_segment_separation_v1_text","runtime_directory":"data/autonomy/legacy_advisory_segment_separation/","smoke_check":"legacy-smoke-segmentation-stale-expectation-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v664-stale-expectation-repair-audit","version":"v664.0","era":"legacy-smoke-segmentation-repair","dashboard_route":"/stale-expectation-repair-audit","api_route":"/api/stale-expectation-repair-audit/layer","cli_flag":"--stale-expectation-repair-audit-v1","builder_function":"build_stale_expectation_repair_audit_v1","text_function":"stale_expectation_repair_audit_v1_text","runtime_directory":"data/autonomy/stale_expectation_repair_audit/","smoke_check":"legacy-smoke-segmentation-stale-expectation-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v665-smoke-segmentation-integrity-board","version":"v685.0","era":"legacy-smoke-segmentation-repair","dashboard_route":"/smoke-segmentation-integrity-board","api_route":"/api/smoke-segmentation-integrity-board/layer","cli_flag":"--smoke-segmentation-integrity-board-v1","builder_function":"build_smoke_segmentation_integrity_board_v1","text_function":"smoke_segmentation_integrity_board_v1_text","runtime_directory":"data/autonomy/smoke_segmentation_integrity_board/","smoke_check":"legacy-smoke-segmentation-stale-expectation-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v661.0-v665.0 source surface manifest tokens: legacy_smoke_segmentation_repair.py smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy-smoke-segmentation-stale-expectation-repair-v1 classification_changes_smoke_results=False current_gate_executes_smoke=False legacy_advisory_blocks_current_release=False stale_expectation_repair_rewrites_history=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v666-surface-registry-manifest-contract","version":"666.0","era":"manifest-driven-surface-registry","dashboard_route":"/surface-registry-manifest-contract","api_route":"/api/surface-registry-manifest-contract/layer","cli_flag":"--surface-registry-manifest-contract-v1","builder_function":"build_surface_registry_manifest_contract_v1","text_function":"surface_registry_manifest_contract_v1_text","runtime_directory":"data/autonomy/surface_registry_manifest_contract/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v667-dashboard-surface-manifest-adapter","version":"667.0","era":"manifest-driven-surface-registry","dashboard_route":"/dashboard-surface-manifest-adapter","api_route":"/api/dashboard-surface-manifest-adapter/layer","cli_flag":"--dashboard-surface-manifest-adapter-v1","builder_function":"build_dashboard_surface_manifest_adapter_v1","text_function":"dashboard_surface_manifest_adapter_v1_text","runtime_directory":"data/autonomy/dashboard_surface_manifest_adapter/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v668-api-cli-surface-manifest-adapter","version":"668.0","era":"manifest-driven-surface-registry","dashboard_route":"/api-cli-surface-manifest-adapter","api_route":"/api/api-cli-surface-manifest-adapter/layer","cli_flag":"--api-cli-surface-manifest-adapter-v1","builder_function":"build_api_cli_surface_manifest_adapter_v1","text_function":"api_cli_surface_manifest_adapter_v1_text","runtime_directory":"data/autonomy/api_cli_surface_manifest_adapter/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v669-smoke-surface-manifest-adapter","version":"669.0","era":"manifest-driven-surface-registry","dashboard_route":"/smoke-surface-manifest-adapter","api_route":"/api/smoke-surface-manifest-adapter/layer","cli_flag":"--smoke-surface-manifest-adapter-v1","builder_function":"build_smoke_surface_manifest_adapter_v1","text_function":"smoke_surface_manifest_adapter_v1_text","runtime_directory":"data/autonomy/smoke_surface_manifest_adapter/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v670-source-surface-manifest-reconciliation","version":"670.0","era":"manifest-driven-surface-registry","dashboard_route":"/source-surface-manifest-reconciliation","api_route":"/api/source-surface-manifest-reconciliation/layer","cli_flag":"--source-surface-manifest-reconciliation-v1","builder_function":"build_source_surface_manifest_reconciliation_v1","text_function":"source_surface_manifest_reconciliation_v1_text","runtime_directory":"data/autonomy/source_surface_manifest_reconciliation/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v671-documentation-token-manifest-validation","version":"671.0","era":"manifest-driven-surface-registry","dashboard_route":"/documentation-token-manifest-validation","api_route":"/api/documentation-token-manifest-validation/layer","cli_flag":"--documentation-token-manifest-validation-v1","builder_function":"build_documentation_token_manifest_validation_v1","text_function":"documentation_token_manifest_validation_v1_text","runtime_directory":"data/autonomy/documentation_token_manifest_validation/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v672-manifest-drift-detection-board","version":"672.0","era":"manifest-driven-surface-registry","dashboard_route":"/manifest-drift-detection-board","api_route":"/api/manifest-drift-detection-board/layer","cli_flag":"--manifest-drift-detection-board-v1","builder_function":"build_manifest_drift_detection_board_v1","text_function":"manifest_drift_detection_board_v1_text","runtime_directory":"data/autonomy/manifest_drift_detection_board/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v673-registry-generation-prep-layer","version":"673.0","era":"manifest-driven-surface-registry","dashboard_route":"/registry-generation-prep-layer","api_route":"/api/registry-generation-prep-layer/layer","cli_flag":"--registry-generation-prep-layer-v1","builder_function":"build_registry_generation_prep_layer_v1","text_function":"registry_generation_prep_layer_v1_text","runtime_directory":"data/autonomy/registry_generation_prep_layer/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v674-manifest-driven-current-release-gate","version":"674.0","era":"manifest-driven-surface-registry","dashboard_route":"/manifest-driven-current-release-gate","api_route":"/api/manifest-driven-current-release-gate/layer","cli_flag":"--manifest-driven-current-release-gate-v1","builder_function":"build_manifest_driven_current_release_gate_v1","text_function":"manifest_driven_current_release_gate_v1_text","runtime_directory":"data/autonomy/manifest_driven_current_release_gate/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v675-manifest-driven-surface-registry-board","version":"675.0","era":"manifest-driven-surface-registry","dashboard_route":"/manifest-driven-surface-registry-board","api_route":"/api/manifest-driven-surface-registry-board/layer","cli_flag":"--manifest-driven-surface-registry-board-v1","builder_function":"build_manifest_driven_surface_registry_board_v1","text_function":"manifest_driven_surface_registry_board_v1_text","runtime_directory":"data/autonomy/manifest_driven_surface_registry_board/","smoke_check":"manifest-driven-surface-registry-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v666.0-v685.0 source surface manifest tokens: manifest_driven_surface_registry.py surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board manifest-driven-surface-registry-v1 manifest_contract_writes_source=False dashboard_manifest_adapter_registers_routes=False api_cli_manifest_adapter_registers_endpoints=False smoke_manifest_adapter_executes_smoke=False source_surface_reconciliation_mutates_manifest=False documentation_token_validation_rewrites_docs=False drift_detection_auto_fixes=False generation_prep_generates_live_routes=False manifest_current_gate_executes_checks=False manifest_board_expands_autonomy=False manifest_presence_is_authorization=False registry_health_is_approval=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v676-dashboard-component-contract","version":"676.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/dashboard-component-contract","api_route":"/api/dashboard-component-contract/layer","cli_flag":"--dashboard-component-contract-v1","builder_function":"build_dashboard_component_contract_v1","text_function":"dashboard_component_contract_v1_text","runtime_directory":"data/autonomy/dashboard_component_contract/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v677-shared-review-packet-renderer","version":"677.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/shared-review-packet-renderer","api_route":"/api/shared-review-packet-renderer/layer","cli_flag":"--shared-review-packet-renderer-v1","builder_function":"build_shared_review_packet_renderer_v1","text_function":"shared_review_packet_renderer_v1_text","runtime_directory":"data/autonomy/shared_review_packet_renderer/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v678-shared-boundary-matrix-renderer","version":"678.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/shared-boundary-matrix-renderer","api_route":"/api/shared-boundary-matrix-renderer/layer","cli_flag":"--shared-boundary-matrix-renderer-v1","builder_function":"build_shared_boundary_matrix_renderer_v1","text_function":"shared_boundary_matrix_renderer_v1_text","runtime_directory":"data/autonomy/shared_boundary_matrix_renderer/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v679-shared-evidence-warning-renderer","version":"679.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/shared-evidence-warning-renderer","api_route":"/api/shared-evidence-warning-renderer/layer","cli_flag":"--shared-evidence-warning-renderer-v1","builder_function":"build_shared_evidence_warning_renderer_v1","text_function":"shared_evidence_warning_renderer_v1_text","runtime_directory":"data/autonomy/shared_evidence_warning_renderer/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v680-shared-decision-approval-renderer","version":"680.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/shared-decision-approval-renderer","api_route":"/api/shared-decision-approval-renderer/layer","cli_flag":"--shared-decision-approval-renderer-v1","builder_function":"build_shared_decision_approval_renderer_v1","text_function":"shared_decision_approval_renderer_v1_text","runtime_directory":"data/autonomy/shared_decision_approval_renderer/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v681-shared-resume-continuity-renderer","version":"681.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/shared-resume-continuity-renderer","api_route":"/api/shared-resume-continuity-renderer/layer","cli_flag":"--shared-resume-continuity-renderer-v1","builder_function":"build_shared_resume_continuity_renderer_v1","text_function":"shared_resume_continuity_renderer_v1_text","runtime_directory":"data/autonomy/shared_resume_continuity_renderer/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v682-dashboard-route-renderer-adapter","version":"682.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/dashboard-route-renderer-adapter","api_route":"/api/dashboard-route-renderer-adapter/layer","cli_flag":"--dashboard-route-renderer-adapter-v1","builder_function":"build_dashboard_route_renderer_adapter_v1","text_function":"dashboard_route_renderer_adapter_v1_text","runtime_directory":"data/autonomy/dashboard_route_renderer_adapter/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v683-dashboard-style-regression-guard","version":"683.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/dashboard-style-regression-guard","api_route":"/api/dashboard-style-regression-guard/layer","cli_flag":"--dashboard-style-regression-guard-v1","builder_function":"build_dashboard_style_regression_guard_v1","text_function":"dashboard_style_regression_guard_v1_text","runtime_directory":"data/autonomy/dashboard_style_regression_guard/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v684-legacy-renderer-duplication-audit","version":"684.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/legacy-renderer-duplication-audit","api_route":"/api/legacy-renderer-duplication-audit/layer","cli_flag":"--legacy-renderer-duplication-audit-v1","builder_function":"build_legacy_renderer_duplication_audit_v1","text_function":"legacy_renderer_duplication_audit_v1_text","runtime_directory":"data/autonomy/legacy_renderer_duplication_audit/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v685-dashboard-renderer-component-extraction-board","version":"685.0","era":"dashboard-renderer-component-extraction","dashboard_route":"/dashboard-renderer-component-extraction-board","api_route":"/api/dashboard-renderer-component-extraction-board/layer","cli_flag":"--dashboard-renderer-component-extraction-board-v1","builder_function":"build_dashboard_renderer_component_extraction_board_v1","text_function":"dashboard_renderer_component_extraction_board_v1_text","runtime_directory":"data/autonomy/dashboard_renderer_component_extraction_board/","smoke_check":"dashboard-renderer-component-extraction-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])
# v676.0-v685.0 source surface manifest tokens: dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard-renderer-component-extraction-v1 component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v686-neural-deck-layout-shell","version":"686.0","era":"neural-command-deck-dashboard-redesign","dashboard_route":"/neural-deck-layout-shell","api_route":"/api/neural-deck-layout-shell/layer","cli_flag":"--neural-deck-layout-shell-v1","builder_function":"build_neural_deck_layout_shell_v1","text_function":"neural_deck_layout_shell_v1_text","runtime_directory":"data/autonomy/neural_deck_layout_shell/","smoke_check":"neural-command-deck-dashboard-redesign-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v687-eidolon-thinking-core-panel","version":"687.0","era":"neural-command-deck-dashboard-redesign","dashboard_route":"/eidolon-thinking-core-panel","api_route":"/api/eidolon-thinking-core-panel/layer","cli_flag":"--eidolon-thinking-core-panel-v1","builder_function":"build_eidolon_thinking_core_panel_v1","text_function":"eidolon_thinking_core_panel_v1_text","runtime_directory":"data/autonomy/eidolon_thinking_core_panel/","smoke_check":"neural-command-deck-dashboard-redesign-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v688-operator-conversation-console","version":"688.0","era":"neural-command-deck-dashboard-redesign","dashboard_route":"/operator-conversation-console","api_route":"/api/operator-conversation-console/layer","cli_flag":"--operator-conversation-console-v1","builder_function":"build_operator_conversation_console_v1","text_function":"operator_conversation_console_v1_text","runtime_directory":"data/autonomy/operator_conversation_console/","smoke_check":"neural-command-deck-dashboard-redesign-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v689-side-intelligence-panels","version":"689.0","era":"neural-command-deck-dashboard-redesign","dashboard_route":"/side-intelligence-panels","api_route":"/api/side-intelligence-panels/layer","cli_flag":"--side-intelligence-panels-v1","builder_function":"build_side_intelligence_panels_v1","text_function":"side_intelligence_panels_v1_text","runtime_directory":"data/autonomy/side_intelligence_panels/","smoke_check":"neural-command-deck-dashboard-redesign-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v690-neural-command-deck-dashboard-board","version":"690.0","era":"neural-command-deck-dashboard-redesign","dashboard_route":"/neural-command-deck-dashboard-board","api_route":"/api/neural-command-deck-dashboard-board/layer","cli_flag":"--neural-command-deck-dashboard-board-v1","builder_function":"build_neural_command_deck_dashboard_board_v1","text_function":"neural_command_deck_dashboard_board_v1_text","runtime_directory":"data/autonomy/neural_command_deck_dashboard_board/","smoke_check":"neural-command-deck-dashboard-redesign-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v686.0-v690.0 source surface manifest tokens: neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural-command-deck-dashboard-redesign-v1 layout_shell_writes_source=False thinking_core_executes_models=False conversation_console_sends_commands=False side_panels_execute_checks=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v691-interaction-focus-rail","version":"691.0","era":"neural-command-deck-interaction-refinement","dashboard_route":"/interaction-focus-rail","api_route":"/api/interaction-focus-rail/layer","cli_flag":"--interaction-focus-rail-v1","builder_function":"build_interaction_focus_rail_v1","text_function":"interaction_focus_rail_v1_text","runtime_directory":"data/autonomy/interaction_focus_rail/","smoke_check":"neural-command-deck-interaction-refinement-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v692-interaction-safe-input-deck","version":"692.0","era":"neural-command-deck-interaction-refinement","dashboard_route":"/interaction-safe-input-deck","api_route":"/api/interaction-safe-input-deck/layer","cli_flag":"--interaction-safe-input-deck-v1","builder_function":"build_interaction_safe_input_deck_v1","text_function":"interaction_safe_input_deck_v1_text","runtime_directory":"data/autonomy/interaction_safe_input_deck/","smoke_check":"neural-command-deck-interaction-refinement-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v693-panel-density-priority-tuning","version":"693.0","era":"neural-command-deck-interaction-refinement","dashboard_route":"/panel-density-priority-tuning","api_route":"/api/panel-density-priority-tuning/layer","cli_flag":"--panel-density-priority-tuning-v1","builder_function":"build_panel_density_priority_tuning_v1","text_function":"panel_density_priority_tuning_v1_text","runtime_directory":"data/autonomy/panel_density_priority_tuning/","smoke_check":"neural-command-deck-interaction-refinement-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v694-context-telemetry-affordance","version":"694.0","era":"neural-command-deck-interaction-refinement","dashboard_route":"/context-telemetry-affordance","api_route":"/api/context-telemetry-affordance/layer","cli_flag":"--context-telemetry-affordance-v1","builder_function":"build_context_telemetry_affordance_v1","text_function":"context_telemetry_affordance_v1_text","runtime_directory":"data/autonomy/context_telemetry_affordance/","smoke_check":"neural-command-deck-interaction-refinement-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v695-neural-command-deck-interaction-board","version":"695.0","era":"neural-command-deck-interaction-refinement","dashboard_route":"/neural-command-deck-interaction-board","api_route":"/api/neural-command-deck-interaction-board/layer","cli_flag":"--neural-command-deck-interaction-board-v1","builder_function":"build_neural_command_deck_interaction_board_v1","text_function":"neural_command_deck_interaction_board_v1_text","runtime_directory":"data/autonomy/neural_command_deck_interaction_board/","smoke_check":"neural-command-deck-interaction-refinement-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v691.0-v695.0 source surface manifest tokens: neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural-command-deck-interaction-refinement-v1 focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v696-autonomy-phase-zero-definition-contract","version":"696.0","era":"autonomy-phase-zero-readiness-harness","dashboard_route":"/autonomy-phase-zero-definition-contract","api_route":"/api/autonomy-phase-zero-definition-contract/layer","cli_flag":"--autonomy-phase-zero-definition-contract-v1","builder_function":"build_autonomy_phase_zero_definition_contract_v1","text_function":"autonomy_phase_zero_definition_contract_v1_text","runtime_directory":"data/autonomy/autonomy_phase_zero_definition_contract/","smoke_check":"autonomy-phase-zero-readiness-harness-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v697-observation-only-cycle-simulator","version":"697.0","era":"autonomy-phase-zero-readiness-harness","dashboard_route":"/observation-only-cycle-simulator","api_route":"/api/observation-only-cycle-simulator/layer","cli_flag":"--observation-only-cycle-simulator-v1","builder_function":"build_observation_only_cycle_simulator_v1","text_function":"observation_only_cycle_simulator_v1_text","runtime_directory":"data/autonomy/observation_only_cycle_simulator/","smoke_check":"autonomy-phase-zero-readiness-harness-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v698-no-mutation-autonomy-boundary-guard","version":"698.0","era":"autonomy-phase-zero-readiness-harness","dashboard_route":"/no-mutation-autonomy-boundary-guard","api_route":"/api/no-mutation-autonomy-boundary-guard/layer","cli_flag":"--no-mutation-autonomy-boundary-guard-v1","builder_function":"build_no_mutation_autonomy_boundary_guard_v1","text_function":"no_mutation_autonomy_boundary_guard_v1_text","runtime_directory":"data/autonomy/no_mutation_autonomy_boundary_guard/","smoke_check":"autonomy-phase-zero-readiness-harness-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v699-autonomy-phase-zero-handoff-packet","version":"699.0","era":"autonomy-phase-zero-readiness-harness","dashboard_route":"/autonomy-phase-zero-handoff-packet","api_route":"/api/autonomy-phase-zero-handoff-packet/layer","cli_flag":"--autonomy-phase-zero-handoff-packet-v1","builder_function":"build_autonomy_phase_zero_handoff_packet_v1","text_function":"autonomy_phase_zero_handoff_packet_v1_text","runtime_directory":"data/autonomy/autonomy_phase_zero_handoff_packet/","smoke_check":"autonomy-phase-zero-readiness-harness-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v700-autonomy-phase-zero-readiness-board","version":"700.0","era":"autonomy-phase-zero-readiness-harness","dashboard_route":"/autonomy-phase-zero-readiness-board","api_route":"/api/autonomy-phase-zero-readiness-board/layer","cli_flag":"--autonomy-phase-zero-readiness-board-v1","builder_function":"build_autonomy_phase_zero_readiness_board_v1","text_function":"autonomy_phase_zero_readiness_board_v1_text","runtime_directory":"data/autonomy/autonomy_phase_zero_readiness_board/","smoke_check":"autonomy-phase-zero-readiness-harness-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v696.0-v700.0 source surface manifest tokens: autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy-phase-zero-readiness-harness-v1 phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False

# v711.0-v760.0 UI stabilization and publish-safety repair tokens: self-development-cycle-v1 install-governance source_only_zip_excludes_data_tasks=True source_only_zip_excludes_data_approvals=True dashboard_version_marker_current=True api_version_marker_current=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v721-self-development-trial-review","version":"721.0","era":"self-development-cycle-trial-review","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-trial-review","builder_function":"build_self_development_trial_review","text_function":"self_development_trial_review_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-cycle-trial-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v722-protected-system-gate-expansion","version":"722.0","era":"self-development-cycle-trial-review","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-trial-review","builder_function":"classify_protected_systems","text_function":"self_development_trial_review_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-cycle-trial-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v723-prompt-regression-fixtures","version":"723.0","era":"self-development-cycle-trial-review","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-trial-review","builder_function":"build_self_development_trial_review","text_function":"self_development_trial_review_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-cycle-trial-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v724-candidate-quality-scoring","version":"724.0","era":"self-development-cycle-trial-review","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-trial-review","builder_function":"generate_candidate_improvements","text_function":"self_development_trial_review_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-cycle-trial-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v725-self-development-cycle-dashboard","version":"760.0","era":"self-development-cycle-trial-review","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-trial-review","builder_function":"build_self_development_trial_review","text_function":"self_development_trial_review_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-cycle-trial-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v721.0-v760.0 self-development trial review tokens: self-development-cycle-trial-review-v1 self-development-cycle /self-development-cycle --self-development-trial-review PROMPT_REGRESSION_FIXTURES PROTECTED_SYSTEM_FIXTURES protected_systems_require_operator_approval=True source_mutation_allowed=False applies_patch=False executes_commands=False self_development_task_is_implementation_permission=False dashboard_route_review_only=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v726-self-development-dashboard-hardening","version":"726.0","era":"self-development-dashboard-trial-hardening","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-dashboard-hardening","builder_function":"build_self_development_dashboard_hardening_review","text_function":"self_development_dashboard_hardening_text","runtime_directory":"data/self_development_cycles/","smoke_check":"broad-smoke-triage-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v727-self-development-receipt-browser","version":"727.0","era":"self-development-dashboard-trial-hardening","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-dashboard-hardening","builder_function":"build_self_development_receipt_browser","text_function":"self_development_receipt_browser_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-implementation-proposal-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v728-broad-smoke-triage-report","version":"728.0","era":"self-development-dashboard-trial-hardening","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-smoke-triage","builder_function":"build_broad_smoke_triage_report","text_function":"broad_smoke_triage_text","runtime_directory":"none","smoke_check":"broad-smoke-triage-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v729-broad-smoke-low-risk-stale-triage","version":"729.0","era":"self-development-dashboard-trial-hardening","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-smoke-triage","builder_function":"classify_smoke_blocker","text_function":"broad_smoke_triage_text","runtime_directory":"none","smoke_check":"broad-smoke-triage-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v730-self-development-dashboard-smoke-triage-surface","version":"760.0","era":"self-development-dashboard-trial-hardening","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-dashboard-hardening","builder_function":"build_self_development_dashboard_hardening_review","text_function":"self_development_dashboard_hardening_text","runtime_directory":"data/self_development_cycles/","smoke_check":"broad-smoke-triage-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v726.0-v730.0 source surface tokens: self-development-implementation-proposal-v1 self-development-dashboard-trial-hardening-v1 /self-development-cycle --self-development-smoke-triage --self-development-dashboard-hardening build_broad_smoke_triage_report build_self_development_receipt_browser current_release_failure stale_legacy_expectation intentional_supervised_only_blocker missing_optional_dependency needs_manual_operator_approval runs_broad_smoke=False treats_blocked_as_pass=False applies_source_edits=False writes_memory=False creates_release=False expands_autonomy=False self_development_task_is_implementation_permission=False no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v731-self-development-implementation-proposal-packet","version":"731.0","era":"self-development-implementation-proposal","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-implementation-proposal","builder_function":"build_self_development_implementation_proposal","text_function":"self_development_implementation_proposal_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-implementation-proposal-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v732-self-development-proposal-cli","version":"732.0","era":"self-development-implementation-proposal","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-implementation-proposal","builder_function":"print_self_development_implementation_proposal","text_function":"self_development_implementation_proposal_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-implementation-proposal-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v733-dashboard-proposal-surface","version":"733.0","era":"self-development-implementation-proposal","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-dashboard-hardening","builder_function":"build_self_development_implementation_proposal","text_function":"self_development_implementation_proposal_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-implementation-proposal-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v734-low-risk-legacy-smoke-cleanup-boundary","version":"734.0","era":"self-development-implementation-proposal","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-implementation-proposal","builder_function":"build_self_development_implementation_proposal","text_function":"self_development_implementation_proposal_text","runtime_directory":"none","smoke_check":"self-development-implementation-proposal-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v735-implementation-proposal-smoke","version":"760.0","era":"self-development-implementation-proposal","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-implementation-proposal","builder_function":"build_self_development_implementation_proposal","text_function":"self_development_implementation_proposal_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-implementation-proposal-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v731.0-v760.0 source surface tokens: self-development-implementation-proposal-v1 --self-development-implementation-proposal build_self_development_implementation_proposal self_development_implementation_proposal_text proposal_packet_only_no_source_edits selected_task_preserved=True source_edits_authorized_by_this_packet=False task_is_implementation_permission=False protected_systems_require_operator_approval=True applies_source_edits=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v740-operator-approved-self-development-patch-draft","version":"760.0","era":"operator-approved-self-development-patch-draft","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-patch-draft","builder_function":"build_operator_approved_self_development_patch_draft","text_function":"operator_approved_self_development_patch_draft_text","runtime_directory":"data/self_development_cycles/","smoke_check":"operator-approved-self-development-patch-draft-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v736.0-v760.0 source surface tokens: operator-approved-self-development-patch-draft-v1 --self-development-patch-draft build_operator_approved_self_development_patch_draft operator_approved_self_development_patch_draft_text expected_self_development_patch_draft_approval_phrase validate_self_development_patch_draft_approval patch_draft_prepared_not_applied no_patch_draft_without_explicit_operator_approval draft_is_not_application_permission=True requires_separate_approval_before_patch_application=True source_edits_authorized_by_this_packet=False applies_source_edits=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v745-operator-approved-self-development-patch-application-trial","version":"760.0","era":"operator-approved-self-development-patch-application","dashboard_route":"/self-development-cycle","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-patch-application","builder_function":"build_operator_approved_self_development_patch_application_trial","text_function":"operator_approved_self_development_patch_application_trial_text","runtime_directory":"data/self_development_cycles/","smoke_check":"operator-approved-self-development-patch-application-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
])

# v741.0-v760.0 source surface tokens: operator-approved-self-development-patch-application-v1 --self-development-patch-application build_operator_approved_self_development_patch_application_trial operator_approved_self_development_patch_application_trial_text expected_self_development_patch_application_approval_phrase validate_self_development_patch_application_approval application_blocked_no_concrete_diff captures_preimage_hashes=True low_risk_file_allowlist_enforced=True blocks_protected_targets=True applies_source_edits=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False stops_before_release_publish_autonomy=True current_smoke_debt_reduction legacy_blockers_classified_not_overridden=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v746-self-development-application-receipt-review","version":"760.0","era":"self-development-smoke-debt-ledger","dashboard_route":"/self-development-smoke-debt","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-application-receipt-review","builder_function":"build_self_development_application_receipt_review","text_function":"self_development_application_receipt_review_text","runtime_directory":"data/self_development_cycles/","smoke_check":"self-development-application-receipt-review-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v747-current-smoke-debt-ledger","version":"760.0","era":"self-development-smoke-debt-ledger","dashboard_route":"/self-development-smoke-debt","api_route":"/api/self-development-cycle/layer","cli_flag":"--current-smoke-debt-ledger","builder_function":"build_current_smoke_debt_ledger","text_function":"current_smoke_debt_ledger_text","runtime_directory":"data/self_development_cycles/","smoke_check":"current-smoke-debt-ledger-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":True,"status":"represented"},
    {"surface_id":"v748-low-risk-smoke-debt-cleanup-candidates","version":"760.0","era":"self-development-smoke-debt-ledger","dashboard_route":"/self-development-smoke-debt","api_route":"/api/self-development-cycle/layer","cli_flag":"--low-risk-smoke-debt-cleanup-candidates","builder_function":"build_low_risk_smoke_debt_cleanup_candidates","text_function":"low_risk_smoke_debt_cleanup_candidates_text","runtime_directory":"none","smoke_check":"current-smoke-debt-ledger-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v749-self-development-smoke-debt-dashboard","version":"760.0","era":"self-development-smoke-debt-ledger","dashboard_route":"/self-development-smoke-debt","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-smoke-debt-dashboard","builder_function":"build_self_development_smoke_debt_dashboard","text_function":"self_development_smoke_debt_dashboard_text","runtime_directory":"none","smoke_check":"current-smoke-debt-ledger-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v751-self-development-api-surface-truth-review","version":"760.0","era":"self-development-api-surface-truth","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--self-development-api-surface-truth-review","builder_function":"build_self_development_api_surface_truth_review","text_function":"self_development_api_surface_truth_review_text","runtime_directory":"none","smoke_check":"self-development-api-surface-truth-review-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v760.0 source surface tokens: self-development-api-surface-truth-review-v1 /self-development-smoke-debt not_exposed_review_only --self-development-api-surface-truth-review build_self_development_api_surface_truth_review self_development_api_surface_truth_review_text api_route_presence_is_live_probed=True unsupported_claims_are_reported_not_repaired=True manifest_claims_are_not_authorization=True applies_source_edits=False creates_concrete_diff=False implements_api_routes=False modifies_manifest=False runs_broad_smoke=False marks_blockers_as_pass=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v755-self-development-api-route-repair","version":"760.0","era":"self-development-api-route-repair","dashboard_route":"/self-development-smoke-debt","api_route":"/api/self-development-cycle/layer","cli_flag":"--self-development-api-surface-truth-review","builder_function":"build_self_development_cycle_api_layer","text_function":"self_development_api_surface_truth_review_text","runtime_directory":"none","smoke_check":"self-development-api-route-repair-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v760.0 API route repair source surface tokens: self-development-api-route-repair-v1 /api/self-development-cycle/layer build_self_development_cycle_api_layer build_manifest_gated_self_development_api_parity manifest_claimed_api_routes_must_dispatch=True api_404_is_release_blocking_for_claimed_routes=True api_route_presence_is_live_probed=True route_repair_is_review_only=True manifest_claims_are_not_authorization=True applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False marks_blockers_as_pass=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v746.0-v760.0 source surface tokens: self-development-application-receipt-review-v1 current-smoke-debt-ledger-v1 /self-development-smoke-debt --self-development-application-receipt-review --current-smoke-debt-ledger --low-risk-smoke-debt-cleanup-candidates --self-development-smoke-debt-dashboard build_self_development_application_receipt_review self_development_application_receipt_review_text build_current_smoke_debt_ledger current_smoke_debt_ledger_text build_low_risk_smoke_debt_cleanup_candidates build_self_development_smoke_debt_dashboard receipt_is_not_success=True blocked_trial_is_not_success=True source_edits_implied_by_receipt=False marks_blockers_as_pass=False runs_broad_smoke=False creates_concrete_diff=False applies_source_edits=False executes_commands=False writes_memory=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v760-self-development-cycle-duplicate-cleanup","version":"760.0","era":"self-development-cycle-duplicate-cleanup","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--self-development-cycle-duplicate-cleanup","builder_function":"build_self_development_cycle_duplicate_cleanup_review","text_function":"self_development_cycle_duplicate_cleanup_review_text","runtime_directory":"none","smoke_check":"self-development-cycle-duplicate-cleanup-v1","smoke_segment":"install-governance","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v760.0 duplicate cleanup source surface tokens: self-development-cycle-duplicate-cleanup-v1 /self-development-smoke-debt not_exposed_review_only --self-development-cycle-duplicate-cleanup build_self_development_cycle_duplicate_cleanup_review self_development_cycle_duplicate_cleanup_review_text duplicate_definition_count=0 retired_shadowed_v720_helpers=True stale_self_maintenance_exact_version_smoke_debt_reduced=True applies_source_edits_beyond_this_operator_patch=False creates_concrete_diff=False runs_broad_smoke=False marks_blockers_as_pass=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([

    {"surface_id":"v770-current-smoke-debt-ledger-reconciliation","version":"845.0","era":"smoke-debt-ledger-reconciliation","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--current-smoke-debt-ledger-reconciliation","builder_function":"build_current_smoke_debt_ledger_reconciliation_review","text_function":"current_smoke_debt_ledger_reconciliation_review_text","runtime_directory":"none","smoke_check":"current-smoke-debt-ledger-reconciliation-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v765-legacy-self-maintenance-smoke-blocker-review","version":"845.0","era":"legacy-self-maintenance-smoke-debt-cleanup","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--legacy-self-maintenance-smoke-blocker-review","builder_function":"build_legacy_self_maintenance_smoke_blocker_review","text_function":"legacy_self_maintenance_smoke_blocker_review_text","runtime_directory":"none","smoke_check":"legacy-self-maintenance-smoke-blocker-review-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 smoke debt ledger reconciliation source surface tokens: current-smoke-debt-ledger-reconciliation-v1 /self-development-smoke-debt not_exposed_review_only --current-smoke-debt-ledger-reconciliation build_current_smoke_debt_ledger_reconciliation_review current_smoke_debt_ledger_reconciliation_review_text resolved_legacy_smoke_debt_not_active=True install_regression_recent_expected_status=pass next_broad_smoke_recovery_candidates=True marks_blockers_as_pass=False hides_unresolved_failures=False runs_broad_smoke=False applies_source_edits=False creates_concrete_diff=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v845.0 legacy self-maintenance smoke blocker review source surface tokens: legacy-self-maintenance-smoke-blocker-review-v1 /self-development-smoke-debt not_exposed_review_only --legacy-self-maintenance-smoke-blocker-review build_legacy_self_maintenance_smoke_blocker_review legacy_self_maintenance_smoke_blocker_review_text repaired_legacy_self_maintenance_blockers=True install_regression_recent_expected_status=pass stale_exact_version_expectation_repaired=True marks_blockers_as_pass=False runs_broad_smoke=False applies_source_edits_beyond_this_operator_patch=False creates_concrete_diff=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v780-current-audit-wording-cleanup","version":"845.0","era":"current-audit-wording-cleanup","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--current-audit-wording-cleanup","builder_function":"build_current_audit_wording_cleanup_review","text_function":"current_audit_wording_cleanup_review_text","runtime_directory":"none","smoke_check":"current-audit-wording-cleanup-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v780-manifest-generation-prep-review","version":"845.0","era":"manifest-generation-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-generation-prep-review","builder_function":"build_manifest_generation_prep_review","text_function":"manifest_generation_prep_review_text","runtime_directory":"none","smoke_check":"current-audit-wording-cleanup-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 current audit wording cleanup and manifest generation prep source surface tokens: current-audit-wording-cleanup-v1 manifest-generation-prep-review-v1 /self-development-smoke-debt not_exposed_review_only --current-audit-wording-cleanup --manifest-generation-prep-review build_current_audit_wording_cleanup_review current_audit_wording_cleanup_review_text build_manifest_generation_prep_review manifest_generation_prep_review_text stale_current_audit_wording_clean=True historical_release_references_allowed=True manifest_generation_prep_is_review_only=True generates_surfaces=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v780-manifest-gated-surface-validation","version":"845.0","era":"manifest-gated-surface-validation","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-gated-surface-validation","builder_function":"build_manifest_gated_surface_validation_review","text_function":"manifest_gated_surface_validation_review_text","runtime_directory":"none","smoke_check":"manifest-gated-surface-validation-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest-gated surface validation source surface tokens: manifest-gated-surface-validation-v1 /self-development-smoke-debt not_exposed_review_only --manifest-gated-surface-validation build_manifest_gated_surface_validation_review manifest_gated_surface_validation_review_text validation_is_review_only=True generates_surfaces=False manifest_drives_wiring=False declared_and_live declared_but_missing live_but_undeclared historical_only review_only not_applicable applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v785-manifest-driven-surface-registry-pilot","version":"845.0","era":"manifest-driven-surface-registry-pilot","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-driven-surface-registry-pilot","builder_function":"build_manifest_driven_surface_registry_pilot_review","text_function":"manifest_driven_surface_registry_pilot_review_text","runtime_directory":"none","smoke_check":"manifest-driven-surface-registry-pilot-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v785-manifest-surface-generation-readiness","version":"845.0","era":"manifest-surface-generation-readiness","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-surface-generation-readiness","builder_function":"build_manifest_surface_generation_readiness_review","text_function":"manifest_surface_generation_readiness_review_text","runtime_directory":"none","smoke_check":"manifest-driven-surface-registry-pilot-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest-driven surface registry pilot source surface tokens: manifest-driven-surface-registry-pilot-v1 /self-development-smoke-debt not_exposed_review_only --manifest-driven-surface-registry-pilot --manifest-surface-generation-readiness build_manifest_driven_surface_registry_pilot_review manifest_driven_surface_registry_pilot_review_text build_manifest_surface_generation_readiness_review manifest_surface_generation_readiness_review_text registry_pilot_is_review_only=True pilot_registers_one_surface=True generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False safe_for_manifest_registration safe_for_generated_validation_only manual_until_further_review protected_operator_controlled never_autonomous applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v790-manifest-registry-expanded-review-surfaces","version":"845.0","era":"manifest-registry-expansion","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-registry-expanded-review-surfaces","builder_function":"build_manifest_registry_expanded_review_surfaces_review","text_function":"manifest_registry_expanded_review_surfaces_review_text","runtime_directory":"none","smoke_check":"manifest-registry-expanded-review-surfaces-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v790-manifest-registry-generation-readiness-scoring","version":"845.0","era":"manifest-registry-expansion-readiness-scoring","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-registry-generation-readiness-scoring","builder_function":"build_manifest_registry_generation_readiness_scoring_review","text_function":"manifest_registry_generation_readiness_scoring_review_text","runtime_directory":"none","smoke_check":"manifest-registry-expanded-review-surfaces-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest registry expansion source surface tokens: manifest-registry-expanded-review-surfaces-v1 /self-development-smoke-debt not_exposed_review_only --manifest-registry-expanded-review-surfaces --manifest-registry-generation-readiness-scoring build_manifest_registry_expanded_review_surfaces_review manifest_registry_expanded_review_surfaces_review_text build_manifest_registry_generation_readiness_scoring_review manifest_registry_generation_readiness_scoring_review_text registry_expansion_is_review_only=True selected_surface_count=8 additional_surface_count=7 registry_only_ready validation_generation_ready manual_wiring_required blocked_by_protected_system never_generate generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v795-manifest-registry-drift-detection","version":"845.0","era":"manifest-registry-drift-detection","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-registry-drift-detection","builder_function":"build_manifest_registry_drift_detection_review","text_function":"manifest_registry_drift_detection_review_text","runtime_directory":"none","smoke_check":"manifest-registry-drift-detection-v1","smoke_segment":"install-regression-recent","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest registry drift detection source surface tokens: manifest-registry-drift-detection-v1 /self-development-smoke-debt not_exposed_review_only --manifest-registry-drift-detection build_manifest_registry_drift_detection_review manifest_registry_drift_detection_review_text registry_drift_detection_is_review_only=True registered_surface_count=8 drift_count=0 in_sync_count=8 missing_builder missing_text_renderer missing_cli_flag missing_dashboard_card missing_smoke safety_boundary_drift autonomy_boundary_drift manual_review_required generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False repairs_drift=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v810-self-development-manifest-guided-generated-validation-probe","version":"845.0","era":"self-development-manifest-guided-generated-validation-probe","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-generated-validation-probe","builder_function":"build_manifest_guided_generated_validation_probe_review","text_function":"manifest_guided_generated_validation_probe_review_text","runtime_directory":"none","smoke_check":"manifest-guided-generated-validation-probe-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v800-manifest-guided-validation-probe-dry-run","version":"845.0","era":"manifest-guided-validation-probe-dry-run","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-validation-probe-dry-run","builder_function":"build_manifest_guided_validation_probe_dry_run_review","text_function":"manifest_guided_validation_probe_dry_run_review_text","runtime_directory":"none","smoke_check":"manifest-guided-validation-probe-dry-run-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest-guided validation probe dry-run source surface tokens: manifest-guided-validation-probe-dry-run-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-validation-probe-dry-run build_manifest_guided_validation_probe_dry_run_review manifest_guided_validation_probe_dry_run_review_text validation_probe_dry_run_is_review_only=True dry_run_selected_surface_count=1 planned_probe_check_count=8 selected_surface_id=v780-manifest-gated-surface-validation generates_validation_probe=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v845.0 manifest-guided generated validation probe source surface tokens: manifest-guided-generated-validation-probe-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-generated-validation-probe build_manifest_guided_generated_validation_probe_review manifest_guided_generated_validation_probe_review_text generated_validation_probe_is_review_only=True generated_probe_selected_surface_count=1 generated_probe_check_count=8 selected_surface_id=v780-manifest-gated-surface-validation smoke_segment_parity_status=deferred generates_validation_probe=True generates_live_validation_probe=False generated_wiring_activated=False writes_probe_file=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v815-manifest-smoke-segment-parity-drift","version":"845.0","era":"manifest-smoke-segment-parity-drift","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-smoke-segment-parity-drift","builder_function":"build_manifest_smoke_segment_parity_drift_review","text_function":"manifest_smoke_segment_parity_drift_review_text","runtime_directory":"none","smoke_check":"manifest-smoke-segment-parity-drift-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest smoke segment parity drift source surface tokens: manifest-smoke-segment-parity-drift-v1 /self-development-smoke-debt not_exposed_review_only --manifest-smoke-segment-parity-drift build_manifest_smoke_segment_parity_drift_review manifest_smoke_segment_parity_drift_review_text manifest_smoke_segment_parity_drift_is_review_only=True manifest_surface_count surfaces_with_smoke_checks matching_segment_count mismatching_segment_count missing_live_segment_count known_mismatch_detected=True auto_repair_enabled=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v820-manifest-smoke-segment-parity-repair-packet","version":"845.0","era":"manifest-smoke-segment-parity-repair-packet","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-smoke-segment-parity-repair-packet","builder_function":"build_manifest_smoke_segment_parity_repair_packet_review","text_function":"manifest_smoke_segment_parity_repair_packet_review_text","runtime_directory":"none","smoke_check":"manifest-smoke-segment-parity-repair-packet-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest smoke segment parity repair packet source surface tokens: manifest-smoke-segment-parity-repair-packet-v1 /self-development-smoke-debt not_exposed_review_only --manifest-smoke-segment-parity-repair-packet build_manifest_smoke_segment_parity_repair_packet_review manifest_smoke_segment_parity_repair_packet_review_text manifest_smoke_segment_parity_repair_packet_is_review_only=True reviewed_surface_count mismatching_segment_count proposed_repair_count missing_live_segment_count known_v780_repair_proposed=True auto_apply_enabled=False applies_repair=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console
RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v825-manifest-smoke-segment-repair-application","version":"845.0","era":"manifest-smoke-segment-repair-application","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-smoke-segment-repair-application","builder_function":"build_manifest_smoke_segment_repair_application_review","text_function":"manifest_smoke_segment_repair_application_review_text","runtime_directory":"none","smoke_check":"manifest-smoke-segment-repair-application-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest smoke segment repair application source surface tokens: manifest-smoke-segment-repair-application-v1 /self-development-smoke-debt not_exposed_review_only --manifest-smoke-segment-repair-application build_manifest_smoke_segment_repair_application_review manifest_smoke_segment_repair_application_review_text manifest_smoke_segment_repair_application_is_review_only=True operator_approved_application=True reviewed_surface_count corrected_segment_count mismatching_segment_count_after_application=0 proposed_repair_count_after_application=0 known_v780_segment_corrected=True writes_manifest=True writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=True creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v830-manifest-segment-parity-enforcement-gate","version":"845.0","era":"manifest-segment-parity-enforcement-gate","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-segment-parity-enforcement-gate","builder_function":"build_manifest_segment_parity_enforcement_gate_review","text_function":"manifest_segment_parity_enforcement_gate_review_text","runtime_directory":"none","smoke_check":"manifest-segment-parity-enforcement-gate-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest segment parity enforcement gate source surface tokens: manifest-segment-parity-enforcement-gate-v1 /self-development-smoke-debt not_exposed_review_only --manifest-segment-parity-enforcement-gate build_manifest_segment_parity_enforcement_gate_review manifest_segment_parity_enforcement_gate_review_text manifest_segment_parity_enforcement_gate_is_review_only=True release_blocking=True enforcement_gate_passed=True mismatching_segment_count=0 missing_live_segment_count=0 auto_repair_enabled=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v835-manifest-guided-validation-probe-expansion-readiness","version":"845.0","era":"manifest-guided-validation-probe-expansion-readiness","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-validation-probe-expansion-readiness","builder_function":"build_manifest_guided_validation_probe_expansion_readiness_review","text_function":"manifest_guided_validation_probe_expansion_readiness_review_text","runtime_directory":"none","smoke_check":"manifest-guided-validation-probe-expansion-readiness-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest-guided validation probe expansion readiness source surface tokens: manifest-guided-validation-probe-expansion-readiness-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-validation-probe-expansion-readiness build_manifest_guided_validation_probe_expansion_readiness_review manifest_guided_validation_probe_expansion_readiness_review_text expansion_readiness_is_review_only=True registered_review_surface_count currently_supported_probe_surface_count=1 recommended_expansion_surface_count=3 blocked_surface_count=0 readiness_passed=True expansion_mode=review_only generated_wiring_enabled=False generated_wiring_activated=False generates_multi_surface_probe=False generates_validation_probe=False generates_live_validation_probe=False writes_probe_file=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v840-manifest-guided-multi-surface-validation-probe-dry-run","version":"845.0","era":"manifest-guided-multi-surface-validation-probe-dry-run","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-multi-surface-validation-probe-dry-run","builder_function":"build_manifest_guided_multi_surface_validation_probe_dry_run_review","text_function":"manifest_guided_multi_surface_validation_probe_dry_run_review_text","runtime_directory":"none","smoke_check":"manifest-guided-multi-surface-validation-probe-dry-run-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v845-manifest-guided-multi-surface-generated-validation-probe-packet","version":"845.0","era":"manifest-guided-multi-surface-generated-validation-probe-packet","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-multi-surface-generated-validation-probe-packet","builder_function":"build_manifest_guided_multi_surface_generated_validation_probe_packet_review","text_function":"manifest_guided_multi_surface_generated_validation_probe_packet_review_text","runtime_directory":"none","smoke_check":"manifest-guided-multi-surface-generated-validation-probe-packet-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v845.0 manifest-guided multi-surface validation probe dry-run source surface tokens: manifest-guided-multi-surface-validation-probe-dry-run-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-multi-surface-validation-probe-dry-run build_manifest_guided_multi_surface_validation_probe_dry_run_review manifest_guided_multi_surface_validation_probe_dry_run_review_text multi_surface_validation_probe_dry_run_is_review_only=True selected_surface_count=3 planned_probe_check_count_per_surface=8 total_planned_probe_check_count=24 segment_parity_gate_passed=True generated_wiring_enabled=False generated_wiring_activated=False writes_probe_files=False generates_live_validation_probe=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


# v845.0 manifest-guided multi-surface generated validation probe packet source surface tokens: manifest-guided-multi-surface-generated-validation-probe-packet-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-multi-surface-generated-validation-probe-packet build_manifest_guided_multi_surface_generated_validation_probe_packet_review manifest_guided_multi_surface_generated_validation_probe_packet_review_text multi_surface_generated_validation_probe_packet_is_review_only=True selected_surface_count=3 generated_probe_packet_count=3 generated_probe_check_count_per_surface=8 total_generated_probe_check_count=24 segment_parity_gate_passed=True expansion_readiness_passed=True dry_run_prerequisite_passed=True writes_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v850-manifest-guided-multi-surface-probe-packet-consistency-gate","version":"885.0","era":"manifest-guided-multi-surface-probe-packet-consistency-gate","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-multi-surface-probe-packet-consistency-gate","builder_function":"build_manifest_guided_multi_surface_probe_packet_consistency_gate_review","text_function":"manifest_guided_multi_surface_probe_packet_consistency_gate_review_text","runtime_directory":"none","smoke_check":"manifest-guided-multi-surface-probe-packet-consistency-gate-v1","smoke_segment":"install-dashboard","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v850.0 manifest-guided multi-surface probe packet consistency gate source surface tokens: manifest-guided-multi-surface-probe-packet-consistency-gate-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-multi-surface-probe-packet-consistency-gate build_manifest_guided_multi_surface_probe_packet_consistency_gate_review manifest_guided_multi_surface_probe_packet_consistency_gate_review_text multi_surface_probe_packet_consistency_gate_is_review_only=True selected_surface_count=3 dry_run_surface_count=3 generated_packet_surface_count=3 expected_surface_ids_match=True check_count_per_surface=8 total_check_count=24 segment_parity_gate_passed=True expansion_readiness_passed=True dry_run_prerequisite_passed=True generated_packet_prerequisite_passed=True consistency_gate_passed=True release_blocking=True review_only=True writes_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v855-manifest-guided-sandbox-probe-file-generation-readiness","version":"885.0","era":"manifest-guided-sandbox-probe-file-generation-readiness","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-sandbox-probe-file-generation-readiness","builder_function":"build_manifest_guided_sandbox_probe_file_generation_readiness_review","text_function":"manifest_guided_sandbox_probe_file_generation_readiness_review_text","runtime_directory":"none","smoke_check":"manifest-guided-sandbox-probe-file-generation-readiness-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v865.0 manifest-guided sandbox probe file generation readiness source surface tokens: manifest-guided-sandbox-probe-file-generation-readiness-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-sandbox-probe-file-generation-readiness build_manifest_guided_sandbox_probe_file_generation_readiness_review manifest_guided_sandbox_probe_file_generation_readiness_review_text sandbox_probe_file_generation_readiness_is_review_only=True selected_surface_count=3 eligible_surface_count=3 planned_sandbox_probe_file_count=3 generated_probe_file_count=0 consistency_gate_passed=True consistency_gate_prerequisite_passed=True policy_count=8 policies_passed=True readiness_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v860-manifest-guided-sandbox-probe-file-generation-dry-run","version":"885.0","era":"manifest-guided-sandbox-probe-file-generation-dry-run","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-guided-sandbox-probe-file-generation-dry-run","builder_function":"build_manifest_guided_sandbox_probe_file_generation_dry_run","text_function":"manifest_guided_sandbox_probe_file_generation_dry_run_text","runtime_directory":"none","smoke_check":"manifest-guided-sandbox-probe-file-generation-dry-run-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v865.0 manifest-guided sandbox probe file generation dry-run source surface tokens: manifest-guided-sandbox-probe-file-generation-dry-run-v1 /self-development-smoke-debt not_exposed_review_only --manifest-guided-sandbox-probe-file-generation-dry-run build_manifest_guided_sandbox_probe_file_generation_dry_run manifest_guided_sandbox_probe_file_generation_dry_run_text sandbox_probe_file_generation_dry_run_is_review_only=True selected_surface_count=3 readiness_prerequisite_passed=True planned_probe_file_count=3 preview_probe_file_count=3 written_probe_file_count=0 generated_probe_file_count=0 policy_count=12 policies_passed=True dry_run_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v865-operator-approved-sandbox-probe-file-generation-trial","version":"885.0","era":"operator-approved-sandbox-probe-file-generation-trial","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--operator-approved-sandbox-probe-file-generation-trial","builder_function":"build_operator_approved_sandbox_probe_file_generation_trial","text_function":"operator_approved_sandbox_probe_file_generation_trial_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"operator-approved-sandbox-probe-file-generation-trial-v1","smoke_segment":"install-live-trial","authority_level":"operator_approved_sandbox_write","writes_files":True,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v865.0 operator-approved sandbox probe file generation trial source surface tokens: operator-approved-sandbox-probe-file-generation-trial-v1 /self-development-smoke-debt not_exposed_review_only --operator-approved-sandbox-probe-file-generation-trial build_operator_approved_sandbox_probe_file_generation_trial operator_approved_sandbox_probe_file_generation_trial_text operator_approved_sandbox_probe_file_generation_trial=True selected_surface_count=3 readiness_prerequisite_passed=True dry_run_prerequisite_passed=True operator_approval_required=True operator_approval_present=True planned_probe_file_count=3 preview_probe_file_count=3 written_probe_file_count=3 sandbox_generated_probe_file_count=3 generated_live_probe_file_count=0 file_content_matches_preview=True policy_count=14 policies_passed=True generation_trial_passed=True release_blocking=True review_only=False operator_approved_sandbox_write=True writes_probe_files=True generates_sandbox_probe_files=True generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v870-sandbox-probe-file-verification-and-cleanup-review","version":"885.0","era":"sandbox-probe-file-verification-and-cleanup-review","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--sandbox-probe-file-verification-and-cleanup-review","builder_function":"build_sandbox_probe_file_verification_and_cleanup_review","text_function":"sandbox_probe_file_verification_and_cleanup_review_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"sandbox-probe-file-verification-and-cleanup-review-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v870.0 sandbox probe file verification and cleanup review source surface tokens: sandbox-probe-file-verification-and-cleanup-review-v1 /self-development-smoke-debt not_exposed_review_only --sandbox-probe-file-verification-and-cleanup-review build_sandbox_probe_file_verification_and_cleanup_review sandbox_probe_file_verification_and_cleanup_review_text sandbox_probe_file_verification_and_cleanup_review_is_review_only=True sandbox_probe_file_count=3 expected_probe_file_count=3 unexpected_probe_file_count=0 missing_probe_file_count=0 files_match_dry_run_preview=True all_paths_inside_sandbox_root=True unsafe_import_count=0 command_execution_detected=False memory_write_detected=False approval_write_detected=False release_write_detected=False scheduler_write_detected=False network_access_detected=False live_wiring_detected=False cleanup_plan_available=True cleanup_review_only=True verification_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v875-sandbox-probe-execution-harness-readiness-review","version":"885.0","era":"sandbox-probe-execution-harness-readiness-review","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--sandbox-probe-execution-harness-readiness-review","builder_function":"build_sandbox_probe_execution_harness_readiness_review","text_function":"sandbox_probe_execution_harness_readiness_review_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"sandbox-probe-execution-harness-readiness-review-v1","smoke_segment":"install-core","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v880-operator-approved-sandbox-probe-execution-trial","version":"885.0","era":"operator-approved-sandbox-probe-execution-trial","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_operator_approved_sandbox_execution","cli_flag":"--operator-approved-sandbox-probe-execution-trial","builder_function":"build_operator_approved_sandbox_probe_execution_trial","text_function":"operator_approved_sandbox_probe_execution_trial_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"operator-approved-sandbox-probe-execution-trial-v1","smoke_segment":"install-live-trial","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v885.0 sandbox probe execution harness readiness source surface tokens: sandbox-probe-execution-harness-readiness-review-v1 /self-development-smoke-debt not_exposed_review_only --sandbox-probe-execution-harness-readiness-review build_sandbox_probe_execution_harness_readiness_review sandbox_probe_execution_harness_readiness_review_text sandbox_probe_execution_harness_readiness_review_is_review_only=True sandbox_probe_file_count=3 verification_prerequisite_passed=True execution_harness_defined=True execution_performed=False probe_execution_count=0 command_allowlist_defined=True timeout_policy_defined=True network_access_allowed=False scheduler_access_allowed=False memory_write_allowed=False approval_write_allowed=False release_write_allowed=False source_write_allowed=False live_wiring_allowed=False stdout_capture_defined=True stderr_capture_defined=True result_schema_defined=True cleanup_plan_available=True operator_approval_required=True single_use_approval_required=True approval_burnout_required=True policy_count=36 policies_passed=True readiness_passed=True release_blocking=True review_only=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False executes_probe_files=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v885.0 operator-approved sandbox probe execution trial source surface tokens: operator-approved-sandbox-probe-execution-trial-v1 /self-development-smoke-debt not_exposed_operator_approved_sandbox_execution --operator-approved-sandbox-probe-execution-trial build_operator_approved_sandbox_probe_execution_trial operator_approved_sandbox_probe_execution_trial_text operator_approved_sandbox_probe_execution_trial=True sandbox_probe_file_count=3 probe_execution_count=3 probe_execution_pass_count=3 probe_execution_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 execution_trial_passed=True release_blocking=True review_only=False operator_approved_sandbox_execution=True writes_probe_files=False deletes_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v885.0 sandbox probe execution result review and promotion readiness source surface tokens: sandbox-probe-execution-result-review-and-promotion-readiness-v1 /self-development-smoke-debt not_exposed_review_only --sandbox-probe-execution-result-review-and-promotion-readiness build_sandbox_probe_execution_result_review_and_promotion_readiness sandbox_probe_execution_result_review_and_promotion_readiness_text sandbox_probe_execution_result_review_and_promotion_readiness=True sandbox_probe_file_count=3 probe_execution_count=3 probe_execution_pass_count=3 probe_execution_fail_count=0 promotion_candidate_count=3 promotion_blocker_count=0 promotion_readiness_passed=True live_integration_planned=False live_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False autonomy_expanded=False review_only=True writes_files=False writes_memory=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v890-live-probe-promotion-plan-review","version":"890.0","era":"live-probe-promotion-plan-review","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--live-probe-promotion-plan-review","builder_function":"build_live_probe_promotion_plan_review","text_function":"live_probe_promotion_plan_review_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"live-probe-promotion-plan-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v890.0 live probe promotion plan review source surface tokens: live-probe-promotion-plan-review-v1 /self-development-smoke-debt not_exposed_review_only --live-probe-promotion-plan-review build_live_probe_promotion_plan_review live_probe_promotion_plan_review_text live_probe_promotion_plan_review=True promotion_readiness_prerequisite_passed=True sandbox_probe_file_count=3 promotion_candidate_count=3 promotion_blocker_count=0 promotion_plan_created=True planned_live_probe_count=3 planned_smoke_registration_count=3 planned_dashboard_wiring_count=0 planned_api_wiring_count=0 planned_cli_wiring_count=0 source_files_to_modify_count=6 operator_approval_required=True single_use_approval_required=True approval_burnout_required=True rollback_plan_available=True live_integration_applied=False live_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False autonomy_expanded=False review_only=True writes_files=False writes_memory=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v895-operator-approved-live-probe-registration-trial","version":"895.0","era":"operator-approved-live-probe-registration-trial","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_operator_approved_live_registration","cli_flag":"--operator-approved-live-probe-registration-trial","builder_function":"build_operator_approved_live_probe_registration_trial","text_function":"operator_approved_live_probe_registration_trial_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"operator-approved-live-probe-registration-trial-v1","smoke_segment":"install-live-trial","authority_level":"operator_approved_single_use_trial","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v895.0 operator-approved live probe registration trial source surface tokens: operator-approved-live-probe-registration-trial-v1 /self-development-smoke-debt not_exposed_operator_approved_live_registration --operator-approved-live-probe-registration-trial build_operator_approved_live_probe_registration_trial operator_approved_live_probe_registration_trial_text operator_approved_live_probe_registration_trial=True promotion_plan_prerequisite_passed=True operator_approval_required=True operator_approval_present=True single_use_approval_required=True approval_burnout_required=True planned_live_probe_count=3 registered_live_probe_count=3 live_smoke_registration_applied=True dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False probe_execution_during_registration=False rollback_plan_available=True registration_trial_passed=True release_blocking=True review_only=False operator_approved_live_registration=True autonomy_expanded=False policy_count=49 policies_passed=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_dashboard_wiring=False activates_api_wiring=False activates_cli_wiring=False applies_source_edits=True applies_source_edits_only_for_live_smoke_registration=True creates_concrete_diff=False runs_broad_smoke=False executes_commands=True executes_probe_files=True writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True generated-live-probe-v780-manifest-gated-surface-validation-v1 generated-live-probe-v790-manifest-registry-expanded-review-surfaces-v1 generated-live-probe-v795-manifest-registry-drift-detection-v1 no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v900-live-registered-probe-verification-and-structural-hardening-review","version":"900.0","era":"live-registered-probe-verification-and-structural-hardening-review","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--live-registered-probe-verification-and-structural-hardening-review","builder_function":"build_live_registered_probe_verification_and_structural_hardening_review","text_function":"live_registered_probe_verification_and_structural_hardening_review_text","runtime_directory":"sandbox/generated_validation_probes","smoke_check":"live-registered-probe-verification-and-structural-hardening-review-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v900.0 live registered probe verification and structural hardening review source surface tokens: live-registered-probe-verification-and-structural-hardening-review-v1 /self-development-smoke-debt not_exposed_review_only --live-registered-probe-verification-and-structural-hardening-review build_live_registered_probe_verification_and_structural_hardening_review live_registered_probe_verification_and_structural_hardening_review_text live_registered_probe_verification_and_structural_hardening_review=True live_probe_registration_prerequisite_passed=True registered_live_probe_count=3 live_probe_execution_count=3 live_probe_pass_count=3 live_probe_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 rollback_plan_available=True runtime_registry_issue_detected=True nested_metadata_stale_check_gap_detected=False manifest_version_semantics_issue_detected=True autonomy_boundary_key_normalization_needed=True giant_file_cleanup_needed=True structural_hardening_plan_created=True live_registered_probe_verification_passed=True policy_count=31 policies_passed=True release_blocking=True review_only=True autonomy_expanded=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v906-v905-baseline-verification-and-manifest-version-semantics-prep","version":"906.0","era":"v905-baseline-verification-and-manifest-version-semantics-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--v905-baseline-verification-and-manifest-version-semantics-prep","builder_function":"build_v905_baseline_verification_and_manifest_version_semantics_prep","text_function":"v905_baseline_verification_and_manifest_version_semantics_prep_text","runtime_directory":"none","smoke_check":"v905-baseline-verification-and-manifest-version-semantics-prep-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v906.0 v905 baseline verification and manifest version semantics prep source surface tokens: v905-baseline-verification-and-manifest-version-semantics-prep-v1 /self-development-smoke-debt not_exposed_review_only --v905-baseline-verification-and-manifest-version-semantics-prep build_v905_baseline_verification_and_manifest_version_semantics_prep v905_baseline_verification_and_manifest_version_semantics_prep_text v905_containment_baseline_passed=True generated_probe_harness_present=True runtime_registry_issue_detected=False manifest_semantic_mismatch_count manifest_split_field_missing_count manifest_schema_migration_applied=False source_package_privacy_prep=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v907-manifest-version-semantics-split","version":"907.0","surface_origin_version":"907.0","manifest_representation_version":"907.0","last_verified_for_version":"907.0","era":"manifest-version-semantics-split","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-version-semantics-split","builder_function":"build_manifest_version_semantics_split_review","text_function":"manifest_version_semantics_split_review_text","runtime_directory":"none","smoke_check":"manifest-version-semantics-split-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v907.0 manifest version semantics split source surface tokens: manifest-version-semantics-split-v1 /self-development-smoke-debt not_exposed_review_only --manifest-version-semantics-split build_manifest_version_semantics_split_review manifest_version_semantics_split_review_text surface_origin_version manifest_representation_version last_verified_for_version legacy_version_field_retained_for_compatibility=True manifest_version_schema_split_applied=True historical_origin_mismatch_allowed=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v908-manifest-validation-normalization","version":"908.0","surface_origin_version":"908.0","manifest_representation_version":"908.0","last_verified_for_version":"908.0","era":"manifest-validation-normalization","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-validation-normalization","builder_function":"build_manifest_validation_normalization_review","text_function":"manifest_validation_normalization_review_text","runtime_directory":"none","smoke_check":"manifest-validation-normalization-v1","smoke_segment":"install-live-trial","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v908.0 manifest validation normalization source surface tokens: manifest-validation-normalization-v1 /self-development-smoke-debt not_exposed_review_only --manifest-validation-normalization build_manifest_validation_normalization_review manifest_validation_normalization_review_text build_manifest_validation_normalization_summary legacy_version_field_validation_mode=compatibility_only_not_current_state historical_origin_versions_allowed=True current_state_version_source=manifest_representation_version_and_last_verified_for_version legacy_version_is_current_state_source=False surface_origin_versions_required=True manifest_representation_versions_required_current=True last_verified_versions_required_current=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v909-source-package-privacy-deep-scan","version":"909.0","surface_origin_version":"909.0","manifest_representation_version":"909.0","last_verified_for_version":"909.0","era":"source-package-privacy-deep-scan","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--source-package-privacy-deep-scan","builder_function":"build_source_package_privacy_deep_scan_review","text_function":"source_package_privacy_deep_scan_review_text","runtime_directory":"none","smoke_check":"source-package-privacy-deep-scan-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v909.0 source package privacy deep scan source surface tokens: source-package-privacy-deep-scan-v1 /self-development-smoke-debt not_exposed_review_only --source-package-privacy-deep-scan build_source_package_privacy_deep_scan_review source_package_privacy_deep_scan_review_text privacy_deep_scan_summary private_content_findings_for_items content_scans_allowlisted_data=True blocks_private_self_state_content=True user_specific_identifier_detected runtime_goal_state_detected approval_or_action_trace_detected memory_like_state_detected data/self_model.json source_metadata_allowed=False release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v910-metadata-and-current-marker-gate-reconciliation","version":"910.0","surface_origin_version":"910.0","manifest_representation_version":"910.0","last_verified_for_version":"910.0","era":"metadata-and-current-marker-gate-reconciliation","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--metadata-and-current-marker-gate-reconciliation","builder_function":"build_metadata_and_current_marker_gate_reconciliation_review","text_function":"metadata_and_current_marker_gate_reconciliation_review_text","runtime_directory":"none","smoke_check":"metadata-and-current-marker-gate-reconciliation-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v910.0 metadata/current marker gate reconciliation source surface tokens: metadata-and-current-marker-gate-reconciliation-v1 /self-development-smoke-debt not_exposed_review_only --metadata-and-current-marker-gate-reconciliation build_metadata_and_current_marker_gate_reconciliation_review metadata_and_current_marker_gate_reconciliation_review_text current_marker_source_count current_marker_checked_count stale_current_marker_count historical_reference_allowed=True metadata_current_state_aligned=True release_history_current_entry_aligned=True smoke_expectation_current_aligned=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v911-release-gate-stale-assertion-truth-repair","version":"911.0","surface_origin_version":"911.0","manifest_representation_version":"911.0","last_verified_for_version":"911.0","era":"release-gate-stale-assertion-truth-repair","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--release-gate-stale-assertion-truth-repair","builder_function":"build_release_gate_stale_assertion_truth_repair_review","text_function":"release_gate_stale_assertion_truth_repair_review_text","runtime_directory":"none","smoke_check":"release-gate-stale-assertion-truth-repair-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])

# v911.0 release gate stale assertion truth repair source surface tokens: release-gate-stale-assertion-truth-repair-v1 /self-development-smoke-debt not_exposed_review_only --release-gate-stale-assertion-truth-repair build_release_gate_stale_assertion_truth_repair_review release_gate_stale_assertion_truth_repair_review_text executable_smoke_assertion_audit executable_smoke_assertion_finding_count EXPECTED_CURRENT_VERSION token_presence_not_enough=True metadata_docs_audit_dynamic_current=True probe_containment_limits_honest=True network_access_not_measured=True external_filesystem_writes_not_measured=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v912-install-release-segment-blocker-classification","version":"912.0","surface_origin_version":"912.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"install-release-segment-blocker-classification","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--install-release-segment-blocker-classification","builder_function":"build_install_release_segment_blocker_classification_review","text_function":"install_release_segment_blocker_classification_review_text","runtime_directory":"none","smoke_check":"install-release-segment-blocker-classification-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},

    {"surface_id":"v913-release-archive-and-recovery-gate-boundedness-repair","version":"913.0","surface_origin_version":"913.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"release-archive-recovery-boundedness","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--release-archive-and-recovery-gate-boundedness-repair","builder_function":"build_release_archive_and_recovery_gate_boundedness_repair_review","text_function":"release_archive_and_recovery_gate_boundedness_repair_review_text","runtime_directory":"none","smoke_check":"release-archive-and-recovery-gate-boundedness-repair-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v914-install-release-segment-evidence-summary-gate","version":"914.0","surface_origin_version":"914.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"install-release-evidence-summary","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--install-release-segment-evidence-summary-gate","builder_function":"build_install_release_segment_evidence_summary_gate_review","text_function":"install_release_segment_evidence_summary_gate_review_text","runtime_directory":"none","smoke_check":"install-release-segment-evidence-summary-gate-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v915-manifest-driven-surface-generation-prep","version":"915.0","surface_origin_version":"915.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-driven-surface-generation-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-driven-surface-generation-prep","builder_function":"build_manifest_driven_surface_generation_prep_review","text_function":"manifest_driven_surface_generation_prep_review_text","runtime_directory":"none","smoke_check":"manifest-driven-surface-generation-prep-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
# v913.0-v915.0 source surface tokens: release-archive-and-recovery-gate-boundedness-repair-v1 install-release-segment-evidence-summary-gate-v1 manifest-driven-surface-generation-prep-v1 --release-archive-and-recovery-gate-boundedness-repair --install-release-segment-evidence-summary-gate --manifest-driven-surface-generation-prep build_release_archive_and_recovery_gate_boundedness_repair_review build_install_release_segment_evidence_summary_gate_review build_manifest_driven_surface_generation_prep_review release_archive_and_recovery_gate_boundedness_repair_review_text install_release_segment_evidence_summary_gate_review_text manifest_driven_surface_generation_prep_review_text generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
])


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v916-manifest-review-packet-schema","version":"916.0","surface_origin_version":"916.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-review-packet-schema","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--manifest-review-packet-schema","builder_function":"build_manifest_review_packet_schema_review","text_function":"manifest_review_packet_schema_review_text","runtime_directory":"none","smoke_check":"manifest-review-packet-schema-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v917-dashboard-surface-preview-generator","version":"917.0","surface_origin_version":"917.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"dashboard-surface-preview-generator","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--dashboard-surface-preview-generator","builder_function":"build_dashboard_surface_preview_generator_review","text_function":"dashboard_surface_preview_generator_review_text","runtime_directory":"none","smoke_check":"dashboard-surface-preview-generator-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v918-cli-api-surface-preview-generator","version":"918.0","surface_origin_version":"918.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"cli-api-surface-preview-generator","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--cli-api-surface-preview-generator","builder_function":"build_cli_api_surface_preview_generator_review","text_function":"cli_api_surface_preview_generator_review_text","runtime_directory":"none","smoke_check":"cli-api-surface-preview-generator-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v919-smoke-surface-preview-generator","version":"919.0","surface_origin_version":"919.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"smoke-surface-preview-generator","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--smoke-surface-preview-generator","builder_function":"build_smoke_surface_preview_generator_review","text_function":"smoke_surface_preview_generator_review_text","runtime_directory":"none","smoke_check":"smoke-surface-preview-generator-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v920-generated-preview-parity-report","version":"920.0","surface_origin_version":"920.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-preview-parity-report","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-preview-parity-report","builder_function":"build_generated_preview_parity_report_review","text_function":"generated_preview_parity_report_review_text","runtime_directory":"none","smoke_check":"generated-preview-parity-report-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])
# v916.0-v920.0 source surface tokens: manifest-review-packet-schema-v1 dashboard-surface-preview-generator-v1 cli-api-surface-preview-generator-v1 smoke-surface-preview-generator-v1 generated-preview-parity-report-v1 --manifest-review-packet-schema --dashboard-surface-preview-generator --cli-api-surface-preview-generator --smoke-surface-preview-generator --generated-preview-parity-report build_manifest_review_packet_schema_review build_dashboard_surface_preview_generator_review build_cli_api_surface_preview_generator_review build_smoke_surface_preview_generator_review build_generated_preview_parity_report_review manifest_review_packet_schema_review_text dashboard_surface_preview_generator_review_text cli_api_surface_preview_generator_review_text smoke_surface_preview_generator_review_text generated_preview_parity_report_review_text generated_preview_authoritative=False generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v921-low-risk-surface-selection-gate","version":"921.0","surface_origin_version":"921.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-generated-surface-parity-hardening","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--low-risk-surface-selection-gate","builder_function":"build_low_risk_surface_selection_gate_review","text_function":"low_risk_surface_selection_gate_review_text","runtime_directory":"none","smoke_check":"low-risk-surface-selection-gate-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v922-generated-dashboard-preview-exact-match-gate","version":"922.0","surface_origin_version":"922.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-generated-surface-parity-hardening","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-dashboard-preview-exact-match-gate","builder_function":"build_generated_dashboard_preview_exact_match_gate_review","text_function":"generated_dashboard_preview_exact_match_gate_review_text","runtime_directory":"none","smoke_check":"generated-dashboard-preview-exact-match-gate-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v923-generated-cli-api-preview-exact-match-gate","version":"923.0","surface_origin_version":"923.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-generated-surface-parity-hardening","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-cli-api-preview-exact-match-gate","builder_function":"build_generated_cli_api_preview_exact_match_gate_review","text_function":"generated_cli_api_preview_exact_match_gate_review_text","runtime_directory":"none","smoke_check":"generated-cli-api-preview-exact-match-gate-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v924-generated-smoke-preview-exact-match-gate","version":"924.0","surface_origin_version":"924.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-generated-surface-parity-hardening","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-smoke-preview-exact-match-gate","builder_function":"build_generated_smoke_preview_exact_match_gate_review","text_function":"generated_smoke_preview_exact_match_gate_review_text","runtime_directory":"none","smoke_check":"generated-smoke-preview-exact-match-gate-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v926-multi-surface-selection-gate","version":"926.0","surface_origin_version":"926.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"multi-surface-generated-parity-batch","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--multi-surface-selection-gate","builder_function":"build_multi_surface_selection_gate_review","text_function":"multi_surface_selection_gate_review_text","runtime_directory":"none","smoke_check":"multi-surface-selection-gate-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v927-multi-surface-dashboard-preview-parity","version":"927.0","surface_origin_version":"927.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"multi-surface-generated-parity-batch","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--multi-surface-dashboard-preview-parity","builder_function":"build_multi_surface_dashboard_preview_parity_review","text_function":"multi_surface_dashboard_preview_parity_review_text","runtime_directory":"none","smoke_check":"multi-surface-dashboard-preview-parity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v928-multi-surface-cli-api-preview-parity","version":"928.0","surface_origin_version":"928.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"multi-surface-generated-parity-batch","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--multi-surface-cli-api-preview-parity","builder_function":"build_multi_surface_cli_api_preview_parity_review","text_function":"multi_surface_cli_api_preview_parity_review_text","runtime_directory":"none","smoke_check":"multi-surface-cli-api-preview-parity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v929-multi-surface-smoke-preview-parity","version":"929.0","surface_origin_version":"929.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"multi-surface-generated-parity-batch","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--multi-surface-smoke-preview-parity","builder_function":"build_multi_surface_smoke_preview_parity_review","text_function":"multi_surface_smoke_preview_parity_review_text","runtime_directory":"none","smoke_check":"multi-surface-smoke-preview-parity-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v930-multi-surface-generated-parity-batch-closure","version":"930.0","surface_origin_version":"930.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"multi-surface-generated-parity-batch","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--multi-surface-generated-parity-batch-closure","builder_function":"build_multi_surface_generated_parity_batch_closure_review","text_function":"multi_surface_generated_parity_batch_closure_review_text","runtime_directory":"none","smoke_check":"multi-surface-generated-parity-batch-closure-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v925-single-surface-generated-parity-closure","version":"925.0","surface_origin_version":"925.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"manifest-generated-surface-parity-hardening","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--single-surface-generated-parity-closure","builder_function":"build_single_surface_generated_parity_closure_review","text_function":"single_surface_generated_parity_closure_review_text","runtime_directory":"none","smoke_check":"single-surface-generated-parity-closure-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v931-generated-scaffold-sandbox-output-schema","version":"931.0","surface_origin_version":"931.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-sandbox-output-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-sandbox-output-schema","builder_function":"build_generated_scaffold_sandbox_output_schema_review","text_function":"generated_scaffold_sandbox_output_schema_review_text","runtime_directory":"sandbox/generated_surface_scaffold_previews/","smoke_check":"generated-scaffold-sandbox-output-schema-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v932-generated-scaffold-sandbox-artifact-preview","version":"932.0","surface_origin_version":"932.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-sandbox-output-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-sandbox-artifact-preview","builder_function":"build_generated_scaffold_sandbox_artifact_preview_review","text_function":"generated_scaffold_sandbox_artifact_preview_review_text","runtime_directory":"sandbox/generated_surface_scaffold_previews/","smoke_check":"generated-scaffold-sandbox-artifact-preview-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v933-generated-scaffold-hash-ledger","version":"933.0","surface_origin_version":"933.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-sandbox-output-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-hash-ledger","builder_function":"build_generated_scaffold_hash_ledger_review","text_function":"generated_scaffold_hash_ledger_review_text","runtime_directory":"sandbox/generated_surface_scaffold_previews/","smoke_check":"generated-scaffold-hash-ledger-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v934-generated-scaffold-sandbox-parity-comparison","version":"934.0","surface_origin_version":"934.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-sandbox-output-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-sandbox-parity-comparison","builder_function":"build_generated_scaffold_sandbox_parity_comparison_review","text_function":"generated_scaffold_sandbox_parity_comparison_review_text","runtime_directory":"sandbox/generated_surface_scaffold_previews/","smoke_check":"generated-scaffold-sandbox-parity-comparison-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v935-generated-scaffold-sandbox-output-closure","version":"935.0","surface_origin_version":"935.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-sandbox-output-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-sandbox-output-closure","builder_function":"build_generated_scaffold_sandbox_output_closure_review","text_function":"generated_scaffold_sandbox_output_closure_review_text","runtime_directory":"sandbox/generated_surface_scaffold_previews/","smoke_check":"generated-scaffold-sandbox-output-closure-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])
# v931.0-v935.0 source surface tokens: generated-scaffold-sandbox-output-schema-v1 generated-scaffold-sandbox-artifact-preview-v1 generated-scaffold-hash-ledger-v1 generated-scaffold-sandbox-parity-comparison-v1 generated-scaffold-sandbox-output-closure-v1 --generated-scaffold-sandbox-output-schema --generated-scaffold-sandbox-artifact-preview --generated-scaffold-hash-ledger --generated-scaffold-sandbox-parity-comparison --generated-scaffold-sandbox-output-closure build_generated_scaffold_sandbox_output_schema_review build_generated_scaffold_sandbox_artifact_preview_review build_generated_scaffold_hash_ledger_review build_generated_scaffold_sandbox_parity_comparison_review build_generated_scaffold_sandbox_output_closure_review generated_scaffold_sandbox_output_schema_review_text generated_scaffold_sandbox_artifact_preview_review_text generated_scaffold_hash_ledger_review_text generated_scaffold_sandbox_parity_comparison_review_text generated_scaffold_sandbox_output_closure_review_text sandbox_artifact_count=5 hash_count=5 comparison_count=5 runtime_writes_sandbox_files=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v926.0-v930.0 source surface tokens: multi-surface-selection-gate-v1 multi-surface-dashboard-preview-parity-v1 multi-surface-cli-api-preview-parity-v1 multi-surface-smoke-preview-parity-v1 multi-surface-generated-parity-batch-closure-v1 --multi-surface-selection-gate --multi-surface-dashboard-preview-parity --multi-surface-cli-api-preview-parity --multi-surface-smoke-preview-parity --multi-surface-generated-parity-batch-closure build_multi_surface_selection_gate_review build_multi_surface_dashboard_preview_parity_review build_multi_surface_cli_api_preview_parity_review build_multi_surface_smoke_preview_parity_review build_multi_surface_generated_parity_batch_closure_review multi_surface_selection_gate_review_text multi_surface_dashboard_preview_parity_review_text multi_surface_cli_api_preview_parity_review_text multi_surface_smoke_preview_parity_review_text multi_surface_generated_parity_batch_closure_review_text selected_surface_count=5 dashboard_parity=exact_for_all_selected cli_parity=exact_for_all_selected api_parity=exact_not_exposed_review_only_for_all_selected smoke_parity=exact_for_all_selected stale_marker_parity=exact_current_version_source_for_all_selected generated_preview_authoritative=False generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v921.0-v925.0 source surface tokens: low-risk-surface-selection-gate-v1 generated-dashboard-preview-exact-match-gate-v1 generated-cli-api-preview-exact-match-gate-v1 generated-smoke-preview-exact-match-gate-v1 single-surface-generated-parity-closure-v1 --low-risk-surface-selection-gate --generated-dashboard-preview-exact-match-gate --generated-cli-api-preview-exact-match-gate --generated-smoke-preview-exact-match-gate --single-surface-generated-parity-closure build_low_risk_surface_selection_gate_review build_generated_dashboard_preview_exact_match_gate_review build_generated_cli_api_preview_exact_match_gate_review build_generated_smoke_preview_exact_match_gate_review build_single_surface_generated_parity_closure_review low_risk_surface_selection_gate_review_text generated_dashboard_preview_exact_match_gate_review_text generated_cli_api_preview_exact_match_gate_review_text generated_smoke_preview_exact_match_gate_review_text single_surface_generated_parity_closure_review_text selected_surface_id=v916-manifest-review-packet-schema dashboard_parity=exact cli_parity=exact api_parity=exact_not_exposed_review_only smoke_parity=exact generated_preview_authoritative=False generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v912.0 install-release segment blocker classification source surface tokens: install-release-segment-blocker-classification-v1 /self-development-smoke-debt not_exposed_review_only --install-release-segment-blocker-classification build_install_release_segment_blocker_classification_review install_release_segment_blocker_classification_review_text currently_passing valid_historical_blocked_state slow_or_hanging_check superseded_check marks_install_release_clean=False executes_full_install_release_segment=False release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v936-generated-scaffold-wrapper-mapping-schema","version":"936.0","surface_origin_version":"936.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-wrapper-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-wrapper-mapping-schema","builder_function":"build_generated_scaffold_wrapper_mapping_schema_review","text_function":"generated_scaffold_wrapper_mapping_schema_review_text","runtime_directory":"sandbox/generated_scaffold_wrapper_previews/","smoke_check":"generated-scaffold-wrapper-mapping-schema-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v937-dashboard-compatibility-wrapper-preview","version":"937.0","surface_origin_version":"937.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-wrapper-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--dashboard-compatibility-wrapper-preview","builder_function":"build_dashboard_compatibility_wrapper_preview_review","text_function":"dashboard_compatibility_wrapper_preview_review_text","runtime_directory":"sandbox/generated_scaffold_wrapper_previews/","smoke_check":"dashboard-compatibility-wrapper-preview-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v938-cli-api-compatibility-wrapper-preview","version":"938.0","surface_origin_version":"938.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-wrapper-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--cli-api-compatibility-wrapper-preview","builder_function":"build_cli_api_compatibility_wrapper_preview_review","text_function":"cli_api_compatibility_wrapper_preview_review_text","runtime_directory":"sandbox/generated_scaffold_wrapper_previews/","smoke_check":"cli-api-compatibility-wrapper-preview-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v939-smoke-compatibility-wrapper-preview","version":"939.0","surface_origin_version":"939.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-wrapper-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--smoke-compatibility-wrapper-preview","builder_function":"build_smoke_compatibility_wrapper_preview_review","text_function":"smoke_compatibility_wrapper_preview_review_text","runtime_directory":"sandbox/generated_scaffold_wrapper_previews/","smoke_check":"smoke-compatibility-wrapper-preview-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v940-generated-scaffold-wrapper-prep-closure","version":"940.0","surface_origin_version":"940.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"generated-scaffold-wrapper-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--generated-scaffold-wrapper-prep-closure","builder_function":"build_generated_scaffold_wrapper_prep_closure_review","text_function":"generated_scaffold_wrapper_prep_closure_review_text","runtime_directory":"sandbox/generated_scaffold_wrapper_previews/","smoke_check":"generated-scaffold-wrapper-prep-closure-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])
# v936.0-v940.0 source surface tokens: generated-scaffold-wrapper-mapping-schema-v1 dashboard-compatibility-wrapper-preview-v1 cli-api-compatibility-wrapper-preview-v1 smoke-compatibility-wrapper-preview-v1 generated-scaffold-wrapper-prep-closure-v1 --generated-scaffold-wrapper-mapping-schema --dashboard-compatibility-wrapper-preview --cli-api-compatibility-wrapper-preview --smoke-compatibility-wrapper-preview --generated-scaffold-wrapper-prep-closure build_generated_scaffold_wrapper_mapping_schema_review build_dashboard_compatibility_wrapper_preview_review build_cli_api_compatibility_wrapper_preview_review build_smoke_compatibility_wrapper_preview_review build_generated_scaffold_wrapper_prep_closure_review generated_scaffold_wrapper_mapping_schema_review_text dashboard_compatibility_wrapper_preview_review_text cli_api_compatibility_wrapper_preview_review_text smoke_compatibility_wrapper_preview_review_text generated_scaffold_wrapper_prep_closure_review_text wrapper_artifact_count=5 wrapper_hash_count=5 wrapper_schema_field_count=16 runtime_writes_wrapper_files=False manual_code_replaced=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {"surface_id":"v941-giant-file-extraction-inventory","version":"941.0","surface_origin_version":"941.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--giant-file-extraction-inventory","builder_function":"build_giant_file_extraction_inventory_review","text_function":"giant_file_extraction_inventory_review_text","runtime_directory":"none","smoke_check":"giant-file-extraction-inventory-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v942-self-development-cycle-extraction-map","version":"942.0","surface_origin_version":"942.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--self-development-cycle-extraction-map","builder_function":"build_self_development_cycle_extraction_map_review","text_function":"self_development_cycle_extraction_map_review_text","runtime_directory":"none","smoke_check":"self-development-cycle-extraction-map-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v943-self-maintenance-builder-text-renderer-extraction-map","version":"943.0","surface_origin_version":"943.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--self-maintenance-builder-text-renderer-extraction-map","builder_function":"build_self_maintenance_builder_text_renderer_extraction_map_review","text_function":"self_maintenance_builder_text_renderer_extraction_map_review_text","runtime_directory":"none","smoke_check":"self-maintenance-builder-text-renderer-extraction-map-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v944-dashboard-route-renderer-extraction-map","version":"944.0","surface_origin_version":"944.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--dashboard-route-renderer-extraction-map","builder_function":"build_dashboard_route_renderer_extraction_map_review","text_function":"dashboard_route_renderer_extraction_map_review_text","runtime_directory":"none","smoke_check":"dashboard-route-renderer-extraction-map-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v945-cli-api-dispatch-extraction-map","version":"945.0","surface_origin_version":"945.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--cli-api-dispatch-extraction-map","builder_function":"build_cli_api_dispatch_extraction_map_review","text_function":"cli_api_dispatch_extraction_map_review_text","runtime_directory":"none","smoke_check":"cli-api-dispatch-extraction-map-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v946-smoke-registry-extraction-map","version":"946.0","surface_origin_version":"946.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--smoke-registry-extraction-map","builder_function":"build_smoke_registry_extraction_map_review","text_function":"smoke_registry_extraction_map_review_text","runtime_directory":"none","smoke_check":"smoke-registry-extraction-map-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v947-compatibility-wrapper-risk-ledger","version":"947.0","surface_origin_version":"947.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--compatibility-wrapper-risk-ledger","builder_function":"build_compatibility_wrapper_risk_ledger_review","text_function":"compatibility_wrapper_risk_ledger_review_text","runtime_directory":"none","smoke_check":"compatibility-wrapper-risk-ledger-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v948-extraction-order-proposal","version":"948.0","surface_origin_version":"948.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--extraction-order-proposal","builder_function":"build_extraction_order_proposal_review","text_function":"extraction_order_proposal_review_text","runtime_directory":"none","smoke_check":"extraction-order-proposal-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v949-extraction-rollback-evidence-plan","version":"949.0","surface_origin_version":"949.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--extraction-rollback-evidence-plan","builder_function":"build_extraction_rollback_evidence_plan_review","text_function":"extraction_rollback_evidence_plan_review_text","runtime_directory":"none","smoke_check":"extraction-rollback-evidence-plan-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
    {"surface_id":"v950-giant-file-compatibility-extraction-prep-closure","version":"950.0","surface_origin_version":"950.0","manifest_representation_version":"970.0","last_verified_for_version":"970.0","era":"giant-file-compatibility-extraction-prep","dashboard_route":"/self-development-smoke-debt","api_route":"not_exposed_review_only","cli_flag":"--giant-file-compatibility-extraction-prep-closure","builder_function":"build_giant_file_compatibility_extraction_prep_closure_review","text_function":"giant_file_compatibility_extraction_prep_closure_review_text","runtime_directory":"none","smoke_check":"giant-file-compatibility-extraction-prep-closure-v1","smoke_segment":"install-release","authority_level":"review_only","writes_files":False,"writes_memory":False,"requires_operator_approval":True,"single_use_approval_required":True,"approval_burnout_required":True,"package_privacy_sensitive":False,"status":"represented"},
])
# v941.0-v950.0 source surface tokens: giant-file-extraction-inventory-v1 self-development-cycle-extraction-map-v1 self-maintenance-builder-text-renderer-extraction-map-v1 dashboard-route-renderer-extraction-map-v1 cli-api-dispatch-extraction-map-v1 smoke-registry-extraction-map-v1 compatibility-wrapper-risk-ledger-v1 extraction-order-proposal-v1 extraction-rollback-evidence-plan-v1 giant-file-compatibility-extraction-prep-closure-v1 --giant-file-extraction-inventory --self-development-cycle-extraction-map --self-maintenance-builder-text-renderer-extraction-map --dashboard-route-renderer-extraction-map --cli-api-dispatch-extraction-map --smoke-registry-extraction-map --compatibility-wrapper-risk-ledger --extraction-order-proposal --extraction-rollback-evidence-plan --giant-file-compatibility-extraction-prep-closure build_giant_file_extraction_inventory_review build_self_development_cycle_extraction_map_review build_self_maintenance_builder_text_renderer_extraction_map_review build_dashboard_route_renderer_extraction_map_review build_cli_api_dispatch_extraction_map_review build_smoke_registry_extraction_map_review build_compatibility_wrapper_risk_ledger_review build_extraction_order_proposal_review build_extraction_rollback_evidence_plan_review build_giant_file_compatibility_extraction_prep_closure_review giant_file_extraction_inventory_review_text self_development_cycle_extraction_map_review_text self_maintenance_builder_text_renderer_extraction_map_review_text dashboard_route_renderer_extraction_map_review_text cli_api_dispatch_extraction_map_review_text smoke_registry_extraction_map_review_text compatibility_wrapper_risk_ledger_review_text extraction_order_proposal_review_text extraction_rollback_evidence_plan_review_text giant_file_compatibility_extraction_prep_closure_review_text candidate_count low_risk_extraction_count protected_manual_count recommended_first_extraction_module rollback_plan_status moves_live_code=False splits_files=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v951.0-v960.0 source surface tokens: extraction-candidate-lock-gate-v1 pre-extraction-function-inventory-v1 generated-preview-review-module-extraction-v1 compatibility-import-wrapper-gate-v1 dashboard-cli-api-parity-after-extraction-v1 smoke-registry-parity-after-extraction-v1 stale-version-and-metadata-post-extraction-gate-v1 rollback-path-verification-v1 extraction-release-evidence-packet-v1 first-compatibility-extraction-closure-v1 --extraction-candidate-lock-gate --pre-extraction-function-inventory --generated-preview-review-module-extraction --compatibility-import-wrapper-gate --dashboard-cli-api-parity-after-extraction --smoke-registry-parity-after-extraction --stale-version-and-metadata-post-extraction-gate --rollback-path-verification --extraction-release-evidence-packet --first-compatibility-extraction-closure build_extraction_candidate_lock_gate_review build_pre_extraction_function_inventory_review build_generated_preview_review_module_extraction_review build_compatibility_import_wrapper_gate_review build_dashboard_cli_api_parity_after_extraction_review build_smoke_registry_parity_after_extraction_review build_stale_version_and_metadata_post_extraction_gate_review build_rollback_path_verification_review build_extraction_release_evidence_packet_review build_first_compatibility_extraction_closure_review extraction_candidate_lock_gate_review_text pre_extraction_function_inventory_review_text generated_preview_review_module_extraction_review_text compatibility_import_wrapper_gate_review_text dashboard_cli_api_parity_after_extraction_review_text smoke_registry_parity_after_extraction_review_text stale_version_and_metadata_post_extraction_gate_review_text rollback_path_verification_review_text extraction_release_evidence_packet_review_text first_compatibility_extraction_closure_review_text extracted_module=conscious_agent/generated_surface_preview_reviews.py wrappers_preserved=True dashboard_parity=pass cli_api_parity=pass smoke_parity=pass rollback_path=documented generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend(
[
    {
        "surface_id": "v961-second-extraction-candidate-selection-gate",
        "version": "961.0",
        "surface_origin_version": "961.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--second-extraction-candidate-selection-gate",
        "builder_function": "build_second_extraction_candidate_selection_gate_review",
        "text_function": "second_extraction_candidate_selection_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "second-extraction-candidate-selection-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v962-second-pre-extraction-function-inventory",
        "version": "962.0",
        "surface_origin_version": "962.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--second-pre-extraction-function-inventory",
        "builder_function": "build_second_pre_extraction_function_inventory_review",
        "text_function": "second_pre_extraction_function_inventory_review_text",
        "runtime_directory": "none",
        "smoke_check": "second-pre-extraction-function-inventory-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v963-generated-scaffold-review-packet-extraction",
        "version": "963.0",
        "surface_origin_version": "963.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--generated-scaffold-review-packet-extraction",
        "builder_function": "build_generated_scaffold_review_packet_extraction_review",
        "text_function": "generated_scaffold_review_packet_extraction_review_text",
        "runtime_directory": "none",
        "smoke_check": "generated-scaffold-review-packet-extraction-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v964-second-compatibility-wrapper-gate",
        "version": "964.0",
        "surface_origin_version": "964.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--second-compatibility-wrapper-gate",
        "builder_function": "build_second_compatibility_wrapper_gate_review",
        "text_function": "second_compatibility_wrapper_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "second-compatibility-wrapper-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v965-second-extraction-surface-parity-gate",
        "version": "965.0",
        "surface_origin_version": "965.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--second-extraction-surface-parity-gate",
        "builder_function": "build_second_extraction_surface_parity_gate_review",
        "text_function": "second_extraction_surface_parity_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "second-extraction-surface-parity-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v966-smoke-registry-data-model-prep",
        "version": "966.0",
        "surface_origin_version": "966.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-data-model-prep",
        "builder_function": "build_smoke_registry_data_model_prep_review",
        "text_function": "smoke_registry_data_model_prep_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-data-model-prep-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v967-smoke-registry-static-inventory",
        "version": "967.0",
        "surface_origin_version": "967.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-static-inventory",
        "builder_function": "build_smoke_registry_static_inventory_review",
        "text_function": "smoke_registry_static_inventory_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-static-inventory-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v968-smoke-registry-migration-risk-ledger",
        "version": "968.0",
        "surface_origin_version": "968.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-migration-risk-ledger",
        "builder_function": "build_smoke_registry_migration_risk_ledger_review",
        "text_function": "smoke_registry_migration_risk_ledger_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-migration-risk-ledger-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v969-smoke-registry-rollback-plan",
        "version": "969.0",
        "surface_origin_version": "969.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-rollback-plan",
        "builder_function": "build_smoke_registry_rollback_plan_review",
        "text_function": "smoke_registry_rollback_plan_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-rollback-plan-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v970-second-extraction-and-smoke-registry-prep-closure",
        "version": "970.0",
        "surface_origin_version": "970.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "second-compatibility-extraction-and-smoke-registry-prep",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--second-extraction-and-smoke-registry-prep-closure",
        "builder_function": "build_second_extraction_and_smoke_registry_prep_closure_review",
        "text_function": "second_extraction_and_smoke_registry_prep_closure_review_text",
        "runtime_directory": "none",
        "smoke_check": "second-extraction-and-smoke-registry-prep-closure-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }
]
)

# v961.0-v970.0 source surface tokens: second-extraction-candidate-selection-gate-v1 second-pre-extraction-function-inventory-v1 generated-scaffold-review-packet-extraction-v1 second-compatibility-wrapper-gate-v1 second-extraction-surface-parity-gate-v1 smoke-registry-data-model-prep-v1 smoke-registry-static-inventory-v1 smoke-registry-migration-risk-ledger-v1 smoke-registry-rollback-plan-v1 second-extraction-and-smoke-registry-prep-closure-v1 --second-extraction-candidate-selection-gate --second-pre-extraction-function-inventory --generated-scaffold-review-packet-extraction --second-compatibility-wrapper-gate --second-extraction-surface-parity-gate --smoke-registry-data-model-prep --smoke-registry-static-inventory --smoke-registry-migration-risk-ledger --smoke-registry-rollback-plan --second-extraction-and-smoke-registry-prep-closure build_second_extraction_candidate_selection_gate_review build_second_pre_extraction_function_inventory_review build_generated_scaffold_review_packet_extraction_review build_second_compatibility_wrapper_gate_review build_second_extraction_surface_parity_gate_review build_smoke_registry_data_model_prep_review build_smoke_registry_static_inventory_review build_smoke_registry_migration_risk_ledger_review build_smoke_registry_rollback_plan_review build_second_extraction_and_smoke_registry_prep_closure_review second_extraction_candidate_selection_gate_review_text second_pre_extraction_function_inventory_review_text generated_scaffold_review_packet_extraction_review_text second_compatibility_wrapper_gate_review_text second_extraction_surface_parity_gate_review_text smoke_registry_data_model_prep_review_text smoke_registry_static_inventory_review_text smoke_registry_migration_risk_ledger_review_text smoke_registry_rollback_plan_review_text second_extraction_and_smoke_registry_prep_closure_review_text second_extracted_module=conscious_agent/generated_scaffold_review_packets.py extracted_cluster=v931-v935 wrappers_preserved=True dashboard_parity=pass cli_api_parity=pass smoke_parity=pass smoke_registry_model=prepared_only smoke_registry_behavior_changed=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v971-smoke-registry-pilot-selection-gate",
        "version": "971.0",
        "surface_origin_version": "971.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-pilot-selection-gate",
        "builder_function": "build_smoke_registry_pilot_selection_gate_review",
        "text_function": "smoke_registry_pilot_selection_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-pilot-selection-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v972-smoke-registry-pilot-schema",
        "version": "972.0",
        "surface_origin_version": "972.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-pilot-schema",
        "builder_function": "build_smoke_registry_pilot_schema_review",
        "text_function": "smoke_registry_pilot_schema_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-pilot-schema-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v973-smoke-registry-pilot-data-table",
        "version": "973.0",
        "surface_origin_version": "973.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-pilot-data-table",
        "builder_function": "build_smoke_registry_pilot_data_table_review",
        "text_function": "smoke_registry_pilot_data_table_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-pilot-data-table-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v974-smoke-registry-pilot-resolver",
        "version": "974.0",
        "surface_origin_version": "974.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-pilot-resolver",
        "builder_function": "build_smoke_registry_pilot_resolver_review",
        "text_function": "smoke_registry_pilot_resolver_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-pilot-resolver-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v975-manual-vs-pilot-smoke-parity-gate",
        "version": "975.0",
        "surface_origin_version": "975.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--manual-vs-pilot-smoke-parity-gate",
        "builder_function": "build_manual_vs_pilot_smoke_parity_gate_review",
        "text_function": "manual_vs_pilot_smoke_parity_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "manual-vs-pilot-smoke-parity-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v976-pilot-json-shape-compatibility-gate",
        "version": "976.0",
        "surface_origin_version": "976.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-json-shape-compatibility-gate",
        "builder_function": "build_pilot_json_shape_compatibility_gate_review",
        "text_function": "pilot_json_shape_compatibility_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-json-shape-compatibility-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v977-pilot-rollback-evidence-gate",
        "version": "977.0",
        "surface_origin_version": "977.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-rollback-evidence-gate",
        "builder_function": "build_pilot_rollback_evidence_gate_review",
        "text_function": "pilot_rollback_evidence_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-rollback-evidence-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v978-smoke-registry-pilot-risk-review",
        "version": "978.0",
        "surface_origin_version": "978.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-pilot-risk-review",
        "builder_function": "build_smoke_registry_pilot_risk_review",
        "text_function": "smoke_registry_pilot_risk_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-pilot-risk-review-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v979-pilot-expansion-readiness-review",
        "version": "979.0",
        "surface_origin_version": "979.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-expansion-readiness-review",
        "builder_function": "build_pilot_expansion_readiness_review",
        "text_function": "pilot_expansion_readiness_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-expansion-readiness-review-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v980-smoke-registry-data-driven-pilot-closure",
        "version": "980.0",
        "surface_origin_version": "980.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-data-driven-pilot-closure",
        "builder_function": "build_smoke_registry_data_driven_pilot_closure_review",
        "text_function": "smoke_registry_data_driven_pilot_closure_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-data-driven-pilot-closure-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v981-smoke-registry-execution-trial-readiness-gate",
        "version": "981.0",
        "surface_origin_version": "981.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-execution-trial-readiness-gate",
        "builder_function": "build_smoke_registry_execution_trial_readiness_gate_review",
        "text_function": "smoke_registry_execution_trial_readiness_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-execution-trial-readiness-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v982-data-driven-smoke-callable-execution-harness",
        "version": "982.0",
        "surface_origin_version": "982.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-smoke-callable-execution-harness",
        "builder_function": "build_data_driven_smoke_callable_execution_harness_review",
        "text_function": "data_driven_smoke_callable_execution_harness_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-smoke-callable-execution-harness-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v983-pilot-smoke-execution-result-packet",
        "version": "983.0",
        "surface_origin_version": "983.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-smoke-execution-result-packet",
        "builder_function": "build_pilot_smoke_execution_result_packet_review",
        "text_function": "pilot_smoke_execution_result_packet_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-smoke-execution-result-packet-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v984-manual-vs-data-driven-execution-parity-gate",
        "version": "984.0",
        "surface_origin_version": "984.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--manual-vs-data-driven-execution-parity-gate",
        "builder_function": "build_manual_vs_data_driven_execution_parity_gate_review",
        "text_function": "manual_vs_data_driven_execution_parity_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "manual-vs-data-driven-execution-parity-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v985-data-driven-smoke-json-output-preview",
        "version": "985.0",
        "surface_origin_version": "985.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-smoke-json-output-preview",
        "builder_function": "build_data_driven_smoke_json_output_preview_review",
        "text_function": "data_driven_smoke_json_output_preview_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-smoke-json-output-preview-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v986-data-driven-smoke-timeout-failure-semantics",
        "version": "986.0",
        "surface_origin_version": "986.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-smoke-timeout-failure-semantics",
        "builder_function": "build_data_driven_smoke_timeout_failure_semantics_review",
        "text_function": "data_driven_smoke_timeout_failure_semantics_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-smoke-timeout-failure-semantics-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v987-data-driven-smoke-manual-fallback-proof",
        "version": "987.0",
        "surface_origin_version": "987.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-smoke-manual-fallback-proof",
        "builder_function": "build_data_driven_smoke_manual_fallback_proof_review",
        "text_function": "data_driven_smoke_manual_fallback_proof_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-smoke-manual-fallback-proof-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v988-data-driven-smoke-execution-risk-review",
        "version": "988.0",
        "surface_origin_version": "988.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-smoke-execution-risk-review",
        "builder_function": "build_data_driven_smoke_execution_risk_review",
        "text_function": "data_driven_smoke_execution_risk_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-smoke-execution-risk-review-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v989-data-driven-smoke-expansion-readiness",
        "version": "989.0",
        "surface_origin_version": "989.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-smoke-expansion-readiness",
        "builder_function": "build_data_driven_smoke_expansion_readiness_review",
        "text_function": "data_driven_smoke_expansion_readiness_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-smoke-expansion-readiness-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v990-smoke-registry-data-driven-execution-trial-closure",
        "version": "990.0",
        "surface_origin_version": "990.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-data-driven-execution-trial",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-data-driven-execution-trial-closure",
        "builder_function": "build_smoke_registry_data_driven_execution_trial_closure_review",
        "text_function": "smoke_registry_data_driven_execution_trial_closure_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-data-driven-execution-trial-closure-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },

    {
        "surface_id": "v991-fallback-migration-readiness-gate",
        "version": "991.0",
        "surface_origin_version": "991.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--fallback-migration-readiness-gate",
        "builder_function": "build_fallback_migration_readiness_gate_review",
        "text_function": "fallback_migration_readiness_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "fallback-migration-readiness-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v992-data-driven-first-pilot-dispatch-preview",
        "version": "992.0",
        "surface_origin_version": "992.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--data-driven-first-pilot-dispatch-preview",
        "builder_function": "build_data_driven_first_pilot_dispatch_preview_review",
        "text_function": "data_driven_first_pilot_dispatch_preview_review_text",
        "runtime_directory": "none",
        "smoke_check": "data-driven-first-pilot-dispatch-preview-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v993-pilot-fallback-dispatch-trial",
        "version": "993.0",
        "surface_origin_version": "993.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-fallback-dispatch-trial",
        "builder_function": "build_pilot_fallback_dispatch_trial_review",
        "text_function": "pilot_fallback_dispatch_trial_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-fallback-dispatch-trial-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v994-pilot-fallback-result-ledger",
        "version": "994.0",
        "surface_origin_version": "994.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-fallback-result-ledger",
        "builder_function": "build_pilot_fallback_result_ledger_review",
        "text_function": "pilot_fallback_result_ledger_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-fallback-result-ledger-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v995-json-output-stability-gate",
        "version": "995.0",
        "surface_origin_version": "995.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--json-output-stability-gate",
        "builder_function": "build_json_output_stability_gate_review",
        "text_function": "json_output_stability_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "json-output-stability-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v996-fast-install-release-isolation-gate",
        "version": "996.0",
        "surface_origin_version": "996.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--fast-install-release-isolation-gate",
        "builder_function": "build_fast_install_release_isolation_gate_review",
        "text_function": "fast_install_release_isolation_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "fast-install-release-isolation-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v997-manual-fallback-removal-resistance-gate",
        "version": "997.0",
        "surface_origin_version": "997.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--manual-fallback-removal-resistance-gate",
        "builder_function": "build_manual_fallback_removal_resistance_gate_review",
        "text_function": "manual_fallback_removal_resistance_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "manual-fallback-removal-resistance-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v998-pilot-migration-risk-review",
        "version": "998.0",
        "surface_origin_version": "998.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--pilot-migration-risk-review",
        "builder_function": "build_pilot_migration_risk_review",
        "text_function": "pilot_migration_risk_review_text",
        "runtime_directory": "none",
        "smoke_check": "pilot-migration-risk-review-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v999-v1000-milestone-readiness-review",
        "version": "999.0",
        "surface_origin_version": "999.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--v1000-milestone-readiness-review",
        "builder_function": "build_v1000_milestone_readiness_review",
        "text_function": "v1000_milestone_readiness_review_text",
        "runtime_directory": "none",
        "smoke_check": "v1000-milestone-readiness-review-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v1000-smoke-registry-fallback-migration-pilot-closure",
        "version": "1000.0",
        "surface_origin_version": "1000.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-fallback-migration-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--smoke-registry-fallback-migration-pilot-closure",
        "builder_function": "build_smoke_registry_fallback_migration_pilot_closure_review",
        "text_function": "smoke_registry_fallback_migration_pilot_closure_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-fallback-migration-pilot-closure-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    },
    {
        "surface_id": "v1002-install-release-blocker-ledger-refresh",
        "version": "1002.0",
        "surface_origin_version": "1002.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-evidence-ledger",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-blocker-ledger-refresh",
        "builder_function": "build_install_release_blocker_ledger_refresh_review",
        "text_function": "install_release_blocker_ledger_refresh_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-blocker-ledger-refresh-v1",
        "smoke_segment": "install-release",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

    ,
    {
        "surface_id": "v1003-install-release-timeout-harness-repair",
        "version": "1003.0",
        "surface_origin_version": "1003.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-timeout-harness-repair",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-timeout-harness-repair",
        "builder_function": "build_install_release_timeout_harness_repair_review",
        "text_function": "install_release_timeout_harness_repair_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-timeout-harness-repair-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

    ,
    {
        "surface_id": "v1004-install-release-timeout-row-bounded-retest",
        "version": "1004.0",
        "surface_origin_version": "1004.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-timeout-row-bounded-retest",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-timeout-row-bounded-retest",
        "builder_function": "build_install_release_timeout_row_bounded_retest_review",
        "text_function": "install_release_timeout_row_bounded_retest_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-timeout-row-bounded-retest-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

    ,
    {
        "surface_id": "v1005-install-release-fixture-decomposition-plan",
        "version": "1005.0",
        "surface_origin_version": "1005.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-fixture-decomposition-plan",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-fixture-decomposition-plan",
        "builder_function": "build_install_release_fixture_decomposition_plan_review",
        "text_function": "install_release_fixture_decomposition_plan_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-fixture-decomposition-plan-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

    ,
    {
        "surface_id": "v1006-install-release-fixture-smoke-split-pilot",
        "version": "1006.0",
        "surface_origin_version": "1006.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-fixture-smoke-split-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-fixture-smoke-split-pilot",
        "builder_function": "build_install_release_fixture_smoke_split_pilot_review",
        "text_function": "install_release_fixture_smoke_split_pilot_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-fixture-smoke-split-pilot-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }


    ,
    {
        "surface_id": "v1007-release-archive-fixture-split-expansion",
        "version": "1007.0",
        "surface_origin_version": "1007.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "release-archive-fixture-split-expansion",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--release-archive-fixture-split-expansion",
        "builder_function": "build_release_archive_fixture_split_expansion_review",
        "text_function": "release_archive_fixture_split_expansion_review_text",
        "runtime_directory": "none",
        "smoke_check": "release-archive-fixture-split-expansion-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }


    ,
    {
        "surface_id": "v1008-supervised-blocker-semantics-repair",
        "version": "1008.0",
        "surface_origin_version": "1008.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "supervised-blocker-semantics-repair",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--supervised-blocker-semantics-repair",
        "builder_function": "build_supervised_blocker_semantics_repair_review",
        "text_function": "supervised_blocker_semantics_repair_review_text",
        "runtime_directory": "none",
        "smoke_check": "supervised-blocker-semantics-repair-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

    ,
    {
        "surface_id": "v1009-install-release-segment-cleanliness-gate",
        "version": "1009.0",
        "surface_origin_version": "1009.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-segment-cleanliness-gate",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-segment-cleanliness-gate",
        "builder_function": "build_install_release_segment_cleanliness_gate_review",
        "text_function": "install_release_segment_cleanliness_gate_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-segment-cleanliness-gate-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

    ,
    {
        "surface_id": "v1010-post-v1000-defect-closure-phase-zero-boundary",
        "version": "1010.0",
        "surface_origin_version": "1010.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "post-v1000-defect-closure-phase-zero-boundary",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--post-v1000-defect-closure-audit-and-phase-zero-boundary",
        "builder_function": "build_post_v1000_defect_closure_phase_zero_boundary_review",
        "text_function": "post_v1000_defect_closure_phase_zero_boundary_review_text",
        "runtime_directory": "none",
        "smoke_check": "post-v1000-defect-closure-audit-and-phase-zero-boundary-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }

])

# v1010.0 source surface tokens: install-release-fixture-smoke-split-pilot-v1 --install-release-fixture-smoke-split-pilot build_install_release_fixture_smoke_split_pilot_review install_release_fixture_smoke_split_pilot_review_text fixture_family_selected=archive_continuity_index parent_timeout_row=release-archive-retrieval-and-continuity-index-v1 fixture_targets_in_family=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v991.0-v1000.0 source surface tokens: fallback-migration-readiness-gate-v1 data-driven-first-pilot-dispatch-preview-v1 pilot-fallback-dispatch-trial-v1 pilot-fallback-result-ledger-v1 json-output-stability-gate-v1 fast-install-release-isolation-gate-v1 manual-fallback-removal-resistance-gate-v1 pilot-migration-risk-review-v1 v1000-milestone-readiness-review-v1 smoke-registry-fallback-migration-pilot-closure-v1 --fallback-migration-readiness-gate --data-driven-first-pilot-dispatch-preview --pilot-fallback-dispatch-trial --pilot-fallback-result-ledger --json-output-stability-gate --fast-install-release-isolation-gate --manual-fallback-removal-resistance-gate --pilot-migration-risk-review --v1000-milestone-readiness-review --smoke-registry-fallback-migration-pilot-closure build_fallback_migration_readiness_gate_review build_data_driven_first_pilot_dispatch_preview_review build_pilot_fallback_dispatch_trial_review build_pilot_fallback_result_ledger_review build_json_output_stability_gate_review build_fast_install_release_isolation_gate_review build_manual_fallback_removal_resistance_gate_review build_pilot_migration_risk_review build_v1000_milestone_readiness_review build_smoke_registry_fallback_migration_pilot_closure_review fallback_migration_readiness_gate_review_text data_driven_first_pilot_dispatch_preview_review_text pilot_fallback_dispatch_trial_review_text pilot_fallback_result_ledger_review_text json_output_stability_gate_review_text fast_install_release_isolation_gate_review_text manual_fallback_removal_resistance_gate_review_text pilot_migration_risk_review_text v1000_milestone_readiness_review_text smoke_registry_fallback_migration_pilot_closure_review_text pilot_checks=5 data_driven_first_dispatch=active_for_pilot_trial_path_only manual_fallback=preserved registry_globally_replaced=False manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v971.0-v980.0 source surface tokens: smoke-registry-pilot-selection-gate-v1 smoke-registry-pilot-schema-v1 smoke-registry-pilot-data-table-v1 smoke-registry-pilot-resolver-v1 manual-vs-pilot-smoke-parity-gate-v1 pilot-json-shape-compatibility-gate-v1 pilot-rollback-evidence-gate-v1 smoke-registry-pilot-risk-review-v1 pilot-expansion-readiness-review-v1 smoke-registry-data-driven-pilot-closure-v1 --smoke-registry-pilot-selection-gate --smoke-registry-pilot-schema --smoke-registry-pilot-data-table --smoke-registry-pilot-resolver --manual-vs-pilot-smoke-parity-gate --pilot-json-shape-compatibility-gate --pilot-rollback-evidence-gate --smoke-registry-pilot-risk-review --pilot-expansion-readiness-review --smoke-registry-data-driven-pilot-closure build_smoke_registry_pilot_selection_gate_review build_smoke_registry_pilot_schema_review build_smoke_registry_pilot_data_table_review build_smoke_registry_pilot_resolver_review build_manual_vs_pilot_smoke_parity_gate_review build_pilot_json_shape_compatibility_gate_review build_pilot_rollback_evidence_gate_review build_smoke_registry_pilot_risk_review build_pilot_expansion_readiness_review build_smoke_registry_data_driven_pilot_closure_review smoke_registry_pilot_selection_gate_review_text smoke_registry_pilot_schema_review_text smoke_registry_pilot_data_table_review_text smoke_registry_pilot_resolver_review_text manual_vs_pilot_smoke_parity_gate_review_text pilot_json_shape_compatibility_gate_review_text pilot_rollback_evidence_gate_review_text smoke_registry_pilot_risk_review_text pilot_expansion_readiness_review_text smoke_registry_data_driven_pilot_closure_review_text pilot_checks=5 pilot_table_exists=True manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v981.0-v990.0 source surface tokens: smoke-registry-execution-trial-readiness-gate-v1 data-driven-smoke-callable-execution-harness-v1 pilot-smoke-execution-result-packet-v1 manual-vs-data-driven-execution-parity-gate-v1 data-driven-smoke-json-output-preview-v1 data-driven-smoke-timeout-failure-semantics-v1 data-driven-smoke-manual-fallback-proof-v1 data-driven-smoke-execution-risk-review-v1 data-driven-smoke-expansion-readiness-v1 smoke-registry-data-driven-execution-trial-closure-v1 --smoke-registry-execution-trial-readiness-gate --data-driven-smoke-callable-execution-harness --pilot-smoke-execution-result-packet --manual-vs-data-driven-execution-parity-gate --data-driven-smoke-json-output-preview --data-driven-smoke-timeout-failure-semantics --data-driven-smoke-manual-fallback-proof --data-driven-smoke-execution-risk-review --data-driven-smoke-expansion-readiness --smoke-registry-data-driven-execution-trial-closure build_smoke_registry_execution_trial_readiness_gate_review build_data_driven_smoke_callable_execution_harness_review build_pilot_smoke_execution_result_packet_review build_manual_vs_data_driven_execution_parity_gate_review build_data_driven_smoke_json_output_preview_review build_data_driven_smoke_timeout_failure_semantics_review build_data_driven_smoke_manual_fallback_proof_review build_data_driven_smoke_execution_risk_review build_data_driven_smoke_expansion_readiness_review build_smoke_registry_data_driven_execution_trial_closure_review smoke_registry_execution_trial_readiness_gate_review_text data_driven_smoke_callable_execution_harness_review_text pilot_smoke_execution_result_packet_review_text manual_vs_data_driven_execution_parity_gate_review_text data_driven_smoke_json_output_preview_review_text data_driven_smoke_timeout_failure_semantics_review_text data_driven_smoke_manual_fallback_proof_review_text data_driven_smoke_execution_risk_review_text data_driven_smoke_expansion_readiness_review_text smoke_registry_data_driven_execution_trial_closure_review_text pilot_checks_executed=5 data_driven_execution=pass manual_parity=exact_for_all_selected manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1002.0 source surface tokens: install-release-blocker-ledger-refresh-v1 --install-release-blocker-ledger-refresh build_install_release_blocker_ledger_refresh_review install_release_blocker_ledger_refresh_review_text install_release_passed_checks=17 install_release_blocked_checks=6 install_release_timeout_checks=7 full_install_release_clean=False timeout_harness_problem expected_supervised_blocker already_passing release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 source surface tokens: install-release-timeout-harness-repair-v1 --install-release-timeout-harness-repair build_install_release_timeout_harness_repair_review install_release_timeout_harness_repair_review_text timeout_rows_reviewed=7 timeout_rows_protected=7 timeout_harness_repaired=True timeout_protected_pending_retest full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 source surface tokens: install-release-timeout-row-bounded-retest-v1 --install-release-timeout-row-bounded-retest build_install_release_timeout_row_bounded_retest_review install_release_timeout_row_bounded_retest_review_text timeout_rows_total=7 timeout_rows_retested=7 timeout_rows_reclassified=7 still_timeout full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 source surface tokens: release-archive-fixture-split-expansion-v1 --release-archive-fixture-split-expansion build_release_archive_fixture_split_expansion_review release_archive_fixture_split_expansion_review_text expanded_fixture_families=archive_search_handoff,archive_export_closure expanded_family_count=2 split_fixture_targets_total=10 split_fixture_pass_count=10 parent_rows_still_timeout=True total_split_families_including_v1006=3 total_split_fixture_targets_including_v1006=15 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 source surface tokens: supervised-blocker-semantics-repair-v1 --supervised-blocker-semantics-repair build_supervised_blocker_semantics_repair_review supervised_blocker_semantics_repair_review_text supervised_blocker_rows_reviewed=6 supervised_blocker_semantics_repaired=6 operator_gated_rows=6 fixture_required_rows=1 release_authorizing_blockers_remaining=0 timeout_rows_remaining=7 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 source surface tokens: install-release-segment-cleanliness-gate-v1 --install-release-segment-cleanliness-gate build_install_release_segment_cleanliness_gate_review install_release_segment_cleanliness_gate_review_text install_release_total_checks=30 install_release_passing_rows=17 operator_gated_semantics_rows=6 timeout_rows_still_blocking=7 split_fixture_families_passing=3 split_fixture_targets_passing=15 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 source surface tokens: post-v1000-defect-closure-audit-and-phase-zero-boundary-v1 --post-v1000-defect-closure-audit-and-phase-zero-boundary build_post_v1000_defect_closure_phase_zero_boundary_review post_v1000_defect_closure_phase_zero_boundary_review_text original_v1000_findings_total=8 fixed_findings=5 repaired_and_monitored=1 partially_mitigated=2 timeout_rows_still_blocking=7 full_install_release_clean=False phase_zero_enabled=False observation_only_autonomy_enabled=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1011-install-release-timeout-parent-row-replacement-pilot",
        "version": "1011.0",
        "surface_origin_version": "1011.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-timeout-parent-row-replacement-pilot",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-timeout-parent-row-replacement-pilot",
        "builder_function": "build_install_release_timeout_parent_replacement_pilot_review",
        "text_function": "install_release_timeout_parent_replacement_pilot_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-timeout-parent-row-replacement-pilot-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented"
    }
])

# v1011.0 source surface tokens: install-release-timeout-parent-row-replacement-pilot-v1 --install-release-timeout-parent-row-replacement-pilot build_install_release_timeout_parent_replacement_pilot_review install_release_timeout_parent_replacement_pilot_review_text replacement_parent_row=release-archive-retrieval-and-continuity-index-v1 replacement_fixture_family=archive_continuity_index replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True timeout_rows_before_replacement=7 replaced_parent_rows=1 timeout_rows_remaining_after_replacement=6 active_cleanliness_blockers_after_replacement=6 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1012-install-release-parent-replacement-expansion",
        "version": "1012.0",
        "surface_origin_version": "1012.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "install-release-parent-replacement-expansion",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--install-release-parent-replacement-expansion",
        "builder_function": "build_install_release_parent_replacement_expansion_review",
        "text_function": "install_release_parent_replacement_expansion_review_text",
        "runtime_directory": "none",
        "smoke_check": "install-release-parent-replacement-expansion-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    }
])

# v1013.0 source surface tokens: install-release-parent-replacement-expansion-v1 --install-release-parent-replacement-expansion build_install_release_parent_replacement_expansion_review install_release_parent_replacement_expansion_review_text expansion_replacement_families=archive_search_handoff,archive_export_closure expansion_replaced_parent_rows=2 total_replaced_parent_rows_after_expansion=3 replacement_fixture_targets_after_expansion=15 parent_rows_original_timeout_preserved=True parent_rows_marked_pass=False timeout_rows_before_replacement=7 timeout_rows_remaining_after_expansion=4 active_cleanliness_blockers_after_expansion=4 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1013-remaining-timeout-parent-fixture-selection",
        "version": "1013.0",
        "surface_origin_version": "1013.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "remaining-timeout-parent-fixture-selection",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--remaining-timeout-parent-fixture-selection",
        "builder_function": "build_remaining_timeout_parent_fixture_selection_review",
        "text_function": "remaining_timeout_parent_fixture_selection_review_text",
        "runtime_directory": "none",
        "smoke_check": "remaining-timeout-parent-fixture-selection-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    }
])

# v1013.0 source surface tokens: remaining-timeout-parent-fixture-selection-v1 --remaining-timeout-parent-fixture-selection build_remaining_timeout_parent_fixture_selection_review remaining_timeout_parent_fixture_selection_review_text selected_parent_row=recovery-drill-and-release-closure-v1 selected_fixture_family=recovery_closure selected_fixture_targets=5 remaining_timeout_parent_rows_before_selection=4 selected_parent_original_timeout_preserved=True selected_parent_marked_pass=False projected_timeout_blockers_after_future_replacement=3 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1014-recovery-closure-fixture-split-smoke",
        "version": "1014.0",
        "surface_origin_version": "1014.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "recovery-closure-fixture-split-smoke",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--recovery-closure-fixture-split-smoke",
        "builder_function": "build_recovery_closure_fixture_split_smoke_review",
        "text_function": "recovery_closure_fixture_split_smoke_review_text",
        "runtime_directory": "none",
        "smoke_check": "recovery-closure-fixture-split-smoke-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    }
])

# v1014.0 source surface tokens: recovery-closure-fixture-split-smoke-v1 --recovery-closure-fixture-split-smoke build_recovery_closure_fixture_split_smoke_review recovery_closure_fixture_split_smoke_review_text fixture_family_selected=recovery_closure parent_timeout_row=recovery-drill-and-release-closure-v1 fixture_targets_in_family=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False projected_timeout_blockers_after_future_replacement=3 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1015-recovery-closure-parent-replacement-overlay",
        "version": "1015.0",
        "surface_origin_version": "1015.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "recovery-closure-parent-replacement-overlay",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--recovery-closure-parent-replacement-overlay",
        "builder_function": "build_recovery_closure_parent_replacement_overlay_review",
        "text_function": "recovery_closure_parent_replacement_overlay_review_text",
        "runtime_directory": "none",
        "smoke_check": "recovery-closure-parent-replacement-overlay-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    }
])

# v1015.0 source surface tokens: recovery-closure-parent-replacement-overlay-v1 --recovery-closure-parent-replacement-overlay build_recovery_closure_parent_replacement_overlay_review recovery_closure_parent_replacement_overlay_review_text replacement_parent_row=recovery-drill-and-release-closure-v1 replacement_fixture_family=recovery_closure replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=3 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=4 replacement_fixture_targets_after_overlay=20 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=3 active_cleanliness_blockers_after_overlay=3 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1016-remaining-timeout-parent-fixture-split-expansion",
        "version": "1016.0",
        "surface_origin_version": "1016.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "remaining-timeout-parent-fixture-split-expansion",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--remaining-timeout-parent-fixture-split-expansion",
        "builder_function": "build_remaining_timeout_parent_fixture_split_expansion_review",
        "text_function": "remaining_timeout_parent_fixture_split_expansion_review_text",
        "runtime_directory": "none",
        "smoke_check": "remaining-timeout-parent-fixture-split-expansion-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    }
])

# v1016.0 source surface tokens: remaining-timeout-parent-fixture-split-expansion-v1 --remaining-timeout-parent-fixture-split-expansion build_remaining_timeout_parent_fixture_split_expansion_review remaining_timeout_parent_fixture_split_expansion_review_text selected_parent_row=release-decision-and-archive-ledger-v1 selected_fixture_family=decision_archive_ledger selected_fixture_targets=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False already_replaced_parent_rows=4 remaining_timeout_parent_rows_before_split=3 projected_timeout_blockers_after_future_replacement=2 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1017-decision-archive-ledger-parent-replacement-overlay",
        "version": "1017.0",
        "surface_origin_version": "1017.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "decision-archive-ledger-parent-replacement-overlay",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--decision-archive-ledger-parent-replacement-overlay",
        "builder_function": "build_decision_archive_ledger_parent_replacement_overlay_review",
        "text_function": "decision_archive_ledger_parent_replacement_overlay_review_text",
        "runtime_directory": "none",
        "smoke_check": "decision-archive-ledger-parent-replacement-overlay-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    }
])

# v1017.0 source surface tokens: decision-archive-ledger-parent-replacement-overlay-v1 --decision-archive-ledger-parent-replacement-overlay build_decision_archive_ledger_parent_replacement_overlay_review decision_archive_ledger_parent_replacement_overlay_review_text replacement_parent_row=release-decision-and-archive-ledger-v1 replacement_fixture_family=decision_archive_ledger replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=4 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=5 replacement_fixture_targets_after_overlay=25 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=2 active_cleanliness_blockers_after_overlay=2 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

RECENT_SURFACE_ENTRIES.extend([
    {
        "surface_id": "v1018-candidate-handoff-fixture-split-smoke",
        "version": "1018.0",
        "surface_origin_version": "1018.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "candidate-handoff-fixture-split-smoke",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--candidate-handoff-fixture-split-smoke",
        "builder_function": "build_candidate_handoff_fixture_split_smoke_review",
        "text_function": "candidate_handoff_fixture_split_smoke_review_text",
        "runtime_directory": "none",
        "smoke_check": "candidate-handoff-fixture-split-smoke-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },
    {
        "surface_id": "v1019-candidate-handoff-parent-replacement-overlay",
        "version": "1019.0",
        "surface_origin_version": "1019.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "candidate-handoff-parent-replacement-overlay",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--candidate-handoff-parent-replacement-overlay",
        "builder_function": "build_candidate_handoff_parent_replacement_overlay_review",
        "text_function": "candidate_handoff_parent_replacement_overlay_review_text",
        "runtime_directory": "none",
        "smoke_check": "candidate-handoff-parent-replacement-overlay-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },
    {
        "surface_id": "v1020-final-timeout-parent-overlay-closure",
        "version": "1020.0",
        "surface_origin_version": "1020.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "final-timeout-parent-overlay-closure",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--final-timeout-parent-overlay-closure",
        "builder_function": "build_final_timeout_parent_overlay_closure_review",
        "text_function": "final_timeout_parent_overlay_closure_review_text",
        "runtime_directory": "none",
        "smoke_check": "final-timeout-parent-overlay-closure-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },
    {
        "surface_id": "v1021-live-install-release-ledger-smoke-debt-route-repair",
        "version": "1021.0",
        "surface_origin_version": "1021.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "live-install-release-ledger-smoke-debt-route-repair",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "--final-timeout-parent-overlay-closure",
        "builder_function": "build_install_release_blocker_ledger_refresh_review",
        "text_function": "install_release_blocker_ledger_refresh_review_text",
        "runtime_directory": "none",
        "smoke_check": "live-install-release-ledger-and-smoke-debt-route-repair-v1",
        "smoke_segment": "install",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },

    {
        "surface_id": "v1022-metadata-currentness-historical-prerequisite-repair",
        "version": "1022.0",
        "surface_origin_version": "1022.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "metadata-currentness-and-historical-prerequisite-repair",
        "dashboard_route": "/metadata-release-integrity-audit",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_metadata_currentness_and_historical_prerequisite_repair_review",
        "text_function": "render_metadata_release_integrity_lines",
        "runtime_directory": "none",
        "smoke_check": "metadata-currentness-and-historical-prerequisite-repair-v1",
        "smoke_segment": "install-core",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },
    {
        "surface_id": "v1023-compile-timeout-historical-gate-harness-honesty",
        "version": "1023.0",
        "surface_origin_version": "1023.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "compile-timeout-historical-gate-harness-honesty",
        "dashboard_route": "/self-development-smoke-debt",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_compile_timeout_and_historical_gate_harness_honesty_review",
        "text_function": "compile_timeout_and_historical_gate_harness_honesty_review_text",
        "runtime_directory": "none",
        "smoke_check": "compile-timeout-and-historical-gate-harness-honesty-v1",
        "smoke_segment": "install-core",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },
    {
        "surface_id": "v1024-behavioral-dashboard-route-coverage-source-decomposition-prep",
        "version": "1024.0",
        "surface_origin_version": "1024.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "behavioral-dashboard-route-coverage-source-decomposition-prep",
        "dashboard_route": "/behavioral-dashboard-route-coverage",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_behavioral_dashboard_route_coverage_and_source_decomposition_prep_review",
        "text_function": "behavioral_dashboard_route_coverage_and_source_decomposition_prep_review_text",
        "runtime_directory": "none",
        "smoke_check": "behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1",
        "smoke_segment": "install-core",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },
    {
        "surface_id": "v1025-first-source-decomposition-compatibility-slice",
        "version": "1025.0",
        "surface_origin_version": "1025.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "first-source-decomposition-compatibility-slice",
        "dashboard_route": "/source-decomposition-compatibility-slice",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_first_source_decomposition_compatibility_slice_review",
        "text_function": "first_source_decomposition_compatibility_slice_review_text",
        "runtime_directory": "none",
        "smoke_check": "first-source-decomposition-compatibility-slice-v1",
        "smoke_segment": "install-core",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },

    {
        "surface_id": "v1026-dashboard-shell-component-extraction-compatibility-slice",
        "version": "1026.0",
        "surface_origin_version": "1026.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "dashboard-shell-component-extraction-compatibility-slice",
        "dashboard_route": "/dashboard-shell-component-extraction",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_dashboard_shell_component_extraction_review",
        "text_function": "dashboard_shell_component_extraction_review_text",
        "runtime_directory": "none",
        "smoke_check": "dashboard-shell-component-extraction-compatibility-slice-v1",
        "smoke_segment": "install-core",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },


    {
        "surface_id": "v1027-smoke-registry-sidecar-compatibility-extraction-slice",
        "version": "1027.0",
        "surface_origin_version": "1027.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-sidecar-compatibility-extraction-slice",
        "dashboard_route": "/smoke-registry-sidecar-compatibility",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_smoke_registry_sidecar_compatibility_review",
        "text_function": "smoke_registry_sidecar_compatibility_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-sidecar-compatibility-extraction-slice-v1",
        "smoke_segment": "install-regression-recent",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },


    {
        "surface_id": "v1028-smoke-registry-sidecar-expansion-route-manifest-prep",
        "version": "1028.0",
        "surface_origin_version": "1028.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "smoke-registry-sidecar-expansion-route-manifest-prep",
        "dashboard_route": "/smoke-registry-sidecar-expansion-route-manifest",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_smoke_registry_sidecar_expansion_route_manifest_prep_review",
        "text_function": "smoke_registry_sidecar_expansion_route_manifest_prep_review_text",
        "runtime_directory": "none",
        "smoke_check": "smoke-registry-sidecar-expansion-and-route-manifest-prep-v1",
        "smoke_segment": "install-regression-recent",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },


    {
        "surface_id": "v1029-route-manifest-inventory-dashboard-parity",
        "version": "1029.0",
        "surface_origin_version": "1029.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "route-manifest-inventory-dashboard-parity",
        "dashboard_route": "/route-manifest-dashboard-parity",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_route_manifest_inventory_expansion_dashboard_parity_review",
        "text_function": "route_manifest_inventory_dashboard_parity_review_text",
        "runtime_directory": "none",
        "smoke_check": "route-manifest-inventory-expansion-and-dashboard-parity-gate-v1",
        "smoke_segment": "install-regression-recent",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },


    {
        "surface_id": "v1030-dashboard-route-behavioral-coverage-expansion",
        "version": "1030.0",
        "surface_origin_version": "1030.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "dashboard-route-behavioral-coverage-expansion",
        "dashboard_route": "/dashboard-route-behavioral-coverage-expansion",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_dashboard_route_behavioral_coverage_expansion_review",
        "text_function": "dashboard_route_behavioral_coverage_expansion_review_text",
        "runtime_directory": "none",
        "smoke_check": "dashboard-route-behavioral-coverage-expansion-v1",
        "smoke_segment": "install-regression-recent",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },

    {
        "surface_id": "v1031-dashboard-route-manifest-renderer-reconciliation",
        "version": "1031.0",
        "surface_origin_version": "1031.0",
        "manifest_representation_version": "1031.0",
        "last_verified_for_version": "1031.0",
        "era": "dashboard-route-manifest-renderer-reconciliation",
        "dashboard_route": "/dashboard-route-manifest-renderer-reconciliation",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_dashboard_route_manifest_renderer_reconciliation_review",
        "text_function": "dashboard_route_manifest_renderer_reconciliation_review_text",
        "runtime_directory": "none",
        "smoke_check": "dashboard-route-manifest-to-renderer-reconciliation-v1",
        "smoke_segment": "install-regression-recent",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },


    {
        "surface_id": "v1032-dashboard-route-coverage-completion-dispatch-classification",
        "version": "1032.0",
        "surface_origin_version": "1032.0",
        "manifest_representation_version": "1032.0",
        "last_verified_for_version": "1032.0",
        "era": "dashboard-route-coverage-completion-dispatch-classification",
        "dashboard_route": "/dashboard-route-coverage-completion-dispatch-classification",
        "api_route": "not_exposed_review_only",
        "cli_flag": "not_exposed_review_only",
        "builder_function": "build_dashboard_route_coverage_completion_dispatch_classification_review",
        "text_function": "dashboard_route_coverage_completion_dispatch_classification_review_text",
        "runtime_directory": "none",
        "smoke_check": "dashboard-route-coverage-completion-and-dispatch-classification-v1",
        "smoke_segment": "install-regression-recent",
        "authority_level": "review_only",
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "package_privacy_sensitive": False,
        "status": "represented",
    },

])

# v1018-v1021 source surface tokens: live-install-release-ledger-and-smoke-debt-route-repair-v1 install-release-blocker-ledger-refresh-v1  candidate-handoff-fixture-split-smoke-v1 candidate-handoff-parent-replacement-overlay-v1 final-timeout-parent-overlay-closure-v1 --candidate-handoff-fixture-split-smoke --candidate-handoff-parent-replacement-overlay --final-timeout-parent-overlay-closure build_candidate_handoff_fixture_split_smoke_review build_candidate_handoff_parent_replacement_overlay_review build_final_timeout_parent_overlay_closure_review candidate_handoff_fixture_split_smoke_review_text candidate_handoff_parent_replacement_overlay_review_text final_timeout_parent_overlay_closure_review_text build_install_release_blocker_ledger_refresh_review build_live_install_release_ledger_rows install_release_blocker_ledger_refresh_review_text live_install_release_total_checks=42 frozen_v1002_install_release_total_checks=30 current_only_check_count=12 install_release_tracked_checks=12 timeout_parent_overlay_clean=True intentional_supervised_blockers_remaining=6 full_install_release_clean=False release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1022 source surface tokens: metadata-currentness-and-historical-prerequisite-repair-v1 build_metadata_currentness_and_historical_prerequisite_repair_review metadata_currentness_dynamic_contract=True stale_wrapper_tokens_required=False historical_prerequisite_next_arc_dynamic=True post_v1000_dashboard_marker_dynamic=True centralized_current_version_required=True stale_expected_current_version_fallback_removed=True release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console

# v1023 source surface tokens: compile-timeout-and-historical-gate-harness-honesty-v1 build_compile_timeout_and_historical_gate_harness_honesty_review compile_timeout_and_historical_gate_harness_honesty_review_text COMPILE_SMOKE_TIMEOUT_SECONDS = 35 compile_timeout_registry_matches_actual=True actual_compile_timeout_uses_constant=True advertised_compile_timeout_uses_constant=True literal_compile_subprocess_timeout_removed=True historical_gate_next_arc_dynamic=True post_v1000_dashboard_marker_dynamic=True centralized_current_version_required=True release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console

# v1024 source surface tokens: behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1 build_behavioral_dashboard_route_coverage_and_source_decomposition_prep_review behavioral_dashboard_route_coverage_and_source_decomposition_prep_review_text behavioral_route_probe_executes_renderers=True behavioral_route_probe_uses_token_presence_only=False critical_dashboard_route_count=12 critical_routes_pass=True source_decomposition_prep_only=True source_decomposition_applied=False manual_registry_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /behavioral-dashboard-route-coverage

# v1025 source surface tokens: first-source-decomposition-compatibility-slice-v1 smoke-timeout-contract-extraction-v1 build_first_source_decomposition_compatibility_slice_review first_source_decomposition_compatibility_slice_review_text build_smoke_timeout_contract_review smoke_timeout_contract_review_text extracted_module=conscious_agent/smoke_timeout_contract.py source_module=tools/smoke_check.py compatibility_slice_applied=True constant_extracted_from_smoke_check=True manual_smoke_local_timeout_assignment_removed=True registry_and_subprocess_still_share_timeout=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /source-decomposition-compatibility-slice

# v1026 source surface tokens: dashboard-shell-component-extraction-compatibility-slice-v1 dashboard-shell-component-extraction-v1 build_dashboard_shell_component_extraction_review dashboard_shell_component_extraction_review_text build_dashboard_shell_component_contract_review dashboard_shell_component_contract_review_text component_module=conscious_agent/dashboard_shell_components.py source_module=conscious_agent/dashboard.py extracted_helpers=safe_html,render_text_block_component,render_card_component compatibility_slice_applied=True legacy_card_wrapper_delegates=True legacy_text_block_wrapper_delegates=True manual_dashboard_remains_authoritative=True dashboard_routes_preserved=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /dashboard-shell-component-extraction

# v1027 source surface tokens: smoke-registry-sidecar-compatibility-extraction-slice-v1 smoke-registry-sidecar-compatibility-v1 build_smoke_registry_sidecar_compatibility_review smoke_registry_sidecar_compatibility_review_text sidecar_module=conscious_agent/smoke_registry_sidecar_compatibility.py manual_smoke_module=tools/smoke_check.py sidecar_metadata_only=True manual_smoke_remains_authoritative=True manual_build_checks_remains_authoritative=True sidecar_executes_checks=False sidecar_replaces_manual_registry=False sidecar_dispatches_callables=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /smoke-registry-sidecar-compatibility


# v1028 source surface tokens: smoke-registry-sidecar-expansion-and-route-manifest-prep-v1 smoke-registry-sidecar-expansion-route-manifest-v1 build_smoke_registry_sidecar_expansion_route_manifest_prep_review smoke_registry_sidecar_expansion_route_manifest_prep_review_text expansion_module=conscious_agent/smoke_registry_sidecar_expansion_route_manifest_prep.py sidecar_compatibility_module=conscious_agent/smoke_registry_sidecar_compatibility.py manual_smoke_module=tools/smoke_check.py expanded_sidecar_check_count=8 route_manifest_route_count=5 sidecar_expanded=True sidecar_metadata_only=True route_manifest_prep_only=True command_manifest_prep_only=True check_manifest_prep_only=True manual_smoke_remains_authoritative=True manual_dashboard_remains_authoritative=True sidecar_executes_checks=False sidecar_replaces_manual_registry=False sidecar_dispatches_callables=False route_manifest_replaces_dashboard_routes=False command_manifest_replaces_cli_dispatch=False check_manifest_replaces_manual_smoke=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /smoke-registry-sidecar-expansion-route-manifest

# v1029 source surface tokens: route-manifest-inventory-expansion-and-dashboard-parity-gate-v1 route-manifest-dashboard-parity-v1 build_route_manifest_inventory_expansion_dashboard_parity_review route_manifest_inventory_dashboard_parity_review_text module=conscious_agent/route_manifest_inventory_dashboard_parity.py dashboard_module=conscious_agent/dashboard.py manual_smoke_module=tools/smoke_check.py route_manifest_inventory_expanded=True dashboard_parity_gate_behavioral=True route_manifest_route_count=23 route_manifest_render_pass_count=23 manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /route-manifest-dashboard-parity

# v1030 source surface tokens: dashboard-route-behavioral-coverage-expansion-v1 dashboard-route-behavioral-coverage-expansion build_dashboard_route_behavioral_coverage_expansion_review dashboard_route_behavioral_coverage_expansion_review_text expanded_behavioral_route_count=48 baseline_route_count=23 added_route_count=25 route_cohort_count=15 render_pass_count=48 render_blocked_count=0 manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /dashboard-route-behavioral-coverage-expansion

# v1031 source surface tokens: dashboard-route-manifest-to-renderer-reconciliation-v1 dashboard-route-manifest-renderer-reconciliation-v1 build_dashboard_route_manifest_renderer_reconciliation_review dashboard_route_manifest_renderer_reconciliation_review_text module=conscious_agent/dashboard_route_manifest_renderer_reconciliation.py dashboard_module=conscious_agent/dashboard.py baseline_module=conscious_agent/dashboard_route_behavioral_coverage_expansion.py baseline_behavioral_route_count=48 mapping_reconciled_route_count=49 behavior_rendered_route_count=48 self_route_mapping_verified=True manual_dispatch_routes_classified=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /dashboard-route-manifest-renderer-reconciliation

# v1032 source surface tokens: dashboard-route-coverage-completion-and-dispatch-classification-v1 dashboard-route-coverage-completion-dispatch-classification-v1 build_dashboard_route_coverage_completion_dispatch_classification_review dashboard_route_coverage_completion_dispatch_classification_review_text module=conscious_agent/dashboard_route_coverage_completion_dispatch_classification.py dashboard_module=conscious_agent/dashboard.py baseline_module=conscious_agent/dashboard_route_behavioral_coverage_expansion.py inherited_baseline_route_count=48 additional_behavioral_route_count=24 total_behavioral_coverage_count=72 mapping_reconciled_route_count=74 additional_render_pass_count=24 manual_dispatch_routes_classified=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True route_manifest_replaces_dashboard_routes=False route_manifest_generates_routes=False dashboard_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False data-tip command-deck operator-console /dashboard-route-coverage-completion-dispatch-classification
