from __future__ import annotations
"""v1134.4 deterministic prospective plan-versus-no-action arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_planning_deliberation_sessions import ProspectivePlanningDeliberationSessionStore
CONTRACT_VERSION='v1134.4'; SCHEMA_VERSION='1'
OUTCOMES={'plan_recommended','alternative_comparison_recommended','counterfactual_review_recommended','plan_revision_recommended','deliberate_no_action','defer_for_recovery','defer_for_focus','defer_for_cognitive_budget','defer_for_operator_review','await_prerequisite','await_timing_window','await_risk_review','await_stop_condition_review','suppress_false_urgency','suppress_low_value_plan','suppress_high_risk_plan','suppress_irreversible_plan','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_activate_goal':False,'can_activate_plan':False,'can_create_initiative':False,'can_browse':False,'can_contact_provider':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_create_notification':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class ProspectivePlanningArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'prospective_planning_arbitration.json'; self.clock=clock or _now; self.sessions=ProspectivePlanningDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,feasibility:float=0.0,value_support:float=0.0,risk_acceptability:float=0.0,reversibility_support:float=0.0,alternative_quality:float=0.0,counterfactual_support:float=0.0,deliberate_no_action:bool=False,revision_requested:bool=False,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,timing_window_open:bool=True,risk_review_ready:bool=True,stop_conditions_satisfied:bool=True):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('prospective-planning deliberation session required')
  clamp=lambda x:max(0.,min(float(x),1.)); feas,val,risk,rev,alt,cf=map(clamp,(feasibility,value_support,risk_acceptability,reversibility_support,alternative_quality,counterfactual_support)); pause=row.get('pause_reason',''); outcome='unresolved'; reason='insufficient_structural_support'
  if deliberate_no_action: outcome='deliberate_no_action'; reason='bounded_no_action_selected'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='timing_window_pending' or not timing_window_open: outcome='await_timing_window'; reason='timing_window_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='focus_constraint' or not focus_available: outcome='defer_for_focus'; reason='focus_constraint'
  elif pause=='cognitive_budget_constraint' or not cognitive_budget_available: outcome='defer_for_cognitive_budget'; reason='cognitive_budget_constraint'
  elif pause=='risk_review_pending' or not risk_review_ready: outcome='await_risk_review'; reason='risk_review_pending'
  elif pause=='stop_condition_review_pending' or not stop_conditions_satisfied: outcome='await_stop_condition_review'; reason='stop_condition_review_pending'
  elif row.get('urgency',0)>.8 and row.get('importance',0)<.45: outcome='suppress_false_urgency'; reason='urgency_not_supported_by_importance'
  elif val<.35 or row.get('expected_value',0)<.25: outcome='suppress_low_value_plan'; reason='value_below_threshold'
  elif risk<.4 or row.get('risk',0)>.85: outcome='suppress_high_risk_plan'; reason='risk_threshold'
  elif rev<.35 or (row.get('reversibility',1)<.2 and not row.get('stop_condition_ids')): outcome='suppress_irreversible_plan'; reason='reversibility_or_stop_condition_threshold'
  elif revision_requested: outcome='plan_revision_recommended'; reason='bounded_revision_requested'
  elif row.get('comparison_candidate_ids') or (row.get('alternative_ids') and alt>=.55): outcome='alternative_comparison_recommended'; reason='supported_alternative_comparison'
  elif row.get('counterfactual_ids') and cf>=.55: outcome='counterfactual_review_recommended'; reason='supported_counterfactual_review'
  elif val>=.6 and feas>=.55 and risk>=.5 and rev>=.45: outcome='plan_recommended'; reason='supported_prospective_plan'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'planning_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock(); aid=f'planning-arbitration-{session_id.rsplit("-",1)[-1]}'; s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'comparison_candidate_ids':row.get('comparison_candidate_ids',[]),'signal_ids':row.get('signal_ids',[]),'goal_ids':row.get('goal_ids',[]),'plan_class':row.get('plan_class'),'scope_digest':row.get('scope_digest',''),'evidence_ids':row.get('evidence_ids',[]),'predecessor_candidate_ids':row.get('predecessor_candidate_ids',[]),'alternative_ids':row.get('alternative_ids',[]),'counterfactual_ids':row.get('counterfactual_ids',[]),'stop_condition_ids':row.get('stop_condition_ids',[]),'constraint_ids':row.get('constraint_ids',[]),'outcome':outcome,'reason_code':reason,'feasibility':round(feas,4),'value_support':round(val,4),'risk_acceptability':round(risk,4),'reversibility_support':round(rev,4),'alternative_quality':round(alt,4),'counterfactual_support':round(cf,4),'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}],'plan_id':'','initiative_id':'','message_id':'','notification_id':'','approval_id':'','authorization_id':'','action_id':''}); result={'status':'planning_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'goal_text_exposed':False,'plan_text_exposed':False,'counterfactual_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_prospective_planning_arbitration_inspection(runtime_root=None): return ProspectivePlanningArbitrationStore(runtime_root).inspection_summary()
