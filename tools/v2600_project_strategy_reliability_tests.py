from conscious_agent.project_strategy_reliability_v2600 import build_project_strategy_reliability

def main():
 rows=[{'strategy_code':'a','criteria_satisfied':True,'evidence_complete':True,'failed_required_criteria':[]} for _ in range(4)]+[{'strategy_code':'b','criteria_satisfied':False,'evidence_complete':True,'failed_required_criteria':['latency']} for _ in range(4)]
 r=build_project_strategy_reliability(rows);m={x['strategy_code']:x for x in r['profiles']};checks=[m['a']['reliability']=='reliable',m['b']['reliability']=='underperforming',m['b']['recurring_failed_criteria'][0]['criterion_id']=='latency',not r['strategy_policy_mutated'],not r['automatic_strategy_selection_permitted'],r['raw_content_stored'] is False,len(r['profile_digest'])==64]
 print({'suite':'v2600-project-strategy-reliability','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
