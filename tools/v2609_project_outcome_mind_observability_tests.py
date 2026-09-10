import tempfile
from conscious_agent.project_outcome_history_v2599 import append_project_outcome_history
from conscious_agent.project_outcome_mind_observability_v2609 import build_project_outcome_mind_observability

def main():
 with tempfile.TemporaryDirectory() as d:
  for i in range(3):append_project_outcome_history({'project_id':f'p{i}','goal_digest':('a'*63)+str(i),'review_digest':('b'*63)+str(i),'criteria_satisfied':False,'evidence_complete':True,'failed_required_criteria':['x']},strategy_code='bad',runtime_root=d)
  x=build_project_outcome_mind_observability(d);checks=[x['state']=='attention',x['project_count']==3,x['underperforming_strategy_count']==1,not x['automatic_strategy_change_permitted'],not x['automatic_plan_reprioritization_permitted'],x['raw_project_content_stored'] is False,not x['authority_granted']]
 print({'suite':'v2609-project-outcome-mind-observability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
