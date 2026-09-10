from __future__ import annotations

"""Isolated focused verification for ordinary post-review Eidolon development.

Each suite runs from its own disposable source copy with its own external runtime
and file-backed output. The caller's source tree is never used as a fixture
workspace, so a destructive or stale test cannot corrupt later evidence.
"""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))
INFRASTRUCTURE_NAMES = {".git", ".venv", "venv"}


@dataclass(frozen=True)
class SuiteSpec:
    name: str
    script: str
    arguments: tuple[str, ...] = ("--json",)
    timeout_seconds: int = 300
    profiles: tuple[str, ...] = ("full",)


SUITES: tuple[SuiteSpec, ...] = (
    SuiteSpec("v1107.5-attention-intention-checkpoint", "tools/v1107_5_attention_intention_checkpoint_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.6-intention-reconsideration-decay", "tools/v1107_6_intention_reconsideration_decay_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.7-intention-conflict-resolution", "tools/v1107_7_intention_conflict_resolution_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.8-intention-lifecycle-review", "tools/v1107_8_intention_lifecycle_review_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.4-bounded-intention-formation", "tools/v1107_4_bounded_intention_formation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.3-agenda-guided-reflection", "tools/v1107_3_agenda_guided_reflection_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.2-agenda-continuity-inspection-checkpoint", "tools/v1107_2_agenda_continuity_inspection_checkpoint_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1107.1-motivation-to-agenda-arbitration", "tools/v1107_1_motivation_to_agenda_arbitration_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1107.0-autonomous-attention-agenda-foundation", "tools/v1107_0_autonomous_attention_agenda_foundation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.9-knowledge-maintenance-checkpoint", "tools/v1106_9_knowledge_maintenance_checkpoint_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1106.8-knowledge-maintenance-consolidation", "tools/v1106_8_knowledge_maintenance_consolidation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.7-belief-maintenance-outcomes", "tools/v1106_7_belief_maintenance_outcomes_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.6-bounded-reconsideration-reflection", "tools/v1106_6_bounded_reconsideration_reflection_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.5-reconsideration-conversation-continuity", "tools/v1106_5_reconsideration_conversation_continuity_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.4-evidence-change-propagation", "tools/v1106_4_evidence_change_propagation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.3-knowledge-reconsideration-scheduling", "tools/v1106_3_knowledge_reconsideration_scheduling_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.2-knowledge-confidence-maintenance-checkpoint", "tools/v1106_2_knowledge_confidence_maintenance_checkpoint_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.1-cross-inquiry-evidence-lineage", "tools/v1106_1_cross_inquiry_evidence_lineage_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1106.0-inquiry-residual-question-lineage", "tools/v1106_0_inquiry_residual_question_lineage_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.9-inquiry-cognition-checkpoint", "tools/v1105_9_inquiry_cognition_checkpoint_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.8-inquiry-resolution-knowledge-consolidation", "tools/v1105_8_inquiry_resolution_knowledge_consolidation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.7-bounded-inquiry-reflection", "tools/v1105_7_bounded_inquiry_reflection_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.6-inquiry-development-evidence-quality", "tools/v1105_6_inquiry_development_evidence_quality_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.5-inquiry-conversation-continuity", "tools/v1105_5_inquiry_conversation_continuity_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.4-evidence-assimilation-research-boundary", "tools/v1105_4_evidence_assimilation_research_boundary_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.3-inquiry-activation-attention-routing", "tools/v1105_3_inquiry_activation_attention_routing_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.2-cognitive-development-checkpoint", "tools/v1105_2_cognitive_development_checkpoint_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.1-prospective-planning-counterfactual", "tools/v1105_1_prospective_planning_counterfactual_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1105.0-self-directed-inquiry-workspace", "tools/v1105_0_self_directed_inquiry_workspace_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.9-persistent-internal-life-checkpoint", "tools/v1104_9_persistent_internal_life_checkpoint_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.8-native-reflection-quality-resource-validation", "tools/v1104_8_native_reflection_quality_resource_validation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.7-motivation-conflict-belief-revision", "tools/v1104_7_motivation_conflict_belief_revision_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.6-multi-day-cognitive-continuity", "tools/v1104_6_multi_day_cognitive_continuity_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.5-proactive-communication-continuity", "tools/v1104_5_proactive_communication_continuity_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1104.4-endogenous-attention-reflection-cycle", "tools/v1104_4_endogenous_attention_reflection_cycle_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.3-persistent-motivation-self-model-foundation", "tools/v1104_3_persistent_motivation_self_model_foundation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.2-action-proposal-explanation-cards", "tools/v1104_2_action_proposal_explanation_cards_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1104.1-bounded-operator-visible-tool-catalog", "tools/v1104_1_bounded_operator_visible_tool_catalog_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1104.0-conversation-action-intent-classification", "tools/v1104_0_conversation_action_intent_classification_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.9-messaging-reliability-checkpoint", "tools/v1103_9_messaging_reliability_checkpoint_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1103.8-long-session-messaging-soak", "tools/v1103_8_long_session_messaging_soak_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.7-multi-tab-ownership-stale-tab-recovery", "tools/v1103_7_multi_tab_ownership_stale_tab_recovery_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.6-cancellation-retry-late-result-reconciliation", "tools/v1103_6_cancellation_retry_late_result_reconciliation_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.5-provider-outage-return", "tools/v1103_5_provider_outage_return_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.4-conversation-switching-draft-continuity", "tools/v1103_4_conversation_switching_draft_continuity_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.3-scroll-anchoring-jump-latest", "tools/v1103_3_scroll_anchoring_jump_latest_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.2-exactly-once-send-provider-request", "tools/v1103_2_exactly_once_send_provider_request_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1103.1-keyboard-ime-remote-input", "tools/v1103_1_keyboard_ime_remote_input_tests.py", timeout_seconds=120, profiles=("core", "full")),
    SuiteSpec("v1103.0-first-visible-token-timing", "tools/v1103_0_first_visible_token_timing_tests.py", timeout_seconds=120, profiles=("core", "full")),
    SuiteSpec("v1102.9-natural-conversation-checkpoint", "tools/v1102_9_natural_conversation_checkpoint_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1102.6-native-conversation-quality-evaluation", "tools/v1102_6_native_conversation_quality_evaluation_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.7-provider-neutral-conversation-tuning", "tools/v1102_7_provider_neutral_conversation_tuning_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.8-long-conversation-personality-stability", "tools/v1102_8_long_conversation_personality_stability_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.0-identity-relationship-prompt-foundation", "tools/v1102_0_identity_relationship_prompt_foundation_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.1-greeting-repetition-suppression", "tools/v1102_1_greeting_repetition_suppression_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.2-intent-topic-continuity", "tools/v1102_2_intent_topic_continuity_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.3-corrections-preference-propagation", "tools/v1102_3_corrections_preference_propagation_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.4-affection-nickname-boundaries", "tools/v1102_4_affection_nickname_boundaries_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1102.5-response-length-depth-matching", "tools/v1102_5_response_length_depth_matching_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1101.0-cold-start-budget-truth", "tools/v1101_0_cold_start_budget_truth_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1101.1-lazy-dashboard-shell", "tools/v1101_1_lazy_dashboard_shell_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1101.2-deferred-administrative-loading", "tools/v1101_2_deferred_administrative_loading_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1101.3-active-project-self-description-repair", "tools/v1101_3_active_project_self_description_repair_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1101.4-startup-progress-failure-recovery", "tools/v1101_4_startup_progress_failure_recovery_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1101.5-warm-cold-restart-parity", "tools/v1101_5_warm_cold_restart_parity_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1101.6-windows-startup-soak", "tools/v1101_6_windows_startup_soak_tests.py", timeout_seconds=600, profiles=("core", "full")),
    SuiteSpec("v1101.7-source-runtime-migration-guidance", "tools/v1101_7_source_runtime_migration_guidance_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1101.8-ordinary-launch-usability", "tools/v1101_8_ordinary_launch_usability_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1101.9-first-use-coherence-checkpoint", "tools/v1101_9_first_use_coherence_checkpoint_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1100.0-product-reality-benchmark", "tools/v1100_0_product_reality_benchmark_tests.py", timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.9-consumer-use-lifecycle-consolidation", "tools/v1099_9_consumer_use_lifecycle_consolidation_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.8-downstream-consumer-result-validation", "tools/v1099_8_downstream_consumer_result_validation_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.7-exact-consumer-use-handoff-plan", "tools/v1099_7_exact_consumer_use_handoff_plan_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.6-consumer-daily-use-binding-consolidation", "tools/v1099_6_consumer_daily_use_binding_consolidation_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.5-exact-successor-consumer-revalidation", "tools/v1099_5_successor_consumer_revalidation_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.4-consumer-daily-use-binding-recovery-expiry", "tools/v1099_4_consumer_daily_use_recovery_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.3-release-authority-consumer-daily-use-consolidation", "tools/v1099_3_consumer_daily_use_consolidation_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.2-exact-consumer-use-preflight-binding", "tools/v1099_2_consumer_use_preflight_binding_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1099.1-exact-consumer-selection-pinning", "tools/v1099_1_consumer_selection_pinning_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1098.9-release-authority-handoff-lifecycle-consolidation", "tools/v1098_9_handoff_lifecycle_consolidation_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1098.8-handoff-consumer-supersession-binding", "tools/v1098_8_handoff_consumer_supersession_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1098.7-consumer-receipt-recovery-retirement", "tools/v1098_7_consumer_receipt_recovery_retirement_tests.py", arguments=(), timeout_seconds=300, profiles=("core", "full")),
    SuiteSpec("v1098.6-release-authority-handoff-consolidation-checkpoint", "tools/v1098_6_release_authority_handoff_consolidation_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1098.5-release-authority-consumer-validation-receipt-binding", "tools/v1098_5_release_authority_consumer_validation_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1098.4-handoff-acknowledgment-recovery-expiry-hardening", "tools/v1098_4_handoff_acknowledgment_recovery_expiry_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1098.3-release-authority-daily-use-coherence-checkpoint", "tools/v1098_3_release_authority_daily_use_coherence_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1098.2-release-authority-handoff-plan-binding", "tools/v1098_2_release_authority_handoff_plan_binding_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1098.1-release-authority-readiness-refresh-recovery-hardening", "tools/v1098_1_release_authority_readiness_refresh_recovery_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1098.0-certification-to-release-authority-boundary", "tools/v1098_0_certification_to_release_authority_boundary_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.9-certification-authority-consolidation-checkpoint", "tools/v1097_9_certification_authority_consolidation_checkpoint_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.8-certification-policy-evolution-migration-preview", "tools/v1097_8_certification_policy_evolution_migration_preview_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.7-certification-authority-history-reconciliation", "tools/v1097_7_certification_authority_history_reconciliation_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.6-certification-daily-use-release-authority-coherence", "tools/v1097_6_certification_daily_use_authority_coherence_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.5-evidence-freshness-replacement-recertification-preview", "tools/v1097_5_evidence_freshness_replacement_recertification_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.4-certification-decision-interruption-recovery", "tools/v1097_4_certification_decision_interruption_recovery_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.3-certification-decision-release-authority-coherence", "tools/v1097_3_certification_decision_release_authority_tests.py", arguments=(), timeout_seconds=1200, profiles=("core", "full")),
    SuiteSpec("v1097.2-certification-plan-binding-exact-authorization", "tools/v1097_2_certification_plan_authorization_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1097.1-certification-evidence-intake-readiness-preview", "tools/v1097_1_certification_evidence_readiness_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1097.0-transactional-promotion-apply-release-coherence", "tools/v1097_0_transactional_promotion_release_coherence_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1096.9-promotion-plan-binding-exact-authorization", "tools/v1096_9_promotion_plan_authorization_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1096.8-promotion-impact-preview-foundation", "tools/v1096_8_promotion_impact_preview_foundation_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1096.7-installed-state-reconciliation-daily-use-coherence", "tools/v1096_7_installed_state_daily_use_coherence_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1096.6-interrupted-installation-recovery-rollback", "tools/v1096_6_interrupted_installation_recovery_rollback_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1096.5-exact-transactional-installation-apply-foundation", "tools/v1096_5_exact_transactional_installation_apply_tests.py", arguments=(), timeout_seconds=900, profiles=("core", "full")),
    SuiteSpec("v1096.4-installation-authorization-external-staging-foundation", "tools/v1096_4_installation_authorization_external_staging_tests.py", arguments=(), timeout_seconds=600, profiles=("core", "full")),
    SuiteSpec("v1096.3-installation-plan-binding-drift-protection", "tools/v1096_3_installation_plan_binding_tests.py", arguments=(), timeout_seconds=600, profiles=("core", "full")),
    SuiteSpec("v1096.2-operator-controlled-installation-preview-foundation", "tools/v1096_2_installation_preview_foundation_tests.py", arguments=(), timeout_seconds=600, profiles=("core", "full")),
    SuiteSpec("v1096.1-handoff-recovery-replacement-hardening", "tools/v1096_1_handoff_recovery_replacement_hardening_tests.py", arguments=(), timeout_seconds=600, profiles=("core", "full")),
    SuiteSpec("v1096.0-operator-controlled-release-handoff-foundation", "tools/v1096_0_operator_controlled_release_handoff_foundation_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1095.9-release-packaging-coherence-checkpoint", "tools/v1095_9_release_packaging_coherence_checkpoint_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1095.8-candidate-handoff-daily-use-coherence", "tools/v1095_8_candidate_handoff_daily_use_coherence_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.7-archive-manifest-coherence", "tools/v1095_7_archive_manifest_coherence_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.6-exact-candidate-identity-contract", "tools/v1095_6_exact_candidate_identity_contract_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.5-historical-verification-daily-use-consolidation", "tools/v1095_5_historical_verification_daily_use_consolidation_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.4-duplicate-ordering-reconciliation-preview", "tools/v1095_4_duplicate_ordering_reconciliation_preview_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.3-authoritative-release-history-structure", "tools/v1095_3_authoritative_release_history_structure_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.2-version-drift-safe-reconciliation", "tools/v1095_2_version_drift_safe_reconciliation_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.1-cross-surface-version-resolution", "tools/v1095_1_cross_surface_version_resolution_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1095.0-authoritative-version-role-contract", "tools/v1095_0_authoritative_version_role_contract_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1094.9-process-reliability-checkpoint", "tools/v1094_9_process_reliability_checkpoint_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.8-long-session-multi-tab-process-ux", "tools/v1094_8_long_session_multi_tab_process_ux_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.7-cancellation-escalation-uncertain-result", "tools/v1094_7_cancellation_escalation_uncertain_result_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.6-unified-operation-recovery-state", "tools/v1094_6_unified_operation_recovery_state_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.5-cancellation-recovery-daily-use", "tools/v1094_5_cancellation_recovery_daily_use_hardening_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.4-dashboard-restart-reattachment", "tools/v1094_4_dashboard_restart_live_worker_reattachment_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.3-exact-cancellation-semantics", "tools/v1094_3_exact_cancellation_semantics_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.2-orphan-crash-recovery", "tools/v1094_2_orphan_crash_recovery_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.1-process-ownership-lock-lifecycle", "tools/v1094_1_process_ownership_lock_lifecycle_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1094.0-spawn-safe-worker-entry-points", "tools/v1094_0_spawn_safe_worker_entry_points_tests.py", arguments=(), timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1093.9-metadata-reliability-checkpoint", "tools/v1093_9_metadata_reliability_checkpoint_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.8-daily-use-metadata-recovery-hardening", "tools/v1093_8_daily_use_metadata_recovery_hardening_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.7-windows-replacement-sharing-hardening", "tools/v1093_7_windows_replacement_sharing_hardening_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.6-orphaned-metadata-artifact-reconciliation", "tools/v1093_6_orphaned_metadata_artifact_reconciliation_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.5-migration-recovery-daily-use-hardening", "tools/v1093_5_migration_recovery_daily_use_hardening_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.4-cross-process-metadata-mutation-coordination", "tools/v1093_4_cross_process_metadata_mutation_coordination_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.3-governed-metadata-migration-application", "tools/v1093_3_governed_metadata_migration_application_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.2-previewed-backup-bound-metadata-migration", "tools/v1093_2_previewed_backup_bound_metadata_migration_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.1-canonical-atomic-utf8-saves", "tools/v1093_1_canonical_atomic_utf8_saves_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1093.0-remaining-mutable-json-inventory-bom", "tools/v1093_0_remaining_mutable_json_inventory_bom_tests.py", arguments=(), profiles=("core", "full")),
    SuiteSpec("v1092.9-active-project-recovery-checkpoint", "tools/v1092_9_active_project_recovery_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.5-restart-multi-tab-switching-hardening", "tools/v1092_5_restart_multi_tab_switching_hardening_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.6-unified-project-recovery-state", "tools/v1092_6_unified_project_recovery_state_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.7-restart-revalidation-recovery", "tools/v1092_7_restart_revalidation_recovery_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.8-daily-use-project-recovery-ux", "tools/v1092_8_daily_use_project_recovery_ux_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.4-missing-moved-project-recovery", "tools/v1092_4_missing_moved_project_recovery_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.3-project-switch-conversation-continuity", "tools/v1092_3_project_switch_conversation_continuity_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.2-source-root-capability-binding", "tools/v1092_2_source_root_capability_binding_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.1-active-project-selection-switching", "tools/v1092_1_active_project_selection_switching_tests.py", profiles=("core", "full")),
    SuiteSpec("v1092.0-authoritative-project-identity", "tools/v1092_0_authoritative_project_identity_tests.py", profiles=("core", "full")),
    SuiteSpec("v1091.9-startup-foundation-checkpoint", "tools/v1091_9_startup_foundation_checkpoint_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1091.8-startup-failure-recovery", "tools/v1091_8_startup_failure_recovery_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1091.7-deferred-administrative-services", "tools/v1091_7_deferred_administrative_services_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1091.6-conversation-first-initialization", "tools/v1091_6_conversation_first_initialization_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1091.5-cold-startup-route-parity-hardening", "tools/v1091_5_cold_startup_route_parity_hardening_tests.py", timeout_seconds=240, profiles=("core", "full")),
    SuiteSpec("v1091.4-dashboard-lazy-import-decomposition", "tools/v1091_4_dashboard_lazy_import_decomposition_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1091.3-cold-dashboard-startup-measurement", "tools/v1091_3_cold_dashboard_startup_measurement_tests.py", timeout_seconds=180, profiles=("core", "full")),
    SuiteSpec("v1091.2-cross-platform-process-verification", "tools/v1091_2_cross_platform_process_verification_tests.py", timeout_seconds=420, profiles=("core", "full")),
    SuiteSpec("v1091.1-active-project-truth", "tools/v1091_1_active_project_truth_tests.py", profiles=("core", "full")),
    SuiteSpec("v1091.0-bom-aware-json-metadata-migration", "tools/v1091_0_bom_aware_json_metadata_migration_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.9-desktop-alpha-repair-candidate-review-checkpoint", "tools/v1090_9_repair_candidate_review_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.8-long-session-candidate-review", "tools/v1090_8_long_session_candidate_review_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.7-candidate-review-export", "tools/v1090_7_candidate_review_export_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.6-operator-candidate-review-console", "tools/v1090_6_operator_candidate_review_console_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.5-candidate-supersession-lineage", "tools/v1090_5_candidate_supersession_lineage_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.4-bounded-candidate-comparison", "tools/v1090_4_bounded_candidate_comparison_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.3-candidate-verification-evidence", "tools/v1090_3_candidate_verification_evidence_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.2-explicit-candidate-review-findings", "tools/v1090_2_explicit_candidate_review_findings_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.1-immutable-candidate-registration", "tools/v1090_1_immutable_candidate_registration_tests.py", profiles=("core", "full")),
    SuiteSpec("v1090.0-repair-candidate-review-protocol", "tools/v1090_0_repair_candidate_review_protocol_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.9-desktop-alpha-evaluation-findings-repair-intake-checkpoint", "tools/v1089_9_evaluation_findings_repair_intake_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.8-long-session-findings-ux", "tools/v1089_8_long_session_findings_ux_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.7-finding-review-export", "tools/v1089_7_finding_review_export_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.6-operator-findings-console", "tools/v1089_6_operator_findings_console_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.5-bounded-repair-intake-comparison", "tools/v1089_5_bounded_repair_intake_comparison_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.4-finding-triage-review", "tools/v1089_4_finding_triage_review_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.3-finding-aggregation", "tools/v1089_3_finding_aggregation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.2-repair-candidate-references", "tools/v1089_2_repair_candidate_reference_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.1-finding-reproducibility-review", "tools/v1089_1_finding_reproducibility_review_tests.py", profiles=("core", "full")),
    SuiteSpec("v1089.0-evaluation-finding-intake", "tools/v1089_0_evaluation_finding_intake_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.9-desktop-alpha-operator-evaluation-campaign-checkpoint", "tools/v1088_9_operator_evaluation_campaign_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.8-campaign-review-export", "tools/v1088_8_campaign_review_export_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.7-operator-campaign-console", "tools/v1088_7_operator_campaign_console_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.6-campaign-review-workflow", "tools/v1088_6_campaign_review_workflow_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.5-bounded-campaign-comparison", "tools/v1088_5_bounded_campaign_comparison_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.4-campaign-follow-up-references", "tools/v1088_4_campaign_follow_up_reference_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.3-campaign-issue-aggregation", "tools/v1088_3_campaign_issue_aggregation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.2-campaign-evaluation-enrollment", "tools/v1088_2_campaign_evaluation_enrollment_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.1-evaluation-campaign-lifecycle", "tools/v1088_1_evaluation_campaign_lifecycle_tests.py", profiles=("core", "full")),
    SuiteSpec("v1088.0-operator-evaluation-campaign-protocol", "tools/v1088_0_operator_evaluation_campaign_protocol_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.9-desktop-alpha-daily-evaluation-checkpoint", "tools/v1087_9_desktop_alpha_daily_evaluation_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.8-evaluation-review-export", "tools/v1087_8_evaluation_review_export_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.7-desktop-alpha-evaluation-console", "tools/v1087_7_desktop_alpha_evaluation_console_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.6-long-session-daily-use-evaluation", "tools/v1087_6_long_session_daily_use_evaluation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.5-restart-outage-evaluation", "tools/v1087_5_restart_outage_evaluation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.4-daily-evaluation-trends", "tools/v1087_4_daily_evaluation_trends_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.3-evaluation-reproduction-packet", "tools/v1087_3_evaluation_reproduction_packet_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.2-session-outcome-classification", "tools/v1087_2_session_outcome_classification_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.1-operator-observation-capture", "tools/v1087_1_operator_observation_capture_tests.py", profiles=("core", "full")),
    SuiteSpec("v1087.0-daily-evaluation-protocol", "tools/v1087_0_daily_evaluation_protocol_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.9-desktop-alpha-conversation-readiness-checkpoint", "tools/v1086_9_desktop_alpha_conversation_readiness_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.8-long-session-performance-ux-hardening", "tools/v1086_8_long_session_performance_ux_hardening_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.7-offline-conversation-degradation", "tools/v1086_7_offline_conversation_degradation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.6-pinned-working-context", "tools/v1086_6_pinned_working_context_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.5-message-editing-branching", "tools/v1086_5_message_editing_branching_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.4-safe-retry-regeneration", "tools/v1086_4_safe_retry_regeneration_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.3-generation-interruption-steering", "tools/v1086_3_generation_interruption_steering_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.2-temporary-instruction-scope", "tools/v1086_2_temporary_instruction_scope_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.1-per-conversation-response-preferences", "tools/v1086_1_per_conversation_response_preferences_tests.py", profiles=("core", "full")),
    SuiteSpec("v1086.0-conversation-control-foundation", "tools/v1086_0_conversation_control_foundation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.9-context-intelligence-checkpoint", "tools/v1085_9_context_intelligence_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.8-context-inspection-console", "tools/v1085_8_context_inspection_console_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.7-stale-summary-detection", "tools/v1085_7_stale_summary_detection_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.6-cross-session-thread-linking", "tools/v1085_6_cross_session_thread_linking_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.5-correction-aware-retrieval", "tools/v1085_5_correction_aware_retrieval_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.4-context-budget-management", "tools/v1085_4_context_budget_management_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.3-conversation-topic-segmentation", "tools/v1085_3_conversation_topic_segmentation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.2-recency-salience-balance", "tools/v1085_2_recency_salience_balance_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.1-bounded-relevance-ranking", "tools/v1085_1_bounded_relevance_ranking_tests.py", profiles=("core", "full")),
    SuiteSpec("v1085.0-context-assembly-architecture", "tools/v1085_0_context_assembly_architecture_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.9-conversation-quality-checkpoint", "tools/v1084_9_conversation_quality_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.8-conversation-quality-diagnostics", "tools/v1084_8_conversation_quality_diagnostics_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.7-personality-expression-stability", "tools/v1084_7_personality_expression_stability_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.6-conversational-correction-handling", "tools/v1084_6_conversational_correction_handling_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.5-topic-transition-quality", "tools/v1084_5_topic_transition_quality_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.4-natural-conversational-callbacks", "tools/v1084_4_natural_conversational_callbacks_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.3-unresolved-thread-continuity", "tools/v1084_3_unresolved_thread_continuity_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.2-response-length-depth-matching", "tools/v1084_2_response_length_depth_matching_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.1-turn-intent-alignment", "tools/v1084_1_turn_intent_alignment_tests.py", profiles=("core", "full")),
    SuiteSpec("v1084.0-conversation-quality-foundation", "tools/v1084_0_conversation_quality_foundation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.9-relationship-continuity-checkpoint", "tools/v1083_9_relationship_continuity_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.8-memory-browse-search-privacy", "tools/v1083_8_memory_browse_search_privacy_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.7-user-correction-propagation", "tools/v1083_7_user_correction_propagation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.6-memory-conflict-reconciliation", "tools/v1083_6_memory_conflict_reconciliation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.5-important-moment-provenance", "tools/v1083_5_important_moment_provenance_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.4-mood-continuity-without-inflation", "tools/v1083_4_mood_continuity_without_inflation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.3-long-session-personality-stability", "tools/v1083_3_long_session_personality_stability_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.2-retraction-vector-cleanup", "tools/v1083_2_retraction_vector_cleanup_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.1-relationship-memory-curation-ux", "tools/v1083_1_relationship_memory_curation_ux_tests.py", profiles=("core", "full")),
    SuiteSpec("v1083.0-memory-commit-attribution", "tools/v1083_0_memory_commit_attribution_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.9-daily-use-stability-checkpoint", "tools/v1082_9_daily_use_stability_checkpoint_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.8-cross-process-claim-lease", "tools/v1082_8_cross_process_claim_lease_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.7-sleep-wake-hidden-tab", "tools/v1082_7_sleep_wake_hidden_tab_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.6-cancellation-retry-presentation", "tools/v1082_6_cancellation_retry_presentation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.5-large-history-rendering", "tools/v1082_5_large_history_rendering_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.4-browser-navigation-hardening", "tools/v1082_4_browser_navigation_hardening_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.3-search-archive-consistency", "tools/v1082_3_search_archive_consistency_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.2-reading-position-unread-boundary", "tools/v1082_2_reading_position_unread_boundary_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.1-cross-tab-draft-conflict", "tools/v1082_1_cross_tab_draft_conflict_tests.py", profiles=("core", "full")),
    SuiteSpec("v1082.0-offline-first-session-durability", "tools/v1082_0_offline_first_session_durability_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.9-provider-recovery-arc-consolidation", "tools/v1081_9_provider_recovery_arc_consolidation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.8-recovery-claim-lineage", "tools/v1081_8_recovery_claim_resend_lineage_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.7-recovery-history-presentation", "tools/v1081_7_recovery_history_retry_presentation_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.6-conversation-failure-retry", "tools/v1081_6_conversation_failure_retry_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.5-recovery-evidence-resume", "tools/v1081_5_recovery_evidence_conversation_resume_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.4-offline-companion-recovery", "tools/v1081_4_offline_companion_recovery_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.3-provider-availability-recovery", "tools/v1081_3_provider_availability_recovery_tests.py", profiles=("core", "full")),
    SuiteSpec("local-model-readiness", "tools/local_model_readiness_tests.py", profiles=("full",)),
    SuiteSpec("provider-readiness-offline-recovery", "tools/provider_readiness_recovery_tests.py", profiles=("full",)),
    SuiteSpec("v1081.2-conversation-transport-recovery", "tools/v1081_2_conversation_transport_recovery_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.1-daily-use-baseline-soak", "tools/v1081_1_daily_use_baseline_soak_tests.py", profiles=("core", "full")),
    SuiteSpec("v1081.0-consolidated-baseline", "tools/v1081_0_consolidated_post_review_baseline_tests.py", profiles=("core", "full")),
    SuiteSpec("v1080.9-usability", "tools/v1080_9_desktop_alpha_usability_consolidation_tests.py"),
    SuiteSpec("v1080.8-relationship-personality", "tools/v1080_8_relationship_personality_continuity_tests.py"),
    SuiteSpec("v1080.7-attention-continuity", "tools/v1080_7_notification_task_project_continuity_tests.py"),
    SuiteSpec("v1080.6-conversation-organization", "tools/v1080_6_conversation_search_archive_session_organization_tests.py"),
    SuiteSpec("v1080.5-daily-use-expansion", "tools/v1080_5_desktop_alpha_daily_use_expansion_tests.py"),
    SuiteSpec("v1080.4-action-claim", "tools/v1080_4_desktop_alpha_candidate_consolidation_tests.py"),
    SuiteSpec("v1080.3-conversation-operator-soak", "tools/v1080_3_daily_conversation_operator_soak_tests.py", arguments=()),
    SuiteSpec("v1080.2-control-portal", "tools/v1080_2_conversational_control_portal_tests.py", arguments=()),
    SuiteSpec("conversation-responsiveness", "tools/conversational_responsiveness_companion_quality_tests.py"),
    SuiteSpec("conversation-sessions", "tools/conversation_session_tests.py"),
    SuiteSpec("conversation-experience", "tools/conversation_experience_tests.py"),
    SuiteSpec("multi-tab-coordination", "tools/multi_tab_conversation_coordination_tests.py"),
    SuiteSpec("relationship-memory-curation", "tools/relationship_memory_curation_tests.py"),
    SuiteSpec("mood-important-moment-continuity", "tools/mood_moment_continuity_tests.py"),
    SuiteSpec("session-organization-recovery", "tools/conversation_session_organization_tests.py"),
    SuiteSpec("provider-neutral-conversation", "tools/native_conversation_validation_tests.py", timeout_seconds=360, profiles=("core", "full")),
    SuiteSpec("conversation-runtime-critical-path", "tools/conversation_runtime_tests.py", timeout_seconds=360, profiles=("core", "full")),
)


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in INFRASTRUCTURE_NAMES or name == "__pycache__"}
    ignored.update(name for name in names if name.endswith((".pyc", ".pyo")))
    return ignored


def source_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in INFRASTRUCTURE_NAMES for part in relative.parts):
            continue
        snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def parse_json_report(text: str) -> tuple[dict[str, Any], str | None]:
    stripped = text.strip()
    candidates = [stripped]
    candidates.extend(stripped[index:] for index, char in reversed(list(enumerate(stripped))) if char == "{")
    error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            if not isinstance(payload, dict):
                raise TypeError("suite report must be a JSON object")
            return payload, None
        except (json.JSONDecodeError, TypeError) as exc:
            error = exc
    return {}, f"{type(error).__name__}: {error}" if error else "JSONDecodeError: empty output"


