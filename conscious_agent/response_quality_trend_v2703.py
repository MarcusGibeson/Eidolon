from __future__ import annotations
"""v2703 bounded response-quality trend from explicit/structural evidence."""
from typing import Any, Iterable, Mapping
import hashlib, json
CONTRACT_VERSION='v2703.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_quality_trend(rows:Iterable[Mapping[str,Any]],*,window:int=10)->dict[str,Any]:
    raw=[dict(r) for r in rows if isinstance(r,Mapping)]
    latest={}
    order=[]
    for r in raw:
        key=str(r.get('operation_ref_digest') or r.get('row_digest') or len(order))
        if key not in latest: order.append(key)
        latest[key]=r
    items=[latest[k] for k in order]
    w=max(3,min(32,int(window or 10)));recent=items[-w:];prior=items[-2*w:-w]
    def score(rs):
        return sum(-2 if str(r.get('state'))=='quality_concern' else -1 if str(r.get('state'))=='mixed_evidence' else 2 if str(r.get('state'))=='supported_success' else 0 for r in rs)
    rs,ps=score(recent),score(prior)
    if not prior or len(recent)<3: direction='insufficient_history'
    elif rs>ps+1: direction='improving'
    elif rs+1<ps: direction='worsening'
    else: direction='stable'
    known=sum(1 for r in recent if str(r.get('state'))!='unknown')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'direction':direction,'recent_score':rs,'prior_score':ps,'recent_observations':len(recent),'prior_observations':len(prior),'recent_known_outcomes':known,'unknown_outcomes_preserved':len(recent)-known,'automatic_policy_change':False,'raw_conversation_text_stored':False,'authority_granted':False};out['trend_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_quality_trend']
