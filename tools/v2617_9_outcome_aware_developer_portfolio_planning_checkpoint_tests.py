from pathlib import Path
from conscious_agent.developer_portfolio_checkpoint_v2617 import build_developer_portfolio_review

def main():
 rows=[{'project_id':'reliability','strategy_code':'safe','expected_value':.7,'effort':2,'risk':.2,'reversibility':.9,'operator_priority':.8,'verification_confidence':.9},{'project_id':'speed','strategy_code':'fast','expected_value':.85,'effort':1,'risk':.5,'reversibility':.6,'operator_priority':.5,'verification_confidence':.6}]
 x=build_developer_portfolio_review(rows)
 checks=[x['ok'],len(x['ranking']['ranked_candidates'])==2,x['operator_selection_required'],not x['automatic_project_selection_permitted'],not x['campaign_start_authorized'],not x['source_mutation_authorized'],not x['authority_granted']]
 names=['developer_portfolio_contract_v2611.py','developer_portfolio_scoring_v2612.py','developer_portfolio_diversity_v2613.py','developer_portfolio_review_v2614.py','developer_portfolio_conflicts_v2615.py','developer_portfolio_sensitivity_v2616.py','developer_portfolio_checkpoint_v2617.py']
 checks.append(all((Path('conscious_agent')/n).exists() for n in names))
 print({'suite':'v2617.9-outcome-aware-developer-portfolio-planning-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
