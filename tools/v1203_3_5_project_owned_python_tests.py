from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn,_read_json,_atomic_json
from python_cli_test_execution_checkpoint import run_or_resume_python_cli_with_tests,public_python_cli_test_checkpoint,_path as checkpoint_path
from project_owned_python_tests import execute_or_resume_project_python_tests,_path as tests_path
from isolated_implementation_workspace import _record_path,_workspace_root
start=time.monotonic();checks=[]
def req(v,d=None):
 checks.append(bool(v))
 if not v:raise AssertionError(d)
def sig():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or any(x in {'.git','data','__pycache__','.pytest_cache','.venv','venv'} for x in p.parts) or p.suffix in {'.pyc','.pyo'}:continue
  h.update(p.relative_to(ROOT).as_posix().encode());h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()
def approved(rt):
 r=process_ordinary_chat_development_turn('Build me a Python CLI that counts words',action_projection={'intent':{'category':'action_request'}},session_id='py-tests',runtime_root=rt);req(r['active']);p=r['proposal']
 a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",runtime_root=rt);req(a['event']=='approval_consumed');req(a['approval_consumption_count']==1);return p
def provider(calls,mode='pass'):
 def gen(prompt):
  calls.append(1);q=json.loads(prompt)
  test="from tool import count_words\nassert count_words('one two') == 2\n"
  if mode=='fail':test="from tool import count_words\nassert count_words('one two') == 3\n"
  if mode=='network':test="import socket\nfrom tool import count_words\nassert count_words('one') == 1\n"
  c={'main.py':"import argparse\nfrom tool import count_words\np=argparse.ArgumentParser();p.add_argument('text',nargs='*');a=p.parse_args();print(count_words(' '.join(a.text)))\n",'tool.py':"def count_words(text):\n    return len(str(text).split())\n",'tests/test_tool.py':test,'README.md':'# Word counter\n'}
  return json.dumps({'authority':q['authority'],'files':[{'path':x,'operation':'create','content':c[x]} for x in q['planned_paths']]})
 return gen
before=sig()
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-5-pass-'))
try:
 p=approved(rt);calls=[];r=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));req(r['ok'],r);req(r['status']=='python_cli_tests_ready_for_operator_review');req(r['stage_count']==7);req(r['project_test_summary']['passed']);req(r['project_test_summary']['test_file_count']==1);req(r['project_test_summary']['command_count']==1);req(r['project_test_summary']['passed_result_count']==1);req(len(calls)==1)
 pub=public_python_cli_test_checkpoint(r);encoded=json.dumps(pub,sort_keys=True);req('test_tool.py' not in encoded);req('count_words' not in encoded);req(str(rt) not in encoded);req(not pub['network_allowed']);req(not pub['dependencies_installed']);req(not pub['repair_authorized']);req(not pub['apply_authorized'])
 r2=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));req(r2['operation_status']=='resumed');req(r2['checkpoint_digest']==r['checkpoint_digest']);req(len(calls)==1)
 tr=_read_json(tests_path(p['proposal_id'],1,rt));req(tr['passed']);req(tr['command_count']==1);req('output_digest' in tr['results'][0]);req('test_path_digest' in tr['results'][0]);req('test_tool.py' not in json.dumps(public_python_cli_test_checkpoint(r)))
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-5-fail-'))
try:
 p=approved(rt);calls=[];r=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls,'fail'));req(not r['ok']);req(r['failed_stage']=='project_tests');req(r['status']=='project_python_tests_failed');req(not r.get('repair_authorized',False));req(not checkpoint_path(p['proposal_id'],1,rt).exists());req(len(calls)==1)
 tr=_read_json(tests_path(p['proposal_id'],1,rt));req(tr['passed'] is False);req(tr['results'][0]['exit_class']=='nonzero')
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-5-network-'))
try:
 p=approved(rt);calls=[];r=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls,'network'));req(not r['ok']);req(r['failed_stage']=='project_tests');req(r['status']=='project_test_capability_rejected');req(not tests_path(p['proposal_id'],1,rt).exists())
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-5-stale-'))
try:
 p=approved(rt);calls=[];base=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));req(base['ok'])
 bad=execute_or_resume_project_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_workspace_digest=base['workspace_digest'],runtime_root=rt);req(bad['status']=='stale_proposal_revision')
 bad=execute_or_resume_project_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest='f'*64,runtime_root=rt);req(bad['status']=='stale_workspace_revision')
 record=_read_json(tests_path(p['proposal_id'],1,rt));record['command_count']=99;_atomic_json(tests_path(p['proposal_id'],1,rt),record)
 bad=execute_or_resume_project_python_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=base['workspace_digest'],runtime_root=rt);req(bad['status']=='project_test_record_invalid')
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-5-race-'))
try:
 p=approved(rt);calls=[];out=[];bar=threading.Barrier(6);lock=threading.Lock();gen=provider(calls)
 def worker():
  bar.wait();v=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=gen)
  with lock:out.append(v)
 ts=[threading.Thread(target=worker) for _ in range(6)]
 for t in ts:t.start()
 for t in ts:t.join(30)
 req(len(out)==6);req(all(x.get('ok') for x in out),out);req(len(calls)==1);req(len({x.get('checkpoint_digest') for x in out})==1);req(sum(x.get('operation_status')=='created' for x in out)==1);req(sum(x.get('operation_status')=='resumed' for x in out)==5)
finally:shutil.rmtree(rt,ignore_errors=True)
req(sig()==before)
print(json.dumps({'ok':True,'version':'1203.5','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4),'source_immutable':True,'dependencies_installed':False,'network_allowed':False,'process_spawning_allowed':False,'selected_project_modified':False,'apply_authorized':False,'repair_authorized':False,'release_authorized':False},sort_keys=True))
