import json
from conscious_agent.developer_project_simulation_scenarios_v2649 import build_project_simulation_scenarios
from conscious_agent.developer_project_simulation_health_v2650 import build_project_simulation_health
checks=[]
pre={'ok':True,'checks':{'verification_not_degraded':True,'no_blockers':True},'verification_state':'nominal'};s=build_project_simulation_scenarios(pre);checks += [s['ok'],s['scenario_count']==2,s['includes_adversarial'],not s['automatic_execution_permitted']]
r={'ok':True,'failure_modes':['verification_failure_requires_repair_or_review']};h=build_project_simulation_health(r,s);checks += [h['ok'],h['state']=='attention',h['operator_review_required'],not h['automatic_project_start_permitted'],not h['authority_granted']]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
