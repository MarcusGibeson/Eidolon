from __future__ import annotations
"""v1130.4 deterministic inquiry proceed-versus-defer arbitration; outcomes never perform inquiry."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from genuine_inquiry_deliberation_sessions import GenuineInquiryDeliberationSessionStore
CONTRACT_VERSION='v1130.4'; SCHEMA_VERSION='1'
OUTCOMES={'internal_review_eligible','clarification_eligible','bounded_inquiry_eligible','deliberate_no_inquiry','defer_for_recovery','defer_for_focus','defer_for_cognitive_budget','defer_for_operator_review','await_prerequisite','suppress_false_pressure','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_browse':False,'can_contact_provider':False,'can_generate_question_text':False,'can_send_message':False,'can_create_notification':False,'can_mutate_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False,'can_promote':False,'can_certify':False}}
class GenuineInquiryArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'genuine_inquiry_arbitration.json'; self.clock=clock or _now; self.sessions=GenuineInquiryDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,relevance:float=0.0,importance:float=0.0,uncertainty:float=1.0,evidence_sufficiency:float=0.0,deliberate_no_inquiry:bool=False,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,false_pressure:bool=False):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('inquiry deliberation session required')
  rel=max(0.,min(float(relevance),1.)); imp=max(0.,min(float(importance),1.)); unc=max(0.,min(float(uncertainty),1.)); ev=max(0.,min(float(evidence_sufficiency),1.)); pause=row.get('pause_reason',''); purposes=set(row.get('purpose_categories',[])); outcome='unresolved'; reason='insufficient_structural_support'
  if deliberate_no_inquiry: outcome='deliberate_no_inquiry'; reason='bounded_no_inquiry_selected'
  elif false_pressure: outcome='suppress_false_pressure'; reason='novelty_or_false_urgency'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='focus_constraint' or not focus_available: outcome='defer_for_focus'; reason='focus_constraint'
  elif pause=='cognitive_budget_constraint' or not cognitive_budget_available: outcome='defer_for_cognitive_budget'; reason='cognitive_budget_constraint'
  elif rel>=.6 and imp>=.45 and unc>=.25:
   if 'resolve_uncertainty' in purposes: outcome='clarification_eligible'; reason='clarification_need_supported'
   elif 'reconcile_contradiction' in purposes or 'close_knowledge_gap' in purposes or row.get('inquiry_classification')=='bounded_external_research': outcome='bounded_inquiry_eligible'; reason='bounded_inquiry_supported'
   else: outcome='internal_review_eligible'; reason='internal_review_supported'
  elif ev>=.85 and unc<=.2: outcome='deliberate_no_inquiry'; reason='evidence_already_sufficient'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'inquiry_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock(); aid=f'inquiry-arbitration-{session_id.rsplit("-",1)[-1]}'; s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'signal_ids':row.get('signal_ids',[]),'purpose_categories':row.get('purpose_categories',[]),'source_categories':row.get('source_categories',[]),'outcome':outcome,'reason_code':reason,'relevance':rel,'importance':imp,'uncertainty':unc,'evidence_sufficiency':ev,'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}],'question_id':'','browse_request_id':'','provider_request_id':'','message_id':'','notification_id':'','initiative_id':'','approval_id':'','authorization_id':'','action_id':''}); result={'status':'inquiry_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_mutated':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'question_text_exposed':False,'hidden_reasoning_exposed':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_mutated':False}
def build_genuine_inquiry_arbitration_inspection(runtime_root=None): return GenuineInquiryArbitrationStore(runtime_root).inspection_summary()
