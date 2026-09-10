from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from grounded_development_planning import create_or_resume_grounded_plan
from javascript_tool_test_execution_checkpoint import run_or_resume_javascript_tool_with_tests,public_javascript_tool_test_checkpoint,_path
start=time.monotonic();checks=[]
def require(v,d=None):
 checks.append(bool(v));
 if not v: raise AssertionError(d)
def sig():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or any(x in {'.git','data','__pycache__','.pytest_cache','.venv','venv'} for x in p.parts) or p.suffix in {'.pyc','.pyo'}:continue
  h.update(p.relative_to(ROOT).as_posix().encode());h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()
def approved(rt):
 r=process_ordinary_chat_development_turn('Build me a Node command-line tool that counts words',action_projection={'intent':{'category':'action_request'}},session_id='js-tests',runtime_root=rt);p=r['proposal']
 a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",runtime_root=rt);require(a['event']=='approval_consumed');return p
def provider(calls,mode='pass'):
 def gen(prompt):
  calls.append(1);payload=json.loads(prompt)
  test="const test=require('node:test');const assert=require('node:assert');const {countWords}=require('../lib/tool');test('counts',()=>assert.equal(countWords('one two'),2));\n"
  if mode=='fail':test=test.replace("2));","3));")
  if mode=='network':test="const http=require('node:http');\n"+test
  content={'package.json':json.dumps({'name':'word-counter','private':True,'type':'commonjs'}),'cli.js':"const {countWords}=require('./lib/tool');if(process.argv.includes('--help')){console.log('usage');process.exit(0)}console.log(countWords(process.argv.slice(2).join(' ')));\n",'lib/tool.js':"exports.countWords=t=>String(t).trim()?String(t).trim().split(/\\s+/).length:0;\n",'tests/tool.test.js':test}
  return json.dumps({'authority':payload['authority'],'files':[{'path':x,'operation':'create','content':content[x]} for x in payload['planned_paths']]})
 return gen
before=sig()
rt=Path(tempfile.mkdtemp(prefix='eid-v1202-5-pass-'))
try:
 p=approved(rt);plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt)
 require([x['adapter'] for x in plan['test_plan']]==['javascript_syntax','node_cli_smoke'])
 calls=[];r=run_or_resume_javascript_tool_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls))
 require(r['ok']);require(r['status']=='javascript_tool_tests_ready_for_operator_review');require(r['stage_count']==7);require(r['project_test_summary']['passed']);require(r['project_test_summary']['test_file_count']==1);require(r['project_test_summary']['command_count']==1);require(len(calls)==1)
 pub=public_javascript_tool_test_checkpoint(r);enc=json.dumps(pub,sort_keys=True);require('tool.test.js' not in enc);require('counts' not in enc);require(str(rt) not in enc);require(not pub['apply_authorized']);require(not pub['repair_authorized'])
 rr=run_or_resume_javascript_tool_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));require(rr['operation_status']=='resumed');require(len(calls)==1)
finally:shutil.rmtree(rt,ignore_errors=True)
for mode,status in [('fail','project_javascript_tests_failed'),('network','project_test_network_capability_rejected')]:
 rt=Path(tempfile.mkdtemp(prefix='eid-v1202-5-'+mode+'-'))
 try:
  p=approved(rt);calls=[];r=run_or_resume_javascript_tool_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls,mode));require(not r['ok']);require(r['failed_stage']=='project_tests');require(r['status']==status);require(not r['repair_authorized']);require(not _path(p['proposal_id'],1,rt).exists())
 finally:shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eid-v1202-5-race-'))
try:
 p=approved(rt);calls=[];out=[];bar=threading.Barrier(6);lock=threading.Lock();gen=provider(calls)
 def worker():
  bar.wait();x=run_or_resume_javascript_tool_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=gen)
  with lock:out.append(x)
 ts=[threading.Thread(target=worker) for _ in range(6)]
 [t.start() for t in ts];[t.join(30) for t in ts]
 require(len(out)==6);require(all(x.get('ok') for x in out),out);require(len({x.get('checkpoint_digest') for x in out})==1);require(len(calls)==1);require(sum(x.get('operation_status')=='created' for x in out)==1)
finally:shutil.rmtree(rt,ignore_errors=True)
require(sig()==before)
print(json.dumps({'ok':True,'version':'1202.5','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4),'source_immutable':True,'selected_project_modified':False,'dependencies_installed':False,'network_allowed':False,'apply_authorized':False,'repair_authorized':False,'release_authorized':False,'authority_granted':False},sort_keys=True))
