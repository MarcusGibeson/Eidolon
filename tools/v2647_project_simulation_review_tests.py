import json
from conscious_agent.developer_project_simulation_review_v2647 import build_project_simulation_review
rows=[{'synthetic_evidence_only':True,'simulated_status':'success'},{'synthetic_evidence_only':True,'simulated_status':'verification_failure'},{'synthetic_evidence_only':True,'simulated_status':'blocked'}]
r=build_project_simulation_review(rows);checks=[r['ok'],r['scenario_count']==3,r['nominal_path_observed'],len(r['failure_modes'])==2,r['operator_review_required'],not r['automatic_project_start_permitted'],not r['authority_granted']];print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
