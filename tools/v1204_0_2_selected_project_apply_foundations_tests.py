from __future__ import annotations
import hashlib, json, shutil, sys, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from python_cli_implementation_checkpoint import run_or_resume_python_cli_implementation_checkpoint
from selected_project_apply import create_or_resume_apply_request, authorize_and_apply_selected_project, public_apply_record, _result_path, _rollback_path
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v));
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
 proposal=turn['proposal']; approval=process_ordinary_chat_development_turn(f"Approve development proposal {proposal['proposal_id']} revision 1.",runtime_root=rt); require(approval['event']=='approval_consumed')
 calls=[]
 final=run_or_resume_python_cli_implementation_checkpoint(proposal['proposal_id'],expected_revision=1,expected_revision_digest=proposal['revision_digest'],action='retain',runtime_root=rt,provider_generate=provider(calls),python_executable='/usr/bin/python3')
 require(final['ok'] is True,final); require(sig(project)==before); require(len(calls)==1)
 request=create_or_resume_apply_request(proposal['proposal_id'],expected_revision=1,expected_revision_digest=proposal['revision_digest'],expected_implementation_checkpoint_digest=final['implementation_checkpoint_digest'],runtime_root=rt)
 require(request['ok'] is True,request); require(request['status']=='selected_project_apply_awaiting_exact_authorization'); require(request['operation_count']==2); require(sig(project)==before)
 return project,proposal,final,request,calls,before
SOURCE_BEFORE=sig(ROOT)
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-basic-'))
try:
 project,p,f,r,c,b=prepared(rt,'basic')
 wrong=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=r['apply_request_digest'],authorization_phrase='apply it',runtime_root=rt)
 require(wrong['status']=='exact_apply_authorization_required'); require(sig(project)==b)
 phrase=f"APPLY {p['proposal_id']} REVISION 1 REQUEST {r['apply_request_digest']}"
 applied=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=r['apply_request_digest'],authorization_phrase=phrase,runtime_root=rt)
 require(applied['ok'] is True,applied); require(applied['status']=='selected_project_apply_completed'); require(applied['authorization_consumption_count']==1); require(applied['applied_count']==2); require(applied['rollback_prepared'] is True); require(applied['selected_project_modified'] is True); require((project/'tests/test_main.py').is_file()); require('argparse' in (project/'main.py').read_text()); require(_rollback_path(p['proposal_id'],1,rt).is_file())
 resumed=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=r['apply_request_digest'],authorization_phrase=phrase,runtime_root=rt)
 require(resumed['operation_status']=='resumed'); require(resumed['apply_result_digest']==applied['apply_result_digest']); require(resumed['authorization_consumption_count']==1)
 pub=public_apply_record(applied); enc=json.dumps(pub); require(str(project) not in enc); require('main.py' not in enc); require(pub['private_path_exposed'] is False); require(pub['rollback_content_exposed'] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
# Snapshot conflict blocks before second authorization is consumed.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-conflict-'))
try:
 project,p,f,r,c,b=prepared(rt,'conflict'); (project/'README.md').write_text('changed externally\n')
 phrase=f"APPLY {p['proposal_id']} REVISION 1 REQUEST {r['apply_request_digest']}"
 blocked=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=r['apply_request_digest'],authorization_phrase=phrase,runtime_root=rt)
 require(blocked['status']=='selected_project_snapshot_changed'); require(not _result_path(p['proposal_id'],1,rt).exists())
finally: shutil.rmtree(rt,ignore_errors=True)
# Concurrent exact duplicates consume one authorization and return one result.
rt=Path(tempfile.mkdtemp(prefix='eid-v1204-race-'))
try:
 project,p,f,r,c,b=prepared(rt,'race'); phrase=f"APPLY {p['proposal_id']} REVISION 1 REQUEST {r['apply_request_digest']}"; barrier=threading.Barrier(6); out=[]; lock=threading.Lock()
 def worker():
  barrier.wait(); x=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=r['apply_request_digest'],authorization_phrase=phrase,runtime_root=rt)
  with lock: out.append(x)
 ts=[threading.Thread(target=worker) for _ in range(6)]; [t.start() for t in ts]; [t.join(30) for t in ts]
 require(len(out)==6); require(all(x['ok'] is True for x in out)); require(len({x['apply_result_digest'] for x in out})==1); require(sum(x['operation_status']=='created' for x in out)==1); require(all(x['authorization_consumption_count']==1 for x in out))
finally: shutil.rmtree(rt,ignore_errors=True)
# Static integration and source immutability.
dashboard=(ROOT/'conscious_agent/dashboard.py').read_text(errors='ignore'); metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(); verifier=(ROOT/'tools/release_verify.py').read_text()
require('/api/development-campaign/request-selected-project-apply' in dashboard); require('/api/development-campaign/apply-selected-project' in dashboard); require('Selected-project apply' in dashboard)
require('WORKING_SOURCE_VERSION = "1204.2"' in metadata); require('v1204.0-v1204.2 Selected-Project Apply Foundations' in metadata)
require(verifier.count('v1204.2-selected-project-apply-foundations')==2); require(verifier.count('tools/v1204_0_2_selected_project_apply_foundations_tests.py')==1)
require('v1204.0-v1204.2' in (ROOT/'README_NEXT_STEPS.md').read_text()); require('v1204.0-v1204.2 Selected-Project Apply Foundations' in (ROOT/'README_RELEASE_HISTORY.md').read_text())
require(SOURCE_BEFORE==sig(ROOT))
print(json.dumps({'ok':True,'version':'1204.2','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'second_exact_authorization':True,'transactional_apply':True,'rollback_prepared':True,'release_authorized':False,'authority_granted':False},sort_keys=True))
