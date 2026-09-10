from __future__ import annotations
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal
from grounded_development_planning import create_or_resume_grounded_plan
from structured_development_generation import generate_or_resume_structured_output, public_structured_output
start=time.monotonic(); checks=[]
def req(x,d=None): checks.append(bool(x)); assert x,d
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1200-9-runtime-'))
try:
 p=create_or_resume_development_proposal('Build me a to-do webpage',runtime_root=runtime); a=approve_development_campaign_proposal(p['proposal_id'],revision=1,revision_digest=p['revision_digest'],runtime_root=runtime); plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 authority={'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'planning_digest':plan['planning_digest'],'project_snapshot_digest':plan['project_snapshot_digest']}
 payload={'authority':authority,'files':[{'path':'index.html','operation':'create','content':'<!doctype html><main id="app"></main>'},{'path':'styles.css','operation':'create','content':'body { font-family: sans-serif; }'},{'path':'app.js','operation':'create','content':'const tasks = [];\n'}]}
 calls=[]
 def provider(prompt): calls.append(prompt); return json.dumps(payload)
 out=generate_or_resume_structured_output(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],runtime_root=runtime,provider_generate=provider)
 req(out['status']=='validated_generation_ready'); req(len(calls)==1); req(out['file_count']==3); req(not out['implementation_applied']); req(not out['workspace_created']); req(not out['command_executed']); req(not out['selected_project_modified']); req(not out['source_modified']); req(not out['authority_granted'])
 resumed=generate_or_resume_structured_output(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],runtime_root=runtime,provider_generate=lambda _: (_ for _ in ()).throw(Exception('must not call')))
 req(resumed['operation_status']=='resumed'); req(resumed['generation_digest']==out['generation_digest'])
 pub=public_structured_output(out); encoded=json.dumps(pub); req('index.html' not in encoded); req('<main' not in encoded); req(not pub['provider_payload_exposed']); req(pub['file_count']==3)
 raw=list((runtime/'development_campaigns'/'generation_private').rglob('*.json')); req(len(raw)==1); req('raw_output' in json.loads(raw[0].read_text()))
 def rejected(mod,status='structured_output_rejected'):
  r=Path(tempfile.mkdtemp(prefix='eidolon-v1200-9-case-'))
  try:
   q=create_or_resume_development_proposal('Build me a to-do webpage',runtime_root=r); approve_development_campaign_proposal(q['proposal_id'],revision=1,revision_digest=q['revision_digest'],runtime_root=r); pl=create_or_resume_grounded_plan(q['proposal_id'],expected_revision=1,expected_revision_digest=q['revision_digest'],runtime_root=r); au={'proposal_id':q['proposal_id'],'revision':1,'revision_digest':q['revision_digest'],'planning_digest':pl['planning_digest'],'project_snapshot_digest':pl['project_snapshot_digest']}; data={'authority':au,'files':[{'path':'index.html','operation':'create','content':'x'}]}; mod(data); z=generate_or_resume_structured_output(q['proposal_id'],expected_revision=1,expected_revision_digest=q['revision_digest'],expected_planning_digest=pl['planning_digest'],runtime_root=r,provider_generate=lambda _:json.dumps(data)); req(z['status']==status,z)
  finally: shutil.rmtree(r,ignore_errors=True)
 rejected(lambda d:d['files'][0].update(path='../evil.py'))
 rejected(lambda d:d['files'][0].update(path='unplanned.py'))
 rejected(lambda d:d['files'][0].update(content='x'*(240*1024+1)))
 rejected(lambda d:d['files'].append(dict(d['files'][0])), 'structured_output_rejected')
 rejected(lambda d:d['authority'].update(revision=2),'authority_binding_rejected')
 rejected(lambda d:d['files'][0].update(path='app.js',content='{'),'structured_output_rejected')
 bad=generate_or_resume_structured_output(p['proposal_id'],expected_revision=2,expected_revision_digest='0'*64,expected_planning_digest='0'*64,runtime_root=runtime,provider_generate=provider); req(bad['status']=='stale_or_missing_plan')
 req(not (ROOT/'data'/'development_campaigns').exists())
finally: shutil.rmtree(runtime,ignore_errors=True)
print(json.dumps({'ok':True,'suite':'v1200.7-v1200.9-structured-generation','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4)},sort_keys=True))
