from __future__ import annotations

"""Read-only v1253.9 Runtime Efficiency Beta checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from performance_budgets import performance_budgets
from runtime_efficiency_beta import runtime_efficiency_beta_contract

CONTRACT_VERSION="v1253.9"
CHECKPOINT_ID="runtime-efficiency-beta-checkpoint"


def build_runtime_efficiency_beta_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
    del runtime_root
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    contract=runtime_efficiency_beta_contract(source_root=root)
    budgets=performance_budgets()
    docs=all((root/name).is_file() for name in (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1253_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1253_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1253_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1253_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1253_9.md",
        "docs/release/v1253_runtime_efficiency_budgets.json",
    ))
    checks={
        "integrated_contract_passes":contract.get("ok") is True,
        "all_nine_precheckpoint_units_present":len(contract.get("versions") or [])==9,
        "critical_path_split_present":contract.get("checks",{}).get("deferred_planning_completed_post_provider") is True,
        "import_dependency_isolation_present":contract.get("checks",{}).get("chat_runtime_import_lazy") is True and contract.get("checks",{}).get("dashboard_fast_status_isolated") is True,
        "performance_governance_present":contract.get("checks",{}).get("performance_budgets_defined") is True and contract.get("checks",{}).get("regression_harness_uses_median_p95") is True,
        "checkpoint_docs_present":docs,
        "authority_remains_denied":not any(bool(contract.get(k)) for k in ("approval_granted","tool_execution_authorized","project_mutation_authorized","provider_contact_authorized","release_authorized","independent_authority_granted")),
        "budgets_do_not_grant_authority":budgets.get("release_authorized") is False and budgets.get("independent_authority_granted") is False,
    }
    details={
        "runtime_efficiency_contract_digest":contract.get("contract_digest"),
        "native_performance_benchmark_required_by_checkpoint_tests":True,
        "full_segmented_verifier_required":True,
        "desktop_codex_review_state_after_checkpoint":"ready_for_postponed_desktop_codex_review",
    }
    return build_read_only_checkpoint_report(version="1253.9",status="runtime_efficiency_beta_checkpoint_ready",checks=checks,source_root=root,details=details)


__all__=["CONTRACT_VERSION","CHECKPOINT_ID","build_runtime_efficiency_beta_checkpoint"]
