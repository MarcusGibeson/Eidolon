from __future__ import annotations
"""v2566 read-only candidates for verification coverage gaps."""
from typing import Any, Mapping
import hashlib,json,re
CONTRACT_VERSION='v2566.0'
AUTHORITY={'test_creation_authorized':False,'source_mutation_authorized':False,'test_execution_authorized':False,'approval_granted':False,'release_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_verification_gap_candidates(blind_spots:Mapping[str,Any])->dict[str,Any]:
    if str(blind_spots.get('contract_version') or '')!='v2562.0': raise ValueError('blind_spot_contract_required')
    rows=[]
    for spot in list(blind_spots.get('blind_spots') or [])[:16]:
        path=str(spot.get('path') or '').replace('\\','/')[:240]
        if not path or '..' in path.split('/'): continue
        stem=path.rsplit('/',1)[-1].rsplit('.',1)[0]
        concept=re.sub(r'[^A-Za-z0-9_]+','_',stem).strip('_')[:80]
        kind=str(spot.get('kind') or '')
        candidate={'target_path':path,'gap_kind':kind,'severity':str(spot.get('severity') or 'medium'),'recommended_evidence':str(spot.get('recommended_evidence') or '')[:120],
                   'suggested_test_concept':f'{concept}_focused_behavior' if concept else 'focused_behavior','candidate_only':True,'source_content_proposed':False,'test_body_generated':False,**AUTHORITY}
        candidate['candidate_digest']=_digest(candidate);rows.append(candidate)
    out={'ok':True,'contract_version':CONTRACT_VERSION,'candidate_count':len(rows),'candidates':rows,'tests_created':0,'source_files_changed':0,**AUTHORITY};out['set_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_verification_gap_candidates']
