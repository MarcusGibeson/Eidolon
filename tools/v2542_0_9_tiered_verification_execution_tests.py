from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.tiered_verification_runtime_v2541 import build_tiered_verification_plan,run_tier1

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);(r/'conscious_agent').mkdir();(r/'tools').mkdir()
  (r/'conscious_agent/__init__.py').write_text('')
  (r/'conscious_agent/x.py').write_text('VALUE=3\n')
  (r/'tools/x_tests.py').write_text('from conscious_agent.x import VALUE\nprint({"ok": VALUE == 3})\n')
  plan=build_tiered_verification_plan(r,['conscious_agent/x.py'])
  checks += [plan['tier1_test_count']==1]
  result=run_tier1(r,['conscious_agent/x.py'],timeout_each=5)
  checks += [result['ok'],result['tier']==1,result['test_count']==1,result['tests'][0]['status']=='passed',len(result['tests'][0]['stdout_sha256'])==64,result['content_free_receipts']]
  checks += [not result['source_mutation_authorized'],not result['network_authorized'],not result['release_authorized']]
  debris=list(r.rglob('__pycache__'))+list(r.rglob('*.pyc')); checks += [not debris]
 passed=sum(bool(x) for x in checks);print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]});raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