def report_counts(report: dict[str, Any]) -> tuple[int, int]:
    try:
        passed = int(report.get("passed"))
        total = int(report.get("total"))
    except (TypeError, ValueError):
        passed = total = 0
    if total > 0:
        return passed, total
    checks = report.get("checks")
    if isinstance(checks, list):
        rows = [row for row in checks if isinstance(row, dict)]
        return sum((row.get("status") == "pass") or (row.get("ok") is True) for row in rows), len(rows)
    summary = report.get("summary")
    if isinstance(summary, dict):
        try:
            passed = int(summary.get("passed") or 0)
            failed = int(summary.get("failed") or 0)
        except (TypeError, ValueError):
            return 0, 0
        return passed, passed + failed
    return 0, 0


def report_functional_ok(report: dict[str, Any]) -> bool:
    explicit = report.get("ok")
    if explicit is not None:
        return explicit is True
    passed, total = report_counts(report)
    status = report.get("status")
    if status is not None:
        return status == "pass" and total > 0 and passed == total
    failed = report.get("failed")
    if failed is not None:
        try:
            return int(failed) == 0 and total > 0 and passed == total
        except (TypeError, ValueError):
            return False
    # Historical authoritative suites often report only passed/total and use
    # their process return code for failure.  A complete count is sufficient;
    # run_suite still requires return_code == 0 and source immutability.
    return total > 0 and passed == total


