from __future__ import annotations
"""v1143.1 governed content-free workload coordination candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from workload_budget_eligibility import WorkloadBudgetEligibilityStore
CONTRACT_VERSION='v1143.1'; SCHEMA_VERSION='1'
ACTIONS={'admit','defer','yield','reserve','require_operator_review','no_action'}
STATES={'active','suppressed','deferred','awaiting_prerequisite','requires_operator_review','expired','superseded','retracted','retired'}
AUTHORITY_KEYS=('can_execute','can_schedule','can_preempt','can_cancel','can_contact_provider','can_send_message','can_modify_source','can_approve','can_authorize','can_install','can_promote','can_certify')
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'candidates':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{k:False for k in AUTHORITY_KEYS}}
class WorkloadCoordinationCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'workload_coordination_candidates.json'; self.clock=clock or _now; self.eligibility=WorkloadBudgetEligibilityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,eligibility_id:str,coordination_action:str,coordination_group_id:str,fairness_class_id:str='',reason_code:str='bounded_arbitration',operator_review_required:bool=False):
  event_id=_clean(event_id,180); coordination_action=_clean(coordination_action,80); coordination_group_id=_clean(coordination_group_id); fairness_class_id=_clean(fairness_class_id)
  if not event_id or coordination_action not in ACTIONS or not coordination_group_id: raise ValueError('bounded event, action, and group required')
  eligibility=next((r for r in self.eligibility.snapshot().get('records',[]) if r.get('eligibility_id')==eligibility_id),None)
  if not eligibility: raise ValueError('exact v1143.0 eligibility required')
  state='active'
  if eligibility.get('state')=='awaiting_prerequisite': state='awaiting_prerequisite'
  elif eligibility.get('state')!='eligible' or coordination_action in {'defer','yield','no_action'}: state='deferred'
  elif operator_review_required or coordination_action=='require_operator_review': state='requires_operator_review'
  structural=_digest(eligibility_id,coordination_action,coordination_group_id,fairness_class_id,reason_code,operator_review_required)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   duplicate=next((x for x in s['candidates'] if x.get('structural_digest')==structural and x.get('state') in {'active','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if duplicate: result={'status':'duplicate_suppressed','candidate_id':duplicate['candidate_id'],'state':'suppressed'}
   else:
    now=self.clock(); cid=f'workload-coordination-candidate-{structural[:24]}'; row={'candidate_id':cid,'eligibility_id':eligibility_id,'workload_id':eligibility.get('workload_id'),'workload_kind':eligibility.get('workload_kind'),'owner_id':eligibility.get('owner_id'),'coordination_action':coordination_action,'coordination_group_id':coordination_group_id,'fairness_class_id':fairness_class_id,'reason_code':_clean(reason_code,120),'priority':eligibility.get('priority'),'cpu_budget_ms':eligibility.get('cpu_budget_ms'),'memory_budget_mb':eligibility.get('memory_budget_mb'),'latency_budget_ms':eligibility.get('latency_budget_ms'),'token_budget':eligibility.get('token_budget'),'operator_review_required':bool(operator_review_required),'advisory_only':True,'execution_started':False,'schedule_mutated':False,'state':state,'structural_digest':structural,'created_at':now,'history':[{'change':'recorded','state':state,'occurred_at':now,'content_free':True}]};s['candidates'].append(row);result={'status':'candidate_recorded','candidate_id':cid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for r in s['candidates']:counts[r.get('state')]=counts.get(r.get('state'),0)+1
  keys=('candidate_id','eligibility_id','workload_id','workload_kind','owner_id','coordination_action','coordination_group_id','fairness_class_id','reason_code','priority','cpu_budget_ms','memory_budget_mb','latency_budget_ms','token_budget','operator_review_required','advisory_only','execution_started','schedule_mutated','state','structural_digest')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'record_count':len(s['candidates']),'state_counts':counts,'recent_records':[{k:r.get(k) for k in keys} for r in s['candidates'][-32:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'workload_payload_exposed':False,'execution_started':False,'schedule_mutated':False}
def build_workload_coordination_candidate_inspection(runtime_root=None): return WorkloadCoordinationCandidateStore(runtime_root).inspection_summary()
