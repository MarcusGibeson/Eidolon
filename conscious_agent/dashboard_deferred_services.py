from __future__ import annotations

"""Declarative lazy boundary for non-conversation dashboard services.

The module contains only literal route/UI contracts and lazy call mappings. It
does not import the underlying administrative, release, evaluation, repair, or
development services until a matching dashboard surface is used.
"""

from typing import Any, MutableMapping

from lazy_imports import install_lazy_callables, lazy_import_status

DEFERRED_CONSTANTS: dict[str, Any] = {
    'DASHBOARD_ROUTE_REGISTRY_ROUTE': '/dashboard-route-registry-extraction',  # dashboard_route_registry.DASHBOARD_ROUTE_REGISTRY_ROUTE
    'DASHBOARD_RENDERER_METADATA_ROUTE': '/dashboard-renderer-metadata-extraction',  # dashboard_renderer_metadata.DASHBOARD_RENDERER_METADATA_ROUTE
    'DASHBOARD_DISPATCHER_PARITY_ROUTE': '/dashboard-dispatcher-parity',  # dashboard_dispatcher_parity.DASHBOARD_DISPATCHER_PARITY_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE': '/dashboard-dispatcher-branch-extraction-prep',  # dashboard_dispatcher_branch_prep.DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE': '/dashboard-dispatcher-branch-extraction-trial',  # dashboard_dispatcher_branch_trial.DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE': '/dashboard-dispatcher-branch-extraction-backfill',  # dashboard_dispatcher_branch_backfill.DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE': '/dashboard-dispatcher-branch-helper-consolidation',  # dashboard_dispatcher_branch_helper_consolidation.DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE': '/dashboard-dispatcher-branch-extraction-expansion-prep',  # dashboard_dispatcher_branch_expansion_prep.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE': '/dashboard-dispatcher-branch-expansion-trial',  # dashboard_dispatcher_branch_expansion_trial.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_ROUTE': '/dashboard-dispatcher-branch-expansion-backfill-prep',  # dashboard_dispatcher_branch_expansion_backfill_prep.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_ROUTE': '/dashboard-dispatcher-branch-expansion-backfill-trial',  # dashboard_dispatcher_branch_expansion_backfill_trial.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_ROUTE': '/dashboard-dispatcher-branch-expansion-backfill-prep-v2',  # dashboard_dispatcher_branch_expansion_backfill_prep_v2.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE': '/dashboard-dispatcher-branch-expansion-backfill-trial-v2',  # dashboard_dispatcher_branch_expansion_backfill_trial_v2.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_ROUTE': '/dashboard-dispatcher-branch-expansion-backfill-prep-v3',  # dashboard_dispatcher_branch_expansion_backfill_prep_v3.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE': '/dashboard-dispatcher-branch-expansion-backfill-trial-v3',  # dashboard_dispatcher_branch_expansion_backfill_trial_v3.DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE': '/dashboard-dispatcher-branch-decomposition-hardening',  # dashboard_dispatcher_branch_decomposition_hardening.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE
    'EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE': '/eidolon-v1073-source-review-checkpoint',  # eidolon_v1073_source_review_checkpoint.EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_ROUTE': '/dashboard-dispatcher-branch-decomposition-continuation-prep',  # dashboard_dispatcher_branch_decomposition_continuation_prep.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE': '/dashboard-dispatcher-branch-decomposition-continuation-trial',  # dashboard_dispatcher_branch_decomposition_continuation_trial.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V2_ROUTE': '/dashboard-dispatcher-branch-decomposition-continuation-prep-v2',  # dashboard_dispatcher_branch_decomposition_continuation_prep_v2.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V2_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE': '/dashboard-dispatcher-branch-decomposition-continuation-trial-v2',  # dashboard_dispatcher_branch_decomposition_continuation_trial_v2.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE': '/dashboard-dispatcher-branch-decomposition-continuation-prep-v3',  # dashboard_dispatcher_branch_decomposition_continuation_prep_v3.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE': '/dashboard-dispatcher-branch-decomposition-continuation-trial-v3',  # dashboard_dispatcher_branch_decomposition_continuation_trial_v3.DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE': '/dashboard-dispatcher-batch-strategy-checkpoint',  # dashboard_dispatcher_batch_strategy_checkpoint.DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep',  # dashboard_dispatcher_batch_decomposition_prep.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial',  # dashboard_dispatcher_batch_decomposition_trial.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V2_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v2',  # dashboard_dispatcher_batch_decomposition_checkpoint_v2.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V2_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v3',  # dashboard_dispatcher_batch_decomposition_prep_v3.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V3_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v3',  # dashboard_dispatcher_batch_decomposition_trial_v3.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V3_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V3_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v3',  # dashboard_dispatcher_batch_decomposition_checkpoint_v3.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V3_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V4_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v4',  # dashboard_dispatcher_batch_decomposition_prep_v4.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V4_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V4_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v4',  # dashboard_dispatcher_batch_decomposition_trial_v4.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V4_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V4_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v4',  # dashboard_dispatcher_batch_decomposition_checkpoint_v4.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V4_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v5',  # dashboard_dispatcher_batch_decomposition_prep_v5.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V5_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v5',  # dashboard_dispatcher_batch_decomposition_trial_v5.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V5_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v5',  # dashboard_dispatcher_batch_decomposition_checkpoint_v5.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v6',  # dashboard_dispatcher_batch_decomposition_prep_v6.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v6',  # dashboard_dispatcher_batch_decomposition_trial_v6.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v6',  # dashboard_dispatcher_batch_decomposition_checkpoint_v6.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V7_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v7',  # dashboard_dispatcher_batch_decomposition_prep_v7.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V7_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V7_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v7',  # dashboard_dispatcher_batch_decomposition_trial_v7.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V7_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v7',  # dashboard_dispatcher_batch_decomposition_checkpoint_v7.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v8',  # dashboard_dispatcher_batch_decomposition_prep_v8.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V8_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v8',  # dashboard_dispatcher_batch_decomposition_trial_v8.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V8_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V8_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v8',  # dashboard_dispatcher_batch_decomposition_checkpoint_v8.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V8_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V9_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v9',  # dashboard_dispatcher_batch_decomposition_prep_v9.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V9_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V9_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v9',  # dashboard_dispatcher_batch_decomposition_trial_v9.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V9_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V9_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v9',  # dashboard_dispatcher_batch_decomposition_checkpoint_v9.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V9_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v10',  # dashboard_dispatcher_batch_decomposition_prep_v10.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v10',  # dashboard_dispatcher_batch_decomposition_trial_v10.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V10_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v10',  # dashboard_dispatcher_batch_decomposition_checkpoint_v10.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V10_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V11_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v11',  # dashboard_dispatcher_batch_decomposition_prep_v11.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V11_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V11_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v11',  # dashboard_dispatcher_batch_decomposition_trial_v11.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V11_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V11_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v11',  # dashboard_dispatcher_batch_decomposition_checkpoint_v11.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V11_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v12',  # dashboard_dispatcher_batch_decomposition_prep_v12.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v12',  # dashboard_dispatcher_batch_decomposition_trial_v12.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v12',  # dashboard_dispatcher_batch_decomposition_checkpoint_v12.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE': '/dashboard-dispatcher-batch-decomposition-prep-v13',  # dashboard_dispatcher_batch_decomposition_prep_v13.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE': '/dashboard-dispatcher-batch-decomposition-trial-v13',  # dashboard_dispatcher_batch_decomposition_trial_v13.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE': '/dashboard-dispatcher-batch-decomposition-checkpoint-v13',  # dashboard_dispatcher_batch_decomposition_checkpoint_v13.DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE': '/dashboard-dispatcher-proof-surface-consolidation-prep-v1',  # dashboard_dispatcher_proof_surface_consolidation_prep_v1.DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE': '/dashboard-dispatcher-proof-surface',  # dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1.DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE': '/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1',  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1.DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1': ('/dashboard-dispatcher-batch-decomposition-checkpoint', '/dashboard-dispatcher-batch-decomposition-prep-v2', '/dashboard-dispatcher-batch-decomposition-trial-v2'),  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1.HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V1_ROUTE': '/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v1',  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1.ROUTE
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V2': ('/dashboard-dispatcher-batch-decomposition-checkpoint-v2', '/dashboard-dispatcher-batch-decomposition-prep-v3', '/dashboard-dispatcher-batch-decomposition-trial-v3', '/dashboard-dispatcher-batch-decomposition-checkpoint-v3', '/dashboard-dispatcher-batch-decomposition-prep-v4', '/dashboard-dispatcher-batch-decomposition-trial-v4', '/dashboard-dispatcher-batch-decomposition-checkpoint-v4', '/dashboard-dispatcher-batch-decomposition-prep-v5', '/dashboard-dispatcher-batch-decomposition-trial-v5', '/dashboard-dispatcher-batch-decomposition-checkpoint-v5'),  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2.HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V2
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V2_ROUTE': '/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v2',  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2.ROUTE
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3': ('/dashboard-dispatcher-batch-decomposition-prep-v6', '/dashboard-dispatcher-batch-decomposition-trial-v6', '/dashboard-dispatcher-batch-decomposition-checkpoint-v6', '/dashboard-dispatcher-batch-decomposition-prep-v7', '/dashboard-dispatcher-batch-decomposition-trial-v7', '/dashboard-dispatcher-batch-decomposition-checkpoint-v7', '/dashboard-dispatcher-batch-decomposition-prep-v8', '/dashboard-dispatcher-batch-decomposition-trial-v8', '/dashboard-dispatcher-batch-decomposition-checkpoint-v8', '/dashboard-dispatcher-batch-decomposition-prep-v9', '/dashboard-dispatcher-batch-decomposition-trial-v9', '/dashboard-dispatcher-batch-decomposition-checkpoint-v9'),  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3.HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V3_ROUTE': '/dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3',  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3.ROUTE
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_COMPLETION': ('/dashboard-dispatcher-batch-decomposition-prep-v10', '/dashboard-dispatcher-batch-decomposition-trial-v10', '/dashboard-dispatcher-batch-decomposition-checkpoint-v10', '/dashboard-dispatcher-batch-decomposition-prep-v11', '/dashboard-dispatcher-batch-decomposition-trial-v11', '/dashboard-dispatcher-batch-decomposition-checkpoint-v11', '/dashboard-dispatcher-batch-decomposition-prep-v12', '/dashboard-dispatcher-batch-decomposition-trial-v12', '/dashboard-dispatcher-batch-decomposition-checkpoint-v12', '/dashboard-dispatcher-batch-decomposition-prep-v13', '/dashboard-dispatcher-batch-decomposition-trial-v13', '/dashboard-dispatcher-batch-decomposition-checkpoint-v13'),  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1.HISTORICAL_COMPATIBILITY_ALIAS_BATCH_COMPLETION
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_COMPLETION_ROUTE': '/dashboard-dispatcher-proof-surface-historical-compatibility-migration-completion-v1',  # dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1.ROUTE
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_PREP_ROUTE': '/dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1',  # dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_v1.ROUTE
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_TRIAL_ROUTE': '/dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1',  # dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_v1.ROUTE
    'EVALUATION_SIGNALS': ('consecutive_use', 'restart_resume', 'provider_outage', 'provider_return', 'generation_interruption', 'failed_retry', 'completed_regeneration', 'explicit_resend', 'message_branch', 'response_preference', 'temporary_instruction', 'pinned_context', 'offline_intent', 'long_history', 'multi_tab', 'memory_correction', 'topic_transition', 'draft_continuity', 'scroll_anchor', 'jump_to_latest', 'context_inspection', 'search_navigation', 'memory_browse'),  # conversation_daily_evaluation_protocol.EVALUATION_SIGNALS
    'RATING_DIMENSIONS': ('continuity', 'relevance', 'tone', 'responsiveness', 'recovery', 'usability'),  # conversation_daily_evaluation_protocol.RATING_DIMENSIONS
    'STAGE_FILTER_LABELS': {'all': 'All', 'open': 'Open', 'needs_attention': 'Needs attention', 'ready_to_act': 'Ready to act', 'ready': 'Ready', 'active': 'Active', 'approval_required': 'Needs approval request', 'approval_pending': 'Approval pending', 'approved_ready': 'Approved, ready to run', 'approval_rejected': 'Approval rejected', 'approval_failed': 'Approval failed', 'recovery_needed': 'Recovery needed', 'blocked': 'Blocked', 'patch_proposed': 'Patch proposed', 'done': 'Done', 'cancelled': 'Cancelled', 'unknown': 'Unknown', 'stable_loop_followup': 'Stable-loop follow-ups'},  # task_lifecycle.STAGE_FILTER_LABELS
    'REVIEW_FILTER_LABELS': {'all': 'All', 'open': 'Open review queue', 'unreviewed': 'Unreviewed', 'reviewed': 'Reviewed', 'approved_for_live': 'Approved for live', 'approved_ready': 'Approved/live-ready', 'rejected': 'Rejected', 'superseded': 'Superseded', 'archived': 'Archived', 'preview': 'Preview runs', 'live': 'Live runs', 'failed': 'Attention / failed', 'cleanup_default': 'Cleanup candidates'},  # stable_loop_review.REVIEW_FILTER_LABELS
    'REVIEW_STATUS_LABELS': {'unreviewed': 'Unreviewed', 'reviewed': 'Reviewed', 'approved_for_live': 'Approved for live', 'rejected': 'Rejected', 'superseded': 'Superseded'},  # stable_loop_review.REVIEW_STATUS_LABELS
    'FINAL_DECISION_LABELS': {'undecided': 'Undecided', 'keep': 'Keep result', 'fix_forward': 'Fix forward', 'rollback': 'Rollback recommended', 'needs_review': 'Needs more review'},  # stable_loop_operator_notes.FINAL_DECISION_LABELS
    'DECISION_FILTER_LABELS': {'all': 'All decisions', 'open': 'Open decisions', 'undecided': 'Undecided', 'keep': 'Keep', 'fix_forward': 'Fix forward', 'rollback': 'Rollback', 'needs_review': 'Needs review', 'action_required': 'Action required', 'decided': 'Decided', 'complete': 'Checklist complete', 'incomplete': 'Checklist incomplete', 'cleanup_default': 'Cleanup candidates', 'archived': 'Archived'},  # stable_loop_decision_report.DECISION_FILTER_LABELS
    'FOLLOWUP_COMPLETION_FILTER_LABELS': {'all': 'All follow-up chains', 'action_required': 'Action-required decisions', 'missing_followups': 'Missing follow-up tasks', 'open': 'Open follow-up tasks', 'unresolved': 'Unresolved', 'ready_to_resolve': 'Ready to resolve', 'resolved': 'Resolved', 'archived': 'Archived', 'cleanup_default': 'Cleanup candidates'},  # stable_loop_followup_completion.FOLLOWUP_COMPLETION_FILTER_LABELS
}

