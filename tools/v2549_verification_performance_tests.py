from conscious_agent.verification_performance_v2549 import *
from conscious_agent.verification_history_v2547 import CONTRACT_VERSION

def rows(vals):return [{'contract_version':CONTRACT_VERSION,'elapsed_seconds':v} for v in vals]
def main():
    stable=assess_duration_drift('s',rows([2,2.1,1.9,2,2,2.1,2,2.2])); reg=assess_duration_drift('r',rows([1,1,1,1,2,2,2,2])); severe=assess_duration_drift('x',rows([1,1,1,1,3,3,3,3])); improved=assess_duration_drift('i',rows([4,4,4,4,2,2,2,2])); short=assess_duration_drift('q',rows([1,1,1]))
    report=assess_history_performance({'r':rows([1,1,1,1,2,2,2,2]),'s':rows([2,2,2,2,2,2,2,2])})
    checks=[stable['status']=='stable',reg['status']=='severe_regression',severe['status']=='severe_regression',improved['status']=='improved',short['status']=='insufficient_history',reg['timeout_changed'] is False,reg['required_test_still_required'] is True,report['regression_count']==1,report['timeouts_changed']==0,len(report['report_digest'])==64]
    print({'suite':'v2549-verification-performance','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
