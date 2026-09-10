from __future__ import annotations
import json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.long_horizon_planning_intelligence import create_long_horizon_plan,record_task_outcome
from conscious_agent.adaptive_plan_health_v2508 import AdaptivePlanHealthStore,evaluate_plan_health
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='eidolon-v2508-7-9-') as td:
 root=Path(td);plan=create_long_horizon_plan('Long objective',[{'milestone_code':'foundation','tasks':[{'task_code':'one'}]},{'milestone_code':'integration','depends_on':['foundation'],'tasks':[{'task_code':'two'}]}],stop_condition_codes=['value_no_longer_positive'],deferred_alternative_codes=['alternative_b'],runtime_root=root)
 progressed=record_task_outcome(plan['plan_id'],plan['plan_digest'],task_code='one',outcome='completed',evidence_digest=d('done'),runtime_root=root);req(progressed['completed_task_count']==1,'progress_recorded')
 store=AdaptivePlanHealthStore(root);store.record_signal('new',plan_id=progressed['plan_id'],plan_digest=progressed['plan_digest'],signal_type='goal_value_changed',evidence_digest=d('value'),severity=.7,expected_value_delta=-.8)
 review=evaluate_plan_health(progressed,store.signals_for(progressed['plan_id'],progressed['plan_digest']));req(review['expected_value_delta']<0,'value_drop_seen');req(review['completed_work_preserved'],'completed_preserved');req(review['recommended_disposition'] in {'review_plan_assumptions','prepare_replan_candidate'},'adaptive_review');req(not review['plan_modified'],'not_mutated');store.stage_review('stage',review);ins=store.inspection_summary();req(ins['review_count']==1,'durable_review');req(not ins['external_action_executed'],'no_execution');req(not ins['authority_boundary']['can_reprioritize_plan'],'no_auto_reprioritize');req(not ins['provider_contacted'],'no_provider')
print(json.dumps({'ok':True,'checkpoint_version':'2508.9','contract':'Living Adaptive Plans Foundations','passed':len(checks),'total':len(checks),'checks':checks},sort_keys=True))
