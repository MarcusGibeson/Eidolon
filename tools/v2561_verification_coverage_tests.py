from pathlib import Path
import tempfile
from conscious_agent.verification_coverage_v2561 import assess_verification_coverage

def main():
  with tempfile.TemporaryDirectory() as td:
    r=Path(td);(r/'conscious_agent').mkdir();(r/'tools').mkdir()
    (r/'conscious_agent'/'alpha_feature.py').write_text('x=1')
    (r/'conscious_agent'/'dashboard.py').write_text('x=1')
    (r/'conscious_agent'/'orphan_feature.py').write_text('x=1')
    (r/'tools'/'v1_alpha_tests.py').write_text('from conscious_agent.alpha_feature import x')
    plan={'tiers':{'1':{'tests':['tools/v1_alpha_tests.py']}}}
    out=assess_verification_coverage(r,['conscious_agent/alpha_feature.py','conscious_agent/dashboard.py','conscious_agent/orphan_feature.py'],plan)
    cov={x['path']:x['coverage'] for x in out['coverage']}
    checks=[cov['conscious_agent/alpha_feature.py']=='focused_direct',cov['conscious_agent/dashboard.py']=='integration_only',cov['conscious_agent/orphan_feature.py']=='uncovered',out['confidence']=='weak',out['uncovered_count']==1,out['tests_removed']==0,not out['test_suppression_authorized'],not out['release_authorized'],len(out['coverage_digest'])==64]
  print({'suite':'v2561-verification-coverage','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
