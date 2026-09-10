from __future__ import annotations

"""Read-only v1252.9 Persistent-State Performance checkpoint."""
import hashlib,json
from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from persistent_state_performance import persistent_state_performance_contract

CONTRACT_VERSION="v1252.9"
CHECKPOINT_ID="persistent-state-performance-checkpoint"

def _digest(value:object)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_persistent_state_performance_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
    del runtime_root
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    contract=persistent_state_performance_contract(source_root=root)
    docs=all((root/name).is_file() for name in (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1252_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1252_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1252_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1252_9_FINAL_VALIDATION.md","docs/release/v1252_persistent_state_performance_budgets.json",
    ))
    checks={
        "integrated_contract_passes":contract.get("ok") is True,
        "all_nine_precheckpoint_units_present":len(contract.get("versions") or [])==9,
        "canonical_json_authority_preserved":contract.get("checks",{}).get("canonical_json_fallbacks_retained") is True,
        "bounded_cross_session_retrieval":contract.get("checks",{}).get("cross_session_bounded") is True,
        "indexed_memory_and_actions":contract.get("checks",{}).get("memory_recent_indexed") is True and contract.get("checks",{}).get("action_listing_indexed") is True,
        "checkpoint_docs_present":docs,
        "authority_remains_denied":not any(bool(contract.get(k)) for k in ("approval_granted","tool_execution_authorized","project_mutation_authorized","provider_contact_authorized","release_authorized","independent_authority_granted")),
    }
    details={"persistent_state_contract_digest":contract.get("contract_digest"),"native_scale_benchmark_required_by_checkpoint_tests":True,"desktop_codex_review_deferred_to_v1253_9":True}
    return build_read_only_checkpoint_report(version="1252.9",status="persistent_state_performance_checkpoint_ready",checks=checks,source_root=root,details=details)

__all__=["CONTRACT_VERSION","CHECKPOINT_ID","build_persistent_state_performance_checkpoint"]
