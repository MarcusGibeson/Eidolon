from conscious_agent.project_strategy_learning_v2602 import build_project_strategy_learning_candidates

def main():
 r={'profiles':[{'strategy_code':'a','reliability':'underperforming'},{'strategy_code':'b','reliability':'reliable'}]};c={'profiles':[{'strategy_code':'a','calibration':'systematic_overprediction'},{'strategy_code':'b','calibration':'roughly_calibrated'}]};x=build_project_strategy_learning_candidates(r,c);m={z['strategy_code']:z for z in x['candidates']};checks=[m['a']['recommendation']=='review_strategy_before_reuse',m['b']['recommendation']=='retain_strategy_as_supported_option',not x['automatic_strategy_change_permitted'],not x['priority_model_mutated'],not x['development_policy_mutated'],x['operator_review_required'],len(x['learning_digest'])==64]
 print({'suite':'v2602-project-strategy-learning','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
