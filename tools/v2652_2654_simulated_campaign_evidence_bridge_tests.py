import json
from conscious_agent.developer_project_simulation_evidence_v2652 import build_project_simulation_developer_evidence
from conscious_agent.developer_project_simulation_readiness_v2653 import build_simulation_informed_start_readiness
from conscious_agent.developer_project_simulation_review_packet_v2654 import build_simulation_informed_operator_packet
checks=[]
e=build_project_simulation_developer_evidence(simulation_health={'ok':True,'state':'nominal','scenario_count':3},simulation_review={'ok':True,'failure_modes':[]},project_id='p',project_digest='a'*64);checks += [e['ok'],e['synthetic_evidence_only'],not e['real_verification_substituted'],not e['authority_granted']]
r=build_simulation_informed_start_readiness({'project_id':'p','project_digest':'a'*64,'eligible_for_operator_start_review':True},e);checks += [r['ok'],r['eligible_for_operator_start_trial_review'],r['real_verification_still_required'],not r['automatic_project_start_permitted']]
p=build_simulation_informed_operator_packet(r,e);checks += [p['ok'],p['synthetic_evidence_disclosed'],p['review_only'],not p['start_authorization_issued'],not p['project_started']]
e2=build_project_simulation_developer_evidence(simulation_health={'ok':True,'state':'attention','scenario_count':3},simulation_review={'ok':True,'failure_modes':['x']},project_id='p',project_digest='a'*64);r2=build_simulation_informed_start_readiness({'project_id':'p','project_digest':'a'*64,'eligible_for_operator_start_review':True},e2);checks += [not r2['eligible_for_operator_start_trial_review'],'simulation_requires_attention' in r2['reasons']]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
