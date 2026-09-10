from pathlib import Path
import tempfile
from conscious_agent.coverage_aware_verification_plan_v2564 import build_coverage_aware_verification_plan

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);(r/'conscious_agent').mkdir();(r/'tools').mkdir()
  (r/'conscious_agent'/'special_signal.py').write_text('x=1')
  (r/'tools'/'v1_special_signal_tests.py').write_text('from conscious_agent.special_signal import x')
  out=build_coverage_aware_verification_plan(r,['conscious_agent/special_signal.py'])
  checks=[out['ok'],out['coverage']['confidence']=='strong',out['blind_spots']['blind_spot_count']==0,out['selected_tests_modified'] is False,out['tier1_tests']==out['plan']['tiers']['1']['tests'],out['runs_commands'] is False,not out['test_execution_authorized'],not out['release_authorized'],len(out['record_digest'])==64]
 print({'suite':'v2564-coverage-aware-verification-plan','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
