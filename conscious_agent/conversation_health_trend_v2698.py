from __future__ import annotations
"""v2698 bounded trend analysis over content-free conversation-health history."""
from typing import Any,Iterable,Mapping
import hashlib,json
CONTRACT_VERSION='v2698.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_conversation_health_trend(rows:Iterable[Mapping[str,Any]],*,window:int=8)->dict[str,Any]:
 items=[dict(r) for r in rows if isinstance(r,Mapping)];w=max(2,min(24,int(window or 8)));recent=items[-w:];prior=items[-2*w:-w]
 score=lambda rs:sum(2 if str(r.get('state'))=='degraded' else 1 if str(r.get('state'))=='attention' else 0 for r in rs)
 rs,ps=score(recent),score(prior)
 if not prior or len(recent)<2:direction='insufficient_history'
 elif rs+1<ps:direction='improving'
 elif rs>ps+1:direction='worsening'
 else:direction='stable'
 out={'ok':True,'contract_version':CONTRACT_VERSION,'direction':direction,'recent_score':rs,'prior_score':ps,'recent_observations':len(recent),'prior_observations':len(prior),'automatic_policy_change':False,'raw_conversation_text_stored':False,'authority_granted':False};out['trend_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_conversation_health_trend']
