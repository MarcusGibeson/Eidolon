from __future__ import annotations
"""v1127.3 bounded continuous-thought execution sessions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from continuous_thought_threads import ContinuousThoughtThreadStore
CONTRACT_VERSION='v1127.3'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*v:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'sessions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_contact_provider':False,'can_update_internal_records':False,'can_send_message':False,'can_execute':False}}
class ThoughtThreadExecutionSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/'thought_thread_execution_sessions.json';self.clock=clock or _now;self.threads=ContinuousThoughtThreadStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def open(self,event_id:str,*,thread_id:str,cycle_budget:int=1,recovery_compatible:bool=True,interrupted:bool=False):
  t=next((x for x in self.threads.snapshot().get('threads',[]) if x.get('thread_id')==thread_id),None)
  if not t or t.get('state') not in {'active','paused','resumable','branched','unresolved'}:raise ValueError('eligible thought thread required')
  budget=max(1,min(int(cycle_budget),4));state='paused' if interrupted or not recovery_compatible else 'open';reason='interrupted' if interrupted else ('recovery_constraint' if not recovery_compatible else '')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['sessions'] if x.get('thread_id')==thread_id and x.get('state') in {'open','paused','resumable'}),None)
   if existing:result={'status':'thought_thread_execution_session_reused','session_id':existing['session_id'],'state':existing['state']}
   else:
    now=self.clock();dig=_digest(thread_id,budget,recovery_compatible,interrupted);sid=f'thought-thread-session-{dig[:24]}';s['sessions'].append({'session_id':sid,'thread_id':thread_id,'root_reflection_outcome_id':t.get('root_reflection_outcome_id'),'current_reflection_outcome_id':t.get('current_reflection_outcome_id'),'cycle_budget':budget,'cycles_completed':0,'recovery_compatible':bool(recovery_compatible),'state':state,'pause_reason':reason,'resume_token_digest':_digest(sid,'resume'),'structural_digest':dig,'created_at':now,'updated_at':now,'history':[{'change':'opened' if state=='open' else 'paused_at_open','occurred_at':now,'content_free':True}]});result={'status':'thought_thread_execution_session_opened','session_id':sid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['sessions']:counts[x.get('state')]=counts.get(x.get('state'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'session_count':len(s['sessions']),'state_counts':counts,'recent_sessions':deepcopy(s['sessions'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
def build_thought_thread_execution_session_inspection(runtime_root=None):return ThoughtThreadExecutionSessionStore(runtime_root).inspection_summary()
