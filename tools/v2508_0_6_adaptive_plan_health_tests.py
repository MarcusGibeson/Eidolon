from __future__ import annotations
import json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.long_horizon_planning_intelligence import create_long_horizon_plan
from conscious_agent.adaptive_plan_health_v2508 import AdaptivePlanHealthStore,evaluate_plan_health,rank_plan_candidates
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='eidolon-v2508-0-6-') as td:
 root=Path(td);plan=create_long_horizon_plan('Improve system',[{'milestone_code':'m1','tasks':[{'task_code':'t1'}]},{'milestone_code':'m2','depends_on':['m1'],'tasks':[{'task_code':'t2'}]}],runtime_root=root)
 s=AdaptivePlanHealthStore(root);healthy=evaluate_plan_health(plan,[]);req(healthy['health_state']=='healthy','healthy_initial');req(healthy['recommended_disposition']=='continue_current_plan','continue')
 s.record_signal('b1',plan_id=plan['plan_id'],plan_digest=plan['plan_digest'],signal_type='assumption_invalidated',evidence_digest=d('b1'),severity=.9,expected_value_delta=-.4);s.record_signal('b2',plan_id=plan['plan_id'],plan_digest=plan['plan_digest'],signal_type='blocker',evidence_digest=d('b2'),severity=.8,expected_value_delta=-.3)
 review=evaluate_plan_health(plan,s.signals_for(plan['plan_id'],plan['plan_digest']));req(review['health_state']=='replan_required','replan_required');req(review['alternative_should_be_compared'],'compare_alt');req(review['original_objective_preserved'],'objective_preserved');stage=s.stage_review('review',review);req(stage['ok'],'review_staged');req(not stage['plan_modified'],'candidate_only')
 ranking=rank_plan_candidates([{'plan_id':'a','plan_digest':'a'*64,'expected_benefit':.9,'urgency':.6,'confidence':.8,'resource_cost':.3,'operator_priority':.8,'health_score':.8},{'plan_id':'b','plan_digest':'b'*64,'expected_benefit':.4,'urgency':.4,'confidence':.9,'resource_cost':.2,'operator_priority':.4,'health_score':.9}]);req(ranking['leading_plan_id']=='a','ranked');req(not ranking['plans_reprioritized'],'advisory_only');ins=s.inspection_summary();req(ins['signal_count']==2 and ins['review_count']==1,'history');req(not ins['authority_boundary']['can_abandon_plan'],'no_abandon')
print(json.dumps({'ok':True,'contract':'v2508.0-v2508.6','passed':len(checks),'checks':checks},sort_keys=True))
