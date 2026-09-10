from conscious_agent.adaptive_plan_strategy_ranking_v2607 import rank_plan_candidates_with_strategy_evidence

def main():
 rows=[{'plan_id':'a','plan_digest':'a'*64,'strategy_code':'bad','expected_benefit':.8,'urgency':.5,'confidence':.8,'resource_cost':.3,'operator_priority':.5,'health_score':.8},{'plan_id':'b','plan_digest':'b'*64,'strategy_code':'good','expected_benefit':.8,'urgency':.5,'confidence':.8,'resource_cost':.3,'operator_priority':.5,'health_score':.8}];ann={'annotations':[{'strategy_code':'bad','confidence_factor':.5},{'strategy_code':'good','confidence_factor':1.05}]};x=rank_plan_candidates_with_strategy_evidence(rows,ann);checks=[x['leading_plan_id']=='b',x['historical_strategy_evidence_applied'],x['comparison_is_advisory'],not x['plans_reprioritized'],not x['operator_priority_overridden'],not x['plan_mutation_performed'],not x['execution_authorized'],len(x['ranking_digest'])==64]
 print({'suite':'v2607-adaptive-plan-strategy-ranking','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
