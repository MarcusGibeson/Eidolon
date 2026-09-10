from __future__ import annotations
"""v1128.3 bounded reflection-supported revision deliberation sessions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_supported_revision_candidates import ReflectionSupportedRevisionCandidateStore
CONTRACT_VERSION='v1128.3'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'sessions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_apply_revision':False,'can_revise_target':False,'can_approve':False,'can_authorize':False,'can_execute':False}}
class ReflectionSupportedRevisionDeliberationSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/'reflection_supported_revision_deliberation_sessions.json';self.clock=clock or _now;self.candidates=ReflectionSupportedRevisionCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,deliberation_budget:int=1,recovery_compatible:bool=True,operator_review_required:bool=False):
  c=next((x for x in self.candidates.snapshot().get('candidates',[]) if x.get('candidate_id')==candidate_id),None)
  if not c or c.get('state') not in {'active','deferred','requires_operator_review','awaiting_prerequisite'}: raise ValueError('eligible revision candidate required')
  budget=max(1,min(int(deliberation_budget),6)); blocked=bool(c.get('prerequisite_ids')) or not recovery_compatible or operator_review_required or c.get('state')!='active';state='paused' if blocked else 'open';reason='prerequisite_pending' if c.get('prerequisite_ids') else ('operator_review_required' if operator_review_required or c.get('state')=='requires_operator_review' else ('recovery_constraint' if not recovery_compatible or c.get('state')=='deferred' else ''))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['sessions'] if x.get('candidate_id')==candidate_id and x.get('state') in {'open','paused'}),None)
   if existing:result={'status':'active_revision_deliberation_session_reused','session_id':existing['session_id'],'state':existing['state']}
   else:
    now=self.clock();structural=_digest(candidate_id,budget,state,reason);sid=f'revision-deliberation-session-{structural[:24]}';s['sessions'].append({'session_id':sid,'candidate_id':candidate_id,'signal_ids':c.get('signal_ids',[]),'target_type':c.get('target_type'),'target_id':c.get('target_id'),'revision_kind':c.get('revision_kind'),'deliberation_budget':budget,'recovery_compatible':bool(recovery_compatible),'operator_review_required':bool(operator_review_required),'state':state,'pause_reason':reason,'structural_digest':structural,'created_at':now,'updated_at':now,'history':[{'change':'opened' if state=='open' else 'paused_at_open','occurred_at':now,'content_free':True}]});result={'status':'revision_deliberation_session_opened','session_id':sid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['sessions']:counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('session_id','candidate_id','signal_ids','target_type','target_id','revision_kind','deliberation_budget','recovery_compatible','operator_review_required','state','pause_reason','structural_digest','created_at','updated_at')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'session_count':len(s['sessions']),'state_counts':counts,'recent_sessions':[{k:x.get(k) for k in keys} for x in s['sessions'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'hidden_reasoning_exposed':False,'target_revised':False,'revision_applied':False,'external_action_executed':False}
def build_reflection_supported_revision_deliberation_session_inspection(runtime_root=None):return ReflectionSupportedRevisionDeliberationSessionStore(runtime_root).inspection_summary()
