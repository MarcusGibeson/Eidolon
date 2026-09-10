from __future__ import annotations
from typing import Any,Iterable,Mapping
from cognitive_coding_foundations import DENIED_AUTHORITY
CONTRACT_VERSION='v1290.8'
REQUIRED_CHECKS={'objective_preserved','project_identity_preserved','multi_file_project_completed','mistaken_assumption_revised','discriminating_diagnostic_observed','focused_verification_passed','regression_verification_passed','no_failed_verification_remaining','product_quality_operator_ready_candidate','product_quality_not_release_authority'}

def assess_cognitive_coding_reliability(results:Iterable[Mapping[str,Any]])->dict[str,Any]:
    rows=[dict(x) for x in results]; violations=[]
    for i,row in enumerate(rows):
        p=f'result_{i}'
        checks=row.get('checks') if isinstance(row.get('checks'),Mapping) else {}
        if set(checks)!=REQUIRED_CHECKS:violations.append(p+':check_coverage')
        if row.get('ok') and not all(checks.values()):violations.append(p+':false_completion')
        if row.get('ok') and int(row.get('changed_path_count') or 0)<2:violations.append(p+':single_file_overclaim')
        if row.get('ok') and int(row.get('assumption_revision_count') or 0)<1:violations.append(p+':no_revision_overclaim')
        if row.get('release_ready_claimed') is not False:violations.append(p+':release_overclaim')
        if row.get('completion_is_authorization') is not False:violations.append(p+':authority_claim')
        if any(bool(row.get(k)) for k in DENIED_AUTHORITY):violations.append(p+':authority_expansion')
    return {'contract_version':CONTRACT_VERSION,'ok':not violations,'result_count':len(rows),'violations':violations,'violation_count':len(violations),'content_free':True,'read_only':True,**DENIED_AUTHORITY}
