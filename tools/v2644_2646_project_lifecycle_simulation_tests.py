import json
from conscious_agent.developer_project_lifecycle_simulation_v2644 import build_project_lifecycle_simulation
from conscious_agent.developer_project_simulated_execution_v2645 import build_simulated_execution_receipt
from conscious_agent.developer_project_simulated_outcome_v2646 import build_simulated_project_outcome
from conscious_agent.developer_project_simulation_review_v2647 import build_project_simulation_review
checks=[]
p={'eligible_for_operator_start_review':True,'project_id':'p','project_digest':'a'*64,'preflight_digest':'b'*64};s=build_project_lifecycle_simulation(p);checks += [s['ok'],len(s['stages'])==5,not s['tool_execution_authorized'],not s['project_started']]
for scenario,status in [('nominal','simulated_completed'),('verification_failure','simulated_verification_failed'),('blocked_dependency','simulated_blocked')]:
 e=build_simulated_execution_receipt(s,scenario=scenario);o=build_simulated_project_outcome(e,goal_digest='c'*64);checks += [e['status']==status,not e['real_execution_performed'],o['synthetic_evidence_only'],not o['project_completed_automatically']]
print(json.dumps({'ok':all(checks),'passed':sum(bool(x) for x in checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)

