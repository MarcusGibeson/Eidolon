from conscious_agent.tiered_verification_runtime_v2541 import run_tiered_verification
from conscious_agent.verification_feedback_v2544 import build_verification_feedback,project_verification_activity
from conscious_agent.developer_verification_evidence_v2545 import build_developer_verification_evidence
import tempfile
from pathlib import Path

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'conscious_agent').mkdir(); (r/'tools').mkdir(); (r/'conscious_agent/__init__.py').write_text('')
        (r/'conscious_agent/x_feature.py').write_text('VALUE=1\n')
        (r/'tools/v2546_x_feature_tests.py').write_text('from conscious_agent.x_feature import VALUE\nraise SystemExit(0 if VALUE==1 else 1)\n')
        vr=run_tiered_verification(r,['conscious_agent/x_feature.py'],through_tier=1,timeout_each_tier1=5)
        f=build_verification_feedback(vr); a=project_verification_activity(f); e=build_developer_verification_evidence(f,candidate_ref='fixture')
        checks += [vr['ok'],f['verification_ok'],a['status']=='passed',e['fast_verification_passed'],e['candidate_ref']=='fixture']
        checks += [not f['release_certified'],not a['release_certified'],not e['release_certified'],not e['install_authorized'],not e['candidate_applied']]
        checks += [len(f['feedback_digest'])==64,len(e['evidence_digest'])==64]
    p=sum(map(bool,checks)); print({'suite':'v2546.9-verification-feedback-alpha','passed':p,'total':len(checks),'ok':p==len(checks)}); raise SystemExit(0 if p==len(checks) else 1)
if __name__=='__main__': main()
