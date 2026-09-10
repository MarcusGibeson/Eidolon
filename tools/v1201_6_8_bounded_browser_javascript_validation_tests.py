from __future__ import annotations
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal
from grounded_development_planning import create_or_resume_grounded_plan
from structured_development_generation import generate_or_resume_structured_output
from isolated_implementation_workspace import materialize_or_resume_workspace
from isolated_workspace_preview import create_or_resume_workspace_preview
from bounded_workspace_validation import validate_or_resume_workspace, public_validation, _validation_path
start=time.monotonic(); checks=[]
def req(x,d=None): checks.append(bool(x)); assert x,d

def campaign(runtime, js='const tasks=[];'):
 p=create_or_resume_development_proposal('Build me a to-do webpage',runtime_root=runtime); approve_development_campaign_proposal(p['proposal_id'],revision=1,revision_digest=p['revision_digest'],runtime_root=runtime)
 plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 a={'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'planning_digest':plan['planning_digest'],'project_snapshot_digest':plan['project_snapshot_digest']}
 files=[{'path':'index.html','operation':'create','content':'<!doctype html><html><head><title>Tasks</title><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="styles.css"></head><body><main id="app"></main><script src="app.js"></script></body></html>'},{'path':'styles.css','operation':'create','content':'body{font-family:sans-serif}'},{'path':'app.js','operation':'create','content':js}]
 gen=generate_or_resume_structured_output(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],runtime_root=runtime,provider_generate=lambda _:json.dumps({'authority':a,'files':files}))
 ws=materialize_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],expected_generation_digest=gen['generation_digest'],runtime_root=runtime)
 preview=create_or_resume_workspace_preview(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 return p,ws,preview

runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1201-8-runtime-'))
try:
 p,ws,preview=campaign(runtime)
 result=validate_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(result['ok']); req(result['passed']); req(result['status']=='workspace_validation_passed'); req(result['command_count']==1); req(result['command_executed']); req(result['tests_executed']); req(not result['apply_authorized']); req(not result['authority_granted'])
 adapters={x['adapter']:x for x in result['adapters']}; req(adapters['browser_document']['passed']); req(adapters['browser_document']['missing_asset_count']==0); req(adapters['javascript_syntax']['passed']); req(adapters['javascript_syntax']['file_count']==1)
 resumed=validate_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime); req(resumed['operation_status']=='resumed'); req(resumed['validation_digest']==result['validation_digest'])
 pub=public_validation(result); encoded=json.dumps(pub); req(str(ws['workspace_path']) not in encoded); req('index.html' not in encoded); req('const tasks' not in encoded); req(not pub['private_path_exposed']); req(not pub['raw_output_exposed']); req(pub['command_count']==1)
 req(validate_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_workspace_digest=ws['workspace_digest'],runtime_root=runtime)['status']=='stale_proposal_revision')
 req(validate_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest='1'*64,runtime_root=runtime)['status']=='stale_workspace_revision')
 rec=_validation_path(p['proposal_id'],1,runtime); raw=json.loads(rec.read_text()); raw['passed']=False; rec.write_text(json.dumps(raw)); req(validate_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='validation_record_invalid')
finally: shutil.rmtree(runtime,ignore_errors=True)

runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1201-8-fail-'))
try:
 p,ws,preview=campaign(runtime,js='const = ;')
 result=validate_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(result['ok']); req(not result['passed']); req(result['status']=='workspace_validation_failed'); js=next(x for x in result['adapters'] if x['adapter']=='javascript_syntax'); req(js['status']=='failed'); req(js['results'][0]['exit_class']=='nonzero'); req('output_digest' in js['results'][0]); req('stderr' not in json.dumps(public_validation(result)).lower())
finally: shutil.rmtree(runtime,ignore_errors=True)

dashboard=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8'); req('/api/development-campaign/validate' in dashboard); req('Run bounded validation' in dashboard); req('@media(max-width:760px)' in dashboard)
req(not (ROOT/'data'/'development_campaigns').exists())
print(json.dumps({'ok':True,'suite':'v1201.6-v1201.8-bounded-browser-javascript-validation','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4)},sort_keys=True))
