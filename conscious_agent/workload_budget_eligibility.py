from __future__ import annotations
"""v1143.0 durable, content-free workload budget eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1143.0'; SCHEMA_VERSION='1'
WORKLOAD_KINDS={'cognition','conversation','inquiry','development'}
STATES={'eligible','deferred','awaiting_budget','awaiting_prerequisite','suppressed','expired','superseded','retracted','retired'}
AUTHORITY_KEYS=('can_execute','can_schedule','can_preempt','can_cancel','can_contact_provider','can_send_message','can_create_goal','can_modify_source','can_approve','can_authorize','can_install','can_promote','can_certify')
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'records':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in AUTHORITY_KEYS}}
class WorkloadBudgetEligibilityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'workload_budget_eligibility.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,workload_id:str,workload_kind:str,owner_id:str,project_digest:str='',scope_digest:str='',priority:int=50,cpu_budget_ms:int=0,memory_budget_mb:int=0,latency_budget_ms:int=0,token_budget:int=0,prerequisite_ids:list[str]|None=None,expiry_id:str='',contradiction_ids:list[str]|None=None,retraction_ids:list[str]|None=None,supersession_ids:list[str]|None=None,retirement_ids:list[str]|None=None):
  event_id=_clean(event_id,180); workload_id=_clean(workload_id); workload_kind=_clean(workload_kind,80); owner_id=_clean(owner_id)
  if not event_id or not workload_id or workload_kind not in WORKLOAD_KINDS or not owner_id: raise ValueError('bounded event, workload, kind, and owner required')
  budgets=[max(0,int(cpu_budget_ms)),max(0,int(memory_budget_mb)),max(0,int(latency_budget_ms)),max(0,int(token_budget))]
  prerequisites=sorted({_clean(x) for x in prerequisite_ids or [] if _clean(x)}); contradictions=sorted({_clean(x) for x in contradiction_ids or [] if _clean(x)}); retractions=sorted({_clean(x) for x in retraction_ids or [] if _clean(x)}); supersessions=sorted({_clean(x) for x in supersession_ids or [] if _clean(x)}); retirements=sorted({_clean(x) for x in retirement_ids or [] if _clean(x)})
  state='eligible'; reason='bounded_resource_profile'
  if retirements: state,reason='retired','retirement_lineage'
  elif retractions: state,reason='retracted','retraction_lineage'
  elif supersessions: state,reason='superseded','supersession_lineage'
  elif contradictions: state,reason='suppressed','contradictory_lineage'
  elif any(v<=0 for v in budgets): state,reason='awaiting_budget','complete_positive_budgets_required'
  elif prerequisites: state,reason='awaiting_prerequisite','prerequisites_unresolved'
  structural=_digest(workload_id,workload_kind,owner_id,project_digest,scope_digest,priority,*budgets,*prerequisites,expiry_id,*contradictions,*retractions,*supersessions,*retirements)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   duplicate=next((x for x in s['records'] if x.get('structural_digest')==structural and x.get('state') in {'eligible','awaiting_budget','awaiting_prerequisite','deferred'}),None)
   if duplicate: result={'status':'duplicate_suppressed','eligibility_id':duplicate['eligibility_id'],'state':'suppressed'}
   else:
    now=self.clock(); eid=f'workload-budget-eligibility-{structural[:24]}'; row={'eligibility_id':eid,'workload_id':workload_id,'workload_kind':workload_kind,'owner_id':owner_id,'project_digest':_clean(project_digest,128),'scope_digest':_clean(scope_digest,128),'priority':max(0,min(int(priority),100)),'cpu_budget_ms':budgets[0],'memory_budget_mb':budgets[1],'latency_budget_ms':budgets[2],'token_budget':budgets[3],'prerequisite_ids':prerequisites,'expiry_id':_clean(expiry_id),'contradiction_ids':contradictions,'retraction_ids':retractions,'supersession_ids':supersessions,'retirement_ids':retirements,'state':state,'state_reason':reason,'structural_digest':structural,'created_at':now,'content_free':True,'execution_started':False,'history':[{'change':'recorded','state':state,'occurred_at':now,'content_free':True}]}; s['records'].append(row); result={'status':'eligibility_recorded','eligibility_id':eid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s['records']: counts[r.get('state')]=counts.get(r.get('state'),0)+1
  keys=('eligibility_id','workload_id','workload_kind','owner_id','project_digest','scope_digest','priority','cpu_budget_ms','memory_budget_mb','latency_budget_ms','token_budget','prerequisite_ids','expiry_id','state','state_reason','structural_digest','execution_started')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'record_count':len(s['records']),'state_counts':counts,'recent_records':[{k:r.get(k) for k in keys} for r in s['records'][-32:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'workload_payload_exposed':False,'execution_started':False}
def build_workload_budget_eligibility_inspection(runtime_root=None): return WorkloadBudgetEligibilityStore(runtime_root).inspection_summary()
