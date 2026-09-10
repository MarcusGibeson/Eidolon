from __future__ import annotations

from release_metadata import NEXT_RECOMMENDED_ARC as RELEASE_NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, RUNTIME_VERSION, RUNTIME_VERSION_TAG

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from source_project_metadata import load_source_project_metadata

CURRENT_VERSION_STALENESS_AUDIT_VERSION = RUNTIME_VERSION
CURRENT_VERSION = RUNTIME_VERSION
CURRENT_VERSION_TAG = RUNTIME_VERSION_TAG
CURRENT_MILESTONE = RUNTIME_MILESTONE
NEXT_RECOMMENDED_ARC = RELEASE_NEXT_RECOMMENDED_ARC
TARGETED_SMOKE = "registry-navigation-smoke-consolidation-v1"
STALE_AUDIT_ID = "v710_neural_console_visual_restoration_real_chat_affordance_repair"
SOURCE_OF_TRUTH_ID = "v546_current_version_source_of_truth_contract"
STALE_SCANNER_ID = "v547_stale_version_string_scanner"
MILESTONE_DRIFT_ID = "v548_stale_milestone_title_drift_audit"
POST_PATCH_VERIFICATION_ID = "v549_post_live_patch_verification_prep"
FINAL_AUDIT_ID = "v710_neural_console_restoration_chat_affordance_board"
CURRENT_SYMBOL_AUDIT_ID = "v710_expanded_current_symbol_and_surface_marker_staleness_audit"

EXPECTED_TITLE = CURRENT_MILESTONE.removeprefix(f"{CURRENT_VERSION_TAG} ").strip()
PREVIOUS_CURRENT_TITLE = "Verification Truth and Evidence Attestation Hotfix"
CURRENT_STATE_FILES: tuple[str, ...] = (
    "conscious_agent/registry_navigation_smoke_consolidation.py",
    "conscious_agent/desktop_setup_helper.py",
    "conscious_agent/desktop_onboarding_wizard.py",
    "conscious_agent/ai_patch_assistance.py",
    "conscious_agent/validated_ai_patch_loop.py",
    "conscious_agent/self_maintenance_modular_extraction.py",
    "conscious_agent/self_maintenance_shadow_cleanup.py",
    "conscious_agent/self_maintenance_version_package_gates.py",
    "conscious_agent/self_maintenance_surface_gates.py",
    "conscious_agent/self_maintenance_governance_gates.py",
    "README_NEXT_STEPS.md",
    "data/settings.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
    "conscious_agent/self_maintenance.py",
    "conscious_agent/current_version_staleness_audit.py",
    "conscious_agent/post_live_patch_verification_rollback_trial.py",
    "conscious_agent/recovery_drill_release_closure.py",
    "conscious_agent/release_candidate_operator_handoff.py",
    "conscious_agent/release_decision_archive_ledger.py",
    "conscious_agent/release_archive_continuity_index.py",
    "conscious_agent/release_archive_search_handoff.py",
    "conscious_agent/release_archive_export_closure.py",
    "conscious_agent/release_archive_import_closure_recall.py",
    "conscious_agent/imported_archive_conflict_reconciliation.py",
    "conscious_agent/archive_reconciliation_decision_ledger.py",
    "conscious_agent/current_state_integrity_staleness_hardening.py",
    "conscious_agent/archive_reconciliation_application_prep.py",
    "conscious_agent/operator_command_center_ui_consolidation.py",
    "conscious_agent/dashboard_workflow_simplification.py",
    "conscious_agent/operator_action_semantics_ux.py",
    "conscious_agent/review_packet_evidence_ux.py",
    "conscious_agent/dashboard_search_surface_discovery.py",
    "conscious_agent/operator_decision_approval_ux.py",
    "conscious_agent/operator_receipt_timeline_audit_ux.py",
    "conscious_agent/operator_session_continuity_resume_ux.py",
    "conscious_agent/operator_guided_review_wizard_ux.py",
    "conscious_agent/project_metadata_active_context_repair.py",
    "conscious_agent/legacy_smoke_segmentation_repair.py",
    "conscious_agent/manifest_driven_surface_registry.py",
    "conscious_agent/dashboard_renderer_component_extraction.py",
    "conscious_agent/neural_command_deck_dashboard_redesign.py",
    "conscious_agent/neural_command_deck_interaction_refinement.py",
    "conscious_agent/autonomy_phase_zero_readiness_harness.py",
    "tools/smoke_check.py",
    "tools/smoke_result_formatting.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/dashboard_route_registry.py",
    "conscious_agent/dashboard_renderer_metadata.py",
    "conscious_agent/dashboard_dispatcher_parity.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v12.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v12.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v13.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v13.py",
    "conscious_agent/dashboard_dispatcher_proof_surface_consolidation_prep_v1.py",
    "conscious_agent/dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1.py",
    "conscious_agent/dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1.py",
    "conscious_agent/dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1.py",
    "conscious_agent/dashboard_dispatcher_branch_prep.py",
    "conscious_agent/dashboard_dispatcher_branch_trial.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_trial.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py",
    "conscious_agent/eidolon_v1073_source_review_checkpoint.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_hardening.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v3.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v3.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v2.py",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v2.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v2.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v2.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v3.py",
    "conscious_agent/dashboard_dispatcher_batch_strategy_checkpoint.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v2.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v3.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v3.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v4.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v4.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v4.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v5.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v5.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v5.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v6.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v6.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v6.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v7.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v7.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v7.py",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v8.py",
    "conscious_agent/dashboard_route_probe.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/smoke_segment_registry.py",
    "conscious_agent/install_release_blocker_ledger.py",
    "conscious_agent/install_release_fixture_decomposition.py",
    "conscious_agent/install_release_fixture_smoke_split.py",
    "conscious_agent/release_archive_fixture_split_expansion.py",
    "conscious_agent/supervised_blocker_semantics_repair.py",
    "conscious_agent/install_release_segment_cleanliness_gate.py",
    "conscious_agent/post_v1000_defect_closure_phase_zero_boundary.py",
    "conscious_agent/install_release_timeout_parent_replacement.py",
    "conscious_agent/install_release_parent_replacement_expansion.py",
    "conscious_agent/remaining_timeout_parent_fixture_selection.py",
    "conscious_agent/recovery_closure_fixture_split_smoke.py",
    "conscious_agent/recovery_closure_parent_replacement_overlay.py",
    "conscious_agent/remaining_timeout_parent_fixture_split_expansion.py",
    "conscious_agent/decision_archive_ledger_parent_replacement_overlay.py",
    "conscious_agent/final_timeout_parent_overlay_closure.py",
    "conscious_agent/candidate_handoff_parent_replacement_overlay.py",
    "conscious_agent/candidate_handoff_fixture_split_smoke.py",
    "conscious_agent/documentation_continuity_header.py",
    "conscious_agent/operator_observation_prep.py",
    "conscious_agent/observation_ledger_boundary.py",
    "conscious_agent/observation_proposal_queue.py",
    "conscious_agent/sandbox_autonomy_boundary.py",
    "conscious_agent/autonomy_readiness_review_board.py",
    "conscious_agent/manual_observation_to_sandbox_bridge.py",
    "conscious_agent/sandbox_execution_approval_gate.py",
    "conscious_agent/sandbox_execution_dry_run_receipt.py",
    "conscious_agent/first_sandbox_execution_trial.py",
    "conscious_agent/sandbox_execution_runner.py",
    "conscious_agent/sandbox_to_source_promotion_packet.py",
    "conscious_agent/narrow_live_patch_promotion_gate.py",
    "conscious_agent/first_narrow_live_patch_application_trial.py",
    "conscious_agent/source_package_privacy_metadata_integrity.py",
    "conscious_agent/metadata_release_integrity.py",
    "conscious_agent/compile_timeout_historical_gate_harness.py",
    "conscious_agent/behavioral_dashboard_route_coverage.py",
    "conscious_agent/dashboard_shell_component_extraction.py",
    "conscious_agent/dashboard_shell_components.py",
    "conscious_agent/smoke_registry_sidecar_compatibility.py",
    "conscious_agent/smoke_registry_sidecar_expansion_route_manifest_prep.py",
    "conscious_agent/route_manifest_inventory_dashboard_parity.py",
    "conscious_agent/dashboard_route_behavioral_coverage_expansion.py",
    "conscious_agent/dashboard_route_manifest_renderer_reconciliation.py",
    "conscious_agent/dashboard_route_coverage_completion_dispatch_classification.py",
    "conscious_agent/smoke_registry_sidecar_parity_expansion.py",
    "conscious_agent/dashboard_route_behavioral_coverage_continuation.py",
    "conscious_agent/dashboard_deferred_route_harness_renderer_repair_prep.py",
    "conscious_agent/dashboard_slow_route_isolated_behavioral_coverage.py",
    "conscious_agent/dashboard_parameterized_route_harness_prep.py",
    "conscious_agent/dashboard_timeout_lane_classification_slow_renderer_decomposition_prep.py",
    "conscious_agent/dashboard_doctor_renderer_decomposition_slice.py",
    "conscious_agent/dashboard_doctor_deferred_diagnostic_api_parity.py",
    "conscious_agent/doctor_deferred_diagnostic_latency_budget_payload_shape.py",
    "conscious_agent/controlled_self_build_lightweight_preview_endpoint_prep.py",
    "conscious_agent/doctor_controlled_self_build_lightweight_link_migration.py",
    "conscious_agent/doctor_diagnostic_preview_cache_heavy_route_decoupling.py",
    "conscious_agent/doctor_diagnostic_cache_freshness_invalidation_review.py",
    "conscious_agent/doctor_diagnostic_cache_source_dependency_digest_verification.py",
    "conscious_agent/doctor_diagnostic_cache_digest_drift_classification.py",
    "conscious_agent/doctor_diagnostic_cache_contract_drift_fixture_expansion.py",
    "conscious_agent/doctor_diagnostic_cache_drift_severity_guidance.py",
    "conscious_agent/doctor_diagnostic_cache_severity_route_impact_matrix.py",
    "conscious_agent/dashboard_doctor_headroom_repair.py",
    "conscious_agent/installed_tree_cleanup_historical_verification_reconciliation.py",
    "conscious_agent/doctor_diagnostic_cache_impact_operator_action_ledger.py",
    "conscious_agent/doctor_deep_diagnostic_latency_budget_repair.py",
    "conscious_agent/dashboard_slow_route_cohort_repair.py",
    "conscious_agent/install_release_historical_blocker_reduction.py",
    "conscious_agent/source_surface_manifest_dispatch_candidate_preparation.py",
    "conscious_agent/manifest_generated_dispatch_parity_fixture_preview.py",
    "conscious_agent/manifest_generated_dispatch_fixture_harness_isolation.py",
    "conscious_agent/manifest_generated_dispatch_fixture_harness_dry_run_ledger.py",
    "conscious_agent/manifest_generated_dispatch_fixture_dry_run_execution_prep.py",
    "conscious_agent/manifest_generated_dispatch_fixture_first_isolated_dry_run_trial.py",
    "conscious_agent/manifest_generated_dispatch_fixture_trial_receipt_hardening.py",
    "conscious_agent/manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion.py",
    "conscious_agent/manifest_fixture_sandbox_adapter_contract.py",
    "conscious_agent/full_tree_mutation_snapshot.py",
    "conscious_agent/diagnostic_api_compatibility_restoration.py",
    "conscious_agent/release_tier_blocker_repair_batch_i.py",
    "conscious_agent/release_tier_blocker_repair_batch_ii.py",
    "conscious_agent/installed_tree_cleanup_enforcement.py",
    "conscious_agent/dashboard_shell_performance_stabilization.py",
    "conscious_agent/dashboard_full_navigation_get_side_effect_safety_gate.py",
    "conscious_agent/install_release_segment_runner_timeout_decomposition.py",
    "conscious_agent/manifest_fixture_receipt_consolidation.py",
    "conscious_agent/review_surface_shared.py",
    "conscious_agent/source_decomposition_batch_ii.py",
    "conscious_agent/sandbox_backend_adapter.py",
    "conscious_agent/dashboard_api_smoke_shared_utility_adoption.py",
    "conscious_agent/dashboard_review_component_extraction_pilot.py",
    "conscious_agent/smoke_check_shared.py",
    "conscious_agent/smoke_check_helper_extraction_pilot.py",
    "conscious_agent/api_preview_adapter_backfill.py",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/api_server_dispatch_route_table_extraction.py",
    "conscious_agent/api_server_dispatch_route_table_backfill.py",
    "conscious_agent/api_server_dispatch_route_table_safety_parity.py",
    "conscious_agent/audited_sandbox_backend_evidence_interface.py",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/api_server_dispatch_helper_extraction_pilot.py",
    "conscious_agent/api_server_dispatch_helper_backfill.py",
    "conscious_agent/memory_governance.py",
    "conscious_agent/live_patch_history_memory_candidates.py",
    "conscious_agent/memory_candidate_application_trial.py",
    "conscious_agent/stable_loop_audit.py",
    "conscious_agent/stable_loop_operator_notes.py",
    "conscious_agent/stable_loop_decision_report.py",
    "conscious_agent/stable_loop_followup_tasks.py",
    "conscious_agent/stable_loop_followup_lifecycle.py",
    "conscious_agent/stable_loop_followup_completion.py",
    "conscious_agent/stable_loop_guardrails.py",
    "conscious_agent/stabilization_checkpoint.py",
    "conscious_agent/operational_readiness.py",
    "conscious_agent/controlled_build_cycle.py",
    "conscious_agent/project_intelligence.py",
    "conscious_agent/workspace_execution.py",
    "conscious_agent/patch_drafting.py",
)