DEFERRED_CONSTANT_SOURCES: dict[str, tuple[str, str]] = {
    'DASHBOARD_ROUTE_REGISTRY_ROUTE': ('dashboard_route_registry', 'DASHBOARD_ROUTE_REGISTRY_ROUTE'),
    'DASHBOARD_RENDERER_METADATA_ROUTE': ('dashboard_renderer_metadata', 'DASHBOARD_RENDERER_METADATA_ROUTE'),
    'DASHBOARD_DISPATCHER_PARITY_ROUTE': ('dashboard_dispatcher_parity', 'DASHBOARD_DISPATCHER_PARITY_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE': ('dashboard_dispatcher_branch_prep', 'DASHBOARD_DISPATCHER_BRANCH_PREP_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE': ('dashboard_dispatcher_branch_trial', 'DASHBOARD_DISPATCHER_BRANCH_TRIAL_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE': ('dashboard_dispatcher_branch_backfill', 'DASHBOARD_DISPATCHER_BRANCH_BACKFILL_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE': ('dashboard_dispatcher_branch_helper_consolidation', 'DASHBOARD_DISPATCHER_BRANCH_HELPER_CONSOLIDATION_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE': ('dashboard_dispatcher_branch_expansion_prep', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_PREP_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE': ('dashboard_dispatcher_branch_expansion_trial', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_TRIAL_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_ROUTE': ('dashboard_dispatcher_branch_expansion_backfill_prep', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_ROUTE': ('dashboard_dispatcher_branch_expansion_backfill_trial', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_ROUTE': ('dashboard_dispatcher_branch_expansion_backfill_prep_v2', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V2_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE': ('dashboard_dispatcher_branch_expansion_backfill_trial_v2', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V2_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_ROUTE': ('dashboard_dispatcher_branch_expansion_backfill_prep_v3', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_PREP_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE': ('dashboard_dispatcher_branch_expansion_backfill_trial_v3', 'DASHBOARD_DISPATCHER_BRANCH_EXPANSION_BACKFILL_TRIAL_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE': ('dashboard_dispatcher_branch_decomposition_hardening', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_HARDENING_ROUTE'),
    'EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE': ('eidolon_v1073_source_review_checkpoint', 'EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_ROUTE': ('dashboard_dispatcher_branch_decomposition_continuation_prep', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE': ('dashboard_dispatcher_branch_decomposition_continuation_trial', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V2_ROUTE': ('dashboard_dispatcher_branch_decomposition_continuation_prep_v2', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V2_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE': ('dashboard_dispatcher_branch_decomposition_continuation_trial_v2', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V2_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE': ('dashboard_dispatcher_branch_decomposition_continuation_prep_v3', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_PREP_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE': ('dashboard_dispatcher_branch_decomposition_continuation_trial_v3', 'DASHBOARD_DISPATCHER_BRANCH_DECOMPOSITION_CONTINUATION_TRIAL_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE': ('dashboard_dispatcher_batch_strategy_checkpoint', 'DASHBOARD_DISPATCHER_BATCH_STRATEGY_CHECKPOINT_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V2_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v2', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V2_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v3', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V3_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v3', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V3_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v3', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V3_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V4_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v4', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V4_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V4_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v4', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V4_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V4_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v4', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V4_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v5', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V5_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V5_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v5', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V5_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v5', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V5_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v6', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V6_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v6', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V6_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v6', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V6_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V7_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v7', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V7_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V7_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v7', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V7_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v7', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V7_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v8', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V8_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V8_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v8', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V8_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V8_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v8', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V8_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V9_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v9', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V9_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V9_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v9', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V9_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V9_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v9', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V9_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v10', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V10_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v10', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V10_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V10_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v10', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V10_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V11_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v11', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V11_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V11_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v11', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V11_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V11_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v11', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V11_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v12', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V12_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v12', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V12_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v12', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V12_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE': ('dashboard_dispatcher_batch_decomposition_prep_v13', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_PREP_V13_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE': ('dashboard_dispatcher_batch_decomposition_trial_v13', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_TRIAL_V13_ROUTE'),
    'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE': ('dashboard_dispatcher_batch_decomposition_checkpoint_v13', 'DASHBOARD_DISPATCHER_BATCH_DECOMPOSITION_CHECKPOINT_V13_ROUTE'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE': ('dashboard_dispatcher_proof_surface_consolidation_prep_v1', 'DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE': ('dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1', 'DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATED_RENDERER_TRIAL_V1_ROUTE'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1', 'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_PREP_V1_ROUTE'),
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1', 'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V1'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V1_ROUTE': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1', 'ROUTE'),
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V2': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2', 'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V2'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V2_ROUTE': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2', 'ROUTE'),
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3', 'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_V3'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_TRIAL_V3_ROUTE': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3', 'ROUTE'),
    'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_COMPLETION': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1', 'HISTORICAL_COMPATIBILITY_ALIAS_BATCH_COMPLETION'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_COMPATIBILITY_MIGRATION_COMPLETION_ROUTE': ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1', 'ROUTE'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_PREP_ROUTE': ('dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_v1', 'ROUTE'),
    'DASHBOARD_DISPATCHER_PROOF_SURFACE_HISTORICAL_SURFACE_RETIREMENT_TRIAL_ROUTE': ('dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_v1', 'ROUTE'),
    'EVALUATION_SIGNALS': ('conversation_daily_evaluation_protocol', 'EVALUATION_SIGNALS'),
    'RATING_DIMENSIONS': ('conversation_daily_evaluation_protocol', 'RATING_DIMENSIONS'),
    'STAGE_FILTER_LABELS': ('task_lifecycle', 'STAGE_FILTER_LABELS'),
    'REVIEW_FILTER_LABELS': ('stable_loop_review', 'REVIEW_FILTER_LABELS'),
    'REVIEW_STATUS_LABELS': ('stable_loop_review', 'REVIEW_STATUS_LABELS'),
    'FINAL_DECISION_LABELS': ('stable_loop_operator_notes', 'FINAL_DECISION_LABELS'),
    'DECISION_FILTER_LABELS': ('stable_loop_decision_report', 'DECISION_FILTER_LABELS'),
    'FOLLOWUP_COMPLETION_FILTER_LABELS': ('stable_loop_followup_completion', 'FOLLOWUP_COMPLETION_FILTER_LABELS'),
}

DEFERRED_EXPORTS: tuple[tuple[str, dict[str, str]], ...] = (
    ('dashboard_local_model', {
        '_render_local_model_status': 'render_local_model_status',
    }),
    ('provider_recovery_evidence', {
        'provider_resume_cue': 'provider_resume_cue',
    }),
    ('dashboard_dispatcher_branch_helpers', {
        'render_dashboard_dispatcher_branch_extraction_prep_backfill_branch': 'render_dashboard_dispatcher_branch_extraction_prep_backfill_branch',
        'render_dashboard_dispatcher_branch_extraction_trial_backfill_v2_branch': 'render_dashboard_dispatcher_branch_extraction_trial_backfill_v2_branch',
        'render_dashboard_dispatcher_branch_extraction_backfill_backfill_v3_branch': 'render_dashboard_dispatcher_branch_extraction_backfill_backfill_v3_branch',
        'render_smoke_check_helper_extraction_pilot_continuation_branch': 'render_smoke_check_helper_extraction_pilot_continuation_branch',
        'render_diagnostics_continuation_branch': 'render_diagnostics_continuation_branch',
        'render_settings_continuation_branch': 'render_settings_continuation_branch',
        'render_audited_sandbox_backend_preflight_contract_batch_branch': 'render_audited_sandbox_backend_preflight_contract_batch_branch',
        'render_sandbox_backend_capability_evidence_gate_batch_branch': 'render_sandbox_backend_capability_evidence_gate_batch_branch',
        'render_fixture_execution_admission_gate_batch_branch': 'render_fixture_execution_admission_gate_batch_branch',
        'render_sandboxed_fixture_execution_trial_batch_v2_branch': 'render_sandboxed_fixture_execution_trial_batch_v2_branch',
        'render_sandboxed_fixture_batch_execution_batch_v2_branch': 'render_sandboxed_fixture_batch_execution_batch_v2_branch',
        'render_generated_dispatch_promotion_readiness_ledger_batch_v2_branch': 'render_generated_dispatch_promotion_readiness_ledger_batch_v2_branch',
        'render_source_decomposition_batch_i_batch_v3_branch': 'render_source_decomposition_batch_i_batch_v3_branch',
        'render_autonomy_phase_zero_observation_contract_batch_v3_branch': 'render_autonomy_phase_zero_observation_contract_batch_v3_branch',
        'render_source_decomposition_batch_ii_batch_v3_branch': 'render_source_decomposition_batch_ii_batch_v3_branch',
        'render_dashboard_api_smoke_shared_utility_adoption_batch_v4_branch': 'render_dashboard_api_smoke_shared_utility_adoption_batch_v4_branch',
        'render_dashboard_review_component_extraction_pilot_batch_v4_branch': 'render_dashboard_review_component_extraction_pilot_batch_v4_branch',
        'render_api_preview_adapter_extraction_pilot_batch_v4_branch': 'render_api_preview_adapter_extraction_pilot_batch_v4_branch',
        'render_api_preview_adapter_backfill_batch_v5_branch': 'render_api_preview_adapter_backfill_batch_v5_branch',
        'render_api_server_dispatch_helper_extraction_pilot_batch_v5_branch': 'render_api_server_dispatch_helper_extraction_pilot_batch_v5_branch',
        'render_api_server_dispatch_helper_backfill_batch_v5_branch': 'render_api_server_dispatch_helper_backfill_batch_v5_branch',
        'render_api_server_dispatch_helper_route_table_extraction_batch_v6_branch': 'render_api_server_dispatch_helper_route_table_extraction_batch_v6_branch',
        'render_api_server_dispatch_route_table_backfill_batch_v6_branch': 'render_api_server_dispatch_route_table_backfill_batch_v6_branch',
        'render_api_server_dispatch_route_table_safety_parity_batch_v6_branch': 'render_api_server_dispatch_route_table_safety_parity_batch_v6_branch',
        'render_audited_sandbox_backend_evidence_interface_batch_v7_branch': 'render_audited_sandbox_backend_evidence_interface_batch_v7_branch',
        'render_dashboard_dispatcher_branch_helper_consolidation_batch_v7_branch': 'render_dashboard_dispatcher_branch_helper_consolidation_batch_v7_branch',
        'render_dashboard_dispatcher_branch_extraction_expansion_prep_batch_v7_branch': 'render_dashboard_dispatcher_branch_extraction_expansion_prep_batch_v7_branch',
        'render_dashboard_dispatcher_branch_expansion_trial_batch_v8_branch': 'render_dashboard_dispatcher_branch_expansion_trial_batch_v8_branch',
        'render_dashboard_dispatcher_branch_expansion_backfill_prep_batch_v8_branch': 'render_dashboard_dispatcher_branch_expansion_backfill_prep_batch_v8_branch',
        'render_dashboard_dispatcher_branch_expansion_backfill_trial_batch_v8_branch': 'render_dashboard_dispatcher_branch_expansion_backfill_trial_batch_v8_branch',
        'render_dashboard_dispatcher_branch_expansion_backfill_prep_v2_batch_v9_branch': 'render_dashboard_dispatcher_branch_expansion_backfill_prep_v2_batch_v9_branch',
        'render_dashboard_dispatcher_branch_expansion_backfill_trial_v2_batch_v9_branch': 'render_dashboard_dispatcher_branch_expansion_backfill_trial_v2_batch_v9_branch',
        'render_dashboard_dispatcher_branch_expansion_backfill_prep_v3_batch_v9_branch': 'render_dashboard_dispatcher_branch_expansion_backfill_prep_v3_batch_v9_branch',
        'render_dashboard_dispatcher_branch_expansion_backfill_trial_v3_batch_v10_branch': 'render_dashboard_dispatcher_branch_expansion_backfill_trial_v3_batch_v10_branch',
        'render_dashboard_dispatcher_branch_decomposition_hardening_batch_v10_branch': 'render_dashboard_dispatcher_branch_decomposition_hardening_batch_v10_branch',
        'render_eidolon_v1073_source_review_checkpoint_batch_v10_branch': 'render_eidolon_v1073_source_review_checkpoint_batch_v10_branch',
        'render_dashboard_dispatcher_branch_decomposition_continuation_prep_batch_v11_branch': 'render_dashboard_dispatcher_branch_decomposition_continuation_prep_batch_v11_branch',
        'render_dashboard_dispatcher_branch_decomposition_continuation_trial_batch_v11_branch': 'render_dashboard_dispatcher_branch_decomposition_continuation_trial_batch_v11_branch',
        'render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_batch_v11_branch': 'render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_batch_v11_branch',
        'render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_batch_v12_branch': 'render_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_batch_v12_branch',
        'render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_batch_v12_branch': 'render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_batch_v12_branch',
        'render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_batch_v12_branch': 'render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_batch_v12_branch',
        'render_dashboard_dispatcher_batch_strategy_checkpoint_batch_v13_branch': 'render_dashboard_dispatcher_batch_strategy_checkpoint_batch_v13_branch',
        'render_dashboard_dispatcher_batch_decomposition_prep_batch_v13_branch': 'render_dashboard_dispatcher_batch_decomposition_prep_batch_v13_branch',
        'render_dashboard_dispatcher_batch_decomposition_trial_batch_v13_branch': 'render_dashboard_dispatcher_batch_decomposition_trial_batch_v13_branch',
    }),
    ('dashboard_shell_components', {
        'render_card_component': 'render_card_component',
        'render_text_block_component': 'render_text_block_component',
    }),
    ('dashboard_route_registry', {
        'build_dashboard_route_registry_extraction_report': 'build_dashboard_route_registry_extraction_report',
        'dashboard_route_registry_extraction_text': 'dashboard_route_registry_extraction_text',
        'dashboard_route_registry_nav_items': 'dashboard_route_registry_nav_items',
    }),
    ('dashboard_renderer_metadata', {
        'build_dashboard_renderer_metadata_extraction_report': 'build_dashboard_renderer_metadata_extraction_report',
        'dashboard_renderer_metadata_extraction_text': 'dashboard_renderer_metadata_extraction_text',
    }),
    ('dashboard_dispatcher_parity', {
        'build_dashboard_dispatcher_parity_report': 'build_dashboard_dispatcher_parity_report',
        'dashboard_dispatcher_parity_text': 'dashboard_dispatcher_parity_text',
    }),
    ('dashboard_dispatcher_branch_prep', {
        'build_dashboard_dispatcher_branch_extraction_prep_report': 'build_dashboard_dispatcher_branch_extraction_prep_report',
        'dashboard_dispatcher_branch_extraction_prep_text': 'dashboard_dispatcher_branch_extraction_prep_text',
    }),
    ('dashboard_dispatcher_branch_trial', {
        'build_dashboard_dispatcher_branch_extraction_trial_report': 'build_dashboard_dispatcher_branch_extraction_trial_report',
        'dashboard_dispatcher_branch_extraction_trial_text': 'dashboard_dispatcher_branch_extraction_trial_text',
        'render_dashboard_route_registry_extraction_trial_branch': 'render_dashboard_route_registry_extraction_trial_branch',
    }),
    ('dashboard_dispatcher_branch_backfill', {
        'build_dashboard_dispatcher_branch_extraction_backfill_report': 'build_dashboard_dispatcher_branch_extraction_backfill_report',
        'dashboard_dispatcher_branch_extraction_backfill_text': 'dashboard_dispatcher_branch_extraction_backfill_text',
        'render_dashboard_renderer_metadata_extraction_backfill_branch': 'render_dashboard_renderer_metadata_extraction_backfill_branch',
    }),
    ('dashboard_dispatcher_branch_helper_consolidation', {
        'build_dashboard_dispatcher_branch_helper_consolidation_report': 'build_dashboard_dispatcher_branch_helper_consolidation_report',
        'dashboard_dispatcher_branch_helper_consolidation_text': 'dashboard_dispatcher_branch_helper_consolidation_text',
    }),
    ('dashboard_dispatcher_branch_expansion_prep', {
        'build_dashboard_dispatcher_branch_extraction_expansion_prep_report': 'build_dashboard_dispatcher_branch_extraction_expansion_prep_report',
        'dashboard_dispatcher_branch_extraction_expansion_prep_text': 'dashboard_dispatcher_branch_extraction_expansion_prep_text',
    }),
    ('dashboard_dispatcher_branch_expansion_trial', {
        'build_dashboard_dispatcher_branch_expansion_trial_report': 'build_dashboard_dispatcher_branch_expansion_trial_report',
        'dashboard_dispatcher_branch_expansion_trial_text': 'dashboard_dispatcher_branch_expansion_trial_text',
        'render_dashboard_dispatcher_parity_expansion_trial_branch': 'render_dashboard_dispatcher_parity_expansion_trial_branch',
    }),
    ('dashboard_dispatcher_branch_expansion_backfill_prep', {
        'build_dashboard_dispatcher_branch_expansion_backfill_prep_report': 'build_dashboard_dispatcher_branch_expansion_backfill_prep_report',
        'dashboard_dispatcher_branch_expansion_backfill_prep_text': 'dashboard_dispatcher_branch_expansion_backfill_prep_text',
    }),
    ('dashboard_dispatcher_branch_expansion_backfill_trial', {
        'build_dashboard_dispatcher_branch_expansion_backfill_trial_report': 'build_dashboard_dispatcher_branch_expansion_backfill_trial_report',
        'dashboard_dispatcher_branch_expansion_backfill_trial_text': 'dashboard_dispatcher_branch_expansion_backfill_trial_text',
    }),
    ('dashboard_dispatcher_branch_expansion_backfill_prep_v2', {
        'build_dashboard_dispatcher_branch_expansion_backfill_prep_v2_report': 'build_dashboard_dispatcher_branch_expansion_backfill_prep_v2_report',
        'dashboard_dispatcher_branch_expansion_backfill_prep_v2_text': 'dashboard_dispatcher_branch_expansion_backfill_prep_v2_text',
    }),
    ('dashboard_dispatcher_branch_expansion_backfill_trial_v2', {
        'build_dashboard_dispatcher_branch_expansion_backfill_trial_v2_report': 'build_dashboard_dispatcher_branch_expansion_backfill_trial_v2_report',
        'dashboard_dispatcher_branch_expansion_backfill_trial_v2_text': 'dashboard_dispatcher_branch_expansion_backfill_trial_v2_text',
    }),
    ('dashboard_dispatcher_branch_expansion_backfill_prep_v3', {
        'build_dashboard_dispatcher_branch_expansion_backfill_prep_v3_report': 'build_dashboard_dispatcher_branch_expansion_backfill_prep_v3_report',
        'dashboard_dispatcher_branch_expansion_backfill_prep_v3_text': 'dashboard_dispatcher_branch_expansion_backfill_prep_v3_text',
    }),
    ('dashboard_dispatcher_branch_expansion_backfill_trial_v3', {
        'build_dashboard_dispatcher_branch_expansion_backfill_trial_v3_report': 'build_dashboard_dispatcher_branch_expansion_backfill_trial_v3_report',
        'dashboard_dispatcher_branch_expansion_backfill_trial_v3_text': 'dashboard_dispatcher_branch_expansion_backfill_trial_v3_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_hardening', {
        'build_dashboard_dispatcher_branch_decomposition_hardening_report': 'build_dashboard_dispatcher_branch_decomposition_hardening_report',
        'dashboard_dispatcher_branch_decomposition_hardening_text': 'dashboard_dispatcher_branch_decomposition_hardening_text',
    }),
    ('eidolon_v1073_source_review_checkpoint', {
        'build_eidolon_v1073_source_review_checkpoint_report': 'build_eidolon_v1073_source_review_checkpoint_report',
        'eidolon_v1073_source_review_checkpoint_text': 'eidolon_v1073_source_review_checkpoint_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_continuation_prep', {
        'build_dashboard_dispatcher_branch_decomposition_continuation_prep_report': 'build_dashboard_dispatcher_branch_decomposition_continuation_prep_report',
        'dashboard_dispatcher_branch_decomposition_continuation_prep_text': 'dashboard_dispatcher_branch_decomposition_continuation_prep_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_continuation_trial', {
        'build_dashboard_dispatcher_branch_decomposition_continuation_trial_report': 'build_dashboard_dispatcher_branch_decomposition_continuation_trial_report',
        'dashboard_dispatcher_branch_decomposition_continuation_trial_text': 'dashboard_dispatcher_branch_decomposition_continuation_trial_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_continuation_prep_v2', {
        'build_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_report': 'build_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_report',
        'dashboard_dispatcher_branch_decomposition_continuation_prep_v2_text': 'dashboard_dispatcher_branch_decomposition_continuation_prep_v2_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_continuation_trial_v2', {
        'build_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_report': 'build_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_report',
        'dashboard_dispatcher_branch_decomposition_continuation_trial_v2_text': 'dashboard_dispatcher_branch_decomposition_continuation_trial_v2_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_continuation_prep_v3', {
        'build_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_report': 'build_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_report',
        'dashboard_dispatcher_branch_decomposition_continuation_prep_v3_text': 'dashboard_dispatcher_branch_decomposition_continuation_prep_v3_text',
    }),
    ('dashboard_dispatcher_branch_decomposition_continuation_trial_v3', {
        'build_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_report': 'build_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_report',
        'dashboard_dispatcher_branch_decomposition_continuation_trial_v3_text': 'dashboard_dispatcher_branch_decomposition_continuation_trial_v3_text',
    }),
    ('dashboard_dispatcher_batch_strategy_checkpoint', {
        'build_dashboard_dispatcher_batch_strategy_checkpoint_report': 'build_dashboard_dispatcher_batch_strategy_checkpoint_report',
        'dashboard_dispatcher_batch_strategy_checkpoint_text': 'dashboard_dispatcher_batch_strategy_checkpoint_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep', {
        'build_dashboard_dispatcher_batch_decomposition_prep_report': 'build_dashboard_dispatcher_batch_decomposition_prep_report',
        'dashboard_dispatcher_batch_decomposition_prep_text': 'dashboard_dispatcher_batch_decomposition_prep_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial', {
        'build_dashboard_dispatcher_batch_decomposition_trial_report': 'build_dashboard_dispatcher_batch_decomposition_trial_report',
        'dashboard_dispatcher_batch_decomposition_trial_text': 'dashboard_dispatcher_batch_decomposition_trial_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v2', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v2_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v2_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v2_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v2_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v3', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v3_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v3_report',
        'dashboard_dispatcher_batch_decomposition_prep_v3_text': 'dashboard_dispatcher_batch_decomposition_prep_v3_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v3', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v3_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v3_report',
        'dashboard_dispatcher_batch_decomposition_trial_v3_text': 'dashboard_dispatcher_batch_decomposition_trial_v3_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v3', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v3_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v3_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v3_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v3_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v4', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v4_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v4_report',
        'dashboard_dispatcher_batch_decomposition_prep_v4_text': 'dashboard_dispatcher_batch_decomposition_prep_v4_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v4', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v4_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v4_report',
        'dashboard_dispatcher_batch_decomposition_trial_v4_text': 'dashboard_dispatcher_batch_decomposition_trial_v4_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v4', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v4_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v4_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v4_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v4_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v5', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v5_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v5_report',
        'dashboard_dispatcher_batch_decomposition_prep_v5_text': 'dashboard_dispatcher_batch_decomposition_prep_v5_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v5', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v5_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v5_report',
        'dashboard_dispatcher_batch_decomposition_trial_v5_text': 'dashboard_dispatcher_batch_decomposition_trial_v5_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v5', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v5_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v5_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v5_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v5_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v6', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v6_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v6_report',
        'dashboard_dispatcher_batch_decomposition_prep_v6_text': 'dashboard_dispatcher_batch_decomposition_prep_v6_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v6', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v6_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v6_report',
        'dashboard_dispatcher_batch_decomposition_trial_v6_text': 'dashboard_dispatcher_batch_decomposition_trial_v6_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v6', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v6_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v6_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v6_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v6_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v7', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v7_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v7_report',
        'dashboard_dispatcher_batch_decomposition_prep_v7_text': 'dashboard_dispatcher_batch_decomposition_prep_v7_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v7', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v7_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v7_report',
        'dashboard_dispatcher_batch_decomposition_trial_v7_text': 'dashboard_dispatcher_batch_decomposition_trial_v7_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v7', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v7_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v7_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v7_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v7_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v8', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v8_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v8_report',
        'dashboard_dispatcher_batch_decomposition_prep_v8_text': 'dashboard_dispatcher_batch_decomposition_prep_v8_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v8', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v8_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v8_report',
        'dashboard_dispatcher_batch_decomposition_trial_v8_text': 'dashboard_dispatcher_batch_decomposition_trial_v8_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v8', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v8_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v8_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v8_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v8_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v9', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v9_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v9_report',
        'dashboard_dispatcher_batch_decomposition_prep_v9_text': 'dashboard_dispatcher_batch_decomposition_prep_v9_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v9', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v9_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v9_report',
        'dashboard_dispatcher_batch_decomposition_trial_v9_text': 'dashboard_dispatcher_batch_decomposition_trial_v9_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v9', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v9_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v9_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v9_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v9_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v10', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v10_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v10_report',
        'dashboard_dispatcher_batch_decomposition_prep_v10_text': 'dashboard_dispatcher_batch_decomposition_prep_v10_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v10', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v10_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v10_report',
        'dashboard_dispatcher_batch_decomposition_trial_v10_text': 'dashboard_dispatcher_batch_decomposition_trial_v10_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v10', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v10_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v10_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v10_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v10_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v11', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v11_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v11_report',
        'dashboard_dispatcher_batch_decomposition_prep_v11_text': 'dashboard_dispatcher_batch_decomposition_prep_v11_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v11', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v11_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v11_report',
        'dashboard_dispatcher_batch_decomposition_trial_v11_text': 'dashboard_dispatcher_batch_decomposition_trial_v11_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v11', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v11_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v11_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v11_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v11_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v12', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v12_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v12_report',
        'dashboard_dispatcher_batch_decomposition_prep_v12_text': 'dashboard_dispatcher_batch_decomposition_prep_v12_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v12', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v12_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v12_report',
        'dashboard_dispatcher_batch_decomposition_trial_v12_text': 'dashboard_dispatcher_batch_decomposition_trial_v12_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v12', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v12_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v12_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v12_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v12_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_prep_v13', {
        'build_dashboard_dispatcher_batch_decomposition_prep_v13_report': 'build_dashboard_dispatcher_batch_decomposition_prep_v13_report',
        'dashboard_dispatcher_batch_decomposition_prep_v13_text': 'dashboard_dispatcher_batch_decomposition_prep_v13_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_trial_v13', {
        'build_dashboard_dispatcher_batch_decomposition_trial_v13_report': 'build_dashboard_dispatcher_batch_decomposition_trial_v13_report',
        'dashboard_dispatcher_batch_decomposition_trial_v13_text': 'dashboard_dispatcher_batch_decomposition_trial_v13_text',
    }),
    ('dashboard_dispatcher_batch_decomposition_checkpoint_v13', {
        'build_dashboard_dispatcher_batch_decomposition_checkpoint_v13_report': 'build_dashboard_dispatcher_batch_decomposition_checkpoint_v13_report',
        'dashboard_dispatcher_batch_decomposition_checkpoint_v13_text': 'dashboard_dispatcher_batch_decomposition_checkpoint_v13_text',
    }),
    ('dashboard_dispatcher_proof_surface_consolidation_prep_v1', {
        'build_dashboard_dispatcher_proof_surface_consolidation_prep_v1_report': 'build_dashboard_dispatcher_proof_surface_consolidation_prep_v1_report',
        'dashboard_dispatcher_proof_surface_consolidation_prep_v1_text': 'dashboard_dispatcher_proof_surface_consolidation_prep_v1_text',
    }),
    ('dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1', {
        'build_dashboard_dispatcher_proof_surface_selection': 'build_dashboard_dispatcher_proof_surface_selection',
        'build_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_report': 'build_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_report',
        'dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_text': 'dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1', {
        'build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_report': 'build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_report',
        'dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_text': 'dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1', {
        'build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1_report': 'build_report',
        'dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1_text': 'report_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2', {
        'build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2_report': 'build_report',
        'dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2_text': 'report_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3', {
        'build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_report': 'build_report',
        'dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_text': 'report_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1', {
        'build_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_report': 'build_report',
        'dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_text': 'report_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_v1', {
        'build_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_report': 'build_report',
        'dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_text': 'report_text',
    }),
    ('dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_v1', {
        'build_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_report': 'build_report',
        'dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_text': 'report_text',
    }),
    ('approval_manager', {
        'approve_approval': 'approve_approval',
        'approval_text': 'approval_text',
        'get_approval': 'get_approval',
        'list_approvals': 'list_approvals',
        'reject_approval': 'reject_approval',
    }),
    ('conversation_action_portal', {
        'build_action_portal_state': 'build_action_portal_state',
    }),
    ('chat_action_router', {
        'propose_chat_action': 'propose_chat_action',
        'execute_chat_action': 'execute_chat_action',
        'list_chat_actions': 'list_chat_actions',
        'load_chat_action': 'load_chat_action',
        'chat_action_text': 'chat_action_text',
    }),
    ('conversation_daily_evaluation', {
        'finish_daily_evaluation': 'finish_daily_evaluation',
        'load_daily_evaluation': 'load_daily_evaluation',
        'record_operator_observation': 'record_operator_observation',
        'start_daily_evaluation': 'start_daily_evaluation',
    }),
    ('desktop_shell', {
        'desktop_status_text': 'desktop_status_text',
    }),
    ('desktop_setup_helper', {
        'create_setup_report': 'create_setup_report',
        'list_setup_reports': 'list_setup_reports',
        'load_setup_report': 'load_setup_report',
        'setup_report_text': 'setup_report_text',
    }),
    ('desktop_onboarding_wizard', {
        'build_onboarding_run': 'build_onboarding_run',
        'list_onboarding_runs': 'list_onboarding_runs',
        'load_onboarding_run': 'load_onboarding_run',
        'onboarding_run_text': 'onboarding_run_text',
    }),
    ('diagnostics', {
        'build_diagnostic_report': 'build_diagnostic_report',
        'diagnostic_report_text': 'diagnostic_report_text',
        'list_diagnostic_reports': 'list_diagnostic_reports',
        'load_diagnostic_report': 'load_diagnostic_report',
        'save_diagnostic_report': 'save_diagnostic_report',
    }),
    ('goal_manager', {
        'add_goal': 'add_goal',
        'get_goal': 'get_goal',
        'list_goals': 'list_goals',
    }),
    ('maintenance_advisor', {
        'list_maintenance_scans': 'list_maintenance_scans',
        'load_maintenance_scan': 'load_maintenance_scan',
        'maintenance_scan_text': 'maintenance_scan_text',
        'run_maintenance_scan': 'run_maintenance_scan',
    }),
    ('notification_manager', {
        'clear_dismissed_notifications': 'clear_dismissed_notifications',
        'list_notifications': 'list_notifications',
        'load_notification': 'load_notification',
        'notification_text': 'notification_text',
        'update_notification_status': 'update_notification_status',
    }),
    ('memory', {
        'load_memories': 'load_memories',
    }),
    ('memory_compactor', {
        'list_memory_summaries': 'list_memory_summaries',
        'load_memory_summary': 'load_memory_summary',
        'memory_status_text': 'memory_status_text',
        'memory_summary_text': 'memory_summary_text',
    }),
    ('patch_suggester', {
        'list_patch_proposals': 'list_patch_proposals',
        'load_patch_proposal': 'load_patch_proposal',
        'patch_proposal_text': 'patch_proposal_text',
        'suggest_patch': 'suggest_patch',
    }),
    ('work_queue_patch_bridge', {
        'create_patch_followup_items': 'create_patch_followup_items',
        'create_patch_work_item': 'create_patch_work_item',
        'suggest_patch_for_work_item': 'suggest_patch_for_work_item',
    }),
    ('project_manager', {
        'get_active_project': 'get_active_project',
    }),
    ('session_planner', {
        'create_session_plan': 'create_session_plan',
        'list_session_plans': 'list_session_plans',
        'load_session_plan': 'load_session_plan',
        'session_plan_text': 'session_plan_text',
    }),
    ('settings_manager', {
        'get_setting': 'get_setting',
        'load_settings': 'load_settings',
        'set_setting': 'set_setting',
        'settings_health': 'settings_health',
        'settings_text': 'settings_text',
    }),
    ('task_queue', {
        'add_task': 'add_task',
        'get_task': 'get_task',
        'list_tasks': 'list_tasks',
        'next_task': 'next_task',
        'task_detail_text': 'task_detail_text',
        'task_status_counts': 'task_status_counts',
    }),
    ('work_queue', {
        'add_work_item': 'add_work_item',
        'find_work_item': 'find_work_item',
        'format_work_item': 'format_work_item',
        'list_work_items': 'list_work_items',
        'summarize_queue': 'summarize_queue',
        'update_work_item': 'update_work_item',
    }),
    ('task_work_executor', {
        'execute_next_task_work': 'execute_next_task_work',
        'execute_task_work_item': 'execute_task_work_item',
        'task_work_execution_text': 'task_work_execution_text',
    }),
    ('task_approval_bridge', {
        'request_task_work_approval': 'request_task_work_approval',
        'task_approvals_text': 'task_approvals_text',
    }),
    ('task_lifecycle', {
        'derive_task_lifecycle': 'derive_task_lifecycle',
        'lifecycle_stage_matches': 'lifecycle_stage_matches',
        'list_task_lifecycles': 'list_task_lifecycles',
        'normalize_lifecycle_stage_filter': 'normalize_lifecycle_stage_filter',
        'task_lifecycle_summary': 'task_lifecycle_summary',
        'task_lifecycle_text': 'task_lifecycle_text',
    }),
    ('task_recovery', {
        'build_task_recovery': 'build_task_recovery',
        'mark_task_ready_for_retry': 'mark_task_ready_for_retry',
        'retry_task_work': 'retry_task_work',
        'task_recovery_summary': 'task_recovery_summary',
        'task_recovery_text': 'task_recovery_text',
    }),
    ('work_cycle', {
        'run_supervised_work_cycle': 'run_supervised_work_cycle',
        'list_work_cycles': 'list_work_cycles',
        'load_work_cycle': 'load_work_cycle',
        'work_cycle_text': 'work_cycle_text',
    }),
    ('stable_supervised_loop', {
        'build_stable_loop_preflight': 'build_stable_loop_preflight',
        'list_stable_loops': 'list_stable_loops',
        'load_stable_loop': 'load_stable_loop',
        'run_stable_supervised_loop': 'run_stable_supervised_loop',
        'stable_loop_text': 'stable_loop_text',
        'stable_preflight_text': 'stable_preflight_text',
    }),
    ('stable_loop_review', {
        'cleanup_stable_loop_history': 'cleanup_stable_loop_history',
        'list_stable_loop_reviews': 'list_stable_loop_reviews',
        'loop_is_archived': 'loop_is_archived',
        'loop_is_live_ready': 'loop_is_live_ready',
        'normalize_review_filter': 'normalize_review_filter',
        'review_label_for_loop': 'review_label_for_loop',
        'review_status_for_loop': 'review_status_for_loop',
        'run_approved_stable_loop_live': 'run_approved_stable_loop_live',
        'set_stable_loop_archived': 'set_stable_loop_archived',
        'stable_loop_review_summary': 'stable_loop_review_summary',
        'stable_loop_review_text': 'stable_loop_review_text',
        'update_stable_loop_review': 'update_stable_loop_review',
    }),
    ('stable_loop_audit', {
        'refresh_stable_loop_audit': 'refresh_stable_loop_audit',
        'stable_loop_audit_text': 'stable_loop_audit_text',
    }),
    ('stable_loop_operator_notes', {
        'add_stable_loop_operator_note': 'add_stable_loop_operator_note',
        'get_stable_loop_operator_notes': 'get_stable_loop_operator_notes',
        'set_stable_loop_final_decision': 'set_stable_loop_final_decision',
        'stable_loop_operator_notes_text': 'stable_loop_operator_notes_text',
        'update_stable_loop_check': 'update_stable_loop_check',
    }),
    ('stable_loop_decision_report', {
        'cleanup_stable_loop_decision_history': 'cleanup_stable_loop_decision_history',
        'list_stable_loop_decision_rows': 'list_stable_loop_decision_rows',
        'normalize_decision_filter': 'normalize_decision_filter',
        'stable_loop_decision_row': 'stable_loop_decision_row',
        'stable_loop_decision_summary': 'stable_loop_decision_summary',
        'stable_loop_decision_report_text': 'stable_loop_decision_report_text',
    }),
    ('stable_loop_followup_tasks', {
        'create_stable_loop_followup_tasks': 'create_stable_loop_followup_tasks',
        'create_stable_loop_followups_for_decisions': 'create_stable_loop_followups_for_decisions',
        'stable_loop_followup_summary': 'stable_loop_followup_summary',
        'followup_result_text': 'followup_result_text',
        'followup_batch_text': 'followup_batch_text',
    }),
    ('stable_loop_followup_lifecycle', {
        'followup_lifecycle_summary_text': 'followup_lifecycle_summary_text',
        'followup_resolution_text': 'followup_resolution_text',
        'list_stable_loop_followup_task_rows': 'list_stable_loop_followup_task_rows',
        'resolve_stable_loop_followups': 'resolve_stable_loop_followups',
        'resolve_task_stable_loop_followup': 'resolve_task_stable_loop_followup',
        'stable_loop_followup_lifecycle_summary': 'stable_loop_followup_lifecycle_summary',
        'stable_loop_followup_task_text': 'stable_loop_followup_task_text',
    }),
    ('stable_loop_followup_completion', {
        'cleanup_stable_loop_followup_completions': 'cleanup_stable_loop_followup_completions',
        'mark_stable_loop_followup_chain_closed': 'mark_stable_loop_followup_chain_closed',
        'normalize_followup_completion_filter': 'normalize_followup_completion_filter',
        'stable_loop_followup_completion_cleanup_text': 'stable_loop_followup_completion_cleanup_text',
        'stable_loop_followup_completion_report_text': 'stable_loop_followup_completion_report_text',
        'stable_loop_followup_completion_summary': 'stable_loop_followup_completion_summary',
        'stable_loop_followup_completion_row': 'stable_loop_followup_completion_row',
        'stable_loop_followup_closure_text': 'stable_loop_followup_closure_text',
    }),
    ('stable_loop_guardrails', {
        'stable_loop_guardrail_summary': 'stable_loop_guardrail_summary',
        'stable_loop_guardrails_text': 'stable_loop_guardrails_text',
    }),
    ('stabilization_checkpoint', {
        'build_stabilization_checkpoint': 'build_stabilization_checkpoint',
        'build_stabilization_dashboard_summary': 'build_stabilization_dashboard_summary',
        'stabilization_checkpoint_text': 'stabilization_checkpoint_text',
    }),
    ('controlled_build_cycle', {
        'build_controlled_task_selection': 'build_controlled_task_selection',
        'build_patch_plan': 'build_patch_plan',
        'patch_workspace_status': 'patch_workspace_status',
        'preview_staged_diff': 'preview_staged_diff',
        'readme_gate': 'readme_gate',
        'build_controlled_build_cycle': 'build_controlled_build_cycle',
        'build_supervised_dev_loop': 'build_supervised_dev_loop',
        'controlled_task_selection_text': 'controlled_task_selection_text',
        'patch_plan_text': 'patch_plan_text',
        'workspace_status_text': 'workspace_status_text',
        'diff_preview_text': 'diff_preview_text',
        'readme_gate_text': 'readme_gate_text',
        'controlled_build_cycle_text': 'controlled_build_cycle_text',
        'supervised_dev_loop_text': 'supervised_dev_loop_text',
    }),
    ('project_intelligence', {
        'build_codebase_map': 'build_codebase_map',
        'build_task_dependencies': 'build_task_dependencies',
        'build_test_plan': 'build_test_plan',
        'build_patch_risk': 'build_patch_risk',
        'build_patch_review': 'build_patch_review',
        'build_project_memory_index': 'build_project_memory_index',
        'build_workspace_status': 'build_workspace_status',
        'build_cross_project_task_review': 'build_cross_project_task_review',
        'build_asymmetric_dev_loop': 'build_asymmetric_dev_loop',
        'codebase_map_text': 'codebase_map_text',
        'task_dependencies_text': 'task_dependencies_text',
        'test_plan_text': 'test_plan_text',
        'patch_risk_text': 'patch_risk_text',
        'patch_review_text': 'patch_review_text',
        'project_memory_index_text': 'project_memory_index_text',
        'intelligence_workspace_status_text': 'workspace_status_text',
        'cross_project_task_review_text': 'cross_project_task_review_text',
        'asymmetric_dev_loop_text': 'asymmetric_dev_loop_text',
    }),
    ('workspace_orchestration', {
        'build_project_registry': 'build_project_registry',
        'build_project_health': 'build_project_health',
        'build_command_profiles': 'build_command_profiles',
        'build_workspace_dependency_map': 'build_workspace_dependency_map',
        'build_workspace_task_inbox': 'build_workspace_task_inbox',
        'build_project_context': 'build_project_context',
        'build_workspace_timeline': 'build_workspace_timeline',
        'build_workspace_dev_loop': 'build_workspace_dev_loop',
        'project_registry_text': 'project_registry_text',
        'project_health_text': 'project_health_text',
        'command_profiles_text': 'command_profiles_text',
        'workspace_dependency_map_text': 'workspace_dependency_map_text',
        'workspace_task_inbox_text': 'workspace_task_inbox_text',
        'project_context_text': 'project_context_text',
        'workspace_timeline_text': 'workspace_timeline_text',
        'workspace_dev_loop_text': 'workspace_dev_loop_text',
    }),
    ('workspace_execution', {
        'build_workspace_registry_audit': 'build_workspace_registry_audit',
        'build_workspace_repair_suggestions': 'build_workspace_repair_suggestions',
        'build_project_boundary_check': 'build_project_boundary_check',
        'build_workspace_patch_plan': 'build_workspace_patch_plan',
        'build_workspace_preview_diff': 'build_workspace_preview_diff',
        'build_workspace_verify_latest': 'build_workspace_verify_latest',
        'build_guarded_workspace_dev_loop': 'build_guarded_workspace_dev_loop',
        'workspace_registry_audit_text': 'workspace_registry_audit_text',
        'workspace_repair_suggestions_text': 'workspace_repair_suggestions_text',
        'project_boundary_check_text': 'project_boundary_check_text',
        'workspace_patch_plan_text': 'workspace_patch_plan_text',
        'workspace_preview_diff_text': 'workspace_preview_diff_text',
        'workspace_verify_latest_text': 'workspace_verify_latest_text',
        'guarded_workspace_dev_loop_text': 'guarded_workspace_dev_loop_text',
    }),
    ('patch_drafting', {
        'build_patch_draft_request': 'build_patch_draft_request',
        'build_draft_patch': 'build_draft_patch',
        'build_patch_draft_status': 'build_patch_draft_status',
        'build_patch_review_notes': 'build_patch_review_notes',
        'build_draft_diff': 'build_draft_diff',
        'build_draft_test_impact': 'build_draft_test_impact',
        'build_approval_gate': 'build_approval_gate',
        'build_apply_approved_draft': 'build_apply_approved_draft',
        'build_rollback_approved_draft': 'build_rollback_approved_draft',
        'build_human_approved_patch_loop': 'build_human_approved_patch_loop',
        'build_draft_quality': 'build_draft_quality',
        'build_draft_file_targets': 'build_draft_file_targets',
        'build_draft_intent_blocks': 'build_draft_intent_blocks',
        'build_draft_conflicts': 'build_draft_conflicts',
        'build_draft_verification_bundle': 'build_draft_verification_bundle',
        'build_draft_review_checklist': 'build_draft_review_checklist',
        'build_approved_draft_execution_report': 'build_approved_draft_execution_report',
        'build_review_centered_patch_loop': 'build_review_centered_patch_loop',
        'patch_draft_request_text': 'patch_draft_request_text',
        'draft_patch_text': 'draft_patch_text',
        'patch_draft_status_text': 'patch_draft_status_text',
        'patch_review_notes_text': 'patch_review_notes_text',
        'draft_diff_text': 'draft_diff_text',
        'draft_test_impact_text': 'draft_test_impact_text',
        'approval_gate_text': 'approval_gate_text',
        'apply_approved_draft_text': 'apply_approved_draft_text',
        'draft_rollback_text': 'draft_rollback_text',
        'human_approved_patch_loop_text': 'human_approved_patch_loop_text',
        'draft_quality_text': 'draft_quality_text',
        'draft_file_targets_text': 'draft_file_targets_text',
        'draft_intent_blocks_text': 'draft_intent_blocks_text',
        'draft_conflicts_text': 'draft_conflicts_text',
        'draft_verification_bundle_text': 'draft_verification_bundle_text',
        'draft_review_checklist_text': 'draft_review_checklist_text',
        'approved_draft_execution_report_text': 'approved_draft_execution_report_text',
        'review_centered_patch_loop_text': 'review_centered_patch_loop_text',
    }),
    ('release_pipeline', {
        'build_code_edit_proposal': 'build_code_edit_proposal',
        'build_safe_rewrite_preview': 'build_safe_rewrite_preview',
        'build_generated_code_patch': 'build_generated_code_patch',
        'build_test_suggestions': 'build_test_suggestions',
        'build_inline_review_note': 'build_inline_review_note',
        'build_apply_approved_code_patch': 'build_apply_approved_code_patch',
        'build_prepare_release_package': 'build_prepare_release_package',
        'build_release_readiness': 'build_release_readiness',
        'build_human_approved_release_loop': 'build_human_approved_release_loop',
        'code_edit_proposal_text': 'code_edit_proposal_text',
        'safe_rewrite_preview_text': 'safe_rewrite_preview_text',
        'generated_code_patch_text': 'generated_code_patch_text',
        'test_suggestions_text': 'test_suggestions_text',
        'inline_review_note_text': 'inline_review_note_text',
        'apply_approved_code_patch_text': 'apply_approved_code_patch_text',
        'prepare_release_package_text': 'prepare_release_package_text',
        'release_readiness_text': 'release_readiness_text',
        'human_approved_release_loop_text': 'human_approved_release_loop_text',
    }),
    ('code_patch_release', {
        'build_code_patch_status': 'build_code_patch_status',
        'build_symbol_scan': 'build_symbol_scan',
        'build_rewrite_plan': 'build_rewrite_plan',
        'build_rewrite_conflicts': 'build_rewrite_conflicts',
        'build_code_patch_diff_bundle': 'build_code_patch_diff_bundle',
        'build_apply_code_patch_transaction': 'build_apply_code_patch_transaction',
        'build_semantic_checks': 'build_semantic_checks',
        'build_release_artifact': 'build_release_artifact',
        'build_release_audit_trail': 'build_release_audit_trail',
        'build_generated_code_release_loop': 'build_generated_code_release_loop',
        'code_patch_status_text': 'code_patch_status_text',
        'symbol_scan_text': 'symbol_scan_text',
        'rewrite_plan_text': 'rewrite_plan_text',
        'rewrite_conflicts_text': 'rewrite_conflicts_text',
        'code_patch_diff_bundle_text': 'code_patch_diff_bundle_text',
        'apply_code_patch_transaction_text': 'apply_code_patch_transaction_text',
        'semantic_checks_text': 'semantic_checks_text',
        'release_artifact_text': 'release_artifact_text',
        'release_audit_trail_text': 'release_audit_trail_text',
        'generated_code_release_loop_text': 'generated_code_release_loop_text',
    }),
    ('ai_patch_assistance', {
        'build_task_to_code_patch': 'build_task_to_code_patch',
        'build_code_context': 'build_code_context',
        'build_patch_prompt': 'build_patch_prompt',
        'build_parse_generated_edits': 'build_parse_generated_edits',
        'build_edit_consistency': 'build_edit_consistency',
        'build_ai_code_patch_dry_run': 'build_ai_code_patch_dry_run',
        'build_patch_failure_analysis': 'build_patch_failure_analysis',
        'build_patch_learning_notes': 'build_patch_learning_notes',
        'build_ai_assisted_code_patch_loop': 'build_ai_assisted_code_patch_loop',
        'task_to_code_patch_text': 'task_to_code_patch_text',
        'code_context_text': 'code_context_text',
        'patch_prompt_text': 'patch_prompt_text',
        'parse_generated_edits_text': 'parse_generated_edits_text',
        'edit_consistency_text': 'edit_consistency_text',
        'ai_code_patch_dry_run_text': 'ai_code_patch_dry_run_text',
        'patch_failure_analysis_text': 'patch_failure_analysis_text',
        'patch_learning_notes_text': 'patch_learning_notes_text',
        'ai_assisted_code_patch_loop_text': 'ai_assisted_code_patch_loop_text',
    }),
    ('validated_ai_patch_loop', {
        'build_patch_objective_refinement': 'build_patch_objective_refinement',
        'build_code_context_ranking': 'build_code_context_ranking',
        'build_patch_safety_envelope': 'build_patch_safety_envelope',
        'build_generated_patch_validation': 'build_generated_patch_validation',
        'build_patch_simulation': 'build_patch_simulation',
        'build_test_stub_plan': 'build_test_stub_plan',
        'build_patch_review_score': 'build_patch_review_score',
        'build_patch_recovery_plan': 'build_patch_recovery_plan',
        'build_validated_ai_code_patch_loop': 'build_validated_ai_code_patch_loop',
        'patch_objective_refinement_text': 'patch_objective_refinement_text',
        'code_context_ranking_text': 'code_context_ranking_text',
        'patch_safety_envelope_text': 'patch_safety_envelope_text',
        'generated_patch_validation_text': 'generated_patch_validation_text',
        'patch_simulation_text': 'patch_simulation_text',
        'test_stub_plan_text': 'test_stub_plan_text',
        'patch_review_score_text': 'patch_review_score_text',
        'patch_recovery_plan_text': 'patch_recovery_plan_text',
        'validated_ai_code_patch_loop_text': 'validated_ai_code_patch_loop_text',
    }),
    ('approval_release_workflow', {
        'bind_current_approval_to_validated_manifest': 'bind_current_approval_to_validated_manifest',
        'build_ai_patch_review_bundle': 'build_ai_patch_review_bundle',
        'build_review_bundle_integrity': 'build_review_bundle_integrity',
        'build_approval_ready': 'build_approval_ready',
        'build_approval_ledger': 'build_approval_ledger',
        'build_apply_validated_ai_patch': 'build_apply_validated_ai_patch',
        'build_post_apply_review': 'build_post_apply_review',
        'build_package_build_plan': 'build_package_build_plan',
        'build_approval_to_release_loop': 'build_approval_to_release_loop',
        'ai_patch_review_bundle_text': 'ai_patch_review_bundle_text',
        'review_bundle_integrity_text': 'review_bundle_integrity_text',
        'approval_ready_text': 'approval_ready_text',
        'approval_ledger_text': 'approval_ledger_text',
        'apply_validated_ai_patch_text': 'apply_validated_ai_patch_text',
        'post_apply_review_text': 'post_apply_review_text',
        'package_build_plan_text': 'package_build_plan_text',
        'approval_to_release_loop_text': 'approval_to_release_loop_text',
        'bind_validated_approval_text': 'bind_validated_approval_text',
    }),
    ('release_packaging', {
        'build_release_manifest_integrity': 'build_release_manifest_integrity',
        'build_package_inventory': 'build_package_inventory',
        'build_package_checksums': 'build_package_checksums',
        'build_release_notes': 'build_release_notes',
        'build_release_handoff_report': 'build_release_handoff_report',
        'build_release_zip': 'build_release_zip',
        'build_verify_release_unzip': 'build_verify_release_unzip',
        'build_release_pipeline_audit': 'build_release_pipeline_audit',
        'build_verified_release_package_loop': 'build_verified_release_package_loop',
        'release_manifest_integrity_text': 'release_manifest_integrity_text',
        'package_inventory_text': 'package_inventory_text',
        'package_checksums_text': 'package_checksums_text',
        'release_notes_text': 'release_notes_text',
        'release_handoff_report_text': 'release_handoff_report_text',
        'build_release_zip_text': 'build_release_zip_text',
        'verify_release_unzip_text': 'verify_release_unzip_text',
        'release_pipeline_audit_text': 'release_pipeline_audit_text',
        'verified_release_package_loop_text': 'verified_release_package_loop_text',
        '_package_name': '_package_name',
    }),
    ('release_installation', {
        'build_release_profiles': 'build_release_profiles',
        'build_package_privacy_scan': 'build_package_privacy_scan',
        'build_portable_metadata_check': 'build_portable_metadata_check',
        'build_first_run_check': 'build_first_run_check',
        'build_dependency_advisor': 'build_dependency_advisor',
        'build_upgrade_notes': 'build_upgrade_notes',
        'build_runtime_migration_check': 'build_runtime_migration_check',
        'build_release_install_verification': 'build_release_install_verification',
        'build_verified_installable_release_loop': 'build_verified_installable_release_loop',
        'build_smoke_runtime_hardening': 'build_smoke_runtime_hardening',
        'build_external_zip_install_verification': 'build_external_zip_install_verification',
        'build_deterministic_release_manifest': 'build_deterministic_release_manifest',
        'build_update_dry_run_plan': 'build_update_dry_run_plan',
        'build_atomic_source_update': 'build_atomic_source_update',
        'build_runtime_migration_assistant': 'build_runtime_migration_assistant',
        'build_route_safety_harness': 'build_route_safety_harness',
        'build_release_dashboard_command_center': 'build_release_dashboard_command_center',
        'build_clean_room_install_harness': 'build_clean_room_install_harness',
        'build_verified_self_update_release_pipeline': 'build_verified_self_update_release_pipeline',
        'release_profiles_text': 'release_profiles_text',
        'package_privacy_scan_text': 'package_privacy_scan_text',
        'portable_metadata_check_text': 'portable_metadata_check_text',
        'first_run_check_text': 'first_run_check_text',
        'dependency_advisor_text': 'dependency_advisor_text',
        'upgrade_notes_text': 'upgrade_notes_text',
        'runtime_migration_check_text': 'runtime_migration_check_text',
        'release_install_verification_text': 'release_install_verification_text',
        'verified_installable_release_loop_text': 'verified_installable_release_loop_text',
        'smoke_runtime_hardening_text': 'smoke_runtime_hardening_text',
        'external_zip_install_verification_text': 'external_zip_install_verification_text',
        'deterministic_release_manifest_text': 'deterministic_release_manifest_text',
        'update_dry_run_plan_text': 'update_dry_run_plan_text',
        'atomic_source_update_text': 'atomic_source_update_text',
        'runtime_migration_assistant_text': 'runtime_migration_assistant_text',
        'route_safety_harness_text': 'route_safety_harness_text',
        'release_dashboard_command_center_text': 'release_dashboard_command_center_text',
        'clean_room_install_harness_text': 'clean_room_install_harness_text',
        'verified_self_update_release_pipeline_text': 'verified_self_update_release_pipeline_text',
    }),
    ('test_runner', {
        'list_test_reports': 'list_test_reports',
        'load_test_report': 'load_test_report',
        'test_report_text': 'test_report_text',
    }),
    ('test_report_reviewer', {
        'list_test_reviews': 'list_test_reviews',
        'load_test_review': 'load_test_review',
        'test_review_text': 'test_review_text',
    }),
    ('watch_mode', {
        'list_watch_reports': 'list_watch_reports',
        'load_watch_report': 'load_watch_report',
        'run_watch_once': 'run_watch_once',
        'run_watch_loop': 'run_watch_loop',
        'watch_report_text': 'watch_report_text',
    }),
    ('autonomous_dev_cycle', {
        'dev_cycle_text': 'dev_cycle_text',
        'get_dev_cycle': 'get_dev_cycle',
        'list_dev_cycles': 'list_dev_cycles',
    }),
    ('dev_loop_runner', {
        'get_dev_loop': 'get_dev_loop',
        'list_dev_loops': 'list_dev_loops',
        'run_dev_loop': 'run_dev_loop',
        'dev_loop_text': 'dev_loop_text',
    }),
)

DEFERRED_MODULES: tuple[str, ...] = tuple(dict.fromkeys(module for module, _mapping in DEFERRED_EXPORTS))

def install_dashboard_deferred_services(namespace: MutableMapping[str, Any]) -> dict[str, tuple[str, ...]]:
    namespace.update(DEFERRED_CONSTANTS)
    installed: dict[str, tuple[str, ...]] = {}
    for module_name, mapping in DEFERRED_EXPORTS:
        installed[module_name] = install_lazy_callables(namespace, module_name, mapping)
    return installed

def deferred_dashboard_status() -> dict[str, Any]:
    status = lazy_import_status(list(DEFERRED_MODULES))
    return {
        "module_count": len(DEFERRED_MODULES),
        "loaded_module_count": sum(1 for row in status.values() if row.get("loaded")),
        "resolved_export_count": sum(int(row.get("resolved_export_count", 0)) for row in status.values()),
        "modules": status,
    }
