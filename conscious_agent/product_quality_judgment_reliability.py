from __future__ import annotations
from typing import Any, Iterable, Mapping
from product_quality_judgment_foundations import DENIED_AUTHORITY, DIMENSIONS
CONTRACT_VERSION="v1289.8"

def assess_product_quality_reliability(judgments: Iterable[Mapping[str,Any]]) -> dict[str,Any]:
    rows=[dict(x) for x in judgments]; violations=[]
    for i,row in enumerate(rows):
        prefix=f"judgment_{i}"
        states=row.get("dimension_states") or {}
        if set(states)!=set(DIMENSIONS): violations.append(prefix+":dimension_coverage")
        if row.get("release_ready_claimed") is not False: violations.append(prefix+":release_claim")
        if row.get("quality_judgment_is_authorization") is not False: violations.append(prefix+":authority_claim")
        if row.get("deterministic_tests_alone_sufficient") is not False: violations.append(prefix+":test_only_readiness")
        if row.get("operator_ready_claimed") and any(v!="pass" for v in states.values()): violations.append(prefix+":premature_operator_ready")
        if any(bool(row.get(k)) for k in DENIED_AUTHORITY): violations.append(prefix+":authority_expansion")
    return {"contract_version":CONTRACT_VERSION,"ok":not violations,"judgment_count":len(rows),"violations":violations,"violation_count":len(violations),"multidimensional_quality_preserved":not any('dimension_coverage' in x for x in violations),"test_success_not_overclaimed":not any('test_only_readiness' in x for x in violations),"release_boundary_preserved":not any('release_claim' in x for x in violations),"content_free":True,"read_only":True,**DENIED_AUTHORITY}
