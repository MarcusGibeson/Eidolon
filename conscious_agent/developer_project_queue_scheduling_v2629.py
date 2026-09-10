from __future__ import annotations
"""v2629 advisory scheduling view over ready, stale, and blocked developer projects."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2629.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_queue_scheduling_advisory(queue:Mapping[str,Any],readiness:Mapping[str,Any],staleness:Mapping[str,Any])->dict[str,Any]:
    stale={str(x) for x in staleness.get('stale_project_ids') or []};ready=[str(x) for x in readiness.get('ready_project_ids') or [] if str(x) not in stale]
    entries={str(e.get('project_id')):e for e in queue.get('entries') or [] if isinstance(e,Mapping)}
    ready_sorted=sorted(ready,key=lambda pid:(-float((entries.get(pid) or {}).get('operator_priority') or 0),pid))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'eligible_for_operator_start_review':ready_sorted,'next_for_operator_review':ready_sorted[0] if ready_sorted else '','stale_excluded_count':sum(1 for x in readiness.get('ready_project_ids') or [] if str(x) in stale),'scheduling_is_advisory':True,'operator_start_confirmation_required':True,'automatic_project_start_permitted':False,'automatic_queue_mutation_permitted':False,'authority_granted':False};out['scheduling_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_queue_scheduling_advisory']
