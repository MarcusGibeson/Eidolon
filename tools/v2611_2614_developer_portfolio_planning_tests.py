from conscious_agent.developer_portfolio_contract_v2611 import *
from conscious_agent.developer_portfolio_scoring_v2612 import *
from conscious_agent.developer_portfolio_diversity_v2613 import *
from conscious_agent.developer_portfolio_review_v2614 import *
from conscious_agent.project_strategy_plan_confidence_v2606 import build_strategy_confidence_annotations

def main():
 c=build_developer_portfolio_candidates([{'project_id':'a','strategy_code':'safe','expected_value':.8,'effort':2,'risk':.2,'reversibility':.9,'operator_priority':.7,'verification_confidence':.8},{'project_id':'b','strategy_code':'risky','expected_value':1,'effort':1,'risk':.9,'reversibility':.2,'operator_priority':.5,'verification_confidence':.4}])
 ann=build_strategy_confidence_annotations({'profiles':[{'strategy_code':'safe','reliability':'reliable'},{'strategy_code':'risky','reliability':'underperforming'}]},{'profiles':[{'strategy_code':'safe','calibration':'roughly_calibrated'},{'strategy_code':'risky','calibration':'systematic_overprediction'}]})
 r=score_developer_portfolio(c,ann);d=inspect_portfolio_diversity(c);p=build_portfolio_review_packet(c,r,d)
 checks=[c['candidate_count']==2,not c['automatic_project_selection_permitted'],r['leading_project_id']=='a',not r['automatic_project_selection_permitted'],d['candidate_set_modified'] is False,p['operator_selection_required'],not p['project_selected'],not p['campaign_started'],not p['authority_granted']]
 print({'suite':'v2611-v2614-developer-portfolio-planning','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
