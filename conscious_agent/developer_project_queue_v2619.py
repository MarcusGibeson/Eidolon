from __future__ import annotations
"""v2619 durable-structure project queue contracts; caller owns persistence."""
from typing import Any, Mapping, Sequence
import hashlib,json
CONTRACT_VERSION='v2619.0';VALID={'selected','deferred','blocked','review'}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_queue(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
 out=[];seen=set()
 for r in rows[:32]:
  if not isinstance(r,Mapping):continue
  pid=str(r.get('project_id') or '')[:120]
  if not pid or pid in seen:continue
  seen.add(pid);status=str(r.get('status') or 'review');status=status if status in VALID else 'review'
  out.append({'project_id':pid,'project_digest':str(r.get('project_digest') or '')[:64],'status':status,'operator_priority':max(0,min(1,float(r.get('operator_priority') if r.get('operator_priority') is not None else .5))),'depends_on':[str(x)[:120] for x in r.get('depends_on') or []][:12],'blockers':[str(x)[:120] for x in r.get('blockers') or []][:12],'queue_entry_applied':False})
 result={'ok':True,'contract_version':CONTRACT_VERSION,'entries':out,'entry_count':len(out),'queue_persisted':False,'campaign_started':False,'automatic_selection_permitted':False,'authority_granted':False};result['queue_digest']=_digest(result);return result
__all__=['CONTRACT_VERSION','build_project_queue']
