from conscious_agent.historical_verification_feedback_v2552 import *
from conscious_agent.verification_history_v2547 import CONTRACT_VERSION

def rows(pattern,times=None,timeouts=None):
    times=times or [1]*len(pattern);timeouts=timeouts or [False]*len(pattern)
    return [{'contract_version':CONTRACT_VERSION,'ok':pattern[i],'timed_out':timeouts[i],'elapsed_seconds':times[i]} for i in range(len(pattern))]
def main():
    hist={'tools/a.py':rows([1,0,1,0]),'tools/b.py':rows([1,1,1,1,1,1,1,1],[1,1,1,1,2,2,2,2]),'tools/c.py':rows([1,1,1,1])}
    out=build_historical_verification_feedback(hist)
    tests={r['test'] for r in out['concerns']}
    checks=[out['status']=='attention_required',out['concern_count']==2,'tools/a.py' in tests,'tools/b.py' in tests,'tools/c.py' not in tests,out['intermittent_count']==1,out['performance_regression_count']==1,out['required_tests_waived']==0,out['raw_test_output_stored'] is False,out['test_suppression_authorized'] is False,out['timeout_change_authorized'] is False,len(out['feedback_digest'])==64]
    print({'suite':'v2552-historical-verification-feedback','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
