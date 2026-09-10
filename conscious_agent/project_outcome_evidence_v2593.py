from __future__ import annotations
"""v2593 bounded evidence packet for generic project success evaluation."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2593.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_outcome_evidence(*,project_id:str,goal_digest:str,current_metrics:Mapping[str,Any],verification:Mapping[str,Any]|None=None,governance:Mapping[str,Any]|None=None)->dict[str,Any]:
    gd=str(goal_digest or '').lower();
    if len(gd)!=64:raise ValueError('goal_digest_required')
    allowed_types=(str,int,float,bool,type(None))
    metrics={str(k)[:120]:v for k,v in list(current_metrics.items())[:64] if isinstance(v,allowed_types)}
    ver=dict(verification or {});gov=dict(governance or {})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'project_id':str(project_id)[:160],'goal_digest':gd,'current_metrics':metrics,'verification':{'passed':bool(ver.get('passed')),'unexplained_regression_count':int(ver.get('unexplained_regression_count') or 0),'verification_digest':str(ver.get('verification_digest') or '')[:64],'behavior_preserved':bool(ver.get('behavior_preserved'))},'governance':{'governance_authority_unchanged':bool(gov.get('governance_authority_unchanged',True))},'raw_test_output_stored':False,'raw_source_stored':False,'source_modified':False,'authority_granted':False}
    out['evidence_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_outcome_evidence']
