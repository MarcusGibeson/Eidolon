from pathlib import Path
import tempfile, os
from conscious_agent.verification_health_trends_v2557 import build_verification_health_trends
from conscious_agent.verification_observability_v2558 import build_verification_observability
from conscious_agent.coverage_aware_verification_plan_v2564 import build_coverage_aware_verification_plan
from conscious_agent.verification_history_v2547 import append_observations, CONTRACT_VERSION
from conscious_agent import dashboard

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);src=r/'src';(src/'conscious_agent').mkdir(parents=True);(src/'tools').mkdir()
  (src/'conscious_agent'/'alpha_observer.py').write_text('x=1')
  (src/'tools'/'v1_alpha_observer_tests.py').write_text('from conscious_agent.alpha_observer import x')
  plan=build_coverage_aware_verification_plan(src,['conscious_agent/alpha_observer.py'])
  checks += [plan['coverage']['confidence']=='strong',plan['blind_spots']['blind_spot_count']==0,plan['selected_tests_modified'] is False,not plan['release_authorized']]
  hp=r/'history.json'; rows=[]
  for i,ok in enumerate([1,1,1,1,0,1,0,1]): rows.append({'contract_version':CONTRACT_VERSION,'test':'tools/check.py','tier':1,'ok':bool(ok),'status':'passed' if ok else 'failed','timed_out':False,'observed_at':str(i),'parent_receipt_digest':'','elapsed_seconds':1.0,'raw_output_stored':False,'observation_digest':f'{i:064x}'})
  append_observations(hp,rows); obs=build_verification_observability(history_path=hp,window_size=4)
  checks += [obs['ok'],obs['health']['state']=='attention',obs['trends']['direction'] in {'worsening','mixed'},obs['authority_boundary']['read_only'],not obs['authority_boundary']['can_suppress_test']]
 html=dashboard.render_cognitive_observability_dashboard();checks += ['Verification health' in html,'/api/cognition/observability/verification' in html]
 print({'suite':'v2565.9-verification-observability-coverage-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
