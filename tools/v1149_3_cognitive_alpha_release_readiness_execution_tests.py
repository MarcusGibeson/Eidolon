from conscious_agent.cognitive_alpha_release_readiness_execution import *
r=build_cognitive_alpha_release_readiness_execution(); bad=build_cognitive_alpha_release_readiness_execution(confirmation='NO')
checks=[r['contract_version']=='v1149.3',r['readiness_valid'],r['operator_confirmed'],r['execution_count']==5,not r['duplicate_execution_ids'],r['all_operations_simulated'],all(x['status']=='passed' for x in r['executions']),all(x['step_budget']==4 for x in r['executions']),not any(r['authority_boundary'].values()),not bad['operator_confirmed'],bad['execution_count']==0,not r['consciousness_proven']]
print(f"v1149.3: {sum(checks)}/{len(checks)}");raise SystemExit(0 if all(checks) else 1)
