from __future__ import annotations
"""v2633 content-minimized operator review packet for recovered developer project queues."""
from typing import Any, Mapping
import hashlib, json
CONTRACT_VERSION="v2633.0"
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_recovered_queue_operator_review(recovery:Mapping[str,Any])->dict[str,Any]:
 q=recovery.get('queue') if isinstance(recovery.get('queue'),Mapping) else {}; r=recovery.get('readiness') if isinstance(recovery.get('readiness'),Mapping) else {}
 entries=q.get('entries') or []; ready={str(x) for x in r.get('ready_project_ids') or []}
 rows=[]
 for e in entries[:32]:
  if not isinstance(e,Mapping):continue
  pid=str(e.get('project_id') or '')[:120]
  rows.append({'project_id':pid,'project_digest':str(e.get('project_digest') or '')[:64],'status':str(e.get('status') or 'review')[:16],'ready':pid in ready,'blocker_count':len(e.get('blockers') or []),'dependency_count':len(e.get('depends_on') or [])})
 out={'ok':bool(recovery.get('ok')),'contract_version':CONTRACT_VERSION,'projects':rows,'project_count':len(rows),'operator_review_required':True,'recovery_digest':str(recovery.get('recovery_digest') or '')[:64],'content_minimized':True,'project_content_stored':False,'automatic_project_start_permitted':False,'automatic_queue_mutation_permitted':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_recovered_queue_operator_review']
