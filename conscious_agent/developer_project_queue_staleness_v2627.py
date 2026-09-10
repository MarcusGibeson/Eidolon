from __future__ import annotations
"""v2627 read-only staleness detection for queued developer projects."""
from typing import Any, Mapping
import hashlib, json
CONTRACT_VERSION='v2627.0'

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def evaluate_project_queue_staleness(queue:Mapping[str,Any], current_portfolio_review:Mapping[str,Any]|None=None)->dict[str,Any]:
    review=current_portfolio_review if isinstance(current_portfolio_review,Mapping) else {}
    current={(str(x.get('project_id') or ''),str(x.get('project_digest') or '')) for x in review.get('ranked_candidates') or [] if isinstance(x,Mapping)}
    current_ids={pid for pid,_ in current}
    rows=[]
    for e in queue.get('entries') or []:
        if not isinstance(e,Mapping):continue
        pid=str(e.get('project_id') or '')[:120];pd=str(e.get('project_digest') or '')[:64]
        reasons=[]
        if current:
            if pid not in current_ids:reasons.append('project_missing_from_current_portfolio')
            elif (pid,pd) not in current:reasons.append('project_digest_changed')
        if not pd:reasons.append('missing_project_digest')
        rows.append({'project_id':pid,'project_digest':pd,'stale':bool(reasons),'reasons':reasons,'status':str(e.get('status') or 'review')[:16]})
    stale=[x for x in rows if x['stale']]
    out={'ok':True,'contract_version':CONTRACT_VERSION,'projects':rows,'stale_project_ids':[x['project_id'] for x in stale],'stale_count':len(stale),'revalidation_required':bool(stale),'queue_mutated':False,'automatic_reselection_permitted':False,'campaign_started':False,'authority_granted':False}
    out['staleness_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','evaluate_project_queue_staleness']
