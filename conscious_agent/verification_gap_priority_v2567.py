from __future__ import annotations
"""v2567 deterministic priority ordering for read-only verification gap candidates."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2567.0'
AUTHORITY={'automatic_selection_authorized':False,'test_creation_authorized':False,'source_mutation_authorized':False,'approval_granted':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def rank_verification_gap_candidates(candidate_set:Mapping[str,Any])->dict[str,Any]:
    if str(candidate_set.get('contract_version') or '')!='v2566.0': raise ValueError('gap_candidate_contract_required')
    ranked=[]
    for c in candidate_set.get('candidates') or []:
        sev={'high':3,'medium':2,'low':1}.get(str(c.get('severity')),1)
        path=str(c.get('target_path') or '')
        authority_sensitive=any(t in path.lower() for t in ('authority','approval','release','rollback','security','permission'))
        score=sev*10+(8 if authority_sensitive else 0)+(4 if c.get('gap_kind')=='no_focused_structural_coverage' else 0)
        ranked.append({'candidate_digest':c.get('candidate_digest'),'target_path':path,'priority_score':score,'authority_sensitive':authority_sensitive,'reason':'direct_coverage_gap' if c.get('gap_kind')=='no_focused_structural_coverage' else 'generic_surface_coverage_gap'})
    ranked.sort(key=lambda r:(-r['priority_score'],r['target_path']))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'ranked':ranked,'candidate_count':len(ranked),'selected_candidate_digest':'','selection_performed':False,**AUTHORITY};out['ranking_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','rank_verification_gap_candidates']
