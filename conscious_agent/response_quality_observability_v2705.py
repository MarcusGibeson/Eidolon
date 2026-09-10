from __future__ import annotations
"""v2705 read-only response-quality observability."""
from typing import Any
import hashlib,json
from response_quality_history_v2702 import load_response_quality_history
from response_quality_trend_v2703 import build_response_quality_trend
CONTRACT_VERSION='v2705.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_quality_observability(runtime_root=None)->dict[str,Any]:
    rows=load_response_quality_history(runtime_root).get('rows') or []
    trend=build_response_quality_trend(rows)
    latest=dict(rows[-1]) if rows else {}
    states={k:sum(1 for r in rows if str(r.get('state'))==k) for k in ('supported_success','quality_concern','mixed_evidence','unknown')}
    out={'ok':True,'contract_version':CONTRACT_VERSION,'state':str(latest.get('state') or 'no_history'),'observation_count':len(rows),'supported_success_count':states['supported_success'],'quality_concern_count':states['quality_concern'],'mixed_count':states['mixed_evidence'],'unknown_count':states['unknown'],'trend':trend,'automatic_policy_change':False,'automatic_response_repair':False,'raw_conversation_text_stored':False,'authority_granted':False};out['observability_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_quality_observability']
