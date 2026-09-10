from __future__ import annotations
import hashlib, json, shutil, sys, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from grounded_development_planning import create_or_resume_grounded_plan
from javascript_tool_implementation_foundations import run_or_resume_javascript_tool_implementation, public_javascript_tool_checkpoint, _checkpoint_path

start=time.monotonic(); checks=[]
def require(v,d=None):
 checks.append(bool(v))
 if not v: raise AssertionError(d)

def source_sig():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or any(x in {'.git','data','__pycache__','.pytest_cache','.venv','venv'} for x in p.parts) or p.suffix in {'.pyc','.pyo'}: continue
  h.update(p.relative_to(ROOT).as_posix().encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()

def approved(rt):
 r=process_ordinary_chat_development_turn('Build me a Node command-line tool that counts words',action_projection={'intent':{'category':'action_request'}},session_id='js-tool',runtime_root=rt)
 require(r['active']); p=r['proposal']
 a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",runtime_root=rt)
 require(a['event']=='approval_consumed'); require(a['approval_consumption_count']==1)
 return p

def provider(calls,bad=False):
 def gen(prompt):
  calls.append(1); payload=json.loads(prompt); files=[]
  content={
   'package.json': json.dumps({'name':'word-counter','private':True,'type':'commonjs','bin':{'word-counter':'cli.js'}}),
   'cli.js': "const {countWords}=require('./lib/tool'); if(process.argv.includes('--help')){console.log('usage: word-counter <text>');process.exit(0)} console.log(countWords(process.argv.slice(2).join(' ')));\n",
   'lib/tool.js': "exports.countWords=(text)=>String(text).trim()?String(text).trim().split(/\\s+/).length:0;\n",
   'tests/tool.test.js': "const assert=require('node:assert'); const {countWords}=require('../lib/tool'); assert.equal(countWords('one two'),2);\n",
  }
  if bad: content['cli.js']='const = ;\n'
  for path in payload['planned_paths']:
   files.append({'path':path,'operation':'create','content':content[path]})
  return json.dumps({'authority':payload['authority'],'files':files})
 return gen

before=source_sig(); rt=Path(tempfile.mkdtemp(prefix='eidolon-v1202-js-'))
try:
 p=approved(rt)
 plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt)
 require(plan['project_kind']=='new_javascript_tool_project',plan)
 require([x['relative_path'] for x in plan['file_plan']]==['package.json','cli.js','lib/tool.js','tests/tool.test.js'])
 require([x['adapter'] for x in plan['test_plan']]==['javascript_syntax','node_cli_smoke'])
 calls=[]
 result=run_or_resume_javascript_tool_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls))
 require(result['ok']); require(result['status']=='javascript_tool_implementation_ready_for_operator_review'); require(result['stage_count']==6)
 require([x['stage'] for x in result['stage_receipts']]==['proposal','approval','planning','generation','workspace','validation'])
 require(result['change_summary']['file_count']==4); require(result['test_summary']['passed']); require(result['test_summary']['command_count']==4)
 statuses={x['adapter']:x for x in result['test_summary']['adapter_statuses']}
 require(statuses['browser_document']['status']=='not_applicable'); require(statuses['javascript_syntax']['passed']); require(statuses['node_cli_smoke']['passed'])
 require(len(calls)==1); require(not result['implementation_applied']); require(not result['apply_authorized']); require(not result['repair_authorized'])
 public=public_javascript_tool_checkpoint(result); encoded=json.dumps(public,sort_keys=True)
 require('word-counter' not in encoded); require('cli.js' not in encoded); require(str(rt) not in encoded); require(not public['private_content_exposed'])
 resumed=run_or_resume_javascript_tool_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls))
 require(resumed['operation_status']=='resumed'); require(len(calls)==1)
finally: shutil.rmtree(rt,ignore_errors=True)

rt=Path(tempfile.mkdtemp(prefix='eidolon-v1202-bad-'))
try:
 p=approved(rt); calls=[]
 result=run_or_resume_javascript_tool_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls,bad=True))
 require(not result['ok']); require(result['failed_stage']=='validation'); require(not result['repair_authorized']); require(not _checkpoint_path(p['proposal_id'],1,rt).exists())
finally: shutil.rmtree(rt,ignore_errors=True)

rt=Path(tempfile.mkdtemp(prefix='eidolon-v1202-race-'))
try:
 p=approved(rt); calls=[]; out=[]; barrier=threading.Barrier(6); lock=threading.Lock(); gen=provider(calls)
 def worker():
  barrier.wait(); value=run_or_resume_javascript_tool_implementation(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=gen)
  with lock: out.append(value)
 ts=[threading.Thread(target=worker) for _ in range(6)]
 for t in ts:t.start()
 for t in ts:t.join(30)
 require(len(out)==6); require(all(x.get('ok') for x in out),out); require(len({x.get('checkpoint_digest') for x in out})==1); require(len(calls)==1)
 require(sum(x.get('operation_status')=='created' for x in out)==1); require(sum(x.get('operation_status')=='resumed' for x in out)==5)
finally: shutil.rmtree(rt,ignore_errors=True)
require(source_sig()==before)
print(json.dumps({'ok':True,'version':'1202.2','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4),'source_immutable':True,'selected_project_modified':False,'apply_authorized':False,'repair_authorized':False,'release_authorized':False,'authority_granted':False},sort_keys=True))
