from __future__ import annotations
import concurrent.futures,json,os,threading,time,urllib.error,urllib.request
from http.server import HTTPServer
from v1208_test_support import ROOT,campaign,cleanup,runtime,source_signature
import sys;sys.path.insert(0,str(ROOT/'conscious_agent'))
from dashboard import EidolonDashboardHandler
from isolated_implementation_workspace import _record_path
import ordinary_chat_development_campaign as campaign_module
from ordinary_chat_development_campaign import _approval_path
from python_test_adapter import _operation_path,_result_path,run_or_resume_python_tests
from python_test_adapter_checkpoint import _checkpoint_path,load_python_test_adapter_checkpoint,public_python_test_adapter_checkpoint,seal_or_resume_python_test_adapter_checkpoint
START=time.monotonic();CHECKS=[]
def req(v,d=None): CHECKS.append(bool(v)); (_ for _ in ()).throw(AssertionError(d)) if not v else None
before=source_signature()
def prepare(rt,mode='unittest',session='checkpoint'):
 p,i=campaign(rt,mode=mode,session_id=session);r=run_or_resume_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],runtime_root=rt);req(bool(r.get('python_test_adapter_digest')),r);return p,i,r
def seal(p,i,r,rt): return seal_or_resume_python_test_adapter_checkpoint(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],expected_python_test_adapter_digest=r['python_test_adapter_digest'],runtime_root=rt)
rt=runtime('checkpoint-shared');old_data_dir=campaign_module.DATA_DIR
try:
 p,i,r=prepare(rt,session='checkpoint-shared');checkpoint_path=_checkpoint_path(p['proposal_id'],1,rt);req(_approval_path(p['proposal_id'],1,rt).is_file());req(_record_path(p['proposal_id'],1,rt).is_file());req(_operation_path(p['proposal_id'],1,rt).is_file());req(_result_path(p['proposal_id'],1,rt).is_file())
 c=seal(p,i,r,rt);req(c['ok']);req(c['status']=='python_test_adapter_checkpoint_passed');req(c['stage_count']==8);req(c['tests_passed']);req(c['python_executed']);req(c['runner'] if 'runner' in c else True);req(c['operator_review_required']);req(not c['repair_authorized']);req(not c['apply_authorized']);req(not c['release_authorized']);req(c['content_free']);req(len(c['stage_receipts'])==8);req(c['stage_receipts'][0]['stage']=='proposal_revision');req(c['stage_receipts'][-1]['stage']=='privacy_authority_boundary');req(load_python_test_adapter_checkpoint(p['proposal_id'],1,rt)['checkpoint_digest']==c['checkpoint_digest'])
 resumed=seal(p,i,r,rt);req(resumed['operation_status']=='resumed');req(resumed['checkpoint_digest']==c['checkpoint_digest'])
 pub=public_python_test_adapter_checkpoint(c);encoded=json.dumps(pub,sort_keys=True);req(pub['private_path_exposed'] is False);req(pub['private_content_exposed'] is False);req(pub['raw_output_exposed'] is False);req(pub['python_executable_path_exposed'] is False);req(str(rt) not in encoded);req('tests/test_tool.py' not in encoded);req('count_words' not in encoded)
 checkpoint_path.unlink()
 def worker(_): return seal(p,i,r,rt)
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: rows=list(pool.map(worker,range(8)))
 req(len({x.get('checkpoint_digest') for x in rows})==1,rows);req(sum(x.get('operation_status')=='created' for x in rows)==1);req(sum(x.get('operation_status')=='resumed' for x in rows)==7)
 checkpoint_path.unlink()
 req(seal_or_resume_python_test_adapter_checkpoint(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_workspace_digest=i['workspace_digest'],expected_python_test_adapter_digest=r['python_test_adapter_digest'],runtime_root=rt)['status']=='stale_proposal_revision');req(seal_or_resume_python_test_adapter_checkpoint(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest='f'*64,expected_python_test_adapter_digest=r['python_test_adapter_digest'],runtime_root=rt)['status']=='workspace_record_missing_or_stale');req(seal_or_resume_python_test_adapter_checkpoint(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=i['workspace_digest'],expected_python_test_adapter_digest='e'*64,runtime_root=rt)['status']=='python_operation_result_mismatch')
 cases=((_approval_path(p['proposal_id'],1,rt),'approval_consumed_once',False,'approval_receipt_missing_or_invalid'),(_operation_path(p['proposal_id'],1,rt),'phase','prepared','python_operation_missing_or_invalid'),(_result_path(p['proposal_id'],1,rt),'passed',False,'python_result_missing_or_invalid'),(_record_path(p['proposal_id'],1,rt),'file_count',999,'workspace_record_invalid'))
 for path,field,value,expected in cases:
  checkpoint_path.unlink(missing_ok=True);original=path.read_text(encoding='utf-8');raw=json.loads(original);raw[field]=value;path.write_text(json.dumps(raw),encoding='utf-8');req(seal(p,i,r,rt)['status']==expected);path.write_text(original,encoding='utf-8')
 checkpoint_path.unlink(missing_ok=True);c=seal(p,i,r,rt);raw=json.loads(checkpoint_path.read_text(encoding='utf-8'));raw['stage_count']=99;checkpoint_path.write_text(json.dumps(raw),encoding='utf-8');req(seal(p,i,r,rt)['status']=='python_checkpoint_invalid');checkpoint_path.unlink()
 campaign_module.DATA_DIR=rt;server=HTTPServer(('127.0.0.1',0),EidolonDashboardHandler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  url=f'http://127.0.0.1:{server.server_port}/api/development-campaign/finalize-python-test-checkpoint';body=json.dumps({'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'python_test_adapter_digest':r['python_test_adapter_digest']}).encode();request=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(request,timeout=20) as response: payload=json.loads(response.read())
  req(payload['ok']);req(payload['stage_count']==8);req(bool(payload['checkpoint_digest']))
  stale=json.dumps({'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'python_test_adapter_digest':'f'*64}).encode();request=urllib.request.Request(url,data=stale,headers={'Content-Type':'application/json'},method='POST')
  try: urllib.request.urlopen(request,timeout=20);req(False)
  except urllib.error.HTTPError as error: data=json.loads(error.read());req(error.code==409);req(data['status']=='stale_python_test_checkpoint_request')
 finally: server.shutdown();server.server_close();thread.join(timeout=3)
finally:
 campaign_module.DATA_DIR=old_data_dir;cleanup(rt)
rt=runtime('checkpoint-fail')
try:
 p,i,r=prepare(rt,mode='fail',session='checkpoint-fail');req(not r['passed']);c=seal(p,i,r,rt);req(c['ok']);req(c['status']=='python_test_adapter_checkpoint_failed_review_required');req(not c['tests_passed']);req(c['stage_receipts'][6]['status']=='python_tests_failed_review_required');req(not c['repair_authorized'])
finally:cleanup(rt)
dashboard=(ROOT/'conscious_agent/dashboard.py').read_text(encoding='utf-8');req('/api/development-campaign/python-test' in dashboard);req('/api/development-campaign/finalize-python-test-checkpoint' in dashboard);req('Run Python tests' in dashboard);req('Seal Python test checkpoint' in dashboard)
release=(ROOT/'tools/release_verify.py').read_text(encoding='utf-8');names=('v1208.2-python-test-adapter-foundations','v1208.5-python-project-test-execution','v1208.8-python-test-adapter-reliability','v1208.9-python-test-adapter-checkpoint')
for name in names:req(name in release);req(f'"{name}"' in release.split('QUICK_STAGE_NAMES',1)[1].split('}',1)[0])
metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding='utf-8');req('WORKING_SOURCE_VERSION = "1208.9"' in metadata);req('WORKING_SOURCE_VERSION = "1208.8"' in metadata);req('Python Test Adapter Checkpoint' in (ROOT/'README_NEXT_STEPS.md').read_text(encoding='utf-8'));req('v1208.9' in (ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'));req(not (ROOT/'data'/'development_campaigns').exists());req(source_signature()==before)
print(json.dumps({'ok':True,'version':'1208.9','suite':'python-test-adapter-checkpoint','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'source_immutable':True,'network_allowed':False,'dependencies_installed':False,'shell_executed':False,'operator_review_required':True,'repair_authorized':False,'release_authorized':False},sort_keys=True),flush=True)
os._exit(0)
