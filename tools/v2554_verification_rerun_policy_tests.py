from conscious_agent.verification_rerun_policy_v2554 import *
def main():
 f={'test':'tools/a.py','ok':False,'timed_out':False}; i=build_rerun_policy(f,{'classification':'intermittent'}); p=build_rerun_policy(f,{'classification':'persistent_failure'}); l=build_rerun_policy(f,{'classification':'intermittent'},reruns_already=1)
 checks=[i['rerun_recommended'],not p['rerun_recommended'],not l['rerun_recommended'],i['max_additional_reruns']==1,i['original_failure_retained'],i['rerun_pass_would_not_erase_failure'],i['required_test_still_required'],not i['failure_erasure_authorized'],not i['required_test_waiver_authorized'],not i['release_authorized'],len(i['policy_digest'])==64]
 print({'suite':'v2554-verification-rerun-policy','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
