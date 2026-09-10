from conscious_agent.developer_project_queue_v2619 import build_project_queue
from conscious_agent.developer_project_readiness_v2620 import evaluate_project_queue_readiness
from conscious_agent.developer_project_queue_observability_v2622 import build_project_queue_observability
from conscious_agent.developer_project_queue_staleness_v2627 import evaluate_project_queue_staleness
from conscious_agent.developer_project_queue_revalidation_v2628 import build_project_queue_revalidation_review
from conscious_agent.developer_project_queue_scheduling_v2629 import build_project_queue_scheduling_advisory
from conscious_agent.api_server import handle_api_get
from conscious_agent import dashboard

def run():
 checks=[]
 q=build_project_queue([{'project_id':'p1','project_digest':'a'*64,'status':'selected','operator_priority':1.0}]);r=evaluate_project_queue_readiness(q);o=build_project_queue_observability(q,r)
 s=evaluate_project_queue_staleness(q,{'ranked_candidates':[{'project_id':'p1','project_digest':'b'*64}]});rv=build_project_queue_revalidation_review(q,s,r);a=build_project_queue_scheduling_advisory(q,r,s)
 checks += [o['ready_count']==1,s['stale_count']==1,rv['operator_review_required'] is True,a['eligible_for_operator_start_review']==[],a['automatic_project_start_permitted'] is False]
 status,payload=handle_api_get('/api/cognition/observability/project-queue');html=dashboard.render_cognitive_observability_dashboard()
 checks += [status==200,(payload.get('data') or payload).get('authority_granted') is False,'Project queue' in html,'automatic project start' in html.lower()]
 print(f'passed={sum(bool(x) for x in checks)}/{len(checks)}')
 if not all(checks):raise SystemExit(1)
if __name__=='__main__':run()
