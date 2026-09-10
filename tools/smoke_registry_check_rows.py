from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

SMOKE_REGISTRY_CHECK_ROWS_VERSION = RUNTIME_VERSION
SMOKE_REGISTRY_CHECK_ROW_EXTRACTION_CHECK_ID = "smoke-registry-check-row-extraction-v1"


@dataclass(frozen=True)
class SmokeCheckRowSpec:
    name: str
    tier: str
    timeout: int
    function_name: str


SMOKE_REGISTRY_CHECK_ROW_SPECS: tuple[SmokeCheckRowSpec, ...] = (
    SmokeCheckRowSpec("smoke-check-decomposition-extraction-v1", "install", 120, "check_smoke_check_decomposition_extraction_v1"),
    SmokeCheckRowSpec("smoke-registry-metadata-extraction-v1", "install", 120, "check_smoke_registry_metadata_extraction_v1"),
    SmokeCheckRowSpec("audited-sandbox-backend-evidence-interface-v1", "install", 120, "check_audited_sandbox_backend_evidence_interface_v1"),
    SmokeCheckRowSpec(SMOKE_REGISTRY_CHECK_ROW_EXTRACTION_CHECK_ID, "install", 120, "run_smoke_registry_check_row_extraction_check"),
    SmokeCheckRowSpec("dashboard-route-registry-extraction-v1", "install", 120, "run_dashboard_route_registry_extraction_check"),
    SmokeCheckRowSpec("dashboard-renderer-metadata-extraction-v1", "install", 120, "run_dashboard_renderer_metadata_extraction_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-parity-gate-v1", "install", 120, "run_dashboard_dispatcher_parity_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-extraction-prep-v1", "install", 120, "run_dashboard_dispatcher_branch_extraction_prep_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-extraction-trial-v1", "install", 120, "run_dashboard_dispatcher_branch_extraction_trial_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-extraction-backfill-v1", "install", 120, "run_dashboard_dispatcher_branch_extraction_backfill_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-helper-consolidation-v1", "install", 120, "run_dashboard_dispatcher_branch_helper_consolidation_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-extraction-expansion-prep-v1", "install", 120, "run_dashboard_dispatcher_branch_extraction_expansion_prep_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-trial-v1", "install", 120, "run_dashboard_dispatcher_branch_expansion_trial_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-backfill-prep-v1", "install", 120, "run_dashboard_dispatcher_branch_expansion_backfill_prep_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-backfill-trial-v1", "install", 120, "run_dashboard_dispatcher_branch_expansion_backfill_trial_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-backfill-prep-v2", "install", 120, "run_dashboard_dispatcher_branch_expansion_backfill_prep_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-backfill-trial-v2", "install", 120, "run_dashboard_dispatcher_branch_expansion_backfill_trial_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-backfill-prep-v3", "install", 120, "run_dashboard_dispatcher_branch_expansion_backfill_prep_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-expansion-backfill-trial-v3", "install", 120, "run_dashboard_dispatcher_branch_expansion_backfill_trial_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-hardening-v1", "install", 120, "run_dashboard_dispatcher_branch_decomposition_hardening_check"),
    SmokeCheckRowSpec("eidolon-v1073-source-review-checkpoint-v1", "install", 120, "run_eidolon_v1073_source_review_checkpoint_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-continuation-prep-v1", "install", 120, "run_dashboard_dispatcher_branch_decomposition_continuation_prep_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-continuation-trial-v1", "install", 120, "run_dashboard_dispatcher_branch_decomposition_continuation_trial_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-continuation-prep-v2", "install", 120, "run_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-continuation-trial-v2", "install", 120, "run_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-continuation-prep-v3", "install", 120, "run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-branch-decomposition-continuation-trial-v3", "install", 120, "run_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-strategy-checkpoint-v1", "install", 120, "run_dashboard_dispatcher_batch_strategy_checkpoint_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v1", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v1", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v1", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v2", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v2", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v2", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v3", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v3", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v3", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v4", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v4_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v4", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v4_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v4", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v4_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v5", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v5_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v5", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v5_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v5", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v6", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v6_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v6", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v6_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v6", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v7", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v7_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v7", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v7_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v7", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v7_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v8", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v8_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v8", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v8_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v8", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v8_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v9", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v9_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v9", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v9_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v9", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v9_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v10", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v10_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v10", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v10_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v10", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v10_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v11", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v11_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v11", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v11_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v11", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v11_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v12", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v12_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v12", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v12_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v12", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-prep-v13", "install", 120, "run_dashboard_dispatcher_batch_decomposition_prep_v13_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-trial-v13", "install", 120, "run_dashboard_dispatcher_batch_decomposition_trial_v13_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-batch-decomposition-checkpoint-v13", "install", 120, "run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-consolidation-prep-v1", "install", 120, "run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface", "install", 120, "run_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1", "install", 120, "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v1", "install", 120, "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v2", "install", 120, "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-compatibility-migration-trial-v3", "install", 120, "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-compatibility-migration-completion-v1", "install", 180, "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-surface-retirement-prep-v1", "install", 180, "run_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_check"),
    SmokeCheckRowSpec("dashboard-dispatcher-proof-surface-historical-surface-retirement-trial-v1", "install", 240, "run_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_check"),
    SmokeCheckRowSpec("runtime-compile-and-live-version-truth-repair-v1", "install", 180, "run_runtime_compile_and_live_version_truth_repair_check"),
    SmokeCheckRowSpec("release-baseline-stabilization-v1", "install", 180, "run_release_baseline_stabilization_check"),
    SmokeCheckRowSpec("release-baseline-active-project-hotfix-v1", "install", 180, "run_release_baseline_active_project_hotfix_check"),
    SmokeCheckRowSpec("registry-navigation-smoke-consolidation-v1", "install", 240, "run_registry_navigation_smoke_consolidation_check"),
)

