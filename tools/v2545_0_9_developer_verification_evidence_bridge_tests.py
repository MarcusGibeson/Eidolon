from conscious_agent.verification_feedback_v2544 import build_verification_feedback
from conscious_agent.developer_verification_evidence_v2545 import build_developer_verification_evidence

def main():
    checks=[]
    base={'status':'tiered_verification_passed','ok':True,'stopped_after_tier':2,'receipts':[{'tier':0,'ok':True,'status':'tier0_passed'},{'tier':1,'ok':True,'status':'tier1_passed','tests':[]},{'tier':2,'ok':True,'status':'tier2_passed','tests':[]}]}
    f=build_verification_feedback(base); e=build_developer_verification_evidence(f,candidate_ref='candidate-7')
    checks += [e['fast_verification_passed'],e['highest_fast_tier']==2,e['candidate_ref']=='candidate-7',e['developer_guidance']=='continue_supervised_review']
    checks += [not e['release_certified'],not e['install_authorized'],not e['candidate_applied'],not e['approval_granted'],not e['source_mutation_authorized']]
    bad={'status':'tiered_verification_failed','ok':False,'stopped_after_tier':1,'receipts':[{'tier':1,'ok':False,'status':'tier1_failed','tests':[{'test':'tools/fail.py','ok':False,'status':'failed'}]}]}
    be=build_developer_verification_evidence(build_verification_feedback(bad)); checks += [not be['fast_verification_passed'],be['failure_count']==1,be['developer_guidance']=='repair_candidate_before_further_progress']
    p=sum(map(bool,checks)); print({'passed':p,'total':len(checks)}); raise SystemExit(0 if p==len(checks) else 1)
if __name__=='__main__': main()
