from conscious_agent.verification_feedback_v2544 import build_verification_feedback,project_verification_activity

def main():
    checks=[]
    r={'status':'tiered_verification_passed','ok':True,'stopped_after_tier':2,'receipts':[{'tier':0,'ok':True,'status':'tier0_passed'},{'tier':1,'ok':True,'status':'tier1_passed','test_count':1,'tests':[{'test':'tools/a_tests.py','ok':True,'status':'completed','stdout_sha256':'a'*64,'stderr_sha256':'b'*64,'elapsed_seconds':1.2}]},{'tier':2,'ok':True,'status':'tier2_passed','test_count':1,'tests':[{'test':'tools/b_tests.py','ok':True,'status':'completed','stdout_sha256':'c'*64,'stderr_sha256':'d'*64,'elapsed_seconds':2.3}]}]}
    f=build_verification_feedback(r); a=project_verification_activity(f)
    checks += [f['verification_ok'],f['failure_count']==0,f['recommendation'].startswith('fast_confidence_complete'),f['measured_test_seconds']==3.5]
    checks += [a['kind']=='verification',a['status']=='passed',not a['release_certified'],not a['authority_granted']]
    bad={'status':'tiered_verification_failed','ok':False,'stopped_after_tier':1,'receipts':[{'tier':0,'ok':True,'status':'tier0_passed'},{'tier':1,'ok':False,'status':'tier1_failed','test_count':1,'tests':[{'test':'tools/fail.py','ok':False,'status':'failed','timed_out':False,'stdout_sha256':'e'*64,'stderr_sha256':'f'*64}]}]}
    b=build_verification_feedback(bad); checks += [not b['verification_ok'],b['failure_count']==1,b['recommendation']=='repair_before_further_verification']
    checks += [not f['source_mutation_authorized'],not f['release_authorized'],not f['certification_authorized']]
    p=sum(map(bool,checks)); print({'passed':p,'total':len(checks)}); raise SystemExit(0 if p==len(checks) else 1)
if __name__=='__main__': main()
