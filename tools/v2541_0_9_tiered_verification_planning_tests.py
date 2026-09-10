from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.tiered_verification_runtime_v2541 import build_tiered_verification_plan,run_tier0

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);(r/'conscious_agent').mkdir();(r/'tools').mkdir()
  (r/'conscious_agent/x.py').write_text('x=1\n')
  (r/'tools/x_tests.py').write_text('from conscious_agent import x\nprint({"ok":True})\n')
  plan=build_tiered_verification_plan(r,['conscious_agent/x.py'])
  checks += [plan['ok'],plan['tiers']['0']['syntax_paths']==['conscious_agent/x.py'],plan['tier1_test_count']==1,plan['tiers']['1']['tests']==['tools/x_tests.py'],plan['tiers']['3']['bounded_by_existing_verifiers']]
  checks += [not plan['runs_commands'],not plan['release_authorized'],not plan['source_mutation_authorized']]
  t0=run_tier0(r,['conscious_agent/x.py']);checks += [t0['ok'],t0['check_count']==1,not t0['external_process_spawned']]
  (r/'conscious_agent/bad.py').write_text('def nope(:\n')
  bad=run_tier0(r,['conscious_agent/bad.py']);checks += [not bad['ok'],bad['status']=='tier0_failed']
 passed=sum(bool(x) for x in checks);print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]});raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
