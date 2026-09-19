from __future__ import annotations

API_CLI_HELP_SENTINEL = "EIDOLON_API_CLI_HELP_OK"

# Routes exercised by the stabilization contract. The dispatcher below remains
# authoritative; this declaration keeps the operator-facing API surface
# inspectable without executing the server or depending on branch formatting.
STABILIZATION_API_SURFACE = (
    "GET /api/stabilization-checkpoint",
    "GET /api/doctor",
    "GET /api/repair-suggestions",
    "GET /api/patch-integrity",
    "GET /api/project-snapshot",
    "GET /api/tasks/review",
    "GET /api/recovery-drill",
    "GET /api/stable-loops/confidence",
    "GET /api/hardening-report",
    "GET /api/controlled-self-build",
    "GET /api/controlled-build/select-task",
    "GET /api/controlled-build/plan-patch",
    "GET /api/controlled-build/workspace",
    "GET /api/controlled-build/preview-diff",
    "GET /api/controlled-build/readme-gate",
    "POST /api/supervised-dev-loop",
    "GET /api/codebase-map",
    "GET /api/patch-context/layer",
    "GET /api/patch-context/gate",
    "GET /api/task-dependencies",
    "GET /api/test-plan",
    "GET /api/patch-risk",
    "GET /api/patch-review",
    "GET /api/project-memory-index",
    "GET /api/workspace-status",
    "GET /api/cross-project-task-review",
    "GET /api/asymmetric-dev-loop",
    "GET /api/project-registry",
    "POST /api/projects/register",
    "POST /api/projects/active",
    "GET /api/project-health",
    "GET /api/command-profiles",
    "GET /api/workspace-dependency-map",
    "GET /api/workspace-task-inbox",
    "POST /api/workspace/switch-project",
    "GET /api/project-context",
    "GET /api/workspace-timeline",
    "GET /api/workspace-dev-loop",
    "GET /api/stable-loops/preflight",
    "GET /api/stable-loops/guardrails",
    "GET /api/tasks/lifecycle",
    "GET /api/tasks/recovery/summary",
)


def _run_lightweight_api_cli_help() -> None:
    """Serve real API CLI help before importing the historical route graph."""
    import sys as _sys

    if __name__ != "__main__" or not any(arg in {"-h", "--help"} for arg in _sys.argv[1:]):
        return
    import argparse as _argparse

    parser = _argparse.ArgumentParser(
        prog="eidolon-api",
        description="Run or inspect Eidolon's local operator-governed HTTP API.",
        epilog=API_CLI_HELP_SENTINEL,
    )
    parser.add_argument("--host", default=None, help="Bind host; defaults to the configured local API host.")
    parser.add_argument("--port", type=int, default=None, help="Bind port; defaults to the configured local API port.")
    parser.add_argument("--help-sentinel", action="store_true", help=_argparse.SUPPRESS)
    parser.parse_args()
    raise SystemExit(0)


_run_lightweight_api_cli_help()

from release_metadata import RUNTIME_VERSION

import json
import os
import threading
import traceback
import zipfile
from pathlib import Path
from dataclasses import asdict, is_dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from attention_center import build_attention_center
from approval_manager import approve_approval, get_approval, list_approvals, reject_approval
from chat_action_router import execute_chat_action, list_chat_actions, load_chat_action, propose_chat_action
from dashboard_chat_console import create_dashboard_chat_turn, list_dashboard_chat_turns, load_dashboard_chat_turn, stream_dashboard_chat_turn
from conversation_runtime import cancel_conversation_operation
from conversation_control_foundation import build_conversation_control_foundation
from conversation_offline_degradation import offline_conversation_degradation_state
from conversation_long_session_hardening import build_long_session_hardening_state
from conversation_readiness_checkpoint import build_conversation_readiness_checkpoint
from conversation_daily_evaluation_protocol import build_daily_evaluation_protocol
from conversation_daily_evaluation import DailyEvaluationError, load_daily_evaluation
from conversation_evaluation_reproduction import build_reproduction_packet
from conversation_evaluation_trends import build_daily_evaluation_trends
from conversation_evaluation_recovery_scenarios import build_restart_outage_evaluation
from conversation_evaluation_long_session import build_long_session_evaluation
from conversation_evaluation_console import build_evaluation_console_state
from conversation_evaluation_review_export import build_evaluation_review_export
from conversation_daily_evaluation_checkpoint import build_daily_evaluation_checkpoint
from conversation_evaluation_campaign_protocol import build_evaluation_campaign_protocol
from conversation_evaluation_campaign import (
    EvaluationCampaignError,
    abort_evaluation_campaign,
    activate_evaluation_campaign,
    create_evaluation_campaign,
    load_evaluation_campaign,
    update_evaluation_campaign_plan,
)
from conversation_evaluation_campaign_enrollment import (
    build_evaluation_campaign_progress,
    complete_evaluation_campaign,
    enroll_daily_evaluation,
    unenroll_daily_evaluation,
)
from conversation_evaluation_campaign_issues import build_evaluation_campaign_issue_aggregation
from conversation_evaluation_campaign_followups import (
    add_evaluation_campaign_follow_up,
    build_evaluation_campaign_follow_ups,
    remove_evaluation_campaign_follow_up,
    update_evaluation_campaign_follow_up_state,
)
from conversation_evaluation_campaign_comparison import build_evaluation_campaign_comparison
from conversation_evaluation_campaign_review import (
    build_evaluation_campaign_review,
    complete_evaluation_campaign_review,
    remove_evaluation_campaign_review_disposition,
    reopen_evaluation_campaign_review,
    set_evaluation_campaign_review_disposition,
    start_evaluation_campaign_review,
)
from conversation_evaluation_campaign_console import build_evaluation_campaign_console_state
from conversation_evaluation_campaign_review_export import build_evaluation_campaign_review_export
from conversation_evaluation_campaign_checkpoint import build_operator_evaluation_campaign_checkpoint
from conversation_evaluation_finding import (
    EvaluationFindingError,
    create_evaluation_finding,
    list_evaluation_findings,
    load_evaluation_finding,
    set_evaluation_finding_state,
    update_evaluation_finding_details,
)
from conversation_evaluation_finding_reproducibility import (
    build_finding_reproducibility,
    record_reproduction_attempt,
    remove_reproduction_attempt,
)
from conversation_evaluation_finding_repair_candidates import (
    add_repair_candidate_reference,
    build_finding_repair_candidates,
    remove_repair_candidate_reference,
    update_repair_candidate_reference,
)
from conversation_evaluation_finding_aggregation import build_evaluation_finding_aggregation
from conversation_evaluation_finding_triage import (
    build_evaluation_finding_triage,
    complete_evaluation_finding_triage,
    reopen_evaluation_finding_triage,
    set_evaluation_finding_triage_disposition,
    start_evaluation_finding_triage,
)
from conversation_evaluation_finding_comparison import build_evaluation_finding_comparison
from conversation_evaluation_finding_console import build_evaluation_finding_console_state
from conversation_evaluation_finding_review_export import build_evaluation_finding_review_export
from conversation_evaluation_finding_long_session import build_evaluation_finding_window
from conversation_evaluation_finding_checkpoint import build_evaluation_findings_checkpoint
from repair_candidate_review_protocol import build_repair_candidate_review_protocol
from repair_candidate_registration import build_repair_candidate_registrations, register_repair_candidate
from repair_candidate_review import build_repair_candidate_review, record_repair_candidate_review
from repair_candidate_verification_evidence import (
    build_repair_candidate_verification_evidence,
    record_repair_candidate_verification_evidence,
)
from repair_candidate_comparison import build_repair_candidate_comparison
from repair_candidate_lineage import build_repair_candidate_lineage, link_repair_candidate_lineage
from repair_candidate_console import build_repair_candidate_console_state
from repair_candidate_review_export import build_repair_candidate_review_export
from repair_candidate_long_session import build_repair_candidate_window
from repair_candidate_review_checkpoint import build_repair_candidate_review_checkpoint
from product_reality_benchmark import build_product_reality_benchmark
from conversation_generation_steering import (
    ConversationSteeringError,
    build_generation_steering_plan,
    request_generation_steering,
)
from conversation_retry_regeneration import (
    ConversationTurnActionError,
    build_turn_action_plan,
    execute_turn_action,
)
from conversation_message_branching import (
    ConversationBranchError,
    build_message_branch_plan,
    create_message_edit_branch,
)
from daily_use_stability_checkpoint import build_daily_use_stability_checkpoint
from conversation_quality_checkpoint import build_conversation_quality_checkpoint
from context_inspection_console import build_context_inspection_for_session
from context_intelligence_checkpoint import build_context_intelligence_checkpoint
from relationship_continuity_checkpoint import build_relationship_continuity_checkpoint
from diagnostics import build_diagnostic_report, list_diagnostic_reports, load_diagnostic_report, save_diagnostic_report
from goal_manager import add_goal, get_goal, list_goals
from maintenance_advisor import list_maintenance_scans, load_maintenance_scan, run_maintenance_scan
from memory import count_memories, load_memories
from local_brain import local_model_status
from local_model_readiness import native_model_smoke, provider_readiness
from local_model import LocalModelConfig
from local_model_evidence import configuration_digest
from provider_recovery_evidence import (
    load_provider_recovery_evidence,
    persist_provider_recovery_evidence,
    provider_resume_cue,
)
from native_conversation_validation import CONFIRMATION_PHRASE as NATIVE_CONVERSATION_CONFIRMATION, run_native_conversation_validation
from local_model_configuration import (
    LocalModelConfigurationValidationError,
    configuration_payload,
    save_local_model_configuration,
    validate_local_model_configuration,
)
from notification_manager import (
    clear_dismissed_notifications,
    list_notifications,
    load_notification,
    update_notification_status,
)
from patch_suggester import list_patch_proposals, load_patch_proposal, suggest_patch
from task_patch_bridge import (
    create_patch_followup_tasks,
    create_patch_task,
    suggest_patch_for_task,
)
from work_queue_patch_bridge import (
    create_patch_followup_items,
    create_patch_work_item,
    suggest_patch_for_work_item,
)
from project_manager import get_active_project
from session_planner import create_session_plan, list_session_plans, load_session_plan
from settings_manager import get_setting, load_settings
from desktop_setup_helper import create_setup_report, list_setup_reports, load_setup_report
from desktop_onboarding_wizard import build_onboarding_run, list_onboarding_runs, load_onboarding_run
from task_queue import add_task, get_task, list_tasks, task_status_counts, update_task_fields
from work_queue import (
    add_work_item,
    find_work_item,
    list_work_items,
    summarize_queue,
    update_work_item,
)
from task_work_executor import execute_next_task_work, execute_task_work_item
from task_approval_bridge import (
    list_task_approvals,
    request_next_task_work_approval,
    request_task_work_approval,
)
from task_lifecycle import derive_task_lifecycle, list_task_lifecycles, normalize_lifecycle_stage_filter, task_lifecycle_summary
from task_recovery import (
    build_task_recovery,
    list_task_recoveries,
    mark_task_ready_for_retry,
    retry_task_work,
    task_recovery_summary,
)
from work_cycle import list_work_cycles, load_work_cycle, run_supervised_work_cycle
from stable_supervised_loop import (
    build_stable_loop_preflight,
    list_stable_loops,
    load_stable_loop,
    run_stable_supervised_loop,
)
from stable_loop_review import (
    cleanup_stable_loop_history,
    list_stable_loop_reviews,
    run_approved_stable_loop_live,
    set_stable_loop_archived,
    stable_loop_review_summary,
    update_stable_loop_review,
)
from stable_loop_audit import build_stable_loop_audit, refresh_stable_loop_audit
from stable_loop_operator_notes import (
    add_stable_loop_operator_note,
    get_stable_loop_operator_notes,
    set_stable_loop_final_decision,
    update_stable_loop_check,
)
from stable_loop_decision_report import (
    cleanup_stable_loop_decision_history,
    list_stable_loop_decision_rows,
    stable_loop_decision_summary,
)
from stable_loop_followup_tasks import (
    create_stable_loop_followup_tasks,
    create_stable_loop_followups_for_decisions,
    plan_stable_loop_followups,
    stable_loop_followup_summary,
)
from stable_loop_followup_lifecycle import (
    list_stable_loop_followup_task_rows,
    resolve_stable_loop_followups,
    resolve_task_stable_loop_followup,
    stable_loop_followup_lifecycle_summary,
    stable_loop_followup_task_row,
)
from stable_loop_followup_completion import (
    cleanup_stable_loop_followup_completions,
    list_stable_loop_followup_completion_rows,
    mark_stable_loop_followup_chain_closed,
    stable_loop_followup_completion_summary,
)
from stable_loop_guardrails import stable_loop_guardrail_summary
from stabilization_checkpoint import build_stabilization_checkpoint
from operational_readiness import (
    build_doctor_report,
    build_repair_suggestions,
    build_patch_integrity_report,
    build_project_snapshot,
    build_task_review,
    build_recovery_drill,
    build_stable_loop_confidence,
    build_hardening_report,
    build_controlled_self_build,
    build_controlled_self_build_lightweight_preview,
)
from doctor_diagnostic_preview_cache_heavy_route_decoupling import build_doctor_diagnostic_preview_cache
from doctor_diagnostic_cache_freshness_invalidation_review import build_doctor_diagnostic_cache_freshness_metadata
from doctor_diagnostic_cache_source_dependency_digest_verification import build_doctor_diagnostic_cache_source_dependency_digest_metadata
from doctor_diagnostic_cache_digest_drift_classification import build_doctor_diagnostic_cache_digest_drift_classification_metadata
from doctor_diagnostic_cache_contract_drift_fixture_expansion import build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata
from doctor_diagnostic_cache_drift_severity_guidance import build_doctor_diagnostic_cache_drift_severity_guidance_metadata
from doctor_diagnostic_cache_severity_route_impact_matrix import build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata
from doctor_diagnostic_cache_impact_operator_action_ledger import build_doctor_diagnostic_cache_impact_operator_action_ledger_metadata
from doctor_deep_diagnostic_latency_budget_repair import (
    build_doctor_deep_diagnostic_latency_budget_repair_metadata,
    build_bounded_repair_suggestions,
    build_bounded_project_snapshot,
    build_bounded_stable_loop_confidence,
    build_bounded_hardening_report,
)
from controlled_build_cycle import (
    build_controlled_task_selection,
    build_patch_plan,
    patch_workspace_status,
    stage_controlled_patch,
    preview_staged_diff,
    apply_staged_patch,
    verify_latest_patch,
    rollback_latest_patch,
    readme_gate,
    build_controlled_build_cycle,
    build_supervised_dev_loop,
)

from project_intelligence import (
    build_codebase_map,
    build_task_dependencies,
    build_test_plan,
    build_patch_risk,
    build_patch_review,
    build_project_memory_index,
    build_workspace_status,
    build_cross_project_task_review,
    build_asymmetric_dev_loop,
)
from workspace_orchestration import (
    build_project_registry,
    register_project,
    set_active_workspace_project,
    build_project_health,
    build_command_profiles,
    build_workspace_dependency_map,
    build_workspace_task_inbox,
    switch_workspace_project,
    build_project_context,
    build_workspace_timeline,
    build_workspace_dev_loop,
)
from workspace_execution import (
    build_workspace_registry_audit,
    build_workspace_repair_suggestions,
    build_project_registration_wizard,
    build_project_boundary_check,
    build_workspace_patch_plan,
    build_workspace_preview_diff,
    build_workspace_apply,
    build_workspace_verify_latest,
    build_guarded_workspace_dev_loop,
)
from patch_drafting import (
    build_patch_draft_request,
    build_draft_patch,
    build_patch_draft_status,
    build_patch_review_notes,
    build_draft_diff,
    build_draft_test_impact,
    build_approval_gate,
    approve_draft,
    reject_draft,
    build_apply_approved_draft,
    build_rollback_approved_draft,
    reopen_draft,
    build_human_approved_patch_loop,
    build_draft_quality,
    build_draft_file_targets,
    build_draft_intent_blocks,
    build_draft_conflicts,
    build_draft_verification_bundle,
    build_draft_review_checklist,
    build_approved_draft_execution_report,
    build_review_centered_patch_loop,
)
from release_pipeline import (
    build_code_edit_proposal,
    build_safe_rewrite_preview,
    build_generated_code_patch,
    build_test_suggestions,
    build_inline_review_note,
    build_apply_approved_code_patch,
    build_prepare_release_package,
    build_release_readiness,
    build_human_approved_release_loop,
)
from code_patch_release import (
    build_code_patch_status,
    build_symbol_scan,
    build_rewrite_plan,
    build_rewrite_conflicts,
    build_code_patch_diff_bundle,
    build_apply_code_patch_transaction,
    build_semantic_checks,
    build_release_artifact,
    build_release_audit_trail,
    build_generated_code_release_loop,
)
from ai_patch_assistance import (
    build_task_to_code_patch,
    build_code_context,
    build_patch_prompt,
    build_parse_generated_edits,
    build_edit_consistency,
    build_ai_code_patch_dry_run,
    build_patch_failure_analysis,
    build_patch_learning_notes,
    build_ai_assisted_code_patch_loop,
)
from validated_ai_patch_loop import (
    build_patch_objective_refinement,
    build_code_context_ranking,
    build_patch_safety_envelope,
    build_generated_patch_validation,
    build_patch_simulation,
    build_test_stub_plan,
    build_patch_review_score,
    build_patch_recovery_plan,
    build_validated_ai_code_patch_loop,
)
from approval_release_workflow import (
    bind_current_approval_to_validated_manifest,
    build_ai_patch_review_bundle,
    build_review_bundle_integrity,
    build_approval_ready,
    build_approval_ledger,
    build_apply_validated_ai_patch,
    build_post_apply_review,
    build_package_build_plan,
    build_approval_to_release_loop,
)
from release_packaging import (
    build_release_manifest_integrity,
    build_package_inventory,
    build_package_checksums,
    build_release_notes,
    build_release_handoff_report,
    build_release_zip,
    build_verify_release_unzip,
    build_release_pipeline_audit,
    build_verified_release_package_loop,
    summarize_release_report,
    _package_name,
)
from release_installation import (
    build_release_profiles,
    build_package_privacy_scan,
    build_portable_metadata_check,
    build_first_run_check,
    build_dependency_advisor,
    build_upgrade_notes,
    build_runtime_migration_check,
    build_release_install_verification,
    build_verified_installable_release_loop,
    build_smoke_runtime_hardening,
    build_external_zip_install_verification,
    build_deterministic_release_manifest,
    build_update_dry_run_plan,
    build_atomic_source_update,
    build_runtime_migration_assistant,
    build_route_safety_harness,
    build_release_dashboard_command_center,
    build_clean_room_install_harness,
    build_verified_self_update_release_pipeline,
    build_trial_upgrade_harness,
    build_backup_rollback_drill,
    build_update_collision_detector,
    build_version_registry_report,
    build_release_provenance_report,
    build_dashboard_upgrade_wizard_preview,
    build_api_upgrade_wizard_preview,
    build_staged_apply_drill,
    build_real_apply_guard_rails,
    build_real_apply_rollback_verification,
    build_self_update_ux_polish,
    build_v23_readiness_gate,
    build_controlled_self_maintenance_loop,
    summarize_installation_report,
)
class _LazyModuleProxy:
    """Resolve a historically heavy module only when an API route needs it."""

    __slots__ = ("_module_name", "_module")

    def __init__(self, module_name: str) -> None:
        self._module_name = module_name
        self._module = None

    def _load(self):
        if self._module is None:
            import importlib
            self._module = importlib.import_module(self._module_name)
        return self._module

    def __getattr__(self, name: str):
        return getattr(self._load(), name)


def _lazy_module_callable(proxy: _LazyModuleProxy, name: str):
    def invoke(*args, **kwargs):
        return getattr(proxy, name)(*args, **kwargs)
    invoke.__name__ = name
    invoke.__qualname__ = name
    return invoke


sm_v45 = _LazyModuleProxy("self_maintenance")
_SELF_MAINTENANCE_LAZY_EXPORTS = (
    'build_self_maintenance_proposal_sandbox',
    'build_patch_plan_builder',
    'build_dry_run_patch_generator',
    'build_patch_safety_auditor',
    'build_apply_patch_to_temp_clone',
    'build_maintenance_review_bundle',
    'build_human_approval_binding',
    'build_real_maintenance_patch_apply',
    'build_post_apply_health_monitor',
    'build_controlled_maintenance_cycle',
    'build_assisted_self_improvement_release',
    'build_improvement_candidate_scan',
    'build_candidate_prioritizer',
    'build_candidate_to_proposal_bridge',
    'build_maintenance_backlog_registry',
    'build_dashboard_maintenance_backlog',
    'build_api_maintenance_backlog',
    'build_candidate_regression_detector',
    'build_release_memory_privacy',
    'build_candidate_verification_recipes',
    'build_assisted_improvement_cycle',
    'build_semi_autonomous_maintenance_review',
    'build_hotfix_regression_lockdown',
    'build_dashboard_route_coverage_auditor',
    'build_api_default_source_audit',
    'build_nested_readiness_severity_engine',
    'build_review_bundle_approval_contract',
    'build_maintenance_report_diff_viewer',
    'build_release_gate_composition_test',
    'build_dashboard_api_parity_audit',
    'build_operator_trust_report',
    'build_trustworthy_maintenance_console',
    'build_trust_console_drill',
    'build_trust_console_snapshot',
    'build_trust_console_diff',
    'build_release_candidate_freezer',
    'build_frozen_release_zip_verification',
    'build_approval_evidence_ledger',
    'build_release_command_reproducer',
    'build_console_readme_consistency',
    'build_pre_v27_safety_audit',
    'build_release_candidate_governance',
    'build_release_governance_drill',
    'build_release_evidence_bundle',
    'build_release_evidence_bundle_verifier',
    'build_release_governance_page',
    'build_governance_api_read_only_surface',
    'build_release_artifact_diff',
    'build_release_signing_preparation',
    'build_local_trust_policy',
    'build_release_governance_ux_polish',
    'build_pre_v28_governance_audit',
    'build_verifiable_release_evidence_system',
    'build_evidence_replay_drill',
    'build_evidence_bundle_persistence',
    'build_replay_release_evidence',
    'build_evidence_timeline',
    'build_evidence_operator_summary',
    'build_dashboard_evidence_viewer',
    'build_api_evidence_viewer',
    'build_evidence_retention_policy',
    'build_evidence_regression_lockdown',
    'build_pre_v29_evidence_audit',
    'build_durable_release_evidence_archive',
    'build_signing_readiness_audit',
    'build_canonical_manifest_format',
    'build_canonical_evidence_schema',
    'build_release_signing_status',
    'build_signature_placeholder_contract',
    'build_key_policy_preparation',
    'build_signature_verification_placeholder',
    'build_dashboard_signing_status',
    'build_api_signing_status',
    'build_pre_v30_signing_prep_audit',
    'build_signed_release_preparation_system',
    'build_signing_api_hardening',
    'build_canonical_schema_validator',
    'build_source_data_sanitizer',
    'build_signing_trust_model',
    'build_release_signing_tamper_drill',
    'build_public_key_policy_design',
    'build_detached_signature_contract',
    'build_signature_fixture_verification',
    'build_external_signer_workflow',
    'build_detached_signature_verification_system',
    'build_signature_verification_hardening',
    'build_public_trust_root_config',
    'build_external_signing_payload_export',
    'build_signed_fixture_test_suite',
    'build_release_publish_gate',
    'build_release_trust_dashboard_polish',
    'build_api_route_safety_audit',
    'build_release_reproducibility_check',
    'build_pre_v32_release_candidate_gate',
    'build_signed_release_governance',
    'build_governance_report_cleanup',
    'build_release_candidate_workspace',
    'build_artifact_binding_audit_v2',
    'build_surface_consistency_audit',
    'build_external_signing_handoff',
    'build_signature_intake_validation',
    'build_trusted_signer_registry',
    'build_governance_scenario_suite',
    'build_pre_v33_operations_gate',
    'build_release_operations_console',
    'build_operations_console_cleanup',
    'build_release_candidate_review',
    'build_signed_artifact_intake',
    'build_trust_root_lifecycle',
    'build_publish_decision_explainer',
    'build_operator_action_guardrails',
    'build_unsigned_release_drill',
    'build_signed_fixture_release_drill',
    'build_pre_v34_operator_workflow_gate',
    'build_release_operator_workflow',
    'build_release_candidate_record_v2',
    'build_signed_artifact_intake_v2',
    'build_trust_root_management_policy',
    'build_trust_root_mutation_guardrails',
    'build_signed_release_publish_decision',
    'build_operator_dashboard_action_states',
    'build_release_audit_trail',
    'build_trusted_fixture_workflow',
    'build_pre_v35_trusted_candidate_gate',
    'build_trusted_release_candidate_system',
    'build_candidate_review_state',
    'build_publish_approval_policy',
    'build_publish_approval_dry_run',
    'build_publish_approval_record_schema',
    'build_dashboard_approval_state_preview',
    'build_approval_route_safety_audit',
    'build_approval_fixture_drill',
    'build_publish_approval_explainer',
    'build_pre_v36_approval_separation_gate',
    'build_publish_approval_separation_system',
    'build_publish_approval_record_validator',
    'build_publish_approval_dry_run_v2',
    'build_approval_storage_quarantine',
    'build_publish_approval_api_preview',
    'build_dashboard_approval_workflow_preview',
    'build_approval_confirmation_policy',
    'build_approval_record_fixture_drill',
    'build_approval_audit_trail',
    'build_pre_v37_approval_records_gate',
    'build_controlled_publish_approval_system',
    'build_publish_approval_write_preflight',
    'build_publish_approval_write_schema_lock',
    'build_publish_approval_confirmation_validator',
    'build_post_only_approval_write_route_design',
    'build_approval_write_dashboard_preview',
    'build_write_publish_approval',
    'build_approval_write_rollback_safety_audit',
    'build_approval_write_fixture_drill',
    'build_pre_v38_approval_write_gate',
    'build_controlled_publish_approval_write_system',
    'build_publish_approval_record_reader',
    'build_approval_artifact_revalidation',
    'build_approval_record_conflict_detector',
    'build_approval_status_viewer',
    'build_approval_revocation_policy',
    'build_approval_revocation_dry_run',
    'build_approval_lifecycle_audit',
    'build_approval_lifecycle_fixture_drill',
    'build_pre_v39_approval_lifecycle_gate',
    'build_publish_approval_lifecycle_system',
    'build_approval_revocation_record_schema',
    'build_approval_revocation_confirmation_validator',
    'build_approval_revocation_write_preflight',
    'build_revocation_storage_quarantine',
    'build_post_only_revocation_route_design',
    'build_write_approval_revocation',
    'build_dashboard_revocation_preview',
    'build_approval_revocation_fixture_drill',
    'build_pre_v40_revocation_gate',
    'build_controlled_publish_approval_revocation_system',
    'build_autonomy_capability_inventory',
    'build_autonomous_task_proposal_schema',
    'build_autonomous_dry_run_plan',
    'build_autonomy_action_policy_engine',
    'build_autonomous_patch_sandbox',
    'build_autonomous_patch_risk_classifier',
    'build_autonomous_test_selection',
    'build_autonomy_human_checkpoint',
    'build_pre_v41_autonomy_readiness_gate',
    'build_autonomy_readiness_boundary_system',
    'build_patch_proposal_schema',
    'build_autonomous_change_target_selector',
    'build_generate_sandbox_patch',
    'build_sandbox_patch_diff',
    'build_sandbox_patch_validation',
    'build_sandbox_patch_test_run',
    'build_patch_review_checkpoint',
    'build_source_apply_dry_run',
    'build_pre_v42_autonomous_patch_gate',
    'build_autonomous_patch_proposal_system',
    'build_source_apply_eligibility',
    'build_source_apply_confirmation_policy',
    'build_source_apply_dry_run_v2',
    'build_source_apply_backup_quarantine',
    'build_apply_reviewed_patch',
    'build_post_source_apply_verification',
    'build_source_apply_rollback_preview',
    'build_source_apply_fixture_drill',
    'build_pre_v43_source_apply_gate',
    'build_controlled_source_apply_system',
    'build_source_apply_record_reader',
    'build_source_rollback_eligibility',
    'build_source_rollback_confirmation_policy',
    'build_source_rollback_dry_run_v2',
    'build_rollback_applied_patch',
    'build_post_source_rollback_verification',
    'build_source_rollback_audit_trail',
    'build_source_rollback_fixture_drill',
    'build_pre_v44_source_rollback_gate',
    'build_controlled_source_rollback_system',
    'summarize_self_maintenance_report',
)
for _lazy_name in _SELF_MAINTENANCE_LAZY_EXPORTS:
    globals()[_lazy_name] = _lazy_module_callable(sm_v45, _lazy_name)
del _lazy_name
from self_development_cycle import build_self_development_cycle_api_layer
from dev_loop_runner import get_dev_loop, list_dev_loops, run_dev_loop
from test_report_reviewer import list_test_reviews
from test_runner import list_test_reports
from watch_mode import list_watch_reports, load_watch_report, run_watch_loop, run_watch_once

from api_request_boundary import (
    ApiError,
    _now,
    _to_jsonable,
    _query_release_zip_path,
    _query_path,
    _query_signature_options,
    _path_parts,
    _query_bool,
    _body_bool,
    _require_confirmation,
    parse_request_body,
)


API_VERSION = RUNTIME_VERSION

def _ok(data: Any | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "api_version": API_VERSION,
        "served_at": _now(),
    }
    if data is not None:
        payload["data"] = _to_jsonable(data)
    payload.update({key: _to_jsonable(value) for key, value in extra.items()})
    return payload


def _error(status: int, message: str, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "api_version": API_VERSION,
        "served_at": _now(),
        "error": message,
    }
    if details is not None:
        payload["details"] = _to_jsonable(details)
    return payload



def _api_index() -> dict[str, Any]:
    """Return the extracted read-only API catalog."""
    from api_catalog import build_api_index

    return build_api_index(API_VERSION)


def _build_status_payload_uncached() -> dict[str, Any]:
    tasks = list_tasks(include_cancelled=False)
    approvals = list_approvals(include_closed=True)
    pending_approvals = [item for item in approvals if item.get("status") == "pending"]
    notifications = list_notifications(include_dismissed=True)
    unread_notifications = [item for item in notifications if item.get("status") == "unread"]
    patches = list_patch_proposals()
    reports = list_test_reports()
    reviews = list_test_reviews()
    watch_reports = list_watch_reports()
    diagnostics = list_diagnostic_reports()
    setup_reports = list_setup_reports()
    onboarding_runs = list_onboarding_runs()
    work_summary = summarize_queue()
    lifecycle_summary = task_lifecycle_summary()
    recovery_summary = task_recovery_summary()
    work_cycles = list_work_cycles()
    stable_loops = list_stable_loops()
    stable_review_summary = stable_loop_review_summary()
    stable_decision_summary = stable_loop_decision_summary()
    try:
        stable_guardrails = stable_loop_guardrail_summary(project_id="eidolon")
    except Exception as guardrail_error:
        stable_guardrails = {"ok": False, "error": str(guardrail_error), "unresolved_count": 0, "ok_for_live": False}
    next_work = work_summary.get("next_item") or {}
    settings = load_settings()

    return {
        "name": "Eidolon",
        "api_version": API_VERSION,
        "active_project": get_active_project(),
        "counts": {
            "memories": count_memories(),
            "tasks": len(tasks),
            "task_status": task_status_counts(),
            "approvals": len(approvals),
            "pending_approvals": len(pending_approvals),
            "notifications": len(notifications),
            "unread_notifications": len(unread_notifications),
            "patches": len(patches),
            "test_reports": len(reports),
            "test_reviews": len(reviews),
            "watch_reports": len(watch_reports),
            "diagnostic_reports": len(diagnostics),
            "session_plans": len(list_session_plans()),
            "maintenance_scans": len(list_maintenance_scans()),
            "chat_actions": len(list_chat_actions(include_closed=True)),
            "dashboard_chat_turns": len(list_dashboard_chat_turns()),
            "goals": len(list_goals()),
            "setup_reports": len(setup_reports),
            "onboarding_runs": len(onboarding_runs),
            "work_queue_total": work_summary.get("total", 0),
            "work_queue_pending": work_summary.get("pending", 0),
            "work_queue_active": work_summary.get("active", 0),
            "work_queue_blocked": work_summary.get("blocked", 0),
            "work_queue_done": work_summary.get("done", 0),
            "work_queue_failed": work_summary.get("failed", 0),
            "work_queue_approval_required": work_summary.get("approval_required", 0),
            "task_lifecycle_needs_attention": lifecycle_summary.get("needs_attention", 0),
            "task_lifecycle_open": lifecycle_summary.get("open", 0),
            "task_recovery_needed": recovery_summary.get("recoverable", 0),
            "work_cycles": len(work_cycles),
            "stable_loops": len(stable_loops),
            "stable_loop_unreviewed": stable_review_summary.get("unreviewed_preview_count", 0),
            "stable_loop_approved_ready": stable_review_summary.get("approved_ready_count", 0),
            "stable_loop_decision_action_required": stable_decision_summary.get("action_required_count", 0),
            "stable_loop_decision_cleanup_candidates": stable_decision_summary.get("cleanup_candidate_count", 0),
            "stable_loop_guardrail_unresolved": stable_guardrails.get("unresolved_count", 0),
            "stable_loop_guardrail_live_ready": bool(stable_guardrails.get("ok_for_live")),
        },
        "task_lifecycle": lifecycle_summary,
        "task_recovery": recovery_summary,
        "stable_loop_review": stable_review_summary,
        "stable_loop_decisions": stable_decision_summary,
        "stable_loop_guardrails": stable_guardrails,
        "latest": {
            "diagnostic_report_id": diagnostics[0].get("id") if diagnostics else "",
            "watch_report_id": watch_reports[0].get("id") if watch_reports else "",
            "pending_approval_id": pending_approvals[0].get("id") if pending_approvals else "",
            "unread_notification_id": unread_notifications[0].get("id") if unread_notifications else "",
            "maintenance_scan_id": list_maintenance_scans()[0].get("id") if list_maintenance_scans() else "",
            "dev_loop_id": list_dev_loops()[0].get("id") if list_dev_loops() else "",
            "setup_report_id": setup_reports[0].get("id") if setup_reports else "",
            "setup_status": setup_reports[0].get("status") if setup_reports else "",
            "onboarding_run_id": onboarding_runs[0].get("id") if onboarding_runs else "",
            "onboarding_status": onboarding_runs[0].get("status") if onboarding_runs else "",
            "work_item_id": next_work.get("id", ""),
            "work_item_title": next_work.get("title", ""),
            "work_cycle_id": work_cycles[0].get("id") if work_cycles else "",
            "stable_loop_id": stable_loops[0].get("id") if stable_loops else "",
        },
        "settings": {
            "dashboard_host": settings.get("dashboard_host"),
            "dashboard_port": settings.get("dashboard_port"),
            "api_host": settings.get("api_host"),
            "api_port": settings.get("api_port"),
            "safe_mode": settings.get("safe_mode"),
            "dashboard_live_refresh_enabled": settings.get("dashboard_live_refresh_enabled"),
            "dashboard_live_refresh_seconds": settings.get("dashboard_live_refresh_seconds"),
        },
        "live_refresh": {
            "enabled": bool(settings.get("dashboard_live_refresh_enabled", True)),
            "interval_seconds": int(settings.get("dashboard_live_refresh_seconds", 5) or 5),
        },
    }


def build_status_payload() -> dict[str, Any]:
    """Return a short-lived read-only status projection for polling clients."""
    from runtime_projection_cache import cached_read_only_projection
    return cached_read_only_projection("api_status", _build_status_payload_uncached, ttl_seconds=0.75)


def build_desktop_attention_payload() -> dict[str, Any]:
    """Compact desktop-focused status payload for quick actions.

    This is read-only. It exists so the desktop shell can display the most
    important pending items without scraping several endpoints like a raccoon
    in a JSON dumpster.
    """
    status = build_status_payload()
    unread = list_notifications(status="unread", include_dismissed=False)
    pending = list_approvals(status="pending", include_closed=False)

    quick_actions = [
        {
            "id": "run_diagnostics",
            "label": "Run diagnostics",
            "method": "POST",
            "endpoint": "/api/diagnostics/run",
            "risk": "read_only",
        },
        {
            "id": "watch_once",
            "label": "Run watch once",
            "method": "POST",
            "endpoint": "/api/watch/run-once",
            "risk": "read_only",
        },
        {
            "id": "maintenance_scan",
            "label": "Run maintenance scan",
            "method": "POST",
            "endpoint": "/api/maintenance/run",
            "risk": "read_only",
        },
        {
            "id": "plan_session",
            "label": "Plan session",
            "method": "POST",
            "endpoint": "/api/session-plans/run",
            "risk": "read_only",
        },
        {
            "id": "mark_latest_unread_read",
            "label": "Mark latest unread notification read",
            "method": "POST",
            "endpoint": "/api/notifications/latest-unread/read",
            "risk": "metadata_only",
        },
        {
            "id": "dismiss_latest_unread",
            "label": "Dismiss latest unread notification",
            "method": "POST",
            "endpoint": "/api/notifications/latest-unread/dismiss",
            "risk": "metadata_only",
        },
        {
            "id": "dry_run_latest_approval",
            "label": "Dry-run latest pending approval",
            "method": "POST",
            "endpoint": "/api/approvals/latest-pending/approve",
            "risk": "dry_run",
        },
    ]

    return {
        "status": status,
        "top_unread_notifications": unread[:5],
        "top_pending_approvals": pending[:5],
        "quick_actions": quick_actions,
        "safety": "Desktop quick actions are local API calls. File edits and approval-gated actions still use existing safety gates.",
    }


def handle_api_get(path: str, query: dict[str, list[str]] | None = None) -> tuple[int, dict[str, Any]]:
    parsed_path = urlparse(path)
    query = query or parse_qs(parsed_path.query)
    path = parsed_path.path
    parts = _path_parts(path)

    if not parts:
        return 200, _ok(_api_index())

    if parts == ["activities"] or (len(parts) == 2 and parts[0] == "activities"):
        from activity import activities
        try:
            return 200, _ok(activities(activity_id=parts[1] if len(parts) == 2 else None))
        except ValueError:
            return 400, {"ok": False, "error": "invalid_activity_id"}

    if parts == ["training-evidence", "status"]:
        from model_training.training_operator import build_training_evidence_status
        return 200, _ok(build_training_evidence_status())

    if parts == ["cognition", "observability", "project-queue"]:
        from developer_project_queue_mind_v2626 import build_developer_project_queue_mind_observability
        return 200, _ok(build_developer_project_queue_mind_observability())

    if parts == ["cognition", "observability", "project-simulation"]:
        from developer_project_simulation_observability_v2656 import build_project_simulation_observability
        return 200, _ok(build_project_simulation_observability())

    if parts == ["cognition", "observability", "verification"]:
        from verification_observability_v2558 import build_verification_observability
        try:
            window_size = int(query.get("window", ["8"])[0] or 8)
        except (TypeError, ValueError):
            window_size = 8
        return 200, _ok(build_verification_observability(window_size=window_size))

    if parts == ["cognition", "observability", "sessions"]:
        from cognitive_observability_sessions_v2537 import build_cognitive_observability_sessions
        try:
            limit = int(query.get("limit", ["12"])[0] or 12)
        except (TypeError, ValueError):
            limit = 12
        return 200, _ok(build_cognitive_observability_sessions(limit=limit))

    if parts == ["cognition", "observability"]:
        from cognitive_observability_v2533 import build_cognitive_observability_snapshot
        try:
            limit = int(query.get("limit", ["40"])[0] or 40)
        except (TypeError, ValueError):
            limit = 40
        kind = str(query.get("kind", [""])[0] or "")
        try:
            return 200, _ok(build_cognitive_observability_snapshot(limit=limit, kind=kind))
        except ValueError as error:
            return 400, _error(400, str(error))

    if parts == ["cognition", "inspection"]:
        from proactive_communication import build_cognition_inspection
        return 200, _ok(build_cognition_inspection())

    if parts == ["cognition", "continuity"]:
        from cognitive_continuity import build_cognitive_continuity_inspection
        return 200, _ok(build_cognitive_continuity_inspection())

    if parts == ["cognition", "beliefs"]:
        from belief_revision import build_belief_revision_inspection
        return 200, _ok(build_belief_revision_inspection())

    if parts == ["cognition", "inquiries"]:
        from self_directed_inquiry import build_inquiry_inspection
        return 200, _ok(build_inquiry_inspection())

    if parts == ["cognition", "inquiry-attention"]:
        from inquiry_attention_routing import build_inquiry_attention_inspection
        return 200, _ok(build_inquiry_attention_inspection())

    if parts == ["cognition", "inquiry-evidence"]:
        from inquiry_evidence_assimilation import build_inquiry_evidence_inspection
        return 200, _ok(build_inquiry_evidence_inspection())

    if parts == ["cognition", "inquiry-conversation"]:
        from inquiry_conversation_continuity import build_inquiry_conversation_inspection
        return 200, _ok(build_inquiry_conversation_inspection())

    if parts == ["cognition", "inquiry-quality"]:
        from inquiry_evidence_quality import build_inquiry_evidence_quality_inspection
        return 200, _ok(build_inquiry_evidence_quality_inspection())

    if parts == ["cognition", "inquiry-reflections"]:
        from inquiry_reflection import build_inquiry_reflection_inspection
        return 200, _ok(build_inquiry_reflection_inspection())

    if parts == ["cognition", "inquiry-resolutions"]:
        from inquiry_resolution import build_inquiry_resolution_inspection
        return 200, _ok(build_inquiry_resolution_inspection())

    if parts == ["cognition", "prospective-planning"]:
        from prospective_planning import build_prospective_planning_inspection
        return 200, _ok(build_prospective_planning_inspection())

    if parts == ["cognition", "native-reflection-evaluation"]:
        from native_reflection_evaluation import build_native_reflection_evaluation_inspection
        return 200, _ok(build_native_reflection_evaluation_inspection())

    if parts == ["cognition", "internal-life-checkpoint"]:
        from persistent_internal_life_checkpoint import build_persistent_internal_life_checkpoint
        return 200, _ok(build_persistent_internal_life_checkpoint())

    if parts == ["cognition", "development-checkpoint"]:
        from cognitive_development_checkpoint import build_cognitive_development_checkpoint
        return 200, _ok(build_cognitive_development_checkpoint())

    if parts == ["cognition", "inquiry-checkpoint"]:
        from inquiry_cognition_checkpoint import build_inquiry_cognition_checkpoint
        return 200, _ok(build_inquiry_cognition_checkpoint())

    if parts == ["cognition", "inquiry-residual-lineage"]:
        from inquiry_residual_lineage import build_inquiry_residual_lineage_inspection
        return 200, _ok(build_inquiry_residual_lineage_inspection())

    if parts == ["cognition", "cross-inquiry-evidence-lineage"]:
        from cross_inquiry_evidence_lineage import build_cross_inquiry_evidence_lineage_inspection
        return 200, _ok(build_cross_inquiry_evidence_lineage_inspection())

    if parts == ["cognition", "knowledge-confidence-checkpoint"]:
        from knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
        return 200, _ok(build_knowledge_confidence_checkpoint())

    if parts == ["cognition", "knowledge-reconsideration"]:
        from knowledge_reconsideration_scheduling import build_reconsideration_scheduling_inspection
        return 200, _ok(build_reconsideration_scheduling_inspection())

    if parts == ["cognition", "evidence-change-propagation"]:
        from evidence_change_propagation import build_evidence_change_propagation_inspection
        return 200, _ok(build_evidence_change_propagation_inspection())

    if parts == ["cognition", "reconsideration-conversation"]:
        from reconsideration_conversation_continuity import build_reconsideration_conversation_inspection
        return 200, _ok(build_reconsideration_conversation_inspection())

    if parts == ["cognition", "reconsideration-reflections"]:
        from bounded_reconsideration_reflection import build_bounded_reconsideration_reflection_inspection
        return 200, _ok(build_bounded_reconsideration_reflection_inspection())

    if parts == ["cognition", "belief-maintenance-outcomes"]:
        from belief_maintenance_outcomes import build_belief_maintenance_outcomes_inspection
        return 200, _ok(build_belief_maintenance_outcomes_inspection())

    if parts == ["cognition", "knowledge-maintenance-consolidation"]:
        from knowledge_maintenance_consolidation import build_knowledge_maintenance_consolidation
        return 200, _ok(build_knowledge_maintenance_consolidation())

    if parts == ["cognition", "knowledge-maintenance-checkpoint"]:
        from knowledge_maintenance_checkpoint import build_knowledge_maintenance_checkpoint
        return 200, _ok(build_knowledge_maintenance_checkpoint())

    if parts == ["cognition", "attention-agenda"]:
        from autonomous_attention_agenda import build_autonomous_attention_agenda_inspection
        return 200, _ok(build_autonomous_attention_agenda_inspection())

    if parts == ["cognition", "attention-arbitration"]:
        from motivation_agenda_arbitration import build_motivation_agenda_arbitration_inspection
        return 200, _ok(build_motivation_agenda_arbitration_inspection())

    if parts == ["cognition", "attention-agenda-checkpoint"]:
        from agenda_continuity_checkpoint import build_agenda_continuity_checkpoint
        return 200, _ok(build_agenda_continuity_checkpoint())

    if parts == ["cognition", "agenda-guided-reflection"]:
        from agenda_guided_reflection import build_agenda_guided_reflection_inspection
        return 200, _ok(build_agenda_guided_reflection_inspection())

    if parts == ["cognition", "bounded-intentions"]:
        from bounded_intention_formation import build_bounded_intention_inspection
        return 200, _ok(build_bounded_intention_inspection())

    if parts == ["cognition", "attention-intention-checkpoint"]:
        from attention_intention_checkpoint import build_attention_intention_checkpoint
        return 200, _ok(build_attention_intention_checkpoint())

    if parts == ["cognition", "intention-lifecycle"]:
        from intention_reconsideration_decay import build_intention_lifecycle_inspection
        return 200, _ok(build_intention_lifecycle_inspection())

    if parts == ["cognition", "intention-conflicts"]:
        from intention_conflict_resolution import build_intention_conflict_inspection
        return 200, _ok(build_intention_conflict_inspection())

    if parts == ["cognition", "intention-lifecycle-review"]:
        from intention_lifecycle_review import build_intention_lifecycle_review
        return 200, _ok(build_intention_lifecycle_review())

    if parts == ["cognition", "autonomous-attention-intention-checkpoint"]:
        from autonomous_attention_intention_checkpoint import build_autonomous_attention_intention_checkpoint
        return 200, _ok(build_autonomous_attention_intention_checkpoint())

    if parts == ["cognition", "persistent-initiative"]:
        from persistent_initiative import build_persistent_initiative_inspection
        return 200, _ok(build_persistent_initiative_inspection())

    if parts == ["cognition", "initiative-arbitration"]:
        from initiative_arbitration import build_initiative_arbitration_inspection
        return 200, _ok(build_initiative_arbitration_inspection())

    if parts == ["cognition", "persistent-initiative-checkpoint"]:
        from persistent_initiative_checkpoint import build_persistent_initiative_checkpoint
        return 200, _ok(build_persistent_initiative_checkpoint())

    if parts == ["cognition", "initiative-conversation-proposal"]:
        from initiative_conversation_proposal import build_initiative_conversation_proposal_inspection
        return 200, _ok(build_initiative_conversation_proposal_inspection())

    if parts == ["cognition", "initiative-communication-restraint"]:
        from initiative_communication_restraint import build_initiative_communication_restraint_inspection
        return 200, _ok(build_initiative_communication_restraint_inspection())

    if parts == ["cognition", "initiative-communication-checkpoint"]:
        from initiative_communication_checkpoint import build_initiative_communication_checkpoint
        return 200, _ok(build_initiative_communication_checkpoint())

    if parts == ["cognition", "surfaced-initiative-reconciliation"]:
        from surfaced_initiative_reconciliation import build_surfaced_initiative_reconciliation_inspection
        return 200, _ok(build_surfaced_initiative_reconciliation_inspection())

    if parts == ["cognition", "initiative-response-reconciliation"]:
        from initiative_response_reconciliation import build_initiative_response_reconciliation_inspection
        return 200, _ok(build_initiative_response_reconciliation_inspection())

    if parts == ["cognition", "initiative-lifecycle-checkpoint"]:
        from initiative_lifecycle_checkpoint import build_initiative_lifecycle_checkpoint
        return 200, _ok(build_initiative_lifecycle_checkpoint())

    if parts == ["cognition", "persistent-initiative-consolidation-checkpoint"]:
        from persistent_initiative_consolidation_checkpoint import build_persistent_initiative_consolidation_checkpoint
        return 200, _ok(build_persistent_initiative_consolidation_checkpoint())

    if parts == ["cognition", "long-horizon-objective"]:
        from long_horizon_objective import build_long_horizon_objective_inspection
        return 200, _ok(build_long_horizon_objective_inspection())

    if parts == ["cognition", "objective-review-arbitration"]:
        from objective_review_arbitration import build_objective_review_arbitration_inspection
        return 200, _ok(build_objective_review_arbitration_inspection())

    if parts == ["cognition", "long-horizon-objective-checkpoint"]:
        from long_horizon_objective_checkpoint import build_long_horizon_objective_checkpoint
        return 200, _ok(build_long_horizon_objective_checkpoint())

    if parts == ["cognition", "objective-milestones"]:
        from objective_milestone_decomposition import build_objective_milestone_inspection
        return 200, _ok(build_objective_milestone_inspection())

    if parts == ["cognition", "objective-progress-evidence"]:
        from objective_progress_evidence import build_objective_progress_inspection
        return 200, _ok(build_objective_progress_inspection())

    if parts == ["cognition", "objective-planning-progress-checkpoint"]:
        from objective_planning_progress_checkpoint import build_objective_planning_progress_checkpoint
        return 200, _ok(build_objective_planning_progress_checkpoint())

    if parts == ["cognition", "objective-conflict-reconciliation"]:
        from objective_conflict_reconciliation import build_objective_conflict_inspection
        return 200, _ok(build_objective_conflict_inspection())

    if parts == ["cognition", "objective-completion-abandonment"]:
        from objective_completion_abandonment import build_objective_lifecycle_inspection
        return 200, _ok(build_objective_lifecycle_inspection())

    if parts == ["cognition", "long-horizon-objective-lifecycle-checkpoint"]:
        from long_horizon_objective_lifecycle_checkpoint import build_long_horizon_objective_lifecycle_checkpoint
        return 200, _ok(build_long_horizon_objective_lifecycle_checkpoint())

    if parts == ["cognition", "long-horizon-follow-through-checkpoint"]:
        from long_horizon_follow_through_checkpoint import build_long_horizon_follow_through_checkpoint
        return 200, _ok(build_long_horizon_follow_through_checkpoint())

    if parts == ["cognition", "endogenous-curiosity"]:
        from endogenous_curiosity import build_endogenous_curiosity_inspection
        return 200, _ok(build_endogenous_curiosity_inspection())

    if parts == ["cognition", "curiosity-arbitration"]:
        from curiosity_arbitration import build_curiosity_arbitration_inspection
        return 200, _ok(build_curiosity_arbitration_inspection())

    if parts == ["cognition", "curiosity-continuity-checkpoint"]:
        from curiosity_continuity_checkpoint import build_curiosity_continuity_checkpoint
        return 200, _ok(build_curiosity_continuity_checkpoint())

    if parts == ["cognition", "curiosity-questions"]:
        from curiosity_question_formulation import build_curiosity_question_inspection
        return 200, _ok(build_curiosity_question_inspection())

    if parts == ["cognition", "curiosity-quality"]:
        from curiosity_quality_arbitration import build_curiosity_quality_inspection
        return 200, _ok(build_curiosity_quality_inspection())

    if parts == ["cognition", "curiosity-quality-checkpoint"]:
        from curiosity_quality_checkpoint import build_curiosity_quality_checkpoint
        return 200, _ok(build_curiosity_quality_checkpoint())

    if parts == ["cognition", "curiosity-inquiry-promotion"]:
        from curiosity_inquiry_promotion import build_curiosity_inquiry_promotion_inspection
        return 200, _ok(build_curiosity_inquiry_promotion_inspection())

    if parts == ["cognition", "curiosity-question-lifecycle"]:
        from curiosity_question_lifecycle import build_curiosity_question_lifecycle_inspection
        return 200, _ok(build_curiosity_question_lifecycle_inspection())

    if parts == ["cognition", "curiosity-lifecycle-checkpoint"]:
        from curiosity_lifecycle_checkpoint import build_curiosity_lifecycle_checkpoint
        return 200, _ok(build_curiosity_lifecycle_checkpoint())

    if parts == ["cognition", "endogenous-curiosity-checkpoint"]:
        from endogenous_curiosity_checkpoint import build_endogenous_curiosity_checkpoint
        return 200, _ok(build_endogenous_curiosity_checkpoint())

    if parts == ["cognition", "behavioral-outcomes"]:
        from behavioral_outcome_evidence import build_behavioral_outcome_inspection
        return 200, _ok(build_behavioral_outcome_inspection())

    if parts == ["cognition", "behavioral-attributions"]:
        from behavioral_outcome_attribution import build_behavioral_attribution_inspection
        return 200, _ok(build_behavioral_attribution_inspection())

    if parts == ["cognition", "behavioral-evidence-checkpoint"]:
        from behavioral_evidence_continuity_checkpoint import build_behavioral_evidence_continuity_checkpoint
        return 200, _ok(build_behavioral_evidence_continuity_checkpoint())

    if parts == ["cognition", "behavioral-patterns"]:
        from behavioral_pattern_detection import build_behavioral_pattern_inspection
        return 200, _ok(build_behavioral_pattern_inspection())

    if parts == ["cognition", "behavioral-self-evaluation"]:
        from behavioral_self_evaluation import build_behavioral_self_evaluation_inspection
        return 200, _ok(build_behavioral_self_evaluation_inspection())

    if parts == ["cognition", "behavioral-self-evaluation-checkpoint"]:
        from behavioral_self_evaluation_checkpoint import build_behavioral_self_evaluation_checkpoint
        return 200, _ok(build_behavioral_self_evaluation_checkpoint())

    if parts == ["cognition", "behavioral-adaptation-proposals"]:
        from behavioral_adaptation_proposals import build_behavioral_adaptation_proposal_inspection
        return 200, _ok(build_behavioral_adaptation_proposal_inspection())

    if parts == ["cognition", "behavioral-adaptation-lifecycle"]:
        from behavioral_adaptation_lifecycle import build_behavioral_adaptation_lifecycle_inspection
        return 200, _ok(build_behavioral_adaptation_lifecycle_inspection())

    if parts == ["cognition", "behavioral-adaptation-checkpoint"]:
        from behavioral_adaptation_checkpoint import build_behavioral_adaptation_checkpoint
        return 200, _ok(build_behavioral_adaptation_checkpoint())

    if parts == ["cognition", "reflective-behavioral-learning-checkpoint"]:
        from reflective_behavioral_learning_checkpoint import build_reflective_behavioral_learning_checkpoint
        return 200, _ok(build_reflective_behavioral_learning_checkpoint())

    if parts == ["cognition", "active-inquiries"]:
        from active_inquiry_records import build_active_inquiry_inspection
        return 200, _ok(build_active_inquiry_inspection())

    if parts == ["cognition", "inquiry-activation"]:
        from inquiry_activation_arbitration import build_inquiry_activation_arbitration_inspection
        return 200, _ok(build_inquiry_activation_arbitration_inspection())

    if parts == ["cognition", "active-inquiry-checkpoint"]:
        from active_inquiry_continuity_checkpoint import build_active_inquiry_continuity_checkpoint
        return 200, _ok(build_active_inquiry_continuity_checkpoint())
    if parts == ["cognition", "inquiry-evidence-governance-checkpoint"]:
        from inquiry_evidence_governance_checkpoint import build_inquiry_evidence_governance_checkpoint
        return 200, _ok(build_inquiry_evidence_governance_checkpoint())
    if parts == ["cognition", "inquiry-resolution-checkpoint"]:
        from inquiry_resolution_checkpoint import build_inquiry_resolution_checkpoint
        return 200, _ok(build_inquiry_resolution_checkpoint())
    if parts == ["cognition", "bounded-inquiry-checkpoint"]:
        from bounded_inquiry_checkpoint import build_bounded_inquiry_checkpoint
        return 200, _ok(build_bounded_inquiry_checkpoint())
    if parts == ["cognition", "deliberative-options"]:
        from deliberative_option_records import build_deliberative_option_inspection
        return 200, _ok(build_deliberative_option_inspection())
    if parts == ["cognition", "deliberative-option-arbitration"]:
        from deliberative_option_arbitration import build_deliberative_option_arbitration_inspection
        return 200, _ok(build_deliberative_option_arbitration_inspection())
    if parts == ["cognition", "deliberative-continuity-checkpoint"]:
        from deliberative_continuity_checkpoint import build_deliberative_continuity_checkpoint
        return 200, _ok(build_deliberative_continuity_checkpoint())
    if parts == ["cognition", "decision-commitment-checkpoint"]:
        from decision_commitment_checkpoint import build_decision_commitment_checkpoint
        return 200, _ok(build_decision_commitment_checkpoint())
    if parts == ["cognition", "deliberative-decision-review-checkpoint"]:
        from deliberative_decision_review_checkpoint import build_deliberative_decision_review_checkpoint
        return 200, _ok(build_deliberative_decision_review_checkpoint())
    if parts == ["cognition", "cognitive-load-continuity-checkpoint"]:
        from cognitive_load_continuity_checkpoint import build_cognitive_load_continuity_checkpoint
        return 200, _ok(build_cognitive_load_continuity_checkpoint())
    if parts == ["cognition", "cognitive-work-continuity-checkpoint"]:
        from cognitive_work_continuity_checkpoint import build_cognitive_work_continuity_checkpoint
        return 200, _ok(build_cognitive_work_continuity_checkpoint())
    if parts == ["cognition", "cognitive-coordination-review-checkpoint"]:
        from cognitive_coordination_review_checkpoint import build_cognitive_coordination_review_checkpoint
        return 200, _ok(build_cognitive_coordination_review_checkpoint())
    if parts == ["cognition", "cognitive-sustainability-review-checkpoint"]:
        from cognitive_sustainability_review_checkpoint import build_cognitive_sustainability_review_checkpoint
        return 200, _ok(build_cognitive_sustainability_review_checkpoint())
    if parts == ["cognition", "temporal-review-checkpoint"]:
        from temporal_review_checkpoint import build_temporal_review_checkpoint
        return 200, {"ok": True, "data": build_temporal_review_checkpoint()}

    if parts == ["cognition", "prospective-continuity-review-checkpoint"]:
        from prospective_continuity_review_checkpoint import build_prospective_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_prospective_continuity_review_checkpoint()}

    if parts == ["cognition", "motivational-continuity-intake-checkpoint"]:
        from motivational_continuity_intake_checkpoint import build_motivational_continuity_intake_checkpoint
        return 200, {"ok": True, "data": build_motivational_continuity_intake_checkpoint()}

    if parts == ["cognition", "motivational-drive-deliberation-checkpoint"]:
        from motivational_drive_deliberation_checkpoint import build_motivational_drive_deliberation_checkpoint
        return 200, {"ok": True, "data": build_motivational_drive_deliberation_checkpoint()}

    if parts == ["cognition", "motivational-continuity-review-checkpoint"]:
        from motivational_continuity_review_checkpoint import build_motivational_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_motivational_continuity_review_checkpoint()}

    if parts == ["cognition", "motivational-continuity-endogenous-drive-regulation-checkpoint"]:
        from motivational_continuity_endogenous_drive_regulation_checkpoint import build_motivational_continuity_endogenous_drive_regulation_checkpoint
        return 200, {"ok": True, "data": build_motivational_continuity_endogenous_drive_regulation_checkpoint()}

    if parts == ["cognition", "reflective-attention-salience-intake-checkpoint"]:
        from reflective_attention_salience_intake_checkpoint import build_reflective_attention_salience_intake_checkpoint
        return 200, {"ok": True, "data": build_reflective_attention_salience_intake_checkpoint()}

    if parts == ["cognition", "reflective-attention-continuity-review-checkpoint"]:
        from reflective_attention_continuity_review_checkpoint import build_reflective_attention_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_reflective_attention_continuity_review_checkpoint()}

    if parts == ["cognition", "selected-attention-focus-intake-checkpoint"]:
        from selected_attention_focus_intake_checkpoint import build_selected_attention_focus_intake_checkpoint
        return 200, {"ok": True, "data": build_selected_attention_focus_intake_checkpoint()}
    if parts == ["cognition", "reflective-focus-deliberation-checkpoint"]:
        from reflective_focus_deliberation_checkpoint import build_reflective_focus_deliberation_checkpoint
        return 200, {"ok": True, "data": build_reflective_focus_deliberation_checkpoint()}
    if parts == ["cognition", "reflective-focus-continuity-review-checkpoint"]:
        from reflective_focus_continuity_review_checkpoint import build_reflective_focus_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_reflective_focus_continuity_review_checkpoint()}
    if parts == ["cognition", "selected-attention-reflective-focus-governance-checkpoint"]:
        from selected_attention_reflective_focus_governance_checkpoint import build_selected_attention_reflective_focus_governance_checkpoint
        return 200, {"ok": True, "data": build_selected_attention_reflective_focus_governance_checkpoint()}
    if parts == ["cognition", "reflective-execution-continuity-checkpoint"]:
        from reflective_execution_continuity_checkpoint import build_reflective_execution_continuity_checkpoint
        return 200, {"ok": True, "data": build_reflective_execution_continuity_checkpoint()}

    if parts == ["cognition", "reflective-integration-reliability-checkpoint"]:
        from reflective_integration_reliability_checkpoint import build_reflective_integration_reliability_checkpoint
        return 200, {"ok": True, "data": build_reflective_integration_reliability_checkpoint()}

    if parts == ["cognition", "real-reflective-cognition-checkpoint"]:
        from real_reflective_cognition_checkpoint import build_real_reflective_cognition_checkpoint
        return 200, {"ok": True, "data": build_real_reflective_cognition_checkpoint()}
    if parts == ["cognition", "reflection-quality-intake-checkpoint"]:
        from reflection_quality_intake_checkpoint import build_reflection_quality_intake_checkpoint
        return 200, {"ok": True, "data": build_reflection_quality_intake_checkpoint()}
    if parts == ["cognition", "reflection-quality-deliberation-checkpoint"]:
        from reflection_quality_deliberation_checkpoint import build_reflection_quality_deliberation_checkpoint
        return 200, {"ok": True, "data": build_reflection_quality_deliberation_checkpoint()}
    if parts == ["cognition", "reflection-quality-integration-checkpoint"]:
        from reflection_quality_integration_checkpoint import build_reflection_quality_integration_checkpoint
        return 200, {"ok": True, "data": build_reflection_quality_integration_checkpoint()}
    if parts == ["cognition", "reflection-quality-governance-checkpoint"]:
        from reflection_quality_governance_checkpoint import build_reflection_quality_governance_checkpoint
        return 200, {"ok": True, "data": build_reflection_quality_governance_checkpoint()}
    if parts == ["cognition", "continuous-thought-governance-checkpoint"]:
        from continuous_thought_governance_checkpoint import build_continuous_thought_governance_checkpoint
        return 200, {"ok": True, "data": build_continuous_thought_governance_checkpoint()}

    if parts == ["cognition", "continuous-thought-integration-checkpoint"]:
        from continuous_thought_integration_checkpoint import build_continuous_thought_integration_checkpoint
        return 200, {"ok": True, "data": build_continuous_thought_integration_checkpoint()}

    if parts == ["cognition", "continuous-thought-deliberation-checkpoint"]:
        from continuous_thought_deliberation_checkpoint import build_continuous_thought_deliberation_checkpoint
        return 200, {"ok": True, "data": build_continuous_thought_deliberation_checkpoint()}

    if parts == ["cognition", "reflective-communication-integration-checkpoint"]:
        from reflective_communication_integration_checkpoint import build_reflective_communication_integration_checkpoint
        return 200, {"ok": True, "data": build_reflective_communication_integration_checkpoint()}
    if parts == ["cognition", "reflective-communication-governance-checkpoint"]:
        from reflective_communication_governance_checkpoint import build_reflective_communication_governance_checkpoint
        return 200, {"ok": True, "data": build_reflective_communication_governance_checkpoint()}

    if parts == ["cognition", "reflective-communication-deliberation-checkpoint"]:
        from reflective_communication_deliberation_checkpoint import build_reflective_communication_deliberation_checkpoint
        return 200, {"ok": True, "data": build_reflective_communication_deliberation_checkpoint()}

    if parts == ["cognition", "reflective-communication-intake-checkpoint"]:
        from reflective_communication_intake_checkpoint import build_reflective_communication_intake_checkpoint
        return 200, {"ok": True, "data": build_reflective_communication_intake_checkpoint()}

    if parts == ["cognition", "genuine-inquiry-deliberation-checkpoint"]:
        from genuine_inquiry_deliberation_checkpoint import build_genuine_inquiry_deliberation_checkpoint
        return 200, {"ok": True, "data": build_genuine_inquiry_deliberation_checkpoint()}

    if parts == ["cognition", "genuine-inquiry-integration-checkpoint"]:
        from genuine_inquiry_integration_checkpoint import build_genuine_inquiry_integration_checkpoint
        return 200, {"ok": True, "data": build_genuine_inquiry_integration_checkpoint()}

    if parts == ["cognition", "read-only-perception-governance-checkpoint"]:
        from read_only_perception_governance_checkpoint import build_read_only_perception_governance_checkpoint
        return 200, {"ok": True, "data": build_read_only_perception_governance_checkpoint()}

    if parts == ["cognition", "genuine-inquiry-governance-checkpoint"]:
        from genuine_inquiry_governance_checkpoint import build_genuine_inquiry_governance_checkpoint
        return 200, {"ok": True, "data": build_genuine_inquiry_governance_checkpoint()}

    if parts == ["cognition", "genuine-inquiry-intake-checkpoint"]:
        from genuine_inquiry_intake_checkpoint import build_genuine_inquiry_intake_checkpoint
        return 200, {"ok": True, "data": build_genuine_inquiry_intake_checkpoint()}

    if parts == ["cognition", "read-only-perception-intake-checkpoint"]:
        from read_only_perception_intake_checkpoint import build_read_only_perception_intake_checkpoint
        return 200, {"ok": True, "data": build_read_only_perception_intake_checkpoint()}
    if parts == ["cognition", "revisable-world-model-intake-checkpoint"]:
        from revisable_world_model_intake_checkpoint import build_revisable_world_model_intake_checkpoint
        return 200, {"ok": True, "data": build_revisable_world_model_intake_checkpoint()}
    if parts == ["cognition", "internally-generated-goal-intake-checkpoint"]:
        from internally_generated_goal_intake_checkpoint import build_internally_generated_goal_intake_checkpoint
        return 200, {"ok": True, "data": build_internally_generated_goal_intake_checkpoint()}
    if parts == ["cognition", "supervised-specification-intake-checkpoint"]:
        from supervised_specification_intake_checkpoint import build_supervised_specification_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_specification_intake_checkpoint()}
    if parts == ["cognition", "supervised-test-plan-intake-checkpoint"]:
        from supervised_test_plan_intake_checkpoint import build_supervised_test_plan_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_test_plan_intake_checkpoint()}
    if parts == ["cognition", "supervised-sandbox-change-intake-checkpoint"]:
        from supervised_sandbox_change_intake_checkpoint import build_supervised_sandbox_change_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_change_intake_checkpoint()}

    if parts == ["cognition", "supervised-isolated-sandbox-execution-intake-checkpoint"]:
        from supervised_isolated_sandbox_execution_intake_checkpoint import build_supervised_isolated_sandbox_execution_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_isolated_sandbox_execution_intake_checkpoint()}

    if parts == ["cognition", "supervised-isolated-sandbox-execution-deliberation-checkpoint"]:
        from supervised_isolated_sandbox_execution_deliberation_checkpoint import build_supervised_isolated_sandbox_execution_deliberation_checkpoint
        return 200, {"ok": True, "data": build_supervised_isolated_sandbox_execution_deliberation_checkpoint()}

    if parts == ["cognition", "supervised-isolated-sandbox-execution-integration-checkpoint"]:
        from supervised_isolated_sandbox_execution_integration_checkpoint import build_supervised_isolated_sandbox_execution_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_isolated_sandbox_execution_integration_checkpoint()}

    if parts == ["cognition", "supervised-isolated-sandbox-execution-governance-checkpoint"]:
        from supervised_isolated_sandbox_execution_governance_checkpoint import build_supervised_isolated_sandbox_execution_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_isolated_sandbox_execution_governance_checkpoint()}

    if parts == ["cognition", "operator-correction-acceptance-intake-checkpoint"]:
        from operator_correction_acceptance_intake_checkpoint import build_operator_correction_acceptance_intake_checkpoint
        return 200, {"ok": True, "data": build_operator_correction_acceptance_intake_checkpoint()}

    if parts == ["cognition", "operator-correction-reasoning-integration-checkpoint"]:
        from operator_correction_reasoning_integration_checkpoint import build_operator_correction_reasoning_integration_checkpoint
        return 200, {"ok": True, "data": build_operator_correction_reasoning_integration_checkpoint()}

    if parts == ["cognition", "operator-correction-reliability-visible-behavior-checkpoint"]:
        from operator_correction_reliability_visible_behavior_checkpoint import build_operator_correction_reliability_visible_behavior_checkpoint
        return 200, {"ok": True, "data": build_operator_correction_reliability_visible_behavior_checkpoint()}

    if parts == ["cognition", "operator-correction-acceptance-learning-governance-checkpoint"]:
        from operator_correction_acceptance_learning_governance_checkpoint import build_operator_correction_acceptance_learning_governance_checkpoint
        return 200, {"ok": True, "data": build_operator_correction_acceptance_learning_governance_checkpoint()}

    if parts == ["cognition", "workload-coordination-intake-checkpoint"]:
        from workload_coordination_intake_checkpoint import build_workload_coordination_intake_checkpoint
        return 200, {"ok": True, "data": build_workload_coordination_intake_checkpoint()}

    if parts == ["cognition", "workload-coordination-execution-checkpoint"]:
        from workload_coordination_execution_checkpoint import build_workload_coordination_execution_checkpoint
        return 200, {"ok": True, "data": build_workload_coordination_execution_checkpoint()}
    if parts == ["cognition", "workload-coordination-reliability-checkpoint"]:
        from workload_coordination_reliability_checkpoint import build_workload_coordination_reliability_checkpoint
        return 200, {"ok": True, "data": build_workload_coordination_reliability_checkpoint()}

    if parts == ["cognition", "workload-coordination-governance-checkpoint"]:
        from workload_coordination_governance_checkpoint import build_workload_coordination_governance_checkpoint
        return 200, {"ok": True, "data": build_workload_coordination_governance_checkpoint()}

    if parts == ["cognition", "multi-day-continuity-soak-intake-checkpoint"]:
        from multi_day_continuity_soak_intake_checkpoint import build_multi_day_continuity_soak_intake_checkpoint
        return 200, {"ok": True, "data": build_multi_day_continuity_soak_intake_checkpoint()}

    if parts == ["cognition", "multi-day-continuity-soak-execution-checkpoint"]:
        from multi_day_continuity_soak_execution_checkpoint import build_multi_day_continuity_soak_execution_checkpoint
        return 200, {"ok": True, "data": build_multi_day_continuity_soak_execution_checkpoint()}

    if parts == ["cognition", "multi-day-continuity-soak-reliability-checkpoint"]:
        from multi_day_continuity_soak_reliability_checkpoint import build_multi_day_continuity_soak_reliability_checkpoint
        return 200, {"ok": True, "data": build_multi_day_continuity_soak_reliability_checkpoint()}

    if parts == ["cognition", "multi-day-continuity-soak-governance-checkpoint"]:
        from multi_day_continuity_soak_governance_checkpoint import build_multi_day_continuity_soak_governance_checkpoint
        return 200, {"ok": True, "data": build_multi_day_continuity_soak_governance_checkpoint()}

    if parts == ["cognition", "conversation-cognition-unification-intake-checkpoint"]:
        from conversation_cognition_unification_intake_checkpoint import build_conversation_cognition_unification_intake_checkpoint
        return 200, {"ok": True, "data": build_conversation_cognition_unification_intake_checkpoint()}
    if parts == ["cognition", "conversation-cognition-unification-execution-checkpoint"]:
        from conversation_cognition_unification_execution_checkpoint import build_conversation_cognition_unification_execution_checkpoint
        return 200, {"ok": True, "data": build_conversation_cognition_unification_execution_checkpoint()}
    if parts == ["cognition", "conversation-cognition-unification-reliability-checkpoint"]:
        from conversation_cognition_unification_reliability_checkpoint import build_conversation_cognition_unification_reliability_checkpoint
        return 200, {"ok": True, "data": build_conversation_cognition_unification_reliability_checkpoint()}
    if parts == ["cognition", "conversation-cognition-unification-governance-checkpoint"]:
        from conversation_cognition_unification_governance_checkpoint import build_conversation_cognition_unification_governance_checkpoint
        return 200, {"ok": True, "data": build_conversation_cognition_unification_governance_checkpoint()}
    if parts == ["cognition", "understandable-cognitive-controls-intake-checkpoint"]:
        from understandable_cognitive_controls_intake_checkpoint import build_understandable_cognitive_controls_intake_checkpoint
        return 200, {"ok": True, "data": build_understandable_cognitive_controls_intake_checkpoint()}
    if parts == ["cognition", "understandable-cognitive-controls-execution-checkpoint"]:
        from understandable_cognitive_controls_execution_checkpoint import build_understandable_cognitive_controls_execution_checkpoint
        return 200, {"ok": True, "data": build_understandable_cognitive_controls_execution_checkpoint()}
    if parts == ["cognition", "understandable-cognitive-controls-reliability-checkpoint"]:
        from understandable_cognitive_controls_reliability_checkpoint import build_understandable_cognitive_controls_reliability_checkpoint
        return 200, {"ok": True, "data": build_understandable_cognitive_controls_reliability_checkpoint()}
    if parts == ["cognition", "understandable-cognitive-controls-governance-checkpoint"]:
        from understandable_cognitive_controls_governance_checkpoint import build_understandable_cognitive_controls_governance_checkpoint
        return 200, {"ok": True, "data": build_understandable_cognitive_controls_governance_checkpoint()}
    if parts == ["cognition", "architecture-consolidation-intake-checkpoint"]:
        from architecture_consolidation_intake_checkpoint import build_architecture_consolidation_intake_checkpoint
        return 200, {"ok": True, "data": build_architecture_consolidation_intake_checkpoint()}
    if parts == ["cognition", "architecture-consolidation-execution-checkpoint"]:
        from architecture_consolidation_execution_checkpoint import build_architecture_consolidation_execution_checkpoint
        return 200, {"ok": True, "data": build_architecture_consolidation_execution_checkpoint()}
    if parts == ["cognition", "architecture-consolidation-reliability-checkpoint"]:
        from architecture_consolidation_reliability_checkpoint import build_architecture_consolidation_reliability_checkpoint
        return 200, {"ok": True, "data": build_architecture_consolidation_reliability_checkpoint()}
    if parts == ["cognition", "architecture-consolidation-governance-checkpoint"]:
        from architecture_consolidation_governance_checkpoint import build_architecture_consolidation_governance_checkpoint
        return 200, {"ok": True, "data": build_architecture_consolidation_governance_checkpoint()}
    if parts == ["cognition", "privacy-security-hardening-intake-checkpoint"]:
        from privacy_security_hardening_intake_checkpoint import build_privacy_security_hardening_intake_checkpoint
        return 200, {"ok": True, "data": build_privacy_security_hardening_intake_checkpoint()}


    if parts == ["cognition", "privacy-security-hardening-execution-checkpoint"]:
        from privacy_security_hardening_execution_checkpoint import build_privacy_security_hardening_execution_checkpoint
        return 200, {"ok": True, "data": build_privacy_security_hardening_execution_checkpoint()}

    if parts == ["cognition", "privacy-security-hardening-reliability-checkpoint"]:
        from privacy_security_hardening_reliability_checkpoint import build_privacy_security_hardening_reliability_checkpoint
        return 200, {"ok": True, "data": build_privacy_security_hardening_reliability_checkpoint()}

    if parts == ["cognition", "privacy-security-hardening-governance-checkpoint"]:
        from privacy_security_hardening_governance_checkpoint import build_privacy_security_hardening_governance_checkpoint
        return 200, {"ok": True, "data": build_privacy_security_hardening_governance_checkpoint()}

    if parts == ["cognition", "cognitive-alpha-feature-freeze-intake-checkpoint"]:
        from cognitive_alpha_feature_freeze_intake_checkpoint import build_cognitive_alpha_feature_freeze_intake_checkpoint
        return 200, {"ok": True, "data": build_cognitive_alpha_feature_freeze_intake_checkpoint()}
    if parts == ["cognition", "cognitive-alpha-feature-freeze-execution-checkpoint"]:
        from cognitive_alpha_feature_freeze_execution_checkpoint import build_cognitive_alpha_feature_freeze_execution_checkpoint
        return 200, {"ok": True, "data": build_cognitive_alpha_feature_freeze_execution_checkpoint()}
    if parts == ["cognition", "cognitive-alpha-feature-freeze-reliability-checkpoint"]:
        from cognitive_alpha_feature_freeze_reliability_checkpoint import build_cognitive_alpha_feature_freeze_reliability_checkpoint
        return 200, {"ok": True, "data": build_cognitive_alpha_feature_freeze_reliability_checkpoint()}

    if parts == ["cognition", "cognitive-alpha-feature-freeze-governance-checkpoint"]:
        from cognitive_alpha_feature_freeze_governance_checkpoint import build_cognitive_alpha_feature_freeze_governance_checkpoint
        return 200, {"ok": True, "data": build_cognitive_alpha_feature_freeze_governance_checkpoint()}

    if parts == ["cognition", "reasoning-alpha-checkpoint"]:
        from reasoning_alpha_checkpoint import build_reasoning_alpha_checkpoint
        return 200, {"ok": True, "data": build_reasoning_alpha_checkpoint()}

    if parts == ["cognition", "reflection-alpha-checkpoint"]:
        from reflection_alpha_checkpoint import build_reflection_alpha_checkpoint
        return 200, {"ok": True, "data": build_reflection_alpha_checkpoint()}

    if parts == ["cognition", "belief-revision-alpha-checkpoint"]:
        from belief_revision_alpha_checkpoint import build_belief_revision_alpha_checkpoint
        return 200, {"ok": True, "data": build_belief_revision_alpha_checkpoint()}

    if parts == ["cognition", "multi-step-deliberation-alpha-checkpoint"]:
        from multi_step_deliberation_alpha_checkpoint import build_multi_step_deliberation_alpha_checkpoint
        return 200, {"ok": True, "data": build_multi_step_deliberation_alpha_checkpoint()}

    if parts == ["cognition", "decision-boundary-alpha-checkpoint"]:
        from decision_boundary_alpha_checkpoint import build_decision_boundary_alpha_checkpoint
        return 200, {"ok": True, "data": build_decision_boundary_alpha_checkpoint()}

    if parts == ["cognition", "reasoning-alpha-consolidation-checkpoint"]:
        from reasoning_alpha_consolidation_checkpoint import build_reasoning_alpha_consolidation_checkpoint
        return 200, {"ok": True, "data": build_reasoning_alpha_consolidation_checkpoint()}

    if parts == ["cognition", "conversation-intent-selection-checkpoint"]:
        from conversation_intent_selection_checkpoint import build_conversation_intent_selection_checkpoint
        return 200, {"ok": True, "data": build_conversation_intent_selection_checkpoint()}

    if parts == ["cognition", "contextual-conversation-behavior-checkpoint"]:
        from contextual_conversation_behavior_checkpoint import build_contextual_conversation_behavior_checkpoint
        return 200, {"ok": True, "data": build_contextual_conversation_behavior_checkpoint()}
    if parts == ["cognition", "follow-up-silence-checkpoint"]:
        from follow_up_silence_checkpoint import build_follow_up_silence_checkpoint
        return 200, {"ok": True, "data": build_follow_up_silence_checkpoint()}
    if parts == ["cognition", "cognitive-integration-alpha-checkpoint"]:
        from cognitive_integration_alpha_checkpoint import build_cognitive_integration_alpha_checkpoint
        return 200, {"ok": True, "data": build_cognitive_integration_alpha_checkpoint()}
    if parts == ["cognition", "conversation-policy-checkpoint"]:
        from conversation_policy_checkpoint import build_conversation_policy_checkpoint
        return 200, {"ok": True, "data": build_conversation_policy_checkpoint()}
    if parts == ["cognition", "natural-conversation-continuity-checkpoint"]:
        from natural_conversation_continuity_checkpoint import build_natural_conversation_continuity_checkpoint
        return 200, {"ok": True, "data": build_natural_conversation_continuity_checkpoint()}
    if parts == ["cognition", "natural-follow-up-checkpoint"]:
        from natural_follow_up_checkpoint import build_natural_follow_up_checkpoint
        return 200, {"ok": True, "data": build_natural_follow_up_checkpoint()}
    if parts == ["cognition", "governed-speech-checkpoint"]:
        from governed_speech_checkpoint import build_governed_speech_checkpoint
        return 200, {"ok": True, "data": build_governed_speech_checkpoint()}
    if parts == ["cognition", "daily-companion-cognition-checkpoint"]:
        from daily_companion_cognition_checkpoint import build_daily_companion_cognition_checkpoint
        return 200, {"ok": True, "data": build_daily_companion_cognition_checkpoint()}

    if parts == ["cognition", "unified-memory-checkpoint"]:
        from unified_memory_checkpoint import build_unified_memory_checkpoint
        return 200, {"ok": True, "data": build_unified_memory_checkpoint()}

    if parts == ["cognition", "memory-retrieval-relevance-checkpoint"]:
        from memory_retrieval_relevance_checkpoint import build_memory_retrieval_relevance_checkpoint
        return 200, {"ok": True, "data": build_memory_retrieval_relevance_checkpoint()}

    if parts == ["cognition", "immediate-memory-learning-checkpoint"]:
        from immediate_memory_learning_checkpoint import build_immediate_memory_learning_checkpoint
        return 200, {"ok": True, "data": build_immediate_memory_learning_checkpoint()}

    if parts == ["cognition", "bounded-experiential-lessons-checkpoint"]:
        from bounded_experiential_lessons_checkpoint import build_bounded_experiential_lessons_checkpoint
        return 200, {"ok": True, "data": build_bounded_experiential_lessons_checkpoint()}

    if parts == ["cognition", "memory-experiential-learning-alpha-checkpoint"]:
        from memory_experiential_learning_alpha_checkpoint import build_memory_experiential_learning_alpha_checkpoint
        return 200, {"ok": True, "data": build_memory_experiential_learning_alpha_checkpoint()}

    if parts == ["cognition", "internally-generated-goal-candidate-checkpoint"]:
        from internally_generated_goal_candidate_checkpoint import build_internally_generated_goal_candidate_checkpoint
        return 200, {"ok": True, "data": build_internally_generated_goal_candidate_checkpoint()}

    if parts == ["cognition", "hierarchical-planning-checkpoint"]:
        from hierarchical_planning_checkpoint import build_hierarchical_planning_checkpoint
        return 200, {"ok": True, "data": build_hierarchical_planning_checkpoint()}

    if parts == ["cognition", "plan-simulation-checkpoint"]:
        from plan_simulation_checkpoint import build_plan_simulation_checkpoint
        return 200, {"ok": True, "data": build_plan_simulation_checkpoint()}

    if parts == ["cognition", "persistent-follow-through-checkpoint"]:
        from persistent_follow_through_checkpoint import build_persistent_follow_through_checkpoint
        return 200, {"ok": True, "data": build_persistent_follow_through_checkpoint()}

    if parts == ["cognition", "goal-and-planning-alpha-checkpoint"]:
        from goal_and_planning_alpha_checkpoint import build_goal_and_planning_alpha_checkpoint
        return 200, {"ok": True, "data": build_goal_and_planning_alpha_checkpoint()}
    if parts == ["cognition", "natural-language-action-execution-checkpoint"]:
        from natural_language_action_execution_checkpoint import build_natural_language_action_execution_checkpoint
        return 200, {"ok": True, "data": build_natural_language_action_execution_checkpoint()}

    if parts == ["cognition", "clarification-argument-routing-checkpoint"]:
        from clarification_argument_routing_checkpoint import build_clarification_argument_routing_checkpoint
        return 200, {"ok": True, "data": build_clarification_argument_routing_checkpoint()}

    if parts == ["cognition", "natural-language-action-approval-governance-checkpoint"]:
        from natural_language_action_approval_governance_checkpoint import build_natural_language_action_approval_governance_checkpoint
        return 200, {"ok": True, "data": build_natural_language_action_approval_governance_checkpoint()}

    if parts == ["cognition", "natural-language-action-authoritative-result-checkpoint"]:
        from natural_language_action_authoritative_result_checkpoint import build_natural_language_action_authoritative_result_checkpoint
        return 200, {"ok": True, "data": build_natural_language_action_authoritative_result_checkpoint()}

    if parts == ["cognition", "natural-language-action-checkpoint"]:
        from natural_language_action_checkpoint import build_natural_language_action_checkpoint
        return 200, {"ok": True, "data": build_natural_language_action_checkpoint()}

    if parts == ["cognition", "supervised-project-inspection-planning-checkpoint"]:
        from supervised_project_inspection_planning_checkpoint import build_supervised_project_inspection_planning_checkpoint
        return 200, {"ok": True, "data": build_supervised_project_inspection_planning_checkpoint()}

    if parts == ["cognition", "supervised-implementation-checkpoint"]:
        from supervised_implementation_checkpoint import build_supervised_implementation_checkpoint
        return 200, {"ok": True, "data": build_supervised_implementation_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-testing-repair-checkpoint"]:
        from supervised_sandbox_testing_repair_checkpoint import build_supervised_sandbox_testing_repair_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_testing_repair_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-repair-draft-checkpoint"]:
        from supervised_sandbox_repair_draft_checkpoint import build_supervised_sandbox_repair_draft_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_repair_draft_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-repair-materialization-checkpoint"]:
        from supervised_sandbox_repair_materialization_checkpoint import build_supervised_sandbox_repair_materialization_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_repair_materialization_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-retesting-checkpoint"]:
        from supervised_sandbox_retesting_checkpoint import build_supervised_sandbox_retesting_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_retesting_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-repair-retest-checkpoint"]:
        from supervised_sandbox_repair_retest_checkpoint import build_supervised_sandbox_repair_retest_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_repair_retest_checkpoint()}
    if parts == ["cognition", "supervised-project-development-foundations-checkpoint"]:
        from supervised_project_development_foundations_checkpoint import build_supervised_project_development_foundations_checkpoint
        return 200, {"ok": True, "data": build_supervised_project_development_foundations_checkpoint()}
    if parts == ["cognition", "supervised-project-outcome-learning-checkpoint"]:
        from supervised_project_outcome_learning_checkpoint import build_supervised_project_outcome_learning_checkpoint
        return 200, {"ok": True, "data": build_supervised_project_outcome_learning_checkpoint()}
    if parts == ["cognition", "supervised-project-reliability-recovery-checkpoint"]:
        from supervised_project_reliability_recovery_checkpoint import build_supervised_project_reliability_recovery_checkpoint
        return 200, {"ok": True, "data": build_supervised_project_reliability_recovery_checkpoint()}
    if parts == ["cognition", "supervised-project-development-alpha-checkpoint"]:
        from supervised_project_development_alpha_checkpoint import build_supervised_project_development_alpha_checkpoint
        return 200, {"ok": True, "data": build_supervised_project_development_alpha_checkpoint()}
    if parts == ["cognition", "persistent-development-campaign-foundations-checkpoint"]:
        from persistent_development_campaign_foundations_checkpoint import build_persistent_development_campaign_foundations_checkpoint
        return 200, {"ok": True, "data": build_persistent_development_campaign_foundations_checkpoint()}
    if parts == ["cognition", "persistent-development-campaign-continuation-checkpoint"]:
        from persistent_development_campaign_continuation_checkpoint import build_persistent_development_campaign_continuation_checkpoint
        return 200, {"ok": True, "data": build_persistent_development_campaign_continuation_checkpoint()}
    if parts == ["cognition", "persistent-development-campaign-reliability-checkpoint"]:
        from persistent_development_campaign_reliability_checkpoint import build_persistent_development_campaign_reliability_checkpoint
        return 200, {"ok": True, "data": build_persistent_development_campaign_reliability_checkpoint()}
    if parts == ["cognition", "persistent-supervised-developer-alpha-checkpoint"]:
        from persistent_supervised_developer_alpha_checkpoint import build_persistent_supervised_developer_alpha_checkpoint
        return 200, {"ok": True, "data": build_persistent_supervised_developer_alpha_checkpoint()}
    if parts == ["cognition", "persistent-campaign-storage-checkpoint"]:
        from persistent_campaign_storage_checkpoint import build_persistent_campaign_storage_checkpoint
        return 200, {"ok": True, "data": build_persistent_campaign_storage_checkpoint()}
    if parts == ["cognition", "persistent-campaign-resume-reconciliation-checkpoint"]:
        from persistent_campaign_resume_reconciliation_checkpoint import build_persistent_campaign_resume_reconciliation_checkpoint
        return 200, {"ok": True, "data": build_persistent_campaign_resume_reconciliation_checkpoint()}
    if parts == ["cognition", "persistent-campaign-resume-materialization-checkpoint"]:
        from persistent_campaign_resume_materialization_checkpoint import build_persistent_campaign_resume_materialization_checkpoint
        return 200, {"ok": True, "data": build_persistent_campaign_resume_materialization_checkpoint()}
    if parts == ["cognition", "durable-campaign-continuation-checkpoint"]:
        from durable_campaign_continuation_checkpoint import build_durable_campaign_continuation_checkpoint
        return 200, {"ok": True, "data": build_durable_campaign_continuation_checkpoint()}
    if parts == ["cognition", "bounded-campaign-work-execution-checkpoint"]:
        from bounded_campaign_work_execution_checkpoint import build_bounded_campaign_work_execution_checkpoint
        return 200, {"ok": True, "data": build_bounded_campaign_work_execution_checkpoint()}
    if parts == ["cognition", "campaign-work-result-ledger-checkpoint"]:
        from campaign_work_result_ledger_checkpoint import build_campaign_work_result_ledger_checkpoint
        return 200, {"ok": True, "data": build_campaign_work_result_ledger_checkpoint()}
    if parts == ["cognition", "governed-campaign-work-continuation-checkpoint"]:
        from governed_campaign_work_continuation_checkpoint import build_governed_campaign_work_continuation_checkpoint
        return 200, {"ok": True, "data": build_governed_campaign_work_continuation_checkpoint()}
    if parts == ["cognition", "complete-campaign-development-loop-checkpoint"]:
        from complete_campaign_development_loop_checkpoint import build_complete_campaign_development_loop_checkpoint
        return 200, {"ok": True, "data": build_complete_campaign_development_loop_checkpoint()}
    if parts == ["cognition", "campaign-loop-execution-result-integration-checkpoint"]:
        from campaign_loop_execution_result_integration_checkpoint import build_campaign_loop_execution_result_integration_checkpoint
        return 200, {"ok": True, "data": build_campaign_loop_execution_result_integration_checkpoint()}
    if parts == ["cognition", "campaign-loop-reliability-recovery-learning-checkpoint"]:
        from campaign_loop_reliability_recovery_learning_checkpoint import build_campaign_loop_reliability_recovery_learning_checkpoint
        return 200, {"ok": True, "data": build_campaign_loop_reliability_recovery_learning_checkpoint()}
    if parts == ["cognition", "persistent-supervised-developer-hardening-checkpoint"]:
        from persistent_supervised_developer_hardening_checkpoint import build_persistent_supervised_developer_hardening_checkpoint
        return 200, {"ok": True, "data": build_persistent_supervised_developer_hardening_checkpoint()}
    if parts == ["cognition", "adversarial-campaign-hardening-long-session-checkpoint"]:
        from adversarial_campaign_hardening_long_session_checkpoint import build_adversarial_campaign_hardening_long_session_checkpoint
        return 200, {"ok": True, "data": build_adversarial_campaign_hardening_long_session_checkpoint()}
    if parts == ["cognition", "persistent-developer-adversarial-reliability-checkpoint"]:
        from persistent_developer_adversarial_reliability_checkpoint import build_persistent_developer_adversarial_reliability_checkpoint
        return 200, {"ok": True, "data": build_persistent_developer_adversarial_reliability_checkpoint()}
    if parts == ["cognition", "persistent-supervised-developer-alpha-hardening-checkpoint"]:
        from persistent_supervised_developer_alpha_hardening_checkpoint import build_persistent_supervised_developer_alpha_hardening_checkpoint
        return 200, {"ok": True, "data": build_persistent_supervised_developer_alpha_hardening_checkpoint()}
    if parts == ["cognition", "responsive-work-queue-checkpoint"]:
        from responsive_work_queue_checkpoint import build_responsive_work_queue_checkpoint
        return 200, {"ok": True, "data": build_responsive_work_queue_checkpoint()}
    if parts == ["cognition", "responsive-work-queue-review-checkpoint"]:
        from responsive_work_queue_review_checkpoint import build_responsive_work_queue_review_checkpoint
        return 200, {"ok": True, "data": build_responsive_work_queue_review_checkpoint()}
    if parts == ["cognition", "responsive-work-queue-reliability-checkpoint"]:
        from responsive_work_queue_reliability_checkpoint import build_responsive_work_queue_reliability_checkpoint
        return 200, {"ok": True, "data": build_responsive_work_queue_reliability_checkpoint()}
    if parts == ["cognition", "responsiveness-background-work-checkpoint"]:
        from responsiveness_background_work_checkpoint import build_responsiveness_background_work_checkpoint
        return 200, {"ok": True, "data": build_responsiveness_background_work_checkpoint()}
    if parts == ["cognition", "bounded-evidence-compaction-checkpoint"]:
        from bounded_evidence_compaction_checkpoint import build_bounded_evidence_compaction_checkpoint
        return 200, {"ok": True, "data": build_bounded_evidence_compaction_checkpoint()}
    if parts == ["cognition", "evidence-compaction-review-checkpoint"]:
        from evidence_compaction_review_checkpoint import build_evidence_compaction_review_checkpoint
        return 200, {"ok": True, "data": build_evidence_compaction_review_checkpoint()}
    if parts == ["cognition", "evidence-compaction-reliability-checkpoint"]:
        from evidence_compaction_reliability_checkpoint import build_evidence_compaction_reliability_checkpoint
        return 200, {"ok": True, "data": build_evidence_compaction_reliability_checkpoint()}
    if parts == ["cognition", "evidence-compaction-checkpoint"]:
        from evidence_compaction_checkpoint import build_evidence_compaction_checkpoint
        return 200, {"ok": True, "data": build_evidence_compaction_checkpoint()}
    if parts == ["cognition", "verifier-ownership-checkpoint"]:
        from verifier_ownership_checkpoint import build_verifier_ownership_checkpoint
        return 200, {"ok": True, "data": build_verifier_ownership_checkpoint()}
    if parts == ["cognition", "verifier-profile-reconciliation-checkpoint"]:
        from verifier_profile_reconciliation_checkpoint import build_verifier_profile_reconciliation_checkpoint
        return 200, {"ok": True, "data": build_verifier_profile_reconciliation_checkpoint()}
    if parts == ["cognition", "fixture-historical-debt-consolidation-checkpoint"]:
        from fixture_historical_debt_consolidation_checkpoint import build_fixture_historical_debt_consolidation_checkpoint
        return 200, {"ok": True, "data": build_fixture_historical_debt_consolidation_checkpoint()}
    if parts == ["cognition", "verifier-historical-debt-checkpoint"]:
        from verifier_historical_debt_checkpoint import build_verifier_historical_debt_checkpoint
        return 200, {"ok": True, "data": build_verifier_historical_debt_checkpoint()}
    if parts == ["cognition", "unified-cognitive-developer-experience-checkpoint"]:
        from unified_cognitive_developer_experience_checkpoint import build_unified_cognitive_developer_experience_checkpoint
        return 200, {"ok": True, "data": build_unified_cognitive_developer_experience_checkpoint()}
    if parts == ["cognition", "unified-cognitive-developer-coordination-checkpoint"]:
        from unified_cognitive_developer_coordination_checkpoint import build_unified_cognitive_developer_coordination_checkpoint
        return 200, {"ok": True, "data": build_unified_cognitive_developer_coordination_checkpoint()}
    if parts == ["cognition", "unified-cognitive-developer-reliability-checkpoint"]:
        from unified_cognitive_developer_reliability_checkpoint import build_unified_cognitive_developer_reliability_checkpoint
        return 200, {"ok": True, "data": build_unified_cognitive_developer_reliability_checkpoint()}
    if parts == ["cognition", "unified-cognitive-developer-checkpoint"]:
        from unified_cognitive_developer_checkpoint import build_unified_cognitive_developer_checkpoint
        return 200, {"ok": True, "data": build_unified_cognitive_developer_checkpoint()}
    if parts == ["cognition", "general-test-adapter-consolidation-checkpoint"]:
        from general_test_adapter_consolidation_checkpoint import build_general_test_adapter_consolidation_checkpoint
        return 200, {"ok": True, "data": build_general_test_adapter_consolidation_checkpoint()}
    if parts == ["cognition", "conversational-build-test-loop-checkpoint"]:
        from conversational_build_test_loop_checkpoint import build_conversational_build_test_loop_checkpoint
        return 200, {"ok": True, "data": build_conversational_build_test_loop_checkpoint()}
    if parts == ["cognition", "operator-build-test-results-checkpoint"]:
        from operator_build_test_results_checkpoint import build_operator_build_test_results_checkpoint
        return 200, {"ok": True, "data": build_operator_build_test_results_checkpoint()}
    if parts == ["cognition", "conversational-build-test-continuation-checkpoint"]:
        from conversational_build_test_continuation_checkpoint import build_conversational_build_test_continuation_checkpoint
        return 200, {"ok": True, "data": build_conversational_build_test_continuation_checkpoint()}
    if parts == ["cognition", "bounded-automatic-diagnosis-checkpoint"]:
        from bounded_automatic_diagnosis_checkpoint import build_bounded_automatic_diagnosis_checkpoint
        return 200, {"ok": True, "data": build_bounded_automatic_diagnosis_checkpoint()}
    if parts == ["cognition", "operator-diagnosis-review-checkpoint"]:
        from operator_diagnosis_review_checkpoint import build_operator_diagnosis_review_checkpoint
        return 200, {"ok": True, "data": build_operator_diagnosis_review_checkpoint()}
    if parts == ["cognition", "conversational-supervised-repair-execution-checkpoint"]:
        from conversational_supervised_repair_execution_checkpoint import build_conversational_supervised_repair_execution_checkpoint
        return 200, {"ok": True, "data": build_conversational_supervised_repair_execution_checkpoint()}
    if parts == ["cognition", "operator-repair-result-review-checkpoint"]:
        from operator_repair_result_review_checkpoint import build_operator_repair_result_review_checkpoint
        return 200, {"ok": True, "data": build_operator_repair_result_review_checkpoint()}
    if parts == ["cognition", "supervised-repaired-candidate-apply-checkpoint"]:
        from supervised_repaired_candidate_apply_checkpoint import build_supervised_repaired_candidate_apply_checkpoint
        return 200, {"ok": True, "data": build_supervised_repaired_candidate_apply_checkpoint()}
    if parts == ["cognition", "operator-repaired-candidate-apply-result-review-checkpoint"]:
        from operator_repaired_candidate_apply_result_review_checkpoint import build_operator_repaired_candidate_apply_result_review_checkpoint
        return 200, {"ok": True, "data": build_operator_repaired_candidate_apply_result_review_checkpoint()}
    if parts == ["cognition", "supervised-repaired-candidate-rollback-checkpoint"]:
        from supervised_repaired_candidate_rollback_checkpoint import build_supervised_repaired_candidate_rollback_checkpoint
        return 200, {"ok": True, "data": build_supervised_repaired_candidate_rollback_checkpoint()}
    if parts == ["cognition", "operator-repaired-candidate-rollback-result-review-checkpoint"]:
        from operator_repaired_candidate_rollback_result_review_checkpoint import build_operator_repaired_candidate_rollback_result_review_checkpoint
        return 200, {"ok": True, "data": build_operator_repaired_candidate_rollback_result_review_checkpoint()}
    if parts == ["cognition", "unified-supervised-development-transaction-history-checkpoint"]:
        from unified_supervised_development_transaction_history_checkpoint import build_unified_supervised_development_transaction_history_checkpoint
        return 200, {"ok": True, "data": build_unified_supervised_development_transaction_history_checkpoint()}
    if parts == ["cognition", "transaction-resumption-abandoned-work-reconciliation-checkpoint"]:
        from transaction_resumption_abandoned_work_reconciliation_checkpoint import build_transaction_resumption_abandoned_work_reconciliation_checkpoint
        return 200, {"ok": True, "data": build_transaction_resumption_abandoned_work_reconciliation_checkpoint()}
    if parts == ["cognition", "unified-development-work-queue-checkpoint"]:
        from unified_development_work_queue_checkpoint import build_unified_development_work_queue_checkpoint
        return 200, {"ok": True, "data": build_unified_development_work_queue_checkpoint()}
    if parts == ["cognition", "operator-governed-work-prioritization-scheduling-checkpoint"]:
        from operator_governed_work_prioritization_scheduling_checkpoint import build_operator_governed_work_prioritization_scheduling_checkpoint
        return 200, {"ok": True, "data": build_operator_governed_work_prioritization_scheduling_checkpoint()}
    if parts == ["cognition", "supervised-work-dispatch-execution-session-preparation-checkpoint"]:
        from supervised_work_dispatch_execution_session_preparation_checkpoint import build_supervised_work_dispatch_execution_session_preparation_checkpoint
        return 200, {"ok": True, "data": build_supervised_work_dispatch_execution_session_preparation_checkpoint()}
    if parts == ["cognition", "execution-session-authorization-bounded-launch-checkpoint"]:
        from execution_session_authorization_bounded_launch_checkpoint import build_execution_session_authorization_bounded_launch_checkpoint
        return 200, {"ok": True, "data": build_execution_session_authorization_bounded_launch_checkpoint()}
    if parts == ["cognition", "live-execution-monitoring-operator-intervention-checkpoint"]:
        from live_execution_monitoring_operator_intervention_checkpoint import build_live_execution_monitoring_operator_intervention_checkpoint
        return 200, {"ok": True, "data": build_live_execution_monitoring_operator_intervention_checkpoint()}
    if parts == ["cognition", "execution-session-pause-resume-cancel-recovery-checkpoint"]:
        from execution_session_pause_resume_cancel_recovery_checkpoint import build_execution_session_pause_resume_cancel_recovery_checkpoint
        return 200, {"ok": True, "data": build_execution_session_pause_resume_cancel_recovery_checkpoint()}
    if parts == ["cognition", "execution-outcome-reflection-learning-integration-checkpoint"]:
        from execution_outcome_reflection_learning_integration_checkpoint import build_execution_outcome_reflection_learning_integration_checkpoint
        return 200, {"ok": True, "data": build_execution_outcome_reflection_learning_integration_checkpoint()}
    if parts == ["cognition", "dynamic-execution-plan-revisions"]:
        from dynamic_execution_plan_revision import public_dynamic_execution_plan_revisions
        return 200, {"ok": True, "data": public_dynamic_execution_plan_revisions()}
    if parts == ["cognition", "dynamic-execution-plan-revision-reviews"]:
        from dynamic_execution_plan_revision import public_dynamic_execution_plan_revision_reviews
        return 200, {"ok": True, "data": public_dynamic_execution_plan_revision_reviews()}
    if parts == ["cognition", "dynamic-execution-plan-revision-checkpoint"]:
        from dynamic_execution_plan_revision_checkpoint import build_dynamic_execution_plan_revision_checkpoint
        return 200, {"ok": True, "data": build_dynamic_execution_plan_revision_checkpoint()}
    if parts == ["cognition", "feature-freeze-registry"]:
        from feature_freeze_final_hardening import feature_freeze_registry
        return 200, {"ok": True, "data": feature_freeze_registry()}
    if parts == ["cognition", "feature-freeze-manifest"]:
        from feature_freeze_final_hardening import build_feature_freeze_manifest
        return 200, {"ok": True, "data": build_feature_freeze_manifest()}
    if parts == ["cognition", "feature-freeze-final-hardening-report"]:
        from feature_freeze_final_hardening import build_final_hardening_report
        return 200, {"ok": True, "data": build_final_hardening_report()}
    if parts == ["cognition", "feature-freeze-final-hardening-checkpoint"]:
        from feature_freeze_final_hardening_checkpoint import build_feature_freeze_final_hardening_checkpoint
        return 200, {"ok": True, "data": build_feature_freeze_final_hardening_checkpoint()}
    if parts == ["cognition", "integrated-mind-conversation-development-benchmark-registry"]:
        from integrated_mind_conversation_development_benchmark import benchmark_registry
        return 200, {"ok": True, "data": benchmark_registry()}
    if parts == ["cognition", "integrated-mind-conversation-development-benchmark"]:
        from integrated_mind_conversation_development_benchmark import build_integrated_mind_conversation_development_contract
        return 200, {"ok": True, "data": build_integrated_mind_conversation_development_contract()}
    if parts == ["cognition", "integrated-mind-conversation-development-benchmark-checkpoint"]:
        from integrated_mind_conversation_development_benchmark_checkpoint import build_integrated_mind_conversation_development_benchmark_checkpoint
        return 200, {"ok": True, "data": build_integrated_mind_conversation_development_benchmark_checkpoint()}
    if parts == ["cognition", "privacy-security-secret-management-registry"]:
        from privacy_security_secret_management_audit import privacy_security_secret_management_registry
        return 200, {"ok": True, "data": privacy_security_secret_management_registry()}
    if parts == ["cognition", "privacy-security-audits"]:
        from privacy_security_secret_management_audit import public_privacy_security_audits
        return 200, {"ok": True, "data": public_privacy_security_audits()}
    if parts == ["cognition", "privacy-security-audit-reviews"]:
        from privacy_security_secret_management_audit import public_privacy_security_audit_reviews
        return 200, {"ok": True, "data": public_privacy_security_audit_reviews()}
    if parts == ["cognition", "secret-management-remediation-proposals"]:
        from privacy_security_secret_management_audit import public_secret_management_remediation_proposals
        return 200, {"ok": True, "data": public_secret_management_remediation_proposals()}
    if parts == ["cognition", "secret-management-remediation-reviews"]:
        from privacy_security_secret_management_audit import public_secret_management_remediation_reviews
        return 200, {"ok": True, "data": public_secret_management_remediation_reviews()}
    if parts == ["cognition", "privacy-security-secret-management-audit-checkpoint"]:
        from privacy_security_secret_management_audit_checkpoint import build_privacy_security_secret_management_audit_checkpoint
        return 200, {"ok": True, "data": build_privacy_security_secret_management_audit_checkpoint()}
    if parts == ["cognition", "initiative-proposal-pacing-registry"]:
        from initiative_proposal_pacing import initiative_proposal_pacing_registry
        return 200, {"ok": True, "data": initiative_proposal_pacing_registry()}
    if parts == ["cognition", "initiative-proposal-candidates"]:
        from initiative_proposal_pacing import public_initiative_proposal_candidates
        return 200, {"ok": True, "data": public_initiative_proposal_candidates()}
    if parts == ["cognition", "initiative-pacing-decisions"]:
        from initiative_proposal_pacing import public_initiative_pacing_decisions
        return 200, {"ok": True, "data": public_initiative_pacing_decisions()}
    if parts == ["cognition", "initiative-pacing-reviews"]:
        from initiative_proposal_pacing import public_initiative_pacing_reviews
        return 200, {"ok": True, "data": public_initiative_pacing_reviews()}
    if parts == ["cognition", "initiative-proposal-pacing-checkpoint"]:
        from initiative_proposal_pacing_checkpoint import build_initiative_proposal_pacing_checkpoint
        return 200, {"ok": True, "data": build_initiative_proposal_pacing_checkpoint()}
    if parts == ["cognition", "cross-session-project-understanding-registry"]:
        from cross_session_project_understanding import cross_session_project_understanding_registry
        return 200, {"ok": True, "data": cross_session_project_understanding_registry()}
    if parts == ["cognition", "project-understanding-snapshots"]:
        from cross_session_project_understanding import public_project_understanding_snapshots
        return 200, {"ok": True, "data": public_project_understanding_snapshots()}
    if parts == ["cognition", "project-understanding-reconciliations"]:
        from cross_session_project_understanding import public_project_understanding_reconciliations
        return 200, {"ok": True, "data": public_project_understanding_reconciliations()}
    if parts == ["cognition", "project-understanding-reviews"]:
        from cross_session_project_understanding import public_project_understanding_reviews
        return 200, {"ok": True, "data": public_project_understanding_reviews()}
    if parts == ["cognition", "cross-session-project-understanding-checkpoint"]:
        from cross_session_project_understanding_checkpoint import build_cross_session_project_understanding_checkpoint
        return 200, {"ok": True, "data": build_cross_session_project_understanding_checkpoint()}
    if parts == ["cognition", "long-running-session-continuity-registry"]:
        from long_running_multi_day_session_continuity import long_running_session_continuity_registry
        return 200, {"ok": True, "data": long_running_session_continuity_registry()}
    if parts == ["cognition", "session-continuity-progress"]:
        from long_running_multi_day_session_continuity import public_session_continuity_progress
        return 200, {"ok": True, "data": public_session_continuity_progress()}
    if parts == ["cognition", "session-continuity-manifests"]:
        from long_running_multi_day_session_continuity import public_session_continuity_manifests
        return 200, {"ok": True, "data": public_session_continuity_manifests()}
    if parts == ["cognition", "session-continuity-assessments"]:
        from long_running_multi_day_session_continuity import public_session_continuity_assessments
        return 200, {"ok": True, "data": public_session_continuity_assessments()}
    if parts == ["cognition", "session-continuity-reviews"]:
        from long_running_multi_day_session_continuity import public_session_continuity_reviews
        return 200, {"ok": True, "data": public_session_continuity_reviews()}
    if parts == ["cognition", "long-running-multi-day-session-continuity-checkpoint"]:
        from long_running_multi_day_session_continuity_checkpoint import build_long_running_multi_day_session_continuity_checkpoint
        return 200, {"ok": True, "data": build_long_running_multi_day_session_continuity_checkpoint()}
    if parts == ["cognition", "provider-model-governance-registry"]:
        from provider_fallback_model_governance import provider_model_governance_registry
        return 200, {"ok": True, "data": provider_model_governance_registry()}
    if parts == ["cognition", "provider-model-registry-snapshots"]:
        from provider_fallback_model_governance import public_provider_model_registry_snapshots
        return 200, {"ok": True, "data": public_provider_model_registry_snapshots()}
    if parts == ["cognition", "provider-model-selection-proposals"]:
        from provider_fallback_model_governance import public_provider_model_selection_proposals
        return 200, {"ok": True, "data": public_provider_model_selection_proposals()}
    if parts == ["cognition", "provider-model-selection-reviews"]:
        from provider_fallback_model_governance import public_provider_model_selection_reviews
        return 200, {"ok": True, "data": public_provider_model_selection_reviews()}
    if parts == ["cognition", "provider-fallback-assessments"]:
        from provider_fallback_model_governance import public_provider_fallback_assessments
        return 200, {"ok": True, "data": public_provider_fallback_assessments()}
    if parts == ["cognition", "provider-fallback-reviews"]:
        from provider_fallback_model_governance import public_provider_fallback_reviews
        return 200, {"ok": True, "data": public_provider_fallback_reviews()}
    if parts == ["cognition", "provider-fallback-model-governance-checkpoint"]:
        from provider_fallback_model_governance_checkpoint import build_provider_fallback_model_governance_checkpoint
        return 200, {"ok": True, "data": build_provider_fallback_model_governance_checkpoint()}
    if parts == ["cognition", "installation-lifecycle-registry"]:
        from installation_upgrade_backup_rollback_integration import lifecycle_operation_registry
        return 200, {"ok": True, "data": lifecycle_operation_registry()}
    if parts == ["cognition", "installation-lifecycle-preflights"]:
        from installation_upgrade_backup_rollback_integration import public_installation_lifecycle_preflights
        return 200, {"ok": True, "data": public_installation_lifecycle_preflights()}
    if parts == ["cognition", "installation-lifecycle-proposals"]:
        from installation_upgrade_backup_rollback_integration import public_installation_lifecycle_proposals
        return 200, {"ok": True, "data": public_installation_lifecycle_proposals()}
    if parts == ["cognition", "installation-lifecycle-reviews"]:
        from installation_upgrade_backup_rollback_integration import public_installation_lifecycle_reviews
        return 200, {"ok": True, "data": public_installation_lifecycle_reviews()}
    if parts == ["cognition", "installation-lifecycle-recovery-assessments"]:
        from installation_upgrade_backup_rollback_integration import public_installation_lifecycle_recovery_assessments
        return 200, {"ok": True, "data": public_installation_lifecycle_recovery_assessments()}
    if parts == ["cognition", "installation-lifecycle-recovery-reviews"]:
        from installation_upgrade_backup_rollback_integration import public_installation_lifecycle_recovery_reviews
        return 200, {"ok": True, "data": public_installation_lifecycle_recovery_reviews()}
    if parts == ["cognition", "installation-lifecycle-integration-checkpoint"]:
        from installation_lifecycle_integration_checkpoint import build_installation_lifecycle_integration_checkpoint
        return 200, {"ok": True, "data": build_installation_lifecycle_integration_checkpoint()}
    if parts == ["cognition", "unified-operator-dashboard-registry"]:
        from unified_operator_dashboard import dashboard_panel_registry
        return 200, {"ok": True, "data": dashboard_panel_registry()}
    if parts == ["cognition", "unified-operator-dashboard-snapshot"]:
        from unified_operator_dashboard import build_unified_operator_dashboard_snapshot
        return 200, {"ok": True, "data": build_unified_operator_dashboard_snapshot()}
    if parts == ["cognition", "unified-operator-dashboard-checkpoint"]:
        from unified_operator_dashboard_checkpoint import build_unified_operator_dashboard_checkpoint
        return 200, {"ok": True, "data": build_unified_operator_dashboard_checkpoint()}
    if parts == ["cognition", "integrated-developer-beta-scenario-registry"]:
        from integrated_developer_beta import scenario_registry
        return 200, {"ok": True, "data": scenario_registry()}
    if parts == ["cognition", "integrated-developer-beta-benchmark"]:
        from integrated_developer_beta import build_integrated_developer_beta_contract
        return 200, {"ok": True, "data": build_integrated_developer_beta_contract()}
    if parts == ["cognition", "integrated-developer-beta-checkpoint"]:
        from integrated_developer_beta_checkpoint import build_integrated_developer_beta_checkpoint
        return 200, {"ok": True, "data": build_integrated_developer_beta_checkpoint()}
    if parts == ["cognition", "adversarial-boundary-attack-registry"]:
        from adversarial_execution_cognitive_boundary import attack_registry
        return 200, {"ok": True, "data": attack_registry()}
    if parts == ["cognition", "adversarial-boundary-assessments"]:
        from adversarial_execution_cognitive_boundary import public_adversarial_boundary_assessments
        return 200, {"ok": True, "data": public_adversarial_boundary_assessments()}
    if parts == ["cognition", "adversarial-boundary-reviews"]:
        from adversarial_execution_cognitive_boundary import public_adversarial_boundary_reviews
        return 200, {"ok": True, "data": public_adversarial_boundary_reviews()}
    if parts == ["cognition", "adversarial-execution-cognitive-boundary-checkpoint"]:
        from adversarial_execution_cognitive_boundary_checkpoint import build_adversarial_execution_cognitive_boundary_checkpoint
        return 200, {"ok": True, "data": build_adversarial_execution_cognitive_boundary_checkpoint()}
    if parts == ["cognition", "broader-project-language-adapter-registry"]:
        from broader_project_language_adapters import adapter_registry
        return 200, {"ok": True, "data": adapter_registry()}
    if parts == ["cognition", "broader-project-language-adapter-assessments"]:
        from broader_project_language_adapters import public_broader_project_adapter_assessments
        return 200, {"ok": True, "data": public_broader_project_adapter_assessments()}
    if parts == ["cognition", "broader-project-language-adapter-reviews"]:
        from broader_project_language_adapters import public_broader_project_adapter_reviews
        return 200, {"ok": True, "data": public_broader_project_adapter_reviews()}
    if parts == ["cognition", "broader-project-language-adapters-checkpoint"]:
        from broader_project_language_adapters_checkpoint import build_broader_project_language_adapters_checkpoint
        return 200, {"ok": True, "data": build_broader_project_language_adapters_checkpoint()}
    if parts == ["cognition", "multi-tool-orchestration-plans"]:
        from multi_tool_orchestration import public_multi_tool_orchestration_plans
        return 200, {"ok": True, "data": public_multi_tool_orchestration_plans()}
    if parts == ["cognition", "multi-tool-orchestration-reviews"]:
        from multi_tool_orchestration import public_multi_tool_orchestration_reviews
        return 200, {"ok": True, "data": public_multi_tool_orchestration_reviews()}
    if parts == ["cognition", "multi-tool-orchestration-results"]:
        from multi_tool_orchestration import public_multi_tool_orchestration_results
        return 200, {"ok": True, "data": public_multi_tool_orchestration_results()}
    if parts == ["cognition", "multi-tool-orchestration-handoffs"]:
        from multi_tool_orchestration import public_multi_tool_orchestration_handoffs
        return 200, {"ok": True, "data": public_multi_tool_orchestration_handoffs()}
    if parts == ["cognition", "multi-tool-orchestration-handoff-reviews"]:
        from multi_tool_orchestration import public_multi_tool_orchestration_handoff_reviews
        return 200, {"ok": True, "data": public_multi_tool_orchestration_handoff_reviews()}
    if parts == ["cognition", "multi-tool-orchestration-checkpoint"]:
        from multi_tool_orchestration_checkpoint import build_multi_tool_orchestration_checkpoint
        return 200, {"ok": True, "data": build_multi_tool_orchestration_checkpoint()}
    if parts == ["cognition", "goal-motivation-work-priority-integrations"]:
        from goal_motivation_work_priority_integration import public_goal_motivation_work_priority_integrations
        return 200, {"ok": True, "data": public_goal_motivation_work_priority_integrations()}
    if parts == ["cognition", "goal-motivation-work-priority-integration-reviews"]:
        from goal_motivation_work_priority_integration import public_goal_motivation_work_priority_integration_reviews
        return 200, {"ok": True, "data": public_goal_motivation_work_priority_integration_reviews()}
    if parts == ["cognition", "goal-motivation-work-priority-integration-checkpoint"]:
        from goal_motivation_work_priority_integration_checkpoint import build_goal_motivation_work_priority_integration_checkpoint
        return 200, {"ok": True, "data": build_goal_motivation_work_priority_integration_checkpoint()}
    if parts == ["cognition", "evidence-backed-development-lessons"]:
        from evidence_backed_development_outcome_lessons import public_evidence_backed_development_lessons
        return 200, {"ok": True, "data": public_evidence_backed_development_lessons()}
    if parts == ["cognition", "evidence-backed-development-lesson-reviews"]:
        from evidence_backed_development_outcome_lessons import public_evidence_backed_development_lesson_reviews
        return 200, {"ok": True, "data": public_evidence_backed_development_lesson_reviews()}
    if parts == ["cognition", "evidence-backed-development-lesson-reconsiderations"]:
        from evidence_backed_development_outcome_lessons import public_evidence_backed_development_lesson_reconsiderations
        return 200, {"ok": True, "data": public_evidence_backed_development_lesson_reconsiderations()}
    if parts == ["cognition", "evidence-backed-development-outcome-lessons-checkpoint"]:
        from evidence_backed_development_outcome_lessons_checkpoint import build_evidence_backed_development_outcome_lessons_checkpoint
        return 200, {"ok": True, "data": build_evidence_backed_development_outcome_lessons_checkpoint()}
    if parts == ["cognition", "requirement-quality-assessments"]:
        from requirement_quality_assessment import public_requirement_quality_assessments
        return 200, {"ok": True, "data": public_requirement_quality_assessments()}
    if parts == ["cognition", "requirement-quality-assessment-reviews"]:
        from requirement_quality_assessment import public_requirement_quality_assessment_reviews
        return 200, {"ok": True, "data": public_requirement_quality_assessment_reviews()}
    if parts == ["cognition", "requirement-quality-assessment-checkpoint"]:
        from requirement_quality_assessment_checkpoint import build_requirement_quality_assessment_checkpoint
        return 200, {"ok": True, "data": build_requirement_quality_assessment_checkpoint()}
    if parts == ["cognition", "resource-concurrency-governance-assessments"]:
        from resource_concurrency_governance import public_resource_concurrency_governance_assessments
        return 200, {"ok": True, "data": public_resource_concurrency_governance_assessments()}
    if parts == ["cognition", "resource-concurrency-governance-reviews"]:
        from resource_concurrency_governance import public_resource_concurrency_governance_reviews
        return 200, {"ok": True, "data": public_resource_concurrency_governance_reviews()}
    if parts == ["cognition", "resource-concurrency-governance-checkpoint"]:
        from resource_concurrency_governance_checkpoint import build_resource_concurrency_governance_checkpoint
        return 200, {"ok": True, "data": build_resource_concurrency_governance_checkpoint()}
    if parts == ["cognition", "dependency-aware-execution-assessments"]:
        from dependency_aware_execution import public_dependency_aware_execution_assessments
        return 200, {"ok": True, "data": public_dependency_aware_execution_assessments()}
    if parts == ["cognition", "dependency-aware-execution-reviews"]:
        from dependency_aware_execution import public_dependency_aware_execution_reviews
        return 200, {"ok": True, "data": public_dependency_aware_execution_reviews()}
    if parts == ["cognition", "dependency-aware-execution-checkpoint"]:
        from dependency_aware_execution_checkpoint import build_dependency_aware_execution_checkpoint
        return 200, {"ok": True, "data": build_dependency_aware_execution_checkpoint()}
    if parts == ["cognition", "mindful-execution-alpha-integration-benchmark-checkpoint"]:
        from mindful_execution_alpha_integration_benchmark_checkpoint import build_mindful_execution_alpha_integration_benchmark_checkpoint
        return 200, {"ok": True, "data": build_mindful_execution_alpha_integration_benchmark_checkpoint()}
    if parts == ["cognition", "long-session-multi-day-soak-checkpoint"]:
        from long_session_multi_day_soak_checkpoint import build_long_session_multi_day_soak_checkpoint
        return 200, {"ok": True, "data": build_long_session_multi_day_soak_checkpoint()}
    if parts == ["cognition", "operator-reviewed-soak-progression-checkpoint"]:
        from operator_reviewed_soak_progression_checkpoint import build_operator_reviewed_soak_progression_checkpoint
        return 200, {"ok": True, "data": build_operator_reviewed_soak_progression_checkpoint()}
    if parts == ["cognition", "soak-reliability-adversarial-checkpoint"]:
        from soak_reliability_adversarial_checkpoint import build_soak_reliability_adversarial_checkpoint
        return 200, {"ok": True, "data": build_soak_reliability_adversarial_checkpoint()}
    if parts == ["cognition", "adversarial-privacy-authority-checkpoint"]:
        from adversarial_privacy_authority_checkpoint import build_adversarial_privacy_authority_checkpoint
        return 200, {"ok": True, "data": build_adversarial_privacy_authority_checkpoint()}
    if parts == ["cognition", "adversarial-replay-recovery-review-checkpoint"]:
        from adversarial_replay_recovery_review_checkpoint import build_adversarial_replay_recovery_review_checkpoint
        return 200, {"ok": True, "data": build_adversarial_replay_recovery_review_checkpoint()}
    if parts == ["cognition", "adversarial-reliability-integration-checkpoint"]:
        from adversarial_reliability_integration_checkpoint import build_adversarial_reliability_integration_checkpoint
        return 200, {"ok": True, "data": build_adversarial_reliability_integration_checkpoint()}
    if parts == ["cognition", "adversarial-privacy-authority-replay-recovery-checkpoint"]:
        from adversarial_privacy_authority_replay_recovery_checkpoint import build_adversarial_privacy_authority_replay_recovery_checkpoint
        return 200, {"ok": True, "data": build_adversarial_privacy_authority_replay_recovery_checkpoint()}
    if parts == ["cognition", "runtime-lifecycle-migration-checkpoint"]:
        from runtime_lifecycle_migration_checkpoint import build_runtime_lifecycle_migration_checkpoint
        return 200, {"ok": True, "data": build_runtime_lifecycle_migration_checkpoint()}
    if parts == ["cognition", "runtime-lifecycle-application-review-checkpoint"]:
        from runtime_lifecycle_application_review_checkpoint import build_runtime_lifecycle_application_review_checkpoint
        return 200, {"ok": True, "data": build_runtime_lifecycle_application_review_checkpoint()}
    if parts == ["cognition", "runtime-lifecycle-reliability-adversarial-checkpoint"]:
        from runtime_lifecycle_reliability_adversarial_checkpoint import build_runtime_lifecycle_reliability_adversarial_checkpoint
        return 200, {"ok": True, "data": build_runtime_lifecycle_reliability_adversarial_checkpoint()}
    if parts == ["cognition", "runtime-lifecycle-checkpoint"]:
        from runtime_lifecycle_checkpoint import build_runtime_lifecycle_checkpoint
        return 200, {"ok": True, "data": build_runtime_lifecycle_checkpoint()}
    if parts == ["cognition", "feature-freeze-architecture-consolidation-checkpoint"]:
        from feature_freeze_architecture_consolidation_checkpoint import build_feature_freeze_architecture_consolidation_checkpoint
        return 200, {"ok": True, "data": build_feature_freeze_architecture_consolidation_checkpoint()}
    if parts == ["cognition", "performance-documentation-verifier-hardening-checkpoint"]:
        from performance_documentation_verifier_hardening_checkpoint import build_performance_documentation_verifier_hardening_checkpoint
        return 200, {"ok": True, "data": build_performance_documentation_verifier_hardening_checkpoint()}
    if parts == ["cognition", "feature-freeze-consolidation-review-checkpoint"]:
        from feature_freeze_consolidation_review_checkpoint import build_feature_freeze_consolidation_review_checkpoint
        return 200, {"ok": True, "data": build_feature_freeze_consolidation_review_checkpoint()}
    if parts == ["cognition", "feature-freeze-architecture-consolidated-checkpoint"]:
        from feature_freeze_architecture_consolidated_checkpoint import build_feature_freeze_architecture_consolidated_checkpoint
        return 200, {"ok": True, "data": build_feature_freeze_architecture_consolidated_checkpoint()}
    if parts == ["cognition", "final-source-candidate-preparation-checkpoint"]:
        from final_source_candidate_preparation_checkpoint import build_final_source_candidate_preparation_checkpoint
        return 200, {"ok": True, "data": build_final_source_candidate_preparation_checkpoint()}
    if parts == ["cognition", "final-candidate-review-checkpoint"]:
        from final_candidate_review_checkpoint import build_final_candidate_review_checkpoint
        return 200, {"ok": True, "data": build_final_candidate_review_checkpoint()}
    if parts == ["cognition", "final-candidate-reliability-checkpoint"]:
        from final_candidate_reliability_checkpoint import build_final_candidate_reliability_checkpoint
        return 200, {"ok": True, "data": build_final_candidate_reliability_checkpoint()}
    if parts == ["cognition", "final-source-candidate-checkpoint"]:
        from final_source_candidate_checkpoint import build_final_source_candidate_checkpoint
        return 200, {"ok": True, "data": build_final_source_candidate_checkpoint()}
    if parts == ["cognition", "long-session-multi-day-soak-consolidated-checkpoint"]:
        from long_session_multi_day_soak_consolidated_checkpoint import build_long_session_multi_day_soak_consolidated_checkpoint
        return 200, {"ok": True, "data": build_long_session_multi_day_soak_consolidated_checkpoint()}
    if parts == ["cognition", "unified-experience-foundations-checkpoint"]:
        from unified_experience_foundations_checkpoint import build_unified_experience_foundations_checkpoint
        return 200, {"ok": True, "data": build_unified_experience_foundations_checkpoint()}
    if parts == ["cognition", "unified-experience-navigation-checkpoint"]:
        from unified_experience_navigation_checkpoint import build_unified_experience_navigation_checkpoint
        return 200, {"ok": True, "data": build_unified_experience_navigation_checkpoint()}
    if parts == ["cognition", "unified-experience-reliability-checkpoint"]:
        from unified_experience_reliability_checkpoint import build_unified_experience_reliability_checkpoint
        return 200, {"ok": True, "data": build_unified_experience_reliability_checkpoint()}
    if parts == ["cognition", "unified-experience-checkpoint"]:
        from unified_experience_checkpoint import build_unified_experience_checkpoint
        return 200, {"ok": True, "data": build_unified_experience_checkpoint()}
    if parts == ["cognition", "complete-campaign-development-loop-alpha-checkpoint"]:
        from complete_campaign_development_loop_alpha_checkpoint import build_complete_campaign_development_loop_alpha_checkpoint
        return 200, {"ok": True, "data": build_complete_campaign_development_loop_alpha_checkpoint()}
    if parts == ["cognition", "persistent-campaign-work-execution-checkpoint"]:
        from persistent_campaign_work_execution_checkpoint import build_persistent_campaign_work_execution_checkpoint
        return 200, {"ok": True, "data": build_persistent_campaign_work_execution_checkpoint()}


    if parts == ["cognition", "supervised-sandbox-repair-implementation-governance-checkpoint"]:
        from supervised_sandbox_repair_implementation_governance_checkpoint import build_supervised_sandbox_repair_implementation_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_repair_implementation_governance_checkpoint()}

    if parts == ["cognition", "supervised-repair-implementation-intake-checkpoint"]:
        from supervised_repair_implementation_intake_checkpoint import build_supervised_repair_implementation_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_repair_implementation_intake_checkpoint()}

    if parts == ["cognition", "supervised-repair-execution-checkpoint"]:
        from supervised_repair_execution_checkpoint import build_supervised_repair_execution_checkpoint
        return 200, {"ok": True, "data": build_supervised_repair_execution_checkpoint()}

    if parts == ["cognition", "supervised-repair-execution-integration-checkpoint"]:
        from supervised_repair_execution_integration_checkpoint import build_supervised_repair_execution_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_repair_execution_integration_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-change-deliberation-checkpoint"]:
        from supervised_sandbox_change_deliberation_checkpoint import build_supervised_sandbox_change_deliberation_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_change_deliberation_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-change-integration-checkpoint"]:
        from supervised_sandbox_change_integration_checkpoint import build_supervised_sandbox_change_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_change_integration_checkpoint()}

    if parts == ["cognition", "supervised-sandbox-change-governance-checkpoint"]:
        from supervised_sandbox_change_governance_checkpoint import build_supervised_sandbox_change_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_sandbox_change_governance_checkpoint()}

    if parts == ["cognition", "supervised-test-plan-deliberation-checkpoint"]:
        from supervised_test_plan_deliberation_checkpoint import build_supervised_test_plan_deliberation_checkpoint
        return 200, {"ok": True, "data": build_supervised_test_plan_deliberation_checkpoint()}
    if parts == ["cognition", "supervised-test-plan-integration-checkpoint"]:
        from supervised_test_plan_integration_checkpoint import build_supervised_test_plan_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_test_plan_integration_checkpoint()}
    if parts == ["cognition", "supervised-test-planning-governance-checkpoint"]:
        from supervised_test_plan_governance_checkpoint import build_supervised_test_plan_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_test_plan_governance_checkpoint()}
    if parts == ["cognition", "supervised-specification-deliberation-checkpoint"]:
        from supervised_specification_deliberation_checkpoint import build_supervised_specification_deliberation_checkpoint
        return 200, {"ok": True, "data": build_supervised_specification_deliberation_checkpoint()}
    if parts == ["cognition", "supervised-specification-integration-checkpoint"]:
        from supervised_specification_integration_checkpoint import build_supervised_specification_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_specification_integration_checkpoint()}
    if parts == ["cognition", "supervised-specification-governance-checkpoint"]:
        from supervised_specification_governance_checkpoint import build_supervised_specification_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_specification_governance_checkpoint()}
    if parts == ["cognition", "supervised-development-proposal-intake-checkpoint"]:
        from supervised_development_proposal_intake_checkpoint import build_supervised_development_proposal_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_development_proposal_intake_checkpoint()}
    if parts == ["cognition", "supervised-development-proposal-deliberation-checkpoint"]:
        from supervised_development_proposal_deliberation_checkpoint import build_supervised_development_proposal_deliberation_checkpoint
        return 200, {"ok": True, "data": build_supervised_development_proposal_deliberation_checkpoint()}
    if parts == ["cognition", "supervised-development-proposal-integration-checkpoint"]:
        from supervised_development_proposal_integration_checkpoint import build_supervised_development_proposal_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_development_proposal_integration_checkpoint()}
    if parts == ["cognition", "supervised-development-proposal-governance-checkpoint"]:
        from supervised_development_proposal_governance_checkpoint import build_supervised_development_proposal_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_development_proposal_governance_checkpoint()}
    if parts == ["cognition", "supervised-deficiency-intake-checkpoint"]:
        from supervised_deficiency_intake_checkpoint import build_supervised_deficiency_intake_checkpoint
        return 200, {"ok": True, "data": build_supervised_deficiency_intake_checkpoint()}
    if parts == ["cognition", "supervised-deficiency-deliberation-checkpoint"]:
        from supervised_deficiency_deliberation_checkpoint import build_supervised_deficiency_deliberation_checkpoint
        return 200, {"ok": True, "data": build_supervised_deficiency_deliberation_checkpoint()}
    if parts == ["cognition", "supervised-deficiency-integration-checkpoint"]:
        from supervised_deficiency_integration_checkpoint import build_supervised_deficiency_integration_checkpoint
        return 200, {"ok": True, "data": build_supervised_deficiency_integration_checkpoint()}
    if parts == ["cognition", "supervised-deficiency-governance-checkpoint"]:
        from supervised_deficiency_governance_checkpoint import build_supervised_deficiency_governance_checkpoint
        return 200, {"ok": True, "data": build_supervised_deficiency_governance_checkpoint()}
    if parts == ["cognition", "prospective-planning-intake-checkpoint"]:
        from prospective_planning_intake_checkpoint import build_prospective_planning_intake_checkpoint
        return 200, {"ok": True, "data": build_prospective_planning_intake_checkpoint()}
    if parts == ["cognition", "prospective-planning-deliberation-checkpoint"]:
        from prospective_planning_deliberation_checkpoint import build_prospective_planning_deliberation_checkpoint
        return 200, {"ok": True, "data": build_prospective_planning_deliberation_checkpoint()}
    if parts == ["cognition", "prospective-planning-integration-checkpoint"]:
        from prospective_planning_integration_checkpoint import build_prospective_planning_integration_checkpoint
        return 200, {"ok": True, "data": build_prospective_planning_integration_checkpoint()}
    if parts == ["cognition", "prospective-planning-governance-checkpoint"]:
        from prospective_planning_governance_checkpoint import build_prospective_planning_governance_checkpoint
        return 200, {"ok": True, "data": build_prospective_planning_governance_checkpoint()}
    if parts == ["cognition", "internally-generated-goal-integration-checkpoint"]:
        from internally_generated_goal_integration_checkpoint import build_internally_generated_goal_integration_checkpoint
        return 200, {"ok": True, "data": build_internally_generated_goal_integration_checkpoint()}

    if parts == ["cognition", "internally-generated-goal-governance-checkpoint"]:
        from internally_generated_goal_governance_checkpoint import build_internally_generated_goal_governance_checkpoint
        return 200, {"ok": True, "data": build_internally_generated_goal_governance_checkpoint()}

    if parts == ["cognition", "internally-generated-goal-deliberation-checkpoint"]:
        from internally_generated_goal_deliberation_checkpoint import build_internally_generated_goal_deliberation_checkpoint
        return 200, {"ok": True, "data": build_internally_generated_goal_deliberation_checkpoint()}
    if parts == ["cognition", "revisable-world-model-deliberation-checkpoint"]:
        from revisable_world_model_deliberation_checkpoint import build_revisable_world_model_deliberation_checkpoint
        return 200, {"ok": True, "data": build_revisable_world_model_deliberation_checkpoint()}

    if parts == ["cognition", "revisable-world-model-integration-checkpoint"]:
        from revisable_world_model_integration_checkpoint import build_revisable_world_model_integration_checkpoint
        return 200, {"ok": True, "data": build_revisable_world_model_integration_checkpoint()}

    if parts == ["cognition", "revisable-world-model-governance-checkpoint"]:
        from revisable_world_model_governance_checkpoint import build_revisable_world_model_governance_checkpoint
        return 200, {"ok": True, "data": build_revisable_world_model_governance_checkpoint()}

    if parts == ["cognition", "read-only-perception-integration-checkpoint"]:
        from read_only_perception_integration_checkpoint import build_read_only_perception_integration_checkpoint
        return 200, {"ok": True, "data": build_read_only_perception_integration_checkpoint()}

    if parts == ["cognition", "read-only-perception-deliberation-checkpoint"]:
        from read_only_perception_deliberation_checkpoint import build_read_only_perception_deliberation_checkpoint
        return 200, {"ok": True, "data": build_read_only_perception_deliberation_checkpoint()}

    if parts == ["cognition", "reflection-supported-revision-intake-checkpoint"]:
        from reflection_supported_revision_intake_checkpoint import build_reflection_supported_revision_intake_checkpoint
        return 200, {"ok": True, "data": build_reflection_supported_revision_intake_checkpoint()}

    if parts == ["cognition", "reflection-supported-revision-integration-checkpoint"]:
        from reflection_supported_revision_integration_checkpoint import build_reflection_supported_revision_integration_checkpoint
        return 200, {"ok": True, "data": build_reflection_supported_revision_integration_checkpoint()}

    if parts == ["cognition", "reflection-supported-revision-deliberation-checkpoint"]:
        from reflection_supported_revision_deliberation_checkpoint import build_reflection_supported_revision_deliberation_checkpoint
        return 200, {"ok": True, "data": build_reflection_supported_revision_deliberation_checkpoint()}

    if parts == ["cognition", "reflection-supported-revision-governance-checkpoint"]:
        from reflection_supported_revision_governance_checkpoint import build_reflection_supported_revision_governance_checkpoint
        return 200, {"ok": True, "data": build_reflection_supported_revision_governance_checkpoint()}

    if parts == ["cognition", "continuous-thought-intake-checkpoint"]:
        from continuous_thought_intake_checkpoint import build_continuous_thought_intake_checkpoint
        return 200, {"ok": True, "data": build_continuous_thought_intake_checkpoint()}

    if parts == ["cognition", "reflective-session-intake-checkpoint"]:
        from reflective_session_intake_checkpoint import build_reflective_session_intake_checkpoint
        return 200, {"ok": True, "data": build_reflective_session_intake_checkpoint()}

    if parts == ["cognition", "reflective-attention-salience-governance-checkpoint"]:
        from reflective_attention_salience_governance_checkpoint import build_reflective_attention_salience_governance_checkpoint
        return 200, {"ok": True, "data": build_reflective_attention_salience_governance_checkpoint()}

    if parts == ["cognition", "reflective-attention-deliberation-checkpoint"]:
        from reflective_attention_deliberation_checkpoint import build_reflective_attention_deliberation_checkpoint
        return 200, {"ok": True, "data": build_reflective_attention_deliberation_checkpoint()}

    if parts == ["cognition", "objective-coherence-intake-checkpoint"]:
        from objective_coherence_intake_checkpoint import build_objective_coherence_intake_checkpoint
        return 200, {"ok": True, "data": build_objective_coherence_intake_checkpoint()}

    if parts == ["cognition", "objective-coherence-deliberation-checkpoint"]:
        from objective_coherence_deliberation_checkpoint import build_objective_coherence_deliberation_checkpoint
        return 200, {"ok": True, "data": build_objective_coherence_deliberation_checkpoint()}

    if parts == ["cognition", "goal-continuity-review-checkpoint"]:
        from goal_continuity_review_checkpoint import build_goal_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_goal_continuity_review_checkpoint()}

    if parts == ["cognition", "goal-coherence-long-horizon-objective-governance-checkpoint"]:
        from goal_coherence_long_horizon_objective_governance_checkpoint import build_goal_coherence_long_horizon_objective_governance_checkpoint
        return 200, {"ok": True, "data": build_goal_coherence_long_horizon_objective_governance_checkpoint()}

    if parts == ["cognition", "self-model-integrity-intake-checkpoint"]:
        from self_model_integrity_intake_checkpoint import build_self_model_integrity_intake_checkpoint
        return 200, {"ok": True, "data": build_self_model_integrity_intake_checkpoint()}

    if parts == ["cognition", "self-model-revision-deliberation-checkpoint"]:
        from self_model_revision_deliberation_checkpoint import build_self_model_revision_deliberation_checkpoint
        return 200, {"ok": True, "data": build_self_model_revision_deliberation_checkpoint()}
    if parts == ["cognition", "self-model-continuity-review-checkpoint"]:
        from self_model_continuity_review_checkpoint import build_self_model_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_self_model_continuity_review_checkpoint()}

    if parts == ["cognition", "self-model-integrity-identity-claim-governance-checkpoint"]:
        from self_model_integrity_identity_claim_governance_checkpoint import build_self_model_integrity_identity_claim_governance_checkpoint
        return 200, {"ok": True, "data": build_self_model_integrity_identity_claim_governance_checkpoint()}

    if parts == ["cognition", "epistemic-coherence-intake-checkpoint"]:
        from epistemic_coherence_intake_checkpoint import build_epistemic_coherence_intake_checkpoint
        return 200, {"ok": True, "data": build_epistemic_coherence_intake_checkpoint()}

    if parts == ["cognition", "epistemic-coherence-deliberation-checkpoint"]:
        from epistemic_coherence_deliberation_checkpoint import build_epistemic_coherence_deliberation_checkpoint
        return 200, {"ok": True, "data": build_epistemic_coherence_deliberation_checkpoint()}

    if parts == ["cognition", "knowledge-belief-integration-checkpoint"]:
        from knowledge_belief_integration_checkpoint import build_knowledge_belief_integration_checkpoint
        return 200, {"ok": True, "data": build_knowledge_belief_integration_checkpoint()}

    if parts == ["cognition", "epistemic-coherence-knowledge-belief-integration-checkpoint"]:
        from epistemic_coherence_knowledge_belief_integration_checkpoint import build_epistemic_coherence_knowledge_belief_integration_checkpoint
        return 200, {"ok": True, "data": build_epistemic_coherence_knowledge_belief_integration_checkpoint()}

    if parts == ["cognition", "epistemic-maintenance-belief-revision-governance-checkpoint"]:
        from epistemic_maintenance_belief_revision_governance_checkpoint import build_epistemic_maintenance_belief_revision_governance_checkpoint
        return 200, {"ok": True, "data": build_epistemic_maintenance_belief_revision_governance_checkpoint()}

    if parts == ["cognition", "belief-continuity-review-checkpoint"]:
        from belief_continuity_review_checkpoint import build_belief_continuity_review_checkpoint
        return 200, {"ok": True, "data": build_belief_continuity_review_checkpoint()}

    if parts == ["cognition", "belief-revision-deliberation-checkpoint"]:
        from belief_revision_deliberation_checkpoint import build_belief_revision_deliberation_checkpoint
        return 200, {"ok": True, "data": build_belief_revision_deliberation_checkpoint()}

    if parts == ["cognition", "belief-reconsideration-intake-checkpoint"]:
        from belief_reconsideration_intake_checkpoint import build_belief_reconsideration_intake_checkpoint
        return 200, {"ok": True, "data": build_belief_reconsideration_intake_checkpoint()}

    if parts == ["cognition", "reflective-temporal-continuity-prospective-memory-checkpoint"]:
        from reflective_temporal_continuity_prospective_memory_checkpoint import build_reflective_temporal_continuity_prospective_memory_checkpoint
        return 200, {"ok": True, "data": build_reflective_temporal_continuity_prospective_memory_checkpoint()}

    if parts == ["cognition", "prospective-memory-continuity-checkpoint"]:
        from prospective_memory_continuity_checkpoint import build_prospective_memory_continuity_checkpoint
        return 200, _ok(build_prospective_memory_continuity_checkpoint())
    if parts == ["cognition", "cognitive-homeostasis-sustainable-cognition-checkpoint"]:
        from cognitive_homeostasis_sustainable_cognition_checkpoint import build_cognitive_homeostasis_sustainable_cognition_checkpoint
        return 200, _ok(build_cognitive_homeostasis_sustainable_cognition_checkpoint())
    if parts == ["cognition", "cognitive-recovery-continuity-checkpoint"]:
        from cognitive_recovery_continuity_checkpoint import build_cognitive_recovery_continuity_checkpoint
        return 200, _ok(build_cognitive_recovery_continuity_checkpoint())
    if parts == ["cognition", "cognitive-homeostasis-continuity-checkpoint"]:
        from cognitive_homeostasis_continuity_checkpoint import build_cognitive_homeostasis_continuity_checkpoint
        return 200, _ok(build_cognitive_homeostasis_continuity_checkpoint())
    if parts == ["cognition", "internal-coordination-cognitive-load-governance-checkpoint"]:
        from internal_coordination_cognitive_load_governance_checkpoint import build_internal_coordination_cognitive_load_governance_checkpoint
        return 200, _ok(build_internal_coordination_cognitive_load_governance_checkpoint())
    if parts == ["cognition", "reflective-planning-deliberative-choice-checkpoint"]:
        from reflective_planning_deliberative_choice_checkpoint import build_reflective_planning_deliberative_choice_checkpoint
        return 200, _ok(build_reflective_planning_deliberative_choice_checkpoint())

    if parts == ["cognition", "persistent-identity-model"]:
        from persistent_identity_model import build_persistent_identity_model_inspection
        return 200, _ok(build_persistent_identity_model_inspection())

    if parts == ["cognition", "identity-evidence-arbitration"]:
        from identity_evidence_arbitration import build_identity_evidence_arbitration_inspection
        return 200, _ok(build_identity_evidence_arbitration_inspection())

    if parts == ["cognition", "self-model-continuity-checkpoint"]:
        from self_model_continuity_checkpoint import build_self_model_continuity_checkpoint
        return 200, _ok(build_self_model_continuity_checkpoint())

    if parts == ["cognition", "identity-change-detection"]:
        from identity_change_detection import build_identity_change_detection_inspection
        return 200, _ok(build_identity_change_detection_inspection())

    if parts == ["cognition", "self-model-revision"]:
        from self_model_revision import build_self_model_revision_inspection
        return 200, _ok(build_self_model_revision_inspection())

    if parts == ["cognition", "identity-revision-checkpoint"]:
        from identity_revision_checkpoint import build_identity_revision_checkpoint
        return 200, _ok(build_identity_revision_checkpoint())

    if parts == ["cognition", "self-model-reflection-influence"]:
        from self_model_reflection_influence import build_self_model_reflection_influence_inspection
        return 200, _ok(build_self_model_reflection_influence_inspection())

    if parts == ["cognition", "identity-communication-arbitration"]:
        from identity_communication_arbitration import build_identity_communication_arbitration_inspection
        return 200, _ok(build_identity_communication_arbitration_inspection())

    if parts == ["cognition", "identity-expression-lifecycle-checkpoint"]:
        from identity_expression_lifecycle_checkpoint import build_identity_expression_lifecycle_checkpoint
        return 200, _ok(build_identity_expression_lifecycle_checkpoint())

    if parts == ["cognition", "persistent-self-model-checkpoint"]:
        from persistent_self_model_checkpoint import build_persistent_self_model_checkpoint
        return 200, _ok(build_persistent_self_model_checkpoint())

    if parts == ["cognition", "proactive", "unread"]:
        from proactive_communication import ProactiveCommunicationStore
        payload = ProactiveCommunicationStore().inspection_summary(message_limit=32, decision_limit=8)
        payload["messages"] = [row for row in payload.get("recent_messages", []) if row.get("unread") and row.get("state") == "delivered"]
        return 200, _ok(payload)

    if parts == ["status"]:
        return 200, _ok(build_status_payload())

    if parts == ["release-candidate-package-status"]:
        from release_candidate_coherence import candidate_package_handoff_status
        return 200, _ok(candidate_package_handoff_status(
            installed_version=str(query.get("installed_version", [""])[0] or ""),
            promoted_version=str(query.get("promoted_version", [""])[0] or ""),
            certified_version=str(query.get("certified_version", [""])[0] or ""),
        ))

    if parts == ["release-handoff", "status"]:
        from release_handoff_inspection import operator_selected_handoff_status
        return 200, _ok(operator_selected_handoff_status())

    if parts == ["release-installation", "preview", "status"]:
        from release_installation_preview import installation_impact_preview_status
        return 200, _ok(installation_impact_preview_status())

    if parts == ["release-installation", "plan", "status"]:
        from release_installation_plan import installation_plan_status
        return 200, _ok(installation_plan_status())

    if parts == ["release-installation", "staging", "status"]:
        from release_installation_staging import installation_staging_status
        return 200, _ok(installation_staging_status())

    if parts == ["release-installation", "transaction", "status"]:
        from release_installation_transaction import installation_transaction_status
        return 200, _ok(installation_transaction_status())

    if parts == ["release-installation", "recovery", "status"]:
        from release_installation_recovery import inspect_installation_transaction
        return 200, _ok(inspect_installation_transaction())

    if parts == ["release-installation", "installed-state", "status"]:
        from release_installed_state import installed_state_status
        return 200, _ok(installed_state_status())

    if parts == ["release-promotion", "preview", "status"]:
        from release_promotion_preview import promotion_preview_status
        return 200, _ok(promotion_preview_status())

    if parts == ["release-promotion", "plan", "status"]:
        from release_promotion_plan import promotion_plan_status
        return 200, _ok(promotion_plan_status())

    if parts == ["release-promotion", "status"]:
        from release_promotion_transaction import promotion_transaction_status
        return 200, _ok(promotion_transaction_status())

    if parts == ["release-certification", "readiness", "status"]:
        from release_certification_evidence import certification_readiness_status
        return 200, _ok(certification_readiness_status())

    if parts == ["release-certification", "plan", "status"]:
        from release_certification_plan import certification_plan_status
        return 200, _ok(certification_plan_status())

    if parts == ["release-certification", "status"]:
        from release_certification_transaction import certification_status
        return 200, _ok(certification_status())

    if parts == ["release-certification", "recovery", "status"]:
        from release_certification_recovery import certification_recovery_status
        return 200, _ok(certification_recovery_status())

    if parts == ["release-certification", "evidence", "freshness"]:
        from release_certification_freshness import evidence_freshness_status
        return 200, _ok(evidence_freshness_status())

    if parts == ["release-certification", "recertification", "status"]:
        from release_certification_freshness import recertification_readiness_status
        return 200, _ok(recertification_readiness_status())

    if parts == ["release-certification", "coherence", "status"]:
        from release_certification_coherence import certification_coherence_status
        return 200, _ok(certification_coherence_status())

    if parts == ["release-certification", "history", "status"]:
        from release_certification_history import certification_history_status
        return 200, _ok(certification_history_status())

    if parts == ["release-certification", "policy", "status"]:
        from release_certification_policy import certification_policy_status
        return 200, _ok(certification_policy_status())

    if parts == ["release-certification", "policy", "migration", "status"]:
        from release_certification_policy import policy_migration_status
        return 200, _ok(policy_migration_status())

    if parts == ["release-certification", "authority", "status"]:
        from release_certification_authority import certification_authority_coherence_status
        return 200, _ok(certification_authority_coherence_status())

    if parts == ["release-authority", "readiness", "status"]:
        from release_authority_readiness import release_authority_readiness_status
        return 200, _ok(release_authority_readiness_status())

    if parts == ["release-authority", "readiness", "refresh", "status"]:
        from release_authority_readiness_recovery import readiness_refresh_status
        return 200, _ok(readiness_refresh_status())

    if parts == ["release-authority", "handoff-plan", "status"]:
        from release_authority_handoff_plan import release_authority_handoff_plan_status
        return 200, _ok(release_authority_handoff_plan_status())

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "status"]:
        from release_authority_handoff_plan import release_authority_handoff_acknowledgment_status
        return 200, _ok(release_authority_handoff_acknowledgment_status())

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "recovery", "status"]:
        from release_authority_handoff_ack_recovery import handoff_acknowledgment_recovery_status
        return 200, _ok(handoff_acknowledgment_recovery_status())

    if parts == ["release-authority", "consumer", "receipt", "status"]:
        from release_authority_consumer import release_authority_consumer_receipt_status
        payload = release_authority_consumer_receipt_status(
            str(query.get("consumer_id", [""])[0] or ""),
            str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""),
            str(query.get("expected_use", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "lifecycle", "status"]:
        from release_authority_consumer_lifecycle import consumer_receipt_lifecycle_status
        payload = consumer_receipt_lifecycle_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-lifecycle", "status"]:
        from release_authority_consumer_lifecycle import release_authority_handoff_lifecycle_status
        payload = release_authority_handoff_lifecycle_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "selection", "status"]:
        from release_authority_consumer_daily_use import consumer_selection_status
        payload = consumer_selection_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
            str(query.get("selection_purpose", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "use-preflight", "status"]:
        from release_authority_consumer_daily_use import consumer_use_preflight_status
        payload = consumer_use_preflight_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
            str(query.get("selection_purpose", [""])[0] or ""), str(query.get("use_id", [""])[0] or ""),
            str(query.get("use_schema", [""])[0] or ""), str(query.get("use_version", [""])[0] or ""),
            str(query.get("declared_use", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer-daily-use", "status"]:
        from release_authority_consumer_daily_use import release_authority_consumer_daily_use_status
        payload = release_authority_consumer_daily_use_status(
            consumer_id=str(query.get("consumer_id", [""])[0] or ""),
            consumer_schema=str(query.get("consumer_schema", [""])[0] or ""),
            consumer_version=str(query.get("consumer_version", [""])[0] or ""),
            expected_use=str(query.get("expected_use", [""])[0] or ""),
            selection_purpose=str(query.get("selection_purpose", [""])[0] or ""),
            use_id=str(query.get("use_id", [""])[0] or ""),
            use_schema=str(query.get("use_schema", [""])[0] or ""),
            use_version=str(query.get("use_version", [""])[0] or ""),
            declared_use=str(query.get("declared_use", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer-daily-use-binding", "status"]:
        from release_authority_consumer_daily_use_recovery import release_authority_consumer_daily_use_binding_status
        successor_consumer = (
            str(query.get("successor_consumer_id", [""])[0] or ""),
            str(query.get("successor_consumer_schema", [""])[0] or ""),
            str(query.get("successor_consumer_version", [""])[0] or ""),
            str(query.get("successor_expected_use", [""])[0] or ""),
        )
        successor_use = (
            str(query.get("successor_use_id", [""])[0] or ""),
            str(query.get("successor_use_schema", [""])[0] or ""),
            str(query.get("successor_use_version", [""])[0] or ""),
            str(query.get("successor_declared_use", [""])[0] or ""),
        )
        payload = release_authority_consumer_daily_use_binding_status(
            consumer_id=str(query.get("consumer_id", [""])[0] or ""), consumer_schema=str(query.get("consumer_schema", [""])[0] or ""),
            consumer_version=str(query.get("consumer_version", [""])[0] or ""), expected_use=str(query.get("expected_use", [""])[0] or ""),
            selection_purpose=str(query.get("selection_purpose", [""])[0] or ""), use_id=str(query.get("use_id", [""])[0] or ""),
            use_schema=str(query.get("use_schema", [""])[0] or ""), use_version=str(query.get("use_version", [""])[0] or ""),
            declared_use=str(query.get("declared_use", [""])[0] or ""),
            successor_consumer=successor_consumer if any(successor_consumer) else None,
            successor_selection_purpose=str(query.get("successor_selection_purpose", [""])[0] or ""),
            successor_use=successor_use if any(successor_use) else None,
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-recovery", "status"]:
        from release_authority_consumer_daily_use_recovery import consumer_daily_use_recovery_status
        payload = consumer_daily_use_recovery_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
            str(query.get("selection_purpose", [""])[0] or ""), str(query.get("use_id", [""])[0] or ""),
            str(query.get("use_schema", [""])[0] or ""), str(query.get("use_version", [""])[0] or ""),
            str(query.get("declared_use", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer-use-handoff", "status"]:
        from release_authority_consumer_use_handoff import consumer_use_handoff_plan_status
        payload = consumer_use_handoff_plan_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
            str(query.get("selection_purpose", [""])[0] or ""), str(query.get("use_id", [""])[0] or ""),
            str(query.get("use_schema", [""])[0] or ""), str(query.get("use_version", [""])[0] or ""),
            str(query.get("declared_use", [""])[0] or ""), str(query.get("downstream_consumer_id", [""])[0] or ""),
            str(query.get("downstream_consumer_schema", [""])[0] or ""), str(query.get("downstream_consumer_version", [""])[0] or ""),
            str(query.get("downstream_expected_use", [""])[0] or ""), str(query.get("expected_result_schema", [""])[0] or ""),
            str(query.get("expected_result_version", [""])[0] or ""), str(query.get("expected_outcome", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "result-validation", "status"]:
        from release_authority_consumer_use_handoff import downstream_consumer_result_validation_status
        payload = downstream_consumer_result_validation_status(
            str(query.get("consumer_id", [""])[0] or ""), str(query.get("consumer_schema", [""])[0] or ""),
            str(query.get("consumer_version", [""])[0] or ""), str(query.get("expected_use", [""])[0] or ""),
            str(query.get("selection_purpose", [""])[0] or ""), str(query.get("use_id", [""])[0] or ""),
            str(query.get("use_schema", [""])[0] or ""), str(query.get("use_version", [""])[0] or ""),
            str(query.get("declared_use", [""])[0] or ""), str(query.get("downstream_consumer_id", [""])[0] or ""),
            str(query.get("downstream_consumer_schema", [""])[0] or ""), str(query.get("downstream_consumer_version", [""])[0] or ""),
            str(query.get("downstream_expected_use", [""])[0] or ""), str(query.get("expected_result_schema", [""])[0] or ""),
            str(query.get("expected_result_version", [""])[0] or ""), str(query.get("expected_outcome", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer-use-lifecycle", "status"]:
        from release_authority_consumer_use_handoff import release_authority_consumer_use_lifecycle_status
        payload = release_authority_consumer_use_lifecycle_status(
            consumer_id=str(query.get("consumer_id", [""])[0] or ""), consumer_schema=str(query.get("consumer_schema", [""])[0] or ""),
            consumer_version=str(query.get("consumer_version", [""])[0] or ""), expected_use=str(query.get("expected_use", [""])[0] or ""),
            selection_purpose=str(query.get("selection_purpose", [""])[0] or ""), use_id=str(query.get("use_id", [""])[0] or ""),
            use_schema=str(query.get("use_schema", [""])[0] or ""), use_version=str(query.get("use_version", [""])[0] or ""),
            declared_use=str(query.get("declared_use", [""])[0] or ""), downstream_consumer_id=str(query.get("downstream_consumer_id", [""])[0] or ""),
            downstream_consumer_schema=str(query.get("downstream_consumer_schema", [""])[0] or ""),
            downstream_consumer_version=str(query.get("downstream_consumer_version", [""])[0] or ""),
            downstream_expected_use=str(query.get("downstream_expected_use", [""])[0] or ""),
            expected_result_schema=str(query.get("expected_result_schema", [""])[0] or ""),
            expected_result_version=str(query.get("expected_result_version", [""])[0] or ""),
            expected_outcome=str(query.get("expected_outcome", [""])[0] or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "daily-use", "status"]:
        from release_authority_daily_use import release_authority_daily_use_status
        return 200, _ok(release_authority_daily_use_status(
            consumer_id=str(query.get("consumer_id", [""])[0] or ""),
            consumer_schema=str(query.get("consumer_schema", [""])[0] or ""),
            consumer_version=str(query.get("consumer_version", [""])[0] or ""),
            consumer_expected_use=str(query.get("expected_use", [""])[0] or ""),
        ))

    if parts == ["release-history-status"]:
        from release_history import release_history_status
        return 200, _ok(release_history_status())

    if parts == ["release-history-reconciliation", "preview"]:
        from release_history_reconciliation import preview_release_history_reconciliation
        payload = preview_release_history_reconciliation()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["version-roles"]:
        from version_roles import build_version_role_contract
        return 200, _ok(build_version_role_contract(
            installed_version=str(query.get("installed_version", [""])[0] or ""),
            candidate_version=str(query.get("candidate_version", [""])[0] or ""),
            packaged_archive_name=str(query.get("archive_name", [""])[0] or ""),
            promoted_version=str(query.get("promoted_version", [""])[0] or ""),
            certified_version=str(query.get("certified_version", [""])[0] or ""),
        ))

    if parts == ["version-resolution"]:
        from version_resolution import build_cross_surface_version_resolution
        return 200, _ok(build_cross_surface_version_resolution(
            installed_version=str(query.get("installed_version", [""])[0] or ""),
            candidate_version=str(query.get("candidate_version", [""])[0] or ""),
            packaged_archive_name=str(query.get("archive_name", [""])[0] or ""),
        ))

    if parts == ["version-drift"]:
        from version_drift_reconciliation import build_version_drift_preview
        return 200, _ok(build_version_drift_preview(
            candidate_version=str(query.get("candidate_version", [""])[0] or ""),
            packaged_archive_name=str(query.get("archive_name", [""])[0] or ""),
            archive_root_name=str(query.get("archive_root", [""])[0] or ""),
        ))

    if parts == ["version-reconciliation", "preview"]:
        from version_drift_reconciliation import preview_version_reconciliation
        try:
            payload = preview_version_reconciliation(
                str(query.get("surface_id", [""])[0] or ""),
                expected_role=str(query.get("expected_role", ["working_source"])[0] or "working_source"),
                expected_version=str(query.get("expected_version", [""])[0] or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["conversation", "daily-use-stability-checkpoint"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_daily_use_stability_checkpoint(session_id=session_id))

    if parts == ["conversation", "relationship-continuity-checkpoint"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_relationship_continuity_checkpoint(session_id=session_id))

    if parts == ["conversation", "conversation-quality-checkpoint"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_conversation_quality_checkpoint(session_id=session_id))

    if parts == ["conversation", "context-inspection"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_context_inspection_for_session(session_id=session_id))

    if parts == ["conversation", "context-intelligence-checkpoint"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_context_intelligence_checkpoint(session_id=session_id))

    if parts == ["conversation", "control-foundation"]:
        return 200, _ok(build_conversation_control_foundation())
    if parts == ["conversation", "offline-degradation"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(offline_conversation_degradation_state(session_id=session_id, provider_available=False))
    if parts == ["conversation", "long-session-hardening"]:
        try:
            return 200, _ok(build_long_session_hardening_state(str(query.get("session_id", [""])[0] or "")))
        except ValueError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "readiness-checkpoint"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_conversation_readiness_checkpoint(session_id=session_id))
    if parts == ["conversation", "daily-evaluation-protocol"]:
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_daily_evaluation_protocol(session_id=session_id))
    if parts == ["conversation", "daily-evaluation"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        try:
            return 200, _ok(load_daily_evaluation(evaluation_id))
        except DailyEvaluationError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-reproduction"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        try:
            return 200, _ok(build_reproduction_packet(evaluation_id))
        except DailyEvaluationError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-trends"]:
        return 200, _ok(build_daily_evaluation_trends(maximum_evaluations=int(query.get("maximum_evaluations", ["256"])[0] or 256)))
    if parts == ["conversation", "restart-outage-evaluation"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        try:
            return 200, _ok(build_restart_outage_evaluation(evaluation_id))
        except DailyEvaluationError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "long-session-evaluation"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        try:
            return 200, _ok(build_long_session_evaluation(evaluation_id))
        except DailyEvaluationError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-console"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_evaluation_console_state(evaluation_id=evaluation_id, session_id=session_id))
    if parts == ["conversation", "evaluation-review-export"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_review_export(evaluation_id))
        except DailyEvaluationError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "daily-evaluation-checkpoint"]:
        evaluation_id = str(query.get("evaluation_id", [""])[0] or "")
        session_id = str(query.get("session_id", [""])[0] or "")
        return 200, _ok(build_daily_evaluation_checkpoint(evaluation_id=evaluation_id, session_id=session_id))
    if parts == ["conversation", "evaluation-campaign-protocol"]:
        return 200, _ok(build_evaluation_campaign_protocol())
    if parts == ["conversation", "evaluation-campaign"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        try:
            return 200, _ok(load_evaluation_campaign(campaign_id))
        except EvaluationCampaignError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-progress"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_campaign_progress(campaign_id))
        except EvaluationCampaignError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-issues"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_campaign_issue_aggregation(campaign_id))
        except EvaluationCampaignError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-follow-ups"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_campaign_follow_ups(campaign_id))
        except EvaluationCampaignError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-comparison"]:
        campaign_ids = [str(value or "").strip() for value in query.get("campaign_id", [])]
        for raw in query.get("campaign_ids", []):
            campaign_ids.extend(part.strip() for part in str(raw or "").split(","))
        try:
            return 200, _ok(build_evaluation_campaign_comparison(campaign_ids))
        except EvaluationCampaignError as error:
            raise ApiError(400, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-review"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_campaign_review(campaign_id))
        except EvaluationCampaignError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-console"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        comparison_ids = [str(value or "").strip() for value in query.get("comparison_campaign_id", [])]
        for raw in query.get("comparison_campaign_ids", []):
            comparison_ids.extend(part.strip() for part in str(raw or "").split(","))
        return 200, _ok(build_evaluation_campaign_console_state(
            campaign_id=campaign_id,
            comparison_campaign_ids=comparison_ids,
        ))
    if parts == ["conversation", "evaluation-campaign-review-export"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_campaign_review_export(campaign_id))
        except EvaluationCampaignError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-campaign-checkpoint"]:
        campaign_id = str(query.get("campaign_id", [""])[0] or "")
        comparison_ids = [str(value or "").strip() for value in query.get("comparison_campaign_id", [])]
        for raw in query.get("comparison_campaign_ids", []):
            comparison_ids.extend(part.strip() for part in str(raw or "").split(","))
        return 200, _ok(build_operator_evaluation_campaign_checkpoint(
            campaign_id=campaign_id,
            comparison_campaign_ids=comparison_ids,
        ))
    if parts == ["conversation", "evaluation-findings-checkpoint"]:
        comparison_ids = [str(value or "").strip() for value in query.get("comparison_finding_id", [])]
        for raw in query.get("comparison_finding_ids", []):
            comparison_ids.extend(part.strip() for part in str(raw or "").split(","))
        return 200, _ok(build_evaluation_findings_checkpoint(
            finding_id=str(query.get("finding_id", [""])[0] or ""),
            campaign_id=str(query.get("campaign_id", [""])[0] or ""),
            evaluation_id=str(query.get("evaluation_id", [""])[0] or ""),
            state=str(query.get("state", [""])[0] or ""),
            comparison_finding_ids=comparison_ids,
        ))
    if parts == ["conversation", "repair-candidate-review-protocol"]:
        return 200, _ok(build_repair_candidate_review_protocol())

    if parts == ["conversation", "repair-candidate-registrations"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            return 200, _ok(build_repair_candidate_registrations(finding_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error

    if parts == ["conversation", "repair-candidate-review"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        candidate_id = str(query.get("candidate_id", [""])[0] or "")
        try:
            return 200, _ok(build_repair_candidate_review(finding_id, candidate_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error

    if parts == ["conversation", "repair-candidate-verification-evidence"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        candidate_id = str(query.get("candidate_id", [""])[0] or "")
        try:
            return 200, _ok(build_repair_candidate_verification_evidence(finding_id, candidate_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error

    if parts == ["conversation", "repair-candidate-comparison"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        candidate_ids = [str(value or "").strip() for value in query.get("candidate_id", [])]
        for raw in query.get("candidate_ids", []):
            candidate_ids.extend(part.strip() for part in str(raw or "").split(","))
        try:
            return 200, _ok(build_repair_candidate_comparison(finding_id, candidate_ids))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error

    if parts == ["conversation", "repair-candidate-lineage"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            return 200, _ok(build_repair_candidate_lineage(finding_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error

    if parts == ["conversation", "repair-candidate-console"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        candidate_id = str(query.get("candidate_id", [""])[0] or "")
        comparison_ids = [str(value or "").strip() for value in query.get("comparison_candidate_id", [])]
        for raw in query.get("comparison_candidate_ids", []):
            comparison_ids.extend(part.strip() for part in str(raw or "").split(","))
        try:
            offset = int(query.get("offset", ["0"])[0] or 0)
        except (TypeError, ValueError):
            offset = 0
        limit_raw = query.get("limit", [""])[0]
        try:
            limit = int(limit_raw) if str(limit_raw or "").strip() else None
        except (TypeError, ValueError):
            limit = None
        return 200, _ok(build_repair_candidate_console_state(
            finding_id=finding_id,
            candidate_id=candidate_id,
            comparison_candidate_ids=comparison_ids,
            candidate_kind=str(query.get("candidate_kind", [""])[0] or ""),
            review_state=str(query.get("review_state", [""])[0] or ""),
            offset=offset,
            limit=limit,
        ))

    if parts == ["conversation", "repair-candidate-review-export"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        candidate_id = str(query.get("candidate_id", [""])[0] or "")
        try:
            return 200, _ok(build_repair_candidate_review_export(finding_id, candidate_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error

    if parts == ["conversation", "repair-candidate-window"]:
        try:
            offset = int(query.get("offset", ["0"])[0] or 0)
        except (TypeError, ValueError):
            offset = 0
        limit_raw = query.get("limit", [""])[0]
        try:
            limit = int(limit_raw) if str(limit_raw or "").strip() else None
        except (TypeError, ValueError):
            limit = None
        return 200, _ok(build_repair_candidate_window(
            finding_id=str(query.get("finding_id", [""])[0] or ""),
            candidate_kind=str(query.get("candidate_kind", [""])[0] or ""),
            review_state=str(query.get("review_state", [""])[0] or ""),
            offset=offset,
            limit=limit,
        ))

    if parts == ["conversation", "repair-candidate-review-checkpoint"]:
        comparison_ids = [str(value or "").strip() for value in query.get("comparison_candidate_id", [])]
        for raw in query.get("comparison_candidate_ids", []):
            comparison_ids.extend(part.strip() for part in str(raw or "").split(","))
        return 200, _ok(build_repair_candidate_review_checkpoint(
            finding_id=str(query.get("finding_id", [""])[0] or ""),
            candidate_id=str(query.get("candidate_id", [""])[0] or ""),
            comparison_candidate_ids=comparison_ids,
            candidate_kind=str(query.get("candidate_kind", [""])[0] or ""),
            review_state=str(query.get("review_state", [""])[0] or ""),
        ))

    if parts == ["product-reality-benchmark"]:
        return 200, _ok(build_product_reality_benchmark())

    if parts == ["conversation", "evaluation-finding"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            if finding_id:
                return 200, _ok(load_evaluation_finding(finding_id))
            limit_raw = query.get("limit", ["100"])[0]
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 100
            return 200, _ok(list_evaluation_findings(
                campaign_id=str(query.get("campaign_id", [""])[0] or ""),
                evaluation_id=str(query.get("evaluation_id", [""])[0] or ""),
                state=str(query.get("state", [""])[0] or ""),
                limit=limit,
            ))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-finding-reproducibility"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            return 200, _ok(build_finding_reproducibility(finding_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-finding-repair-candidates"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            return 200, _ok(build_finding_repair_candidates(finding_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-finding-aggregation"]:
        limit_raw = query.get("limit", ["256"])[0]
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = 256
        return 200, _ok(build_evaluation_finding_aggregation(
            campaign_id=str(query.get("campaign_id", [""])[0] or ""),
            evaluation_id=str(query.get("evaluation_id", [""])[0] or ""),
            limit=limit,
        ))
    if parts == ["conversation", "evaluation-finding-triage"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_finding_triage(finding_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-finding-comparison"]:
        finding_ids = [str(value or "").strip() for value in query.get("finding_id", [])]
        for raw in query.get("finding_ids", []):
            finding_ids.extend(part.strip() for part in str(raw or "").split(","))
        try:
            return 200, _ok(build_evaluation_finding_comparison(finding_ids))
        except EvaluationFindingError as error:
            raise ApiError(400, str(error)) from error
    if parts == ["conversation", "evaluation-finding-console"]:
        comparison_ids = [str(value or "").strip() for value in query.get("comparison_finding_id", [])]
        for raw in query.get("comparison_finding_ids", []):
            comparison_ids.extend(part.strip() for part in str(raw or "").split(","))
        try:
            offset = int(query.get("offset", ["0"])[0] or 0)
        except (TypeError, ValueError):
            offset = 0
        limit_value = query.get("limit", [None])[0]
        try:
            limit = int(limit_value) if limit_value not in {None, ""} else None
        except (TypeError, ValueError):
            limit = None
        return 200, _ok(build_evaluation_finding_console_state(
            finding_id=str(query.get("finding_id", [""])[0] or ""),
            campaign_id=str(query.get("campaign_id", [""])[0] or ""),
            evaluation_id=str(query.get("evaluation_id", [""])[0] or ""),
            state=str(query.get("state", [""])[0] or ""),
            comparison_finding_ids=comparison_ids,
            offset=offset,
            limit=limit,
        ))
    if parts == ["conversation", "evaluation-finding-review-export"]:
        finding_id = str(query.get("finding_id", [""])[0] or "")
        try:
            return 200, _ok(build_evaluation_finding_review_export(finding_id))
        except EvaluationFindingError as error:
            raise ApiError(404, str(error)) from error
    if parts == ["conversation", "evaluation-finding-window"]:
        try:
            offset = int(query.get("offset", ["0"])[0] or 0)
        except (TypeError, ValueError):
            offset = 0
        limit_value = query.get("limit", [None])[0]
        try:
            limit = int(limit_value) if limit_value not in {None, ""} else None
        except (TypeError, ValueError):
            limit = None
        return 200, _ok(build_evaluation_finding_window(
            campaign_id=str(query.get("campaign_id", [""])[0] or ""),
            evaluation_id=str(query.get("evaluation_id", [""])[0] or ""),
            state=str(query.get("state", [""])[0] or ""),
            offset=offset,
            limit=limit,
        ))
    if parts == ["conversation", "turn-action-plan"]:
        try:
            return 200, _ok(build_turn_action_plan(
                str(query.get("session_id", [""])[0]),
                str(query.get("turn_id", [""])[0]),
            ))
        except (ConversationTurnActionError, ValueError) as error:
            raise ApiError(400, str(error)) from error

    if parts == ["local-model", "status"]:
        return 200, _ok(local_model_status())

    if parts == ["local-model", "readiness"]:
        report = provider_readiness(previous_state=str(query.get("previous_state", [""])[0] or "") or None)
        evidence = load_provider_recovery_evidence()
        report["persisted_recovery_evidence"] = evidence
        report["provider_resume_cue"] = provider_resume_cue(evidence)
        return 200, _ok(report)

    if parts == ["local-model", "configuration"]:
        return 200, _ok(configuration_payload())

    if parts == ["stabilization-checkpoint"]:
        project_id = query.get("project", ["eidolon"])[0]
        full = _query_bool(query, "full", False)
        return 200, _ok(build_stabilization_checkpoint(project_id=project_id, full=full))

    if parts == ["doctor"]:
        project_id = query.get("project", ["eidolon"])[0]
        full = _query_bool(query, "full", False)
        return 200, _ok(build_doctor_report(project_id=project_id, full=full))

    if parts == ["doctor", "diagnostic-preview-cache"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_preview_cache(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic preview cache is GET preview-only and does not execute live diagnostic fan-out.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_freshness_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache freshness metadata is GET preview-only and does not execute live diagnostic fan-out or write a persisted cache.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness", "digest-verification"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_source_dependency_digest_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache digest verification is GET preview-only, dry-run overlay only, and does not mutate source or write a persisted cache.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness", "digest-drift-classification"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_digest_drift_classification_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache digest drift classification is GET preview-only, dry-run overlay only, and does not mutate source or write a persisted cache.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness", "contract-drift-fixtures"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_contract_drift_fixture_expansion_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache contract drift fixtures are GET preview-only, dry-run overlay only, and do not mutate source or write a persisted cache.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness", "drift-severity-guidance"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_drift_severity_guidance_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache drift severity guidance is GET preview-only, dry-run overlay only, and does not mutate source, write a persisted cache, or auto-repair drift.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness", "severity-route-impact-matrix"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_severity_route_impact_matrix_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache severity route impact matrix is GET preview-only, dry-run guidance only, and does not mutate source, write a persisted cache, execute diagnostics, or auto-repair drift.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-preview-cache", "freshness", "impact-operator-action-ledger"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_diagnostic_cache_impact_operator_action_ledger_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor diagnostic cache impact operator action ledger is GET preview-only, dry-run guidance only, and does not mutate source, write a persisted cache, execute diagnostics, auto-repair drift, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["doctor", "headroom"]:
        from dashboard_doctor_headroom_repair import build_doctor_dashboard_headroom_snapshot

        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_dashboard_headroom_snapshot(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Doctor headroom snapshot is GET preview-only and does not execute live diagnostic fan-out.")
        return 200, _ok(report)




    if parts == ["install-release", "historical-blocker-reduction"]:
        from install_release_historical_blocker_reduction import build_install_release_historical_blocker_reduction, build_install_release_historical_blocker_reduction_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_registry = _query_bool(query, "inspect_registry", True)
        report = build_install_release_historical_blocker_reduction(None, inspect_registry=inspect_registry) if inspect_registry else build_install_release_historical_blocker_reduction_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Install-release historical blocker reduction is GET preview-only and does not execute blocked checks, mark install-release clean, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["source-surface", "dispatch-candidate-preparation"]:
        from source_surface_manifest_dispatch_candidate_preparation import build_source_surface_manifest_dispatch_candidate_preparation, build_source_surface_manifest_dispatch_candidate_preparation_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_source_surface_manifest_dispatch_candidate_preparation(None, inspect_sources=inspect_sources) if inspect_sources else build_source_surface_manifest_dispatch_candidate_preparation_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Source surface manifest dispatch candidate preparation is GET preview-only and does not generate wiring, register routes, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["source-surface", "manifest-generated-dispatch-parity-fixture-preview"]:
        from manifest_generated_dispatch_parity_fixture_preview import build_manifest_generated_dispatch_parity_fixture_preview, build_manifest_generated_dispatch_parity_fixture_preview_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_manifest_generated_dispatch_parity_fixture_preview(None, inspect_sources=inspect_sources) if inspect_sources else build_manifest_generated_dispatch_parity_fixture_preview_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest-generated dispatch parity fixture preview is GET preview-only and does not write fixture files, execute a fixture harness, activate generated dispatch, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["source-surface", "manifest-generated-dispatch-fixture-harness-isolation"]:
        from manifest_generated_dispatch_fixture_harness_isolation import build_manifest_generated_dispatch_fixture_harness_isolation, build_manifest_generated_dispatch_fixture_harness_isolation_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_manifest_generated_dispatch_fixture_harness_isolation(None, inspect_sources=inspect_sources) if inspect_sources else build_manifest_generated_dispatch_fixture_harness_isolation_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest-generated dispatch fixture harness isolation is GET preview-only and does not write fixture files, spawn subprocesses, execute a harness, activate generated dispatch, authorize release, or expand autonomy.")
        return 200, _ok(report)


    if parts == ["source-surface", "manifest-generated-dispatch-fixture-harness-dry-run-ledger"]:
        from manifest_generated_dispatch_fixture_harness_dry_run_ledger import build_manifest_generated_dispatch_fixture_harness_dry_run_ledger, build_manifest_generated_dispatch_fixture_harness_dry_run_ledger_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_manifest_generated_dispatch_fixture_harness_dry_run_ledger(None, inspect_sources=inspect_sources) if inspect_sources else build_manifest_generated_dispatch_fixture_harness_dry_run_ledger_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest-generated dispatch fixture harness dry-run ledger is GET preview-only and does not write fixture files, spawn subprocesses, execute a harness, activate generated dispatch, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["source-surface", "manifest-generated-dispatch-fixture-dry-run-execution-prep"]:
        from manifest_generated_dispatch_fixture_dry_run_execution_prep import build_manifest_generated_dispatch_fixture_dry_run_execution_prep, build_manifest_generated_dispatch_fixture_dry_run_execution_prep_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_manifest_generated_dispatch_fixture_dry_run_execution_prep(None, inspect_sources=inspect_sources) if inspect_sources else build_manifest_generated_dispatch_fixture_dry_run_execution_prep_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest-generated dispatch fixture dry-run execution prep is GET preview-only and does not create temp workspaces, spawn subprocesses, execute commands, write fixture files, activate generated dispatch, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["source-surface", "manifest-generated-dispatch-fixture-first-isolated-dry-run-trial"]:
        from manifest_generated_dispatch_fixture_first_isolated_dry_run_trial import build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial, build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        # GET is preview-only after v1065.10; execute=true is ignored here.
        execute_trial = False
        report = build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial(None, inspect_sources=inspect_sources, execute_trial=execute_trial) if inspect_sources else build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest-generated dispatch fixture first isolated dry-run trial is bounded review evidence only. GET now spawns zero subprocesses even when inspect_sources=true; it does not write fixture files, activate generated dispatch, authorize release, or expand autonomy.")
        return 200, _ok(report)


    if parts == ["source-surface", "manifest-generated-dispatch-fixture-trial-receipt-hardening"]:
        from manifest_generated_dispatch_fixture_trial_receipt_hardening import build_manifest_generated_dispatch_fixture_trial_receipt_hardening, build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        # GET is preview-only after v1065.10; execute=true is ignored here.
        execute_trial = False
        report = build_manifest_generated_dispatch_fixture_trial_receipt_hardening(None, inspect_sources=inspect_sources, execute_trial=execute_trial) if inspect_sources else build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest-generated dispatch fixture trial receipt hardening is bounded review evidence only. Hardened receipts do not write fixture files, activate generated dispatch, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["source-surface", "manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion"]:
        from manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion import build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion, build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        # GET is side-effect free after v1065.2. Even execute=true is ignored here
        # and redirected to the explicit POST/operator action route. Tiny miracle:
        # a read route now reads.
        report = build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion(None, inspect_sources=inspect_sources, execute_batch=False, operator_confirmed=False) if inspect_sources else build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("GET is preview-only and spawns zero subprocesses. Use POST /api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion/run with the exact confirmation phrase for any future execution attempt.")
        return 200, _ok(report)

    if parts == ["source-surface", "manifest-fixture-sandbox-adapter-contract"]:
        from manifest_fixture_sandbox_adapter_contract import build_manifest_fixture_sandbox_adapter_contract, build_manifest_fixture_sandbox_adapter_contract_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_manifest_fixture_sandbox_adapter_contract(None, inspect_sources=inspect_sources) if inspect_sources else build_manifest_fixture_sandbox_adapter_contract_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Sandbox adapter contract is GET preview-only. It detects capability and blocks actual fixture execution until an audited OS-enforced backend is integrated; no subprocess, fixture file, generated wiring, release, or autonomy action is authorized.")
        return 200, _ok(report)


    if parts == ["source-surface", "full-tree-mutation-snapshot-expansion"]:
        from full_tree_mutation_snapshot import build_full_tree_mutation_snapshot_expansion, build_full_tree_mutation_snapshot_expansion_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_full_tree_mutation_snapshot_expansion(None, inspect_sources=inspect_sources) if inspect_sources else build_full_tree_mutation_snapshot_expansion_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Full-tree mutation snapshot expansion is GET preview-only. It captures source snapshots only and does not run fixtures, spawn subprocesses, write files, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["doctor", "diagnostic-api-compatibility-restoration"]:
        from diagnostic_api_compatibility_restoration import build_diagnostic_api_compatibility_restoration, build_diagnostic_api_compatibility_restoration_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_diagnostic_api_compatibility_restoration(None, inspect_sources=inspect_sources, probe_previews=inspect_sources) if inspect_sources else build_diagnostic_api_compatibility_restoration_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Diagnostic API compatibility restoration is GET preview-only. It verifies preview/full route separation and does not execute live work, apply patches, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)


    if parts == ["release", "release-tier-blocker-repair-batch-i"]:
        from release_tier_blocker_repair_batch_i import build_release_tier_blocker_repair_batch_i, build_release_tier_blocker_repair_batch_i_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_release_tier_blocker_repair_batch_i(None, execute_builders=inspect_sources) if inspect_sources else build_release_tier_blocker_repair_batch_i_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Release-tier blocker repair batch I is GET preview-only. It does not run install-release, apply patches, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["release", "release-tier-blocker-repair-batch-ii"]:
        from release_tier_blocker_repair_batch_ii import build_release_tier_blocker_repair_batch_ii, build_release_tier_blocker_repair_batch_ii_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_release_tier_blocker_repair_batch_ii(None, execute_builders=inspect_sources) if inspect_sources else build_release_tier_blocker_repair_batch_ii_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Release-tier blocker repair batch II is GET preview-only. It does not run install-release, apply patches, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)


    if parts == ["dashboard", "full-navigation-get-side-effect-safety-gate"]:
        from dashboard_full_navigation_get_side_effect_safety_gate import build_dashboard_full_navigation_get_side_effect_safety_gate, build_dashboard_full_navigation_get_side_effect_safety_gate_metadata

        project_id = query.get("project", ["eidolon"])[0]
        measure = _query_bool(query, "measure", False)
        report = build_dashboard_full_navigation_get_side_effect_safety_gate(None, measure_routes=True) if measure else build_dashboard_full_navigation_get_side_effect_safety_gate_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Full-navigation GET side-effect safety is GET preview-only by default. Bounded measurement requires explicit measure=true and still does not apply patches, run install-release, execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["install-release", "segment-runner-timeout-decomposition"]:
        from install_release_segment_runner_timeout_decomposition import build_install_release_segment_runner_timeout_decomposition, build_install_release_segment_runner_timeout_decomposition_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_install_release_segment_runner_timeout_decomposition(Path(__file__).resolve().parents[1]) if inspect_sources else build_install_release_segment_runner_timeout_decomposition_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Install-release segment runner timeout decomposition is GET preview-only. It does not run install-release, mark historical parent rows as current passes, authorize release, activate generated wiring, or expand autonomy.")
        return 200, _ok(report)


    if parts == ["source-surface", "manifest-fixture-receipt-consolidation"]:
        from manifest_fixture_receipt_consolidation import build_manifest_fixture_receipt_consolidation, build_manifest_fixture_receipt_consolidation_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_manifest_fixture_receipt_consolidation(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_manifest_fixture_receipt_consolidation_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Manifest fixture receipt consolidation is GET preview-only. It consolidates receipt evidence but does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)


    if parts == ['source-surface', 'audited-sandbox-backend-preflight-contract']:
        from audited_sandbox_backend_preflight_contract import build_audited_sandbox_backend_preflight_contract, build_audited_sandbox_backend_preflight_contract_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_audited_sandbox_backend_preflight_contract(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_audited_sandbox_backend_preflight_contract_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Audited Sandbox Backend Preflight Contract is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'sandbox-backend-capability-evidence-gate']:
        from sandbox_backend_capability_evidence_gate import build_sandbox_backend_capability_evidence_gate, build_sandbox_backend_capability_evidence_gate_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_sandbox_backend_capability_evidence_gate(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_sandbox_backend_capability_evidence_gate_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Sandbox Backend Capability Evidence Gate is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'fixture-execution-admission-gate']:
        from fixture_execution_admission_gate import build_fixture_execution_admission_gate, build_fixture_execution_admission_gate_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_fixture_execution_admission_gate(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_fixture_execution_admission_gate_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Fixture Execution Admission Gate is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'sandboxed-fixture-execution-trial']:
        from sandboxed_fixture_execution_trial import build_sandboxed_fixture_execution_trial, build_sandboxed_fixture_execution_trial_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_sandboxed_fixture_execution_trial(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_sandboxed_fixture_execution_trial_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("First Sandboxed Fixture Execution Trial is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'sandboxed-fixture-batch-execution']:
        from sandboxed_fixture_batch_execution import build_sandboxed_fixture_batch_execution, build_sandboxed_fixture_batch_execution_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_sandboxed_fixture_batch_execution(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_sandboxed_fixture_batch_execution_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Sandboxed Fixture Batch Execution is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'generated-dispatch-promotion-readiness-ledger']:
        from generated_dispatch_promotion_readiness_ledger import build_generated_dispatch_promotion_readiness_ledger, build_generated_dispatch_promotion_readiness_ledger_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_generated_dispatch_promotion_readiness_ledger(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_generated_dispatch_promotion_readiness_ledger_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Generated Dispatch Promotion Readiness Ledger is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'source-decomposition-batch-i']:
        from source_decomposition_batch_i import build_source_decomposition_batch_i, build_source_decomposition_batch_i_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_source_decomposition_batch_i(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_source_decomposition_batch_i_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Source Decomposition Batch I is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ['source-surface', 'source-decomposition-batch-ii']:
        from source_decomposition_batch_ii import build_source_decomposition_batch_ii, build_source_decomposition_batch_ii_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_source_decomposition_batch_ii(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_source_decomposition_batch_ii_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Source Decomposition Batch II is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)


    if parts == ['source-surface', 'dashboard-api-smoke-shared-utility-adoption']:
        from dashboard_api_smoke_shared_utility_adoption import api_preview_payload, build_dashboard_api_smoke_shared_utility_adoption, build_dashboard_api_smoke_shared_utility_adoption_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_dashboard_api_smoke_shared_utility_adoption(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_dashboard_api_smoke_shared_utility_adoption_metadata(project_id=project_id)
        warning = None
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            warning = "Dashboard API Smoke Shared Utility Adoption is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy."
        return 200, _ok(api_preview_payload(report) if warning is None else api_preview_payload(report) | {"warnings": [warning]})

    if parts == ['source-surface', 'dashboard-review-component-extraction-pilot']:
        from dashboard_review_component_extraction_pilot import api_preview_payload, build_dashboard_review_component_extraction_pilot, build_dashboard_review_component_extraction_pilot_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_dashboard_review_component_extraction_pilot(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_dashboard_review_component_extraction_pilot_metadata(project_id=project_id)
        warning = None
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            warning = "Dashboard Review Component Extraction Pilot is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy."
        return 200, _ok(api_preview_payload(report) if warning is None else api_preview_payload(report) | {"warnings": [warning]})

    if parts == ['source-surface', 'smoke-check-helper-extraction-pilot']:
        from smoke_check_helper_extraction_pilot import api_preview_payload, build_smoke_check_helper_extraction_pilot, build_smoke_check_helper_extraction_pilot_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_smoke_check_helper_extraction_pilot(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_smoke_check_helper_extraction_pilot_metadata(project_id=project_id)
        warning = None
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            warning = "Smoke Check Helper Extraction Pilot is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy."
        return 200, _ok(api_preview_payload(report) if warning is None else api_preview_payload(report) | {"warnings": [warning]})

    from api_server_dispatch_shared import build_manual_preview_dispatch_payload, build_route_table_preview_payload, source_surface_route_matches
    if source_surface_route_matches(parts, "api-preview-adapter-extraction-pilot"):
        from api_preview_adapter_extraction_pilot import api_preview_payload, build_api_preview_adapter_extraction_pilot, build_api_preview_adapter_extraction_pilot_metadata

        payload = build_manual_preview_dispatch_payload(
            query,
            project_root=Path(__file__).resolve().parents[1],
            metadata_builder=build_api_preview_adapter_extraction_pilot_metadata,
            report_builder=build_api_preview_adapter_extraction_pilot,
            payload_builder=api_preview_payload,
            warning="API Preview Adapter Extraction Pilot is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.",
        )
        return 200, _ok(payload)

    if source_surface_route_matches(parts, "api-preview-adapter-backfill"):
        from api_preview_adapter_backfill import api_preview_payload, build_api_preview_adapter_backfill, build_api_preview_adapter_backfill_metadata

        payload = build_manual_preview_dispatch_payload(
            query,
            project_root=Path(__file__).resolve().parents[1],
            metadata_builder=build_api_preview_adapter_backfill_metadata,
            report_builder=build_api_preview_adapter_backfill,
            payload_builder=api_preview_payload,
            warning="API Preview Adapter Backfill is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.",
        )
        return 200, _ok(payload)

    route_table_payload = build_route_table_preview_payload(parts, query, project_root=Path(__file__).resolve().parents[1])
    if route_table_payload is not None:
        return 200, _ok(route_table_payload)

    if source_surface_route_matches(parts, "api-server-dispatch-route-table-safety-parity"):
        from api_server_dispatch_route_table_safety_parity import api_preview_payload, build_api_server_dispatch_route_table_safety_parity, build_api_server_dispatch_route_table_safety_parity_metadata

        payload = build_manual_preview_dispatch_payload(
            query,
            project_root=Path(__file__).resolve().parents[1],
            metadata_builder=build_api_server_dispatch_route_table_safety_parity_metadata,
            report_builder=build_api_server_dispatch_route_table_safety_parity,
            payload_builder=api_preview_payload,
            warning="API Server Dispatch Route Table Safety Parity is GET preview-only. It does not execute generated fixtures, spawn subprocesses, write or delete source, activate generated wiring, authorize release, or expand autonomy.",
        )
        return 200, _ok(payload)

    if parts == ['source-surface', 'autonomy-phase-zero-observation-contract']:
        from autonomy_phase_zero_observation_contract import build_autonomy_phase_zero_observation_contract, build_autonomy_phase_zero_observation_contract_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_autonomy_phase_zero_observation_contract(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_autonomy_phase_zero_observation_contract_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Autonomy Phase 0 Observation-Only Contract is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["dashboard", "shell-performance-stabilization"]:
        from dashboard_shell_performance_stabilization import build_dashboard_shell_performance_stabilization, build_dashboard_shell_performance_stabilization_metadata

        project_id = query.get("project", ["eidolon"])[0]
        measure = _query_bool(query, "measure", False)
        report = build_dashboard_shell_performance_stabilization(None, measure_routes=True) if measure else build_dashboard_shell_performance_stabilization_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Dashboard shell performance stabilization GET is preview-only by default. Measured route checks require explicit measure=true and still do not apply patches, run install-release, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["dashboard", "slow-route-cohort-repair"]:
        from dashboard_slow_route_cohort_repair import build_dashboard_slow_route_cohort_repair, build_dashboard_slow_route_cohort_repair_metadata

        project_id = query.get("project", ["eidolon"])[0]
        measure = _query_bool(query, "measure", False)
        report = build_dashboard_slow_route_cohort_repair(project_id if False else None, measure_routes=measure) if measure else build_dashboard_slow_route_cohort_repair_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Slow dashboard route cohort repair is GET preview-only and does not execute governed actions, apply patches, write memory, create releases, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["doctor", "deep-diagnostic-latency-budget-repair"]:
        project_id = query.get("project", ["eidolon"])[0]
        report = build_doctor_deep_diagnostic_latency_budget_repair_metadata(project_id=project_id)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Deep diagnostic latency repair is GET preview-only and does not execute live work, apply patches, write memory, create releases, or expand autonomy.")
        return 200, _ok(report)


    if parts == ["installed-tree-cleanup", "historical-verification-reconciliation"]:
        from installed_tree_cleanup_historical_verification_reconciliation import build_installed_tree_cleanup_historical_verification_reconciliation

        project_id = query.get("project", ["eidolon"])[0]
        measure_startup = _query_bool(query, "measure_startup", False)
        report = build_installed_tree_cleanup_historical_verification_reconciliation(project_id=project_id, measure_startup=measure_startup)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Installed-tree cleanup report is review-only; it does not delete files, authorize release, or expand autonomy.")
        return 200, _ok(report)

    if parts == ["installed-tree-cleanup", "enforcement"]:
        from installed_tree_cleanup_enforcement import build_installed_tree_cleanup_enforcement, build_installed_tree_cleanup_enforcement_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_installed_tree_cleanup_enforcement(None, inspect_sources=inspect_sources, apply_cleanup=False) if inspect_sources else build_installed_tree_cleanup_enforcement_metadata(project_id=project_id)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Installed-tree cleanup enforcement GET is preview-only. Deletion requires POST with exact confirmation and never deletes active imported modules, runtime/private data, activates generated wiring, authorizes release, or expands autonomy.")
        return 200, _ok(report)

    if parts == ["repair-suggestions", "preview"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_bounded_repair_suggestions(project_id=project_id))

    if parts == ["repair-suggestions"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_repair_suggestions(project_id=project_id))

    if parts == ["patch-integrity"]:
        return 200, _ok(build_patch_integrity_report())

    if parts == ["project-snapshot", "preview"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_bounded_project_snapshot(project_id=project_id))

    if parts == ["project-snapshot"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_snapshot(project_id=project_id))

    if parts == ["recovery-drill"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_recovery_drill(project_id=project_id))

    if parts == ["hardening-report", "preview"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_bounded_hardening_report(project_id=project_id))

    if parts == ["hardening-report"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_hardening_report(project_id=project_id))

    if parts == ["controlled-self-build", "lightweight-preview"]:
        project_id = query.get("project", ["eidolon"])[0]
        max_steps = int(query.get("steps", ["1"])[0] or 1)
        report = build_controlled_self_build_lightweight_preview(project_id=project_id, max_steps=max_steps)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("Lightweight GET is preview-only. Use POST /api/controlled-self-build with explicit JSON confirmation for live work.")
        return 200, _ok(report)

    if parts == ["controlled-self-build", "preview"]:
        project_id = query.get("project", ["eidolon"])[0]
        max_steps = int(query.get("steps", ["1"])[0] or 1)
        report = build_controlled_self_build_lightweight_preview(project_id=project_id, max_steps=max_steps)
        report.setdefault("warnings", []).append("Explicit preview endpoint. Use POST /api/controlled-self-build with LIVE_CONTROLLED_BUILD for any live work.")
        return 200, _ok(report)

    if parts == ["controlled-self-build"]:
        project_id = query.get("project", ["eidolon"])[0]
        max_steps = int(query.get("steps", ["1"])[0] or 1)
        report = build_controlled_self_build(project_id=project_id, max_steps=max_steps, live=False, approve_live=False, use_ai=False)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("GET is preview-only. Use POST /api/controlled-self-build with explicit JSON confirmation for live work.")
        return 200, _ok(report)

    if len(parts) >= 2 and parts[0] == "controlled-build":
        project_id = query.get("project", ["eidolon"])[0]
        action = parts[1]
        if action == "select-task":
            return 200, _ok(build_controlled_task_selection(project_id=project_id))
        if action == "plan-patch":
            return 200, _ok(build_patch_plan(project_id=project_id, target_version=query.get("version", ["10.0"])[0], save=False))
        if action == "workspace":
            return 200, _ok(patch_workspace_status())
        if action == "stage-patch":
            return 200, _ok(stage_controlled_patch(project_id=project_id, save=False))
        if action == "preview-diff":
            return 200, _ok(preview_staged_diff(project_id=project_id, stage_if_missing=False, save=False))
        if action == "readme-gate":
            return 200, _ok(readme_gate(project_id=project_id))

    if parts == ["supervised-dev-loop"]:
        raise ApiError(405, "GET /api/supervised-dev-loop is disabled. Use POST with explicit JSON confirmation for live behavior or dry_run=true for preview.")


    if parts == ["codebase-map"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_codebase_map(project_id=project_id))

    if parts == ["task-dependencies"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_task_dependencies(project_id=project_id))

    if parts == ["test-plan"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_test_plan(project_id=project_id))

    if parts == ["patch-risk"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_risk(project_id=project_id))

    if parts == ["patch-review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_review(project_id=project_id))

    if parts == ["project-memory-index"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_memory_index(project_id=project_id))

    if parts == ["workspace-status"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_status(project_id=project_id))

    if parts == ["cross-project-task-review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_cross_project_task_review(project_id=project_id))

    if parts == ["asymmetric-dev-loop"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_asymmetric_dev_loop(project_id=project_id))

    if parts == ["project-registry"]:
        return 200, _ok(build_project_registry(repair=False))

    if parts == ["project-health"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_health(project_id=project_id, all_projects=_query_bool(query, "all", False)))

    if parts == ["command-profiles"]:
        return 200, _ok(build_command_profiles(save=False))

    if parts == ["workspace-dependency-map"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_dependency_map(project_id=project_id))

    if parts == ["workspace-task-inbox"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_task_inbox(project_id=project_id))

    if parts == ["project-context"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_context(project_id=project_id))

    if parts == ["workspace-timeline"]:
        return 200, _ok(build_workspace_timeline())

    if parts == ["workspace-dev-loop"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_dev_loop(project_id=project_id, live=False, save_timeline=False))

    if parts == ["workspace-registry-audit"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_registry_audit(project_id=project_id, archive_stale=False))

    if parts == ["workspace-repair-suggestions"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_repair_suggestions(project_id=project_id))

    if parts == ["project-registration-wizard"]:
        name = query.get("name", ["Workspace Project"])[0]
        root = query.get("root", [None])[0]
        project_id = query.get("project_id", [None])[0]
        return 200, _ok(build_project_registration_wizard(name=name, root=root, project_id=project_id))

    if parts == ["project-boundary-check"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_boundary_check(project_id=project_id))

    if parts == ["workspace-patch-plan"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_patch_plan(project_id=project_id, target_version=query.get("version", ["12.0"])[0], save=False))

    if parts == ["workspace-preview-diff"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_preview_diff(project_id=project_id, save=False))

    if parts == ["workspace-verify-latest"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_verify_latest(project_id=project_id, save=False))

    if parts == ["guarded-workspace-dev-loop"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_guarded_workspace_dev_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["patch-draft-status"], ["patch-drafts", "status"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_draft_status(project_id=project_id))

    if parts in (["patch-draft-request"], ["patch-drafts", "request"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_draft_request(project_id=project_id, target_version=query.get("version", ["20.0.1"])[0], task=query.get("task", [None])[0], intent=query.get("intent", [None])[0], risk_limit=query.get("risk_limit", ["medium"])[0], save=False))

    if parts in (["draft-patch"], ["patch-drafts", "draft"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_patch(project_id=project_id, save=False))

    if parts in (["patch-review-notes"], ["patch-drafts", "notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_review_notes(project_id=project_id, save=False))

    if parts in (["draft-diff"], ["patch-drafts", "diff"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_diff(project_id=project_id, save=False))

    if parts in (["draft-test-impact"], ["patch-drafts", "test-impact"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_test_impact(project_id=project_id, save=False))

    if parts in (["approval-gate"], ["patch-drafts", "approval-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_gate(project_id=project_id))

    if parts in (["human-approved-patch-loop"], ["patch-drafts", "human-approved-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_human_approved_patch_loop(project_id=project_id, approve_apply=False, dry_run=True, save=False))

    # v13.1-v14.0 draft review endpoints are read-only GET previews.
    if parts in (["patch-drafts", "quality"], ["draft-quality"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_quality(project_id=project_id, save=False))

    if parts in (["patch-drafts", "file-targets"], ["draft-file-targets"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_file_targets(project_id=project_id, save=False))

    if parts in (["patch-drafts", "intent-blocks"], ["draft-intent-blocks"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_intent_blocks(project_id=project_id, save=False))

    if parts in (["patch-drafts", "conflicts"], ["draft-conflicts"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_conflicts(project_id=project_id, save=False))

    if parts in (["patch-drafts", "verification-bundle"], ["draft-verification-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_verification_bundle(project_id=project_id, save=False))

    if parts in (["patch-drafts", "review-checklist"], ["draft-review-checklist"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_review_checklist(project_id=project_id, save=False))

    if parts in (["patch-drafts", "execution-report"], ["approved-draft-execution-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approved_draft_execution_report(project_id=project_id, save=False))

    if parts in (["patch-drafts", "review-loop"], ["review-centered-patch-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_review_centered_patch_loop(project_id=project_id, approve_apply=False, dry_run=True, save=False))

    if parts == ["patch-drafts", "review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_verification_bundle(project_id=project_id, save=False))

    # v14.1-v15.0 release pipeline endpoints are read-only GET previews.
    if parts in (["code-edit-proposal"], ["patch-drafts", "code-edit-proposal"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_edit_proposal(project_id=project_id, save=False))

    if parts in (["safe-rewrite-preview"], ["patch-drafts", "safe-rewrite-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_safe_rewrite_preview(project_id=project_id, save=False))

    if parts in (["generate-code-patch"], ["patch-drafts", "generated-code-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_generated_code_patch(project_id=project_id, save=False))

    if parts in (["test-suggestions"], ["patch-drafts", "test-suggestions"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_test_suggestions(project_id=project_id, save=False))

    if parts in (["inline-review-notes"], ["patch-drafts", "inline-review-notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_inline_review_note(project_id=project_id, save=False))

    if parts in (["approved-code-apply-report"], ["patch-drafts", "approved-code-apply-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_apply_approved_code_patch(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["prepare-release-package"], ["release", "package"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_prepare_release_package(project_id=project_id, package_name=query.get("package", [None])[0], save=False))

    if parts in (["release-readiness"], ["release", "readiness"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_readiness(project_id=project_id, save=False))

    if parts in (["human-approved-release-loop"], ["release", "human-approved-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_human_approved_release_loop(project_id=project_id, approve_apply=False, dry_run=True, save=False))

    # v15.1-v16.0 generated code release endpoints are read-only GET previews.
    if parts in (["code-patch-status"], ["code-patches", "status"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_patch_status(project_id=project_id, save=False))

    if parts in (["symbol-scan"], ["code-patches", "symbol-scan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_symbol_scan(project_id=project_id, save=False))

    if parts in (["rewrite-plan"], ["code-patches", "rewrite-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_rewrite_plan(project_id=project_id, save=False))

    if parts in (["rewrite-conflicts"], ["code-patches", "rewrite-conflicts"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_rewrite_conflicts(project_id=project_id, save=False))

    if parts in (["code-patch-diff-bundle"], ["code-patches", "diff-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_patch_diff_bundle(project_id=project_id, save=False))

    if parts in (["apply-code-patch-transaction"], ["code-patches", "apply-transaction"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_apply_code_patch_transaction(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["semantic-checks"], ["code-patches", "semantic-checks"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_semantic_checks(project_id=project_id, save=False))

    if parts in (["release-artifact"], ["release", "artifact"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_artifact(project_id=project_id, package_name=query.get("package", [None])[0], save=False))

    if parts in (["release-audit-trail"], ["release", "audit-trail"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_audit_trail(project_id=project_id, save=False))

    if parts in (["generated-code-release-loop"], ["release", "generated-code-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_generated_code_release_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    # v16.1-v17.0 AI-assisted code patch endpoints are read-only GET previews.
    if parts in (["task-to-code-patch"], ["code-patches", "task-to-code-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_task_to_code_patch(project_id=project_id, save=False))

    if parts in (["code-context"], ["code-patches", "code-context"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_context(project_id=project_id, save=False))

    if parts in (["patch-prompt"], ["code-patches", "patch-prompt"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_prompt(project_id=project_id, save=False))

    if parts in (["parse-generated-edits"], ["code-patches", "parse-generated-edits"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_parse_generated_edits(project_id=project_id, save=False))

    if parts in (["edit-consistency"], ["code-patches", "edit-consistency"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_edit_consistency(project_id=project_id, save=False))

    if parts in (["ai-code-patch-dry-run"], ["code-patches", "ai-dry-run"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_ai_code_patch_dry_run(project_id=project_id, save=False))

    if parts in (["patch-failure-analysis"], ["code-patches", "failure-analysis"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_failure_analysis(project_id=project_id, save=False))

    if parts in (["patch-learning-notes"], ["code-patches", "learning-notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_learning_notes(project_id=project_id, save=False))

    if parts in (["ai-assisted-code-patch-loop"], ["code-patches", "ai-assisted-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_ai_assisted_code_patch_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    # v17.1-v18.0 validated AI code patch endpoints are read-only GET previews.
    if parts in (["refine-patch-objective"], ["code-patches", "objective-refinement"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_objective_refinement(project_id=project_id, save=False))

    if parts in (["rank-code-context"], ["code-patches", "context-ranking"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_context_ranking(project_id=project_id, save=False))

    if parts in (["patch-safety-envelope"], ["code-patches", "safety-envelope"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_safety_envelope(project_id=project_id, save=False))

    if parts in (["validate-generated-patch"], ["code-patches", "validate-generated-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_generated_patch_validation(project_id=project_id, save=False))

    if parts in (["patch-simulation"], ["code-patches", "simulation"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_simulation(project_id=project_id, save=False))

    if parts in (["test-stub-plan"], ["code-patches", "test-stub-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_test_stub_plan(project_id=project_id, save=False))

    if parts in (["patch-review-score"], ["code-patches", "review-score"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_review_score(project_id=project_id, save=False))

    if parts in (["patch-recovery-plan"], ["code-patches", "recovery-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_recovery_plan(project_id=project_id, save=False))

    if parts in (["validated-ai-code-patch-loop"], ["code-patches", "validated-ai-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_validated_ai_code_patch_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    # v18.1-v19.0 approval-to-release endpoints are read-only GET previews.
    if parts in (["ai-patch-review-bundle"], ["code-patches", "review-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_ai_patch_review_bundle(project_id=project_id, save=False))

    if parts in (["ai-patch-review-integrity"], ["code-patches", "review-integrity"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_review_bundle_integrity(project_id=project_id, save=False))

    if parts in (["approval-ready"], ["code-patches", "approval-ready"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_ready(project_id=project_id, save=False))

    if parts in (["approval-ledger"], ["code-patches", "approval-ledger"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_ledger(project_id=project_id, save=False))

    if parts in (["apply-validated-ai-patch"], ["code-patches", "apply-validated-ai-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_apply_validated_ai_patch(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["post-apply-review"], ["code-patches", "post-apply-review"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_post_apply_review(project_id=project_id, save=False))

    if parts in (["package-build-plan"], ["release", "package-build-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_package_build_plan(project_id=project_id, package_name=package_name, save=False))

    if parts in (["approval-to-release-loop"], ["release", "approval-to-release-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_to_release_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["release-manifest-integrity"], ["release", "manifest-integrity"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False))

    if parts in (["package-inventory"], ["release", "package-inventory"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_package_inventory(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["package-checksums"], ["release", "package-checksums"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_package_checksums(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["release-notes"], ["release", "notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_notes(project_id=project_id, save=False))

    if parts in (["release-handoff-report"], ["release", "handoff"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_release_handoff_report(project_id=project_id, package_name=package_name, save=False))

    if parts in (["build-release-zip"], ["release", "build-zip"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_release_zip(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False))

    if parts in (["verify-release-unzip"], ["release", "verify-unzip"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_verify_release_unzip(project_id=project_id, package_name=package_name, save=False))

    if parts in (["release-pipeline-audit"], ["release", "pipeline-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_release_pipeline_audit(project_id=project_id, package_name=package_name, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["verified-release-package-loop"], ["release", "verified-package-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_verified_release_package_loop(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["release-profiles"], ["release", "profiles"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_profiles(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["package-privacy-scan"], ["release", "privacy-scan"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_package_privacy_scan(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["portable-metadata-check"], ["release", "portable-metadata"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_portable_metadata_check(project_id=project_id, save=False))

    if parts in (["first-run-check"], ["release", "first-run-check"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_first_run_check(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["dependency-advisor"], ["release", "dependency-advisor"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dependency_advisor(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["upgrade-notes"], ["release", "upgrade-notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_upgrade_notes(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["runtime-migration-check"], ["release", "runtime-migration"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_runtime_migration_check(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["release-install-verification"], ["release", "install-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_release_install_verification(project_id=project_id, package_name=package_name, run_smoke=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["verified-installable-release-loop"], ["release", "verified-installable-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_verified_installable_release_loop(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["smoke-runtime-hardening"], ["release", "smoke-runtime-hardening"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_smoke_runtime_hardening(project_id=project_id, tier=query.get("tier", ["full"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["external-zip-install-verification"], ["release", "external-zip-install-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), run_compile=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["deterministic-release-manifest"], ["release", "deterministic-release-manifest"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["update-dry-run-plan"], ["release", "update-dry-run-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["atomic-source-update"], ["release", "atomic-source-update"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_atomic_source_update(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), expected_manifest_hash=query.get("expected_manifest_hash", [None])[0], confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["runtime-migration-assistant"], ["release", "runtime-migration-assistant"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_runtime_migration_assistant(project_id=project_id, confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["route-safety-harness"], ["release", "route-safety-harness"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_route_safety_harness(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["release-dashboard-command-center"], ["release", "dashboard-command-center"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_dashboard_command_center(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["clean-room-install-harness"], ["release", "clean-room-install-harness"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_clean_room_install_harness(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), run_smoke_tier=query.get("tier", ["fast"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["verified-self-update-release-pipeline"], ["release", "verified-self-update-release-pipeline"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_verified_self_update_release_pipeline(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), confirm=False, dry_run=True, run_clean_room=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["trial-upgrade-from-zip"], ["release", "trial-upgrade-from-zip"], ["release", "trial-upgrade"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_trial_upgrade_harness(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), run_smoke_tier=query.get("tier", ["fast"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["backup-rollback-drill"], ["release", "backup-rollback-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_backup_rollback_drill(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["update-collision-detector"], ["release", "update-collision-detector"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_update_collision_detector(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["version-registry-report"], ["release", "version-registry-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_version_registry_report(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["release-provenance-report"], ["release", "provenance-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_release_provenance_report(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["dashboard-upgrade-wizard-preview"], ["release", "dashboard-upgrade-wizard-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dashboard_upgrade_wizard_preview(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["api-upgrade-wizard-preview"], ["release", "api-upgrade-wizard-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_api_upgrade_wizard_preview(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["staged-apply-drill"], ["release", "staged-apply-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_staged_apply_drill(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["real-apply-guard-rails"], ["release", "real-apply-guard-rails"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_real_apply_guard_rails(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), expected_manifest_hash=query.get("expected_manifest_hash", [None])[0], confirm_phrase=query.get("confirm_phrase", [""])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["real-apply-rollback-verification"], ["release", "real-apply-rollback-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_real_apply_rollback_verification(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["self-update-ux-polish"], ["release", "self-update-ux-polish"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_self_update_ux_polish(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["v23-readiness-gate"], ["release", "v23-readiness-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_v23_readiness_gate(project_id=project_id, package_name=package_name, zip_path=_query_release_zip_path(query), run_heavy=query.get("run_heavy", ["false"])[0].lower() == "true", save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["controlled-self-maintenance-loop"], ["release", "controlled-self-maintenance-loop"], ["autonomy", "controlled-self-maintenance-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = sm_v45.build_controlled_self_maintenance_loop(project_id=project_id, goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False)
        return 200, _ok(report)

    if parts in (["self-maintenance", "self-maintenance-cycle-schema"], ["release", "self-maintenance-cycle-schema"], ["autonomy", "self-maintenance-cycle-schema"], ["self-maintenance-cycle-schema"]):
        return 200, _ok(sm_v45.build_self_maintenance_cycle_schema(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "self-maintenance-plan"], ["release", "self-maintenance-plan"], ["autonomy", "self-maintenance-plan"], ["self-maintenance-plan"]):
        return 200, _ok(sm_v45.build_self_maintenance_plan(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "self-maintenance-sandbox-cycle"], ["release", "self-maintenance-sandbox-cycle"], ["autonomy", "self-maintenance-sandbox-cycle"], ["self-maintenance-sandbox-cycle"]):
        return 200, _ok(sm_v45.build_self_maintenance_sandbox_cycle(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-checkpoint-binder"], ["release", "maintenance-checkpoint-binder"], ["autonomy", "maintenance-checkpoint-binder"], ["maintenance-checkpoint-binder"]):
        return 200, _ok(sm_v45.build_maintenance_checkpoint_binder(project_id=query.get("project", ["eidolon"])[0], cycle_id=query.get("cycle_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "self-maintenance-apply-dry-run"], ["release", "self-maintenance-apply-dry-run"], ["autonomy", "self-maintenance-apply-dry-run"], ["self-maintenance-apply-dry-run"]):
        return 200, _ok(sm_v45.build_self_maintenance_apply_dry_run(project_id=query.get("project", ["eidolon"])[0], cycle_id=query.get("cycle_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "self-maintenance-apply-handoff"], ["release", "self-maintenance-apply-handoff"], ["autonomy", "self-maintenance-apply-handoff"], ["self-maintenance-apply-handoff"]):
        return 200, _ok(sm_v45.build_self_maintenance_apply_handoff(project_id=query.get("project", ["eidolon"])[0], cycle_id=query.get("cycle_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "post-maintenance-verification-summary"], ["release", "post-maintenance-verification-summary"], ["autonomy", "post-maintenance-verification-summary"], ["post-maintenance-verification-summary"]):
        return 200, _ok(sm_v45.build_post_maintenance_verification_summary(project_id=query.get("project", ["eidolon"])[0], cycle_id=query.get("cycle_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "self-maintenance-fixture-drill"], ["release", "self-maintenance-fixture-drill"], ["autonomy", "self-maintenance-fixture-drill"], ["self-maintenance-fixture-drill"]):
        return 200, _ok(sm_v45.build_self_maintenance_fixture_drill(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v45-self-maintenance-gate"], ["release", "pre-v45-self-maintenance-gate"], ["autonomy", "pre-v45-self-maintenance-gate"], ["pre-v45-self-maintenance-gate"]):
        return 200, _ok(sm_v45.build_pre_v45_self_maintenance_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))

    if parts in (["self-maintenance", "maintenance-task-record-schema"], ["release", "maintenance-task-record-schema"], ["autonomy", "maintenance-task-record-schema"], ["maintenance-task-record-schema"]):
        return 200, _ok(sm_v45.build_maintenance_task_record_schema(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-priority-risk-scoring"], ["release", "maintenance-task-priority-risk-scoring"], ["autonomy", "maintenance-task-priority-risk-scoring"], ["maintenance-task-priority-risk-scoring"]):
        return 200, _ok(sm_v45.build_maintenance_task_priority_risk_scoring(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-queue-registry"], ["release", "maintenance-task-queue-registry"], ["autonomy", "maintenance-task-queue-registry"], ["maintenance-task-queue-registry"]):
        return 200, _ok(sm_v45.build_maintenance_task_queue_registry(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-selection-policy"], ["release", "maintenance-task-selection-policy"], ["autonomy", "maintenance-task-selection-policy"], ["maintenance-task-selection-policy"]):
        return 200, _ok(sm_v45.build_maintenance_task_selection_policy(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-cycle-orchestrator"], ["release", "maintenance-task-cycle-orchestrator"], ["autonomy", "maintenance-task-cycle-orchestrator"], ["maintenance-task-cycle-orchestrator"]):
        return 200, _ok(sm_v45.build_maintenance_task_cycle_orchestrator(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-checkpoint-binding"], ["release", "maintenance-task-checkpoint-binding"], ["autonomy", "maintenance-task-checkpoint-binding"], ["maintenance-task-checkpoint-binding"]):
        return 200, _ok(sm_v45.build_maintenance_task_checkpoint_binding(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], task_id=query.get("task_id", [None])[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-source-apply-lockout"], ["release", "maintenance-task-source-apply-lockout"], ["autonomy", "maintenance-task-source-apply-lockout"], ["maintenance-task-source-apply-lockout"]):
        return 200, _ok(sm_v45.build_maintenance_task_source_apply_lockout(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-dashboard-api-views"], ["release", "maintenance-task-dashboard-api-views"], ["autonomy", "maintenance-task-dashboard-api-views"], ["maintenance-task-dashboard-api-views"]):
        return 200, _ok(sm_v45.build_maintenance_task_dashboard_api_views(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-fixture-drill"], ["release", "maintenance-task-fixture-drill"], ["autonomy", "maintenance-task-fixture-drill"], ["maintenance-task-fixture-drill"]):
        return 200, _ok(sm_v45.build_maintenance_task_fixture_drill(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v46-maintenance-queue-gate"], ["release", "pre-v46-maintenance-queue-gate"], ["autonomy", "pre-v46-maintenance-queue-gate"], ["pre-v46-maintenance-queue-gate"]):
        return 200, _ok(sm_v45.build_pre_v46_maintenance_queue_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "controlled-self-maintenance-work-queue"], ["release", "controlled-self-maintenance-work-queue"], ["autonomy", "controlled-self-maintenance-work-queue"], ["controlled-self-maintenance-work-queue"]):
        return 200, _ok(sm_v45.build_controlled_self_maintenance_work_queue(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "autonomy-queue-report-cache"], ["release", "autonomy-queue-report-cache"], ["autonomy", "queue-report-cache"], ["autonomy-queue-report-cache"]):
        return 200, _ok(sm_v45.build_autonomy_queue_report_cache(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-task-drilldown"], ["release", "maintenance-task-drilldown"], ["autonomy", "maintenance-task-drilldown"], ["maintenance-task-drilldown"]):
        return 200, _ok(sm_v45.build_maintenance_task_drilldown_view(project_id=query.get("project", ["eidolon"])[0], task_id=query.get("task_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "queue-stale-state-warnings"], ["release", "queue-stale-state-warnings"], ["autonomy", "queue-stale-state-warnings"], ["queue-stale-state-warnings"]):
        return 200, _ok(sm_v45.build_maintenance_queue_stale_state_warnings(project_id=query.get("project", ["eidolon"])[0], task_id=query.get("task_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "maintenance-runtime-privacy-audit"], ["release", "maintenance-runtime-privacy-audit"], ["autonomy", "maintenance-runtime-privacy-audit"], ["maintenance-runtime-privacy-audit"]):
        return 200, _ok(sm_v45.build_maintenance_runtime_privacy_audit(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "operator-command-palette"], ["release", "operator-command-palette"], ["autonomy", "operator-command-palette"], ["operator-command-palette"]):
        return 200, _ok(sm_v45.build_operator_command_palette_report(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "dashboard-api-queue-parity"], ["release", "dashboard-api-queue-parity"], ["autonomy", "dashboard-api-queue-parity"], ["dashboard-api-queue-parity"]):
        return 200, _ok(sm_v45.build_dashboard_api_queue_parity(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "queue-verification-receipt"], ["release", "queue-verification-receipt"], ["autonomy", "queue-verification-receipt"], ["queue-verification-receipt"]):
        return 200, _ok(sm_v45.build_queue_verification_receipt(project_id=query.get("project", ["eidolon"])[0], task_id=query.get("task_id", [None])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "dashboard-accessibility-compact-layout"], ["release", "dashboard-accessibility-compact-layout"], ["autonomy", "dashboard-accessibility-compact-layout"], ["dashboard-accessibility-compact-layout"]):
        return 200, _ok(sm_v45.build_dashboard_accessibility_compact_layout(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v47-attention-scheduler-gate"], ["release", "pre-v47-attention-scheduler-gate"], ["autonomy", "pre-v47-attention-scheduler-gate"], ["pre-v47-attention-scheduler-gate"]):
        return 200, _ok(sm_v45.build_pre_v47_attention_scheduler_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "attention-scheduler"], ["release", "attention-scheduler"], ["autonomy", "attention-scheduler"], ["attention-scheduler"]):
        return 200, _ok(sm_v45.build_controlled_attention_scheduler(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "attention-selection-receipt"], ["release", "attention-selection-receipt"], ["autonomy", "attention-selection-receipt"], ["attention-selection-receipt"]):
        return 200, _ok(sm_v45.build_attention_selection_receipt(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "pre-v47-1-attention-receipt-gate"], ["release", "pre-v47-1-attention-receipt-gate"], ["autonomy", "pre-v47-1-attention-receipt-gate"], ["pre-v47-1-attention-receipt-gate"]):
        return 200, _ok(sm_v45.build_pre_v47_1_attention_receipt_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "attention-budget-ledger"], ["release", "attention-budget-ledger"], ["autonomy", "attention-budget-ledger"], ["attention-budget-ledger"]):
        return 200, _ok(sm_v45.build_attention_budget_ledger(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "deferred-task-memory"], ["release", "deferred-task-memory"], ["autonomy", "deferred-task-memory"], ["deferred-task-memory"]):
        return 200, _ok(sm_v45.build_deferred_task_memory(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "blocked-task-handling"], ["release", "blocked-task-handling"], ["autonomy", "blocked-task-handling"], ["blocked-task-handling"]):
        return 200, _ok(sm_v45.build_blocked_task_handling(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "attention-resume-context"], ["release", "attention-resume-context"], ["autonomy", "attention-resume-context"], ["attention-resume-context"]):
        return 200, _ok(sm_v45.build_attention_resume_context(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "attention-dashboard-polish"], ["release", "attention-dashboard-polish"], ["autonomy", "attention-dashboard-polish"], ["attention-dashboard-polish"]):
        return 200, _ok(sm_v45.build_attention_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "attention-api-parity-gate"], ["release", "attention-api-parity-gate"], ["autonomy", "attention-api-parity-gate"], ["attention-api-parity-gate"]):
        return 200, _ok(sm_v45.build_attention_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "reflection-hooks-read-only"], ["release", "reflection-hooks-read-only"], ["autonomy", "reflection-hooks-read-only"], ["reflection-hooks-read-only"]):
        return 200, _ok(sm_v45.build_reflection_hooks_read_only(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "pre-v48-reflection-gate"], ["release", "pre-v48-reflection-gate"], ["autonomy", "pre-v48-reflection-gate"], ["pre-v48-reflection-gate"]):
        return 200, _ok(sm_v45.build_pre_v48_reflection_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "reflection-memory-loop"], ["release", "reflection-memory-loop"], ["autonomy", "reflection-memory-loop"], ["reflection-memory-loop"]):
        return 200, _ok(sm_v45.build_controlled_reflection_memory_loop(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))

    if parts in (["self-maintenance", "reflection-review-receipts"], ["release", "reflection-review-receipts"], ["autonomy", "reflection-review-receipts"], ["reflection-review-receipts"]):
        return 200, _ok(sm_v45.build_reflection_review_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "reflection-candidate-deduplication"], ["release", "reflection-candidate-deduplication"], ["autonomy", "reflection-candidate-deduplication"], ["reflection-candidate-deduplication"]):
        return 200, _ok(sm_v45.build_reflection_candidate_deduplication(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "reflection-rejection-memory"], ["release", "reflection-rejection-memory"], ["autonomy", "reflection-rejection-memory"], ["reflection-rejection-memory"]):
        return 200, _ok(sm_v45.build_reflection_rejection_memory_runtime(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "reflection-promotion-drafts"], ["release", "reflection-promotion-drafts"], ["autonomy", "reflection-promotion-drafts"], ["reflection-promotion-drafts"]):
        return 200, _ok(sm_v45.build_reflection_promotion_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-safety-classifier"], ["release", "memory-safety-classifier"], ["autonomy", "memory-safety-classifier"], ["memory-safety-classifier"]):
        return 200, _ok(sm_v45.build_memory_safety_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "reflection-dashboard-polish"], ["release", "reflection-dashboard-polish"], ["autonomy", "reflection-dashboard-polish"], ["reflection-dashboard-polish"]):
        return 200, _ok(sm_v45.build_reflection_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "reflection-api-parity-gate"], ["release", "reflection-api-parity-gate"], ["autonomy", "reflection-api-parity-gate"], ["reflection-api-parity-gate"]):
        return 200, _ok(sm_v45.build_reflection_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "reflection-privacy-package-hardening"], ["release", "reflection-privacy-package-hardening"], ["autonomy", "reflection-privacy-package-hardening"], ["reflection-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_reflection_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v49-identity-continuity-gate"], ["release", "pre-v49-identity-continuity-gate"], ["autonomy", "pre-v49-identity-continuity-gate"], ["pre-v49-identity-continuity-gate"]):
        return 200, _ok(sm_v45.build_pre_v49_identity_continuity_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "identity-continuity-layer"], ["release", "identity-continuity-layer"], ["autonomy", "identity-continuity-layer"], ["identity-continuity-layer"]):
        return 200, _ok(sm_v45.build_identity_continuity_layer(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "identity-receipts"], ["release", "identity-receipts"], ["autonomy", "identity-receipts"], ["identity-receipts"]):
        return 200, _ok(sm_v45.build_identity_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "pre-v49-1-identity-receipts-gate"], ["release", "pre-v49-1-identity-receipts-gate"], ["autonomy", "pre-v49-1-identity-receipts-gate"], ["pre-v49-1-identity-receipts-gate"]):
        return 200, _ok(sm_v45.build_pre_v49_1_identity_receipts_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))

    if parts in (["self-maintenance", "stable-principles-ledger"], ["release", "stable-principles-ledger"], ["autonomy", "stable-principles-ledger"], ["stable-principles-ledger"]):
        return 200, _ok(sm_v45.build_stable_principles_ledger(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "identity-drift-classifier"], ["release", "identity-drift-classifier"], ["autonomy", "identity-drift-classifier"], ["identity-drift-classifier"]):
        return 200, _ok(sm_v45.build_identity_drift_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "identity-snapshot-comparison"], ["release", "identity-snapshot-comparison"], ["autonomy", "identity-snapshot-comparison"], ["identity-snapshot-comparison"]):
        return 200, _ok(sm_v45.build_identity_snapshot_comparison(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "operator-identity-review-drafts"], ["release", "operator-identity-review-drafts"], ["autonomy", "operator-identity-review-drafts"], ["operator-identity-review-drafts"]):
        return 200, _ok(sm_v45.build_operator_identity_review_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "identity-dashboard-polish"], ["release", "identity-dashboard-polish"], ["autonomy", "identity-dashboard-polish"], ["identity-dashboard-polish"]):
        return 200, _ok(sm_v45.build_identity_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "identity-api-parity-gate"], ["release", "identity-api-parity-gate"], ["autonomy", "identity-api-parity-gate"], ["identity-api-parity-gate"]):
        return 200, _ok(sm_v45.build_identity_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "identity-privacy-package-hardening"], ["release", "identity-privacy-package-hardening"], ["autonomy", "identity-privacy-package-hardening"], ["identity-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_identity_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v50-durable-memory-gate"], ["release", "pre-v50-durable-memory-gate"], ["autonomy", "pre-v50-durable-memory-gate"], ["pre-v50-durable-memory-gate"]):
        return 200, _ok(sm_v45.build_pre_v50_durable_memory_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "durable-memory-promotion"], ["release", "durable-memory-promotion"], ["autonomy", "durable-memory-promotion"], ["durable-memory-promotion"]):
        return 200, _ok(sm_v45.build_supervised_durable_memory_promotion(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))


    if parts in (["self-maintenance", "memory-promotion-receipts"], ["release", "memory-promotion-receipts"], ["autonomy", "memory-promotion-receipts"], ["memory-promotion-receipts"]):
        return 200, _ok(sm_v45.build_memory_promotion_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-promotion-deduplication"], ["release", "memory-promotion-deduplication"], ["autonomy", "memory-promotion-deduplication"], ["memory-promotion-deduplication"]):
        return 200, _ok(sm_v45.build_memory_promotion_deduplication(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-rejection-runtime-ledger"], ["release", "memory-rejection-runtime-ledger"], ["autonomy", "memory-rejection-runtime-ledger"], ["memory-rejection-runtime-ledger"]):
        return 200, _ok(sm_v45.build_memory_rejection_runtime_ledger(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-promotion-confirmation-gate"], ["release", "memory-promotion-confirmation-gate"], ["autonomy", "memory-promotion-confirmation-gate"], ["memory-promotion-confirmation-gate"]):
        return 200, _ok(sm_v45.build_memory_promotion_confirmation_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], promotion_id=query.get("promotion_id", [None])[0], confirmation=query.get("confirmation", [None])[0], save=False))
    if parts in (["self-maintenance", "memory-removal-drafts"], ["release", "memory-removal-drafts"], ["autonomy", "memory-removal-drafts"], ["memory-removal-drafts"]):
        return 200, _ok(sm_v45.build_memory_removal_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-dashboard-polish"], ["release", "memory-dashboard-polish"], ["autonomy", "memory-dashboard-polish"], ["memory-dashboard-polish"]):
        return 200, _ok(sm_v45.build_memory_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "memory-api-parity-gate"], ["release", "memory-api-parity-gate"], ["autonomy", "memory-api-parity-gate"], ["memory-api-parity-gate"]):
        return 200, _ok(sm_v45.build_memory_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "memory-privacy-package-hardening"], ["release", "memory-privacy-package-hardening"], ["autonomy", "memory-privacy-package-hardening"], ["memory-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_memory_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v51-durable-write-gate"], ["release", "pre-v51-durable-write-gate"], ["autonomy", "pre-v51-durable-write-gate"], ["pre-v51-durable-write-gate"]):
        return 200, _ok(sm_v45.build_pre_v51_durable_write_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "durable-memory-write"], ["release", "durable-memory-write"], ["autonomy", "durable-memory-write"], ["durable-memory-write"]):
        return 200, _ok(sm_v45.build_controlled_durable_memory_write_path(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], promotion_id=query.get("promotion_id", [None])[0], confirmation=query.get("confirmation", [None])[0], execute=False, save=False))




    if parts in (["self-maintenance", "durable-memory-write-receipts"], ["release", "durable-memory-write-receipts"], ["autonomy", "durable-memory-write-receipts"], ["durable-memory-write-receipts"]):
        return 200, _ok(sm_v45.build_durable_memory_write_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-store-schema-hardening"], ["release", "memory-store-schema-hardening"], ["autonomy", "memory-store-schema-hardening"], ["memory-store-schema-hardening"]):
        return 200, _ok(sm_v45.build_memory_store_schema_hardening(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-read-path"], ["release", "memory-read-path"], ["autonomy", "memory-read-path"], ["memory-read-path"]):
        return 200, _ok(sm_v45.build_memory_read_path(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-search-filter"], ["release", "memory-search-filter"], ["autonomy", "memory-search-filter"], ["memory-search-filter"]):
        return 200, _ok(sm_v45.build_memory_search_filter(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], memory_type=query.get("memory_type", [None])[0], save=False))
    if parts in (["self-maintenance", "memory-correction-drafts"], ["release", "memory-correction-drafts"], ["autonomy", "memory-correction-drafts"], ["memory-correction-drafts"]):
        return 200, _ok(sm_v45.build_memory_correction_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-removal-confirmation-path"], ["release", "memory-removal-confirmation-path"], ["autonomy", "memory-removal-confirmation-path"], ["memory-removal-confirmation-path"]):
        return 200, _ok(sm_v45.build_memory_removal_confirmation_path(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], memory_id=query.get("memory_id", [None])[0], confirmation=query.get("confirmation", [None])[0], execute=False, save=False))
    if parts in (["self-maintenance", "memory-store-dashboard-polish"], ["release", "memory-store-dashboard-polish"], ["autonomy", "memory-store-dashboard-polish"], ["memory-store-dashboard-polish"]):
        return 200, _ok(sm_v45.build_memory_store_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "memory-store-api-parity-gate"], ["release", "memory-store-api-parity-gate"], ["autonomy", "memory-store-api-parity-gate"], ["memory-store-api-parity-gate"]):
        return 200, _ok(sm_v45.build_memory_store_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v52-recall-gate"], ["release", "pre-v52-recall-gate"], ["autonomy", "pre-v52-recall-gate"], ["pre-v52-recall-gate"]):
        return 200, _ok(sm_v45.build_pre_v52_recall_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "memory-recall-self-context"], ["release", "memory-recall-self-context"], ["autonomy", "memory-recall-self-context"], ["memory-recall-self-context"]):
        return 200, _ok(sm_v45.build_memory_recall_self_context(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))

    if parts in (["self-maintenance", "memory-recall-receipts"], ["release", "memory-recall-receipts"], ["autonomy", "memory-recall-receipts"], ["memory-recall-receipts"]):
        return 200, _ok(sm_v45.build_memory_recall_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "recall-conflict-resolver"], ["release", "recall-conflict-resolver"], ["autonomy", "recall-conflict-resolver"], ["recall-conflict-resolver"]):
        return 200, _ok(sm_v45.build_recall_conflict_resolver(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "stale-memory-handling"], ["release", "stale-memory-handling"], ["autonomy", "stale-memory-handling"], ["stale-memory-handling"]):
        return 200, _ok(sm_v45.build_stale_memory_handling(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "recall-scope-controls"], ["release", "recall-scope-controls"], ["autonomy", "recall-scope-controls"], ["recall-scope-controls"]):
        return 200, _ok(sm_v45.build_recall_scope_controls(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], scope=query.get("scope", ["project"])[0], save=False))
    if parts in (["self-maintenance", "recall-privacy-classifier"], ["release", "recall-privacy-classifier"], ["autonomy", "recall-privacy-classifier"], ["recall-privacy-classifier"]):
        return 200, _ok(sm_v45.build_recall_privacy_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "recall-dashboard-polish"], ["release", "recall-dashboard-polish"], ["autonomy", "recall-dashboard-polish"], ["recall-dashboard-polish"]):
        return 200, _ok(sm_v45.build_recall_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "recall-api-parity-gate"], ["release", "recall-api-parity-gate"], ["autonomy", "recall-api-parity-gate"], ["recall-api-parity-gate"]):
        return 200, _ok(sm_v45.build_recall_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "recall-privacy-package-hardening"], ["release", "recall-privacy-package-hardening"], ["autonomy", "recall-privacy-package-hardening"], ["recall-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_recall_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v53-memory-informed-planning-gate"], ["release", "pre-v53-memory-informed-planning-gate"], ["autonomy", "pre-v53-memory-informed-planning-gate"], ["pre-v53-memory-informed-planning-gate"]):
        return 200, _ok(sm_v45.build_pre_v53_memory_informed_planning_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "memory-informed-planning"], ["release", "memory-informed-planning"], ["autonomy", "memory-informed-planning"], ["memory-informed-planning"]):
        return 200, _ok(sm_v45.build_memory_informed_planning_loop(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "memory-informed-planning-receipts"], ["release", "memory-informed-planning-receipts"], ["autonomy", "memory-informed-planning-receipts"], ["memory-informed-planning-receipts"]):
        return 200, _ok(sm_v45.build_memory_informed_planning_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "plan-conflict-classifier"], ["release", "plan-conflict-classifier"], ["autonomy", "plan-conflict-classifier"], ["plan-conflict-classifier"]):
        return 200, _ok(sm_v45.build_plan_conflict_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "plan-revision-drafts"], ["release", "plan-revision-drafts"], ["autonomy", "plan-revision-drafts"], ["plan-revision-drafts"]):
        return 200, _ok(sm_v45.build_plan_revision_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], save=False))
    if parts in (["self-maintenance", "planning-scope-controls"], ["release", "planning-scope-controls"], ["autonomy", "planning-scope-controls"], ["planning-scope-controls"]):
        return 200, _ok(sm_v45.build_planning_scope_controls(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "planning-risk-budget"], ["release", "planning-risk-budget"], ["autonomy", "planning-risk-budget"], ["planning-risk-budget"]):
        return 200, _ok(sm_v45.build_planning_risk_budget(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "planning-dashboard-polish"], ["release", "planning-dashboard-polish"], ["autonomy", "planning-dashboard-polish"], ["planning-dashboard-polish"]):
        return 200, _ok(sm_v45.build_planning_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "planning-api-parity-gate"], ["release", "planning-api-parity-gate"], ["autonomy", "planning-api-parity-gate"], ["planning-api-parity-gate"]):
        return 200, _ok(sm_v45.build_planning_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "planning-privacy-package-hardening"], ["release", "planning-privacy-package-hardening"], ["autonomy", "planning-privacy-package-hardening"], ["planning-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_planning_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v54-action-planning-gate"], ["release", "pre-v54-action-planning-gate"], ["autonomy", "pre-v54-action-planning-gate"], ["pre-v54-action-planning-gate"]):
        return 200, _ok(sm_v45.build_pre_v54_action_planning_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "supervised-action-planning"], ["release", "supervised-action-planning"], ["autonomy", "supervised-action-planning"], ["supervised-action-planning"]):
        return 200, _ok(sm_v45.build_supervised_action_planning_loop(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))

    if parts in (["self-maintenance", "action-plan-receipts"], ["release", "action-plan-receipts"], ["autonomy", "action-plan-receipts"], ["action-plan-receipts"]):
        return 200, _ok(sm_v45.build_action_plan_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "action-step-classifier"], ["release", "action-step-classifier"], ["autonomy", "action-step-classifier"], ["action-step-classifier"]):
        return 200, _ok(sm_v45.build_action_step_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "action-dependency-graph"], ["release", "action-dependency-graph"], ["autonomy", "action-dependency-graph"], ["action-dependency-graph"]):
        return 200, _ok(sm_v45.build_action_dependency_graph(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "action-risk-budget"], ["release", "action-risk-budget"], ["autonomy", "action-risk-budget"], ["action-risk-budget"]):
        return 200, _ok(sm_v45.build_action_risk_budget(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "action-rehearsal-dry-run-preview"], ["release", "action-rehearsal-dry-run-preview"], ["autonomy", "action-rehearsal-dry-run-preview"], ["action-rehearsal-dry-run-preview"]):
        return 200, _ok(sm_v45.build_action_rehearsal_dry_run_preview(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "action-dashboard-polish"], ["release", "action-dashboard-polish"], ["autonomy", "action-dashboard-polish"], ["action-dashboard-polish"]):
        return 200, _ok(sm_v45.build_action_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "action-api-parity-gate"], ["release", "action-api-parity-gate"], ["autonomy", "action-api-parity-gate"], ["action-api-parity-gate"]):
        return 200, _ok(sm_v45.build_action_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "action-privacy-package-hardening"], ["release", "action-privacy-package-hardening"], ["autonomy", "action-privacy-package-hardening"], ["action-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_action_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v55-controlled-execution-gate"], ["release", "pre-v55-controlled-execution-gate"], ["autonomy", "pre-v55-controlled-execution-gate"], ["pre-v55-controlled-execution-gate"]):
        return 200, _ok(sm_v45.build_pre_v55_controlled_execution_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "controlled-action-execution-preview"], ["release", "controlled-action-execution-preview"], ["autonomy", "controlled-action-execution-preview"], ["controlled-action-execution-preview"]):
        return 200, _ok(sm_v45.build_controlled_action_execution_preview(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], action_plan_id=query.get("action_plan_id", [None])[0], confirmation=query.get("confirmation", [None])[0], execute_preview=False, save=False))
    if parts in (["self-maintenance", "execution-preview-receipts"], ["release", "execution-preview-receipts"], ["autonomy", "execution-preview-receipts"], ["execution-preview-receipts"]):
        return 200, _ok(sm_v45.build_execution_preview_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "execution-step-permission-classifier"], ["release", "execution-step-permission-classifier"], ["autonomy", "execution-step-permission-classifier"], ["execution-step-permission-classifier"]):
        return 200, _ok(sm_v45.build_execution_step_permission_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "read-only-command-allowlist"], ["release", "read-only-command-allowlist"], ["autonomy", "read-only-command-allowlist"], ["read-only-command-allowlist"]):
        return 200, _ok(sm_v45.build_read_only_command_allowlist(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "execution-sandbox-evidence-binder"], ["release", "execution-sandbox-evidence-binder"], ["autonomy", "execution-sandbox-evidence-binder"], ["execution-sandbox-evidence-binder"]):
        return 200, _ok(sm_v45.build_execution_sandbox_evidence_binder(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "execution-result-receipts"], ["release", "execution-result-receipts"], ["autonomy", "execution-result-receipts"], ["execution-result-receipts"]):
        return 200, _ok(sm_v45.build_execution_result_receipts(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "execution-dashboard-polish"], ["release", "execution-dashboard-polish"], ["autonomy", "execution-dashboard-polish"], ["execution-dashboard-polish"]):
        return 200, _ok(sm_v45.build_execution_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "execution-api-parity-gate"], ["release", "execution-api-parity-gate"], ["autonomy", "execution-api-parity-gate"], ["execution-api-parity-gate"]):
        return 200, _ok(sm_v45.build_execution_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "execution-privacy-package-hardening"], ["release", "execution-privacy-package-hardening"], ["autonomy", "execution-privacy-package-hardening"], ["execution-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_execution_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v56-read-only-execution-gate"], ["release", "pre-v56-read-only-execution-gate"], ["autonomy", "pre-v56-read-only-execution-gate"], ["pre-v56-read-only-execution-gate"]):
        return 200, _ok(sm_v45.build_pre_v56_read_only_execution_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "controlled-read-only-action-execution"], ["release", "controlled-read-only-action-execution"], ["autonomy", "controlled-read-only-action-execution"], ["controlled-read-only-action-execution"]):
        return 200, _ok(sm_v45.build_controlled_read_only_action_execution(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], confirmation=query.get("confirmation", [None])[0], execute=False, goal=query.get("goal", query.get("autonomy_goal", [None]))[0], query=query.get("q", query.get("query", query.get("goal", query.get("autonomy_goal", [None]))))[0], planning_scope=query.get("planning_scope", query.get("scope", ["release_maintenance"]))[0], save=False))
    if parts in (["self-maintenance", "read-only-execution-receipts"], ["release", "read-only-execution-receipts"], ["autonomy", "read-only-execution-receipts"], ["read-only-execution-receipts"]):
        return 200, _ok(sm_v45.build_read_only_execution_receipts(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "expanded-diagnostic-allowlist"], ["release", "expanded-diagnostic-allowlist"], ["autonomy", "expanded-diagnostic-allowlist"], ["expanded-diagnostic-allowlist"]):
        return 200, _ok(sm_v45.build_expanded_diagnostic_allowlist(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "read-only-output-classifier"], ["release", "read-only-output-classifier"], ["autonomy", "read-only-output-classifier"], ["read-only-output-classifier"]):
        return 200, _ok(sm_v45.build_read_only_output_classifier(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "diagnostic-evidence-binder"], ["release", "diagnostic-evidence-binder"], ["autonomy", "diagnostic-evidence-binder"], ["diagnostic-evidence-binder"]):
        return 200, _ok(sm_v45.build_diagnostic_evidence_binder(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], save=False))
    if parts in (["self-maintenance", "diagnostic-result-summaries"], ["release", "diagnostic-result-summaries"], ["autonomy", "diagnostic-result-summaries"], ["diagnostic-result-summaries"]):
        return 200, _ok(sm_v45.build_diagnostic_result_summaries(project_id=query.get("project", ["eidolon"])[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "read-only-execution-dashboard-polish"], ["release", "read-only-execution-dashboard-polish"], ["autonomy", "read-only-execution-dashboard-polish"], ["read-only-execution-dashboard-polish"]):
        return 200, _ok(sm_v45.build_read_only_execution_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "read-only-execution-api-parity-gate"], ["release", "read-only-execution-api-parity-gate"], ["autonomy", "read-only-execution-api-parity-gate"], ["read-only-execution-api-parity-gate"]):
        return 200, _ok(sm_v45.build_read_only_execution_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "read-only-execution-privacy-package-hardening"], ["release", "read-only-execution-privacy-package-hardening"], ["autonomy", "read-only-execution-privacy-package-hardening"], ["read-only-execution-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_read_only_execution_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v57-evidence-gathering-gate"], ["release", "pre-v57-evidence-gathering-gate"], ["autonomy", "pre-v57-evidence-gathering-gate"], ["pre-v57-evidence-gathering-gate"]):
        return 200, _ok(sm_v45.build_pre_v57_evidence_gathering_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "evidence-gathering-maintenance-loop"], ["release", "evidence-gathering-maintenance-loop"], ["autonomy", "evidence-gathering-maintenance-loop"], ["evidence-gathering-maintenance-loop"]):
        return 200, _ok(sm_v45.build_evidence_gathering_maintenance_loop(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], execute=False, save=False))
    if parts in (["self-maintenance", "evidence-collection-receipts"], ["release", "evidence-collection-receipts"], ["autonomy", "evidence-collection-receipts"], ["evidence-collection-receipts"]):
        return 200, _ok(sm_v45.build_evidence_collection_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "diagnostic-issue-classifier"], ["release", "diagnostic-issue-classifier"], ["autonomy", "diagnostic-issue-classifier"], ["diagnostic-issue-classifier"]):
        return 200, _ok(sm_v45.build_diagnostic_issue_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "evidence-conflict-staleness-resolver"], ["release", "evidence-conflict-staleness-resolver"], ["autonomy", "evidence-conflict-staleness-resolver"], ["evidence-conflict-staleness-resolver"]):
        return 200, _ok(sm_v45.build_evidence_conflict_staleness_resolver(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "evidence-to-plan-update-drafts"], ["release", "evidence-to-plan-update-drafts"], ["autonomy", "evidence-to-plan-update-drafts"], ["evidence-to-plan-update-drafts"]):
        return 200, _ok(sm_v45.build_evidence_to_plan_update_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "diagnostic-coverage-map"], ["release", "diagnostic-coverage-map"], ["autonomy", "diagnostic-coverage-map"], ["diagnostic-coverage-map"]):
        return 200, _ok(sm_v45.build_diagnostic_coverage_map(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "evidence-dashboard-polish"], ["release", "evidence-dashboard-polish"], ["autonomy", "evidence-dashboard-polish"], ["evidence-dashboard-polish"]):
        return 200, _ok(sm_v45.build_evidence_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "evidence-api-parity-gate"], ["release", "evidence-api-parity-gate"], ["autonomy", "evidence-api-parity-gate"], ["evidence-api-parity-gate"]):
        return 200, _ok(sm_v45.build_evidence_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "evidence-privacy-package-hardening"], ["release", "evidence-privacy-package-hardening"], ["autonomy", "evidence-privacy-package-hardening"], ["evidence-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_evidence_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v58-patch-proposal-gate"], ["release", "pre-v58-patch-proposal-gate"], ["autonomy", "pre-v58-patch-proposal-gate"], ["pre-v58-patch-proposal-gate"]):
        return 200, _ok(sm_v45.build_pre_v58_patch_proposal_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "evidence-grounded-patch-proposal"], ["release", "evidence-grounded-patch-proposal"], ["autonomy", "evidence-grounded-patch-proposal"], ["evidence-grounded-patch-proposal"]):
        return 200, _ok(sm_v45.build_evidence_grounded_patch_proposal_loop(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))


    if parts in (["self-maintenance", "patch-proposal-receipts"], ["release", "patch-proposal-receipts"], ["autonomy", "patch-proposal-receipts"], ["patch-proposal-receipts"]):
        return 200, _ok(sm_v45.build_patch_proposal_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "patch-scope-classifier"], ["release", "patch-scope-classifier"], ["autonomy", "patch-scope-classifier"], ["patch-scope-classifier"]):
        return 200, _ok(sm_v45.build_patch_scope_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "patch-risk-budget"], ["release", "patch-risk-budget"], ["autonomy", "patch-risk-budget"], ["patch-risk-budget"]):
        return 200, _ok(sm_v45.build_patch_risk_budget(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "patch-diff-preview-drafts"], ["release", "patch-diff-preview-drafts"], ["autonomy", "patch-diff-preview-drafts"], ["patch-diff-preview-drafts"]):
        return 200, _ok(sm_v45.build_patch_diff_preview_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "patch-verification-plan"], ["release", "patch-verification-plan"], ["autonomy", "patch-verification-plan"], ["patch-verification-plan"]):
        return 200, _ok(sm_v45.build_patch_verification_plan(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "patch-dashboard-polish"], ["release", "patch-dashboard-polish"], ["autonomy", "patch-dashboard-polish"], ["patch-dashboard-polish"]):
        return 200, _ok(sm_v45.build_patch_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "patch-api-parity-gate"], ["release", "patch-api-parity-gate"], ["autonomy", "patch-api-parity-gate"], ["patch-api-parity-gate"]):
        return 200, _ok(sm_v45.build_patch_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "patch-privacy-package-hardening"], ["release", "patch-privacy-package-hardening"], ["autonomy", "patch-privacy-package-hardening"], ["patch-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_patch_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v59-sandbox-patch-execution-gate"], ["release", "pre-v59-sandbox-patch-execution-gate"], ["autonomy", "pre-v59-sandbox-patch-execution-gate"], ["pre-v59-sandbox-patch-execution-gate"]):
        return 200, _ok(sm_v45.build_pre_v59_sandbox_patch_execution_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "controlled-sandbox-patch-execution"], ["release", "controlled-sandbox-patch-execution"], ["autonomy", "controlled-sandbox-patch-execution"], ["controlled-sandbox-patch-execution"]):
        return 200, _ok(sm_v45.build_controlled_sandbox_patch_execution(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], confirmation=query.get("confirmation", [None])[0], execute=False, save=False))

    if parts in (["self-maintenance", "sandbox-execution-receipts"], ["release", "sandbox-execution-receipts"], ["autonomy", "sandbox-execution-receipts"], ["sandbox-execution-receipts"]):
        return 200, _ok(sm_v45.build_sandbox_execution_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-verification-matrix"], ["release", "sandbox-verification-matrix"], ["autonomy", "sandbox-verification-matrix"], ["sandbox-verification-matrix"]):
        return 200, _ok(sm_v45.build_sandbox_verification_matrix(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-drift-detector"], ["release", "sandbox-drift-detector"], ["autonomy", "sandbox-drift-detector"], ["sandbox-drift-detector"]):
        return 200, _ok(sm_v45.build_sandbox_drift_detector(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-rollback-rehearsal"], ["release", "sandbox-rollback-rehearsal"], ["autonomy", "sandbox-rollback-rehearsal"], ["sandbox-rollback-rehearsal"]):
        return 200, _ok(sm_v45.build_sandbox_rollback_rehearsal(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-apply-candidate-drafts"], ["release", "sandbox-apply-candidate-drafts"], ["autonomy", "sandbox-apply-candidate-drafts"], ["sandbox-apply-candidate-drafts"]):
        return 200, _ok(sm_v45.build_sandbox_apply_candidate_drafts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-dashboard-polish"], ["release", "sandbox-dashboard-polish"], ["autonomy", "sandbox-dashboard-polish"], ["sandbox-dashboard-polish"]):
        return 200, _ok(sm_v45.build_sandbox_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-api-parity-gate"], ["release", "sandbox-api-parity-gate"], ["autonomy", "sandbox-api-parity-gate"], ["sandbox-api-parity-gate"]):
        return 200, _ok(sm_v45.build_sandbox_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "sandbox-privacy-package-hardening"], ["release", "sandbox-privacy-package-hardening"], ["autonomy", "sandbox-privacy-package-hardening"], ["sandbox-privacy-package-hardening"]):
        return 200, _ok(sm_v45.build_sandbox_privacy_package_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v60-source-apply-handoff-gate"], ["release", "pre-v60-source-apply-handoff-gate"], ["autonomy", "pre-v60-source-apply-handoff-gate"], ["pre-v60-source-apply-handoff-gate"]):
        return 200, _ok(sm_v45.build_pre_v60_source_apply_handoff_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "controlled-sandbox-source-apply-handoff"], ["release", "controlled-sandbox-source-apply-handoff"], ["autonomy", "controlled-sandbox-source-apply-handoff"], ["controlled-sandbox-source-apply-handoff"]):
        return 200, _ok(sm_v45.build_controlled_sandbox_source_apply_handoff(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], confirmation=query.get("confirmation", [None])[0], execute=False, save=False))

    if parts in (["self-maintenance", "source-apply-handoff-receipts"], ["release", "source-apply-handoff-receipts"], ["autonomy", "source-apply-handoff-receipts"], ["source-apply-handoff-receipts"]):
        return 200, _ok(sm_v45.build_source_apply_handoff_receipts(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-baseline-drift-resolver"], ["release", "source-baseline-drift-resolver"], ["autonomy", "source-baseline-drift-resolver"], ["source-baseline-drift-resolver"]):
        return 200, _ok(sm_v45.build_source_baseline_drift_resolver(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "reviewed-artifact-set-binder"], ["release", "reviewed-artifact-set-binder"], ["autonomy", "reviewed-artifact-set-binder"], ["reviewed-artifact-set-binder"]):
        return 200, _ok(sm_v45.build_reviewed_artifact_set_binder(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-handoff-eligibility"], ["release", "source-apply-handoff-eligibility"], ["autonomy", "source-apply-handoff-eligibility"], ["source-apply-handoff-eligibility"]):
        return 200, _ok(sm_v45.build_source_apply_handoff_eligibility_classifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-dry-run-bridge"], ["release", "source-apply-dry-run-bridge"], ["autonomy", "source-apply-dry-run-bridge"], ["source-apply-dry-run-bridge"]):
        return 200, _ok(sm_v45.build_source_apply_dry_run_bridge(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-handoff-dashboard-polish"], ["release", "source-apply-handoff-dashboard-polish"], ["autonomy", "source-apply-handoff-dashboard-polish"], ["source-apply-handoff-dashboard-polish"]):
        return 200, _ok(sm_v45.build_source_apply_handoff_dashboard_polish(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-handoff-api-parity-gate"], ["release", "source-apply-handoff-api-parity-gate"], ["autonomy", "source-apply-handoff-api-parity-gate"], ["source-apply-handoff-api-parity-gate"]):
        return 200, _ok(sm_v45.build_source_apply_handoff_api_parity_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-handoff-privacy-hardening"], ["release", "source-apply-handoff-privacy-hardening"], ["autonomy", "source-apply-handoff-privacy-hardening"], ["source-apply-handoff-privacy-hardening"]):
        return 200, _ok(sm_v45.build_source_apply_handoff_privacy_hardening(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v61-controlled-apply-bridge-gate"], ["release", "pre-v61-controlled-apply-bridge-gate"], ["autonomy", "pre-v61-controlled-apply-bridge-gate"], ["pre-v61-controlled-apply-bridge-gate"]):
        return 200, _ok(sm_v45.build_pre_v61_controlled_apply_bridge_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "controlled-source-apply-bridge-refinement"], ["release", "controlled-source-apply-bridge-refinement"], ["autonomy", "controlled-source-apply-bridge-refinement"], ["controlled-source-apply-bridge-refinement"]):
        return 200, _ok(sm_v45.build_controlled_source_apply_bridge_refinement(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))

    if parts in (["self-maintenance", "source-apply-transaction-planner"], ["release", "source-apply-transaction-planner"], ["autonomy", "source-apply-transaction-planner"], ["source-apply-transaction-planner"]):
        return 200, _ok(sm_v45.build_source_apply_transaction_planner(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-backup-binder"], ["release", "source-apply-backup-binder"], ["autonomy", "source-apply-backup-binder"], ["source-apply-backup-binder"]):
        return 200, _ok(sm_v45.build_source_apply_backup_binder(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-transaction-dry-run-verifier"], ["release", "source-apply-transaction-dry-run-verifier"], ["autonomy", "source-apply-transaction-dry-run-verifier"], ["source-apply-transaction-dry-run-verifier"]):
        return 200, _ok(sm_v45.build_source_apply_transaction_dry_run_verifier(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-transaction-confirmation-gate"], ["release", "source-apply-transaction-confirmation-gate"], ["autonomy", "source-apply-transaction-confirmation-gate"], ["source-apply-transaction-confirmation-gate"]):
        return 200, _ok(sm_v45.build_source_apply_transaction_confirmation_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], confirmation=query.get("confirmation", query.get("transaction_confirm_phrase", [None]))[0], save=False))
    if parts in (["self-maintenance", "supervised-source-apply-executor"], ["release", "supervised-source-apply-executor"], ["autonomy", "supervised-source-apply-executor"], ["supervised-source-apply-executor"]):
        return 200, _ok(sm_v45.build_supervised_source_apply_executor(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], confirmation=query.get("confirmation", query.get("transaction_confirm_phrase", [None]))[0], approve=False, dry_run=True, save=False))
    if parts in (["self-maintenance", "post-apply-verification-runner"], ["release", "post-apply-verification-runner"], ["autonomy", "post-apply-verification-runner"], ["post-apply-verification-runner"]):
        return 200, _ok(sm_v45.build_post_apply_verification_runner(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-rollback-rehearsal"], ["release", "transaction-rollback-rehearsal"], ["autonomy", "transaction-rollback-rehearsal"], ["transaction-rollback-rehearsal"]):
        return 200, _ok(sm_v45.build_transaction_rollback_rehearsal(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "source-apply-transaction-dashboard-command-center"], ["release", "source-apply-transaction-dashboard-command-center"], ["autonomy", "source-apply-transaction-dashboard-command-center"], ["source-apply-transaction-dashboard-command-center"]):
        return 200, _ok(sm_v45.build_source_apply_transaction_dashboard_command_center(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v62-transaction-release-gate"], ["release", "pre-v62-transaction-release-gate"], ["autonomy", "pre-v62-transaction-release-gate"], ["pre-v62-transaction-release-gate"]):
        return 200, _ok(sm_v45.build_pre_v62_transaction_release_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "supervised-source-apply-transaction-layer"], ["release", "supervised-source-apply-transaction-layer"], ["autonomy", "supervised-source-apply-transaction-layer"], ["supervised-source-apply-transaction-layer"]):
        return 200, _ok(sm_v45.build_supervised_source_apply_transaction_layer(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))

    if parts in (["self-maintenance", "transaction-receipt-ledger"], ["release", "transaction-receipt-ledger"], ["autonomy", "transaction-receipt-ledger"], ["transaction-receipt-ledger"]):
        return 200, _ok(sm_v45.build_transaction_receipt_ledger(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-diff-viewer"], ["release", "transaction-diff-viewer"], ["autonomy", "transaction-diff-viewer"], ["transaction-diff-viewer"]):
        return 200, _ok(sm_v45.build_transaction_diff_viewer(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-conflict-detector"], ["release", "transaction-conflict-detector"], ["autonomy", "transaction-conflict-detector"], ["transaction-conflict-detector"]):
        return 200, _ok(sm_v45.build_transaction_conflict_detector(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-approval-record-binder"], ["release", "transaction-approval-record-binder"], ["autonomy", "transaction-approval-record-binder"], ["transaction-approval-record-binder"]):
        return 200, _ok(sm_v45.build_transaction_approval_record_binder(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-package-evidence-exporter"], ["release", "transaction-package-evidence-exporter"], ["autonomy", "transaction-package-evidence-exporter"], ["transaction-package-evidence-exporter"]):
        return 200, _ok(sm_v45.build_transaction_package_evidence_exporter(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-replay-audit"], ["release", "transaction-replay-audit"], ["autonomy", "transaction-replay-audit"], ["transaction-replay-audit"]):
        return 200, _ok(sm_v45.build_transaction_replay_audit(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-dashboard-receipt-timeline"], ["release", "transaction-dashboard-receipt-timeline"], ["autonomy", "transaction-dashboard-receipt-timeline"], ["transaction-dashboard-receipt-timeline"]):
        return 200, _ok(sm_v45.build_transaction_dashboard_receipt_timeline(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "transaction-api-search-filtering"], ["release", "transaction-api-search-filtering"], ["autonomy", "transaction-api-search-filtering"], ["transaction-api-search-filtering"]):
        return 200, _ok(sm_v45.build_transaction_api_search_filtering(project_id=query.get("project", ["eidolon"])[0], transaction_id=query.get("transaction_id", [None])[0], status_filter=query.get("status", [None])[0], stage_filter=query.get("stage", [None])[0], file_touched=query.get("file", [None])[0], save=False))
    if parts in (["self-maintenance", "pre-v63-transaction-evidence-gate"], ["release", "pre-v63-transaction-evidence-gate"], ["autonomy", "pre-v63-transaction-evidence-gate"], ["pre-v63-transaction-evidence-gate"]):
        return 200, _ok(sm_v45.build_pre_v63_transaction_evidence_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "durable-transaction-evidence-system"], ["release", "durable-transaction-evidence-system"], ["autonomy", "durable-transaction-evidence-system"], ["durable-transaction-evidence-system"]):
        return 200, _ok(sm_v45.build_durable_transaction_evidence_system(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", query.get("autonomy_goal", [None]))[0], command_key=query.get("command_key", ["version-import"])[0], save=False))
    if parts in (["self-maintenance", "transaction-evidence-summarizer"], ["release", "transaction-evidence-summarizer"], ["autonomy", "transaction-evidence-summarizer"], ["transaction-evidence-summarizer"]):
        return 200, _ok(sm_v45.build_transaction_evidence_summarizer(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "improvement-candidate-registry"], ["release", "improvement-candidate-registry"], ["autonomy", "improvement-candidate-registry"], ["improvement-candidate-registry"]):
        return 200, _ok(sm_v45.build_improvement_candidate_registry(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "evidence-based-candidate-scoring"], ["release", "evidence-based-candidate-scoring"], ["autonomy", "evidence-based-candidate-scoring"], ["evidence-based-candidate-scoring"]):
        return 200, _ok(sm_v45.build_evidence_based_candidate_scoring(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "improvement-regression-pattern-detector"], ["release", "improvement-regression-pattern-detector"], ["autonomy", "improvement-regression-pattern-detector"], ["improvement-regression-pattern-detector"]):
        return 200, _ok(sm_v45.build_improvement_regression_pattern_detector(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "improvement-risk-blast-radius-forecaster"], ["release", "improvement-risk-blast-radius-forecaster"], ["autonomy", "improvement-risk-blast-radius-forecaster"], ["improvement-risk-blast-radius-forecaster"]):
        return 200, _ok(sm_v45.build_improvement_risk_blast_radius_forecaster(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "supervised-recommendation-queue"], ["release", "supervised-recommendation-queue"], ["autonomy", "supervised-recommendation-queue"], ["supervised-recommendation-queue"]):
        return 200, _ok(sm_v45.build_supervised_recommendation_queue(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "improvement-intelligence-dashboard"], ["release", "improvement-intelligence-dashboard"], ["autonomy", "improvement-intelligence-dashboard"], ["improvement-intelligence-dashboard"]):
        return 200, _ok(sm_v45.build_improvement_intelligence_dashboard(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "improvement-intelligence-api-cli-access"], ["release", "improvement-intelligence-api-cli-access"], ["autonomy", "improvement-intelligence-api-cli-access"], ["improvement-intelligence-api-cli-access"]):
        return 200, _ok(sm_v45.build_improvement_intelligence_api_cli_access(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v64-improvement-intelligence-gate"], ["release", "pre-v64-improvement-intelligence-gate"], ["autonomy", "pre-v64-improvement-intelligence-gate"], ["pre-v64-improvement-intelligence-gate"]):
        return 200, _ok(sm_v45.build_pre_v64_improvement_intelligence_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "supervised-improvement-intelligence-layer"], ["release", "supervised-improvement-intelligence-layer"], ["autonomy", "supervised-improvement-intelligence-layer"], ["supervised-improvement-intelligence-layer"]):
        return 200, _ok(sm_v45.build_supervised_improvement_intelligence_layer(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "accepted-recommendation-intake"], ["release", "accepted-recommendation-intake"], ["autonomy", "accepted-recommendation-intake"], ["accepted-recommendation-intake"]):
        return 200, _ok(sm_v45.build_accepted_recommendation_intake(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-draft-skeleton"], ["release", "proposal-draft-skeleton"], ["autonomy", "proposal-draft-skeleton"], ["proposal-draft-skeleton"]):
        return 200, _ok(sm_v45.build_proposal_draft_skeleton(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "evidence-requirement-mapper"], ["release", "evidence-requirement-mapper"], ["autonomy", "evidence-requirement-mapper"], ["evidence-requirement-mapper"]):
        return 200, _ok(sm_v45.build_evidence_requirement_mapper(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-risk-contract"], ["release", "proposal-risk-contract"], ["autonomy", "proposal-risk-contract"], ["proposal-risk-contract"]):
        return 200, _ok(sm_v45.build_proposal_risk_contract(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "sandbox-patch-request-compiler"], ["release", "sandbox-patch-request-compiler"], ["autonomy", "sandbox-patch-request-compiler"], ["sandbox-patch-request-compiler"]):
        return 200, _ok(sm_v45.build_sandbox_patch_request_compiler(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-review-packet-binder"], ["release", "proposal-review-packet-binder"], ["autonomy", "proposal-review-packet-binder"], ["proposal-review-packet-binder"]):
        return 200, _ok(sm_v45.build_proposal_review_packet_binder(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-dashboard-review-console"], ["release", "proposal-dashboard-review-console"], ["autonomy", "proposal-dashboard-review-console"], ["proposal-dashboard-review-console"]):
        return 200, _ok(sm_v45.build_proposal_dashboard_review_console(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "proposal-api-cli-access"], ["release", "proposal-api-cli-access"], ["autonomy", "proposal-api-cli-access"], ["proposal-api-cli-access"]):
        return 200, _ok(sm_v45.build_proposal_api_cli_access(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v65-proposal-drafting-gate"], ["release", "pre-v65-proposal-drafting-gate"], ["autonomy", "pre-v65-proposal-drafting-gate"], ["pre-v65-proposal-drafting-gate"]):
        return 200, _ok(sm_v45.build_pre_v65_proposal_drafting_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "recommendation-to-proposal-drafting-layer"], ["release", "recommendation-to-proposal-drafting-layer"], ["autonomy", "recommendation-to-proposal-drafting-layer"], ["recommendation-to-proposal-drafting-layer"]):
        return 200, _ok(sm_v45.build_recommendation_to_proposal_drafting_layer(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "reviewed-proposal-acceptance-gate"], ["release", "reviewed-proposal-acceptance-gate"], ["autonomy", "reviewed-proposal-acceptance-gate"], ["reviewed-proposal-acceptance-gate"]):
        return 200, _ok(sm_v45.build_reviewed_proposal_acceptance_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "sandbox-workspace-plan"], ["release", "sandbox-workspace-plan"], ["autonomy", "sandbox-workspace-plan"], ["sandbox-workspace-plan"]):
        return 200, _ok(sm_v45.build_sandbox_workspace_plan(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "patch-implementation-request"], ["release", "patch-implementation-request"], ["autonomy", "patch-implementation-request"], ["patch-implementation-request"]):
        return 200, _ok(sm_v45.build_patch_implementation_request(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-sandbox-execution-harness"], ["release", "proposal-sandbox-execution-harness"], ["autonomy", "proposal-sandbox-execution-harness"], ["proposal-sandbox-execution-harness"]):
        return 200, _ok(sm_v45.build_proposal_sandbox_execution_harness(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], execute_copy=False, save=False))
    if parts in (["self-maintenance", "proposal-sandbox-verification-matrix"], ["release", "proposal-sandbox-verification-matrix"], ["autonomy", "proposal-sandbox-verification-matrix"], ["proposal-sandbox-verification-matrix"]):
        return 200, _ok(sm_v45.build_proposal_sandbox_verification_matrix(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-sandbox-evidence-binder"], ["release", "proposal-sandbox-evidence-binder"], ["autonomy", "proposal-sandbox-evidence-binder"], ["proposal-sandbox-evidence-binder"]):
        return 200, _ok(sm_v45.build_proposal_sandbox_evidence_binder(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-sandbox-failure-triage"], ["release", "proposal-sandbox-failure-triage"], ["autonomy", "proposal-sandbox-failure-triage"], ["proposal-sandbox-failure-triage"]):
        return 200, _ok(sm_v45.build_proposal_sandbox_failure_triage(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "proposal-sandbox-api-cli-access"], ["release", "proposal-sandbox-api-cli-access"], ["autonomy", "proposal-sandbox-api-cli-access"], ["proposal-sandbox-api-cli-access"]):
        return 200, _ok(sm_v45.build_proposal_sandbox_api_cli_access(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v66-proposal-sandbox-gate"], ["release", "pre-v66-proposal-sandbox-gate"], ["autonomy", "pre-v66-proposal-sandbox-gate"], ["pre-v66-proposal-sandbox-gate"]):
        return 200, _ok(sm_v45.build_pre_v66_proposal_sandbox_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "reviewed-proposal-sandbox-execution-layer"], ["release", "reviewed-proposal-sandbox-execution-layer"], ["autonomy", "reviewed-proposal-sandbox-execution-layer"], ["reviewed-proposal-sandbox-execution-layer"]):
        return 200, _ok(sm_v45.build_reviewed_proposal_sandbox_execution_layer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))

    if parts in (["self-maintenance", "sandbox-promotion-candidate"], ["release", "sandbox-promotion-candidate"], ["autonomy", "sandbox-promotion-candidate"], ["sandbox-promotion-candidate"]):
        return 200, _ok(sm_v45.build_sandbox_promotion_candidate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "sandbox-source-diff-normalizer"], ["release", "sandbox-source-diff-normalizer"], ["autonomy", "sandbox-source-diff-normalizer"], ["sandbox-source-diff-normalizer"]):
        return 200, _ok(sm_v45.build_sandbox_source_diff_normalizer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "promotion-safety-boundary-gate"], ["release", "promotion-safety-boundary-gate"], ["autonomy", "promotion-safety-boundary-gate"], ["promotion-safety-boundary-gate"]):
        return 200, _ok(sm_v45.build_promotion_safety_boundary_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "transaction-draft-from-sandbox"], ["release", "transaction-draft-from-sandbox"], ["autonomy", "transaction-draft-from-sandbox"], ["transaction-draft-from-sandbox"]):
        return 200, _ok(sm_v45.build_transaction_draft_from_sandbox(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "promotion-review-packet-binder"], ["release", "promotion-review-packet-binder"], ["autonomy", "promotion-review-packet-binder"], ["promotion-review-packet-binder"]):
        return 200, _ok(sm_v45.build_promotion_review_packet_binder(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "promotion-conflict-staleness-detector"], ["release", "promotion-conflict-staleness-detector"], ["autonomy", "promotion-conflict-staleness-detector"], ["promotion-conflict-staleness-detector"]):
        return 200, _ok(sm_v45.build_promotion_conflict_staleness_detector(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "sandbox-promotion-api-cli-access"], ["release", "sandbox-promotion-api-cli-access"], ["autonomy", "sandbox-promotion-api-cli-access"], ["sandbox-promotion-api-cli-access"]):
        return 200, _ok(sm_v45.build_sandbox_promotion_api_cli_access(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v67-sandbox-promotion-gate"], ["release", "pre-v67-sandbox-promotion-gate"], ["autonomy", "pre-v67-sandbox-promotion-gate"], ["pre-v67-sandbox-promotion-gate"]):
        return 200, _ok(sm_v45.build_pre_v67_sandbox_promotion_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "sandbox-evidence-promotion-handoff-layer"], ["release", "sandbox-evidence-promotion-handoff-layer"], ["autonomy", "sandbox-evidence-promotion-handoff-layer"], ["sandbox-evidence-promotion-handoff-layer"]):
        return 200, _ok(sm_v45.build_sandbox_evidence_promotion_handoff_layer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "promotion-packet-intake-gate"], ["release", "promotion-packet-intake-gate"], ["autonomy", "promotion-packet-intake-gate"], ["promotion-packet-intake-gate"]):
        return 200, _ok(sm_v45.build_promotion_packet_intake_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "transaction-plan-materializer"], ["release", "transaction-plan-materializer"], ["autonomy", "transaction-plan-materializer"], ["transaction-plan-materializer"]):
        return 200, _ok(sm_v45.build_transaction_plan_materializer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "source-baseline-reconciliation"], ["release", "source-baseline-reconciliation"], ["autonomy", "source-baseline-reconciliation"], ["source-baseline-reconciliation"]):
        return 200, _ok(sm_v45.build_source_baseline_reconciliation(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "backup-rollback-preflight-binder"], ["release", "backup-rollback-preflight-binder"], ["autonomy", "backup-rollback-preflight-binder"], ["backup-rollback-preflight-binder"]):
        return 200, _ok(sm_v45.build_backup_rollback_preflight_binder(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "final-transaction-safety-gate"], ["release", "final-transaction-safety-gate"], ["autonomy", "final-transaction-safety-gate"], ["final-transaction-safety-gate"]):
        return 200, _ok(sm_v45.build_final_transaction_safety_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "transaction-ledger-preregistration"], ["release", "transaction-ledger-preregistration"], ["autonomy", "transaction-ledger-preregistration"], ["transaction-ledger-preregistration"]):
        return 200, _ok(sm_v45.build_transaction_ledger_preregistration(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "source-transaction-review-console"], ["release", "source-transaction-review-console"], ["autonomy", "source-transaction-review-console"], ["source-transaction-review-console"]):
        return 200, _ok(sm_v45.build_source_transaction_review_console(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "transaction-review-api-cli-access"], ["release", "transaction-review-api-cli-access"], ["autonomy", "transaction-review-api-cli-access"], ["transaction-review-api-cli-access"]):
        return 200, _ok(sm_v45.build_transaction_review_api_cli_access(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v68-transaction-integration-gate"], ["release", "pre-v68-transaction-integration-gate"], ["autonomy", "pre-v68-transaction-integration-gate"], ["pre-v68-transaction-integration-gate"]):
        return 200, _ok(sm_v45.build_pre_v68_transaction_integration_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "promotion-to-transaction-integration-layer"], ["release", "promotion-to-transaction-integration-layer"], ["autonomy", "promotion-to-transaction-integration-layer"], ["promotion-to-transaction-integration-layer"]):
        return 200, _ok(sm_v45.build_promotion_to_transaction_integration_layer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))

    if parts in (["self-maintenance", "transaction-execution-eligibility"], ["release", "transaction-execution-eligibility"], ["autonomy", "transaction-execution-eligibility"], ["transaction-execution-eligibility"]):
        return 200, _ok(sm_v45.build_transaction_execution_eligibility(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "exact-confirmation-binder"], ["release", "exact-confirmation-binder"], ["autonomy", "exact-confirmation-binder"], ["exact-confirmation-binder"]):
        return 200, _ok(sm_v45.build_exact_confirmation_binder(project_id=query.get("project", ["eidolon"])[0], confirmation_phrase=query.get("confirmation_phrase", [""])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "backup-snapshot-materializer"], ["release", "backup-snapshot-materializer"], ["autonomy", "backup-snapshot-materializer"], ["backup-snapshot-materializer"]):
        return 200, _ok(sm_v45.build_backup_snapshot_materializer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "transaction-apply-rehearsal"], ["release", "transaction-apply-rehearsal"], ["autonomy", "transaction-apply-rehearsal"], ["transaction-apply-rehearsal"]):
        return 200, _ok(sm_v45.build_transaction_apply_rehearsal(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "operator-confirmed-apply-executor"], ["release", "operator-confirmed-apply-executor"], ["autonomy", "operator-confirmed-apply-executor"], ["operator-confirmed-apply-executor"]):
        return 200, _ok(sm_v45.build_operator_confirmed_apply_executor(project_id=query.get("project", ["eidolon"])[0], confirmation_phrase=query.get("confirmation_phrase", [""])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "post-execution-verification"], ["release", "post-execution-verification"], ["autonomy", "post-execution-verification"], ["post-execution-verification"]):
        return 200, _ok(sm_v45.build_post_execution_verification(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "rollback-recommendation-gate"], ["release", "rollback-recommendation-gate"], ["autonomy", "rollback-recommendation-gate"], ["rollback-recommendation-gate"]):
        return 200, _ok(sm_v45.build_rollback_recommendation_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "transaction-execution-dashboard-api-cli"], ["release", "transaction-execution-dashboard-api-cli"], ["autonomy", "transaction-execution-dashboard-api-cli"], ["transaction-execution-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_transaction_execution_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v69-execution-gate"], ["release", "pre-v69-execution-gate"], ["autonomy", "pre-v69-execution-gate"], ["pre-v69-execution-gate"]):
        return 200, _ok(sm_v45.build_pre_v69_execution_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "operator-confirmed-transaction-execution-layer"], ["release", "operator-confirmed-transaction-execution-layer"], ["autonomy", "operator-confirmed-transaction-execution-layer"], ["operator-confirmed-transaction-execution-layer"]):
        return 200, _ok(sm_v45.build_operator_confirmed_transaction_execution_layer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))

    if parts in (["self-maintenance", "execution-result-ledger-finalizer"], ["release", "execution-result-ledger-finalizer"], ["autonomy", "execution-result-ledger-finalizer"], ["execution-result-ledger-finalizer"]):
        return 200, _ok(sm_v45.build_execution_result_ledger_finalizer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "rollback-decision-resolver"], ["release", "rollback-decision-resolver"], ["autonomy", "rollback-decision-resolver"], ["rollback-decision-resolver"]):
        return 200, _ok(sm_v45.build_rollback_decision_resolver(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "operator-confirmed-rollback-executor"], ["release", "operator-confirmed-rollback-executor"], ["autonomy", "operator-confirmed-rollback-executor"], ["operator-confirmed-rollback-executor"]):
        return 200, _ok(sm_v45.build_operator_confirmed_rollback_executor(project_id=query.get("project", ["eidolon"])[0], rollback_confirmation_phrase=query.get("rollback_confirmation_phrase", [""])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "post-rollback-verification"], ["release", "post-rollback-verification"], ["autonomy", "post-rollback-verification"], ["post-rollback-verification"]):
        return 200, _ok(sm_v45.build_post_rollback_verification(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "release-candidate-finalization-gate"], ["release", "release-candidate-finalization-gate"], ["autonomy", "release-candidate-finalization-gate"], ["release-candidate-finalization-gate"]):
        return 200, _ok(sm_v45.build_release_candidate_finalization_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "source-only-package-certifier"], ["release", "source-only-package-certifier"], ["autonomy", "source-only-package-certifier"], ["source-only-package-certifier"]):
        return 200, _ok(sm_v45.build_source_only_package_certifier(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "release-finalization-dashboard-api-cli"], ["release", "release-finalization-dashboard-api-cli"], ["autonomy", "release-finalization-dashboard-api-cli"], ["release-finalization-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_release_finalization_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "recovery-simulation-harness"], ["release", "recovery-simulation-harness"], ["autonomy", "recovery-simulation-harness"], ["recovery-simulation-harness"]):
        return 200, _ok(sm_v45.build_recovery_simulation_harness(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v70-recovery-finalization-gate"], ["release", "pre-v70-recovery-finalization-gate"], ["autonomy", "pre-v70-recovery-finalization-gate"], ["pre-v70-recovery-finalization-gate"]):
        return 200, _ok(sm_v45.build_pre_v70_recovery_finalization_gate(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))
    if parts in (["self-maintenance", "verified-execution-recovery-release-layer"], ["release", "verified-execution-recovery-release-layer"], ["autonomy", "verified-execution-recovery-release-layer"], ["verified-execution-recovery-release-layer"]):
        return 200, _ok(sm_v45.build_verified_execution_recovery_release_layer(project_id=query.get("project", ["eidolon"])[0], recommendation_id=query.get("recommendation_id", [None])[0], save=False))

    if parts in (["self-maintenance", "source-tree-inventory"], ["release", "source-tree-inventory"], ["autonomy", "source-tree-inventory"], ["codebase-map", "inventory"], ["source-tree-inventory"]):
        return 200, _ok(sm_v45.build_source_tree_inventory(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "module-responsibility-map"], ["release", "module-responsibility-map"], ["autonomy", "module-responsibility-map"], ["codebase-map", "responsibilities"], ["module-responsibility-map"]):
        return 200, _ok(sm_v45.build_module_responsibility_map(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "dependency-call-surface-map"], ["release", "dependency-call-surface-map"], ["autonomy", "dependency-call-surface-map"], ["codebase-map", "dependencies"], ["dependency-call-surface-map"]):
        return 200, _ok(sm_v45.build_dependency_call_surface_map(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "module-risk-profile"], ["release", "module-risk-profile"], ["autonomy", "module-risk-profile"], ["codebase-map", "risk"], ["module-risk-profile"]):
        return 200, _ok(sm_v45.build_module_risk_profile(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "historical-failure-memory"], ["release", "historical-failure-memory"], ["autonomy", "historical-failure-memory"], ["codebase-map", "failures"], ["historical-failure-memory"]):
        return 200, _ok(sm_v45.build_historical_failure_memory(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "verification-command-map"], ["release", "verification-command-map"], ["autonomy", "verification-command-map"], ["codebase-map", "verification"], ["verification-command-map"]):
        return 200, _ok(sm_v45.build_verification_command_map(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "improvement-opportunity-detector"], ["release", "improvement-opportunity-detector"], ["autonomy", "improvement-opportunity-detector"], ["codebase-map", "opportunities"], ["improvement-opportunity-detector"]):
        return 200, _ok(sm_v45.build_improvement_opportunity_detector(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "codebase-understanding-dashboard-api-cli"], ["release", "codebase-understanding-dashboard-api-cli"], ["autonomy", "codebase-understanding-dashboard-api-cli"], ["codebase-map", "parity"], ["codebase-understanding-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_codebase_understanding_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "pre-v71-codebase-understanding-gate"], ["release", "pre-v71-codebase-understanding-gate"], ["autonomy", "pre-v71-codebase-understanding-gate"], ["codebase-map", "gate"], ["pre-v71-codebase-understanding-gate"]):
        return 200, _ok(sm_v45.build_pre_v71_codebase_understanding_gate(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "codebase-understanding-map"], ["release", "codebase-understanding-map"], ["autonomy", "codebase-understanding-map"], ["codebase-map", "layer"], ["codebase-understanding-map"]):
        return 200, _ok(sm_v45.build_codebase_understanding_map(project_id=query.get("project", ["eidolon"])[0], save=False))

    patch_goal = query.get("patch_goal", query.get("goal", [None]))[0]
    if parts in (["self-maintenance", "patch-goal-intake-classifier"], ["release", "patch-goal-intake-classifier"], ["autonomy", "patch-goal-intake-classifier"], ["patch-context", "goal"], ["patch-goal-intake-classifier"]):
        return 200, _ok(sm_v45.build_patch_goal_intake_classifier(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "relevant-file-context-selector"], ["release", "relevant-file-context-selector"], ["autonomy", "relevant-file-context-selector"], ["patch-context", "files"], ["relevant-file-context-selector"]):
        return 200, _ok(sm_v45.build_relevant_file_context_selector(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "historical-failure-context-binder"], ["release", "historical-failure-context-binder"], ["autonomy", "historical-failure-context-binder"], ["patch-context", "failures"], ["historical-failure-context-binder"]):
        return 200, _ok(sm_v45.build_historical_failure_context_binder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "risk-aware-context-budgeter"], ["release", "risk-aware-context-budgeter"], ["autonomy", "risk-aware-context-budgeter"], ["patch-context", "budget"], ["risk-aware-context-budgeter"]):
        return 200, _ok(sm_v45.build_risk_aware_context_budgeter(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "verification-requirement-compiler"], ["release", "verification-requirement-compiler"], ["autonomy", "verification-requirement-compiler"], ["patch-context", "verification"], ["verification-requirement-compiler"]):
        return 200, _ok(sm_v45.build_verification_requirement_compiler(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-prompt-context-packet-builder"], ["release", "patch-prompt-context-packet-builder"], ["autonomy", "patch-prompt-context-packet-builder"], ["patch-context", "packet"], ["patch-prompt-context-packet-builder"]):
        return 200, _ok(sm_v45.build_patch_prompt_context_packet_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "context-completeness-reviewer"], ["release", "context-completeness-reviewer"], ["autonomy", "context-completeness-reviewer"], ["patch-context", "review"], ["context-completeness-reviewer"]):
        return 200, _ok(sm_v45.build_context_completeness_reviewer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-context-dashboard-api-cli"], ["release", "patch-context-dashboard-api-cli"], ["autonomy", "patch-context-dashboard-api-cli"], ["patch-context", "parity"], ["patch-context-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_context_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "pre-v72-patch-context-gate"], ["release", "pre-v72-patch-context-gate"], ["autonomy", "pre-v72-patch-context-gate"], ["patch-context", "gate"], ["pre-v72-patch-context-gate"]):
        return 200, _ok(sm_v45.build_pre_v72_patch_context_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-generation-context-builder"], ["release", "patch-generation-context-builder"], ["autonomy", "patch-generation-context-builder"], ["patch-context", "layer"], ["patch-generation-context-builder"]):
        return 200, _ok(sm_v45.build_patch_generation_context_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))

    if parts in (["self-maintenance", "patch-intent-normalizer"], ["release", "patch-intent-normalizer"], ["autonomy", "patch-intent-normalizer"], ["patch-drafts", "intake"], ["patch-intent-normalizer"]):
        return 200, _ok(sm_v45.build_patch_intent_normalizer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-scope-contract-builder"], ["release", "patch-scope-contract-builder"], ["autonomy", "patch-scope-contract-builder"], ["patch-drafts", "scope"], ["patch-scope-contract-builder"]):
        return 200, _ok(sm_v45.build_patch_scope_contract_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-prompt-composer"], ["release", "patch-prompt-composer"], ["autonomy", "patch-prompt-composer"], ["patch-drafts", "prompt"], ["patch-prompt-composer"]):
        return 200, _ok(sm_v45.build_patch_prompt_composer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-draft-output-schema"], ["release", "patch-draft-output-schema"], ["autonomy", "patch-draft-output-schema"], ["patch-drafts", "schema"], ["patch-draft-output-schema"]):
        return 200, _ok(sm_v45.build_patch_draft_output_schema(project_id=query.get("project", ["eidolon"])[0], save=False))
    if parts in (["self-maintenance", "patch-draft-safety-reviewer"], ["release", "patch-draft-safety-reviewer"], ["autonomy", "patch-draft-safety-reviewer"], ["patch-drafts", "safety"], ["patch-draft-safety-reviewer"]):
        return 200, _ok(sm_v45.build_patch_draft_safety_reviewer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-draft-evidence-binder"], ["release", "patch-draft-evidence-binder"], ["autonomy", "patch-draft-evidence-binder"], ["patch-drafts", "evidence"], ["patch-draft-evidence-binder"]):
        return 200, _ok(sm_v45.build_patch_draft_evidence_binder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-draft-dashboard-api-cli"], ["release", "patch-draft-dashboard-api-cli"], ["autonomy", "patch-draft-dashboard-api-cli"], ["patch-drafts", "parity"], ["patch-draft-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_draft_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "local-model-handoff-stub"], ["release", "local-model-handoff-stub"], ["autonomy", "local-model-handoff-stub"], ["patch-drafts", "handoff"], ["local-model-handoff-stub"]):
        return 200, _ok(sm_v45.build_local_model_handoff_stub(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "pre-v73-patch-draft-gate"], ["release", "pre-v73-patch-draft-gate"], ["autonomy", "pre-v73-patch-draft-gate"], ["patch-drafts", "gate"], ["pre-v73-patch-draft-gate"]):
        return 200, _ok(sm_v45.build_pre_v73_patch_draft_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "supervised-patch-draft-composer"], ["release", "supervised-patch-draft-composer"], ["autonomy", "supervised-patch-draft-composer"], ["patch-drafts", "layer"], ["supervised-patch-draft-composer"]):
        return 200, _ok(sm_v45.build_supervised_patch_draft_composer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))

    draft_file = query.get("patch_draft_file", query.get("draft_file", [None]))[0]
    draft_text = query.get("draft_text", [None])[0]
    if parts in (["self-maintenance", "patch-review-intake-parser"], ["release", "patch-review-intake-parser"], ["autonomy", "patch-review-intake-parser"], ["patch-review", "intake"], ["patch-review-intake-parser"]):
        return 200, _ok(sm_v45.build_patch_review_intake_parser(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "diff-boundary-extractor"], ["release", "diff-boundary-extractor"], ["autonomy", "diff-boundary-extractor"], ["patch-review", "diff-boundary"], ["diff-boundary-extractor"]):
        return 200, _ok(sm_v45.build_patch_review_diff_boundary_extractor(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "scope-contract-validator"], ["release", "scope-contract-validator"], ["autonomy", "scope-contract-validator"], ["patch-review", "scope"], ["scope-contract-validator"]):
        return 200, _ok(sm_v45.build_patch_review_scope_contract_validator(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "patch-safety-boundary-validator"], ["release", "patch-safety-boundary-validator"], ["autonomy", "patch-safety-boundary-validator"], ["patch-review", "safety"], ["patch-safety-boundary-validator"]):
        return 200, _ok(sm_v45.build_patch_review_safety_boundary_validator(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "documentation-update-validator"], ["release", "documentation-update-validator"], ["autonomy", "documentation-update-validator"], ["patch-review", "docs"], ["documentation-update-validator"]):
        return 200, _ok(sm_v45.build_documentation_update_validator(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "verification-plan-validator"], ["release", "verification-plan-validator"], ["autonomy", "verification-plan-validator"], ["patch-review", "verification"], ["verification-plan-validator"]):
        return 200, _ok(sm_v45.build_verification_plan_validator(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "patch-risk-scorer"], ["release", "patch-risk-scorer"], ["autonomy", "patch-risk-scorer"], ["patch-review", "risk"], ["patch-risk-scorer"]):
        return 200, _ok(sm_v45.build_patch_risk_scorer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "patch-review-report-builder"], ["release", "patch-review-report-builder"], ["autonomy", "patch-review-report-builder"], ["patch-review", "report"], ["patch-review-report-builder"]):
        return 200, _ok(sm_v45.build_patch_review_report_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "patch-review-dashboard-api-cli"], ["release", "patch-review-dashboard-api-cli"], ["autonomy", "patch-review-dashboard-api-cli"], ["patch-review", "parity"], ["patch-review-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_review_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "pre-v74-patch-review-gate"], ["release", "pre-v74-patch-review-gate"], ["autonomy", "pre-v74-patch-review-gate"], ["patch-review", "gate"], ["pre-v74-patch-review-gate"]):
        return 200, _ok(sm_v45.build_pre_v74_patch_review_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))
    if parts in (["self-maintenance", "patch-draft-review-diff-validation-layer"], ["release", "patch-draft-review-diff-validation-layer"], ["autonomy", "patch-draft-review-diff-validation-layer"], ["patch-review", "layer"], ["patch-draft-review-diff-validation-layer"]):
        return 200, _ok(sm_v45.build_patch_draft_review_diff_validation_layer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, save=False))

    trial_id = query.get("patch_trial_id", query.get("trial_id", [None]))[0]
    cleanup = query.get("cleanup", ["false"])[0].lower() in {"1", "true", "yes"}
    if parts in (["self-maintenance", "patch-trial-intake-binder"], ["release", "patch-trial-intake-binder"], ["autonomy", "patch-trial-intake-binder"], ["patch-trials", "intake"], ["patch-trial-intake-binder"]):
        return 200, _ok(sm_v45.build_patch_trial_intake_binder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "disposable-workspace-builder"], ["release", "disposable-workspace-builder"], ["autonomy", "disposable-workspace-builder"], ["patch-trials", "workspace"], ["disposable-workspace-builder"]):
        return 200, _ok(sm_v45.build_disposable_workspace_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "patch-draft-materializer"], ["release", "patch-draft-materializer"], ["autonomy", "patch-draft-materializer"], ["patch-trials", "materialize"], ["patch-draft-materializer"]):
        return 200, _ok(sm_v45.build_patch_draft_materializer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "sandbox-verification-runner"], ["release", "sandbox-verification-runner"], ["autonomy", "sandbox-verification-runner"], ["patch-trials", "verify"], ["sandbox-verification-runner"]):
        return 200, _ok(sm_v45.build_sandbox_verification_runner(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "sandbox-evidence-collector"], ["release", "sandbox-evidence-collector"], ["autonomy", "sandbox-evidence-collector"], ["patch-trials", "evidence"], ["sandbox-evidence-collector"]):
        return 200, _ok(sm_v45.build_sandbox_evidence_collector(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "sandbox-escape-mutation-guard"], ["release", "sandbox-escape-mutation-guard"], ["autonomy", "sandbox-escape-mutation-guard"], ["patch-trials", "escape-guard"], ["sandbox-escape-mutation-guard"]):
        return 200, _ok(sm_v45.build_sandbox_escape_mutation_guard(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "patch-trial-dashboard-api-cli"], ["release", "patch-trial-dashboard-api-cli"], ["autonomy", "patch-trial-dashboard-api-cli"], ["patch-trials", "parity"], ["patch-trial-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_trial_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "patch-trial-cleanup-retention"], ["release", "patch-trial-cleanup-retention"], ["autonomy", "patch-trial-cleanup-retention"], ["patch-trials", "cleanup"], ["patch-trials", "list"], ["patch-trial-cleanup-retention"]):
        return 200, _ok(sm_v45.build_patch_trial_cleanup_retention(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, cleanup=cleanup, save=False))
    if parts in (["self-maintenance", "pre-v75-sandbox-trial-gate"], ["release", "pre-v75-sandbox-trial-gate"], ["autonomy", "pre-v75-sandbox-trial-gate"], ["patch-trials", "gate"], ["pre-v75-sandbox-trial-gate"]):
        return 200, _ok(sm_v45.build_pre_v75_sandbox_trial_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))
    if parts in (["self-maintenance", "sandbox-patch-trial-runner"], ["release", "sandbox-patch-trial-runner"], ["autonomy", "sandbox-patch-trial-runner"], ["patch-trials", "layer"], ["sandbox-patch-trial-runner"]):
        return 200, _ok(sm_v45.build_sandbox_patch_trial_runner(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, save=False))

    evidence_file = query.get("patch_evidence_file", query.get("evidence_file", [None]))[0]
    if parts in (["self-maintenance", "patch-evidence-intake-reader"], ["release", "patch-evidence-intake-reader"], ["autonomy", "patch-evidence-intake-reader"], ["patch-evidence", "intake"], ["patch-evidence-intake-reader"]):
        return 200, _ok(sm_v45.build_patch_evidence_intake_reader(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "trial-integrity-validator"], ["release", "trial-integrity-validator"], ["autonomy", "trial-integrity-validator"], ["patch-evidence", "integrity"], ["trial-integrity-validator"]):
        return 200, _ok(sm_v45.build_trial_integrity_validator(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "verification-evidence-scorer"], ["release", "verification-evidence-scorer"], ["autonomy", "verification-evidence-scorer"], ["patch-evidence", "verification"], ["verification-evidence-scorer"]):
        return 200, _ok(sm_v45.build_verification_evidence_scorer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "scope-documentation-evidence-reviewer"], ["release", "scope-documentation-evidence-reviewer"], ["autonomy", "scope-documentation-evidence-reviewer"], ["patch-evidence", "scope-docs"], ["scope-documentation-evidence-reviewer"]):
        return 200, _ok(sm_v45.build_scope_documentation_evidence_reviewer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "risk-acceptance-classifier"], ["release", "risk-acceptance-classifier"], ["autonomy", "risk-acceptance-classifier"], ["patch-evidence", "risk"], ["risk-acceptance-classifier"]):
        return 200, _ok(sm_v45.build_risk_acceptance_classifier(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "promotion-readiness-packet-builder"], ["release", "promotion-readiness-packet-builder"], ["autonomy", "promotion-readiness-packet-builder"], ["patch-evidence", "readiness"], ["promotion-readiness-packet-builder"]):
        return 200, _ok(sm_v45.build_promotion_readiness_packet_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "patch-evidence-dashboard-api-cli"], ["release", "patch-evidence-dashboard-api-cli"], ["autonomy", "patch-evidence-dashboard-api-cli"], ["patch-evidence", "parity"], ["patch-evidence-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_evidence_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "recommendation-archive-comparison"], ["release", "recommendation-archive-comparison"], ["autonomy", "recommendation-archive-comparison"], ["patch-evidence", "archive"], ["recommendation-archive-comparison"]):
        return 200, _ok(sm_v45.build_recommendation_archive_comparison(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "pre-v76-evidence-review-gate"], ["release", "pre-v76-evidence-review-gate"], ["autonomy", "pre-v76-evidence-review-gate"], ["patch-evidence", "gate"], ["pre-v76-evidence-review-gate"]):
        return 200, _ok(sm_v45.build_pre_v76_evidence_review_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))
    if parts in (["self-maintenance", "sandbox-evidence-review-recommendation-layer"], ["release", "sandbox-evidence-review-recommendation-layer"], ["autonomy", "sandbox-evidence-review-recommendation-layer"], ["patch-evidence", "layer"], ["sandbox-evidence-review-recommendation-layer"]):
        return 200, _ok(sm_v45.build_sandbox_evidence_review_recommendation_layer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, save=False))

    approval_file = query.get("patch_approval_file", query.get("approval_file", [None]))[0]
    approval_phrase = query.get("approval_phrase", [None])[0]
    approved_files = query.get("approved_files", query.get("patch_approved_files", [None]))[0]
    application_id = query.get("patch_application_id", query.get("application_id", [None]))[0]
    operator_label = query.get("operator", query.get("operator_label", ["api-preview"]))[0]
    apply_approved = query.get("patch_apply_approved", query.get("approved", ["false"]))[0].lower() in {"1", "true", "yes"}
    if parts in (["self-maintenance", "patch-approval-intake-contract"], ["release", "patch-approval-intake-contract"], ["autonomy", "patch-approval-intake-contract"], ["patch-apply", "approval"], ["patch-approval-intake-contract"]):
        return 200, _ok(sm_v45.build_patch_approval_intake_contract(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, save=False))
    if parts in (["self-maintenance", "recommendation-approval-binder"], ["release", "recommendation-approval-binder"], ["autonomy", "recommendation-approval-binder"], ["patch-apply", "bind"], ["recommendation-approval-binder"]):
        return 200, _ok(sm_v45.build_recommendation_approval_binder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, save=False))
    if parts in (["self-maintenance", "live-source-snapshot-builder"], ["release", "live-source-snapshot-builder"], ["autonomy", "live-source-snapshot-builder"], ["patch-apply", "snapshot"], ["live-source-snapshot-builder"]):
        return 200, _ok(sm_v45.build_live_source_snapshot_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, save=False))
    if parts in (["self-maintenance", "approved-patch-materializer"], ["release", "approved-patch-materializer"], ["autonomy", "approved-patch-materializer"], ["patch-apply", "apply"], ["approved-patch-materializer"]):
        return 200, _ok(sm_v45.build_approved_patch_materializer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, dry_run=True, save=False))
    if parts in (["self-maintenance", "post-apply-verification-runner"], ["release", "post-apply-verification-runner"], ["autonomy", "post-apply-verification-runner"], ["patch-apply", "verify"], ["post-apply-verification-runner"]):
        return 200, _ok(sm_v45.build_post_apply_verification_runner(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, dry_run=True, save=False))
    if parts in (["self-maintenance", "automatic-rollback-executor"], ["release", "automatic-rollback-executor"], ["autonomy", "automatic-rollback-executor"], ["patch-apply", "rollback"], ["automatic-rollback-executor"]):
        return 200, _ok(sm_v45.build_automatic_rollback_executor(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, dry_run=True, verification_failed=True, save=False))
    if parts in (["self-maintenance", "application-evidence-recorder"], ["release", "application-evidence-recorder"], ["autonomy", "application-evidence-recorder"], ["patch-apply", "evidence"], ["application-evidence-recorder"]):
        return 200, _ok(sm_v45.build_application_evidence_recorder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, dry_run=True, save=False))
    if parts in (["self-maintenance", "patch-application-dashboard-api-cli"], ["release", "patch-application-dashboard-api-cli"], ["autonomy", "patch-application-dashboard-api-cli"], ["patch-apply", "parity"], ["patch-application-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_application_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "pre-v77-application-gate"], ["release", "pre-v77-application-gate"], ["autonomy", "pre-v77-application-gate"], ["patch-apply", "gate"], ["pre-v77-application-gate"]):
        return 200, _ok(sm_v45.build_pre_v77_application_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, operator_label=operator_label, save=False))
    if parts in (["self-maintenance", "operator-approved-patch-application-layer"], ["release", "operator-approved-patch-application-layer"], ["autonomy", "operator-approved-patch-application-layer"], ["patch-apply", "layer"], ["operator-approved-patch-application-layer"]):
        return 200, _ok(sm_v45.build_operator_approved_patch_application_layer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approval_phrase=approval_phrase, approved_files=approved_files, application_id=application_id, operator_label=operator_label, apply_approved=apply_approved, dry_run=True, save=False))

    if parts in (["self-maintenance", "dirty-tree-preflight-detector"], ["release", "dirty-tree-preflight-detector"], ["autonomy", "dirty-tree-preflight-detector"], ["patch-recovery", "preflight"], ["dirty-tree-preflight-detector"]):
        return 200, _ok(sm_v45.build_dirty_tree_preflight_detector(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "snapshot-completeness-validator"], ["release", "snapshot-completeness-validator"], ["autonomy", "snapshot-completeness-validator"], ["patch-recovery", "snapshot"], ["snapshot-completeness-validator"]):
        return 200, _ok(sm_v45.build_snapshot_completeness_validator(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "partial-apply-detector"], ["release", "partial-apply-detector"], ["autonomy", "partial-apply-detector"], ["patch-recovery", "partial-apply"], ["partial-apply-detector"]):
        return 200, _ok(sm_v45.build_partial_apply_detector(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "rollback-integrity-verifier"], ["release", "rollback-integrity-verifier"], ["autonomy", "rollback-integrity-verifier"], ["patch-recovery", "rollback-integrity"], ["rollback-integrity-verifier"]):
        return 200, _ok(sm_v45.build_rollback_integrity_verifier(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "failed-verification-triage"], ["release", "failed-verification-triage"], ["autonomy", "failed-verification-triage"], ["patch-recovery", "triage"], ["failed-verification-triage"]):
        return 200, _ok(sm_v45.build_failed_verification_triage(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "recovery-recommendation-builder"], ["release", "recovery-recommendation-builder"], ["autonomy", "recovery-recommendation-builder"], ["patch-recovery", "recommendation"], ["recovery-recommendation-builder"]):
        return 200, _ok(sm_v45.build_recovery_recommendation_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "application-audit-timeline"], ["release", "application-audit-timeline"], ["autonomy", "application-audit-timeline"], ["patch-recovery", "timeline"], ["application-audit-timeline"]):
        return 200, _ok(sm_v45.build_application_audit_timeline(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "patch-recovery-dashboard-api-cli"], ["release", "patch-recovery-dashboard-api-cli"], ["autonomy", "patch-recovery-dashboard-api-cli"], ["patch-recovery", "parity"], ["patch-recovery-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_recovery_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "pre-v78-recovery-gate"], ["release", "pre-v78-recovery-gate"], ["autonomy", "pre-v78-recovery-gate"], ["patch-recovery", "gate"], ["pre-v78-recovery-gate"]):
        return 200, _ok(sm_v45.build_pre_v78_recovery_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))
    if parts in (["self-maintenance", "verified-application-recovery-rollback-hardening"], ["release", "verified-application-recovery-rollback-hardening"], ["autonomy", "verified-application-recovery-rollback-hardening"], ["patch-recovery", "layer"], ["verified-application-recovery-rollback-hardening"]):
        return 200, _ok(sm_v45.build_verified_application_recovery_rollback_hardening(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, draft_text=draft_text, draft_file=draft_file, trial_id=trial_id, evidence_file=evidence_file, approval_file=approval_file, approved_files=approved_files, application_id=application_id, save=False))

    queue_file = query.get("patch_queue_file", query.get("queue_file", [None]))[0]
    queue_id = query.get("patch_queue_id", query.get("queue_id", [None]))[0]
    if parts in (["self-maintenance", "patch-queue-record-schema"], ["release", "patch-queue-record-schema"], ["autonomy", "patch-queue-record-schema"], ["patch-queue", "schema"], ["patch-queue-record-schema"]):
        return 200, _ok(sm_v45.build_patch_queue_record_schema(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-intake-organizer"], ["release", "patch-queue-intake-organizer"], ["autonomy", "patch-queue-intake-organizer"], ["patch-queue", "intake"], ["patch-queue-intake-organizer"]):
        return 200, _ok(sm_v45.build_patch_queue_intake_organizer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-conflict-detector"], ["release", "patch-queue-conflict-detector"], ["autonomy", "patch-queue-conflict-detector"], ["patch-queue", "conflicts"], ["patch-queue-conflict-detector"]):
        return 200, _ok(sm_v45.build_patch_queue_conflict_detector(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-risk-priority-scheduler"], ["release", "patch-queue-risk-priority-scheduler"], ["autonomy", "patch-queue-risk-priority-scheduler"], ["patch-queue", "priority"], ["patch-queue-risk-priority-scheduler"]):
        return 200, _ok(sm_v45.build_patch_queue_risk_priority_scheduler(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-stale-evidence-detector"], ["release", "patch-queue-stale-evidence-detector"], ["autonomy", "patch-queue-stale-evidence-detector"], ["patch-queue", "stale-evidence"], ["patch-queue-stale-evidence-detector"]):
        return 200, _ok(sm_v45.build_patch_queue_stale_evidence_detector(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-serial-trial-plan-builder"], ["release", "patch-queue-serial-trial-plan-builder"], ["autonomy", "patch-queue-serial-trial-plan-builder"], ["patch-queue", "serial-plan"], ["patch-queue-serial-trial-plan-builder"]):
        return 200, _ok(sm_v45.build_patch_queue_serial_trial_plan_builder(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-operator-review-packet"], ["release", "patch-queue-operator-review-packet"], ["autonomy", "patch-queue-operator-review-packet"], ["patch-queue", "review-packet"], ["patch-queue-operator-review-packet"]):
        return 200, _ok(sm_v45.build_patch_queue_operator_review_packet(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "patch-queue-dashboard-api-cli"], ["release", "patch-queue-dashboard-api-cli"], ["autonomy", "patch-queue-dashboard-api-cli"], ["patch-queue", "parity"], ["patch-queue-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_patch_queue_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, save=False))
    if parts in (["self-maintenance", "pre-v79-queue-gate"], ["release", "pre-v79-queue-gate"], ["autonomy", "pre-v79-queue-gate"], ["patch-queue", "gate"], ["pre-v79-queue-gate"]):
        return 200, _ok(sm_v45.build_pre_v79_queue_gate(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))
    if parts in (["self-maintenance", "multi-patch-queue-planning-layer"], ["release", "multi-patch-queue-planning-layer"], ["autonomy", "multi-patch-queue-planning-layer"], ["patch-queue", "layer"], ["multi-patch-queue-planning-layer"]):
        return 200, _ok(sm_v45.build_multi_patch_queue_planning_layer(project_id=query.get("project", ["eidolon"])[0], patch_goal=patch_goal, queue_file=queue_file, queue_id=queue_id, save=False))

    improvement_goal = query.get("improvement_goal", query.get("patch_goal", [None]))[0]
    local_model_name = query.get("local_model_name", query.get("model", [None]))[0]
    improvement_cycle_id = query.get("improvement_cycle_id", query.get("cycle_id", [None]))[0]
    candidate_file = query.get("candidate_file", [None])[0]
    if parts in (["self-maintenance", "improvement-opportunity-intake"], ["release", "improvement-opportunity-intake"], ["autonomy", "improvement-opportunity-intake"], ["improvement-loop", "intake"], ["improvement-opportunity-intake"]):
        return 200, _ok(sm_v45.build_improvement_opportunity_intake(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "improvement-cycle-state-machine"], ["release", "improvement-cycle-state-machine"], ["autonomy", "improvement-cycle-state-machine"], ["improvement-loop", "state"], ["improvement-cycle-state-machine"]):
        return 200, _ok(sm_v45.build_improvement_cycle_state_machine(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pipeline-stage-binder"], ["release", "pipeline-stage-binder"], ["autonomy", "pipeline-stage-binder"], ["improvement-loop", "binder"], ["pipeline-stage-binder"]):
        return 200, _ok(sm_v45.build_pipeline_stage_binder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "local-model-invocation-stub"], ["release", "local-model-invocation-stub"], ["autonomy", "local-model-invocation-stub"], ["improvement-loop", "model-stub"], ["local-model-invocation-stub"]):
        return 200, _ok(sm_v45.build_local_model_invocation_stub(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "improvement-loop-evidence-recorder"], ["release", "improvement-loop-evidence-recorder"], ["autonomy", "improvement-loop-evidence-recorder"], ["improvement-loop", "evidence"], ["improvement-loop-evidence-recorder"]):
        return 200, _ok(sm_v45.build_improvement_loop_evidence_recorder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "operator-stop-gate"], ["release", "operator-stop-gate"], ["autonomy", "operator-stop-gate"], ["improvement-loop", "stop-gate"], ["operator-stop-gate"]):
        return 200, _ok(sm_v45.build_operator_stop_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "improvement-loop-dashboard-api-cli"], ["release", "improvement-loop-dashboard-api-cli"], ["autonomy", "improvement-loop-dashboard-api-cli"], ["improvement-loop", "parity"], ["improvement-loop-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_improvement_loop_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "loop-safety-auditor"], ["release", "loop-safety-auditor"], ["autonomy", "loop-safety-auditor"], ["improvement-loop", "safety"], ["loop-safety-auditor"]):
        return 200, _ok(sm_v45.build_loop_safety_auditor(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v80-supervised-loop-gate"], ["release", "pre-v80-supervised-loop-gate"], ["autonomy", "pre-v80-supervised-loop-gate"], ["improvement-loop", "gate"], ["pre-v80-supervised-loop-gate"]):
        return 200, _ok(sm_v45.build_pre_v80_supervised_loop_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "supervised-local-improvement-loop"], ["release", "supervised-local-improvement-loop"], ["autonomy", "supervised-local-improvement-loop"], ["improvement-loop", "layer"], ["supervised-local-improvement-loop"]):
        return 200, _ok(sm_v45.build_supervised_local_improvement_loop(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "local-model-adapter-contract"], ["release", "local-model-adapter-contract"], ["autonomy", "local-model-adapter-contract"], ["local-model-proposals", "adapter"], ["local-model-adapter-contract"]):
        return 200, _ok(sm_v45.build_local_model_adapter_contract(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "model-capability-profile"], ["release", "model-capability-profile"], ["autonomy", "model-capability-profile"], ["local-model-proposals", "profile"], ["model-capability-profile"]):
        return 200, _ok(sm_v45.build_model_capability_profile(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "prompt-export-invocation-guard"], ["release", "prompt-export-invocation-guard"], ["autonomy", "prompt-export-invocation-guard"], ["local-model-proposals", "prompt-export"], ["prompt-export-invocation-guard"]):
        return 200, _ok(sm_v45.build_prompt_export_invocation_guard(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "proposal-capture-parser"], ["release", "proposal-capture-parser"], ["autonomy", "proposal-capture-parser"], ["local-model-proposals", "capture"], ["proposal-capture-parser"]):
        return 200, _ok(sm_v45.build_proposal_capture_parser(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "proposal-safety-precheck"], ["release", "proposal-safety-precheck"], ["autonomy", "proposal-safety-precheck"], ["local-model-proposals", "safety"], ["proposal-safety-precheck"]):
        return 200, _ok(sm_v45.build_proposal_safety_precheck(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "model-output-provenance-recorder"], ["release", "model-output-provenance-recorder"], ["autonomy", "model-output-provenance-recorder"], ["local-model-proposals", "provenance"], ["model-output-provenance-recorder"]):
        return 200, _ok(sm_v45.build_model_output_provenance_recorder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "proposal-integration-dashboard-api-cli"], ["release", "proposal-integration-dashboard-api-cli"], ["autonomy", "proposal-integration-dashboard-api-cli"], ["local-model-proposals", "parity"], ["proposal-integration-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_proposal_integration_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "disabled-by-default-invocation-gate"], ["release", "disabled-by-default-invocation-gate"], ["autonomy", "disabled-by-default-invocation-gate"], ["local-model-proposals", "disabled-gate"], ["disabled-by-default-invocation-gate"]):
        return 200, _ok(sm_v45.build_disabled_by_default_invocation_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v81-model-integration-gate"], ["release", "pre-v81-model-integration-gate"], ["autonomy", "pre-v81-model-integration-gate"], ["local-model-proposals", "gate"], ["pre-v81-model-integration-gate"]):
        return 200, _ok(sm_v45.build_pre_v81_model_integration_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "local-model-patch-proposal-integration"], ["release", "local-model-patch-proposal-integration"], ["autonomy", "local-model-patch-proposal-integration"], ["local-model-proposals", "layer"], ["local-model-patch-proposal-integration"]):
        return 200, _ok(sm_v45.build_local_model_patch_proposal_integration(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "proposal-collection-intake"], ["release", "proposal-collection-intake"], ["autonomy", "proposal-collection-intake"], ["proposal-critique", "intake"], ["proposal-collection-intake"]):
        return 200, _ok(sm_v45.build_proposal_collection_intake(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "candidate-diff-normalizer"], ["release", "candidate-diff-normalizer"], ["autonomy", "candidate-diff-normalizer"], ["proposal-critique", "diff-normalize"], ["candidate-diff-normalizer"]):
        return 200, _ok(sm_v45.build_candidate_diff_normalizer(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "proposal-quality-heuristic-scorer"], ["release", "proposal-quality-heuristic-scorer"], ["autonomy", "proposal-quality-heuristic-scorer"], ["proposal-critique", "quality"], ["proposal-quality-heuristic-scorer"]):
        return 200, _ok(sm_v45.build_proposal_quality_heuristic_scorer(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "safety-scope-comparison"], ["release", "safety-scope-comparison"], ["autonomy", "safety-scope-comparison"], ["proposal-critique", "safety-scope"], ["safety-scope-comparison"]):
        return 200, _ok(sm_v45.build_safety_scope_comparison(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "verification-plan-comparison"], ["release", "verification-plan-comparison"], ["autonomy", "verification-plan-comparison"], ["proposal-critique", "verification"], ["verification-plan-comparison"]):
        return 200, _ok(sm_v45.build_verification_plan_comparison(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "critique-report-builder"], ["release", "critique-report-builder"], ["autonomy", "critique-report-builder"], ["proposal-critique", "report"], ["critique-report-builder"]):
        return 200, _ok(sm_v45.build_critique_report_builder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "critique-dashboard-api-cli"], ["release", "critique-dashboard-api-cli"], ["autonomy", "critique-dashboard-api-cli"], ["proposal-critique", "parity"], ["critique-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_critique_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "operator-review-bundle-exporter"], ["release", "operator-review-bundle-exporter"], ["autonomy", "operator-review-bundle-exporter"], ["proposal-critique", "operator-bundle"], ["operator-review-bundle-exporter"]):
        return 200, _ok(sm_v45.build_operator_review_bundle_exporter(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v82-output-critique-gate"], ["release", "pre-v82-output-critique-gate"], ["autonomy", "pre-v82-output-critique-gate"], ["proposal-critique", "gate"], ["pre-v82-output-critique-gate"]):
        return 200, _ok(sm_v45.build_pre_v82_output_critique_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "local-model-output-comparison-critique"], ["release", "local-model-output-comparison-critique"], ["autonomy", "local-model-output-comparison-critique"], ["proposal-critique", "layer"], ["local-model-output-comparison-critique"]):
        return 200, _ok(sm_v45.build_local_model_output_comparison_critique(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "candidate-registry-schema"], ["release", "candidate-registry-schema"], ["autonomy", "candidate-registry-schema"], ["candidate-ranking", "schema"], ["candidate-registry-schema"]):
        return 200, _ok(sm_v45.build_candidate_registry_schema(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "candidate-deduplication"], ["release", "candidate-deduplication"], ["autonomy", "candidate-deduplication"], ["candidate-ranking", "dedupe"], ["candidate-deduplication"]):
        return 200, _ok(sm_v45.build_candidate_deduplication(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "risk-weighted-ranking"], ["release", "risk-weighted-ranking"], ["autonomy", "risk-weighted-ranking"], ["candidate-ranking", "risk-ranking"], ["risk-weighted-ranking"]):
        return 200, _ok(sm_v45.build_risk_weighted_ranking(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "conflict-aware-grouping"], ["release", "conflict-aware-grouping"], ["autonomy", "conflict-aware-grouping"], ["candidate-ranking", "conflicts"], ["conflict-aware-grouping"]):
        return 200, _ok(sm_v45.build_conflict_aware_grouping(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "evidence-completeness-ranker"], ["release", "evidence-completeness-ranker"], ["autonomy", "evidence-completeness-ranker"], ["candidate-ranking", "evidence"], ["evidence-completeness-ranker"]):
        return 200, _ok(sm_v45.build_evidence_completeness_ranker(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "ranking-explainer"], ["release", "ranking-explainer"], ["autonomy", "ranking-explainer"], ["candidate-ranking", "explainer"], ["ranking-explainer"]):
        return 200, _ok(sm_v45.build_ranking_explainer(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "ranking-dashboard-api-cli"], ["release", "ranking-dashboard-api-cli"], ["autonomy", "ranking-dashboard-api-cli"], ["candidate-ranking", "parity"], ["ranking-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_ranking_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "operator-selection-packet"], ["release", "operator-selection-packet"], ["autonomy", "operator-selection-packet"], ["candidate-ranking", "selection"], ["operator-selection-packet"]):
        return 200, _ok(sm_v45.build_operator_selection_packet(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v83-ranking-gate"], ["release", "pre-v83-ranking-gate"], ["autonomy", "pre-v83-ranking-gate"], ["candidate-ranking", "gate"], ["pre-v83-ranking-gate"]):
        return 200, _ok(sm_v45.build_pre_v83_ranking_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "multi-model-patch-candidate-ranking"], ["release", "multi-model-patch-candidate-ranking"], ["autonomy", "multi-model-patch-candidate-ranking"], ["candidate-ranking", "layer"], ["multi-model-patch-candidate-ranking"]):
        return 200, _ok(sm_v45.build_multi_model_patch_candidate_ranking(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "refinement-goal-binder"], ["release", "refinement-goal-binder"], ["autonomy", "refinement-goal-binder"], ["candidate-refinement", "goal"], ["refinement-goal-binder"]):
        return 200, _ok(sm_v45.build_refinement_goal_binder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "critique-revision-prompt-builder"], ["release", "critique-revision-prompt-builder"], ["autonomy", "critique-revision-prompt-builder"], ["candidate-refinement", "revision-prompt"], ["critique-revision-prompt-builder"]):
        return 200, _ok(sm_v45.build_critique_revision_prompt_builder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "constrained-revision-scope-builder"], ["release", "constrained-revision-scope-builder"], ["autonomy", "constrained-revision-scope-builder"], ["candidate-refinement", "scope"], ["constrained-revision-scope-builder"]):
        return 200, _ok(sm_v45.build_constrained_revision_scope_builder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "refinement-safety-reviewer"], ["release", "refinement-safety-reviewer"], ["autonomy", "refinement-safety-reviewer"], ["candidate-refinement", "safety"], ["refinement-safety-reviewer"]):
        return 200, _ok(sm_v45.build_refinement_safety_reviewer(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "refinement-evidence-recorder"], ["release", "refinement-evidence-recorder"], ["autonomy", "refinement-evidence-recorder"], ["candidate-refinement", "evidence"], ["refinement-evidence-recorder"]):
        return 200, _ok(sm_v45.build_refinement_evidence_recorder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "refinement-iteration-limiter"], ["release", "refinement-iteration-limiter"], ["autonomy", "refinement-iteration-limiter"], ["candidate-refinement", "iteration-limit"], ["refinement-iteration-limiter"]):
        return 200, _ok(sm_v45.build_refinement_iteration_limiter(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "refinement-dashboard-api-cli"], ["release", "refinement-dashboard-api-cli"], ["autonomy", "refinement-dashboard-api-cli"], ["candidate-refinement", "parity"], ["refinement-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_refinement_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "operator-revision-packet"], ["release", "operator-revision-packet"], ["autonomy", "operator-revision-packet"], ["candidate-refinement", "operator-packet"], ["operator-revision-packet"]):
        return 200, _ok(sm_v45.build_operator_revision_packet(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v84-refinement-gate"], ["release", "pre-v84-refinement-gate"], ["autonomy", "pre-v84-refinement-gate"], ["candidate-refinement", "gate"], ["pre-v84-refinement-gate"]):
        return 200, _ok(sm_v45.build_pre_v84_refinement_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "supervised-patch-candidate-refinement"], ["release", "supervised-patch-candidate-refinement"], ["autonomy", "supervised-patch-candidate-refinement"], ["candidate-refinement", "layer"], ["supervised-patch-candidate-refinement"]):
        return 200, _ok(sm_v45.build_supervised_patch_candidate_refinement(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-source-intake"], ["release", "suggestion-source-intake"], ["autonomy", "suggestion-source-intake"], ["suggestion-loop", "intake"], ["suggestion-source-intake"]):
        return 200, _ok(sm_v45.build_suggestion_source_intake(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-cycle-state-machine"], ["release", "suggestion-cycle-state-machine"], ["autonomy", "suggestion-cycle-state-machine"], ["suggestion-loop", "state"], ["suggestion-cycle-state-machine"]):
        return 200, _ok(sm_v45.build_suggestion_cycle_state_machine(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "recurring-suggestion-budgeter"], ["release", "recurring-suggestion-budgeter"], ["autonomy", "recurring-suggestion-budgeter"], ["suggestion-loop", "budget"], ["recurring-suggestion-budgeter"]):
        return 200, _ok(sm_v45.build_recurring_suggestion_budgeter(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "safety-boundary-enforcer"], ["release", "safety-boundary-enforcer"], ["autonomy", "safety-boundary-enforcer"], ["suggestion-loop", "safety"], ["safety-boundary-enforcer"]):
        return 200, _ok(sm_v45.build_safety_boundary_enforcer(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-deduplication-memory"], ["release", "suggestion-deduplication-memory"], ["autonomy", "suggestion-deduplication-memory"], ["suggestion-loop", "dedupe"], ["suggestion-deduplication-memory"]):
        return 200, _ok(sm_v45.build_suggestion_deduplication_memory(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "operator-attention-packet"], ["release", "operator-attention-packet"], ["autonomy", "operator-attention-packet"], ["suggestion-loop", "attention"], ["operator-attention-packet"]):
        return 200, _ok(sm_v45.build_operator_attention_packet(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-loop-dashboard-api-cli"], ["release", "suggestion-loop-dashboard-api-cli"], ["autonomy", "suggestion-loop-dashboard-api-cli"], ["suggestion-loop", "parity"], ["suggestion-loop-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_suggestion_loop_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "no-autonomous-apply-auditor"], ["release", "no-autonomous-apply-auditor"], ["autonomy", "no-autonomous-apply-auditor"], ["suggestion-loop", "no-apply"], ["no-autonomous-apply-auditor"]):
        return 200, _ok(sm_v45.build_no_autonomous_apply_auditor(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v85-suggestion-loop-gate"], ["release", "pre-v85-suggestion-loop-gate"], ["autonomy", "pre-v85-suggestion-loop-gate"], ["suggestion-loop", "gate"], ["pre-v85-suggestion-loop-gate"]):
        return 200, _ok(sm_v45.build_pre_v85_suggestion_loop_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "safe-autonomous-suggestion-loop"], ["release", "safe-autonomous-suggestion-loop"], ["autonomy", "safe-autonomous-suggestion-loop"], ["suggestion-loop", "layer"], ["safe-autonomous-suggestion-loop"]):
        return 200, _ok(sm_v45.build_safe_autonomous_suggestion_loop(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, model_name=local_model_name, cycle_id=improvement_cycle_id, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-inbox-record-schema"], ["release", "suggestion-inbox-record-schema"], ["autonomy", "suggestion-inbox-record-schema"], ["suggestion-inbox", "schema"], ["suggestion-inbox-record-schema"]):
        return 200, _ok(sm_v45.build_suggestion_inbox_record_schema(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-intake-normalizer"], ["release", "suggestion-intake-normalizer"], ["autonomy", "suggestion-intake-normalizer"], ["suggestion-inbox", "intake"], ["suggestion-intake-normalizer"]):
        return 200, _ok(sm_v45.build_suggestion_intake_normalizer(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-deduplication-drift-resolver"], ["release", "suggestion-deduplication-drift-resolver"], ["autonomy", "suggestion-deduplication-drift-resolver"], ["suggestion-inbox", "dedupe"], ["suggestion-deduplication-drift-resolver"]):
        return 200, _ok(sm_v45.build_suggestion_deduplication_drift_resolver(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "operator-triage-state-machine"], ["release", "operator-triage-state-machine"], ["autonomy", "operator-triage-state-machine"], ["suggestion-inbox", "triage"], ["operator-triage-state-machine"]):
        return 200, _ok(sm_v45.build_operator_triage_state_machine(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "work-order-draft-builder"], ["release", "work-order-draft-builder"], ["autonomy", "work-order-draft-builder"], ["suggestion-inbox", "work-order-draft"], ["work-order-draft-builder"]):
        return 200, _ok(sm_v45.build_work_order_draft_builder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "safety-scope-contract-binder"], ["release", "safety-scope-contract-binder"], ["autonomy", "safety-scope-contract-binder"], ["suggestion-inbox", "safety"], ["safety-scope-contract-binder"]):
        return 200, _ok(sm_v45.build_safety_scope_contract_binder(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pipeline-handoff-planner"], ["release", "pipeline-handoff-planner"], ["autonomy", "pipeline-handoff-planner"], ["suggestion-inbox", "handoff"], ["pipeline-handoff-planner"]):
        return 200, _ok(sm_v45.build_pipeline_handoff_planner(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "suggestion-inbox-dashboard-api-cli"], ["release", "suggestion-inbox-dashboard-api-cli"], ["autonomy", "suggestion-inbox-dashboard-api-cli"], ["suggestion-inbox", "parity"], ["suggestion-inbox-dashboard-api-cli"]):
        return 200, _ok(sm_v45.build_suggestion_inbox_dashboard_api_cli(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "pre-v86-suggestion-inbox-gate"], ["release", "pre-v86-suggestion-inbox-gate"], ["autonomy", "pre-v86-suggestion-inbox-gate"], ["suggestion-inbox", "gate"], ["pre-v86-suggestion-inbox-gate"]):
        return 200, _ok(sm_v45.build_pre_v86_suggestion_inbox_gate(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))
    if parts in (["self-maintenance", "supervised-suggestion-inbox-work-order-planner"], ["release", "supervised-suggestion-inbox-work-order-planner"], ["autonomy", "supervised-suggestion-inbox-work-order-planner"], ["suggestion-inbox", "layer"], ["supervised-suggestion-inbox-work-order-planner"]):
        return 200, _ok(sm_v45.build_supervised_suggestion_inbox_work_order_planner(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))


    # v120.1-v125.0 supervised development learning API routes intentionally handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/development-outcome-review/collector /api/development-outcome-review/comparison /api/development-outcome-review/missed /api/development-outcome-review/unexpected /api/development-outcome-review/verification /api/development-outcome-review/burden /api/development-outcome-review/binder /api/development-outcome-review/parity /api/development-outcome-review/gate /api/development-outcome-review/layer /api/lesson-extraction/schema /api/lesson-extraction/bugs /api/lesson-extraction/successes /api/lesson-extraction/false-alarms /api/lesson-extraction/usefulness /api/lesson-extraction/memory-boundary /api/lesson-extraction/packet /api/lesson-extraction/parity /api/lesson-extraction/gate /api/lesson-extraction/layer /api/recommendation-refinement/schema /api/recommendation-refinement/accuracy /api/recommendation-refinement/mistakes /api/recommendation-refinement/noise /api/recommendation-refinement/adjuster /api/recommendation-refinement/safety /api/recommendation-refinement/binder /api/recommendation-refinement/parity /api/recommendation-refinement/gate /api/recommendation-refinement/layer /api/operator-feedback-integration/schema /api/operator-feedback-integration/standing-rules /api/operator-feedback-integration/temporary /api/operator-feedback-integration/contradictions /api/operator-feedback-integration/work-packages /api/operator-feedback-integration/packet /api/operator-feedback-integration/safety /api/operator-feedback-integration/parity /api/operator-feedback-integration/gate /api/operator-feedback-integration/layer /api/development-learning-audit/walkthrough /api/development-learning-audit/lesson-quality /api/development-learning-audit/recommendations /api/development-learning-audit/feedback /api/development-learning-audit/memory /api/development-learning-audit/safety /api/development-learning-audit/burden /api/development-learning-audit/parity /api/development-learning-audit/gate /api/development-learning-audit/layer
    # v115.1-v120.0 supervised development execution API routes intentionally handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/development-session-planner/intent /api/development-session-planner/scope /api/development-session-planner/files /api/development-session-planner/tests /api/development-session-planner/docs /api/development-session-planner/safety /api/development-session-planner/decisions /api/development-session-planner/parity /api/development-session-planner/gate /api/development-session-planner/layer /api/source-change-cartographer/inventory /api/source-change-cartographer/route-parity /api/source-change-cartographer/builders /api/source-change-cartographer/docs /api/source-change-cartographer/smoke /api/source-change-cartographer/fragile /api/source-change-cartographer/report /api/source-change-cartographer/parity /api/source-change-cartographer/gate /api/source-change-cartographer/layer /api/patch-simulation/schema /api/patch-simulation/expected-diff /api/patch-simulation/missing /api/patch-simulation/overreach /api/patch-simulation/safety /api/patch-simulation/verification /api/patch-simulation/summary /api/patch-simulation/parity /api/patch-simulation/gate /api/patch-simulation/layer /api/verification-matrix/schema /api/verification-matrix/dashboard /api/verification-matrix/api-cli /api/verification-matrix/packaging /api/verification-matrix/safety /api/verification-matrix/docs /api/verification-matrix/recommendation /api/verification-matrix/parity /api/verification-matrix/gate /api/verification-matrix/layer /api/development-execution-audit/walkthrough /api/development-execution-audit/burden /api/development-execution-audit/quality /api/development-execution-audit/coverage /api/development-execution-audit/safety /api/development-execution-audit/dashboard /api/development-execution-audit/docs /api/development-execution-audit/parity /api/development-execution-audit/gate /api/development-execution-audit/layer
    # v110.1-v115.0 supervised self-development API routes intentionally handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/improvement-intent/inventory /api/improvement-intent/problem /api/improvement-intent/evidence /api/improvement-intent/scope /api/improvement-intent/value /api/improvement-intent/safety /api/improvement-intent/binder /api/improvement-intent/parity /api/improvement-intent/gate /api/improvement-intent/layer /api/work-package-builder/schema /api/work-package-builder/boundary /api/work-package-builder/criteria /api/work-package-builder/tests /api/work-package-builder/docs /api/work-package-builder/risks /api/work-package-builder/packet /api/work-package-builder/parity /api/work-package-builder/gate /api/work-package-builder/layer /api/patch-readiness/schema /api/patch-readiness/expectations /api/patch-readiness/completeness /api/patch-readiness/contradictions /api/patch-readiness/safety /api/patch-readiness/dashboard /api/patch-readiness/summary /api/patch-readiness/parity /api/patch-readiness/gate /api/patch-readiness/layer /api/release-candidate-judgment/schema /api/release-candidate-judgment/version /api/release-candidate-judgment/route-parity /api/release-candidate-judgment/docs /api/release-candidate-judgment/privacy /api/release-candidate-judgment/install /api/release-candidate-judgment/recommendation /api/release-candidate-judgment/coverage /api/release-candidate-judgment/gate /api/release-candidate-judgment/layer /api/supervised-development-readiness/walkthrough /api/supervised-development-readiness/burden /api/supervised-development-readiness/safety /api/supervised-development-readiness/evidence /api/supervised-development-readiness/trace /api/supervised-development-readiness/dashboard /api/supervised-development-readiness/release-process /api/supervised-development-readiness/parity /api/supervised-development-readiness/gate /api/supervised-development-readiness/layer
    # v105.1-v110.0 practical coherence API routes intentionally handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/memory-quality/inventory /api/memory-quality/freshness /api/memory-quality/conflicts /api/memory-quality/evidence /api/memory-quality/relevance /api/memory-quality/corrections /api/memory-quality/parity /api/memory-quality/privacy /api/memory-quality/gate /api/memory-quality/layer /api/goal-continuity/inventory /api/goal-continuity/lifecycle /api/goal-continuity/evidence /api/goal-continuity/priority /api/goal-continuity/blocked /api/goal-continuity/contradictions /api/goal-continuity/summary /api/goal-continuity/parity /api/goal-continuity/gate /api/goal-continuity/layer /api/reasoning-workbench/schema /api/reasoning-workbench/context /api/reasoning-workbench/permission /api/reasoning-workbench/capture /api/reasoning-workbench/rubric /api/reasoning-workbench/boundaries /api/reasoning-workbench/evidence /api/reasoning-workbench/parity /api/reasoning-workbench/gate /api/reasoning-workbench/layer /api/workflow-console/friction /api/workflow-console/queue /api/workflow-console/commands /api/workflow-console/packets /api/workflow-console/consolidation /api/workflow-console/lazy-loader /api/workflow-console/tooltips /api/workflow-console/parity /api/workflow-console/gate /api/workflow-console/layer /api/practical-mind-audit/walkthrough /api/practical-mind-audit/memory /api/practical-mind-audit/goals /api/practical-mind-audit/reasoning /api/practical-mind-audit/burden /api/practical-mind-audit/dashboard /api/practical-mind-audit/safety /api/practical-mind-audit/parity /api/practical-mind-audit/gate /api/practical-mind-audit/layer
    # v100.1-v105.0 coherent runtime API routes intentionally handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/v100-stabilization/inventory /api/v100-stabilization/duplicates /api/v100-stabilization/dashboard-review /api/v100-stabilization/coverage /api/v100-stabilization/privacy /api/v100-stabilization/operator-friction /api/v100-stabilization/report /api/v100-stabilization/parity /api/v100-stabilization/gate /api/v100-stabilization/layer /api/system-map/schema /api/system-map/core-mind /api/system-map/development-pipeline /api/system-map/governance /api/system-map/operator-home /api/system-map/cross-links /api/system-map/integrity /api/system-map/parity /api/system-map/gate /api/system-map/layer /api/coherence-binder/schema /api/coherence-binder/memory-reflection /api/coherence-binder/reflection-goal /api/coherence-binder/goal-suggestion /api/coherence-binder/outcome-lesson /api/coherence-binder/conflicts /api/coherence-binder/summary /api/coherence-binder/parity /api/coherence-binder/gate /api/coherence-binder/layer /api/daily-loop/schema /api/daily-loop/status /api/daily-loop/priorities /api/daily-loop/operator-actions /api/daily-loop/safety /api/daily-loop/reflection-prompts /api/daily-loop/parity /api/daily-loop/privacy /api/daily-loop/gate /api/daily-loop/layer /api/local-mind-runtime/schema /api/local-mind-runtime/snapshot /api/local-mind-runtime/continuity /api/local-mind-runtime/next-step /api/local-mind-runtime/health /api/local-mind-runtime/contradictions /api/local-mind-runtime/parity /api/local-mind-runtime/containment /api/local-mind-runtime/gate /api/local-mind-runtime/layer
    if parts == ["self-development-cycle", "layer"]:
        return 200, _ok(build_self_development_cycle_api_layer())

    _v90_route_key = "/".join(parts)
    _v90_slug = getattr(sm_v45, "SUPERVISED_DEV_ROUTE_MAP", {}).get(_v90_route_key)
    if _v90_slug:
        return 200, _ok(getattr(sm_v45, f"build_{_v90_slug}")(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))

    _v95_route_key = "/".join(parts)
    _v95_slug = getattr(sm_v45, "SUPERVISED_RUNTIME_ROUTE_MAP", {}).get(_v95_route_key)
    if _v95_slug:
        return 200, _ok(getattr(sm_v45, f"build_{_v95_slug}")(project_id=query.get("project", ["eidolon"])[0], improvement_goal=improvement_goal, candidate_file=candidate_file, save=False))

    if parts in (["self-maintenance", "proposal"], ["release", "self-maintenance-proposal"], ["self-maintenance-proposal"]):
        report = build_self_maintenance_proposal_sandbox(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "patch-plan"], ["release", "build-patch-plan"], ["build-patch-plan"]):
        report = build_patch_plan_builder(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "patch-preview"], ["release", "generate-maintenance-patch"], ["generate-maintenance-patch"]):
        report = build_dry_run_patch_generator(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "safety-audit"], ["release", "patch-safety-audit"], ["patch-safety-audit"]):
        report = build_patch_safety_auditor(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "temp-apply-drill"], ["release", "apply-maintenance-patch-to-temp"], ["apply-maintenance-patch-to-temp"]):
        report = build_apply_patch_to_temp_clone(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "review-bundle"], ["release", "maintenance-review-bundle"], ["maintenance-review-bundle"]):
        report = build_maintenance_review_bundle(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-binding"], ["release", "approve-maintenance-bundle"], ["approve-maintenance-bundle"]):
        report = build_human_approval_binding(project_id=query.get("project", ["eidolon"])[0], bundle_hash=query.get("bundle_hash", [None])[0], confirm=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "apply-gate"], ["release", "real-maintenance-patch-apply"], ["real-maintenance-patch-apply"]):
        report = build_real_maintenance_patch_apply(project_id=query.get("project", ["eidolon"])[0], bundle_hash=query.get("bundle_hash", [None])[0], dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "post-apply-health"], ["release", "post-apply-health-monitor"], ["post-apply-health-monitor"]):
        report = build_post_apply_health_monitor(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "controlled-cycle"], ["release", "controlled-maintenance-cycle"], ["controlled-maintenance-cycle"]):
        report = build_controlled_maintenance_cycle(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "assisted-release"], ["release", "assisted-self-improvement-release"], ["assisted-self-improvement-release"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        zip_path = query.get("zip_path", [None])[0]
        report = build_assisted_self_improvement_release(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "improvement-candidates"], ["release", "improvement-candidate-scan"], ["improvement-candidate-scan"]):
        report = build_improvement_candidate_scan(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "candidate-prioritizer"], ["release", "candidate-prioritizer"], ["candidate-prioritizer"]):
        report = build_candidate_prioritizer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "candidate-to-proposal"], ["release", "candidate-to-proposal"], ["candidate-to-proposal"]):
        report = build_candidate_to_proposal_bridge(project_id=query.get("project", ["eidolon"])[0], candidate_id=query.get("candidate_id", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "maintenance-backlog"], ["release", "maintenance-backlog"], ["maintenance-backlog"]):
        report = build_maintenance_backlog_registry(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-backlog"], ["release", "dashboard-maintenance-backlog"], ["dashboard-maintenance-backlog"]):
        report = build_dashboard_maintenance_backlog(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-backlog"], ["release", "api-maintenance-backlog"], ["api-maintenance-backlog"]):
        report = build_api_maintenance_backlog(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "regression-detector"], ["release", "candidate-regression-detector"], ["candidate-regression-detector"]):
        report = build_candidate_regression_detector(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-memory-privacy"], ["release", "release-memory-privacy"], ["release-memory-privacy"]):
        report = build_release_memory_privacy(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verification-recipes"], ["release", "candidate-verification-recipes"], ["candidate-verification-recipes"]):
        report = build_candidate_verification_recipes(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "assisted-improvement-cycle"], ["release", "assisted-improvement-cycle"], ["assisted-improvement-cycle"]):
        report = build_assisted_improvement_cycle(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "semi-autonomous-review"], ["release", "semi-autonomous-maintenance-review"], ["semi-autonomous-maintenance-review"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        zip_path = query.get("zip_path", [None])[0]
        report = build_semi_autonomous_maintenance_review(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "hotfix-regression-lockdown"], ["release", "hotfix-regression-lockdown"], ["hotfix-regression-lockdown"]):
        report = build_hotfix_regression_lockdown(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-route-coverage"], ["release", "dashboard-route-coverage"], ["dashboard-route-coverage"]):
        report = build_dashboard_route_coverage_auditor(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-default-source-audit"], ["release", "api-default-source-audit"], ["api-default-source-audit"]):
        report = build_api_default_source_audit(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "nested-readiness-severity"], ["release", "nested-readiness-severity"], ["nested-readiness-severity"]):
        report = build_nested_readiness_severity_engine(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "review-bundle-approval-contract"], ["release", "review-bundle-approval-contract"], ["review-bundle-approval-contract"]):
        report = build_review_bundle_approval_contract(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "maintenance-report-diff"], ["release", "maintenance-report-diff"], ["maintenance-report-diff"]):
        report = build_maintenance_report_diff_viewer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-gate-composition-test"], ["release", "release-gate-composition-test"], ["release-gate-composition-test"]):
        report = build_release_gate_composition_test(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-api-parity-audit"], ["release", "dashboard-api-parity-audit"], ["dashboard-api-parity-audit"]):
        report = build_dashboard_api_parity_audit(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "operator-trust-report"], ["release", "operator-trust-report"], ["operator-trust-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_operator_trust_report(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trustworthy-maintenance-console"], ["release", "trustworthy-maintenance-console"], ["trustworthy-maintenance-console"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trustworthy_maintenance_console(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-console-drill"], ["release", "trust-console-drill"], ["trust-console-drill"]):
        report = build_trust_console_drill(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-console-snapshot"], ["release", "trust-console-snapshot"], ["trust-console-snapshot"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trust_console_snapshot(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-console-diff"], ["release", "trust-console-diff"], ["trust-console-diff"]):
        report = build_trust_console_diff(project_id=query.get("project", ["eidolon"])[0], before_path=query.get("before", [None])[0], after_path=query.get("after", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "freeze-release-candidate"], ["release", "freeze-release-candidate"], ["freeze-release-candidate"]):
        report = build_release_candidate_freezer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verify-frozen-release-zip"], ["release", "verify-frozen-release-zip"], ["verify-frozen-release-zip"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_frozen_release_zip_verification(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-evidence-ledger"], ["release", "approval-evidence-ledger"], ["approval-evidence-ledger"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_evidence_ledger(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-command-reproducer"], ["release", "release-command-reproducer"], ["release-command-reproducer"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_command_reproducer(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "console-readme-consistency"], ["release", "console-readme-consistency"], ["console-readme-consistency"]):
        report = build_console_readme_consistency(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v27-safety-audit"], ["release", "pre-v27-safety-audit"], ["pre-v27-safety-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v27_safety_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-candidate-governance"], ["release", "release-candidate-governance"], ["release-candidate-governance"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_candidate_governance(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))


    if parts in (["self-maintenance", "release-governance-drill"], ["release", "release-governance-drill"], ["release-governance-drill"]):
        report = build_release_governance_drill(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-evidence-bundle"], ["release", "release-evidence-bundle"], ["release-evidence-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_evidence_bundle(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verify-release-evidence-bundle"], ["release", "verify-release-evidence-bundle"], ["verify-release-evidence-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_evidence_bundle_verifier(project_id=project_id, bundle_path=query.get("bundle_path", [None])[0], package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-governance-page"], ["release", "release-governance-page"], ["release-governance-page"]):
        report = build_release_governance_page(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "governance-api-read-only"], ["release", "governance-api-read-only"], ["governance-api-read-only"]):
        report = build_governance_api_read_only_surface(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-artifact-diff"], ["release", "release-artifact-diff"], ["release-artifact-diff"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_artifact_diff(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-signing-preparation"], ["release", "release-signing-preparation"], ["release-signing-preparation"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_signing_preparation(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "local-trust-policy"], ["release", "local-trust-policy"], ["local-trust-policy"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_local_trust_policy(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-governance-ux-polish"], ["release", "release-governance-ux-polish"], ["release-governance-ux-polish"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_governance_ux_polish(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v28-governance-audit"], ["release", "pre-v28-governance-audit"], ["pre-v28-governance-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v28_governance_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verifiable-release-evidence-system"], ["release", "verifiable-release-evidence-system"], ["verifiable-release-evidence-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_verifiable_release_evidence_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))



    if parts in (["self-maintenance", "evidence-replay-drill"], ["release", "evidence-replay-drill"], ["evidence-replay-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_evidence_replay_drill(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "persist-release-evidence"], ["release", "persist-release-evidence"], ["persist-release-evidence"], ["release", "evidence"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_evidence_bundle_persistence(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "replay-release-evidence"], ["release", "replay-release-evidence"], ["replay-release-evidence"], ["release", "evidence", "replay"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_replay_release_evidence(project_id=project_id, bundle_path=query.get("bundle_path", [None])[0], package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-timeline"], ["release", "evidence-timeline"], ["evidence-timeline"]):
        report = build_evidence_timeline(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-summary"], ["release", "evidence-summary"], ["evidence-summary"], ["release", "evidence", "summary"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_evidence_operator_summary(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-evidence-viewer"], ["release", "dashboard-evidence-viewer"], ["dashboard-evidence-viewer"]):
        report = build_dashboard_evidence_viewer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-evidence-viewer"], ["release", "api-evidence-viewer"], ["api-evidence-viewer"]):
        report = build_api_evidence_viewer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-retention-policy"], ["release", "evidence-retention-policy"], ["evidence-retention-policy"]):
        report = build_evidence_retention_policy(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-regression-lockdown"], ["release", "evidence-regression-lockdown"], ["evidence-regression-lockdown"]):
        report = build_evidence_regression_lockdown(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v29-evidence-audit"], ["release", "pre-v29-evidence-audit"], ["pre-v29-evidence-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v29_evidence_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "durable-release-evidence-archive"], ["release", "durable-release-evidence-archive"], ["durable-release-evidence-archive"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_durable_release_evidence_archive(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signing-readiness-audit"], ["release", "signing-readiness-audit"], ["signing-readiness-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signing_readiness_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "canonical-manifest-format"], ["release", "canonical-manifest-format"], ["canonical-manifest-format"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_canonical_manifest_format(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "canonical-evidence-schema"], ["release", "canonical-evidence-schema"], ["canonical-evidence-schema"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_canonical_evidence_schema(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-signing-status"], ["release", "release-signing-status"], ["release", "signing"], ["release-signing-status"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_signing_status(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signature-placeholder-contract"], ["release", "signature-placeholder-contract"], ["signature-placeholder-contract"]):
        report = build_signature_placeholder_contract(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "key-policy-preparation"], ["release", "key-policy-preparation"], ["release", "signing-policy"], ["signing-policy"]):
        report = build_key_policy_preparation(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verify-release-signature"], ["release", "verify-release-signature"], ["release", "signature", "verify"], ["verify-release-signature"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signature_verification_placeholder(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-signing-status"], ["release", "dashboard-signing-status"], ["dashboard-signing-status"]):
        report = build_dashboard_signing_status(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-signing-status"], ["release", "api-signing-status"], ["api-signing-status"]):
        report = build_api_signing_status(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v30-signing-prep-audit"], ["release", "pre-v30-signing-prep-audit"], ["pre-v30-signing-prep-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v30_signing_prep_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-release-preparation-system"], ["release", "signed-release-preparation-system"], ["signed-release-preparation-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_release_preparation_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signing-api-hardening"], ["release", "signing-api-hardening"], ["signing-api-hardening"]):
        report = build_signing_api_hardening(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "canonical-schema-validator"], ["release", "canonical-schema-validator"], ["canonical-schema-validator"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_canonical_schema_validator(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "source-data-sanitizer"], ["release", "source-data-sanitizer"], ["source-data-sanitizer"]):
        report = build_source_data_sanitizer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signing-trust-model"], ["release", "signing-trust-model"], ["signing-trust-model"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signing_trust_model(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-signing-tamper-drill"], ["release", "release-signing-tamper-drill"], ["release-signing-tamper-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_signing_tamper_drill(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "public-key-policy-design"], ["release", "public-key-policy-design"], ["public-key-policy-design"]):
        report = build_public_key_policy_design(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "detached-signature-contract"], ["release", "detached-signature-contract"], ["detached-signature-contract"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_detached_signature_contract(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signature-fixture-verification"], ["release", "signature-fixture-verification"], ["signature-fixture-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signature_fixture_verification(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "external-signer-workflow"], ["release", "external-signer-workflow"], ["external-signer-workflow"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_external_signer_workflow(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "detached-signature-verification-system"], ["release", "detached-signature-verification-system"], ["release", "signature", "detached-verify"], ["detached-signature-verification-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_detached_signature_verification_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signature-verification-hardening"], ["release", "signature-verification-hardening"], ["signature-verification-hardening"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signature_verification_hardening(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "public-trust-root-config"], ["release", "public-trust-root-config"], ["release", "trust-roots"], ["public-trust-root-config"]):
        report = build_public_trust_root_config(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "external-signing-payload-export"], ["release", "external-signing-payload-export"], ["release", "signing-payload"], ["external-signing-payload-export"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_external_signing_payload_export(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-fixture-test-suite"], ["release", "signed-fixture-test-suite"], ["signed-fixture-test-suite"]):
        report = build_signed_fixture_test_suite(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-publish-gate"], ["release", "release-publish-gate"], ["release", "publish-gate"], ["release-publish-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_publish_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-trust-dashboard-polish"], ["release", "release-trust-dashboard-polish"], ["release", "trust-dashboard"], ["release-trust-dashboard-polish"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_trust_dashboard_polish(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-route-safety-audit"], ["release", "api-route-safety-audit"], ["release", "route-safety-audit"], ["api-route-safety-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_api_route_safety_audit(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-reproducibility-check"], ["release", "release-reproducibility-check"], ["release", "reproducibility-check"], ["release-reproducibility-check"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_reproducibility_check(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v32-release-candidate-gate"], ["release", "pre-v32-release-candidate-gate"], ["release", "pre-v32-gate"], ["pre-v32-release-candidate-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v32_release_candidate_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-release-governance"], ["release", "signed-release-governance"], ["release", "governance-v32"], ["signed-release-governance"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_release_governance(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "governance-report-cleanup"], ["release", "governance-report-cleanup"], ["governance-report-cleanup"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_governance_report_cleanup(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-candidate-workspace"], ["release", "release-candidate-workspace"], ["release", "candidate-workspace"], ["release-candidate-workspace"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_candidate_workspace(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "artifact-binding-audit"], ["release", "artifact-binding-audit"], ["release", "artifact-binding-audit-v2"], ["artifact-binding-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_artifact_binding_audit_v2(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "surface-consistency-audit"], ["release", "surface-consistency-audit"], ["release", "surface-consistency"], ["surface-consistency-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_surface_consistency_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "external-signing-handoff"], ["release", "external-signing-handoff"], ["release", "signing-handoff"], ["external-signing-handoff"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_external_signing_handoff(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signature-intake-validation"], ["release", "signature-intake-validation"], ["release", "signature-intake"], ["signature-intake-validation"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signature_intake_validation(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), signature_path=_query_signature_options(query).get("signature_path"), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trusted-signer-registry"], ["release", "trusted-signer-registry"], ["release", "trust-roots", "registry"], ["trusted-signer-registry"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trusted_signer_registry(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "governance-scenario-suite"], ["release", "governance-scenario-suite"], ["release", "scenario-suite"], ["governance-scenario-suite"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_governance_scenario_suite(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v33-operations-gate"], ["release", "pre-v33-operations-gate"], ["release", "pre-v33-gate"], ["pre-v33-operations-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v33_operations_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-operations-console"], ["release", "release-operations-console"], ["release", "operations-console"], ["release-operations-console"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_operations_console(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))


    if parts in (["self-maintenance", "operations-console-cleanup"], ["release", "operations-console-cleanup"], ["release", "operations-cleanup"], ["operations-console-cleanup"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_operations_console_cleanup(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-candidate-review"], ["release", "release-candidate-review"], ["release", "candidate-review"], ["release-candidate-review"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_candidate_review(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-artifact-intake"], ["release", "signed-artifact-intake"], ["release", "signed-intake"], ["signed-artifact-intake"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_artifact_intake(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-root-lifecycle"], ["release", "trust-root-lifecycle"], ["release", "trust-lifecycle"], ["trust-root-lifecycle"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trust_root_lifecycle(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-decision-explainer"], ["release", "publish-decision-explainer"], ["release", "publish-decision"], ["publish-decision-explainer"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_decision_explainer(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "operator-action-guardrails"], ["release", "operator-action-guardrails"], ["release", "operator-guardrails"], ["operator-action-guardrails"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_operator_action_guardrails(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "unsigned-release-drill"], ["release", "unsigned-release-drill"], ["release", "unsigned-drill"], ["unsigned-release-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_unsigned_release_drill(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-fixture-release-drill"], ["release", "signed-fixture-release-drill"], ["release", "signed-fixture-drill"], ["signed-fixture-release-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_fixture_release_drill(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v34-operator-workflow-gate"], ["release", "pre-v34-operator-workflow-gate"], ["release", "pre-v34-gate"], ["pre-v34-operator-workflow-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v34_operator_workflow_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-operator-workflow"], ["release", "release-operator-workflow"], ["release", "operator-workflow"], ["release-operator-workflow"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_operator_workflow(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))


    if parts in (["self-maintenance", "release-candidate-record"], ["release", "release-candidate-record"], ["release", "candidate-record"], ["release-candidate-record"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_candidate_record_v2(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-artifact-intake-v2"], ["release", "signed-artifact-intake-v2"], ["release", "signature-intake-v2"], ["signed-artifact-intake-v2"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_artifact_intake_v2(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-root-management-policy"], ["release", "trust-root-management-policy"], ["release", "trust-policy"], ["trust-root-management-policy"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trust_root_management_policy(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-root-mutation-guardrails"], ["release", "trust-root-mutation-guardrails"], ["release", "trust-mutation-guardrails"], ["trust-root-mutation-guardrails"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trust_root_mutation_guardrails(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-release-publish-decision"], ["release", "signed-release-publish-decision"], ["release", "publish-decision-v2"], ["signed-release-publish-decision"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_release_publish_decision(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "operator-dashboard-action-states"], ["release", "operator-dashboard-action-states"], ["release", "dashboard-action-states"], ["operator-dashboard-action-states"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_operator_dashboard_action_states(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-audit-trail"], ["release", "release-audit-trail"], ["release", "audit-trail"], ["release-audit-trail"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_audit_trail(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trusted-fixture-workflow"], ["release", "trusted-fixture-workflow"], ["release", "fixture-workflow"], ["trusted-fixture-workflow"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trusted_fixture_workflow(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v35-trusted-candidate-gate"], ["release", "pre-v35-trusted-candidate-gate"], ["release", "pre-v35-gate"], ["pre-v35-trusted-candidate-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v35_trusted_candidate_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trusted-release-candidate-system"], ["release", "trusted-release-candidate-system"], ["release", "trusted-candidate-system"], ["release", "candidate-system"], ["trusted-release-candidate-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trusted_release_candidate_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "candidate-review-state"], ["release", "candidate-review-state"], ["release", "review-state"], ["candidate-review-state"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_candidate_review_state(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-policy"], ["release", "publish-approval-policy"], ["publish-approval-policy"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_policy(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-dry-run"], ["release", "publish-approval-dry-run"], ["release", "approval-dry-run"], ["publish-approval-dry-run"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_dry_run(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-record-schema"], ["release", "publish-approval-record-schema"], ["publish-approval-record-schema"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_record_schema(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-approval-state-preview"], ["release", "dashboard-approval-state-preview"], ["release", "approval-state-preview"], ["dashboard-approval-state-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dashboard_approval_state_preview(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-route-safety-audit"], ["release", "approval-route-safety-audit"], ["approval-route-safety-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_route_safety_audit(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-fixture-drill"], ["release", "approval-fixture-drill"], ["approval-fixture-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_fixture_drill(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-explainer"], ["release", "publish-approval-explainer"], ["release", "approval-explainer"], ["publish-approval-explainer"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_explainer(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v36-approval-separation-gate"], ["release", "pre-v36-approval-separation-gate"], ["release", "pre-v36-gate"], ["pre-v36-approval-separation-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v36_approval_separation_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-separation-system"], ["release", "publish-approval-separation-system"], ["release", "approval-separation"], ["release", "publish-approval-separation"], ["publish-approval-separation-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_separation_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-record-validator"], ["release", "publish-approval-record-validator"], ["publish-approval-record-validator"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_record_validator(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-dry-run-v2"], ["release", "publish-approval-dry-run-v2"], ["release", "publish-approval-preview"], ["publish-approval-dry-run-v2"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_dry_run_v2(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-storage-quarantine"], ["release", "approval-storage-quarantine"], ["approval-storage-quarantine"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_storage_quarantine(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-api-preview"], ["release", "publish-approval-api-preview"], ["publish-approval-api-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_api_preview(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-approval-workflow-preview"], ["release", "dashboard-approval-workflow-preview"], ["dashboard-approval-workflow-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dashboard_approval_workflow_preview(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-confirmation-policy"], ["release", "approval-confirmation-policy"], ["approval-confirmation-policy"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_confirmation_policy(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-record-fixture-drill"], ["release", "approval-record-fixture-drill"], ["approval-record-fixture-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_record_fixture_drill(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-audit-trail"], ["release", "approval-audit-trail"], ["approval-audit-trail"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_audit_trail(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v37-approval-records-gate"], ["release", "pre-v37-approval-records-gate"], ["pre-v37-approval-records-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v37_approval_records_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))


    if parts in (["self-maintenance", "publish-approval-write-preflight"], ["release", "publish-approval-write-preflight"], ["publish-approval-write-preflight"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_write_preflight(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-write-schema-lock"], ["release", "publish-approval-write-schema-lock"], ["publish-approval-write-schema-lock"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_write_schema_lock(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-confirmation-validator"], ["release", "publish-approval-confirmation-validator"], ["publish-approval-confirmation-validator"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_confirmation_validator(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), confirmation=query.get("confirmation", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "post-only-approval-write-route-design"], ["release", "post-only-approval-write-route-design"], ["post-only-approval-write-route-design"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_post_only_approval_write_route_design(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-write-dashboard-preview"], ["release", "approval-write-dashboard-preview"], ["approval-write-dashboard-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_write_dashboard_preview(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), confirmation=query.get("confirmation", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-write-rollback-safety-audit"], ["release", "approval-write-rollback-safety-audit"], ["approval-write-rollback-safety-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_write_rollback_safety_audit(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-write-fixture-drill"], ["release", "approval-write-fixture-drill"], ["approval-write-fixture-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_write_fixture_drill(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v38-approval-write-gate"], ["release", "pre-v38-approval-write-gate"], ["pre-v38-approval-write-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v38_approval_write_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "controlled-publish-approval-write-system"], ["release", "controlled-publish-approval-write"], ["release", "controlled-publish-approval-write-system"], ["controlled-publish-approval-write-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_controlled_publish_approval_write_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-record-reader"], ["release", "publish-approval-records"], ["release", "publish-approval-record-reader"], ["publish-approval-record-reader"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_record_reader(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-artifact-revalidation"], ["release", "approval-artifact-revalidation"], ["approval-artifact-revalidation"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_artifact_revalidation(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-record-conflict-detector"], ["release", "approval-record-conflicts"], ["release", "approval-record-conflict-detector"], ["approval-record-conflict-detector"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_record_conflict_detector(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-status-viewer"], ["release", "approval-status-viewer"], ["approval-status-viewer"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_status_viewer(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-revocation-policy"], ["release", "approval-revocation-policy"], ["approval-revocation-policy"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_revocation_policy(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-revocation-dry-run"], ["release", "approval-revocation-dry-run"], ["approval-revocation-dry-run"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_revocation_dry_run(project_id=project_id, approval_record_id=query.get("approval_record_id", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-lifecycle-audit"], ["release", "approval-lifecycle-audit"], ["approval-lifecycle-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_lifecycle_audit(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-lifecycle-fixture-drill"], ["release", "approval-lifecycle-fixture-drill"], ["approval-lifecycle-fixture-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_lifecycle_fixture_drill(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v39-approval-lifecycle-gate"], ["release", "pre-v39-approval-lifecycle-gate"], ["pre-v39-approval-lifecycle-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v39_approval_lifecycle_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "publish-approval-lifecycle-system"], ["release", "publish-approval-lifecycle"], ["release", "publish-approval-lifecycle-system"], ["publish-approval-lifecycle-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_publish_approval_lifecycle_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-revocation-record-schema"], ["release", "approval-revocation-record-schema"], ["approval-revocation-record-schema"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_revocation_record_schema(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-revocation-confirmation-validator"], ["release", "approval-revocation-confirmation-validator"], ["approval-revocation-confirmation-validator"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_revocation_confirmation_validator(project_id=project_id, approval_record_id=query.get("approval_record_id", [None])[0], confirmation=query.get("confirmation", [""])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-revocation-write-preflight"], ["release", "approval-revocation-write-preflight"], ["approval-revocation-write-preflight"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_revocation_write_preflight(project_id=project_id, approval_record_id=query.get("approval_record_id", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "revocation-storage-quarantine"], ["release", "revocation-storage-quarantine"], ["revocation-storage-quarantine"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_revocation_storage_quarantine(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "post-only-revocation-route-design"], ["release", "post-only-revocation-route-design"], ["post-only-revocation-route-design"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_post_only_revocation_route_design(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-revocation-preview"], ["release", "dashboard-revocation-preview"], ["dashboard-revocation-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dashboard_revocation_preview(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-revocation-fixture-drill"], ["release", "approval-revocation-fixture-drill"], ["approval-revocation-fixture-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_revocation_fixture_drill(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v40-revocation-gate"], ["release", "pre-v40-revocation-gate"], ["pre-v40-revocation-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v40_revocation_gate(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "controlled-publish-approval-revocation-system"], ["release", "controlled-publish-approval-revocation"], ["release", "controlled-publish-approval-revocation-system"], ["controlled-publish-approval-revocation-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_controlled_publish_approval_revocation_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "controlled-publish-approval-system"], ["release", "controlled-publish-approval"], ["release", "controlled-publish-approval-system"], ["controlled-publish-approval-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_controlled_publish_approval_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=_query_release_zip_path(query), **_query_signature_options(query), save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "autonomy-capability-inventory"], ["release", "autonomy-capability-inventory"], ["autonomy-capability-inventory"]):
        report = build_autonomy_capability_inventory(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-task-proposal-schema"], ["release", "autonomous-task-proposal-schema"], ["autonomous-task-proposal-schema"]):
        report = build_autonomous_task_proposal_schema(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-dry-run-plan"], ["release", "autonomous-dry-run-plan"], ["autonomous-dry-run-plan"]):
        report = build_autonomous_dry_run_plan(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomy-action-policy-engine"], ["release", "autonomy-action-policy-engine"], ["autonomy-action-policy-engine"]):
        report = build_autonomy_action_policy_engine(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-patch-sandbox"], ["release", "autonomous-patch-sandbox"], ["autonomous-patch-sandbox"]):
        report = build_autonomous_patch_sandbox(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-patch-risk-classifier"], ["release", "autonomous-patch-risk-classifier"], ["autonomous-patch-risk-classifier"]):
        report = build_autonomous_patch_risk_classifier(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-test-selection"], ["release", "autonomous-test-selection"], ["autonomous-test-selection"]):
        report = build_autonomous_test_selection(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomy-human-checkpoint"], ["release", "autonomy-human-checkpoint"], ["autonomy-human-checkpoint"]):
        report = build_autonomy_human_checkpoint(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "pre-v41-autonomy-readiness-gate"], ["release", "pre-v41-autonomy-readiness-gate"], ["pre-v41-autonomy-readiness-gate"]):
        report = build_pre_v41_autonomy_readiness_gate(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomy-readiness-boundary-system"], ["release", "autonomy-readiness-boundary-system"], ["autonomy-readiness-boundary-system"], ["autonomy", "boundary"]):
        report = build_autonomy_readiness_boundary_system(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "patch-proposal-schema"], ["release", "patch-proposal-schema"], ["autonomy", "patch-proposal-schema"], ["patch-proposal-schema"]):
        report = build_patch_proposal_schema(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-change-target-selector"], ["release", "autonomous-change-target-selector"], ["autonomy", "change-target-selector"], ["autonomous-change-target-selector"]):
        report = build_autonomous_change_target_selector(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "generate-sandbox-patch"], ["release", "generate-sandbox-patch"], ["autonomy", "generate-sandbox-patch"], ["generate-sandbox-patch"]):
        report = build_generate_sandbox_patch(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "sandbox-patch-diff"], ["release", "sandbox-patch-diff"], ["autonomy", "sandbox-patch-diff"], ["sandbox-patch-diff"]):
        report = build_sandbox_patch_diff(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "sandbox-patch-validation"], ["release", "sandbox-patch-validation"], ["autonomy", "sandbox-patch-validation"], ["sandbox-patch-validation"]):
        report = build_sandbox_patch_validation(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "sandbox-patch-test-run"], ["release", "sandbox-patch-test-run"], ["autonomy", "sandbox-patch-test-run"], ["sandbox-patch-test-run"]):
        report = build_sandbox_patch_test_run(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "patch-review-checkpoint"], ["release", "patch-review-checkpoint"], ["autonomy", "patch-review-checkpoint"], ["patch-review-checkpoint"]):
        report = build_patch_review_checkpoint(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-apply-dry-run"], ["release", "source-apply-dry-run"], ["autonomy", "source-apply-dry-run"], ["source-apply-dry-run"]):
        report = build_source_apply_dry_run(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "pre-v42-autonomous-patch-gate"], ["release", "pre-v42-autonomous-patch-gate"], ["autonomy", "pre-v42-autonomous-patch-gate"], ["pre-v42-autonomous-patch-gate"]):
        report = build_pre_v42_autonomous_patch_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "autonomous-patch-proposal-system"], ["release", "autonomous-patch-proposal-system"], ["autonomy", "patch-proposal-system"], ["autonomous-patch-proposal-system"]):
        report = build_autonomous_patch_proposal_system(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "source-apply-eligibility"], ["release", "source-apply-eligibility"], ["autonomy", "source-apply-eligibility"], ["source-apply-eligibility"]):
        report = build_source_apply_eligibility(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-apply-confirmation-policy"], ["release", "source-apply-confirmation-policy"], ["autonomy", "source-apply-confirmation-policy"], ["source-apply-confirmation-policy"]):
        report = build_source_apply_confirmation_policy(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, confirmation=query.get("confirmation", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-apply-dry-run-v2"], ["release", "source-apply-dry-run-v2"], ["autonomy", "source-apply-dry-run-v2"], ["source-apply-dry-run-v2"]):
        report = build_source_apply_dry_run_v2(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-apply-backup-quarantine"], ["release", "source-apply-backup-quarantine"], ["autonomy", "source-apply-backup-quarantine"], ["source-apply-backup-quarantine"]):
        report = build_source_apply_backup_quarantine(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "post-source-apply-verification"], ["release", "post-source-apply-verification"], ["autonomy", "post-source-apply-verification"], ["post-source-apply-verification"]):
        report = build_post_source_apply_verification(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-apply-rollback-preview"], ["release", "source-apply-rollback-preview"], ["autonomy", "source-apply-rollback-preview"], ["source-apply-rollback-preview"]):
        report = build_source_apply_rollback_preview(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-apply-fixture-drill"], ["release", "source-apply-fixture-drill"], ["autonomy", "source-apply-fixture-drill"], ["source-apply-fixture-drill"]):
        report = build_source_apply_fixture_drill(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "pre-v43-source-apply-gate"], ["release", "pre-v43-source-apply-gate"], ["autonomy", "pre-v43-source-apply-gate"], ["pre-v43-source-apply-gate"]):
        report = build_pre_v43_source_apply_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "controlled-source-apply-system"], ["release", "controlled-source-apply-system"], ["autonomy", "controlled-source-apply-system"], ["controlled-source-apply-system"]):
        report = build_controlled_source_apply_system(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "source-apply-record-reader"], ["release", "source-apply-record-reader"], ["autonomy", "source-apply-record-reader"], ["source-apply-record-reader"]):
        report = build_source_apply_record_reader(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-rollback-eligibility"], ["release", "source-rollback-eligibility"], ["autonomy", "source-rollback-eligibility"], ["source-rollback-eligibility"]):
        report = build_source_rollback_eligibility(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-rollback-confirmation-policy"], ["release", "source-rollback-confirmation-policy"], ["autonomy", "source-rollback-confirmation-policy"], ["source-rollback-confirmation-policy"]):
        report = build_source_rollback_confirmation_policy(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, confirmation=query.get("confirmation", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-rollback-dry-run-v2"], ["release", "source-rollback-dry-run-v2"], ["autonomy", "source-rollback-dry-run-v2"], ["source-rollback-dry-run-v2"]):
        report = build_source_rollback_dry_run_v2(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "post-source-rollback-verification"], ["release", "post-source-rollback-verification"], ["autonomy", "post-source-rollback-verification"], ["post-source-rollback-verification"]):
        report = build_post_source_rollback_verification(project_id=query.get("project", ["eidolon"])[0], proposal_id=query.get("proposal_id", [""])[0] or None, goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-rollback-audit-trail"], ["release", "source-rollback-audit-trail"], ["autonomy", "source-rollback-audit-trail"], ["source-rollback-audit-trail"]):
        report = build_source_rollback_audit_trail(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "source-rollback-fixture-drill"], ["release", "source-rollback-fixture-drill"], ["autonomy", "source-rollback-fixture-drill"], ["source-rollback-fixture-drill"]):
        report = build_source_rollback_fixture_drill(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "pre-v44-source-rollback-gate"], ["release", "pre-v44-source-rollback-gate"], ["autonomy", "pre-v44-source-rollback-gate"], ["pre-v44-source-rollback-gate"]):
        report = build_pre_v44_source_rollback_gate(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))
    if parts in (["self-maintenance", "controlled-source-rollback-system"], ["release", "controlled-source-rollback-system"], ["autonomy", "controlled-source-rollback-system"], ["controlled-source-rollback-system"]):
        report = build_controlled_source_rollback_system(project_id=query.get("project", ["eidolon"])[0], goal=query.get("goal", [""])[0] or None, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts[0] == "diagnostics":
        reports = list_diagnostic_reports()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(reports[: max(1, min(limit, 100))])
        report_id = "latest" if parts[1] == "latest" else parts[1]
        report = reports[0] if report_id == "latest" and reports else load_diagnostic_report(report_id)
        if not report:
            raise ApiError(404, f"Diagnostic report not found: {report_id}")
        return 200, _ok(report)

    if parts[0] == "watch":
        reports = list_watch_reports()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(reports[: max(1, min(limit, 100))])
        report_id = "latest" if parts[1] == "latest" else parts[1]
        report = reports[0] if report_id == "latest" and reports else load_watch_report(report_id)
        if not report:
            raise ApiError(404, f"Watch report not found: {report_id}")
        return 200, _ok(report)

    if parts == ["tasks", "review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_task_review(project_id=project_id))

    if parts == ["stable-loops", "confidence", "preview"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_bounded_stable_loop_confidence(project_id=project_id))

    if parts == ["stable-loops", "confidence"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_stable_loop_confidence(project_id=project_id))

    if parts[0] == "session-plans":
        plans = list_session_plans()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(plans[: max(1, min(limit, 100))])
        plan_id = "latest" if parts[1] == "latest" else parts[1]
        plan = plans[0] if plan_id == "latest" and plans else load_session_plan(plan_id)
        if not plan:
            raise ApiError(404, f"Session plan not found: {plan_id}")
        return 200, _ok(plan)

    if parts[0] == "maintenance":
        scans = list_maintenance_scans()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(scans[: max(1, min(limit, 100))])
        scan_id = "latest" if parts[1] == "latest" else parts[1]
        scan = scans[0] if scan_id == "latest" and scans else load_maintenance_scan(scan_id)
        if not scan:
            raise ApiError(404, f"Maintenance scan not found: {scan_id}")
        return 200, _ok(scan)

    if parts[0] == "dev-loops":
        loops = list_dev_loops()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(loops[: max(1, min(limit, 100))])
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        loop = loops[0] if loop_id == "latest" and loops else get_dev_loop(loop_id)
        if not loop:
            raise ApiError(404, f"Dev loop not found: {loop_id}")
        return 200, _ok(loop)

    if parts[0] == "setup":
        reports = list_setup_reports()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(reports[: max(1, min(limit, 100))])
        report_id = "latest" if parts[1] == "latest" else parts[1]
        report = reports[0] if report_id == "latest" and reports else load_setup_report(report_id)
        if not report:
            raise ApiError(404, f"Setup report not found: {report_id}")
        return 200, _ok(report)

    if parts[0] == "onboarding":
        runs = list_onboarding_runs()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(runs[: max(1, min(limit, 100))])
        run_id = "latest" if parts[1] == "latest" else parts[1]
        run = runs[0] if run_id == "latest" and runs else load_onboarding_run(run_id)
        if not run:
            raise ApiError(404, f"Onboarding run not found: {run_id}")
        return 200, _ok(run)

    if parts == ["desktop", "attention"]:
        return 200, _ok(build_desktop_attention_payload())

    if parts == ["attention-center"]:
        return 200, _ok(build_attention_center())

    if parts[0] == "notifications":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            severity = query.get("severity", [""])[0]
            include_dismissed = _query_bool(query, "include_dismissed", True)
            return 200, _ok(list_notifications(status=status, severity=severity, include_dismissed=include_dismissed))
        note = load_notification(parts[1])
        if not note:
            raise ApiError(404, f"Notification not found: {parts[1]}")
        return 200, _ok(note)

    if parts[0] == "approvals":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_approvals(status=status, include_closed=include_closed))
        approval = get_approval(parts[1])
        if not approval:
            raise ApiError(404, f"Approval not found: {parts[1]}")
        return 200, _ok(approval)

    if parts[0] == "chat-actions":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_chat_actions(status=status, include_closed=include_closed))
        action = load_chat_action(parts[1])
        if not action:
            raise ApiError(404, f"Chat action not found: {parts[1]}")
        return 200, _ok(action)

    if parts[0] == "stable-loops":
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            review_filter = query.get("review", query.get("status", ["all"]))[0]
            decision_filter = query.get("decision", query.get("final_decision", [""]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            if decision_filter:
                include_live = not _query_bool(query, "exclude_live", False)
                return 200, _ok(list_stable_loop_decision_rows(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live, limit=limit))
            return 200, _ok(list_stable_loop_reviews(review_filter=review_filter, include_archived=include_archived, limit=limit))
        if len(parts) == 2 and parts[1] == "preflight":
            project_id = query.get("project", ["eidolon"])[0]
            max_steps = int(query.get("max_steps", query.get("steps", ["1"]))[0] or 1)
            return 200, _ok(build_stable_loop_preflight(project_id=project_id, max_steps=max_steps))
        if len(parts) == 2 and parts[1] == "guardrails":
            project_id = query.get("project", ["eidolon"])[0]
            include_archived = _query_bool(query, "include_archived", False)
            bypass = _query_bool(query, "bypass", False)
            return 200, _ok(stable_loop_guardrail_summary(project_id=project_id, bypass=bypass, include_archived=include_archived))
        if len(parts) == 2 and parts[1] == "reviews":
            review_filter = query.get("review", query.get("status", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(stable_loop_review_summary(review_filter=review_filter, include_archived=include_archived))
        if len(parts) == 2 and parts[1] == "history":
            limit = int(query.get("limit", ["50"])[0] or 50)
            review_filter = query.get("review", query.get("status", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(list_stable_loop_reviews(review_filter=review_filter, include_archived=include_archived, limit=limit))
        if len(parts) == 2 and parts[1] == "decisions":
            decision_filter = query.get("decision", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            include_live = not _query_bool(query, "exclude_live", False)
            return 200, _ok(stable_loop_decision_summary(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live))
        if len(parts) == 3 and parts[1] == "decisions" and parts[2] == "report":
            decision_filter = query.get("decision", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            include_live = not _query_bool(query, "exclude_live", False)
            limit = int(query.get("limit", ["50"])[0] or 50)
            report = stable_loop_decision_summary(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live)
            report["rows"] = list_stable_loop_decision_rows(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live, limit=limit)
            return 200, _ok(report)
        if len(parts) == 2 and parts[1] == "followups":
            decision_filter = query.get("decision", query.get("filter", ["action_required"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            include_live = not _query_bool(query, "exclude_live", False)
            return 200, _ok(stable_loop_followup_summary(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live))
        if len(parts) == 3 and parts[1] == "followups" and parts[2] == "completion":
            completion_filter = query.get("completion", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(stable_loop_followup_completion_summary(completion_filter=completion_filter, include_archived=include_archived))
        if len(parts) == 4 and parts[1] == "followups" and parts[2] == "completion" and parts[3] == "report":
            completion_filter = query.get("completion", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            limit = int(query.get("limit", ["50"])[0] or 50)
            report = stable_loop_followup_completion_summary(completion_filter=completion_filter, include_archived=include_archived)
            report["rows"] = list_stable_loop_followup_completion_rows(completion_filter=completion_filter, include_archived=include_archived, limit=limit)
            return 200, _ok(report)
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        loop = load_stable_loop(loop_id)
        if not loop:
            raise ApiError(404, f"Stable loop not found: {loop_id}")
        if len(parts) == 3 and parts[2] == "review":
            return 200, _ok(loop)
        if len(parts) == 3 and parts[2] == "audit":
            if _query_bool(query, "refresh", False):
                result = refresh_stable_loop_audit(loop_id)
                if not result.ok:
                    raise ApiError(404, result.error, result.to_dict())
                return 200, _ok(result.audit, message=result.message)
            return 200, _ok(loop.get("audit") if isinstance(loop.get("audit"), dict) else build_stable_loop_audit(loop))
        if len(parts) == 3 and parts[2] == "operator-notes":
            result = get_stable_loop_operator_notes(loop_id, ensure=True, save=_query_bool(query, "save", True))
            if not result.ok:
                raise ApiError(404, result.error, result.to_dict())
            return 200, _ok(result.operator_notes, message=result.message)
        if len(parts) == 3 and parts[2] == "followups":
            result = plan_stable_loop_followups(loop_id=loop_id, force=_query_bool(query, "force", False))
            if not result.ok:
                raise ApiError(404, result.error, result.to_dict())
            return 200, _ok(result.to_dict(), message=result.message)
        if len(parts) == 3 and parts[2] == "followup-lifecycle":
            return 200, _ok(stable_loop_followup_lifecycle_summary(loop_id=loop_id, include_closed=True, include_archived=True))
        return 200, _ok(loop)

    if parts[0] == "work-cycles":
        cycles = list_work_cycles()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(cycles[: max(1, min(limit, 100))])
        cycle_id = "latest" if parts[1] == "latest" else parts[1]
        cycle = cycles[0] if cycle_id == "latest" and cycles else load_work_cycle(cycle_id)
        if not cycle:
            raise ApiError(404, f"Work cycle not found: {cycle_id}")
        return 200, _ok(cycle)

    if parts[0] == "work-queue":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            project_id = query.get("project", [""])[0]
            include_done = _query_bool(query, "include_done", False)
            return 200, _ok(list_work_items(status=status or None, project_id=project_id or None, include_done=include_done))
        if len(parts) == 2 and parts[1] == "summary":
            project_id = query.get("project", [""])[0]
            return 200, _ok(summarize_queue(project_id=project_id or None))
        item = find_work_item(parts[1])
        if not item:
            raise ApiError(404, f"Task not found through legacy alias: {parts[1]}")
        return 200, _ok(item)

    if parts[0] == "tasks":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            stage = query.get("stage", [""])[0]
            project_id = query.get("project", [""])[0]
            include_cancelled = _query_bool(query, "include_cancelled", False)
            if stage:
                rows = list_task_lifecycles(project=project_id or "", include_closed=include_cancelled, stage_filter=stage)
                ids = {str(row.get("task_id") or "") for row in rows}
                return 200, _ok([task for task in list_tasks(status=status, project=project_id or "", include_cancelled=include_cancelled) if task.get("id") in ids])
            return 200, _ok(list_tasks(status=status, project=project_id or "", include_cancelled=include_cancelled))
        if len(parts) == 2 and parts[1] == "summary":
            project_id = query.get("project", [""])[0]
            return 200, _ok(summarize_queue(project_id=project_id or None))
        if len(parts) == 2 and parts[1] == "lifecycle":
            project_id = query.get("project", [""])[0]
            stage = query.get("stage", [""])[0]
            return 200, _ok(task_lifecycle_summary(project=project_id or "", stage_filter=stage))
        if len(parts) == 2 and parts[1] == "stable-loop-followups":
            decision_filter = query.get("decision", query.get("filter", ["all"]))[0]
            include_closed = _query_bool(query, "include_closed", True)
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(stable_loop_followup_lifecycle_summary(decision_filter=decision_filter, include_closed=include_closed, include_archived=include_archived))
        if len(parts) == 2 and parts[1] == "recovery":
            project_id = query.get("project", [""])[0]
            include_nonrecoverable = _query_bool(query, "include_nonrecoverable", False)
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(list_task_recoveries(project=project_id or "", include_nonrecoverable=include_nonrecoverable, limit=limit))
        if len(parts) == 3 and parts[1] == "recovery" and parts[2] == "summary":
            project_id = query.get("project", [""])[0]
            return 200, _ok(task_recovery_summary(project=project_id or ""))
        if len(parts) == 3 and parts[2] == "approvals":
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_task_approvals(parts[1], include_closed=include_closed))
        if len(parts) == 3 and parts[2] == "lifecycle":
            task = get_task(parts[1])
            if not task:
                raise ApiError(404, f"Task not found: {parts[1]}")
            return 200, _ok(derive_task_lifecycle(task))
        if len(parts) == 3 and parts[2] == "stable-loop-followup":
            row = stable_loop_followup_task_row(parts[1])
            if not row.get("ok"):
                raise ApiError(404, str(row.get("message") or "Task not found."), row)
            return 200, _ok(row)
        if len(parts) == 3 and parts[2] == "recovery":
            recovery = build_task_recovery(parts[1])
            if not recovery.get("ok"):
                raise ApiError(404, str(recovery.get("message") or "Task not found."), recovery)
            return 200, _ok(recovery)
        task = get_task(parts[1])
        if not task:
            raise ApiError(404, f"Task not found: {parts[1]}")
        return 200, _ok(task)

    if parts[0] == "goals":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            include_cancelled = _query_bool(query, "include_cancelled", False)
            return 200, _ok(list_goals(status=status, include_cancelled=include_cancelled))
        goal = get_goal(parts[1])
        if not goal:
            raise ApiError(404, f"Goal not found: {parts[1]}")
        return 200, _ok(goal)

    if parts[0] == "patches":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            patches = list_patch_proposals()
            if status:
                patches = [patch for patch in patches if patch.get("status") == status]
            return 200, _ok(patches)
        patch = load_patch_proposal(parts[1])
        if not patch:
            raise ApiError(404, f"Patch proposal not found: {parts[1]}")
        return 200, _ok(patch)

    if parts[0] == "dashboard-chat":
        session_id = str(query.get("session_id", [""])[0] or "").strip()
        turns = list_dashboard_chat_turns(session_id)
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(turns[: max(1, min(limit, 100))])
        turn_id = "latest" if parts[1] == "latest" else parts[1]
        turn = turns[0] if turn_id == "latest" and turns else load_dashboard_chat_turn(turn_id)
        if not turn:
            raise ApiError(404, f"Dashboard chat turn not found: {turn_id}")
        return 200, _ok(turn)

    raise ApiError(404, f"Unknown API endpoint: /api/{'/'.join(parts)}")


def handle_api_post(path: str, body: dict[str, Any] | None = None, query: dict[str, list[str]] | None = None) -> tuple[int, dict[str, Any]]:
    body = body or {}
    query = query or {}
    parts = _path_parts(path)

    if parts == ["training-evidence", "settings"]:
        from model_training.training_policy import SETTING_KEYS, update_training_evidence_capture_policy
        patch = {str(key): value for key, value in body.items() if str(key) in SETTING_KEYS}
        try:
            policy = update_training_evidence_capture_policy(patch)
        except (TypeError, ValueError) as error:
            raise ApiError(400, "Training capture settings are invalid.", {"failure_class": type(error).__name__}) from error
        return 200, _ok(
            {"status": "training_capture_settings_updated", "policy": policy.public_record()},
            message="Training evidence capture settings updated.",
        )

    if parts == ["cognition", "control"]:
        from endogenous_cognitive_cycle import EndogenousCognitiveCycle
        try:
            payload = EndogenousCognitiveCycle().set_control(
                str(body.get("event_id") or ""),
                action=str(body.get("action") or ""),
                cadence_seconds=body.get("cadence_seconds"),
                max_cycles_per_hour=body.get("max_cycles_per_hour"),
                max_cycles_per_day=body.get("max_cycles_per_day"),
                max_reflection_steps_per_cycle=body.get("max_reflection_steps_per_cycle"),
                minimum_salience=body.get("minimum_salience"),
                communication_salience=body.get("communication_salience"),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        if str(body.get("action") or "") in {"sleep", "wake"}:
            from cognitive_continuity import CognitiveContinuityStore
            continuity_store = CognitiveContinuityStore()
            if str(body.get("action") or "") == "sleep":
                payload["continuity"] = continuity_store.sleep_and_consolidate(str(body.get("event_id") or "") + ":continuity")
            else:
                payload["continuity"] = continuity_store.wake(str(body.get("event_id") or "") + ":continuity")
        return 200, _ok(payload)

    if parts == ["cognition", "continuity", "advance"]:
        from cognitive_continuity import CognitiveContinuityStore
        try:
            payload = CognitiveContinuityStore().advance_time(str(body.get("event_id") or ""), now_epoch=body.get("now_epoch"))
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiries", "create"]:
        from self_directed_inquiry import InquiryWorkspace
        try:
            payload = InquiryWorkspace().create_inquiry(
                str(body.get("event_id") or ""),
                motivation_id=str(body.get("motivation_id") or ""),
                question=str(body.get("question") or ""),
                uncertainty=body.get("uncertainty", 0.5),
                sources_sought=body.get("sources_sought") if isinstance(body.get("sources_sought"), list) else (),
                stop_conditions=body.get("stop_conditions") if isinstance(body.get("stop_conditions"), list) else (),
                project_id=str(body.get("project_id") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiries", "progress"]:
        from self_directed_inquiry import InquiryWorkspace
        try:
            payload = InquiryWorkspace().add_progress(
                str(body.get("event_id") or ""),
                inquiry_id=str(body.get("inquiry_id") or ""),
                conclusion=str(body.get("conclusion") or ""),
                supporting_refs=body.get("supporting_refs") if isinstance(body.get("supporting_refs"), list) else (),
                uncertainty_after=body.get("uncertainty_after"),
                next_question=str(body.get("next_question") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiries", "status"]:
        from self_directed_inquiry import InquiryWorkspace
        try:
            payload = InquiryWorkspace().set_status(
                str(body.get("event_id") or ""),
                inquiry_id=str(body.get("inquiry_id") or ""),
                status=str(body.get("status") or ""),
                reason_code=str(body.get("reason_code") or "operator_update"),
                correction_ref=str(body.get("correction_ref") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiry-residual-lineage", "create"]:
        from inquiry_residual_lineage import InquiryResidualLineage
        try:
            payload = InquiryResidualLineage().create_child(str(body.get("event_id") or ""), parent_inquiry_id=str(body.get("parent_inquiry_id") or ""), residual_question=str(body.get("residual_question") or ""), uncertainty=body.get("uncertainty", 0.7))
        except ValueError as error: raise ApiError(400, str(error)) from error
        except KeyError as error: raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "cross-inquiry-evidence-lineage", "link"]:
        from cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage
        try:
            payload = CrossInquiryEvidenceLineage().link(str(body.get("event_id") or ""), evidence_id=str(body.get("evidence_id") or ""), target_inquiry_id=str(body.get("target_inquiry_id") or ""), stance=str(body.get("stance") or "supports"), relevance=body.get("relevance", 0.5))
        except ValueError as error: raise ApiError(400, str(error)) from error
        except KeyError as error: raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "knowledge-reconsideration", "schedule"]:
        from knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
        try: payload = KnowledgeReconsiderationScheduler().schedule_from_checkpoint(str(body.get("event_id") or ""), max_items=int(body.get("max_items") or 8))
        except ValueError as error: raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "evidence-change-propagation", "propagate"]:
        from evidence_change_propagation import EvidenceChangePropagation
        try: payload = EvidenceChangePropagation().propagate(str(body.get("event_id") or ""), evidence_id=str(body.get("evidence_id") or ""), change_type=str(body.get("change_type") or "updated"))
        except ValueError as error: raise ApiError(400, str(error)) from error
        except KeyError as error: raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "reconsideration-conversation", "consider"]:
        from reconsideration_conversation_continuity import ReconsiderationConversationBridge
        try: payload = ReconsiderationConversationBridge().consider(str(body.get("event_id") or ""), schedule_id=str(body.get("schedule_id") or ""), conclusion=str(body.get("conclusion") or ""), changed_belief=bool(body.get("changed_belief")), tone=str(body.get("tone") or "thoughtful"), continuation_of=str(body.get("continuation_of") or ""))
        except ValueError as error: raise ApiError(400, str(error)) from error
        except KeyError as error: raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "reconsideration-reflections", "reflect"]:
        from bounded_reconsideration_reflection import BoundedReconsiderationReflection
        try: payload = BoundedReconsiderationReflection().reflect(str(body.get("event_id") or ""), schedule_id=str(body.get("schedule_id") or ""), conclusion=str(body.get("conclusion") or ""), select_silence=bool(body.get("select_silence")))
        except ValueError as error: raise ApiError(400, str(error)) from error
        except KeyError as error: raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "belief-maintenance-outcomes", "apply"]:
        from belief_maintenance_outcomes import BeliefMaintenanceOutcomes
        try: payload = BeliefMaintenanceOutcomes().apply(str(body.get("event_id") or ""), schedule_id=str(body.get("schedule_id") or ""), outcome=str(body.get("outcome") or "retain"), conclusion=str(body.get("conclusion") or ""), new_confidence=body.get("new_confidence"))
        except ValueError as error: raise ApiError(400, str(error)) from error
        except KeyError as error: raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiry-attention", "activate"]:
        from inquiry_attention_routing import InquiryAttentionRouter
        try:
            payload = InquiryAttentionRouter().activate(str(body.get("event_id") or ""), trigger_type=str(body.get("trigger_type") or "event"))
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiry-evidence", "assimilate"]:
        from inquiry_evidence_assimilation import InquiryEvidenceLedger
        try:
            payload = InquiryEvidenceLedger().assimilate(str(body.get("event_id") or ""), inquiry_id=str(body.get("inquiry_id") or ""), summary=str(body.get("summary") or ""), source_label=str(body.get("source_label") or ""), evidence_kind=str(body.get("evidence_kind") or "operator_note"), reliability=body.get("reliability", 0.5), supports=str(body.get("supports") or ""))
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiry-evidence", "research-proposal"]:
        from inquiry_evidence_assimilation import InquiryEvidenceLedger
        try:
            payload = InquiryEvidenceLedger().propose_research(str(body.get("event_id") or ""), inquiry_id=str(body.get("inquiry_id") or ""), question=str(body.get("question") or ""), justification=str(body.get("justification") or ""), requested_sources=body.get("requested_sources") if isinstance(body.get("requested_sources"), list) else ())
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "inquiry-conversation", "consider"]:
        from inquiry_conversation_continuity import InquiryConversationBridge
        try:
            payload = InquiryConversationBridge().consider(str(body.get("event_id") or ""), inquiry_id=str(body.get("inquiry_id") or ""), tone=str(body.get("tone") or "thoughtful"), continuation_of=str(body.get("continuation_of") or ""))
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "prospective-planning", "create"]:
        from prospective_planning import ProspectivePlanningStore
        try:
            payload = ProspectivePlanningStore().create_plan(
                str(body.get("event_id") or ""),
                subject=str(body.get("subject") or ""),
                alternatives=body.get("alternatives") if isinstance(body.get("alternatives"), list) else (),
                motivation_ids=body.get("motivation_ids") if isinstance(body.get("motivation_ids"), list) else (),
                inquiry_ids=body.get("inquiry_ids") if isinstance(body.get("inquiry_ids"), list) else (),
                constraints=body.get("constraints") if isinstance(body.get("constraints"), list) else (),
                project_id=str(body.get("project_id") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "prospective-planning", "compare"]:
        from prospective_planning import ProspectivePlanningStore
        try:
            payload = ProspectivePlanningStore().compare_plan(str(body.get("event_id") or ""), plan_id=str(body.get("plan_id") or ""))
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "prospective-planning", "counterfactual"]:
        from prospective_planning import ProspectivePlanningStore
        try:
            payload = ProspectivePlanningStore().record_counterfactual(
                str(body.get("event_id") or ""), plan_id=str(body.get("plan_id") or ""),
                alternative_id=str(body.get("alternative_id") or ""), premise=str(body.get("premise") or ""),
                expected_outcome=str(body.get("expected_outcome") or ""), probability=body.get("probability", 0.5),
                downside=body.get("downside", 0.5), reversibility=body.get("reversibility", 0.5),
                supporting_refs=body.get("supporting_refs") if isinstance(body.get("supporting_refs"), list) else (),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "prospective-planning", "proposal"]:
        from prospective_planning import ProspectivePlanningStore
        try:
            payload = ProspectivePlanningStore().propose_intention(
                str(body.get("event_id") or ""), plan_id=str(body.get("plan_id") or ""),
                alternative_id=str(body.get("alternative_id") or ""), rationale=str(body.get("rationale") or ""),
                supporting_refs=body.get("supporting_refs") if isinstance(body.get("supporting_refs"), list) else (),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "prospective-planning", "status"]:
        from prospective_planning import ProspectivePlanningStore
        try:
            payload = ProspectivePlanningStore().set_status(
                str(body.get("event_id") or ""), plan_id=str(body.get("plan_id") or ""),
                status=str(body.get("status") or ""), reason_code=str(body.get("reason_code") or "operator_update"),
                correction_ref=str(body.get("correction_ref") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "beliefs", "record"]:
        from belief_revision import BeliefRevisionStore
        try:
            payload = BeliefRevisionStore().record_belief(
                str(body.get("event_id") or ""),
                proposition=str(body.get("proposition") or ""),
                confidence=body.get("confidence", 0.5),
                origin_type=str(body.get("origin_type") or "operator_observation"),
                origin_ref=str(body.get("origin_ref") or body.get("event_id") or ""),
                scope_project_id=str(body.get("scope_project_id") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "beliefs", "evidence"]:
        from belief_revision import BeliefRevisionStore
        try:
            payload = BeliefRevisionStore().add_evidence(
                str(body.get("event_id") or ""), belief_id=str(body.get("belief_id") or ""),
                stance=str(body.get("stance") or ""), weight=body.get("weight", 0.5), reliability=body.get("reliability", 0.5),
                evidence_ref=str(body.get("evidence_ref") or ""), source_type=str(body.get("source_type") or "observation"),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "beliefs", "conflict"]:
        from belief_revision import BeliefRevisionStore
        try:
            payload = BeliefRevisionStore().create_conflict_set(
                str(body.get("event_id") or ""), belief_ids=body.get("belief_ids") if isinstance(body.get("belief_ids"), list) else (),
                reason_code=str(body.get("reason_code") or "explicit_contradiction"),
                motivation_ids=body.get("motivation_ids") if isinstance(body.get("motivation_ids"), list) else (),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "native-reflection-evaluation", "run"]:
        from native_reflection_evaluation import NativeReflectionEvaluator
        try:
            payload = NativeReflectionEvaluator().evaluate(
                str(body.get("event_id") or ""),
                operator_confirmed=bool(body.get("confirm_native", False)),
                provider_id=str(body.get("provider_id") or "configured"),
                max_cases=body.get("max_cases", 3),
                max_total_ms=body.get("max_total_ms", 30000),
                max_output_chars=body.get("max_output_chars", 700),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["cognition", "communication", "preferences"]:
        from proactive_communication import ProactiveCommunicationStore
        try:
            payload = ProactiveCommunicationStore().set_preferences(
                str(body.get("event_id") or ""),
                initiative_enabled=body.get("initiative_enabled"),
                frequency=body.get("frequency"),
                cooldown_seconds=body.get("cooldown_seconds"),
                max_per_day=body.get("max_per_day"),
                quiet_indefinite=body.get("quiet_indefinite"),
                quiet_until_epoch=body.get("quiet_until_epoch"),
                form_of_address=body.get("form_of_address"),
                blocked_topics=body.get("blocked_topics") if isinstance(body.get("blocked_topics"), list) else None,
                allowed_tones=body.get("allowed_tones") if isinstance(body.get("allowed_tones"), list) else None,
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "communication", "boundary"]:
        from proactive_communication import ProactiveCommunicationStore
        try:
            payload = ProactiveCommunicationStore().apply_user_boundary(
                str(body.get("event_id") or ""),
                quiet=body.get("quiet"),
                quiet_until_epoch=body.get("quiet_until_epoch"),
                form_of_address=body.get("form_of_address"),
                add_blocked_topics=body.get("add_blocked_topics") if isinstance(body.get("add_blocked_topics"), list) else (),
                remove_blocked_topics=body.get("remove_blocked_topics") if isinstance(body.get("remove_blocked_topics"), list) else (),
                relationship_correction=bool(body.get("relationship_correction", False)),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "cycle"]:
        from proactive_communication import CognitiveInitiativeService
        try:
            payload = CognitiveInitiativeService().process_event(
                str(body.get("event_id") or ""),
                trigger_type=str(body.get("trigger_type") or "manual_review"),
                perceived_events=body.get("perceived_events") if isinstance(body.get("perceived_events"), list) else (),
                provider_available=body.get("provider_available"),
                tone=str(body.get("tone") or "thoughtful"),
                relationship_context_refs=body.get("relationship_context_refs") if isinstance(body.get("relationship_context_refs"), list) else (),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["cognition", "proactive", "claim"]:
        from proactive_communication import ProactiveCommunicationStore
        try:
            payload = ProactiveCommunicationStore().claim_delivery(
                str(body.get("event_id") or ""),
                message_id=str(body.get("message_id") or ""),
                delivery_id=str(body.get("delivery_id") or ""),
                tab_id=str(body.get("tab_id") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["cognition", "proactive", "read"]:
        from proactive_communication import ProactiveCommunicationStore
        try:
            payload = ProactiveCommunicationStore().mark_read(
                str(body.get("event_id") or ""),
                message_id=str(body.get("message_id") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        except KeyError as error:
            raise ApiError(404, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["cognition", "proactive", "response"]:
        from proactive_communication import ProactiveCommunicationStore
        try:
            payload = ProactiveCommunicationStore().record_user_response(
                str(body.get("event_id") or ""),
                in_reply_to_message_id=str(body.get("message_id") or ""),
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        return 200, _ok(payload)

    if parts == ["release-certification", "evidence", "select"]:
        from release_certification_evidence import select_certification_evidence
        payload = select_certification_evidence(str(body.get("evidence_path") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "readiness", "create"]:
        from release_certification_evidence import create_certification_readiness_preview
        payload = create_certification_readiness_preview(str(body.get("certification_scope") or "general_release"))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "plan", "create"]:
        from release_certification_plan import create_certification_plan
        payload = create_certification_plan(str(body.get("proposed_decision") or "auto"))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "authorization-preview"]:
        from release_certification_plan import preview_certification_authorization
        payload = preview_certification_authorization()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "decision", "apply"]:
        from release_certification_transaction import apply_authorized_certification
        payload = apply_authorized_certification(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "revocation-preview"]:
        from release_certification_transaction import preview_certification_revocation
        payload = preview_certification_revocation(str(body.get("certification_scope") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "revoke"]:
        from release_certification_transaction import revoke_certification_scope
        payload = revoke_certification_scope(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "recovery", "preview"]:
        from release_certification_recovery import preview_certification_recovery
        payload = preview_certification_recovery()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "recovery", "resume"]:
        from release_certification_recovery import resume_certification_decision
        payload = resume_certification_decision(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "evidence", "replacement-preview"]:
        from release_certification_freshness import preview_evidence_replacement
        payload = preview_evidence_replacement(str(body.get("evidence_path") or ""), str(body.get("scope") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "evidence", "replace"]:
        from release_certification_freshness import replace_certification_evidence
        payload = replace_certification_evidence(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "recertification", "create"]:
        from release_certification_freshness import create_recertification_readiness_preview
        payload = create_recertification_readiness_preview(str(body.get("certification_scope") or "general_release"))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "history", "create"]:
        from release_certification_history import create_certification_history_reconciliation_preview
        payload = create_certification_history_reconciliation_preview(str(body.get("scope") or "all"))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "policy", "select"]:
        from release_certification_policy import select_certification_policy
        policy_path = str(body.get("policy_path") or "").strip()
        payload = select_certification_policy(policy_path or None, built_in_policy_id=str(body.get("built_in_policy_id") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "policy", "migration", "create"]:
        from release_certification_policy import create_policy_migration_preview
        payload = create_policy_migration_preview()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "policy", "migration", "acknowledge"]:
        from release_certification_policy import acknowledge_policy_migration_preview
        payload = acknowledge_policy_migration_preview(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "create"]:
        from release_authority_readiness import create_release_authority_readiness_preview
        payload = create_release_authority_readiness_preview()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "refresh"]:
        from release_authority_readiness_recovery import refresh_release_authority_readiness
        payload = refresh_release_authority_readiness(interrupt_after=str(body.get("interrupt_after") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "recovery-preview"]:
        from release_authority_readiness_recovery import preview_readiness_refresh_recovery
        payload = preview_readiness_refresh_recovery()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "recover"]:
        from release_authority_readiness_recovery import resume_release_authority_readiness_refresh
        payload = resume_release_authority_readiness_refresh(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "replacement-preview"]:
        from release_authority_readiness_recovery import preview_readiness_snapshot_replacement
        payload = preview_readiness_snapshot_replacement(str(body.get("preview_id") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "replace"]:
        from release_authority_readiness_recovery import replace_release_authority_readiness_snapshot
        payload = replace_release_authority_readiness_snapshot(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "cleanup-preview"]:
        from release_authority_readiness_recovery import preview_readiness_cleanup
        payload = preview_readiness_cleanup()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "readiness", "cleanup"]:
        from release_authority_readiness_recovery import cleanup_readiness_artifacts
        payload = cleanup_readiness_artifacts(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "create"]:
        from release_authority_handoff_plan import create_release_authority_handoff_plan
        payload = create_release_authority_handoff_plan(interrupt_after=str(body.get("interrupt_after") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment-preview"]:
        from release_authority_handoff_plan import preview_release_authority_handoff_acknowledgment
        payload = preview_release_authority_handoff_acknowledgment(
            operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"),
            operation_revision=int(body.get("operation_revision") or 1),
            authorization_ttl_seconds=int(body.get("authorization_ttl_seconds") or 900),
            acknowledgment_ttl_seconds=int(body.get("acknowledgment_ttl_seconds") or 86400),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledge"]:
        from release_authority_handoff_plan import acknowledge_release_authority_handoff_plan
        payload = acknowledge_release_authority_handoff_plan(
            str(body.get("authorization_token") or ""),
            confirm=str(body.get("confirm") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"),
            operation_revision=int(body.get("operation_revision") or 1),
            interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "recovery-preview"]:
        from release_authority_handoff_ack_recovery import preview_handoff_acknowledgment_recovery
        payload = preview_handoff_acknowledgment_recovery(
            operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"),
            operation_revision=int(body.get("operation_revision") or 1),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "recover"]:
        from release_authority_handoff_ack_recovery import recover_handoff_acknowledgment
        payload = recover_handoff_acknowledgment(
            str(body.get("authorization_token") or ""),
            confirm=str(body.get("confirm") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"),
            operation_revision=int(body.get("operation_revision") or 1),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "replacement-preview"]:
        from release_authority_handoff_ack_recovery import preview_handoff_acknowledgment_replacement
        payload = preview_handoff_acknowledgment_replacement(
            operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"),
            operation_revision=int(body.get("operation_revision") or 1),
            acknowledgment_ttl_seconds=int(body.get("acknowledgment_ttl_seconds") or 86400),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "replace"]:
        from release_authority_handoff_ack_recovery import replace_handoff_acknowledgment
        payload = replace_handoff_acknowledgment(
            str(body.get("authorization_token") or ""),
            confirm=str(body.get("confirm") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"),
            operation_revision=int(body.get("operation_revision") or 1),
            interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "cleanup-preview"]:
        from release_authority_handoff_ack_recovery import preview_handoff_acknowledgment_cleanup
        payload = preview_handoff_acknowledgment_cleanup()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "handoff-plan", "acknowledgment", "cleanup"]:
        from release_authority_handoff_ack_recovery import cleanup_handoff_acknowledgment_artifacts
        payload = cleanup_handoff_acknowledgment_artifacts(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "validation-preview"]:
        from release_authority_consumer import preview_release_authority_consumer_validation
        payload = preview_release_authority_consumer_validation(
            str(body.get("consumer_id") or ""),
            str(body.get("consumer_schema") or ""),
            str(body.get("consumer_version") or ""),
            str(body.get("expected_use") or ""),
            list(body.get("required_scopes") or []),
            list(body.get("unsupported_scopes") or []),
            scope_sources=dict(body.get("scope_sources") or {}),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "receipt", "create"]:
        from release_authority_consumer import acknowledge_release_authority_consumer_validation
        payload = acknowledge_release_authority_consumer_validation(
            str(body.get("authorization_token") or ""),
            confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""),
            consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""),
            expected_use=str(body.get("expected_use") or ""),
            interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "receipt", "recovery-preview"]:
        from release_authority_consumer_lifecycle import preview_consumer_receipt_recovery
        payload = preview_consumer_receipt_recovery(str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""), str(body.get("expected_use") or ""), operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"), operation_revision=int(body.get("operation_revision") or 1))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "receipt", "recover"]:
        from release_authority_consumer_lifecycle import recover_consumer_receipt
        payload = recover_consumer_receipt(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""), consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""), consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""), operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"), operation_revision=int(body.get("operation_revision") or 1))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "receipt", "retirement-preview"]:
        from release_authority_consumer_lifecycle import preview_consumer_receipt_retirement, create_consumer_receipt_retirement_preview
        token = str(body.get("authorization_token") or "")
        if token:
            payload = create_consumer_receipt_retirement_preview(token, confirm=str(body.get("confirm") or ""), consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""), consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""), operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"), operation_revision=int(body.get("operation_revision") or 1))
        else:
            payload = preview_consumer_receipt_retirement(str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""), str(body.get("expected_use") or ""), operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"), operation_revision=int(body.get("operation_revision") or 1))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "supersession-preview"]:
        from release_authority_consumer_lifecycle import preview_consumer_handoff_supersession
        payload = preview_consumer_handoff_supersession(tuple(body.get("predecessor") or ()), tuple(body.get("successor") or ()), operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"), operation_revision=int(body.get("operation_revision") or 1))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "supersession", "create"]:
        from release_authority_consumer_lifecycle import create_consumer_handoff_supersession
        payload = create_consumer_handoff_supersession(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""), predecessor=tuple(body.get("predecessor") or ()), successor=tuple(body.get("successor") or ()), operator_tab_id=str(body.get("operator_tab_id") or "operator-tab"), operation_revision=int(body.get("operation_revision") or 1))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "selection-preview"]:
        from release_authority_consumer_daily_use import preview_consumer_selection
        payload = preview_consumer_selection(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""),
            str(body.get("consumer_version") or ""), str(body.get("expected_use") or ""),
            str(body.get("selection_purpose") or ""), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0),
            selection_ttl_seconds=int(body.get("selection_ttl_seconds") or 3600),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "selection", "create"]:
        from release_authority_consumer_daily_use import create_consumer_selection
        payload = create_consumer_selection(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            selection_purpose=str(body.get("selection_purpose") or ""), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0), interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "use-preflight", "preview"]:
        from release_authority_consumer_daily_use import preview_consumer_use_preflight
        payload = preview_consumer_use_preflight(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""),
            str(body.get("consumer_version") or ""), str(body.get("expected_use") or ""),
            str(body.get("selection_purpose") or ""), str(body.get("use_id") or ""),
            str(body.get("use_schema") or ""), str(body.get("use_version") or ""), str(body.get("declared_use") or ""),
            list(body.get("required_scopes") or []), list(body.get("unsupported_scopes") or []),
            scope_sources=dict(body.get("scope_sources") or {}), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "use-preflight", "create"]:
        from release_authority_consumer_daily_use import create_consumer_use_preflight_receipt
        payload = create_consumer_use_preflight_receipt(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            selection_purpose=str(body.get("selection_purpose") or ""), use_id=str(body.get("use_id") or ""),
            use_schema=str(body.get("use_schema") or ""), use_version=str(body.get("use_version") or ""),
            declared_use=str(body.get("declared_use") or ""), required_scopes=list(body.get("required_scopes") or []),
            unsupported_scopes=list(body.get("unsupported_scopes") or []), scope_sources=dict(body.get("scope_sources") or {}),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
            interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-recovery", "preview"]:
        from release_authority_consumer_daily_use_recovery import preview_consumer_daily_use_recovery
        payload = preview_consumer_daily_use_recovery(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""),
            str(body.get("expected_use") or ""), str(body.get("selection_purpose") or ""), str(body.get("use_id") or ""),
            str(body.get("use_schema") or ""), str(body.get("use_version") or ""), str(body.get("declared_use") or ""),
            str(body.get("recovery_target") or ""), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-recovery", "recover"]:
        from release_authority_consumer_daily_use_recovery import recover_consumer_daily_use_binding
        payload = recover_consumer_daily_use_binding(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            selection_purpose=str(body.get("selection_purpose") or ""), use_id=str(body.get("use_id") or ""),
            use_schema=str(body.get("use_schema") or ""), use_version=str(body.get("use_version") or ""),
            declared_use=str(body.get("declared_use") or ""), recovery_target=str(body.get("recovery_target") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-replacement", "preview"]:
        from release_authority_consumer_daily_use_recovery import preview_expired_daily_use_replacement
        payload = preview_expired_daily_use_replacement(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""),
            str(body.get("expected_use") or ""), str(body.get("selection_purpose") or ""), str(body.get("use_id") or ""),
            str(body.get("use_schema") or ""), str(body.get("use_version") or ""), str(body.get("declared_use") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
            replacement_ttl_seconds=int(body.get("replacement_ttl_seconds") or 3600),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-replacement", "replace"]:
        from release_authority_consumer_daily_use_recovery import replace_expired_daily_use_binding
        payload = replace_expired_daily_use_binding(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            selection_purpose=str(body.get("selection_purpose") or ""), use_id=str(body.get("use_id") or ""),
            use_schema=str(body.get("use_schema") or ""), use_version=str(body.get("use_version") or ""),
            declared_use=str(body.get("declared_use") or ""), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0), interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-cleanup", "preview"]:
        from release_authority_consumer_daily_use_recovery import preview_consumer_daily_use_cleanup
        payload = preview_consumer_daily_use_cleanup(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""),
            str(body.get("expected_use") or ""), str(body.get("selection_purpose") or ""), str(body.get("use_id") or ""),
            str(body.get("use_schema") or ""), str(body.get("use_version") or ""), str(body.get("declared_use") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "daily-use-cleanup", "apply"]:
        from release_authority_consumer_daily_use_recovery import cleanup_consumer_daily_use_artifacts
        payload = cleanup_consumer_daily_use_artifacts(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            use_id=str(body.get("use_id") or ""), use_schema=str(body.get("use_schema") or ""),
            use_version=str(body.get("use_version") or ""), declared_use=str(body.get("declared_use") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "successor-revalidation", "preview"]:
        from release_authority_consumer_daily_use_recovery import preview_successor_consumer_daily_use_revalidation
        payload = preview_successor_consumer_daily_use_revalidation(
            tuple(body.get("predecessor_consumer") or ()), str(body.get("predecessor_selection_purpose") or ""), tuple(body.get("predecessor_use") or ()),
            tuple(body.get("successor_consumer") or ()), str(body.get("successor_selection_purpose") or ""), tuple(body.get("successor_use") or ()),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "successor-revalidation", "create"]:
        from release_authority_consumer_daily_use_recovery import create_successor_consumer_daily_use_revalidation
        payload = create_successor_consumer_daily_use_revalidation(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            predecessor_consumer=tuple(body.get("predecessor_consumer") or ()), predecessor_selection_purpose=str(body.get("predecessor_selection_purpose") or ""),
            predecessor_use=tuple(body.get("predecessor_use") or ()), successor_consumer=tuple(body.get("successor_consumer") or ()),
            successor_selection_purpose=str(body.get("successor_selection_purpose") or ""), successor_use=tuple(body.get("successor_use") or ()),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
            interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer-use-handoff", "preview"]:
        from release_authority_consumer_use_handoff import preview_consumer_use_handoff_plan
        payload = preview_consumer_use_handoff_plan(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""),
            str(body.get("expected_use") or ""), str(body.get("selection_purpose") or ""), str(body.get("use_id") or ""),
            str(body.get("use_schema") or ""), str(body.get("use_version") or ""), str(body.get("declared_use") or ""),
            str(body.get("downstream_consumer_id") or ""), str(body.get("downstream_consumer_schema") or ""),
            str(body.get("downstream_consumer_version") or ""), str(body.get("downstream_expected_use") or ""),
            str(body.get("expected_result_schema") or ""), str(body.get("expected_result_version") or ""), str(body.get("expected_outcome") or ""),
            operator_tab_id=str(body.get("operator_tab_id") or ""), operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer-use-handoff", "create"]:
        from release_authority_consumer_use_handoff import create_consumer_use_handoff_plan
        payload = create_consumer_use_handoff_plan(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            selection_purpose=str(body.get("selection_purpose") or ""), use_id=str(body.get("use_id") or ""),
            use_schema=str(body.get("use_schema") or ""), use_version=str(body.get("use_version") or ""), declared_use=str(body.get("declared_use") or ""),
            downstream_consumer_id=str(body.get("downstream_consumer_id") or ""), downstream_consumer_schema=str(body.get("downstream_consumer_schema") or ""),
            downstream_consumer_version=str(body.get("downstream_consumer_version") or ""), downstream_expected_use=str(body.get("downstream_expected_use") or ""),
            expected_result_schema=str(body.get("expected_result_schema") or ""), expected_result_version=str(body.get("expected_result_version") or ""),
            expected_outcome=str(body.get("expected_outcome") or ""), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0), interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "result-validation", "preview"]:
        from release_authority_consumer_use_handoff import preview_downstream_consumer_result_validation
        payload = preview_downstream_consumer_result_validation(
            str(body.get("consumer_id") or ""), str(body.get("consumer_schema") or ""), str(body.get("consumer_version") or ""),
            str(body.get("expected_use") or ""), str(body.get("selection_purpose") or ""), str(body.get("use_id") or ""),
            str(body.get("use_schema") or ""), str(body.get("use_version") or ""), str(body.get("declared_use") or ""),
            str(body.get("downstream_consumer_id") or ""), str(body.get("downstream_consumer_schema") or ""),
            str(body.get("downstream_consumer_version") or ""), str(body.get("downstream_expected_use") or ""),
            str(body.get("expected_result_schema") or ""), str(body.get("expected_result_version") or ""), str(body.get("expected_outcome") or ""),
            dict(body.get("result") or {}), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-authority", "consumer", "result-validation", "create"]:
        from release_authority_consumer_use_handoff import create_downstream_consumer_result_validation_receipt
        payload = create_downstream_consumer_result_validation_receipt(
            str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""),
            consumer_id=str(body.get("consumer_id") or ""), consumer_schema=str(body.get("consumer_schema") or ""),
            consumer_version=str(body.get("consumer_version") or ""), expected_use=str(body.get("expected_use") or ""),
            use_id=str(body.get("use_id") or ""), use_schema=str(body.get("use_schema") or ""),
            use_version=str(body.get("use_version") or ""), declared_use=str(body.get("declared_use") or ""),
            result=dict(body.get("result") or {}), operator_tab_id=str(body.get("operator_tab_id") or ""),
            operation_revision=int(body.get("operation_revision") or 0), interrupt_after=str(body.get("interrupt_after") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "operation", "claim-preview"]:
        from release_certification_coherence import preview_operation_claim
        payload = preview_operation_claim(str(body.get("operation") or ""), str(body.get("tab_id") or ""), int(body.get("revision") or 0))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "operation", "claim"]:
        from release_certification_coherence import claim_operation
        payload = claim_operation(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-certification", "operation", "release"]:
        from release_certification_coherence import release_operation
        payload = release_operation(str(body.get("tab_id") or ""), int(body.get("generation") or 0), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "preview", "create"]:
        from release_promotion_preview import create_promotion_impact_preview
        payload = create_promotion_impact_preview()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "plan", "create"]:
        from release_promotion_plan import create_promotion_plan
        payload = create_promotion_plan()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "authorization-preview"]:
        from release_promotion_plan import preview_promotion_authorization
        payload = preview_promotion_authorization()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "apply"]:
        from release_promotion_transaction import apply_authorized_promotion
        payload = apply_authorized_promotion(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "resume-preview"]:
        from release_promotion_transaction import preview_promotion_resume
        payload = preview_promotion_resume()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "resume"]:
        from release_promotion_transaction import resume_promotion_transaction
        payload = resume_promotion_transaction(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "reversal-preview"]:
        from release_promotion_transaction import preview_promotion_reversal
        payload = preview_promotion_reversal()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-promotion", "reverse"]:
        from release_promotion_transaction import reverse_promotion
        payload = reverse_promotion(str(body.get("authorization_token") or ""), confirm=str(body.get("confirm") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "transaction", "authorization-preview"]:
        from release_installation_transaction import preview_installation_apply_authorization
        payload = preview_installation_apply_authorization()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "transaction", "apply"]:
        from release_installation_transaction import apply_authorized_installation
        payload = apply_authorized_installation(
            body.get("authorization_token") if isinstance(body.get("authorization_token"), str) else "",
            confirm=body.get("confirm") if isinstance(body.get("confirm"), str) else "",
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "recovery", "resume-preview"]:
        from release_installation_recovery import preview_installation_resume
        payload = preview_installation_resume()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "recovery", "resume"]:
        from release_installation_recovery import resume_installation_transaction
        payload = resume_installation_transaction(
            body.get("authorization_token") if isinstance(body.get("authorization_token"), str) else "",
            confirm=body.get("confirm") if isinstance(body.get("confirm"), str) else "",
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "recovery", "rollback-preview"]:
        from release_installation_recovery import preview_installation_rollback
        payload = preview_installation_rollback()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "recovery", "rollback"]:
        from release_installation_recovery import rollback_installation_transaction
        payload = rollback_installation_transaction(
            body.get("authorization_token") if isinstance(body.get("authorization_token"), str) else "",
            confirm=body.get("confirm") if isinstance(body.get("confirm"), str) else "",
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "staging", "authorization-preview"]:
        from release_installation_staging import preview_installation_staging_authorization
        payload = preview_installation_staging_authorization()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "staging", "create"]:
        from release_installation_staging import stage_authorized_installation
        payload = stage_authorized_installation(
            body.get("authorization_token") if isinstance(body.get("authorization_token"), str) else "",
            confirm=body.get("confirm") if isinstance(body.get("confirm"), str) else "",
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "plan", "create"]:
        from release_installation_plan import create_installation_plan
        payload = create_installation_plan()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-installation", "preview", "create"]:
        from release_installation_preview import create_installation_impact_preview
        payload = create_installation_impact_preview(str(body.get("target_project_id") or ""))
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "inspect"]:
        from release_handoff_inspection import inspect_selected_candidate_archive
        archive_path = str(body.get("archive_path") or "").strip()
        if not archive_path:
            raise ApiError(400, "archive_path is required; archive discovery and automatic selection are not supported")
        try:
            payload = inspect_selected_candidate_archive(archive_path)
        except (OSError, TypeError, ValueError) as error:
            raise ApiError(400, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "recovery", "preview"]:
        from release_handoff_recovery import preview_handoff_recovery
        payload = preview_handoff_recovery()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "recovery", "apply"]:
        from release_handoff_recovery import confirm_handoff_recovery
        payload = confirm_handoff_recovery(
            preview_token=str(body.get("preview_token") or ""),
            operator_confirmed=body.get("operator_confirmed") is True,
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "replacement", "preview"]:
        from release_handoff_recovery import preview_handoff_replacement
        archive_path = str(body.get("archive_path") or "").strip()
        if not archive_path:
            raise ApiError(400, "archive_path is required; replacement archives are never discovered automatically")
        try:
            payload = preview_handoff_replacement(archive_path)
        except (OSError, TypeError, ValueError) as error:
            raise ApiError(400, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "replacement", "apply"]:
        from release_handoff_recovery import confirm_handoff_replacement
        payload = confirm_handoff_replacement(
            preview_token=str(body.get("preview_token") or ""),
            operator_confirmed=body.get("operator_confirmed") is True,
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "cleanup", "preview"]:
        from release_handoff_recovery import preview_abandoned_handoff_cleanup
        payload = preview_abandoned_handoff_cleanup()
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-handoff", "cleanup", "apply"]:
        from release_handoff_recovery import confirm_abandoned_handoff_cleanup
        payload = confirm_abandoned_handoff_cleanup(
            preview_token=str(body.get("preview_token") or ""),
            operator_confirmed=body.get("operator_confirmed") is True,
            confirmation_phrase=str(body.get("confirmation_phrase") or ""),
        )
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["release-history-reconciliation", "apply"]:
        from release_history_reconciliation import apply_release_history_reconciliation
        try:
            payload = apply_release_history_reconciliation(
                preview_token=str(body.get("preview_token") or ""),
                operator_confirmed=body.get("operator_confirmed") is True,
            )
        except (OSError, TypeError, ValueError) as error:
            raise ApiError(400, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["version-reconciliation", "apply"]:
        from version_drift_reconciliation import apply_version_reconciliation
        try:
            payload = apply_version_reconciliation(
                str(body.get("surface_id") or ""),
                preview_token=str(body.get("preview_token") or ""),
                operator_confirmed=body.get("operator_confirmed") is True,
                mutable_runtime_confirmed=body.get("mutable_runtime_confirmed") is True,
                expected_role=str(body.get("expected_role") or "working_source"),
                expected_version=str(body.get("expected_version") or ""),
            )
        except (OSError, TypeError, ValueError) as error:
            raise ApiError(400, str(error)) from error
        return (200 if payload.get("ok") else 409), _ok(payload)

    if parts == ["conversation", "evaluation-finding"]:
        action = str(body.get("action") or "").strip().lower()
        finding_id = str(body.get("finding_id") or "").strip()
        expected_raw = body.get("expected_revision")
        try:
            expected_revision = int(expected_raw) if expected_raw not in {None, ""} else None
        except (TypeError, ValueError) as error:
            raise ApiError(400, "expected_revision must be an integer.") from error
        confirmed = _body_bool(body, "operator_confirmed", False)
        try:
            if action == "create":
                result = create_evaluation_finding(
                    finding_title=str(body.get("finding_title") or ""),
                    finding_details=str(body.get("finding_details") or ""),
                    issue_domain=str(body.get("issue_domain") or ""),
                    severity=str(body.get("severity") or ""),
                    campaign_id=str(body.get("campaign_id") or ""),
                    evaluation_id=str(body.get("evaluation_id") or ""),
                    operator_confirmed=confirmed,
                    finding_id=finding_id,
                )
            elif action == "update_details":
                result = update_evaluation_finding_details(
                    finding_id,
                    finding_title=str(body.get("finding_title") or ""),
                    finding_details=str(body.get("finding_details") or ""),
                    issue_domain=str(body.get("issue_domain") or ""),
                    severity=str(body.get("severity") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "set_state":
                result = set_evaluation_finding_state(
                    finding_id,
                    state=str(body.get("state") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "record_reproduction_attempt":
                result = record_reproduction_attempt(
                    finding_id,
                    outcome=str(body.get("outcome") or ""),
                    environment_kind=str(body.get("environment_kind") or ""),
                    environment_label=str(body.get("environment_label") or ""),
                    note=str(body.get("reproduction_note") or body.get("note") or ""),
                    evidence_digest=str(body.get("evidence_digest") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "remove_reproduction_attempt":
                result = remove_reproduction_attempt(
                    finding_id,
                    str(body.get("attempt_id") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "add_repair_candidate":
                result = add_repair_candidate_reference(
                    finding_id,
                    reference_kind=str(body.get("reference_kind") or ""),
                    reference_value=str(body.get("reference_value") or ""),
                    label=str(body.get("reference_label") or body.get("label") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "update_repair_candidate":
                result = update_repair_candidate_reference(
                    finding_id,
                    str(body.get("repair_reference_id") or ""),
                    state=str(body.get("state") or ""),
                    label=(str(body.get("reference_label") or body.get("label") or "") if ("reference_label" in body or "label" in body) else None),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "remove_repair_candidate":
                result = remove_repair_candidate_reference(
                    finding_id,
                    str(body.get("repair_reference_id") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "start_triage":
                result = start_evaluation_finding_triage(
                    finding_id,
                    note=str(body.get("triage_note") or body.get("note") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "set_triage_disposition":
                result = set_evaluation_finding_triage_disposition(
                    finding_id,
                    disposition=str(body.get("disposition") or ""),
                    note=(str(body.get("triage_note") or body.get("note") or "") if ("triage_note" in body or "note" in body) else None),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "complete_triage":
                result = complete_evaluation_finding_triage(
                    finding_id,
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "reopen_triage":
                result = reopen_evaluation_finding_triage(
                    finding_id,
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "register_review_candidate":
                result = register_repair_candidate(
                    finding_id,
                    candidate_kind=str(body.get("candidate_kind") or ""),
                    artifact_sha256=str(body.get("artifact_sha256") or ""),
                    source_manifest_sha256=str(body.get("source_manifest_sha256") or ""),
                    evidence_digest=str(body.get("evidence_digest") or ""),
                    label=str(body.get("candidate_label") or body.get("label") or ""),
                    private_reference=str(body.get("candidate_reference") or body.get("reference_value") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "record_candidate_review":
                result = record_repair_candidate_review(
                    finding_id,
                    str(body.get("candidate_id") or ""),
                    review_area=str(body.get("review_area") or ""),
                    review_outcome=str(body.get("review_outcome") or ""),
                    evidence_digest=str(body.get("evidence_digest") or ""),
                    note=str(body.get("review_note") or body.get("note") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "record_candidate_verification_evidence":
                result = record_repair_candidate_verification_evidence(
                    finding_id,
                    str(body.get("candidate_id") or ""),
                    evidence_kind=str(body.get("evidence_kind") or ""),
                    result=str(body.get("verification_result") or body.get("result") or ""),
                    evidence_digest=str(body.get("evidence_digest") or ""),
                    passed_checks=body.get("passed_checks", 0),
                    total_checks=body.get("total_checks", 0),
                    suite_count=body.get("suite_count", 0),
                    source_tree_unchanged=_body_bool(body, "source_tree_unchanged", False),
                    note=str(body.get("verification_note") or body.get("note") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "link_candidate_lineage":
                result = link_repair_candidate_lineage(
                    finding_id,
                    predecessor_candidate_id=str(body.get("predecessor_candidate_id") or ""),
                    successor_candidate_id=str(body.get("successor_candidate_id") or ""),
                    relation_kind=str(body.get("relation_kind") or ""),
                    evidence_digest=str(body.get("evidence_digest") or ""),
                    note=str(body.get("lineage_note") or body.get("note") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            else:
                raise EvaluationFindingError("Unsupported evaluation finding action.")
        except EvaluationFindingError as error:
            raise ApiError(409, str(error)) from error
        return 200, _ok(result)

    if parts == ["conversation", "evaluation-campaign"]:
        action = str(body.get("action") or "").strip().lower()
        campaign_id = str(body.get("campaign_id") or "").strip()
        evaluation_id = str(body.get("evaluation_id") or "").strip()
        follow_up_id = str(body.get("follow_up_id") or "").strip()
        expected_raw = body.get("expected_revision")
        try:
            expected_revision = int(expected_raw) if expected_raw not in {None, ""} else None
        except (TypeError, ValueError) as error:
            raise ApiError(400, "expected_revision must be an integer.") from error
        confirmed = _body_bool(body, "operator_confirmed", False)
        try:
            if action == "create":
                result = create_evaluation_campaign(
                    campaign_label=str(body.get("campaign_label") or ""),
                    objective=str(body.get("objective") or ""),
                    focus_areas=body.get("focus_areas"),
                    target_evaluation_count=body.get("target_evaluation_count", 1),
                    minimum_completed_evaluations=body.get("minimum_completed_evaluations", 1),
                    planned_duration_days=body.get("planned_duration_days", 1),
                    required_signals=body.get("required_signals"),
                    operator_confirmed=confirmed,
                    campaign_id=campaign_id,
                )
            elif action == "update_plan":
                result = update_evaluation_campaign_plan(
                    campaign_id,
                    campaign_label=str(body.get("campaign_label") or ""),
                    objective=str(body.get("objective") or ""),
                    focus_areas=body.get("focus_areas"),
                    target_evaluation_count=body.get("target_evaluation_count", 1),
                    minimum_completed_evaluations=body.get("minimum_completed_evaluations", 1),
                    planned_duration_days=body.get("planned_duration_days", 1),
                    required_signals=body.get("required_signals"),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "activate":
                result = activate_evaluation_campaign(
                    campaign_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "enroll":
                result = enroll_daily_evaluation(
                    campaign_id, evaluation_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "unenroll":
                result = unenroll_daily_evaluation(
                    campaign_id, evaluation_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "add_follow_up":
                result = add_evaluation_campaign_follow_up(
                    campaign_id,
                    reference_kind=str(body.get("reference_kind") or ""),
                    reference_value=str(body.get("reference_value") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "update_follow_up":
                result = update_evaluation_campaign_follow_up_state(
                    campaign_id,
                    follow_up_id,
                    state=str(body.get("follow_up_state") or body.get("state") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "remove_follow_up":
                result = remove_evaluation_campaign_follow_up(
                    campaign_id,
                    follow_up_id,
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "start_review":
                result = start_evaluation_campaign_review(
                    campaign_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "set_review_disposition":
                result = set_evaluation_campaign_review_disposition(
                    campaign_id,
                    finding_kind=str(body.get("finding_kind") or ""),
                    finding_value=str(body.get("finding_value") or ""),
                    disposition=str(body.get("disposition") or ""),
                    note=str(body.get("review_note") or body.get("note") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "remove_review_disposition":
                result = remove_evaluation_campaign_review_disposition(
                    campaign_id,
                    finding_kind=str(body.get("finding_kind") or ""),
                    finding_value=str(body.get("finding_value") or ""),
                    expected_revision=expected_revision,
                    operator_confirmed=confirmed,
                )
            elif action == "complete_review":
                result = complete_evaluation_campaign_review(
                    campaign_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "reopen_review":
                result = reopen_evaluation_campaign_review(
                    campaign_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "complete":
                result = complete_evaluation_campaign(
                    campaign_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            elif action == "abort":
                result = abort_evaluation_campaign(
                    campaign_id, expected_revision=expected_revision, operator_confirmed=confirmed
                )
            else:
                raise EvaluationCampaignError("Unsupported evaluation campaign action.")
        except EvaluationCampaignError as error:
            raise ApiError(409, str(error)) from error
        return 200, _ok(result)

    if parts == ["conversation", "steer"]:
        try:
            result = request_generation_steering(
                str(body.get("session_id") or ""),
                str(body.get("operation_id") or ""),
                str(body.get("redirect_message") or ""),
            )
        except (ConversationSteeringError, ValueError) as error:
            raise ApiError(409, str(error)) from error
        return 200, _ok(result)

    if parts == ["conversation", "turn-action"]:
        action = str(body.get("action") or "").strip().lower()
        use_ai_raw = body.get("use_ai", True)
        use_ai = bool(use_ai_raw) if not isinstance(use_ai_raw, str) else use_ai_raw.lower() in {"1", "true", "yes", "on"}
        operation_id = str(body.get("operation_id") or "").strip()
        if action in {"regenerate_completed_response", "explicit_resend"} and not operation_id:
            raise ApiError(400, "A fresh explicit operation_id is required for regeneration or resend.")
        try:
            result = execute_turn_action(
                str(body.get("session_id") or ""),
                str(body.get("turn_id") or ""),
                action,
                use_ai=use_ai,
                expected_recovery_cue=str(body.get("recovery_cue") or ""),
                operation_id=operation_id,
            )
        except (ConversationTurnActionError, ValueError) as error:
            raise ApiError(409, str(error)) from error
        return 200, _ok(result.to_dict(include_response=True))

    if parts == ["conversation", "message-branch"]:
        try:
            result = create_message_edit_branch(
                str(body.get("session_id") or ""),
                str(body.get("turn_id") or ""),
                str(body.get("edited_user_message") or ""),
                branch_request_id=str(body.get("branch_request_id") or ""),
                title=str(body.get("title") or ""),
                select_session=_body_bool(body, "select_session", True),
            )
        except (ConversationBranchError, ValueError) as error:
            raise ApiError(409, str(error)) from error
        return 200, _ok(result)

    if parts == ["local-model", "configuration"]:
        patch = body.get("settings", body)
        if not isinstance(patch, dict):
            raise ApiError(400, "Local-model settings must be a JSON object.")
        try:
            report = save_local_model_configuration(patch)
        except LocalModelConfigurationValidationError as error:
            raise ApiError(400, "Local-model settings were not saved.", error.to_dict()) from error
        return 200, _ok(report, message="Local-model settings saved after validation.")

    if parts == ["local-model", "readiness"]:
        patch = body.get("settings")
        requested_previous_state = str(body.get("previous_state") or "").strip() or None
        trigger = str(body.get("recovery_trigger") or "api_post").strip().lower()
        if trigger not in {"manual_check", "visibility_recovery", "api_post"}:
            trigger = "api_post"
        current_settings = load_settings()
        try:
            configured_digest = configuration_digest(LocalModelConfig.from_settings(current_settings).validated())
        except Exception:
            configured_digest = ""
        prior_evidence = load_provider_recovery_evidence() or {}
        persisted_previous_state = str(prior_evidence.get("observed_state") or prior_evidence.get("state") or "").strip() or None
        if patch is None:
            report = provider_readiness(previous_state=persisted_previous_state or requested_previous_state)
        else:
            if not isinstance(patch, dict):
                raise ApiError(400, "Local-model readiness settings must be a JSON object.")
            try:
                merged, config = validate_local_model_configuration(patch)
            except LocalModelConfigurationValidationError as error:
                raise ApiError(400, "Local-model readiness settings are invalid.", error.to_dict()) from error
            submitted_digest = configuration_digest(config)
            authoritative_previous_state = (
                persisted_previous_state
                if configured_digest and submitted_digest == configured_digest
                else requested_previous_state
            )
            report = provider_readiness(settings=merged, config=config, previous_state=authoritative_previous_state)
        evidence = persist_provider_recovery_evidence(
            report, configured_configuration_digest=configured_digest, trigger=trigger,
        )
        report["persisted_recovery_evidence"] = evidence
        report["provider_resume_cue"] = provider_resume_cue(evidence)
        return 200, _ok(report)

    if parts == ["local-model", "native-smoke"]:
        if str(body.get("confirm") or "") != "RUN_NATIVE_MODEL_SMOKE":
            raise ApiError(400, "Native model smoke requires exact confirm='RUN_NATIVE_MODEL_SMOKE'.")
        patch = body.get("settings")
        config = None
        merged = None
        if patch is not None:
            if not isinstance(patch, dict):
                raise ApiError(400, "Native-smoke settings must be a JSON object.")
            try:
                merged, config = validate_local_model_configuration(patch)
            except LocalModelConfigurationValidationError as error:
                raise ApiError(400, "Native-smoke settings are invalid.", error.to_dict()) from error
        try:
            timeout_seconds = float(body.get("timeout_seconds", 30.0))
        except (TypeError, ValueError) as error:
            raise ApiError(400, "timeout_seconds must be a number.") from error
        report = native_model_smoke(
            settings=merged,
            config=config,
            confirmed=True,
            timeout_seconds=timeout_seconds,
            readiness_configuration_digest=str(body.get("readiness_configuration_digest") or "") or None,
        )
        status = 200 if report.get("status") in {"pass", "partial"} else 422
        return status, _ok(report)

    if parts == ["local-model", "native-conversation-validation"]:
        if str(body.get("confirm") or "") != NATIVE_CONVERSATION_CONFIRMATION:
            raise ApiError(400, f"Native conversation validation requires exact confirm={NATIVE_CONVERSATION_CONFIRMATION!r}.")
        patch = body.get("settings")
        config = None
        merged = None
        if patch is not None:
            if not isinstance(patch, dict):
                raise ApiError(400, "Native conversation validation settings must be a JSON object.")
            try:
                merged, config = validate_local_model_configuration(patch)
            except LocalModelConfigurationValidationError as error:
                raise ApiError(400, "Native conversation validation settings are invalid.", error.to_dict()) from error
        try:
            timeout_seconds = float(body.get("timeout_seconds", 45.0))
            first_token_budget_ms = int(body.get("first_token_budget_ms", 8000))
            total_budget_ms = int(body.get("total_budget_ms", 30000))
        except (TypeError, ValueError) as error:
            raise ApiError(400, "Native conversation validation timing values must be numeric.") from error
        try:
            report = run_native_conversation_validation(
                confirmed=True,
                confirmation=NATIVE_CONVERSATION_CONFIRMATION,
                settings=merged,
                config=config,
                timeout_seconds=timeout_seconds,
                first_token_budget_ms=first_token_budget_ms,
                total_budget_ms=total_budget_ms,
                validation_id=str(body.get("validation_id") or "") or None,
                persist=True,
            )
        except ValueError as error:
            raise ApiError(400, str(error)) from error
        status = 200 if report.get("status") in {"pass", "partial"} else 422
        return status, _ok(report)

    if parts == ["source-surface", "manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion", "run"]:
        from manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion import OPERATOR_CONFIRMATION_PHRASE, build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion

        confirmation = str(body.get("confirmation") or "")
        if confirmation != OPERATOR_CONFIRMATION_PHRASE:
            raise ApiError(400, "Fixture batch truth stabilization run requires exact operator confirmation.")
        report = build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion(None, inspect_sources=True, execute_batch=True, operator_confirmed=True)
        report.setdefault("warnings", []).append("POST was explicitly confirmed, but actual fixture execution remains blocked unless an audited OS-enforced sandbox backend is available. Generated dispatch, release, and autonomy remain unauthorized.")
        return 200, _ok(report)

    if parts == ["installed-tree-cleanup", "enforcement", "run"]:
        from installed_tree_cleanup_enforcement import OPERATOR_CONFIRMATION_PHRASE, build_installed_tree_cleanup_enforcement

        confirmation = str(body.get("confirmation") or "")
        if confirmation != OPERATOR_CONFIRMATION_PHRASE:
            raise ApiError(400, "Installed-tree cleanup enforcement requires exact operator confirmation.")
        report = build_installed_tree_cleanup_enforcement(None, inspect_sources=True, apply_cleanup=True, confirmation=confirmation)
        report.setdefault("warnings", []).append("POST was explicitly confirmed; only unreferenced obsolete generated source candidates may be deleted. Active imported modules, runtime/private data, generated wiring, release, and autonomy remain protected.")
        return 200, _ok(report)

    if parts in (["release", "durable-memory-write"], ["durable-memory-write"], ["autonomy", "durable-memory-write"]):
        project_id = str(body.get("project", "eidolon"))
        execute = _body_bool(body, "execute", False) or _body_bool(body, "approve", False)
        confirmation = str(body.get("confirmation") or body.get("memory_confirm_phrase") or "")
        promotion_id = str(body.get("promotion_id") or body.get("memory_promotion_id") or "") or None
        goal = str(body.get("goal") or body.get("autonomy_goal") or "") or None
        if execute:
            if not confirmation:
                raise ApiError(400, "Durable memory write requires exact confirmation.")
        report = sm_v45.build_controlled_durable_memory_write_path(project_id=project_id, goal=goal, promotion_id=promotion_id, confirmation=confirmation, execute=execute, save=True)
        status = 200 if report.get("ok") else 409
        return status, _ok(report)


    if parts in (["release", "memory-removal-confirmation-path"], ["memory-removal-confirmation-path"], ["autonomy", "memory-removal-confirmation-path"]):
        project_id = str(body.get("project", "eidolon"))
        execute = _body_bool(body, "execute", False) or _body_bool(body, "approve", False)
        confirmation = str(body.get("confirmation") or body.get("memory_confirm_phrase") or "")
        memory_id = str(body.get("memory_id") or "") or None
        goal = str(body.get("goal") or body.get("autonomy_goal") or "") or None
        if execute and not confirmation:
            raise ApiError(400, "Memory removal requires exact confirmation.")
        report = sm_v45.build_memory_removal_confirmation_path(project_id=project_id, goal=goal, memory_id=memory_id, confirmation=confirmation, execute=execute, save=True)
        status = 200 if report.get("ok") else 409
        return status, _ok(report)

    if parts == ["controlled-self-build"]:
        project_id = str(body.get("project", "eidolon"))
        max_steps = int(body.get("steps", body.get("max_steps", 1)) or 1)
        live = _body_bool(body, "live", False)
        approve = _body_bool(body, "approve", False)
        use_ai = _body_bool(body, "use_ai", False)
        if live:
            _require_confirmation(body, "LIVE_CONTROLLED_BUILD")
        return 200, _ok(build_controlled_self_build(project_id=project_id, max_steps=max_steps, live=live, approve_live=approve, use_ai=use_ai))

    if len(parts) >= 2 and parts[0] == "controlled-build":
        project_id = str(body.get("project", "eidolon"))
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        live = _body_bool(body, "live", False)
        action = parts[1]
        if action == "plan-patch":
            return 200, _ok(build_patch_plan(project_id=project_id, target_version=str(body.get("version", "10.0")), save=True))
        if action == "stage-patch":
            return 200, _ok(stage_controlled_patch(project_id=project_id, save=True))
        if action == "preview-diff":
            return 200, _ok(preview_staged_diff(project_id=project_id, stage_if_missing=True, save=True))
        if action == "apply-staged-patch":
            if not dry_run and approve:
                _require_confirmation(body, "APPLY_STAGED_PATCH")
            return 200, _ok(apply_staged_patch(project_id=project_id, approve=approve, dry_run=dry_run))
        if action == "verify-latest-patch":
            return 200, _ok(verify_latest_patch(project_id=project_id))
        if action == "rollback-latest-patch":
            if not dry_run and approve:
                _require_confirmation(body, "ROLLBACK_LATEST_PATCH")
            return 200, _ok(rollback_latest_patch(project_id=project_id, approve=approve, dry_run=dry_run))
        if action == "cycle":
            if live:
                _require_confirmation(body, "LIVE_CONTROLLED_BUILD_CYCLE")
            return 200, _ok(build_controlled_build_cycle(project_id=project_id, live=live, approve=approve, dry_run=dry_run or not live))

    if parts == ["controlled-build-cycle"]:
        project_id = str(body.get("project", "eidolon"))
        live = _body_bool(body, "live", False)
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if live:
            _require_confirmation(body, "LIVE_CONTROLLED_BUILD_CYCLE")
        return 200, _ok(build_controlled_build_cycle(project_id=project_id, live=live, approve=approve, dry_run=dry_run or not live))

    if parts == ["supervised-dev-loop"]:
        project_id = str(body.get("project", "eidolon"))
        live = _body_bool(body, "live", False)
        approve = _body_bool(body, "approve", False)
        use_ai = _body_bool(body, "use_ai", False)
        if live:
            _require_confirmation(body, "LIVE_SUPERVISED_DEV_LOOP")
        return 200, _ok(build_supervised_dev_loop(project_id=project_id, live=live, approve=approve, use_ai=use_ai))

    if parts == ["workspace", "apply"]:
        project_id = str(body.get("project", "eidolon"))
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "GUARDED_WORKSPACE_APPLY")
        return 200, _ok(build_workspace_apply(project_id=project_id, approve=approve, dry_run=dry_run or not approve))

    if parts == ["workspace", "guarded-dev-loop"]:
        project_id = str(body.get("project", "eidolon"))
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "GUARDED_WORKSPACE_DEV_LOOP")
        return 200, _ok(build_guarded_workspace_dev_loop(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=bool(approve and not dry_run)))

    if parts == ["patch-draft-request"]:
        return 200, _ok(build_patch_draft_request(
            project_id=str(body.get("project", "eidolon")),
            target_version=str(body.get("target_version") or body.get("version") or "20.0.1"),
            task=str(body.get("task")) if body.get("task") is not None else None,
            intent=str(body.get("intent")) if body.get("intent") is not None else None,
            constraints=[str(item) for item in body.get("constraints", [])] if isinstance(body.get("constraints", []), list) else None,
            expected_files=[str(item) for item in body.get("expected_files", [])] if isinstance(body.get("expected_files", []), list) else None,
            risk_limit=str(body.get("risk_limit") or "medium"),
            save=True,
        ))

    if parts == ["draft-patch"]:
        return 200, _ok(build_draft_patch(project_id=str(body.get("project", "eidolon")), save=True))

    if parts == ["patch-review-notes"]:
        return 200, _ok(build_patch_review_notes(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["draft-diff"]:
        return 200, _ok(build_draft_diff(project_id=str(body.get("project", "eidolon")), save=True))

    if parts == ["draft-test-impact"]:
        return 200, _ok(build_draft_test_impact(project_id=str(body.get("project", "eidolon")), save=True))

    if parts == ["approve-draft"]:
        return 200, _ok(approve_draft(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["reject-draft"]:
        return 200, _ok(reject_draft(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["apply-approved-draft"]:
        dry_run = _body_bool(body, "dry_run", True)
        if not dry_run:
            _require_confirmation(body, "APPLY_APPROVED_DRAFT")
        return 200, _ok(build_apply_approved_draft(project_id=str(body.get("project", "eidolon")), dry_run=dry_run, save=True))

    if parts == ["rollback-approved-draft"]:
        dry_run = _body_bool(body, "dry_run", True)
        approve = _body_bool(body, "approve", False)
        if approve and not dry_run:
            _require_confirmation(body, "ROLLBACK_APPROVED_DRAFT")
        return 200, _ok(build_rollback_approved_draft(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts == ["reopen-draft"]:
        return 200, _ok(reopen_draft(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["human-approved-patch-loop"]:
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "HUMAN_APPROVED_PATCH_LOOP")
        return 200, _ok(build_human_approved_patch_loop(project_id=str(body.get("project", "eidolon")), approve_apply=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["patch-drafts", "quality"], ["draft-quality"]):
        return 200, _ok(build_draft_quality(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "file-targets"], ["draft-file-targets"]):
        return 200, _ok(build_draft_file_targets(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "intent-blocks"], ["draft-intent-blocks"]):
        return 200, _ok(build_draft_intent_blocks(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "conflicts"], ["draft-conflicts"]):
        return 200, _ok(build_draft_conflicts(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "verification-bundle"], ["draft-verification-bundle"]):
        return 200, _ok(build_draft_verification_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "review-checklist"], ["draft-review-checklist"]):
        return 200, _ok(build_draft_review_checklist(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "execution-report"], ["approved-draft-execution-report"]):
        return 200, _ok(build_approved_draft_execution_report(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "review-loop"], ["review-centered-patch-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "REVIEW_CENTERED_PATCH_LOOP")
        return 200, _ok(build_review_centered_patch_loop(project_id=str(body.get("project", "eidolon")), approve_apply=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-edit-proposal"], ["patch-drafts", "code-edit-proposal"]):
        return 200, _ok(build_code_edit_proposal(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["safe-rewrite-preview"], ["patch-drafts", "safe-rewrite-preview"]):
        return 200, _ok(build_safe_rewrite_preview(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["generate-code-patch"], ["patch-drafts", "generated-code-patch"]):
        return 200, _ok(build_generated_code_patch(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["test-suggestions"], ["patch-drafts", "test-suggestions"]):
        return 200, _ok(build_test_suggestions(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["inline-review-note"], ["patch-drafts", "inline-review-note"]):
        return 200, _ok(build_inline_review_note(
            project_id=str(body.get("project", "eidolon")),
            note=str(body.get("note")) if body.get("note") is not None else None,
            file_path=str(body.get("file")) if body.get("file") is not None else None,
            intent_block=str(body.get("intent_block")) if body.get("intent_block") is not None else None,
            save=True,
        ))

    if parts in (["apply-approved-code-patch"], ["patch-drafts", "apply-approved-code-patch"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPLY_APPROVED_CODE_PATCH")
        return 200, _ok(build_apply_approved_code_patch(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["prepare-release-package"], ["release", "package"]):
        return 200, _ok(build_prepare_release_package(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name")) if body.get("package_name") is not None else None, save=True))

    if parts in (["release-readiness"], ["release", "readiness"]):
        return 200, _ok(build_release_readiness(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["human-approved-release-loop"], ["release", "human-approved-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "HUMAN_APPROVED_RELEASE_LOOP")
        return 200, _ok(build_human_approved_release_loop(project_id=str(body.get("project", "eidolon")), approve_apply=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "status"], ["code-patch-status"]):
        return 200, _ok(build_code_patch_status(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "symbol-scan"], ["symbol-scan"]):
        return 200, _ok(build_symbol_scan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "rewrite-plan"], ["rewrite-plan"]):
        return 200, _ok(build_rewrite_plan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "rewrite-conflicts"], ["rewrite-conflicts"]):
        return 200, _ok(build_rewrite_conflicts(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "diff-bundle"], ["code-patch-diff-bundle"]):
        return 200, _ok(build_code_patch_diff_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "apply-transaction"], ["apply-code-patch-transaction"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPLY_CODE_PATCH_TRANSACTION")
        return 200, _ok(build_apply_code_patch_transaction(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "semantic-checks"], ["semantic-checks"]):
        return 200, _ok(build_semantic_checks(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "artifact"], ["release-artifact"]):
        return 200, _ok(build_release_artifact(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name")) if body.get("package_name") is not None else None, save=True))

    if parts in (["release", "audit-trail"], ["release-audit-trail"]):
        return 200, _ok(build_release_audit_trail(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "generated-code-loop"], ["generated-code-release-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "GENERATED_CODE_RELEASE_LOOP")
        return 200, _ok(build_generated_code_release_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "task-to-code-patch"], ["task-to-code-patch"]):
        return 200, _ok(build_task_to_code_patch(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "code-context"], ["code-context"]):
        return 200, _ok(build_code_context(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "patch-prompt"], ["patch-prompt"]):
        return 200, _ok(build_patch_prompt(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "parse-generated-edits"], ["parse-generated-edits"]):
        return 200, _ok(build_parse_generated_edits(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "edit-consistency"], ["edit-consistency"]):
        return 200, _ok(build_edit_consistency(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "ai-dry-run"], ["ai-code-patch-dry-run"]):
        return 200, _ok(build_ai_code_patch_dry_run(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "failure-analysis"], ["patch-failure-analysis"]):
        return 200, _ok(build_patch_failure_analysis(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "learning-notes"], ["patch-learning-notes"]):
        return 200, _ok(build_patch_learning_notes(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") else None, save=True))

    if parts in (["code-patches", "ai-assisted-loop"], ["ai-assisted-code-patch-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "AI_ASSISTED_CODE_PATCH_LOOP")
        return 200, _ok(build_ai_assisted_code_patch_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "objective-refinement"], ["refine-patch-objective"]):
        return 200, _ok(build_patch_objective_refinement(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "context-ranking"], ["rank-code-context"]):
        return 200, _ok(build_code_context_ranking(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "safety-envelope"], ["patch-safety-envelope"]):
        return 200, _ok(build_patch_safety_envelope(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "validate-generated-patch"], ["validate-generated-patch"]):
        return 200, _ok(build_generated_patch_validation(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "simulation"], ["patch-simulation"]):
        return 200, _ok(build_patch_simulation(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "test-stub-plan"], ["test-stub-plan"]):
        return 200, _ok(build_test_stub_plan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "review-score"], ["patch-review-score"]):
        return 200, _ok(build_patch_review_score(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "recovery-plan"], ["patch-recovery-plan"]):
        return 200, _ok(build_patch_recovery_plan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "validated-ai-loop"], ["validated-ai-code-patch-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "VALIDATED_AI_CODE_PATCH_LOOP")
        return 200, _ok(build_validated_ai_code_patch_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "apply-validated-ai-patch"], ["apply-validated-ai-patch"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPLY_VALIDATED_AI_PATCH")
        return 200, _ok(build_apply_validated_ai_patch(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["release", "approval-to-release-loop"], ["approval-to-release-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPROVAL_TO_RELEASE_LOOP")
        return 200, _ok(build_approval_to_release_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "refresh-review-bundle"], ["refresh-ai-patch-review-bundle"]):
        return 200, _ok(build_ai_patch_review_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "bind-validated-approval"], ["bind-validated-approval"]):
        return 200, _ok(bind_current_approval_to_validated_manifest(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "manifest-integrity"], ["release-manifest-integrity"]):
        return 200, _ok(build_release_manifest_integrity(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "package-inventory"], ["package-inventory"]):
        return 200, _ok(build_package_inventory(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "package-checksums"], ["package-checksums"]):
        return 200, _ok(build_package_checksums(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "notes"], ["release-notes"]):
        return 200, _ok(build_release_notes(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "handoff"], ["release-handoff-report"]):
        return 200, _ok(build_release_handoff_report(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "build-zip"], ["build-release-zip"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "BUILD_RELEASE_ZIP")
        return 200, _ok(build_release_zip(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "verify-unzip"], ["verify-release-unzip"]):
        return 200, _ok(build_verify_release_unzip(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "pipeline-audit"], ["release-pipeline-audit"]):
        return 200, _ok(build_release_pipeline_audit(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "verified-package-loop"], ["verified-release-package-loop"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "VERIFIED_RELEASE_PACKAGE_LOOP")
        return 200, _ok(build_verified_release_package_loop(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "profiles"], ["release-profiles"]):
        return 200, _ok(build_release_profiles(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "privacy-scan"], ["package-privacy-scan"]):
        return 200, _ok(build_package_privacy_scan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "portable-metadata"], ["portable-metadata-check"]):
        return 200, _ok(build_portable_metadata_check(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "first-run-check"], ["first-run-check"]):
        return 200, _ok(build_first_run_check(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "dependency-advisor"], ["dependency-advisor"]):
        return 200, _ok(build_dependency_advisor(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "upgrade-notes"], ["upgrade-notes"]):
        return 200, _ok(build_upgrade_notes(project_id=str(body.get("project", "eidolon")), to_version=str(body.get("to_version") or "21.0"), save=True))

    if parts in (["release", "runtime-migration"], ["runtime-migration-check"]):
        return 200, _ok(build_runtime_migration_check(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "install-verification"], ["release-install-verification"]):
        return 200, _ok(build_release_install_verification(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), run_smoke=_body_bool(body, "run_smoke", False), save=True))

    if parts in (["release", "verified-installable-loop"], ["verified-installable-release-loop"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "VERIFIED_INSTALLABLE_RELEASE_LOOP")
        return 200, _ok(build_verified_installable_release_loop(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), confirm=confirm, dry_run=dry_run or not confirm, run_smoke=_body_bool(body, "run_smoke", False), save=True))

    if parts in (["release", "smoke-runtime-hardening"], ["smoke-runtime-hardening"]):
        return 200, _ok(build_smoke_runtime_hardening(project_id=str(body.get("project", "eidolon")), tier=str(body.get("tier") or "full"), save=True))

    if parts in (["release", "external-zip-install-verification"], ["external-zip-install-verification"]):
        return 200, _ok(build_external_zip_install_verification(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "deterministic-release-manifest"], ["deterministic-release-manifest"]):
        return 200, _ok(build_deterministic_release_manifest(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "update-dry-run-plan"], ["update-dry-run-plan"]):
        return 200, _ok(build_update_dry_run_plan(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "atomic-source-update"], ["atomic-source-update"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "ATOMIC_SOURCE_UPDATE")
        return 200, _ok(build_atomic_source_update(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), expected_manifest_hash=body.get("expected_manifest_hash"), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "runtime-migration-assistant"], ["runtime-migration-assistant"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "RUNTIME_MIGRATION_ASSISTANT")
        return 200, _ok(build_runtime_migration_assistant(project_id=str(body.get("project", "eidolon")), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "route-safety-harness"], ["route-safety-harness"]):
        return 200, _ok(build_route_safety_harness(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "dashboard-command-center"], ["release-dashboard-command-center"]):
        return 200, _ok(build_release_dashboard_command_center(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "clean-room-install-harness"], ["clean-room-install-harness"]):
        return 200, _ok(build_clean_room_install_harness(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), run_smoke_tier=str(body.get("tier") or "fast"), save=True))

    if parts in (["release", "verified-self-update-release-pipeline"], ["verified-self-update-release-pipeline"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "VERIFIED_SELF_UPDATE_RELEASE_PIPELINE")
        return 200, _ok(build_verified_self_update_release_pipeline(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), expected_manifest_hash=body.get("expected_manifest_hash"), confirm=confirm, dry_run=dry_run or not confirm, run_clean_room=_body_bool(body, "run_clean_room", False), save=True))

    if parts in (["release", "trial-upgrade-from-zip"], ["trial-upgrade-from-zip"], ["release", "trial-upgrade"]):
        return 200, _ok(build_trial_upgrade_harness(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), run_smoke_tier=str(body.get("tier") or "fast"), save=True))

    if parts in (["release", "backup-rollback-drill"], ["backup-rollback-drill"]):
        return 200, _ok(build_backup_rollback_drill(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "update-collision-detector"], ["update-collision-detector"]):
        return 200, _ok(build_update_collision_detector(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "version-registry-report"], ["version-registry-report"]):
        return 200, _ok(build_version_registry_report(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), dry_run=not _body_bool(body, "confirm", False), save=True))

    if parts in (["release", "release-provenance-report"], ["release-provenance-report"]):
        return 200, _ok(build_release_provenance_report(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "dashboard-upgrade-wizard-preview"], ["dashboard-upgrade-wizard-preview"]):
        return 200, _ok(build_dashboard_upgrade_wizard_preview(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "api-upgrade-wizard-preview"], ["api-upgrade-wizard-preview"]):
        return 200, _ok(build_api_upgrade_wizard_preview(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "staged-apply-drill"], ["staged-apply-drill"]):
        return 200, _ok(build_staged_apply_drill(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "real-apply-guard-rails"], ["real-apply-guard-rails"]):
        return 200, _ok(build_real_apply_guard_rails(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), expected_manifest_hash=body.get("expected_manifest_hash"), confirm_phrase=str(body.get("confirm_phrase") or ""), save=True))

    if parts in (["release", "real-apply-rollback-verification"], ["real-apply-rollback-verification"]):
        return 200, _ok(build_real_apply_rollback_verification(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "self-update-ux-polish"], ["self-update-ux-polish"]):
        return 200, _ok(build_self_update_ux_polish(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "v23-readiness-gate"], ["v23-readiness-gate"]):
        return 200, _ok(build_v23_readiness_gate(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), run_heavy=_body_bool(body, "run_heavy", False), save=True))

    if parts in (["release", "controlled-self-maintenance-loop"], ["controlled-self-maintenance-loop"], ["autonomy", "controlled-self-maintenance-loop"]):
        return 200, _ok(sm_v45.build_controlled_self_maintenance_loop(project_id=str(body.get("project", "eidolon")), goal=str(body.get("goal") or body.get("autonomy_goal") or "improve release dashboard performance"), save=True))

    if parts in (["release", "controlled-self-maintenance-work-queue"], ["controlled-self-maintenance-work-queue"], ["autonomy", "controlled-self-maintenance-work-queue"]):
        return 200, _ok(sm_v45.build_controlled_self_maintenance_work_queue(project_id=str(body.get("project", "eidolon")), goal=str(body.get("goal") or body.get("autonomy_goal") or "improve release dashboard performance"), save=True))

    if parts in (["release", "controlled-read-only-action-execution"], ["controlled-read-only-action-execution"], ["autonomy", "controlled-read-only-action-execution"]):
        return 200, _ok(sm_v45.build_controlled_read_only_action_execution(project_id=str(body.get("project", "eidolon")), command_key=str(body.get("command_key") or "version-import"), confirmation=str(body.get("confirmation") or body.get("confirm_phrase") or ""), execute=_body_bool(body, "execute", False) or _body_bool(body, "confirm", False), goal=str(body.get("goal") or body.get("autonomy_goal") or "improve release dashboard performance"), query=str(body.get("query") or body.get("q") or body.get("goal") or body.get("autonomy_goal") or ""), planning_scope=str(body.get("planning_scope") or body.get("scope") or "release_maintenance"), save=True))

    if parts in (["release", "evidence-gathering-maintenance-loop"], ["evidence-gathering-maintenance-loop"], ["autonomy", "evidence-gathering-maintenance-loop"]):
        return 200, _ok(sm_v45.build_evidence_gathering_maintenance_loop(project_id=str(body.get("project", "eidolon")), goal=str(body.get("goal") or body.get("autonomy_goal") or "improve release dashboard performance"), command_key=str(body.get("command_key") or "version-import"), confirmation=str(body.get("confirmation") or body.get("confirm_phrase") or ""), execute=_body_bool(body, "execute", False) or _body_bool(body, "confirm", False), save=True))

    if parts in (["release", "evidence-grounded-patch-proposal"], ["evidence-grounded-patch-proposal"], ["autonomy", "evidence-grounded-patch-proposal"]):
        return 200, _ok(sm_v45.build_evidence_grounded_patch_proposal_loop(project_id=str(body.get("project", "eidolon")), goal=str(body.get("goal") or body.get("autonomy_goal") or "improve release dashboard performance"), command_key=str(body.get("command_key") or "version-import"), save=True))


    if parts in (["release", "self-maintenance-proposal"], ["self-maintenance-proposal"]):
        return 200, _ok(build_self_maintenance_proposal_sandbox(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "build-patch-plan"], ["build-patch-plan"]):
        return 200, _ok(build_patch_plan_builder(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "generate-maintenance-patch"], ["generate-maintenance-patch"]):
        return 200, _ok(build_dry_run_patch_generator(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "patch-safety-audit"], ["patch-safety-audit"]):
        return 200, _ok(build_patch_safety_auditor(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "apply-maintenance-patch-to-temp"], ["apply-maintenance-patch-to-temp"]):
        return 200, _ok(build_apply_patch_to_temp_clone(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "maintenance-review-bundle"], ["maintenance-review-bundle"]):
        return 200, _ok(build_maintenance_review_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "approve-maintenance-bundle"], ["approve-maintenance-bundle"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        if confirm:
            _require_confirmation(body, "APPROVE_MAINTENANCE_BUNDLE")
        return 200, _ok(build_human_approval_binding(project_id=str(body.get("project", "eidolon")), bundle_hash=body.get("bundle_hash"), confirm=confirm, save=True))

    if parts in (["release", "real-maintenance-patch-apply"], ["real-maintenance-patch-apply"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "APPLY EXACT REVIEWED MAINTENANCE BUNDLE")
        return 200, _ok(build_real_maintenance_patch_apply(project_id=str(body.get("project", "eidolon")), bundle_hash=body.get("bundle_hash"), confirm_phrase=str(body.get("confirm_phrase") or body.get("confirmation") or ""), dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "improvement-candidate-scan"], ["improvement-candidate-scan"]):
        return 200, _ok(build_improvement_candidate_scan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-prioritizer"], ["candidate-prioritizer"]):
        return 200, _ok(build_candidate_prioritizer(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-to-proposal"], ["candidate-to-proposal"]):
        return 200, _ok(build_candidate_to_proposal_bridge(project_id=str(body.get("project", "eidolon")), candidate_id=body.get("candidate_id"), save=True))

    if parts in (["release", "maintenance-backlog"], ["maintenance-backlog"]):
        return 200, _ok(build_maintenance_backlog_registry(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-regression-detector"], ["candidate-regression-detector"]):
        return 200, _ok(build_candidate_regression_detector(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "release-memory-privacy"], ["release-memory-privacy"]):
        return 200, _ok(build_release_memory_privacy(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-verification-recipes"], ["candidate-verification-recipes"]):
        return 200, _ok(build_candidate_verification_recipes(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "assisted-improvement-cycle"], ["assisted-improvement-cycle"]):
        return 200, _ok(build_assisted_improvement_cycle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "semi-autonomous-maintenance-review"], ["semi-autonomous-maintenance-review"]):
        return 200, _ok(build_semi_autonomous_maintenance_review(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "set-maintenance-candidate-status"], ["set-maintenance-candidate-status"]):
        _require_confirmation(body, "ACCEPT_MAINTENANCE_CANDIDATE_STATUS")
        return 200, _ok({"status": "preview_saved", "message": "Candidate status mutation requires POST confirmation; runtime backlog writes remain outside source-only packages.", "candidate_id": body.get("candidate_id"), "new_status": body.get("status")})

    if parts in (["release", "post-apply-health-monitor"], ["post-apply-health-monitor"]):
        return 200, _ok(build_post_apply_health_monitor(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "controlled-maintenance-cycle"], ["controlled-maintenance-cycle"]):
        return 200, _ok(build_controlled_maintenance_cycle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "assisted-self-improvement-release"], ["assisted-self-improvement-release"]):
        return 200, _ok(build_assisted_self_improvement_release(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts == ["projects", "register"]:
        name = str(body.get("name") or body.get("project") or "Workspace Project")
        tests = body.get("test_commands", [])
        if isinstance(tests, str):
            tests = [tests]
        if not isinstance(tests, list):
            tests = []
        return 200, _ok(register_project(
            name=name,
            root=str(body.get("root") or "."),
            version=str(body.get("version") or "unknown"),
            language=str(body.get("language") or "unknown"),
            framework_type=str(body.get("framework_type") or body.get("framework") or "unknown"),
            readme_path=str(body.get("readme_path") or "README_NEXT_STEPS.md"),
            test_commands=[str(item) for item in tests],
            safe_command_profile=str(body.get("safe_command_profile") or "default_python"),
            project_id=str(body.get("id") or body.get("project_id") or "") or None,
        ))

    if parts == ["projects", "active"]:
        project_id = str(body.get("project_id") or body.get("id") or "")
        if not project_id:
            raise ApiError(400, "project_id is required.")
        return 200, _ok(set_active_workspace_project(project_id, operator_confirmed=True))

    if parts == ["workspace", "switch-project"]:
        project_id = str(body.get("project_id") or body.get("id") or "")
        if not project_id:
            raise ApiError(400, "project_id is required.")
        return 200, _ok(switch_workspace_project(project_id=project_id, force=_body_bool(body, "force", False), operator_confirmed=True))

    if parts == ["setup", "run"]:
        report = create_setup_report(save=True)
        return 201, _ok(report, message=f"Setup report saved: {report.get('id')}")

    if parts == ["onboarding", "run"]:
        refresh_setup = _body_bool(body, "refresh_setup", True)
        run = build_onboarding_run(save=True, refresh_setup=refresh_setup)
        return 201, _ok(run, message=f"Onboarding run saved: {run.get('id')} ({run.get('status')})")

    if parts == ["diagnostics", "run"]:
        include_full = _body_bool(body, "include_full", False) or _query_bool(query, "include_full", False)
        report = build_diagnostic_report(include_full=include_full)
        save_diagnostic_report(report)
        return 201, _ok(report, message=f"Diagnostic report saved: {report.get('id')}")

    if parts == ["watch", "run-once"]:
        use_ai = _body_bool(body, "use_ai", False)
        create_maintenance = _body_bool(body, "create_maintenance", True)
        create_session = _body_bool(body, "create_session", True)
        result = run_watch_once(use_ai=use_ai, create_maintenance=create_maintenance, create_session=create_session)
        report = load_watch_report(result.report_id) if result.report_id else None
        return 201, _ok({"result": result, "report": report}, message=result.text.splitlines()[0] if result.text else "Watch report saved.")

    if parts == ["watch", "run-loop"]:
        cycles = int(body.get("cycles", query.get("cycles", [2])[0]) or 2)
        interval = int(body.get("interval_seconds", body.get("interval", query.get("interval", [5])[0])) or 5)
        use_ai = _body_bool(body, "use_ai", False)
        create_maintenance = _body_bool(body, "create_maintenance", True)
        create_session = _body_bool(body, "create_session", True)
        loop = run_watch_loop(cycles=cycles, interval_seconds=interval, use_ai=use_ai, create_maintenance=create_maintenance, create_session=create_session)
        return 201, _ok(loop, message=f"Watch loop saved: {loop.get('id')}")

    if parts == ["session-plans", "run"]:
        use_ai = _body_bool(body, "use_ai", bool(get_setting("ai_reviews_enabled", True)))
        result = create_session_plan(use_ai=use_ai)
        if not result.ok:
            raise ApiError(400, result.error or "Session plan creation failed.", result)
        plan = load_session_plan(result.plan_id)
        return 201, _ok({"result": result, "plan": plan}, message=f"Session plan saved: {result.plan_id}")

    if parts == ["maintenance", "run"]:
        use_ai = _body_bool(body, "use_ai", False)
        result = run_maintenance_scan(use_ai=use_ai)
        if not result.ok:
            raise ApiError(400, result.error or "Maintenance scan failed.", result)
        scan = load_maintenance_scan(result.scan_id)
        return 201, _ok({"result": result, "scan": scan}, message=f"Maintenance scan saved: {result.scan_id}")

    if parts == ["dev-loops", "run"]:
        task_id = str(body.get("task_id") or "latest-ready")
        max_steps = int(body.get("max_steps", body.get("steps", 3)) or 3)
        dry_run = _body_bool(body, "dry_run", True)
        approve_apply = _body_bool(body, "approve_apply", False)
        apply_evaluation = _body_bool(body, "apply_evaluation", False)
        use_ai = _body_bool(body, "use_ai", False)
        loop = run_dev_loop(
            task_id=task_id,
            max_steps=max_steps,
            dry_run=dry_run,
            approve_apply=approve_apply,
            apply_evaluation=apply_evaluation,
            use_ai=use_ai,
        )
        return 201, _ok(loop, message=f"Dev loop saved: {loop.get('id')}")

    if len(parts) == 3 and parts[0] == "stable-loops" and parts[1] not in {"decisions", "followups"} and parts[2] in {"review", "approve-live", "reject", "archive", "restore", "run-approved-live", "refresh-audit", "operator-notes", "decision", "create-followups", "resolve-followups", "mark-followups-closed"}:
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        note = str(body.get("note") or "")
        if parts[2] == "review":
            status = str(body.get("status") or "reviewed")
            result = update_stable_loop_review(loop_id, status=status, note=note, reviewer="api")
        elif parts[2] == "approve-live":
            result = update_stable_loop_review(loop_id, status="approved_for_live", note=note or "Approved for live through local API.", reviewer="api")
        elif parts[2] == "reject":
            result = update_stable_loop_review(loop_id, status="rejected", note=note or "Rejected through local API.", reviewer="api")
        elif parts[2] == "archive":
            result = set_stable_loop_archived(loop_id, archived=True, note=note or "Archived through local API.", reviewer="api")
        elif parts[2] == "restore":
            result = set_stable_loop_archived(loop_id, archived=False, note=note or "Restored through local API.", reviewer="api")
        elif parts[2] == "refresh-audit":
            result = refresh_stable_loop_audit(loop_id)
        elif parts[2] == "operator-notes":
            result = add_stable_loop_operator_note(loop_id, note=note, reviewer="api")
        elif parts[2] == "decision":
            result = set_stable_loop_final_decision(
                loop_id,
                decision=str(body.get("decision") or body.get("final_decision") or "needs_review"),
                note=note,
                reviewer="api",
            )
        elif parts[2] == "create-followups":
            result = create_stable_loop_followup_tasks(
                loop_id=loop_id,
                dry_run=_body_bool(body, "dry_run", True),
                force=_body_bool(body, "force", False),
                reviewer="api",
            )
        elif parts[2] == "resolve-followups":
            result = resolve_stable_loop_followups(
                loop_id=loop_id,
                archive=_body_bool(body, "archive", False),
                force=_body_bool(body, "force", False),
                note=note or "Resolved through local API.",
                reviewer="api",
            )
        elif parts[2] == "mark-followups-closed":
            result = mark_stable_loop_followup_chain_closed(
                loop_id=loop_id,
                note=note or "Follow-up chain closure confirmed through local API.",
                reviewer="api",
                archive=_body_bool(body, "archive", False),
            )
        else:
            use_ai = body.get("use_ai")
            approve_work_execution = body.get("approve_work_execution")
            result = run_approved_stable_loop_live(
                loop_id,
                use_ai=None if use_ai is None else _body_bool(body, "use_ai", False),
                approve_work_execution=None if approve_work_execution is None else _body_bool(body, "approve_work_execution", False),
                note=note or "Live stable loop launched through local API review action.",
            )
        result_ok = result.get("ok") if isinstance(result, dict) else result.ok
        result_error = result.get("error", "") if isinstance(result, dict) else result.error
        result_message = result.get("message", "") if isinstance(result, dict) else result.message
        if not result_ok:
            raise ApiError(400, result_error or "Stable loop review action failed.", result)
        return 200, _ok(result, message=result_message)

    if len(parts) == 4 and parts[0] == "stable-loops" and parts[2] == "checklist":
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        result = update_stable_loop_check(
            loop_id,
            check_id=parts[3],
            status=str(body.get("status") or "done"),
            note=str(body.get("note") or ""),
            reviewer="api",
        )
        if not result.ok:
            raise ApiError(400, result.error or "Stable loop checklist action failed.", result)
        return 200, _ok(result, message=result.message)

    if len(parts) == 4 and parts[0] == "tasks" and parts[2] == "stable-loop-followup" and parts[3] == "resolve":
        result = resolve_task_stable_loop_followup(
            parts[1],
            archive=_body_bool(body, "archive", False),
            force=_body_bool(body, "force", False),
            note=str(body.get("note") or "Resolved through local API task endpoint."),
            reviewer="api",
        )
        if not result.ok:
            raise ApiError(400, result.error or "Stable-loop follow-up resolution failed.", result.to_dict())
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "followups", "completion", "cleanup"]:
        completion_filter = str(body.get("completion") or body.get("filter") or query.get("completion", ["cleanup_default"])[0])
        limit = int(body.get("limit") or query.get("limit", ["25"])[0] or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_archived = _body_bool(body, "include_archived", False)
        result = cleanup_stable_loop_followup_completions(
            completion_filter=completion_filter,
            limit=limit,
            dry_run=dry_run,
            include_archived=include_archived,
            reviewer="api",
        )
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "decisions", "cleanup"]:
        decision_filter = str(body.get("decision") or body.get("filter") or query.get("decision", ["cleanup_default"])[0])
        limit = int(body.get("limit") or query.get("limit", ["25"])[0] or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_live = _body_bool(body, "include_live", True)
        result = cleanup_stable_loop_decision_history(
            decision_filter=decision_filter,
            limit=limit,
            dry_run=dry_run,
            include_live=include_live,
        )
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "decisions", "create-followups"]:
        decision_filter = str(body.get("decision") or body.get("filter") or query.get("decision", ["action_required"])[0])
        limit = int(body.get("limit") or query.get("limit", ["25"])[0] or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_live = _body_bool(body, "include_live", True)
        include_archived = _body_bool(body, "include_archived", False)
        result = create_stable_loop_followups_for_decisions(
            decision_filter=decision_filter,
            dry_run=dry_run,
            include_archived=include_archived,
            include_live=include_live,
            limit=limit,
            force=_body_bool(body, "force", False),
            reviewer="api",
        )
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "history", "cleanup"]:
        review_filter = str(body.get("review") or body.get("status") or "cleanup_default")
        limit = int(body.get("limit", 25) or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_live = _body_bool(body, "include_live", True)
        result = cleanup_stable_loop_history(
            review_filter=review_filter,
            limit=limit,
            dry_run=dry_run,
            include_live=include_live,
            reviewer="api",
        )
        return 200, _ok(result, message=result.get("message", "Stable loop history cleanup complete."))

    if parts == ["stable-loops", "run"]:
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        max_steps = int(body.get("max_steps", body.get("steps", 1)) or 1)
        live = _body_bool(body, "live", False)
        use_ai = _body_bool(body, "use_ai", True)
        approve_work_execution = _body_bool(body, "approve_work_execution", False)
        seed_if_empty = _body_bool(body, "seed_if_empty", True)
        auto_followups = _body_bool(body, "auto_create_patch_followups", True)
        auto_request_approvals = _body_bool(body, "auto_request_approvals", True)
        auto_retry_recovery = _body_bool(body, "auto_retry_recovery", False)
        bypass_closure_guardrails = _body_bool(body, "bypass_closure_guardrails", False)
        result = run_stable_supervised_loop(
            project_id=project_id,
            max_steps=max_steps,
            live=live,
            use_ai=use_ai,
            approve_work_execution=approve_work_execution,
            seed_if_empty=seed_if_empty,
            auto_create_patch_followups=auto_followups,
            auto_request_approvals=auto_request_approvals,
            auto_retry_recovery=auto_retry_recovery,
            bypass_closure_guardrails=bypass_closure_guardrails,
        )
        loop = load_stable_loop(result.loop_id)
        return 201, _ok({"result": result, "loop": loop}, message=result.message)

    if parts == ["work-cycles", "run"]:
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        max_steps = int(body.get("max_steps", body.get("steps", 1)) or 1)
        dry_run = _body_bool(body, "dry_run", True)
        use_ai = _body_bool(body, "use_ai", True)
        approve_work_execution = _body_bool(body, "approve_work_execution", False)
        seed_if_empty = _body_bool(body, "seed_if_empty", True)
        auto_followups = _body_bool(body, "auto_create_patch_followups", True)
        auto_request_approvals = _body_bool(body, "auto_request_approvals", True)
        auto_retry_recovery = _body_bool(body, "auto_retry_recovery", False)
        result = run_supervised_work_cycle(
            project_id=project_id,
            max_steps=max_steps,
            dry_run=dry_run,
            use_ai=use_ai,
            approve_work_execution=approve_work_execution,
            seed_if_empty=seed_if_empty,
            auto_create_patch_followups=auto_followups,
            auto_request_approvals=auto_request_approvals,
            auto_retry_recovery=auto_retry_recovery,
        )
        cycle = load_work_cycle(result.cycle_id)
        return 201, _ok({"result": result, "cycle": cycle}, message=result.message)

    if parts and parts[0] == "notifications":
        if parts == ["notifications", "clear-dismissed"]:
            count = clear_dismissed_notifications()
            return 200, _ok({"cleared": count}, message=f"Cleared {count} dismissed notification(s).")
        if len(parts) == 3 and parts[2] in {"read", "dismiss"}:
            status = "read" if parts[2] == "read" else "dismissed"
            note = body.get("note", f"Marked {status} through local API.")
            result = update_notification_status(parts[1], status, note=note)
            if not result.get("ok"):
                raise ApiError(404, str(result.get("error", "Notification update failed.")), result)
            return 200, _ok(result, message=f"Notification marked {status}.")

    if parts and parts[0] == "approvals" and len(parts) == 3:
        approval_id = parts[1]
        if parts[2] == "approve":
            dry_run = _body_bool(body, "dry_run", False)
            result = approve_approval(approval_id, dry_run=dry_run)
            if not result.get("ok"):
                raise ApiError(400, str(result.get("error", "Approval failed.")), result)
            return 200, _ok(result, message=str(result.get("message") or result.get("status") or "Approval handled."))
        if parts[2] == "reject":
            note = str(body.get("note", "Rejected through local API."))
            result = reject_approval(approval_id, note=note)
            if not result.get("ok"):
                raise ApiError(400, str(result.get("error", "Approval reject failed.")), result)
            return 200, _ok(result, message=f"Approval rejected: {result.get('id', approval_id)}")

    if parts == ["chat-actions"]:
        message = str(body.get("message") or body.get("request") or "").strip()
        if not message:
            raise ApiError(400, "message is required.")
        action = propose_chat_action(message, save=True)
        return 201, _ok(action, message=f"Chat action saved: {action.get('id')}")

    if parts and parts[0] == "chat-actions" and len(parts) == 3:
        action_id = parts[1]
        if parts[2] in {"dry-run", "execute"}:
            dry_run = parts[2] == "dry-run" or _body_bool(body, "dry_run", False)
            result = execute_chat_action(
                action_id,
                dry_run=dry_run,
                timeout_seconds=180 if not dry_run else None,
                retry=_body_bool(body, "retry", False),
                claimant="api",
            )
            if not result.ok:
                raise ApiError(400, result.error or result.message or "Chat action failed.", result)
            saved = load_chat_action(result.chat_action_id)
            return 200, _ok({"result": result, "chat_action": saved}, message=result.message)

    if parts == ["tasks", "request-approvals"]:
        stage = normalize_lifecycle_stage_filter(str(body.get("stage") or "approval_required"))
        project_id = str(body.get("project_id") or body.get("project") or "").strip()
        dry_run = _body_bool(body, "dry_run", False)
        use_ai = _body_bool(body, "use_ai", True)
        force = _body_bool(body, "force", False)
        reason = str(body.get("reason") or "Batch approval request from lifecycle filter.")
        rows = list_task_lifecycles(project=project_id, include_closed=False, stage_filter=stage)
        results = []
        created = 0
        failed = 0
        for row in rows:
            task_id = str(row.get("task_id") or "").strip()
            if not task_id:
                continue
            result = request_task_work_approval(task_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            result_data = _to_jsonable(result)
            result_data["stage"] = row.get("stage")
            results.append(result_data)
            if result.ok:
                created += 1
            else:
                failed += 1
        return 200 if dry_run else 201, _ok({
            "stage": stage,
            "dry_run": dry_run,
            "matched": len(rows),
            "created_or_valid": created,
            "failed": failed,
            "results": results,
        }, message=f"Handled approval requests for {created} of {len(rows)} task(s).")


    if parts in (["release", "approve-publish"], ["release", "write-publish-approval"], ["approve-publish"]):
        project_id = str(body.get("project") or body.get("project_id") or "eidolon")
        dry_run = _body_bool(body, "dry_run", True)
        report = build_write_publish_approval(
            project_id=project_id,
            package_name=str(body.get("package_name") or _package_name()),
            zip_path=str(body.get("release_zip_path") or body.get("zip_path") or "") or None,
            confirmation=str(body.get("confirmation") or body.get("release_confirm_phrase") or ""),
            approver_label=str(body.get("approver_label") or "local-operator"),
            signature_path=str(body.get("signature_path") or "") or None,
            public_key_path=str(body.get("public_key_path") or "") or None,
            trusted_fingerprint=str(body.get("trusted_fingerprint") or "") or None,
            dry_run=dry_run,
            save=True,
        )
        if not dry_run and not report.get("publish_approved"):
            raise ApiError(400, "Publish approval write was blocked.", report)
        return (200 if dry_run else 201), _ok(report, message=report.get("message", "Publish approval write handled."))


    if parts in (["release", "apply-reviewed-patch"], ["autonomy", "apply-reviewed-patch"], ["apply-reviewed-patch"]):
        proposal_id = str(body.get("proposal_id") or "").strip() or None
        confirmation = str(body.get("confirmation") or body.get("release_confirm_phrase") or "").strip() or None
        goal = str(body.get("goal") or "").strip() or None
        dry_run = _body_bool(body, "dry_run", True)
        approve = _body_bool(body, "approve_source_apply", False) and not dry_run
        report = build_apply_reviewed_patch(project_id=str(body.get("project") or "eidolon"), proposal_id=proposal_id, goal=goal, confirmation=confirmation, approve=approve, dry_run=dry_run, save=True)
        if not dry_run and not report.get("source_apply_written"):
            raise ApiError(400, "Reviewed patch source apply was blocked.", report)
        return (200 if dry_run else 201), _ok(report, message=report.get("message", "Reviewed patch source apply handled."))

    if parts in (["release", "rollback-applied-patch"], ["autonomy", "rollback-applied-patch"], ["rollback-applied-patch"]):
        proposal_id = str(body.get("proposal_id") or "").strip() or None
        confirmation = str(body.get("confirmation") or body.get("release_confirm_phrase") or "").strip() or None
        goal = str(body.get("goal") or "").strip() or None
        dry_run = _body_bool(body, "dry_run", True)
        approve = _body_bool(body, "approve_source_rollback", False) and not dry_run
        report = build_rollback_applied_patch(project_id=str(body.get("project") or "eidolon"), proposal_id=proposal_id, goal=goal, confirmation=confirmation, approve=approve, dry_run=dry_run, save=True)
        if not dry_run and not report.get("source_rollback_written"):
            raise ApiError(400, "Applied patch source rollback was blocked.", report)
        return (200 if dry_run else 201), _ok(report, message=report.get("message", "Applied patch rollback handled."))

    if parts in (["release", "revoke-publish-approval"], ["release", "write-approval-revocation"], ["revoke-publish-approval"]):
        project_id = str(body.get("project") or body.get("project_id") or "eidolon")
        dry_run = _body_bool(body, "dry_run", True)
        approval_record_id = str(body.get("approval_record_id") or "").strip()
        if not approval_record_id:
            raise ApiError(400, "approval_record_id is required for publish approval revocation writes.")
        report = build_write_approval_revocation(
            project_id=project_id,
            approval_record_id=approval_record_id,
            confirmation=str(body.get("confirmation") or body.get("release_confirm_phrase") or ""),
            revocation_reason=str(body.get("reason") or body.get("revocation_reason") or "superseded release"),
            revoker_label=str(body.get("revoker_label") or "local-operator"),
            dry_run=dry_run,
            approve=not dry_run,
            save=True,
        )
        if not dry_run and not report.get("revocation_written"):
            raise ApiError(400, "Publish approval revocation write was blocked.", report)
        return (200 if dry_run else 201), _ok(report, message=report.get("message", "Publish approval revocation handled."))

    if parts == ["tasks", "patch-request"]:
        target_file = str(body.get("target_file") or body.get("file") or "").strip()
        request = str(body.get("request") or body.get("description") or body.get("message") or "").strip()
        if not target_file:
            raise ApiError(400, "target_file is required.")
        if not request:
            raise ApiError(400, "request is required.")
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        task = create_patch_task(
            target_file=target_file,
            request=request,
            project_id=str(body.get("project_id") or body.get("project") or "eidolon"),
            priority=int(body.get("priority") or 7),
            risk=str(body.get("risk") or "low"),
            source="dashboard" if str(body.get("source") or "") == "dashboard" else "system",
            requires_approval=requires_approval,
        )
        return 201, _ok(task, message=f"Patch task created: {task.get('id')}")

    if parts == ["work-queue", "patch-request"]:
        target_file = str(body.get("target_file") or body.get("file") or "").strip()
        request = str(body.get("request") or body.get("description") or body.get("message") or "").strip()
        if not target_file:
            raise ApiError(400, "target_file is required.")
        if not request:
            raise ApiError(400, "request is required.")
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        item = create_patch_work_item(
            target_file=target_file,
            request=request,
            project_id=str(body.get("project_id") or body.get("project") or "eidolon"),
            priority=int(body.get("priority") or 7),
            risk=str(body.get("risk") or "low"),
            source="dashboard" if str(body.get("source") or "") == "dashboard" else "system",
            requires_approval=requires_approval,
        )
        return 201, _ok(item, message=f"Patch task created through legacy alias: {item.id}")

    if parts == ["work-queue"]:
        title = str(body.get("title") or "").strip()
        if not title:
            raise ApiError(400, "title is required.")
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        item = add_work_item(
            title=title,
            description=str(body.get("description") or ""),
            project_id=str(body.get("project_id") or body.get("project") or "default"),
            priority=int(body.get("priority") or 5),
            risk=str(body.get("risk") or "low"),
            source="dashboard" if str(body.get("source") or "") == "dashboard" else "system",
            requires_approval=requires_approval,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
        )
        return 201, _ok(item, message=f"Task created through legacy alias: {item.id}")

    if parts and parts[0] == "tasks" and len(parts) == 3 and parts[2] == "suggest-patch":
        task_id = parts[1]
        dry_run = _body_bool(body, "dry_run", False)
        use_ai = _body_bool(body, "use_ai", True)
        result = suggest_patch_for_task(task_id, use_ai=use_ai, dry_run=dry_run)
        if not result.ok:
            raise ApiError(400, result.error or "Patch suggestion from task failed.", result)
        patch = load_patch_proposal(result.patch_id) if result.patch_id else None
        return 200, _ok({"result": result, "patch": patch}, message=result.message or "Patch suggestion handled.")

    if parts and parts[0] == "tasks" and len(parts) == 3:
        task_id = parts[1]
        operation = parts[2]
        if task_id == "next" and operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            result = execute_next_task_work(project_id=project_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if task_id == "next" and operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            reason = str(body.get("reason") or "")
            result = request_next_task_work_approval(project_id=project_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            reason = str(body.get("reason") or "")
            result = request_task_work_approval(task_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            result = execute_task_work_item(task_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if operation == "ready-for-retry":
            note = str(body.get("note") or "Marked ready for retry through local API.")
            result = mark_task_ready_for_retry(task_id, note=note)
            if not result.ok:
                raise ApiError(400, result.error or "Could not mark task ready for retry.", result)
            return 200, _ok(result, message=result.message)
        if operation == "retry":
            dry_run = _body_bool(body, "dry_run", True)
            use_ai = _body_bool(body, "use_ai", True)
            allow_approval_required = _body_bool(body, "allow_approval_required", False)
            result = retry_task_work(task_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai)
            if not result.ok and not dry_run:
                raise ApiError(400, result.error or "Task retry failed.", result)
            return 200, _ok(result, message=result.message or result.error or "Task retry handled.")
        if operation == "done":
            result_text = str(body.get("result") or "Marked done through local API.")
            mutation = update_task_fields(task_id, status="done", result=result_text)
            if not mutation.ok:
                raise ApiError(404, mutation.error or f"Task not found: {task_id}", mutation)
            return 200, _ok(mutation.task, message=f"Task marked done: {task_id}")
        if operation == "block":
            reason = str(body.get("reason") or "Blocked through local API.")
            mutation = update_task_fields(task_id, status="blocked", blocked_reason=reason)
            if not mutation.ok:
                raise ApiError(404, mutation.error or f"Task not found: {task_id}", mutation)
            return 200, _ok(mutation.task, message=f"Task blocked: {task_id}")
        if operation == "cancel":
            result_text = str(body.get("result") or "Cancelled through local API.")
            mutation = update_task_fields(task_id, status="cancelled", result=result_text)
            if not mutation.ok:
                raise ApiError(404, mutation.error or f"Task not found: {task_id}", mutation)
            return 200, _ok(mutation.task, message=f"Task cancelled: {task_id}")

    if parts and parts[0] == "work-queue" and len(parts) == 3:
        item_id = parts[1]
        operation = parts[2]
        if item_id == "next" and operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            result = execute_next_task_work(project_id=project_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if item_id == "next" and operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            reason = str(body.get("reason") or "")
            result = request_next_task_work_approval(project_id=project_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            reason = str(body.get("reason") or "")
            result = request_task_work_approval(item_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation == "suggest-patch":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            result = suggest_patch_for_work_item(item_id, use_ai=use_ai, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Patch suggestion from task failed.", result)
            patch = load_patch_proposal(result.patch_id) if result.patch_id else None
            return 200, _ok({"result": result, "patch": patch}, message=result.message or "Patch suggestion handled.")
        if operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            result = execute_task_work_item(item_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if operation == "done":
            item = update_work_item(item_id, status="done", result=str(body.get("result") or "Marked done through local API."))
            if not item:
                raise ApiError(404, f"Task not found: {item_id}")
            return 200, _ok(item, message=f"Task marked done through legacy alias: {item_id}")
        if operation == "block":
            reason = str(body.get("reason") or "Blocked through local API.")
            item = update_work_item(item_id, status="blocked", blocked_reason=reason)
            if not item:
                raise ApiError(404, f"Task not found: {item_id}")
            return 200, _ok(item, message=f"Task blocked through legacy alias: {item_id}")
        if operation == "cancel":
            item = update_work_item(item_id, status="cancelled", result=str(body.get("result") or "Cancelled through local API."))
            if not item:
                raise ApiError(404, f"Task not found: {item_id}")
            return 200, _ok(item, message=f"Task cancelled through legacy alias: {item_id}")

    if parts == ["tasks"]:
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        result = add_task(
            title=str(body.get("title") or ""),
            description=str(body.get("description") or ""),
            priority=str(body.get("priority") or "medium"),
            status=str(body.get("status") or "planned"),
            project=str(body.get("project_id") or body.get("project") or ""),
            command=str(body.get("command") or ""),
            next_action=str(body.get("next_action") or ""),
            linked_goal=str(body.get("linked_goal") or ""),
            risk=str(body.get("risk") or "low"),
            source="local_api",
            requires_approval=requires_approval,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
        )
        if not result.ok:
            raise ApiError(400, result.error or "Task creation failed.", result)
        return 201, _ok(result.task, message=result.message)

    if parts == ["goals"]:
        result = add_goal(
            title=str(body.get("title") or ""),
            description=str(body.get("description") or ""),
            priority=str(body.get("priority") or "medium"),
            status=str(body.get("status") or "planned"),
            next_action=str(body.get("next_action") or ""),
        )
        if not result.ok:
            raise ApiError(400, result.error or "Goal creation failed.", result)
        return 201, _ok(result.goal, message=result.message)

    if parts and parts[0] == "patches" and len(parts) == 3 and parts[2] == "create-task-followups":
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        result = create_patch_followup_tasks(parts[1], project_id=project_id)
        if not result.ok:
            raise ApiError(400, result.error or "Could not create patch follow-up tasks.", result)
        return 201, _ok(result, message=result.message)

    if parts and parts[0] == "patches" and len(parts) == 3 and parts[2] == "create-followups":
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        result = create_patch_followup_items(parts[1], project_id=project_id)
        if not result.ok:
            raise ApiError(400, result.error or "Could not create patch follow-up tasks.", result)
        return 201, _ok(result, message=result.message)

    if parts == ["patches", "suggest"]:
        target_file = str(body.get("target_file") or body.get("file") or "").strip()
        request = str(body.get("request") or body.get("message") or "").strip()
        use_ai = _body_bool(body, "use_ai", True)
        if not target_file:
            raise ApiError(400, "target_file is required.")
        if not request:
            raise ApiError(400, "request is required.")
        result = suggest_patch(target_file, request, use_ai=use_ai)
        if not result.ok:
            raise ApiError(400, result.error or "Patch suggestion failed.", result)
        patch = load_patch_proposal(result.patch_id)
        return 201, _ok({"result": result, "patch": patch}, message=f"Patch proposal saved: {result.patch_id}")

    if parts == ["dashboard-chat"]:
        message = str(body.get("message") or "").strip()
        if not message:
            raise ApiError(400, "message is required.")
        use_ai = _body_bool(body, "use_ai", bool(get_setting("dashboard_chat_use_ai_default", True)))
        session_id = str(body.get("session_id") or "").strip()
        turn = create_dashboard_chat_turn(message, use_ai=use_ai, session_id=session_id)
        return 201, _ok(turn, message=f"Dashboard chat turn saved: {turn.get('id')}")

    raise ApiError(404, f"Unknown API endpoint: /api/{'/'.join(parts)}")


def dispatch_api(method: str, path: str, query: dict[str, list[str]] | None = None, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    try:
        if method.upper() == "GET":
            return handle_api_get(path, query=query)
        if method.upper() == "POST":
            return handle_api_post(path, body=body, query=query)
        raise ApiError(405, f"Unsupported API method: {method}")
    except ApiError as error:
        return error.status, _error(error.status, error.message, error.details)
    except Exception as error:
        details = traceback.format_exc() if os.environ.get("EIDOLON_API_DEBUG_TRACEBACKS") == "1" else {"error_type": type(error).__name__}
        return 500, _error(500, "API route crashed.", details)




from api_http_runtime import ApiRuntimeDependencies, build_api_handler_class, serve_api

EidolonApiHandler = build_api_handler_class(
    ApiRuntimeDependencies(
        # Keep the historical api_server monkeypatch surface late-bound.
        to_jsonable=lambda value: _to_jsonable(value),
        ok=lambda *args, **kwargs: _ok(*args, **kwargs),
        error=lambda *args, **kwargs: _error(*args, **kwargs),
        dispatch_api=lambda *args, **kwargs: dispatch_api(*args, **kwargs),
        parse_request_body=lambda body, content_type="": parse_request_body(body, content_type),
        api_error_type=ApiError,
        cancel_conversation_operation=lambda operation_id: cancel_conversation_operation(operation_id),
        stream_dashboard_chat_turn=lambda *args, **kwargs: stream_dashboard_chat_turn(*args, **kwargs),
    )
)


def run_api_server(host: str | None = None, port: int | None = None) -> None:
    """Run the extracted HTTP transport with the manual dispatch surface."""
    return serve_api(
        host=host,
        port=port,
        handler_class=EidolonApiHandler,
        load_settings=load_settings,
    )


# v215.1-v220.0 simulation/foresight API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/internal-simulation-packet/layer /api/foresight-branch-comparison/layer /api/pre-change-consequence-modeling/layer /api/expectation-reality-check/layer /api/simulation-foresight-audit/layer

# v220.1-v225.0 learning curriculum API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/learning-objective-map/layer /api/practice-task-design/layer /api/capability-calibration/layer /api/skill-gap-remediation-planner/layer /api/learning-curriculum-audit/layer

# v225.1-v230.0 knowledge/belief API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/knowledge-claim-ledger/schema /api/belief-candidate-review/schema /api/contradiction-staleness-intelligence/schema /api/project-knowledge-map/schema /api/knowledge-organization-audit/layer operator-governed-knowledge-and-belief-organization-layer-v1

# v230.1-v235.0 local model workbench API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/local-model-inventory/schema /api/model-evaluation-plan/schema /api/model-output-comparison/schema /api/cognitive-workbench-routing/schema /api/local-model-workbench-audit/layer operator-governed-local-model-evaluation-and-cognitive-workbench-layer-v1
# v245.1-v250.0 model-assisted patch draft assembly API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/model-assisted-patch-draft/layer /api/file-impact-documentation-planner/layer /api/smoke-verification-suggestions/layer /api/sandbox-preparation-packet/layer /api/patch-draft-assembly-audit/layer
# v240.1-v245.0 model-assisted patch review API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/model-assisted-patch-critique/layer /api/multi-model-review-synthesis/layer /api/patch-risk-remediation-synthesis/layer /api/model-review-quality-calibration/layer /api/model-assisted-patch-review-audit/layer
# v235.1-v240.0 local model invocation sandbox API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/local-model-invocation-consent/schema /api/model-evaluation-run-ledger/schema /api/multi-model-output-triage/schema /api/model-reliability-profile-candidates/schema /api/local-model-invocation-sandbox-audit/layer operator-approved-local-model-invocation-sandbox-v1

# v250.1-v255.0 patch execution packet bridge API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/draft-to-execution-packet/layer /api/patch-diff-preview-planner/layer /api/execution-approval-scope/layer /api/verification-rollback-packet/layer /api/patch-execution-packet-audit/layer operator-governed-patch-execution-packet-bridge-v1

# v255.1-v260.0 approved application prep API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/application-prep-intake/layer /api/source-edit-application-plan/layer /api/documentation-application-plan/layer /api/final-application-governance-gate/layer /api/application-prep-integration-audit/layer operator-governed-approved-execution-packet-application-prep-v1

# v260.1-v265.0 structural stabilization API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/structural-inventory/layer /api/runtime-registry-prep/layer /api/dashboard-stabilization-audit/layer /api/dispatch-stabilization/layer /api/structural-stabilization-audit/layer operator-governed-structural-stabilization-and-runtime-modularization-v1

# v265.1-v270.0 module extraction API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/runtime-registry/layer /api/governance-report-builder-audit/layer /api/dashboard-registry-integration/layer /api/runtime-dispatch-registry-audit/layer /api/module-extraction-audit/layer operator-governed-runtime-module-extraction-v1

# v270.1-v275.0 self-maintenance decomposition API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/self-maintenance-extraction-map/layer /api/package-version-integrity/layer /api/surface-parity-audit/layer /api/verification-planning-audit/layer /api/self-maintenance-decomposition-audit/layer operator-governed-self-maintenance-decomposition-v1

# v275.1-v280.0 dashboard/API/CLI modularization API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/dashboard-extraction-map/layer /api/dashboard-component-audit/layer /api/api-surface-audit/layer /api/cli-surface-audit/layer /api/interface-modularization-audit/layer operator-governed-dashboard-api-cli-modularization-v1 dashboard_components.py api_surface.py cli_surface.py

# v280.1-v285.0 application execution refinement API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/approved-application-binding/layer /api/operator-execution-checklist/layer /api/post-application-result-review/layer /api/application-outcome-learning/layer /api/application-execution-refinement-audit/layer operator-approved-application-execution-refinement-v1 application_execution_refinement.py

# v285.1-v290.0 rollback and recovery intelligence API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/rollback-scope-binding/layer /api/failure-damage-map/layer /api/recovery-checklist/layer /api/post-recovery-review/layer /api/rollback-recovery-audit/layer operator-governed-rollback-and-recovery-intelligence-v1 rollback_recovery.py

# v290.1-v295.0 memory candidate governance API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/memory-candidate-intake/layer /api/memory-candidate-classification/layer /api/memory-approval-packet/layer /api/memory-contradiction-review/layer /api/memory-governance-audit/layer operator-governed-memory-candidate-governance-upgrade-v1 memory_governance.py

# v295.1-v300.0 continuity kernel API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/continuity-state-intake/layer /api/self-model-snapshot-v2/layer /api/purpose-coherence-review/layer /api/supervised-growth-priorities/layer /api/continuity-kernel-v2-audit/layer local-artificial-mind-continuity-kernel-v2 continuity_kernel.py
# v300.1-v305.0 identity/personality/coherence expression API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/identity-expression-boundary/layer /api/personality-trait-ledger/layer /api/voice-affect-style-map/layer /api/coherence-expression-review/layer /api/identity-personality-coherence-audit/layer operator-governed-identity-personality-coherence-expression-layer-v1 identity_expression.py risky_request_classifier
# v305.1-v310.0 behavioral expression preview and runtime health API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/dashboard-route-health/layer /api/runtime-test-visibility/layer /api/behavioral-expression-preview/layer /api/style-delta-staging/layer /api/expression-runtime-health-audit/layer operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1

# v310.1-v315.0 conversational expression sandbox API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-profile-packets/layer /api/conversation-scenario-sandbox/layer /api/expression-regression-review/layer /api/expression-operator-review-console/layer /api/conversational-expression-sandbox-audit/layer operator-governed-conversational-expression-sandbox-v1 conversational_expression_sandbox.py

# v315.1-v320.0 expression application bridge API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-approval-criteria/layer /api/expression-live-surface-impact-map/layer /api/expression-implementation-packet-draft/layer /api/expression-rollback-reversion-plan/layer /api/expression-application-bridge-audit/layer operator-governed-conversational-expression-application-bridge-v1 expression_application_bridge.py
# v320.1-v325.0 expression patch dry-run API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-patch-candidates/layer /api/expression-sandbox-diff-preview/layer /api/expression-dry-run-verification-plan/layer /api/expression-dry-run-review-packet/layer /api/expression-patch-dry-run-audit/layer operator-governed-expression-patch-dry-run-sandbox-v1 expression_patch_dry_run.py

# v325.1-v330.0 expression sandbox trial harness API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-sandbox-trial-packet/layer /api/expression-sandbox-workspace-plan/layer /api/expression-sandbox-verification-matrix/layer /api/expression-sandbox-result-review-prep/layer /api/expression-sandbox-trial-harness-audit/layer operator-governed-expression-patch-sandbox-trial-harness-v1 expression_sandbox_trial_harness.py

# v330.1-v335.0 expression sandbox execution bridge API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-sandbox-execution-approval-gate/layer /api/expression-sandbox-workspace-execution-packet/layer /api/expression-sandbox-patch-bundle-packet/layer /api/expression-sandbox-verification-command-packet/layer /api/expression-sandbox-execution-packet-bridge-audit/layer operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 expression_sandbox_execution_bridge.py

# v335.1-v340.0 expression sandbox result intake API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-sandbox-trial-evidence-intake/layer /api/expression-sandbox-outcome-comparison/layer /api/expression-sandbox-regression-result-review/layer /api/expression-sandbox-revision-recommendations/layer /api/expression-sandbox-promotion-review-prep/layer operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1 expression_sandbox_result_intake.py

# v340.1-v345.0 expression promotion packet API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-promotion-evidence-binder/layer /api/expression-live-promotion-scope-risk/layer /api/expression-promotion-verification-rollback/layer /api/expression-promotion-decision-packet/layer /api/expression-promotion-packet-assembly-audit/layer operator-governed-expression-promotion-packet-assembly-layer-v1 expression_promotion_packet.py

# v345.1-v350.0 expression live application packet API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-live-application-eligibility-gate/layer /api/expression-live-source-change-manifest/layer /api/expression-live-patch-instruction-packet/layer /api/expression-live-verification-rollback-packet/layer /api/expression-live-application-packet-audit/layer operator-governed-expression-live-application-packet-drafting-layer-v1 expression_live_application_packet.py

# v350.1-v355.0 expression live application execution prep API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/expression-live-execution-approval-intake/layer /api/expression-live-source-transaction-preimage/layer /api/expression-live-manual-execution-checklist/layer /api/expression-live-rollback-reversion-packet/layer /api/expression-live-execution-prep-audit/layer operator-governed-expression-live-application-execution-prep-v1 expression_live_execution_prep.py
# v355.1-v360.0 minimal live expression application API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/minimal-live-expression-change-candidate/layer /api/minimal-live-expression-approval-lock/layer /api/minimal-live-expression-patch-transaction/layer /api/minimal-live-expression-application-harness/layer /api/minimal-live-expression-application-audit/layer operator-approved-minimal-live-expression-application-audit-v1 minimal_live_expression_application.py candidate_selection_applies_change=False approval_lock_self_approves=False transaction_builder_writes_files=False application_harness_executes_without_confirmation=False application_audit_publishes_release=False

# v360.1-v365.0 self-maintenance refactor API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/self-maintenance-gate-registry/layer /api/self-maintenance-version-expectations/layer /api/governed-surface-metadata-registry/layer /api/smoke-check-legacy-gate-registry/layer /api/self-maintenance-refactor-audit/layer operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1 self_maintenance_refactor_registry.py refactor_registry_writes_files=False refactor_registry_executes_smoke=False centralized_version_expectations_required=True

# v365.1-v370.0 minimal live change replay API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/minimal-live-change-replay-packet/layer /api/minimal-live-change-expected-actual-comparison/layer /api/minimal-live-change-regression-drift-detector/layer /api/minimal-live-change-recovery-recommendation/layer /api/minimal-live-change-replay-regression-audit/layer operator-governed-minimal-live-change-replay-and-regression-hardening-v1 minimal_live_change_replay.py replay_packet_applies_change=False expected_actual_writes_files=False recovery_recommendation_executes_rollback=False

# v370.1-v375.0 modular extraction API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/self-maintenance-module-extraction-plan/layer /api/self-maintenance-version-package-gates/layer /api/self-maintenance-surface-gates/layer /api/self-maintenance-governance-gates/layer /api/self-maintenance-modular-extraction-audit/layer operator-governed-self-maintenance-modular-extraction-v1 self_maintenance_modular_extraction.py self_maintenance_version_package_gates.py self_maintenance_surface_gates.py self_maintenance_governance_gates.py modular_extraction_applies_live_patches=False

# v375.1-v380.0 live change application trial API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/live-change-transaction-narrowing/layer /api/live-change-approval-execution-lock/layer /api/live-change-real-patch-trial-plan/layer /api/live-change-operator-confirmed-application-trial/layer /api/live-change-application-trial-audit/layer operator-governed-live-change-application-trial-audit-v1 live_change_application_trial.py transaction_narrowing_applies_patch=False approval_execution_lock_self_approves=False trial_plan_writes_files=False application_trial_runs_without_confirmation=False application_trial_continues_automatically=False
# v380.1-v385.0 live patch trial closure API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/live-patch-trial-result-intake/layer /api/live-patch-applied-diff-evidence/layer /api/live-patch-approval-burnout/layer /api/live-patch-post-trial-regression-review/layer /api/live-patch-trial-closure-audit/layer operator-governed-live-patch-trial-closure-audit-v1 live_patch_trial_closure.py result_intake_reruns_commands=False diff_evidence_edits_source=False approval_burnout_reuses_approval=False post_trial_review_executes_rollback=False closure_audit_applies_another_patch=False

# v385.1-v390.0 second live patch trial API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/second-minimal-live-patch-candidate/layer /api/registry-driven-live-patch-approval-validation/layer /api/registry-driven-live-patch-transaction-lock/layer /api/second-live-patch-application-harness/layer /api/second-live-patch-trial-registry-audit/layer operator-governed-second-live-patch-trial-registry-audit-v1 second_live_patch_trial.py candidate_selection_applies_patch=False approval_validation_reuses_approval=False transaction_lock_writes_files=False application_harness_runs_without_confirmation=False registry_audit_applies_patch=False
# v390.1-v395.0 live patch history memory candidate API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/live-patch-trial-history-ledger/layer /api/operator-live-patch-decision-patterns/layer /api/live-patch-supervised-lesson-candidates/layer /api/live-patch-memory-candidate-governance/layer /api/live-patch-history-memory-candidate-audit/layer operator-governed-live-patch-history-and-memory-candidate-audit-v1 live_patch_history_memory_candidates.py history_ledger_treats_history_as_permission=False decision_review_changes_future_behavior=False lesson_candidates_write_memory=False memory_governance_stores_memory=False history_memory_audit_writes_memory=False memory_candidates_review_only=True operator_approval_required_before_memory_storage=True

# v395.1-v400.0 memory candidate application trial API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/memory-candidate-selection-packet/layer /api/memory-application-approval-lock/layer /api/memory-write-transaction-preview/layer /api/operator-confirmed-memory-application-trial/layer /api/memory-application-trial-audit/layer operator-governed-memory-application-trial-audit-v1 memory_candidate_application_trial.py candidate_selection_writes_memory=False approval_lock_reuses_approval=False transaction_preview_writes_memory=False application_harness_runs_without_confirmation=False application_audit_runs_retraction=False fresh_operator_approval_required=True single_use_memory_approval_required=True sensitive_data_screen_required=True identity_personality_mutation_screen_required=True retraction_packet_required=True

# v510.1-v515.0 sandbox execution approval gate routes/CLI flags are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-approval-scope-contract/layer /api/exact-confirmation-phrase-builder/layer /api/approval-burnout-expiry-ledger/layer /api/sandbox-command-allowlist-preview/layer /api/sandbox-execution-approval-gate-audit/layer --sandbox-execution-approval-gate-v1 sandbox_execution_approval_gate.py approval_contract_exists_is_approval_granted=False confirmation_phrase_generated_is_confirmation_entered=False command_preview_executes_commands=False approval_status=not_granted execution_status=not_executed sandbox_status=not_started autonomy_status=not_autonomous
# v515.1-v520.0 sandbox execution dry-run receipt routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-dry-run-execution-model/layer /api/command-transcript-preview/layer /api/sandbox-diff-receipt-preview/layer /api/dry-run-misinterpretation-firewall/layer /api/sandbox-execution-dry-run-receipt-audit/layer --sandbox-execution-dry-run-receipt-v1 sandbox_execution_dry_run_receipt.py dry_run_model_exists_is_sandbox_execution=False transcript_preview_is_command_output=False diff_receipt_preview_is_actual_file_change=False dry_run_success_is_authorization=False dry_run_receipt_status=prepared actual_execution_status=not_executed approval_status=not_granted sandbox_status=not_started autonomy_status=not_autonomous

# v520.1-v525.0 first sandbox execution trial routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-workspace-isolation-contract/layer /api/approved-sandbox-command-plan/layer /api/single-use-sandbox-execution-receipt/layer /api/sandbox-execution-misinterpretation-firewall/layer /api/first-sandbox-execution-trial-audit/layer --first-operator-approved-sandbox-execution-trial-v1 first_sandbox_execution_trial.py sandbox_workspace_exists_is_execution_permission=False command_plan_exists_is_command_run=False receipt_written_is_future_approval=False successful_sandbox_trial_is_autonomy=False trial_layer_status=prepared sandbox_execution_status=not_run_by_default approval_status=required live_source_status=untouched memory_status=untouched autonomy_status=not_autonomous

# v525.1-v530.0 sandbox execution runner routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-execution-runner-contract/layer /api/approval-phrase-validator/layer /api/sandbox-command-execution-harness/layer /api/execution-receipt-intake-cleanup-audit/layer /api/sandbox-execution-trial-review-board/layer --operator-approved-sandbox-execution-runner-v1 sandbox_execution_runner.py runner_contract_exists_is_execution_permission=False phrase_validated_is_command_executed=False sandbox_command_success_is_live_patch_approval=False receipt_success_is_future_authorization=False runner_status=available_under_approval_only execution_status=not_executed_by_default approval_status=required live_source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous

# v530.1-v540.0 sandbox-to-source promotion packet routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-evidence-intake-packet/layer /api/promotion-candidate-diff-preview/layer /api/rollback-recovery-packet-builder/layer /api/promotion-misinterpretation-firewall/layer /api/sandbox-to-source-promotion-review-board/layer --sandbox-to-source-promotion-packet-v1 sandbox_to_source_promotion_packet.py sandbox_evidence_exists_is_live_source_approval=False promotion_diff_preview_is_live_source_mutation=False rollback_packet_exists_is_rollback_executed=False promotion_packet_status=prepared live_source_status=untouched approval_status=required authorization_status=not_authorized rollback_status=planned_not_executed release_status=not_created autonomy_status=not_autonomous
# v601.0-v605.0 current-state integrity hardening API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/smoke-summary-version-alignment-contract/layer /api/nested-metadata-root-version-guard/layer /api/readme-current-handoff-staleness-guard/layer /api/setup-smoke-scope-guard/layer /api/current-state-integrity-staleness-hardening-board/layer current-state-integrity-staleness-hardening-v1 current_state_integrity_staleness_hardening.py hardening_report_writes_source=False hardening_report_writes_metadata=False hardening_report_executes_smoke=False audit_pass_is_release_approval=False audit_pass_is_live_patch_permission=False
# v606.0-v610.0 archive reconciliation application prep API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/archive-reconciliation-application-scope-packet/layer /api/reconciliation-application-candidate-map/layer /api/operator-reconciliation-application-approval-checklist/layer /api/dry-run-application-receipt-prep/layer /api/archive-reconciliation-application-prep-board/layer archive-reconciliation-application-prep-v1 archive_reconciliation_application_prep.py application_prep_board_is_operator_approval=False application_prep_board_writes_archive_records=False application_prep_board_mutates_current_state=False

# v611.0-v615.0 operator command center UI consolidation API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/command-center-landing-screen/layer /api/operator-queue-panel/layer /api/safety-state-panel/layer /api/workflow-navigation-groups/layer /api/system-health-summary-board/layer /api/operator-command-center-ui-consolidation-board/layer operator-command-center-ui-consolidation-v1 operator_command_center_ui_consolidation.py command_center_executes_actions=False operator_queue_grants_approval=False safety_panel_changes_authorization=False system_health_summary_runs_smoke=False ui_consolidation_expands_autonomy=False

# v616.0-v620.0 dashboard workflow simplification API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/workflow-group-route-index/layer /api/legacy-route-drawer/layer /api/archive-workflow-pipeline-view/layer /api/patch-safety-memory-group-views/layer /api/dashboard-simplification-board/layer dashboard-workflow-simplification-legacy-drawer-v1 dashboard_workflow_simplification.py workflow_index_executes_actions=False legacy_drawer_deletes_routes=False archive_pipeline_writes_archive_records=False group_views_write_memory=False simplification_board_expands_autonomy=False

# v621.0-v625.0 operator action semantics UX API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/universal-action-label-standard/layer /api/blocked-action-explanation-cards/layer /api/one-time-approval-burnout-ux/layer /api/safe-preview-before-action-summary/layer /api/operator-action-semantics-board/layer operator-action-semantics-approval-ux-v1 operator_action_semantics_ux.py action_labels_execute_actions=False blocked_cards_unblock_actions=False approval_card_reuses_approval=False safe_preview_executes_action=False semantics_board_expands_autonomy=False
# v626.0-v630.0 review packet evidence UX API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/review-packet-summary-header/layer /api/evidence-grouping-priority-layout/layer /api/receipt-ledger-readability-cards/layer /api/system-health-evidence-ux/layer /api/review-packet-evidence-ux-board/layer review-packet-readability-evidence-ux-v1 review_packet_evidence_ux.py summary_header_grants_approval=False evidence_grouping_hides_raw_evidence=False receipt_cards_treat_receipt_as_approval=False system_health_panels_run_smoke=False evidence_board_expands_autonomy=False
# v631.0-v635.0 dashboard search and surface discovery API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/surface-search-index/layer /api/route-module-smoke-discovery-cards/layer /api/workflow-aware-search-filters/layer /api/current-historical-surface-guard/layer /api/dashboard-search-discovery-board/layer operator-dashboard-search-surface-discovery-v1 dashboard_search_surface_discovery.py search_index_grants_approval=False search_index_treats_presence_as_authorization=False discovery_cards_execute_commands=False workflow_filters_hide_safety=False current_historical_guard_treats_current_as_approval=False discovery_board_expands_autonomy=False
# v636.0-v640.0 operator decision capture/approval form UX API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/decision-capture-form-schema/layer /api/approval-scope-target-binding-panel/layer /api/approval-expiration-burnout-form-ux/layer /api/denial-deferral-revision-decision-capture/layer /api/operator-decision-approval-ux-board/layer operator-decision-capture-approval-form-ux-v1 operator_decision_approval_ux.py decision_form_creates_approval=False scope_binding_grants_authorization=False approval_burnout_reuse_allowed=False denial_deferral_is_approval=False ux_board_expands_autonomy=False
# v641.0-v645.0 operator receipt timeline/audit UX API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/operator-decision-timeline-model/layer /api/approval-burnout-consumption-timeline-cards/layer /api/blocked-action-safety-event-timeline-cards/layer /api/verification-receipt-timeline-cards/layer /api/decision-audit-trail-board/layer operator-receipt-timeline-decision-audit-trail-ux-v1 operator_receipt_timeline_audit_ux.py timeline_model_grants_approval=False approval_consumption_cards_allow_reuse=False blocked_action_cards_unblock_actions=False verification_cards_treat_pass_as_authorization=False audit_trail_expands_autonomy=False

# v646.0-v650.0 operator session continuity/resume UX API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/session-resume-state-summary/layer /api/unresolved-warning-blocker-carryover/layer /api/pending-decisions-prepared-work-resume-queue/layer /api/verification-state-resume-card/layer /api/operator-session-continuity-board/layer operator-session-continuity-resume-console-ux-v1 operator_session_continuity_resume_ux.py resume_summary_starts_work=False pending_queue_starts_work=False verification_card_treats_pass_as_authorization=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False

# v651.0-v655.0 operator guided review wizard UX API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/guided-review-wizard-entry-model/layer /api/guided-evidence-warning-step-cards/layer /api/guided-decision-approval-step-ux/layer /api/guided-verification-resume-step-summary/layer /api/operator-guided-review-wizard-board/layer operator-guided-review-wizard-ux-v1 operator_guided_review_wizard_ux.py wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_treats_pass_as_authorization=False wizard_board_expands_autonomy=False

# v656.0-v660.0 project metadata schema and active context repair API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP: /api/metadata-schema-contract/layer /api/active-project-resolution-audit/layer /api/project-status-rendering-hardening/layer /api/release-note-version-semantics-audit/layer /api/metadata-integrity-board-smoke-gate/layer project-metadata-schema-active-context-repair-v1 project_metadata_active_context_repair.py schema_contract_writes_metadata=False active_project_resolution_changes_project=False status_rendering_executes_actions=False release_note_semantics_rewrites_history=False metadata_integrity_board_executes_smoke=False metadata_integrity_board_expands_autonomy=False

# v661.0-v665.0 legacy smoke segmentation repair API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py current_gate_executes_smoke=False legacy_advisory_blocks_current_release=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False
# v666.0-v675.0 manifest-driven surface registry API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board manifest-driven-surface-registry-v1 manifest_driven_surface_registry.py api_cli_manifest_adapter_status=validated_or_blocked api_cli_manifest_adapter_registers_endpoints=False manifest_presence_is_authorization=False registry_health_is_approval=False manifest_board_expands_autonomy=False

# v676.0-v685.0 dashboard renderer component extraction API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/dashboard-component-contract/layer /api/shared-review-packet-renderer/layer /api/shared-boundary-matrix-renderer/layer /api/shared-evidence-warning-renderer/layer /api/shared-decision-approval-renderer/layer /api/shared-resume-continuity-renderer/layer /api/dashboard-route-renderer-adapter/layer /api/dashboard-style-regression-guard/layer /api/legacy-renderer-duplication-audit/layer /api/dashboard-renderer-component-extraction-board/layer dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False

# v686.0-v690.0 neural command deck dashboard redesign API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/neural-deck-layout-shell/layer /api/eidolon-thinking-core-panel/layer /api/operator-conversation-console/layer /api/side-intelligence-panels/layer /api/neural-command-deck-dashboard-board/layer neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py visual_health_is_authorization=False thinking_animation_is_model_execution=False

# v691.0-v695.0 neural command deck interaction refinement API routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/interaction-focus-rail/layer /api/interaction-safe-input-deck/layer /api/panel-density-priority-tuning/layer /api/context-telemetry-affordance/layer /api/neural-command-deck-interaction-board/layer neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v760.0 API route repair tokens: /api/self-development-cycle/layer build_self_development_cycle_api_layer self-development-api-route-repair-v1 manifest_claimed_api_routes_must_dispatch=True api_404_is_release_blocking_for_claimed_routes=True applies_source_edits=False creates_concrete_diff=False expands_autonomy=False

# v845.0 manifest-gated surface validation API tokens: /api/self-development-cycle/layer manifest-gated-surface-validation-v1 validation_is_review_only=True generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False expands_autonomy=False

# v1055.0 deep diagnostic latency budget repair API tokens: doctor-deep-diagnostic-latency-budget-repair-v1 /api/doctor/deep-diagnostic-latency-budget-repair build_doctor_deep_diagnostic_latency_budget_repair_metadata build_bounded_repair_suggestions build_bounded_project_snapshot build_bounded_stable_loop_confidence build_bounded_hardening_report /api/repair-suggestions?full=true /api/project-snapshot?full=true /api/stable-loops/confidence?full=true /api/hardening-report?full=true /api/controlled-self-build?full=true bounded_preview_default=False explicit_preview_endpoints=True legacy_default_full_compatibility_restored=True heavy_full_diagnostics_preserved=True manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1056.0 slow dashboard route cohort repair API tokens: dashboard-slow-route-cohort-repair-v1 /api/dashboard/slow-route-cohort-repair build_dashboard_slow_route_cohort_repair_metadata build_dashboard_slow_route_cohort_repair bounded_route_shell_count=4 normal_dashboard_render_avoids_historical_probe_fanout=True heavy_historical_route_proofs_preserved=True manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1057.0 install-release historical blocker reduction API tokens: install-release-historical-blocker-reduction-v1 /api/install-release/historical-blocker-reduction build_install_release_historical_blocker_reduction_metadata build_install_release_historical_blocker_reduction prior_install_release_check_count=44 current_install_release_check_count=45 classified_historical_blocker_count=22 unclassified_historical_blocker_count_after_reduction=0 active_cleanliness_blocker_count_after_reduction=7 executes_full_install_release_segment=False marks_blocked_checks_pass=False marks_install_release_clean=False manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1058.0 source surface manifest dispatch candidate preparation API tokens: source-surface-manifest-dispatch-candidate-preparation-v1 /api/source-surface/dispatch-candidate-preparation build_source_surface_manifest_dispatch_candidate_preparation_metadata build_source_surface_manifest_dispatch_candidate_preparation candidate_surface_count=8 dispatch_family_count=3 dispatch_candidate_row_count=24 represented_dispatch_candidate_count=24 dashboard_dispatch_candidate_count=8 api_dispatch_candidate_count=8 smoke_dispatch_candidate_count=8 manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False api_wiring_generated=False smoke_wiring_generated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1059.0 manifest generated dispatch parity fixture preview API tokens: manifest-generated-dispatch-parity-fixture-preview-v1 /api/source-surface/manifest-generated-dispatch-parity-fixture-preview build_manifest_generated_dispatch_parity_fixture_preview_metadata build_manifest_generated_dispatch_parity_fixture_preview input_candidate_surface_count=8 input_dispatch_candidate_row_count=24 parity_fixture_surface_count=8 dispatch_family_count=3 parity_fixture_row_count=24 represented_parity_fixture_count=24 previewed_parity_fixture_count=24 dashboard_parity_fixture_count=8 api_parity_fixture_count=8 smoke_parity_fixture_count=8 fixture_files_written=False fixture_harness_executed=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1060.0 manifest generated dispatch fixture harness isolation API tokens: manifest-generated-dispatch-fixture-harness-isolation-v1 /api/source-surface/manifest-generated-dispatch-fixture-harness-isolation build_manifest_generated_dispatch_fixture_harness_isolation_metadata build_manifest_generated_dispatch_fixture_harness_isolation input_parity_fixture_row_count=24 harness_isolation_plan_count=24 dispatch_family_count=3 dashboard_harness_plan_count=8 api_harness_plan_count=8 smoke_harness_plan_count=8 isolation_contract_pass_count=24 fixture_files_written=False fixture_harness_executed=False subprocesses_spawned=False network_access_permitted=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1061.0 manifest generated dispatch fixture harness dry run ledger API tokens: manifest-generated-dispatch-fixture-harness-dry-run-ledger-v1 /api/source-surface/manifest-generated-dispatch-fixture-harness-dry-run-ledger build_manifest_generated_dispatch_fixture_harness_dry_run_ledger_metadata build_manifest_generated_dispatch_fixture_harness_dry_run_ledger input_harness_isolation_plan_count=24 dry_run_ledger_row_count=24 dispatch_family_count=3 dashboard_dry_run_ledger_count=8 api_dry_run_ledger_count=8 smoke_dry_run_ledger_count=8 dry_run_step_count_per_row=6 dry_run_ledger_step_count=144 dry_run_command_prepared_count=24 dry_run_command_executed_count=0 containment_ready_count=24 dry_run_ledger_only=True dry_run_commands_prepared=True dry_run_commands_executed=False fixture_files_written=False fixture_harness_executed=False subprocesses_spawned=False temp_workspaces_created=False mutation_snapshots_captured=False network_access_permitted=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1064.0 manifest generated dispatch fixture dry run execution prep API tokens: manifest-generated-dispatch-fixture-dry-run-execution-prep-v1 /api/source-surface/manifest-generated-dispatch-fixture-dry-run-execution-prep build_manifest_generated_dispatch_fixture_dry_run_execution_prep_metadata build_manifest_generated_dispatch_fixture_dry_run_execution_prep input_dry_run_ledger_row_count=24 execution_prep_row_count=24 dispatch_family_count=3 dashboard_execution_prep_count=8 api_execution_prep_count=8 smoke_execution_prep_count=8 execution_preflight_step_count_per_row=7 execution_preflight_step_count=168 execution_ready_contract_count=24 dry_run_execution_prepared=True dry_run_commands_executed=False fixture_files_written=False fixture_harness_executed=False subprocesses_spawned=False temp_workspaces_created=False mutation_snapshots_captured=False network_access_permitted=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1064.0 manifest generated dispatch fixture first isolated dry run trial API tokens: manifest-generated-dispatch-fixture-first-isolated-dry-run-trial-v1 /api/source-surface/manifest-generated-dispatch-fixture-first-isolated-dry-run-trial build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial input_execution_prep_row_count=24 trial_candidate_row_count=1 trial_attempt_count=1 trial_pass_count=1 remaining_unexecuted_fixture_row_count=23 dry_run_timeout_seconds=5 subprocess_spawn_count=1 temp_workspace_count=1 mutation_snapshot_count=2 source_mutation_count=0 fixture_files_written=False generated_wiring_activated=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1064.0 manifest generated dispatch fixture trial receipt hardening API tokens: manifest-generated-dispatch-fixture-trial-receipt-hardening-v1 /api/source-surface/manifest-generated-dispatch-fixture-trial-receipt-hardening build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata build_manifest_generated_dispatch_fixture_trial_receipt_hardening input_trial_receipt_count=1 hardened_receipt_count=1 receipt_required_field_count=14 receipt_boundary_field_count=8 receipt_required_fields_present_count=1 receipt_boundary_fields_valid_count=1 receipt_marker_found_count=1 snapshot_hash_pair_count=1 source_mutation_count=0 promotion_allowed_from_receipt_count=0 release_allowed_from_receipt_count=0 autonomy_allowed_from_receipt_count=0 fixture_files_written=False generated_wiring_activated=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.2 manifest fixture truth stabilization API tokens: manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion-v1 /api/source-surface/manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion input_execution_prep_row_count=24 input_hardened_receipt_count=1 batch_candidate_row_count=3 batch_attempt_count=3 batch_pass_count=3 remaining_unexecuted_fixture_row_count=21 dispatch_family_count=3 dry_run_timeout_seconds=5 subprocess_spawn_count=0 temp_workspace_count=0 mutation_snapshot_count=0 source_mutation_count=0 fixture_files_written=False generated_wiring_activated=False manual_api_dispatch_remains_authoritative=True manifest_replaces_api_dispatch=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.4 manifest fixture sandbox adapter API tokens: manifest-fixture-sandbox-adapter-contract-v1 /api/source-surface/manifest-fixture-sandbox-adapter-contract build_manifest_fixture_sandbox_adapter_contract_metadata build_manifest_fixture_sandbox_adapter_contract integrated_backend_count=0 execution_allowed=False actual_fixture_execution_allowed=False network_policy_env_var_counts_as_enforcement=False network_policy_enforced=False filesystem_policy_enforced=False source_tree_readonly_enforced=False temp_workspace_write_only_enforced=False unsupported_sandbox_blocks_fixture_execution=True fixture_files_written=False generated_wiring_activated=False manual_api_dispatch_remains_authoritative=True release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.4 full-tree mutation snapshot API tokens: full-tree-mutation-snapshot-expansion-v1 /api/source-surface/full-tree-mutation-snapshot-expansion build_full_tree_mutation_snapshot_expansion_metadata build_full_tree_mutation_snapshot_expansion watched_root_count=13 full_tree_source_scope=True installation_wide_source_scope=True root_file_watch_count=3 sandbox_root_included=True runtime_private_paths_excluded=True spawns_subprocess=False executes_fixture=False source_mutation_count=0 fixture_files_written=False generated_wiring_activated=False manual_api_dispatch_remains_authoritative=True release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.10 diagnostic API compatibility restoration API tokens: diagnostic-api-compatibility-restoration-v1 /api/doctor/diagnostic-api-compatibility-restoration /api/repair-suggestions/preview /api/project-snapshot/preview /api/stable-loops/confidence/preview /api/hardening-report/preview /api/controlled-self-build/lightweight-preview build_diagnostic_api_compatibility_restoration_metadata build_diagnostic_api_compatibility_restoration legacy_default_full_compatibility_restored=True explicit_preview_endpoints=True preview_routes_claim_full_diagnostics=False doctor_diagnostic_latency_uses_preview_routes=True manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1065.10 release-tier blocker repair batch I API tokens: release-tier-blocker-repair-batch-i-v1 /api/release/release-tier-blocker-repair-batch-i build_release_tier_blocker_repair_batch_i_metadata build_release_tier_blocker_repair_batch_i repaired_target_count=5 docs_evidence_repaired=True release_install_executed=False manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1065.10 release-tier blocker repair batch II API tokens: release-tier-blocker-repair-batch-ii-v1 /api/release/release-tier-blocker-repair-batch-ii build_release_tier_blocker_repair_batch_ii_metadata build_release_tier_blocker_repair_batch_ii repaired_target_count=3 helper_version_currentness_repaired=True source_only_private_runtime_absence_allowed=True release_install_executed=False manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1065.10 installed tree cleanup enforcement API tokens: installed-tree-cleanup-enforcement-v1 /api/installed-tree-cleanup/enforcement /api/installed-tree-cleanup/enforcement/run build_installed_tree_cleanup_enforcement_metadata build_installed_tree_cleanup_enforcement installed_tree_scan_includes_sandbox=True protected_active_candidate_count=3 deletable_obsolete_candidate_count=0 sandbox_obsolete_candidate_count=0 stale_17_file_expectation_reconciled=True delete_requires_post_confirmation=True get_preview_only=True source_files_mutated_by_get=False deletes_active_imported_modules=False generated_wiring_activated=False manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.10 dashboard shell performance stabilization API tokens: dashboard-shell-performance-stabilization-v1 /api/dashboard/shell-performance-stabilization build_dashboard_shell_performance_stabilization_metadata build_dashboard_shell_performance_stabilization target_shell_route_count=9 shell_route_budget_ms=2000 route_shell_pass_count=9 subprocess_call_count=0 dashboard_get_preview_only=True dashboard_get_spawns_subprocesses=False dashboard_get_executes_full_diagnostics=False dashboard_get_runs_install_release=False heavy_proof_paths_preserved=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.11 full navigation GET side effect safety API tokens: dashboard-full-navigation-get-side-effect-safety-gate-v1 /api/dashboard/full-navigation-get-side-effect-safety-gate build_dashboard_full_navigation_get_side_effect_safety_gate_metadata build_dashboard_full_navigation_get_side_effect_safety_gate expected_min_nav_route_count=560 dynamic_dashboard_render_target_count=18 dynamic_api_get_target_count=9 dashboard_get_subprocess_call_count=0 api_get_subprocess_call_count=0 dashboard_get_write_call_count=0 api_get_write_call_count=0 dashboard_get_delete_call_count=0 api_get_delete_call_count=0 full_navigation_static_scan_only_for_all_routes=True bounded_dynamic_render_for_risk_routes=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1065.12 install-release segment runner timeout decomposition API tokens: install-release-segment-runner-timeout-decomposition-v1 /api/install-release/segment-runner-timeout-decomposition build_install_release_segment_runner_timeout_decomposition_metadata build_install_release_segment_runner_timeout_decomposition superseded_timeout_parent_row_count=7 overlay_evidence_row_count=7 install_release_parent_segment_decomposed=True parent_segment_runs_superseded_timeout_rows=False segment_runner_treats_superseded_parent_as_current_pass=False individual_parent_checks_remain_available=True manual_smoke_remains_authoritative=True manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# v1066.0 manifest fixture receipt consolidation API tokens: manifest-fixture-receipt-consolidation-v1 /api/source-surface/manifest-fixture-receipt-consolidation build_manifest_fixture_receipt_consolidation_metadata build_manifest_fixture_receipt_consolidation receipt_family_count=3 consolidated_receipt_row_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_requires_os_sandbox=True dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True

# 1066.1 Audited Sandbox Backend Preflight Contract API tokens: audited-sandbox-backend-preflight-contract-v1 /api/source-surface/audited-sandbox-backend-preflight-contract build_audited_sandbox_backend_preflight_contract_metadata build_audited_sandbox_backend_preflight_contract actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1066.2 Sandbox Backend Capability Evidence Gate API tokens: sandbox-backend-capability-evidence-gate-v1 /api/source-surface/sandbox-backend-capability-evidence-gate build_sandbox_backend_capability_evidence_gate_metadata build_sandbox_backend_capability_evidence_gate actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1066.3 Fixture Execution Admission Gate API tokens: fixture-execution-admission-gate-v1 /api/source-surface/fixture-execution-admission-gate build_fixture_execution_admission_gate_metadata build_fixture_execution_admission_gate actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1066.4 First Sandboxed Fixture Execution Trial API tokens: sandboxed-fixture-execution-trial-v1 /api/source-surface/sandboxed-fixture-execution-trial build_sandboxed_fixture_execution_trial_metadata build_sandboxed_fixture_execution_trial actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1066.5 Sandboxed Fixture Batch Execution API tokens: sandboxed-fixture-batch-execution-v1 /api/source-surface/sandboxed-fixture-batch-execution build_sandboxed_fixture_batch_execution_metadata build_sandboxed_fixture_batch_execution actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1067.0 Generated Dispatch Promotion Readiness Ledger API tokens: generated-dispatch-promotion-readiness-ledger-v1 /api/source-surface/generated-dispatch-promotion-readiness-ledger build_generated_dispatch_promotion_readiness_ledger_metadata build_generated_dispatch_promotion_readiness_ledger actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1068.0 Source Decomposition Batch I API tokens: source-decomposition-batch-i-v1 /api/source-surface/source-decomposition-batch-i build_source_decomposition_batch_i_metadata build_source_decomposition_batch_i actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
# 1069.0 Autonomy Phase 0 Observation-Only Contract API tokens: autonomy-phase-zero-observation-contract-v1 /api/source-surface/autonomy-phase-zero-observation-contract build_autonomy_phase_zero_observation_contract_metadata build_autonomy_phase_zero_observation_contract actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# 1069.1 Source Decomposition Batch II API tokens: source-decomposition-batch-ii-v1 /api/source-surface/source-decomposition-batch-ii build_source_decomposition_batch_ii_metadata build_source_decomposition_batch_ii review-surface-shared-v1 actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# 1070.1 Dashboard API Smoke Shared Utility Adoption API tokens: dashboard-api-smoke-shared-utility-adoption-v1 /api/source-surface/dashboard-api-smoke-shared-utility-adoption build_dashboard_api_smoke_shared_utility_adoption_metadata build_dashboard_api_smoke_shared_utility_adoption api_preview_payload preview_response_payload missing_tokens sandbox-backend-adapter-skeleton-v1 actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# 1070.1 Dashboard Review Component Extraction Pilot API tokens: dashboard-review-component-extraction-pilot-v1 /api/source-surface/dashboard-review-component-extraction-pilot build_dashboard_review_component_extraction_pilot_metadata build_dashboard_review_component_extraction_pilot api_preview_payload preview_response_payload render_review_card_component render_review_table_component actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# v1070.2 Smoke Check Helper Extraction Pilot API tokens: smoke-check-helper-extraction-pilot-v1 /api/source-surface/smoke-check-helper-extraction-pilot build_smoke_check_helper_extraction_pilot_metadata build_smoke_check_helper_extraction_pilot api_preview_payload smoke-check-shared-v1 read_docs_bundle missing_required_tokens authority_boundary_violations smoke_token_validation_row actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True
    if parts == ['source-surface', 'api-preview-adapter-extraction-pilot']:
        from api_preview_adapter_extraction_pilot import api_preview_payload, build_api_preview_adapter_extraction_pilot, build_api_preview_adapter_extraction_pilot_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_api_preview_adapter_extraction_pilot(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_api_preview_adapter_extraction_pilot_metadata(project_id=project_id)
        payload = api_preview_payload(report)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            payload.setdefault("warnings", []).append("API Preview Adapter Extraction Pilot is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(payload)

    if parts == ['source-surface', 'api-preview-adapter-backfill']:
        from api_preview_adapter_backfill import api_preview_payload, build_api_preview_adapter_backfill, build_api_preview_adapter_backfill_metadata

        project_id = query.get("project", ["eidolon"])[0]
        inspect_sources = _query_bool(query, "inspect_sources", False)
        report = build_api_preview_adapter_backfill(Path(__file__).resolve().parents[1], inspect_sources=True) if inspect_sources else build_api_preview_adapter_backfill_metadata(project_id=project_id)
        payload = api_preview_payload(report)
        if _query_bool(query, "execute", False) or _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            payload.setdefault("warnings", []).append("API Preview Adapter Backfill is GET preview-only. It does not execute generated fixtures, activate generated wiring, authorize release, or expand autonomy.")
        return 200, _ok(payload)

# v1070.3 API Preview Adapter Extraction Pilot API tokens: api-preview-adapter-extraction-pilot-v1 /api/source-surface/api-preview-adapter-extraction-pilot build_api_preview_adapter_extraction_pilot_metadata build_api_preview_adapter_extraction_pilot api_preview_payload build_api_preview_envelope api_preview_adapter_rows preview_response_payload actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# v1070.4 API Preview Adapter Backfill API tokens: api-preview-adapter-backfill-v1 /api/source-surface/api-preview-adapter-backfill build_api_preview_adapter_backfill_metadata build_api_preview_adapter_backfill api_preview_payload build_api_preview_envelope api_preview_adapter_backfill_rows actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True

# v1070.5 API Server Dispatch Helper Extraction Pilot API tokens: api-server-dispatch-helper-extraction-pilot-v1 /api/source-surface/api-server-dispatch-helper-extraction-pilot build_api_server_dispatch_helper_extraction_pilot_metadata build_api_server_dispatch_helper_extraction_pilot api_preview_payload api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_rows actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_api_dispatch_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.7 API Server Dispatch Helper Backfill API tokens: api-server-dispatch-helper-backfill-v1 /api/source-surface/api-server-dispatch-helper-backfill build_api_server_dispatch_helper_backfill_metadata build_api_server_dispatch_helper_backfill api_preview_payload api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_backfill_rows actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_api_dispatch_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.7 API Server Dispatch Helper Route Table Extraction API tokens: api-server-dispatch-helper-route-table-extraction-v1 /api/source-surface/api-server-dispatch-helper-route-table-extraction build_api_server_dispatch_route_table_extraction_metadata build_api_server_dispatch_route_table_extraction api_preview_payload api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_api_dispatch_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.8 API Server Dispatch Route Table Backfill API tokens: api-server-dispatch-route-table-backfill-v1 /api/source-surface/api-server-dispatch-route-table-backfill build_api_server_dispatch_route_table_backfill_metadata build_api_server_dispatch_route_table_backfill api_preview_payload api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows api_dispatch_route_table_backfill_rows build_route_table_preview_payload route_table_backfilled_route_count=1 route_table_route_count=3 manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_api_dispatch_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1070.9 API Server Dispatch Route Table Safety Parity API tokens: api-server-dispatch-route-table-safety-parity-v1 /api/source-surface/api-server-dispatch-route-table-safety-parity build_api_server_dispatch_route_table_safety_parity_metadata build_api_server_dispatch_route_table_safety_parity api_preview_payload route_table_payload_manual_helper_parity=True route_table_safety_key_parity=True route_table_safe_preview_row_count=4 route_table_newly_migrated_route_count=1 old_direct_branch_removed=True manual_route_table_replaces_api_dispatch=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_api_dispatch_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1071.5 audited sandbox evidence interface API tokens: audited-sandbox-backend-evidence-interface-v1 /api/source-surface/audited-sandbox-backend-evidence-interface build_audited_sandbox_backend_evidence_interface_metadata build_audited_sandbox_backend_evidence_interface api_preview_payload route_table_safe_preview_row_count=5 sandbox_backend_admitted=False fixture_execution_remains_blocked=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_api_dispatch_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_smoke_remains_authoritative=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="eidolon-api",
        description="Run Eidolon's local operator-governed HTTP API.",
        epilog=API_CLI_HELP_SENTINEL,
    )
    parser.add_argument("--host", default=None, help="Bind host; defaults to the configured local API host.")
    parser.add_argument("--port", type=int, default=None, help="Bind port; defaults to the configured local API port.")
    args = parser.parse_args(argv)
    run_api_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
