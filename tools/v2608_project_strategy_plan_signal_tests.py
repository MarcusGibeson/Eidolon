from conscious_agent.project_strategy_plan_signal_v2608 import build_strategy_plan_signal_candidate

def main():
 x=build_strategy_plan_signal_candidate(plan_id='p',plan_digest='a'*64,strategy_code='bad',annotations={'annotations':[{'strategy_code':'bad','confidence_factor':.5}]});checks=[x['candidate_present'],x['signal_type']=='goal_value_changed',x['severity']==.5,x['expected_value_delta']<0,not x['signal_recorded'],not x['plan_modified'],not x['plan_reprioritized'],not x['operator_priority_overridden'],len(x['candidate_digest'])==64]
 print({'suite':'v2608-project-strategy-plan-signal','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
