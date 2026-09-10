from __future__ import annotations
import concurrent.futures,json,os,time
from v1208_test_support import ROOT,campaign,cleanup,runtime,source_signature
import sys;sys.path.insert(0,str(ROOT/'conscious_agent'))
import python_test_adapter as adapter
from grounded_development_planning import load_grounded_plan
from ordinary_chat_development_campaign import _read_json
from python_test_adapter import _operation_path,_python_candidates,_record_valid,_result_path,_write_operation,run_or_resume_python_tests
START=time.monotonic();CHECKS=[]
def req(v,d=None): CHECKS.append(bool(v)); (_ for _ in ()).throw(AssertionError(d)) if not v else None
before=source_signature();old_system=adapter.platform.system;old_which=adapter.shutil.which;old_env=dict(os.environ)
try:
 adapter.shutil.which=lambda name: f'/path/{name}' if name=='python' else None;adapter.platform.system=lambda:'Linux';rows=_python_candidates('/explicit/python');req(rows[0]==('explicit','/explicit/python'));req(any(s=='path' for s,_ in rows));req(len(rows)<=adapter.MAX_PYTHON_LAUNCH_ATTEMPTS)
 adapter.platform.system=lambda:'Darwin';req(any('homebrew' in v or '/usr/local/bin/python3' in v for _,v in _python_candidates()))
 adapter.platform.system=lambda:'Windows';os.environ['LOCALAPPDATA']=r'C:\FixtureUser\Local';req(any(s=='platform_default' and v.endswith('python.exe') for s,v in _python_candidates()))
 os.environ['EIDOLON_PYTHON_EXECUTABLE']=r'C:\FixturePython\python.exe';req(_python_candidates()[0][0]=='environment')
finally:adapter.platform.system=old_system;adapter.shutil.which=old_which;os.environ.clear();os.environ.update(old_env)
def prepared(rt,p,i,age=0):
 plan=load_grounded_plan(p['proposal_id'],1,runtime_root=rt)
 return _write_operation(_operation_path(p['proposal_id'],1,rt),{'schema_version':adapter.SCHEMA_VERSION,'contract_version':adapter.CONTRACT_VERSION,'phase':'prepared','proposal_id':p['proposal_id'],'proposal_revision':1,'proposal_revision_digest':p['revision_digest'],'planning_digest':plan['planning_digest'],'generation_digest':i['generation_digest'],'workspace_digest':i['workspace_digest'],'attempt_count':1,'recovery_count':0,'updated_at_epoch':time.time()-age,'network_allowed':False,'dependencies_installed':False,'shell_executed':False,'selected_project_modified':False,'source_modified':False,'repair_authorized':False,'apply_authorized':False,'release_authorized':False,'authority_granted':False})
rt=runtime('reliability-shared');old_run=adapter._run_bounded_command
try:
 p,i=campaign(rt,session_id='reliability-shared');calls=[]
 def counted(*a,**k): calls.append(tuple(a[0]));return old_run(*a,**k)
 adapter._run_bounded_command=counted
 def worker(_): return run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt)
 with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: out=list(pool.map(worker,range(12)))
 req(len({x.get('python_test_adapter_digest') for x in out})==1,out);req(sum(x.get('operation_status')=='created' for x in out)==1);req(sum(x.get('operation_status')=='resumed' for x in out)==11);req(len(calls)==5,calls)
 adapter._run_bounded_command=old_run
 op_path=_operation_path(p['proposal_id'],1,rt);result_path=_result_path(p['proposal_id'],1,rt);valid_op=op_path.read_text();valid_result=result_path.read_text()
 result_path.unlink();prepared(rt,p,i);r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(r['status']=='python_test_operation_in_progress');req(not result_path.exists())
 result_path.unlink(missing_ok=True);prepared(rt,p,i,adapter.OPERATION_STALE_SECONDS+5);r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(r['passed']);req(r['operation_recovery_count']==1);op=_read_json(op_path);req(op['phase']=='sealed');req(op['attempt_count']==2);req(op['recovery_count']==1)
 result_path.unlink(missing_ok=True);op=prepared(rt,p,i,100);op['phase']='sealed';op_path.write_text(json.dumps(op));r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(r['status']=='python_test_operation_invalid')
 result_path.unlink(missing_ok=True);op=prepared(rt,p,i,100);_write_operation(op_path,{**{k:v for k,v in op.items() if k!='operation_digest'},'phase':'sealed','result_digest':'f'*64});r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(r['status']=='python_test_result_missing')
 op_path.write_text(valid_op);result_path.write_text(valid_result);raw=json.loads(valid_result);raw['passed']=False;result_path.write_text(json.dumps(raw));blocked=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(blocked['status']=='python_test_adapter_record_invalid');req(not _record_valid(raw))
 op_path.unlink(missing_ok=True);result_path.unlink(missing_ok=True);r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest='0'*64,runtime_root=rt);req(r['status']=='stale_workspace_revision')
finally:adapter._run_bounded_command=old_run;cleanup(rt)
req(source_signature()==before)
print(json.dumps({'ok':True,'version':'1208.8','suite':'python-test-adapter-reliability-cross-platform','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'source_immutable':True,'network_allowed':False,'dependencies_installed':False,'shell_executed':False,'repair_authorized':False},sort_keys=True),flush=True)
os._exit(0)
