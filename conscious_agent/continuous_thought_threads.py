from __future__ import annotations
"""v1127.0 durable continuous thought threads without downstream authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflective_outcome_lineage import ReflectiveOutcomeLineageStore
CONTRACT_VERSION='v1127.0'; SCHEMA_VERSION='1'
STATES={'active','paused','resumable','branched','concluded','unresolved','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*v:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'threads':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_start_provider_request':False,'can_update_belief':False,'can_update_goal':False,'can_update_self_model':False,'can_send_message':False,'can_create_initiative':False,'can_execute':False}}
class ContinuousThoughtThreadStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'continuous_thought_threads.json'; self.clock=clock or _now; self.outcomes=ReflectiveOutcomeLineageStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def create(self,event_id:str,*,reflection_outcome_id:str,thread_kind:str='reflection',continuity_horizon_days:int=7):
  outcome=next((x for x in self.outcomes.snapshot().get('outcomes',[]) if x.get('outcome_id')==reflection_outcome_id),None)
  if not outcome: raise ValueError('existing reflection outcome required')
  horizon=max(1,min(int(continuity_horizon_days),30)); structural=_digest(reflection_outcome_id,thread_kind,horizon)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['threads'] if x.get('structural_digest')==structural and x.get('state') not in {'retired'}),None)
   if existing: result={'status':'duplicate_thought_thread_suppressed','thread_id':existing['thread_id']}
   else:
    now=self.clock();tid=f'thought-thread-{structural[:24]}'; row={'thread_id':tid,'root_reflection_outcome_id':reflection_outcome_id,'current_reflection_outcome_id':reflection_outcome_id,'subject_id':outcome.get('subject_id'),'thread_kind':_clean(thread_kind,80),'state':'active','parent_thread_id':'','branch_ids':[],'continuity_horizon_days':horizon,'resume_token_digest':_digest(tid,'resume'),'conclusion_digest':'','uncertainty':outcome.get('uncertainty',1.0),'structural_digest':structural,'created_at':now,'updated_at':now,'history':[{'change':'created','occurred_at':now,'content_free':True}],'belief_id':'','goal_id':'','self_model_id':'','message_id':'','action_id':''};s['threads'].append(row);result={'status':'thought_thread_created','thread_id':tid}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def transition(self,event_id:str,*,thread_id:str,state:str,reflection_outcome_id:str='',conclusion_digest:str=''):
  if state not in STATES: raise ValueError('recognized thread state required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   row=next((x for x in s['threads'] if x.get('thread_id')==thread_id),None)
   if not row: raise ValueError('existing thought thread required')
   if reflection_outcome_id:
    if not any(x.get('outcome_id')==reflection_outcome_id for x in self.outcomes.snapshot().get('outcomes',[])): raise ValueError('existing reflection outcome required')
    row['current_reflection_outcome_id']=reflection_outcome_id
   now=self.clock();row['state']=state;row['updated_at']=now
   if conclusion_digest: row['conclusion_digest']=_clean(conclusion_digest,128)
   row['history'].append({'change':state,'occurred_at':now,'reflection_outcome_id':_clean(reflection_outcome_id,220),'content_free':True})
   result={'status':f'thought_thread_{state}','thread_id':thread_id};s['processed_events'].append({'event_id':event_id,'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def branch(self,event_id:str,*,thread_id:str,reflection_outcome_id:str):
  parent=next((x for x in self.snapshot().get('threads',[]) if x.get('thread_id')==thread_id),None)
  if not parent: raise ValueError('existing thought thread required')
  created=self.create(event_id,reflection_outcome_id=reflection_outcome_id,thread_kind='branch',continuity_horizon_days=parent.get('continuity_horizon_days',7))
  child_id=created.get('thread_id')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();p=next(x for x in s['threads'] if x.get('thread_id')==thread_id);c=next(x for x in s['threads'] if x.get('thread_id')==child_id);c['parent_thread_id']=thread_id
   if child_id not in p['branch_ids']:p['branch_ids'].append(child_id)
   p['state']='branched';now=self.clock();p['updated_at']=now;p['history'].append({'change':'branched','child_thread_id':child_id,'occurred_at':now,'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
  return {'ok':True,'status':'thought_thread_branched','thread_id':thread_id,'branch_thread_id':child_id}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['threads']:counts[x.get('state')]=counts.get(x.get('state'),0)+1
  recent=[{k:x.get(k) for k in ('thread_id','root_reflection_outcome_id','current_reflection_outcome_id','subject_id','thread_kind','state','parent_thread_id','branch_ids','continuity_horizon_days','resume_token_digest','conclusion_digest','uncertainty','structural_digest','created_at','updated_at')} for x in s['threads'][-24:]]
  return {'ok':True,'contract_version':CONTRACT_VERSION,'thread_count':len(s['threads']),'state_counts':counts,'recent_threads':recent,'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'conclusions_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
def build_continuous_thought_thread_inspection(runtime_root=None): return ContinuousThoughtThreadStore(runtime_root).inspection_summary()
