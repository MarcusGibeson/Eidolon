from pathlib import Path

def main():
 names=['project_success_contract_v2592.py','project_outcome_evidence_v2593.py','project_success_evaluator_v2594.py','project_outcome_learning_v2595.py','project_success_review_v2596.py','project_success_observability_v2597.py']
 checks=[all((Path('conscious_agent')/n).exists() for n in names),'architecture_acceptance_to_success_contract' in Path('conscious_agent/project_success_contract_v2592.py').read_text(),'project_completed_automatically' in Path('conscious_agent/project_success_evaluator_v2594.py').read_text(),'automatic_completion_permitted' in Path('conscious_agent/project_success_review_v2596.py').read_text(),'raw_project_content_stored' in Path('conscious_agent/project_success_observability_v2597.py').read_text()]
 print({'suite':'v2598.9-project-success-evaluation-alpha-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
