from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from grounded_development_planning import create_or_resume_grounded_plan
from python_cli_implementation_foundations import run_or_resume_python_cli_implementation,public_python_cli_checkpoint,_checkpoint_path
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
 r=process_ordinary_chat_development_turn('Build me a Python CLI that counts words',action_projection={'intent':{'category':'action_request'}},session_id='py-cli',runtime_root=rt);req(r['active']);p=r['proposal']
 a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",runtime_root=rt);req(a['event']=='approval_consumed');req(a['approval_consumption_count']==1);return p
def provider(calls,bad=False):
 def gen(prompt):
  calls.append(1);q=json.loads(prompt);c={'main.py':"import argparse\nfrom tool import count_words\np=argparse.ArgumentParser();p.add_argument('text',nargs='*');a=p.parse_args();print(count_words(' '.join(a.text)))\n",'tool.py':"def count_words(text):\n    return len(str(text).split())\n",'tests/test_tool.py':"from tool import count_words\nassert count_words('one two') == 2\n",'README.md':'# Word counter\n'}
  if bad:c['main.py']='def broken(:\n'
  return json.dumps({'authority':q['authority'],'files':[{'path':x,'operation':'create','content':c[x]} for x in q['planned_paths']]})
 return gen
before=sig();rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-py-'))
try:
 p=approved(rt);plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt)
 req(plan['project_kind']=='new_python_cli_project',plan);req([x['relative_path'] for x in plan['file_plan']]==['main.py','tool.py','tests/test_tool.py','README.md']);req([x['adapter'] for x in plan['test_plan']]==['python_syntax','python_cli_smoke'])
 calls=[];r=run_or_resume_python_cli_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));req(r['ok'],r);req(r['status']=='python_cli_implementation_ready_for_operator_review');req(r['stage_count']==6);req(r['test_summary']['passed']);req(r['test_summary']['command_count']==4)
 st={x['adapter']:x for x in r['test_summary']['adapter_statuses']};req(st['browser_document']['status']=='not_applicable');req(st['javascript_syntax']['status']=='not_applicable');req(st['python_syntax']['passed']);req(st['python_cli_smoke']['passed']);req(len(calls)==1)
 pub=public_python_cli_checkpoint(r);enc=json.dumps(pub,sort_keys=True);req('main.py' not in enc);req('count_words' not in enc);req(str(rt) not in enc);req(not pub['dependencies_installed']);req(not pub['network_allowed']);req(not pub['apply_authorized']);req(not pub['repair_authorized'])
 r2=run_or_resume_python_cli_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));req(r2['operation_status']=='resumed');req(len(calls)==1)
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-bad-'))
try:
 p=approved(rt);calls=[];r=run_or_resume_python_cli_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls,bad=True));req(not r['ok']);req(r['failed_stage'] in {'generation','validation'});req(not r.get('repair_authorized',False));req(not _checkpoint_path(p['proposal_id'],1,rt).exists())
finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eidolon-v1203-race-'))
try:
 p=approved(rt);calls=[];out=[];bar=threading.Barrier(6);lock=threading.Lock();gen=provider(calls)
 def worker():
  bar.wait();v=run_or_resume_python_cli_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=gen)
  with lock:out.append(v)
 ts=[threading.Thread(target=worker) for _ in range(6)]
 for t in ts:t.start()
 for t in ts:t.join(30)
 req(len(out)==6);req(all(x.get('ok') for x in out),out);req(len(calls)==1);req(len({x.get('checkpoint_digest') for x in out})==1);req(sum(x.get('operation_status')=='created' for x in out)==1)
finally:shutil.rmtree(rt,ignore_errors=True)
req(sig()==before)
print(json.dumps({'ok':True,'version':'1203.2','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4),'source_immutable':True,'dependencies_installed':False,'network_allowed':False,'selected_project_modified':False,'apply_authorized':False,'repair_authorized':False,'release_authorized':False},sort_keys=True))