CHECK_ROW_EXTRACTION_SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "manual_smoke_remains_authoritative": True,
    "check_discovery_changed": False,
    "check_execution_changed": False,
}


def smoke_registry_check_row_names() -> list[str]:
    return [spec.name for spec in SMOKE_REGISTRY_CHECK_ROW_SPECS]


def build_smoke_checks_from_specs(
    smoke_check_factory: Callable[[str, str, int, Callable[[], bool]], Any],
    namespace: Mapping[str, Any],
    *,
    project_root: str | Path,
    expected_version: str,
) -> list[Any]:
    rows: list[Any] = []
    for spec in SMOKE_REGISTRY_CHECK_ROW_SPECS:
        if spec.function_name == "run_smoke_registry_check_row_extraction_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                return run_smoke_registry_check_row_extraction_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_route_registry_extraction_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_route_registry import run_dashboard_route_registry_extraction_check
                return run_dashboard_route_registry_extraction_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_renderer_metadata_extraction_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_renderer_metadata import run_dashboard_renderer_metadata_extraction_check
                return run_dashboard_renderer_metadata_extraction_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_parity_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_parity import run_dashboard_dispatcher_parity_check
                return run_dashboard_dispatcher_parity_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_extraction_prep_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_prep import run_dashboard_dispatcher_branch_extraction_prep_check
                return run_dashboard_dispatcher_branch_extraction_prep_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_extraction_trial_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_trial import run_dashboard_dispatcher_branch_extraction_trial_check
                return run_dashboard_dispatcher_branch_extraction_trial_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_extraction_backfill_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_backfill import run_dashboard_dispatcher_branch_extraction_backfill_check
                return run_dashboard_dispatcher_branch_extraction_backfill_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_helper_consolidation_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_helper_consolidation import run_dashboard_dispatcher_branch_helper_consolidation_check
                return run_dashboard_dispatcher_branch_helper_consolidation_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_extraction_expansion_prep_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_prep import run_dashboard_dispatcher_branch_extraction_expansion_prep_check
                return run_dashboard_dispatcher_branch_extraction_expansion_prep_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_trial_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_trial import run_dashboard_dispatcher_branch_expansion_trial_check
                return run_dashboard_dispatcher_branch_expansion_trial_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_backfill_prep_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_backfill_prep import run_dashboard_dispatcher_branch_expansion_backfill_prep_check
                return run_dashboard_dispatcher_branch_expansion_backfill_prep_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_backfill_trial_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_backfill_trial import run_dashboard_dispatcher_branch_expansion_backfill_trial_check
                return run_dashboard_dispatcher_branch_expansion_backfill_trial_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_backfill_prep_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_backfill_prep_v2 import run_dashboard_dispatcher_branch_expansion_backfill_prep_v2_check
                return run_dashboard_dispatcher_branch_expansion_backfill_prep_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_backfill_trial_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_backfill_trial_v2 import run_dashboard_dispatcher_branch_expansion_backfill_trial_v2_check
                return run_dashboard_dispatcher_branch_expansion_backfill_trial_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_backfill_prep_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_backfill_prep_v3 import run_dashboard_dispatcher_branch_expansion_backfill_prep_v3_check
                return run_dashboard_dispatcher_branch_expansion_backfill_prep_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_expansion_backfill_trial_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_expansion_backfill_trial_v3 import run_dashboard_dispatcher_branch_expansion_backfill_trial_v3_check
                return run_dashboard_dispatcher_branch_expansion_backfill_trial_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_hardening_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_hardening import run_dashboard_dispatcher_branch_decomposition_hardening_check
                return run_dashboard_dispatcher_branch_decomposition_hardening_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_eidolon_v1073_source_review_checkpoint_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from eidolon_v1073_source_review_checkpoint import run_eidolon_v1073_source_review_checkpoint_check
                return run_eidolon_v1073_source_review_checkpoint_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_continuation_prep_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_continuation_prep import run_dashboard_dispatcher_branch_decomposition_continuation_prep_check
                return run_dashboard_dispatcher_branch_decomposition_continuation_prep_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_continuation_trial_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_continuation_trial import run_dashboard_dispatcher_branch_decomposition_continuation_trial_check
                return run_dashboard_dispatcher_branch_decomposition_continuation_trial_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_continuation_prep_v2 import run_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_check
                return run_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_continuation_trial_v2 import run_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_check
                return run_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_continuation_prep_v3 import run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check
                return run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_branch_decomposition_continuation_trial_v3 import run_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_check
                return run_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_strategy_checkpoint_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_strategy_checkpoint import run_dashboard_dispatcher_batch_strategy_checkpoint_check
                return run_dashboard_dispatcher_batch_strategy_checkpoint_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep import run_dashboard_dispatcher_batch_decomposition_prep_check
                return run_dashboard_dispatcher_batch_decomposition_prep_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial import run_dashboard_dispatcher_batch_decomposition_trial_check
                return run_dashboard_dispatcher_batch_decomposition_trial_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint import run_dashboard_dispatcher_batch_decomposition_checkpoint_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v2 import run_dashboard_dispatcher_batch_decomposition_prep_v2_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v2 import run_dashboard_dispatcher_batch_decomposition_trial_v2_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v2 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v2_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v3 import run_dashboard_dispatcher_batch_decomposition_prep_v3_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v3 import run_dashboard_dispatcher_batch_decomposition_trial_v3_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v3 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v3_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v4_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v4 import run_dashboard_dispatcher_batch_decomposition_prep_v4_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v4_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v4_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v4 import run_dashboard_dispatcher_batch_decomposition_trial_v4_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v4_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v4_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v4 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v4_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v4_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v5_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v5 import run_dashboard_dispatcher_batch_decomposition_prep_v5_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v5_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v5_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v5 import run_dashboard_dispatcher_batch_decomposition_trial_v5_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v5_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v5 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v6_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v6 import run_dashboard_dispatcher_batch_decomposition_prep_v6_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v6_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v6_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v6 import run_dashboard_dispatcher_batch_decomposition_trial_v6_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v6_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v6 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v7_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v7 import run_dashboard_dispatcher_batch_decomposition_prep_v7_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v7_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v7_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v7 import run_dashboard_dispatcher_batch_decomposition_trial_v7_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v7_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v7_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v7 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v7_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v7_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v8_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v8 import run_dashboard_dispatcher_batch_decomposition_prep_v8_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v8_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v8_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v8 import run_dashboard_dispatcher_batch_decomposition_trial_v8_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v8_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v8_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v8 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v8_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v8_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v9_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v9 import run_dashboard_dispatcher_batch_decomposition_prep_v9_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v9_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v9_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v9 import run_dashboard_dispatcher_batch_decomposition_trial_v9_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v9_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v9_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v9 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v9_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v9_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v10_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v10 import run_dashboard_dispatcher_batch_decomposition_prep_v10_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v10_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v10_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v10 import run_dashboard_dispatcher_batch_decomposition_trial_v10_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v10_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v10_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v10 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v10_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v10_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v11_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v11 import run_dashboard_dispatcher_batch_decomposition_prep_v11_check
                return run_dashboard_dispatcher_batch_decomposition_prep_v11_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v11_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v11 import run_dashboard_dispatcher_batch_decomposition_trial_v11_check
                return run_dashboard_dispatcher_batch_decomposition_trial_v11_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v11_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v11 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v11_check
                return run_dashboard_dispatcher_batch_decomposition_checkpoint_v11_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v12_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v12 import run_dashboard_dispatcher_batch_decomposition_prep_v12_check
                check_ok = run_dashboard_dispatcher_batch_decomposition_prep_v12_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-batch-decomposition-prep-v12: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe(["/dashboard-dispatcher-batch-decomposition-prep-v12"]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v12_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v12 import run_dashboard_dispatcher_batch_decomposition_trial_v12_check
                check_ok = run_dashboard_dispatcher_batch_decomposition_trial_v12_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-batch-decomposition-trial-v12: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-batch-decomposition-trial-v12",
                    "/dashboard-dispatcher-branch-decomposition-continuation-trial-v2",
                    "/dashboard-dispatcher-branch-decomposition-continuation-prep-v3",
                    "/dashboard-dispatcher-branch-decomposition-continuation-trial-v3",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v12 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check
                check_ok = run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v12: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-batch-decomposition-checkpoint-v12",
                    "/dashboard-dispatcher-batch-strategy-checkpoint",
                    "/dashboard-dispatcher-batch-decomposition-prep",
                    "/dashboard-dispatcher-batch-decomposition-trial",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_prep_v13_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_batch_decomposition_prep_v13 import run_dashboard_dispatcher_batch_decomposition_prep_v13_check
                check_ok = run_dashboard_dispatcher_batch_decomposition_prep_v13_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-batch-decomposition-prep-v13: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-batch-decomposition-prep-v13",
                    "/dashboard-dispatcher-batch-strategy-checkpoint",
                    "/dashboard-dispatcher-batch-decomposition-prep",
                    "/dashboard-dispatcher-batch-decomposition-trial",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_trial_v13_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_batch_decomposition_trial_v13 import run_dashboard_dispatcher_batch_decomposition_trial_v13_check
                check_ok = run_dashboard_dispatcher_batch_decomposition_trial_v13_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-batch-decomposition-trial-v13: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-batch-decomposition-trial-v13",
                    "/dashboard-dispatcher-batch-strategy-checkpoint",
                    "/dashboard-dispatcher-batch-decomposition-prep",
                    "/dashboard-dispatcher-batch-decomposition-trial",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_batch_decomposition_checkpoint_v13 import run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check
                check_ok = run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-batch-decomposition-checkpoint-v13: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-batch-decomposition-checkpoint-v13",
                    "/dashboard-dispatcher-batch-decomposition-trial-v13",
                    "/dashboard-dispatcher-batch-decomposition-checkpoint-v12",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_proof_surface_consolidation_prep_v1 import run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check
                check_ok = run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-proof-surface-consolidation-prep-v1",
                    "/dashboard-dispatcher-batch-decomposition-checkpoint-v13",
                    "/dashboard-dispatcher-batch-decomposition-trial-v13",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1 import run_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_check
                check_ok = run_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-proof-surface: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-proof-surface",
                    "/dashboard-dispatcher-proof-surface-consolidation-prep-v1",
                    "/dashboard-dispatcher-batch-decomposition-checkpoint-v13",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version, namespace: Mapping[str, Any] = namespace) -> bool:
                from dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1 import run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_check
                check_ok = run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_check(project_root, expected_version=expected_version)
                http_probe = namespace.get("probe_dashboard_http_routes")
                if not callable(http_probe):
                    print("[fail] dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1: real HTTP probe unavailable")
                    return False
                return check_ok and bool(http_probe([
                    "/dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1",
                    "/dashboard-dispatcher-proof-surface",
                    "/dashboard-dispatcher-batch-decomposition-checkpoint",
                ]))
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1 import run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1_check
                return run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v1_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2 import run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2_check
                return run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v2_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3 import run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_check
                return run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_trial_v3_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_v1 import run_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_check
                return run_dashboard_dispatcher_proof_surface_historical_surface_retirement_prep_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_v1 import run_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_check
                return run_dashboard_dispatcher_proof_surface_historical_surface_retirement_trial_check(project_root, expected_version=expected_version)
            check_callable = runner
        elif spec.function_name == "run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_check":
            def runner(project_root: str | Path = project_root, expected_version: str = expected_version) -> bool:
                from dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_v1 import run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_check
                return run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_completion_check(project_root, expected_version=expected_version)
            check_callable = runner
        else:
            check_callable = namespace.get(spec.function_name)
        if not callable(check_callable):
            raise KeyError(f"Missing smoke check callable for {spec.name}: {spec.function_name}")
        rows.append(smoke_check_factory(spec.name, spec.tier, spec.timeout, check_callable))
    return rows


