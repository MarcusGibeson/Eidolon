from conscious_agent.project_success_contract_v2592 import build_project_success_contract
from conscious_agent.project_outcome_evidence_v2593 import build_project_outcome_evidence
from conscious_agent.project_success_evaluator_v2594 import evaluate_project_success

def main():
 g='d'*64;c=build_project_success_contract(project_id='p',goal_digest=g,criteria=[{'criterion_id':'latency','metric':'latency_ms','comparison':'less_or_equal','target':100},{'criterion_id':'behavior','metric':'behavior_preserved','comparison':'boolean_true','target':True}]);e=build_project_outcome_evidence(project_id='p',goal_digest=g,current_metrics={'latency_ms':95},verification={'passed':True,'behavior_preserved':True});r=evaluate_project_success(c,e);bad=evaluate_project_success(c,{**e,'goal_digest':'e'*64})
 checks=[r['criteria_satisfied'],r['passed_count']==2,r['evidence_complete'],not r['project_completed_automatically'],r['operator_review_required'],bad['status']=='evidence_binding_mismatch',len(r['evaluation_digest'])==64]
 print({'suite':'v2594-project-success-evaluator','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
