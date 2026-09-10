from __future__ import annotations
import json,time,os
from v1208_test_support import ROOT,campaign,cleanup,runtime,source_signature
import sys;sys.path.insert(0,str(ROOT/'conscious_agent'))
import python_test_adapter as adapter
from python_test_adapter import run_or_resume_python_tests
START=time.monotonic();CHECKS=[]
def req(v,d=None): CHECKS.append(bool(v)); (_ for _ in ()).throw(AssertionError(d)) if not v else None
before=source_signature()
rt=runtime('exec-pytest-fail')
try:
 p,i=campaign(rt,mode='pytest_fail',session_id='exec-pytest-fail');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(r['runner']=='pytest');req(r['pytest_available']);req(not r['passed']);req(r['outcome_class']=='tests_failed');req(r['command_results'][-1]['exit_class']=='nonzero')
finally:cleanup(rt)
rt=runtime('exec-timeout');old=adapter.TEST_TIMEOUT_SECONDS
try:
 adapter.TEST_TIMEOUT_SECONDS=0.25;p,i=campaign(rt,mode='timeout',session_id='exec-timeout');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(not r['passed']);req(r['outcome_class']=='test_timeout',r);req(r['command_results'][-1]['exit_class']=='timeout');req(r['cleanup_confirmed'])
finally:adapter.TEST_TIMEOUT_SECONDS=old;cleanup(rt)
rt=runtime('exec-output')
try:
 p,i=campaign(rt,mode='output',session_id='exec-output');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(not r['passed']);req(r['outcome_class']=='test_output_limit',r);req(r['command_results'][-1]['output_limit_exceeded']);req('x'*100 not in json.dumps(r))
finally:cleanup(rt)
rt=runtime('exec-write')
try:
 p,i=campaign(rt,mode='write',session_id='exec-write');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(not r['passed']);req(r['outcome_class']=='tests_failed');req(not (i.get('workspace_path') and False));req(not (ROOT/'forbidden.txt').exists())
finally:cleanup(rt)
rt=runtime('exec-pathlib-write')
try:
 p,i=campaign(rt,mode='pathlib_write',session_id='exec-pathlib-write');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(not r['passed']);req(r['outcome_class']=='tests_failed');req(r['sandbox_backend']=='python-audit-hook');req(r['os_isolation_provided'] is False);req(r['security_boundary']=='language_runtime_policy_not_os_container');req(not list(rt.rglob('forbidden-pathlib.txt')))
finally:cleanup(rt)
rt=runtime('exec-process')
try:
 p,i=campaign(rt,mode='process',session_id='exec-process');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(r['status']=='python_test_capability_contract_rejected');req(not r['python_executed']);req(not r['process_spawning_allowed'])
finally:cleanup(rt)
rt=runtime('exec-pytest-missing')
old_run=adapter._run_bounded_command
try:
 def no_pytest(argv,**kwargs):
  if "find_spec('pytest')" in ' '.join(str(x) for x in argv):
   return {'passed':False,'exit_class':'nonzero','output_digest':'0'*64,'output_bytes':0,'output_limit_exceeded':False,'cleanup_confirmed':True,'duration_ms':1}
  return old_run(argv,**kwargs)
 adapter._run_bounded_command=no_pytest
 p,i=campaign(rt,mode='pytest',session_id='exec-pytest-missing');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt,python_executable=sys.executable)
 req(r['status']=='python_pytest_unavailable',r);req(r['runner']=='pytest');req(not r['pytest_available']);req(not r['passed']);req(not r['dependencies_installed'])
finally:adapter._run_bounded_command=old_run;cleanup(rt)
req(source_signature()==before)
print(json.dumps({'ok':True,'version':'1208.5','suite':'python-project-test-discovery-execution','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'source_immutable':True,'network_allowed':False,'process_spawning_allowed':False,'native_extensions_allowed':False,'dependencies_installed':False},sort_keys=True),flush=True)
os._exit(0)
