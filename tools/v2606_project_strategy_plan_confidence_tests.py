from conscious_agent.project_strategy_plan_confidence_v2606 import build_strategy_confidence_annotations

def main():
 r={'profiles':[{'strategy_code':'bad','reliability':'underperforming'},{'strategy_code':'good','reliability':'reliable'}]};c={'profiles':[{'strategy_code':'bad','calibration':'systematic_overprediction'},{'strategy_code':'good','calibration':'roughly_calibrated'}]};x=build_strategy_confidence_annotations(r,c);m={a['strategy_code']:a for a in x['annotations']};checks=[m['bad']['confidence_factor']<.6,m['good']['confidence_factor']>1,not x['automatic_plan_reprioritization_permitted'],x['operator_priority_unchanged'],not x['plan_mutation_performed'],len(x['annotation_digest'])==64]
 print({'suite':'v2606-project-strategy-plan-confidence','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
