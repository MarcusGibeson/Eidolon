import argparse

from chat import run_chat
from code_reviewer import print_code_review
from patch_suggester import (
    print_patch_suggestion,
    print_patch_list,
    print_patch_proposal,
    list_patch_proposals,
    resolve_patch_id,
)
from patch_applier import (
    print_apply_patch,
    print_applied_patches,
    print_rollback_patch,
    print_rolled_back_patches,
)
from file_tools import list_project_files, read_project_file, search_project_files, project_tree_text
from command_runner import (
    print_allowed_commands,
    print_run_command,
    print_command_history,
)
from test_runner import (
    print_test_workflow,
    print_test_reports,
    print_test_report,
    list_test_reports,
)
from test_report_reviewer import (
    print_test_review,
    print_saved_test_review,
    print_test_reviews,
    list_test_reviews,
)
from self_improver import (
    print_self_improvement,
    print_self_improvement_apply,
    print_self_improvement_runs,
    print_self_improvement_run,
    list_self_improvement_runs,
    latest_self_improvement_patch_id,
)
from maintenance_advisor import (
    print_maintenance_scan,
    print_maintenance_scans,
    print_saved_maintenance_scan,
    list_maintenance_scans,
)
from memory_compactor import (
    print_memory_status,
    print_compact_memory,
    print_memory_summaries,
    print_memory_summary,
    list_memory_summaries,
)
from goal_manager import (
    print_goal_status,
    print_goal_list,
    print_goal_detail,
    print_add_goal,
    print_set_goal_status,
    print_add_goal_note,
    print_add_goal_next_action,
    print_block_goal,
    print_complete_goal,
    list_goals,
    resolve_goal_id,
)
from session_planner import (
    print_session_plan,
    print_session_plans,
    print_saved_session_plan,
    list_session_plans,
)
from work_queue import run_cli as run_work_queue_cli
from task_work_executor import print_execute_next_task_work_item, print_execute_task_work_item
from task_approval_bridge import (
    print_request_task_work_approval,
    print_request_next_task_work_approval,
    print_task_approvals,
)
from task_recovery import (
    print_task_recovery,
    print_task_recoveries,
    print_mark_task_ready_for_retry,
    print_retry_task_work,
)
from task_patch_bridge import (
    print_create_patch_task,
    print_suggest_patch_for_task,
    print_create_patch_task_followups,
)
from work_queue_patch_bridge import (
    print_create_patch_work_item,
    print_suggest_patch_for_work_item,
    print_create_patch_followups,
)
from work_cycle import (
    print_work_cycle,
    print_work_cycles,
    print_saved_work_cycle,
    list_work_cycles,
    resolve_work_cycle_id,
)
from stable_supervised_loop import (
    print_stable_loop_preflight,
    print_stable_loop,
    print_stable_loops,
    print_saved_stable_loop,
    list_stable_loops,
    resolve_stable_loop_id,
)
from stable_loop_review import (
    print_stable_loop_review_summary,
    print_stable_loop_review,
    print_update_stable_loop_review,
    print_run_approved_stable_loop_live,
    print_stable_loop_reviews,
    print_archive_stable_loop,
    print_cleanup_stable_loop_history,
)
from stable_loop_audit import print_stable_loop_audit
from stable_loop_operator_notes import (
    print_stable_loop_operator_notes,
    print_add_stable_loop_operator_note,
    print_update_stable_loop_check,
    print_set_stable_loop_final_decision,
)
from stable_loop_decision_report import (
    print_stable_loop_decision_report,
    print_stable_loop_decision_rows,
    print_cleanup_stable_loop_decisions,
)
from stable_loop_followup_tasks import (
    print_stable_loop_followup_summary,
    print_create_stable_loop_followups,
    print_create_stable_loop_followups_for_decisions,
)
from stable_loop_followup_lifecycle import (
    print_resolve_stable_loop_followups,
    print_resolve_task_stable_loop_followup,
    print_stable_loop_followup_lifecycle_summary,
    print_stable_loop_followup_task,
)
from stable_loop_followup_completion import (
    print_cleanup_stable_loop_followup_completions,
    print_mark_stable_loop_followup_closed,
    print_stable_loop_followup_completion_report,
    print_stable_loop_followup_completion_rows,
)
from stable_loop_guardrails import print_stable_loop_guardrails
from stabilization_checkpoint import print_stabilization_checkpoint
from operational_readiness import (
    print_doctor,
    print_repair_suggestions,
    print_patch_integrity,
    print_project_snapshot,
    print_task_review,
    print_recovery_drill,
    print_stable_loop_confidence,
    print_hardening_report,
    print_controlled_self_build,
)
from controlled_build_cycle import (
    print_controlled_task_selection,
    print_patch_plan,
    print_patch_workspace_status,
    print_stage_controlled_patch,
    print_preview_staged_diff,
    print_apply_staged_patch,
    print_verify_latest_patch,
    print_rollback_latest_patch,
    print_readme_gate,
    print_controlled_build_cycle,
    print_supervised_dev_loop,
)

from project_intelligence import (
    print_codebase_map,
    print_task_dependencies,
    print_test_plan,
    print_patch_risk,
    print_patch_review,
    print_project_memory_index,
    print_workspace_status,
    print_cross_project_task_review,
    print_asymmetric_dev_loop,
)
from workspace_orchestration import (
    print_project_registry,
    print_register_project,
    print_set_active_workspace_project,
    print_project_health,
    print_command_profiles,
    print_workspace_dependency_map,
    print_workspace_task_inbox,
    print_switch_workspace_project,
    print_project_context,
    print_workspace_timeline,
    print_workspace_dev_loop,
)
from workspace_execution import (
    print_workspace_registry_audit,
    print_workspace_repair_suggestions,
    print_project_registration_wizard,
    print_project_boundary_check,
    print_workspace_patch_plan,
    print_workspace_preview_diff,
    print_workspace_apply,
    print_workspace_verify_latest,
    print_guarded_workspace_dev_loop,
)
from patch_drafting import (
    print_patch_draft_request,
    print_draft_patch,
    print_patch_draft_status,
    print_patch_review_notes,
    print_draft_diff,
    print_draft_test_impact,
    print_approve_draft,
    print_reject_draft,
    print_apply_approved_draft,
    print_rollback_approved_draft,
    print_reopen_draft,
    print_human_approved_patch_loop,
    print_draft_quality,
    print_draft_file_targets,
    print_draft_intent_blocks,
    print_draft_conflicts,
    print_draft_verification_bundle,
    print_draft_review_checklist,
    print_approved_draft_execution_report,
    print_review_centered_patch_loop,
)
from release_pipeline import (
    print_code_edit_proposal,
    print_safe_rewrite_preview,
    print_generated_code_patch,
    print_test_suggestions,
    print_inline_review_note,
    print_apply_approved_code_patch,
    print_prepare_release_package,
    print_release_readiness,
    print_human_approved_release_loop,
)
from code_patch_release import (
    print_code_patch_status,
    print_symbol_scan,
    print_rewrite_plan,
    print_rewrite_conflicts,
    print_code_patch_diff_bundle,
    print_apply_code_patch_transaction,
    print_semantic_checks,
    print_release_artifact,
    print_release_audit_trail,
    print_generated_code_release_loop,
)
from ai_patch_assistance import (
    print_task_to_code_patch,
    print_code_context,
    print_patch_prompt,
    print_parse_generated_edits,
    print_edit_consistency,
    print_ai_code_patch_dry_run,
    print_patch_failure_analysis,
    print_patch_learning_notes,
    print_ai_assisted_code_patch_loop,
)
from validated_ai_patch_loop import (
    print_patch_objective_refinement,
    print_code_context_ranking,
    print_patch_safety_envelope,
    print_generated_patch_validation,
    print_patch_simulation,
    print_test_stub_plan,
    print_patch_review_score,
    print_patch_recovery_plan,
    print_validated_ai_code_patch_loop,
)
from approval_release_workflow import (
    print_bind_validated_approval,
    print_ai_patch_review_bundle,
    print_review_bundle_integrity,
    print_approval_ready,
    print_approval_ledger,
    print_apply_validated_ai_patch,
    print_post_apply_review,
    print_package_build_plan,
    print_approval_to_release_loop,
)
from release_packaging import (
    print_release_manifest_integrity,
    print_package_inventory,
    print_package_checksums,
    print_release_notes,
    print_release_handoff_report,
    print_build_release_zip,
    print_verify_release_unzip,
    print_release_pipeline_audit,
    print_verified_release_package_loop,
)
from release_installation import (
    print_release_profiles,
    print_package_privacy_scan,
    print_portable_metadata_check,
    print_first_run_check,
    print_dependency_advisor,
    print_upgrade_notes,
    print_runtime_migration_check,
    print_release_install_verification,
    print_verified_installable_release_loop,
    print_smoke_runtime_hardening,
    print_external_zip_install_verification,
    print_deterministic_release_manifest,
    print_update_dry_run_plan,
    print_atomic_source_update,
    print_runtime_migration_assistant,
    print_route_safety_harness,
    print_release_dashboard_command_center,
    print_clean_room_install_harness,
    print_verified_self_update_release_pipeline,
    print_trial_upgrade_harness,
    print_backup_rollback_drill,
    print_update_collision_detector,
    print_version_registry_report,
    print_release_provenance_report,
    print_dashboard_upgrade_wizard_preview,
    print_api_upgrade_wizard_preview,
    print_staged_apply_drill,
    print_real_apply_guard_rails,
    print_real_apply_rollback_verification,
    print_self_update_ux_polish,
    print_v23_readiness_gate,
    print_controlled_self_maintenance_loop,
)
from self_maintenance import (
    print_self_maintenance_proposal,
    print_patch_plan_builder,
    print_dry_run_patch_generator,
    print_patch_safety_auditor,
    print_apply_patch_to_temp_clone,
    print_maintenance_review_bundle,
    print_human_approval_binding,
    print_real_maintenance_patch_apply,
    print_post_apply_health_monitor,
    print_controlled_maintenance_cycle,
    print_assisted_self_improvement_release,
    print_improvement_candidate_scan,
    print_candidate_prioritizer,
    print_candidate_to_proposal_bridge,
    print_maintenance_backlog_registry,
    print_dashboard_maintenance_backlog,
    print_api_maintenance_backlog,
    print_candidate_regression_detector,
    print_release_memory_privacy,
    print_candidate_verification_recipes,
    print_assisted_improvement_cycle,
    print_semi_autonomous_maintenance_review,
    print_hotfix_regression_lockdown,
    print_dashboard_route_coverage_auditor,
    print_api_default_source_audit,
    print_nested_readiness_severity_engine,
    print_review_bundle_approval_contract,
    print_maintenance_report_diff_viewer,
    print_release_gate_composition_test,
    print_dashboard_api_parity_audit,
    print_operator_trust_report,
    print_trustworthy_maintenance_console,
    print_trust_console_drill,
    print_trust_console_snapshot,
    print_trust_console_diff,
    print_release_candidate_freezer,
    print_frozen_release_zip_verification,
    print_approval_evidence_ledger,
    print_release_command_reproducer,
    print_console_readme_consistency,
    print_pre_v27_safety_audit,
    print_release_candidate_governance,
    print_release_governance_drill,
    print_release_evidence_bundle,
    print_release_evidence_bundle_verifier,
    print_release_governance_page,
    print_governance_api_read_only_surface,
    print_release_artifact_diff,
    print_release_signing_preparation,
    print_local_trust_policy,
    print_release_governance_ux_polish,
    print_pre_v28_governance_audit,
    print_verifiable_release_evidence_system,
    print_evidence_replay_drill,
    print_evidence_bundle_persistence,
    print_replay_release_evidence,
    print_evidence_timeline,
    print_evidence_operator_summary,
    print_dashboard_evidence_viewer,
    print_api_evidence_viewer,
    print_evidence_retention_policy,
    print_evidence_regression_lockdown,
    print_pre_v29_evidence_audit,
    print_durable_release_evidence_archive,
    print_signing_readiness_audit,
    print_canonical_manifest_format,
    print_canonical_evidence_schema,
    print_release_signing_status,
    print_signature_placeholder_contract,
    print_key_policy_preparation,
    print_signature_verification_placeholder,
    print_dashboard_signing_status,
    print_api_signing_status,
    print_pre_v30_signing_prep_audit,
    print_signed_release_preparation_system,
    print_signing_api_hardening,
    print_canonical_schema_validator,
    print_source_data_sanitizer,
    print_signing_trust_model,
    print_release_signing_tamper_drill,
    print_public_key_policy_design,
    print_detached_signature_contract,
    print_signature_fixture_verification,
    print_external_signer_workflow,
    print_detached_signature_verification_system,
    print_signature_verification_hardening,
    print_public_trust_root_config,
    print_external_signing_payload_export,
    print_signed_fixture_test_suite,
    print_release_publish_gate,
    print_release_trust_dashboard_polish,
    print_api_route_safety_audit,
    print_release_reproducibility_check,
    print_pre_v32_release_candidate_gate,
    print_signed_release_governance,
    print_governance_report_cleanup,
    print_release_candidate_workspace,
    print_artifact_binding_audit_v2,
    print_surface_consistency_audit,
    print_external_signing_handoff,
    print_signature_intake_validation,
    print_trusted_signer_registry,
    print_governance_scenario_suite,
    print_pre_v33_operations_gate,
    print_release_operations_console,
    print_operations_console_cleanup,
    print_release_candidate_review,
    print_signed_artifact_intake,
    print_trust_root_lifecycle,
    print_publish_decision_explainer,
    print_operator_action_guardrails,
    print_unsigned_release_drill,
    print_signed_fixture_release_drill,
    print_pre_v34_operator_workflow_gate,
    print_release_operator_workflow,
    print_release_candidate_record_v2,
    print_signed_artifact_intake_v2,
    print_trust_root_management_policy,
    print_trust_root_mutation_guardrails,
    print_signed_release_publish_decision,
    print_operator_dashboard_action_states,
    print_release_workflow_audit_trail,
    print_trusted_fixture_workflow,
    print_pre_v35_trusted_candidate_gate,
    print_trusted_release_candidate_system,
    print_candidate_review_state,
    print_publish_approval_policy,
    print_publish_approval_dry_run,
    print_publish_approval_record_schema,
    print_dashboard_approval_state_preview,
    print_approval_route_safety_audit,
    print_approval_fixture_drill,
    print_publish_approval_explainer,
    print_pre_v36_approval_separation_gate,
    print_publish_approval_separation_system,
    print_publish_approval_record_validator,
    print_publish_approval_dry_run_v2,
    print_approval_storage_quarantine,
    print_publish_approval_api_preview,
    print_dashboard_approval_workflow_preview,
    print_approval_confirmation_policy,
    print_approval_record_fixture_drill,
    print_approval_audit_trail,
    print_pre_v37_approval_records_gate,
    print_controlled_publish_approval_system,
    print_publish_approval_write_preflight,
    print_publish_approval_write_schema_lock,
    print_publish_approval_confirmation_validator,
    print_post_only_approval_write_route_design,
    print_approval_write_dashboard_preview,
    print_write_publish_approval,
    print_approval_write_rollback_safety_audit,
    print_approval_write_fixture_drill,
    print_pre_v38_approval_write_gate,
    print_controlled_publish_approval_write_system,
    print_publish_approval_record_reader,
    print_approval_artifact_revalidation,
    print_approval_record_conflict_detector,
    print_approval_status_viewer,
    print_approval_revocation_policy,
    print_approval_revocation_dry_run,
    print_approval_lifecycle_audit,
    print_approval_lifecycle_fixture_drill,
    print_pre_v39_approval_lifecycle_gate,
    print_publish_approval_lifecycle_system,
    print_approval_revocation_record_schema,
    print_approval_revocation_confirmation_validator,
    print_approval_revocation_write_preflight,
    print_revocation_storage_quarantine,
    print_post_only_revocation_route_design,
    print_write_approval_revocation,
    print_dashboard_revocation_preview,
    print_approval_revocation_fixture_drill,
    print_pre_v40_revocation_gate,
    print_controlled_publish_approval_revocation_system,
    print_autonomy_capability_inventory,
    print_autonomous_task_proposal_schema,
    print_autonomous_dry_run_plan,
    print_autonomy_action_policy_engine,
    print_autonomous_patch_sandbox,
    print_autonomous_patch_risk_classifier,
    print_autonomous_test_selection,
    print_autonomy_human_checkpoint,
    print_pre_v41_autonomy_readiness_gate,
    print_autonomy_readiness_boundary_system,
    print_patch_proposal_schema,
    print_autonomous_change_target_selector,
    print_generate_sandbox_patch,
    print_sandbox_patch_diff,
    print_sandbox_patch_validation,
    print_sandbox_patch_test_run,
    print_patch_review_checkpoint,
    print_source_apply_dry_run,
    print_pre_v42_autonomous_patch_gate,
    print_autonomous_patch_proposal_system,
    print_source_apply_eligibility,
    print_source_apply_confirmation_policy,
    print_source_apply_dry_run_v2,
    print_source_apply_backup_quarantine,
    print_apply_reviewed_patch,
    print_post_source_apply_verification,
    print_source_apply_rollback_preview,
    print_source_apply_fixture_drill,
    print_pre_v43_source_apply_gate,
    print_controlled_source_apply_system,
    print_source_apply_record_reader,
    print_source_rollback_eligibility,
    print_source_rollback_confirmation_policy,
    print_source_rollback_dry_run_v2,
    print_rollback_applied_patch,
    print_post_source_rollback_verification,
    print_source_rollback_audit_trail,
    print_source_rollback_fixture_drill,
    print_pre_v44_source_rollback_gate,
    print_controlled_source_rollback_system,
 )
from self_maintenance import (
    print_self_maintenance_cycle_schema as print_v45_self_maintenance_cycle_schema,
    print_self_maintenance_plan as print_v45_self_maintenance_plan,
    print_self_maintenance_sandbox_cycle as print_v45_self_maintenance_sandbox_cycle,
    print_maintenance_checkpoint_binder as print_v45_maintenance_checkpoint_binder,
    print_self_maintenance_apply_dry_run as print_v45_self_maintenance_apply_dry_run,
    print_self_maintenance_apply_handoff as print_v45_self_maintenance_apply_handoff,
    print_post_maintenance_verification_summary as print_v45_post_maintenance_verification_summary,
    print_self_maintenance_fixture_drill as print_v45_self_maintenance_fixture_drill,
    print_pre_v45_self_maintenance_gate as print_v45_pre_v45_self_maintenance_gate,
    print_controlled_self_maintenance_loop as print_v45_controlled_self_maintenance_loop,
    print_maintenance_task_record_schema as print_v46_maintenance_task_record_schema,
    print_maintenance_task_priority_risk_scoring as print_v46_maintenance_task_priority_risk_scoring,
    print_maintenance_task_queue_registry as print_v46_maintenance_task_queue_registry,
    print_maintenance_task_selection_policy as print_v46_maintenance_task_selection_policy,
    print_maintenance_task_cycle_orchestrator as print_v46_maintenance_task_cycle_orchestrator,
    print_maintenance_task_checkpoint_binding as print_v46_maintenance_task_checkpoint_binding,
    print_maintenance_task_source_apply_lockout as print_v46_maintenance_task_source_apply_lockout,
    print_maintenance_task_dashboard_api_views as print_v46_maintenance_task_dashboard_api_views,
    print_maintenance_task_fixture_drill as print_v46_maintenance_task_fixture_drill,
    print_pre_v46_maintenance_queue_gate as print_v46_pre_v46_maintenance_queue_gate,
    print_controlled_self_maintenance_work_queue as print_v46_controlled_self_maintenance_work_queue,
    print_autonomy_queue_report_cache as print_v47_autonomy_queue_report_cache,
    print_maintenance_task_drilldown_view as print_v47_maintenance_task_drilldown_view,
    print_maintenance_queue_stale_state_warnings as print_v47_maintenance_queue_stale_state_warnings,
    print_maintenance_runtime_privacy_audit as print_v47_maintenance_runtime_privacy_audit,
    print_operator_command_palette_report as print_v47_operator_command_palette_report,
    print_dashboard_api_queue_parity as print_v47_dashboard_api_queue_parity,
    print_queue_verification_receipt as print_v47_queue_verification_receipt,
    print_dashboard_accessibility_compact_layout as print_v47_dashboard_accessibility_compact_layout,
    print_pre_v47_attention_scheduler_gate as print_v47_pre_v47_attention_scheduler_gate,
    print_controlled_attention_scheduler as print_v47_controlled_attention_scheduler,
    print_attention_selection_receipt as print_v47_attention_selection_receipt,
    print_pre_v47_1_attention_receipt_gate as print_v47_pre_v47_1_attention_receipt_gate,
    print_attention_budget_ledger as print_v48_attention_budget_ledger,
    print_deferred_task_memory as print_v48_deferred_task_memory,
    print_blocked_task_handling as print_v48_blocked_task_handling,
    print_attention_resume_context as print_v48_attention_resume_context,
    print_attention_dashboard_polish as print_v48_attention_dashboard_polish,
    print_attention_api_parity_gate as print_v48_attention_api_parity_gate,
    print_reflection_hooks_read_only as print_v48_reflection_hooks_read_only,
    print_pre_v48_reflection_gate as print_v48_pre_v48_reflection_gate,
    print_controlled_reflection_memory_loop as print_v48_controlled_reflection_memory_loop,
    print_reflection_review_receipts as print_v49_reflection_review_receipts,
    print_reflection_candidate_deduplication as print_v49_reflection_candidate_deduplication,
    print_reflection_rejection_memory as print_v49_reflection_rejection_memory,
    print_reflection_promotion_drafts as print_v49_reflection_promotion_drafts,
    print_memory_safety_classifier as print_v49_memory_safety_classifier,
    print_reflection_dashboard_polish as print_v49_reflection_dashboard_polish,
    print_reflection_api_parity_gate as print_v49_reflection_api_parity_gate,
    print_reflection_privacy_package_hardening as print_v49_reflection_privacy_package_hardening,
    print_pre_v49_identity_continuity_gate as print_v49_pre_v49_identity_continuity_gate,
    print_identity_continuity_layer as print_v49_identity_continuity_layer,
    print_identity_receipts as print_v50_0_identity_receipts,
    print_pre_v49_1_identity_receipts_gate as print_v50_0_pre_v49_1_identity_receipts_gate,
    print_stable_principles_ledger as print_v50_stable_principles_ledger,
    print_identity_drift_classifier as print_v50_identity_drift_classifier,
    print_identity_snapshot_comparison as print_v50_identity_snapshot_comparison,
    print_operator_identity_review_drafts as print_v50_operator_identity_review_drafts,
    print_identity_dashboard_polish as print_v50_identity_dashboard_polish,
    print_identity_api_parity_gate as print_v50_identity_api_parity_gate,
    print_identity_privacy_package_hardening as print_v50_identity_privacy_package_hardening,
    print_pre_v50_durable_memory_gate as print_v50_pre_v50_durable_memory_gate,
    print_supervised_durable_memory_promotion as print_v50_supervised_durable_memory_promotion,
    print_memory_promotion_receipts as print_v51_memory_promotion_receipts,
    print_memory_promotion_deduplication as print_v51_memory_promotion_deduplication,
    print_memory_rejection_runtime_ledger as print_v51_memory_rejection_runtime_ledger,
    print_memory_promotion_confirmation_gate as print_v51_memory_promotion_confirmation_gate,
    print_memory_removal_drafts as print_v51_memory_removal_drafts,
    print_memory_dashboard_polish as print_v51_memory_dashboard_polish,
    print_memory_api_parity_gate as print_v51_memory_api_parity_gate,
    print_memory_privacy_package_hardening as print_v51_memory_privacy_package_hardening,
    print_pre_v51_durable_write_gate as print_v51_pre_v51_durable_write_gate,
    print_controlled_durable_memory_write_path as print_v51_controlled_durable_memory_write_path,
    print_durable_memory_write_receipts as print_v52_durable_memory_write_receipts,
    print_memory_store_schema_hardening as print_v52_memory_store_schema_hardening,
    print_memory_read_path as print_v52_memory_read_path,
    print_memory_search_filter as print_v52_memory_search_filter,
    print_memory_correction_drafts as print_v52_memory_correction_drafts,
    print_memory_removal_confirmation_path as print_v52_memory_removal_confirmation_path,
    print_memory_store_dashboard_polish as print_v52_memory_store_dashboard_polish,
    print_memory_store_api_parity_gate as print_v52_memory_store_api_parity_gate,
    print_pre_v52_recall_gate as print_v52_pre_v52_recall_gate,
    print_memory_recall_self_context as print_v52_memory_recall_self_context,
    print_memory_recall_receipts as print_v53_memory_recall_receipts,
    print_recall_conflict_resolver as print_v53_recall_conflict_resolver,
    print_stale_memory_handling as print_v53_stale_memory_handling,
    print_recall_scope_controls as print_v53_recall_scope_controls,
    print_recall_privacy_classifier as print_v53_recall_privacy_classifier,
    print_recall_dashboard_polish as print_v53_recall_dashboard_polish,
    print_recall_api_parity_gate as print_v53_recall_api_parity_gate,
    print_recall_privacy_package_hardening as print_v53_recall_privacy_package_hardening,
    print_pre_v53_memory_informed_planning_gate as print_v53_pre_v53_memory_informed_planning_gate,
    print_memory_informed_planning_loop as print_v53_memory_informed_planning_loop,
    print_memory_informed_planning_receipts as print_v54_memory_informed_planning_receipts,
    print_plan_conflict_classifier as print_v54_plan_conflict_classifier,
    print_plan_revision_drafts as print_v54_plan_revision_drafts,
    print_planning_scope_controls as print_v54_planning_scope_controls,
    print_planning_risk_budget as print_v54_planning_risk_budget,
    print_planning_dashboard_polish as print_v54_planning_dashboard_polish,
    print_planning_api_parity_gate as print_v54_planning_api_parity_gate,
    print_planning_privacy_package_hardening as print_v54_planning_privacy_package_hardening,
    print_pre_v54_action_planning_gate as print_v54_pre_v54_action_planning_gate,
    print_supervised_action_planning_loop as print_v54_supervised_action_planning_loop,
    print_action_plan_receipts as print_v55_action_plan_receipts,
    print_action_step_classifier as print_v55_action_step_classifier,
    print_action_dependency_graph as print_v55_action_dependency_graph,
    print_action_risk_budget as print_v55_action_risk_budget,
    print_action_rehearsal_dry_run_preview as print_v55_action_rehearsal_dry_run_preview,
    print_action_dashboard_polish as print_v55_action_dashboard_polish,
    print_action_api_parity_gate as print_v55_action_api_parity_gate,
    print_action_privacy_package_hardening as print_v55_action_privacy_package_hardening,
    print_pre_v55_controlled_execution_gate as print_v55_pre_v55_controlled_execution_gate,
    print_controlled_action_execution_preview as print_v55_controlled_action_execution_preview,
    print_execution_preview_receipts as print_v56_execution_preview_receipts,
    print_execution_step_permission_classifier as print_v56_execution_step_permission_classifier,
    print_read_only_command_allowlist as print_v56_read_only_command_allowlist,
    print_execution_sandbox_evidence_binder as print_v56_execution_sandbox_evidence_binder,
    print_execution_result_receipts as print_v56_execution_result_receipts,
    print_execution_dashboard_polish as print_v56_execution_dashboard_polish,
    print_execution_api_parity_gate as print_v56_execution_api_parity_gate,
    print_execution_privacy_package_hardening as print_v56_execution_privacy_package_hardening,
    print_pre_v56_read_only_execution_gate as print_v56_pre_v56_read_only_execution_gate,
    print_controlled_read_only_action_execution as print_v56_controlled_read_only_action_execution,
    print_read_only_execution_receipts as print_v57_read_only_execution_receipts,
    print_expanded_diagnostic_allowlist as print_v57_expanded_diagnostic_allowlist,
    print_read_only_output_classifier as print_v57_read_only_output_classifier,
    print_diagnostic_evidence_binder as print_v57_diagnostic_evidence_binder,
    print_diagnostic_result_summaries as print_v57_diagnostic_result_summaries,
    print_read_only_execution_dashboard_polish as print_v57_read_only_execution_dashboard_polish,
    print_read_only_execution_api_parity_gate as print_v57_read_only_execution_api_parity_gate,
    print_read_only_execution_privacy_package_hardening as print_v57_read_only_execution_privacy_package_hardening,
    print_pre_v57_evidence_gathering_gate as print_v57_pre_v57_evidence_gathering_gate,
    print_evidence_gathering_maintenance_loop as print_v57_evidence_gathering_maintenance_loop,
    print_evidence_collection_receipts as print_v58_evidence_collection_receipts,
    print_diagnostic_issue_classifier as print_v58_diagnostic_issue_classifier,
    print_evidence_conflict_staleness_resolver as print_v58_evidence_conflict_staleness_resolver,
    print_evidence_to_plan_update_drafts as print_v58_evidence_to_plan_update_drafts,
    print_diagnostic_coverage_map as print_v58_diagnostic_coverage_map,
    print_evidence_dashboard_polish as print_v58_evidence_dashboard_polish,
    print_evidence_api_parity_gate as print_v58_evidence_api_parity_gate,
    print_evidence_privacy_package_hardening as print_v58_evidence_privacy_package_hardening,
    print_pre_v58_patch_proposal_gate as print_v58_pre_v58_patch_proposal_gate,
    print_evidence_grounded_patch_proposal_loop as print_v58_evidence_grounded_patch_proposal_loop,
    print_patch_proposal_receipts as print_v59_patch_proposal_receipts,
    print_patch_scope_classifier as print_v59_patch_scope_classifier,
    print_patch_risk_budget as print_v59_patch_risk_budget,
    print_patch_diff_preview_drafts as print_v59_patch_diff_preview_drafts,
    print_patch_verification_plan as print_v59_patch_verification_plan,
    print_patch_dashboard_polish as print_v59_patch_dashboard_polish,
    print_patch_api_parity_gate as print_v59_patch_api_parity_gate,
    print_patch_privacy_package_hardening as print_v59_patch_privacy_package_hardening,
    print_pre_v59_sandbox_patch_execution_gate as print_v59_pre_v59_sandbox_patch_execution_gate,
    print_controlled_sandbox_patch_execution as print_v59_controlled_sandbox_patch_execution,
    print_sandbox_execution_receipts as print_v60_sandbox_execution_receipts,
    print_sandbox_verification_matrix as print_v60_sandbox_verification_matrix,
    print_sandbox_drift_detector as print_v60_sandbox_drift_detector,
    print_sandbox_rollback_rehearsal as print_v60_sandbox_rollback_rehearsal,
    print_sandbox_apply_candidate_drafts as print_v60_sandbox_apply_candidate_drafts,
    print_sandbox_dashboard_polish as print_v60_sandbox_dashboard_polish,
    print_sandbox_api_parity_gate as print_v60_sandbox_api_parity_gate,
    print_sandbox_privacy_package_hardening as print_v60_sandbox_privacy_package_hardening,
    print_pre_v60_source_apply_handoff_gate as print_v60_pre_v60_source_apply_handoff_gate,
    print_controlled_sandbox_source_apply_handoff as print_v60_controlled_sandbox_source_apply_handoff,
    print_source_apply_handoff_receipts as print_v61_source_apply_handoff_receipts,
    print_source_baseline_drift_resolver as print_v61_source_baseline_drift_resolver,
    print_reviewed_artifact_set_binder as print_v61_reviewed_artifact_set_binder,
    print_source_apply_handoff_eligibility_classifier as print_v61_source_apply_handoff_eligibility_classifier,
    print_source_apply_dry_run_bridge as print_v61_source_apply_dry_run_bridge,
    print_source_apply_handoff_dashboard_polish as print_v61_source_apply_handoff_dashboard_polish,
    print_source_apply_handoff_api_parity_gate as print_v61_source_apply_handoff_api_parity_gate,
    print_source_apply_handoff_privacy_hardening as print_v61_source_apply_handoff_privacy_hardening,
    print_pre_v61_controlled_apply_bridge_gate as print_v61_pre_v61_controlled_apply_bridge_gate,
    print_controlled_source_apply_bridge_refinement as print_v61_controlled_source_apply_bridge_refinement,
    print_source_apply_transaction_planner as print_v62_source_apply_transaction_planner,
    print_source_apply_backup_binder as print_v62_source_apply_backup_binder,
    print_source_apply_transaction_dry_run_verifier as print_v62_source_apply_transaction_dry_run_verifier,
    print_source_apply_transaction_confirmation_gate as print_v62_source_apply_transaction_confirmation_gate,
    print_supervised_source_apply_executor as print_v62_supervised_source_apply_executor,
    print_post_apply_verification_runner as print_v62_post_apply_verification_runner,
    print_transaction_rollback_rehearsal as print_v62_transaction_rollback_rehearsal,
    print_source_apply_transaction_dashboard_command_center as print_v62_source_apply_transaction_dashboard_command_center,
    print_pre_v62_transaction_release_gate as print_v62_pre_v62_transaction_release_gate,
    print_supervised_source_apply_transaction_layer as print_v62_supervised_source_apply_transaction_layer,
    print_transaction_receipt_ledger as print_v63_transaction_receipt_ledger,
    print_transaction_diff_viewer as print_v63_transaction_diff_viewer,
    print_transaction_conflict_detector as print_v63_transaction_conflict_detector,
    print_transaction_approval_record_binder as print_v63_transaction_approval_record_binder,
    print_transaction_package_evidence_exporter as print_v63_transaction_package_evidence_exporter,
    print_transaction_replay_audit as print_v63_transaction_replay_audit,
    print_transaction_dashboard_receipt_timeline as print_v63_transaction_dashboard_receipt_timeline,
    print_transaction_api_search_filtering as print_v63_transaction_api_search_filtering,
    print_pre_v63_transaction_evidence_gate as print_v63_pre_v63_transaction_evidence_gate,
    print_durable_transaction_evidence_system as print_v63_durable_transaction_evidence_system,
    print_transaction_evidence_summarizer as print_v64_transaction_evidence_summarizer,
    print_improvement_candidate_registry as print_v64_improvement_candidate_registry,
    print_evidence_based_candidate_scoring as print_v64_evidence_based_candidate_scoring,
    print_improvement_regression_pattern_detector as print_v64_improvement_regression_pattern_detector,
    print_improvement_risk_blast_radius_forecaster as print_v64_improvement_risk_blast_radius_forecaster,
    print_supervised_recommendation_queue as print_v64_supervised_recommendation_queue,
    print_improvement_intelligence_dashboard as print_v64_improvement_intelligence_dashboard,
    print_improvement_intelligence_api_cli_access as print_v64_improvement_intelligence_api_cli_access,
    print_pre_v64_improvement_intelligence_gate as print_v64_pre_v64_improvement_intelligence_gate,
    print_supervised_improvement_intelligence_layer as print_v64_supervised_improvement_intelligence_layer,
    print_accepted_recommendation_intake as print_v65_accepted_recommendation_intake,
    print_proposal_draft_skeleton as print_v65_proposal_draft_skeleton,
    print_evidence_requirement_mapper as print_v65_evidence_requirement_mapper,
    print_proposal_risk_contract as print_v65_proposal_risk_contract,
    print_sandbox_patch_request_compiler as print_v65_sandbox_patch_request_compiler,
    print_proposal_review_packet_binder as print_v65_proposal_review_packet_binder,
    print_proposal_dashboard_review_console as print_v65_proposal_dashboard_review_console,
    print_proposal_api_cli_access as print_v65_proposal_api_cli_access,
    print_pre_v65_proposal_drafting_gate as print_v65_pre_v65_proposal_drafting_gate,
    print_recommendation_to_proposal_drafting_layer as print_v65_recommendation_to_proposal_drafting_layer,
    print_reviewed_proposal_acceptance_gate as print_v66_reviewed_proposal_acceptance_gate,
    print_sandbox_workspace_plan as print_v66_sandbox_workspace_plan,
    print_patch_implementation_request as print_v66_patch_implementation_request,
    print_proposal_sandbox_execution_harness as print_v66_proposal_sandbox_execution_harness,
    print_proposal_sandbox_verification_matrix as print_v66_proposal_sandbox_verification_matrix,
    print_proposal_sandbox_evidence_binder as print_v66_proposal_sandbox_evidence_binder,
    print_proposal_sandbox_failure_triage as print_v66_proposal_sandbox_failure_triage,
    print_proposal_sandbox_api_cli_access as print_v66_proposal_sandbox_api_cli_access,
    print_pre_v66_proposal_sandbox_gate as print_v66_pre_v66_proposal_sandbox_gate,
    print_reviewed_proposal_sandbox_execution_layer as print_v66_reviewed_proposal_sandbox_execution_layer,
    print_sandbox_promotion_candidate as print_v67_sandbox_promotion_candidate,
    print_sandbox_source_diff_normalizer as print_v67_sandbox_source_diff_normalizer,
    print_promotion_safety_boundary_gate as print_v67_promotion_safety_boundary_gate,
    print_transaction_draft_from_sandbox as print_v67_transaction_draft_from_sandbox,
    print_promotion_review_packet_binder as print_v67_promotion_review_packet_binder,
    print_promotion_conflict_staleness_detector as print_v67_promotion_conflict_staleness_detector,
    print_sandbox_promotion_api_cli_access as print_v67_sandbox_promotion_api_cli_access,
    print_pre_v67_sandbox_promotion_gate as print_v67_pre_v67_sandbox_promotion_gate,
    print_sandbox_evidence_promotion_handoff_layer as print_v67_sandbox_evidence_promotion_handoff_layer,
    print_promotion_packet_intake_gate as print_v68_promotion_packet_intake_gate,
    print_transaction_plan_materializer as print_v68_transaction_plan_materializer,
    print_source_baseline_reconciliation as print_v68_source_baseline_reconciliation,
    print_backup_rollback_preflight_binder as print_v68_backup_rollback_preflight_binder,
    print_final_transaction_safety_gate as print_v68_final_transaction_safety_gate,
    print_transaction_ledger_preregistration as print_v68_transaction_ledger_preregistration,
    print_source_transaction_review_console as print_v68_source_transaction_review_console,
    print_transaction_review_api_cli_access as print_v68_transaction_review_api_cli_access,
    print_pre_v68_transaction_integration_gate as print_v68_pre_v68_transaction_integration_gate,
    print_promotion_to_transaction_integration_layer as print_v68_promotion_to_transaction_integration_layer,
    print_transaction_execution_eligibility as print_v69_transaction_execution_eligibility,
    print_exact_confirmation_binder as print_v69_exact_confirmation_binder,
    print_backup_snapshot_materializer as print_v69_backup_snapshot_materializer,
    print_transaction_apply_rehearsal as print_v69_transaction_apply_rehearsal,
    print_operator_confirmed_apply_executor as print_v69_operator_confirmed_apply_executor,
    print_post_execution_verification as print_v69_post_execution_verification,
    print_rollback_recommendation_gate as print_v69_rollback_recommendation_gate,
    print_transaction_execution_dashboard_api_cli as print_v69_transaction_execution_dashboard_api_cli,
    print_pre_v69_execution_gate as print_v69_pre_v69_execution_gate,
    print_operator_confirmed_transaction_execution_layer as print_v69_operator_confirmed_transaction_execution_layer,
    print_execution_result_ledger_finalizer as print_v70_execution_result_ledger_finalizer,
    print_rollback_decision_resolver as print_v70_rollback_decision_resolver,
    print_operator_confirmed_rollback_executor as print_v70_operator_confirmed_rollback_executor,
    print_post_rollback_verification as print_v70_post_rollback_verification,
    print_release_candidate_finalization_gate as print_v70_release_candidate_finalization_gate,
    print_source_only_package_certifier as print_v70_source_only_package_certifier,
    print_release_finalization_dashboard_api_cli as print_v70_release_finalization_dashboard_api_cli,
    print_recovery_simulation_harness as print_v70_recovery_simulation_harness,
    print_pre_v70_recovery_finalization_gate as print_v70_pre_v70_recovery_finalization_gate,
    print_verified_execution_recovery_release_layer as print_v70_verified_execution_recovery_release_layer,
    print_source_tree_inventory as print_v71_source_tree_inventory,
    print_module_responsibility_map as print_v71_module_responsibility_map,
    print_dependency_call_surface_map as print_v71_dependency_call_surface_map,
    print_module_risk_profile as print_v71_module_risk_profile,
    print_historical_failure_memory as print_v71_historical_failure_memory,
    print_verification_command_map as print_v71_verification_command_map,
    print_improvement_opportunity_detector as print_v71_improvement_opportunity_detector,
    print_codebase_understanding_dashboard_api_cli as print_v71_codebase_understanding_dashboard_api_cli,
    print_pre_v71_codebase_understanding_gate as print_v71_pre_v71_codebase_understanding_gate,
    print_codebase_understanding_map as print_v71_codebase_understanding_map,
    print_patch_goal_intake_classifier as print_v72_patch_goal_intake_classifier,
    print_relevant_file_context_selector as print_v72_relevant_file_context_selector,
    print_historical_failure_context_binder as print_v72_historical_failure_context_binder,
    print_risk_aware_context_budgeter as print_v72_risk_aware_context_budgeter,
    print_verification_requirement_compiler as print_v72_verification_requirement_compiler,
    print_patch_prompt_context_packet_builder as print_v72_patch_prompt_context_packet_builder,
    print_context_completeness_reviewer as print_v72_context_completeness_reviewer,
    print_patch_context_dashboard_api_cli as print_v72_patch_context_dashboard_api_cli,
    print_pre_v72_patch_context_gate as print_v72_pre_v72_patch_context_gate,
    print_patch_generation_context_builder as print_v72_patch_generation_context_builder,
    print_patch_intent_normalizer as print_v73_patch_intent_normalizer,
    print_patch_scope_contract_builder as print_v73_patch_scope_contract_builder,
    print_patch_prompt_composer as print_v73_patch_prompt_composer,
    print_patch_draft_output_schema as print_v73_patch_draft_output_schema,
    print_patch_draft_safety_reviewer as print_v73_patch_draft_safety_reviewer,
    print_patch_draft_evidence_binder as print_v73_patch_draft_evidence_binder,
    print_patch_draft_dashboard_api_cli as print_v73_patch_draft_dashboard_api_cli,
    print_local_model_handoff_stub as print_v73_local_model_handoff_stub,
    print_pre_v73_patch_draft_gate as print_v73_pre_v73_patch_draft_gate,
    print_supervised_patch_draft_composer as print_v73_supervised_patch_draft_composer,
    print_patch_review_intake_parser as print_v74_patch_review_intake_parser,
    print_patch_review_diff_boundary_extractor as print_v74_patch_review_diff_boundary_extractor,
    print_patch_review_scope_contract_validator as print_v74_patch_review_scope_contract_validator,
    print_patch_review_safety_boundary_validator as print_v74_patch_review_safety_boundary_validator,
    print_documentation_update_validator as print_v74_documentation_update_validator,
    print_verification_plan_validator as print_v74_verification_plan_validator,
    print_patch_risk_scorer as print_v74_patch_risk_scorer,
    print_patch_review_report_builder as print_v74_patch_review_report_builder,
    print_patch_review_dashboard_api_cli as print_v74_patch_review_dashboard_api_cli,
    print_pre_v74_patch_review_gate as print_v74_pre_v74_patch_review_gate,
    print_patch_draft_review_diff_validation_layer as print_v74_patch_draft_review_diff_validation_layer,
    print_patch_trial_intake_binder as print_v75_patch_trial_intake_binder,
    print_disposable_workspace_builder as print_v75_disposable_workspace_builder,
    print_patch_draft_materializer as print_v75_patch_draft_materializer,
    print_sandbox_verification_runner as print_v75_sandbox_verification_runner,
    print_sandbox_evidence_collector as print_v75_sandbox_evidence_collector,
    print_sandbox_escape_mutation_guard as print_v75_sandbox_escape_mutation_guard,
    print_patch_trial_dashboard_api_cli as print_v75_patch_trial_dashboard_api_cli,
    print_patch_trial_cleanup_retention as print_v75_patch_trial_cleanup_retention,
    print_pre_v75_sandbox_trial_gate as print_v75_pre_v75_sandbox_trial_gate,
    print_sandbox_patch_trial_runner as print_v75_sandbox_patch_trial_runner,
    print_patch_evidence_intake_reader as print_v76_patch_evidence_intake_reader,
    print_trial_integrity_validator as print_v76_trial_integrity_validator,
    print_verification_evidence_scorer as print_v76_verification_evidence_scorer,
    print_scope_documentation_evidence_reviewer as print_v76_scope_documentation_evidence_reviewer,
    print_risk_acceptance_classifier as print_v76_risk_acceptance_classifier,
    print_promotion_readiness_packet_builder as print_v76_promotion_readiness_packet_builder,
    print_patch_evidence_dashboard_api_cli as print_v76_patch_evidence_dashboard_api_cli,
    print_recommendation_archive_comparison as print_v76_recommendation_archive_comparison,
    print_pre_v76_evidence_review_gate as print_v76_pre_v76_evidence_review_gate,
    print_sandbox_evidence_review_recommendation_layer as print_v76_sandbox_evidence_review_recommendation_layer,
    print_patch_approval_intake_contract as print_v77_patch_approval_intake_contract,
    print_recommendation_approval_binder as print_v77_recommendation_approval_binder,
    print_live_source_snapshot_builder as print_v77_live_source_snapshot_builder,
    print_approved_patch_materializer as print_v77_approved_patch_materializer,
    print_post_apply_verification_runner as print_v77_post_apply_verification_runner,
    print_automatic_rollback_executor as print_v77_automatic_rollback_executor,
    print_application_evidence_recorder as print_v77_application_evidence_recorder,
    print_patch_application_dashboard_api_cli as print_v77_patch_application_dashboard_api_cli,
    print_pre_v77_application_gate as print_v77_pre_v77_application_gate,
    print_operator_approved_patch_application_layer as print_v77_operator_approved_patch_application_layer,
    print_dirty_tree_preflight_detector as print_v78_dirty_tree_preflight_detector,
    print_snapshot_completeness_validator as print_v78_snapshot_completeness_validator,
    print_partial_apply_detector as print_v78_partial_apply_detector,
    print_rollback_integrity_verifier as print_v78_rollback_integrity_verifier,
    print_failed_verification_triage as print_v78_failed_verification_triage,
    print_recovery_recommendation_builder as print_v78_recovery_recommendation_builder,
    print_application_audit_timeline as print_v78_application_audit_timeline,
    print_patch_recovery_dashboard_api_cli as print_v78_patch_recovery_dashboard_api_cli,
    print_pre_v78_recovery_gate as print_v78_pre_v78_recovery_gate,
    print_verified_application_recovery_rollback_hardening as print_v78_verified_application_recovery_rollback_hardening,
    print_patch_queue_record_schema as print_v79_patch_queue_record_schema,
    print_patch_queue_intake_organizer as print_v79_patch_queue_intake_organizer,
    print_patch_queue_conflict_detector as print_v79_patch_queue_conflict_detector,
    print_patch_queue_risk_priority_scheduler as print_v79_patch_queue_risk_priority_scheduler,
    print_patch_queue_stale_evidence_detector as print_v79_patch_queue_stale_evidence_detector,
    print_patch_queue_serial_trial_plan_builder as print_v79_patch_queue_serial_trial_plan_builder,
    print_patch_queue_operator_review_packet as print_v79_patch_queue_operator_review_packet,
    print_patch_queue_dashboard_api_cli as print_v79_patch_queue_dashboard_api_cli,
    print_pre_v79_queue_gate as print_v79_pre_v79_queue_gate,
    print_multi_patch_queue_planning_layer as print_v79_multi_patch_queue_planning_layer,
    print_improvement_opportunity_intake as print_v80_improvement_opportunity_intake,
    print_improvement_cycle_state_machine as print_v80_improvement_cycle_state_machine,
    print_pipeline_stage_binder as print_v80_pipeline_stage_binder,
    print_local_model_invocation_stub as print_v80_local_model_invocation_stub,
    print_improvement_loop_evidence_recorder as print_v80_improvement_loop_evidence_recorder,
    print_operator_stop_gate as print_v80_operator_stop_gate,
    print_improvement_loop_dashboard_api_cli as print_v80_improvement_loop_dashboard_api_cli,
    print_loop_safety_auditor as print_v80_loop_safety_auditor,
    print_pre_v80_supervised_loop_gate as print_v80_pre_v80_supervised_loop_gate,
    print_supervised_local_improvement_loop as print_v80_supervised_local_improvement_loop,
    print_local_model_adapter_contract as print_v81_local_model_adapter_contract,
    print_model_capability_profile as print_v81_model_capability_profile,
    print_prompt_export_invocation_guard as print_v81_prompt_export_invocation_guard,
    print_proposal_capture_parser as print_v81_proposal_capture_parser,
    print_proposal_safety_precheck as print_v81_proposal_safety_precheck,
    print_model_output_provenance_recorder as print_v81_model_output_provenance_recorder,
    print_proposal_integration_dashboard_api_cli as print_v81_proposal_integration_dashboard_api_cli,
    print_disabled_by_default_invocation_gate as print_v81_disabled_by_default_invocation_gate,
    print_pre_v81_model_integration_gate as print_v81_pre_v81_model_integration_gate,
    print_local_model_patch_proposal_integration as print_v81_local_model_patch_proposal_integration,
    print_proposal_collection_intake as print_v82_proposal_collection_intake,
    print_candidate_diff_normalizer as print_v82_candidate_diff_normalizer,
    print_proposal_quality_heuristic_scorer as print_v82_proposal_quality_heuristic_scorer,
    print_safety_scope_comparison as print_v82_safety_scope_comparison,
    print_verification_plan_comparison as print_v82_verification_plan_comparison,
    print_critique_report_builder as print_v82_critique_report_builder,
    print_critique_dashboard_api_cli as print_v82_critique_dashboard_api_cli,
    print_operator_review_bundle_exporter as print_v82_operator_review_bundle_exporter,
    print_pre_v82_output_critique_gate as print_v82_pre_v82_output_critique_gate,
    print_local_model_output_comparison_critique as print_v82_local_model_output_comparison_critique,
    print_candidate_registry_schema as print_v83_candidate_registry_schema,
    print_candidate_deduplication as print_v83_candidate_deduplication,
    print_risk_weighted_ranking as print_v83_risk_weighted_ranking,
    print_conflict_aware_grouping as print_v83_conflict_aware_grouping,
    print_evidence_completeness_ranker as print_v83_evidence_completeness_ranker,
    print_ranking_explainer as print_v83_ranking_explainer,
    print_ranking_dashboard_api_cli as print_v83_ranking_dashboard_api_cli,
    print_operator_selection_packet as print_v83_operator_selection_packet,
    print_pre_v83_ranking_gate as print_v83_pre_v83_ranking_gate,
    print_multi_model_patch_candidate_ranking as print_v83_multi_model_patch_candidate_ranking,
    print_refinement_goal_binder as print_v84_refinement_goal_binder,
    print_critique_revision_prompt_builder as print_v84_critique_revision_prompt_builder,
    print_constrained_revision_scope_builder as print_v84_constrained_revision_scope_builder,
    print_refinement_safety_reviewer as print_v84_refinement_safety_reviewer,
    print_refinement_evidence_recorder as print_v84_refinement_evidence_recorder,
    print_refinement_iteration_limiter as print_v84_refinement_iteration_limiter,
    print_refinement_dashboard_api_cli as print_v84_refinement_dashboard_api_cli,
    print_operator_revision_packet as print_v84_operator_revision_packet,
    print_pre_v84_refinement_gate as print_v84_pre_v84_refinement_gate,
    print_supervised_patch_candidate_refinement as print_v84_supervised_patch_candidate_refinement,
    print_suggestion_source_intake as print_v85_suggestion_source_intake,
    print_suggestion_cycle_state_machine as print_v85_suggestion_cycle_state_machine,
    print_recurring_suggestion_budgeter as print_v85_recurring_suggestion_budgeter,
    print_safety_boundary_enforcer as print_v85_safety_boundary_enforcer,
    print_suggestion_deduplication_memory as print_v85_suggestion_deduplication_memory,
    print_operator_attention_packet as print_v85_operator_attention_packet,
    print_suggestion_loop_dashboard_api_cli as print_v85_suggestion_loop_dashboard_api_cli,
    print_no_autonomous_apply_auditor as print_v85_no_autonomous_apply_auditor,
    print_pre_v85_suggestion_loop_gate as print_v85_pre_v85_suggestion_loop_gate,
    print_safe_autonomous_suggestion_loop as print_v85_safe_autonomous_suggestion_loop,
    print_suggestion_inbox_record_schema as print_v86_suggestion_inbox_record_schema,
    print_suggestion_intake_normalizer as print_v86_suggestion_intake_normalizer,
    print_suggestion_deduplication_drift_resolver as print_v86_suggestion_deduplication_drift_resolver,
    print_operator_triage_state_machine as print_v86_operator_triage_state_machine,
    print_work_order_draft_builder as print_v86_work_order_draft_builder,
    print_safety_scope_contract_binder as print_v86_safety_scope_contract_binder,
    print_pipeline_handoff_planner as print_v86_pipeline_handoff_planner,
    print_suggestion_inbox_dashboard_api_cli as print_v86_suggestion_inbox_dashboard_api_cli,
    print_pre_v86_suggestion_inbox_gate as print_v86_pre_v86_suggestion_inbox_gate,
    print_supervised_suggestion_inbox_work_order_planner as print_v86_supervised_suggestion_inbox_work_order_planner,
)
import self_maintenance as sm_v90
from task_queue import (
    print_task_status,
    print_task_list,
    print_task_detail,
    print_add_task,
    print_set_task_status,
    print_add_task_note,
    print_add_task_action,
    print_block_task,
    print_complete_task,
    print_start_task,
    print_next_task,
    print_queue_from_session,
    list_tasks,
    resolve_task_id,
)
from task_executor import (
    print_task_command_options,
    print_execute_task,
    print_task_execution_history,
)
from task_result_evaluator import (
    print_task_evaluation,
    print_task_evaluations,
    print_saved_task_evaluation,
    print_apply_task_evaluation,
    list_task_evaluations,
    resolve_task_evaluation_id,
)
from guided_work_session import (
    print_guided_work_session,
    print_advance_guided_work_session,
    print_guided_sessions,
    print_saved_guided_session,
    list_guided_sessions,
    resolve_guided_session_id,
)
from autonomous_dev_cycle import (
    print_dev_cycle,
    print_advance_dev_cycle,
    print_dev_cycles,
    print_saved_dev_cycle,
    list_dev_cycles,
    resolve_dev_cycle_id,
)
from dev_loop_runner import (
    print_dev_loop,
    print_dev_loops,
    print_saved_dev_loop,
    list_dev_loops,
    resolve_dev_loop_id,
)
from approval_manager import (
    print_approval_inbox,
    print_approval,
    print_approve,
    print_reject,
    list_approvals,
    resolve_approval_id,
)
from settings_manager import (
    print_settings,
    print_get_setting,
    print_set_setting,
    print_reset_settings,
    print_settings_health,
    get_setting,
)
from diagnostics import (
    print_diagnostics,
    print_diagnostic_reports,
    print_saved_diagnostic_report,
    list_diagnostic_reports,
)
from watch_mode import (
    print_watch_once,
    print_watch_loop,
    print_watch_reports,
    print_saved_watch_report,
    list_watch_reports,
    resolve_watch_report_id,
)
from notification_manager import (
    print_notifications,
    print_notification,
    print_mark_notification_read,
    print_dismiss_notification,
    print_clear_dismissed_notifications,
    list_notifications,
    resolve_notification_id,
)
from chat_action_router import (
    print_chat_action,
    print_execute_chat_action,
    print_chat_actions,
    print_saved_chat_action,
    list_chat_actions,
    resolve_chat_action_id,
)
from self_development_cycle import (
    print_self_development_cycle,
    print_self_development_cycles,
    print_saved_self_development_cycle,
    print_self_development_trial_review,
    print_broad_smoke_triage,
    print_self_development_dashboard_hardening_review,
    print_self_development_implementation_proposal,
    print_operator_approved_self_development_patch_draft,
    print_operator_approved_self_development_patch_application_trial,
    print_self_development_application_receipt_review,
    print_current_smoke_debt_ledger,
    print_low_risk_smoke_debt_cleanup_candidates,
    print_self_development_smoke_debt_dashboard,
    print_self_development_api_surface_truth_review,
    print_self_development_cycle_duplicate_cleanup_review,
    print_legacy_self_maintenance_smoke_blocker_review,
    print_current_smoke_debt_ledger_reconciliation_review,
    print_current_audit_wording_cleanup_review,
    print_manifest_generation_prep_review,
    print_manifest_gated_surface_validation_review,
    print_manifest_driven_surface_registry_pilot_review,
    print_manifest_surface_generation_readiness_review,
    print_manifest_registry_expanded_review_surfaces_review,
    print_manifest_registry_generation_readiness_scoring_review,
    print_manifest_registry_drift_detection_review,
    print_manifest_guided_validation_probe_dry_run_review,
    print_manifest_guided_generated_validation_probe_review,
    print_manifest_smoke_segment_parity_drift_review,
    print_manifest_smoke_segment_parity_repair_packet_review,
    print_manifest_smoke_segment_repair_application_review,
    print_manifest_segment_parity_enforcement_gate_review,
    print_manifest_guided_validation_probe_expansion_readiness_review,
    print_manifest_guided_multi_surface_validation_probe_dry_run_review,
    print_manifest_guided_multi_surface_generated_validation_probe_packet_review,
    print_manifest_guided_multi_surface_probe_packet_consistency_gate_review,
    print_manifest_guided_sandbox_probe_file_generation_readiness_review,
    print_manifest_guided_sandbox_probe_file_generation_dry_run,
    print_operator_approved_sandbox_probe_file_generation_trial,
    print_sandbox_probe_file_verification_and_cleanup_review,
    print_sandbox_probe_execution_harness_readiness_review,
    print_operator_approved_sandbox_probe_execution_trial,
    print_sandbox_probe_execution_result_review_and_promotion_readiness,
    print_live_probe_promotion_plan_review,
    print_operator_approved_live_probe_registration_trial,
    print_live_registered_probe_verification_and_structural_hardening_review,
    print_v905_baseline_verification_and_manifest_version_semantics_prep,
    print_manifest_version_semantics_split_review,
    print_manifest_validation_normalization_review,
    print_source_package_privacy_deep_scan_review,
    print_metadata_and_current_marker_gate_reconciliation_review,
    print_release_gate_stale_assertion_truth_repair_review,
    print_install_release_segment_blocker_classification_review,
    print_release_archive_and_recovery_gate_boundedness_repair_review,
    print_install_release_segment_evidence_summary_gate_review,
    print_manifest_driven_surface_generation_prep_review,
    print_manifest_review_packet_schema_review,
    print_dashboard_surface_preview_generator_review,
    print_cli_api_surface_preview_generator_review,
    print_smoke_surface_preview_generator_review,
    print_generated_preview_parity_report_review,
    print_low_risk_surface_selection_gate_review,
    print_generated_dashboard_preview_exact_match_gate_review,
    print_generated_cli_api_preview_exact_match_gate_review,
    print_generated_smoke_preview_exact_match_gate_review,
    print_single_surface_generated_parity_closure_review,
    print_multi_surface_selection_gate_review,
    print_multi_surface_dashboard_preview_parity_review,
    print_multi_surface_cli_api_preview_parity_review,
    print_multi_surface_smoke_preview_parity_review,
    print_multi_surface_generated_parity_batch_closure_review,
    print_generated_scaffold_sandbox_output_schema_review,
    print_generated_scaffold_sandbox_artifact_preview_review,
    print_generated_scaffold_hash_ledger_review,
    print_generated_scaffold_sandbox_parity_comparison_review,
    print_generated_scaffold_sandbox_output_closure_review,
    print_generated_scaffold_wrapper_mapping_schema_review,
    print_dashboard_compatibility_wrapper_preview_review,
    print_cli_api_compatibility_wrapper_preview_review,
    print_smoke_compatibility_wrapper_preview_review,
    print_generated_scaffold_wrapper_prep_closure_review,
    print_giant_file_extraction_inventory_review,
    print_self_development_cycle_extraction_map_review,
    print_self_maintenance_builder_text_renderer_extraction_map_review,
    print_dashboard_route_renderer_extraction_map_review,
    print_cli_api_dispatch_extraction_map_review,
    print_smoke_registry_extraction_map_review,
    print_compatibility_wrapper_risk_ledger_review,
    print_extraction_order_proposal_review,
    print_extraction_rollback_evidence_plan_review,
    print_giant_file_compatibility_extraction_prep_closure_review,
    print_extraction_candidate_lock_gate_review,
    print_pre_extraction_function_inventory_review,
    print_generated_preview_review_module_extraction_review,
    print_compatibility_import_wrapper_gate_review,
    print_dashboard_cli_api_parity_after_extraction_review,
    print_smoke_registry_parity_after_extraction_review,
    print_stale_version_and_metadata_post_extraction_gate_review,
    print_rollback_path_verification_review,
    print_extraction_release_evidence_packet_review,
    print_first_compatibility_extraction_closure_review,
    print_second_extraction_candidate_selection_gate_review,
    print_second_pre_extraction_function_inventory_review,
    print_generated_scaffold_review_packet_extraction_review,
    print_second_compatibility_wrapper_gate_review,
    print_second_extraction_surface_parity_gate_review,
    print_smoke_registry_data_model_prep_review,
    print_smoke_registry_static_inventory_review,
    print_smoke_registry_migration_risk_ledger_review,
    print_smoke_registry_rollback_plan_review,
    print_second_extraction_and_smoke_registry_prep_closure_review,
    print_smoke_registry_pilot_selection_gate_review,
    print_smoke_registry_pilot_schema_review,
    print_smoke_registry_pilot_data_table_review,
    print_smoke_registry_pilot_resolver_review,
    print_manual_vs_pilot_smoke_parity_gate_review,
    print_pilot_json_shape_compatibility_gate_review,
    print_pilot_rollback_evidence_gate_review,
    print_smoke_registry_pilot_risk_review,
    print_pilot_expansion_readiness_review,
    print_smoke_registry_data_driven_pilot_closure_review,
    print_smoke_registry_execution_trial_readiness_gate_review,
    print_data_driven_smoke_callable_execution_harness_review,
    print_pilot_smoke_execution_result_packet_review,
    print_manual_vs_data_driven_execution_parity_gate_review,
    print_data_driven_smoke_json_output_preview_review,
    print_data_driven_smoke_timeout_failure_semantics_review,
    print_data_driven_smoke_manual_fallback_proof_review,
    print_data_driven_smoke_execution_risk_review,
    print_data_driven_smoke_expansion_readiness_review,
    print_smoke_registry_data_driven_execution_trial_closure_review,
    print_fallback_migration_readiness_gate_review,
    print_data_driven_first_pilot_dispatch_preview_review,
    print_pilot_fallback_dispatch_trial_review,
    print_pilot_fallback_result_ledger_review,
    print_json_output_stability_gate_review,
    print_fast_install_release_isolation_gate_review,
    print_manual_fallback_removal_resistance_gate_review,
    print_pilot_migration_risk_review,
    print_v1000_milestone_readiness_review,
    print_smoke_registry_fallback_migration_pilot_closure_review,
)
from install_release_blocker_ledger import print_install_release_blocker_ledger_refresh_review
from install_release_timeout_harness import print_install_release_timeout_harness_repair_review
from install_release_timeout_retest import print_install_release_timeout_row_bounded_retest_review
from install_release_fixture_decomposition import print_install_release_fixture_decomposition_plan_review
from install_release_fixture_smoke_split import print_install_release_fixture_smoke_split_pilot_review
from release_archive_fixture_split_expansion import print_release_archive_fixture_split_expansion_review
from supervised_blocker_semantics_repair import print_supervised_blocker_semantics_repair_review
from install_release_segment_cleanliness_gate import print_install_release_segment_cleanliness_gate_review
from post_v1000_defect_closure_phase_zero_boundary import print_post_v1000_defect_closure_phase_zero_boundary_review
from install_release_timeout_parent_replacement import print_install_release_timeout_parent_replacement_pilot_review
from install_release_parent_replacement_expansion import print_install_release_parent_replacement_expansion_review
from remaining_timeout_parent_fixture_selection import print_remaining_timeout_parent_fixture_selection_review
from recovery_closure_fixture_split_smoke import print_recovery_closure_fixture_split_smoke_review
from recovery_closure_parent_replacement_overlay import print_recovery_closure_parent_replacement_overlay_review
from remaining_timeout_parent_fixture_split_expansion import print_remaining_timeout_parent_fixture_split_expansion_review
from decision_archive_ledger_parent_replacement_overlay import print_decision_archive_ledger_parent_replacement_overlay_review
from candidate_handoff_fixture_split_smoke import print_candidate_handoff_fixture_split_smoke_review
from candidate_handoff_parent_replacement_overlay import print_candidate_handoff_parent_replacement_overlay_review
from final_timeout_parent_overlay_closure import print_final_timeout_parent_overlay_closure_review
from dashboard_chat_console import list_dashboard_chat_turns, resolve_dashboard_chat_turn_id
from dashboard import run_dashboard
from api_server import run_api_server
from desktop_shell import print_desktop_status, print_desktop_tray_status, run_desktop_shell
from desktop_setup_helper import (
    print_setup_check,
    print_setup_reports,
    print_saved_setup_report,
    list_setup_reports,
    resolve_setup_report_id,
)
from desktop_onboarding_wizard import (
    print_onboarding_run,
    print_onboarding_runs,
    print_saved_onboarding_run,
    list_onboarding_runs,
    resolve_onboarding_run_id,
)
from inner_loop import run_cycle, run_loop
from memory import load_memories, search_memories
from opinions import load_opinions
from project_manager import (
    add_project,
    add_project_item,
    print_project_status,
    set_active_project,
    get_active_project,
)
from project_indexer import (
    index_project,
    print_project_index_summary,
    print_project_index_search,
)
from self_model import load_self_model


def print_status() -> None:
    self_model = load_self_model()
    memories = load_memories()
    opinions = load_opinions()

    print(f"Name: {self_model.get('name', 'Eidolon')}")
    print(f"Stored memories: {len(memories)}")
    print(f"Opinions: {len(opinions)}")
    print("Active goals:")
    for goal in self_model.get("active_goals", []):
        print(f"- {goal}")
    print()
    print_project_status()


def print_keyword_search(query: str) -> None:
    matches = search_memories(query)
    if not matches:
        print("No keyword matches found.")
        return

    for match in matches:
        print(f"[{match.get('created_at', '?')}] {match.get('type', 'memory')}: {match.get('content', match)}")


def print_semantic_search(query: str) -> None:
    try:
        from vector_memory import search_memory_vectors
    except Exception as error:
        print(f"Semantic search unavailable: {error}")
        return

    matches = search_memory_vectors(query)
    if not matches:
        print("No semantic matches found. Make sure ChromaDB is installed and Ollama is running with nomic-embed-text pulled.")
        return

    for match in matches:
        print(f"[distance={match.get('distance')}] {match.get('content')}")


def rebuild_semantic_memory() -> None:
    try:
        from vector_memory import rebuild_vector_memory
    except Exception as error:
        print(f"Semantic memory rebuild unavailable: {error}")
        return

    memories = load_memories()
    count = rebuild_vector_memory(memories)
    print(f"Rebuilt semantic memory vectors for {count} memories.")


def ai_reviews_enabled() -> bool:
    return bool(get_setting("ai_reviews_enabled", True))


def print_project_tree(path: str = "") -> None:
    print(project_tree_text(relative_path=path))


def print_project_file(path: str) -> None:
    result = read_project_file(path)
    if not result.ok:
        print(f"Could not read {path}: {result.error}")
        return

    print(f"--- {result.path} ---")
    print(result.content)


def print_project_file_search(query: str, path: str = "") -> None:
    matches = search_project_files(query=query, relative_path=path)
    if not matches:
        print("No project file matches found.")
        return

    for match in matches:
        print(f"{match['path']}:{match['line']}: {match['preview']}")


def print_latest_ids() -> None:
    """Prints the newest ids and the aliases that resolve to them."""
    patches = list_patch_proposals()
    proposed_patch = resolve_patch_id("latest-proposed")
    applied_patch = resolve_patch_id("latest-applied")
    rolled_back_patch = resolve_patch_id("latest-rolled-back")
    any_patch = resolve_patch_id("latest")

    runs = list_self_improvement_runs()
    reports = list_test_reports()
    reviews = list_test_reviews()
    maintenance_scans = list_maintenance_scans()
    memory_summaries = list_memory_summaries()
    goals = list_goals()
    session_plans = list_session_plans()
    tasks = list_tasks()
    task_evaluations = list_task_evaluations()
    guided_sessions = list_guided_sessions()
    latest_guided_session = resolve_guided_session_id("latest")
    latest_guided_overview = resolve_guided_session_id("latest-overview")
    latest_guided_dry_run = resolve_guided_session_id("latest-dry-run")
    latest_guided_execute = resolve_guided_session_id("latest-execute")
    latest_guided_evaluate = resolve_guided_session_id("latest-evaluate")
    dev_cycles = list_dev_cycles()
    latest_dev_cycle = resolve_dev_cycle_id("latest")
    latest_dev_review = resolve_dev_cycle_id("latest-review-proposed-patch")
    latest_dev_advance = resolve_dev_cycle_id("latest-advance-task")
    latest_dev_plan = resolve_dev_cycle_id("latest-plan-and-queue")
    dev_loops = list_dev_loops()
    latest_dev_loop = resolve_dev_loop_id("latest")
    latest_dev_loop_approval = resolve_dev_loop_id("latest-approval_required")
    latest_dev_loop_max = resolve_dev_loop_id("latest-max_steps_reached")
    latest_dev_loop_dry = resolve_dev_loop_id("latest-dry_run_complete")
    approvals = list_approvals()
    diagnostic_reports = list_diagnostic_reports()
    latest_diagnostic = diagnostic_reports[0].get("id") if diagnostic_reports else None
    watch_reports = list_watch_reports()
    latest_watch = resolve_watch_report_id("latest")
    latest_watch_attention = resolve_watch_report_id("latest-attention_needed")
    latest_watch_error = resolve_watch_report_id("latest-error")
    latest_watch_healthy = resolve_watch_report_id("latest-healthy")
    notifications = list_notifications(include_dismissed=True)
    latest_notification = resolve_notification_id("latest")
    latest_unread_notification = resolve_notification_id("latest-unread")
    latest_read_notification = resolve_notification_id("latest-read")
    latest_dismissed_notification = resolve_notification_id("latest-dismissed")
    latest_warning_notification = resolve_notification_id("latest-warning")
    latest_critical_notification = resolve_notification_id("latest-critical")
    latest_approval = resolve_approval_id("latest")
    latest_pending_approval = resolve_approval_id("latest-pending")
    latest_approved_approval = resolve_approval_id("latest-approved")
    latest_rejected_approval = resolve_approval_id("latest-rejected")
    latest_task = resolve_task_id("latest")
    latest_open_task = resolve_task_id("latest-open")
    latest_ready_task = resolve_task_id("latest-ready")
    latest_active_task = resolve_task_id("latest-active")
    latest_blocked_task = resolve_task_id("latest-blocked")
    latest_done_task = resolve_task_id("latest-done")
    latest_task_eval = resolve_task_evaluation_id("latest")
    latest_complete_task_eval = resolve_task_evaluation_id("latest-complete")
    latest_block_task_eval = resolve_task_evaluation_id("latest-block")
    latest_retry_task_eval = resolve_task_evaluation_id("latest-retry")
    latest_goal = resolve_goal_id("latest")
    latest_open_goal = resolve_goal_id("latest-open")
    latest_active_goal = resolve_goal_id("latest-active")
    latest_blocked_goal = resolve_goal_id("latest-blocked")
    latest_completed_goal = resolve_goal_id("latest-completed")
    chat_actions = list_chat_actions(include_closed=True)
    dashboard_chat_turns = list_dashboard_chat_turns()
    latest_dashboard_chat = resolve_dashboard_chat_turn_id("latest")
    latest_chat_action = resolve_chat_action_id("latest")
    latest_proposed_chat_action = resolve_chat_action_id("latest-proposed")
    latest_executed_chat_action = resolve_chat_action_id("latest-executed")
    latest_approval_chat_action = resolve_chat_action_id("latest-approval")
    latest_blocked_chat_action = resolve_chat_action_id("latest-blocked")
    setup_reports = list_setup_reports()
    latest_setup_report = resolve_setup_report_id("latest")
    latest_ready_setup_report = resolve_setup_report_id("latest-ready")
    latest_attention_setup_report = resolve_setup_report_id("latest-attention_needed")
    latest_critical_setup_report = resolve_setup_report_id("latest-critical")
    onboarding_runs = list_onboarding_runs()
    latest_onboarding = resolve_onboarding_run_id("latest")
    latest_ready_onboarding = resolve_onboarding_run_id("latest-ready")
    latest_action_onboarding = resolve_onboarding_run_id("latest-needs_action")
    latest_blocked_onboarding = resolve_onboarding_run_id("latest-blocked")

    print("# Latest shortcuts")
    print()
    print("Patch aliases:")
    print(f"  latest: {any_patch or '[none]'}")
    print(f"  latest-proposed: {proposed_patch or '[none]'}")
    print(f"  latest-applied: {applied_patch or '[none]'}")
    print(f"  latest-rolled-back: {rolled_back_patch or '[none]'}")
    print()
    print("Self-improvement aliases:")
    print(f"  latest run: {(runs[0].get('id') if runs else '[none]')}")
    print(f"  latest self-improvement patch: {latest_self_improvement_patch_id() or '[none]'}")
    print()
    print("Test aliases:")
    print(f"  latest report: {(reports[0].get('id') if reports else '[none]')}")
    print(f"  latest review: {(reviews[0].get('id') if reviews else '[none]')}")
    print()
    print("Maintenance aliases:")
    print(f"  latest maintenance scan: {(maintenance_scans[0].get('id') if maintenance_scans else '[none]')}")
    print()
    print("Memory aliases:")
    print(f"  latest memory summary: {(memory_summaries[0].get('id') if memory_summaries else '[none]')}")
    print()
    print("Session aliases:")
    print(f"  latest session plan: {(session_plans[0].get('id') if session_plans else '[none]')}")
    print()
    print("Task aliases:")
    print(f"  latest task: {latest_task or '[none]'}")
    print(f"  latest-open task: {latest_open_task or '[none]'}")
    print(f"  latest-ready task: {latest_ready_task or '[none]'}")
    print(f"  latest-active task: {latest_active_task or '[none]'}")
    print(f"  latest-blocked task: {latest_blocked_task or '[none]'}")
    print(f"  latest-done task: {latest_done_task or '[none]'}")
    print()
    print("Task evaluation aliases:")
    print(f"  latest task evaluation: {latest_task_eval or '[none]'}")
    print(f"  latest-complete task evaluation: {latest_complete_task_eval or '[none]'}")
    print(f"  latest-block task evaluation: {latest_block_task_eval or '[none]'}")
    print(f"  latest-retry task evaluation: {latest_retry_task_eval or '[none]'}")
    print()
    print("Guided work session aliases:")
    print(f"  latest guided session: {latest_guided_session or '[none]'}")
    print(f"  latest-overview guided session: {latest_guided_overview or '[none]'}")
    print(f"  latest-dry-run guided session: {latest_guided_dry_run or '[none]'}")
    print(f"  latest-execute guided session: {latest_guided_execute or '[none]'}")
    print(f"  latest-evaluate guided session: {latest_guided_evaluate or '[none]'}")
    print()
    print("Dev cycle aliases:")
    print(f"  latest dev cycle: {latest_dev_cycle or '[none]'}")
    print(f"  latest-review-proposed-patch dev cycle: {latest_dev_review or '[none]'}")
    print(f"  latest-advance-task dev cycle: {latest_dev_advance or '[none]'}")
    print(f"  latest-plan-and-queue dev cycle: {latest_dev_plan or '[none]'}")
    print()
    print("Dev loop aliases:")
    print(f"  latest dev loop: {latest_dev_loop or '[none]'}")
    print(f"  latest-approval_required dev loop: {latest_dev_loop_approval or '[none]'}")
    print(f"  latest-max_steps_reached dev loop: {latest_dev_loop_max or '[none]'}")
    print(f"  latest-dry_run_complete dev loop: {latest_dev_loop_dry or '[none]'}")
    print()
    print("Diagnostic aliases:")
    print(f"  latest diagnostic report: {latest_diagnostic or '[none]'}")
    print()
    print("Watch report aliases:")
    print(f"  latest watch report: {latest_watch or '[none]'}")
    print(f"  latest-attention_needed watch report: {latest_watch_attention or '[none]'}")
    print(f"  latest-error watch report: {latest_watch_error or '[none]'}")
    print(f"  latest-healthy watch report: {latest_watch_healthy or '[none]'}")
    print()
    print("Notification aliases:")
    print(f"  latest notification: {latest_notification or '[none]'}")
    print(f"  latest-unread notification: {latest_unread_notification or '[none]'}")
    print(f"  latest-read notification: {latest_read_notification or '[none]'}")
    print(f"  latest-dismissed notification: {latest_dismissed_notification or '[none]'}")
    print(f"  latest-warning notification: {latest_warning_notification or '[none]'}")
    print(f"  latest-critical notification: {latest_critical_notification or '[none]'}")
    print()
    print("Approval aliases:")
    print(f"  latest approval: {latest_approval or '[none]'}")
    print(f"  latest-pending approval: {latest_pending_approval or '[none]'}")
    print(f"  latest-approved approval: {latest_approved_approval or '[none]'}")
    print(f"  latest-rejected approval: {latest_rejected_approval or '[none]'}")
    print()
    print("Dashboard chat aliases:")
    print(f"  latest dashboard chat: {latest_dashboard_chat or '[none]'}")
    print()
    print("Chat action aliases:")
    print(f"  latest chat action: {latest_chat_action or '[none]'}")
    print(f"  latest-proposed chat action: {latest_proposed_chat_action or '[none]'}")
    print(f"  latest-executed chat action: {latest_executed_chat_action or '[none]'}")
    print(f"  latest-approval chat action: {latest_approval_chat_action or '[none]'}")
    print(f"  latest-blocked chat action: {latest_blocked_chat_action or '[none]'}")
    print()
    print("Setup aliases:")
    print(f"  latest setup report: {latest_setup_report or '[none]'}")
    print(f"  latest-ready setup report: {latest_ready_setup_report or '[none]'}")
    print(f"  latest-attention_needed setup report: {latest_attention_setup_report or '[none]'}")
    print(f"  latest-critical setup report: {latest_critical_setup_report or '[none]'}")
    print()
    print("Onboarding aliases:")
    print(f"  latest onboarding run: {latest_onboarding or '[none]'}")
    print(f"  latest-ready onboarding run: {latest_ready_onboarding or '[none]'}")
    print(f"  latest-needs_action onboarding run: {latest_action_onboarding or '[none]'}")
    print(f"  latest-blocked onboarding run: {latest_blocked_onboarding or '[none]'}")
    print()
    print("Goal aliases:")
    print(f"  latest goal: {latest_goal or '[none]'}")
    print(f"  latest-open goal: {latest_open_goal or '[none]'}")
    print(f"  latest-active goal: {latest_active_goal or '[none]'}")
    print(f"  latest-blocked goal: {latest_blocked_goal or '[none]'}")
    print(f"  latest-completed goal: {latest_completed_goal or '[none]'}")
    print()
    print("Common no-copy commands:")
    print("  python conscious_agent/main.py --chat-action \"run diagnostics\"")
    print("  python conscious_agent/main.py --show-chat-action latest")
    print("  python conscious_agent/main.py --execute-chat-action latest --dry-run")
    print("  python conscious_agent/main.py --show-patch latest")
    print("  python conscious_agent/main.py --apply-patch latest --dry-run")
    print("  python conscious_agent/main.py --rollback-patch latest --dry-run")
    print("  python conscious_agent/main.py --show-self-improvement latest")
    print("  python conscious_agent/main.py --self-improve-apply latest --dry-run")
    print("  python conscious_agent/main.py --show-test-report latest")
    print("  python conscious_agent/main.py --review-test-report latest")
    print("  python conscious_agent/main.py --show-test-review latest")
    print("  python conscious_agent/main.py --show-maintenance-scan latest")
    print("  python conscious_agent/main.py --show-memory-summary latest")
    print("  python conscious_agent/main.py --show-session-plan latest")
    print("  python conscious_agent/main.py --queue-from-session latest")
    print("  python conscious_agent/main.py --next-task")
    print("  python conscious_agent/main.py --show-task latest-ready")
    print("  python conscious_agent/main.py --start-task latest-ready")
    print("  python conscious_agent/main.py --complete-task latest-active")
    print("  python conscious_agent/main.py --evaluate-task latest")
    print("  python conscious_agent/main.py --show-task-evaluation latest")
    print("  python conscious_agent/main.py --apply-task-evaluation latest")
    print("  python conscious_agent/main.py --guided-work-session latest-ready")
    print("  python conscious_agent/main.py --advance-work-session latest-ready")
    print("  python conscious_agent/main.py --show-guided-session latest")
    print("  python conscious_agent/main.py --dev-cycle")
    print("  python conscious_agent/main.py --advance-dev-cycle --dry-run")
    print("  python conscious_agent/main.py --show-dev-cycle latest")
    print("  python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop")
    print("  python conscious_agent/main.py --dev-loop")
    print("  python conscious_agent/main.py --show-dev-loop latest")
    print("  python conscious_agent/main.py --settings")
    print("  python conscious_agent/main.py --settings-health")
    print("  python conscious_agent/main.py --work-cycle --dry-run")
    print("  python conscious_agent/main.py --work-cycle --work-cycle-steps 3")
    print("  python conscious_agent/main.py --show-work-cycle latest")
    print("  python conscious_agent/main.py --diagnostics")
    print("  python conscious_agent/main.py --dashboard")
    print("  python conscious_agent/main.py --diagnostics --diagnostics-full")
    print("  python conscious_agent/main.py --show-diagnostic-report latest")
    print("  python conscious_agent/main.py --watch-once --no-ai-watch")
    print("  python conscious_agent/main.py --watch-loop --watch-cycles 3 --no-ai-watch")
    print("  python conscious_agent/main.py --show-watch-report latest")
    print("  python conscious_agent/main.py --notifications")
    print("  python conscious_agent/main.py --show-notification latest-unread")
    print("  python conscious_agent/main.py --mark-notification-read latest-unread")
    print("  python conscious_agent/main.py --dismiss-notification latest-unread")
    print("  python conscious_agent/main.py --approval-inbox")
    print("  python conscious_agent/main.py --show-approval latest-pending")
    print("  python conscious_agent/main.py --approve latest-pending --dry-run")
    print("  python conscious_agent/main.py --reject latest-pending --approval-note \"Reason here\"")
    print("  python conscious_agent/main.py --show-goal latest-open")
    print("  python conscious_agent/main.py --complete-goal latest-active")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eidolon autonomous inner-thought prototype")
    parser.add_argument("--once", action="store_true", help="Run one inner-thought cycle")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--search", type=str, help="Search memories by keyword")
    parser.add_argument("--semantic-search", type=str, help="Search memories by meaning")
    parser.add_argument("--rebuild-semantic-memory", action="store_true", help="Vectorize existing JSON memories")
    parser.add_argument("--chat", action="store_true", help="Start terminal chat mode")
    parser.add_argument(
        "--work-queue",
        nargs=argparse.REMAINDER,
        help="Legacy alias: manage task-backed tasks through the old work-queue CLI.",
    )
    parser.add_argument(
        "--task-work",
        nargs=argparse.REMAINDER,
        help="Manage canonical task-backed tasks through the Tasks / Work CLI.",
    )
    parser.add_argument("--execute-task-work", action="store_true", help="Execute the next safe planned/active task through the task work executor")
    parser.add_argument("--execute-task-work-id", type=str, help="Execute one specific task through the task work executor")
    parser.add_argument("--execute-task-work-project", type=str, default="", help="Optional project filter for --execute-task-work")
    parser.add_argument("--execute-work", action="store_true", help="Legacy alias: execute the next safe task-backed task")
    parser.add_argument("--execute-work-id", type=str, help="Legacy alias: execute one specific task-backed task by id")
    parser.add_argument("--execute-work-project", type=str, default="", help="Legacy alias project filter for --execute-work")
    parser.add_argument("--approve-task-work-execution", action="store_true", help="Allow approval-required task work to execute; use carefully")
    parser.add_argument("--approve-work-execution", action="store_true", help="Legacy alias: allow approval-required task-backed tasks to execute; use carefully")
    parser.add_argument("--no-ai-task-work-executor", action="store_true", help="Disable local AI during task work execution")
    parser.add_argument("--no-ai-work-executor", action="store_true", help="Legacy alias: disable local AI during task work execution")
    parser.add_argument("--task-work-executor-full", action="store_true", help="Show full task work executor output")
    parser.add_argument("--work-executor-full", action="store_true", help="Legacy alias: show full task work executor output")
    parser.add_argument("--request-task-approval", type=str, help="Create an approval request for executing one approval-gated task")
    parser.add_argument("--request-next-task-approval", action="store_true", help="Create an approval request for the next approval-gated task")
    parser.add_argument("--task-approval-project", type=str, default="", help="Optional project filter for --request-next-task-approval")
    parser.add_argument("--task-approval-reason", type=str, default="", help="Reason to store on a task approval request")
    parser.add_argument("--force-task-approval", action="store_true", help="Create a task approval even if the task is not currently risk-gated")
    parser.add_argument("--show-task-approvals", type=str, help="Show approval requests linked to a task")
    parser.add_argument("--task-approval-full", action="store_true", help="Show full task approval request details")
    parser.add_argument("--task-recovery-summary", action="store_true", help="Show recoverable blocked/failed task summary")
    parser.add_argument("--list-task-recoveries", action="store_true", help="List recoverable blocked/failed tasks and suggested recovery actions")
    parser.add_argument("--show-task-recovery", type=str, help="Show recovery plan for a task by id or alias")
    parser.add_argument("--mark-task-ready-for-retry", type=str, help="Clear failed/blocked work markers and mark a task planned for retry")
    parser.add_argument("--retry-task-work", type=str, help="Retry a recoverable task through the task work executor; use --dry-run first")
    parser.add_argument("--task-recovery-project", type=str, default="", help="Optional project filter for task recovery listing")
    parser.add_argument("--task-recovery-note", type=str, default="", help="Optional note for --mark-task-ready-for-retry")
    parser.add_argument("--task-recovery-full", action="store_true", help="Show full task recovery details")
    parser.add_argument("--queue-patch", nargs=2, metavar=("FILE", "REQUEST"), help="Legacy alias: create a task-backed patch-generation item for a file")
    parser.add_argument("--queue-task-patch", nargs=2, metavar=("FILE", "REQUEST"), help="Create a task-backed item that will generate a patch proposal for a file")
    parser.add_argument("--queue-patch-project", type=str, default="eidolon", help="Project id for --queue-patch / --queue-task-patch")
    parser.add_argument("--queue-patch-priority", type=int, default=7, help="Priority 1-10 for --queue-patch / --queue-task-patch")
    parser.add_argument("--queue-patch-risk", type=str, default="low", choices=["low", "medium", "high"], help="Risk level for --queue-patch / --queue-task-patch")
    parser.add_argument("--queue-patch-requires-approval", action="store_true", help="Force the queued patch task to require approval")
    parser.add_argument("--suggest-patch-for-work", type=str, help="Legacy alias: generate and link a patch proposal from a task-backed task")
    parser.add_argument("--suggest-patch-for-task", type=str, help="Generate and link a patch proposal from a task")
    parser.add_argument("--create-patch-followups", type=str, help="Legacy alias: create review/apply/test follow-up tasks for a patch id")
    parser.add_argument("--create-patch-task-followups", type=str, help="Create review/apply/test follow-up tasks for a patch id")
    parser.add_argument("--patch-followup-project", type=str, default="eidolon", help="Project id for --create-patch-followups")
    parser.add_argument("--work-cycle", action="store_true", help="Run one supervised autonomous work cycle over task-backed tasks")
    parser.add_argument("--work-cycle-project", type=str, default="eidolon", help="Project id for --work-cycle")
    parser.add_argument("--work-cycle-steps", type=int, default=1, help="Maximum tasks to advance during --work-cycle, capped at 10")
    parser.add_argument("--approve-work-cycle-actions", action="store_true", help="Allow approval-required tasks during --work-cycle; use carefully")
    parser.add_argument("--no-ai-work-cycle", action="store_true", help="Disable local AI during --work-cycle")
    parser.add_argument("--no-work-cycle-seed", action="store_true", help="Do not create seed tasks when the queue is empty")
    parser.add_argument("--no-work-cycle-followups", action="store_true", help="Do not auto-create review/apply/test follow-ups for proposed patches")
    parser.add_argument("--no-work-cycle-approval-requests", action="store_true", help="Do not auto-create approval requests for approval-required tasks during --work-cycle")
    parser.add_argument("--work-cycle-auto-retry-recovery", action="store_true", help="Allow --work-cycle to mark recovery-needed tasks ready for retry; default only reports recovery plans")
    parser.add_argument("--work-cycle-full", action="store_true", help="Show full supervised work cycle details")
    parser.add_argument("--list-work-cycles", action="store_true", help="List saved supervised work cycle records")
    parser.add_argument("--show-work-cycle", nargs="?", const="latest", help="Show a saved supervised work cycle by id or alias")
    parser.add_argument("--stable-loop-preflight", action="store_true", help="Preview stable supervised loop health and next lifecycle decision")
    parser.add_argument("--stable-loop", action="store_true", help="Run the v6.9 stable supervised loop; preview-only unless --stable-loop-live is used")
    parser.add_argument("--stable-loop-project", type=str, default="eidolon", help="Project id for --stable-loop")
    parser.add_argument("--stable-loop-steps", type=int, default=1, help="Maximum stable loop steps, capped at 5")
    parser.add_argument("--stable-loop-live", action="store_true", help="Allow the stable loop to run a live cycle after its dry-run preview")
    parser.add_argument("--approve-stable-loop-actions", action="store_true", help="Allow approval-required task work during a live stable loop; use carefully")
    parser.add_argument("--no-ai-stable-loop", action="store_true", help="Disable local AI during stable loop preview/live cycle")
    parser.add_argument("--no-stable-loop-seed", action="store_true", help="Do not create seed tasks when stable loop finds an empty queue")
    parser.add_argument("--no-stable-loop-followups", action="store_true", help="Do not auto-create patch follow-up tasks during stable loop")
    parser.add_argument("--no-stable-loop-approval-requests", action="store_true", help="Do not auto-create task approval requests during stable loop")
    parser.add_argument("--stable-loop-auto-retry-recovery", action="store_true", help="Allow live stable loop to mark recovery-needed tasks ready for retry")
    parser.add_argument("--stable-loop-full", action="store_true", help="Show full stable loop details")
    parser.add_argument("--stable-loop-guardrails", action="store_true", help="Show closure-aware guardrails for stable-loop live advancement")
    parser.add_argument("--stable-loop-bypass-closure-guardrails", action="store_true", help="Explicitly bypass unresolved follow-up guardrails for a live stable-loop run")
    parser.add_argument("--stabilization-checkpoint", action="store_true", help="Run the v8.0 read-only stabilization checkpoint across CLI/API/dashboard/task/stable-loop surfaces")
    parser.add_argument("--stabilization-full", action="store_true", help="Include every stabilization checkpoint item and raw report details")
    parser.add_argument("--stabilization-json", action="store_true", help="Print the stabilization checkpoint report as JSON")
    parser.add_argument("--doctor", action="store_true", help="Run the v7.2 one-command doctor report")
    parser.add_argument("--doctor-full", action="store_true", help="Include raw JSON/details for doctor and operational readiness reports")
    parser.add_argument("--readiness-json", action="store_true", help="Print new operational readiness reports as JSON")
    parser.add_argument("--repair-suggestions", action="store_true", help="Show v7.3 self-repair suggestions based on current diagnostics")
    parser.add_argument("--patch-integrity", action="store_true", help="Show v7.4 patch metadata and rollback integrity report")
    parser.add_argument("--project-snapshot", action="store_true", help="Show v7.5 project state snapshot")
    parser.add_argument("--task-review", action="store_true", help="Show v7.6 task queue risk/lifecycle review")
    parser.add_argument("--recovery-drill", action="store_true", help="Run v7.7 read-only recovery drill scenarios")
    parser.add_argument("--stable-loop-confidence", action="store_true", help="Show v7.8 stable-loop confidence score")
    parser.add_argument("--hardening-report", action="store_true", help="Show v7.9 pre-v8 hardening report")
    parser.add_argument("--controlled-self-build", action="store_true", help="Run v8.0 controlled self-build preview unless live approval flags are supplied")
    parser.add_argument("--controlled-self-build-live", action="store_true", help="Allow controlled self-build/supervised loop commands to attempt live work after doctor/guardrail gates")
    parser.add_argument("--approve-controlled-self-build", action="store_true", help="Explicit operator approval required for live controlled self-build, apply, or rollback actions")
    parser.add_argument("--controlled-self-build-steps", type=int, default=1, help="Bounded step count for controlled self-build, capped internally")
    parser.add_argument("--select-task", action="store_true", help="Run v8.1 controlled self-build task selection")
    parser.add_argument("--plan-patch", action="store_true", help="Run v8.2 controlled patch planner and save data/patch_workspace/current_plan.json")
    parser.add_argument("--patch-workspace-status", action="store_true", help="Show v8.3 controlled patch workspace status")
    parser.add_argument("--stage-patch", action="store_true", help="Run v8.3 patch staging into data/patch_workspace without touching source files")
    parser.add_argument("--preview-diff", action="store_true", help="Run v8.4 staged file diff preview")
    parser.add_argument("--apply-staged-patch", action="store_true", help="Run v8.5 apply staged patch; writes only with --approve-controlled-self-build")
    parser.add_argument("--verify-latest-patch", action="store_true", help="Run v8.6 verification for the latest controlled patch/apply report")
    parser.add_argument("--rollback-latest-patch", action="store_true", help="Run v8.7 rollback for the latest controlled patch; writes only with --approve-controlled-self-build")
    parser.add_argument("--readme-gate", action="store_true", help="Run v8.8 README enforcement gate")
    parser.add_argument("--controlled-self-build-cycle", action="store_true", help="Run v8.9 full controlled build cycle; preview by default")
    parser.add_argument("--supervised-dev-loop", action="store_true", help="Run v9.0 one-cycle supervised autonomous development loop; preview by default")
    parser.add_argument("--codebase-map", action="store_true", help="Run v9.1 codebase map")
    parser.add_argument("--task-dependencies", action="store_true", help="Run v9.2 dependency-aware task planning")
    parser.add_argument("--test-plan", action="store_true", help="Run v9.3 test planner")
    parser.add_argument("--patch-risk", action="store_true", help="Run v9.4 patch risk analyzer")
    parser.add_argument("--patch-review", action="store_true", help="Run v9.5 patch review report")
    parser.add_argument("--project-memory-index", action="store_true", help="Run v9.7 project memory index")
    parser.add_argument("--workspace-status", action="store_true", help="Run v9.8 multi-project workspace status")
    parser.add_argument("--cross-project-task-review", action="store_true", help="Run v9.9 cross-project task review")
    parser.add_argument("--asymmetric-dev-loop", action="store_true", help="Run v10.0 asymmetric multi-project dev loop preview")
    parser.add_argument("--project-registry", action="store_true", help="Run v10.1 workspace project registry report")
    parser.add_argument("--register-project", help="Register or update a workspace project by name")
    parser.add_argument("--workspace-project-id", help="Workspace project id for registration/context commands")
    parser.add_argument("--workspace-project-root", help="Workspace project root; use . to derive from ROOT_DIR")
    parser.add_argument("--workspace-project-version", default="unknown", help="Workspace project version metadata")
    parser.add_argument("--workspace-project-language", default="unknown", help="Workspace project language metadata")
    parser.add_argument("--workspace-project-framework", default="unknown", help="Workspace project framework/type metadata")
    parser.add_argument("--workspace-project-readme", default="README_NEXT_STEPS.md", help="Workspace project README path")
    parser.add_argument("--workspace-project-test-command", action="append", default=[], help="Project-specific test command; may be provided multiple times")
    parser.add_argument("--workspace-command-profile", default="default_python", help="Project safe command profile id")
    parser.add_argument("--set-active-workspace-project", help="Set the active workspace project id")
    parser.add_argument("--project-health", action="store_true", help="Run v10.2 per-project health check")
    parser.add_argument("--project-health-all", action="store_true", help="Run v10.2 health check across all registered projects")
    parser.add_argument("--command-profiles", action="store_true", help="Run v10.3 project command profile report and seed defaults")
    parser.add_argument("--workspace-dependency-map", action="store_true", help="Run v10.4 cross-project dependency map")
    parser.add_argument("--workspace-task-inbox", action="store_true", help="Run v10.5 multi-project task inbox")
    parser.add_argument("--switch-project", help="Safely switch active workspace project, blocked by dirty patch workspace unless forced")
    parser.add_argument("--force-switch-project", action="store_true", help="Force workspace project switch despite patch workspace state")
    parser.add_argument("--project-context", action="store_true", help="Run v10.7 project context bundle")
    parser.add_argument("--workspace-timeline", action="store_true", help="Run v10.8 workspace timeline")
    parser.add_argument("--workspace-dev-loop", action="store_true", help="Run v11.0 workspace-orchestrated development loop preview")
    parser.add_argument("--workspace-registry-audit", action="store_true", help="Run v11.1 workspace registry persistence audit")
    parser.add_argument("--workspace-repair-suggestions", action="store_true", help="Run v11.2 workspace repair suggestions")
    parser.add_argument("--project-registration-wizard", nargs="?", const="Workspace Project", help="Run v11.3 project registration wizard preview")
    parser.add_argument("--project-boundary-check", action="store_true", help="Run v11.4 project boundary guard")
    parser.add_argument("--workspace-patch-plan", action="store_true", help="Run v11.5 workspace patch plan")
    parser.add_argument("--workspace-preview-diff", action="store_true", help="Run v11.6 workspace diff preview")
    parser.add_argument("--workspace-apply", action="store_true", help="Run v11.7/v11.8 workspace apply; dry-run unless --approve-controlled-self-build is provided")
    parser.add_argument("--workspace-verify-latest", action="store_true", help="Run v11.9 workspace verification pipeline")
    parser.add_argument("--guarded-workspace-dev-loop", action="store_true", help="Run v12.0 guarded workspace development loop; dry-run unless approved")
    parser.add_argument("--patch-draft-request", action="store_true", help="Run v12.1 patch draft request format and save data/patch_drafts/draft_request.json")
    parser.add_argument("--draft-patch", action="store_true", help="Run v12.2 AI patch drafting interface without applying source edits")
    parser.add_argument("--patch-draft-status", action="store_true", help="Run v12.3 patch draft workspace status")
    parser.add_argument("--patch-review-notes", action="store_true", help="Run v12.4 human patch review notes")
    parser.add_argument("--patch-review-note", help="Review note text to attach to the current patch draft")
    parser.add_argument("--draft-diff", action="store_true", help="Run v12.5 draft diff generator")
    parser.add_argument("--draft-test-impact", action="store_true", help="Run v12.6 draft test impact planner")
    parser.add_argument("--approve-draft", action="store_true", help="Run v12.7 approval gate and approve the current draft for one apply if gates pass")
    parser.add_argument("--reject-draft", action="store_true", help="Reject the current patch draft")
    parser.add_argument("--apply-approved-draft", action="store_true", help="Run v12.8 approved draft apply; use --dry-run to preview without writing")
    parser.add_argument("--rollback-approved-draft", action="store_true", help="Run v12.9 approved draft rollback; writes only with --approve-controlled-self-build")
    parser.add_argument("--reopen-draft", action="store_true", help="Run v12.9 reopen draft and clear approval state")
    parser.add_argument("--human-approved-patch-loop", action="store_true", help="Run v13.0 human-approved autonomous patch loop; stops unless a draft is already approved")
    parser.add_argument("--draft-quality", action="store_true", help="Run v13.1 draft quality scoring")
    parser.add_argument("--draft-file-targets", action="store_true", help="Run v13.2 draft file target resolver")
    parser.add_argument("--draft-intent-blocks", action="store_true", help="Run v13.3 draft change intent blocks")
    parser.add_argument("--draft-conflicts", action="store_true", help="Run v13.4 draft conflict detector")
    parser.add_argument("--draft-verification-bundle", action="store_true", help="Run v13.7 draft verification bundle")
    parser.add_argument("--draft-review-checklist", action="store_true", help="Run v13.8 human review checklist")
    parser.add_argument("--approved-draft-execution-report", action="store_true", help="Run v13.9 approved draft execution report")
    parser.add_argument("--review-centered-patch-loop", action="store_true", help="Run v14.0 review-centered patch loop; stops unless approval exists and apply is approved")
    parser.add_argument("--code-edit-proposal", action="store_true", help="Run v14.1 real code edit proposal format")
    parser.add_argument("--safe-rewrite-preview", action="store_true", help="Run v14.2 safe file rewrite preview with hash checks")
    parser.add_argument("--generate-code-patch", action="store_true", help="Run v14.3 generated code patch artifact builder")
    parser.add_argument("--test-suggestions", action="store_true", help="Run v14.4 unit/manual test suggestion generator")
    parser.add_argument("--inline-review-note", action="store_true", help="Run v14.6 inline patch review note capture")
    parser.add_argument("--inline-review-file", help="File path for --inline-review-note")
    parser.add_argument("--inline-review-intent", help="Intent block id/title for --inline-review-note")
    parser.add_argument("--apply-approved-code-patch", action="store_true", help="Run v14.7 approved generated code patch apply; dry-run unless approved")
    parser.add_argument("--prepare-release-package", action="store_true", help="Run v14.8 release package metadata preparation")
    parser.add_argument("--release-package-name", default=None, help="Package name for release preparation metadata; defaults to current settings version")
    parser.add_argument("--release-readiness", action="store_true", help="Run v14.9 release readiness gate")
    parser.add_argument("--human-approved-release-loop", action="store_true", help="Run v15.0 human-approved release loop; stops after one approval/apply decision")
    parser.add_argument("--code-patch-status", action="store_true", help="Run v15.1 generated-code patch workspace status")
    parser.add_argument("--symbol-scan", action="store_true", help="Run v15.2 symbol-aware target file scanner")
    parser.add_argument("--rewrite-plan", action="store_true", help="Run v15.3 targeted rewrite planner")
    parser.add_argument("--rewrite-conflicts", action="store_true", help="Run v15.4 rewrite conflict detector")
    parser.add_argument("--code-patch-diff-bundle", action="store_true", help="Run v15.5 generated code patch diff bundle")
    parser.add_argument("--apply-code-patch-transaction", action="store_true", help="Run v15.6 guarded code patch apply transaction; dry-run unless approved")
    parser.add_argument("--semantic-checks", action="store_true", help="Run v15.7 post-apply semantic checks")
    parser.add_argument("--release-artifact", action="store_true", help="Run v15.8 release artifact manifest builder")
    parser.add_argument("--release-audit-trail", action="store_true", help="Run v15.9 release audit trail")
    parser.add_argument("--generated-code-release-loop", action="store_true", help="Run v16.0 generated code patch release loop; one bounded dry-run/apply then stop")
    parser.add_argument("--task-to-code-patch", action="store_true", help="Run v16.1 task-to-code patch translator")
    parser.add_argument("--code-context", action="store_true", help="Run v16.2 focused code context extractor")
    parser.add_argument("--patch-prompt", action="store_true", help="Run v16.3 structured patch prompt builder")
    parser.add_argument("--parse-generated-edits", action="store_true", help="Run v16.4 generated edit parser")
    parser.add_argument("--edit-consistency", action="store_true", help="Run v16.5 multi-edit consistency checker")
    parser.add_argument("--ai-code-patch-dry-run", action="store_true", help="Run v16.6 AI-assisted patch dry-run without source writes")
    parser.add_argument("--patch-failure-analysis", action="store_true", help="Run v16.8 generated patch failure classifier")
    parser.add_argument("--patch-learning-notes", action="store_true", help="Run v16.9 generated patch learning notes")
    parser.add_argument("--ai-assisted-code-patch-loop", action="store_true", help="Run v17.0 AI-assisted human-approved code patch loop; bounded and approval-gated")
    parser.add_argument("--refine-patch-objective", action="store_true", help="Run v17.1 patch objective refinement")
    parser.add_argument("--rank-code-context", action="store_true", help="Run v17.2 code context ranking")
    parser.add_argument("--patch-safety-envelope", action="store_true", help="Run v17.3 prompt safety envelope")
    parser.add_argument("--validate-generated-patch", action="store_true", help="Run v17.4 generated patch validator")
    parser.add_argument("--patch-simulation", action="store_true", help="Run v17.5 patch simulation without source writes")
    parser.add_argument("--test-stub-plan", action="store_true", help="Run v17.6 test stub planner")
    parser.add_argument("--patch-review-score", action="store_true", help="Run v17.7 patch review scoring")
    parser.add_argument("--patch-recovery-plan", action="store_true", help="Run v17.9 patch failure recovery plan")
    parser.add_argument("--validated-ai-code-patch-loop", action="store_true", help="Run v18.0 validated AI code patch loop; validates, simulates, scores, and stops for approval")
    parser.add_argument("--ai-patch-review-bundle", action="store_true", help="Run v18.1 AI patch review bundle")
    parser.add_argument("--ai-patch-review-integrity", action="store_true", help="Run v18.2 review bundle integrity check")
    parser.add_argument("--approval-ready", action="store_true", help="Run v18.3 approval-ready gate")
    parser.add_argument("--approval-ledger", action="store_true", help="Run v18.5 human approval ledger")
    parser.add_argument("--apply-validated-ai-patch", action="store_true", help="Run v18.6 validated AI patch apply; dry-run unless approved")
    parser.add_argument("--post-apply-review", action="store_true", help="Run v18.7 post-apply review comparison")
    parser.add_argument("--package-build-plan", action="store_true", help="Run v18.9 package build plan")
    parser.add_argument("--approval-to-release-loop", action="store_true", help="Run v19.0 approval-to-release loop")
    parser.add_argument("--bind-validated-approval", action="store_true", help="Bind the current approved draft to the saved validated AI patch manifest before real validated apply")
    parser.add_argument("--refresh-ai-patch-review-bundle", action="store_true", help="Refresh and save the authoritative validated AI patch review bundle/manifest")
    parser.add_argument("--release-manifest-integrity", action="store_true", help="Run v19.1 release manifest integrity check")
    parser.add_argument("--package-inventory", action="store_true", help="Run v19.2 package file inventory")
    parser.add_argument("--package-checksums", action="store_true", help="Run v19.3 package checksum builder")
    parser.add_argument("--release-notes", action="store_true", help="Run v19.4 release notes generator")
    parser.add_argument("--release-handoff-report", action="store_true", help="Run v19.5 release handoff report")
    parser.add_argument("--build-release-zip", action="store_true", help="Run v19.6 guarded release zip builder; dry-run unless --approve-controlled-self-build is provided")
    parser.add_argument("--verify-release-unzip", action="store_true", help="Run v19.7 install/unzip verification for the latest release zip")
    parser.add_argument("--release-pipeline-audit", action="store_true", help="Run v19.9 release pipeline audit")
    parser.add_argument("--verified-release-package-loop", action="store_true", help="Run v22.0 verified installable release package loop")
    parser.add_argument("--release-profiles", action="store_true", help="Run v20.1 release profile report")
    parser.add_argument("--package-privacy-scan", action="store_true", help="Run v20.2 package privacy scanner")
    parser.add_argument("--portable-metadata-check", action="store_true", help="Run v20.3 portable workspace metadata check")
    parser.add_argument("--first-run-check", action="store_true", help="Run v20.4 first-run setup check")
    parser.add_argument("--dependency-advisor", action="store_true", help="Run v20.5 dependency install advisor")
    parser.add_argument("--upgrade-notes", action="store_true", help="Run v20.6 release upgrade notes")
    parser.add_argument("--runtime-migration-check", action="store_true", help="Run v20.7 runtime data migration guard")
    parser.add_argument("--release-install-verification", action="store_true", help="Run v20.8 release install verification")
    parser.add_argument("--verified-installable-release-loop", action="store_true", help="Run v22.0 verified installable release loop")
    parser.add_argument("--smoke-runtime-hardening", action="store_true", help="Run v21.1 smoke runtime hardening report")
    parser.add_argument("--external-zip-install-verification", action="store_true", help="Run v21.2 external release zip install verification")
    parser.add_argument("--deterministic-release-manifest", action="store_true", help="Run v21.3 deterministic release manifest")
    parser.add_argument("--update-dry-run-plan", action="store_true", help="Run v21.4 update dry-run planner")
    parser.add_argument("--atomic-source-update", action="store_true", help="Run v21.5 guarded atomic source update; dry-run unless approved")
    parser.add_argument("--runtime-migration-assistant", action="store_true", help="Run v21.6 runtime migration assistant")
    parser.add_argument("--route-safety-harness", action="store_true", help="Run v21.7 route safety harness")
    parser.add_argument("--release-dashboard-command-center", action="store_true", help="Run v21.8 release dashboard/API/CLI command center check")
    parser.add_argument("--clean-room-install-harness", action="store_true", help="Run v21.9 clean-room install harness from a release zip")
    parser.add_argument("--verified-self-update-release-pipeline", action="store_true", help="Run v22.0 verified self-update release pipeline")
    parser.add_argument("--trial-upgrade-from-zip", action="store_true", help="Run v22.1 trial upgrade harness from a release zip")
    parser.add_argument("--backup-rollback-drill", action="store_true", help="Run v22.2 backup and rollback drill in temp space")
    parser.add_argument("--update-collision-detector", action="store_true", help="Run v22.3 update collision detector")
    parser.add_argument("--version-registry-report", action="store_true", help="Run v22.4 version registry preview report")
    parser.add_argument("--release-provenance-report", action="store_true", help="Run v22.5 release provenance report")
    parser.add_argument("--dashboard-upgrade-wizard-preview", action="store_true", help="Run v22.6 dashboard upgrade wizard preview check")
    parser.add_argument("--api-upgrade-wizard-preview", action="store_true", help="Run v22.7 API upgrade wizard preview check")
    parser.add_argument("--staged-apply-drill", action="store_true", help="Run v22.8 staged apply drill in temp clone")
    parser.add_argument("--real-apply-guard-rails", action="store_true", help="Run v22.9 real apply guard rail check")
    parser.add_argument("--real-apply-rollback-verification", action="store_true", help="Run v22.10 real apply rollback verification preview")
    parser.add_argument("--self-update-ux-polish", action="store_true", help="Run v22.11 self-update UX polish check")
    parser.add_argument("--v23-readiness-gate", action="store_true", help="Run v22.12 v23 readiness gate")
    parser.add_argument("--controlled-self-maintenance-loop", action="store_true", help="Run v45.0 controlled self-maintenance loop")
    parser.add_argument("--controlled-self-maintenance-work-queue", action="store_true", help="Run v46.x controlled self-maintenance work queue")
    parser.add_argument("--controlled-attention-scheduler", action="store_true", help="Run v47.0 controlled attention scheduler")

    parser.add_argument("--self-maintenance-proposal", action="store_true", help="Run v23.1 self-maintenance proposal sandbox")
    parser.add_argument("--build-patch-plan", action="store_true", help="Run v23.2 maintenance patch plan builder")
    parser.add_argument("--generate-maintenance-patch", action="store_true", help="Run v23.3 dry-run maintenance patch generator")
    parser.add_argument("--patch-safety-audit", action="store_true", help="Run v23.4 patch safety auditor")
    parser.add_argument("--apply-maintenance-patch-to-temp", action="store_true", help="Run v23.5 maintenance patch apply drill in a temporary clone")
    parser.add_argument("--maintenance-review-bundle", action="store_true", help="Run v23.6 maintenance review bundle")
    parser.add_argument("--approve-maintenance-bundle", action="store_true", help="Run v23.7 exact maintenance bundle approval binding preview")
    parser.add_argument("--real-maintenance-patch-apply", action="store_true", help="Run v23.8 real maintenance patch apply gate; dry-run unless approved")
    parser.add_argument("--post-apply-health-monitor", action="store_true", help="Run v23.9 post-apply health monitor")
    parser.add_argument("--controlled-maintenance-cycle", action="store_true", help="Run v23.10 controlled maintenance cycle and stop before live apply")
    parser.add_argument("--assisted-self-improvement-release", action="store_true", help="Run v24.0 assisted self-improvement release gate")
    parser.add_argument("--improvement-candidate-scan", action="store_true", help="Run v24.1 improvement candidate scanner")
    parser.add_argument("--candidate-prioritizer", action="store_true", help="Run v24.2 improvement candidate prioritizer")
    parser.add_argument("--candidate-to-proposal", action="store_true", help="Run v24.3 candidate-to-proposal bridge")
    parser.add_argument("--maintenance-backlog", action="store_true", help="Run v24.4 maintenance backlog registry preview")
    parser.add_argument("--dashboard-maintenance-backlog", action="store_true", help="Run v24.5 dashboard maintenance backlog preview check")
    parser.add_argument("--api-maintenance-backlog", action="store_true", help="Run v24.6 API maintenance backlog preview check")
    parser.add_argument("--candidate-regression-detector", action="store_true", help="Run v24.7 candidate regression detector")
    parser.add_argument("--release-memory-privacy", action="store_true", help="Run v24.8 release memory privacy check")
    parser.add_argument("--candidate-verification-recipes", action="store_true", help="Run v24.9 candidate verification recipes")
    parser.add_argument("--assisted-improvement-cycle", action="store_true", help="Run v24.10 assisted improvement cycle")
    parser.add_argument("--semi-autonomous-maintenance-review", action="store_true", help="Run v25.0.1 semi-autonomous maintenance review hotfix gate")
    parser.add_argument("--hotfix-regression-lockdown", action="store_true", help="Run v25.1 hotfix regression lockdown")
    parser.add_argument("--dashboard-route-coverage", action="store_true", help="Run v25.2 dashboard route coverage auditor")
    parser.add_argument("--api-default-source-audit", action="store_true", help="Run v25.3 API default source-of-truth audit")
    parser.add_argument("--nested-readiness-severity", action="store_true", help="Run v25.4 nested readiness severity engine")
    parser.add_argument("--review-bundle-approval-contract", action="store_true", help="Run v25.5 review bundle approval contract")
    parser.add_argument("--maintenance-report-diff", action="store_true", help="Run v25.6 maintenance report diff viewer")
    parser.add_argument("--release-gate-composition-test", action="store_true", help="Run v25.7 release gate composition test")
    parser.add_argument("--dashboard-api-parity-audit", action="store_true", help="Run v25.8 dashboard/API parity audit")
    parser.add_argument("--operator-trust-report", action="store_true", help="Run v25.9 operator trust report")
    parser.add_argument("--trustworthy-maintenance-console", action="store_true", help="Run v26.0 trustworthy maintenance console gate")
    parser.add_argument("--trust-console-drill", action="store_true", help="Run v26.1 trust console drill mode")
    parser.add_argument("--trust-console-snapshot", action="store_true", help="Run v26.2 trust console snapshot export")
    parser.add_argument("--trust-console-diff", action="store_true", help="Run v26.3 trust console snapshot diff")
    parser.add_argument("--freeze-release-candidate", action="store_true", help="Run v26.4 release candidate freezer")
    parser.add_argument("--verify-frozen-release-zip", action="store_true", help="Run v26.5 freeze-to-zip verifier")
    parser.add_argument("--approval-evidence-ledger", action="store_true", help="Run v26.6 approval evidence ledger")
    parser.add_argument("--release-command-reproducer", action="store_true", help="Run v26.7 release command reproducer")
    parser.add_argument("--console-readme-consistency", action="store_true", help="Run v26.8 console-to-README consistency check")
    parser.add_argument("--pre-v27-safety-audit", action="store_true", help="Run v26.9 pre-v27 safety audit")
    parser.add_argument("--release-candidate-governance", action="store_true", help="Run v27.0 release candidate governance system")
    parser.add_argument("--release-governance-drill", action="store_true", help="Run v27.1 release governance evidence drill")
    parser.add_argument("--release-evidence-bundle", action="store_true", help="Run v27.2 release evidence bundle export")
    parser.add_argument("--verify-release-evidence-bundle", action="store_true", help="Run v27.3 release evidence bundle verifier")
    parser.add_argument("--release-governance-page", action="store_true", help="Run v27.4 dashboard release governance page check")
    parser.add_argument("--governance-api-read-only", action="store_true", help="Run v27.5 governance API read-only surface check")
    parser.add_argument("--release-artifact-diff", action="store_true", help="Run v27.6 release artifact diff")
    parser.add_argument("--release-signing-preparation", action="store_true", help="Run v27.7 release signing preparation")
    parser.add_argument("--local-trust-policy", action="store_true", help="Run v27.8 local trust policy")
    parser.add_argument("--release-governance-ux-polish", action="store_true", help="Run v27.9 release governance UX polish")
    parser.add_argument("--pre-v28-governance-audit", action="store_true", help="Run v27.10 pre-v28 governance audit")
    parser.add_argument("--verifiable-release-evidence-system", action="store_true", help="Run v28.0 verifiable release evidence system")
    parser.add_argument("--evidence-replay-drill", action="store_true", help="Run v28.1 evidence replay and tamper drill")
    parser.add_argument("--persist-release-evidence", action="store_true", help="Run v28.2 evidence bundle persistence")
    parser.add_argument("--replay-release-evidence", action="store_true", help="Run v28.3 replay release evidence command")
    parser.add_argument("--evidence-timeline", action="store_true", help="Run v28.4 evidence timeline")
    parser.add_argument("--evidence-operator-summary", action="store_true", help="Run v28.5 evidence-to-operator summary")
    parser.add_argument("--dashboard-evidence-viewer", action="store_true", help="Run v28.6 dashboard evidence viewer check")
    parser.add_argument("--api-evidence-viewer", action="store_true", help="Run v28.7 API evidence viewer check")
    parser.add_argument("--evidence-retention-policy", action="store_true", help="Run v28.8 evidence retention policy")
    parser.add_argument("--evidence-regression-lockdown", action="store_true", help="Run v28.9 evidence regression lockdown")
    parser.add_argument("--pre-v29-evidence-audit", action="store_true", help="Run v28.10 pre-v29 evidence audit")
    parser.add_argument("--durable-release-evidence-archive", action="store_true", help="Run v29.0 durable release evidence archive gate")
    parser.add_argument("--signing-readiness-audit", action="store_true", help="Run v29.1 signing readiness audit")
    parser.add_argument("--canonical-manifest-format", action="store_true", help="Run v29.2 canonical manifest format report")
    parser.add_argument("--canonical-evidence-schema", action="store_true", help="Run v29.3 canonical evidence bundle schema report")
    parser.add_argument("--release-signing-status", action="store_true", help="Run v29.4 release signing status reporter")
    parser.add_argument("--signature-placeholder-contract", action="store_true", help="Run v29.5 signature placeholder contract")
    parser.add_argument("--key-policy-preparation", action="store_true", help="Run v29.6 key policy preparation")
    parser.add_argument("--verify-release-signature", action="store_true", help="Run v29.7 signature verification placeholder")
    parser.add_argument("--dashboard-signing-status", action="store_true", help="Run v29.8 dashboard signing status check")
    parser.add_argument("--api-signing-status", action="store_true", help="Run v29.9 API signing status check")
    parser.add_argument("--pre-v30-signing-prep-audit", action="store_true", help="Run v29.10 pre-v30 signing prep audit")
    parser.add_argument("--signed-release-preparation-system", action="store_true", help="Run v30.0 signed release preparation system")
    parser.add_argument("--signing-api-hardening", action="store_true", help="Run v30.1 signing API hardening audit")
    parser.add_argument("--canonical-schema-validator", action="store_true", help="Run v30.2 strict canonical schema validator")
    parser.add_argument("--source-data-sanitizer", action="store_true", help="Run v30.3 source data sanitizer audit")
    parser.add_argument("--signing-trust-model", action="store_true", help="Run v30.4 signing trust model split")
    parser.add_argument("--release-signing-tamper-drill", action="store_true", help="Run v30.5 release signing tamper drill")
    parser.add_argument("--public-key-policy-design", action="store_true", help="Run v30.6 public key policy design")
    parser.add_argument("--detached-signature-contract", action="store_true", help="Run v30.7 detached signature contract")
    parser.add_argument("--signature-fixture-verification", action="store_true", help="Run v30.8 signature fixture verification harness")
    parser.add_argument("--external-signer-workflow", action="store_true", help="Run v30.9 external signer workflow preview")
    parser.add_argument("--detached-signature-verification-system", action="store_true", help="Run v31.0 detached signature verification system")
    parser.add_argument("--signature-verification-hardening", action="store_true", help="Run v31.1 signature verification hardening")
    parser.add_argument("--public-trust-root-config", action="store_true", help="Run v31.2 public trust root config audit")
    parser.add_argument("--external-signing-payload-export", action="store_true", help="Run v31.3 external signing payload export")
    parser.add_argument("--signed-fixture-test-suite", action="store_true", help="Run v31.4 signed fixture test suite")
    parser.add_argument("--release-publish-gate", action="store_true", help="Run v31.5 release publish readiness gate")
    parser.add_argument("--release-trust-dashboard-polish", action="store_true", help="Run v31.6 release trust dashboard polish audit")
    parser.add_argument("--api-route-safety-audit", action="store_true", help="Run v31.7 API route safety audit")
    parser.add_argument("--release-reproducibility-check", action="store_true", help="Run v31.8 release reproducibility check")
    parser.add_argument("--pre-v32-release-candidate-gate", action="store_true", help="Run v31.9 pre-v32 release candidate gate")
    parser.add_argument("--signed-release-governance", action="store_true", help="Run v32.0 signed release governance report")
    parser.add_argument("--governance-report-cleanup", action="store_true", help="Run v32.1 governance report cleanup")
    parser.add_argument("--release-candidate-workspace", action="store_true", help="Run v32.2 release candidate workspace report")
    parser.add_argument("--artifact-binding-audit", action="store_true", help="Run v32.3 artifact binding audit v2")
    parser.add_argument("--surface-consistency-audit", action="store_true", help="Run v32.4 dashboard/API/CLI surface consistency audit")
    parser.add_argument("--external-signing-handoff", action="store_true", help="Run v32.5 external signing handoff report")
    parser.add_argument("--signature-intake-validation", action="store_true", help="Run v32.6 signature intake validation")
    parser.add_argument("--trusted-signer-registry", action="store_true", help="Run v32.7 trusted signer registry viewer")
    parser.add_argument("--governance-scenario-suite", action="store_true", help="Run v32.8 governance dry-run scenario suite")
    parser.add_argument("--pre-v33-operations-gate", action="store_true", help="Run v32.9 pre-v33 operations gate")
    parser.add_argument("--release-operations-console", action="store_true", help="Run v33.0 release operations console")
    parser.add_argument("--operations-console-cleanup", action="store_true", help="Run v33.1 operations console cleanup")
    parser.add_argument("--release-candidate-review", action="store_true", help="Run v33.2 release candidate review workflow")
    parser.add_argument("--signed-artifact-intake", action="store_true", help="Run v33.3 signed artifact intake workflow")
    parser.add_argument("--trust-root-lifecycle", action="store_true", help="Run v33.4 trust root lifecycle report")
    parser.add_argument("--publish-decision-explainer", action="store_true", help="Run v33.5 publish decision explainer")
    parser.add_argument("--operator-action-guardrails", action="store_true", help="Run v33.6 operator action guardrails")
    parser.add_argument("--unsigned-release-drill", action="store_true", help="Run v33.7 unsigned release drill")
    parser.add_argument("--signed-fixture-release-drill", action="store_true", help="Run v33.8 signed fixture release drill")
    parser.add_argument("--pre-v34-operator-workflow-gate", action="store_true", help="Run v33.9 pre-v34 operator workflow gate")
    parser.add_argument("--release-operator-workflow", action="store_true", help="Run v34.0 release operator workflow")
    parser.add_argument("--release-candidate-record", action="store_true", help="Run v34.1 release candidate record v2")
    parser.add_argument("--signed-artifact-intake-v2", action="store_true", help="Run v34.2 signed artifact intake v2")
    parser.add_argument("--trust-root-management-policy", action="store_true", help="Run v34.3 trust root management policy")
    parser.add_argument("--trust-root-mutation-guardrails", action="store_true", help="Run v34.4 trust root mutation guardrails")
    parser.add_argument("--signed-release-publish-decision", action="store_true", help="Run v34.5 signed release publish decision v2")
    parser.add_argument("--operator-dashboard-action-states", action="store_true", help="Run v34.6 operator dashboard action states")
    parser.add_argument("--release-workflow-audit-trail", action="store_true", help="Run v34.7 release workflow audit trail viewer")
    parser.add_argument("--trusted-fixture-workflow", action="store_true", help="Run v34.8 trusted fixture workflow")
    parser.add_argument("--pre-v35-trusted-candidate-gate", action="store_true", help="Run v34.9 pre-v35 trusted candidate gate")
    parser.add_argument("--trusted-release-candidate-system", action="store_true", help="Run v35.0 trusted release candidate system")
    parser.add_argument("--candidate-review-state", action="store_true", help="Run v35.1 candidate review state hardening")
    parser.add_argument("--publish-approval-policy", action="store_true", help="Run v35.2 publish approval policy")
    parser.add_argument("--publish-approval-dry-run", action="store_true", help="Run v35.3 publish approval dry-run")
    parser.add_argument("--publish-approval-record-schema", action="store_true", help="Run v35.4 publish approval record schema")
    parser.add_argument("--dashboard-approval-state-preview", action="store_true", help="Run v35.5 dashboard approval state preview")
    parser.add_argument("--approval-route-safety-audit", action="store_true", help="Run v35.6 approval route safety audit")
    parser.add_argument("--approval-fixture-drill", action="store_true", help="Run v35.7 approval fixture drill")
    parser.add_argument("--publish-approval-explainer", action="store_true", help="Run v35.8 publish approval explainer")
    parser.add_argument("--pre-v36-approval-separation-gate", action="store_true", help="Run v35.9 pre-v36 approval separation gate")
    parser.add_argument("--publish-approval-separation-system", action="store_true", help="Run v36.0 publish approval separation system")
    parser.add_argument("--publish-approval-record-validator", action="store_true", help="Run v36.1 publish approval record validator")
    parser.add_argument("--publish-approval-dry-run-v2", action="store_true", help="Run v36.2 publish approval dry-run v2")
    parser.add_argument("--approval-storage-quarantine", action="store_true", help="Run v36.3 approval storage quarantine")
    parser.add_argument("--publish-approval-api-preview", action="store_true", help="Run v36.4 publish approval API preview")
    parser.add_argument("--dashboard-approval-workflow-preview", action="store_true", help="Run v36.5 dashboard approval workflow preview")
    parser.add_argument("--approval-confirmation-policy", action="store_true", help="Run v36.6 approval confirmation policy")
    parser.add_argument("--approval-record-fixture-drill", action="store_true", help="Run v36.7 approval record fixture drill")
    parser.add_argument("--approval-audit-trail", action="store_true", help="Run v36.8 approval audit trail viewer")
    parser.add_argument("--pre-v37-approval-records-gate", action="store_true", help="Run v36.9 pre-v37 approval records gate")
    parser.add_argument("--controlled-publish-approval-system", action="store_true", help="Run v37.0 controlled publish approval system")
    parser.add_argument("--publish-approval-write-preflight", action="store_true", help="Run v37.1 publish approval write preflight")
    parser.add_argument("--publish-approval-write-schema-lock", action="store_true", help="Run v37.2 publish approval write schema lock")
    parser.add_argument("--publish-approval-confirmation-validator", action="store_true", help="Run v37.3 publish approval confirmation validator")
    parser.add_argument("--post-only-approval-write-route-design", action="store_true", help="Run v37.4 POST-only approval write route design")
    parser.add_argument("--approval-write-dashboard-preview", action="store_true", help="Run v37.5 approval write dashboard preview")
    parser.add_argument("--write-publish-approval", action="store_true", help="Run v37.6 guarded publish approval write; dry-run unless --approve-publish-approval-write is used")
    parser.add_argument("--approve-publish-approval-write", action="store_true", help="Allow v37.6 publish approval write when eligibility and confirmation pass")
    parser.add_argument("--approval-write-rollback-safety-audit", action="store_true", help="Run v37.7 approval write rollback/apply pointer safety audit")
    parser.add_argument("--approval-write-fixture-drill", action="store_true", help="Run v37.8 approval write fixture drill")
    parser.add_argument("--pre-v38-approval-write-gate", action="store_true", help="Run v37.9 pre-v38 approval write gate")
    parser.add_argument("--controlled-publish-approval-write-system", action="store_true", help="Run v38.0 controlled publish approval write system")
    parser.add_argument("--publish-approval-record-reader", action="store_true", help="Run v38.1 publish approval record reader")
    parser.add_argument("--approval-artifact-revalidation", action="store_true", help="Run v38.2 approval artifact revalidation")
    parser.add_argument("--approval-record-conflict-detector", action="store_true", help="Run v38.3 approval record conflict detector")
    parser.add_argument("--approval-status-viewer", action="store_true", help="Run v38.4 approval status dashboard/API viewer")
    parser.add_argument("--approval-revocation-policy", action="store_true", help="Run v38.5 approval revocation policy")
    parser.add_argument("--approval-revocation-dry-run", action="store_true", help="Run v38.6 approval revocation dry-run")
    parser.add_argument("--approval-record-id", help="Approval record ID or hash for lifecycle/revocation checks")
    parser.add_argument("--approval-lifecycle-audit", action="store_true", help="Run v38.7 approval lifecycle audit viewer")
    parser.add_argument("--approval-lifecycle-fixture-drill", action="store_true", help="Run v38.8 approval lifecycle fixture drill")
    parser.add_argument("--pre-v39-approval-lifecycle-gate", action="store_true", help="Run v38.9 pre-v39 approval lifecycle gate")
    parser.add_argument("--publish-approval-lifecycle-system", action="store_true", help="Run v39.0 publish approval lifecycle system")
    parser.add_argument("--approval-revocation-record-schema", action="store_true", help="Run v39.1 approval revocation record schema")
    parser.add_argument("--approval-revocation-confirmation-validator", action="store_true", help="Run v39.2 approval revocation confirmation validator")
    parser.add_argument("--approval-revocation-write-preflight", action="store_true", help="Run v39.3 approval revocation write preflight")
    parser.add_argument("--revocation-storage-quarantine", action="store_true", help="Run v39.4 revocation storage quarantine")
    parser.add_argument("--post-only-revocation-route-design", action="store_true", help="Run v39.5 POST-only revocation route design")
    parser.add_argument("--write-approval-revocation", action="store_true", help="Run v39.6 guarded approval revocation write; dry-run unless --approve-publish-approval-revocation is used")
    parser.add_argument("--approve-publish-approval-revocation", action="store_true", help="Allow v39.6 publish approval revocation write when eligibility and confirmation pass")
    parser.add_argument("--dashboard-revocation-preview", action="store_true", help="Run v39.7 dashboard revocation preview")
    parser.add_argument("--approval-revocation-fixture-drill", action="store_true", help="Run v39.8 approval revocation fixture drill")
    parser.add_argument("--pre-v40-revocation-gate", action="store_true", help="Run v39.9 pre-v40 revocation gate")
    parser.add_argument("--controlled-publish-approval-revocation-system", action="store_true", help="Run v40.0 controlled publish approval revocation system")
    parser.add_argument("--autonomy-capability-inventory", action="store_true", help="Run v40.1 autonomy capability inventory")
    parser.add_argument("--autonomous-task-proposal-schema", action="store_true", help="Run v40.2 autonomous task proposal schema")
    parser.add_argument("--autonomous-dry-run-plan", action="store_true", help="Run v40.3 autonomous dry-run planner")
    parser.add_argument("--autonomy-action-policy-engine", action="store_true", help="Run v40.4 autonomy action policy engine")
    parser.add_argument("--autonomous-patch-sandbox", action="store_true", help="Run v40.5 autonomous patch sandbox report")
    parser.add_argument("--autonomous-patch-risk-classifier", action="store_true", help="Run v40.6 autonomous patch risk classifier")
    parser.add_argument("--autonomous-test-selection", action="store_true", help="Run v40.7 autonomous test selection")
    parser.add_argument("--autonomy-human-checkpoint", action="store_true", help="Run v40.8 autonomy human checkpoint report")
    parser.add_argument("--pre-v41-autonomy-readiness-gate", action="store_true", help="Run v40.9 pre-v41 autonomy readiness gate")
    parser.add_argument("--autonomy-readiness-boundary-system", action="store_true", help="Run v41.0 autonomy readiness boundary system")
    parser.add_argument("--patch-proposal-schema", action="store_true", help="Run v41.1 patch proposal schema")
    parser.add_argument("--autonomous-change-target-selector", action="store_true", help="Run v41.2 autonomous change target selector")
    parser.add_argument("--generate-sandbox-patch", action="store_true", help="Run v41.3 sandbox patch generator")
    parser.add_argument("--sandbox-patch-diff", action="store_true", help="Run v41.4 sandbox patch diff viewer")
    parser.add_argument("--sandbox-patch-validation", action="store_true", help="Run v41.5 sandbox patch validation")
    parser.add_argument("--sandbox-patch-test-run", action="store_true", help="Run v41.6 sandbox patch test run")
    parser.add_argument("--patch-review-checkpoint", action="store_true", help="Run v41.7 patch review checkpoint")
    parser.add_argument("--source-apply-dry-run", action="store_true", help="Run v41.8 controlled source apply dry-run")
    parser.add_argument("--pre-v42-autonomous-patch-gate", action="store_true", help="Run v41.9 pre-v42 autonomous patch gate")
    parser.add_argument("--autonomous-patch-proposal-system", action="store_true", help="Run v42.0 autonomous patch proposal system")
    parser.add_argument("--source-apply-eligibility", action="store_true", help="Run v42.1 source apply eligibility report")
    parser.add_argument("--source-apply-confirmation-policy", action="store_true", help="Run v42.2 source apply confirmation policy")
    parser.add_argument("--source-apply-dry-run-v2", action="store_true", help="Run v42.3 exact source apply dry-run")
    parser.add_argument("--source-apply-backup-quarantine", action="store_true", help="Run v42.4 source apply backup quarantine")
    parser.add_argument("--apply-reviewed-patch", action="store_true", help="Run v42.5 guarded reviewed patch apply; dry-run unless --approve-source-apply is provided")
    parser.add_argument("--approve-source-apply", action="store_true", help="Allow v42.5 guarded source apply when eligibility and confirmation pass")
    parser.add_argument("--post-source-apply-verification", action="store_true", help="Run v42.6 post source apply verification")
    parser.add_argument("--source-apply-rollback-preview", action="store_true", help="Run v42.7 source apply rollback preview")
    parser.add_argument("--source-apply-fixture-drill", action="store_true", help="Run v42.8 source apply fixture drill")
    parser.add_argument("--pre-v43-source-apply-gate", action="store_true", help="Run v42.9 pre-v43 source apply gate")
    parser.add_argument("--controlled-source-apply-system", action="store_true", help="Run v43.0 controlled source apply system")
    parser.add_argument("--source-apply-record-reader", action="store_true", help="Run v43.1 source apply record reader")
    parser.add_argument("--source-rollback-eligibility", action="store_true", help="Run v43.2 source rollback eligibility report")
    parser.add_argument("--source-rollback-confirmation-policy", action="store_true", help="Run v43.3 source rollback confirmation policy")
    parser.add_argument("--source-rollback-dry-run-v2", action="store_true", help="Run v43.4 exact source rollback dry-run")
    parser.add_argument("--rollback-applied-patch", action="store_true", help="Run v43.5 guarded applied patch rollback; dry-run unless --approve-source-rollback is provided")
    parser.add_argument("--approve-source-rollback", action="store_true", help="Allow v43.5 guarded source rollback when eligibility and confirmation pass")
    parser.add_argument("--post-source-rollback-verification", action="store_true", help="Run v43.6 post source rollback verification")
    parser.add_argument("--source-rollback-audit-trail", action="store_true", help="Run v43.7 source rollback audit trail")
    parser.add_argument("--source-rollback-fixture-drill", action="store_true", help="Run v43.8 source rollback fixture drill")
    parser.add_argument("--pre-v44-source-rollback-gate", action="store_true", help="Run v43.9 pre-v44 source rollback gate")
    parser.add_argument("--controlled-source-rollback-system", action="store_true", help="Run v44.0 controlled source rollback system")
    parser.add_argument("--self-maintenance-cycle-schema", action="store_true", help="Run v44.1 self-maintenance cycle schema")
    parser.add_argument("--self-maintenance-plan", action="store_true", help="Run v44.2 self-maintenance planner")
    parser.add_argument("--self-maintenance-sandbox-cycle", action="store_true", help="Run v44.3 self-maintenance sandbox cycle")
    parser.add_argument("--maintenance-checkpoint-binder", action="store_true", help="Run v44.4 maintenance checkpoint binder")
    parser.add_argument("--self-maintenance-apply-dry-run", action="store_true", help="Run v44.5 self-maintenance apply dry-run")
    parser.add_argument("--self-maintenance-apply-handoff", action="store_true", help="Run v44.6 self-maintenance apply handoff")
    parser.add_argument("--post-maintenance-verification-summary", action="store_true", help="Run v44.7 post-maintenance verification summary")
    parser.add_argument("--self-maintenance-fixture-drill", action="store_true", help="Run v44.8 self-maintenance fixture drill")
    parser.add_argument("--pre-v45-self-maintenance-gate", action="store_true", help="Run v44.9 pre-v45 self-maintenance gate")
    parser.add_argument("--maintenance-task-record-schema", action="store_true", help="Run v45.1 maintenance task record schema")
    parser.add_argument("--maintenance-task-priority-risk-scoring", action="store_true", help="Run v45.2 maintenance task priority/risk scoring")
    parser.add_argument("--maintenance-task-queue-registry", action="store_true", help="Run v45.3 maintenance task queue registry")
    parser.add_argument("--maintenance-task-selection-policy", action="store_true", help="Run v45.4 maintenance task selection policy")
    parser.add_argument("--maintenance-task-cycle-orchestrator", action="store_true", help="Run v45.5 maintenance task cycle orchestrator")
    parser.add_argument("--maintenance-task-checkpoint-binding", action="store_true", help="Run v45.6 maintenance task checkpoint binding")
    parser.add_argument("--maintenance-task-source-apply-lockout", action="store_true", help="Run v45.7 maintenance task source apply lockout")
    parser.add_argument("--maintenance-task-dashboard-api-views", action="store_true", help="Run v45.8 maintenance task dashboard/API views")
    parser.add_argument("--maintenance-task-fixture-drill", action="store_true", help="Run v45.9 maintenance task fixture drill")
    parser.add_argument("--pre-v46-maintenance-queue-gate", action="store_true", help="Run v45.10 pre-v46 maintenance queue gate")
    parser.add_argument("--autonomy-queue-report-cache", action="store_true", help="Run v46.2 autonomy/queue report cache")
    parser.add_argument("--maintenance-task-drilldown", action="store_true", help="Run v46.3 maintenance task drill-down view")
    parser.add_argument("--queue-stale-state-warnings", action="store_true", help="Run v46.4 maintenance queue stale-state warnings")
    parser.add_argument("--maintenance-runtime-privacy-audit", action="store_true", help="Run v46.5 runtime privacy audit hardening")
    parser.add_argument("--operator-command-palette", action="store_true", help="Run v46.6 operator command palette/filter report")
    parser.add_argument("--dashboard-api-queue-parity", action="store_true", help="Run v46.7 dashboard/API queue parity report")
    parser.add_argument("--queue-verification-receipt", action="store_true", help="Run v46.8 queue verification receipt")
    parser.add_argument("--dashboard-accessibility-compact-layout", action="store_true", help="Run v46.9 dashboard accessibility and compact layout audit")
    parser.add_argument("--pre-v47-attention-scheduler-gate", action="store_true", help="Run v46.10 pre-v47 attention scheduler gate")
    parser.add_argument("--attention-selection-receipt", action="store_true", help="Run v47.1 attention selection receipt and explainability report")
    parser.add_argument("--pre-v47-1-attention-receipt-gate", action="store_true", help="Run v47.1 attention receipt explainability gate")
    parser.add_argument("--attention-budget-ledger", action="store_true", help="Run v47.2 attention budget ledger")
    parser.add_argument("--deferred-task-memory", action="store_true", help="Run v47.3 deferred task memory preview")
    parser.add_argument("--blocked-task-handling", action="store_true", help="Run v47.4 blocked task handling report")
    parser.add_argument("--attention-resume-context", action="store_true", help="Run v47.5 attention resume context")
    parser.add_argument("--attention-dashboard-polish", action="store_true", help="Run v47.6 attention dashboard polish audit")
    parser.add_argument("--attention-api-parity-gate", action="store_true", help="Run v47.7 attention/API parity gate")
    parser.add_argument("--reflection-hooks-read-only", action="store_true", help="Run v47.8 read-only reflection hooks")
    parser.add_argument("--pre-v48-reflection-gate", action="store_true", help="Run v47.9 pre-v48 reflection gate")
    parser.add_argument("--reflection-memory-loop", action="store_true", help="Run v48.0 controlled reflection memory loop")
    parser.add_argument("--reflection-review-receipts", action="store_true", help="Run v48.1 reflection receipts and review console")
    parser.add_argument("--reflection-candidate-deduplication", action="store_true", help="Run v48.2 reflection candidate deduplication")
    parser.add_argument("--reflection-rejection-memory", action="store_true", help="Run v48.3 runtime-only reflection rejection memory")
    parser.add_argument("--reflection-promotion-drafts", action="store_true", help="Run v48.4 reflection promotion drafts")
    parser.add_argument("--memory-safety-classifier", action="store_true", help="Run v48.5 memory safety classifier")
    parser.add_argument("--reflection-dashboard-polish", action="store_true", help="Run v48.6 reflection dashboard polish audit")
    parser.add_argument("--reflection-api-parity-gate", action="store_true", help="Run v48.7 reflection/API parity gate")
    parser.add_argument("--reflection-privacy-package-hardening", action="store_true", help="Run v48.8 reflection privacy package hardening")
    parser.add_argument("--pre-v49-identity-continuity-gate", action="store_true", help="Run v48.9 pre-v49 identity continuity gate")
    parser.add_argument("--identity-continuity-layer", action="store_true", help="Run v49.0 identity continuity layer")
    parser.add_argument("--identity-receipts", action="store_true", help="Run v49.1 identity receipts and drift explainability")
    parser.add_argument("--pre-v49-1-identity-receipts-gate", action="store_true", help="Run v50.0 identity receipt explainability gate")
    parser.add_argument("--stable-principles-ledger", action="store_true", help="Run v49.2 stable principles ledger")
    parser.add_argument("--identity-drift-classifier", action="store_true", help="Run v49.3 identity drift classifier")
    parser.add_argument("--identity-snapshot-comparison", action="store_true", help="Run v49.4 identity snapshot comparison")
    parser.add_argument("--operator-identity-review-drafts", action="store_true", help="Run v49.5 operator identity review drafts")
    parser.add_argument("--identity-dashboard-polish", action="store_true", help="Run v49.6 identity dashboard polish audit")
    parser.add_argument("--identity-api-parity-gate", action="store_true", help="Run v49.7 identity/API parity gate")
    parser.add_argument("--identity-privacy-package-hardening", action="store_true", help="Run v49.8 identity privacy package hardening")
    parser.add_argument("--pre-v50-durable-memory-gate", action="store_true", help="Run v49.9 pre-v50 durable memory gate")
    parser.add_argument("--durable-memory-promotion", action="store_true", help="Run v50.0 supervised durable-memory promotion queue")
    parser.add_argument("--memory-promotion-receipts", action="store_true", help="Run v50.1 memory promotion receipts and review console")
    parser.add_argument("--memory-promotion-deduplication", action="store_true", help="Run v50.2 memory promotion deduplication")
    parser.add_argument("--memory-rejection-runtime-ledger", action="store_true", help="Run v50.3 runtime-only memory rejection ledger")
    parser.add_argument("--memory-promotion-confirmation-gate", action="store_true", help="Run v50.4 memory promotion confirmation gate")
    parser.add_argument("--memory-removal-drafts", action="store_true", help="Run v50.5 memory removal drafts")
    parser.add_argument("--memory-dashboard-polish", action="store_true", help="Run v50.6 memory dashboard polish audit")
    parser.add_argument("--memory-api-parity-gate", action="store_true", help="Run v50.7 memory/API parity gate")
    parser.add_argument("--memory-privacy-package-hardening", action="store_true", help="Run v50.8 memory privacy and package hardening")
    parser.add_argument("--pre-v51-durable-write-gate", action="store_true", help="Run v50.9 pre-v51 durable write gate")
    parser.add_argument("--durable-memory-write", action="store_true", help="Run v51.0 controlled durable memory write path; preview unless execute and exact confirmation are supplied")
    parser.add_argument("--memory-promotion-id", default="", help="Promotion id for memory confirmation/write checks")
    parser.add_argument("--memory-confirm-phrase", default="", help="Exact durable-memory confirmation phrase")
    parser.add_argument("--execute-durable-memory-write", action="store_true", help="Execute v51.0 durable-memory write only with exact confirmation")
    parser.add_argument("--durable-memory-write-receipts", action="store_true", help="Run v51.1 durable-memory write receipts and audit console")
    parser.add_argument("--memory-store-schema-hardening", action="store_true", help="Run v51.2 memory store schema hardening")
    parser.add_argument("--memory-read-path", action="store_true", help="Run v51.3 read-only memory read path")
    parser.add_argument("--memory-search-filter", action="store_true", help="Run v51.4 memory search and filter")
    parser.add_argument("--memory-correction-drafts", action="store_true", help="Run v51.5 memory correction drafts")
    parser.add_argument("--memory-removal-confirmation-path", action="store_true", help="Run v51.6 memory removal confirmation path; preview unless execute and exact confirmation are supplied")
    parser.add_argument("--memory-store-dashboard-polish", action="store_true", help="Run v51.7 memory dashboard polish gate")
    parser.add_argument("--memory-store-api-parity-gate", action="store_true", help="Run v51.8 memory/API parity gate")
    parser.add_argument("--pre-v52-recall-gate", action="store_true", help="Run v51.9 pre-v52 memory recall gate")
    parser.add_argument("--memory-recall-self-context", action="store_true", help="Run v52.0 memory recall and self-context retrieval")
    parser.add_argument("--memory-recall-receipts", action="store_true", help="Run v52.1 recall receipts and evidence console")
    parser.add_argument("--recall-conflict-resolver", action="store_true", help="Run v52.2 recall conflict resolver")
    parser.add_argument("--stale-memory-handling", action="store_true", help="Run v52.3 stale memory handling")
    parser.add_argument("--recall-scope-controls", action="store_true", help="Run v52.4 recall scope controls")
    parser.add_argument("--recall-privacy-classifier", action="store_true", help="Run v52.5 recall privacy classifier")
    parser.add_argument("--recall-dashboard-polish", action="store_true", help="Run v52.6 recall dashboard polish audit")
    parser.add_argument("--recall-api-parity-gate", action="store_true", help="Run v52.7 recall/API parity gate")
    parser.add_argument("--recall-privacy-package-hardening", action="store_true", help="Run v52.8 recall privacy and package hardening")
    parser.add_argument("--pre-v53-memory-informed-planning-gate", action="store_true", help="Run v52.9 pre-v53 memory-informed planning gate")
    parser.add_argument("--memory-informed-planning", action="store_true", help="Run v53.0 memory-informed planning loop")
    parser.add_argument("--memory-informed-planning-receipts", action="store_true", help="Run v53.1 planning receipts and evidence console")
    parser.add_argument("--plan-conflict-classifier", action="store_true", help="Run v53.2 plan conflict classifier")
    parser.add_argument("--plan-revision-drafts", action="store_true", help="Run v53.3 plan revision drafts")
    parser.add_argument("--planning-scope-controls", action="store_true", help="Run v53.4 planning scope controls")
    parser.add_argument("--planning-risk-budget", action="store_true", help="Run v53.5 planning risk budget")
    parser.add_argument("--planning-dashboard-polish", action="store_true", help="Run v53.6 planning dashboard polish audit")
    parser.add_argument("--planning-api-parity-gate", action="store_true", help="Run v53.7 planning/API parity gate")
    parser.add_argument("--planning-privacy-package-hardening", action="store_true", help="Run v53.8 planning privacy and package hardening")
    parser.add_argument("--pre-v54-action-planning-gate", action="store_true", help="Run v53.9 pre-v54 action planning gate")
    parser.add_argument("--supervised-action-planning", action="store_true", help="Run v54.0 supervised action planning loop")
    parser.add_argument("--action-plan-receipts", action="store_true", help="Run v54.1 action plan receipts and evidence console")
    parser.add_argument("--action-step-classifier", action="store_true", help="Run v54.2 action step classifier")
    parser.add_argument("--action-dependency-graph", action="store_true", help="Run v54.3 action dependency graph")
    parser.add_argument("--action-risk-budget", action="store_true", help="Run v54.4 action risk budget")
    parser.add_argument("--action-rehearsal-dry-run-preview", action="store_true", help="Run v54.5 action rehearsal / dry-run preview")
    parser.add_argument("--action-dashboard-polish", action="store_true", help="Run v54.6 action dashboard polish audit")
    parser.add_argument("--action-api-parity-gate", action="store_true", help="Run v54.7 action/API parity gate")
    parser.add_argument("--action-privacy-package-hardening", action="store_true", help="Run v54.8 action privacy and package hardening")
    parser.add_argument("--pre-v55-controlled-execution-gate", action="store_true", help="Run v54.9 pre-v55 controlled execution gate")
    parser.add_argument("--controlled-action-execution-preview", action="store_true", help="Run v55.0 controlled action execution preview; no real operations are executed")
    parser.add_argument("--execution-preview-receipts", action="store_true", help="Run v55.1 execution preview receipts and evidence console")
    parser.add_argument("--execution-step-permission-classifier", action="store_true", help="Run v55.2 execution step permission classifier")
    parser.add_argument("--read-only-command-allowlist", action="store_true", help="Run v55.3 read-only command allowlist")
    parser.add_argument("--execution-sandbox-evidence-binder", action="store_true", help="Run v55.4 execution sandbox evidence binder")
    parser.add_argument("--execution-result-receipts", action="store_true", help="Run v55.5 execution result receipts")
    parser.add_argument("--execution-dashboard-polish", action="store_true", help="Run v55.6 execution dashboard polish audit")
    parser.add_argument("--execution-api-parity-gate", action="store_true", help="Run v55.7 execution/API parity gate")
    parser.add_argument("--execution-privacy-package-hardening", action="store_true", help="Run v55.8 execution privacy and package hardening")
    parser.add_argument("--pre-v56-read-only-execution-gate", action="store_true", help="Run v55.9 pre-v56 read-only execution gate")
    parser.add_argument("--controlled-read-only-action-execution", action="store_true", help="Run v56.0 controlled read-only action execution")
    parser.add_argument("--read-only-command-key", default="version-import", help="Allowlisted read-only command key for v56 execution")
    parser.add_argument("--read-only-confirm-phrase", default="", help="Exact confirmation phrase for v56 read-only execution")
    parser.add_argument("--execute-read-only-action", action="store_true", help="Execute one allowlisted read-only command after exact confirmation")
    parser.add_argument("--read-only-execution-receipts", action="store_true", help="Run v56.1 read-only execution receipts and audit console")
    parser.add_argument("--expanded-diagnostic-allowlist", action="store_true", help="Run v56.2 expanded diagnostic allowlist")
    parser.add_argument("--read-only-output-classifier", action="store_true", help="Run v56.3 read-only output classifier")
    parser.add_argument("--diagnostic-evidence-binder", action="store_true", help="Run v56.4 diagnostic evidence binder")
    parser.add_argument("--diagnostic-result-summaries", action="store_true", help="Run v56.5 diagnostic result summaries")
    parser.add_argument("--read-only-execution-dashboard-polish", action="store_true", help="Run v56.6 read-only execution dashboard polish audit")
    parser.add_argument("--read-only-execution-api-parity-gate", action="store_true", help="Run v56.7 read-only execution/API parity gate")
    parser.add_argument("--read-only-execution-privacy-package-hardening", action="store_true", help="Run v56.8 read-only execution privacy and package hardening")
    parser.add_argument("--pre-v57-evidence-gathering-gate", action="store_true", help="Run v56.9 pre-v57 evidence-gathering gate")
    parser.add_argument("--evidence-gathering-maintenance-loop", action="store_true", help="Run v57.0 evidence-gathering maintenance loop")
    parser.add_argument("--evidence-collection-receipts", action="store_true", help="Run v57.1 evidence receipts and diagnostic audit console")
    parser.add_argument("--diagnostic-issue-classifier", action="store_true", help="Run v57.2 diagnostic issue classifier")
    parser.add_argument("--evidence-conflict-staleness-resolver", action="store_true", help="Run v57.3 evidence conflict and staleness resolver")
    parser.add_argument("--evidence-to-plan-update-drafts", action="store_true", help="Run v57.4 evidence-to-plan update drafts")
    parser.add_argument("--diagnostic-coverage-map", action="store_true", help="Run v57.5 diagnostic coverage map")
    parser.add_argument("--evidence-dashboard-polish", action="store_true", help="Run v57.6 evidence dashboard polish audit")
    parser.add_argument("--evidence-api-parity-gate", action="store_true", help="Run v57.7 evidence/API parity gate")
    parser.add_argument("--evidence-privacy-package-hardening", action="store_true", help="Run v57.8 evidence privacy and package hardening")
    parser.add_argument("--pre-v58-patch-proposal-gate", action="store_true", help="Run v57.9 pre-v58 patch proposal gate")
    parser.add_argument("--evidence-grounded-patch-proposal", action="store_true", help="Run v58.0 evidence-grounded sandbox patch proposal loop")
    parser.add_argument("--patch-proposal-receipts", action="store_true", help="Run v58.1 patch proposal receipts")
    parser.add_argument("--patch-scope-classifier", action="store_true", help="Run v58.2 patch scope classifier")
    parser.add_argument("--patch-risk-budget", action="store_true", help="Run v58.3 patch risk budget")
    parser.add_argument("--patch-diff-preview-drafts", action="store_true", help="Run v58.4 patch diff preview drafts")
    parser.add_argument("--patch-verification-plan", action="store_true", help="Run v58.5 patch verification plan")
    parser.add_argument("--patch-dashboard-polish", action="store_true", help="Run v58.6 patch dashboard polish audit")
    parser.add_argument("--patch-api-parity-gate", action="store_true", help="Run v58.7 patch/API parity gate")
    parser.add_argument("--patch-privacy-package-hardening", action="store_true", help="Run v58.8 patch privacy and package hardening")
    parser.add_argument("--pre-v59-sandbox-patch-execution-gate", action="store_true", help="Run v58.9 pre-v59 sandbox patch execution gate")
    parser.add_argument("--controlled-sandbox-patch-execution", action="store_true", help="Run v59.0 controlled sandbox patch execution preview or confirmed sandbox-only rehearsal")
    parser.add_argument("--sandbox-patch-confirm-phrase", default="", help="Exact confirmation phrase for controlled sandbox patch execution")
    parser.add_argument("--execute-sandbox-patch", action="store_true", help="Execute v59 sandbox patch rehearsal only inside a temporary sandbox copy with exact confirmation")
    parser.add_argument("--sandbox-execution-receipts", action="store_true", help="Run v59.1 sandbox execution receipts and review console")
    parser.add_argument("--sandbox-verification-matrix", action="store_true", help="Run v59.2 sandbox verification matrix")
    parser.add_argument("--sandbox-drift-detector", action="store_true", help="Run v59.3 sandbox drift detector")
    parser.add_argument("--sandbox-rollback-rehearsal", action="store_true", help="Run v59.4 sandbox rollback rehearsal")
    parser.add_argument("--sandbox-apply-candidate-drafts", action="store_true", help="Run v59.5 sandbox apply candidate drafts")
    parser.add_argument("--sandbox-dashboard-polish", action="store_true", help="Run v59.6 sandbox dashboard polish audit")
    parser.add_argument("--sandbox-api-parity-gate", action="store_true", help="Run v59.7 sandbox/API parity gate")
    parser.add_argument("--sandbox-privacy-package-hardening", action="store_true", help="Run v59.8 sandbox privacy and package hardening")
    parser.add_argument("--pre-v60-source-apply-handoff-gate", action="store_true", help="Run v59.9 pre-v60 source apply handoff gate")
    parser.add_argument("--controlled-sandbox-source-apply-handoff", action="store_true", help="Run v60.0 controlled sandbox-to-source apply handoff preview or record")
    parser.add_argument("--source-apply-handoff-confirm-phrase", default="", help="Exact confirmation phrase for controlled sandbox-to-source apply handoff record")
    parser.add_argument("--record-source-apply-handoff", action="store_true", help="Record v60 source-apply handoff packet only; never applies source")
    parser.add_argument("--source-apply-handoff-receipts", action="store_true", help="Run v60.1 source apply handoff receipts and review console")
    parser.add_argument("--source-baseline-drift-resolver", action="store_true", help="Run v60.2 source baseline drift resolver")
    parser.add_argument("--reviewed-artifact-set-binder", action="store_true", help="Run v60.3 reviewed artifact set binder")
    parser.add_argument("--source-apply-handoff-eligibility", action="store_true", help="Run v60.4 source apply handoff eligibility classifier")
    parser.add_argument("--source-apply-dry-run-bridge", action="store_true", help="Run v60.5 source apply dry-run bridge")
    parser.add_argument("--source-apply-handoff-dashboard-polish", action="store_true", help="Run v60.6 source apply handoff dashboard polish audit")
    parser.add_argument("--source-apply-handoff-api-parity-gate", action="store_true", help="Run v60.7 source apply handoff/API parity gate")
    parser.add_argument("--source-apply-handoff-privacy-hardening", action="store_true", help="Run v60.8 source apply handoff privacy hardening")
    parser.add_argument("--pre-v61-controlled-apply-bridge-gate", action="store_true", help="Run v60.9 pre-v61 controlled apply bridge gate")
    parser.add_argument("--controlled-source-apply-bridge-refinement", action="store_true", help="Run v61.0 controlled source apply bridge refinement")
    parser.add_argument("--source-apply-transaction-planner", action="store_true", help="Run v61.1 source apply transaction planner")
    parser.add_argument("--source-apply-backup-binder", action="store_true", help="Run v61.2 source apply backup binder")
    parser.add_argument("--source-apply-transaction-dry-run-verifier", action="store_true", help="Run v61.3 transaction dry-run verifier")
    parser.add_argument("--source-apply-transaction-confirmation-gate", action="store_true", help="Run v61.4 exact confirmation transaction gate")
    parser.add_argument("--transaction-confirm-phrase", default="", help="Exact confirmation phrase for supervised source apply transactions")
    parser.add_argument("--supervised-source-apply-executor", action="store_true", help="Run v61.5 supervised source apply executor preview")
    parser.add_argument("--approve-source-apply-transaction", action="store_true", help="Request supervised source apply transaction execution; exact phrase still required")
    parser.add_argument("--post-apply-verification-runner", action="store_true", help="Run v61.6 post-apply verification runner")
    parser.add_argument("--transaction-rollback-rehearsal", action="store_true", help="Run v61.7 transaction rollback rehearsal fixture")
    parser.add_argument("--source-apply-transaction-dashboard-command-center", action="store_true", help="Run v61.8 source apply transaction dashboard command center audit")
    parser.add_argument("--pre-v62-transaction-release-gate", action="store_true", help="Run v61.9 pre-v62 transaction release gate")
    parser.add_argument("--supervised-source-apply-transaction-layer", action="store_true", help="Run v62.0 supervised source apply transaction layer")
    parser.add_argument("--transaction-receipt-ledger", action="store_true", help="Run v62.1 transaction receipt ledger")
    parser.add_argument("--transaction-diff-viewer", action="store_true", help="Run v62.2 transaction diff viewer")
    parser.add_argument("--transaction-conflict-detector", action="store_true", help="Run v62.3 transaction conflict detector")
    parser.add_argument("--transaction-approval-record-binder", action="store_true", help="Run v62.4 transaction approval record binder")
    parser.add_argument("--transaction-package-evidence-exporter", action="store_true", help="Run v62.5 transaction package evidence exporter")
    parser.add_argument("--transaction-replay-audit", action="store_true", help="Run v62.6 transaction replay audit")
    parser.add_argument("--transaction-dashboard-receipt-timeline", action="store_true", help="Run v62.7 transaction dashboard receipt timeline")
    parser.add_argument("--transaction-api-search-filtering", action="store_true", help="Run v62.8 transaction API search/filtering")
    parser.add_argument("--transaction-filter-id", default="", help="Filter transaction receipt API search by transaction id fragment")
    parser.add_argument("--transaction-filter-status", default="", help="Filter transaction receipt API search by status")
    parser.add_argument("--transaction-filter-stage", default="", help="Filter transaction receipt API search by stage")
    parser.add_argument("--transaction-filter-file", default="", help="Filter transaction receipt API search by touched file")
    parser.add_argument("--pre-v63-transaction-evidence-gate", action="store_true", help="Run v62.9 pre-v63 transaction evidence gate")
    parser.add_argument("--durable-transaction-evidence-system", action="store_true", help="Run v63.0 durable transaction evidence system")
    parser.add_argument("--transaction-evidence-summarizer", action="store_true", help="Run v63.1 transaction evidence summarizer")
    parser.add_argument("--improvement-candidate-registry", action="store_true", help="Run v63.2 improvement candidate registry")
    parser.add_argument("--evidence-based-candidate-scoring", action="store_true", help="Run v63.3 evidence-based candidate scoring")
    parser.add_argument("--improvement-regression-pattern-detector", action="store_true", help="Run v63.4 regression pattern detector")
    parser.add_argument("--improvement-risk-blast-radius-forecaster", action="store_true", help="Run v63.5 risk and blast-radius forecaster")
    parser.add_argument("--supervised-recommendation-queue", action="store_true", help="Run v63.6 supervised recommendation queue")
    parser.add_argument("--improvement-intelligence-dashboard", action="store_true", help="Run v63.7 improvement intelligence dashboard audit")
    parser.add_argument("--improvement-intelligence-api-cli-access", action="store_true", help="Run v63.8 improvement intelligence API/CLI parity")
    parser.add_argument("--pre-v64-improvement-intelligence-gate", action="store_true", help="Run v63.9 pre-v64 improvement intelligence gate")
    parser.add_argument("--supervised-improvement-intelligence-layer", action="store_true", help="Run v64.0 supervised improvement intelligence layer")
    parser.add_argument("--accepted-recommendation-intake", action="store_true", help="Run v64.1 accepted recommendation intake")
    parser.add_argument("--proposal-draft-skeleton", action="store_true", help="Run v64.2 proposal draft skeleton builder")
    parser.add_argument("--evidence-requirement-mapper", action="store_true", help="Run v64.3 evidence-to-requirement mapper")
    parser.add_argument("--proposal-risk-contract", action="store_true", help="Run v64.4 proposal risk contract")
    parser.add_argument("--sandbox-patch-request-compiler", action="store_true", help="Run v64.5 sandbox patch request compiler")
    parser.add_argument("--proposal-review-packet-binder", action="store_true", help="Run v64.6 proposal review packet binder")
    parser.add_argument("--proposal-dashboard-review-console", action="store_true", help="Run v64.7 proposal dashboard review console audit")
    parser.add_argument("--proposal-api-cli-access", action="store_true", help="Run v64.8 proposal API/CLI parity")
    parser.add_argument("--pre-v65-proposal-drafting-gate", action="store_true", help="Run v64.9 pre-v65 proposal drafting gate")
    parser.add_argument("--recommendation-to-proposal-drafting-layer", action="store_true", help="Run v65.0 recommendation-to-proposal drafting layer")
    parser.add_argument("--reviewed-proposal-acceptance-gate", action="store_true", help="Run v65.1 reviewed proposal acceptance gate")
    parser.add_argument("--sandbox-workspace-plan", action="store_true", help="Run v65.2 sandbox workspace plan builder")
    parser.add_argument("--patch-implementation-request", action="store_true", help="Run v65.3 patch implementation request compiler")
    parser.add_argument("--proposal-sandbox-execution-harness", action="store_true", help="Run v65.4 sandbox execution harness preview")
    parser.add_argument("--proposal-sandbox-execute-copy", action="store_true", help="Exercise v65.4 sandbox copy only; never mutates live source")
    parser.add_argument("--proposal-sandbox-verification-matrix", action="store_true", help="Run v65.5 sandbox verification matrix")
    parser.add_argument("--proposal-sandbox-evidence-binder", action="store_true", help="Run v65.6 sandbox evidence binder")
    parser.add_argument("--proposal-sandbox-failure-triage", action="store_true", help="Run v65.7 sandbox failure triage")
    parser.add_argument("--proposal-sandbox-api-cli-access", action="store_true", help="Run v65.8 proposal sandbox API/CLI parity")
    parser.add_argument("--pre-v66-proposal-sandbox-gate", action="store_true", help="Run v65.9 pre-v66 proposal sandbox gate")
    parser.add_argument("--reviewed-proposal-sandbox-execution-layer", action="store_true", help="Run v66.0 reviewed proposal sandbox execution layer")
    parser.add_argument("--sandbox-promotion-candidate", action="store_true", help="Run v66.1 sandbox promotion candidate builder")
    parser.add_argument("--sandbox-source-diff-normalizer", action="store_true", help="Run v66.2 sandbox-to-source diff normalizer")
    parser.add_argument("--promotion-safety-boundary-gate", action="store_true", help="Run v66.3 promotion safety boundary gate")
    parser.add_argument("--transaction-draft-from-sandbox", action="store_true", help="Run v66.4 transaction draft from sandbox evidence")
    parser.add_argument("--promotion-review-packet-binder", action="store_true", help="Run v66.5 promotion review packet binder")
    parser.add_argument("--promotion-conflict-staleness-detector", action="store_true", help="Run v66.6 promotion conflict and staleness detector")
    parser.add_argument("--sandbox-promotion-api-cli-access", action="store_true", help="Run v66.8 sandbox promotion API/CLI parity")
    parser.add_argument("--pre-v67-sandbox-promotion-gate", action="store_true", help="Run v66.9 pre-v67 sandbox promotion gate")
    parser.add_argument("--sandbox-evidence-promotion-handoff-layer", action="store_true", help="Run v67.0 sandbox evidence promotion handoff layer")
    parser.add_argument("--promotion-packet-intake-gate", action="store_true", help="Run v67.1 promotion packet intake gate")
    parser.add_argument("--transaction-plan-materializer", action="store_true", help="Run v67.2 transaction plan materializer")
    parser.add_argument("--source-baseline-reconciliation", action="store_true", help="Run v67.3 source baseline reconciliation")
    parser.add_argument("--backup-rollback-preflight-binder", action="store_true", help="Run v67.4 backup and rollback preflight binder")
    parser.add_argument("--final-transaction-safety-gate", action="store_true", help="Run v67.5 final transaction safety gate")
    parser.add_argument("--transaction-ledger-preregistration", action="store_true", help="Run v67.6 transaction ledger pre-registration")
    parser.add_argument("--source-transaction-review-console", action="store_true", help="Run v67.7 source transaction review console audit")
    parser.add_argument("--transaction-review-api-cli-access", action="store_true", help="Run v67.8 transaction review API/CLI parity")
    parser.add_argument("--pre-v68-transaction-integration-gate", action="store_true", help="Run v67.9 pre-v68 transaction integration gate")
    parser.add_argument("--promotion-to-transaction-integration-layer", action="store_true", help="Run v68.0 promotion-to-transaction integration layer")
    parser.add_argument("--transaction-execution-eligibility", action="store_true", help="Run v68.1 transaction execution eligibility resolver")
    parser.add_argument("--exact-confirmation-binder", action="store_true", help="Run v68.2 exact confirmation binder")
    parser.add_argument("--backup-snapshot-materializer", action="store_true", help="Run v68.3 backup snapshot materializer")
    parser.add_argument("--transaction-apply-rehearsal", action="store_true", help="Run v68.4 transaction apply rehearsal")
    parser.add_argument("--operator-confirmed-apply-executor", action="store_true", help="Run v68.5 operator-confirmed apply executor guard")
    parser.add_argument("--post-execution-verification", action="store_true", help="Run v68.6 post-execution verification planner")
    parser.add_argument("--rollback-recommendation-gate", action="store_true", help="Run v68.7 rollback recommendation gate")
    parser.add_argument("--transaction-execution-dashboard-api-cli", action="store_true", help="Run v68.8 transaction execution dashboard/API/CLI parity")
    parser.add_argument("--pre-v69-execution-gate", action="store_true", help="Run v68.9 pre-v69 execution gate")
    parser.add_argument("--operator-confirmed-transaction-execution-layer", action="store_true", help="Run v69.0 operator-confirmed transaction execution layer")
    parser.add_argument("--execution-result-ledger-finalizer", action="store_true", help="Run v69.1 execution result ledger finalizer")
    parser.add_argument("--rollback-decision-resolver", action="store_true", help="Run v69.2 rollback decision resolver")
    parser.add_argument("--operator-confirmed-rollback-executor", action="store_true", help="Run v69.3 operator-confirmed rollback executor guard")
    parser.add_argument("--rollback-confirm-phrase", default="", help="Exact rollback confirmation phrase for guarded rollback execution")
    parser.add_argument("--post-rollback-verification", action="store_true", help="Run v69.4 post-rollback verification runner")
    parser.add_argument("--release-candidate-finalization-gate", action="store_true", help="Run v69.5 release candidate finalization gate")
    parser.add_argument("--source-only-package-certifier", action="store_true", help="Run v69.6 source-only package certifier")
    parser.add_argument("--release-finalization-dashboard-api-cli", action="store_true", help="Run v69.7 release finalization dashboard/API/CLI parity")
    parser.add_argument("--recovery-simulation-harness", action="store_true", help="Run v69.8 recovery simulation harness")
    parser.add_argument("--pre-v70-recovery-finalization-gate", action="store_true", help="Run v69.9 pre-v70 recovery and finalization gate")
    parser.add_argument("--verified-execution-recovery-release-layer", action="store_true", help="Run v70.0 verified execution recovery and release finalization layer")
    parser.add_argument("--source-tree-inventory", action="store_true", help="Run v70.1 source tree inventory builder")
    parser.add_argument("--module-responsibility-map", action="store_true", help="Run v70.2 module responsibility classifier")
    parser.add_argument("--dependency-call-surface-map", action="store_true", help="Run v70.3 dependency and call surface mapper")
    parser.add_argument("--module-risk-profile", action="store_true", help="Run v70.4 module risk profile builder")
    parser.add_argument("--historical-failure-memory", action="store_true", help="Run v70.5 historical failure memory binder")
    parser.add_argument("--verification-command-map", action="store_true", help="Run v70.6 verification command mapper")
    parser.add_argument("--improvement-opportunity-detector", action="store_true", help="Run v70.7 improvement opportunity detector")
    parser.add_argument("--codebase-understanding-dashboard-api-cli", action="store_true", help="Run v70.8 codebase understanding dashboard/API/CLI parity")
    parser.add_argument("--pre-v71-codebase-understanding-gate", action="store_true", help="Run v70.9 pre-v71 codebase understanding gate")
    parser.add_argument("--codebase-understanding-map", action="store_true", help="Run v71.0 codebase understanding map")
    parser.add_argument("--patch-goal-intake-classifier", action="store_true", help="Run v71.1 patch goal intake classifier")
    parser.add_argument("--relevant-file-context-selector", action="store_true", help="Run v71.2 relevant file context selector")
    parser.add_argument("--historical-failure-context-binder", action="store_true", help="Run v71.3 historical failure context binder")
    parser.add_argument("--risk-aware-context-budgeter", action="store_true", help="Run v71.4 risk-aware context budgeter")
    parser.add_argument("--verification-requirement-compiler", action="store_true", help="Run v71.5 verification requirement compiler")
    parser.add_argument("--patch-prompt-context-packet-builder", action="store_true", help="Run v71.6 patch prompt context packet builder")
    parser.add_argument("--context-completeness-reviewer", action="store_true", help="Run v71.7 context completeness reviewer")
    parser.add_argument("--patch-context-dashboard-api-cli", action="store_true", help="Run v71.8 patch context dashboard/API/CLI parity")
    parser.add_argument("--pre-v72-patch-context-gate", action="store_true", help="Run v71.9 pre-v72 patch context gate")
    parser.add_argument("--patch-generation-context-builder", action="store_true", help="Run v72.0 patch generation context builder")
    parser.add_argument("--patch-intent-normalizer", action="store_true", help="Run v72.1 patch intent normalizer")
    parser.add_argument("--patch-scope-contract-builder", action="store_true", help="Run v72.2 patch scope contract builder")
    parser.add_argument("--patch-prompt-composer", action="store_true", help="Run v72.3 patch prompt composer")
    parser.add_argument("--patch-draft-output-schema", action="store_true", help="Run v72.4 patch draft output schema")
    parser.add_argument("--patch-draft-safety-reviewer", action="store_true", help="Run v72.5 patch draft safety reviewer")
    parser.add_argument("--patch-draft-evidence-binder", action="store_true", help="Run v72.6 patch draft evidence binder")
    parser.add_argument("--patch-draft-dashboard-api-cli", action="store_true", help="Run v72.7 patch draft dashboard/API/CLI parity")
    parser.add_argument("--local-model-handoff-stub", action="store_true", help="Run v72.8 local model handoff stub")
    parser.add_argument("--pre-v73-patch-draft-gate", action="store_true", help="Run v72.9 pre-v73 patch draft gate")
    parser.add_argument("--supervised-patch-draft-composer", action="store_true", help="Run v73.0 supervised patch draft composer")
    parser.add_argument("--patch-review-intake", action="store_true", help="Run v73.1 patch draft intake parser")
    parser.add_argument("--patch-review-diff-boundary", action="store_true", help="Run v73.2 diff boundary extractor")
    parser.add_argument("--patch-review-scope", action="store_true", help="Run v73.3 scope contract validator")
    parser.add_argument("--patch-review-safety", action="store_true", help="Run v73.4 safety boundary validator")
    parser.add_argument("--patch-review-docs", action="store_true", help="Run v73.5 documentation update validator")
    parser.add_argument("--patch-review-verification", action="store_true", help="Run v73.6 verification plan validator")
    parser.add_argument("--patch-review-risk", action="store_true", help="Run v73.7 patch risk scorer")
    parser.add_argument("--patch-review-report", action="store_true", help="Run v73.8 patch review report builder")
    parser.add_argument("--patch-review-dashboard-api-cli", action="store_true", help="Run v73.9 patch review dashboard/API/CLI parity")
    parser.add_argument("--pre-v74-patch-review-gate", action="store_true", help="Run v73.9 pre-v74 patch review gate")
    parser.add_argument("--patch-draft-review-diff-validation-layer", action="store_true", help="Run v74.0 patch draft review and diff validation layer")
    parser.add_argument("--patch-trial-intake", action="store_true", help="Run v74.1 sandbox trial intake binder")
    parser.add_argument("--patch-trial-workspace", action="store_true", help="Run v74.2 disposable workspace builder")
    parser.add_argument("--patch-trial-materialize", action="store_true", help="Run v74.3 patch draft materializer inside sandbox")
    parser.add_argument("--patch-trial-verify", action="store_true", help="Run v74.4 sandbox verification runner")
    parser.add_argument("--patch-trial-evidence", action="store_true", help="Run v74.5 sandbox evidence collector")
    parser.add_argument("--patch-trial-escape-guard", action="store_true", help="Run v74.6 sandbox escape/mutation guard")
    parser.add_argument("--patch-trial-dashboard-api-cli", action="store_true", help="Run v74.7 patch trial dashboard/API/CLI parity")
    parser.add_argument("--patch-trial-cleanup", action="store_true", help="Run v74.8 patch trial cleanup retention policy and prune old trials")
    parser.add_argument("--patch-trial-list", action="store_true", help="List retained v75 patch trial sandboxes without deleting them")
    parser.add_argument("--pre-v75-sandbox-trial-gate", action="store_true", help="Run v74.9 pre-v75 sandbox trial gate")
    parser.add_argument("--sandbox-patch-trial-runner", action="store_true", help="Run v75.0 sandbox patch trial runner")
    parser.add_argument("--patch-evidence-intake", action="store_true", help="Run v75.1 sandbox evidence intake reader")
    parser.add_argument("--patch-evidence-integrity", action="store_true", help="Run v75.2 trial integrity validator")
    parser.add_argument("--patch-evidence-verification", action="store_true", help="Run v75.3 verification evidence scorer")
    parser.add_argument("--patch-evidence-scope-docs", action="store_true", help="Run v75.4 scope and documentation evidence reviewer")
    parser.add_argument("--patch-evidence-risk", action="store_true", help="Run v75.5 risk acceptance classifier")
    parser.add_argument("--patch-evidence-readiness", action="store_true", help="Run v75.6 promotion readiness packet builder")
    parser.add_argument("--patch-evidence-dashboard-api-cli", action="store_true", help="Run v75.7 patch evidence dashboard/API/CLI parity")
    parser.add_argument("--patch-evidence-archive", action="store_true", help="Run v75.8 recommendation archive and comparison")
    parser.add_argument("--pre-v76-evidence-review-gate", action="store_true", help="Run v75.9 pre-v76 evidence review gate")
    parser.add_argument("--sandbox-evidence-review-recommendation-layer", action="store_true", help="Run v76.0 sandbox evidence review and promotion recommendation layer")
    parser.add_argument("--patch-apply-approval", action="store_true", help="Run v76.1 approval intake contract")
    parser.add_argument("--patch-apply-bind", action="store_true", help="Run v76.2 recommendation-to-approval binder")
    parser.add_argument("--patch-apply-snapshot", action="store_true", help="Run v76.3 live source snapshot builder")
    parser.add_argument("--patch-apply-materialize", action="store_true", help="Run v76.4 approved patch materializer")
    parser.add_argument("--patch-apply-verify", action="store_true", help="Run v76.5 post-apply verification runner")
    parser.add_argument("--patch-apply-rollback", action="store_true", help="Run v76.6 automatic rollback executor")
    parser.add_argument("--patch-apply-evidence", action="store_true", help="Run v76.7 application evidence recorder")
    parser.add_argument("--patch-application-dashboard-api-cli", action="store_true", help="Run v76.8 patch application dashboard/API/CLI parity")
    parser.add_argument("--pre-v77-application-gate", action="store_true", help="Run v76.9 pre-v77 application gate")
    parser.add_argument("--operator-approved-patch-application-layer", action="store_true", help="Run v77.0 operator-approved patch application layer")
    parser.add_argument("--patch-recovery-preflight", action="store_true", help="Run v77.1 dirty tree preflight detector")
    parser.add_argument("--patch-recovery-snapshot", action="store_true", help="Run v77.2 snapshot completeness validator")
    parser.add_argument("--patch-recovery-partial-apply", action="store_true", help="Run v77.3 partial apply detector")
    parser.add_argument("--patch-recovery-rollback-integrity", action="store_true", help="Run v77.4 rollback integrity verifier")
    parser.add_argument("--patch-recovery-triage", action="store_true", help="Run v77.5 failed verification triage")
    parser.add_argument("--patch-recovery-recommendation", action="store_true", help="Run v77.6 recovery recommendation builder")
    parser.add_argument("--patch-recovery-timeline", action="store_true", help="Run v77.7 application audit timeline")
    parser.add_argument("--patch-recovery-dashboard-api-cli", action="store_true", help="Run v77.8 patch recovery dashboard/API/CLI parity")
    parser.add_argument("--pre-v78-recovery-gate", action="store_true", help="Run v77.9 pre-v78 recovery gate")
    parser.add_argument("--verified-application-recovery-rollback-hardening", action="store_true", help="Run v78.0 verified application recovery and rollback hardening layer")
    parser.add_argument("--patch-queue-schema", action="store_true", help="Run v78.1 patch queue record schema")
    parser.add_argument("--patch-queue-intake", action="store_true", help="Run v78.2 patch queue intake organizer")
    parser.add_argument("--patch-queue-conflicts", action="store_true", help="Run v78.3 patch queue conflict detector")
    parser.add_argument("--patch-queue-priority", action="store_true", help="Run v78.4 patch queue risk priority scheduler")
    parser.add_argument("--patch-queue-stale-evidence", action="store_true", help="Run v78.5 patch queue stale evidence detector")
    parser.add_argument("--patch-queue-serial-plan", action="store_true", help="Run v78.6 patch queue serial trial plan builder")
    parser.add_argument("--patch-queue-review-packet", action="store_true", help="Run v78.7 patch queue operator review packet")
    parser.add_argument("--patch-queue-dashboard-api-cli", action="store_true", help="Run v78.8 patch queue dashboard/API/CLI parity")
    parser.add_argument("--pre-v79-queue-gate", action="store_true", help="Run v78.9 pre-v79 queue gate")
    parser.add_argument("--multi-patch-queue-planning-layer", action="store_true", help="Run v79.0 multi-patch queue planning layer")
    parser.add_argument("--patch-apply-approved", action="store_true", help="Explicitly request approved patch application; still requires exact --approval-phrase")
    parser.add_argument("--patch-apply-live", action="store_true", help="Allow live source materialization after exact approval; omitted means dry-run")
    parser.add_argument("--approval-phrase", type=str, default=None, help="Exact v77 approval phrase, required as APPROVE PATCH APPLICATION for live patch application")
    parser.add_argument("--patch-approval-file", type=str, default=None, help="Optional JSON approval contract file for v77 patch application")
    parser.add_argument("--patch-approved-files", type=str, default=None, help="Optional comma-separated approved file scope for v77 patch application")
    parser.add_argument("--patch-application-id", type=str, default=None, help="Optional stable v77 patch application id")
    parser.add_argument("--patch-queue-file", type=str, default=None, help="Optional JSON file containing queued patch records for v79 planning")
    parser.add_argument("--patch-queue-id", type=str, default=None, help="Optional stable v79 patch queue id")
    parser.add_argument("--improvement-opportunity-intake", action="store_true", help="Run v79.1 improvement opportunity intake")
    parser.add_argument("--improvement-cycle-state-machine", action="store_true", help="Run v79.2 improvement cycle state machine")
    parser.add_argument("--pipeline-stage-binder", action="store_true", help="Run v79.3 pipeline stage binder")
    parser.add_argument("--local-model-invocation-stub", action="store_true", help="Run v79.4 local model invocation stub")
    parser.add_argument("--improvement-loop-evidence-recorder", action="store_true", help="Run v79.5 improvement loop evidence recorder")
    parser.add_argument("--operator-stop-gate", action="store_true", help="Run v79.6 operator stop gate")
    parser.add_argument("--improvement-loop-dashboard-api-cli", action="store_true", help="Run v79.7 improvement loop dashboard/api/cli")
    parser.add_argument("--loop-safety-auditor", action="store_true", help="Run v79.8 loop safety auditor")
    parser.add_argument("--pre-v80-supervised-loop-gate", action="store_true", help="Run v79.9 pre-v80 supervised loop gate")
    parser.add_argument("--supervised-local-improvement-loop", action="store_true", help="Run v80.0 supervised local improvement loop")
    parser.add_argument("--local-model-adapter-contract", action="store_true", help="Run v80.1 local model adapter contract")
    parser.add_argument("--model-capability-profile", action="store_true", help="Run v80.2 model capability profile")
    parser.add_argument("--prompt-export-invocation-guard", action="store_true", help="Run v80.3 prompt export and invocation guard")
    parser.add_argument("--proposal-capture-parser", action="store_true", help="Run v80.4 proposal capture parser")
    parser.add_argument("--proposal-safety-precheck", action="store_true", help="Run v80.5 proposal safety precheck")
    parser.add_argument("--model-output-provenance-recorder", action="store_true", help="Run v80.6 model output provenance recorder")
    parser.add_argument("--proposal-integration-dashboard-api-cli", action="store_true", help="Run v80.7 proposal integration dashboard/api/cli")
    parser.add_argument("--disabled-by-default-invocation-gate", action="store_true", help="Run v80.8 disabled-by-default invocation gate")
    parser.add_argument("--pre-v81-model-integration-gate", action="store_true", help="Run v80.9 pre-v81 model integration gate")
    parser.add_argument("--local-model-patch-proposal-integration", action="store_true", help="Run v81.0 local model patch proposal integration")
    parser.add_argument("--proposal-collection-intake", action="store_true", help="Run v81.1 proposal collection intake")
    parser.add_argument("--candidate-diff-normalizer", action="store_true", help="Run v81.2 candidate diff normalizer")
    parser.add_argument("--proposal-quality-heuristic-scorer", action="store_true", help="Run v81.3 proposal quality heuristic scorer")
    parser.add_argument("--safety-scope-comparison", action="store_true", help="Run v81.4 safety and scope comparison")
    parser.add_argument("--verification-plan-comparison", action="store_true", help="Run v81.5 verification plan comparison")
    parser.add_argument("--critique-report-builder", action="store_true", help="Run v81.6 critique report builder")
    parser.add_argument("--critique-dashboard-api-cli", action="store_true", help="Run v81.7 critique dashboard/api/cli")
    parser.add_argument("--operator-review-bundle-exporter", action="store_true", help="Run v81.8 operator review bundle exporter")
    parser.add_argument("--pre-v82-output-critique-gate", action="store_true", help="Run v81.9 pre-v82 output critique gate")
    parser.add_argument("--local-model-output-comparison-critique", action="store_true", help="Run v82.0 local model output comparison and critique")
    parser.add_argument("--candidate-registry-schema", action="store_true", help="Run v82.1 candidate registry schema")
    parser.add_argument("--candidate-deduplication", action="store_true", help="Run v82.2 candidate deduplication")
    parser.add_argument("--risk-weighted-ranking", action="store_true", help="Run v82.3 risk-weighted ranking")
    parser.add_argument("--conflict-aware-grouping", action="store_true", help="Run v82.4 conflict-aware grouping")
    parser.add_argument("--evidence-completeness-ranker", action="store_true", help="Run v82.5 evidence completeness ranker")
    parser.add_argument("--ranking-explainer", action="store_true", help="Run v82.6 ranking explainer")
    parser.add_argument("--ranking-dashboard-api-cli", action="store_true", help="Run v82.7 ranking dashboard/api/cli")
    parser.add_argument("--operator-selection-packet", action="store_true", help="Run v82.8 operator selection packet")
    parser.add_argument("--pre-v83-ranking-gate", action="store_true", help="Run v82.9 pre-v83 ranking gate")
    parser.add_argument("--multi-model-patch-candidate-ranking", action="store_true", help="Run v83.0 multi-model patch candidate ranking")
    parser.add_argument("--refinement-goal-binder", action="store_true", help="Run v83.1 refinement goal binder")
    parser.add_argument("--critique-revision-prompt-builder", action="store_true", help="Run v83.2 critique-to-revision prompt builder")
    parser.add_argument("--constrained-revision-scope-builder", action="store_true", help="Run v83.3 constrained revision scope builder")
    parser.add_argument("--refinement-safety-reviewer", action="store_true", help="Run v83.4 refinement safety reviewer")
    parser.add_argument("--refinement-evidence-recorder", action="store_true", help="Run v83.5 refinement evidence recorder")
    parser.add_argument("--refinement-iteration-limiter", action="store_true", help="Run v83.6 refinement iteration limiter")
    parser.add_argument("--refinement-dashboard-api-cli", action="store_true", help="Run v83.7 refinement dashboard/api/cli")
    parser.add_argument("--operator-revision-packet", action="store_true", help="Run v83.8 operator revision packet")
    parser.add_argument("--pre-v84-refinement-gate", action="store_true", help="Run v83.9 pre-v84 refinement gate")
    parser.add_argument("--supervised-patch-candidate-refinement", action="store_true", help="Run v84.0 supervised patch candidate refinement")
    parser.add_argument("--suggestion-source-intake", action="store_true", help="Run v84.1 suggestion source intake")
    parser.add_argument("--suggestion-cycle-state-machine", action="store_true", help="Run v84.2 suggestion cycle state machine")
    parser.add_argument("--recurring-suggestion-budgeter", action="store_true", help="Run v84.3 recurring suggestion budgeter")
    parser.add_argument("--safety-boundary-enforcer", action="store_true", help="Run v84.4 safety boundary enforcer")
    parser.add_argument("--suggestion-deduplication-memory", action="store_true", help="Run v84.5 suggestion deduplication memory")
    parser.add_argument("--operator-attention-packet", action="store_true", help="Run v84.6 operator attention packet")
    parser.add_argument("--suggestion-loop-dashboard-api-cli", action="store_true", help="Run v84.7 suggestion loop dashboard/api/cli")
    parser.add_argument("--no-autonomous-apply-auditor", action="store_true", help="Run v84.8 no-autonomous-apply auditor")
    parser.add_argument("--pre-v85-suggestion-loop-gate", action="store_true", help="Run v84.9 pre-v85 suggestion loop gate")
    parser.add_argument("--safe-autonomous-suggestion-loop", action="store_true", help="Run v85.0 safe autonomous suggestion loop")
    parser.add_argument("--suggestion-inbox-record-schema", action="store_true", help="Run v85.1 suggestion inbox record schema")
    parser.add_argument("--suggestion-intake-normalizer", action="store_true", help="Run v85.2 suggestion intake normalizer")
    parser.add_argument("--suggestion-deduplication-drift-resolver", action="store_true", help="Run v85.3 suggestion deduplication and drift resolver")
    parser.add_argument("--operator-triage-state-machine", action="store_true", help="Run v85.4 operator triage state machine")
    parser.add_argument("--work-order-draft-builder", action="store_true", help="Run v85.5 work order draft builder")
    parser.add_argument("--safety-scope-contract-binder", action="store_true", help="Run v85.6 safety and scope contract binder")
    parser.add_argument("--pipeline-handoff-planner", action="store_true", help="Run v85.7 pipeline handoff planner")
    parser.add_argument("--suggestion-inbox-dashboard-api-cli", action="store_true", help="Run v85.8 suggestion inbox dashboard/api/cli")
    parser.add_argument("--pre-v86-suggestion-inbox-gate", action="store_true", help="Run v85.9 pre-v86 suggestion inbox gate")
    parser.add_argument("--supervised-suggestion-inbox-work-order-planner", action="store_true", help="Run v86.0 supervised suggestion inbox and work order planner")
    parser.add_argument("--work-order-context-schema", action="store_true", help="Run v86.1 work order context schema")
    parser.add_argument("--patch-context-preflight-validator", action="store_true", help="Run v86.2 patch context preflight validator")
    parser.add_argument("--source-impact-mapper", action="store_true", help="Run v86.3 source impact mapper")
    parser.add_argument("--handoff-packet-builder", action="store_true", help="Run v86.4 handoff packet builder")
    parser.add_argument("--patch-context-risk-classifier", action="store_true", help="Run v86.5 patch context risk classifier")
    parser.add_argument("--context-to-draft-compatibility-layer", action="store_true", help="Run v86.6 context-to-draft compatibility layer")
    parser.add_argument("--handoff-dashboard-api-cli-coverage", action="store_true", help="Run v86.7 handoff dashboard/api/cli coverage")
    parser.add_argument("--handoff-parity-privacy-gate", action="store_true", help="Run v86.8 handoff parity and privacy gate")
    parser.add_argument("--pre-v87-integration-gate", action="store_true", help="Run v86.9 pre-v87 integration gate")
    parser.add_argument("--work-order-to-patch-context-handoff", action="store_true", help="Run v87.0 work order to patch context handoff")
    parser.add_argument("--execution-evidence-schema", action="store_true", help="Run v87.1 execution evidence schema")
    parser.add_argument("--patch-attempt-linker", action="store_true", help="Run v87.2 patch attempt linker")
    parser.add_argument("--sandbox-evidence-binder", action="store_true", help="Run v87.3 sandbox evidence binder")
    parser.add_argument("--review-decision-ledger", action="store_true", help="Run v87.4 review decision ledger")
    parser.add_argument("--regression-drift-tracker", action="store_true", help="Run v87.5 regression and drift tracker")
    parser.add_argument("--evidence-summary-builder", action="store_true", help="Run v87.6 evidence summary builder")
    parser.add_argument("--evidence-dashboard-api-cli-coverage", action="store_true", help="Run v87.7 evidence dashboard/api/cli coverage")
    parser.add_argument("--evidence-privacy-safety-gate", action="store_true", help="Run v87.8 evidence privacy and safety gate")
    parser.add_argument("--pre-v88-integration-gate", action="store_true", help="Run v87.9 pre-v88 integration gate")
    parser.add_argument("--work-order-execution-evidence-binder", action="store_true", help="Run v88.0 work order execution evidence binder")
    parser.add_argument("--dashboard-route-inventory", action="store_true", help="Run v88.1 dashboard route inventory")
    parser.add_argument("--navigation-grouping-model", action="store_true", help="Run v88.2 navigation grouping model")
    parser.add_argument("--self-development-console-page", action="store_true", help="Run v88.3 self-development console page")
    parser.add_argument("--operator-action-queue", action="store_true", help="Run v88.4 operator action queue")
    parser.add_argument("--dashboard-performance-pass", action="store_true", help="Run v88.5 performance")
    parser.add_argument("--dashboard-safety-banner-system", action="store_true", help="Run v88.6 safety-banners")
    parser.add_argument("--dashboard-api-cli-console-parity", action="store_true", help="Run v88.7 console dashboard/api/cli parity")
    parser.add_argument("--tooltip-regression-ux-gate", action="store_true", help="Run v88.8 tooltip regression and ux gate")
    parser.add_argument("--pre-v89-integration-gate", action="store_true", help="Run v88.9 pre-v89 integration gate")
    parser.add_argument("--self-development-dashboard-consolidation", action="store_true", help="Run v89.0 self-development dashboard consolidation")
    parser.add_argument("--readiness-audit-schema", action="store_true", help="Run v89.1 readiness audit schema")
    parser.add_argument("--capability-boundary-scanner", action="store_true", help="Run v89.2 capability boundary scanner")
    parser.add_argument("--approval-gate-integrity-audit", action="store_true", help="Run v89.3 approval gate integrity audit")
    parser.add_argument("--evidence-traceability-audit", action="store_true", help="Run v89.4 evidence traceability audit")
    parser.add_argument("--verification-coverage-audit", action="store_true", help="Run v89.5 verification coverage audit")
    parser.add_argument("--autonomy-risk-register", action="store_true", help="Run v89.6 autonomy risk register")
    parser.add_argument("--readiness-scorecard-builder", action="store_true", help="Run v89.7 readiness scorecard builder")
    parser.add_argument("--readiness-audit-dashboard-api-cli-coverage", action="store_true", help="Run v89.8 readiness audit dashboard/api/cli coverage")
    parser.add_argument("--pre-v90-final-governance-gate", action="store_true", help="Run v89.9 pre-v90 final governance gate")
    parser.add_argument("--supervised-self-development-readiness-audit", action="store_true", help="Run v90.0 supervised self-development readiness audit")
    for _flag_name, _slug in getattr(sm_v90, "SUPERVISED_RUNTIME_CLI_MAP", {}).items():
        _definition = sm_v90.SUPERVISED_RUNTIME_STAGE_BY_SLUG[_slug]
        parser.add_argument(f"--{_flag_name}", action="store_true", help=f"Run {_definition['stage']} {_definition['label'].lower()}")
    # v90.1-v95.0 supervised runtime CLI flags intentionally registered dynamically and listed for parity checks: --development-session-schema --session-creation-planner --session-scope-binder --session-state-machine --session-linkage-builder --session-summary-builder --session-dashboard-api-cli-coverage --session-privacy-safety-gate --pre-v91-integration-gate --supervised-development-session-manager --approval-request-schema --approval-queue-builder --approval-decision-ledger --approval-dependency-resolver --approval-risk-explainer --approval-reversal-audit-trail --approval-console-dashboard-api-cli --approval-safety-gate --pre-v92-integration-gate --operator-approval-workflow-console --experiment-branch-schema --experiment-eligibility-checker --experiment-plan-builder --sandbox-workspace-allocator --experiment-evidence-contract --experiment-promotion-blocker --experiment-dashboard-api-cli-coverage --experiment-privacy-safety-gate --pre-v93-integration-gate --safe-experiment-branch-planner --outcome-reflection-schema --completion-outcome-classifier --evidence-to-lesson-extractor --recurring-issue-detector --reflection-safety-filter --reflection-to-suggestion-handoff --reflection-dashboard-api-cli-coverage --reflection-privacy-containment-gate --pre-v94-integration-gate --learning-from-outcome-reflection-layer --improvement-cycle-schema --cycle-stage-resolver --cycle-blocker-detector --cycle-next-step-recommender --cycle-timeline-builder --cycle-governance-gate --cycle-dashboard-api-cli-coverage --cycle-privacy-package-gate --pre-v95-integration-gate --supervised-improvement-cycle-orchestrator
    # v95.1-v100.0 governed simulation CLI flags intentionally registered dynamically and listed for parity checks: --replay-record-schema --synthetic-cycle-fixture-builder --replay-runner --expected-decision-comparator --benchmark-scoring-model --regression-benchmark-set --replay-dashboard-api-cli-coverage --replay-safety-privacy-gate --pre-v96-integration-gate --supervised-cycle-replay-benchmark-harness --capability-ledger-schema --default-capability-policy-builder --capability-request-classifier --capability-budget-tracker --permission-conflict-detector --denial-reason-builder --permission-ledger-dashboard-api-cli-coverage --capability-safety-gate --pre-v97-integration-gate --capability-permission-budget-ledger --shadow-simulation-schema --autonomous-intention-simulator --action-shadowing-engine --simulation-to-approval-request-mapper --unsafe-simulation-detector --shadow-plan-comparator --shadow-simulation-dashboard-api-cli-coverage --simulation-containment-gate --pre-v98-integration-gate --shadow-autonomy-simulation-layer --failure-scenario-schema --known-failure-scenario-builder --recovery-path-planner --rollback-readiness-checker --failure-containment-simulator --recovery-evidence-binder --war-game-dashboard-api-cli-coverage --failure-safety-privacy-gate --pre-v99-integration-gate --failure-recovery-rollback-war-game-layer --mind-milestone-audit-schema --architecture-coherence-mapper --identity-memory-boundary-audit --goal-motivation-audit --self-development-maturity-scorecard --human-operator-burden-review --v100-milestone-dashboard-api-cli-coverage --v100-governance-autonomy-boundary-gate --pre-v100-final-integration-gate --local-artificial-mind-milestone-audit
    # v120.1-v125.0 supervised development learning CLI flags intentionally registered dynamically and listed for parity checks: --session-outcome-collector --planned-vs-actual-comparator --missed-surface-detector --unexpected-change-detector --verification-accuracy-scorer --operator-burden-result-tracker --outcome-review-binder --development-outcome-review-dashboard-api-cli --pre-v121-outcome-review-gate --development-outcome-review-layer --lesson-candidate-schema --bug-pattern-extractor --successful-pattern-extractor --false-alarm-detector --lesson-usefulness-scorer --memory-mutation-boundary-check --operator-lesson-review-packet --lesson-extraction-dashboard-api-cli --pre-v122-lesson-extraction-gate --supervised-lesson-extraction-layer --recommendation-history-schema --recommendation-accuracy-scorer --repeated-mistake-detector --recommendation-noise-reducer --future-recommendation-adjuster --safety-aware-recommendation-filter --recommendation-refinement-binder --recommendation-refinement-dashboard-api-cli --pre-v123-recommendation-refinement-gate --recommendation-refinement-layer --feedback-capture-schema --standing-rule-detector --temporary-preference-detector --contradictory-feedback-detector --feedback-to-work-package-linker --feedback-review-packet-builder --feedback-safety-boundary-gate --operator-feedback-integration-dashboard-api-cli --pre-v124-feedback-gate --operator-feedback-integration-layer --end-to-end-learning-walkthrough --lesson-quality-audit --recommendation-improvement-audit --feedback-handling-audit --learning-memory-boundary-audit --learning-safety-regression-audit --learning-operator-burden-audit --development-learning-dashboard-api-cli --pre-v125-learning-audit-gate --supervised-development-learning-audit
    # v115.1-v120.0 supervised development execution CLI flags intentionally registered dynamically and listed for parity checks: --session-intent-collector --session-scope-builder --file-impact-predictor --test-target-planner --documentation-task-planner --safety-boundary-planner --operator-decision-checklist --development-session-planner-dashboard-api-cli --pre-v116-session-planner-gate --development-session-planner --source-surface-inventory --route-api-cli-link-mapper --builder-function-dependency-mapper --documentation-link-mapper --smoke-coverage-mapper --fragile-surface-detector --change-cartography-report --source-cartographer-dashboard-api-cli --pre-v117-source-cartographer-gate --source-change-cartographer --patch-simulation-schema --expected-diff-planner --missing-change-detector --overreach-detector --safety-regression-prediction --verification-prediction-binder --dry-run-review-summary --patch-simulation-dashboard-api-cli --pre-v118-patch-simulation-gate --patch-simulation-dry-run-review-layer --verification-matrix-schema --dashboard-regression-matrix --api-cli-regression-matrix --packaging-regression-matrix --safety-regression-matrix --documentation-regression-matrix --verification-recommendation-builder --verification-matrix-dashboard-api-cli --pre-v119-verification-matrix-gate --verification-matrix-regression-memory-layer --end-to-end-session-walkthrough --execution-operator-burden-audit --patch-planning-quality-audit --execution-verification-coverage-audit --execution-safety-containment-audit --execution-dashboard-sprawl-audit --execution-documentation-continuity-audit --development-execution-dashboard-api-cli --pre-v120-execution-audit-gate --supervised-development-execution-audit
    # v110.1-v115.0 supervised self-development CLI flags intentionally registered dynamically and listed for parity checks: --improvement-intent-inventory --problem-statement-builder --evidence-requirement-classifier --impact-scope-estimator --operator-value-scorer --safety-sensitivity-classifier --improvement-intent-binder --improvement-intent-dashboard-api-cli --pre-v111-improvement-intent-gate --improvement-intent-problem-framing-layer --work-package-schema --change-boundary-mapper --acceptance-criteria-builder --test-plan-builder --documentation-obligation-tracker --regression-risk-mapper --work-package-review-packet --work-package-dashboard-api-cli --pre-v112-work-package-gate --supervised-work-package-builder --patch-readiness-schema --patch-diff-expectation-builder --patch-completeness-checker --patch-contradiction-scanner --patch-safety-regression-scanner --dashboard-regression-scanner --patch-review-summary-builder --patch-readiness-dashboard-api-cli --pre-v113-patch-readiness-gate --patch-readiness-review-intelligence-layer --release-candidate-schema --version-consistency-auditor --route-api-cli-parity-auditor --documentation-completeness-auditor --package-privacy-auditor-upgrade --install-layer-verification-binder --release-recommendation-builder --release-judgment-dashboard-api-cli --pre-v114-release-judgment-gate --release-candidate-judgment-layer --end-to-end-improvement-walkthrough --self-development-operator-burden-audit --self-development-safety-boundary-audit --evidence-quality-audit --decision-trace-audit --self-development-dashboard-usability-audit --self-development-release-process-audit --self-development-readiness-dashboard-api-cli --pre-v115-milestone-gate --supervised-self-development-readiness
    # v105.1-v110.0 practical coherence CLI flags intentionally registered dynamically and listed for parity checks: --memory-source-inventory --memory-freshness-classifier --memory-duplicate-conflict-detector --memory-evidence-link-builder --memory-relevance-scorer --memory-correction-draft-builder --memory-quality-dashboard-api-cli --memory-privacy-mutation-boundary-gate --pre-v106-memory-quality-gate --memory-quality-evidence-hygiene-layer --goal-inventory-normalizer --goal-lifecycle-classifier --goal-evidence-linker --priority-stability-scorer --blocked-goal-resolver --goal-contradiction-scanner --goal-continuity-summary-builder --goal-continuity-dashboard-api-cli --pre-v107-goal-continuity-gate --goal-continuity-priority-stability-layer --reasoning-task-schema --context-pack-builder --local-model-permission-gate --manual-output-capture-layer --reasoning-quality-rubric --hallucination-boundary-scanner --reasoning-evidence-binder --reasoning-workbench-dashboard-api-cli --pre-v108-reasoning-containment-gate --contained-local-reasoning-workbench --workflow-friction-inventory-refresh --unified-operator-action-queue --copy-safe-command-builder --review-packet-shortcut-builder --dashboard-consolidation-recommendations --lazy-diagnostics-loader-plan --tooltip-nav-safety-review --workflow-console-dashboard-api-cli --pre-v109-workflow-gate --operator-workflow-compression-console --end-to-end-daily-use-walkthrough --memory-usefulness-audit --goal-stability-audit --reasoning-workbench-usefulness-audit --operator-burden-scorecard --dashboard-performance-sprawl-review --safety-boundary-regression-audit --practical-mind-dashboard-api-cli --pre-v110-practical-usefulness-gate --practical-supervised-mind-usefulness-audit
    # v100.1-v105.0 coherent local mind CLI flags intentionally registered dynamically and listed for parity checks: --v100-system-inventory-pass --route-command-duplicate-detector --dashboard-reality-review --smoke-readiness-coverage-audit --runtime-data-privacy-review --operator-workflow-friction-review --v100-reality-report-builder --stabilization-dashboard-api-cli-coverage --pre-v101-stabilization-gate --v100-milestone-stabilization-review --system-map-schema --core-mind-component-mapper --development-pipeline-mapper --safety-governance-mapper --operator-home-summary-model --cross-link-builder --map-integrity-checker --operator-home-dashboard-api-cli-coverage --pre-v102-system-map-gate --unified-eidolon-system-map-operator-home --coherence-binder-schema --memory-to-reflection-linker --reflection-to-goal-linker --goal-to-suggestion-linker --outcome-to-lesson-linker --coherence-conflict-detector --coherence-summary-builder --coherence-dashboard-api-cli-coverage --pre-v103-coherence-gate --memory-reflection-goal-coherence-binder --daily-loop-schema --morning-status-builder --priority-queue-builder --operator-action-prompt-builder --daily-safety-check-builder --daily-reflection-prompt-builder --daily-loop-dashboard-api-cli-coverage --daily-loop-safety-privacy-gate --pre-v104-daily-loop-gate --practical-daily-operating-loop --coherent-runtime-schema --unified-mind-state-snapshot --local-mind-continuity-report --unified-next-step-resolver --coherence-health-scorecard --runtime-contradiction-scanner --coherent-runtime-dashboard-api-cli-coverage --runtime-safety-containment-gate --pre-v105-integration-gate --coherent-local-mind-runtime-v1
    parser.add_argument("--improvement-goal", type=str, default=None, help="Optional supervised improvement goal for v80-v85 loop stages")
    parser.add_argument("--local-model-name", type=str, default=None, help="Optional local model name for v81-v85 proposal stages; invocation remains disabled by default")
    parser.add_argument("--improvement-cycle-id", type=str, default=None, help="Optional stable supervised improvement cycle id")
    parser.add_argument("--candidate-file", type=str, default=None, help="Optional JSON/text file containing patch candidates for v82-v85 review/ranking/refinement")
    parser.add_argument("--patch-trial-id", type=str, default=None, help="Optional stable sandbox patch trial id")
    parser.add_argument("--patch-draft-file", type=str, default=None, help="Optional patch draft/diff text file for v74/v75/v76 review and sandbox validation")
    parser.add_argument("--patch-evidence-file", type=str, default=None, help="Optional v75 sandbox evidence JSON file for v76 review")
    parser.add_argument("--patch-goal", type=str, default=None, help="Optional natural-language patch goal for v72+ patch context/review/trial/evidence building")
    parser.add_argument("--proposal-recommendation-id", type=str, default=None, help="Optional recommendation/candidate id for proposal drafting")
    parser.add_argument("--recall-scope", default="project", help="Optional recall scope: project, identity, safety, operator_preference, or release_task")
    parser.add_argument("--planning-scope", default="release_maintenance", help="Optional planning scope: release_maintenance, dashboard_cleanup, memory_review, identity_review, safety_hardening, coding_proposal, or documentation_update")
    parser.add_argument("--action-plan-id", default="", help="Action plan id for controlled execution preview binding")
    parser.add_argument("--action-confirm-phrase", default="", help="Exact action preview confirmation phrase")
    parser.add_argument("--execute-action-preview", action="store_true", help="Validate a controlled action execution preview only; never executes real source/memory/publish/live/rollback/identity operations")
    parser.add_argument("--memory-query", default="", help="Query text for memory search or recall")
    parser.add_argument("--memory-type", default="", help="Optional memory type filter for memory search")
    parser.add_argument("--memory-id", default="", help="Memory id for correction/removal preview")
    parser.add_argument("--execute-memory-removal", action="store_true", help="Execute v51.6 removal only with exact confirmation and a real durable store record")
    parser.add_argument("--maintenance-task-id", default="", help="Maintenance task id for queue checkpoint binding")
    parser.add_argument("--cycle-id", default="", help="Controlled self-maintenance cycle id")
    parser.add_argument("--proposal-id", default="", help="Sandbox autonomy patch proposal id")
    parser.add_argument("--autonomy-goal", default="", help="Goal text for autonomous dry-run planning and patch proposals")
    parser.add_argument("--revocation-reason", default="superseded release", help="Reason for guarded publish approval revocation writes")
    parser.add_argument("--revoker-label", default="local-operator", help="Revoker label for guarded publish approval revocation records")
    parser.add_argument("--approver-label", default="local-operator", help="Approver label for guarded publish approval write records")
    parser.add_argument("--release-evidence-bundle-path", help="Path to a release evidence bundle JSON for verification")
    parser.add_argument("--trust-snapshot-before", help="Before snapshot JSON path for --trust-console-diff")
    parser.add_argument("--trust-snapshot-after", help="After snapshot JSON path for --trust-console-diff")
    parser.add_argument("--maintenance-candidate-id", help="Specific maintenance candidate id for candidate-to-proposal bridge")
    parser.add_argument("--maintenance-bundle-hash", help="Exact reviewed maintenance bundle hash for approval-bound apply gates")
    parser.add_argument("--maintenance-confirm-phrase", default="", help="Explicit maintenance confirmation phrase for guarded live apply")
    parser.add_argument("--release-confirm-phrase", default="", help="Explicit release confirmation phrase for guarded checks")
    parser.add_argument("--run-heavy-release-checks", action="store_true", help="Run heavier zip compile/smoke checks inside v23 gates")
    parser.add_argument("--release-zip-path", help="Path to an external release zip for install/update verification")
    parser.add_argument("--signature-path", help="Path to detached signature sidecar JSON for public-key verification")
    parser.add_argument("--public-key-path", help="Path to public key PEM for detached signature verification")
    parser.add_argument("--trusted-fingerprint", help="Comma-separated trusted public key fingerprint(s) for detached signature verification")
    parser.add_argument("--expected-manifest-hash", help="Exact deterministic manifest SHA-256 required for live source update")
    parser.add_argument("--run-clean-room", action="store_true", help="Run clean-room install harness inside v22 self-update pipeline")
    parser.add_argument("--smoke-tier", default="fast", help="Smoke tier for clean-room or hardened smoke workflows")
    parser.add_argument("--run-install-smoke", action="store_true", help="Run full smoke check inside release install verification")
    parser.add_argument("--patch-draft-task", help="Patch draft task title/summary")
    parser.add_argument("--patch-draft-intent", help="Patch draft intent/why this patch exists")
    parser.add_argument("--patch-draft-target-version", default="50.0", help="Target version for a patch draft request")
    parser.add_argument("--patch-draft-risk-limit", default="medium", help="Maximum accepted draft risk for approval")
    parser.add_argument("--list-stable-loops", action="store_true", help="List saved stable supervised loop records")
    parser.add_argument("--show-stable-loop", nargs="?", const="latest", help="Show a saved stable supervised loop by id or alias")
    parser.add_argument("--stable-loop-review-summary", action="store_true", help="Summarize stable loop operator review states")
    parser.add_argument("--show-stable-loop-review", nargs="?", const="latest", help="Show review metadata for a saved stable loop")
    parser.add_argument("--mark-stable-loop-reviewed", type=str, help="Mark a stable loop reviewed")
    parser.add_argument("--approve-stable-loop-live", type=str, help="Mark a preview stable loop approved for explicit live run")
    parser.add_argument("--reject-stable-loop", type=str, help="Reject a stable loop review record")
    parser.add_argument("--run-approved-stable-loop-live", type=str, help="Run a live stable loop from a preview already approved for live")
    parser.add_argument("--stable-loop-review-note", type=str, default="", help="Optional note for stable loop review actions")
    parser.add_argument("--stable-loop-review-full", action="store_true", help="Show full stable loop review details")
    parser.add_argument("--list-stable-loop-reviews", nargs="?", const="all", help="List stable loop review/history records by filter")
    parser.add_argument("--stable-loop-review-filter", type=str, default="all", help="Review/history filter for stable loop review listings and cleanup")
    parser.add_argument("--include-archived-stable-loops", action="store_true", help="Include archived stable loop history records in listings")
    parser.add_argument("--archive-stable-loop", type=str, help="Archive one stable loop history record without deleting it")
    parser.add_argument("--restore-stable-loop", type=str, help="Restore one archived stable loop history record")
    parser.add_argument("--cleanup-stable-loop-history", action="store_true", help="Archive old stable loop history records matching a filter; dry-run unless --cleanup-stable-loop-confirm is used")
    parser.add_argument("--cleanup-stable-loop-limit", type=int, default=25, help="Maximum stable loop records to archive during cleanup")
    parser.add_argument("--cleanup-stable-loop-confirm", action="store_true", help="Actually archive cleanup candidates instead of previewing them")
    parser.add_argument("--cleanup-stable-loop-exclude-live", action="store_true", help="Do not archive live stable-loop records during cleanup")
    parser.add_argument("--show-stable-loop-audit", nargs="?", const="latest", help="Show audit, rollback, and verification notes for a stable-loop record")
    parser.add_argument("--refresh-stable-loop-audit", nargs="?", const="latest", help="Refresh and save the audit block for a stable-loop record")
    parser.add_argument("--stable-loop-audit-full", action="store_true", help="Include raw audit JSON when showing stable-loop audit notes")
    parser.add_argument("--show-stable-loop-operator-notes", nargs="?", const="latest", help="Show post-run checklist, operator notes, and final decision for a stable-loop record")
    parser.add_argument("--add-stable-loop-operator-note", type=str, help="Add an operator note to a stable-loop record")
    parser.add_argument("--complete-stable-loop-check", nargs=2, metavar=("LOOP_ID", "CHECK_ID"), help="Mark one stable-loop post-run checklist item done")
    parser.add_argument("--skip-stable-loop-check", nargs=2, metavar=("LOOP_ID", "CHECK_ID"), help="Mark one stable-loop post-run checklist item skipped")
    parser.add_argument("--set-stable-loop-final-decision", type=str, help="Set final operator decision for a stable-loop record")
    parser.add_argument("--stable-loop-final-decision", type=str, default="undecided", choices=["undecided", "keep", "fix_forward", "rollback", "needs_review"], help="Final stable-loop decision value")
    parser.add_argument("--stable-loop-operator-note", type=str, default="", help="Operator note for stable-loop checklist or final decision actions")
    parser.add_argument("--stable-loop-operator-full", action="store_true", help="Include raw operator-note JSON when showing post-run checklist details")
    parser.add_argument("--stable-loop-decision-report", nargs="?", const="all", help="Show stable-loop final-decision report by decision filter")
    parser.add_argument("--list-stable-loop-decisions", nargs="?", const="all", help="List stable-loop records by final-decision filter")
    parser.add_argument("--stable-loop-decision-filter", type=str, default="all", help="Final-decision filter for stable-loop decision reporting and cleanup")
    parser.add_argument("--include-live-stable-loop-decisions", action="store_true", help="Include live stable-loop records in decision reports and cleanup; enabled by default for cleanup")
    parser.add_argument("--cleanup-stable-loop-decisions", action="store_true", help="Archive stable-loop history by final decision; dry-run unless --cleanup-stable-loop-confirm is used")
    parser.add_argument("--stable-loop-decision-full", action="store_true", help="Include raw decision report/cleanup JSON")
    parser.add_argument("--stable-loop-followup-summary", nargs="?", const="action_required", help="Summarize decision-aware stable-loop follow-up task needs by final-decision filter")
    parser.add_argument("--create-stable-loop-followups", type=str, help="Create or preview follow-up tasks for one stable-loop final decision")
    parser.add_argument("--create-stable-loop-decision-followups", nargs="?", const="action_required", help="Create or preview follow-up tasks for stable-loop records matching a final-decision filter")
    parser.add_argument("--stable-loop-followup-force", action="store_true", help="Allow stable-loop follow-up task creation even when the final decision is not normally action-required")
    parser.add_argument("--stable-loop-followup-full", action="store_true", help="Include raw stable-loop follow-up task JSON output")
    parser.add_argument("--stable-loop-followup-lifecycle-summary", nargs="?", const="all", help="Summarize stable-loop decision follow-up tasks and lifecycle resolution state")
    parser.add_argument("--show-task-stable-loop-followup", type=str, help="Show stable-loop decision follow-up metadata for a task")
    parser.add_argument("--resolve-stable-loop-followups", type=str, help="Mark a stable-loop decision follow-up chain resolved once linked follow-up tasks are done")
    parser.add_argument("--resolve-task-stable-loop-followup", type=str, help="Resolve the stable-loop decision follow-up chain linked to a completed follow-up task")
    parser.add_argument("--archive-resolved-stable-loop", action="store_true", help="Archive the stable-loop record after resolving its follow-up task chain")
    parser.add_argument("--force-stable-loop-followup-resolution", action="store_true", help="Allow resolving stable-loop follow-ups even when linked tasks are still open")
    parser.add_argument("--stable-loop-followup-note", type=str, default="", help="Optional note for stable-loop follow-up lifecycle resolution")
    parser.add_argument("--stable-loop-followup-completion-report", nargs="?", const="all", help="Show stable-loop follow-up completion report by closure filter")
    parser.add_argument("--list-stable-loop-followup-completions", nargs="?", const="all", help="List stable-loop follow-up completion rows by closure filter")
    parser.add_argument("--stable-loop-followup-completion-filter", type=str, default="all", help="Filter for stable-loop follow-up completion reporting and cleanup")
    parser.add_argument("--mark-stable-loop-followup-closed", type=str, help="Mark a resolved stable-loop follow-up chain closed after operator review")
    parser.add_argument("--cleanup-stable-loop-followup-completions", action="store_true", help="Archive resolved stable-loop follow-up completion records; dry-run unless --cleanup-stable-loop-confirm is used")
    parser.add_argument("--stable-loop-followup-completion-full", action="store_true", help="Include raw follow-up completion report/cleanup JSON")
    parser.add_argument("--project-status", action="store_true", help="Show tracked projects")
    parser.add_argument("--add-project", type=str, help="Add a project and set it active")
    parser.add_argument("--project-path", type=str, default="", help="Path for --add-project")
    parser.add_argument("--project-language", type=str, default="Unknown", help="Language for --add-project")
    parser.add_argument("--project-description", type=str, default="", help="Description for --add-project")
    parser.add_argument("--set-active-project", type=str, help="Set the active project by name")
    parser.add_argument("--add-project-goal", type=str, help="Add a goal to the active project")
    parser.add_argument("--add-project-issue", type=str, help="Add a known issue to the active project")
    parser.add_argument("--add-project-next-step", type=str, help="Add a next step to the active project")
    parser.add_argument("--project-tree", nargs="?", const="", help="List files under the active project path")
    parser.add_argument("--read-project-file", type=str, help="Read a text file from the active project path")
    parser.add_argument("--search-project-files", type=str, help="Search active project files for exact text")
    parser.add_argument("--project-file-path", type=str, default="", help="Optional subfolder/file path for file search/tree commands")
    parser.add_argument("--index-project", nargs="?", const="", help="Build a read-only index of the active project or optional subfolder")
    parser.add_argument("--project-index-summary", action="store_true", help="Show saved project index summary")
    parser.add_argument("--search-project-index", type=str, help="Search the saved project index")
    parser.add_argument("--review-project-file", type=str, help="Review a project file without editing it")
    parser.add_argument("--no-ai-review", action="store_true", help="Use static review only, without the local Ollama model")
    parser.add_argument("--suggest-patch", nargs=2, metavar=("FILE", "REQUEST"), help="Suggest a patch for a project file without applying it")
    parser.add_argument("--list-patches", action="store_true", help="List saved patch proposals")
    parser.add_argument("--show-patch", type=str, help="Show a saved patch proposal by id")
    parser.add_argument("--show-patch-full", action="store_true", help="Include full proposed file content with --show-patch")
    parser.add_argument("--apply-patch", type=str, help="Apply a saved patch proposal by id")
    parser.add_argument("--dry-run", action="store_true", help="Preview patch apply checks without writing files")
    parser.add_argument("--list-applied-patches", action="store_true", help="List patches that have been applied")
    parser.add_argument("--rollback-patch", type=str, help="Rollback an applied patch using its saved backup")
    parser.add_argument("--list-rolled-back-patches", action="store_true", help="List patches that have been rolled back")
    parser.add_argument("--run-command", type=str, help="Run an approved whitelisted command")
    parser.add_argument("--list-allowed-commands", action="store_true", help="List approved command patterns")
    parser.add_argument("--command-history", action="store_true", help="Show recent approved command execution history")
    parser.add_argument("--run-test-workflow", nargs="?", const="", help="Run approved test workflow, optionally for a patch id")
    parser.add_argument("--test-command", action="append", default=[], help="Approved command to include in --run-test-workflow; can be repeated")
    parser.add_argument("--list-test-reports", action="store_true", help="List saved test workflow reports")
    parser.add_argument("--show-test-report", type=str, help="Show a saved test workflow report by id")
    parser.add_argument("--show-test-output", action="store_true", help="Include stdout/stderr when showing a test report")
    parser.add_argument("--review-test-report", type=str, help="Auto-review a test workflow report by id, or use latest")
    parser.add_argument("--auto-review", action="store_true", help="After --run-test-workflow, immediately review the newest test report")
    parser.add_argument("--no-ai-test-review", action="store_true", help="Use heuristic test report review only, without the local Ollama model")
    parser.add_argument("--list-test-reviews", action="store_true", help="List saved test report reviews")
    parser.add_argument("--show-test-review", type=str, help="Show a saved test report review by id")
    parser.add_argument("--hide-ai-review", action="store_true", help="Hide local AI section when showing a saved test review")
    parser.add_argument("--self-improve", nargs=2, metavar=("FILE", "REQUEST"), help="Start supervised self-improvement: review file and propose a patch, but do not apply it")
    parser.add_argument("--self-improve-apply", type=str, help="Apply a proposed self-improvement patch, then run tests and review the report")
    parser.add_argument("--self-improve-ai-review", action="store_true", help="Use local AI during the initial self-improvement code review")
    parser.add_argument("--no-ai-self-review", action="store_true", help="Disable local AI during self-improvement test report review")
    parser.add_argument("--list-self-improvements", action="store_true", help="List saved self-improvement runs")
    parser.add_argument("--show-self-improvement", type=str, help="Show a saved self-improvement run by id")
    parser.add_argument("--show-self-improvement-full", action="store_true", help="Include stored review/report details when showing a self-improvement run")
    parser.add_argument("--latest-ids", action="store_true", help="Show newest patch/run/report/review ids and no-copy aliases")
    parser.add_argument("--settings", action="store_true", help="Show Eidolon settings from data/settings.json")
    parser.add_argument("--get-setting", type=str, help="Show one setting by key")
    parser.add_argument("--set-setting", nargs=2, metavar=("KEY", "VALUE"), help="Update one setting in data/settings.json")
    parser.add_argument("--reset-settings", action="store_true", help="Reset settings to defaults")
    parser.add_argument("--settings-health", action="store_true", help="Check configured Ollama URL and model availability")
    parser.add_argument("--diagnostics", action="store_true", help="Run full Eidolon diagnostics and save a report")
    parser.add_argument("--diagnostics-full", action="store_true", help="Show detailed diagnostic JSON sections")
    parser.add_argument("--list-diagnostic-reports", action="store_true", help="List saved diagnostic reports")
    parser.add_argument("--show-diagnostic-report", nargs="?", const="latest", help="Show a saved diagnostic report by id or alias")
    parser.add_argument("--watch-once", action="store_true", help="Run one background watch-mode check and save a report")
    parser.add_argument("--watch-loop", action="store_true", help="Run a bounded background watch-mode loop")
    parser.add_argument("--watch-interval", type=int, default=int(get_setting("watch_interval_seconds", 300)), help="Seconds between watch-loop cycles")
    parser.add_argument("--watch-cycles", type=int, default=int(get_setting("watch_default_cycles", 3)), help="Number of cycles for --watch-loop")
    parser.add_argument("--no-ai-watch", action="store_true", help="Run watch mode without local AI summary")
    parser.add_argument("--watch-full", action="store_true", help="Include raw details when showing watch reports")
    parser.add_argument("--list-watch-reports", action="store_true", help="List saved background watch reports")
    parser.add_argument("--show-watch-report", nargs="?", const="latest", help="Show a saved watch report by id or alias")
    parser.add_argument("--hide-watch-ai", action="store_true", help="Hide local AI summary when showing a watch report")
    parser.add_argument("--notifications", action="store_true", help="Show unread notifications")
    parser.add_argument("--list-notifications", action="store_true", help="List notifications")
    parser.add_argument("--notification-filter-status", type=str, default="", help="Optional status filter for --list-notifications")
    parser.add_argument("--include-dismissed-notifications", action="store_true", help="Include dismissed notifications when listing")
    parser.add_argument("--show-notification", nargs="?", const="latest-unread", help="Show a notification by id or alias")
    parser.add_argument("--notification-full", action="store_true", help="Include raw notification JSON when showing a notification")
    parser.add_argument("--mark-notification-read", nargs="?", const="latest-unread", help="Mark a notification read by id or alias")
    parser.add_argument("--dismiss-notification", nargs="?", const="latest-unread", help="Dismiss a notification by id or alias")
    parser.add_argument("--notification-note", type=str, default="", help="Optional note for notification status changes")
    parser.add_argument("--clear-dismissed-notifications", action="store_true", help="Delete dismissed notification records")
    parser.add_argument("--chat-action", type=str, help="Translate a plain-English request into a safe proposed Eidolon action")
    parser.add_argument("--execute-chat-action", nargs="?", const="latest", help="Execute or create approval for a saved chat action by id or alias")
    parser.add_argument("--list-chat-actions", action="store_true", help="List saved chat-to-action proposals")
    parser.add_argument("--chat-action-filter-status", type=str, default="", help="Optional status filter for --list-chat-actions")
    parser.add_argument("--show-chat-action", nargs="?", const="latest", help="Show a saved chat action by id or alias")
    parser.add_argument("--chat-action-full", action="store_true", help="Include raw chat action JSON when showing a chat action")
    parser.add_argument("--dashboard", action="store_true", help="Start the local web dashboard with integrated /api routes")
    parser.add_argument("--dashboard-host", type=str, default=str(get_setting("dashboard_host", "127.0.0.1")), help="Host/interface for --dashboard")
    parser.add_argument("--dashboard-port", type=int, default=int(get_setting("dashboard_port", 8765)), help="Port for --dashboard")
    parser.add_argument("--api-server", action="store_true", help="Start the standalone local JSON API server")
    parser.add_argument("--api-host", type=str, default=str(get_setting("api_host", "127.0.0.1")), help="Host/interface for --api-server")
    parser.add_argument("--api-port", type=int, default=int(get_setting("api_port", 8766)), help="Port for --api-server")
    parser.add_argument("--desktop", action="store_true", help="Start the local desktop companion shell")
    parser.add_argument("--desktop-status", action="store_true", help="Show desktop companion shell launch info and URLs")
    parser.add_argument("--desktop-tray-status", action="store_true", help="Show optional real system tray availability and settings")
    parser.add_argument("--setup-check", action="store_true", help="Run and save a first-run/desktop startup setup check")
    parser.add_argument("--setup-full", action="store_true", help="Include detailed setup check diagnostics")
    parser.add_argument("--list-setup-reports", action="store_true", help="List saved setup helper reports")
    parser.add_argument("--show-setup-report", nargs="?", const="latest", help="Show a saved setup helper report by id or alias")
    parser.add_argument("--onboarding", action="store_true", help="Run and save the guided desktop onboarding wizard")
    parser.add_argument("--onboarding-full", action="store_true", help="Include detailed setup report and raw onboarding data")
    parser.add_argument("--onboarding-use-latest-setup", action="store_true", help="Build onboarding from latest setup report instead of running a fresh setup check")
    parser.add_argument("--list-onboarding-runs", action="store_true", help="List saved guided onboarding wizard runs")
    parser.add_argument("--show-onboarding-run", nargs="?", const="latest", help="Show a saved onboarding run by id or alias")
    parser.add_argument("--maintenance-scan", action="store_true", help="Create read-only maintenance suggestions for the active project")
    parser.add_argument("--no-ai-maintenance", action="store_true", help="Create maintenance suggestions without local AI summary")
    parser.add_argument("--list-maintenance-scans", action="store_true", help="List saved maintenance suggestion scans")
    parser.add_argument("--show-maintenance-scan", type=str, help="Show a saved maintenance scan by id, or use latest")
    parser.add_argument("--show-maintenance-full", action="store_true", help="Include detailed notes when showing a maintenance scan")
    parser.add_argument("--hide-maintenance-ai", action="store_true", help="Hide local AI summary when showing a maintenance scan")
    parser.add_argument("--memory-status", action="store_true", help="Show active memory counts and compaction status")
    parser.add_argument("--compact-memory", action="store_true", help="Archive and summarize older memories")
    parser.add_argument("--keep-recent-memories", type=int, default=int(get_setting("memory_keep_recent", 40)), help="How many recent memories to keep active during compaction")
    parser.add_argument("--min-memories-to-compact", type=int, default=int(get_setting("memory_min_count", 80)), help="Minimum active memory count before compaction runs")
    parser.add_argument("--no-ai-memory-compact", action="store_true", help="Compact memory using heuristic summary only, without local AI")
    parser.add_argument("--list-memory-summaries", action="store_true", help="List saved memory compaction summaries")
    parser.add_argument("--show-memory-summary", type=str, help="Show a memory summary by id, or use latest")
    parser.add_argument("--show-memory-summary-full", action="store_true", help="Include heuristic and local AI details when showing a memory summary")
    parser.add_argument("--plan-session", action="store_true", help="Create a read-only recommended session plan")
    parser.add_argument("--no-ai-session", action="store_true", help="Create session plan without local AI brief")
    parser.add_argument("--list-session-plans", action="store_true", help="List saved session plans")
    parser.add_argument("--show-session-plan", type=str, help="Show a saved session plan by id, or use latest")
    parser.add_argument("--show-session-plan-full", action="store_true", help="Include context details and all recommendations when showing a session plan")
    parser.add_argument("--hide-session-ai", action="store_true", help="Hide local AI brief when showing a session plan")
    parser.add_argument("--task-status", action="store_true", help="Show task queue status")
    parser.add_argument("--list-tasks", action="store_true", help="List task queue items")
    parser.add_argument("--task-filter-status", type=str, default="", help="Optional status filter for --list-tasks")
    parser.add_argument("--task-filter-project", type=str, default="", help="Optional project filter for --list-tasks")
    parser.add_argument("--hide-cancelled-tasks", action="store_true", help="Hide cancelled tasks when listing tasks")
    parser.add_argument("--show-task", type=str, help="Show a task by id, or use latest/latest-open/latest-ready/latest-active/latest-blocked/latest-done")
    parser.add_argument("--show-task-full", action="store_true", help="Include notes when showing a task")
    parser.add_argument("--add-task", type=str, help="Add a task to the queue")
    parser.add_argument("--task-description", type=str, default="", help="Description for --add-task")
    parser.add_argument("--task-priority", type=str, default="medium", help="Priority for --add-task: low, medium, high, critical")
    parser.add_argument("--task-initial-status", type=str, default="planned", help="Initial status for --add-task")
    parser.add_argument("--task-project", type=str, default="", help="Project name for --add-task or task list filter")
    parser.add_argument("--task-command", type=str, default="", help="Recommended command for --add-task")
    parser.add_argument("--task-next-action", type=str, default="", help="First next action for --add-task")
    parser.add_argument("--task-goal", type=str, default="", help="Linked goal id for --add-task")
    parser.add_argument("--task-risk", type=str, default="low", help="Risk label for --add-task")
    parser.add_argument("--set-task-status", nargs=2, metavar=("TASK", "STATUS"), help="Set a task status")
    parser.add_argument("--task-note", type=str, default="", help="Optional note for --set-task-status, --start-task, or --complete-task")
    parser.add_argument("--add-task-note", nargs=2, metavar=("TASK", "NOTE"), help="Add a note to a task")
    parser.add_argument("--add-task-action", nargs=2, metavar=("TASK", "ACTION"), help="Add a next action to a task")
    parser.add_argument("--start-task", type=str, help="Mark a task active")
    parser.add_argument("--complete-task", type=str, help="Mark a task done")
    parser.add_argument("--block-task", nargs=2, metavar=("TASK", "REASON"), help="Mark a task blocked with a blocker reason")
    parser.add_argument("--next-task", action="store_true", help="Show the highest-priority ready task")
    parser.add_argument("--queue-from-session", nargs="?", const="latest", help="Create task queue items from a saved session plan")
    parser.add_argument("--queue-task-limit", type=int, default=6, help="Maximum tasks to create from a session plan")
    parser.add_argument("--task-command-options", nargs="?", const="latest-ready", help="Show command options for a task")
    parser.add_argument("--execute-task", nargs="?", const="latest-ready", help="Run a queued task command through the approved command runner")
    parser.add_argument("--task-command-index", type=int, default=0, help="Command option index for --execute-task; 0 is primary, 1+ are follow-ups")
    parser.add_argument("--complete-on-success", action="store_true", help="Mark task done if --execute-task succeeds")
    parser.add_argument("--task-execution-history", nargs="?", const="latest", help="Show command execution history for a task")
    parser.add_argument("--evaluate-task", nargs="?", const="latest", help="Evaluate a task's execution history and recommend the next safe action")
    parser.add_argument("--no-ai-task-evaluation", action="store_true", help="Skip local AI summary when evaluating a task")
    parser.add_argument("--list-task-evaluations", action="store_true", help="List saved task result evaluations")
    parser.add_argument("--show-task-evaluation", nargs="?", const="latest", help="Show a saved task evaluation by id or alias")
    parser.add_argument("--hide-task-evaluation-ai", action="store_true", help="Hide AI section when showing a saved task evaluation")
    parser.add_argument("--apply-task-evaluation", nargs="?", const="latest", help="Apply a saved task evaluation when it recommends a safe status change")
    parser.add_argument("--task-evaluation-follow-up", action="store_true", help="Create a follow-up task when applying a task evaluation")
    parser.add_argument("--guided-work-session", nargs="?", const="latest-ready", help="Show and save a guided next-step plan for a task")
    parser.add_argument("--advance-work-session", nargs="?", const="latest-ready", help="Advance a task by one safe guided step")
    parser.add_argument("--apply-guided-evaluation", action="store_true", help="Allow --advance-work-session to apply a safe task evaluation recommendation")
    parser.add_argument("--guided-session-full", action="store_true", help="Include full task details when showing guided session output")
    parser.add_argument("--list-guided-sessions", action="store_true", help="List saved guided work sessions")
    parser.add_argument("--show-guided-session", nargs="?", const="latest", help="Show a saved guided work session by id or alias")
    parser.add_argument("--dev-cycle", nargs="?", const="latest-ready", help="Inspect the next supervised autonomous development step")
    parser.add_argument("--advance-dev-cycle", nargs="?", const="latest-ready", help="Advance the supervised autonomous dev cycle by one safe step")
    parser.add_argument("--approve-dev-cycle-apply", action="store_true", help="Allow --advance-dev-cycle to apply or rollback a patch when that is the selected step")
    parser.add_argument("--apply-dev-cycle-evaluation", action="store_true", help="Allow --advance-dev-cycle to apply a safe task evaluation recommendation")
    parser.add_argument("--no-ai-dev-cycle", action="store_true", help="Skip local AI summaries during dev-cycle advancement")
    parser.add_argument("--dev-cycle-full", action="store_true", help="Include full state details when showing dev cycle output")
    parser.add_argument("--list-dev-cycles", action="store_true", help="List saved supervised dev cycle records")
    parser.add_argument("--show-dev-cycle", nargs="?", const="latest", help="Show a saved supervised dev cycle by id or alias")
    parser.add_argument("--dev-loop", nargs="?", const="latest-ready", help="Run a bounded autonomous dev loop for a task alias/id")
    parser.add_argument("--dev-loop-steps", type=int, default=int(get_setting("default_dev_loop_steps", 3)), help="Maximum number of bounded dev-loop steps to run, capped by settings max_dev_loop_steps")
    parser.add_argument("--approve-dev-loop-actions", action="store_true", help="Allow dev loop to apply or rollback patches when that approved step is selected")
    parser.add_argument("--apply-dev-loop-evaluation", action="store_true", help="Allow dev loop to apply safe task evaluation recommendations")
    parser.add_argument("--no-ai-dev-loop", action="store_true", help="Skip local AI summaries during bounded dev-loop actions")
    parser.add_argument("--dev-loop-full", action="store_true", help="Include raw loop details when showing dev-loop output")
    parser.add_argument("--list-dev-loops", action="store_true", help="List saved bounded autonomous dev-loop records")
    parser.add_argument("--show-dev-loop", nargs="?", const="latest", help="Show a saved bounded dev loop by id or alias")
    parser.add_argument("--self-development-cycle", action="store_true", help="Run the controlled Self Development Cycle planner; proposal-only unless --self-development-create-task is supplied")
    parser.add_argument("--self-development-create-task", action="store_true", help="Allow the Self Development Cycle to create or reuse one low-risk task record, then stop before source edits")
    parser.add_argument("--self-development-prompt", type=str, default="", help="Original operator prompt to bind into the Self Development Cycle receipt")
    parser.add_argument("--no-ai-self-development", action="store_true", help="Reserved safety flag: the v1 Self Development Cycle is deterministic and does not invoke local AI")
    parser.add_argument("--self-development-full", action="store_true", help="Include full candidates and inspection data when showing Self Development Cycle output")
    parser.add_argument("--list-self-development-cycles", action="store_true", help="List saved Self Development Cycle records")
    parser.add_argument("--show-self-development-cycle", nargs="?", const="latest", help="Show a saved Self Development Cycle by id or alias")
    parser.add_argument("--self-development-trial-review", action="store_true", help="Show the v730 Self Development Cycle trial review and protected-system gate report")
    parser.add_argument("--self-development-smoke-triage", action="store_true", help="Show the v730 broad smoke triage classification report without running broad smoke")
    parser.add_argument("--self-development-dashboard-hardening", action="store_true", help="Show the v730 dashboard hardening review packet for Self Development Cycle")
    parser.add_argument("--self-development-implementation-proposal", nargs="?", const="latest", help="Prepare a reviewable implementation proposal packet for a Self Development Cycle id or latest")
    parser.add_argument("--self-development-save-proposal", action="store_true", help="Save the implementation proposal receipt; still applies no source edits")
    parser.add_argument("--self-development-patch-draft", nargs="?", const="", help="Prepare an operator-approved patch draft packet using the exact approval phrase for the selected Self Development task")
    parser.add_argument("--self-development-patch-draft-cycle", default="latest", help="Self Development Cycle id or alias used by --self-development-patch-draft")
    parser.add_argument("--self-development-save-patch-draft", action="store_true", help="Save the patch draft receipt; still applies no source edits")
    parser.add_argument("--self-development-patch-application", nargs="?", const="", help="Prepare an operator-approved patch application trial receipt using the exact approval phrase for a patch draft")
    parser.add_argument("--self-development-patch-application-draft", default="latest", help="Patch draft id or alias used by --self-development-patch-application")
    parser.add_argument("--self-development-save-patch-application", action="store_true", help="Save the patch application trial receipt; still applies no source edits when no concrete diff exists")
    parser.add_argument("--self-development-application-receipt-review", action="store_true", help="Show the v750 Self Development application receipt review packet")
    parser.add_argument("--current-smoke-debt-ledger", action="store_true", help="Show the v750 current smoke debt ledger without running broad smoke")
    parser.add_argument("--save-current-smoke-debt-ledger", action="store_true", help="Save the current smoke debt ledger as a private runtime receipt; never packaged")
    parser.add_argument("--low-risk-smoke-debt-cleanup-candidates", action="store_true", help="Show proposal-only low-risk smoke debt cleanup candidates")
    parser.add_argument("--self-development-smoke-debt-dashboard", action="store_true", help="Show the v751 Self Development smoke debt dashboard packet")
    parser.add_argument("--self-development-api-surface-truth-review", action="store_true", help="Show the v751 Self Development API surface truth review packet")
    parser.add_argument("--self-development-cycle-duplicate-cleanup", action="store_true", help="Show the v760 Self Development Cycle duplicate cleanup review packet")
    parser.add_argument("--legacy-self-maintenance-smoke-blocker-review", action="store_true", help="Show the v765 Legacy Self Maintenance smoke blocker review packet")
    parser.add_argument("--current-smoke-debt-ledger-reconciliation", action="store_true", help="Show the v780 current smoke debt ledger reconciliation review packet")
    parser.add_argument("--current-audit-wording-cleanup", action="store_true", help="Show the v780 current audit wording cleanup review packet")
    parser.add_argument("--manifest-generation-prep-review", action="store_true", help="Show the v780 manifest generation prep review packet")
    parser.add_argument("--manifest-gated-surface-validation", action="store_true", help="Show the v780 manifest-gated surface validation review packet")
    parser.add_argument("--manifest-driven-surface-registry-pilot", action="store_true", help="Show the v790 manifest-driven surface registry pilot review packet")
    parser.add_argument("--manifest-surface-generation-readiness", action="store_true", help="Show the v790 manifest surface generation readiness review packet")
    parser.add_argument("--manifest-registry-expanded-review-surfaces", action="store_true", help="Show the v790 manifest registry expanded review surfaces packet")
    parser.add_argument("--manifest-registry-generation-readiness-scoring", action="store_true", help="Show the v790 manifest registry generation readiness scoring packet")
    parser.add_argument("--manifest-registry-drift-detection", action="store_true", help="Show the v795 manifest registry drift detection packet")
    parser.add_argument("--manifest-guided-validation-probe-dry-run", action="store_true", help="Show the v800 manifest-guided validation probe dry-run packet")
    parser.add_argument("--manifest-guided-generated-validation-probe", action="store_true", help="Show the v815 manifest-guided generated validation probe review-only packet")
    parser.add_argument("--manifest-smoke-segment-parity-drift", action="store_true", help="Show the v815 manifest smoke segment parity repair packet-only packet")
    parser.add_argument("--manifest-smoke-segment-parity-repair-packet", action="store_true", help="Show the v825 manifest smoke segment parity repair packet review-only packet")
    parser.add_argument("--manifest-smoke-segment-repair-application", action="store_true", help="Show the v825 operator-approved manifest smoke segment repair application review")
    parser.add_argument("--manifest-segment-parity-enforcement-gate", action="store_true", help="Show the v835 release-blocking manifest segment parity enforcement gate review")
    parser.add_argument("--manifest-guided-validation-probe-expansion-readiness", action="store_true", help="Show the v835 manifest-guided validation probe expansion readiness review")
    parser.add_argument("--manifest-guided-multi-surface-validation-probe-dry-run", action="store_true", help="Show the v840 manifest-guided multi-surface validation probe dry-run review")
    parser.add_argument("--manifest-guided-multi-surface-generated-validation-probe-packet", action="store_true", help="Show the v845 manifest-guided multi-surface generated validation probe packet review")
    parser.add_argument("--manifest-guided-multi-surface-probe-packet-consistency-gate", action="store_true", help="Show the v850 manifest-guided multi-surface probe packet consistency gate review")
    parser.add_argument("--manifest-guided-sandbox-probe-file-generation-readiness", action="store_true", help="Show the v855 manifest-guided sandbox probe file generation readiness review")
    parser.add_argument("--manifest-guided-sandbox-probe-file-generation-dry-run", action="store_true", help="Show the v860 manifest-guided sandbox probe file generation dry-run review")
    parser.add_argument("--operator-approved-sandbox-probe-file-generation-trial", action="store_true", help="Show the v865 operator-approved sandbox probe file generation trial review")
    parser.add_argument("--sandbox-probe-file-verification-and-cleanup-review", action="store_true", help="Show the v870 sandbox probe file verification and cleanup review")
    parser.add_argument("--sandbox-probe-execution-harness-readiness-review", action="store_true", help="Show the v875 sandbox probe execution harness readiness review")
    parser.add_argument("--operator-approved-sandbox-probe-execution-trial", action="store_true", help="Show the v880 operator-approved sandbox probe execution trial")
    parser.add_argument("--sandbox-probe-execution-result-review-and-promotion-readiness", action="store_true", help="Show the v885 sandbox probe execution result review and promotion readiness report")
    parser.add_argument("--live-probe-promotion-plan-review", action="store_true", help="Show the v890 live probe promotion plan review")
    parser.add_argument("--operator-approved-live-probe-registration-trial", action="store_true", help="Show the v895 operator-approved live probe registration trial")
    parser.add_argument("--live-registered-probe-verification-and-structural-hardening-review", action="store_true", help="Show the v900 live registered probe verification and structural hardening review")
    parser.add_argument("--v905-baseline-verification-and-manifest-version-semantics-prep", action="store_true", help="Show the v906 v905 baseline verification and manifest version semantics prep review")
    parser.add_argument("--manifest-version-semantics-split", action="store_true", help="Show the v907 manifest version semantics split review")
    parser.add_argument("--manifest-validation-normalization", action="store_true", help="Show the v908 manifest validation normalization review")
    parser.add_argument("--source-package-privacy-deep-scan", action="store_true", help="Show the v909 source package privacy deep scan review")
    parser.add_argument("--metadata-and-current-marker-gate-reconciliation", action="store_true", help="Show the v910 metadata and current marker gate reconciliation review")
    parser.add_argument("--release-gate-stale-assertion-truth-repair", action="store_true", help="Show the v911 release gate stale assertion truth repair review")
    parser.add_argument("--install-release-segment-blocker-classification", action="store_true", help="Show the v912 install-release segment blocker classification review")
    parser.add_argument("--release-archive-and-recovery-gate-boundedness-repair", action="store_true", help="Show the v913 release archive and recovery gate boundedness repair review")
    parser.add_argument("--install-release-segment-evidence-summary-gate", action="store_true", help="Show the v914 install-release segment evidence summary gate review")
    parser.add_argument("--manifest-driven-surface-generation-prep", action="store_true", help="Show the v915 manifest-driven surface generation prep review")
    parser.add_argument("--manifest-review-packet-schema", action="store_true", help="Show the v916 manifest review packet schema review")
    parser.add_argument("--dashboard-surface-preview-generator", action="store_true", help="Show the v917 dashboard surface preview generator review")
    parser.add_argument("--cli-api-surface-preview-generator", action="store_true", help="Show the v918 CLI/API surface preview generator review")
    parser.add_argument("--smoke-surface-preview-generator", action="store_true", help="Show the v919 smoke surface preview generator review")
    parser.add_argument("--generated-preview-parity-report", action="store_true", help="Show the v920 generated preview parity report review")
    parser.add_argument("--low-risk-surface-selection-gate", action="store_true", help="Show the v921 low-risk surface selection gate review")
    parser.add_argument("--generated-dashboard-preview-exact-match-gate", action="store_true", help="Show the v922 generated dashboard preview exact-match gate review")
    parser.add_argument("--generated-cli-api-preview-exact-match-gate", action="store_true", help="Show the v923 generated CLI/API preview exact-match gate review")
    parser.add_argument("--generated-smoke-preview-exact-match-gate", action="store_true", help="Show the v924 generated smoke preview exact-match gate review")
    parser.add_argument("--single-surface-generated-parity-closure", action="store_true", help="Show the v925 single-surface generated parity closure review")
    parser.add_argument("--multi-surface-selection-gate", action="store_true", help="Show the v926 multi-surface selection gate review")
    parser.add_argument("--multi-surface-dashboard-preview-parity", action="store_true", help="Show the v927 multi-surface dashboard preview parity review")
    parser.add_argument("--multi-surface-cli-api-preview-parity", action="store_true", help="Show the v928 multi-surface CLI/API preview parity review")
    parser.add_argument("--multi-surface-smoke-preview-parity", action="store_true", help="Show the v929 multi-surface smoke preview parity review")
    parser.add_argument("--multi-surface-generated-parity-batch-closure", action="store_true", help="Show the v930 multi-surface generated parity batch closure review")
    parser.add_argument("--generated-scaffold-sandbox-output-schema", action="store_true", help="Show the v931 generated scaffold sandbox output schema review")
    parser.add_argument("--generated-scaffold-sandbox-artifact-preview", action="store_true", help="Show the v932 generated scaffold sandbox artifact preview review")
    parser.add_argument("--generated-scaffold-hash-ledger", action="store_true", help="Show the v933 generated scaffold hash ledger review")
    parser.add_argument("--generated-scaffold-sandbox-parity-comparison", action="store_true", help="Show the v934 generated scaffold sandbox parity comparison review")
    parser.add_argument("--generated-scaffold-sandbox-output-closure", action="store_true", help="Show the v935 generated scaffold sandbox output closure review")
    parser.add_argument("--generated-scaffold-wrapper-mapping-schema", action="store_true", help="Show the v936 generated scaffold wrapper mapping schema review")
    parser.add_argument("--dashboard-compatibility-wrapper-preview", action="store_true", help="Show the v937 dashboard compatibility wrapper preview review")
    parser.add_argument("--cli-api-compatibility-wrapper-preview", action="store_true", help="Show the v938 CLI/API compatibility wrapper preview review")
    parser.add_argument("--smoke-compatibility-wrapper-preview", action="store_true", help="Show the v939 smoke compatibility wrapper preview review")
    parser.add_argument("--generated-scaffold-wrapper-prep-closure", action="store_true", help="Show the v940 generated scaffold wrapper prep closure review")
    parser.add_argument("--giant-file-extraction-inventory", action="store_true", help="Show the v941 giant file extraction inventory review")
    parser.add_argument("--self-development-cycle-extraction-map", action="store_true", help="Show the v942 self-development cycle extraction map review")
    parser.add_argument("--self-maintenance-builder-text-renderer-extraction-map", action="store_true", help="Show the v943 self-maintenance builder/text renderer extraction map review")
    parser.add_argument("--dashboard-route-renderer-extraction-map", action="store_true", help="Show the v944 dashboard route/renderer extraction map review")
    parser.add_argument("--cli-api-dispatch-extraction-map", action="store_true", help="Show the v945 CLI/API dispatch extraction map review")
    parser.add_argument("--smoke-registry-extraction-map", action="store_true", help="Show the v946 smoke registry extraction map review")
    parser.add_argument("--compatibility-wrapper-risk-ledger", action="store_true", help="Show the v947 compatibility wrapper risk ledger review")
    parser.add_argument("--extraction-order-proposal", action="store_true", help="Show the v948 extraction order proposal review")
    parser.add_argument("--extraction-rollback-evidence-plan", action="store_true", help="Show the v949 extraction rollback evidence plan review")
    parser.add_argument("--giant-file-compatibility-extraction-prep-closure", action="store_true", help="Show the v950 giant file compatibility extraction prep closure review")
    parser.add_argument("--extraction-candidate-lock-gate", action="store_true", help="Show the v951 extraction candidate lock gate review")
    parser.add_argument("--pre-extraction-function-inventory", action="store_true", help="Show the v952 pre-extraction function inventory review")
    parser.add_argument("--generated-preview-review-module-extraction", action="store_true", help="Show the v953 generated preview review module extraction review")
    parser.add_argument("--compatibility-import-wrapper-gate", action="store_true", help="Show the v954 compatibility import wrapper gate review")
    parser.add_argument("--dashboard-cli-api-parity-after-extraction", action="store_true", help="Show the v955 dashboard/CLI/API parity after extraction review")
    parser.add_argument("--smoke-registry-parity-after-extraction", action="store_true", help="Show the v956 smoke registry parity after extraction review")
    parser.add_argument("--stale-version-and-metadata-post-extraction-gate", action="store_true", help="Show the v957 stale-version and metadata post-extraction gate review")
    parser.add_argument("--rollback-path-verification", action="store_true", help="Show the v958 rollback path verification review")
    parser.add_argument("--extraction-release-evidence-packet", action="store_true", help="Show the v959 extraction release evidence packet review")
    parser.add_argument("--first-compatibility-extraction-closure", action="store_true", help="Show the v960 first compatibility extraction closure review")

    parser.add_argument("--second-extraction-candidate-selection-gate", action="store_true", help="Show the v961 second extraction candidate selection gate review")
    parser.add_argument("--second-pre-extraction-function-inventory", action="store_true", help="Show the v962 second pre-extraction function inventory review")
    parser.add_argument("--generated-scaffold-review-packet-extraction", action="store_true", help="Show the v963 generated scaffold review packet extraction review")
    parser.add_argument("--second-compatibility-wrapper-gate", action="store_true", help="Show the v964 second compatibility wrapper gate review")
    parser.add_argument("--second-extraction-surface-parity-gate", action="store_true", help="Show the v965 second extraction surface parity gate review")
    parser.add_argument("--smoke-registry-data-model-prep", action="store_true", help="Show the v966 smoke registry data model prep review")
    parser.add_argument("--smoke-registry-static-inventory", action="store_true", help="Show the v967 smoke registry static inventory review")
    parser.add_argument("--smoke-registry-migration-risk-ledger", action="store_true", help="Show the v968 smoke registry migration risk ledger review")
    parser.add_argument("--smoke-registry-rollback-plan", action="store_true", help="Show the v969 smoke registry rollback plan review")
    parser.add_argument("--second-extraction-and-smoke-registry-prep-closure", action="store_true", help="Show the v970 second extraction and smoke registry prep closure review")
    parser.add_argument("--smoke-registry-pilot-selection-gate", action="store_true", help="Show the v971 smoke registry pilot selection gate review")
    parser.add_argument("--smoke-registry-pilot-schema", action="store_true", help="Show the v972 smoke registry pilot schema review")
    parser.add_argument("--smoke-registry-pilot-data-table", action="store_true", help="Show the v973 smoke registry pilot data table review")
    parser.add_argument("--smoke-registry-pilot-resolver", action="store_true", help="Show the v974 smoke registry pilot resolver review")
    parser.add_argument("--manual-vs-pilot-smoke-parity-gate", action="store_true", help="Show the v975 manual-vs-pilot smoke parity gate review")
    parser.add_argument("--pilot-json-shape-compatibility-gate", action="store_true", help="Show the v976 pilot JSON shape compatibility gate review")
    parser.add_argument("--pilot-rollback-evidence-gate", action="store_true", help="Show the v977 pilot rollback evidence gate review")
    parser.add_argument("--smoke-registry-pilot-risk-review", action="store_true", help="Show the v978 smoke registry pilot risk review")
    parser.add_argument("--pilot-expansion-readiness-review", action="store_true", help="Show the v979 pilot expansion readiness review")
    parser.add_argument("--smoke-registry-data-driven-pilot-closure", action="store_true", help="Show the v980 smoke registry data-driven pilot closure review")
    parser.add_argument("--smoke-registry-execution-trial-readiness-gate", action="store_true", help="Show the v981 smoke registry execution trial readiness gate review")
    parser.add_argument("--data-driven-smoke-callable-execution-harness", action="store_true", help="Show the v982 data-driven smoke callable execution harness review")
    parser.add_argument("--pilot-smoke-execution-result-packet", action="store_true", help="Show the v983 pilot smoke execution result packet review")
    parser.add_argument("--manual-vs-data-driven-execution-parity-gate", action="store_true", help="Show the v984 manual-vs-data-driven execution parity gate review")
    parser.add_argument("--data-driven-smoke-json-output-preview", action="store_true", help="Show the v985 data-driven smoke JSON output preview review")
    parser.add_argument("--data-driven-smoke-timeout-failure-semantics", action="store_true", help="Show the v986 data-driven smoke timeout/failure semantics review")
    parser.add_argument("--data-driven-smoke-manual-fallback-proof", action="store_true", help="Show the v987 data-driven smoke manual fallback proof review")
    parser.add_argument("--data-driven-smoke-execution-risk-review", action="store_true", help="Show the v988 data-driven smoke execution risk review")
    parser.add_argument("--data-driven-smoke-expansion-readiness", action="store_true", help="Show the v989 data-driven smoke expansion readiness review")
    parser.add_argument("--smoke-registry-data-driven-execution-trial-closure", action="store_true", help="Show the v990 smoke registry data-driven execution trial closure review")
    parser.add_argument("--fallback-migration-readiness-gate", action="store_true", help="Show the v991 fallback migration readiness gate review")
    parser.add_argument("--data-driven-first-pilot-dispatch-preview", action="store_true", help="Show the v992 data-driven first pilot dispatch preview review")
    parser.add_argument("--pilot-fallback-dispatch-trial", action="store_true", help="Show the v993 pilot fallback dispatch trial review")
    parser.add_argument("--pilot-fallback-result-ledger", action="store_true", help="Show the v994 pilot fallback result ledger review")
    parser.add_argument("--json-output-stability-gate", action="store_true", help="Show the v995 JSON output stability gate review")
    parser.add_argument("--fast-install-release-isolation-gate", action="store_true", help="Show the v996 fast/install/release isolation gate review")
    parser.add_argument("--manual-fallback-removal-resistance-gate", action="store_true", help="Show the v997 manual fallback removal resistance gate review")
    parser.add_argument("--pilot-migration-risk-review", action="store_true", help="Show the v998 pilot migration risk review")
    parser.add_argument("--v1000-milestone-readiness-review", action="store_true", help="Show the v999 v1000 milestone readiness review")
    parser.add_argument("--smoke-registry-fallback-migration-pilot-closure", action="store_true", help="Show the v1000 smoke registry fallback migration pilot closure review")
    parser.add_argument("--install-release-blocker-ledger-refresh", action="store_true", help="Show the v1002 install-release blocker ledger refresh review")
    parser.add_argument("--install-release-timeout-harness-repair", action="store_true", help="Show the v1003 install-release timeout harness repair review")
    parser.add_argument("--install-release-timeout-row-bounded-retest", action="store_true", help="Show the v1004 install-release timeout row bounded retest review")
    parser.add_argument("--install-release-fixture-decomposition-plan", action="store_true", help="Show the v1005 install-release fixture decomposition plan review")
    parser.add_argument("--install-release-fixture-smoke-split-pilot", action="store_true", help="Show the v1006 install-release fixture smoke split pilot review")
    parser.add_argument("--release-archive-fixture-split-expansion", action="store_true", help="Show the v1007 release archive fixture split expansion review")
    parser.add_argument("--supervised-blocker-semantics-repair", action="store_true", help="Show the v1008 supervised blocker semantics repair review")
    parser.add_argument("--install-release-segment-cleanliness-gate", action="store_true", help="Show the v1009 install-release segment cleanliness gate review")
    parser.add_argument("--post-v1000-defect-closure-audit-and-phase-zero-boundary", action="store_true", help="Show the v1010 post-v1000 defect closure audit and Phase 0 boundary review")
    parser.add_argument("--install-release-timeout-parent-row-replacement-pilot", action="store_true", help="Show the v1011 install-release timeout parent row replacement pilot review")
    parser.add_argument("--install-release-parent-replacement-expansion", action="store_true", help="Show the v1012 install-release parent replacement expansion review")
    parser.add_argument("--remaining-timeout-parent-fixture-selection", action="store_true", help="Show the v1013 remaining timeout parent fixture split selection review")
    parser.add_argument("--recovery-closure-fixture-split-smoke", action="store_true", help="Show the v1014 recovery closure fixture split smoke review")
    parser.add_argument("--recovery-closure-parent-replacement-overlay", action="store_true", help="Show the v1015 recovery closure parent replacement overlay review")
    parser.add_argument("--remaining-timeout-parent-fixture-split-expansion", action="store_true", help="Show the v1016 remaining timeout parent fixture split expansion review")
    parser.add_argument("--decision-archive-ledger-parent-replacement-overlay", action="store_true", help="Show the v1017 decision archive ledger parent replacement overlay review")
    parser.add_argument("--candidate-handoff-fixture-split-smoke", action="store_true", help="Show the v1018 candidate handoff fixture split smoke review")
    parser.add_argument("--candidate-handoff-parent-replacement-overlay", action="store_true", help="Show the v1019 candidate handoff parent replacement overlay review")
    parser.add_argument("--final-timeout-parent-overlay-closure", action="store_true", help="Show the v1020 final timeout parent overlay closure review")
    parser.add_argument("--approval-inbox", action="store_true", help="Show pending approval requests")
    parser.add_argument("--list-approvals", action="store_true", help="List approval requests, including closed ones")
    parser.add_argument("--approval-filter-status", type=str, default="", help="Optional status filter for --list-approvals")
    parser.add_argument("--show-approval", nargs="?", const="latest-pending", help="Show an approval request by id or alias")
    parser.add_argument("--approval-full", action="store_true", help="Include raw approval JSON when showing an approval")
    parser.add_argument("--approve", nargs="?", const="latest-pending", help="Execute a pending approval request by id or alias")
    parser.add_argument("--reject", nargs="?", const="latest-pending", help="Reject a pending approval request by id or alias")
    parser.add_argument("--approval-note", type=str, default="", help="Optional note for --reject")
    parser.add_argument("--goal-status", action="store_true", help="Show structured goal counts and open goal context")
    parser.add_argument("--list-goals", action="store_true", help="List structured goals")
    parser.add_argument("--goal-filter-status", type=str, default="", help="Optional status filter for --list-goals")
    parser.add_argument("--goal-filter-project", type=str, default="", help="Optional project filter for --list-goals")
    parser.add_argument("--hide-cancelled-goals", action="store_true", help="Hide cancelled goals when listing goals")
    parser.add_argument("--show-goal", type=str, help="Show a goal by id, or use latest/latest-open/latest-active/latest-blocked/latest-completed")
    parser.add_argument("--show-goal-full", action="store_true", help="Include notes when showing a goal")
    parser.add_argument("--add-goal-structured", type=str, help="Add a structured goal")
    parser.add_argument("--goal-description", type=str, default="", help="Description for --add-goal-structured")
    parser.add_argument("--goal-priority", type=str, default="medium", help="Priority for --add-goal-structured: low, medium, high, critical")
    parser.add_argument("--goal-initial-status", type=str, default="planned", help="Initial status for --add-goal-structured")
    parser.add_argument("--goal-project", type=str, default="", help="Project name for --add-goal-structured or --list-goals filter")
    parser.add_argument("--goal-next-action", type=str, default="", help="First next action for --add-goal-structured")
    parser.add_argument("--set-goal-status", nargs=2, metavar=("GOAL", "STATUS"), help="Set a structured goal status")
    parser.add_argument("--goal-note", type=str, default="", help="Optional note used with --set-goal-status or --complete-goal")
    parser.add_argument("--add-goal-note", nargs=2, metavar=("GOAL", "NOTE"), help="Add a note to a structured goal")
    parser.add_argument("--add-goal-action", nargs=2, metavar=("GOAL", "ACTION"), help="Add a next action to a structured goal")
    parser.add_argument("--block-goal", nargs=2, metavar=("GOAL", "REASON"), help="Mark a goal blocked with a blocker reason")
    parser.add_argument("--complete-goal", type=str, help="Mark a structured goal completed")
    parser.add_argument("--delay", type=int, default=10, help="Seconds between loop cycles")
    args = parser.parse_args()

    if args.work_queue is not None:
        raise SystemExit(run_work_queue_cli(args.work_queue))

    if args.task_work is not None:
        raise SystemExit(run_work_queue_cli(args.task_work))

    task_work_full = args.task_work_executor_full or args.work_executor_full
    allow_task_work_approval = args.approve_task_work_execution or args.approve_work_execution
    use_task_work_ai = not (args.no_ai_task_work_executor or args.no_ai_work_executor)

    if args.request_task_approval:
        print_request_task_work_approval(
            args.request_task_approval,
            reason=args.task_approval_reason,
            use_ai=use_task_work_ai,
            full_output=task_work_full,
            force=args.force_task_approval,
            dry_run=args.dry_run,
            full=args.task_approval_full,
        )
        return

    if args.request_next_task_approval:
        print_request_next_task_work_approval(
            project_id=args.task_approval_project or None,
            reason=args.task_approval_reason,
            use_ai=use_task_work_ai,
            full_output=task_work_full,
            force=args.force_task_approval,
            dry_run=args.dry_run,
            full=args.task_approval_full,
        )
        return

    if args.show_task_approvals:
        print_task_approvals(
            args.show_task_approvals,
            include_closed=True,
            full=args.task_approval_full,
        )
        return

    if args.task_recovery_summary:
        print_task_recoveries(
            project=args.task_recovery_project,
            include_nonrecoverable=False,
            full=False,
        )
        return

    if args.list_task_recoveries:
        print_task_recoveries(
            project=args.task_recovery_project,
            include_nonrecoverable=False,
            full=args.task_recovery_full,
        )
        return

    if args.show_task_recovery:
        print_task_recovery(args.show_task_recovery, full=args.task_recovery_full)
        return

    if args.mark_task_ready_for_retry:
        print_mark_task_ready_for_retry(
            args.mark_task_ready_for_retry,
            note=args.task_recovery_note,
            full=args.task_recovery_full,
        )
        return

    if args.retry_task_work:
        print_retry_task_work(
            args.retry_task_work,
            dry_run=args.dry_run,
            allow_approval_required=allow_task_work_approval,
            use_ai=use_task_work_ai,
            full=args.task_recovery_full or task_work_full,
        )
        return

    if args.execute_task_work_id or args.execute_work_id:
        target_task_id = args.execute_task_work_id or args.execute_work_id
        print_execute_task_work_item(
            target_task_id,
            dry_run=args.dry_run,
            allow_approval_required=allow_task_work_approval,
            use_ai=use_task_work_ai,
            full=task_work_full,
        )
        return

    if args.execute_task_work or args.execute_work:
        project_filter = args.execute_task_work_project or args.execute_work_project or None
        print_execute_next_task_work_item(
            project_id=project_filter,
            dry_run=args.dry_run,
            allow_approval_required=allow_task_work_approval,
            use_ai=use_task_work_ai,
            full=task_work_full,
        )
        return

    if args.queue_task_patch:
        target_file, request = args.queue_task_patch
        print_create_patch_task(
            target_file=target_file,
            request=request,
            project_id=args.queue_patch_project,
            priority=args.queue_patch_priority,
            risk=args.queue_patch_risk,
            requires_approval=args.queue_patch_requires_approval or None,
        )
        return

    if args.queue_patch:
        target_file, request = args.queue_patch
        print_create_patch_work_item(
            target_file=target_file,
            request=request,
            project_id=args.queue_patch_project,
            priority=args.queue_patch_priority,
            risk=args.queue_patch_risk,
            requires_approval=args.queue_patch_requires_approval or None,
        )
        return

    if args.suggest_patch_for_task:
        print_suggest_patch_for_task(
            args.suggest_patch_for_task,
            use_ai=not args.no_ai_work_executor,
            dry_run=args.dry_run,
            full=args.work_executor_full,
        )
        return

    if args.suggest_patch_for_work:
        print_suggest_patch_for_work_item(
            args.suggest_patch_for_work,
            use_ai=not args.no_ai_work_executor,
            dry_run=args.dry_run,
            full=args.work_executor_full,
        )
        return

    if args.create_patch_task_followups:
        print_create_patch_task_followups(args.create_patch_task_followups, project_id=args.patch_followup_project)
        return

    if args.create_patch_followups:
        print_create_patch_followups(args.create_patch_followups, project_id=args.patch_followup_project)
        return

    if args.work_cycle:
        print_work_cycle(
            project_id=args.work_cycle_project,
            max_steps=args.work_cycle_steps,
            dry_run=args.dry_run,
            use_ai=not args.no_ai_work_cycle,
            approve_work_execution=args.approve_work_cycle_actions,
            seed_if_empty=not args.no_work_cycle_seed,
            auto_create_patch_followups=not args.no_work_cycle_followups,
            auto_request_approvals=not args.no_work_cycle_approval_requests,
            auto_retry_recovery=args.work_cycle_auto_retry_recovery,
            full=args.work_cycle_full,
        )
        return

    if args.list_work_cycles:
        print_work_cycles()
        return

    if args.show_work_cycle:
        print_saved_work_cycle(args.show_work_cycle, full=args.work_cycle_full)
        return

    if args.stable_loop_preflight:
        print_stable_loop_preflight(
            project_id=args.stable_loop_project,
            max_steps=args.stable_loop_steps,
            full=args.stable_loop_full,
        )
        return

    if args.stable_loop_guardrails:
        print_stable_loop_guardrails(
            project_id=args.stable_loop_project,
            bypass=args.stable_loop_bypass_closure_guardrails,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_full,
        )
        return

    if args.stabilization_checkpoint:
        print_stabilization_checkpoint(
            project_id=args.stable_loop_project,
            full=args.stabilization_full,
            json_output=args.stabilization_json,
        )
        return

    if args.doctor:
        print_doctor(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.repair_suggestions:
        print_repair_suggestions(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.patch_integrity:
        print_patch_integrity(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_snapshot:
        print_project_snapshot(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.task_review:
        print_task_review(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.recovery_drill:
        print_recovery_drill(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.stable_loop_confidence:
        print_stable_loop_confidence(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.hardening_report:
        print_hardening_report(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.controlled_self_build and args.select_task:
        print_controlled_task_selection(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.plan_patch:
        print_patch_plan(project_id=args.stable_loop_project, target_version="12.0", full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_workspace_status or (args.controlled_self_build and args.patch_workspace_status):
        print_patch_workspace_status(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.stage_patch:
        print_stage_controlled_patch(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.preview_diff:
        print_preview_staged_diff(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.apply_staged_patch:
        print_apply_staged_patch(
            project_id=args.stable_loop_project,
            approve=args.approve_controlled_self_build,
            dry_run=args.dry_run,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.verify_latest_patch:
        print_verify_latest_patch(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rollback_latest_patch:
        print_rollback_latest_patch(
            project_id=args.stable_loop_project,
            approve=args.approve_controlled_self_build,
            dry_run=args.dry_run,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.readme_gate:
        print_readme_gate(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build_cycle:
        print_controlled_build_cycle(
            project_id=args.stable_loop_project,
            live=args.controlled_self_build_live,
            approve=args.approve_controlled_self_build,
            dry_run=args.dry_run or not args.controlled_self_build_live,
            full=args.doctor_full or args.stable_loop_full,
            json_output=args.readiness_json,
        )
        return

    if args.supervised_dev_loop:
        print_supervised_dev_loop(
            project_id=args.stable_loop_project,
            live=args.controlled_self_build_live,
            approve=args.approve_controlled_self_build,
            use_ai=(not args.no_ai_stable_loop and ai_reviews_enabled()),
            full=args.doctor_full or args.stable_loop_full,
            json_output=args.readiness_json,
        )
        return

    if args.controlled_self_build:
        print_controlled_self_build(
            project_id=args.stable_loop_project,
            max_steps=args.controlled_self_build_steps,
            live=args.controlled_self_build_live,
            approve_live=args.approve_controlled_self_build,
            use_ai=(not args.no_ai_stable_loop and ai_reviews_enabled()),
            full=args.doctor_full or args.stable_loop_full,
            json_output=args.readiness_json,
        )
        return


    if args.codebase_map:
        print_codebase_map(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.task_dependencies:
        print_task_dependencies(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.test_plan:
        print_test_plan(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_risk:
        print_patch_risk(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review:
        print_patch_review(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_memory_index:
        print_project_memory_index(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_status:
        print_workspace_status(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.cross_project_task_review:
        print_cross_project_task_review(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.asymmetric_dev_loop:
        print_asymmetric_dev_loop(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_registry:
        print_project_registry(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.register_project:
        print_register_project(
            name=args.register_project,
            root=args.workspace_project_root,
            version=args.workspace_project_version,
            language=args.workspace_project_language,
            framework_type=args.workspace_project_framework,
            readme_path=args.workspace_project_readme,
            test_commands=args.workspace_project_test_command,
            profile=args.workspace_command_profile,
            project_id=args.workspace_project_id,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.set_active_workspace_project:
        print_set_active_workspace_project(args.set_active_workspace_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_health or args.project_health_all:
        print_project_health(project_id=args.workspace_project_id or args.stable_loop_project, all_projects=args.project_health_all, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.command_profiles:
        print_command_profiles(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_dependency_map:
        print_workspace_dependency_map(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_task_inbox:
        print_workspace_task_inbox(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.switch_project:
        print_switch_workspace_project(args.switch_project, force=args.force_switch_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_context:
        print_project_context(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_timeline:
        print_workspace_timeline(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_dev_loop:
        print_workspace_dev_loop(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_registry_audit:
        print_workspace_registry_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json, archive_stale=True)
        return

    if args.workspace_repair_suggestions:
        print_workspace_repair_suggestions(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_registration_wizard:
        print_project_registration_wizard(name=args.project_registration_wizard, root=args.workspace_project_root, project_id=args.workspace_project_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_boundary_check:
        print_project_boundary_check(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_patch_plan:
        print_workspace_patch_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_preview_diff:
        print_workspace_preview_diff(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_apply:
        approved = bool(args.approve_controlled_self_build)
        print_workspace_apply(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_verify_latest:
        print_workspace_verify_latest(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.guarded_workspace_dev_loop:
        approved = bool(args.approve_controlled_self_build)
        print_guarded_workspace_dev_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_draft_request:
        print_patch_draft_request(project_id=args.workspace_project_id or args.stable_loop_project, target_version=args.patch_draft_target_version, task=args.patch_draft_task, intent=args.patch_draft_intent, risk_limit=args.patch_draft_risk_limit, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_patch:
        print_draft_patch(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_draft_status:
        print_patch_draft_status(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review_notes:
        print_patch_review_notes(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_diff:
        print_draft_diff(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_test_impact:
        print_draft_test_impact(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approve_draft:
        print_approve_draft(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reject_draft:
        print_reject_draft(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_approved_draft:
        print_apply_approved_draft(project_id=args.workspace_project_id or args.stable_loop_project, dry_run=args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rollback_approved_draft:
        approved = bool(args.approve_controlled_self_build)
        print_rollback_approved_draft(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reopen_draft:
        print_reopen_draft(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.human_approved_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_human_approved_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve_apply=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_quality:
        print_draft_quality(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_file_targets:
        print_draft_file_targets(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_intent_blocks:
        print_draft_intent_blocks(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_conflicts:
        print_draft_conflicts(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_verification_bundle:
        print_draft_verification_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_review_checklist:
        print_draft_review_checklist(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approved_draft_execution_report:
        print_approved_draft_execution_report(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.review_centered_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_review_centered_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve_apply=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_edit_proposal:
        print_code_edit_proposal(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.safe_rewrite_preview:
        print_safe_rewrite_preview(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.generate_code_patch:
        print_generated_code_patch(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.test_suggestions:
        print_test_suggestions(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.inline_review_note:
        print_inline_review_note(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, file_path=args.inline_review_file, intent_block=args.inline_review_intent, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_approved_code_patch:
        approved = bool(args.approve_controlled_self_build)
        print_apply_approved_code_patch(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.prepare_release_package:
        print_prepare_release_package(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_readiness:
        print_release_readiness(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.human_approved_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_human_approved_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve_apply=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_patch_status:
        print_code_patch_status(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.symbol_scan:
        print_symbol_scan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rewrite_plan:
        print_rewrite_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rewrite_conflicts:
        print_rewrite_conflicts(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_patch_diff_bundle:
        print_code_patch_diff_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_code_patch_transaction:
        approved = bool(args.approve_controlled_self_build)
        print_apply_code_patch_transaction(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.semantic_checks:
        print_semantic_checks(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_artifact:
        print_release_artifact(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_audit_trail:
        print_release_audit_trail(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.generated_code_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_generated_code_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.task_to_code_patch:
        print_task_to_code_patch(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_context:
        print_code_context(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_prompt:
        print_patch_prompt(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.parse_generated_edits:
        print_parse_generated_edits(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.edit_consistency:
        print_edit_consistency(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_code_patch_dry_run:
        print_ai_code_patch_dry_run(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_failure_analysis:
        print_patch_failure_analysis(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_learning_notes:
        print_patch_learning_notes(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_assisted_code_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_ai_assisted_code_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.refine_patch_objective:
        print_patch_objective_refinement(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rank_code_context:
        print_code_context_ranking(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_safety_envelope:
        print_patch_safety_envelope(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.validate_generated_patch:
        print_generated_patch_validation(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_simulation:
        print_patch_simulation(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.test_stub_plan:
        print_test_stub_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review_score:
        print_patch_review_score(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_recovery_plan:
        print_patch_recovery_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.validated_ai_code_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_validated_ai_code_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_patch_review_bundle:
        print_ai_patch_review_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_patch_review_integrity:
        print_review_bundle_integrity(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_ready:
        print_approval_ready(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_ledger:
        print_approval_ledger(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_validated_ai_patch:
        approved = bool(args.approve_controlled_self_build)
        print_apply_validated_ai_patch(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.post_apply_review:
        print_post_apply_review(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_build_plan:
        print_package_build_plan(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_to_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_approval_to_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.bind_validated_approval:
        print_bind_validated_approval(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.refresh_ai_patch_review_bundle:
        print_ai_patch_review_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_manifest_integrity:
        print_release_manifest_integrity(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_inventory:
        print_package_inventory(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_checksums:
        print_package_checksums(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_notes:
        print_release_notes(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_handoff_report:
        print_release_handoff_report(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.build_release_zip:
        approved = bool(args.approve_controlled_self_build)
        print_build_release_zip(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, confirm=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verify_release_unzip:
        print_verify_release_unzip(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_pipeline_audit:
        print_release_pipeline_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verified_release_package_loop:
        approved = bool(args.approve_controlled_self_build)
        print_verified_release_package_loop(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, confirm=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_profiles:
        print_release_profiles(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_privacy_scan:
        print_package_privacy_scan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.portable_metadata_check:
        print_portable_metadata_check(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.first_run_check:
        print_first_run_check(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dependency_advisor:
        print_dependency_advisor(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.upgrade_notes:
        print_upgrade_notes(project_id=args.workspace_project_id or args.stable_loop_project, to_version=args.patch_draft_target_version, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.runtime_migration_check:
        print_runtime_migration_check(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_install_verification:
        print_release_install_verification(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, run_smoke=args.run_install_smoke, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verified_installable_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_verified_installable_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, confirm=approved, dry_run=not approved or args.dry_run, run_smoke=args.run_install_smoke, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.smoke_runtime_hardening:
        print_smoke_runtime_hardening(project_id=args.workspace_project_id or args.stable_loop_project, tier=args.smoke_tier, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.external_zip_install_verification:
        print_external_zip_install_verification(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.deterministic_release_manifest:
        print_deterministic_release_manifest(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.update_dry_run_plan:
        print_update_dry_run_plan(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.atomic_source_update:
        approved = bool(args.approve_controlled_self_build)
        print_atomic_source_update(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, expected_manifest_hash=args.expected_manifest_hash, confirm=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.runtime_migration_assistant:
        approved = bool(args.approve_controlled_self_build)
        print_runtime_migration_assistant(project_id=args.workspace_project_id or args.stable_loop_project, confirm=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.route_safety_harness:
        print_route_safety_harness(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_dashboard_command_center:
        print_release_dashboard_command_center(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.clean_room_install_harness:
        print_clean_room_install_harness(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, run_smoke_tier=args.smoke_tier, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verified_self_update_release_pipeline:
        approved = bool(args.approve_controlled_self_build)
        print_verified_self_update_release_pipeline(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, expected_manifest_hash=args.expected_manifest_hash, confirm=approved, dry_run=not approved or args.dry_run, run_clean_room=args.run_clean_room, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.trial_upgrade_from_zip:
        print_trial_upgrade_harness(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, run_smoke_tier=args.smoke_tier, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.backup_rollback_drill:
        print_backup_rollback_drill(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.update_collision_detector:
        print_update_collision_detector(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.version_registry_report:
        print_version_registry_report(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, dry_run=not args.approve_controlled_self_build, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_provenance_report:
        print_release_provenance_report(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dashboard_upgrade_wizard_preview:
        print_dashboard_upgrade_wizard_preview(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.api_upgrade_wizard_preview:
        print_api_upgrade_wizard_preview(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.staged_apply_drill:
        print_staged_apply_drill(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.real_apply_guard_rails:
        print_real_apply_guard_rails(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, expected_manifest_hash=args.expected_manifest_hash, confirm_phrase=args.release_confirm_phrase, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.real_apply_rollback_verification:
        print_real_apply_rollback_verification(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.self_update_ux_polish:
        print_self_update_ux_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.v23_readiness_gate:
        print_v23_readiness_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, run_heavy=args.run_heavy_release_checks, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_maintenance_loop:
        print_v45_controlled_self_maintenance_loop(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_maintenance_work_queue:
        print_v46_controlled_self_maintenance_work_queue(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_attention_scheduler:
        print_v47_controlled_attention_scheduler(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.attention_selection_receipt:
        print_v47_attention_selection_receipt(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v47_1_attention_receipt_gate:
        print_v47_pre_v47_1_attention_receipt_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.attention_budget_ledger:
        print_v48_attention_budget_ledger(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.deferred_task_memory:
        print_v48_deferred_task_memory(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.blocked_task_handling:
        print_v48_blocked_task_handling(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.attention_resume_context:
        print_v48_attention_resume_context(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.attention_dashboard_polish:
        print_v48_attention_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.attention_api_parity_gate:
        print_v48_attention_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_hooks_read_only:
        print_v48_reflection_hooks_read_only(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v48_reflection_gate:
        print_v48_pre_v48_reflection_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_memory_loop:
        print_v48_controlled_reflection_memory_loop(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_review_receipts:
        print_v49_reflection_review_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_candidate_deduplication:
        print_v49_reflection_candidate_deduplication(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_rejection_memory:
        print_v49_reflection_rejection_memory(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_promotion_drafts:
        print_v49_reflection_promotion_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_safety_classifier:
        print_v49_memory_safety_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_dashboard_polish:
        print_v49_reflection_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_api_parity_gate:
        print_v49_reflection_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reflection_privacy_package_hardening:
        print_v49_reflection_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v49_identity_continuity_gate:
        print_v49_pre_v49_identity_continuity_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_continuity_layer:
        print_v49_identity_continuity_layer(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_receipts:
        print_v50_0_identity_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v49_1_identity_receipts_gate:
        print_v50_0_pre_v49_1_identity_receipts_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.stable_principles_ledger:
        print_v50_stable_principles_ledger(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_drift_classifier:
        print_v50_identity_drift_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_snapshot_comparison:
        print_v50_identity_snapshot_comparison(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.operator_identity_review_drafts:
        print_v50_operator_identity_review_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_dashboard_polish:
        print_v50_identity_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_api_parity_gate:
        print_v50_identity_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.identity_privacy_package_hardening:
        print_v50_identity_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v50_durable_memory_gate:
        print_v50_pre_v50_durable_memory_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.durable_memory_promotion:
        print_v50_supervised_durable_memory_promotion(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_promotion_receipts:
        print_v51_memory_promotion_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_promotion_deduplication:
        print_v51_memory_promotion_deduplication(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_rejection_runtime_ledger:
        print_v51_memory_rejection_runtime_ledger(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_promotion_confirmation_gate:
        print_v51_memory_promotion_confirmation_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, promotion_id=args.memory_promotion_id or None, confirmation=args.memory_confirm_phrase or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_removal_drafts:
        print_v51_memory_removal_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_dashboard_polish:
        print_v51_memory_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_api_parity_gate:
        print_v51_memory_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_privacy_package_hardening:
        print_v51_memory_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v51_durable_write_gate:
        print_v51_pre_v51_durable_write_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.durable_memory_write:
        print_v51_controlled_durable_memory_write_path(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, promotion_id=args.memory_promotion_id or None, confirmation=args.memory_confirm_phrase or None, execute=bool(args.execute_durable_memory_write), full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.durable_memory_write_receipts:
        print_v52_durable_memory_write_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_store_schema_hardening:
        print_v52_memory_store_schema_hardening(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_read_path:
        print_v52_memory_read_path(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_search_filter:
        print_v52_memory_search_filter(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, memory_type=args.memory_type or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_correction_drafts:
        print_v52_memory_correction_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_removal_confirmation_path:
        print_v52_memory_removal_confirmation_path(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, memory_id=args.memory_id or None, confirmation=args.memory_confirm_phrase or None, execute=bool(args.execute_memory_removal), full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_store_dashboard_polish:
        print_v52_memory_store_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_store_api_parity_gate:
        print_v52_memory_store_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v52_recall_gate:
        print_v52_pre_v52_recall_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_recall_self_context:
        print_v52_memory_recall_self_context(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_recall_receipts:
        print_v53_memory_recall_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.recall_conflict_resolver:
        print_v53_recall_conflict_resolver(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.stale_memory_handling:
        print_v53_stale_memory_handling(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.recall_scope_controls:
        print_v53_recall_scope_controls(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, scope=args.recall_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.recall_privacy_classifier:
        print_v53_recall_privacy_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.recall_dashboard_polish:
        print_v53_recall_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.recall_api_parity_gate:
        print_v53_recall_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.recall_privacy_package_hardening:
        print_v53_recall_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v53_memory_informed_planning_gate:
        print_v53_pre_v53_memory_informed_planning_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_informed_planning:
        print_v53_memory_informed_planning_loop(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.memory_informed_planning_receipts:
        print_v54_memory_informed_planning_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.plan_conflict_classifier:
        print_v54_plan_conflict_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.plan_revision_drafts:
        print_v54_plan_revision_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.planning_scope_controls:
        print_v54_planning_scope_controls(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.planning_risk_budget:
        print_v54_planning_risk_budget(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.planning_dashboard_polish:
        print_v54_planning_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.planning_api_parity_gate:
        print_v54_planning_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.planning_privacy_package_hardening:
        print_v54_planning_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v54_action_planning_gate:
        print_v54_pre_v54_action_planning_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.supervised_action_planning:
        print_v54_supervised_action_planning_loop(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return


    if args.action_plan_receipts:
        print_v55_action_plan_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_step_classifier:
        print_v55_action_step_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_dependency_graph:
        print_v55_action_dependency_graph(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_risk_budget:
        print_v55_action_risk_budget(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_rehearsal_dry_run_preview:
        print_v55_action_rehearsal_dry_run_preview(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_dashboard_polish:
        print_v55_action_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_api_parity_gate:
        print_v55_action_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.action_privacy_package_hardening:
        print_v55_action_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v55_controlled_execution_gate:
        print_v55_pre_v55_controlled_execution_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_action_execution_preview:
        print_v55_controlled_action_execution_preview(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, action_plan_id=args.action_plan_id or None, confirmation=args.action_confirm_phrase or None, execute_preview=args.execute_action_preview, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.execution_preview_receipts:
        print_v56_execution_preview_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.execution_step_permission_classifier:
        print_v56_execution_step_permission_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.read_only_command_allowlist:
        print_v56_read_only_command_allowlist(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.execution_sandbox_evidence_binder:
        print_v56_execution_sandbox_evidence_binder(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.execution_result_receipts:
        print_v56_execution_result_receipts(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.execution_dashboard_polish:
        print_v56_execution_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.execution_api_parity_gate:
        print_v56_execution_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.execution_privacy_package_hardening:
        print_v56_execution_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v56_read_only_execution_gate:
        print_v56_pre_v56_read_only_execution_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_read_only_action_execution:
        print_v56_controlled_read_only_action_execution(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, confirmation=args.read_only_confirm_phrase or None, execute=args.execute_read_only_action, goal=args.autonomy_goal or None, query=args.memory_query or args.autonomy_goal or None, planning_scope=args.planning_scope or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.read_only_execution_receipts:
        print_v57_read_only_execution_receipts(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.expanded_diagnostic_allowlist:
        print_v57_expanded_diagnostic_allowlist(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.read_only_output_classifier:
        print_v57_read_only_output_classifier(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.diagnostic_evidence_binder:
        print_v57_diagnostic_evidence_binder(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.diagnostic_result_summaries:
        print_v57_diagnostic_result_summaries(project_id=args.workspace_project_id or args.stable_loop_project, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.read_only_execution_dashboard_polish:
        print_v57_read_only_execution_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.read_only_execution_api_parity_gate:
        print_v57_read_only_execution_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.read_only_execution_privacy_package_hardening:
        print_v57_read_only_execution_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v57_evidence_gathering_gate:
        print_v57_pre_v57_evidence_gathering_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_gathering_maintenance_loop:
        print_v57_evidence_gathering_maintenance_loop(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, confirmation=args.read_only_confirm_phrase or None, execute=args.execute_read_only_action, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_collection_receipts:
        print_v58_evidence_collection_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.diagnostic_issue_classifier:
        print_v58_diagnostic_issue_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_conflict_staleness_resolver:
        print_v58_evidence_conflict_staleness_resolver(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_to_plan_update_drafts:
        print_v58_evidence_to_plan_update_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.diagnostic_coverage_map:
        print_v58_diagnostic_coverage_map(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_dashboard_polish:
        print_v58_evidence_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_api_parity_gate:
        print_v58_evidence_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_privacy_package_hardening:
        print_v58_evidence_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v58_patch_proposal_gate:
        print_v58_pre_v58_patch_proposal_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_grounded_patch_proposal:
        print_v58_evidence_grounded_patch_proposal_loop(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_proposal_receipts:
        print_v59_patch_proposal_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_scope_classifier:
        print_v59_patch_scope_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_risk_budget:
        print_v59_patch_risk_budget(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_diff_preview_drafts:
        print_v59_patch_diff_preview_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_verification_plan:
        print_v59_patch_verification_plan(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_dashboard_polish:
        print_v59_patch_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_api_parity_gate:
        print_v59_patch_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_privacy_package_hardening:
        print_v59_patch_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v59_sandbox_patch_execution_gate:
        print_v59_pre_v59_sandbox_patch_execution_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_sandbox_patch_execution:
        print_v59_controlled_sandbox_patch_execution(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, confirmation=args.sandbox_patch_confirm_phrase or None, execute=args.execute_sandbox_patch, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.sandbox_execution_receipts:
        print_v60_sandbox_execution_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_verification_matrix:
        print_v60_sandbox_verification_matrix(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_drift_detector:
        print_v60_sandbox_drift_detector(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_rollback_rehearsal:
        print_v60_sandbox_rollback_rehearsal(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_apply_candidate_drafts:
        print_v60_sandbox_apply_candidate_drafts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_dashboard_polish:
        print_v60_sandbox_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_api_parity_gate:
        print_v60_sandbox_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_privacy_package_hardening:
        print_v60_sandbox_privacy_package_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v60_source_apply_handoff_gate:
        print_v60_pre_v60_source_apply_handoff_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_sandbox_source_apply_handoff:
        print_v60_controlled_sandbox_source_apply_handoff(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, confirmation=args.source_apply_handoff_confirm_phrase or None, execute=args.record_source_apply_handoff, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.source_apply_handoff_receipts:
        print_v61_source_apply_handoff_receipts(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_baseline_drift_resolver:
        print_v61_source_baseline_drift_resolver(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.reviewed_artifact_set_binder:
        print_v61_reviewed_artifact_set_binder(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_handoff_eligibility:
        print_v61_source_apply_handoff_eligibility_classifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_dry_run_bridge:
        print_v61_source_apply_dry_run_bridge(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_handoff_dashboard_polish:
        print_v61_source_apply_handoff_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_handoff_api_parity_gate:
        print_v61_source_apply_handoff_api_parity_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_handoff_privacy_hardening:
        print_v61_source_apply_handoff_privacy_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v61_controlled_apply_bridge_gate:
        print_v61_pre_v61_controlled_apply_bridge_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_source_apply_bridge_refinement:
        print_v61_controlled_source_apply_bridge_refinement(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_transaction_planner:
        print_v62_source_apply_transaction_planner(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_backup_binder:
        print_v62_source_apply_backup_binder(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_transaction_dry_run_verifier:
        print_v62_source_apply_transaction_dry_run_verifier(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_transaction_confirmation_gate:
        print_v62_source_apply_transaction_confirmation_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, confirmation=args.transaction_confirm_phrase or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_source_apply_executor:
        print_v62_supervised_source_apply_executor(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, confirmation=args.transaction_confirm_phrase or None, approve=args.approve_source_apply_transaction, dry_run=args.dry_run or not args.approve_source_apply_transaction, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_apply_verification_runner:
        print_v62_post_apply_verification_runner(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_rollback_rehearsal:
        print_v62_transaction_rollback_rehearsal(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_transaction_dashboard_command_center:
        print_v62_source_apply_transaction_dashboard_command_center(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v62_transaction_release_gate:
        print_v62_pre_v62_transaction_release_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_source_apply_transaction_layer:
        print_v62_supervised_source_apply_transaction_layer(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_receipt_ledger:
        print_v63_transaction_receipt_ledger(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_diff_viewer:
        print_v63_transaction_diff_viewer(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_conflict_detector:
        print_v63_transaction_conflict_detector(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_approval_record_binder:
        print_v63_transaction_approval_record_binder(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_package_evidence_exporter:
        print_v63_transaction_package_evidence_exporter(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_replay_audit:
        print_v63_transaction_replay_audit(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_dashboard_receipt_timeline:
        print_v63_transaction_dashboard_receipt_timeline(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_api_search_filtering:
        print_v63_transaction_api_search_filtering(project_id=args.workspace_project_id or args.stable_loop_project, transaction_id=args.transaction_filter_id or None, status_filter=args.transaction_filter_status or None, stage_filter=args.transaction_filter_stage or None, file_touched=args.transaction_filter_file or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v63_transaction_evidence_gate:
        print_v63_pre_v63_transaction_evidence_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.durable_transaction_evidence_system:
        print_v63_durable_transaction_evidence_system(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, command_key=args.read_only_command_key, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_evidence_summarizer:
        print_v64_transaction_evidence_summarizer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_candidate_registry:
        print_v64_improvement_candidate_registry(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_based_candidate_scoring:
        print_v64_evidence_based_candidate_scoring(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_regression_pattern_detector:
        print_v64_improvement_regression_pattern_detector(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_risk_blast_radius_forecaster:
        print_v64_improvement_risk_blast_radius_forecaster(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_recommendation_queue:
        print_v64_supervised_recommendation_queue(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_intelligence_dashboard:
        print_v64_improvement_intelligence_dashboard(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_intelligence_api_cli_access:
        print_v64_improvement_intelligence_api_cli_access(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v64_improvement_intelligence_gate:
        print_v64_pre_v64_improvement_intelligence_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_improvement_intelligence_layer:
        print_v64_supervised_improvement_intelligence_layer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.accepted_recommendation_intake:
        print_v65_accepted_recommendation_intake(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_draft_skeleton:
        print_v65_proposal_draft_skeleton(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_requirement_mapper:
        print_v65_evidence_requirement_mapper(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_risk_contract:
        print_v65_proposal_risk_contract(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_patch_request_compiler:
        print_v65_sandbox_patch_request_compiler(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_review_packet_binder:
        print_v65_proposal_review_packet_binder(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_dashboard_review_console:
        print_v65_proposal_dashboard_review_console(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_api_cli_access:
        print_v65_proposal_api_cli_access(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v65_proposal_drafting_gate:
        print_v65_pre_v65_proposal_drafting_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.recommendation_to_proposal_drafting_layer:
        print_v65_recommendation_to_proposal_drafting_layer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.reviewed_proposal_acceptance_gate:
        print_v66_reviewed_proposal_acceptance_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_workspace_plan:
        print_v66_sandbox_workspace_plan(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_implementation_request:
        print_v66_patch_implementation_request(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_sandbox_execution_harness:
        print_v66_proposal_sandbox_execution_harness(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, execute_copy=args.proposal_sandbox_execute_copy, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_sandbox_verification_matrix:
        print_v66_proposal_sandbox_verification_matrix(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_sandbox_evidence_binder:
        print_v66_proposal_sandbox_evidence_binder(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_sandbox_failure_triage:
        print_v66_proposal_sandbox_failure_triage(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_sandbox_api_cli_access:
        print_v66_proposal_sandbox_api_cli_access(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v66_proposal_sandbox_gate:
        print_v66_pre_v66_proposal_sandbox_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.reviewed_proposal_sandbox_execution_layer:
        print_v66_reviewed_proposal_sandbox_execution_layer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_promotion_candidate:
        print_v67_sandbox_promotion_candidate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_source_diff_normalizer:
        print_v67_sandbox_source_diff_normalizer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.promotion_safety_boundary_gate:
        print_v67_promotion_safety_boundary_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_draft_from_sandbox:
        print_v67_transaction_draft_from_sandbox(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.promotion_review_packet_binder:
        print_v67_promotion_review_packet_binder(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.promotion_conflict_staleness_detector:
        print_v67_promotion_conflict_staleness_detector(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_promotion_api_cli_access:
        print_v67_sandbox_promotion_api_cli_access(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v67_sandbox_promotion_gate:
        print_v67_pre_v67_sandbox_promotion_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_evidence_promotion_handoff_layer:
        print_v67_sandbox_evidence_promotion_handoff_layer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.promotion_packet_intake_gate:
        print_v68_promotion_packet_intake_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_plan_materializer:
        print_v68_transaction_plan_materializer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_baseline_reconciliation:
        print_v68_source_baseline_reconciliation(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.backup_rollback_preflight_binder:
        print_v68_backup_rollback_preflight_binder(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.final_transaction_safety_gate:
        print_v68_final_transaction_safety_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_ledger_preregistration:
        print_v68_transaction_ledger_preregistration(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_transaction_review_console:
        print_v68_source_transaction_review_console(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_review_api_cli_access:
        print_v68_transaction_review_api_cli_access(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v68_transaction_integration_gate:
        print_v68_pre_v68_transaction_integration_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.promotion_to_transaction_integration_layer:
        print_v68_promotion_to_transaction_integration_layer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.transaction_execution_eligibility:
        print_v69_transaction_execution_eligibility(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.exact_confirmation_binder:
        print_v69_exact_confirmation_binder(project_id=args.workspace_project_id or args.stable_loop_project, confirmation_phrase=args.transaction_confirm_phrase, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.backup_snapshot_materializer:
        print_v69_backup_snapshot_materializer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_apply_rehearsal:
        print_v69_transaction_apply_rehearsal(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_confirmed_apply_executor:
        print_v69_operator_confirmed_apply_executor(project_id=args.workspace_project_id or args.stable_loop_project, confirmation_phrase=args.transaction_confirm_phrase, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_execution_verification:
        print_v69_post_execution_verification(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.rollback_recommendation_gate:
        print_v69_rollback_recommendation_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.transaction_execution_dashboard_api_cli:
        print_v69_transaction_execution_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v69_execution_gate:
        print_v69_pre_v69_execution_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_confirmed_transaction_execution_layer:
        print_v69_operator_confirmed_transaction_execution_layer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.execution_result_ledger_finalizer:
        print_v70_execution_result_ledger_finalizer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.rollback_decision_resolver:
        print_v70_rollback_decision_resolver(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_confirmed_rollback_executor:
        print_v70_operator_confirmed_rollback_executor(project_id=args.workspace_project_id or args.stable_loop_project, rollback_confirmation_phrase=args.rollback_confirm_phrase, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_rollback_verification:
        print_v70_post_rollback_verification(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_candidate_finalization_gate:
        print_v70_release_candidate_finalization_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_only_package_certifier:
        print_v70_source_only_package_certifier(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_finalization_dashboard_api_cli:
        print_v70_release_finalization_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.recovery_simulation_harness:
        print_v70_recovery_simulation_harness(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v70_recovery_finalization_gate:
        print_v70_pre_v70_recovery_finalization_gate(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.verified_execution_recovery_release_layer:
        print_v70_verified_execution_recovery_release_layer(project_id=args.workspace_project_id or args.stable_loop_project, recommendation_id=args.proposal_recommendation_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.source_tree_inventory:
        print_v71_source_tree_inventory(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.module_responsibility_map:
        print_v71_module_responsibility_map(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.dependency_call_surface_map:
        print_v71_dependency_call_surface_map(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.module_risk_profile:
        print_v71_module_risk_profile(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.historical_failure_memory:
        print_v71_historical_failure_memory(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.verification_command_map:
        print_v71_verification_command_map(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_opportunity_detector:
        print_v71_improvement_opportunity_detector(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.codebase_understanding_dashboard_api_cli:
        print_v71_codebase_understanding_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v71_codebase_understanding_gate:
        print_v71_pre_v71_codebase_understanding_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.codebase_understanding_map:
        print_v71_codebase_understanding_map(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_goal_intake_classifier:
        print_v72_patch_goal_intake_classifier(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.relevant_file_context_selector:
        print_v72_relevant_file_context_selector(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.historical_failure_context_binder:
        print_v72_historical_failure_context_binder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.risk_aware_context_budgeter:
        print_v72_risk_aware_context_budgeter(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.verification_requirement_compiler:
        print_v72_verification_requirement_compiler(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_prompt_context_packet_builder:
        print_v72_patch_prompt_context_packet_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.context_completeness_reviewer:
        print_v72_context_completeness_reviewer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_context_dashboard_api_cli:
        print_v72_patch_context_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v72_patch_context_gate:
        print_v72_pre_v72_patch_context_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_generation_context_builder:
        print_v72_patch_generation_context_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_intent_normalizer:
        print_v73_patch_intent_normalizer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_scope_contract_builder:
        print_v73_patch_scope_contract_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_prompt_composer:
        print_v73_patch_prompt_composer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_draft_output_schema:
        print_v73_patch_draft_output_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_draft_safety_reviewer:
        print_v73_patch_draft_safety_reviewer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_draft_evidence_binder:
        print_v73_patch_draft_evidence_binder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_draft_dashboard_api_cli:
        print_v73_patch_draft_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.local_model_handoff_stub:
        print_v73_local_model_handoff_stub(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v73_patch_draft_gate:
        print_v73_pre_v73_patch_draft_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_patch_draft_composer:
        print_v73_supervised_patch_draft_composer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review_intake:
        print_v74_patch_review_intake_parser(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_diff_boundary:
        print_v74_patch_review_diff_boundary_extractor(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_scope:
        print_v74_patch_review_scope_contract_validator(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_safety:
        print_v74_patch_review_safety_boundary_validator(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_docs:
        print_v74_documentation_update_validator(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_verification:
        print_v74_verification_plan_validator(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_risk:
        print_v74_patch_risk_scorer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_report:
        print_v74_patch_review_report_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_dashboard_api_cli:
        print_v74_patch_review_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v74_patch_review_gate:
        print_v74_pre_v74_patch_review_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_draft_review_diff_validation_layer:
        print_v74_patch_draft_review_diff_validation_layer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_trial_intake:
        print_v75_patch_trial_intake_binder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_workspace:
        print_v75_disposable_workspace_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_materialize:
        print_v75_patch_draft_materializer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_verify:
        print_v75_sandbox_verification_runner(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_evidence:
        print_v75_sandbox_evidence_collector(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_escape_guard:
        print_v75_sandbox_escape_mutation_guard(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_dashboard_api_cli:
        print_v75_patch_trial_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_cleanup:
        print_v75_patch_trial_cleanup_retention(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, cleanup=True, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_trial_list:
        print_v75_patch_trial_cleanup_retention(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, cleanup=False, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v75_sandbox_trial_gate:
        print_v75_pre_v75_sandbox_trial_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_patch_trial_runner:
        print_v75_sandbox_patch_trial_runner(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_evidence_intake:
        print_v76_patch_evidence_intake_reader(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_integrity:
        print_v76_trial_integrity_validator(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_verification:
        print_v76_verification_evidence_scorer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_scope_docs:
        print_v76_scope_documentation_evidence_reviewer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_risk:
        print_v76_risk_acceptance_classifier(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_readiness:
        print_v76_promotion_readiness_packet_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_dashboard_api_cli:
        print_v76_patch_evidence_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_evidence_archive:
        print_v76_recommendation_archive_comparison(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v76_evidence_review_gate:
        print_v76_pre_v76_evidence_review_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_evidence_review_recommendation_layer:
        print_v76_sandbox_evidence_review_recommendation_layer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, full=args.doctor_full, json_output=args.readiness_json)
        return

    patch_apply_dry_run = not args.patch_apply_live
    if args.patch_apply_approval:
        print_v77_patch_approval_intake_contract(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_apply_bind:
        print_v77_recommendation_approval_binder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_apply_snapshot:
        print_v77_live_source_snapshot_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_apply_materialize:
        print_v77_approved_patch_materializer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, dry_run=patch_apply_dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_apply_verify:
        print_v77_post_apply_verification_runner(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, dry_run=patch_apply_dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_apply_rollback:
        print_v77_automatic_rollback_executor(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, dry_run=patch_apply_dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_apply_evidence:
        print_v77_application_evidence_recorder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, dry_run=patch_apply_dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_application_dashboard_api_cli:
        print_v77_patch_application_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v77_application_gate:
        print_v77_pre_v77_application_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.operator_approved_patch_application_layer:
        print_v77_operator_approved_patch_application_layer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approval_phrase=args.approval_phrase, approved_files=args.patch_approved_files, application_id=args.patch_application_id, operator_label=args.approver_label, apply_approved=args.patch_apply_approved, dry_run=patch_apply_dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_recovery_preflight:
        print_v78_dirty_tree_preflight_detector(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_snapshot:
        print_v78_snapshot_completeness_validator(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_partial_apply:
        print_v78_partial_apply_detector(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_rollback_integrity:
        print_v78_rollback_integrity_verifier(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_triage:
        print_v78_failed_verification_triage(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_recommendation:
        print_v78_recovery_recommendation_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_timeline:
        print_v78_application_audit_timeline(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_recovery_dashboard_api_cli:
        print_v78_patch_recovery_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v78_recovery_gate:
        print_v78_pre_v78_recovery_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.verified_application_recovery_rollback_hardening:
        print_v78_verified_application_recovery_rollback_hardening(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, draft_file=args.patch_draft_file, trial_id=args.patch_trial_id, evidence_file=args.patch_evidence_file, approval_file=args.patch_approval_file, approved_files=args.patch_approved_files, application_id=args.patch_application_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_queue_schema:
        print_v79_patch_queue_record_schema(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_intake:
        print_v79_patch_queue_intake_organizer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_conflicts:
        print_v79_patch_queue_conflict_detector(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_priority:
        print_v79_patch_queue_risk_priority_scheduler(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_stale_evidence:
        print_v79_patch_queue_stale_evidence_detector(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_serial_plan:
        print_v79_patch_queue_serial_trial_plan_builder(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_review_packet:
        print_v79_patch_queue_operator_review_packet(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_queue_dashboard_api_cli:
        print_v79_patch_queue_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v79_queue_gate:
        print_v79_pre_v79_queue_gate(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.multi_patch_queue_planning_layer:
        print_v79_multi_patch_queue_planning_layer(project_id=args.workspace_project_id or args.stable_loop_project, patch_goal=args.patch_goal, queue_file=args.patch_queue_file, queue_id=args.patch_queue_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.improvement_opportunity_intake:
        print_v80_improvement_opportunity_intake(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_cycle_state_machine:
        print_v80_improvement_cycle_state_machine(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pipeline_stage_binder:
        print_v80_pipeline_stage_binder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.local_model_invocation_stub:
        print_v80_local_model_invocation_stub(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_loop_evidence_recorder:
        print_v80_improvement_loop_evidence_recorder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_stop_gate:
        print_v80_operator_stop_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.improvement_loop_dashboard_api_cli:
        print_v80_improvement_loop_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.loop_safety_auditor:
        print_v80_loop_safety_auditor(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v80_supervised_loop_gate:
        print_v80_pre_v80_supervised_loop_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_local_improvement_loop:
        print_v80_supervised_local_improvement_loop(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.local_model_adapter_contract:
        print_v81_local_model_adapter_contract(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.model_capability_profile:
        print_v81_model_capability_profile(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.prompt_export_invocation_guard:
        print_v81_prompt_export_invocation_guard(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_capture_parser:
        print_v81_proposal_capture_parser(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_safety_precheck:
        print_v81_proposal_safety_precheck(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.model_output_provenance_recorder:
        print_v81_model_output_provenance_recorder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_integration_dashboard_api_cli:
        print_v81_proposal_integration_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.disabled_by_default_invocation_gate:
        print_v81_disabled_by_default_invocation_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v81_model_integration_gate:
        print_v81_pre_v81_model_integration_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.local_model_patch_proposal_integration:
        print_v81_local_model_patch_proposal_integration(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_collection_intake:
        print_v82_proposal_collection_intake(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.candidate_diff_normalizer:
        print_v82_candidate_diff_normalizer(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.proposal_quality_heuristic_scorer:
        print_v82_proposal_quality_heuristic_scorer(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.safety_scope_comparison:
        print_v82_safety_scope_comparison(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.verification_plan_comparison:
        print_v82_verification_plan_comparison(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.critique_report_builder:
        print_v82_critique_report_builder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.critique_dashboard_api_cli:
        print_v82_critique_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_review_bundle_exporter:
        print_v82_operator_review_bundle_exporter(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v82_output_critique_gate:
        print_v82_pre_v82_output_critique_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.local_model_output_comparison_critique:
        print_v82_local_model_output_comparison_critique(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.candidate_registry_schema:
        print_v83_candidate_registry_schema(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.candidate_deduplication:
        print_v83_candidate_deduplication(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.risk_weighted_ranking:
        print_v83_risk_weighted_ranking(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.conflict_aware_grouping:
        print_v83_conflict_aware_grouping(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.evidence_completeness_ranker:
        print_v83_evidence_completeness_ranker(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.ranking_explainer:
        print_v83_ranking_explainer(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.ranking_dashboard_api_cli:
        print_v83_ranking_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_selection_packet:
        print_v83_operator_selection_packet(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v83_ranking_gate:
        print_v83_pre_v83_ranking_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.multi_model_patch_candidate_ranking:
        print_v83_multi_model_patch_candidate_ranking(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.refinement_goal_binder:
        print_v84_refinement_goal_binder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.critique_revision_prompt_builder:
        print_v84_critique_revision_prompt_builder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.constrained_revision_scope_builder:
        print_v84_constrained_revision_scope_builder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.refinement_safety_reviewer:
        print_v84_refinement_safety_reviewer(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.refinement_evidence_recorder:
        print_v84_refinement_evidence_recorder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.refinement_iteration_limiter:
        print_v84_refinement_iteration_limiter(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.refinement_dashboard_api_cli:
        print_v84_refinement_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_revision_packet:
        print_v84_operator_revision_packet(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v84_refinement_gate:
        print_v84_pre_v84_refinement_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_patch_candidate_refinement:
        print_v84_supervised_patch_candidate_refinement(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_source_intake:
        print_v85_suggestion_source_intake(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_cycle_state_machine:
        print_v85_suggestion_cycle_state_machine(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.recurring_suggestion_budgeter:
        print_v85_recurring_suggestion_budgeter(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.safety_boundary_enforcer:
        print_v85_safety_boundary_enforcer(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_deduplication_memory:
        print_v85_suggestion_deduplication_memory(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_attention_packet:
        print_v85_operator_attention_packet(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_loop_dashboard_api_cli:
        print_v85_suggestion_loop_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.no_autonomous_apply_auditor:
        print_v85_no_autonomous_apply_auditor(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v85_suggestion_loop_gate:
        print_v85_pre_v85_suggestion_loop_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.safe_autonomous_suggestion_loop:
        print_v85_safe_autonomous_suggestion_loop(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, model_name=args.local_model_name, cycle_id=args.improvement_cycle_id, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_inbox_record_schema:
        print_v86_suggestion_inbox_record_schema(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_intake_normalizer:
        print_v86_suggestion_intake_normalizer(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_deduplication_drift_resolver:
        print_v86_suggestion_deduplication_drift_resolver(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_triage_state_machine:
        print_v86_operator_triage_state_machine(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.work_order_draft_builder:
        print_v86_work_order_draft_builder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.safety_scope_contract_binder:
        print_v86_safety_scope_contract_binder(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pipeline_handoff_planner:
        print_v86_pipeline_handoff_planner(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.suggestion_inbox_dashboard_api_cli:
        print_v86_suggestion_inbox_dashboard_api_cli(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v86_suggestion_inbox_gate:
        print_v86_pre_v86_suggestion_inbox_gate(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.supervised_suggestion_inbox_work_order_planner:
        print_v86_supervised_suggestion_inbox_work_order_planner(project_id=args.workspace_project_id or args.stable_loop_project, improvement_goal=args.improvement_goal or args.patch_goal, candidate_file=args.candidate_file, full=args.doctor_full, json_output=args.readiness_json)
        return

    for _flag_name, _slug in sm_v90.SUPERVISED_DEV_CLI_MAP.items():
        if getattr(args, _flag_name.replace("-", "_"), False):
            getattr(sm_v90, f"print_{_slug}")(
                project_id=args.workspace_project_id or args.stable_loop_project,
                improvement_goal=args.improvement_goal or args.patch_goal,
                candidate_file=args.candidate_file,
                full=args.doctor_full,
                json_output=args.readiness_json,
            )
            return

    for _flag_name, _slug in getattr(sm_v90, "SUPERVISED_RUNTIME_CLI_MAP", {}).items():
        if getattr(args, _flag_name.replace("-", "_"), False):
            getattr(sm_v90, f"print_{_slug}")(
                project_id=args.workspace_project_id or args.stable_loop_project,
                improvement_goal=args.improvement_goal or args.patch_goal,
                candidate_file=args.candidate_file,
                full=args.doctor_full,
                json_output=args.readiness_json,
            )
            return

    if args.self_maintenance_proposal:
        print_self_maintenance_proposal(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.build_patch_plan:
        print_patch_plan_builder(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.generate_maintenance_patch:
        print_dry_run_patch_generator(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_safety_audit:
        print_patch_safety_auditor(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_maintenance_patch_to_temp:
        print_apply_patch_to_temp_clone(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.maintenance_review_bundle:
        print_maintenance_review_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approve_maintenance_bundle:
        print_human_approval_binding(project_id=args.workspace_project_id or args.stable_loop_project, bundle_hash=args.maintenance_bundle_hash, confirm=bool(args.approve_controlled_self_build), full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.real_maintenance_patch_apply:
        approved = bool(args.approve_controlled_self_build)
        print_real_maintenance_patch_apply(project_id=args.workspace_project_id or args.stable_loop_project, bundle_hash=args.maintenance_bundle_hash, confirm_phrase=args.maintenance_confirm_phrase, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.post_apply_health_monitor:
        print_post_apply_health_monitor(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_maintenance_cycle:
        print_controlled_maintenance_cycle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.assisted_self_improvement_release:
        print_assisted_self_improvement_release(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.improvement_candidate_scan:
        print_improvement_candidate_scan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.candidate_prioritizer:
        print_candidate_prioritizer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.candidate_to_proposal:
        print_candidate_to_proposal_bridge(project_id=args.workspace_project_id or args.stable_loop_project, candidate_id=args.maintenance_candidate_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.maintenance_backlog:
        print_maintenance_backlog_registry(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dashboard_maintenance_backlog:
        print_dashboard_maintenance_backlog(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.api_maintenance_backlog:
        print_api_maintenance_backlog(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.candidate_regression_detector:
        print_candidate_regression_detector(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_memory_privacy:
        print_release_memory_privacy(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.candidate_verification_recipes:
        print_candidate_verification_recipes(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.assisted_improvement_cycle:
        print_assisted_improvement_cycle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.semi_autonomous_maintenance_review:
        print_semi_autonomous_maintenance_review(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.hotfix_regression_lockdown:
        print_hotfix_regression_lockdown(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dashboard_route_coverage:
        print_dashboard_route_coverage_auditor(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.api_default_source_audit:
        print_api_default_source_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.nested_readiness_severity:
        print_nested_readiness_severity_engine(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.review_bundle_approval_contract:
        print_review_bundle_approval_contract(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.maintenance_report_diff:
        print_maintenance_report_diff_viewer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_gate_composition_test:
        print_release_gate_composition_test(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dashboard_api_parity_audit:
        print_dashboard_api_parity_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.operator_trust_report:
        print_operator_trust_report(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.trustworthy_maintenance_console:
        print_trustworthy_maintenance_console(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.trust_console_drill:
        print_trust_console_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.trust_console_snapshot:
        print_trust_console_snapshot(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.trust_console_diff:
        print_trust_console_diff(project_id=args.workspace_project_id or args.stable_loop_project, before_path=args.trust_snapshot_before, after_path=args.trust_snapshot_after, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.freeze_release_candidate:
        print_release_candidate_freezer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verify_frozen_release_zip:
        print_frozen_release_zip_verification(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_evidence_ledger:
        print_approval_evidence_ledger(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_command_reproducer:
        print_release_command_reproducer(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.console_readme_consistency:
        print_console_readme_consistency(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v27_safety_audit:
        print_pre_v27_safety_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_candidate_governance:
        print_release_candidate_governance(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_governance_drill:
        print_release_governance_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_evidence_bundle:
        print_release_evidence_bundle(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verify_release_evidence_bundle:
        print_release_evidence_bundle_verifier(project_id=args.workspace_project_id or args.stable_loop_project, bundle_path=args.release_evidence_bundle_path, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_governance_page:
        print_release_governance_page(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.governance_api_read_only:
        print_governance_api_read_only_surface(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_artifact_diff:
        print_release_artifact_diff(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_signing_preparation:
        print_release_signing_preparation(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.local_trust_policy:
        print_local_trust_policy(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_governance_ux_polish:
        print_release_governance_ux_polish(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v28_governance_audit:
        print_pre_v28_governance_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verifiable_release_evidence_system:
        print_verifiable_release_evidence_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return


    if args.evidence_replay_drill:
        print_evidence_replay_drill(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.persist_release_evidence:
        print_evidence_bundle_persistence(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.replay_release_evidence:
        print_replay_release_evidence(project_id=args.workspace_project_id or args.stable_loop_project, bundle_path=args.release_evidence_bundle_path, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.evidence_timeline:
        print_evidence_timeline(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.evidence_operator_summary:
        print_evidence_operator_summary(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dashboard_evidence_viewer:
        print_dashboard_evidence_viewer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.api_evidence_viewer:
        print_api_evidence_viewer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.evidence_retention_policy:
        print_evidence_retention_policy(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.evidence_regression_lockdown:
        print_evidence_regression_lockdown(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v29_evidence_audit:
        print_pre_v29_evidence_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.durable_release_evidence_archive:
        print_durable_release_evidence_archive(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signing_readiness_audit:
        print_signing_readiness_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.canonical_manifest_format:
        print_canonical_manifest_format(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.canonical_evidence_schema:
        print_canonical_evidence_schema(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_signing_status:
        print_release_signing_status(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signature_placeholder_contract:
        print_signature_placeholder_contract(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.key_policy_preparation:
        print_key_policy_preparation(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verify_release_signature:
        print_signature_verification_placeholder(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.dashboard_signing_status:
        print_dashboard_signing_status(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.api_signing_status:
        print_api_signing_status(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.pre_v30_signing_prep_audit:
        print_pre_v30_signing_prep_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signed_release_preparation_system:
        print_signed_release_preparation_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signing_api_hardening:
        print_signing_api_hardening(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.canonical_schema_validator:
        print_canonical_schema_validator(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.source_data_sanitizer:
        print_source_data_sanitizer(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signing_trust_model:
        print_signing_trust_model(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_signing_tamper_drill:
        print_release_signing_tamper_drill(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.public_key_policy_design:
        print_public_key_policy_design(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.detached_signature_contract:
        print_detached_signature_contract(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signature_fixture_verification:
        print_signature_fixture_verification(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.external_signer_workflow:
        print_external_signer_workflow(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.detached_signature_verification_system:
        print_detached_signature_verification_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signature_verification_hardening:
        print_signature_verification_hardening(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.public_trust_root_config:
        print_public_trust_root_config(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.external_signing_payload_export:
        print_external_signing_payload_export(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.signed_fixture_test_suite:
        print_signed_fixture_test_suite(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_publish_gate:
        print_release_publish_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_trust_dashboard_polish:
        print_release_trust_dashboard_polish(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.api_route_safety_audit:
        print_api_route_safety_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_reproducibility_check:
        print_release_reproducibility_check(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v32_release_candidate_gate:
        print_pre_v32_release_candidate_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.signed_release_governance:
        print_signed_release_governance(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.governance_report_cleanup:
        print_governance_report_cleanup(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_candidate_workspace:
        print_release_candidate_workspace(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.artifact_binding_audit:
        print_artifact_binding_audit_v2(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.surface_consistency_audit:
        print_surface_consistency_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.external_signing_handoff:
        print_external_signing_handoff(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.signature_intake_validation:
        print_signature_intake_validation(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.trusted_signer_registry:
        print_trusted_signer_registry(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.governance_scenario_suite:
        print_governance_scenario_suite(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v33_operations_gate:
        print_pre_v33_operations_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_operations_console:
        print_release_operations_console(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operations_console_cleanup:
        print_operations_console_cleanup(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_candidate_review:
        print_release_candidate_review(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.signed_artifact_intake:
        print_signed_artifact_intake(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.trust_root_lifecycle:
        print_trust_root_lifecycle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_decision_explainer:
        print_publish_decision_explainer(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_action_guardrails:
        print_operator_action_guardrails(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.unsigned_release_drill:
        print_unsigned_release_drill(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.signed_fixture_release_drill:
        print_signed_fixture_release_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v34_operator_workflow_gate:
        print_pre_v34_operator_workflow_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_operator_workflow:
        print_release_operator_workflow(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_candidate_record:
        print_release_candidate_record_v2(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.signed_artifact_intake_v2:
        print_signed_artifact_intake_v2(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.trust_root_management_policy:
        print_trust_root_management_policy(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.trust_root_mutation_guardrails:
        print_trust_root_mutation_guardrails(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.signed_release_publish_decision:
        print_signed_release_publish_decision(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_dashboard_action_states:
        print_operator_dashboard_action_states(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.release_workflow_audit_trail:
        print_release_workflow_audit_trail(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.trusted_fixture_workflow:
        print_trusted_fixture_workflow(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v35_trusted_candidate_gate:
        print_pre_v35_trusted_candidate_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.trusted_release_candidate_system:
        print_trusted_release_candidate_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.candidate_review_state:
        print_candidate_review_state(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_policy:
        print_publish_approval_policy(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_dry_run:
        print_publish_approval_dry_run(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_record_schema:
        print_publish_approval_record_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.dashboard_approval_state_preview:
        print_dashboard_approval_state_preview(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_route_safety_audit:
        print_approval_route_safety_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_fixture_drill:
        print_approval_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_explainer:
        print_publish_approval_explainer(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v36_approval_separation_gate:
        print_pre_v36_approval_separation_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_separation_system:
        print_publish_approval_separation_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.publish_approval_record_validator:
        print_publish_approval_record_validator(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_dry_run_v2:
        print_publish_approval_dry_run_v2(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_storage_quarantine:
        print_approval_storage_quarantine(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_api_preview:
        print_publish_approval_api_preview(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.dashboard_approval_workflow_preview:
        print_dashboard_approval_workflow_preview(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_confirmation_policy:
        print_approval_confirmation_policy(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_record_fixture_drill:
        print_approval_record_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_audit_trail:
        print_approval_audit_trail(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v37_approval_records_gate:
        print_pre_v37_approval_records_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_publish_approval_system:
        print_controlled_publish_approval_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.publish_approval_write_preflight:
        print_publish_approval_write_preflight(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_write_schema_lock:
        print_publish_approval_write_schema_lock(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_confirmation_validator:
        print_publish_approval_confirmation_validator(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, confirmation=args.release_confirm_phrase, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_only_approval_write_route_design:
        print_post_only_approval_write_route_design(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_write_dashboard_preview:
        print_approval_write_dashboard_preview(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, confirmation=args.release_confirm_phrase, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.write_publish_approval:
        print_write_publish_approval(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, confirmation=args.release_confirm_phrase, approver_label=args.approver_label, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, dry_run=(not args.approve_publish_approval_write or args.dry_run), full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_write_rollback_safety_audit:
        print_approval_write_rollback_safety_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_write_fixture_drill:
        print_approval_write_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v38_approval_write_gate:
        print_pre_v38_approval_write_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_publish_approval_write_system:
        print_controlled_publish_approval_write_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, signature_path=args.signature_path, public_key_path=args.public_key_path, trusted_fingerprint=args.trusted_fingerprint, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_record_reader:
        print_publish_approval_record_reader(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_artifact_revalidation:
        print_approval_artifact_revalidation(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_record_conflict_detector:
        print_approval_record_conflict_detector(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_status_viewer:
        print_approval_status_viewer(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_revocation_policy:
        print_approval_revocation_policy(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_revocation_dry_run:
        print_approval_revocation_dry_run(project_id=args.workspace_project_id or args.stable_loop_project, approval_record_id=args.approval_record_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_lifecycle_audit:
        print_approval_lifecycle_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_lifecycle_fixture_drill:
        print_approval_lifecycle_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v39_approval_lifecycle_gate:
        print_pre_v39_approval_lifecycle_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.publish_approval_lifecycle_system:
        print_publish_approval_lifecycle_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_revocation_record_schema:
        print_approval_revocation_record_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_revocation_confirmation_validator:
        print_approval_revocation_confirmation_validator(project_id=args.workspace_project_id or args.stable_loop_project, approval_record_id=args.approval_record_id, confirmation=args.release_confirm_phrase, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_revocation_write_preflight:
        print_approval_revocation_write_preflight(project_id=args.workspace_project_id or args.stable_loop_project, approval_record_id=args.approval_record_id, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.revocation_storage_quarantine:
        print_revocation_storage_quarantine(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_only_revocation_route_design:
        print_post_only_revocation_route_design(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.write_approval_revocation:
        approved = bool(args.approve_publish_approval_revocation)
        print_write_approval_revocation(project_id=args.workspace_project_id or args.stable_loop_project, approval_record_id=args.approval_record_id, confirmation=args.release_confirm_phrase, revocation_reason=args.revocation_reason, revoker_label=args.revoker_label, dry_run=not approved or args.dry_run, approve=approved, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.dashboard_revocation_preview:
        print_dashboard_revocation_preview(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.approval_revocation_fixture_drill:
        print_approval_revocation_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v40_revocation_gate:
        print_pre_v40_revocation_gate(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_publish_approval_revocation_system:
        print_controlled_publish_approval_revocation_system(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, zip_path=args.release_zip_path, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.autonomy_capability_inventory:
        print_autonomy_capability_inventory(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_task_proposal_schema:
        print_autonomous_task_proposal_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_dry_run_plan:
        print_autonomous_dry_run_plan(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomy_action_policy_engine:
        print_autonomy_action_policy_engine(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_patch_sandbox:
        print_autonomous_patch_sandbox(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_patch_risk_classifier:
        print_autonomous_patch_risk_classifier(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_test_selection:
        print_autonomous_test_selection(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomy_human_checkpoint:
        print_autonomy_human_checkpoint(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v41_autonomy_readiness_gate:
        print_pre_v41_autonomy_readiness_gate(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomy_readiness_boundary_system:
        print_autonomy_readiness_boundary_system(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_proposal_schema:
        print_patch_proposal_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_change_target_selector:
        print_autonomous_change_target_selector(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.generate_sandbox_patch:
        print_generate_sandbox_patch(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_patch_diff:
        print_sandbox_patch_diff(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_patch_validation:
        print_sandbox_patch_validation(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.sandbox_patch_test_run:
        print_sandbox_patch_test_run(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.patch_review_checkpoint:
        print_patch_review_checkpoint(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_dry_run:
        print_source_apply_dry_run(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v42_autonomous_patch_gate:
        print_pre_v42_autonomous_patch_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomous_patch_proposal_system:
        print_autonomous_patch_proposal_system(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.source_apply_eligibility:
        print_source_apply_eligibility(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_confirmation_policy:
        print_source_apply_confirmation_policy(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, confirmation=args.release_confirm_phrase or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_dry_run_v2:
        print_source_apply_dry_run_v2(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_backup_quarantine:
        print_source_apply_backup_quarantine(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.apply_reviewed_patch:
        approved = bool(args.approve_source_apply)
        print_apply_reviewed_patch(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, confirmation=args.release_confirm_phrase or None, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_source_apply_verification:
        print_post_source_apply_verification(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_rollback_preview:
        print_source_apply_rollback_preview(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_fixture_drill:
        print_source_apply_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v43_source_apply_gate:
        print_pre_v43_source_apply_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_source_apply_system:
        print_controlled_source_apply_system(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_apply_record_reader:
        print_source_apply_record_reader(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_rollback_eligibility:
        print_source_rollback_eligibility(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_rollback_confirmation_policy:
        print_source_rollback_confirmation_policy(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, confirmation=args.release_confirm_phrase or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_rollback_dry_run_v2:
        print_source_rollback_dry_run_v2(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.rollback_applied_patch:
        approved = bool(args.approve_source_rollback)
        print_rollback_applied_patch(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, confirmation=args.release_confirm_phrase or None, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_source_rollback_verification:
        print_post_source_rollback_verification(project_id=args.workspace_project_id or args.stable_loop_project, proposal_id=args.proposal_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_rollback_audit_trail:
        print_source_rollback_audit_trail(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.source_rollback_fixture_drill:
        print_source_rollback_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v44_source_rollback_gate:
        print_pre_v44_source_rollback_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.controlled_source_rollback_system:
        print_controlled_source_rollback_system(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.self_maintenance_cycle_schema:
        print_v45_self_maintenance_cycle_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.self_maintenance_plan:
        print_v45_self_maintenance_plan(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.self_maintenance_sandbox_cycle:
        print_v45_self_maintenance_sandbox_cycle(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_checkpoint_binder:
        print_v45_maintenance_checkpoint_binder(project_id=args.workspace_project_id or args.stable_loop_project, cycle_id=args.cycle_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.self_maintenance_apply_dry_run:
        print_v45_self_maintenance_apply_dry_run(project_id=args.workspace_project_id or args.stable_loop_project, cycle_id=args.cycle_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.self_maintenance_apply_handoff:
        print_v45_self_maintenance_apply_handoff(project_id=args.workspace_project_id or args.stable_loop_project, cycle_id=args.cycle_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.post_maintenance_verification_summary:
        print_v45_post_maintenance_verification_summary(project_id=args.workspace_project_id or args.stable_loop_project, cycle_id=args.cycle_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.self_maintenance_fixture_drill:
        print_v45_self_maintenance_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v45_self_maintenance_gate:
        print_v45_pre_v45_self_maintenance_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_record_schema:
        print_v46_maintenance_task_record_schema(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_priority_risk_scoring:
        print_v46_maintenance_task_priority_risk_scoring(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_queue_registry:
        print_v46_maintenance_task_queue_registry(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_selection_policy:
        print_v46_maintenance_task_selection_policy(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_cycle_orchestrator:
        print_v46_maintenance_task_cycle_orchestrator(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_checkpoint_binding:
        print_v46_maintenance_task_checkpoint_binding(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, task_id=args.maintenance_task_id or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_source_apply_lockout:
        print_v46_maintenance_task_source_apply_lockout(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_dashboard_api_views:
        print_v46_maintenance_task_dashboard_api_views(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_fixture_drill:
        print_v46_maintenance_task_fixture_drill(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v46_maintenance_queue_gate:
        print_v46_pre_v46_maintenance_queue_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.autonomy_queue_report_cache:
        print_v47_autonomy_queue_report_cache(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_task_drilldown:
        print_v47_maintenance_task_drilldown_view(project_id=args.workspace_project_id or args.stable_loop_project, task_id=args.maintenance_task_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.queue_stale_state_warnings:
        print_v47_maintenance_queue_stale_state_warnings(project_id=args.workspace_project_id or args.stable_loop_project, task_id=args.maintenance_task_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.maintenance_runtime_privacy_audit:
        print_v47_maintenance_runtime_privacy_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.operator_command_palette:
        print_v47_operator_command_palette_report(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.dashboard_api_queue_parity:
        print_v47_dashboard_api_queue_parity(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.queue_verification_receipt:
        print_v47_queue_verification_receipt(project_id=args.workspace_project_id or args.stable_loop_project, task_id=args.maintenance_task_id or None, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.dashboard_accessibility_compact_layout:
        print_v47_dashboard_accessibility_compact_layout(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return
    if args.pre_v47_attention_scheduler_gate:
        print_v47_pre_v47_attention_scheduler_gate(project_id=args.workspace_project_id or args.stable_loop_project, goal=args.autonomy_goal or None, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.stable_loop:
        print_stable_loop(
            project_id=args.stable_loop_project,
            max_steps=args.stable_loop_steps,
            live=args.stable_loop_live,
            use_ai=not args.no_ai_stable_loop,
            approve_work_execution=args.approve_stable_loop_actions,
            seed_if_empty=not args.no_stable_loop_seed,
            auto_create_patch_followups=not args.no_stable_loop_followups,
            auto_request_approvals=not args.no_stable_loop_approval_requests,
            auto_retry_recovery=args.stable_loop_auto_retry_recovery,
            bypass_closure_guardrails=args.stable_loop_bypass_closure_guardrails,
            full=args.stable_loop_full,
        )
        return

    if args.list_stable_loops:
        print_stable_loops()
        return

    if args.stable_loop_review_summary:
        print_stable_loop_review_summary(full=args.stable_loop_review_full)
        return

    if args.list_stable_loop_reviews is not None:
        filter_value = args.list_stable_loop_reviews or args.stable_loop_review_filter
        print_stable_loop_reviews(
            review_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_review_full,
        )
        return

    if args.archive_stable_loop:
        print_archive_stable_loop(
            args.archive_stable_loop,
            archived=True,
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.restore_stable_loop:
        print_archive_stable_loop(
            args.restore_stable_loop,
            archived=False,
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.cleanup_stable_loop_history:
        print_cleanup_stable_loop_history(
            review_filter=args.stable_loop_review_filter,
            limit=args.cleanup_stable_loop_limit,
            dry_run=not args.cleanup_stable_loop_confirm,
            include_live=not args.cleanup_stable_loop_exclude_live,
            full=args.stable_loop_review_full,
        )
        return

    if args.show_stable_loop_review:
        print_stable_loop_review(args.show_stable_loop_review, full=args.stable_loop_review_full)
        return

    if args.show_stable_loop_audit:
        print_stable_loop_audit(args.show_stable_loop_audit, refresh=False, full=args.stable_loop_audit_full)
        return

    if args.refresh_stable_loop_audit:
        print_stable_loop_audit(args.refresh_stable_loop_audit, refresh=True, full=args.stable_loop_audit_full)
        return

    if args.show_stable_loop_operator_notes:
        print_stable_loop_operator_notes(args.show_stable_loop_operator_notes, full=args.stable_loop_operator_full)
        return

    if args.add_stable_loop_operator_note:
        print_add_stable_loop_operator_note(
            args.add_stable_loop_operator_note,
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.complete_stable_loop_check:
        loop_id, check_id = args.complete_stable_loop_check
        print_update_stable_loop_check(
            loop_id,
            check_id,
            status="done",
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.skip_stable_loop_check:
        loop_id, check_id = args.skip_stable_loop_check
        print_update_stable_loop_check(
            loop_id,
            check_id,
            status="skipped",
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.set_stable_loop_final_decision:
        print_set_stable_loop_final_decision(
            args.set_stable_loop_final_decision,
            decision=args.stable_loop_final_decision,
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.stable_loop_decision_report is not None:
        filter_value = args.stable_loop_decision_report or args.stable_loop_decision_filter
        print_stable_loop_decision_report(
            decision_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            include_live=True,
            full=args.stable_loop_decision_full,
        )
        return

    if args.list_stable_loop_decisions is not None:
        filter_value = args.list_stable_loop_decisions or args.stable_loop_decision_filter
        print_stable_loop_decision_rows(
            decision_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            include_live=True,
        )
        return

    if args.cleanup_stable_loop_decisions:
        print_cleanup_stable_loop_decisions(
            decision_filter=args.stable_loop_decision_filter,
            limit=args.cleanup_stable_loop_limit,
            dry_run=not args.cleanup_stable_loop_confirm,
            include_live=not args.cleanup_stable_loop_exclude_live,
            full=args.stable_loop_decision_full,
        )
        return

    if args.cleanup_stable_loop_followup_completions:
        print_cleanup_stable_loop_followup_completions(
            completion_filter=args.stable_loop_followup_completion_filter,
            limit=args.cleanup_stable_loop_limit,
            dry_run=not args.cleanup_stable_loop_confirm,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_followup_completion_full,
        )
        return

    if args.mark_stable_loop_followup_closed:
        print_mark_stable_loop_followup_closed(
            args.mark_stable_loop_followup_closed,
            note=args.stable_loop_followup_note,
            archive=args.archive_resolved_stable_loop,
            full=args.stable_loop_followup_completion_full,
        )
        return

    if args.stable_loop_followup_completion_report is not None:
        filter_value = args.stable_loop_followup_completion_report or args.stable_loop_followup_completion_filter or "all"
        print_stable_loop_followup_completion_report(
            completion_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_followup_completion_full,
        )
        return

    if args.list_stable_loop_followup_completions is not None:
        filter_value = args.list_stable_loop_followup_completions or args.stable_loop_followup_completion_filter or "all"
        print_stable_loop_followup_completion_rows(
            completion_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            limit=args.cleanup_stable_loop_limit,
        )
        return

    if args.stable_loop_followup_lifecycle_summary is not None:
        filter_value = args.stable_loop_followup_lifecycle_summary or "all"
        print_stable_loop_followup_lifecycle_summary(
            decision_filter=filter_value,
            include_closed=True,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_followup_full,
        )
        return

    if args.show_task_stable_loop_followup:
        print_stable_loop_followup_task(args.show_task_stable_loop_followup, full=args.stable_loop_followup_full)
        return

    if args.resolve_stable_loop_followups:
        print_resolve_stable_loop_followups(
            args.resolve_stable_loop_followups,
            archive=args.archive_resolved_stable_loop,
            force=args.force_stable_loop_followup_resolution,
            note=args.stable_loop_followup_note,
            full=args.stable_loop_followup_full,
        )
        return

    if args.resolve_task_stable_loop_followup:
        print_resolve_task_stable_loop_followup(
            args.resolve_task_stable_loop_followup,
            archive=args.archive_resolved_stable_loop,
            force=args.force_stable_loop_followup_resolution,
            note=args.stable_loop_followup_note,
            full=args.stable_loop_followup_full,
        )
        return

    if args.stable_loop_followup_summary is not None:
        filter_value = args.stable_loop_followup_summary or args.stable_loop_decision_filter or "action_required"
        print_stable_loop_followup_summary(
            decision_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            include_live=not args.cleanup_stable_loop_exclude_live,
            full=args.stable_loop_followup_full,
        )
        return

    if args.create_stable_loop_followups:
        print_create_stable_loop_followups(
            args.create_stable_loop_followups,
            dry_run=args.dry_run,
            force=args.stable_loop_followup_force,
            full=args.stable_loop_followup_full,
        )
        return

    if args.create_stable_loop_decision_followups is not None:
        filter_value = args.create_stable_loop_decision_followups or args.stable_loop_decision_filter or "action_required"
        print_create_stable_loop_followups_for_decisions(
            decision_filter=filter_value,
            dry_run=args.dry_run,
            include_archived=args.include_archived_stable_loops,
            include_live=not args.cleanup_stable_loop_exclude_live,
            limit=args.cleanup_stable_loop_limit,
            force=args.stable_loop_followup_force,
            full=args.stable_loop_followup_full,
        )
        return

    if args.mark_stable_loop_reviewed:
        print_update_stable_loop_review(
            args.mark_stable_loop_reviewed,
            status="reviewed",
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.approve_stable_loop_live:
        print_update_stable_loop_review(
            args.approve_stable_loop_live,
            status="approved_for_live",
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.reject_stable_loop:
        print_update_stable_loop_review(
            args.reject_stable_loop,
            status="rejected",
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.run_approved_stable_loop_live:
        print_run_approved_stable_loop_live(
            args.run_approved_stable_loop_live,
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full or args.stable_loop_full,
        )
        return

    if args.status:
        print_status()
        return

    if args.latest_ids:
        print_latest_ids()
        return

    if args.settings:
        print_settings()
        return

    if args.get_setting:
        print_get_setting(args.get_setting)
        return

    if args.set_setting:
        key, value = args.set_setting
        print_set_setting(key, value)
        return

    if args.reset_settings:
        print_reset_settings()
        return

    if args.settings_health:
        print_settings_health()
        return

    if args.watch_once:
        print_watch_once(use_ai=(not args.no_ai_watch and ai_reviews_enabled()), full=args.watch_full)
        return

    if args.watch_loop:
        print_watch_loop(
            cycles=args.watch_cycles,
            interval_seconds=args.watch_interval,
            use_ai=(not args.no_ai_watch and ai_reviews_enabled()),
            full=args.watch_full,
        )
        return

    if args.list_watch_reports:
        print_watch_reports()
        return

    if args.show_watch_report is not None:
        print_saved_watch_report(args.show_watch_report, full=args.watch_full, include_ai=not args.hide_watch_ai)
        return

    if args.notifications:
        print_notifications(status="unread", include_dismissed=False)
        return

    if args.list_notifications:
        print_notifications(status=args.notification_filter_status, include_dismissed=args.include_dismissed_notifications)
        return

    if args.show_notification is not None:
        print_notification(args.show_notification, full=args.notification_full)
        return

    if args.mark_notification_read is not None:
        print_mark_notification_read(args.mark_notification_read, note=args.notification_note)
        return

    if args.dismiss_notification is not None:
        print_dismiss_notification(args.dismiss_notification, note=args.notification_note)
        return

    if args.clear_dismissed_notifications:
        print_clear_dismissed_notifications()
        return

    if args.chat_action:
        print_chat_action(args.chat_action)
        return

    if args.execute_chat_action is not None:
        print_execute_chat_action(args.execute_chat_action, dry_run=args.dry_run)
        return

    if args.list_chat_actions:
        print_chat_actions(status=args.chat_action_filter_status, include_closed=True)
        return

    if args.show_chat_action is not None:
        print_saved_chat_action(args.show_chat_action, full=args.chat_action_full)
        return

    if args.dashboard:
        run_dashboard(host=args.dashboard_host, port=args.dashboard_port)
        return

    if args.api_server:
        run_api_server(host=args.api_host, port=args.api_port)
        return

    if args.desktop_status:
        print_desktop_status()
        return

    if args.desktop_tray_status:
        print_desktop_tray_status()
        return

    if args.setup_check:
        print_setup_check(full=args.setup_full)
        return

    if args.list_setup_reports:
        print_setup_reports()
        return

    if args.show_setup_report is not None:
        print_saved_setup_report(args.show_setup_report, full=args.setup_full)
        return

    if args.onboarding:
        print_onboarding_run(full=args.onboarding_full, refresh_setup=not args.onboarding_use_latest_setup)
        return

    if args.list_onboarding_runs:
        print_onboarding_runs()
        return

    if args.show_onboarding_run is not None:
        print_saved_onboarding_run(args.show_onboarding_run, full=args.onboarding_full)
        return

    if args.desktop:
        run_desktop_shell()
        return

    if args.diagnostics:
        print_diagnostics(include_full=args.diagnostics_full)
        return

    if args.list_diagnostic_reports:
        print_diagnostic_reports()
        return

    if args.show_diagnostic_report:
        print_saved_diagnostic_report(args.show_diagnostic_report, include_full=args.diagnostics_full)
        return

    if args.maintenance_scan:
        print_maintenance_scan(use_ai=(not args.no_ai_maintenance and ai_reviews_enabled()))
        return

    if args.list_maintenance_scans:
        print_maintenance_scans()
        return

    if args.show_maintenance_scan:
        print_saved_maintenance_scan(
            args.show_maintenance_scan,
            include_ai=not args.hide_maintenance_ai,
            full=args.show_maintenance_full,
        )
        return

    if args.memory_status:
        print_memory_status()
        return

    if args.compact_memory:
        print_compact_memory(
            keep_recent=args.keep_recent_memories,
            min_memories=args.min_memories_to_compact,
            use_ai=(not args.no_ai_memory_compact and ai_reviews_enabled()),
            dry_run=args.dry_run,
        )
        return

    if args.list_memory_summaries:
        print_memory_summaries()
        return

    if args.show_memory_summary:
        print_memory_summary(args.show_memory_summary, include_full=args.show_memory_summary_full)
        return

    if args.plan_session:
        print_session_plan(use_ai=(not args.no_ai_session and ai_reviews_enabled()))
        return

    if args.list_session_plans:
        print_session_plans()
        return

    if args.show_session_plan:
        print_saved_session_plan(
            args.show_session_plan,
            include_ai=not args.hide_session_ai,
            full=args.show_session_plan_full,
        )
        return

    if args.task_status:
        print_task_status()
        return

    if args.list_tasks:
        print_task_list(
            status=args.task_filter_status,
            project=args.task_filter_project or args.task_project,
            include_cancelled=not args.hide_cancelled_tasks,
        )
        return

    if args.show_task:
        print_task_detail(args.show_task, full=args.show_task_full)
        return

    if args.add_task:
        print_add_task(
            title=args.add_task,
            description=args.task_description,
            priority=args.task_priority,
            status=args.task_initial_status,
            project=args.task_project,
            command=args.task_command,
            next_action=args.task_next_action,
            linked_goal=args.task_goal,
            risk=args.task_risk,
        )
        return

    if args.set_task_status:
        task_id, status = args.set_task_status
        print_set_task_status(task_id, status, note=args.task_note)
        return

    if args.add_task_note:
        task_id, note = args.add_task_note
        print_add_task_note(task_id, note)
        return

    if args.add_task_action:
        task_id, action = args.add_task_action
        print_add_task_action(task_id, action)
        return

    if args.start_task:
        print_start_task(args.start_task, note=args.task_note)
        return

    if args.complete_task:
        print_complete_task(args.complete_task, note=args.task_note)
        return

    if args.block_task:
        task_id, reason = args.block_task
        print_block_task(task_id, reason)
        return

    if args.next_task:
        print_next_task()
        return

    if args.queue_from_session is not None:
        print_queue_from_session(args.queue_from_session, limit=args.queue_task_limit)
        return

    if args.task_command_options is not None:
        print_task_command_options(args.task_command_options)
        return

    if args.execute_task is not None:
        print_execute_task(
            args.execute_task,
            command_index=args.task_command_index,
            dry_run=args.dry_run,
            complete_on_success=args.complete_on_success,
        )
        return

    if args.task_execution_history is not None:
        print_task_execution_history(args.task_execution_history)
        return

    if args.evaluate_task is not None:
        print_task_evaluation(args.evaluate_task, use_ai=(not args.no_ai_task_evaluation and ai_reviews_enabled()))
        return

    if args.list_task_evaluations:
        print_task_evaluations()
        return

    if args.show_task_evaluation is not None:
        print_saved_task_evaluation(args.show_task_evaluation, include_ai=not args.hide_task_evaluation_ai)
        return

    if args.apply_task_evaluation is not None:
        print_apply_task_evaluation(args.apply_task_evaluation, create_follow_up=args.task_evaluation_follow_up)
        return

    if args.guided_work_session is not None:
        print_guided_work_session(args.guided_work_session, full=args.guided_session_full)
        return

    if args.advance_work_session is not None:
        print_advance_guided_work_session(
            args.advance_work_session,
            command_index=args.task_command_index,
            dry_run=args.dry_run,
            use_ai=(not args.no_ai_task_evaluation and ai_reviews_enabled()),
            apply_guided_evaluation=args.apply_guided_evaluation,
            full=args.guided_session_full,
        )
        return

    if args.list_guided_sessions:
        print_guided_sessions()
        return

    if args.show_guided_session is not None:
        print_saved_guided_session(args.show_guided_session, full=args.guided_session_full)
        return

    if args.dev_cycle is not None:
        print_dev_cycle(args.dev_cycle, full=args.dev_cycle_full)
        return

    if args.advance_dev_cycle is not None:
        print_advance_dev_cycle(
            args.advance_dev_cycle,
            dry_run=args.dry_run,
            approve_apply=args.approve_dev_cycle_apply,
            apply_evaluation=args.apply_dev_cycle_evaluation,
            use_ai=(not args.no_ai_dev_cycle and ai_reviews_enabled()),
            full=args.dev_cycle_full,
        )
        return

    if args.list_dev_cycles:
        print_dev_cycles()
        return

    if args.show_dev_cycle is not None:
        print_saved_dev_cycle(args.show_dev_cycle, full=args.dev_cycle_full)
        return

    if args.dev_loop is not None:
        print_dev_loop(
            args.dev_loop,
            max_steps=args.dev_loop_steps,
            dry_run=args.dry_run,
            approve_apply=args.approve_dev_loop_actions,
            apply_evaluation=args.apply_dev_loop_evaluation,
            use_ai=(not args.no_ai_dev_loop and ai_reviews_enabled()),
            full=args.dev_loop_full,
        )
        return

    if args.list_dev_loops:
        print_dev_loops()
        return

    if args.show_dev_loop is not None:
        print_saved_dev_loop(args.show_dev_loop, full=args.dev_loop_full)
        return

    if args.self_development_cycle:
        print_self_development_cycle(
            prompt=args.self_development_prompt,
            create_task=args.self_development_create_task,
            full=args.self_development_full,
        )
        return

    if args.list_self_development_cycles:
        print_self_development_cycles()
        return

    if args.show_self_development_cycle is not None:
        print_saved_self_development_cycle(args.show_self_development_cycle, full=args.self_development_full)
        return

    if args.self_development_trial_review:
        print_self_development_trial_review(full=args.self_development_full)
        return

    if args.self_development_smoke_triage:
        print_broad_smoke_triage(full=args.self_development_full)
        return

    if args.self_development_dashboard_hardening:
        print_self_development_dashboard_hardening_review(full=args.self_development_full)
        return

    if args.self_development_implementation_proposal is not None:
        print_self_development_implementation_proposal(
            cycle_id=args.self_development_implementation_proposal,
            full=args.self_development_full,
            save=args.self_development_save_proposal,
        )
        return

    if args.self_development_patch_draft is not None:
        print_operator_approved_self_development_patch_draft(
            approval_phrase=args.self_development_patch_draft,
            cycle_id=args.self_development_patch_draft_cycle,
            full=args.self_development_full,
            save=args.self_development_save_patch_draft,
        )
        return

    if args.self_development_patch_application is not None:
        print_operator_approved_self_development_patch_application_trial(
            approval_phrase=args.self_development_patch_application,
            draft_id=args.self_development_patch_application_draft,
            full=args.self_development_full,
            save=args.self_development_save_patch_application,
        )
        return

    if args.self_development_application_receipt_review:
        print_self_development_application_receipt_review(full=args.self_development_full)
        return

    if args.current_smoke_debt_ledger:
        print_current_smoke_debt_ledger(full=args.self_development_full, save=args.save_current_smoke_debt_ledger)
        return

    if args.low_risk_smoke_debt_cleanup_candidates:
        print_low_risk_smoke_debt_cleanup_candidates(full=args.self_development_full)
        return

    if args.self_development_smoke_debt_dashboard:
        print_self_development_smoke_debt_dashboard(full=args.self_development_full)
        return

    if args.self_development_api_surface_truth_review:
        print_self_development_api_surface_truth_review(full=args.self_development_full)
        return

    if args.self_development_cycle_duplicate_cleanup:
        print_self_development_cycle_duplicate_cleanup_review(full=args.self_development_full)
        return

    if args.legacy_self_maintenance_smoke_blocker_review:
        print_legacy_self_maintenance_smoke_blocker_review(full=args.self_development_full)
        return

    if args.current_smoke_debt_ledger_reconciliation:
        print_current_smoke_debt_ledger_reconciliation_review(full=args.self_development_full)
        return

    if args.current_audit_wording_cleanup:
        print_current_audit_wording_cleanup_review(full=args.self_development_full)
        return

    if args.manifest_generation_prep_review:
        print_manifest_generation_prep_review(full=args.self_development_full)
        return

    if args.manifest_gated_surface_validation:
        print_manifest_gated_surface_validation_review(full=args.self_development_full)
        return

    if args.manifest_driven_surface_registry_pilot:
        print_manifest_driven_surface_registry_pilot_review(full=args.self_development_full)
        return

    if args.manifest_surface_generation_readiness:
        print_manifest_surface_generation_readiness_review(full=args.self_development_full)
        return

    if args.manifest_registry_expanded_review_surfaces:
        print_manifest_registry_expanded_review_surfaces_review(full=args.self_development_full)
        return

    if args.manifest_registry_generation_readiness_scoring:
        print_manifest_registry_generation_readiness_scoring_review(full=args.self_development_full)
        return

    if args.manifest_registry_drift_detection:
        print_manifest_registry_drift_detection_review(full=args.self_development_full)
        return

    if args.manifest_guided_validation_probe_dry_run:
        print_manifest_guided_validation_probe_dry_run_review(full=args.self_development_full)
        return

    if args.manifest_guided_generated_validation_probe:
        print_manifest_guided_generated_validation_probe_review(full=args.self_development_full)
        return

    if args.manifest_smoke_segment_parity_drift:
        print_manifest_smoke_segment_parity_drift_review(full=args.self_development_full)
        return

    if args.manifest_smoke_segment_parity_repair_packet:
        print_manifest_smoke_segment_parity_repair_packet_review(full=args.self_development_full)
        return

    if args.manifest_smoke_segment_repair_application:
        print_manifest_smoke_segment_repair_application_review(full=args.self_development_full)
        return

    if args.manifest_segment_parity_enforcement_gate:
        print_manifest_segment_parity_enforcement_gate_review(full=args.self_development_full)
        return

    if args.manifest_guided_validation_probe_expansion_readiness:
        print_manifest_guided_validation_probe_expansion_readiness_review(full=args.self_development_full)
        return

    if args.manifest_guided_multi_surface_validation_probe_dry_run:
        print_manifest_guided_multi_surface_validation_probe_dry_run_review(full=args.self_development_full)
        return

    if args.manifest_guided_multi_surface_generated_validation_probe_packet:
        print_manifest_guided_multi_surface_generated_validation_probe_packet_review(full=args.self_development_full)
        return

    if args.manifest_guided_multi_surface_probe_packet_consistency_gate:
        print_manifest_guided_multi_surface_probe_packet_consistency_gate_review(full=args.self_development_full)
        return

    if args.manifest_guided_sandbox_probe_file_generation_readiness:
        print_manifest_guided_sandbox_probe_file_generation_readiness_review(full=args.self_development_full)
        return

    if args.manifest_guided_sandbox_probe_file_generation_dry_run:
        print_manifest_guided_sandbox_probe_file_generation_dry_run(full=args.self_development_full)
        return

    if args.operator_approved_sandbox_probe_file_generation_trial:
        print_operator_approved_sandbox_probe_file_generation_trial(full=args.self_development_full)
        return

    if args.sandbox_probe_file_verification_and_cleanup_review:
        print_sandbox_probe_file_verification_and_cleanup_review(full=args.self_development_full)
        return

    if args.sandbox_probe_execution_harness_readiness_review:
        print_sandbox_probe_execution_harness_readiness_review(full=args.self_development_full)
        return

    if args.operator_approved_sandbox_probe_execution_trial:
        print_operator_approved_sandbox_probe_execution_trial(full=args.self_development_full)
        return

    if args.sandbox_probe_execution_result_review_and_promotion_readiness:
        print_sandbox_probe_execution_result_review_and_promotion_readiness(full=args.self_development_full)
        return

    if args.live_probe_promotion_plan_review:
        print_live_probe_promotion_plan_review(full=args.self_development_full)
        return

    if args.operator_approved_live_probe_registration_trial:
        print_operator_approved_live_probe_registration_trial(full=args.self_development_full)
        return

    if args.live_registered_probe_verification_and_structural_hardening_review:
        print_live_registered_probe_verification_and_structural_hardening_review(full=args.self_development_full)
        return

    if args.v905_baseline_verification_and_manifest_version_semantics_prep:
        print_v905_baseline_verification_and_manifest_version_semantics_prep(full=args.self_development_full)
        return

    if args.manifest_version_semantics_split:
        print_manifest_version_semantics_split_review(full=args.self_development_full)
        return

    if args.manifest_validation_normalization:
        print_manifest_validation_normalization_review(full=args.self_development_full)
        return

    if args.source_package_privacy_deep_scan:
        print_source_package_privacy_deep_scan_review(full=args.self_development_full)
        return

    if args.metadata_and_current_marker_gate_reconciliation:
        print_metadata_and_current_marker_gate_reconciliation_review(full=args.self_development_full)
        return

    if args.release_gate_stale_assertion_truth_repair:
        print_release_gate_stale_assertion_truth_repair_review(full=args.self_development_full)
        return

    if args.install_release_segment_blocker_classification:
        print_install_release_segment_blocker_classification_review(full=args.self_development_full)
    if args.release_archive_and_recovery_gate_boundedness_repair:
        print_release_archive_and_recovery_gate_boundedness_repair_review(full=args.self_development_full)
    if args.install_release_segment_evidence_summary_gate:
        print_install_release_segment_evidence_summary_gate_review(full=args.self_development_full)
    if args.manifest_driven_surface_generation_prep:
        print_manifest_driven_surface_generation_prep_review(full=args.self_development_full)
        return

    if args.manifest_review_packet_schema:
        print_manifest_review_packet_schema_review(full=args.self_development_full)
        return

    if args.dashboard_surface_preview_generator:
        print_dashboard_surface_preview_generator_review(full=args.self_development_full)
        return

    if args.cli_api_surface_preview_generator:
        print_cli_api_surface_preview_generator_review(full=args.self_development_full)
        return

    if args.smoke_surface_preview_generator:
        print_smoke_surface_preview_generator_review(full=args.self_development_full)
        return

    if args.generated_preview_parity_report:
        print_generated_preview_parity_report_review(full=args.self_development_full)
        return

    if args.low_risk_surface_selection_gate:
        print_low_risk_surface_selection_gate_review(full=args.self_development_full)
        return

    if args.generated_dashboard_preview_exact_match_gate:
        print_generated_dashboard_preview_exact_match_gate_review(full=args.self_development_full)
        return

    if args.generated_cli_api_preview_exact_match_gate:
        print_generated_cli_api_preview_exact_match_gate_review(full=args.self_development_full)
        return

    if args.generated_smoke_preview_exact_match_gate:
        print_generated_smoke_preview_exact_match_gate_review(full=args.self_development_full)
        return

    if args.single_surface_generated_parity_closure:
        print_single_surface_generated_parity_closure_review(full=args.self_development_full)
        return

    if args.multi_surface_selection_gate:
        print_multi_surface_selection_gate_review(full=args.self_development_full)
        return

    if args.multi_surface_dashboard_preview_parity:
        print_multi_surface_dashboard_preview_parity_review(full=args.self_development_full)
        return

    if args.multi_surface_cli_api_preview_parity:
        print_multi_surface_cli_api_preview_parity_review(full=args.self_development_full)
        return

    if args.multi_surface_smoke_preview_parity:
        print_multi_surface_smoke_preview_parity_review(full=args.self_development_full)
        return

    if args.multi_surface_generated_parity_batch_closure:
        print_multi_surface_generated_parity_batch_closure_review(full=args.self_development_full)
        return

    if args.generated_scaffold_sandbox_output_schema:
        print_generated_scaffold_sandbox_output_schema_review(full=args.self_development_full)
        return

    if args.generated_scaffold_sandbox_artifact_preview:
        print_generated_scaffold_sandbox_artifact_preview_review(full=args.self_development_full)
        return

    if args.generated_scaffold_hash_ledger:
        print_generated_scaffold_hash_ledger_review(full=args.self_development_full)
        return

    if args.generated_scaffold_sandbox_parity_comparison:
        print_generated_scaffold_sandbox_parity_comparison_review(full=args.self_development_full)
        return

    if args.generated_scaffold_sandbox_output_closure:
        print_generated_scaffold_sandbox_output_closure_review(full=args.self_development_full)
        return

    if args.generated_scaffold_wrapper_mapping_schema:
        print_generated_scaffold_wrapper_mapping_schema_review(full=args.self_development_full)
        return

    if args.dashboard_compatibility_wrapper_preview:
        print_dashboard_compatibility_wrapper_preview_review(full=args.self_development_full)
        return

    if args.cli_api_compatibility_wrapper_preview:
        print_cli_api_compatibility_wrapper_preview_review(full=args.self_development_full)
        return

    if args.smoke_compatibility_wrapper_preview:
        print_smoke_compatibility_wrapper_preview_review(full=args.self_development_full)
        return

    if args.generated_scaffold_wrapper_prep_closure:
        print_generated_scaffold_wrapper_prep_closure_review(full=args.self_development_full)
        return

    if args.giant_file_extraction_inventory:
        print_giant_file_extraction_inventory_review(full=args.self_development_full)
        return

    if args.self_development_cycle_extraction_map:
        print_self_development_cycle_extraction_map_review(full=args.self_development_full)
        return

    if args.self_maintenance_builder_text_renderer_extraction_map:
        print_self_maintenance_builder_text_renderer_extraction_map_review(full=args.self_development_full)
        return

    if args.dashboard_route_renderer_extraction_map:
        print_dashboard_route_renderer_extraction_map_review(full=args.self_development_full)
        return

    if args.cli_api_dispatch_extraction_map:
        print_cli_api_dispatch_extraction_map_review(full=args.self_development_full)
        return

    if args.smoke_registry_extraction_map:
        print_smoke_registry_extraction_map_review(full=args.self_development_full)
        return

    if args.compatibility_wrapper_risk_ledger:
        print_compatibility_wrapper_risk_ledger_review(full=args.self_development_full)
        return

    if args.extraction_order_proposal:
        print_extraction_order_proposal_review(full=args.self_development_full)
        return

    if args.extraction_rollback_evidence_plan:
        print_extraction_rollback_evidence_plan_review(full=args.self_development_full)
        return

    if args.giant_file_compatibility_extraction_prep_closure:
        print_giant_file_compatibility_extraction_prep_closure_review(full=args.self_development_full)
        return
    if args.extraction_candidate_lock_gate:
        print_extraction_candidate_lock_gate_review(full=args.self_development_full)
        return
    if args.pre_extraction_function_inventory:
        print_pre_extraction_function_inventory_review(full=args.self_development_full)
        return
    if args.generated_preview_review_module_extraction:
        print_generated_preview_review_module_extraction_review(full=args.self_development_full)
        return
    if args.compatibility_import_wrapper_gate:
        print_compatibility_import_wrapper_gate_review(full=args.self_development_full)
        return
    if args.dashboard_cli_api_parity_after_extraction:
        print_dashboard_cli_api_parity_after_extraction_review(full=args.self_development_full)
        return
    if args.smoke_registry_parity_after_extraction:
        print_smoke_registry_parity_after_extraction_review(full=args.self_development_full)
        return
    if args.stale_version_and_metadata_post_extraction_gate:
        print_stale_version_and_metadata_post_extraction_gate_review(full=args.self_development_full)
        return
    if args.rollback_path_verification:
        print_rollback_path_verification_review(full=args.self_development_full)
        return
    if args.extraction_release_evidence_packet:
        print_extraction_release_evidence_packet_review(full=args.self_development_full)
        return
    if args.first_compatibility_extraction_closure:
        print_first_compatibility_extraction_closure_review(full=args.self_development_full)
        return

    if args.second_extraction_candidate_selection_gate:
        print_second_extraction_candidate_selection_gate_review(full=args.self_development_full)
        return
    if args.second_pre_extraction_function_inventory:
        print_second_pre_extraction_function_inventory_review(full=args.self_development_full)
        return
    if args.generated_scaffold_review_packet_extraction:
        print_generated_scaffold_review_packet_extraction_review(full=args.self_development_full)
        return
    if args.second_compatibility_wrapper_gate:
        print_second_compatibility_wrapper_gate_review(full=args.self_development_full)
        return
    if args.second_extraction_surface_parity_gate:
        print_second_extraction_surface_parity_gate_review(full=args.self_development_full)
        return
    if args.smoke_registry_data_model_prep:
        print_smoke_registry_data_model_prep_review(full=args.self_development_full)
        return
    if args.smoke_registry_static_inventory:
        print_smoke_registry_static_inventory_review(full=args.self_development_full)
        return
    if args.smoke_registry_migration_risk_ledger:
        print_smoke_registry_migration_risk_ledger_review(full=args.self_development_full)
        return
    if args.smoke_registry_rollback_plan:
        print_smoke_registry_rollback_plan_review(full=args.self_development_full)
        return
    if args.second_extraction_and_smoke_registry_prep_closure:
        print_second_extraction_and_smoke_registry_prep_closure_review(full=args.self_development_full)
        return
    if args.smoke_registry_pilot_selection_gate:
        print_smoke_registry_pilot_selection_gate_review(full=args.self_development_full)
        return
    if args.smoke_registry_pilot_schema:
        print_smoke_registry_pilot_schema_review(full=args.self_development_full)
        return
    if args.smoke_registry_pilot_data_table:
        print_smoke_registry_pilot_data_table_review(full=args.self_development_full)
        return
    if args.smoke_registry_pilot_resolver:
        print_smoke_registry_pilot_resolver_review(full=args.self_development_full)
        return
    if args.manual_vs_pilot_smoke_parity_gate:
        print_manual_vs_pilot_smoke_parity_gate_review(full=args.self_development_full)
        return
    if args.pilot_json_shape_compatibility_gate:
        print_pilot_json_shape_compatibility_gate_review(full=args.self_development_full)
        return
    if args.pilot_rollback_evidence_gate:
        print_pilot_rollback_evidence_gate_review(full=args.self_development_full)
        return
    if args.smoke_registry_pilot_risk_review:
        print_smoke_registry_pilot_risk_review(full=args.self_development_full)
        return
    if args.pilot_expansion_readiness_review:
        print_pilot_expansion_readiness_review(full=args.self_development_full)
        return
    if args.smoke_registry_data_driven_pilot_closure:
        print_smoke_registry_data_driven_pilot_closure_review(full=args.self_development_full)
        return
    if args.smoke_registry_execution_trial_readiness_gate:
        print_smoke_registry_execution_trial_readiness_gate_review(full=args.self_development_full)
        return
    if args.data_driven_smoke_callable_execution_harness:
        print_data_driven_smoke_callable_execution_harness_review(full=args.self_development_full)
        return
    if args.pilot_smoke_execution_result_packet:
        print_pilot_smoke_execution_result_packet_review(full=args.self_development_full)
        return
    if args.manual_vs_data_driven_execution_parity_gate:
        print_manual_vs_data_driven_execution_parity_gate_review(full=args.self_development_full)
        return
    if args.data_driven_smoke_json_output_preview:
        print_data_driven_smoke_json_output_preview_review(full=args.self_development_full)
        return
    if args.data_driven_smoke_timeout_failure_semantics:
        print_data_driven_smoke_timeout_failure_semantics_review(full=args.self_development_full)
        return
    if args.data_driven_smoke_manual_fallback_proof:
        print_data_driven_smoke_manual_fallback_proof_review(full=args.self_development_full)
        return
    if args.data_driven_smoke_execution_risk_review:
        print_data_driven_smoke_execution_risk_review(full=args.self_development_full)
        return
    if args.data_driven_smoke_expansion_readiness:
        print_data_driven_smoke_expansion_readiness_review(full=args.self_development_full)
        return
    if args.smoke_registry_data_driven_execution_trial_closure:
        print_smoke_registry_data_driven_execution_trial_closure_review(full=args.self_development_full)
    if args.fallback_migration_readiness_gate:
        print_fallback_migration_readiness_gate_review(full=args.self_development_full)
    if args.data_driven_first_pilot_dispatch_preview:
        print_data_driven_first_pilot_dispatch_preview_review(full=args.self_development_full)
    if args.pilot_fallback_dispatch_trial:
        print_pilot_fallback_dispatch_trial_review(full=args.self_development_full)
    if args.pilot_fallback_result_ledger:
        print_pilot_fallback_result_ledger_review(full=args.self_development_full)
    if args.json_output_stability_gate:
        print_json_output_stability_gate_review(full=args.self_development_full)
    if args.fast_install_release_isolation_gate:
        print_fast_install_release_isolation_gate_review(full=args.self_development_full)
    if args.manual_fallback_removal_resistance_gate:
        print_manual_fallback_removal_resistance_gate_review(full=args.self_development_full)
    if args.pilot_migration_risk_review:
        print_pilot_migration_risk_review(full=args.self_development_full)
    if args.v1000_milestone_readiness_review:
        print_v1000_milestone_readiness_review(full=args.self_development_full)
    if args.smoke_registry_fallback_migration_pilot_closure:
        print_smoke_registry_fallback_migration_pilot_closure_review(full=args.self_development_full)
        return
    if args.install_release_blocker_ledger_refresh:
        print_install_release_blocker_ledger_refresh_review(full=args.self_development_full)
        return
    if args.install_release_timeout_harness_repair:
        print_install_release_timeout_harness_repair_review(full=args.self_development_full)
        return
    if args.install_release_timeout_row_bounded_retest:
        print_install_release_timeout_row_bounded_retest_review(full=args.self_development_full)
        return
    if args.install_release_fixture_decomposition_plan:
        print_install_release_fixture_decomposition_plan_review(full=args.self_development_full)
        return
    if args.install_release_fixture_smoke_split_pilot:
        print_install_release_fixture_smoke_split_pilot_review(full=args.self_development_full)
        return
    if args.release_archive_fixture_split_expansion:
        print_release_archive_fixture_split_expansion_review(full=args.self_development_full)
        return
    if args.supervised_blocker_semantics_repair:
        print_supervised_blocker_semantics_repair_review(full=args.self_development_full)
        return
    if args.install_release_segment_cleanliness_gate:
        print_install_release_segment_cleanliness_gate_review(full=args.self_development_full)
        return
    if args.post_v1000_defect_closure_audit_and_phase_zero_boundary:
        print_post_v1000_defect_closure_phase_zero_boundary_review(full=args.self_development_full)
        return
    if args.install_release_timeout_parent_row_replacement_pilot:
        print_install_release_timeout_parent_replacement_pilot_review(full=args.self_development_full)
        return
    if args.install_release_parent_replacement_expansion:
        print_install_release_parent_replacement_expansion_review(full=args.self_development_full)
    if args.remaining_timeout_parent_fixture_selection:
        print_remaining_timeout_parent_fixture_selection_review(full=args.self_development_full)
        return
    if args.recovery_closure_fixture_split_smoke:
        print_recovery_closure_fixture_split_smoke_review(full=args.self_development_full)
        return
    if args.recovery_closure_parent_replacement_overlay:
        print_recovery_closure_parent_replacement_overlay_review(full=args.self_development_full)
        return
    if args.remaining_timeout_parent_fixture_split_expansion:
        print_remaining_timeout_parent_fixture_split_expansion_review(full=args.self_development_full)
        return
    if args.decision_archive_ledger_parent_replacement_overlay:
        print_decision_archive_ledger_parent_replacement_overlay_review(full=args.self_development_full)
        return
    if args.candidate_handoff_fixture_split_smoke:
        print_candidate_handoff_fixture_split_smoke_review(full=args.self_development_full)
        return
    if args.candidate_handoff_parent_replacement_overlay:
        print_candidate_handoff_parent_replacement_overlay_review(full=args.self_development_full)
        return
    if args.final_timeout_parent_overlay_closure:
        print_final_timeout_parent_overlay_closure_review(full=args.self_development_full)
        return

    if args.approval_inbox:
        print_approval_inbox(status="pending", include_closed=False)
        return

    if args.list_approvals:
        print_approval_inbox(status=args.approval_filter_status, include_closed=True)
        return

    if args.show_approval is not None:
        print_approval(args.show_approval, full=args.approval_full)
        return

    if args.approve is not None:
        print_approve(args.approve, dry_run=args.dry_run)
        return

    if args.reject is not None:
        print_reject(args.reject, note=args.approval_note)
        return

    if args.goal_status:
        print_goal_status()
        return

    if args.list_goals:
        print_goal_list(
            status=args.goal_filter_status,
            project=args.goal_filter_project or args.goal_project,
            include_cancelled=not args.hide_cancelled_goals,
        )
        return

    if args.show_goal:
        print_goal_detail(args.show_goal, full=args.show_goal_full)
        return

    if args.add_goal_structured:
        print_add_goal(
            title=args.add_goal_structured,
            description=args.goal_description,
            priority=args.goal_priority,
            status=args.goal_initial_status,
            project=args.goal_project,
            next_action=args.goal_next_action,
        )
        return

    if args.set_goal_status:
        goal_id, status = args.set_goal_status
        print_set_goal_status(goal_id, status, note=args.goal_note)
        return

    if args.add_goal_note:
        goal_id, note = args.add_goal_note
        print_add_goal_note(goal_id, note)
        return

    if args.add_goal_action:
        goal_id, action = args.add_goal_action
        print_add_goal_next_action(goal_id, action)
        return

    if args.block_goal:
        goal_id, reason = args.block_goal
        print_block_goal(goal_id, reason)
        return

    if args.complete_goal:
        print_complete_goal(args.complete_goal, note=args.goal_note)
        return

    if args.search:
        print_keyword_search(args.search)
        return

    if args.semantic_search:
        print_semantic_search(args.semantic_search)
        return

    if args.rebuild_semantic_memory:
        rebuild_semantic_memory()
        return

    if args.project_status:
        print_project_status()
        return

    if args.add_project:
        project = add_project(
            name=args.add_project,
            path=args.project_path,
            language=args.project_language,
            description=args.project_description,
        )
        print(f"Added/set active project: {project.get('name')}")
        return

    if args.set_active_project:
        if set_active_project(args.set_active_project):
            print(f"Active project set to: {args.set_active_project}")
        else:
            print(f"Project not found: {args.set_active_project}")
        return

    active_project = get_active_project()
    active_name = active_project.get("name") if active_project else ""

    if args.add_project_goal:
        if active_name and add_project_item(active_name, "goals", args.add_project_goal):
            print(f"Added goal to {active_name}: {args.add_project_goal}")
        else:
            print("No active project found.")
        return

    if args.add_project_issue:
        if active_name and add_project_item(active_name, "known_issues", args.add_project_issue):
            print(f"Added known issue to {active_name}: {args.add_project_issue}")
        else:
            print("No active project found.")
        return

    if args.add_project_next_step:
        if active_name and add_project_item(active_name, "next_steps", args.add_project_next_step):
            print(f"Added next step to {active_name}: {args.add_project_next_step}")
        else:
            print("No active project found.")
        return

    if args.project_tree is not None:
        print_project_tree(args.project_tree or args.project_file_path)
        return

    if args.read_project_file:
        print_project_file(args.read_project_file)
        return

    if args.search_project_files:
        print_project_file_search(args.search_project_files, path=args.project_file_path)
        return

    if args.index_project is not None:
        result = index_project(relative_path=args.index_project or args.project_file_path)
        print(result.get("message"))
        print(f"Files indexed: {result.get('files_indexed')}")
        if result.get("index_file"):
            print(f"Index file: {result.get('index_file')}")
        return

    if args.project_index_summary:
        print_project_index_summary()
        return

    if args.search_project_index:
        print_project_index_search(args.search_project_index)
        return

    if args.review_project_file:
        print_code_review(args.review_project_file, use_ai=(not args.no_ai_review and ai_reviews_enabled()))
        return

    if args.suggest_patch:
        target_file, request = args.suggest_patch
        print_patch_suggestion(target_file, request, use_ai=True)
        return

    if args.list_patches:
        print_patch_list()
        return

    if args.show_patch:
        print_patch_proposal(args.show_patch, include_full_content=args.show_patch_full)
        return

    if args.apply_patch:
        print_apply_patch(args.apply_patch, dry_run=args.dry_run)
        return

    if args.list_applied_patches:
        print_applied_patches()
        return

    if args.rollback_patch:
        print_rollback_patch(args.rollback_patch, dry_run=args.dry_run)
        return

    if args.list_rolled_back_patches:
        print_rolled_back_patches()
        return

    if args.list_allowed_commands:
        print_allowed_commands()
        return

    if args.run_command:
        print_run_command(args.run_command, dry_run=args.dry_run)
        return

    if args.command_history:
        print_command_history()
        return

    if args.run_test_workflow is not None:
        print_test_workflow(
            patch_id=args.run_test_workflow,
            commands=args.test_command,
            dry_run=args.dry_run,
        )
        if args.auto_review:
            print()
            print("# Auto-review")
            print_test_review("latest", use_ai=(not args.no_ai_test_review and ai_reviews_enabled()))
        return

    if args.list_test_reports:
        print_test_reports()
        return

    if args.show_test_report:
        print_test_report(args.show_test_report, include_output=args.show_test_output)
        return

    if args.review_test_report:
        print_test_review(args.review_test_report, use_ai=(not args.no_ai_test_review and ai_reviews_enabled()))
        return

    if args.list_test_reviews:
        print_test_reviews()
        return

    if args.show_test_review:
        print_saved_test_review(args.show_test_review, include_ai=not args.hide_ai_review)
        return

    if args.self_improve:
        target_file, request = args.self_improve
        print_self_improvement(target_file, request, use_ai_review=(args.self_improve_ai_review and ai_reviews_enabled()))
        return

    if args.self_improve_apply:
        print_self_improvement_apply(
            args.self_improve_apply,
            commands=args.test_command,
            use_ai_review=(not args.no_ai_self_review and ai_reviews_enabled()),
            dry_run=args.dry_run,
        )
        return

    if args.list_self_improvements:
        print_self_improvement_runs()
        return

    if args.show_self_improvement:
        print_self_improvement_run(args.show_self_improvement, include_review=args.show_self_improvement_full)
        return

    if args.chat:
        run_chat()
        return

    if args.loop:
        run_loop(delay_seconds=args.delay)
        return

    # Default behavior: one cycle, so it does not trap beginners in an infinite loop immediately.
    run_cycle(verbose=True)


if __name__ == "__main__":
    main()

# v215.1-v220.0 simulation/foresight CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --supervised-internal-simulation-packet-layer --operator-governed-foresight-branch-comparison --supervised-pre-change-consequence-modeling --supervised-expectation-reality-check-layer --operator-governed-internal-simulation-and-foresight-layer-v1

# v220.1-v225.0 learning curriculum CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --supervised-learning-objective-map --supervised-practice-task-design-layer --operator-governed-capability-calibration-layer --supervised-skill-gap-remediation-planner --operator-governed-learning-curriculum-and-capability-calibration-layer-v1

# v225.1-v230.0 knowledge/belief CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --supervised-knowledge-claim-ledger --operator-reviewed-belief-candidate-layer --supervised-contradiction-and-staleness-intelligence --supervised-project-knowledge-map-layer --operator-governed-knowledge-and-belief-organization-layer-v1

# v230.1-v235.0 local model workbench CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-local-model-inventory-layer --supervised-model-evaluation-plan-layer --operator-governed-model-output-comparison-layer --supervised-cognitive-workbench-routing-layer --operator-governed-local-model-evaluation-and-cognitive-workbench-layer-v1
# v235.1-v240.0 local model invocation sandbox CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-approved-local-model-invocation-consent-gate --sandboxed-model-evaluation-run-ledger --operator-governed-multi-model-output-triage --supervised-model-reliability-profile-candidates --operator-approved-local-model-invocation-sandbox-v1

# v240.1-v245.0 model-assisted patch review CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-model-assisted-patch-critique-layer --supervised-multi-model-review-synthesis-layer --operator-governed-patch-risk-and-remediation-synthesis --supervised-model-review-quality-calibration --operator-governed-model-assisted-patch-review-and-synthesis-layer-v1

# v245.1-v250.0 model-assisted patch draft assembly CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-model-assisted-patch-draft-packet-layer --supervised-file-impact-and-documentation-planner --supervised-smoke-and-verification-suggestion-layer --operator-governed-sandbox-preparation-packet-layer --operator-governed-model-assisted-patch-draft-assembly-layer-v1

# v250.1-v255.0 patch execution packet bridge CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-draft-to-execution-packet-gate --supervised-patch-diff-preview-and-edit-plan-layer --operator-governed-explicit-approval-scope-ledger --supervised-verification-and-rollback-packet-planner --operator-governed-patch-execution-packet-bridge-v1

# v255.1-v260.0 approved application prep CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-execution-packet-intake-layer --supervised-source-edit-application-plan-builder --supervised-documentation-and-release-metadata-application-plan --operator-governed-final-pre-application-governance-gate --operator-governed-approved-execution-packet-application-prep-v1

# v260.1-v265.0 structural stabilization CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-structural-inventory-layer --operator-governed-runtime-registry-prep-layer --operator-governed-dashboard-stabilization-layer --operator-governed-cli-api-dispatch-stabilization-layer --operator-governed-structural-stabilization-and-runtime-modularization-v1

# v265.1-v270.0 module extraction CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-runtime-metadata-registry-extraction --operator-governed-governance-report-builder-extraction --operator-governed-dashboard-surface-registry-integration --operator-governed-cli-api-runtime-registry-integration --operator-governed-runtime-module-extraction-v1

# v270.1-v275.0 self-maintenance decomposition CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-self-maintenance-extraction-map --operator-governed-package-and-version-utility-extraction --operator-governed-surface-parity-utility-extraction --operator-governed-smoke-and-verification-utility-extraction --operator-governed-self-maintenance-decomposition-v1

# v275.1-v280.0 dashboard/API/CLI modularization CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-dashboard-surface-extraction-map --operator-governed-dashboard-component-helper-extraction --operator-governed-api-surface-helper-extraction --operator-governed-cli-surface-helper-extraction --operator-governed-dashboard-api-cli-modularization-v1

# v280.1-v285.0 application execution refinement CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-approved-application-packet-binding-layer --operator-execution-checklist-builder-layer --operator-governed-post-application-result-review-layer --operator-governed-application-outcome-learning-extractor --operator-approved-application-execution-refinement-v1 application_execution_refinement.py

# v285.1-v290.0 rollback and recovery intelligence CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-rollback-scope-binding-layer --operator-governed-failure-classification-and-damage-map --operator-governed-recovery-checklist-builder --operator-governed-post-recovery-review-layer --operator-governed-rollback-and-recovery-intelligence-v1 rollback_recovery.py

# v290.1-v295.0 memory candidate governance CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --memory-candidate-intake --memory-candidate-classification --memory-approval-packet --memory-contradiction-review --memory-governance-audit memory_governance.py

# v295.1-v300.0 continuity kernel CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --continuity-state-intake --self-model-snapshot-v2 --purpose-coherence-review --supervised-growth-priorities --continuity-kernel-v2-audit continuity_kernel.py
# v300.1-v305.0 identity/personality/coherence expression CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-identity-expression-boundary-layer --operator-governed-personality-trait-candidate-ledger --operator-governed-voice-and-affect-style-map --operator-governed-coherence-expression-review --operator-governed-identity-personality-coherence-expression-layer-v1 identity_expression.py risky_request_classifier
# v305.1-v310.0 behavioral expression preview and runtime health CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-dashboard-route-health-registry-v1 --operator-governed-runtime-test-visibility-layer-v1 --operator-governed-behavioral-expression-preview-packets-v1 --operator-governed-style-delta-staging-v1 --operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1 route_health.py behavioral_expression_preview.py

# v310.1-v315.0 conversational expression sandbox CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-expression-profile-packet-assembly-v1 --operator-governed-conversation-scenario-sandbox-v1 --operator-governed-expression-regression-review-v1 --operator-governed-expression-candidate-review-console-v1 --operator-governed-conversational-expression-sandbox-v1 conversational_expression_sandbox.py

# v315.1-v320.0 expression application bridge CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-expression-approval-criteria-layer-v1 --operator-governed-live-surface-impact-map-v1 --operator-governed-expression-implementation-packet-drafting-v1 --operator-governed-expression-rollback-and-reversion-planning-v1 --operator-governed-conversational-expression-application-bridge-v1 expression_application_bridge.py
# v320.1-v325.0 expression patch dry-run CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-expression-patch-candidate-schema-v1 --operator-governed-sandbox-diff-preview-assembly-v1 --operator-governed-expression-dry-run-verification-planning-v1 --operator-governed-expression-dry-run-review-packet-v1 --operator-governed-expression-patch-dry-run-sandbox-v1 expression_patch_dry_run.py

# v325.1-v330.0 expression sandbox trial harness CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-expression-sandbox-trial-packet-prep-v1 --operator-governed-expression-sandbox-workspace-plan-v1 --operator-governed-expression-sandbox-trial-verification-matrix-v1 --operator-governed-expression-sandbox-trial-result-review-prep-v1 --operator-governed-expression-patch-sandbox-trial-harness-v1 expression_sandbox_trial_harness.py

# v330.1-v335.0 expression sandbox execution bridge CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-sandbox-trial-execution-approval-gate-v1 --operator-governed-sandbox-workspace-execution-packet-draft-v1 --operator-governed-expression-sandbox-patch-bundle-packet-v1 --operator-governed-sandbox-verification-command-packet-draft-v1 --operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 expression_sandbox_execution_bridge.py

# v335.1-v340.0 expression sandbox result intake CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-sandbox-trial-evidence-intake-layer-v1 --operator-governed-sandbox-outcome-comparison-v1 --operator-governed-expression-regression-result-review-v1 --operator-governed-sandbox-trial-revision-recommendation-layer-v1 --operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1 expression_sandbox_result_intake.py

# v340.1-v345.0 expression promotion packet CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-expression-promotion-evidence-binder-v1 --operator-governed-live-promotion-scope-and-risk-packet-v1 --operator-governed-promotion-verification-and-rollback-requirements-v1 --operator-governed-expression-promotion-decision-packet-v1 --operator-governed-expression-promotion-packet-assembly-layer-v1 expression_promotion_packet.py

# v345.1-v350.0 expression live application packet CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-live-application-packet-eligibility-gate-v1 --operator-governed-live-source-change-manifest-draft-v1 --operator-governed-live-diff-and-patch-instruction-packet-draft-v1 --operator-governed-live-application-verification-and-rollback-packet-v1 --operator-governed-expression-live-application-packet-drafting-layer-v1 expression_live_application_packet.py

# v350.1-v355.0 expression live application execution prep CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-live-expression-execution-approval-intake-v1 --operator-governed-live-source-transaction-preimage-v1 --operator-governed-live-expression-manual-execution-checklist-v1 --operator-governed-live-expression-rollback-reversion-packet-v1 --operator-governed-expression-live-application-execution-prep-v1 expression_live_execution_prep.py
# v355.1-v360.0 minimal live expression application CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-approved-minimal-live-expression-change-candidate-v1 --operator-approved-minimal-live-expression-approval-lock-v1 --operator-approved-minimal-live-expression-patch-transaction-v1 --operator-confirmed-minimal-live-expression-application-harness-v1 --operator-approved-minimal-live-expression-application-audit-v1 minimal_live_expression_application.py candidate_selection_applies_change=False approval_lock_self_approves=False transaction_builder_writes_files=False application_harness_executes_without_confirmation=False application_audit_publishes_release=False

# v360.1-v365.0 self-maintenance refactor CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-self-maintenance-gate-inventory-registry-seed-v1 --operator-governed-self-maintenance-version-expectation-layer-v1 --operator-governed-surface-metadata-registry-v1 --operator-governed-smoke-check-registry-and-legacy-gate-cleanup-v1 --operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1 self_maintenance_refactor_registry.py refactor_registry_writes_files=False refactor_registry_executes_smoke=False centralized_version_expectations_required=True

# v365.1-v370.0 minimal live change replay CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-minimal-live-change-replay-packet-v1 --operator-governed-minimal-live-change-expected-actual-comparison-v1 --operator-governed-minimal-live-change-regression-drift-detector-v1 --operator-governed-minimal-live-change-recovery-recommendation-v1 --operator-governed-minimal-live-change-replay-and-regression-hardening-v1 minimal_live_change_replay.py replay_packet_applies_change=False expected_actual_writes_files=False regression_detector_auto_fixes=False recovery_recommendation_executes_rollback=False

# v370.1-v375.0 modular extraction CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-self-maintenance-module-extraction-plan-v1 --operator-governed-self-maintenance-version-package-gate-extraction-v1 --operator-governed-self-maintenance-surface-gate-extraction-v1 --operator-governed-self-maintenance-governance-gate-extraction-v1 --operator-governed-self-maintenance-modular-extraction-v1 self_maintenance_modular_extraction.py modular_extraction_applies_live_patches=False

# v375.1-v380.0 live change application trial CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-live-change-transaction-narrowing-v1 --operator-governed-live-change-approval-execution-lock-v1 --operator-governed-live-change-real-patch-trial-plan-v1 --operator-confirmed-live-change-application-trial-v1 --operator-governed-live-change-application-trial-audit-v1 live_change_application_trial.py transaction_narrowing_applies_patch=False approval_execution_lock_self_approves=False trial_plan_writes_files=False application_trial_runs_without_confirmation=False application_trial_continues_automatically=False
# v380.1-v385.0 live patch trial closure CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-live-patch-trial-result-intake-v1 --operator-governed-live-patch-applied-diff-evidence-v1 --operator-governed-live-patch-approval-burnout-v1 --operator-governed-live-patch-post-trial-regression-review-v1 --operator-governed-live-patch-trial-closure-audit-v1 live_patch_trial_closure.py result_intake_reruns_commands=False diff_evidence_edits_source=False approval_burnout_reuses_approval=False post_trial_review_executes_rollback=False closure_audit_applies_another_patch=False

# v385.1-v390.0 second live patch trial CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-second-minimal-live-patch-candidate-v1 --operator-governed-registry-driven-live-patch-approval-validation-v1 --operator-governed-registry-driven-live-patch-transaction-lock-v1 --operator-confirmed-second-live-patch-application-harness-v1 --operator-governed-second-live-patch-trial-registry-audit-v1 second_live_patch_trial.py candidate_selection_applies_patch=False approval_validation_reuses_approval=False transaction_lock_writes_files=False application_harness_runs_without_confirmation=False registry_audit_applies_patch=False
# v390.1-v395.0 live patch history memory candidate CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-live-patch-trial-history-ledger-v1 --operator-governed-live-patch-decision-pattern-review-v1 --operator-governed-live-patch-supervised-lesson-candidate-drafting-v1 --operator-governed-live-patch-memory-candidate-governance-v1 --operator-governed-live-patch-history-and-memory-candidate-audit-v1 live_patch_history_memory_candidates.py history_ledger_treats_history_as_permission=False decision_review_changes_future_behavior=False lesson_candidates_write_memory=False memory_governance_stores_memory=False history_memory_audit_writes_memory=False memory_candidates_review_only=True operator_approval_required_before_memory_storage=True

# v395.1-v400.0 memory candidate application trial CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-governed-memory-candidate-selection-packet-v1 --operator-governed-memory-application-approval-lock-v1 --operator-governed-memory-write-transaction-preview-v1 --operator-confirmed-memory-application-trial-v1 --operator-governed-memory-application-trial-audit-v1 memory_candidate_application_trial.py candidate_selection_writes_memory=False approval_lock_reuses_approval=False transaction_preview_writes_memory=False application_harness_runs_without_confirmation=False application_audit_runs_retraction=False fresh_operator_approval_required=True single_use_memory_approval_required=True sensitive_data_screen_required=True identity_personality_mutation_screen_required=True retraction_packet_required=True

# v510.1-v515.0 sandbox execution approval gate routes/CLI flags are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-approval-scope-contract/layer /api/exact-confirmation-phrase-builder/layer /api/approval-burnout-expiry-ledger/layer /api/sandbox-command-allowlist-preview/layer /api/sandbox-execution-approval-gate-audit/layer --sandbox-execution-approval-gate-v1 sandbox_execution_approval_gate.py approval_contract_exists_is_approval_granted=False confirmation_phrase_generated_is_confirmation_entered=False command_preview_executes_commands=False approval_status=not_granted execution_status=not_executed sandbox_status=not_started autonomy_status=not_autonomous
# v515.1-v520.0 sandbox execution dry-run receipt routes/CLI flags are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-dry-run-execution-model/layer /api/command-transcript-preview/layer /api/sandbox-diff-receipt-preview/layer /api/dry-run-misinterpretation-firewall/layer /api/sandbox-execution-dry-run-receipt-audit/layer --sandbox-execution-dry-run-receipt-v1 sandbox_execution_dry_run_receipt.py dry_run_model_exists_is_sandbox_execution=False transcript_preview_is_command_output=False diff_receipt_preview_is_actual_file_change=False dry_run_success_is_authorization=False dry_run_receipt_status=prepared actual_execution_status=not_executed approval_status=not_granted sandbox_status=not_started autonomy_status=not_autonomous

# v520.1-v525.0 first sandbox execution trial routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-workspace-isolation-contract/layer /api/approved-sandbox-command-plan/layer /api/single-use-sandbox-execution-receipt/layer /api/sandbox-execution-misinterpretation-firewall/layer /api/first-sandbox-execution-trial-audit/layer --first-operator-approved-sandbox-execution-trial-v1 first_sandbox_execution_trial.py sandbox_workspace_exists_is_execution_permission=False command_plan_exists_is_command_run=False receipt_written_is_future_approval=False successful_sandbox_trial_is_autonomy=False trial_layer_status=prepared sandbox_execution_status=not_run_by_default approval_status=required live_source_status=untouched memory_status=untouched autonomy_status=not_autonomous

# v525.1-v530.0 sandbox execution runner routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-execution-runner-contract/layer /api/approval-phrase-validator/layer /api/sandbox-command-execution-harness/layer /api/execution-receipt-intake-cleanup-audit/layer /api/sandbox-execution-trial-review-board/layer --operator-approved-sandbox-execution-runner-v1 sandbox_execution_runner.py runner_contract_exists_is_execution_permission=False phrase_validated_is_command_executed=False sandbox_command_success_is_live_patch_approval=False receipt_success_is_future_authorization=False runner_status=available_under_approval_only execution_status=not_executed_by_default approval_status=required live_source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous

# v530.1-v540.0 sandbox-to-source promotion packet routes are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: /api/sandbox-evidence-intake-packet/layer /api/promotion-candidate-diff-preview/layer /api/rollback-recovery-packet-builder/layer /api/promotion-misinterpretation-firewall/layer /api/sandbox-to-source-promotion-review-board/layer --sandbox-to-source-promotion-packet-v1 sandbox_to_source_promotion_packet.py sandbox_evidence_exists_is_live_source_approval=False promotion_diff_preview_is_live_source_mutation=False rollback_packet_exists_is_rollback_executed=False promotion_packet_status=prepared live_source_status=untouched approval_status=required authorization_status=not_authorized rollback_status=planned_not_executed release_status=not_created autonomy_status=not_autonomous
# v601.0-v605.0 current-state integrity hardening CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --smoke-summary-version-alignment-contract-v1 --nested-metadata-root-version-guard-v1 --readme-current-handoff-staleness-guard-v1 --setup-smoke-scope-guard-v1 --current-state-integrity-staleness-hardening-board-v1 current-state-integrity-staleness-hardening-v1 current_state_integrity_staleness_hardening.py hardening_report_writes_source=False hardening_report_writes_metadata=False hardening_report_executes_smoke=False audit_pass_is_release_approval=False audit_pass_is_live_patch_permission=False
# v606.0-v610.0 archive reconciliation application prep CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --archive-reconciliation-application-scope-packet-v1 --reconciliation-application-candidate-map-v1 --operator-reconciliation-application-approval-checklist-v1 --dry-run-application-receipt-prep-v1 --archive-reconciliation-application-prep-board-v1 archive-reconciliation-application-prep-v1 archive_reconciliation_application_prep.py application_prep_board_is_operator_approval=False application_prep_board_writes_archive_records=False application_prep_board_mutates_current_state=False

# v611.0-v615.0 operator command center UI consolidation CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --command-center-landing-screen-v1 --operator-queue-panel-v1 --safety-state-panel-v1 --workflow-navigation-groups-v1 --system-health-summary-board-v1 --operator-command-center-ui-consolidation-board-v1 operator-command-center-ui-consolidation-v1 operator_command_center_ui_consolidation.py command_center_executes_actions=False operator_queue_grants_approval=False safety_panel_changes_authorization=False system_health_summary_runs_smoke=False ui_consolidation_expands_autonomy=False

# v616.0-v620.0 dashboard workflow simplification CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --workflow-group-route-index-v1 --legacy-route-drawer-v1 --archive-workflow-pipeline-view-v1 --patch-safety-memory-group-views-v1 --dashboard-simplification-board-v1 dashboard-workflow-simplification-legacy-drawer-v1 dashboard_workflow_simplification.py workflow_index_executes_actions=False legacy_drawer_deletes_routes=False archive_pipeline_writes_archive_records=False group_views_write_memory=False simplification_board_expands_autonomy=False

# v621.0-v625.0 operator action semantics UX CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --universal-action-label-standard-v1 --blocked-action-explanation-cards-v1 --one-time-approval-burnout-ux-v1 --safe-preview-before-action-summary-v1 --operator-action-semantics-board-v1 operator-action-semantics-approval-ux-v1 operator_action_semantics_ux.py action_labels_execute_actions=False blocked_cards_unblock_actions=False approval_card_reuses_approval=False safe_preview_executes_action=False semantics_board_expands_autonomy=False
# v626.0-v630.0 review packet evidence UX CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --review-packet-summary-header-v1 --evidence-grouping-priority-layout-v1 --receipt-ledger-readability-cards-v1 --system-health-evidence-ux-v1 --review-packet-evidence-ux-board-v1 review-packet-readability-evidence-ux-v1 review_packet_evidence_ux.py summary_header_grants_approval=False evidence_grouping_hides_raw_evidence=False receipt_cards_treat_receipt_as_approval=False system_health_panels_run_smoke=False evidence_board_expands_autonomy=False
# v631.0-v635.0 dashboard search and surface discovery CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --surface-search-index-v1 --route-module-smoke-discovery-cards-v1 --workflow-aware-search-filters-v1 --current-historical-surface-guard-v1 --dashboard-search-discovery-board-v1 operator-dashboard-search-surface-discovery-v1 dashboard_search_surface_discovery.py search_index_grants_approval=False search_index_treats_presence_as_authorization=False discovery_cards_execute_commands=False workflow_filters_hide_safety=False current_historical_guard_treats_current_as_approval=False discovery_board_expands_autonomy=False
# v636.0-v640.0 operator decision capture/approval form UX CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --decision-capture-form-schema-v1 --approval-scope-target-binding-panel-v1 --approval-expiration-burnout-form-ux-v1 --denial-deferral-revision-decision-capture-v1 --operator-decision-approval-ux-board-v1 operator-decision-capture-approval-form-ux-v1 operator_decision_approval_ux.py decision_form_creates_approval=False scope_binding_grants_authorization=False approval_burnout_reuse_allowed=False denial_deferral_is_approval=False ux_board_expands_autonomy=False
# v641.0-v645.0 operator receipt timeline/audit UX CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --operator-decision-timeline-model-v1 --approval-burnout-consumption-timeline-cards-v1 --blocked-action-safety-event-timeline-cards-v1 --verification-receipt-timeline-cards-v1 --decision-audit-trail-board-v1 operator-receipt-timeline-decision-audit-trail-ux-v1 operator_receipt_timeline_audit_ux.py timeline_model_grants_approval=False approval_consumption_cards_allow_reuse=False blocked_action_cards_unblock_actions=False verification_cards_treat_pass_as_authorization=False audit_trail_expands_autonomy=False

# v646.0-v650.0 operator session continuity/resume UX CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --session-resume-state-summary-v1 --unresolved-warning-blocker-carryover-v1 --pending-decisions-prepared-work-resume-queue-v1 --verification-state-resume-card-v1 --operator-session-continuity-board-v1 operator-session-continuity-resume-console-ux-v1 operator_session_continuity_resume_ux.py resume_summary_starts_work=False pending_queue_starts_work=False verification_card_treats_pass_as_authorization=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False

# v651.0-v655.0 operator guided review wizard UX CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --guided-review-wizard-entry-model-v1 --guided-evidence-warning-step-cards-v1 --guided-decision-approval-step-ux-v1 --guided-verification-resume-step-summary-v1 --operator-guided-review-wizard-board-v1 operator-guided-review-wizard-ux-v1 operator_guided_review_wizard_ux.py wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_treats_pass_as_authorization=False wizard_board_expands_autonomy=False

# v656.0-v660.0 project metadata schema and active context repair CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --metadata-schema-contract-v1 --active-project-resolution-audit-v1 --project-status-rendering-hardening-v1 --release-note-version-semantics-audit-v1 --metadata-integrity-board-smoke-gate-v1 project-metadata-schema-active-context-repair-v1 project_metadata_active_context_repair.py schema_contract_writes_metadata=False active_project_resolution_changes_project=False status_rendering_executes_actions=False release_note_semantics_rewrites_history=False metadata_integrity_board_executes_smoke=False metadata_integrity_board_expands_autonomy=False

# v661.0-v665.0 legacy smoke segmentation repair CLI flags are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py current_gate_executes_smoke=False legacy_advisory_blocks_current_release=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False
# v666.0-v675.0 manifest-driven surface registry CLI flags are handled dynamically by SUPERVISED_RUNTIME_ROUTE_MAP/SUPERVISED_RUNTIME_CLI_MAP: surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board manifest-driven-surface-registry-v1 manifest_driven_surface_registry.py api_cli_manifest_adapter_status=validated_or_blocked api_cli_manifest_adapter_executes_commands=False manifest_presence_is_authorization=False registry_health_is_approval=False manifest_board_expands_autonomy=False

# v676.0-v685.0 dashboard renderer component extraction CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --dashboard-component-contract-v1 --shared-review-packet-renderer-v1 --shared-boundary-matrix-renderer-v1 --shared-evidence-warning-renderer-v1 --shared-decision-approval-renderer-v1 --shared-resume-continuity-renderer-v1 --dashboard-route-renderer-adapter-v1 --dashboard-style-regression-guard-v1 --legacy-renderer-duplication-audit-v1 --dashboard-renderer-component-extraction-board-v1 dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py renderer_presence_is_authorization=False style_guard_pass_is_approval=False component_board_expands_autonomy=False

# v686.0-v690.0 neural command deck dashboard redesign CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --neural-deck-layout-shell-v1 --eidolon-thinking-core-panel-v1 --operator-conversation-console-v1 --side-intelligence-panels-v1 --neural-command-deck-dashboard-board-v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py visual_health_is_authorization=False thinking_animation_is_model_execution=False

# v691.0-v695.0 neural command deck interaction refinement CLI flags are registered dynamically through SUPERVISED_RUNTIME_CLI_MAP: --interaction-focus-rail-v1 --interaction-safe-input-deck-v1 --panel-density-priority-tuning-v1 --context-telemetry-affordance-v1 --neural-command-deck-interaction-board-v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v760.0 duplicate cleanup CLI tokens: --self-development-cycle-duplicate-cleanup build_self_development_cycle_duplicate_cleanup_review self_development_cycle_duplicate_cleanup_review_text self-development-cycle-duplicate-cleanup-v1 expands_autonomy=False
# v845.0 smoke debt ledger reconciliation CLI tokens: --current-smoke-debt-ledger-reconciliation build_current_smoke_debt_ledger_reconciliation_review current_smoke_debt_ledger_reconciliation_review_text current-smoke-debt-ledger-reconciliation-v1 resolved_legacy_smoke_debt_not_active=True install_regression_recent_expected_status=pass marks_blockers_as_pass=False runs_broad_smoke=False expands_autonomy=False
# v845.0 legacy self-maintenance smoke blocker review CLI tokens: --legacy-self-maintenance-smoke-blocker-review build_legacy_self_maintenance_smoke_blocker_review legacy_self_maintenance_smoke_blocker_review_text legacy-self-maintenance-smoke-blocker-review-v1 install_regression_recent_expected_status=pass marks_blockers_as_pass=False runs_broad_smoke=False expands_autonomy=False

# v845.0 current audit wording cleanup CLI tokens: --current-audit-wording-cleanup --manifest-generation-prep-review build_current_audit_wording_cleanup_review current_audit_wording_cleanup_review_text build_manifest_generation_prep_review manifest_generation_prep_review_text current-audit-wording-cleanup-v1 manifest-generation-prep-review-v1 stale_current_audit_wording_clean=True historical_release_references_allowed=True manifest_generation_prep_is_review_only=True generates_surfaces=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False modifies_approval_system=False modifies_release_system=False expands_autonomy=False

# v845.0 manifest-gated surface validation CLI tokens: manifest-gated-surface-validation-v1 --manifest-gated-surface-validation build_manifest_gated_surface_validation_review manifest_gated_surface_validation_review_text validation_is_review_only=True generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False expands_autonomy=False

# v845.0 manifest-driven surface registry pilot CLI tokens: manifest-driven-surface-registry-pilot-v1 --manifest-driven-surface-registry-pilot --manifest-surface-generation-readiness build_manifest_driven_surface_registry_pilot_review manifest_driven_surface_registry_pilot_review_text build_manifest_surface_generation_readiness_review manifest_surface_generation_readiness_review_text registry_pilot_is_review_only=True pilot_registers_one_surface=True generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False safe_for_manifest_registration safe_for_generated_validation_only manual_until_further_review protected_operator_controlled never_autonomous applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False expands_autonomy=False

# v845.0 manifest registry expansion CLI tokens: manifest-registry-expanded-review-surfaces-v1 --manifest-registry-expanded-review-surfaces --manifest-registry-generation-readiness-scoring build_manifest_registry_expanded_review_surfaces_review manifest_registry_expanded_review_surfaces_review_text build_manifest_registry_generation_readiness_scoring_review manifest_registry_generation_readiness_scoring_review_text registry_expansion_is_review_only=True selected_surface_count=8 additional_surface_count=7 generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False expands_autonomy=False

# v845.0 manifest registry drift detection CLI tokens: manifest-registry-drift-detection-v1 --manifest-registry-drift-detection build_manifest_registry_drift_detection_review manifest_registry_drift_detection_review_text registry_drift_detection_is_review_only=True registered_surface_count=8 drift_count=0 in_sync_count=8 generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False expands_autonomy=False

# v845.0 manifest-guided validation probe dry-run CLI tokens: manifest-guided-validation-probe-dry-run-v1 --manifest-guided-validation-probe-dry-run build_manifest_guided_validation_probe_dry_run_review manifest_guided_validation_probe_dry_run_review_text validation_probe_dry_run_is_review_only=True dry_run_selected_surface_count=1 planned_probe_check_count=8 selected_surface_id=v780-manifest-gated-surface-validation generates_validation_probe=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False expands_autonomy=False

# v845.0 manifest-guided generated validation probe CLI tokens: manifest-guided-generated-validation-probe-v1 --manifest-guided-generated-validation-probe build_manifest_guided_generated_validation_probe_review manifest_guided_generated_validation_probe_review_text generated_validation_probe_is_review_only=True generated_probe_selected_surface_count=1 generated_probe_check_count=8 selected_surface_id=v780-manifest-gated-surface-validation smoke_segment_parity_status=deferred generates_validation_probe=True generates_live_validation_probe=False generated_wiring_activated=False writes_probe_file=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False expands_autonomy=False

# v845.0 manifest smoke segment parity drift CLI tokens: manifest-smoke-segment-parity-drift-v1 --manifest-smoke-segment-parity-drift build_manifest_smoke_segment_parity_drift_review manifest_smoke_segment_parity_drift_review_text manifest_smoke_segment_parity_drift_is_review_only=True manifest_surface_count surfaces_with_smoke_checks matching_segment_count mismatching_segment_count missing_live_segment_count known_mismatch_detected=True auto_repair_enabled=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest smoke segment parity repair packet CLI tokens: manifest-smoke-segment-parity-repair-packet-v1 --manifest-smoke-segment-parity-repair-packet build_manifest_smoke_segment_parity_repair_packet_review manifest_smoke_segment_parity_repair_packet_review_text manifest_smoke_segment_parity_repair_packet_is_review_only=True proposed_repair_count auto_apply_enabled=False applies_repair=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest smoke segment repair application CLI tokens: manifest-smoke-segment-repair-application-v1 --manifest-smoke-segment-repair-application build_manifest_smoke_segment_repair_application_review manifest_smoke_segment_repair_application_review_text manifest_smoke_segment_repair_application_is_review_only=True operator_approved_application=True corrected_segment_count=35 mismatching_segment_count_after_application=0 proposed_repair_count_after_application=0 known_v780_segment_corrected=True auto_apply_enabled=False runtime_writes_manifest=False writes_manifest=True writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=True creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest segment parity enforcement gate CLI tokens: manifest-segment-parity-enforcement-gate-v1 --manifest-segment-parity-enforcement-gate build_manifest_segment_parity_enforcement_gate_review manifest_segment_parity_enforcement_gate_review_text manifest_segment_parity_enforcement_gate_is_review_only=True release_blocking=True enforcement_gate_passed=True mismatching_segment_count=0 missing_live_segment_count=0 auto_repair_enabled=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest-guided validation probe expansion readiness CLI tokens: manifest-guided-validation-probe-expansion-readiness-v1 --manifest-guided-validation-probe-expansion-readiness build_manifest_guided_validation_probe_expansion_readiness_review manifest_guided_validation_probe_expansion_readiness_review_text expansion_readiness_is_review_only=True currently_supported_probe_surface_count=1 recommended_expansion_surface_count=3 blocked_surface_count=0 readiness_passed=True expansion_mode=review_only generated_wiring_enabled=False generated_wiring_activated=False generates_multi_surface_probe=False generates_validation_probe=False generates_live_validation_probe=False writes_probe_file=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest-guided multi-surface validation probe dry-run CLI tokens: manifest-guided-multi-surface-validation-probe-dry-run-v1 --manifest-guided-multi-surface-validation-probe-dry-run build_manifest_guided_multi_surface_validation_probe_dry_run_review manifest_guided_multi_surface_validation_probe_dry_run_review_text multi_surface_validation_probe_dry_run_is_review_only=True selected_surface_count=3 planned_probe_check_count_per_surface=8 total_planned_probe_check_count=24 segment_parity_gate_passed=True generated_wiring_enabled=False generated_wiring_activated=False writes_probe_files=False generates_live_validation_probe=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest-guided multi-surface generated validation probe packet CLI tokens: manifest-guided-multi-surface-generated-validation-probe-packet-v1 --manifest-guided-multi-surface-generated-validation-probe-packet build_manifest_guided_multi_surface_generated_validation_probe_packet_review manifest_guided_multi_surface_generated_validation_probe_packet_review_text multi_surface_generated_validation_probe_packet_is_review_only=True selected_surface_count=3 generated_probe_packet_count=3 generated_probe_check_count_per_surface=8 total_generated_probe_check_count=24 segment_parity_gate_passed=True expansion_readiness_passed=True dry_run_prerequisite_passed=True writes_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v850.0 manifest-guided multi-surface probe packet consistency gate CLI tokens: manifest-guided-multi-surface-probe-packet-consistency-gate-v1 --manifest-guided-multi-surface-probe-packet-consistency-gate build_manifest_guided_multi_surface_probe_packet_consistency_gate_review manifest_guided_multi_surface_probe_packet_consistency_gate_review_text multi_surface_probe_packet_consistency_gate_is_review_only=True selected_surface_count=3 dry_run_surface_count=3 generated_packet_surface_count=3 expected_surface_ids_match=True check_count_per_surface=8 total_check_count=24 segment_parity_gate_passed=True expansion_readiness_passed=True dry_run_prerequisite_passed=True generated_packet_prerequisite_passed=True consistency_gate_passed=True release_blocking=True writes_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v865.0 manifest-guided sandbox probe file generation readiness CLI tokens: manifest-guided-sandbox-probe-file-generation-readiness-v1 --manifest-guided-sandbox-probe-file-generation-readiness build_manifest_guided_sandbox_probe_file_generation_readiness_review manifest_guided_sandbox_probe_file_generation_readiness_review_text sandbox_probe_file_generation_readiness_is_review_only=True selected_surface_count=3 eligible_surface_count=3 planned_sandbox_probe_file_count=3 generated_probe_file_count=0 consistency_gate_passed=True consistency_gate_prerequisite_passed=True policy_count=8 policies_passed=True readiness_passed=True release_blocking=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v865.0 manifest-guided sandbox probe file generation dry-run CLI tokens: manifest-guided-sandbox-probe-file-generation-dry-run-v1 --manifest-guided-sandbox-probe-file-generation-dry-run build_manifest_guided_sandbox_probe_file_generation_dry_run manifest_guided_sandbox_probe_file_generation_dry_run_text sandbox_probe_file_generation_dry_run_is_review_only=True selected_surface_count=3 readiness_prerequisite_passed=True planned_probe_file_count=3 preview_probe_file_count=3 written_probe_file_count=0 generated_probe_file_count=0 policy_count=12 policies_passed=True dry_run_passed=True release_blocking=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v865.0 operator-approved sandbox probe file generation trial CLI tokens: operator-approved-sandbox-probe-file-generation-trial-v1 --operator-approved-sandbox-probe-file-generation-trial build_operator_approved_sandbox_probe_file_generation_trial operator_approved_sandbox_probe_file_generation_trial_text selected_surface_count=3 readiness_prerequisite_passed=True dry_run_prerequisite_passed=True operator_approval_required=True operator_approval_present=True planned_probe_file_count=3 preview_probe_file_count=3 written_probe_file_count=3 sandbox_generated_probe_file_count=3 generated_live_probe_file_count=0 file_content_matches_preview=True policy_count=14 policies_passed=True generation_trial_passed=True release_blocking=True review_only=False operator_approved_sandbox_write=True writes_probe_files=True generates_sandbox_probe_files=True generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v870.0 sandbox probe file verification and cleanup review CLI tokens: sandbox-probe-file-verification-and-cleanup-review-v1 --sandbox-probe-file-verification-and-cleanup-review build_sandbox_probe_file_verification_and_cleanup_review sandbox_probe_file_verification_and_cleanup_review_text sandbox_probe_file_verification_and_cleanup_review_is_review_only=True sandbox_probe_file_count=3 expected_probe_file_count=3 unexpected_probe_file_count=0 missing_probe_file_count=0 files_match_dry_run_preview=True all_paths_inside_sandbox_root=True unsafe_import_count=0 command_execution_detected=False memory_write_detected=False approval_write_detected=False release_write_detected=False scheduler_write_detected=False network_access_detected=False live_wiring_detected=False cleanup_plan_available=True cleanup_review_only=True verification_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v885.0 sandbox probe execution harness readiness CLI tokens: sandbox-probe-execution-harness-readiness-review-v1 --sandbox-probe-execution-harness-readiness-review build_sandbox_probe_execution_harness_readiness_review sandbox_probe_execution_harness_readiness_review_text sandbox_probe_execution_harness_readiness_review_is_review_only=True sandbox_probe_file_count=3 verification_prerequisite_passed=True execution_harness_defined=True execution_performed=False probe_execution_count=0 command_allowlist_defined=True timeout_policy_defined=True network_access_allowed=False scheduler_access_allowed=False memory_write_allowed=False approval_write_allowed=False release_write_allowed=False source_write_allowed=False live_wiring_allowed=False stdout_capture_defined=True stderr_capture_defined=True result_schema_defined=True cleanup_plan_available=True operator_approval_required=True single_use_approval_required=True approval_burnout_required=True policy_count=36 policies_passed=True readiness_passed=True release_blocking=True review_only=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False executes_probe_files=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v885.0 operator-approved sandbox probe execution trial CLI tokens: operator-approved-sandbox-probe-execution-trial-v1 --operator-approved-sandbox-probe-execution-trial build_operator_approved_sandbox_probe_execution_trial operator_approved_sandbox_probe_execution_trial_text operator_approved_sandbox_probe_execution_trial=True selected_surface_count=3 execution_harness_prerequisite_passed=True verification_prerequisite_passed=True sandbox_probe_file_count=3 operator_approval_required=True operator_approval_present=True single_use_approval_required=True approval_burnout_required=True execution_performed=True probe_execution_count=3 probe_execution_pass_count=3 probe_execution_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 network_access_detected=False scheduler_access_detected=False memory_write_detected=False approval_write_detected=False release_write_detected=False source_write_detected=False live_wiring_detected=False policy_count=41 policies_passed=True execution_trial_passed=True release_blocking=True review_only=False operator_approved_sandbox_execution=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=True executes_probe_files=True writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v885.0 sandbox probe execution result review and promotion readiness CLI tokens: sandbox-probe-execution-result-review-and-promotion-readiness-v1 --sandbox-probe-execution-result-review-and-promotion-readiness build_sandbox_probe_execution_result_review_and_promotion_readiness sandbox_probe_execution_result_review_and_promotion_readiness_text sandbox_probe_execution_result_review_and_promotion_readiness=True execution_trial_prerequisite_passed=True sandbox_probe_file_count=3 probe_execution_count=3 probe_execution_pass_count=3 probe_execution_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 execution_results_reviewed=True execution_results_clean=True promotion_candidate_count=3 promotion_blocker_count=0 promotion_readiness_passed=True live_integration_planned=False live_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False autonomy_expanded=False release_blocking=True review_only=True protected_systems_require_operator_approval=True

# v890.0 live probe promotion plan review CLI tokens: live-probe-promotion-plan-review-v1 --live-probe-promotion-plan-review build_live_probe_promotion_plan_review live_probe_promotion_plan_review_text live_probe_promotion_plan_review=True promotion_readiness_prerequisite_passed=True sandbox_probe_file_count=3 promotion_candidate_count=3 promotion_blocker_count=0 promotion_plan_created=True planned_live_probe_count=3 planned_smoke_registration_count=3 planned_dashboard_wiring_count=0 planned_api_wiring_count=0 planned_cli_wiring_count=0 source_files_to_modify_count=6 operator_approval_required=True single_use_approval_required=True approval_burnout_required=True rollback_plan_available=True live_integration_applied=False live_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False autonomy_expanded=False policy_count=44 policies_passed=True release_blocking=True review_only=True protected_systems_require_operator_approval=True

# v895.0 operator-approved live probe registration trial CLI tokens: operator-approved-live-probe-registration-trial-v1 --operator-approved-live-probe-registration-trial build_operator_approved_live_probe_registration_trial operator_approved_live_probe_registration_trial_text operator_approved_live_probe_registration_trial=True registered_live_probe_count=3 live_smoke_registration_applied=True dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False probe_execution_during_registration=False registration_trial_passed=True review_only=False operator_approved_live_registration=True expands_autonomy=False protected_systems_require_operator_approval=True

# v900.0 live registered probe verification and structural hardening review CLI tokens: live-registered-probe-verification-and-structural-hardening-review-v1 --live-registered-probe-verification-and-structural-hardening-review build_live_registered_probe_verification_and_structural_hardening_review live_registered_probe_verification_and_structural_hardening_review_text live_probe_registration_prerequisite_passed=True registered_live_probe_count=3 live_probe_execution_count=3 live_probe_pass_count=3 live_probe_fail_count=0 rollback_plan_available=True runtime_registry_issue_detected=True structural_hardening_plan_created=True live_registered_probe_verification_passed=True review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v906.0 v905 baseline verification and manifest version semantics prep CLI tokens: v905-baseline-verification-and-manifest-version-semantics-prep-v1 --v905-baseline-verification-and-manifest-version-semantics-prep build_v905_baseline_verification_and_manifest_version_semantics_prep v905_baseline_verification_and_manifest_version_semantics_prep_text v905_containment_baseline_passed=True generated_probe_harness_present=True manifest_semantic_mismatch_count manifest_schema_migration_applied=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v907.0 manifest version semantics split CLI tokens: manifest-version-semantics-split-v1 --manifest-version-semantics-split build_manifest_version_semantics_split_review manifest_version_semantics_split_review_text surface_origin_version manifest_representation_version last_verified_for_version legacy_version_field_retained_for_compatibility=True manifest_version_schema_split_applied=True historical_origin_mismatch_allowed=True review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v908.0 manifest validation normalization CLI tokens: manifest-validation-normalization-v1 --manifest-validation-normalization build_manifest_validation_normalization_review manifest_validation_normalization_review_text build_manifest_validation_normalization_summary legacy_version_field_validation_mode=compatibility_only_not_current_state historical_origin_versions_allowed=True current_state_version_source=manifest_representation_version_and_last_verified_for_version legacy_version_is_current_state_source=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v909.0 source package privacy deep scan CLI tokens: source-package-privacy-deep-scan-v1 --source-package-privacy-deep-scan build_source_package_privacy_deep_scan_review source_package_privacy_deep_scan_review_text privacy_deep_scan_summary private_content_findings_for_items content_scans_allowlisted_data=True blocks_private_self_state_content=True data/self_model.json source_metadata_allowed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v910.0 metadata/current marker gate reconciliation CLI tokens: metadata-and-current-marker-gate-reconciliation-v1 --metadata-and-current-marker-gate-reconciliation build_metadata_and_current_marker_gate_reconciliation_review metadata_and_current_marker_gate_reconciliation_review_text current_marker_source_count current_marker_checked_count stale_current_marker_count historical_reference_allowed=True metadata_current_state_aligned=True release_history_current_entry_aligned=True smoke_expectation_current_aligned=True review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v911.0 release gate stale assertion truth repair CLI tokens: release-gate-stale-assertion-truth-repair-v1 --release-gate-stale-assertion-truth-repair build_release_gate_stale_assertion_truth_repair_review release_gate_stale_assertion_truth_repair_review_text executable_smoke_assertion_audit EXPECTED_CURRENT_VERSION metadata_docs_audit_dynamic_current=True network_access_not_measured=True external_filesystem_writes_not_measured=True review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v912.0 install-release segment blocker classification CLI tokens: install-release-segment-blocker-classification-v1 --install-release-segment-blocker-classification build_install_release_segment_blocker_classification_review install_release_segment_blocker_classification_review_text currently_passing valid_historical_blocked_state slow_or_hanging_check superseded_check marks_install_release_clean=False executes_full_install_release_segment=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v913.0-v915.0 CLI tokens: release-archive-and-recovery-gate-boundedness-repair-v1 --release-archive-and-recovery-gate-boundedness-repair build_release_archive_and_recovery_gate_boundedness_repair_review release_archive_and_recovery_gate_boundedness_repair_review_text install-release-segment-evidence-summary-gate-v1 --install-release-segment-evidence-summary-gate build_install_release_segment_evidence_summary_gate_review install_release_segment_evidence_summary_gate_review_text manifest-driven-surface-generation-prep-v1 --manifest-driven-surface-generation-prep build_manifest_driven_surface_generation_prep_review manifest_driven_surface_generation_prep_review_text generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v916.0-v920.0 CLI tokens: manifest-review-packet-schema-v1 --manifest-review-packet-schema build_manifest_review_packet_schema_review manifest_review_packet_schema_review_text dashboard-surface-preview-generator-v1 --dashboard-surface-preview-generator build_dashboard_surface_preview_generator_review dashboard_surface_preview_generator_review_text cli-api-surface-preview-generator-v1 --cli-api-surface-preview-generator build_cli_api_surface_preview_generator_review cli_api_surface_preview_generator_review_text smoke-surface-preview-generator-v1 --smoke-surface-preview-generator build_smoke_surface_preview_generator_review smoke_surface_preview_generator_review_text generated-preview-parity-report-v1 --generated-preview-parity-report build_generated_preview_parity_report_review generated_preview_parity_report_review_text generates_surfaces=False generated_wiring_activated=False generated_preview_authoritative=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v921.0-v925.0 CLI tokens: low-risk-surface-selection-gate-v1 --low-risk-surface-selection-gate build_low_risk_surface_selection_gate_review low_risk_surface_selection_gate_review_text generated-dashboard-preview-exact-match-gate-v1 --generated-dashboard-preview-exact-match-gate build_generated_dashboard_preview_exact_match_gate_review generated_dashboard_preview_exact_match_gate_review_text generated-cli-api-preview-exact-match-gate-v1 --generated-cli-api-preview-exact-match-gate build_generated_cli_api_preview_exact_match_gate_review generated_cli_api_preview_exact_match_gate_review_text generated-smoke-preview-exact-match-gate-v1 --generated-smoke-preview-exact-match-gate build_generated_smoke_preview_exact_match_gate_review generated_smoke_preview_exact_match_gate_review_text single-surface-generated-parity-closure-v1 --single-surface-generated-parity-closure build_single_surface_generated_parity_closure_review single_surface_generated_parity_closure_review_text selected_surface_id=v916-manifest-review-packet-schema dashboard_parity=exact cli_parity=exact api_parity=exact_not_exposed_review_only smoke_parity=exact generated_preview_authoritative=False generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v926.0-v930.0 CLI tokens: multi-surface-selection-gate-v1 --multi-surface-selection-gate build_multi_surface_selection_gate_review multi_surface_selection_gate_review_text multi-surface-dashboard-preview-parity-v1 --multi-surface-dashboard-preview-parity build_multi_surface_dashboard_preview_parity_review multi_surface_dashboard_preview_parity_review_text multi-surface-cli-api-preview-parity-v1 --multi-surface-cli-api-preview-parity build_multi_surface_cli_api_preview_parity_review multi_surface_cli_api_preview_parity_review_text multi-surface-smoke-preview-parity-v1 --multi-surface-smoke-preview-parity build_multi_surface_smoke_preview_parity_review multi_surface_smoke_preview_parity_review_text multi-surface-generated-parity-batch-closure-v1 --multi-surface-generated-parity-batch-closure build_multi_surface_generated_parity_batch_closure_review multi_surface_generated_parity_batch_closure_review_text selected_surface_count=5 dashboard_parity=exact_for_all_selected cli_parity=exact_for_all_selected api_parity=exact_not_exposed_review_only_for_all_selected smoke_parity=exact_for_all_selected stale_marker_parity=exact_current_version_source_for_all_selected generated_preview_authoritative=False generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v931.0-v935.0 CLI tokens: generated-scaffold-sandbox-output-schema-v1 --generated-scaffold-sandbox-output-schema build_generated_scaffold_sandbox_output_schema_review generated_scaffold_sandbox_output_schema_review_text generated-scaffold-sandbox-artifact-preview-v1 --generated-scaffold-sandbox-artifact-preview build_generated_scaffold_sandbox_artifact_preview_review generated_scaffold_sandbox_artifact_preview_review_text generated-scaffold-hash-ledger-v1 --generated-scaffold-hash-ledger build_generated_scaffold_hash_ledger_review generated_scaffold_hash_ledger_review_text generated-scaffold-sandbox-parity-comparison-v1 --generated-scaffold-sandbox-parity-comparison build_generated_scaffold_sandbox_parity_comparison_review generated_scaffold_sandbox_parity_comparison_review_text generated-scaffold-sandbox-output-closure-v1 --generated-scaffold-sandbox-output-closure build_generated_scaffold_sandbox_output_closure_review generated_scaffold_sandbox_output_closure_review_text sandbox_artifact_count=5 hash_count=5 comparison_count=5 runtime_writes_sandbox_files=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v936.0-v940.0 CLI tokens: generated-scaffold-wrapper-mapping-schema-v1 --generated-scaffold-wrapper-mapping-schema build_generated_scaffold_wrapper_mapping_schema_review generated_scaffold_wrapper_mapping_schema_review_text dashboard-compatibility-wrapper-preview-v1 --dashboard-compatibility-wrapper-preview build_dashboard_compatibility_wrapper_preview_review dashboard_compatibility_wrapper_preview_review_text cli-api-compatibility-wrapper-preview-v1 --cli-api-compatibility-wrapper-preview build_cli_api_compatibility_wrapper_preview_review cli_api_compatibility_wrapper_preview_review_text smoke-compatibility-wrapper-preview-v1 --smoke-compatibility-wrapper-preview build_smoke_compatibility_wrapper_preview_review smoke_compatibility_wrapper_preview_review_text generated-scaffold-wrapper-prep-closure-v1 --generated-scaffold-wrapper-prep-closure build_generated_scaffold_wrapper_prep_closure_review generated_scaffold_wrapper_prep_closure_review_text wrapper_artifact_count=5 wrapper_hash_count=5 wrapper_schema_field_count=16 runtime_writes_wrapper_files=False manual_code_replaced=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v941.0-v950.0 CLI tokens: giant-file-extraction-inventory-v1 --giant-file-extraction-inventory build_giant_file_extraction_inventory_review giant_file_extraction_inventory_review_text self-development-cycle-extraction-map-v1 --self-development-cycle-extraction-map build_self_development_cycle_extraction_map_review self_development_cycle_extraction_map_review_text self-maintenance-builder-text-renderer-extraction-map-v1 --self-maintenance-builder-text-renderer-extraction-map build_self_maintenance_builder_text_renderer_extraction_map_review self_maintenance_builder_text_renderer_extraction_map_review_text dashboard-route-renderer-extraction-map-v1 --dashboard-route-renderer-extraction-map build_dashboard_route_renderer_extraction_map_review dashboard_route_renderer_extraction_map_review_text cli-api-dispatch-extraction-map-v1 --cli-api-dispatch-extraction-map build_cli_api_dispatch_extraction_map_review cli_api_dispatch_extraction_map_review_text smoke-registry-extraction-map-v1 --smoke-registry-extraction-map build_smoke_registry_extraction_map_review smoke_registry_extraction_map_review_text compatibility-wrapper-risk-ledger-v1 --compatibility-wrapper-risk-ledger build_compatibility_wrapper_risk_ledger_review compatibility_wrapper_risk_ledger_review_text extraction-order-proposal-v1 --extraction-order-proposal build_extraction_order_proposal_review extraction_order_proposal_review_text extraction-rollback-evidence-plan-v1 --extraction-rollback-evidence-plan build_extraction_rollback_evidence_plan_review extraction_rollback_evidence_plan_review_text giant-file-compatibility-extraction-prep-closure-v1 --giant-file-compatibility-extraction-prep-closure build_giant_file_compatibility_extraction_prep_closure_review giant_file_compatibility_extraction_prep_closure_review_text candidate_count low_risk_extraction_count protected_manual_count recommended_first_extraction_module rollback_plan_status moves_live_code=False splits_files=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v951.0-v960.0 CLI tokens: extraction-candidate-lock-gate-v1 --extraction-candidate-lock-gate build_extraction_candidate_lock_gate_review extraction_candidate_lock_gate_review_text pre-extraction-function-inventory-v1 --pre-extraction-function-inventory build_pre_extraction_function_inventory_review pre_extraction_function_inventory_review_text generated-preview-review-module-extraction-v1 --generated-preview-review-module-extraction build_generated_preview_review_module_extraction_review generated_preview_review_module_extraction_review_text compatibility-import-wrapper-gate-v1 --compatibility-import-wrapper-gate build_compatibility_import_wrapper_gate_review compatibility_import_wrapper_gate_review_text dashboard-cli-api-parity-after-extraction-v1 --dashboard-cli-api-parity-after-extraction build_dashboard_cli_api_parity_after_extraction_review dashboard_cli_api_parity_after_extraction_review_text smoke-registry-parity-after-extraction-v1 --smoke-registry-parity-after-extraction build_smoke_registry_parity_after_extraction_review smoke_registry_parity_after_extraction_review_text stale-version-and-metadata-post-extraction-gate-v1 --stale-version-and-metadata-post-extraction-gate build_stale_version_and_metadata_post_extraction_gate_review stale_version_and_metadata_post_extraction_gate_review_text rollback-path-verification-v1 --rollback-path-verification build_rollback_path_verification_review rollback_path_verification_review_text extraction-release-evidence-packet-v1 --extraction-release-evidence-packet build_extraction_release_evidence_packet_review extraction_release_evidence_packet_review_text first-compatibility-extraction-closure-v1 --first-compatibility-extraction-closure build_first_compatibility_extraction_closure_review first_compatibility_extraction_closure_review_text extracted_module=conscious_agent/generated_surface_preview_reviews.py extracted_cluster=v916-v920 wrappers_preserved=True dashboard_parity=pass cli_api_parity=pass smoke_parity=pass rollback_path=documented generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v961.0-v970.0 CLI tokens: second-extraction-candidate-selection-gate-v1 --second-extraction-candidate-selection-gate build_second_extraction_candidate_selection_gate_review second_extraction_candidate_selection_gate_review_text second-pre-extraction-function-inventory-v1 --second-pre-extraction-function-inventory build_second_pre_extraction_function_inventory_review second_pre_extraction_function_inventory_review_text generated-scaffold-review-packet-extraction-v1 --generated-scaffold-review-packet-extraction build_generated_scaffold_review_packet_extraction_review generated_scaffold_review_packet_extraction_review_text second-compatibility-wrapper-gate-v1 --second-compatibility-wrapper-gate build_second_compatibility_wrapper_gate_review second_compatibility_wrapper_gate_review_text second-extraction-surface-parity-gate-v1 --second-extraction-surface-parity-gate build_second_extraction_surface_parity_gate_review second_extraction_surface_parity_gate_review_text smoke-registry-data-model-prep-v1 --smoke-registry-data-model-prep build_smoke_registry_data_model_prep_review smoke_registry_data_model_prep_review_text smoke-registry-static-inventory-v1 --smoke-registry-static-inventory build_smoke_registry_static_inventory_review smoke_registry_static_inventory_review_text smoke-registry-migration-risk-ledger-v1 --smoke-registry-migration-risk-ledger build_smoke_registry_migration_risk_ledger_review smoke_registry_migration_risk_ledger_review_text smoke-registry-rollback-plan-v1 --smoke-registry-rollback-plan build_smoke_registry_rollback_plan_review smoke_registry_rollback_plan_review_text second-extraction-and-smoke-registry-prep-closure-v1 --second-extraction-and-smoke-registry-prep-closure build_second_extraction_and_smoke_registry_prep_closure_review second_extraction_and_smoke_registry_prep_closure_review_text second_extracted_module=conscious_agent/generated_scaffold_review_packets.py extracted_cluster=v931-v935 wrappers_preserved=True smoke_registry_model=prepared_only smoke_registry_behavior_changed=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v971.0-v980.0 CLI tokens: smoke-registry-pilot-selection-gate-v1 --smoke-registry-pilot-selection-gate build_smoke_registry_pilot_selection_gate_review smoke_registry_pilot_selection_gate_review_text smoke-registry-pilot-schema-v1 --smoke-registry-pilot-schema build_smoke_registry_pilot_schema_review smoke_registry_pilot_schema_review_text smoke-registry-pilot-data-table-v1 --smoke-registry-pilot-data-table build_smoke_registry_pilot_data_table_review smoke_registry_pilot_data_table_review_text smoke-registry-pilot-resolver-v1 --smoke-registry-pilot-resolver build_smoke_registry_pilot_resolver_review smoke_registry_pilot_resolver_review_text manual-vs-pilot-smoke-parity-gate-v1 --manual-vs-pilot-smoke-parity-gate build_manual_vs_pilot_smoke_parity_gate_review manual_vs_pilot_smoke_parity_gate_review_text pilot-json-shape-compatibility-gate-v1 --pilot-json-shape-compatibility-gate build_pilot_json_shape_compatibility_gate_review pilot_json_shape_compatibility_gate_review_text pilot-rollback-evidence-gate-v1 --pilot-rollback-evidence-gate build_pilot_rollback_evidence_gate_review pilot_rollback_evidence_gate_review_text smoke-registry-pilot-risk-review-v1 --smoke-registry-pilot-risk-review build_smoke_registry_pilot_risk_review smoke_registry_pilot_risk_review_text pilot-expansion-readiness-review-v1 --pilot-expansion-readiness-review build_pilot_expansion_readiness_review pilot_expansion_readiness_review_text smoke-registry-data-driven-pilot-closure-v1 --smoke-registry-data-driven-pilot-closure build_smoke_registry_data_driven_pilot_closure_review smoke_registry_data_driven_pilot_closure_review_text pilot_checks=5 pilot_table_exists=True manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v981.0-v990.0 CLI tokens: smoke-registry-execution-trial-readiness-gate-v1 --smoke-registry-execution-trial-readiness-gate build_smoke_registry_execution_trial_readiness_gate_review smoke_registry_execution_trial_readiness_gate_review_text data-driven-smoke-callable-execution-harness-v1 --data-driven-smoke-callable-execution-harness build_data_driven_smoke_callable_execution_harness_review data_driven_smoke_callable_execution_harness_review_text pilot-smoke-execution-result-packet-v1 --pilot-smoke-execution-result-packet build_pilot_smoke_execution_result_packet_review pilot_smoke_execution_result_packet_review_text manual-vs-data-driven-execution-parity-gate-v1 --manual-vs-data-driven-execution-parity-gate build_manual_vs_data_driven_execution_parity_gate_review manual_vs_data_driven_execution_parity_gate_review_text data-driven-smoke-json-output-preview-v1 --data-driven-smoke-json-output-preview build_data_driven_smoke_json_output_preview_review data_driven_smoke_json_output_preview_review_text data-driven-smoke-timeout-failure-semantics-v1 --data-driven-smoke-timeout-failure-semantics build_data_driven_smoke_timeout_failure_semantics_review data_driven_smoke_timeout_failure_semantics_review_text data-driven-smoke-manual-fallback-proof-v1 --data-driven-smoke-manual-fallback-proof build_data_driven_smoke_manual_fallback_proof_review data_driven_smoke_manual_fallback_proof_review_text data-driven-smoke-execution-risk-review-v1 --data-driven-smoke-execution-risk-review build_data_driven_smoke_execution_risk_review data_driven_smoke_execution_risk_review_text data-driven-smoke-expansion-readiness-v1 --data-driven-smoke-expansion-readiness build_data_driven_smoke_expansion_readiness_review data_driven_smoke_expansion_readiness_review_text smoke-registry-data-driven-execution-trial-closure-v1 --smoke-registry-data-driven-execution-trial-closure build_smoke_registry_data_driven_execution_trial_closure_review smoke_registry_data_driven_execution_trial_closure_review_text pilot_checks_executed=5 data_driven_execution=pass manual_parity=exact_for_all_selected manual_registry_replaced=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v991.0-v1000.0 CLI tokens: fallback-migration-readiness-gate-v1 --fallback-migration-readiness-gate build_fallback_migration_readiness_gate_review fallback_migration_readiness_gate_review_text data-driven-first-pilot-dispatch-preview-v1 --data-driven-first-pilot-dispatch-preview build_data_driven_first_pilot_dispatch_preview_review data_driven_first_pilot_dispatch_preview_review_text pilot-fallback-dispatch-trial-v1 --pilot-fallback-dispatch-trial build_pilot_fallback_dispatch_trial_review pilot_fallback_dispatch_trial_review_text pilot-fallback-result-ledger-v1 --pilot-fallback-result-ledger build_pilot_fallback_result_ledger_review pilot_fallback_result_ledger_review_text json-output-stability-gate-v1 --json-output-stability-gate build_json_output_stability_gate_review json_output_stability_gate_review_text fast-install-release-isolation-gate-v1 --fast-install-release-isolation-gate build_fast_install_release_isolation_gate_review fast_install_release_isolation_gate_review_text manual-fallback-removal-resistance-gate-v1 --manual-fallback-removal-resistance-gate build_manual_fallback_removal_resistance_gate_review manual_fallback_removal_resistance_gate_review_text pilot-migration-risk-review-v1 --pilot-migration-risk-review build_pilot_migration_risk_review pilot_migration_risk_review_text v1000-milestone-readiness-review-v1 --v1000-milestone-readiness-review build_v1000_milestone_readiness_review v1000_milestone_readiness_review_text smoke-registry-fallback-migration-pilot-closure-v1 --smoke-registry-fallback-migration-pilot-closure build_smoke_registry_fallback_migration_pilot_closure_review smoke_registry_fallback_migration_pilot_closure_review_text pilot_checks=5 data_driven_first_dispatch=active_for_pilot_trial_path_only manual_fallback=preserved registry_globally_replaced=False manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v1002.0 CLI tokens: install-release-blocker-ledger-refresh-v1 --install-release-blocker-ledger-refresh build_install_release_blocker_ledger_refresh_review install_release_blocker_ledger_refresh_review_text full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True
# v1010.0 CLI tokens: install-release-timeout-harness-repair-v1 --install-release-timeout-harness-repair build_install_release_timeout_harness_repair_review install_release_timeout_harness_repair_review_text timeout_rows_reviewed=7 timeout_rows_protected=7 timeout_harness_repaired=True full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v1010.0 CLI tokens: install-release-timeout-row-bounded-retest-v1 --install-release-timeout-row-bounded-retest build_install_release_timeout_row_bounded_retest_review install_release_timeout_row_bounded_retest_review_text timeout_rows_total=7 timeout_rows_retested=7 timeout_rows_reclassified=7 still_timeout full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v1010.0 CLI tokens: install-release-fixture-smoke-split-pilot-v1 --install-release-fixture-smoke-split-pilot build_install_release_fixture_smoke_split_pilot_review install_release_fixture_smoke_split_pilot_review_text timeout_rows_total=7 timeout_rows_planned=7 fixture_targets_total=35 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v1010.0 CLI tokens: install-release-fixture-smoke-split-pilot-v1 --install-release-fixture-smoke-split-pilot build_install_release_fixture_smoke_split_pilot_review install_release_fixture_smoke_split_pilot_review_text fixture_family_selected=archive_continuity_index parent_timeout_row=release-archive-retrieval-and-continuity-index-v1 fixture_targets_in_family=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v1010.0 CLI tokens: release-archive-fixture-split-expansion-v1 --release-archive-fixture-split-expansion build_release_archive_fixture_split_expansion_review release_archive_fixture_split_expansion_review_text expanded_fixture_families=archive_search_handoff,archive_export_closure expanded_family_count=2 split_fixture_targets_total=10 split_fixture_pass_count=10 parent_rows_still_timeout=True total_split_families_including_v1006=3 total_split_fixture_targets_including_v1006=15 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 CLI tokens: supervised-blocker-semantics-repair-v1 --supervised-blocker-semantics-repair build_supervised_blocker_semantics_repair_review supervised_blocker_semantics_repair_review_text supervised_blocker_rows_reviewed=6 supervised_blocker_semantics_repaired=6 operator_gated_rows=6 fixture_required_rows=1 release_authorizing_blockers_remaining=0 timeout_rows_remaining=7 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 CLI tokens: install-release-segment-cleanliness-gate-v1 --install-release-segment-cleanliness-gate build_install_release_segment_cleanliness_gate_review install_release_segment_cleanliness_gate_review_text install_release_total_checks=30 install_release_passing_rows=17 operator_gated_semantics_rows=6 timeout_rows_still_blocking=7 split_fixture_families_passing=3 split_fixture_targets_passing=15 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1010.0 CLI tokens: post-v1000-defect-closure-audit-and-phase-zero-boundary-v1 --post-v1000-defect-closure-audit-and-phase-zero-boundary build_post_v1000_defect_closure_phase_zero_boundary_review post_v1000_defect_closure_phase_zero_boundary_review_text original_v1000_findings_total=8 fixed_findings=5 repaired_and_monitored=1 partially_mitigated=2 timeout_rows_still_blocking=7 full_install_release_clean=False phase_zero_enabled=False observation_only_autonomy_enabled=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1011.0 CLI tokens: install-release-timeout-parent-row-replacement-pilot-v1 --install-release-timeout-parent-row-replacement-pilot build_install_release_timeout_parent_replacement_pilot_review install_release_timeout_parent_replacement_pilot_review_text replacement_parent_row=release-archive-retrieval-and-continuity-index-v1 replacement_fixture_family=archive_continuity_index replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True timeout_rows_before_replacement=7 replaced_parent_rows=1 timeout_rows_remaining_after_replacement=6 active_cleanliness_blockers_after_replacement=6 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1013.0 CLI tokens: install-release-parent-replacement-expansion-v1 --install-release-parent-replacement-expansion build_install_release_parent_replacement_expansion_review install_release_parent_replacement_expansion_review_text expansion_replacement_families=archive_search_handoff,archive_export_closure expansion_replaced_parent_rows=2 total_replaced_parent_rows_after_expansion=3 replacement_fixture_targets_after_expansion=15 parent_rows_original_timeout_preserved=True parent_rows_marked_pass=False timeout_rows_before_replacement=7 timeout_rows_remaining_after_expansion=4 active_cleanliness_blockers_after_expansion=4 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1013.0 CLI tokens: remaining-timeout-parent-fixture-selection-v1 --remaining-timeout-parent-fixture-selection build_remaining_timeout_parent_fixture_selection_review remaining_timeout_parent_fixture_selection_review_text selected_parent_row=recovery-drill-and-release-closure-v1 selected_fixture_family=recovery_closure selected_fixture_targets=5 remaining_timeout_parent_rows_before_selection=4 selected_parent_original_timeout_preserved=True selected_parent_marked_pass=False projected_timeout_blockers_after_future_replacement=3 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1015.0 CLI tokens: recovery-closure-fixture-split-smoke-v1 --recovery-closure-fixture-split-smoke build_recovery_closure_fixture_split_smoke_review recovery_closure_fixture_split_smoke_review_text fixture_family_selected=recovery_closure parent_timeout_row=recovery-drill-and-release-closure-v1 fixture_targets_in_family=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False projected_timeout_blockers_after_future_replacement=3 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1015.0 CLI tokens: recovery-closure-parent-replacement-overlay-v1 --recovery-closure-parent-replacement-overlay build_recovery_closure_parent_replacement_overlay_review recovery_closure_parent_replacement_overlay_review_text replacement_parent_row=recovery-drill-and-release-closure-v1 replacement_fixture_family=recovery_closure replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=3 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=4 replacement_fixture_targets_after_overlay=20 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=3 active_cleanliness_blockers_after_overlay=3 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1016.0 CLI tokens: remaining-timeout-parent-fixture-split-expansion-v1 --remaining-timeout-parent-fixture-split-expansion build_remaining_timeout_parent_fixture_split_expansion_review remaining_timeout_parent_fixture_split_expansion_review_text selected_parent_row=release-decision-and-archive-ledger-v1 selected_fixture_family=decision_archive_ledger selected_fixture_targets=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False already_replaced_parent_rows=4 remaining_timeout_parent_rows_before_split=3 projected_timeout_blockers_after_future_replacement=2 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1017.0 CLI tokens: decision-archive-ledger-parent-replacement-overlay-v1 --decision-archive-ledger-parent-replacement-overlay build_decision_archive_ledger_parent_replacement_overlay_review decision_archive_ledger_parent_replacement_overlay_review_text replacement_parent_row=release-decision-and-archive-ledger-v1 replacement_fixture_family=decision_archive_ledger replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=4 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=5 replacement_fixture_targets_after_overlay=25 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=2 active_cleanliness_blockers_after_overlay=2 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1018.0 CLI tokens: candidate-handoff-fixture-split-smoke-v1 --candidate-handoff-fixture-split-smoke build_candidate_handoff_fixture_split_smoke_review candidate_handoff_fixture_split_smoke_review_text selected_parent_row=release-candidate-integrity-and-operator-handoff-v1 selected_fixture_family=candidate_handoff selected_fixture_targets=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False already_replaced_parent_rows=5 remaining_timeout_parent_rows_before_split=2 projected_timeout_blockers_after_future_replacement=1 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
# v1019.0 CLI tokens: candidate-handoff-parent-replacement-overlay-v1 --candidate-handoff-parent-replacement-overlay build_candidate_handoff_parent_replacement_overlay_review candidate_handoff_parent_replacement_overlay_review_text replacement_parent_row=release-candidate-integrity-and-operator-handoff-v1 replacement_fixture_family=candidate_handoff replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=5 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=6 replacement_fixture_targets_after_overlay=30 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=1 active_cleanliness_blockers_after_overlay=1 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
# v1024.0 CLI tokens: final-timeout-parent-overlay-closure-v1 --final-timeout-parent-overlay-closure build_final_timeout_parent_overlay_closure_review final_timeout_parent_overlay_closure_review_text replacement_parent_row=fast-install-release-isolation-gate-v1 replacement_fixture_family=fast_install_release_isolation replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=6 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=7 replacement_fixture_targets_after_overlay=35 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=0 active_timeout_parent_blockers_after_overlay=0 timeout_parent_overlay_clean=True intentional_supervised_blockers_remaining=6 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