def _terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        except Exception:
            if process.poll() is None:
                process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception:
            if process.poll() is None:
                process.kill()
    try:
        process.wait(timeout=10)
    except Exception:
        pass


def _seed_runtime(stage_source: Path, runtime_data: Path) -> None:
    source_data = stage_source / "data"
    if source_data.exists():
        shutil.copytree(source_data, runtime_data, dirs_exist_ok=True)
    else:
        runtime_data.mkdir(parents=True, exist_ok=True)


def run_suite(
    spec: SuiteSpec,
    *,
    source_root: Path = ROOT,
    workspace_parent: Path | None = None,
    keep_workspace: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    workspace = Path(tempfile.mkdtemp(prefix=f"eidolon-{spec.name}-", dir=workspace_parent))
    stage_source = workspace / "Eidolon"
    runtime_root = workspace / "runtime"
    runtime_data = runtime_root / "data"
    temp_root = runtime_root / "tmp"
    bytecode_root = runtime_root / "bytecode"
    output_root = workspace / "output"
    process_runtime_root = runtime_root / "process_runtime"
    metadata_lock_root = runtime_root / "metadata_locks"
    output_root.mkdir(parents=True, exist_ok=True)
    for path in (temp_root, bytecode_root, process_runtime_root, metadata_lock_root):
        path.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source_root, stage_source, ignore=_copy_ignore)
        _seed_runtime(stage_source, runtime_data)
        before = source_snapshot(stage_source)
        stdout_path = output_root / "stdout.log"
        stderr_path = output_root / "stderr.log"
        handoff_path = output_root / "worker-result.json"
        suite_command = [str(Path(sys.executable).resolve()), spec.script, *spec.arguments]
        operation_id = f"verify_{uuid.uuid4().hex}"
        previous_process_root = os.environ.get("EIDOLON_PROCESS_RUNTIME_ROOT")
        previous_lock_root = os.environ.get("EIDOLON_METADATA_LOCK_DIR")
        os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = str(process_runtime_root)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(metadata_lock_root)
        try:
            from process_ownership import accept_process_operation
            accepted = accept_process_operation(
                operation_id, operation_kind="isolated_verification", may_mutate=False,
                acceptance_key=f"{spec.name}:{uuid.uuid4().hex}",
            )
        finally:
            if previous_process_root is None:
                os.environ.pop("EIDOLON_PROCESS_RUNTIME_ROOT", None)
            else:
                os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = previous_process_root
            if previous_lock_root is None:
                os.environ.pop("EIDOLON_METADATA_LOCK_DIR", None)
            else:
                os.environ["EIDOLON_METADATA_LOCK_DIR"] = previous_lock_root
        if not accepted.get("ok"):
            raise RuntimeError(f"Could not accept isolated verification operation: {accepted.get('status')}")
        operation_generation = int(accepted.get("generation") or 0)
        worker_command = [
            str(Path(sys.executable).resolve()),
            "tools/isolated_suite_worker.py",
            "--cwd", str(stage_source),
            "--stdout", str(stdout_path),
            "--stderr", str(stderr_path),
            "--result", str(handoff_path),
            "--timeout", str(spec.timeout_seconds),
            "--handoff-grace", "15",
            "--command-json", json.dumps(suite_command),
            "--operation-id", operation_id,
            "--generation", str(operation_generation),
        ]
        existing_pythonpath = os.environ.get("PYTHONPATH", "")
        staged_pythonpath = str(stage_source)
        if existing_pythonpath:
            staged_pythonpath = os.pathsep.join((staged_pythonpath, existing_pythonpath))
        environment = {
            **os.environ,
            "EIDOLON_DATA_DIR": str(runtime_data),
            "EIDOLON_VERIFICATION_RUNTIME_ROOT": str(runtime_root),
            "EIDOLON_PROCESS_RUNTIME_ROOT": str(process_runtime_root),
            "EIDOLON_METADATA_LOCK_DIR": str(metadata_lock_root),
            "PYTHONPATH": staged_pythonpath,
            "PYTHONPYCACHEPREFIX": str(bytecode_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "TMPDIR": str(temp_root),
        }
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        popen_kwargs: dict[str, Any] = {} if os.name == "nt" else {"start_new_session": True}
        worker = subprocess.Popen(
            worker_command,
            cwd=stage_source,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            creationflags=creationflags,
            **popen_kwargs,
        )
        deadline = time.monotonic() + spec.timeout_seconds + 15
        while time.monotonic() < deadline and not handoff_path.exists() and worker.poll() is None:
            time.sleep(0.05)
        if handoff_path.exists():
            try:
                handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                handoff = {"return_code": -1, "timed_out": False, "handoff_error": True}
        else:
            handoff = {"return_code": -1, "timed_out": True, "handoff_error": True}
        # The worker deliberately remains alive after handoff so taskkill /T or
        # killpg can remove every descendant that survived the direct suite.
        _terminate_process_tree(worker)
        return_code = int(handoff.get("return_code", -1))
        timed_out = bool(handoff.get("timed_out"))
        command = suite_command
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        report, parse_error = ({}, "timeout") if timed_out else parse_json_report(stdout)
        after = source_snapshot(stage_source)
        modified = sorted(path for path in before.keys() & after.keys() if before[path] != after[path])
        added = sorted(after.keys() - before.keys())
        deleted = sorted(before.keys() - after.keys())
        immutable = not modified and not added and not deleted
        functional_ok = report_functional_ok(report)
        passed_count, total_count = report_counts(report)
        ok = not timed_out and return_code == 0 and functional_ok and immutable
        return {
            "name": spec.name,
            "ok": ok,
            "status": "pass" if ok else "fail",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "return_code": return_code,
            "timed_out": timed_out,
            "report": report,
            "passed": passed_count,
            "total": total_count,
            "parse_error": parse_error,
            "source_tree_unchanged": immutable,
            "source_changes": {"modified": modified, "added": added, "deleted": deleted},
            "stdout_tail": "\n".join(stdout.splitlines()[-20:]) if not functional_ok else "",
            "stderr_tail": "\n".join(stderr.splitlines()[-20:]),
            "command": command,
        }
    finally:
        if not keep_workspace:
            shutil.rmtree(workspace, ignore_errors=True)


def select_suites(profile: str, names: Iterable[str] = ()) -> tuple[SuiteSpec, ...]:
    requested = {name for name in names if name}
    selected = tuple(spec for spec in SUITES if profile in spec.profiles and (not requested or spec.name in requested))
    missing = requested - {spec.name for spec in selected}
    if missing:
        raise ValueError(f"unknown or unavailable suite names: {', '.join(sorted(missing))}")
    return selected


def build_report(profile: str, suite_names: Iterable[str] = (), *, progress: bool = False) -> dict[str, Any]:
    selected = select_suites(profile, suite_names)
    master_before = source_snapshot(ROOT)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    for spec in selected:
        if progress:
            print(f"[RUNNING] {spec.name}", file=sys.stderr, flush=True)
        result = run_suite(spec)
        results.append(result)
        if progress:
            print(f"[{'PASS' if result['ok'] else 'FAIL'}] {spec.name}: {result['passed']}/{result['total']}", file=sys.stderr, flush=True)
    master_after = source_snapshot(ROOT)
    master_unchanged = master_before == master_after
    passed_checks = sum(int(result.get("passed") or 0) for result in results)
    total_checks = sum(int(result.get("total") or 0) for result in results)
    ok = bool(results) and all(result.get("ok") is True for result in results) and master_unchanged
    return {
        "suite": "post-review-isolated-development-verification",
        "profile": profile,
        "ok": ok,
        "status": "pass" if ok else "fail",
        "passed": passed_checks,
        "total": total_checks,
        "suite_count": len(results),
        "source_tree_unchanged": master_unchanged,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("core", "full"), default="full")
    parser.add_argument("--suite", action="append", default=[])
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    if args.list:
        payload = {"suites": [asdict(spec) for spec in SUITES]}
        print(json.dumps(payload, indent=2))
        return 0
    try:
        report = build_report(args.profile, args.suite, progress=args.progress)
    except ValueError as exc:
        print(json.dumps({"ok": False, "status": "fail", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(report, indent=2 if args.json else None))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

# v1205.0-v1205.2 general small-project implementation consolidation
# tools/v1205_0_2_general_small_project_consolidation_tests.py

# v1205.3-v1205.5 broader selected-project compatibility and mixed operations
# tools/v1205_3_5_selected_project_mixed_operations_tests.py

# v1205.6-v1205.8 general small-project reliability and adversarial hardening
# tools/v1205_6_8_general_small_project_reliability_hardening_tests.py

# v1205.9 general small-project implementation checkpoint
# tools/v1205_9_general_small_project_implementation_checkpoint_tests.py
# Mixed conversational/action turns remain incomplete and are deferred to v1206.0-v1206.2.
