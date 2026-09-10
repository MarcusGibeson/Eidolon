from __future__ import annotations
"""v2628 review-only revalidation packet for stale developer queue entries."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2628.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_queue_revalidation_review(queue:Mapping[str,Any],staleness:Mapping[str,Any],readiness:Mapping[str,Any])->dict[str,Any]:
    stale={str(x) for x in staleness.get('stale_project_ids') or []};ready={str(x) for x in readiness.get('ready_project_ids') or []}
    rows=[]
    for e in queue.get('entries') or []:
        if not isinstance(e,Mapping):continue
        pid=str(e.get('project_id') or '')[:120]
        if pid not in stale:continue
        reason=next((x.get('reasons') for x in staleness.get('projects') or [] if isinstance(x,Mapping) and str(x.get('project_id'))==pid),[]) or []
        rows.append({'project_id':pid,'project_digest':str(e.get('project_digest') or '')[:64],'status':str(e.get('status') or 'review')[:16],'was_ready':pid in ready,'stale_reasons':[str(x)[:120] for x in reason][:8],'recommended_state':'review'})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'review_rows':rows,'review_count':len(rows),'operator_review_required':bool(rows),'automatic_queue_mutation_permitted':False,'automatic_project_reselection_permitted':False,'campaign_started':False,'authority_granted':False};out['revalidation_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_queue_revalidation_review']
