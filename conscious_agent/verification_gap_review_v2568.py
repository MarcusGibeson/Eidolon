from __future__ import annotations
"""v2568 content-minimized review packet for a verification gap candidate."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2568.0'
AUTHORITY={'test_creation_authorized':False,'test_execution_authorized':False,'source_mutation_authorized':False,'approval_granted':False,'candidate_applied':False,'release_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_verification_gap_review(candidate:Mapping[str,Any], ranking:Mapping[str,Any])->dict[str,Any]:
    dig=str(candidate.get('candidate_digest') or '')
    if len(dig)!=64 or str(ranking.get('contract_version') or '')!='v2567.0': raise ValueError('candidate_and_ranking_required')
    row=next((r for r in ranking.get('ranked') or [] if r.get('candidate_digest')==dig),None)
    if not row: raise ValueError('candidate_not_in_ranking')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'candidate_digest':dig,'target_path':str(candidate.get('target_path') or '')[:240],'gap_kind':str(candidate.get('gap_kind') or '')[:80],
         'priority_score':int(row.get('priority_score') or 0),'authority_sensitive':bool(row.get('authority_sensitive')),'suggested_test_concept':str(candidate.get('suggested_test_concept') or '')[:100],
         'operator_selection_required_before_remediation':True,'test_body_included':False,'source_content_included':False,**AUTHORITY};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_verification_gap_review']