HISTORICAL_TEXT_FILES: tuple[str, ...] = (
    "README_RELEASE_HISTORY.md",
    "README_NEXT_STEPS.md",
    "conscious_agent/first_narrow_live_patch_application_trial.py",
    "conscious_agent/narrow_live_patch_promotion_gate.py",
    "conscious_agent/current_version_staleness_audit.py",
)

POST_PATCH_VERIFICATION_COMMANDS: tuple[str, ...] = (
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --check <targeted-check>",
    "python tools/smoke_check.py --tier fast",
    "python tools/smoke_check.py --segment install-dashboard",
    "python tools/smoke_check.py --segment install-release",
    "python conscious_agent/main.py --<target-cli-flag>",
    "GET /api/<target-api-route>/layer",
)

STALE_VERSION_BOUNDARIES: dict[str, bool] = {
    "historical_version_references_are_blocked": False,
    "current_state_stale_references_are_allowed": False,
    "matching_version_marker_alone_is_metadata_integrity": False,
    "verification_plan_exists_is_patch_applied": False,
    "stale_audit_pass_is_live_patch_permission": False,
    "stale_audit_pass_is_release_approval": False,
    "post_patch_verification_plan_executes_checks": False,
    "post_patch_verification_plan_applies_patch": False,
    "stale_audit_writes_source": False,
    "stale_audit_writes_memory": False,
    "stale_audit_creates_release": False,
    "stale_audit_executes_rollback": False,
    "stale_audit_invokes_models_by_default": False,
    "stale_audit_schedules_work": False,
    "stale_audit_reuses_approval": False,
    "stale_audit_continues_automatically": False,
    "stale_audit_expands_autonomy": False,
    "approval_required": True,
    "operator_review_required": True,
}

CURRENT_FIELD_NAMES = {
    "version",
    "settings_version",
    "last_updated_for",
    "current_milestone",
    "name",
    "root_version",
    "next_recommended_arc",
    "next_steps",
    "notes",
}

CURRENT_SYMBOL_NAMES = {"CURRENT_VERSION_TAG", "CURRENT_MILESTONE", "NEXT_RECOMMENDED_ARC", "WORKSPACE_CURRENT_MILESTONE", "WORKSPACE_NEXT_RECOMMENDED_ARC"}

