from __future__ import annotations
"""v1294.0-v1294.2 foundations for evidence-backed competing candidate evaluation."""
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping
from competing_candidate_evaluation_foundations_candidate import (
    SymbolDependencies as _CompetingCandidateEvaluationFoundationsCandidateSymbolDependencies,
    normalize_candidate_evidence as _normalize_candidate_evidence_implementation,
    seal_candidate_identity as _seal_candidate_identity_implementation,
)


CONTRACT_VERSION = "v1294.2"
MAX_CANDIDATES = 6
MIN_COMPARISON_UNCERTAINTY = 55

DENIED_AUTHORITY = {
    "candidate_build_authorized": False,
    "provider_contact_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "self_update_authorized": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "standing_authority_granted": False,
}

ARCHITECTURE_LINEAGE = {
    "isolated_coding": "v1254",
    "alternative_planning": "v1264",
    "test_selection": "v1266",
    "causal_diagnostics": "v1281",
    "calibrated_uncertainty": "v1282",
    "product_quality": "v1289",
    "cognitive_coding": "v1290",
    "value_risk_deliberation": "v1292",
    "bounded_campaigns": "v1293",
}


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def valid_digest(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(c in "0123456789abcdef" for c in text)


def comparison_trigger(*, uncertainty: int, viable_approach_count: int, competing_hypothesis_count: int = 0, high_reversibility_value: bool = False) -> dict[str, Any]:
    uncertainty = max(0, min(100, int(uncertainty)))
    approaches = max(0, int(viable_approach_count))
    hypotheses = max(0, int(competing_hypothesis_count))
    reasons = []
    if approaches >= 2 and uncertainty >= MIN_COMPARISON_UNCERTAINTY: reasons.append("material_uncertainty_with_multiple_viable_approaches")
    if approaches >= 2 and hypotheses >= 2: reasons.append("competing_causal_hypotheses")
    if approaches >= 2 and high_reversibility_value and uncertainty >= 40: reasons.append("cheap_reversible_comparison_can_reduce_uncertainty")
    required = bool(reasons)
    return {
        "comparison_required": required,
        "reason_codes": reasons,
        "uncertainty": uncertainty,
        "viable_approach_count": approaches,
        "competing_hypothesis_count": hypotheses,
        "build_every_possible_candidate": False,
        "content_free": True,
        **DENIED_AUTHORITY,
    }


def _build_competing_candidate_evaluation_foundations_candidate_dependencies() -> _CompetingCandidateEvaluationFoundationsCandidateSymbolDependencies:
    return _CompetingCandidateEvaluationFoundationsCandidateSymbolDependencies(
        Iterable=Iterable,
        Mapping=Mapping,
        default=default,
        digest=digest,
        valid_digest=valid_digest,
    )

def seal_candidate_identity(*, campaign_id: str, baseline_digest: str, approach_digest: str, workspace_digest: str, changed_path_digests: Iterable[str]) -> dict[str, Any]:
    return _seal_candidate_identity_implementation(campaign_id=campaign_id, baseline_digest=baseline_digest, approach_digest=approach_digest, workspace_digest=workspace_digest, changed_path_digests=changed_path_digests, _deps=_build_competing_candidate_evaluation_foundations_candidate_dependencies())



def normalize_candidate_evidence(raw: Mapping[str, Any]) -> dict[str, Any]:
    return _normalize_candidate_evidence_implementation(raw, _deps=_build_competing_candidate_evaluation_foundations_candidate_dependencies())

