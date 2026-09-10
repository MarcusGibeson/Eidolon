from conscious_agent.project_outcome_learning_v2595 import build_project_outcome_learning_candidate

def main():
 s=build_project_outcome_learning_candidate({'criteria_satisfied':True,'failed_required_criteria':[]});f=build_project_outcome_learning_candidate({'criteria_satisfied':False,'failed_required_criteria':['latency']})
 checks=[s['candidate_type']=='successful_project_pattern_candidate',f['candidate_type']=='project_failure_pattern_candidate',f['failed_criteria']==['latency'],not s['durable_lesson_committed'],not f['self_model_mutated'],not f['project_goal_completed'],f['operator_review_required'],len(f['candidate_digest'])==64]
 print({'suite':'v2595-project-outcome-learning','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
