from __future__ import annotations
"""v2620 read-only readiness/arbitration for operator-shaped project queues."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2620.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def evaluate_project_queue_readiness(queue:Mapping[str,Any], completed_project_ids=())->dict[str,Any]:
 completed=set(map(str,completed_project_ids));rows=[]
 for e in queue.get('entries') or []:
  if not isinstance(e,Mapping):continue
  deps=[str(x) for x in e.get('depends_on') or []];blockers=[str(x) for x in e.get('blockers') or []];status=str(e.get('status') or 'review')
  missing=[x for x in deps if x not in completed];ready=status=='selected' and not missing and not blockers
  rows.append({'project_id':e.get('project_id'),'project_digest':e.get('project_digest'),'status':status,'ready':ready,'missing_dependencies':missing,'blocker_count':len(blockers),'operator_priority':float(e.get('operator_priority') or 0)})
 ready_rows=sorted((x for x in rows if x['ready']),key=lambda x:(-x['operator_priority'],str(x['project_id'])))
 out={'ok':True,'contract_version':CONTRACT_VERSION,'projects':rows,'ready_project_ids':[x['project_id'] for x in ready_rows],'next_ready_project_id':ready_rows[0]['project_id'] if ready_rows else '','readiness_is_advisory':True,'campaign_started':False,'queue_mutated':False,'automatic_priority_change_permitted':False,'authority_granted':False};out['readiness_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','evaluate_project_queue_readiness']
