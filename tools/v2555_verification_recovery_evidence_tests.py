from conscious_agent.verification_recovery_evidence_v2555 import *
def main():
 o={'test':'tools/a.py','ok':False}; good={'test':'tools/a.py','ok':True}; bad={'test':'tools/a.py','ok':False}
 a=reconcile_rerun(o,good,history_classification='intermittent');b=reconcile_rerun(o,bad,history_classification='intermittent');c=reconcile_rerun(o,None,history_classification='persistent_failure');d=reconcile_rerun(o,good,history_classification='persistent_failure')
 checks=[a['status']=='intermittent_failure_confirmed_by_rerun',b['status']=='failure_reproduced',c['status']=='unresolved_failure',d['status']=='failure_then_pass_requires_review',not a['verification_considered_clean'],a['original_failure_retained'],a['rerun_passed'],not a['failure_erasure_authorized'],not a['required_test_waiver_authorized'],not a['release_authorized'],not a['candidate_applied'],len(a['evidence_digest'])==64]
 print({'suite':'v2555-verification-recovery-evidence','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
