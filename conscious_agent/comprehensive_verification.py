from __future__ import annotations
"""v1295.3-v1295.5 aggregate comprehensive verification without executing it."""
from typing import Any,Iterable,Mapping
from comprehensive_verification_foundations import ARCHITECTURE_LINEAGE,DENIED_AUTHORITY,EVIDENCE_DOMAINS,digest,valid_digest
from comprehensive_verification_evidence import (
    SymbolDependencies as _ComprehensiveVerificationEvidenceSymbolDependencies,
    combine_verification_evidence as _combine_verification_evidence_implementation,
    evidence_from_suite as _evidence_from_suite_implementation,
)

CONTRACT_VERSION='v1295.5'
def _build_comprehensive_verification_evidence_dependencies() -> _ComprehensiveVerificationEvidenceSymbolDependencies:
    return _ComprehensiveVerificationEvidenceSymbolDependencies(
        ARCHITECTURE_LINEAGE=ARCHITECTURE_LINEAGE,
        CONTRACT_VERSION=CONTRACT_VERSION,
        DENIED_AUTHORITY=DENIED_AUTHORITY,
        EVIDENCE_DOMAINS=EVIDENCE_DOMAINS,
        Iterable=Iterable,
        Mapping=Mapping,
        digest=digest,
        evidence_record=evidence_record,
        valid_digest=valid_digest,
    )

def combine_verification_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    return _combine_verification_evidence_implementation(records, _deps=_build_comprehensive_verification_evidence_dependencies())


def evidence_from_suite(*, domain: str, passed: int, total: int, source_tree_digest: str, candidate_digest: str, evidence_digest: str) -> dict[str, Any]:
    return _evidence_from_suite_implementation(domain=domain, passed=passed, total=total, source_tree_digest=source_tree_digest, candidate_digest=candidate_digest, evidence_digest=evidence_digest, _deps=_build_comprehensive_verification_evidence_dependencies())

