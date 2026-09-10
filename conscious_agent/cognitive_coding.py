from __future__ import annotations

"""v1290.3-v1290.5 cognitive-coding campaign evidence integration."""
from typing import Any, Iterable, Mapping
from cognitive_coding_foundations import DENIED_AUTHORITY, MIN_MULTI_FILE_CHANGE, digest
from product_quality_judgment import build_product_quality_judgment
from cognitive_coding_cognitive_coding_result import (
    SymbolDependencies as _CognitiveCodingCognitiveCodingResultSymbolDependencies,
    build_cognitive_coding_result as _build_cognitive_coding_result_implementation,
    public_cognitive_coding_result as _public_cognitive_coding_result_implementation,
)


CONTRACT_VERSION="v1290.5"


def _build_cognitive_coding_cognitive_coding_result_dependencies() -> _CognitiveCodingCognitiveCodingResultSymbolDependencies:
    return _CognitiveCodingCognitiveCodingResultSymbolDependencies(
        CONTRACT_VERSION=CONTRACT_VERSION,
        DENIED_AUTHORITY=DENIED_AUTHORITY,
        Iterable=Iterable,
        MIN_MULTI_FILE_CHANGE=MIN_MULTI_FILE_CHANGE,
        Mapping=Mapping,
        build_product_quality_judgment=build_product_quality_judgment,
        digest=digest,
    )

def build_cognitive_coding_result(campaign: Mapping[str, Any], *, assumption_revisions: Iterable[Mapping[str, Any]], diagnostic_results: Iterable[Mapping[str, Any]], changed_paths: Iterable[str], verification_results: Iterable[Mapping[str, Any]], quality_evidence: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    return _build_cognitive_coding_result_implementation(campaign, assumption_revisions=assumption_revisions, diagnostic_results=diagnostic_results, changed_paths=changed_paths, verification_results=verification_results, quality_evidence=quality_evidence, _deps=_build_cognitive_coding_cognitive_coding_result_dependencies())



def public_cognitive_coding_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return _public_cognitive_coding_result_implementation(result, _deps=_build_cognitive_coding_cognitive_coding_result_dependencies())

