from __future__ import annotations
import hashlib, json, shutil, sys, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from python_cli_implementation_checkpoint import run_or_resume_python_cli_implementation_checkpoint
from selected_project_apply import (
 create_or_resume_apply_request, authorize_and_apply_selected_project,
 create_or_resume_rollback_request, authorize_and_rollback_selected_project,
 recover_interrupted_selected_project_apply, public_rollback_record,
 _result_path, _rollback_result_path,
)
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
def sig(root):
 h=hashlib.sha256()
 for p in sorted(root.rglob('*')):
  if p.is_file(): h.update(p.relative_to(root).as_posix().encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()
def provider(calls):
 def gen(prompt):
  calls.append(hashlib.sha256(prompt.encode()).hexdigest()); payload=json.loads(prompt)
  content={'main.py':"import argparse\ndef count_words(text): return len(str(text).split())\ndef main():\n parser=argparse.ArgumentParser()\n parser.add_argument('text',nargs='*')\n args=parser.parse_args()\n print(count_words(' '.join(args.text)))\nif __name__=='__main__': main()\n",'tests/test_main.py':"from main import count_words\nassert count_words('one two')==2\n"}
  ops={'main.py':'modify','tests/test_main.py':'create'}
  return json.dumps({'authority':payload['authority'],'files':[{'path':p,'operation':ops[p],'content':content[p]} for p in payload['planned_paths']]})
 return gen
def prepared(rt,name):
 project=rt/'selected'; (project/'tests').mkdir(parents=True)
 (project/'main.py').write_text("print('old')\n"); (project/'tool.py').write_text('def old(): return 1\n'); (project/'tests/test_tool.py').write_text('assert True\n'); (project/'README.md').write_text('# old\n')
 before=sig(project)
 turn=process_ordinary_chat_development_turn('Build me a Python CLI that counts words',action_projection={'intent':{'category':'action_request'}},session_id=name,project_state={'id':name,'path':str(project)},runtime_root=rt)
 p=turn['proposal']; approval=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision 1.",runtime_root=rt); require(approval['event']=='approval_consumed')
 calls=[]; final=run_or_resume_python_cli_implementation_checkpoint(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],action='retain',runtime_root=rt,provider_generate=provider(calls),python_executable='/usr/bin/python3')
 require(final['ok'] is True,final); require(sig(project)==before); require(len(calls)==1)
 req=create_or_resume_apply_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_implementation_checkpoint_digest=final['implementation_checkpoint_digest'],runtime_root=rt)
 phrase=f"APPLY {p['proposal_id']} REVISION 1 REQUEST {req['apply_request_digest']}"
 applied=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=req['apply_request_digest'],authorization_phrase=phrase,runtime_root=rt)
 require(applied['ok'] is True,applied); require(sig(project)!=before)
 return project,p,req,applied,before,calls
