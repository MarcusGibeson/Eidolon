from __future__ import annotations

"""v2504.6-v2504.8 Unified Cognitive Runtime Alpha.

One governed coordinator above retained cognitive subsystems. Each activation
builds a unified frame, selects at most one cognitive operation, and either
records deliberate rest or emits one bounded cognitive-work ticket. Completion
is separate, structural, idempotent, and candidate-only. The runtime never
contacts providers, browses, sends messages, authorizes protected actions,
executes tools, mutates source, or treats a selected operation as completed.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_cognitive_state_frame import build_unified_cognitive_state_frame
from cognitive_operation_arbitration import arbitrate_cognitive_operation
from cognitive_operation_registry import get_cognitive_operation
from cognitive_thought_continuity import CognitiveThoughtContinuityStore
from cognitive_outcome_integration import CognitiveOutcomeIntegrationStore, OUTCOME_TYPES
from cognitive_cycle_receipts_v2504 import CognitiveCycleReceiptStore

CONTRACT_VERSION='v2504.8';SCHEMA_VERSION='1'

def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v,n=280):return ' '.join(str(v or '').split())[:n]
def _digest(*p):return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _ref(v):
 r=_clean(v,220)
 return r if re.fullmatch(r'[A-Za-z0-9._:/#-]{1,220}',r or '') else ('subject-digest:'+hashlib.sha256(r.encode()).hexdigest()[:32] if r else '')
def _default():return {
 'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'cycles':[],'processed_begin_events':[],'processed_completion_events':[],'revision':0,'updated_at':'',
 'controls':{'max_cycles':512,'max_open_cycles':16,'minimum_utility':0.22},
 'authority_boundary':{'can_contact_provider':False,'can_browse':False,'can_send_message':False,'can_authorize_action':False,'can_execute_action':False,'can_modify_source':False,'can_apply_candidate':False,'operator_authority_unchanged':True},
}

_TARGET_BY_OUTCOME={
 'NO_DURABLE_CHANGE':'none','BELIEF_REVISION_CANDIDATE':'beliefs','GOAL_UPDATE_CANDIDATE':'goals','PLAN_UPDATE_CANDIDATE':'planning','MEMORY_INTEGRATION_CANDIDATE':'memory','SELF_MODEL_EVIDENCE_CANDIDATE':'self_model','CONFLICT_RESOLUTION_CANDIDATE':'conflict','THOUGHT_CONTINUATION':'continuity','THOUGHT_COMPLETED':'continuity',
}

class UnifiedCognitiveRuntime:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):
  self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'unified_cognitive_runtime_state.json';self.clock=clock or _now
  self.thoughts=CognitiveThoughtContinuityStore(self.root,clock=self.clock);self.outcomes=CognitiveOutcomeIntegrationStore(self.root,clock=self.clock);self.receipts=CognitiveCycleReceiptStore(self.root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def begin_cycle(self,event_id:str,*,trigger_type:str='cadence',trigger_ref:str='',subject_ref:str='',new_experience:bool=False,self_model_evidence:bool=False):
  event_id=_clean(event_id,180);trigger_type=_clean(trigger_type,80);subject_ref=_ref(subject_ref)
  if not event_id:raise ValueError('event_id required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_begin_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_begin_ignored','cycle_id':prior['cycle_id'],'idempotent':True,'cycle':deepcopy(next((c for c in s['cycles'] if c.get('cycle_id')==prior['cycle_id']),{}))}
   open_cycles=[x for x in s['cycles'] if x.get('status')=='awaiting_cognitive_work']
   if len(open_cycles)>=int(s['controls']['max_open_cycles']):
    return {'ok':False,'status':'open_cycle_budget_exhausted','open_cycle_count':len(open_cycles),'idempotent':False,'authority_broadened':False}
   thought_state=self.thoughts.inspection_summary();frame=build_unified_cognitive_state_frame(self.root,trigger_type=trigger_type,trigger_ref=trigger_ref)
   arbitration=arbitrate_cognitive_operation(frame,unfinished_thought_count=int(thought_state.get('active_count') or 0),new_experience=bool(new_experience),self_model_evidence=bool(self_model_evidence),minimum_utility=float(s['controls']['minimum_utility']))
   operation=str(arbitration['selected_operation']);op=get_cognitive_operation(operation);now=self.clock();cycle_id='unified-cognitive-cycle-'+_digest(event_id,frame['frame_digest'],operation)[:24]
   selected_subject=subject_ref
   if operation=='CONTINUE_THOUGHT' and thought_state.get('active_thoughts'):
    selected_subject=_ref(thought_state['active_thoughts'][0].get('subject_ref'))
   if not selected_subject:selected_subject='frame:'+frame['frame_id']
   row={'cycle_id':cycle_id,'begin_event_id':event_id,'trigger_type':trigger_type,'frame_id':frame['frame_id'],'frame_digest':frame['frame_digest'],'selected_operation':operation,'selected_utility':arbitration['selected_utility'],'operation_cost':op['cost'],'subject_ref':selected_subject,'status':'completed_no_action' if operation=='REST' else 'awaiting_cognitive_work','work_ticket_id':'','outcome_id':'','outcome_type':'','created_at':now,'updated_at':now,'provider_contacted':False,'external_action_executed':False,'authority_broadened':False}
   if operation=='REST':
    rr=self.receipts.append('receipt-begin-'+event_id,{'cycle_id':cycle_id,'trigger_type':trigger_type,'frame_digest':frame['frame_digest'],'selected_operation':operation,'selected_utility':arbitration['selected_utility'],'status':'no_useful_cognitive_action','subject_ref':selected_subject});row['receipt_id']=rr.get('receipt_id','')
   else:
    ticket='cognitive-work-'+_digest(cycle_id,operation,selected_subject)[:24];row['work_ticket_id']=ticket
    self.thoughts.record('thought-begin-'+event_id,operation=operation,subject_ref=selected_subject,frame_digest=frame['frame_digest'],status='unfinished',progress_marker='operation_selected',next_step='complete bounded cognitive work')
   s['cycles']=(s['cycles']+[row])[-int(s['controls']['max_cycles']):];s['processed_begin_events']=(s['processed_begin_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'cycle_id':cycle_id,'occurred_at':now,'content_free':True}])[-1024:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {'ok':True,'status':row['status'],'cycle_id':cycle_id,'frame_id':frame['frame_id'],'frame_digest':frame['frame_digest'],'selected_operation':operation,'selected_utility':arbitration['selected_utility'],'subject_ref':selected_subject,'work_ticket_id':row['work_ticket_id'],'requires_completion':operation!='REST','deliberate_inactivity':operation=='REST','provider_contacted':False,'message_sent':False,'external_action_executed':False,'source_mutated':False,'authority_broadened':False,'hidden_reasoning_exposed':False,'idempotent':False}
 def complete_cycle(self,event_id:str,*,cycle_id:str,work_ticket_id:str,outcome_type:str,evidence_digests:list[str]|None=None,changed_fields:list[str]|None=None,confidence:float=0.5):
  event_id=_clean(event_id,180);cycle_id=_clean(cycle_id,220);work_ticket_id=_clean(work_ticket_id,220);outcome_type=_clean(outcome_type,80).upper()
  if not event_id or not cycle_id or not work_ticket_id:raise ValueError('event_id, cycle_id, work_ticket_id required')
  if outcome_type not in OUTCOME_TYPES:raise ValueError('unsupported outcome_type')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_completion_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_completion_ignored','cycle_id':prior['cycle_id'],'outcome_id':prior.get('outcome_id',''),'idempotent':True}
   row=next((x for x in s['cycles'] if x.get('cycle_id')==cycle_id),None)
   if not row:raise ValueError('unknown cycle_id')
   if row.get('status')!='awaiting_cognitive_work':raise ValueError('cycle is not awaiting cognitive work')
   if row.get('work_ticket_id')!=work_ticket_id:raise ValueError('work ticket does not match cycle')
   target=_TARGET_BY_OUTCOME[outcome_type];out=self.outcomes.record('outcome-'+event_id,cycle_id=cycle_id,operation=row['selected_operation'],outcome_type=outcome_type,target=target,subject_ref=row['subject_ref'],evidence_digests=evidence_digests,changed_fields=changed_fields,confidence=confidence)
   thought_status='unfinished' if outcome_type=='THOUGHT_CONTINUATION' else 'completed';self.thoughts.record('thought-complete-'+event_id,operation=row['selected_operation'],subject_ref=row['subject_ref'],frame_digest=row['frame_digest'],status=thought_status,progress_marker='bounded_outcome_recorded',next_step='continue in later cognitive cycle' if thought_status=='unfinished' else '',evidence_digests=evidence_digests)
   now=self.clock();row['status']='completed_with_candidate' if target!='none' else 'completed_no_change';row['outcome_id']=out.get('outcome_id','');row['outcome_type']=outcome_type;row['updated_at']=now
   rr=self.receipts.append('receipt-complete-'+event_id,{'cycle_id':cycle_id,'trigger_type':row['trigger_type'],'frame_digest':row['frame_digest'],'selected_operation':row['selected_operation'],'selected_utility':row['selected_utility'],'status':row['status'],'subject_ref':row['subject_ref'],'outcome_type':outcome_type,'outcome_id':row['outcome_id'],'durable_targets':[] if target=='none' else [target]});row['receipt_id']=rr.get('receipt_id','')
   s['processed_completion_events']=(s['processed_completion_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'cycle_id':cycle_id,'outcome_id':row['outcome_id'],'occurred_at':now,'content_free':True}])[-1024:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {'ok':True,'status':row['status'],'cycle_id':cycle_id,'selected_operation':row['selected_operation'],'outcome_type':outcome_type,'outcome_id':row['outcome_id'],'candidate_target':target,'candidate_applied':False,'thought_status':thought_status,'receipt_id':row['receipt_id'],'provider_contacted':False,'message_sent':False,'external_action_executed':False,'source_mutated':False,'authority_broadened':False,'hidden_reasoning_exposed':False,'idempotent':False}
 def inspection_summary(self):
  s=self._load();open_rows=[x for x in s['cycles'] if x.get('status')=='awaiting_cognitive_work'];counts={}
  for x in s['cycles']:counts[x.get('selected_operation')]=counts.get(x.get('selected_operation'),0)+1
  keys=('cycle_id','trigger_type','frame_id','frame_digest','selected_operation','selected_utility','operation_cost','subject_ref','status','work_ticket_id','outcome_id','outcome_type','receipt_id','created_at','updated_at')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'cycle_count':len(s['cycles']),'open_cycle_count':len(open_rows),'operation_counts':counts,'recent_cycles':[{k:x.get(k) for k in keys} for x in s['cycles'][-32:]],'thought_continuity':self.thoughts.inspection_summary(),'outcomes':self.outcomes.inspection_summary(),'receipts':self.receipts.inspection_summary(),'authority_boundary':deepcopy(s['authority_boundary']),'provider_contacted':False,'message_sent':False,'external_action_executed':False,'source_mutated':False,'authority_broadened':False,'hidden_reasoning_exposed':False}

def build_unified_cognitive_runtime_inspection(runtime_root:str|Path):return UnifiedCognitiveRuntime(runtime_root).inspection_summary()