CURRENT_SURFACE_VERSION_MARKERS: dict[str, str] = {
    "conscious_agent/dashboard_dispatcher_branch_backfill.py": "DASHBOARD_DISPATCHER_BRANCH_BACKFILL_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v3.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v2.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v3.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v2.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v3.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_helper_consolidation.py": "DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_VERSION",
    "conscious_agent/install_release_segment_runner_timeout_decomposition.py": "INSTALL_RELEASE_SEGMENT_RUNNER_TIMEOUT_DECOMPOSITION_VERSION",
    "conscious_agent/manifest_fixture_receipt_consolidation.py": "MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_VERSION",
    "conscious_agent/review_surface_shared.py": "REVIEW_SURFACE_SHARED_VERSION",
    "conscious_agent/sandbox_backend_adapter.py": "SANDBOX_BACKEND_ADAPTER_VERSION",
    "conscious_agent/registry_navigation_smoke_consolidation.py": "MODULE_VERSION",
    "conscious_agent/desktop_setup_helper.py": "SETUP_VERSION",
    "conscious_agent/desktop_onboarding_wizard.py": "ONBOARDING_VERSION",
    "conscious_agent/ai_patch_assistance.py": "AI_PATCH_ASSIST_VERSION",
    "conscious_agent/validated_ai_patch_loop.py": "VALIDATED_AI_PATCH_VERSION",
    "conscious_agent/self_maintenance_modular_extraction.py": "SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION",
    "conscious_agent/self_maintenance_shadow_cleanup.py": "SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION",
    "conscious_agent/self_maintenance_version_package_gates.py": "SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION",
    "conscious_agent/self_maintenance_surface_gates.py": "SELF_MAINTENANCE_SURFACE_GATES_VERSION",
    "conscious_agent/self_maintenance_governance_gates.py": "SELF_MAINTENANCE_GOVERNANCE_GATES_VERSION",
    "conscious_agent/self_maintenance.py": "SELF_MAINTENANCE_VERSION",
    "conscious_agent/dashboard.py": "DASHBOARD_VERSION",
    "conscious_agent/api_server.py": "API_VERSION",
    "conscious_agent/release_packaging.py": "RELEASE_PACKAGING_VERSION",
    "conscious_agent/release_zip_privacy_critical_gate_repair.py": "RELEASE_ZIP_PRIVACY_CRITICAL_GATE_REPAIR_VERSION",
    "conscious_agent/release_pipeline.py": "RELEASE_PIPELINE_VERSION",
    "conscious_agent/code_patch_release.py": "CODE_PATCH_RELEASE_VERSION",
    "conscious_agent/approval_release_workflow.py": "APPROVAL_RELEASE_VERSION",
    "conscious_agent/autonomy_phase_zero_readiness_harness.py": "AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION",
    "conscious_agent/release_installation.py": "RELEASE_INSTALLATION_VERSION",
    "conscious_agent/workspace_orchestration.py": "WORKSPACE_ORCHESTRATION_VERSION",
    "conscious_agent/runtime_registry.py": "RUNTIME_REGISTRY_VERSION",
    "conscious_agent/governance_reports.py": "GOVERNANCE_REPORTS_VERSION",
    "conscious_agent/package_integrity.py": "PACKAGE_INTEGRITY_VERSION",
    "conscious_agent/version_state.py": "VERSION_STATE_VERSION",
    "conscious_agent/surface_parity.py": "SURFACE_PARITY_VERSION",
    "conscious_agent/verification_planning.py": "VERIFICATION_PLANNING_VERSION",
    "conscious_agent/identity_expression.py": "IDENTITY_EXPRESSION_VERSION",
    "conscious_agent/self_maintenance_refactor_registry.py": "SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION",
    "conscious_agent/minimal_live_change_replay.py": "MINIMAL_LIVE_CHANGE_REPLAY_VERSION",
    "conscious_agent/current_state_integrity_staleness_hardening.py": "CURRENT_STATE_INTEGRITY_STALENESS_HARDENING_VERSION",
    "conscious_agent/source_surface_manifest.py": "SOURCE_SURFACE_MANIFEST_VERSION",
    "conscious_agent/source_package_privacy_metadata_integrity.py": "SOURCE_PACKAGE_PRIVACY_METADATA_INTEGRITY_VERSION",
    "conscious_agent/metadata_release_integrity.py": "METADATA_RELEASE_INTEGRITY_VERSION",
    "conscious_agent/smoke_segment_registry.py": "SMOKE_SEGMENT_REGISTRY_VERSION",
    "conscious_agent/smoke_registry_sidecar_parity_expansion.py": "SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_VERSION",
    "conscious_agent/dashboard_route_behavioral_coverage_continuation.py": "DASHBOARD_ROUTE_BEHAVIORAL_COVERAGE_CONTINUATION_VERSION",
    "conscious_agent/dashboard_deferred_route_harness_renderer_repair_prep.py": "DASHBOARD_DEFERRED_ROUTE_HARNESS_RENDERER_REPAIR_PREP_VERSION",
    "conscious_agent/dashboard_slow_route_isolated_behavioral_coverage.py": "DASHBOARD_SLOW_ROUTE_ISOLATED_BEHAVIORAL_COVERAGE_VERSION",
    "conscious_agent/dashboard_parameterized_route_harness_prep.py": "DASHBOARD_PARAMETERIZED_ROUTE_HARNESS_PREP_VERSION",
    "conscious_agent/dashboard_timeout_lane_classification_slow_renderer_decomposition_prep.py": "DASHBOARD_TIMEOUT_LANE_CLASSIFICATION_SLOW_RENDERER_DECOMPOSITION_PREP_VERSION",
    "conscious_agent/dashboard_doctor_renderer_decomposition_slice.py": "DASHBOARD_DOCTOR_RENDERER_DECOMPOSITION_SLICE_VERSION",
    "conscious_agent/dashboard_doctor_deferred_diagnostic_api_parity.py": "DASHBOARD_DOCTOR_DEFERRED_DIAGNOSTIC_API_PARITY_VERSION",
    "conscious_agent/doctor_deferred_diagnostic_latency_budget_payload_shape.py": "DOCTOR_DEFERRED_DIAGNOSTIC_LATENCY_BUDGET_PAYLOAD_SHAPE_VERSION",
    "conscious_agent/controlled_self_build_lightweight_preview_endpoint_prep.py": "CONTROLLED_SELF_BUILD_LIGHTWEIGHT_PREVIEW_ENDPOINT_PREP_VERSION",
    "conscious_agent/doctor_controlled_self_build_lightweight_link_migration.py": "DOCTOR_CONTROLLED_SELF_BUILD_LIGHTWEIGHT_LINK_MIGRATION_VERSION",
    "conscious_agent/doctor_diagnostic_preview_cache_heavy_route_decoupling.py": "DOCTOR_DIAGNOSTIC_PREVIEW_CACHE_HEAVY_ROUTE_DECOUPLING_VERSION",
    "conscious_agent/doctor_diagnostic_cache_freshness_invalidation_review.py": "DOCTOR_DIAGNOSTIC_CACHE_FRESHNESS_INVALIDATION_REVIEW_VERSION",
    "conscious_agent/doctor_diagnostic_cache_source_dependency_digest_verification.py": "DOCTOR_DIAGNOSTIC_CACHE_SOURCE_DEPENDENCY_DIGEST_VERIFICATION_VERSION",
    "conscious_agent/doctor_diagnostic_cache_digest_drift_classification.py": "DOCTOR_DIAGNOSTIC_CACHE_DIGEST_DRIFT_CLASSIFICATION_VERSION",
    "conscious_agent/doctor_diagnostic_cache_contract_drift_fixture_expansion.py": "DOCTOR_DIAGNOSTIC_CACHE_CONTRACT_DRIFT_FIXTURE_EXPANSION_VERSION",
    "conscious_agent/doctor_diagnostic_cache_drift_severity_guidance.py": "DOCTOR_DIAGNOSTIC_CACHE_DRIFT_SEVERITY_GUIDANCE_VERSION",
    "conscious_agent/doctor_diagnostic_cache_severity_route_impact_matrix.py": "DOCTOR_DIAGNOSTIC_CACHE_SEVERITY_ROUTE_IMPACT_MATRIX_VERSION",
    "conscious_agent/dashboard_doctor_headroom_repair.py": "DASHBOARD_DOCTOR_HEADROOM_REPAIR_VERSION",
    "conscious_agent/installed_tree_cleanup_historical_verification_reconciliation.py": "INSTALLED_TREE_CLEANUP_HISTORICAL_VERIFICATION_RECONCILIATION_VERSION",
    "conscious_agent/doctor_diagnostic_cache_impact_operator_action_ledger.py": "DOCTOR_DIAGNOSTIC_CACHE_IMPACT_OPERATOR_ACTION_LEDGER_VERSION",
    "conscious_agent/doctor_deep_diagnostic_latency_budget_repair.py": "DOCTOR_DEEP_DIAGNOSTIC_LATENCY_BUDGET_REPAIR_VERSION",
    "conscious_agent/dashboard_slow_route_cohort_repair.py": "DASHBOARD_SLOW_ROUTE_COHORT_REPAIR_VERSION",
    "conscious_agent/install_release_historical_blocker_reduction.py": "INSTALL_RELEASE_HISTORICAL_BLOCKER_REDUCTION_VERSION",
    "conscious_agent/source_surface_manifest_dispatch_candidate_preparation.py": "SOURCE_SURFACE_MANIFEST_DISPATCH_CANDIDATE_PREPARATION_VERSION",
    "conscious_agent/manifest_generated_dispatch_parity_fixture_preview.py": "MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_VERSION",
    "conscious_agent/manifest_generated_dispatch_fixture_harness_isolation.py": "MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_VERSION",
    "conscious_agent/manifest_generated_dispatch_fixture_harness_dry_run_ledger.py": "MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_VERSION",
    "conscious_agent/manifest_generated_dispatch_fixture_dry_run_execution_prep.py": "MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_VERSION",
    "conscious_agent/manifest_generated_dispatch_fixture_trial_receipt_hardening.py": "MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_VERSION",
    "conscious_agent/manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion.py": "MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_VERSION",
    "conscious_agent/manifest_fixture_sandbox_adapter_contract.py": "MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_VERSION",
    "conscious_agent/full_tree_mutation_snapshot.py": "FULL_TREE_MUTATION_SNAPSHOT_VERSION",
    "conscious_agent/diagnostic_api_compatibility_restoration.py": "DIAGNOSTIC_API_COMPATIBILITY_RESTORATION_VERSION",
    "conscious_agent/stable_loop_audit.py": "AUDIT_VERSION",
    "conscious_agent/stable_loop_operator_notes.py": "OPERATOR_NOTES_VERSION",
    "conscious_agent/stable_loop_decision_report.py": "DECISION_REPORT_VERSION",
    "conscious_agent/stable_loop_followup_tasks.py": "FOLLOWUP_TASK_VERSION",
    "conscious_agent/stable_loop_followup_lifecycle.py": "FOLLOWUP_LIFECYCLE_VERSION",
    "conscious_agent/stable_loop_followup_completion.py": "FOLLOWUP_COMPLETION_VERSION",
    "conscious_agent/stable_loop_guardrails.py": "STABLE_LOOP_GUARDRAIL_VERSION",
    "conscious_agent/stabilization_checkpoint.py": "STABILIZATION_CHECKPOINT_VERSION",
    "conscious_agent/operational_readiness.py": "OPERATIONAL_READINESS_VERSION",
    "conscious_agent/controlled_build_cycle.py": "CONTROLLED_BUILD_VERSION",
    "conscious_agent/project_intelligence.py": "PROJECT_INTELLIGENCE_VERSION",
    "conscious_agent/workspace_execution.py": "WORKSPACE_EXECUTION_VERSION",
    "conscious_agent/patch_drafting.py": "PATCH_DRAFTING_VERSION",
    "conscious_agent/release_tier_blocker_repair_batch_i.py": "RELEASE_TIER_BLOCKER_REPAIR_BATCH_I_VERSION",
    "conscious_agent/release_tier_blocker_repair_batch_ii.py": "RELEASE_TIER_BLOCKER_REPAIR_BATCH_II_VERSION",
    "conscious_agent/installed_tree_cleanup_enforcement.py": "INSTALLED_TREE_CLEANUP_ENFORCEMENT_VERSION",
    "conscious_agent/dashboard_shell_performance_stabilization.py": "DASHBOARD_SHELL_PERFORMANCE_STABILIZATION_VERSION",
    "conscious_agent/dashboard_full_navigation_get_side_effect_safety_gate.py": "FULL_NAVIGATION_GET_SIDE_EFFECT_SAFETY_GATE_VERSION",
    "conscious_agent/memory_governance.py": "MEMORY_GOVERNANCE_VERSION",
    "conscious_agent/live_patch_history_memory_candidates.py": "LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION",
    "conscious_agent/memory_candidate_application_trial.py": "MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION",
    "conscious_agent/smoke_check_shared.py": "SMOKE_CHECK_SHARED_VERSION",
    "tools/smoke_result_formatting.py": "SMOKE_RESULT_FORMATTING_VERSION",
    "tools/smoke_registry_metadata.py": "SMOKE_REGISTRY_METADATA_VERSION",
    "tools/smoke_registry_check_rows.py": "SMOKE_REGISTRY_CHECK_ROWS_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_VERSION",
    "conscious_agent/dashboard_route_registry.py": "DASHBOARD_ROUTE_REGISTRY_VERSION",
    "conscious_agent/dashboard_renderer_metadata.py": "DASHBOARD_RENDERER_METADATA_VERSION",
    "conscious_agent/dashboard_dispatcher_parity.py": "DASHBOARD_DISPATCHER_PARITY_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_prep.py": "DASHBOARD_DISPATCHER_BRANCH_PREP_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_trial.py": "DASHBOARD_DISPATCHER_BRANCH_TRIAL_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_helpers.py": "DASHBOARD_DISPATCHER_BRANCH_HELPERS_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_prep.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_trial.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_VERSION",
    "conscious_agent/eidolon_v1073_source_review_checkpoint.py": "EIDOLON_SOURCE_REVIEW_CHECKPOINT_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_hardening.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v3.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v3.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial_v2.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_TWO_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep_v2.py": "DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_TWO_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v2.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_TWO_VERSION",
    "conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v2.py": "DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_TWO_VERSION",
    "conscious_agent/api_preview_adapter_backfill.py": "MODULE_VERSION",
    "conscious_agent/api_server_dispatch_shared.py": "API_SERVER_DISPATCH_SHARED_VERSION",
    "conscious_agent/api_server_dispatch_route_table_extraction.py": "MODULE_VERSION",
    "conscious_agent/api_server_dispatch_route_table_backfill.py": "MODULE_VERSION",
    "conscious_agent/api_server_dispatch_route_table_safety_parity.py": "MODULE_VERSION",
    "conscious_agent/audited_sandbox_backend_evidence_interface.py": "MODULE_VERSION",
    "conscious_agent/dashboard_route_registry.py": "DASHBOARD_ROUTE_REGISTRY_VERSION",
    "conscious_agent/api_preview_adapter_extraction_pilot.py": "MODULE_VERSION",
    "conscious_agent/api_server_dispatch_helper_backfill.py": "MODULE_VERSION",
    "conscious_agent/api_server_dispatch_helper_extraction_pilot.py": "MODULE_VERSION",
    "conscious_agent/audited_sandbox_backend_preflight_contract.py": "MODULE_VERSION",
    "conscious_agent/autonomy_phase_zero_observation_contract.py": "MODULE_VERSION",
    "conscious_agent/dashboard_api_smoke_shared_utility_adoption.py": "MODULE_VERSION",
    "conscious_agent/dashboard_review_component_extraction_pilot.py": "MODULE_VERSION",
    "conscious_agent/fixture_execution_admission_gate.py": "MODULE_VERSION",
    "conscious_agent/generated_dispatch_promotion_readiness_ledger.py": "MODULE_VERSION",
    "conscious_agent/sandbox_backend_capability_evidence_gate.py": "MODULE_VERSION",
    "conscious_agent/sandboxed_fixture_batch_execution.py": "MODULE_VERSION",
    "conscious_agent/sandboxed_fixture_execution_trial.py": "MODULE_VERSION",
    "conscious_agent/smoke_check_helper_extraction_pilot.py": "MODULE_VERSION",
    "conscious_agent/source_decomposition_batch_i.py": "MODULE_VERSION",
    "conscious_agent/source_decomposition_batch_ii.py": "MODULE_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v3.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_THREE_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v5.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v5.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v6.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v6.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v6.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v7.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v8.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v12.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_VERSION",
    "conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py": "DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_VERSION",
}
CURRENT_SURFACE_VERSION_ASSIGNMENT_RE = re.compile(r'^(?P<name>(?:[A-Z0-9_]+VERSION|MODULE_VERSION))\s*=\s*["\'](?P<value>[^"\']+)["\']', re.MULTILINE)