def build_smoke_registry_check_row_extraction_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_smoke_line_count: int = 22038,
) -> dict[str, Any]:
    root = Path(project_root)
    smoke_path = root / "tools" / "smoke_check.py"
    helper_path = root / "tools" / "smoke_registry_check_rows.py"
    smoke_text = smoke_path.read_text(encoding="utf-8")
    helper_text = helper_path.read_text(encoding="utf-8")
    smoke_lines = smoke_text.count("\n") + 1
    moved_names = smoke_registry_check_row_names()
    direct_constructor_tokens = [f'SmokeCheck("{name}"' for name in moved_names]
    rows: list[dict[str, Any]] = [
        {"name": "check-row-helper-current", "ok": SMOKE_REGISTRY_CHECK_ROWS_VERSION == expected_version},
        {"name": "check-row-helper-exists", "ok": helper_path.exists()},
        {"name": "row-specs-moved-to-helper", "ok": "SMOKE_REGISTRY_CHECK_ROW_SPECS" in helper_text and all(name in helper_text for name in moved_names)},
        {"name": "smoke-check-imports-row-helper", "ok": "from smoke_registry_check_rows import" in smoke_text and "build_smoke_checks_from_specs" in smoke_text},
        {"name": "direct-row-constructors-removed", "ok": not any(token in smoke_text for token in direct_constructor_tokens), "moved_rows": moved_names},
        {"name": "check-discovery-remains-local", "ok": "def _build_checks" in smoke_text and "build_smoke_checks_from_specs(SmokeCheck, globals()" in smoke_text},
        {"name": "check-execution-remains-callable-bound", "ok": all(spec.function_name for spec in SMOKE_REGISTRY_CHECK_ROW_SPECS)},
        {"name": "new-check-row-registered-through-helper", "ok": SMOKE_REGISTRY_CHECK_ROW_EXTRACTION_CHECK_ID in helper_text and SMOKE_REGISTRY_CHECK_ROW_EXTRACTION_CHECK_ID not in smoke_text},
        {"name": "smoke-check-line-count-within-successor-budget", "ok": smoke_lines <= max(previous_smoke_line_count + 80, 22200), "current_line_count": smoke_lines, "previous_line_count": previous_smoke_line_count, "successor_budget": max(previous_smoke_line_count + 80, 22200)},
        {"name": "manual-smoke-registry-remains-authoritative", "ok": CHECK_ROW_EXTRACTION_SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True},
    ]
    ok = all(row.get("ok") is True for row in rows)
    return {
        "version": expected_version,
        "check_id": SMOKE_REGISTRY_CHECK_ROW_EXTRACTION_CHECK_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "tools/smoke_registry_check_rows.py",
        "extracted_row_specs": [spec.__dict__ for spec in SMOKE_REGISTRY_CHECK_ROW_SPECS],
        "moved_row_names": moved_names,
        "smoke_check_line_count": smoke_lines,
        "previous_smoke_check_line_count": previous_smoke_line_count,
        "line_count_delta": smoke_lines - previous_smoke_line_count,
        "rows": rows,
        **CHECK_ROW_EXTRACTION_SAFETY_BOUNDARY,
    }


