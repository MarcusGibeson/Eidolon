from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_SURFACE_MANIFEST_VERSION = "500.0"

AUTHORITY_LEVELS = {
    "review_only",
    "simulation_only",
    "sandbox_only",
    "execution_prep_only",
    "operator_approved_single_use_trial",
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

RECENT_SURFACE_ENTRIES: list[dict[str, Any]] = [
    {
        "surface_id": "v400-memory-candidate-application-trial",
        "version": "v400.0",
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
        "version": "v405.0",
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
        "version": "v410.0",
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
        "version": "v415.0",
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
        "version": "v420.0",
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
        "version": "v425.0",
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
        "version": "v435.0",
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
        "version": "v440.0",
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
        "version": "v445.0",
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
        "version": "v430.0",
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
        "version": "v450.0",
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


def build_source_surface_manifest_summary(entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entries = [dict(entry) for entry in (entries or RECENT_SURFACE_ENTRIES)]
    blockers: list[str] = []
    required_fields = {
        "surface_id", "version", "era", "dashboard_route", "api_route", "cli_flag",
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
    return {
        "version": SOURCE_SURFACE_MANIFEST_VERSION,
        "state": "canonical_source_surface_manifest_review_only",
        "entries": entries,
        "entry_count": len(entries),
        "manifest_hash": _stable_hash(entries),
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
