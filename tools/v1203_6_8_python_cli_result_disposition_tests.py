from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn,_read_json,_atomic_json
from python_cli_test_execution_checkpoint import run_or_resume_python_cli_with_tests
from python_cli_result_disposition import ACTIONS,create_or_resume_python_cli_review_packet,dispose_python_cli_result,public_python_cli_disposition,_packet_path
from isolated_implementation_workspace import _workspace_root
start=time.monotonic();checks=[]
def req(v,d=None):checks.append(bool(v));assert v,d
def sig():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or any(x in {'.git','data','__pycache__','.pytest_cache','.venv','venv'} for x in p.parts) or p.suffix in {'.pyc','.pyo'}:continue
  h.update(p.relative_to(ROOT).as_posix().encode());h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()
def approved(rt):
 r=process_ordinary_chat_development_turn('Build me a Python CLI that counts words',action_projection={'intent':{'category':'action_request'}},session_id='py-disposition',runtime_root=rt);p=r['proposal'];a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision 1.",runtime_root=rt);req(a['event']=='approval_consumed');return p
def provider(calls):
 def gen(prompt):
  calls.append(1);q=json.loads(prompt);c={'main.py':"import argparse\nfrom tool import count_words\np=argparse.ArgumentParser();p.add_argument('text',nargs='*');a=p.parse_args();print(count_words(' '.join(a.text)))\n",'tool.py':"def count_words(text):\n    return len(str(text).split())\n",'tests/test_tool.py':"from tool import count_words\nassert count_words('one two') == 2\n",'README.md':'# Word counter\n'};return json.dumps({'authority':q['authority'],'files':[{'path':x,'operation':'create','content':c[x]} for x in q['planned_paths']]})
 return gen
def setup(rt):
 p=approved(rt);calls=[];cp=run_or_resume_python_cli_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));req(cp['ok']);req(len(calls)==1);packet=create_or_resume_python_cli_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt);req(packet['ok']);return p,cp,packet
before=sig()
for action in sorted(ACTIONS):
 rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-8-'))
 try:
  p,cp,packet=setup(rt);d=dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action=action,runtime_root=rt);req(d['ok']);req(d['action']==action);req(d['consumption_count']==1);req(not d['apply_authorized']);req(not d['repair_authorized']);req(not d['release_authorized'])
  root=_workspace_root(p['proposal_id'],1,cp['generation_digest'],rt);req(root.exists() if action!='discard' else not root.exists())
  same=dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action=action,runtime_root=rt);req(same['operation_status']=='resumed');req(same['consumption_count']==1)
  other='retain' if action!='retain' else 'reject';bad=dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action=other,runtime_root=rt);req(bad['status']=='python_cli_disposition_already_consumed')
  pub=json.dumps(public_python_cli_disposition(d),sort_keys=True);req(str(rt) not in pub);req('main.py' not in pub);req('count_words' not in pub)
 finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-8-stale-'))
try:
 p,cp,packet=setup(rt);req(dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='retain',runtime_root=rt)['status']=='stale_proposal_revision');req(dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest='f'*64,expected_review_packet_digest=packet['review_packet_digest'],action='retain',runtime_root=rt)['status']=='stale_checkpoint_revision');req(dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest='e'*64,action='retain',runtime_root=rt)['status']=='stale_review_packet');req(dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='apply',runtime_root=rt)['status']=='unsupported_python_cli_disposition')
 path=_packet_path(p['proposal_id'],1,rt);obj=_read_json(path);obj['status']='tampered';_atomic_json(path,obj);req(dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='retain',runtime_root=rt)['status']=='python_cli_review_packet_missing_or_invalid')
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-8-race-'))
try:
 p,cp,packet=setup(rt);out=[];bar=threading.Barrier(8);lock=threading.Lock()
 def worker():
  bar.wait();x=dispose_python_cli_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='retain',runtime_root=rt)
  with lock:out.append(x)
 ts=[threading.Thread(target=worker) for _ in range(8)]
 for t in ts:t.start()
 for t in ts:t.join(30)
 req(len(out)==8);req(all(x.get('ok') for x in out));req(sum(x.get('operation_status')=='created' for x in out)==1);req(sum(x.get('operation_status')=='resumed' for x in out)==7);req(len({x.get('disposition_digest') for x in out})==1);req(all(x.get('consumption_count')==1 for x in out))
finally:shutil.rmtree(rt,ignore_errors=True)
release_verify=(ROOT/'tools'/'release_verify.py').read_text()
req('"v1203.2-python-cli-implementation-foundations"' in release_verify.split('SUPPLEMENTAL_RECEIPT_STAGE_NAMES',1)[0])
req('"v1203.5-project-owned-python-tests"' in release_verify.split('SUPPLEMENTAL_RECEIPT_STAGE_NAMES',1)[0])
req('"v1203.8-python-cli-result-disposition"' in release_verify.split('SUPPLEMENTAL_RECEIPT_STAGE_NAMES',1)[0])
req(sig()==before)
print(json.dumps({'ok':True,'version':'1203.8','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4),'source_immutable':True,'selected_project_modified':False,'apply_authorized':False,'repair_authorized':False,'release_authorized':False},sort_keys=True))
