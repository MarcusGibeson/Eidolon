from pathlib import Path
from conscious_agent.developer_project_queue_v2619 import build_project_queue
from conscious_agent.developer_project_readiness_v2620 import evaluate_project_queue_readiness

def main():
 q=build_project_queue([{'project_id':'a','status':'selected','operator_priority':.9},{'project_id':'b','status':'blocked','blockers':['x']}]);r=evaluate_project_queue_readiness(q)
 names=['developer_portfolio_selection_v2618.py','developer_project_queue_v2619.py','developer_project_readiness_v2620.py'];checks=[all((Path('conscious_agent')/n).exists() for n in names),q['entry_count']==2,r['next_ready_project_id']=='a',not r['campaign_started'],not r['queue_mutated'],not r['authority_granted']]
 print({'suite':'v2621.9-developer-project-queue-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
