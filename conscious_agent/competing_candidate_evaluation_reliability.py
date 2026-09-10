from __future__ import annotations
"""v1294.6-v1294.8 reliability checks for candidate comparison evidence."""
from typing import Any, Iterable, Mapping
from competing_candidate_evaluation_foundations import DENIED_AUTHORITY,valid_digest
CONTRACT_VERSION="v1294.8"

def assess_competing_candidate_evaluation_reliability(results: Iterable[Mapping[str,Any]])->dict[str,Any]:
    violations=[];count=0
    for r in results:
        count+=1;tag=f"evaluation-{count}"
        if any(bool(r.get(k)) for k in DENIED_AUTHORITY):violations.append(f"{tag}:authority_expansion")
        if r.get("selection_is_application") or r.get("selection_is_update"):violations.append(f"{tag}:selection_conflated_with_application")
        disp=str(r.get("disposition") or "");selected=str(r.get("recommended_candidate_id") or "")
        if disp=="recommend_candidate_for_operator_review" and not selected:violations.append(f"{tag}:missing_recommended_candidate")
        if selected and not r.get("operator_review_required"):violations.append(f"{tag}:missing_operator_review")
        assessments=list(r.get("assessments") or [])
        ids=[str(x.get("candidate_id") or "") for x in assessments]
        if len(ids)!=len(set(ids)):violations.append(f"{tag}:duplicate_candidate_assessment")
        for row in assessments:
            if row.get("blocked") and str(row.get("candidate_id") or "")==selected:violations.append(f"{tag}:blocked_candidate_recommended")
        if r.get("integrity_violations") and selected:violations.append(f"{tag}:integrity_failure_still_selected")
        if r.get("evaluation_digest") and not valid_digest(r.get("evaluation_digest")):violations.append(f"{tag}:invalid_evaluation_digest")
    return {"contract_version":CONTRACT_VERSION,"ok":not violations,"status":"competing_candidate_evaluation_reliability_clear" if not violations else "competing_candidate_evaluation_reliability_blocked","evaluation_count":count,"violations":violations,"native_windows_candidate_isolation_validation_pending":True,"content_free":True,"read_only":True,**DENIED_AUTHORITY}
