import json,tempfile
from conscious_agent.developer_project_simulation_observability_v2656 import persist_project_simulation_observability,build_project_simulation_observability
checks=[]
with tempfile.TemporaryDirectory() as td:
 p=persist_project_simulation_observability(health={'state':'attention','scenario_count':3,'failure_mode_count':1},evidence={'simulation_confidence':'low','failure_modes':['x']},readiness={'eligible_for_operator_start_trial_review':False,'real_verification_still_required':True},runtime_root=td);checks += [p['ok'],p['runtime_only'],not p['project_content_stored']]
 r=build_project_simulation_observability(td);checks += [r['state']=='attention',r['scenario_count']==3,r['failure_mode_count']==1,r['simulation_confidence']=='low',not r['eligible_for_operator_start_trial_review'],r['real_verification_still_required'],not r['authority_granted']]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
