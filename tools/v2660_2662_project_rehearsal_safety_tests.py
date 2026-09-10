import json
from conscious_agent.developer_project_rehearsal_history_v2660 import build_rehearsal_history
from conscious_agent.developer_project_evidence_firewall_v2661 import classify_project_outcome_evidence
from conscious_agent.developer_project_rehearsal_review_v2662 import build_rehearsal_learning_review
checks=[]
h=build_rehearsal_history([{'project_id':'p','project_digest':'a'*64,'simulation_health_state':'nominal','scenario_count':2,'failure_modes':[]},{'project_id':'p','project_digest':'a'*64,'simulation_health_state':'attention','scenario_count':3,'failure_modes':['x']}]);checks += [h['ok'],h['count']==2,h['synthetic_evidence_only'],not h['automatic_strategy_learning_permitted']]
f=classify_project_outcome_evidence({'synthetic_evidence_only':True});checks += [f['evidence_lane']=='synthetic_rehearsal',not f['eligible_for_real_strategy_learning'],f['eligible_for_rehearsal_learning'],not f['synthetic_counts_as_real_success']]
real=classify_project_outcome_evidence({'reviewed_real_outcome':True});checks += [real['evidence_lane']=='reviewed_real_outcome',real['eligible_for_real_strategy_learning']]
r=build_rehearsal_learning_review(h);checks += [r['ok'],r['simulated_failure_mode_count']==1,r['synthetic_evidence_only'],not r['durable_real_strategy_lesson_committed'],not r['real_strategy_weights_mutated']]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
