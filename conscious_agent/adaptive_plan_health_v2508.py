from __future__ import annotations

"""v2508.0-v2508.6 evidence-bound living-plan health and adaptation candidates."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,re
from pathlib import Path
from typing import Any,Callable,Mapping,Sequence
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION='v2508.6';SCHEMA_VERSION='1'
SIGNAL_TYPES=frozenset({'new_evidence','blocker','assumption_invalidated','priority_shift','resource_change','progress_stall','dependency_changed','goal_value_changed'})

def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _code(v,n=120):return re.sub(r'[^a-z0-9_]+','_',str(v or '').strip().lower()).strip('_')[:n]
def _sha(v):
 s=str(v or '').lower();return len(s)==64 and all(c in '0123456789abcdef' for c in s)
def _bounded(v,d=.5):
 try:return round(max(0,min(1,float(v))),4)
 except (TypeError,ValueError):return d
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'signals':[],'reviews':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_signals':2048,'max_reviews':512},'authority_boundary':{'can_modify_plan':False,'can_reprioritize_plan':False,'can_abandon_plan':False,'can_execute_plan':False,'can_override_operator_priority':False,'operator_review_required':True}}
class AdaptivePlanHealthStore:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'adaptive_plan_health_v2508.json';self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def record_signal(self,event_id:str,*,plan_id:str,plan_digest:str,signal_type:str,evidence_digest:str,severity:float=.5,expected_value_delta:float=0.0,signal_code:str=''):
  event_id=str(event_id or '').strip()[:180];plan_id=str(plan_id or '').strip()[:120];kind=str(signal_type or '').strip().lower();code=_code(signal_code or kind)
  if not event_id or not plan_id or not _sha(plan_digest) or kind not in SIGNAL_TYPES or not _sha(evidence_digest):raise ValueError('valid plan signal required')
  try:delta=max(-1,min(1,float(expected_value_delta)))
  except (TypeError,ValueError):delta=0.0
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'plan_signal_replayed','signal_id':prior['signal_id'],'idempotent':True}
   now=self.clock();sid='plan-signal-'+_digest({'event':event_id,'plan':plan_id,'evidence':evidence_digest})[:24];row={'signal_id':sid,'plan_id':plan_id,'plan_digest':plan_digest,'signal_type':kind,'signal_code':code,'severity':_bounded(severity),'expected_value_delta':round(delta,4),'evidence_digest':evidence_digest.lower(),'created_at':now,'content_free':True}
   s['signals']=(s['signals']+[row])[-int(s['controls']['max_signals']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'signal_id':sid,'occurred_at':now,'content_free':True}])[-4096:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':'plan_signal_recorded','signal_id':sid,'idempotent':False,'plan_modified':False}
 def signals_for(self,plan_id:str,plan_digest:str)->list[dict[str,Any]]:return [deepcopy(x) for x in self._load()['signals'] if x.get('plan_id')==plan_id and x.get('plan_digest')==plan_digest]
 def stage_review(self,event_id:str,review:Mapping[str,Any]):
  event_id=str(event_id or '').strip()[:180]
  if not event_id or not isinstance(review,Mapping) or len(str(review.get('review_digest') or ''))!=64:raise ValueError('valid review required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior and prior.get('review_id'):return {'ok':True,'status':'plan_review_replayed','review_id':prior['review_id'],'idempotent':True,'plan_modified':False}
   now=self.clock();rid='adaptive-plan-review-'+_digest({'event':event_id,'review':review['review_digest']})[:24];row={'review_id':rid,'plan_id':str(review.get('plan_id') or ''),'plan_digest':str(review.get('plan_digest') or ''),'health_state':str(review.get('health_state') or ''),'recommended_disposition':str(review.get('recommended_disposition') or ''),'review_digest':str(review['review_digest']),'status':'candidate_only_unapplied','created_at':now,'plan_modified':False}
   s['reviews']=(s['reviews']+[row])[-int(s['controls']['max_reviews']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'review_id':rid,'occurred_at':now,'content_free':True}])[-4096:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {'ok':True,'status':'adaptive_plan_review_staged','review_id':rid,'idempotent':False,'plan_modified':False}
 def inspection_summary(self):
  s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'signal_count':len(s['signals']),'review_count':len(s['reviews']),'recent_reviews':deepcopy(s['reviews'][-32:]),'authority_boundary':deepcopy(s['authority_boundary']),'plan_modified':False,'external_action_executed':False,'provider_contacted':False}

def evaluate_plan_health(plan:Mapping[str,Any],signals:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 if not isinstance(plan,Mapping) or not plan.get('ok') or not _sha(plan.get('plan_digest')):raise ValueError('valid public long-horizon plan required')
 relevant=[x for x in signals if isinstance(x,Mapping) and x.get('plan_id')==plan.get('plan_id') and x.get('plan_digest')==plan.get('plan_digest')]
 blockers=sum(1 for x in relevant if x.get('signal_type') in {'blocker','assumption_invalidated','dependency_changed'} and float(x.get('severity') or 0)>=.5);stalls=sum(1 for x in relevant if x.get('signal_type')=='progress_stall');value_delta=sum(float(x.get('expected_value_delta') or 0) for x in relevant);failed=len(plan.get('failed_strategy_codes') or []);completion=_bounded(plan.get('completion_ratio'),0);paused=bool(plan.get('paused'));cancelled=bool(plan.get('cancelled'))
 risk=min(1,blockers*.25+stalls*.18+min(failed,4)*.10+max(0,-value_delta)*.25);health_score=round(max(0,min(1,.65+.25*completion-.55*risk+.15*max(0,value_delta))),4)
 if cancelled:state='terminal'
 elif blockers>=2 or health_score<.35 or value_delta<=-.75:state='replan_required'
 elif blockers or stalls or health_score<.55 or value_delta<=-.35:state='attention_required'
 elif paused:state='paused'
 else:state='healthy'
 disposition={'terminal':'retain_terminal','replan_required':'prepare_replan_candidate','attention_required':'review_plan_assumptions','paused':'review_resume_conditions','healthy':'continue_current_plan'}[state]
 result={'ok':True,'contract_version':CONTRACT_VERSION,'plan_id':str(plan['plan_id']),'plan_digest':str(plan['plan_digest']),'health_state':state,'health_score':health_score,'completion_ratio':completion,'blocker_count':blockers,'stall_count':stalls,'failed_strategy_count':failed,'expected_value_delta':round(value_delta,4),'recommended_disposition':disposition,'assumptions_should_be_rechecked':bool(blockers or stalls),'alternative_should_be_compared':bool(state=='replan_required' or value_delta<-.25),'original_objective_preserved':bool(plan.get('original_objective_preserved')),'completed_work_preserved':True,'plan_modified':False,'execution_authorized':False,'operator_priority_overridden':False,'content_free':True};result['review_digest']=_digest(result);return result

def rank_plan_candidates(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
 ranked=[]
 for row in rows[:24]:
  if not isinstance(row,Mapping) or not row.get('plan_id'):continue
  benefit=_bounded(row.get('expected_benefit'),.5);urgency=_bounded(row.get('urgency'),.5);confidence=_bounded(row.get('confidence'),.5);cost=_bounded(row.get('resource_cost'),.5);operator_priority=_bounded(row.get('operator_priority'),.5);health=_bounded(row.get('health_score'),.5)
  utility=round(.28*benefit+.20*urgency+.17*confidence+.20*operator_priority+.15*health-.20*cost,4);ranked.append({'plan_id':str(row['plan_id'])[:120],'plan_digest':str(row.get('plan_digest') or '')[:64],'utility':utility,'operator_priority':operator_priority,'source_metrics_only':True})
 ranked.sort(key=lambda x:(x['utility'],x['operator_priority'],x['plan_id']),reverse=True)
 return {'ok':True,'contract_version':CONTRACT_VERSION,'ranked_plans':ranked,'leading_plan_id':ranked[0]['plan_id'] if ranked else '','comparison_is_advisory':True,'plans_reprioritized':False,'operator_priority_overridden':False,'execution_authorized':False,'comparison_digest':_digest(ranked)}

__all__=['CONTRACT_VERSION','SIGNAL_TYPES','AdaptivePlanHealthStore','evaluate_plan_health','rank_plan_candidates']
