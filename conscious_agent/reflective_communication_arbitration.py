from __future__ import annotations
"""v1129.4 deterministic silence-versus-communication arbitration; outcomes never send."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflective_communication_deliberation_sessions import ReflectiveCommunicationDeliberationSessionStore
CONTRACT_VERSION='v1129.4';SCHEMA_VERSION='1'
OUTCOMES={'communicate_when_eligible','delayed_follow_up','curiosity_question_eligible','clarification_eligible','deliberate_silence','defer_for_interruption','defer_for_timing','defer_for_recovery','defer_for_focus','defer_for_operator_review','await_prerequisite','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_contact_provider':False,'can_generate_message_text':False,'can_send_message':False,'can_create_notification':False,'can_create_initiative':False,'can_approve':False,'can_authorize':False,'can_execute':False}}
class ReflectiveCommunicationArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/'reflective_communication_arbitration.json';self.clock=clock or _now;self.sessions=ReflectiveCommunicationDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,usefulness:float=0.0,urgency:float=0.0,uncertainty:float=1.0,deliberate_silence:bool=False,interruption_permission:bool=False,timing_ready:bool=True,recovery_ready:bool=True,focus_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('communication deliberation session required')
  useful=max(0.,min(float(usefulness),1.)); urgent=max(0.,min(float(urgency),1.)); unc=max(0.,min(float(uncertainty),1.)); outcome='unresolved';reason='insufficient_structural_support';purposes=set(row.get('purpose_categories',[]));pause=row.get('pause_reason','')
  if deliberate_silence: outcome='deliberate_silence';reason='bounded_silence_selected'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review';reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite';reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery';reason='recovery_constraint'
  elif pause=='timing_window_pending' or not timing_ready: outcome='defer_for_timing';reason='timing_window_pending'
  elif pause=='considerate_non_interruption' or ((row.get('user_interrupting') or row.get('active_conversation')) and not interruption_permission): outcome='defer_for_interruption';reason='considerate_non_interruption'
  elif pause=='focus_constraint' or not focus_available: outcome='defer_for_focus';reason='focus_constraint'
  elif useful>=.65 and unc<=.45:
   if 'curiosity_question' in purposes:
    if interruption_permission and row.get('curiosity_classification') not in {'none','weak','novelty_only'}: outcome='curiosity_question_eligible';reason='bounded_curiosity_supported'
    else: outcome='deliberate_silence';reason='curiosity_lacks_interruption_permission'
   elif 'clarification_request' in purposes: outcome='clarification_eligible';reason='clarification_supported'
   elif 'delayed_follow_up' in purposes or (row.get('delay_compatible') and urgent<.7): outcome='delayed_follow_up';reason='delay_preferred_over_interruption'
   else: outcome='communicate_when_eligible';reason='communicative_usefulness_supported'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'communication_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock();aid=f'communication-arbitration-{session_id.rsplit("-",1)[-1]}';s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'signal_ids':row.get('signal_ids',[]),'purpose_categories':row.get('purpose_categories',[]),'outcome':outcome,'reason_code':reason,'usefulness':useful,'urgency':urgent,'uncertainty':unc,'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}],'message_id':'','notification_id':'','initiative_id':'','conversation_proposal_id':''});result={'status':'communication_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock();s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)});s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,**result,'idempotent':False,'message_sent':False,'notification_created':False,'initiative_created':False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'message_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_created':False}
def build_reflective_communication_arbitration_inspection(runtime_root=None): return ReflectiveCommunicationArbitrationStore(runtime_root).inspection_summary()
