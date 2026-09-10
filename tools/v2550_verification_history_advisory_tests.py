from conscious_agent.verification_history_advisory_v2550 import *
from conscious_agent.verification_history_v2547 import CONTRACT_VERSION

def rows(pattern,times=None,timeouts=None):
    times=times or [1]*len(pattern); timeouts=timeouts or [False]*len(pattern)
    return [{'contract_version':CONTRACT_VERSION,'ok':pattern[i],'timed_out':timeouts[i],'elapsed_seconds':times[i]} for i in range(len(pattern))]
def main():
    plan={'plan_digest':'a'*64,'tiers':{'1':{'tests':['tools/a.py','tools/b.py']},'2':{'tests':['tools/c.py']}}}
    hist={'tools/a.py':rows([1,0,1,0]),'tools/b.py':rows([0,0,0,0]),'tools/c.py':rows([1,1,1,1,1,1,1,1],[1,1,1,1,2,2,2,2])}
    out=advise_plan(plan,hist); by={r['test']:r for r in out['advisories']}
    checks=[out['selected_test_count']==3,out['removed_tests']==[],out['added_waivers']==[],out['timeouts_changed'] is False,by['tools/a.py']['action']=='run_as_selected_then_rerun_on_failure',by['tools/b.py']['priority']=='critical',by['tools/c.py']['action']=='run_as_selected_and_investigate_duration',all(r['required_test_still_required'] for r in out['advisories']),out['test_suppression_authorized'] is False,out['required_test_waiver_authorized'] is False,len(out['advisory_digest'])==64]
    print({'suite':'v2550-verification-history-advisory','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
