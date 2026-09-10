from __future__ import annotations
"""v1134.3 bounded content-free prospective-planning deliberation sessions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_planning_candidates import ProspectivePlanningCandidateStore
CONTRACT_VERSION='v1134.3'; SCHEMA_VERSION='1'
def _now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _clean(v:Any,n=240): return ' '.join(str(v or '').split())[:n]
def _digest(*p:Any): return hashlib.sha256('\x1f'.join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _default(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'sessions':[],'processed_events':[],'revision':0,'updated_at':'','authority_boundary':{'can_activate_goal':False,'can_activate_plan':False,'can_create_initiative':False,'can_browse':False,'can_contact_provider':False,'can_execute':False,'can_modify_files':False,'can_send_message':False,'can_create_notification':False,'can_approve':False,'can_authorize':False,'can_promote':False,'can_certify':False}}
class ProspectivePlanningDeliberationSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/'prospective_planning_deliberation_sessions.json'; self.clock=clock or _now; self.candidates=ProspectivePlanningCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,comparison_candidate_ids:list[str]|None=None,deliberation_budget:int=1,recovery_ready:bool=True,focus_available:bool=True,cognitive_budget_available:bool=True,operator_review_ready:bool=False,prerequisites_satisfied:bool=True,timing_window_open:bool=True,risk_review_ready:bool=True,stop_conditions_satisfied:bool=True):
  allc=self.candidates.snapshot().get('candidates',[]); c=next((x for x in allc if x.get('candidate_id')==candidate_id),None)
  if not c or c.get('state') not in {'active','deferred','awaiting_timing_window','awaiting_prerequisite','requires_operator_review'}: raise ValueError('eligible prospective-planning candidate required')
  compare=list(dict.fromkeys(_clean(x,220) for x in (comparison_candidate_ids or []) if _clean(x,220))); known={x.get('candidate_id') for x in allc}
  if any(x not in known for x in compare): raise ValueError('known comparison candidate lineage required')
  budget=max(1,min(int(deliberation_budget),6)); reason=''
  if c.get('state')=='requires_operator_review' and not operator_review_ready: reason='operator_review_required'
  elif c.get('state')=='awaiting_prerequisite' or not prerequisites_satisfied: reason='prerequisite_pending'
  elif c.get('state')=='awaiting_timing_window' or not timing_window_open: reason='timing_window_pending'
  elif c.get('state')=='deferred' or not recovery_ready: reason='recovery_constraint'
  elif not focus_available: reason='focus_constraint'
  elif not cognitive_budget_available: reason='cognitive_budget_constraint'
  elif not risk_review_ready: reason='risk_review_pending'
  elif not stop_conditions_satisfied: reason='stop_condition_review_pending'
  state='paused' if reason else 'open'
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,**deepcopy(prior['result']),'idempotent':True}
   existing=next((x for x in s['sessions'] if x.get('candidate_id')==candidate_id and x.get('state') in {'open','paused'}),None)
   if existing: result={'status':'planning_deliberation_session_reused','session_id':existing['session_id'],'state':existing['state']}
   else:
    now=self.clock(); structural=_digest(candidate_id,*compare,budget,state,reason,c.get('scope_digest','')); sid=f'planning-deliberation-session-{structural[:24]}'
    s['sessions'].append({'session_id':sid,'candidate_id':candidate_id,'comparison_candidate_ids':compare,'signal_ids':c.get('signal_ids',[]),'source_categories':c.get('source_categories',[]),'goal_ids':c.get('goal_ids',[]),'purpose_categories':c.get('purpose_categories',[]),'plan_class':c.get('plan_class'),'scope_digest':c.get('scope_digest',''),'evidence_ids':c.get('evidence_ids',[]),'predecessor_candidate_ids':c.get('predecessor_candidate_ids',[]),'relevance':c.get('relevance',0),'importance':c.get('importance',0),'urgency':c.get('urgency',0),'uncertainty':c.get('uncertainty',0),'expected_value':c.get('expected_value',0),'estimated_cost':c.get('estimated_cost',0),'estimated_duration':c.get('estimated_duration',0),'risk':c.get('risk',0),'reversibility':c.get('reversibility',0),'time_horizons':c.get('time_horizons',[]),'alternative_ids':c.get('alternative_ids',[]),'counterfactual_ids':c.get('counterfactual_ids',[]),'stop_condition_ids':c.get('stop_condition_ids',[]),'constraint_ids':c.get('constraint_ids',[]),'prerequisite_ids':c.get('prerequisite_ids',[]),'timing_window_id':c.get('timing_window_id',''),'deliberate_no_action_eligible':c.get('deliberate_no_action_eligible',False),'deliberation_budget':budget,'state':state,'pause_reason':reason,'structural_digest':structural,'created_at':now,'updated_at':now,'history':[{'change':'opened' if state=='open' else 'paused_at_open','occurred_at':now,'content_free':True}]}); result={'status':'planning_deliberation_session_opened','session_id':sid,'state':state}
   now=self.clock(); s['processed_events'].append({'event_id':_clean(event_id,180),'occurred_at':now,'result':deepcopy(result)}); s['revision']+=1; s['updated_at']=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {'ok':True,**result,'idempotent':False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s['sessions']: counts[x.get('state')]=counts.get(x.get('state'),0)+1
  return {'ok':True,'contract_version':CONTRACT_VERSION,'session_count':len(s['sessions']),'state_counts':counts,'recent_sessions':deepcopy(s['sessions'][-24:]),'authority_boundary':deepcopy(s['authority_boundary']),'raw_content_exposed':False,'goal_text_exposed':False,'plan_text_exposed':False,'counterfactual_text_exposed':False,'evidence_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'external_action_executed':False}
def build_prospective_planning_deliberation_session_inspection(runtime_root=None): return ProspectivePlanningDeliberationSessionStore(runtime_root).inspection_summary()
