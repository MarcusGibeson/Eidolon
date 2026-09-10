from __future__ import annotations
"""v1133.4 deterministic internally generated goal acceptance-versus-deferral arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from internally_generated_goal_deliberation_sessions import InternallyGeneratedGoalDeliberationSessionStore
CONTRACT_VERSION='v1133.4'; SCHEMA_VERSION='1'
OUTCOMES={'goal_acceptance_recommended','goal_comparison_recommended','goal_revision_recommended','goal_suspension_recommended','goal_retirement_recommended','deliberate_no_goal','defer_for_recovery','defer_for_focus','defer_for_cognitive_budget','defer_for_operator_review','await_prerequisite','await_goal_conflict_review','suppress_false_urgency','suppress_low_value_goal','suppress_infeasible_goal','unresolved'}
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=200): return ' '.join(str(v or '').split())[:n]
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'outcomes':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_activate_goal':False,'can_create_plan':False,'can_create_initiative':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class InternallyGeneratedGoalArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'internally_generated_goal_arbitration.json'; self.clock=clock or _now; self.sessions=InternallyGeneratedGoalDeliberationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,feasibility:float=0.0,value_support:float=0.0,risk_acceptability:float=0.0,priority_coherence:float=0.0,deliberate_no_goal:bool=False,revision_requested:bool=False,suspension_requested:bool=False,retirement_requested:bool=False,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,conflict_review_ready:bool=True):
  row=next((x for x in self.sessions.snapshot().get('sessions',[]) if x.get('session_id')==session_id),None)
  if not row: raise ValueError('goal deliberation session required')
  clamp=lambda x:max(0.,min(float(x),1.)); feas,val,risk,coh=map(clamp,(feasibility,value_support,risk_acceptability,priority_coherence)); pause=row.get('pause_reason',''); outcome='unresolved'; reason='insufficient_structural_support'
  if deliberate_no_goal: outcome='deliberate_no_goal'; reason='bounded_no_goal_selected'
  elif pause=='operator_review_required' and not operator_review_ready: outcome='defer_for_operator_review'; reason=pause
  elif pause=='prerequisite_pending' or not prerequisites_satisfied: outcome='await_prerequisite'; reason='prerequisite_pending'
  elif pause=='recovery_constraint' or not recovery_ready: outcome='defer_for_recovery'; reason='recovery_constraint'
  elif pause=='focus_constraint' or not focus_available: outcome='defer_for_focus'; reason='focus_constraint'
  elif pause=='cognitive_budget_constraint' or not cognitive_budget_available: outcome='defer_for_cognitive_budget'; reason='cognitive_budget_constraint'
  elif pause=='goal_conflict_review_pending' or not conflict_review_ready: outcome='await_goal_conflict_review'; reason='goal_conflict_review_pending'
  elif row.get('urgency',0)>.75 and row.get('importance',0)<.45: outcome='suppress_false_urgency'; reason='urgency_not_supported_by_importance'
  elif val<.35 or row.get('expected_value',0)<.25: outcome='suppress_low_value_goal'; reason='value_below_threshold'
  elif feas<.35 or risk<.35: outcome='suppress_infeasible_goal'; reason='feasibility_or_risk_threshold'
  elif revision_requested: outcome='goal_revision_recommended'; reason='bounded_revision_requested'
  elif suspension_requested: outcome='goal_suspension_recommended'; reason='bounded_suspension_requested'
  elif retirement_requested: outcome='goal_retirement_recommended'; reason='bounded_retirement_requested'
  elif row.get('comparison_candidate_ids') and coh>=.55: outcome='goal_comparison_recommended'; reason='supported_competing_goal_review'
  elif val>=.6 and feas>=.55 and risk>=.5 and coh>=.5: outcome='goal_acceptance_recommended'; reason='supported_goal_candidate'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['outcomes'] if x.get('session_id')==session_id),None)
   if existing: result={'status':'goal_arbitration_outcome_reused','arbitration_id':existing['arbitration_id'],'outcome':existing['outcome']}
   else:
    now=self.clock(); aid=f'goal-arbitration-{session_id.rsplit("-",1)[-1]}'; s['outcomes'].append({'arbitration_id':aid,'session_id':session_id,'candidate_id':row.get('candidate_id'),'comparison_candidate_ids':row.get('comparison_candidate_ids',[]),'signal_ids':row.get('signal_ids',[]),'goal_class':row.get('goal_class'),'scope_digest':row.get('scope_digest',''),'evidence_ids':row.get('evidence_ids',[]),'predecessor_candidate_ids':row.get('predecessor_candidate_ids',[]),'outcome':outcome,'reason_code':reason,'feasibility':round(feas,4),'value_support':round(val,4),'risk_acceptability':round(risk,4),'priority_coherence':round(coh,4),'state':'recorded','created_at':now,'history':[{'change':'arbitrated','occurred_at':now,'content_free':True}],'goal_id':'','plan_id':'','initiative_id':'','message_id':'','approval_id':'','authorization_id':'','action_id':''}); result={'status':'goal_arbitration_recorded','arbitration_id':aid,'outcome':outcome,'reason_code':reason}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False,'provider_contacted':False,'external_action_executed':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['outcomes']: counts[x.get('outcome')]=counts.get(x.get('outcome'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'outcome_count':len(s['outcomes']),'outcome_counts':counts,'recognized_outcomes':sorted(OUTCOMES),'recent_outcomes':deepcopy(s['outcomes'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'goal_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_internally_generated_goal_arbitration_inspection(runtime_root=None): return InternallyGeneratedGoalArbitrationStore(runtime_root).inspection_summary()