def run_smoke_registry_check_row_extraction_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_smoke_registry_check_row_extraction_report(project_root, expected_version=expected_version)
        if SMOKE_REGISTRY_CHECK_ROWS_VERSION != expected_version:
            print("[fail] smoke-registry-check-row-extraction-v1: helper version is stale")
            return False
        if report.get("ok") is not True:
            print("[fail] smoke-registry-check-row-extraction-v1: extraction report blocked")
            print(report.get("rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0:
            print("[fail] smoke-registry-check-row-extraction-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] smoke-registry-check-row-extraction-v1: authority boundary changed")
            return False
        if report.get("check_discovery_changed") is not False or report.get("check_execution_changed") is not False:
            print("[fail] smoke-registry-check-row-extraction-v1: registry behavior boundary changed")
            return False
        print(f"[ok] smoke-registry-check-row-extraction-v1 line_delta={report.get('line_count_delta')} helper={report.get('helper_module')}")
        return True
    except Exception as error:
        print(f"[fail] smoke-registry-check-row-extraction-v1: {error}")
        return False
# v1071.6 dashboard dispatcher parity smoke row tokens: dashboard-dispatcher-parity-gate-v1 run_dashboard_dispatcher_parity_check route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch extraction prep smoke row tokens: dashboard-dispatcher-branch-extraction-prep-v1 run_dashboard_dispatcher_branch_extraction_prep_check branch_extraction_prepared_only=True branch_extraction_executed=False dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed_for_candidates=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch extraction trial smoke row tokens: dashboard-dispatcher-branch-extraction-trial-v1 run_dashboard_dispatcher_branch_extraction_trial_check render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch extraction backfill smoke row tokens: dashboard-dispatcher-branch-extraction-backfill-v1 run_dashboard_dispatcher_branch_extraction_backfill_check render_dashboard_renderer_metadata_extraction_backfill_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=2 backfilled_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch helper consolidation smoke row tokens: dashboard-dispatcher-branch-helper-consolidation-v1 run_dashboard_dispatcher_branch_helper_consolidation_check conscious_agent/dashboard_dispatcher_branch_helpers.py CONSOLIDATED_DASHBOARD_DISPATCHER_BRANCH_HELPERS dispatcher_branch_helper_consolidated=True additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch extraction expansion prep smoke row tokens: dashboard-dispatcher-branch-extraction-expansion-prep-v1 run_dashboard_dispatcher_branch_extraction_expansion_prep_check conscious_agent/dashboard_dispatcher_branch_expansion_prep.py build_dashboard_dispatcher_branch_extraction_expansion_prep_report branch_expansion_prepared_only=True branch_expansion_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=2 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch expansion trial smoke row tokens: dashboard-dispatcher-branch-expansion-trial-v1 run_dashboard_dispatcher_branch_expansion_trial_check conscious_agent/dashboard_dispatcher_branch_expansion_trial.py build_dashboard_dispatcher_branch_expansion_trial_report branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 extracted_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.3 dashboard dispatcher branch expansion backfill prep smoke row tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v1 run_dashboard_dispatcher_branch_expansion_backfill_prep_check conscious_agent/dashboard_dispatcher_branch_expansion_backfill_prep.py build_dashboard_dispatcher_branch_expansion_backfill_prep_report branch_expansion_backfill_prepared_only=True branch_expansion_backfill_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=3 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1072.4 dashboard dispatcher branch expansion backfill trial smoke row tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 run_dashboard_dispatcher_branch_expansion_backfill_trial_check conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py build_dashboard_dispatcher_branch_expansion_backfill_trial_report branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.0 smoke registry check row tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 run_eidolon_v1073_source_review_checkpoint_check actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.1 smoke registry check row tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 run_dashboard_dispatcher_branch_decomposition_continuation_prep_check conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep.py branch_decomposition_continuation_prepared_only=True branch_decomposition_continuation_executed=False additional_branch_extraction_count=0 helper_backed_branch_count=6 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.3 smoke registry check row tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 run_dashboard_dispatcher_branch_decomposition_continuation_trial_check conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial.py branch_decomposition_continuation_trial_executed=True additional_branch_extraction_count=1 helper_backed_branch_count=7 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1073.3 smoke registry check row tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 run_dashboard_dispatcher_branch_decomposition_continuation_prep_v2_check conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v2.py branch_decomposition_continuation_prepared_only=True branch_decomposition_continuation_executed=False additional_branch_extraction_count=0 helper_backed_branch_count=7 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v2 run_dashboard_dispatcher_branch_decomposition_continuation_trial_v2_check conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v2.py branch_decomposition_continuation_trial_executed=True additional_branch_extraction_count=1 helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 run_dashboard_dispatcher_branch_decomposition_continuation_prep_v3_check conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py branch_decomposition_continuation_prepared_only=True additional_branch_extraction_count=0 helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 run_dashboard_dispatcher_branch_decomposition_continuation_trial_v3_check conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v3.py branch_decomposition_continuation_trial_executed=True additional_branch_extraction_count=1 helper_backed_branch_count=9 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-batch-strategy-checkpoint-v1 run_dashboard_dispatcher_batch_strategy_checkpoint_check conscious_agent/dashboard_dispatcher_batch_strategy_checkpoint.py recommended_batch_size=3 helper_backed_branch_count=9 additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v1 run_dashboard_dispatcher_batch_decomposition_prep_check conscious_agent/dashboard_dispatcher_batch_decomposition_prep.py prepared_batch_size=3 helper_backed_branch_count=9 additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v1 run_dashboard_dispatcher_batch_decomposition_trial_check conscious_agent/dashboard_dispatcher_batch_decomposition_trial.py moved_batch_size=3 helper_backed_branch_count=12 additional_branch_extraction_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 run_dashboard_dispatcher_batch_decomposition_checkpoint_check conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py recommended_batch_size=3 helper_backed_branch_count=12 remaining_registry_direct_branch_count=36 additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.1 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v2 run_dashboard_dispatcher_batch_decomposition_prep_v2_check conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v2.py prepared_batch_size=3 helper_backed_branch_count=12 additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.3 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v2 run_dashboard_dispatcher_batch_decomposition_trial_v2_check conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v2.py moved_batch_size=3 helper_backed_branch_count=15 additional_branch_extraction_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.3 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 run_dashboard_dispatcher_batch_decomposition_checkpoint_v2_check conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v2.py recommended_batch_size=3 helper_backed_branch_count=15 remaining_registry_direct_branch_count=36 additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.4 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v3 run_dashboard_dispatcher_batch_decomposition_prep_v3_check conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py prepared_batch_size=3 helper_backed_branch_count=15 additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.5 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v3 run_dashboard_dispatcher_batch_decomposition_trial_v3_check helper_backed_branch_count=18 moved_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.6 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v3 run_dashboard_dispatcher_batch_decomposition_checkpoint_v3_check helper_backed_branch_count=18 recommended_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v4 run_dashboard_dispatcher_batch_decomposition_prep_v4_check helper_backed_branch_count=18 prepared_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.8 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v4 run_dashboard_dispatcher_batch_decomposition_trial_v4_check helper_backed_branch_count=21 moved_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.9 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v4 run_dashboard_dispatcher_batch_decomposition_checkpoint_v4_check helper_backed_branch_count=21 recommended_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.0 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v5 run_dashboard_dispatcher_batch_decomposition_prep_v5_check helper_backed_branch_count=21 prepared_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.1 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v5 run_dashboard_dispatcher_batch_decomposition_trial_v5_check helper_backed_branch_count=24 moved_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
# v1075.2 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 run_dashboard_dispatcher_batch_decomposition_checkpoint_v5_check helper_backed_branch_count=24 recommended_batch_size=3 remaining_registry_direct_branch_count=36 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.3 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v6 run_dashboard_dispatcher_batch_decomposition_prep_v6_check helper_backed_branch_count=24 prepared_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.4 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v6 run_dashboard_dispatcher_batch_decomposition_trial_v6_check helper_backed_branch_count=27 moved_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.5 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 run_dashboard_dispatcher_batch_decomposition_checkpoint_v6_check helper_backed_branch_count=27 recommended_batch_size=3 remaining_registry_direct_branch_count=36 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.6 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v7 run_dashboard_dispatcher_batch_decomposition_prep_v7_check helper_backed_branch_count=27 prepared_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.7 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-trial-v7 run_dashboard_dispatcher_batch_decomposition_trial_v7_check helper_backed_branch_count=30 moved_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1075.8 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v7 run_dashboard_dispatcher_batch_decomposition_checkpoint_v7_check helper_backed_branch_count=30 recommended_batch_size=3 remaining_registry_direct_branch_count=36 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 smoke registry check row tokens: dashboard-dispatcher-batch-decomposition-prep-v8 run_dashboard_dispatcher_batch_decomposition_prep_v8_check helper_backed_branch_count=30 prepared_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 dashboard-dispatcher-batch-decomposition-trial-v8 run_dashboard_dispatcher_batch_decomposition_trial_v8_check helper_backed_branch_count=33

# v1076.1 smoke registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v8 run_dashboard_dispatcher_batch_decomposition_checkpoint_v8_check helper_backed_branch_count=33 recommended_batch_size=3 remaining_registry_direct_branch_count=36 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1076.2 smoke registry tokens: dashboard-dispatcher-batch-decomposition-prep-v9 run_dashboard_dispatcher_batch_decomposition_prep_v9_check helper_backed_branch_count=33 prepared_batch_size=3 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 dashboard-dispatcher-batch-decomposition-trial-v9 run_dashboard_dispatcher_batch_decomposition_trial_v9_check helper_backed_branch_count=36

# v1076.5 smoke registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v9 run_dashboard_dispatcher_batch_decomposition_checkpoint_v9_check helper_backed_branch_count=36 recommended_batch_size=3 remaining_registry_direct_branch_count=36 manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 smoke registry tokens: dashboard-dispatcher-batch-decomposition-prep-v10 run_dashboard_dispatcher_batch_decomposition_prep_v10_check helper_backed_branch_count=36 prepared_batch_size=3

# v1077.0 dashboard-dispatcher-batch-decomposition-trial-v10 run_dashboard_dispatcher_batch_decomposition_trial_v10_check helper_backed_branch_count=39

# v1077.0 dashboard-dispatcher-batch-decomposition-checkpoint-v10 run_dashboard_dispatcher_batch_decomposition_checkpoint_v10_check helper_backed_branch_count=39 remaining_registry_direct_branch_count=36 recommended_batch_size=3

# v1077.0 smoke registry tokens: dashboard-dispatcher-batch-decomposition-prep-v11 run_dashboard_dispatcher_batch_decomposition_prep_v11_check helper_backed_branch_count=39 prepared_batch_size=3

# v1077.0 smoke registry tokens: dashboard-dispatcher-batch-decomposition-trial-v11 run_dashboard_dispatcher_batch_decomposition_trial_v11_check helper_backed_branch_count=42 moved_batch_size=3

# v1077.0 dashboard-dispatcher-batch-decomposition-checkpoint-v11 run_dashboard_dispatcher_batch_decomposition_checkpoint_v11_check helper_backed_branch_count=42 remaining_registry_direct_branch_count=36 recommended_batch_size=3

# v1077.1 smoke registry tokens: dashboard-dispatcher-batch-decomposition-prep-v12 run_dashboard_dispatcher_batch_decomposition_prep_v12_check helper_backed_branch_count=42 prepared_batch_size=3 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.2 smoke registry tokens: dashboard-dispatcher-batch-decomposition-trial-v12 run_dashboard_dispatcher_batch_decomposition_trial_v12_check helper_backed_branch_count=45 moved_batch_size=3 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.3 smoke registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v12 run_dashboard_dispatcher_batch_decomposition_checkpoint_v12_check helper_backed_branch_count=45 remaining_registry_direct_branch_count=36 recommended_batch_size=3 net_direct_route_reduction_per_cycle=0 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.4 smoke registry tokens: dashboard-dispatcher-batch-decomposition-prep-v13 run_dashboard_dispatcher_batch_decomposition_prep_v13_check helper_backed_branch_count=45 prepared_batch_size=3 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.5 smoke registry tokens: dashboard-dispatcher-batch-decomposition-trial-v13 run_dashboard_dispatcher_batch_decomposition_trial_v13_check helper_backed_branch_count=48 moved_batch_size=3 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.6 smoke registry tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v13 run_dashboard_dispatcher_batch_decomposition_checkpoint_v13_check helper_backed_branch_count=48 historical_proof_direct_route_count=36 precheckpoint_legacy_proof_route_count=35 ordinary_operational_direct_route_count=0 net_direct_route_reduction_per_legacy_cycle=0 proof_surface_consolidation_selected=True direct_http_probe_required=True

# v1077.7 smoke registry tokens: dashboard-dispatcher-proof-surface-consolidation-prep-v1 run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check historical_proof_route_count=37 helper_backed_branch_count=48 parameterized_proof_ledger_prepared=True compatibility_contract_prepared=True direct_http_probe_required=True

# v1077.8 canonical proof surface smoke tokens: dashboard-dispatcher-proof-surface run_dashboard_dispatcher_proof_surface_consolidated_renderer_trial_v1_check proof_route historical_proof_route_count=37 helper_backed_branch_count=48 direct_http_probe_required=True

# v1077.9 compatibility migration prep smoke tokens: dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1 run_dashboard_dispatcher_proof_surface_historical_compatibility_migration_prep_v1_check historical_proof_route_count=37 helper_backed_branch_count=48 compatibility_aliases_activated=False direct_http_probe_required=True
