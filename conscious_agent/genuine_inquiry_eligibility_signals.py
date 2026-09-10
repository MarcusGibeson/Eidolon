from __future__ import annotations
"""v1130.0 durable content-free genuine-inquiry eligibility signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v1130.0'; SCHEMA_VERSION='1'
SOURCES={'curiosity','uncertainty','contradiction','unfinished_thought','knowledge_gap'}
PURPOSES={'resolve_uncertainty','reconcile_contradiction','continue_unfinished_thought','close_knowledge_gap','bounded_exploration','deliberate_non_inquiry_review'}
STATES={'active','suppressed','deferred','awaiting_prerequisite','requires_operator_review','superseded','retracted','stale','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'signals':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_generate_question_text':False,'can_send_message':False,'can_create_notification':False,'can_create_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False,'can_promote':False,'can_certify':False}}
class GenuineInquiryEligibilitySignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/'genuine_inquiry_eligibility_signals.json'; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_ids:list[str],source_categories:list[str],purpose:str,relevance:float,importance:float,uncertainty:float,knowledge_gap:float,contradiction_strength:float,unfinished_thought_strength:float,curiosity_strength:float,cognitive_cost:float,recovery_compatible:bool=True,prerequisite_ids:list[str]|None=None,confidence:float=.5,operator_review_required:bool=False,novelty_only:bool=False,false_urgency:bool=False,structural_digest:str=''):
  event_id=_clean(event_id,180); origins=list(dict.fromkeys(_clean(x,220) for x in origin_ids if _clean(x,220))); sources=list(dict.fromkeys(_clean(x,80) for x in source_categories if _clean(x,80))); purpose=_clean(purpose,64); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220)))
  if not event_id or not origins or not sources or any(x not in SOURCES for x in sources) or purpose not in PURPOSES: raise ValueError('complete structural inquiry lineage required')
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
  relevance,importance,uncertainty,knowledge_gap,contradiction_strength,unfinished_thought_strength,curiosity_strength,cognitive_cost,confidence=[clamp(x) for x in (relevance,importance,uncertainty,knowledge_gap,contradiction_strength,unfinished_thought_strength,curiosity_strength,cognitive_cost,confidence)]
  semantic=_digest(*sorted(origins),*sorted(sources),purpose,structural_digest)
  weak=novelty_only or false_urgency or relevance<.35 or (sources==['curiosity'] and curiosity_strength<.55)
  state='requires_operator_review' if operator_review_required else ('suppressed' if weak else ('awaiting_prerequisite' if prereqs else ('deferred' if not recovery_compatible or cognitive_cost>.85 else 'active')))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['signals'] if x.get('semantic_key')==semantic and x.get('state') in {'active','deferred','awaiting_prerequisite','requires_operator_review'}),None)
   if dup: result={'status':'duplicate_signal_ignored','signal_id':dup['signal_id']}
   else:
    now=self.clock(); sid=f'inquiry-eligibility-{semantic[:24]}'; row={'signal_id':sid,'semantic_key':semantic,'origin_ids':origins,'source_categories':sources,'purpose':purpose,'relevance':relevance,'importance':importance,'uncertainty':uncertainty,'knowledge_gap':knowledge_gap,'contradiction_strength':contradiction_strength,'unfinished_thought_strength':unfinished_thought_strength,'curiosity_strength':curiosity_strength,'cognitive_cost':cognitive_cost,'recovery_compatible':bool(recovery_compatible),'prerequisite_ids':prereqs,'confidence':confidence,'operator_review_required':bool(operator_review_required),'novelty_only':bool(novelty_only),'false_urgency':bool(false_urgency),'structural_digest':_clean(structural_digest,128),'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'inquiry_candidate_id':'','inquiry_session_id':'','question_id':'','browse_request_id':'','provider_request_id':'','initiative_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''}; s['signals'].append(row); result={'status':'inquiry_eligibility_registered','signal_id':sid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['signals']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('signal_id','origin_ids','source_categories','purpose','relevance','importance','uncertainty','knowledge_gap','contradiction_strength','unfinished_thought_strength','curiosity_strength','cognitive_cost','recovery_compatible','prerequisite_ids','confidence','operator_review_required','novelty_only','false_urgency','structural_digest','state','inquiry_candidate_id','inquiry_session_id','question_id','browse_request_id','provider_request_id','initiative_id','notification_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'signal_count':len(s['signals']),'state_counts':counts,'recent_signals':[{k:x.get(k) for k in keys} for x in s['signals'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'question_text_exposed':False,'reflection_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'runtime_mutated':False}
def build_genuine_inquiry_eligibility_inspection(runtime_root=None): return GenuineInquiryEligibilitySignalStore(runtime_root).inspection_summary()
