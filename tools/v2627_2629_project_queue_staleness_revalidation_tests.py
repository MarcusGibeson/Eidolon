from conscious_agent.developer_project_queue_v2619 import build_project_queue
from conscious_agent.developer_project_readiness_v2620 import evaluate_project_queue_readiness
from conscious_agent.developer_project_queue_staleness_v2627 import evaluate_project_queue_staleness
from conscious_agent.developer_project_queue_revalidation_v2628 import build_project_queue_revalidation_review
from conscious_agent.developer_project_queue_scheduling_v2629 import build_project_queue_scheduling_advisory

def run():
 checks=[]
 q=build_project_queue([{'project_id':'p1','project_digest':'a'*64,'status':'selected','operator_priority':.9},{'project_id':'p2','project_digest':'b'*64,'status':'selected','operator_priority':.7}]);r=evaluate_project_queue_readiness(q)
 review={'ranked_candidates':[{'project_id':'p1','project_digest':'c'*64},{'project_id':'p2','project_digest':'b'*64}]}
 s=evaluate_project_queue_staleness(q,review)
 checks += [s['stale_count']==1,s['stale_project_ids']==['p1'],s['revalidation_required'] is True,s['queue_mutated'] is False]
 rv=build_project_queue_revalidation_review(q,s,r)
 checks += [rv['review_count']==1,rv['review_rows'][0]['project_id']=='p1',rv['review_rows'][0]['recommended_state']=='review',rv['automatic_queue_mutation_permitted'] is False]
 a=build_project_queue_scheduling_advisory(q,r,s)
 checks += [a['eligible_for_operator_start_review']==['p2'],a['stale_excluded_count']==1,a['operator_start_confirmation_required'] is True,a['automatic_project_start_permitted'] is False]
 clean=evaluate_project_queue_staleness(q,{'ranked_candidates':[{'project_id':'p1','project_digest':'a'*64},{'project_id':'p2','project_digest':'b'*64}]})
 checks += [clean['stale_count']==0,clean['revalidation_required'] is False]
 print(f'passed={sum(bool(x) for x in checks)}/{len(checks)}')
 if not all(checks):raise SystemExit(1)
if __name__=='__main__':run()
