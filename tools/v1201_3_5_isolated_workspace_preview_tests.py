from __future__ import annotations
import json, shutil, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import create_or_resume_development_proposal, approve_development_campaign_proposal
from grounded_development_planning import create_or_resume_grounded_plan
from structured_development_generation import generate_or_resume_structured_output
from isolated_implementation_workspace import materialize_or_resume_workspace
from isolated_workspace_preview import create_or_resume_workspace_preview, resolve_preview_asset, public_preview
start=time.monotonic(); checks=[]
def req(x,d=None): checks.append(bool(x)); assert x,d
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1201-5-runtime-'))
try:
 p=create_or_resume_development_proposal('Build me a to-do webpage',runtime_root=runtime); approve_development_campaign_proposal(p['proposal_id'],revision=1,revision_digest=p['revision_digest'],runtime_root=runtime); plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime)
 a={'proposal_id':p['proposal_id'],'revision':1,'revision_digest':p['revision_digest'],'planning_digest':plan['planning_digest'],'project_snapshot_digest':plan['project_snapshot_digest']}
 files=[{'path':'index.html','operation':'create','content':'<!doctype html><html><head><title>Tasks</title><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="styles.css"></head><body><main id="app"></main><script src="app.js"></script></body></html>'},{'path':'styles.css','operation':'create','content':'body{font-family:sans-serif}'},{'path':'app.js','operation':'create','content':'const tasks=[];'}]
 gen=generate_or_resume_structured_output(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],runtime_root=runtime,provider_generate=lambda _:json.dumps({'authority':a,'files':files}))
 ws=materialize_or_resume_workspace(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_planning_digest=plan['planning_digest'],expected_generation_digest=gen['generation_digest'],runtime_root=runtime); req(ws['ok'])
 preview=create_or_resume_workspace_preview(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime); req(preview['status']=='browser_preview_ready'); req(preview['evidence']['missing_asset_count']==0); req(preview['evidence']['has_title']); req(preview['evidence']['has_viewport']); req(preview['preview_url'].startswith('/development-preview/'))
 token=preview['preview_token']; html=resolve_preview_asset(token,'',runtime_root=runtime); req(html['ok']); req(html['content_type']=='text/html'); req(b'<main' in html['content']); css=resolve_preview_asset(token,'styles.css',runtime_root=runtime); req(css['ok']); req(css['content_type']=='text/css'); req(not resolve_preview_asset(token,'../secret','runtime_root' if False else runtime).get('ok'))
 resumed=create_or_resume_workspace_preview(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime); req(resumed['operation_status']=='resumed'); req(resumed['preview_digest']==preview['preview_digest'])
 pub=public_preview(preview); enc=json.dumps(pub); req(str(ws['workspace_path']) not in enc); req('index.html' not in enc); req(not pub['private_path_exposed']); req(not pub['apply_authorized']); req(not pub['tests_executed']); req(not pub['authority_granted'])
 (Path(ws['workspace_path'])/'index.html').write_text('tampered'); bad=create_or_resume_workspace_preview(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=runtime); req(bad['status'] in {'workspace_record_invalid','preview_record_invalid'})
 dashboard=(ROOT/'conscious_agent'/'dashboard.py').read_text(encoding='utf-8')
 req('/api/development-campaign/preview' in dashboard); req('/development-preview/' in dashboard); req('Content-Security-Policy' in dashboard); req('Open isolated preview' in dashboard); req('@media(max-width:760px)' in dashboard)
 req(not (ROOT/'data'/'development_campaigns').exists())
finally: shutil.rmtree(runtime,ignore_errors=True)
print(json.dumps({'ok':True,'suite':'v1201.3-v1201.5-isolated-workspace-preview','checks':len(checks),'passed':sum(checks),'elapsed_seconds':round(time.monotonic()-start,4)},sort_keys=True))
