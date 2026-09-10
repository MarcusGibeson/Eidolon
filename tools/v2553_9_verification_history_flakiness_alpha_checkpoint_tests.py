from conscious_agent.verification_history_v2547 import observations_from_tiered_receipt,CONTRACT_VERSION as H
from conscious_agent.verification_flakiness_v2548 import classify_test_history
from conscious_agent.verification_performance_v2549 import assess_duration_drift
from conscious_agent.verification_history_advisory_v2550 import advise_plan
from conscious_agent.historical_verification_feedback_v2552 import build_historical_verification_feedback

def rows(pattern,times=None):
    times=times or [1]*len(pattern)
    return [{'contract_version':H,'ok':pattern[i],'timed_out':False,'elapsed_seconds':times[i]} for i in range(len(pattern))]
def main():
    receipt={'status':'tiered_verification_failed','receipt_digest':'a'*64,'receipts':[{'tier':1,'tests':[{'test':'tools/a.py','ok':False,'status':'completed','timed_out':False,'elapsed_seconds':2.0}]}]}
    obs=observations_from_tiered_receipt(receipt)
    hist={'tools/a.py':rows([1,0,1,0]),'tools/b.py':rows([1,1,1,1,1,1,1,1],[1,1,1,1,2,2,2,2])}
    flaky=classify_test_history('tools/a.py',hist['tools/a.py']); perf=assess_duration_drift('tools/b.py',hist['tools/b.py'])
    plan={'plan_digest':'b'*64,'tiers':{'1':{'tests':['tools/a.py']},'2':{'tests':['tools/b.py']}}}; adv=advise_plan(plan,hist); feed=build_historical_verification_feedback(hist)
    checks=[len(obs)==1,flaky['classification']=='intermittent',perf['status']=='severe_regression',adv['selected_test_count']==2,adv['removed_tests']==[],adv['added_waivers']==[],feed['concern_count']==2,feed['required_tests_waived']==0,feed['raw_test_output_stored'] is False,not feed['release_authorized'],not feed['certification_authorized'],not feed['independent_authority_granted']]
    print({'suite':'v2553.9-verification-history-flakiness-alpha','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