SOURCE_BEFORE=sig(ROOT)
# Explicit rollback needs a third exact authorization and restores byte identity.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-rollback-'))
try:
 project,p,ar,applied,before,calls=prepared(rt,'rollback')
 request=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt)
 require(request['status']=='selected_project_rollback_awaiting_exact_authorization'); require(request['authorization_consumption_count']==0)
 wrong=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=request['rollback_request_digest'],authorization_phrase='ROLLBACK NOW',runtime_root=rt)
 require(wrong['status']=='exact_rollback_authorization_required'); require(sig(project)!=before)
 phrase=f"ROLLBACK {p['proposal_id']} REVISION 1 REQUEST {request['rollback_request_digest']}"
 result=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=request['rollback_request_digest'],authorization_phrase=phrase,runtime_root=rt)
 require(result['ok'] is True,result); require(result['status']=='selected_project_rollback_completed'); require(result['authorization_consumption_count']==1); require(result['rollback_executed'] is True); require(sig(project)==before); require(not (project/'tests/test_main.py').exists())
 resumed=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=request['rollback_request_digest'],authorization_phrase=phrase,runtime_root=rt)
 require(resumed['operation_status']=='resumed'); require(resumed['rollback_result_digest']==result['rollback_result_digest']); require(resumed['authorization_consumption_count']==1)
 pub=public_rollback_record(result); enc=json.dumps(pub); require(str(project) not in enc); require('main.py' not in enc); require(pub['private_path_exposed'] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
# Fully applied interrupted operation seals without another write or authorization.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-recover-applied-'))
try:
 project,p,ar,applied,before,calls=prepared(rt,'recover-applied'); after=sig(project); _result_path(p['proposal_id'],1,rt).unlink()
 recovered=recover_interrupted_selected_project_apply(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=ar['apply_request_digest'],runtime_root=rt)
 require(recovered['status']=='selected_project_apply_completed_recovered'); require(recovered['recovery_performed'] is True); require(recovered['authorization_consumption_count']==1); require(sig(project)==after)
finally: shutil.rmtree(rt,ignore_errors=True)
# Partial/mixed interrupted application automatically restores the prepared rollback snapshot.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-recover-partial-'))
try:
 project,p,ar,applied,before,calls=prepared(rt,'recover-partial'); _result_path(p['proposal_id'],1,rt).unlink(); (project/'main.py').write_text('corrupted partial write\n')
 recovered=recover_interrupted_selected_project_apply(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=ar['apply_request_digest'],runtime_root=rt)
 require(recovered['status']=='interrupted_apply_recovered_by_rollback'); require(recovered['rollback_executed'] is True); require(recovered['selected_project_modified'] is False); require(sig(project)==before)
finally: shutil.rmtree(rt,ignore_errors=True)
# Concurrent exact rollback duplicates consume once and converge.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-rollback-race-'))
try:
 project,p,ar,applied,before,calls=prepared(rt,'rollback-race'); request=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt); phrase=f"ROLLBACK {p['proposal_id']} REVISION 1 REQUEST {request['rollback_request_digest']}"
 barrier=threading.Barrier(6); out=[]; lock=threading.Lock()
 def worker():
  barrier.wait(); x=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=request['rollback_request_digest'],authorization_phrase=phrase,runtime_root=rt)
  with lock: out.append(x)
 ts=[threading.Thread(target=worker) for _ in range(6)]; [t.start() for t in ts]; [t.join(30) for t in ts]
 require(len(out)==6); require(all(x['ok'] is True for x in out)); require(len({x['rollback_result_digest'] for x in out})==1); require(sum(x['operation_status']=='created' for x in out)==1); require(all(x['authorization_consumption_count']==1 for x in out)); require(sig(project)==before)
finally: shutil.rmtree(rt,ignore_errors=True)
# Static integration and immutable source evidence.
dashboard=(ROOT/'conscious_agent/dashboard.py').read_text(errors='ignore'); metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(); verifier=(ROOT/'tools/release_verify.py').read_text()
for route in ('/api/development-campaign/request-selected-project-rollback','/api/development-campaign/rollback-selected-project','/api/development-campaign/recover-selected-project-apply'): require(route in dashboard,route)
require('WORKING_SOURCE_VERSION = "1204.5"' in metadata); require('v1204.3-v1204.5 Selected-Project Rollback Execution and Apply Recovery' in metadata)
require(verifier.count('v1204.5-selected-project-rollback-recovery')==2); require(verifier.count('tools/v1204_3_5_selected_project_rollback_recovery_tests.py')==1)
require('v1204.3-v1204.5' in (ROOT/'README_NEXT_STEPS.md').read_text()); require('v1204.3-v1204.5 Selected-Project Rollback Execution and Apply Recovery' in (ROOT/'README_RELEASE_HISTORY.md').read_text())
require(SOURCE_BEFORE==sig(ROOT))
print(json.dumps({'ok':True,'version':'1204.5','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'exact_rollback_authorization':True,'interrupted_apply_recovery':True,'rollback_execution':True,'release_authorized':False,'authority_granted':False},sort_keys=True))
