from conscious_agent.verification_history_v2547 import CONTRACT_VERSION
from conscious_agent.verification_flakiness_v2548 import classify_test_history
from conscious_agent.verification_rerun_policy_v2554 import build_rerun_policy
from conscious_agent.verification_recovery_evidence_v2555 import reconcile_rerun
from conscious_agent.verification_health_v2556 import build_verification_health

def rows(p): return [{'contract_version':CONTRACT_VERSION,'ok':x,'timed_out':False,'elapsed_seconds':1.0} for x in p]
def main():
 hist={'tools/a.py':rows([1,0,1,0])}; cls=classify_test_history('tools/a.py',hist['tools/a.py']); fail={'test':'tools/a.py','ok':False,'timed_out':False}; pol=build_rerun_policy(fail,cls); rec=reconcile_rerun(fail,{'test':'tools/a.py','ok':True},history_classification=cls['classification']); health=build_verification_health(hist)
 checks=[cls['classification']=='intermittent',pol['rerun_recommended'],pol['max_additional_reruns']==1,rec['status']=='intermittent_failure_confirmed_by_rerun',not rec['verification_considered_clean'],rec['original_failure_retained'],health['state']=='attention',health['required_tests_waived']==0,not health['release_authorized'],not health['certification_authorized'],not health['independent_authority_granted']]
 print({'suite':'v2556.9-verification-history-recovery','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
