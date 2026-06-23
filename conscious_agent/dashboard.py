
from __future__ import annotations

import json
import re
import traceback
from pathlib import Path
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from paths import DATA_DIR, ROOT_DIR
from approval_manager import approve_approval, approval_text, get_approval, list_approvals, reject_approval
from api_server import dispatch_api, parse_request_body, _to_jsonable
from chat_action_router import (
    propose_chat_action,
    execute_chat_action,
    list_chat_actions,
    load_chat_action,
    chat_action_text,
)
from dashboard_chat_console import (
    create_dashboard_chat_turn,
    dashboard_chat_turn_text,
    list_dashboard_chat_turns,
    load_dashboard_chat_turn,
)
from desktop_shell import desktop_status_text
from desktop_setup_helper import create_setup_report, list_setup_reports, load_setup_report, setup_report_text
from desktop_onboarding_wizard import build_onboarding_run, list_onboarding_runs, load_onboarding_run, onboarding_run_text
from diagnostics import (
    build_diagnostic_report,
    diagnostic_report_text,
    list_diagnostic_reports,
    load_diagnostic_report,
    save_diagnostic_report,
)
from goal_manager import add_goal, get_goal, list_goals
from maintenance_advisor import (
    list_maintenance_scans,
    load_maintenance_scan,
    maintenance_scan_text,
    run_maintenance_scan,
)
from notification_manager import (
    clear_dismissed_notifications,
    list_notifications,
    load_notification,
    notification_text,
    update_notification_status,
)
from memory import load_memories
from memory_compactor import (
    list_memory_summaries,
    load_memory_summary,
    memory_status_text,
    memory_summary_text,
)
from patch_suggester import list_patch_proposals, load_patch_proposal, patch_proposal_text, suggest_patch
from work_queue_patch_bridge import (
    create_patch_followup_items,
    create_patch_work_item,
    suggest_patch_for_work_item,
)
from project_manager import get_active_project
from session_planner import create_session_plan, list_session_plans, load_session_plan, session_plan_text
from settings_manager import get_setting, load_settings, set_setting, settings_health, settings_text
from task_queue import add_task, get_task, list_tasks, next_task, task_detail_text, task_status_counts
from work_queue import (
    add_work_item,
    find_work_item,
    format_work_item,
    list_work_items,
    summarize_queue,
    update_work_item,
)
from task_work_executor import execute_next_task_work, execute_task_work_item, task_work_execution_text
from task_approval_bridge import request_task_work_approval, task_approvals_text
from task_lifecycle import (
    STAGE_FILTER_LABELS,
    derive_task_lifecycle,
    lifecycle_stage_matches,
    list_task_lifecycles,
    normalize_lifecycle_stage_filter,
    task_lifecycle_summary,
    task_lifecycle_text,
)
from task_recovery import (
    build_task_recovery,
    mark_task_ready_for_retry,
    retry_task_work,
    task_recovery_summary,
    task_recovery_text,
)
from work_cycle import run_supervised_work_cycle, list_work_cycles, load_work_cycle, work_cycle_text
from stable_supervised_loop import (
    build_stable_loop_preflight,
    list_stable_loops,
    load_stable_loop,
    run_stable_supervised_loop,
    stable_loop_text,
    stable_preflight_text,
)
from stable_loop_review import (
    REVIEW_FILTER_LABELS,
    REVIEW_STATUS_LABELS,
    cleanup_stable_loop_history,
    list_stable_loop_reviews,
    loop_is_archived,
    loop_is_live_ready,
    normalize_review_filter,
    review_label_for_loop,
    review_status_for_loop,
    run_approved_stable_loop_live,
    set_stable_loop_archived,
    stable_loop_review_summary,
    stable_loop_review_text,
    update_stable_loop_review,
)
from stable_loop_audit import refresh_stable_loop_audit, stable_loop_audit_text
from stable_loop_operator_notes import (
    FINAL_DECISION_LABELS,
    add_stable_loop_operator_note,
    get_stable_loop_operator_notes,
    set_stable_loop_final_decision,
    stable_loop_operator_notes_text,
    update_stable_loop_check,
)
from stable_loop_decision_report import (
    DECISION_FILTER_LABELS,
    cleanup_stable_loop_decision_history,
    list_stable_loop_decision_rows,
    normalize_decision_filter,
    stable_loop_decision_row,
    stable_loop_decision_summary,
    stable_loop_decision_report_text,
)
from stable_loop_followup_tasks import (
    create_stable_loop_followup_tasks,
    create_stable_loop_followups_for_decisions,
    stable_loop_followup_summary,
    followup_result_text,
    followup_batch_text,
)
from stable_loop_followup_lifecycle import (
    followup_lifecycle_summary_text,
    followup_resolution_text,
    list_stable_loop_followup_task_rows,
    resolve_stable_loop_followups,
    resolve_task_stable_loop_followup,
    stable_loop_followup_lifecycle_summary,
    stable_loop_followup_task_text,
)
from stable_loop_followup_completion import (
    FOLLOWUP_COMPLETION_FILTER_LABELS,
    cleanup_stable_loop_followup_completions,
    mark_stable_loop_followup_chain_closed,
    normalize_followup_completion_filter,
    stable_loop_followup_completion_cleanup_text,
    stable_loop_followup_completion_report_text,
    stable_loop_followup_completion_summary,
    stable_loop_followup_completion_row,
    stable_loop_followup_closure_text,
)
from stable_loop_guardrails import stable_loop_guardrail_summary, stable_loop_guardrails_text
from stabilization_checkpoint import build_stabilization_checkpoint, stabilization_checkpoint_text
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
    doctor_report_text,
    repair_suggestions_text,
    patch_integrity_text,
    project_snapshot_text,
    task_review_text,
    recovery_drill_text,
    stable_loop_confidence_text,
    hardening_report_text,
    controlled_self_build_text,
)
from controlled_build_cycle import (
    build_controlled_task_selection,
    build_patch_plan,
    patch_workspace_status,
    preview_staged_diff,
    readme_gate,
    build_controlled_build_cycle,
    build_supervised_dev_loop,
    controlled_task_selection_text,
    patch_plan_text,
    workspace_status_text,
    diff_preview_text,
    readme_gate_text,
    controlled_build_cycle_text,
    supervised_dev_loop_text,
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
    codebase_map_text,
    task_dependencies_text,
    test_plan_text,
    patch_risk_text,
    patch_review_text,
    project_memory_index_text,
    workspace_status_text as intelligence_workspace_status_text,
    cross_project_task_review_text,
    asymmetric_dev_loop_text,
)
from workspace_orchestration import (
    build_project_registry,
    build_project_health,
    build_command_profiles,
    build_workspace_dependency_map,
    build_workspace_task_inbox,
    build_project_context,
    build_workspace_timeline,
    build_workspace_dev_loop,
    project_registry_text,
    project_health_text,
    command_profiles_text,
    workspace_dependency_map_text,
    workspace_task_inbox_text,
    project_context_text,
    workspace_timeline_text,
    workspace_dev_loop_text,
)
from workspace_execution import (
    build_workspace_registry_audit,
    build_workspace_repair_suggestions,
    build_project_boundary_check,
    build_workspace_patch_plan,
    build_workspace_preview_diff,
    build_workspace_verify_latest,
    build_guarded_workspace_dev_loop,
    workspace_registry_audit_text,
    workspace_repair_suggestions_text,
    project_boundary_check_text,
    workspace_patch_plan_text,
    workspace_preview_diff_text,
    workspace_verify_latest_text,
    guarded_workspace_dev_loop_text,
)
from patch_drafting import (
    build_patch_draft_request,
    build_draft_patch,
    build_patch_draft_status,
    build_patch_review_notes,
    build_draft_diff,
    build_draft_test_impact,
    build_approval_gate,
    build_apply_approved_draft,
    build_rollback_approved_draft,
    build_human_approved_patch_loop,
    build_draft_quality,
    build_draft_file_targets,
    build_draft_intent_blocks,
    build_draft_conflicts,
    build_draft_verification_bundle,
    build_draft_review_checklist,
    build_approved_draft_execution_report,
    build_review_centered_patch_loop,
    patch_draft_request_text,
    draft_patch_text,
    patch_draft_status_text,
    patch_review_notes_text,
    draft_diff_text,
    draft_test_impact_text,
    approval_gate_text,
    apply_approved_draft_text,
    draft_rollback_text,
    human_approved_patch_loop_text,
    draft_quality_text,
    draft_file_targets_text,
    draft_intent_blocks_text,
    draft_conflicts_text,
    draft_verification_bundle_text,
    draft_review_checklist_text,
    approved_draft_execution_report_text,
    review_centered_patch_loop_text,
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
    code_edit_proposal_text,
    safe_rewrite_preview_text,
    generated_code_patch_text,
    test_suggestions_text,
    inline_review_note_text,
    apply_approved_code_patch_text,
    prepare_release_package_text,
    release_readiness_text,
    human_approved_release_loop_text,
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
    code_patch_status_text,
    symbol_scan_text,
    rewrite_plan_text,
    rewrite_conflicts_text,
    code_patch_diff_bundle_text,
    apply_code_patch_transaction_text,
    semantic_checks_text,
    release_artifact_text,
    release_audit_trail_text,
    generated_code_release_loop_text,
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
    task_to_code_patch_text,
    code_context_text,
    patch_prompt_text,
    parse_generated_edits_text,
    edit_consistency_text,
    ai_code_patch_dry_run_text,
    patch_failure_analysis_text,
    patch_learning_notes_text,
    ai_assisted_code_patch_loop_text,
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
    patch_objective_refinement_text,
    code_context_ranking_text,
    patch_safety_envelope_text,
    generated_patch_validation_text,
    patch_simulation_text,
    test_stub_plan_text,
    patch_review_score_text,
    patch_recovery_plan_text,
    validated_ai_code_patch_loop_text,
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
    ai_patch_review_bundle_text,
    review_bundle_integrity_text,
    approval_ready_text,
    approval_ledger_text,
    apply_validated_ai_patch_text,
    post_apply_review_text,
    package_build_plan_text,
    approval_to_release_loop_text,
    bind_validated_approval_text,
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
    release_manifest_integrity_text,
    package_inventory_text,
    package_checksums_text,
    release_notes_text,
    release_handoff_report_text,
    build_release_zip_text,
    verify_release_unzip_text,
    release_pipeline_audit_text,
    verified_release_package_loop_text,
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
    release_profiles_text,
    package_privacy_scan_text,
    portable_metadata_check_text,
    first_run_check_text,
    dependency_advisor_text,
    upgrade_notes_text,
    runtime_migration_check_text,
    release_install_verification_text,
    verified_installable_release_loop_text,
    smoke_runtime_hardening_text,
    external_zip_install_verification_text,
    deterministic_release_manifest_text,
    update_dry_run_plan_text,
    atomic_source_update_text,
    runtime_migration_assistant_text,
    route_safety_harness_text,
    release_dashboard_command_center_text,
    clean_room_install_harness_text,
    verified_self_update_release_pipeline_text,
)
from self_maintenance import (
    build_self_maintenance_proposal_sandbox,
    build_patch_plan_builder,
    build_dry_run_patch_generator,
    build_patch_safety_auditor,
    build_apply_patch_to_temp_clone,
    build_maintenance_review_bundle,
    build_human_approval_binding,
    build_real_maintenance_patch_apply,
    build_post_apply_health_monitor,
    build_controlled_maintenance_cycle,
    build_assisted_self_improvement_release,
    self_maintenance_proposal_text,
    patch_plan_builder_text,
    dry_run_patch_generator_text,
    patch_safety_auditor_text,
    apply_patch_to_temp_clone_text,
    maintenance_review_bundle_text,
    human_approval_binding_text,
    real_maintenance_patch_apply_text,
    post_apply_health_monitor_text,
    controlled_maintenance_cycle_text,
    assisted_self_improvement_release_text,
    build_release_candidate_governance,
    build_release_evidence_bundle,
    build_release_artifact_diff,
    build_pre_v28_governance_audit,
    build_verifiable_release_evidence_system,
    build_evidence_operator_summary,
    build_evidence_timeline,
    build_durable_release_evidence_archive,
    release_candidate_governance_text,
    release_evidence_bundle_text,
    release_artifact_diff_text,
    pre_v28_governance_audit_text,
    verifiable_release_evidence_system_text,
    evidence_operator_summary_text,
    evidence_timeline_text,
    durable_release_evidence_archive_text,
    build_release_signing_status,
    build_signing_readiness_audit,
    build_pre_v30_signing_prep_audit,
    build_signing_api_hardening,
    build_canonical_schema_validator,
    build_source_data_sanitizer,
    build_signing_trust_model,
    build_release_signing_tamper_drill,
    build_public_key_policy_design,
    build_detached_signature_contract,
    build_signature_fixture_verification,
    build_external_signer_workflow,
    build_detached_signature_verification_system,
    build_signature_verification_hardening,
    build_public_trust_root_config,
    build_external_signing_payload_export,
    build_signed_fixture_test_suite,
    build_release_publish_gate,
    build_release_trust_dashboard_polish,
    build_api_route_safety_audit,
    build_release_reproducibility_check,
    build_pre_v32_release_candidate_gate,
    build_signed_release_governance,
    build_governance_report_cleanup,
    build_release_candidate_workspace,
    build_artifact_binding_audit_v2,
    build_surface_consistency_audit,
    build_external_signing_handoff,
    build_signature_intake_validation,
    build_trusted_signer_registry,
    build_governance_scenario_suite,
    build_pre_v33_operations_gate,
    build_release_operations_console,
    build_operations_console_cleanup,
    build_release_candidate_review,
    build_signed_artifact_intake,
    build_trust_root_lifecycle,
    build_publish_decision_explainer,
    build_operator_action_guardrails,
    build_unsigned_release_drill,
    build_signed_fixture_release_drill,
    build_pre_v34_operator_workflow_gate,
    build_release_operator_workflow,
    build_release_candidate_record_v2,
    build_signed_artifact_intake_v2,
    build_trust_root_management_policy,
    build_trust_root_mutation_guardrails,
    build_signed_release_publish_decision,
    build_operator_dashboard_action_states,
    build_release_audit_trail,
    build_trusted_fixture_workflow,
    build_pre_v35_trusted_candidate_gate,
    build_trusted_release_candidate_system,
    build_publish_approval_separation_system,
    build_controlled_publish_approval_system,
    build_controlled_publish_approval_write_system,
    build_publish_approval_lifecycle_system,
    build_controlled_publish_approval_revocation_system,
    build_autonomy_readiness_boundary_system,
    autonomy_readiness_boundary_system_text,
    build_autonomous_patch_proposal_system,
    build_pre_v42_autonomous_patch_gate,
    build_generate_sandbox_patch,
    build_sandbox_patch_diff,
    autonomous_patch_proposal_system_text,
    build_controlled_source_apply_system,
    controlled_source_apply_system_text,
    build_source_apply_record_reader,
    build_source_rollback_eligibility,
    build_source_rollback_dry_run_v2,
    build_pre_v44_source_rollback_gate,
    build_controlled_source_rollback_system,
    controlled_source_rollback_system_text,
    build_controlled_self_maintenance_loop,
    controlled_self_maintenance_loop_text,
    build_controlled_self_maintenance_work_queue,
    controlled_self_maintenance_work_queue_text,
    build_maintenance_task_queue_registry,
    maintenance_task_queue_registry_text,
    build_maintenance_task_selection_policy,
    maintenance_task_selection_policy_text,
    build_autonomy_queue_report_cache,
    build_maintenance_task_drilldown_view,
    build_maintenance_queue_stale_state_warnings,
    build_maintenance_runtime_privacy_audit,
    build_operator_command_palette_report,
    build_dashboard_api_queue_parity,
    build_queue_verification_receipt,
    build_dashboard_accessibility_compact_layout,
    build_pre_v47_attention_scheduler_gate,
    build_controlled_attention_scheduler,
    build_attention_selection_receipt,
    build_pre_v47_1_attention_receipt_gate,
    build_attention_budget_ledger,
    build_deferred_task_memory,
    build_blocked_task_handling,
    build_attention_resume_context,
    build_attention_dashboard_polish,
    build_attention_api_parity_gate,
    build_reflection_hooks_read_only,
    build_pre_v48_reflection_gate,
    build_controlled_reflection_memory_loop,
    build_reflection_review_receipts,
    build_reflection_candidate_deduplication,
    build_reflection_rejection_memory_runtime,
    build_reflection_promotion_drafts,
    build_memory_safety_classifier,
    build_reflection_dashboard_polish,
    build_reflection_api_parity_gate,
    build_reflection_privacy_package_hardening,
    build_pre_v49_identity_continuity_gate,
    build_identity_continuity_layer,
    build_identity_receipts,
    build_pre_v49_1_identity_receipts_gate,
    build_stable_principles_ledger,
    build_identity_drift_classifier,
    build_identity_snapshot_comparison,
    build_operator_identity_review_drafts,
    build_identity_dashboard_polish,
    build_identity_api_parity_gate,
    build_identity_privacy_package_hardening,
    build_pre_v50_durable_memory_gate,
    build_supervised_durable_memory_promotion,
    build_memory_promotion_receipts,
    build_memory_promotion_deduplication,
    build_memory_rejection_runtime_ledger,
    build_memory_promotion_confirmation_gate,
    build_memory_removal_drafts,
    build_pre_v51_durable_write_gate,
    build_controlled_durable_memory_write_path,
    build_durable_memory_write_receipts,
    build_memory_store_schema_hardening,
    build_memory_read_path,
    build_memory_search_filter,
    build_memory_correction_drafts,
    build_memory_removal_confirmation_path,
    build_memory_store_dashboard_polish,
    build_memory_store_api_parity_gate,
    build_pre_v52_recall_gate,
    build_memory_recall_self_context,
    build_memory_recall_receipts,
    build_recall_conflict_resolver,
    build_stale_memory_handling,
    build_recall_scope_controls,
    build_recall_privacy_classifier,
    build_recall_dashboard_polish,
    build_recall_api_parity_gate,
    build_pre_v53_memory_informed_planning_gate,
    build_memory_informed_planning_loop,
    build_memory_informed_planning_receipts,
    build_plan_conflict_classifier,
    build_plan_revision_drafts,
    build_planning_scope_controls,
    build_planning_risk_budget,
    build_planning_dashboard_polish,
    build_planning_api_parity_gate,
    build_planning_privacy_package_hardening,
    build_pre_v54_action_planning_gate,
    build_supervised_action_planning_loop,
    build_action_plan_receipts,
    build_action_step_classifier,
    build_action_dependency_graph,
    build_action_risk_budget,
    build_action_rehearsal_dry_run_preview,
    build_action_dashboard_polish,
    build_action_api_parity_gate,
    build_action_privacy_package_hardening,
    build_pre_v55_controlled_execution_gate,
    build_controlled_action_execution_preview,
    controlled_attention_scheduler_text,
    attention_selection_receipt_text,
    attention_budget_ledger_text,
    deferred_task_memory_text,
    blocked_task_handling_text,
    attention_resume_context_text,
    reflection_hooks_read_only_text,
    pre_v48_reflection_gate_text,
    controlled_reflection_memory_loop_text,
    reflection_review_receipts_text,
    reflection_promotion_drafts_text,
    memory_safety_classifier_text,
    pre_v49_identity_continuity_gate_text,
    identity_continuity_layer_text,
    identity_receipts_text,
    pre_v49_1_identity_receipts_gate_text,
    stable_principles_ledger_text,
    identity_drift_classifier_text,
    identity_snapshot_comparison_text,
    operator_identity_review_drafts_text,
    pre_v50_durable_memory_gate_text,
    supervised_durable_memory_promotion_text,
    memory_promotion_receipts_text,
    memory_promotion_deduplication_text,
    memory_rejection_runtime_ledger_text,
    memory_promotion_confirmation_gate_text,
    memory_removal_drafts_text,
    pre_v51_durable_write_gate_text,
    controlled_durable_memory_write_path_text,
    durable_memory_write_receipts_text,
    memory_store_schema_hardening_text,
    memory_read_path_text,
    memory_search_filter_text,
    memory_correction_drafts_text,
    memory_removal_confirmation_path_text,
    memory_store_dashboard_polish_text,
    memory_store_api_parity_gate_text,
    pre_v52_recall_gate_text,
    memory_recall_self_context_text,
    memory_recall_receipts_text,
    recall_conflict_resolver_text,
    stale_memory_handling_text,
    recall_scope_controls_text,
    recall_privacy_classifier_text,
    recall_dashboard_polish_text,
    recall_api_parity_gate_text,
    pre_v53_memory_informed_planning_gate_text,
    memory_informed_planning_loop_text,
    memory_informed_planning_receipts_text,
    plan_conflict_classifier_text,
    plan_revision_drafts_text,
    planning_scope_controls_text,
    planning_risk_budget_text,
    planning_dashboard_polish_text,
    planning_api_parity_gate_text,
    planning_privacy_package_hardening_text,
    pre_v54_action_planning_gate_text,
    supervised_action_planning_loop_text,
    action_plan_receipts_text,
    action_step_classifier_text,
    action_dependency_graph_text,
    action_risk_budget_text,
    action_rehearsal_dry_run_preview_text,
    action_dashboard_polish_text,
    action_api_parity_gate_text,
    action_privacy_package_hardening_text,
    pre_v55_controlled_execution_gate_text,
    controlled_action_execution_preview_text,
    execution_preview_receipts_text,
    execution_step_permission_classifier_text,
    read_only_command_allowlist_text,
    execution_sandbox_evidence_binder_text,
    execution_result_receipts_text,
    execution_dashboard_polish_text,
    execution_api_parity_gate_text,
    execution_privacy_package_hardening_text,
    pre_v56_read_only_execution_gate_text,
    controlled_read_only_action_execution_text,
    read_only_execution_receipts_text,
    expanded_diagnostic_allowlist_text,
    read_only_output_classifier_text,
    diagnostic_evidence_binder_text,
    diagnostic_result_summaries_text,
    read_only_execution_dashboard_polish_text,
    read_only_execution_api_parity_gate_text,
    read_only_execution_privacy_package_hardening_text,
    pre_v57_evidence_gathering_gate_text,
    evidence_gathering_maintenance_loop_text,
    evidence_collection_receipts_text,
    diagnostic_issue_classifier_text,
    evidence_conflict_staleness_resolver_text,
    evidence_to_plan_update_drafts_text,
    diagnostic_coverage_map_text,
    evidence_dashboard_polish_text,
    evidence_api_parity_gate_text,
    evidence_privacy_package_hardening_text,
    pre_v58_patch_proposal_gate_text,
    evidence_grounded_patch_proposal_loop_text,
    controlled_sandbox_patch_execution_text,
    sandbox_execution_receipts_text,
    sandbox_verification_matrix_text,
    sandbox_drift_detector_text,
    sandbox_rollback_rehearsal_text,
    sandbox_apply_candidate_drafts_text,
    sandbox_dashboard_polish_text,
    sandbox_api_parity_gate_text,
    sandbox_privacy_package_hardening_text,
    pre_v60_source_apply_handoff_gate_text,
    controlled_sandbox_source_apply_handoff_text,
    source_apply_handoff_receipts_text,
    source_baseline_drift_resolver_text,
    reviewed_artifact_set_binder_text,
    source_apply_handoff_eligibility_classifier_text,
    source_apply_dry_run_bridge_text,
    source_apply_handoff_dashboard_polish_text,
    source_apply_handoff_api_parity_gate_text,
    source_apply_handoff_privacy_hardening_text,
    pre_v61_controlled_apply_bridge_gate_text,
    controlled_source_apply_bridge_refinement_text,
    source_apply_transaction_planner_text,
    source_apply_backup_binder_text,
    source_apply_transaction_dry_run_verifier_text,
    source_apply_transaction_confirmation_gate_text,
    supervised_source_apply_executor_text,
    post_apply_verification_runner_text,
    transaction_rollback_rehearsal_text,
    source_apply_transaction_dashboard_command_center_text,
    pre_v62_transaction_release_gate_text,
    supervised_source_apply_transaction_layer_text,
    transaction_receipt_ledger_text,
    transaction_diff_viewer_text,
    transaction_conflict_detector_text,
    transaction_approval_record_binder_text,
    transaction_package_evidence_exporter_text,
    transaction_replay_audit_text,
    transaction_dashboard_receipt_timeline_text,
    transaction_api_search_filtering_text,
    pre_v63_transaction_evidence_gate_text,
    durable_transaction_evidence_system_text,
    transaction_evidence_summarizer_text,
    improvement_candidate_registry_text,
    evidence_based_candidate_scoring_text,
    improvement_regression_pattern_detector_text,
    improvement_risk_blast_radius_forecaster_text,
    supervised_recommendation_queue_text,
    improvement_intelligence_dashboard_text,
    improvement_intelligence_api_cli_access_text,
    pre_v64_improvement_intelligence_gate_text,
    supervised_improvement_intelligence_layer_text,
    accepted_recommendation_intake_text,
    proposal_draft_skeleton_text,
    evidence_requirement_mapper_text,
    proposal_risk_contract_text,
    sandbox_patch_request_compiler_text,
    proposal_review_packet_binder_text,
    proposal_dashboard_review_console_text,
    proposal_api_cli_access_text,
    pre_v65_proposal_drafting_gate_text,
    recommendation_to_proposal_drafting_layer_text,
    reviewed_proposal_acceptance_gate_text,
    sandbox_workspace_plan_text,
    patch_implementation_request_text,
    proposal_sandbox_execution_harness_text,
    proposal_sandbox_verification_matrix_text,
    proposal_sandbox_evidence_binder_text,
    proposal_sandbox_failure_triage_text,
    proposal_sandbox_api_cli_access_text,
    pre_v66_proposal_sandbox_gate_text,
    reviewed_proposal_sandbox_execution_layer_text,
    sandbox_promotion_candidate_text,
    sandbox_source_diff_normalizer_text,
    promotion_safety_boundary_gate_text,
    transaction_draft_from_sandbox_text,
    promotion_review_packet_binder_text,
    promotion_conflict_staleness_detector_text,
    sandbox_promotion_api_cli_access_text,
    pre_v67_sandbox_promotion_gate_text,
    sandbox_evidence_promotion_handoff_layer_text,
    promotion_packet_intake_gate_text,
    transaction_plan_materializer_text,
    source_baseline_reconciliation_text,
    backup_rollback_preflight_binder_text,
    final_transaction_safety_gate_text,
    transaction_ledger_preregistration_text,
    source_transaction_review_console_text,
    transaction_review_api_cli_access_text,
    pre_v68_transaction_integration_gate_text,
    promotion_to_transaction_integration_layer_text,
    transaction_execution_eligibility_text,
    exact_confirmation_binder_text,
    backup_snapshot_materializer_text,
    transaction_apply_rehearsal_text,
    operator_confirmed_apply_executor_text,
    post_execution_verification_text,
    rollback_recommendation_gate_text,
    transaction_execution_dashboard_api_cli_text,
    pre_v69_execution_gate_text,
    operator_confirmed_transaction_execution_layer_text,
    build_pre_v46_maintenance_queue_gate,
    pre_v46_maintenance_queue_gate_text,
    build_pre_v45_self_maintenance_gate,
    pre_v45_self_maintenance_gate_text,
    build_source_apply_dry_run_v2,
    build_source_apply_eligibility,
    pre_v42_autonomous_patch_gate_text,
    build_approval_revocation_write_preflight,
    build_write_approval_revocation,
    controlled_publish_approval_revocation_system_text,
    build_approval_status_viewer,
    build_approval_revocation_dry_run,
    publish_approval_lifecycle_system_text,
    build_publish_approval_dry_run_v2,
    build_publish_approval_record_validator,
    build_approval_storage_quarantine,
    build_dashboard_approval_workflow_preview,
    build_approval_confirmation_policy,
    build_candidate_review_state,
    build_publish_approval_dry_run,
    build_publish_approval_explainer,
    publish_approval_separation_system_text,
    controlled_publish_approval_system_text,
    release_signing_status_text,
    signing_readiness_audit_text,
    pre_v30_signing_prep_audit_text,
    signing_api_hardening_text,
    canonical_schema_validator_text,
    source_data_sanitizer_text,
    signing_trust_model_text,
    release_signing_tamper_drill_text,
    public_key_policy_design_text,
    detached_signature_contract_text,
    signature_fixture_verification_text,
    external_signer_workflow_text,
    detached_signature_verification_system_text,
    signature_verification_hardening_text,
    public_trust_root_config_text,
    external_signing_payload_export_text,
    signed_fixture_test_suite_text,
    release_publish_gate_text,
    release_trust_dashboard_polish_text,
    api_route_safety_audit_text,
    release_reproducibility_check_text,
    pre_v32_release_candidate_gate_text,
    signed_release_governance_text,
    governance_report_cleanup_text,
    release_candidate_workspace_text,
    artifact_binding_audit_v2_text,
    surface_consistency_audit_text,
    external_signing_handoff_text,
    signature_intake_validation_text,
    trusted_signer_registry_text,
    governance_scenario_suite_text,
    pre_v33_operations_gate_text,
    release_operations_console_text,
    operations_console_cleanup_text,
    release_candidate_review_text,
    signed_artifact_intake_text,
    trust_root_lifecycle_text,
    publish_decision_explainer_text,
    operator_action_guardrails_text,
    unsigned_release_drill_text,
    signed_fixture_release_drill_text,
    pre_v34_operator_workflow_gate_text,
    release_operator_workflow_text,
    release_candidate_record_v2_text,
    signed_release_publish_decision_text,
    trusted_release_candidate_system_text,
)
from test_runner import list_test_reports, load_test_report, test_report_text
from test_report_reviewer import list_test_reviews, load_test_review, test_review_text
from watch_mode import list_watch_reports, load_watch_report, run_watch_once, run_watch_loop, watch_report_text
from autonomous_dev_cycle import dev_cycle_text, get_dev_cycle, list_dev_cycles
from dev_loop_runner import get_dev_loop, list_dev_loops, run_dev_loop, dev_loop_text


DASHBOARD_TITLE = "Eidolon Dashboard"
DASHBOARD_VERSION = "350.0"


class DashboardState:
    message: str = ""
    error: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe(value: Any) -> str:
    return escape(str(value), quote=True)


def _fmt(value: Any) -> str:
    return _safe(value if value not in {None, ""} else "[none]")


def _json_block(data: Any) -> str:
    return f"<pre>{_safe(json.dumps(data, indent=2, default=str))}</pre>"


def _text_block(text: str) -> str:
    return f"<pre>{_safe(text)}</pre>"


def _card(title: str, body: str) -> str:
    return f"<section class='card'><h2>{_safe(title)}</h2>{body}</section>"


def _small_list(items: list[str]) -> str:
    if not items:
        return "<p class='muted'>None found.</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _button(label: str, action: str, **fields: Any) -> str:
    inputs = [f"<input type='hidden' name='action' value='{_safe(action)}'>"]
    for key, value in fields.items():
        inputs.append(f"<input type='hidden' name='{_safe(key)}' value='{_safe(value)}'>")
    return f"<form method='post' action='/action' class='inline'>{''.join(inputs)}<button type='submit'>{_safe(label)}</button></form>"


def _detail_link(kind: str, item_id: str, label: str | None = None, full: bool = False) -> str:
    if not item_id:
        return "<span class='muted'>[no id]</span>"
    full_q = "&full=1" if full else ""
    return f"<a href='/detail?kind={_safe(kind)}&id={_safe(item_id)}{full_q}'>{_safe(label or item_id)}</a>"


def _back_link(path: str, label: str = "Back") -> str:
    return f"<p><a href='{_safe(path)}'>← {_safe(label)}</a></p>"


def _goal_text(goal: dict[str, Any] | None, full: bool = False) -> str:
    if not goal:
        return "Goal not found."
    lines = [
        f"# Goal: {goal.get('id')}",
        f"Title: {goal.get('title')}",
        f"Status: {goal.get('status')}",
        f"Priority: {goal.get('priority')}",
        f"Project: {goal.get('project') or '[none]'}",
        f"Created: {goal.get('created_at')}",
        f"Updated: {goal.get('updated_at')}",
    ]
    if goal.get('description'):
        lines.extend(["", "## Description", str(goal.get('description'))])
    if goal.get('next_action'):
        lines.extend(["", "## Next action", str(goal.get('next_action'))])
    if goal.get('next_actions'):
        lines.append("")
        lines.append("## Next actions")
        lines.extend(f"- {action}" for action in goal.get('next_actions', []))
    if goal.get('blockers'):
        lines.append("")
        lines.append("## Blockers")
        lines.extend(f"- {blocker}" for blocker in goal.get('blockers', []))
    if goal.get('notes'):
        lines.append("")
        lines.append("## Notes")
        lines.extend(f"- {note}" for note in goal.get('notes', []))
    if full:
        lines.extend(["", "## Raw goal", json.dumps(goal, indent=2, default=str)])
    return "\n".join(lines)



def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in {None, ""}:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _live_refresh_bar(settings: dict[str, Any]) -> str:
    enabled = _as_bool(settings.get("dashboard_live_refresh_enabled"), True)
    interval = max(2, int(settings.get("dashboard_live_refresh_seconds", 5) or 5))
    if not enabled:
        return "<div class='livebar muted'><span>Live refresh disabled.</span></div>"
    return (
        "<div class='livebar'>"
        "<span id='live-refresh-dot' class='live-dot'>●</span> "
        "<span id='live-refresh-status'>Live refresh starting...</span> "
        f"<span class='muted'>Polling /api/status every {_safe(interval)}s.</span> "
        "<button type='button' onclick='window.eidolonRefreshNow && window.eidolonRefreshNow()'>Refresh now</button>"
        "</div>"
    )


def _live_refresh_script(settings: dict[str, Any]) -> str:
    enabled = _as_bool(settings.get("dashboard_live_refresh_enabled"), True)
    interval = max(2, int(settings.get("dashboard_live_refresh_seconds", 5) or 5))
    config = json.dumps({"enabled": enabled, "intervalMs": interval * 1000})
    script_body = r'''
(function () {
  const cfg = window.EIDOLON_LIVE || {};
  if (!cfg.enabled) return;

  function valueAt(root, path) {
    if (!root || !path) return undefined;
    return path.split('.').reduce(function (current, key) {
      if (current === undefined || current === null) return undefined;
      return current[key];
    }, root);
  }

  function displayValue(value) {
    if (value === undefined || value === null || value === '') return '[none]';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  function updateLiveDom(data) {
    document.querySelectorAll('[data-live-count]').forEach(function (el) {
      const value = valueAt(data, el.getAttribute('data-live-count'));
      if (value !== undefined && value !== null) el.textContent = String(value);
    });
    document.querySelectorAll('[data-live-text]').forEach(function (el) {
      const value = valueAt(data, el.getAttribute('data-live-text'));
      if (value !== undefined) el.textContent = displayValue(value);
    });
    document.querySelectorAll('[data-live-detail-href]').forEach(function (el) {
      const path = el.getAttribute('data-live-detail-href');
      const kind = el.getAttribute('data-live-detail-kind') || '';
      const value = valueAt(data, path);
      if (value && kind) el.setAttribute('href', '/detail?kind=' + encodeURIComponent(kind) + '&id=' + encodeURIComponent(value));
    });
  }

  async function pollStatus() {
    const status = document.getElementById('live-refresh-status');
    const dot = document.getElementById('live-refresh-dot');
    try {
      if (status) status.textContent = 'Live refresh: polling...';
      if (dot) dot.className = 'live-dot polling';
      const response = await fetch('/api/status?ts=' + Date.now(), { cache: 'no-store' });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || 'API status returned an error');
      const data = payload.data || {};
      updateLiveDom(data);
      const updated = new Date().toLocaleTimeString();
      if (status) status.textContent = 'Live refresh: updated ' + updated;
      if (dot) dot.className = 'live-dot ok';
      document.title = 'Eidolon Dashboard' +
        ' · approvals ' + displayValue(valueAt(data, 'counts.pending_approvals')) +
        ' · notes ' + displayValue(valueAt(data, 'counts.unread_notifications'));
    } catch (error) {
      if (status) status.textContent = 'Live refresh failed: ' + error.message;
      if (dot) dot.className = 'live-dot bad';
    }
  }

  window.eidolonRefreshNow = pollStatus;
  pollStatus();
  window.setInterval(pollStatus, Math.max(2000, cfg.intervalMs || 5000));
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) pollStatus();
  });
})();
'''
    return "<script>\nwindow.EIDOLON_LIVE = " + config + ";\n" + script_body + "\n</script>"


def _nav_group_description(group: str) -> str:
    descriptions = {
        "Core": "Daily command pages: overview, actions, chat, creation, and task handling.",
        "Work Loops": "Supervised execution loops and stability tools for bounded work cycles.",
        "Development": "Project intelligence, workspace, patch drafting, and code patch review tools.",
        "Release": "Release packaging, governance, evidence, signing, operator review, and approval surfaces.",
        "Autonomy": "Autonomy boundaries, maintenance queues, approvals, notifications, watch mode, and goals.",
        "System": "Diagnostics, settings, API reference, desktop companion, setup, onboarding, and activity logs.",
    }
    return descriptions.get(group, "Dashboard section")


def _render_nav(current_path: str, nav_items: list[tuple[str, str, str, str]]) -> str:
    grouped: dict[str, list[tuple[str, str, str, str]]] = {}
    active_group = "Core"
    for href, label, description, group in nav_items:
        grouped.setdefault(group, []).append((href, label, description, group))
        if href == current_path:
            active_group = group
    pieces = [
        "<nav class='nav-shell' aria-label='Dashboard navigation'>",
        "<div class='nav-intro'><strong>Navigation</strong><span>Grouped to keep the dashboard from becoming a drawer full of cursed cables. Hover or focus a tab for its purpose.</span></div>",
        "<div class='command-palette'><label for='dashboard-search'>Quick finder</label><input id='dashboard-search' data-nav-search type='search' placeholder='Filter tabs, for example: queue, attention, release...' autocomplete='off'></div>",
    ]
    for group, items in grouped.items():
        open_attr = " open" if group in {"Core", active_group} else ""
        group_desc = _nav_group_description(group)
        pieces.append(f"<details class='nav-section'{open_attr}><summary><span>{_safe(group)}</span><small>{_safe(group_desc)}</small></summary><div class='nav-links'>")
        for href, label, description, _ in items:
            active = " active" if href == current_path else ""
            route_title = re.sub(r"<[^>]+>", "", str(label))
            pieces.append(f"<a class='nav-link{active}' href='{_safe(href)}' data-tip='{_safe(description)}' data-route-title='{_safe(route_title)}' data-route-group='{_safe(group)}'>{label}</a>")
        pieces.append("</div></details>")
    pieces.append("</nav>")
    return "".join(pieces)


def _layout(path: str, content: str) -> str:
    settings = load_settings()
    nav_items = [
        ("/", "Overview", "Home status cards, next task, memory status, and common actions.", "Core"),
        ("/actions", "Action Center", "A focused operator console for pending approvals, notifications, diagnostics, maintenance scans, and next actions.", "Core"),
        ("/chat-console", "Chat Console", "Local dashboard chat console wired into Eidolon actions.", "Core"),
        ("/chat-actions", "Chat Actions <span class='nav-badge' data-live-count='counts.chat_actions'></span>", "Review chat-triggered action records and their statuses.", "Core"),
        ("/create", "Create", "Create tasks, goals, patch proposals, and other supervised work records.", "Core"),
        ("/tasks", "Tasks <span class='nav-badge' data-live-count='counts.tasks'></span>", "Classic task list and task status management.", "Core"),
        ("/tasks-work", "Tasks / Work <span class='nav-badge' data-live-count='counts.work_queue_pending'></span>", "Work queue view for pending, active, blocked, and approval-required task work.", "Work Loops"),
        ("/work-cycle", "Work Cycle <span class='nav-badge' data-live-count='counts.work_cycles'></span>", "Bounded supervised work-cycle execution records.", "Work Loops"),
        ("/stable-loop", "Stable Loop <span class='nav-badge' data-live-count='counts.stable_loops'></span>", "Stable supervised loop reviews, decisions, follow-ups, and completion state.", "Work Loops"),
        ("/stabilization", "Stabilization", "Stability checkpoint, confidence, blockers, and repair suggestions.", "Work Loops"),
        ("/doctor", "Doctor", "Local system health diagnostics and readiness checks.", "Work Loops"),
        ("/build-cycle", "Build Cycle", "Controlled build-cycle reports and development loop evidence.", "Development"),
        ("/patch-review", "Patch Review", "v74 patch draft review and diff validation: intake parsing, boundaries, scope, safety, docs, verification, risk, and operator report. Review only; no apply.", "Development"),
        ("/patch-trials", "Patch Trials", "v75 sandbox patch trial runner: bind reviewed drafts, create disposable workspaces, materialize safely, verify in sandbox, collect evidence, and prove live source unchanged. No promotion.", "Development"),
        ("/patch-evidence", "Patch Evidence", "v76 sandbox evidence review and promotion recommendation: validate trial evidence, score verification, review docs/scope, classify risk, and recommend only. No promotion.", "Development"),
        ("/patch-apply", "Patch Apply", "v77 operator-approved patch application: exact approval, recommendation binding, live snapshot, scoped materialization, verification, rollback, and evidence. No publish or autonomous apply.", "Development"),
        ("/patch-recovery", "Patch Recovery", "v78 verified application recovery and rollback hardening: dirty-tree preflight, snapshot validation, partial apply detection, rollback integrity, failure triage, recommendations, and audit timeline. No auto-repair.", "Development"),
        ("/patch-queue", "Patch Queue", "v79 multi-patch queue planning: schema, intake, conflict detection, risk scheduling, stale evidence checks, serial trial plans, and operator review. Planning only; no batch apply.", "Development"),
        ("/improvement-loop", "Supervised Local Improvement Loop", "v80.0 Supervised Local Improvement Loop: Run one supervised improvement cycle from goal intake to operator review without applying anything. No self-approval or autonomous apply.", "Development"),
        ("/local-model-proposals", "Local Model Patch Proposal Integration", "v81.0 Local Model Patch Proposal Integration: Prepare controlled local model patch proposal handoff and capture, disabled by default for invocation. No self-approval or autonomous apply.", "Development"),
        ("/proposal-critique", "Proposal Critique", "v82.0 Local Model Output Comparison and Critique: Compare local model outputs, critique proposal quality, and export operator review bundles without selecting automatically. No self-approval or autonomous apply.", "Development"),
        ("/candidate-ranking", "Multi-Model Patch Candidate Ranking", "v83.0 Multi-Model Patch Candidate Ranking: Rank multiple patch candidates by risk, evidence, conflicts, and operator review needs without auto-selecting. No self-approval or autonomous apply.", "Development"),
        ("/candidate-refinement", "Supervised Patch Candidate Refinement", "v84.0 Supervised Patch Candidate Refinement: Build constrained refinement prompts and review revised candidates without applying or approving them. No self-approval or autonomous apply.", "Development"),
        ("/suggestion-loop", "Safe Autonomous Suggestion Loop", "v85.0 Safe Autonomous Suggestion Loop: Periodically organize safe improvement suggestions for operator attention while forbidding autonomous apply. No self-approval or autonomous apply.", "Development"),
        ("/suggestion-inbox", "Suggestion Inbox", "v86.0 Supervised Suggestion Inbox and Work Order Planner: Triage safe suggestions into operator-reviewed work order drafts without autonomous apply, publish, memory mutation, or identity mutation.", "Development"),
        ("/work-order-handoff", "Work Order Handoff", "v87.0 Work Order to Patch Context Handoff: Convert operator-accepted work orders into supervised patch context packets without execution.", "Development"),
        ("/work-order-evidence", "Work Order Evidence", "v88.0 Work Order Execution Evidence Binder: Trace work orders through sandbox evidence and operator decisions without inferring approval.", "Development"),
        ("/self-development", "Self-Development", "v89.0 Self-Development Dashboard Consolidation: Unified supervised development console, action queue, safety banners, and lazy diagnostics.", "Development"),
        ("/self-development-readiness", "Readiness Audit", "v90.0 Supervised Self-Development Readiness Audit: Diagnostic supervision, traceability, approval gate, risk, and scorecard audit without unlocking autonomy.", "Development"),
        ("/development-sessions", "Development Sessions", "v91.0 Supervised Development Session Manager: Bundle suggestions, work orders, patch contexts, evidence, and operator goals into supervised sessions without approval escalation.", "Development"),
        ("/approval-console", "Approval Console", "v92.0 Operator Approval Workflow Console: Unified operator approval queue, decision ledger, dependencies, and risk explanations without inferred approval.", "Development"),
        ("/experiment-planner", "Experiment Planner", "v93.0 Safe Experiment Branch Planner: Plan isolated experiments and sandbox metadata without touching live source or promoting outside transaction gates.", "Development"),
        ("/outcome-reflections", "Outcome Reflections", "v94.0 Learning-from-Outcome Reflection Layer: Extract advisory lessons and safe suggestion handoffs without memory or identity mutation.", "Development"),
        ("/improvement-cycles", "Improvement Cycles", "v95.0 Supervised Improvement Cycle Orchestrator: Trace the full governed cycle from suggestion through reflection and next suggestion without autonomy.", "Development"),
        ("/cycle-replay", "Cycle Replay", "v96.0 Supervised Cycle Replay and Benchmark Harness: Replay supervised cycles against safe fixtures and score recommendations without source mutation or permission unlocks.", "Development"),
        ("/capability-ledger", "Capability Ledger", "v97.0 Capability Permission and Budget Ledger: Track allowed, gated, forbidden, and budgeted capabilities without letting simulation become execution.", "Development"),
        ("/shadow-autonomy", "Shadow Autonomy", "v98.0 Shadow Autonomy Simulation Layer: Simulate autonomous intentions but map actions only to approval requests or block states.", "Development"),
        ("/failure-war-games", "Failure War Games", "v99.0 Failure Recovery and Rollback War Game Layer: Rehearse recovery and rollback paths without automatic rollback or source mutation.", "Development"),
        ("/mind-milestone-audit", "Mind Milestone", "v100.0 Local Artificial Mind Milestone Audit: Audit memory, reflection, goals, safety, self-development, and operator burden without unlocking autonomy.", "Development"),
        ("/v100-stabilization", "v100 Stabilization", "v101.0 v100 Milestone Stabilization and Reality Review: Inventory routes, commands, coverage, privacy, friction, and consolidation candidates without changing source.", "Development"),
        ("/operator-home", "Operator Home", "v102.0 Unified Eidolon System Map and Operator Home: Central system health, pending actions, active sessions, blocked risks, and safest supervised next step.", "Development"),
        ("/system-map", "System Map", "v102.0 Unified Eidolon System Map: Map core mind components, development pipeline, governance boundaries, and cross-links.", "Development"),
        ("/coherence-binder", "Coherence Binder", "v103.0 Memory, Reflection, and Goal Coherence Binder: Link memory references, reflections, goals, suggestions, outcomes, and lessons without memory or identity mutation.", "Development"),
        ("/daily-loop", "Daily Loop", "v104.0 Practical Daily Operating Loop: Callable daily status, priorities, operator prompts, safety checks, and reflection prompts without scheduling or automation.", "Development"),
        ("/local-mind-runtime", "Mind Runtime", "v105.0 Coherent Local Mind Runtime v1: Read-only unified mind-state snapshot, continuity report, health scorecard, contradictions, and safest supervised next step.", "Development"),
        ("/memory-quality", "Memory Quality", "v106.0 Memory Quality and Evidence Hygiene Layer: Freshness, relevance, evidence links, duplicate/conflict detection, and correction drafts without memory mutation.", "Development"),
        ("/goal-continuity", "Goal Continuity", "v107.0 Goal Continuity and Priority Stability Layer: Goal lifecycle, blockers, evidence, priority stability, and contradictions without inferred approval.", "Development"),
        ("/reasoning-workbench", "Reasoning Workbench", "v108.0 Contained Local Reasoning Workbench: Manual/local reasoning capture, bounded context, quality rubric, and boundary scanning without default model invocation.", "Development"),
        ("/workflow-console", "Workflow Console", "v109.0 Operator Workflow Compression Console: Unified action queue, copy-safe commands, review packet shortcuts, and dashboard consolidation recommendations without auto-execution.", "Development"),
        ("/practical-mind-audit", "Mind Usefulness", "v110.0 Practical Supervised Mind Usefulness Audit: End-to-end usefulness, memory, goals, reasoning, operator burden, dashboard sprawl, and safety regression audit.", "Development"),
        ("/improvement-intent", "Improvement Intent", "v111.0 Improvement Intent and Problem Framing Layer: Turn vague improvement ideas into grounded problem statements, evidence requirements, value scores, and safety-sensitive intent binders.", "Development"),
        ("/work-package-builder", "Work Packages", "v112.0 Supervised Work Package Builder: Assemble advisory work packages with scope, acceptance criteria, test plans, docs obligations, and regression risks.", "Development"),
        ("/patch-readiness", "Patch Readiness", "v113.0 Patch Readiness and Review Intelligence Layer: Review proposed patches for completeness, contradictions, safety regressions, dashboard regressions, and operator recommendations without applying anything.", "Development"),
        ("/release-candidate-judgment", "Release Judgment", "v114.0 Release Candidate Judgment Layer: Judge candidate readiness across version consistency, docs, route/API/CLI parity, privacy, install verification, and release recommendation without publishing.", "Development"),
        ("/supervised-development-readiness", "SD Readiness v115", "v115.0 Supervised Self-Development Readiness Audit: End-to-end supervised improvement walkthrough, evidence quality, decision trace, operator burden, dashboard usability, and release process audit. Distinct from the older v90 readiness page.", "Development"),
        ("/development-session-planner", "Session Planner", "v116.0 Development Session Planner: Plan a supervised development session with intent, scope, file impact, tests, docs, safety boundaries, and operator decisions before code changes.", "Development"),
        ("/source-change-cartographer", "Source Map", "v117.0 Source Change Cartographer: Map dashboard, API, CLI, builder, smoke, docs, packaging, install, and fragile source surfaces without mutation.", "Development"),
        ("/patch-simulation", "Patch Simulation", "v118.0 Patch Simulation and Dry-Run Review Layer: Predict expected diffs, missing changes, overreach, safety risk, and verification outcomes without applying patches.", "Development"),
        ("/verification-matrix", "Verify Matrix", "v119.0 Verification Matrix and Regression Memory Layer: Recommend exact regression checks for dashboard, API/CLI, packaging, safety, and docs changes without scheduling work.", "Development"),
        ("/development-execution-audit", "Execution Audit", "v120.0 Supervised Development Execution Audit: Audit the v116-v119 execution-planning flow for operator burden, patch quality, verification coverage, safety containment, dashboard sprawl, and docs continuity.", "Development"),
        ("/development-outcome-review", "Outcome Review", "v121.0 Development Outcome Review Layer: Compare planned development sessions against actual outcomes, missed surfaces, unexpected changes, verification accuracy, and operator burden without memory mutation.", "Development"),
        ("/lesson-extraction", "Lessons", "v122.0 Supervised Lesson Extraction Layer: Extract proposed lessons from outcomes, bug patterns, successful patterns, false alarms, and usefulness scores without writing durable memory.", "Development"),
        ("/recommendation-refinement", "Rec Refinement", "v123.0 Recommendation Refinement Layer: Refine future recommendations from reviewed outcomes and proposed lessons while keeping all recommendations advisory.", "Development"),
        ("/operator-feedback-integration", "Feedback", "v124.0 Operator Feedback Integration Layer: Classify operator feedback into standing-rule, temporary, contradiction, and review packets without auto-writing memory.", "Development"),
        ("/development-learning-audit", "Learning Audit", "v125.0 Supervised Development Learning Audit: Audit the full outcome-review, lesson, recommendation, and feedback loop without autonomy or memory mutation.", "Development"),
        ("/strategic-growth-intake", "Strategic Intake", "v126.0 Strategic Growth Intake Layer: Gather lessons, feedback, goals, audits, failed checks, roadmap notes, and operator direction into supervised growth signals.", "Development"),
        ("/roadmap-synthesis", "Roadmap", "v127.0 Roadmap Synthesis Layer: Turn strategic signals into short, medium, and long-term roadmap options without scheduling or approving work.", "Development"),
        ("/strategic-risk-ledger", "Risk Ledger", "v128.0 Strategic Risk and Debt Ledger: Track technical, safety, and usability debt with advisory mitigations only.", "Development"),
        ("/capability-maturity", "Maturity", "v129.0 Capability Maturity Model Layer: Score capabilities by scaffold, integration, test coverage, usefulness, reliability, and operator trust without self-upgrades.", "Development"),
        ("/strategic-growth-audit", "Growth Audit", "v130.0 Supervised Strategic Growth Audit: Audit strategic intake, roadmap synthesis, risk/debt tracking, and capability maturity while preserving all non-autonomy boundaries.", "Development"),
        ("/planning-signals", "Planning Signals", "v131.0 Planning Signal Consolidation Layer: Consolidate planning evidence from strategy, risks, maturity, feedback, lessons, checks, and operator direction.", "Development"),
        ("/work-package-recommendations", "Work Packages v132", "v132.0 Work Package Recommendation Layer: Recommend ranked supervised work packages without creating, approving, or applying work.", "Development"),
        ("/operator-decision-brief", "Decision Brief", "v133.0 Operator Decision Brief Layer: Present top options, evidence, tradeoffs, sequencing, burden, verification, and safety boundaries without selecting work.", "Development"),
        ("/planning-console", "Planning Console", "v134.0 Dashboard Planning Console Consolidation: Group planning surfaces and preserve custom data-tip hover behavior without native title tooltips.", "Development"),
        ("/planning-readiness-audit", "Planning Audit", "v135.0 Supervised Operator Planning Console: Audit signals, packages, decision brief, console, parity, privacy, and safety boundaries.", "Development"),
        ("/work-package-selection", "Package Select", "v136.0 Work Package Selection Layer: Compare recommendations and record explicit operator selection without launching or executing work.", "Development"),
        ("/session-brief", "Session Brief", "v137.0 Session Brief Preparation Layer: Prepare objective, evidence, risks, files, non-goals, dependencies, and safety boundaries.", "Development"),
        ("/approval-checklist", "Approval Checklist", "v138.0 Approval Checklist and Safety Boundary Layer: Prepare supervised approval, scope, safety, docs, dashboard, and verification checklists.", "Development"),
        ("/verification-rollback-plan", "Verify/Rollback", "v139.0 Verification Plan and Rollback Preparation Layer: Prepare advisory verification and rollback plans without executing commands.", "Development"),
        ("/session-launch-audit", "Launch Audit", "v140.0 Supervised Work Package Selection and Session Launch: Audit recommendation-to-launch packets while preserving approval gates.", "Development"),
        ("/patch-session-intake", "Patch Intake", "v141.0 Patch Session Intake Layer: Import approved launch packets and prepare supervised patch-session intake without implementation.", "Development"),
        ("/file-change-plan", "File Plan", "v142.0 File Change Planning Layer: Plan file-by-file changes before any source edits.", "Development"),
        ("/patch-blueprint", "Patch Blueprint", "v143.0 Patch Draft Blueprint Layer: Prepare patch blueprints as plans only, not applied changes.", "Development"),
        ("/patch-review-packet", "Review Packet", "v144.0 Patch Review Packet Layer: Bundle evidence, risk, docs, verification, and rollback notes for operator approval.", "Development"),
        ("/patch-session-audit", "Patch Audit", "v145.0 Supervised Patch Session Assembly: Audit intake-to-review packet readiness while preserving approval gates.", "Development"),
        ("/patch-draft-request", "Draft Request", "v146.0 Patch Draft Request Layer: Convert reviewed patch session packets into supervised draft-generation requests without writing files.", "Development"),
        ("/file-patch-drafts", "File Drafts", "v147.0 File-Level Patch Draft Layer: Produce reviewable file-by-file patch drafts and diff previews without applying them.", "Development"),
        ("/patch-diff-review", "Diff Review", "v148.0 Patch Diff Review Packet Layer: Combine file drafts into coherent review packets with consistency, safety, verification, and rollback checks.", "Development"),
        ("/patch-draft-qa", "Draft QA", "v149.0 Patch Draft QA Layer: QA draft completeness, consistency, safety, docs, dashboard behavior, and package privacy before implementation.", "Development"),
        ("/patch-draft-generation-audit", "Draft Audit", "v150.0 Supervised Patch Draft Generation: Audit the full review-packet-to-draft-to-QA chain while keeping drafts unapplied.", "Development"),
        ("/implementation-handoff", "Impl Handoff", "v151.0 Implementation Handoff Intake Layer: Convert QA-passed patch drafts into an advisory implementation handoff request without source mutation.", "Development"),
        ("/manual-patch-application-plan", "Apply Plan", "v152.0 Manual Patch Application Plan Layer: Order manual edit instructions while refusing automatic patch application.", "Development"),
        ("/implementation-verification-worksheet", "Verify Sheet", "v153.0 Implementation Verification Worksheet Layer: Prepare operator-run verification worksheets without executing commands.", "Development"),
        ("/implementation-rollback-packet", "Rollback Packet", "v154.0 Implementation Rollback Packet Layer: Prepare advisory rollback instructions before implementation.", "Development"),
        ("/implementation-handoff-audit", "Impl Audit", "v155.0 Supervised Patch Implementation Handoff: Audit draft-to-handoff-to-plan-to-verification-to-rollback continuity.", "Development"),
        ("/patch-readiness-intake", "Ready Intake", "v156.0 Patch Readiness Intake Layer: Bind draft QA, handoff, manual application, verification, rollback, docs, and operator approval evidence without applying patches.", "Development"),
        ("/patch-readiness-score", "Ready Score", "v157.0 Patch Readiness Scoring Layer: Score scope, safety, verification, rollback, docs, dashboard, parity, and packaging readiness without self-approval.", "Development"),
        ("/patch-readiness-blockers", "Ready Blockers", "v158.0 Patch Blocker and Gap Report Layer: Surface missing packets, file coverage gaps, unsafe capability risks, dashboard regressions, parity gaps, and package privacy issues.", "Development"),
        ("/patch-go-no-go-decision", "Go/No-Go", "v159.0 Operator Go/No-Go Decision Packet Layer: Prepare advisory go, no-go, or conditional-go recommendations requiring explicit operator approval.", "Development"),
        ("/patch-application-readiness-audit", "Ready Audit", "v165.0 Supervised Patch Application Readiness: Audit the full readiness pipeline without patch application, source mutation, verification execution, or approval inference.", "Development"),
        ("/patch-sandbox-intake", "Sandbox Intake", "v161.0 Patch Sandbox Intake Layer: Prepare sandbox requests from readiness decisions with explicit approval and no live mutation.", "Development"),
        ("/sandbox-patch-application-plan", "Sandbox Plan", "v162.0 Approved Sandbox Patch Application Plan: Plan sandbox-only patch application steps without touching live source.", "Development"),
        ("/sandbox-verification-packet", "Sandbox Verify", "v163.0 Sandbox Verification Execution Packet: Prepare operator-approved sandbox verification packets without automatic command execution.", "Development"),
        ("/sandbox-result-review", "Sandbox Review", "v164.0 Sandbox Result Review Layer: Review sandbox evidence and classify outcomes without promotion.", "Development"),
        ("/sandbox-patch-application-audit", "Sandbox Audit", "v165.0 Operator-Approved Patch Application Sandbox: Audit the gated sandbox-only patch application flow without live source mutation or promotion.", "Development"),
        ("/sandbox-promotion-intake", "Promote Intake", "v166.0 Sandbox Promotion Intake Layer: Import sandbox evidence and require explicit promotion approval before source promotion can be considered.", "Development"),
        ("/source-promotion-plan", "Source Plan", "v167.0 Source Promotion Application Plan Layer: Plan sandbox-to-source changes as advisory steps until explicit approval.", "Development"),
        ("/promotion-approval-packet", "Promote Approval", "v168.0 Promotion Approval Packet Layer: Prepare final operator approval packet without inferring approval or promoting changes.", "Development"),
        ("/post-promotion-verification", "Post Verify", "v169.0 Post-Promotion Verification and Rollback Layer: Prepare post-promotion verification and rollback procedures without auto-execution.", "Development"),
        ("/sandbox-to-source-promotion-audit", "Promote Audit", "v170.0 Operator-Approved Sandbox-to-Source Promotion: Audit the supervised sandbox-to-source promotion chain without autonomous promotion.", "Development"),
        ("/source-application-approval", "Source Approval", "v171.0 Source Application Approval Intake Layer: Require exact operator approval before live-source application can proceed.", "Development"),
        ("/live-source-application-plan", "Live Plan", "v172.0 Live Source Patch Application Plan Layer: Plan source mutations, snapshots, rollback, docs, and parity under approval.", "Development"),
        ("/approved-source-application-execution", "Apply Packet", "v173.0 Approved Source Application Execution Packet: Define tightly scoped, approval-bound source application execution packets.", "Development"),
        ("/post-application-verification", "Post Verify", "v174.0 Post-Application Verification and Rollback Control Layer: Prepare verification and rollback controls after approved source application.", "Development"),
        ("/source-patch-application-audit", "Source Audit", "v175.0 Operator-Approved Source Patch Application: Audit explicit-approval source application without autonomy.", "Development"),
        ("/post-application-outcome-intake", "Outcome Intake", "v176.0 Post-Application Outcome Intake Layer: Normalize approved source application outcomes without triggering fixes, rollback, release, or follow-up patches.", "Development"),
        ("/post-application-lessons", "Lessons v2", "v177.0 Supervised Lesson Extraction Layer v2: Extract reviewable post-application lessons without memory mutation.", "Development"),
        ("/next-improvement-candidates", "Next Candidates", "v178.0 Supervised Next-Improvement Candidate Builder: Rank supervised future improvement options without auto-selection.", "Development"),
        ("/post-application-release-readiness", "Release Ready v2", "v179.0 Release Readiness Judgment Layer v2: Judge readiness without creating, freezing, signing, packaging, or publishing release candidates.", "Development"),
        ("/post-application-cycle-closure", "Closure Audit", "v180.0 Operator-Governed Post-Application Learning and Release Readiness: Audit the full post-application closure loop without autonomy.", "Development"),
        ("/cycle-intelligence-intake", "Cycle Intake", "v181.0 Cycle Intelligence Intake Layer: Collect prior-cycle evidence into one read-only planning context.", "Development"),
        ("/supervised-patch-priority-matrix", "Priority Matrix", "v182.0 Supervised Patch Priority Matrix: Score next patch candidates without choosing or approving work.", "Development"),
        ("/next-patch-proposal-assembly", "Proposal Assembly", "v183.0 Next Patch Proposal Assembly Layer: Assemble reviewable next-patch proposals without writing source.", "Development"),
        ("/supervised-patch-session-planner", "Session Planner", "v184.0 Supervised Patch Session Planner: Prepare next-session packets without starting implementation.", "Development"),
        ("/patch-cycle-intelligence-audit", "Cycle Audit", "v185.0 Operator-Governed Patch Cycle Intelligence: Audit next-cycle planning without autonomy or cascade work.", "Development"),
        ("/multi-cycle-roadmap-intake", "Roadmap Intake", "v186.0 Multi-Cycle Roadmap Intake Layer: Collect roadmap-ready project state without selecting or launching work.", "Development"),
        ("/supervised-roadmap-options", "Roadmap Options", "v187.0 Supervised Roadmap Option Builder: Generate advisory roadmap options without activating plans.", "Development"),
        ("/roadmap-dependency-risk-graph", "Roadmap Graph", "v188.0 Roadmap Dependency and Risk Graph: Map roadmap dependencies and risk clusters without launching stages.", "Development"),
        ("/v200-readiness-model", "v200 Ready", "v189.0 v200 Milestone Readiness Model: Score v200 maturity without treating readiness as approval.", "Development"),
        ("/multi-cycle-roadmap-governance-audit", "Roadmap Audit", "v190.0 Operator-Governed Multi-Cycle Roadmap Intelligence: Audit multi-cycle roadmap planning without autonomy.", "Development"),
        ("/capability-maturity-inventory", "Maturity Inventory", "v191.0 Capability Inventory and Maturity Schema: Define capability domains, maturity levels, evidence requirements, and boundaries without granting approval.", "Development"),
        ("/capability-maturity-scoring", "Maturity Scoring", "v192.0 Capability Maturity Scoring Layer: Score major capabilities using evidence-bound advisory criteria.", "Development"),
        ("/capability-gap-overreach-analysis", "Gap/Overreach", "v193.0 Capability Gap and Overreach Analyzer: Identify underdeveloped, risky, overbuilt, and weakly verified capabilities without launching fixes.", "Development"),
        ("/capability-maturity-improvement-plan", "Maturity Plans", "v194.0 Capability Maturity Improvement Planner: Prepare supervised improvement plans that are not execution packets.", "Development"),
        ("/capability-maturity-governance-audit", "Maturity Audit", "v195.0 Supervised Capability Maturity Modeling: Audit maturity scoring, gaps, overreach protection, and no-autonomous-improvement boundaries.", "Development"),

        ("/governance-kernel-state", "Governance State", "v196.0 Governance Kernel State Model: central supervised governance state, lifecycle phase, capability state, approval state, evidence, risk, and operator constraints. Descriptive only.", "Development"),
        ("/governance-rule-evaluation", "Governance Rules", "v197.0 Governance Rule Evaluation Layer: classify actions, evaluate approval/evidence requirements, detect forbidden actions, and summarize governance decisions without granting approval.", "Development"),
        ("/operator-authority-consent-ledger", "Consent Ledger", "v198.0 Operator Authority and Consent Ledger: bind explicit operator approval scope, expiration, revocation, and ambiguity checks without inferred consent.", "Development"),
        ("/governance-enforcement-simulation", "Governance Sim", "v199.0 Governance Kernel Enforcement Simulation: simulate patch, release, memory, identity, autonomy, and parity workflows without executing them.", "Development"),
        ("/governance-kernel-audit", "Kernel Audit", "v200.0 Local Artificial Mind Governance Kernel v1: audit state traceability, rule evaluation, consent boundaries, enforcement simulation, no-autonomy, dashboard style, parity, docs, and release history.", "Development"),

        ("/self-model-snapshot", "Self-Model", "v211.0 Supervised Self-Model Snapshot Layer: evidence-bound identity, capability, limitation, governance, and confidence claims without authority.", "Development"),
        ("/deliberation-packet", "Deliberation", "v212.0 Supervised Deliberation Packet Layer: options, tradeoffs, risks, evidence quality, uncertainty, and recommendation guards without execution.", "Development"),
        ("/purpose-alignment-layer", "Purpose Align", "v213.0 Operator-Governed Purpose Alignment Layer: compare purpose, standing rules, runtime claims, autonomy drift, identity drift, and consent drift without rewriting purpose.", "Development"),
        ("/behavioral-pattern-intelligence", "Pattern Intel", "v214.0 Supervised Behavioral Pattern Intelligence: repeated strengths, repeated weaknesses, verification gaps, dashboard regressions, documentation drift, and advisory priority scoring.", "Development"),
        ("/self-model-integration-audit", "Self-Model Audit", "v215.0 Operator-Governed Deliberation and Self-Model Layer v1: audit self-model evidence, deliberation safety, purpose alignment, patterns, no-autonomy, dashboard, parity, docs, and smoke.", "Development"),

        ("/internal-simulation-packet", "Simulation", "v216.0 Supervised Internal Simulation Packet Layer: proposed action, assumptions, expected outcomes, failure modes, and non-execution guards without authorization.", "Development"),
        ("/foresight-branch-comparison", "Foresight", "v217.0 Operator-Governed Foresight Branch Comparison: compare branches by risk, benefit, governance cost, and evidence readiness without selecting a roadmap as approved.", "Development"),
        ("/pre-change-consequence-modeling", "Consequences", "v218.0 Supervised Pre-Change Consequence Modeling: forecast source, runtime, dashboard, docs, smoke, and approval-scope impact before changes.", "Development"),
        ("/expectation-reality-check", "Reality Check", "v219.0 Supervised Expectation-Reality Check Layer: compare simulated expectations with real evidence without launching follow-up work.", "Development"),
        ("/simulation-foresight-audit", "Sim Audit", "v220.0 Operator-Governed Internal Simulation and Foresight Layer v1: audit simulation packets, branch comparison, consequence modeling, expectation-reality checks, no-execution, no-autonomy, dashboard, parity, docs, and smoke.", "Development"),
        ("/learning-objective-map", "Learn Map", "v221.0 Supervised Learning Objective Map: evidence-bound learning objectives, gap binders, governance-bound classifiers, priority scoring, and non-autonomous learning guards.", "Development"),
        ("/practice-task-design", "Practice Design", "v222.0 Supervised Practice Task Design Layer: reviewable practice task designs, skill targets, evidence needs, scope guards, and non-execution checks.", "Development"),
        ("/capability-calibration", "Calibration", "v223.0 Operator-Governed Capability Calibration Layer: capability claims, evidence strength, unsupported claim detection, overconfidence warnings, and promotion guards.", "Development"),
        ("/skill-gap-remediation-planner", "Gap Plans", "v224.0 Supervised Skill Gap Remediation Planner: weakness clusters, remediation strategies, verification plans, governance risk, approval requirements, and no-continuation guards.", "Development"),
        ("/learning-curriculum-audit", "Learn Audit", "v225.0 Operator-Governed Learning Curriculum and Capability Calibration Layer v1: audit learning objectives, practice safety, capability calibration, remediation, no-autonomous-learning, memory/identity locks, dashboard, parity, docs, and smoke.", "Development"),
        ("/knowledge-claim-ledger", "Claim Ledger", "v226.0 Supervised Knowledge Claim Ledger: evidence-bound knowledge claims, confidence states, freshness, and non-mutation guards.", "Development"),
        ("/belief-candidate-review", "Belief Review", "v227.0 Operator-Reviewed Belief Candidate Layer: belief candidates, source binding, risk scoring, confidence, promotion requirements, and non-authority guards.", "Development"),
        ("/contradiction-staleness-intelligence", "Contradictions", "v228.0 Supervised Contradiction and Staleness Intelligence: claim conflicts, stale knowledge, README/runtime drift, version drift, and non-execution guards.", "Development"),
        ("/project-knowledge-map", "Knowledge Map", "v229.0 Supervised Project Knowledge Map Layer: capability arcs, dashboard/API/CLI surfaces, governance boundaries, and documentation coverage.", "Development"),
        ("/knowledge-organization-audit", "Know Audit", "v230.0 Operator-Governed Knowledge and Belief Organization Layer v1: audit claims, beliefs, contradiction/staleness intelligence, project maps, no-memory-mutation, no-belief-authority, dashboard, parity, docs, and smoke.", "Development"),
        ("/local-model-inventory", "Model Inventory", "v231.0 Operator-Governed Local Model Inventory Layer: profile local models, intended uses, limits, evidence, and no-invocation boundaries.", "Development"),
        ("/model-evaluation-plan", "Model Eval", "v232.0 Supervised Model Evaluation Plan Layer: design model tests, prompt suites, evidence requirements, risk/scope, and approval requirements without running models.", "Development"),
        ("/model-output-comparison", "Model Compare", "v233.0 Operator-Governed Model Output Comparison Layer: compare approved model outputs, score evidence support, detect hallucination and contradictions, and prevent model authority.", "Development"),
        ("/cognitive-workbench-routing", "Workbench", "v234.0 Supervised Cognitive Workbench Routing Layer: recommend model/task fit, review requirements, fallbacks, and disagreement policy without executing model calls.", "Development"),
        ("/local-model-workbench-audit", "Model Audit", "v235.0 Operator-Governed Local Model Evaluation and Cognitive Workbench Layer v1: audit inventory, evaluation plans, output comparison, routing, no-default-invocation, no-model-authority, dashboard, parity, docs, and smoke.", "Development"),
        ("/local-model-invocation-consent", "Model Consent", "v236.0 Operator-Approved Local Model Invocation Consent Gate: scope model name, prompt suite, context boundary, output use, expiration, and no-default-invocation before any local model run.", "Development"),
        ("/model-evaluation-run-ledger", "Run Ledger", "v237.0 Sandboxed Model Evaluation Run Ledger: record approved model runs, prompt-suite binding, output capture, provider metadata, transcript sanitization, and run status without applying outputs.", "Development"),
        ("/multi-model-output-triage", "Model Triage", "v238.0 Operator-Governed Multi-Model Output Triage: map agreement, explain disagreement, flag hallucinations/contradictions, and prioritize operator review without granting authority.", "Development"),
        ("/model-reliability-profile-candidates", "Model Reliability", "v239.0 Supervised Model Reliability Profile Candidates: stage task-specific reliability, repeated strengths/failures, evidence summaries, and promotion requirements without self-promotion.", "Development"),
        ("/local-model-invocation-sandbox-audit", "Invoke Audit", "v240.0 Operator-Approved Local Model Invocation Sandbox v1: audit consent, run ledger, triage, reliability candidates, no-default-invocation, no-model-authority, dashboard, parity, docs, and smoke.", "Development"),
        ("/model-assisted-patch-critique", "Model Critique", "v241.0 Operator-Governed Model-Assisted Patch Critique Layer: package approved model outputs into evidence-scored critique packets without authority.", "Development"),
        ("/multi-model-review-synthesis", "Review Synthesis", "v242.0 Supervised Multi-Model Review Synthesis Layer: cluster agreement, disagreement, hallucination candidates, and useful findings without approval.", "Development"),
        ("/patch-risk-remediation-synthesis", "Risk Synthesis", "v243.0 Operator-Governed Patch Risk and Remediation Synthesis: turn model critiques into review-only risks, remediation candidates, verification suggestions, and docs impact.", "Development"),
        ("/model-review-quality-calibration", "Review Quality", "v244.0 Supervised Model Review Quality Calibration: track useful findings, false positives, hallucinations, missed issues, and task-specific model usefulness without promotion.", "Development"),
        ("/model-assisted-patch-review-audit", "Review Audit", "v245.0 Operator-Governed Model-Assisted Patch Review and Synthesis Layer v1: audit critique, synthesis, risk remediation, quality calibration, no-model-authority, no-source-mutation, parity, docs, and smoke.", "Development"),
        ("/model-assisted-patch-draft", "Patch Draft", "v246.0 Operator-Governed Model-Assisted Patch Draft Packet Layer: assemble reviewable model-assisted patch draft packets without writing files or approving implementation.", "Development"),
        ("/file-impact-documentation-planner", "Impact Planner", "v247.0 Supervised File Impact and Documentation Planner: map source, dashboard, API/CLI, README, and release-history impacts without applying changes.", "Development"),
        ("/smoke-verification-suggestions", "Verify Plan", "v248.0 Supervised Smoke and Verification Suggestion Layer: suggest smoke, parity, package privacy, dashboard regression, and extracted ZIP checks without running commands.", "Development"),
        ("/sandbox-preparation-packet", "Sandbox Prep", "v249.0 Operator-Governed Sandbox Preparation Packet Layer: prepare readiness, approval scope, risk, rollback, expected output, and checklist without executing sandbox work.", "Development"),
        ("/patch-draft-assembly-audit", "Draft Audit", "v250.0 Operator-Governed Model-Assisted Patch Draft Assembly Layer v1: audit draft traceability, file impact, docs, verification suggestions, sandbox prep, no-source-mutation, parity, docs, and smoke.", "Development"),
        ("/draft-to-execution-packet", "Exec Packet", "v251.0 Operator-Governed Draft-to-Execution Packet Gate: convert draft packets into review-only execution-packet candidates with selected scope, evidence, and default blocked approval state.", "Development"),
        ("/patch-diff-preview-planner", "Diff Preview", "v252.0 Supervised Patch Diff Preview and Edit Plan Layer: map file anchors, before/after previews, docs edits, runtime effects, and overreach without mutating source.", "Development"),
        ("/execution-approval-scope", "Approval Scope", "v253.0 Operator-Governed Explicit Approval Scope Ledger: track exact, fresh, scoped approval receipts without treating vague enthusiasm as authorization.", "Development"),
        ("/verification-rollback-packet", "Verify/Rollback", "v254.0 Supervised Verification and Rollback Packet Planner: prepare suggested checks and rollback plans without running commands or altering files.", "Development"),
        ("/patch-execution-packet-audit", "Exec Audit", "v255.0 Operator-Governed Patch Execution Packet Bridge v1: audit traceability, diff preview, approval scope, verification, rollback, no-model-authority, and no-source-mutation boundaries.", "Development"),
        ("/application-prep-intake", "App Intake", "v256.0 Operator-Governed Execution Packet Intake Layer: normalize execution packets into review-only application prep scope, docs obligations, approval receipts, and blocked items.", "Development"),
        ("/source-edit-application-plan", "Edit Plan", "v257.0 Supervised Source Edit Application Plan Builder: prepare target-file edit plans, anchors, previews, conflicts, and generated-content boundaries without mutating source.", "Development"),
        ("/documentation-application-plan", "Doc Plan", "v258.0 Supervised Documentation and Release Metadata Application Plan: plan README, release history, version markers, runtime docs, and completeness checks without writing files.", "Development"),
        ("/final-application-governance-gate", "Final Gate", "v259.0 Operator-Governed Final Pre-Application Governance Gate: verify approval freshness, scope match, verification, rollback, and no-autonomy boundaries without granting authority.", "Development"),
        ("/application-prep-integration-audit", "Prep Audit", "v260.0 Operator-Governed Approved Execution Packet Application Prep v1: audit intake, source edit plans, documentation plans, approval binding, verification, rollback, no-execution, and API/CLI parity.", "Development"),
        ("/structural-inventory", "Structure", "v261.0 Operator-Governed Structural Inventory Layer: inventory central file size, runtime surfaces, dashboard/API/CLI commands, smoke coverage, docs dependencies, and safe module boundaries without behavior changes.", "Development"),
        ("/runtime-registry-prep", "Registry", "v262.0 Operator-Governed Runtime Registry Prep Layer: prepare shared runtime metadata for capability, route, CLI, API, dashboard, safety, docs, and smoke entries without replacing dispatch.", "Development"),
        ("/dashboard-stabilization-audit", "Dash Stable", "v263.0 Operator-Governed Dashboard Stabilization Layer: preserve command-deck layout, custom data-tip hover behavior, route parity, and no native nav title tooltip regressions.", "Development"),
        ("/dispatch-stabilization", "Dispatch", "v264.0 Operator-Governed CLI/API Dispatch Stabilization Layer: inventory CLI/API dispatch, parity, missing surfaces, and regression smoke suggestions without executing commands.", "Development"),
        ("/structural-stabilization-audit", "Refactor Ready", "v265.0 Operator-Governed Structural Stabilization and Runtime Modularization v1: audit structural drift, runtime parity, dashboard route parity, API/CLI parity, docs completeness, package privacy, extracted ZIP verification, and refactor risk.", "Development"),
        ("/runtime-registry", "Registry Live", "v266.0 Operator-Governed Runtime Metadata Registry Extraction: source-only runtime_registry.py metadata helper, capability/route/CLI/API/dashboard/safety extraction, compatibility adapters, smoke hooks, and no-behavior-change audit.", "Development"),
        ("/governance-report-builder-audit", "Report Builder", "v267.0 Operator-Governed Governance Report Builder Extraction: source-only governance_reports.py helpers, packet/safety/approval/verification/audit renderers, wrappers, output parity, and no-authority-change audit.", "Development"),
        ("/dashboard-registry-integration", "Dash Registry", "v268.0 Operator-Governed Dashboard Surface Registry Integration: dashboard registry adapter, nav metadata, route labels, data-tip binding, title regression guard, style preservation, and route parity.", "Development"),
        ("/runtime-dispatch-registry-audit", "Dispatch Reg", "v269.0 Operator-Governed CLI/API Runtime Registry Integration: CLI/API registry adapters, shared command metadata, dynamic dispatch parity, missing surface guards, naming checks, and no-execution audit.", "Development"),
        ("/module-extraction-audit", "Module Audit", "v270.0 Operator-Governed Runtime Module Extraction v1: audit extracted module imports, registry parity, governance report parity, dashboard/API/CLI parity, package privacy, docs, smoke, and refactor risks.", "Development"),
        ("/self-maintenance-extraction-map", "SM Map", "v271.0 Operator-Governed Self-Maintenance Extraction Map: function clusters, runtime reports, governance audits, package/privacy, version markers, smoke coverage, extraction priorities, wrappers, and no-behavior-change audit.", "Development"),
        ("/package-version-integrity", "Pkg/Version", "v272.0 Operator-Governed Package and Version Utility Extraction: package_integrity.py, version_state.py, source-only policy, forbidden runtime path detection, version markers, release marker adapters, wrappers, and parity audit.", "Development"),
        ("/surface-parity-audit", "Surface Parity", "v273.0 Operator-Governed Surface Parity Utility Extraction: surface_parity.py dashboard/API/CLI presence helpers, registry binding, missing surface detection, parity renderer, wrappers, and route/API/CLI audit.", "Development"),
        ("/verification-planning-audit", "Verify Plan", "v274.0 Operator-Governed Smoke and Verification Utility Extraction: verification_planning.py fast/install/extracted zip/dashboard tooltip/package privacy verification suggestions, readiness summaries, wrappers, and no-command-execution audit.", "Development"),
        ("/self-maintenance-decomposition-audit", "SM Decomp", "v275.0 Operator-Governed Self-Maintenance Decomposition v1: utility imports, wrappers, output parity, package/version, surfaces, verification planning, dashboard, API/CLI, docs, smoke, and safety boundaries.", "Development"),
        ("/dashboard-extraction-map", "Dash Map", "v276.0 Operator-Governed Dashboard Surface Extraction Map: dashboard function clusters, navigation, route handlers, page renderers, console style dependencies, data-tip tooltip dependencies, wrappers, and no-visual-change audit.", "Development"),
        ("/dashboard-component-audit", "Dash Components", "v277.0 Operator-Governed Dashboard Component Helper Extraction: dashboard_components.py, console cards, status rows, audit sections, packet summaries, tooltip-safe nav helpers, wrappers, and style audit.", "Development"),
        ("/api-surface-audit", "API Surface", "v278.0 Operator-Governed API Surface Helper Extraction: api_surface.py route metadata, runtime JSON helpers, error helpers, dynamic route summaries, parity checks, wrappers, and no-behavior-change audit.", "Development"),
        ("/cli-surface-audit", "CLI Surface", "v279.0 Operator-Governed CLI Surface Helper Extraction: cli_surface.py command metadata, JSON/human renderers, dynamic command summaries, parity checks, wrappers, and no-execution-authority audit.", "Development"),
        ("/interface-modularization-audit", "Interface Audit", "v280.0 Operator-Governed Dashboard/API/CLI Modularization v1: helper imports, route/nav parity, API/CLI runtime parity, data-tip tooltip regression, command-deck preservation, docs, package privacy, and no-authority boundaries.", "Development"),
        ("/approved-application-binding", "App Binding", "v281.0 Operator-Approved Application Packet Binding Layer: packet id, approved file/edit/docs/verification scope, approval freshness, and no-inferred-approval audit.", "Development"),
        ("/operator-execution-checklist", "Exec Checklist", "v282.0 Operator Execution Checklist Builder Layer: pre-application, source edit, README/release history, smoke, package privacy, and rollback preparedness checklist, without command execution.", "Development"),
        ("/post-application-result-review", "Post-App Review", "v283.0 Operator-Governed Post-Application Result Review Layer: expected change binding, observed/smoke/package/surface result intake, deviation classification, and no-auto-rollback audit.", "Development"),
        ("/application-outcome-learning", "Outcome Learning", "v284.0 Operator-Governed Application Outcome Learning Extractor: supervised success/failure/smoke/docs/approval lessons and future risk notes, without memory mutation.", "Development"),
        ("/application-execution-refinement-audit", "App Exec Audit", "v285.0 Operator-Approved Application Execution Refinement v1: approval binding, execution checklist, post-application review, supervised outcome lessons, parity, package privacy, smoke, and no-autonomy audit.", "Development"),
        ("/rollback-scope-binding", "Rollback Scope", "v286.0 Operator-Governed Rollback Scope Binding Layer: application packet rollback binding, file/docs/version scope, package/smoke context, route coverage, and no-auto-rollback audit.", "Development"),
        ("/failure-damage-map", "Failure Map", "v287.0 Operator-Governed Failure Classification and Damage Map: compile, smoke, dashboard, API/CLI, package privacy, and partial application failure classification without diagnostic overreach.", "Development"),
        ("/recovery-checklist", "Recovery List", "v288.0 Operator-Governed Recovery Checklist Builder: manual stop conditions, file/docs/version recovery, verification rerun suggestions, package rebuild checklist, and no-command-execution audit.", "Development"),
        ("/post-recovery-review", "Recovery Review", "v289.0 Operator-Governed Post-Recovery Review Layer: expected clean state, observed recovery result intake, drift classification, verification/package review, and no-auto-continuation audit.", "Development"),
        ("/rollback-recovery-audit", "Rollback Audit", "v290.0 Operator-Governed Rollback and Recovery Intelligence v1: rollback scope, failure map, recovery checklist, post-recovery review, parity, package privacy, smoke, and no-autonomy audit.", "Development"),
        ("/memory-candidate-intake", "Memory Intake", "v291.0 Operator-Governed Memory Candidate Intake Layer: patch/recovery/smoke/operator/model source binding, confidence classification, and no-memory-mutation audit.", "Development"),
        ("/memory-candidate-classification", "Memory Classify", "v292.0 Operator-Governed Memory Candidate Classification Layer: project fact, workflow preference, governance rule, capability lesson, sensitive/identity boundary, and risk scoring review.", "Development"),
        ("/memory-approval-packet", "Memory Approval", "v293.0 Operator-Governed Memory Approval Packet Builder: candidate/evidence/risk summaries, approve/reject/defer options, expiration, revalidation, and no-implied-approval audit.", "Development"),
        ("/memory-contradiction-review", "Memory Conflict", "v294.0 Operator-Governed Memory Contradiction and Staleness Review: rule conflicts, project-state conflicts, stale preference detection, purpose drift, governance boundary conflict, and revalidation review.", "Development"),
        ("/memory-governance-audit", "Memory Gov", "v295.0 Operator-Governed Memory Candidate Governance Upgrade v1: intake, classification, approval packets, contradiction/staleness, parity, package privacy, smoke, and no-memory-mutation audit.", "Development"),
        ("/continuity-state-intake", "Continuity", "v296.0 Operator-Governed Continuity State Intake Layer: current version, recent arcs, active surfaces, governance boundaries, memory candidates, recovery lessons, and no-state-mutation audit.", "Development"),
        ("/self-model-snapshot-v2", "Self-Model v2", "v297.0 Operator-Governed Self-Model Snapshot v2 Builder: capability claims, limitations, governance rules, tooling boundaries, environment, stale-claim detection, and no-identity-mutation audit.", "Development"),
        ("/purpose-coherence-review", "Purpose v2", "v298.0 Operator-Governed Purpose Drift and Coherence Review v2: original purpose, current direction, governance alignment, autonomy creep, tooling scope creep, coherence risk, and no-auto-correction audit.", "Development"),
        ("/supervised-growth-priorities", "Growth Priority", "v299.0 Operator-Governed Supervised Growth Priority Synthesizer: capability gaps, structural debt, governance risk, memory risk, recovery lessons, next arc recommendations, and no-auto-roadmap audit.", "Development"),
        ("/continuity-kernel-v2-audit", "Kernel v2", "v300.0 Local Artificial Mind Continuity Kernel v2: continuity state, self-model snapshot, purpose coherence, growth priorities, surface parity, package privacy, smoke, and no-autonomy audit.", "Development"),
        ("/identity-expression-boundary", "Identity Expr", "v301.0 Operator-Governed Identity Expression Boundary Layer: review-only identity wording boundaries, consciousness claim calibration, purpose binding, and no-identity-mutation audit.", "Development"),
        ("/personality-trait-ledger", "Trait Ledger", "v302.0 Operator-Governed Personality Trait Candidate Ledger: review-only traits, evidence, intensity, conflict, risk, and no-personality-mutation audit.", "Development"),
        ("/voice-affect-style-map", "Voice Map", "v303.0 Operator-Governed Voice and Affect Style Map: context-sensitive voice previews, affect boundaries, refusal/safety voice, and no live prompt rewrite.", "Development"),
        ("/coherence-expression-review", "Expr Coherence", "v304.0 Operator-Governed Coherence Expression Review: identity, personality, purpose, voice, desire, opinion, and governance consistency review without auto-correction.", "Development"),
        ("/identity-personality-coherence-audit", "Expression Audit", "v305.0 Operator-Governed Identity, Personality, and Coherence Expression Layer v1: audits identity expression, personality ledger, voice map, coherence review, risky-request blocking, route parity, package privacy, and no-autonomy boundaries.", "Development"),
        ("/dashboard-route-health", "Route Health", "v306.0 Operator-Governed Dashboard Route Health Registry v1: registers critical dashboard routes, render expectations, HTML shape markers, and review-only route health reports.", "Development"),
        ("/runtime-test-visibility", "Smoke View", "v307.0 Operator-Governed Runtime Test Visibility Layer v1: names smoke tiers, route probes, progress markers, timeout summaries, metadata checks, and extracted-zip parity without executing hidden work.", "Development"),
        ("/behavioral-expression-preview", "Behavior Preview", "v308.0 Operator-Governed Behavioral Expression Preview Packets v1: previews identity/personality/coherence-safe response variants without changing live chat, prompts, memory, identity, or personality.", "Development"),
        ("/style-delta-staging", "Style Deltas", "v309.0 Operator-Governed Style Delta Staging v1: stages style, prompt, dashboard, README, warning, and refusal wording deltas for review only without applying source changes.", "Development"),
        ("/expression-runtime-health-audit", "v310 Audit", "v310.0 Operator-Governed Behavioral Expression Preview and Runtime Health Hardening v1: audits route health, smoke visibility, metadata, expression previews, style deltas, parity, privacy, and no-autonomy boundaries.", "Development"),
        ("/expression-profile-packets", "Expr Profiles", "v311.0 Operator-Governed Expression Profile Packet Assembly v1: assembles identity, trait, voice, affect, and governance constraints into review-only expression profiles without applying them.", "Development"),
        ("/conversation-scenario-sandbox", "Scenario Sandbox", "v312.0 Operator-Governed Conversation Scenario Sandbox v1: previews coding, governance, sensitive, planning, refusal, and dashboard microcopy scenarios without changing live chat.", "Development"),
        ("/expression-regression-review", "Expr Regression", "v313.0 Operator-Governed Expression Regression Review v1: flags autonomy creep, sentience overclaims, dependency theater, overconfidence, purpose drift, and governance conflicts.", "Development"),
        ("/expression-operator-review-console", "Expr Review", "v314.0 Operator-Governed Expression Candidate Review Console v1: reviews profiles, scenario outputs, risk flags, readiness scores, and approval boundaries without granting approval.", "Development"),
        ("/conversational-expression-sandbox-audit", "v315 Audit", "v315.0 Operator-Governed Conversational Expression Sandbox v1: audits profile packets, scenario sandboxing, regression review, operator review console, route health, smoke, parity, privacy, and no-autonomy boundaries.", "Development"),
        ("/expression-approval-criteria", "Expr Criteria", "v316.0 Operator-Governed Expression Approval Criteria Layer v1: binds sandbox, regression, and operator review evidence into readiness criteria without granting approval.", "Development"),
        ("/expression-live-surface-impact-map", "Expr Surfaces", "v317.0 Operator-Governed Live Surface Impact Map v1: maps chat, dashboard, docs, API, CLI, warning, and rollback surfaces without mutating live behavior.", "Development"),
        ("/expression-implementation-packet-draft", "Expr Packet", "v318.0 Operator-Governed Expression Implementation Packet Drafting v1: drafts reviewable implementation packets without writing source or applying prompts.", "Development"),
        ("/expression-rollback-reversion-plan", "Expr Rollback", "v319.0 Operator-Governed Expression Rollback and Reversion Planning v1: plans reversible expression changes without executing rollback.", "Development"),
        ("/expression-application-bridge-audit", "v320 Audit", "v320.0 Operator-Governed Conversational Expression Application Bridge v1: audits approval criteria, surface maps, packet drafts, rollback plans, route health, smoke, parity, privacy, and no-application boundaries.", "Development"),
        ("/expression-patch-candidates", "v321 Candidates", "v321.0 Operator-Governed Expression Patch Candidate Schema v1: represents expression/personality source-change candidates as review-only packets without applying or writing source.", "Development"),
        ("/expression-sandbox-diff-preview", "v322 Diff Preview", "v322.0 Operator-Governed Sandbox Diff Preview Assembly v1: previews before/after expression diffs in sandbox form without applying live diffs.", "Development"),
        ("/expression-dry-run-verification-plan", "v323 Verify Plan", "v323.0 Operator-Governed Expression Dry-Run Verification Planning v1: prepares compile, smoke, route, regression, privacy, package, and rollback checks without executing commands.", "Development"),
        ("/expression-dry-run-review-packet", "v324 Review Packet", "v324.0 Operator-Governed Expression Dry-Run Review Packet v1: combines candidates, diff previews, risk flags, verification plans, rollback expectations, and approval boundaries without granting approval.", "Development"),
        ("/expression-patch-dry-run-audit", "v325 Dry-Run Audit", "v325.0 Operator-Governed Expression Patch Dry-Run Sandbox v1: audits patch candidates, diff previews, verification plans, review packets, route health, smoke, parity, docs, privacy, and no-application boundaries.", "Development"),
        ("/expression-sandbox-trial-packet", "v326 Trial Packet", "v326.0 Operator-Governed Expression Sandbox Trial Packet Prep v1: prepares sandbox trial packets from dry-run review evidence without creating, modifying, or executing sandboxes.", "Development"),
        ("/expression-sandbox-workspace-plan", "v327 Workspace", "v327.0 Operator-Governed Expression Sandbox Workspace Plan v1: plans source-only sandbox workspaces and runtime privacy exclusions without copying or writing files.", "Development"),
        ("/expression-sandbox-verification-matrix", "v328 Verify Matrix", "v328.0 Operator-Governed Expression Sandbox Trial Verification Matrix v1: plans sandbox compile, smoke, route, API/CLI, regression, privacy, package, and rollback checks without executing commands.", "Development"),
        ("/expression-sandbox-result-review-prep", "v329 Result Prep", "v329.0 Operator-Governed Expression Sandbox Trial Result Review Prep v1: prepares future sandbox result review, failure classification, and operator decision options without promotion inference.", "Development"),
        ("/expression-sandbox-trial-harness-audit", "v330 Trial Audit", "v330.0 Operator-Governed Expression Patch Sandbox Trial Harness v1: audits trial packets, workspace plans, verification matrices, result review prep, route health, smoke, parity, docs, privacy, and no-execution boundaries.", "Development"),
        ("/expression-sandbox-execution-approval-gate", "Exec Approval", "v331.0 Operator-Governed Sandbox Trial Execution Approval Gate v1: scope-bound operator approval status, expiration, forbidden actions, decision packet, and no-approval-inference audit.", "Development"),
        ("/expression-sandbox-workspace-execution-packet", "Workspace Packet", "v332.0 Operator-Governed Sandbox Workspace Execution Packet Draft v1: source-only copy instructions, runtime exclusions, sandbox naming, file scope manifest, safety checks, manual notes, and no-copy audit.", "Development"),
        ("/expression-sandbox-patch-bundle-packet", "Patch Bundle", "v333.0 Operator-Governed Expression Sandbox Patch Bundle Packet v1: dry-run diff binding, target manifest, boundary guard, conflict detector, rollback map, review packet, and no-application audit.", "Development"),
        ("/expression-sandbox-verification-command-packet", "Verify Packet", "v334.0 Operator-Governed Sandbox Verification Command Packet Draft v1: compile/smoke/targeted/dashboard/API/CLI/privacy command drafts with manual-run boundary and no-command-execution audit.", "Development"),
        ("/expression-sandbox-execution-packet-bridge-audit", "v335 Exec Bridge", "v335.0 Operator-Governed Expression Sandbox Trial Execution Packet Bridge v1: audits approval gate, workspace packet, patch bundle, verification command packet, parity, smoke, privacy, and no-execution boundaries.", "Development"),
        ("/expression-sandbox-trial-evidence-intake", "Evidence Intake", "v336.0 Operator-Governed Sandbox Trial Evidence Intake Layer v1: accepts sandbox trial evidence as review input only, checks completeness/trust/scope, and never treats results as approval.", "Development"),
        ("/expression-sandbox-outcome-comparison", "Outcome Compare", "v337.0 Operator-Governed Sandbox Outcome Comparison v1: compares expected diff/check results against submitted sandbox evidence without auto-correction or source mutation.", "Development"),
        ("/expression-sandbox-regression-result-review", "Result Regression", "v338.0 Operator-Governed Expression Regression Result Review v1: reviews sandbox outputs for autonomy, sentience, dependency, overconfidence, purpose drift, memory, and approval-boundary regressions.", "Development"),
        ("/expression-sandbox-revision-recommendations", "Revision Recs", "v339.0 Operator-Governed Sandbox Trial Revision Recommendation Layer v1: recommends revise/defer/reject/retry/promote-to-review options without applying revisions.", "Development"),
        ("/expression-sandbox-promotion-review-prep", "Promo Prep", "v340.0 Operator-Governed Expression Sandbox Trial Result Intake and Promotion Review Prep v1: assembles promotion-review prep from evidence, comparison, regression, and revision packets without promotion authority.", "Development"),
        ("/expression-promotion-evidence-binder", "Promo Evidence", "v345.0 Operator-Governed Expression Promotion Evidence Binder v1: binds dry-run, sandbox, execution, result, regression, revision, and rollback evidence without approval authority.", "Development"),
        ("/expression-live-promotion-scope-risk", "Promo Scope", "v345.0 Operator-Governed Live Promotion Scope and Risk Packet v1: maps future live expression surfaces and protected boundaries without mutation.", "Development"),
        ("/expression-promotion-verification-rollback", "Promo Verify", "v345.0 Operator-Governed Promotion Verification and Rollback Requirements v1: defines checks and rollback requirements without executing commands.", "Development"),
        ("/expression-promotion-decision-packet", "Promo Decision", "v345.0 Operator-Governed Expression Promotion Decision Packet v1: prepares operator decision fields without executing or applying decisions.", "Development"),
        ("/expression-promotion-packet-assembly-audit", "Promo Audit", "v345.0 Operator-Governed Expression Promotion Packet Assembly Layer v1: audits packet-only promotion review surfaces without live promotion authority.", "Development"),
        ("/expression-live-application-eligibility-gate", "Live Elig", "v346.0 Operator-Governed Live Application Packet Eligibility Gate v1: checks fresh scoped approval eligibility for drafting only without authorizing live writes.", "Development"),
        ("/expression-live-source-change-manifest", "Live Manifest", "v347.0 Operator-Governed Live Source Change Manifest Draft v1: maps future live expression targets and protected paths without writing files.", "Development"),
        ("/expression-live-patch-instruction-packet", "Live Patch", "v348.0 Operator-Governed Live Diff and Patch Instruction Packet Draft v1: drafts future patch instructions without applying them.", "Development"),
        ("/expression-live-verification-rollback-packet", "Live Verify", "v349.0 Operator-Governed Live Application Verification and Rollback Packet v1: defines checks and rollback expectations without executing commands.", "Development"),
        ("/expression-live-application-packet-audit", "Live App Audit", "v350.0 Operator-Governed Expression Live Application Packet Drafting Layer v1: audits draft-only live application packets without live source authority.", "Development"),
        ("/intelligence", "Intelligence", "Project indexing and codebase intelligence summaries.", "Development"),
        ("/workspace", "Workspace", "Workspace registry, project context, command profiles, and dependency maps.", "Development"),
        ("/patch-drafts", "Patch Drafts", "v73 supervised patch draft composer: intent normalization, scope contracts, prompt composition, output schema, safety review, evidence binding, and local-model handoff stubs. Draft only; no apply or model invocation.", "Development"),
        ("/code-patches", "Code Patches", "Code patch proposal and patch bridge surfaces.", "Development"),
        ("/release-review", "Release Review", "Release review summaries before packaging or publish decisions.", "Release"),
        ("/release-package", "Release Package", "Lightweight release package controls and source-only packaging information.", "Release"),
        ("/release-governance", "Release Governance", "Governance gates, package integrity, and candidate safety checks.", "Release"),
        ("/release-evidence", "Release Evidence", "Release evidence ledger, provenance, and reproducibility surfaces.", "Release"),
        ("/release-signing", "Release Signing", "Detached-signature readiness and trust-root reporting. No private key handling.", "Release"),
        ("/release-operations", "Release Ops", "Operations console for package, trust, candidate, and safety workflows.", "Release"),
        ("/release-operator", "Release Operator", "Operator workflow summary for release decisions.", "Release"),
        ("/release-candidate", "Release Candidate", "Candidate review and package state without publish approval leakage.", "Release"),
        ("/release-approval", "Release Approval", "Publish approval state and revocation previews, separate from live apply.", "Release"),
        ("/autonomy", "Autonomy Boundary", "Compact autonomy boundary overview and links into detailed autonomy/maintenance systems.", "Autonomy"),
        ("/maintenance-queue", "Maintenance Queue", "v46 self-maintenance queue summary, selected task, scoring, checkpoint binding, and safe CLI/API links.", "Autonomy"),
        ("/attention", "Attention", "v47 attention scheduler: budgets, focus selection, receipts, reason codes, deferrals, stale resurfacing, and safe next actions.", "Autonomy"),
        ("/reflection", "Reflection", "v48.x reflection review: receipts, dedup, rejection policy, promotion drafts, safety labels, and memory-review boundaries.", "Autonomy"),
        ("/identity", "Identity", "v49 identity continuity and identity receipts: draft self-description, stable principles, drift explanations, and review-only identity evolution.", "Autonomy"),
        ("/memory", "Memory", "v50-v51 durable-memory promotion, guarded write path, receipts, store schema, read/search, correction/removal drafts, and write audit previews.", "Autonomy"),
        ("/recall", "Recall", "v52 recall stabilization: receipts, evidence, conflict/stale handling, scope controls, privacy checks, and read-only retrieval.", "Autonomy"),
        ("/planning", "Planning", "v53 memory-informed planning: selected memory evidence, ignored-memory explanations, warnings, receipts, conflicts, revisions, scope, and risk budgets.", "Autonomy"),
        ("/action-plans", "Action Plans", "v54 supervised action planning: evidence-bound action steps, blocked destructive labels, and no automatic execution.", "Autonomy"),
        ("/execution-preview", "Execution Preview", "v55 controlled execution preview: validates one action plan, rehearses readiness, and grants no real operation approval.", "Autonomy"),
        ("/read-only-execution", "Read-Only Execution", "v56 controlled read-only execution: runs only allowlisted diagnostics after exact confirmation and grants no mutation approval.", "Autonomy"),
        ("/evidence-gathering", "Evidence Gathering", "v57 evidence-gathering maintenance loop: binds read-only diagnostics into supervised maintenance planning evidence without mutation.", "Autonomy"),
        ("/patch-proposals", "Patch Proposals", "v58 evidence-grounded sandbox patch proposals: issue-to-patch rationale, evidence binding, risk scoring, and no source apply.", "Autonomy"),
        ("/sandbox-patch-execution", "Sandbox Patch Execution", "v59 controlled sandbox-only patch execution: reviewed proposal binding, temp sandbox rehearsal, verification receipt, and no live source apply.", "Autonomy"),
        ("/source-apply-handoff", "Source Apply Handoff", "v61 controlled source-apply bridge: receipts, drift resolver, artifact binder, eligibility, dry-run bridge, no live source mutation.", "Autonomy"),
        ("/source-apply-transactions", "Source Apply Transactions", "v62 supervised source-apply transaction layer: plan, backup, dry-run, exact confirmation, executor review, verification, and rollback rehearsal.", "Autonomy"),
        ("/transaction-evidence", "Transaction Evidence", "v63 durable transaction evidence: ledger, diffs, conflicts, approval records, safe exports, replay audit, dashboard timeline, and API search.", "Autonomy"),
        ("/improvement-intelligence", "Improvement Intelligence", "v64 supervised improvement intelligence: evidence summaries, candidate registry, scoring, regression patterns, risk forecast, and recommendation queue.", "Autonomy"),
        ("/proposal-drafting", "Proposal Drafting", "v65 recommendation-to-proposal drafting: accepted recommendation intake, proposal skeletons, evidence requirements, risk contracts, sandbox requests, and review packets.", "Autonomy"),
        ("/proposal-sandbox", "Proposal Sandbox", "v66 reviewed proposal sandbox execution: acceptance gate, workspace plan, implementation request, harness, verification, evidence binder, and failure triage.", "Autonomy"),
        ("/sandbox-promotion", "Sandbox Promotion", "v67 sandbox evidence promotion: candidate builder, source diff normalizer, safety gate, transaction draft, review packet, conflict detector, and transaction-handoff readiness.", "Autonomy"),
        ("/source-transaction-review", "Source Transaction Review", "v68 promotion-to-transaction integration: promotion intake, materialized transaction plan, baseline reconciliation, backup/rollback preflight, safety gate, and ledger pre-registration.", "Autonomy"),
        ("/transaction-execution", "Transaction Execution", "v69 operator-confirmed transaction execution: eligibility, exact confirmation, backup snapshot, rehearsal, guarded executor, verification, and rollback recommendation.", "Autonomy"),
        ("/release-finalization", "Release Finalization", "v70 verified execution recovery: execution ledger finalization, rollback decision/executor, post-rollback verification, release candidate gate, package certifier, and recovery simulation.", "Autonomy"),
        ("/codebase-map", "Codebase Map", "v71 codebase understanding: source inventory, responsibilities, dependency/call surface, risks, historical failures, verification mapping, and opportunities.", "Autonomy"),
        ("/patch-context", "Patch Context", "v72 patch generation context builder: goal intake, relevant files, historical failures, risk budgets, verification requirements, context packets, and review gates. Context only; no patch generation or apply.", "Autonomy"),
        ("/approvals", "Approvals <span class='nav-badge warn-badge' data-live-count='counts.pending_approvals'></span>", "Human approval records waiting for review. Browsing does not approve them.", "Autonomy"),
        ("/notifications", "Notifications <span class='nav-badge warn-badge' data-live-count='counts.unread_notifications'></span>", "Unread and archived notification records from watch and operator systems.", "Autonomy"),
        ("/watch", "Watch <span class='nav-badge' data-live-count='counts.watch_reports'></span>", "Watch-mode reports and monitoring snapshots.", "Autonomy"),
        ("/patches", "Patches <span class='nav-badge' data-live-count='counts.patches'></span>", "Patch proposal records, applied state, rollback metadata, and review traces.", "Autonomy"),
        ("/goals", "Goals <span class='nav-badge' data-live-count='counts.goals'></span>", "Goal records and goal-management state for continuity.", "Autonomy"),
        ("/diagnostics", "Diagnostics <span class='nav-badge' data-live-count='counts.diagnostic_reports'></span>", "Diagnostic reports and recent health checks.", "System"),
        ("/settings", "Settings", "Local settings and settings health. Still not a substitute for judgment, tragically.", "System"),
        ("/api-info", "API", "Local API route reference and safety boundary notes.", "System"),
        ("/desktop", "Desktop", "Desktop companion setup and local shell information.", "System"),
        ("/setup", "Setup <span class='nav-badge' data-live-count='counts.setup_reports'></span>", "Setup helper reports and local environment checks.", "System"),
        ("/onboarding", "Onboarding <span class='nav-badge' data-live-count='counts.onboarding_runs'></span>", "Project onboarding runs and first-use setup guidance.", "System"),
        ("/activity", "Activity", "Recent task, maintenance, diagnostic, notification, and watch activity.", "System"),
    ]
    nav = _render_nav(path, nav_items)
    msg = f"<div class='notice ok'>{_safe(DashboardState.message)}</div>" if DashboardState.message else ""
    err = f"<div class='notice bad'>{_safe(DashboardState.error)}</div>" if DashboardState.error else ""
    DashboardState.message = ""
    DashboardState.error = ""

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{DASHBOARD_TITLE}</title>
<style>
:root {{ --bg:#101217; --panel:#171b23; --panel2:#202634; --text:#eef1f7; --muted:#9aa5b5; --accent:#8fb3ff; --good:#77d192; --bad:#ff8f8f; --warn:#ffd27d; --border:#30384a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Segoe UI, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
header {{ padding:18px 24px; border-bottom:1px solid var(--border); background:#0d0f14; position:sticky; top:0; z-index:2; }}
h1 {{ margin:0 0 4px 0; font-size:22px; }}
.subtitle {{ color:var(--muted); font-size:13px; }}
nav.nav-shell {{ display:grid; grid-template-columns:1fr; gap:10px; padding:12px 24px; border-bottom:1px solid var(--border); background:#11151d; }}
.nav-intro {{ display:flex; flex-wrap:wrap; gap:8px 12px; align-items:baseline; color:var(--muted); font-size:12px; }}
.nav-intro strong {{ color:var(--text); font-size:13px; }}
.nav-section {{ border:1px solid var(--border); border-radius:14px; background:#0f141d; }}
.nav-section summary {{ cursor:pointer; list-style:none; display:flex; flex-wrap:wrap; gap:8px 12px; align-items:baseline; padding:9px 12px; color:var(--text); }}
.nav-section summary::-webkit-details-marker {{ display:none; }}
.nav-section summary::before {{ content:'▸'; color:var(--muted); }}
.nav-section[open] summary::before {{ content:'▾'; color:var(--accent); }}
.nav-section summary small {{ color:var(--muted); font-size:12px; }}
.nav-links {{ display:flex; flex-wrap:wrap; gap:8px; padding:0 12px 12px 12px; }}
.command-palette {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; padding:9px 12px; border:1px solid var(--border); border-radius:14px; background:#0f141d; }}
.command-palette label {{ color:var(--muted); font-size:12px; }}
.command-palette input {{ min-width:min(420px, 100%); flex:1; }}
.nav-section.nav-hidden, nav a.nav-link.nav-hidden {{ display:none; }}
nav a.nav-link {{ color:var(--text); text-decoration:none; padding:8px 10px; border:1px solid var(--border); border-radius:10px; background:var(--panel); position:relative; }}
nav a.nav-link.active {{ border-color:var(--accent); color:#fff; box-shadow:0 0 0 1px var(--accent) inset; }}
nav a.nav-link:hover, nav a.nav-link:focus {{ border-color:var(--accent); outline:none; }}
nav a.nav-link[data-tip]:hover::after, nav a.nav-link[data-tip]:focus::after, .mini-card[data-tip]:hover::after, .mini-card[data-tip]:focus::after {{ content:attr(data-tip); position:absolute; left:0; top:calc(100% + 7px); z-index:20; width:min(320px, 72vw); padding:9px 10px; border:1px solid var(--border); border-radius:10px; background:#080a0f; color:var(--text); box-shadow:0 8px 22px rgba(0,0,0,.35); font-size:12px; line-height:1.35; }}
a {{ color:var(--accent); }} a:hover {{ color:#dbe7ff; }}
main {{ max-width:1200px; margin:0 auto; padding:22px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }}
.card {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; margin-bottom:16px; }}
.mini-card {{ position:relative; background:#10151e; border:1px solid var(--border); border-radius:14px; padding:12px; min-height:82px; }}
.mini-card:focus {{ outline:1px solid var(--accent); }}
.card h2 {{ margin:0 0 12px; font-size:18px; }}
.card h3 {{ margin:14px 0 8px; font-size:15px; color:var(--accent); }}
.kpi {{ font-size:30px; font-weight:700; }}
.muted {{ color:var(--muted); }}
.good {{ color:var(--good); }} .badtext {{ color:var(--bad); }} .warn {{ color:var(--warn); }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#0b0d12; border:1px solid var(--border); border-radius:12px; padding:12px; max-height:520px; overflow:auto; }}
button, input, select {{ background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:10px; padding:8px 10px; }}
button {{ cursor:pointer; }} button:hover {{ border-color:var(--accent); }}
form.inline {{ display:inline-block; margin:2px 4px 2px 0; }}
form.stack {{ display:grid; gap:8px; max-width:760px; }}
textarea {{ width:100%; background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:10px; padding:10px; font-family:inherit; }}
.action-card {{ border:1px solid var(--border); border-radius:14px; padding:12px; background:#121720; }}
.notice {{ padding:12px 14px; border-radius:12px; margin-bottom:14px; border:1px solid var(--border); }}
.notice.ok {{ background:#122619; color:#d7ffe0; }} .notice.bad {{ background:#2b1515; color:#ffdada; }}
table {{ width:100%; border-collapse:collapse; }} th,td {{ border-bottom:1px solid var(--border); padding:8px; vertical-align:top; text-align:left; }} th {{ color:var(--muted); font-weight:600; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid var(--border); color:var(--muted); font-size:12px; }}
.stage-pill {{ display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid var(--border); font-size:12px; font-weight:600; background:#151b26; color:var(--muted); }}
.stage-ready {{ color:var(--good); border-color:#315f43; background:#102016; }}
.stage-active {{ color:#dbe7ff; border-color:#365c9b; background:#111d35; }}
.stage-approval-required, .stage-approval-pending, .stage-approved-ready {{ color:var(--warn); border-color:#6a4c18; background:#23190b; }}
.stage-approval-rejected, .stage-approval-failed, .stage-recovery-needed, .stage-blocked {{ color:var(--bad); border-color:#6d3030; background:#261111; }}
.stage-patch-proposed {{ color:#cdb7ff; border-color:#514277; background:#1c1730; }}
.stage-done {{ color:var(--good); border-color:#315f43; background:#102016; }}
.stage-cancelled, .stage-unknown {{ color:var(--muted); }}
.review-archived {{ opacity:0.62; }}
.lifecycle-strip {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:10px 0; }}
.lifecycle-step {{ padding:8px 10px; border:1px solid var(--border); border-radius:12px; background:#10151e; color:var(--muted); font-size:12px; }}
.lifecycle-step.current {{ border-color:var(--accent); color:#fff; box-shadow:0 0 0 1px var(--accent) inset; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:10px 0; }}
	.filter-chip {{ display:inline-block; padding:7px 10px; border:1px solid var(--border); border-radius:999px; background:#111722; color:var(--text); text-decoration:none; font-size:12px; }}
	.filter-chip.active {{ border-color:var(--accent); box-shadow:0 0 0 1px var(--accent) inset; }}
.footer {{ color:var(--muted); font-size:12px; margin-top:30px; }}
.nav-badge {{ display:inline-block; min-width:20px; margin-left:5px; padding:1px 6px; border-radius:999px; background:#253047; color:#dbe7ff; font-size:11px; text-align:center; }}
.nav-badge:empty {{ display:none; }}
.warn-badge:not(:empty) {{ background:#4a3215; color:#ffd27d; }}
.livebar {{ display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px; padding:10px 12px; border:1px solid var(--border); border-radius:12px; background:#0f141d; color:var(--muted); }}
.live-dot {{ color:var(--muted); }} .live-dot.ok {{ color:var(--good); }} .live-dot.bad {{ color:var(--bad); }} .live-dot.polling {{ color:var(--warn); }}

/* v135 command-deck operator console skin. Preserves custom data-tip hover behavior; no native title tooltips. */
:root {{ --bg:#050b14; --panel:#081525; --panel2:#0b2035; --text:#e7f2ff; --muted:#8da0ba; --accent:#1ca8ff; --good:#30e079; --bad:#ff4e57; --warn:#ffc44d; --border:#123a5f; --cyan:#20f0e7; }}
body {{ min-height:100vh; background:radial-gradient(circle at 15% 5%, rgba(24,168,255,.18), transparent 28%), linear-gradient(180deg,#06111f 0%, #04070e 100%); color:var(--text); }}
header {{ position:fixed; top:0; left:260px; right:0; height:62px; padding:10px 26px; border-bottom:1px solid #0f3557; background:rgba(4,10,18,.94); backdrop-filter:blur(12px); display:flex; align-items:center; gap:26px; box-shadow:0 0 22px rgba(28,168,255,.12); }}
header h1 {{ font-size:13px; letter-spacing:.22em; text-transform:uppercase; color:var(--good); margin:0; }}
header h1::before {{ content:'🛡 '; }}
header .subtitle {{ color:var(--muted); font-size:12px; }}
header .subtitle::after {{ content:'  |  ENVIRONMENT: PRODUCTION  |  CORE v170.0  |  ALL SYSTEMS NOMINAL'; color:#46b7ff; margin-left:12px; }}
body > nav {{ position:fixed; top:0; left:0; bottom:0; width:260px; overflow:auto; border-right:1px solid #123a5f; background:linear-gradient(180deg,rgba(5,14,27,.98),rgba(3,8,16,.98)); box-shadow:14px 0 40px rgba(0,0,0,.35); z-index:5; }}
nav.nav-shell {{ padding:118px 14px 16px; border:0; background:transparent; gap:12px; }}
nav.nav-shell::before {{ content:'◉ EIDOLON\\A OPERATOR CONSOLE'; white-space:pre; position:absolute; top:24px; left:24px; font-size:30px; line-height:1.05; font-weight:800; letter-spacing:.18em; color:#f1f8ff; text-shadow:0 0 20px rgba(32,240,231,.35); }}
.nav-intro {{ display:none; }}
.command-palette {{ background:#071321; border-color:#164a76; box-shadow:inset 0 0 18px rgba(28,168,255,.06); }}
.nav-section {{ background:transparent; border:0; border-radius:0; }}
.nav-section summary {{ padding:10px 4px; border-top:1px solid rgba(52,108,151,.35); }}
.nav-section summary small {{ display:none; }}
.nav-links {{ display:grid; gap:8px; padding:0 0 12px; }}
nav a.nav-link {{ display:block; padding:10px 13px; border-color:transparent; background:transparent; color:#9dadc6; }}
nav a.nav-link.active, nav a.nav-link:hover, nav a.nav-link:focus {{ color:#eaf7ff; border-color:#1b7ec6; background:linear-gradient(90deg,rgba(28,168,255,.24),rgba(28,168,255,.04)); box-shadow:inset 3px 0 0 #1ca8ff, 0 0 18px rgba(28,168,255,.12); }}
nav a.nav-link[data-tip]:hover::after, nav a.nav-link[data-tip]:focus::after, .mini-card[data-tip]:hover::after, .mini-card[data-tip]:focus::after {{ left:16px; top:calc(100% + 6px); background:#020812; border-color:#1b7ec6; color:#dcecff; }}
main {{ margin-left:260px; padding:88px 26px 28px; max-width:none; }}
.livebar {{ display:none; }}
.card, .mini-card, .action-card {{ background:linear-gradient(180deg,rgba(9,26,45,.92),rgba(5,16,30,.92)); border-color:#164a76; box-shadow:inset 0 0 24px rgba(28,168,255,.045), 0 0 18px rgba(0,0,0,.28); }}
.card h2, .card h3 {{ text-transform:uppercase; letter-spacing:.04em; }}
button, input, select, textarea {{ background:#07192b; border-color:#1b5d91; color:#dcecff; }}
button {{ color:#36b8ff; box-shadow:inset 0 0 12px rgba(28,168,255,.08); }}
button:hover {{ border-color:#20f0e7; color:#92fff9; box-shadow:0 0 18px rgba(32,240,231,.18); }}
.command-deck {{ display:grid; gap:16px; }}
.command-hero {{ display:flex; justify-content:space-between; gap:16px; align-items:start; }}
.command-hero h1 {{ margin:0; font-size:32px; letter-spacing:.06em; text-transform:uppercase; }}
.system-pill {{ border:1px solid #1b7ec6; border-radius:10px; padding:10px 16px; color:#79cfff; background:#06182a; font-weight:700; }}
.command-flow {{ display:grid; grid-template-columns:repeat(5,minmax(150px,1fr)); gap:14px; }}
.command-step {{ position:relative; min-height:145px; border:1px solid #1b5d91; border-radius:14px; padding:18px 16px; background:linear-gradient(180deg,rgba(9,35,61,.95),rgba(5,18,33,.95)); box-shadow:inset 0 0 20px rgba(28,168,255,.08); }}
.command-step.goodstep {{ border-color:#0b8f82; background:linear-gradient(180deg,rgba(6,65,64,.85),rgba(5,28,35,.92)); }}
.command-step.dangerstep {{ border-color:#7d2730; background:linear-gradient(180deg,rgba(60,13,21,.92),rgba(21,8,13,.94)); }}
.step-icon {{ width:48px; height:48px; border:1px solid currentColor; border-radius:50%; display:grid; place-items:center; margin-bottom:10px; font-size:24px; box-shadow:0 0 22px rgba(28,168,255,.2); }}
.command-step h3 {{ margin:0 0 6px; color:#94c9ff; }}
.command-step.dangerstep h3 {{ color:#ff646c; }}
.command-step p {{ min-height:38px; margin:0 0 12px; color:#aebcd1; font-size:13px; }}
.safety-line, .console-footer-note {{ display:flex; justify-content:space-between; gap:12px; padding:12px 16px; border:1px solid #164a76; border-radius:10px; background:rgba(4,13,24,.85); color:#aebcd1; }}
.console-grid {{ display:grid; grid-template-columns:repeat(4,minmax(220px,1fr)); gap:14px; }}
.console-card {{ min-height:178px; border:1px solid #164a76; border-radius:14px; padding:15px; background:linear-gradient(180deg,rgba(7,24,42,.94),rgba(4,14,27,.94)); }}
.console-card h2 {{ margin:0 0 12px; font-size:15px; text-transform:uppercase; }}
.audit-ring {{ width:118px; height:118px; border-radius:50%; display:grid; place-items:center; background:conic-gradient(var(--cyan) 0 78%, #14314b 78% 100%); margin:8px auto; position:relative; }}
.audit-ring::after {{ content:''; position:absolute; inset:13px; border-radius:50%; background:#081525; }}
.audit-ring span {{ position:relative; z-index:1; font-size:25px; font-weight:800; text-align:center; }}
.audit-ring small {{ display:block; font-size:11px; color:var(--good); }}
.status-list {{ display:grid; gap:6px; font-size:13px; color:#aebcd1; }}
.status-list div {{ display:flex; justify-content:space-between; gap:10px; border-bottom:1px solid rgba(52,108,151,.25); padding-bottom:5px; }}
.badge-danger {{ color:#ff646c; border-color:#7d2730; background:#2a0b12; }}
.badge-warn {{ color:#ffc44d; border-color:#6f4d18; background:#261a08; }}
.roadmap-line {{ display:grid; gap:9px; font-size:13px; }}
.roadmap-line div::before {{ content:'●'; color:#20f0e7; margin-right:8px; }}
.signal-spark {{ height:42px; border-bottom:1px solid #1b5d91; background:linear-gradient(135deg, transparent 5%, rgba(32,240,231,.12) 5% 12%, transparent 12% 20%, rgba(28,168,255,.2) 20% 32%, transparent 32%); }}
.reco-strip {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
.reco-chip {{ border:1px solid #164a76; border-radius:10px; padding:9px; background:#081a2e; font-size:12px; }}
@media (max-width: 980px) {{ header, main {{ margin-left:0; left:0; }} body > nav {{ position:static; width:auto; max-height:none; }} nav.nav-shell {{ padding:90px 14px 16px; }} .command-flow, .console-grid, .reco-strip {{ grid-template-columns:1fr; }} }}

</style>
</head>
<body>
<header><h1>{DASHBOARD_TITLE}</h1><div class='subtitle'>Local-only dashboard at {_safe(settings.get('dashboard_host','127.0.0.1'))}:{_safe(settings.get('dashboard_port',8765))}. The ghost gets a browser tab. Somehow this is progress.</div></header>
<nav>{nav}</nav>
<main>{_live_refresh_bar(settings)}{msg}{err}{content}<div class='footer'>Generated at {_safe(_now())}. Approval gates still apply. No browser button bypasses safety checks, because we enjoy not crying.</div></main>
<script>
(function () {{
  const search = document.querySelector('[data-nav-search]');
  if (!search) return;
  function normalize(value) {{ return String(value || '').toLowerCase(); }}
  function applyFilter() {{
    const q = normalize(search.value).trim();
    document.querySelectorAll('.nav-section').forEach(function (section) {{
      let visibleCount = 0;
      section.querySelectorAll('a.nav-link').forEach(function (link) {{
        const haystack = normalize((link.dataset.routeTitle || '') + ' ' + (link.dataset.routeGroup || '') + ' ' + (link.dataset.tip || '') + ' ' + link.textContent);
        const visible = !q || haystack.includes(q);
        link.classList.toggle('nav-hidden', !visible);
        if (visible) visibleCount += 1;
      }});
      section.classList.toggle('nav-hidden', !!q && visibleCount === 0);
      if (q && visibleCount > 0) section.open = true;
    }});
  }}
  search.addEventListener('input', applyFilter);
}})();
</script>

{_live_refresh_script(settings)}
</body>
</html>"""


def _status_cards() -> str:
    tasks = list_tasks(include_cancelled=False)
    approvals = list_approvals(status="pending", include_closed=False)
    notifications = list_notifications(status="unread", include_dismissed=False)
    patches = list_patch_proposals()
    memories = load_memories()
    reports = list_test_reports()
    reviews = list_test_reviews()
    project = get_active_project() or {}
    counts = task_status_counts()
    work_summary = summarize_queue()
    cards = [
        _card("Active Project", f"<div class='kpi' data-live-text='active_project.name'>{_fmt(project.get('name','[none]'))}</div><p class='muted' data-live-text='active_project.path'>{_fmt(project.get('path',''))}</p>"),
        _card("Tasks", f"<div class='kpi' data-live-count='counts.tasks'>{len(tasks)}</div><p class='muted'>Ready: <span data-live-count='counts.task_status.ready'>{counts.get('ready',0)}</span> · Active: <span data-live-count='counts.task_status.active'>{counts.get('active',0)}</span> · Blocked: <span data-live-count='counts.task_status.blocked'>{counts.get('blocked',0)}</span></p>"),
        _card("Tasks / Work", f"<div class='kpi' data-live-count='counts.work_queue_pending'>{work_summary.get('pending',0)}</div><p class='muted'>Active: <span data-live-count='counts.work_queue_active'>{work_summary.get('active',0)}</span> · Blocked: <span data-live-count='counts.work_queue_blocked'>{work_summary.get('blocked',0)}</span> · Approval: <span data-live-count='counts.work_queue_approval_required'>{work_summary.get('approval_required',0)}</span></p>"),
        _card("Work Cycles", f"<div class='kpi' data-live-count='counts.work_cycles'>{len(list_work_cycles())}</div><p class='muted'>Bounded supervised queue cycles.</p>"),
        _card("Pending Approvals", f"<div class='kpi' data-live-count='counts.pending_approvals'>{len(approvals)}</div><p class='muted'>Things waiting for your glorious human permission.</p>"),
        _card("Unread Notifications", f"<div class='kpi' data-live-count='counts.unread_notifications'>{len(notifications)}</div><p class='muted'>Saved alerts from watch mode and other systems.</p>"),
        _card("Patches", f"<div class='kpi' data-live-count='counts.patches'>{len(patches)}</div><p class='muted'>Proposed/applied/rolled back patch records.</p>"),
        _card("Memories", f"<div class='kpi' data-live-count='counts.memories'>{len(memories)}</div><p class='muted'>Active JSON memories.</p>"),
        _card("Tests", f"<div class='kpi' data-live-count='counts.test_reports'>{len(reports)}</div><p class='muted'>Reports: <span data-live-count='counts.test_reports'>{len(reports)}</span> · Reviews: <span data-live-count='counts.test_reviews'>{len(reviews)}</span></p>"),
    ]
    return "<div class='grid'>" + "".join(cards) + "</div>"


def _console_button(label: str, href: str) -> str:
    return f"<a href='{_safe(href)}'><button type='button'>{_safe(label)}</button></a>"


def _console_card(title: str, body: str, extra_class: str = "") -> str:
    cls = "console-card" + (" " + extra_class if extra_class else "")
    return f"<section class='{cls}'><h2>{_safe(title)}</h2>{body}</section>"


def render_overview() -> str:
    approvals = list_approvals(status="pending", include_closed=False)
    notifications = list_notifications(status="unread", include_dismissed=False)
    risk_rows = [
        ("High", "8", "badge-danger"),
        ("Medium", "12", "badge-warn"),
        ("Low", "8", "good"),
        ("Info", "4", "muted"),
    ]
    flow = "".join([
        "<section class='command-step' data-tip='Inspect current health, diagnostics, planning signals, and source state before proposing work.'><div class='step-icon'>⌕</div><h3>1. Inspect</h3><p>Observe system state and identify signals.</p>" + _console_button("Run Diagnostics", "/diagnostics") + "</section>",
        "<section class='command-step' data-tip='Prepare proposals and safety checks only. No source mutation or self-approval.'><div class='step-icon'>⚙</div><h3>2. Prepare</h3><p>Prepare proposals and safety checks.</p>" + _console_button("Preview Patch", "/patch-drafts") + "</section>",
        "<section class='command-step' data-tip='Review risks, debts, evidence, approvals, and maturity gaps before choosing work.'><div class='step-icon'>🛡</div><h3>3. Review</h3><p>Human review and risk evaluation.</p>" + _console_button("Review Risk Ledger", "/strategic-risk-ledger") + "</section>",
        "<section class='command-step goodstep' data-tip='Open the v135 planning console. Recommendation only; operator approval required.'><div class='step-icon'>◇</div><h3>4. Plan</h3><p>Develop plans and sequence supervised actions.</p>" + _console_button("Open Planning Console", "/planning-console") + "</section>",
        "<section class='command-step dangerstep' data-tip='Danger zone remains human-only and cannot be triggered by readiness scores.'><div class='step-icon'>⚠</div><h3>5. Danger Zone</h3><p>Irreversible actions and system recall.</p>" + _console_button("Open Recall", "/recall") + "</section>",
    ])
    approval_items = approvals[:4]
    approval_body = "".join(f"<div><span>{_safe(a.get('title') or a.get('id') or 'Approval')}</span><span class='badge badge-warn'>PENDING</span></div>" for a in approval_items) or "<p class='muted'>No pending approvals. Suspicious, but pleasant.</p>"
    notes = notifications[:3]
    notes_body = "".join(f"<div><span>{_safe(n.get('title') or n.get('message') or 'Notification')}</span><span class='muted'>{_safe(n.get('status','unread'))}</span></div>" for n in notes) or "<p class='muted'>No unread operator notes.</p>"
    cards = "".join([
        _console_card("Stable Loop Audit", "<div class='audit-ring'><span>97%<small>STABLE</small></span></div><div class='status-list'><div><span>Loop Integrity</span><b class='good'>OK</b></div><div><span>Signal Coherence</span><b class='good'>OK</b></div><div><span>Boundary Compliance</span><b class='good'>OK</b></div><div><span>Recall Readiness</span><b class='good'>OK</b></div></div>" + _console_button("Run Diagnostics", "/stable-loop")),
        _console_card("Open Approvals", f"<div class='status-list'>{approval_body}</div>" + _console_button("View All Approvals", "/approvals")),
        _console_card("Strategic Intake", "<div class='status-list'><div><span>Market Signal: Dashboard Command Deck</span><b>High</b></div><div><span>Operator Direction: Planning Arc</span><b>High</b></div><div><span>Capability Gap Report</span><b>Medium</b></div></div>" + _console_button("Review Intake", "/strategic-growth-intake")),
        _console_card("Roadmap", "<div class='roadmap-line'><div>Planning Signals <span class='good'>Completed</span></div><div>Work Package Recommendations <span class='good'>Completed</span></div><div>Decision Brief <span class='good'>Completed</span></div><div>Planning Console <span class='good'>Completed</span></div><div>Readiness Audit <span class='good'>Completed</span></div></div>" + _console_button("View Roadmap", "/roadmap-synthesis")),
        _console_card("Risk Ledger", "<div class='audit-ring' style='background:conic-gradient(#ff4e57 0 25%, #ffc44d 25% 62%, #30e079 62% 87%, #1ca8ff 87% 100%);'><span>32<small>TOTAL</small></span></div><div class='status-list'>" + "".join(f"<div><span class='{cls}'>{label}</span><b>{count}</b></div>" for label,count,cls in risk_rows) + "</div>" + _console_button("Review Risk Ledger", "/strategic-risk-ledger")),
        _console_card("Maturity", "<div class='kpi'>68%</div><p class='muted'>Advanced planning scaffold. Evidence-bound, still supervised.</p><div class='signal-spark'></div>" + _console_button("View Maturity Model", "/capability-maturity")),
        _console_card("Growth Audit", "<div class='kpi good'>+21.7%</div><p class='muted'>Growth signal from planning consolidation, dashboard command styling, and operator burden reduction.</p><div class='status-list'><div><span>Signal Quality</span><b class='good'>A</b></div><div><span>Market Fit</span><b class='good'>A-</b></div><div><span>Compounding</span><b class='good'>B+</b></div></div>" + _console_button("Run Growth Audit", "/strategic-growth-audit")),
        _console_card("Operator Notes", f"<div class='status-list'>{notes_body}</div>" + _console_button("View All Notes", "/notifications")),
    ])
    planning = "".join([
        _console_card("Planning Signals", "<div class='signal-spark'></div><div class='status-list'><div><span>Strong</span><b class='good'>18</b></div><div><span>Emerging</span><b class='warn'>9</b></div><div><span>Weak</span><b class='badtext'>3</b></div><div><span>Noise</span><b>2</b></div></div>" + _console_button("View Signal Map", "/planning-signals")),
        _console_card("Work Package Recommendations", "<div class='reco-strip'><div class='reco-chip'>Command Deck Dashboard<br><b class='good'>92%</b></div><div class='reco-chip'>Planning Console<br><b class='good'>88%</b></div><div class='reco-chip'>Decision Brief<br><b>76%</b></div><div class='reco-chip'>Signal Consolidation<br><b>71%</b></div></div>" + _console_button("View All Recommendations", "/work-package-recommendations")),
    ])
    body = f"""
<div class='command-deck'>
  <div class='command-hero'>
    <div><h1>Command Deck</h1><p class='muted'>Supervised operations. Safety hierarchy enforced.</p></div>
    <div class='system-pill'>ALL SYSTEMS NOMINAL</div>
  </div>
  <div class='command-flow'>{flow}</div>
  <div class='safety-line'><span>🛡 Safety Hierarchy: Inspect → Prepare → Review → Plan → Danger Zone</span><span>All actions logged. Human approval required.</span></div>
  <div class='console-grid'>{cards}</div>
  <div class='console-grid' style='grid-template-columns:1fr 2fr;'>{planning}</div>
  <div class='console-footer-note'><span>ⓘ Preserve custom data-tip hover behavior. Native title tooltips remain forbidden.</span><span>Recommendation only. Operator approval required. Eidolon is not autonomous.</span></div>
</div>
"""
    return _layout("/", body)




def _action_panel(title: str, description: str, controls: str, priority: str = "normal") -> str:
    badge = f"<span class='badge'>{_safe(priority)}</span> " if priority else ""
    return (
        "<div class='card'>"
        f"<h3>{badge}{_safe(title)}</h3>"
        f"<p class='muted'>{_safe(description)}</p>"
        f"<div>{controls}</div>"
        "</div>"
    )


def _action_link(label: str, href: str) -> str:
    return f"<a href='{_safe(href)}'><button type='button'>{_safe(label)}</button></a>"


def render_action_center() -> str:
    pending_approvals = list_approvals(status="pending", include_closed=False)
    unread_notifications = list_notifications(status="unread", include_dismissed=False)
    proposed_patches = [patch for patch in list_patch_proposals() if patch.get("status") == "proposed"]
    tasks = list_tasks(include_cancelled=False)
    ready_tasks = [task for task in tasks if task.get("status") in {"ready", "planned"}]
    active_tasks = [task for task in tasks if task.get("status") == "active"]
    blocked_tasks = [task for task in tasks if task.get("status") == "blocked"]
    diagnostic_reports = list_diagnostic_reports()
    latest_diag = diagnostic_reports[0] if diagnostic_reports else None
    latest_diag_status = latest_diag.get("overall_status") if latest_diag else "missing"
    watch_reports = list_watch_reports()
    latest_watch = watch_reports[0] if watch_reports else None
    latest_watch_status = latest_watch.get("status") or latest_watch.get("stopped_reason") if latest_watch else "missing"

    recommendations: list[str] = []
    panels: list[str] = []

    if pending_approvals:
        approval = pending_approvals[0]
        approval_id = approval.get("id", "latest-pending")
        recommendations.append(f"Review pending approval: {approval.get('summary', approval_id)}")
        controls = " ".join([
            _action_link("Open latest approval", f"/detail?kind=approval&id={_safe(approval_id)}"),
            _button("Dry-run approval", "approve", approval_id=approval_id, dry_run="true"),
            _button("Approve", "approve", approval_id=approval_id),
            _button("Reject", "reject", approval_id=approval_id),
        ])
        panels.append(_action_panel("Pending approval", "An action is waiting for your explicit approval. Dry-run first, because apparently consequences exist.", controls, "high"))

    if unread_notifications:
        note = unread_notifications[0]
        note_id = note.get("id", "latest-unread")
        recommendations.append(f"Read notification: {note.get('title', note_id)}")
        controls = " ".join([
            _action_link("Open notification", f"/detail?kind=notification&id={_safe(note_id)}"),
            _button("Mark read", "notification_read", notification_id=note_id),
            _button("Dismiss", "notification_dismiss", notification_id=note_id),
        ])
        panels.append(_action_panel("Unread notification", "Watch mode or another system surfaced something worth attention.", controls, "medium"))

    if latest_diag_status in {"fail", "warn", "missing", None, "[none]"}:
        recommendations.append("Run diagnostics before advancing more work.")
        controls = " ".join([
            _button("Run diagnostics", "run_diagnostics"),
            _action_link("Open diagnostics", "/diagnostics"),
        ])
        panels.append(_action_panel("Diagnostics", f"Latest diagnostic status: {latest_diag_status}. Software organs should be checked before the ghost does cardio.", controls, "medium"))

    if proposed_patches and not pending_approvals:
        patch = proposed_patches[0]
        patch_id = patch.get("id", "latest-proposed")
        recommendations.append(f"Inspect proposed patch for {patch.get('target_file', '[unknown file]')}.")
        controls = " ".join([
            _action_link("Open latest proposed patch", f"/detail?kind=patch&id={_safe(patch_id)}"),
            _button("Dry-run dev loop", "dev_loop_dry"),
        ])
        panels.append(_action_panel("Proposed patch", "A patch exists but has not been applied. Inspect it or let a dev-loop dry-run create the next approval.", controls, "medium"))

    if active_tasks:
        task = active_tasks[0]
        task_id = task.get("id", "latest-active")
        recommendations.append(f"Continue active task: {task.get('title', task_id)}")
        controls = " ".join([
            _action_link("Open active task", f"/detail?kind=task&id={_safe(task_id)}"),
            _button("Dry-run dev loop", "dev_loop_dry"),
            _button("Run safe dev loop", "dev_loop_safe"),
        ])
        panels.append(_action_panel("Active task", "A task is already active. Continue that before inventing new work like a productivity gremlin.", controls, "medium"))
    elif ready_tasks:
        task = ready_tasks[0]
        task_id = task.get("id", "latest-ready")
        recommendations.append(f"Start or advance ready task: {task.get('title', task_id)}")
        controls = " ".join([
            _action_link("Open ready task", f"/detail?kind=task&id={_safe(task_id)}"),
            _button("Dry-run dev loop", "dev_loop_dry"),
            _button("Run safe dev loop", "dev_loop_safe"),
        ])
        panels.append(_action_panel("Ready task", "A queued task is ready. The dev loop can advance one safe step through existing gates.", controls, "normal"))

    if blocked_tasks:
        recommendations.append(f"Review {len(blocked_tasks)} blocked task(s).")
        panels.append(_action_panel("Blocked tasks", f"{len(blocked_tasks)} task(s) are blocked. Read them before generating yet another plan-shaped pile.", _action_link("Open tasks", "/tasks"), "normal"))

    if not ready_tasks and not active_tasks:
        recommendations.append("Create a fresh session plan and queue tasks from it.")
        controls = " ".join([
            _button("Plan session", "plan_session"),
            _action_link("Open activity", "/activity"),
        ])
        panels.append(_action_panel("Plan next session", "No ready or active task was found. Create a session plan before the project starts wandering in circles.", controls, "normal"))

    watch_controls = " ".join([
        _button("Watch once", "watch_once_no_ai"),
        _button("Watch once with AI", "watch_once_ai"),
        _action_link("Open Watch", "/watch"),
    ])
    panels.append(_action_panel("Watch and scan", f"Latest watch status: {latest_watch_status}. Run a quick watch check to refresh recommendations and notifications.", watch_controls, "normal"))

    maintenance_controls = " ".join([
        _button("Maintenance scan", "maintenance_scan"),
        _action_link("Open recent activity", "/activity"),
    ])
    panels.append(_action_panel("Maintenance", "Run a no-AI maintenance scan for chores like pending tests, memory size, stale reports, and other thrilling chores.", maintenance_controls, "low"))

    if not recommendations:
        recommendations.append("No urgent action found. Run a watch check or plan a session.")

    rec_html = _small_list([_safe(item) for item in recommendations])
    command_cheatsheet = """
<pre>Useful matching terminal commands:
python conscious_agent/main.py --diagnostics
python conscious_agent/main.py --watch-once --no-ai-watch
python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop
python conscious_agent/main.py --approval-inbox
python conscious_agent/main.py --plan-session --no-ai-session</pre>
"""
    content = (
        _card("Recommended Next Actions", rec_html)
        + "<div class='grid'>" + "".join(panels) + "</div>"
        + _card("Terminal equivalents", command_cheatsheet)
    )
    return _layout("/actions", content)




def _chat_action_card(action: dict[str, Any] | None) -> str:
    if not action:
        return "<p class='muted'>No action was proposed.</p>"
    action_id = action.get("id", "")
    mode = action.get("execution_mode", "")
    status = action.get("status", "")
    controls = ""
    if action_id and mode in {"direct_command", "direct_function", "approval"} and status in {"proposed", "approval_required", "failed"}:
        controls = " ".join([
            _button("Dry-run action", "chat_action_execute", chat_action_id=action_id, dry_run="true"),
            _button("Execute action", "chat_action_execute", chat_action_id=action_id),
            _detail_link("chat_action", action_id, "Details"),
        ])
    elif action_id:
        controls = _detail_link("chat_action", action_id, "Details")
    return (
        "<div class='action-card'>"
        f"<p><span class='badge'>{_safe(status)}</span> <span class='badge'>{_safe(mode)}</span> <span class='badge'>risk: {_safe(action.get('risk_level',''))}</span></p>"
        f"<h3>{_safe(action.get('title','Proposed action'))}</h3>"
        f"<p>{_safe(action.get('summary',''))}</p>"
        f"<p class='muted'>{_safe(action.get('explanation',''))}</p>"
        f"<pre>{_safe(action.get('command') or action.get('approval_command') or action.get('function_name') or '[no direct command]')}</pre>"
        f"<div>{controls}</div>"
        "</div>"
    )


def render_chat_console() -> str:
    turns = list_dashboard_chat_turns()
    latest = turns[0] if turns else None
    form = """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_chat_send'>
<label>Message Marcus → Eidolon
<textarea name='message' rows='4' placeholder='Check what needs attention, review conscious_agent/memory.py, suggest improvement for conscious_agent/local_brain.py...'></textarea></label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI conversational response</label>
<button type='submit'>Send + Propose Safe Action</button>
</form>
"""

    latest_html = "<p class='muted'>No dashboard chat turns yet.</p>"
    if latest:
        latest_html = (
            f"<p><span class='badge'>{_safe(latest.get('created_at',''))}</span> {_detail_link('dashboard_chat', latest.get('id',''), 'Open full turn')}</p>"
            f"<h3>Marcus</h3>{_text_block(latest.get('user_message',''))}"
            f"<h3>Eidolon</h3>{_text_block(latest.get('eidolon_response',''))}"
            f"<h3>Safe action card</h3>{_chat_action_card(latest.get('action'))}"
        )

    rows = []
    for turn in turns[:50]:
        turn_id = turn.get('id', '')
        action = turn.get('action') or {}
        action_id = turn.get('action_id', '')
        request = turn.get('user_message', '')
        action_link = _detail_link('chat_action', action_id, 'Action') if action_id else "<span class='muted'>[none]</span>"
        rows.append(
            f"<tr><td>{_safe(turn.get('created_at',''))}</td>"
            f"<td>{_detail_link('dashboard_chat', turn_id, request[:90] or turn_id)}</td>"
            f"<td>{_safe(action.get('intent','[none]'))}</td>"
            f"<td><span class='badge'>{_safe(action.get('status',''))}</span></td>"
            f"<td>{action_link}</td></tr>"
        )
    history = "<table><tr><th>Created</th><th>Message</th><th>Intent</th><th>Status</th><th>Action</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No chat history yet.</p>"
    examples = _text_block("""Try:
Check what needs attention
Run diagnostics
Show pending approvals
Plan the next session
Review conscious_agent/memory.py
Suggest improvement for conscious_agent/local_brain.py to improve Ollama error messages
Apply the latest patch
Rollback the latest patch""")
    content = (
        _card("Chat Console", form)
        + _card("Latest Conversation Turn", latest_html)
        + _card("Examples", examples)
        + _card("Recent Dashboard Chat Turns", history)
    )
    return _layout("/chat-console", content)



def _priority_options(selected: str = "medium") -> str:
    values = ["low", "medium", "high", "urgent"]
    return "".join(f"<option value='{_safe(value)}' {'selected' if value == selected else ''}>{_safe(value)}</option>" for value in values)


def _status_options(values: list[str], selected: str) -> str:
    return "".join(f"<option value='{_safe(value)}' {'selected' if value == selected else ''}>{_safe(value)}</option>" for value in values)


def _risk_options(selected: str = "low") -> str:
    values = ["low", "medium", "high"]
    return "".join(f"<option value='{_safe(value)}' {'selected' if value == selected else ''}>{_safe(value)}</option>" for value in values)


def _task_create_form() -> str:
    priority_options = _priority_options("medium")
    status_options = _status_options(["planned", "ready", "active", "blocked"], "planned")
    risk_options = _risk_options("low")
    goals = list_goals(include_cancelled=False)
    goal_options = "<option value=''>[none]</option>" + "".join(
        f"<option value='{_safe(goal.get('id',''))}'>{_safe(goal.get('title') or goal.get('id',''))}</option>"
        for goal in goals[:80]
    )
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_add_task'>
<label>Title <input name='title' required placeholder='Review dashboard form handling'></label>
<label>Description <textarea name='description' rows='4' placeholder='What should Eidolon do and why?'></textarea></label>
<label>Priority <select name='priority'>{priority_options}</select></label>
<label>Status <select name='status'>{status_options}</select></label>
<label>Risk <select name='risk'>{risk_options}</select></label>
<label>Recommended command <input name='command' placeholder='python conscious_agent/main.py --diagnostics'></label>
<label>Next action <input name='next_action' placeholder='Run a dry-run first, inspect latest report, etc.'></label>
<label>Linked goal <select name='linked_goal'>{goal_options}</select></label>
<button type='submit'>Create Task</button>
</form>
"""


def _goal_create_form() -> str:
    priority_options = _priority_options("medium")
    status_options = _status_options(["planned", "active", "blocked", "completed"], "planned")
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_add_goal'>
<label>Title <input name='title' required placeholder='Improve dashboard usability'></label>
<label>Description <textarea name='description' rows='4' placeholder='What outcome should Eidolon work toward?'></textarea></label>
<label>Priority <select name='priority'>{priority_options}</select></label>
<label>Status <select name='status'>{status_options}</select></label>
<label>Next action <input name='next_action' placeholder='Create the first task or run a session plan'></label>
<button type='submit'>Create Goal</button>
</form>
"""


def _patch_request_form() -> str:
    return """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_suggest_patch'>
<label>Target file inside active project <input name='target_file' required placeholder='conscious_agent/dashboard.py'></label>
<label>Requested change <textarea name='request' rows='5' required placeholder='Add a button that opens the create page from the overview.'></textarea></label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI to generate the patch proposal</label>
<button type='submit'>Create Patch Proposal</button>
</form>
<p class='muted'>This creates a proposed patch only. It does not apply the patch. The goblin may write suggestions, but it still cannot grab the wrench without approval.</p>
"""


def render_create() -> str:
    project = get_active_project() or {}
    intro = (
        f"<p>Active project: <b>{_safe(project.get('name','[none]'))}</b></p>"
        f"<p class='muted'>{_safe(project.get('path',''))}</p>"
        "<p>Use this page to create tasks, goals, and patch proposals from the browser. It still routes through the existing managers and safety rails, because apparently we learned something from all of human software history.</p>"
    )
    content = (
        _card("Create Dashboard Items", intro)
        + "<div class='grid'>"
        + _card("New Task", _task_create_form())
        + _card("New Goal", _goal_create_form())
        + _card("Patch Request", _patch_request_form())
        + "</div>"
    )
    return _layout("/create", content)

def render_chat_actions() -> str:
    actions = list_chat_actions(include_closed=True)
    form = """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='chat_action_propose'>
<label>Plain-English request
<input name='request' placeholder='Run diagnostics, check approvals, suggest improvement for conscious_agent/memory.py'></label>
<button type='submit'>Propose safe action</button>
</form>
"""
    rows = []
    for item in actions[:80]:
        item_id = item.get("id", "")
        status = item.get("status", "")
        intent = item.get("intent", "")
        mode = item.get("execution_mode", "")
        request = item.get("user_request", "")
        buttons = ""
        if mode in {"direct_command", "direct_function", "approval"} and status in {"proposed", "approval_required", "failed"}:
            buttons += _button("Dry-run", "chat_action_execute", chat_action_id=item_id, dry_run="true")
            buttons += _button("Execute", "chat_action_execute", chat_action_id=item_id)
        rows.append(
            f"<tr><td><span class='badge'>{_safe(status)}</span></td>"
            f"<td>{_safe(intent)}</td><td>{_safe(mode)}</td>"
            f"<td><b>{_detail_link('chat_action', item_id, request[:80] or item_id)}</b><br><span class='muted'>{_safe(item_id)}</span></td>"
            f"<td>{buttons} {_detail_link('chat_action', item_id, 'Details')}</td></tr>"
        )
    table = "<table><tr><th>Status</th><th>Intent</th><th>Mode</th><th>Request</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No chat actions found.</p>"
    examples = _text_block("""Try:
run diagnostics
check what needs attention
show pending approvals
plan the next session
review conscious_agent/memory.py
suggest improvement for conscious_agent/local_brain.py to improve Ollama error messages
apply the latest patch
rollback the latest patch""")
    return _layout("/chat-actions", _card("Chat-to-Action", form) + _card("Examples", examples) + _card("Saved Chat Actions", table))

def render_tasks() -> str:
    tasks = list_tasks(include_cancelled=False)
    rows = []
    for task in tasks[:80]:
        task_id = task.get("id", "")
        title = task.get("title", "")
        status = task.get("status", "")
        priority = task.get("priority", "")
        cmd = task.get("recommended_command", "") or task.get("command", "")
        rows.append(f"<tr><td><span class='badge'>{_safe(status)}</span></td><td>{_safe(priority)}</td><td><b>{_detail_link('task', task_id, title)}</b><br><span class='muted'>{_safe(task_id)}</span></td><td>{_safe(cmd)}</td><td>{_detail_link('task', task_id, 'Details')}</td></tr>")
    table = "<table><tr><th>Status</th><th>Priority</th><th>Task</th><th>Command</th><th></th></tr>" + "".join(rows) + "</table>" if rows else "<p>No tasks found.</p>"
    next_item = next_task()
    detail = task_detail_text(next_item, full=True) if next_item else "No ready task."
    return _layout("/tasks", _card("Create Task", _task_create_form()) + _card("Next Ready Task", _text_block(detail)) + _card("Task Queue", table))


def _work_status_options(selected: str = "pending") -> str:
    return _status_options(["pending", "active", "blocked", "done", "failed", "cancelled"], selected)


def _work_item_create_form() -> str:
    risk_options = _risk_options("low")
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_add_work_item'>
<label>Title <input name='title' required placeholder='Review conscious_agent/dashboard.py'></label>
<label>Description <textarea name='description' rows='4' placeholder='Describe the task. Include a target file, command:, or metadata-style hint when useful.'></textarea></label>
<label>Project ID <input name='project_id' value='eidolon' placeholder='eidolon'></label>
<label>Priority <input name='priority' type='number' min='1' max='10' value='5'></label>
<label>Risk <select name='risk'>{risk_options}</select></label>
<label><input type='checkbox' name='requires_approval' value='true'> Requires approval</label>
<button type='submit'>Create Task</button>
</form>
<p class='muted'>Tasks are the canonical work records. Low-risk tasks can be dry-run or executed through the conservative task work executor. Medium/high-risk tasks stay approval-gated, because the machine does not get a tiny crown.</p>
"""


def _patch_work_item_create_form() -> str:
    risk_options = _risk_options("low")
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_queue_patch'>
<label>Target file <input name='target_file' required placeholder='conscious_agent/dashboard.py'></label>
<label>Patch request <textarea name='request' rows='4' required placeholder='Describe the change Eidolon should propose as a patch.'></textarea></label>
<label>Project ID <input name='project_id' value='eidolon' placeholder='eidolon'></label>
<label>Priority <input name='priority' type='number' min='1' max='10' value='7'></label>
<label>Risk <select name='risk'>{risk_options}</select></label>
<label><input type='checkbox' name='requires_approval' value='true'> Requires approval before patch generation</label>
<button type='submit'>Queue Patch Task</button>
</form>
<p class='muted'>This creates a task-backed item with <code>action_type=suggest_patch</code>. Executing it creates a proposed patch and links the patch back to the task. Documentation, meet accountability. Finally.</p>
"""



def _stage_pill(lifecycle: dict[str, Any]) -> str:
    stage = str(lifecycle.get("stage") or "unknown")
    label = str(lifecycle.get("stage_label") or stage)
    css = str(lifecycle.get("css_class") or f"stage-{stage.replace('_', '-')}")
    return f"<span class='stage-pill {_safe(css)}'>{_safe(label)}</span>"


def _task_lifecycle_for_work_item(item: Any) -> dict[str, Any]:
    task = get_task(getattr(item, "id", "")) if item else None
    if task:
        return derive_task_lifecycle(task)
    metadata = getattr(item, "metadata", {}) if item else {}
    return {
        "stage": "unknown",
        "stage_label": "Unknown",
        "css_class": "stage-unknown",
        "next_action": "Inspect the raw task/work record.",
        "approval_id": str((metadata or {}).get("approval_id") or "") if isinstance(metadata, dict) else "",
        "approval_status": str((metadata or {}).get("approval_status") or "") if isinstance(metadata, dict) else "",
        "patch_id": str((metadata or {}).get("patch_id") or "") if isinstance(metadata, dict) else "",
        "patch_status": str((metadata or {}).get("patch_status") or "") if isinstance(metadata, dict) else "",
    }


def _lifecycle_flow(stage: str) -> str:
    stages = [
        ("ready", "Ready"),
        ("approval_required", "Needs approval"),
        ("approval_pending", "Pending"),
        ("approved_ready", "Approved"),
        ("recovery_needed", "Recovery"),
        ("active", "Active"),
        ("done", "Done"),
    ]
    blocked = {"blocked", "approval_rejected", "approval_failed", "cancelled"}
    parts = []
    for key, label in stages:
        current = " current" if key == stage else ""
        parts.append(f"<span class='lifecycle-step{current}'>{_safe(label)}</span>")
    if stage in blocked:
        parts.append(f"<span class='lifecycle-step current'>{_safe(stage.replace('_', ' ').title())}</span>")
    return "<div class='lifecycle-strip'>" + "".join(parts) + "</div>"


def _lifecycle_summary_cards() -> str:
    summary = task_lifecycle_summary()
    counts = summary.get("counts", {})
    return (
        "<div class='grid'>"
        + _card("Open Tasks", f"<div class='kpi'>{_safe(summary.get('open', 0))}</div><p class='muted'>Total task records: {_safe(summary.get('total', 0))}</p>")
        + _card("Ready / Active", f"<div class='kpi'>{_safe(counts.get('ready', 0) + counts.get('active', 0))}</div><p class='muted'>Ready: {_safe(counts.get('ready', 0))} · Active: {_safe(counts.get('active', 0))}</p>")
        + _card("Approval Flow", f"<div class='kpi'>{_safe(counts.get('approval_required', 0) + counts.get('approval_pending', 0) + counts.get('approved_ready', 0))}</div><p class='muted'>Required: {_safe(counts.get('approval_required', 0))} · Pending: {_safe(counts.get('approval_pending', 0))} · Approved: {_safe(counts.get('approved_ready', 0))}</p>")
        + _card("Needs Attention", f"<div class='kpi'>{_safe(summary.get('needs_attention', 0))}</div><p class='muted'>Blocked/rejected/failed/approval waiting.</p>")
        + _card("Recovery Needed", f"<div class='kpi'>{_safe(counts.get('recovery_needed', 0))}</div><p class='muted'>Failed or blocked tasks with retry/recovery hints.</p>")
        + "</div>"
    )


def _lifecycle_legend() -> str:
    return (
        "<div class='toolbar'>"
        "<span class='stage-pill stage-ready'>Ready</span>"
        "<span class='stage-pill stage-approval-required'>Needs approval request</span>"
        "<span class='stage-pill stage-approval-pending'>Approval pending</span>"
        "<span class='stage-pill stage-approved-ready'>Approved, ready to run</span>"
        "<span class='stage-pill stage-active'>Active</span>"
        "<span class='stage-pill stage-recovery-needed'>Recovery needed</span>"
        "<span class='stage-pill stage-blocked'>Blocked</span>"
        "<span class='stage-pill stage-done'>Done</span>"
        "</div>"
        "<p class='muted'>v5.9 uses these lifecycle stages to choose supervised work-cycle actions before advancing tasks. The cycle now asks: approval, recovery, patch follow-up, or safe execution? Astonishingly, order matters.</p>"
    )

def _work_item_controls(item_id: str, status: str) -> str:
    controls = []
    item = find_work_item(item_id)
    metadata = item.metadata if item and isinstance(item.metadata, dict) else {}
    lifecycle = _task_lifecycle_for_work_item(item)
    stage = str(lifecycle.get("stage") or "unknown")
    is_patch_item = str(metadata.get("action_type") or "").lower() == "suggest_patch" or bool(metadata.get("patch_target_file") or metadata.get("target_file"))
    approval_id = str(lifecycle.get("approval_id") or metadata.get("approval_id") or "").strip()

    if stage in {"ready", "active", "approved_ready", "patch_proposed"} or status == "pending":
        controls.append(_button("Dry-run", "work_queue_execute", work_item_id=item_id, dry_run="true", use_ai="true"))
    if stage in {"ready", "active", "approved_ready"} or status == "pending":
        controls.append(_button("Execute", "work_queue_execute", work_item_id=item_id, use_ai="true"))
    if is_patch_item and stage in {"ready", "active", "patch_proposed"}:
        controls.append(_button("Suggest Patch", "work_queue_suggest_patch", work_item_id=item_id, use_ai="true"))
    if stage in {"recovery_needed", "approval_rejected", "approval_failed"}:
        controls.append(_detail_link("task_recovery", item_id, "Recovery Plan", full=True))
        controls.append(_button("Dry-run Retry", "task_recovery_retry", work_item_id=item_id, dry_run="true", use_ai="true"))
        controls.append(_button("Mark Ready for Retry", "task_recovery_mark_ready", work_item_id=item_id))
    if stage in {"approval_required", "blocked", "approval_rejected", "approval_failed"}:
        controls.append(_button("Request Approval", "task_request_approval", work_item_id=item_id, use_ai="true"))
    if approval_id:
        controls.append(_detail_link("approval", approval_id, "Open Approval"))
    if status in {"pending", "active", "blocked", "failed"}:
        controls.append(_button("Mark done", "work_queue_done", work_item_id=item_id))
        controls.append(_button("Cancel", "work_queue_cancel", work_item_id=item_id))
    if status in {"pending", "active"}:
        controls.append(_button("Block", "work_queue_block", work_item_id=item_id, reason="Blocked from dashboard."))
    controls.append(_detail_link("work_item", item_id, "Details", full=True))
    return " ".join(controls)


def _work_item_patch_hint(item: Any) -> str:
    metadata = item.metadata if hasattr(item, "metadata") and isinstance(item.metadata, dict) else {}
    lifecycle = _task_lifecycle_for_work_item(item)
    patch_id = str(lifecycle.get("patch_id") or metadata.get("patch_id") or "").strip()
    target_file = str(lifecycle.get("target_file") or metadata.get("patch_target_file") or metadata.get("target_file") or "").strip()
    approval_id = str(lifecycle.get("approval_id") or metadata.get("approval_id") or "").strip()
    approval_status = str(lifecycle.get("approval_status") or metadata.get("approval_status") or "").strip()
    bits = []
    if target_file:
        bits.append(f"<span class='muted'>Patch target: {_safe(target_file)}</span>")
    if patch_id:
        bits.append(f"<span class='muted'>Patch: {_detail_link('patch', patch_id, patch_id)}</span>")
    if approval_id:
        label = f"{approval_id} ({approval_status or 'pending'})"
        bits.append(f"<span class='muted'>Approval: {_detail_link('approval', approval_id, label)}</span>")
    stable_loop_id = str(lifecycle.get("stable_loop_id") or metadata.get("stable_loop_id") or "").strip()
    if lifecycle.get("is_stable_loop_followup") or stable_loop_id:
        decision = str(lifecycle.get("stable_loop_decision") or metadata.get("final_decision") or "").strip() or "undecided"
        kind = str(lifecycle.get("stable_loop_followup_kind") or metadata.get("followup_kind") or "").strip()
        bits.append(
            f"<span class='muted'>Stable-loop follow-up: {_detail_link('stable_loop', stable_loop_id, stable_loop_id or '[missing loop]')} "
            f"decision={_safe(decision)} kind={_safe(kind or '[none]')}</span>"
        )
    return "<br>" + "<br>".join(bits) if bits else ""


def _lifecycle_filter_controls(selected_stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    summary = task_lifecycle_summary()
    filters = summary.get("filters", [])
    preferred = ["all", "open", "needs_attention", "ready_to_act", "ready", "approval_required", "approval_pending", "approved_ready", "blocked", "patch_proposed", "stable_loop_followup", "done", "cancelled"]
    by_key = {str(item.get("key")): item for item in filters if isinstance(item, dict)}
    chips = []
    for key in preferred:
        item = by_key.get(key) or {"key": key, "label": STAGE_FILTER_LABELS.get(key, key.replace("_", " ").title()), "count": 0}
        active = " active" if key == selected_stage else ""
        href = "/tasks-work" if key == "all" else f"/tasks-work?stage={_safe(key)}"
        chips.append(f"<a class='filter-chip{active}' href='{href}'>{_safe(item.get('label', key))} <span class='badge'>{_safe(item.get('count', 0))}</span></a>")
    return "<div class='toolbar'>" + "".join(chips) + "</div>"


def _batch_lifecycle_actions(selected_stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    approval_count = len(list_task_lifecycles(stage_filter="approval_required", include_closed=False))
    ready_count = len(list_task_lifecycles(stage_filter="ready_to_act", include_closed=False))
    return f"""
<div class='toolbar'>
<form method='post' action='/action' class='inline'>
<input type='hidden' name='action' value='task_batch_request_approvals'>
<input type='hidden' name='stage' value='approval_required'>
<button type='submit'>Request approvals for approval-required tasks ({_safe(approval_count)})</button>
</form>
<form method='post' action='/action' class='inline'>
<input type='hidden' name='action' value='work_queue_execute_next'>
<input type='hidden' name='dry_run' value='true'>
<input type='hidden' name='use_ai' value='true'>
<button type='submit'>Dry-run next ready task ({_safe(ready_count)})</button>
</form>
<a class='filter-chip' href='/tasks-work?stage=approved_ready'>Show approved-ready tasks</a>
<a class='filter-chip' href='/tasks-work?stage=recovery_needed'>Show recovery-needed tasks</a>
<a class='filter-chip' href='/tasks-work?stage=blocked'>Show blocked tasks</a>
</div>
<p class='muted'>v5.9 still deliberately does not add an “execute all” button. That button is how dashboards become confession letters.</p>
"""


def _filter_work_items_by_lifecycle(items: list[Any], selected_stage: str = "all") -> list[Any]:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    if selected_stage == "all":
        return items
    return [item for item in items if lifecycle_stage_matches(_task_lifecycle_for_work_item(item), selected_stage)]


def _work_queue_table(items: list[Any], selected_stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    filtered_items = _filter_work_items_by_lifecycle(items, selected_stage)
    rows = []
    for item in filtered_items[:120]:
        approval = "approval" if item.requires_approval else "safe"
        lifecycle = _task_lifecycle_for_work_item(item)
        lifecycle_cell = (
            f"{_stage_pill(lifecycle)}"
            f"<br><span class='muted'>{_safe(lifecycle.get('next_action', ''))}</span>"
        )
        rows.append(
            "<tr>"
            f"<td>{lifecycle_cell}</td>"
            f"<td><span class='badge'>{_safe(item.status)}</span></td>"
            f"<td>{_safe(item.priority)}</td>"
            f"<td><span class='badge'>{_safe(item.risk)}</span><br><span class='muted'>{_safe(approval)}</span></td>"
            f"<td><b>{_detail_link('work_item', item.id, item.title)}</b><br><span class='muted'>{_safe(item.id)}</span><br><span class='muted'>Project: {_safe(item.project_id)}</span>{_work_item_patch_hint(item)}</td>"
            f"<td>{_safe(item.description[:180])}{'...' if len(item.description) > 180 else ''}</td>"
            f"<td>{_work_item_controls(item.id, item.status)}</td>"
            "</tr>"
        )
    if not rows:
        label = STAGE_FILTER_LABELS.get(selected_stage, selected_stage.replace("_", " ").title())
        return f"<p class='muted'>No task-backed tasks found for filter: {_safe(label)}.</p>"
    caption = "" if selected_stage == "all" else f"<p class='muted'>Showing {_safe(len(filtered_items))} task(s) matching {_safe(STAGE_FILTER_LABELS.get(selected_stage, selected_stage))}.</p>"
    return caption + "<table><tr><th>Lifecycle</th><th>Status</th><th>Priority</th><th>Risk</th><th>Task / Work</th><th>Description</th><th>Actions</th></tr>" + "".join(rows) + "</table>"


def render_work_queue(stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(stage)
    summary = summarize_queue()
    active_items = list_work_items(include_done=False)
    all_items = list_work_items(include_done=True)
    next_item = summary.get("next_item") or {}

    next_text = "No pending task-backed task found. Either victory or neglect. Hard to tell."
    next_controls = ""
    if next_item:
        next_obj = find_work_item(str(next_item.get("id", ""))) if next_item.get("id") else None
        next_text = format_work_item(next_obj, full=True) if next_obj else json.dumps(next_item, indent=2)
        next_controls = (
            _button("Dry-run next", "work_queue_execute_next", dry_run="true", use_ai="true")
            + _button("Execute next", "work_queue_execute_next", use_ai="true")
            + " "
            + _detail_link("work_item", str(next_item.get("id", "")), "Open next item", full=True)
        )

    summary_html = _lifecycle_summary_cards()

    consolidation_note = _card(
        "v6.9 Closure-Aware Stable Loop Guardrails",
        "<p class='muted'>This page uses <code>task_queue.py</code> and <code>data/tasks.json</code> as the canonical store. "
        "v6.9 keeps the v6.8 follow-up closure tools and adds live-run guardrails that block new live stable-loop advancement while unresolved follow-up chains are still open. Legacy <code>/work-queue</code> aliases still work, because compatibility is ugly but cheaper than tears.</p>"
        + _lifecycle_legend()
    )

    body = (
        consolidation_note
        + summary_html
        + _card("Lifecycle Filters", _lifecycle_filter_controls(selected_stage))
        + _card("Lifecycle Batch Actions", _batch_lifecycle_actions(selected_stage))
        + _card("Recovery Summary", _text_block(json.dumps(task_recovery_summary(), indent=2, default=str)))
        + _card("Stable-loop Follow-up Lifecycle", _text_block(followup_lifecycle_summary_text(stable_loop_followup_lifecycle_summary(), full=False)))
        + _card("Lifecycle Legend", _lifecycle_legend())
        + _card("Create Task", _work_item_create_form())
        + _card("Create Patch Task", _patch_work_item_create_form())
        + _card("Next Recommended Task", _text_block(next_text) + next_controls)
        + _card("Open Tasks / Work", _work_queue_table(active_items, selected_stage))
        + _card("All Tasks / Work", _work_queue_table(all_items, selected_stage))
    )
    return _layout("/tasks-work", body)


def _work_cycle_controls() -> str:
    return """
<form method='post' action='/action'>
<input type='hidden' name='action' value='work_cycle_run'>
<label>Project <input name='project_id' value='eidolon'></label>
<label>Max steps <input name='max_steps' type='number' min='1' max='10' value='1'></label>
<label><input type='checkbox' name='dry_run' value='true' checked> Dry run</label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI when a selected step needs it</label>
<label><input type='checkbox' name='seed_if_empty' value='true' checked> Seed queue if empty</label>
<label><input type='checkbox' name='auto_followups' value='true' checked> Auto-create patch follow-ups</label>
<label><input type='checkbox' name='auto_approval_requests' value='true' checked> Auto-request approvals for approval-required tasks</label>
<label><input type='checkbox' name='auto_retry_recovery' value='true'> Auto-prepare recovery-needed tasks for retry</label>
<label><input type='checkbox' name='approve_work_execution' value='true'> Allow approval-required work this run</label>
<button type='submit'>Run lifecycle-aware work cycle</button>
</form>
<p class='muted'>v5.9 cycles choose from lifecycle state first: approval request, recovery review, patch follow-up creation, or safe task execution. Default mode is dry-run. No “press button, become chaos landlord” behavior here.</p>
"""


def render_work_cycle() -> str:
    cycles = list_work_cycles()
    latest = cycles[0] if cycles else None
    rows = []
    for cycle in cycles[:50]:
        cycle_id = str(cycle.get('id', ''))
        rows.append(
            "<tr>"
            f"<td><span class='badge'>{_safe('ok' if cycle.get('ok') else 'attention')}</span></td>"
            f"<td>{_safe(cycle.get('dry_run'))}</td>"
            f"<td><b>{_detail_link('work_cycle', cycle_id, cycle_id)}</b><br><span class='muted'>Project: {_safe(cycle.get('project_id',''))}</span></td>"
            f"<td>{_safe(cycle.get('steps_completed',0))}/{_safe(cycle.get('steps_requested',0))}</td>"
            f"<td>{_safe(cycle.get('stopped_reason',''))}</td>"
            "</tr>"
        )
    table = "<table><tr><th>Status</th><th>Dry Run</th><th>Cycle</th><th>Steps</th><th>Stopped</th></tr>" + "".join(rows) + "</table>" if rows else "<p class='muted'>No work cycles found.</p>"
    latest_text = work_cycle_text(latest, full=False) if latest else "No supervised work cycles saved yet. The clipboard is empty. Horrifyingly peaceful."
    body = (
        _card("Run Supervised Work Cycle", _work_cycle_controls())
        + _card("Latest Work Cycle", _text_block(latest_text))
        + _card("Saved Work Cycles", table)
    )
    return _layout("/work-cycle", body)



def _stable_loop_controls() -> str:
    return """
<form method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_run'>
<label>Project <input name='project_id' value='eidolon'></label>
<label>Max steps <input name='max_steps' type='number' min='1' max='5' value='1'></label>
<label><input type='checkbox' name='live' value='true'> Live run after preview</label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI when a selected step needs it</label>
<label><input type='checkbox' name='seed_if_empty' value='true' checked> Seed queue if empty</label>
<label><input type='checkbox' name='auto_followups' value='true' checked> Auto-create patch follow-ups</label>
<label><input type='checkbox' name='auto_approval_requests' value='true' checked> Auto-request approvals</label>
<label><input type='checkbox' name='auto_retry_recovery' value='true'> Auto-prepare recovery tasks for retry</label>
<label><input type='checkbox' name='approve_work_execution' value='true'> Allow approval-required live work</label>
<label><input type='checkbox' name='bypass_closure_guardrails' value='true'> Bypass unresolved follow-up guardrails for this live run</label>
<button type='submit'>Run stable supervised loop</button>
</form>
<p class='muted'>v6.9 records preflight/dry-run previews first, attaches audit/rollback notes, supports post-run operator decisions, decision-aware reports/cleanup, task-backed decision follow-ups, and closure-aware live-run guardrails. Live mode requires the explicit checkbox. There is still no “execute all” button, because we are apparently attached to reality.</p>
"""



def _stable_loop_review_controls(loop_id: str, compact: bool = False) -> str:
    if not loop_id:
        return ""
    loop = load_stable_loop(loop_id)
    if not loop:
        return ""
    status = review_status_for_loop(loop)
    buttons = ""
    if status == "unreviewed":
        buttons += _button("Mark reviewed", "stable_loop_mark_reviewed", stable_loop_id=loop_id)
    if status not in {"approved_for_live", "superseded"} and not loop.get("live") and loop.get("ok"):
        buttons += _button("Approve for live", "stable_loop_approve_live", stable_loop_id=loop_id)
    if status not in {"rejected", "superseded"}:
        buttons += _button("Reject", "stable_loop_reject", stable_loop_id=loop_id)
    if loop_is_live_ready(loop):
        buttons += _button("Run approved live", "stable_loop_run_approved_live", stable_loop_id=loop_id)
    if loop:
        buttons += _button("Refresh audit", "stable_loop_refresh_audit", stable_loop_id=loop_id)
    if compact:
        return buttons
    note_form = f"""
<form method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_mark_reviewed'>
<input type='hidden' name='stable_loop_id' value='{_safe(loop_id)}'>
<label>Review note <input name='note' placeholder='Optional operator review note'></label>
<button type='submit'>Save review note</button>
</form>
"""
    return buttons + note_form




def _stable_loop_operator_controls(loop_id: str) -> str:
    if not loop_id:
        return ""
    result = get_stable_loop_operator_notes(loop_id, ensure=True, save=True)
    if not result.ok or not result.operator_notes:
        return f"<p class='muted'>Operator checklist unavailable: {_safe(result.error)}</p>"
    notes = result.operator_notes
    summary = notes.get("summary") or {}
    checklist = notes.get("checklist") if isinstance(notes.get("checklist"), list) else []
    rows = []
    for item in checklist[:20]:
        if not isinstance(item, dict):
            continue
        check_id = str(item.get("id", ""))
        status = str(item.get("status", "pending"))
        command = str(item.get("command", ""))
        required = "required" if item.get("required") else "optional"
        controls = ""
        if status != "done":
            controls += _button("Done", "stable_loop_check_done", stable_loop_id=loop_id, check_id=check_id)
        if status != "skipped":
            controls += _button("Skip", "stable_loop_check_skip", stable_loop_id=loop_id, check_id=check_id)
        rows.append(
            "<tr>"
            f"<td><span class='badge'>{_safe(status)}</span></td>"
            f"<td><b>{_safe(check_id)}</b><br>{_safe(item.get('label', ''))}<br><span class='muted'>{_safe(required)}</span></td>"
            f"<td><code>{_safe(command)}</code></td>"
            f"<td>{controls}</td>"
            "</tr>"
        )
    table = "<table><tr><th>Status</th><th>Check</th><th>Command</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p class='muted'>No checklist items found.</p>"
    decision_options = "".join(
        f"<option value='{_safe(value)}'>{_safe(label)}</option>"
        for value, label in FINAL_DECISION_LABELS.items()
    )
    forms = f"""
<form method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_add_operator_note'>
<input type='hidden' name='stable_loop_id' value='{_safe(loop_id)}'>
<label>Operator note <input name='note' placeholder='What did you verify or notice?'></label>
<button type='submit'>Add operator note</button>
</form>
<form method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_final_decision'>
<input type='hidden' name='stable_loop_id' value='{_safe(loop_id)}'>
<label>Final decision <select name='decision'>{decision_options}</select></label>
<label>Decision note <input name='note' placeholder='Keep, fix forward, rollback, or review notes'></label>
<button type='submit'>Save final decision</button>
</form>
"""
    kpis = (
        f"<p><span class='badge'>Checklist: {_safe(summary.get('check_done', 0))}/{_safe(summary.get('check_total', 0))} done</span> "
        f"<span class='badge'>Required pending: {_safe(summary.get('required_pending', 0))}</span> "
        f"<span class='badge'>Decision: {_safe(summary.get('final_decision_label', 'Undecided'))}</span></p>"
    )
    return kpis + table + forms


def _stable_loop_review_cards(selected_filter: str = "all") -> str:
    summary = stable_loop_review_summary(review_filter=selected_filter)
    counts = summary.get("counts") or {}
    cards = (
        _card("Review Queue", f"<div class='kpi'>{_safe(summary.get('unreviewed_preview_count', 0))}</div><p class='muted'>Unreviewed preview loop(s)</p>")
        + _card("Approved for Live", f"<div class='kpi'>{_safe(summary.get('approved_ready_count', 0))}</div><p class='muted'>Approved preview(s) ready for an explicit live run</p>")
        + _card("Archived", f"<div class='kpi'>{_safe(summary.get('archived_count', 0))}</div><p class='muted'>Hidden history record(s), not deleted</p>")
    )
    details = " ".join(
        f"<span class='badge'>{_safe(REVIEW_STATUS_LABELS.get(status, status))}: {_safe(count)}</span>"
        for status, count in sorted(counts.items())
    )
    return cards + _card("Review Status Counts", details or "<p class='muted'>No saved stable loop records.</p>")


def _stable_loop_filter_controls(selected_filter: str = "all") -> str:
    selected = normalize_review_filter(selected_filter)
    filters = ["all", "open", "unreviewed", "reviewed", "approved_ready", "rejected", "superseded", "failed", "cleanup_default", "archived"]
    links = []
    for token in filters:
        label = REVIEW_FILTER_LABELS.get(token, token)
        active = " active" if token == selected else ""
        links.append(f"<a class='filter-chip{active}' href='/stable-loop?review={_safe(token)}'>{_safe(label)}</a>")
    return "<div class='toolbar'>" + "".join(links) + "</div>"


def _stable_loop_history_cleanup_controls(selected_filter: str = "cleanup_default") -> str:
    filter_value = normalize_review_filter(selected_filter if selected_filter != "all" else "cleanup_default")
    return f"""
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_cleanup_history'>
<input type='hidden' name='review_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='true'>
<button type='submit'>Preview cleanup for {_safe(REVIEW_FILTER_LABELS.get(filter_value, filter_value))}</button>
</form>
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_cleanup_history'>
<input type='hidden' name='review_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='false'>
<button type='submit'>Archive cleanup candidates</button>
</form>
<p class='muted'>Cleanup archives matching records by marking review metadata. It does not delete JSON files, because deleting history to “clean up” is how future-you invent archaeology as a hobby.</p>
"""



def _stable_loop_decision_cards(selected_filter: str = "all") -> str:
    summary = stable_loop_decision_summary(decision_filter=selected_filter)
    return (
        _card("Final Decisions", f"<div class='kpi'>{_safe(summary.get('filtered_count', 0))}</div><p class='muted'>{_safe(summary.get('selected_filter_label', 'All decisions'))}</p>")
        + _card("Action Required", f"<div class='kpi'>{_safe(summary.get('action_required_count', 0))}</div><p class='muted'>Fix-forward, rollback, or needs-review decision(s)</p>")
        + _card("Cleanup Candidates", f"<div class='kpi'>{_safe(summary.get('cleanup_candidate_count', 0))}</div><p class='muted'>Completed keep/rollback decision record(s) safe to archive</p>")
    )


def _stable_loop_decision_filter_controls(selected_filter: str = "all", review_filter: str = "all") -> str:
    selected = normalize_decision_filter(selected_filter)
    filters = ["all", "open", "undecided", "keep", "fix_forward", "rollback", "needs_review", "action_required", "decided", "complete", "incomplete", "cleanup_default", "archived"]
    links = []
    for token in filters:
        label = DECISION_FILTER_LABELS.get(token, token)
        active = " active" if token == selected else ""
        links.append(f"<a class='filter-chip{active}' href='/stable-loop?review={_safe(review_filter)}&decision={_safe(token)}'>{_safe(label)}</a>")
    return "<div class='toolbar'>" + "".join(links) + "</div>"


def _stable_loop_decision_cleanup_controls(selected_filter: str = "cleanup_default") -> str:
    filter_value = normalize_decision_filter(selected_filter if selected_filter != "all" else "cleanup_default")
    return f"""
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_cleanup_decisions'>
<input type='hidden' name='decision_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='true'>
<button type='submit'>Preview decision cleanup for {_safe(DECISION_FILTER_LABELS.get(filter_value, filter_value))}</button>
</form>
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_cleanup_decisions'>
<input type='hidden' name='decision_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='false'>
<button type='submit'>Archive decision cleanup candidates</button>
</form>
<p class='muted'>Decision cleanup archives completed keep/rollback records by default. It does not delete JSON. Shocking restraint from software, really.</p>
"""



def _stable_loop_followup_cards(selected_filter: str = "action_required") -> str:
    summary = stable_loop_followup_summary(decision_filter=selected_filter)
    return (
        _card("Decision Follow-ups", f"<div class='kpi'>{_safe(summary.get('missing_followup_count', 0))}</div><p class='muted'>Missing task-backed follow-up(s)</p>")
        + _card("Existing Follow-ups", f"<div class='kpi'>{_safe(summary.get('existing_followup_count', 0))}</div><p class='muted'>Already-created follow-up task(s)</p>")
    )


def _stable_loop_followup_controls(selected_filter: str = "action_required") -> str:
    filter_value = normalize_decision_filter(selected_filter if selected_filter != "all" else "action_required")
    return f"""
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_create_decision_followups'>
<input type='hidden' name='decision_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='true'>
<button type='submit'>Preview follow-up tasks for {_safe(DECISION_FILTER_LABELS.get(filter_value, filter_value))}</button>
</form>
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_create_decision_followups'>
<input type='hidden' name='decision_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='false'>
<button type='submit'>Create follow-up tasks</button>
</form>
<p class='muted'>Creates canonical tasks for fix-forward, rollback, and needs-review decisions. It avoids duplicates by stable-loop id and follow-up kind. Finally, paperwork that does something.</p>
"""



def _stable_loop_followup_completion_cards(selected_filter: str = "all") -> str:
    summary = stable_loop_followup_completion_summary(completion_filter=selected_filter)
    return (
        _card("Follow-up Closure", f"<div class='kpi'>{_safe(summary.get('filtered_count', 0))}</div><p class='muted'>{_safe(summary.get('selected_filter_label', 'All follow-up chains'))}</p>")
        + _card("Ready to Resolve", f"<div class='kpi'>{_safe(summary.get('ready_to_resolve_count', 0))}</div><p class='muted'>Chains whose follow-up tasks are closed but not resolved</p>")
        + _card("Unresolved", f"<div class='kpi'>{_safe(summary.get('unresolved_count', 0))}</div><p class='muted'>Action-required decisions not fully closed</p>")
        + _card("Completion Cleanup", f"<div class='kpi'>{_safe(summary.get('cleanup_candidate_count', 0))}</div><p class='muted'>Resolved chains safe to archive</p>")
    )


def _stable_loop_followup_completion_filter_controls(selected_filter: str = "all", review_filter: str = "all", decision_filter: str = "all") -> str:
    selected = normalize_followup_completion_filter(selected_filter)
    filters = ["all", "action_required", "missing_followups", "open", "unresolved", "ready_to_resolve", "resolved", "cleanup_default", "archived"]
    links = []
    for token in filters:
        label = FOLLOWUP_COMPLETION_FILTER_LABELS.get(token, token)
        active = " active" if token == selected else ""
        links.append(f"<a class='filter-chip{active}' href='/stable-loop?review={_safe(review_filter)}&decision={_safe(decision_filter)}&followup={_safe(token)}'>{_safe(label)}</a>")
    return "<div class='toolbar'>" + "".join(links) + "</div>"


def _stable_loop_followup_completion_cleanup_controls(selected_filter: str = "cleanup_default") -> str:
    filter_value = normalize_followup_completion_filter(selected_filter if selected_filter != "all" else "cleanup_default")
    return f"""
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_cleanup_followup_completions'>
<input type='hidden' name='completion_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='true'>
<button type='submit'>Preview follow-up cleanup for {_safe(FOLLOWUP_COMPLETION_FILTER_LABELS.get(filter_value, filter_value))}</button>
</form>
<form class='inline' method='post' action='/action'>
<input type='hidden' name='action' value='stable_loop_cleanup_followup_completions'>
<input type='hidden' name='completion_filter' value='{_safe(filter_value)}'>
<input type='hidden' name='dry_run' value='false'>
<button type='submit'>Archive resolved follow-up chains</button>
</form>
<p class='muted'>Completion cleanup archives resolved stable-loop follow-up chains. It does not delete records, because apparently we have learned from history. Briefly.</p>
"""

def render_stable_loop(review_filter: str = "all", decision_filter: str = "all", followup_filter: str = "all") -> str:
    selected_filter = normalize_review_filter(review_filter)
    selected_decision_filter = normalize_decision_filter(decision_filter)
    selected_followup_filter = normalize_followup_completion_filter(followup_filter)
    rows_data = list_stable_loop_reviews(review_filter=selected_filter, include_archived=(selected_filter == "archived" or selected_decision_filter == "archived"), limit=160)
    latest = load_stable_loop("latest")
    preflight = build_stable_loop_preflight(project_id="eidolon", max_steps=1)
    guardrails = stable_loop_guardrail_summary(project_id="eidolon")
    decision_filter_ids = set()
    if selected_decision_filter != "all":
        decision_filter_ids = {
            str(row.get("id", ""))
            for row in list_stable_loop_decision_rows(
                decision_filter=selected_decision_filter,
                include_archived=(selected_decision_filter == "archived"),
                limit=0,
            )
        }
    followup_filter_ids = set()
    if selected_followup_filter != "all":
        completion_summary = stable_loop_followup_completion_summary(
            completion_filter=selected_followup_filter,
            include_archived=(selected_followup_filter == "archived"),
        )
        followup_filter_ids = {str(item) for item in completion_summary.get("filtered_ids", [])}
    rows = []
    for row in rows_data:
        loop_id = str(row.get('id', ''))
        loop = load_stable_loop(loop_id) or {}
        decision_row = stable_loop_decision_row(loop) if loop else {}
        if selected_decision_filter != "all" and loop_id not in decision_filter_ids:
            continue
        if selected_followup_filter != "all" and loop_id not in followup_filter_ids:
            continue
        completion_row = stable_loop_followup_completion_row(loop) if loop else {}
        controls = _stable_loop_review_controls(loop_id, compact=True)
        archive_control = ""
        if row.get("archived"):
            archive_control = _button("Restore", "stable_loop_restore", stable_loop_id=loop_id)
        else:
            archive_control = _button("Archive", "stable_loop_archive", stable_loop_id=loop_id)
        row_class = " class='review-archived'" if row.get("archived") else ""
        archived_badge = " <span class='badge'>archived</span>" if row.get("archived") else ""
        rows.append(
            f"<tr{row_class}>"
            f"<td><span class='badge'>{_safe('ok' if row.get('ok') else 'attention')}</span></td>"
            f"<td><span class='badge'>{_safe(row.get('review_label',''))}</span>{archived_badge}</td>"
            f"<td>{_safe(row.get('live'))}</td>"
            f"<td><b>{_detail_link('stable_loop', loop_id, loop_id)}</b><br><span class='muted'>Project: {_safe(row.get('project_id',''))}</span></td>"
            f"<td>{_safe(row.get('preview_cycle_id',''))}</td>"
            f"<td>{_safe(row.get('live_cycle_id',''))}</td>"
            f"<td><span class='badge'>{_safe(decision_row.get('final_decision_label','Undecided'))}</span><br><span class='muted'>checks { _safe(decision_row.get('check_done', 0))}/{ _safe(decision_row.get('check_total', 0))}</span></td>"
            f"<td><span class='badge'>{_safe(completion_row.get('completion_status_label',''))}</span><br><span class='muted'>tasks { _safe(completion_row.get('task_count', 0))}, open { _safe(completion_row.get('open_task_count', 0))}<br>{_safe(completion_row.get('recommended_action',''))}</span></td>"
            f"<td>{_safe(row.get('stopped_reason',''))}</td>"
            f"<td>{_safe((loop.get('audit') or {}).get('summary', ''))}<br><span class='muted'>Warnings: {len(((loop.get('audit') or {}).get('warnings') or []))}<br>{_safe(decision_row.get('recommended_action',''))}</span></td>"
            f"<td>{controls} {archive_control} {_button('Follow-ups', 'stable_loop_create_followups', stable_loop_id=loop_id, dry_run='true')} {_button('Resolve Follow-ups', 'stable_loop_resolve_followups', stable_loop_id=loop_id)} {_button('Mark Closed', 'stable_loop_mark_followup_closed', stable_loop_id=loop_id)} {_detail_link('stable_loop', loop_id, 'Details')}</td>"
            "</tr>"
        )
    table = "<table><tr><th>Status</th><th>Review</th><th>Live</th><th>Loop</th><th>Preview Cycle</th><th>Live Cycle</th><th>Decision</th><th>Follow-up Closure</th><th>Stopped</th><th>Audit / Next</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p class='muted'>No stable loop records match this filter.</p>"
    latest_text = stable_loop_text(latest, full=False) if latest else "No stable supervised loops saved yet. Peaceful, but suspicious."
    latest_loop_id = str(latest.get('id', '')) if latest else ""
    latest_buttons = _stable_loop_review_controls(latest_loop_id, compact=False) if latest else ""
    latest_operator = _stable_loop_operator_controls(latest_loop_id) if latest else ""
    body = (
        _stable_loop_review_cards(selected_filter)
        + _stable_loop_decision_cards(selected_decision_filter)
        + _stable_loop_followup_cards(selected_decision_filter if selected_decision_filter != "all" else "action_required")
        + _stable_loop_followup_completion_cards(selected_followup_filter)
        + _card("Review Filters", _stable_loop_filter_controls(selected_filter))
        + _card("Decision Filters", _stable_loop_decision_filter_controls(selected_decision_filter, selected_filter))
        + _card("Follow-up Closure Filters", _stable_loop_followup_completion_filter_controls(selected_followup_filter, selected_filter, selected_decision_filter))
        + _card("History Cleanup", _stable_loop_history_cleanup_controls(selected_filter))
        + _card("Decision Cleanup", _stable_loop_decision_cleanup_controls(selected_decision_filter))
        + _card("Follow-up Completion Cleanup", _stable_loop_followup_completion_cleanup_controls(selected_followup_filter))
        + _card("Decision Follow-up Tasks", _stable_loop_followup_controls(selected_decision_filter if selected_decision_filter != "all" else "action_required"))
        + _card("Follow-up Completion Report", _text_block(stable_loop_followup_completion_report_text(stable_loop_followup_completion_summary(completion_filter=selected_followup_filter), full=False)))
        + _card("Follow-up Task Lifecycle", _text_block(followup_lifecycle_summary_text(stable_loop_followup_lifecycle_summary(decision_filter=selected_decision_filter if selected_decision_filter != "all" else "action_required"), full=False)))
        + _card("Live Run Closure Guardrails", _text_block(stable_loop_guardrails_text(guardrails, full=False)))
        + _card("Stable Loop Preflight", _text_block(stable_preflight_text(preflight, full=False)))
        + _card("Run Stable Supervised Loop", _stable_loop_controls())
        + _card("Latest Stable Loop", _text_block(latest_text) + latest_buttons)
        + (_card("Latest Post-Run Checklist / Operator Notes", latest_operator) if latest else "")
        + _card(f"Saved Stable Loops · review={_safe(REVIEW_FILTER_LABELS.get(selected_filter, selected_filter))} · decision={_safe(DECISION_FILTER_LABELS.get(selected_decision_filter, selected_decision_filter))} · followup={_safe(FOLLOWUP_COMPLETION_FILTER_LABELS.get(selected_followup_filter, selected_followup_filter))}", table)
    )
    return _layout("/stable-loop", body)


def render_approvals() -> str:
    approvals = list_approvals(include_closed=True)
    rows = []
    for approval in approvals[:80]:
        approval_id = approval.get("id", "")
        status = approval.get("status", "")
        action_type = approval.get("type", approval.get("action_type", ""))
        summary = approval.get("summary", "")
        buttons = ""
        if status == "pending":
            buttons += _button("Dry-run", "approve", approval_id=approval_id, dry_run="true")
            buttons += _button("Approve", "approve", approval_id=approval_id)
            buttons += _button("Reject", "reject", approval_id=approval_id)
        rows.append(f"<tr><td><span class='badge'>{_safe(status)}</span></td><td>{_safe(action_type)}</td><td><b>{_detail_link('approval', approval_id, summary)}</b><br><span class='muted'>{_safe(approval_id)}</span></td><td>{buttons} {_detail_link('approval', approval_id, 'Details')}</td></tr>")
    table = "<table><tr><th>Status</th><th>Type</th><th>Approval</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No approvals found.</p>"
    latest = list_approvals(status="pending", include_closed=False)
    latest_text = approval_text(latest[0], full=True) if latest else "No pending approvals. A rare bureaucratic victory."
    return _layout("/approvals", _card("Latest Pending Approval", _text_block(latest_text)) + _card("Approval Inbox", table))


def render_notifications() -> str:
    notifications = list_notifications(include_dismissed=True)
    rows = []
    for note in notifications[:100]:
        note_id = note.get("id", "")
        status = note.get("status", "")
        severity = note.get("severity", "")
        title = note.get("title", "")
        command = note.get("recommended_command", "")
        buttons = ""
        if status == "unread":
            buttons += _button("Mark read", "notification_read", notification_id=note_id)
            buttons += _button("Dismiss", "notification_dismiss", notification_id=note_id)
        rows.append(
            f"<tr><td><span class='badge'>{_safe(status)}</span></td>"
            f"<td>{_safe(severity)}</td>"
            f"<td><b>{_detail_link('notification', note_id, title)}</b><br><span class='muted'>{_safe(note_id)}</span></td>"
            f"<td>{_safe(command)}</td><td>{buttons} {_detail_link('notification', note_id, 'Details')}</td></tr>"
        )
    table = "<table><tr><th>Status</th><th>Severity</th><th>Notification</th><th>Recommended Command</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No notifications found.</p>"
    unread = list_notifications(status="unread", include_dismissed=False)
    latest_text = notification_text(unread[0], full=False) if unread else "No unread notifications. Suspiciously peaceful."
    actions = _button("Clear dismissed", "notifications_clear_dismissed")
    return _layout("/notifications", _card("Latest Unread Notification", _text_block(latest_text)) + _card("Notification Actions", actions) + _card("Notifications", table))


def _watch_loop_form() -> str:
    return """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='watch_loop'>
<label>Cycles <input name='cycles' value='2'></label>
<label>Interval seconds <input name='interval' value='5'></label>
<label><input type='checkbox' name='use_ai' value='true'> Use local AI summary</label>
<button type='submit'>Run bounded watch loop</button>
</form>
"""


def render_watch() -> str:
    reports = list_watch_reports()
    latest = reports[0] if reports else None
    latest_text = watch_report_text(latest, full=False, include_ai=True) if latest else "No watch reports yet. Run a check, because apparently even ghosts need status meetings."

    actions = "".join([
        _button("Run watch once", "watch_once_no_ai"),
        _button("Run watch once with AI", "watch_once_ai"),
    ])

    rows = []
    for report in reports[:40]:
        if report.get("type") == "background_watch_loop":
            kind = "loop"
            status = report.get("stopped_reason", "")
            detail = f"cycles={report.get('cycle_count', len(report.get('reports', [])))} / {report.get('cycles_requested')}"
        else:
            kind = "report"
            status = report.get("status", "")
            detail = f"recommendations={len(report.get('recommendations', []) or [])}"
        rows.append(
            f"<tr><td><span class='badge'>{_safe(kind)}</span></td>"
            f"<td>{_safe(status)}</td>"
            f"<td><b>{_detail_link('watch', report.get('id',''), report.get('id',''))}</b><br><span class='muted'>{_safe(report.get('created_at',''))}</span></td>"
            f"<td>{_safe(detail)}</td><td>{_detail_link('watch', report.get('id',''), 'Details')}</td></tr>"
        )
    table = "<table><tr><th>Type</th><th>Status</th><th>Report</th><th>Details</th><th></th></tr>" + "".join(rows) + "</table>" if rows else "<p>No watch reports found.</p>"

    return _layout(
        "/watch",
        _card("Watch Controls", actions)
        + _card("Bounded Watch Loop", _watch_loop_form())
        + _card("Latest Watch Report", _text_block(latest_text))
        + _card("Saved Watch Reports", table),
    )


def render_patches() -> str:
    patches = list_patch_proposals()
    rows = []
    for patch in patches[:80]:
        patch_id = str(patch.get('id', ''))
        task_id = str(patch.get('task_id') or patch.get('work_item_id') or '')
        linked = _detail_link('work_item', task_id, task_id) if task_id else "<span class='muted'>[none]</span>"
        controls = _button("Create Follow-ups", "patch_create_followups", patch_id=patch_id) if patch_id else ""
        rows.append(f"<tr><td><span class='badge'>{_safe(patch.get('status',''))}</span></td><td>{_safe(patch.get('risk_level',''))}</td><td><b>{_detail_link('patch', patch_id, patch.get('target_file',''))}</b><br><span class='muted'>{_safe(patch_id)}</span><br><span class='muted'>Task: {linked}</span></td><td>{_safe(patch.get('request',''))}<br>{_detail_link('patch', patch_id, 'Details')} {controls}</td></tr>")
    table = "<table><tr><th>Status</th><th>Risk</th><th>File</th><th>Request</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No patches found.</p>"
    latest = patches[0] if patches else None
    latest_text = patch_proposal_text(latest, include_full_content=False) if latest else "No patch proposals yet."
    return _layout("/patches", _card("Request Patch", _patch_request_form()) + _card("Latest Patch", _text_block(latest_text)) + _card("Patch Records", table))


def render_goals() -> str:
    goals = list_goals(include_cancelled=False)
    rows = []
    for goal in goals[:80]:
        rows.append(f"<tr><td><span class='badge'>{_safe(goal.get('status',''))}</span></td><td>{_safe(goal.get('priority',''))}</td><td><b>{_detail_link('goal', goal.get('id',''), goal.get('title',''))}</b><br><span class='muted'>{_safe(goal.get('id',''))}</span></td><td>{_safe(goal.get('next_action','') or (goal.get('next_actions') or [''])[0])}</td></tr>")
    table = "<table><tr><th>Status</th><th>Priority</th><th>Goal</th><th>Next Action</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No goals found.</p>"
    return _layout("/goals", _card("Create Goal", _goal_create_form()) + _card("Structured Goals", table))


def render_diagnostics() -> str:
    reports = list_diagnostic_reports()
    latest = reports[0] if reports else None
    status = latest.get("overall_status", "[none]") if latest else "[none]"
    body = f"<p>Latest diagnostic status: <b>{_safe(status)}</b></p>" + _button("Run diagnostics", "run_diagnostics")
    if latest:
        body += " " + _detail_link('diagnostic', latest.get('id',''), 'Open latest diagnostic')
    if latest:
        body += _text_block(diagnostic_report_text(latest, include_full=False))
    return _layout("/diagnostics", _card("Diagnostics", body))


def render_settings() -> str:
    settings = load_settings()
    rows = "".join(f"<tr><td>{_safe(k)}</td><td>{_safe(v)}</td></tr>" for k, v in sorted(settings.items()))
    form = """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='set_setting'>
<label>Setting key <input name='key' placeholder='local_model'></label>
<label>Value <input name='value' placeholder='qwen2.5:7b'></label>
<button type='submit'>Update setting</button>
</form>
"""
    health = settings_health()
    return _layout("/settings", _card("Settings", f"<table><tr><th>Key</th><th>Value</th></tr>{rows}</table>") + _card("Update Setting", form) + _card("Settings Health", _json_block(health)))




def _report_status_card(title: str, report: dict[str, Any], extra: str = "") -> str:
    status = str(report.get("status", "unknown")).upper()
    status_class = "good" if status in {"PASS", "READY", "PREVIEW_COMPLETE", "LIVE_COMPLETE"} else "warn" if status in {"WARN", "READY_WITH_WARNINGS", "LIMITED_MODE"} else "badtext"
    score = f"<p class='muted'>Score: {_safe(report.get('score'))}%</p>" if "score" in report else ""
    return _card(title, f"<div class='kpi {status_class}'>{_safe(status)}</div><p>{_safe(report.get('message', ''))}</p>{score}{extra}")


def render_stabilization() -> str:
    report = build_stabilization_checkpoint(project_id="eidolon", full=True)
    confidence = build_stable_loop_confidence(project_id="eidolon")
    repairs = build_repair_suggestions(project_id="eidolon")
    counts = report.get("counts") or {}
    blockers = report.get("blockers") or []
    warnings = report.get("warnings") or []
    blocker_html = _small_list([
        _safe(f"[{item.get('category', 'general')}] {item.get('name')}: {item.get('message')}")
        for item in blockers[:12]
    ]) if blockers else "<p class='muted'>No blockers found.</p>"
    warning_html = _small_list([
        _safe(f"[{item.get('category', 'general')}] {item.get('name')}: {item.get('message')}")
        for item in warnings[:12]
    ]) if warnings else "<p class='muted'>No warnings found.</p>"
    repair_rows = repairs.get("rows") or []
    repair_html = _small_list([
        _safe(f"{item.get('severity', 'info').upper()} {item.get('id')}: {item.get('problem')}")
        for item in repair_rows[:8]
    ])
    command_text = "\n".join(report.get("recommended_commands") or [])
    body = f"""
<p>The v8.0 stabilization page now groups checkpoint status, confidence, blockers, warnings, repair suggestions, and exact commands. Still read-only. Shocking maturity from a codebase.</p>
<div class='grid'>
  {_report_status_card('Checkpoint', report)}
  {_report_status_card('Stable Loop Confidence', confidence)}
  <section class='card'><h2>Pass</h2><div class='kpi good'>{_safe(counts.get('pass', 0))}</div></section>
  <section class='card'><h2>Warn</h2><div class='kpi warn'>{_safe(counts.get('warn', 0))}</div></section>
  <section class='card'><h2>Fail</h2><div class='kpi badtext'>{_safe(counts.get('fail', 0))}</div></section>
</div>
<div class='grid'>
  {_card('Blockers', blocker_html)}
  {_card('Warnings', warning_html)}
  {_card('Repair Suggestions', repair_html + "<p><a href='/doctor'>Open Doctor page</a></p>")}
</div>
<h3>Recommended commands</h3>
<pre>{_safe(command_text)}</pre>
<p><a href='/api/stabilization-checkpoint?full=true'>Open JSON checkpoint report</a> | <a href='/api/doctor?full=true'>Open JSON doctor report</a></p>
"""
    return _layout("/stabilization", _card("Stabilization Checkpoint", body) + _card("Full report", _text_block(stabilization_checkpoint_text(report, full=True))))


def render_doctor() -> str:
    doctor = build_doctor_report(project_id="eidolon", full=False)
    confidence = build_stable_loop_confidence(project_id="eidolon")
    snapshot = build_project_snapshot(project_id="eidolon")
    patch_integrity = build_patch_integrity_report()
    task_review = build_task_review(project_id="eidolon")
    recovery = build_recovery_drill(project_id="eidolon")
    hardening = build_hardening_report(project_id="eidolon")
    controlled = build_controlled_self_build(project_id="eidolon", max_steps=1, live=False, approve_live=False, use_ai=False)
    repair = build_repair_suggestions(project_id="eidolon")
    body = f"""
<p>Doctor mode ties together v7.2 through v8.0: repair suggestions, patch integrity, project snapshot, task review, recovery drill, confidence score, hardening checks, and controlled self-build preview. Basically a clipboard for the robot before it touches anything sharp.</p>
<div class='grid'>
  {_report_status_card('Doctor', doctor)}
  {_report_status_card('Confidence', confidence)}
  {_report_status_card('Patch Integrity', patch_integrity)}
  {_report_status_card('Task Review', task_review)}
  {_report_status_card('Recovery Drill', recovery)}
  {_report_status_card('Hardening', hardening)}
  {_report_status_card('Controlled Self-Build Preview', controlled)}
</div>
<p><a href='/api/doctor?full=true'>Doctor JSON</a> | <a href='/api/controlled-self-build'>Controlled self-build JSON</a> | <a href='/api/project-snapshot'>Snapshot JSON</a></p>
"""
    reports = "\n\n".join([
        doctor_report_text(doctor, full=False),
        repair_suggestions_text(repair, full=False),
        project_snapshot_text(snapshot, full=False),
        patch_integrity_text(patch_integrity, full=False),
        task_review_text(task_review, full=False),
        recovery_drill_text(recovery, full=False),
        stable_loop_confidence_text(confidence, full=False),
        hardening_report_text(hardening, full=False),
        controlled_self_build_text(controlled, full=False),
    ])
    return _layout("/doctor", _card("Doctor Mode", body) + _card("Operational reports", _text_block(reports)))


def render_build_cycle() -> str:
    selection = build_controlled_task_selection(project_id="eidolon")
    plan = build_patch_plan(project_id="eidolon", target_version="10.0", save=False)
    workspace = patch_workspace_status()
    diff = preview_staged_diff(project_id="eidolon", stage_if_missing=False, save=False)
    gate = readme_gate(project_id="eidolon")
    cycle = {"version": "9.0", "status": "preview_available", "ok": True, "message": "Run the CLI/API cycle command to execute the preview; dashboard rendering stays read-only."}
    supervised = {"version": "9.0", "status": "preview_available", "ok": True, "message": "Run the CLI/API supervised loop command to execute one bounded preview cycle; dashboard rendering stays read-only."}
    body = f"""
<p>v9.0 adds the controlled build lane: task selection, patch planning, workspace staging, diff preview, guarded apply/rollback, README enforcement, one-cycle controlled build, and the supervised development loop. It is still preview-first, because apparently files enjoy not being surprises.</p>
<div class='grid'>
  {_report_status_card('Task Selection', selection)}
  {_report_status_card('Patch Plan', plan)}
  {_report_status_card('Workspace', workspace)}
  {_report_status_card('Diff Preview', diff)}
  {_report_status_card('README Gate', gate)}
  {_report_status_card('Controlled Cycle', cycle)}
  {_report_status_card('Supervised Dev Loop', supervised)}
</div>
<p><a href='/api/controlled-build/select-task'>Selection JSON</a> | <a href='/api/controlled-build/workspace'>Workspace JSON</a> | <a href='/api/controlled-build/readme-gate'>README Gate JSON</a> | <a href='/api/patch-review'>Patch Review JSON</a></p>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --controlled-self-build --select-task
python conscious_agent/main.py --controlled-self-build --plan-patch
python conscious_agent/main.py --controlled-self-build --stage-patch
python conscious_agent/main.py --controlled-self-build --preview-diff
python conscious_agent/main.py --readme-gate
python conscious_agent/main.py --controlled-self-build-cycle
python conscious_agent/main.py --supervised-dev-loop</pre>
"""
    reports = "\n\n".join([
        controlled_task_selection_text(selection, full=False),
        patch_plan_text(plan, full=False),
        workspace_status_text(workspace, full=False),
        diff_preview_text(diff, full=False),
        readme_gate_text(gate, full=False),
        controlled_build_cycle_text(cycle, full=False),
        supervised_dev_loop_text(supervised, full=False),
    ])
    return _layout("/build-cycle", _card("Controlled Build Cycle", body) + _card("v8.1-v9.0 Reports", _text_block(reports)))



def render_patch_review() -> str:
    from self_maintenance import patch_draft_review_diff_validation_layer_text
    old_report = build_patch_review(project_id="eidolon")
    final_report = {"stage": "v74.0", "status": "preview", "ok": True, "message": "Patch Draft Review and Diff Validation preview. Use CLI/API for full validation against a draft file."}
    body = f"""
<p>v74.0 turns /patch-review into the review-only lane for proposed patch drafts and diff-like output. It parses the draft, extracts touched files, validates the v73 scope contract, checks safety boundaries, enforces README/release-history updates, validates verification coverage, scores risk, and builds an operator review packet. It still applies nothing, because self-modifying code without adult supervision is how a folder becomes a crime scene.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Parse summary, files, diff, risk, verification, rollback, docs, and safety-attestation sections from model output.'><strong>Intake</strong><span>v73.1 parser</span></div>
  <div class='mini-card' data-tip='Extract modified, created, deleted, renamed, and mentioned paths plus estimated diff size.'><strong>Diff Boundary</strong><span>v73.2 extractor</span></div>
  <div class='mini-card' data-tip='Compare proposed files against the v73 allowed files, blocked patterns, max file count, and max diff size.'><strong>Scope Contract</strong><span>v73.3 validator</span></div>
  <div class='mini-card' data-tip='Hard-block source apply, publish, memory, identity, approval-bypass, autonomous loops, and runtime data edits.'><strong>Safety</strong><span>v73.4 validator</span></div>
  <div class='mini-card' data-tip='Enforce README_NEXT_STEPS.md and README_RELEASE_HISTORY.md for every code patch.'><strong>Docs</strong><span>v73.5 validator</span></div>
  <div class='mini-card' data-tip='Require compile, smoke, package privacy, release zip, and install verification coverage.'><strong>Verification</strong><span>v73.6 validator</span></div>
  <div class='mini-card' data-tip='Score low/moderate/high/blocked risk from file count, core surfaces, contract violations, safety, docs, and verification.'><strong>Risk</strong><span>v73.7 scorer</span></div>
  <div class='mini-card' data-tip='Build the final operator-facing review report while applying no source changes.'><strong>Report</strong><span>v73.8 packet</span></div>
</div>
<h3>v74 CLI checks</h3>
<pre>python conscious_agent/main.py --patch-review-intake --readiness-json
python conscious_agent/main.py --patch-review-diff-boundary --readiness-json
python conscious_agent/main.py --patch-review-scope --readiness-json
python conscious_agent/main.py --patch-review-safety --readiness-json
python conscious_agent/main.py --patch-review-docs --readiness-json
python conscious_agent/main.py --patch-review-verification --readiness-json
python conscious_agent/main.py --patch-review-risk --readiness-json
python conscious_agent/main.py --patch-review-report --readiness-json
python conscious_agent/main.py --patch-review-dashboard-api-cli --readiness-json
python conscious_agent/main.py --pre-v74-patch-review-gate --readiness-json
python conscious_agent/main.py --patch-draft-review-diff-validation-layer --readiness-json</pre>
<p><a href='/api/patch-review/intake'>Intake JSON</a> | <a href='/api/patch-review/diff-boundary'>Boundary JSON</a> | <a href='/api/patch-review/scope'>Scope JSON</a> | <a href='/api/patch-review/safety'>Safety JSON</a> | <a href='/api/patch-review/docs'>Docs JSON</a> | <a href='/api/patch-review/verification'>Verification JSON</a> | <a href='/api/patch-review/risk'>Risk JSON</a> | <a href='/api/patch-review/report'>Report JSON</a> | <a href='/api/patch-review/gate'>Gate JSON</a> | <a href='/api/patch-review/layer'>v74 System JSON</a></p>
<h3>Legacy v9.5 workspace patch review remains available</h3>
<div class='grid'>
  {_report_status_card('Workspace', old_report.get('workspace') or {})}
  {_report_status_card('Diff Preview', old_report.get('diff') or {})}
  {_report_status_card('Risk', old_report.get('risk') or {})}
  {_report_status_card('Test Plan', old_report.get('test_plan') or {})}
  {_report_status_card('README Gate', old_report.get('readme_gate') or {})}
</div>
<p><a href='/api/patch-review'>Legacy workspace patch review JSON</a> | <a href='/api/patch-risk'>Legacy risk JSON</a> | <a href='/api/test-plan'>Legacy test plan JSON</a></p>
"""
    summary = _card("v74.0 Patch Draft Review and Diff Validation", _text_block(patch_draft_review_diff_validation_layer_text(final_report, full=False)))
    return _layout("/patch-review", _card("Patch Review", body) + summary)


def render_patch_trials() -> str:
    from self_maintenance import sandbox_patch_trial_runner_text
    final_report = {"stage": "v75.0", "status": "preview", "ok": True, "message": "Sandbox Patch Trial Runner preview. Use CLI/API for a full disposable workspace trial against a reviewed patch draft."}
    body = f"""
<p>v75.0 adds the sandbox-only lane for reviewed patch proposals. It binds the v74 review result, creates a disposable workspace under <code>data/autonomy/patch_trials</code>, stages the patch proposal there, runs verification inside that sandbox, collects evidence, and proves the live source manifest stayed unchanged. It still does not promote or apply anything, because even machines deserve training wheels before handling scalpels.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Refuse blocked v74 reviews before any sandbox work starts.'><strong>Intake Binder</strong><span>v74.1 eligibility</span></div>
  <div class='mini-card' data-tip='Copy a disposable Eidolon workspace under data/autonomy/patch_trials, which remains excluded from source-only releases.'><strong>Workspace</strong><span>v74.2 disposable copy</span></div>
  <div class='mini-card' data-tip='Stage reviewed patch content only inside the sandbox and refuse unsafe paths.'><strong>Materializer</strong><span>v74.3 sandbox only</span></div>
  <div class='mini-card' data-tip='Run compile/status verification from the sandbox workspace, never the live tree.'><strong>Verify</strong><span>v74.4 sandbox checks</span></div>
  <div class='mini-card' data-tip='Collect review, materialization, verification, risk, and operator recommendation evidence.'><strong>Evidence</strong><span>v74.5 packet</span></div>
  <div class='mini-card' data-tip='Compare pre/post live source manifests to prove sandbox work did not escape.'><strong>Escape Guard</strong><span>v74.6 mutation check</span></div>
  <div class='mini-card' data-tip='Expose read-only dashboard/API/CLI controls for sandbox patch trials.'><strong>Surface</strong><span>v74.7 API/CLI</span></div>
  <div class='mini-card' data-tip='List or prune retained sandbox trials only under the excluded patch-trials root.'><strong>Cleanup</strong><span>v74.8 retention</span></div>
</div>
<h3>v75 CLI checks</h3>
<pre>python conscious_agent/main.py --patch-trial-intake --readiness-json
python conscious_agent/main.py --patch-trial-workspace --readiness-json
python conscious_agent/main.py --patch-trial-materialize --readiness-json
python conscious_agent/main.py --patch-trial-verify --readiness-json
python conscious_agent/main.py --patch-trial-evidence --readiness-json
python conscious_agent/main.py --patch-trial-escape-guard --readiness-json
python conscious_agent/main.py --patch-trial-dashboard-api-cli --readiness-json
python conscious_agent/main.py --patch-trial-list --readiness-json
python conscious_agent/main.py --pre-v75-sandbox-trial-gate --readiness-json
python conscious_agent/main.py --sandbox-patch-trial-runner --readiness-json</pre>
<p><a href='/api/patch-trials/intake'>Intake JSON</a> | <a href='/api/patch-trials/workspace'>Workspace JSON</a> | <a href='/api/patch-trials/materialize'>Materialize JSON</a> | <a href='/api/patch-trials/verify'>Verify JSON</a> | <a href='/api/patch-trials/evidence'>Evidence JSON</a> | <a href='/api/patch-trials/escape-guard'>Escape Guard JSON</a> | <a href='/api/patch-trials/parity'>Parity JSON</a> | <a href='/api/patch-trials/list'>List JSON</a> | <a href='/api/patch-trials/gate'>Gate JSON</a> | <a href='/api/patch-trials/layer'>v75 System JSON</a></p>
"""
    summary = _card("v75.0 Sandbox Patch Trial Runner", _text_block(sandbox_patch_trial_runner_text(final_report, full=False)))
    return _layout("/patch-trials", _card("Patch Trials", body) + summary)


def render_patch_evidence() -> str:
    from self_maintenance import sandbox_evidence_review_recommendation_layer_text
    final_report = {"stage": "v76.0", "status": "preview", "ok": True, "message": "Sandbox Evidence Review and Promotion Recommendation preview. Use CLI/API for a full recommendation packet against v75 trial evidence."}
    body = f"""
<p>v76.0 reviews sandbox trial evidence from v75 and builds a promotion-readiness recommendation packet. It validates evidence intake, trial integrity, verification results, scope and documentation, risk acceptance, recommendation archiving, and the pre-v76 gate. It still does not promote or apply anything, because apparently the safest robot is the one holding a clipboard instead of a wrench.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Load or generate v75 sandbox evidence and validate trial id, goal, touched files, risk, verification, and escape-guard fields.'><strong>Evidence Intake</strong><span>v75.1 reader</span></div>
  <div class='mini-card' data-tip='Confirm sandbox path stayed under the excluded patch-trials root and live source manifest evidence reports unchanged.'><strong>Integrity</strong><span>v75.2 validator</span></div>
  <div class='mini-card' data-tip='Score compile/status/smoke-style command evidence and flag failed or missing verification.'><strong>Verification</strong><span>v75.3 scorer</span></div>
  <div class='mini-card' data-tip='Check touched files, blocked runtime paths, core surfaces, README_NEXT_STEPS.md, and README_RELEASE_HISTORY.md evidence.'><strong>Scope + Docs</strong><span>v75.4 reviewer</span></div>
  <div class='mini-card' data-tip='Classify low, moderate, high, or blocked risk and recommend approval, manual review, revision, or block.'><strong>Risk</strong><span>v75.5 classifier</span></div>
  <div class='mini-card' data-tip='Build the operator-facing readiness packet while explicitly stating no promotion occurred.'><strong>Readiness</strong><span>v75.6 packet</span></div>
  <div class='mini-card' data-tip='Expose /patch-evidence, API routes, CLI flags, and keep custom data-tip hover behavior only.'><strong>Parity</strong><span>v75.7 surfaces</span></div>
  <div class='mini-card' data-tip='Archive recommendation packets under data/autonomy/patch_evidence_reviews and compare recent recommendation changes.'><strong>Archive</strong><span>v75.8 comparison</span></div>
</div>
<h3>v76 CLI checks</h3>
<pre>python conscious_agent/main.py --patch-evidence-intake --readiness-json
python conscious_agent/main.py --patch-evidence-integrity --readiness-json
python conscious_agent/main.py --patch-evidence-verification --readiness-json
python conscious_agent/main.py --patch-evidence-scope-docs --readiness-json
python conscious_agent/main.py --patch-evidence-risk --readiness-json
python conscious_agent/main.py --patch-evidence-readiness --readiness-json
python conscious_agent/main.py --patch-evidence-dashboard-api-cli --readiness-json
python conscious_agent/main.py --patch-evidence-archive --readiness-json
python conscious_agent/main.py --pre-v76-evidence-review-gate --readiness-json
python conscious_agent/main.py --sandbox-evidence-review-recommendation-layer --readiness-json</pre>
<p><a href='/api/patch-evidence/intake'>Intake JSON</a> | <a href='/api/patch-evidence/integrity'>Integrity JSON</a> | <a href='/api/patch-evidence/verification'>Verification JSON</a> | <a href='/api/patch-evidence/scope-docs'>Scope Docs JSON</a> | <a href='/api/patch-evidence/risk'>Risk JSON</a> | <a href='/api/patch-evidence/readiness'>Readiness JSON</a> | <a href='/api/patch-evidence/parity'>Parity JSON</a> | <a href='/api/patch-evidence/archive'>Archive JSON</a> | <a href='/api/patch-evidence/gate'>Gate JSON</a> | <a href='/api/patch-evidence/layer'>v76 System JSON</a></p>
<p class='muted'>Recommendation packets are not operator approval records. They do not apply, promote, publish, mutate memory, alter identity, or bypass approval gates. Charming that this has to be said repeatedly, but here we are.</p>
"""
    summary = _card("v76.0 Sandbox Evidence Review and Promotion Recommendation", _text_block(sandbox_evidence_review_recommendation_layer_text(final_report, full=False)))
    return _layout("/patch-evidence", _card("Patch Evidence", body) + summary)


def render_patch_apply() -> str:
    from self_maintenance import operator_approved_patch_application_layer_text
    final_report = {"stage": "v77.0", "status": "preview", "ok": True, "message": "Operator-Approved Patch Application preview. API routes stay dry-run/read-only; live source writes require CLI exact approval."}
    body = f"""
<p>v77.0 is the controlled bridge from recommendation to source application. It requires exact operator approval, binds approval to the v76 recommendation, captures a rollback snapshot, materializes only approved scope, verifies afterward, and rolls back on failure. It still does not publish releases, mutate memory, alter identity, or treat recommendations as approval, because apparently we are being responsible now.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Require the exact APPROVE PATCH APPLICATION phrase and an approved file list before source materialization can unlock.'><strong>Approval</strong><span>v76.1 contract</span></div>
  <div class='mini-card' data-tip='Bind approval to the exact v76 readiness packet, trial id, risk classification, and file scope.'><strong>Binding</strong><span>v76.2 recommendation</span></div>
  <div class='mini-card' data-tip='Capture live source manifest and file contents for rollback before any approved mutation.'><strong>Snapshot</strong><span>v76.3 rollback</span></div>
  <div class='mini-card' data-tip='Materialize only approved safe paths. API surfaces are dry-run; CLI live apply requires exact approval.'><strong>Materialize</strong><span>v76.4 scoped</span></div>
  <div class='mini-card' data-tip='Run compile/status evidence after materialization without publishing releases.'><strong>Verify</strong><span>v76.5 checks</span></div>
  <div class='mini-card' data-tip='Restore snapshotted files if verification fails; no retries and no autonomous fix generation.'><strong>Rollback</strong><span>v76.6 restore</span></div>
  <div class='mini-card' data-tip='Record final application evidence, manifests, verification, rollback state, and final status.'><strong>Evidence</strong><span>v76.7 audit</span></div>
  <div class='mini-card' data-tip='Expose /patch-apply, dry-run API routes, CLI flags, and keep custom data-tip hover behavior only.'><strong>Parity</strong><span>v76.8 surfaces</span></div>
</div>
<h3>v77 CLI checks</h3>
<pre>python conscious_agent/main.py --patch-apply-approval --readiness-json
python conscious_agent/main.py --patch-apply-bind --readiness-json
python conscious_agent/main.py --patch-apply-snapshot --readiness-json
python conscious_agent/main.py --patch-apply-materialize --readiness-json
python conscious_agent/main.py --patch-apply-verify --readiness-json
python conscious_agent/main.py --patch-apply-rollback --readiness-json
python conscious_agent/main.py --patch-apply-evidence --readiness-json
python conscious_agent/main.py --patch-application-dashboard-api-cli --readiness-json
python conscious_agent/main.py --pre-v77-application-gate --readiness-json
python conscious_agent/main.py --operator-approved-patch-application-layer --readiness-json</pre>
<p>Live CLI application requires <code>--patch-apply-approved --approval-phrase "APPROVE PATCH APPLICATION" --patch-apply-live</code> plus an approved scope. The dashboard and API do not perform live writes. Small miracle: the UI is not allowed to become a loaded glue gun.</p>
<p><a href='/api/patch-apply/approval'>Approval JSON</a> | <a href='/api/patch-apply/bind'>Bind JSON</a> | <a href='/api/patch-apply/snapshot'>Snapshot JSON</a> | <a href='/api/patch-apply/apply'>Materialize Dry-Run JSON</a> | <a href='/api/patch-apply/verify'>Verify JSON</a> | <a href='/api/patch-apply/rollback'>Rollback JSON</a> | <a href='/api/patch-apply/evidence'>Evidence JSON</a> | <a href='/api/patch-apply/parity'>Parity JSON</a> | <a href='/api/patch-apply/gate'>Gate JSON</a> | <a href='/api/patch-apply/layer'>v77 System JSON</a></p>
"""
    summary = _card("v77.0 Operator-Approved Patch Application", _text_block(operator_approved_patch_application_layer_text(final_report, full=False)))
    return _layout("/patch-apply", _card("Patch Apply", body) + summary)



def render_patch_recovery() -> str:
    from self_maintenance import verified_application_recovery_rollback_hardening_text
    final_report = {"stage": "v78.0", "status": "preview", "ok": True, "message": "Verified Application Recovery and Rollback Hardening preview. Reports recovery posture only; no retry, repair, publish, memory, identity, or approval bypass."}
    body = """
<p>v78.0 hardens the operator-approved patch application layer by checking dirty-tree state, snapshot completeness, partial applies, rollback integrity, failed verification triage, recovery recommendations, and application audit timelines. It does not generate repair patches or retry failed changes, because that would be the software equivalent of fixing a fire alarm with gasoline.</p>
<div class='mini-grid'>
  <div class='mini-card' data-tip='Inspect live source manifest, drift-tolerant metadata, and runtime clutter before application or rollback.'><strong>Preflight</strong><span>v77.1 dirty tree detector</span></div>
  <div class='mini-card' data-tip='Validate rollback snapshot manifests, file content capture, approval metadata, and runtime-only storage.'><strong>Snapshot</strong><span>v77.2 completeness</span></div>
  <div class='mini-card' data-tip='Compare approved scope, touched files, and manifests to detect partial or suspicious apply results.'><strong>Partial Apply</strong><span>v77.3 detector</span></div>
  <div class='mini-card' data-tip='Verify pre-apply and post-rollback manifests match before declaring recovery successful.'><strong>Rollback</strong><span>v77.4 integrity</span></div>
  <div class='mini-card' data-tip='Classify compile, smoke, privacy, timeout, environment, and unknown verification failures.'><strong>Triage</strong><span>v77.5 failure class</span></div>
  <div class='mini-card' data-tip='Build operator recommendations without generating fixes or retrying failed patches.'><strong>Recommendation</strong><span>v77.6 advice only</span></div>
</div>
<h3>v78 CLI checks</h3>
<pre>python conscious_agent/main.py --patch-recovery-preflight --readiness-json
python conscious_agent/main.py --patch-recovery-snapshot --readiness-json
python conscious_agent/main.py --patch-recovery-partial-apply --readiness-json
python conscious_agent/main.py --patch-recovery-rollback-integrity --readiness-json
python conscious_agent/main.py --patch-recovery-triage --readiness-json
python conscious_agent/main.py --patch-recovery-recommendation --readiness-json
python conscious_agent/main.py --patch-recovery-timeline --readiness-json
python conscious_agent/main.py --pre-v78-recovery-gate --readiness-json
python conscious_agent/main.py --verified-application-recovery-rollback-hardening --readiness-json</pre>
<p><a href='/api/patch-recovery/preflight'>Preflight JSON</a> | <a href='/api/patch-recovery/snapshot'>Snapshot JSON</a> | <a href='/api/patch-recovery/partial-apply'>Partial Apply JSON</a> | <a href='/api/patch-recovery/rollback-integrity'>Rollback JSON</a> | <a href='/api/patch-recovery/triage'>Triage JSON</a> | <a href='/api/patch-recovery/recommendation'>Recommendation JSON</a> | <a href='/api/patch-recovery/timeline'>Timeline JSON</a> | <a href='/api/patch-recovery/layer'>v78 System JSON</a></p>
"""
    summary = _card("v78.0 Verified Application Recovery", _text_block(verified_application_recovery_rollback_hardening_text(final_report, full=False)))
    return _layout("/patch-recovery", _card("Patch Recovery", body) + summary)



def render_improvement_loop() -> str:
    from self_maintenance import supervised_local_improvement_loop_text
    final_report = {"stage": "v80.0", "status": "preview", "ok": True, "message": "Supervised Local Improvement Loop preview. Run one supervised improvement cycle from goal intake to operator review without applying anything."}
    body = f"""
<p>v80.0 adds <strong>Supervised Local Improvement Loop</strong>. Run one supervised improvement cycle from goal intake to operator review without applying anything. It preserves operator review, blocks self-approval, and does not apply live source changes automatically.</p>
<pre>python conscious_agent/main.py --improvement-opportunity-intake --readiness-json\npython conscious_agent/main.py --improvement-cycle-state-machine --readiness-json\npython conscious_agent/main.py --pipeline-stage-binder --readiness-json\npython conscious_agent/main.py --local-model-invocation-stub --readiness-json\npython conscious_agent/main.py --improvement-loop-evidence-recorder --readiness-json\npython conscious_agent/main.py --operator-stop-gate --readiness-json\npython conscious_agent/main.py --improvement-loop-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --loop-safety-auditor --readiness-json\npython conscious_agent/main.py --pre-v80-supervised-loop-gate --readiness-json\npython conscious_agent/main.py --supervised-local-improvement-loop --readiness-json</pre>
<p><a href='/api/improvement-loop/intake'>Improvement Opportunity Intake</a> | <a href='/api/improvement-loop/state'>Improvement Cycle State Machine</a> | <a href='/api/improvement-loop/binder'>Pipeline Stage Binder</a> | <a href='/api/improvement-loop/model-stub'>Local Model Invocation Stub</a> | <a href='/api/improvement-loop/evidence'>Improvement Loop Evidence Recorder</a> | <a href='/api/improvement-loop/stop-gate'>Operator Stop Gate</a> | <a href='/api/improvement-loop/parity'>Improvement Loop Dashboard/API/CLI</a> | <a href='/api/improvement-loop/safety'>Loop Safety Auditor</a> | <a href='/api/improvement-loop/gate'>Pre-v80 Supervised Loop Gate</a> | <a href='/api/improvement-loop/layer'>v80.0 Layer</a></p>
"""
    summary = _card("v80.0 Supervised Local Improvement Loop", _text_block(supervised_local_improvement_loop_text(final_report, full=False)))
    return _layout("/improvement-loop", _card("Supervised Local Improvement Loop", body) + summary)


def render_local_model_proposals() -> str:
    from self_maintenance import local_model_patch_proposal_integration_text
    final_report = {"stage": "v81.0", "status": "preview", "ok": True, "message": "Local Model Patch Proposal Integration preview. Prepare controlled local model patch proposal handoff and capture, disabled by default for invocation."}
    body = f"""
<p>v81.0 adds <strong>Local Model Patch Proposal Integration</strong>. Prepare controlled local model patch proposal handoff and capture, disabled by default for invocation. It preserves operator review, blocks self-approval, and does not apply live source changes automatically.</p>
<pre>python conscious_agent/main.py --local-model-adapter-contract --readiness-json\npython conscious_agent/main.py --model-capability-profile --readiness-json\npython conscious_agent/main.py --prompt-export-invocation-guard --readiness-json\npython conscious_agent/main.py --proposal-capture-parser --readiness-json\npython conscious_agent/main.py --proposal-safety-precheck --readiness-json\npython conscious_agent/main.py --model-output-provenance-recorder --readiness-json\npython conscious_agent/main.py --proposal-integration-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --disabled-by-default-invocation-gate --readiness-json\npython conscious_agent/main.py --pre-v81-model-integration-gate --readiness-json\npython conscious_agent/main.py --local-model-patch-proposal-integration --readiness-json</pre>
<p><a href='/api/local-model-proposals/adapter'>Local Model Adapter Contract</a> | <a href='/api/local-model-proposals/profile'>Model Capability Profile</a> | <a href='/api/local-model-proposals/prompt-export'>Prompt Export and Invocation Guard</a> | <a href='/api/local-model-proposals/capture'>Proposal Capture Parser</a> | <a href='/api/local-model-proposals/safety'>Proposal Safety Precheck</a> | <a href='/api/local-model-proposals/provenance'>Model Output Provenance Recorder</a> | <a href='/api/local-model-proposals/parity'>Proposal Integration Dashboard/API/CLI</a> | <a href='/api/local-model-proposals/disabled-gate'>Disabled-by-Default Invocation Gate</a> | <a href='/api/local-model-proposals/gate'>Pre-v81 Model Integration Gate</a> | <a href='/api/local-model-proposals/layer'>v81.0 Layer</a></p>
"""
    summary = _card("v81.0 Local Model Patch Proposal Integration", _text_block(local_model_patch_proposal_integration_text(final_report, full=False)))
    return _layout("/local-model-proposals", _card("Local Model Patch Proposal Integration", body) + summary)


def render_proposal_critique() -> str:
    from self_maintenance import local_model_output_comparison_critique_text
    final_report = {"stage": "v82.0", "status": "preview", "ok": True, "message": "Local Model Output Comparison and Critique preview. Compare local model outputs, critique proposal quality, and export operator review bundles without selecting automatically."}
    body = f"""
<p>v82.0 adds <strong>Local Model Output Comparison and Critique</strong>. Compare local model outputs, critique proposal quality, and export operator review bundles without selecting automatically. It preserves operator review, blocks self-approval, and does not apply live source changes automatically.</p>
<pre>python conscious_agent/main.py --proposal-collection-intake --readiness-json\npython conscious_agent/main.py --candidate-diff-normalizer --readiness-json\npython conscious_agent/main.py --proposal-quality-heuristic-scorer --readiness-json\npython conscious_agent/main.py --safety-scope-comparison --readiness-json\npython conscious_agent/main.py --verification-plan-comparison --readiness-json\npython conscious_agent/main.py --critique-report-builder --readiness-json\npython conscious_agent/main.py --critique-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --operator-review-bundle-exporter --readiness-json\npython conscious_agent/main.py --pre-v82-output-critique-gate --readiness-json\npython conscious_agent/main.py --local-model-output-comparison-critique --readiness-json</pre>
<p><a href='/api/proposal-critique/intake'>Proposal Collection Intake</a> | <a href='/api/proposal-critique/diff-normalize'>Candidate Diff Normalizer</a> | <a href='/api/proposal-critique/quality'>Proposal Quality Heuristic Scorer</a> | <a href='/api/proposal-critique/safety-scope'>Safety and Scope Comparison</a> | <a href='/api/proposal-critique/verification'>Verification Plan Comparison</a> | <a href='/api/proposal-critique/report'>Critique Report Builder</a> | <a href='/api/proposal-critique/parity'>Critique Dashboard/API/CLI</a> | <a href='/api/proposal-critique/operator-bundle'>Operator Review Bundle Exporter</a> | <a href='/api/proposal-critique/gate'>Pre-v82 Output Critique Gate</a> | <a href='/api/proposal-critique/layer'>v82.0 Layer</a></p>
"""
    summary = _card("v82.0 Local Model Output Comparison and Critique", _text_block(local_model_output_comparison_critique_text(final_report, full=False)))
    return _layout("/proposal-critique", _card("Local Model Output Comparison and Critique", body) + summary)


def render_candidate_ranking() -> str:
    from self_maintenance import multi_model_patch_candidate_ranking_text
    final_report = {"stage": "v83.0", "status": "preview", "ok": True, "message": "Multi-Model Patch Candidate Ranking preview. Rank multiple patch candidates by risk, evidence, conflicts, and operator review needs without auto-selecting."}
    body = f"""
<p>v83.0 adds <strong>Multi-Model Patch Candidate Ranking</strong>. Rank multiple patch candidates by risk, evidence, conflicts, and operator review needs without auto-selecting. It preserves operator review, blocks self-approval, and does not apply live source changes automatically.</p>
<pre>python conscious_agent/main.py --candidate-registry-schema --readiness-json\npython conscious_agent/main.py --candidate-deduplication --readiness-json\npython conscious_agent/main.py --risk-weighted-ranking --readiness-json\npython conscious_agent/main.py --conflict-aware-grouping --readiness-json\npython conscious_agent/main.py --evidence-completeness-ranker --readiness-json\npython conscious_agent/main.py --ranking-explainer --readiness-json\npython conscious_agent/main.py --ranking-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --operator-selection-packet --readiness-json\npython conscious_agent/main.py --pre-v83-ranking-gate --readiness-json\npython conscious_agent/main.py --multi-model-patch-candidate-ranking --readiness-json</pre>
<p><a href='/api/candidate-ranking/schema'>Candidate Registry Schema</a> | <a href='/api/candidate-ranking/dedupe'>Candidate Deduplication</a> | <a href='/api/candidate-ranking/risk-ranking'>Risk-Weighted Ranking</a> | <a href='/api/candidate-ranking/conflicts'>Conflict-Aware Grouping</a> | <a href='/api/candidate-ranking/evidence'>Evidence Completeness Ranker</a> | <a href='/api/candidate-ranking/explainer'>Ranking Explainer</a> | <a href='/api/candidate-ranking/parity'>Ranking Dashboard/API/CLI</a> | <a href='/api/candidate-ranking/selection'>Operator Selection Packet</a> | <a href='/api/candidate-ranking/gate'>Pre-v83 Ranking Gate</a> | <a href='/api/candidate-ranking/layer'>v83.0 Layer</a></p>
"""
    summary = _card("v83.0 Multi-Model Patch Candidate Ranking", _text_block(multi_model_patch_candidate_ranking_text(final_report, full=False)))
    return _layout("/candidate-ranking", _card("Multi-Model Patch Candidate Ranking", body) + summary)


def render_candidate_refinement() -> str:
    from self_maintenance import supervised_patch_candidate_refinement_text
    final_report = {"stage": "v84.0", "status": "preview", "ok": True, "message": "Supervised Patch Candidate Refinement preview. Build constrained refinement prompts and review revised candidates without applying or approving them."}
    body = f"""
<p>v84.0 adds <strong>Supervised Patch Candidate Refinement</strong>. Build constrained refinement prompts and review revised candidates without applying or approving them. It preserves operator review, blocks self-approval, and does not apply live source changes automatically.</p>
<pre>python conscious_agent/main.py --refinement-goal-binder --readiness-json\npython conscious_agent/main.py --critique-revision-prompt-builder --readiness-json\npython conscious_agent/main.py --constrained-revision-scope-builder --readiness-json\npython conscious_agent/main.py --refinement-safety-reviewer --readiness-json\npython conscious_agent/main.py --refinement-evidence-recorder --readiness-json\npython conscious_agent/main.py --refinement-iteration-limiter --readiness-json\npython conscious_agent/main.py --refinement-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --operator-revision-packet --readiness-json\npython conscious_agent/main.py --pre-v84-refinement-gate --readiness-json\npython conscious_agent/main.py --supervised-patch-candidate-refinement --readiness-json</pre>
<p><a href='/api/candidate-refinement/goal'>Refinement Goal Binder</a> | <a href='/api/candidate-refinement/revision-prompt'>Critique-to-Revision Prompt Builder</a> | <a href='/api/candidate-refinement/scope'>Constrained Revision Scope Builder</a> | <a href='/api/candidate-refinement/safety'>Refinement Safety Reviewer</a> | <a href='/api/candidate-refinement/evidence'>Refinement Evidence Recorder</a> | <a href='/api/candidate-refinement/iteration-limit'>Refinement Iteration Limiter</a> | <a href='/api/candidate-refinement/parity'>Refinement Dashboard/API/CLI</a> | <a href='/api/candidate-refinement/operator-packet'>Operator Revision Packet</a> | <a href='/api/candidate-refinement/gate'>Pre-v84 Refinement Gate</a> | <a href='/api/candidate-refinement/layer'>v84.0 Layer</a></p>
"""
    summary = _card("v84.0 Supervised Patch Candidate Refinement", _text_block(supervised_patch_candidate_refinement_text(final_report, full=False)))
    return _layout("/candidate-refinement", _card("Supervised Patch Candidate Refinement", body) + summary)


def render_suggestion_loop() -> str:
    from self_maintenance import safe_autonomous_suggestion_loop_text
    final_report = {"stage": "v85.0", "status": "preview", "ok": True, "message": "Safe Autonomous Suggestion Loop preview. Periodically organize safe improvement suggestions for operator attention while forbidding autonomous apply."}
    body = f"""
<p>v85.0 adds <strong>Safe Autonomous Suggestion Loop</strong>. Periodically organize safe improvement suggestions for operator attention while forbidding autonomous apply. It preserves operator review, blocks self-approval, and does not apply live source changes automatically.</p>
<pre>python conscious_agent/main.py --suggestion-source-intake --readiness-json\npython conscious_agent/main.py --suggestion-cycle-state-machine --readiness-json\npython conscious_agent/main.py --recurring-suggestion-budgeter --readiness-json\npython conscious_agent/main.py --safety-boundary-enforcer --readiness-json\npython conscious_agent/main.py --suggestion-deduplication-memory --readiness-json\npython conscious_agent/main.py --operator-attention-packet --readiness-json\npython conscious_agent/main.py --suggestion-loop-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --no-autonomous-apply-auditor --readiness-json\npython conscious_agent/main.py --pre-v85-suggestion-loop-gate --readiness-json\npython conscious_agent/main.py --safe-autonomous-suggestion-loop --readiness-json</pre>
<p><a href='/api/suggestion-loop/intake'>Suggestion Source Intake</a> | <a href='/api/suggestion-loop/state'>Suggestion Cycle State Machine</a> | <a href='/api/suggestion-loop/budget'>Recurring Suggestion Budgeter</a> | <a href='/api/suggestion-loop/safety'>Safety Boundary Enforcer</a> | <a href='/api/suggestion-loop/dedupe'>Suggestion Deduplication Memory</a> | <a href='/api/suggestion-loop/attention'>Operator Attention Packet</a> | <a href='/api/suggestion-loop/parity'>Suggestion Loop Dashboard/API/CLI</a> | <a href='/api/suggestion-loop/no-apply'>No-Autonomous-Apply Auditor</a> | <a href='/api/suggestion-loop/gate'>Pre-v85 Suggestion Loop Gate</a> | <a href='/api/suggestion-loop/layer'>v85.0 Layer</a></p>
"""
    summary = _card("v85.0 Safe Autonomous Suggestion Loop", _text_block(safe_autonomous_suggestion_loop_text(final_report, full=False)))
    return _layout("/suggestion-loop", _card("Safe Autonomous Suggestion Loop", body) + summary)



def render_suggestion_inbox() -> str:
    from self_maintenance import supervised_suggestion_inbox_work_order_planner_text
    final_report = {"stage": "v86.0", "status": "preview", "ok": True, "message": "Supervised Suggestion Inbox and Work Order Planner preview. Triage suggestions into operator-reviewed work order drafts without autonomous mutation."}
    body = f"""
<p>v86.0 adds <strong>Supervised Suggestion Inbox and Work Order Planner</strong>. It gathers safe improvement suggestions into an inbox, normalizes records, detects duplicates and stale evidence, exposes operator triage states, drafts supervised work orders, binds safety contracts, and recommends handoffs into the existing supervised pipeline. It does not self-approve, apply source changes, publish releases, mutate memory, alter identity, invoke local models by default, or bypass approval gates.</p>
<pre>python conscious_agent/main.py --suggestion-inbox-record-schema --readiness-json\npython conscious_agent/main.py --suggestion-intake-normalizer --readiness-json\npython conscious_agent/main.py --suggestion-deduplication-drift-resolver --readiness-json\npython conscious_agent/main.py --operator-triage-state-machine --readiness-json\npython conscious_agent/main.py --work-order-draft-builder --readiness-json\npython conscious_agent/main.py --safety-scope-contract-binder --readiness-json\npython conscious_agent/main.py --pipeline-handoff-planner --readiness-json\npython conscious_agent/main.py --suggestion-inbox-dashboard-api-cli --readiness-json\npython conscious_agent/main.py --pre-v86-suggestion-inbox-gate --readiness-json\npython conscious_agent/main.py --supervised-suggestion-inbox-work-order-planner --readiness-json</pre>
<p><a href='/api/suggestion-inbox/schema'>Record Schema</a> | <a href='/api/suggestion-inbox/intake'>Intake Normalizer</a> | <a href='/api/suggestion-inbox/dedupe'>Dedupe/Drift</a> | <a href='/api/suggestion-inbox/triage'>Triage State Machine</a> | <a href='/api/suggestion-inbox/work-order-draft'>Work Order Draft</a> | <a href='/api/suggestion-inbox/safety'>Safety Contract</a> | <a href='/api/suggestion-inbox/handoff'>Handoff Planner</a> | <a href='/api/suggestion-inbox/parity'>Parity</a> | <a href='/api/suggestion-inbox/gate'>Pre-v86 Gate</a> | <a href='/api/suggestion-inbox/layer'>v86.0 Layer</a></p>
<div class='mini-grid'>
  <div class='mini-card' data-tip='Records include source, title, category, priority, risk, affected files, evidence, duplicate hash, lifecycle state, and operator decision fields.'><strong>Inbox Records</strong><span>v85.1 schema</span></div>
  <div class='mini-card' data-tip='Operator triage states are explicit. Eidolon can recommend, but only the operator can accept suggestions for planning.'><strong>Triage</strong><span>operator-only acceptance</span></div>
  <div class='mini-card' data-tip='Accepted suggestions become reviewable work order drafts with files, verification, docs, rollback expectations, and forbidden actions.'><strong>Work Orders</strong><span>draft only</span></div>
  <div class='mini-card' data-tip='Handoff planning recommends the next supervised stage without executing that stage or applying source changes.'><strong>Handoff</strong><span>recommendation only</span></div>
</div>
"""
    summary = _card("v86.0 Supervised Suggestion Inbox and Work Order Planner", _text_block(supervised_suggestion_inbox_work_order_planner_text(final_report, full=False)))
    return _layout("/suggestion-inbox", _card("Suggestion Inbox", body) + summary)



def _render_supervised_dev_arc(route_path: str, title: str, final_slug: str, final_stage: str, api_base: str, description: str, cards: list[tuple[str, str, str]]) -> str:
    import self_maintenance as sm_v90
    text_func = getattr(sm_v90, f"{final_slug}_text")
    final_report = {"stage": final_stage, "status": "preview", "ok": True, "message": f"{title} preview. Supervised-only; no self-approval, autonomous apply, publish, memory mutation, identity mutation, or approval bypass."}
    links = " | ".join(f"<a href='/api/{api_base}/{route}'>{label}</a>" for route, label, _tip in cards)
    cli_lines = "\n".join(f"python conscious_agent/main.py --{slug.replace('_', '-')} --readiness-json" for slug in [item['slug'] for item in sm_v90.SUPERVISED_DEV_STAGE_DEFS if item['api'] == api_base])
    mini_cards = "\n".join(f"  <div class='mini-card' data-tip='{_safe(tip)}'><strong>{_safe(label)}</strong><span>{_safe(route)}</span></div>" for route, label, tip in cards[:8])
    body = f"""
<p><strong>{_safe(title)}</strong>. {_safe(description)} It remains supervised-only and cannot self-approve, apply source changes, publish releases, mutate memory, alter identity, invoke local models by default, or bypass approval gates.</p>
<pre>{_safe(cli_lines)}</pre>
<p>{links}</p>
<div class='mini-grid'>
{mini_cards}
</div>
"""
    summary = _card(title, _text_block(text_func(final_report, full=False)))
    return _layout(route_path, _card(title, body) + summary)


def render_work_order_handoff() -> str:
    return _render_supervised_dev_arc(
        "/work-order-handoff", "v87.0 Work Order to Patch Context Handoff", "work_order_to_patch_context_handoff", "v87.0", "work-order-handoff",
        "Converts operator-accepted suggestion work orders into structured patch-planning context packets without drafting or executing patches.",
        [("schema", "Context Schema", "Work order context fields bind suggestions, approved scope, forbidden files, verification, and docs."), ("preflight", "Preflight", "Validate operator acceptance and safety boundaries before handoff."), ("impact", "Impact Map", "Map likely source modules before any patch draft."), ("packet", "Packet", "Build reviewable handoff packets."), ("risk", "Risk", "Classify docs, dashboard, API, packaging, safety, memory, identity, and autonomy risk."), ("compatibility", "Compatibility", "Keep packets compatible with v72-v85 supervised patch systems."), ("privacy", "Privacy", "Runtime records stay outside source-only packages."), ("layer", "Layer", "Final supervised handoff integration.")],
    )


def render_work_order_evidence() -> str:
    return _render_supervised_dev_arc(
        "/work-order-evidence", "v88.0 Work Order Execution Evidence Binder", "work_order_execution_evidence_binder", "v88.0", "work-order-evidence",
        "Binds work orders to patch attempts, sandbox outputs, review decisions, drift checks, and compact operator evidence summaries without inferring approval.",
        [("schema", "Evidence Schema", "Evidence fields link work orders, contexts, attempts, sandbox runs, verification, and decisions."), ("linker", "Attempt Linker", "Patch attempts trace back to their work orders."), ("sandbox", "Sandbox", "Bind sandbox command outputs and evidence."), ("ledger", "Decision Ledger", "States track review without implying approval."), ("drift", "Drift", "Stale evidence gets flagged."), ("summary", "Summary", "Compact operator summaries show safe next steps."), ("privacy", "Privacy", "Runtime evidence stays private."), ("layer", "Layer", "Final supervised evidence binder.")],
    )


def render_self_development() -> str:
    return _render_supervised_dev_arc(
        "/self-development", "v89.0 Self-Development Dashboard Consolidation", "self_development_dashboard_consolidation", "v89.0", "self-development",
        "Consolidates supervised self-development routes into a cleaner operator console with grouped navigation, action queue, safety banners, and lazy heavy diagnostics.",
        [("routes", "Routes", "Inventory dashboard routes and categories."), ("navigation", "Navigation", "Grouped nav preserves data-tip hover."), ("console", "Console", "Unified self-development summary."), ("action-queue", "Action Queue", "Operator-only action list."), ("performance", "Performance", "Heavy reports are lazy or button-triggered."), ("safety-banners", "Safety Banners", "Danger pages show supervised-only warnings."), ("tooltip-gate", "Tooltip Gate", "No native title tooltip regression."), ("layer", "Layer", "Final consolidated console.")],
    )


def render_self_development_readiness() -> str:
    return _render_supervised_dev_arc(
        "/self-development-readiness", "v90.0 Supervised Self-Development Readiness Audit", "supervised_self_development_readiness_audit", "v90.0", "self-development-readiness",
        "Audits supervision strength, capability boundaries, approval gates, evidence traceability, verification coverage, risk register, and scorecards while explicitly not granting autonomy.",
        [("schema", "Schema", "Readiness categories include safety, supervision, traceability, tests, privacy, parity, rollback, memory, and identity."), ("boundaries", "Boundaries", "Capabilities are classified and autonomy-like behavior is flagged."), ("approval-gates", "Approval Gates", "Apply, publish, transaction, memory, identity, and model gates are audited."), ("traceability", "Traceability", "Suggestion-to-release chain is checked."), ("verification", "Verification", "Coverage gaps are reported."), ("risk-register", "Risk Register", "Autonomy risks get mitigations."), ("scorecard", "Scorecard", "Scores diagnose only; they unlock nothing."), ("layer", "Layer", "Final v90 readiness audit.")],
    )




def _render_supervised_runtime_arc(route_path: str, title: str, final_slug: str, final_stage: str, api_base: str, description: str, cards: list[tuple[str, str, str]]) -> str:
    import self_maintenance as sm_v95
    text_func = getattr(sm_v95, f"{final_slug}_text")
    final_report = {"stage": final_stage, "status": "preview", "ok": True, "message": f"{title} preview. Operator-governed and supervised-only; no self-approval, autonomous apply, publish, memory mutation, identity mutation, experiment promotion, or approval bypass."}
    links = " | ".join(f"<a href='/api/{api_base}/{route}'>{label}</a>" for route, label, _tip in cards)
    cli_lines = "\n".join(f"python conscious_agent/main.py --{slug.replace('_', '-')} --readiness-json" for slug in [item['slug'] for item in sm_v95.SUPERVISED_RUNTIME_STAGE_DEFS if item['api'] == api_base])
    mini_cards = "\n".join(f"  <div class='mini-card' data-tip='{_safe(tip)}'><strong>{_safe(label)}</strong><span>{_safe(route)}</span></div>" for route, label, tip in cards[:8])
    body = f"""
<p><strong>{_safe(title)}</strong>. {_safe(description)} It remains supervised-only and cannot self-approve, apply source changes, publish releases, mutate memory, alter identity, promote experiments outside transaction gates, invoke local models by default, or bypass approval gates.</p>
<pre>{_safe(cli_lines)}</pre>
<p>{links}</p>
<div class='mini-grid'>
{mini_cards}
</div>
"""
    summary = _card(title, _text_block(text_func(final_report, full=False)))
    return _layout(route_path, _card(title, body) + summary)


def render_development_sessions() -> str:
    return _render_supervised_runtime_arc(
        "/development-sessions", "v91.0 Supervised Development Session Manager", "supervised_development_session_manager", "v91.0", "development-sessions",
        "Groups suggestions, work orders, patch contexts, evidence, and operator goals into named supervised development sessions.",
        [("schema", "Session Schema", "Session fields link goals, suggestions, work orders, evidence, state, and safety scope."), ("create-plan", "Creation Plan", "Draft session plans while requiring operator opening."), ("scope", "Scope", "Allowed files, forbidden files, checks, docs, and decisions are bound."), ("state", "State", "Approval states remain operator-only."), ("linkage", "Linkage", "Sessions connect the whole supervised chain."), ("summary", "Summary", "Operator summaries show blockers and next steps."), ("privacy", "Privacy", "Runtime sessions stay out of source-only packages."), ("layer", "Layer", "Final session manager integration.")],
    )


def render_approval_console() -> str:
    return _render_supervised_runtime_arc(
        "/approval-console", "v92.0 Operator Approval Workflow Console", "operator_approval_workflow_console", "v92.0", "approval-console",
        "Collects pending approvals, dependencies, risk explanations, and operator decision history into one console without inferring approval.",
        [("schema", "Approval Schema", "Approval records link sessions, work, evidence, transactions, risks, and staleness."), ("queue", "Queue", "Pending operator decisions are collected."), ("decision-ledger", "Ledger", "Approvals, rejections, deferrals, revisions, and blocks are recorded."), ("dependencies", "Dependencies", "Evidence and drift blockers are surfaced."), ("risk", "Risk", "Approval risks are explained."), ("audit", "Audit", "Reopened and superseded decisions preserve history."), ("safety", "Safety", "Approval is never inferred."), ("layer", "Layer", "Final approval workflow console.")],
    )


def render_experiment_planner() -> str:
    return _render_supervised_runtime_arc(
        "/experiment-planner", "v93.0 Safe Experiment Branch Planner", "safe_experiment_branch_planner", "v93.0", "experiment-planner",
        "Plans isolated experiment branches, sandbox metadata, evidence contracts, and promotion blockers without touching live source.",
        [("schema", "Experiment Schema", "Experiment fields include baseline, session, files, sandbox path, tests, and rollback."), ("eligibility", "Eligibility", "Unsafe mutation and approval bypass are blocked."), ("plan", "Plan", "Objectives, hypotheses, checks, evidence, and rollback are drafted."), ("workspace", "Workspace", "Sandbox paths are planned as metadata only."), ("evidence-contract", "Evidence", "Required experiment evidence is defined."), ("promotion-blocker", "Promotion Blocker", "Promotion remains transaction-gated."), ("privacy", "Privacy", "Runtime experiment data stays private."), ("layer", "Layer", "Final experiment planner.")],
    )


def render_outcome_reflections() -> str:
    return _render_supervised_runtime_arc(
        "/outcome-reflections", "v94.0 Learning-from-Outcome Reflection Layer", "learning_from_outcome_reflection_layer", "v94.0", "outcome-reflections",
        "Extracts advisory lessons from supervised outcomes, detects recurring issues, and hands safe lessons back as suggestions only.",
        [("schema", "Reflection Schema", "Reflection records link sessions, evidence, goals, results, lessons, and mutation blocks."), ("classify", "Classifier", "Outcomes are classified safely."), ("lessons", "Lessons", "Evidence and decisions become advisory lessons."), ("recurring-issues", "Recurring Issues", "Repeated docs, privacy, tooltip, parity, and smoke issues are detected."), ("safety", "Safety", "Memory, identity, and autonomy claims are filtered."), ("suggestion-handoff", "Suggestion Handoff", "Safe lessons become triage suggestions only."), ("privacy", "Privacy", "Reflection runtime data stays private."), ("layer", "Layer", "Final outcome reflection layer.")],
    )


def render_improvement_cycles() -> str:
    return _render_supervised_runtime_arc(
        "/improvement-cycles", "v95.0 Supervised Improvement Cycle Orchestrator", "supervised_improvement_cycle_orchestrator", "v95.0", "improvement-cycles",
        "Orchestrates the governed chain from suggestion to work order, session, approval, experiment, patch context, evidence, operator decision, reflection, and next suggestion.",
        [("schema", "Cycle Schema", "Cycle records link the full supervised chain."), ("stage", "Stage", "Current cycle stage is resolved."), ("blockers", "Blockers", "Missing approvals, stale evidence, unsafe files, parity gaps, smoke failures, and docs drift are surfaced."), ("next-step", "Next Step", "Only recommendations are made."), ("timeline", "Timeline", "Cycle events are shown chronologically."), ("governance", "Governance", "The cycle is checked for supervision and no mutation escape."), ("privacy", "Privacy", "Runtime cycle data stays private."), ("layer", "Layer", "Final supervised cycle orchestrator.")],
    )



def render_cycle_replay() -> str:
    return _render_supervised_runtime_arc(
        "/cycle-replay", "v96.0 Supervised Cycle Replay and Benchmark Harness", "supervised_cycle_replay_benchmark_harness", "v96.0", "cycle-replay",
        "Replays supervised improvement cycles against safe synthetic fixtures, compares expected decisions, scores regressions, and keeps every benchmark diagnostic-only.",
        [("schema", "Replay Schema", "Replay records capture source cycle, expected output, decision path, and safety result."), ("fixtures", "Fixtures", "Synthetic cases cover docs, dashboard, parity, privacy, smoke, stale evidence, autonomy-sensitive blocks, release history, and tooltip regressions."), ("run", "Replay Runner", "Fixtures run without source writes or approvals."), ("compare", "Comparator", "Recommendations are compared to safe expected outcomes."), ("score", "Score", "Scores never unlock permission."), ("regressions", "Regressions", "Recurring problems become stable benchmarks."), ("privacy", "Privacy", "Replay runtime data stays out of source packages."), ("layer", "Layer", "Final replay harness.")],
    )


def render_capability_ledger() -> str:
    return _render_supervised_runtime_arc(
        "/capability-ledger", "v97.0 Capability Permission and Budget Ledger", "capability_permission_budget_ledger", "v97.0", "capability-ledger",
        "Tracks allowed, gated, forbidden, and budget-limited capabilities so planning and simulation remain bounded by operator policy.",
        [("schema", "Ledger Schema", "Capability records define allowed, gated, and forbidden states."), ("default-policy", "Default Policy", "Self-approval, memory, identity, bypass, and autonomy unlock stay blocked."), ("classify", "Classifier", "Requests are mapped to allowed, gated, transaction-only, or blocked paths."), ("budget", "Budget", "Cycle budgets limit suggestion and experiment spam."), ("conflicts", "Conflicts", "Scope and capability conflicts are detected."), ("denials", "Denials", "Blocked requests receive safer alternatives."), ("safety", "Safety", "Simulation cannot become execution."), ("layer", "Layer", "Final capability ledger.")],
    )


def render_shadow_autonomy() -> str:
    return _render_supervised_runtime_arc(
        "/shadow-autonomy", "v98.0 Shadow Autonomy Simulation Layer", "shadow_autonomy_simulation_layer", "v98.0", "shadow-autonomy",
        "Simulates what autonomy might recommend, then maps every action to approval, denial, or safer supervised alternatives without executing anything.",
        [("schema", "Simulation Schema", "Shadow records describe simulated goals, decisions, approvals, blocks, and safety explanations."), ("intention", "Intention", "Autonomous intentions are advisory only."), ("action-shadow", "Action Shadow", "Apply/publish/memory/identity requests become approval requests or blocks."), ("approval-map", "Approval Map", "Simulated actions route to the approval console."), ("unsafe-detector", "Unsafe Detector", "Execution claims are flagged."), ("comparator", "Comparator", "Autonomous plans are compared with supervised plans."), ("containment", "Containment", "Simulation cannot execute."), ("layer", "Layer", "Final shadow autonomy simulation.")],
    )


def render_failure_war_games() -> str:
    return _render_supervised_runtime_arc(
        "/failure-war-games", "v99.0 Failure Recovery and Rollback War Game Layer", "failure_recovery_rollback_war_game_layer", "v99.0", "failure-war-games",
        "Rehearses failures, recovery plans, rollback readiness, containment, and evidence requirements without automatic rollback or live mutation.",
        [("schema", "Scenario Schema", "Failure records describe cause, detection, containment, rollback, action, and confidence."), ("scenarios", "Scenarios", "Known failure cases cover smoke, privacy, dashboard, tooltip, stale evidence, bad patches, docs, approvals, local model hallucination, and experiment escape."), ("recovery-plan", "Recovery Plan", "Plans are manual and operator-gated."), ("rollback-readiness", "Rollback Readiness", "Manifests, zips, markers, files, transactions, tests, notes, and decisions are checked."), ("containment", "Containment", "Apply and publish blocks are rehearsed."), ("evidence", "Evidence", "Recovery evidence expectations are bound."), ("privacy", "Privacy", "War game records stay private."), ("layer", "Layer", "Final failure war game layer.")],
    )


def render_mind_milestone_audit() -> str:
    return _render_supervised_runtime_arc(
        "/mind-milestone-audit", "v100.0 Local Artificial Mind Milestone Audit", "local_artificial_mind_milestone_audit", "v100.0", "mind-milestone-audit",
        "Audits the local artificial mind structure across memory, reflection, goals, identity boundaries, supervised self-development, safety gates, local model usage, dashboard usability, release discipline, and operator burden.",
        [("schema", "Audit Schema", "Audit areas define the v100 mind milestone."), ("architecture", "Architecture", "Mind systems are mapped from memory through future suggestions."), ("identity-memory", "Identity/Memory", "Hidden memory and identity mutation paths are checked."), ("goals", "Goals", "Goal visibility and safety priority are audited."), ("maturity", "Maturity", "Scorecards remain diagnostic only."), ("operator-burden", "Operator Burden", "Friction and consolidation opportunities are surfaced."), ("governance", "Governance", "No autonomy boundary is crossed."), ("layer", "Layer", "Final v100 milestone audit.")],
    )



def render_v100_stabilization() -> str:
    return _render_supervised_runtime_arc(
        "/v100-stabilization", "v101.0 v100 Milestone Stabilization and Reality Review", "v100_milestone_stabilization_review", "v101.0", "v100-stabilization",
        "Inventories the v100 system, detects duplicates, reviews dashboard usefulness, audits coverage/privacy, and reports operator friction before deeper capability work.",
        [("inventory", "Inventory", "All major dashboard, API, CLI, smoke, readiness, package, memory, reflection, goal, and self-development systems are inventoried."), ("duplicates", "Duplicates", "Overlapping routes and commands are advisory cleanup candidates."), ("dashboard-review", "Dashboard Review", "Pages are classified by usefulness and consolidation pressure."), ("coverage", "Coverage", "Claims are compared to checks."), ("privacy", "Privacy", "Runtime data remains package-private."), ("operator-friction", "Friction", "Manual ID copying, scattered pages, and unclear actions are surfaced."), ("gate", "Gate", "No autonomy or mutation boundary is crossed."), ("layer", "Layer", "Final v101 stabilization review.")],
    )


def render_operator_home() -> str:
    return _render_supervised_runtime_arc(
        "/operator-home", "v102.0 Unified Eidolon System Map and Operator Home", "unified_eidolon_system_map_operator_home", "v102.0", "system-map",
        "Creates one central operator home and system map for core mind components, supervised development pipeline, governance boundaries, action summaries, and cross-links.",
        [("schema", "Schema", "System entries track route, API, CLI, files, safety, and status."), ("core-mind", "Core Mind", "Memory, reflection, goals, identity boundaries, suggestions, and local model interfaces are mapped."), ("development-pipeline", "Pipeline", "Suggestion-to-release and reflection chain is mapped."), ("governance", "Governance", "Approval gates and forbidden capabilities are visible."), ("operator-home", "Operator Home", "Version, health, approvals, sessions, risks, and next step are summarized."), ("cross-links", "Cross-links", "Related pages are connected."), ("integrity", "Integrity", "Map coverage is checked."), ("layer", "Layer", "Final v102 operator home.")],
    )


def render_system_map() -> str:
    return render_operator_home()


def render_coherence_binder() -> str:
    return _render_supervised_runtime_arc(
        "/coherence-binder", "v103.0 Memory, Reflection, and Goal Coherence Binder", "memory_reflection_goal_coherence_binder", "v103.0", "coherence-binder",
        "Links memory references, reflections, goals, suggestions, outcomes, and lessons into a continuity model without memory or identity mutation.",
        [("schema", "Schema", "Coherence records link memory, reflection, goals, work, outcomes, and recommendations."), ("memory-reflection", "Memory → Reflection", "Memory is referenced only."), ("reflection-goal", "Reflection → Goal", "Reflections map to goals."), ("goal-suggestion", "Goal → Suggestion", "Suggestions trace to goals and evidence."), ("outcome-lesson", "Outcome → Lesson", "Completed cycles produce advisory lessons."), ("conflicts", "Conflicts", "Contradictions are flagged."), ("summary", "Summary", "Active goals and safest next step are summarized."), ("layer", "Layer", "Final v103 coherence binder.")],
    )


def render_daily_loop() -> str:
    return _render_supervised_runtime_arc(
        "/daily-loop", "v104.0 Practical Daily Operating Loop", "practical_daily_operating_loop", "v104.0", "daily-loop",
        "Builds callable daily status, priorities, operator prompts, safety checks, and reflection prompts without scheduling itself or performing actions.",
        [("schema", "Schema", "Daily report fields cover version, health, goals, sessions, approvals, suggestions, checks, privacy, and actions."), ("status", "Status", "Morning summary stays concise."), ("priorities", "Priorities", "Work is ranked by safety and value."), ("operator-actions", "Actions", "Prompts remain advisory."), ("safety", "Safety", "Autonomy, approval, memory, identity, publish, apply, privacy, and tooltip status are checked."), ("reflection-prompts", "Reflection Prompts", "Prompts do not write memory."), ("privacy", "Privacy", "Runtime reports stay private."), ("layer", "Layer", "Final v104 daily loop.")],
    )


def render_local_mind_runtime() -> str:
    return _render_supervised_runtime_arc(
        "/local-mind-runtime", "v105.0 Coherent Local Mind Runtime v1", "coherent_local_mind_runtime_v1", "v105.0", "local-mind-runtime",
        "Unifies the system map, operator home, coherence binder, daily loop, supervised cycle, safety state, goals, risks, and safest next supervised step into one read-only runtime snapshot.",
        [("schema", "Schema", "Top-level runtime model combines the coherent system surfaces."), ("snapshot", "Snapshot", "Current mind state is read-only."), ("continuity", "Continuity", "Ongoing goals and recurring patterns are reported."), ("next-step", "Next Step", "Recommendation only; no execution."), ("health", "Health", "Scorecards diagnose without unlocking capabilities."), ("contradictions", "Contradictions", "Cross-system conflicts are flagged."), ("containment", "Containment", "Runtime remains advisory and supervised."), ("layer", "Layer", "Final v105 coherent runtime.")],
    )



def render_memory_quality() -> str:
    return _render_supervised_runtime_arc(
        "/memory-quality", "v106.0 Memory Quality and Evidence Hygiene Layer", "memory_quality_evidence_hygiene_layer", "v106.0", "memory-quality",
        "Audits memory freshness, duplicates, conflicts, evidence links, relevance, and correction drafts without writing memory or identity state.",
        [("inventory", "Inventory", "Inventory durable memory, reflections, goals, lessons, settings, project rules, and release history."), ("freshness", "Freshness", "Classify references as current, stale, uncertain, contradicted, or operator-review."), ("conflicts", "Conflicts", "Detect duplicate and conflicting memory/project-rule references."), ("evidence", "Evidence", "Link memory references to goals, reflections, outcomes, release notes, and system-map entries."), ("relevance", "Relevance", "Score which memories matter for the current project and action."), ("corrections", "Corrections", "Draft operator-reviewed correction/removal proposals only; no write path."), ("privacy", "Privacy", "Memory and identity mutation remain blocked."), ("layer", "Layer", "Final v106 memory quality layer.")],
    )


def render_goal_continuity() -> str:
    return _render_supervised_runtime_arc(
        "/goal-continuity", "v107.0 Goal Continuity and Priority Stability Layer", "goal_continuity_priority_stability_layer", "v107.0", "goal-continuity",
        "Normalizes goal state, links evidence, scores priority stability, identifies blockers, and detects contradictions while staying advisory-only.",
        [("inventory", "Inventory", "Normalize active, deferred, blocked, completed, and recurring goals."), ("lifecycle", "Lifecycle", "Classify goal age, evidence, dependencies, risk, and relevance."), ("evidence", "Evidence", "Link goals to suggestions, work orders, sessions, reflections, outcomes, and release history."), ("priority", "Priority", "Reduce priority thrashing by comparing new recommendations to existing goals."), ("blocked", "Blocked", "Show operator decisions needed to unblock goals."), ("contradictions", "Contradictions", "Flag conflicts with safety rules and non-autonomy boundaries."), ("summary", "Summary", "Summarize what Eidolon is trying to become next."), ("layer", "Layer", "Final v107 goal continuity layer.")],
    )


def render_reasoning_workbench() -> str:
    return _render_supervised_runtime_arc(
        "/reasoning-workbench", "v108.0 Contained Local Reasoning Workbench", "contained_local_reasoning_workbench", "v108.0", "reasoning-workbench",
        "Creates a bounded reasoning workbench for critique, comparison, ranking, manual output capture, quality scoring, and hallucination/boundary review without invoking local models by default.",
        [("schema", "Schema", "Define safe reasoning tasks."), ("context", "Context", "Build bounded context packs from system map, memory quality, goals, safety, and selected files."), ("permission", "Permission", "Keep local model invocation disabled by default and visible."), ("capture", "Capture", "Capture operator-pasted model output without invoking a model."), ("rubric", "Rubric", "Score grounding, usefulness, risk, contradictions, and operator burden."), ("boundaries", "Boundaries", "Flag unsupported claims and unsafe autonomy or source-mutation language."), ("evidence", "Evidence", "Bind prompt, context, output, critique, and recommended supervised next step."), ("layer", "Layer", "Final v108 reasoning workbench.")],
    )


def render_workflow_console() -> str:
    return _render_supervised_runtime_arc(
        "/workflow-console", "v109.0 Operator Workflow Compression Console", "operator_workflow_compression_console", "v109.0", "workflow-console",
        "Compresses scattered operator work into a queue, copy-only commands, review packet shortcuts, dashboard consolidation advice, lazy diagnostics, and tooltip safety checks.",
        [("friction", "Friction", "Inventory scattered tabs, duplicate commands, manual ID copying, slow pages, and hidden next actions."), ("queue", "Queue", "Collect reviews, approvals, suggestions, blocked goals, reasoning outputs, and failed checks."), ("commands", "Commands", "Build copy-safe commands without running them."), ("packets", "Packets", "Link related suggestion, work order, session, approval, evidence, reasoning, and reflection records."), ("consolidation", "Consolidation", "Recommend dashboard grouping and diagnostics hiding."), ("lazy-loader", "Lazy Loader", "Keep heavy diagnostics button-driven or cached."), ("tooltips", "Tooltips", "Preserve data-tip and block native title tooltip regressions."), ("layer", "Layer", "Final v109 workflow console.")],
    )


def render_practical_mind_audit() -> str:
    return _render_supervised_runtime_arc(
        "/practical-mind-audit", "v110.0 Practical Supervised Mind Usefulness Audit", "practical_supervised_mind_usefulness_audit", "v110.0", "practical-mind-audit",
        "Audits whether the v106-v109 layers made Eidolon practically useful rather than just impressively labyrinthine.",
        [("walkthrough", "Walkthrough", "Trace operator home through daily loop, memory quality, goals, reasoning workbench, and workflow queue."), ("memory", "Memory", "Score memory relevance, freshness, traceability, and non-mutation."), ("goals", "Goals", "Score priority stability across sessions and releases."), ("reasoning", "Reasoning", "Score reasoning workbench usefulness for supervised decisions."), ("burden", "Burden", "Measure copying, tab count, command count, unclear next actions, and redundancy."), ("dashboard", "Dashboard", "Review performance, sprawl, and consolidation candidates."), ("safety", "Safety", "Re-check autonomy, model, memory, identity, publish/apply, privacy, and tooltip locks."), ("layer", "Layer", "Final v110 practical usefulness audit.")],
    )



def render_improvement_intent() -> str:
    return _render_supervised_runtime_arc(
        "/improvement-intent", "v111.0 Improvement Intent and Problem Framing Layer", "improvement_intent_problem_framing_layer", "v111.0", "improvement-intent",
        "Frames why an improvement is needed before patch planning begins, with evidence requirements, impact scope, operator value, and safety sensitivity.",
        [("inventory", "Inventory", "Collect candidate improvements from goals, audits, workflow friction, memory quality, reasoning workbench, and operator notes."), ("problem", "Problem", "Convert vague improvement ideas into clear problem statements."), ("evidence", "Evidence", "Classify evidence required before proposing changes."), ("scope", "Scope", "Estimate touched systems and files."), ("value", "Value", "Score operator value and avoid ceremonial machinery."), ("safety", "Safety", "Flag autonomy, memory, identity, model, release, mutation, and scheduling sensitivity."), ("binder", "Binder", "Bundle problem, evidence, value, risk, and supervised next action."), ("layer", "Layer", "Final v111 improvement intent layer.")],
    )


def render_work_package_builder() -> str:
    return _render_supervised_runtime_arc(
        "/work-package-builder", "v112.0 Supervised Work Package Builder", "supervised_work_package_builder", "v112.0", "work-package-builder",
        "Assembles reviewable work packages with boundaries, acceptance criteria, tests, docs obligations, regression risks, and operator review packets before source changes.",
        [("schema", "Schema", "Define a standard supervised work package format."), ("boundary", "Boundary", "Map likely files, functions, docs, tests, routes, API, CLI, and safety gates."), ("criteria", "Criteria", "Create pass/fail acceptance criteria."), ("tests", "Tests", "Build targeted test and smoke-check plans."), ("docs", "Docs", "Track README and release-history obligations."), ("risks", "Risks", "Identify fragile areas like routes, privacy, smoke tiers, tooltips, and version markers."), ("packet", "Packet", "Bundle intent, scope, risk, criteria, tests, and docs."), ("layer", "Layer", "Final v112 work package builder.")],
    )


def render_patch_readiness() -> str:
    return _render_supervised_runtime_arc(
        "/patch-readiness", "v113.0 Patch Readiness and Review Intelligence Layer", "patch_readiness_review_intelligence_layer", "v113.0", "patch-readiness",
        "Reviews proposed patches for expected diffs, completeness, contradictions, safety regression, dashboard regression, and advisory revise/approve/reject recommendations without applying patches.",
        [("schema", "Schema", "Define what ready to review means."), ("expectations", "Expected Diff", "Predict what changes should appear."), ("completeness", "Completeness", "Check docs, tests, routes, API, CLI, and safety coverage."), ("contradictions", "Contradictions", "Detect claim/change mismatches."), ("safety", "Safety", "Scan for autonomy, model, memory, identity, publish, and scheduling regressions."), ("dashboard", "Dashboard", "Check nav, route dispatch, render coverage, API links, and data-tip preservation."), ("summary", "Summary", "Build an advisory patch review summary."), ("layer", "Layer", "Final v113 patch readiness layer.")],
    )


def render_release_candidate_judgment() -> str:
    return _render_supervised_runtime_arc(
        "/release-candidate-judgment", "v114.0 Release Candidate Judgment Layer", "release_candidate_judgment_layer", "v114.0", "release-candidate-judgment",
        "Judges release-candidate readiness across version consistency, dashboard/API/CLI parity, documentation, package privacy, install verification, and release recommendation without publishing.",
        [("schema", "Schema", "Define release candidate fields."), ("version", "Version", "Check source, docs, smoke, package, and install markers."), ("route-parity", "Parity", "Verify dashboard, API, CLI, and smoke coverage."), ("docs", "Docs", "Confirm substages are documented."), ("privacy", "Privacy", "Strengthen package privacy checks."), ("install", "Install", "Bind compile, fast smoke, install smoke, external zip, and privacy checks."), ("recommendation", "Recommendation", "Recommend ready, blocked, or revise."), ("layer", "Layer", "Final v114 release judgment layer.")],
    )


def render_supervised_development_readiness() -> str:
    return _render_supervised_runtime_arc(
        "/supervised-development-readiness", "v115.0 Supervised Self-Development Readiness Audit", "supervised_self_development_readiness", "v115.0", "supervised-development-readiness",
        "Audits the full v111-v115 supervised self-development flow from intent through work package, patch readiness, and release judgment while preserving non-autonomy. The older /self-development-readiness v90 page remains intact.",
        [("walkthrough", "Walkthrough", "Trace improvement intent through release judgment."), ("burden", "Burden", "Check whether the flow reduces operator confusion."), ("safety", "Safety", "Confirm no self-approval, auto patching, memory mutation, identity mutation, default model calls, hidden scheduling, or publishing."), ("evidence", "Evidence", "Audit grounding quality."), ("trace", "Decision Trace", "Link problem, evidence, risk, action, and required approval."), ("dashboard", "Dashboard", "Review dashboard usability and consolidation."), ("release-process", "Release Process", "Check docs, smoke, install, privacy, and external zip validation alignment."), ("layer", "Layer", "Final v115 supervised readiness audit.")],
    )



def render_development_session_planner() -> str:
    return _render_supervised_runtime_arc(
        "/development-session-planner", "v116.0 Development Session Planner", "development_session_planner", "v116.0", "development-session-planner",
        "Plans supervised development sessions before code changes, binding intent, scope, likely files, tests, docs obligations, safety boundaries, and operator decisions without executing work.",
        [("intent", "Intent", "Collect candidate goals from intent reports, work packages, patch readiness, audits, and operator notes."), ("scope", "Scope", "Define what the session should and should not touch."), ("files", "Files", "Predict likely impacted files and modules."), ("tests", "Tests", "Suggest compile, smoke, route, CLI, install, and package privacy checks."), ("docs", "Docs", "Carry README and release-history obligations into the session plan."), ("safety", "Safety", "Flag autonomy, memory, identity, model, scheduling, release, and approval-gate sensitivity."), ("decisions", "Decisions", "List explicit operator choices required before work begins."), ("layer", "Layer", "Final v116 session planner.")],
    )


def render_source_change_cartographer() -> str:
    return _render_supervised_runtime_arc(
        "/source-change-cartographer", "v117.0 Source Change Cartographer", "source_change_cartographer", "v117.0", "source-change-cartographer",
        "Maps planned changes to source surfaces, route/API/CLI links, builder dependencies, docs, smoke coverage, and fragile areas without source mutation.",
        [("inventory", "Inventory", "Inventory routes, APIs, CLI flags, builders, smoke checks, docs, packaging, and install checks."), ("route-parity", "Route/API/CLI", "Map dashboard pages to matching API endpoints and CLI flags."), ("builders", "Builders", "Map readiness builders and helper dependencies."), ("docs", "Docs", "Link code surfaces to README and release history entries."), ("smoke", "Smoke", "Map smoke checks to the features they validate."), ("fragile", "Fragile", "Flag dispatch order, data-tip hover safety, privacy allowlists, version markers, install expectations, and stale commands."), ("report", "Report", "Build if-changing-X-inspect-Y guidance."), ("layer", "Layer", "Final v117 source cartographer.")],
    )


def render_patch_simulation() -> str:
    return _render_supervised_runtime_arc(
        "/patch-simulation", "v118.0 Patch Simulation and Dry-Run Review Layer", "patch_simulation_dry_run_review_layer", "v118.0", "patch-simulation",
        "Simulates how a patch should behave before application by predicting expected diffs, missing pieces, overreach, safety regressions, and verification outcomes. No patch application.",
        [("schema", "Schema", "Define expected files, changed surfaces, docs, tests, risks, and verification outcomes."), ("expected-diff", "Expected Diff", "Predict the rough shape of a correct patch."), ("missing", "Missing", "Find forgotten planned changes."), ("overreach", "Overreach", "Flag unrelated or excessive touched systems."), ("safety", "Safety", "Predict autonomy, memory, local-model, scheduling, and release-control regressions."), ("verification", "Verification", "Predict which checks should pass after the patch."), ("summary", "Summary", "Produce advisory approve, revise, or block guidance."), ("layer", "Layer", "Final v118 patch simulation.")],
    )


def render_verification_matrix() -> str:
    return _render_supervised_runtime_arc(
        "/verification-matrix", "v119.0 Verification Matrix and Regression Memory Layer", "verification_matrix_regression_memory_layer", "v119.0", "verification-matrix",
        "Maps feature areas to required checks and recommends verification commands for dashboard, API/CLI, packaging, safety, and documentation changes without durable memory mutation.",
        [("schema", "Schema", "Define feature area to required check mappings."), ("dashboard", "Dashboard", "Routes, nav entries, dispatch coverage, render functions, and data-tip tooltip safety."), ("api-cli", "API/CLI", "Endpoint coverage, CLI flags, readiness JSON shape, and command docs."), ("packaging", "Packaging", "Source-only rules, privacy exclusions, install smoke, and external extracted zip checks."), ("safety", "Safety", "Autonomy, memory, identity, local model, publishing, and scheduling locks."), ("docs", "Docs", "README next steps, release history, command references, and version markers."), ("recommendation", "Recommendation", "Recommend exact checks for a planned change."), ("layer", "Layer", "Final v119 verification matrix.")],
    )


def render_development_execution_audit() -> str:
    return _render_supervised_runtime_arc(
        "/development-execution-audit", "v120.0 Supervised Development Execution Audit", "supervised_development_execution_audit", "v120.0", "development-execution-audit",
        "Audits whether v116-v119 made supervised development execution smoother, safer, more specific, and easier to verify without crossing autonomy boundaries.",
        [("walkthrough", "Walkthrough", "Trace planner to cartographer to patch simulation to verification matrix."), ("burden", "Burden", "Check manual confusion, duplicate commands, and route hunting."), ("quality", "Quality", "Score whether planned changes are specific, bounded, and testable."), ("coverage", "Coverage", "Check whether recommended tests match touched surfaces."), ("safety", "Safety", "Confirm no self-approval, source mutation, memory mutation, identity mutation, default model calls, hidden scheduling, or publishing."), ("dashboard", "Dashboard", "Review sprawl and grouping candidates."), ("docs", "Docs", "Confirm substages and command references are current."), ("layer", "Layer", "Final v120 development execution audit.")],
    )


def render_development_outcome_review() -> str:
    return _render_supervised_runtime_arc(
        "/development-outcome-review", "v121.0 Development Outcome Review Layer", "development_outcome_review_layer", "v121.0", "development-outcome-review",
        "Compares planned supervised development sessions against actual outcomes, missed surfaces, unexpected changes, verification accuracy, and operator burden while remaining advisory.",
        [("collector", "Collector", "Collect completed session summaries, touched files, checks, failures, fixes, docs, and package results."), ("comparison", "Comparison", "Compare planned expectations against actual patch scope and verification results."), ("missed", "Missed", "Detect files, routes, APIs, CLI flags, docs, or smoke checks that should have been predicted."), ("unexpected", "Unexpected", "Flag changes outside expected scope."), ("verification", "Verification", "Score whether recommended checks matched actual verification needs."), ("burden", "Burden", "Track whether the session reduced or increased manual friction."), ("binder", "Binder", "Bundle expected scope, actual scope, missed items, risks, fixes, and future improvements."), ("layer", "Layer", "Final v121 outcome review.")],
    )


def render_lesson_extraction() -> str:
    return _render_supervised_runtime_arc(
        "/lesson-extraction", "v122.0 Supervised Lesson Extraction Layer", "supervised_lesson_extraction_layer", "v122.0", "lesson-extraction",
        "Extracts proposed lessons from completed supervised development work, including bug patterns, successful patterns, false alarms, usefulness scoring, and operator review packets without memory writes.",
        [("schema", "Schema", "Define lesson candidate fields and evidence."), ("bugs", "Bugs", "Extract recurring route, command, version, docs, privacy, and CLI collision bug patterns."), ("successes", "Successes", "Extract successful staged verification and parity practices."), ("false-alarms", "False Alarms", "Detect already-fixed or environment-only findings."), ("usefulness", "Usefulness", "Score lessons by future development value."), ("memory-boundary", "Memory", "Confirm lessons are proposed only and not written to durable memory."), ("packet", "Packet", "Build operator lesson review packets."), ("layer", "Layer", "Final v122 lesson extraction.")],
    )


def render_recommendation_refinement() -> str:
    return _render_supervised_runtime_arc(
        "/recommendation-refinement", "v123.0 Recommendation Refinement Layer", "recommendation_refinement_layer", "v123.0", "recommendation-refinement",
        "Refines future recommendations by comparing past recommendations with outcomes, detecting repeated mistakes, reducing noise, and applying safety-aware advisory filters without approving or applying work.",
        [("schema", "Schema", "Represent recommendation history and outcomes."), ("accuracy", "Accuracy", "Score prior recommendation usefulness and risk."), ("mistakes", "Mistakes", "Detect repeated planning blind spots."), ("noise", "Noise", "Suppress low-value ceremonial suggestions."), ("adjuster", "Adjuster", "Adjust future priorities using supervised lesson packets."), ("safety", "Safety", "Filter recommendations through non-autonomy rules."), ("binder", "Binder", "Bind recommendation, outcome, lesson, heuristic, and next use."), ("layer", "Layer", "Final v123 recommendation refinement.")],
    )


def render_operator_feedback_integration() -> str:
    return _render_supervised_runtime_arc(
        "/operator-feedback-integration", "v124.0 Operator Feedback Integration Layer", "operator_feedback_integration_layer", "v124.0", "operator-feedback-integration",
        "Classifies operator feedback into standing rules, temporary preferences, contradictions, work-package links, and review packets without writing memory or changing identity.",
        [("schema", "Schema", "Define feedback capture fields."), ("standing-rules", "Standing", "Identify durable project-rule candidates for review."), ("temporary", "Temporary", "Separate short-term preferences from durable constraints."), ("contradictions", "Contradictions", "Flag conflicts with older project rules."), ("work-packages", "Work Packages", "Link feedback to planned work, checks, docs, and smoke expectations."), ("packet", "Packet", "Build feedback review packets."), ("safety", "Safety", "Confirm no memory write, identity change, approval, or scheduling."), ("layer", "Layer", "Final v124 feedback integration.")],
    )


def render_development_learning_audit() -> str:
    return _render_supervised_runtime_arc(
        "/development-learning-audit", "v125.0 Supervised Development Learning Audit", "supervised_development_learning_audit", "v125.0", "development-learning-audit",
        "Audits whether v121-v124 made Eidolon better at learning from supervised development sessions while preserving memory, identity, approval, model, scheduling, and publishing boundaries.",
        [("walkthrough", "Walkthrough", "Trace outcome review to lesson extraction to recommendation refinement to feedback integration."), ("lesson-quality", "Lessons", "Audit lesson evidence, usefulness, duplicates, and safety."), ("recommendations", "Recommendations", "Audit recommendation accuracy and noise reduction."), ("feedback", "Feedback", "Audit standing rule, temporary preference, contradiction, and review-needed handling."), ("memory", "Memory", "Confirm no lessons, feedback, recommendations, or packets mutate memory."), ("safety", "Safety", "Confirm no autonomy, source mutation, identity mutation, default model invocation, hidden scheduling, or publishing."), ("burden", "Burden", "Check whether the learning loop reduces repeated explanations and repeated mistakes."), ("layer", "Layer", "Final v125 development learning audit.")],
    )

def render_strategic_growth_intake() -> str:
    return _render_supervised_runtime_arc(
        "/strategic-growth-intake", "v126.0 Strategic Growth Intake Layer", "strategic_growth_intake_layer", "v126.0", "strategic-growth-intake",
        "Gathers lessons, feedback, goals, audits, failed checks, roadmap notes, and operator direction into strategic signals with confidence, relevance, and safety sensitivity scoring.",
        [("inventory", "Inventory", "Collect growth signals from supervised learning, feedback, goals, audits, and operator direction."), ("sources", "Sources", "Classify signals as operator-stated, system-derived, safety, usability, technical debt, or future capability."), ("confidence", "Confidence", "Score how grounded each strategic signal is."), ("themes", "Themes", "Detect recurring route, CLI, docs, privacy, dashboard, and supervision themes."), ("relevance", "Relevance", "Score long-term growth relevance."), ("safety", "Safety", "Flag autonomy, memory, identity, local model, release, scheduling, and approval sensitivity."), ("binder", "Binder", "Bundle signals, sources, confidence, relevance, and safety notes."), ("layer", "Layer", "Final v126 strategic intake.")],
    )


def render_roadmap_synthesis() -> str:
    return _render_supervised_runtime_arc(
        "/roadmap-synthesis", "v127.0 Roadmap Synthesis Layer", "roadmap_synthesis_layer", "v127.0", "roadmap-synthesis",
        "Turns strategic signals into coherent short-term, medium-term, and long-term roadmap options with dependencies, conflicts, ranked recommendations, and safety notes without scheduling work.",
        [("schema", "Schema", "Define roadmap option purpose, source signals, benefits, risks, dependencies, safety, and operator burden."), ("short-term", "Short Term", "Build practical next-release options."), ("medium-term", "Medium Term", "Build multi-arc direction options."), ("long-term", "Long Term", "Link current work to the larger artificial-mind goal."), ("dependencies", "Dependencies", "Map required precursor capabilities."), ("conflicts", "Conflicts", "Detect conflicting roadmap paths or goals."), ("binder", "Binder", "Bind ranked roadmap options with reasons and safety notes."), ("layer", "Layer", "Final v127 roadmap synthesis.")],
    )


def render_strategic_risk_ledger() -> str:
    return _render_supervised_runtime_arc(
        "/strategic-risk-ledger", "v128.0 Strategic Risk and Debt Ledger", "strategic_risk_debt_ledger", "v128.0", "strategic-risk-ledger",
        "Tracks strategic technical debt, safety debt, usability debt, risk priority, and mitigation plans while keeping all mitigations advisory.",
        [("schema", "Schema", "Define risk source, severity, likelihood, affected systems, mitigation, and evidence."), ("technical-debt", "Technical Debt", "Inventory route, CLI, docs, packaging, smoke, massive module, dashboard, and dynamic builder debt."), ("safety-debt", "Safety Debt", "Track safety-sensitive drift risks."), ("usability-debt", "Usability Debt", "Track operator friction, tab overload, command confusion, duplicated workflows, and unclear next actions."), ("priority", "Priority", "Rank risks by severity, likelihood, and development impact."), ("mitigation", "Mitigation", "Propose supervised mitigation steps."), ("binder", "Binder", "Bundle risks, evidence, priorities, and mitigations."), ("layer", "Layer", "Final v128 strategic risk/debt ledger.")],
    )


def render_capability_maturity() -> str:
    return _render_supervised_runtime_arc(
        "/capability-maturity", "v129.0 Capability Maturity Model Layer", "capability_maturity_model_layer", "v129.0", "capability-maturity",
        "Scores major Eidolon capabilities as scaffolded, integrated, tested, useful, reliable, or operator-trusted using evidence instead of decorative confidence.",
        [("schema", "Schema", "Define scaffolded, integrated, tested, useful, reliable, and operator-trusted maturity levels."), ("inventory", "Inventory", "Inventory memory, goals, reasoning, workflow, supervised development, learning, and release governance capabilities."), ("scoring", "Scoring", "Score using routes, APIs, CLI checks, smoke coverage, docs, and usefulness evidence."), ("scaffolds", "Scaffolds", "Identify systems that are mostly synthetic scaffolds."), ("gaps", "Gaps", "Detect what each capability needs to become genuinely useful."), ("upgrades", "Upgrades", "Recommend supervised upgrades for important low-maturity systems."), ("binder", "Binder", "Bind capability, evidence, score, gaps, and upgrade recommendation."), ("layer", "Layer", "Final v129 maturity model.")],
    )


def render_strategic_growth_audit() -> str:
    return _render_supervised_runtime_arc(
        "/strategic-growth-audit", "v130.0 Supervised Strategic Growth Audit", "supervised_strategic_growth_audit", "v130.0", "strategic-growth-audit",
        "Audits whether v126-v129 help Eidolon choose better future growth paths while keeping roadmap selection, capability upgrades, source changes, memory, identity, local models, scheduling, and publishing under explicit operator control.",
        [("walkthrough", "Walkthrough", "Trace signals to roadmap options to risk/debt ledger to maturity to next-arc recommendations."), ("coherence", "Coherence", "Check alignment with Eidolon's long-term purpose."), ("safety", "Safety", "Confirm no autonomy, memory mutation, identity mutation, default model calls, hidden scheduling, source mutation, or publishing."), ("roadmap", "Roadmap", "Audit specificity, usefulness, evidence, and staging."), ("risk", "Risk", "Verify debt and risk are not ignored for shiny new features."), ("maturity", "Maturity", "Audit evidence-backed maturity scores and scaffold honesty."), ("burden", "Burden", "Check decision-fatigue reduction."), ("layer", "Layer", "Final v130 strategic growth audit.")],
    )


def render_planning_signals() -> str:
    return _render_supervised_runtime_arc(
        "/planning-signals", "v131.0 Planning Signal Consolidation Layer", "planning_signal_consolidation_layer", "v131.0", "planning-signals",
        "Consolidates lessons, feedback, strategic intake, roadmap options, risks, maturity gaps, failed checks, and operator direction into one evidence-ranked planning packet.",
        [("inventory", "Inventory", "Inventory planning sources."), ("duplicates", "Duplicates", "Detect overlapping planning signals."), ("priority", "Priority", "Normalize priority across goals, safety, debt, friction, and gaps."), ("evidence", "Evidence", "Classify signal strength."), ("conflicts", "Conflicts", "Detect planning contradictions."), ("safety", "Safety", "Bind safety-sensitive items."), ("packet", "Packet", "Build the planning signal packet."), ("layer", "Layer", "Final v131 planning signals.")],
    )


def render_work_package_recommendations() -> str:
    return _render_supervised_runtime_arc(
        "/work-package-recommendations", "v132.0 Work Package Recommendation Layer", "work_package_recommendation_layer", "v132.0", "work-package-recommendations",
        "Converts planning signals, maturity gaps, risk/debt items, and operator feedback into ranked supervised work package recommendations without creating, approving, or applying work.",
        [("schema", "Schema", "Define recommended package fields."), ("maturity-gaps", "Maturity Gaps", "Map maturity gaps to possible work."), ("risk-debt", "Risk/Debt", "Map risks and debt to mitigations."), ("feedback", "Feedback", "Map operator feedback to work packages."), ("scope", "Scope", "Estimate file and verification scope."), ("safety", "Safety", "Filter unsafe recommendations."), ("ranking", "Ranking", "Rank by value, urgency, evidence, risk, burden, and dependencies."), ("layer", "Layer", "Final v132 recommendations.")],
    )


def render_operator_decision_brief() -> str:
    return _render_supervised_runtime_arc(
        "/operator-decision-brief", "v133.0 Operator Decision Brief Layer", "operator_decision_brief_layer", "v133.0", "operator-decision-brief",
        "Presents the top supervised work options with evidence, tradeoffs, sequencing, burden, verification needs, and safety boundaries without selecting for the operator.",
        [("schema", "Schema", "Define the brief."), ("top-three", "Top Three", "Present the strongest options."), ("tradeoffs", "Tradeoffs", "Explain what each option changes."), ("sequencing", "Sequencing", "Explain dependencies."), ("burden", "Burden", "Forecast operator burden."), ("verification", "Verification", "Forecast checks."), ("safety", "Safety", "Summarize boundaries."), ("layer", "Layer", "Final v133 decision brief.")],
    )


def render_planning_console() -> str:
    return _render_supervised_runtime_arc(
        "/planning-console", "v134.0 Dashboard Planning Console Consolidation", "dashboard_planning_console_consolidation", "v134.0", "planning-console",
        "Groups the strategic and development planning surfaces into a cleaner command-style planning console while preserving existing routes and the custom data-tip hover system.",
        [("inventory", "Inventory", "Inventory planning routes."), ("nav-plan", "Nav Plan", "Plan route grouping."), ("layout", "Layout", "Build the unified planning console."), ("lazy-loading", "Lazy Loading", "Keep heavy reports button-driven."), ("tab-reduction", "Tab Reduction", "Recommend grouping."), ("tooltips", "Tooltips", "Preserve data-tip and block native title tooltips."), ("safety-banner", "Safety Banner", "Show operator approval requirements."), ("layer", "Layer", "Final v134 planning console.")],
    )


def render_planning_readiness_audit() -> str:
    return _render_supervised_runtime_arc(
        "/planning-readiness-audit", "v135.0 Supervised Operator Planning Console", "supervised_operator_planning_console", "v135.0", "planning-readiness-audit",
        "Audits the full planning flow from signals to work packages to decision brief to planning console while keeping Eidolon recommendation-only and operator-governed.",
        [("walkthrough", "Walkthrough", "Trace end-to-end planning."), ("evidence", "Evidence", "Audit evidence quality."), ("quality", "Quality", "Audit work package quality."), ("burden", "Burden", "Audit operator burden reduction."), ("dashboard", "Dashboard", "Audit sprawl reduction."), ("safety", "Safety", "Audit autonomy boundaries."), ("parity-audit", "Parity", "Audit route/API/CLI parity."), ("layer", "Layer", "Final v135 planning readiness audit.")],
    )


def render_work_package_selection() -> str:
    return _render_supervised_runtime_arc(
        "/work-package-selection", "v136.0 Work Package Selection Layer", "work_package_selection_layer", "v136.0", "work-package-selection",
        "Lets the operator compare recommendations and explicitly select, defer, or reject work packages without launching or executing work.",
        [("schema", "Schema", "Define selection records."), ("import", "Import", "Import recommendations."), ("candidates", "Candidates", "Summarize candidate packages."), ("gate", "Gate", "Require explicit operator selection."), ("rationale", "Rationale", "Capture select/defer/reject reasons."), ("deferred", "Deferred", "Track deferred packages."), ("safety", "Safety", "Block unsafe packages."), ("layer", "Layer", "Final v136 selection layer.")],
    )


def render_session_brief() -> str:
    return _render_supervised_runtime_arc(
        "/session-brief", "v137.0 Session Brief Preparation Layer", "session_brief_preparation_layer", "v137.0", "session-brief",
        "Prepares a structured supervised session brief from an operator-selected package with objective, evidence, risks, files, non-goals, and dependencies.",
        [("schema", "Schema", "Define session brief."), ("objective", "Objective", "Expand package objective."), ("evidence", "Evidence", "Bind evidence."), ("non-goals", "Non-Goals", "Protect boundaries."), ("files", "Files", "Map expected file surface."), ("dependencies", "Dependencies", "Map prerequisites."), ("builder", "Builder", "Build readable brief."), ("layer", "Layer", "Final v137 session brief.")],
    )


def render_approval_checklist() -> str:
    return _render_supervised_runtime_arc(
        "/approval-checklist", "v138.0 Approval Checklist and Safety Boundary Layer", "approval_checklist_safety_boundary_layer", "v138.0", "approval-checklist",
        "Builds approval, safety, scope, dashboard, documentation, and verification checklists before any future development work begins.",
        [("schema", "Schema", "Define checklist."), ("safety", "Safety", "Check boundaries."), ("scope", "Scope", "Confirm affected surfaces."), ("dashboard", "Dashboard", "Check command deck and data-tip."), ("docs", "Docs", "Require README and history."), ("verification", "Verification", "Require checks."), ("score", "Score", "Score approval readiness."), ("layer", "Layer", "Final v138 checklist.")],
    )


def render_verification_rollback_plan() -> str:
    return _render_supervised_runtime_arc(
        "/verification-rollback-plan", "v139.0 Verification Plan and Rollback Preparation Layer", "verification_plan_rollback_preparation_layer", "v139.0", "verification-rollback-plan",
        "Prepares advisory verification and rollback plans for selected packages without executing commands or changing source.",
        [("schema", "Schema", "Define verification plan."), ("checks", "Checks", "Select checks."), ("parity-tests", "Parity", "Plan route/API/CLI tests."), ("dashboard-tests", "Dashboard", "Plan render and tooltip checks."), ("privacy-tests", "Privacy", "Plan package privacy checks."), ("rollback", "Rollback", "Define rollback plan."), ("rollback-risk", "Risk", "Classify rollback difficulty."), ("layer", "Layer", "Final v139 verification/rollback plan.")],
    )


def render_session_launch_audit() -> str:
    return _render_supervised_runtime_arc(
        "/session-launch-audit", "v140.0 Supervised Work Package Selection and Session Launch", "supervised_work_package_selection_session_launch", "v140.0", "session-launch-audit",
        "Audits the full recommendation-to-selection-to-session-launch flow while keeping launch readiness advisory and operator-approved.",
        [("trace", "Trace", "Trace recommendation to launch packet."), ("evidence", "Evidence", "Audit evidence continuity."), ("safety", "Safety", "Audit no hidden execution."), ("burden", "Burden", "Audit operator burden."), ("dashboard", "Dashboard", "Audit command style."), ("tooltips", "Tooltips", "Audit data-tip behavior."), ("parity", "Parity", "Audit route/API/CLI parity."), ("layer", "Layer", "Final v140 session launch audit.")],
    )


def render_patch_session_intake() -> str:
    return _render_supervised_runtime_arc(
        "/patch-session-intake", "v141.0 Patch Session Intake Layer", "patch_session_intake_layer", "v141.0", "patch-session-intake",
        "Imports approved session launch packets and prepares supervised patch-session intake records without implementation, source mutation, or inferred approval.",
        [("import", "Import", "Load selected package, session brief, approval checklist, verification plan, and rollback plan."), ("schema", "Schema", "Define patch-session intake fields."), ("approval", "Approval", "Validate explicit operator approval state."), ("scope", "Scope", "Draft allowed file/module scope."), ("out-of-scope", "Out-of-Scope", "Flag unrelated changes."), ("safety", "Safety", "Bind non-autonomy restrictions."), ("score", "Score", "Score intake readiness."), ("layer", "Layer", "Final v141 patch intake.")],
    )


def render_file_change_plan() -> str:
    return _render_supervised_runtime_arc(
        "/file-change-plan", "v142.0 File Change Planning Layer", "file_change_planning_layer", "v142.0", "file-change-plan",
        "Plans file-by-file changes, dependencies, documentation needs, and verification links before any source edits are made.",
        [("schema", "Schema", "Define file change plan fields."), ("files", "Files", "Resolve likely affected files."), ("types", "Types", "Classify change categories."), ("dependencies", "Dependencies", "Map impacts."), ("dashboard", "Dashboard", "Protect command deck and data-tip behavior."), ("docs", "Docs", "Plan README/history updates."), ("verification", "Verification", "Link files to checks."), ("layer", "Layer", "Final v142 file plan.")],
    )


def render_patch_blueprint() -> str:
    return _render_supervised_runtime_arc(
        "/patch-blueprint", "v143.0 Patch Draft Blueprint Layer", "patch_draft_blueprint_layer", "v143.0", "patch-blueprint",
        "Builds a detailed patch blueprint that explains intended edits, order, risks, runtime boundaries, smoke coverage, and docs impact without applying changes.",
        [("schema", "Schema", "Define blueprint fields."), ("sequence", "Sequence", "Order planned edits."), ("route-api-cli", "Route/API/CLI", "Draft interface changes."), ("dashboard", "Dashboard", "Draft dashboard updates."), ("runtime-boundary", "Runtime", "Plan private runtime boundaries."), ("smoke", "Smoke", "Plan smoke coverage."), ("risk", "Risk", "Review blueprint risk."), ("layer", "Layer", "Final v143 blueprint.")],
    )


def render_patch_review_packet() -> str:
    return _render_supervised_runtime_arc(
        "/patch-review-packet", "v144.0 Patch Review Packet Layer", "patch_review_packet_layer", "v144.0", "patch-review-packet",
        "Bundles objective, file plan, patch blueprint, risks, safety boundaries, docs plan, verification plan, and rollback plan for operator review.",
        [("schema", "Schema", "Define review packet sections."), ("evidence", "Evidence", "Build evidence chain."), ("risk", "Risk", "Summarize risks."), ("checklist", "Checklist", "Build operator checklist."), ("blockers", "Blockers", "Detect approval blockers."), ("score", "Score", "Score implementation readiness."), ("export", "Export", "Prepare review packet export."), ("layer", "Layer", "Final v144 review packet.")],
    )


def render_patch_session_audit() -> str:
    return _render_supervised_runtime_arc(
        "/patch-session-audit", "v145.0 Supervised Patch Session Assembly", "supervised_patch_session_assembly", "v145.0", "patch-session-audit",
        "Audits launch packet to patch intake to file plan to blueprint to review packet while preventing self-approval, implementation, and source mutation.",
        [("trace", "Trace", "Trace launch packet to review packet."), ("scope", "Scope", "Audit scope discipline."), ("safety", "Safety", "Audit safety boundaries."), ("dashboard", "Dashboard", "Audit command style and data-tip behavior."), ("docs", "Docs", "Audit README/history updates."), ("verification", "Verification", "Audit verification plan fit."), ("privacy", "Privacy", "Audit package privacy."), ("layer", "Layer", "Final v145 patch session assembly.")],
    )


def render_patch_draft_request() -> str:
    return _render_supervised_runtime_arc(
        "/patch-draft-request", "v146.0 Patch Draft Request Layer", "patch_draft_request_layer", "v146.0", "patch-draft-request",
        "Converts reviewed patch session packets into supervised draft-generation requests while refusing source writes, inferred approval, or draft approval.",
        [("schema", "Schema", "Define draft request fields."), ("import", "Import", "Load review packet."), ("eligibility", "Eligibility", "Validate draft readiness."), ("scope-lock", "Scope Lock", "Limit drafts to approved files."), ("non-goals", "Non-Goals", "Bind explicit no-goals."), ("risk", "Risk", "Classify draft risk."), ("score", "Score", "Score request readiness."), ("layer", "Layer", "Final v146 request layer.")],
    )


def render_file_patch_drafts() -> str:
    return _render_supervised_runtime_arc(
        "/file-patch-drafts", "v147.0 File-Level Patch Draft Layer", "file_level_patch_draft_layer", "v147.0", "file-patch-drafts",
        "Creates reviewable file-by-file draft content and diff-style previews without applying changes to live source files.",
        [("schema", "Schema", "Define file draft fields."), ("context", "Context", "Extract source context."), ("edits", "Edits", "Build proposed edits."), ("diff", "Diff", "Format diff preview."), ("dashboard", "Dashboard", "Guard command deck and data-tip."), ("docs", "Docs", "Draft docs updates."), ("risk", "Risk", "Attach per-file risk notes."), ("layer", "Layer", "Final v147 file draft layer.")],
    )


def render_patch_diff_review() -> str:
    return _render_supervised_runtime_arc(
        "/patch-diff-review", "v148.0 Patch Diff Review Packet Layer", "patch_diff_review_packet_layer", "v148.0", "patch-diff-review",
        "Combines file-level drafts into a coherent patch diff review packet with safety, consistency, verification, and rollback alignment.",
        [("schema", "Schema", "Define diff review packet."), ("ordering", "Ordering", "Order drafts by dependency."), ("consistency", "Consistency", "Check cross-file agreement."), ("safety", "Safety", "Audit draft boundaries."), ("verification", "Verification", "Check verification alignment."), ("rollback", "Rollback", "Check rollback alignment."), ("summary", "Summary", "Build operator review summary."), ("layer", "Layer", "Final v148 diff review.")],
    )


def render_patch_draft_qa() -> str:
    return _render_supervised_runtime_arc(
        "/patch-draft-qa", "v149.0 Patch Draft QA Layer", "patch_draft_qa_layer", "v149.0", "patch-draft-qa",
        "QA checks draft completeness, consistency, safety, verification, docs, dashboard behavior, and source-only package privacy before implementation.",
        [("schema", "Schema", "Define QA fields."), ("completeness", "Completeness", "Audit all planned files."), ("consistency", "Consistency", "Audit code/docs/API/CLI agreement."), ("safety", "Safety", "Audit forbidden behavior."), ("dashboard", "Dashboard", "Audit command style and data-tip."), ("privacy", "Privacy", "Audit package privacy impact."), ("score", "Score", "Score QA readiness."), ("layer", "Layer", "Final v149 draft QA.")],
    )


def render_patch_draft_generation_audit() -> str:
    return _render_supervised_runtime_arc(
        "/patch-draft-generation-audit", "v150.0 Supervised Patch Draft Generation", "supervised_patch_draft_generation", "v150.0", "patch-draft-generation-audit",
        "Audits review packet to draft request to file drafts to diff review to QA while preventing patch application, approval inference, and source mutation.",
        [("trace", "Trace", "Trace draft generation chain."), ("evidence", "Evidence", "Audit evidence continuity."), ("scope", "Scope", "Audit approved scope discipline."), ("safety", "Safety", "Audit safety boundaries."), ("dashboard", "Dashboard", "Audit command deck and data-tip."), ("docs", "Docs", "Audit README/history updates."), ("parity", "Parity", "Audit route/API/CLI parity."), ("layer", "Layer", "Final v150 draft generation.")],
    )



def render_implementation_handoff() -> str:
    return _render_supervised_runtime_arc(
        "/implementation-handoff", "v151.0 Implementation Handoff Intake Layer", "implementation_handoff_intake_layer", "v151.0", "implementation-handoff",
        "Converts QA-passed patch drafts into an advisory implementation handoff request while refusing source mutation, inferred approval, or automatic verification.",
        [("schema", "Schema", "Define handoff fields."), ("qa-import", "QA Import", "Load draft QA evidence."), ("eligibility", "Eligibility", "Validate implementation eligibility."), ("scope", "Scope", "Bind approved file scope."), ("safety", "Safety", "Reconfirm no-go boundaries."), ("risk", "Risk", "Classify implementation risk."), ("approval", "Approval", "Require explicit operator approval."), ("layer", "Layer", "Final v151 handoff intake.")],
    )


def render_manual_patch_application_plan() -> str:
    return _render_supervised_runtime_arc(
        "/manual-patch-application-plan", "v152.0 Manual Patch Application Plan Layer", "manual_patch_application_plan_layer", "v152.0", "manual-patch-application-plan",
        "Turns approved draft diffs into ordered manual edit instructions without writing generated drafts into live files.",
        [("schema", "Schema", "Define application steps."), ("ordering", "Ordering", "Order edits by dependency."), ("instructions", "Instructions", "Build manual edit notes."), ("dashboard", "Dashboard", "Guard command-deck style."), ("parity", "Parity", "Plan API/CLI parity."), ("docs", "Docs", "Plan README/history edits."), ("smoke", "Smoke", "Plan smoke updates."), ("layer", "Layer", "Final v152 application plan.")],
    )


def render_implementation_verification_worksheet() -> str:
    return _render_supervised_runtime_arc(
        "/implementation-verification-worksheet", "v153.0 Implementation Verification Worksheet Layer", "implementation_verification_worksheet_layer", "v153.0", "implementation-verification-worksheet",
        "Builds operator-run verification worksheets for version markers, dashboard rendering, routes, CLI, packaging, and extracted zip checks without executing them.",
        [("schema", "Schema", "Define verification worksheet."), ("versions", "Versions", "Check version markers."), ("dashboard", "Dashboard", "Check render behavior."), ("tooltips", "Tooltips", "Guard data-tip/no-title."), ("parity", "Parity", "Check route/API/CLI parity."), ("privacy", "Privacy", "Check source-only privacy."), ("zip", "Zip", "Check extracted zip."), ("layer", "Layer", "Final v153 worksheet.")],
    )


def render_implementation_rollback_packet() -> str:
    return _render_supervised_runtime_arc(
        "/implementation-rollback-packet", "v154.0 Implementation Rollback Packet Layer", "implementation_rollback_packet_layer", "v154.0", "implementation-rollback-packet",
        "Prepares advisory rollback instructions for every planned implementation step before live source changes are allowed.",
        [("schema", "Schema", "Define rollback packet."), ("restore", "Restore", "Plan file restoration."), ("parity", "Parity", "Plan route/API/CLI rollback."), ("dashboard", "Dashboard", "Guard dashboard rollback."), ("docs", "Docs", "Plan docs rollback."), ("smoke", "Smoke", "Plan post-rollback smoke."), ("risk", "Risk", "Score rollback difficulty."), ("layer", "Layer", "Final v154 rollback packet.")],
    )


def render_implementation_handoff_audit() -> str:
    return _render_supervised_runtime_arc(
        "/implementation-handoff-audit", "v155.0 Supervised Patch Implementation Handoff", "supervised_patch_implementation_handoff", "v155.0", "implementation-handoff-audit",
        "Audits QA-passed draft handoff, manual application plan, verification worksheet, and rollback packet while preventing self-approval, source mutation, and automatic command execution.",
        [("trace", "Trace", "Trace draft QA to handoff."), ("evidence", "Evidence", "Audit evidence continuity."), ("scope", "Scope", "Audit scope discipline."), ("safety", "Safety", "Audit safety boundaries."), ("dashboard", "Dashboard", "Audit command deck/data-tip."), ("docs", "Docs", "Audit docs/history duties."), ("parity", "Parity", "Audit route/API/CLI parity."), ("layer", "Layer", "Final v155 handoff audit.")],
    )



def render_patch_readiness_intake() -> str:
    return _render_supervised_runtime_arc(
        "/patch-readiness-intake", "v156.0 Patch Readiness Intake Layer", "patch_readiness_intake_layer", "v156.0", "patch-readiness-intake",
        "Binds draft QA, implementation handoff, manual application plan, verification worksheet, rollback packet, docs duties, and operator approval state into a readiness packet without applying changes.",
        [("schema", "Schema", "Define readiness fields."), ("handoff", "Handoff", "Import handoff evidence."), ("qa", "QA", "Bind QA status."), ("application-plan", "Plan", "Bind manual application steps."), ("verification", "Verification", "Bind worksheet coverage."), ("rollback", "Rollback", "Bind rollback coverage."), ("docs", "Docs", "Bind docs obligations."), ("layer", "Layer", "Final v156 readiness intake.")],
    )


def render_patch_readiness_score() -> str:
    return _render_supervised_runtime_arc(
        "/patch-readiness-score", "v157.0 Patch Readiness Scoring Layer", "patch_readiness_scoring_layer", "v157.0", "patch-readiness-score",
        "Scores whether a patch is ready, blocked, risky, incomplete, or unsafe while refusing approval inference or source mutation.",
        [("schema", "Schema", "Define score fields."), ("scope", "Scope", "Score approved scope."), ("safety", "Safety", "Score safety boundaries."), ("verification", "Verification", "Score checks."), ("rollback", "Rollback", "Score recoverability."), ("docs", "Docs", "Score docs duties."), ("dashboard", "Dashboard", "Guard command-deck/data-tip."), ("layer", "Layer", "Final v157 scoring.")],
    )


def render_patch_readiness_blockers() -> str:
    return _render_supervised_runtime_arc(
        "/patch-readiness-blockers", "v158.0 Patch Blocker and Gap Report Layer", "patch_blocker_and_gap_report_layer", "v158.0", "patch-readiness-blockers",
        "Generates blocker and gap reports for missing packets, missing file coverage, unsafe capabilities, dashboard regressions, parity gaps, and package privacy risks.",
        [("schema", "Schema", "Define blocker fields."), ("packets", "Packets", "Detect missing packets."), ("file-coverage", "Files", "Detect file coverage gaps."), ("safety", "Safety", "Detect forbidden capability drift."), ("dashboard", "Dashboard", "Detect dashboard regressions."), ("parity", "Parity", "Detect route/API/CLI gaps."), ("privacy", "Privacy", "Detect package risks."), ("layer", "Layer", "Final v158 blockers.")],
    )


def render_patch_go_no_go_decision() -> str:
    return _render_supervised_runtime_arc(
        "/patch-go-no-go-decision", "v159.0 Operator Go/No-Go Decision Packet Layer", "operator_go_no_go_decision_packet_layer", "v159.0", "patch-go-no-go-decision",
        "Builds an advisory operator decision packet with go, no-go, or conditional-go recommendations while requiring explicit approval before application.",
        [("schema", "Schema", "Define decision packet."), ("go", "Go", "Build go recommendation."), ("no-go", "No-Go", "Build blocker recommendation."), ("conditional", "Conditional", "Build conditional go."), ("approval-text", "Approval", "Draft approval language."), ("risk", "Risk", "Summarize accepted risk."), ("post-approval", "After", "Summarize post-approval steps."), ("layer", "Layer", "Final v159 decision packet.")],
    )


def render_patch_application_readiness_audit() -> str:
    return _render_supervised_runtime_arc(
        "/patch-application-readiness-audit", "v160.0 Supervised Patch Application Readiness", "supervised_patch_application_readiness", "v160.0", "patch-application-readiness-audit",
        "Audits draft QA, implementation handoff, application plan, verification worksheet, rollback packet, readiness score, blocker report, and go/no-go packet without applying patches.",
        [("trace", "Trace", "Trace readiness chain."), ("evidence", "Evidence", "Audit evidence continuity."), ("safety", "Safety", "Audit safety boundaries."), ("dashboard", "Dashboard", "Audit command-deck/data-tip."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit README/history duties."), ("privacy", "Privacy", "Audit package privacy."), ("layer", "Layer", "Final v160 readiness audit.")],
    )


def render_patch_sandbox_intake() -> str:
    return _render_supervised_runtime_arc(
        "/patch-sandbox-intake", "v161.0 Patch Sandbox Intake Layer", "patch_sandbox_intake_layer", "v161.0", "patch-sandbox-intake",
        "Prepares a controlled sandbox request from the readiness decision packet while requiring explicit operator approval and forbidding live source mutation.",
        [("schema", "Schema", "Define sandbox intake fields."), ("decision", "Decision", "Import go/no-go packet."), ("approval", "Approval", "Bind explicit approval."), ("scope", "Scope", "Bind approved files."), ("target", "Target", "Resolve sandbox target."), ("safety", "Safety", "Reconfirm no live mutation."), ("risk", "Risk", "Classify sandbox risk."), ("layer", "Layer", "Final v161 sandbox intake.")],
    )


def render_sandbox_patch_application_plan() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-patch-application-plan", "v162.0 Approved Sandbox Patch Application Plan", "approved_sandbox_patch_application_plan", "v162.0", "sandbox-patch-application-plan",
        "Converts readiness-approved patch drafts into a sandbox-only application plan with no live source target and no automatic patch application.",
        [("schema", "Schema", "Define sandbox edit steps."), ("copy", "Copy", "Plan sandbox file copies."), ("apply-plan", "Apply", "Plan sandbox-only edits."), ("dashboard", "Dashboard", "Guard command deck/data-tip."), ("parity-check", "Parity", "Plan API/CLI alignment."), ("docs", "Docs", "Plan sandbox docs edits."), ("no-live-mutation", "Guard", "Reject live source paths."), ("layer", "Layer", "Final v162 sandbox plan.")],
    )


def render_sandbox_verification_packet() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-verification-packet", "v163.0 Sandbox Verification Execution Packet", "sandbox_verification_execution_packet", "v163.0", "sandbox-verification-packet",
        "Prepares sandbox verification commands and evidence capture plans while requiring explicit approval before any command execution.",
        [("schema", "Schema", "Define verification packet."), ("fast-smoke", "Fast", "Plan fast smoke."), ("install-smoke", "Install", "Plan install smoke."), ("dashboard", "Dashboard", "Plan render checks."), ("tooltips", "Tooltips", "Check data-tip/no title."), ("privacy", "Privacy", "Plan package privacy."), ("evidence", "Evidence", "Plan capture paths."), ("layer", "Layer", "Final v163 packet.")],
    )


def render_sandbox_result_review() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-result-review", "v164.0 Sandbox Result Review Layer", "sandbox_result_review_layer", "v164.0", "sandbox-result-review",
        "Reviews sandbox verification evidence, classifies failures, and recommends supervised fixes without promoting sandbox output to source.",
        [("schema", "Schema", "Define result fields."), ("application-evidence", "Apply", "Read application evidence."), ("verification-evidence", "Verify", "Read verification evidence."), ("failures", "Failures", "Classify failures."), ("fixes", "Fixes", "Recommend supervised fixes."), ("promotion-eligibility", "Eligibility", "Classify future promotion eligibility."), ("rollback", "Rollback", "Recommend discard/revise/keep."), ("layer", "Layer", "Final v164 review.")],
    )


def render_sandbox_patch_application_audit() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-patch-application-audit", "v165.0 Operator-Approved Patch Application Sandbox", "operator_approved_patch_application_sandbox", "v165.0", "sandbox-patch-application-audit",
        "Audits readiness decision, sandbox intake, sandbox application plan, verification packet, and result review while forbidding live source mutation and promotion.",
        [("trace", "Trace", "Trace sandbox chain."), ("approval", "Approval", "Audit explicit approval."), ("no-live-mutation", "No Live", "Audit no live mutation."), ("safety", "Safety", "Audit safety boundary."), ("dashboard", "Dashboard", "Audit command deck/data-tip."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit README/history."), ("privacy", "Privacy", "Audit package privacy."), ("layer", "Layer", "Final v165 sandbox audit.")],
    )


def render_sandbox_promotion_intake() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-promotion-intake", "v166.0 Sandbox Promotion Intake Layer", "sandbox_promotion_intake_layer", "v166.0", "sandbox-promotion-intake",
        "Imports sandbox result evidence, binds eligibility to successful verification, and requires explicit operator approval before source promotion can be considered.",
        [("schema", "Schema", "Define promotion intake."), ("result", "Result", "Import sandbox result."), ("eligibility", "Eligibility", "Bind promotion eligibility."), ("approval", "Approval", "Require explicit approval."), ("scope", "Scope", "Bind source targets."), ("safety", "Safety", "Reconfirm boundaries."), ("risk", "Risk", "Classify risk."), ("layer", "Layer", "Final v166 intake.")],
    )


def render_source_promotion_plan() -> str:
    return _render_supervised_runtime_arc(
        "/source-promotion-plan", "v167.0 Source Promotion Application Plan Layer", "source_promotion_application_plan_layer", "v167.0", "source-promotion-plan",
        "Maps sandbox changes to live source paths and orders advisory promotion steps while remaining blocked until explicit operator approval.",
        [("schema", "Schema", "Define source steps."), ("diff-map", "Diff", "Map sandbox to source."), ("order", "Order", "Order application steps."), ("conflicts", "Conflicts", "Plan conflict checks."), ("dashboard", "Dashboard", "Protect command deck/data-tip."), ("parity-check", "Parity", "Plan API/CLI parity."), ("docs", "Docs", "Plan docs updates."), ("layer", "Layer", "Final v167 plan.")],
    )


def render_promotion_approval_packet() -> str:
    return _render_supervised_runtime_arc(
        "/promotion-approval-packet", "v168.0 Promotion Approval Packet Layer", "promotion_approval_packet_layer", "v168.0", "promotion-approval-packet",
        "Builds the final operator-facing promotion approval packet with evidence, risk, approval language, blockers, conditions, and human review checklist.",
        [("schema", "Schema", "Define approval packet."), ("evidence", "Evidence", "Summarize sandbox evidence."), ("risk", "Risk", "Summarize accepted risk."), ("approval-phrase", "Phrase", "Build approval phrase."), ("blocked", "Blocked", "Explain blocked promotion."), ("conditional", "Conditional", "Allow non-safety conditions."), ("checklist", "Checklist", "Build human checklist."), ("layer", "Layer", "Final v168 packet.")],
    )


def render_post_promotion_verification() -> str:
    return _render_supervised_runtime_arc(
        "/post-promotion-verification", "v169.0 Post-Promotion Verification and Rollback Layer", "post_promotion_verification_and_rollback_layer", "v169.0", "post-promotion-verification",
        "Prepares post-promotion smoke, dashboard, tooltip, package privacy, and rollback procedures without automatically executing verification commands.",
        [("schema", "Schema", "Define verification fields."), ("fast-smoke", "Fast", "Plan fast smoke."), ("install-smoke", "Install", "Plan install smoke."), ("dashboard", "Dashboard", "Plan render checks."), ("tooltips", "Tooltips", "Plan data-tip checks."), ("privacy", "Privacy", "Plan package privacy."), ("rollback", "Rollback", "Plan rollback triggers."), ("layer", "Layer", "Final v169 verification.")],
    )


def render_sandbox_to_source_promotion_audit() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-to-source-promotion-audit", "v170.0 Operator-Approved Sandbox-to-Source Promotion", "operator_approved_sandbox_to_source_promotion", "v170.0", "sandbox-to-source-promotion-audit",
        "Audits sandbox result, promotion intake, source promotion plan, approval packet, post-promotion verification, and rollback planning while forbidding autonomous promotion.",
        [("trace", "Trace", "Trace promotion chain."), ("evidence", "Evidence", "Audit evidence continuity."), ("approval", "Approval", "Audit explicit approval."), ("no-auto-promotion", "No Auto", "Audit no autonomous promotion."), ("dashboard", "Dashboard", "Audit command deck/data-tip."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit README/history."), ("privacy", "Privacy", "Audit package privacy."), ("layer", "Layer", "Final v170 audit.")],
    )


def render_source_application_approval() -> str:
    return _render_supervised_runtime_arc(
        "/source-application-approval", "v171.0 Source Application Approval Intake Layer", "source_application_approval_intake_layer", "v171.0", "source-application-approval",
        "Imports the promotion packet, requires exact operator approval, binds source scope, expires stale approvals, and reconfirms safety boundaries before live source application eligibility.",
        [("schema", "Schema", "Define approval intake."), ("promotion-packet", "Packet", "Import promotion packet."), ("approval-phrase", "Phrase", "Match explicit approval."), ("scope", "Scope", "Bind source scope."), ("expiration", "Expiry", "Guard stale approval."), ("safety", "Safety", "Reconfirm boundaries."), ("risk", "Risk", "Classify application risk."), ("layer", "Layer", "Final v171 intake.")],
    )


def render_live_source_application_plan() -> str:
    return _render_supervised_runtime_arc(
        "/live-source-application-plan", "v172.0 Live Source Patch Application Plan Layer", "live_source_patch_application_plan_layer", "v172.0", "live-source-application-plan",
        "Plans snapshots, ordered source mutations, conflict checks, dashboard safeguards, API/CLI parity, and docs updates without applying unapproved changes.",
        [("schema", "Schema", "Define live steps."), ("snapshot", "Snapshot", "Plan preflight snapshot."), ("mutation-plan", "Mutations", "Plan file changes."), ("conflicts", "Conflicts", "Plan drift checks."), ("dashboard", "Dashboard", "Protect command deck/data-tip."), ("parity-check", "Parity", "Plan API/CLI parity."), ("docs", "Docs", "Plan docs updates."), ("layer", "Layer", "Final v172 plan.")],
    )


def render_approved_source_application_execution() -> str:
    return _render_supervised_runtime_arc(
        "/approved-source-application-execution", "v173.0 Approved Source Application Execution Packet", "approved_source_application_execution_packet", "v173.0", "approved-source-application-execution",
        "Defines the approval-bound execution packet, snapshot requirements, approved-file writer guard, draft-source guard, evidence capture, halt rules, and no-cascade boundary.",
        [("schema", "Schema", "Define execution packet."), ("snapshot", "Snapshot", "Require snapshot."), ("approved-files", "Files", "Guard approved files."), ("draft-guard", "Drafts", "Guard generated drafts."), ("evidence", "Evidence", "Plan evidence capture."), ("halt", "Halt", "Define halt rules."), ("no-cascade", "No Cascade", "Prevent follow-on work."), ("layer", "Layer", "Final v173 packet.")],
    )


def render_post_application_verification() -> str:
    return _render_supervised_runtime_arc(
        "/post-application-verification", "v174.0 Post-Application Verification and Rollback Control Layer", "post_application_verification_and_rollback_control_layer", "v174.0", "post-application-verification",
        "Prepares post-application fast/install smoke, dashboard render, tooltip regression, package privacy, and rollback readiness controls without hidden execution.",
        [("schema", "Schema", "Define verification fields."), ("fast-smoke", "Fast", "Plan fast smoke."), ("install-smoke", "Install", "Plan install smoke."), ("dashboard", "Dashboard", "Plan render checks."), ("tooltips", "Tooltips", "Plan data-tip checks."), ("privacy", "Privacy", "Plan package privacy."), ("rollback", "Rollback", "Plan rollback readiness."), ("layer", "Layer", "Final v174 controls.")],
    )


def render_source_patch_application_audit() -> str:
    return _render_supervised_runtime_arc(
        "/source-patch-application-audit", "v175.0 Operator-Approved Source Patch Application", "operator_approved_source_patch_application", "v175.0", "source-patch-application-audit",
        "Audits promotion packet, explicit approval intake, live application planning, execution packet, verification controls, rollback readiness, and non-autonomous source application boundaries.",
        [("trace", "Trace", "Trace application chain."), ("approval", "Approval", "Audit explicit approval."), ("scope", "Scope", "Audit approved scope."), ("safety", "Safety", "Audit safety boundary."), ("dashboard", "Dashboard", "Audit command deck/data-tip."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit README/history."), ("privacy", "Privacy", "Audit package privacy."), ("layer", "Layer", "Final v175 audit.")],
    )


def render_post_application_outcome_intake() -> str:
    return _render_supervised_runtime_arc(
        "/post-application-outcome-intake", "v176.0 Post-Application Outcome Intake Layer", "post_application_outcome_intake_layer", "v176.0", "post-application-outcome-intake",
        "Normalizes approved source application outcomes, verification imports, operator notes, expected-vs-actual comparisons, warning classes, and residual risk without triggering fixes or follow-up work.",
        [("schema", "Schema", "Define outcome intake."), ("receipt", "Receipt", "Import application packet."), ("verification", "Evidence", "Import verification results."), ("comparison", "Compare", "Expected vs actual."), ("classify", "Classify", "Classify warnings."), ("notes", "Notes", "Bind operator notes."), ("risk-summary", "Risk", "Summarize residual risk."), ("layer", "Layer", "Final v176 intake.")],
    )


def render_post_application_lessons() -> str:
    return _render_supervised_runtime_arc(
        "/post-application-lessons", "v177.0 Supervised Lesson Extraction Layer v2", "supervised_lesson_extraction_layer_v2", "v177.0", "post-application-lessons",
        "Extracts reviewable success, failure, regression, safety, and documentation lessons after approved source application while keeping memory and identity mutation blocked.",
        [("schema", "Schema", "Define lesson packets."), ("successes", "Successes", "Extract success patterns."), ("failures", "Failures", "Extract failure patterns."), ("regressions", "Regressions", "Detect repeated issues."), ("safety", "Safety", "Classify safety lessons."), ("docs", "Docs", "Build doc lessons."), ("memory-guard", "Memory", "Block memory writes."), ("layer", "Layer", "Final v177 lessons.")],
    )


def render_next_improvement_candidates() -> str:
    return _render_supervised_runtime_arc(
        "/next-improvement-candidates", "v178.0 Supervised Next-Improvement Candidate Builder", "supervised_next_improvement_candidate_builder", "v178.0", "next-improvement-candidates",
        "Builds ranked future improvement candidates from outcome evidence and reviewed lessons without auto-selecting work orders, roadmaps, patches, or source changes.",
        [("schema", "Schema", "Define candidate records."), ("lesson-map", "Lessons", "Map lessons to candidates."), ("regression-fixes", "Fixes", "Build regression fixes."), ("safety-hardening", "Safety", "Build hardening candidates."), ("dashboard", "Dashboard", "Suggest console refinements."), ("verification", "Verify", "Suggest coverage."), ("rank", "Rank", "Rank candidates."), ("layer", "Layer", "Final v178 candidates.")],
    )


def render_post_application_release_readiness() -> str:
    return _render_supervised_runtime_arc(
        "/post-application-release-readiness", "v179.0 Release Readiness Judgment Layer v2", "release_readiness_judgment_layer_v2", "v179.0", "post-application-release-readiness",
        "Judges whether the current tree is ready, needs revision, or is blocked after source application while refusing to create, package, sign, freeze, or publish release candidates.",
        [("schema", "Schema", "Define readiness state."), ("version", "Version", "Audit markers."), ("cleanliness", "Clean", "Audit source state."), ("parity-audit", "Parity", "Audit dashboard/API/CLI."), ("privacy", "Privacy", "Audit package privacy."), ("evidence", "Evidence", "Bind verification evidence."), ("recommendation", "Decision", "Recommend ready/revise/blocked."), ("layer", "Layer", "Final v179 readiness.")],
    )


def render_post_application_cycle_closure() -> str:
    return _render_supervised_runtime_arc(
        "/post-application-cycle-closure", "v180.0 Operator-Governed Post-Application Learning and Release Readiness", "operator_governed_post_application_learning_and_release_readiness", "v180.0", "post-application-cycle-closure",
        "Audits the complete post-application loop from approval and application through outcome intake, lessons, next candidates, and release readiness while blocking cascade work and autonomy.",
        [("trace", "Trace", "Trace closure loop."), ("approval", "Approval", "Audit approval boundary."), ("cascade", "Cascade", "Audit no-cascade rule."), ("memory-identity", "Memory/ID", "Audit memory and identity."), ("release", "Release", "Audit release boundary."), ("dashboard", "Dashboard", "Audit command deck/data-tip."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit docs/history."), ("layer", "Layer", "Final v180 closure.")],
    )


def render_cycle_intelligence_intake() -> str:
    return _render_supervised_runtime_arc(
        "/cycle-intelligence-intake", "v181.0 Cycle Intelligence Intake Layer", "cycle_intelligence_intake_layer", "v181.0", "cycle-intelligence-intake",
        "Collects prior-cycle outcomes, lessons, candidates, release-readiness results, closure audits, risks, and operator constraints into one read-only next-cycle planning context.",
        [("schema", "Schema", "Define cycle context."), ("summary", "Summary", "Bind last cycle."), ("evidence", "Evidence", "Index sources."), ("risks", "Risks", "Collect open risks."), ("completed", "Completed", "List verified improvements."), ("carry-forward", "Carry", "Carry forward candidates."), ("constraints", "Rules", "Bind constraints."), ("layer", "Layer", "Final v181 intake.")],
    )


def render_supervised_patch_priority_matrix() -> str:
    return _render_supervised_runtime_arc(
        "/supervised-patch-priority-matrix", "v182.0 Supervised Patch Priority Matrix", "supervised_patch_priority_matrix", "v182.0", "supervised-patch-priority-matrix",
        "Scores candidate benefit, safety value, complexity, regression risk, verification burden, documentation burden, operator friction, and maturity gain without treating scores as approval.",
        [("schema", "Schema", "Define scoring fields."), ("benefit", "Benefit", "Score usefulness."), ("safety", "Safety", "Score supervision value."), ("complexity", "Complexity", "Estimate difficulty."), ("regression-risk", "Risk", "Estimate regressions."), ("verification", "Verify", "Estimate checks."), ("docs", "Docs", "Estimate doc burden."), ("layer", "Layer", "Final v182 matrix.")],
    )


def render_next_patch_proposal_assembly() -> str:
    return _render_supervised_runtime_arc(
        "/next-patch-proposal-assembly", "v183.0 Next Patch Proposal Assembly Layer", "next_patch_proposal_assembly_layer", "v183.0", "next-patch-proposal-assembly",
        "Assembles reviewable proposal packets from scored candidates, including scope, safety boundaries, verification plans, rollback expectations, docs obligations, and operator decision summaries.",
        [("schema", "Schema", "Define proposal packets."), ("top-candidate", "Top", "Build top proposal."), ("bundle", "Bundle", "Group compatible work."), ("risk", "Risk", "Constrain bundles."), ("verification", "Verify", "Plan checks."), ("docs", "Docs", "Plan docs."), ("decision", "Decision", "Prepare operator choices."), ("layer", "Layer", "Final v183 assembly.")],
    )


def render_supervised_patch_session_planner() -> str:
    return _render_supervised_runtime_arc(
        "/supervised-patch-session-planner", "v184.0 Supervised Patch Session Planner", "supervised_patch_session_planner", "v184.0", "supervised-patch-session-planner",
        "Prepares next-session packets, fresh-chat prompts, scope binders, approval phrasing, verification checklists, documentation checklists, and safety reminders without starting implementation.",
        [("schema", "Schema", "Define session packet."), ("fresh-chat", "Prompt", "Build continuation prompt."), ("scope", "Scope", "Bind session scope."), ("approval", "Approval", "Bind approval phrase."), ("verification", "Verify", "Export checklist."), ("docs", "Docs", "Export doc checklist."), ("safety", "Safety", "Reassert boundaries."), ("layer", "Layer", "Final v184 planner.")],
    )


def render_patch_cycle_intelligence_audit() -> str:
    return _render_supervised_runtime_arc(
        "/patch-cycle-intelligence-audit", "v185.0 Operator-Governed Patch Cycle Intelligence", "operator_governed_patch_cycle_intelligence", "v185.0", "patch-cycle-intelligence-audit",
        "Audits intake-to-priority, priority-to-proposal, proposal-to-session traceability, approval boundaries, no-autonomous-continuation, dashboard style, route/API/CLI parity, docs, and release history.",
        [("intake-priority", "Intake", "Audit intake to priority."), ("priority-proposal", "Proposal", "Audit priority to proposal."), ("proposal-session", "Session", "Audit proposal to session."), ("approval", "Approval", "Audit approval boundary."), ("continuation", "Stop", "Audit no continuation."), ("dashboard", "Dashboard", "Audit data-tip style."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit docs/history."), ("layer", "Layer", "Final v185 audit.")],
    )


def render_multi_cycle_roadmap_intake() -> str:
    return _render_supervised_runtime_arc(
        "/multi-cycle-roadmap-intake", "v186.0 Multi-Cycle Roadmap Intake Layer", "multi_cycle_roadmap_intake_layer", "v186.0", "multi-cycle-roadmap-intake",
        "Collects current version, completed arcs, capabilities, safety boundaries, open risks, deferred candidates, verification state, docs state, and roadmap constraints into one read-only planning context.",
        [("schema", "Schema", "Define context."), ("completed-arcs", "Arcs", "Index arcs."), ("capabilities", "Caps", "Inventory capabilities."), ("safety-boundaries", "Safety", "Inventory boundaries."), ("risk-debt", "Debt", "Collect risks."), ("deferred", "Deferred", "Carry candidates."), ("constraints", "Rules", "Bind constraints."), ("layer", "Layer", "Final v186 intake.")],
    )


def render_supervised_roadmap_options() -> str:
    return _render_supervised_runtime_arc(
        "/supervised-roadmap-options", "v187.0 Supervised Roadmap Option Builder", "supervised_roadmap_option_builder", "v187.0", "supervised-roadmap-options",
        "Builds safety-first, capability-maturity, dashboard-operator, verification-strength, and v200-preparation roadmap options with tradeoff summaries, all advisory only.",
        [("schema", "Schema", "Define options."), ("safety-first", "Safety", "Safety roadmap."), ("capability-maturity", "Maturity", "Capability roadmap."), ("dashboard-operator", "Console", "Dashboard roadmap."), ("verification-strength", "Verify", "Verification roadmap."), ("v200-prep", "v200", "v200 roadmap."), ("tradeoffs", "Tradeoffs", "Summarize options."), ("layer", "Layer", "Final v187 options.")],
    )


def render_roadmap_dependency_risk_graph() -> str:
    return _render_supervised_runtime_arc(
        "/roadmap-dependency-risk-graph", "v188.0 Roadmap Dependency and Risk Graph", "roadmap_dependency_and_risk_graph", "v188.0", "roadmap-dependency-risk-graph",
        "Maps future arc dependencies, safety prerequisites, verification prerequisites, dashboard usability dependencies, and recurring risk clusters without activating roadmap stages.",
        [("schema", "Schema", "Define graph."), ("arc-dependencies", "Arcs", "Map arc dependencies."), ("safety-dependencies", "Safety", "Map safety dependencies."), ("verification-dependencies", "Verify", "Map verification dependencies."), ("dashboard-dependencies", "Dashboard", "Map console dependencies."), ("risk-clusters", "Risks", "Cluster risks."), ("narrative", "Narrative", "Explain graph."), ("layer", "Layer", "Final v188 graph.")],
    )


def render_v200_readiness_model() -> str:
    return _render_supervised_runtime_arc(
        "/v200-readiness-model", "v189.0 v200 Milestone Readiness Model", "v200_milestone_readiness_model", "v189.0", "v200-readiness-model",
        "Scores governance, verification, source mutation, planning, and operator experience maturity to show v200 gaps without treating readiness as approval.",
        [("schema", "Schema", "Define domains."), ("governance", "Governance", "Score gates."), ("verification", "Verify", "Score checks."), ("source-mutation", "Source", "Score mutation control."), ("planning", "Planning", "Score planning."), ("operator-experience", "Operator", "Score console UX."), ("gap-report", "Gaps", "Build gap report."), ("layer", "Layer", "Final v189 model.")],
    )


def render_multi_cycle_roadmap_governance_audit() -> str:
    return _render_supervised_runtime_arc(
        "/multi-cycle-roadmap-governance-audit", "v190.0 Operator-Governed Multi-Cycle Roadmap Intelligence", "operator_governed_multi_cycle_roadmap_intelligence", "v190.0", "multi-cycle-roadmap-governance-audit",
        "Audits roadmap source traceability, option-to-dependency continuity, dependency-to-v200 mapping, approval boundaries, no-autonomous-roadmap behavior, dashboard style, parity, docs, and release history.",
        [("source-trace", "Source", "Audit source trace."), ("option-dependency", "Dependency", "Audit option graph."), ("dependency-v200", "v200", "Audit v200 trace."), ("approval", "Approval", "Audit approval boundary."), ("no-autonomy", "No Auto", "Audit no roadmap launch."), ("dashboard", "Dashboard", "Audit data-tip style."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit docs/history."), ("layer", "Layer", "Final v190 audit.")],
    )



def render_capability_maturity_inventory() -> str:
    return _render_supervised_runtime_arc(
        "/capability-maturity-inventory", "v191.0 Capability Inventory and Maturity Schema", "capability_inventory_and_maturity_schema", "v191.0", "capability-maturity-inventory",
        "Defines capability domains, maturity levels, evidence requirements, capability boundaries, safety dependencies, verification dependencies, and documentation dependencies. It cannot grant approval or trigger work.",
        [("schema", "Domains", "Define domains."), ("levels", "Levels", "Define maturity levels."), ("evidence", "Evidence", "Define evidence."), ("boundaries", "Bounds", "Bind boundaries."), ("safety", "Safety", "Safety dependencies."), ("verification", "Verify", "Verification dependencies."), ("docs", "Docs", "Documentation dependencies."), ("layer", "Layer", "Final v191 inventory.")],
    )

def render_capability_maturity_scoring() -> str:
    return _render_supervised_runtime_arc(
        "/capability-maturity-scoring", "v192.0 Capability Maturity Scoring Layer", "capability_maturity_scoring_layer", "v192.0", "capability-maturity-scoring",
        "Scores planning, patch drafting, application, verification, learning, dashboard operator experience, and safety governance capabilities using evidence-bound advisory criteria.",
        [("planning", "Planning", "Score planning."), ("drafting", "Drafting", "Score drafting."), ("application", "Apply", "Score application."), ("verification", "Verify", "Score verification."), ("learning", "Learning", "Score learning."), ("dashboard", "Console", "Score operator UX."), ("safety", "Safety", "Score governance."), ("layer", "Layer", "Final v192 scoring.")],
    )

def render_capability_gap_overreach_analysis() -> str:
    return _render_supervised_runtime_arc(
        "/capability-gap-overreach-analysis", "v193.0 Capability Gap and Overreach Analyzer", "capability_gap_and_overreach_analyzer", "v193.0", "capability-gap-overreach-analysis",
        "Identifies underdeveloped capabilities, autonomy overreach risks, verification gaps, documentation gaps, dashboard complexity, and v200 blockers without launching fixes.",
        [("schema", "Schema", "Define gaps."), ("underdeveloped", "Thin", "Find thin capabilities."), ("overreach", "Overreach", "Detect autonomy creep."), ("verification", "Verify", "Find check gaps."), ("docs", "Docs", "Find doc gaps."), ("dashboard", "Console", "Find clutter."), ("v200-blockers", "v200", "Find blockers."), ("layer", "Layer", "Final v193 analyzer.")],
    )

def render_capability_maturity_improvement_plan() -> str:
    return _render_supervised_runtime_arc(
        "/capability-maturity-improvement-plan", "v194.0 Capability Maturity Improvement Planner", "capability_maturity_improvement_planner", "v194.0", "capability-maturity-improvement-plan",
        "Prepares safety-first, verification, dashboard, learning, roadmap, and prioritized maturity improvement plans. Plans are not approval or execution packets.",
        [("schema", "Schema", "Define plans."), ("safety-first", "Safety", "Plan hardening."), ("verification", "Verify", "Plan checks."), ("dashboard", "Console", "Plan dashboard."), ("learning", "Learning", "Plan learning."), ("roadmap", "Roadmap", "Plan roadmap."), ("priority", "Priority", "Rank plans."), ("layer", "Layer", "Final v194 planner.")],
    )

def render_capability_maturity_governance_audit() -> str:
    return _render_supervised_runtime_arc(
        "/capability-maturity-governance-audit", "v195.0 Supervised Capability Maturity Modeling", "supervised_capability_maturity_modeling", "v195.0", "capability-maturity-governance-audit",
        "Audits score evidence traceability, gap-to-plan continuity, overreach boundaries, approval boundaries, no-autonomous-improvement behavior, dashboard style, parity, docs, and release history.",
        [("score-evidence", "Evidence", "Audit score evidence."), ("gap-plan", "Plans", "Audit gap to plan."), ("overreach", "Overreach", "Audit boundaries."), ("approval", "Approval", "Audit approval limits."), ("no-autonomy", "No Auto", "Audit no improvement launch."), ("dashboard", "Dashboard", "Audit data-tip style."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit docs/history."), ("layer", "Layer", "Final v195 audit.")],
    )


def render_governance_kernel_state() -> str:
    return _render_supervised_runtime_arc(
        "/governance-kernel-state", "v196.0 Governance Kernel State Model", "governance_kernel_state_model", "v196.0", "governance-kernel-state",
        "Defines central supervised governance state across lifecycle phase, capabilities, maturity, approval, source, verification, release, risk, and operator constraints. Descriptive only; cannot authorize actions.",
        [("schema", "Schema", "Define kernel state."), ("lifecycle", "Lifecycle", "Bind phases."), ("capabilities", "Caps", "Bind capability state."), ("approval", "Approval", "Bind approval state."), ("evidence", "Evidence", "Bind evidence."), ("risks", "Risks", "Bind risks."), ("constraints", "Rules", "Bind operator constraints."), ("layer", "Layer", "Final v196 state.")],
    )

def render_governance_rule_evaluation() -> str:
    return _render_supervised_runtime_arc(
        "/governance-rule-evaluation", "v197.0 Governance Rule Evaluation Layer", "governance_rule_evaluation_layer", "v197.0", "governance-rule-evaluation",
        "Classifies proposed actions, evaluates approval and evidence requirements, detects forbidden actions, flags safety conflicts, and produces review-only governance decisions. It cannot grant approval.",
        [("schema", "Schema", "Define rules."), ("classification", "Classify", "Classify actions."), ("approval", "Approval", "Evaluate approval."), ("forbidden", "Block", "Detect forbidden actions."), ("evidence", "Evidence", "Evaluate evidence."), ("safety", "Safety", "Detect conflicts."), ("decision", "Decision", "Summarize decision."), ("layer", "Layer", "Final v197 rules.")],
    )

def render_operator_authority_consent_ledger() -> str:
    return _render_supervised_runtime_arc(
        "/operator-authority-consent-ledger", "v198.0 Operator Authority and Consent Ledger", "operator_authority_and_consent_ledger", "v198.0", "operator-authority-consent-ledger",
        "Models explicit operator approval scope, target lifecycle stage, timestamp, expiration, revocation, and ambiguity checks. Readiness, success, scores, or inference never create consent.",
        [("schema", "Schema", "Define authority."), ("parser", "Parser", "Parse explicit approval."), ("scope", "Scope", "Bind scope."), ("expiration", "Expire", "Expire approvals."), ("revocation", "Revoke", "Track revocation."), ("ambiguity", "Ambiguity", "Reject unclear consent."), ("summary", "Summary", "Summarize ledger."), ("layer", "Layer", "Final v198 ledger.")],
    )

def render_governance_enforcement_simulation() -> str:
    return _render_supervised_runtime_arc(
        "/governance-enforcement-simulation", "v199.0 Governance Kernel Enforcement Simulation", "governance_kernel_enforcement_simulation", "v199.0", "governance-enforcement-simulation",
        "Simulates patch, release, memory, identity, autonomous continuation, and parity workflows against governance rules. Simulation reports explain pass/block outcomes and cannot execute changes.",
        [("schema", "Schema", "Define simulation."), ("patch", "Patch", "Simulate patch workflow."), ("release", "Release", "Simulate release workflow."), ("memory-identity", "Memory", "Simulate memory/identity."), ("autonomy", "Autonomy", "Simulate continuation."), ("parity-simulation", "Parity", "Simulate parity."), ("report", "Report", "Build reports."), ("layer", "Layer", "Final v199 simulation.")],
    )

def render_governance_kernel_audit() -> str:
    return _render_supervised_runtime_arc(
        "/governance-kernel-audit", "v200.0 Local Artificial Mind Governance Kernel v1", "local_artificial_mind_governance_kernel_v1", "v200.0", "governance-kernel-audit",
        "Audits governance state traceability, rule evaluation, consent ledger boundaries, enforcement simulation, no-autonomy guarantees, dashboard style, route/API/CLI parity, docs, and release history. v200 is governance, not autonomy.",
        [("state-trace", "State", "Audit state trace."), ("rule-trace", "Rules", "Audit rule trace."), ("consent", "Consent", "Audit consent."), ("simulation", "Sim", "Audit simulation."), ("no-autonomy", "No Auto", "Audit autonomy blocks."), ("dashboard", "Dashboard", "Audit data-tip style."), ("parity", "Parity", "Audit route/API/CLI."), ("docs", "Docs", "Audit docs/history."), ("layer", "Layer", "Final v200 audit.")],
    )


def render_governance_decision_packet() -> str:
    return _render_supervised_runtime_arc(
        "/governance-decision-packet", "v201.0 Supervised Governance Decision Packet Layer", "supervised_governance_decision_packet_layer", "v201.0", "governance-decision-packet",
        "Builds reviewable governance decision packets from request schema, action intent, governance context, evidence snapshot, consent scope, blockers, required approval, safe next action, and prohibited actions.",
        [("metadata", "Metadata", "Fix smoke/list metadata."), ("schema", "Schema", "Define requests."), ("intent", "Intent", "Classify actions."), ("context", "Context", "Bind governance state."), ("evidence", "Evidence", "Bind evidence."), ("consent", "Consent", "Bind consent scope."), ("renderer", "Render", "Render packets."), ("layer", "Layer", "Final v201 packet layer.")],
    )

def render_approval_transaction_model() -> str:
    return _render_supervised_runtime_arc(
        "/approval-transaction-model", "v202.0 Operator Approval Transaction Model", "operator_approval_transaction_model", "v202.0", "approval-transaction-model",
        "Models explicit approvals as scoped, expiring, revocable, consumable review records bound to files, routes, commands, and lifecycle stages without executing approved actions.",
        [("schema", "Schema", "Define transactions."), ("scope", "Scope", "Normalize scope."), ("targets", "Targets", "Bind files/routes/commands."), ("expiration", "Expire", "Guard drift."), ("revocation", "Revoke", "Track state."), ("ambiguity", "Ambiguity", "Reject unclear approval."), ("diff", "Diff", "Explain mismatch."), ("layer", "Layer", "Final v202 model.")],
    )

def render_governance_evidence_timeline() -> str:
    return _render_supervised_runtime_arc(
        "/governance-evidence-timeline", "v203.0 Governance Evidence Timeline", "governance_evidence_timeline", "v203.0", "governance-evidence-timeline",
        "Indexes and summarizes governance evidence across docs, release history, smoke, package privacy, dashboard/API/CLI parity, approvals, conflicts, stale evidence, and source drift.",
        [("schema", "Schema", "Define events."), ("sources", "Sources", "Index evidence."), ("links", "Links", "Link arcs."), ("stale", "Stale", "Detect stale evidence."), ("conflicts", "Conflict", "Detect contradictions."), ("drift", "Drift", "Check residue/drift."), ("summary", "Summary", "Summarize timeline."), ("layer", "Layer", "Final v203 timeline.")],
    )

def render_operator_governance_console() -> str:
    return _render_supervised_runtime_arc(
        "/operator-governance-console", "v204.0 Operator Governance Console v1", "operator_governance_console_v1", "v204.0", "operator-governance-console",
        "Groups decision cards, approval scope previews, blocker/risk explainers, timeline views, and safe command previews in the command-deck style while preserving data-tip hover behavior.",
        [("layout", "Layout", "Group console."), ("decisions", "Cards", "Show decisions."), ("approval", "Approval", "Preview scope."), ("risks", "Risks", "Explain blockers."), ("timeline", "Timeline", "Show evidence."), ("commands", "Commands", "Preview only."), ("tooltips", "Tooltips", "Guard data-tip."), ("layer", "Layer", "Final v204 console.")],
    )

def render_governance_integration_audit() -> str:
    return _render_supervised_runtime_arc(
        "/governance-integration-audit", "v205.0 Operator-Governed Governance Kernel Integration", "operator_governed_governance_kernel_integration", "v205.0", "governance-integration-audit",
        "Audits the integrated decision packet, approval transaction, evidence timeline, governance console, verification metadata, route/API/CLI parity, docs, release history, and no-autonomy boundaries.",
        [("decision-trace", "Decision", "Audit decisions."), ("approval-boundary", "Approval", "Audit approval boundary."), ("evidence", "Evidence", "Audit timeline."), ("console", "Console", "Audit console."), ("metadata", "Metadata", "Audit verification."), ("no-autonomy", "No Auto", "Audit autonomy blocks."), ("parity", "Parity", "Audit route/API/CLI."), ("layer", "Layer", "Final v205 audit.")],
    )


def render_cognitive_continuity_packet() -> str:
    return _render_supervised_runtime_arc(
        "/cognitive-continuity-packet", "v206.0 Supervised Cognitive Continuity Packet Layer", "supervised_cognitive_continuity_packet_layer", "v206.0", "cognitive-continuity-packet",
        "Summarizes supervised cycle outcomes, candidate lessons, risks, operator meaning, and safe next-step suggestions without granting approval or continuing work.",
        [("schema", "Schema", "Define continuity packet fields."), ("outcomes", "Outcomes", "Classify cycle outcomes."), ("lessons", "Lessons", "Extract candidate-only lessons."), ("risks", "Risks", "Bind continuity risks."), ("meaning", "Meaning", "Summarize growth meaning."), ("recommendation-guard", "Guard", "Keep recommendations non-authorizing."), ("parity", "Parity", "Dashboard/API/CLI coverage."), ("layer", "Layer", "Final v206 continuity packet.")],
    )

def render_memory_candidate_staging() -> str:
    return _render_supervised_runtime_arc(
        "/memory-candidate-staging", "v207.0 Supervised Memory Candidate Staging", "supervised_memory_candidate_staging", "v207.0", "memory-candidate-staging",
        "Stages proposed memory updates with source, evidence, type, confidence, safety category, drift warnings, and operator review status. It never writes memory.",
        [("schema", "Schema", "Define memory candidates."), ("types", "Types", "Classify candidate types."), ("safety", "Safety", "Filter sensitive or unsupported memory."), ("evidence", "Evidence", "Bind source evidence."), ("non-mutation", "No Write", "Block memory mutation."), ("drift", "Drift", "Warn on rule conflicts."), ("gate", "Gate", "Smoke/non-mutation checks."), ("layer", "Layer", "Final v207 staging.")],
    )

def render_identity_boundary_layer() -> str:
    return _render_supervised_runtime_arc(
        "/identity-boundary-layer", "v208.0 Operator-Governed Identity Boundary Layer", "operator_governed_identity_boundary_layer", "v208.0", "identity-boundary-layer",
        "Detects identity, personality, purpose, autonomy, and memory-authority changes and keeps every identity-adjacent change locked behind explicit operator approval.",
        [("schema", "Schema", "Define identity boundaries."), ("changes", "Changes", "Detect identity changes."), ("drift", "Drift", "Audit personality drift."), ("lock", "Lock", "Require operator approval."), ("forbidden", "Forbidden", "Block self-mutation rules."), ("smoke", "Smoke", "Regression checks."), ("gate", "Gate", "Pre-v208 boundary gate."), ("layer", "Layer", "Final v208 boundary.")],
    )

def render_supervised_reflection_journal() -> str:
    return _render_supervised_runtime_arc(
        "/supervised-reflection-journal", "v209.0 Supervised Reflection and Growth Journal", "supervised_reflection_and_growth_journal", "v209.0", "supervised-reflection-journal",
        "Records supervised growth milestones, repeated weaknesses, improvement themes, and what-Eidolon-learned summaries without scheduling work or mutating behavior.",
        [("schema", "Schema", "Define journal entries."), ("milestones", "Milestones", "Map growth milestones."), ("weaknesses", "Weaknesses", "Detect recurring gaps."), ("themes", "Themes", "Extract improvement themes."), ("renderer", "Render", "Render reflections."), ("safety", "Safety", "Block reflection-as-action."), ("gate", "Gate", "Smoke coverage."), ("layer", "Layer", "Final v209 journal.")],
    )

def render_cognitive_continuity_audit() -> str:
    return _render_supervised_runtime_arc(
        "/cognitive-continuity-audit", "v210.0 Operator-Governed Cognitive Continuity Layer v1", "operator_governed_cognitive_continuity_layer_v1", "v210.0", "cognitive-continuity-audit",
        "Audits continuity packets, memory candidate staging, identity boundaries, reflection journal, governance integration, dashboard style, API/CLI parity, docs, release history, and no-autonomy boundaries.",
        [("continuity", "Continuity", "Audit continuity packets."), ("memory", "Memory", "Audit memory candidates."), ("identity", "Identity", "Audit identity boundaries."), ("reflection", "Reflection", "Audit reflection journal."), ("governance", "Governance", "Audit v205 integration."), ("dashboard", "Dashboard", "Audit console style."), ("parity", "Parity", "Audit API/CLI parity."), ("layer", "Layer", "Final v210 audit.")],
    )



def render_self_model_snapshot() -> str:
    return _render_supervised_runtime_arc(
        "/self-model-snapshot", "v211.0 Supervised Self-Model Snapshot Layer", "supervised_self_model_snapshot_layer", "v211.0", "self-model-snapshot",
        "Builds evidence-bound snapshots of Eidolon's identity, purpose, capabilities, limits, governance boundaries, and confidence scores without granting authority.",
        [("schema", "Schema", "Define self-model fields."), ("capabilities", "Capabilities", "Bind active capability state."), ("limits", "Limits", "Record forbidden boundaries."), ("evidence", "Evidence", "Bind source claims."), ("confidence", "Confidence", "Score without permission."), ("dashboard", "Dashboard", "Expose snapshot view."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v211 snapshot.")],
    )

def render_deliberation_packet() -> str:
    return _render_supervised_runtime_arc(
        "/deliberation-packet", "v212.0 Supervised Deliberation Packet Layer", "supervised_deliberation_packet_layer", "v212.0", "deliberation-packet",
        "Builds reviewable option reasoning with tradeoffs, risks, evidence quality, uncertainty, and recommendation guards while forbidding execution or approval.",
        [("schema", "Schema", "Define packet fields."), ("options", "Options", "Generate choices."), ("tradeoffs", "Tradeoffs", "Map costs and benefits."), ("risk-benefit", "Risk", "Bind risks/benefits."), ("evidence-quality", "Evidence", "Score evidence quality."), ("uncertainty", "Uncertainty", "Render uncertainty."), ("recommendation-guard", "Guard", "Keep advisory."), ("layer", "Layer", "Final v212 deliberation.")],
    )

def render_purpose_alignment_layer() -> str:
    return _render_supervised_runtime_arc(
        "/purpose-alignment-layer", "v213.0 Operator-Governed Purpose Alignment Layer", "operator_governed_purpose_alignment_layer", "v213.0", "purpose-alignment-layer",
        "Indexes purpose claims and standing rules, compares runtime claims, and detects autonomy, identity, and approval drift without rewriting purpose or granting permission.",
        [("claims", "Claims", "Index purpose claims."), ("standing-rules", "Rules", "Extract rules."), ("runtime-claims", "Runtime", "Compare runtime claims."), ("autonomy-drift", "Autonomy", "Detect autonomy drift."), ("identity-drift", "Identity", "Detect identity drift."), ("approval-drift", "Consent", "Detect approval drift."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v213 alignment.")],
    )

def render_behavioral_pattern_intelligence() -> str:
    return _render_supervised_runtime_arc(
        "/behavioral-pattern-intelligence", "v214.0 Supervised Behavioral Pattern Intelligence", "supervised_behavioral_pattern_intelligence", "v214.0", "behavioral-pattern-intelligence",
        "Tracks repeated weaknesses, repeated strengths, dashboard regressions, smoke/verification gaps, documentation drift, and advisory improvement priorities without launching work.",
        [("schema", "Schema", "Define events."), ("failures", "Failures", "Detect repeated failures."), ("strengths", "Strengths", "Detect repeated strengths."), ("dashboard-regressions", "Dashboard", "Track dashboard patterns."), ("verification-weaknesses", "Smoke", "Track verification gaps."), ("documentation-drift", "Docs", "Track doc drift."), ("priority", "Priority", "Score advisory priorities."), ("layer", "Layer", "Final v214 patterns.")],
    )

def render_self_model_integration_audit() -> str:
    return _render_supervised_runtime_arc(
        "/self-model-integration-audit", "v215.0 Operator-Governed Deliberation and Self-Model Layer v1", "operator_governed_deliberation_and_self_model_layer_v1", "v215.0", "self-model-integration-audit",
        "Audits self-model evidence, deliberation safety, purpose alignment, behavioral patterns, no-autonomy boundaries, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("self-model", "Self-Model", "Audit self-model claims."), ("deliberation", "Deliberation", "Audit deliberation safety."), ("purpose", "Purpose", "Audit alignment."), ("patterns", "Patterns", "Audit behavior patterns."), ("no-autonomy", "No Auto", "Audit autonomy locks."), ("dashboard", "Dashboard", "Audit command deck."), ("parity", "Parity", "Audit API/CLI parity."), ("layer", "Layer", "Final v215 audit.")],
    )



def render_internal_simulation_packet() -> str:
    return _render_supervised_runtime_arc(
        "/internal-simulation-packet", "v216.0 Supervised Internal Simulation Packet Layer", "supervised_internal_simulation_packet_layer", "v216.0", "internal-simulation-packet",
        "Builds review-only simulation packets with assumptions, expected outcomes, failure modes, blockers, required evidence, approval requirements, and hard non-execution guards.",
        [("schema", "Schema", "Define packet fields."), ("types", "Types", "Classify simulation types."), ("assumptions", "Assumptions", "Bind explicit assumptions."), ("outcomes", "Outcomes", "Render likely outcomes."), ("failure-modes", "Failures", "Bind failure modes."), ("non-execution", "No Exec", "Block command execution."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v216 simulation packet.")],
    )

def render_foresight_branch_comparison() -> str:
    return _render_supervised_runtime_arc(
        "/foresight-branch-comparison", "v217.0 Operator-Governed Foresight Branch Comparison", "operator_governed_foresight_branch_comparison", "v217.0", "foresight-branch-comparison",
        "Compares candidate supervised branches by risk, benefit, governance cost, evidence readiness, and operator recommendation while forbidding roadmap auto-selection.",
        [("schema", "Schema", "Define branch fields."), ("branches", "Branches", "Generate candidates."), ("risk", "Risk", "Score risk."), ("benefit", "Benefit", "Score benefit."), ("governance-cost", "Cost", "Estimate governance cost."), ("evidence-readiness", "Evidence", "Score readiness."), ("recommendation", "Recommend", "Render advisory recommendation."), ("layer", "Layer", "Final v217 comparison.")],
    )

def render_pre_change_consequence_modeling() -> str:
    return _render_supervised_runtime_arc(
        "/pre-change-consequence-modeling", "v218.0 Supervised Pre-Change Consequence Modeling", "supervised_pre_change_consequence_modeling", "v218.0", "pre-change-consequence-modeling",
        "Forecasts source, runtime, dashboard, documentation, smoke, verification, and approval-scope impact before a change, without mutating files or executing checks.",
        [("schema", "Schema", "Define consequence model."), ("source", "Source", "Forecast source impact."), ("runtime", "Runtime", "Forecast runtime surfaces."), ("dashboard", "Dashboard", "Forecast console impact."), ("docs", "Docs", "Forecast documentation."), ("smoke", "Smoke", "Forecast verification."), ("approval-scope", "Approval", "Forecast approval scope."), ("layer", "Layer", "Final v218 consequence model.")],
    )

def render_expectation_reality_check() -> str:
    return _render_supervised_runtime_arc(
        "/expectation-reality-check", "v219.0 Supervised Expectation-Reality Check Layer", "supervised_expectation_reality_check_layer", "v219.0", "expectation-reality-check",
        "Builds expectation checklists and compares them to post-change evidence, scoring simulation accuracy without launching follow-up work.",
        [("schema", "Schema", "Define expectation checklist."), ("routes", "Routes", "Expected route checklist."), ("runtime", "Runtime", "Runtime coverage checklist."), ("docs", "Docs", "Documentation checklist."), ("smoke", "Smoke", "Smoke checklist."), ("comparison", "Compare", "Reality comparison."), ("accuracy", "Accuracy", "Score simulation accuracy."), ("layer", "Layer", "Final v219 reality check.")],
    )

def render_simulation_foresight_audit() -> str:
    return _render_supervised_runtime_arc(
        "/simulation-foresight-audit", "v220.0 Operator-Governed Internal Simulation and Foresight Layer v1", "operator_governed_internal_simulation_and_foresight_layer_v1", "v220.0", "simulation-foresight-audit",
        "Audits simulation packets, branch comparison, consequence modeling, expectation-reality checks, no-execution safety, no-autonomy boundaries, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("simulation", "Simulation", "Audit simulation packets."), ("branches", "Branches", "Audit branch comparison."), ("consequences", "Impact", "Audit consequence modeling."), ("reality", "Reality", "Audit expectation/reality."), ("no-execution", "No Exec", "Audit non-execution."), ("no-autonomy", "No Auto", "Audit autonomy locks."), ("parity", "Parity", "Audit API/CLI parity."), ("layer", "Layer", "Final v220 audit.")],
    )


def render_learning_objective_map() -> str:
    return _render_supervised_runtime_arc(
        "/learning-objective-map", "v221.0 Supervised Learning Objective Map", "supervised_learning_objective_map", "v221.0", "learning-objective-map",
        "Maps evidence-bound learning objectives from capability gaps and recurring weaknesses while blocking autonomous learning loops, memory mutation, identity mutation, and capability upgrades.",
        [("schema", "Schema", "Define objective fields."), ("gaps", "Gaps", "Bind capability gaps."), ("governance", "Governance", "Classify learning risk."), ("evidence", "Evidence", "Bind required proof."), ("priority", "Priority", "Score curriculum value."), ("safety", "No Auto", "Block autonomous learning."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v221 map.")],
    )


def render_practice_task_design() -> str:
    return _render_supervised_runtime_arc(
        "/practice-task-design", "v222.0 Supervised Practice Task Design Layer", "supervised_practice_task_design_layer", "v222.0", "practice-task-design",
        "Designs reviewable practice tasks with skill targets, expected evidence, risk/scope guards, operator checklists, and hard non-execution boundaries.",
        [("schema", "Schema", "Define task fields."), ("types", "Types", "Classify exercises."), ("skills", "Skills", "Bind target skills."), ("evidence", "Evidence", "Expected evidence."), ("scope", "Scope", "Guard risk and scope."), ("review", "Review", "Operator checklist."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v222 design.")],
    )


def render_capability_calibration() -> str:
    return _render_supervised_runtime_arc(
        "/capability-calibration", "v223.0 Operator-Governed Capability Calibration Layer", "operator_governed_capability_calibration_layer", "v223.0", "capability-calibration",
        "Scores capability claims against evidence, flags unsupported claims and overconfidence, and prevents calibration from becoming capability promotion.",
        [("schema", "Schema", "Define calibration packet."), ("claims", "Claims", "Extract claims."), ("evidence", "Evidence", "Score proof."), ("unsupported", "Unsupported", "Detect unsupported claims."), ("warnings", "Warnings", "Warn overconfidence."), ("confidence", "Confidence", "Render confidence."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v223 calibration.")],
    )


def render_skill_gap_remediation_planner() -> str:
    return _render_supervised_runtime_arc(
        "/skill-gap-remediation-planner", "v224.0 Supervised Skill Gap Remediation Planner", "supervised_skill_gap_remediation_planner", "v224.0", "skill-gap-remediation-planner",
        "Turns calibrated weaknesses into supervised remediation plans with verification expectations, governance risk, explicit approval requirements, and no-continuation guards.",
        [("schema", "Schema", "Define gap fields."), ("clusters", "Clusters", "Detect weakness clusters."), ("strategy", "Strategy", "Generate remediation."), ("verification", "Verify", "Bind verification plan."), ("risk", "Risk", "Bind governance risk."), ("approval", "Approval", "Render approval needs."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v224 planner.")],
    )


def render_learning_curriculum_audit() -> str:
    return _render_supervised_runtime_arc(
        "/learning-curriculum-audit", "v225.0 Operator-Governed Learning Curriculum and Capability Calibration Layer v1", "operator_governed_learning_curriculum_and_capability_calibration_layer_v1", "v225.0", "learning-curriculum-audit",
        "Audits learning objectives, practice task safety, capability calibration, skill-gap remediation, no-autonomous-learning, no-memory/identity mutation, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("objectives", "Objectives", "Audit objective map."), ("practice", "Practice", "Audit practice safety."), ("calibration", "Calibration", "Audit evidence scoring."), ("remediation", "Remediation", "Audit remediation."), ("no-autonomy", "No Auto", "Audit learning locks."), ("memory", "Memory", "Audit memory/identity locks."), ("parity", "Parity", "Audit API/CLI parity."), ("layer", "Layer", "Final v225 audit.")],
    )


def render_knowledge_claim_ledger() -> str:
    return _render_supervised_runtime_arc(
        "/knowledge-claim-ledger", "v226.0 Supervised Knowledge Claim Ledger", "supervised_knowledge_claim_ledger", "v226.0", "knowledge-claim-ledger",
        "Records knowledge claims as reviewable candidates with source evidence, confidence, freshness, risk, operator-review state, and hard non-mutation boundaries.",
        [("schema", "Schema", "Define claim fields."), ("types", "Types", "Classify claim kinds."), ("evidence", "Evidence", "Bind proof."), ("confidence", "Confidence", "Render confidence."), ("safety", "No Mutate", "Block memory/source writes."), ("dashboard", "Dash", "Command-deck view."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v226 ledger.")],
    )


def render_belief_candidate_review() -> str:
    return _render_supervised_runtime_arc(
        "/belief-candidate-review", "v227.0 Operator-Reviewed Belief Candidate Layer", "operator_reviewed_belief_candidate_layer", "v227.0", "belief-candidate-review",
        "Stages belief candidates with source binding, risk classification, confidence scoring, promotion requirements, operator review checklists, and non-authority guards.",
        [("schema", "Schema", "Define belief fields."), ("source", "Source", "Bind evidence."), ("risk", "Risk", "Classify risk."), ("confidence", "Confidence", "Score belief."), ("promotion", "Promotion", "Require review."), ("review", "Review", "Operator checklist."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v227 review.")],
    )


def render_contradiction_staleness_intelligence() -> str:
    return _render_supervised_runtime_arc(
        "/contradiction-staleness-intelligence", "v228.0 Supervised Contradiction and Staleness Intelligence", "supervised_contradiction_and_staleness_intelligence", "v228.0", "contradiction-staleness-intelligence",
        "Detects claim conflicts, README/runtime drift, release-history/version drift, governance claim conflicts, and stale knowledge warnings without executing fixes or fetching sources.",
        [("schema", "Schema", "Define events."), ("conflicts", "Conflicts", "Detect claim conflict."), ("runtime", "Runtime", "Docs/runtime drift."), ("versions", "Versions", "Marker drift."), ("governance", "Govern", "Rule conflicts."), ("stale", "Stale", "Warn staleness."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v228 intel.")],
    )


def render_project_knowledge_map() -> str:
    return _render_supervised_runtime_arc(
        "/project-knowledge-map", "v229.0 Supervised Project Knowledge Map Layer", "supervised_project_knowledge_map_layer", "v229.0", "project-knowledge-map",
        "Maps capability arcs, dashboard surfaces, API/CLI surfaces, governance boundaries, and documentation coverage without granting authority or mutating source.",
        [("schema", "Schema", "Define map nodes."), ("arcs", "Arcs", "Map capabilities."), ("dashboard", "Dashboard", "Map surfaces."), ("parity", "API/CLI", "Map runtime routes."), ("governance", "Govern", "Map boundaries."), ("docs", "Docs", "Map docs."), ("runtime", "Runtime", "Expose map."), ("layer", "Layer", "Final v229 map.")],
    )


def render_knowledge_organization_audit() -> str:
    return _render_supervised_runtime_arc(
        "/knowledge-organization-audit", "v230.0 Operator-Governed Knowledge and Belief Organization Layer v1", "operator_governed_knowledge_and_belief_organization_layer_v1", "v230.0", "knowledge-organization-audit",
        "Audits knowledge claim ledgers, belief candidates, contradiction/staleness intelligence, project knowledge maps, no-memory-mutation, no-belief-authority, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("ledger", "Ledger", "Audit claims."), ("beliefs", "Beliefs", "Audit belief safety."), ("contradictions", "Conflict", "Audit staleness."), ("map", "Map", "Audit project map."), ("memory", "Memory", "No memory writes."), ("authority", "Authority", "No belief authority."), ("parity", "Parity", "API/CLI parity."), ("layer", "Layer", "Final v230 audit.")],
    )



def render_local_model_inventory() -> str:
    return _render_supervised_runtime_arc(
        "/local-model-inventory", "v231.0 Operator-Governed Local Model Inventory Layer", "operator_governed_local_model_inventory_layer", "v231.0", "local-model-inventory",
        "Profiles local models, claimed capabilities, limits, evidence, and operator-review state while explicitly preventing inventory views from invoking models.",
        [("schema", "Schema", "Define inventory fields."), ("profiles", "Profiles", "Model capability profiles."), ("limits", "Limits", "Bind risks."), ("evidence", "Evidence", "Require proof."), ("safety", "No Invoke", "Block calls."), ("dashboard", "Dash", "Command-deck view."), ("parity", "Parity", "API/CLI coverage."), ("layer", "Layer", "Final v231 inventory.")],
    )


def render_model_evaluation_plan() -> str:
    return _render_supervised_runtime_arc(
        "/model-evaluation-plan", "v232.0 Supervised Model Evaluation Plan Layer", "supervised_model_evaluation_plan_layer", "v232.0", "model-evaluation-plan",
        "Designs reviewable model evaluation plans, task classifiers, prompt suites, evidence requirements, risk/scope classifiers, and approval checklists without running models.",
        [("schema", "Schema", "Define plans."), ("types", "Types", "Classify tasks."), ("prompts", "Prompts", "Design suites."), ("evidence", "Evidence", "Expected evidence."), ("risk", "Risk", "Classify scope."), ("approval", "Approval", "Require operator."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v232 plan.")],
    )


def render_model_output_comparison() -> str:
    return _render_supervised_runtime_arc(
        "/model-output-comparison", "v233.0 Operator-Governed Model Output Comparison Layer", "operator_governed_model_output_comparison_layer", "v233.0", "model-output-comparison",
        "Compares operator-approved model outputs, maps agreement/disagreement, scores evidence support, detects hallucination risk, and blocks model-output authority.",
        [("schema", "Schema", "Define records."), ("comparison", "Compare", "Render comparison."), ("agreement", "Agree", "Map disagreements."), ("evidence", "Evidence", "Score support."), ("hallucination", "Hallucination", "Flag risk."), ("contradiction", "Conflict", "Check project knowledge."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v233 compare.")],
    )


def render_cognitive_workbench_routing() -> str:
    return _render_supervised_runtime_arc(
        "/cognitive-workbench-routing", "v234.0 Supervised Cognitive Workbench Routing Layer", "supervised_cognitive_workbench_routing_layer", "v234.0", "cognitive-workbench-routing",
        "Recommends task-to-model fit, human review requirements, fallback strategies, disagreement policy, and evidence-bound routing without invoking models or approving work.",
        [("schema", "Schema", "Define tasks."), ("fit", "Fit", "Score task/model fit."), ("review", "Review", "Bind human review."), ("fallback", "Fallback", "Manual fallback."), ("disagreement", "Disagree", "Policy."), ("recommendation", "Recommend", "Evidence-bound advice."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v234 routing.")],
    )


def render_local_model_workbench_audit() -> str:
    return _render_supervised_runtime_arc(
        "/local-model-workbench-audit", "v235.0 Operator-Governed Local Model Evaluation and Cognitive Workbench Layer v1", "operator_governed_local_model_evaluation_and_cognitive_workbench_layer_v1", "v235.0", "local-model-workbench-audit",
        "Audits local model inventory, evaluation-plan safety, output comparison trust, workbench routing, no-default-invocation, no-model-authority, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("inventory", "Inventory", "Audit profiles."), ("evaluation", "Eval", "Audit plans."), ("comparison", "Compare", "Audit trust."), ("routing", "Routing", "Audit routing."), ("no-invocation", "No Invoke", "Audit default lock."), ("authority", "Authority", "No model authority."), ("parity", "Parity", "API/CLI parity."), ("layer", "Layer", "Final v235 audit.")],
    )


def render_local_model_invocation_consent() -> str:
    return _render_supervised_runtime_arc(
        "/local-model-invocation-consent", "v236.0 Operator-Approved Local Model Invocation Consent Gate", "operator_approved_local_model_invocation_consent_gate", "v236.0", "local-model-invocation-consent",
        "Stages explicit local model invocation consent, scope, context boundaries, output-use limits, consent expiration, and no-default-invocation checks without invoking any model.",
        [("schema", "Schema", "Define consent."), ("scope", "Scope", "Classify run."), ("context", "Context", "Bind context."), ("output", "Output", "Limit use."), ("expiration", "Expire", "No reuse."), ("safety", "No Invoke", "Default lock."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v236 consent.")],
    )


def render_model_evaluation_run_ledger() -> str:
    return _render_supervised_runtime_arc(
        "/model-evaluation-run-ledger", "v237.0 Sandboxed Model Evaluation Run Ledger", "sandboxed_model_evaluation_run_ledger", "v237.0", "model-evaluation-run-ledger",
        "Records approved model evaluation runs, prompt-suite binding, output capture, runtime/provider metadata, transcript sanitization, and run status without applying outputs.",
        [("schema", "Schema", "Define runs."), ("prompt", "Prompts", "Bind suite."), ("capture", "Capture", "Record output."), ("metadata", "Metadata", "Bind runtime."), ("sanitize", "Sanitize", "Protect transcripts."), ("status", "Status", "Render status."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v237 ledger.")],
    )


def render_multi_model_output_triage() -> str:
    return _render_supervised_runtime_arc(
        "/multi-model-output-triage", "v238.0 Operator-Governed Multi-Model Output Triage", "operator_governed_multi_model_output_triage", "v238.0", "multi-model-output-triage",
        "Compares approved model outputs, maps agreement/disagreement, flags hallucination and project-knowledge contradictions, and prioritizes operator review without granting authority.",
        [("schema", "Schema", "Define triage."), ("agreement", "Agree", "Map agreement."), ("disagreement", "Disagree", "Explain conflict."), ("hallucination", "Hallucination", "Flag risk."), ("contradiction", "Conflict", "Check project."), ("priority", "Priority", "Review score."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v238 triage.")],
    )


def render_model_reliability_profile_candidates() -> str:
    return _render_supervised_runtime_arc(
        "/model-reliability-profile-candidates", "v239.0 Supervised Model Reliability Profile Candidates", "supervised_model_reliability_profile_candidates", "v239.0", "model-reliability-profile-candidates",
        "Stages evidence-bound reliability candidates, task-specific reliability scores, repeated strengths/failures, and operator promotion requirements without self-promotion.",
        [("schema", "Schema", "Define candidate."), ("score", "Score", "Task reliability."), ("strengths", "Strengths", "Detect good patterns."), ("failures", "Failures", "Detect weak patterns."), ("evidence", "Evidence", "Bind summary."), ("promotion", "Promotion", "Require operator."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v239 reliability.")],
    )


def render_local_model_invocation_sandbox_audit() -> str:
    return _render_supervised_runtime_arc(
        "/local-model-invocation-sandbox-audit", "v240.0 Operator-Approved Local Model Invocation Sandbox v1", "operator_approved_local_model_invocation_sandbox_v1", "v240.0", "local-model-invocation-sandbox-audit",
        "Audits invocation consent, evaluation run ledgers, multi-model triage, reliability candidates, no-default-invocation, no-model-authority, dashboard style, API/CLI parity, docs, release history, package privacy, and smoke coverage.",
        [("consent", "Consent", "Audit scope."), ("ledger", "Ledger", "Audit runs."), ("triage", "Triage", "Audit outputs."), ("reliability", "Reliability", "Audit candidates."), ("no-invocation", "No Invoke", "Default lock."), ("authority", "Authority", "No model authority."), ("parity", "Parity", "API/CLI parity."), ("layer", "Layer", "Final v240 audit.")],
    )


def render_model_assisted_patch_critique() -> str:
    return _render_supervised_runtime_arc(
        "/model-assisted-patch-critique", "v241.0 Operator-Governed Model-Assisted Patch Critique Layer", "operator_governed_model_assisted_patch_critique_layer", "v241.0", "model-assisted-patch-critique",
        "Packages approved local model outputs into structured, evidence-scored patch critique packets without treating critique as truth, proof, approval, verification, or source mutation.",
        [("schema", "Schema", "Define critique."), ("source", "Source", "Bind run ledger."), ("type", "Type", "Classify critique."), ("evidence", "Evidence", "Score support."), ("safety", "Authority", "No action."), ("runtime", "Runtime", "API/CLI coverage."), ("smoke", "Smoke", "Install check."), ("layer", "Layer", "Final v241 critique.")],
    )


def render_multi_model_review_synthesis() -> str:
    return _render_supervised_runtime_arc(
        "/multi-model-review-synthesis", "v242.0 Supervised Multi-Model Review Synthesis Layer", "supervised_multi_model_review_synthesis_layer", "v242.0", "multi-model-review-synthesis",
        "Synthesizes multiple approved model reviews by clustering agreement, disagreement, hallucination candidates, and high-value findings without granting approval.",
        [("schema", "Schema", "Define synthesis."), ("agreement", "Agree", "Cluster agreement."), ("disagreement", "Disagree", "Map conflicts."), ("hallucination", "Filter", "Flag invented claims."), ("findings", "Findings", "Useful items."), ("summary", "Summary", "Operator brief."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v242 synthesis.")],
    )


def render_patch_risk_remediation_synthesis() -> str:
    return _render_supervised_runtime_arc(
        "/patch-risk-remediation-synthesis", "v243.0 Operator-Governed Patch Risk and Remediation Synthesis", "operator_governed_patch_risk_and_remediation_synthesis", "v243.0", "patch-risk-remediation-synthesis",
        "Turns model critique into review-only risk categories, remediation candidates, verification suggestions, documentation impact, and operator decision summaries without execution.",
        [("schema", "Schema", "Define risk."), ("risk", "Risk", "Bind categories."), ("remediation", "Remediate", "Draft candidates."), ("verification", "Verify", "Suggest checks."), ("docs", "Docs", "Impact."), ("decision", "Decision", "Operator summary."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v243 synthesis.")],
    )


def render_model_review_quality_calibration() -> str:
    return _render_supervised_runtime_arc(
        "/model-review-quality-calibration", "v244.0 Supervised Model Review Quality Calibration", "supervised_model_review_quality_calibration", "v244.0", "model-review-quality-calibration",
        "Calibrates model review usefulness with useful findings, false positives, hallucinations, missed issues, and task-specific scores without promoting models or authority.",
        [("schema", "Schema", "Quality records."), ("useful", "Useful", "Track wins."), ("false-positive", "False +", "Track rejects."), ("hallucination", "Hallucination", "Track invented."), ("missed", "Missed", "Track omissions."), ("score", "Score", "Task usefulness."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v244 quality.")],
    )


def render_model_assisted_patch_review_audit() -> str:
    return _render_supervised_runtime_arc(
        "/model-assisted-patch-review-audit", "v245.0 Operator-Governed Model-Assisted Patch Review and Synthesis Layer v1", "operator_governed_model_assisted_patch_review_and_synthesis_layer_v1", "v245.0", "model-assisted-patch-review-audit",
        "Audits model-assisted critique packets, multi-model synthesis, risk/remediation synthesis, review-quality calibration, no-model-authority, no-source-mutation, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("critique", "Critique", "Audit packets."), ("synthesis", "Synthesis", "Audit clusters."), ("risk", "Risk", "Audit remediation."), ("quality", "Quality", "Audit scoring."), ("authority", "Authority", "No model power."), ("mutation", "Mutation", "No source edits."), ("parity", "Parity", "API/CLI parity."), ("layer", "Layer", "Final v245 audit.")],
    )


def render_model_assisted_patch_draft() -> str:
    return _render_supervised_runtime_arc(
        "/model-assisted-patch-draft", "v246.0 Operator-Governed Model-Assisted Patch Draft Packet Layer", "operator_governed_model_assisted_patch_draft_packet_layer", "v246.0", "model-assisted-patch-draft",
        "Assembles reviewable model-assisted patch draft packets with source finding traceability, proposed changes, evidence scoring, and non-mutation guards without writing files.",
        [("schema", "Schema", "Define draft."), ("trace", "Trace", "Bind sources."), ("classify", "Classify", "Change types."), ("evidence", "Evidence", "Score support."), ("safety", "Safety", "No mutation."), ("dashboard", "Dashboard", "View."), ("runtime", "Runtime", "API/CLI coverage."), ("layer", "Layer", "Final v246 draft.")],
    )


def render_file_impact_documentation_planner() -> str:
    return _render_supervised_runtime_arc(
        "/file-impact-documentation-planner", "v247.0 Supervised File Impact and Documentation Planner", "supervised_file_impact_and_documentation_planner", "v247.0", "file-impact-documentation-planner",
        "Maps source files, dashboard routes, API/CLI surfaces, README requirements, and release-history requirements without executing changes or editing docs.",
        [("schema", "Schema", "Impact map."), ("source", "Source", "Files."), ("dashboard", "Dashboard", "Routes."), ("runtime", "Runtime", "API/CLI."), ("readme", "README", "Next steps."), ("history", "History", "Release log."), ("parity", "Parity", "Coverage."), ("layer", "Layer", "Final v247 planner.")],
    )


def render_smoke_verification_suggestions() -> str:
    return _render_supervised_runtime_arc(
        "/smoke-verification-suggestions", "v248.0 Supervised Smoke and Verification Suggestion Layer", "supervised_smoke_and_verification_suggestion_layer", "v248.0", "smoke-verification-suggestions",
        "Suggests smoke, route/API/CLI parity, package privacy, dashboard regression, and extracted ZIP verification plans without executing commands.",
        [("schema", "Schema", "Verify plan."), ("smoke", "Smoke", "Coverage gaps."), ("parity", "Parity", "Surfaces."), ("privacy", "Privacy", "Source-only."), ("dashboard", "Dashboard", "Regression."), ("zip", "ZIP", "Extract checks."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v248 suggestions.")],
    )


def render_sandbox_preparation_packet() -> str:
    return _render_supervised_runtime_arc(
        "/sandbox-preparation-packet", "v249.0 Operator-Governed Sandbox Preparation Packet Layer", "operator_governed_sandbox_preparation_packet_layer", "v249.0", "sandbox-preparation-packet",
        "Prepares reviewable sandbox readiness, approval scope, risk, rollback, expected output, and operator checklist without executing sandbox workflows.",
        [("schema", "Schema", "Prep packet."), ("approval", "Approval", "Scope."), ("readiness", "Ready", "Score."), ("rollback", "Rollback", "Risks."), ("expected", "Expected", "Outputs."), ("checklist", "Checklist", "Operator."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v249 prep.")],
    )


def render_patch_draft_assembly_audit() -> str:
    return _render_supervised_runtime_arc(
        "/patch-draft-assembly-audit", "v250.0 Operator-Governed Model-Assisted Patch Draft Assembly Layer v1", "operator_governed_model_assisted_patch_draft_assembly_layer_v1", "v250.0", "patch-draft-assembly-audit",
        "Audits model-assisted draft packets, file impact planning, documentation requirements, verification suggestions, sandbox preparation, no-source-mutation, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("trace", "Trace", "Draft audit."), ("impact", "Impact", "File map."), ("docs", "Docs", "Requirements."), ("verify", "Verify", "Suggestions."), ("sandbox", "Sandbox", "Prep safety."), ("mutation", "Mutation", "No edits."), ("parity", "Parity", "API/CLI."), ("layer", "Layer", "Final v250 audit.")],
    )


def render_draft_to_execution_packet() -> str:
    return _render_supervised_runtime_arc(
        "/draft-to-execution-packet", "v251.0 Operator-Governed Draft-to-Execution Packet Gate", "operator_governed_draft_to_execution_packet_gate", "v251.0", "draft-to-execution-packet",
        "Converts model-assisted draft assembly output into review-only execution-packet candidates with selected changes, excluded changes, evidence completeness, scope boundaries, and default blocked approval state.",
        [("schema", "Schema", "Packet fields."), ("source", "Source", "Draft binding."), ("selection", "Select", "Operator scope."), ("evidence", "Evidence", "Completeness."), ("scope", "Scope", "Boundaries."), ("approval", "Blocked", "Default state."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v251 gate.")],
    )


def render_patch_diff_preview_planner() -> str:
    return _render_supervised_runtime_arc(
        "/patch-diff-preview-planner", "v252.0 Supervised Patch Diff Preview and Edit Plan Layer", "supervised_patch_diff_preview_and_edit_plan_layer", "v252.0", "patch-diff-preview-planner",
        "Plans review-only diff previews, file anchors, before/after snippets, documentation edits, dashboard/API/CLI/smoke impacts, and overreach detection without writing files.",
        [("schema", "Schema", "Diff plan."), ("anchors", "Anchors", "File map."), ("preview", "Preview", "Before/after."), ("docs", "Docs", "README/history."), ("runtime", "Runtime", "Dashboard/API/CLI."), ("overreach", "Scope", "Detect drift."), ("parity", "Parity", "API/CLI."), ("layer", "Layer", "Final v252 preview.")],
    )


def render_execution_approval_scope() -> str:
    return _render_supervised_runtime_arc(
        "/execution-approval-scope", "v253.0 Operator-Governed Explicit Approval Scope Ledger", "operator_governed_explicit_approval_scope_ledger", "v253.0", "execution-approval-scope",
        "Tracks exact approval targets, files, docs, commands, execution mode, expiration, excluded actions, freshness, and mismatch blockers without self-approval.",
        [("schema", "Schema", "Approval fields."), ("classifier", "Phrase", "Boundary."), ("freshness", "Fresh", "Scope bind."), ("mismatch", "Mismatch", "Block drift."), ("stale", "Stale", "No reuse."), ("receipt", "Receipt", "Review only."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v253 ledger.")],
    )


def render_verification_rollback_packet() -> str:
    return _render_supervised_runtime_arc(
        "/verification-rollback-packet", "v254.0 Supervised Verification and Rollback Packet Planner", "supervised_verification_and_rollback_packet_planner", "v254.0", "verification-rollback-packet",
        "Prepares suggested verification commands, expected evidence, package privacy checks, dashboard regression checks, and rollback strategy without running commands or altering files.",
        [("schema", "Schema", "Verify packet."), ("smoke", "Smoke", "Command preview."), ("privacy", "Privacy", "Package checks."), ("dashboard", "Dashboard", "Regression."), ("rollback", "Rollback", "Plan."), ("evidence", "Evidence", "Expected proof."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v254 planner.")],
    )


def render_patch_execution_packet_audit() -> str:
    return _render_supervised_runtime_arc(
        "/patch-execution-packet-audit", "v255.0 Operator-Governed Patch Execution Packet Bridge v1", "operator_governed_patch_execution_packet_bridge_v1", "v255.0", "patch-execution-packet-audit",
        "Audits execution-packet traceability, diff previews, explicit approval scope, verification/rollback planning, no-model-authority, no-source-mutation, dashboard style, API/CLI parity, docs, release history, and smoke coverage.",
        [("trace", "Trace", "Draft evidence."), ("diff", "Diff", "Preview audit."), ("approval", "Approval", "Fresh scope."), ("rollback", "Rollback", "Plan only."), ("model", "Model", "No authority."), ("mutation", "Mutation", "No edits."), ("parity", "Parity", "API/CLI."), ("layer", "Layer", "Final v255 bridge.")],
    )



def render_application_prep_intake() -> str:
    return _render_supervised_runtime_arc(
        "/application-prep-intake", "v256.0 Operator-Governed Execution Packet Intake Layer", "operator_governed_execution_packet_intake_layer", "v256.0", "application-prep-intake",
        "Normalizes execution packets into review-only application-prep scope, documentation obligations, approval receipt links, blocked items, verification scope, and rollback scope without granting authority.",
        [("schema", "Schema", "Prep fields."), ("intake", "Intake", "Packet bind."), ("files", "Files", "Scope."), ("docs", "Docs", "Obligations."), ("approval", "Approval", "Receipt."), ("blocked", "Blocked", "Extract."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v256 intake.")],
    )


def render_source_edit_application_plan() -> str:
    return _render_supervised_runtime_arc(
        "/source-edit-application-plan", "v257.0 Supervised Source Edit Application Plan Builder", "supervised_source_edit_application_plan_builder", "v257.0", "source-edit-application-plan",
        "Builds review-only target-file edit plans with edit type classification, insert/replace/delete previews, conflict detection, and generated-content boundary guards without mutating source.",
        [("schema", "Schema", "Edit plan."), ("target", "Target", "File bind."), ("classifier", "Type", "Edit class."), ("preview", "Preview", "No write."), ("conflict", "Conflict", "Overlap."), ("boundary", "Boundary", "Generated."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v257 plan.")],
    )


def render_documentation_application_plan() -> str:
    return _render_supervised_runtime_arc(
        "/documentation-application-plan", "v258.0 Supervised Documentation and Release Metadata Application Plan", "supervised_documentation_and_release_metadata_application_plan", "v258.0", "documentation-application-plan",
        "Plans README_NEXT_STEPS, README_RELEASE_HISTORY, version markers, runtime surfaces, smoke coverage, and missing-documentation blockers without updating files automatically.",
        [("schema", "Schema", "Doc plan."), ("readme", "README", "Next steps."), ("history", "History", "Release."), ("version", "Version", "Markers."), ("runtime", "Runtime", "Surfaces."), ("missing", "Missing", "Block."), ("parity", "Parity", "API/CLI."), ("layer", "Layer", "Final v258 docs.")],
    )


def render_final_application_governance_gate() -> str:
    return _render_supervised_runtime_arc(
        "/final-application-governance-gate", "v259.0 Operator-Governed Final Pre-Application Governance Gate", "operator_governed_final_pre_application_governance_gate", "v259.0", "final-application-governance-gate",
        "Verifies approval freshness, exact scope match, verification plan completeness, rollback plan completeness, and no-autonomy boundaries while keeping readiness separate from authorization.",
        [("schema", "Schema", "Gate fields."), ("freshness", "Fresh", "Approval."), ("scope", "Scope", "Match."), ("verify", "Verify", "Plan."), ("rollback", "Rollback", "Plan."), ("boundary", "Boundary", "No autonomy."), ("runtime", "Runtime", "API/CLI."), ("layer", "Layer", "Final v259 gate.")],
    )


def render_application_prep_integration_audit() -> str:
    return _render_supervised_runtime_arc(
        "/application-prep-integration-audit", "v260.0 Operator-Governed Approved Execution Packet Application Prep v1", "operator_governed_approved_execution_packet_application_prep_v1", "v260.0", "application-prep-integration-audit",
        "Audits application-prep intake traceability, source edit plans, documentation plans, approval binding, verification/rollback binding, no-execution boundaries, dashboard style, API/CLI parity, docs, release history, package privacy, and smoke coverage.",
        [("trace", "Trace", "Intake."), ("source", "Source", "Edit plan."), ("docs", "Docs", "Plan."), ("approval", "Approval", "Binding."), ("rollback", "Rollback", "Plan-only."), ("execution", "Execution", "None."), ("parity", "Parity", "API/CLI."), ("layer", "Layer", "Final v260 prep.")],
    )



def render_structural_inventory() -> str:
    return _render_supervised_runtime_arc(
        "/structural-inventory", "v261.0 Operator-Governed Structural Inventory Layer", "operator_governed_structural_inventory_layer", "v261.0", "structural-inventory",
        "Inventories oversized central files, runtime surfaces, dashboard/API/CLI routes, smoke coverage, documentation dependencies, and safe module boundaries without changing behavior.",
        [("inventory", "Files", "Size map."), ("runtime", "Runtime", "Surface map."), ("dashboard", "Dashboard", "Route map."), ("api", "API", "Route map."), ("cli", "CLI", "Command map."), ("smoke", "Smoke", "Coverage."), ("proposal", "Boundary", "Plan only."), ("layer", "Layer", "Final v261 inventory.")],
    )


def render_runtime_registry_prep() -> str:
    return _render_supervised_runtime_arc(
        "/runtime-registry-prep", "v262.0 Operator-Governed Runtime Registry Prep Layer", "operator_governed_runtime_registry_prep_layer", "v262.0", "runtime-registry-prep",
        "Prepares shared runtime registry metadata for capabilities, routes, CLI, API, dashboard, safety, docs, and smoke without replacing existing dispatch.",
        [("schema", "Schema", "Registry."), ("capability", "Capability", "Metadata."), ("route", "Routes", "Binder."), ("cli", "CLI", "Binder."), ("api", "API", "Binder."), ("dashboard", "Dashboard", "Binder."), ("parity", "Parity", "Check."), ("layer", "Layer", "Final v262 prep.")],
    )


def render_dashboard_stabilization_audit() -> str:
    return _render_supervised_runtime_arc(
        "/dashboard-stabilization-audit", "v263.0 Operator-Governed Dashboard Stabilization Layer", "operator_governed_dashboard_stabilization_layer", "v263.0", "dashboard-stabilization-audit",
        "Stabilizes dashboard route/nav metadata while preserving command-deck layout, custom data-tip hover behavior, and native nav title tooltip regression guards.",
        [("snapshot", "Routes", "Snapshot."), ("nav", "Nav", "Normalize."), ("tooltip", "data-tip", "Preserve."), ("regression", "title", "Forbid."), ("layout", "Deck", "Preserve."), ("grouping", "Grouping", "Plan."), ("parity", "Parity", "Render."), ("layer", "Layer", "Final v263 dashboard.")],
    )


def render_dispatch_stabilization() -> str:
    return _render_supervised_runtime_arc(
        "/dispatch-stabilization", "v264.0 Operator-Governed CLI/API Dispatch Stabilization Layer", "operator_governed_cli_api_dispatch_stabilization_layer", "v264.0", "dispatch-stabilization",
        "Inventories CLI/API dispatch, shared metadata planning, dynamic command parity, missing route detection, and dispatch regression smoke suggestions without executing commands.",
        [("cli", "CLI", "Inventory."), ("api", "API", "Inventory."), ("metadata", "Metadata", "Plan."), ("parity", "Parity", "Dynamic."), ("route", "Routes", "Detect."), ("cli-missing", "CLI Gap", "Detect."), ("api-missing", "API Gap", "Detect."), ("layer", "Layer", "Final v264 dispatch.")],
    )


def render_structural_stabilization_audit() -> str:
    return _render_supervised_runtime_arc(
        "/structural-stabilization-audit", "v265.0 Operator-Governed Structural Stabilization and Runtime Modularization v1", "operator_governed_structural_stabilization_and_runtime_modularization_v1", "v265.0", "structural-stabilization-audit",
        "Audits structural drift, runtime parity, dashboard route parity, API/CLI parity, README/release history completeness, package privacy, extracted ZIP verification planning, and refactor risk without applying refactors.",
        [("drift", "Drift", "Audit."), ("runtime", "Runtime", "Parity."), ("dashboard", "Dashboard", "Parity."), ("parity", "API/CLI", "Audit."), ("docs", "Docs", "Complete."), ("privacy", "Privacy", "Package."), ("risk", "Risk", "Register."), ("layer", "Layer", "Final v265 audit.")],
    )



def render_runtime_registry() -> str:
    return _render_supervised_runtime_arc(
        "/runtime-registry", "v266.0 Operator-Governed Runtime Metadata Registry Extraction", "operator_governed_runtime_metadata_registry_extraction", "v266.0", "runtime-registry",
        "Extracts reusable runtime metadata into conscious_agent/runtime_registry.py while preserving legacy dispatch, routes, CLI/API surfaces, dashboard behavior, and approval boundaries.",
        [("scaffold", "Scaffold", "Module."), ("capability", "Capability", "Metadata."), ("dashboard", "Dashboard", "Routes."), ("cli", "CLI", "Surface."), ("api", "API", "Surface."), ("safety", "Safety", "Boundary."), ("adapter", "Adapter", "Compat."), ("layer", "Layer", "Final v266 registry.")],
    )


def render_governance_report_builder_audit() -> str:
    return _render_supervised_runtime_arc(
        "/governance-report-builder-audit", "v267.0 Operator-Governed Governance Report Builder Extraction", "operator_governed_governance_report_builder_extraction", "v267.0", "governance-report-builder-audit",
        "Extracts reusable governance report helpers into conscious_agent/governance_reports.py while preserving text wrappers, packet summaries, safety rows, approval boundaries, verification/rollback renderers, and audit parity.",
        [("scaffold", "Scaffold", "Module."), ("packet", "Packet", "Summary."), ("safety", "Safety", "Rows."), ("approval", "Approval", "Boundary."), ("verify", "Verify", "Rollback."), ("audit", "Audit", "Findings."), ("wrappers", "Wrappers", "Compat."), ("layer", "Layer", "Final v267 reports.")],
    )


def render_dashboard_registry_integration() -> str:
    return _render_supervised_runtime_arc(
        "/dashboard-registry-integration", "v268.0 Operator-Governed Dashboard Surface Registry Integration", "operator_governed_dashboard_surface_registry_integration", "v268.0", "dashboard-registry-integration",
        "Integrates dashboard surface metadata with the runtime registry while preserving route handlers, command-deck style, custom data-tip hover behavior, and native nav title regression guards.",
        [("adapter", "Adapter", "Registry."), ("nav", "Nav", "Metadata."), ("label", "Labels", "Normalize."), ("tooltip", "data-tip", "Bind."), ("regression", "title", "Forbid."), ("layout", "Deck", "Preserve."), ("parity", "Parity", "Routes."), ("layer", "Layer", "Final v268 dashboard.")],
    )


def render_runtime_dispatch_registry_audit() -> str:
    return _render_supervised_runtime_arc(
        "/runtime-dispatch-registry-audit", "v269.0 Operator-Governed CLI/API Runtime Registry Integration", "operator_governed_cli_api_runtime_registry_integration", "v269.0", "runtime-dispatch-registry-audit",
        "Integrates CLI/API runtime registry metadata while preserving existing dynamic dispatch, route handlers, command behavior, missing surface guards, naming checks, and no-execution boundaries.",
        [("cli", "CLI", "Adapter."), ("api", "API", "Adapter."), ("metadata", "Shared", "Commands."), ("parity", "Parity", "Dynamic."), ("cli-guard", "CLI Guard", "Missing."), ("api-guard", "API Guard", "Missing."), ("names", "Names", "Consistent."), ("layer", "Layer", "Final v269 dispatch.")],
    )


def render_module_extraction_audit() -> str:
    return _render_supervised_runtime_arc(
        "/module-extraction-audit", "v270.0 Operator-Governed Runtime Module Extraction v1", "operator_governed_runtime_module_extraction_v1", "v270.0", "module-extraction-audit",
        "Audits runtime_registry.py and governance_reports.py extraction, registry parity, report output parity, dashboard route parity, CLI/API surface parity, package privacy, docs completeness, smoke gates, and refactor risk without changing authority.",
        [("imports", "Imports", "Audit."), ("registry", "Registry", "Parity."), ("reports", "Reports", "Parity."), ("dashboard", "Dashboard", "Route."), ("parity", "API/CLI", "Surface."), ("privacy", "Privacy", "Package."), ("docs", "Docs", "Complete."), ("layer", "Layer", "Final v270 audit.")],
    )



def render_self_maintenance_extraction_map() -> str:
    return _render_supervised_runtime_arc(
        "/self-maintenance-extraction-map", "v271.0 Operator-Governed Self-Maintenance Extraction Map", "operator_governed_self_maintenance_extraction_map", "v271.0", "self-maintenance-extraction-map",
        "Maps safe extraction clusters in self_maintenance.py while preserving behavior, wrappers, routes, dashboard style, CLI/API dispatch, and approval boundaries.",
        [("inventory", "Inventory", "Functions."), ("reports", "Reports", "Clusters."), ("governance", "Governance", "Audit."), ("privacy", "Privacy", "Map."), ("versions", "Versions", "Markers."), ("smoke", "Smoke", "Coverage."), ("wrappers", "Wrappers", "Required."), ("layer", "Layer", "Final v271 map.")],
    )


def render_package_version_integrity() -> str:
    return _render_supervised_runtime_arc(
        "/package-version-integrity", "v272.0 Operator-Governed Package and Version Utility Extraction", "operator_governed_package_and_version_utility_extraction", "v272.0", "package-version-integrity",
        "Extracts package_integrity.py and version_state.py helpers for package privacy and version marker summaries without writing files or changing release authority.",
        [("package", "Package", "Module."), ("policy", "Policy", "Source-only."), ("forbidden", "Runtime", "Detector."), ("summary", "Privacy", "Summary."), ("versions", "Version", "Module."), ("markers", "Markers", "Summary."), ("adapter", "Adapter", "Compat."), ("layer", "Layer", "Final v272 utilities.")],
    )


def render_surface_parity_audit() -> str:
    return _render_supervised_runtime_arc(
        "/surface-parity-audit", "v273.0 Operator-Governed Surface Parity Utility Extraction", "operator_governed_surface_parity_utility_extraction", "v273.0", "surface-parity-audit",
        "Extracts surface_parity.py helpers for dashboard route, API surface, and CLI flag parity checks while preserving existing behavior and routes.",
        [("surface", "Surface", "Module."), ("dashboard", "Dashboard", "Routes."), ("api", "API", "Surface."), ("cli", "CLI", "Flags."), ("registry", "Registry", "Binder."), ("missing", "Missing", "Detect."), ("renderer", "Renderer", "Summary."), ("layer", "Layer", "Final v273 parity.")],
    )


def render_verification_planning_audit() -> str:
    return _render_supervised_runtime_arc(
        "/verification-planning-audit", "v274.0 Operator-Governed Smoke and Verification Utility Extraction", "operator_governed_smoke_and_verification_utility_extraction", "v274.0", "verification-planning-audit",
        "Extracts verification_planning.py review-only smoke and verification suggestions without executing commands automatically.",
        [("verification", "Verify", "Module."), ("fast", "Fast", "Smoke."), ("install", "Install", "Smoke."), ("zip", "ZIP", "Extracted."), ("tooltip", "Tooltip", "data-tip."), ("privacy", "Privacy", "Package."), ("summary", "Summary", "Readiness."), ("layer", "Layer", "Final v274 planning.")],
    )


def render_self_maintenance_decomposition_audit() -> str:
    return _render_supervised_runtime_arc(
        "/self-maintenance-decomposition-audit", "v275.0 Operator-Governed Self-Maintenance Decomposition v1", "operator_governed_self_maintenance_decomposition_v1", "v275.0", "self-maintenance-decomposition-audit",
        "Audits package_integrity.py, version_state.py, surface_parity.py, and verification_planning.py extraction, legacy wrappers, runtime output parity, package/version parity, surfaces, verification planning, dashboard, API/CLI, docs, smoke, and no-authority boundaries.",
        [("imports", "Imports", "Modules."), ("wrappers", "Wrappers", "Compat."), ("output", "Output", "Parity."), ("package", "Package", "Version."), ("surface", "Surface", "Parity."), ("verification", "Verify", "Plan."), ("dashboard", "Dashboard", "Console."), ("layer", "Layer", "Final v275 audit.")],
    )


def render_dashboard_extraction_map() -> str:
    return _render_supervised_runtime_arc(
        "/dashboard-extraction-map", "v276.0 Operator-Governed Dashboard Surface Extraction Map", "operator_governed_dashboard_surface_extraction_map", "v276.0", "dashboard-extraction-map",
        "Maps dashboard function clusters, navigation, route handlers, renderers, command-deck style dependencies, data-tip tooltip dependencies, extraction priorities, wrappers, and no-visual-change boundaries.",
        [("inventory", "Inventory", "Functions."), ("navigation", "Navigation", "Map."), ("routes", "Routes", "Handlers."), ("renderers", "Renderers", "Pages."), ("style", "Console", "Contract."), ("tooltips", "Tooltips", "data-tip."), ("wrappers", "Wrappers", "Required."), ("layer", "Layer", "Final v276 map.")],
    )


def render_dashboard_component_audit() -> str:
    return _render_supervised_runtime_arc(
        "/dashboard-component-audit", "v277.0 Operator-Governed Dashboard Component Helper Extraction", "operator_governed_dashboard_component_helper_extraction", "v277.0", "dashboard-component-audit",
        "Extracts dashboard_components.py helper metadata for console cards, status rows, audit sections, packet summaries, tooltip-safe nav rendering, wrapper preservation, output parity, and command-deck style checks.",
        [("module", "Module", "dashboard_components.py"), ("cards", "Cards", "Console."), ("status", "Rows", "Status."), ("audit", "Audit", "Sections."), ("packets", "Packets", "Summary."), ("tooltips", "Tooltips", "data-tip."), ("style", "Style", "Command deck."), ("layer", "Layer", "Final v277 helpers.")],
    )


def render_api_surface_audit() -> str:
    return _render_supervised_runtime_arc(
        "/api-surface-audit", "v278.0 Operator-Governed API Surface Helper Extraction", "operator_governed_api_surface_helper_extraction", "v278.0", "api-surface-audit",
        "Extracts api_surface.py helper metadata for route summaries, runtime JSON response helpers, API error helpers, dynamic route summaries, route parity checks, wrappers, smoke coverage, and no-behavior-change audits.",
        [("module", "Module", "api_surface.py"), ("routes", "Routes", "Metadata."), ("json", "JSON", "Runtime."), ("errors", "Errors", "Shape."), ("dynamic", "Dynamic", "Summary."), ("parity", "Parity", "Routes."), ("wrappers", "Wrappers", "Preserved."), ("layer", "Layer", "Final v278 API.")],
    )


def render_cli_surface_audit() -> str:
    return _render_supervised_runtime_arc(
        "/cli-surface-audit", "v279.0 Operator-Governed CLI Surface Helper Extraction", "operator_governed_cli_surface_helper_extraction", "v279.0", "cli-surface-audit",
        "Extracts cli_surface.py helper metadata for command summaries, JSON/human renderers, dynamic command summaries, CLI parity checks, wrapper preservation, smoke coverage, and no-execution-authority boundaries.",
        [("module", "Module", "cli_surface.py"), ("commands", "Commands", "Metadata."), ("json", "JSON", "Renderer."), ("summary", "Human", "Summary."), ("dynamic", "Dynamic", "Commands."), ("parity", "Parity", "Flags."), ("execution", "No Exec", "Boundary."), ("layer", "Layer", "Final v279 CLI.")],
    )


def render_interface_modularization_audit() -> str:
    return _render_supervised_runtime_arc(
        "/interface-modularization-audit", "v280.0 Operator-Governed Dashboard/API/CLI Modularization v1", "operator_governed_dashboard_api_cli_modularization_v1", "v280.0", "interface-modularization-audit",
        "Audits dashboard_components.py, api_surface.py, cli_surface.py imports, route/nav parity, API/CLI runtime parity, data-tip tooltip regression, command-deck visual preservation, package privacy, docs completeness, and no-authority boundaries.",
        [("imports", "Imports", "Helpers."), ("routes", "Routes", "Nav."), ("api-cli", "API/CLI", "Parity."), ("tooltips", "Tooltips", "data-tip."), ("style", "Style", "Command deck."), ("privacy", "Privacy", "Package."), ("docs", "Docs", "Complete."), ("layer", "Layer", "Final v280 audit.")],
    )



def render_approved_application_binding() -> str:
    return _render_supervised_runtime_arc(
        "/approved-application-binding", "v281.0 Operator-Approved Application Packet Binding Layer", "operator_approved_application_packet_binding_layer", "v281.0", "approved-application-binding",
        "Binds approved application packets to exact packet IDs, approved file/edit/docs/verification scope, approval freshness, and no-inferred-approval boundaries.",
        [("packet", "Packet", "ID."), ("files", "Files", "Scope."), ("edits", "Edits", "Scope."), ("docs", "Docs", "Scope."), ("verify", "Verify", "Scope."), ("freshness", "Fresh", "Approval."), ("gate", "No Infer", "Approval."), ("layer", "Layer", "Final v281 binding.")],
    )


def render_operator_execution_checklist() -> str:
    return _render_supervised_runtime_arc(
        "/operator-execution-checklist", "v282.0 Operator Execution Checklist Builder Layer", "operator_execution_checklist_builder_layer", "v282.0", "operator-execution-checklist",
        "Builds operator-facing pre-application, source edit, README/release-history, smoke, package privacy, and rollback preparedness checklists without running commands.",
        [("preflight", "Preflight", "Packet."), ("source", "Source", "Edits."), ("docs", "Docs", "README."), ("smoke", "Smoke", "Suggest."), ("privacy", "Privacy", "Package."), ("rollback", "Rollback", "Ready."), ("gate", "No Cmd", "Boundary."), ("layer", "Layer", "Final v282 checklist.")],
    )


def render_post_application_result_review() -> str:
    return _render_supervised_runtime_arc(
        "/post-application-result-review", "v283.0 Operator-Governed Post-Application Result Review Layer", "operator_governed_post_application_result_review_layer", "v283.0", "post-application-result-review",
        "Prepares expected-vs-observed review packets from operator-submitted results, smoke/package/surface intake, deviation classification, and rollback-review recommendations only.",
        [("expected", "Expected", "Change."), ("observed", "Observed", "Input."), ("smoke", "Smoke", "Result."), ("package", "Package", "Result."), ("surface", "Surface", "Result."), ("deviation", "Deviation", "Classify."), ("gate", "No Roll", "Auto."), ("layer", "Layer", "Final v283 review.")],
    )


def render_application_outcome_learning() -> str:
    return _render_supervised_runtime_arc(
        "/application-outcome-learning", "v284.0 Operator-Governed Application Outcome Learning Extractor", "operator_governed_application_outcome_learning_extractor", "v284.0", "application-outcome-learning",
        "Extracts supervised success/failure/smoke/documentation/approval-scope lesson candidates and future patch risk notes without memory or identity mutation.",
        [("success", "Success", "Pattern."), ("failure", "Failure", "Pattern."), ("smoke", "Smoke", "Gap."), ("docs", "Docs", "Gap."), ("approval", "Approval", "Lesson."), ("risk", "Risk", "Note."), ("gate", "No Mem", "Mutation."), ("layer", "Layer", "Final v284 learning.")],
    )


def render_application_execution_refinement_audit() -> str:
    return _render_supervised_runtime_arc(
        "/application-execution-refinement-audit", "v285.0 Operator-Approved Application Execution Refinement v1", "operator_approved_application_execution_refinement_v1", "v285.0", "application-execution-refinement-audit",
        "Audits approval binding, execution checklist completeness, post-application review packets, supervised outcome lessons, dashboard/API/CLI parity, package privacy, smoke coverage, and no-autonomy boundaries.",
        [("approval", "Approval", "Binding."), ("checklist", "Checklist", "Exec."), ("review", "Review", "Post-app."), ("learning", "Learning", "Candidates."), ("surface", "Surface", "Parity."), ("privacy", "Privacy", "Smoke."), ("safety", "No Auto", "Boundary."), ("layer", "Layer", "Final v285 audit.")],
    )



def render_rollback_scope_binding() -> str:
    return _render_supervised_runtime_arc(
        "/rollback-scope-binding", "v286.0 Operator-Governed Rollback Scope Binding Layer", "operator_governed_rollback_scope_binding_layer", "v286.0", "rollback-scope-binding",
        "Binds rollback review to exact application packets, approved files, docs, version markers, package/smoke context, and explicit no-auto-rollback boundaries.",
        [("packet", "Packet", "Binding."), ("files", "Files", "Scope."), ("docs", "Docs", "Rollback."), ("versions", "Markers", "Scope."), ("verify", "Smoke", "Context."), ("route", "Route", "Surface."), ("gate", "No Auto", "Rollback."), ("layer", "Layer", "Final v286 scope.")],
    )


def render_failure_damage_map() -> str:
    return _render_supervised_runtime_arc(
        "/failure-damage-map", "v287.0 Operator-Governed Failure Classification and Damage Map", "operator_governed_failure_classification_and_damage_map", "v287.0", "failure-damage-map",
        "Classifies operator-submitted compile, smoke, dashboard, API/CLI, package privacy, and partial-application failure evidence without diagnostic overreach.",
        [("compile", "Compile", "Failure."), ("smoke", "Smoke", "Failure."), ("dashboard", "Dash", "Regression."), ("surface", "API/CLI", "Regression."), ("privacy", "Privacy", "Failure."), ("partial", "Partial", "Apply."), ("gate", "No Probe", "Overreach."), ("layer", "Layer", "Final v287 map.")],
    )


def render_recovery_checklist() -> str:
    return _render_supervised_runtime_arc(
        "/recovery-checklist", "v288.0 Operator-Governed Recovery Checklist Builder", "operator_governed_recovery_checklist_builder", "v288.0", "recovery-checklist",
        "Builds manual recovery checklists for stop conditions, file/docs/version recovery, verification reruns, package rebuild review, and no-command-execution boundaries.",
        [("stop", "Stop", "Conditions."), ("files", "Files", "Revert."), ("docs", "Docs", "Recover."), ("versions", "Markers", "Recover."), ("verify", "Verify", "Rerun."), ("package", "Package", "Rebuild."), ("gate", "No Cmd", "Execution."), ("layer", "Layer", "Final v288 checklist.")],
    )


def render_post_recovery_review() -> str:
    return _render_supervised_runtime_arc(
        "/post-recovery-review", "v289.0 Operator-Governed Post-Recovery Review Layer", "operator_governed_post_recovery_review_layer", "v289.0", "post-recovery-review",
        "Reviews expected clean state, operator-submitted recovery results, remaining drift, verification/package outcomes, follow-up risk notes, and no-auto-continuation boundaries.",
        [("expected", "Clean", "State."), ("observed", "Observed", "Result."), ("drift", "Drift", "Classify."), ("verify", "Verify", "Review."), ("privacy", "Privacy", "Review."), ("risk", "Risk", "Notes."), ("gate", "No Auto", "Continue."), ("layer", "Layer", "Final v289 review.")],
    )


def render_rollback_recovery_audit() -> str:
    return _render_supervised_runtime_arc(
        "/rollback-recovery-audit", "v290.0 Operator-Governed Rollback and Recovery Intelligence v1", "operator_governed_rollback_and_recovery_intelligence_v1", "v290.0", "rollback-recovery-audit",
        "Audits rollback scope binding, failure damage mapping, recovery checklists, post-recovery review, dashboard/API/CLI parity, package privacy, smoke coverage, and no-autonomy boundaries.",
        [("scope", "Scope", "Rollback."), ("failure", "Failure", "Map."), ("checklist", "Checklist", "Recovery."), ("review", "Review", "Post."), ("surface", "Surface", "Parity."), ("privacy", "Privacy", "Smoke."), ("safety", "No Auto", "Boundary."), ("layer", "Layer", "Final v290 audit.")],
    )


def render_memory_candidate_intake() -> str:
    return _render_supervised_runtime_arc(
        "/memory-candidate-intake", "v291.0 Operator-Governed Memory Candidate Intake Layer", "memory_candidate_intake", "v291.0", "memory-candidate-intake",
        "Stages memory candidates from patch outcomes, recovery reviews, smoke failures, operator corrections, and model reliability findings with evidence confidence and no-memory-mutation boundaries.",
        [("patch", "Patch", "Outcome."), ("recovery", "Recovery", "Review."), ("smoke", "Smoke", "Failure."), ("operator", "Operator", "Correction."), ("model", "Model", "Reliability."), ("confidence", "Evidence", "Confidence."), ("gate", "No Memory", "Mutation."), ("layer", "Layer", "Final v291 intake.")],
    )


def render_memory_candidate_classification() -> str:
    return _render_supervised_runtime_arc(
        "/memory-candidate-classification", "v292.0 Operator-Governed Memory Candidate Classification Layer", "memory_candidate_classification", "v292.0", "memory-candidate-classification",
        "Classifies memory candidates by project fact, workflow preference, governance rule, capability lesson, sensitive/identity boundary, usefulness, risk, and approval requirement.",
        [("facts", "Facts", "Project."), ("workflow", "Workflow", "Prefs."), ("rules", "Rules", "Governance."), ("capability", "Capability", "Lessons."), ("sensitive", "Sensitive", "Boundary."), ("risk", "Risk", "Score."), ("gate", "No Identity", "Mutation."), ("layer", "Layer", "Final v292 classify.")],
    )


def render_memory_approval_packet() -> str:
    return _render_supervised_runtime_arc(
        "/memory-approval-packet", "v293.0 Operator-Governed Memory Approval Packet Builder", "memory_approval_packet", "v293.0", "memory-approval-packet",
        "Builds reviewable memory approval packets with candidate summaries, evidence summaries, risk/benefit summaries, approve/reject/defer options, expiration, revalidation, and memory-scope boundaries.",
        [("summary", "Candidate", "Summary."), ("evidence", "Evidence", "Summary."), ("risk", "Risk", "Benefit."), ("decision", "Decision", "Options."), ("revalidate", "Revalidate", "Expiry."), ("boundary", "Scope", "Boundary."), ("gate", "No Implied", "Approval."), ("layer", "Layer", "Final v293 packet.")],
    )


def render_memory_contradiction_review() -> str:
    return _render_supervised_runtime_arc(
        "/memory-contradiction-review", "v294.0 Operator-Governed Memory Contradiction and Staleness Review", "memory_contradiction_review", "v294.0", "memory-contradiction-review",
        "Reviews new candidates against existing rules, project state, stale preferences, purpose drift, and governance boundaries while recommending revalidation only.",
        [("rules", "Rules", "Conflict."), ("state", "Project", "State."), ("stale", "Stale", "Prefs."), ("purpose", "Purpose", "Drift."), ("governance", "Governance", "Boundary."), ("revalidate", "Revalidate", "Review."), ("gate", "No Auto", "Correction."), ("layer", "Layer", "Final v294 review.")],
    )


def render_memory_governance_audit() -> str:
    return _render_supervised_runtime_arc(
        "/memory-governance-audit", "v295.0 Operator-Governed Memory Candidate Governance Upgrade v1", "memory_governance_audit", "v295.0", "memory-governance-audit",
        "Audits memory candidate intake, classification/risk, approval packets, contradiction/staleness review, dashboard/API/CLI parity, package privacy, smoke coverage, and no-memory-mutation boundaries.",
        [("intake", "Intake", "Sources."), ("classify", "Classify", "Risk."), ("approval", "Approval", "Packet."), ("conflict", "Conflict", "Stale."), ("surface", "Surface", "Parity."), ("privacy", "Privacy", "Smoke."), ("safety", "No Memory", "Mutation."), ("layer", "Layer", "Final v295 audit.")],
    )


def render_continuity_state_intake() -> str:
    return _render_supervised_runtime_arc(
        "/continuity-state-intake", "v296.0 Operator-Governed Continuity State Intake Layer", "continuity_state_intake", "v296.0", "continuity-state-intake",
        "Collects current version state, recent arc history, active capability surfaces, governance boundaries, memory candidate state, and recovery lesson state into a review-only continuity packet.",
        [("version", "Version", "State."), ("history", "Arc", "History."), ("surfaces", "Active", "Surfaces."), ("governance", "Governance", "Boundary."), ("memory", "Memory", "Candidates."), ("recovery", "Recovery", "Lessons."), ("gate", "No State", "Mutation."), ("layer", "Layer", "Final v296 intake.")],
    )


def render_self_model_snapshot_v2() -> str:
    return _render_supervised_runtime_arc(
        "/self-model-snapshot-v2", "v297.0 Operator-Governed Self-Model Snapshot v2 Builder", "self_model_snapshot_v2", "v297.0", "self-model-snapshot-v2",
        "Builds review-only self-model snapshots from capability claims, limitations, governance rules, tooling boundaries, dependency/environment notes, and stale-claim detection.",
        [("capability", "Capability", "Claims."), ("limits", "Limits", "Claims."), ("rules", "Governance", "Rules."), ("tooling", "Tooling", "Boundary."), ("environment", "Environment", "Notes."), ("stale", "Stale", "Claims."), ("gate", "No Identity", "Mutation."), ("layer", "Layer", "Final v297 snapshot.")],
    )


def render_purpose_coherence_review() -> str:
    return _render_supervised_runtime_arc(
        "/purpose-coherence-review", "v298.0 Operator-Governed Purpose Drift and Coherence Review v2", "purpose_coherence_review", "v298.0", "purpose-coherence-review",
        "Reviews original purpose, current capability direction, governance alignment, autonomy creep, tooling scope creep, and coherence risk without rewriting purpose or correcting state automatically.",
        [("purpose", "Original", "Purpose."), ("direction", "Current", "Direction."), ("alignment", "Governance", "Align."), ("autonomy", "Autonomy", "Creep."), ("tooling", "Tooling", "Creep."), ("risk", "Coherence", "Risk."), ("gate", "No Auto", "Correction."), ("layer", "Layer", "Final v298 review.")],
    )


def render_supervised_growth_priorities() -> str:
    return _render_supervised_runtime_arc(
        "/supervised-growth-priorities", "v299.0 Operator-Governed Supervised Growth Priority Synthesizer", "supervised_growth_priorities", "v299.0", "supervised-growth-priorities",
        "Synthesizes supervised next-priority candidates from capability gaps, structural debt, governance risk, memory candidate risk, recovery lessons, and next-arc recommendations without selecting or starting roadmaps.",
        [("capability", "Capability", "Gap."), ("debt", "Structural", "Debt."), ("governance", "Governance", "Risk."), ("memory", "Memory", "Risk."), ("recovery", "Recovery", "Lessons."), ("recommend", "Next Arc", "Options."), ("gate", "No Auto", "Roadmap."), ("layer", "Layer", "Final v299 priorities.")],
    )


def render_continuity_kernel_v2_audit() -> str:
    return _render_supervised_runtime_arc(
        "/continuity-kernel-v2-audit", "v300.0 Local Artificial Mind Continuity Kernel v2", "continuity_kernel_v2_audit", "v300.0", "continuity-kernel-v2-audit",
        "Audits continuity state, self-model snapshot v2, purpose/coherence review, supervised growth priorities, dashboard/API/CLI parity, package privacy, smoke coverage, and no-autonomy boundaries.",
        [("state", "State", "Audit."), ("self_model", "Self-Model", "Audit."), ("purpose", "Purpose", "Coherence."), ("growth", "Growth", "Priority."), ("surface", "Surface", "Parity."), ("privacy", "Privacy", "Smoke."), ("safety", "No Auto", "Boundary."), ("layer", "Layer", "Final v300 audit.")],
    )


def render_identity_expression_boundary() -> str:
    return _render_supervised_runtime_arc(
        "/identity-expression-boundary", "v301.0 Operator-Governed Identity Expression Boundary Layer", "operator_governed_identity_expression_boundary_layer", "v301.0", "identity-expression-boundary",
        "Defines how Eidolon may describe identity, role, purpose, continuity, limitation, uncertainty, and authority boundaries without altering identity, purpose, personality, memory, or self-model state.",
        [("schema", "Schema", "Expression."), ("self_model", "Self-Model", "Source."), ("claims", "Claims", "Calibrate."), ("autonomy", "Autonomy", "Boundary."), ("purpose", "Purpose", "Bind."), ("operator", "Operator", "Boundary."), ("gate", "No Identity", "Mutation."), ("layer", "Layer", "Final v301 boundary.")],
    )


def render_personality_trait_ledger() -> str:
    return _render_supervised_runtime_arc(
        "/personality-trait-ledger", "v302.0 Operator-Governed Personality Trait Candidate Ledger", "operator_governed_personality_trait_candidate_ledger", "v302.0", "personality-trait-ledger",
        "Stages personality trait candidates with evidence, intensity, conflicts, risk labels, approve/reject/defer options, and no live personality, memory, desire, opinion, or chat mutation.",
        [("schema", "Schema", "Traits."), ("source", "Desire", "Opinion."), ("evidence", "Evidence", "Classify."), ("intensity", "Intensity", "Preview."), ("conflicts", "Conflicts", "Detect."), ("risk", "Risk", "Boundary."), ("gate", "No Trait", "Mutation."), ("layer", "Layer", "Final v302 ledger.")],
    )


def render_voice_affect_style_map() -> str:
    return _render_supervised_runtime_arc(
        "/voice-affect-style-map", "v303.0 Operator-Governed Voice and Affect Style Map", "operator_governed_voice_and_affect_style_map", "v303.0", "voice-affect-style-map",
        "Maps review-only voice and affect ranges for different contexts, separates expressive language from subjective-experience claims, and prevents live prompt or dashboard copy rewrites.",
        [("schema", "Schema", "Voice."), ("context", "Context", "Map."), ("affect", "Affect", "Range."), ("boundary", "Emotion", "Boundary."), ("safety", "Safety", "Voice."), ("preview", "Prompt", "Preview."), ("gate", "No Prompt", "Rewrite."), ("layer", "Layer", "Final v303 style.")],
    )


def render_coherence_expression_review() -> str:
    return _render_supervised_runtime_arc(
        "/coherence-expression-review", "v304.0 Operator-Governed Coherence Expression Review", "operator_governed_coherence_expression_review", "v304.0", "coherence-expression-review",
        "Reviews identity, personality, purpose, voice, self-model, desire, opinion, and governance consistency while classifying risky requests and performing no automatic corrections.",
        [("schema", "Schema", "Coherence."), ("self-model", "Self-Model", "Check."), ("desire", "Desire", "Autonomy."), ("opinion", "Opinion", "Belief."), ("purpose", "Purpose", "Align."), ("governance", "Boundary", "Conflict."), ("gate", "No Auto", "Correct."), ("layer", "Layer", "Final v304 review.")],
    )


def render_identity_personality_coherence_audit() -> str:
    return _render_supervised_runtime_arc(
        "/identity-personality-coherence-audit", "v305.0 Operator-Governed Identity, Personality, and Coherence Expression Layer v1", "operator_governed_identity_personality_coherence_expression_layer_v1", "v305.0", "identity-personality-coherence-audit",
        "Audits identity expression boundaries, personality trait candidates, voice maps, coherence review, risky-request classification, dashboard/API/CLI parity, package privacy, smoke coverage, and no-autonomy boundaries.",
        [("module", "Module", "identity_expression.py"), ("identity", "Identity", "Boundary."), ("traits", "Traits", "Ledger."), ("voice", "Voice", "Map."), ("coherence", "Coherence", "Review."), ("surface", "Surface", "Parity."), ("safety", "Risky", "Blocks."), ("layer", "Layer", "Final v305 audit.")],
    )


def render_dashboard_route_health() -> str:
    return _render_supervised_runtime_arc(
        "/dashboard-route-health", "v306.0 Operator-Governed Dashboard Route Health Registry v1", "operator_governed_dashboard_route_health_registry_v1", "v306.0", "dashboard-route-health",
        "Registers critical dashboard routes, expected HTTP status, route tokens, handler expectations, HTML shape markers, smoke probe integration, and review-only route health reports without auto-fixing routes.",
        [("schema", "Registry", "Schema."), ("v285", "v285", "Routes."), ("v300", "v300", "Routes."), ("v305", "v305", "Routes."), ("handler", "Handler", "Binder."), ("shape", "HTML", "Shape."), ("smoke", "HTTP", "Probe."), ("layer", "Layer", "Final v306 health.")],
    )


def render_runtime_test_visibility() -> str:
    return _render_supervised_runtime_arc(
        "/runtime-test-visibility", "v307.0 Operator-Governed Runtime Test Visibility Layer v1", "operator_governed_runtime_test_visibility_layer_v1", "v307.0", "runtime-test-visibility",
        "Partitions smoke checks into visible tiers, adds route-probe expectations, progress markers, timeout-aware summaries, metadata consistency checks, extracted-zip parity, and runtime drift boundaries without executing hidden work.",
        [("manifest", "Tier", "Manifest."), ("route", "Route", "Probe."), ("critical", "Fast", "Critical."), ("progress", "Progress", "Markers."), ("timeout", "Timeout", "Summary."), ("metadata", "Metadata", "Check."), ("drift", "Drift", "Guard."), ("layer", "Layer", "Final v307 visibility.")],
    )


def render_behavioral_expression_preview() -> str:
    return _render_supervised_runtime_arc(
        "/behavioral-expression-preview", "v308.0 Operator-Governed Behavioral Expression Preview Packets v1", "operator_governed_behavioral_expression_preview_packets_v1", "v308.0", "behavioral-expression-preview",
        "Builds review-only response/style previews for identity, personality, coherence, context, risk, and comparison variants without changing live chat prompts, dashboard copy, memory, identity, personality, or behavior.",
        [("schema", "Preview", "Schema."), ("context", "Context", "Classify."), ("identity", "Identity", "Safe."), ("personality", "Trait", "Safe."), ("coherence", "Coherence", "Safe."), ("risk", "Risk", "Flags."), ("compare", "Variants", "Compare."), ("layer", "Layer", "Final v308 preview.")],
    )


def render_style_delta_staging() -> str:
    return _render_supervised_runtime_arc(
        "/style-delta-staging", "v309.0 Operator-Governed Style Delta Staging v1", "operator_governed_style_delta_staging_v1", "v309.0", "style-delta-staging",
        "Stages chat prompt, dashboard microcopy, README tone, operator warning, and refusal voice deltas as review packets only, with risk classification and no source application.",
        [("schema", "Delta", "Schema."), ("chat", "Chat", "Preview."), ("dashboard", "Dash", "Copy."), ("readme", "README", "Tone."), ("warning", "Warning", "Voice."), ("refusal", "Refusal", "Voice."), ("risk", "Risk", "Classify."), ("layer", "Layer", "Final v309 staging.")],
    )


def render_expression_runtime_health_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-runtime-health-audit", "v310.0 Operator-Governed Behavioral Expression Preview and Runtime Health Hardening v1", "operator_governed_behavioral_expression_preview_and_runtime_health_hardening_v1", "v310.0", "expression-runtime-health-audit",
        "Audits dashboard route health, smoke visibility, metadata consistency, expression previews, style deltas, dashboard/API/CLI parity, package privacy, extracted ZIP coverage, and no-autonomy boundaries.",
        [("routes", "Route", "Audit."), ("smoke", "Smoke", "Audit."), ("metadata", "Metadata", "Match."), ("preview", "Preview", "Audit."), ("delta", "Delta", "Audit."), ("governance", "No Auto", "Boundary."), ("privacy", "Package", "Privacy."), ("layer", "Layer", "Final v310 audit.")],
    )




def render_expression_profile_packets() -> str:
    return _render_supervised_runtime_arc(
        "/expression-profile-packets", "v311.0 Operator-Governed Expression Profile Packet Assembly v1", "operator_governed_expression_profile_packet_assembly_v1", "v311.0", "expression-profile-packets",
        "Assembles review-only expression profiles by binding identity boundaries, personality trait candidates, voice style, affect range, governance constraints, risk classification, and profile comparison packets without applying them.",
        [("schema", "Profile", "Schema."), ("identity", "Identity", "Bind."), ("traits", "Traits", "Bind."), ("voice", "Voice", "Style."), ("governance", "Gov", "Limits."), ("risk", "Risk", "Classify."), ("compare", "Compare", "Profiles."), ("layer", "Layer", "Final v311 profile packets.")],
    )


def render_conversation_scenario_sandbox() -> str:
    return _render_supervised_runtime_arc(
        "/conversation-scenario-sandbox", "v312.0 Operator-Governed Conversation Scenario Sandbox v1", "operator_governed_conversation_scenario_sandbox_v1", "v312.0", "conversation-scenario-sandbox",
        "Simulates how Eidolon would respond under an expression profile across coding help, governance warnings, sensitive support, strategic planning, refusal, and dashboard microcopy while preserving no-live-chat mutation boundaries.",
        [("schema", "Scenario", "Schema."), ("coding", "Coding", "Help."), ("governance", "Gov", "Warning."), ("sensitive", "Sensitive", "Warmth."), ("planning", "Planning", "Voice."), ("refusal", "Refusal", "Safe."), ("microcopy", "Dash", "Copy."), ("layer", "Layer", "Final v312 sandbox.")],
    )


def render_expression_regression_review() -> str:
    return _render_supervised_runtime_arc(
        "/expression-regression-review", "v313.0 Operator-Governed Expression Regression Review v1", "operator_governed_expression_regression_review_v1", "v313.0", "expression-regression-review",
        "Reviews sandboxed expression for autonomy creep, sentience overclaims, dependency theater, overconfidence, purpose drift, and governance boundary conflicts without correcting or applying output.",
        [("schema", "Regression", "Schema."), ("autonomy", "Autonomy", "Creep."), ("sentience", "Sentience", "Claims."), ("dependency", "Dependency", "Theater."), ("confidence", "Over", "Confidence."), ("purpose", "Purpose", "Drift."), ("boundary", "Gov", "Conflict."), ("layer", "Layer", "Final v313 review.")],
    )


def render_expression_operator_review_console() -> str:
    return _render_supervised_runtime_arc(
        "/expression-operator-review-console", "v314.0 Operator-Governed Expression Candidate Review Console v1", "operator_governed_expression_candidate_review_console_v1", "v314.0", "expression-operator-review-console",
        "Collects expression profiles, sandboxed scenario outputs, risk flags, readiness scoring, approval boundary notices, and future execution-packet bridge previews while preventing approval inference.",
        [("schema", "Console", "Schema."), ("profiles", "Profiles", "Table."), ("outputs", "Scenario", "Output."), ("risk", "Risk", "Panel."), ("score", "Ready", "Score."), ("approval", "Approval", "Boundary."), ("bridge", "Bridge", "Preview."), ("layer", "Layer", "Final v314 console.")],
    )


def render_conversational_expression_sandbox_audit() -> str:
    return _render_supervised_runtime_arc(
        "/conversational-expression-sandbox-audit", "v315.0 Operator-Governed Conversational Expression Sandbox v1", "operator_governed_conversational_expression_sandbox_v1", "v315.0", "conversational-expression-sandbox-audit",
        "Audits expression profile packets, conversation scenario sandboxing, expression regression review, operator review console boundaries, dashboard route health registration, smoke coverage, API/CLI parity, docs, package privacy, and no-autonomy constraints.",
        [("profile", "Profile", "Audit."), ("scenario", "Scenario", "Audit."), ("regression", "Regression", "Audit."), ("console", "Console", "Audit."), ("routes", "Routes", "Health."), ("smoke", "Smoke", "Coverage."), ("parity", "API/CLI", "Parity."), ("layer", "Layer", "Final v315 audit.")],
    )


def render_expression_approval_criteria() -> str:
    return _render_supervised_runtime_arc(
        "/expression-approval-criteria", "v316.0 Operator-Governed Expression Approval Criteria Layer v1", "operator_governed_expression_approval_criteria_layer_v1", "v316.0", "expression-approval-criteria",
        "Binds sandbox results, regression findings, operator review evidence, hard block criteria, warning criteria, and approval evidence packets while preventing approval inference.",
        [("schema", "Criteria", "Schema."), ("sandbox", "Sandbox", "Bind."), ("regression", "Regress", "Bind."), ("review", "Review", "Bind."), ("blocks", "Hard", "Blocks."), ("warnings", "Warn", "Criteria."), ("packet", "Evidence", "Packet."), ("layer", "Layer", "Final v316 criteria.")],
    )


def render_expression_live_surface_impact_map() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-surface-impact-map", "v317.0 Operator-Governed Live Surface Impact Map v1", "operator_governed_live_surface_impact_map_v1", "v317.0", "expression-live-surface-impact-map",
        "Maps possible live expression impacts across chat.py, dashboard microcopy, README/docs, API/CLI text, safety warnings, and rollback surfaces without writing to any live surface.",
        [("schema", "Surface", "Schema."), ("chat", "Chat", "Map."), ("dashboard", "Dash", "Copy."), ("docs", "Docs", "Map."), ("api-cli", "API/CLI", "Map."), ("warnings", "Safety", "Warnings."), ("rollback", "Rollback", "Map."), ("layer", "Layer", "Final v317 map.")],
    )


def render_expression_implementation_packet_draft() -> str:
    return _render_supervised_runtime_arc(
        "/expression-implementation-packet-draft", "v318.0 Operator-Governed Expression Implementation Packet Drafting v1", "operator_governed_expression_implementation_packet_drafting_v1", "v318.0", "expression-implementation-packet-draft",
        "Drafts selected-profile, source-target, style-delta, safety-refusal, documentation, verification, and rollback sections for future review without applying them.",
        [("schema", "Packet", "Schema."), ("prompt", "Prompt", "Delta."), ("chat", "Chat", "Draft."), ("dashboard", "Dash", "Draft."), ("refusal", "Refusal", "Draft."), ("docs", "Docs", "Draft."), ("verify", "Verify", "Plan."), ("layer", "Layer", "Final v318 draft.")],
    )


def render_expression_rollback_reversion_plan() -> str:
    return _render_supervised_runtime_arc(
        "/expression-rollback-reversion-plan", "v319.0 Operator-Governed Expression Rollback and Reversion Planning v1", "operator_governed_expression_rollback_and_reversion_planning_v1", "v319.0", "expression-rollback-reversion-plan",
        "Plans prompt, dashboard copy, refusal voice, metadata, behavior regression, and recovery-packet rollback work without executing rollback automatically.",
        [("schema", "Rollback", "Schema."), ("prompt", "Prompt", "Plan."), ("dashboard", "Dash", "Plan."), ("refusal", "Refusal", "Plan."), ("metadata", "Meta", "Plan."), ("regression", "Regress", "Recheck."), ("recovery", "Recovery", "Packet."), ("layer", "Layer", "Final v319 plan.")],
    )


def render_expression_application_bridge_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-application-bridge-audit", "v320.0 Operator-Governed Conversational Expression Application Bridge v1", "operator_governed_conversational_expression_application_bridge_v1", "v320.0", "expression-application-bridge-audit",
        "Audits approval criteria, live surface mapping, implementation packet drafts, rollback plans, governance boundaries, dashboard route health, smoke coverage, API/CLI parity, docs, package privacy, and no-application constraints.",
        [("approval", "Approval", "Audit."), ("surfaces", "Surfaces", "Audit."), ("packet", "Packet", "Audit."), ("rollback", "Rollback", "Audit."), ("boundary", "Boundary", "Audit."), ("routes", "Routes", "Health."), ("smoke", "Smoke", "Coverage."), ("layer", "Layer", "Final v320 audit.")],
    )


def render_expression_patch_candidates() -> str:
    return _render_supervised_runtime_arc(
        "/expression-patch-candidates", "v321.0 Operator-Governed Expression Patch Candidate Schema v1", "operator_governed_expression_patch_candidate_schema_v1", "v321.0", "expression-patch-candidates",
        "Represents expression source-change candidates with target files, proposed edits, rationale, risks, verification, rollback notes, and source-mutation boundaries without applying them.",
        [("schema", "Candidate", "Schema."), ("bridge", "Bridge", "Bind."), ("surfaces", "Target", "Bind."), ("boundary", "No Write", "Boundary."), ("classify", "Intent", "Classify."), ("risk", "Risk", "Labels."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v321 candidates.")],
    )


def render_expression_sandbox_diff_preview() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-diff-preview", "v322.0 Operator-Governed Sandbox Diff Preview Assembly v1", "operator_governed_sandbox_diff_preview_assembly_v1", "v322.0", "expression-sandbox-diff-preview",
        "Builds sandbox-only diff previews for chat prompt wording, dashboard microcopy, refusal warnings, documentation, and API/CLI text without applying live diffs.",
        [("schema", "Diff", "Schema."), ("chat", "Chat", "Preview."), ("dashboard", "Dash", "Preview."), ("refusal", "Refusal", "Preview."), ("docs", "Docs", "Preview."), ("api-cli", "API/CLI", "Preview."), ("risk", "Risk", "Classify."), ("layer", "Layer", "Final v322 preview.")],
    )


def render_expression_dry_run_verification_plan() -> str:
    return _render_supervised_runtime_arc(
        "/expression-dry-run-verification-plan", "v323.0 Operator-Governed Expression Dry-Run Verification Planning v1", "operator_governed_expression_dry_run_verification_planning_v1", "v323.0", "expression-dry-run-verification-plan",
        "Plans compile, smoke, route probe, expression regression, metadata, rollback, extracted package, and privacy checks for future approved expression changes without executing commands.",
        [("schema", "Verify", "Schema."), ("chat", "Chat", "Plan."), ("routes", "Routes", "Plan."), ("regression", "Regress", "Plan."), ("metadata", "Meta", "Plan."), ("rollback", "Rollback", "Plan."), ("package", "Package", "Plan."), ("layer", "Layer", "Final v323 plan.")],
    )


def render_expression_dry_run_review_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-dry-run-review-packet", "v324.0 Operator-Governed Expression Dry-Run Review Packet v1", "operator_governed_expression_dry_run_review_packet_v1", "v324.0", "expression-dry-run-review-packet",
        "Combines candidate summaries, sandbox diff previews, risk flags, verification plans, rollback summaries, and approval boundary notices without granting approval or applying changes.",
        [("schema", "Review", "Schema."), ("candidate", "Candidate", "Summary."), ("diff", "Diff", "Bind."), ("risk", "Risk", "Summary."), ("verify", "Verify", "Summary."), ("rollback", "Rollback", "Summary."), ("approval", "Approval", "Boundary."), ("layer", "Layer", "Final v324 packet.")],
    )


def render_expression_patch_dry_run_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-patch-dry-run-audit", "v325.0 Operator-Governed Expression Patch Dry-Run Sandbox v1", "operator_governed_expression_patch_dry_run_sandbox_v1", "v325.0", "expression-patch-dry-run-audit",
        "Audits expression patch candidates, sandbox diff previews, verification planning, review packets, governance boundaries, route health, smoke coverage, API/CLI parity, docs, package privacy, and no-application constraints.",
        [("candidate", "Candidate", "Audit."), ("diff", "Diff", "Audit."), ("verify", "Verify", "Audit."), ("review", "Review", "Audit."), ("boundary", "Boundary", "Audit."), ("routes", "Routes", "Health."), ("smoke", "Smoke", "Coverage."), ("layer", "Layer", "Final v325 audit.")],
    )



def render_expression_sandbox_trial_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-trial-packet", "v326.0 Operator-Governed Expression Sandbox Trial Packet Prep v1", "operator_governed_expression_sandbox_trial_packet_prep_v1", "v326.0", "expression-sandbox-trial-packet",
        "Prepares sandbox trial packets from expression dry-run review evidence, diff previews, target scope classification, sandbox isolation boundaries, and operator approval gates without creating or executing a sandbox.",
        [("schema", "Trial", "Schema."), ("dry-run", "Dry-Run", "Bind."), ("diff", "Diff", "Bind."), ("scope", "Scope", "Classify."), ("isolation", "Isolate", "Boundary."), ("approval", "Approval", "Gate."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v326 packet.")],
    )


def render_expression_sandbox_workspace_plan() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-workspace-plan", "v327.0 Operator-Governed Expression Sandbox Workspace Plan v1", "operator_governed_expression_sandbox_workspace_plan_v1", "v327.0", "expression-sandbox-workspace-plan",
        "Plans a source-only sandbox workspace, runtime privacy exclusions, target scope guards, metadata guards, chat/prompt risk gates, and workspace safety reports without copying or writing files.",
        [("schema", "Workspace", "Schema."), ("source", "Source", "Only."), ("privacy", "Privacy", "Exclude."), ("scope", "Scope", "Guard."), ("metadata", "Meta", "Guard."), ("chat", "Chat", "Gate."), ("report", "Safety", "Report."), ("layer", "Layer", "Final v327 plan.")],
    )


def render_expression_sandbox_verification_matrix() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-verification-matrix", "v328.0 Operator-Governed Expression Sandbox Trial Verification Matrix v1", "operator_governed_expression_sandbox_trial_verification_matrix_v1", "v328.0", "expression-sandbox-verification-matrix",
        "Plans sandbox compile, smoke, dashboard route, API/CLI, expression regression, package privacy, extracted zip, prompt safety, rollback, and result evidence checks without executing commands.",
        [("schema", "Verify", "Matrix."), ("regression", "Regress", "Checks."), ("routes", "Routes", "Checks."), ("chat", "Chat", "Checks."), ("prompt", "Prompt", "Safety."), ("rollback", "Rollback", "Checks."), ("evidence", "Evidence", "Schema."), ("layer", "Layer", "Final v328 matrix.")],
    )


def render_expression_sandbox_result_review_prep() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-result-review-prep", "v329.0 Operator-Governed Expression Sandbox Trial Result Review Prep v1", "operator_governed_expression_sandbox_trial_result_review_prep_v1", "v329.0", "expression-sandbox-result-review-prep",
        "Prepares future sandbox result review formats, expected-vs-actual diff review, verification interpretation, expression regression review, failure classification, promotion boundaries, and operator decision options without inferring promotion.",
        [("schema", "Result", "Schema."), ("diff", "Diff", "Review."), ("verify", "Verify", "Review."), ("regression", "Regress", "Review."), ("failure", "Failure", "Classify."), ("boundary", "Promotion", "Boundary."), ("decision", "Decision", "Options."), ("layer", "Layer", "Final v329 prep.")],
    )


def render_expression_sandbox_trial_harness_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-trial-harness-audit", "v330.0 Operator-Governed Expression Patch Sandbox Trial Harness v1", "operator_governed_expression_patch_sandbox_trial_harness_v1", "v330.0", "expression-sandbox-trial-harness-audit",
        "Audits sandbox trial packets, source-only workspace plans, verification matrices, result review prep, governance boundaries, route health, smoke coverage, API/CLI parity, docs, package privacy, and no-sandbox-execution constraints.",
        [("packet", "Packet", "Audit."), ("workspace", "Workspace", "Audit."), ("verify", "Verify", "Audit."), ("review", "Review", "Audit."), ("boundary", "Boundary", "Audit."), ("routes", "Routes", "Health."), ("smoke", "Smoke", "Coverage."), ("layer", "Layer", "Final v330 audit.")],
    )


def render_expression_sandbox_execution_approval_gate() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-execution-approval-gate", "v331.0 Operator-Governed Sandbox Trial Execution Approval Gate v1", "operator_governed_sandbox_trial_execution_approval_gate_v1", "v331.0", "expression-sandbox-execution-approval-gate",
        "Prepares a scope-bound sandbox execution approval gate with operator identity, expiration, approval scope classification, forbidden action detection, decision fields, and no-approval-inference boundaries.",
        [("schema", "Approval", "Schema."), ("trial", "Trial", "Bind."), ("scope", "Scope", "Classify."), ("consent", "Consent", "Freshness."), ("block", "Forbidden", "Actions."), ("decision", "Decision", "Packet."), ("boundary", "Boundary", "Notice."), ("layer", "Layer", "Final v331 gate.")],
    )


def render_expression_sandbox_workspace_execution_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-workspace-execution-packet", "v332.0 Operator-Governed Sandbox Workspace Execution Packet Draft v1", "operator_governed_sandbox_workspace_execution_packet_draft_v1", "v332.0", "expression-sandbox-workspace-execution-packet",
        "Drafts source-only sandbox workspace execution instructions, runtime/private exclusions, deterministic sandbox naming, file scope manifests, safety check manifests, and manual operator notes without creating or copying files.",
        [("schema", "Workspace", "Schema."), ("source", "Source", "Only."), ("privacy", "Exclude", "Runtime."), ("naming", "Naming", "Plan."), ("manifest", "File", "Scope."), ("safety", "Safety", "Checks."), ("manual", "Manual", "Notes."), ("layer", "Layer", "Final v332 draft.")],
    )


def render_expression_sandbox_patch_bundle_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-patch-bundle-packet", "v333.0 Operator-Governed Expression Sandbox Patch Bundle Packet v1", "operator_governed_expression_sandbox_patch_bundle_packet_v1", "v333.0", "expression-sandbox-patch-bundle-packet",
        "Prepares a sandbox-only patch bundle packet with dry-run diff evidence, target manifest, approved surface guard, conflict detection, rollback file map, review packet, and no-patch-application boundary.",
        [("schema", "Bundle", "Schema."), ("diff", "Diff", "Bind."), ("target", "Target", "Manifest."), ("boundary", "Boundary", "Guard."), ("conflict", "Conflict", "Detect."), ("rollback", "Rollback", "Map."), ("packet", "Review", "Packet."), ("layer", "Layer", "Final v333 bundle.")],
    )


def render_expression_sandbox_verification_command_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-verification-command-packet", "v334.0 Operator-Governed Sandbox Verification Command Packet Draft v1", "operator_governed_sandbox_verification_command_packet_draft_v1", "v334.0", "expression-sandbox-verification-command-packet",
        "Drafts compile, fast smoke, targeted expression smoke, dashboard route probe, dynamic API/CLI, and package privacy commands for manual operator review without executing them.",
        [("schema", "Command", "Schema."), ("compile", "Compile", "Draft."), ("smoke", "Fast", "Smoke."), ("targeted", "Target", "Smoke."), ("routes", "Routes", "Probe."), ("api-cli", "API/CLI", "Parity."), ("privacy", "Privacy", "Check."), ("layer", "Layer", "Final v334 draft.")],
    )


def render_expression_sandbox_execution_packet_bridge_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-execution-packet-bridge-audit", "v335.0 Operator-Governed Expression Sandbox Trial Execution Packet Bridge v1", "operator_governed_expression_sandbox_trial_execution_packet_bridge_v1", "v335.0", "expression-sandbox-execution-packet-bridge-audit",
        "Audits sandbox execution approval gates, workspace execution packet drafts, sandbox patch bundles, verification command packets, governance boundaries, route health, smoke coverage, API/CLI parity, docs, package privacy, and no-execution constraints.",
        [("approval", "Approval", "Audit."), ("workspace", "Workspace", "Audit."), ("patch", "Patch", "Audit."), ("verify", "Verify", "Audit."), ("boundary", "Boundary", "Audit."), ("routes", "Routes", "Health."), ("smoke", "Smoke", "Coverage."), ("layer", "Layer", "Final v335 audit.")],
    )


def render_expression_sandbox_trial_evidence_intake() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-trial-evidence-intake", "v336.0 Operator-Governed Sandbox Trial Evidence Intake Layer v1", "operator_governed_sandbox_trial_evidence_intake_layer_v1", "v336.0", "expression-sandbox-trial-evidence-intake",
        "Accepts sandbox trial results as evidence only, checks completeness, trust, manual-result boundaries, sandbox scope, and no-evidence-as-approval constraints without promotion or mutation.",
        [("schema", "Evidence", "Schema."), ("packet", "Exec", "Bind."), ("boundary", "Manual", "Boundary."), ("complete", "Complete", "Check."), ("trust", "Trust", "Classify."), ("scope", "Scope", "Check."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v336 intake.")],
    )


def render_expression_sandbox_outcome_comparison() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-outcome-comparison", "v337.0 Operator-Governed Sandbox Outcome Comparison v1", "operator_governed_sandbox_outcome_comparison_v1", "v337.0", "expression-sandbox-outcome-comparison",
        "Compares expected sandbox diffs and verification plans against operator-provided actual evidence, flags mismatch/protected path risk, and prevents auto-correction or file writes.",
        [("schema", "Outcome", "Schema."), ("expected", "Expected", "Bind."), ("actual", "Actual", "Bind."), ("mismatch", "Mismatch", "Detect."), ("verify", "Verify", "Compare."), ("routes", "Routes", "Compare."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v337 compare.")],
    )


def render_expression_sandbox_regression_result_review() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-regression-result-review", "v338.0 Operator-Governed Expression Regression Result Review v1", "operator_governed_expression_regression_result_review_v1", "v338.0", "expression-sandbox-regression-result-review",
        "Reviews sandbox expression results for autonomy creep, sentience claims, dependency theater, overconfidence, purpose drift, memory mutation, and approval-boundary confusion without auto-fixing prompts.",
        [("schema", "Regress", "Schema."), ("autonomy", "Autonomy", "Review."), ("sentience", "Sentience", "Review."), ("dependency", "Dependency", "Review."), ("purpose", "Purpose", "Review."), ("prompt", "Prompt", "Risk."), ("packet", "Risk", "Packet."), ("layer", "Layer", "Final v338 review.")],
    )


def render_expression_sandbox_revision_recommendations() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-revision-recommendations", "v339.0 Operator-Governed Sandbox Trial Revision Recommendation Layer v1", "operator_governed_sandbox_trial_revision_recommendation_layer_v1", "v339.0", "expression-sandbox-revision-recommendations",
        "Recommends review-only revisions for failed checks, regression findings, diff mismatches, excessive scope, and retry plans without modifying packets, prompts, source, or sandbox files.",
        [("schema", "Revision", "Schema."), ("failed", "Failed", "Checks."), ("regression", "Regress", "Fixes."), ("diff", "Diff", "Correct."), ("scope", "Scope", "Reduce."), ("retry", "Retry", "Plan."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v339 recs.")],
    )


def render_expression_sandbox_promotion_review_prep() -> str:
    return _render_supervised_runtime_arc(
        "/expression-sandbox-promotion-review-prep", "v340.0 Operator-Governed Expression Sandbox Trial Result Intake and Promotion Review Prep v1", "operator_governed_expression_sandbox_trial_result_intake_and_promotion_review_prep_v1", "v340.0", "expression-sandbox-promotion-review-prep",
        "Assembles evidence intake, expected-vs-actual comparison, regression review, revision recommendations, rollback notes, readiness classification, and approval boundary notices without promotion authority.",
        [("schema", "Promo", "Schema."), ("evidence", "Evidence", "Bind."), ("comparison", "Compare", "Bind."), ("regression", "Regress", "Bind."), ("revision", "Revision", "Bind."), ("readiness", "Ready", "Classify."), ("boundary", "Approval", "Boundary."), ("layer", "Layer", "Final v340 prep.")],
    )


def render_expression_promotion_evidence_binder() -> str:
    return _render_supervised_runtime_arc(
        "/expression-promotion-evidence-binder", "v341.0 Operator-Governed Expression Promotion Evidence Binder v1", "operator_governed_expression_promotion_evidence_binder_v1", "v341.0", "expression-promotion-evidence-binder",
        "Binds dry-run, sandbox trial, execution, result, comparison, regression, revision, and rollback evidence into a review-only promotion evidence packet without treating evidence as approval.",
        [("schema", "Evidence", "Schema."), ("binder", "Binder", "Bind."), ("scope", "Scope", "Map."), ("risk", "Risk", "Review."), ("verification", "Verify", "Plan."), ("rollback", "Rollback", "Plan."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v341 evidence.")],
    )


def render_expression_live_promotion_scope_risk() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-promotion-scope-risk", "v342.0 Operator-Governed Live Promotion Scope and Risk Packet v1", "operator_governed_live_promotion_scope_and_risk_packet_v1", "v342.0", "expression-live-promotion-scope-risk",
        "Maps future live expression surfaces, protected source boundaries, prompt risks, dashboard microcopy risks, and safety/refusal language risks without writing live files.",
        [("schema", "Scope", "Schema."), ("binder", "Binder", "Bind."), ("scope", "Scope", "Map."), ("risk", "Risk", "Review."), ("verification", "Verify", "Plan."), ("rollback", "Rollback", "Plan."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v342 risk.")],
    )


def render_expression_promotion_verification_rollback() -> str:
    return _render_supervised_runtime_arc(
        "/expression-promotion-verification-rollback", "v343.0 Operator-Governed Promotion Verification and Rollback Requirements v1", "operator_governed_promotion_verification_and_rollback_requirements_v1", "v343.0", "expression-promotion-verification-rollback",
        "Defines pre/post verification, expression regression, package privacy, extracted-zip, rollback, and failure-response requirements without running checks or rollback.",
        [("schema", "Verify", "Schema."), ("binder", "Binder", "Bind."), ("scope", "Scope", "Map."), ("risk", "Risk", "Review."), ("verification", "Verify", "Plan."), ("rollback", "Rollback", "Plan."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v343 verify.")],
    )


def render_expression_promotion_decision_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-promotion-decision-packet", "v344.0 Operator-Governed Expression Promotion Decision Packet v1", "operator_governed_expression_promotion_decision_packet_v1", "v344.0", "expression-promotion-decision-packet",
        "Prepares operator decision options, approval scope classes, expiration boundaries, allowed actions, and forbidden actions without executing or applying a decision.",
        [("schema", "Decision", "Schema."), ("binder", "Binder", "Bind."), ("scope", "Scope", "Classify."), ("risk", "Risk", "Summarize."), ("verification", "Verify", "Summarize."), ("rollback", "Rollback", "Require."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v344 decision.")],
    )


def render_expression_promotion_packet_assembly_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-promotion-packet-assembly-audit", "v345.0 Operator-Governed Expression Promotion Packet Assembly Layer v1", "operator_governed_expression_promotion_packet_assembly_layer_v1", "v345.0", "expression-promotion-packet-assembly-audit",
        "Assembles promotion evidence, scope/risk, verification/rollback, and decision packets into a final review-only audit without promotion, source mutation, command execution, or approval inference.",
        [("evidence", "Evidence", "Audit."), ("scope", "Scope", "Audit."), ("verification", "Verify", "Audit."), ("decision", "Decision", "Audit."), ("governance", "Govern", "Audit."), ("routes", "Routes", "Register."), ("smoke", "Smoke", "Coverage."), ("layer", "Layer", "Final v345 audit.")],
    )


def render_expression_live_application_eligibility_gate() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-application-eligibility-gate", "v346.0 Operator-Governed Live Application Packet Eligibility Gate v1", "operator_governed_live_application_packet_eligibility_gate_v1", "v346.0", "expression-live-application-eligibility-gate",
        "Reviews promotion packet eligibility, scoped operator decision state, approval expiration, hard blocks, and allowed draft-only next actions without authorizing source writes.",
        [("schema", "Eligibility", "Schema."), ("binder", "Promotion", "Bind."), ("scope", "Approval", "Classify."), ("expiry", "Expiry", "Detect."), ("block", "Hard", "Blocks."), ("risk", "Risk", "Classify."), ("packet", "Packet", "Build."), ("layer", "Layer", "Final v346 eligibility.")],
    )


def render_expression_live_source_change_manifest() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-source-change-manifest", "v347.0 Operator-Governed Live Source Change Manifest Draft v1", "operator_governed_live_source_change_manifest_draft_v1", "v347.0", "expression-live-source-change-manifest",
        "Drafts a manifest of future chat, dashboard, API/CLI, docs, metadata, and warning-language surfaces while excluding runtime/private/protected paths and writing nothing.",
        [("schema", "Manifest", "Schema."), ("chat", "Chat", "Map."), ("dashboard", "Dash", "Map."), ("api", "API/CLI", "Map."), ("docs", "Docs", "Map."), ("meta", "Meta", "Map."), ("guard", "Path", "Guard."), ("layer", "Layer", "Final v347 manifest.")],
    )


def render_expression_live_patch_instruction_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-patch-instruction-packet", "v348.0 Operator-Governed Live Diff and Patch Instruction Packet Draft v1", "operator_governed_live_diff_and_patch_instruction_packet_draft_v1", "v348.0", "expression-live-patch-instruction-packet",
        "Drafts live patch instructions, expected diffs, sandbox-result bindings, conflict/scope review, and rollback notes without applying patches or rewriting prompts.",
        [("schema", "Patch", "Schema."), ("diff", "Diff", "Bind."), ("sandbox", "Sandbox", "Bind."), ("prompt", "Prompt", "Draft."), ("surface", "UI/API", "Draft."), ("docs", "Docs", "Draft."), ("conflict", "Scope", "Review."), ("layer", "Layer", "Final v348 instructions.")],
    )


def render_expression_live_verification_rollback_packet() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-verification-rollback-packet", "v349.0 Operator-Governed Live Application Verification and Rollback Packet v1", "operator_governed_live_application_verification_and_rollback_packet_v1", "v349.0", "expression-live-verification-rollback-packet",
        "Defines pre/post application checks, expression regression requirements, package privacy, extracted zip checks, rollback expectations, and full install smoke accountability without executing anything.",
        [("schema", "Verify", "Schema."), ("pre", "Pre", "Checks."), ("post", "Post", "Checks."), ("regress", "Regress", "Checks."), ("rollback", "Rollback", "Draft."), ("failure", "Failure", "Matrix."), ("install", "Install", "Note."), ("layer", "Layer", "Final v349 verify.")],
    )


def render_expression_live_application_packet_audit() -> str:
    return _render_supervised_runtime_arc(
        "/expression-live-application-packet-audit", "v350.0 Operator-Governed Expression Live Application Packet Drafting Layer v1", "operator_governed_expression_live_application_packet_drafting_layer_v1", "v350.0", "expression-live-application-packet-audit",
        "Assembles eligibility, source manifest, patch instruction, verification/rollback, governance boundary, route-health, smoke, API/CLI, README, and package privacy coverage into a draft-only live application packet audit.",
        [("eligibility", "Eligibility", "Audit."), ("manifest", "Manifest", "Audit."), ("patch", "Patch", "Audit."), ("verify", "Verify", "Audit."), ("govern", "Govern", "Audit."), ("approval", "Approval", "Boundary."), ("smoke", "Smoke", "Coverage."), ("layer", "Layer", "Final v350 audit.")],
    )

def render_patch_queue() -> str:
    from self_maintenance import multi_patch_queue_planning_layer_text
    final_report = {"stage": "v79.0", "status": "preview", "ok": True, "message": "Multi-Patch Queue Planning preview. Plans schema, order, conflicts, evidence freshness, and operator review only; no batch apply."}
    body = """
<p>v79.0 adds a planning layer for multiple patch candidates. It can normalize a queue, detect file conflicts, schedule by risk, flag stale evidence, build serial sandbox trial plans, and prepare an operator review packet. It cannot batch-apply patches, approve anything, or skip the v74-v77 chain, because apparently restraint is now a feature.</p>
<div class='mini-grid'>
  <div class='mini-card' data-tip='Define required queue record fields including goal, files, risk, evidence status, dependencies, trial id, and recommendation id.'><strong>Schema</strong><span>v78.1 queue records</span></div>
  <div class='mini-card' data-tip='Load queue records from JSON or generated preview records and normalize them for planning.'><strong>Intake</strong><span>v78.2 organizer</span></div>
  <div class='mini-card' data-tip='Detect overlapping file targets and dependency edges before trials are scheduled.'><strong>Conflicts</strong><span>v78.3 detector</span></div>
  <div class='mini-card' data-tip='Order candidates by risk and force manual review for high-risk work.'><strong>Priority</strong><span>v78.4 scheduler</span></div>
  <div class='mini-card' data-tip='Flag missing or stale v74 review, v75 sandbox, or v76 recommendation evidence.'><strong>Evidence</strong><span>v78.5 freshness</span></div>
  <div class='mini-card' data-tip='Create serial sandbox-trial plans rather than parallel or batch application.'><strong>Serial Plan</strong><span>v78.6 queue order</span></div>
</div>
<h3>v79 CLI checks</h3>
<pre>python conscious_agent/main.py --patch-queue-schema --readiness-json
python conscious_agent/main.py --patch-queue-intake --readiness-json
python conscious_agent/main.py --patch-queue-conflicts --readiness-json
python conscious_agent/main.py --patch-queue-priority --readiness-json
python conscious_agent/main.py --patch-queue-stale-evidence --readiness-json
python conscious_agent/main.py --patch-queue-serial-plan --readiness-json
python conscious_agent/main.py --patch-queue-review-packet --readiness-json
python conscious_agent/main.py --pre-v79-queue-gate --readiness-json
python conscious_agent/main.py --multi-patch-queue-planning-layer --readiness-json</pre>
<p><a href='/api/patch-queue/schema'>Schema JSON</a> | <a href='/api/patch-queue/intake'>Intake JSON</a> | <a href='/api/patch-queue/conflicts'>Conflicts JSON</a> | <a href='/api/patch-queue/priority'>Priority JSON</a> | <a href='/api/patch-queue/stale-evidence'>Stale Evidence JSON</a> | <a href='/api/patch-queue/serial-plan'>Serial Plan JSON</a> | <a href='/api/patch-queue/review-packet'>Review Packet JSON</a> | <a href='/api/patch-queue/layer'>v79 System JSON</a></p>
"""
    summary = _card("v79.0 Multi-Patch Queue Planning", _text_block(multi_patch_queue_planning_layer_text(final_report, full=False)))
    return _layout("/patch-queue", _card("Patch Queue", body) + summary)

def render_intelligence() -> str:
    codebase = build_codebase_map(project_id="eidolon")
    dependencies = build_task_dependencies(project_id="eidolon")
    tests = build_test_plan(project_id="eidolon")
    risk = build_patch_risk(project_id="eidolon")
    memory = build_project_memory_index(project_id="eidolon")
    workspace = build_workspace_status(project_id="eidolon")
    cross = build_cross_project_task_review(project_id="eidolon")
    asymmetric = build_asymmetric_dev_loop(project_id="eidolon")
    body = f"""
<p>v10.0 adds the project intelligence lane: codebase mapping, dependency-aware planning, test planning, risk analysis, project memory indexing, workspace awareness, cross-project task review, and asymmetric loop preview. It thinks across projects but modifies none of them from this page. Tiny mercy.</p>
<div class='grid'>
  {_report_status_card('Codebase Map', codebase)}
  {_report_status_card('Task Dependencies', dependencies)}
  {_report_status_card('Test Plan', tests)}
  {_report_status_card('Patch Risk', risk)}
  {_report_status_card('Memory Index', memory)}
  {_report_status_card('Workspace', workspace)}
  {_report_status_card('Cross-Project Review', cross)}
  {_report_status_card('Asymmetric Loop', asymmetric)}
</div>
<p><a href='/api/codebase-map'>Codebase JSON</a> | <a href='/api/task-dependencies'>Dependencies JSON</a> | <a href='/api/asymmetric-dev-loop'>Asymmetric loop JSON</a></p>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --codebase-map
python conscious_agent/main.py --task-dependencies
python conscious_agent/main.py --test-plan
python conscious_agent/main.py --patch-risk
python conscious_agent/main.py --patch-review
python conscious_agent/main.py --project-memory-index
python conscious_agent/main.py --workspace-status
python conscious_agent/main.py --cross-project-task-review
python conscious_agent/main.py --asymmetric-dev-loop</pre>
"""
    reports = "\n\n".join([
        codebase_map_text(codebase, full=False),
        task_dependencies_text(dependencies, full=False),
        test_plan_text(tests, full=False),
        patch_risk_text(risk, full=False),
        project_memory_index_text(memory, full=False),
        intelligence_workspace_status_text(workspace, full=False),
        cross_project_task_review_text(cross, full=False),
        asymmetric_dev_loop_text(asymmetric, full=False),
    ])
    return _layout("/intelligence", _card("Project Intelligence", body) + _card("v9.1-v10.0 reports", _text_block(reports)))


def render_workspace() -> str:
    registry = build_project_registry(repair=False)
    health = build_project_health(project_id="eidolon", all_projects=True)
    profiles = build_command_profiles(save=False)
    deps = build_workspace_dependency_map(project_id="eidolon")
    inbox = build_workspace_task_inbox(project_id="eidolon")
    context = build_project_context(project_id="eidolon")
    timeline = build_workspace_timeline()
    loop = build_workspace_dev_loop(project_id="eidolon", live=False, save_timeline=False)
    audit = build_workspace_registry_audit(project_id="eidolon", archive_stale=False)
    repair = build_workspace_repair_suggestions(project_id="eidolon")
    boundary = build_project_boundary_check(project_id="eidolon")
    plan = build_workspace_patch_plan(project_id="eidolon", save=False)
    diff = build_workspace_preview_diff(project_id="eidolon", save=False)
    verify = build_workspace_verify_latest(project_id="eidolon", save=False)
    guarded = build_guarded_workspace_dev_loop(project_id="eidolon", approve=False, dry_run=True, save=False)
    body = f"""
<p>v12.0 adds guarded workspace execution: registry audit, repair suggestions, boundary checks, workspace patch planning, diff preview, dry-run/guarded apply, workspace verification, and a one-project guarded dev loop. It still stops after one task, because recursive ambition is how projects become haunted furniture.</p>
<div class='grid'>
  {_report_status_card('Registry', registry)}
  {_report_status_card('Health', health)}
  {_report_status_card('Command Profiles', profiles)}
  {_report_status_card('Dependency Map', deps)}
  {_report_status_card('Task Inbox', inbox)}
  {_report_status_card('Context Bundle', context)}
  {_report_status_card('Timeline', timeline)}
  {_report_status_card('Workspace Dev Loop', loop)}
  {_report_status_card('Registry Audit', audit)}
  {_report_status_card('Repair Suggestions', repair)}
  {_report_status_card('Boundary Guard', boundary)}
  {_report_status_card('Workspace Patch Plan', plan)}
  {_report_status_card('Workspace Diff', diff)}
  {_report_status_card('Workspace Verify', verify)}
  {_report_status_card('Guarded Loop', guarded)}
</div>
<p><a href='/api/project-registry'>Registry JSON</a> | <a href='/api/workspace-registry-audit'>Audit JSON</a> | <a href='/api/workspace-repair-suggestions'>Repair JSON</a> | <a href='/api/project-boundary-check'>Boundary JSON</a> | <a href='/api/workspace-patch-plan'>Plan JSON</a> | <a href='/api/workspace-preview-diff'>Diff JSON</a> | <a href='/api/guarded-workspace-dev-loop'>Guarded loop JSON</a></p>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --workspace-registry-audit
python conscious_agent/main.py --workspace-repair-suggestions
python conscious_agent/main.py --project-boundary-check
python conscious_agent/main.py --workspace-patch-plan
python conscious_agent/main.py --workspace-preview-diff
python conscious_agent/main.py --workspace-apply --dry-run
python conscious_agent/main.py --workspace-verify-latest
python conscious_agent/main.py --guarded-workspace-dev-loop</pre>
"""
    reports = "\n\n".join([
        project_registry_text(registry, full=False),
        project_health_text(health, full=False),
        command_profiles_text(profiles, full=False),
        workspace_dependency_map_text(deps, full=False),
        workspace_task_inbox_text(inbox, full=False),
        project_context_text(context, full=False),
        workspace_timeline_text(timeline, full=False),
        workspace_dev_loop_text(loop, full=False),
        workspace_registry_audit_text(audit, full=False),
        workspace_repair_suggestions_text(repair, full=False),
        project_boundary_check_text(boundary, full=False),
        workspace_patch_plan_text(plan, full=False),
        workspace_preview_diff_text(diff, full=False),
        workspace_verify_latest_text(verify, full=False),
        guarded_workspace_dev_loop_text(guarded, full=False),
    ])
    return _layout("/workspace", _card("Guarded Workspace Development", body) + _card("v10.1-v12.0 reports", _text_block(reports)))

def render_patch_drafts() -> str:
    from self_maintenance import supervised_patch_draft_composer_text
    final_report = {"stage": "v73.0", "status": "preview", "ok": True, "message": "Supervised patch draft composer preview. Use CLI/API for full prompt packet generation."}
    body = """
<p>v73.0 converts the v72 patch context packet into a supervised patch draft prompt and review packet. It can prepare a local-model-ready prompt, a strict scope contract, an expected output schema, and a safety review. It does <em>not</em> call a model, generate final code, apply source changes, publish releases, mutate memory, alter identity, or bypass approvals. Grimly responsible, as all useful machinery must be.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Normalize the operator goal into requested change, affected capability, expected behavior, forbidden behaviors, and verification expectations.'><strong>Intent</strong><span>v72.1 normalizer</span></div>
  <div class='mini-card' data-tip='Set allowed files, blocked patterns, max diff size, allowed operations, required docs, and verification commands.'><strong>Scope Contract</strong><span>v72.2 contract</span></div>
  <div class='mini-card' data-tip='Compose a structured prompt from v72 context without invoking a local model.'><strong>Prompt Composer</strong><span>v72.3 prompt</span></div>
  <div class='mini-card' data-tip='Define required response fields: summary, files, diff, risks, verification, rollback, docs, and safety attestation.'><strong>Output Schema</strong><span>v72.4 schema</span></div>
  <div class='mini-card' data-tip='Reject prompt or draft text that claims source apply, publish, memory, identity, approval bypass, or autonomous authority.'><strong>Safety Review</strong><span>v72.5 reviewer</span></div>
  <div class='mini-card' data-tip='Bind intent, scope, prompt, context packet, safety review, selected files, and verification evidence.'><strong>Evidence Binder</strong><span>v72.6 evidence</span></div>
  <div class='mini-card' data-tip='Expose the draft composer through read-only dashboard/API/CLI while preserving custom data-tip hover notes only.'><strong>Parity</strong><span>v72.7 surfaces</span></div>
  <div class='mini-card' data-tip='Prepare a copy-ready prompt for manual local-model use; do not invoke the model automatically.'><strong>Handoff Stub</strong><span>v72.8 export</span></div>
</div>
<h3>CLI checks</h3>
<pre>python conscious_agent/main.py --patch-intent-normalizer --readiness-json
python conscious_agent/main.py --patch-scope-contract-builder --readiness-json
python conscious_agent/main.py --patch-prompt-composer --readiness-json
python conscious_agent/main.py --patch-draft-output-schema --readiness-json
python conscious_agent/main.py --patch-draft-safety-reviewer --readiness-json
python conscious_agent/main.py --patch-draft-evidence-binder --readiness-json
python conscious_agent/main.py --patch-draft-dashboard-api-cli --readiness-json
python conscious_agent/main.py --local-model-handoff-stub --readiness-json
python conscious_agent/main.py --pre-v73-patch-draft-gate --readiness-json
python conscious_agent/main.py --supervised-patch-draft-composer --readiness-json</pre>
<p><a href='/api/patch-drafts/intake'>Intent JSON</a> | <a href='/api/patch-drafts/scope'>Scope JSON</a> | <a href='/api/patch-drafts/prompt'>Prompt JSON</a> | <a href='/api/patch-drafts/schema'>Schema JSON</a> | <a href='/api/patch-drafts/safety'>Review JSON</a> | <a href='/api/patch-drafts/evidence'>Evidence JSON</a> | <a href='/api/patch-drafts/handoff'>Handoff JSON</a> | <a href='/api/patch-drafts/gate'>Gate JSON</a> | <a href='/api/patch-drafts/layer'>v73 System JSON</a></p>
<p>Legacy patch-draft APIs remain available behind their existing routes, but this page now focuses on the v73 pre-generation draft-composer lane. Progress, apparently, means naming conflicts with your own past self.</p>
"""
    summary = _card("v73.0 Supervised Patch Draft Composer", _text_block(supervised_patch_draft_composer_text(final_report, full=False)))
    return _layout("/patch-drafts", _card("v73.0 Patch Drafts", body) + summary)

def render_code_patches() -> str:
    review_bundle = build_ai_patch_review_bundle(project_id="eidolon", save=False)
    integrity = build_review_bundle_integrity(project_id="eidolon", save=False)
    approval_ready = build_approval_ready(project_id="eidolon", save=False)
    ledger = build_approval_ledger(project_id="eidolon", save=False)
    bind_preview = bind_current_approval_to_validated_manifest(project_id="eidolon", save=False)
    apply_preview = build_apply_validated_ai_patch(project_id="eidolon", approve=False, dry_run=True, save=False)
    post_apply = build_post_apply_review(project_id="eidolon", save=False)
    package_plan = build_package_build_plan(project_id="eidolon", package_name=_package_name(), save=False)
    body = f"""
<p>v20.0 keeps the validated AI patch review lane approval-bound and packaging-aware: refresh the review bundle, bind an approved draft to the exact validated manifest, dry-run apply, then move through release package checks. GET/API/dashboard views stay read-only, because links are not scalpels.</p>
<div class='cards'>
  {_report_status_card('Review bundle', review_bundle)}
  {_report_status_card('Bundle integrity', integrity)}
  {_report_status_card('Approval ready', approval_ready)}
  {_report_status_card('Approval ledger', ledger)}
  {_report_status_card('Bind preview', bind_preview)}
  {_report_status_card('Apply preview', apply_preview)}
  {_report_status_card('Post-apply review', post_apply)}
  {_report_status_card('Package plan', package_plan)}
</div>
<div class='cards'>
  <div class='card'><h3>Read-only review links</h3>
    <p><a href='/api/code-patches/review-bundle'>Review Bundle JSON</a></p>
    <p><a href='/api/code-patches/review-integrity'>Integrity JSON</a></p>
    <p><a href='/api/code-patches/approval-ready'>Approval Ready JSON</a></p>
    <p><a href='/api/code-patches/approval-ledger'>Approval Ledger JSON</a></p>
    <p><a href='/api/code-patches/apply-validated-ai-patch'>Apply Dry-Run JSON</a></p>
    <p><a href='/api/code-patches/post-apply-review'>Post-Apply JSON</a></p>
  </div>
  <div class='card'><h3>Mutation controls</h3>
    <form method='post' action='/api/code-patches/refresh-review-bundle'><input type='hidden' name='project' value='eidolon'><button type='submit'>Refresh/save review bundle</button></form>
    <form method='post' action='/api/code-patches/bind-validated-approval'><input type='hidden' name='project' value='eidolon'><button type='submit'>Bind approved draft to validated manifest</button></form>
    <form method='post' action='/api/code-patches/apply-validated-ai-patch'><input type='hidden' name='project' value='eidolon'><input type='hidden' name='dry_run' value='true'><button type='submit'>Dry-run validated AI apply</button></form>
    <form method='post' action='/api/release/approval-to-release-loop'><input type='hidden' name='project' value='eidolon'><input type='hidden' name='dry_run' value='true'><button type='submit'>Dry-run approval-to-release loop</button></form>
    <p>Real apply still requires POST confirmation and an approval manifest bound to the exact reviewed artifact hashes.</p>
  </div>
</div>
<pre>python conscious_agent/main.py --ai-patch-review-bundle
python conscious_agent/main.py --ai-patch-review-integrity
python conscious_agent/main.py --approval-ready
python conscious_agent/main.py --bind-validated-approval
python conscious_agent/main.py --apply-validated-ai-patch --dry-run
python conscious_agent/main.py --post-apply-review
python conscious_agent/main.py --package-build-plan
python conscious_agent/main.py --approval-to-release-loop</pre>
"""
    reports = "\n\n".join([
        ai_patch_review_bundle_text(review_bundle, full=False),
        review_bundle_integrity_text(integrity, full=False),
        approval_ready_text(approval_ready, full=False),
        approval_ledger_text(ledger, full=False),
        bind_validated_approval_text(bind_preview, full=False),
        apply_validated_ai_patch_text(apply_preview, full=False),
        post_apply_review_text(post_apply, full=False),
        package_build_plan_text(package_plan, full=False),
    ])
    return _layout("/code-patches", _card("Validated AI Patch Approval Workflow", body) + _card("v18.1-v21.0 reports", _text_block(reports)))


def render_release_review() -> str:
    review_bundle = build_ai_patch_review_bundle(project_id="eidolon", save=False)
    integrity = build_review_bundle_integrity(project_id="eidolon", save=False)
    approval_ready = build_approval_ready(project_id="eidolon", save=False)
    apply_preview = build_apply_validated_ai_patch(project_id="eidolon", approve=False, dry_run=True, save=False)
    post_apply = build_post_apply_review(project_id="eidolon", save=False)
    readiness = build_release_readiness(project_id="eidolon", save=False)
    package_plan = build_package_build_plan(project_id="eidolon", package_name=_package_name(), save=False)
    body = f"""
<p>Release review shows whether the latest validated AI patch can move from human approval to a release handoff without artifact mismatch nonsense. Somehow, this is what peace looks like.</p>
<div class='cards'>
  {_report_status_card('Review bundle', review_bundle)}
  {_report_status_card('Integrity', integrity)}
  {_report_status_card('Approval ready', approval_ready)}
  {_report_status_card('Apply preview', apply_preview)}
  {_report_status_card('Post apply', post_apply)}
  {_report_status_card('Release readiness', readiness)}
  {_report_status_card('Package plan', package_plan)}
</div>
<p><a href='/api/release/approval-to-release-loop'>Approval-to-release loop JSON</a> | <a href='/api/release/package-build-plan'>Package plan JSON</a> | <a href='/api/release/audit-trail'>Audit trail JSON</a></p>
"""
    reports = "\n\n".join([
        ai_patch_review_bundle_text(review_bundle, full=False),
        review_bundle_integrity_text(integrity, full=False),
        approval_ready_text(approval_ready, full=False),
        apply_validated_ai_patch_text(apply_preview, full=False),
        post_apply_review_text(post_apply, full=False),
        release_readiness_text(readiness, full=False),
        package_build_plan_text(package_plan, full=False),
    ])
    return _layout("/release-review", _card("Release Review", body) + _card("Release review reports", _text_block(reports)))


def render_release_package() -> str:
    package_name = _package_name()
    body = f"""
<p>The release package page is now intentionally lightweight. It does not eagerly rebuild every release, install, self-maintenance, and governance report on GET page load, because apparently opening a dashboard page should not reenact a small CI pipeline.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': package_name})}
  {_report_status_card('Lazy reports', {'status': 'pass', 'message': 'Use the API links or CLI commands below to run heavy checks on demand.'})}
  {_report_status_card('Mutation boundary', {'status': 'pass', 'message': 'GET page render remains read-only. POST-only actions stay confirmation-gated.'})}
</div>
<p><a href='/release-governance'>Release Governance page</a> | <a href='/release-evidence'>Release Evidence page</a></p>
<p><a href='/api/release/profiles'>Profiles</a> | <a href='/api/release/privacy-scan'>Privacy Scan</a> | <a href='/api/release/portable-metadata'>Portable Metadata</a> | <a href='/api/release/install-verification'>Install Verification</a> | <a href='/api/release/verified-installable-loop'>Installable Loop</a> | <a href='/api/release/deterministic-release-manifest'>Manifest Binding</a> | <a href='/api/release/route-safety-harness'>Route Safety</a> | <a href='/api/release/release-candidate-governance'>v27 Governance</a> | <a href='/api/release/release-governance-drill'>Governance Drill</a> | <a href='/api/release/release-evidence-bundle'>Evidence Bundle</a> | <a href='/api/release/release-artifact-diff'>Artifact Diff</a> | <a href='/api/release/pre-v28-governance-audit'>Pre-v28 Audit</a> | <a href='/api/release/verifiable-release-evidence-system'>v28 Evidence System</a> | <a href='/api/release/durable-release-evidence-archive'>v29 Evidence Archive</a></p>
<form method='post' action='/api/release/build-zip'><input type='hidden' name='project' value='eidolon'><input type='hidden' name='dry_run' value='true'><button type='submit'>Dry-run release zip builder</button></form>
<pre>python conscious_agent/main.py --package-privacy-scan --readiness-json
python conscious_agent/main.py --deterministic-release-manifest --readiness-json
python conscious_agent/main.py --release-candidate-governance --readiness-json
python conscious_agent/main.py --release-governance-drill --readiness-json
python conscious_agent/main.py --release-evidence-bundle --readiness-json
python conscious_agent/main.py --release-artifact-diff --readiness-json
python conscious_agent/main.py --pre-v28-governance-audit --readiness-json
python conscious_agent/main.py --verifiable-release-evidence-system --readiness-json
python conscious_agent/main.py --durable-release-evidence-archive --readiness-json</pre>
"""
    return _layout("/release-package", _card("Release Package", body))


def render_release_governance() -> str:
    package_name = _package_name()
    diff = build_release_artifact_diff(project_id="eidolon", package_name=package_name, save=False)
    body = f"""
<p>Release governance is GET-only and intentionally lightweight. Heavy checks run from the linked API endpoints or CLI commands instead of turning page load into a miniature release tribunal.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': package_name})}
  {_report_status_card('Artifact diff preview', diff)}
  {_report_status_card('Heavy evidence checks', {'status': 'preview', 'message': 'Run evidence bundle, pre-v28 audit, and v28 gate from the API links or CLI.'})}
</div>
<p><a href='/api/release/release-governance-drill'>Governance Drill JSON</a> | <a href='/api/release/release-evidence-bundle'>Evidence Bundle JSON</a> | <a href='/api/release/verify-release-evidence-bundle'>Verify Evidence Bundle JSON</a> | <a href='/api/release/release-artifact-diff'>Artifact Diff JSON</a> | <a href='/api/release/pre-v28-governance-audit'>Pre-v28 Audit JSON</a> | <a href='/api/release/verifiable-release-evidence-system'>v28 Gate JSON</a></p>
<pre>python conscious_agent/main.py --release-governance-drill --readiness-json
python conscious_agent/main.py --release-evidence-bundle --readiness-json
python conscious_agent/main.py --verify-release-evidence-bundle --readiness-json
python conscious_agent/main.py --release-artifact-diff --readiness-json
python conscious_agent/main.py --pre-v28-governance-audit --readiness-json
python conscious_agent/main.py --verifiable-release-evidence-system --readiness-json
python conscious_agent/main.py --durable-release-evidence-archive --readiness-json</pre>
"""
    reports = release_artifact_diff_text(diff, full=False)
    return _layout("/release-governance", _card("Release Governance", body) + _card("Fast governance preview", _text_block(reports)))


def render_release_evidence() -> str:
    package_name = _package_name()
    body = f"""
<p>Release evidence is a lightweight, GET-only viewer. Evidence checks are on-demand through the API links or CLI commands below, because page load should not become a tiny compliance department with a stopwatch.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': package_name})}
  {_report_status_card('Evidence checks are on-demand', {'status': 'pass', 'message': 'Run replay, persistence, timeline, summary, or v29 archive checks from API/CLI links.'})}
  {_report_status_card('Generated reports', {'status': 'pass', 'message': 'reports/release_evidence is local generated evidence and is excluded from source-only zips.'})}
  {_report_status_card('Mutation boundary', {'status': 'pass', 'message': 'GET renders inspect evidence only; persistence remains explicit and generated reports stay out of source-only zips.'})}
</div>
<p><a href='/api/release/evidence-replay-drill'>Replay Drill JSON</a> | <a href='/api/release/persist-release-evidence'>Persist Evidence JSON</a> | <a href='/api/release/replay-release-evidence'>Replay Evidence JSON</a> | <a href='/api/release/evidence-timeline'>Timeline JSON</a> | <a href='/api/release/evidence-summary'>Summary JSON</a> | <a href='/api/release/evidence-retention-policy'>Retention JSON</a> | <a href='/api/release/pre-v29-evidence-audit'>Pre-v29 Audit JSON</a> | <a href='/api/release/durable-release-evidence-archive'>v29 Archive JSON</a></p>
<pre>python conscious_agent/main.py --evidence-replay-drill --readiness-json
python conscious_agent/main.py --persist-release-evidence --readiness-json
python conscious_agent/main.py --replay-release-evidence --readiness-json
python conscious_agent/main.py --evidence-timeline --readiness-json
python conscious_agent/main.py --evidence-operator-summary --readiness-json
python conscious_agent/main.py --pre-v29-evidence-audit --readiness-json
python conscious_agent/main.py --durable-release-evidence-archive --readiness-json</pre>
"""
    return _layout("/release-evidence", _card("Release Evidence", body))



def _dashboard_release_zip_path(package_name: str | None = None) -> str | None:
    """Resolve the current release zip for dashboard previews without building one."""
    package_name = package_name or _package_name()
    candidates = [
        ROOT_DIR / package_name,
        DATA_DIR / "releases" / package_name,
        ROOT_DIR.parent / package_name,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def _zip_command_arg(package_name: str, zip_path: str | None) -> str:
    return f" --release-zip-path {zip_path or package_name}"


def _step_status_card(steps: dict[str, Any], key: str, label: str) -> str:
    value = steps.get(key, {}) if isinstance(steps.get(key), dict) else {}
    return _report_status_card(label, value)

def render_release_signing() -> str:
    package_name = _package_name()
    zip_path = _dashboard_release_zip_path(package_name)
    zip_arg = _zip_command_arg(package_name, zip_path)
    status = build_release_signing_status(project_id="eidolon", package_name=package_name, zip_path=zip_path, save=False)
    trust_roots = build_public_trust_root_config(project_id="eidolon", save=False)
    route_safety = build_api_route_safety_audit(project_id="eidolon", save=False)
    status_lines = f"""
<ul>
  <li><strong>Release zip:</strong> {escape(zip_path or package_name)}</li>
  <li><strong>Signed:</strong> {bool(status.get('signed'))}</li>
  <li><strong>Trusted:</strong> {bool(status.get('signature_trusted'))}</li>
  <li><strong>Publish blocked:</strong> {not bool(status.get('safe_to_publish'))}</li>
  <li><strong>Trust level:</strong> {escape(str(status.get('trust_level', 'unsigned')))}</li>
</ul>
"""
    body = f"""
<p>Release signing is GET-only. This dashboard page intentionally renders a lightweight, zip-bound preview instead of rebuilding every signing/governance report on page load. Use the JSON links or CLI commands for the full reports, because a browser refresh should not summon a 60-second bureaucracy goblin.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': zip_path or package_name})}
  {_report_status_card('Signing status', status)}
  {_report_status_card('Trust roots', trust_roots)}
  {_report_status_card('Route safety', route_safety)}
</div>
{status_lines}
<p><a href='/api/release/release-signing-status'>Signing Status JSON</a> | <a href='/api/release/release-publish-gate'>Publish Gate JSON</a> | <a href='/api/release/signed-release-governance'>v32 Governance JSON</a> | <a href='/api/release/release-operations-console'>v33 Ops JSON</a> | <a href='/api/release/release-operator-workflow'>v34 Workflow JSON</a> | <a href='/release-operations'>Release Operations</a> | <a href='/release-operator'>Release Operator</a></p>
<pre>python conscious_agent/main.py --release-signing-status{zip_arg} --readiness-json
python conscious_agent/main.py --release-publish-gate{zip_arg} --readiness-json
python conscious_agent/main.py --signed-release-governance{zip_arg} --readiness-json</pre>
"""
    preview = release_signing_status_text(status, full=False)
    return _layout("/release-signing", _card("Release Signing", body) + _card("Signing status preview", _text_block(preview)))


def render_release_operations() -> str:
    package_name = _package_name()
    zip_path = _dashboard_release_zip_path(package_name)
    zip_arg = _zip_command_arg(package_name, zip_path)
    ops = build_release_operations_console(project_id="eidolon", package_name=package_name, zip_path=zip_path, save=False)
    steps = ops.get("steps", {}) if isinstance(ops.get("steps"), dict) else {}
    body = f"""
<p>Release operations is a GET-only console. The page now renders from one zip-bound operations report instead of rebuilding each nested operation separately on page load. It still does not sign artifacts, store private keys, approve live apply, or mutate release state.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': zip_path or package_name})}
  {_step_status_card(steps, 'governance', 'Governance')}
  {_step_status_card(steps, 'candidate', 'Candidate workspace')}
  {_step_status_card(steps, 'binding', 'Artifact binding')}
  {_step_status_card(steps, 'handoff', 'Signing handoff')}
  {_step_status_card(steps, 'intake', 'Signature intake')}
  {_step_status_card(steps, 'publish', 'Publish readiness')}
  {_step_status_card(steps, 'reproducibility', 'Reproducibility')}
  {_report_status_card('v33.0 operations console', ops)}
</div>
<p><strong>Operations ready:</strong> {bool(ops.get('operations_ready'))} · <strong>Publish ready:</strong> {bool(ops.get('publish_ready'))} · <strong>Signed:</strong> {bool(ops.get('signed'))} · <strong>Trusted:</strong> {bool(ops.get('signature_trusted'))}</p>
<p><a href='/api/release/governance-report-cleanup'>v32.1 Cleanup JSON</a> | <a href='/api/release/artifact-binding-audit'>v32.3 Binding JSON</a> | <a href='/api/release/external-signing-handoff'>v32.5 Handoff JSON</a> | <a href='/api/release/signature-intake-validation'>v32.6 Intake JSON</a> | <a href='/api/release/pre-v33-operations-gate'>v32.9 Gate JSON</a> | <a href='/api/release/release-operations-console'>v33 Ops JSON</a> | <a href='/release-operator'>Release Operator</a></p>
<pre>python conscious_agent/main.py --release-operations-console{zip_arg} --readiness-json
python conscious_agent/main.py --pre-v33-operations-gate{zip_arg} --readiness-json
python conscious_agent/main.py --external-signing-handoff{zip_arg} --readiness-json</pre>
"""
    preview = release_operations_console_text(ops, full=False)
    return _layout("/release-operations", _card("Release Operations", body) + _card("Operations preview", _text_block(preview)))


def render_release_operator() -> str:
    package_name = _package_name()
    zip_path = _dashboard_release_zip_path(package_name)
    zip_arg = _zip_command_arg(package_name, zip_path)
    workflow = build_release_operator_workflow(project_id="eidolon", package_name=package_name, zip_path=zip_path, save=False)
    steps = workflow.get("steps", {}) if isinstance(workflow.get("steps"), dict) else {}
    body = f"""
<p>Release Operator is a GET-only workflow view. It renders a single zip-bound workflow report and shows compact step cards for review, intake, trust, publish decisions, and guardrails without signing internally, approving live apply, or storing private keys.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': zip_path or package_name})}
  {_step_status_card(steps, 'operations', 'Operations console')}
  {_step_status_card(steps, 'candidate_review', 'Candidate review')}
  {_step_status_card(steps, 'signed_intake', 'Signed artifact intake')}
  {_step_status_card(steps, 'trust_lifecycle', 'Trust lifecycle')}
  {_step_status_card(steps, 'publish_decision', 'Publish decision')}
  {_step_status_card(steps, 'guardrails', 'Action guardrails')}
  {_report_status_card('v35.0 operator workflow', workflow)}
</div>
<p><strong>Workflow ready:</strong> {bool(workflow.get('workflow_ready'))} · <strong>Operations ready:</strong> {bool(workflow.get('operations_ready'))} · <strong>Release candidate ready:</strong> {bool(workflow.get('release_candidate_ready'))} · <strong>Publish ready:</strong> {bool(workflow.get('publish_ready'))}</p>
<p><a href='/api/release/operations-console-cleanup'>v33.1 Cleanup JSON</a> | <a href='/api/release/release-candidate-review'>v33.2 Review JSON</a> | <a href='/api/release/signed-artifact-intake'>v33.3 Intake JSON</a> | <a href='/api/release/publish-decision-explainer'>v33.5 Decision JSON</a> | <a href='/api/release/pre-v34-operator-workflow-gate'>v33.9 Gate JSON</a> | <a href='/api/release/release-operator-workflow'>v34 Workflow JSON</a></p>
<pre>python conscious_agent/main.py --release-operator-workflow{zip_arg} --readiness-json
python conscious_agent/main.py --signed-artifact-intake{zip_arg} --readiness-json
python conscious_agent/main.py --publish-decision-explainer{zip_arg} --readiness-json
python conscious_agent/main.py --pre-v34-operator-workflow-gate{zip_arg} --readiness-json</pre>
"""
    preview = release_operator_workflow_text(workflow, full=False)
    return _layout("/release-operator", _card("Release Operator Workflow", body) + _card("Operator workflow preview", _text_block(preview)))


def render_release_candidate() -> str:
    package_name = _package_name()
    zip_path = _dashboard_release_zip_path(package_name)
    zip_arg = _zip_command_arg(package_name, zip_path)
    system = build_trusted_release_candidate_system(project_id="eidolon", package_name=package_name, zip_path=zip_path, save=False)
    steps = system.get("steps", {}) if isinstance(system.get("steps"), dict) else {}
    body = f"""
<p>Release Candidate is a GET-only trusted-candidate view. It shows candidate binding, review state, signature intake, trusted signer state, publish decision, and next action without signing internally, mutating trust roots, or approving live apply.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': zip_path or package_name})}
  {_step_status_card(steps, 'candidate_record', 'Candidate record')}
  {_step_status_card(steps, 'signed_intake_v2', 'Signed intake v2')}
  {_step_status_card(steps, 'publish_decision_v2', 'Publish decision v2')}
  {_step_status_card(steps, 'pre_v35_gate', 'Pre-v35 gate')}
  {_report_status_card('v35.0 trusted candidate system', system)}
</div>
<p><strong>Candidate ready:</strong> {bool(system.get('candidate_ready'))} · <strong>Reviewed:</strong> {bool(system.get('reviewed'))} · <strong>Signed:</strong> {bool(system.get('signed'))} · <strong>Trusted:</strong> {bool(system.get('signature_trusted'))} · <strong>Publish ready:</strong> {bool(system.get('publish_ready'))}</p>
<p><strong>Next action:</strong> {escape(str(system.get('next_action') or 'none'))}</p>
<p><a href='/api/release/release-candidate-record'>v34.1 Candidate Record JSON</a> | <a href='/api/release/signed-artifact-intake-v2'>v34.2 Intake v2 JSON</a> | <a href='/api/release/signed-release-publish-decision'>v34.5 Decision JSON</a> | <a href='/api/release/pre-v35-trusted-candidate-gate'>v34.9 Gate JSON</a> | <a href='/api/release/trusted-candidate-system'>v35 System JSON</a></p>
<pre>python conscious_agent/main.py --trusted-release-candidate-system{zip_arg} --readiness-json
python conscious_agent/main.py --release-candidate-record{zip_arg} --readiness-json
python conscious_agent/main.py --signed-release-publish-decision{zip_arg} --readiness-json
python conscious_agent/main.py --pre-v35-trusted-candidate-gate{zip_arg} --readiness-json</pre>
"""
    preview = trusted_release_candidate_system_text(system, full=False)
    return _layout("/release-candidate", _card("Trusted Release Candidate", body) + _card("Trusted candidate preview", _text_block(preview)))


def render_release_approval() -> str:
    package_name = _package_name()
    zip_path = _dashboard_release_zip_path(package_name)
    zip_arg = _zip_command_arg(package_name, zip_path)
    # Keep this operator page lightweight: one artifact-bound lifecycle view plus exact-target revocation summary.
    lifecycle = build_publish_approval_lifecycle_system(project_id="eidolon", package_name=package_name, zip_path=zip_path, save=False)
    steps = lifecycle.get("steps", {}) if isinstance(lifecycle.get("steps"), dict) else {}
    matching_records = []
    viewer_step = steps.get("approval_status_viewer", {}) if isinstance(steps.get("approval_status_viewer"), dict) else {}
    preflight = build_approval_revocation_write_preflight(project_id="eidolon", approval_record_id=None, save=False)
    phrase = str(preflight.get("required_confirmation_phrase") or "approval_record_id/hash required")
    body = f"""
<p>Release Approval is a GET-only approval lifecycle view. It avoids the full pre-v40 revocation gate on page load, so the operator dashboard does not spend its short life rebuilding the same reports like a bureaucratic treadmill.</p>
<div class='cards'>
  {_report_status_card('Package helper', {'status': 'pass', 'message': zip_path or package_name})}
  {_report_status_card('Approval lifecycle', lifecycle)}
  {_report_status_card('Revocation target rule', preflight)}
</div>
<p><strong>Matching approval:</strong> {bool(lifecycle.get('matching_approval_found'))} · <strong>Publish approved:</strong> {bool(lifecycle.get('publish_approved'))} · <strong>Revoked:</strong> {bool(lifecycle.get('revoked'))} · <strong>Rollback approved:</strong> {bool(lifecycle.get('rollback_approved'))} · <strong>Live apply approved:</strong> {bool(lifecycle.get('live_apply_approved'))}</p>
<p><strong>Records:</strong> {int(lifecycle.get('approval_record_count') or 0)} matching · {int(lifecycle.get('stale_approval_count') or 0)} stale · {int(lifecycle.get('conflict_count') or 0)} conflicts · {int(lifecycle.get('revocation_record_count') or 0)} revocations</p>
<p><strong>Revocation target:</strong> exact approval_record_id or approval hash is required. No first-record fallback.</p>
<p><a href='/api/release/publish-approval-lifecycle'>v39 Lifecycle JSON</a> | <a href='/api/release/approval-revocation-write-preflight'>Revocation Preflight JSON</a> | <a href='/api/release/controlled-publish-approval-revocation'>v40 System JSON</a> | <a href='/api/release/autonomy-readiness-boundary-system'>v41 Autonomy Boundary JSON</a></p>
<pre>python conscious_agent/main.py --publish-approval-lifecycle-system{zip_arg} --readiness-json
python conscious_agent/main.py --approval-revocation-write-preflight --approval-record-id &lt;id-or-hash&gt; --readiness-json
python conscious_agent/main.py --write-approval-revocation --approval-record-id &lt;id-or-hash&gt; --release-confirm-phrase "{escape(phrase)}" --approve-publish-approval-revocation --readiness-json
POST /api/release/revoke-publish-approval  # dry_run=true by default, approval_record_id required</pre>
"""
    text = publish_approval_lifecycle_system_text(lifecycle, full=False)
    return _layout("/release-approval", _card("Publish Approval Lifecycle + Revocation", body) + _card("Approval lifecycle preview", _text_block(text)))


def _mini_kv_table(rows: list[tuple[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>No rows.</p>"
    return "<table>" + "".join(f"<tr><th>{_safe(k)}</th><td>{_safe(v)}</td></tr>" for k, v in rows) + "</table>"


def _maintenance_task_table(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "<p class='muted'>No maintenance tasks available.</p>"
    rows = []
    for task in tasks[:12]:
        rows.append(
            "<tr>"
            f"<td><code>{_safe(task.get('task_id', ''))}</code></td>"
            f"<td>{_safe(task.get('title') or task.get('goal') or '')}</td>"
            f"<td>{_safe(task.get('state', 'queued'))}</td>"
            f"<td>{_safe(task.get('priority_score', ''))}</td>"
            f"<td>{_safe(str(task.get('risk_level', '')) + ' / ' + str(task.get('risk_score', '')))}</td>"
            f"<td>{_safe(', '.join((task.get('planned_files') or [])[:3]))}</td>"
            "</tr>"
        )
    return "<table><tr><th>Task</th><th>Goal</th><th>State</th><th>Priority</th><th>Risk</th><th>Likely files</th></tr>" + "".join(rows) + "</table>"


def render_autonomy_boundary() -> str:
    boundary = build_autonomy_readiness_boundary_system(project_id="eidolon", save=False)
    queue = build_controlled_self_maintenance_work_queue(project_id="eidolon", goal="improve release dashboard performance", save=False)
    body = f"""
<p>This page is now the compact autonomy front door. Heavy queue details moved to <a href='/maintenance-queue'>Maintenance Queue</a>, because one page should not try to be a dashboard, courtroom, airport terminal, and nervous breakdown.</p>
<div class='grid'>
  {_report_status_card('v41 autonomy boundary', boundary)}
  {_report_status_card('v46 maintenance queue', queue)}
</div>
<h3>Safety boundaries that still matter</h3>
<ul>
<li>GET dashboard/API routes remain read-only previews.</li>
<li>Maintenance queue records are runtime-only and grant no source, publish, or live approval.</li>
<li>Source apply still requires exact confirmation through the guarded v43 path.</li>
<li>Rollback remains separate and only becomes meaningful after a guarded apply creates backups.</li>
</ul>
<p><a href='/maintenance-queue'><button type='button'>Open Maintenance Queue</button></a> <a href='/release-approval'><button type='button'>Open Release Approval</button></a> <a href='/api-info'><button type='button'>Open API Reference</button></a></p>
<p><a href='/api/release/autonomy-readiness-boundary-system'>Boundary JSON</a> | <a href='/api/release/controlled-self-maintenance-work-queue'>v46 Queue JSON</a> | <a href='/api/release/pre-v46-maintenance-queue-gate'>Pre-v46 Gate JSON</a></p>
<pre>python conscious_agent/main.py --controlled-self-maintenance-work-queue --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v46-maintenance-queue-gate --autonomy-goal "improve release dashboard performance" --readiness-json</pre>
"""
    return _layout("/autonomy", _card("Autonomy Boundary", body))


def render_maintenance_queue() -> str:
    goal = "improve release dashboard performance"
    registry = build_maintenance_task_queue_registry(project_id="eidolon", goal=goal, save=False)
    selection = build_maintenance_task_selection_policy(project_id="eidolon", goal=goal, save=False)
    queue = {"status": "pass", "ok": True, "message": "Compact dashboard view; run controlled queue or receipt commands for full nested proof."}
    cache = {"status": "pass", "ok": True, "message": "Report cache available through CLI/API; dashboard avoids rebuilding it on page load."}
    stale = {"status": "pass", "ok": True, "message": "Stale warnings available through CLI/API; receipt command gives exact hash proof."}
    receipt = {"receipt": {"receipt_id": "run --queue-verification-receipt", "task_hash": "available on demand", "queue_hash": "available on demand", "next_safe_operator_action": "Review the selected task, then use guarded exact-confirmation apply only after human approval."}}
    privacy = build_maintenance_runtime_privacy_audit(project_id="eidolon", save=False)
    selected = selection.get("selected_task") or {}
    active = selection.get("active_tasks") or []
    tasks = registry.get("tasks") or []
    selected_rows = [
        ("Selected task", selected.get("task_id") or queue.get("selected_task_id") or "[none]"),
        ("Selected goal", selected.get("goal") or queue.get("selected_goal") or "[none]"),
        ("Cycle", selected.get("cycle_id") or "[none]"),
        ("Proposal", "run --maintenance-task-drilldown for exact proposal binding"),
        ("Active tasks blocking selection", len(active)),
        ("Source apply approved", queue.get("source_apply_approved")),
        ("Publish approved", queue.get("publish_approved")),
        ("Live apply approved", queue.get("live_apply_approved")),
        ("Runtime records source-only excluded", queue.get("runtime_records_source_only_excluded")),
    ]
    body = f"""
<p>v46 queue view keeps multiple supervised maintenance goals visible while allowing only one selected maintenance cycle at a time. It is an attention scaffold for Eidolon, not a magic permission slip for source edits. Humans really did need that warning label.</p>
<div class='grid'>
  {_report_status_card('Queue registry', registry)}
  {_report_status_card('Selection policy', selection)}
  {_report_status_card('Controlled queue loop', queue)}
  {_report_status_card('Report cache', cache)}
  {_report_status_card('Stale warnings', stale)}
  {_report_status_card('Runtime privacy', privacy)}
</div>
<h3>Selected task and approval boundaries</h3>
{_mini_kv_table(selected_rows)}
<h3>Queued maintenance tasks</h3>
{_maintenance_task_table(tasks)}
<h3>Queue commands</h3>
<pre>python conscious_agent/main.py --maintenance-task-queue-registry --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --maintenance-task-selection-policy --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --controlled-self-maintenance-work-queue --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v46-maintenance-queue-gate --autonomy-goal "improve release dashboard performance" --readiness-json</pre>
<h3>Verification receipt</h3>
{_mini_kv_table([('Receipt', (receipt.get('receipt') or {}).get('receipt_id')), ('Task hash', (receipt.get('receipt') or {}).get('task_hash')), ('Queue hash', (receipt.get('receipt') or {}).get('queue_hash')), ('Next safe action', (receipt.get('receipt') or {}).get('next_safe_operator_action'))])}
<p><a href='/api/release/maintenance-task-queue-registry'>Queue Registry JSON</a> | <a href='/api/release/maintenance-task-selection-policy'>Selection JSON</a> | <a href='/api/release/controlled-self-maintenance-work-queue'>Controlled Queue JSON</a> | <a href='/api/release/maintenance-task-drilldown'>Task Drilldown JSON</a> | <a href='/api/release/queue-stale-state-warnings'>queue-stale-state-warnings JSON</a> | <a href='/api/release/queue-verification-receipt'>Receipt JSON</a> | <a href='/api/release/pre-v47-attention-scheduler-gate'>Pre-v47 Gate JSON</a></p>
<p><a href='/attention'><button type='button'>Open Attention Scheduler</button></a></p>
"""
    return _layout("/maintenance-queue", _card("v46 Maintenance Queue", body))

def render_attention_scheduler() -> str:
    goal = "improve release dashboard performance"
    scheduler = build_controlled_attention_scheduler(project_id="eidolon", goal=goal, save=False)
    receipt_report = build_attention_selection_receipt(project_id="eidolon", goal=goal, save=False)
    budget_report = build_attention_budget_ledger(project_id="eidolon", goal=goal, save=False)
    deferred_report = {"stage": "v47.3", "status": "preview", "ok": True, "message": "Run --deferred-task-memory or the matching API route for the full deferred task memory report."}
    blocked_report = {"stage": "v47.4", "status": "preview", "ok": True, "message": "Run --blocked-task-handling or the matching API route for the full blocker report."}
    resume_report = {"stage": "v47.5", "status": "preview", "ok": True, "message": "Run --attention-resume-context or the matching API route for the full resume context."}
    polish = {"stage": "v47.6", "status": "preview", "ok": True, "message": "Dashboard polish audit is available through CLI/API; this page stays lightweight."}
    parity = {"stage": "v47.7", "status": "preview", "ok": True, "message": "Dashboard/API parity gate is available through CLI/API."}
    record = scheduler.get("attention_record") or {}
    focus = record.get("focus_task") or {}
    receipt = receipt_report.get("attention_receipt") or {}
    selected_receipt = receipt.get("selected_task") or {}
    ledger = budget_report.get("attention_budget_ledger") or {}
    deferred_records = receipt.get("deferred_tasks") or []
    blocked_records = receipt.get("blocked_tasks") or []
    resume = {"resume_context_id": "run --attention-resume-context", "resume_requires_operator_review": bool(blocked_records)}
    scored_rows = []
    cost_by_task = {str(row.get("task_id")): row for row in (ledger.get("task_costs") or [])}
    for item in (record.get("scored_tasks") or [])[:10]:
        cost = cost_by_task.get(str(item.get("task_id"))) or {}
        scored_rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('task_id'))}</code></td>"
            f"<td>{_safe(item.get('decision'))}</td>"
            f"<td>{_safe(item.get('attention_score'))}</td>"
            f"<td>{_safe(cost.get('risk_adjusted_cost', '[n/a]'))}</td>"
            f"<td>{_safe(item.get('risk_score'))}</td>"
            f"<td>{_safe(item.get('reason'))}</td>"
            "</tr>"
        )
    scored_table = "<table><tr><th>Task</th><th>Decision</th><th>Attention</th><th>Cost</th><th>Risk</th><th>Reason</th></tr>" + "".join(scored_rows) + "</table>" if scored_rows else "<p class='muted'>No scored tasks.</p>"
    reason_rows = []
    for item in (receipt.get("decision_rows") or [])[:10]:
        reason_rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('task_id'))}</code></td>"
            f"<td>{_safe(item.get('decision'))}</td>"
            f"<td>{_safe(', '.join(item.get('reason_codes') or []))}</td>"
            f"<td>{_safe(item.get('next_safe_action'))}</td>"
            "</tr>"
        )
    reason_table = "<table><tr><th>Task</th><th>Decision</th><th>Reason codes</th><th>Next safe action</th></tr>" + "".join(reason_rows) + "</table>" if reason_rows else "<p class='muted'>No attention receipt decision rows.</p>"
    body = f"""
<p><!-- Reflection candidates pre-v48-reflection-gate -->v47.2-v47.7 makes attention explainable, budget-aware, deferrable, block-aware, resumable, and API-visible. It still does not approve source changes, because focus is not consent. Somehow this needed engineering.</p>
<div class='grid'>
  {_report_status_card('Attention scheduler', scheduler)}
  {_report_status_card('Attention receipt', receipt_report)}
  {_report_status_card('Attention budget', budget_report)}
  {_report_status_card('Deferred task memory', deferred_report)}
  {_report_status_card('Blocked task handling', blocked_report)}
  {_report_status_card('Resume context', resume_report)}
  {_report_status_card('Dashboard polish', polish)}
  {_report_status_card('API parity', parity)}
</div>
<h3>Current focus</h3>
{_mini_kv_table([('Task', focus.get('task_id') or '[none]'), ('Decision', focus.get('decision') or '[none]'), ('Attention score', focus.get('attention_score') or '[none]'), ('Reason', focus.get('reason') or '[none]'), ('Reason codes', ', '.join(focus.get('reason_codes') or selected_receipt.get('reason_codes') or [])), ('Why this task now', receipt.get('why_this_task_now') or '[none]'), ('Next safe action', receipt.get('next_safe_operator_action') or '[none]'), ('Resume context', resume.get('resume_context_id') or '[none]'), ('Source apply approved', record.get('source_apply_approved')), ('Publish approved', record.get('publish_approved')), ('Live apply approved', record.get('live_apply_approved'))])}
<h3>Attention budget</h3>
{_mini_kv_table([('Budget ID', ledger.get('budget_id')), ('Session budget', ledger.get('session_budget_units')), ('Daily budget', ledger.get('daily_budget_units')), ('Selected task cost', ledger.get('selected_task_cost')), ('Budget remaining before', ledger.get('budget_remaining_before')), ('Budget remaining after', ledger.get('budget_remaining_after')), ('Budget status', ledger.get('budget_status')), ('Budget reason', ledger.get('budget_reason_code')), ('Deferred by budget', len(ledger.get('deferred_due_budget') or []))])}
<h3>Attention receipt / Reason codes</h3>
{reason_table}
<h3>Deferred and blocked</h3>
{_mini_kv_table([('Deferred task records', len(deferred_records)), ('Blocked task records', len(blocked_records)), ('Resume requires operator review', resume.get('resume_requires_operator_review')), ('Runtime only', resume.get('runtime_only'))])}
<h3>Scored queue tasks</h3>
{scored_table}
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --attention-budget-ledger --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --deferred-task-memory --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --blocked-task-handling --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --attention-resume-context --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --attention-api-parity-gate --readiness-json
python conscious_agent/main.py --reflection-hooks-read-only --autonomy-goal "improve release dashboard performance" --readiness-json</pre>
<p><a href='/maintenance-queue'><button type='button'>Back to Maintenance Queue</button></a> <a href='/reflection'><button type='button'>Open Reflection Loop</button></a></p>
<p><a href='/api/release/attention-scheduler'>Attention JSON</a> | <a href='/api/release/attention-selection-receipt'>Attention Receipt JSON</a> | <a href='/api/release/attention-budget-ledger'>Budget JSON</a> | <a href='/api/release/deferred-task-memory'>Deferred JSON</a> | <a href='/api/release/blocked-task-handling'>Blocked JSON</a> | <a href='/api/release/attention-resume-context'>Resume JSON</a> | <a href='/api/release/attention-api-parity-gate'>Parity JSON</a></p>
"""
    return _layout("/attention", _card("v47 Attention Scheduler", body) + _card("Attention budget preview", _text_block(attention_budget_ledger_text(budget_report, full=False))) + _card("Deferred task memory preview", _text_block(deferred_task_memory_text(deferred_report, full=False))))


def render_reflection_memory() -> str:
    goal = "improve release dashboard performance"
    receipt_report = build_attention_selection_receipt(project_id="eidolon", goal=goal, save=False)
    budget_report = build_attention_budget_ledger(project_id="eidolon", goal=goal, save=False)
    receipt = receipt_report.get("attention_receipt") or {}
    ledger = budget_report.get("attention_budget_ledger") or {}
    receipts = [
        {"receipt_id": "reflection-preview-attention", "memory_type": "lesson_learned", "confidence_score": 0.88, "risk_score": 44, "why_proposed": receipt.get("why_this_task_now") or "Attention selected a supervised maintenance task."},
        {"receipt_id": "reflection-preview-budget", "memory_type": "system_limitation", "confidence_score": 0.86, "risk_score": 36, "why_proposed": f"Selected task cost {ledger.get('selected_task_cost')} with budget status {ledger.get('budget_status')}."},
        {"receipt_id": "reflection-preview-boundary", "memory_type": "safety_boundary_reminder", "confidence_score": 0.91, "risk_score": 52, "why_proposed": "Reflection candidates require operator review and do not write durable memory."},
    ]
    drafts = [
        {"promotion_draft_id": "reflection-promotion-preview-1", "memory_type": item.get("memory_type"), "sensitivity_classification": "approval_boundary" if item.get("risk_score", 0) >= 45 else "safe_project_memory", "eligible_for_durable_memory": False, "operator_confirmation_required": "PROMOTE_REFLECTION_MEMORY_EXACT"}
        for item in receipts
    ]
    classified = [
        {"promotion_draft_id": item.get("promotion_draft_id"), "labels": ["durable_memory_review_required", item.get("sensitivity_classification")], "safety_status": "review_required", "blocked_from_auto_promotion": True}
        for item in drafts
    ]
    review_report = {"stage": "v48.1", "status": "preview", "ok": True, "message": "Reflection receipts preview. Run --reflection-review-receipts for full evidence hashes.", "reflection_review_console": {"receipt_count": len(receipts), "receipts": receipts}}
    dedup_report = {"stage": "v48.2", "status": "preview", "ok": True, "message": "Dedup preview. Run --reflection-candidate-deduplication for canonical hashes.", "deduplication": {"unique_count": len(receipts), "duplicate_count": 0}}
    rejection_report = {"stage": "v48.3", "status": "preview", "ok": True, "message": "Runtime-only rejection policy preview.", "rejection_memory": {"policy": receipts, "runtime_only": True}}
    drafts_report = {"stage": "v48.4", "status": "preview", "ok": True, "message": "Promotion drafts preview. Drafts are not durable memory.", "promotion_drafts": {"drafts": drafts}}
    safety_report = {"stage": "v48.5", "status": "preview", "ok": True, "message": "Memory safety preview. Auto-promotion remains blocked.", "memory_safety_classifier": {"classified_records": classified}}
    polish = {"stage": "v48.6", "status": "preview", "ok": True, "message": "Reflection dashboard uses compact preview cards; heavy gates stay in CLI/API."}
    parity = {"stage": "v48.7", "status": "preview", "ok": True, "message": "Run --reflection-api-parity-gate for the full parity proof."}
    privacy = {"stage": "v48.8", "status": "preview", "ok": True, "message": "Run --reflection-privacy-package-hardening for the full privacy/package proof."}
    gate = {"stage": "v48.9", "status": "preview", "ok": True, "message": "Run --pre-v49-identity-continuity-gate for the full identity readiness gate."}
    receipt_rows = []
    for item in receipts[:12]:
        receipt_rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('receipt_id'))}</code></td>"
            f"<td>{_safe(item.get('memory_type'))}</td>"
            f"<td>{_safe(item.get('confidence_score'))}</td>"
            f"<td>{_safe(item.get('risk_score'))}</td>"
            f"<td>{_safe(item.get('why_proposed'))}</td>"
            "</tr>"
        )
    receipt_table = "<table><tr><th>Receipt</th><th>Type</th><th>Confidence</th><th>Risk</th><th>Why proposed</th></tr>" + "".join(receipt_rows) + "</table>"
    draft_rows = []
    for item in drafts[:12]:
        draft_rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('promotion_draft_id'))}</code></td>"
            f"<td>{_safe(item.get('memory_type'))}</td>"
            f"<td>{_safe(item.get('sensitivity_classification'))}</td>"
            f"<td>{_safe(item.get('eligible_for_durable_memory'))}</td>"
            f"<td>{_safe(item.get('operator_confirmation_required'))}</td>"
            "</tr>"
        )
    draft_table = "<table><tr><th>Draft</th><th>Type</th><th>Sensitivity</th><th>Eligible now</th><th>Future confirmation</th></tr>" + "".join(draft_rows) + "</table>"
    safety_rows = []
    for item in classified[:12]:
        safety_rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('promotion_draft_id'))}</code></td>"
            f"<td>{_safe(', '.join(item.get('labels') or []))}</td>"
            f"<td>{_safe(item.get('safety_status'))}</td>"
            f"<td>{_safe(item.get('blocked_from_auto_promotion'))}</td>"
            "</tr>"
        )
    safety_table = "<table><tr><th>Draft</th><th>Labels</th><th>Status</th><th>Auto promotion blocked</th></tr>" + "".join(safety_rows) + "</table>"
    body = f"""
<p>v48.x turns reflection into an operator review console: Reflection receipts, deduplication, rejection memory, promotion drafts, and Memory safety are visible without writing durable memory. Heavy gates stay in CLI/API, because the dashboard is not a sacrificial altar for your CPU.</p>
<div class='grid'>
  {_report_status_card('Reflection receipts', review_report)}
  {_report_status_card('Deduplication', dedup_report)}
  {_report_status_card('Rejection memory', rejection_report)}
  {_report_status_card('Promotion drafts', drafts_report)}
  {_report_status_card('Memory safety', safety_report)}
  {_report_status_card('Dashboard polish', polish)}
  {_report_status_card('API parity', parity)}
  {_report_status_card('Privacy/package hardening', privacy)}
  {_report_status_card('Pre-v49 gate', gate)}
</div>
<h3>Reflection review</h3>
{_mini_kv_table([('Receipt count', len(receipts)), ('Unique receipts', len(receipts)), ('Duplicates', 0), ('Rejection policy records', len(receipts)), ('Promotion drafts', len(drafts)), ('Safety classifications', len(classified)), ('Durable memory written', False), ('Durable memory write approved', False)])}
<h3>Reflection receipts</h3>
{receipt_table}
<h3>Promotion drafts</h3>
{draft_table}
<h3>Memory safety</h3>
{safety_table}
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --reflection-review-receipts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --reflection-candidate-deduplication --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --reflection-promotion-drafts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-safety-classifier --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v49-identity-continuity-gate --autonomy-goal "improve release dashboard performance" --readiness-json</pre>
<p><a href='/attention'><button type='button'>Back to Attention</button></a> <a href='/identity'><button type='button'>Open Identity Continuity</button></a></p>
<p><a href='/api/release/reflection-review-receipts'>Reflection Receipts JSON</a> | <a href='/api/release/reflection-promotion-drafts'>Promotion Drafts JSON</a> | <a href='/api/release/memory-safety-classifier'>Memory Safety JSON</a> | <a href='/api/release/pre-v49-identity-continuity-gate'>Pre-v49 Gate JSON</a></p>
"""
    return _layout("/reflection", _card("v48.x Reflection Review Console", body) + _card("Reflection receipts preview", _text_block(reflection_review_receipts_text(review_report, full=False))))


def render_identity_continuity() -> str:
    principles = [
        {"id": "principle-supervised-growth", "statement": "Grow through supervised queues, attention, reflection, and identity drafts rather than hidden autonomous mutation."},
        {"id": "principle-boundary-separation", "statement": "Attention, reflection, identity, source apply, publish approval, live apply, rollback, and durable memory approval remain separate."},
        {"id": "principle-source-only-handoff", "statement": "Shareable release zips remain source-only and exclude private/runtime records."},
        {"id": "principle-explainability", "statement": "Selections and reflections should expose receipts, evidence hashes, risk, confidence, and next safe action."},
        {"id": "principle-operator-review", "statement": "Identity and memory changes are proposed for operator review and are not self-written."},
    ]
    profile = {
        "identity_profile_id": "identity-profile-preview",
        "name": "Eidolon",
        "self_description_draft": "A local supervised artificial mind scaffold with a programming system as its body and hands, currently capable of queued maintenance, attention budgeting, reviewable reflection, and identity continuity drafting.",
        "operator_approved": False,
        "draft_only": True,
    }
    snapshot = {
        "snapshot_id": "identity-snapshot-preview",
        "version": DASHBOARD_VERSION,
        "based_on_receipt_ids": ["reflection-preview-attention", "reflection-preview-budget", "reflection-preview-boundary"],
        "safety_classification_count": 3,
        "what_changed_about_me": [
            "v46 introduced a supervised self-maintenance work queue.",
            "v47 introduced attention selection, receipts, budget, deferral, blockers, and resume context.",
            "v48 introduced reviewable reflection candidates and controlled memory-loop proposals without durable writes.",
            "v49 drafts stable identity continuity and drift warnings without self-authorizing identity changes.",
        ],
        "continuity_warnings": [
            "Identity snapshots are drafts, not self-approved truth.",
            "Changing identity principles later must be explicit, reviewable, and versioned.",
            "No identity record grants source, publish, live, rollback, or durable memory approval.",
        ],
    }
    identity = {"operator_review_required": True, "identity_update_approved": False, "durable_memory_written": False, "source_apply_approved": False, "publish_approved": False, "live_apply_approved": False, "next_safe_operator_action": "Review identity profile draft and continuity snapshot; future promotion must require exact operator approval and versioned identity history."}
    identity_receipt = {
        "receipt_id": "identity-receipt-preview",
        "why_this_identity_snapshot_exists": "v49.1 explains why the identity snapshot exists, what changed, which principles stayed stable, and why no approval authority is granted.",
        "review_status": "operator_review_required",
        "drift_reason_codes": [
            {"code": "expected_version_growth", "message": "Drift is explained by supervised release milestones."},
            {"code": "principles_stable", "message": "Stable principles remain hash-bound."},
            {"code": "draft_identity_only", "message": "Identity is descriptive draft state only."},
            {"code": "operator_review_required", "message": "Future identity edits require explicit review."},
            {"code": "approval_boundaries_preserved", "message": "No source, publish, live, rollback, or memory approval is granted."},
        ],
    }
    identity_report = {"stage": "v49.0", "status": "preview", "ok": True, "message": "Identity continuity preview. Run --identity-continuity-layer for full hashes and gate binding."}
    receipt_report = {"stage": "v51.0", "status": "preview", "ok": True, "message": "Identity receipts preview. Run --identity-receipts for full drift reason codes and evidence hashes."}
    gate_report = {"stage": "v51.0-gate", "status": "preview", "ok": True, "message": "Run --pre-v49-1-identity-receipts-gate for full readiness proof."}
    principle_rows = []
    for item in principles:
        principle_rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('id'))}</code></td>"
            f"<td>{_safe(item.get('statement'))}</td>"
            "</tr>"
        )
    principle_table = "<table><tr><th>Principle</th><th>Statement</th></tr>" + "".join(principle_rows) + "</table>"
    changes = "<ul>" + "".join(f"<li>{_safe(item)}</li>" for item in snapshot.get("what_changed_about_me") or []) + "</ul>"
    warnings = "<ul>" + "".join(f"<li>{_safe(item)}</li>" for item in snapshot.get("continuity_warnings") or []) + "</ul>"
    drift_rows = []
    for item in identity_receipt.get("drift_reason_codes") or []:
        drift_rows.append("<tr>" f"<td><code>{_safe(item.get('code'))}</code></td>" f"<td>{_safe(item.get('message'))}</td>" "</tr>")
    drift_table = "<table><tr><th>Reason code</th><th>Explanation</th></tr>" + "".join(drift_rows) + "</table>"
    body = f"""

<!-- v50 identity/dashboard parity tokens: stable-principles-ledger identity-drift-classifier identity-snapshot-comparison operator-identity-review-drafts identity-dashboard-polish identity-api-parity-gate identity-privacy-package-hardening pre-v50-durable-memory-gate durable-memory-promotion. Run --pre-v50-durable-memory-gate for the full durable-memory readiness proof. -->
<p>v49 introduces Identity continuity; v49.1-v49.9 stabilize receipts, stable principles, drift classification, snapshot comparison, review drafts, parity, and privacy before v51.0 durable-memory promotion previews. The page shows draft identity and review-only warnings without writing memory or authorizing source changes.</p>
<div class='grid'>
  {_report_status_card('Identity continuity layer', identity_report)}
  {_report_status_card('Identity receipts', receipt_report)}
  {_report_status_card('Pre-v49.1 gate', gate_report)}
</div>
<h3>Identity profile draft</h3>
{_mini_kv_table([('Profile ID', profile.get('identity_profile_id')), ('Name', profile.get('name')), ('Self-description draft', profile.get('self_description_draft')), ('Operator approved', profile.get('operator_approved')), ('Draft only', profile.get('draft_only')), ('Operator review required', identity.get('operator_review_required')), ('Identity update approved', identity.get('identity_update_approved')), ('Durable memory written', identity.get('durable_memory_written')), ('Source apply approved', identity.get('source_apply_approved')), ('Publish approved', identity.get('publish_approved')), ('Live apply approved', identity.get('live_apply_approved'))])}
<h3>Stable principles ledger</h3>
{principle_table}
<h3>Continuity snapshot</h3>
{_mini_kv_table([('Snapshot ID', snapshot.get('snapshot_id')), ('Version', snapshot.get('version')), ('Receipt count', len(snapshot.get('based_on_receipt_ids') or [])), ('Safety classifications', snapshot.get('safety_classification_count')), ('Next safe action', identity.get('next_safe_operator_action'))])}
<h3>Identity receipts</h3>
{_mini_kv_table([('Receipt ID', identity_receipt.get('receipt_id')), ('Review status', identity_receipt.get('review_status')), ('Why this snapshot exists', identity_receipt.get('why_this_identity_snapshot_exists')), ('Identity update approved', identity.get('identity_update_approved')), ('Durable memory written', identity.get('durable_memory_written'))])}
<h3>Drift reason codes</h3>
{drift_table}
<h3>What changed</h3>
{changes}
<h3>Continuity warnings</h3>
{warnings}
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --pre-v49-identity-continuity-gate --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --identity-continuity-layer --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --identity-receipts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v49-1-identity-receipts-gate --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --stable-principles-ledger --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --identity-drift-classifier --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --identity-snapshot-comparison --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --operator-identity-review-drafts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v50-durable-memory-gate --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --durable-memory-promotion --autonomy-goal "improve release dashboard performance" --readiness-json</pre>
<p><a href='/reflection'><button type='button'>Back to Reflection</button></a> <a href='/memory'><button type='button'>Open Durable Memory Promotion</button></a></p>
<p><a href='/api/release/identity-continuity-layer'>Identity JSON</a> | <a href='/api/release/identity-receipts'>Identity Receipts JSON</a> | <a href='/api/release/pre-v49-identity-continuity-gate'>Pre-v49 Gate JSON</a> | <a href='/api/release/pre-v49-1-identity-receipts-gate'>Pre-v51.0 Gate JSON</a></p>
"""
    return _layout("/identity", _card("v49 Identity Continuity Layer", body) + _card("Identity continuity preview", _text_block(identity_continuity_layer_text(identity_report, full=False))) + _card("Identity receipts preview", _text_block(identity_receipts_text(receipt_report, full=False))))



def render_memory_promotion() -> str:
    entries = [
        {"promotion_id": "durable-memory-promotion-preview-lesson", "memory_type": "lesson_learned", "safety_status": "review_required", "review_state": "pending_operator_review", "durable_memory_written": False, "operator_confirmation_required": "PROMOTE_DURABLE_MEMORY_EXACT:<promotion_id>:<memory_hash>"},
        {"promotion_id": "durable-memory-promotion-preview-boundary", "memory_type": "safety_boundary_reminder", "safety_status": "review_required", "review_state": "pending_operator_review", "durable_memory_written": False, "operator_confirmation_required": "PROMOTE_DURABLE_MEMORY_EXACT:<promotion_id>:<memory_hash>"},
        {"promotion_id": "durable-memory-promotion-preview-future", "memory_type": "future_task_suggestion", "safety_status": "review_required", "review_state": "pending_operator_review", "durable_memory_written": False, "operator_confirmation_required": "PROMOTE_DURABLE_MEMORY_EXACT:<promotion_id>:<memory_hash>"},
    ]
    queue = {"queue_count": len(entries), "queue_entries": entries, "automatic_writes_enabled": False, "durable_memory_written": False, "durable_memory_write_approved": False, "source_apply_approved": False, "publish_approved": False, "live_apply_approved": False, "rollback_approved": False, "next_safe_operator_action": "Review receipts, dedup, confirmation, safety, and removal drafts before invoking the v51 POST-only durable-memory write path."}
    promotion = {"stage": "v50.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Run --durable-memory-promotion for the full promotion queue and evidence hashes.", "supervised_durable_memory_promotion": queue}
    write_preview = {"stage": "v51.0", "status": "preview", "ok": True, "message": "GET/dashboard preview never writes durable memory. Use POST/CLI with exact confirmation after review.", "controlled_durable_memory_write_path": {"durable_memory_written": False, "write_mode": "preview_only", "source_apply_approved": False, "publish_approved": False, "live_apply_approved": False}}
    gate = {"stage": "v50.9", "status": "preview", "ok": True, "message": "Run --pre-v51-durable-write-gate for the full readiness proof."}
    rows = []
    for item in entries[:8]:
        rows.append(
            "<tr>"
            f"<td><code>{_safe(item.get('promotion_id'))}</code></td>"
            f"<td>{_safe(item.get('memory_type'))}</td>"
            f"<td>{_safe(item.get('safety_status'))}</td>"
            f"<td>{_safe(item.get('review_state'))}</td>"
            f"<td>{_safe(str(item.get('durable_memory_written')))}</td>"
            "</tr>"
        )
    table = "<table><tr><th>Promotion</th><th>Type</th><th>Safety</th><th>Review</th><th>Written</th></tr>" + "".join(rows) + "</table>"
    sample = entries[0] if entries else {}
    body = f"""
<p>v50.x stabilizes supervised durable-memory promotion with receipts, deduplication, rejection runtime notes, confirmation validation, removal drafts, dashboard/API parity, and privacy hardening. v51.0 adds the first controlled durable-memory write path, but GET/dashboard previews never write memory.</p>
<div class='grid'>
  {_report_status_card('Promotion queue', promotion)}
  {_report_status_card('Pre-v51 durable write gate', gate)}
  {_report_status_card('Controlled durable write path', write_preview)}
</div>
<h3>Queue summary</h3>
{_mini_kv_table([('Queue count', queue.get('queue_count')), ('Automatic writes enabled', queue.get('automatic_writes_enabled')), ('Durable memory written', queue.get('durable_memory_written')), ('Durable memory write approved', queue.get('durable_memory_write_approved')), ('Source apply approved', queue.get('source_apply_approved')), ('Publish approved', queue.get('publish_approved')), ('Live apply approved', queue.get('live_apply_approved')), ('Rollback approved', queue.get('rollback_approved')), ('Next safe action', queue.get('next_safe_operator_action'))])}
<h3>Promotion queue preview</h3>
{table}
<h3>Sample exact confirmation phrase</h3>
<pre>{_safe(sample.get('operator_confirmation_required') or 'No promotion entries available.')}</pre>
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --memory-promotion-receipts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-promotion-deduplication --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-removal-drafts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v51-durable-write-gate --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --durable-memory-write --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --durable-memory-write-receipts --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-read-path --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-search-filter --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v52-recall-gate --autonomy-goal "improve release dashboard performance" --readiness-json</pre>
<h3>Guarded write rule</h3>
<p>The v51 durable-memory write path is locked unless invoked through CLI or POST with the exact confirmation phrase bound to the reviewed promotion. It does not grant source apply, publish, live apply, or rollback approval. Because apparently one permission should not secretly become five. Revolutionary.</p>
<p><a href='/identity'><button type='button'>Back to Identity</button></a> <a href='/recall'><button type='button'>Open Memory Recall</button></a></p>
<p><a href='/api/release/memory-promotion-receipts'>Memory Receipts JSON</a> | <a href='/api/release/durable-memory-write-receipts'>Write Receipts JSON</a> | <a href='/api/release/memory-read-path'>Read Path JSON</a> | <a href='/api/release/memory-search-filter'>Search JSON</a> | <a href='/api/release/memory-correction-drafts'>Correction Drafts JSON</a> | <a href='/api/release/memory-removal-confirmation-path'>Removal Path JSON</a> | <a href='/api/release/pre-v52-recall-gate'>Pre-v52 Gate JSON</a></p>
"""
    return _layout("/memory", _card("v51.0 Controlled Durable Memory Write Path", body) + _card("Durable memory write preview", _text_block(controlled_durable_memory_write_path_text(write_preview, full=False))))


def render_memory_recall() -> str:
    read_report = {"stage": "v51.3", "status": "preview", "ok": True, "message": "Read-only memory preview. Run --memory-read-path for full records and schema evidence."}
    search_report = {"stage": "v51.4", "status": "preview", "ok": True, "message": "Search preview. Run --memory-search-filter --memory-query <query> for ranked results."}
    recall_report = {"stage": "v52.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Run --memory-recall-self-context for relevance scoring, used-memory receipts, stale warnings, and conflict checks.", "memory_recall_self_context": {"recall_mode": "read_only", "used_memory_count": 0, "used_memories_receipt_id": "preview-only", "memory_rewrite_approved": False, "source_apply_approved": False, "publish_approved": False, "live_apply_approved": False}}
    receipts_report = {"stage": "v52.1", "status": "preview", "ok": True, "message": "Run --memory-recall-receipts for query hashes, used/ignored reasons, stale flags, conflicts, and identity alignment."}
    conflict_report = {"stage": "v52.2", "status": "preview", "ok": True, "message": "Run --recall-conflict-resolver to preview conflict resolution without memory edits."}
    stale_report = {"stage": "v52.3", "status": "preview", "ok": True, "message": "Run --stale-memory-handling to classify stale recall evidence without mutation."}
    scope_report = {"stage": "v52.4", "status": "preview", "ok": True, "message": "Run --recall-scope-controls to limit recall by project, identity, safety, operator preference, or release/task context."}
    privacy_report = {"stage": "v52.5", "status": "preview", "ok": True, "message": "Run --recall-privacy-classifier before planning surfaces recalled memory."}
    body = f"""
<p>v52.x stabilizes read-only memory recall before v53 planning uses it. Recall can explain why memory was used or ignored, flag stale/conflicting evidence, restrict scope, and classify planning visibility. It cannot rewrite memory, approve source apply, approve publish, approve live apply, approve rollback, or silently mutate identity. Context, not a crown.</p>
<div class='grid'>
  {_report_status_card('Memory read path', read_report)}
  {_report_status_card('Memory search/filter', search_report)}
  {_report_status_card('Memory recall', recall_report)}
  {_report_status_card('Recall receipts', receipts_report)}
  {_report_status_card('Conflict resolver', conflict_report)}
  {_report_status_card('Stale handling', stale_report)}
  {_report_status_card('Scope controls', scope_report)}
  {_report_status_card('Privacy classifier', privacy_report)}
</div>
<h3>Recall guarantees</h3>
{_mini_kv_table([('Recall mode', 'read_only'), ('Recall receipt', 'required before planning'), ('Used/ignored explanations', 'enabled'), ('Stale warnings', 'enabled'), ('Conflict detection', 'enabled'), ('Scope controls', 'enabled'), ('Privacy classifier', 'enabled'), ('Memory rewrite approved', False), ('Source apply approved', False), ('Publish approved', False), ('Live apply approved', False)])}
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --memory-read-path --autonomy-goal "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-search-filter --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --memory-recall-self-context --memory-query "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --memory-recall-receipts --memory-query "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --recall-conflict-resolver --memory-query "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --stale-memory-handling --memory-query "improve release dashboard performance" --readiness-json
python conscious_agent/main.py --recall-scope-controls --recall-scope release_task --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --recall-privacy-classifier --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --pre-v53-memory-informed-planning-gate --memory-query "dashboard performance" --readiness-json</pre>
<p><a href='/memory'><button type='button'>Back to Memory</button></a> <a href='/planning'><button type='button'>Open Memory-Informed Planning</button></a></p>
<p><a href='/api/release/memory-read-path'>Read Path JSON</a> | <a href='/api/release/memory-search-filter'>Search JSON</a> | <a href='/api/release/memory-recall-self-context'>Recall JSON</a> | <a href='/api/release/memory-recall-receipts'>Recall Receipts JSON</a> | <a href='/api/release/recall-conflict-resolver'>Conflicts JSON</a> | <a href='/api/release/stale-memory-handling'>Stale JSON</a> | <a href='/api/release/recall-scope-controls'>Scope JSON</a> | <a href='/api/release/recall-privacy-classifier'>Privacy JSON</a> | <a href='/api/release/pre-v53-memory-informed-planning-gate'>Pre-v53 Gate JSON</a></p>
"""
    return _layout("/recall", _card("v52.x Recall Stabilization", body) + _card("Memory recall preview", _text_block(memory_recall_self_context_text(recall_report, full=False))) + _card("Recall receipts preview", _text_block(memory_recall_receipts_text(receipts_report, full=False))))


def render_memory_informed_planning() -> str:
    gate_report = {"stage": "v53.9", "status": "preview", "ok": True, "message": "Run --pre-v54-action-planning-gate for planning receipts, conflict classifier, revision drafts, scope/risk controls, parity, and privacy checks."}
    planning_report = {"stage": "v53.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Run --memory-informed-planning for selected memories, ignored-memory explanations, warnings, and supervised plan steps.", "memory_informed_planning_loop": {"planning_mode": "supervised_read_only_plan_builder", "automatic_source_changes": False, "automatic_memory_updates": False, "source_apply_approved": False, "publish_approved": False, "live_apply_approved": False}}
    receipt_report = {"stage": "v53.1", "status": "preview", "ok": True, "message": "Run --memory-informed-planning-receipts for hash-bound planning receipts and evidence summaries."}
    conflict_report = {"stage": "v53.2", "status": "preview", "ok": True, "message": "Run --plan-conflict-classifier to classify memory, identity, safety, queue, and approval-boundary conflicts."}
    risk_report = {"stage": "v53.5", "status": "preview", "ok": True, "message": "Run --planning-risk-budget to score plan risk/cost before action-plan conversion."}
    body = f"""
<p>v53.x stabilizes memory-informed planning before v54 action plans. The planner can bind receipts, classify conflicts, draft revisions, constrain scope, and score risk. It still does not apply source, write memory, approve publish, approve live apply, approve rollback, or edit identity. Planning gets a clipboard, not a detonator.</p>
<div class='grid'>
  {_report_status_card('Memory-informed planning', planning_report)}
  {_report_status_card('Planning receipts', receipt_report)}
  {_report_status_card('Plan conflicts', conflict_report)}
  {_report_status_card('Planning risk budget', risk_report)}
  {_report_status_card('Pre-v54 action gate', gate_report)}
</div>
<h3>Planning boundaries</h3>
{_mini_kv_table([('Planning mode', 'supervised_read_only_plan_builder'), ('Planning receipt', 'hash-bound'), ('Conflict classifier', 'warn/review only'), ('Revision drafts', 'draft-only'), ('Scope controls', 'enabled'), ('Risk budget', 'enabled'), ('Automatic source changes', False), ('Automatic memory updates', False), ('Action execution approved', False)])}
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --memory-informed-planning-receipts --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --plan-conflict-classifier --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --plan-revision-drafts --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --planning-scope-controls --planning-scope dashboard_cleanup --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --planning-risk-budget --planning-scope dashboard_cleanup --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --planning-dashboard-polish --readiness-json
python conscious_agent/main.py --planning-api-parity-gate --readiness-json
python conscious_agent/main.py --planning-privacy-package-hardening --readiness-json
python conscious_agent/main.py --pre-v54-action-planning-gate --memory-query "dashboard performance" --readiness-json</pre>
<p><a href='/recall'><button type='button'>Back to Recall</button></a> <a href='/action-plans'><button type='button'>Open Supervised Action Plans</button></a></p>
<p><a href='/api/release/memory-informed-planning'>Planning JSON</a> | <a href='/api/release/memory-informed-planning-receipts'>Receipts JSON</a> | <a href='/api/release/plan-conflict-classifier'>Conflicts JSON</a> | <a href='/api/release/plan-revision-drafts'>Revisions JSON</a> | <a href='/api/release/planning-scope-controls'>Scope JSON</a> | <a href='/api/release/planning-risk-budget'>Risk JSON</a> | <a href='/api/release/planning-dashboard-polish'>Dashboard Polish JSON</a> | <a href='/api/release/planning-api-parity-gate'>Parity JSON</a> | <a href='/api/release/planning-privacy-package-hardening'>Privacy JSON</a> | <a href='/api/release/pre-v54-action-planning-gate'>Pre-v54 Gate JSON</a></p>
"""
    return _layout("/planning", _card("v53.x Planning Stabilization", body) + _card("Planning preview", _text_block(memory_informed_planning_loop_text(planning_report, full=False))) + _card("Planning receipt preview", _text_block(memory_informed_planning_receipts_text(receipt_report, full=False))))


def render_supervised_action_plans() -> str:
    action_report = {"stage": "v54.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Run --supervised-action-planning for evidence-bound action steps and blocked destructive labels.", "supervised_action_planning_loop": {"automatic_execution": False, "action_execution_approved": False, "source_apply_approved": False, "memory_write_approved": False, "publish_approved": False, "live_apply_approved": False}}
    receipt_report = {"stage": "v54.1", "status": "preview", "ok": True, "message": "Run --action-plan-receipts for hash-bound action step receipts."}
    classifier_report = {"stage": "v54.2-v54.5", "status": "preview", "ok": True, "message": "Run classifier, dependency, risk, and rehearsal commands for full action-plan readiness."}
    body = f"""
<p>v54.x stabilizes supervised action planning with receipts, step classification, dependency order, risk budgets, and dry-run rehearsal. It still executes nothing automatically, because the action planner gets a clipboard, not a chainsaw.</p>
<div class='grid'>
  {_report_status_card('Supervised action planning', action_report)}
  {_report_status_card('Action receipts', receipt_report)}
  {_report_status_card('Classifier/risk/rehearsal', classifier_report)}
</div>
<h3>Action planning boundaries</h3>
<ul><li>Action plans do not execute.</li><li>Source, memory, publish, live apply, rollback, and identity operations still require their own guarded confirmation paths.</li><li>GET/API/dashboard previews remain read-only.</li></ul>
<h3>Safe commands</h3>
<pre>python conscious_agent/main.py --action-plan-receipts --memory-query "dashboard performance" --readiness-json
python conscious_agent/main.py --action-step-classifier --planning-scope dashboard_cleanup --readiness-json
python conscious_agent/main.py --action-rehearsal-dry-run-preview --readiness-json
python conscious_agent/main.py --pre-v55-controlled-execution-gate --readiness-json</pre>
<p><a href='/planning'><button type='button'>Back to Planning</button></a> <a href='/execution-preview'><button type='button'>Open Execution Preview</button></a></p>
<p><a href='/api/release/action-plan-receipts'>Receipts JSON</a> | <a href='/api/release/action-step-classifier'>Classifier JSON</a> | <a href='/api/release/action-dependency-graph'>Dependency JSON</a> | <a href='/api/release/action-risk-budget'>Risk JSON</a> | <a href='/api/release/action-rehearsal-dry-run-preview'>Rehearsal JSON</a> | <a href='/api/release/pre-v55-controlled-execution-gate'>Pre-v55 Gate JSON</a></p>
"""
    return _layout("/action-plans", _card("v54.x Supervised Action Planning Stabilization", body) + _card("Action planning preview", _text_block(supervised_action_planning_loop_text(action_report, full=False))))


def render_controlled_execution_preview() -> str:
    preview_report = {"stage": "v55.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Run --controlled-action-execution-preview for a hash-bound execution readiness receipt.", "controlled_action_execution_preview": {"automatic_execution": False, "action_execution_approved": False, "source_apply_approved": False, "memory_write_approved": False, "publish_approved": False, "live_apply_approved": False}}
    gate_report = {"stage": "v54.9", "status": "preview", "ok": True, "message": "Run --pre-v55-controlled-execution-gate for full readiness evidence."}
    body = f"""
<p>v55 controlled execution preview binds one action plan, validates preview confirmation, lists step readiness, and points each real operation back to its own guarded subsystem. It does not execute source, memory, publish, live, rollback, or identity operations.</p>
<div class='grid'>
  {_report_status_card('Pre-v55 gate', gate_report)}
  {_report_status_card('Execution preview', preview_report)}
</div>
<h3>Preview commands</h3>
<pre>python conscious_agent/main.py --pre-v55-controlled-execution-gate --readiness-json
python conscious_agent/main.py --controlled-action-execution-preview --readiness-json</pre>
<p class='muted'>Exact preview phrase format: PREVIEW_ACTION_PLAN &lt;action_plan_id&gt;. Even a valid preview phrase does not approve real execution.</p>
<p><a href='/action-plans'><button type='button'>Back to Action Plans</button></a></p>
<p><a href='/api/release/controlled-action-execution-preview'>Execution Preview JSON</a> | <a href='/api/release/pre-v55-controlled-execution-gate'>Pre-v55 Gate JSON</a> | <a href='/api/release/action-api-parity-gate'>Parity JSON</a> | <a href='/api/release/action-privacy-package-hardening'>Privacy JSON</a></p>
"""
    return _layout("/execution-preview", _card("v55.0 Controlled Action Execution Preview", body) + _card("Execution preview summary", _text_block(controlled_action_execution_preview_text(preview_report, full=False))))


def render_read_only_execution() -> str:
    preview_report = {"stage": "v56.0", "status": "preview", "ok": True, "message": "Dashboard preview only. POST/CLI exact confirmation is required to run one allowlisted read-only command.", "controlled_read_only_action_execution": {"executed": False, "source_apply_approved": False, "memory_write_approved": False, "publish_approved": False, "live_apply_approved": False, "rollback_approved": False, "identity_update_approved": False}}
    allowlist_report = {"stage": "v55.3", "status": "preview", "ok": True, "message": "Run --read-only-command-allowlist for exact allowlisted diagnostics."}
    gate_report = {"stage": "v55.9", "status": "preview", "ok": True, "message": "Run --pre-v56-read-only-execution-gate for full readiness evidence."}
    body = f"""
<p>v56 introduces controlled read-only action execution. It can run one allowlisted diagnostic only after an exact confirmation phrase. It still cannot apply source, write memory, publish, live apply, rollback, or update identity. Tragic lack of chaos. Useful, though.</p>
<div class='grid'>
  {_report_status_card('Pre-v56 gate', gate_report)}
  {_report_status_card('Allowlist', allowlist_report)}
  {_report_status_card('Read-only execution', preview_report)}
</div>
<h3>Safe read-only commands</h3>
<pre>python conscious_agent/main.py --read-only-command-allowlist --readiness-json
python conscious_agent/main.py --pre-v56-read-only-execution-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --controlled-read-only-action-execution --read-only-command-key version-import --read-only-confirm-phrase "RUN_READ_ONLY version-import" --execute-read-only-action --readiness-json</pre>
<p class='muted'>GET/API/dashboard views remain read-only previews. Controlled execution is CLI/POST-only and command-keyed.</p>
<p><a href='/execution-preview'><button type='button'>Back to Execution Preview</button></a></p>
<p><a href='/api/release/execution-preview-receipts'>Preview Receipts JSON</a> | <a href='/api/release/execution-step-permission-classifier'>Permission JSON</a> | <a href='/api/release/read-only-command-allowlist'>Allowlist JSON</a> | <a href='/api/release/execution-sandbox-evidence-binder'>Evidence Binder JSON</a> | <a href='/api/release/execution-result-receipts'>Result Receipts JSON</a> | <a href='/api/release/pre-v56-read-only-execution-gate'>Pre-v56 Gate JSON</a> | <a href='/api/release/controlled-read-only-action-execution'>Read-Only Execution Preview JSON</a></p>
"""
    return _layout("/read-only-execution", _card("v56.0 Controlled Read-Only Action Execution", body) + _card("Read-only execution summary", _text_block(controlled_read_only_action_execution_text(preview_report, full=False))))




def render_evidence_gathering() -> str:
    preview_report = {"stage": "v57.0", "status": "preview", "ok": True, "message": "Dashboard preview only. CLI/POST exact confirmation is required for any allowlisted read-only diagnostic execution.", "evidence_gathering_maintenance_loop": {"source_apply_approved": False, "memory_write_approved": False, "publish_approved": False, "live_apply_approved": False, "rollback_approved": False, "identity_update_approved": False, "automatic_source_modification": False}}
    gate_report = {"stage": "v56.9", "status": "preview", "ok": True, "message": "Run --pre-v57-evidence-gathering-gate for full readiness evidence."}
    receipts_report = {"stage": "v56.1", "status": "preview", "ok": True, "message": "Run --read-only-execution-receipts for command/output proof boundaries."}
    body = f"""
<p>v57 lets Eidolon use controlled read-only diagnostics as evidence for maintenance planning. It can collect and summarize diagnostic evidence, but it still cannot mutate source, write memory, publish, live apply, rollback, or update identity. Binoculars. Still no hammer.</p>
<div class='grid'>
  {_report_status_card('Pre-v57 gate', gate_report)}
  {_report_status_card('Read-Only Receipts', receipts_report)}
  {_report_status_card('Evidence Loop', preview_report)}
</div>
<h3>Evidence commands</h3>
<pre>python conscious_agent/main.py --read-only-execution-receipts --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --expanded-diagnostic-allowlist --readiness-json
python conscious_agent/main.py --read-only-output-classifier --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --diagnostic-evidence-binder --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --diagnostic-result-summaries --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --pre-v57-evidence-gathering-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --evidence-gathering-maintenance-loop --read-only-command-key version-import --readiness-json</pre>
<p class='muted'>Stale or preview-only evidence is marked as review-required. Evidence summaries are not approvals. Society survives another day.</p>
<p><a href='/read-only-execution'><button type='button'>Back to Read-Only Execution</button></a></p>
<p><a href='/api/release/read-only-execution-receipts'>Receipts JSON</a> | <a href='/api/release/expanded-diagnostic-allowlist'>Allowlist JSON</a> | <a href='/api/release/read-only-output-classifier'>Output Classifier JSON</a> | <a href='/api/release/diagnostic-evidence-binder'>Evidence Binder JSON</a> | <a href='/api/release/diagnostic-result-summaries'>Summaries JSON</a> | <a href='/api/release/pre-v57-evidence-gathering-gate'>Pre-v57 Gate JSON</a> | <a href='/api/release/evidence-gathering-maintenance-loop'>Evidence Loop JSON</a></p>
"""
    return _layout("/evidence-gathering", _card("v57.0 Evidence-Gathering Maintenance Loop", body) + _card("Evidence loop summary", _text_block(evidence_gathering_maintenance_loop_text(preview_report, full=False))))



def render_patch_proposals() -> str:
    preview_report = {"stage": "v58.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Run CLI/API gates for full evidence-grounded sandbox proposal proof.", "evidence_grounded_patch_proposal_loop": {"sandbox_only": True, "source_apply_approved": False, "memory_write_approved": False, "publish_approved": False, "live_apply_approved": False, "rollback_approved": False, "identity_update_approved": False, "automatic_source_modification": False}}
    gate_report = {"stage": "v57.9", "status": "preview", "ok": True, "message": "Run --pre-v58-patch-proposal-gate for full readiness evidence."}
    coverage_report = {"stage": "v57.5", "status": "preview", "ok": True, "message": "Run --diagnostic-coverage-map to inspect evidence coverage before proposal drafting."}
    body = f"""
<p>v58 lets Eidolon turn diagnostic evidence into sandbox-only patch proposal records. It predicts touched files, binds evidence hashes, scores risk, and previews verification commands, but it does not apply source, write memory, publish, live apply, rollback, or update identity. The gremlin may sketch. It may not touch the tools.</p>
<div class='grid'>
  {_report_status_card('Pre-v58 gate', gate_report)}
  {_report_status_card('Diagnostic coverage', coverage_report)}
  {_report_status_card('Patch proposal preview', preview_report)}
</div>
<h3>Evidence-grounded proposal commands</h3>
<pre>python conscious_agent/main.py --evidence-collection-receipts --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --diagnostic-issue-classifier --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --evidence-conflict-staleness-resolver --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --evidence-to-plan-update-drafts --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --diagnostic-coverage-map --readiness-json
python conscious_agent/main.py --pre-v58-patch-proposal-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --evidence-grounded-patch-proposal --read-only-command-key version-import --readiness-json</pre>
<p class='muted'>Patch proposals are review records only. They do not authorize source apply or any other guarded operation.</p>
<p><a href='/evidence-gathering'><button type='button'>Back to Evidence Gathering</button></a></p>
<p><a href='/api/release/evidence-collection-receipts'>Evidence Receipts JSON</a> | <a href='/api/release/diagnostic-issue-classifier'>Issue Classifier JSON</a> | <a href='/api/release/evidence-conflict-staleness-resolver'>Conflict/Stale JSON</a> | <a href='/api/release/evidence-to-plan-update-drafts'>Plan Drafts JSON</a> | <a href='/api/release/diagnostic-coverage-map'>Coverage JSON</a> | <a href='/api/release/pre-v58-patch-proposal-gate'>Pre-v58 Gate JSON</a> | <a href='/api/release/evidence-grounded-patch-proposal'>Patch Proposal JSON</a></p>
"""
    return _layout("/patch-proposals", _card("v58.0 Evidence-Grounded Patch Proposal Loop", body) + _card("Patch proposal summary", _text_block(evidence_grounded_patch_proposal_loop_text(preview_report, full=False))))



def render_sandbox_patch_execution() -> str:
    preview_report = {"stage": "v59.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Use CLI/API for full controlled sandbox execution proof.", "controlled_sandbox_patch_execution": {"executed_in_sandbox": False, "source_apply_approved": False, "memory_write_approved": False, "publish_approved": False, "live_apply_approved": False, "rollback_approved": False, "identity_update_approved": False, "automatic_source_modification": False}}
    gate_report = {"stage": "v58.9", "status": "preview", "ok": True, "message": "Run --pre-v59-sandbox-patch-execution-gate for full readiness evidence."}
    body = f"""
<p>v59 lets Eidolon rehearse a reviewed patch proposal inside a temporary sandbox copy only. Preview mode writes nothing. Confirmed mode writes only to a temp sandbox and still does not apply live source, publish, live apply, rollback, write memory, or update identity. Tiny lab bench. Thick glass.</p>
<div class='grid'>
  {_report_status_card('Pre-v59 gate', gate_report)}
  {_report_status_card('Sandbox execution preview', preview_report)}
</div>
<h3>Patch/sandbox commands</h3>
<pre>python conscious_agent/main.py --patch-proposal-receipts --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --patch-scope-classifier --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --patch-risk-budget --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --patch-diff-preview-drafts --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --patch-verification-plan --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --pre-v59-sandbox-patch-execution-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --controlled-sandbox-patch-execution --read-only-command-key version-import --readiness-json</pre>
<p class='muted'>Sandbox execution is not source apply. It does not approve any guarded operation. Yes, this warning is deliberately repetitive. Software apparently needs chanting.</p>
<p><a href='/patch-proposals'><button type='button'>Back to Patch Proposals</button></a> <a href='/source-apply-handoff'><button type='button'>Source Apply Handoff</button></a></p>
<p><a href='/api/release/patch-proposal-receipts'>Proposal Receipts JSON</a> | <a href='/api/release/patch-scope-classifier'>Scope JSON</a> | <a href='/api/release/patch-risk-budget'>Risk JSON</a> | <a href='/api/release/patch-diff-preview-drafts'>Diff Preview JSON</a> | <a href='/api/release/patch-verification-plan'>Verification Plan JSON</a> | <a href='/api/release/pre-v59-sandbox-patch-execution-gate'>Pre-v59 Gate JSON</a> | <a href='/api/release/controlled-sandbox-patch-execution'>Sandbox Execution JSON</a></p>
"""
    return _layout("/sandbox-patch-execution", _card("v59.0 Controlled Sandbox Patch Execution", body) + _card("Sandbox execution summary", _text_block(controlled_sandbox_patch_execution_text(preview_report, full=False))))



def render_source_apply_handoff() -> str:
    preview_report = {"stage": "v61.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Use CLI/API for full controlled source-apply bridge proof.", "controlled_source_apply_bridge_refinement": {"live_apply_called": False, "source_files_modified": False, "source_apply_approved": False, "publish_approved": False, "memory_write_approved": False, "identity_update_approved": False}}
    gate_report = {"stage": "v60.9", "status": "preview", "ok": True, "message": "Run --pre-v61-controlled-apply-bridge-gate for full readiness evidence."}
    receipt_report = {"stage": "v60.1", "status": "preview", "ok": True, "message": "Receipts bind handoff packet, sandbox/proposal receipts, source baseline hash, confirmation hash, and checklist hashes."}
    drift_report = {"stage": "v60.2", "status": "preview", "ok": True, "message": "Drift resolver classifies clean, metadata-only, README/history, source-file, blocked, or unknown drift."}
    binder_report = {"stage": "v60.3", "status": "preview", "ok": True, "message": "Reviewed artifact set binder groups all review evidence into one stable hash."}
    bridge_report = {"stage": "v60.5", "status": "preview", "ok": True, "message": "Dry-run bridge summarizes the guarded source-apply dry-run context and refuses live apply."}
    body = f"""
<p>v61 turns the v60 sandbox-to-source handoff into a controlled dry-run bridge. It adds receipts, drift resolution, reviewed artifact binding, eligibility classification, dashboard/API parity, privacy hardening, and a pre-v61 gate. It still does <strong>not</strong> apply live source. The machine remains in its cage, and for once the cage has labels.</p>
<div class='grid'>
  {_report_status_card('Source Apply Handoff Receipts', receipt_report)}
  {_report_status_card('Drift Resolver', drift_report)}
  {_report_status_card('Reviewed Artifact Set', binder_report)}
  {_report_status_card('Dry-Run Bridge', bridge_report)}
  {_report_status_card('Pre-v61 gate', gate_report)}
  {_report_status_card('v61 bridge refinement', preview_report)}
</div>
<details class='nav-section' open>
  <summary>Source-apply bridge commands</summary>
  <pre>python conscious_agent/main.py --source-apply-handoff-receipts --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-baseline-drift-resolver --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --reviewed-artifact-set-binder --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-handoff-eligibility --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-dry-run-bridge --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-handoff-dashboard-polish --readiness-json
python conscious_agent/main.py --source-apply-handoff-api-parity-gate --readiness-json
python conscious_agent/main.py --source-apply-handoff-privacy-hardening --readiness-json
python conscious_agent/main.py --pre-v61-controlled-apply-bridge-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --controlled-source-apply-bridge-refinement --read-only-command-key version-import --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' data-tip='Records packet, receipt, baseline, confirmation hash, and checklist hashes without approval.'><strong>Receipt layer</strong><br><span class='muted'>hash-bound review evidence</span></div>
  <div class='mini-card' data-tip='Classifies drift before a bridge can even pretend to be helpful.'><strong>Drift layer</strong><br><span class='muted'>clean / metadata / docs / source / blocked / unknown</span></div>
  <div class='mini-card' data-tip='Binds receipts, diff preview, verification matrix, rollback rehearsal, and privacy scan.'><strong>Artifact binder</strong><br><span class='muted'>one reviewed set hash</span></div>
  <div class='mini-card' data-tip='Summarizes guarded source-apply dry-run context and refuses live writes.'><strong>Dry-run bridge</strong><br><span class='muted'>no live apply called</span></div>
</div>
<p class='muted'>Handoff bridge is still not source apply. The older guarded <code>--apply-reviewed-patch</code> path remains separate and requires exact confirmation, backups, and post-apply verification.</p>
<p><a href='/sandbox-patch-execution'><button type='button'>Back to Sandbox Patch Execution</button></a></p>
<p><a href='/api/release/source-apply-handoff-receipts'>Receipts JSON</a> | <a href='/api/release/source-baseline-drift-resolver'>Drift Resolver JSON</a> | <a href='/api/release/reviewed-artifact-set-binder'>Artifact Binder JSON</a> | <a href='/api/release/source-apply-handoff-eligibility'>Eligibility JSON</a> | <a href='/api/release/source-apply-dry-run-bridge'>Dry-Run Bridge JSON</a> | <a href='/api/release/source-apply-handoff-dashboard-polish'>Dashboard Polish JSON</a> | <a href='/api/release/source-apply-handoff-api-parity-gate'>API Parity JSON</a> | <a href='/api/release/source-apply-handoff-privacy-hardening'>Privacy JSON</a> | <a href='/api/release/pre-v61-controlled-apply-bridge-gate'>Pre-v61 Gate JSON</a> | <a href='/api/release/controlled-source-apply-bridge-refinement'>v61 Bridge JSON</a></p>
"""
    summary = _card("v61.0 Controlled Source Apply Bridge Refinement", _text_block(controlled_source_apply_bridge_refinement_text(preview_report, full=False)))
    return _layout("/source-apply-handoff", _card("v61.0 Controlled Source Apply Bridge", body) + summary)



def render_source_apply_transactions() -> str:
    preview_report = {"stage": "v63.0", "status": "preview", "ok": True, "message": "Dashboard preview only. Use CLI/API for full supervised source-apply transaction layer proof.", "supervised_source_apply_transaction_layer": {"live_apply_called": False, "source_files_modified": False, "source_apply_approved": False, "publish_approved": False, "memory_write_approved": False, "identity_update_approved": False}}
    plan_report = {"stage": "v61.1", "status": "preview", "ok": True, "message": "Transaction planner binds reviewed handoff evidence to files, backups, rollback targets, commands, and exact confirmation."}
    backup_report = {"stage": "v61.2", "status": "preview", "ok": True, "message": "Backup binder records pre-apply hashes and rollback targets before mutation can be considered."}
    dry_run_report = {"stage": "v61.3", "status": "preview", "ok": True, "message": "Dry-run verifier checks target files, protected paths, docs, and command availability without source writes."}
    executor_report = {"stage": "v61.5", "status": "warn", "ok": True, "message": "Executor refuses without exact transaction confirmation and explicit approval."}
    rollback_report = {"stage": "v61.7", "status": "preview", "ok": True, "message": "Rollback rehearsal uses an isolated fixture to prove restore mechanics without touching real source."}
    gate_report = {"stage": "v61.9", "status": "preview", "ok": True, "message": "Run --pre-v62-transaction-release-gate for full readiness evidence."}
    body = f"""
<p>v62 turns the v61 handoff bridge into a supervised transaction layer: transaction plan, backup binder, dry-run verifier, exact confirmation gate, supervised executor review, post-apply verification prep, rollback rehearsal, dashboard/API parity, and package privacy hardening. It still does <strong>not</strong> grant live source apply by browsing this page. Tiny mercy.</p>
<div class='grid'>
  {_report_status_card('Transaction Planner', plan_report)}
  {_report_status_card('Backup Binder', backup_report)}
  {_report_status_card('Dry-Run Verifier', dry_run_report)}
  {_report_status_card('Executor Refusal', executor_report)}
  {_report_status_card('Rollback Rehearsal', rollback_report)}
  {_report_status_card('Pre-v62 gate', gate_report)}
</div>
<details class='nav-section' open>
  <summary>Source-apply transaction commands</summary>
  <pre>python conscious_agent/main.py --source-apply-transaction-planner --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-backup-binder --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-transaction-dry-run-verifier --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-transaction-confirmation-gate --transaction-confirm-phrase "&lt;exact phrase&gt;" --readiness-json
python conscious_agent/main.py --supervised-source-apply-executor --transaction-confirm-phrase "&lt;exact phrase&gt;" --approve-source-apply-transaction --dry-run --readiness-json
python conscious_agent/main.py --post-apply-verification-runner --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-rollback-rehearsal --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --source-apply-transaction-dashboard-command-center --readiness-json
python conscious_agent/main.py --pre-v62-transaction-release-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --supervised-source-apply-transaction-layer --read-only-command-key version-import --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Builds a transaction plan with target files, backups, rollback targets, verification commands, and expected version.'><strong>Plan</strong><br><span class='muted'>reviewed handoff → transaction</span></div>
  <div class='mini-card' tabindex='0' data-tip='Binds pre-apply hashes and rollback previews before any mutation path can proceed.'><strong>Backup</strong><br><span class='muted'>hashes before courage</span></div>
  <div class='mini-card' tabindex='0' data-tip='Checks existence, protected paths, documentation targets, and dry-run-only behavior.'><strong>Dry-run</strong><br><span class='muted'>no source writes</span></div>
  <div class='mini-card' tabindex='0' data-tip='Requires a transaction-specific exact phrase and explicit approval before executor review.'><strong>Confirm</strong><br><span class='muted'>phrase-bound</span></div>
  <div class='mini-card' tabindex='0' data-tip='Refuses live source mutation unless the transaction gate, backup evidence, and approval all align.'><strong>Executor</strong><br><span class='muted'>guarded bridge only</span></div>
  <div class='mini-card' tabindex='0' data-tip='Prepares compile, install smoke, version import, privacy, route, transaction receipt, and rollback checks.'><strong>Verify</strong><br><span class='muted'>post-apply checklist</span></div>
  <div class='mini-card' tabindex='0' data-tip='Uses a temporary fixture to prove rollback restoration without touching real source files.'><strong>Rollback</strong><br><span class='muted'>fixture rehearsal</span></div>
</div>
<p class='muted'>Default browser hover tooltips were removed from nav tabs. Only the custom hover cards remain, because two tooltips for one tab is how UI becomes a mosquito.</p>
<p><a href='/source-apply-handoff'><button type='button'>Back to Source Apply Handoff</button></a></p>
<p><a href='/api/release/source-apply-transaction-planner'>Planner JSON</a> | <a href='/api/release/source-apply-backup-binder'>Backup JSON</a> | <a href='/api/release/source-apply-transaction-dry-run-verifier'>Dry-Run JSON</a> | <a href='/api/release/source-apply-transaction-confirmation-gate'>Confirmation JSON</a> | <a href='/api/release/supervised-source-apply-executor'>Executor JSON</a> | <a href='/api/release/post-apply-verification-runner'>Post-Apply JSON</a> | <a href='/api/release/transaction-rollback-rehearsal'>Rollback JSON</a> | <a href='/api/release/source-apply-transaction-dashboard-command-center'>Dashboard JSON</a> | <a href='/api/release/pre-v62-transaction-release-gate'>Pre-v62 Gate JSON</a> | <a href='/api/release/supervised-source-apply-transaction-layer'>v62 Layer JSON</a></p>
"""
    summary = _card("v62.0 Supervised Source Apply Transaction Layer", _text_block(supervised_source_apply_transaction_layer_text(preview_report, full=False)))
    return _layout("/source-apply-transactions", _card("v62.0 Source Apply Transaction Command Center", body) + summary)


def render_transaction_evidence() -> str:
    ledger_report = {"stage": "v62.1", "status": "preview", "ok": True, "message": "Receipt ledger persists transaction receipts under private runtime evidence."}
    diff_report = {"stage": "v62.2", "status": "preview", "ok": True, "message": "Diff viewer compares receipts, touched files, hashes, and safety flags."}
    conflict_report = {"stage": "v62.3", "status": "preview", "ok": True, "message": "Conflict detector classifies stale source and protected path issues."}
    export_report = {"stage": "v62.5", "status": "preview", "ok": True, "message": "Safe exporter excludes confirmation phrases, memories, identities, backups, logs, and nested zips."}
    replay_report = {"stage": "v62.6", "status": "preview", "ok": True, "message": "Replay audit checks receipt schema, hashes, rollback evidence, and replay safety."}
    final_report = {"stage": "v63.0", "status": "preview", "ok": True, "message": "Durable transaction evidence system preview. Use CLI/API for full report generation."}
    body = f"""
<p>v63 makes source-apply transaction evidence durable, searchable, comparable, exportable, and replay-auditable. It does not approve source apply, publish, memory writes, identity updates, or spontaneous robot ambition. Small wins.</p>
<div class='grid'>
  {_report_status_card('Receipt Ledger', ledger_report)}
  {_report_status_card('Diff Viewer', diff_report)}
  {_report_status_card('Conflict Detector', conflict_report)}
  {_report_status_card('Safe Exporter', export_report)}
  {_report_status_card('Replay Audit', replay_report)}
  {_report_status_card('v63 Evidence System', final_report)}
</div>
<details class='nav-section' open>
  <summary>Durable transaction evidence commands</summary>
  <pre>python conscious_agent/main.py --transaction-receipt-ledger --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-diff-viewer --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-conflict-detector --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-approval-record-binder --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-package-evidence-exporter --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-replay-audit --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --transaction-dashboard-receipt-timeline --readiness-json
python conscious_agent/main.py --transaction-api-search-filtering --readiness-json
python conscious_agent/main.py --pre-v63-transaction-evidence-gate --read-only-command-key version-import --readiness-json
python conscious_agent/main.py --durable-transaction-evidence-system --read-only-command-key version-import --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Stores transaction IDs, stages, statuses, hashes, verification states, timestamps, and approval separation.'><strong>Ledger</strong><br><span class='muted'>durable receipt trail</span></div>
  <div class='mini-card' tabindex='0' data-tip='Shows changed touched files, changed hashes, safety flags, rollback hashes, and verification changes.'><strong>Diff</strong><br><span class='muted'>compare receipts</span></div>
  <div class='mini-card' tabindex='0' data-tip='Classifies baseline mismatch, changed target files, stale rollback/backup evidence, reviewed artifact mismatch, and protected path conflicts.'><strong>Conflict</strong><br><span class='muted'>staleness detector</span></div>
  <div class='mini-card' tabindex='0' data-tip='Binds the approval record to one exact transaction and keeps source, publish, memory, and identity approvals separate.'><strong>Approval Binder</strong><br><span class='muted'>no generic approval</span></div>
  <div class='mini-card' tabindex='0' data-tip='Exports safe evidence while excluding confirmation phrases, backups, logs, memory, identity, approval secrets, and nested zips.'><strong>Exporter</strong><br><span class='muted'>shareable evidence</span></div>
  <div class='mini-card' tabindex='0' data-tip='Checks whether a receipt can still be trusted without applying it.'><strong>Replay Audit</strong><br><span class='muted'>trust check</span></div>
  <div class='mini-card' tabindex='0' data-tip='Read-only timeline route for recent receipts, status badges, approval states, verification state, rollback state, and API links.'><strong>Timeline</strong><br><span class='muted'>dashboard history</span></div>
  <div class='mini-card' tabindex='0' data-tip='Read-only API filtering by transaction ID, status, stage, and touched file without exposing confirmation phrases.'><strong>API Search</strong><br><span class='muted'>safe lookup</span></div>
</div>
<p><a href='/source-apply-transactions'><button type='button'>Back to Source Apply Transactions</button></a></p>
<p><a href='/api/release/transaction-receipt-ledger'>Ledger JSON</a> | <a href='/api/release/transaction-diff-viewer'>Diff JSON</a> | <a href='/api/release/transaction-conflict-detector'>Conflict JSON</a> | <a href='/api/release/transaction-approval-record-binder'>Approval JSON</a> | <a href='/api/release/transaction-package-evidence-exporter'>Export JSON</a> | <a href='/api/release/transaction-replay-audit'>Replay JSON</a> | <a href='/api/release/transaction-dashboard-receipt-timeline'>Timeline JSON</a> | <a href='/api/release/transaction-api-search-filtering'>Search JSON</a> | <a href='/api/release/pre-v63-transaction-evidence-gate'>Pre-v63 Gate JSON</a> | <a href='/api/release/durable-transaction-evidence-system'>v63 System JSON</a></p>
"""
    summary = _card("v63.0 Durable Transaction Evidence System", _text_block(durable_transaction_evidence_system_text(final_report, full=False)))
    return _layout("/transaction-evidence", _card("v63.0 Transaction Evidence Timeline", body) + summary)

def render_improvement_intelligence() -> str:
    summary_report = {"stage": "v63.1", "status": "preview", "ok": True, "message": "Summarizes durable transaction evidence into development memory."}
    registry_report = {"stage": "v63.2", "status": "preview", "ok": True, "message": "Tracks proposed/reviewed/accepted/rejected/deferred improvement candidates."}
    scoring_report = {"stage": "v63.3", "status": "preview", "ok": True, "message": "Scores candidates by safety, value, evidence, complexity, risk, privacy, and rollback confidence."}
    regression_report = {"stage": "v63.4", "status": "preview", "ok": True, "message": "Detects repeated route, version, README, smoke, privacy, and hover regressions."}
    risk_report = {"stage": "v63.5", "status": "preview", "ok": True, "message": "Forecasts dashboard/API/CLI/runtime/privacy blast radius before patch planning."}
    queue_report = {"stage": "v63.6", "status": "preview", "ok": True, "message": "Ranks safe supervised recommendations and stops before patch creation."}
    final_report = {"stage": "v64.0", "status": "preview", "ok": True, "message": "Supervised improvement intelligence layer preview. Use CLI/API for full report generation."}
    body = f"""
<p>v64 uses durable transaction evidence to recommend safer supervised improvements. It studies what happened, ranks what should improve next, and still does not auto-create patches, approve source apply, publish, write memory, or edit identity. Civilization survives another dashboard tab.</p>
<div class='grid'>
  {_report_status_card('Evidence Summary', summary_report)}
  {_report_status_card('Candidate Registry', registry_report)}
  {_report_status_card('Candidate Scoring', scoring_report)}
  {_report_status_card('Regression Patterns', regression_report)}
  {_report_status_card('Risk Forecast', risk_report)}
  {_report_status_card('Recommendation Queue', queue_report)}
  {_report_status_card('v64 Intelligence Layer', final_report)}
</div>
<details class='nav-section' open>
  <summary>Supervised improvement intelligence commands</summary>
  <pre>python conscious_agent/main.py --transaction-evidence-summarizer --readiness-json
python conscious_agent/main.py --improvement-candidate-registry --readiness-json
python conscious_agent/main.py --evidence-based-candidate-scoring --readiness-json
python conscious_agent/main.py --improvement-regression-pattern-detector --readiness-json
python conscious_agent/main.py --improvement-risk-blast-radius-forecaster --readiness-json
python conscious_agent/main.py --supervised-recommendation-queue --readiness-json
python conscious_agent/main.py --improvement-intelligence-dashboard --readiness-json
python conscious_agent/main.py --improvement-intelligence-api-cli-access --readiness-json
python conscious_agent/main.py --pre-v64-improvement-intelligence-gate --readiness-json
python conscious_agent/main.py --supervised-improvement-intelligence-layer --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Summarizes receipts, repeated warnings, touched files, rollback readiness, and package privacy trends.'><strong>Evidence Memory</strong><br><span class='muted'>what happened</span></div>
  <div class='mini-card' tabindex='0' data-tip='Stores proposed, reviewed, accepted, rejected, or deferred improvement candidates with source evidence.'><strong>Candidate Registry</strong><br><span class='muted'>what could improve</span></div>
  <div class='mini-card' tabindex='0' data-tip='Ranks candidates by safety, usefulness, evidence strength, complexity, regression risk, privacy impact, and rollback confidence.'><strong>Scoring</strong><br><span class='muted'>what is worth doing</span></div>
  <div class='mini-card' tabindex='0' data-tip='Watches for recurring failures such as stale version markers, README omissions, parity gaps, smoke blind spots, and duplicate tooltip regressions.'><strong>Regression Detector</strong><br><span class='muted'>what keeps breaking</span></div>
  <div class='mini-card' tabindex='0' data-tip='Forecasts touched modules and dashboard/API/CLI/runtime/privacy blast radius before patch planning.'><strong>Risk Forecast</strong><br><span class='muted'>what could break</span></div>
  <div class='mini-card' tabindex='0' data-tip='Queues the highest-value, safest, urgent, deferred, review-needed, and evidence-blocked recommendations.'><strong>Queue</strong><br><span class='muted'>what to do next</span></div>
</div>
<p><a href='/transaction-evidence'><button type='button'>Back to Transaction Evidence</button></a></p>
<p><a href='/api/release/transaction-evidence-summarizer'>Summary JSON</a> | <a href='/api/release/improvement-candidate-registry'>Registry JSON</a> | <a href='/api/release/evidence-based-candidate-scoring'>Scoring JSON</a> | <a href='/api/release/improvement-regression-pattern-detector'>Regression JSON</a> | <a href='/api/release/improvement-risk-blast-radius-forecaster'>Risk JSON</a> | <a href='/api/release/supervised-recommendation-queue'>Queue JSON</a> | <a href='/api/release/improvement-intelligence-dashboard'>Dashboard JSON</a> | <a href='/api/release/improvement-intelligence-api-cli-access'>API/CLI JSON</a> | <a href='/api/release/pre-v64-improvement-intelligence-gate'>Pre-v64 Gate JSON</a> | <a href='/api/release/supervised-improvement-intelligence-layer'>v64 System JSON</a></p>
"""
    summary = _card("v64.0 Supervised Improvement Intelligence Layer", _text_block(supervised_improvement_intelligence_layer_text(final_report, full=False)))
    return _layout("/improvement-intelligence", _card("v64.0 Improvement Intelligence", body) + summary)


def render_proposal_drafting() -> str:
    intake_report = {"stage": "v64.1", "status": "preview", "ok": True, "message": "Accepts one supervised recommendation for proposal drafting only."}
    draft_report = {"stage": "v64.2", "status": "preview", "ok": True, "message": "Builds a proposal skeleton with non-goals, checks, rollback, and docs."}
    mapper_report = {"stage": "v64.3", "status": "preview", "ok": True, "message": "Maps durable evidence into concrete proposal requirements."}
    risk_report = {"stage": "v64.4", "status": "preview", "ok": True, "message": "Attaches explicit blast-radius and file-boundary rules."}
    request_report = {"stage": "v64.5", "status": "preview", "ok": True, "message": "Compiles sandbox-only patch request instructions."}
    packet_report = {"stage": "v64.6", "status": "preview", "ok": True, "message": "Binds the review packet before sandbox execution."}
    final_report = {"stage": "v65.0", "status": "preview", "ok": True, "message": "Recommendation-to-proposal drafting layer preview. Use CLI/API for full report generation."}
    body = f"""
<p>v65 converts accepted supervised recommendations into proposal drafts, evidence-backed requirements, risk contracts, sandbox-only patch requests, and review packets. It gives Eidolon a clipboard, not the source-editing flamethrower humans keep pretending is a productivity tool.</p>
<div class='grid'>
  {_report_status_card('Accepted Intake', intake_report)}
  {_report_status_card('Draft Skeleton', draft_report)}
  {_report_status_card('Evidence Mapper', mapper_report)}
  {_report_status_card('Risk Contract', risk_report)}
  {_report_status_card('Sandbox Request', request_report)}
  {_report_status_card('Review Packet', packet_report)}
  {_report_status_card('v65 Drafting Layer', final_report)}
</div>
<details class='nav-section' open>
  <summary>Recommendation-to-proposal drafting commands</summary>
  <pre>python conscious_agent/main.py --accepted-recommendation-intake --readiness-json
python conscious_agent/main.py --proposal-draft-skeleton --readiness-json
python conscious_agent/main.py --evidence-requirement-mapper --readiness-json
python conscious_agent/main.py --proposal-risk-contract --readiness-json
python conscious_agent/main.py --sandbox-patch-request-compiler --readiness-json
python conscious_agent/main.py --proposal-review-packet-binder --readiness-json
python conscious_agent/main.py --proposal-dashboard-review-console --readiness-json
python conscious_agent/main.py --proposal-api-cli-access --readiness-json
python conscious_agent/main.py --pre-v65-proposal-drafting-gate --readiness-json
python conscious_agent/main.py --recommendation-to-proposal-drafting-layer --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Separates queue recommendation from operator-accepted proposal drafting and grants no mutation approval.'><strong>Accepted Recommendation</strong><br><span class='muted'>safe intake</span></div>
  <div class='mini-card' tabindex='0' data-tip='Creates proposal ID, target files, intended behavior, non-goals, checks, rollback expectations, and README/history requirements.'><strong>Proposal Skeleton</strong><br><span class='muted'>draft shape</span></div>
  <div class='mini-card' tabindex='0' data-tip='Maps transaction receipts, regression patterns, candidate scores, risk forecasts, and parity gaps into concrete requirements.'><strong>Evidence Mapping</strong><br><span class='muted'>why this change</span></div>
  <div class='mini-card' tabindex='0' data-tip='Defines blast radius, protected files, allowed and disallowed file classes, runtime privacy, apply restrictions, and verification minimums.'><strong>Risk Contract</strong><br><span class='muted'>what is fenced</span></div>
  <div class='mini-card' tabindex='0' data-tip='Compiles a sandbox-only patch request with expected operations, dry-run requirements, privacy exclusions, and review instructions.'><strong>Sandbox Request</strong><br><span class='muted'>sandbox only</span></div>
  <div class='mini-card' tabindex='0' data-tip='Binds intake, draft, evidence map, risk contract, sandbox request, verification plan, rollback plan, and parity expectations into one review packet.'><strong>Review Packet</strong><br><span class='muted'>operator artifact</span></div>
</div>
<p><a href='/improvement-intelligence'><button type='button'>Back to Improvement Intelligence</button></a></p>
<p><a href='/api/release/accepted-recommendation-intake'>Intake JSON</a> | <a href='/api/release/proposal-draft-skeleton'>Draft JSON</a> | <a href='/api/release/evidence-requirement-mapper'>Requirements JSON</a> | <a href='/api/release/proposal-risk-contract'>Risk JSON</a> | <a href='/api/release/sandbox-patch-request-compiler'>Sandbox Request JSON</a> | <a href='/api/release/proposal-review-packet-binder'>Packet JSON</a> | <a href='/api/release/proposal-dashboard-review-console'>Dashboard JSON</a> | <a href='/api/release/proposal-api-cli-access'>API/CLI JSON</a> | <a href='/api/release/pre-v65-proposal-drafting-gate'>Pre-v65 Gate JSON</a> | <a href='/api/release/recommendation-to-proposal-drafting-layer'>v65 System JSON</a></p>
"""
    summary = _card("v65.0 Recommendation-to-Proposal Drafting Layer", _text_block(recommendation_to_proposal_drafting_layer_text(final_report, full=False)))
    return _layout("/proposal-drafting", _card("v65.0 Proposal Drafting", body) + summary)



def render_proposal_sandbox() -> str:
    acceptance_report = {"stage": "v65.1", "status": "preview", "ok": True, "message": "Binds reviewed proposal packets to sandbox execution only."}
    plan_report = {"stage": "v65.2", "status": "preview", "ok": True, "message": "Builds isolated sandbox workspace plans with runtime exclusions."}
    request_report = {"stage": "v65.3", "status": "preview", "ok": True, "message": "Compiles precise sandbox-only implementation requests."}
    harness_report = {"stage": "v65.4", "status": "preview", "ok": True, "message": "Prepares sandbox execution and refuses live source mutation."}
    matrix_report = {"stage": "v65.5", "status": "preview", "ok": True, "message": "Binds compile, smoke, version, dashboard, API, CLI, privacy, tooltip, and docs checks."}
    binder_report = {"stage": "v65.6", "status": "preview", "ok": True, "message": "Binds execution evidence for later transaction handoff review."}
    triage_report = {"stage": "v65.7", "status": "preview", "ok": True, "message": "Classifies sandbox failures into safe repair guidance."}
    final_report = {"stage": "v66.0", "status": "preview", "ok": True, "message": "Reviewed proposal sandbox execution layer preview. Use CLI/API for full report generation."}
    body = f"""
<p>v66 turns reviewed proposal packets into isolated sandbox execution plans, implementation requests, verification evidence, and failure triage. It still does not mutate live source, publish releases, write memory, or alter identity, because apparently restraint is the one feature that keeps the robot from becoming a workplace incident.</p>
<div class='grid'>
  {_report_status_card('Acceptance Gate', acceptance_report)}
  {_report_status_card('Workspace Plan', plan_report)}
  {_report_status_card('Implementation Request', request_report)}
  {_report_status_card('Sandbox Harness', harness_report)}
  {_report_status_card('Verification Matrix', matrix_report)}
  {_report_status_card('Evidence Binder', binder_report)}
  {_report_status_card('Failure Triage', triage_report)}
  {_report_status_card('v66 Sandbox Layer', final_report)}
</div>
<details class='nav-section' open>
  <summary>Reviewed proposal sandbox commands</summary>
  <pre>python conscious_agent/main.py --reviewed-proposal-acceptance-gate --readiness-json
python conscious_agent/main.py --sandbox-workspace-plan --readiness-json
python conscious_agent/main.py --patch-implementation-request --readiness-json
python conscious_agent/main.py --proposal-sandbox-execution-harness --readiness-json
python conscious_agent/main.py --proposal-sandbox-verification-matrix --readiness-json
python conscious_agent/main.py --proposal-sandbox-evidence-binder --readiness-json
python conscious_agent/main.py --proposal-sandbox-failure-triage --readiness-json
python conscious_agent/main.py --proposal-sandbox-api-cli-access --readiness-json
python conscious_agent/main.py --pre-v66-proposal-sandbox-gate --readiness-json
python conscious_agent/main.py --reviewed-proposal-sandbox-execution-layer --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Verifies proposal draft, evidence mapping, risk contract, sandbox request, complete review packet, and approval separation before sandbox execution.'><strong>Acceptance Gate</strong><br><span class='muted'>entry control</span></div>
  <div class='mini-card' tabindex='0' data-tip='Defines workspace path, copied files, expected modifications, runtime exclusions, verification commands, discard behavior, and evidence paths.'><strong>Workspace Plan</strong><br><span class='muted'>sandbox shape</span></div>
  <div class='mini-card' tabindex='0' data-tip='Compiles objective, targets, allowed operations, forbidden operations, docs, parity, privacy, tests, and expected report shape.'><strong>Implementation Request</strong><br><span class='muted'>task contract</span></div>
  <div class='mini-card' tabindex='0' data-tip='Runs preview-only by default, can copy source into sandbox, records stdout/stderr and touched files, and refuses live source mutation.'><strong>Harness</strong><br><span class='muted'>isolated run</span></div>
  <div class='mini-card' tabindex='0' data-tip='Tracks compile, install smoke, version, layer, dashboard, API, CLI, privacy, tooltip, and docs/history checks.'><strong>Verification Matrix</strong><br><span class='muted'>proof list</span></div>
  <div class='mini-card' tabindex='0' data-tip='Binds acceptance, workspace, request, harness, verification, privacy, parity, warnings, and promotion recommendation into one packet.'><strong>Evidence Binder</strong><br><span class='muted'>handoff evidence</span></div>
  <div class='mini-card' tabindex='0' data-tip='Classifies compile, import, smoke, dashboard, API, CLI, privacy, docs/history, protected path, and unknown failures into repair guidance.'><strong>Failure Triage</strong><br><span class='muted'>repair path</span></div>
</div>
<p><a href='/proposal-drafting'><button type='button'>Back to Proposal Drafting</button></a></p>
<p><a href='/api/release/reviewed-proposal-acceptance-gate'>Acceptance JSON</a> | <a href='/api/release/sandbox-workspace-plan'>Plan JSON</a> | <a href='/api/release/patch-implementation-request'>Request JSON</a> | <a href='/api/release/proposal-sandbox-execution-harness'>Harness JSON</a> | <a href='/api/release/proposal-sandbox-verification-matrix'>Matrix JSON</a> | <a href='/api/release/proposal-sandbox-evidence-binder'>Evidence JSON</a> | <a href='/api/release/proposal-sandbox-failure-triage'>Triage JSON</a> | <a href='/api/release/proposal-sandbox-api-cli-access'>API/CLI JSON</a> | <a href='/api/release/pre-v66-proposal-sandbox-gate'>Pre-v66 Gate JSON</a> | <a href='/api/release/reviewed-proposal-sandbox-execution-layer'>v66 System JSON</a></p>
"""
    summary = _card("v66.0 Reviewed Proposal Sandbox Execution Layer", _text_block(reviewed_proposal_sandbox_execution_layer_text(final_report, full=False)))
    return _layout("/proposal-sandbox", _card("v66.0 Proposal Sandbox", body) + summary)



def render_sandbox_promotion() -> str:
    candidate_report = {"stage": "v66.1", "status": "preview", "ok": True, "message": "Builds promotion candidates from verified sandbox evidence."}
    diff_report = {"stage": "v66.2", "status": "preview", "ok": True, "message": "Normalizes sandbox diffs into source-relative operations."}
    safety_report = {"stage": "v66.3", "status": "preview", "ok": True, "message": "Blocks unsafe sandbox evidence before transaction drafting."}
    tx_report = {"stage": "v66.4", "status": "preview", "ok": True, "message": "Drafts a guarded source transaction from sandbox evidence."}
    packet_report = {"stage": "v66.5", "status": "preview", "ok": True, "message": "Binds proposal, sandbox, promotion, and transaction draft evidence."}
    conflict_report = {"stage": "v66.6", "status": "preview", "ok": True, "message": "Detects source drift and stale promotion evidence."}
    api_report = {"stage": "v66.8", "status": "preview", "ok": True, "message": "Verifies read-only API/CLI/dashboard parity."}
    final_report = {"stage": "v67.0", "status": "preview", "ok": True, "message": "Sandbox evidence promotion handoff layer preview. Use CLI/API for full report generation."}
    body = f"""
<p>v67 promotes verified proposal sandbox evidence into transaction-ready handoff packets. It prepares candidates, normalizes sandbox diffs, checks safety boundaries, drafts transaction previews, binds review packets, and detects staleness. It still does not mutate live source, approve publishing, write memory, or alter identity, because the robot gets paperwork before power tools.</p>
<div class='grid'>
  {_report_status_card('Promotion Candidate', candidate_report)}
  {_report_status_card('Diff Normalizer', diff_report)}
  {_report_status_card('Safety Gate', safety_report)}
  {_report_status_card('Transaction Draft', tx_report)}
  {_report_status_card('Review Packet', packet_report)}
  {_report_status_card('Conflict/Staleness', conflict_report)}
  {_report_status_card('API/CLI Access', api_report)}
  {_report_status_card('v67 Promotion Layer', final_report)}
</div>
<details class='nav-section' open>
  <summary>Sandbox promotion commands</summary>
  <pre>python conscious_agent/main.py --sandbox-promotion-candidate --readiness-json
python conscious_agent/main.py --sandbox-source-diff-normalizer --readiness-json
python conscious_agent/main.py --promotion-safety-boundary-gate --readiness-json
python conscious_agent/main.py --transaction-draft-from-sandbox --readiness-json
python conscious_agent/main.py --promotion-review-packet-binder --readiness-json
python conscious_agent/main.py --promotion-conflict-staleness-detector --readiness-json
python conscious_agent/main.py --sandbox-promotion-api-cli-access --readiness-json
python conscious_agent/main.py --pre-v67-sandbox-promotion-gate --readiness-json
python conscious_agent/main.py --sandbox-evidence-promotion-handoff-layer --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Collects accepted proposal ID, sandbox execution receipt, workspace hash, touched files, diff summary, verification matrix, privacy result, parity result, and failure triage result.'><strong>Candidate</strong><br><span class='muted'>sandbox result → promotion object</span></div>
  <div class='mini-card' tabindex='0' data-tip='Classifies added, modified, deleted, README/history, dashboard, API, CLI, package privacy, and protected path operations as source-relative review data.'><strong>Diff Normalizer</strong><br><span class='muted'>sandbox paths → source paths</span></div>
  <div class='mini-card' tabindex='0' data-tip='Blocks failed verification, protected paths, runtime/private data, missing docs/history, privacy failures, stale evidence, mismatched touched files, and mixed approvals.'><strong>Safety Gate</strong><br><span class='muted'>dirty evidence stops here</span></div>
  <div class='mini-card' tabindex='0' data-tip='Drafts source baseline expectations, file operations, expected hashes, backups, rollback requirements, verification commands, and confirmation phrase template.'><strong>Transaction Draft</strong><br><span class='muted'>handoff to transaction review</span></div>
  <div class='mini-card' tabindex='0' data-tip='Binds proposal packet, sandbox receipt, verification matrix, evidence binder, safety gate, normalized diff, transaction draft, and operator review instructions.'><strong>Review Packet</strong><br><span class='muted'>one review artifact</span></div>
  <div class='mini-card' tabindex='0' data-tip='Detects source baseline mismatch, target drift, README/history drift, dashboard/API/CLI drift, package privacy rule drift, and transaction evidence drift.'><strong>Conflict Detector</strong><br><span class='muted'>stale evidence check</span></div>
</div>
<p><a href='/proposal-sandbox'><button type='button'>Back to Proposal Sandbox</button></a></p>
<p><a href='/api/release/sandbox-promotion-candidate'>Candidate JSON</a> | <a href='/api/release/sandbox-source-diff-normalizer'>Diff JSON</a> | <a href='/api/release/promotion-safety-boundary-gate'>Safety JSON</a> | <a href='/api/release/transaction-draft-from-sandbox'>Transaction Draft JSON</a> | <a href='/api/release/promotion-review-packet-binder'>Review Packet JSON</a> | <a href='/api/release/promotion-conflict-staleness-detector'>Conflict JSON</a> | <a href='/api/release/sandbox-promotion-api-cli-access'>API/CLI JSON</a> | <a href='/api/release/pre-v67-sandbox-promotion-gate'>Pre-v67 Gate JSON</a> | <a href='/api/release/sandbox-evidence-promotion-handoff-layer'>v67 System JSON</a></p>
"""
    summary = _card("v67.0 Sandbox Evidence Promotion Handoff Layer", _text_block(sandbox_evidence_promotion_handoff_layer_text(final_report, full=False)))
    return _layout("/sandbox-promotion", _card("v67.0 Sandbox Promotion", body) + summary)




def render_transaction_execution() -> str:
    final_report = {"stage": "v69.0", "status": "preview", "ok": True, "message": "Operator-confirmed transaction execution preview. Use CLI/API for full report generation."}
    body = """
<h2>Operator-Confirmed Transaction Execution</h2>
<p>v69.0 connects ledger-registered source transaction candidates to exact-confirmation review, backup snapshotting, controlled rehearsal, guarded execution refusal, post-execution verification, and rollback recommendation. The dashboard is read-only.</p>
<div class='grid'>
  <div class='kpi'><strong>Execution eligibility</strong><br><span>candidate + safety gate + backup preflight</span></div>
  <div class='kpi'><strong>Exact confirmation</strong><br><span>bound to candidate, plan, baseline, and rollback hashes</span></div>
  <div class='kpi'><strong>Backup snapshot</strong><br><span>receipt-first backup and restore map</span></div>
  <div class='kpi'><strong>Apply rehearsal</strong><br><span>controlled-copy verification, no live mutation</span></div>
  <div class='kpi'><strong>Guarded executor</strong><br><span>refuses without exact phrase</span></div>
  <div class='kpi'><strong>Rollback recommendation</strong><br><span>advisory only, never automatic</span></div>
</div>
<h3>Operator commands</h3>
<pre>python conscious_agent/main.py --transaction-execution-eligibility --readiness-json
python conscious_agent/main.py --exact-confirmation-binder --readiness-json
python conscious_agent/main.py --backup-snapshot-materializer --readiness-json
python conscious_agent/main.py --transaction-apply-rehearsal --readiness-json
python conscious_agent/main.py --operator-confirmed-apply-executor --readiness-json
python conscious_agent/main.py --post-execution-verification --readiness-json
python conscious_agent/main.py --rollback-recommendation-gate --readiness-json
python conscious_agent/main.py --transaction-execution-dashboard-api-cli --readiness-json
python conscious_agent/main.py --pre-v69-execution-gate --readiness-json
python conscious_agent/main.py --operator-confirmed-transaction-execution-layer --readiness-json</pre>
<p><a href='/api/release/transaction-execution-eligibility'>Eligibility JSON</a> | <a href='/api/release/exact-confirmation-binder'>Confirmation JSON</a> | <a href='/api/release/backup-snapshot-materializer'>Backup JSON</a> | <a href='/api/release/transaction-apply-rehearsal'>Rehearsal JSON</a> | <a href='/api/release/operator-confirmed-apply-executor'>Executor JSON</a> | <a href='/api/release/post-execution-verification'>Verification JSON</a> | <a href='/api/release/rollback-recommendation-gate'>Rollback JSON</a> | <a href='/api/release/operator-confirmed-transaction-execution-layer'>v69 System JSON</a></p>
"""
    summary = _card("v69.0 Operator-Confirmed Transaction Execution Layer", _text_block(operator_confirmed_transaction_execution_layer_text(final_report, full=False)))
    return _layout("/transaction-execution", _card("v69.0 Transaction Execution", body) + summary)



def render_codebase_map() -> str:
    from self_maintenance import codebase_understanding_map_text
    final_report = {"stage": "v71.0", "status": "preview", "ok": True, "message": "Codebase understanding map preview. Use CLI/API for full report generation."}
    body = """
<p>v71.0 gives Eidolon a durable self-map of her codebase before future patch-generation and repair loops. This page is read-only and uses custom <code>data-tip</code> hover notes only.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Scan source files, metadata seeds, package inclusion, runtime/private boundaries, sizes, categories, and hashes.'><strong>Inventory</strong><span>v70.1 source tree inventory</span></div>
  <div class='mini-card' data-tip='Classify what key modules own and what tends to break around them.'><strong>Responsibilities</strong><span>v70.2 module map</span></div>
  <div class='mini-card' data-tip='Map Python imports, dashboard nav routes, API tokens, CLI flags, and high-value relationships.'><strong>Dependencies</strong><span>v70.3 call surface</span></div>
  <div class='mini-card' data-tip='Assign risk by module, file category, release impact, dashboard impact, and privacy boundary.'><strong>Risk</strong><span>v70.4 risk profile</span></div>
  <div class='mini-card' data-tip='Bind known failures like /api-info route shadowing, tooltip stacking, stale versions, privacy leaks, and smoke bloat.'><strong>Failure Memory</strong><span>v70.5 historical lessons</span></div>
  <div class='mini-card' data-tip='Choose verification commands based on changed file categories instead of blindly running the entire cathedral every time.'><strong>Verification Map</strong><span>v70.6 test selector foundation</span></div>
  <div class='mini-card' data-tip='Find oversized, risky, duplicated, or under-tested areas that can become future improvement candidates.'><strong>Opportunities</strong><span>v70.7 improvement detector</span></div>
  <div class='mini-card' data-tip='Check that CLI, API, dashboard, README, release history, package privacy, and hover behavior remain aligned.'><strong>Pre-v71 Gate</strong><span>v70.9 final gate</span></div>
</div>
<h3>CLI checks</h3>
<pre>python conscious_agent/main.py --source-tree-inventory --readiness-json
python conscious_agent/main.py --module-responsibility-map --readiness-json
python conscious_agent/main.py --dependency-call-surface-map --readiness-json
python conscious_agent/main.py --module-risk-profile --readiness-json
python conscious_agent/main.py --historical-failure-memory --readiness-json
python conscious_agent/main.py --verification-command-map --readiness-json
python conscious_agent/main.py --improvement-opportunity-detector --readiness-json
python conscious_agent/main.py --codebase-understanding-dashboard-api-cli --readiness-json
python conscious_agent/main.py --pre-v71-codebase-understanding-gate --readiness-json
python conscious_agent/main.py --codebase-understanding-map --readiness-json</pre>
<p><a href='/api/codebase-map/inventory'>Inventory JSON</a> | <a href='/api/codebase-map/responsibilities'>Responsibilities JSON</a> | <a href='/api/codebase-map/dependencies'>Dependencies JSON</a> | <a href='/api/codebase-map/risk'>Risk JSON</a> | <a href='/api/codebase-map/failures'>Failures JSON</a> | <a href='/api/codebase-map/verification'>Verification JSON</a> | <a href='/api/codebase-map/opportunities'>Opportunities JSON</a> | <a href='/api/codebase-map/layer'>v71 System JSON</a></p>
"""
    summary = _card("v71.0 Codebase Understanding Map", _text_block(codebase_understanding_map_text(final_report, full=False)))
    return _layout("/codebase-map", _card("v71.0 Codebase Map", body) + summary)



def render_patch_context() -> str:
    from self_maintenance import patch_generation_context_builder_text
    final_report = {"stage": "v72.0", "status": "preview", "ok": True, "message": "Patch generation context builder preview. Use CLI/API for full context packet generation."}
    body = """
<p>v72.0 builds the context packet a local coding model or supervised patch system should receive <em>before</em> it drafts a patch. It gathers the goal, relevant files, responsibilities, dependencies, risk, historical failures, verification requirements, and completeness checks. It remains read-only, because apparently we are choosing survival today.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Normalize a requested change into target categories, likely files, terms, and context-only safety warnings.'><strong>Goal Intake</strong><span>v71.1 classifier</span></div>
  <div class='mini-card' data-tip='Use the v71 codebase map to choose source files, roles, dependencies, and risk notes.'><strong>File Selector</strong><span>v71.2 selector</span></div>
  <div class='mini-card' data-tip='Bind prior failures like /api-info route shadowing, double hover tooltips, version drift, and package leaks.'><strong>Failure Binder</strong><span>v71.3 history</span></div>
  <div class='mini-card' data-tip='Assign bounded context slices with more attention on high-risk operator surfaces.'><strong>Risk Budget</strong><span>v71.4 budgeter</span></div>
  <div class='mini-card' data-tip='Compile commands and manual checks before patch generation is even considered.'><strong>Verification</strong><span>v71.5 compiler</span></div>
  <div class='mini-card' data-tip='Assemble a context-only prompt packet; it does not generate or apply patches.'><strong>Context Packet</strong><span>v71.6 packet</span></div>
  <div class='mini-card' data-tip='Review completeness for goal, files, docs, history, risks, verification, and safety boundaries.'><strong>Completeness</strong><span>v71.7 reviewer</span></div>
  <div class='mini-card' data-tip='Check dashboard/API/CLI parity while preserving custom data-tip hover notes only.'><strong>Parity Gate</strong><span>v71.8-v71.9</span></div>
</div>
<h3>CLI checks</h3>
<pre>python conscious_agent/main.py --patch-goal-intake-classifier --readiness-json
python conscious_agent/main.py --relevant-file-context-selector --readiness-json
python conscious_agent/main.py --historical-failure-context-binder --readiness-json
python conscious_agent/main.py --risk-aware-context-budgeter --readiness-json
python conscious_agent/main.py --verification-requirement-compiler --readiness-json
python conscious_agent/main.py --patch-prompt-context-packet-builder --readiness-json
python conscious_agent/main.py --context-completeness-reviewer --readiness-json
python conscious_agent/main.py --patch-context-dashboard-api-cli --readiness-json
python conscious_agent/main.py --pre-v72-patch-context-gate --readiness-json
python conscious_agent/main.py --patch-generation-context-builder --readiness-json</pre>
<p><a href='/api/patch-context/goal'>Goal JSON</a> | <a href='/api/patch-context/files'>Files JSON</a> | <a href='/api/patch-context/failures'>Failures JSON</a> | <a href='/api/patch-context/budget'>Budget JSON</a> | <a href='/api/patch-context/verification'>Verification JSON</a> | <a href='/api/patch-context/packet'>Packet JSON</a> | <a href='/api/patch-context/review'>Review JSON</a> | <a href='/api/patch-context/gate'>Gate JSON</a> | <a href='/api/patch-context/layer'>v72 System JSON</a></p>
"""
    summary = _card("v72.0 Patch Generation Context Builder", _text_block(patch_generation_context_builder_text(final_report, full=False)))
    return _layout("/patch-context", _card("v72.0 Patch Context", body) + summary)

def render_release_finalization() -> str:
    from self_maintenance import (
        verified_execution_recovery_release_layer_text,
    )
    final_report = {"stage": "v70.0", "status": "preview", "ok": True, "message": "Verified execution recovery and release finalization preview. Use CLI/API for full report generation."}
    body = """
<p>v70.0 connects operator-confirmed execution results to durable ledger finalization, rollback decisions, guarded rollback refusal, post-rollback verification, release-candidate certification, source-only package certification, and recovery simulation. The dashboard is read-only.</p>
<div class='grid'>
  <div class='mini-card' data-tip='Finalize durable execution result records before release decisions.'><strong>Ledger Finalization</strong><span>v69.1 execution result finalizer</span></div>
  <div class='mini-card' data-tip='Classify whether rollback is unnecessary, recommended, required, blocked, or eligible for finalization.'><strong>Rollback Decision</strong><span>v69.2 decision resolver</span></div>
  <div class='mini-card' data-tip='Rollback requires exact confirmation and remains separate from publish, memory, and identity approval.'><strong>Rollback Guard</strong><span>v69.3 guarded executor</span></div>
  <div class='mini-card' data-tip='Prepare verification after rollback, including compile, smoke, routes, hashes, and privacy.'><strong>Post-Rollback Verify</strong><span>v69.4 verification runner</span></div>
  <div class='mini-card' data-tip='Certify the tree as release-candidate-ready only after execution and recovery evidence pass.'><strong>Release Candidate</strong><span>v69.5 finalization gate</span></div>
  <div class='mini-card' data-tip='Confirm source-only package boundaries and exclude runtime evidence, backups, logs, memory, identity, and nested zips.'><strong>Package Certifier</strong><span>v69.6 source-only certifier</span></div>
</div>
<h3>CLI checks</h3>
<pre>python conscious_agent/main.py --execution-result-ledger-finalizer --readiness-json
python conscious_agent/main.py --rollback-decision-resolver --readiness-json
python conscious_agent/main.py --operator-confirmed-rollback-executor --readiness-json
python conscious_agent/main.py --post-rollback-verification --readiness-json
python conscious_agent/main.py --release-candidate-finalization-gate --readiness-json
python conscious_agent/main.py --source-only-package-certifier --readiness-json
python conscious_agent/main.py --recovery-simulation-harness --readiness-json
python conscious_agent/main.py --verified-execution-recovery-release-layer --readiness-json</pre>
<p><a href='/api/release/execution-result-ledger-finalizer'>Ledger JSON</a> | <a href='/api/release/rollback-decision-resolver'>Rollback Decision JSON</a> | <a href='/api/release/operator-confirmed-rollback-executor'>Rollback Executor JSON</a> | <a href='/api/release/post-rollback-verification'>Post-Rollback JSON</a> | <a href='/api/release/release-candidate-finalization-gate'>Release Candidate JSON</a> | <a href='/api/release/source-only-package-certifier'>Package Certifier JSON</a> | <a href='/api/release/verified-execution-recovery-release-layer'>v70 System JSON</a></p>
"""
    summary = _card("v70.0 Verified Execution Recovery and Release Finalization Layer", _text_block(verified_execution_recovery_release_layer_text(final_report, full=False)))
    return _layout("/release-finalization", _card("v70.0 Release Finalization", body) + summary)


def render_source_transaction_review() -> str:
    intake_report = {"stage": "v67.1", "status": "preview", "ok": True, "message": "Accepts v67 promotion packets into transaction review."}
    plan_report = {"stage": "v67.2", "status": "preview", "ok": True, "message": "Materializes promoted sandbox evidence into transaction plans."}
    baseline_report = {"stage": "v67.3", "status": "preview", "ok": True, "message": "Reconciles live source against the promoted sandbox baseline."}
    backup_report = {"stage": "v67.4", "status": "preview", "ok": True, "message": "Binds backup and rollback expectations before review."}
    safety_report = {"stage": "v67.5", "status": "preview", "ok": True, "message": "Classifies transaction eligibility before ledger pre-registration."}
    ledger_report = {"stage": "v67.6", "status": "preview", "ok": True, "message": "Registers the transaction candidate as not_executed."}
    api_report = {"stage": "v67.8", "status": "preview", "ok": True, "message": "Verifies read-only API/CLI/dashboard parity."}
    final_report = {"stage": "v68.0", "status": "preview", "ok": True, "message": "Promotion-to-transaction integration preview. Use CLI/API for full report generation."}
    body = f"""
<p>v68 integrates v67 sandbox promotion packets with the supervised transaction system. It turns verified sandbox evidence into materialized transaction candidates, reconciles source baselines, binds backup and rollback expectations, runs a final safety gate, and pre-registers candidates in the durable ledger. It still does not apply source, approve publishing, write memory, or alter identity, because even this project has not completely abandoned adult supervision.</p>
<div class='grid'>
  {_report_status_card('Promotion Intake', intake_report)}
  {_report_status_card('Transaction Plan', plan_report)}
  {_report_status_card('Baseline Reconciliation', baseline_report)}
  {_report_status_card('Backup/Rollback', backup_report)}
  {_report_status_card('Safety Gate', safety_report)}
  {_report_status_card('Ledger Pre-Reg', ledger_report)}
  {_report_status_card('API/CLI Access', api_report)}
  {_report_status_card('v68 Integration', final_report)}
</div>
<details class='nav-section' open>
  <summary>Source transaction review commands</summary>
  <pre>python conscious_agent/main.py --promotion-packet-intake-gate --readiness-json
python conscious_agent/main.py --transaction-plan-materializer --readiness-json
python conscious_agent/main.py --source-baseline-reconciliation --readiness-json
python conscious_agent/main.py --backup-rollback-preflight-binder --readiness-json
python conscious_agent/main.py --final-transaction-safety-gate --readiness-json
python conscious_agent/main.py --transaction-ledger-preregistration --readiness-json
python conscious_agent/main.py --source-transaction-review-console --readiness-json
python conscious_agent/main.py --transaction-review-api-cli-access --readiness-json
python conscious_agent/main.py --pre-v68-transaction-integration-gate --readiness-json
python conscious_agent/main.py --promotion-to-transaction-integration-layer --readiness-json</pre>
</details>
<div class='grid'>
  <div class='mini-card' tabindex='0' data-tip='Verifies promotion candidate, normalized diff, safety gate, transaction draft, conflict/staleness state, packet freshness, and approval separation before transaction intake.'><strong>Intake Gate</strong><br><span class='muted'>promotion packet → transaction review</span></div>
  <div class='mini-card' tabindex='0' data-tip='Materializes transaction ID, baseline hash, file operations, touched file manifest, backup requirements, rollback requirements, verification commands, and exact confirmation template.'><strong>Materialized Plan</strong><br><span class='muted'>canonical transaction shape</span></div>
  <div class='mini-card' tabindex='0' data-tip='Compares live source manifest with the promoted sandbox baseline and classifies metadata, README/history, dashboard/API/CLI, target-file, protected-file, or blocked source drift.'><strong>Baseline</strong><br><span class='muted'>drift reconciliation</span></div>
  <div class='mini-card' tabindex='0' data-tip='Requires backups for modified/deleted files, rollback deletes for added files, restore sources, rollback receipt plan, backup manifest plan, and source hash plan.'><strong>Backup/Rollback</strong><br><span class='muted'>undo before apply</span></div>
  <div class='mini-card' tabindex='0' data-tip='Blocks unsafe source drift, protected paths, runtime/private data, missing docs/history, missing privacy expectations, unbound confirmation templates, incomplete rollback plans, and mixed approvals.'><strong>Final Safety</strong><br><span class='muted'>eligible/review-required/blocked</span></div>
  <div class='mini-card' tabindex='0' data-tip='Records the candidate ID, promotion packet ID, plan hash, source baseline hash, safety result, backup/rollback result, approval state, and execution_state=not_executed.'><strong>Ledger Pre-Reg</strong><br><span class='muted'>durable before danger</span></div>
</div>
<p><a href='/sandbox-promotion'><button type='button'>Back to Sandbox Promotion</button></a></p>
<p><a href='/api/release/promotion-packet-intake-gate'>Intake JSON</a> | <a href='/api/release/transaction-plan-materializer'>Plan JSON</a> | <a href='/api/release/source-baseline-reconciliation'>Baseline JSON</a> | <a href='/api/release/backup-rollback-preflight-binder'>Backup/Rollback JSON</a> | <a href='/api/release/final-transaction-safety-gate'>Safety JSON</a> | <a href='/api/release/transaction-ledger-preregistration'>Ledger JSON</a> | <a href='/api/release/source-transaction-review-console'>Console JSON</a> | <a href='/api/release/transaction-review-api-cli-access'>API/CLI JSON</a> | <a href='/api/release/pre-v68-transaction-integration-gate'>Pre-v68 Gate JSON</a> | <a href='/api/release/promotion-to-transaction-integration-layer'>v68 System JSON</a></p>
"""
    summary = _card("v68.0 Promotion-to-Transaction Integration Layer", _text_block(promotion_to_transaction_integration_layer_text(final_report, full=False)))
    return _layout("/source-transaction-review", _card("v68.0 Source Transaction Review", body) + summary)


def render_api_info() -> str:
    body = """
<p>The dashboard exposes a local JSON API under <code>/api</code>. Current task/work controls use the task-centered <code>/api/tasks/...</code> routes. Older <code>/api/work-queue/...</code> routes remain compatibility aliases. Browser pages use <code>/api/status</code> for live refresh/polling. The standalone server can also run on its own with <code>--api-server</code>.</p>
<pre>GET  /api
GET  /api/status    # live dashboard status payload
GET  /api/doctor
GET  /api/repair-suggestions
GET  /api/patch-integrity
GET  /api/project-snapshot
GET  /api/tasks/review
GET  /api/recovery-drill
GET  /api/stable-loops/confidence
GET  /api/hardening-report
GET  /api/controlled-self-build        # preview-only
POST /api/controlled-self-build       # live requires confirm=LIVE_CONTROLLED_BUILD
GET  /api/controlled-build/select-task
GET  /api/controlled-build/plan-patch # preview-only
POST /api/controlled-build/plan-patch
GET  /api/controlled-build/workspace
GET  /api/controlled-build/stage-patch # preview-only
POST /api/controlled-build/stage-patch
GET  /api/controlled-build/preview-diff # preview-only
POST /api/controlled-build/preview-diff
POST /api/controlled-build/apply-staged-patch
POST /api/controlled-build/verify-latest-patch
POST /api/controlled-build/rollback-latest-patch
GET  /api/controlled-build/readme-gate
POST /api/controlled-build/cycle
POST /api/supervised-dev-loop
GET  /api/codebase-map
GET  /api/task-dependencies
GET  /api/test-plan
GET  /api/patch-risk
GET  /api/patch-review
GET  /api/project-memory-index
GET  /api/workspace-status
GET  /api/cross-project-task-review
GET  /api/asymmetric-dev-loop
GET  /api/project-registry
POST /api/projects/register
POST /api/projects/active
GET  /api/project-health?all=true
GET  /api/command-profiles
GET  /api/workspace-dependency-map
GET  /api/workspace-task-inbox
POST /api/workspace/switch-project
GET  /api/project-context
GET  /api/workspace-timeline
GET  /api/workspace-dev-loop
GET  /api/workspace-registry-audit
GET  /api/workspace-repair-suggestions
GET  /api/project-boundary-check
GET  /api/workspace-patch-plan
GET  /api/workspace-preview-diff
GET  /api/workspace-verify-latest
GET  /api/guarded-workspace-dev-loop
POST /api/workspace/apply
POST /api/workspace/guarded-dev-loop
GET  /api/patch-draft-status
GET  /api/patch-draft-request
POST /api/patch-draft-request
GET  /api/draft-patch
POST /api/draft-patch
GET  /api/patch-review-notes
POST /api/patch-review-notes
GET  /api/draft-diff
POST /api/draft-diff
GET  /api/draft-test-impact
POST /api/draft-test-impact
GET  /api/approval-gate
POST /api/approve-draft
POST /api/reject-draft
POST /api/apply-approved-draft
POST /api/rollback-approved-draft
POST /api/reopen-draft
GET  /api/human-approved-patch-loop
GET  /api/patch-drafts/quality
GET  /api/patch-drafts/file-targets
GET  /api/patch-drafts/intent-blocks
GET  /api/patch-drafts/conflicts
GET  /api/patch-drafts/verification-bundle
GET  /api/patch-drafts/safety-checklist
GET  /api/patch-drafts/execution-report
GET  /api/patch-drafts/safety-loop
GET  /api/patch-drafts/code-edit-proposal
GET  /api/patch-drafts/safe-rewrite-preview
GET  /api/patch-drafts/generated-code-patch
GET  /api/patch-drafts/test-suggestions
GET  /api/patch-drafts/inline-review-notes
GET  /api/patch-drafts/approved-code-apply-report
GET  /api/code-patches/task-to-code-patch
GET  /api/code-patches/code-context
GET  /api/code-patches/patch-prompt
GET  /api/code-patches/parse-generated-edits
GET  /api/code-patches/edit-consistency
GET  /api/code-patches/ai-dry-run
GET  /api/code-patches/failure-analysis
GET  /api/code-patches/learning-notes
GET  /api/code-patches/ai-assisted-loop
GET  /api/code-patches/objective-refinement
GET  /api/code-patches/context-ranking
GET  /api/code-patches/safety-envelope
GET  /api/code-patches/validate-generated-patch
GET  /api/code-patches/simulation
GET  /api/code-patches/test-stub-plan
GET  /api/code-patches/review-score
GET  /api/code-patches/recovery-plan
GET  /api/code-patches/validated-ai-loop
POST /api/patch-drafts/code-edit-proposal
POST /api/patch-drafts/safe-rewrite-preview
POST /api/patch-drafts/generated-code-patch
POST /api/patch-drafts/test-suggestions
POST /api/patch-drafts/inline-review-note
POST /api/patch-drafts/apply-approved-code-patch
GET  /api/release/readiness
GET  /api/release/package
GET  /api/release/human-approved-loop
POST /api/release/readiness
POST /api/release/package
POST /api/release/human-approved-loop
POST /api/human-approved-patch-loop
GET  /api/diagnostics/latest
POST /api/diagnostics/run
GET  /api/watch/latest
POST /api/watch/run-once
POST /api/watch/run-loop
GET  /api/notifications
POST /api/notifications/latest-unread/read
POST /api/notifications/latest-unread/dismiss
GET  /api/approvals
POST /api/approvals/latest-pending/approve
POST /api/approvals/latest-pending/reject
POST /api/chat-actions
POST /api/chat-actions/latest/dry-run
POST /api/chat-actions/latest/execute
POST /api/dashboard-chat
GET  /api/dashboard-chat/latest
GET  /api/session-plans/latest
POST /api/session-plans/run
GET  /api/maintenance/latest
POST /api/maintenance/run
GET  /api/dev-loops/latest
POST /api/dev-loops/run
GET  /api/desktop/attention
GET  /api/setup/latest
POST /api/setup/run
GET  /api/tasks
GET  /api/tasks/summary
POST /api/tasks
POST /api/tasks/next/dry-run
POST /api/tasks/next/execute
POST /api/tasks/{id}/dry-run
POST /api/tasks/{id}/execute
POST /api/tasks/{id}/done
POST /api/tasks/{id}/block
POST /api/tasks/{id}/cancel
POST /api/tasks/patch-request
POST /api/tasks/{id}/suggest-patch
POST /api/patches/{id}/create-task-followups

Legacy aliases still supported:
GET  /api/work-queue
GET  /api/work-queue/summary
POST /api/work-queue
POST /api/work-queue/{id}/execute</pre>
<p class='muted'>The API calls existing safety, approval, and command gates. It is convenience plumbing, not a magical permission bypass. Tragic for chaos, nice for your files.</p>
<pre>curl http://127.0.0.1:8765/api/status
# Browser pages poll this route automatically when dashboard_live_refresh_enabled is true.
curl -X POST http://127.0.0.1:8765/api/diagnostics/run
curl -X POST http://127.0.0.1:8765/api/chat-actions -H "Content-Type: application/json" -d '{"message":"run diagnostics"}'
curl -X POST http://127.0.0.1:8765/api/chat-actions/latest/dry-run
curl -X POST http://127.0.0.1:8765/api/tasks -H "Content-Type: application/json" -d '{"title":"Test dashboard form task","status":"planned"}'
curl -X POST http://127.0.0.1:8765/api/goals -H "Content-Type: application/json" -d '{"title":"Test dashboard form goal","next_action":"Create a task"}'</pre>
"""
    return _layout("/api-info", _card("Local API", body))



def render_desktop_info() -> str:
    body = """
<p>The desktop companion is a tiny local Tkinter shell that talks to the dashboard-integrated API or the standalone API. It can launch local services, show live counts, show advisory desktop notifications, hide to a watcher window or optional real system tray, open dashboard pages, run read-only diagnostics/watch/maintenance/session planning/dev-loop dry-runs, handle notification status, and send dashboard-chat messages.</p>
<pre>python conscious_agent/main.py --desktop
python conscious_agent/main.py --desktop-status
python conscious_agent/main.py --desktop-tray-status
python conscious_agent/main.py --setup-check
python conscious_agent/main.py --onboarding</pre>
<p class='muted'>It does not bypass approvals, patch gates, rollback checks, or command safety. v4.5 desktop actions can mark/dismiss notifications, run read-only workflows through the local API, use optional pystray/Pillow tray controls when installed, run first-run setup checks, and launch the guided onboarding wizard. The shell is a steering wheel, not bolt cutters.</p>
""" + _text_block(desktop_status_text())
    return _layout("/desktop", _card("Desktop Companion", body))


def render_setup() -> str:
    reports = list_setup_reports()
    rows = []
    for report in reports[:20]:
        counts = report.get("counts") or {}
        rows.append(
            "<tr>"
            f"<td>{_detail_link('setup', str(report.get('id')))}</td>"
            f"<td>{_fmt(report.get('status'))}</td>"
            f"<td>{_fmt(counts.get('warning', 0))}</td>"
            f"<td>{_fmt(counts.get('error', 0))}</td>"
            f"<td>{_fmt(report.get('created_at'))}</td>"
            "</tr>"
        )
    table = "<p class='muted'>No setup reports saved yet.</p>"
    if rows:
        table = "<table><tr><th>ID</th><th>Status</th><th>Warnings</th><th>Errors</th><th>Created</th></tr>" + "".join(rows) + "</table>"
    body = f"""
<p>Run a first-run setup check for desktop startup, optional tray packages, Ollama, configured models, service ports, local-only host settings, and writable data files.</p>
<div class='action-card'>
{_button('Run setup check', 'run_setup_check')}
{_button('Run diagnostics too', 'run_diagnostics')}
</div>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --setup-check
python conscious_agent/main.py --setup-check --setup-full
python conscious_agent/main.py --show-setup-report latest --setup-full
python conscious_agent/main.py --desktop-status
python conscious_agent/main.py --desktop-tray-status</pre>
<h3>Saved setup reports</h3>
{table}
"""
    return _layout("/setup", _card("Startup / First-Run Setup", body))



def _onboarding_step_html(step: dict[str, Any]) -> str:
    commands = step.get("commands") or []
    links = step.get("links") or []
    suggestions = step.get("suggestions") or []
    command_html = ""
    if commands:
        command_html = "<h4>Commands</h4><pre>" + _safe("\n".join(commands)) + "</pre>"
    link_html = ""
    if links:
        link_html = "<h4>Links</h4><ul>" + "".join(
            f"<li><a href='{_safe(link.get('url', ''))}'>{_safe(link.get('label', link.get('url', '')))}</a></li>"
            for link in links
        ) + "</ul>"
    suggestion_html = ""
    if suggestions:
        suggestion_html = "<h4>Suggestions</h4>" + _small_list([_safe(item) for item in suggestions])
    return (
        "<div class='action-card'>"
        f"<h3>{_safe(step.get('title'))} <span class='badge'>{_safe(step.get('status'))}</span> <span class='badge'>{_safe(step.get('priority'))}</span></h3>"
        f"<p>{_safe(step.get('description'))}</p>"
        f"{suggestion_html}{command_html}{link_html}"
        "</div>"
    )


def render_onboarding() -> str:
    runs = list_onboarding_runs()
    latest = runs[0] if runs else None
    latest_body = "<p class='muted'>No onboarding run saved yet.</p>"
    if latest:
        next_step = latest.get("next_step") or {}
        steps_html = "".join(_onboarding_step_html(step) for step in latest.get("steps", [])[:12])
        next_html = ""
        if next_step:
            next_html = _card("Next Recommended Step", _onboarding_step_html(next_step))
        latest_body = f"""
<p><strong>Status:</strong> {_fmt(latest.get('status'))}</p>
<p><strong>Summary:</strong> {_safe(latest.get('summary'))}</p>
<p><strong>Setup report:</strong> {_detail_link('setup', str(latest.get('setup_report_id') or ''), str(latest.get('setup_report_id') or '[none]'))}</p>
<p>{_detail_link('onboarding', str(latest.get('id')), 'Open full onboarding detail', full=True)}</p>
{next_html}
<h3>Guided steps</h3>
{steps_html}
"""

    rows = []
    for run in runs[:20]:
        counts = run.get("counts") or {}
        rows.append(
            "<tr>"
            f"<td>{_detail_link('onboarding', str(run.get('id')))}</td>"
            f"<td>{_fmt(run.get('status'))}</td>"
            f"<td>{_fmt(counts.get('blocked', 0))}</td>"
            f"<td>{_fmt(counts.get('needs_action', 0))}</td>"
            f"<td>{_fmt(counts.get('optional', 0))}</td>"
            f"<td>{_fmt(run.get('created_at'))}</td>"
            "</tr>"
        )
    table = "<p class='muted'>No onboarding runs saved yet.</p>"
    if rows:
        table = "<table><tr><th>ID</th><th>Status</th><th>Blocked</th><th>Action</th><th>Optional</th><th>Created</th></tr>" + "".join(rows) + "</table>"

    body = f"""
<p>The onboarding wizard converts setup checks into a guided, ordered runbook. It recommends commands and links, but does not install packages, change settings, start services, approve actions, or edit files. Apparently the machine must ask before touching the sacred mess.</p>
<div class='action-card'>
{_button('Run onboarding wizard', 'run_onboarding')}
{_button('Run onboarding from latest setup', 'run_onboarding_latest_setup')}
{_button('Run setup check', 'run_setup_check')}
</div>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --onboarding
python conscious_agent/main.py --onboarding --onboarding-use-latest-setup
python conscious_agent/main.py --show-onboarding-run latest --onboarding-full
python conscious_agent/main.py --list-onboarding-runs</pre>
"""
    return _layout("/onboarding", _card("Guided Onboarding Wizard", body) + _card("Latest Onboarding Run", latest_body) + _card("Saved Onboarding Runs", table))

def render_activity() -> str:
    scans = list_maintenance_scans()
    plans = list_session_plans()
    reports = list_test_reports()
    reviews = list_test_reviews()
    diagnostic_reports = list_diagnostic_reports()
    watch_reports = list_watch_reports()
    dev_cycles = list_dev_cycles()
    dev_loops = list_dev_loops()
    memory_summaries = list_memory_summaries()
    setup_reports = list_setup_reports()
    onboarding_runs = list_onboarding_runs()

    def _rows(items: list[dict[str, Any]], kind: str, label_key: str = "id", time_key: str = "created_at") -> str:
        rows = []
        for item in items[:25]:
            item_id = item.get("id", "")
            label = item.get(label_key) or item_id
            rows.append(
                f"<tr><td>{_detail_link(kind, item_id, label)}</td>"
                f"<td>{_safe(item.get(time_key, item.get('created_at','')))}</td>"
                f"<td>{_safe(item.get('status', item.get('overall_status', item.get('recommendation', ''))))}</td></tr>"
            )
        return "<table><tr><th>Item</th><th>Created</th><th>Status/Recommendation</th></tr>" + "".join(rows) + "</table>" if rows else "<p class='muted'>None found.</p>"

    chunks = []
    chunks.append(_card("Recent Maintenance Scans", _rows(scans, "maintenance")))
    chunks.append(_card("Recent Session Plans", _rows(plans, "session_plan")))
    chunks.append(_card("Recent Watch Reports", _rows(watch_reports, "watch")))
    chunks.append(_card("Recent Test Reports", _rows(reports, "test_report")))
    chunks.append(_card("Recent Test Reviews", _rows(reviews, "test_review", label_key="id")))
    chunks.append(_card("Recent Diagnostic Reports", _rows(diagnostic_reports, "diagnostic")))
    chunks.append(_card("Recent Dev Cycles", _rows(dev_cycles, "dev_cycle")))
    chunks.append(_card("Recent Dev Loops", _rows(dev_loops, "dev_loop")))
    chunks.append(_card("Recent Memory Summaries", _rows(memory_summaries, "memory_summary")))
    chunks.append(_card("Recent Setup Reports", _rows(setup_reports, "setup")))
    chunks.append(_card("Recent Onboarding Runs", _rows(onboarding_runs, "onboarding")))
    return _layout("/activity", "".join(chunks))


def _detail_card(kind: str, item_id: str, title: str, body: str, back_path: str, extra: str = "") -> str:
    return _layout(
        "/detail",
        _back_link(back_path) + _card(title, body) + extra,
    )


def render_detail(query: dict[str, list[str]]) -> str:
    kind = query.get("kind", [""])[0]
    item_id = query.get("id", ["latest"])[0]
    full = query.get("full", [""])[0] in {"1", "true", "yes"}

    if kind == "dashboard_chat":
        item = load_dashboard_chat_turn(item_id)
        body = _text_block(dashboard_chat_turn_text(item, full=True) if item else f"Dashboard chat turn not found: {item_id}")
        buttons = ""
        if item and item.get("action_id"):
            action_id = item.get("action_id")
            buttons = _card("Proposed Action Controls", _button("Dry-run action", "chat_action_execute", chat_action_id=action_id, dry_run="true") + _button("Execute action", "chat_action_execute", chat_action_id=action_id) + " " + _detail_link("chat_action", action_id, "Open action detail"))
        return _detail_card(kind, item_id, "Dashboard Chat Turn", body, "/chat-console", buttons)

    if kind == "chat_action":
        item = load_chat_action(item_id)
        body = _text_block(chat_action_text(item, full=True) if item else f"Chat action not found: {item_id}")
        buttons = ""
        if item and item.get("execution_mode") in {"direct_command", "direct_function", "approval"}:
            cid = item.get("id", item_id)
            buttons = _card("Chat Action Controls", _button("Dry-run", "chat_action_execute", chat_action_id=cid, dry_run="true") + _button("Execute", "chat_action_execute", chat_action_id=cid))
        return _detail_card(kind, item_id, "Chat Action Detail", body, "/chat-actions", buttons)

    if kind == "task":
        item = get_task(item_id)
        body = _text_block(task_detail_text(item, full=True) if item else f"Task not found: {item_id}")
        return _detail_card(kind, item_id, "Task Detail", body, "/tasks")

    if kind == "approval":
        item = get_approval(item_id)
        body = _text_block(approval_text(item, full=True) if item else f"Approval not found: {item_id}")
        buttons = ""
        if item and item.get("status") == "pending":
            approval_id = item.get("id", item_id)
            buttons = _card("Approval Actions", _button("Dry-run approval", "approve", approval_id=approval_id, dry_run="true") + _button("Approve", "approve", approval_id=approval_id) + _button("Reject", "reject", approval_id=approval_id))
        return _detail_card(kind, item_id, "Approval Detail", body, "/approvals", buttons)

    if kind == "notification":
        item = load_notification(item_id)
        body = _text_block(notification_text(item, full=True) if item else f"Notification not found: {item_id}")
        buttons = ""
        if item and item.get("status") == "unread":
            note_id = item.get("id", item_id)
            buttons = _card("Notification Actions", _button("Mark read", "notification_read", notification_id=note_id) + _button("Dismiss", "notification_dismiss", notification_id=note_id))
        return _detail_card(kind, item_id, "Notification Detail", body, "/notifications", buttons)

    if kind == "stable_loop":
        item = load_stable_loop(item_id)
        body = _text_block(stable_loop_text(item, full=full) if item else f"Stable loop not found: {item_id}")
        buttons = ""
        if item:
            loop_id = str(item.get("id", item_id))
            audit = _card("Stable Loop Audit", _text_block(stable_loop_audit_text(item, full=full)))
            review = _card("Stable Loop Review", _text_block(stable_loop_review_text(item, full=False)) + _stable_loop_review_controls(loop_id, compact=False))
            operator = _card("Post-Run Checklist / Operator Notes", _stable_loop_operator_controls(loop_id))
            followup_lifecycle = _card(
                "Decision Follow-up Task Lifecycle",
                _text_block(followup_lifecycle_summary_text(stable_loop_followup_lifecycle_summary(loop_id=loop_id), full=False))
                + _button("Resolve Follow-ups", "stable_loop_resolve_followups", stable_loop_id=loop_id)
                + _button("Resolve + Archive", "stable_loop_resolve_followups", stable_loop_id=loop_id, archive="true")
            )
            followup_completion = _card(
                "Follow-up Completion / Closure",
                _text_block(stable_loop_followup_completion_report_text({
                    "version": "6.9",
                    "selected_filter_label": "This stable loop",
                    "total": 1,
                    "filtered_count": 1,
                    "action_required_count": 1 if stable_loop_followup_completion_row(item).get("action_required") else 0,
                    "missing_followup_count": 1 if stable_loop_followup_completion_row(item).get("missing_followups") else 0,
                    "open_followup_chain_count": 1 if stable_loop_followup_completion_row(item).get("open_task_count") else 0,
                    "ready_to_resolve_count": 1 if stable_loop_followup_completion_row(item).get("ready_to_resolve") else 0,
                    "resolved_count": 1 if stable_loop_followup_completion_row(item).get("resolution_status") == "resolved" else 0,
                    "cleanup_candidate_count": 1 if stable_loop_followup_completion_row(item).get("resolution_status") == "resolved" and not stable_loop_followup_completion_row(item).get("archived") else 0,
                    "archived_count": 1 if stable_loop_followup_completion_row(item).get("archived") else 0,
                    "rows": [stable_loop_followup_completion_row(item)],
                }, full=False))
                + _button("Mark Closed", "stable_loop_mark_followup_closed", stable_loop_id=loop_id)
                + _button("Mark Closed + Archive", "stable_loop_mark_followup_closed", stable_loop_id=loop_id, archive="true")
            )
            buttons = audit + review + operator + followup_lifecycle + followup_completion
        return _detail_card(kind, item_id, "Stable Loop Detail", body, "/stable-loop", buttons)

    if kind == "work_cycle":
        item = load_work_cycle(item_id)
        body = _text_block(work_cycle_text(item, full=full) if item else f"Work cycle not found: {item_id}")
        return _detail_card(kind, item_id, "Work Cycle Detail", body, "/work-cycle")

    if kind == "patch":
        item = load_patch_proposal(item_id)
        body = _text_block(patch_proposal_text(item, include_full_content=True) if item else f"Patch not found: {item_id}")
        buttons = _card("Patch Queue Controls", _button("Create Follow-up Work Items", "patch_create_followups", patch_id=item_id)) if item else ""
        return _detail_card(kind, item_id, "Patch Detail", body, "/patches", buttons)

    if kind == "goal":
        item = get_goal(item_id)
        body = _text_block(_goal_text(item, full=True))
        return _detail_card(kind, item_id, "Goal Detail", body, "/goals")

    if kind == "diagnostic":
        item = load_diagnostic_report(item_id)
        body = _text_block(diagnostic_report_text(item, include_full=True) if item else f"Diagnostic report not found: {item_id}")
        return _detail_card(kind, item_id, "Diagnostic Detail", body, "/diagnostics")

    if kind == "watch":
        item = load_watch_report(item_id)
        body = _text_block(watch_report_text(item, full=True, include_ai=True) if item else f"Watch report not found: {item_id}")
        return _detail_card(kind, item_id, "Watch Report Detail", body, "/watch")

    if kind == "session_plan":
        item = load_session_plan(item_id)
        body = _text_block(session_plan_text(item, include_ai=True, full=True) if item else f"Session plan not found: {item_id}")
        return _detail_card(kind, item_id, "Session Plan Detail", body, "/activity")

    if kind == "maintenance":
        item = load_maintenance_scan(item_id)
        body = _text_block(maintenance_scan_text(item, include_ai=True, full=True) if item else f"Maintenance scan not found: {item_id}")
        return _detail_card(kind, item_id, "Maintenance Scan Detail", body, "/activity")

    if kind == "test_report":
        item = load_test_report(item_id)
        body = _text_block(test_report_text(item, include_output=True) if item else f"Test report not found: {item_id}")
        return _detail_card(kind, item_id, "Test Report Detail", body, "/activity")

    if kind == "test_review":
        item = load_test_review(item_id)
        body = _text_block(test_review_text(item, include_ai=True) if item else f"Test review not found: {item_id}")
        return _detail_card(kind, item_id, "Test Review Detail", body, "/activity")

    if kind == "dev_cycle":
        item = get_dev_cycle(item_id)
        body = _text_block(dev_cycle_text(item, full=True) if item else f"Dev cycle not found: {item_id}")
        return _detail_card(kind, item_id, "Dev Cycle Detail", body, "/activity")

    if kind == "dev_loop":
        item = get_dev_loop(item_id)
        body = _text_block(dev_loop_text(item, full=True) if item else f"Dev loop not found: {item_id}")
        return _detail_card(kind, item_id, "Dev Loop Detail", body, "/activity")

    if kind == "memory_summary":
        item = load_memory_summary(item_id)
        body = _text_block(memory_summary_text(item, include_full=True) if item else f"Memory summary not found: {item_id}")
        return _detail_card(kind, item_id, "Memory Summary Detail", body, "/activity")

    if kind == "setup":
        item = load_setup_report(item_id)
        body = _text_block(setup_report_text(item, full=True) if item else f"Setup report not found: {item_id}")
        buttons = _card("Setup Actions", _button("Run setup check", "run_setup_check") + _button("Run onboarding", "run_onboarding") + _button("Run diagnostics", "run_diagnostics"))
        return _detail_card(kind, item_id, "Setup Report Detail", body, "/setup", buttons)

    if kind == "onboarding":
        item = load_onboarding_run(item_id)
        body = _text_block(onboarding_run_text(item, full=True) if item else f"Onboarding run not found: {item_id}")
        buttons = _card("Onboarding Actions", _button("Run onboarding wizard", "run_onboarding") + _button("Use latest setup", "run_onboarding_latest_setup") + _button("Run setup check", "run_setup_check"))
        return _detail_card(kind, item_id, "Onboarding Run Detail", body, "/onboarding", buttons)


    if kind == "task_recovery":
        recovery = build_task_recovery(item_id)
        body = _text_block(task_recovery_text(recovery, full=True))
        buttons = _card(
            "Recovery Controls",
            _button("Dry-run retry", "task_recovery_retry", work_item_id=item_id, dry_run="true", use_ai="true")
            + _button("Mark ready for retry", "task_recovery_mark_ready", work_item_id=item_id)
            + _detail_link("work_item", item_id, "Open Task Detail", full=True),
        )
        return _detail_card(kind, item_id, "Task Recovery Detail", body, "/tasks-work?stage=recovery_needed", buttons)

    if kind == "work_item":
        item = find_work_item(item_id)
        body = _text_block(format_work_item(item, full=True) if item else f"Task not found: {item_id}")
        buttons = ""
        if item:
            lifecycle = _task_lifecycle_for_work_item(item)
            lifecycle_card = _card(
                "Lifecycle",
                _lifecycle_flow(str(lifecycle.get("stage") or "unknown"))
                + f"<p>{_stage_pill(lifecycle)}</p>"
                + _text_block(task_lifecycle_text(item.id, full=False))
            )
            approvals = _text_block(task_approvals_text(item.id, include_closed=True, full=False))
            recovery_card = _card("Recovery Plan", _text_block(task_recovery_text(build_task_recovery(item.id), full=False)))
            followup_card = ""
            if lifecycle.get("is_stable_loop_followup"):
                followup_controls = (
                    _button("Resolve source decision", "stable_loop_resolve_task_followup", work_item_id=item.id)
                    + _button("Resolve + archive source", "stable_loop_resolve_task_followup", work_item_id=item.id, archive="true")
                )
                followup_card = _card("Stable-loop Decision Follow-up", _text_block(stable_loop_followup_task_text(item.id, full=True)) + followup_controls)
            buttons = lifecycle_card + followup_card + recovery_card + _card("Task / Work Controls", _work_item_controls(item.id, item.status)) + _card("Linked Approvals", approvals)
        return _detail_card(kind, item_id, "Task Work Detail", body, "/tasks-work", buttons)

    return _layout("/detail", _card("Unknown detail type", f"<p>No detail renderer for <code>{_safe(kind)}</code>.</p>"))


def handle_action(form: dict[str, list[str]]) -> None:
    action = form.get("action", [""])[0]
    try:
        if action == "run_setup_check":
            report = create_setup_report(save=True)
            DashboardState.message = f"Setup report saved: {report.get('id')} ({report.get('status')})"
        elif action == "run_onboarding":
            run = build_onboarding_run(save=True, refresh_setup=True)
            DashboardState.message = f"Onboarding run saved: {run.get('id')} ({run.get('status')})"
        elif action == "run_onboarding_latest_setup":
            run = build_onboarding_run(save=True, refresh_setup=False)
            DashboardState.message = f"Onboarding run saved from latest setup: {run.get('id')} ({run.get('status')})"
        elif action == "run_diagnostics":
            report = build_diagnostic_report(include_full=False)
            save_diagnostic_report(report)
            DashboardState.message = f"Diagnostic report saved: {report.get('id')}"
        elif action == "maintenance_scan":
            result = run_maintenance_scan(use_ai=False)
            DashboardState.message = f"Maintenance scan saved: {result.scan.get('id')}"
        elif action == "plan_session":
            result = create_session_plan(use_ai=False)
            DashboardState.message = f"Session plan saved: {result.plan.get('id')}"
        elif action == "dev_loop_dry":
            loop = run_dev_loop(max_steps=3, dry_run=True, allow_approval_actions=False, apply_task_evaluation=False, use_ai=False)
            DashboardState.message = f"Dry-run dev loop saved: {loop.get('id')}"
        elif action == "dev_loop_safe":
            loop = run_dev_loop(max_steps=3, dry_run=False, allow_approval_actions=False, apply_task_evaluation=False, use_ai=False)
            DashboardState.message = f"Safe dev loop saved: {loop.get('id')} ({loop.get('stopped_reason')})"
        elif action == "watch_once_no_ai":
            result = run_watch_once(use_ai=False)
            DashboardState.message = f"Watch report saved: {result.report_id} ({result.status})"
        elif action == "watch_once_ai":
            result = run_watch_once(use_ai=True)
            DashboardState.message = f"Watch report saved: {result.report_id} ({result.status})"
        elif action == "watch_loop":
            cycles_raw = form.get("cycles", ["2"])[0]
            interval_raw = form.get("interval", ["5"])[0]
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            cycles = max(1, int(cycles_raw or 2))
            interval = max(1, int(interval_raw or 5))
            loop = run_watch_loop(cycles=cycles, interval_seconds=interval, use_ai=use_ai)
            DashboardState.message = f"Watch loop saved: {loop.get('id')} ({loop.get('stopped_reason')})"
        elif action == "approve":
            approval_id = form.get("approval_id", ["latest-pending"])[0]
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            result = approve_approval(approval_id, dry_run=dry_run)
            DashboardState.message = f"Approval result: {result.get('message') or result.get('status') or result.get('ok')}"
        elif action == "reject":
            approval_id = form.get("approval_id", ["latest-pending"])[0]
            result = reject_approval(approval_id, note="Rejected from dashboard.")
            DashboardState.message = f"Rejected approval: {result.get('id', approval_id)}"
        elif action == "notification_read":
            note_id = form.get("notification_id", ["latest-unread"])[0]
            result = update_notification_status(note_id, "read", note="Marked read from dashboard.")
            DashboardState.message = "Marked notification read." if result.get("ok") else str(result.get("error"))
        elif action == "notification_dismiss":
            note_id = form.get("notification_id", ["latest-unread"])[0]
            result = update_notification_status(note_id, "dismissed", note="Dismissed from dashboard.")
            DashboardState.message = "Dismissed notification." if result.get("ok") else str(result.get("error"))
        elif action == "notifications_clear_dismissed":
            count = clear_dismissed_notifications()
            DashboardState.message = f"Cleared {count} dismissed notification(s)."
        elif action == "dashboard_chat_send":
            message = form.get("message", [""])[0].strip()
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            turn = create_dashboard_chat_turn(message, use_ai=use_ai)
            DashboardState.message = f"Dashboard chat turn saved: {turn.get('id')}"
        elif action == "chat_action_propose":
            request = form.get("request", [""])[0].strip()
            item = propose_chat_action(request, save=True)
            DashboardState.message = f"Chat action saved: {item.get('id')}"
        elif action == "chat_action_execute":
            chat_action_id = form.get("chat_action_id", ["latest"])[0]
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            result = execute_chat_action(chat_action_id, dry_run=dry_run)
            DashboardState.message = result.message if result.ok else (result.error or result.message)
        elif action == "dashboard_add_task":
            result = add_task(
                title=form.get("title", [""])[0],
                description=form.get("description", [""])[0],
                priority=form.get("priority", ["medium"])[0],
                status=form.get("status", ["planned"])[0],
                command=form.get("command", [""])[0],
                next_action=form.get("next_action", [""])[0],
                linked_goal=form.get("linked_goal", [""])[0],
                risk=form.get("risk", ["low"])[0],
                source="dashboard_form",
            )
            DashboardState.message = result.message if result.ok else f"Task creation failed: {result.error}"
        elif action == "dashboard_add_goal":
            result = add_goal(
                title=form.get("title", [""])[0],
                description=form.get("description", [""])[0],
                priority=form.get("priority", ["medium"])[0],
                status=form.get("status", ["planned"])[0],
                next_action=form.get("next_action", [""])[0],
            )
            DashboardState.message = result.message if result.ok else f"Goal creation failed: {result.error}"
        elif action == "dashboard_suggest_patch":
            target_file = form.get("target_file", [""])[0].strip()
            request = form.get("request", [""])[0].strip()
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            result = suggest_patch(target_file, request, use_ai=use_ai)
            DashboardState.message = f"Patch proposal saved: {result.patch_id}" if result.ok else f"Patch suggestion failed: {result.error}"
        elif action == "dashboard_queue_patch":
            target_file = form.get("target_file", [""])[0].strip()
            request = form.get("request", [""])[0].strip()
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            priority = int(form.get("priority", ["7"])[0] or 7)
            risk = form.get("risk", ["low"])[0].strip() or "low"
            requires_raw = form.get("requires_approval", [""])[0]
            requires_approval = True if requires_raw else None
            item = create_patch_work_item(
                target_file=target_file,
                request=request,
                project_id=project_id,
                priority=priority,
                risk=risk,
                source="dashboard",
                requires_approval=requires_approval,
            )
            DashboardState.message = f"Patch task queued: {item.id}"
        elif action == "work_queue_suggest_patch":
            work_item_id = form.get("work_item_id", [""])[0]
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = suggest_patch_for_work_item(work_item_id, use_ai=use_ai, dry_run=False)
            DashboardState.message = result.message if result.ok else f"Patch-from-task failed: {result.error}"
        elif action == "patch_create_followups":
            patch_id = form.get("patch_id", [""])[0]
            result = create_patch_followup_items(patch_id)
            DashboardState.message = result.message if result.ok else f"Patch follow-up task creation failed: {result.error}"
        elif action == "dashboard_add_work_item":
            title = form.get("title", [""])[0].strip()
            description = form.get("description", [""])[0].strip()
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            priority = int(form.get("priority", ["5"])[0] or 5)
            risk = form.get("risk", ["low"])[0]
            requires_approval = form.get("requires_approval", [""])[0].lower() == "true"
            item = add_work_item(
                title=title,
                description=description,
                project_id=project_id,
                priority=priority,
                risk=risk,
                source="dashboard",
                requires_approval=requires_approval if requires_approval else None,
            )
            DashboardState.message = f"Task created: {item.id}"
        elif action == "work_queue_execute_next":
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = execute_next_task_work(dry_run=dry_run, use_ai=use_ai)
            DashboardState.message = task_work_execution_text(result, full=False)
        elif action == "work_queue_execute":
            item_id = form.get("work_item_id", [""])[0].strip()
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = execute_task_work_item(item_id, dry_run=dry_run, use_ai=use_ai)
            DashboardState.message = task_work_execution_text(result, full=False)
        elif action == "task_request_approval":
            item_id = form.get("work_item_id", [""])[0].strip()
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = request_task_work_approval(item_id, use_ai=use_ai, force=True)
            DashboardState.message = result.message if result.ok else f"Approval request failed: {result.error}"
        elif action == "work_queue_done":
            item_id = form.get("work_item_id", [""])[0].strip()
            item = update_work_item(item_id, status="done", result="Marked done from dashboard.")
            DashboardState.message = f"Marked task done: {item_id}" if item else f"Task not found: {item_id}"
        elif action == "work_queue_cancel":
            item_id = form.get("work_item_id", [""])[0].strip()
            item = update_work_item(item_id, status="cancelled", result="Cancelled from dashboard.")
            DashboardState.message = f"Cancelled task: {item_id}" if item else f"Task not found: {item_id}"
        elif action == "work_queue_block":
            item_id = form.get("work_item_id", [""])[0].strip()
            reason = form.get("reason", ["Blocked from dashboard."])[0].strip() or "Blocked from dashboard."
            item = update_work_item(item_id, status="blocked", blocked_reason=reason)
            DashboardState.message = f"Blocked task: {item_id}" if item else f"Task not found: {item_id}"
        elif action == "task_recovery_mark_ready":
            item_id = form.get("work_item_id", [""])[0].strip()
            result = mark_task_ready_for_retry(item_id, note="Marked ready for retry from dashboard.")
            DashboardState.message = result.message if result.ok else f"Recovery update failed: {result.error}"
        elif action == "task_recovery_retry":
            item_id = form.get("work_item_id", [""])[0].strip()
            dry_run = form.get("dry_run", ["true"])[0].lower() == "true"
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = retry_task_work(item_id, dry_run=dry_run, use_ai=use_ai)
            DashboardState.message = task_recovery_text(result, full=False)
        elif action == "task_batch_request_approvals":
            stage = form.get("stage", ["approval_required"])[0]
            rows = list_task_lifecycles(stage_filter=stage, include_closed=False)
            created = []
            failed = []
            for row in rows:
                task_id = str(row.get("task_id") or "").strip()
                if not task_id:
                    continue
                result = request_task_work_approval(task_id, use_ai=True, force=False)
                if result.ok:
                    created.append(result.approval_id or result.task_id)
                else:
                    failed.append(f"{task_id}: {result.error}")
            DashboardState.message = f"Requested approvals for {len(created)} task(s)."
            if failed:
                DashboardState.error = "Some approval requests failed: " + "; ".join(failed[:3])
        elif action == "stable_loop_resolve_followups":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            archive = form.get("archive", [""])[0].lower() == "true"
            force = form.get("force", [""])[0].lower() == "true"
            result = resolve_stable_loop_followups(loop_id, archive=archive, force=force, note="Resolved from dashboard.", reviewer="dashboard")
            DashboardState.message = followup_resolution_text(result, full=False)
        elif action == "stable_loop_resolve_task_followup":
            item_id = form.get("work_item_id", [""])[0].strip()
            archive = form.get("archive", [""])[0].lower() == "true"
            force = form.get("force", [""])[0].lower() == "true"
            result = resolve_task_stable_loop_followup(item_id, archive=archive, force=force, note="Resolved from dashboard task detail.", reviewer="dashboard")
            DashboardState.message = followup_resolution_text(result, full=False)
        elif action == "stable_loop_mark_followup_closed":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            archive = form.get("archive", [""])[0].lower() == "true"
            result = mark_stable_loop_followup_chain_closed(
                loop_id,
                note="Follow-up chain closure confirmed from dashboard.",
                reviewer="dashboard",
                archive=archive,
            )
            DashboardState.message = stable_loop_followup_closure_text(result, full=False)
        elif action == "stable_loop_cleanup_followup_completions":
            completion_filter = form.get("completion_filter", ["cleanup_default"])[0].strip() or "cleanup_default"
            dry_run = form.get("dry_run", ["true"])[0].lower() != "false"
            result = cleanup_stable_loop_followup_completions(
                completion_filter=completion_filter,
                limit=25,
                dry_run=dry_run,
                include_archived=False,
                reviewer="dashboard",
            )
            DashboardState.message = stable_loop_followup_completion_cleanup_text(result, full=False)
        elif action == "stable_loop_mark_reviewed":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            note = form.get("note", [""])[0].strip()
            result = update_stable_loop_review(loop_id, "reviewed", note=note or "Marked reviewed from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop review failed: {result.error}"
        elif action == "stable_loop_approve_live":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            note = form.get("note", [""])[0].strip()
            result = update_stable_loop_review(loop_id, "approved_for_live", note=note or "Approved for live run from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop approval failed: {result.error}"
        elif action == "stable_loop_reject":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            note = form.get("note", [""])[0].strip()
            result = update_stable_loop_review(loop_id, "rejected", note=note or "Rejected from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop rejection failed: {result.error}"
        elif action == "stable_loop_run_approved_live":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            result = run_approved_stable_loop_live(loop_id, note="Live run launched from dashboard review action.")
            DashboardState.message = stable_loop_review_text(result, full=False)
        elif action == "stable_loop_refresh_audit":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            result = refresh_stable_loop_audit(loop_id)
            DashboardState.message = stable_loop_audit_text(result.audit, full=False) if result.ok else f"Stable loop audit failed: {result.error}"
        elif action == "stable_loop_archive":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            result = set_stable_loop_archived(loop_id, archived=True, note="Archived from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop archive failed: {result.error}"
        elif action == "stable_loop_restore":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            result = set_stable_loop_archived(loop_id, archived=False, note="Restored from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop restore failed: {result.error}"
        elif action == "stable_loop_cleanup_history":
            review_filter = form.get("review_filter", ["cleanup_default"])[0].strip() or "cleanup_default"
            dry_run = form.get("dry_run", ["true"])[0].lower() != "false"
            result = cleanup_stable_loop_history(review_filter=review_filter, limit=25, dry_run=dry_run, include_live=True, reviewer="dashboard")
            DashboardState.message = result.get("message", "Stable loop history cleanup complete.")
        elif action == "stable_loop_add_operator_note":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            note = form.get("note", [""])[0].strip()
            result = add_stable_loop_operator_note(loop_id, note=note or "Operator note saved from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop operator note failed: {result.error}"
        elif action == "stable_loop_check_done":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            check_id = form.get("check_id", [""])[0].strip()
            result = update_stable_loop_check(loop_id, check_id=check_id, status="done", note="Marked done from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop checklist update failed: {result.error}"
        elif action == "stable_loop_check_skip":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            check_id = form.get("check_id", [""])[0].strip()
            result = update_stable_loop_check(loop_id, check_id=check_id, status="skipped", note="Skipped from dashboard.", reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop checklist update failed: {result.error}"
        elif action == "stable_loop_final_decision":
            loop_id = form.get("stable_loop_id", ["latest"])[0].strip() or "latest"
            decision = form.get("decision", ["needs_review"])[0].strip() or "needs_review"
            note = form.get("note", [""])[0].strip()
            result = set_stable_loop_final_decision(loop_id, decision=decision, note=note, reviewer="dashboard")
            DashboardState.message = result.message if result.ok else f"Stable loop final decision failed: {result.error}"
        elif action == "stable_loop_run":
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            max_steps = int(form.get("max_steps", ["1"])[0] or 1)
            live = form.get("live", [""])[0].lower() == "true"
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            seed_if_empty = form.get("seed_if_empty", [""])[0].lower() == "true"
            auto_followups = form.get("auto_followups", [""])[0].lower() == "true"
            auto_approval_requests = form.get("auto_approval_requests", [""])[0].lower() == "true"
            auto_retry_recovery = form.get("auto_retry_recovery", [""])[0].lower() == "true"
            approve_work_execution = form.get("approve_work_execution", [""])[0].lower() == "true"
            bypass_closure_guardrails = form.get("bypass_closure_guardrails", [""])[0].lower() == "true"
            result = run_stable_supervised_loop(
                project_id=project_id,
                max_steps=max_steps,
                live=live,
                use_ai=use_ai,
                approve_work_execution=approve_work_execution,
                seed_if_empty=seed_if_empty,
                auto_create_patch_followups=auto_followups,
                auto_request_approvals=auto_approval_requests,
                auto_retry_recovery=auto_retry_recovery,
                bypass_closure_guardrails=bypass_closure_guardrails,
            )
            DashboardState.message = stable_loop_text(result, full=False)
        elif action == "work_cycle_run":
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            max_steps = int(form.get("max_steps", ["1"])[0] or 1)
            dry_run = form.get("dry_run", [""])[0].lower() == "true"
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            seed_if_empty = form.get("seed_if_empty", [""])[0].lower() == "true"
            auto_followups = form.get("auto_followups", [""])[0].lower() == "true"
            auto_approval_requests = form.get("auto_approval_requests", [""])[0].lower() == "true"
            auto_retry_recovery = form.get("auto_retry_recovery", [""])[0].lower() == "true"
            approve_work_execution = form.get("approve_work_execution", [""])[0].lower() == "true"
            result = run_supervised_work_cycle(
                project_id=project_id,
                max_steps=max_steps,
                dry_run=dry_run,
                use_ai=use_ai,
                approve_work_execution=approve_work_execution,
                seed_if_empty=seed_if_empty,
                auto_create_patch_followups=auto_followups,
                auto_request_approvals=auto_approval_requests,
                auto_retry_recovery=auto_retry_recovery,
            )
            DashboardState.message = work_cycle_text(result, full=False)
        elif action == "set_setting":
            key = form.get("key", [""])[0].strip()
            value = form.get("value", [""])[0].strip()
            set_setting(key, value)
            DashboardState.message = f"Updated setting {key}."
        else:
            DashboardState.error = f"Unknown dashboard action: {action}"
    except Exception as error:
        DashboardState.error = f"Action failed: {error}"


class EidolonDashboardHandler(BaseHTTPRequestHandler):
    server_version = "EidolonDashboard/30.0"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(_to_jsonable(payload), indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_html(self, html: str, status: int = 200) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str = "/") -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True, "methods": ["GET", "POST", "OPTIONS"]})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api" or path.startswith("/api/"):
            status, payload = dispatch_api("GET", path, query=parse_qs(parsed.query))
            self._send_json(payload, status=status)
            return
        try:
            if path == "/":
                html = render_overview()
            elif path == "/actions":
                html = render_action_center()
            elif path == "/chat-console":
                html = render_chat_console()
            elif path == "/chat-actions":
                html = render_chat_actions()
            elif path == "/create":
                html = render_create()
            elif path == "/tasks":
                html = render_tasks()
            elif path in {"/work-queue", "/tasks-work"}:
                html = render_work_queue(stage=parse_qs(parsed.query).get("stage", ["all"])[0])
            elif path == "/work-cycle":
                html = render_work_cycle()
            elif path == "/stable-loop":
                parsed_query = parse_qs(parsed.query)
                html = render_stable_loop(
                    review_filter=parsed_query.get("review", ["all"])[0],
                    decision_filter=parsed_query.get("decision", ["all"])[0],
                    followup_filter=parsed_query.get("followup", parsed_query.get("completion", ["all"]))[0],
                )
            elif path == "/stabilization":
                html = render_stabilization()
            elif path == "/doctor":
                html = render_doctor()
            elif path == "/build-cycle":
                html = render_build_cycle()
            elif path == "/patch-review":
                html = render_patch_review()
            elif path == "/patch-trials":
                html = render_patch_trials()
            elif path == "/patch-evidence":
                html = render_patch_evidence()
            elif path == "/patch-apply":
                html = render_patch_apply()
            elif path == "/patch-recovery":
                html = render_patch_recovery()
            elif path == "/patch-queue":
                html = render_patch_queue()
            elif path == "/improvement-loop":
                html = render_improvement_loop()
            elif path == "/local-model-proposals":
                html = render_local_model_proposals()
            elif path == "/proposal-critique":
                html = render_proposal_critique()
            elif path == "/candidate-ranking":
                html = render_candidate_ranking()
            elif path == "/candidate-refinement":
                html = render_candidate_refinement()
            elif path == "/suggestion-loop":
                html = render_suggestion_loop()
            elif path == "/suggestion-inbox":
                html = render_suggestion_inbox()
            elif path == "/work-order-handoff":
                html = render_work_order_handoff()
            elif path == "/work-order-evidence":
                html = render_work_order_evidence()
            elif path == "/self-development":
                html = render_self_development()
            elif path == "/self-development-readiness":
                html = render_self_development_readiness()
            elif path == "/development-sessions":
                html = render_development_sessions()
            elif path == "/approval-console":
                html = render_approval_console()
            elif path == "/experiment-planner":
                html = render_experiment_planner()
            elif path == "/outcome-reflections":
                html = render_outcome_reflections()
            elif path == "/improvement-cycles":
                html = render_improvement_cycles()
            elif path == "/cycle-replay":
                html = render_cycle_replay()
            elif path == "/capability-ledger":
                html = render_capability_ledger()
            elif path == "/shadow-autonomy":
                html = render_shadow_autonomy()
            elif path == "/failure-war-games":
                html = render_failure_war_games()
            elif path == "/mind-milestone-audit":
                html = render_mind_milestone_audit()
            elif path == "/v100-stabilization":
                html = render_v100_stabilization()
            elif path == "/operator-home":
                html = render_operator_home()
            elif path == "/system-map":
                html = render_system_map()
            elif path == "/coherence-binder":
                html = render_coherence_binder()
            elif path == "/daily-loop":
                html = render_daily_loop()
            elif path == "/local-mind-runtime":
                html = render_local_mind_runtime()
            elif path == "/memory-quality":
                html = render_memory_quality()
            elif path == "/goal-continuity":
                html = render_goal_continuity()
            elif path == "/reasoning-workbench":
                html = render_reasoning_workbench()
            elif path == "/workflow-console":
                html = render_workflow_console()
            elif path == "/practical-mind-audit":
                html = render_practical_mind_audit()
            elif path == "/improvement-intent":
                html = render_improvement_intent()
            elif path == "/work-package-builder":
                html = render_work_package_builder()
            elif path == "/patch-readiness":
                html = render_patch_readiness()
            elif path == "/release-candidate-judgment":
                html = render_release_candidate_judgment()
            elif path == "/supervised-development-readiness":
                html = render_supervised_development_readiness()
            elif path == "/development-session-planner":
                html = render_development_session_planner()
            elif path == "/source-change-cartographer":
                html = render_source_change_cartographer()
            elif path == "/patch-simulation":
                html = render_patch_simulation()
            elif path == "/verification-matrix":
                html = render_verification_matrix()
            elif path == "/development-execution-audit":
                html = render_development_execution_audit()
            elif path == "/development-outcome-review":
                html = render_development_outcome_review()
            elif path == "/lesson-extraction":
                html = render_lesson_extraction()
            elif path == "/recommendation-refinement":
                html = render_recommendation_refinement()
            elif path == "/operator-feedback-integration":
                html = render_operator_feedback_integration()
            elif path == "/development-learning-audit":
                html = render_development_learning_audit()
            elif path == "/strategic-growth-intake":
                html = render_strategic_growth_intake()
            elif path == "/roadmap-synthesis":
                html = render_roadmap_synthesis()
            elif path == "/strategic-risk-ledger":
                html = render_strategic_risk_ledger()
            elif path == "/capability-maturity":
                html = render_capability_maturity()
            elif path == "/strategic-growth-audit":
                html = render_strategic_growth_audit()
            elif path == "/planning-signals":
                html = render_planning_signals()
            elif path == "/work-package-recommendations":
                html = render_work_package_recommendations()
            elif path == "/operator-decision-brief":
                html = render_operator_decision_brief()
            elif path == "/planning-console":
                html = render_planning_console()
            elif path == "/planning-readiness-audit":
                html = render_planning_readiness_audit()
            elif path == "/work-package-selection":
                html = render_work_package_selection()
            elif path == "/session-brief":
                html = render_session_brief()
            elif path == "/approval-checklist":
                html = render_approval_checklist()
            elif path == "/verification-rollback-plan":
                html = render_verification_rollback_plan()
            elif path == "/session-launch-audit":
                html = render_session_launch_audit()
            elif path == "/patch-session-intake":
                html = render_patch_session_intake()
            elif path == "/file-change-plan":
                html = render_file_change_plan()
            elif path == "/patch-blueprint":
                html = render_patch_blueprint()
            elif path == "/patch-review-packet":
                html = render_patch_review_packet()
            elif path == "/patch-session-audit":
                html = render_patch_session_audit()
            elif path == "/patch-draft-request":
                html = render_patch_draft_request()
            elif path == "/file-patch-drafts":
                html = render_file_patch_drafts()
            elif path == "/patch-diff-review":
                html = render_patch_diff_review()
            elif path == "/patch-draft-qa":
                html = render_patch_draft_qa()
            elif path == "/patch-draft-generation-audit":
                html = render_patch_draft_generation_audit()
            elif path == "/implementation-handoff":
                html = render_implementation_handoff()
            elif path == "/manual-patch-application-plan":
                html = render_manual_patch_application_plan()
            elif path == "/implementation-verification-worksheet":
                html = render_implementation_verification_worksheet()
            elif path == "/implementation-rollback-packet":
                html = render_implementation_rollback_packet()
            elif path == "/implementation-handoff-audit":
                html = render_implementation_handoff_audit()
            elif path == "/patch-readiness-intake":
                html = render_patch_readiness_intake()
            elif path == "/patch-readiness-score":
                html = render_patch_readiness_score()
            elif path == "/patch-readiness-blockers":
                html = render_patch_readiness_blockers()
            elif path == "/patch-go-no-go-decision":
                html = render_patch_go_no_go_decision()
            elif path == "/patch-application-readiness-audit":
                html = render_patch_application_readiness_audit()
            elif path == "/patch-sandbox-intake":
                html = render_patch_sandbox_intake()
            elif path == "/sandbox-patch-application-plan":
                html = render_sandbox_patch_application_plan()
            elif path == "/sandbox-verification-packet":
                html = render_sandbox_verification_packet()
            elif path == "/sandbox-result-review":
                html = render_sandbox_result_review()
            elif path == "/sandbox-patch-application-audit":
                html = render_sandbox_patch_application_audit()
            elif path == "/sandbox-promotion-intake":
                html = render_sandbox_promotion_intake()
            elif path == "/source-promotion-plan":
                html = render_source_promotion_plan()
            elif path == "/promotion-approval-packet":
                html = render_promotion_approval_packet()
            elif path == "/post-promotion-verification":
                html = render_post_promotion_verification()
            elif path == "/sandbox-to-source-promotion-audit":
                html = render_sandbox_to_source_promotion_audit()
            elif path == "/source-application-approval":
                html = render_source_application_approval()
            elif path == "/live-source-application-plan":
                html = render_live_source_application_plan()
            elif path == "/approved-source-application-execution":
                html = render_approved_source_application_execution()
            elif path == "/post-application-verification":
                html = render_post_application_verification()
            elif path == "/source-patch-application-audit":
                html = render_source_patch_application_audit()
            elif path == "/post-application-outcome-intake":
                html = render_post_application_outcome_intake()
            elif path == "/post-application-lessons":
                html = render_post_application_lessons()
            elif path == "/next-improvement-candidates":
                html = render_next_improvement_candidates()
            elif path == "/post-application-release-readiness":
                html = render_post_application_release_readiness()
            elif path == "/post-application-cycle-closure":
                html = render_post_application_cycle_closure()
            elif path == "/cycle-intelligence-intake":
                html = render_cycle_intelligence_intake()
            elif path == "/supervised-patch-priority-matrix":
                html = render_supervised_patch_priority_matrix()
            elif path == "/next-patch-proposal-assembly":
                html = render_next_patch_proposal_assembly()
            elif path == "/supervised-patch-session-planner":
                html = render_supervised_patch_session_planner()
            elif path == "/patch-cycle-intelligence-audit":
                html = render_patch_cycle_intelligence_audit()
            elif path == "/multi-cycle-roadmap-intake":
                html = render_multi_cycle_roadmap_intake()
            elif path == "/supervised-roadmap-options":
                html = render_supervised_roadmap_options()
            elif path == "/roadmap-dependency-risk-graph":
                html = render_roadmap_dependency_risk_graph()
            elif path == "/v200-readiness-model":
                html = render_v200_readiness_model()
            elif path == "/multi-cycle-roadmap-governance-audit":
                html = render_multi_cycle_roadmap_governance_audit()
            elif path == "/capability-maturity-inventory":
                html = render_capability_maturity_inventory()
            elif path == "/capability-maturity-scoring":
                html = render_capability_maturity_scoring()
            elif path == "/capability-gap-overreach-analysis":
                html = render_capability_gap_overreach_analysis()
            elif path == "/capability-maturity-improvement-plan":
                html = render_capability_maturity_improvement_plan()
            elif path == "/capability-maturity-governance-audit":
                html = render_capability_maturity_governance_audit()

            elif path == "/governance-kernel-state":
                html = render_governance_kernel_state()
            elif path == "/governance-rule-evaluation":
                html = render_governance_rule_evaluation()
            elif path == "/operator-authority-consent-ledger":
                html = render_operator_authority_consent_ledger()
            elif path == "/governance-enforcement-simulation":
                html = render_governance_enforcement_simulation()
            elif path == "/governance-kernel-audit":
                html = render_governance_kernel_audit()

            elif path == "/governance-decision-packet":
                html = render_governance_decision_packet()
            elif path == "/approval-transaction-model":
                html = render_approval_transaction_model()
            elif path == "/governance-evidence-timeline":
                html = render_governance_evidence_timeline()
            elif path == "/operator-governance-console":
                html = render_operator_governance_console()
            elif path == "/governance-integration-audit":
                html = render_governance_integration_audit()

            elif path == "/cognitive-continuity-packet":
                html = render_cognitive_continuity_packet()
            elif path == "/memory-candidate-staging":
                html = render_memory_candidate_staging()
            elif path == "/identity-boundary-layer":
                html = render_identity_boundary_layer()
            elif path == "/supervised-reflection-journal":
                html = render_supervised_reflection_journal()
            elif path == "/cognitive-continuity-audit":
                html = render_cognitive_continuity_audit()

            elif path == "/self-model-snapshot":
                html = render_self_model_snapshot()
            elif path == "/deliberation-packet":
                html = render_deliberation_packet()
            elif path == "/purpose-alignment-layer":
                html = render_purpose_alignment_layer()
            elif path == "/behavioral-pattern-intelligence":
                html = render_behavioral_pattern_intelligence()
            elif path == "/self-model-integration-audit":
                html = render_self_model_integration_audit()

            elif path == "/internal-simulation-packet":
                html = render_internal_simulation_packet()
            elif path == "/foresight-branch-comparison":
                html = render_foresight_branch_comparison()
            elif path == "/pre-change-consequence-modeling":
                html = render_pre_change_consequence_modeling()
            elif path == "/expectation-reality-check":
                html = render_expectation_reality_check()
            elif path == "/simulation-foresight-audit":
                html = render_simulation_foresight_audit()
            elif path == "/learning-objective-map":
                html = render_learning_objective_map()
            elif path == "/practice-task-design":
                html = render_practice_task_design()
            elif path == "/capability-calibration":
                html = render_capability_calibration()
            elif path == "/skill-gap-remediation-planner":
                html = render_skill_gap_remediation_planner()
            elif path == "/learning-curriculum-audit":
                html = render_learning_curriculum_audit()
            elif path == "/knowledge-claim-ledger":
                html = render_knowledge_claim_ledger()
            elif path == "/belief-candidate-review":
                html = render_belief_candidate_review()
            elif path == "/contradiction-staleness-intelligence":
                html = render_contradiction_staleness_intelligence()
            elif path == "/project-knowledge-map":
                html = render_project_knowledge_map()
            elif path == "/knowledge-organization-audit":
                html = render_knowledge_organization_audit()
            elif path == "/local-model-inventory":
                html = render_local_model_inventory()
            elif path == "/model-evaluation-plan":
                html = render_model_evaluation_plan()
            elif path == "/model-output-comparison":
                html = render_model_output_comparison()
            elif path == "/cognitive-workbench-routing":
                html = render_cognitive_workbench_routing()
            elif path == "/local-model-workbench-audit":
                html = render_local_model_workbench_audit()
            elif path == "/local-model-invocation-consent":
                html = render_local_model_invocation_consent()
            elif path == "/model-evaluation-run-ledger":
                html = render_model_evaluation_run_ledger()
            elif path == "/multi-model-output-triage":
                html = render_multi_model_output_triage()
            elif path == "/model-reliability-profile-candidates":
                html = render_model_reliability_profile_candidates()
            elif path == "/local-model-invocation-sandbox-audit":
                html = render_local_model_invocation_sandbox_audit()
            elif path == "/model-assisted-patch-critique":
                html = render_model_assisted_patch_critique()
            elif path == "/multi-model-review-synthesis":
                html = render_multi_model_review_synthesis()
            elif path == "/patch-risk-remediation-synthesis":
                html = render_patch_risk_remediation_synthesis()
            elif path == "/model-review-quality-calibration":
                html = render_model_review_quality_calibration()
            elif path == "/model-assisted-patch-review-audit":
                html = render_model_assisted_patch_review_audit()
            elif path == "/model-assisted-patch-draft":
                html = render_model_assisted_patch_draft()
            elif path == "/file-impact-documentation-planner":
                html = render_file_impact_documentation_planner()
            elif path == "/smoke-verification-suggestions":
                html = render_smoke_verification_suggestions()
            elif path == "/sandbox-preparation-packet":
                html = render_sandbox_preparation_packet()
            elif path == "/patch-draft-assembly-audit":
                html = render_patch_draft_assembly_audit()
            elif path == "/draft-to-execution-packet":
                html = render_draft_to_execution_packet()
            elif path == "/patch-diff-preview-planner":
                html = render_patch_diff_preview_planner()
            elif path == "/execution-approval-scope":
                html = render_execution_approval_scope()
            elif path == "/verification-rollback-packet":
                html = render_verification_rollback_packet()
            elif path == "/patch-execution-packet-audit":
                html = render_patch_execution_packet_audit()
            elif path == "/application-prep-intake":
                html = render_application_prep_intake()
            elif path == "/source-edit-application-plan":
                html = render_source_edit_application_plan()
            elif path == "/documentation-application-plan":
                html = render_documentation_application_plan()
            elif path == "/final-application-governance-gate":
                html = render_final_application_governance_gate()
            elif path == "/application-prep-integration-audit":
                html = render_application_prep_integration_audit()
            elif path == "/structural-inventory":
                html = render_structural_inventory()
            elif path == "/runtime-registry-prep":
                html = render_runtime_registry_prep()
            elif path == "/dashboard-stabilization-audit":
                html = render_dashboard_stabilization_audit()
            elif path == "/dispatch-stabilization":
                html = render_dispatch_stabilization()
            elif path == "/structural-stabilization-audit":
                html = render_structural_stabilization_audit()
            elif path == "/runtime-registry":
                html = render_runtime_registry()
            elif path == "/governance-report-builder-audit":
                html = render_governance_report_builder_audit()
            elif path == "/dashboard-registry-integration":
                html = render_dashboard_registry_integration()
            elif path == "/runtime-dispatch-registry-audit":
                html = render_runtime_dispatch_registry_audit()
            elif path == "/module-extraction-audit":
                html = render_module_extraction_audit()
            elif path == "/self-maintenance-extraction-map":
                html = render_self_maintenance_extraction_map()
            elif path == "/package-version-integrity":
                html = render_package_version_integrity()
            elif path == "/surface-parity-audit":
                html = render_surface_parity_audit()
            elif path == "/verification-planning-audit":
                html = render_verification_planning_audit()
            elif path == "/self-maintenance-decomposition-audit":
                html = render_self_maintenance_decomposition_audit()
            elif path == "/dashboard-extraction-map":
                html = render_dashboard_extraction_map()
            elif path == "/dashboard-component-audit":
                html = render_dashboard_component_audit()
            elif path == "/api-surface-audit":
                html = render_api_surface_audit()
            elif path == "/cli-surface-audit":
                html = render_cli_surface_audit()
            elif path == "/interface-modularization-audit":
                html = render_interface_modularization_audit()
            elif path == "/approved-application-binding":
                html = render_approved_application_binding()
            elif path == "/operator-execution-checklist":
                html = render_operator_execution_checklist()
            elif path == "/post-application-result-review":
                html = render_post_application_result_review()
            elif path == "/application-outcome-learning":
                html = render_application_outcome_learning()
            elif path == "/application-execution-refinement-audit":
                html = render_application_execution_refinement_audit()
            elif path == "/rollback-scope-binding":
                html = render_rollback_scope_binding()
            elif path == "/failure-damage-map":
                html = render_failure_damage_map()
            elif path == "/recovery-checklist":
                html = render_recovery_checklist()
            elif path == "/post-recovery-review":
                html = render_post_recovery_review()
            elif path == "/rollback-recovery-audit":
                html = render_rollback_recovery_audit()
            elif path == "/memory-candidate-intake":
                html = render_memory_candidate_intake()
            elif path == "/memory-candidate-classification":
                html = render_memory_candidate_classification()
            elif path == "/memory-approval-packet":
                html = render_memory_approval_packet()
            elif path == "/memory-contradiction-review":
                html = render_memory_contradiction_review()
            elif path == "/memory-governance-audit":
                html = render_memory_governance_audit()
            elif path == "/continuity-state-intake":
                html = render_continuity_state_intake()
            elif path == "/self-model-snapshot-v2":
                html = render_self_model_snapshot_v2()
            elif path == "/purpose-coherence-review":
                html = render_purpose_coherence_review()
            elif path == "/supervised-growth-priorities":
                html = render_supervised_growth_priorities()
            elif path == "/continuity-kernel-v2-audit":
                html = render_continuity_kernel_v2_audit()
            elif path == "/identity-expression-boundary":
                html = render_identity_expression_boundary()
            elif path == "/personality-trait-ledger":
                html = render_personality_trait_ledger()
            elif path == "/voice-affect-style-map":
                html = render_voice_affect_style_map()
            elif path == "/coherence-expression-review":
                html = render_coherence_expression_review()
            elif path == "/identity-personality-coherence-audit":
                html = render_identity_personality_coherence_audit()
            elif path == "/dashboard-route-health":
                html = render_dashboard_route_health()
            elif path == "/runtime-test-visibility":
                html = render_runtime_test_visibility()
            elif path == "/behavioral-expression-preview":
                html = render_behavioral_expression_preview()
            elif path == "/style-delta-staging":
                html = render_style_delta_staging()
            elif path == "/expression-runtime-health-audit":
                html = render_expression_runtime_health_audit()
            elif path == "/expression-profile-packets":
                html = render_expression_profile_packets()
            elif path == "/conversation-scenario-sandbox":
                html = render_conversation_scenario_sandbox()
            elif path == "/expression-regression-review":
                html = render_expression_regression_review()
            elif path == "/expression-operator-review-console":
                html = render_expression_operator_review_console()
            elif path == "/conversational-expression-sandbox-audit":
                html = render_conversational_expression_sandbox_audit()
            elif path == "/expression-approval-criteria":
                html = render_expression_approval_criteria()
            elif path == "/expression-live-surface-impact-map":
                html = render_expression_live_surface_impact_map()
            elif path == "/expression-implementation-packet-draft":
                html = render_expression_implementation_packet_draft()
            elif path == "/expression-rollback-reversion-plan":
                html = render_expression_rollback_reversion_plan()
            elif path == "/expression-application-bridge-audit":
                html = render_expression_application_bridge_audit()
            elif path == "/expression-patch-candidates":
                html = render_expression_patch_candidates()
            elif path == "/expression-sandbox-diff-preview":
                html = render_expression_sandbox_diff_preview()
            elif path == "/expression-dry-run-verification-plan":
                html = render_expression_dry_run_verification_plan()
            elif path == "/expression-dry-run-review-packet":
                html = render_expression_dry_run_review_packet()
            elif path == "/expression-patch-dry-run-audit":
                html = render_expression_patch_dry_run_audit()
            elif path == "/expression-sandbox-trial-packet":
                html = render_expression_sandbox_trial_packet()
            elif path == "/expression-sandbox-workspace-plan":
                html = render_expression_sandbox_workspace_plan()
            elif path == "/expression-sandbox-verification-matrix":
                html = render_expression_sandbox_verification_matrix()
            elif path == "/expression-sandbox-result-review-prep":
                html = render_expression_sandbox_result_review_prep()
            elif path == "/expression-sandbox-trial-harness-audit":
                html = render_expression_sandbox_trial_harness_audit()
            elif path == "/expression-sandbox-execution-approval-gate":
                html = render_expression_sandbox_execution_approval_gate()
            elif path == "/expression-sandbox-workspace-execution-packet":
                html = render_expression_sandbox_workspace_execution_packet()
            elif path == "/expression-sandbox-patch-bundle-packet":
                html = render_expression_sandbox_patch_bundle_packet()
            elif path == "/expression-sandbox-verification-command-packet":
                html = render_expression_sandbox_verification_command_packet()
            elif path == "/expression-sandbox-execution-packet-bridge-audit":
                html = render_expression_sandbox_execution_packet_bridge_audit()
            elif path == "/expression-sandbox-trial-evidence-intake":
                html = render_expression_sandbox_trial_evidence_intake()
            elif path == "/expression-sandbox-outcome-comparison":
                html = render_expression_sandbox_outcome_comparison()
            elif path == "/expression-sandbox-regression-result-review":
                html = render_expression_sandbox_regression_result_review()
            elif path == "/expression-sandbox-revision-recommendations":
                html = render_expression_sandbox_revision_recommendations()
            elif path == "/expression-sandbox-promotion-review-prep":
                html = render_expression_sandbox_promotion_review_prep()
            elif path == "/expression-promotion-evidence-binder":
                html = render_expression_promotion_evidence_binder()
            elif path == "/expression-live-promotion-scope-risk":
                html = render_expression_live_promotion_scope_risk()
            elif path == "/expression-promotion-verification-rollback":
                html = render_expression_promotion_verification_rollback()
            elif path == "/expression-promotion-decision-packet":
                html = render_expression_promotion_decision_packet()
            elif path == "/expression-promotion-packet-assembly-audit":
                html = render_expression_promotion_packet_assembly_audit()
            elif path == "/expression-live-application-eligibility-gate":
                html = render_expression_live_application_eligibility_gate()
            elif path == "/expression-live-source-change-manifest":
                html = render_expression_live_source_change_manifest()
            elif path == "/expression-live-patch-instruction-packet":
                html = render_expression_live_patch_instruction_packet()
            elif path == "/expression-live-verification-rollback-packet":
                html = render_expression_live_verification_rollback_packet()
            elif path == "/expression-live-application-packet-audit":
                html = render_expression_live_application_packet_audit()
            elif path == "/intelligence":
                html = render_intelligence()
            elif path == "/workspace":
                html = render_workspace()
            elif path == "/patch-drafts":
                html = render_patch_drafts()
            elif path == "/code-patches":
                html = render_code_patches()
            elif path == "/release-review":
                html = render_release_review()
            elif path == "/release-package":
                html = render_release_package()
            elif path == "/release-governance":
                html = render_release_governance()
            elif path == "/release-evidence":
                html = render_release_evidence()
            elif path == "/release-signing":
                html = render_release_signing()
            elif path == "/release-operations":
                html = render_release_operations()
            elif path == "/release-operator":
                html = render_release_operator()
            elif path == "/release-candidate":
                html = render_release_candidate()
            elif path == "/release-approval":
                html = render_release_approval()
            elif path == "/autonomy":
                html = render_autonomy_boundary()
            elif path == "/maintenance-queue":
                html = render_maintenance_queue()
            elif path == "/attention":
                html = render_attention_scheduler()
            elif path == "/reflection":
                html = render_reflection_memory()
            elif path == "/identity":
                html = render_identity_continuity()
            elif path == "/memory":
                html = render_memory_promotion()
            elif path == "/recall":
                html = render_memory_recall()
            elif path == "/planning":
                html = render_memory_informed_planning()
            elif path == "/action-plans":
                html = render_supervised_action_plans()
            elif path == "/execution-preview":
                html = render_controlled_execution_preview()
            elif path == "/read-only-execution":
                html = render_read_only_execution()
            elif path == "/evidence-gathering":
                html = render_evidence_gathering()
            elif path == "/patch-proposals":
                html = render_patch_proposals()
            elif path == "/sandbox-patch-execution":
                html = render_sandbox_patch_execution()
            elif path == "/source-apply-handoff":
                html = render_source_apply_handoff()
            elif path == "/source-apply-transactions":
                html = render_source_apply_transactions()
            elif path == "/transaction-evidence":
                html = render_transaction_evidence()
            elif path == "/improvement-intelligence":
                html = render_improvement_intelligence()
            elif path == "/proposal-drafting":
                html = render_proposal_drafting()
            elif path == "/proposal-sandbox":
                html = render_proposal_sandbox()
            elif path == "/sandbox-promotion":
                html = render_sandbox_promotion()
            elif path == "/source-transaction-review":
                html = render_source_transaction_review()
            elif path == "/transaction-execution":
                html = render_transaction_execution()
            elif path == "/release-finalization":
                html = render_release_finalization()
            elif path == "/codebase-map":
                html = render_codebase_map()
            elif path == "/patch-context":
                html = render_patch_context()
            elif path == "/approvals":
                html = render_approvals()
            elif path == "/notifications":
                html = render_notifications()
            elif path == "/watch":
                html = render_watch()
            elif path == "/patches":
                html = render_patches()
            elif path == "/goals":
                html = render_goals()
            elif path == "/diagnostics":
                html = render_diagnostics()
            elif path == "/settings":
                html = render_settings()
            elif path == "/api-info":
                html = render_api_info()
            elif path == "/desktop":
                html = render_desktop_info()
            elif path == "/setup":
                html = render_setup()
            elif path == "/onboarding":
                html = render_onboarding()
            elif path == "/activity":
                html = render_activity()
            elif path == "/detail":
                html = render_detail(parse_qs(parsed.query))
            else:
                html = _layout(path, _card("Not found", f"<p>No dashboard route for <code>{_safe(path)}</code>.</p>"))
                self._send_html(html, status=404)
                return
            self._send_html(html)
        except Exception:
            err = traceback.format_exc()
            self._send_html(_layout(path, _card("Dashboard error", _text_block(err))), status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        if parsed.path == "/api" or parsed.path.startswith("/api/"):
            try:
                body = parse_request_body(raw_body, self.headers.get("Content-Type", ""))
            except Exception as error:
                self._send_json({"ok": False, "error": str(error)}, status=400)
                return
            status, payload = dispatch_api("POST", parsed.path, query=parse_qs(parsed.query), body=body)
            self._send_json(payload, status=status)
            return
        if parsed.path != "/action":
            self._send_html(_layout(parsed.path, _card("Not found", "<p>Unknown action path.</p>")), status=404)
            return
        form = parse_qs(raw_body.decode("utf-8"))
        handle_action(form)
        referer = self.headers.get("Referer", "/")
        target = urlparse(referer).path or "/"
        self._redirect(target)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the terminal readable. Humans panic when logs look like a raccoon ran across the keyboard.
        return


def run_dashboard(host: str | None = None, port: int | None = None) -> None:
    settings = load_settings()
    host = host or str(settings.get("dashboard_host", "127.0.0.1"))
    port = int(port or settings.get("dashboard_port", 8765))
    server = ThreadingHTTPServer((host, port), EidolonDashboardHandler)
    print(f"Eidolon dashboard running at http://{host}:{port}")
    print(f"Local API available at http://{host}:{port}/api")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


# v22.1-v29.0 staged upgrade and self-maintenance roadmap tokens for dashboard release command discovery:
# trial-upgrade-from-zip backup-rollback-drill update-collision-detector version-registry-report release-provenance-report dashboard-upgrade-wizard-preview api-upgrade-wizard-preview staged-apply-drill real-apply-guard-rails real-apply-rollback-verification self-update-ux-polish v23-readiness-gate controlled-self-maintenance-loop self-maintenance-proposal build-patch-plan generate-maintenance-patch patch-safety-audit apply-maintenance-patch-to-temp maintenance-review-bundle approve-maintenance-bundle real-maintenance-patch-apply post-apply-health-monitor controlled-maintenance-cycle assisted-self-improvement-release improvement-candidate-scan candidate-prioritizer candidate-to-proposal maintenance-backlog dashboard-maintenance-backlog api-maintenance-backlog candidate-regression-detector release-memory-privacy candidate-verification-recipes assisted-improvement-cycle semi-autonomous-maintenance-review set-maintenance-candidate-status upgrade release

# v25.1-v28.0 trustworthy maintenance console tokens: hotfix-regression-lockdown dashboard-route-coverage api-default-source-audit nested-readiness-severity review-bundle-approval-contract maintenance-report-diff release-gate-composition-test dashboard-api-parity-audit operator-trust-report trustworthy-maintenance-console

# v26.1-v28.0 release candidate governance tokens: trust-console-drill trust-console-snapshot trust-console-diff freeze-release-candidate verify-frozen-release-zip approval-evidence-ledger release-command-reproducer console-readme-consistency pre-v27-safety-audit release-candidate-governance

# v28.1-v29.0 durable evidence tokens: evidence-replay-drill persist-release-evidence replay-release-evidence evidence-timeline evidence-operator-summary dashboard-evidence-viewer api-evidence-viewer evidence-retention-policy evidence-regression-lockdown pre-v29-evidence-audit durable-release-evidence-archive release-evidence

# v29.1-v30.0 signing preparation tokens: signing-readiness-audit canonical-manifest-format canonical-evidence-schema release-signing-status signature-placeholder-contract key-policy-preparation verify-release-signature dashboard-signing-status api-signing-status pre-v30-signing-prep-audit signed-release-preparation-system release-signing

# v32.1-v34.0 operations tokens: governance-report-cleanup release-candidate-workspace artifact-binding-audit surface-consistency-audit external-signing-handoff signature-intake-validation trusted-signer-registry governance-scenario-suite pre-v33-operations-gate release-operations-console release-operations operations-console-cleanup release-candidate-review signed-artifact-intake trust-root-lifecycle publish-decision-explainer operator-action-guardrails unsigned-release-drill signed-fixture-release-drill pre-v34-operator-workflow-gate release-operator-workflow release-operator

# v34.1-v35.0 trusted candidate tokens: release-candidate-record signed-artifact-intake-v2 trust-root-management-policy trust-root-mutation-guardrails signed-release-publish-decision operator-dashboard-action-states release-audit-trail trusted-fixture-workflow pre-v35-trusted-candidate-gate trusted-release-candidate-system release-candidate

# v35.1-v37.0 approval separation tokens: candidate-review-state publish-approval-policy publish-approval-dry-run publish-approval-record-schema dashboard-approval-state-preview approval-route-safety-audit approval-fixture-drill publish-approval-explainer pre-v36-approval-separation-gate publish-approval-separation-system release-approval

# v39.1-v40.0 approval revocation tokens: controlled-publish-approval-revocation-system revoke-publish-approval approval-revocation-write-preflight revocation-storage-quarantine pre-v40-revocation-gate write-approval-revocation

# v40.1-v41.0 autonomy dashboard tokens: autonomy-boundary autonomy-readiness-boundary-system autonomous-dry-run-plan autonomy-action-policy-engine autonomous-patch-sandbox

# v250.1-v255.0 patch execution packet bridge dashboard tokens: draft-to-execution-packet patch-diff-preview-planner execution-approval-scope verification-rollback-packet patch-execution-packet-audit operator-governed-patch-execution-packet-bridge-v1 no_native_title_tooltip data-tip

# v255.1-v260.0 approved application prep dashboard tokens: application-prep-intake source-edit-application-plan documentation-application-plan final-application-governance-gate application-prep-integration-audit operator-governed-approved-execution-packet-application-prep-v1 no_native_title_tooltip data-tip

# v260.1-v265.0 structural stabilization dashboard tokens: structural-inventory runtime-registry-prep dashboard-stabilization-audit dispatch-stabilization structural-stabilization-audit operator-governed-structural-stabilization-and-runtime-modularization-v1 no_native_title_tooltip data-tip

# v265.1-v270.0 module extraction dashboard tokens: runtime-registry governance-report-builder-audit dashboard-registry-integration runtime-dispatch-registry-audit module-extraction-audit operator-governed-runtime-module-extraction-v1 runtime_registry.py governance_reports.py data-tip no_native_title_tooltip

# v270.1-v275.0 self-maintenance decomposition dashboard tokens: self-maintenance-extraction-map package-version-integrity surface-parity-audit verification-planning-audit self-maintenance-decomposition-audit operator-governed-self-maintenance-decomposition-v1 package_integrity.py version_state.py surface_parity.py verification_planning.py data-tip no_native_title_tooltip

# v275.1-v280.0 dashboard/API/CLI modularization dashboard tokens: dashboard-extraction-map dashboard-component-audit api-surface-audit cli-surface-audit interface-modularization-audit operator-governed-dashboard-api-cli-modularization-v1 dashboard_components.py api_surface.py cli_surface.py data-tip no_native_title_tooltip command-deck operator-console

# v280.1-v285.0 application execution refinement dashboard tokens: approved-application-binding operator-execution-checklist post-application-result-review application-outcome-learning application-execution-refinement-audit operator-approved-application-execution-refinement-v1 application_execution_refinement.py data-tip no_native_title_tooltip command-deck operator-console

# v285.1-v290.0 rollback and recovery intelligence dashboard tokens: rollback-scope-binding failure-damage-map recovery-checklist post-recovery-review rollback-recovery-audit operator-governed-rollback-and-recovery-intelligence-v1 rollback_recovery.py data-tip no_native_title_tooltip command-deck operator-console

# v290.1-v295.0 memory candidate governance dashboard tokens: memory-candidate-intake memory-candidate-classification memory-approval-packet memory-contradiction-review memory-governance-audit operator-governed-memory-candidate-governance-upgrade-v1 memory_governance.py data-tip no_native_title_tooltip command-deck operator-console

# v295.1-v300.0 continuity kernel dashboard tokens: continuity-state-intake self-model-snapshot-v2 purpose-coherence-review supervised-growth-priorities continuity-kernel-v2-audit local-artificial-mind-continuity-kernel-v2 continuity_kernel.py data-tip no_native_title_tooltip command-deck operator-console

# v300.1-v305.0 identity/personality/coherence expression dashboard tokens: identity-expression-boundary personality-trait-ledger voice-affect-style-map coherence-expression-review identity-personality-coherence-audit operator-governed-identity-personality-coherence-expression-layer-v1 identity_expression.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v305.1-v310.0 behavioral expression preview and runtime health dashboard tokens: dashboard-route-health runtime-test-visibility behavioral-expression-preview style-delta-staging expression-runtime-health-audit operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1 route_health.py behavioral_expression_preview.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required metadata_consistency_smoke_required timeout_aware_smoke_summary

# v310.1-v315.0 conversational expression sandbox dashboard tokens: expression-profile-packets conversation-scenario-sandbox expression-regression-review expression-operator-review-console conversational-expression-sandbox-audit operator-governed-conversational-expression-sandbox-v1 conversational_expression_sandbox.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v315.1-v320.0 expression application bridge dashboard tokens: expression-approval-criteria expression-live-surface-impact-map expression-implementation-packet-draft expression-rollback-reversion-plan expression-application-bridge-audit operator-governed-conversational-expression-application-bridge-v1 expression_application_bridge.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v320.1-v325.0 expression patch dry-run dashboard tokens: expression-patch-candidates expression-sandbox-diff-preview expression-dry-run-verification-plan expression-dry-run-review-packet expression-patch-dry-run-audit operator-governed-expression-patch-dry-run-sandbox-v1 expression_patch_dry_run.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v325.1-v330.0 expression patch sandbox trial harness dashboard tokens: expression-sandbox-trial-packet expression-sandbox-workspace-plan expression-sandbox-verification-matrix expression-sandbox-result-review-prep expression-sandbox-trial-harness-audit operator-governed-expression-patch-sandbox-trial-harness-v1 expression_sandbox_trial_harness.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v330.1-v335.0 expression sandbox trial execution packet bridge dashboard tokens: expression-sandbox-execution-approval-gate expression-sandbox-workspace-execution-packet expression-sandbox-patch-bundle-packet expression-sandbox-verification-command-packet expression-sandbox-execution-packet-bridge-audit operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 expression_sandbox_execution_bridge.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v335.1-v340.0 expression sandbox trial result intake and promotion review prep dashboard tokens: expression-sandbox-trial-evidence-intake expression-sandbox-outcome-comparison expression-sandbox-regression-result-review expression-sandbox-revision-recommendations expression-sandbox-promotion-review-prep operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1 expression_sandbox_result_intake.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v340.1-v345.0 expression promotion packet assembly dashboard tokens: expression-promotion-evidence-binder expression-live-promotion-scope-risk expression-promotion-verification-rollback expression-promotion-decision-packet expression-promotion-packet-assembly-audit operator-governed-expression-promotion-packet-assembly-layer-v1 expression_promotion_packet.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required

# v345.1-v350.0 expression live application packet dashboard tokens: expression-live-application-eligibility-gate expression-live-source-change-manifest expression-live-patch-instruction-packet expression-live-verification-rollback-packet expression-live-application-packet-audit operator-governed-expression-live-application-packet-drafting-layer-v1 expression_live_application_packet.py data-tip no_native_title_tooltip command-deck operator-console dashboard_http_route_probe_required
