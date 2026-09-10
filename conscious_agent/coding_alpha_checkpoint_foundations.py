from __future__ import annotations

"""v1260.0-v1260.2 canonical Coding Alpha campaign contract.

This layer is evidence-only.  It defines the end-to-end scenario and the exact
stage/authority invariants that v1260 proves using the already-governed
v1254-v1259 pipeline.  It never creates execution/application authority.
"""

import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from coding_alpha_checkpoint_foundations_coding_alpha_contract import (
    SymbolDependencies as _CodingAlphaCheckpointFoundationsCodingAlphaContractSymbolDependencies,
    build_coding_alpha_contract as _build_coding_alpha_contract_implementation,
    public_coding_alpha_contract as _public_coding_alpha_contract_implementation,
)


SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1260.2"

DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "application_authorized": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}

STAGES = (
    ("conversational_intake", "v1259", "ordinary_action_request"),
    ("proposal_approval", "ordinary_chat_development_campaign", "exact_proposal_revision_approval"),
    ("requirements_inspection_plan", "v1254", "sealed_request_inspection_plan"),
    ("isolated_workspace", "v1254", "disposable_workspace_only"),
    ("implementation_verification", "v1254", "exact_execution_authorization"),
    ("diagnosis_repair", "v1257", "evidence_ranked_bounded_repair"),
    ("application_quality", "v1258", "cross_file_quality_verification"),
    ("persistent_session", "v1256", "restart_safe_observation_only"),
    ("operator_review", "v1254_v1258", "reviewable_diff_and_evidence"),
    ("controlled_application", "v1255", "separate_exact_application_authorization"),
    ("post_apply_verification", "v1255", "bounded_live_verification"),
    ("controlled_rollback", "v1255", "separate_exact_rollback_authorization"),
    ("restoration_verification", "v1255", "sealed_pre_apply_state_restored"),
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _build_coding_alpha_checkpoint_foundations_coding_alpha_contract_dependencies() -> _CodingAlphaCheckpointFoundationsCodingAlphaContractSymbolDependencies:
    return _CodingAlphaCheckpointFoundationsCodingAlphaContractSymbolDependencies(
        CONTRACT_VERSION=CONTRACT_VERSION,
        DENIED_AUTHORITY=DENIED_AUTHORITY,
        Mapping=Mapping,
        SCHEMA_VERSION=SCHEMA_VERSION,
        STAGES=STAGES,
        _digest=_digest,
    )

def build_coding_alpha_contract() -> dict[str, Any]:
    return _build_coding_alpha_contract_implementation(_deps=_build_coding_alpha_checkpoint_foundations_coding_alpha_contract_dependencies())



def public_coding_alpha_contract(value: Mapping[str, Any] | None=None) -> dict[str, Any]:
    return _public_coding_alpha_contract_implementation(value, _deps=_build_coding_alpha_checkpoint_foundations_coding_alpha_contract_dependencies())


__all__ = ["CONTRACT_VERSION", "DENIED_AUTHORITY", "STAGES", "build_coding_alpha_contract", "public_coding_alpha_contract"]
