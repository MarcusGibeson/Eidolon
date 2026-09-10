from __future__ import annotations
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal
from grounded_development_planning import create_or_resume_grounded_plan
from structured_development_generation import generate_or_resume_structured_output
from isolated_implementation_workspace import materialize_or_resume_workspace
from isolated_workspace_preview import create_or_resume_workspace_preview
import browser_runtime_test_adapter as adapter
from browser_runtime_test_adapter import run_or_resume_browser_runtime_test, public_browser_runtime_test, _runtime_test_path, _runtime_operation_path, _chromium_candidates, _operation_valid
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

runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-8-runtime-'))
try:
 p,ws,preview=campaign(runtime,"document.querySelector('#app').setAttribute('data-runtime-ready','true'); console.log('ready'); fetch('https://example.com/blocked').catch(()=>{});")
 result=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(result['ok']); req(result['passed']); req(result['contract_version']=='v1206.8'); req(result['platform_family'] in {'windows','linux','macos'}); req(result['browser_source_class'] in {'explicit','environment','path','platform_default'}); req(result['launch_attempt_count']>=1); req(result['cleanup_confirmed']); req(result['operation_recovery_count']==0); req(result['status']=='browser_runtime_test_passed'); req(result['dom_ready']); req(result['runtime_marker_present']); req(result['browser_executed']); req(not result['network_allowed']); req(result['blocked_external_request_count']>=1); req(result['page_error_count']==0); req(not result['selected_project_modified']); req(not result['apply_authorized']); req(not result['repair_authorized']); req(not result['authority_granted'])
 resumed=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime); req(resumed['operation_status']=='resumed'); req(resumed['browser_runtime_test_digest']==result['browser_runtime_test_digest'])
 pub=public_browser_runtime_test(result); encoded=json.dumps(pub); req(str(ws['workspace_path']) not in encoded); req('index.html' not in encoded); req(not pub['private_path_exposed']); req(not pub['private_content_exposed']); req(not pub['raw_browser_output_exposed'])
 req(run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest='0'*64,expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='stale_proposal_revision')
 req(run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest='1'*64,expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='stale_workspace_revision')
 op=_runtime_operation_path(p['proposal_id'],1,runtime); opraw=json.loads(op.read_text()); req(opraw['phase']=='sealed'); req(_operation_valid(opraw)); req(opraw['result_digest']==result['browser_runtime_test_digest'])
 rec=_runtime_test_path(p['proposal_id'],1,runtime); raw=json.loads(rec.read_text()); raw['passed']=False; rec.write_text(json.dumps(raw)); req(run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)['status']=='browser_runtime_record_invalid')
finally: shutil.rmtree(runtime,ignore_errors=True)

runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-8-error-'))
try:
 p,ws,preview=campaign(runtime,"throw new Error('private browser failure text');")
 result=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(result['ok']); req(not result['passed']); req(result['page_error_count']>=1); req('private browser failure text' not in json.dumps(public_browser_runtime_test(result)))
finally: shutil.rmtree(runtime,ignore_errors=True)


# Cross-platform candidate discovery is bounded, deduplicated, and path-private in public evidence.
original_system=adapter.platform.system; original_which=adapter.shutil.which
old_env=dict(adapter.os.environ)
try:
 adapter.platform.system=lambda:'Windows'
 adapter.shutil.which=lambda name: r'C:\FixtureTools\chromium.exe' if name=='chromium' else None
 adapter.os.environ['PROGRAMFILES']=r'C:\FixtureProgramFiles'
 adapter.os.environ['LOCALAPPDATA']=r'C:\FixtureLocal'
 rows=_chromium_candidates(r'C:\Explicit\chrome.exe')
 req(rows[0][0]=='explicit'); req(len(rows)<=adapter.MAX_BROWSER_LAUNCH_ATTEMPTS); req(len({v.lower() for _,v in rows})==len(rows)); req(any(k=='path' for k,_ in rows)); req(any(k=='platform_default' for k,_ in rows))
 adapter.platform.system=lambda:'Darwin'; adapter.shutil.which=lambda _name:None
 mac=_chromium_candidates(None); req(any('Applications' in value for _,value in mac)); req(len(mac)<=adapter.MAX_BROWSER_LAUNCH_ATTEMPTS)
 adapter.platform.system=lambda:'Linux'
 linux=_chromium_candidates(None); req(any(value.startswith('/usr/bin/') for _,value in linux)); req(len(linux)<=adapter.MAX_BROWSER_LAUNCH_ATTEMPTS)
