from conscious_agent.verification_flakiness_v2548 import *
from conscious_agent.verification_history_v2547 import CONTRACT_VERSION

def rows(pattern,timeouts=None):
    timeouts=timeouts or [False]*len(pattern)
    return [{'contract_version':CONTRACT_VERSION,'ok':v,'timed_out':timeouts[i],'elapsed_seconds':1.0} for i,v in enumerate(pattern)]
def main():
    a=classify_test_history('a',rows([1,1,1,1])); b=classify_test_history('b',rows([0,0,0,0])); c=classify_test_history('c',rows([1,0,1,0])); d=classify_test_history('d',rows([0,0,1,0],[1,1,0,1])); e=classify_test_history('e',rows([1,0]))
    report=classify_history({'a':rows([1,1,1,1]),'c':rows([1,0,1,0])})
    checks=[a['classification']=='stable_pass',b['classification']=='persistent_failure',c['classification']=='intermittent',d['classification']=='timeout_prone',e['classification']=='insufficient_history',c['required_test_still_required'] is True,c['test_suppression_authorized'] is False,report['intermittent_count']==1,report['required_tests_waived']==0,len(report['report_digest'])==64]
    print({'suite':'v2548-verification-flakiness','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
