from __future__ import annotations
"""v1129.1 durable governed communication candidates; candidacy never communicates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflective_communication_eligibility_signals import ReflectiveCommunicationEligibilitySignalStore
CONTRACT_VERSION='v1129.1';SCHEMA_VERSION='1'
STATES={'active','suppressed','deferred','awaiting_timing_window','awaiting_prerequisite','requires_operator_review','merged','superseded','stale','obsolete','retracted','retired'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'candidates':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_contact_provider':False,'can_generate_message_text':False,'can_send_message':False,'can_create_notification':False,'can_mutate_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False,'can_promote':False,'can_certify':False}}
class ReflectiveCommunicationCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/'reflective_communication_candidates.json';self.signals=ReflectiveCommunicationEligibilitySignalStore(self.runtime_root);self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,signal_ids:list[str],timing_window:str='eligible_now',prerequisite_ids:list[str]|None=None,curiosity_classification:str='none',operator_review_required:bool=False,semantic_overlap_key:str=''):
  ids=list(dict.fromkeys(_clean(x,220) for x in signal_ids if _clean(x,220))); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220))); event_id=_clean(event_id,180); timing_window=_clean(timing_window,64); curiosity_classification=_clean(curiosity_classification,64); overlap=_clean(semantic_overlap_key,128)
  known={x.get('signal_id'):x for x in self.signals.snapshot().get('signals',[])}
  if not event_id or not ids or any(i not in known for i in ids): raise ValueError('known communication eligibility lineage required')
  purposes={known[i].get('purpose') for i in ids}; semantic=_digest(*sorted(ids),*sorted(purposes),timing_window,*sorted(prereqs),overlap)
  rows=[known[i] for i in ids]; weak=all(x.get('state')=='suppressed' for x in rows) or all(x.get('novelty_only') or x.get('false_urgency') for x in rows)
  review=operator_review_required or any(x.get('operator_review_required') for x in rows)
  recovery=all(x.get('recovery_compatible') for x in rows); timing=all(x.get('timing_eligible') for x in rows) and timing_window=='eligible_now'
  state='requires_operator_review' if review else ('suppressed' if weak else ('awaiting_prerequisite' if prereqs else ('deferred' if not recovery else ('awaiting_timing_window' if not timing else 'active'))))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'duplicate_event_ignored','result':deepcopy(prior['result']),'idempotent':True}
   dup=next((x for x in s['candidates'] if x.get('semantic_key')==semantic and x.get('state') in {'active','deferred','awaiting_timing_window','awaiting_prerequisite','requires_operator_review'}),None)
   overlap_row=next((x for x in s['candidates'] if overlap and x.get('semantic_overlap_key')==overlap and x.get('purpose_categories')==sorted(purposes) and x.get('state')=='active'),None)
   if dup or overlap_row: result={'status':'duplicate_candidate_ignored','candidate_id':(dup or overlap_row)['candidate_id']}
   else:
    now=self.clock();cid=f'communication-candidate-{semantic[:24]}';row={'candidate_id':cid,'semantic_key':semantic,'signal_ids':ids,'purpose_categories':sorted(purposes),'source_categories':sorted({c for i in ids for c in known[i].get('source_categories',[])}),'relevance':max(known[i].get('relevance',0) for i in ids),'importance':max(known[i].get('importance',0) for i in ids),'urgency':max(known[i].get('urgency',0) for i in ids),'uncertainty':max(known[i].get('uncertainty',0) for i in ids),'sensitivity':max(known[i].get('sensitivity',0) for i in ids),'interruption_cost':max(known[i].get('interruption_cost',0) for i in ids),'timing_window':timing_window,'delay_compatible':all(known[i].get('delay_compatible') for i in ids),'recovery_compatible':recovery,'continuity_relevance':max(known[i].get('continuity_relevance',0) for i in ids),'curiosity_classification':curiosity_classification,'operator_review_required':review,'semantic_overlap_key':overlap,'confidence':min(known[i].get('confidence',0) for i in ids),'state':state,'created_at':now,'updated_at':now,'history':[{'change':'registered','occurred_at':now,'content_free':True}],'communication_session_id':'','communication_outcome_id':'','conversation_proposal_id':'','initiative_id':'','message_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''};s['candidates'].append(row);result={'status':'communication_candidate_registered','candidate_id':cid,'state':state}
   now=self.clock();s['processed_events'].append({'event_id':event_id,'event_digest':_digest(event_id),'occurred_at':now,'result':deepcopy(result),'content_free':True});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':result['status'],'result':result,'idempotent':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['candidates']:counts[x.get('state')]=counts.get(x.get('state'),0)+1
  keys=('candidate_id','signal_ids','purpose_categories','source_categories','relevance','importance','urgency','uncertainty','sensitivity','interruption_cost','timing_window','delay_compatible','recovery_compatible','continuity_relevance','curiosity_classification','operator_review_required','semantic_overlap_key','confidence','state','communication_session_id','communication_outcome_id','conversation_proposal_id','initiative_id','message_id','notification_id','approval_id','authorization_id','action_id')
  return {'ok':True,'contract_version':CONTRACT_VERSION,'candidate_count':len(s['candidates']),'state_counts':counts,'recent_candidates':[{k:x.get(k) for k in keys} for x in s['candidates'][-24:]],'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'message_text_exposed':False,'reflection_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_mutated':False,'runtime_mutated':False}
def build_reflective_communication_candidate_inspection(runtime_root=None): return ReflectiveCommunicationCandidateStore(runtime_root).inspection_summary()