finally:
 adapter.platform.system=original_system; adapter.shutil.which=original_which
 adapter.os.environ.clear(); adapter.os.environ.update(old_env)

# A stale prepared journal recovers once; a live prepared journal blocks duplicate launch.
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-8-recovery-'))
try:
 p,ws,preview=campaign(runtime,"document.body.setAttribute('data-runtime-ready','true');")
 op=_runtime_operation_path(p['proposal_id'],1,runtime); op.parent.mkdir(parents=True,exist_ok=True)
 payload={'schema_version':'1','contract_version':'v1206.8','phase':'prepared','proposal_id':p['proposal_id'],'proposal_revision':1,'proposal_revision_digest':p['revision_digest'],'workspace_digest':ws['workspace_digest'],'preview_digest':preview['preview_digest'],'attempt_count':1,'recovery_count':0,'updated_at_epoch':time.time(),'selected_project_modified':False,'authority_granted':False}
 adapter._write_operation(op,payload)
 live=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(live['status']=='browser_runtime_operation_in_progress')
 payload['updated_at_epoch']=time.time()-adapter.OPERATION_STALE_SECONDS-2; adapter._write_operation(op,payload)
 recovered=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(recovered['ok']); req(recovered['operation_recovery_count']==1); req(recovered['passed'])
finally: shutil.rmtree(runtime,ignore_errors=True)

# Tampered and stale operation journals block before browser launch.
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-8-journal-'))
try:
 p,ws,preview=campaign(runtime,"document.body.setAttribute('data-runtime-ready','true');")
 op=_runtime_operation_path(p['proposal_id'],1,runtime); op.parent.mkdir(parents=True,exist_ok=True)
 payload={'schema_version':'1','contract_version':'v1206.8','phase':'prepared','proposal_id':p['proposal_id'],'proposal_revision':1,'proposal_revision_digest':p['revision_digest'],'workspace_digest':ws['workspace_digest'],'preview_digest':preview['preview_digest'],'attempt_count':1,'recovery_count':0,'updated_at_epoch':time.time()-99,'selected_project_modified':False,'authority_granted':False}
 adapter._write_operation(op,payload); raw=json.loads(op.read_text()); raw['attempt_count']=99; op.write_text(json.dumps(raw))
 bad=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime); req(bad['status']=='browser_runtime_operation_invalid')
 payload['workspace_digest']='f'*64; adapter._write_operation(op,payload)
 stale=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime); req(stale['status']=='stale_browser_runtime_operation')
finally: shutil.rmtree(runtime,ignore_errors=True)

# Missing executable candidates fail with bounded, content-free evidence.
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1206-8-missing-browser-'))
orig_candidates=adapter._chromium_candidates
try:
 p,ws,preview=campaign(runtime,"document.body.setAttribute('data-runtime-ready','true');")
 adapter._chromium_candidates=lambda _explicit=None:[('explicit',str(runtime/'missing-browser'))]
 failed=run_or_resume_browser_runtime_test(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_workspace_digest=ws['workspace_digest'],expected_preview_digest=preview['preview_digest'],runtime_root=runtime)
 req(failed['ok']); req(not failed['passed']); req(failed['status']=='browser_runtime_test_failed'); req(failed['launch_attempt_count']==1); req(failed['browser_source_class']=='none'); req(not failed['cleanup_confirmed']); req(str(runtime) not in json.dumps(public_browser_runtime_test(failed)))
finally:
 adapter._chromium_candidates=orig_candidates; shutil.rmtree(runtime,ignore_errors=True)

dashboard=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8'); req('/api/development-campaign/browser-runtime-test' in dashboard); req('Run browser runtime test' in dashboard)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8'); req('v1206.8-browser-runtime-reliability' in release); req('v1206.5-browser-runtime-test-adapter' in release)
metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8'); req('WORKING_SOURCE_VERSION = "1206.8"' in metadata); req('WORKING_SOURCE_VERSION = "1206.5"' in metadata)
req(not (ROOT/'data'/'development_campaigns').exists())
print(json.dumps({'ok':True,'suite':'v1206.6-v1206.8-browser-runtime-reliability','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4)},sort_keys=True))