CURRENT_SYMBOL_ASSIGNMENT_RE = re.compile(r'^(?P<name>CURRENT_VERSION_TAG|CURRENT_MILESTONE|NEXT_RECOMMENDED_ARC|WORKSPACE_CURRENT_MILESTONE|WORKSPACE_NEXT_RECOMMENDED_ARC)\s*=\s*["\'](?P<value>[^"\']+)["\']', re.MULTILINE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_read_text(path))
    except Exception:
        return None


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _docs(root: str | Path | None = None, extra_docs: str = "") -> str:
    repo = _repo(root)
    paths = list(CURRENT_STATE_FILES) + ["README_RELEASE_HISTORY.md", "conscious_agent/api_server.py", "conscious_agent/main.py"]
    seen: set[str] = set()
    parts: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            parts.append(_read_text(repo / path))
    return "\n".join(parts) + "\n" + extra_docs


def _collect_current_json_fields(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in CURRENT_FIELD_NAMES:
                found.append((path, value))
            if key == "release_notes":
                continue
            found.extend(_collect_current_json_fields(value, path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_collect_current_json_fields(value, f"{prefix}[{index}]"))
    return found


def _top_readme_current_text(root: str | Path | None = None) -> str:
    text = _read_text(_repo(root) / "README_NEXT_STEPS.md")
    # Inspect only the active current-state header block; historical arc sections can begin immediately after it.
    return text.split("\n## ", 1)[0]


def _current_symbol_findings(root: str | Path | None = None) -> list[dict[str, str]]:
    repo = _repo(root)
    findings: list[dict[str, str]] = []
    for path in sorted((repo / "conscious_agent").glob("*.py")):
        rel = path.relative_to(repo).as_posix()
        text = _read_text(path)
        for match in CURRENT_SYMBOL_ASSIGNMENT_RE.finditer(text):
            name = match.group("name")
            value = match.group("value")
            ok = True
            expected = ""
            if name == "CURRENT_VERSION_TAG":
                ok = value == CURRENT_VERSION_TAG
                expected = CURRENT_VERSION_TAG
            elif name == "CURRENT_MILESTONE":
                ok = CURRENT_VERSION_TAG in value and EXPECTED_TITLE in value
                expected = CURRENT_MILESTONE
            elif name == "NEXT_RECOMMENDED_ARC":
                ok = value == NEXT_RECOMMENDED_ARC
                expected = NEXT_RECOMMENDED_ARC
            elif name == "WORKSPACE_CURRENT_MILESTONE":
                ok = CURRENT_VERSION_TAG in value and EXPECTED_TITLE in value
                expected = CURRENT_MILESTONE
            elif name == "WORKSPACE_NEXT_RECOMMENDED_ARC":
                ok = value == NEXT_RECOMMENDED_ARC
                expected = NEXT_RECOMMENDED_ARC
            if not ok:
                findings.append({"path": rel, "field": name, "value": value, "expected": expected})
    return findings



def _current_surface_marker_findings(root: str | Path | None = None) -> list[dict[str, str]]:
    repo = _repo(root)
    findings: list[dict[str, str]] = []
    for rel, marker in CURRENT_SURFACE_VERSION_MARKERS.items():
        text = _read_text(repo / rel)
        match = None
        for candidate in CURRENT_SURFACE_VERSION_ASSIGNMENT_RE.finditer(text):
            if candidate.group("name") == marker:
                match = candidate
                break
        runtime_alias_present = (
            f"{marker} = RUNTIME_VERSION" in text
            and "from release_metadata import" in text and "RUNTIME_VERSION" in text
        )
        value = match.group("value") if match else (CURRENT_VERSION if runtime_alias_present else "[missing]")
        if value != CURRENT_VERSION:
            findings.append({"path": rel, "field": marker, "value": value, "expected": CURRENT_VERSION})
    return findings


STALE_EXECUTABLE_SMOKE_ASSERTION_VERSIONS = {"660.0", "700.0", "760.0", "900.0"}


def _stale_executable_smoke_assertion_findings(root: str | Path | None = None) -> list[dict[str, str]]:
    """Find executable current-version comparisons pinned to retired literals.

    This intentionally uses a bounded line scanner instead of repeatedly parsing
    giant modules. Historical prose and release-note helpers are allowed; active
    current-state equality/inequality comparisons against retired global versions
    are release-blocking.
    """
    repo = _repo(root)
    candidate_paths: list[Path] = []
    for rel in ["conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/main.py", "conscious_agent/api_server.py", "conscious_agent/self_development_cycle.py"]:
        path = repo / rel
        if path.suffix == ".py" and path.exists() and path not in candidate_paths:
            candidate_paths.append(path)
    findings: list[dict[str, str]] = []
    compare_markers = ("==", "!=", "<=", ">=", " in ", " not in ")
    for path in candidate_paths:
        rel = path.relative_to(repo).as_posix()
        for lineno, line in enumerate(_read_text(path).splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not any(version in stripped for version in STALE_EXECUTABLE_SMOKE_ASSERTION_VERSIONS):
                continue
            if not any(marker in stripped for marker in compare_markers):
                continue
            # Block active current/global version assertions, not historical module provenance checks.
            active_markers = ("CURRENT_VERSION", "EXPECTED_CURRENT_VERSION", "SELF_MAINTENANCE_VERSION", "DASHBOARD_ROUTE_PROBE_VERSION", "ROUTE_SURFACE_PARITY_VERSION")
            if not any(marker in stripped for marker in active_markers):
                continue
            if ".count(" in stripped or "stale_smoke_text" in stripped or "smoke_text.count" in stripped:
                continue
            lowered = stripped.lower()
            if "historical" in lowered or "release_note" in lowered or "origin_version" in lowered:
                continue
            findings.append({
                "path": rel,
                "field": f"line:{lineno}",
                "value": stripped[:240],
                "expected": f"use CURRENT_VERSION/EXPECTED_CURRENT_VERSION ({CURRENT_VERSION}) or a classified historical-origin check",
            })
    return findings

def build_executable_smoke_current_version_assertion_audit(root: str | Path | None = None) -> dict[str, Any]:
    findings = _stale_executable_smoke_assertion_findings(root)
    rows = [
        _row("no-stale-executable-smoke-version-assertions", len(findings) == 0, "Executable current-state assertions no longer pin global/current version checks to obsolete 660.0, 700.0, 760.0, or 900.0 literals outside classified historical checks."),
        _row("token-presence-not-enough", STALE_VERSION_BOUNDARIES["matching_version_marker_alone_is_metadata_integrity"] is False, "A current smoke JSON token is evidence only; executable assertion drift is scanned separately."),
        _row("historical-text-still-allowed", STALE_VERSION_BOUNDARIES["historical_version_references_are_blocked"] is False, "Historical release/archive references remain allowed outside active executable current-state assertions."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "executable_smoke_current_version_assertion_audit_review_only",
        "target_versions_blocked": sorted(STALE_EXECUTABLE_SMOKE_ASSERTION_VERSIONS),
        "finding_count": len(findings),
        "findings": findings,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "writes_source": False,
        "writes_memory": False,
        "executes_smoke": False,
        "expands_autonomy": False,
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
    }

def _stale_current_findings(root: str | Path | None = None) -> list[dict[str, str]]:
    repo = _repo(root)
    findings: list[dict[str, str]] = []
    top_readme = _top_readme_current_text(repo)
    if CURRENT_VERSION_TAG not in top_readme or EXPECTED_TITLE not in top_readme:
        findings.append({"path": "README_NEXT_STEPS.md", "field": "top_current_state", "value": f"missing {CURRENT_VERSION_TAG} current-state header"})
    if PREVIOUS_CURRENT_TITLE in top_readme:
        findings.append({"path": "README_NEXT_STEPS.md", "field": "top_current_state", "value": PREVIOUS_CURRENT_TITLE})

    json_paths = ["data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"]
    for rel in json_paths:
        data = _read_json(repo / rel)
        for field, value in _collect_current_json_fields(data):
            if isinstance(value, str):
                if field.endswith("last_updated_for") and value != CURRENT_VERSION_TAG:
                    findings.append({"path": rel, "field": field, "value": value, "expected": CURRENT_VERSION_TAG})
                if field.endswith("settings_version") and value != CURRENT_VERSION:
                    findings.append({"path": rel, "field": field, "value": value, "expected": CURRENT_VERSION})
                if field.endswith("current_milestone") and (CURRENT_VERSION_TAG not in value or EXPECTED_TITLE not in value):
                    findings.append({"path": rel, "field": field, "value": value, "expected": CURRENT_MILESTONE})
                if field.endswith("name") and value.startswith("v") and (CURRENT_VERSION_TAG not in value or EXPECTED_TITLE not in value):
                    findings.append({"path": rel, "field": field, "value": value, "expected": CURRENT_MILESTONE})
                if field.endswith("root_version") and value != CURRENT_VERSION:
                    findings.append({"path": rel, "field": field, "value": value, "expected": CURRENT_VERSION})
                if field.endswith("next_recommended_arc") and value != NEXT_RECOMMENDED_ARC:
                    findings.append({"path": rel, "field": field, "value": value, "expected": NEXT_RECOMMENDED_ARC})
    readme = _read_text(repo / "README_NEXT_STEPS.md")
    current_handoff_heading = "## Current Operator Continuity Handoff"
    if current_handoff_heading in readme and f"## Current Operator Continuity Handoff — {CURRENT_VERSION_TAG}" not in readme:
        findings.append({"path": "README_NEXT_STEPS.md", "field": "current_operator_continuity_handoff", "value": "stale or ambiguous Current Operator Continuity Handoff section", "expected": f"historical heading or current {CURRENT_VERSION_TAG} handoff only"})
    smoke = _read_text(repo / "tools/smoke_check.py")
    if f'"version": "{CURRENT_VERSION}"' not in smoke:
        findings.append({"path": "tools/smoke_check.py", "field": "json_summary.version", "value": "missing current smoke JSON summary version", "expected": CURRENT_VERSION})
    stale_summary_literal = '"version": "' + '551' + '.0"'
    if stale_summary_literal in smoke:
        findings.append({"path": "tools/smoke_check.py", "field": "json_summary.version", "value": "551.0", "expected": CURRENT_VERSION})
    dashboard = _read_text(repo / "conscious_agent/dashboard.py")
    marker = "def render_self_development_smoke_debt"
    smoke_debt_section = ""
    if marker in dashboard:
        start = dashboard.index(marker)
        next_def = dashboard.find("\ndef ", start + len(marker))
        smoke_debt_section = dashboard[start: next_def if next_def != -1 else len(dashboard)]
    if smoke_debt_section:
        if CURRENT_VERSION_TAG not in smoke_debt_section or EXPECTED_TITLE not in smoke_debt_section:
            findings.append({"path": "conscious_agent/dashboard.py", "field": "render_self_development_smoke_debt", "value": "missing current smoke debt dashboard marker", "expected": CURRENT_MILESTONE})
        if "v910.0 Metadata and Current Marker Gate Reconciliation v1" in smoke_debt_section:
            findings.append({"path": "conscious_agent/dashboard.py", "field": "render_self_development_smoke_debt", "value": "v910 smoke debt dashboard drift", "expected": CURRENT_MILESTONE})
    findings.extend(_current_symbol_findings(root))
    findings.extend(_current_surface_marker_findings(root))
    findings.extend(_stale_executable_smoke_assertion_findings(root))
    return findings


def build_current_version_source_of_truth_contract(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    settings = _read_json(repo / "data/settings.json") or {}
    active = _read_json(repo / "data/workspaces/active_project.json") or {}
    projects = load_source_project_metadata(repo)
    workspace_projects = _read_json(repo / "data/workspaces/projects.json") or {}
    source_of_truth = {
        "module_version": CURRENT_VERSION,
        "settings_version": settings.get("settings_version"),
        "settings_last_updated_for": settings.get("last_updated_for"),
        "active_project_version": active.get("version"),
        "active_project_last_updated_for": active.get("last_updated_for"),
        "active_project_current_milestone": active.get("current_milestone"),
        "projects_current_milestone": projects.get("current_milestone"),
        "projects_current_project_root_version": (projects.get("current_project") or {}).get("root_version"),
        "projects_next_recommended_arc": projects.get("next_recommended_arc"),
        "projects_current_project_next_recommended_arc": (projects.get("current_project") or {}).get("next_recommended_arc"),
        "workspace_projects_version": workspace_projects.get("version"),
        "workspace_projects_root_version": workspace_projects.get("root_version"),
        "workspace_projects_next_recommended_arc": workspace_projects.get("next_recommended_arc"),
        "workspace_projects_project_next_recommended_arc": ((workspace_projects.get("projects") or [{}])[0]).get("next_recommended_arc", "") if isinstance(workspace_projects.get("projects"), list) else "",
    }
    rows = [
        _row("module-version", CURRENT_VERSION_STALENESS_AUDIT_VERSION == CURRENT_VERSION, f"current={CURRENT_VERSION}"),
        _row("settings-current", settings.get("settings_version") == CURRENT_VERSION and settings.get("last_updated_for") == CURRENT_VERSION_TAG, "settings.json current fields point to the current release."),
        _row("active-project-current", active.get("version") == CURRENT_VERSION and active.get("last_updated_for") == CURRENT_VERSION_TAG and EXPECTED_TITLE in str(active.get("current_milestone", "")), "active project metadata points to the current milestone."),
        _row("projects-current", CURRENT_VERSION_TAG in str(projects.get("current_milestone", "")) and EXPECTED_TITLE in str(projects.get("current_milestone", "")) and str((projects.get("current_project") or {}).get("root_version")) == CURRENT_VERSION, "projects.json current milestone and nested root_version point to the current release."),
        _row("workspace-projects-current", workspace_projects.get("version") == CURRENT_VERSION and str(workspace_projects.get("root_version", CURRENT_VERSION)) == CURRENT_VERSION, "workspace projects metadata points to the current release."),
        _row("next-recommended-arc-current", all(value == NEXT_RECOMMENDED_ARC for value in [projects.get("next_recommended_arc"), (projects.get("current_project") or {}).get("next_recommended_arc"), active.get("next_recommended_arc"), workspace_projects.get("next_recommended_arc"), ((workspace_projects.get("projects") or [{}])[0]).get("next_recommended_arc", "") if isinstance(workspace_projects.get("projects"), list) else ""]), "Top-level and nested project/workspace next_recommended_arc fields point to the current next arc."),
        _row("historical-allowed", STALE_VERSION_BOUNDARIES["historical_version_references_are_blocked"] is False, "Historical version references remain allowed in release history and prior module archives."),
        _row("current-stale-blocked", STALE_VERSION_BOUNDARIES["current_state_stale_references_are_allowed"] is False, "Current-state stale references are blocked."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "current_version_source_of_truth_contract_review_only",
        "source_of_truth_id": SOURCE_OF_TRUTH_ID,
        "source_of_truth": source_of_truth,
        "stale_version_audit_status": "prepared",
        "metadata_current_state_status": "aligned_or_blocked",
        "post_patch_verification_status": "review_prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "creates_release": False,
        "expands_autonomy": False,
    }


def build_current_symbol_staleness_audit(root: str | Path | None = None) -> dict[str, Any]:
    findings = _current_symbol_findings(root) + _current_surface_marker_findings(root)
    rows = [
        _row("current-symbols-clean", len(findings) == 0, "All current symbol assignments and current surface version markers point to the current release/next arc."),
        _row("symbol-audit-review-only", STALE_VERSION_BOUNDARIES["stale_audit_writes_source"] is False and STALE_VERSION_BOUNDARIES["stale_audit_writes_memory"] is False, "Expanded symbol audit is review-only and writes no source or memory."),
        _row("current-symbols-not-authority", STALE_VERSION_BOUNDARIES["matching_version_marker_alone_is_metadata_integrity"] is False, "Matching current symbols alone are not approval, release permission, or metadata integrity by themselves."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "expanded_current_symbol_staleness_audit_review_only",
        "current_symbol_audit_id": CURRENT_SYMBOL_AUDIT_ID,
        "symbols_checked": sorted(CURRENT_SYMBOL_NAMES),
        "surface_version_markers_checked": dict(CURRENT_SURFACE_VERSION_MARKERS),
        "current_symbol_findings": findings,
        "stale_version_audit_status": "clean_or_blocked" if not findings else "blocked",
        "metadata_current_state_status": "aligned_or_blocked" if not findings else "blocked",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "writes_source": False,
        "writes_memory": False,
        "creates_release": False,
        "executes_commands": False,
        "expands_autonomy": False,
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
    }


def build_stale_version_string_scanner(root: str | Path | None = None) -> dict[str, Any]:
    findings = _stale_current_findings(root)
    executable_assertion_audit = build_executable_smoke_current_version_assertion_audit(root)
    repo = _repo(root)
    history_text = "\n".join(_read_text(repo / rel) for rel in HISTORICAL_TEXT_FILES)
    rows = [
        _row("current-state-findings", len(findings) == 0, "No stale current-state version, title, metadata, current-symbol drift, or executable smoke current-version assertion drift found in active current-state surfaces."),
        _row("executable-smoke-assertions-current", executable_assertion_audit.get("ok") is True, "Live current-state comparisons no longer require obsolete global/current versions outside classified historical checks."),
        _row("historical-archive-allowed", "v550.0" in history_text and STALE_VERSION_BOUNDARIES["historical_version_references_are_blocked"] is False, "Historical release/module text may retain older version strings."),
        _row("scanner-is-review-only", STALE_VERSION_BOUNDARIES["stale_audit_writes_source"] is False and STALE_VERSION_BOUNDARIES["stale_audit_writes_memory"] is False, "Scanner is review-only and writes no source or memory."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "stale_version_string_scanner_review_only",
        "scanner_id": STALE_SCANNER_ID,
        "scanned_current_state_files": list(CURRENT_STATE_FILES),
        "historical_text_files_allowed": list(HISTORICAL_TEXT_FILES),
        "stale_current_state_findings": findings,
        "executable_smoke_assertion_audit": executable_assertion_audit,
        "stale_version_audit_status": "clean_or_blocked" if not findings else "blocked",
        "metadata_current_state_status": "aligned_or_blocked" if not findings else "blocked",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "creates_release": False,
        "executes_commands": False,
        "expands_autonomy": False,
    }


def build_stale_milestone_title_drift_audit(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    active = _read_json(repo / "data/workspaces/active_project.json") or {}
    projects = load_source_project_metadata(repo)
    workspace_projects = _read_json(repo / "data/workspaces/projects.json") or {}
    milestones = {
        "active_project.current_milestone": active.get("current_milestone", ""),
        "projects.current_milestone": projects.get("current_milestone", ""),
        "projects.current_project.current_milestone": (projects.get("current_project") or {}).get("current_milestone", ""),
        "workspace_projects.projects[0].current_milestone": ((workspace_projects.get("projects") or [{}])[0]).get("current_milestone", "") if isinstance(workspace_projects.get("projects"), list) else "",
    }
    stale_titles = {key: value for key, value in milestones.items() if (CURRENT_VERSION_TAG not in str(value) or EXPECTED_TITLE not in str(value))}
    rows = [
        _row("milestones-current", not stale_titles, "Current milestone titles use the current release and arc title."),
        _row("version-alone-not-enough", STALE_VERSION_BOUNDARIES["matching_version_marker_alone_is_metadata_integrity"] is False, "Matching version marker alone is not considered metadata integrity."),
        _row("previous-title-not-current", all(PREVIOUS_CURRENT_TITLE not in str(value) for value in milestones.values()), "Previous current title is not present in current milestone fields."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "stale_milestone_title_drift_audit_review_only",
        "milestone_drift_id": MILESTONE_DRIFT_ID,
        "milestones": milestones,
        "stale_milestone_title_findings": stale_titles,
        "metadata_current_state_status": "aligned_or_blocked" if not stale_titles else "blocked",
        "stale_version_audit_status": "clean_or_blocked" if not stale_titles else "blocked",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "creates_release": False,
        "expands_autonomy": False,
    }


def build_post_live_patch_verification_prep(root: str | Path | None = None) -> dict[str, Any]:
    verification_plan = {
        "verification_plan_id": POST_PATCH_VERIFICATION_ID,
        "compile": "python -m compileall conscious_agent tools",
        "targeted_smoke": "python tools/smoke_check.py --check <targeted-check>",
        "fast_smoke": "python tools/smoke_check.py --tier fast",
        "affected_dashboard_routes": "probe affected routes and dashboard route probe coverage",
        "affected_api_route": "call affected /api/<route>/layer",
        "affected_cli_flag": "call affected CLI flag",
        "release_docs_updated": True,
        "package_privacy_clean": True,
        "no_memory_mutation": True,
        "no_autonomy_expansion": True,
        "rollback_packet_still_valid": True,
        "verification_plan_executes_checks": False,
        "patch_applied": False,
    }
    rows = [
        _row("commands-declared", len(POST_PATCH_VERIFICATION_COMMANDS) >= 5, "Compile, targeted smoke, fast smoke, dashboard, API, CLI, and release verification expectations are declared."),
        _row("docs-required", verification_plan["release_docs_updated"] is True, "README and release history updates remain required after any future live patch."),
        _row("safety-required", verification_plan["no_memory_mutation"] is True and verification_plan["no_autonomy_expansion"] is True and verification_plan["rollback_packet_still_valid"] is True, "No memory mutation, no autonomy expansion, and rollback validity remain required."),
        _row("plan-not-patch", verification_plan["patch_applied"] is False and STALE_VERSION_BOUNDARIES["verification_plan_exists_is_patch_applied"] is False, "Verification plan existence is not patch application."),
        _row("plan-does-not-run", verification_plan["verification_plan_executes_checks"] is False and STALE_VERSION_BOUNDARIES["post_patch_verification_plan_executes_checks"] is False, "Post-patch verification prep does not execute commands."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "post_live_patch_verification_prep_review_only",
        "post_patch_verification_id": POST_PATCH_VERIFICATION_ID,
        "verification_plan": verification_plan,
        "verification_commands": list(POST_PATCH_VERIFICATION_COMMANDS),
        "post_patch_verification_status": "review_prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "creates_release": False,
        "executes_commands": False,
        "applies_patch": False,
        "expands_autonomy": False,
    }


def build_release_staleness_and_verification_audit_board(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    source = build_current_version_source_of_truth_contract(root)
    scanner = build_stale_version_string_scanner(root)
    milestone = build_stale_milestone_title_drift_audit(root)
    symbols = build_current_symbol_staleness_audit(root)
    verification = build_post_live_patch_verification_prep(root)
    text = _docs(root, docs)
    required_tokens = [
        "v860.0 Manifest-Guided Sandbox Probe File Generation Dry-Run v1",
        "v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
        "v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
        "v885.0 Sandbox Probe Execution Result Review and Promotion Readiness v1",
        "v895.0 Operator-Approved Live Probe Registration Trial v1",
        "v890.0 Live Probe Promotion Plan Review v1",
        "v870.0 Sandbox Probe File Verification and Cleanup Review v1",
        TARGETED_SMOKE,
        "--operator-approved-live-probe-registration-trial",
        "build_operator_approved_live_probe_registration_trial",
        "operator_approved_live_probe_registration_trial_text",
        "--sandbox-probe-file-verification-and-cleanup-review",
        "build_sandbox_probe_file_verification_and_cleanup_review",
        "sandbox_probe_file_verification_and_cleanup_review_text",
        "--operator-approved-sandbox-probe-file-generation-trial",
        "build_operator_approved_sandbox_probe_file_generation_trial",
        "operator_approved_sandbox_probe_file_generation_trial_text",
        "dashboard-chat-sse-parser-active-smoke-debt-repair-v1",
        "buffer.split('\\\\n\\\\n')",
        "packet.split('\\\\n')",
        "intent=small_talk",
        "release-pipeline",
        "code-patch-release",
        "approval-release-workflow",
        "current_release_failure",
        ".gitignore",
        "--self-development-prompt",
        "applies_source_edits=False",
        "creates_concrete_diff=False",
        "runs_broad_smoke=False",
        "modifies_approval_system=False",
        "modifies_release_system=False",
        "expands_autonomy=False",
        "documentation_state_is_authorization=False",
        "metadata_consistency_is_authorization=False",
        "release_integrity_pass_is_approval=False",
        "no_native_title_tooltip",
        "data-tip",
    ]
    rows = [
        _row("source-of-truth", source.get("ok") is True, "Current version source-of-truth contract aligns settings, active project, project metadata, and workspace metadata to the current release."),
        _row("stale-scanner", scanner.get("ok") is True, "Stale current-state version string scanner is clean while allowing historical text."),
        _row("milestone-title-drift", milestone.get("ok") is True, "Current milestone titles are aligned and previous current title is not active."),
        _row("current-symbol-staleness", symbols.get("ok") is True, "Expanded current-symbol audit finds no stale CURRENT_VERSION_TAG, CURRENT_MILESTONE, or NEXT_RECOMMENDED_ARC assignments."),
        _row("verification-prep", verification.get("ok") is True and verification.get("executes_commands") is False, "Post-live-patch verification prep is declared but does not run checks."),
        _row("docs", all(token in text for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v780 audit-wording cleanup and manifest-generation prep surfaces without granting authority."),
        _row("no-authority", all(STALE_VERSION_BOUNDARIES[key] is False for key in ["stale_audit_pass_is_live_patch_permission", "stale_audit_pass_is_release_approval", "post_patch_verification_plan_executes_checks", "post_patch_verification_plan_applies_patch", "stale_audit_writes_source", "stale_audit_writes_memory", "stale_audit_creates_release", "stale_audit_executes_rollback", "stale_audit_invokes_models_by_default", "stale_audit_schedules_work", "stale_audit_reuses_approval", "stale_audit_continues_automatically", "stale_audit_expands_autonomy"]), "Audit grants no live patch, release, command execution, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "current_audit_wording_cleanup_and_manifest_generation_prep_review_only",
        "audit_id": FINAL_AUDIT_ID,
        "stale_version_audit_status": "clean_or_blocked",
        "metadata_current_state_status": "aligned_or_blocked",
        "post_patch_verification_status": "review_prepared",
        "recovery_drill_status": "prepared_not_executed",
        "rollback_decision_status": "review_prepared",
        "release_closure_status": "evidence_prepared",
        "closure_approval_status": "required",
        "release_decision_status": "prepared_for_operator",
        "operator_decision_status": "required",
        "archive_ledger_status": "prepared_not_written_externally",
        "archive_retrieval_status": "prepared_read_only",
        "continuity_index_status": "prepared",
        "historical_reference_status": "classified",
        "stale_current_reference_status": "blocked_if_detected",
        "retrieval_packet_status": "prepared",
        "archive_search_status": "prepared_read_only",
        "release_record_query_status": "matrix_prepared",
        "search_result_review_status": "prepared",
        "archive_handoff_status": "prepared",
        "archive_write_status": "not_performed",
        "archive_export_status": "prepared_not_written_externally",
        "export_packet_status": "prepared",
        "operator_decision_closure_status": "required",
        "archive_export_integrity_status": "review_prepared",
        "external_archive_write_status": "not_performed",
        "archive_import_status": "prepared_not_written",
        "import_packet_status": "review_prepared",
        "closure_recall_status": "historical_review_prepared",
        "imported_archive_continuity_status": "guarded",
        "current_state_mutation_status": "not_performed",
        "publish_status": "not_authorized",
        "verification_receipt_status": "awaiting_operator_supplied_evidence",
        "rollback_status": "not_executed",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "current_version_source_of_truth_contract": source,
        "stale_version_string_scanner": scanner,
        "stale_milestone_title_drift_audit": milestone,
        "current_symbol_staleness_audit": symbols,
        "post_live_patch_verification_prep": verification,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(STALE_VERSION_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_commands": False,
        "executes_rollback": False,
        "creates_release": False,
        "publishes_release": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the v776-v780 manifest-gated surface validation expansion. It should remain review-only and must not generate surfaces, approve itself, execute commands, write memory, create releases, publish, continue automatically, or expand autonomy.",
    }


def render_release_staleness_and_verification_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"stale_version_audit_status: {report.get('stale_version_audit_status', 'clean_or_blocked')}",
        f"metadata_current_state_status: {report.get('metadata_current_state_status', 'aligned_or_blocked')}",
        f"post_patch_verification_status: {report.get('post_patch_verification_status', 'prepared')}",
        f"evidence_intake_status: {report.get('evidence_intake_status', 'awaiting_operator_supplied_evidence')}",
        f"verification_receipt_status: {report.get('verification_receipt_status', 'not_supplied')}",
        f"rollback_status: {report.get('rollback_status', 'not_executed')}",
        f"live_patch_status: {report.get('live_patch_status', 'not_applied_by_default')}",
        f"approval_status: {report.get('approval_status', 'required')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v545.1-v551.0 current version staleness and post patch evidence tokens: current-version-source-of-truth-contract stale-version-string-scanner stale-milestone-title-drift-audit post-live-patch-verification-prep release-staleness-verification-audit-board post-live-patch-evidence-intake-contract expanded-current-symbol-staleness-audit post-live-patch-evidence-intake-contract-v1 current_version_staleness_audit.py post_live_patch_verification_rollback_trial.py current-symbols-clean historical_version_references_are_blocked=False current_state_stale_references_are_allowed=False matching_version_marker_alone_is_metadata_integrity=False verification_plan_exists_is_patch_applied=False stale_audit_pass_is_live_patch_permission=False stale_audit_pass_is_release_approval=False post_patch_verification_plan_executes_checks=False post_patch_verification_plan_applies_patch=False stale_audit_writes_source=False stale_audit_writes_memory=False stale_audit_creates_release=False stale_audit_executes_rollback=False stale_audit_invokes_models_by_default=False stale_audit_schedules_work=False stale_audit_reuses_approval=False stale_audit_continues_automatically=False stale_audit_expands_autonomy=False stale_version_audit_status=clean_or_blocked metadata_current_state_status=aligned_or_blocked post_patch_verification_status=prepared evidence_intake_status=awaiting_operator_supplied_evidence verification_receipt_status=not_supplied rollback_status=not_executed live_patch_status=not_applied_by_default approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console

# v552.0-v555.0 post live patch verification rollback tokens: verification-receipt-review-layer rollback-snapshot-validity-review post-patch-regression-staleness-audit-board post-live-patch-verification-rollback-trial post-live-patch-verification-and-rollback-trial-v1 current-symbols-clean receipt_review_does_not_execute_commands=True receipt_review_is_release_approval=False rollback_plan_is_rollback_execution=False regression_audit_pass_is_release_approval=False trial_board_is_autonomy_approval=False evidence_intake_status=awaiting_operator_supplied_evidence verification_receipt_status=awaiting_operator_supplied_evidence rollback_status=planned_not_executed stale_version_audit_status=clean_or_blocked metadata_current_state_status=aligned_or_blocked post_patch_verification_status=review_prepared live_patch_status=not_applied_by_default approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console

# v556.0-v565.0 recovery drill release closure current audit tokens: recovery-drill-scope-contract rollback-decision-review-packet release-closure-evidence-board operator-closure-approval-gate recovery-drill-release-closure-board recovery-drill-and-release-closure-v1 recovery_drill_release_closure.py recovery_drill_status=prepared_not_executed rollback_decision_status=review_prepared release_closure_status=evidence_prepared closure_approval_status=required rollback_status=not_executed release_status=not_created authorization_status=not_authorized autonomy_status=not_autonomous current-symbols-clean no_native_title_tooltip data-tip command-deck operator-console

# v651.0-v655.0 current version staleness tokens: operator-guided-review-wizard-ux-v1 operator_guided_review_wizard_ux.py guided-review-wizard-entry-model guided-evidence-warning-step-cards guided-decision-approval-step-ux guided-verification-resume-step-summary operator-guided-review-wizard-board guided_review_wizard_ux_status=prepared_only wizard_entry_status=prepared evidence_warning_cards_status=prepared decision_approval_step_status=prepared verification_resume_step_status=prepared guided_review_board_status=review_only approval_semantics_changed=False wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_treats_pass_as_authorization=False wizard_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v656.0-v660.0 current version staleness tokens: project-metadata-schema-active-context-repair-v1 project_metadata_active_context_repair.py metadata-schema-contract active-project-resolution-audit project-status-rendering-hardening release-note-version-semantics-audit metadata-integrity-board-smoke-gate metadata_active_context_repair_status=prepared_only metadata_schema_contract_status=prepared active_project_resolution_status=audited project_status_rendering_status=hardened_or_blocked release_note_version_semantics_status=classified_or_blocked metadata_integrity_board_status=review_only approval_semantics_changed=False schema_contract_writes_metadata=False active_project_resolution_changes_project=False status_rendering_executes_actions=False release_note_semantics_rewrites_history=False metadata_integrity_board_executes_smoke=False metadata_integrity_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v661.0-v665.0 current version staleness tokens: legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy_smoke_segmentation_repair_status=prepared_only smoke_gate_classification_status=prepared current_release_gate_segment_status=prepared legacy_advisory_segment_status=separated stale_expectation_repair_status=audited smoke_segmentation_integrity_board_status=review_only current_release_blocking legacy_advisory historical_pinned slow_full_audit migration_debt approval_semantics_changed=False classification_changes_smoke_results=False current_gate_executes_smoke=False current_gate_treats_pass_as_authorization=False legacy_advisory_blocks_current_release=False legacy_advisory_executes_checks=False stale_expectation_repair_rewrites_history=False stale_expectation_repair_executes_smoke=False segmentation_board_executes_smoke=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v666.0-v685.0 current version staleness tokens: manifest-driven-surface-registry-v1 manifest_driven_surface_registry.py surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board manifest_driven_surface_registry_status=prepared_only surface_registry_manifest_contract_status=prepared dashboard_manifest_adapter_status=validated_or_blocked api_cli_manifest_adapter_status=validated_or_blocked smoke_manifest_adapter_status=validated_or_blocked source_surface_reconciliation_status=reconciled_or_blocked documentation_token_manifest_status=validated_or_blocked manifest_drift_detection_status=prepared registry_generation_prep_status=prepared manifest_current_release_gate_status=prepared manifest_surface_registry_board_status=review_only approval_semantics_changed=False manifest_contract_writes_source=False dashboard_manifest_adapter_registers_routes=False api_cli_manifest_adapter_registers_endpoints=False smoke_manifest_adapter_executes_smoke=False source_surface_reconciliation_mutates_manifest=False documentation_token_validation_rewrites_docs=False drift_detection_auto_fixes=False generation_prep_generates_live_routes=False manifest_current_gate_executes_checks=False manifest_board_expands_autonomy=False manifest_presence_is_authorization=False registry_health_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v676.0-v685.0 current integrity tokens: v685.0 Dashboard Renderer Component Extraction v1 dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard_renderer_component_extraction_status=prepared_only dashboard_renderer_component_extraction_board_status=review_only approval_semantics_changed=False component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v686.0-v690.0 current version staleness tokens: v690.0 Neural Command Deck Dashboard Redesign v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only approval_semantics_changed=False layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 neural command deck interaction refinement current version staleness tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False focus_rail_auto_selects_roadmap=False input_deck_sends_commands=False input_deck_creates_approval=False input_deck_executes_models=False priority_tuning_hides_blockers=False priority_tuning_treats_visual_priority_as_authorization=False context_affordance_reads_private_data=False context_affordance_mutates_memory=False telemetry_affordance_executes_checks=False interaction_board_writes_source=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v711.0-v760.0 current staleness audit tokens: DASHBOARD_VERSION API_VERSION RELEASE_PACKAGING_VERSION RELEASE_INSTALLATION_VERSION VERSION_STATE_VERSION source_only_zip_excludes_data_tasks=True source_only_zip_excludes_data_approvals=True self-development-cycle-v1

# v1072.3 current version staleness audit tokens: dashboard-dispatcher-branch-extraction-prep-v1 /dashboard-dispatcher-branch-extraction-prep conscious_agent/dashboard_dispatcher_branch_prep.py build_dashboard_dispatcher_branch_extraction_prep_report dashboard_dispatcher_branch_extraction_prep_text branch_extraction_prepared_only=True branch_extraction_executed=False dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed_for_candidates=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 current version staleness audit tokens: dashboard-dispatcher-branch-extraction-trial-v1 /dashboard-dispatcher-branch-extraction-trial conscious_agent/dashboard_dispatcher_branch_trial.py build_dashboard_dispatcher_branch_extraction_trial_report dashboard_dispatcher_branch_extraction_trial_text render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 current version staleness audit tokens: dashboard-dispatcher-branch-expansion-trial-v1 /dashboard-dispatcher-branch-extraction-expansion-prep conscious_agent/dashboard_dispatcher_branch_expansion_trial.py build_dashboard_dispatcher_branch_expansion_trial_report dashboard_dispatcher_branch_expansion_trial_text branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 current version staleness audit tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v1 /dashboard-dispatcher-branch-expansion-backfill-prep conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep.py build_dashboard_dispatcher_branch_expansion_backfill_prep_report dashboard_dispatcher_branch_expansion_backfill_prep_text NEXT_BACKFILL_CANDIDATE_PATH=/dashboard-dispatcher-branch-extraction-prep branch_expansion_backfill_prepared_only=True branch_expansion_backfill_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=3 prepared_candidate_count=1 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.4 current version staleness audit tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 /dashboard-dispatcher-branch-expansion-backfill-trial conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py build_dashboard_dispatcher_branch_expansion_backfill_trial_report dashboard_dispatcher_branch_expansion_backfill_trial_text CURRENT_VERSION=1072.4 CURRENT_MILESTONE="v1072.4 Dashboard Dispatcher Branch Expansion Backfill Trial v1" TARGETED_SMOKE=dashboard-dispatcher-branch-expansion-backfill-trial-v1 branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.0 current version staleness audit tokens: eidolon-v1073-source-review-checkpoint-v1 /eidolon-v1073-source-review-checkpoint CURRENT_VERSION=1073.0 CURRENT_MILESTONE="v1073.0 Dashboard Dispatcher Decomposition Checkpoint v1" TARGETED_SMOKE=eidolon-v1073-source-review-checkpoint-v1 helper_backed_branch_count=6 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.1 current version staleness audit tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 /dashboard-dispatcher-branch-decomposition-continuation-prep CURRENT_VERSION=1073.1 CURRENT_MILESTONE="v1073.1 Dispatcher Branch Decomposition Continuation Prep v1" TARGETED_SMOKE=dashboard-dispatcher-branch-decomposition-continuation-prep-v1 helper_backed_branch_count=6 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.3 current version staleness audit tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 CURRENT_VERSION=1073.3 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-branch-decomposition-continuation-prep-v2 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=7 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /dashboard-dispatcher-branch-decomposition-continuation-trial-v2 CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-branch-decomposition-continuation-trial-v2 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-branch-decomposition-continuation-prep-v3 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-branch-decomposition-continuation-trial-v3 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=9 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-batch-strategy-checkpoint-v1 /dashboard-dispatcher-batch-strategy-checkpoint CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-batch-strategy-checkpoint-v1 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=9 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v1 /dashboard-dispatcher-batch-decomposition-prep CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v1 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=9 prepared_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-trial-v1 /dashboard-dispatcher-batch-decomposition-trial CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v1 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=12 moved_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint CURRENT_VERSION=1074.0 CURRENT_MILESTONE="v1074.0 Dispatcher Batch Decomposition Checkpoint v1" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-checkpoint-v1 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Prep v2" helper_backed_branch_count=12 recommended_batch_size=3 remaining_registry_direct_branch_count=36 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.3 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v2 /dashboard-dispatcher-batch-decomposition-prep-v2 CURRENT_VERSION=1074.3 CURRENT_MILESTONE="v1074.3 Dispatcher Batch Decomposition Prep v2" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v2 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Checkpoint v2" helper_backed_branch_count=12 prepared_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.3 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 CURRENT_VERSION=1074.3 CURRENT_MILESTONE="v1074.3 Dispatcher Batch Decomposition Checkpoint v2" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-checkpoint-v2 NEXT_RECOMMENDED_ARC="v1074.3 Dispatcher Batch Decomposition Checkpoint v2" helper_backed_branch_count=15 moved_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.4 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v3 /dashboard-dispatcher-batch-decomposition-prep-v3 CURRENT_VERSION=1074.4 CURRENT_MILESTONE="v1074.6 Dispatcher Batch Decomposition Checkpoint v3" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v3 NEXT_RECOMMENDED_ARC="v1074.6 Dispatcher Batch Decomposition Checkpoint v3" helper_backed_branch_count=15 prepared_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.8 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v4 /dashboard-dispatcher-batch-decomposition-prep-v4 CURRENT_VERSION=1074.7 CURRENT_MILESTONE="v1074.8 Dispatcher Batch Decomposition Trial v4" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v4 NEXT_RECOMMENDED_ARC="v1074.9 Dispatcher Batch Decomposition Checkpoint v4" helper_backed_branch_count=18 prepared_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.8 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 CURRENT_VERSION=1074.8 CURRENT_MILESTONE="v1074.8 Dispatcher Batch Decomposition Trial v4" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v4 NEXT_RECOMMENDED_ARC="v1074.9 Dispatcher Batch Decomposition Checkpoint v4" helper_backed_branch_count=21 moved_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.9 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v4 /dashboard-dispatcher-batch-decomposition-checkpoint-v4 CURRENT_VERSION=1074.9 CURRENT_MILESTONE="v1074.9 Dispatcher Batch Decomposition Checkpoint v4" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-checkpoint-v4 NEXT_RECOMMENDED_ARC="v1075.0 Dispatcher Batch Decomposition Prep v5" helper_backed_branch_count=21 recommended_batch_size=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.0 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v5 /dashboard-dispatcher-batch-decomposition-prep-v5 CURRENT_VERSION=1075.0 CURRENT_MILESTONE="v1075.1 Dispatcher Batch Decomposition Trial v5" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v5 NEXT_RECOMMENDED_ARC="v1075.2 Dispatcher Batch Decomposition Checkpoint v5" helper_backed_branch_count=21 prepared_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.0 current surface marker parser repair tokens: CURRENT_SURFACE_VERSION_ASSIGNMENT_RE supports digits in version constant names such as DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_VERSION current_state_stale_references_are_allowed=False

# v1075.1 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-trial-v5 /dashboard-dispatcher-batch-decomposition-trial-v5 CURRENT_VERSION=1075.1 CURRENT_MILESTONE="v1075.1 Dispatcher Batch Decomposition Trial v5" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v5 NEXT_RECOMMENDED_ARC="v1075.2 Dispatcher Batch Decomposition Checkpoint v5" helper_backed_branch_count=24 moved_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False
# v1075.2 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 /dashboard-dispatcher-batch-decomposition-checkpoint-v5 CURRENT_VERSION=1075.2 CURRENT_MILESTONE="v1075.2 Dispatcher Batch Decomposition Checkpoint v5" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-checkpoint-v5 NEXT_RECOMMENDED_ARC="v1075.3 Dispatcher Batch Decomposition Prep v6" helper_backed_branch_count=24 recommended_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.3 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v6 /dashboard-dispatcher-batch-decomposition-prep-v6 CURRENT_VERSION=1075.3 CURRENT_MILESTONE="v1075.3 Dispatcher Batch Decomposition Prep v6" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v6 NEXT_RECOMMENDED_ARC="v1075.4 Dispatcher Batch Decomposition Trial v6" helper_backed_branch_count=24 prepared_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.4 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-trial-v6 /dashboard-dispatcher-batch-decomposition-trial-v6 CURRENT_VERSION=1075.4 CURRENT_MILESTONE="v1075.4 Dispatcher Batch Decomposition Trial v6" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v6 NEXT_RECOMMENDED_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" helper_backed_branch_count=27 moved_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.5 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 /dashboard-dispatcher-batch-decomposition-checkpoint-v6 CURRENT_VERSION=1075.5 CURRENT_MILESTONE="v1075.7 Dispatcher Batch Decomposition Trial v7" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-checkpoint-v6 NEXT_RECOMMENDED_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" helper_backed_branch_count=27 recommended_batch_size=3 remaining_registry_direct_branch_count=36 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.5 workspace next arc symbol parsing repair tokens: WORKSPACE_NEXT_RECOMMENDED_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" current_symbol_scan_covers_workspace_next=True dashboard-dispatcher-batch-decomposition-checkpoint-v6

# v1075.6 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v7 /dashboard-dispatcher-batch-decomposition-prep-v7 CURRENT_VERSION=1075.6 CURRENT_MILESTONE="v1075.7 Dispatcher Batch Decomposition Trial v7" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v7 NEXT_RECOMMENDED_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" helper_backed_branch_count=27 prepared_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1075.7 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-trial-v7 /dashboard-dispatcher-batch-decomposition-trial-v7 CURRENT_VERSION=1075.7 CURRENT_MILESTONE="v1075.7 Dispatcher Batch Decomposition Trial v7" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v7 NEXT_RECOMMENDED_ARC="v1075.8 Dispatcher Batch Decomposition Checkpoint v7" helper_backed_branch_count=30 moved_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1076.1 current version staleness audit tokens: dashboard-dispatcher-batch-decomposition-prep-v8 /dashboard-dispatcher-batch-decomposition-prep-v8 CURRENT_VERSION=1076.1 CURRENT_MILESTONE="v1076.5 Dispatcher Batch Decomposition Prep v10" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-prep-v8 NEXT_RECOMMENDED_ARC="v1076.5 Dispatcher Batch Decomposition Prep v10" helper_backed_branch_count=30 prepared_batch_size=3 actual_fixture_execution_count=0 sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1077.2 current version staleness tokens: dashboard-dispatcher-batch-decomposition-trial-v12 /dashboard-dispatcher-batch-decomposition-trial-v12 CURRENT_VERSION=1077.2 CURRENT_MILESTONE="v1077.2 Dispatcher Batch Decomposition Trial v12" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v12 NEXT_RECOMMENDED_ARC="v1077.3 Dispatcher Batch Decomposition Checkpoint v12" helper_backed_branch_count=45

# v1077.4 current version staleness tokens: dashboard-dispatcher-batch-decomposition-trial-v13 /dashboard-dispatcher-batch-decomposition-trial-v13 CURRENT_VERSION=1077.4 CURRENT_MILESTONE="v1077.5 Dispatcher Batch Decomposition Trial v13" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v13 NEXT_RECOMMENDED_ARC="v1077.6 Dispatcher Batch Decomposition Checkpoint v13" helper_backed_branch_count=48 moved_batch_size=3

# v1077.5 current version staleness tokens: dashboard-dispatcher-batch-decomposition-trial-v13 /dashboard-dispatcher-batch-decomposition-trial-v13 CURRENT_VERSION=1077.5 CURRENT_MILESTONE="v1077.5 Dispatcher Batch Decomposition Trial v13" TARGETED_SMOKE=dashboard-dispatcher-batch-decomposition-trial-v13 NEXT_RECOMMENDED_ARC="v1077.6 Dispatcher Batch Decomposition Checkpoint v13" helper_backed_branch_count=48 moved_batch_size=3
