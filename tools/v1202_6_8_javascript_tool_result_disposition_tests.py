from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn,list_development_campaign_proposals
from javascript_tool_test_execution_checkpoint import run_or_resume_javascript_tool_with_tests
from javascript_tool_result_disposition import (
 create_or_resume_javascript_tool_review_packet,dispose_javascript_tool_result,
 public_javascript_tool_review_packet,public_javascript_tool_disposition,
 _packet_path,_disposition_path
)
from isolated_implementation_workspace import _workspace_root
start=time.monotonic();checks=[]
def require(v,d=None):
 checks.append(bool(v))
 if not v: raise AssertionError(d)
def sig():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or any(x in {'.git','data','__pycache__','.pytest_cache','.venv','venv'} for x in p.parts) or p.suffix in {'.pyc','.pyo'}:continue
  h.update(p.relative_to(ROOT).as_posix().encode());h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()
def approved(rt,sid='review'):
 r=process_ordinary_chat_development_turn('Build me a Node command-line tool that counts words',action_projection={'intent':{'category':'action_request'}},session_id=sid,runtime_root=rt);p=r['proposal']
 a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",runtime_root=rt);require(a['event']=='approval_consumed');return p
def provider(calls):
 def gen(prompt):
  calls.append(1);payload=json.loads(prompt)
  content={'package.json':json.dumps({'name':'word-counter','private':True,'type':'commonjs'}),'cli.js':"const {countWords}=require('./lib/tool');if(process.argv.includes('--help')){console.log('usage');process.exit(0)}console.log(countWords(process.argv.slice(2).join(' ')));\n",'lib/tool.js':"exports.countWords=t=>String(t).trim()?String(t).trim().split(/\\s+/).length:0;\n",'tests/tool.test.js':"const test=require('node:test');const assert=require('node:assert');const {countWords}=require('../lib/tool');test('counts',()=>assert.equal(countWords('one two'),2));\n"}
  return json.dumps({'authority':payload['authority'],'files':[{'path':x,'operation':'create','content':content[x]} for x in payload['planned_paths']]})
 return gen
def ready(rt,sid='review'):
 p=approved(rt,sid);calls=[];cp=run_or_resume_javascript_tool_with_tests(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt,provider_generate=provider(calls));require(cp['ok']);require(len(calls)==1);return p,cp
before=sig()
# Packet creation, projection, idempotency, stale binding.
rt=Path(tempfile.mkdtemp(prefix='eid-v1202-8-packet-'))
try:
 p,cp=ready(rt)
 packet=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt)
 require(packet['ok']);require(packet['status']=='javascript_tool_result_awaiting_disposition');require(packet['allowed_dispositions']==['discard','reject','retain','revise']);require(packet['operator_disposition_required']);require(packet['operation_status']=='created')
 pub=public_javascript_tool_review_packet(packet);enc=json.dumps(pub,sort_keys=True);require(str(rt) not in enc);require('cli.js' not in enc);require(not pub['apply_authorized']);require(not pub['repair_authorized']);require(pub['operator_disposition_required'])
 again=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt);require(again['operation_status']=='resumed');require(again['review_packet_digest']==packet['review_packet_digest'])
 stale=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt);require(stale['status']=='stale_proposal_revision')
 stale2=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest='1'*64,runtime_root=rt);require(stale2['status']=='stale_checkpoint_revision')
finally:shutil.rmtree(rt,ignore_errors=True)
# Each disposition behavior.
for action in ('retain','revise','reject','discard'):
 rt=Path(tempfile.mkdtemp(prefix='eid-v1202-8-'+action+'-'))
 try:
  p,cp=ready(rt,action);packet=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt)
  root=_workspace_root(p['proposal_id'],1,cp['generation_digest'],rt);require(root.exists())
  d=dispose_javascript_tool_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action=action,runtime_root=rt)
  require(d['ok']);require(d['action']==action);require(d['consumption_count']==1);require(not d['apply_authorized']);require(not d['repair_authorized']);require(not d['selected_project_modified']);require(d['workspace_discarded']==(action=='discard'));require(root.exists()!=(action=='discard'))
  require(d['terminal']==(action in {'reject','discard'}));require(d['revision_required']==(action=='revise'));require(d['workspace_retained']==(action!='discard'));require(d['evidence_retained'])
  pub=public_javascript_tool_disposition(d);require(pub['action']==action);require(pub['consumption_count']==1);require(not pub['implementation_applied']);require(not pub['authority_granted'])
  same=dispose_javascript_tool_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action=action,runtime_root=rt);require(same['operation_status']=='resumed');require(same['consumption_count']==1)
  other='retain' if action!='retain' else 'reject';conflict=dispose_javascript_tool_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action=other,runtime_root=rt);require(conflict['status']=='javascript_tool_disposition_already_consumed')
  rows=list_development_campaign_proposals(runtime_root=rt,public=True)['proposals'];row=next(x for x in rows if x['proposal_id']==p['proposal_id']);require(row['javascript_tool_disposition']['action']==action);require(row['current_stage']==d['status'])
 finally:shutil.rmtree(rt,ignore_errors=True)
# Concurrent exactly-once same action.
rt=Path(tempfile.mkdtemp(prefix='eid-v1202-8-race-'))
try:
 p,cp=ready(rt,'race');packet=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt)
 out=[];lock=threading.Lock();bar=threading.Barrier(8)
 def worker():
  bar.wait();x=dispose_javascript_tool_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='retain',runtime_root=rt)
  with lock:out.append(x)
 ts=[threading.Thread(target=worker) for _ in range(8)];[t.start() for t in ts];[t.join(30) for t in ts]
 require(len(out)==8);require(all(x.get('ok') for x in out));require(len({x.get('disposition_digest') for x in out})==1);require(sum(x.get('operation_status')=='created' for x in out)==1);require(all(x.get('consumption_count')==1 for x in out))
finally:shutil.rmtree(rt,ignore_errors=True)
# Tamper blocking and unsupported action.
rt=Path(tempfile.mkdtemp(prefix='eid-v1202-8-tamper-'))
try:
 p,cp=ready(rt,'tamper');packet=create_or_resume_javascript_tool_review_packet(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],runtime_root=rt)
 bad=dispose_javascript_tool_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='apply',runtime_root=rt);require(bad['status']=='unsupported_javascript_tool_disposition')
 path=_packet_path(p['proposal_id'],1,rt);obj=json.loads(path.read_text());obj['status']='tampered';path.write_text(json.dumps(obj));blocked=dispose_javascript_tool_result(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_checkpoint_digest=cp['checkpoint_digest'],expected_review_packet_digest=packet['review_packet_digest'],action='retain',runtime_root=rt);require(blocked['status']=='javascript_tool_review_packet_missing_or_invalid');require(not _disposition_path(p['proposal_id'],1,rt).exists())
finally:shutil.rmtree(rt,ignore_errors=True)
# Dashboard and source boundaries.
dash=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8');require('/api/development-campaign/review-javascript-tool-result' in dash);require('/api/development-campaign/dispose-javascript-tool-result' in dash);require('data-disposition="retain"' in dash);require('data-disposition="discard"' in dash)
require(sig()==before)
print(json.dumps({'ok':True,'version':'1202.8','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4),'source_immutable':True,'selected_project_modified':False,'implementation_applied':False,'apply_authorized':False,'repair_authorized':False,'release_authorized':False,'authority_granted':False},sort_keys=True))
