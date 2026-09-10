from __future__ import annotations
"""v1129.0 durable content-free reflection-to-communication eligibility signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION='v1129.0'; SCHEMA_VERSION='1'
PURPOSES={'proactive_update','delayed_follow_up','curiosity_question','clarification_request','concern_or_caution','acknowledgment','deliberate_silence_review'}
STATES={'active','suppressed','deferred','awaiting_timing_window','awaiting_prerequisite','requires_operator_review','superseded','retracted','stale','retired'}

def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'signals':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_contact_provider':False,'can_generate_message_text':False,'can_send_message':False,'can_create_notification':False,'can_create_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False,'can_promote':False,'can_certify':False}}

class ReflectiveCommunicationEligibilitySignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'reflective_communication_eligibility_signals.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_ids:list[str],source_categories:list[str],purpose:str,relevance:float,importance:float,urgency:float,uncertainty:float,sensitivity:float,interruption_cost:float,continuity_relevance:float,timing_eligible:bool=True,delay_compatible:bool=True,recovery_compatible:bool=True,confidence:float=.5,operator_confirmed:bool=False,operator_review_required:bool=False,novelty_only:bool=False,false_urgency:bool=False,structural_digest:str=''):
  event_id=_clean(event_id,180); origins=list(dict.fromkeys(_clean(x,220) for x in origin_ids if _clean(x,220))); sources=list(dict.fromkeys(_clean(x,80) for x in source_categories if _clean(x,80))); purpose=_clean(purpose,48)
  if not event_id or not origins or not sources or purpose not in PURPOSES: raise ValueError('complete structural communication lineage required')
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
  relevance,importance,urgency,uncertainty,sensitivity,interruption_cost,continuity_relevance,confidence=[clamp(x) for x in (relevance,importance,urgency,uncertainty,sensitivity,interruption_cost,continuity_relevance,confidence)]
  semantic=_digest(*sorted(origins),*sorted(sources),purpose,structural_digest)
  weak_curiosity=purpose=='curiosity_question' and relevance<.55
  suppress=novelty_only or false_urgency or weak_curiosity or relevance<.35
  state='requires_operator_review' if operator_review_required else ('suppressed' if suppress else ('deferred' if not recovery_compatible else ('awaiting_timing_window' if not timing_eligible else 'active')))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['signals'] if x.get('semantic_key')==semantic and x.get('state') in {'active','deferred','awaiting_timing_window','requires_operator_review'}),None)
   if dup: result={'status':'duplicate_signal_ignored','signal_id':dup['signal_id']}
   else:
    now=self.clock(); sid=f'communication-eligibility-{semantic[:24]}'; row={'signal_id':sid,'semantic_key':semantic,'origin_ids':origins,'source_categories':sources,'purpose':purpose,'relevance':relevance,'importance':importance,'urgency':urgency,'uncertainty':uncertainty,'sensitivity':sensitivity,'interruption_cost':interruption_cost,'continuity_relevance':continuity_relevance,'timing_eligible':bool(timing_eligible),'delay_compatible':bool(delay_compatible),'recovery_compatible':bool(recovery_compatible),'confidence':confidence,'operator_confirmed':bool(operator_confirmed),'operator_review_required':bool(operator_review_required),'novelty_only':bool(novelty_only),'false_urgency':bool(false_urgency),'structural_digest':_clean(structural_digest,128),'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'communication_candidate_id':'','conversation_proposal_id':'','initiative_id':'','message_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''};s['signals'].append(row);result={'status':'communication_eligibility_registered','signal_id':sid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['signals']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('signal_id','origin_ids','source_categories','purpose','relevance','importance','urgency','uncertainty','sensitivity','interruption_cost','continuity_relevance','timing_eligible','delay_compatible','recovery_compatible','confidence','operator_confirmed','operator_review_required','novelty_only','false_urgency','structural_digest','state','communication_candidate_id','conversation_proposal_id','initiative_id','message_id','notification_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'signal_count':len(s['signals']),'state_counts':counts,'recent_signals':[{k:x.get(k) for k in keys} for x in s['signals'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'message_text_exposed':False,'reflection_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'runtime_mutated':False}
def build_reflective_communication_eligibility_inspection(runtime_root=None): return ReflectiveCommunicationEligibilitySignalStore(runtime_root).inspection_summary()
