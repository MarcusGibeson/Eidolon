import json
from conscious_agent.developer_project_start_preflight_v2640 import build_project_start_preflight
from conscious_agent.developer_project_start_review_v2641 import build_project_start_review
from conscious_agent.developer_project_start_handoff_v2642 import build_project_start_handoff_candidate
checks=[]
base=dict(project_id='p',project_digest='a'*64,recovery={'ok':True,'queue':{'entries':[{'project_id':'p','project_digest':'a'*64,'blockers':[]}]}},readiness={'ready_project_ids':['p']},staleness={'stale_project_ids':[]},verification_health={'state':'nominal'})
p=build_project_start_preflight(**base);checks += [p['ok'],p['eligible_for_operator_start_review'],not p['automatic_project_start_permitted'],not p['authority_granted']]
r=build_project_start_review(p);h=build_project_start_handoff_candidate(r);checks += [r['eligible'],r['review_only'],not r['project_started'],h['ok'],h['handoff_candidate_only'],not h['project_started']]
bad=build_project_start_preflight(**{**base,'staleness':{'stale_project_ids':['p']}});checks += [not bad['eligible_for_operator_start_review'],not build_project_start_handoff_candidate(build_project_start_review(bad))['ok']]
print(json.dumps({'ok':all(checks),'passed':sum(bool(x) for x in checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
