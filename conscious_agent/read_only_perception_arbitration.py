from __future__ import annotations
"""v1131.4 deterministic read-only perception selection-versus-deferral arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from read_only_perception_deliberation_sessions import ReadOnlyPerceptionDeliberationSessionStore
CONTRACT_VERSION='v1131.4'; SCHEMA_VERSION='1'
OUTCOMES={'structural_review_eligible','failure_review_prioritized','changed_file_review_prioritized','completed_work_review_eligible','project_state_review_eligible','system_event_review_eligible','deliberate_no_perception','defer_for_recovery','defer_for_focus','defer_for_cognitive_budget','defer_for_conversation_sensitivity','defer_for_operator_review','await_prerequisite','suppress_false_priority','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_read_raw_file_content':False,'can_browse':False,'can_contact_provider':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_create_notification':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class ReadOnlyPerceptionArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'read_only_perception_arbitration.json'; self.clock=clock or _now; self.sessions=ReadOnlyPerceptionDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,relevance:float=0.0,importance:float=0.0,uncertainty:float=1.0,evidence_sufficiency:float=0.0,deliberate_no_perception:bool=False,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,conversation_sensitivity_clear:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,false_priority:bool=False):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('perception deliberation session required')
  clamp=lambda x:max(0.,min(float(x),1.)); rel,imp,unc,ev=map(clamp,(relevance,importance,uncertainty,evidence_sufficiency)); pause=row.get('pause_reason',''); categories=set(row.get('categories',[])); outcome='unresolved'; reason='insufficient_structural_support'
  if deliberate_no_perception: outcome='deliberate_no_perception'; reason='bounded_no_perception_selected'
  elif false_priority: outcome='suppress_false_priority'; reason='novelty_or_false_priority'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='focus_constraint' or not focus_available: outcome='defer_for_focus'; reason='focus_constraint'
  elif pause=='cognitive_budget_constraint' or not cognitive_budget_available: outcome='defer_for_cognitive_budget'; reason='cognitive_budget_constraint'
  elif pause=='conversation_sensitivity_constraint' or not conversation_sensitivity_clear: outcome='defer_for_conversation_sensitivity'; reason='conversation_sensitivity_constraint'
  elif rel>=.55 and imp>=.45:
   if 'failure' in categories: outcome='failure_review_prioritized'; reason='failure_structurally_prioritized'
   elif 'changed_file' in categories: outcome='changed_file_review_prioritized'; reason='change_structurally_prioritized'
   elif 'completed_work' in categories: outcome='completed_work_review_eligible'; reason='completion_review_supported'
   elif 'project_state' in categories: outcome='project_state_review_eligible'; reason='project_state_review_supported'
   elif 'system_event' in categories: outcome='system_event_review_eligible'; reason='system_event_review_supported'
   else: outcome='structural_review_eligible'; reason='bounded_structural_review_supported'
  elif ev>=.85 and unc<=.2: outcome='deliberate_no_perception'; reason='evidence_already_sufficient'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'perception_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock(); aid=f'perception-arbitration-{session_id.rsplit("-",1)[-1]}'; s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'signal_ids':row.get('signal_ids',[]),'categories':row.get('categories',[]),'perception_purpose':row.get('perception_purpose'),'scope_digest':row.get('scope_digest',''),'outcome':outcome,'reason_code':reason,'relevance':round(rel,4),'importance':round(imp,4),'uncertainty':round(unc,4),'evidence_sufficiency':round(ev,4),'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}],'raw_file_read_id':'','filesystem_action_id':'','inquiry_candidate_id':'','message_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''}); result={'status':'perception_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'filesystem_modified':False,'browser_contacted':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_file_content_exposed':False,'raw_event_payload_exposed':False,'hidden_reasoning_exposed':False,'filesystem_modified':False,'browser_contacted':False,'provider_contacted':False,'external_action_executed':False}
def build_read_only_perception_arbitration_inspection(runtime_root=None): return ReadOnlyPerceptionArbitrationStore(runtime_root).inspection_summary()
