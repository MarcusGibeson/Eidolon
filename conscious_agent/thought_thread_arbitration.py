from __future__ import annotations
"""v1127.4 deterministic pause/resume, branch, conclusion, and unresolved arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from thought_thread_execution_sessions import ThoughtThreadExecutionSessionStore
CONTRACT_VERSION='v1127.4';SCHEMA_VERSION='1'
OUTCOMES={'continue_thread','pause_thread','resume_thread','branch_thread','conclude_thread','remain_unresolved','defer_for_recovery','defer_for_operator_review'}
def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _root():return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_contact_provider':False,'can_update_internal_records':False,'can_send_message':False,'can_execute':False}}
class ThoughtThreadArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/'thought_thread_arbitration.json';self.clock=clock or _now;self.sessions=ThoughtThreadExecutionSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def arbitrate(self,event_id:str,*,session_id:str,requested_outcome:str='',branch_supported:bool=False,conclusion_supported:bool=False,operator_review_required:bool=False):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row:raise ValueError('thought thread execution session required')
  if operator_review_required:outcome='defer_for_operator_review';reason='operator_review_required'
  elif row.get('state')=='paused' and row.get('pause_reason')=='recovery_constraint':outcome='defer_for_recovery';reason='recovery_constraint'
  elif requested_outcome=='branch_thread' and branch_supported:outcome='branch_thread';reason='branch_structurally_supported'
  elif requested_outcome=='conclude_thread' and conclusion_supported:outcome='conclude_thread';reason='conclusion_structurally_supported'
  elif requested_outcome in {'pause_thread','resume_thread','continue_thread','remain_unresolved'}:outcome=requested_outcome;reason='requested_outcome_eligible'
  else:outcome='remain_unresolved';reason='insufficient_structural_support'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing:result={'status':'thought_thread_arbitration_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock();aid=f'thought-thread-arbitration-{session_id.rsplit("-",1)[-1]}';s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'thread_id':row.get('thread_id'),'outcome':outcome,'reason_code':reason,'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}]});result={'status':'thought_thread_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['outcomes']:counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False}
def build_thought_thread_arbitration_inspection(runtime_root=None):return ThoughtThreadArbitrationStore(runtime_root).inspection_summary()
