from conscious_agent.developer_portfolio_selection_v2618 import bind_operator_portfolio_selection
from conscious_agent.developer_project_queue_v2619 import build_project_queue
from conscious_agent.developer_project_readiness_v2620 import evaluate_project_queue_readiness

def main():
 review={'operator_selection_required':True,'review_digest':'r'*64,'ranked_candidates':[{'project_id':'a','project_digest':'a'*64}]}
 bad=bind_operator_portfolio_selection(review,project_id='a',project_digest='a'*64,confirm='SELECT b')
 sel=bind_operator_portfolio_selection(review,project_id='a',project_digest='a'*64,confirm='SELECT a')
 q=build_project_queue([{'project_id':'a','project_digest':'a'*64,'status':'selected','operator_priority':.8,'depends_on':['prep']},{'project_id':'b','status':'deferred'}]);r1=evaluate_project_queue_readiness(q);r2=evaluate_project_queue_readiness(q,['prep'])
 checks=[not bad['ok'],sel['ok'],sel['operator_selection_bound'],not sel['campaign_started'],q['entry_count']==2,not q['queue_persisted'],r1['next_ready_project_id']=='',r2['next_ready_project_id']=='a',not r2['campaign_started'],not r2['authority_granted']]
 print({'suite':'v2618-v2620-project-queue-foundations','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
