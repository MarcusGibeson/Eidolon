from __future__ import annotations
"""v1130.3 bounded genuine-inquiry deliberation sessions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from genuine_inquiry_candidates import GenuineInquiryCandidateStore
CONTRACT_VERSION='v1130.3'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'sessions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_generate_question_text':False,'can_send_message':False,'can_create_notification':False,'can_mutate_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False,'can_promote':False,'can_certify':False}}
class GenuineInquiryDeliberationSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'genuine_inquiry_deliberation_sessions.json'; self.clock=clock or _now; self.candidates=GenuineInquiryCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,deliberation_budget:int=1,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True):
  c=next((x for x in self.candidates.snapshot().get('candidates',[]) if x.get('candidate_id')==candidate_id),None)
  if not c or c.get('state') not in {'active','deferred','awaiting_prerequisite','requires_operator_review'}: raise ValueError('eligible inquiry candidate required')
  budget=max(1,min(int(deliberation_budget),6)); reason=''
  if c.get('state')=='requires_operator_review' and not operator_review_ready: reason='operator_review_required'
  elif c.get('state')=='awaiting_prerequisite' or not prerequisites_satisfied: reason='prerequisite_pending'
  elif c.get('state')=='deferred' or not recovery_ready: reason='recovery_constraint'
  elif not focus_available: reason='focus_constraint'
  elif not cognitive_budget_available: reason='cognitive_budget_constraint'
  state='paused' if reason else 'open'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['sessions'] if x.get('candidate_id')==candidate_id and x.get('state') in {'open','paused'}),None)
   if existing: result={'status':'inquiry_deliberation_session_reused','session_id':existing['session_id'],'state':existing['state']}
   else:
    now=self.clock(); structural=_digest(candidate_id,budget,state,reason); sid=f'inquiry-deliberation-session-{structural[:24]}'
    s['sessions'].append({'session_id':sid,'candidate_id':candidate_id,'signal_ids':c.get('signal_ids',[]),'purpose_categories':c.get('purpose_categories',[]),'source_categories':c.get('source_categories',[]),'inquiry_classification':c.get('inquiry_classification'),'deliberation_budget':budget,'recovery_ready':bool(recovery_ready),'focus_available':bool(focus_available),'cognitive_budget_available':bool(cognitive_budget_available),'operator_review_ready':bool(operator_review_ready),'prerequisites_satisfied':bool(prerequisites_satisfied),'uncertainty':c.get('uncertainty',0),'knowledge_gap':c.get('knowledge_gap',0),'contradiction_strength':c.get('contradiction_strength',0),'unfinished_thought_strength':c.get('unfinished_thought_strength',0),'curiosity_strength':c.get('curiosity_strength',0),'cognitive_cost':c.get('cognitive_cost',0),'bounded_scope_digest':c.get('bounded_scope_digest',''),'state':state,'pause_reason':reason,'structural_digest':structural,'created_at':now,'updated_at':now,'history':[{'change':'opened' if state=='open' else 'paused_at_open','occurred_at':now,'content_free':True}]}); result={'status':'inquiry_deliberation_session_opened','session_id':sid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['sessions']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('session_id','candidate_id','signal_ids','purpose_categories','source_categories','inquiry_classification','deliberation_budget','recovery_ready','focus_available','cognitive_budget_available','operator_review_ready','prerequisites_satisfied','uncertainty','knowledge_gap','contradiction_strength','unfinished_thought_strength','curiosity_strength','cognitive_cost','bounded_scope_digest','state','pause_reason','structural_digest','created_at','updated_at')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'session_count':len(s['sessions']),'state_counts':counts,'recent_sessions':[{k:x.get(k) for k in keys} for x in s['sessions'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'question_text_exposed':False,'hidden_reasoning_exposed':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_mutated':False}
def build_genuine_inquiry_deliberation_session_inspection(runtime_root=None): return GenuineInquiryDeliberationSessionStore(runtime_root).inspection_summary()
