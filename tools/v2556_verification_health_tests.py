from conscious_agent.verification_health_v2556 import *
from conscious_agent.verification_history_v2547 import CONTRACT_VERSION

def rows(p,times=None,timeouts=None):
 times=times or [1]*len(p);timeouts=timeouts or [False]*len(p)
 return [{'contract_version':CONTRACT_VERSION,'ok':p[i],'timed_out':timeouts[i],'elapsed_seconds':times[i]} for i in range(len(p))]
def main():
 a=build_verification_health({'a':rows([1,0,1,0])}); d=build_verification_health({'b':rows([0,0,0,0])}); n=build_verification_health({'c':rows([1,1,1,1])})
 checks=[a['state']=='attention',d['state']=='degraded',n['state']=='nominal',a['raw_test_output_stored'] is False,a['required_tests_waived']==0,not a['test_suppression_authorized'],not a['required_test_waiver_authorized'],not a['release_authorized'],len(a['health_digest'])==64]
 print({'suite':'v2556-verification-health','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
