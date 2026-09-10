from __future__ import annotations

"""One-command verification for an Eidolon source release."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import signal
import tempfile
import time
import sys
sys.dont_write_bytecode = True
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_INTEGRITY_BEHAVIOR_SUITES = (
    ("v2730-product-integrity-behavior", "tools/v2730_0_product_integrity_behavior_tests.py"),
    ("v2730-verification-quality-policy", "tools/v2730_4_verification_quality_policy_tests.py"),
    ("v2730-product-integrity-checkpoint", "tools/v2730_9_product_integrity_repair_architecture_freeze_checkpoint_tests.py"),
    ("v2730.9.1-pretesting-integrity-repair-checkpoint", "tools/v2730_9_1_pretesting_integrity_repair_checkpoint_tests.py"),
    ("v2730.9.2-pretesting-reliability-truthfulness", "tools/v2730_9_2_pretesting_reliability_truthfulness_tests.py"),
    ("v2730.9.3-review-repairs", "tools/v2730_9_3_review_repairs_tests.py"),
)

V1489_BROWSER_FOCUSED_SUITES = (
    ("v1489-browser-b01", "tools/v1489_0001_0010_trial3_review_closure_tests.py"),
    ("v1489-browser-b02", "tools/v1489_0011_0020_memory_provenance_integrity_tests.py"),
    ("v1489-browser-b03", "tools/v1489_0021_0030_correction_recall_reliability_tests.py"),
    ("v1489-browser-b04", "tools/v1489_0031_0040_natural_conversation_quality_tests.py"),
    ("v1489-browser-b05", "tools/v1489_0041_0050_relationship_preference_continuity_tests.py"),
    ("v1489-browser-b06", "tools/v1489_0051_0060_conversation_command_distinction_tests.py"),
    ("v1489-browser-b07", "tools/v1489_0061_0070_action_truth_receipts_tests.py"),
    ("v1489-browser-b08", "tools/v1489_0071_0080_exactly_once_recovery_tests.py"),
    ("v1489-browser-b09", "tools/v1489_0081_0090_response_time_reduction_tests.py"),
    ("v1489-browser-b10", "tools/v1489_0091_0100_provider_reliability_tests.py"),
    ("v1489-browser-b11", "tools/v1489_0101_0110_desktop_chat_usability_tests.py"),
    ("v1489-browser-b12", "tools/v1489_0111_0120_accessibility_input_hardening_tests.py"),
    ("v1489-browser-b13", "tools/v1489_0121_0130_governed_initiative_tests.py"),
    ("v1489-browser-b14", "tools/v1489_0131_0140_reasoning_planning_quality_tests.py"),
    ("v1489-browser-b15", "tools/v1489_0141_0150_practical_coding_capability_tests.py"),
    ("v1489-browser-b16", "tools/v1489_0151_0160_supervised_self_development_tests.py"),
    ("v1489-browser-b17", "tools/v1489_0161_0170_security_privacy_authority_tests.py"),
    ("v1489-browser-b18", "tools/v1489_0171_0180_verification_evidence_quality_tests.py"),
    ("v1489-browser-b20", "tools/v1489_0191_0200_integrated_completion_benchmark_tests.py"),
    ("v1489-browser-b19", "tools/v1489_0181_0190_installation_upgrade_rollback_tests.py"),
    ("v1489-product-capability-integration", "tools/v1489_product_capability_integration_tests.py"),
    ("v1489-generic-self-development-execution", "tools/v1489_generic_self_development_execution_tests.py"),
    ("v1489-symbol-level-refactoring", "tools/v1489_symbol_level_refactoring_tests.py"),
)

V1490_BROWSER_FOCUSED_SUITES = (
    ("v1490-dynamic-improvement-discovery-foundations", "tools/v1490_0_2_dynamic_improvement_discovery_tests.py"),
    ("v1490-dynamic-discovery-hardening", "tools/v1490_3_9_dynamic_discovery_hardening_tests.py"),
    ("v1491-dynamic-candidate-quality", "tools/v1491_dynamic_candidate_quality_tests.py"),
    ("v1492-dynamic-development-backlog", "tools/v1492_dynamic_development_backlog_tests.py"),
    ("v1493-dynamic-implementation-planning", "tools/v1493_dynamic_implementation_planning_tests.py"),
    ("v1494-generalized-isolated-coding", "tools/v1494_generalized_isolated_coding_tests.py"),
    ("v1495-bounded-failure-diagnosis", "tools/v1495_bounded_failure_diagnosis_tests.py"),
    ("v1496-verification-intelligence", "tools/v1496_verification_intelligence_tests.py"),
    ("v1497-governed-candidate-review", "tools/v1497_governed_candidate_review_tests.py"),
    ("v1498-continuous-development-campaign", "tools/v1498_continuous_development_campaign_tests.py"),
    ("v1499-windows-certification-protocol", "tools/v1499_windows_certification_protocol_tests.py"),
    ("v1500-autonomous-developer-benchmark", "tools/v1500_autonomous_developer_benchmark_tests.py"),
    ("v1500-authority-integration-repair", "tools/v1500_0_1_authority_integration_repair_tests.py"),
    ("v1500.1-conversation-memory-identity-repair", "tools/v1500_1_conversation_memory_identity_repair_tests.py"),
    ("v1500.2-entity-association-foundation", "tools/v1500_2_entity_association_foundation_tests.py"),
    ("v1500.3-conversation-entity-associations", "tools/v1500_3_conversation_entity_association_tests.py"),
    ("v1500.4-entity-association-curation", "tools/v1500_4_entity_association_curation_tests.py"),
    ("v1500.5-conversational-association-governance", "tools/v1500_5_conversational_association_governance_tests.py"),
    ("v1500.6-dashboard-simplification-performance", "tools/v1500_6_dashboard_simplification_performance_tests.py"),
    ("v1500.7-natural-association-coherence", "tools/v1500_7_natural_association_coherence_tests.py"),
    ("v1500.8-conversation-target-continuity", "tools/v1500_8_conversation_target_continuity_tests.py"),
    ("v1500.9-integrated-daily-use-conversation", "tools/v1500_9_integrated_daily_use_conversation_tests.py"),
    ("v1500.9.1-release-self-knowledge", "tools/v1500_9_1_release_self_knowledge_tests.py"),
    ("v1500.9.2-conversation-evidence-boundary", "tools/v1500_9_2_conversation_evidence_boundary_tests.py"),
    ("v1500.9.3-wish-command-boundary", "tools/v1500_9_3_wish_command_boundary_tests.py"),
    ("v1501.0-supervised-initiative-queue", "tools/v1501_0_supervised_initiative_queue_tests.py"),
    ("v1501.0.1-source-only-workspace-boundary-repair", "tools/v1501_0_1_source_only_workspace_boundary_repair_tests.py"),
    ("v1501.1-candidate-review-installation", "tools/v1501_1_candidate_review_installation_tests.py"),
    ("v1501.2-sustained-supervised-initiative", "tools/v1501_2_sustained_supervised_initiative_tests.py"),
    ("v1501.3-initiative-evidence-intake", "tools/v1501_3_initiative_evidence_intake_tests.py"),
    ("v2500-portfolio-product-planning", "tools/evidence_to_candidate_planner_tests.py"),
    ("v2500-product-plan-lifecycle", "tools/product_plan_lifecycle_tests.py"),
    ("isolated-coding-provider-envelope", "tools/isolated_coding_provider_envelope_tests.py"),
    ("v2500.9.1-daily-use-conversation-grounding", "tools/v2500_9_1_daily_use_conversation_grounding_tests.py"),
    ("v2501.0-bounded-autonomous-web-research", "tools/v2501_0_bounded_autonomous_web_research_tests.py"),
    ("v2501.1-governed-public-web-research-adapter", "tools/v2501_1_governed_public_web_research_adapter_tests.py"),
    ("v2501.2-research-question-decomposition", "tools/v2501_2_research_question_decomposition_tests.py"),
    ("v2501.3-source-strategy", "tools/v2501_3_source_strategy_tests.py"),
    ("v2501.4-search-query-planning", "tools/v2501_4_search_query_planning_tests.py"),
    ("v2501.5-evidence-extraction", "tools/v2501_5_evidence_extraction_tests.py"),
    ("v2501.6-cross-source-comparison", "tools/v2501_6_cross_source_comparison_tests.py"),
    ("v2501.7-cited-conclusion-assembly", "tools/v2501_7_cited_conclusion_assembly_tests.py"),
    ("v2501.8-research-session-integration-ux", "tools/v2501_8_research_session_integration_ux_tests.py"),
    ("v2501.9-desktop-research-acceptance", "tools/v2501_9_desktop_research_acceptance_tests.py"),
    ("v2502.0-conversational-research-routing", "tools/v2502_0_conversational_research_routing_tests.py"),
    ("v2502.1-research-progress-cancellation-reconnect", "tools/v2502_1_research_progress_cancellation_reconnect_tests.py"),
    ("v2502.2-research-result-review-citation-quality", "tools/v2502_2_research_result_review_citation_quality_tests.py"),
    ("v2502.3-durable-research-session-history", "tools/v2502_3_durable_research_session_history_tests.py"),
    ("v2502.4-evidence-summary-comparison", "tools/v2502_4_evidence_summary_comparison_tests.py"),
    ("v2502.5-bounded-cited-report-export", "tools/v2502_5_bounded_cited_report_export_tests.py"),
    ("v2502.6-research-question-decomposition", "tools/v2502_6_research_question_decomposition_tests.py"),
    ("v2502.7-source-strategy-adaptive-follow-up", "tools/v2502_7_source_strategy_adaptive_follow_up_tests.py"),
    ("v2502.8-synthesis-quality-campaign-consolidation", "tools/v2502_8_synthesis_quality_campaign_consolidation_tests.py"),
    ("v2502.9-desktop-research-intelligence-gate", "tools/v2502_9_desktop_research_intelligence_gate_tests.py"),
    ("v2503.0-research-planning-native-synthesis-repair", "tools/v2503_0_research_planning_native_synthesis_repair_tests.py"),
    ("v2503.1-source-quality-synthesis-desktop-edit", "tools/v2503_1_source_quality_synthesis_desktop_edit_tests.py"),
    ("v2503.2-candidate-specific-evidence-follow-up", "tools/v2503_2_candidate_specific_evidence_follow_up_tests.py"),
    ("v2503.3-source-independence-recommendation-confidence", "tools/v2503_3_source_independence_recommendation_confidence_tests.py"),
    ("v2503.4-evidence-language-consistency-source-quality", "tools/v2503_4_evidence_language_consistency_source_quality_tests.py"),
    ("v2503.4.1-research-finding-routing-anti-overfit", "tools/v2503_4_1_research_finding_routing_anti_overfit_tests.py"),
    ("v2503.4.2-one-command-product-repair-cycle", "tools/v2503_4_2_one_command_product_repair_cycle_tests.py"),
    ("v2503.4.3-dedicated-syntax-repair", "tools/v2503_4_3_dedicated_syntax_repair_tests.py"),
    ("v2503.4.4-duplicate-anchor-repair", "tools/v2503_4_4_duplicate_anchor_repair_tests.py"),
    ("v2503.4.5-sequential-anchor-context", "tools/v2503_4_5_sequential_anchor_context_tests.py"),
    ("v2503.4.6-parser-grounded-syntax-repair", "tools/v2503_4_6_parser_grounded_syntax_repair_tests.py"),
    ("v2503.4.7-deterministic-anchor-selection", "tools/v2503_4_7_deterministic_anchor_selection_tests.py"),
    ("v2503.4.8-anchor-occurrence-fallback", "tools/v2503_4_8_anchor_occurrence_fallback_tests.py"),
    ("v2503.4.9-provider-anchor-drift-recovery", "tools/v2503_4_9_provider_anchor_drift_recovery_tests.py"),
    ("v2503.4.10-anchor-intent-binding", "tools/v2503_4_10_anchor_intent_binding_tests.py"),
    ("v2503.4.11-missing-anchor-classification", "tools/v2503_4_11_missing_anchor_classification_tests.py"),
    ("v2503.4.12-grounded-missing-anchor-repair", "tools/v2503_4_12_grounded_missing_anchor_repair_tests.py"),
    ("v2503.4.13-training-evidence-recorder", "tools/v2503_4_13_training_evidence_recorder_tests.py"),
    ("v2503.4.14-training-sanitization", "tools/v2503_4_14_training_sanitization_tests.py"),
    ("v2503.4.15-training-quality-export", "tools/v2503_4_15_training_quality_export_tests.py"),
    ("v2503.4.16-training-capture-adapters", "tools/v2503_4_16_training_capture_adapter_tests.py"),
    ("v2503.4.17-opt-in-training-workflow-capture", "tools/v2503_4_17_opt_in_training_workflow_capture_tests.py"),
    ("v2503.4.18-training-alpha-ii", "tools/v2503_4_18_training_record_schema_tests.py"),
    ("v2503.4.19-training-alpha-ii", "tools/v2503_4_19_training_dedup_diversity_tests.py"),
    ("v2503.4.20-training-alpha-ii", "tools/v2503_4_20_training_privacy_expansion_tests.py"),
    ("v2503.4.21-training-alpha-ii", "tools/v2503_4_21_preference_pair_tests.py"),
    ("v2503.4.22-training-alpha-ii", "tools/v2503_4_22_training_quality_v2_tests.py"),
    ("v2503.4.23-training-alpha-ii", "tools/v2503_4_23_dataset_version_balance_tests.py"),
    ("v2503.4.24-training-alpha-ii", "tools/v2503_4_24_frozen_eval_corpus_tests.py"),
    ("v2503.4.25-training-alpha-ii", "tools/v2503_4_25_baseline_benchmark_tests.py"),
    ("v2503.4.26-training-alpha-ii", "tools/v2503_4_26_model_comparison_tests.py"),
    ("v2503.4.27-training-alpha-ii", "tools/v2503_4_27_model_registry_tests.py"),
    ("v2503.4.28-training-alpha-ii", "tools/v2503_4_28_training_readiness_checkpoint_tests.py"),
    ("v2503.4.28.1-training-alpha-ii-audit-repair", "tools/v2503_4_28_1_training_evidence_audit_repair_tests.py"),
    ("v2503.4.28.2-training-alpha-ii-triple-audit-repair", "tools/v2503_4_28_2_training_evidence_triple_audit_repair_tests.py"),
    ("v2503.4.30-training-alpha-iii-provenance-benchmark", "tools/v2503_4_30_training_provenance_benchmark_tests.py"),
    ("v2503.4.30.1-training-alpha-iii-audit-repair", "tools/v2503_4_30_1_training_provenance_benchmark_audit_tests.py"),
    ("v2503.4.30.2-training-anchor-integration", "tools/v2503_4_30_2_training_anchor_merge_tests.py"),
    ("v2503.4.39-training-operatorization", "tools/v2503_4_39_training_operatorization_acceptance_tests.py"),
    ("v2503.5.0-candidate-specific-evidence-discovery", "tools/v2503_5_candidate_specific_evidence_discovery_tests.py"),
)

V1701_BROWSER_FOCUSED_SUITES = (
    ("v1725.9-requirements-problem-framing", "tools/v1725_9_requirements_problem_framing_checkpoint_tests.py"),
    ("v1750.9-causal-counterfactual-reasoning", "tools/v1750_9_causal_counterfactual_reasoning_checkpoint_tests.py"),
    ("v1775.9-long-horizon-planning", "tools/v1775_9_long_horizon_planning_checkpoint_tests.py"),
    ("v1799.9-metacognition-epistemic-control", "tools/v1799_9_metacognition_epistemic_control_checkpoint_tests.py"),
    ("v1799.9-era3-integrated-reasoning", "tools/v1799_9_era3_integrated_reasoning_campaign_tests.py"),
    ("v1800.9-era3-desktop-cognitive-gate", "tools/v1800_9_era3_desktop_cognitive_gate_tests.py"),
)

V1801_BROWSER_FOCUSED_SUITES = (
    ("v1825.9-memory-consolidation-retrieval", "tools/v1825_9_memory_consolidation_retrieval_checkpoint_tests.py"),
    ("v1850.9-temporal-identity", "tools/v1850_9_temporal_identity_checkpoint_tests.py"),
    ("v1875.9-revisable-belief-world-model", "tools/v1875_9_revisable_belief_world_model_checkpoint_tests.py"),
    ("v1899.9-knowledge-maintenance", "tools/v1899_9_knowledge_maintenance_checkpoint_tests.py"),
    ("v1899.9-era4-integrated-memory-world-model", "tools/v1899_9_era4_integrated_memory_world_model_tests.py"),
    ("v1900.9-era4-desktop-memory-world-model-gate", "tools/v1900_9_era4_desktop_memory_world_model_gate_tests.py"),
)

V1901_BROWSER_FOCUSED_SUITES = (
    ("v1925.9-discourse-conversational-flow", "tools/v1925_9_discourse_conversational_flow_tests.py"),
    ("v1950.9-personality-identity-expression", "tools/v1950_9_personality_identity_expression_tests.py"),
    ("v1975.9-emotional-architecture-regulation", "tools/v1975_9_emotional_architecture_regulation_tests.py"),
    ("v1999.9-relationship-companion-continuity", "tools/v1999_9_relationship_companion_continuity_tests.py"),
    ("v1999.9-era5-integrated-companion", "tools/v1999_9_era5_integrated_companion_tests.py"),
    ("v2000.9-era5-desktop-daily-companion-coherence-gate", "tools/v2000_9_era5_desktop_daily_companion_coherence_gate_tests.py"),
)

V2001_BROWSER_FOCUSED_SUITES = (
    ("v2025.9-attention-salience", "tools/v2025_9_attention_salience_checkpoint_tests.py"),
    ("v2050.9-background-scheduler", "tools/v2050_9_background_scheduler_checkpoint_tests.py"),
    ("v2075.9-proactive-communication", "tools/v2075_9_proactive_communication_checkpoint_tests.py"),
    ("v2099.9-resource-concurrency", "tools/v2099_9_resource_concurrency_checkpoint_tests.py"),
    ("v2099.9-era6-integrated-attention-initiative", "tools/v2099_9_era6_integrated_attention_initiative_tests.py"),
    ("v2100.9-era6-desktop-attention-initiative-gate", "tools/v2100_9_era6_desktop_attention_initiative_gate_tests.py"),
)

V2101_BROWSER_FOCUSED_SUITES = (
    ("v2125.9-local-system-application-tools", "tools/v2125_9_local_system_application_tools_tests.py"),
    ("v2150.9-research-web-intelligence", "tools/v2150_9_research_web_intelligence_tests.py"),
    ("v2175.9-voice-audio-presence", "tools/v2175_9_voice_audio_presence_tests.py"),
    ("v2199.9-multimodal-context", "tools/v2199_9_multimodal_context_tests.py"),
    ("v2199.9-era7-integrated-interaction", "tools/v2199_9_era7_integrated_interaction_tests.py"),
    ("v2200.9-era7-desktop-gate", "tools/v2200_9_era7_desktop_gate_tests.py"),
)

V2201_BROWSER_FOCUSED_SUITES = (
    ("v2225.9-fine-grained-authority", "tools/v2225_9_fine_grained_authority_permissions_tests.py"),
    ("v2250.9-untrusted-content-defense", "tools/v2250_9_untrusted_content_defense_tests.py"),
    ("v2275.9-fault-tolerance-recovery", "tools/v2275_9_fault_tolerance_recovery_tests.py"),
    ("v2299.9-audit-incident-response", "tools/v2299_9_audit_incident_response_tests.py"),
    ("v2299.9-era8-integrated-trustworthy-operation", "tools/v2299_9_era8_integrated_trustworthy_operation_tests.py"),
    ("v2300.9-era8-desktop-gate", "tools/v2300_9_era8_desktop_gate_tests.py"),
    ("v2300.9-era8-windows-native", "tools/v2300_9_era8_windows_native_tests.py"),
)

V2301_BROWSER_FOCUSED_SUITES = (
    ("v2325.9-outcome-learning", "tools/v2325_9_outcome_learning_checkpoint_tests.py"),
    ("v2350.9-preference-adaptation", "tools/v2350_9_preference_adaptation_checkpoint_tests.py"),
    ("v2375.9-cooperative-development", "tools/v2375_9_cooperative_development_checkpoint_tests.py"),
    ("v2399.9-grounded-self-model", "tools/v2399_9_grounded_self_model_checkpoint_tests.py"),
    ("v2399.9-era9-integrated-mind", "tools/v2399_9_era9_integrated_mind_tests.py"),
    ("v2400.9-era9-desktop-integrated-mind-gate", "tools/v2400_9_era9_desktop_integrated_mind_gate_tests.py"),
    ("v2400.9-era9-windows-native", "tools/v2400_9_era9_windows_native_tests.py"),
)

V2401_BROWSER_FOCUSED_SUITES = (
    ("v2425.9-desktop-product-maturity", "tools/v2425_9_desktop_product_maturity_tests.py"),
    ("v2450.9-unattended-operation-soak", "tools/v2450_9_unattended_operation_soak_tests.py"),
    ("v2475.9-autonomous-developer-beta", "tools/v2475_9_autonomous_developer_beta_tests.py"),
    ("v2499.9-autonomy-benchmark-prep", "tools/v2499_9_autonomy_benchmark_preparation_tests.py"),
    ("v2499.9-era10-integrated-product-autonomy", "tools/v2499_9_era10_integrated_product_autonomy_tests.py"),
    ("v2500.9-era10-desktop-adversarial-gate", "tools/v2500_9_era10_desktop_adversarial_gate_tests.py"),
    ("v2500.9-era10-windows-native", "tools/v2500_9_era10_windows_native_tests.py"),
)
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(TOOLS))

from package_integrity import iter_source_tree_entries
from verification_evidence import (
    DASHBOARD_ROUTE_TIMEOUTS as EVIDENCE_DASHBOARD_ROUTE_TIMEOUTS,
    ENV_ATTESTATION_KEY,
    ENV_EVIDENCE_FILE,
    ENV_EVIDENCE_PURPOSE,
    ENV_EXPECTED_PRODUCER,
    ENV_INVOCATION_NONCE,
    ENV_SOURCE_SNAPSHOT,
    build_evidence_bundle,
    build_stage_receipt,
    expected_stage_commands,
    isoformat_utc,
    new_attestation_key,
    new_invocation_nonce,
    source_snapshot_digest,
    validate_evidence_bundle,
    write_evidence_bundle,
)

DASHBOARD_PROBE_WORKER = TOOLS / "dashboard_probe_worker.py"
DASHBOARD_ROUTE_TIMEOUTS: dict[str, int] = dict(EVIDENCE_DASHBOARD_ROUTE_TIMEOUTS)
DASHBOARD_WORKER_GRACE_SECONDS = 30
INFRASTRUCTURE_DIR_NAMES = {".git", ".venv", "venv"}
CONFIGURATION_EXACT_PATHS = {
    "data/settings.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
    "data/signing/trusted_public_keys.json",
    "data/signing_trust_policy.json",
}
CONFIGURATION_PREFIXES = ("data/workspaces/command_profiles/",)
SOURCE_SUFFIXES = {".py", ".md", ".ps1", ".sh", ".txt", ".toml", ".cfg", ".ini", ".json"}

# Historical version-local stage inventories live in the segmented verifier.
# Keep this module focused on bounded daily/full release gates rather than
# retaining a second, dead policy inventory that can drift from executable
# selection behavior.
# The quick profile is a daily/current-release gate, not a historical replay.
# Keep only the attested release-integrity spine plus the latest integrated
# Desktop/research gate and the current-version focused regression. Older
# acceptance/checkpoint suites remain available in ``full`` and exhaustive
# historical coverage remains resumable in segmented_release_verify.py.
QUICK_PARALLEL_CORE_STAGE_NAMES = (
    "python-compile",
    "version-inventory",
    "corrective-suite",
    "import-compatibility",
)

QUICK_STAGE_NAMES = {
    "python-compile",
    "version-inventory",
    "corrective-suite",
    "import-compatibility",
    "dashboard-http-probe",
    "release-integrity",
    "smoke",
    "source-only-runtime-boundary",
    "v2730-product-integrity-behavior",
    "v2730-verification-quality-policy",
    "v2730-product-integrity-checkpoint",
    "v2730.9.1-pretesting-integrity-repair-checkpoint",
    "v2730.9.2-pretesting-reliability-truthfulness",
    "v2730.9.3-review-repairs",
    "v2502.9-desktop-research-intelligence-gate",
    "v2503.4.39-training-operatorization",
    "v2503.5.0-candidate-specific-evidence-discovery",
}

# Full preserves the broader high-signal acceptance set that previously ran in
# quick. This is intentionally separate from the segmented historical verifier:
# full is the bounded release-confidence gate; segmented is the exhaustive,
# resumable archaeology department.
FULL_STAGE_NAMES = set(QUICK_STAGE_NAMES) | {
    "v2503.4.30-training-alpha-iii-provenance-benchmark",
    "v2503.4.28.1-training-alpha-ii-audit-repair",
    "v2503.4.17-opt-in-training-workflow-capture",
    "v1250.0-authoritative-cleanup-baseline",
    "v1250.1-segmented-broad-verifier",
    "v1250.2-hermetic-verification-runtime",
    "v1300.9.1-desktop-checkpoint-coherence-repair",
    "v1450.9-desktop-alpha-checkpoint",
    "v2500.9.1-daily-use-conversation-grounding",
    "v2501.0-bounded-autonomous-web-research",
    "v2501.1-governed-public-web-research-adapter",
    "v2501.9-desktop-research-acceptance",
    "v2502.2-research-result-review-citation-quality",
    "v2502.7-source-strategy-adaptive-follow-up",
    "v2503.2-candidate-specific-evidence-follow-up",
    "v2503.3-source-independence-recommendation-confidence",
    "v2503.4-evidence-language-consistency-source-quality",
    "v2503.4.12-grounded-missing-anchor-repair",
    "v2503.4.13-training-evidence-recorder",
    "v2503.4.14-training-sanitization",
    "v2503.4.15-training-quality-export",
    "v2503.4.16-training-capture-adapters",
}
FULL_STAGE_NAME_MARKERS = (
    "provider-readiness-offline-recovery",
    "daily-companion-resume-draft-continuity",
    "multi-tab-conversation-coordination",
    "conversational-responsiveness-companion-quality",
    "offline-conversation-degradation",
    "native-conversation-validation",
    "relationship-continuity-fixtures",
)


def stage_selected_for_profile(profile: str, name: str) -> bool:
    if profile == "quick":
        return name in QUICK_STAGE_NAMES
    if profile == "full":
        return name in FULL_STAGE_NAMES or any(marker in name for marker in FULL_STAGE_NAME_MARKERS)
    return False

SUPPLEMENTAL_RECEIPT_STAGE_NAMES = {
    "final-checkpoint-hardening-fixtures",
    "reviewed-candidate-repair-fixtures",
}

SUPERSEDED_INSTALL_RELEASE_CHECKS: tuple[str, ...] = (
    "operator-governed-metadata-release-integrity-v1",
    "release-gate-stale-assertion-truth-repair-v1",
    "install-release-segment-blocker-classification-v1",
    "release-archive-and-recovery-gate-boundedness-repair-v1",
    "install-release-segment-evidence-summary-gate-v1",
    "audited-sandbox-backend-evidence-interface-v1",
    "dashboard-route-registry-extraction-v1",
    "dashboard-dispatcher-branch-extraction-prep-v1",
    "dashboard-dispatcher-branch-extraction-trial-v1",
    "dashboard-dispatcher-branch-extraction-backfill-v1",
    "dashboard-dispatcher-branch-helper-consolidation-v1",
    "dashboard-dispatcher-branch-extraction-expansion-prep-v1",
    "dashboard-dispatcher-branch-expansion-trial-v1",
    "dashboard-dispatcher-branch-expansion-backfill-prep-v1",
    "dashboard-dispatcher-branch-expansion-backfill-trial-v1",
    "dashboard-dispatcher-branch-decomposition-continuation-prep-v1",
    "dashboard-dispatcher-branch-decomposition-continuation-trial-v1",
    "dashboard-dispatcher-branch-decomposition-continuation-prep-v2",
    "dashboard-dispatcher-branch-decomposition-continuation-trial-v2",
    "dashboard-dispatcher-branch-decomposition-continuation-prep-v3",
    "dashboard-dispatcher-branch-decomposition-continuation-trial-v3",
)


def _skip_check_args(names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value for name in names for value in ("--skip-check", name))

FULL_RELEASE_SMOKE_STEPS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    # The release tier already includes every fast/loop/readiness check. Running
    # a separate readiness tier duplicated 26 authoritative checks without
    # adding coverage, so full verification executes the superset once.
    ("release", ("--tier", "release"), 2400),
    # These three release checks are already executed by the release tier above.
    # The smoke CLI records each explicit skip as outer-verifier-owned evidence.
    ("install-release", (
        "--segment", "install-release",
        "--skip-check", "code-patch-release",
        "--skip-check", "release-pipeline",
        "--skip-check", "approval-release-workflow",
        *_skip_check_args(SUPERSEDED_INSTALL_RELEASE_CHECKS),
    ), 7200),
    ("install-regression-recent", (
        "--segment", "install-regression-recent",
        "--skip-check", "current-state-integrity-staleness-hardening-v1",
    ), 3600),
)


@dataclass
class VerificationStep:
    name: str
    status: str
    summary: str
    details: Any = None
    elapsed_seconds: float | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"pass", "warn"}


def _classify_tree_path(relative: str) -> str:
    clean = relative.replace("\\", "/")
    parts = set(Path(clean).parts)
    suffix = Path(clean).suffix.lower()
    if "__pycache__" in parts or suffix == ".pyc":
        return "bytecode"
    if clean in CONFIGURATION_EXACT_PATHS or clean.startswith(CONFIGURATION_PREFIXES):
        return "configuration"
    if clean.startswith("data/") or clean.startswith("sandbox/"):
        return "runtime"
    if suffix in {".tmp", ".temp"} or Path(clean).name.startswith(("tmp", ".tmp")):
        return "temporary"
    if suffix in SOURCE_SUFFIXES or clean in {"eidolon.py", ".gitignore"}:
        return "source"
    return "unexpected"


def _source_tree_snapshot(root: Path = ROOT) -> dict[str, Any]:
    """Hash every file and directory in the extracted tree.

    Only repository/tooling infrastructure is outside this scope. Runtime data,
    sandbox files, temporary artifacts, bytecode, and unexpected additions are
    intentionally included.
    """
    hashes: dict[str, str] = {}
    directories: list[str] = []
    errors: list[dict[str, str]] = []
    project_root = Path(root).resolve()
    for current, child_directories, names in os.walk(project_root):
        child_directories[:] = [name for name in child_directories if name not in INFRASTRUCTURE_DIR_NAMES]
        current_path = Path(current)
        if current_path != project_root:
            directories.append(current_path.relative_to(project_root).as_posix())
        for name in names:
            path = current_path / name
            relative = path.relative_to(project_root).as_posix()
            try:
                hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                errors.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
    return {"hashes": hashes, "directories": sorted(directories), "errors": errors}


def _source_tree_immutability_step(before: dict[str, Any], after: dict[str, Any]) -> tuple[VerificationStep, dict[str, Any]]:
    before_hashes = dict(before.get("hashes") or {})
    after_hashes = dict(after.get("hashes") or {})
    modified = [
        {"path": path, "before_sha256": before_hashes[path], "after_sha256": after_hashes[path]}
        for path in sorted(before_hashes.keys() & after_hashes.keys())
        if before_hashes[path] != after_hashes[path]
    ]
    added = [
        {"path": path, "after_sha256": after_hashes[path]}
        for path in sorted(after_hashes.keys() - before_hashes.keys())
    ]
    deleted = [
        {"path": path, "before_sha256": before_hashes[path]}
        for path in sorted(before_hashes.keys() - after_hashes.keys())
    ]
    before_directories = set(before.get("directories") or [])
    after_directories = set(after.get("directories") or [])
    added_directories = sorted(after_directories - before_directories)
    deleted_directories = sorted(before_directories - after_directories)
    errors = [*(before.get("errors") or []), *(after.get("errors") or [])]
    write_paths = [row["path"] for row in modified] + [row["path"] for row in added] + added_directories
    delete_paths = [row["path"] for row in deleted] + deleted_directories
    dimensions = {
        category: {
            "write_count": sum(_classify_tree_path(path) == category for path in write_paths),
            "delete_count": sum(_classify_tree_path(path) == category for path in delete_paths),
        }
        for category in ("source", "configuration", "runtime", "bytecode", "temporary", "unexpected")
    }
    details = {
        "before_file_count": len(before_hashes),
        "after_file_count": len(after_hashes),
        "before_directory_count": len(before_directories),
        "after_directory_count": len(after_directories),
        "modified": modified,
        "added": added,
        "deleted": deleted,
        "added_directories": added_directories,
        "deleted_directories": deleted_directories,
        "snapshot_errors": errors,
        "source_write_count": len(write_paths),
        "source_delete_count": len(delete_paths),
        "write_dimensions": dimensions,
        "scope_excludes": sorted(INFRASTRUCTURE_DIR_NAMES),
    }
    ok = not errors and not write_paths and not delete_paths
    return (
        VerificationStep(
            "source-tree-immutability",
            "pass" if ok else "fail",
            "Every extracted-tree file and directory remained unchanged for the entire verification run."
            if ok
            else "Verification changed the extracted tree or could not complete the whole-tree comparison.",
            details,
        ),
        details,
    )


def _seed_runtime_data(project_root: Path, runtime_data_dir: Path) -> list[str]:
    seeded: list[str] = []
    for relative in iter_source_tree_entries(project_root):
        if not relative.startswith("data/"):
            continue
        source = project_root / relative
        destination = runtime_data_dir / Path(relative).relative_to("data")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        seeded.append(relative)
    return seeded


def _runtime_environment(runtime_root: Path) -> tuple[dict[str, str], list[str]]:
    data_dir = runtime_root / "data"
    temp_dir = runtime_root / "tmp"
    bytecode_dir = runtime_root / "bytecode"
    for path in (data_dir, temp_dir, bytecode_dir):
        path.mkdir(parents=True, exist_ok=True)
    seeded = _seed_runtime_data(ROOT, data_dir)
    environment = {
        "EIDOLON_DATA_DIR": str(data_dir),
        "EIDOLON_VERIFICATION_RUNTIME_ROOT": str(runtime_root),
        "PYTHONPYCACHEPREFIX": str(bytecode_dir),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "TMPDIR": str(temp_dir),
        "PYTHONPATH": str(ROOT),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    return environment, seeded


def _production_launcher_environment(runtime_environment: dict[str, str]) -> dict[str, str]:
    """Return production-launch parity env from the already isolated runtime env.

    Deliberately omits repository-root PYTHONPATH so runtime-status cannot pass
    only because the verifier supplied an import path production launchers do not.
    The input environment is copied and is never mutated or reseeded.
    """
    environment = dict(runtime_environment)
    environment.pop("PYTHONPATH", None)
    return environment


def _fixture_environment(runtime_root: Path) -> dict[str, str]:
    """Create an empty isolated runtime for deterministic fixture stages."""
    data_dir = runtime_root / "data"
    temp_dir = runtime_root / "tmp"
    bytecode_dir = runtime_root / "bytecode"
    for path in (data_dir, temp_dir, bytecode_dir):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "EIDOLON_DATA_DIR": str(data_dir),
        "EIDOLON_VERIFICATION_RUNTIME_ROOT": str(runtime_root),
        "PYTHONPYCACHEPREFIX": str(bytecode_dir),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "TMPDIR": str(temp_dir),
        "PYTHONPATH": str(ROOT),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }


def _command_temp_parent(env_overrides: dict[str, str] | None) -> Path | None:
    if not env_overrides:
        return None
    runtime_root = env_overrides.get("EIDOLON_VERIFICATION_RUNTIME_ROOT")
    if not runtime_root:
        return None
    path = Path(runtime_root) / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _integrity_report(
    evidence_path: Path,
    *,
    env_overrides: dict[str, str],
) -> tuple[VerificationStep, dict[str, Any]]:
    command = [
        sys.executable,
        str(AGENT / "registry_navigation_smoke_consolidation.py"),
        "--root",
        str(ROOT),
        "--json",
        "--evidence-file",
        str(evidence_path),
    ]
    return _run_json_report(
        command,
        timeout=600,
        performance_budget_seconds=300,
        env_overrides=env_overrides,
    )


def _run(
    command: list[str],
    *,
    timeout: int,
    env_overrides: dict[str, str] | None = None,
) -> VerificationStep:
    """Run one verification command in its own process group with file-backed output."""
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(
        prefix="eidolon-verify-command-",
        dir=_command_temp_parent(env_overrides),
    ) as temp_dir:
        temp_root = Path(temp_dir)
        stdout_path = temp_root / "stdout.log"
        stderr_path = temp_root / "stderr.log"
        creationflags = 0
        popen_kwargs: dict[str, Any] = {}
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=stdout_file,
                stderr=stderr_file,
                env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1", **(env_overrides or {})},
                creationflags=creationflags,
                **popen_kwargs,
            )
            try:
                return_code = process.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_worker_tree(process)
                return_code = process.returncode if process.returncode is not None else -1

        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        output = stdout + stderr
        tail = "\n".join(output.splitlines()[-80:])
        if timed_out:
            return VerificationStep(
                " ".join(command),
                "fail",
                f"Timed out after {timeout}s; isolated process group was terminated.",
                tail,
                round(time.perf_counter() - started, 3),
            )
        return VerificationStep(
            " ".join(command),
            "pass" if return_code == 0 else "fail",
            f"Exit code {return_code}.",
            tail,
            round(time.perf_counter() - started, 3),
        )


def _parse_json_report(stdout: str, *, allow_trailing_object: bool) -> tuple[dict[str, Any], str | None]:
    """Parse either a pure JSON report or the final JSON object after human logs."""
    candidates: list[str] = [stdout.strip()]
    if allow_trailing_object:
        candidates.extend(stdout[index:].strip() for index, char in reversed(list(enumerate(stdout))) if char == "{")
    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict):
                raise TypeError("JSON report must be an object")
            return parsed, None
        except (json.JSONDecodeError, TypeError) as exc:
            last_error = exc
    if last_error is None:
        return {}, "JSONDecodeError: empty output"
    return {}, f"{type(last_error).__name__}: {last_error}"


def _run_json_report(
    command: list[str],
    *,
    timeout: int,
    performance_budget_seconds: float | None = None,
    env_overrides: dict[str, str] | None = None,
    allow_trailing_object: bool = False,
) -> tuple[VerificationStep, dict[str, Any]]:
    """Run a JSON report and preserve valid payloads even on nonzero exit."""
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(
        prefix="eidolon-verify-json-",
        dir=_command_temp_parent(env_overrides),
    ) as temp_dir:
        temp_root = Path(temp_dir)
        stdout_path = temp_root / "stdout.log"
        stderr_path = temp_root / "stderr.log"
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        popen_kwargs: dict[str, Any] = {} if os.name == "nt" else {"start_new_session": True}
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1", **(env_overrides or {})},
                creationflags=creationflags,
                **popen_kwargs,
            )
            try:
                return_code = process.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_worker_tree(process)
                return_code = process.returncode if process.returncode is not None else -1
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")

    elapsed = round(time.perf_counter() - started, 3)
    report: dict[str, Any] = {}
    parse_error: str | None = None
    if not timed_out:
        report, parse_error = _parse_json_report(stdout, allow_trailing_object=allow_trailing_object)
    parse_ok = bool(report)
    functional_ok = report.get("ok") is True if parse_ok else False
    exit_ok = not timed_out and return_code == 0
    performance_ok = True if performance_budget_seconds is None else elapsed <= performance_budget_seconds
    ok = parse_ok and functional_ok and exit_ok and performance_ok
    details = {
        "report": report,
        "return_code": return_code,
        "timed_out": timed_out,
        "functional_status": "pass" if functional_ok else "blocked",
        "exit_status": "timeout" if timed_out else ("pass" if exit_ok else "blocked"),
        "parse_status": "pass" if parse_ok else "blocked",
        "performance_status": "pass" if performance_ok else "blocked",
        "performance_budget_seconds": performance_budget_seconds,
        "parse_error": parse_error,
        "stdout_tail": "\n".join(stdout.splitlines()[-20:]) if not parse_ok else None,
        "stderr_tail": "\n".join(stderr.splitlines()[-20:]),
    }
    summary = (
        f"functional={details['functional_status']} exit={details['exit_status']} "
        f"parse={details['parse_status']} performance={details['performance_status']}"
    )
    return VerificationStep(" ".join(command), "pass" if ok else "fail", summary, details, elapsed), report


def _terminate_worker_tree(process: subprocess.Popen[Any]) -> None:
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
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception:
            process.kill()
    try:
        process.wait(timeout=10)
    except Exception:
        pass


def _dashboard_probe(
    *,
    progress: bool = False,
    env_overrides: dict[str, str] | None = None,
) -> VerificationStep:
    """Probe all primary dashboard routes in one isolated suite worker.

    A single disposable subprocess preserves verifier isolation while avoiding the
    repeated process-spawn/cleanup contention observed only inside the complete
    release run. Each route still has its own HTTP timeout inside the worker.
    """
    started = time.perf_counter()
    if progress:
        for path, route_timeout in DASHBOARD_ROUTE_TIMEOUTS.items():
            print(f"[RUNNING] dashboard route {path} (budget {route_timeout}s)", flush=True)
    command = [
        str(Path(sys.executable).resolve()),
        str(DASHBOARD_PROBE_WORKER),
        "--suite-json",
        json.dumps(DASHBOARD_ROUTE_TIMEOUTS, sort_keys=True),
    ]
    with tempfile.TemporaryDirectory(
        prefix="eidolon-dashboard-suite-runtime-",
        dir=_command_temp_parent(env_overrides),
    ) as route_runtime_dir:
        worker_env, _seeded = _runtime_environment(Path(route_runtime_dir))
        worker_env["PYTHONDONTWRITEBYTECODE"] = "0"
        step, payload = _run_json_report(
            command,
            timeout=180,
            performance_budget_seconds=120,
            env_overrides=worker_env,
        )
    routes = dict(payload.get("routes") or {}) if isinstance(payload, dict) else {}
    if progress:
        for path in DASHBOARD_ROUTE_TIMEOUTS:
            row = routes.get(path) or {}
            print(
                f"[{'PASS' if row.get('ok') else 'FAIL'}] dashboard route {path}: "
                f"{row.get('elapsed_seconds', row.get('error', 'missing result'))}",
                flush=True,
            )
    ok = step.status == "pass" and len(routes) == len(DASHBOARD_ROUTE_TIMEOUTS) and all(
        (routes.get(path) or {}).get("ok") is True for path in DASHBOARD_ROUTE_TIMEOUTS
    )
    for path, row in routes.items():
        if isinstance(row, dict):
            row.setdefault("command_identity", [*command[:-1], "<route-timeout-map>"] )
    return VerificationStep(
        "dashboard-http-probe",
        "pass" if ok else "fail",
        f"Probed {len(routes)} primary dashboard routes in one isolated suite worker.",
        {
            "routes": routes,
            "stage_invocation_count": 1,
            "subprocess_execution_count": 1,
            "worker_summary": step.summary,
        },
        round(time.perf_counter() - started, 3),
    )


def build_verification(
    profile: str,
    *,
    skip_smoke: bool = False,
    progress: bool = False,
) -> dict[str, Any]:
    verification_started = time.perf_counter()
    steps: list[VerificationStep] = []
    stage_reports: dict[str, dict[str, Any]] = {}
    source_snapshot_before = _source_tree_snapshot()
    invocation_nonce = new_invocation_nonce()
    attestation_key = new_attestation_key()
    producer = f"release_verify:{profile}"
    python = str(Path(sys.executable).resolve())
    expected_commands = expected_stage_commands(ROOT, purpose="release", python_executable=python)
    try:
        release_source_digest = source_snapshot_digest(ROOT)
    except OSError:
        release_source_digest = "[snapshot-error]"
    stage_receipts: dict[str, dict[str, Any]] = {}
    supplemental_stage_receipts: dict[str, dict[str, Any]] = {}
    evidence_validation: dict[str, Any] = {
        "valid": False,
        "reason": "verification evidence was not built",
        "stage_execution_counts": {},
        "stage_subprocess_execution_counts": {},
        "expensive_stage_single_execution": False,
    }
    integrity: dict[str, Any] = {}
    external_runtime_delta: dict[str, Any] = {
        "source_write_count": -1,
        "source_delete_count": -1,
        "write_dimensions": {},
    }
    runtime_root_text = ""
    runtime_env: dict[str, str] = {}
    runtime_seeded_files: list[str] = []

    def record(step: VerificationStep, name: str) -> None:
        step.name = name
        steps.append(step)
        if progress:
            print(f"[{step.status.upper()}] {name}: {step.summary}", flush=True)

    def execute(name: str, action: Callable[[], VerificationStep]) -> VerificationStep:
        if progress:
            print(f"[RUNNING] {name}", flush=True)
        step = action()
        record(step, name)
        return step

    quick_parallel_results: dict[str, dict[str, Any]] = {}
    quick_dashboard_precomputed: dict[str, Any] | None = None

    def execute_json(
        name: str,
        command: list[str],
        *,
        timeout: int,
        performance_budget_seconds: float | None = None,
        env_overrides: dict[str, str] | None = None,
        allow_trailing_object: bool = False,
        profiles: tuple[str, ...] = ("quick", "full"),
    ) -> dict[str, Any]:
        if profile not in profiles or not stage_selected_for_profile(profile, name):
            return {}
        stage_runtime_root: Path | None = None
        stage_env = env_overrides if env_overrides is not None else runtime_env
        if name.endswith("-fixtures") and env_overrides and env_overrides.get("EIDOLON_VERIFICATION_RUNTIME_ROOT"):
            parent_tmp = Path(env_overrides["EIDOLON_VERIFICATION_RUNTIME_ROOT"]) / "tmp"
            parent_tmp.mkdir(parents=True, exist_ok=True)
            stage_runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-fixture-runtime-", dir=parent_tmp))
            isolated_env = _fixture_environment(stage_runtime_root)
            stage_env = {**env_overrides, **isolated_env}
        precomputed = quick_parallel_results.pop(name, None)
        if precomputed is not None:
            started_at = str(precomputed["started_at"])
            step = precomputed["step"]
            report = precomputed["report"]
            finished_at = str(precomputed["finished_at"])
            source_after = str(precomputed["source_after"])
        else:
            if progress:
                print(f"[RUNNING] {name}", flush=True)
            started_at = isoformat_utc()
            step, report = _run_json_report(
                command,
                timeout=timeout,
                performance_budget_seconds=performance_budget_seconds,
                env_overrides=stage_env,
                allow_trailing_object=allow_trailing_object,
            )
            finished_at = isoformat_utc()
            source_after = ""
        record(step, name)
        stage_reports[name] = report
        receipt_requested = name in expected_commands or name in SUPPLEMENTAL_RECEIPT_STAGE_NAMES
        if receipt_requested and not source_after:
            try:
                source_after = source_snapshot_digest(ROOT)
            except OSError:
                source_after = "[snapshot-error]"
        details = step.details if isinstance(step.details, dict) else {}
        if name in expected_commands:
            stage_receipts[name] = build_stage_receipt(
                name,
                producer=producer,
                invocation_nonce=invocation_nonce,
                source_snapshot_before=release_source_digest,
                source_snapshot_after=source_after,
                commands=[command],
                report=report,
                started_at=started_at,
                finished_at=finished_at,
                elapsed_seconds=step.elapsed_seconds,
                return_code=details.get("return_code"),
                timed_out=bool(details.get("timed_out")),
                subprocess_execution_count=1,
                attestation_key=attestation_key,
            )
        elif name in SUPPLEMENTAL_RECEIPT_STAGE_NAMES:
            supplemental_stage_receipts[name] = {
                "schema": "eidolon.verification.supplemental-stage-receipt.v1",
                "name": name,
                "command": list(command),
                "command_sha256": hashlib.sha256(json.dumps(command, sort_keys=True).encode("utf-8")).hexdigest(),
                "report_sha256": hashlib.sha256(json.dumps(report, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
                "started_at": started_at,
                "finished_at": finished_at,
                "elapsed_seconds": step.elapsed_seconds,
                "return_code": details.get("return_code"),
                "timed_out": bool(details.get("timed_out")),
                "performance_budget_seconds": performance_budget_seconds,
                "runtime_environment_isolated": bool(stage_env and stage_env.get("EIDOLON_DATA_DIR")),
                "source_snapshot_before_sha256": release_source_digest,
                "source_snapshot_after_sha256": source_after,
                "source_snapshot_unchanged": source_after == release_source_digest,
                "release_authorized": False,
                "operator_review_required": True,
            }
        if stage_runtime_root is not None:
            shutil.rmtree(stage_runtime_root, ignore_errors=True)
        return report

    with tempfile.TemporaryDirectory(prefix="eidolon-verification-runtime-") as runtime_dir:
        runtime_root = Path(runtime_dir).resolve()
        runtime_root_text = str(runtime_root)
        runtime_env, runtime_seeded_files = _runtime_environment(runtime_root)
        runtime_snapshot_before = _source_tree_snapshot(runtime_root)
        evidence_dir = runtime_root / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = evidence_dir / "verification-evidence.json"

        # Precompute the authoritative read-only core before any dashboard/server
        # lifecycle begins. On large checkpoints this host can otherwise make the
        # next cold Python subprocess stall after dashboard probing even though the
        # exact command succeeds in isolation. Commands, reports, timing and source
        # digests are cached and consumed at their normal declared stage positions,
        # preserving certification semantics and receipts. Parallel-core mode stays
        # available as an explicit quick-profile diagnostic only.
        if not (profile == "quick" and os.environ.get("EIDOLON_VERIFY_PARALLEL_CORE") == "1"):
            _early_core_specs = {
                "import-compatibility": {
                    "command": [python, "tools/import_compatibility_quick.py"],
                    "timeout": 480,
                    "performance_budget_seconds": None,
                    "env_overrides": {**runtime_env, "EIDOLON_IMPORT_WORKERS": "1"},
                },
                "python-compile": {
                    "command": [python, "tools/verification_source_compile.py"],
                    "timeout": 120,
                    "performance_budget_seconds": 60,
                    "env_overrides": runtime_env,
                },
                "version-inventory": {
                    "command": [python, "-m", "conscious_agent.version_metadata_inventory", "--root", str(ROOT), "--json"],
                    "timeout": 90,
                    "performance_budget_seconds": 30,
                    "env_overrides": runtime_env,
                },
                "corrective-suite": {
                    "command": [python, "tools/pre_v1078_9_corrective_tests.py", "--json"],
                    "timeout": 300,
                    "performance_budget_seconds": 180,
                    "env_overrides": runtime_env,
                },
            }
            for _stage_name, _spec in _early_core_specs.items():
                if not stage_selected_for_profile(profile, _stage_name):
                    continue
                if progress:
                    print(f"[RUNNING] {_stage_name} (early isolated precompute)", flush=True)
                _stage_started = isoformat_utc()
                _stage_step, _stage_report = _run_json_report(
                    list(_spec["command"]),
                    timeout=int(_spec["timeout"]),
                    performance_budget_seconds=_spec.get("performance_budget_seconds"),
                    env_overrides=_spec.get("env_overrides"),
                )
                _stage_finished = isoformat_utc()
                try:
                    _stage_source_after = source_snapshot_digest(ROOT)
                except OSError:
                    _stage_source_after = "[snapshot-error]"
                quick_parallel_results[_stage_name] = {
                    "started_at": _stage_started,
                    "step": _stage_step,
                    "report": _stage_report,
                    "finished_at": _stage_finished,
                    "source_after": _stage_source_after,
                }

        # Run the quick dashboard probe only after the authoritative read-only
        # core is complete. It remains independently runtime-isolated.
        if profile == "quick":
            if progress:
                print("[RUNNING] dashboard-http-probe (early isolated precompute)", flush=True)
            _dashboard_started = isoformat_utc()
            _dashboard_step = _dashboard_probe(progress=progress, env_overrides=runtime_env)
            _dashboard_finished = isoformat_utc()
            try:
                _dashboard_source_after = source_snapshot_digest(ROOT)
            except OSError:
                _dashboard_source_after = "[snapshot-error]"
            quick_dashboard_precomputed = {
                "started_at": _dashboard_started,
                "step": _dashboard_step,
                "finished_at": _dashboard_finished,
                "source_after": _dashboard_source_after,
            }

        # These authoritative read-only gates are logically independent, but
        # concurrent cold Python import/compile workloads have caused later
        # production-parity subprocesses to stall nondeterministically on large
        # checkpoints. Keep the release gate sequential by default; parallel core
        # execution remains an explicit diagnostic opt-in, never the certification
        # path.
        if profile == "quick" and os.environ.get("EIDOLON_VERIFY_PARALLEL_CORE") == "1":
            quick_parallel_specs: dict[str, dict[str, Any]] = {
                "python-compile": {
                    "command": [python, "tools/verification_compile.py", "--json"],
                    "timeout": 300,
                    "performance_budget_seconds": None,
                    "env_overrides": {"EIDOLON_COMPILE_WORKERS": "1"},
                },
                "version-inventory": {
                    "command": [python, "-m", "conscious_agent.version_metadata_inventory", "--root", str(ROOT), "--json"],
                    "timeout": 90,
                    "performance_budget_seconds": 30,
                },
                "corrective-suite": {
                    "command": [python, "tools/pre_v1078_9_corrective_tests.py", "--json"],
                    "timeout": 300,
                    "performance_budget_seconds": 180,
                },
                "import-compatibility": {
                    "command": [python, "tools/import_compatibility_quick.py"],
                    "timeout": 480,
                    "performance_budget_seconds": None,
                    "env_overrides": {"EIDOLON_IMPORT_WORKERS": "2"},
                },
            }
            if set(quick_parallel_specs) != set(QUICK_PARALLEL_CORE_STAGE_NAMES):
                raise RuntimeError("quick parallel core inventory drifted from declared policy")

            def run_quick_parallel_stage(stage_name: str, spec: dict[str, Any]) -> tuple[str, dict[str, Any]]:
                started_at = isoformat_utc()
                step, report = _run_json_report(
                    list(spec["command"]),
                    timeout=int(spec["timeout"]),
                    performance_budget_seconds=spec.get("performance_budget_seconds"),
                    env_overrides={**runtime_env, **dict(spec.get("env_overrides") or {})},
                )
                finished_at = isoformat_utc()
                return stage_name, {
                    "started_at": started_at,
                    "step": step,
                    "report": report,
                    "finished_at": finished_at,
                }

            if progress:
                print("[RUNNING] quick parallel core: python-compile, version-inventory, corrective-suite, import-compatibility", flush=True)
            with ThreadPoolExecutor(max_workers=len(quick_parallel_specs)) as executor:
                futures = {
                    executor.submit(run_quick_parallel_stage, stage_name, spec): stage_name
                    for stage_name, spec in quick_parallel_specs.items()
                }
                for future in as_completed(futures):
                    stage_name, payload = future.result()
                    try:
                        payload["source_after"] = source_snapshot_digest(ROOT)
                    except OSError:
                        payload["source_after"] = "[snapshot-error]"
                    quick_parallel_results[stage_name] = payload
                    if progress:
                        step = payload["step"]
                        print(f"[READY] {stage_name}: {step.summary}", flush=True)

        execute_json(
            "import-compatibility",
            [python, "tools/import_compatibility_quick.py"],
            timeout=480,
            env_overrides={**runtime_env, "EIDOLON_IMPORT_WORKERS": "1"},
        )
        execute_json(
            "python-compile",
            [python, "tools/verification_source_compile.py"],
            timeout=120,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
        )
        execute_json(
            "version-inventory",
            [python, "-m", "conscious_agent.version_metadata_inventory", "--root", str(ROOT), "--json"],
            timeout=90,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
        )
        execute_json(
            "corrective-suite",
            [python, "tools/pre_v1078_9_corrective_tests.py", "--json"],
            timeout=300,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
        )
        execute_json(
            "release-candidate-packaging-coherence-fixtures",
            [
                python, "tools/post_review_development_verify.py",
                "--profile", "core",
                "--suite", "v1100.0-product-reality-benchmark",
                "--suite", "v1099.9-consumer-use-lifecycle-consolidation",
                "--suite", "v1099.8-downstream-consumer-result-validation",
                "--suite", "v1099.7-exact-consumer-use-handoff-plan",
                "--suite", "v1099.6-consumer-daily-use-binding-consolidation",
                "--suite", "v1099.5-exact-successor-consumer-revalidation",
                "--suite", "v1099.4-consumer-daily-use-binding-recovery-expiry",
                "--suite", "v1099.3-release-authority-consumer-daily-use-consolidation",
                "--suite", "v1099.2-exact-consumer-use-preflight-binding",
                "--suite", "v1099.1-exact-consumer-selection-pinning",
                "--suite", "v1098.9-release-authority-handoff-lifecycle-consolidation",
                "--suite", "v1098.8-handoff-consumer-supersession-binding",
                "--suite", "v1098.7-consumer-receipt-recovery-retirement",
                "--suite", "v1098.6-release-authority-handoff-consolidation-checkpoint",
                "--suite", "v1098.5-release-authority-consumer-validation-receipt-binding",
                "--suite", "v1098.4-handoff-acknowledgment-recovery-expiry-hardening",
                "--suite", "v1098.3-release-authority-daily-use-coherence-checkpoint",
                "--suite", "v1098.2-release-authority-handoff-plan-binding",
                "--suite", "v1098.1-release-authority-readiness-refresh-recovery-hardening",
                "--suite", "v1098.0-certification-to-release-authority-boundary",
                "--suite", "v1097.9-certification-authority-consolidation-checkpoint",
                "--suite", "v1097.8-certification-policy-evolution-migration-preview",
                "--suite", "v1097.7-certification-authority-history-reconciliation",
                "--suite", "v1097.6-certification-daily-use-release-authority-coherence",
                "--suite", "v1097.5-evidence-freshness-replacement-recertification-preview",
                "--suite", "v1097.4-certification-decision-interruption-recovery",
                "--suite", "v1097.3-certification-decision-release-authority-coherence",
                "--suite", "v1097.2-certification-plan-binding-exact-authorization",
                "--suite", "v1097.1-certification-evidence-intake-readiness-preview",
                "--suite", "v1097.0-transactional-promotion-apply-release-coherence",
                "--suite", "v1096.9-promotion-plan-binding-exact-authorization",
                "--suite", "v1096.8-promotion-impact-preview-foundation",
                "--suite", "v1096.7-installed-state-reconciliation-daily-use-coherence",
                "--suite", "v1096.6-interrupted-installation-recovery-rollback",
                "--suite", "v1096.5-exact-transactional-installation-apply-foundation",
                "--suite", "v1096.4-installation-authorization-external-staging-foundation",
                "--suite", "v1096.3-installation-plan-binding-drift-protection",
                "--suite", "v1096.2-operator-controlled-installation-preview-foundation",
                "--suite", "v1096.1-handoff-recovery-replacement-hardening",
                "--suite", "v1096.0-operator-controlled-release-handoff-foundation",
                "--suite", "v1095.9-release-packaging-coherence-checkpoint",
                "--suite", "v1095.8-candidate-handoff-daily-use-coherence",
                "--suite", "v1095.7-archive-manifest-coherence",
                "--suite", "v1095.6-exact-candidate-identity-contract",
                "--json",
            ],
            timeout=900,
            performance_budget_seconds=600,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "local-model-readiness-fixtures",
            [python, "tools/local_model_readiness_tests.py", "--json"],
            timeout=120,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "local-model-configuration-fixtures",
            [python, "tools/local_model_configuration_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "local-model-certification-fixtures",
            [python, "tools/local_model_certification_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-runtime-fixtures",
            [python, "tools/conversation_runtime_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "v1174.9-reviewed-repair-fixtures",
            [python, "tools/v1174_9_review_repair_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1175.0-v1175.2-natural-language-action-routing-foundations",
            [python, "tools/v1175_0_2_natural_language_action_routing_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1175.3-v1175.5-action-proposal-handoff-foundations",
            [python, "tools/v1175_3_5_action_proposal_handoff_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1175.6-v1175.8-supervised-action-execution-results-reliability",
            [python, "tools/v1175_6_8_supervised_action_execution_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1175.9-natural-language-action-execution-checkpoint",
            [python, "tools/v1175_9_natural_language_action_execution_checkpoint_tests.py"],
            timeout=180,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1176.0-v1176.2-bounded-action-argument-clarification-foundations",
            [python, "tools/v1176_0_2_bounded_action_argument_clarification_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1176.3-v1176.5-structured-clarification-proposal-binding-integration",
            [python, "tools/v1176_3_5_structured_clarification_proposal_binding_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1176.6-v1176.8-clarification-reliability-conversation-continuity",
            [python, "tools/v1176_6_8_clarification_reliability_continuity_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1176.9-clarification-argument-routing-read-only-checkpoint",
            [python, "tools/v1176_9_clarification_argument_routing_checkpoint_tests.py"],
            timeout=180,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1177.0-v1177.2-persisted-action-proposal-explicit-approval-request-foundations",
            [python, "tools/v1177_0_2_persisted_action_proposal_approval_request_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1177.3-v1177.5-approval-decision-proposal-lifecycle-integration",
            [python, "tools/v1177_3_5_approval_decision_proposal_lifecycle_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1177.6-v1177.8-approval-to-execution-admission-integration",
            [python, "tools/v1177_6_8_approval_to_execution_admission_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1177.9-natural-language-action-approval-governance-read-only-checkpoint",
            [python, "tools/v1177_9_natural_language_action_approval_governance_checkpoint_tests.py"],
            timeout=240,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )

        execute_json(
            "v1178.0-v1178.2-authoritative-supervised-execution-results",
            [python, "tools/v1178_0_2_authoritative_supervised_execution_results_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1178.3-v1178.5-supervised-result-presentation-conversation",
            [python, "tools/v1178_3_5_supervised_result_presentation_conversation_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1178.6-v1178.8-supervised-result-reliability-recovery",
            [python, "tools/v1178_6_8_supervised_result_reliability_recovery_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1178.9-natural-language-action-authoritative-result-read-only-checkpoint",
            [python, "tools/v1178_9_natural_language_action_authoritative_result_checkpoint_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1179.0-v1179.2-action-review-follow-through-foundations",
            [python, "tools/v1179_0_2_action_review_follow_through_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1179.3-v1179.5-governed-action-follow-up-continuity",
            [python, "tools/v1179_3_5_governed_action_follow_up_continuity_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1179.6-v1179.8-complete-action-loop-reliability",
            [python, "tools/v1179_6_8_complete_action_loop_reliability_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1179.9-natural-language-action-read-only-checkpoint",
            [python, "tools/v1179_9_natural_language_action_checkpoint_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1180.0-v1180.2-supervised-project-inspection-foundations",
            [python, "tools/v1180_0_2_supervised_project_inspection_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1180.3-v1180.5-deficiency-review-specification-foundations",
            [python, "tools/v1180_3_5_deficiency_review_specification_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1180.6-v1180.8-supervised-implementation-test-planning-foundations",
            [python, "tools/v1180_6_8_supervised_implementation_test_planning_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1180.9-supervised-project-inspection-planning-read-only-checkpoint",
            [python, "tools/v1180_9_supervised_project_inspection_planning_checkpoint_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1181.0-v1181.2-bounded-implementation-preparation-foundations",
            [python, "tools/v1181_0_2_bounded_implementation_preparation_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1181.3-v1181.5-supervised-patch-draft-foundations",
            [python, "tools/v1181_3_5_supervised_patch_draft_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1181.6-v1181.8-supervised-patch-review-sandbox-materialization",
            [python, "tools/v1181_6_8_supervised_patch_review_sandbox_materialization_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1181.9-supervised-implementation-read-only-checkpoint",
            [python, "tools/v1181_9_supervised_implementation_checkpoint_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1182.0-v1182.2-supervised-sandbox-test-execution-foundations",
            [python, "tools/v1182_0_2_supervised_sandbox_test_execution_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1182.3-v1182.5-sandbox-test-evidence-diagnosis-foundations",
            [python, "tools/v1182_3_5_sandbox_test_evidence_diagnosis_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1182.6-v1182.8-supervised-repair-planning-foundations",
            [python, "tools/v1182_6_8_supervised_repair_planning_foundations_tests.py"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1182.9-supervised-sandbox-testing-repair-read-only-checkpoint",
            [python, "tools/v1182_9_supervised_sandbox_testing_repair_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1183.0-v1183.2-supervised-sandbox-repair-draft-foundations",
            [python, "tools/v1183_0_2_supervised_sandbox_repair_draft_foundations_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1183.3-v1183.5-supervised-sandbox-repair-review-materialization",
            [python, "tools/v1183_3_5_supervised_sandbox_repair_review_materialization_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1183.6-v1183.8-governed-sandbox-retesting",
            [python, "tools/v1183_6_8_supervised_sandbox_retesting_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1183.9-supervised-sandbox-repair-retest-read-only-checkpoint",
            [python, "tools/v1183_9_supervised_sandbox_repair_retest_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1184.0-v1184.2-supervised-project-development-foundations",
            [python, "tools/v1184_2_supervised_project_development_foundations_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1184.3-v1184.5-supervised-project-outcome-learning",
            [python, "tools/v1184_3_5_supervised_project_outcome_learning_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1184.6-v1184.8-supervised-project-reliability-recovery",
            [python, "tools/v1184_6_8_supervised_project_reliability_recovery_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1184.9-supervised-project-development-alpha-read-only-checkpoint",
            [python, "tools/v1184_9_supervised_project_development_alpha_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1185.0-v1185.2-persistent-development-campaign-foundations",
            [python, "tools/v1185_0_2_persistent_development_campaign_foundations_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1185.3-v1185.5-persistent-development-campaign-continuation",
            [python, "tools/v1185_3_5_persistent_development_campaign_continuation_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1185.6-v1185.8-persistent-development-campaign-reliability",
            [python, "tools/v1185_6_8_persistent_development_campaign_reliability_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1185.9-persistent-supervised-developer-alpha-read-only-checkpoint",
            [python, "tools/v1185_9_persistent_supervised_developer_alpha_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1186.0-v1186.2-durable-campaign-storage-restoration-foundations",
            [python, "tools/v1186_0_2_persistent_campaign_storage_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1186.3-v1186.5-durable-campaign-resume-review-reconciliation",
            [python, "tools/v1186_3_5_persistent_campaign_resume_reconciliation_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1186.6-v1186.8-durable-resume-materialization-session-handoff",
            [python, "tools/v1186_6_8_persistent_campaign_resume_materialization_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1186.9-durable-campaign-continuation-read-only-checkpoint",
            [python, "tools/v1186_9_durable_campaign_continuation_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1187.0-v1187.2-bounded-campaign-work-execution-foundations",
            [python, "tools/v1187_0_2_bounded_campaign_work_execution_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1187.3-v1187.5-governed-campaign-work-result-ledger-integration",
            [python, "tools/v1187_3_5_campaign_work_result_ledger_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1187.6-v1187.8-governed-campaign-work-continuation-failure-handling",
            [python, "tools/v1187_6_8_governed_campaign_work_continuation_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1187.9-persistent-campaign-work-execution-read-only-checkpoint",
            [python, "tools/v1187_9_persistent_campaign_work_execution_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1188.2-complete-campaign-development-loop-foundations",
            [python, "tools/v1188_0_2_complete_campaign_development_loop_foundations_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1188.5-campaign-loop-execution-result-integration",
            [python, "tools/v1188_3_5_campaign_loop_execution_result_integration_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1188.8-campaign-loop-reliability-recovery-learning",
            [python, "tools/v1188_6_8_campaign_loop_reliability_recovery_learning_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1189.2-persistent-supervised-developer-hardening-foundations",
            [python, "tools/v1189_0_2_persistent_supervised_developer_hardening_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1189.5-adversarial-campaign-hardening-long-session",
            [python, "tools/v1189_3_5_adversarial_campaign_hardening_long_session_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1189.8-persistent-developer-adversarial-reliability",
            [python, "tools/v1189_6_8_persistent_developer_adversarial_reliability_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1191.2-responsive-work-queue-foundations",
            [python, "tools/v1191_0_2_responsive_work_queue_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1191.5-responsive-work-queue-review",
            [python, "tools/v1191_3_5_responsive_work_queue_review_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1191.8-responsive-work-queue-reliability",
            [python, "tools/v1191_6_8_responsive_work_queue_reliability_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1192.2-bounded-evidence-compaction-foundations",
            [python, "tools/v1192_0_2_bounded_evidence_compaction_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1192.5-operator-evidence-compaction-review",
            [python, "tools/v1192_3_5_evidence_compaction_review_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1192.8-evidence-compaction-reliability",
            [python, "tools/v1192_6_8_evidence_compaction_reliability_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1192.9-bounded-evidence-compaction-checkpoint",
            [python, "tools/v1192_9_evidence_compaction_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1193.2-verifier-ownership-foundations",
            [python, "tools/v1193_0_2_verifier_ownership_tests.py"],
            timeout=300,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1193.5-profile-budget-reconciliation",
            [python, "tools/v1193_3_5_profile_budget_reconciliation_tests.py"],
            timeout=300,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1193.8-fixture-historical-debt-consolidation",
            [python, "tools/v1193_6_8_fixture_historical_debt_consolidation_tests.py"],
            timeout=300,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1194.2-unified-cognitive-developer-experience",
            [python, "tools/v1194_0_2_unified_cognitive_developer_experience_tests.py"],
            timeout=300,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1194.5-operator-coordination-navigation",
            [python, "tools/v1194_3_5_operator_coordination_navigation_tests.py"],
            timeout=300,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1194.8-unified-reliability-integration",
            [python, "tools/v1194_6_8_unified_experience_reliability_integration_tests.py"],
            timeout=300,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1194.9-unified-cognitive-developer-checkpoint",
            [python, "tools/v1194_9_unified_cognitive_developer_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1195.2-long-session-multi-day-soak",
            [python, "tools/v1195_0_2_long_session_multi_day_soak_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1195.5-operator-reviewed-soak-progression",
            [python, "tools/v1195_3_5_operator_reviewed_soak_progression_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1195.8-soak-reliability-adversarial",
            [python, "tools/v1195_6_8_soak_reliability_adversarial_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1196.2-adversarial-privacy-authority",
            [python, "tools/v1196_0_2_adversarial_privacy_authority_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1196.5-adversarial-replay-recovery-review",
            [python, "tools/v1196_3_5_adversarial_replay_recovery_review_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1196.8-adversarial-reliability-integration",
            [python, "tools/v1196_6_8_adversarial_reliability_integration_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        # Next bounded unit: v1197.0-v1197.2 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Foundations
        execute_json(
            "v1196.9-adversarial-privacy-authority-replay-recovery-checkpoint",
            [python, "tools/v1196_9_adversarial_privacy_authority_replay_recovery_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1197.2-runtime-lifecycle-migration",
            [python, "tools/v1197_0_2_runtime_lifecycle_migration_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1197.5-runtime-lifecycle-application-review",
            [python, "tools/v1197_3_5_runtime_lifecycle_application_review_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1197.8-runtime-lifecycle-reliability-adversarial",
            [python, "tools/v1197_6_8_runtime_lifecycle_reliability_adversarial_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1197.9-runtime-lifecycle-checkpoint",
            [python, "tools/v1197_9_runtime_lifecycle_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1198.2-feature-freeze-architecture-consolidation",
            [python, "tools/v1198_0_2_feature_freeze_architecture_consolidation_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1198.5-feature-freeze-consolidation-review",
            [python, "tools/v1198_3_5_feature_freeze_consolidation_review_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1198.8-performance-documentation-verifier-hardening",
            [python, "tools/v1198_6_8_performance_documentation_verifier_hardening_tests.py"],
            timeout=600,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1198.9-feature-freeze-architecture-consolidation-checkpoint",
            [python, "tools/v1198_9_feature_freeze_architecture_consolidation_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1199.2-final-source-candidate-preparation-foundations",
            [python, "tools/v1199_0_2_final_source_candidate_preparation_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1199.5-operator-final-candidate-review",
            [python, "tools/v1199_3_5_final_candidate_review_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1199.8-final-candidate-reliability",
            [python, "tools/v1199_6_8_final_candidate_reliability_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1199.9-final-source-candidate-checkpoint",
            [python, "tools/v1199_9_final_source_candidate_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1200.0-cognitive-beta-autonomous-developer-alpha",
            [python, "tools/v1200_0_cognitive_beta_autonomous_developer_alpha_tests.py"],
            timeout=180,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1200.3-ordinary-chat-development-campaign",
            [python, "tools/v1200_1_3_ordinary_chat_development_campaign_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1200.6-grounded-project-planning",
            [python, "tools/v1200_4_6_grounded_project_planning_tests.py"],
            timeout=180,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1200.9-structured-provider-generation",
            [python, "tools/v1200_7_9_structured_generation_tests.py"],
            timeout=180,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1201.2-isolated-workspace-materialization",
            [python, "tools/v1201_0_2_isolated_workspace_materialization_tests.py"],
            timeout=180,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1201.5-isolated-workspace-browser-preview",
            [python, "tools/v1201_3_5_isolated_workspace_preview_tests.py"],
            timeout=180,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1201.8-bounded-browser-javascript-validation",
            [python, "tools/v1201_6_8_bounded_browser_javascript_validation_tests.py"],
            timeout=180,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1201.9-small-website-implementation-checkpoint",
            [python, "tools/v1201_9_small_website_implementation_checkpoint_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1202.2-javascript-tool-implementation-foundations",
            [python, "tools/v1202_0_2_javascript_tool_implementation_foundations_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1202.5-project-owned-javascript-tests",
            [python, "tools/v1202_3_5_project_owned_javascript_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1202.8-javascript-tool-result-disposition",
            [python, "tools/v1202_6_8_javascript_tool_result_disposition_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1202.9-javascript-tool-implementation-checkpoint",
            [python, "tools/v1202_9_javascript_tool_implementation_checkpoint_tests.py"],
            timeout=300,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1203.2-python-cli-implementation-foundations",
            [python, "tools/v1203_0_2_python_cli_implementation_foundations_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1203.5-project-owned-python-tests",
            [python, "tools/v1203_3_5_project_owned_python_tests.py"],
            timeout=240,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1203.8-python-cli-result-disposition",
            [python, "tools/v1203_6_8_python_cli_result_disposition_tests.py"],
            timeout=240,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1203.9-python-cli-implementation-checkpoint",
            [python, "tools/v1203_9_python_cli_implementation_checkpoint_tests.py"],
            timeout=300,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1204.2-selected-project-apply-foundations",
            [python, "tools/v1204_0_2_selected_project_apply_foundations_tests.py"],
            timeout=300,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1204.5-selected-project-rollback-recovery",
            [python, "tools/v1204_3_5_selected_project_rollback_recovery_tests.py"],
            timeout=300,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1204.8-selected-project-apply-rollback-reliability",
            [python, "tools/v1204_6_8_selected_project_apply_rollback_reliability_tests.py"],
            timeout=300,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1204.9-selected-project-apply-rollback-checkpoint",
            [python, "tools/v1204_9_selected_project_apply_rollback_checkpoint_tests.py"],
            timeout=360,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1205.2-general-small-project-implementation-consolidation",
            [python, "tools/v1205_0_2_general_small_project_consolidation_tests.py"],
            timeout=360,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1205.5-selected-project-mixed-operations",
            [python, "tools/v1205_3_5_selected_project_mixed_operations_tests.py"],
            timeout=360,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1205.8-general-small-project-reliability-hardening",
            [python, "tools/v1205_6_8_general_small_project_reliability_hardening_tests.py"],
            timeout=360,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1205.9-general-small-project-implementation-checkpoint",
            [python, "tools/v1205_9_general_small_project_implementation_checkpoint_tests.py"],
            timeout=420,
            performance_budget_seconds=150,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1206.2-natural-conversation-command-distinction",
            [python, "tools/v1206_0_2_natural_conversation_command_distinction_tests.py"],
            timeout=420,
            performance_budget_seconds=150,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1206.5-browser-runtime-test-adapter",
            [python, "tools/v1206_3_5_browser_runtime_test_adapter_tests.py"],
            timeout=420,
            performance_budget_seconds=150,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1206.8-browser-runtime-reliability",
            [python, "tools/v1206_6_8_browser_runtime_reliability_tests.py"],
            timeout=420,
            performance_budget_seconds=150,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1206.9-browser-runtime-test-adapter-checkpoint",
            [python, "tools/v1206_9_browser_runtime_test_adapter_checkpoint_tests.py"],
            timeout=480,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1207.2-node-javascript-test-adapter-foundations",
            [python, "tools/v1207_0_2_node_javascript_test_adapter_foundations_tests.py"],
            timeout=300,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1207.5-node-javascript-project-test-execution",
            [python, "tools/v1207_3_5_node_javascript_test_execution_tests.py"],
            timeout=360,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1207.8-node-javascript-test-adapter-reliability",
            [python, "tools/v1207_6_8_node_javascript_test_adapter_reliability_tests.py"],
            timeout=360,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1207.9-node-javascript-test-adapter-checkpoint",
            [python, "tools/v1207_9_node_javascript_test_adapter_checkpoint_tests.py"],
            timeout=420,
            performance_budget_seconds=150,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1208.2-python-test-adapter-foundations",
            [python, "tools/v1208_0_2_python_test_adapter_foundations_tests.py"],
            timeout=360, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1208.5-python-project-test-execution",
            [python, "tools/v1208_3_5_python_project_test_execution_tests.py"],
            timeout=420, performance_budget_seconds=150, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1208.8-python-test-adapter-reliability",
            [python, "tools/v1208_6_8_python_test_adapter_reliability_tests.py"],
            timeout=420, performance_budget_seconds=150, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1208.9-python-test-adapter-checkpoint",
            [python, "tools/v1208_9_python_test_adapter_checkpoint_tests.py"],
            timeout=480, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.0-unified-test-adapter-contract",
            [python, "tools/v1209_0_unified_test_adapter_contract_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.1-test-adapter-registry",
            [python, "tools/v1209_1_test_adapter_registry_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.2-test-adapter-selection",
            [python, "tools/v1209_2_test_adapter_selection_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.3-test-adapter-execution-request",
            [python, "tools/v1209_3_test_adapter_execution_request_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.4-test-adapter-dispatch",
            [python, "tools/v1209_4_test_adapter_dispatch_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.5-test-adapter-lifecycle-reliability",
            [python, "tools/v1209_5_test_adapter_lifecycle_reliability_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.6-test-adapter-preflight-hardening",
            [python, "tools/v1209_6_test_adapter_preflight_hardening_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.7-test-adapter-evidence-reconciliation",
            [python, "tools/v1209_7_test_adapter_evidence_reconciliation_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.8-test-adapter-recovery-hardening",
            [python, "tools/v1209_8_test_adapter_recovery_hardening_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1209.9-general-test-adapter-consolidation-checkpoint",
            [python, "tools/v1209_9_general_test_adapter_consolidation_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1210.2-conversational-build-test-foundations",
            [python, "tools/v1210_0_2_conversational_build_test_foundations_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1210.5-conversational-build-test-execution",
            [python, "tools/v1210_3_5_conversational_build_test_execution_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1210.8-conversational-build-test-reliability",
            [python, "tools/v1210_6_8_conversational_build_test_reliability_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1210.9-conversational-build-test-loop-checkpoint",
            [python, "tools/v1210_9_conversational_build_test_loop_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1211.2-operator-build-test-results-foundations",
            [python, "tools/v1211_0_2_operator_build_test_results_foundations_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1211.5-operator-build-test-continuation",
            [python, "tools/v1211_3_5_operator_build_test_continuation_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1211.8-operator-build-test-results-reliability",
            [python, "tools/v1211_6_8_operator_build_test_results_reliability_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1211.9-operator-build-test-results-checkpoint",
            [python, "tools/v1211_9_operator_build_test_results_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1212.2-conversational-build-test-continuation-foundations",
            [python, "tools/v1212_0_2_conversational_build_test_continuation_foundations_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1212.5-conversational-build-test-continuation-execution",
            [python, "tools/v1212_3_5_conversational_build_test_continuation_execution_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1212.8-conversational-build-test-continuation-reliability",
            [python, "tools/v1212_6_8_conversational_build_test_continuation_reliability_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1212.9-conversational-build-test-continuation-checkpoint",
            [python, "tools/v1212_9_conversational_build_test_continuation_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1213.2-bounded-automatic-diagnosis-foundations",
            [python, "tools/v1213_0_2_bounded_automatic_diagnosis_foundations_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1213.5-bounded-automatic-diagnosis-execution",
            [python, "tools/v1213_3_5_bounded_automatic_diagnosis_execution_tests.py"],
            timeout=240, performance_budget_seconds=90, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1213.8-bounded-automatic-diagnosis-reliability",
            [python, "tools/v1213_6_8_bounded_automatic_diagnosis_reliability_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1213.9-bounded-automatic-diagnosis-checkpoint",
            [python, "tools/v1213_9_bounded_automatic_diagnosis_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1214.2-operator-diagnosis-review-foundations",
            [python, "tools/v1214_0_2_operator_diagnosis_review_foundations_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1214.5-operator-diagnosis-decision-repair-proposal",
            [python, "tools/v1214_3_5_operator_diagnosis_decision_repair_proposal_tests.py"],
            timeout=240, performance_budget_seconds=90, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1214.8-operator-diagnosis-review-repair-proposal-reliability",
            [python, "tools/v1214_6_8_operator_diagnosis_review_reliability_tests.py"],
            timeout=180, performance_budget_seconds=60, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1214.9-operator-diagnosis-review-checkpoint",
            [python, "tools/v1214_9_operator_diagnosis_review_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1215.2-supervised-repair-execution-foundations",
            [python, "tools/v1215_0_2_supervised_repair_execution_foundations_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1215.5-supervised-repair-execution-and-verification",
            [python, "tools/v1215_3_5_supervised_repair_execution_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1215.8-supervised-repair-execution-reliability",
            [python, "tools/v1215_6_8_supervised_repair_execution_reliability_tests.py"],
            timeout=360, performance_budget_seconds=150, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1215.9-conversational-supervised-repair-execution-checkpoint",
            [python, "tools/v1215_9_conversational_supervised_repair_execution_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1216.2-operator-repair-result-review-foundations",
            [python, "tools/v1216_0_2_operator_repair_result_review_foundations_tests.py"],
            timeout=360, performance_budget_seconds=150, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1216.5-operator-repair-result-decision-apply-proposal",
            [python, "tools/v1216_3_5_operator_repair_result_decision_apply_proposal_tests.py"],
            timeout=360, performance_budget_seconds=150, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1216.8-operator-repair-result-review-reliability",
            [python, "tools/v1216_6_8_operator_repair_result_review_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1216.9-operator-repair-result-review-checkpoint",
            [python, "tools/v1216_9_operator_repair_result_review_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1217.2-supervised-repaired-candidate-apply-foundations",
            [python, "tools/v1217_0_2_supervised_repaired_candidate_apply_foundations_tests.py"],
            timeout=360, performance_budget_seconds=150, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1217.5-supervised-repaired-candidate-apply-execution",
            [python, "tools/v1217_3_5_supervised_repaired_candidate_apply_execution_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1217.8-supervised-repaired-candidate-apply-reliability",
            [python, "tools/v1217_6_8_supervised_repaired_candidate_apply_reliability_tests.py"],
            timeout=480, performance_budget_seconds=210, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1217.9-supervised-repaired-candidate-apply-checkpoint",
            [python, "tools/v1217_9_supervised_repaired_candidate_apply_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1218.2-operator-repaired-candidate-apply-result-review-foundations",
            [python, "tools/v1218_0_2_operator_repaired_candidate_apply_result_review_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1218.5-operator-repaired-candidate-apply-result-decision-rollback-proposal",
            [python, "tools/v1218_3_5_operator_repaired_candidate_apply_result_decision_rollback_proposal_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1218.8-operator-repaired-candidate-apply-result-review-reliability",
            [python, "tools/v1218_6_8_operator_repaired_candidate_apply_result_review_reliability_tests.py"],
            timeout=480, performance_budget_seconds=210, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1218.9-operator-repaired-candidate-apply-result-review-checkpoint",
            [python, "tools/v1218_9_operator_repaired_candidate_apply_result_review_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1219.2-supervised-repaired-candidate-rollback-foundations",
            [python, "tools/v1219_0_2_supervised_repaired_candidate_rollback_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1219.5-supervised-repaired-candidate-rollback-execution",
            [python, "tools/v1219_3_5_supervised_repaired_candidate_rollback_execution_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1219.8-supervised-repaired-candidate-rollback-reliability",
            [python, "tools/v1219_6_8_supervised_repaired_candidate_rollback_reliability_tests.py"],
            timeout=480, performance_budget_seconds=210, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1219.9-supervised-repaired-candidate-rollback-checkpoint",
            [python, "tools/v1219_9_supervised_repaired_candidate_rollback_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1220.2-operator-repaired-candidate-rollback-result-review-foundations",
            [python, "tools/v1220_0_2_operator_repaired_candidate_rollback_result_review_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1220.5-operator-repaired-candidate-rollback-result-decisions",
            [python, "tools/v1220_3_5_operator_repaired_candidate_rollback_result_decision_tests.py"],
            timeout=540, performance_budget_seconds=240, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1220.8-operator-repaired-candidate-rollback-result-review-reliability",
            [python, "tools/v1220_6_8_operator_repaired_candidate_rollback_result_review_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1220.9-operator-repaired-candidate-rollback-result-review-checkpoint",
            [python, "tools/v1220_9_operator_repaired_candidate_rollback_result_review_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1221.2-unified-supervised-development-transaction-history-foundations",
            [python, "tools/v1221_0_2_unified_supervised_development_transaction_history_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1221.5-unified-supervised-development-transaction-history-conversation",
            [python, "tools/v1221_3_5_unified_supervised_development_transaction_history_conversation_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1221.8-unified-supervised-development-transaction-history-reliability",
            [python, "tools/v1221_6_8_unified_supervised_development_transaction_history_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1221.9-unified-supervised-development-transaction-history-checkpoint",
            [python, "tools/v1221_9_unified_supervised_development_transaction_history_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1222.2-transaction-resumption-abandoned-work-reconciliation-foundations",
            [python, "tools/v1222_0_2_transaction_resumption_abandoned_work_reconciliation_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1222.5-transaction-resumption-operator-review",
            [python, "tools/v1222_3_5_transaction_resumption_operator_review_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1222.8-transaction-resumption-reliability",
            [python, "tools/v1222_6_8_transaction_resumption_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1222.9-transaction-resumption-abandoned-work-reconciliation-checkpoint",
            [python, "tools/v1222_9_transaction_resumption_abandoned_work_reconciliation_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1223.2-unified-development-work-queue-foundations",
            [python, "tools/v1223_0_2_unified_development_work_queue_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1223.5-unified-development-work-queue-conversation-controls",
            [python, "tools/v1223_3_5_unified_development_work_queue_conversation_control_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1223.8-unified-development-work-queue-reliability",
            [python, "tools/v1223_6_8_unified_development_work_queue_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1223.9-unified-development-work-queue-checkpoint",
            [python, "tools/v1223_9_unified_development_work_queue_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1224.2-operator-governed-work-prioritization-foundations",
            [python, "tools/v1224_0_2_operator_governed_work_prioritization_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1224.5-operator-governed-work-prioritization-schedule-review",
            [python, "tools/v1224_3_5_operator_governed_work_prioritization_schedule_review_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1224.8-operator-governed-work-prioritization-scheduling-reliability",
            [python, "tools/v1224_6_8_operator_governed_work_prioritization_scheduling_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1224.9-operator-governed-work-prioritization-scheduling-checkpoint",
            [python, "tools/v1224_9_operator_governed_work_prioritization_scheduling_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1225.2-supervised-work-dispatch-session-preparation-foundations",
            [python, "tools/v1225_0_2_supervised_work_dispatch_session_preparation_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1225.5-supervised-work-dispatch-session-review",
            [python, "tools/v1225_3_5_supervised_work_dispatch_session_review_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1225.8-supervised-work-dispatch-session-preparation-reliability",
            [python, "tools/v1225_6_8_supervised_work_dispatch_session_preparation_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1225.9-supervised-work-dispatch-execution-session-preparation-checkpoint",
            [python, "tools/v1225_9_supervised_work_dispatch_execution_session_preparation_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1226.2-execution-session-authorization-foundations",
            [python, "tools/v1226_0_2_execution_session_authorization_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1226.5-execution-session-bounded-launch",
            [python, "tools/v1226_3_5_execution_session_bounded_launch_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1226.8-execution-session-bounded-launch-reliability",
            [python, "tools/v1226_6_8_execution_session_bounded_launch_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1226.9-execution-session-authorization-bounded-launch-checkpoint",
            [python, "tools/v1226_9_execution_session_authorization_bounded_launch_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1227.2-live-execution-monitoring-foundations",
            [python, "tools/v1227_0_2_live_execution_monitoring_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1227.5-live-execution-monitoring-operator-intervention",
            [python, "tools/v1227_3_5_live_execution_monitoring_operator_intervention_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1227.8-live-execution-monitoring-reliability",
            [python, "tools/v1227_6_8_live_execution_monitoring_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1227.9-live-execution-monitoring-operator-intervention-checkpoint",
            [python, "tools/v1227_9_live_execution_monitoring_operator_intervention_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1228.2-execution-pause-resume-cancel-recovery-foundations",
            [python, "tools/v1228_0_2_execution_pause_resume_cancel_recovery_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1228.5-execution-pause-resume-cancel-controls",
            [python, "tools/v1228_3_5_execution_pause_resume_cancel_controls_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1228.8-execution-control-recovery-reliability",
            [python, "tools/v1228_6_8_execution_control_recovery_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1228.9-execution-session-pause-resume-cancel-recovery-checkpoint",
            [python, "tools/v1228_9_execution_session_pause_resume_cancel_recovery_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1229.2-execution-outcome-reflection-foundations",
            [python, "tools/v1229_0_2_execution_outcome_reflection_foundations_tests.py"],
            timeout=180, performance_budget_seconds=90, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1229.5-execution-outcome-reflection-review",
            [python, "tools/v1229_3_5_execution_outcome_reflection_review_tests.py"],
            timeout=180, performance_budget_seconds=90, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1229.8-execution-outcome-learning-reliability",
            [python, "tools/v1229_6_8_execution_outcome_learning_reliability_tests.py"],
            timeout=180, performance_budget_seconds=90, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1229.9-execution-outcome-reflection-learning-integration-checkpoint",
            [python, "tools/v1229_9_execution_outcome_reflection_learning_integration_checkpoint_tests.py"],
            timeout=180, performance_budget_seconds=90, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1230.2-mindful-execution-alpha-integration-foundations",
            [python, "tools/v1230_0_2_mindful_execution_alpha_integration_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1230.5-mindful-execution-alpha-ordinary-path",
            [python, "tools/v1230_3_5_mindful_execution_alpha_ordinary_path_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1230.8-mindful-execution-alpha-adversarial-reliability",
            [python, "tools/v1230_6_8_mindful_execution_alpha_adversarial_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1230.9-mindful-execution-alpha-integration-benchmark-checkpoint",
            [python, "tools/v1230_9_mindful_execution_alpha_integration_benchmark_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1231.2-dynamic-execution-plan-revision-foundations",
            [python, "tools/v1231_0_2_dynamic_execution_plan_revision_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1231.5-dynamic-execution-plan-revision-operator-review",
            [python, "tools/v1231_3_5_dynamic_execution_plan_revision_operator_review_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1231.8-dynamic-execution-plan-revision-adversarial-reliability",
            [python, "tools/v1231_6_8_dynamic_execution_plan_revision_adversarial_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1231.9-dynamic-execution-plan-revision-checkpoint",
            [python, "tools/v1231_9_dynamic_execution_plan_revision_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1232.2-dependency-aware-execution-foundations",
            [python, "tools/v1232_0_2_dependency_aware_execution_foundations_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1232.5-dependency-aware-execution-operator-review",
            [python, "tools/v1232_3_5_dependency_aware_execution_operator_review_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1232.8-dependency-aware-execution-adversarial-reliability",
            [python, "tools/v1232_6_8_dependency_aware_execution_adversarial_reliability_tests.py"],
            timeout=420, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1232.9-dependency-aware-execution-checkpoint",
            [python, "tools/v1232_9_dependency_aware_execution_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1233.2-resource-concurrency-governance-foundations",
            [python, "tools/v1233_0_2_resource_concurrency_governance_foundations_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1233.5-resource-concurrency-governance-operator-review",
            [python, "tools/v1233_3_5_resource_concurrency_governance_operator_review_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1233.8-resource-concurrency-governance-adversarial-reliability",
            [python, "tools/v1233_6_8_resource_concurrency_governance_adversarial_reliability_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1233.9-resource-concurrency-governance-checkpoint",
            [python, "tools/v1233_9_resource_concurrency_governance_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1234.2-requirement-quality-assessment-foundations",
            [python, "tools/v1234_0_2_requirement_quality_assessment_foundations_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1234.5-requirement-quality-assessment-operator-review",
            [python, "tools/v1234_3_5_requirement_quality_assessment_operator_review_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1234.8-requirement-quality-assessment-adversarial-reliability",
            [python, "tools/v1234_6_8_requirement_quality_assessment_adversarial_reliability_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1234.9-requirement-quality-assessment-checkpoint",
            [python, "tools/v1234_9_requirement_quality_assessment_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1235.2-evidence-backed-development-outcome-lessons-foundations",
            [python, "tools/v1235_0_2_evidence_backed_development_outcome_lessons_foundations_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1235.5-evidence-backed-development-outcome-lessons-operator-review",
            [python, "tools/v1235_3_5_evidence_backed_development_outcome_lessons_operator_review_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1235.8-evidence-backed-development-outcome-lessons-adversarial-reliability",
            [python, "tools/v1235_6_8_evidence_backed_development_outcome_lessons_adversarial_reliability_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1235.9-evidence-backed-development-outcome-lessons-checkpoint",
            [python, "tools/v1235_9_evidence_backed_development_outcome_lessons_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1236.2-goal-motivation-work-priority-integration-foundations",
            [python, "tools/v1236_0_2_goal_motivation_work_priority_integration_foundations_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1236.5-goal-motivation-work-priority-integration-operator-review",
            [python, "tools/v1236_3_5_goal_motivation_work_priority_integration_operator_review_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1236.8-goal-motivation-work-priority-integration-adversarial-reliability",
            [python, "tools/v1236_6_8_goal_motivation_work_priority_integration_adversarial_reliability_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1236.9-goal-motivation-work-priority-integration-checkpoint",
            [python, "tools/v1236_9_goal_motivation_work_priority_integration_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1237.2-multi-tool-orchestration-foundations",
            [python, "tools/v1237_0_2_multi_tool_orchestration_foundations_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1237.5-multi-tool-orchestration-operator-review",
            [python, "tools/v1237_3_5_multi_tool_orchestration_operator_review_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1237.8-multi-tool-orchestration-adversarial-reliability",
            [python, "tools/v1237_6_8_multi_tool_orchestration_adversarial_reliability_tests.py"],
            timeout=900, performance_budget_seconds=300, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1237.9-multi-tool-orchestration-checkpoint",
            [python, "tools/v1237_9_multi_tool_orchestration_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1238.2-broader-project-language-adapter-foundations",
            [python, "tools/v1238_0_2_broader_project_language_adapter_foundations_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1238.5-broader-project-language-adapter-integration",
            [python, "tools/v1238_3_5_broader_project_language_adapter_integration_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1238.8-broader-project-language-adapter-adversarial-reliability",
            [python, "tools/v1238_6_8_broader_project_language_adapter_adversarial_reliability_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1238.9-broader-project-language-adapters-checkpoint",
            [python, "tools/v1238_9_broader_project_language_adapters_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1239.2-adversarial-execution-cognitive-boundary-foundations",
            [python, "tools/v1239_0_2_adversarial_execution_cognitive_boundary_foundations_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1239.5-adversarial-execution-boundary-attacks",
            [python, "tools/v1239_3_5_adversarial_execution_boundary_attacks_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1239.8-adversarial-cognitive-compound-boundary-attacks",
            [python, "tools/v1239_6_8_adversarial_cognitive_compound_boundary_attacks_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1239.9-adversarial-execution-cognitive-boundary-checkpoint",
            [python, "tools/v1239_9_adversarial_execution_cognitive_boundary_checkpoint_tests.py"],
            timeout=300, performance_budget_seconds=120, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1240.2-integrated-developer-beta-foundations",
            [python, "tools/v1240_0_2_integrated_developer_beta_foundations_tests.py"],
            timeout=600, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1240.5-integrated-developer-beta-end-to-end-scenarios",
            [python, "tools/v1240_3_5_integrated_developer_beta_end_to_end_scenarios_tests.py"],
            timeout=600, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1240.8-integrated-developer-beta-adversarial-reliability",
            [python, "tools/v1240_6_8_integrated_developer_beta_adversarial_reliability_tests.py"],
            timeout=600, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json(
            "v1240.9-integrated-developer-beta-checkpoint",
            [python, "tools/v1240_9_integrated_developer_beta_checkpoint_tests.py"],
            timeout=600, performance_budget_seconds=180, env_overrides=runtime_env, profiles=("quick", "full"),
        )
        execute_json("v1245.2-cross-session-project-understanding-foundations",[python,"tools/v1245_0_2_cross_session_project_understanding_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1245.5-cross-session-project-understanding-reconciliation-review",[python,"tools/v1245_3_5_cross_session_project_understanding_reconciliation_review_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1245.8-cross-session-project-understanding-adversarial-reliability",[python,"tools/v1245_6_8_cross_session_project_understanding_adversarial_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1245.9-cross-session-project-understanding-checkpoint",[python,"tools/v1245_9_cross_session_project_understanding_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.0-authoritative-cleanup-baseline",[python,"tools/v1250_0_authoritative_cleanup_baseline_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.1-segmented-broad-verifier",[python,"tools/v1250_1_segmented_broad_verifier_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.2-hermetic-verification-runtime",[python,"tools/v1250_2_hermetic_verification_runtime_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.3-release-metadata-consolidation",[python,"tools/v1250_3_release_metadata_consolidation_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.4-checkpoint-registry-consolidation",[python,"tools/v1250_4_checkpoint_registry_consolidation_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.5-compatibility-registry-migration",[python,"tools/v1250_5_compatibility_registry_migration_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.6-self-maintenance-signature-primitive-decomposition",[python,"tools/v1250_6_self_maintenance_signature_primitive_decomposition_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.7-dashboard-shell-decomposition",[python,"tools/v1250_7_dashboard_shell_decomposition_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.8-api-catalog-http-runtime-decomposition",[python,"tools/v1250_8_api_catalog_http_runtime_decomposition_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1250.9-cleanup-verification-hardening-checkpoint",[python,"tools/v1250_9_cleanup_verification_hardening_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1249.2-feature-freeze-final-hardening-foundations",[python,"tools/v1249_0_2_feature_freeze_final_hardening_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1249.5-feature-freeze-review-and-interface-stability",[python,"tools/v1249_3_5_feature_freeze_review_interface_stability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1249.8-feature-freeze-adversarial-reliability",[python,"tools/v1249_6_8_feature_freeze_adversarial_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1249.9-feature-freeze-final-hardening-checkpoint",[python,"tools/v1249_9_feature_freeze_final_hardening_checkpoint_tests.py"],timeout=600,performance_budget_seconds=180,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1248.2-integrated-mind-conversation-development-benchmark-foundations",[python,"tools/v1248_0_2_integrated_mind_conversation_development_benchmark_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1248.5-integrated-mind-conversation-development-behavioral-scenarios",[python,"tools/v1248_3_5_integrated_mind_conversation_development_behavioral_scenarios_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1248.8-integrated-mind-conversation-development-adversarial-reliability",[python,"tools/v1248_6_8_integrated_mind_conversation_development_adversarial_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1248.9-integrated-mind-conversation-development-benchmark-checkpoint",[python,"tools/v1248_9_integrated_mind_conversation_development_benchmark_checkpoint_tests.py"],timeout=600,performance_budget_seconds=180,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1247.2-privacy-security-secret-management-audit-foundations",[python,"tools/v1247_0_2_privacy_security_secret_management_audit_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1247.5-privacy-security-secret-management-operator-workflows",[python,"tools/v1247_3_5_privacy_security_secret_management_operator_workflows_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1247.8-privacy-security-secret-management-adversarial-reliability",[python,"tools/v1247_6_8_privacy_security_secret_management_adversarial_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1247.9-privacy-security-secret-management-audit-checkpoint",[python,"tools/v1247_9_privacy_security_secret_management_audit_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1246.2-initiative-proposal-pacing-foundations",[python,"tools/v1246_0_2_initiative_proposal_pacing_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1246.5-initiative-proposal-pacing-operator-review",[python,"tools/v1246_3_5_initiative_proposal_pacing_operator_review_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1246.8-initiative-proposal-pacing-adversarial-reliability",[python,"tools/v1246_6_8_initiative_proposal_pacing_adversarial_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1246.9-initiative-proposal-pacing-checkpoint",[python,"tools/v1246_9_initiative_proposal_pacing_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1244.2-long-running-multi-day-session-continuity-foundations",[python,"tools/v1244_0_2_long_running_multi_day_session_continuity_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1244.5-long-running-multi-day-session-continuity-operator-workflows",[python,"tools/v1244_3_5_long_running_multi_day_session_continuity_operator_workflows_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1244.8-long-running-multi-day-session-continuity-adversarial-reliability",[python,"tools/v1244_6_8_long_running_multi_day_session_continuity_adversarial_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1244.9-long-running-multi-day-session-continuity-checkpoint",[python,"tools/v1244_9_long_running_multi_day_session_continuity_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1243.2-provider-fallback-model-governance-foundations",[python,"tools/v1243_0_2_provider_fallback_model_governance_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1243.5-provider-fallback-model-governance-operator-review",[python,"tools/v1243_3_5_provider_fallback_model_governance_operator_review_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1243.8-provider-fallback-model-governance-adversarial-reliability",[python,"tools/v1243_6_8_provider_fallback_model_governance_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1243.9-provider-fallback-model-governance-checkpoint",[python,"tools/v1243_9_provider_fallback_model_governance_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1242.2-installation-lifecycle-integration-foundations",[python,"tools/v1242_0_2_installation_lifecycle_integration_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1242.5-installation-lifecycle-integration-workflows",[python,"tools/v1242_3_5_installation_lifecycle_integration_workflows_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1242.8-installation-lifecycle-integration-reliability",[python,"tools/v1242_6_8_installation_lifecycle_integration_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1242.9-installation-lifecycle-integration-checkpoint",[python,"tools/v1242_9_installation_lifecycle_integration_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1241.2-unified-operator-dashboard-foundations",[python,"tools/v1241_0_2_unified_operator_dashboard_foundations_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1241.5-unified-operator-dashboard-workflows",[python,"tools/v1241_3_5_unified_operator_dashboard_workflows_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1241.8-unified-operator-dashboard-reliability",[python,"tools/v1241_6_8_unified_operator_dashboard_reliability_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        execute_json("v1241.9-unified-operator-dashboard-checkpoint",[python,"tools/v1241_9_unified_operator_dashboard_checkpoint_tests.py"],timeout=300,performance_budget_seconds=120,env_overrides=runtime_env,profiles=("quick","full"))
        # v1200 was reviewed on Windows; native-provider evidence remains separately attributable.
        # Retained roadmap marker: v1199.0-v1199.2 Final Source-Only Candidate Preparation Foundations
        execute_json(
            "v1195.9-long-session-multi-day-soak-checkpoint",
            [python, "tools/v1195_9_long_session_multi_day_soak_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1193.9-verifier-ownership-historical-debt-checkpoint",
            [python, "tools/v1193_9_verifier_historical_debt_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1191.9-responsiveness-background-work-checkpoint",
            [python, "tools/v1191_9_responsiveness_background_work_checkpoint_tests.py"],
            timeout=900,
            performance_budget_seconds=120,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1190.2-unified-experience-foundations",
            [python, "tools/v1190_0_2_unified_experience_foundations_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1190.8-unified-experience-reliability",
            [python, "tools/v1190_6_8_unified_experience_reliability_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1190.9-unified-experience-checkpoint",
            [python, "tools/v1190_9_unified_experience_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1190.5-unified-experience-navigation",
            [python, "tools/v1190_3_5_unified_experience_navigation_tests.py"],
            timeout=900,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1189.9-persistent-supervised-developer-alpha-hardening-checkpoint",
            [python, "tools/v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "v1188.9-complete-campaign-development-loop-read-only-checkpoint",
            [python, "tools/v1188_9_complete_campaign_development_loop_alpha_checkpoint_tests.py"],
            timeout=1200,
            performance_budget_seconds=180,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "conversation-session-fixtures",
            [python, "tools/conversation_session_tests.py", "--json"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-session-organization-recovery-fixtures",
            [python, "tools/conversation_session_organization_tests.py", "--json"],
            timeout=150,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-experience-polish-fixtures",
            [python, "tools/conversation_experience_tests.py", "--json"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "provider-readiness-offline-recovery-fixtures",
            [python, "tools/provider_readiness_recovery_tests.py", "--json"],
            timeout=150,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "inflight-turn-reconciliation-leave-safety-fixtures",
            [python, "tools/inflight_turn_reconciliation_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "daily-reentry-unfinished-conversation-cues-fixtures",
            [python, "tools/daily_reentry_cues_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "daily-companion-resume-draft-continuity-fixtures",
            [python, "tools/daily_companion_usability_tests.py", "--json"],
            timeout=150,
            performance_budget_seconds=45,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-navigation-composer-continuity-fixtures",
            [python, "tools/conversation_navigation_continuity_tests.py", "--json"],
            timeout=210,
            performance_budget_seconds=75,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-lifecycle-new-session-continuity-fixtures",
            [python, "tools/conversation_lifecycle_continuity_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "daily-companion-polish-consolidation-fixtures",
            [python, "tools/daily_companion_polish_consolidation_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "final-checkpoint-hardening-fixtures",
            [python, "tools/final_checkpoint_hardening_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
        )
        execute_json(
            "reviewed-candidate-repair-fixtures",
            [python, "tools/reviewed_candidate_repair_tests.py", "--json"],
            timeout=210,
            performance_budget_seconds=75,
            env_overrides=runtime_env,
        )
        execute_json(
            "multi-tab-conversation-coordination-fixtures",
            [python, "tools/multi_tab_conversation_coordination_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversational-responsiveness-companion-quality-fixtures",
            [python, "tools/conversational_responsiveness_companion_quality_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversational-control-portal-regression-fixtures",
            [python, "tools/v1080_2_conversational_control_portal_tests.py"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "daily-conversation-operator-soak-fixtures",
            [python, "tools/v1080_3_daily_conversation_operator_soak_tests.py"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "desktop-alpha-candidate-consolidation-fixtures",
            [python, "tools/v1080_4_desktop_alpha_candidate_consolidation_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "desktop-alpha-daily-use-expansion-fixtures",
            [python, "tools/v1080_5_desktop_alpha_daily_use_expansion_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-search-archive-session-organization-fixtures",
            [python, "tools/v1080_6_conversation_search_archive_session_organization_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "notification-task-project-continuity-fixtures",
            [python, "tools/v1080_7_notification_task_project_continuity_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "relationship-personality-continuity-fixtures",
            [python, "tools/v1080_8_relationship_personality_continuity_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "desktop-alpha-usability-consolidation-fixtures",
            [python, "tools/v1080_9_desktop_alpha_usability_consolidation_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "consolidated-post-review-development-baseline-fixtures",
            [python, "tools/v1081_0_consolidated_post_review_baseline_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "long-session-performance-ux-hardening-fixtures",
            [python, "tools/v1086_8_long_session_performance_ux_hardening_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "offline-conversation-degradation-fixtures",
            [python, "tools/v1086_7_offline_conversation_degradation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "pinned-working-context-fixtures",
            [python, "tools/v1086_6_pinned_working_context_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "message-editing-branching-fixtures",
            [python, "tools/v1086_5_message_editing_branching_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "safe-retry-regeneration-fixtures",
            [python, "tools/v1086_4_safe_retry_regeneration_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "generation-interruption-steering-fixtures",
            [python, "tools/v1086_3_generation_interruption_steering_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "temporary-instruction-scope-fixtures",
            [python, "tools/v1086_2_temporary_instruction_scope_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "per-conversation-response-preferences-fixtures",
            [python, "tools/v1086_1_per_conversation_response_preferences_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversation-control-foundation-fixtures",
            [python, "tools/v1086_0_conversation_control_foundation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "context-intelligence-checkpoint-fixtures",
            [python, "tools/v1085_9_context_intelligence_checkpoint_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversation-topic-segmentation-fixtures",
            [python, "tools/v1085_3_conversation_topic_segmentation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "context-budget-management-fixtures",
            [python, "tools/v1085_4_context_budget_management_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "context-inspection-console-fixtures",
            [python, "tools/v1085_8_context_inspection_console_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "stale-summary-detection-fixtures",
            [python, "tools/v1085_7_stale_summary_detection_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "cross-session-thread-linking-fixtures",
            [python, "tools/v1085_6_cross_session_thread_linking_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "correction-aware-retrieval-fixtures",
            [python, "tools/v1085_5_correction_aware_retrieval_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "context-assembly-architecture-fixtures",
            [python, "tools/v1085_0_context_assembly_architecture_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "bounded-relevance-ranking-fixtures",
            [python, "tools/v1085_1_bounded_relevance_ranking_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "recency-salience-balance-fixtures",
            [python, "tools/v1085_2_recency_salience_balance_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversation-quality-foundation-fixtures",
            [python, "tools/v1084_0_conversation_quality_foundation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "turn-intent-alignment-fixtures",
            [python, "tools/v1084_1_turn_intent_alignment_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "response-length-depth-matching-fixtures",
            [python, "tools/v1084_2_response_length_depth_matching_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversational-correction-handling-fixtures",
            [python, "tools/v1084_6_conversational_correction_handling_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "personality-expression-stability-fixtures",
            [python, "tools/v1084_7_personality_expression_stability_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversation-quality-checkpoint-fixtures",
            [python, "tools/v1084_9_conversation_quality_checkpoint_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversation-quality-diagnostics-fixtures",
            [python, "tools/v1084_8_conversation_quality_diagnostics_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "unresolved-thread-continuity-fixtures",
            [python, "tools/v1084_3_unresolved_thread_continuity_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "natural-conversational-callbacks-fixtures",
            [python, "tools/v1084_4_natural_conversational_callbacks_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "topic-transition-quality-fixtures",
            [python, "tools/v1084_5_topic_transition_quality_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "relationship-continuity-checkpoint-fixtures",
            [python, "tools/v1083_9_relationship_continuity_checkpoint_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "long-session-personality-stability-fixtures",
            [python, "tools/v1083_3_long_session_personality_stability_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "mood-continuity-without-inflation-fixtures",
            [python, "tools/v1083_4_mood_continuity_without_inflation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "important-moment-provenance-fixtures",
            [python, "tools/v1083_5_important_moment_provenance_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "memory-commit-attribution-fixtures",
            [python, "tools/v1083_0_memory_commit_attribution_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "relationship-memory-curation-ux-fixtures",
            [python, "tools/v1083_1_relationship_memory_curation_ux_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "retraction-vector-cleanup-fixtures",
            [python, "tools/v1083_2_retraction_vector_cleanup_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "daily-use-stability-checkpoint-fixtures",
            [python, "tools/v1082_9_daily_use_stability_checkpoint_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "cross-process-claim-lease-fixtures",
            [python, "tools/v1082_8_cross_process_claim_lease_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "sleep-wake-hidden-tab-fixtures",
            [python, "tools/v1082_7_sleep_wake_hidden_tab_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "cancellation-retry-presentation-fixtures",
            [python, "tools/v1082_6_cancellation_retry_presentation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "large-history-rendering-fixtures",
            [python, "tools/v1082_5_large_history_rendering_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "browser-navigation-hardening-fixtures",
            [python, "tools/v1082_4_browser_navigation_hardening_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "search-archive-consistency-fixtures",
            [python, "tools/v1082_3_search_archive_consistency_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "reading-position-unread-boundary-fixtures",
            [python, "tools/v1082_2_reading_position_unread_boundary_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "cross-tab-draft-conflict-fixtures",
            [python, "tools/v1082_1_cross_tab_draft_conflict_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "offline-first-session-durability-fixtures",
            [python, "tools/v1082_0_offline_first_session_durability_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "provider-recovery-arc-consolidation-fixtures",
            [python, "tools/v1081_9_provider_recovery_arc_consolidation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "recovery-claim-resend-lineage-fixtures",
            [python, "tools/v1081_8_recovery_claim_resend_lineage_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "recovery-history-retry-presentation-fixtures",
            [python, "tools/v1081_7_recovery_history_retry_presentation_tests.py", "--json"],
            timeout=300,
        )
        execute_json(
            "conversation-failure-explicit-retry-fixtures",
            [python, "tools/v1081_6_conversation_failure_retry_tests.py", "--json"],
            timeout=300,
        ),
        execute_json(
            "recovery-evidence-conversation-resume-fixtures",
            [python, "tools/v1081_5_recovery_evidence_conversation_resume_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "offline-companion-provider-recovery-fixtures",
            [python, "tools/v1081_4_offline_companion_recovery_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "provider-availability-recovery-fixtures",
            [python, "tools/v1081_3_provider_availability_recovery_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-transport-recovery-fixtures",
            [python, "tools/v1081_2_conversation_transport_recovery_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "daily-use-baseline-soak-fixtures",
            [python, "tools/v1081_1_daily_use_baseline_soak_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        # The selector keeps this large inventory bounded by profile. Quick runs
        # only its explicitly named current integrated/current-version gates;
        # full retains its broader named acceptance set. Historical exhaustive
        # coverage remains the segmented verifier's job.
        for suite_name, suite_path in (*PRODUCT_INTEGRITY_BEHAVIOR_SUITES, *V1489_BROWSER_FOCUSED_SUITES, *V1490_BROWSER_FOCUSED_SUITES, *V1701_BROWSER_FOCUSED_SUITES, *V1801_BROWSER_FOCUSED_SUITES, *V1901_BROWSER_FOCUSED_SUITES, *V2001_BROWSER_FOCUSED_SUITES, *V2101_BROWSER_FOCUSED_SUITES, *V2201_BROWSER_FOCUSED_SUITES, *V2301_BROWSER_FOCUSED_SUITES, *V2401_BROWSER_FOCUSED_SUITES):
            execute_json(
                suite_name,
                [python, suite_path],
                timeout=240,
                performance_budget_seconds=120,
                env_overrides=runtime_env,
                profiles=("quick", "full"),
            )

        execute_json(
            "v1489-trial3-compound-grounding-memory-truth",
            [python, "tools/v1489_trial3_compound_grounding_memory_truth_tests.py"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("quick", "full"),
        )
        execute_json(
            "native-conversation-validation-fixtures",
            [python, "tools/native_conversation_validation_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "desktop-alpha-daily-use-hardening-fixtures",
            [python, "tools/desktop_alpha_daily_use_hardening_tests.py", "--json"],
            timeout=240,
            performance_budget_seconds=90,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "desktop-alpha-first-use-stabilization-fixtures",
            [python, "tools/desktop_alpha_first_use_stabilization_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
        )
        execute_json(
            "relationship-continuity-fixtures",
            [python, "tools/relationship_continuity_tests.py", "--json"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "relationship-memory-curation-fixtures",
            [python, "tools/relationship_memory_curation_tests.py", "--json"],
            timeout=120,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "mood-important-moment-continuity-fixtures",
            [python, "tools/mood_moment_continuity_tests.py", "--json"],
            timeout=120,
            performance_budget_seconds=30,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "conversation-arc-consolidation-fixtures",
            [python, "tools/conversation_arc_consolidation_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
            profiles=("full",),
        )
        execute_json(
            "v1300.9.1-desktop-checkpoint-coherence-repair",
            [python, "tools/v1300_9_1_desktop_checkpoint_coherence_repair_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
        )
        execute_json(
            "v1450.9-desktop-alpha-checkpoint",
            [python, "tools/v1450_9_desktop_alpha_checkpoint_tests.py", "--json"],
            timeout=180,
            performance_budget_seconds=60,
            env_overrides=runtime_env,
        )
        execute(
            "runtime-status",
            lambda: _run(
                [python, "conscious_agent/main.py", "--status"],
                timeout=90,
                env_overrides=_production_launcher_environment(runtime_env),
            ),
        )
        if profile == "quick" and quick_dashboard_precomputed is not None:
            dashboard_started_at = str(quick_dashboard_precomputed["started_at"])
            dashboard_step = quick_dashboard_precomputed["step"]
            dashboard_finished_at = str(quick_dashboard_precomputed["finished_at"])
            record(dashboard_step, "dashboard-http-probe")
            dashboard_source_after = str(quick_dashboard_precomputed["source_after"])
        else:
            dashboard_started_at = isoformat_utc()
            dashboard_step = execute(
                "dashboard-http-probe",
                lambda: _dashboard_probe(progress=progress, env_overrides=runtime_env),
            )
            dashboard_finished_at = isoformat_utc()
            try:
                dashboard_source_after = source_snapshot_digest(ROOT)
            except OSError:
                dashboard_source_after = "[snapshot-error]"
        dashboard_details = dashboard_step.details if isinstance(dashboard_step.details, dict) else {}
        dashboard_report = {
            "ok": dashboard_step.ok,
            "status": "pass" if dashboard_step.ok else "blocked",
            "routes": dashboard_details.get("routes") or {},
            "stage_invocation_count": dashboard_details.get("stage_invocation_count"),
            "subprocess_execution_count": dashboard_details.get("subprocess_execution_count"),
        }
        stage_reports["dashboard-http-probe"] = dashboard_report
        dashboard_commands = [[
            str(Path(sys.executable).resolve()),
            str(DASHBOARD_PROBE_WORKER),
            "--suite-json",
            json.dumps(DASHBOARD_ROUTE_TIMEOUTS, sort_keys=True),
        ]]
        stage_receipts["dashboard-http-probe"] = build_stage_receipt(
            "dashboard-http-probe",
            producer=producer,
            invocation_nonce=invocation_nonce,
            source_snapshot_before=release_source_digest,
            source_snapshot_after=dashboard_source_after,
            commands=dashboard_commands,
            report=dashboard_report,
            started_at=dashboard_started_at,
            finished_at=dashboard_finished_at,
            elapsed_seconds=dashboard_step.elapsed_seconds,
            return_code=0 if dashboard_step.ok else 1,
            timed_out=any("exceeded" in str(row.get("error", "")) for row in dashboard_report["routes"].values()),
            subprocess_execution_count=int(dashboard_report.get("subprocess_execution_count") or 0),
            attestation_key=attestation_key,
        )

        bundle = build_evidence_bundle(
            ROOT,
            producer=producer,
            invocation_nonce=invocation_nonce,
            source_snapshot_sha256=release_source_digest,
            attestation_key=attestation_key,
            stages=stage_receipts,
            purpose="release",
        )
        write_evidence_bundle(evidence_path, bundle)
        evidence_validation = validate_evidence_bundle(
            bundle,
            expected_root=ROOT,
            expected_producer=producer,
            expected_invocation_nonce=invocation_nonce,
            expected_source_snapshot=release_source_digest,
            attestation_key=attestation_key,
            expected_purpose="release",
        )
        evidence_env = {
            **runtime_env,
            ENV_EVIDENCE_FILE: str(evidence_path),
            ENV_ATTESTATION_KEY: attestation_key,
            ENV_INVOCATION_NONCE: invocation_nonce,
            ENV_EXPECTED_PRODUCER: producer,
            ENV_SOURCE_SNAPSHOT: release_source_digest,
            ENV_EVIDENCE_PURPOSE: "release",
        }

        if progress:
            print("[RUNNING] release-integrity", flush=True)
        integrity_step, integrity = _integrity_report(evidence_path, env_overrides=evidence_env)
        record(integrity_step, "release-integrity")

        if not skip_smoke:
            # Compile and main status are already executed and attested by the
            # outer verifier. Do not pay their cold-start cost again in smoke.
            smoke_skip_args = ["--skip-check", "compile", "--skip-check", "main-status"]
            if profile == "quick":
                execute(
                    "smoke-fast",
                    lambda: _run(
                        [python, "tools/smoke_check.py", "--tier", "fast", *smoke_skip_args],
                        timeout=600,
                        env_overrides=evidence_env,
                    ),
                )
            else:
                for label, smoke_args, timeout in FULL_RELEASE_SMOKE_STEPS:
                    execute_json(
                        f"smoke-{label}",
                        [python, "tools/smoke_check.py", *smoke_args, *smoke_skip_args, "--json"],
                        timeout=timeout,
                        env_overrides=evidence_env,
                        allow_trailing_object=True,
                    )
                    smoke_step = steps[-1]
                    smoke_report = stage_reports.get(f"smoke-{label}") or {}
                    failed_checks = [
                        str(row.get("name"))
                        for row in smoke_report.get("results", [])
                        if isinstance(row, dict) and row.get("ok") is not True
                    ]
                    if failed_checks:
                        smoke_step.summary += f" failed_checks={','.join(failed_checks)}"

        runtime_snapshot_after = _source_tree_snapshot(runtime_root)
        _, external_runtime_delta = _source_tree_immutability_step(runtime_snapshot_before, runtime_snapshot_after)

    runtime_cleanup_ok = bool(runtime_root_text) and not Path(runtime_root_text).exists()
    runtime_outside_source = bool(runtime_root_text) and not Path(runtime_root_text).is_relative_to(ROOT)
    runtime_isolation_ok = runtime_cleanup_ok and runtime_outside_source
    record(
        VerificationStep(
            "runtime-isolation",
            "pass" if runtime_isolation_ok else "fail",
            "Verification runtime, data, bytecode, and temporary reports stayed outside the extracted source and were removed."
            if runtime_isolation_ok
            else "The isolated verification runtime was inside the source tree or could not be removed.",
            {
                "runtime_root": runtime_root_text,
                "runtime_root_outside_source": runtime_outside_source,
                "runtime_cleanup_ok": runtime_cleanup_ok,
                "seeded_configuration_file_count": len(runtime_seeded_files),
                "seeded_configuration_files": runtime_seeded_files,
                "external_seed_write_count": len(runtime_seeded_files),
                "external_verification_write_count": external_runtime_delta.get("source_write_count"),
                "external_total_observed_write_count": len(runtime_seeded_files) + int(external_runtime_delta.get("source_write_count") or 0),
                "external_delete_count": external_runtime_delta.get("source_delete_count"),
                "external_write_dimensions": external_runtime_delta.get("write_dimensions"),
            },
        ),
        "runtime-isolation",
    )
    source_snapshot_after = _source_tree_snapshot()
    immutability_step, mutation_evidence = _source_tree_immutability_step(source_snapshot_before, source_snapshot_after)
    record(immutability_step, "source-tree-immutability")

    elapsed_before_budget = round(time.perf_counter() - verification_started, 3)
    # Quick remains the daily nine-minute gate. Full adds current representative
    # integration coverage while broad history runs through the resumable
    # segmented verifier; both profiles retain bounded Windows targets.
    performance_budget_seconds = 360 if profile == "quick" else 1800
    performance_budget_ok = elapsed_before_budget <= performance_budget_seconds
    performance_step_name = f"{profile}-profile-performance"
    record(
        VerificationStep(
            performance_step_name,
            "pass" if performance_budget_ok else "fail",
            f"{profile.title()} profile completed in {elapsed_before_budget}s against the {performance_budget_seconds}s Windows target.",
            {
                "elapsed_seconds": elapsed_before_budget,
                "performance_budget_seconds": performance_budget_seconds,
                "performance_status": "pass" if performance_budget_ok else "blocked",
                "cold_windows_target": True,
            },
            elapsed_before_budget,
        ),
        performance_step_name,
    )

    failed = [step for step in steps if not step.ok]
    total_elapsed = round(time.perf_counter() - verification_started, 3)
    stage_execution_counts = dict(evidence_validation.get("stage_execution_counts") or {})
    stage_subprocess_counts = dict(evidence_validation.get("stage_subprocess_execution_counts") or {})
    receipt_single_execution = (
        evidence_validation.get("valid") is True
        and evidence_validation.get("expensive_stage_single_execution") is True
    )
    write_dimensions = dict(mutation_evidence.get("write_dimensions") or {})
    return {
        "version": integrity.get("version"),
        "profile": profile,
        "status": "pass" if not failed else "blocked",
        "ok": not failed,
        "steps": [{**asdict(step), "ok": step.ok} for step in steps],
        "release_authorized": integrity.get("release_authorized", False),
        "autonomy_expanded": integrity.get("autonomy_expanded", False),
        "source_write_count": mutation_evidence.get("source_write_count", -1),
        "source_delete_count": mutation_evidence.get("source_delete_count", -1),
        "source_snapshot_before_count": mutation_evidence.get("before_file_count", -1),
        "source_snapshot_after_count": mutation_evidence.get("after_file_count", -1),
        "integrity_reported_source_write_count": integrity.get("source_write_count", -1),
        "integrity_reported_source_delete_count": integrity.get("source_delete_count", -1),
        "actual_fixture_execution_count": integrity.get("actual_fixture_execution_count", -1),
        "generated_wiring_activated": integrity.get("generated_wiring_activated", False),
        "operator_review_required": True,
        "elapsed_seconds": total_elapsed,
        "stage_elapsed_seconds": {step.name: step.elapsed_seconds for step in steps},
        "stage_execution_counts": stage_execution_counts,
        "stage_subprocess_execution_counts": stage_subprocess_counts,
        "expensive_stage_single_execution": receipt_single_execution,
        "verification_evidence_valid": evidence_validation.get("valid") is True,
        "verification_evidence_reason": evidence_validation.get("reason"),
        "verification_evidence_stage_validation": evidence_validation.get("stage_validation"),
        "supplemental_stage_receipts": supplemental_stage_receipts,
        "source_snapshot_sha256": release_source_digest,
        "write_dimensions": {
            "source": write_dimensions.get("source", {}),
            "configuration": write_dimensions.get("configuration", {}),
            "runtime_in_source": write_dimensions.get("runtime", {}),
            "bytecode_in_source": write_dimensions.get("bytecode", {}),
            "temporary_in_source": write_dimensions.get("temporary", {}),
            "unexpected_in_source": write_dimensions.get("unexpected", {}),
            "external_runtime": {
                "seed_write_count": len(runtime_seeded_files),
                "verification_write_count": external_runtime_delta.get("source_write_count"),
                "total_observed_write_count": len(runtime_seeded_files) + int(external_runtime_delta.get("source_write_count") or 0),
                "delete_count": external_runtime_delta.get("source_delete_count"),
                "dimensions": external_runtime_delta.get("write_dimensions"),
            },
        },
        "runtime_root_outside_source": runtime_outside_source,
        "runtime_cleanup_ok": runtime_cleanup_ok,
        "performance_budget_seconds": performance_budget_seconds,
        "performance_budget_ok": performance_budget_ok,
        "quick_profile_budget_seconds": performance_budget_seconds if profile == "quick" else None,
        "quick_profile_budget_ok": performance_budget_ok if profile == "quick" else None,
        "full_profile_budget_seconds": performance_budget_seconds if profile == "full" else None,
        "full_profile_budget_ok": performance_budget_ok if profile == "full" else None,
        "verification_graph": [
            "python-compile",
            "version-inventory",
            "corrective-suite",
            "import-compatibility",
            "runtime-status",
            "dashboard-http-probe",
            "release-integrity(injected-evidence)",
            "smoke",
            "isolated-runtime-write-inventory",
            "source-tree-immutability",
        ],
    }


def _print_text(report: dict[str, Any], *, verbose: bool) -> None:
    print(f"Eidolon release verification ({report.get('profile')})")
    print(f"Status: {report.get('status')}")
    for step in report.get("steps", []):
        print(f"[{step.get('status', 'unknown').upper()}] {step.get('name')}: {step.get('summary')}")
        if verbose and step.get("details") not in (None, "", [], {}):
            if isinstance(step.get("details"), str):
                print(step["details"])
            else:
                print(json.dumps(step.get("details"), indent=2, sort_keys=True, default=str))
    print("Safety: this report verifies evidence; it does not authorize release or expand autonomy.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the current Eidolon source release.")
    parser.add_argument("--profile", choices=("quick", "full"), default="quick")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke tiers while retaining syntax, status, integrity, and dashboard probes.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    report = build_verification(
        args.profile,
        skip_smoke=args.skip_smoke,
        progress=not args.json,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        _print_text(report, verbose=args.verbose)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    exit_code = main()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        # Some historical diagnostic imports register process-finalization work.
        # The verifier has already isolated and terminated its worker groups, so
        # bypass those unrelated atexit hooks and return the authoritative code.
        os._exit(exit_code)

# v1194.0-v1194.2 Unified Cognitive and Developer Experience Foundations
# Next bounded unit: v1194.3-v1194.5 Operator Coordination and Accountable Navigation

# v1194.3-v1194.5 Operator Coordination and Accountable Navigation
# Next bounded unit: v1194.6-v1194.8 Unified Experience Reliability and Integration Hardening

# v1194.6-v1194.8 Unified Experience Reliability and Integration Hardening
# Next bounded unit: v1194.9 Unified Cognitive and Developer Experience checkpoint

# v1194.9 Unified Cognitive and Developer Experience Checkpoint
# Next bounded unit: v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations

# v1195.0-v1195.2 Long-Session and Multi-Day Soak Foundations
# Next bounded unit: v1195.3-v1195.5 Operator-Reviewed Soak Progression

# v1195.3-v1195.5 Operator-Reviewed Soak Progression
# Next bounded unit: v1195.6-v1195.8 Soak Reliability and Adversarial Hardening

# v1195.6-v1195.8 Soak Reliability and Adversarial Hardening
# Next bounded unit: v1195.9 Long-Session and Multi-Day Soak checkpoint

# v1195.9 Long-Session and Multi-Day Soak Checkpoint
# Next bounded unit: v1196.0-v1196.2 Adversarial Privacy and Authority Foundations

# v1197.3-v1197.5 Operator-Reviewed Runtime Lifecycle Application
# Next bounded unit: v1197.6-v1197.8 Runtime Lifecycle Reliability and Adversarial Hardening

# v1197.6-v1197.8 Runtime Lifecycle Reliability and Adversarial Hardening
# Next bounded unit: v1197.9 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Checkpoint
# v1197.9 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Checkpoint
# Next bounded unit: v1198.0-v1198.2 Feature Freeze and Architecture Consolidation Foundations


# Retained roadmap marker: v1198.3-v1198.5 Operator Freeze Exceptions and Consolidation Review
