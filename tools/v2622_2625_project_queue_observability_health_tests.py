from conscious_agent.developer_project_queue_observability_v2622 import build_project_queue_observability
from conscious_agent.developer_portfolio_queue_review_v2623 import build_portfolio_to_queue_review
from conscious_agent.developer_project_queue_history_v2624 import build_queue_transition, build_project_queue_history
from conscious_agent.developer_project_queue_health_v2625 import build_project_queue_health
from conscious_agent.developer_project_queue_v2619 import build_project_queue
from conscious_agent.developer_project_readiness_v2620 import evaluate_project_queue_readiness


def run():
    checks=[]
    queue=build_project_queue([
        {'project_id':'p1','project_digest':'a'*64,'status':'selected','operator_priority':.9},
        {'project_id':'p2','project_digest':'b'*64,'status':'blocked','operator_priority':.8,'blockers':['operator']},
    ])
    ready=evaluate_project_queue_readiness(queue)
    obs=build_project_queue_observability(queue,ready)
    checks += [obs['entry_count']==2, obs['ready_count']==1, obs['project_content_stored'] is False, obs['authority_granted'] is False]

    review={'review_digest':'r'*64,'operator_selection_required':True}
    selection={'operator_selection_bound':True,'project_id':'p1','project_digest':'a'*64,'portfolio_review_digest':'r'*64,'selection_digest':'s'*64}
    binding=build_portfolio_to_queue_review(review,selection,queue,ready)
    checks += [binding['ok'] is True,binding['ready'] is True,binding['operator_review_required'] is True,binding['campaign_started'] is False,binding['automatic_project_start_permitted'] is False]
    bad=build_portfolio_to_queue_review({'review_digest':'x'*64},selection,queue,ready)
    checks += [bad['ok'] is False,bad['project_id']=='']

    transition=build_queue_transition({'project_id':'p1','project_digest':'a'*64,'status':'review'},{'project_id':'p1','project_digest':'a'*64,'status':'selected','blockers':[]})
    history=build_project_queue_history([transition])
    checks += [transition['changed'] is True,history['transition_count']==1,history['content_minimized'] is True,history['queue_mutated'] is False]

    health=build_project_queue_health(queue,ready,history)
    checks += [health['state']=='ready_for_operator_review',health['ready_count']==1,health['automatic_project_start_permitted'] is False,health['queue_mutation_permitted'] is False]
    blocked_queue=build_project_queue([{'project_id':'p3','project_digest':'c'*64,'status':'selected','depends_on':['missing']}])
    blocked_ready=evaluate_project_queue_readiness(blocked_queue)
    blocked_health=build_project_queue_health(blocked_queue,blocked_ready,{})
    checks += ['selected_work_not_ready' in blocked_health['concerns'],'selected_work_blocked' in blocked_health['concerns']]

    print(f'passed={sum(bool(x) for x in checks)}/{len(checks)}')
    if not all(checks):
        raise SystemExit(1)

if __name__=='__main__': run()
