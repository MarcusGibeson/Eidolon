from __future__ import annotations
import json,time,os
from v1208_test_support import ROOT,campaign,cleanup,runtime,source_signature
import sys;sys.path.insert(0,str(ROOT/'conscious_agent'))
from python_test_adapter import _operation_path,_result_path,public_python_test_result,run_or_resume_python_tests
START=time.monotonic();CHECKS=[]
def req(v,d=None): CHECKS.append(bool(v)); (_ for _ in ()).throw(AssertionError(d)) if not v else None
before=source_signature()
rt=runtime('foundations-unittest')
try:
 calls=[];p,i=campaign(rt,calls=calls,session_id='foundations-unittest');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(r['ok']);req(r['passed'],r);req(r['status']=='python_test_adapter_passed');req(r['runner']=='unittest');req(r['python_executed']);req(r['syntax_file_count']==3);req(r['test_file_count']==1);req(r['command_count']==4);req(r['passed_command_count']==4);req(r['cleanup_confirmed']);req(not r['network_allowed']);req(not r['dependencies_installed']);req(not r['shell_executed']);req(not r['repair_authorized']);req(_result_path(p['proposal_id'],1,rt).is_file());req(_operation_path(p['proposal_id'],1,rt).is_file())
 r2=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(r2['operation_status']=='resumed');req(r2['python_test_adapter_digest']==r['python_test_adapter_digest']);req(len(calls)==1)
 pub=public_python_test_result(r);enc=json.dumps(pub,sort_keys=True);req(pub['private_path_exposed'] is False);req(pub['private_content_exposed'] is False);req(pub['raw_output_exposed'] is False);req(str(rt) not in enc);req('tests/test_tool.py' not in enc);req('count_words' not in enc)
finally:cleanup(rt)
rt=runtime('foundations-pytest')
try:
 p,i=campaign(rt,mode='pytest',session_id='foundations-pytest');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(r['passed'],r);req(r['runner']=='pytest');req(r['pytest_available']);req(r['command_results'][-1]['phase']=='tests')
finally:cleanup(rt)
rt=runtime('foundations-fail')
try:
 p,i=campaign(rt,mode='fail',session_id='foundations-fail');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(r['ok']);req(not r['passed']);req(r['outcome_class']=='tests_failed');req(not r['repair_authorized']);req(not r['apply_authorized'])
finally:cleanup(rt)
rt=runtime('foundations-network')
try:
 p,i=campaign(rt,mode='network',session_id='foundations-network');r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 req(r['status']=='python_test_capability_contract_rejected');req(r['outcome_class']=='contract_rejected');req(not r['python_executed']);req(bool(r['rejected_path_digest']))
finally:cleanup(rt)
req(source_signature()==before)
print(json.dumps({'ok':True,'version':'1208.2','suite':'python-test-adapter-foundations','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'source_immutable':True,'dependencies_installed':False,'network_allowed':False,'shell_executed':False,'repair_authorized':False},sort_keys=True),flush=True)
os._exit(0)
