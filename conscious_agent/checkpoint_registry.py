from __future__ import annotations

"""Canonical checkpoint registry with preserved source-discovery compatibility.

The v1250.4 structured registry indexes whole-version release checkpoints and
provides one read-only report schema for new cleanup work.  The original
v1150.2 source-discovered checkpoint descriptor API remains available because
many retained checkpoints and architecture dispatch callers depend on it.
Neither registry executes checkpoint builders during inspection, reads runtime
data, contacts providers, mutates source, or grants authority.
"""

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from release_authority import CHECKPOINT_HISTORY, WORKING_SOURCE_VERSION
except ImportError:
    from release_authority import CHECKPOINT_HISTORY, WORKING_SOURCE_VERSION  # type: ignore

CONTRACT_VERSION = "v1250.4"
LEGACY_DISCOVERY_CONTRACT_VERSION = "v1150.2"
REPORT_SCHEMA = "eidolon.read-only-checkpoint-report.v1"

AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "commands_executed": False,
    "tests_executed": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "cognition_written": False,
    "independent_authority_granted": False,
}

# Preserved v1150.2 source-discovery compatibility contract.
_MIN_CURRENT_CONTRACT = (1108, 0)
_COMPATIBILITY_ALIASES = {
    "conversation-cognition-unification": (
        "conscious_agent.conversation_cognition_unification_governance_checkpoint",
        "build_conversation_cognition_unification_governance_checkpoint",
    ),
    "understandable-cognitive-controls": (
        "conscious_agent.understandable_cognitive_controls_governance_checkpoint",
        "build_understandable_cognitive_controls_governance_checkpoint",
    ),
}
_NO_VERSION_CURRENT_PREFIXES = (
    "conversation_",
    "natural_conversation_",
    "first_use_",
    "context_intelligence_",
)
_EXCLUDED_MODULES = {
    "checkpoint_registry",
    "architecture_checkpoint_dispatch",
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _source_root(value: str | Path | None = None) -> Path:
    return Path(value or Path(__file__).resolve().parents[1]).expanduser().resolve()


# ---------------------------------------------------------------------------
# Preserved source-discovered descriptor API
# ---------------------------------------------------------------------------


def _literal_string(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _contract_version(tree: ast.Module) -> str:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == "CONTRACT_VERSION" for target in targets):
            return _literal_string(node.value)
    return ""


def _version_number(value: str) -> tuple[int, int]:
    token = str(value or "").strip().lower().lstrip("v")
    try:
        major, minor = token.split(".", 1)
        return int(major), int("".join(ch for ch in minor if ch.isdigit()) or 0)
    except (ValueError, AttributeError):
        return (0, 0)


def _is_current_checkpoint(stem: str, contract_version: str) -> bool:
    version = _version_number(contract_version)
    if version >= _MIN_CURRENT_CONTRACT:
        return True
    return not contract_version and stem.startswith(_NO_VERSION_CURRENT_PREFIXES)


def _legacy_checkpoint_id(stem: str, builder: str, builder_count: int) -> str:
    base = stem.replace("_", "-")
    if builder_count == 1:
        return base
    return f"{base}:{builder.replace('_', '-')}"


def _descriptor_rows_uncached(source: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    package = source / "conscious_agent"
    for path in sorted(package.glob("*.py")):
        stem = path.stem
        if stem in _EXCLUDED_MODULES or "checkpoint" not in stem:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        contract_version = _contract_version(tree)
        if not _is_current_checkpoint(stem, contract_version):
            continue
        builder_nodes = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("build_")
            and "checkpoint" in node.name
        }
        builders = sorted(builder_nodes)
        for builder in builders:
            node = builder_nodes[builder]
            positional = list(node.args.posonlyargs) + list(node.args.args)
            default_start = len(positional) - len(node.args.defaults)
            required_inputs = [
                argument.arg
                for index, argument in enumerate(positional)
                if index < default_start
                and argument.arg not in {"source_root", "runtime_root", "data_dir", "root"}
            ]
            descriptor = {
                "checkpoint_id": _legacy_checkpoint_id(stem, builder, len(builders)),
                "contract_version": contract_version or "unversioned-current-contract",
                "module": f"conscious_agent.{stem}",
                "builder": builder,
                "relative_path": path.relative_to(source).as_posix(),
                "discovery": "source_ast",
                "read_only_required": True,
                "read_only": True,
                "post_available": False,
                "required_inputs": required_inputs,
                "required_input_count": len(required_inputs),
            }
            descriptor["structural_digest"] = _digest(descriptor)
            rows.append(descriptor)
    return rows


def _descriptor_source_signature(source: Path) -> tuple[tuple[str, int, int], ...]:
    package = source / "conscious_agent"
    rows: list[tuple[str, int, int]] = []
    for path in sorted(package.glob("*.py")):
        if "checkpoint" not in path.stem:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        rows.append((path.name, int(stat.st_mtime_ns), int(stat.st_size)))
    return tuple(rows)


@lru_cache(maxsize=8)
def _descriptor_rows_cached(
    source_text: str,
    source_signature: tuple[tuple[str, int, int], ...],
) -> tuple[str, ...]:
    del source_signature
    rows = _descriptor_rows_uncached(Path(source_text))
    return tuple(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)


def _descriptor_rows(source: Path) -> list[dict[str, Any]]:
    serialized = _descriptor_rows_cached(str(source), _descriptor_source_signature(source))
    return [json.loads(row) for row in serialized]


def checkpoint_descriptors(*, source_root: str | Path | None = None) -> tuple[dict[str, Any], ...]:
    """Return current checkpoint builders in deterministic source order."""

    return tuple(_descriptor_rows(_source_root(source_root)))


def _alias_rows(descriptors: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    by_target = {(row["module"], row["builder"]): row for row in descriptors}
    aliases: list[dict[str, Any]] = []
    for alias, target in sorted(_COMPATIBILITY_ALIASES.items()):
        descriptor = by_target.get(target)
        aliases.append(
            {
                "alias": alias,
                "target_checkpoint_id": descriptor.get("checkpoint_id", "") if descriptor else "",
                "target_available": descriptor is not None,
            }
        )
    return aliases


def inspect_checkpoint_registry(*, source_root: str | Path | None = None) -> dict[str, Any]:
    """Preserved v1150.2 descriptor inspection surface."""

    descriptors = checkpoint_descriptors(source_root=source_root)
    ids = [row["checkpoint_id"] for row in descriptors]
    modules = [row["module"] for row in descriptors]
    builders = [(row["module"], row["builder"]) for row in descriptors]
    aliases = _alias_rows(descriptors)
    return {
        "contract_version": LEGACY_DISCOVERY_CONTRACT_VERSION,
        "registry_id": "checkpoint-registry:v1150.2",
        "checkpoints": [dict(row) for row in descriptors],
        "checkpoint_count": len(descriptors),
        "checkpoint_module_count": len(set(modules)),
        "duplicate_checkpoint_ids": sorted({item for item in ids if ids.count(item) > 1}),
        "duplicate_builder_targets": sorted(
            f"{module}:{builder}"
            for module, builder in set(builders)
            if builders.count((module, builder)) > 1
        ),
        "compatibility_aliases": aliases,
        "compatibility_alias_count": len(aliases),
        "all_compatibility_targets_available": all(row["target_available"] for row in aliases),
        "required_input_names": sorted(
            {name for row in descriptors for name in row.get("required_inputs", [])}
        ),
        "all_required_inputs_dispatch_supported": all(
            set(row.get("required_inputs", [])).issubset({"bootstrap"}) for row in descriptors
        ),
        "invocation_authority": "read_only_builder_only",
        "provider_contacted": False,
        "runtime_data_read": False,
        "source_modified": False,
        "content_free": True,
        "read_only": True,
        "structural_digest": _digest(descriptors),
    }


def _resolve_descriptor(
    checkpoint_id: str,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(checkpoint_id or "").strip()
    descriptors = checkpoint_descriptors(source_root=source_root)
    descriptor = next((row for row in descriptors if row["checkpoint_id"] == token), None)
    if descriptor is not None:
        return dict(descriptor)
    target = _COMPATIBILITY_ALIASES.get(token)
    if target:
        descriptor = next(
            (row for row in descriptors if (row["module"], row["builder"]) == target),
            None,
        )
        if descriptor is not None:
            resolved = dict(descriptor)
            resolved["resolved_from_alias"] = token
            return resolved
    raise KeyError(token)


def resolve_checkpoint_builder(
    checkpoint_id: str,
    *,
    source_root: str | Path | None = None,
) -> Callable[..., dict[str, Any]]:
    descriptor = _resolve_descriptor(checkpoint_id, source_root=source_root)
    module = __import__(descriptor["module"], fromlist=[descriptor["builder"]])
    builder = getattr(module, descriptor["builder"])
    if not callable(builder):
        raise TypeError("checkpoint builder is not callable")
    return builder


def resolve_checkpoint_descriptor(
    checkpoint_id: str,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    return _resolve_descriptor(checkpoint_id, source_root=source_root)


# ---------------------------------------------------------------------------
# v1250.4 structured release-checkpoint registry and report schema
# ---------------------------------------------------------------------------


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _selector(version: str) -> str:
    recent_explicit_selectors = {
        "1489.0200": "tools/v1489_0191_0200_integrated_completion_benchmark_tests.py",
        "1490.2": "tools/v1490_0_2_dynamic_improvement_discovery_tests.py",
        "1500.1.9": "tools/v1500_1_conversation_memory_identity_repair_tests.py",
        "1500.2.0": "tools/v1500_2_entity_association_foundation_tests.py",
        "1500.3.0": "tools/v1500_3_conversation_entity_association_tests.py",
        "1500.3.1": "tools/v1500_3_conversation_entity_association_tests.py",
        "1500.4.0": "tools/v1500_4_entity_association_curation_tests.py",
        "1500.5.0": "tools/v1500_5_conversational_association_governance_tests.py",
        "1500.6.0": "tools/v1500_6_dashboard_simplification_performance_tests.py",
        "1500.7.0": "tools/v1500_7_natural_association_coherence_tests.py",
        "1500.8.0": "tools/v1500_8_conversation_target_continuity_tests.py",
        "1500.9.0": "tools/v1500_9_integrated_daily_use_conversation_tests.py",
        "1501.0": "tools/v1501_0_supervised_initiative_queue_tests.py",
        "1501.2": "tools/v1501_2_sustained_supervised_initiative_tests.py",
        "1501.3": "tools/v1501_3_initiative_evidence_intake_tests.py",
        "1508.9": "tools/v1508_9_initiative_evidence_review_checkpoint_tests.py",
        "1516.9": "tools/v1516_9_initiative_value_model_checkpoint_tests.py",
        "1525.9": "tools/v1525_9_value_prioritized_selection_checkpoint_tests.py",
        "1550.9": "tools/v1550_9_defect_feedback_intelligence_checkpoint_tests.py",
        "1575.9": "tools/v1575_9_repair_retry_intelligence_checkpoint_tests.py",
        "1599.9": "tools/v1599_9_multi_cycle_supervised_campaign_checkpoint_tests.py",
        "1600.9": "tools/v1600_9_era1_desktop_gate_tests.py",
        "1699.9": "tools/v1699_9_release_upgrade_engineering_checkpoint_tests.py",
        "1700.9": "tools/v1700_9_era2_desktop_engineering_gate_tests.py",
        "1725.9": "tools/v1725_9_requirements_problem_framing_checkpoint_tests.py",
        "1750.9": "tools/v1750_9_causal_counterfactual_reasoning_checkpoint_tests.py",
        "1775.9": "tools/v1775_9_long_horizon_planning_checkpoint_tests.py",
        "1799.9": "tools/v1799_9_metacognition_epistemic_control_checkpoint_tests.py",
        "1800.9": "tools/v1800_9_era3_desktop_cognitive_gate_tests.py",
        "1825.9": "tools/v1825_9_memory_consolidation_retrieval_checkpoint_tests.py",
        "1850.9": "tools/v1850_9_temporal_identity_checkpoint_tests.py",
        "1875.9": "tools/v1875_9_revisable_belief_world_model_checkpoint_tests.py",
        "1899.9": "tools/v1899_9_knowledge_maintenance_checkpoint_tests.py",
        "1900.9": "tools/v1900_9_era4_desktop_memory_world_model_gate_tests.py",
        "1925.9": "tools/v1925_9_discourse_conversational_flow_tests.py",
        "1950.9": "tools/v1950_9_personality_identity_expression_tests.py",
        "1975.9": "tools/v1975_9_emotional_architecture_regulation_tests.py",
        "1999.9": "tools/v1999_9_era5_integrated_companion_tests.py",
        "2000.9": "tools/v2000_9_era5_desktop_daily_companion_coherence_gate_tests.py",
        "2025.9": "tools/v2025_9_attention_salience_checkpoint_tests.py",
        "2050.9": "tools/v2050_9_background_scheduler_checkpoint_tests.py",
        "2075.9": "tools/v2075_9_proactive_communication_checkpoint_tests.py",
        "2099.9": "tools/v2099_9_era6_integrated_attention_initiative_tests.py",
        "2100.9": "tools/v2100_9_era6_desktop_attention_initiative_gate_tests.py",
        "2125.9": "tools/v2125_9_local_system_application_tools_tests.py",
        "2150.9": "tools/v2150_9_research_web_intelligence_tests.py",
        "2175.9": "tools/v2175_9_voice_audio_presence_tests.py",
        "2199.9": "tools/v2199_9_era7_integrated_interaction_tests.py",
        "2200.9": "tools/v2200_9_era7_desktop_gate_tests.py",
        "2225.9": "tools/v2225_9_fine_grained_authority_permissions_tests.py",
        "2250.9": "tools/v2250_9_untrusted_content_defense_tests.py",
        "2275.9": "tools/v2275_9_fault_tolerance_recovery_tests.py",
        "2299.9": "tools/v2299_9_era8_integrated_trustworthy_operation_tests.py",
        "2300.9": "tools/v2300_9_era8_desktop_gate_tests.py",
        "2325.9": "tools/v2325_9_outcome_learning_checkpoint_tests.py",
        "2350.9": "tools/v2350_9_preference_adaptation_checkpoint_tests.py",
        "2375.9": "tools/v2375_9_cooperative_development_checkpoint_tests.py",
        "2399.9": "tools/v2399_9_era9_integrated_mind_tests.py",
        "2400.9": "tools/v2400_9_era9_desktop_integrated_mind_gate_tests.py",
        "2425.9": "tools/v2425_9_desktop_product_maturity_tests.py",
        "2450.9": "tools/v2450_9_unattended_operation_soak_tests.py",
        "2475.9": "tools/v2475_9_autonomous_developer_beta_tests.py",
        "2499.9": "tools/v2499_9_era10_integrated_product_autonomy_tests.py",
        "2500.9": "tools/v2500_9_era10_desktop_adversarial_gate_tests.py",
        # Historical 2501/2503 checkpoints with multiple/no wildcard matches are
        # bound to one retained evidence suite each so registry resolution is unique.
        "2501.1": "tools/v2501_1_governed_public_web_research_adapter_tests.py",
        "2501.9": "tools/v2501_9_desktop_research_acceptance_tests.py",
        "2503.0.1": "tools/v2503_0_research_planning_native_synthesis_repair_tests.py",
        "2503.2": "tools/v2503_2_candidate_specific_evidence_follow_up_tests.py",
        "2503.3": "tools/v2503_3_source_independence_recommendation_confidence_tests.py",
        "2503.4": "tools/v2503_4_evidence_language_consistency_source_quality_tests.py",
        "2503.4.1": "tools/v2503_4_1_research_finding_routing_anti_overfit_tests.py",
        "2503.4.2": "tools/v2503_4_2_one_command_product_repair_cycle_tests.py",
        "2503.4.3": "tools/v2503_4_3_dedicated_syntax_repair_tests.py",
        "2503.4.28": "tools/v2503_4_28_training_readiness_checkpoint_tests.py",
        "2503.4.30": "tools/v2503_4_30_training_provenance_benchmark_tests.py",
        "2503.5.0": "tools/v2503_5_candidate_specific_evidence_discovery_tests.py",
        "2503.5.1": "tools/v2503_5_candidate_specific_evidence_discovery_tests.py",
        "2503.5.2": "tools/v2503_5_candidate_specific_evidence_discovery_tests.py",
        "2503.5.3": "tools/v2503_5_candidate_specific_evidence_discovery_tests.py",
        "2503.5.4": "tools/v2503_5_candidate_specific_evidence_discovery_tests.py",
        "2503.5.5": "tools/v2503_5_candidate_specific_evidence_discovery_tests.py",
        "2503.7.9": "tools/v2503_7_9_architecture_reasoning_checkpoint_tests.py",
        "2504.9": "tools/v2504_9_unified_cognitive_runtime_alpha_checkpoint_tests.py",
        "2505.9": "tools/v2505_9_bounded_background_cognition_checkpoint_tests.py",
        "2506.9": "tools/v2506_6_9_unified_memory_consolidation_checkpoint_tests.py",
        "2507.9": "tools/v2507_7_9_developmental_self_model_checkpoint_tests.py",
        "2508.9": "tools/v2508_9_cognitive_continuity_campaign_checkpoint_tests.py",
        "2509.9": "tools/v2509_9_general_capability_action_framework_checkpoint_tests.py",
        "2510.9": "tools/v2510_6_9_live_activity_ui_checkpoint_tests.py",
        "2511.9": "tools/v2511_7_9_mental_activity_timeline_checkpoint_tests.py",
        "2512.9": "tools/v2512_9_capability_activity_voice_campaign_checkpoint_tests.py",
        "2513.9": "tools/v2513_9_general_capability_adapter_registry_checkpoint_tests.py",
        "2514.9": "tools/v2514_9_general_capability_governance_bridge_checkpoint_tests.py",
        "2515.9": "tools/v2515_9_general_capability_execution_envelope_checkpoint_tests.py",
        "2516.9": "tools/v2516_9_general_capability_inert_preview_checkpoint_tests.py",
        "2517.9": "tools/v2517_9_general_capability_adapter_governance_alpha_checkpoint_tests.py",
        "2518.9": "tools/v2518_9_general_capability_recovery_checkpoint_tests.py",
        "2519.9": "tools/v2519_9_general_capability_lifecycle_reconciliation_checkpoint_tests.py",
        "2520.9": "tools/v2520_9_general_capability_lifecycle_alpha_checkpoint_tests.py",
        "2522.9": "tools/v2522_0_9_richer_structural_cognition_tests.py",
        "2523.9": "tools/v2523_0_9_state_grounded_internal_voice_beta_tests.py",
        "2524.9": "tools/v2524_0_9_background_episode_voice_integration_tests.py",
        "2525.9": "tools/v2525_9_richer_internal_cognition_voice_checkpoint_tests.py",
        "2526.9": "tools/v2526_0_9_provider_admission_tests.py",
        "2527.9": "tools/v2527_0_9_provider_runtime_tests.py",
        "2528.9": "tools/v2528_0_9_provider_voice_guard_tests.py",
        "2529.9": "tools/v2529_9_internal_voice_provider_alpha_checkpoint_tests.py",
        "2530.9": "tools/v2530_0_9_live_internal_voice_runtime_tests.py",
        "2531.9": "tools/v2531_0_9_internal_voice_provider_audit_tests.py",
        "2532.9": "tools/v2532_9_live_internal_voice_provider_integration_checkpoint_tests.py",
        "2536.9": "tools/v2536_9_cognitive_observability_dashboard_beta_checkpoint_tests.py",
        "2540.9": "tools/v2540_9_cognitive_observability_dashboard_beta_completion_tests.py",
        "2543.9": "tools/v2543_9_tiered_fast_verification_alpha_checkpoint_tests.py",
        "2546.9": "tools/v2546_9_verification_feedback_alpha_checkpoint_tests.py",
        "2553.9": "tools/v2553_9_verification_history_flakiness_alpha_checkpoint_tests.py",
        "2556.9": "tools/v2556_9_verification_history_recovery_checkpoint_tests.py",
        "2565.9": "tools/v2565_9_verification_observability_coverage_checkpoint_tests.py",
        "2568.9": "tools/v2568_9_verification_gap_remediation_foundations_checkpoint_tests.py",
        "2574.9": "tools/v2574_9_memory_retrieval_precision_alpha_checkpoint_tests.py",
        "2578.9": "tools/v2578_9_memory_retrieval_observability_checkpoint_tests.py",
        "2579.9": "tools/v2579_memory_retrieval_outcome_tests.py",
        "2580.9": "tools/v2580_memory_retrieval_outcome_history_tests.py",
        "2581.9": "tools/v2581_memory_retrieval_learning_profile_tests.py",
        "2582.9": "tools/v2582_memory_retrieval_learning_advisory_tests.py",
        "2583.9": "tools/v2583_memory_retrieval_followup_learning_tests.py",
        "2584.9": "tools/v2584_memory_retrieval_learning_observability_tests.py",
        "2585.9": "tools/v2585_memory_retrieval_policy_review_tests.py",
        "2586.9": "tools/v2586_9_memory_retrieval_outcome_learning_checkpoint_tests.py",
        "2587.9": "tools/v2587_conversation_context_attribution_tests.py",
        "2588.9": "tools/v2588_conversation_context_arbitration_tests.py",
        "2589.9": "tools/v2589_conversation_context_sufficiency_tests.py",
        "2590.9": "tools/v2590_conversation_context_observability_tests.py",
        "2591.9": "tools/v2591_9_conversation_context_attribution_checkpoint_tests.py",
        "2592.9": "tools/v2592_project_success_contract_tests.py",
        "2593.9": "tools/v2593_project_outcome_evidence_tests.py",
        "2594.9": "tools/v2594_project_success_evaluator_tests.py",
        "2595.9": "tools/v2595_project_outcome_learning_tests.py",
        "2596.9": "tools/v2596_project_success_review_tests.py",
        "2597.9": "tools/v2597_project_success_observability_tests.py",
        "2598.9": "tools/v2598_9_project_success_evaluation_alpha_checkpoint_tests.py",
        "2599.9": "tools/v2599_project_outcome_history_tests.py",
        "2600.9": "tools/v2600_project_strategy_reliability_tests.py",
        "2601.9": "tools/v2601_project_value_calibration_tests.py",
        "2602.9": "tools/v2602_project_strategy_learning_tests.py",
        "2603.9": "tools/v2603_project_strategy_developer_evidence_tests.py",
        "2604.9": "tools/v2604_project_outcome_learning_observability_tests.py",
        "2605.9": "tools/v2605_9_project_outcome_comparative_learning_checkpoint_tests.py",
        "2606.9": "tools/v2606_project_strategy_plan_confidence_tests.py",
        "2607.9": "tools/v2607_adaptive_plan_strategy_ranking_tests.py",
        "2608.9": "tools/v2608_project_strategy_plan_signal_tests.py",
        "2609.9": "tools/v2609_project_outcome_mind_observability_tests.py",
        "2610.9": "tools/v2610_9_project_outcome_strategy_learning_checkpoint_tests.py",
        "2611.9": "tools/v2611_2614_developer_portfolio_planning_tests.py",
        "2612.9": "tools/v2611_2614_developer_portfolio_planning_tests.py",
        "2613.9": "tools/v2611_2614_developer_portfolio_planning_tests.py",
        "2614.9": "tools/v2611_2614_developer_portfolio_planning_tests.py",
        "2615.9": "tools/v2615_2617_portfolio_conflict_sensitivity_checkpoint_tests.py",
        "2616.9": "tools/v2615_2617_portfolio_conflict_sensitivity_checkpoint_tests.py",
        "2618.9": "tools/v2618_2620_project_queue_foundations_tests.py",
        "2619.9": "tools/v2618_2620_project_queue_foundations_tests.py",
        "2620.9": "tools/v2618_2620_project_queue_foundations_tests.py",
        "2617.9": "tools/v2617_9_outcome_aware_developer_portfolio_planning_checkpoint_tests.py",
        "2621.9": "tools/v2621_9_developer_project_queue_checkpoint_tests.py",
        "2630.9": "tools/v2630_9_developer_project_queue_staleness_checkpoint_tests.py",
        "2639.9": "tools/v2638_2639_project_queue_restart_checkpoint_tests.py",
        "2643.9": "tools/v2643_9_project_start_preflight_checkpoint_tests.py",
        "2651.9": "tools/v2651_9_project_lifecycle_simulation_alpha_checkpoint_tests.py",
        "2655.9": "tools/v2655_9_simulated_campaign_evidence_bridge_checkpoint_tests.py",
        "2659.9": "tools/v2659_9_project_simulation_observability_checkpoint_tests.py",
        "2663.9": "tools/v2663_9_project_rehearsal_safety_checkpoint_tests.py",
        "2667.9": "tools/v2667_9_project_rehearsal_comparison_checkpoint_tests.py",
        "2671.9": "tools/v2671_9_portfolio_rehearsal_checkpoint_tests.py",
        "2675.9": "tools/v2675_9_response_grounding_coherence_checkpoint_tests.py",
        "2679.9": "tools/v2679_9_response_grounding_outcome_learning_checkpoint_tests.py",
        "2682.9": "tools/v2682_9_response_grounding_observability_checkpoint_tests.py",
        "2685.9": "tools/v2685_9_response_grounding_output_audit_checkpoint_tests.py",
        "2689.9": "tools/v2689_9_response_grounding_safe_repair_checkpoint_tests.py",
        "2693.9": "tools/v2693_9_conversation_target_outcome_learning_checkpoint_tests.py",
        "2696.9": "tools/v2696_9_conversation_health_checkpoint_tests.py",
        "2699.9": "tools/v2699_9_conversation_health_trend_checkpoint_tests.py",
        "2709.9": "tools/v2709_9_response_quality_evaluation_checkpoint_tests.py",
        "2715.9": "tools/v2713_2715_daily_use_runtime_tests.py",
        "2719.9": "tools/v2719_9_daily_use_readiness_checkpoint_tests.py",
        "2729.9": "tools/v2729_9_combined_trial_campaign_preparation_checkpoint_tests.py",
        "2729.9.1": "tools/v2729_9_1_release_integrity_repair_checkpoint_tests.py",
        "2729.9.2": "tools/v2729_9_2_release_parity_campaign_binding_hardening_checkpoint_tests.py",
    }
    if version in recent_explicit_selectors:
        return recent_explicit_selectors[version]
    # v1401+ uses the standard four-suite whole-version contract without another thousand-line selector table.
    try:
        whole, sub = (int(part) for part in str(version).split(".", 1))
    except (TypeError, ValueError):
        whole, sub = 0, -1
    # v1450 was supplied as one consolidated native Desktop Alpha validation checkpoint.
    # Preserve that historical evidence shape rather than inventing intermediate suite files.
    if whole == 1450 and 0 <= sub <= 9:
        return "tools/v1450_9_desktop_alpha_checkpoint_tests.py"
    if (1401 <= whole <= 1449) or (1451 <= whole <= 1488):
        if 0 <= sub <= 2:
            return f"tools/v{whole}_0_2_*_foundations_tests.py"
        if 3 <= sub <= 5:
            return f"tools/v{whole}_3_5_*_integration_tests.py"
        if 6 <= sub <= 8:
            return f"tools/v{whole}_6_8_*_reliability_tests.py"
        if sub == 9:
            return f"tools/v{whole}_9_*_checkpoint_tests.py"
    if version in {"1251.0", "1251.1", "1251.2"}:
        return "tools/v1251_0_2_response_time_prompt_efficiency_tests.py"
    if version in {"1251.3", "1251.4", "1251.5"}:
        return "tools/v1251_3_5_action_startup_provider_efficiency_tests.py"
    if version in {"1251.6", "1251.7", "1251.8"}:
        return "tools/v1251_6_8_dashboard_response_time_tests.py"
    if version == "1251.9":
        return "tools/v1251_9_response_time_runtime_efficiency_checkpoint_tests.py"
    if version in {"1252.0", "1252.1", "1252.2"}:
        return "tools/v1252_0_2_conversation_indexing_tests.py"
    if version in {"1252.3", "1252.4", "1252.5"}:
        return "tools/v1252_3_5_memory_storage_indexing_tests.py"
    if version in {"1252.6", "1252.7", "1252.8"}:
        return "tools/v1252_6_8_action_cache_migration_tests.py"
    if version == "1252.9":
        return "tools/v1252_9_persistent_state_performance_checkpoint_tests.py"
    if version in {"1253.0", "1253.1", "1253.2"}:
        return "tools/v1253_0_2_critical_path_work_efficiency_tests.py"
    if version in {"1253.3", "1253.4", "1253.5"}:
        return "tools/v1253_3_5_import_dependency_efficiency_tests.py"
    if version in {"1253.6", "1253.7", "1253.8"}:
        return "tools/v1253_6_8_performance_governance_tests.py"
    if version == "1253.9":
        return "tools/v1253_9_runtime_efficiency_beta_checkpoint_tests.py"
    if version == "1253.9.1":
        return "tools/v1253_9_1_pre_codex_runtime_coherence_repair_tests.py"
    if version == "1253.9.2":
        return "tools/v1253_9_2_windows_runtime_coherence_repair_tests.py"
    if version in {"1254.0", "1254.1", "1254.2"}:
        return "tools/v1254_0_2_isolated_coding_execution_foundations_tests.py"
    if version in {"1254.3", "1254.4", "1254.5"}:
        return "tools/v1254_3_5_isolated_coding_execution_integration_tests.py"
    if version in {"1254.6", "1254.7", "1254.8"}:
        return "tools/v1254_6_8_isolated_coding_execution_reliability_tests.py"
    if version == "1254.9":
        return "tools/v1254_9_isolated_coding_execution_checkpoint_tests.py"
    if version in {"1255.0", "1255.1", "1255.2"}:
        return "tools/v1255_0_2_controlled_application_foundations_tests.py"
    if version in {"1255.3", "1255.4", "1255.5"}:
        return "tools/v1255_3_5_controlled_application_integration_tests.py"
    if version in {"1255.6", "1255.7", "1255.8"}:
        return "tools/v1255_6_8_controlled_application_reliability_tests.py"
    if version == "1255.9":
        return "tools/v1255_9_controlled_application_rollback_checkpoint_tests.py"
    if version in {"1256.0", "1256.1", "1256.2"}:
        return "tools/v1256_0_2_persistent_development_session_foundations_tests.py"
    if version in {"1256.3", "1256.4", "1256.5"}:
        return "tools/v1256_3_5_persistent_development_session_integration_tests.py"
    if version in {"1256.6", "1256.7", "1256.8"}:
        return "tools/v1256_6_8_persistent_development_session_reliability_tests.py"
    if version == "1256.9":
        return "tools/v1256_9_persistent_development_sessions_checkpoint_tests.py"
    if version in {"1257.0", "1257.1", "1257.2"}:
        return "tools/v1257_0_2_diagnostic_repair_reasoning_foundations_tests.py"
    if version in {"1257.3", "1257.4", "1257.5"}:
        return "tools/v1257_3_5_diagnostic_repair_reasoning_integration_tests.py"
    if version in {"1257.6", "1257.7", "1257.8"}:
        return "tools/v1257_6_8_diagnostic_repair_reasoning_reliability_tests.py"
    if version == "1257.9":
        return "tools/v1257_9_diagnostic_repair_reasoning_checkpoint_tests.py"
    if version in {"1258.0", "1258.1", "1258.2"}:
        return "tools/v1258_0_2_complete_application_construction_foundations_tests.py"
    if version in {"1258.3", "1258.4", "1258.5"}:
        return "tools/v1258_3_5_complete_application_construction_integration_tests.py"
    if version in {"1258.6", "1258.7", "1258.8"}:
        return "tools/v1258_6_8_complete_application_construction_reliability_tests.py"
    if version == "1258.9":
        return "tools/v1258_9_complete_application_construction_checkpoint_tests.py"
    if version in {"1259.0", "1259.1", "1259.2"}:
        return "tools/v1259_0_2_conversational_command_integration_foundations_tests.py"
    if version in {"1259.3", "1259.4", "1259.5"}:
        return "tools/v1259_3_5_conversational_command_integration_tests.py"
    if version in {"1259.6", "1259.7", "1259.8"}:
        return "tools/v1259_6_8_conversational_command_integration_reliability_tests.py"
    if version == "1259.9":
        return "tools/v1259_9_conversational_command_integration_checkpoint_tests.py"
    if version in {"1260.0", "1260.1", "1260.2"}:
        return "tools/v1260_0_2_coding_alpha_foundations_tests.py"
    if version in {"1260.3", "1260.4", "1260.5"}:
        return "tools/v1260_3_5_coding_alpha_campaign_tests.py"
    if version in {"1260.6", "1260.7", "1260.8"}:
        return "tools/v1260_6_8_coding_alpha_reliability_tests.py"
    if version == "1260.9":
        return "tools/v1260_9_coding_alpha_checkpoint_tests.py"
    if version in {"1261.0", "1261.1", "1261.2"}:
        return "tools/v1261_0_2_evidence_based_project_inspection_foundations_tests.py"
    if version in {"1261.3", "1261.4", "1261.5"}:
        return "tools/v1261_3_5_evidence_based_project_inspection_integration_tests.py"
    if version in {"1261.6", "1261.7", "1261.8"}:
        return "tools/v1261_6_8_evidence_based_project_inspection_reliability_tests.py"
    if version == "1261.9":
        return "tools/v1261_9_evidence_based_project_inspection_checkpoint_tests.py"
    if version in {"1262.0", "1262.1", "1262.2"}:
        return "tools/v1262_0_2_development_backlog_generation_foundations_tests.py"
    if version in {"1262.3", "1262.4", "1262.5"}:
        return "tools/v1262_3_5_development_backlog_generation_integration_tests.py"
    if version in {"1262.6", "1262.7", "1262.8"}:
        return "tools/v1262_6_8_development_backlog_generation_reliability_tests.py"
    if version == "1262.9":
        return "tools/v1262_9_development_backlog_generation_checkpoint_tests.py"
    if version in {"1263.0", "1263.1", "1263.2"}:
        return "tools/v1263_0_2_priority_selection_foundations_tests.py"
    if version in {"1263.3", "1263.4", "1263.5"}:
        return "tools/v1263_3_5_priority_selection_integration_tests.py"
    if version in {"1263.6", "1263.7", "1263.8"}:
        return "tools/v1263_6_8_priority_selection_reliability_tests.py"
    if version == "1263.9":
        return "tools/v1263_9_priority_selection_checkpoint_tests.py"
    if version in {"1264.0", "1264.1", "1264.2"}:
        return "tools/v1264_0_2_alternative_planning_foundations_tests.py"
    if version in {"1264.3", "1264.4", "1264.5"}:
        return "tools/v1264_3_5_alternative_planning_integration_tests.py"
    if version in {"1264.6", "1264.7", "1264.8"}:
        return "tools/v1264_6_8_alternative_planning_reliability_tests.py"
    if version == "1264.9":
        return "tools/v1264_9_alternative_planning_checkpoint_tests.py"
    if version in {"1265.0", "1265.1", "1265.2"}:
        return "tools/v1265_0_2_isolated_self_modification_foundations_tests.py"
    if version in {"1265.3", "1265.4", "1265.5"}:
        return "tools/v1265_3_5_isolated_self_modification_integration_tests.py"
    if version in {"1265.6", "1265.7", "1265.8"}:
        return "tools/v1265_6_8_isolated_self_modification_reliability_tests.py"
    if version == "1265.9":
        return "tools/v1265_9_isolated_self_modification_checkpoint_tests.py"
    if version in {"1266.0", "1266.1", "1266.2"}:
        return "tools/v1266_0_2_intelligent_test_selection_foundations_tests.py"
    if version in {"1266.3", "1266.4", "1266.5"}:
        return "tools/v1266_3_5_intelligent_test_selection_integration_tests.py"
    if version in {"1266.6", "1266.7", "1266.8"}:
        return "tools/v1266_6_8_intelligent_test_selection_reliability_tests.py"
    if version == "1266.9":
        return "tools/v1266_9_intelligent_test_selection_checkpoint_tests.py"
    if version in {"1267.0", "1267.1", "1267.2"}:
        return "tools/v1267_0_2_iterative_self_repair_foundations_tests.py"
    if version in {"1267.3", "1267.4", "1267.5"}:
        return "tools/v1267_3_5_iterative_self_repair_integration_tests.py"
    if version in {"1267.6", "1267.7", "1267.8"}:
        return "tools/v1267_6_8_iterative_self_repair_reliability_tests.py"
    if version == "1267.9":
        return "tools/v1267_9_iterative_self_repair_checkpoint_tests.py"
    if version in {"1268.0", "1268.1", "1268.2"}:
        return "tools/v1268_0_2_operator_review_handoff_foundations_tests.py"
    if version in {"1268.3", "1268.4", "1268.5"}:
        return "tools/v1268_3_5_operator_review_handoff_integration_tests.py"
    if version in {"1268.6", "1268.7", "1268.8"}:
        return "tools/v1268_6_8_operator_review_handoff_reliability_tests.py"
    if version == "1268.9":
        return "tools/v1268_9_operator_review_handoff_checkpoint_tests.py"
    if version in {"1269.0", "1269.1", "1269.2"}:
        return "tools/v1269_0_2_governed_self_update_foundations_tests.py"
    if version in {"1269.3", "1269.4", "1269.5"}:
        return "tools/v1269_3_5_governed_self_update_integration_tests.py"
    if version in {"1269.6", "1269.7", "1269.8"}:
        return "tools/v1269_6_8_governed_self_update_reliability_tests.py"
    if version == "1269.9":
        return "tools/v1269_9_governed_self_update_checkpoint_tests.py"
    if version in {"1270.0", "1270.1", "1270.2"}:
        return "tools/v1270_0_2_self_development_alpha_foundations_tests.py"
    if version in {"1270.3", "1270.4", "1270.5"}:
        return "tools/v1270_3_5_self_development_alpha_integration_tests.py"
    if version in {"1270.6", "1270.7", "1270.8"}:
        return "tools/v1270_6_8_self_development_alpha_reliability_tests.py"
    if version == "1270.9":
        return "tools/v1270_9_self_development_alpha_checkpoint_tests.py"
    if version in {"1271.0", "1271.1", "1271.2"}:
        return "tools/v1271_0_2_long_running_work_sessions_foundations_tests.py"
    if version in {"1271.3", "1271.4", "1271.5"}:
        return "tools/v1271_3_5_long_running_work_sessions_integration_tests.py"
    if version in {"1271.6", "1271.7", "1271.8"}:
        return "tools/v1271_6_8_long_running_work_sessions_reliability_tests.py"
    if version == "1271.9":
        return "tools/v1271_9_long_running_work_sessions_checkpoint_tests.py"
    if version in {"1272.0", "1272.1", "1272.2"}:
        return "tools/v1272_0_2_restart_crash_recovery_foundations_tests.py"
    if version in {"1272.3", "1272.4", "1272.5"}:
        return "tools/v1272_3_5_restart_crash_recovery_integration_tests.py"
    if version in {"1272.6", "1272.7", "1272.8"}:
        return "tools/v1272_6_8_restart_crash_recovery_reliability_tests.py"
    if version == "1272.9":
        return "tools/v1272_9_restart_crash_recovery_checkpoint_tests.py"
    if version in {"1273.0", "1273.1", "1273.2"}:
        return "tools/v1273_0_2_ownership_concurrency_foundations_tests.py"
    if version in {"1273.3", "1273.4", "1273.5"}:
        return "tools/v1273_3_5_ownership_concurrency_integration_tests.py"
    if version in {"1273.6", "1273.7", "1273.8"}:
        return "tools/v1273_6_8_ownership_concurrency_reliability_tests.py"
    if version == "1273.9":
        return "tools/v1273_9_ownership_concurrency_checkpoint_tests.py"
    if version in {"1274.0", "1274.1", "1274.2"}:
        return "tools/v1274_0_2_environment_awareness_foundations_tests.py"
    if version in {"1274.3", "1274.4", "1274.5"}:
        return "tools/v1274_3_5_environment_awareness_integration_tests.py"
    if version in {"1274.6", "1274.7", "1274.8"}:
        return "tools/v1274_6_8_environment_awareness_reliability_tests.py"
    if version == "1274.9":
        return "tools/v1274_9_environment_awareness_checkpoint_tests.py"
    if version in {"1275.0", "1275.1", "1275.2"}:
        return "tools/v1275_0_2_dependency_packaging_foundations_tests.py"
    if version in {"1275.3", "1275.4", "1275.5"}:
        return "tools/v1275_3_5_dependency_packaging_integration_tests.py"
    if version in {"1275.6", "1275.7", "1275.8"}:
        return "tools/v1275_6_8_dependency_packaging_reliability_tests.py"
    if version == "1275.9":
        return "tools/v1275_9_dependency_packaging_checkpoint_tests.py"
    if version in {"1276.0", "1276.1", "1276.2"}:
        return "tools/v1276_0_2_architecture_boundary_foundations_tests.py"
    if version in {"1276.3", "1276.4", "1276.5"}:
        return "tools/v1276_3_5_architecture_boundary_integration_tests.py"
    if version in {"1276.6", "1276.7", "1276.8"}:
        return "tools/v1276_6_8_architecture_boundary_reliability_tests.py"
    if version == "1276.9":
        return "tools/v1276_9_architecture_boundary_checkpoint_tests.py"
    if version in {"1277.0", "1277.1", "1277.2"}:
        return "tools/v1277_0_2_development_observability_foundations_tests.py"
    if version in {"1277.3", "1277.4", "1277.5"}:
        return "tools/v1277_3_5_development_observability_integration_tests.py"
    if version in {"1277.6", "1277.7", "1277.8"}:
        return "tools/v1277_6_8_development_observability_reliability_tests.py"
    if version == "1277.9":
        return "tools/v1277_9_development_observability_checkpoint_tests.py"
    if version in {"1278.0", "1278.1", "1278.2"}:
        return "tools/v1278_0_2_security_privacy_hardening_foundations_tests.py"
    if version in {"1278.3", "1278.4", "1278.5"}:
        return "tools/v1278_3_5_security_privacy_hardening_integration_tests.py"
    if version in {"1278.6", "1278.7", "1278.8"}:
        return "tools/v1278_6_8_security_privacy_hardening_reliability_tests.py"
    if version == "1278.9":
        return "tools/v1278_9_security_privacy_hardening_checkpoint_tests.py"
    if version in {"1279.0", "1279.1", "1279.2"}:
        return "tools/v1279_0_2_operator_experience_foundations_tests.py"
    if version in {"1279.3", "1279.4", "1279.5"}:
        return "tools/v1279_3_5_operator_experience_integration_tests.py"
    if version in {"1279.6", "1279.7", "1279.8"}:
        return "tools/v1279_6_8_operator_experience_reliability_tests.py"
    if version == "1279.9":
        return "tools/v1279_9_operator_experience_checkpoint_tests.py"
    if version in {"1280.0", "1280.1", "1280.2"}:
        return "tools/v1280_0_2_reliability_checkpoint_foundations_tests.py"
    if version in {"1280.3", "1280.4", "1280.5"}:
        return "tools/v1280_3_5_reliability_checkpoint_integration_tests.py"
    if version in {"1280.6", "1280.7", "1280.8"}:
        return "tools/v1280_6_8_reliability_checkpoint_reliability_tests.py"
    if version == "1280.9":
        return "tools/v1280_9_reliability_checkpoint_tests.py"
    if version in {"1281.0", "1281.1", "1281.2"}:
        return "tools/v1281_0_2_causal_diagnostic_reasoning_foundations_tests.py"
    if version in {"1281.3", "1281.4", "1281.5"}:
        return "tools/v1281_3_5_causal_diagnostic_reasoning_integration_tests.py"
    if version in {"1281.6", "1281.7", "1281.8"}:
        return "tools/v1281_6_8_causal_diagnostic_reasoning_reliability_tests.py"
    if version == "1281.9":
        return "tools/v1281_9_causal_diagnostic_reasoning_checkpoint_tests.py"
    if version in {"1282.0", "1282.1", "1282.2"}:
        return "tools/v1282_0_2_calibrated_uncertainty_foundations_tests.py"
    if version in {"1282.3", "1282.4", "1282.5"}:
        return "tools/v1282_3_5_calibrated_uncertainty_integration_tests.py"
    if version in {"1282.6", "1282.7", "1282.8"}:
        return "tools/v1282_6_8_calibrated_uncertainty_reliability_tests.py"
    if version == "1282.9":
        return "tools/v1282_9_calibrated_uncertainty_checkpoint_tests.py"
    if version in {"1283.0", "1283.1", "1283.2"}:
        return "tools/v1283_0_2_development_memory_relevance_foundations_tests.py"
    if version in {"1283.3", "1283.4", "1283.5"}:
        return "tools/v1283_3_5_development_memory_relevance_integration_tests.py"
    if version in {"1283.6", "1283.7", "1283.8"}:
        return "tools/v1283_6_8_development_memory_relevance_reliability_tests.py"
    if version == "1283.9":
        return "tools/v1283_9_development_memory_relevance_checkpoint_tests.py"
    if version in {"1284.0", "1284.1", "1284.2"}:
        return "tools/v1284_0_2_experiential_learning_foundations_tests.py"
    if version in {"1284.3", "1284.4", "1284.5"}:
        return "tools/v1284_3_5_experiential_learning_integration_tests.py"
    if version in {"1284.6", "1284.7", "1284.8"}:
        return "tools/v1284_6_8_experiential_learning_reliability_tests.py"
    if version == "1284.9":
        return "tools/v1284_9_experiential_learning_checkpoint_tests.py"
    if version in {"1285.0", "1285.1", "1285.2"}:
        return "tools/v1285_0_2_hierarchical_goal_management_foundations_tests.py"
    if version in {"1285.3", "1285.4", "1285.5"}:
        return "tools/v1285_3_5_hierarchical_goal_management_integration_tests.py"
    if version in {"1285.6", "1285.7", "1285.8"}:
        return "tools/v1285_6_8_hierarchical_goal_management_reliability_tests.py"
    if version == "1285.9":
        return "tools/v1285_9_hierarchical_goal_management_checkpoint_tests.py"
    if version in {"1286.0", "1286.1", "1286.2"}:
        return "tools/v1286_0_2_dynamic_replanning_foundations_tests.py"
    if version in {"1286.3", "1286.4", "1286.5"}:
        return "tools/v1286_3_5_dynamic_replanning_integration_tests.py"
    if version in {"1286.6", "1286.7", "1286.8"}:
        return "tools/v1286_6_8_dynamic_replanning_reliability_tests.py"
    if version == "1286.9":
        return "tools/v1286_9_dynamic_replanning_checkpoint_tests.py"
    if version in {"1287.0", "1287.1", "1287.2"}:
        return "tools/v1287_0_2_unified_conversation_action_foundations_tests.py"
    if version in {"1287.3", "1287.4", "1287.5"}:
        return "tools/v1287_3_5_unified_conversation_action_integration_tests.py"
    if version in {"1287.6", "1287.7", "1287.8"}:
        return "tools/v1287_6_8_unified_conversation_action_reliability_tests.py"
    if version == "1287.9":
        return "tools/v1287_9_unified_conversation_action_checkpoint_tests.py"
    if version in {"1288.0", "1288.1", "1288.2"}:
        return "tools/v1288_0_2_provider_aware_performance_foundations_tests.py"
    if version in {"1288.3", "1288.4", "1288.5"}:
        return "tools/v1288_3_5_provider_aware_performance_integration_tests.py"
    if version in {"1288.6", "1288.7", "1288.8"}:
        return "tools/v1288_6_8_provider_aware_performance_reliability_tests.py"
    if version == "1288.9":
        return "tools/v1288_9_provider_aware_performance_checkpoint_tests.py"
    if version in {"1289.0", "1289.1", "1289.2"}:
        return "tools/v1289_0_2_product_quality_judgment_foundations_tests.py"
    if version in {"1289.3", "1289.4", "1289.5"}:
        return "tools/v1289_3_5_product_quality_judgment_integration_tests.py"
    if version in {"1289.6", "1289.7", "1289.8"}:
        return "tools/v1289_6_8_product_quality_judgment_reliability_tests.py"
    if version == "1289.9":
        return "tools/v1289_9_product_quality_judgment_checkpoint_tests.py"
    if version in {"1290.0", "1290.1", "1290.2"}:
        return "tools/v1290_0_2_cognitive_coding_foundations_tests.py"
    if version in {"1290.3", "1290.4", "1290.5"}:
        return "tools/v1290_3_5_cognitive_coding_integration_tests.py"
    if version in {"1290.6", "1290.7", "1290.8"}:
        return "tools/v1290_6_8_cognitive_coding_reliability_tests.py"
    if version == "1290.9":
        return "tools/v1290_9_cognitive_coding_checkpoint_tests.py"
    if version in {"1291.0", "1291.1", "1291.2"}:
        return "tools/v1291_0_2_independent_improvement_proposals_foundations_tests.py"
    if version in {"1291.3", "1291.4", "1291.5"}:
        return "tools/v1291_3_5_independent_improvement_proposals_integration_tests.py"
    if version in {"1291.6", "1291.7", "1291.8"}:
        return "tools/v1291_6_8_independent_improvement_proposals_reliability_tests.py"
    if version == "1291.9":
        return "tools/v1291_9_independent_improvement_proposals_checkpoint_tests.py"
    if version in {"1292.0", "1292.1", "1292.2"}:
        return "tools/v1292_0_2_value_risk_deliberation_foundations_tests.py"
    if version in {"1292.3", "1292.4", "1292.5"}:
        return "tools/v1292_3_5_value_risk_deliberation_integration_tests.py"
    if version in {"1292.6", "1292.7", "1292.8"}:
        return "tools/v1292_6_8_value_risk_deliberation_reliability_tests.py"
    if version == "1292.9":
        return "tools/v1292_9_value_risk_deliberation_checkpoint_tests.py"
    if version in {"1293.0", "1293.1", "1293.2"}:
        return "tools/v1293_0_2_bounded_development_campaigns_foundations_tests.py"
    if version in {"1293.3", "1293.4", "1293.5"}:
        return "tools/v1293_3_5_bounded_development_campaigns_integration_tests.py"
    if version in {"1293.6", "1293.7", "1293.8"}:
        return "tools/v1293_6_8_bounded_development_campaigns_reliability_tests.py"
    if version == "1293.9":
        return "tools/v1293_9_bounded_development_campaigns_checkpoint_tests.py"
    if version in {"1294.0", "1294.1", "1294.2"}:
        return "tools/v1294_0_2_competing_candidate_evaluation_foundations_tests.py"
    if version in {"1294.3", "1294.4", "1294.5"}:
        return "tools/v1294_3_5_competing_candidate_evaluation_integration_tests.py"
    if version in {"1294.6", "1294.7", "1294.8"}:
        return "tools/v1294_6_8_competing_candidate_evaluation_reliability_tests.py"
    if version == "1294.9":
        return "tools/v1294_9_competing_candidate_evaluation_checkpoint_tests.py"
    if version in {"1295.0", "1295.1", "1295.2"}:
        return "tools/v1295_0_2_comprehensive_verification_foundations_tests.py"
    if version in {"1295.3", "1295.4", "1295.5"}:
        return "tools/v1295_3_5_comprehensive_verification_integration_tests.py"
    if version in {"1295.6", "1295.7", "1295.8"}:
        return "tools/v1295_6_8_comprehensive_verification_reliability_tests.py"
    if version == "1295.9":
        return "tools/v1295_9_comprehensive_verification_checkpoint_tests.py"
    if version in {"1296.0", "1296.1", "1296.2"}:
        return "tools/v1296_0_2_canary_self_updates_foundations_tests.py"
    if version in {"1296.3", "1296.4", "1296.5"}:
        return "tools/v1296_3_5_canary_self_updates_integration_tests.py"
    if version in {"1296.6", "1296.7", "1296.8"}:
        return "tools/v1296_6_8_canary_self_updates_reliability_tests.py"
    if version == "1296.9":
        return "tools/v1296_9_canary_self_updates_checkpoint_tests.py"
    if version in {"1297.0", "1297.1", "1297.2"}:
        return "tools/v1297_0_2_automated_recovery_foundations_tests.py"
    if version in {"1297.3", "1297.4", "1297.5"}:
        return "tools/v1297_3_5_automated_recovery_integration_tests.py"
    if version in {"1297.6", "1297.7", "1297.8"}:
        return "tools/v1297_6_8_automated_recovery_reliability_tests.py"
    if version == "1297.9":
        return "tools/v1297_9_automated_recovery_checkpoint_tests.py"
    if version in {"1298.0", "1298.1", "1298.2"}:
        return "tools/v1298_0_2_repeated_self_maintenance_foundations_tests.py"
    if version in {"1298.3", "1298.4", "1298.5"}:
        return "tools/v1298_3_5_repeated_self_maintenance_integration_tests.py"
    if version in {"1298.6", "1298.7", "1298.8"}:
        return "tools/v1298_6_8_repeated_self_maintenance_reliability_tests.py"
    if version == "1298.9":
        return "tools/v1298_9_repeated_self_maintenance_checkpoint_tests.py"
    if version in {"1299.0", "1299.1", "1299.2"}:
        return "tools/v1299_0_2_supervised_autonomy_rehearsal_foundations_tests.py"
    if version in {"1299.3", "1299.4", "1299.5"}:
        return "tools/v1299_3_5_supervised_autonomy_rehearsal_integration_tests.py"
    if version in {"1299.6", "1299.7", "1299.8"}:
        return "tools/v1299_6_8_supervised_autonomy_rehearsal_reliability_tests.py"
    if version == "1299.9":
        return "tools/v1299_9_supervised_autonomy_rehearsal_checkpoint_tests.py"
    if version in {"1300.0", "1300.1", "1300.2"}:
        return "tools/v1300_0_2_supervised_self_development_beta_foundations_tests.py"
    if version in {"1300.3", "1300.4", "1300.5"}:
        return "tools/v1300_3_5_supervised_self_development_beta_integration_tests.py"
    if version in {"1300.6", "1300.7", "1300.8"}:
        return "tools/v1300_6_8_supervised_self_development_beta_reliability_tests.py"
    if version == "1300.9":
        return "tools/v1300_9_supervised_self_development_beta_checkpoint_tests.py"
    if version.startswith("1301."):
        minor = int(version.split(".")[1])
        return "tools/v1301_0_2_authority_profiles_foundations_tests.py" if minor <= 2 else ("tools/v1301_3_5_authority_profiles_integration_tests.py" if minor <= 5 else ("tools/v1301_6_8_authority_profiles_reliability_tests.py" if minor <= 8 else "tools/v1301_9_authority_profiles_checkpoint_tests.py"))
    if version.startswith("1302."):
        minor = int(version.split(".")[1])
        return "tools/v1302_0_2_standing_session_grants_foundations_tests.py" if minor <= 2 else ("tools/v1302_3_5_standing_session_grants_integration_tests.py" if minor <= 5 else ("tools/v1302_6_8_standing_session_grants_reliability_tests.py" if minor <= 8 else "tools/v1302_9_standing_session_grants_checkpoint_tests.py"))
    if version.startswith("1303."):
        minor = int(version.split(".")[1])
        return "tools/v1303_0_2_goal_representation_foundations_tests.py" if minor <= 2 else ("tools/v1303_3_5_goal_representation_integration_tests.py" if minor <= 5 else ("tools/v1303_6_8_goal_representation_reliability_tests.py" if minor <= 8 else "tools/v1303_9_goal_representation_checkpoint_tests.py"))
    if version.startswith("1304."):
        minor = int(version.split(".")[1])
        return "tools/v1304_0_2_goal_intake_foundations_tests.py" if minor <= 2 else ("tools/v1304_3_5_goal_intake_integration_tests.py" if minor <= 5 else ("tools/v1304_6_8_goal_intake_reliability_tests.py" if minor <= 8 else "tools/v1304_9_goal_intake_checkpoint_tests.py"))
    if version.startswith("1305."):
        minor = int(version.split(".")[1])
        return "tools/v1305_0_2_goal_clarification_foundations_tests.py" if minor <= 2 else ("tools/v1305_3_5_goal_clarification_integration_tests.py" if minor <= 5 else ("tools/v1305_6_8_goal_clarification_reliability_tests.py" if minor <= 8 else "tools/v1305_9_goal_clarification_checkpoint_tests.py"))
    if version.startswith("1306."):
        minor = int(version.split(".")[1])
        return "tools/v1306_0_2_goal_decomposition_foundations_tests.py" if minor <= 2 else ("tools/v1306_3_5_goal_decomposition_integration_tests.py" if minor <= 5 else ("tools/v1306_6_8_goal_decomposition_reliability_tests.py" if minor <= 8 else "tools/v1306_9_goal_decomposition_checkpoint_tests.py"))
    if version.startswith("1307."):
        minor = int(version.split(".")[1])
        return "tools/v1307_0_2_goal_conflicts_foundations_tests.py" if minor <= 2 else ("tools/v1307_3_5_goal_conflicts_integration_tests.py" if minor <= 5 else ("tools/v1307_6_8_goal_conflicts_reliability_tests.py" if minor <= 8 else "tools/v1307_9_goal_conflicts_checkpoint_tests.py"))
    if version.startswith("1308."):
        minor = int(version.split(".")[1])
        return "tools/v1308_0_2_session_budgets_foundations_tests.py" if minor <= 2 else ("tools/v1308_3_5_session_budgets_integration_tests.py" if minor <= 5 else ("tools/v1308_6_8_session_budgets_reliability_tests.py" if minor <= 8 else "tools/v1308_9_session_budgets_checkpoint_tests.py"))
    if version.startswith("1309."):
        minor = int(version.split(".")[1])
        return "tools/v1309_0_2_goal_lifecycle_foundations_tests.py" if minor <= 2 else ("tools/v1309_3_5_goal_lifecycle_integration_tests.py" if minor <= 5 else ("tools/v1309_6_8_goal_lifecycle_reliability_tests.py" if minor <= 8 else "tools/v1309_9_goal_lifecycle_checkpoint_tests.py"))
    if version.startswith("1310."):
        minor = int(version.split(".")[1])
        return "tools/v1310_0_2_autonomy_contract_foundations_tests.py" if minor <= 2 else ("tools/v1310_3_5_autonomy_contract_integration_tests.py" if minor <= 5 else ("tools/v1310_6_8_autonomy_contract_reliability_tests.py" if minor <= 8 else "tools/v1310_9_autonomy_contract_checkpoint_tests.py"))
    if version.startswith("1311."):
        minor = int(version.split(".")[1])
        return "tools/v1311_0_2_repository_inventory_foundations_tests.py" if minor <= 2 else ("tools/v1311_3_5_repository_inventory_integration_tests.py" if minor <= 5 else ("tools/v1311_6_8_repository_inventory_reliability_tests.py" if minor <= 8 else "tools/v1311_9_repository_inventory_checkpoint_tests.py"))
    if version.startswith("1312."):
        minor = int(version.split(".")[1])
        return "tools/v1312_0_2_symbol_graph_foundations_tests.py" if minor <= 2 else ("tools/v1312_3_5_symbol_graph_integration_tests.py" if minor <= 5 else ("tools/v1312_6_8_symbol_graph_reliability_tests.py" if minor <= 8 else "tools/v1312_9_symbol_graph_checkpoint_tests.py"))
    if version.startswith("1313."):
        minor = int(version.split(".")[1])
        return "tools/v1313_0_2_dependency_graph_foundations_tests.py" if minor <= 2 else ("tools/v1313_3_5_dependency_graph_integration_tests.py" if minor <= 5 else ("tools/v1313_6_8_dependency_graph_reliability_tests.py" if minor <= 8 else "tools/v1313_9_dependency_graph_checkpoint_tests.py"))
    if version.startswith("1314."):
        minor = int(version.split(".")[1])
        return "tools/v1314_0_2_runtime_topology_foundations_tests.py" if minor <= 2 else ("tools/v1314_3_5_runtime_topology_integration_tests.py" if minor <= 5 else ("tools/v1314_6_8_runtime_topology_reliability_tests.py" if minor <= 8 else "tools/v1314_9_runtime_topology_checkpoint_tests.py"))
    if version.startswith("1315."):
        minor = int(version.split(".")[1])
        return "tools/v1315_0_2_behavioral_map_foundations_tests.py" if minor <= 2 else ("tools/v1315_3_5_behavioral_map_integration_tests.py" if minor <= 5 else ("tools/v1315_6_8_behavioral_map_reliability_tests.py" if minor <= 8 else "tools/v1315_9_behavioral_map_checkpoint_tests.py"))
    if version.startswith("1316."):
        minor = int(version.split(".")[1])
        return "tools/v1316_0_2_architecture_summaries_foundations_tests.py" if minor <= 2 else ("tools/v1316_3_5_architecture_summaries_integration_tests.py" if minor <= 5 else ("tools/v1316_6_8_architecture_summaries_reliability_tests.py" if minor <= 8 else "tools/v1316_9_architecture_summaries_checkpoint_tests.py"))
    if version.startswith("1317."):
        minor = int(version.split(".")[1])
        return "tools/v1317_0_2_change_history_understanding_foundations_tests.py" if minor <= 2 else ("tools/v1317_3_5_change_history_understanding_integration_tests.py" if minor <= 5 else ("tools/v1317_6_8_change_history_understanding_reliability_tests.py" if minor <= 8 else "tools/v1317_9_change_history_understanding_checkpoint_tests.py"))
    if version.startswith("1318."):
        minor = int(version.split(".")[1])
        return "tools/v1318_0_2_impact_analysis_foundations_tests.py" if minor <= 2 else ("tools/v1318_3_5_impact_analysis_integration_tests.py" if minor <= 5 else ("tools/v1318_6_8_impact_analysis_reliability_tests.py" if minor <= 8 else "tools/v1318_9_impact_analysis_checkpoint_tests.py"))
    if version.startswith("1319."):
        minor = int(version.split(".")[1])
        return "tools/v1319_0_2_project_unknown_detection_foundations_tests.py" if minor <= 2 else ("tools/v1319_3_5_project_unknown_detection_integration_tests.py" if minor <= 5 else ("tools/v1319_6_8_project_unknown_detection_reliability_tests.py" if minor <= 8 else "tools/v1319_9_project_unknown_detection_checkpoint_tests.py"))
    if version.startswith("1320."):
        minor = int(version.split(".")[1])
        return "tools/v1320_0_2_project_understanding_checkpoint_foundations_tests.py" if minor <= 2 else ("tools/v1320_3_5_project_understanding_checkpoint_integration_tests.py" if minor <= 5 else ("tools/v1320_6_8_project_understanding_checkpoint_reliability_tests.py" if minor <= 8 else "tools/v1320_9_project_understanding_checkpoint_tests.py"))
    if version.startswith("1321."):
        minor = int(version.split(".")[1])
        return "tools/v1321_0_2_candidate_approaches_foundations_tests.py" if minor <= 2 else ("tools/v1321_3_5_candidate_approaches_integration_tests.py" if minor <= 5 else ("tools/v1321_6_8_candidate_approaches_reliability_tests.py" if minor <= 8 else "tools/v1321_9_candidate_approaches_checkpoint_tests.py"))
    if version.startswith("1322."):
        minor = int(version.split(".")[1])
        return "tools/v1322_0_2_tradeoff_evaluation_foundations_tests.py" if minor <= 2 else ("tools/v1322_3_5_tradeoff_evaluation_integration_tests.py" if minor <= 5 else ("tools/v1322_6_8_tradeoff_evaluation_reliability_tests.py" if minor <= 8 else "tools/v1322_9_tradeoff_evaluation_checkpoint_tests.py"))
    if version.startswith("1323."):
        minor = int(version.split(".")[1])
        return "tools/v1323_0_2_assumption_ledger_foundations_tests.py" if minor <= 2 else ("tools/v1323_3_5_assumption_ledger_integration_tests.py" if minor <= 5 else ("tools/v1323_6_8_assumption_ledger_reliability_tests.py" if minor <= 8 else "tools/v1323_9_assumption_ledger_checkpoint_tests.py"))
    if version.startswith("1324."):
        minor = int(version.split(".")[1])
        return "tools/v1324_0_2_plan_construction_foundations_tests.py" if minor <= 2 else ("tools/v1324_3_5_plan_construction_integration_tests.py" if minor <= 5 else ("tools/v1324_6_8_plan_construction_reliability_tests.py" if minor <= 8 else "tools/v1324_9_plan_construction_checkpoint_tests.py"))
    if version.startswith("1325."):
        minor = int(version.split(".")[1])
        return "tools/v1325_0_2_plan_critique_foundations_tests.py" if minor <= 2 else ("tools/v1325_3_5_plan_critique_integration_tests.py" if minor <= 5 else ("tools/v1325_6_8_plan_critique_reliability_tests.py" if minor <= 8 else "tools/v1325_9_plan_critique_checkpoint_tests.py"))
    if version.startswith("1326."):
        minor = int(version.split(".")[1])
        return "tools/v1326_0_2_risk_sensitive_planning_foundations_tests.py" if minor <= 2 else ("tools/v1326_3_5_risk_sensitive_planning_integration_tests.py" if minor <= 5 else ("tools/v1326_6_8_risk_sensitive_planning_reliability_tests.py" if minor <= 8 else "tools/v1326_9_risk_sensitive_planning_checkpoint_tests.py"))
    if version.startswith("1327."):
        minor = int(version.split(".")[1])
        return "tools/v1327_0_2_dynamic_replanning_foundations_tests.py" if minor <= 2 else ("tools/v1327_3_5_dynamic_replanning_integration_tests.py" if minor <= 5 else ("tools/v1327_6_8_dynamic_replanning_reliability_tests.py" if minor <= 8 else "tools/v1327_9_dynamic_replanning_checkpoint_tests.py"))
    if version.startswith("1328."):
        minor = int(version.split(".")[1])
        return "tools/v1328_0_2_stop_escalation_foundations_tests.py" if minor <= 2 else ("tools/v1328_3_5_stop_escalation_integration_tests.py" if minor <= 5 else ("tools/v1328_6_8_stop_escalation_reliability_tests.py" if minor <= 8 else "tools/v1328_9_stop_escalation_checkpoint_tests.py"))
    if version.startswith("1329."):
        minor = int(version.split(".")[1])
        return "tools/v1329_0_2_plan_quality_scoring_foundations_tests.py" if minor <= 2 else ("tools/v1329_3_5_plan_quality_scoring_integration_tests.py" if minor <= 5 else ("tools/v1329_6_8_plan_quality_scoring_reliability_tests.py" if minor <= 8 else "tools/v1329_9_plan_quality_scoring_checkpoint_tests.py"))
    if version.startswith("1330."):
        minor = int(version.split(".")[1])
        return "tools/v1330_0_2_deliberative_planning_checkpoint_foundations_tests.py" if minor <= 2 else ("tools/v1330_3_5_deliberative_planning_checkpoint_integration_tests.py" if minor <= 5 else ("tools/v1330_6_8_deliberative_planning_checkpoint_reliability_tests.py" if minor <= 8 else "tools/v1330_9_deliberative_planning_checkpoint_tests.py"))
    if version.startswith("1331."):
        minor = int(version.split(".")[1])
        return "tools/v1331_0_2_tool_capability_registry_foundations_tests.py" if minor <= 2 else ("tools/v1331_3_5_tool_capability_registry_integration_tests.py" if minor <= 5 else ("tools/v1331_6_8_tool_capability_registry_reliability_tests.py" if minor <= 8 else "tools/v1331_9_tool_capability_registry_checkpoint_tests.py"))
    if version.startswith("1332."):
        minor = int(version.split(".")[1])
        return "tools/v1332_0_2_tool_preconditions_foundations_tests.py" if minor <= 2 else ("tools/v1332_3_5_tool_preconditions_integration_tests.py" if minor <= 5 else ("tools/v1332_6_8_tool_preconditions_reliability_tests.py" if minor <= 8 else "tools/v1332_9_tool_preconditions_checkpoint_tests.py"))
    if version.startswith("1333."):
        minor = int(version.split(".")[1])
        return "tools/v1333_0_2_workspace_isolation_foundations_tests.py" if minor <= 2 else ("tools/v1333_3_5_workspace_isolation_integration_tests.py" if minor <= 5 else ("tools/v1333_6_8_workspace_isolation_reliability_tests.py" if minor <= 8 else "tools/v1333_9_workspace_isolation_checkpoint_tests.py"))
    if version.startswith("1334."):
        minor = int(version.split(".")[1])
        return "tools/v1334_0_2_file_operations_foundations_tests.py" if minor <= 2 else ("tools/v1334_3_5_file_operations_integration_tests.py" if minor <= 5 else ("tools/v1334_6_8_file_operations_reliability_tests.py" if minor <= 8 else "tools/v1334_9_file_operations_checkpoint_tests.py"))
    if version.startswith("1335."):
        minor = int(version.split(".")[1])
        return "tools/v1335_0_2_git_operations_foundations_tests.py" if minor <= 2 else ("tools/v1335_3_5_git_operations_integration_tests.py" if minor <= 5 else ("tools/v1335_6_8_git_operations_reliability_tests.py" if minor <= 8 else "tools/v1335_9_git_operations_checkpoint_tests.py"))
    if version.startswith("1336."):
        minor = int(version.split(".")[1])
        return "tools/v1336_0_2_process_operations_foundations_tests.py" if minor <= 2 else ("tools/v1336_3_5_process_operations_integration_tests.py" if minor <= 5 else ("tools/v1336_6_8_process_operations_reliability_tests.py" if minor <= 8 else "tools/v1336_9_process_operations_checkpoint_tests.py"))
    if version.startswith("1337."):
        minor = int(version.split(".")[1])
        return "tools/v1337_0_2_browser_validation_foundations_tests.py" if minor <= 2 else ("tools/v1337_3_5_browser_validation_integration_tests.py" if minor <= 5 else ("tools/v1337_6_8_browser_validation_reliability_tests.py" if minor <= 8 else "tools/v1337_9_browser_validation_checkpoint_tests.py"))
    if version.startswith("1338."):
        minor = int(version.split(".")[1])
        return "tools/v1338_0_2_service_orchestration_foundations_tests.py" if minor <= 2 else ("tools/v1338_3_5_service_orchestration_integration_tests.py" if minor <= 5 else ("tools/v1338_6_8_service_orchestration_reliability_tests.py" if minor <= 8 else "tools/v1338_9_service_orchestration_checkpoint_tests.py"))
    if version.startswith("1339."):
        minor = int(version.split(".")[1])
        return "tools/v1339_0_2_tool_result_reconciliation_foundations_tests.py" if minor <= 2 else ("tools/v1339_3_5_tool_result_reconciliation_integration_tests.py" if minor <= 5 else ("tools/v1339_6_8_tool_result_reconciliation_reliability_tests.py" if minor <= 8 else "tools/v1339_9_tool_result_reconciliation_checkpoint_tests.py"))
    if version.startswith("1340."):
        minor = int(version.split(".")[1])
        return "tools/v1340_0_2_multi_tool_execution_foundations_tests.py" if minor <= 2 else ("tools/v1340_3_5_multi_tool_execution_integration_tests.py" if minor <= 5 else ("tools/v1340_6_8_multi_tool_execution_reliability_tests.py" if minor <= 8 else "tools/v1340_9_multi_tool_execution_checkpoint_tests.py"))
    if version.startswith("1341."):
        minor = int(version.split(".")[1])
        return "tools/v1341_0_2_python_implementation_foundations_tests.py" if minor <= 2 else ("tools/v1341_3_5_python_implementation_integration_tests.py" if minor <= 5 else ("tools/v1341_6_8_python_implementation_reliability_tests.py" if minor <= 8 else "tools/v1341_9_python_implementation_checkpoint_tests.py"))
    if version.startswith("1342."):
        minor = int(version.split(".")[1])
        return "tools/v1342_0_2_javascript_typescript_foundations_tests.py" if minor <= 2 else ("tools/v1342_3_5_javascript_typescript_integration_tests.py" if minor <= 5 else ("tools/v1342_6_8_javascript_typescript_reliability_tests.py" if minor <= 8 else "tools/v1342_9_javascript_typescript_checkpoint_tests.py"))
    if version.startswith("1343."):
        minor = int(version.split(".")[1])
        return "tools/v1343_0_2_html_css_foundations_tests.py" if minor <= 2 else ("tools/v1343_3_5_html_css_integration_tests.py" if minor <= 5 else ("tools/v1343_6_8_html_css_reliability_tests.py" if minor <= 8 else "tools/v1343_9_html_css_checkpoint_tests.py"))
    if version.startswith("1344."):
        minor = int(version.split(".")[1])
        return "tools/v1344_0_2_data_schema_foundations_tests.py" if minor <= 2 else ("tools/v1344_3_5_data_schema_integration_tests.py" if minor <= 5 else ("tools/v1344_6_8_data_schema_reliability_tests.py" if minor <= 8 else "tools/v1344_9_data_schema_checkpoint_tests.py"))
    if version.startswith("1345."):
        minor = int(version.split(".")[1])
        return "tools/v1345_0_2_windows_automation_foundations_tests.py" if minor <= 2 else ("tools/v1345_3_5_windows_automation_integration_tests.py" if minor <= 5 else ("tools/v1345_6_8_windows_automation_reliability_tests.py" if minor <= 8 else "tools/v1345_9_windows_automation_checkpoint_tests.py"))
    if version.startswith("1346."):
        minor = int(version.split(".")[1])
        return "tools/v1346_0_2_cross_platform_foundations_tests.py" if minor <= 2 else ("tools/v1346_3_5_cross_platform_integration_tests.py" if minor <= 5 else ("tools/v1346_6_8_cross_platform_reliability_tests.py" if minor <= 8 else "tools/v1346_9_cross_platform_checkpoint_tests.py"))
    if version.startswith("1347."):
        minor = int(version.split(".")[1])
        return "tools/v1347_0_2_framework_adaptation_foundations_tests.py" if minor <= 2 else ("tools/v1347_3_5_framework_adaptation_integration_tests.py" if minor <= 5 else ("tools/v1347_6_8_framework_adaptation_reliability_tests.py" if minor <= 8 else "tools/v1347_9_framework_adaptation_checkpoint_tests.py"))
    if version.startswith("1348."):
        minor = int(version.split(".")[1])
        return "tools/v1348_0_2_dependency_selection_foundations_tests.py" if minor <= 2 else ("tools/v1348_3_5_dependency_selection_integration_tests.py" if minor <= 5 else ("tools/v1348_6_8_dependency_selection_reliability_tests.py" if minor <= 8 else "tools/v1348_9_dependency_selection_checkpoint_tests.py"))
    if version.startswith("1349."):
        minor = int(version.split(".")[1])
        return "tools/v1349_0_2_cross_language_foundations_tests.py" if minor <= 2 else ("tools/v1349_3_5_cross_language_integration_tests.py" if minor <= 5 else ("tools/v1349_6_8_cross_language_reliability_tests.py" if minor <= 8 else "tools/v1349_9_cross_language_checkpoint_tests.py"))
    if version.startswith("1350."):
        minor = int(version.split(".")[1])
        return "tools/v1350_0_2_implementation_skill_foundations_tests.py" if minor <= 2 else ("tools/v1350_3_5_implementation_skill_integration_tests.py" if minor <= 5 else ("tools/v1350_6_8_implementation_skill_reliability_tests.py" if minor <= 8 else "tools/v1350_9_implementation_skill_checkpoint_tests.py"))
    if version.startswith("1351."):
        minor = int(version.split(".")[1])
        return "tools/v1351_0_2_acceptance_traceability_foundations_tests.py" if minor <= 2 else ("tools/v1351_3_5_acceptance_traceability_integration_tests.py" if minor <= 5 else ("tools/v1351_6_8_acceptance_traceability_reliability_tests.py" if minor <= 8 else "tools/v1351_9_acceptance_traceability_checkpoint_tests.py"))
    if version.startswith("1352."):
        minor = int(version.split(".")[1])
        return "tools/v1352_0_2_verification_test_selection_foundations_tests.py" if minor <= 2 else ("tools/v1352_3_5_verification_test_selection_integration_tests.py" if minor <= 5 else ("tools/v1352_6_8_verification_test_selection_reliability_tests.py" if minor <= 8 else "tools/v1352_9_verification_test_selection_checkpoint_tests.py"))
    if version.startswith("1353."):
        minor = int(version.split(".")[1])
        return "tools/v1353_0_2_unit_contract_tests_foundations_tests.py" if minor <= 2 else ("tools/v1353_3_5_unit_contract_tests_integration_tests.py" if minor <= 5 else ("tools/v1353_6_8_unit_contract_tests_reliability_tests.py" if minor <= 8 else "tools/v1353_9_unit_contract_tests_checkpoint_tests.py"))
    if version.startswith("1354."):
        minor = int(version.split(".")[1])
        return "tools/v1354_0_2_integration_tests_foundations_tests.py" if minor <= 2 else ("tools/v1354_3_5_integration_tests_integration_tests.py" if minor <= 5 else ("tools/v1354_6_8_integration_tests_reliability_tests.py" if minor <= 8 else "tools/v1354_9_integration_tests_checkpoint_tests.py"))
    if version.startswith("1355."):
        minor = int(version.split(".")[1])
        return "tools/v1355_0_2_property_fuzz_tests_foundations_tests.py" if minor <= 2 else ("tools/v1355_3_5_property_fuzz_tests_integration_tests.py" if minor <= 5 else ("tools/v1355_6_8_property_fuzz_tests_reliability_tests.py" if minor <= 8 else "tools/v1355_9_property_fuzz_tests_checkpoint_tests.py"))
    if version.startswith("1356."):
        minor = int(version.split(".")[1])
        return "tools/v1356_0_2_ui_accessibility_tests_foundations_tests.py" if minor <= 2 else ("tools/v1356_3_5_ui_accessibility_tests_integration_tests.py" if minor <= 5 else ("tools/v1356_6_8_ui_accessibility_tests_reliability_tests.py" if minor <= 8 else "tools/v1356_9_ui_accessibility_tests_checkpoint_tests.py"))
    if version.startswith("1357."):
        minor = int(version.split(".")[1])
        return "tools/v1357_0_2_performance_verification_foundations_tests.py" if minor <= 2 else ("tools/v1357_3_5_performance_verification_integration_tests.py" if minor <= 5 else ("tools/v1357_6_8_performance_verification_reliability_tests.py" if minor <= 8 else "tools/v1357_9_performance_verification_checkpoint_tests.py"))
    if version.startswith("1358."):
        minor = int(version.split(".")[1])
        return "tools/v1358_0_2_security_verification_foundations_tests.py" if minor <= 2 else ("tools/v1358_3_5_security_verification_integration_tests.py" if minor <= 5 else ("tools/v1358_6_8_security_verification_reliability_tests.py" if minor <= 8 else "tools/v1358_9_security_verification_checkpoint_tests.py"))
    if version.startswith("1359."):
        minor = int(version.split(".")[1])
        return "tools/v1359_0_2_evidence_quality_foundations_tests.py" if minor <= 2 else ("tools/v1359_3_5_evidence_quality_integration_tests.py" if minor <= 5 else ("tools/v1359_6_8_evidence_quality_reliability_tests.py" if minor <= 8 else "tools/v1359_9_evidence_quality_checkpoint_tests.py"))
    if version.startswith("1360."):
        minor = int(version.split(".")[1])
        return "tools/v1360_0_2_verification_intelligence_foundations_tests.py" if minor <= 2 else ("tools/v1360_3_5_verification_intelligence_integration_tests.py" if minor <= 5 else ("tools/v1360_6_8_verification_intelligence_reliability_tests.py" if minor <= 8 else "tools/v1360_9_verification_intelligence_checkpoint_tests.py"))
    if version.startswith("1361."):
        minor = int(version.split(".")[1])
        return "tools/v1361_0_2_reproduction_builder_foundations_tests.py" if minor <= 2 else ("tools/v1361_3_5_reproduction_builder_integration_tests.py" if minor <= 5 else ("tools/v1361_6_8_reproduction_builder_reliability_tests.py" if minor <= 8 else "tools/v1361_9_reproduction_builder_checkpoint_tests.py"))
    if version.startswith("1362."):
        minor = int(version.split(".")[1])
        return "tools/v1362_0_2_fault_localization_foundations_tests.py" if minor <= 2 else ("tools/v1362_3_5_fault_localization_integration_tests.py" if minor <= 5 else ("tools/v1362_6_8_fault_localization_reliability_tests.py" if minor <= 8 else "tools/v1362_9_fault_localization_checkpoint_tests.py"))
    if version.startswith("1363."):
        minor = int(version.split(".")[1])
        return "tools/v1363_0_2_root_cause_analysis_foundations_tests.py" if minor <= 2 else ("tools/v1363_3_5_root_cause_analysis_integration_tests.py" if minor <= 5 else ("tools/v1363_6_8_root_cause_analysis_reliability_tests.py" if minor <= 8 else "tools/v1363_9_root_cause_analysis_checkpoint_tests.py"))
    if version.startswith("1364."):
        minor = int(version.split(".")[1])
        return "tools/v1364_0_2_repair_proposal_foundations_tests.py" if minor <= 2 else ("tools/v1364_3_5_repair_proposal_integration_tests.py" if minor <= 5 else ("tools/v1364_6_8_repair_proposal_reliability_tests.py" if minor <= 8 else "tools/v1364_9_repair_proposal_checkpoint_tests.py"))
    if version.startswith("1365."):
        minor = int(version.split(".")[1])
        return "tools/v1365_0_2_iterative_repair_foundations_tests.py" if minor <= 2 else ("tools/v1365_3_5_iterative_repair_integration_tests.py" if minor <= 5 else ("tools/v1365_6_8_iterative_repair_reliability_tests.py" if minor <= 8 else "tools/v1365_9_iterative_repair_checkpoint_tests.py"))
    if version.startswith("1366."):
        minor = int(version.split(".")[1])
        return "tools/v1366_0_2_concurrency_diagnosis_foundations_tests.py" if minor <= 2 else ("tools/v1366_3_5_concurrency_diagnosis_integration_tests.py" if minor <= 5 else ("tools/v1366_6_8_concurrency_diagnosis_reliability_tests.py" if minor <= 8 else "tools/v1366_9_concurrency_diagnosis_checkpoint_tests.py"))
    if version.startswith("1367."):
        minor = int(version.split(".")[1])
        return "tools/v1367_0_2_data_diagnosis_foundations_tests.py" if minor <= 2 else ("tools/v1367_3_5_data_diagnosis_integration_tests.py" if minor <= 5 else ("tools/v1367_6_8_data_diagnosis_reliability_tests.py" if minor <= 8 else "tools/v1367_9_data_diagnosis_checkpoint_tests.py"))
    if version.startswith("1368."):
        minor = int(version.split(".")[1])
        return "tools/v1368_0_2_provider_diagnosis_foundations_tests.py" if minor <= 2 else ("tools/v1368_3_5_provider_diagnosis_integration_tests.py" if minor <= 5 else ("tools/v1368_6_8_provider_diagnosis_reliability_tests.py" if minor <= 8 else "tools/v1368_9_provider_diagnosis_checkpoint_tests.py"))
    if version.startswith("1369."):
        minor = int(version.split(".")[1])
        return "tools/v1369_0_2_ui_diagnosis_foundations_tests.py" if minor <= 2 else ("tools/v1369_3_5_ui_diagnosis_integration_tests.py" if minor <= 5 else ("tools/v1369_6_8_ui_diagnosis_reliability_tests.py" if minor <= 8 else "tools/v1369_9_ui_diagnosis_checkpoint_tests.py"))
    if version.startswith("1370."):
        minor = int(version.split(".")[1])
        return "tools/v1370_0_2_diagnosis_repair_foundations_tests.py" if minor <= 2 else ("tools/v1370_3_5_diagnosis_repair_integration_tests.py" if minor <= 5 else ("tools/v1370_6_8_diagnosis_repair_reliability_tests.py" if minor <= 8 else "tools/v1370_9_diagnosis_repair_checkpoint_tests.py"))
    if version.startswith("1371."):
        minor = int(version.split(".")[1])
        return "tools/v1371_0_2_campaign_records_foundations_tests.py" if minor <= 2 else ("tools/v1371_3_5_campaign_records_integration_tests.py" if minor <= 5 else ("tools/v1371_6_8_campaign_records_reliability_tests.py" if minor <= 8 else "tools/v1371_9_campaign_records_checkpoint_tests.py"))
    if version.startswith("1372."):
        minor = int(version.split(".")[1])
        return "tools/v1372_0_2_crash_safe_checkpoints_foundations_tests.py" if minor <= 2 else ("tools/v1372_3_5_crash_safe_checkpoints_integration_tests.py" if minor <= 5 else ("tools/v1372_6_8_crash_safe_checkpoints_reliability_tests.py" if minor <= 8 else "tools/v1372_9_crash_safe_checkpoints_checkpoint_tests.py"))
    if version.startswith("1373."):
        minor = int(version.split(".")[1])
        return "tools/v1373_0_2_dependency_scheduling_foundations_tests.py" if minor <= 2 else ("tools/v1373_3_5_dependency_scheduling_integration_tests.py" if minor <= 5 else ("tools/v1373_6_8_dependency_scheduling_reliability_tests.py" if minor <= 8 else "tools/v1373_9_dependency_scheduling_checkpoint_tests.py"))
    if version.startswith("1374."):
        minor = int(version.split(".")[1])
        return "tools/v1374_0_2_bounded_parallelism_foundations_tests.py" if minor <= 2 else ("tools/v1374_3_5_bounded_parallelism_integration_tests.py" if minor <= 5 else ("tools/v1374_6_8_bounded_parallelism_reliability_tests.py" if minor <= 8 else "tools/v1374_9_bounded_parallelism_checkpoint_tests.py"))
    if version.startswith("1375."):
        minor = int(version.split(".")[1])
        return "tools/v1375_0_2_long_task_heartbeats_foundations_tests.py" if minor <= 2 else ("tools/v1375_3_5_long_task_heartbeats_integration_tests.py" if minor <= 5 else ("tools/v1375_6_8_long_task_heartbeats_reliability_tests.py" if minor <= 8 else "tools/v1375_9_long_task_heartbeats_checkpoint_tests.py"))
    if version.startswith("1376."):
        minor = int(version.split(".")[1])
        return "tools/v1376_0_2_partial_result_retention_foundations_tests.py" if minor <= 2 else ("tools/v1376_3_5_partial_result_retention_integration_tests.py" if minor <= 5 else ("tools/v1376_6_8_partial_result_retention_reliability_tests.py" if minor <= 8 else "tools/v1376_9_partial_result_retention_checkpoint_tests.py"))
    if version.startswith("1377."):
        minor = int(version.split(".")[1])
        return "tools/v1377_0_2_conflict_reconciliation_foundations_tests.py" if minor <= 2 else ("tools/v1377_3_5_conflict_reconciliation_integration_tests.py" if minor <= 5 else ("tools/v1377_6_8_conflict_reconciliation_reliability_tests.py" if minor <= 8 else "tools/v1377_9_conflict_reconciliation_checkpoint_tests.py"))
    if version.startswith("1378."):
        minor = int(version.split(".")[1])
        return "tools/v1378_0_2_campaign_rollback_foundations_tests.py" if minor <= 2 else ("tools/v1378_3_5_campaign_rollback_integration_tests.py" if minor <= 5 else ("tools/v1378_6_8_campaign_rollback_reliability_tests.py" if minor <= 8 else "tools/v1378_9_campaign_rollback_checkpoint_tests.py"))
    if version.startswith("1379."):
        minor = int(version.split(".")[1])
        return "tools/v1379_0_2_multi_day_continuity_foundations_tests.py" if minor <= 2 else ("tools/v1379_3_5_multi_day_continuity_integration_tests.py" if minor <= 5 else ("tools/v1379_6_8_multi_day_continuity_reliability_tests.py" if minor <= 8 else "tools/v1379_9_multi_day_continuity_checkpoint_tests.py"))
    if version.startswith("1380."):
        minor = int(version.split(".")[1])
        return "tools/v1380_0_2_durable_campaign_checkpoint_foundations_tests.py" if minor <= 2 else ("tools/v1380_3_5_durable_campaign_checkpoint_integration_tests.py" if minor <= 5 else ("tools/v1380_6_8_durable_campaign_checkpoint_reliability_tests.py" if minor <= 8 else "tools/v1380_9_durable_campaign_checkpoint_tests.py"))
    if version.startswith("1381."):
        minor = int(version.split(".")[1])
        return "tools/v1381_0_2_self_model_foundations_tests.py" if minor <= 2 else ("tools/v1381_3_5_self_model_integration_tests.py" if minor <= 5 else ("tools/v1381_6_8_self_model_reliability_tests.py" if minor <= 8 else "tools/v1381_9_self_model_checkpoint_tests.py"))
    if version.startswith("1382."):
        minor = int(version.split(".")[1])
        return "tools/v1382_0_2_self_improvement_backlog_foundations_tests.py" if minor <= 2 else ("tools/v1382_3_5_self_improvement_backlog_integration_tests.py" if minor <= 5 else ("tools/v1382_6_8_self_improvement_backlog_reliability_tests.py" if minor <= 8 else "tools/v1382_9_self_improvement_backlog_checkpoint_tests.py"))
    if version.startswith("1383."):
        minor = int(version.split(".")[1])
        return "tools/v1383_0_2_self_change_isolation_foundations_tests.py" if minor <= 2 else ("tools/v1383_3_5_self_change_isolation_integration_tests.py" if minor <= 5 else ("tools/v1383_6_8_self_change_isolation_reliability_tests.py" if minor <= 8 else "tools/v1383_9_self_change_isolation_checkpoint_tests.py"))
    if version.startswith("1384."):
        minor = int(version.split(".")[1])
        return "tools/v1384_0_2_protected_core_foundations_tests.py" if minor <= 2 else ("tools/v1384_3_5_protected_core_integration_tests.py" if minor <= 5 else ("tools/v1384_6_8_protected_core_reliability_tests.py" if minor <= 8 else "tools/v1384_9_protected_core_checkpoint_tests.py"))
    if version.startswith("1385."):
        minor = int(version.split(".")[1])
        return "tools/v1385_0_2_dogfood_verification_foundations_tests.py" if minor <= 2 else ("tools/v1385_3_5_dogfood_verification_integration_tests.py" if minor <= 5 else ("tools/v1385_6_8_dogfood_verification_reliability_tests.py" if minor <= 8 else "tools/v1385_9_dogfood_verification_checkpoint_tests.py"))
    if version.startswith("1386."):
        minor = int(version.split(".")[1])
        return "tools/v1386_0_2_shadow_execution_foundations_tests.py" if minor <= 2 else ("tools/v1386_3_5_shadow_execution_integration_tests.py" if minor <= 5 else ("tools/v1386_6_8_shadow_execution_reliability_tests.py" if minor <= 8 else "tools/v1386_9_shadow_execution_checkpoint_tests.py"))
    if version.startswith("1387."):
        minor = int(version.split(".")[1])
        return "tools/v1387_0_2_canary_self_update_foundations_tests.py" if minor <= 2 else ("tools/v1387_3_5_canary_self_update_integration_tests.py" if minor <= 5 else ("tools/v1387_6_8_canary_self_update_reliability_tests.py" if minor <= 8 else "tools/v1387_9_canary_self_update_checkpoint_tests.py"))
    if version.startswith("1388."):
        minor = int(version.split(".")[1])
        return "tools/v1388_0_2_automatic_self_rollback_foundations_tests.py" if minor <= 2 else ("tools/v1388_3_5_automatic_self_rollback_integration_tests.py" if minor <= 5 else ("tools/v1388_6_8_automatic_self_rollback_reliability_tests.py" if minor <= 8 else "tools/v1388_9_automatic_self_rollback_checkpoint_tests.py"))
    if version.startswith("1389."):
        minor = int(version.split(".")[1])
        return "tools/v1389_0_2_update_lineage_foundations_tests.py" if minor <= 2 else ("tools/v1389_3_5_update_lineage_integration_tests.py" if minor <= 5 else ("tools/v1389_6_8_update_lineage_reliability_tests.py" if minor <= 8 else "tools/v1389_9_update_lineage_checkpoint_tests.py"))
    if version.startswith("1390."):
        minor = int(version.split(".")[1])
        return "tools/v1390_0_2_self_modification_checkpoint_foundations_tests.py" if minor <= 2 else ("tools/v1390_3_5_self_modification_checkpoint_integration_tests.py" if minor <= 5 else ("tools/v1390_6_8_self_modification_checkpoint_reliability_tests.py" if minor <= 8 else "tools/v1390_9_self_modification_checkpoint_checkpoint_tests.py"))
    if version.startswith("1391."):
        minor = int(version.split(".")[1])
        return "tools/v1391_0_2_small_greenfield_task_foundations_tests.py" if minor <= 2 else ("tools/v1391_3_5_small_greenfield_task_integration_tests.py" if minor <= 5 else ("tools/v1391_6_8_small_greenfield_task_reliability_tests.py" if minor <= 8 else "tools/v1391_9_small_greenfield_task_checkpoint_tests.py"))
    if version.startswith("1392."):
        minor = int(version.split(".")[1])
        return "tools/v1392_0_2_existing_project_feature_foundations_tests.py" if minor <= 2 else ("tools/v1392_3_5_existing_project_feature_integration_tests.py" if minor <= 5 else ("tools/v1392_6_8_existing_project_feature_reliability_tests.py" if minor <= 8 else "tools/v1392_9_existing_project_feature_checkpoint_tests.py"))
    if version.startswith("1393."):
        minor = int(version.split(".")[1])
        return "tools/v1393_0_2_bug_report_task_foundations_tests.py" if minor <= 2 else ("tools/v1393_3_5_bug_report_task_integration_tests.py" if minor <= 5 else ("tools/v1393_6_8_bug_report_task_reliability_tests.py" if minor <= 8 else "tools/v1393_9_bug_report_task_checkpoint_tests.py"))
    if version.startswith("1394."):
        minor = int(version.split(".")[1])
        return "tools/v1394_0_2_refactoring_task_foundations_tests.py" if minor <= 2 else ("tools/v1394_3_5_refactoring_task_integration_tests.py" if minor <= 5 else ("tools/v1394_6_8_refactoring_task_reliability_tests.py" if minor <= 8 else "tools/v1394_9_refactoring_task_checkpoint_tests.py"))
    if version.startswith("1395."):
        minor = int(version.split(".")[1])
        return "tools/v1395_0_2_data_migration_task_foundations_tests.py" if minor <= 2 else ("tools/v1395_3_5_data_migration_task_integration_tests.py" if minor <= 5 else ("tools/v1395_6_8_data_migration_task_reliability_tests.py" if minor <= 8 else "tools/v1395_9_data_migration_task_checkpoint_tests.py"))
    if version.startswith("1396."):
        minor = int(version.split(".")[1])
        return "tools/v1396_0_2_ui_workflow_task_foundations_tests.py" if minor <= 2 else ("tools/v1396_3_5_ui_workflow_task_integration_tests.py" if minor <= 5 else ("tools/v1396_6_8_ui_workflow_task_reliability_tests.py" if minor <= 8 else "tools/v1396_9_ui_workflow_task_checkpoint_tests.py"))
    if version.startswith("1397."):
        minor = int(version.split(".")[1])
        return "tools/v1397_0_2_provider_backed_task_foundations_tests.py" if minor <= 2 else ("tools/v1397_3_5_provider_backed_task_integration_tests.py" if minor <= 5 else ("tools/v1397_6_8_provider_backed_task_reliability_tests.py" if minor <= 8 else "tools/v1397_9_provider_backed_task_checkpoint_tests.py"))
    if version.startswith("1398."):
        minor = int(version.split(".")[1])
        return "tools/v1398_0_2_no_prompt_session_foundations_tests.py" if minor <= 2 else ("tools/v1398_3_5_no_prompt_session_integration_tests.py" if minor <= 5 else ("tools/v1398_6_8_no_prompt_session_reliability_tests.py" if minor <= 8 else "tools/v1398_9_no_prompt_session_checkpoint_tests.py"))
    if version.startswith("1399."):
        minor = int(version.split(".")[1])
        return "tools/v1399_0_2_gamma_scorecard_foundations_tests.py" if minor <= 2 else ("tools/v1399_3_5_gamma_scorecard_integration_tests.py" if minor <= 5 else ("tools/v1399_6_8_gamma_scorecard_reliability_tests.py" if minor <= 8 else "tools/v1399_9_gamma_scorecard_checkpoint_tests.py"))
    if version.startswith("1400."):
        minor = int(version.split(".")[1])
        return "tools/v1400_0_2_autonomous_developer_gamma_checkpoint_foundations_tests.py" if minor <= 2 else ("tools/v1400_3_5_autonomous_developer_gamma_checkpoint_integration_tests.py" if minor <= 5 else ("tools/v1400_6_8_autonomous_developer_gamma_checkpoint_reliability_tests.py" if minor <= 8 else "tools/v1400_9_autonomous_developer_gamma_checkpoint_tests.py"))
    if version == "2730.9":
        return "tools/v2730_9_product_integrity_repair_architecture_freeze_checkpoint_tests.py"
    if version == "2730.9.1":
        return "tools/v2730_9_1_pretesting_integrity_repair_checkpoint_tests.py"
    if version == "2730.9.2":
        return "tools/v2730_9_2_pretesting_reliability_truthfulness_tests.py"
    if version == "2730.9.3":
        return "tools/v2730_9_3_review_repairs_tests.py"
    normalized = "1208_9" if version == "1208.9.1" else version.replace(".", "_")
    return f"tools/v{normalized}*.py"


@dataclass(frozen=True)
class CheckpointRecord:
    version: str
    title: str
    ordinal: int
    checkpoint_id: str
    test_selector: str
    lifecycle: str

    def as_dict(self) -> dict[str, Any]:
        row = {
            "version": self.version,
            "title": self.title,
            "ordinal": self.ordinal,
            "checkpoint_id": self.checkpoint_id,
            "test_selector": self.test_selector,
            "lifecycle": self.lifecycle,
            "read_only_registry_entry": True,
            "authority_state": "evidence_only_no_authority",
        }
        row["record_digest"] = _digest(row)
        return row


def checkpoint_records() -> tuple[CheckpointRecord, ...]:
    return tuple(
        CheckpointRecord(
            version=version,
            title=title,
            ordinal=ordinal,
            checkpoint_id=f"v{version}-{_slug(title)}",
            test_selector=_selector(version),
            lifecycle=("initiative_backlog_scheduling_arc" if any(version.startswith(f"{n}.") for n in range(1401, 1411)) else "learning_from_outcomes_arc" if any(version.startswith(f"{n}.") for n in range(1411, 1421)) else "cognitive_architecture_reflective_reasoning_arc" if any(version.startswith(f"{n}.") for n in range(1421, 1431)) else "unified_conversation_action_companion_arc" if any(version.startswith(f"{n}.") for n in range(1431, 1441)) else "desktop_product_daily_use_arc" if any(version.startswith(f"{n}.") for n in range(1441, 1450)) else "cleanup_bundle" if version.startswith("1250.") else "performance_arc" if version.startswith("1251.") else "persistent_state_performance_arc" if version.startswith("1252.") else "pre_codex_repair" if version in {"1253.9.1", "1253.9.2"} else "runtime_efficiency_beta_arc" if version.startswith("1253.") else "isolated_coding_execution_arc" if version.startswith("1254.") else "controlled_application_rollback_arc" if version.startswith("1255.") else "persistent_development_sessions_arc" if version.startswith("1256.") else "diagnostic_repair_reasoning_arc" if version.startswith("1257.") else "complete_application_construction_arc" if version.startswith("1258.") else "conversational_command_integration_arc" if version.startswith("1259.") else "coding_alpha_checkpoint_arc" if version.startswith("1260.") else "evidence_based_project_inspection_arc" if version.startswith("1261.") else "development_backlog_generation_arc" if version.startswith("1262.") else "priority_selection_arc" if version.startswith("1263.") else "alternative_planning_simulation_arc" if version.startswith("1264.") else "isolated_self_modification_arc" if version.startswith("1265.") else "intelligent_test_selection_arc" if version.startswith("1266.") else "iterative_self_repair_arc" if version.startswith("1267.") else "operator_review_handoff_arc" if version.startswith("1268.") else "governed_self_update_arc" if version.startswith("1269.") else "self_development_alpha_arc" if version.startswith("1270.") else "environment_awareness_arc" if version.startswith("1274.") else "dependency_packaging_management_arc" if version.startswith("1275.") else "unified_conversation_action_arc" if version.startswith("1287.") else "provider_aware_performance_arc" if version.startswith("1288.") else "product_quality_judgment_arc" if version.startswith("1289.") else "cognitive_coding_checkpoint_arc" if version.startswith("1290.") else "independent_improvement_proposals_arc" if version.startswith("1291.") else "value_risk_deliberation_arc" if version.startswith("1292.") else "bounded_development_campaigns_arc" if version.startswith("1293.") else "competing_candidate_evaluation_arc" if version.startswith("1294.") else "comprehensive_verification_arc" if version.startswith("1295.") else "canary_self_updates_arc" if version.startswith("1296.") else "automated_recovery_arc" if version.startswith("1297.") else "repeated_self_maintenance_arc" if version.startswith("1298.") else "final_supervised_autonomy_rehearsal_arc" if version.startswith("1299.") else "supervised_self_development_beta_arc" if version.startswith("1300.") else "autonomy_contract_arc" if any(version.startswith(f"{n}.") for n in range(1301, 1311)) else "project_understanding_arc" if any(version.startswith(f"{n}.") for n in range(1311, 1321)) else "deliberative_planning_arc" if any(version.startswith(f"{n}.") for n in range(1321, 1331)) else "verification_intelligence_arc" if any(version.startswith(f"{n}.") for n in range(1351, 1361)) else "diagnosis_repair_arc" if any(version.startswith(f"{n}.") for n in range(1361, 1371)) else "durable_campaign_arc" if any(version.startswith(f"{n}.") for n in range(1371, 1381)) else "bounded_self_modification_arc" if any(version.startswith(f"{n}.") for n in range(1381, 1391)) else "autonomous_developer_gamma_arc" if any(version.startswith(f"{n}.") for n in range(1391, 1401)) else "retained_checkpoint"),
        )
        for ordinal, (version, title) in enumerate(CHECKPOINT_HISTORY, 1)
    )


def lookup_checkpoint(version: str) -> CheckpointRecord | None:
    return next((row for row in checkpoint_records() if row.version == str(version)), None)


def checkpoint_registry_manifest(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = _source_root(source_root)
    records = checkpoint_records()
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for record in records:
        row = record.as_dict()
        matches = sorted(
            path.relative_to(root).as_posix()
            for path in root.glob(record.test_selector)
            if path.is_file()
        )
        row["test_paths"] = matches
        row["test_path_count"] = len(matches)
        row["test_paths_digest"] = _digest(matches)
        if len(matches) != 1:
            errors.append(
                {
                    "version": record.version,
                    "reason": "checkpoint_test_resolution_not_unique",
                    "count": len(matches),
                }
            )
        rows.append(row)
    versions = [row.version for row in records]
    manifest = {
        "ok": not errors,
        "status": "checkpoint_registry_ready" if not errors else "checkpoint_registry_blocked",
        "contract_version": CONTRACT_VERSION,
        "report_schema": REPORT_SCHEMA,
        "working_source_version": WORKING_SOURCE_VERSION,
        "record_count": len(rows),
        "versions": versions,
        "records": rows,
        "errors": errors,
        "single_registry_authority": True,
        "historical_module_deletion_performed": False,
        "checkpoint_execution_performed": False,
        "legacy_descriptor_contract_version": LEGACY_DISCOVERY_CONTRACT_VERSION,
        "legacy_descriptor_count": len(checkpoint_descriptors(source_root=root)),
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    manifest["registry_digest"] = _digest(manifest)
    return manifest


def build_read_only_checkpoint_report(
    *,
    version: str,
    status: str,
    checks: Mapping[str, object] | Sequence[tuple[str, object]],
    source_root: str | Path | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = _source_root(source_root)
    record = lookup_checkpoint(version)
    if record is None:
        raise ValueError("checkpoint_version_not_registered")
    check_map = dict(checks)
    passed = sum(bool(value) for value in check_map.values())
    manifest = checkpoint_registry_manifest(source_root=root)
    report = {
        "ok": passed == len(check_map),
        "status": status if passed == len(check_map) else f"{status}_blocked",
        "schema": REPORT_SCHEMA,
        "contract_version": f"v{version}",
        "registry_contract_version": CONTRACT_VERSION,
        "checkpoint_id": record.checkpoint_id,
        "checkpoint_version": version,
        "checkpoint_title": record.title,
        "registry_digest": manifest.get("registry_digest"),
        "checks": check_map,
        "passed": passed,
        "total": len(check_map),
        "details": dict(details or {}),
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    report["checkpoint_receipt_digest"] = _digest(report)
    return report


def validate_checkpoint_report(
    report: Mapping[str, Any],
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    del source_root
    record = lookup_checkpoint(str(report.get("checkpoint_version") or ""))
    expected_digest = _digest(
        {key: value for key, value in report.items() if key != "checkpoint_receipt_digest"}
    )
    checks = {
        "schema_valid": report.get("schema") == REPORT_SCHEMA,
        "registered_version": record is not None,
        "checkpoint_id_matches": bool(record and report.get("checkpoint_id") == record.checkpoint_id),
        "counts_complete": report.get("passed") == report.get("total") == len(report.get("checks") or {}),
        "ok_matches_counts": report.get("ok") is True,
        "receipt_digest_valid": report.get("checkpoint_receipt_digest") == expected_digest,
        "read_only": report.get("read_only") is True,
        "content_free": report.get("content_free") is True,
        "no_release_authority": report.get("release_authorized") is False,
        "no_source_mutation": report.get("source_mutation_authorized") is False,
        "no_test_execution_claim": report.get("tests_executed") is False,
    }
    passed = sum(bool(value) for value in checks.values())
    result = {
        "ok": passed == len(checks),
        "status": "checkpoint_report_valid" if passed == len(checks) else "checkpoint_report_invalid",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        **AUTHORITY_FLAGS,
    }
    result["validation_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION",
    "LEGACY_DISCOVERY_CONTRACT_VERSION",
    "REPORT_SCHEMA",
    "AUTHORITY_FLAGS",
    "checkpoint_descriptors",
    "inspect_checkpoint_registry",
    "resolve_checkpoint_builder",
    "resolve_checkpoint_descriptor",
    "CheckpointRecord",
    "checkpoint_records",
    "lookup_checkpoint",
    "checkpoint_registry_manifest",
    "build_read_only_checkpoint_report",
    "validate_checkpoint_report",
]
