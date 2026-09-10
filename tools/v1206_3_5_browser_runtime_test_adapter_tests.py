from __future__ import annotations
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal
from grounded_development_planning import create_or_resume_grounded_plan
from structured_development_generation import generate_or_resume_structured_output
from isolated_implementation_workspace import materialize_or_resume_workspace
from isolated_workspace_preview import create_or_resume_workspace_preview
from browser_runtime_test_adapter import run_or_resume_browser_runtime_test, public_browser_runtime_test, _runtime_test_path
start=time.monotonic(); checks=[]
def req(x,d=None): checks.append(bool(x)); assert x,d

def campaign(runtime, script):
 p=create_or_resume_development_proposal('Build me a browser runtime test webpage',runtime_root=runtime)
 approve_development_campaign_proposal(p['proposal_id'],revision=1,revision_digest=p['revision_digest'],runtime_root=runtime)
 plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 authority={'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'planning_digest':plan['planning_digest'],'project_snapshot_digest':plan['project_snapshot_digest']}
 files=[
  {'path':'index.html','operation':'create','content':'<!doctype html><html><head><title>Runtime</title><meta name="viewport" content="width=device-width"></head><body><main id="app"></main><script src="app.js"></script></body></html>'},
  {'path':'styles.css','operation':'create','content':'body{font-family:sans-serif}'},
  {'path':'app.js','operation':'create','content':script},
 ]
 gen=generate_or_resume_structured_output(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],runtime_root=runtime,provider_generate=lambda _:json.dumps({'authority':authority,'files':files}))
 ws=materialize_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],expected_generation_digest=gen['generation_digest'],runtime_root=runtime)
 preview=create_or_resume_workspace_preview(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 return p,ws,preview

runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-5-runtime-'))
try:
 p,ws,preview=campaign(runtime,"document.querySelector('#app').setAttribute('data-runtime-ready','true'); console.log('ready'); fetch('https://example.com/blocked').catch(()=>{});")
 result=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(result['ok']); req(result['passed']); req(result['status']=='browser_runtime_test_passed'); req(result['dom_ready']); req(result['runtime_marker_present']); req(result['browser_executed']); req(not result['network_allowed']); req(result['blocked_external_request_count']>=1); req(result['page_error_count']==0); req(not result['selected_project_modified']); req(not result['apply_authorized']); req(not result['repair_authorized']); req(not result['authority_granted'])
 resumed=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime); req(resumed['operation_status']=='resumed'); req(resumed['browser_runtime_test_digest']==result['browser_runtime_test_digest'])
 pub=public_browser_runtime_test(result); encoded=json.dumps(pub); req(str(ws['workspace_path']) not in encoded); req('index.html' not in encoded); req(not pub['private_path_exposed']); req(not pub['private_content_exposed']); req(not pub['raw_browser_output_exposed'])
 req(run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='stale_proposal_revision')
 req(run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest='1'*64,expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='stale_workspace_revision')
 rec=_runtime_test_path(p['proposal_id'],1,runtime); raw=json.loads(rec.read_text()); raw['passed']=False; rec.write_text(json.dumps(raw)); req(run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='browser_runtime_record_invalid')
finally: shutil.rmtree(runtime,ignore_errors=True)

runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-5-error-'))
try:
 p,ws,preview=campaign(runtime,"throw new Error('private browser failure text');")
 result=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(result['ok']); req(not result['passed']); req(result['page_error_count']>=1); req('private browser failure text' not in json.dumps(public_browser_runtime_test(result)))
finally: shutil.rmtree(runtime,ignore_errors=True)

dashboard=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8'); req('/api/development-campaign/browser-runtime-test' in dashboard); req('Run browser runtime test' in dashboard)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8'); req('v1206.5-browser-runtime-test-adapter' in release)
metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8'); req('WORKING_SOURCE_VERSION = "1206.5"' in metadata)
req(not (ROOT/'data'/'development_campaigns').exists())
print(json.dumps({'ok':True,'suite':'v1206.3-v1206.5-browser-runtime-test-adapter','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4)},sort_keys=True))
